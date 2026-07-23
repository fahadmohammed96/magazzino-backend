"""Primitive di sicurezza: hashing password e token di accesso.

Due responsabilità, entrambe pure (nessun accesso al DB):

- **Password**: hashing e verifica con bcrypt (salt per-password, generato da
  ``bcrypt.gensalt``). La password in chiaro non viene mai salvata né loggata.
- **Token di accesso**: JWT firmati HS256 con ``settings.auth_secret_key``. Il
  token porta l'id utente (``sub``), il ruolo (``role``) e le scadenze
  ``iat``/``exp``; la firma ne garantisce l'integrità.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import Settings

ALGORITHM = "HS256"

# bcrypt considera solo i primi 72 byte della password: oltre quel limite i
# byte in eccesso verrebbero silenziosamente ignorati.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Restituisce l'hash bcrypt della password (comprensivo di salt).

    Il valore ritornato è una stringa ASCII adatta alla colonna
    ``users.password_hash``; include algoritmo, costo e salt, quindi è
    autosufficiente per la verifica successiva.

    Solleva :class:`ValueError` se la password supera i 72 byte (limite di
    bcrypt): meglio un errore esplicito — es. in fase di seed — che un
    troncamento silenzioso che indebolirebbe la password senza avviso.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        raise ValueError(
            f"La password supera il limite di {_BCRYPT_MAX_BYTES} byte di bcrypt."
        )
    hashed = bcrypt.hashpw(encoded, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica che ``password`` corrisponda a ``password_hash``.

    Ritorna ``False`` — senza sollevare eccezioni — anche quando l'hash
    memorizzato è malformato, così un dato corrotto non diventa un errore 500.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    *,
    subject: int | str,
    role: str,
    settings: Settings,
    expires_minutes: int | None = None,
) -> str:
    """Crea un token di accesso JWT firmato per l'utente indicato.

    Argomenti:
        subject: identificativo dell'utente, serializzato nel claim ``sub``.
        role: ruolo dell'utente, nel claim ``role`` (informativo).
        settings: impostazioni da cui leggere chiave e durata.
        expires_minutes: durata in minuti; se assente usa
            ``settings.access_token_expire_minutes``.
    """
    now = datetime.now(UTC)
    minutes = (
        expires_minutes
        if expires_minutes is not None
        else settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": str(role),
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.auth_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decodifica e verifica un token di accesso.

    Solleva :class:`jwt.PyJWTError` (o sue sottoclassi, es.
    ``ExpiredSignatureError``) se il token è assente di firma valida, scaduto o
    manomesso. La gestione dell'errore — e la traduzione in risposta 401 nel
    formato del progetto — spetta al chiamante.
    """
    return jwt.decode(token, settings.auth_secret_key, algorithms=[ALGORITHM])
