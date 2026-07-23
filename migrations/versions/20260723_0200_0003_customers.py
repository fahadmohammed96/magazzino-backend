"""customers: tabella dell'anagrafica clienti

Revision ID: 0003_customers
Revises: 0002_users
Create Date: 2026-07-23 02:00:00.000000

Crea la tabella ``customers`` (ragione sociale obbligatoria e indicizzata per la
ricerca, dati fiscali e indirizzo opzionali, contatti email/telefono, timestamp
di creazione e aggiornamento).

Reversibile: ``downgrade`` rimuove indice e tabella, riportando lo schema allo
stato della revisione ``0002_users``. Nessuna modifica distruttiva su dati
esistenti (la tabella è nuova).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_customers"
down_revision: str | None = "0002_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabella ``customers`` e l'indice sulla ragione sociale."""
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ragione_sociale", sa.String(length=255), nullable=False),
        sa.Column("piva", sa.String(length=32), nullable=True),
        sa.Column("codice_fiscale", sa.String(length=32), nullable=True),
        sa.Column("indirizzo_spedizione", sa.String(length=500), nullable=True),
        sa.Column("contatto_email", sa.String(length=255), nullable=True),
        sa.Column("contatto_telefono", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_customers_ragione_sociale", "customers", ["ragione_sociale"])


def downgrade() -> None:
    """Rimuove indice e tabella ``customers``."""
    op.drop_index("ix_customers_ragione_sociale", table_name="customers")
    op.drop_table("customers")
