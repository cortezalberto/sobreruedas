"""Escenarios de `platform/delivery-pipeline` que dependen del despliegue.

Cubre dos de los cuatro escenarios que la auditoria de la tarea 10.3 dejo sin
test ejecutable, y que estaban trabados por una razon que YA NO EXISTE: la
auditoria decia "bloqueados por el proveedor cloud sin decidir", y `ADR-023`
cerro esa decision (VPS unico con Docker Compose).

  · Las pruebas de humo posteriores fallan  → un humo fallido NO conmuta
  · Trazabilidad del despliegue             → el commit se identifica unicamente

POR QUE ESTOS TESTS Y NO UNA VERIFICACION A MANO
─────────────────────────────────────────────────
Los dos escenarios describen conducta del mecanismo de despliegue, y esa
conducta se puede ejercitar sin servidor. Verificarla a mano una vez —como se
hizo el 17-ago-2026 levantando la topologia en local— demuestra que anduvo ESE
dia. No impide que el proximo cambio la rompa en silencio.

El escenario del humo es el mas caro de perder: es la red de seguridad entera
del azul-verde. Si el humo falla y el trafico conmuta igual, un despliegue roto
llega a los usuarios y el stack sano queda apagado.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

RAIZ_REPO = Path(__file__).resolve().parents[3]
HUMO = RAIZ_REPO / "infra" / "vps" / "deploy" / "humo.sh"
DESPLEGAR = RAIZ_REPO / "infra" / "vps" / "deploy" / "desplegar.sh"
WORKFLOW_PUBLICAR = RAIZ_REPO / ".github" / "workflows" / "deploy-staging.yml"

# Ruta absoluta, no el nombre pelado: `bash` a secas depende del PATH del
# proceso, que en CI y en la maquina de cada uno puede resolver a binarios
# distintos. Ademas es lo que pide la regla S607 de ruff, y con razon.
BASH = shutil.which("bash")

bash_disponible = pytest.mark.skipif(BASH is None, reason="requiere bash para ejecutar los scripts")


def _correr_humo(tmp_path: Path, *, sonda_falla: bool, duracion: int = 6) -> int:
    """Ejecuta humo.sh con una sonda inyectada y devuelve su codigo de salida."""
    assert BASH is not None  # lo garantiza el marcador `bash_disponible`

    sonda = tmp_path / "sonda.sh"
    codigo = 1 if sonda_falla else 0
    sonda.write_text(f"#!/usr/bin/env bash\nexit {codigo}\n", encoding="utf-8")
    sonda.chmod(0o755)

    entorno = {
        **os.environ,
        "SONDA_CMD": str(sonda),
        "INTERVALO_HUMO": "1",
    }
    # S603: los tres argumentos son rutas que construye este mismo archivo desde
    # constantes; no hay entrada externa que sanear.
    resultado = subprocess.run(  # noqa: S603
        [BASH, str(HUMO), "azul", str(duracion)],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return resultado.returncode


# ── Escenario: Las pruebas de humo posteriores fallan ────────────────────────


@bash_disponible
def test_humo_con_todas_las_sondas_sanas_sale_cero(tmp_path: Path) -> None:
    """El contrato que habilita la conmutacion."""
    assert _correr_humo(tmp_path, sonda_falla=False) == 0


@bash_disponible
def test_humo_con_una_sonda_caida_sale_uno(tmp_path: Path) -> None:
    """El contrato que la IMPIDE.

    `desplegar.sh` decide con `if ! humo.sh ...`. Si esto devolviera 0 con el
    stack roto, el agente conmutaria el trafico a un despliegue fallado y
    apagaria el que estaba sano.
    """
    assert _correr_humo(tmp_path, sonda_falla=True) == 1


@bash_disponible
def test_humo_aborta_en_el_primer_fallo_sin_agotar_la_duracion(
    tmp_path: Path,
) -> None:
    """No tolera intermitencias, y no espera al final para decirlo.

    Si el stack parpadea SIN trafico, con trafico va a ser peor. Es mas barato
    no conmutar que conmutar y volver.
    """
    import time

    inicio = time.monotonic()
    codigo = _correr_humo(tmp_path, sonda_falla=True, duracion=60)
    transcurrido = time.monotonic() - inicio

    assert codigo == 1
    assert transcurrido < 30, (
        f"tardo {transcurrido:.0f}s en abortar sobre una duracion de 60s: "
        "deberia cortar en la primera vuelta, no agotar el presupuesto"
    )


@bash_disponible
def test_humo_rechaza_un_color_invalido(tmp_path: Path) -> None:
    """Sale 2, distinto de 1: un error de invocacion no es un stack roto."""
    assert BASH is not None
    # S603: mismas rutas construidas acá, sin entrada externa.
    resultado = subprocess.run(  # noqa: S603
        [BASH, str(HUMO), "rosa", "5"],
        env={**os.environ, "SONDA_CMD": "/bin/true"},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert resultado.returncode == 2


def test_el_agente_solo_conmuta_despues_del_humo() -> None:
    """El ORDEN importa tanto como los codigos de salida.

    Un humo que devuelve 1 no sirve de nada si el agente ya movio el upstream.
    """
    guion = DESPLEGAR.read_text(encoding="utf-8")

    pos_humo = guion.find("humo.sh")
    pos_conmutar = guion.find("conmutar-upstream.sh")

    assert pos_humo != -1, "desplegar.sh no invoca humo.sh"
    assert pos_conmutar != -1, "desplegar.sh no invoca conmutar-upstream.sh"
    assert pos_humo < pos_conmutar, (
        "conmutar-upstream.sh aparece ANTES que humo.sh: el agente moveria el "
        "trafico sin haber probado el stack nuevo"
    )

    # Y el humo tiene que estar en una guarda, no invocado y descartado.
    assert re.search(r"if\s+!\s+\"?\$\{?RAIZ\}?[^\n]*humo\.sh", guion), (
        "la invocacion de humo.sh no esta dentro de una guarda `if !`: su "
        "codigo de salida se estaria ignorando"
    )


# ── Escenario: Trazabilidad del despliegue ──────────────────────────────────


def test_las_imagenes_se_etiquetan_con_el_sha_completo() -> None:
    """El SHA ES el tag (ADR-023 §Notas de implementacion)."""
    workflow = yaml.safe_load(WORKFLOW_PUBLICAR.read_text(encoding="utf-8"))
    pasos = workflow["jobs"]["publicar"]["steps"]

    construir = [p for p in pasos if "build-push-action" in str(p.get("uses", ""))]
    assert construir, "el workflow no construye ninguna imagen"

    tags = construir[0]["with"]["tags"]
    assert "steps.commit.outputs.sha" in tags, (
        "las imagenes no se etiquetan con el SHA del commit: sin eso una version "
        "desplegada no se puede atribuir a un commit"
    )


def test_las_imagenes_llevan_la_etiqueta_oci_de_revision() -> None:
    """Es como el VPS sabe QUE commit trae la imagen.

    Sin esta etiqueta el agente tendria que adivinar el SHA, o el pipeline
    tendria que empujarselo — que es justo lo que ADR-023 prohibe.
    """
    workflow = yaml.safe_load(WORKFLOW_PUBLICAR.read_text(encoding="utf-8"))
    pasos = workflow["jobs"]["publicar"]["steps"]
    construir = [p for p in pasos if "build-push-action" in str(p.get("uses", ""))]

    labels = construir[0]["with"].get("labels", "")
    assert (
        "org.opencontainers.image.revision" in labels
    ), "falta la etiqueta OCI de revision en la imagen"


def test_el_agente_lee_la_revision_y_la_persiste() -> None:
    """La trazabilidad tiene que sobrevivir al despliegue, no solo ocurrir.

    Se inspecciona una version desplegada preguntandole al VPS que SHA sirve.
    """
    guion = DESPLEGAR.read_text(encoding="utf-8")

    assert (
        "org.opencontainers.image.revision" in guion
    ), "el agente no lee la etiqueta de revision de la imagen"
    assert re.search(r'>\s*"\$ESTADO_SHA"', guion), (
        "el agente no deja registrado el SHA desplegado: sin eso, inspeccionar "
        "una version desplegada no permite identificar su commit"
    )


def test_la_firma_se_verifica_por_digest_y_no_por_tag() -> None:
    """Un tag se puede mover; un digest no.

    Verificar la firma contra un tag deja la puerta abierta a que la imagen
    verificada y la desplegada no sean la misma.
    """
    workflow = yaml.safe_load(WORKFLOW_PUBLICAR.read_text(encoding="utf-8"))
    pasos = workflow["jobs"]["publicar"]["steps"]
    firmar = [p for p in pasos if "cosign sign" in str(p.get("run", ""))]

    assert firmar, "el workflow no firma las imagenes"
    assert "${DIGEST}" in firmar[0]["run"], "cosign firma por tag en vez de por digest"
