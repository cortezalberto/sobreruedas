"""Tests del verificador de cobertura — tarea 8.2 de C-01.

Por que existe este archivo: `fail_under` de coverage.py compara UN solo
numero. Con `branch = true` ese numero es (lineas cubiertas + ramas cubiertas)
sobre (sentencias + ramas), o sea un promedio ponderado de las dos cosas.

ADR-014 no pide eso. Pide 80 % de LINEAS **y** 60 % de RAMAS, cada uno por su
lado. Un modulo con 95 % de lineas y 20 % de ramas puede dar 84 % combinado y
pasar el `fail_under = 80` sin que nadie se entere. Ese es exactamente el caso
que estos tests fijan.

Se invoca el script como PROCESO, no importando funciones: lo que el pipeline
consume es el codigo de salida, y eso es lo que hay que probar. Un test que
llama a una funcion interna puede pasar mientras el script real devuelve 0
siempre.

Se corren desde la raiz del repositorio:

    python -m pytest tools/tests
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "tools" / "check-coverage.py"


def escribir_cobertura(
    destino: Path,
    *,
    sentencias: int,
    lineas_cubiertas: int,
    ramas: int,
    ramas_cubiertas: int,
) -> Path:
    """Escribe un coverage.json con la forma que emite `coverage json`.

    Solo se llena `totals`: es lo unico que el verificador mira. El resto del
    archivo real (`files`, `meta`) es ruido para este contrato.
    """
    contenido: dict[str, Any] = {
        "meta": {"branch_coverage": True},
        "totals": {
            "num_statements": sentencias,
            "covered_lines": lineas_cubiertas,
            "num_branches": ramas,
            "covered_branches": ramas_cubiertas,
        },
    }
    destino.write_text(json.dumps(contenido), encoding="utf-8")
    return destino


def correr(
    *argumentos: str, entorno: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argumentos],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, **entorno} if entorno else None,
    )


# Una consola que NO puede representar caracteres fuera de Latin-1. Es la de
# Windows por defecto, y tambien la que hereda cualquier subproceso lanzado
# desde Git Bash en esa maquina.
#
# Se fija por variable de entorno y no por deteccion de plataforma para que el
# runner de Linux corra exactamente el mismo caso: un fallo que solo aparece en
# la maquina de quien lo sufre es un fallo que el pipeline nunca va a atajar.
CONSOLA_LATIN1 = {"PYTHONIOENCODING": "cp1252"}


# ── El caso feliz ────────────────────────────────────────────────────────────


def test_por_encima_de_ambos_umbrales_pasa(tmp_path: Path) -> None:
    archivo = escribir_cobertura(
        tmp_path / "coverage.json",
        sentencias=100,
        lineas_cubiertas=90,
        ramas=50,
        ramas_cubiertas=35,
    )
    resultado = correr("--coverage-json", str(archivo))
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "90.00" in resultado.stdout
    assert "70.00" in resultado.stdout


def test_justo_en_el_umbral_pasa(tmp_path: Path) -> None:
    """El umbral es un piso inclusivo: 80 % exacto cumple.

    Si fuera estricto, un proyecto que apunta a 80 % nunca podria llegar.
    """
    archivo = escribir_cobertura(
        tmp_path / "coverage.json",
        sentencias=100,
        lineas_cubiertas=80,
        ramas=100,
        ramas_cubiertas=60,
    )
    assert correr("--coverage-json", str(archivo)).returncode == 0


# ── Los dos umbrales, cada uno por su lado ───────────────────────────────────


def test_lineas_por_debajo_bloquea(tmp_path: Path) -> None:
    archivo = escribir_cobertura(
        tmp_path / "coverage.json",
        sentencias=100,
        lineas_cubiertas=79,
        ramas=100,
        ramas_cubiertas=100,
    )
    resultado = correr("--coverage-json", str(archivo))
    assert resultado.returncode == 1
    assert "lineas" in resultado.stdout.lower()
    assert "79.00" in resultado.stdout


def test_ramas_por_debajo_bloquea_aunque_las_lineas_sobren(tmp_path: Path) -> None:
    """EL test que justifica todo este script.

    95 % de lineas y 20 % de ramas dan 82.14 % combinado: `fail_under = 80` lo
    deja pasar. ADR-014 no, porque las ramas estan 40 puntos por debajo de su
    piso. Si este test se vuelve verde con un verificador que mira un solo
    numero, el verificador esta mal.
    """
    archivo = escribir_cobertura(
        tmp_path / "coverage.json",
        sentencias=100,
        lineas_cubiertas=95,
        ramas=40,
        ramas_cubiertas=8,
    )
    resultado = correr("--coverage-json", str(archivo))
    assert resultado.returncode == 1
    assert "ramas" in resultado.stdout.lower()
    assert "20.00" in resultado.stdout


def test_los_dos_por_debajo_reporta_los_dos(tmp_path: Path) -> None:
    """No se corta en el primer fallo: quien lee el log quiere la lista entera."""
    archivo = escribir_cobertura(
        tmp_path / "coverage.json",
        sentencias=100,
        lineas_cubiertas=50,
        ramas=100,
        ramas_cubiertas=10,
    )
    resultado = correr("--coverage-json", str(archivo))
    assert resultado.returncode == 1
    assert "50.00" in resultado.stdout
    assert "10.00" in resultado.stdout


def test_los_umbrales_son_configurables(tmp_path: Path) -> None:
    """ADR-014 fija 80/60, pero el script no los hardcodea: el frontend usa
    otros y el mismo verificador tiene que servir."""
    archivo = escribir_cobertura(
        tmp_path / "coverage.json",
        sentencias=100,
        lineas_cubiertas=70,
        ramas=100,
        ramas_cubiertas=50,
    )
    assert correr("--coverage-json", str(archivo)).returncode == 1
    aprobado = correr(
        "--coverage-json", str(archivo), "--min-lineas", "70", "--min-ramas", "50"
    )
    assert aprobado.returncode == 0


# ── Casos de borde del propio archivo ────────────────────────────────────────


def test_sin_ramas_en_el_codigo_no_divide_por_cero(tmp_path: Path) -> None:
    """Un proyecto sin una sola bifurcacion tiene 0 ramas. 0/0 no es 0 %: no
    hay nada que cubrir, asi que la exigencia se da por cumplida."""
    archivo = escribir_cobertura(
        tmp_path / "coverage.json",
        sentencias=100,
        lineas_cubiertas=100,
        ramas=0,
        ramas_cubiertas=0,
    )
    resultado = correr("--coverage-json", str(archivo))
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_archivo_inexistente_falla_distinto_que_cobertura_baja(tmp_path: Path) -> None:
    """Codigo 2, no 1. Que no haya archivo es un pipeline roto, no un umbral
    incumplido, y confundirlos manda a buscar tests faltantes que no faltan."""
    resultado = correr("--coverage-json", str(tmp_path / "no-existe.json"))
    assert resultado.returncode == 2
    assert "no-existe.json" in resultado.stdout + resultado.stderr


def test_json_sin_medicion_de_ramas_falla_ruidoso(tmp_path: Path) -> None:
    """Si alguien apaga `branch = true`, el JSON viene sin `num_branches`.

    Dar por buena la corrida seria peor que fallar: el gate de ramas quedaria
    apagado sin que nadie lo note. Se exige el dato.
    """
    archivo = tmp_path / "coverage.json"
    archivo.write_text(
        json.dumps({"totals": {"num_statements": 100, "covered_lines": 100}}),
        encoding="utf-8",
    )
    resultado = correr("--coverage-json", str(archivo))
    assert resultado.returncode == 2
    assert "branch" in (resultado.stdout + resultado.stderr).lower()


def test_json_corrupto_falla_ruidoso(tmp_path: Path) -> None:
    archivo = tmp_path / "coverage.json"
    archivo.write_text("{ esto no es json", encoding="utf-8")
    assert correr("--coverage-json", str(archivo)).returncode == 2


# ── No decrecimiento contra main — tarea 8.4 ─────────────────────────────────


def test_cobertura_que_decrece_bloquea(tmp_path: Path) -> None:
    """Art. 2: la cobertura no decrece entre commits. Ambos umbrales se cumplen
    y aun asi tiene que fallar, porque el punto no es el piso sino la direccion.
    """
    base = escribir_cobertura(
        tmp_path / "base.json", sentencias=100, lineas_cubiertas=95, ramas=100, ramas_cubiertas=90
    )
    actual = escribir_cobertura(
        tmp_path / "actual.json", sentencias=100, lineas_cubiertas=90, ramas=100, ramas_cubiertas=90
    )
    resultado = correr("--coverage-json", str(actual), "--base", str(base))
    assert resultado.returncode == 1
    assert "decrece" in resultado.stdout.lower()


def test_cobertura_igual_a_la_base_pasa(tmp_path: Path) -> None:
    base = escribir_cobertura(
        tmp_path / "base.json", sentencias=100, lineas_cubiertas=90, ramas=100, ramas_cubiertas=70
    )
    actual = escribir_cobertura(
        tmp_path / "actual.json", sentencias=100, lineas_cubiertas=90, ramas=100, ramas_cubiertas=70
    )
    assert correr("--coverage-json", str(actual), "--base", str(base)).returncode == 0


def test_cobertura_que_mejora_pasa(tmp_path: Path) -> None:
    base = escribir_cobertura(
        tmp_path / "base.json", sentencias=100, lineas_cubiertas=85, ramas=100, ramas_cubiertas=65
    )
    actual = escribir_cobertura(
        tmp_path / "actual.json", sentencias=100, lineas_cubiertas=99, ramas=100, ramas_cubiertas=99
    )
    assert correr("--coverage-json", str(actual), "--base", str(base)).returncode == 0


def test_ramas_que_decrecen_bloquean_aunque_las_lineas_suban(tmp_path: Path) -> None:
    """El caso que se cuela si se compara un solo numero: se agregan lineas
    triviales cubiertas mientras se mete logica condicional sin testear."""
    base = escribir_cobertura(
        tmp_path / "base.json", sentencias=100, lineas_cubiertas=90, ramas=100, ramas_cubiertas=80
    )
    actual = escribir_cobertura(
        tmp_path / "actual.json", sentencias=200, lineas_cubiertas=190, ramas=100, ramas_cubiertas=70
    )
    resultado = correr("--coverage-json", str(actual), "--base", str(base))
    assert resultado.returncode == 1
    assert "ramas" in resultado.stdout.lower()


def test_base_inexistente_no_bloquea(tmp_path: Path) -> None:
    """La primera vez no hay contra que comparar: `main` todavia no publico su
    medicion. Ausencia de base no es evidencia de retroceso — se avisa y se
    sigue, siempre que los umbrales absolutos se cumplan.
    """
    actual = escribir_cobertura(
        tmp_path / "actual.json", sentencias=100, lineas_cubiertas=90, ramas=100, ramas_cubiertas=70
    )
    resultado = correr("--coverage-json", str(actual), "--base", str(tmp_path / "nada.json"))
    assert resultado.returncode == 0
    assert "sin base" in resultado.stdout.lower()


def test_base_corrupta_no_bloquea_pero_avisa(tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    base.write_text("{ roto", encoding="utf-8")
    actual = escribir_cobertura(
        tmp_path / "actual.json", sentencias=100, lineas_cubiertas=90, ramas=100, ramas_cubiertas=70
    )
    resultado = correr("--coverage-json", str(actual), "--base", str(base))
    assert resultado.returncode == 0
    assert "sin base" in resultado.stdout.lower()


# ── El umbral absoluto manda sobre la comparacion ────────────────────────────


def test_no_decrecer_no_alcanza_si_no_se_llega_al_piso(tmp_path: Path) -> None:
    """Mejorar de 10 % a 20 % es no decrecer, y sigue estando prohibido."""
    base = escribir_cobertura(
        tmp_path / "base.json", sentencias=100, lineas_cubiertas=10, ramas=100, ramas_cubiertas=10
    )
    actual = escribir_cobertura(
        tmp_path / "actual.json", sentencias=100, lineas_cubiertas=20, ramas=100, ramas_cubiertas=20
    )
    assert correr("--coverage-json", str(actual), "--base", str(base)).returncode == 1


@pytest.mark.parametrize("bandera", ["--min-lineas", "--min-ramas"])
def test_umbral_fuera_de_rango_es_error_de_uso(tmp_path: Path, bandera: str) -> None:
    archivo = escribir_cobertura(
        tmp_path / "coverage.json",
        sentencias=100,
        lineas_cubiertas=100,
        ramas=100,
        ramas_cubiertas=100,
    )
    resultado = correr("--coverage-json", str(archivo), bandera, "150")
    assert resultado.returncode == 2


# ── El gate tiene que hablar en una consola que no entiende Unicode ──────────
#
# Un gate que se cae al IMPRIMIR miente dos veces: no dice la cobertura, y sale
# con un codigo que se lee como "la cobertura no alcanza". El diagnostico
# arranca mirando los tests equivocados.


def test_el_caso_feliz_no_se_cae_en_consola_latin1(tmp_path: Path) -> None:
    archivo = escribir_cobertura(
        tmp_path / "coverage.json",
        sentencias=100,
        lineas_cubiertas=90,
        ramas=50,
        ramas_cubiertas=35,
    )
    resultado = correr("--coverage-json", str(archivo), entorno=CONSOLA_LATIN1)

    assert "UnicodeEncodeError" not in resultado.stderr, resultado.stderr
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    # No alcanza con no reventar: tiene que seguir informando los numeros.
    assert "90.00" in resultado.stdout
    assert "70.00" in resultado.stdout


def test_el_bloqueo_sigue_siendo_por_cobertura_en_consola_latin1(tmp_path: Path) -> None:
    """El 1 tiene que venir del piso incumplido, no de la codificacion.

    Es la mitad que importa: los dos fallos salen 1, y sin esta distincion el
    test de arriba se cumpliria igual con un script que aborta siempre.
    """
    archivo = escribir_cobertura(
        tmp_path / "coverage.json",
        sentencias=100,
        lineas_cubiertas=50,
        ramas=100,
        ramas_cubiertas=90,
    )
    resultado = correr("--coverage-json", str(archivo), entorno=CONSOLA_LATIN1)

    assert "UnicodeEncodeError" not in resultado.stderr, resultado.stderr
    assert resultado.returncode == 1
    assert "50.00" in resultado.stdout
