"""Schemi Pydantic al confine dell'API.

Gli schemi validano l'input in ingresso e definiscono la forma delle risposte,
che alimenta anche il contratto OpenAPI consumato dal frontend. Sono raccolti
qui, un modulo unico, per area: autenticazione e catalogo prodotti.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

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


# Prezzo: importo decimale non negativo, al massimo 12 cifre di cui 2 decimali.
# Il vincolo è applicato al confine (Pydantic) e ribadito a DB (Numeric(12, 2)).
PriceField = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class ProductBase(BaseModel):
    """Campi comuni a creazione e aggiornamento di un prodotto.

    Validazione al confine: prezzo e quantità non negativi, ``sku`` e ``name``
    non vuoti. Gli spazi in testa e coda di ``sku`` e ``name`` sono rimossi.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    price: PriceField
    stock_quantity: int = Field(ge=0)
    low_stock_threshold: int = Field(ge=0)


class ProductCreate(ProductBase):
    """Corpo per creare un prodotto (``POST``) o una riga d'import CSV."""


class ProductUpdate(ProductBase):
    """Corpo per aggiornare un prodotto (``PUT``): sostituisce tutti i campi."""


class ProductOut(BaseModel):
    """Rappresentazione di un prodotto in risposta, con ``low_stock`` calcolato.

    ``price`` è serializzato come stringa decimale (es. ``"12.50"``) per non
    perdere precisione nel JSON; ``low_stock`` è ``stock_quantity <=
    low_stock_threshold``, calcolato dal modello e non persistito.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str | None
    price: Decimal
    stock_quantity: int
    low_stock_threshold: int
    low_stock: bool
    created_at: datetime
    updated_at: datetime


class ImportRowError(BaseModel):
    """Errore su una singola riga dell'import CSV."""

    row: int = Field(description="Numero di riga nel file CSV (l'intestazione è 1).")
    message: str


class ImportResult(BaseModel):
    """Riepilogo di un import CSV: conteggi e righe rifiutate.

    Le righe valide vengono comunque applicate anche se altre falliscono: gli
    errori sono raccolti in ``errors`` senza abortire l'intero import.
    """

    created: int
    updated: int
    errors: list[ImportRowError]
