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
