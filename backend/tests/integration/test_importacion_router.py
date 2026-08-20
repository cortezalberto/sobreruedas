"""Los endpoints de importacion, sobre HTTP — C-17, `T-095`.

QUE SE PRUEBA ACA
──────────────────
El contrato del `Flujo 4`: subir devuelve **202** con una corrida en `pending`,
y el polling de esa corrida es de la agencia y de nadie mas.

El encolado se ESPIA, no se ejecuta: lo que hace el worker ya esta probado en
`test_importacion_ejecucion.py` contra PostgreSQL y Redis reales. Levantar
Celery acá probaria a Celery.

Sin mocks de base de datos (regla dura 8).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import auth, tasks
from app.main import create_app
from app.modules.stock.importacion import LIMITE_DE_BYTES, PLANTILLA

from ..emisor_de_tokens import EmisorDePrueba
from .soporte import DSN_APLICACION, reponer_entorno, sesion_de_propietario

pytestmark = pytest.mark.integration


@pytest.fixture
def proveedor() -> EmisorDePrueba:
    return EmisorDePrueba()


@pytest.fixture
def encolados(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    """Espia de `importar_stock.delay`. Sin esto el POST intenta hablar con el
    broker y el test pasa a depender de que Celery este arriba."""
    llamadas: list[tuple[str, ...]] = []
    monkeypatch.setattr(tasks.importar_stock, "delay", lambda *args: llamadas.append(tuple(args)))
    return llamadas


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


async def _agencia() -> uuid.UUID:
    tenant_id, branch_id = uuid.uuid4(), uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO tenants (id, name, slug, cuit, billing_email, status) "
                "VALUES (:id, 'Agencia', :s, :c, 'f@example.com', 'active')"
            ),
            {
                "id": tenant_id,
                "s": f"ag-{tenant_id.hex[:8]}",
                "c": f"30{tenant_id.int % 10**9:09d}0"[:11],
            },
        )
        await sesion.execute(
            text(
                "INSERT INTO branches (id, tenant_id, name, city, province) "
                "VALUES (:id, :t, 'Casa central', 'Mendoza', 'Mendoza')"
            ),
            {"id": branch_id, "t": tenant_id},
        )
    return tenant_id


@pytest.fixture
async def agencia() -> uuid.UUID:
    return await _agencia()


@pytest.fixture
async def otra_agencia() -> uuid.UUID:
    return await _agencia()


def _cabecera(proveedor: EmisorDePrueba, tenant: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {proveedor.firmar(tenant_id=tenant)}"}


def _archivo(contenido: bytes = PLANTILLA.encode("utf-8")) -> dict[str, Any]:
    return {"archivo": ("stock.csv", contenido, "text/csv")}


# ── El contrato del Flujo 4 ─────────────────────────────────────────────────


def test_subir_una_planilla_devuelve_202_y_una_corrida_pendiente(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: uuid.UUID,
    encolados: list[tuple[str, ...]],
) -> None:
    """202 y no 201: cuando responde **no hay ni un vehiculo creado**.

    Un 201 diria que el recurso existe, y el cliente que fuera a buscarlo
    encontraria cero filas y concluiria que fallo.
    """
    respuesta = cliente.post(
        "/api/v1/vehicles/import",
        files=_archivo(),
        headers=_cabecera(proveedor, agencia),
    )

    assert respuesta.status_code == 202
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "pending"
    assert cuerpo["source_filename"] == "stock.csv"
    assert cuerpo["tenant_id"] == str(agencia)


def test_la_tarea_se_encola_con_los_ids_de_la_corrida(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: uuid.UUID,
    encolados: list[tuple[str, ...]],
) -> None:
    """Sin esto el endpoint devolveria 202 y nadie importaria nunca nada — y el
    sintoma seria una corrida en `pending` para siempre."""
    respuesta = cliente.post(
        "/api/v1/vehicles/import", files=_archivo(), headers=_cabecera(proveedor, agencia)
    )

    assert encolados == [(respuesta.json()["id"], str(agencia))]


def test_el_progreso_se_consulta_por_id(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: uuid.UUID,
    encolados: list[tuple[str, ...]],
) -> None:
    cabecera = _cabecera(proveedor, agencia)
    creada = cliente.post("/api/v1/vehicles/import", files=_archivo(), headers=cabecera).json()

    respuesta = cliente.get(f"/api/v1/imports/{creada['id']}", headers=cabecera)

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == creada["id"]


def test_el_listado_trae_las_corridas_de_la_agencia(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: uuid.UUID,
    encolados: list[tuple[str, ...]],
) -> None:
    cabecera = _cabecera(proveedor, agencia)
    cliente.post("/api/v1/vehicles/import", files=_archivo(), headers=cabecera)

    respuesta = cliente.get("/api/v1/imports", headers=cabecera)

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1


# ── Aislamiento ─────────────────────────────────────────────────────────────


def test_una_corrida_ajena_no_se_consulta_ni_con_su_id(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: uuid.UUID,
    otra_agencia: uuid.UUID,
    encolados: list[tuple[str, ...]],
) -> None:
    """404 y no 403: `errors` guarda dominios, chasis y precios de las filas que
    fallaron — o sea, el inventario de esa agencia tal como lo estaba cargando."""
    ajena = cliente.post(
        "/api/v1/vehicles/import",
        files=_archivo(),
        headers=_cabecera(proveedor, otra_agencia),
    ).json()

    respuesta = cliente.get(f"/api/v1/imports/{ajena['id']}", headers=_cabecera(proveedor, agencia))

    assert respuesta.status_code == 404


def test_el_listado_de_una_agencia_no_muestra_las_de_otra(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: uuid.UUID,
    otra_agencia: uuid.UUID,
    encolados: list[tuple[str, ...]],
) -> None:
    cliente.post(
        "/api/v1/vehicles/import",
        files=_archivo(),
        headers=_cabecera(proveedor, otra_agencia),
    )

    respuesta = cliente.get("/api/v1/imports", headers=_cabecera(proveedor, agencia))

    assert respuesta.json() == []


def test_sin_token_no_se_importa(cliente: TestClient) -> None:
    assert cliente.post("/api/v1/vehicles/import", files=_archivo()).status_code == 401
    assert cliente.get("/api/v1/imports").status_code == 401


# ── Rechazos de archivo, dentro del request ─────────────────────────────────


def test_un_archivo_sin_columnas_obligatorias_se_rechaza_al_subir(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: uuid.UUID,
    encolados: list[tuple[str, ...]],
) -> None:
    """Se sabe en milisegundos. Mandarlo al worker obligaria a esperar un ciclo
    de polling para que te digan que subiste el archivo equivocado."""
    respuesta = cliente.post(
        "/api/v1/vehicles/import",
        files=_archivo(b"una,dos\r\n1,2\r\n"),
        headers=_cabecera(proveedor, agencia),
    )

    assert respuesta.status_code == 422
    assert encolados == []


def test_un_archivo_de_mas_de_10_mb_se_rechaza_con_413(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: uuid.UUID,
    encolados: list[tuple[str, ...]],
) -> None:
    """`RN-ST-13`. 413 y no 422: el problema es el TAMAÑO, no el contenido."""
    respuesta = cliente.post(
        "/api/v1/vehicles/import",
        files=_archivo(b"x" * (LIMITE_DE_BYTES + 1024)),
        headers=_cabecera(proveedor, agencia),
    )

    assert respuesta.status_code == 413
    assert encolados == []
