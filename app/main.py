"""Punto di ingresso del servizio.

Le convenzioni operative del repository sono in AGENTS.md.
"""

from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(
    title="magazzino API",
    description="[PLACEHOLDER] Descrizione del servizio.",
)

app.include_router(health_router)
