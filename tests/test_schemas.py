"""Test unitari degli schemi Pydantic dell'API di autenticazione (nessun DB)."""

import pytest
from pydantic import ValidationError

from app.api.schemas import LoginRequest


def test_login_request_valida() -> None:
    """Un corpo valido è accettato."""
    req = LoginRequest(username="utente", password="password")
    assert req.username == "utente"
    assert req.password == "password"


def test_login_request_password_oltre_72_rifiutata() -> None:
    """La password oltre 72 caratteri (limite bcrypt) è rifiutata alla validazione."""
    with pytest.raises(ValidationError):
        LoginRequest(username="utente", password="x" * 73)


def test_login_request_campi_vuoti_rifiutati() -> None:
    """Username e password non possono essere vuoti."""
    with pytest.raises(ValidationError):
        LoginRequest(username="", password="")
