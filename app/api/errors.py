"""Formato d'errore unico del servizio.

Ogni risposta d'errore ha la forma ``{"error": {"code": ..., "message": ...}}``
(decisione di kickoff, vedi ``AGENTS.md``): mai stack trace né dettagli interni
nel corpo. Il modulo espone :class:`APIError`, l'eccezione da sollevare negli
endpoint, e :func:`register_exception_handlers`, che installa i gestori sul
``FastAPI`` perché anche gli errori generati dal framework (validazione,
``HTTPException``, eccezioni non gestite) rispettino lo stesso formato.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Mappa da codice di stato HTTP a codice d'errore applicativo stabile,
# per gli errori sollevati dal framework (non da APIError).
_STATUS_TO_CODE: dict[int, str] = {
    400: "bad_request",
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
}


class APIError(Exception):
    """Errore applicativo con codice e messaggio destinati al client.

    Argomenti:
        status_code: codice di stato HTTP della risposta.
        code: codice d'errore stabile e machine-readable (es.
            ``invalid_credentials``).
        message: messaggio leggibile, privo di dettagli interni.
    """

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Installa i gestori d'errore sul dato ``FastAPI``."""

    @app.exception_handler(APIError)
    async def _handle_api_error(_request: Request, exc: APIError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            422, "validation_error", "Dati della richiesta non validi."
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = _STATUS_TO_CODE.get(exc.status_code, "error")
        message = exc.detail if isinstance(exc.detail, str) else "Errore."
        return _error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(
        _request: Request, _exc: Exception
    ) -> JSONResponse:
        # Nessun dettaglio interno né stack trace nel corpo: solo un messaggio
        # generico. Il traceback resta nei log del server, non nella risposta.
        return _error_response(500, "internal_error", "Errore interno del server.")
