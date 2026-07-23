"""Modello dell'utente interno e ruolo di autorizzazione.

Due soli ruoli, secondo la decisione di kickoff (vedi ``AGENTS.md``):

- ``admin`` — gestione utenti, prodotti, prezzi e report;
- ``operator`` — ordini, stati ordine e consultazione giacenze.

La password non è mai salvata in chiaro: la colonna ``password_hash`` contiene
solo l'hash bcrypt calcolato in ``app.core.security``.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Role(enum.StrEnum):
    """Ruolo di autorizzazione dell'utente.

    Essendo una :class:`~enum.StrEnum`, ogni membro coincide con il proprio
    valore stringa (``Role.admin == "admin"``): la serializzazione JSON e il
    valore salvato a DB sono quindi la stringa del ruolo.
    """

    admin = "admin"
    operator = "operator"


class User(Base):
    """Utente interno che accede al gestionale.

    Attributi:
        id: identificativo numerico, chiave primaria.
        username: nome utente univoco usato per il login.
        password_hash: hash bcrypt della password; mai la password in chiaro.
        role: ruolo di autorizzazione (:class:`Role`).
        created_at: istante di creazione, valorizzato dal database.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(
            Role,
            name="user_role",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - solo diagnostica
        return f"User(id={self.id!r}, username={self.username!r}, role={self.role!r})"
