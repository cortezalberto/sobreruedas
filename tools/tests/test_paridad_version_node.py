"""Paridad de la version de Node entre CI, `.nvmrc` y `engines`.

Por que existe este archivo: el 18-ago-2026 el CI se cayo en `lint-frontend` y
`test-frontend` con `npm ci` fallando por `Missing: @emnapi/runtime@1.11.3 from
lock file`. El lockfile estaba bien formado; lo que estaba mal era **con que se
habia generado**. La maquina de desarrollo corria Node 24 / npm 11 y el runner
Node 22 / npm 10, y las dos versiones de npm no materializan igual las
dependencias opcionales de `@img/sharp-wasm32` (que Next 16 arrastra).

El detalle que lo hace peligroso: `npm ci` pasaba en local. No habia forma de
notarlo antes del push, porque el unico lugar donde las dos versiones se
comparaban era el runner.

Este test no compara versiones de npm — compara las de Node, que es lo que las
determina y lo unico que el repositorio puede declarar. Fija las tres fuentes
juntas para que no vuelvan a divergir en silencio:

  - `.github/workflows/ci.yml`  → `NODE_VERSION`, lo que corre de verdad
  - `frontend-web/.nvmrc`       → lo que toma quien usa nvm/fnm/volta
  - `frontend-web/package.json` → `engines.node`, lo que queda declarado

⚠️ Lo que este test NO hace: obligar a nadie a usar esa version. Un `.nvmrc` no
se aplica solo y `engines` no bloquea sin `engine-strict`. Lo que evita es el
caso concreto que nos mordio — que CI diga 22, el repositorio no diga nada, y
cada maquina genere el lockfile con lo que tenga instalado.

Se corren desde la raiz del repositorio:

    python -m pytest tools/tests
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
CI = REPO / ".github" / "workflows" / "ci.yml"
NVMRC = REPO / "frontend-web" / ".nvmrc"
PACKAGE_JSON = REPO / "frontend-web" / "package.json"


def _mayor_de_ci() -> str:
    """Lee `NODE_VERSION` del bloque `env` de `ci.yml`.

    Se parsea con expresion regular y no con un lector de YAML a proposito: la
    dependencia extra no se justifica para leer un escalar, y el formato del
    que se depende es el de una sola linea que ya esta ahi.
    """
    texto = CI.read_text(encoding="utf-8")
    hallazgo = re.search(r'^\s*NODE_VERSION:\s*"?(\d+)"?', texto, re.MULTILINE)
    assert hallazgo is not None, f"`NODE_VERSION` no aparece en {CI.name}"
    return hallazgo.group(1)


def test_nvmrc_declara_la_misma_version_mayor_que_ci() -> None:
    esperado = _mayor_de_ci()
    declarado = NVMRC.read_text(encoding="utf-8").strip().lstrip("v")

    assert declarado.split(".")[0] == esperado, (
        f"`.nvmrc` dice Node {declarado} y `ci.yml` corre Node {esperado}. "
        "Con versiones mayores distintas cambia el npm que las acompana, y el "
        "lockfile que se genere en local puede no ser el que el runner acepta."
    )


def test_engines_declara_la_misma_version_mayor_que_ci() -> None:
    esperado = _mayor_de_ci()
    paquete = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))

    engines = paquete.get("engines", {})
    declarado = engines.get("node")
    assert declarado is not None, (
        "`frontend-web/package.json` no declara `engines.node`. Sin eso, nada "
        "en el paquete dice contra que version de Node se resolvio el lockfile."
    )

    mayor = re.match(r"^(\d+)", str(declarado).lstrip("^~>=v ").strip())
    assert (
        mayor is not None
    ), f"`engines.node` = {declarado!r}: no arranca con una version mayor legible"
    assert (
        mayor.group(1) == esperado
    ), f"`engines.node` dice {declarado} y `ci.yml` corre Node {esperado}."
