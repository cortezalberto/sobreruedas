"""`GET /vehicles/{id}/history` — C-15, `T-085`.

La linea de tiempo completa de un vehiculo, del cambio mas nuevo al mas viejo.
Permiso `vehicles:read`, `all` para los tres roles (`ADR-024` §3).

⚠️ `D-4`: la restriccion de campos que `vehicles:read` impone sobre el
VEHICULO (`CAMPOS_DE_VEHICULO_SIN_COSTO`) NO se aplica acá — es una lista
blanca de OTRO recurso. Aplicarla a ciegas devolveria registros en blanco.

Sin mocks de base de datos (regla dura 8).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
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


async def _persona(tenant: uuid.UUID, *, rol: str = "manager") -> uuid.UUID:
    uid = uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Autora de prueba', :r, 'active')"
            ),
            {"id": uid, "t": tenant, "e": f"{uid}@example.com", "r": rol},
        )
    return uid


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


# ── 2.1 · Historial con transiciones, del mas nuevo al mas viejo ────────────


async def test_historial_de_un_vehiculo_con_dos_transiciones_devuelve_tres_filas(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """`cambiar_estado` escribe `changed_by` con el `sub` del token, y esa
    columna tiene FK compuesta a `users` (C-14): hace falta un usuario REAL,
    no un UUID sintetico (advertencia de C-14 sobre este mismo punto)."""
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant, sub=await _persona(tenant))

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="HI100HI"),
        headers=cabecera,
    ).json()
    cliente.post(
        f"/api/v1/vehicles/{creado['id']}/status", json={"status": "available"}, headers=cabecera
    )
    cliente.post(
        f"/api/v1/vehicles/{creado['id']}/status", json={"status": "reserved"}, headers=cabecera
    )

    historial = cliente.get(f"/api/v1/vehicles/{creado['id']}/history", headers=cabecera)

    assert historial.status_code == 200, historial.text
    filas = historial.json()
    assert len(filas) == 3
    assert [f["to_status"] for f in filas] == ["reserved", "available", "in_preparation"]
    # La fila genesis, al final, con `from_status` nulo.
    assert filas[-1]["from_status"] is None


# ── 2.2 · Aislamiento ─────────────────────────────────────────────────────


def test_historial_de_un_vehiculo_de_otra_agencia_da_404(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    otra_agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant_a, _ = agencia
    tenant_b, sucursal_b = otra_agencia

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal_b, modelo_del_catalogo, domain_plate="HI101HI"),
        headers=_cabecera(proveedor, tenant_b),
    ).json()

    ajeno = cliente.get(
        f"/api/v1/vehicles/{creado['id']}/history", headers=_cabecera(proveedor, tenant_a)
    )

    assert ajeno.status_code == 404


# ── 2.3 · Vehiculo dado de baja ──────────────────────────────────────────────


def test_historial_de_un_vehiculo_dado_de_baja_da_404(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="HI102HI"),
        headers=cabecera,
    ).json()
    cliente.delete(f"/api/v1/vehicles/{creado['id']}", headers=cabecera)

    dado_de_baja = cliente.get(f"/api/v1/vehicles/{creado['id']}/history", headers=cabecera)

    assert dado_de_baja.status_code == 404


# ── 2.5 · D-4: un salesperson recibe registros completos ────────────────────


async def test_un_salesperson_recibe_el_historial_completo_no_recortado(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Si alguien aplicara `recortar()` a ciegas con
    `CAMPOS_DE_VEHICULO_SIN_COSTO`, este test devolveria registros en blanco:
    esa lista blanca no tiene `from_status`, `to_status`, `changed_by` ni
    `changed_at` — son columnas de OTRA tabla."""
    tenant, sucursal = agencia
    manager = await _persona(tenant, rol="manager")
    cabecera_manager = _cabecera(proveedor, tenant, role="manager", sub=manager)
    vendedor = await _persona(tenant, rol="salesperson")
    cabecera_vendedor = _cabecera(proveedor, tenant, role="salesperson", sub=vendedor)

    # `salesperson` no tiene `vehicles:create` (`ADR-024`): crea el manager,
    # cambia de estado el manager (para no depender de `own`), y el
    # vendedor solo LEE el historial — que es lo que este test verifica.
    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="HI103HI"),
        headers=cabecera_manager,
    ).json()
    cliente.post(
        f"/api/v1/vehicles/{creado['id']}/status",
        json={"status": "available"},
        headers=cabecera_manager,
    )

    historial = cliente.get(f"/api/v1/vehicles/{creado['id']}/history", headers=cabecera_vendedor)

    assert historial.status_code == 200, historial.text
    fila = historial.json()[0]
    assert fila["to_status"] == "available"
    assert fila["from_status"] == "in_preparation"
    assert "changed_by" in fila
    assert "changed_at" in fila
    assert "reason" in fila


# ── 2.6 · El historial no filtra informacion economica ──────────────────────


def test_el_historial_no_expone_precio_ni_costo(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal,
            modelo_del_catalogo,
            domain_plate="HI104HI",
            acquisition_cost_ars="12000000.00",
        ),
        headers=cabecera,
    ).json()

    historial = cliente.get(f"/api/v1/vehicles/{creado['id']}/history", headers=cabecera)

    assert historial.status_code == 200
    for fila in historial.json():
        assert "price_ars" not in fila
        assert "acquisition_cost_ars" not in fila
        assert "12000000" not in str(fila)


# ── 2.7 · La ruta resuelve bien: no se la come `/{vehiculo_id}` ─────────────


def test_la_ruta_history_no_se_confunde_con_obtener_por_id(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="HI105HI"),
        headers=cabecera,
    ).json()

    historial = cliente.get(f"/api/v1/vehicles/{creado['id']}/history", headers=cabecera)

    assert historial.status_code == 200
    assert isinstance(historial.json(), list)
    # Si `/{vehiculo_id}` se hubiera comido la ruta, FastAPI intentaria parsear
    # "history" como parte del path del UUID y este GET fallaria antes de
    # llegar acá, o devolveria la forma de UN vehiculo (un dict, no una lista).
