"""Test d'integrazione dell'API del catalogo prodotti contro un Postgres reale.

Coprono il contratto end-to-end: CRUD con i vincoli di ruolo (operator riceve
403 in scrittura, admin 2xx), calcolo e filtro ``low_stock``, conflitto su
``sku`` (409), 404 su id inesistente, 422 su validazione, e l'import/export CSV
(round-trip, con raccolta degli errori sulle righe invalide).
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.auth import router as auth_router
from app.api.errors import register_exception_handlers
from app.api.products import router as products_router
from app.db.session import get_session
from app.models.user import Role
from app.services import auth as auth_service

ADMIN = ("admin", "admin-pass")
OPERATOR = ("operatore", "op-pass")

PRODOTTO = {
    "sku": "SKU-1",
    "name": "Vite M6",
    "description": "acciaio inox",
    "price": "1.50",
    "stock_quantity": 100,
    "low_stock_threshold": 10,
}


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """App reale (auth + products) sul DB del container, con admin e operatore."""
    with session_factory() as seed_session:
        auth_service.create_user(seed_session, ADMIN[0], ADMIN[1], Role.admin)
        auth_service.create_user(seed_session, OPERATOR[0], OPERATOR[1], Role.operator)
        seed_session.commit()

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(products_router)

    def _override_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _override_session
    yield TestClient(app)


def _token(client: TestClient, credentials: tuple[str, str]) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"username": credentials[0], "password": credentials[1]},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(client: TestClient, credentials: tuple[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(client, credentials)}"}


def _crea(client: TestClient, **overrides: object) -> dict:
    body = {**PRODOTTO, **overrides}
    response = client.post("/v1/products", json=body, headers=_auth(client, ADMIN))
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_crea_prodotto_201(client: TestClient) -> None:
    body = _crea(client)
    assert body["sku"] == "SKU-1"
    assert body["price"] == "1.50"
    assert body["low_stock"] is False
    assert body["id"] > 0
    assert "created_at" in body and "updated_at" in body


def test_operator_non_puo_creare_403(client: TestClient) -> None:
    response = client.post(
        "/v1/products", json=PRODOTTO, headers=_auth(client, OPERATOR)
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_creazione_senza_token_401(client: TestClient) -> None:
    response = client.post("/v1/products", json=PRODOTTO)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_sku_duplicato_409(client: TestClient) -> None:
    _crea(client)
    response = client.post("/v1/products", json=PRODOTTO, headers=_auth(client, ADMIN))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "sku_conflict"


def test_creazione_prezzo_negativo_422(client: TestClient) -> None:
    response = client.post(
        "/v1/products",
        json={**PRODOTTO, "price": "-1.00"},
        headers=_auth(client, ADMIN),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_operator_puo_leggere_lista_e_dettaglio(client: TestClient) -> None:
    creato = _crea(client)
    lista = client.get("/v1/products", headers=_auth(client, OPERATOR))
    assert lista.status_code == 200
    assert [p["sku"] for p in lista.json()] == ["SKU-1"]

    dettaglio = client.get(
        f"/v1/products/{creato['id']}", headers=_auth(client, OPERATOR)
    )
    assert dettaglio.status_code == 200
    assert dettaglio.json()["id"] == creato["id"]


def test_dettaglio_id_inesistente_404(client: TestClient) -> None:
    response = client.get("/v1/products/999999", headers=_auth(client, OPERATOR))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_low_stock_calcolato_e_filtro(client: TestClient) -> None:
    _crea(client, sku="ALTA", stock_quantity=100, low_stock_threshold=10)
    _crea(client, sku="BASSA", stock_quantity=5, low_stock_threshold=10)

    tutti = client.get("/v1/products", headers=_auth(client, OPERATOR)).json()
    per_sku = {p["sku"]: p for p in tutti}
    assert per_sku["ALTA"]["low_stock"] is False
    assert per_sku["BASSA"]["low_stock"] is True

    solo_bassi = client.get(
        "/v1/products?low_stock=true", headers=_auth(client, OPERATOR)
    ).json()
    assert [p["sku"] for p in solo_bassi] == ["BASSA"]


def test_admin_aggiorna_prodotto(client: TestClient) -> None:
    creato = _crea(client)
    response = client.put(
        f"/v1/products/{creato['id']}",
        json={**PRODOTTO, "name": "Vite M6 zincata", "stock_quantity": 3},
        headers=_auth(client, ADMIN),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Vite M6 zincata"
    assert body["stock_quantity"] == 3
    assert body["low_stock"] is True


def test_operator_non_puo_aggiornare_403(client: TestClient) -> None:
    creato = _crea(client)
    response = client.put(
        f"/v1/products/{creato['id']}", json=PRODOTTO, headers=_auth(client, OPERATOR)
    )
    assert response.status_code == 403


def test_aggiornamento_id_inesistente_404(client: TestClient) -> None:
    response = client.put(
        "/v1/products/999999", json=PRODOTTO, headers=_auth(client, ADMIN)
    )
    assert response.status_code == 404


def test_aggiornamento_sku_su_altro_esistente_409(client: TestClient) -> None:
    _crea(client, sku="SKU-A")
    b = _crea(client, sku="SKU-B")
    response = client.put(
        f"/v1/products/{b['id']}",
        json={**PRODOTTO, "sku": "SKU-A"},
        headers=_auth(client, ADMIN),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "sku_conflict"


def test_admin_elimina_prodotto_204(client: TestClient) -> None:
    creato = _crea(client)
    response = client.delete(
        f"/v1/products/{creato['id']}", headers=_auth(client, ADMIN)
    )
    assert response.status_code == 204
    dopo = client.get(f"/v1/products/{creato['id']}", headers=_auth(client, OPERATOR))
    assert dopo.status_code == 404


def test_operator_non_puo_eliminare_403(client: TestClient) -> None:
    creato = _crea(client)
    response = client.delete(
        f"/v1/products/{creato['id']}", headers=_auth(client, OPERATOR)
    )
    assert response.status_code == 403


def test_import_csv_crea_e_aggiorna_con_errori(client: TestClient) -> None:
    """Import misto: righe valide applicate (create+update), invalida raccolta."""
    _crea(client, sku="SKU-1", name="Vecchio", stock_quantity=1)
    csv_text = (
        "sku,name,description,price,stock_quantity,low_stock_threshold\n"
        "SKU-1,Aggiornato,,2.00,50,5\n"  # update dell'esistente
        "SKU-NEW,Nuovo,desc,3.50,7,10\n"  # create
        "SKU-BAD,Rotto,,non-un-prezzo,7,10\n"  # riga 4: prezzo invalido
    )
    response = client.post(
        "/v1/products/import",
        files={"file": ("prodotti.csv", csv_text, "text/csv")},
        headers=_auth(client, ADMIN),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == 1
    assert body["updated"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 4

    # L'aggiornamento è stato applicato (upsert per sku).
    lista = client.get("/v1/products", headers=_auth(client, ADMIN)).json()
    per_sku = {p["sku"]: p for p in lista}
    assert per_sku["SKU-1"]["name"] == "Aggiornato"
    assert per_sku["SKU-1"]["stock_quantity"] == 50
    assert "SKU-NEW" in per_sku
    assert "SKU-BAD" not in per_sku


def test_operator_non_puo_importare_403(client: TestClient) -> None:
    response = client.post(
        "/v1/products/import",
        files={"file": ("p.csv", "sku,name\n", "text/csv")},
        headers=_auth(client, OPERATOR),
    )
    assert response.status_code == 403


def test_export_csv_round_trip(client: TestClient) -> None:
    """L'export è re-importabile: reimportarlo aggiorna senza errori."""
    _crea(client, sku="SKU-1", stock_quantity=100, low_stock_threshold=10)
    _crea(client, sku="SKU-2", stock_quantity=2, low_stock_threshold=5)

    export = client.get("/v1/products/export", headers=_auth(client, OPERATOR))
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    testo = export.text
    assert (
        testo.splitlines()[0]
        == "sku,name,description,price,stock_quantity,low_stock_threshold"
    )

    reimport = client.post(
        "/v1/products/import",
        files={"file": ("export.csv", testo, "text/csv")},
        headers=_auth(client, ADMIN),
    )
    assert reimport.status_code == 200
    body = reimport.json()
    assert body["created"] == 0
    assert body["updated"] == 2
    assert body["errors"] == []


def test_export_senza_token_401(client: TestClient) -> None:
    response = client.get("/v1/products/export")
    assert response.status_code == 401
