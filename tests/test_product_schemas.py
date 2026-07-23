"""Test unitari degli schemi Pydantic del catalogo e del campo calcolato
``low_stock`` del modello (nessun DB)."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.schemas import ProductCreate, ProductOut
from app.models.product import Product

VALIDO = {
    "sku": "SKU-1",
    "name": "Vite M6",
    "price": "1.50",
    "stock_quantity": 100,
    "low_stock_threshold": 10,
}


def test_product_create_valido() -> None:
    prod = ProductCreate(**VALIDO)
    assert prod.sku == "SKU-1"
    assert prod.price == Decimal("1.50")
    assert prod.description is None


def test_product_create_prezzo_negativo_rifiutato() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(**{**VALIDO, "price": "-1.00"})


def test_product_create_quantita_negativa_rifiutata() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(**{**VALIDO, "stock_quantity": -1})


def test_product_create_soglia_negativa_rifiutata() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(**{**VALIDO, "low_stock_threshold": -1})


def test_product_create_prezzo_troppi_decimali_rifiutato() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(**{**VALIDO, "price": "1.505"})


def test_product_create_sku_vuoto_rifiutato() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(**{**VALIDO, "sku": ""})


def test_product_create_spazi_normalizzati() -> None:
    prod = ProductCreate(**{**VALIDO, "sku": "  SKU-9  ", "name": "  Dado  "})
    assert prod.sku == "SKU-9"
    assert prod.name == "Dado"


def test_low_stock_true_quando_scorta_sotto_soglia() -> None:
    prodotto = Product(
        sku="X",
        name="X",
        price=Decimal("1.00"),
        stock_quantity=5,
        low_stock_threshold=10,
    )
    assert prodotto.low_stock is True


def test_low_stock_false_quando_scorta_sopra_soglia() -> None:
    prodotto = Product(
        sku="X",
        name="X",
        price=Decimal("1.00"),
        stock_quantity=20,
        low_stock_threshold=10,
    )
    assert prodotto.low_stock is False


def test_low_stock_true_al_pari_della_soglia() -> None:
    prodotto = Product(
        sku="X",
        name="X",
        price=Decimal("1.00"),
        stock_quantity=10,
        low_stock_threshold=10,
    )
    assert prodotto.low_stock is True


def test_product_out_espone_low_stock_calcolato() -> None:
    prodotto = Product(
        sku="X",
        name="X",
        price=Decimal("1.00"),
        stock_quantity=3,
        low_stock_threshold=5,
    )
    out = ProductOut.model_validate(
        {
            "id": 1,
            "sku": prodotto.sku,
            "name": prodotto.name,
            "description": None,
            "price": prodotto.price,
            "stock_quantity": prodotto.stock_quantity,
            "low_stock_threshold": prodotto.low_stock_threshold,
            "low_stock": prodotto.low_stock,
            "created_at": "2026-07-23T00:00:00Z",
            "updated_at": "2026-07-23T00:00:00Z",
        }
    )
    assert out.low_stock is True
