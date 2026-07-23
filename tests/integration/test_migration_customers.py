"""Test d'integrazione della migrazione ``0003_customers`` (Postgres reale).

Verifica che ``upgrade head`` crei la tabella ``customers`` con le colonne e
l'indice attesi, e che ``downgrade`` alla revisione ``0002_users`` la rimuova
lasciando intatta la tabella ``users`` (migrazione reversibile e non
distruttiva sulle revisioni precedenti).
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


def test_upgrade_crea_customers_downgrade_lo_rimuove(postgres_url: str) -> None:
    config = _alembic_config(postgres_url)
    engine = create_engine(postgres_url, future=True)
    try:
        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert "customers" in inspector.get_table_names()
        colonne = {c["name"] for c in inspector.get_columns("customers")}
        assert {
            "id",
            "ragione_sociale",
            "piva",
            "codice_fiscale",
            "indirizzo_spedizione",
            "contatto_email",
            "contatto_telefono",
            "created_at",
            "updated_at",
        } <= colonne
        indici = {i["name"] for i in inspector.get_indexes("customers")}
        assert "ix_customers_ragione_sociale" in indici

        command.downgrade(config, "0002_users")
        inspector = inspect(engine)
        assert "customers" not in inspector.get_table_names()
        # La revisione precedente resta intatta.
        assert "users" in inspector.get_table_names()
    finally:
        # Riporta il DB a base per non lasciare stato ai test successivi.
        command.downgrade(config, "base")
        engine.dispose()
