"""Los endpoints de agencia llamados como funciones, sin HTTP — C-05 (parcial).

POR QUE EXISTE ADEMAS DE `test_agencia_router.py`
──────────────────────────────────────────────────
Mismo motivo que `test_stock_service.py`, y conviene dejarlo escrito porque es
contraintuitivo: **`TestClient` corre el endpoint en su propio portal y
`coverage` no traza lo que pasa ahi dentro**. Con los 12 tests de HTTP verdes y
todos los caminos ejercitados, `router_agencia.py` figuraba al 62 %.

Ese numero no dice "falta probar": dice "la herramienta no ve". Y miente en la
direccion peligrosa — si mañana alguien agrega una rama de verdad sin probar,
queda escondida entre las trece lineas que ya figuraban sin cubrir.

Estos tests llaman a las corrutinas del router directamente. Se puede porque
`SesionDeTenant` es, en tiempo de ejecucion, una `AsyncSession` y nada mas: el
`Depends` lo resuelve FastAPI, no el anotado. Lo que la dependency hace —abrir
la sesion del tenant y dejar el id en `.info`— se replica aca en dos lineas, y
esas dos lineas SI las prueba el archivo de HTTP.

Sin mocks de base de datos (regla dura 8).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, PlanQuotaExceeded
from app.db.session import sesion_de_tenant
from app.modules.tenancy.router_agencia import (
    crear_sucursal,
    dar_de_baja_sucursal,
    listar_sucursales,
    mi_agencia,
    obtener_sucursal,
)
from app.modules.tenancy.schemas import SucursalCrear
from app.modules.tenancy.service import TenancyService

from .soporte import DSN_APLICACION, sesion_de_propietario

pytestmark = pytest.mark.integration


@asynccontextmanager
async def _sesion(tenant_id: uuid.UUID) -> AsyncIterator[AsyncSession]:
    """Lo mismo que `sesion_del_tenant_actual`, sin FastAPI en el medio.

    Si esas dos lineas se separan alguna vez de la dependency real, los tests
    de `test_agencia_router.py` —que si pasan por ella— lo detectan.
    """
    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        sesion.info["tenant_id"] = tenant_id
        yield sesion


async def _agencia(*, plan: str | None = None) -> tuple[uuid.UUID, uuid.UUID]:
    tenant_id, branch_id = uuid.uuid4(), uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        plan_id = None
        if plan is not None:
            plan_id = await sesion.scalar(text("SELECT id FROM plans WHERE code = :c"), {"c": plan})
        await sesion.execute(
            text(
                "INSERT INTO tenants (id, name, slug, cuit, billing_email, status, plan_id) "
                "VALUES (:id, :n, :s, :c, 'f@example.com', 'active', :p)"
            ),
            {
                "id": tenant_id,
                "n": f"Agencia {tenant_id.hex[:6]}",
                "s": f"agencia-{tenant_id.hex[:8]}",
                "c": f"30{tenant_id.int % 10**9:09d}0"[:11],
                "p": plan_id,
            },
        )
        await sesion.execute(
            text(
                "INSERT INTO branches (id, tenant_id, name, city, province) "
                "VALUES (:id, :t, 'Casa central', 'Mendoza', 'Mendoza')"
            ),
            {"id": branch_id, "t": tenant_id},
        )
    return tenant_id, branch_id


_ALTA = SucursalCrear(name="Sucursal Norte", city="Godoy Cruz", province="Mendoza")


async def test_mi_agencia_lee_el_tenant_de_la_sesion(base_migrada: None) -> None:
    tenant_id, _ = await _agencia()

    async with _sesion(tenant_id) as sesion:
        agencia = await mi_agencia(sesion)

    assert agencia.id == tenant_id


async def test_mi_agencia_levanta_404_si_el_tenant_no_esta(base_migrada: None) -> None:
    """Token de otro entorno contra esta base. 404, no un `None` que reviente
    despues al serializar."""
    async with _sesion(uuid.uuid4()) as sesion:
        with pytest.raises(HTTPException) as fallo:
            await mi_agencia(sesion)

    assert fallo.value.status_code == 404


async def test_listar_y_obtener_devuelven_lo_de_la_agencia(base_migrada: None) -> None:
    tenant_id, sucursal_id = await _agencia()

    async with _sesion(tenant_id) as sesion:
        listadas = await listar_sucursales(sesion)
        una = await obtener_sucursal(sucursal_id, sesion)

    assert [s.id for s in listadas] == [sucursal_id]
    assert una.tenant_id == tenant_id


async def test_obtener_levanta_404_con_un_id_que_no_es_de_la_agencia(base_migrada: None) -> None:
    tenant_id, _ = await _agencia()
    _, sucursal_ajena = await _agencia()

    async with _sesion(tenant_id) as sesion:
        with pytest.raises(HTTPException) as fallo:
            await obtener_sucursal(sucursal_ajena, sesion)

    assert fallo.value.status_code == 404


async def test_crear_pone_la_sucursal_en_la_agencia_de_la_sesion(base_migrada: None) -> None:
    tenant_id, _ = await _agencia()

    async with _sesion(tenant_id) as sesion:
        creada = await crear_sucursal(_ALTA, sesion)

    assert creada.tenant_id == tenant_id


async def test_crear_levanta_402_al_tocar_el_techo_del_plan(base_migrada: None) -> None:
    """Starter permite una sucursal y la agencia ya la tiene.

    El error viaja **sin traducir** desde el router: el handler global lo
    convierte en 402 con `resource`/`limit`/`used`. Envolverlo aca lo
    degradaria a un 422 sin esos tres campos.
    """
    tenant_id, _ = await _agencia(plan="starter")

    async with _sesion(tenant_id) as sesion:
        with pytest.raises(PlanQuotaExceeded) as fallo:
            await crear_sucursal(_ALTA, sesion)

    assert (fallo.value.recurso, fallo.value.limite, fallo.value.usados) == ("branches", 1, 1)


async def test_dar_de_baja_marca_la_fila_sin_borrarla(base_migrada: None) -> None:
    tenant_id, sucursal_id = await _agencia()

    async with _sesion(tenant_id) as sesion:
        dada_de_baja = await dar_de_baja_sucursal(sucursal_id, sesion)
        assert dada_de_baja.id == sucursal_id

    async with sesion_de_propietario() as sesion:
        borrada_en = await sesion.scalar(
            text("SELECT deleted_at FROM branches WHERE id = :id"), {"id": sucursal_id}
        )

    assert borrada_en is not None


async def test_dar_de_baja_traduce_solo_su_propio_error_a_404(base_migrada: None) -> None:
    """Las DOS ramas del `except`, y la segunda importa mas que la primera.

    Traducir es facil; traducir DE MAS es el error caro. Un `except DomainError`
    que devolviera 404 ante cualquier codigo convertiria una regla de negocio
    incumplida en "no existe", y quien lo consuma va a reintentar con otro id un
    problema que no es de id.

    Ese segundo camino no se puede provocar con datos —hoy el servicio solo
    levanta `sucursal_inexistente` en esta operacion— asi que se fuerza el
    error ajeno. No es un doble de base de datos (regla dura 8): la base sigue
    siendo real y lo que se sustituye es una regla de dominio, para llegar a
    una rama que los datos no alcanzan.
    """
    tenant_id, sucursal_id = await _agencia()

    async with _sesion(tenant_id) as sesion:
        with pytest.raises(HTTPException) as traducido:
            await dar_de_baja_sucursal(uuid.uuid4(), sesion)
        assert traducido.value.status_code == 404

        async def otro_error(*_: object, **__: object) -> None:
            raise DomainError("la agencia esta suspendida", code="estado_invalido")

        with pytest.MonkeyPatch.context() as parche:
            parche.setattr(TenancyService, "dar_de_baja_sucursal", otro_error)
            with pytest.raises(DomainError) as intacto:
                await dar_de_baja_sucursal(sucursal_id, sesion)

    assert intacto.value.code == "estado_invalido"
