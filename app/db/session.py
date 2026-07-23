"""Engine e sessioni SQLAlchemy.

Engine e ``sessionmaker`` sono creati in modo pigro (lazy) e memorizzati con
``lru_cache``: importare questo modulo non apre alcuna connessione, così
l'avvio dell'app e i test che non usano il DB restano isolati dal database.
La connessione reale avviene solo quando una sessione viene effettivamente
usata.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Restituisce l'engine SQLAlchemy, creato una sola volta per processo.

    ``pool_pre_ping`` verifica la connessione prima dell'uso, evitando errori
    su connessioni chiuse lato server (timeout, riavvii del DB).
    """
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def _get_sessionmaker() -> sessionmaker[Session]:
    """Factory di sessioni legata all'engine del processo."""
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def get_session() -> Iterator[Session]:
    """Dependency FastAPI: fornisce una sessione e ne garantisce la chiusura.

    In caso di eccezione la transazione viene annullata (``rollback``); il
    commit resta a carico del chiamante, così la responsabilità della scrittura
    è esplicita.
    """
    session = _get_sessionmaker()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
