"""Configuracion de la agencia y edicion de sucursales — C-05, tarea 5.10.

Sobre base real (regla dura 8).

LO QUE C-04 DEJO SIN ESCRIBIR
──────────────────────────────
`/tenant/me`, el listado y alta de sucursales y la baja ya existian. Faltaban
los dos `PATCH`: configurar la agencia y editar una sucursal. Las celdas de la
matriz ya estaban declaradas (`tenants:update`, `branches:update`) — lo que
faltaba era el endpoint que las usara.
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


def _cabecera(
    proveedor: EmisorDePrueba, tenant: uuid.UUID, *, role: str = "manager"
) -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer {proveedor.firmar(tenant_id=tenant, sub=str(uuid.uuid4()), role=role)}"
        )
    }


# ── La agencia ──────────────────────────────────────────────────────────────


async def test_un_manager_configura_su_agencia(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    tenant, _ = await agencia_con_sucursal(plan="pro")

    respuesta = cliente.patch(
        "/api/v1/tenant/me",
        json={"name": "Agencia Renombrada", "timezone": "America/Argentina/Cordoba"},
        headers=_cabecera(proveedor, tenant),
    )

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["name"] == "Agencia Renombrada"
    assert cuerpo["timezone"] == "America/Argentina/Cordoba"


async def test_la_configuracion_no_acepta_cuit_ni_slug(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Los dos son IDENTIDAD, no configuracion.

    El CUIT identifica a la agencia ante AFIP y el `slug` es su direccion
    publica: cambiarlos por un `PATCH` de configuracion rompe las publicaciones
    ya emitidas y la facturacion, en silencio. Si algun dia hay que cambiarlos,
    es una operacion con su propio nombre y su propia autorizacion.

    El schema es `extra="forbid"`, asi que el rechazo es 422 y no un silencio.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    cabecera = _cabecera(proveedor, tenant)

    for campo, valor in (("cuit", "30-12345678-9"), ("slug", "otra-agencia")):
        respuesta = cliente.patch("/api/v1/tenant/me", json={campo: valor}, headers=cabecera)
        assert respuesta.status_code == 422, f"{campo}: {respuesta.text}"


async def test_un_vendedor_no_configura_la_agencia(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """`tenants:update` solo la tiene `manager`."""
    tenant, _ = await agencia_con_sucursal(plan="pro")

    respuesta = cliente.patch(
        "/api/v1/tenant/me",
        json={"name": "No Deberia"},
        headers=_cabecera(proveedor, tenant, role="salesperson"),
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "insufficient_permission"


# ── Las sucursales ──────────────────────────────────────────────────────────


async def test_un_manager_edita_una_sucursal(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    tenant, sucursal = await agencia_con_sucursal(plan="pro")

    respuesta = cliente.patch(
        f"/api/v1/branches/{sucursal}",
        json={"name": "Sucursal Centro", "phone": "+542614445566"},
        headers=_cabecera(proveedor, tenant),
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["name"] == "Sucursal Centro"


async def test_no_se_puede_editar_la_sucursal_de_otra_agencia(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """El aislamiento, en el camino de escritura.

    404 y no 403: distinguirlos confirmaria que ese id existe en otra agencia.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    _, de_otra = await agencia_con_sucursal(plan="pro")

    respuesta = cliente.patch(
        f"/api/v1/branches/{de_otra}",
        json={"name": "Ajena"},
        headers=_cabecera(proveedor, tenant),
    )

    # 404 con codigo PROPIO, no el `http_404` generico: `SucursalNoEncontrada`
    # declara su `status_code`, igual que `VehiculoNoEncontrado` y
    # `UsuarioNoEncontrado`. El codigo nombra la causa, que es lo que el
    # frontend lee para elegir el mensaje.
    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "sucursal_inexistente"

    async with sesion_de_propietario() as sesion:
        nombre = (
            await sesion.execute(text("SELECT name FROM branches WHERE id = :id"), {"id": de_otra})
        ).scalar_one()
    assert nombre != "Ajena", "se edito la sucursal de otra agencia"


async def test_un_vendedor_no_edita_sucursales(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    tenant, sucursal = await agencia_con_sucursal(plan="pro")

    respuesta = cliente.patch(
        f"/api/v1/branches/{sucursal}",
        json={"name": "No Deberia"},
        headers=_cabecera(proveedor, tenant, role="salesperson"),
    )

    assert respuesta.status_code == 403
