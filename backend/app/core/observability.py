"""Correlacion de peticiones y logging estructurado — T-005.

Esta es la version minima que T-005 necesita: identificador de correlacion y
logs que lo incluyan. Las metricas de Prometheus y las trazas con OpenTelemetry
hacia Tempo (ADR-016) entran en C-03, sobre este mismo modulo.

El identificador viaja en un `ContextVar`, no en un parametro ni en un global.
Es lo unico que funciona con asyncio: cada tarea ve su propio valor aunque haya
cientos de peticiones concurrentes en el mismo hilo.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CABECERA_CORRELACION = "X-Request-ID"

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")

_logger = logging.getLogger("app.request")

# La fabrica de registros se instala una sola vez por proceso. Sin esta guarda,
# cada create_app() en la suite de tests envolveria la anterior.
_fabrica_instalada = False


def get_correlation_id() -> str:
    """Identificador de la peticion en curso, o `-` si no hay ninguna."""
    return _correlation_id.get()


def configure_logging(level: str = "INFO") -> None:
    """Deja el logging listo para que TODO registro lleve el identificador.

    Se usa `setLogRecordFactory` y no un `Filter`: los filtros no se propagan a
    los loggers hijos, asi que un filtro puesto en la raiz no alcanzaria a los
    registros que emita cualquier modulo. La fabrica, si.
    """
    global _fabrica_instalada

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s",
    )
    logging.getLogger().setLevel(level)

    if _fabrica_instalada:
        return

    fabrica_previa = logging.getLogRecordFactory()

    def fabrica(*args: Any, **kwargs: Any) -> logging.LogRecord:
        registro = fabrica_previa(*args, **kwargs)
        registro.correlation_id = get_correlation_id()
        return registro

    logging.setLogRecordFactory(fabrica)
    _fabrica_instalada = True


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Asigna, propaga y devuelve el identificador de correlacion.

    Si el cliente manda uno, se reutiliza. Eso permite seguir una operacion
    entre el frontend, la API y el worker con un solo identificador.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlacion = request.headers.get(CABECERA_CORRELACION) or str(uuid.uuid4())
        testigo = _correlation_id.set(correlacion)
        comienzo = time.perf_counter()
        try:
            respuesta = await call_next(request)
        finally:
            duracion_ms = (time.perf_counter() - comienzo) * 1000
            _logger.info(
                "%s %s (%.1f ms)",
                request.method,
                request.url.path,
                duracion_ms,
            )
            _correlation_id.reset(testigo)

        respuesta.headers[CABECERA_CORRELACION] = correlacion
        return respuesta
