"""El servicio de stock, sin pasar por HTTP — C-14.

POR QUE EXISTE ADEMAS DE `test_stock_router.py`
────────────────────────────────────────────────
El del router prueba el AISLAMIENTO sobre HTTP, que es lo que mas importa. Este
prueba las reglas de negocio contra la sesion directamente, y por dos motivos:

  1. Un fallo acá señala la regla; el mismo fallo por HTTP señala "500 en POST
     /vehicles" y hay que bajar tres capas para encontrarlo.
  2. `TestClient` corre el endpoint en su propio portal, y coverage no traza lo
     que pasa ahi dentro. El servicio figuraba al 57 % con todos sus caminos
     ejercitados por el router — un numero que miente en la direccion peligrosa:
     hace creer que falta cobertura donde no falta, y la esconde donde si.

Sin mocks de base de datos (regla dura 8).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text

from app.db.session import sesion_de_tenant
from app.modules.stock.schemas import (
    EstadoDeVehiculo,
    FiltrosDeBusqueda,
    VehiculoCambioDeEstado,
    VehiculoCrear,
)
from app.modules.stock.service import (
    StockService,
    TransicionInvalida,
    VehiculoDuplicado,
    VehiculoNoEncontrado,
)

from .soporte import DSN_APLICACION, sesion_de_propietario

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(base_migrada: None) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Una agencia con sucursal, y una marca y modelo del catalogo.

    El tenant y la sucursal se crean con el rol PROPIETARIO: son precondicion,
    no lo que se prueba, y `tenants` no tiene politica RLS.
    """
    tenant_id, branch_id = uuid.uuid4(), uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO tenants (id, name, slug, cuit, billing_email, status) "
                "VALUES (:id, :n, :s, :c, 'f@example.com', 'active')"
            ),
            {
                "id": tenant_id,
                "n": "Agencia",
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
        marca, modelo = (
            await sesion.execute(text("SELECT brand_id, id FROM vehicle_models LIMIT 1"))
        ).one()
    return tenant_id, branch_id, uuid.UUID(str(marca)), uuid.UUID(str(modelo))


def _datos(
    branch_id: uuid.UUID, marca: uuid.UUID, modelo: uuid.UUID, **extra: Any
) -> VehiculoCrear:
    """Los defaults se mezclan en un dict, no se pasan como argumentos fijos.

    Con `year=2021` puesto aparte, un test que quisiera otro año le pasaba el
    valor dos veces y Python levantaba `got multiple values`. Mezclar primero
    deja que `extra` pise cualquier default sin excepciones.
    """
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


# ── Alta ────────────────────────────────────────────────────────────────────


async def test_un_vehiculo_nace_en_preparacion(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """`RN-ST-04`."""
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        creado = await StockService(sesion, tenant).crear(
            _datos(sucursal, marca, modelo, domain_plate="AA100AA")
        )

        assert creado.status == EstadoDeVehiculo.EN_PREPARACION.value
        assert creado.tenant_id == tenant


async def test_el_dominio_duplicado_se_rechaza(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """`RN-ST-01`, y el mensaje NO repite el dominio (Ley 25.326)."""
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="AA200AA"))

        with pytest.raises(VehiculoDuplicado) as fallo:
            await servicio.crear(
                _datos(
                    sucursal,
                    marca,
                    modelo,
                    domain_plate="AA200AA",
                    chassis_number="9BWZZZ377VA999999",
                )
            )

        assert "AA200AA" not in str(fallo.value)


# ── Lectura y aislamiento ───────────────────────────────────────────────────


async def test_un_id_de_otra_agencia_no_se_encuentra(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """El servicio acota por tenant aunque el id exista."""
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        creado = await StockService(sesion, tenant).crear(
            _datos(sucursal, marca, modelo, domain_plate="AA300AA")
        )
        ajeno_id = creado.id

    otro_tenant = uuid.uuid4()
    async with sesion_de_tenant(otro_tenant, dsn=DSN_APLICACION) as sesion:
        with pytest.raises(VehiculoNoEncontrado):
            await StockService(sesion, otro_tenant).obtener(ajeno_id)


async def test_un_id_inexistente_no_se_encuentra(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    tenant, _, _, _ = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        with pytest.raises(VehiculoNoEncontrado):
            await StockService(sesion, tenant).obtener(uuid.uuid4())


# ── Filtros ─────────────────────────────────────────────────────────────────


async def test_cada_filtro_acota(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """Los ocho filtros, ejercitados de a uno.

    Se prueban juntos y no en ocho tests porque comparten el mismo escenario de
    dos vehiculos: partirlo obligaria a recrearlo ocho veces contra la base sin
    agregar una sola afirmacion.
    """
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        viejo = await servicio.crear(
            _datos(sucursal, marca, modelo, domain_plate="AA400AA", year=2015)
        )
        nuevo = await servicio.crear(
            _datos(
                sucursal,
                marca,
                modelo,
                domain_plate="AA500AA",
                chassis_number="1BWZZZ377VA111111",
                year=2023,
                price_ars=Decimal("40000000.00"),
            )
        )

        async def ids(**filtros: Any) -> set[uuid.UUID]:
            return {v.id for v in await servicio.listar(FiltrosDeBusqueda(**filtros))}

        assert await ids() == {viejo.id, nuevo.id}
        assert await ids(year_from=2020) == {nuevo.id}
        assert await ids(year_to=2018) == {viejo.id}
        assert await ids(price_from=Decimal("30000000")) == {nuevo.id}
        assert await ids(price_to=Decimal("30000000")) == {viejo.id}
        assert await ids(brand_id=marca) == {viejo.id, nuevo.id}
        assert await ids(model_id=modelo) == {viejo.id, nuevo.id}
        assert await ids(branch_id=sucursal) == {viejo.id, nuevo.id}
        assert await ids(brand_id=uuid.uuid4()) == set()


# ── Estados y baja ──────────────────────────────────────────────────────────


async def test_la_transicion_permitida_se_aplica(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="AA600AA"))

        actualizado = await servicio.cambiar_estado(
            creado.id, VehiculoCambioDeEstado(status=EstadoDeVehiculo.DISPONIBLE)
        )

        assert actualizado.status == EstadoDeVehiculo.DISPONIBLE.value


async def test_vender_deja_la_fecha_de_venta(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """`RN-ST-06`. Se llega por el camino legal: preparacion → disponible →
    reservado → vendido."""
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="AA700AA"))

        for estado in (
            EstadoDeVehiculo.DISPONIBLE,
            EstadoDeVehiculo.RESERVADO,
        ):
            await servicio.cambiar_estado(creado.id, VehiculoCambioDeEstado(status=estado))

        vendido = await servicio.cambiar_estado(
            creado.id,
            VehiculoCambioDeEstado(status=EstadoDeVehiculo.VENDIDO, reason="contado"),
        )

        assert vendido.sold_at is not None


async def test_una_transicion_prohibida_levanta(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """`RN-ST-05`: denegar por defecto."""
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="AA800AA"))

        with pytest.raises(TransicionInvalida, match="in_preparation"):
            await servicio.cambiar_estado(
                creado.id,
                VehiculoCambioDeEstado(status=EstadoDeVehiculo.VENDIDO, reason="x"),
            )


async def test_dar_de_baja_no_borra_la_fila(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """Regla dura 3: borrado logico. La fila sobrevive con `deleted_at`."""
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="AA900AA"))
        vehiculo_id = creado.id

        await servicio.dar_de_baja(vehiculo_id)

        with pytest.raises(VehiculoNoEncontrado):
            await servicio.obtener(vehiculo_id)

    # La fila sigue ahi, con su marca de baja.
    async with sesion_de_propietario() as sesion:
        borrado_en = await sesion.scalar(
            text("SELECT deleted_at FROM vehicles WHERE id = :id"), {"id": vehiculo_id}
        )

    assert borrado_en is not None
