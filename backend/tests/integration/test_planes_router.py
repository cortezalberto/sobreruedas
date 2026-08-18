"""El primer endpoint de dominio del sistema — catalogo de planes.

POR QUE ESTE ENDPOINT Y NO OTRO. El prototipo necesita un recorrido completo
—Next.js, HTTP, FastAPI, SQLAlchemy, PostgreSQL— con datos de verdad, y hasta
que `E-001` no cierre no se pueden tocar ni `users` ni RBAC ni los endpoints de
tenant (son C-05, y su tarea 0.1 es justamente esa puerta).

`plans` no cae en esa zona:

  - Es catalogo GLOBAL, no datos de un tenant. Figura en `EXENTAS_DE_RLS` junto
    con `tenants` (`RN-MT-09`), asi que consultarlo sin contexto de tenant no
    viola la regla dura 1 — no hay tenant al que acotarlo.
  - Ya esta sembrado por la migracion `005_planes` con los tres planes de
    `plan-gtm`, asi que devuelve datos reales sin fixtures.
  - No necesita identidad: es la grilla comercial, lo mismo que se publica.

Sin mocks de base de datos (regla dura 8). Se corre con:

    docker compose run --rm backend pytest -m integration
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

from .soporte import DSN_APLICACION, URL_REDIS

pytestmark = pytest.mark.integration


@pytest.fixture
def cliente(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Un cliente por test, contra los servicios reales.

    ⚠️ LAS DOS COSAS QUE HACEN FALTA ACA, Y NINGUNA ES OPCIONAL.

    1. **Reponer el entorno.** El fixture `entorno_limpio` del conftest raiz es
       `autouse` y borra TODA variable del proyecto antes de cada test. Un
       endpoint que consulta la base necesita `DATABASE_URL`, asi que hay que
       volver a ponerla. Los demas tests de integracion no lo necesitan porque
       abren sesion con un DSN explicito y nunca pasan por la configuracion.

    2. **Descachear `get_settings`.** Es `lru_cache(maxsize=1)`, y varios tests
       de `test_app_health.py` lo envenenan a proposito apuntando `DATABASE_URL`
       a un puerto cerrado para probar el 503. `monkeypatch` restaura la
       variable al terminar; el objeto `Settings` mal construido se queda en la
       cache. Sin este `cache_clear()` estos tests **pasan solos y fallan en la
       suite completa**, conectandose al puerto muerto que dejo otro archivo.

    Se descubrio armando este router: es el primer endpoint del sistema que
    llega a la base a traves de la configuracion de la aplicacion, asi que es el
    primero que pisa las dos cosas. `test_app_health.py` resuelve lo mismo con
    su propio `entorno_real`; cuando haya un tercero, esto va al conftest.

    De alcance por test y no por modulo: con `entorno_limpio` borrando variables
    entre tests, un cliente de modulo sobrevive a su propio entorno.
    """
    monkeypatch.setenv("DATABASE_URL", DSN_APLICACION)
    monkeypatch.setenv("REDIS_URL", URL_REDIS)
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "no-se-usa-en-este-test")
    monkeypatch.setenv("S3_ACCESS_KEY", "no-se-usa-en-este-test")
    monkeypatch.setenv("S3_SECRET_KEY", "no-se-usa-en-este-test")
    monkeypatch.setenv("TENANT_SECRETS_MASTER_KEY", "no-se-usa-en-este-test")
    get_settings.cache_clear()

    # `with` y no `TestClient(...)` a secas: sin el context manager, starlette
    # abre un portal —y con el un event loop— POR PEDIDO, y el engine cacheado
    # del primero queda atado a un loop que ya no existe. El segundo pedido del
    # mismo test muere con "attached to a different loop", lejos de su causa.
    #
    # Con un solo pedido por test no se nota, y por eso aparecio recien al
    # escribir el primer test que hace dos.
    with TestClient(create_app()) as cliente:
        yield cliente


def test_el_catalogo_devuelve_los_tres_planes_sembrados(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/v1/plans")

    assert respuesta.status_code == 200
    codigos = [plan["code"] for plan in respuesta.json()]
    assert codigos == ["starter", "pro", "enterprise"]


def test_el_orden_es_por_precio_y_no_el_que_devuelva_la_base(cliente: TestClient) -> None:
    """Un catalogo comercial que cambia de orden entre peticiones no es un catalogo.

    Sin `ORDER BY` explicito PostgreSQL puede devolver las filas en cualquier
    orden, y el dia que alguien actualice un plan la grilla de precios se
    reordena sola en la pantalla del cliente.
    """
    precios = [float(plan["price_ars"]) for plan in cliente.get("/api/v1/plans").json()]

    assert precios == sorted(precios)


def test_cada_plan_trae_los_limites_que_la_grilla_necesita(cliente: TestClient) -> None:
    starter = cliente.get("/api/v1/plans").json()[0]

    assert starter["max_users"] > 0
    assert starter["max_vehicles"] > 0
    assert starter["max_branches"] > 0
    assert isinstance(starter["modules"], list)


def test_el_plan_sin_techo_viaja_como_cero_y_no_como_nulo(cliente: TestClient) -> None:
    """`0 = ilimitado` es la convencion de `spec-tecnica` 3.3, y cruza el HTTP.

    Enterprise es el unico plan con `max_vehicles = 0`. Si el schema de salida
    lo tradujera a `null`, el frontend tendria que adivinar si el campo falta o
    si el plan no tiene tope — que son cosas distintas. La convencion se sostiene
    de punta a punta o no sirve.
    """
    enterprise = next(p for p in cliente.get("/api/v1/plans").json() if p["code"] == "enterprise")

    assert enterprise["max_vehicles"] == 0


def test_el_catalogo_no_expone_columnas_internas(cliente: TestClient) -> None:
    """Un schema de salida es una lista blanca, no un volcado del modelo.

    `is_active` decide que se muestra, no es informacion del plan; y filtrar por
    el en el servidor mientras se lo publica igual es contradictorio.
    """
    plan = cliente.get("/api/v1/plans").json()[0]

    assert "is_active" not in plan
    assert "created_at" not in plan
