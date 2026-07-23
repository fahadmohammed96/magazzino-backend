"""Logica di dominio dell'autenticazione: lettura utenti e verifica credenziali.

Il modulo lavora su una :class:`~sqlalchemy.orm.Session` ricevuta dal
chiamante e non conosce l'HTTP: gli endpoint lo usano tramite la dependency
``get_session``. Il commit resta responsabilità del chiamante (coerente con
``app.db.session.get_session``), così la scrittura è esplicita.
"""

from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.models.user import Role, User


@lru_cache(maxsize=1)
def _timing_safe_hash() -> str:
    """Hash fittizio (input non segreto), calcolato una sola volta.

    Serve a :func:`authenticate` per verificare comunque una password quando lo
    username non esiste, così il tempo di risposta non dipende dall'esistenza
    dell'utente (mitigazione dell'enumerazione via timing).
    """
    return security.hash_password("timing-safe-placeholder")


def get_user_by_username(session: Session, username: str) -> User | None:
    """Ritorna l'utente con lo ``username`` indicato, o ``None`` se assente."""
    return session.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()


def get_user_by_id(session: Session, user_id: int) -> User | None:
    """Ritorna l'utente con l'``id`` indicato, o ``None`` se assente."""
    return session.get(User, user_id)


def authenticate(session: Session, username: str, password: str) -> User | None:
    """Verifica le credenziali e ritorna l'utente, o ``None`` se non valide.

    Ritorna ``None`` sia per username inesistente sia per password errata: il
    chiamante risponde con lo stesso 401 in entrambi i casi, senza rivelare
    quale dei due sia fallito.
    """
    user = get_user_by_username(session, username)
    if user is None:
        # Verifica comunque contro un hash fittizio: mantiene il tempo di
        # risposta indipendente dall'esistenza dello username.
        security.verify_password(password, _timing_safe_hash())
        return None
    if not security.verify_password(password, user.password_hash):
        return None
    return user


def create_user(session: Session, username: str, password: str, role: Role) -> User:
    """Crea un utente con password hashata e lo aggiunge alla sessione.

    Esegue il ``flush`` per valorizzare la chiave primaria, ma **non** il
    commit: la transazione è chiusa dal chiamante.
    """
    user = User(
        username=username,
        password_hash=security.hash_password(password),
        role=role,
    )
    session.add(user)
    session.flush()
    return user
