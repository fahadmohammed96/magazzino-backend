"""Test d'integrazione dell'API clienti contro un Postgres reale (testcontainers).

Coprono il contratto CRUD end-to-end, il filtro ``?q=``, la validazione (422),
gli errori 404 e l'autorizzazione (401 senza token; admin e operator, entrambi
ammessi dal default MYL-18, possono leggere e scrivere).
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.errors import register_exception_handlers
from app.db.session import get_session
from app.models.user import Role
from app.services import auth as auth_service

ADMIN = ("admin", "admin-pass")
OPERATOR = ("operatore", "op-pass")


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """App reale (router clienti + auth) sul DB del container, con utenti seedati."""
    with session_factory() as seed_session:
        auth_service.create_user(seed_session, ADMIN[0], ADMIN[1], Role.admin)
        auth_service.create_user(seed_session, OPERATOR[0], OPERATOR[1], Role.operator)
        seed_session.commit()

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(customers_router)

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


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payload(ragione_sociale: str, **extra: object) -> dict[str, object]:
    base: dict[str, object] = {"ragione_sociale": ragione_sociale}
    base.update(extra)
    return base


def test_crea_cliente_come_operator_201(client: TestClient) -> None:
    token = _token(client, OPERATOR)
    response = client.post(
        "/v1/customers",
        headers=_auth(token),
        json=_payload(
            "Acme S.r.l.",
            piva="12345678901",
            indirizzo_spedizione="Via Roma 1",
            contatti={"email": "info@acme.example", "telefono": "021234567"},
        ),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] > 0
    assert body["ragione_sociale"] == "Acme S.r.l."
    assert body["contatti"] == {"email": "info@acme.example", "telefono": "021234567"}
    assert body["created_at"] and body["updated_at"]


def test_crea_cliente_come_admin_201(client: TestClient) -> None:
    token = _token(client, ADMIN)
    response = client.post(
        "/v1/customers", headers=_auth(token), json=_payload("Admin Client")
    )
    assert response.status_code == 201, response.text
    assert response.json()["contatti"] == {"email": None, "telefono": None}


def test_crea_senza_ragione_sociale_422(client: TestClient) -> None:
    token = _token(client, OPERATOR)
    response = client.post(
        "/v1/customers", headers=_auth(token), json={"piva": "12345678901"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_lista_e_filtro_q(client: TestClient) -> None:
    token = _token(client, OPERATOR)
    for nome in ("Alfa Trasporti", "Beta Logistica", "Alfa Ricambi"):
        created = client.post(
            "/v1/customers", headers=_auth(token), json=_payload(nome)
        )
        assert created.status_code == 201, created.text

    tutti = client.get("/v1/customers", headers=_auth(token))
    assert tutti.status_code == 200
    nomi = [c["ragione_sociale"] for c in tutti.json()]
    assert nomi == ["Alfa Ricambi", "Alfa Trasporti", "Beta Logistica"]

    filtrati = client.get("/v1/customers", headers=_auth(token), params={"q": "alfa"})
    assert filtrati.status_code == 200
    nomi_filtrati = {c["ragione_sociale"] for c in filtrati.json()}
    assert nomi_filtrati == {"Alfa Trasporti", "Alfa Ricambi"}


def test_dettaglio_e_404(client: TestClient) -> None:
    token = _token(client, OPERATOR)
    created = client.post(
        "/v1/customers", headers=_auth(token), json=_payload("Dettaglio SpA")
    )
    customer_id = created.json()["id"]

    ok = client.get(f"/v1/customers/{customer_id}", headers=_auth(token))
    assert ok.status_code == 200
    assert ok.json()["ragione_sociale"] == "Dettaglio SpA"

    missing = client.get("/v1/customers/999999", headers=_auth(token))
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_aggiorna_cliente(client: TestClient) -> None:
    token = _token(client, OPERATOR)
    created = client.post(
        "/v1/customers",
        headers=_auth(token),
        json=_payload("Vecchio Nome", piva="11111111111"),
    )
    customer_id = created.json()["id"]

    updated = client.put(
        f"/v1/customers/{customer_id}",
        headers=_auth(token),
        json=_payload(
            "Nuovo Nome",
            codice_fiscale="RSSMRA80A01H501U",
            contatti={"email": "nuovo@example.com"},
        ),
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["ragione_sociale"] == "Nuovo Nome"
    # PUT sostituisce l'intera anagrafica: la piva non fornita torna a None.
    assert body["piva"] is None
    assert body["codice_fiscale"] == "RSSMRA80A01H501U"
    assert body["contatti"]["email"] == "nuovo@example.com"
    assert body["updated_at"] >= body["created_at"]


def test_aggiorna_inesistente_404(client: TestClient) -> None:
    token = _token(client, OPERATOR)
    response = client.put(
        "/v1/customers/999999", headers=_auth(token), json=_payload("X")
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_elimina_cliente(client: TestClient) -> None:
    token = _token(client, OPERATOR)
    created = client.post(
        "/v1/customers", headers=_auth(token), json=_payload("Da Eliminare")
    )
    customer_id = created.json()["id"]

    deleted = client.delete(f"/v1/customers/{customer_id}", headers=_auth(token))
    assert deleted.status_code == 204
    assert deleted.content == b""

    missing = client.get(f"/v1/customers/{customer_id}", headers=_auth(token))
    assert missing.status_code == 404


def test_elimina_inesistente_404(client: TestClient) -> None:
    token = _token(client, ADMIN)
    response = client.delete("/v1/customers/999999", headers=_auth(token))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_lista_senza_token_401(client: TestClient) -> None:
    response = client.get("/v1/customers")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_crea_con_token_invalido_401(client: TestClient) -> None:
    response = client.post(
        "/v1/customers",
        headers=_auth("non.un.token"),
        json=_payload("Ignota"),
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
