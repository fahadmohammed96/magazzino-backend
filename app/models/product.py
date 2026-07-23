"""Modello del prodotto a catalogo con la relativa giacenza.

Prima entità di dominio del gestionale: il prodotto e la sua giacenza. È il
presupposto degli ordini, che in una fetta successiva scaleranno le scorte;
qui la giacenza si imposta e aggiorna solo via CRUD e import CSV.

La colonna ``price`` usa ``Numeric(12, 2)`` (mappata su :class:`~decimal.Decimal`)
per rappresentare un importo monetario senza gli errori di arrotondamento del
floating point. ``low_stock`` non è una colonna: è calcolato al volo dalla
proprietà :pyattr:`Product.low_stock` (``stock_quantity <= low_stock_threshold``).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    """Prodotto a catalogo con la sua giacenza.

    Attributi:
        id: identificativo numerico, chiave primaria.
        sku: codice articolo univoco, usato come chiave naturale nell'import.
        name: nome del prodotto.
        description: descrizione opzionale.
        price: prezzo unitario, importo decimale a 2 cifre (mai negativo).
        stock_quantity: quantità a magazzino (mai negativa).
        low_stock_threshold: soglia sotto la quale il prodotto è sotto-scorta.
        created_at: istante di creazione, valorizzato dal database.
        updated_at: istante dell'ultimo aggiornamento, gestito dall'ORM.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
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

    @property
    def low_stock(self) -> bool:
        """Vero se la giacenza è pari o inferiore alla soglia di sotto-scorta.

        Campo calcolato, non persistito: lo espone la risposta API e lo ricalcola
        ad ogni lettura da ``stock_quantity`` e ``low_stock_threshold``.
        """
        return self.stock_quantity <= self.low_stock_threshold

    def __repr__(self) -> str:  # pragma: no cover - solo diagnostica
        return f"Product(id={self.id!r}, sku={self.sku!r}, name={self.name!r})"
