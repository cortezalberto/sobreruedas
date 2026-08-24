"""El gate de `platform/api-conventions` — C-15, `T-080`/`T-078`, `design.md` D-6.

POR QUE UN GATE Y NO DISCIPLINA
─────────────────────────────────
Porque la disciplina ya fallo, de forma documentada. `platform/api-conventions`
describe dos convenciones **como si los endpoints las cumplieran** desde C-02:

    1. Toda ruta `POST` que CREA un recurso declara `Idempotency-Key`.
    2. Toda ruta `GET` que devuelve una COLECCION declara `cursor` y `limit`.

Hasta este change no las cumplia ninguna — los dos modulos (`core/idempotency.py`,
`core/pagination.py`) estaban escritos, probados y DESCONECTADOS, y nada se puso
rojo. El precedente de que esto funciona ya existe: `test_auth_rutas.py`
recorrio las rutas reales y encontro un endpoint sin token que la lectura habia
dado por bueno, y la verificacion de C-02 hizo lo mismo con las celdas de RBAC.

QUE MIRA, Y QUE NO
───────────────────
El recorrido y los cuatro detectores (`es_creacion`, `es_coleccion`,
`declara_idempotency_key`, `declara_cursor_y_limit`) viven en `tests/rutas.py` —
ver su docstring para el porque de cada heuristica. Ninguna heuristica lee la
FORMA del path (si termina en `{param}` o no): esa senal marca como
"coleccion" a `GET /tenant/me`, `GET /auth/me`, `/health` y `/ready`, que
devuelven un objeto — puro ruido de excepciones por cada corrida. Se lee el
`status_code` declarado (creacion) y el TIPO de retorno resuelto (coleccion),
que son las dos unicas senales que no admiten una segunda lectura.

LA TERCERA EXIGENCIA DE `D-6` NO ESTA ACA
───────────────────────────────────────────
`D-6` tambien pide que "ningun endpoint de creacion con clave de idempotencia
elija su schema de respuesta segun la concesion". Esa es una propiedad de UN
endpoint especifico (`POST /vehicles`), no algo que se pueda leer por reflexion
generica sobre cualquier ruta — se prueba con roles reales, contra la respuesta
real. Ya tiene su test, y es la precondicion del patron de `D-1`:
`test_post_vehicles_responde_la_misma_forma_para_todos_los_roles` en
`test_vehicles_idempotencia.py`. Duplicarla aca seria una segunda copia de la
misma asercion, verificada de una forma mas debil.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import FastAPI, Header, Query, status
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import create_app

from ..rutas import (
    declara_cursor_y_limit,
    declara_idempotency_key,
    es_coleccion,
    es_creacion,
    motivos_faltantes,
    rutas_que_incumplen_convenciones,
    todas_las_rutas,
)

# ── 5.1 · Una creacion sin `Idempotency-Key` se marca ───────────────────────


def test_un_post_de_creacion_sin_idempotency_key_incumple() -> None:
    app = FastAPI()

    @app.post("/juguetes", status_code=status.HTTP_201_CREATED)
    async def _crear() -> dict[str, str]:
        return {}

    incumplimientos = rutas_que_incumplen_convenciones(app, excepciones={})

    assert ("POST", "/juguetes") in incumplimientos
    assert "Idempotency-Key" in incumplimientos[("POST", "/juguetes")]


def test_un_post_que_no_crea_no_incumple_aunque_no_tenga_la_clave() -> None:
    """El contrapeso del 5.1: un `POST` de accion (`200`, no `201`) no es una
    creacion, y no se le puede pedir una clave que no tiene sentido ahi —
    `POST /vehicles/{id}/status` es exactamente este caso."""
    app = FastAPI()

    @app.post("/juguetes/{id}/status")
    async def _cambiar_estado(id: str) -> dict[str, str]:
        return {}

    assert rutas_que_incumplen_convenciones(app, excepciones={}) == {}


# ── 5.2 · Una coleccion sin `cursor`/`limit` se marca ───────────────────────


def test_un_get_de_coleccion_sin_cursor_ni_limit_incumple() -> None:
    app = FastAPI()

    @app.get("/juguetes")
    async def _listar() -> list[str]:
        return []

    incumplimientos = rutas_que_incumplen_convenciones(app, excepciones={})

    assert ("GET", "/juguetes") in incumplimientos
    assert "cursor" in incumplimientos[("GET", "/juguetes")]


def test_un_get_de_coleccion_con_cursor_y_limit_no_incumple() -> None:
    app = FastAPI()

    @app.get("/juguetes")
    async def _listar(
        cursor: Annotated[str | None, Query()] = None,
        limit: Annotated[int, Query()] = 20,
    ) -> list[str]:
        return []

    assert rutas_que_incumplen_convenciones(app, excepciones={}) == {}


def test_un_get_de_un_solo_objeto_no_es_coleccion_aunque_no_pagine() -> None:
    """El contrapeso que evita el cajon de excepciones (ver el docstring del
    modulo): `GET /tenant/me`, `GET /auth/me`, `/health`, `/ready` devuelven UN
    objeto, y ninguno deberia necesitar una excepcion para pasar el gate."""
    app = FastAPI()

    @app.get("/me")
    async def _yo() -> dict[str, str]:
        return {"id": "u-1"}

    assert rutas_que_incumplen_convenciones(app, excepciones={}) == {}


# ── 5.3 / 5.4 · La lista de excepciones exige motivo ────────────────────────


def test_una_excepcion_sin_motivo_no_excusa_nada() -> None:
    """Sin este test la lista de excepciones se vuelve un cajon (`D-6`): una
    entrada con motivo vacio pasaria la revision de un diff sin que nadie
    tuviera que justificar nada."""
    app = FastAPI()

    @app.get("/juguetes")
    async def _listar() -> list[str]:
        return []

    excepciones = {("GET", "/juguetes"): ""}

    assert motivos_faltantes(excepciones) == {("GET", "/juguetes")}
    # Y la excepcion sin motivo tampoco excusa a la ruta del gate principal:
    # `rutas_que_incumplen_convenciones` no la trata como valida.
    assert ("GET", "/juguetes") in rutas_que_incumplen_convenciones(app, excepciones=excepciones)


def test_una_excepcion_con_motivo_pasa_y_excusa_la_ruta() -> None:
    """El contrapeso del 5.3: mismo caso, con motivo — no hay incumplimiento
    que reportar y `motivos_faltantes` no la senala."""
    app = FastAPI()

    @app.get("/juguetes")
    async def _listar() -> list[str]:
        return []

    excepciones = {("GET", "/juguetes"): "coleccion acotada por diseno, no crece"}

    assert motivos_faltantes(excepciones) == set()
    assert rutas_que_incumplen_convenciones(app, excepciones=excepciones) == {}


# ── Probar los cuatro detectores por separado, no solo el gate ─────────────


def test_es_creacion_distingue_201_de_otros_codigos() -> None:
    app = FastAPI()

    @app.post("/a", status_code=status.HTTP_201_CREATED)
    async def _a() -> dict[str, str]:
        return {}

    @app.post("/b", status_code=status.HTTP_202_ACCEPTED)
    async def _b() -> dict[str, str]:
        return {}

    rutas = {r.path: r for r in todas_las_rutas(app)}

    assert es_creacion(rutas["/a"]) is True
    assert es_creacion(rutas["/b"]) is False


def test_es_coleccion_lee_el_tipo_resuelto_no_el_texto_de_la_anotacion() -> None:
    """`app/` entero usa `from __future__ import annotations`, y este MODULO
    de prueba tambien (linea 30): si el detector leyera `__annotations__` a
    secas encontraria el STRING `"list[str]"` en vez del tipo, y `get_origin`
    de un string da `None` siempre — el chequeo pasaria callado sobre
    cualquier endpoint. Los dos endpoints de abajo quedan definidos bajo esa
    misma importacion diferida, asi que este test ejercita exactamente ese
    camino sin tener que simularlo aparte."""
    app = FastAPI()

    @app.get("/coleccion")
    async def _listar() -> list[str]:
        return []

    @app.get("/objeto")
    async def _uno() -> dict[str, str]:
        return {}

    rutas = {r.path: r for r in todas_las_rutas(app)}

    assert es_coleccion(rutas["/coleccion"]) is True
    assert es_coleccion(rutas["/objeto"]) is False


def test_declara_idempotency_key_lee_el_alias_http_no_el_nombre_de_python() -> None:
    app = FastAPI()

    @app.post("/con-clave", status_code=status.HTTP_201_CREATED)
    async def _con(
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> dict[str, str]:
        return {}

    @app.post("/sin-clave", status_code=status.HTTP_201_CREATED)
    async def _sin() -> dict[str, str]:
        return {}

    rutas = {r.path: r for r in todas_las_rutas(app)}

    assert declara_idempotency_key(rutas["/con-clave"]) is True
    assert declara_idempotency_key(rutas["/sin-clave"]) is False


class _FiltrosDeJuguete(BaseModel):
    """A nivel de modulo y no local a un test, a proposito: una clase LOCAL a
    una funcion no es resoluble por `get_type_hints` bajo
    `from __future__ import annotations` —su nombre no esta en los globals del
    modulo—, y eso rompe la deteccion de un modo que no tiene nada que ver con
    lo que este test quiere probar. `FiltrosDeBusqueda`, la real, ya vive a
    nivel de modulo en `modules/stock/schemas.py`."""

    cursor: str | None = None
    limit: int = 20
    q: str | None = None


def test_declara_cursor_y_limit_desarma_un_modelo_anidado() -> None:
    """La forma real de `GET /vehicles`: `cursor`/`limit` no son parametros
    sueltos de la funcion, son CAMPOS de un modelo Pydantic recibido por
    `Query()` — ver el docstring de `listar_vehiculos`."""
    app = FastAPI()

    @app.get("/con-filtros")
    async def _listar(filtros: Annotated[_FiltrosDeJuguete, Query()]) -> list[str]:
        return []

    rutas = {r.path: r for r in todas_las_rutas(app)}

    assert declara_cursor_y_limit(rutas["/con-filtros"]) is True


# ── 5.5 / 5.6 · El gate contra la aplicacion real ───────────────────────────

# Excepciones con motivo obligatorio (`D-6`). Cada entrada es una decision que
# se lee en este diff, no un permiso permanente:
#
#   - `vehicles/{id}/history` es la UNICA excepcion de ESTE change: `D-5` de
#     `vehiculos-api` decidio que el historial no pagina porque la maquina de
#     estados acota el numero de filas — seis estados, nueve transiciones
#     legales, cada una una accion humana. El peor caso realista entra en una
#     pantalla.
#
#   - El resto es DEUDA DE OTROS MODULOS que este gate encontro al correr
#     contra la aplicacion real (`D-6`, tarea 5.6): existia desde que cada
#     endpoint se escribio, y hasta hoy nada la habia puesto en rojo. No se
#     arregla en este change — cada una queda con el nombre del change que la
#     tiene en su scope, para que se cierre ahi y no se pierda.
EXCEPCIONES: dict[tuple[str, str], str] = {
    ("GET", "/api/v1/vehicles/{vehiculo_id}/history"): (
        "D-5 de vehiculos-api: el historial no pagina — la maquina de estados "
        "acota el numero de filas a un puñado por vehiculo"
    ),
    ("GET", "/api/v1/plans"): "pendiente — C-04 (tenancy-planes-y-limites)",
    ("GET", "/api/v1/catalog/brands"): "pendiente — C-13 (catalogo-de-vehiculos)",
    ("GET", "/api/v1/catalog/brands/{marca_id}/models"): (
        "pendiente — C-13 (catalogo-de-vehiculos)"
    ),
    ("GET", "/api/v1/imports"): "pendiente — C-17 (importacion-csv-de-stock)",
    (
        "GET",
        "/api/v1/branches",
    ): "pendiente — C-05 (identidad-auth-y-tenant-endpoints, ya archivado; deuda sin change asignado)",
    ("GET", "/api/v1/users"): "pendiente — C-12 (usuarios-invitaciones-y-settings)",
    ("POST", "/api/v1/branches"): (
        "pendiente — C-05 (identidad-auth-y-tenant-endpoints, ya archivado; deuda sin change asignado)"
    ),
    ("POST", "/api/v1/users/invitations"): "pendiente — C-12 (usuarios-invitaciones-y-settings)",
}


def test_las_excepciones_declaradas_tienen_motivo() -> None:
    """El gate de las excepciones, antes que el gate de las rutas: una entrada
    sin motivo no deberia poder colarse en este archivo."""
    assert motivos_faltantes(EXCEPCIONES) == set()


@pytest.fixture
def app_real(entorno_valido: dict[str, str]) -> FastAPI:
    """La aplicacion COMPLETA, con el conjunto minimo de variables que
    `Settings` necesita para construirse (`entorno_valido`, `conftest.py` de
    raiz) — el mismo fixture que usa `test_auth_rutas.py` para el mismo
    proposito: el gate tiene que correr sobre la app que sirve trafico real, no
    sobre una reconstruccion parcial."""
    from app.config import get_settings

    get_settings.cache_clear()
    return create_app()


def test_la_aplicacion_real_no_incumple_mas_alla_de_lo_declarado(app_real: FastAPI) -> None:
    """5.5/5.6: el gate, contra la app de verdad.

    Si esto se pone rojo es porque una ruta NUEVA (o una vieja recien
    detectada) incumple una de las dos convenciones y no esta en
    `EXCEPCIONES` — hay que agregarla con motivo, o corregir el endpoint.
    Que la lista de mas arriba sea mas larga de lo que a alguien le gustaria
    es exactamente el punto de `D-6`: la deuda ahora esta CONTADA, no
    escondida.
    """
    incumplimientos = rutas_que_incumplen_convenciones(app_real, excepciones=EXCEPCIONES)

    assert incumplimientos == {}, (
        f"rutas que incumplen platform/api-conventions y no estan en EXCEPCIONES: "
        f"{sorted(incumplimientos)}"
    )


def test_el_gate_corre_sobre_la_misma_app_que_sirve_trafico_real(app_real: FastAPI) -> None:
    """Que quede probado y no solo dicho: `app_real` es una `TestClient`
    funcional, no un objeto a medio construir."""
    assert TestClient(app_real).get("/health").status_code == 200
