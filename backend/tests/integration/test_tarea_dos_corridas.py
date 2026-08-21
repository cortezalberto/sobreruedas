"""Dos importaciones seguidas, cada una en su event loop — C-17.

EL BUG QUE ESTE ARCHIVO EXISTE PARA QUE NO VUELVA
───────────────────────────────────────────────────
La primera importacion contra el entorno local anduvo perfecto. La segunda
murio con:

    RuntimeError: got Future <Future pending> attached to a different loop

`app/db/session.py` cachea el engine por DSN en un diccionario de MODULO, que
sobrevive al `asyncio.run()`. La primera tarea lo crea con conexiones asyncpg
atadas a su loop; ese loop muere al terminar. La segunda abre un loop nuevo,
recibe el engine cacheado con conexiones del loop muerto, y revienta con un
mensaje que no nombra ni a Celery ni a la importacion.

POR QUE NINGUN TEST LO AGARRABA
─────────────────────────────────
Porque **todos comparten un solo event loop**. La condicion que dispara el bug
—dos loops, un engine cacheado— no existe en la suite: la crea `asyncio.run()`,
que solo aparece dentro de la tarea de Celery.

Por eso este test entra por `importar_stock.apply()` y no por
`ejecutar_importacion()`: lo que se prueba no es la importacion, es el CICLO DE
VIDA del loop. Llamar a la corrutina directamente lo probaria todo menos eso.

⚠️ EL TEST ES SINCRONICO, y tiene que serlo: `asyncio.run()` no se puede llamar
desde adentro de un loop, y un test `async` ya corre en uno. Cada bloque de
preparacion y de verificacion abre el suyo con `_correr()`, igual que la tarea.

⚠️ Es de integracion y no de unidad aunque hable de loops: hace falta
PostgreSQL de verdad, porque el engine que se recicla mal es el suyo.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

import pytest
from sqlalchemy import func, select, text

from app.core.tasks import importar_stock
from app.db.session import cerrar_engines, sesion_de_tenant
from app.modules.stock.importacion_modelo import EstadoDeImportacion
from app.modules.stock.importacion_servicio import ImportService
from app.modules.stock.models import Vehicle

from .soporte import (
    DSN_APLICACION,
    agencia_con_sucursal,
    reponer_entorno,
    sesion_de_propietario,
)

pytestmark = pytest.mark.integration

CABECERA = (
    "marca,modelo,anio,kilometros,color,combustible,transmision,"
    "carroceria,precio_ars,dominio,sucursal"
)


@pytest.fixture(autouse=True)
def _entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    reponer_entorno(monkeypatch, dsn=DSN_APLICACION)


def _correr[T](trabajo: Coroutine[Any, Any, T]) -> T:
    """Un event loop propio, y los engines cerrados al salir.

    Es lo mismo que hace la tarea de Celery, y por el mismo motivo: sin el
    cierre, el proximo `asyncio.run()` de este archivo heredaria conexiones del
    loop que acaba de morir.
    """

    async def envuelto() -> T:
        try:
            return await trabajo
        finally:
            await cerrar_engines()

    return asyncio.run(envuelto())


def test_la_segunda_importacion_tambien_funciona(base_migrada: None) -> None:
    """Dos tareas, dos `asyncio.run()`, dos loops. Las dos tienen que importar.

    Si el `finally` que cierra los engines desaparece, la primera pasa y la
    segunda muere — que es exactamente como se descubrio.
    """
    marca, modelo, tenant_id = _correr(_agencia())

    def csv(dominio: str) -> bytes:
        fila = f"{marca},{modelo},2021,40000,Blanco,diesel,manual,pickup,25000000.00,{dominio},"
        return (CABECERA + "\r\n" + fila + "\r\n").encode("utf-8")

    # ⚠️ LAS DOS CORRIDAS SE REGISTRAN JUNTAS, EN UN SOLO LOOP, Y RECIEN DESPUES
    # se ejecutan las dos tareas SEGUIDAS. El orden importa para que el test
    # sirva: intercalar registro y ejecucion hacia que `_correr` cerrara los
    # engines entre una tarea y la otra —o sea, el test hacia el trabajo que
    # deberia hacer el codigo— y pasaba igual con la correccion sacada.
    #
    # Asi, entre el `apply()` de la primera y el de la segunda no hay nada: es
    # exactamente lo que pasa en el worker cuando llegan dos importaciones.
    corridas = _correr(_registrar_las_dos(tenant_id, csv))

    for corrida_id in corridas:
        # `.apply()` corre la tarea en este proceso, con su `asyncio.run()`
        # adentro. Es lo que crea el loop nuevo, o sea la condicion del bug.
        importar_stock.apply(args=[str(corrida_id), str(tenant_id)])

    estados, total = _correr(_verificar(tenant_id, corridas))

    assert estados == [EstadoDeImportacion.COMPLETADA.value] * 2
    assert total == 2


async def _agencia() -> tuple[str, str, uuid.UUID]:
    tenant_id, _ = await agencia_con_sucursal()
    async with sesion_de_propietario() as sesion:
        marca, modelo = (
            await sesion.execute(
                text(
                    "SELECT b.name, m.name FROM vehicle_models m "
                    "JOIN vehicle_brands b ON b.id = m.brand_id ORDER BY m.name LIMIT 1"
                )
            )
        ).one()
    return str(marca), str(modelo), tenant_id


async def _registrar_las_dos(tenant_id: uuid.UUID, csv: Callable[[str], bytes]) -> list[uuid.UUID]:
    corridas = []
    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        servicio = ImportService(sesion, tenant_id)
        for dominio in ("AH100AA", "AH200AA"):
            corrida = await servicio.registrar(
                nombre_archivo=f"{dominio}.csv", contenido=csv(dominio), creado_por=None
            )
            corridas.append(corrida.id)
    return corridas


async def _verificar(tenant_id: uuid.UUID, corridas: list[uuid.UUID]) -> tuple[list[str], int]:
    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        servicio = ImportService(sesion, tenant_id)
        estados = [(await servicio.obtener(c)).status for c in corridas]
        total = (await sesion.execute(select(func.count()).select_from(Vehicle))).scalar_one()
    return estados, int(total)
