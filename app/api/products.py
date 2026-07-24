"""Endpoint del catalogo prodotti (prefisso ``/v1``).

Contratto:

- ``GET /v1/products`` — lista (admin, operator); ``?low_stock=true`` filtra i
  sotto-scorta.
- ``GET /v1/products/{id}`` — dettaglio (admin, operator).
- ``POST /v1/products`` — crea (solo admin) → 201.
- ``PUT /v1/products/{id}`` — aggiorna (solo admin).
- ``DELETE /v1/products/{id}`` — elimina (solo admin) → 204.
- ``POST /v1/products/import`` — import CSV (solo admin), multipart → riepilogo.
- ``GET /v1/products/export`` — export CSV (admin, operator) → ``text/csv``.

Autorizzazione per ruolo su ogni endpoint (non solo autenticazione): scrittura
riservata all'admin, lettura anche all'operatore. Errori nel formato unico del
progetto: 401 senza token, 403 ruolo insufficiente, 404 id inesistente, 409 sku
duplicato, 422 validazione.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from app.api.deps import SessionDep, require_role
from app.api.errors import APIError
from app.api.schemas import ImportResult, ProductCreate, ProductOut, ProductUpdate
from app.models.user import Role
from app.services import products as products_service
from app.services.products import SkuConflictError

router = APIRouter(prefix="/v1/products", tags=["products"])

# Dependency di autorizzazione riusate: lettura per operator+, scrittura admin.
_read_dep = Depends(require_role(Role.operator))
_write_dep = Depends(require_role(Role.admin))

# Tetto di dimensione per l'import CSV: il file è letto interamente in memoria,
# quindi si limita per evitare che un upload sproporzionato esaurisca la RAM.
# 5 MiB coprono decine di migliaia di righe di catalogo con ampio margine.
_MAX_IMPORT_BYTES = 5 * 1024 * 1024


def _conflict(sku: str) -> APIError:
    return APIError(
        status_code=409,
        code="sku_conflict",
        message=f"Esiste già un prodotto con lo SKU '{sku}'.",
    )


def _not_found(product_id: int) -> APIError:
    return APIError(
        status_code=404,
        code="not_found",
        message=f"Prodotto {product_id} non trovato.",
    )


@router.get("", response_model=list[ProductOut], dependencies=[_read_dep])
def list_products(
    session: SessionDep,
    low_stock: Annotated[
        bool, Query(description="Se true, ritorna solo i prodotti sotto-scorta.")
    ] = False,
) -> list[ProductOut]:
    """Elenca i prodotti; con ``?low_stock=true`` solo quelli sotto-scorta."""
    prodotti = products_service.list_products(session, low_stock_only=low_stock)
    return [ProductOut.model_validate(p) for p in prodotti]


@router.get("/export", dependencies=[_read_dep])
def export_products(session: SessionDep) -> Response:
    """Esporta l'intero catalogo come CSV re-importabile (``text/csv``)."""
    prodotti = products_service.list_products(session)
    corpo = products_service.products_to_csv(prodotti)
    return Response(
        content=corpo,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="products.csv"'},
    )


@router.post(
    "/import",
    response_model=ImportResult,
    dependencies=[_write_dep],
)
async def import_products(
    session: SessionDep,
    file: Annotated[
        UploadFile, File(description="File CSV con le colonne del catalogo.")
    ],
) -> ImportResult:
    """Importa prodotti da CSV con upsert per ``sku``.

    Le righe valide sono create/aggiornate; quelle invalide sono raccolte in
    ``errors`` senza abortire l'import. Applica le modifiche (commit) solo dopo
    aver processato l'intero file. Rifiuta con 413 un file oltre il tetto di
    dimensione (letto interamente in memoria).
    """
    # Legge al massimo il tetto + 1 byte: se supera, il file è troppo grande.
    contenuto = await file.read(_MAX_IMPORT_BYTES + 1)
    if len(contenuto) > _MAX_IMPORT_BYTES:
        raise APIError(
            status_code=413,
            code="file_too_large",
            message="Il file CSV supera il limite di 5 MiB consentito.",
        )
    try:
        testo = contenuto.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise APIError(
            status_code=422,
            code="invalid_file",
            message="Il file non è un CSV codificato in UTF-8.",
        ) from exc
    risultato = products_service.import_products(session, testo)
    session.commit()
    return risultato


@router.get("/{product_id}", response_model=ProductOut, dependencies=[_read_dep])
def get_product(product_id: int, session: SessionDep) -> ProductOut:
    """Ritorna il dettaglio del prodotto, o 404 se l'id non esiste."""
    prodotto = products_service.get_product(session, product_id)
    if prodotto is None:
        raise _not_found(product_id)
    return ProductOut.model_validate(prodotto)


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_write_dep],
)
def create_product(body: ProductCreate, session: SessionDep) -> ProductOut:
    """Crea un prodotto (solo admin); 409 se lo ``sku`` è già in uso."""
    try:
        prodotto = products_service.create_product(session, body)
    except SkuConflictError as exc:
        raise _conflict(exc.sku) from exc
    session.commit()
    return ProductOut.model_validate(prodotto)


@router.put("/{product_id}", response_model=ProductOut, dependencies=[_write_dep])
def update_product(
    product_id: int, body: ProductUpdate, session: SessionDep
) -> ProductOut:
    """Aggiorna un prodotto (solo admin); 404 se assente, 409 su ``sku`` in uso."""
    prodotto = products_service.get_product(session, product_id)
    if prodotto is None:
        raise _not_found(product_id)
    try:
        prodotto = products_service.update_product(session, prodotto, body)
    except SkuConflictError as exc:
        raise _conflict(exc.sku) from exc
    session.commit()
    return ProductOut.model_validate(prodotto)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[_write_dep],
)
def delete_product(product_id: int, session: SessionDep) -> Response:
    """Elimina un prodotto (solo admin); 404 se l'id non esiste."""
    prodotto = products_service.get_product(session, product_id)
    if prodotto is None:
        raise _not_found(product_id)
    products_service.delete_product(session, prodotto)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
