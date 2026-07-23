"""Logica di dominio dell'anagrafica clienti: lettura e scrittura dei clienti.

Come ``app.services.auth``, il modulo lavora su una
:class:`~sqlalchemy.orm.Session` ricevuta dal chiamante e non conosce l'HTTP né
gli schemi Pydantic: riceve valori primitivi e ritorna modelli ORM. Il commit
resta responsabilità del chiamante (coerente con ``app.db.session.get_session``),
così la scrittura è esplicita.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer


def list_customers(session: Session, query: str | None = None) -> list[Customer]:
    """Ritorna i clienti, ordinati per ragione sociale.

    Se ``query`` è valorizzata, filtra per ragione sociale con ricerca
    case-insensitive per sottostringa (``ILIKE``). I caratteri jolly di
    ``LIKE`` presenti in ``query`` vengono trattati come letterali.
    """
    stmt = select(Customer).order_by(Customer.ragione_sociale, Customer.id)
    if query:
        pattern = f"%{_escape_like(query)}%"
        stmt = stmt.where(Customer.ragione_sociale.ilike(pattern, escape="\\"))
    return list(session.execute(stmt).scalars().all())


def get_customer(session: Session, customer_id: int) -> Customer | None:
    """Ritorna il cliente con l'``id`` indicato, o ``None`` se assente."""
    return session.get(Customer, customer_id)


def create_customer(
    session: Session,
    *,
    ragione_sociale: str,
    piva: str | None = None,
    codice_fiscale: str | None = None,
    indirizzo_spedizione: str | None = None,
    contatto_email: str | None = None,
    contatto_telefono: str | None = None,
) -> Customer:
    """Crea un cliente e lo aggiunge alla sessione.

    Esegue il ``flush`` per valorizzare la chiave primaria e i timestamp, ma
    **non** il commit: la transazione è chiusa dal chiamante.
    """
    customer = Customer(
        ragione_sociale=ragione_sociale,
        piva=piva,
        codice_fiscale=codice_fiscale,
        indirizzo_spedizione=indirizzo_spedizione,
        contatto_email=contatto_email,
        contatto_telefono=contatto_telefono,
    )
    session.add(customer)
    session.flush()
    return customer


def update_customer(
    session: Session,
    customer: Customer,
    *,
    ragione_sociale: str,
    piva: str | None = None,
    codice_fiscale: str | None = None,
    indirizzo_spedizione: str | None = None,
    contatto_email: str | None = None,
    contatto_telefono: str | None = None,
) -> Customer:
    """Sostituisce i campi del cliente con quelli forniti (semantica ``PUT``).

    Esegue il ``flush`` (che aggiorna ``updated_at`` via ``onupdate``), non il
    commit: la transazione è chiusa dal chiamante.
    """
    customer.ragione_sociale = ragione_sociale
    customer.piva = piva
    customer.codice_fiscale = codice_fiscale
    customer.indirizzo_spedizione = indirizzo_spedizione
    customer.contatto_email = contatto_email
    customer.contatto_telefono = contatto_telefono
    session.flush()
    return customer


def delete_customer(session: Session, customer: Customer) -> None:
    """Elimina il cliente dalla sessione (commit a carico del chiamante)."""
    session.delete(customer)
    session.flush()


def _escape_like(value: str) -> str:
    """Neutralizza i metacaratteri LIKE (``\\``, ``%``, ``_``) in ``value``."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
