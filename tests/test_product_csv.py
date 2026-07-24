"""Test unitari delle funzioni CSV pure del catalogo (nessun DB).

Coprono la validazione di riga, la serializzazione dell'export, il round-trip
export→import e il caso di intestazione priva delle colonne richieste.
"""

import csv
import io
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.product import Product
from app.services import products as svc


def _riga(**overrides: object) -> dict[str, str | None]:
    base: dict[str, str | None] = {
        "sku": "SKU-1",
        "name": "Vite M6",
        "description": "acciaio inox",
        "price": "1.50",
        "stock_quantity": "100",
        "low_stock_threshold": "10",
    }
    base.update(overrides)  # type: ignore[arg-type]
    return base


def test_parse_csv_row_valida() -> None:
    prod = svc.parse_csv_row(_riga())
    assert prod.sku == "SKU-1"
    assert prod.price == Decimal("1.50")
    assert prod.stock_quantity == 100
    assert prod.description == "acciaio inox"


def test_parse_csv_row_descrizione_vuota_diventa_none() -> None:
    prod = svc.parse_csv_row(_riga(description=""))
    assert prod.description is None


def test_parse_csv_row_prezzo_non_numerico_rifiutato() -> None:
    with pytest.raises(ValidationError):
        svc.parse_csv_row(_riga(price="abc"))


def test_parse_csv_row_quantita_negativa_rifiutata() -> None:
    with pytest.raises(ValidationError):
        svc.parse_csv_row(_riga(stock_quantity="-5"))


def test_products_to_csv_intestazione_e_valori() -> None:
    prodotto = Product(
        sku="SKU-1",
        name="Vite M6",
        description="acciaio",
        price=Decimal("1.5"),
        stock_quantity=100,
        low_stock_threshold=10,
    )
    testo = svc.products_to_csv([prodotto])
    righe = testo.splitlines()
    assert righe[0] == ",".join(svc.CSV_COLUMNS)
    # Prezzo formattato a 2 decimali, re-importabile.
    assert righe[1] == "SKU-1,Vite M6,acciaio,1.50,100,10"


def test_products_to_csv_descrizione_assente_e_cella_vuota() -> None:
    prodotto = Product(
        sku="SKU-2",
        name="Dado",
        description=None,
        price=Decimal("0.10"),
        stock_quantity=0,
        low_stock_threshold=0,
    )
    righe = svc.products_to_csv([prodotto]).splitlines()
    assert righe[1] == "SKU-2,Dado,,0.10,0,0"


def test_round_trip_export_import() -> None:
    """Un CSV prodotto dall'export è ri-parsabile in prodotti equivalenti."""
    prodotti = [
        Product(
            sku="SKU-1",
            name="Vite M6",
            description="acciaio inox",
            price=Decimal("1.50"),
            stock_quantity=100,
            low_stock_threshold=10,
        ),
        Product(
            sku="SKU-2",
            name="Dado",
            description=None,
            price=Decimal("0.10"),
            stock_quantity=0,
            low_stock_threshold=5,
        ),
    ]
    testo = svc.products_to_csv(prodotti)
    reader = csv.DictReader(io.StringIO(testo))
    riparsati = [svc.parse_csv_row(r) for r in reader]
    assert [p.sku for p in riparsati] == ["SKU-1", "SKU-2"]
    assert riparsati[0].price == Decimal("1.50")
    assert riparsati[1].description is None
    assert riparsati[1].stock_quantity == 0


def test_import_intestazione_incompleta_ritorna_errore_riga_1() -> None:
    """Un file privo di colonne richieste produce un solo errore sulla riga 1."""
    testo = "sku,name\nSKU-1,Vite\n"
    # Il ramo di intestazione mancante ritorna prima di toccare la sessione.
    risultato = svc.import_products(None, testo)  # type: ignore[arg-type]
    assert risultato.created == 0
    assert risultato.updated == 0
    assert len(risultato.errors) == 1
    assert risultato.errors[0].row == 1
    assert "price" in risultato.errors[0].message


def test_export_disinnesca_valori_formula() -> None:
    """Un valore che inizierebbe una formula è preceduto da un apice in export."""
    prodotto = Product(
        sku="=CMD",
        name="-1+2",
        description="@ref",
        price=Decimal("1.00"),
        stock_quantity=1,
        low_stock_threshold=1,
    )
    riga = svc.products_to_csv([prodotto]).splitlines()[1]
    # Le celle a rischio sono citate perché contengono la virgola o l'apice.
    assert riga.startswith("'=CMD,")
    assert "'-1+2" in riga
    assert "'@ref" in riga


def test_round_trip_valori_formula_senza_perdite() -> None:
    """La coppia disinnesco (export) / ripulitura (import) è senza perdite."""
    originali = [
        Product(
            sku="=CMD|calc",
            name="-danger",
            description="@formula",
            price=Decimal("2.00"),
            stock_quantity=3,
            low_stock_threshold=1,
        )
    ]
    testo = svc.products_to_csv(originali)
    reader = csv.DictReader(io.StringIO(testo))
    riparsati = [svc.parse_csv_row(r) for r in reader]
    assert riparsati[0].sku == "=CMD|calc"
    assert riparsati[0].name == "-danger"
    assert riparsati[0].description == "@formula"


def test_apice_legittimo_preservato() -> None:
    """Un apice iniziale seguito da testo normale non viene rimosso in import."""
    prod = svc.parse_csv_row(
        {
            "sku": "SKU-1",
            "name": "'Promo",
            "description": "'ok",
            "price": "1.00",
            "stock_quantity": "1",
            "low_stock_threshold": "1",
        }
    )
    assert prod.name == "'Promo"
    assert prod.description == "'ok"
