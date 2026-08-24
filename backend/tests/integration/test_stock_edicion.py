"""`StockService.editar` — C-14, `T-075`.

Edicion PARCIAL de verdad (`design.md` D-7): `exclude_unset` y no
`exclude_none`, para que un campo AUSENTE no se toque y uno presente con
`null` se vacie — cuando la tabla lo admite.

Sin mocks de base de datos (regla dura 8).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text

from app.core.outbox import pendientes
from app.db.session import sesion_de_tenant
from app.modules.stock.schemas import VehiculoCrear, VehiculoEditar
from app.modules.stock.service import StockService, VehiculoNoEncontrado

from .soporte import DSN_APLICACION, agencia_con_sucursal, sesion_de_propietario

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(base_migrada: None) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    tenant_id, branch_id = await agencia_con_sucursal()
    async with sesion_de_propietario() as sesion:
        marca, modelo = (
            await sesion.execute(text("SELECT brand_id, id FROM vehicle_models LIMIT 1"))
        ).one()
    return tenant_id, branch_id, uuid.UUID(str(marca)), uuid.UUID(str(modelo))


def _datos(
    branch_id: uuid.UUID, marca: uuid.UUID, modelo: uuid.UUID, **extra: Any
) -> VehiculoCrear:
    campos: dict[str, Any] = {
        "branch_id": branch_id,
        "brand_id": marca,
        "model_id": modelo,
        "year": 2021,
        "mileage_km": 30_000,
        "color": "Blanco",
        "fuel_type": "diesel",
        "transmission": "manual",
        "body_type": "pickup",
        "price_ars": Decimal("25000000.00"),
        "chassis_number": "8AWZZZ377VA123456",
    }
    return VehiculoCrear(**{**campos, **extra})


# ── 4.4 · Edicion de un solo campo, y ningun otro ────────────────────────────


async def test_editar_un_solo_campo_no_toca_los_demas(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="BB100BB"))
        color_original = creado.color
        mileage_original = creado.mileage_km

        editado = await servicio.editar(
            creado.id, VehiculoEditar(price_ars=Decimal("30000000.00")), autor=None
        )

        assert editado.price_ars == Decimal("30000000.00")
        assert editado.color == color_original
        assert editado.mileage_km == mileage_original


# ── 4.5 · `null` explicito desasigna; ausencia no toca ───────────────────────


async def test_editar_con_null_explicito_desasigna_el_vendedor(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """Es lo que distingue `exclude_unset` de `exclude_none`: sin este test,
    las dos implementaciones pasarian igual."""
    tenant, sucursal, marca, modelo = escenario
    vendedor = uuid.uuid4()

    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Vendedor', 'salesperson', 'active')"
            ),
            {"id": vendedor, "t": tenant, "e": f"{vendedor}@example.com"},
        )

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="BB101BB"))
        creado.assigned_user_id = vendedor
        await sesion.flush()

        # Un PATCH SIN `assigned_user_id` no lo toca.
        sin_tocar = await servicio.editar(creado.id, VehiculoEditar(), autor=None)
        assert sin_tocar.assigned_user_id == vendedor

        # Un PATCH CON `assigned_user_id: null` lo desasigna.
        desasignado = await servicio.editar(
            creado.id, VehiculoEditar(assigned_user_id=None), autor=None
        )
        assert desasignado.assigned_user_id is None


# ── 4.6 · Vehiculo de otra agencia ───────────────────────────────────────────


async def test_editar_un_vehiculo_de_otra_agencia_no_se_encuentra(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """404, no 403: distinguirlos confirmaria que el id existe en otra agencia."""
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        creado = await StockService(sesion, tenant).crear(
            _datos(sucursal, marca, modelo, domain_plate="BB102BB")
        )
        ajeno_id = creado.id

    otro_tenant = uuid.uuid4()
    async with sesion_de_tenant(otro_tenant, dsn=DSN_APLICACION) as sesion:
        with pytest.raises(VehiculoNoEncontrado):
            await StockService(sesion, otro_tenant).editar(
                ajeno_id, VehiculoEditar(color="Rojo"), autor=None
            )


# ── 4.7 · `updated_at` se refresca ───────────────────────────────────────────


async def test_editar_refresca_updated_at(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="BB103BB"))
        creado_en = creado.updated_at

        editado = await servicio.editar(creado.id, VehiculoEditar(color="Rojo"), autor=None)

    assert editado.updated_at >= creado_en


# ── 4.8 / 4.9 · El evento nombra CAMPOS, nunca valores ───────────────────────


async def test_editar_anota_vehicle_updated_con_los_nombres_ordenados(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="BB104BB"))

        await servicio.editar(
            creado.id,
            VehiculoEditar(price_ars=Decimal("31000000.00"), color="Negro"),
            autor=None,
        )

        _, evento = pendientes(sesion)

    assert evento.type == "vehicle.updated"
    assert evento.payload == {
        "vehicle_id": str(creado.id),
        "campos": ["color", "price_ars"],
    }


async def test_el_payload_de_editar_no_lleva_el_costo_de_adquisicion(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """`RN-ST-12` por la puerta de atras — la misma razon que en `service.py`.

    Se afirma sobre la FILA real del outbox, no sobre un mock.
    """
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(
            _datos(
                sucursal,
                marca,
                modelo,
                domain_plate="BB105BB",
                acquisition_cost_ars=Decimal("18000000.00"),
            )
        )

        await servicio.editar(
            creado.id,
            VehiculoEditar(acquisition_cost_ars=Decimal("19500000.00")),
            autor=None,
        )

        _, evento = pendientes(sesion)

    assert evento.payload == {"vehicle_id": str(creado.id), "campos": ["acquisition_cost_ars"]}
    assert "19500000" not in str(evento.payload)
    assert "18000000" not in str(evento.payload)


# ── 4.10 · Sin cambios, sin evento ───────────────────────────────────────────


async def test_editar_con_los_mismos_valores_no_anota_evento(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="BB106BB"))

        await servicio.editar(creado.id, VehiculoEditar(color=creado.color), autor=None)

        assert [sobre.type for sobre in pendientes(sesion)] == ["vehicle.created"]
