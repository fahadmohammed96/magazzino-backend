"""Endpoint dell'anagrafica clienti (prefisso ``/v1``).

Contratto:

- ``GET /v1/customers`` — lista; ``?q=`` filtra per ragione sociale.
- ``GET /v1/customers/{id}`` — dettaglio (404 se inesistente).
- ``POST /v1/customers`` — crea → 201.
- ``PUT /v1/customers/{id}`` — aggiorna (404 se inesistente).
- ``DELETE /v1/customers/{id}`` — elimina → 204.

Autorizzazione: tutti gli endpoint richiedono un token valido e almeno il ruolo
``operator`` (default MYL-18: lettura e scrittura consentite ad admin e
operator, così l'operatore può creare/aggiornare un cliente inserendo un
ordine). Senza token → 401; il ruolo minimo è imposto a livello di router.
Gli errori seguono il formato unico del progetto (vedi ``app.api.errors``).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, require_role
from app.api.errors import APIError
from app.api.schemas import CustomerBase, CustomerCreate, CustomerOut, CustomerUpdate
from app.models.customer import Customer
from app.models.user import Role
from app.services import customer as customer_service

router = APIRouter(
    prefix="/v1/customers",
    tags=["customers"],
    dependencies=[Depends(require_role(Role.operator))],
)


def _write_fields(data: CustomerBase) -> dict[str, str | None]:
    """Appiattisce lo schema di scrittura nei campi del modello ORM."""
    return {
        "ragione_sociale": data.ragione_sociale,
        "piva": data.piva,
        "codice_fiscale": data.codice_fiscale,
        "indirizzo_spedizione": data.indirizzo_spedizione,
        "contatto_email": data.contatti.email,
        "contatto_telefono": data.contatti.telefono,
    }


def _get_or_404(session: SessionDep, customer_id: int) -> Customer:
    customer = customer_service.get_customer(session, customer_id)
    if customer is None:
        raise APIError(
            status_code=404,
            code="not_found",
            message="Cliente non trovato.",
        )
    return customer


@router.get("", response_model=list[CustomerOut])
def list_customers(
    session: SessionDep,
    q: Annotated[
        str | None,
        Query(description="Filtro per ragione sociale (sottostringa)."),
    ] = None,
) -> list[CustomerOut]:
    """Elenca i clienti; con ``?q=`` filtra per ragione sociale."""
    customers = customer_service.list_customers(session, query=q)
    return [CustomerOut.from_model(c) for c in customers]


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(session: SessionDep, customer_id: int) -> CustomerOut:
    """Ritorna il dettaglio di un cliente (404 se inesistente)."""
    return CustomerOut.from_model(_get_or_404(session, customer_id))


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerCreate, session: SessionDep) -> CustomerOut:
    """Crea un nuovo cliente e lo ritorna con id e timestamp valorizzati."""
    customer = customer_service.create_customer(session, **_write_fields(body))
    session.commit()
    return CustomerOut.from_model(customer)


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int, body: CustomerUpdate, session: SessionDep
) -> CustomerOut:
    """Aggiorna un cliente esistente (404 se inesistente)."""
    customer = _get_or_404(session, customer_id)
    customer_service.update_customer(session, customer, **_write_fields(body))
    session.commit()
    return CustomerOut.from_model(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(session: SessionDep, customer_id: int) -> None:
    """Elimina un cliente (404 se inesistente)."""
    customer = _get_or_404(session, customer_id)
    customer_service.delete_customer(session, customer)
    session.commit()
