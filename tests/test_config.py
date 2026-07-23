"""Test unitari della configurazione (nessun DB coinvolto)."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_letta_dall_ambiente(monkeypatch) -> None:
    """DATABASE_URL è letta dall'ambiente."""
    url = "postgresql+psycopg://localhost:5432/magazzino"
    monkeypatch.setenv("DATABASE_URL", url)
    settings = Settings(_env_file=None)
    assert settings.database_url == url


def test_database_url_obbligatoria(monkeypatch) -> None:
    """Senza DATABASE_URL la configurazione fallisce: nessun default nel codice."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_auth_secret_key_troppo_corta_rifiutata(monkeypatch) -> None:
    """Una chiave di firma sotto i 32 caratteri è rifiutata all'avvio."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost:5432/x")
    monkeypatch.setenv("AUTH_SECRET_KEY", "troppo-corta")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_access_token_expire_minutes_default(monkeypatch) -> None:
    """Se ACCESS_TOKEN_EXPIRE_MINUTES non è impostata vale il default 60."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost:5432/x")
    monkeypatch.setenv("AUTH_SECRET_KEY", "chiave-abbastanza-lunga-1234567890")
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    settings = Settings(_env_file=None)
    assert settings.access_token_expire_minutes == 60
