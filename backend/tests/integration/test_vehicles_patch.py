"""`PATCH /vehicles/{id}` — C-15, `T-079`.

Expone `StockService.editar` (C-14) por HTTP. Lo que este archivo prueba y que
C-14 no podia verificar:

  1. El recorte de campos por concesion (`D-3`): `recortar()` se aplica ANTES
     de llamar al servicio, y no hay `if role ==` en el router.
  2. El evento `vehicle.updated` queda PUBLICADO al terminar la peticion,
     porque el drenaje del outbox vive en `sesion_del_tenant_actual`
     (`db/dependencias.py`) y no en el servicio.
  3. El hallazgo `H-a` de C-14: `internal_notes` no es columna ni campo de
     `VehiculoEditar`, asi que un `salesperson` que lo manda choca con
     `extra="forbid"` — 422, no 403.

Sin mocks de base de datos (regla dura 8).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import auth
from app.main import create_app

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
        auth, "claves_del_proveedor", lambda: auth.ClavesDelProveedor(url="x", traer=traer)
    )
    monkeypatch.setattr(auth, "emisor_esperado", lambda: proveedor.emisor)

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
async def modelo_del_catalogo() -> tuple[uuid.UUID, uuid.UUID]:
    async with sesion_de_propietario() as sesion:
        fila = (
            await sesion.execute(
                text("SELECT brand_id, id FROM vehicle_models ORDER BY name LIMIT 1")
            )
        ).one()
    return uuid.UUID(str(fila[0])), uuid.UUID(str(fila[1]))


@pytest.fixture
async def agencia() -> tuple[uuid.UUID, uuid.UUID]:
    return await agencia_con_sucursal()


@pytest.fixture
async def otra_agencia() -> tuple[uuid.UUID, uuid.UUID]:
    return await agencia_con_sucursal()


def _cabecera(
    proveedor: EmisorDePrueba,
    tenant: uuid.UUID,
    *,
    role: str = "manager",
    sub: uuid.UUID | None = None,
) -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer {proveedor.firmar(tenant_id=tenant, role=role, sub=str(sub) if sub else None)}"
        )
    }


def _cuerpo(
    branch_id: uuid.UUID, catalogo: tuple[uuid.UUID, uuid.UUID], **extra: Any
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
        "body_type": "pickup",
        "price_ars": "25000000.00",
        "chassis_number": "8AWZZZ377VA123456",
        **extra,
    }


def _crear(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    catalogo: tuple[uuid.UUID, uuid.UUID],
    **extra: Any,
) -> dict[str, Any]:
    tenant, sucursal = agencia
    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, catalogo, **extra),
        headers=_cabecera(proveedor, tenant),
    )
    assert creado.status_code == 201, creado.text
    resultado: dict[str, Any] = creado.json()
    return resultado


# ── 1.2 · Edicion completa por un rol sin restriccion de campos ─────────────


def test_un_manager_edita_varios_campos_y_el_resto_no_se_mueve(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, _ = agencia
    creado = _crear(cliente, proveedor, agencia, modelo_del_catalogo, domain_plate="PA100PA")

    editado = cliente.patch(
        f"/api/v1/vehicles/{creado['id']}",
        json={"color": "Rojo", "price_ars": "27000000.00"},
        headers=_cabecera(proveedor, tenant),
    )

    assert editado.status_code == 200, editado.text
    cuerpo = editado.json()
    assert cuerpo["color"] == "Rojo"
    assert Decimal(str(cuerpo["price_ars"])) == Decimal("27000000.00")
    # El resto del vehiculo no se movio.
    assert cuerpo["mileage_km"] == creado["mileage_km"]
    assert cuerpo["fuel_type"] == creado["fuel_type"]


# ── 1.3 · Sin el permiso de edicion ──────────────────────────────────────────


def test_un_rol_sin_permiso_de_edicion_recibe_403(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Los tres roles de tenant tienen `vehicles:update` (`ADR-024`), asi que
    se fuerza un rol inexistente para el catalogo: sin celda no hay concesion,
    y `PermisoInsuficiente` es 403 (`insufficient_permission`)."""
    tenant, _ = agencia
    creado = _crear(cliente, proveedor, agencia, modelo_del_catalogo, domain_plate="PA101PA")

    rechazo = cliente.patch(
        f"/api/v1/vehicles/{creado['id']}",
        json={"color": "Rojo"},
        headers=_cabecera(proveedor, tenant, role="rol_inexistente"),
    )

    assert rechazo.status_code == 403


# ── 1.4 · Aislamiento: vehiculo de otra agencia ─────────────────────────────


def test_editar_un_vehiculo_de_otra_agencia_da_404(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    otra_agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant_a, _ = agencia
    creado = _crear(cliente, proveedor, otra_agencia, modelo_del_catalogo, domain_plate="PA102PA")

    ajeno = cliente.patch(
        f"/api/v1/vehicles/{creado['id']}",
        json={"color": "Rojo"},
        headers=_cabecera(proveedor, tenant_a),
    )

    assert ajeno.status_code == 404


# ── 1.6 / 1.7 · Recorte de campos por concesion ──────────────────────────────


async def test_un_salesperson_que_manda_price_ars_solo_cambia_assigned_user_id(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """`D-3`: `salesperson` tiene `CAMPOS_DE_VEHICULO_PARA_VENDEDOR` =
    {internal_notes, assigned_user_id}. `price_ars` se descarta EN SILENCIO."""
    tenant, sucursal = agencia
    creado = _crear(cliente, proveedor, agencia, modelo_del_catalogo, domain_plate="PA103PA")
    vendedor = uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Vendedor', 'salesperson', 'active')"
            ),
            {"id": vendedor, "t": tenant, "e": f"{vendedor}@example.com"},
        )

    editado = cliente.patch(
        f"/api/v1/vehicles/{creado['id']}",
        json={"assigned_user_id": str(vendedor), "price_ars": "1.00"},
        headers=_cabecera(proveedor, tenant, role="salesperson", sub=vendedor),
    )

    assert editado.status_code == 200, editado.text
    cuerpo = editado.json()
    assert cuerpo["assigned_user_id"] == str(vendedor)
    assert Decimal(str(cuerpo["price_ars"])) == Decimal(str(creado["price_ars"]))


