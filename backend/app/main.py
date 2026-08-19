"""Bootstrap de la aplicacion FastAPI — T-005.

Cubre la capability `platform/service-health`: sonda de vida, sonda de
disponibilidad, correlacion de peticiones y el gate de documentacion por
ambiente.

Todavia no registra ningun router de dominio: eso empieza en C-02.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, describir_configuracion, get_settings
from app.core.errors import TIPO_CONTENIDO, register_exception_handlers
from app.core.observability import (
    CorrelationIdMiddleware,
    configure_logging,
    get_correlation_id,
)
from app.modules.stock.router import router as stock_router
from app.modules.tenancy.router import router as tenancy_router

VERSION = "0.1.0"

_logger = logging.getLogger("app.main")

Sonda = Callable[[], Awaitable[None]]


# ─────────────────────────────────────────────────────────────────────────────
# Sondas reales
# ─────────────────────────────────────────────────────────────────────────────


def _dsn_sin_driver(url: str) -> str:
    """`postgresql+asyncpg://...` -> `postgresql://...`.

    SQLAlchemy quiere el dialecto en el esquema; asyncpg, a secas.
    """
    return url.replace("+asyncpg", "", 1)


def _crear_sondas(app: FastAPI, settings: Settings) -> dict[str, Sonda]:
    async def base_de_datos() -> None:
        import asyncpg

        conexion = await asyncpg.connect(
            _dsn_sin_driver(settings.database.url.get_secret_value()), timeout=3
        )
        try:
            await conexion.fetchval("SELECT 1")
        finally:
            await conexion.close()

    async def redis_() -> None:
        cliente: aioredis.Redis = app.state.redis
        await cliente.ping()

    return {"database": base_de_datos, "redis": redis_}


# ─────────────────────────────────────────────────────────────────────────────
# Aplicacion
# ─────────────────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """Arma la aplicacion.

    Es una fabrica y no un modulo con estado global porque el gate de
    documentacion se resuelve al construir: para probar el comportamiento en
    produccion hay que poder construir una app con `APP_ENV=production`.
    """
    settings = get_settings()
    configure_logging(settings.observability.log_level)

    en_produccion = settings.app.is_production

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # El cliente se crea sin conectar: redis-py abre la conexion en el
        # primer comando. Asi el arranque no depende de que Redis ya este
        # arriba, que es justo lo que la sonda de disponibilidad informa.
        # from_url no viene tipada en redis-py; el ignore es puntual y
        # nombra el codigo exacto, no un blanket ignore.
        app.state.redis = aioredis.from_url(  # type: ignore[no-untyped-call]
            settings.redis.url, socket_connect_timeout=3, socket_timeout=3
        )
        app.state.readiness_checks = _crear_sondas(app, settings)
        # Con que configuracion arranco el proceso, enmascarada. Sin esto,
        # diagnosticar "en staging anda distinto" empieza por adivinar que
        # variables tenia el proceso, que es donde se va la primera hora.
        # Los secretos salen como `***` porque son SecretStr; el enmascarado
        # no depende de que nadie se acuerde de excluirlos.
        _logger.info("configuracion efectiva:\n%s", "\n".join(describir_configuracion(settings)))
        _logger.info("aplicacion iniciada (env=%s)", settings.app.env)
        try:
            yield
        finally:
            await app.state.redis.aclose()
            _logger.info("aplicacion detenida")

    app = FastAPI(
        title="deRuedas Gestion API",
        version=VERSION,
        description="API del SaaS multi-tenant para agencias de vehiculos.",
        lifespan=lifespan,
        # En produccion no hay documentacion interactiva ni esquema OpenAPI
        # publicado: es superficie de reconocimiento gratis para un atacante.
        docs_url=None if en_produccion else "/docs",
        redoc_url=None if en_produccion else "/redoc",
        openapi_url=None if en_produccion else "/openapi.json",
    )

    # El orden importa: el de correlacion va PRIMERO para que el identificador
    # exista cuando cualquier otra capa quiera loguear.
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # Primer router de dominio. Publica solo el catalogo de planes, que no lleva
    # `tenant_id` ni requiere identidad — ver el encabezado de `router.py`. Los
    # endpoints de agencias y usuarios siguen siendo C-05.
    app.include_router(tenancy_router)

    # Primer router con datos de una agencia. Cada endpoint pide `SesionDeTenant`,
    # que exige token y acota al tenant del claim. Ver su encabezado: todavia no
    # tiene `require_permission` — eso es el bloque 6 de C-02.
    app.include_router(stock_router)

    @app.get("/health", tags=["salud"], summary="Sonda de vida")
    async def health() -> dict[str, Any]:
        """Responde mientras el proceso viva. NO consulta dependencias.

        Es a proposito: si consultara la base, una caida de PostgreSQL haria
        que Kubernetes reiniciara el pod en loop, sin arreglar nada y
        agregandole carga a una base que ya esta sufriendo.
        """
        return {
            "status": "alive",
            "version": VERSION,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @app.get("/ready", tags=["salud"], summary="Sonda de disponibilidad")
    async def ready() -> JSONResponse:
        """Verifica las dependencias necesarias para atender trafico."""
        fallidas: list[str] = []
        for nombre, sonda in app.state.readiness_checks.items():
            try:
                await sonda()
            except Exception:
                # Se registra el NOMBRE de la dependencia y nada mas. La
                # excepcion suele traer la cadena de conexion completa, con
                # usuario y contrasena adentro.
                _logger.warning("la dependencia '%s' no responde", nombre)
                fallidas.append(nombre)

        if fallidas:
            return JSONResponse(
                status_code=503,
                media_type=TIPO_CONTENIDO,
                content={
                    "status": "not_ready",
                    "failed": fallidas,
                    "correlation_id": get_correlation_id(),
                },
            )
        return JSONResponse(
            status_code=200,
            content={"status": "ready", "correlation_id": get_correlation_id()},
        )

    return app


# A proposito NO hay `app = create_app()` de nivel de modulo: eso dispararia la
# lectura de configuracion al IMPORTAR, y entonces importar el modulo —para un
# test, para una herramienta, para leer el docstring— exigiria un entorno valido.
# La muerte temprana corresponde al arrancar el PROCESO, no al importar.
# Por eso uvicorn se invoca con --factory:
#     uvicorn app.main:create_app --factory
