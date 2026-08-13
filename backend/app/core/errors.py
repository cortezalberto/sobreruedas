"""Errores de dominio y respuestas Problem Details — T-005.

Todo error que sale de la API tiene el MISMO formato, sea de dominio, de
validacion o un 404. Que cada capa invente su propio JSON de error es lo que
obliga a quien consume la API a escribir un parser por endpoint.

El formato es Problem Details (RFC 9457), con dos extensiones propias:

  code            identificador estable del error, para que el cliente
                  discrimine sin parsear el texto en castellano
  correlation_id  el identificador de la peticion. Sin esto, un usuario que
                  reporta "me dio error" no se puede rastrear en los logs.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.observability import get_correlation_id

TIPO_CONTENIDO = "application/problem+json"


class DomainError(Exception):
    """Una regla de negocio dijo que no.

    No es un fallo tecnico: la peticion se entendio, pero el dominio la
    rechaza. Por eso 422 y no 500.
    """

    status_code = 422

    def __init__(self, detail: str, *, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code or "domain_error"


def _problema(
    *, status: int, title: str, detail: str, code: str, extra: dict[str, Any] | None = None
) -> JSONResponse:
    cuerpo: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "correlation_id": get_correlation_id(),
    }
    if extra:
        cuerpo.update(extra)
    return JSONResponse(status_code=status, content=cuerpo, media_type=TIPO_CONTENIDO)


def register_exception_handlers(app: FastAPI) -> None:
    """Cuelga los handlers globales en la aplicacion."""

    @app.exception_handler(DomainError)
    async def _dominio(_: Request, exc: DomainError) -> JSONResponse:
        return _problema(
            status=exc.status_code,
            title="Regla de negocio incumplida",
            detail=exc.detail,
            code=exc.code,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problema(
            status=exc.status_code,
            title="Error HTTP",
            detail=str(exc.detail),
            code=f"http_{exc.status_code}",
        )

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        # `errors()` trae `input`, o sea el valor que mando el cliente. Se
        # descarta a proposito: puede ser una contrasena o un token.
        campos = [
            {
                "field": ".".join(str(parte) for parte in detalle["loc"]),
                "message": detalle["msg"],
            }
            for detalle in exc.errors()
        ]
        return _problema(
            status=422,
            title="Peticion invalida",
            detail="La peticion no supero la validacion.",
            code="validation_error",
            extra={"errors": campos},
        )
