"""La cuota de vehiculos del plan, que hasta hoy no se aplicaba — C-14 / C-17.

QUE ENCONTRO ESTE ARCHIVO
──────────────────────────
`PlanLimitsService` tiene `assert_can_add_vehicle` desde C-04 y **nadie lo
llamaba**. `StockService.crear` insertaba sin preguntar, asi que una agencia con
plan Starter —80 vehiculos— podia cargar 5.000 sin que nada se quejara.

El diseño de `limits.py` preveia exactamente este olvido y falla cerrado: pedir
la cuota de un recurso sin contador registrado LEVANTA. Pero la red solo agarra
al que se cae encima: si nadie pregunta, no hay nada que fallar. C-14 creo
`vehicles`, no registro `contar_vehiculos` y no llamo a la verificacion — y el
sistema quedo sin techo de facturacion, en silencio, con los tests verdes.

Se descubrio al escribir C-17, porque el import necesita la MISMA cuota
aplicada al total de la planilla y no habia contra que aplicarla.

Sin mocks de base de datos (regla dura 8).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text

from app.core.errors import PlanQuotaExceeded
from app.db.session import sesion_de_tenant
from app.modules.stock.schemas import FiltrosDeBusqueda, VehiculoCrear
from app.modules.stock.service import StockService

from .soporte import DSN_APLICACION, sesion_de_propietario

pytestmark = pytest.mark.integration


@pytest.fixture
async def catalogo(base_migrada: None) -> tuple[uuid.UUID, uuid.UUID]:
    async with sesion_de_propietario() as sesion:
        fila = (await sesion.execute(text("SELECT brand_id, id FROM vehicle_models LIMIT 1"))).one()
    return uuid.UUID(str(fila[0])), uuid.UUID(str(fila[1]))


@pytest.fixture
async def agencia_con_plan() -> (
    AsyncIterator[Callable[[int], Awaitable[tuple[uuid.UUID, uuid.UUID]]]]
):
    """Fabrica de agencias con plan a medida, que LIMPIA lo que creo.

    ⚠️ La limpieza no es prolijidad. `plans` es un catalogo GLOBAL —no lleva
    `tenant_id`, no tiene RLS— y la suite corre contra una base compartida:
    dejar un plan de prueba tirado rompe a `test_planes_router.py` y a otros
    tres, que afirman que el catalogo tiene exactamente los tres sembrados. La
    primera version de este archivo no limpiaba y los rompio.

    Los tenants y sus vehiculos se podrian dejar —el aislamiento hace que nadie
    los vea— pero se borran igual: son los que sostienen la FK al plan.
    """
    creados: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def fabricar(maximo: int) -> tuple[uuid.UUID, uuid.UUID]:
        tenant_id, branch_id, plan_id = await _crear(maximo)
        creados.append((tenant_id, plan_id))
        return tenant_id, branch_id

    yield fabricar

    # DELETE fisico y no borrado logico: es andamiaje de test, no dato del
    # dominio. La regla dura 3 gobierna a la aplicacion, no a la limpieza.
    async with sesion_de_propietario() as sesion:
        for tenant_id, plan_id in creados:
            # Escrito a mano y en orden de dependencia. Un bucle sobre nombres de
            # tabla armaria el SQL por interpolacion, que es justo lo que
            # prohibe la regla dura 9 — y la prohibicion no tiene una excepcion
            # para "es un test".
            # `imports` tambien apunta a `tenants`. Va PRIMERO por eso: la FK
            # no la contempla `ON DELETE`, asi que el orden es la unica garantia.
            await sesion.execute(text("DELETE FROM imports WHERE tenant_id = :t"), {"t": tenant_id})
            await sesion.execute(
                text("DELETE FROM vehicles WHERE tenant_id = :t"), {"t": tenant_id}
            )
            await sesion.execute(
                text("DELETE FROM branches WHERE tenant_id = :t"), {"t": tenant_id}
            )
            await sesion.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant_id})
            await sesion.execute(text("DELETE FROM plans WHERE id = :p"), {"p": plan_id})


async def _crear(maximo: int) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Una agencia con un plan a medida, para no depender del seed.

    Starter permite 80 vehiculos y probar el techo exigiria cargar 80 filas por
    test. Un plan de dos hace la misma afirmacion en dos INSERTs.
    """
    tenant_id, branch_id, plan_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO plans (id, code, name, price_ars, max_users, max_vehicles, "
                "max_branches, max_whatsapp_messages_month, modules) "
                "VALUES (:id, :c, 'De prueba', 1000, 5, :m, 5, 100, '[]'::jsonb)"
            ),
            {"id": plan_id, "c": f"prueba-{plan_id.hex[:8]}", "m": maximo},
        )
        await sesion.execute(
            text(
                "INSERT INTO tenants (id, name, slug, cuit, billing_email, status, plan_id) "
                "VALUES (:id, 'Agencia', :s, :c, 'f@example.com', 'active', :p)"
            ),
            {
                "id": tenant_id,
                "s": f"ag-{tenant_id.hex[:8]}",
                "c": f"30{tenant_id.int % 10**9:09d}0"[:11],
                "p": plan_id,
            },
        )
        await sesion.execute(
            text(
                "INSERT INTO branches (id, tenant_id, name, city, province) "
                "VALUES (:id, :t, 'Central', 'Mendoza', 'Mendoza')"
            ),
            {"id": branch_id, "t": tenant_id},
        )
    return tenant_id, branch_id, plan_id


