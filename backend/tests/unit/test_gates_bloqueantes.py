"""Ningun gate del pipeline puede apagarse sin que el pipeline lo denuncie.

Cubre tres escenarios de `platform/delivery-pipeline` que hasta hoy no tenian
test ejecutable: *"Violacion de reglas de linting"*, *"Error de tipado
estatico"* y *"Secreto filtrado en el cambio"*. Los tres afirman lo mismo con
distinto sujeto: **el pipeline falla y el cambio no puede integrarse**.

POR QUE ESTE ARCHIVO EXISTE
────────────────────────────
`test_auditoria_de_dependencias.py` ya defiende esa idea, y su encabezado la
argumenta mejor de lo que la argumentaria acá:

    "apagan el gate dejando el step a la vista, y un job que reporta verde sin
     bloquear es indistinguible de uno que no encontro nada"

Pero su control mira **solo** `pip-audit` y `npm audit`, dentro del job
`security`. Todo lo demas quedaba defendido por comentarios. Y hay uno que lo
dice con todas las letras, en el `ci.yml`, arriba del escaneo de secretos:

    "gitleaks corre tambien en pre-commit, y ESTE es el control"

Por el Principio 5 una decision implicita no es vinculante, y un comentario no
frena a nadie. Hoy alguien puede agregarle `|| true` al gitleaks del pipeline y
los 625 tests siguen verdes — el unico control declarado del secreto en claro se
apaga sin ruido, y la regla dura 4 se queda sin quien la haga cumplir.

QUE SE VERIFICA Y QUE NO
─────────────────────────
Esto NO ejecuta `ruff`, `tsc` ni `gitleaks`: no comprueba que detecten, comprueba
que **sigan pudiendo bloquear**. Que detecten es lo que prueban los tests de
cada herramienta, y en el caso del backend lo prueba esta misma suite cada vez
que corre.

La forma de aflojar un gate no es sutil ni hay que buscarla: son tres, y las
tres destraban una tarde. Estan enumeradas en `NEUTRALIZA_SALIDA` y en el
control de `continue-on-error`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

RAIZ_REPO = Path(__file__).resolve().parents[3]
CI = RAIZ_REPO / ".github" / "workflows" / "ci.yml"

# `|| true`, `|| :` y `; true` al final de una linea: el step corre, falla, y el
# shell devuelve 0 igual. Mismo criterio —y misma expresion— que el control de
# auditoria de dependencias, por la misma razon.
NEUTRALIZA_SALIDA = re.compile(r"\|\|\s*(?:true|:)\s*$|;\s*true\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Gate:
    """Un control que, si falla, tiene que dejar el cambio afuera de `main`."""

    job: str
    huella: re.Pattern[str]
    que: str


# La huella busca el COMANDO, no el nombre del step. Un step se puede renombrar
# —y los del frontend ya se llaman distinto de lo que ejecutan: el step `eslint`
# corre `npm run lint`— y el gate sigue siendo el mismo. Al reves no: cambiar el
# comando es cambiar el gate.
# `que` va SIN articulo: los mensajes lo componen con "el" y con "del", y
# "neutraliza el codigo de salida de el escaneo de secretos" no se le entiende a
# nadie. El mensaje de un control es lo unico que se lee cuando salta.
GATES = (
    Gate("lint-backend", re.compile(r"^\s*ruff check\b", re.M), "lint del backend"),
    Gate("lint-backend", re.compile(r"^\s*black --check\b", re.M), "formato del backend"),
    Gate("lint-backend", re.compile(r"^\s*mypy\b", re.M), "tipado estricto del backend"),
    Gate("lint-frontend", re.compile(r"\bnpm run lint\b"), "lint del frontend"),
    Gate("lint-frontend", re.compile(r"\bnpm run format:check\b"), "formato del frontend"),
    Gate("lint-frontend", re.compile(r"\bnpm run typecheck\b"), "tipado estricto del frontend"),
    Gate("security", re.compile(r"\bgitleaks\b"), "escaneo de secretos"),
    Gate("test-backend-integration", re.compile(r"check-coverage\.py"), "gate de cobertura"),
)


def _sin_comentarios_de_shell(guion: str) -> str:
    """Saca los comentarios `#` de un bloque `run:`.

    El `ci.yml` real explica en sus comentarios por que NO usa `|| true`. Un
    match por texto crudo rechazaria el archivo que documenta la regla que este
    control defiende — y un test que da falso positivo termina desactivado.
    """
    return "\n".join(re.sub(r"#.*$", "", linea) for linea in guion.splitlines())


def _job(documento: dict[str, Any], nombre: str) -> dict[str, Any] | None:
    valor = documento.get("jobs", {}).get(nombre)
    return valor if isinstance(valor, dict) else None


def infracciones(contenido: str) -> list[str]:
    """Devuelve las formas en que este workflow deja de bloquear.

    Publica a proposito: los tests negativos la corren contra workflows
    sinteticos para probar que cada control detecta algo de verdad.
    """
    documento = yaml.safe_load(contenido)
    problemas: list[str] = []

    for gate in GATES:
        job = _job(documento, gate.job)
        if job is None:
            problemas.append(f"no existe el job '{gate.job}', que es donde vive el {gate.que}")
            continue

        # Un `continue-on-error` en el JOB apaga todos sus steps de una. Es la
        # forma mas barata de aflojar y la mas facil de no ver en un diff.
        if job.get("continue-on-error"):
            problemas.append(f"el job '{gate.job}' lleva continue-on-error, asi que no bloquea")

        pasos = [p for p in (job.get("steps") or []) if isinstance(p, dict)]
        coincidencias = [
            p for p in pasos if gate.huella.search(_sin_comentarios_de_shell(str(p.get("run", ""))))
        ]

        # Que el gate DESAPAREZCA es tan grave como que se afloje, y mas
        # silencioso: no queda un step en verde delatandolo, no queda nada.
        if not coincidencias:
            problemas.append(f"el {gate.que} ya no se ejecuta en el job '{gate.job}'")
            continue

        for paso in coincidencias:
            nombre = str(paso.get("name", "(sin nombre)"))
            if paso.get("continue-on-error"):
                problemas.append(f"'{nombre}': lleva continue-on-error, asi que no bloquea")
            if NEUTRALIZA_SALIDA.search(_sin_comentarios_de_shell(str(paso.get("run", "")))):
                problemas.append(f"'{nombre}': neutraliza el codigo de salida del {gate.que}")

    return problemas


@pytest.fixture(scope="module")
def ci_real() -> str:
    return CI.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def documento_real(ci_real: str) -> dict[str, Any]:
    documento: dict[str, Any] = yaml.safe_load(ci_real)
    return documento


def test_el_pipeline_real_no_afloja_ningun_gate(ci_real: str) -> None:
    """Los ocho gates de `GATES` existen y ninguno esta neutralizado."""
    assert infracciones(ci_real) == []


def test_los_dos_escaneos_de_secretos_siguen_en_pie(documento_real: dict[str, Any]) -> None:
    """`gitleaks` corre DOS veces, y las dos importan.

    El escaneo principal recorre la historia con `git log -p`, donde un `.docx`
    sale como "Binary files differ" — o sea que la constitucion y los planes de
    seguridad y de SRE se venian declarando limpios sin abrirlos. El segundo
    paso extrae su texto y lo escanea aparte.

    `infracciones()` se conforma con encontrar UNO. Acá se cuentan, porque
    borrar el segundo deja el punto ciego de vuelta sin apagar ningun gate.
    """
    job = _job(documento_real, "security")
    assert job is not None
    corridas = [
        p
        for p in job["steps"]
        if isinstance(p, dict) and "gitleaks" in _sin_comentarios_de_shell(str(p.get("run", "")))
    ]
    assert len(corridas) == 2, f"se esperaban 2 corridas de gitleaks, hay {len(corridas)}"


# ── El pipeline corre cuando tiene que correr ───────────────────────────────
#
# Escenarios *"Propuesta de cambio abierta"* y *"Duracion de la ejecucion"*. Un
# gate perfecto que no se dispara sobre las propuestas de cambio no gatea nada,
# y es la unica forma de apagar los ocho de arriba a la vez.


def _disparadores(documento: dict[str, Any]) -> dict[str, Any]:
    """`yaml.safe_load` lee la clave `on:` como el booleano True.

    Es el "problema de Noruega" del YAML 1.1 — el mismo por el que `NO` sale
    como False. No es una rareza de este archivo: le pasa a todo workflow de
    GitHub Actions parseado con `safe_load`.
    """
    claves = cast(dict[Any, Any], documento)
    valor = claves.get("on", claves.get(True))
    assert isinstance(valor, dict), "el workflow no declara disparadores"
    return valor


def test_el_pipeline_corre_sobre_toda_propuesta_contra_main(documento_real: dict[str, Any]) -> None:
    assert "main" in _disparadores(documento_real)["pull_request"]["branches"]


def test_el_pipeline_corre_sobre_cada_integracion_a_main(documento_real: dict[str, Any]) -> None:
    assert "main" in _disparadores(documento_real)["push"]["branches"]


# El presupuesto de la spec es de 15 minutos "para un cambio sin modificaciones
# sustantivas". `migraciones-compatibles` solo corre cuando HAY migraciones
# nuevas, que es la definicion de modificacion sustantiva, asi que no cae bajo
# ese presupuesto. Los demas si, y como corren en paralelo el total es el del
# job mas lento — por eso el techo se verifica job por job.
FUERA_DEL_PRESUPUESTO = {"migraciones-compatibles"}


def test_todos_los_jobs_declaran_un_techo_de_duracion(documento_real: dict[str, Any]) -> None:
    """Sin `timeout-minutes` el default de GitHub son 6 HORAS.

    Un job colgado no falla: ocupa un runner toda la mañana y deja la propuesta
    de cambio en "pendiente", que es el unico estado que no obliga a nadie a
    mirar nada.
    """
    sin_techo = [n for n, j in documento_real["jobs"].items() if "timeout-minutes" not in j]
    assert sin_techo == [], f"jobs sin timeout-minutes: {sin_techo}"


def test_los_jobs_del_camino_comun_caben_en_los_15_minutos(documento_real: dict[str, Any]) -> None:
    excedidos = {
        nombre: job["timeout-minutes"]
        for nombre, job in documento_real["jobs"].items()
        if nombre not in FUERA_DEL_PRESUPUESTO and job["timeout-minutes"] > 15
    }
    assert excedidos == {}, f"jobs por encima del presupuesto de 15 min: {excedidos}"


# ── Tests negativos: probar que los controles detectan algo ─────────────────
#
# Un verificador que nunca dice que no es un verificador. Cada caso rompe UNA
# cosa sobre un workflow que por lo demas cumple.

BASE = """
name: CI
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
jobs:
  lint-backend:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: ruff
        run: ruff check app tests alembic
      - name: black --check
        run: black --check app tests alembic
      - name: mypy --strict
        run: mypy .
  lint-frontend:
    runs-on: ubuntu-latest
    timeout-minutes: 15{cont_job_frontend}
    steps:
      - name: eslint
        run: npm run lint
      - name: prettier --check
        run: npm run format:check
      - name: tsc --noEmit
        run: npm run typecheck
  security:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: gitleaks{cont_gitleaks}
        run: |
          gitleaks detect --source /repo --redact{sufijo_gitleaks}
  test-backend-integration:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Gate de cobertura
        run: |
          python tools/check-coverage.py --min-lineas 80{sufijo_cobertura}
