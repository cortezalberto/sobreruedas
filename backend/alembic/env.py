"""Entorno de Alembic — T-007.

Dos decisiones que conviene tener presentes:

1. **La URL sale de `Settings`, no de `alembic.ini`.** Escribirla en el `.ini`
   la versionaria con la contrasena adentro (Art. 3).

   Ojo que la URL de migracion **no es la de la aplicacion**: desde ADR-020 son
   dos roles distintos, y el de la aplicacion no puede crear tablas ni
   politicas — que es exactamente lo que una migracion hace.

   Antes, usar una sola variable garantizaba de arranque que migraciones y
   runtime nunca apuntaran a bases distintas. Con dos variables ese descuido
   vuelve a ser posible, asi que la garantia se **verifica**: si las dos URLs no
   coinciden en host, puerto y nombre de base, esto muere antes de aplicar nada.
   Migrar la base equivocada es de los errores mas caros que existen y no
   deberia depender de que nadie se confunda al copiar un `.env`.

2. **Motor asincrono.** El stack usa `asyncpg` (ADR-003), y Alembic corre
   sincronico por naturaleza. Se usa la receta oficial: se abre un engine async
   y se ejecutan las migraciones dentro de `run_sync`. La alternativa seria
   agregar un driver sincronico solo para migrar, o sea una segunda ruta de
   conexion a la base que nadie ejercita en produccion.
"""

from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from urllib.parse import urlparse

from alembic import context
from sqlalchemy import MetaData, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# `app` es importable porque alembic.ini declara `prepend_sys_path = .` y
# alembic corre desde backend/. No hace falta tocar sys.path a mano.
from app.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ─────────────────────────────────────────────────────────────────────────────
# Metadatos para autogenerate
#
# `app.db.base` lo crea T-010, que cae en C-02 — NO en este change. T-007
# declara depender de T-002 y T-005, pero su especificacion pide importar una
# Base que todavia no existe: es una inversion de dependencia del plan.
#
# Mientras tanto `target_metadata` queda en None. Eso alcanza para C-01, cuya
# unica migracion es la baseline vacia. El import se intenta igual, asi que el
# dia que T-010 aterrice, autogenerate empieza a funcionar sin tocar este
# archivo.
#
# El fallback es RUIDOSO a proposito: un autogenerate silencioso contra
# `None` produce migraciones vacias sin avisar, y eso se descubre en
# produccion.
# ─────────────────────────────────────────────────────────────────────────────
try:
    from app.db.base import Base

    target_metadata: MetaData | None = Base.metadata
except ModuleNotFoundError:
    target_metadata = None
    print(
        "[alembic] AVISO: app/db/base.py no existe todavia (lo crea T-010, C-02).\n"
        "[alembic] autogenerate esta DESACTIVADO: va a generar migraciones vacias.\n"
        "[alembic] Escribi las migraciones a mano hasta que T-010 aterrice.",
        file=sys.stderr,
    )


def _verificar_misma_base(aplicacion: str, migracion: str) -> None:
    """Las dos URLs tienen que apuntar a la misma base; solo cambia el usuario.

    Se comparan host, puerto y nombre de base. El usuario y la contrasena son
    justamente lo que debe diferir: uno es el rol de aplicacion y el otro el
    propietario (ADR-020, design.md D-5).

    El mensaje nombra que componente no coincide y **nunca incluye las URLs**:
    llevan credenciales embebidas y esto va a parar a los logs de despliegue.
    """
    app, mig = urlparse(aplicacion), urlparse(migracion)

    diferencias = [
        nombre
        for nombre, uno, otro in (
            ("host", app.hostname, mig.hostname),
            ("puerto", app.port, mig.port),
            ("base", app.path.strip("/"), mig.path.strip("/")),
        )
        if uno != otro
    ]
    if diferencias:
        raise RuntimeError(
            "DATABASE_URL y DATABASE_MIGRATION_URL apuntan a bases distintas: "
            f"no coinciden en {', '.join(diferencias)}. "
            "Solo pueden diferir en el usuario (ADR-020)."
        )


def _url_de_settings() -> str:
    """La URL del rol PROPIETARIO, verificada contra la de la aplicacion.

    Las migraciones NO corren con el rol de la aplicacion: crear tablas y
    politicas es precisamente lo que ese rol no debe poder hacer (ADR-020).
    """
    base_de_datos = get_settings().database

    if base_de_datos.migration_url is None:
        raise RuntimeError(
            "falta DATABASE_MIGRATION_URL. Las migraciones corren con el rol "
            "propietario y no con el de la aplicacion, que no puede crear "
            "tablas ni politicas (ADR-020). Ver .env.example."
        )

    migracion = base_de_datos.migration_url.get_secret_value()
    _verificar_misma_base(base_de_datos.url.get_secret_value(), migracion)
    return migracion


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse. Util para revisar que va a correr."""
    context.configure(
        url=_url_de_settings(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _aplicar(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Sin esto, un cambio de tipo de columna pasa desapercibido en
        # autogenerate y la migracion sale incompleta.
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    configuracion = config.get_section(config.config_ini_section, {})
    configuracion["sqlalchemy.url"] = _url_de_settings()

    engine = async_engine_from_config(
        configuracion,
        prefix="sqlalchemy.",
        # NullPool: el proceso de migracion es efimero y no gana nada
        # manteniendo conexiones abiertas.
        poolclass=pool.NullPool,
    )

    async with engine.connect() as conexion:
        await conexion.run_sync(_aplicar)

    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
