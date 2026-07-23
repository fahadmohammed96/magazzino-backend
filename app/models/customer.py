"""Modello dell'anagrafica clienti.

Un cliente è l'anagrafica a cui verranno associati gli ordini (dominio
successivo). I contatti (email, telefono) sono modellati come colonne piatte
``contatto_email``/``contatto_telefono``: all'API vengono ricomposti
nell'oggetto annidato ``contatti`` previsto dal contratto (vedi
``app.api.schemas``).

Solo ``ragione_sociale`` è obbligatoria; ``piva`` e ``codice_fiscale`` sono
opzionali (validazione soft: almeno uno consigliato, ma non imposto, come da
issue MYL-18).
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Customer(Base):
    """Cliente dell'anagrafica.

    Attributi:
        id: identificativo numerico, chiave primaria.
        ragione_sociale: denominazione del cliente; unico campo obbligatorio,
            indicizzato per la ricerca ``?q=``.
        piva: partita IVA, opzionale.
        codice_fiscale: codice fiscale, opzionale.
        indirizzo_spedizione: indirizzo di spedizione, opzionale.
        contatto_email: email di contatto, opzionale.
        contatto_telefono: telefono di contatto, opzionale.
        created_at: istante di creazione, valorizzato dal database.
        updated_at: istante dell'ultimo aggiornamento; valorizzato alla
            creazione e riaggiornato a ogni modifica via ORM.
    """

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    ragione_sociale: Mapped[str] = mapped_column(
        String(255), index=True, nullable=False
    )
    piva: Mapped[str | None] = mapped_column(String(32), nullable=True)
    codice_fiscale: Mapped[str | None] = mapped_column(String(32), nullable=True)
    indirizzo_spedizione: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contatto_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contatto_telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - solo diagnostica
        return f"Customer(id={self.id!r}, ragione_sociale={self.ragione_sociale!r})"
