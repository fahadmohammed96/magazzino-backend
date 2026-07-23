"""Schemi Pydantic al confine dell'API di autenticazione.

Gli schemi validano l'input in ingresso e definiscono la forma delle risposte,
che alimenta anche il contratto OpenAPI consumato dal frontend.
"""

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
