"""La auditoria de dependencias del pipeline no baja del piso constitucional.

Cubre el escenario *"Severidad por debajo del piso"* de
`platform/delivery-pipeline`, enmendado el 17-ago-2026.

EL PISO, Y DE DONDE SALE
-------------------------
`constitucion` (N0) fija: *"Las vulnerabilidades de severidad alta o critica
bloquean el merge."* Es un **piso, no un techo** -- no dice en ningun lado que
las bajas no deban bloquear.

De ahi salen dos politicas distintas, y las dos son correctas:

  - `npm audit --audit-level=high`  -> cumple el piso exactamente
  - `pip-audit` sin filtro          -> bloquea ante CUALQUIER severidad

La segunda es **mas estricta a proposito**: `pip-audit` no expone la severidad
de sus hallazgos, y filtrarla obligaria a mantener a mano una lista de
excepciones. Ser mas estricto que el piso esta permitido; bajar de el, no.

POR QUE UN TEST Y NO UN COMENTARIO EN `ci.yml`
-----------------------------------------------
Hasta esta enmienda el motivo vivia **solo en un comentario** de `ci.yml`. Por
el Principio 5 una decision implicita no es vinculante, y un comentario no
frena a nadie.

Lo que hay que frenar es concreto y no es malintencionado: el dia que
`pip-audit` marque una transitiva sin fix disponible y el build quede rojo,
agregar `--ignore-vuln GHSA-xxxx` destraba la tarde. Si esa vulnerabilidad es
alta o critica, el repositorio acaba de caer **por debajo del piso de N0** sin
que nadie lo note, porque el pipeline vuelve a verde -- que es justo la senal
que uno lee como "esta todo bien".

Mismo criterio para `|| true` y `continue-on-error: true`: apagan el gate
dejando el step a la vista, y un job que reporta verde sin bloquear es
indistinguible de uno que no encontro nada.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ_REPO = Path(__file__).resolve().parents[3]
CI = RAIZ_REPO / ".github" / "workflows" / "ci.yml"

# Banderas de `pip-audit` que sacan hallazgos del resultado. Cualquiera de
# ellas puede dejar pasar una alta o una critica, que es lo que N0 prohibe.
BANDERAS_QUE_PERDONAN = re.compile(
    r"--(?:ignore-vuln|skip-editable)\b|--vulnerability-service\s+none\b"
)

# `|| true`, `|| :` y `; true` al final de una linea: el step corre, falla, y
# el shell devuelve 0 igual.
NEUTRALIZA_SALIDA = re.compile(r"\|\|\s*(?:true|:)\s*$|;\s*true\s*$", re.MULTILINE)

# El piso de N0 para el auditor que SI expone severidad. `high` en npm incluye
# `critical`: son los dos niveles que la constitucion manda bloquear.
NIVEL_MINIMO_NPM = "--audit-level=high"


def _sin_comentarios_de_shell(guion: str) -> str:
    """Saca los comentarios `#` de un bloque `run:`.

    El `ci.yml` real **nombra estas banderas en sus comentarios** para explicar
    por que no se usan. Un match por texto crudo se romperia contra el archivo
    que deberia aprobar, y un test que da falso positivo termina desactivado.
    """
    return "\n".join(re.sub(r"#.*$", "", linea) for linea in guion.splitlines())


def _steps_del_job(documento: dict[str, Any], job: str) -> list[dict[str, Any]]:
    return list(documento.get("jobs", {}).get(job, {}).get("steps", []) or [])


def infracciones(contenido: str) -> list[str]:
    """Devuelve las infracciones del contrato de auditoria de dependencias.

    Publica a proposito: los tests negativos la corren contra workflows
    sinteticos para probar que cada control detecta algo de verdad.
    """
    documento = yaml.safe_load(contenido)
    problemas: list[str] = []

    steps = _steps_del_job(documento, "security")
    if not steps:
        return ["no existe el job 'security', o no tiene steps"]

    guiones = {
        str(paso.get("name", f"step[{i}]")): str(paso.get("run", ""))
        for i, paso in enumerate(steps)
    }
    todo = "\n".join(guiones.values())

    # 1. Los dos ecosistemas se auditan. Auditar solo uno deja la mitad de las
    #    dependencias del producto sin mirar.
    if "pip-audit" not in todo:
        problemas.append("el job 'security' no audita las dependencias de Python")
    if "npm audit" not in todo:
        problemas.append("el job 'security' no audita las dependencias de Node")

    for nombre, guion in guiones.items():
        limpio = _sin_comentarios_de_shell(guion)

        # 2. Nada de excepciones puntuales en `pip-audit`: sin severidad
        #    expuesta, perdonar un hallazgo es perdonar a ciegas.
        if "pip-audit" in limpio:
            hallazgo = BANDERAS_QUE_PERDONAN.search(limpio)
            if hallazgo:
                problemas.append(
                    f"'{nombre}': pip-audit corre con '{hallazgo.group().strip()}', "
                    "que puede dejar pasar una alta o una critica"
                )

        # 3. `npm audit` no puede aflojar por encima del piso de N0.
        if "npm audit" in limpio and NIVEL_MINIMO_NPM not in limpio:
            problemas.append(
                f"'{nombre}': npm audit no corre con '{NIVEL_MINIMO_NPM}'; "
                "el piso de N0 son las severidades alta y critica"
            )

        # 4. Ningun auditor puede terminar en verde habiendo fallado.
        if ("pip-audit" in limpio or "npm audit" in limpio) and NEUTRALIZA_SALIDA.search(limpio):
            problemas.append(f"'{nombre}': neutraliza el codigo de salida del auditor")

    # 5. Un step no bloqueante reporta el hallazgo y mergea igual.
    for i, paso in enumerate(steps):
        nombre = str(paso.get("name", f"step[{i}]"))
        guion = _sin_comentarios_de_shell(str(paso.get("run", "")))
        if ("pip-audit" in guion or "npm audit" in guion) and paso.get("continue-on-error"):
            problemas.append(f"'{nombre}': lleva continue-on-error, asi que no bloquea")

    return problemas


@pytest.fixture(scope="module")
def ci_real() -> str:
    return CI.read_text(encoding="utf-8")


def test_el_pipeline_real_cumple_el_piso(ci_real: str) -> None:
    """El `ci.yml` de este repositorio no baja del piso de la constitucion."""
    assert infracciones(ci_real) == []


def test_pip_audit_corre_sin_filtro_de_severidad(ci_real: str) -> None:
    """Mas estricto que el piso, y por escrito.

    No alcanza con que no haya `--ignore-vuln`: hay que ver que el step existe
    y corre pelado. Si manana alguien reemplaza `pip-audit` por una herramienta
    que filtre por severidad, la spec deja de describir al pipeline.
    """
    documento = yaml.safe_load(ci_real)
    steps = _steps_del_job(documento, "security")
    invocaciones = [
        _sin_comentarios_de_shell(str(p.get("run", "")))
        for p in steps
        if "pip-audit" in _sin_comentarios_de_shell(str(p.get("run", "")))
    ]

    assert invocaciones, "no hay ningun step que invoque pip-audit"
    for guion in invocaciones:
        linea = next(ln for ln in guion.splitlines() if re.search(r"^\s*pip-audit\b", ln))
        assert BANDERAS_QUE_PERDONAN.search(linea) is None
        assert "--ignore-vuln" not in linea


# -- Tests negativos: probar que los controles detectan algo -----------------
#
# Un verificador que nunca dice que no es un verificador. Cada caso rompe UNA
# cosa sobre un workflow que por lo demas cumple.

BASE = """
name: CI
on: [push]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - name: pip-audit
        working-directory: backend{cont_pip}
        run: |
          pip install pip-audit
          pip-audit --desc{sufijo_pip}
      - name: npm audit
        working-directory: frontend-web
        run: npm audit {nivel_npm}
