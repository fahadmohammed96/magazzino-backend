"""Base dichiarativa SQLAlchemy 2.

Tutti i modelli ORM del progetto erediteranno da :class:`Base`. La sua
``metadata`` è il bersaglio delle migrazioni Alembic: perché l'autogenerate
veda una tabella, il relativo modulo di modelli deve essere importato prima
che Alembic legga ``Base.metadata`` (vedi ``migrations/env.py``).

Nessun modello di dominio è definito qui: le entità (catalogo, clienti,
ordini) arriveranno nelle issue di dominio dedicate.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe base comune a tutti i modelli ORM del servizio."""
