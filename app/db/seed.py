"""Seed dell'utente admin iniziale, per il primo accesso al gestionale.

Eseguibile come script una tantum::

    python -m app.db.seed

Legge ``SEED_ADMIN_USERNAME`` e ``SEED_ADMIN_PASSWORD`` dall'ambiente (vedi
``.env.example``): se l'utente non esiste lo crea con ruolo ``admin``, altrimenti
non fa nulla (operazione idempotente). La password non viene mai loggata.

Prerequisito: lo schema deve essere già applicato (``alembic upgrade head``).
"""

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.user import Role, User
from app.services import auth as auth_service


def ensure_seed_admin(session: Session, username: str, password: str) -> User | None:
    """Crea l'admin iniziale se assente; ritorna l'utente creato o ``None``.

    Idempotente: se esiste già un utente con quello ``username`` non fa nulla e
    ritorna ``None``. Non esegue il commit: spetta al chiamante.
    """
    if auth_service.get_user_by_username(session, username) is not None:
        return None
    return auth_service.create_user(session, username, password, Role.admin)


def _run(settings: Settings) -> None:
    """Apre una sessione, esegue il seed e committa. Usato da ``__main__``."""
    if not settings.seed_admin_username or not settings.seed_admin_password:
        raise SystemExit(
            "Seed non eseguito: impostare SEED_ADMIN_USERNAME e "
            "SEED_ADMIN_PASSWORD nell'ambiente."
        )

    # Import locale: evita di creare l'engine (e leggere DATABASE_URL) solo per
    # importare il modulo, coerente con l'inizializzazione pigra di app.db.
    from app.db.session import get_session

    session_gen = get_session()
    session = next(session_gen)
    try:
        user = ensure_seed_admin(
            session, settings.seed_admin_username, settings.seed_admin_password
        )
        if user is not None:
            session.commit()
            print(f"Admin '{user.username}' creato.")
        else:
            print(
                f"Admin '{settings.seed_admin_username}' già presente: nessuna azione."
            )
    finally:
        session_gen.close()


if __name__ == "__main__":  # pragma: no cover - entrypoint da riga di comando
    _run(get_settings())