def test_un_manager_sin_recorte_si_cambia_price_ars(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """El contrapeso de 1.6: sin este test, un recorte que descartara TODO
    pasaria igual el de arriba."""
    tenant, _ = agencia
    creado = _crear(cliente, proveedor, agencia, modelo_del_catalogo, domain_plate="PA104PA")

    editado = cliente.patch(
        f"/api/v1/vehicles/{creado['id']}",
        json={"price_ars": "33000000.00"},
        headers=_cabecera(proveedor, tenant, role="manager"),
    )

    assert editado.status_code == 200, editado.text
    assert Decimal(str(editado.json()["price_ars"])) == Decimal("33000000.00")


# ── 1.9 · Cuerpo que queda vacio tras el recorte ─────────────────────────────


async def test_salesperson_que_solo_manda_campos_no_concedidos_no_cambia_nada(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """`D-3`: la respuesta es 200, el vehiculo no cambia. No es un error de
    permiso: el `salesperson` TIENE `vehicles:update`, solo que ninguno de los
    campos enviados le esta concedido."""
    tenant, _ = agencia
    creado = _crear(cliente, proveedor, agencia, modelo_del_catalogo, domain_plate="PA105PA")
    vendedor = uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Vendedor', 'salesperson', 'active')"
            ),
            {"id": vendedor, "t": tenant, "e": f"{vendedor}@example.com"},
        )

    editado = cliente.patch(
        f"/api/v1/vehicles/{creado['id']}",
        json={"price_ars": "1.00", "description": "cambio no concedido"},
        headers=_cabecera(proveedor, tenant, role="salesperson", sub=vendedor),
    )

    assert editado.status_code == 200, editado.text
    cuerpo = editado.json()
    assert Decimal(str(cuerpo["price_ars"])) == Decimal(str(creado["price_ars"]))
    assert cuerpo["description"] == creado["description"]


# ── 1.10 · Hallazgo H-a de C-14: `internal_notes` no es una columna ─────────


async def test_internal_notes_no_es_un_campo_de_vehiculo_editar(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Fija el comportamiento actual del hallazgo `H-a` de C-14: la celda de
    `ADR-024` §6 le da a `salesperson` un campo (`internal_notes`) que no
    existe como columna del modelo ni como campo de `VehiculoEditar`.
    `extra="forbid"` de `_EntradaEstricta` lo rechaza con 422 ANTES de que
    `recortar()` pueda intervenir — el hueco queda visible en la suite, no
    silencioso en el codigo (no bloquea este change, ver proposal.md)."""
    tenant, _ = agencia
    creado = _crear(cliente, proveedor, agencia, modelo_del_catalogo, domain_plate="PA106PA")
    vendedor = uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Vendedor', 'salesperson', 'active')"
            ),
            {"id": vendedor, "t": tenant, "e": f"{vendedor}@example.com"},
        )

    rechazo = cliente.patch(
        f"/api/v1/vehicles/{creado['id']}",
        json={"internal_notes": "el auto tiene un golpe"},
        headers=_cabecera(proveedor, tenant, role="salesperson", sub=vendedor),
    )

    assert rechazo.status_code == 422


# ── 1.11 · De punta a punta: el evento queda publicado ───────────────────────


async def test_un_patch_exitoso_publica_vehicle_updated(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
    redis: Any,
) -> None:
    """Lo que C-14 no podia verificar: el drenaje del outbox vive en
    `sesion_del_tenant_actual` (`db/dependencias.py`), FUERA de la sesion del
    servicio. Se lee del STREAM de Redis, no de la tabla del outbox: leer la
    tabla solo probaria que se anoto, no que se publico."""
    tenant, _ = agencia
    creado = _crear(cliente, proveedor, agencia, modelo_del_catalogo, domain_plate="PA107PA")

    editado = cliente.patch(
        f"/api/v1/vehicles/{creado['id']}",
        json={"color": "Verde"},
        headers=_cabecera(proveedor, tenant),
    )
    assert editado.status_code == 200, editado.text

    mensajes = await redis.xrange("eventos:vehicle.updated")
    tipos_de_vehiculo = [
        m for _, m in mensajes if m.get("tenant_id") == str(tenant) and creado["id"] in m["payload"]
    ]
    assert tipos_de_vehiculo, "no se encontro vehicle.updated publicado para este vehiculo"


# ── 1.12 · El PATCH no puede cambiar el estado ───────────────────────────────


def test_el_patch_no_admite_el_campo_status(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, _ = agencia
    creado = _crear(cliente, proveedor, agencia, modelo_del_catalogo, domain_plate="PA108PA")

    rechazo = cliente.patch(
        f"/api/v1/vehicles/{creado['id']}",
        json={"status": "sold"},
        headers=_cabecera(proveedor, tenant),
    )

    assert rechazo.status_code == 422
    assert (
        cliente.get(
            f"/api/v1/vehicles/{creado['id']}", headers=_cabecera(proveedor, tenant)
        ).json()["status"]
        == "in_preparation"
    )
