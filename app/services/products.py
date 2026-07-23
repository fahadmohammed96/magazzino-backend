"""Logica di dominio del catalogo prodotti: CRUD, giacenza e import/export CSV.

Il modulo lavora su una :class:`~sqlalchemy.orm.Session` ricevuta dal chiamante
e non conosce l'HTTP: gli endpoint lo usano tramite la dependency
``get_session``. Coerente con il resto del progetto, le funzioni eseguono
``flush`` per valorizzare le chiavi e rendere visibili le scritture nella stessa
transazione, ma **non** il commit: quello resta responsabilità esplicita del
chiamante (vedi ``app.db.session.get_session``).

Le funzioni di (de)serializzazione CSV — :func:`parse_csv_row`,
:func:`products_to_csv` — sono pure (nessun DB) e quindi testabili a unità.
"""

import csv
import io
from collections.abc import Sequence

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import ImportResult, ImportRowError, ProductCreate, ProductUpdate
from app.models.product import Product

# Colonne del CSV, nell'ordine usato sia dall'export sia atteso dall'import.
# L'export produce esattamente queste colonne, così il file è re-importabile
# (round-trip). Sono i campi scrivibili del prodotto: id, timestamp e
# ``low_stock`` (calcolato) restano fuori.
CSV_COLUMNS: tuple[str, ...] = (
    "sku",
    "name",
    "description",
    "price",
    "stock_quantity",
    "low_stock_threshold",
)


class SkuConflictError(Exception):
    """Sollevata quando lo ``sku`` è già usato da un altro prodotto.

    Il chiamante (endpoint) la traduce nel 409 del formato d'errore del
    progetto. Vive nel dominio perché l'unicità dello ``sku`` è una regola di
    dominio, non un dettaglio di trasporto.
    """

    def __init__(self, sku: str) -> None:
        self.sku = sku
        super().__init__(f"SKU già esistente: {sku!r}")


def list_products(
    session: Session, *, low_stock_only: bool = False
) -> Sequence[Product]:
    """Ritorna i prodotti ordinati per ``id``.

    Se ``low_stock_only`` è vero, filtra i soli prodotti sotto-scorta
    (``stock_quantity <= low_stock_threshold``), applicando il confronto in SQL.
    """
    stmt = select(Product).order_by(Product.id)
    if low_stock_only:
        stmt = stmt.where(Product.stock_quantity <= Product.low_stock_threshold)
    return session.execute(stmt).scalars().all()


def get_product(session: Session, product_id: int) -> Product | None:
    """Ritorna il prodotto con l'``id`` indicato, o ``None`` se assente."""
    return session.get(Product, product_id)


def get_product_by_sku(session: Session, sku: str) -> Product | None:
    """Ritorna il prodotto con lo ``sku`` indicato, o ``None`` se assente."""
    return session.execute(
        select(Product).where(Product.sku == sku)
    ).scalar_one_or_none()


def create_product(session: Session, data: ProductCreate) -> Product:
    """Crea un prodotto dai dati validati; ``flush`` ma non ``commit``.

    Solleva :class:`SkuConflictError` se lo ``sku`` è già presente.
    """
    if get_product_by_sku(session, data.sku) is not None:
        raise SkuConflictError(data.sku)
    product = Product(**data.model_dump())
    session.add(product)
    session.flush()
    return product


def update_product(session: Session, product: Product, data: ProductUpdate) -> Product:
    """Aggiorna tutti i campi di ``product`` dai dati validati; ``flush``.

    Solleva :class:`SkuConflictError` se il nuovo ``sku`` appartiene a un altro
    prodotto. Non esegue il commit.
    """
    if data.sku != product.sku:
        existing = get_product_by_sku(session, data.sku)
        if existing is not None and existing.id != product.id:
            raise SkuConflictError(data.sku)
    for field, value in data.model_dump().items():
        setattr(product, field, value)
    session.flush()
    return product


def delete_product(session: Session, product: Product) -> None:
    """Elimina il prodotto dalla sessione; ``flush`` ma non ``commit``."""
    session.delete(product)
    session.flush()


def _format_validation_error(exc: ValidationError) -> str:
    """Rende un :class:`ValidationError` in un messaggio conciso per riga.

    Un messaggio per campo problematico, senza dettagli interni: adatto a
    finire nel riepilogo ``errors`` restituito al client.
    """
    parti = []
    for errore in exc.errors():
        campo = errore["loc"][-1] if errore["loc"] else "corpo"
        parti.append(f"{campo}: {errore['msg']}")
    return "; ".join(parti)


def parse_csv_row(raw: dict[str, str | None]) -> ProductCreate:
    """Valida una riga CSV (dizionario colonna→valore) in :class:`ProductCreate`.

    Normalizza gli spazi e tratta una ``description`` vuota come assente. Solleva
    :class:`~pydantic.ValidationError` se un campo obbligatorio manca o un valore
    non rispetta i vincoli (prezzo/quantità non numerici o negativi).
    """
    valori: dict[str, str | None] = {}
    for colonna in CSV_COLUMNS:
        grezzo = raw.get(colonna)
        valori[colonna] = grezzo.strip() if isinstance(grezzo, str) else grezzo
    # description vuota o assente → None (campo opzionale).
    if not valori.get("description"):
        valori["description"] = None
    return ProductCreate.model_validate(valori)


def import_products(session: Session, text: str) -> ImportResult:
    """Importa prodotti da CSV con upsert per ``sku``; ``flush`` ma non ``commit``.

    Le righe valide sono create o aggiornate (upsert sulla chiave naturale
    ``sku``); quelle invalide sono raccolte in ``errors`` senza interrompere
    l'import. La numerazione delle righe negli errori parte da 2 (l'intestazione
    è la riga 1). Un file privo delle colonne richieste produce un unico errore
    sulla riga 1. Il commit resta al chiamante.
    """
    reader = csv.DictReader(io.StringIO(text))
    intestazione = reader.fieldnames or []
    mancanti = [c for c in CSV_COLUMNS if c not in intestazione]
    if mancanti:
        messaggio = f"Colonne mancanti nell'intestazione: {', '.join(mancanti)}."
        return ImportResult(
            created=0,
            updated=0,
            errors=[ImportRowError(row=1, message=messaggio)],
        )

    created = 0
    updated = 0
    errors: list[ImportRowError] = []
    # enumerate da 2: la riga 1 del file è l'intestazione.
    for numero, raw in enumerate(reader, start=2):
        try:
            data = parse_csv_row(raw)
        except ValidationError as exc:
            errors.append(
                ImportRowError(row=numero, message=_format_validation_error(exc))
            )
            continue

        esistente = get_product_by_sku(session, data.sku)
        if esistente is None:
            create_product(session, data)
            created += 1
        else:
            update_product(
                session, esistente, ProductUpdate.model_validate(data.model_dump())
            )
            updated += 1

    return ImportResult(created=created, updated=updated, errors=errors)


def products_to_csv(products: Sequence[Product]) -> str:
    """Serializza i prodotti in un CSV con le colonne di :data:`CSV_COLUMNS`.

    Il file prodotto è re-importabile: contiene solo i campi scrivibili, con il
    prezzo come stringa decimale a 2 cifre e la ``description`` assente resa come
    cella vuota.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for product in products:
        writer.writerow(
            [
                product.sku,
                product.name,
                product.description or "",
                f"{product.price:.2f}",
                product.stock_quantity,
                product.low_stock_threshold,
            ]
        )
    return buffer.getvalue()