def _datos(
    sucursal: uuid.UUID, catalogo: tuple[uuid.UUID, uuid.UUID], **extra: Any
) -> VehiculoCrear:
    marca, modelo = catalogo
    campos: dict[str, Any] = {
        "branch_id": sucursal,
        "brand_id": marca,
        "model_id": modelo,
        "year": 2021,
        "mileage_km": 30_000,
        "color": "Blanco",
        "fuel_type": "diesel",
        "transmission": "manual",
        "body_type": "pickup",
        "price_ars": Decimal("25000000.00"),
    }
    return VehiculoCrear(**{**campos, **extra})


async def test_el_alta_de_a_uno_respeta_el_techo_del_plan(
    catalogo: tuple[uuid.UUID, uuid.UUID],
    agencia_con_plan: Callable[[int], Awaitable[tuple[uuid.UUID, uuid.UUID]]],
) -> None:
    """Plan de 2: el tercero no entra. 402, no 403."""
    tenant, sucursal = await agencia_con_plan(2)

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        await servicio.crear(_datos(sucursal, catalogo, domain_plate="AB100AA"))
        await servicio.crear(_datos(sucursal, catalogo, domain_plate="AB200AA"))

        with pytest.raises(PlanQuotaExceeded) as fallo:
            await servicio.crear(_datos(sucursal, catalogo, domain_plate="AB300AA"))

    assert (fallo.value.recurso, fallo.value.limite, fallo.value.usados) == ("vehicles", 2, 2)


async def test_un_vehiculo_vendido_no_consume_cuota(
    catalogo: tuple[uuid.UUID, uuid.UUID],
    agencia_con_plan: Callable[[int], Awaitable[tuple[uuid.UUID, uuid.UUID]]],
) -> None:
    """`assert_can_add_vehicle` lo promete en su docstring desde C-04 y nunca
    se habia ejercitado: el limite es de vehiculos EN STOCK.

    Si vender consumiera cuota, el plan se agotaria solo con el tiempo y el
    cliente que mas vende seria el primero en quedarse sin lugar.
    """
    tenant, sucursal = await agencia_con_plan(1)

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        vendido = await servicio.crear(_datos(sucursal, catalogo, domain_plate="AB400AA"))

    # Se marca vendido por la puerta de servicio: llegar por transiciones
    # legales es lo que prueba `test_stock_service.py`, acá estorbaria.
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text("UPDATE vehicles SET status = 'sold' WHERE id = :id"), {"id": vendido.id}
        )

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        otro = await StockService(sesion, tenant).crear(
            _datos(sucursal, catalogo, domain_plate="AB500AA")
        )

    assert otro.id is not None


async def test_un_vehiculo_dado_de_baja_no_consume_cuota(
    catalogo: tuple[uuid.UUID, uuid.UUID],
    agencia_con_plan: Callable[[int], Awaitable[tuple[uuid.UUID, uuid.UUID]]],
) -> None:
    tenant, sucursal = await agencia_con_plan(1)

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        primero = await servicio.crear(_datos(sucursal, catalogo, domain_plate="AB600AA"))
        await servicio.dar_de_baja(primero.id)

        otro = await servicio.crear(_datos(sucursal, catalogo, domain_plate="AB700AA"))

    assert otro.id is not None


async def test_un_tenant_sin_plan_no_tiene_techo(
    catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """El trial promete "todas las features de Pro por 14 dias".

    Un trial que no deja cargar nada no es un trial — `_limite_del_plan` trata
    `plan_id IS NULL` como sin techo y NO como cero.
    """
    tenant_id, branch_id = uuid.uuid4(), uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO tenants (id, name, slug, cuit, billing_email, status) "
                "VALUES (:id, 'Trial', :s, :c, 'f@example.com', 'trial')"
            ),
            {
                "id": tenant_id,
                "s": f"ag-{tenant_id.hex[:8]}",
                "c": f"30{tenant_id.int % 10**9:09d}0"[:11],
            },
        )
        await sesion.execute(
            text(
                "INSERT INTO branches (id, tenant_id, name, city, province) "
                "VALUES (:id, :t, 'Central', 'Mendoza', 'Mendoza')"
            ),
            {"id": branch_id, "t": tenant_id},
        )

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant_id)
        for n in range(3):
            await servicio.crear(_datos(branch_id, catalogo, domain_plate=f"AC{n}00AA"))

        assert len(await servicio.listar(FiltrosDeBusqueda())) == 3
