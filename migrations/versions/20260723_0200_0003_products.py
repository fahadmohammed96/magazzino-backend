"""products: tabella del catalogo prodotti con giacenza

Revision ID: 0003_products
Revises: 0002_users
Create Date: 2026-07-23 02:00:00.000000

Crea la tabella ``products`` (sku univoco, nome, descrizione opzionale, prezzo
decimale a 2 cifre, quantità a magazzino, soglia di sotto-scorta, timestamp di
creazione e aggiornamento) con indice univoco su ``sku``.

Reversibile: ``downgrade`` rimuove indice e tabella, riportando lo schema allo
stato della revisione ``0002_users``. Nessuna modifica distruttiva su dati
esistenti (la tabella è nuova).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_products"
down_revision: str | None = "0002_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crea la tabella ``products`` e l'indice univoco su ``sku``."""
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False),
        sa.Column("low_stock_threshold", sa.Integer(), nullable=False),
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
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)


def downgrade() -> None:
    """Rimuove indice e tabella ``products``."""
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_table("products")
