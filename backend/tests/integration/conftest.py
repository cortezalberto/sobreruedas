"""Fixtures comunes de los tests de integracion.

Lo que vive aca es lo que TODOS los tests de integracion necesitan y ninguno
deberia tener que acordarse de pedir. El soporte importable —los dos DSN, la
sesion de propietario, el invocador de alembic— esta en `soporte.py`.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import cerrar_engines, sesion_de_plataforma, sesion_de_tenant

from .soporte import DSN_APLICACION, URL_REDIS, alembic


@pytest.fixture(autouse=True)
async def engines_limpios() -> AsyncIterator[None]:
    """Cierra los engines al terminar cada test.

    pytest-asyncio abre un event loop por test. Un engine reutilizado entre dos
    loops arrastra conexiones del anterior, ya cerrado, y el sintoma —"Event
    loop is closed"— aparece en un test que no tiene nada que ver.

    `autouse` a proposito: acordarse de pedirlo es exactamente el error que este
    fixture existe para evitar.
    """
    yield
    await cerrar_engines()


@pytest.fixture
def tenant() -> uuid.UUID:
    """Un tenant nuevo por test.

    Nuevo y no fijo: dos tests que compartan tenant comparten filas, y el que
    corre segundo empieza a depender de lo que dejo el primero. Ese acoplamiento
    no se nota hasta que alguien corre la suite con `-k` y falla algo que no
    toco.
    """
    return uuid.uuid4()


@pytest.fixture
def otro_tenant() -> uuid.UUID:
    """El segundo tenant, para todo lo que se prueba de a dos."""
    return uuid.uuid4()


@pytest.fixture
async def sesion(tenant: uuid.UUID) -> AsyncIterator[AsyncSession]:
    """Sesion con el contexto de tenant puesto. La forma normal de tocar la base.

    Es la que corresponde a casi todo: si un test necesita la de plataforma, que
    lo diga pidiendola por nombre.
    """
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as abierta:
        yield abierta


@pytest.fixture
async def sesion_sin_tenant() -> AsyncIterator[AsyncSession]:
    """Sesion SIN contexto de tenant. La excepcion, y se nota al pedirla.

    Sobre tablas con RLS activo no devuelve filas, que es el comportamiento
    correcto (`RN-MT-06`). Sirve para comprobar justamente eso.

    OJO: no es la puerta de DDL. Para crear o alterar tablas esta
    `sesion_de_propietario` en `soporte.py` — ver su encabezado.
    """
    async with sesion_de_plataforma(dsn=DSN_APLICACION) as abierta:
        yield abierta


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    """Cliente contra el Redis de tests, cerrado al terminar."""
    cliente: Redis = Redis.from_url(URL_REDIS, decode_responses=True)
    try:
        yield cliente
    finally:
        await cliente.aclose()


@pytest.fixture(scope="session")
def base_migrada() -> None:
    """Aplica las migraciones una vez por corrida, con el rol PROPIETARIO.

    Es de SESION y no de modulo por un motivo concreto: antes de esto vivia en
    `test_migraciones.py` con alcance de modulo, y `test_tenant_isolation.py`
    dependia de que esa migracion ya hubiera corrido **por orden alfabetico de
    los archivos**. Funcionaba, pero por casualidad: renombrar un archivo o
    correr un solo test con `-k` rompia la suite por un motivo ilegible.

    Los tests que tocan tablas lo piden explicitamente y la dependencia queda
    escrita donde se puede leer.

    Corre con la URL del propietario porque crear tablas y politicas es
    justamente lo que el rol de aplicacion no puede hacer (ADR-020).
    """
    resultado = alembic("upgrade", "head")
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
