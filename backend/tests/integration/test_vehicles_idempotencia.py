"""`Idempotency-Key` en `POST /vehicles` — C-15, `T-078`, bloque 4. CODIGO CRITICO.

Sienta el patron para todos los `POST` de creacion que vengan despues (leads,
contactos, operaciones, pagos). La mecanica de concurrencia real —sesion
compartida, `lock_timeout`, la ventana de caida cerrada— ya esta probada a
nivel de modulo en `test_idempotencia.py`; este archivo prueba que el
ENDPOINT la conecta bien: el header, la validacion de longitud, el 409, el
aislamiento por tenant, y la precondicion del patron (`D-1`).

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


def _cabecera(
    proveedor: EmisorDePrueba, tenant: uuid.UUID, *, role: str = "manager"
) -> dict[str, str]:
    return {"Authorization": f"Bearer {proveedor.firmar(tenant_id=tenant, role=role)}"}


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
        **extra,
    }


async def _cantidad_de_vehiculos(tenant: uuid.UUID) -> int:
    async with sesion_de_propietario() as sesion:
        return int(
            (
                await sesion.execute(
                    text("SELECT count(*) FROM vehicles WHERE tenant_id = :t"), {"t": tenant}
                )
            ).scalar_one()
        )


# ── 4.8 · Reintento identico ─────────────────────────────────────────────────


async def test_el_reintento_identico_devuelve_el_mismo_vehiculo_y_no_crea_otro(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)
    cabecera["Idempotency-Key"] = "clave-reintento-001"
    cuerpo = _cuerpo(sucursal, modelo_del_catalogo, domain_plate="ID100ID")

    primera = cliente.post("/api/v1/vehicles", json=cuerpo, headers=cabecera)
    segunda = cliente.post("/api/v1/vehicles", json=cuerpo, headers=cabecera)

    assert primera.status_code == 201, primera.text
    assert segunda.status_code == 201, segunda.text
    assert primera.json() == segunda.json()
    assert await _cantidad_de_vehiculos(tenant) == 1


# ── 4.9 · Misma clave, contenido distinto ────────────────────────────────────


def test_misma_clave_con_cuerpo_distinto_da_409(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)
    cabecera["Idempotency-Key"] = "clave-conflicto-001"

    primera = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="ID101ID"),
        headers=cabecera,
    )
    segunda = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal,
            modelo_del_catalogo,
            domain_plate="ID102ID",
            chassis_number="9BWZZZ377VA111222",
        ),
        headers=cabecera,
    )

    assert primera.status_code == 201
    assert segunda.status_code == 409
    assert segunda.json()["code"] == "idempotency_key_conflict"


# ── 4.10 · Sin clave, alta normal ─────────────────────────────────────────────


def test_sin_clave_el_alta_se_procesa_normalmente_y_admite_reintentos_como_altas_nuevas(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """La idempotencia se OFRECE, no se impone."""
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)

    uno = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="ID103ID"),
        headers=cabecera,
    )
    dos = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal,
            modelo_del_catalogo,
            domain_plate="ID104ID",
            chassis_number="9BWZZZ377VA333444",
        ),
        headers=cabecera,
    )

    assert uno.status_code == 201
    assert dos.status_code == 201
    assert uno.json()["id"] != dos.json()["id"]


# ── 4.11 · La misma clave en dos agencias ────────────────────────────────────


async def test_la_misma_clave_en_dos_agencias_crea_dos_vehiculos(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant_a, sucursal_a = agencia
    tenant_b, sucursal_b = await agencia_con_sucursal()
    clave = "clave-compartida-entre-agencias"

    de_a = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal_a, modelo_del_catalogo, domain_plate="ID105ID"),
        headers={**_cabecera(proveedor, tenant_a), "Idempotency-Key": clave},
    )
    de_b = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal_b,
            modelo_del_catalogo,
            domain_plate="ID106ID",
            chassis_number="9BWZZZ377VA555666",
        ),
        headers={**_cabecera(proveedor, tenant_b), "Idempotency-Key": clave},
    )

    assert de_a.status_code == 201
    assert de_b.status_code == 201
    assert de_a.json()["id"] != de_b.json()["id"]
    assert de_a.json()["domain_plate"] == "ID105ID"
    assert de_b.json()["domain_plate"] == "ID106ID"


# ── 4.12 · Una creacion que falla no deja vehiculo y libera la clave ────────


def test_una_creacion_que_falla_por_dominio_duplicado_no_deja_vehiculo_y_libera_la_clave(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)

    # Dominio ya cargado, SIN idempotencia.
    cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="ID107ID"),
        headers=cabecera,
    )

    cabecera_con_clave = {**cabecera, "Idempotency-Key": "clave-que-falla-001"}
    rechazo = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal,
            modelo_del_catalogo,
            domain_plate="ID107ID",
            chassis_number="1BWZZZ377VA777888",
        ),
        headers=cabecera_con_clave,
    )
    assert rechazo.status_code == 422
    assert rechazo.json()["code"] == "vehicle_duplicate"

    # La clave quedo libre: un reintento con OTRO dominio, misma clave,
    # se procesa como una creacion nueva — no como el conflicto de 4.9.
    reintento = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal,
            modelo_del_catalogo,
            domain_plate="ID108ID",
            chassis_number="1BWZZZ377VA999000",
        ),
        headers=cabecera_con_clave,
    )
    assert reintento.status_code == 201, reintento.text


# ── 4.13 · Clave desmesurada ──────────────────────────────────────────────────


async def test_una_clave_de_idempotencia_desmesurada_se_rechaza_con_422(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """`design.md` D-1 punto 4: la columna `key` de la migracion `003` es
    `TEXT`, sin techo. Se valida en el header — entre 1 y 255 caracteres."""
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)
    cabecera["Idempotency-Key"] = "x" * 256

    rechazo = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="ID109ID"),
        headers=cabecera,
    )

    assert rechazo.status_code == 422
    assert await _cantidad_de_vehiculos(tenant) == 0


def test_una_clave_de_255_caracteres_exactos_se_acepta(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """El contrapeso: el limite es 255, no menos."""
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)
    cabecera["Idempotency-Key"] = "x" * 255

    respuesta = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="ID110ID"),
        headers=cabecera,
    )

    assert respuesta.status_code == 201, respuesta.text


# ── 4.15 · La precondicion del patron ────────────────────────────────────────


def test_post_vehicles_responde_la_misma_forma_para_todos_los_roles(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """`design.md` D-1: si `POST /vehicles` alguna vez empieza a elegir
    schema por concesion, este test se pone rojo ANTES de que la respuesta
    guardada se convierta en una fuga por la puerta de atras."""
    tenant, sucursal = agencia

    de_manager = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal, modelo_del_catalogo, domain_plate="ID111ID", acquisition_cost_ars="5000000.00"
        ),
        headers=_cabecera(proveedor, tenant, role="manager"),
    ).json()
    de_admin = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal,
            modelo_del_catalogo,
            domain_plate="ID112ID",
            chassis_number="1BWZZZ377VA123123",
            acquisition_cost_ars="5000000.00",
        ),
        headers=_cabecera(proveedor, tenant, role="admin_staff"),
    ).json()

    assert set(de_manager.keys()) == set(de_admin.keys())
    assert "acquisition_cost_ars" not in de_manager
    assert "acquisition_cost_ars" not in de_admin


# ── 4.16 · El evento sigue saliendo con clave ────────────────────────────────


async def test_un_alta_con_clave_deja_vehicle_created_publicado(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
    redis: Any,
) -> None:
    """Es el riesgo que descarto la opcion (a) de `design.md`: un `POST` que
    no pasara por `sesion_del_tenant_actual` no publicaria `vehicle.created`,
    y `drenar` no levanta aunque Redis este caido — asi que nadie se
    enteraria. Se lee del STREAM, no de la tabla del outbox."""
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)
    cabecera["Idempotency-Key"] = "clave-con-evento-001"

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="ID113ID"),
        headers=cabecera,
    )
    assert creado.status_code == 201, creado.text

    mensajes = await redis.xrange("eventos:vehicle.created")
    publicados = [
        m
        for _, m in mensajes
        if m.get("tenant_id") == str(tenant) and creado.json()["id"] in m["payload"]
    ]
    assert publicados, "no se encontro vehicle.created publicado para este vehiculo"
