"""Alcance fino sobre endpoints reales — C-02, tareas 6.6 y 6.10.

QUE SE PRUEBA ACA
──────────────────
Que la concesion de `ADR-024` se HAGA CUMPLIR, no solo que este declarada. Son
dos recortes distintos y se prueban por separado:

  - **Campos** (`RN-ST-12`): el vendedor lee el vehiculo y NO recibe
    `acquisition_cost_ars`; el gerente y el administrativo si. Los dos sentidos,
    porque un test que solo verifique que el vendedor no lo ve pasaria igual si
    el campo no se le devolviera a nadie — y ese es el estado del que venimos.

  - **Alcance `own`** (`ADR-024` §4, tarea 6.10): sobre `assigned_user_id` y en
    el MOMENTO de la peticion. El caso que le da sentido a `RN-CR-13` es el de
    la reasignacion: quien creo el vehiculo pierde el acceso cuando se lo pasan
    a otro.

Sobre base real, sin mocks (regla dura 8).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import auth
from app.core.auth import Sujeto
from app.core.errors import AlcanceInsuficiente, TransicionNoPermitida
from app.core.rbac import MATRIZ_DE_TENANT, RolDeTenant
from app.db.session import sesion_de_tenant
from app.main import create_app
from app.modules.stock.models import Vehicle
from app.modules.stock.router import cambiar_estado
from app.modules.stock.schemas import (
    Carroceria,
    Combustible,
    EstadoDeVehiculo,
    Transmision,
    VehiculoCambioDeEstado,
    VehiculoCrear,
)
from app.modules.stock.service import StockService

from ..emisor_de_tokens import EmisorDePrueba
from .soporte import (
    DSN_APLICACION,
    agencia_con_sucursal,
    reponer_entorno,
    sesion_de_propietario,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def proveedor() -> EmisorDePrueba:
    return EmisorDePrueba()


@pytest.fixture
def cliente(
    monkeypatch: pytest.MonkeyPatch, proveedor: EmisorDePrueba, base_migrada: None
) -> Iterator[TestClient]:
    reponer_entorno(monkeypatch, dsn=DSN_APLICACION)

    async def traer() -> dict[str, Any]:
        return proveedor.jwks

    monkeypatch.setattr(
        auth,
        "claves_del_proveedor",
        lambda: auth.ClavesDelProveedor(url="x", traer=traer),
    )
    monkeypatch.setattr(auth, "emisor_esperado", lambda: proveedor.emisor)

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
async def agencia() -> tuple[uuid.UUID, uuid.UUID]:
    return await agencia_con_sucursal()


@pytest.fixture
async def catalogo() -> tuple[uuid.UUID, uuid.UUID]:
    async with sesion_de_propietario() as sesion:
        fila = (
            await sesion.execute(
                text("SELECT brand_id, id FROM vehicle_models ORDER BY name LIMIT 1")
            )
        ).one()
    return uuid.UUID(str(fila[0])), uuid.UUID(str(fila[1]))


def _cabecera(
    proveedor: EmisorDePrueba,
    tenant: uuid.UUID,
    *,
    role: str = "manager",
    sub: uuid.UUID | None = None,
) -> dict[str, str]:
    token = proveedor.firmar(tenant_id=tenant, role=role, sub=str(sub) if sub else None)
    return {"Authorization": f"Bearer {token}"}


def _cuerpo(
    branch_id: uuid.UUID,
    catalogo: tuple[uuid.UUID, uuid.UUID],
    **extra: Any,
) -> dict[str, Any]:
    marca, modelo = catalogo
    return {
        "branch_id": str(branch_id),
        "brand_id": str(marca),
        "model_id": str(modelo),
        "year": 2021,
        "mileage_km": 30000,
        "color": "Blanco",
        "fuel_type": "diesel",
        "transmission": "manual",
        "body_type": "sedan",
        "price_ars": "15000000.00",
        # Formato `AA999AA` — `validadores_ar` rechaza cualquier otra cosa.
        "domain_plate": f"AB{uuid.uuid4().int % 1000:03d}CD",
        **extra,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 6.6 — Restriccion de campos EN LECTURA (`RN-ST-12`)
# ═════════════════════════════════════════════════════════════════════════════


class TestElCostoDeAdquisicion:
    """`ADR-024` §6: ✅ manager · ❌ salesperson · ✅ admin_staff.

    Es la celda que obligo a que la restriccion de campos aplicara tambien a la
    lectura, que la spec de `authorization` no preveia.
    """

    def _crear(
        self,
        cliente: TestClient,
        proveedor: EmisorDePrueba,
        agencia: tuple[uuid.UUID, uuid.UUID],
        catalogo: tuple[uuid.UUID, uuid.UUID],
    ) -> str:
        tenant, sucursal = agencia
        respuesta = cliente.post(
            "/api/v1/vehicles",
            json=_cuerpo(sucursal, catalogo, acquisition_cost_ars="11000000.00"),
            headers=_cabecera(proveedor, tenant),
        )
        assert respuesta.status_code == 201, respuesta.text
        return str(respuesta.json()["id"])

    @pytest.mark.parametrize("rol", ["manager", "admin_staff"])
    def test_quien_puede_verlo_lo_recibe(
        self,
        cliente: TestClient,
        proveedor: EmisorDePrueba,
        agencia: tuple[uuid.UUID, uuid.UUID],
        catalogo: tuple[uuid.UUID, uuid.UUID],
        rol: str,
    ) -> None:
        """La mitad que hace que la otra no sea vacia.

        Sin esto, "el vendedor no ve el costo" seguiria en verde el dia que el
        costo no se le devolviera a nadie — que es exactamente el estado del que
        se viene.
        """
        vehiculo_id = self._crear(cliente, proveedor, agencia, catalogo)
        tenant, _ = agencia

        respuesta = cliente.get(
            f"/api/v1/vehicles/{vehiculo_id}",
            headers=_cabecera(proveedor, tenant, role=rol),
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["acquisition_cost_ars"] == "11000000.00"

    def test_el_vendedor_no_lo_recibe(
        self,
        cliente: TestClient,
        proveedor: EmisorDePrueba,
        agencia: tuple[uuid.UUID, uuid.UUID],
        catalogo: tuple[uuid.UUID, uuid.UUID],
    ) -> None:
        vehiculo_id = self._crear(cliente, proveedor, agencia, catalogo)
        tenant, _ = agencia

        respuesta = cliente.get(
            f"/api/v1/vehicles/{vehiculo_id}",
            headers=_cabecera(proveedor, tenant, role="salesperson"),
        )
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        # NO esta la clave. No es que venga en `null`: un `null` le dice al
        # cliente "este campo existe y no tiene valor", que es informacion sobre
        # el vehiculo que `RN-ST-12` no le concede.
        assert "acquisition_cost_ars" not in cuerpo
        # Y sigue viendo todo lo demas: el recorte es de campos, no de acceso.
        assert cuerpo["price_ars"] == "15000000.00"

    def test_el_listado_recorta_igual_que_el_detalle(
        self,
        cliente: TestClient,
        proveedor: EmisorDePrueba,
        agencia: tuple[uuid.UUID, uuid.UUID],
        catalogo: tuple[uuid.UUID, uuid.UUID],
    ) -> None:
        """El camino de salida que se olvida.

        Un recorte que solo cubre el detalle deja el costo saliendo por el
        listado, y el listado es el endpoint que mas se llama.
        """
        self._crear(cliente, proveedor, agencia, catalogo)
        tenant, _ = agencia

        del_vendedor = cliente.get(
            "/api/v1/vehicles",
            headers=_cabecera(proveedor, tenant, role="salesperson"),
        ).json()
        del_gerente = cliente.get(
            "/api/v1/vehicles", headers=_cabecera(proveedor, tenant, role="manager")
        ).json()

        assert del_vendedor and del_gerente
        assert all("acquisition_cost_ars" not in v for v in del_vendedor)
        assert all("acquisition_cost_ars" in v for v in del_gerente)


# ═════════════════════════════════════════════════════════════════════════════
# 6.10 — `own` es `assigned_user_id` EN EL MOMENTO de la peticion
#
# Estos tests llaman a la corrutina del router DIRECTAMENTE, sin HTTP. Dos
# motivos, los dos ya escritos en `test_agencia_endpoints_directo.py`:
#
#   1. `TestClient` corre el endpoint en su propio portal y `coverage` no traza
#      lo que pasa ahi adentro.
#   2. `own` se prueba REASIGNANDO a mitad de camino, y eso pide escribir en la
#      base entre dos llamadas. Con `TestClient` —sincronico— habria que abrir
#      un `asyncio.run()` sobre un engine cacheado en OTRO loop, que es
#      exactamente el fallo que documenta `test_tarea_dos_corridas.py`.
#
# La concesion se toma de la matriz real y no se arma a mano: lo que se prueba
# es la celda de `ADR-024`, no un `Concesion` de laboratorio.
# ═════════════════════════════════════════════════════════════════════════════

CELDA_DEL_VENDEDOR = MATRIZ_DE_TENANT[RolDeTenant.SALESPERSON]["vehicles:change_status"]
CELDA_DEL_GERENTE = MATRIZ_DE_TENANT[RolDeTenant.MANAGER]["vehicles:change_status"]


@asynccontextmanager
async def _sesion(tenant_id: uuid.UUID) -> AsyncIterator[AsyncSession]:
    """Lo mismo que la dependency real, sin FastAPI en el medio."""
    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        sesion.info["tenant_id"] = tenant_id
        yield sesion


def _vendedor(identificador: uuid.UUID, tenant: uuid.UUID) -> Sujeto:
    return Sujeto(user_id=str(identificador), tenant_id=tenant, role="salesperson")


async def _persona_real(tenant: uuid.UUID, *, rol: str = "salesperson") -> uuid.UUID:
    """Un usuario REAL — C-14: `cambiar_estado` ahora escribe `changed_by` con
    el `user_id` del sujeto, y la FK compuesta (`design.md` D-9) exige que
    exista en `users` para ese tenant. Sin esto, un sujeto sintetico como los
    que este archivo usaba hasta C-14 hace que la transicion EXITOSA reviente
    con un `IntegrityError` al escribir la fila de historial."""
    uid = uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Persona de prueba', :r, 'active')"
            ),
            {"id": uid, "t": tenant, "e": f"{uid}@example.com", "r": rol},
        )
    return uid


async def _vehiculo_disponible(
    sesion: AsyncSession,
    tenant: uuid.UUID,
    sucursal: uuid.UUID,
    catalogo: tuple[uuid.UUID, uuid.UUID],
    *,
    asignado_a: uuid.UUID | None,
) -> Vehicle:
    """Un vehiculo `available` y con el `assigned_user_id` que se pida.

    Se asigna por la puerta de servicio a proposito: `VehiculoCrear` no acepta
    `assigned_user_id` ni `status`, y `PATCH /vehicles/{id}` —la celda que `ADR-024`
    declara para eso— todavia no tiene endpoint (llega con C-14). La precondicion
    se arma como se pueda; lo que se prueba es la autorizacion, por la puerta de
    adelante.
    """
    marca, modelo = catalogo
    vehiculo = await StockService(sesion, tenant).crear(
        VehiculoCrear(
            branch_id=sucursal,
            brand_id=marca,
            model_id=modelo,
            year=2021,
            mileage_km=30000,
            color="Blanco",
            fuel_type=Combustible.DIESEL,
            transmission=Transmision.MANUAL,
            body_type=Carroceria.SEDAN,
            price_ars=Decimal("15000000.00"),
            domain_plate=f"AB{uuid.uuid4().int % 1000:03d}CD",
        )
    )
    vehiculo.status = EstadoDeVehiculo.DISPONIBLE.value
    vehiculo.assigned_user_id = asignado_a
    await sesion.flush()
    return vehiculo


class TestElAlcanceOwn:
    """`ADR-024` §4. `vehicles:change_status` es `own` para el vendedor."""

    async def test_el_vendedor_cambia_el_estado_de_lo_que_tiene_asignado(
        self, catalogo: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        tenant, sucursal = await agencia_con_sucursal()
        vendedor = await _persona_real(tenant)

        async with _sesion(tenant) as sesion:
            vehiculo = await _vehiculo_disponible(
                sesion, tenant, sucursal, catalogo, asignado_a=vendedor
            )
            resultado = await cambiar_estado(
                vehiculo.id,
                VehiculoCambioDeEstado(status=EstadoDeVehiculo.RESERVADO),
                sesion,
                _vendedor(vendedor, tenant),
                CELDA_DEL_VENDEDOR,
            )

        assert resultado.status is EstadoDeVehiculo.RESERVADO

    async def test_el_vendedor_no_toca_lo_asignado_a_otro(
        self, catalogo: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        tenant, sucursal = await agencia_con_sucursal()

        async with _sesion(tenant) as sesion:
            vehiculo = await _vehiculo_disponible(
                sesion, tenant, sucursal, catalogo, asignado_a=uuid.uuid4()
            )
            with pytest.raises(AlcanceInsuficiente):
                await cambiar_estado(
                    vehiculo.id,
                    VehiculoCambioDeEstado(status=EstadoDeVehiculo.RESERVADO),
                    sesion,
                    _vendedor(uuid.uuid4(), tenant),
                    CELDA_DEL_VENDEDOR,
                )

    async def test_el_rechazo_por_alcance_deja_el_recurso_intacto(
        self, catalogo: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """6.6, primera clausula. Rechazar despues de escribir no es rechazar.

        El orden importa y por eso se afirma: `verificar_alcance` corre entre el
        SELECT y el UPDATE. Si corriera despues, el estado ya habria cambiado y
        el 403 seria una mentira cortes.
        """
        tenant, sucursal = await agencia_con_sucursal()

        async with _sesion(tenant) as sesion:
            vehiculo = await _vehiculo_disponible(
                sesion, tenant, sucursal, catalogo, asignado_a=uuid.uuid4()
            )
            with pytest.raises(AlcanceInsuficiente):
                await cambiar_estado(
                    vehiculo.id,
                    VehiculoCambioDeEstado(status=EstadoDeVehiculo.RESERVADO),
                    sesion,
                    _vendedor(uuid.uuid4(), tenant),
                    CELDA_DEL_VENDEDOR,
                )

            await sesion.refresh(vehiculo)
            assert vehiculo.status == EstadoDeVehiculo.DISPONIBLE.value

    async def test_un_vehiculo_sin_asignar_no_es_de_nadie(
        self, catalogo: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """`NULL` no es igual a nada, y `own` pide igualdad.

        La lectura contraria —"sin dueño, de todos"— convertiria el olvido de
        asignar en una concesion.
        """
        tenant, sucursal = await agencia_con_sucursal()

        async with _sesion(tenant) as sesion:
            vehiculo = await _vehiculo_disponible(
                sesion, tenant, sucursal, catalogo, asignado_a=None
            )
            with pytest.raises(AlcanceInsuficiente):
                await cambiar_estado(
                    vehiculo.id,
                    VehiculoCambioDeEstado(status=EstadoDeVehiculo.RESERVADO),
                    sesion,
                    _vendedor(uuid.uuid4(), tenant),
                    CELDA_DEL_VENDEDOR,
                )

    async def test_el_gerente_no_depende_de_la_asignacion(
        self, catalogo: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """Contrapeso. Si `all` tambien mirara `assigned_user_id`, los tests de
        arriba pasarian igual y no probarian `own` sino una denegacion general."""
        tenant, sucursal = await agencia_con_sucursal()
        gerente = await _persona_real(tenant, rol="manager")

        async with _sesion(tenant) as sesion:
            vehiculo = await _vehiculo_disponible(
                sesion, tenant, sucursal, catalogo, asignado_a=uuid.uuid4()
            )
            resultado = await cambiar_estado(
                vehiculo.id,
                VehiculoCambioDeEstado(status=EstadoDeVehiculo.RESERVADO),
                sesion,
                Sujeto(user_id=str(gerente), tenant_id=tenant, role="manager"),
                CELDA_DEL_GERENTE,
            )

        assert resultado.status is EstadoDeVehiculo.RESERVADO

    async def test_reasignar_le_quita_el_acceso_al_anterior(
        self, catalogo: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """EL test de 6.10, y lo que le da sentido a `RN-CR-13`.

        Si reasignar no quitara el acceso, "solo el manager reasigna" no seria un
        control de nada: el vendedor anterior seguiria operando el vehiculo.
        `ADR-024` §4 es explicito en que el alcance se evalua contra el
        `assigned_user_id` DE ESTE MOMENTO — no contra quien lo creo, ni contra
        quien lo tenia cuando abrio sesion.
        """
        tenant, sucursal = await agencia_con_sucursal()
        primero, segundo = await _persona_real(tenant), uuid.uuid4()

        async with _sesion(tenant) as sesion:
            vehiculo = await _vehiculo_disponible(
                sesion, tenant, sucursal, catalogo, asignado_a=primero
            )
            sujeto = _vendedor(primero, tenant)

            # Antes de la reasignacion: puede.
            await cambiar_estado(
                vehiculo.id,
                VehiculoCambioDeEstado(status=EstadoDeVehiculo.RESERVADO),
                sesion,
                sujeto,
                CELDA_DEL_VENDEDOR,
            )

            # El gerente reasigna.
            vehiculo.assigned_user_id = segundo
            await sesion.flush()

            # Despues: el MISMO sujeto, el MISMO vehiculo — y ya no.
            with pytest.raises(AlcanceInsuficiente):
                await cambiar_estado(
                    vehiculo.id,
                    VehiculoCambioDeEstado(status=EstadoDeVehiculo.DISPONIBLE),
                    sesion,
                    sujeto,
                    CELDA_DEL_VENDEDOR,
                )

    async def test_el_vendedor_no_manda_al_taller_un_vehiculo_propio(
        self, catalogo: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """`ADR-034`, y la concesion de mas que ese ADR vino a cerrar.

        `available` -> `in_workshop` es una transicion LEGAL: `RN-ST-05` la
        admite y el gerente la hace. Lo que no puede es hacerla el vendedor,
        aunque el vehiculo sea suyo. Antes de `ADR-034` esta llamada pasaba.

        403 y no 422: el cambio existe, quien pregunta no es quien lo hace.
        """
        tenant, sucursal = await agencia_con_sucursal()
        vendedor = uuid.uuid4()

        async with _sesion(tenant) as sesion:
            vehiculo = await _vehiculo_disponible(
                sesion, tenant, sucursal, catalogo, asignado_a=vendedor
            )
            with pytest.raises(TransicionNoPermitida):
                await cambiar_estado(
                    vehiculo.id,
                    VehiculoCambioDeEstado(status=EstadoDeVehiculo.EN_TALLER),
                    sesion,
                    _vendedor(vendedor, tenant),
                    CELDA_DEL_VENDEDOR,
                )

            await sesion.refresh(vehiculo)
            assert vehiculo.status == EstadoDeVehiculo.DISPONIBLE.value

    async def test_el_gerente_si_lo_manda_al_taller(
        self, catalogo: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """Contrapeso, y no es de adorno.

        Sin esto el test de arriba pasaria igual si `in_workshop` fuera
        inalcanzable para todos — y estaria probando `RN-ST-05`, no el permiso.
        Es el error en el que cai al escribirlo: la primera version usaba
        `available` -> `sold`, que **no** es transicion legal para nadie.
        """
        tenant, sucursal = await agencia_con_sucursal()
        gerente = await _persona_real(tenant, rol="manager")

        async with _sesion(tenant) as sesion:
            vehiculo = await _vehiculo_disponible(
                sesion, tenant, sucursal, catalogo, asignado_a=uuid.uuid4()
            )
            resultado = await cambiar_estado(
                vehiculo.id,
                VehiculoCambioDeEstado(status=EstadoDeVehiculo.EN_TALLER),
                sesion,
                Sujeto(user_id=str(gerente), tenant_id=tenant, role="manager"),
                CELDA_DEL_GERENTE,
            )

        assert resultado.status is EstadoDeVehiculo.EN_TALLER

    async def test_el_vendedor_no_vende_en_dos_pasos(
        self, catalogo: tuple[uuid.UUID, uuid.UUID]
    ) -> None:
        """El camino que `RN-ST-05` sola no cierra.

        Cada salto por separado parece inocente: reservar es suyo, y
        `reserved` -> `sold` es legal. La maquina de estados acota QUE
        transiciones existen, no quien las hace, asi que componer dos permitidas
        no encuentra ningun control en el medio. El eje de `ADR-034` si.
        """
        tenant, sucursal = await agencia_con_sucursal()
        vendedor = await _persona_real(tenant)

        async with _sesion(tenant) as sesion:
            vehiculo = await _vehiculo_disponible(
                sesion, tenant, sucursal, catalogo, asignado_a=vendedor
            )
            sujeto = _vendedor(vendedor, tenant)

            # Paso 1: le corresponde.
            await cambiar_estado(
                vehiculo.id,
                VehiculoCambioDeEstado(status=EstadoDeVehiculo.RESERVADO),
                sesion,
                sujeto,
                CELDA_DEL_VENDEDOR,
            )

            # Paso 2: `RN-ST-05` lo admite, la matriz no se lo da.
            with pytest.raises(TransicionNoPermitida):
                await cambiar_estado(
                    vehiculo.id,
                    VehiculoCambioDeEstado(status=EstadoDeVehiculo.VENDIDO, reason="contado"),
                    sesion,
                    sujeto,
                    CELDA_DEL_VENDEDOR,
                )

            await sesion.refresh(vehiculo)
            assert vehiculo.status == EstadoDeVehiculo.RESERVADO.value
