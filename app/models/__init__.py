"""Modelli ORM del servizio.

Importare qui i moduli dei modelli fa sì che le loro tabelle vengano
registrate su ``Base.metadata`` non appena il package ``app.models`` è
importato: comodo per ``create_all`` nei test e per l'autogenerate Alembic.
"""

from app.models.product import Product
from app.models.user import Role, User

__all__ = ["Product", "Role", "User"]
