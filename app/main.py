"""Punto di ingresso del servizio.

Le convenzioni operative del repository sono in AGENTS.md.
"""

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.errors import register_exception_handlers
from app.api.health import router as health_router

app = FastAPI(
    title="magazzino API",
    description="[PLACEHOLDER] Descrizione del servizio.",
)

# Formato d'errore unico del progetto per ogni risposta di errore.
register_exception_handlers(app)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(customers_router)
