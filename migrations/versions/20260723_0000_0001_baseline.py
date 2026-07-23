"""baseline: ancora della catena di migrazioni

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-23 00:00:00.000000

Prima migrazione del progetto. Non crea alcuna tabella: fissa solo la testa
della catena Alembic su un database pulito, così che ``alembic upgrade head``
e ``alembic downgrade base`` siano funzionanti fin da subito. Le tabelle di
dominio (catalogo, clienti, ordini) arriveranno nelle rispettive migrazioni,
con questa come antenato.
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Baseline: nessuno schema da applicare."""
    pass


def downgrade() -> None:
    """Baseline: nessuno schema da rimuovere."""
    pass
