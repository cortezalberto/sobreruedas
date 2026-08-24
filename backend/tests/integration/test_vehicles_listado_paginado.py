"""`GET /vehicles` pagina — C-15, `T-080`, `design.md` D-2.

`app/core/pagination.py` existe desde C-02 y hasta este change ningun endpoint
HTTP lo usaba. `GET /vehicles` gana `?cursor=` y `?limit=`, SIN tocar
`core/pagination.py` ni cambiar la forma de la respuesta: sigue siendo un
array de vehiculos, y el cursor de la pagina siguiente viaja en el header
`X-Next-Cursor` (su ausencia es la ultima pagina).

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
from app.db.session import violaciones_de_aislamiento
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
    proveedor: EmisorDePrueba, tenant: uuid.UUID, *, sub: uuid.UUID | None = None
) -> dict[str, str]:
    return {
        "Authorization": (
            f"Bearer {proveedor.firmar(tenant_id=tenant, sub=str(sub) if sub else None)}"
        )
    }


async def _persona(tenant: uuid.UUID, *, rol: str = "manager") -> uuid.UUID:
    """Un usuario REAL: `cambiar_estado` escribe `changed_by` con el `sub`
    del token, y esa columna tiene FK compuesta a `users` (C-14)."""
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


def _cuerpo(
    branch_id: uuid.UUID, catalogo: tuple[uuid.UUID, uuid.UUID], *, dominio: str, **extra: Any
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
        "domain_plate": dominio,
        **extra,
    }


def _dominio(numero: int) -> str:
    """`AAA999`, uno por vehiculo. 25 caben en dos letras fijas + 3 digitos."""
    letra = chr(ord("A") + (numero // 900))
    return f"{letra}{letra}{letra}{numero % 900:03d}"


def _sembrar(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    catalogo: tuple[uuid.UUID, uuid.UUID],
    cuantos: int,
) -> list[str]:
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)
    ids = []
    for numero in range(cuantos):
        creado = cliente.post(
            "/api/v1/vehicles",
            json=_cuerpo(sucursal, catalogo, dominio=_dominio(numero)),
            headers=cabecera,
        )
        assert creado.status_code == 201, creado.text
        ids.append(creado.json()["id"])
    return ids


# ── 3.1 · Recorrido completo, siguiendo los cursores ─────────────────────────


def test_recorrido_completo_de_25_con_limit_10_da_tres_paginas_sin_repetir(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, _ = agencia
    esperados = set(_sembrar(cliente, proveedor, agencia, modelo_del_catalogo, 25))
    cabecera = _cabecera(proveedor, tenant)

    vistos: list[str] = []
    cursor: str | None = None
    paginas = 0

    while True:
        parametros = {"limit": 10} | ({"cursor": cursor} if cursor else {})
        respuesta = cliente.get("/api/v1/vehicles", params=parametros, headers=cabecera)
        assert respuesta.status_code == 200
        paginas += 1
        vistos.extend(v["id"] for v in respuesta.json())
        cursor = respuesta.headers.get("X-Next-Cursor")
        if cursor is None:
            break
        assert paginas < 20, "el recorrido no converge"

    assert paginas == 3
    assert set(vistos) == esperados
    assert len(vistos) == len(set(vistos)), "un vehiculo aparecio mas de una vez"


def test_la_ultima_pagina_no_trae_el_header_x_next_cursor(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, _ = agencia
    _sembrar(cliente, proveedor, agencia, modelo_del_catalogo, 5)

    respuesta = cliente.get(
        "/api/v1/vehicles", params={"limit": 10}, headers=_cabecera(proveedor, tenant)
    )

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 5
    assert "X-Next-Cursor" not in respuesta.headers


# ── 3.2 · El cuerpo sigue siendo un array ────────────────────────────────────


def test_el_cuerpo_de_la_respuesta_sigue_siendo_un_array(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Protege a `frontend-web/src/lib/api.ts`, que valida `Array.isArray`."""
    tenant, _ = agencia
    _sembrar(cliente, proveedor, agencia, modelo_del_catalogo, 3)

    respuesta = cliente.get(
        "/api/v1/vehicles", params={"limit": 10}, headers=_cabecera(proveedor, tenant)
    )

    assert isinstance(respuesta.json(), list)


# ── 3.3 · `limit` por encima del maximo se acota ─────────────────────────────


