"""Fixture per i test d'integrazione: PostgreSQL usa-e-getta via testcontainers.

Il container è avviato una sola volta per sessione di test. Se Docker non è
disponibile nell'ambiente (es. sviluppo locale senza daemon), i test che
dipendono dal container vengono saltati con un messaggio esplicito: in CI, dove
Docker è presente, girano davvero.
"""

from collections.abc import Iterator

import pytest

POSTGRES_IMAGE = "postgres:16-alpine"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """URL di connessione a un Postgres effimero (driver psycopg 3).

    Salta l'intero gruppo di test d'integrazione se il container non può essere
    avviato (Docker assente o non raggiungibile).
    """
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError as exc:  # pragma: no cover - dipendenza dev mancante
        pytest.skip(f"testcontainers non installato: {exc}")

    try:
        container = PostgresContainer(POSTGRES_IMAGE, driver="psycopg")
        container.start()
    except Exception as exc:  # Docker non disponibile o non raggiungibile
        pytest.skip(f"Docker non disponibile per i test d'integrazione: {exc}")

    try:
        yield container.get_connection_url()
    finally:
        container.stop()
