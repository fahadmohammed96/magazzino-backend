"""Test unitari della configurazione (nessun DB coinvolto)."""

from app.core.config import Settings


def test_database_url_dall_ambiente(monkeypatch) -> None:
    """DATABASE_URL dall'ambiente ha precedenza sul default."""
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://u:p@db.example:5432/magazzino"
    )
    settings = Settings(_env_file=None)
    assert settings.database_url == "postgresql+psycopg://u:p@db.example:5432/magazzino"


def test_database_url_ha_default() -> None:
    """Senza variabile d'ambiente resta un default utilizzabile in sviluppo."""
    settings = Settings(_env_file=None)
    assert settings.database_url.startswith("postgresql+psycopg://")
