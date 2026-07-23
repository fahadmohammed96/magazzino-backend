"""Test d'integrazione del layer dati contro un Postgres reale (testcontainers)."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


def test_apertura_sessione_ed_esecuzione_query(postgres_url: str) -> None:
    """Una sessione si apre contro il Postgres del container ed esegue una query."""
    engine = create_engine(postgres_url, future=True)
    try:
        with Session(engine) as session:
            risultato = session.execute(text("SELECT 1")).scalar_one()
            assert risultato == 1
    finally:
        engine.dispose()
