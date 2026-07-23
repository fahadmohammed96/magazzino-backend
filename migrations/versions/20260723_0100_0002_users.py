"""users: tabella degli utenti interni e tipo enum del ruolo

Revision ID: 0002_users
Revises: 0001_baseline
Create Date: 2026-07-23 01:00:00.000000

Crea la tabella ``users`` (username univoco, hash password, ruolo, timestamp di
creazione) e il tipo enum PostgreSQL ``user_role`` (``admin``/``operator``).

Reversibile: ``downgrade`` rimuove indice, tabella e tipo enum, riportando lo
schema allo stato del baseline. Nessuna modifica distruttiva su dati esistenti
(la tabella è nuova).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_users"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tipo enum condiviso: create_type=True (default) fa sì che create_table emetta
# il CREATE TYPE; in downgrade lo rimuoviamo esplicitamente.
_role_enum = sa.Enum("admin", "operator", name="user_role")


def upgrade() -> None:
    """Crea il tipo enum del ruolo, la tabella ``users`` e l'indice univoco."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", _role_enum, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    """Rimuove indice, tabella ``users`` e tipo enum ``user_role``."""
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    _role_enum.drop(op.get_bind(), checkfirst=True)