"""
# ⚠️ Los dos steps con sufijo van en escalar de BLOQUE (`run: |`), como en el
# `ci.yml` real. En un escalar plano, `|| :` es YAML invalido —el `: ` abre un
# mapeo— y el caso negativo moriria parseando en vez de probar el control.


def _workflow(
    *,
    sufijo_gitleaks: str = "",
    sufijo_cobertura: str = "",
    cont_gitleaks: str = "",
    cont_job_frontend: str = "",
) -> str:
    return BASE.format(
        sufijo_gitleaks=sufijo_gitleaks,
        sufijo_cobertura=sufijo_cobertura,
        cont_gitleaks=cont_gitleaks,
        cont_job_frontend=cont_job_frontend,
    )


def test_el_workflow_sintetico_de_referencia_pasa() -> None:
    """Sin este caso los negativos no prueban nada: podrian fallar por otra cosa."""
    assert infracciones(_workflow()) == []


@pytest.mark.parametrize(
    ("descripcion", "contenido", "esperado"),
    [
        (
            "el escaneo de secretos con la salida neutralizada",
            _workflow(sufijo_gitleaks=" || true"),
            "neutraliza el codigo de salida del escaneo de secretos",
        ),
        (
            "el gate de cobertura con la salida neutralizada",
            _workflow(sufijo_cobertura=" || :"),
            "neutraliza el codigo de salida del gate de cobertura",
        ),
        (
            "el escaneo de secretos declarado no bloqueante",
            _workflow(cont_gitleaks="\n        continue-on-error: true"),
            "continue-on-error",
        ),
        (
            "el job entero de lint del frontend declarado no bloqueante",
            _workflow(cont_job_frontend="\n    continue-on-error: true"),
            "el job 'lint-frontend' lleva continue-on-error",
        ),
    ],
)
def test_el_control_detecta_cada_forma_de_aflojar(
    descripcion: str, contenido: str, esperado: str
) -> None:
    problemas = infracciones(contenido)
    assert problemas, f"el control no detecto: {descripcion}"
    assert any(esperado in p for p in problemas), f"{descripcion}: {problemas}"


@pytest.mark.parametrize(
    ("comando", "esperado"),
    [
        ("mypy .", "el tipado estricto del backend ya no se ejecuta"),
        ("npm run typecheck", "el tipado estricto del frontend ya no se ejecuta"),
        ("ruff check app tests alembic", "el lint del backend ya no se ejecuta"),
        ("npm run lint", "el lint del frontend ya no se ejecuta"),
    ],
)
def test_el_control_detecta_un_gate_borrado(comando: str, esperado: str) -> None:
    """Borrar el step es la forma que no deja rastro en el resultado del job."""
    contenido = "\n".join(ln for ln in _workflow().splitlines() if comando not in ln)
    problemas = infracciones(contenido)
    assert any(esperado in p for p in problemas), problemas


def test_el_control_detecta_un_job_entero_borrado() -> None:
    contenido = _workflow().split("  security:")[0]
    problemas = infracciones(contenido)
    assert any("no existe el job 'security'" in p for p in problemas), problemas


def test_un_comentario_que_nombra_la_forma_de_aflojar_no_dispara_el_control() -> None:
    """El `ci.yml` real dice en un comentario que no hay que agregar `|| true`.

    Si el control mirara texto crudo, rechazaria el archivo que documenta la
    regla que el mismo control defiende.
    """
    contenido = _workflow(sufijo_gitleaks="\n          # nunca agregar || true aca")
    assert infracciones(contenido) == []
