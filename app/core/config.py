"""Configurazione del servizio, letta esclusivamente da variabili d'ambiente.

I valori reali non vivono mai nel codice: le variabili disponibili e la loro
descrizione sono in `.env.example`. In locale possono essere caricate da un
file `.env` (non versionato); in produzione arrivano dall'ambiente.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Impostazioni del servizio.

    Attributi:
        database_url: DSN SQLAlchemy verso PostgreSQL, driver psycopg 3
            (schema ``postgresql+psycopg://``). Obbligatorio: va fornito via
            variabile d'ambiente ``DATABASE_URL`` (o file ``.env`` locale).
            Nessun valore di default nel codice — le credenziali non vivono
            mai nel sorgente.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        description=(
            "DSN SQLAlchemy verso PostgreSQL (driver psycopg 3), es. "
            "postgresql+psycopg://utente:password@host:5432/database"
        ),
    )


@lru_cache
def get_settings() -> Settings:
    """Restituisce le impostazioni, istanziate una sola volta (cache di processo)."""
    return Settings()
