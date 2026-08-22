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

from app.core.outbox import pendientes
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

from .soporte import DSN_APLICACION, agencia_con_sucursal, sesion_de_propietario

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(base_migrada: None) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Una agencia con sucursal, y una marca y modelo del catalogo.

    El tenant y la sucursal se crean con el rol PROPIETARIO: son precondicion,
    no lo que se prueba, y `tenants` no tiene politica RLS.
    """
    tenant_id, branch_id = await agencia_con_sucursal()
    async with sesion_de_propietario() as sesion:
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


# ── Eventos de dominio (`ADR-036`) ───────────────────────────────────────────
#
# Se prueba lo que el SERVICIO anota, no lo que sale a Redis: el drenaje tiene su
# propio archivo (`test_outbox.py`) y repetirlo acá seria probar dos veces lo
# mismo y una sola vez lo que a este archivo le toca — que cada mutacion deje su
# hecho, con el contenido correcto.


async def test_el_alta_anota_vehicle_created(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        creado = await StockService(sesion, tenant).crear(
            _datos(sucursal, marca, modelo, domain_plate="AA200AA")
        )

        (sobre,) = pendientes(sesion)
        assert sobre.type == "vehicle.created"
        assert sobre.tenant_id == tenant
        assert sobre.payload == {
            "vehicle_id": str(creado.id),
            "status": EstadoDeVehiculo.EN_PREPARACION.value,
        }


async def test_el_id_del_evento_de_alta_no_es_nulo(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """El `flush` va antes del registro, y esto es lo que lo fija.

    El id lo asigna la base. Registrar el evento antes del `flush` anotaria
    `None` — un evento con `vehicle_id: "None"` que ningun consumidor podria
    resolver, y que en una revision se lee igual de bien que el correcto.
    """
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        await StockService(sesion, tenant).crear(
            _datos(sucursal, marca, modelo, domain_plate="AA201AA")
        )

        (sobre,) = pendientes(sesion)
        assert sobre.payload["vehicle_id"] not in ("None", "", None)
        uuid.UUID(str(sobre.payload["vehicle_id"]))


async def test_el_cambio_de_estado_anota_de_donde_y_adonde(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """`from` y `to`, no solo el estado nuevo.

    Un consumidor que recibiera unicamente el destino no podria distinguir
    "se reservo" de "volvio a disponible y despues se reservo", y las
    automatizaciones de C-28 se disparan por la transicion.
    """
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="AA202AA"))
        await servicio.cambiar_estado(
            creado.id, VehiculoCambioDeEstado(status=EstadoDeVehiculo.DISPONIBLE)
        )

        alta, transicion = pendientes(sesion)
        assert alta.type == "vehicle.created"
        assert transicion.type == "vehicle.status_changed"
        assert transicion.payload == {
            "vehicle_id": str(creado.id),
            "from": EstadoDeVehiculo.EN_PREPARACION.value,
            "to": EstadoDeVehiculo.DISPONIBLE.value,
        }


async def test_la_baja_logica_anota_vehicle_archived(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """⚠️ `vehicle.archived` es la BAJA LOGICA, no el estado `archived`.

    El vehiculo de este test se da de baja estando `in_preparation`, y el evento
    sale igual con ese `status`. Son dos conceptos que comparten nombre:
    `dar_de_baja` escribe `deleted_at` y no toca `status`; pasar a `archived` es
    una transicion de `RN-ST-05` que deja el vehiculo vivo. Un consumidor que las
    confunda borra de su indice vehiculos que siguen existiendo.
    """
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="AA203AA"))
        await servicio.dar_de_baja(creado.id)

        _, baja = pendientes(sesion)
        assert baja.type == "vehicle.archived"
        assert baja.payload == {
            "vehicle_id": str(creado.id),
            "status": EstadoDeVehiculo.EN_PREPARACION.value,
        }


async def test_el_payload_no_lleva_el_costo_de_adquisicion(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """`RN-ST-12` por la puerta de atras, que es por donde se escapa.

    La API no le manda `acquisition_cost_ars` a un `salesperson` porque `rbac.py`
    decide segun quien pregunta. **Un evento no tiene quien pregunta**: si el
    payload llevara el vehiculo entero, el costo quedaria en un stream de Redis
    legible por cualquier consumidor futuro y la regla se evaporaria sin que
    ningun test de permisos se enterara.
    """
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(
            _datos(
                sucursal,
                marca,
                modelo,
                domain_plate="AA204AA",
                acquisition_cost_ars=Decimal("19000000.00"),
            )
        )
        await servicio.cambiar_estado(
            creado.id, VehiculoCambioDeEstado(status=EstadoDeVehiculo.DISPONIBLE)
        )
        await servicio.dar_de_baja(creado.id)

        # El costo esta cargado en el vehiculo...
        assert creado.acquisition_cost_ars == Decimal("19000000.00")

        # ...y no aparece en NINGUNO de los tres eventos, ni con ese nombre ni
        # como valor suelto en cualquier otra clave.
        for sobre in pendientes(sesion):
            assert "acquisition_cost_ars" not in sobre.payload, sobre.type
            assert "19000000" not in str(sobre.payload), sobre.type


async def test_una_transicion_rechazada_no_anota_nada(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """El evento sale del hecho, y si el hecho no ocurrio no hay hecho que contar.

    Sin esto, mover el `registrar` unas lineas mas arriba —antes de la validacion
    de la transicion— pasaria desapercibido: el servicio seguiria levantando y el
    endpoint seguiria devolviendo 422, pero el evento ya estaria anotado.
    """
    tenant, sucursal, marca, modelo = escenario

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = StockService(sesion, tenant)
        creado = await servicio.crear(_datos(sucursal, marca, modelo, domain_plate="AA205AA"))

        # `RESERVADO` y no `VENDIDO`: desde `in_preparation` las dos son
        # invalidas, pero vender sin razon lo rechaza el SCHEMA (`RN-ST-06`) y el
        # servicio ni se entera. Lo que hay que ejercitar acá es la maquina de
        # estados, que es donde vive el `registrar`.
        with pytest.raises(TransicionInvalida):
            await servicio.cambiar_estado(
                creado.id, VehiculoCambioDeEstado(status=EstadoDeVehiculo.RESERVADO)
            )

        assert [sobre.type for sobre in pendientes(sesion)] == ["vehicle.created"]
