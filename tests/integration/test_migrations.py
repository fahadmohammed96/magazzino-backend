"""Test d'integrazione delle migrazioni Alembic contro un Postgres reale.

Verifica che, su un database pulito, la catena di migrazioni sia percorribile
in entrambi i sensi: ``upgrade head`` la applica, ``downgrade base`` la annulla.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

# Radice del repo: due livelli sopra questo file (tests/integration/).
REPO_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config(database_url: str) -> Config:
    """Config Alembic puntato all'ini del repo e al database indicato."""
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _current_revision(engine) -> str | None:
    """Revisione attualmente applicata al database, o None se a base."""
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def test_upgrade_head_e_downgrade_base(postgres_url: str) -> None:
    """upgrade porta alla testa; downgrade base riporta il DB a nessuna revisione."""
    config = _alembic_config(postgres_url)
    engine = create_engine(postgres_url, future=True)
    try:
        command.upgrade(config, "head")
        assert _current_revision(engine) == "0001_baseline"

        command.downgrade(config, "base")
        assert _current_revision(engine) is None
    finally:
        engine.dispose()
