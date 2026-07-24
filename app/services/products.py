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
from sqlalchemy.exc import IntegrityError
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

# Colonne testuali libere: su queste si applica la difesa dalla CSV injection
# (i campi numerici non possono iniziare con un carattere di formula).
_TEXT_COLUMNS: frozenset[str] = frozenset({"sku", "name", "description"})

# Caratteri che, in testa a una cella, un foglio di calcolo (Excel, Sheets)
# interpreta come inizio di formula. Un valore che li usa viene "disinnescato"
# in export anteponendo un apice, e ripulito in import: la coppia è simmetrica,
# quindi il round-trip export→import resta senza perdite.
_FORMULA_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")


def _defuse_csv(value: str) -> str:
    """Antepone un apice a un valore che inizierebbe una formula in un foglio."""
    if value and value[0] in _FORMULA_PREFIXES:
        return "'" + value
    return value


def _refuse_csv(value: str) -> str:
    """Inverso di :func:`_defuse_csv`: rimuove l'apice difensivo se presente.

    Toglie un solo apice iniziale, e solo quando precede un carattere di
    formula: così i valori prodotti dall'export tornano identici all'originale,
    senza intaccare un apice legittimo seguito da testo normale.
    """
    if len(value) >= 2 and value[0] == "'" and value[1] in _FORMULA_PREFIXES:
        return value[1:]
    return value


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

    Solleva :class:`SkuConflictError` se lo ``sku`` è già usato. L'unicità è
    affidata all'indice ``ix_products_sku``: il ``flush`` avviene dentro un
    SAVEPOINT (``begin_nested``) così che una violazione (anche sotto
    concorrenza, quando due transazioni superano un controllo applicativo e
    collidono al commit) si traduca in :class:`SkuConflictError` — quindi in un
    409 — senza inquinare la transazione esterna né perdere le altre scritture
    (rilevante durante l'import, dove più righe condividono la stessa
    transazione).
    """
    product = Product(**data.model_dump())
    try:
        with session.begin_nested():
            session.add(product)
            session.flush()
    except IntegrityError as exc:
        raise SkuConflictError(data.sku) from exc
    return product


def update_product(session: Session, product: Product, data: ProductUpdate) -> Product:
    """Aggiorna tutti i campi di ``product`` dai dati validati; ``flush``.

    Solleva :class:`SkuConflictError` se il nuovo ``sku`` appartiene a un altro
    prodotto (violazione dell'indice univoco, intercettata nel SAVEPOINT come in
    :func:`create_product`). Non esegue il commit.
    """
    for field, value in data.model_dump().items():
        setattr(product, field, value)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as exc:
        raise SkuConflictError(data.sku) from exc
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
        pulito = grezzo.strip() if isinstance(grezzo, str) else grezzo
        # Rimuove l'eventuale apice difensivo dai campi testuali (inverso
        # dell'export), preservando il round-trip senza perdite.
        if colonna in _TEXT_COLUMNS and isinstance(pulito, str):
            pulito = _refuse_csv(pulito)
        valori[colonna] = pulito
    # description vuota o assente → None (campo opzionale).
    if not valori.get("description"):
        valori["description"] = None
    return ProductCreate.model_validate(valori)


def import_products(session: Session, text: str) -> ImportResult:
    """Importa prodotti da CSV con upsert per ``sku``; ``flush`` ma non ``commit``.

    Le righe valide sono create o aggiornate (upsert sulla chiave naturale
    ``sku``); quelle invalide — o quelle che collidono su ``sku`` per una
    scrittura concorrente — sono raccolte in ``errors`` senza interrompere
    l'import (ogni riga scrive nel proprio SAVEPOINT, così un errore non annulla
    le righe già applicate). La numerazione delle righe negli errori parte da 2
    (l'intestazione è la riga 1). Un file privo delle colonne richieste produce
    un unico errore sulla riga 1. Il commit resta al chiamante.
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
        try:
            if esistente is None:
                create_product(session, data)
                created += 1
            else:
                update_product(
                    session, esistente, ProductUpdate.model_validate(data.model_dump())
                )
                updated += 1
        except SkuConflictError:
            msg = f"SKU in conflitto con una scrittura concorrente: {data.sku}"
            errors.append(ImportRowError(row=numero, message=msg))

    return ImportResult(created=created, updated=updated, errors=errors)


def products_to_csv(products: Sequence[Product]) -> str:
    """Serializza i prodotti in un CSV con le colonne di :data:`CSV_COLUMNS`.

    Il file prodotto è re-importabile: contiene solo i campi scrivibili, con il
    prezzo come stringa decimale a 2 cifre e la ``description`` assente resa come
    cella vuota. I campi testuali sono disinnescati contro la CSV injection
    (:func:`_defuse_csv`); l'import ne rimuove l'apice, quindi il round-trip
    resta senza perdite.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for product in products:
        writer.writerow(
            [
                _defuse_csv(product.sku),
                _defuse_csv(product.name),
                _defuse_csv(product.description or ""),
                f"{product.price:.2f}",
                product.stock_quantity,
                product.low_stock_threshold,
            ]
        )
    return buffer.getvalue()
