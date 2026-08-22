"""La interfaz `Vehiculo` del frontend declara los campos que el backend manda.

POR QUE HACIA FALTA ESTE GUARDIAN
──────────────────────────────────
Hasta la ficha, `frontend-web/src/lib/api.ts` declaraba **once** campos de los
veintitres que `VehiculoSalida` devuelve. No estaba roto —el listado usaba esos
once— pero era un contrato a medias: los otros doce llegaban por la red sin que
TypeScript supiera que existian, asi que cada pantalla nueva tenia que
redescubrir el schema leyendo Python.

La ficha los declaro todos. Este test es lo que impide que la lista se vuelva a
quedar corta, y sobre todo que se quede LARGA: un campo que el backend saca
—porque una regla lo prohibe, como paso con `password_hash` y con `mfa_secret`—
seguiria declarado del lado del cliente, y alguien lo leeria como si viajara.

POR QUE VIVE DEL LADO DEL BACKEND
──────────────────────────────────
Mismo motivo que `test_transiciones_espejadas.py` y `test_alta_espejada.py`: aca
esta el original. Leer un literal de TypeScript desde Python es un `re` corto; al
reves habria que leer Pydantic desde TypeScript.

Si esto falla, **la que manda es la de `schemas.py`**: el frontend se corrige.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.modules.stock.schemas import VehiculoSalida, VehiculoSalidaConCosto

ESPEJO = Path(__file__).resolve().parents[3] / "frontend-web" / "src" / "lib" / "api.ts"

# `  acquisition_cost_ars?: string | null;` -> ('acquisition_cost_ars', '?')
#
# Anclado a DOS espacios de indentacion, que es el nivel de un campo de la
# interfaz. Las lineas de comentario empiezan con `/` o `*` y no matchean.
_CAMPO = re.compile(r"^ {2}(\w+)(\??):", re.MULTILINE)


def _bloque_de_la_interfaz() -> str:
    """El cuerpo de `export interface Vehiculo { ... }`, sin nada alrededor.

    ⚠️ LEVANTA SI NO LO ENCUENTRA. Es el contrapeso incorporado: si alguien
    renombra la interfaz, devolver una cadena vacia dejaria la comparacion
    enfrentando dos conjuntos —uno vacio y uno lleno— y el mensaje de error
    hablaria de veintitres campos faltantes en vez de decir la verdad, que es
    que el parseo dejo de funcionar.
    """
    fuente = ESPEJO.read_text(encoding="utf-8")
    marca = "export interface Vehiculo {"
    if marca not in fuente:
        raise AssertionError(f"`{marca}` ya no esta en {ESPEJO}")

    # `\n}` cierra la interfaz: los `}` de adentro de un comentario van
    # indentados o pegados a otro texto.
    return fuente.split(marca, 1)[1].split("\n}", 1)[0]


def _campos_del_frontend() -> dict[str, bool]:
    """Los campos declarados, y si cada uno es opcional (`?`)."""
    return {
        coincidencia.group(1): coincidencia.group(2) == "?"
        for coincidencia in _CAMPO.finditer(_bloque_de_la_interfaz())
    }


# ── Contrapesos ─────────────────────────────────────────────────────────────
#
# Sin estos, un parseo que deja de matchear compara dos cosas vacias y pasa en
# verde. Un guardian que se apaga solo es peor que ninguno.


def test_el_archivo_del_espejo_existe() -> None:
    assert ESPEJO.is_file(), f"no esta {ESPEJO}"


def test_la_interfaz_del_frontend_no_esta_vacia() -> None:
    assert len(_campos_del_frontend()) == len(VehiculoSalidaConCosto.model_fields)


# ── El espejo ───────────────────────────────────────────────────────────────


def test_la_interfaz_declara_exactamente_los_campos_del_schema() -> None:
    """`VehiculoSalidaConCosto`, que es `VehiculoSalida` mas el costo.

    Se compara contra el schema CON costo porque la interfaz declara el campo
    —opcional— para poder preguntar por su presencia. Ver `RN-ST-12`.
    """
    backend = set(VehiculoSalidaConCosto.model_fields)
    frontend = set(_campos_del_frontend())

    assert frontend == backend, (
        "la interfaz `Vehiculo` del frontend se despego de `VehiculoSalida`.\n"
        f"  el backend manda y el frontend no declara: {sorted(backend - frontend)}\n"
        f"  el frontend declara y el backend no manda: {sorted(frontend - backend)}"
    )


def test_el_costo_es_el_unico_campo_opcional() -> None:
    """`RN-ST-12` escrito en el sistema de tipos, y nada mas que eso.

    `acquisition_cost_ars` es opcional porque la clave **no viaja** para un rol
    que no puede verla — no viaja en `null`, no viaja. Cualquier OTRO campo
    marcado con `?` seria una laxitud sin regla detras: haria que TypeScript
    dejara de exigir contemplar un caso que el backend nunca produce, y el sitio
    donde eso se nota es una pantalla mostrando `undefined`.
    """
    opcionales = {campo for campo, es_opcional in _campos_del_frontend().items() if es_opcional}

    assert opcionales == {
        "acquisition_cost_ars"
    }, f"campos opcionales inesperados en la interfaz: {sorted(opcionales)}"


def test_el_costo_no_esta_en_el_schema_base() -> None:
    """El contrapeso del test de arriba, del lado del backend.

    Si alguien agregara `acquisition_cost_ars` a `VehiculoSalida`, el campo
    pasaria a viajarle a TODOS los roles y `RN-ST-12` quedaria sin efecto — sin
    que ninguno de los otros tests de este archivo se enterara, porque la
    interfaz del frontend seguiria coincidiendo.
    """
    assert "acquisition_cost_ars" not in VehiculoSalida.model_fields
