"""Ambiente di esecuzione delle migrazioni Alembic.

La URL del database è risolta con questa precedenza:

1. l'opzione ``sqlalchemy.url`` impostata a livello di programma sul
   :class:`~alembic.config.Config` (usata dai test d'integrazione per puntare
   al Postgres usa-e-getta di testcontainers);
2. altrimenti ``DATABASE_URL`` dall'ambiente, via ``app.core.config``.

Il bersaglio dell'autogenerate è ``Base.metadata``: i moduli dei modelli di
dominio andranno importati qui sotto man mano che verranno creati, così che
Alembic li veda.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  (registra i modelli su Base.metadata)
from app.core.config import get_settings
from app.db.base import Base

# Oggetto di configurazione Alembic, dà accesso ai valori di alembic.ini.
config = context.config

# Logging da file di configurazione, se presente.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata bersaglio per l'autogenerate delle migrazioni.
# NB: importare qui i moduli dei modelli quando esisteranno, es.
#   import app.models.ordine  # noqa: F401
target_metadata = Base.metadata


def _database_url() -> str:
    """URL del DB: opzione esplicita del config, altrimenti DATABASE_URL."""
    configured = config.get_main_option("sqlalchemy.url")
    if configured:
        return configured
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Esegue le migrazioni in modalità 'offline' (solo generazione SQL)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Esegue le migrazioni con una connessione reale al database."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
