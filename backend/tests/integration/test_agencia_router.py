"""Los endpoints de la agencia y sus sucursales, sobre HTTP — C-05 (parcial).

QUE SE PRUEBA ACA
──────────────────
Lo mismo que en stock, porque es el mismo riesgo: **con el token de la agencia
A no se ve ni se toca nada de la agencia B**, ni siquiera pidiendo por el id
exacto de una sucursal ajena.

Y una cosa mas que stock no tiene: la CUOTA DEL PLAN. `crear_sucursal` verifica
el techo antes del INSERT, y el rechazo es 402 — no 403. Que la distincion
sobreviva sobre HTTP es lo unico que la hace util para el frontend.

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
from .soporte import DSN_APLICACION, reponer_entorno, sesion_de_propietario

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


async def _agencia(*, plan: str | None = None) -> tuple[uuid.UUID, uuid.UUID]:
    """Un tenant con una sucursal, creados con el rol PROPIETARIO.

    Es andamiaje: `tenants` no tiene politica RLS y el rol de aplicacion no la
    escribe. La precondicion se arma por la puerta de servicio y el endpoint se
    prueba por la de adelante.

    `plan` toma el CODIGO del plan sembrado por la migracion `005`, no su id:
    el id es un UUID generado en esa migracion y no se puede escribir aca.
    """
    tenant_id, branch_id = uuid.uuid4(), uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        plan_id = None
        if plan is not None:
            plan_id = await sesion.scalar(text("SELECT id FROM plans WHERE code = :c"), {"c": plan})
            assert plan_id is not None, f"la migracion 005 no sembro el plan '{plan}'"
        await sesion.execute(
            text(
                "INSERT INTO tenants (id, name, slug, cuit, billing_email, status, plan_id) "
                "VALUES (:id, :n, :s, :c, :e, 'active', :p)"
            ),
            {
                "id": tenant_id,
                "n": f"Agencia {tenant_id.hex[:6]}",
                "s": f"agencia-{tenant_id.hex[:8]}",
                "c": f"30{tenant_id.int % 10**9:09d}0"[:11],
                "e": "facturacion@example.com",
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


@pytest.fixture
async def agencia() -> tuple[uuid.UUID, uuid.UUID]:
    return await _agencia()


@pytest.fixture
async def otra_agencia() -> tuple[uuid.UUID, uuid.UUID]:
    return await _agencia()


def _cabecera(proveedor: EmisorDePrueba, tenant: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {proveedor.firmar(tenant_id=tenant)}"}


_SUCURSAL = {"name": "Sucursal Norte", "city": "Godoy Cruz", "province": "Mendoza"}


# ── Aislamiento — lo que tiene que fallar ruidosamente ───────────────────────


async def test_cada_agencia_ve_solo_sus_sucursales(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    otra_agencia: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant_a, sucursal_a = agencia
    tenant_b, sucursal_b = otra_agencia

    vistas_por_a = cliente.get("/api/v1/branches", headers=_cabecera(proveedor, tenant_a))
    vistas_por_b = cliente.get("/api/v1/branches", headers=_cabecera(proveedor, tenant_b))

    assert vistas_por_a.status_code == 200
    assert [s["id"] for s in vistas_por_a.json()] == [str(sucursal_a)]
    assert [s["id"] for s in vistas_por_b.json()] == [str(sucursal_b)]


async def test_una_sucursal_ajena_no_se_lee_ni_con_su_id(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    otra_agencia: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """404 y no 403: distinguirlos confirmaria que ese id existe en otro tenant."""
    tenant_a, _ = agencia
    _, sucursal_b = otra_agencia

    respuesta = cliente.get(
        f"/api/v1/branches/{sucursal_b}", headers=_cabecera(proveedor, tenant_a)
    )

    assert respuesta.status_code == 404


async def test_una_sucursal_ajena_no_se_da_de_baja(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    otra_agencia: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Y la de al lado sigue viva: el rechazo no puede ser cosmetico."""
    tenant_a, _ = agencia
    tenant_b, sucursal_b = otra_agencia

    respuesta = cliente.post(
        f"/api/v1/branches/{sucursal_b}/deactivate", headers=_cabecera(proveedor, tenant_a)
    )

    assert respuesta.status_code == 404
    sigue = cliente.get(f"/api/v1/branches/{sucursal_b}", headers=_cabecera(proveedor, tenant_b))
    assert sigue.status_code == 200


