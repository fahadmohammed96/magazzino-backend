"""Test d'integrazione del seed dell'admin iniziale (Postgres reale)."""

from sqlalchemy.orm import Session, sessionmaker

from app.core import security
from app.db.seed import ensure_seed_admin
from app.models.user import Role
from app.services import auth as auth_service


def test_seed_crea_admin_e_e_idempotente(
    session_factory: sessionmaker[Session],
) -> None:
    """Il primo seed crea l'admin; il secondo non fa nulla."""
    with session_factory() as session:
        created = ensure_seed_admin(session, "boss", "super-segreta")
        session.commit()

        assert created is not None
        assert created.role is Role.admin
        assert created.password_hash != "super-segreta"
        assert security.verify_password("super-segreta", created.password_hash)

    with session_factory() as session:
        again = ensure_seed_admin(session, "boss", "super-segreta")
        session.commit()
        assert again is None

        # Esiste esattamente un utente "boss".
        user = auth_service.get_user_by_username(session, "boss")
        assert user is not None
        assert user.role is Role.admin
