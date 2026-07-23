"""Dependency di protezione riusabili per gli endpoint.

Due strumenti pensati per essere applicati agli endpoint di dominio futuri:

- :func:`get_current_user` — richiede un token Bearer valido e risolve
  l'utente dal database; risponde 401 se il token manca, è invalido o scaduto.
- :func:`require_role` — factory che, dato un ruolo minimo, produce una
  dependency che risponde 403 quando il ruolo dell'utente è insufficiente.

Il formato d'errore è quello unico del progetto (vedi :mod:`app.api.errors`).
"""

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.core import security
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.models.user import Role, User
from app.services import auth as auth_service

# auto_error=False: gestiamo noi l'assenza del token, così la risposta 401
# rispetta il formato d'errore del progetto invece del default di FastAPI.
_bearer_scheme = HTTPBearer(auto_error=False)

# Ordinamento dei privilegi: un ruolo soddisfa un requisito se il suo rango è
# maggiore o uguale a quello richiesto. Admin ha più privilegi dell'operatore.
_ROLE_RANK: dict[Role, int] = {
    Role.operator: 1,
    Role.admin: 2,
}

_NOT_AUTHENTICATED = APIError(
    status_code=401,
    code="not_authenticated",
    message="Autenticazione richiesta.",
)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """Risolve l'utente autenticato a partire dal token Bearer.

    Solleva :class:`~app.api.errors.APIError` 401 se il token è assente, con
    schema diverso da ``Bearer``, invalido/scaduto, o se l'utente riferito non
    esiste (più).
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _NOT_AUTHENTICATED

    try:
        payload = security.decode_access_token(credentials.credentials, settings)
    except jwt.PyJWTError as exc:
        raise APIError(
            status_code=401,
            code="not_authenticated",
            message="Token non valido o scaduto.",
        ) from exc

    subject = payload.get("sub")
    if subject is None:
        raise _NOT_AUTHENTICATED
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _NOT_AUTHENTICATED from None

    user = auth_service.get_user_by_id(session, user_id)
    if user is None:
        raise _NOT_AUTHENTICATED
    return user


def require_role(minimum: Role) -> Callable[[User], User]:
    """Crea una dependency che richiede almeno il ruolo ``minimum``.

    La dependency risultante prima autentica (401 senza token valido), poi
    verifica il ruolo (403 se insufficiente) e infine ritorna l'utente, così
    che l'endpoint possa usarlo. Esempio d'uso su un endpoint futuro::

        @router.get("/report", dependencies=[Depends(require_role(Role.admin))])
        def report() -> ...:
            ...
    """
    required_rank = _ROLE_RANK[minimum]

    def _require_role(user: Annotated[User, Depends(get_current_user)]) -> User:
        if _ROLE_RANK[user.role] < required_rank:
            raise APIError(
                status_code=403,
                code="forbidden",
                message="Permessi insufficienti per questa operazione.",
            )
        return user

    return _require_role


# Alias riusabili per gli endpoint, nello stile Annotated (evita chiamate nei
# valori di default degli argomenti).
SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
CurrentUser = Annotated[User, Depends(get_current_user)]