"""


def _workflow(
    *, sufijo_pip: str = "", nivel_npm: str = "--audit-level=high", cont_pip: str = ""
) -> str:
    return BASE.format(sufijo_pip=sufijo_pip, nivel_npm=nivel_npm, cont_pip=cont_pip)


def test_el_workflow_sintetico_de_referencia_pasa() -> None:
    """Sin este caso los negativos no prueban nada: podrian fallar por otra cosa."""
    assert infracciones(_workflow()) == []


@pytest.mark.parametrize(
    ("descripcion", "contenido", "esperado"),
    [
        (
            "pip-audit perdonando una vulnerabilidad puntual",
            _workflow(sufijo_pip=" --ignore-vuln GHSA-aaaa-bbbb-cccc"),
            "--ignore-vuln",
        ),
        (
            "pip-audit con la salida neutralizada",
            _workflow(sufijo_pip=" || true"),
            "neutraliza el codigo de salida",
        ),
        (
            "npm audit por debajo del piso de N0",
            _workflow(nivel_npm="--audit-level=critical"),
            "el piso de N0 son las severidades alta y critica",
        ),
        (
            "npm audit sin umbral declarado",
            _workflow(nivel_npm=""),
            "no corre con '--audit-level=high'",
        ),
    ],
)
def test_el_control_detecta_cada_forma_de_aflojar(
    descripcion: str, contenido: str, esperado: str
) -> None:
    problemas = infracciones(contenido)
    assert problemas, f"el control no detecto: {descripcion}"
    assert any(esperado in p for p in problemas), f"{descripcion}: {problemas}"


def test_el_control_detecta_un_auditor_no_bloqueante() -> None:
    """`continue-on-error` es del YAML, no del script: se mira aparte."""
    contenido = _workflow(cont_pip="\n        continue-on-error: true")
    problemas = infracciones(contenido)
    assert any("continue-on-error" in p for p in problemas), problemas


def test_el_control_detecta_un_ecosistema_sin_auditar() -> None:
    contenido = "\n".join(
        ln for ln in _workflow().splitlines() if "npm audit" not in ln and "frontend-web" not in ln
    )
    problemas = infracciones(contenido)
    assert any("dependencias de Node" in p for p in problemas), problemas


def test_un_comentario_que_nombra_la_bandera_no_dispara_el_control() -> None:
    """El `ci.yml` real explica en un comentario por que no usa `--ignore-vuln`.

    Si el control mirara texto crudo, rechazaria el archivo que documenta la
    regla que el mismo control defiende.
    """
    contenido = _workflow(sufijo_pip="\n          # nunca agregar --ignore-vuln aca")
    assert infracciones(contenido) == []


# ── La imagen se escanea ANTES de firmarse — ADR-027 ────────────────────────


DESPLIEGUE = RAIZ_REPO / ".github" / "workflows" / "deploy-staging.yml"


def _pasos_de_publicacion() -> list[dict[str, Any]]:
    documento = yaml.safe_load(DESPLIEGUE.read_text(encoding="utf-8"))
    for job in documento.get("jobs", {}).values():
        pasos = job.get("steps") or []
        if any("docker/build-push-action" in str(p.get("uses", "")) for p in pasos):
            return list(pasos)
    return []


def _indice(pasos: list[dict[str, Any]], marcador: str) -> int:
    """Posicion del primer paso cuyo `uses` o `run` menciona el marcador."""
    for i, paso in enumerate(pasos):
        if marcador in str(paso.get("uses", "")) or marcador in str(paso.get("run", "")):
            return i
    return -1


class TestLaImagenSeEscaneaAntesDeFirmarse:
    """`ADR-027` §1. El ORDEN es la decision, no la presencia del escaner.

    Firmar una imagen sin escanearla es PEOR que no firmarla: la firma acredita
    procedencia, y quien la verifica lee eso como "esta imagen fue revisada".
    Un escaneo despues de `cosign sign` no arregla nada — la imagen firmada ya
    existe y ya es descargable.

    Por eso el test no comprueba que trivy este: comprueba que este ANTES.
    """

    def test_el_workflow_construye_y_firma(self) -> None:
        """Sin esto los dos de abajo son vacuos: `-1 < n` es cierto por accidente
        cuando el paso no existe, y un workflow que no firmara pasaria igual.
        """
        pasos = _pasos_de_publicacion()
        assert pasos, "no se encontro el job que construye imagenes"
        assert _indice(pasos, "docker/build-push-action") >= 0
        assert _indice(pasos, "cosign sign") >= 0

    def test_trivy_corre_y_esta_entre_el_build_y_la_firma(self) -> None:
        pasos = _pasos_de_publicacion()
        build = _indice(pasos, "docker/build-push-action")
        trivy = _indice(pasos, "trivy")
        firma = _indice(pasos, "cosign sign")

        assert trivy >= 0, "la imagen se publica sin escanear (ADR-027 §1)"
        assert build < trivy < firma, (
            f"trivy tiene que ir entre el build ({build}) y la firma ({firma}), "
            f"y esta en {trivy}"
        )

    def test_trivy_bloquea_en_vez_de_solo_reportar(self) -> None:
        """Un escaner que no frena el pipeline es un informe, no un control."""
        pasos = _pasos_de_publicacion()
        paso = pasos[_indice(pasos, "trivy")]
        assert str(paso.get("with", {}).get("exit-code")) == "1"
        assert paso.get("continue-on-error") is not True

    def test_se_escanea_por_digest_y_no_por_tag(self) -> None:
        """Un tag se puede mover entre el escaneo y el despliegue; un digest no.

        Es el mismo criterio con el que se firma por digest.
        """
        pasos = _pasos_de_publicacion()
        referencia = str(pasos[_indice(pasos, "trivy")].get("with", {}).get("image-ref", ""))
        assert "digest" in referencia, f"trivy escanea una referencia movil: {referencia}"
