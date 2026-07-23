"""Test d'integrazione della migrazione ``0002_users`` (Postgres reale).

Verifica che ``upgrade head`` crei la tabella ``users`` e il tipo enum
``user_role``, e che ``downgrade`` alla revisione baseline li rimuova
(migrazione reversibile).
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

REPO_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config(database_url: str) -> Config:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _enum_esiste(engine, nome: str) -> bool:
    with engine.connect() as connection:
        return connection.dialect.has_type(connection, nome)


def test_upgrade_crea_users_downgrade_lo_rimuove(postgres_url: str) -> None:
    config = _alembic_config(postgres_url)
    engine = create_engine(postgres_url, future=True)
    try:
        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert "users" in inspector.get_table_names()
        colonne = {c["name"] for c in inspector.get_columns("users")}
        assert {"id", "username", "password_hash", "role", "created_at"} <= colonne
        indici = {i["name"] for i in inspector.get_indexes("users")}
        assert "ix_users_username" in indici
        assert _enum_esiste(engine, "user_role")

        command.downgrade(config, "0001_baseline")
        inspector = inspect(engine)
        assert "users" not in inspector.get_table_names()
        assert not _enum_esiste(engine, "user_role")
    finally:
        # Riporta il DB a base per non lasciare stato ai test successivi.
        command.downgrade(config, "base")
        engine.dispose()