async def test_sin_token_no_se_entra(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/branches").status_code == 401
    assert cliente.get("/api/v1/tenant/me").status_code == 401


# ── La agencia del token ────────────────────────────────────────────────────


async def test_tenant_me_devuelve_la_agencia_del_token(
    cliente: TestClient, proveedor: EmisorDePrueba, agencia: tuple[uuid.UUID, uuid.UUID]
) -> None:
    tenant_id, _ = agencia

    respuesta = cliente.get("/api/v1/tenant/me", headers=_cabecera(proveedor, tenant_id))

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == str(tenant_id)


async def test_un_token_de_una_agencia_inexistente_da_404(
    cliente: TestClient, proveedor: EmisorDePrueba, base_migrada: None
) -> None:
    """Token bien firmado de un tenant que no esta en esta base. No es un 500."""
    respuesta = cliente.get("/api/v1/tenant/me", headers=_cabecera(proveedor, uuid.uuid4()))

    assert respuesta.status_code == 404


# ── Alta, baja y cuota ──────────────────────────────────────────────────────


async def test_una_sucursal_nueva_nace_en_la_agencia_del_token(
    cliente: TestClient, proveedor: EmisorDePrueba, agencia: tuple[uuid.UUID, uuid.UUID]
) -> None:
    tenant_id, _ = agencia

    respuesta = cliente.post(
        "/api/v1/branches", json=_SUCURSAL, headers=_cabecera(proveedor, tenant_id)
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["tenant_id"] == str(tenant_id)


async def test_el_cuerpo_no_puede_elegir_la_agencia(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    otra_agencia: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Regla dura 1: `tenant_id` se deriva del token y nunca del cuerpo.

    El schema es estricto, asi que el campo de mas es un 422 — y no una
    sucursal creada en la agencia equivocada, que es el fallo que importa.
    """
    tenant_a, _ = agencia
    tenant_b, _ = otra_agencia

    respuesta = cliente.post(
        "/api/v1/branches",
        json={**_SUCURSAL, "tenant_id": str(tenant_b)},
        headers=_cabecera(proveedor, tenant_a),
    )

    assert respuesta.status_code == 422


async def test_dar_de_baja_no_borra_la_fila(
    cliente: TestClient, proveedor: EmisorDePrueba, agencia: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """Regla dura 3: borrado logico."""
    tenant_id, sucursal_id = agencia
    cabecera = _cabecera(proveedor, tenant_id)

    baja = cliente.post(f"/api/v1/branches/{sucursal_id}/deactivate", headers=cabecera)

    assert baja.status_code == 200
    assert cliente.get(f"/api/v1/branches/{sucursal_id}", headers=cabecera).status_code == 404

    async with sesion_de_propietario() as sesion:
        borrada_en = await sesion.scalar(
            text("SELECT deleted_at FROM branches WHERE id = :id"), {"id": sucursal_id}
        )
    assert borrada_en is not None


async def test_una_sucursal_inexistente_da_404_y_no_422(
    cliente: TestClient, proveedor: EmisorDePrueba, agencia: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """El servicio levanta `DomainError` (422); sobre HTTP esto es un 404.

    Si alguna vez vuelve a salir 422, quien consuma la API va a buscar el error
    en un cuerpo que ni siquiera se manda.
    """
    tenant_id, _ = agencia

    respuesta = cliente.post(
        f"/api/v1/branches/{uuid.uuid4()}/deactivate", headers=_cabecera(proveedor, tenant_id)
    )

    assert respuesta.status_code == 404


async def test_el_techo_del_plan_responde_402(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Starter permite UNA sucursal y la agencia ya la tiene.

    402 y no 403 (design.md D-6 de C-04): ningun cambio de rol lo destraba, y
    el cuerpo trae `resource`/`limit`/`used` para que el frontend no parsee
    texto para humanos.
    """
    tenant_id, _ = await _agencia(plan="starter")

    respuesta = cliente.post(
        "/api/v1/branches", json=_SUCURSAL, headers=_cabecera(proveedor, tenant_id)
    )

    assert respuesta.status_code == 402
    cuerpo = respuesta.json()
    assert cuerpo["code"] == "plan_quota_exceeded"
    assert (cuerpo["resource"], cuerpo["limit"], cuerpo["used"]) == ("branches", 1, 1)


async def test_una_baja_devuelve_cuota_al_plan(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """La contracara del test anterior, y la que prueba que la cuota se CUENTA
    y no se guarda: dada de baja la unica sucursal de Starter, entra otra."""
    tenant_id, sucursal_id = await _agencia(plan="starter")
    cabecera = _cabecera(proveedor, tenant_id)

    cliente.post(f"/api/v1/branches/{sucursal_id}/deactivate", headers=cabecera)
    respuesta = cliente.post("/api/v1/branches", json=_SUCURSAL, headers=cabecera)

    assert respuesta.status_code == 201
