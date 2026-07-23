"""Test d'integrazione dell'API di autenticazione contro un Postgres reale.

Coprono il contratto end-to-end (login, /me) e la dependency di protezione
riusabile (401 senza token, 403 con ruolo insufficiente, 200 con ruolo
adeguato), su un'app che monta il router reale e usa la stessa sessione del
container tramite override della dependency ``get_session``.
"""

from collections.abc import Iterator
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.auth import router as auth_router
from app.api.deps import get_current_user, require_role
from app.api.errors import register_exception_handlers
from app.db.session import get_session
from app.models.user import Role, User
from app.services import auth as auth_service

ADMIN = ("admin", "admin-pass")
OPERATOR = ("operatore", "op-pass")


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """App reale (router auth + probe di protezione) sul DB del container."""
    # Seed di un admin e di un operatore.
    with session_factory() as seed_session:
        auth_service.create_user(seed_session, ADMIN[0], ADMIN[1], Role.admin)
        auth_service.create_user(seed_session, OPERATOR[0], OPERATOR[1], Role.operator)
        seed_session.commit()

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(auth_router)

    # Endpoint di prova che esercitano le dependency di protezione riusabili.
    @app.get("/v1/_probe/admin", dependencies=[Depends(require_role(Role.admin))])
    def _probe_admin() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/v1/_probe/any")
    def _probe_any(
        user: Annotated[User, Depends(get_current_user)],
    ) -> dict[str, int]:
        return {"id": user.id}

    def _override_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _override_session
    yield TestClient(app)


def _login(client: TestClient, username: str, password: str):
    return client.post(
        "/v1/auth/login", json={"username": username, "password": password}
    )


def _token(client: TestClient, credentials: tuple[str, str]) -> str:
    response = _login(client, *credentials)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_login_credenziali_valide(client: TestClient) -> None:
    response = _login(client, *ADMIN)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == ADMIN[0]
    assert body["user"]["role"] == "admin"
    assert "password" not in response.text.lower()


def test_login_password_errata(client: TestClient) -> None:
    response = _login(client, ADMIN[0], "sbagliata")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_login_utente_inesistente(client: TestClient) -> None:
    response = _login(client, "nessuno", "x")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_login_body_incompleto_e_validato(client: TestClient) -> None:
    response = client.post("/v1/auth/login", json={"username": "admin"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_me_con_token_valido(client: TestClient) -> None:
    token = _token(client, OPERATOR)
    response = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == OPERATOR[0]
    assert body["role"] == "operator"


def test_me_senza_token(client: TestClient) -> None:
    response = client.get("/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_me_con_token_invalido(client: TestClient) -> None:
    response = client.get(
        "/v1/auth/me", headers={"Authorization": "Bearer non.un.token"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_protezione_senza_token_401(client: TestClient) -> None:
    response = client.get("/v1/_probe/admin")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_protezione_ruolo_insufficiente_403(client: TestClient) -> None:
    token = _token(client, OPERATOR)
    response = client.get(
        "/v1/_probe/admin", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_protezione_ruolo_adeguato_200(client: TestClient) -> None:
    token = _token(client, ADMIN)
    response = client.get(
        "/v1/_probe/admin", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}
