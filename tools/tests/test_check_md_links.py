"""Tests del verificador de enlaces markdown — y su puesta en marcha.

Mismo caso que `test_check_config_parity.py`, encontrado en el mismo barrido
del 18-ago-2026: `tools/check-md-links.py` estaba escrito y funcionaba, pero no
lo ejecutaba nadie — ni `ci.yml`, ni `.pre-commit-config.yaml`, ni ningun test.

La diferencia con el otro es que este **ya estaba en rojo**. Tenia 2 enlaces
rotos que nadie habia visto, los dos por la misma causa: al archivar C-04, la
carpeta paso a `openspec/changes/archive/2026-08-17-tenancy-planes-y-limites/`
y quedaron atras un enlace de `CHANGES.md` y un `../` de menos dentro del
propio `design.md` archivado. Ninguno de los dos rompia nada al ejecutar; solo
mentian al que los clickeara.

Es exactamente lo que la tarea 1.6 de C-01 dice que este script existe para
evitar. Existia, pero no corria.

Se invoca el script como PROCESO, por el mismo motivo que en los otros dos
archivos de este directorio: lo que hace de gate es el codigo de salida.

Se corren desde la raiz del repositorio:

    python -m pytest tools/tests
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "tools" / "check-md-links.py"


def correr(raiz: Path) -> subprocess.CompletedProcess[str]:
    """Ejecuta el verificador que vive dentro de `raiz`."""
    return subprocess.run(
        [sys.executable, str(raiz / "tools" / "check-md-links.py")],
        capture_output=True,
        text=True,
        cwd=raiz,
        check=False,
    )


def armar_raiz(tmp_path: Path, documento: str) -> Path:
    """Arma un arbol minimo con el script adentro y UN markdown a auditar.

    El script calcula su raiz desde `__file__`, asi que la copia audita el
    arbol falso y el repositorio de verdad no se toca.
    """
    (tmp_path / "tools").mkdir()
    shutil.copy(SCRIPT, tmp_path / "tools" / "check-md-links.py")

    (tmp_path / "destino-real.md").write_text("# existe\n", encoding="utf-8")
    (tmp_path / "indice.md").write_text(documento, encoding="utf-8")

    return tmp_path


# ── Lo que este archivo vino a arreglar ──────────────────────────────────────


def test_el_repositorio_real_no_tiene_enlaces_rotos() -> None:
    """El gate en si. Es el unico test que mira los .md de verdad."""
    resultado = correr(REPO)

    assert resultado.returncode == 0, (
        "`tools/check-md-links.py` encontro enlaces relativos rotos:\n"
        f"{resultado.stdout}{resultado.stderr}"
    )


# ── Que el verificador realmente verifique ───────────────────────────────────


def test_enlace_a_un_archivo_que_existe_pasa(tmp_path: Path) -> None:
    """El control del control: sin esto, el caso negativo no prueba nada."""
    raiz = armar_raiz(tmp_path, "Ver [el destino](destino-real.md).\n")

    resultado = correr(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_enlace_a_un_archivo_inexistente_falla(tmp_path: Path) -> None:
    raiz = armar_raiz(tmp_path, "Ver [el destino](destino-que-no-existe.md).\n")

    resultado = correr(raiz)

    assert resultado.returncode == 1, resultado.stdout
    assert "destino-que-no-existe.md" in resultado.stdout


def test_enlace_externo_no_se_resuelve_contra_el_disco(tmp_path: Path) -> None:
    """Un `https://` no es un archivo faltante.

    Si el verificador tratara los enlaces externos como rutas, el repositorio
    entero daria rojo y el gate seria inservible desde el primer dia.
    """
    raiz = armar_raiz(tmp_path, "Ver [la spec](https://example.invalid/pagina-que-no-existe).\n")

    resultado = correr(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
