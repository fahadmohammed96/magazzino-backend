"""Schemi Pydantic al confine dell'API.

Gli schemi validano l'input in ingresso e definiscono la forma delle risposte,
che alimenta anche il contratto OpenAPI consumato dal frontend. Il modulo
raccoglie gli schemi per area (autenticazione, clienti, ...).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.customer import Customer
from app.models.user import Role


class LoginRequest(BaseModel):
    """Corpo della richiesta di login."""

    username: str = Field(min_length=1, max_length=150)
    # Limite allineato a bcrypt, che considera solo i primi 72 byte: accettare
    # di più sarebbe fuorviante (i byte in eccesso non contribuiscono).
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    """Rappresentazione pubblica di un utente (nessun dato sensibile)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role


class LoginResponse(BaseModel):
    """Risposta al login: token di accesso Bearer e utente autenticato."""

    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Anagrafica clienti ---


def _blank_to_none(value: Any) -> Any:
    """Normalizza le stringhe: trim e conversione di "" (o soli spazi) in None."""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


class Contatti(BaseModel):
    """Contatti di un cliente; entrambi i campi sono opzionali."""

    email: str | None = Field(default=None, max_length=255)
    telefono: str | None = Field(default=None, max_length=50)

    _normalize = field_validator("email", "telefono", mode="before")(_blank_to_none)


class CustomerBase(BaseModel):
    """Campi comuni in scrittura (creazione e aggiornamento) di un cliente.

    Solo ``ragione_sociale`` è obbligatoria. Gli altri campi sono opzionali; le
    stringhe vuote vengono normalizzate a ``None`` così l'assenza di un dato è
    rappresentata in modo uniforme.
    """

    ragione_sociale: str = Field(min_length=1, max_length=255)
    piva: str | None = Field(default=None, max_length=32)
    codice_fiscale: str | None = Field(default=None, max_length=32)
    indirizzo_spedizione: str | None = Field(default=None, max_length=500)
    contatti: Contatti = Field(default_factory=Contatti)

    @field_validator("ragione_sociale", mode="before")
    @classmethod
    def _strip_ragione_sociale(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    _normalize_opzionali = field_validator(
        "piva", "codice_fiscale", "indirizzo_spedizione", mode="before"
    )(_blank_to_none)


class CustomerCreate(CustomerBase):
    """Corpo della richiesta di creazione cliente (``POST /v1/customers``)."""


class CustomerUpdate(CustomerBase):
    """Corpo della richiesta di aggiornamento cliente (``PUT /v1/customers/{id}``).

    L'aggiornamento sostituisce l'intera anagrafica: i campi non forniti tornano
    al loro default (``None``), coerentemente con la semantica di ``PUT``.
    """


class CustomerOut(BaseModel):
    """Rappresentazione pubblica di un cliente, con i contatti annidati."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ragione_sociale: str
    piva: str | None
    codice_fiscale: str | None
    indirizzo_spedizione: str | None
    contatti: Contatti
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, customer: Customer) -> "CustomerOut":
        """Costruisce lo schema dal modello ORM, annidando i contatti."""
        return cls(
            id=customer.id,
            ragione_sociale=customer.ragione_sociale,
            piva=customer.piva,
            codice_fiscale=customer.codice_fiscale,
            indirizzo_spedizione=customer.indirizzo_spedizione,
            contatti=Contatti(
                email=customer.contatto_email,
                telefono=customer.contatto_telefono,
            ),
            created_at=customer.created_at,
            updated_at=customer.updated_at,
        )
