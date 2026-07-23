"""Configurazione condivisa dei test.

Imposta valori di default per le variabili d'ambiente obbligatorie, così che
``get_settings()`` sia istanziabile durante i test senza un ambiente reale. I
valori sono fittizi: i test che toccano davvero il database usano il DSN del
container testcontainers, e ``monkeypatch`` può sovrascrivere questi default
dove serve. Nessun segreto reale.
"""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test"
)
os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-not-for-production")