def test_limit_por_encima_del_maximo_se_acota_sin_fallar(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    from app.core.pagination import TAMANO_MAXIMO

    tenant, _ = agencia
    _sembrar(cliente, proveedor, agencia, modelo_del_catalogo, 3)

    respuesta = cliente.get(
        "/api/v1/vehicles",
        params={"limit": TAMANO_MAXIMO + 500},
        headers=_cabecera(proveedor, tenant),
    )

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 3


def test_sin_limit_usa_el_tamano_por_defecto(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    from app.core.pagination import TAMANO_POR_DEFECTO

    tenant, _ = agencia
    _sembrar(cliente, proveedor, agencia, modelo_del_catalogo, TAMANO_POR_DEFECTO + 3)

    respuesta = cliente.get("/api/v1/vehicles", headers=_cabecera(proveedor, tenant))

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == TAMANO_POR_DEFECTO
    assert "X-Next-Cursor" in respuesta.headers


# ── 3.4 · Aislamiento: cursor de otra agencia ────────────────────────────────


async def test_un_cursor_de_otra_agencia_se_rechaza_y_cuenta_como_violacion(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant_a, _ = agencia
    otra_agencia = await agencia_con_sucursal()
    tenant_b, _ = otra_agencia
    _sembrar(cliente, proveedor, otra_agencia, modelo_del_catalogo, 3)

    cursor_ajeno = cliente.get(
        "/api/v1/vehicles", params={"limit": 1}, headers=_cabecera(proveedor, tenant_b)
    ).headers["X-Next-Cursor"]

    antes = violaciones_de_aislamiento()
    rechazo = cliente.get(
        "/api/v1/vehicles",
        params={"cursor": cursor_ajeno},
        headers=_cabecera(proveedor, tenant_a),
    )

    assert rechazo.status_code == 400
    assert rechazo.json()["code"] == "cursor_invalido"
    assert violaciones_de_aislamiento() == antes + 1


# ── 3.5 · Cursor ilegible: mismo error, sin distincion ───────────────────────


def test_un_cursor_ilegible_da_el_mismo_error_que_uno_de_otra_agencia(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, _ = agencia

    rechazo = cliente.get(
        "/api/v1/vehicles",
        params={"cursor": "no-es-un-cursor-valido-!!"},
        headers=_cabecera(proveedor, tenant),
    )

    assert rechazo.status_code == 400
    assert rechazo.json()["code"] == "cursor_invalido"


# ── 3.6 · Paginar con filtros ────────────────────────────────────────────────


async def test_paginar_con_filtro_de_estado_da_el_mismo_conjunto_que_sin_paginar(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """El error clasico: aplicar el cursor antes que el filtro deja "faltan
    autos" mucho despues. Se cambian tres a `available` y se recorre por
    paginas de a 2 filtrando por ese estado."""
    tenant, _ = agencia
    ids = _sembrar(cliente, proveedor, agencia, modelo_del_catalogo, 7)
    cabecera = _cabecera(proveedor, tenant, sub=await _persona(tenant))

    disponibles_esperados = set(ids[:3])
    for vehiculo_id in disponibles_esperados:
        cambio = cliente.post(
            f"/api/v1/vehicles/{vehiculo_id}/status",
            json={"status": "available"},
            headers=cabecera,
        )
        assert cambio.status_code == 200, cambio.text

    vistos: list[str] = []
    cursor: str | None = None
    while True:
        parametros = {"status": "available", "limit": 2} | ({"cursor": cursor} if cursor else {})
        respuesta = cliente.get("/api/v1/vehicles", params=parametros, headers=cabecera)
        vistos.extend(v["id"] for v in respuesta.json())
        cursor = respuesta.headers.get("X-Next-Cursor")
        if cursor is None:
            break

    assert set(vistos) == disponibles_esperados
    assert len(vistos) == len(disponibles_esperados)


# ── 3.8 · La pagina trae instancias de Vehicle, no Row ───────────────────────


async def test_el_repositorio_paginado_devuelve_instancias_de_vehicle(
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Contra la refactorizacion que "simplifica" `select(Vehicle, ...)` a
    `select(Vehicle)` a secas y rompe `paginar` en silencio (`D-2`, riesgo de
    `design.md`)."""
    from app.db.session import sesion_de_tenant
    from app.modules.stock.models import Vehicle
    from app.modules.stock.repository import VehicleRepository
    from app.modules.stock.schemas import FiltrosDeBusqueda, VehiculoCrear
    from app.modules.stock.service import StockService

    tenant, sucursal = agencia
    marca, modelo = modelo_del_catalogo

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        await StockService(sesion, tenant).crear(
            VehiculoCrear(
                branch_id=sucursal,
                brand_id=marca,
                model_id=modelo,
                year=2020,
                mileage_km=1,
                color="Negro",
                fuel_type="diesel",
                transmission="manual",
                body_type="pickup",
                price_ars="1.00",
                domain_plate="ZZ001ZZ",
            )
        )

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        pagina = await VehicleRepository(sesion, tenant).listar_paginado(
            FiltrosDeBusqueda(), tenant=tenant
        )

    assert len(pagina.items) == 1
    assert isinstance(pagina.items[0], Vehicle)
