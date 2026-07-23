"""Test unitari delle primitive di sicurezza (nessun DB)."""

import jwt
import pytest

from app.core import security
from app.core.config import Settings


def _settings(**overrides: object) -> Settings:
    # Chiave lunga ≥ 32 byte, come raccomandato per HS256 (RFC 7518).
    base = {
        "database_url": "postgresql+psycopg://x:y@localhost:5432/z",
        "auth_secret_key": "unit-test-secret-key-abcdefghijklmnop",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_hash_password_non_e_reversibile_e_include_salt() -> None:
    """L'hash non coincide con la password e due hash della stessa differiscono."""
    hashed = security.hash_password("s3greta!")
    assert hashed != "s3greta!"
    assert security.hash_password("s3greta!") != hashed  # salt per-password


def test_verify_password_vero_e_falso() -> None:
    """La verifica accetta la password giusta e rifiuta quella sbagliata."""
    hashed = security.hash_password("s3greta!")
    assert security.verify_password("s3greta!", hashed) is True
    assert security.verify_password("sbagliata", hashed) is False


def test_verify_password_hash_malformato_ritorna_false() -> None:
    """Un hash memorizzato non valido dà False, non un'eccezione."""
    assert security.verify_password("qualsiasi", "non-un-hash-bcrypt") is False


def test_token_roundtrip_riporta_subject_e_ruolo() -> None:
    """Il token creato si decodifica riportando id utente e ruolo."""
    settings = _settings()
    token = security.create_access_token(subject=42, role="admin", settings=settings)
    payload = security.decode_access_token(token, settings)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"


def test_token_scaduto_viene_rifiutato() -> None:
    """Un token con scadenza nel passato solleva ExpiredSignatureError."""
    settings = _settings()
    token = security.create_access_token(
        subject=1, role="operator", settings=settings, expires_minutes=-1
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_access_token(token, settings)


def test_token_con_chiave_diversa_viene_rifiutato() -> None:
    """Un token firmato con un'altra chiave non è accettato."""
    chiave_a = "chiave-A-lunga-abcdefghijklmnopqrstuvwxyz"
    chiave_b = "chiave-B-lunga-abcdefghijklmnopqrstuvwxyz"
    token = security.create_access_token(
        subject=1, role="operator", settings=_settings(auth_secret_key=chiave_a)
    )
    with pytest.raises(jwt.InvalidSignatureError):
        security.decode_access_token(token, _settings(auth_secret_key=chiave_b))
