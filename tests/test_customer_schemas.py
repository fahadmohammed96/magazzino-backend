"""Test unitari degli schemi Pydantic dell'anagrafica clienti (nessun DB)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.api.schemas import Contatti, CustomerCreate, CustomerOut
from app.models.customer import Customer


def test_customer_create_valido() -> None:
    """Un corpo valido è accettato e i contatti sono annidati."""
    body = CustomerCreate(
        ragione_sociale="Acme S.r.l.",
        piva="12345678901",
        indirizzo_spedizione="Via Roma 1, Milano",
        contatti={"email": "info@acme.example", "telefono": "+39 02 1234567"},
    )
    assert body.ragione_sociale == "Acme S.r.l."
    assert body.piva == "12345678901"
    assert body.codice_fiscale is None
    assert body.contatti.email == "info@acme.example"


def test_customer_create_senza_ragione_sociale_rifiutato() -> None:
    """La ragione sociale è obbligatoria."""
    with pytest.raises(ValidationError):
        CustomerCreate(piva="12345678901")


def test_customer_create_ragione_sociale_solo_spazi_rifiutata() -> None:
    """Una ragione sociale di soli spazi, dopo il trim, è vuota → rifiutata."""
    with pytest.raises(ValidationError):
        CustomerCreate(ragione_sociale="   ")


def test_customer_create_normalizza_stringhe_vuote_a_none() -> None:
    """Le stringhe opzionali vuote sono normalizzate a None; i valori sono trimmati."""
    body = CustomerCreate(
        ragione_sociale="  Beta SpA  ",
        piva="   ",
        codice_fiscale="",
        contatti={"email": "  ", "telefono": ""},
    )
    assert body.ragione_sociale == "Beta SpA"
    assert body.piva is None
    assert body.codice_fiscale is None
    assert body.contatti.email is None
    assert body.contatti.telefono is None


def test_customer_create_contatti_default_vuoti() -> None:
    """Senza contatti, l'oggetto contatti esiste con campi None."""
    body = CustomerCreate(ragione_sociale="Gamma")
    assert body.contatti == Contatti(email=None, telefono=None)


def test_customer_out_from_model_annida_contatti() -> None:
    """``from_model`` ricompone i contatti annidati dai campi piatti del modello."""
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    customer = Customer(
        id=7,
        ragione_sociale="Delta",
        piva=None,
        codice_fiscale="RSSMRA80A01H501U",
        indirizzo_spedizione="Via Verdi 2",
        contatto_email="d@delta.example",
        contatto_telefono=None,
        created_at=now,
        updated_at=now,
    )
    out = CustomerOut.from_model(customer)
    assert out.id == 7
    assert out.codice_fiscale == "RSSMRA80A01H501U"
    assert out.contatti.email == "d@delta.example"
    assert out.contatti.telefono is None
    assert out.created_at == now
