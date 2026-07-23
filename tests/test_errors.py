"""Test unitari del formato d'errore unico (nessun DB).

Costruiscono un'app minimale con i soli gestori d'errore per verificare che
ogni tipo di errore risponda nella forma ``{"error": {"code", "message"}}``.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api.errors import APIError, register_exception_handlers


def _build_client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    class Body(BaseModel):
        valore: int

    @app.get("/boom")
    def boom() -> None:
        raise APIError(status_code=418, code="sono_una_teiera", message="nope")

    @app.post("/valida")
    def valida(_body: Body) -> dict[str, str]:
        return {"ok": "sì"}

    @app.get("/crash")
    def crash() -> None:
        raise RuntimeError("dettaglio interno che non deve trapelare")

    return TestClient(app, raise_server_exceptions=False)


def test_api_error_rispetta_il_formato() -> None:
    response = _build_client().get("/boom")
    assert response.status_code == 418
    assert response.json() == {"error": {"code": "sono_una_teiera", "message": "nope"}}


def test_errore_di_validazione_rispetta_il_formato() -> None:
    response = _build_client().post("/valida", json={"valore": "non-un-numero"})
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "validation_error"


def test_eccezione_non_gestita_non_espone_dettagli() -> None:
    response = _build_client().get("/crash")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert "dettaglio interno" not in body["error"]["message"]
