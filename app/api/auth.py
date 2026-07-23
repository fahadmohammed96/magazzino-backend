"""Endpoint di autenticazione: login e profilo dell'utente corrente.

Contratto (prefisso ``/v1``):

- ``POST /v1/auth/login`` — credenziali → token Bearer + dati utente (200) o
  ``invalid_credentials`` (401).
- ``GET /v1/auth/me`` — token Bearer → dati dell'utente autenticato (200) o
  ``not_authenticated`` (401).
"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.api.errors import APIError
from app.api.schemas import LoginRequest, LoginResponse, UserOut
from app.core import security
from app.services import auth as auth_service

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    session: SessionDep,
    settings: SettingsDep,
) -> LoginResponse:
    """Autentica l'utente e ne emette un token di accesso Bearer."""
    user = auth_service.authenticate(session, body.username, body.password)
    if user is None:
        raise APIError(
            status_code=401,
            code="invalid_credentials",
            message="Credenziali non valide.",
        )
    token = security.create_access_token(
        subject=user.id, role=user.role, settings=settings
    )
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser) -> UserOut:
    """Ritorna i dati dell'utente autenticato dal token."""
    return UserOut.model_validate(current_user)
