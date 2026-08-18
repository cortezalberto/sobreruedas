"""Los endpoints del catalogo de vehiculos — C-13.

`test_catalogo_de_vehiculos.py` prueba la BASE: que el seed entro, que todos
leen y nadie escribe. Acá se prueba el contrato HTTP, que es otra cosa: el
orden en que llegan las filas, la forma de la salida y que una marca inexistente
se distinga de una marca sin modelos.

Sin mocks de base de datos (regla dura 8). Se corre con:

    docker compose run --rm backend pytest -m integration
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

from .soporte import DSN_APLICACION, reponer_entorno

pytestmark = pytest.mark.integration


@pytest.fixture
def cliente(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Igual que el de `test_planes_router.py` — ver su docstring.

    Repone el entorno que `entorno_limpio` borra y descachea `get_settings`,
    envenenado por los tests de sondas. Duplicado a proposito: cuando aparezca
    el tercer archivo que lo necesite, se mueve al conftest. Con dos, moverlo
    cambiaria el DSN con el que corren las sondas de salud.
    """
    reponer_entorno(monkeypatch, dsn=DSN_APLICACION)

    # `with` y no `TestClient(...)` a secas: sin el context manager, starlette
    # abre un portal —y con el un event loop— POR PEDIDO, y el engine cacheado
    # del primero queda atado a un loop que ya no existe. El segundo pedido del
    # mismo test muere con "attached to a different loop", lejos de su causa.
    #
    # Con un solo pedido por test no se nota, y por eso aparecio recien al
    # escribir el primer test que hace dos.
    with TestClient(create_app()) as cliente:
        yield cliente


# ── Marcas ───────────────────────────────────────────────────────────────────


def test_el_catalogo_devuelve_las_cuarenta_marcas(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/v1/vehicle-brands")

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 40


def test_las_marcas_llegan_en_orden_alfabetico(cliente: TestClient) -> None:
    """Quien busca una marca entre 40 la busca por nombre.

    El orden de insercion es del seed, no del que mira la pantalla — y sin
    `ORDER BY` explicito PostgreSQL puede devolverlas en cualquier orden.
    """
    nombres = [marca["name"] for marca in cliente.get("/api/v1/vehicle-brands").json()]

    assert nombres == sorted(nombres)


def test_la_marca_no_expone_columnas_internas(cliente: TestClient) -> None:
    marca = cliente.get("/api/v1/vehicle-brands").json()[0]

    assert set(marca) == {"id", "name", "slug", "origin_country"}


# ── Modelos de una marca ─────────────────────────────────────────────────────


def test_los_modelos_de_una_marca_son_solo_de_esa_marca(cliente: TestClient) -> None:
    marcas = {m["slug"]: m["id"] for m in cliente.get("/api/v1/vehicle-brands").json()}

    modelos = cliente.get("/api/v1/vehicle-brands/toyota/models").json()

    assert modelos, "Toyota tiene modelos en el seed"
    assert {m["brand_id"] for m in modelos} == {marcas["toyota"]}


def test_los_modelos_llegan_del_mas_nuevo_al_mas_viejo(cliente: TestClient) -> None:
    """Al cargar stock se busca casi siempre un modelo reciente.

    Dejarlo al final de una lista alfabetica obliga a recorrerla entera.
    """
    anios = [m["year_from"] for m in cliente.get("/api/v1/vehicle-brands/toyota/models").json()]

    assert anios == sorted(anios, reverse=True)


def test_un_modelo_vigente_viaja_con_year_to_nulo(cliente: TestClient) -> None:
    """`null` significa "se sigue vendiendo", no "no sabemos".

    Es una distincion que el cliente necesita hacer, y si el schema omitiera el
    campo cuando esta vacio, las dos situaciones llegarian iguales.
    """
    modelo = cliente.get("/api/v1/vehicle-brands/toyota/models").json()[0]

    assert "year_to" in modelo
    assert modelo["year_to"] is None


def test_una_marca_inexistente_da_404_y_no_una_lista_vacia(cliente: TestClient) -> None:
    """Son dos situaciones distintas y no pueden compartir respuesta.

    "esta marca no tiene modelos cargados" es un catalogo incompleto; "esta
    marca no existe" es un error del que pregunta. Un `[]` para las dos esconde
    la segunda, y el frontend no puede avisar de lo que no ve.
    """
    respuesta = cliente.get("/api/v1/vehicle-brands/marca-que-no-existe/models")

    assert respuesta.status_code == 404


def test_el_404_llega_como_problem_json(cliente: TestClient) -> None:
    """El mismo formato de error que el resto de la aplicacion.

    Que el 404 salga por `HTTPException` no lo exime: el manejador de la
    aplicacion lo convierte a RFC 7807 igual que a los errores de dominio.
    """
    respuesta = cliente.get("/api/v1/vehicle-brands/marca-que-no-existe/models")

    assert respuesta.headers["content-type"].startswith("application/problem+json")
    assert respuesta.json()["status"] == 404
