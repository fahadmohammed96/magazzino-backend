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
        auth_secret_key: chiave segreta per firmare i token di accesso (JWT,
            HS256). Obbligatoria e senza default: un default nel codice
            renderebbe i token falsificabili. Va fornita via
            ``AUTH_SECRET_KEY`` e deve essere lunga almeno 32 caratteri
            (RFC 7518).
        access_token_expire_minutes: durata di validità del token di accesso,
            in minuti. Non è un segreto: ha un default ragionevole.
        seed_admin_username: username dell'utente admin iniziale, usato solo
            dallo script di seed (``python -m app.db.seed``). Opzionale: il
            seed viene eseguito solo se username e password sono entrambi
            valorizzati.
        seed_admin_password: password in chiaro dell'admin iniziale, usata solo
            dallo script di seed per calcolarne l'hash. Segreto: mai un valore
            nel codice o nella configurazione versionata.
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

    auth_secret_key: str = Field(
        ...,
        min_length=32,
        description=(
            "Chiave segreta per firmare i token di accesso (JWT HS256). "
            "Obbligatoria, senza default: fornirla via AUTH_SECRET_KEY. "
            "Minimo 32 caratteri (RFC 7518): una chiave debole è rifiutata "
            "all'avvio, non solo sconsigliata."
        ),
    )

    access_token_expire_minutes: int = Field(
        default=60,
        ge=1,
        description="Durata di validità del token di accesso, in minuti.",
    )

    seed_admin_username: str | None = Field(
        default=None,
        description="Username dell'admin iniziale, usato solo dallo script di seed.",
    )

    seed_admin_password: str | None = Field(
        default=None,
        description="Password dell'admin iniziale, usata solo dallo script di seed.",
    )


@lru_cache
def get_settings() -> Settings:
    """Restituisce le impostazioni, istanziate una sola volta (cache di processo)."""
    return Settings()
