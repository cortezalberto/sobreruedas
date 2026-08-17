"""El pipeline no tiene ni necesita credenciales del VPS — C-01, tarea 9.14.

POR QUE UN TEST Y NO UNA REVISION EN EL CODE REVIEW
────────────────────────────────────────────────────
`ADR-015` puso como control explicito que GitHub Actions NO reciba credenciales
de produccion, y descarto `kubectl apply` desde CI justamente por obligar a
guardar un kubeconfig en los secretos del pipeline. `ADR-023` cambio la
infraestructura entera y **conservo el control**: hoy lo prohibido es la clave
SSH del VPS.

La tentacion de romperlo es concreta y no es malintencionada. Un `ssh` desde el
workflow es tres lineas y despliega; el agente que tira son varios archivos y un
timer. El dia que un despliegue urgente no sale, agregar `SSH_PRIVATE_KEY` a los
secretos resuelve el problema de esa tarde y regala el unico control de
seguridad que `ADR-015` defendio con argumentos concretos.

Un gate que depende de que alguien se acuerde de mirar no es un gate. Es el
mismo criterio que `ADR-023` le aplico a `gitleaks`.

POR QUE SE PARSEA EL YAML Y NO SE HACE `grep`
──────────────────────────────────────────────
Los propios workflows **mencionan `ssh` en sus comentarios** para explicar por
que esta prohibido. Un match por texto se romperia contra el archivo que deberia
aprobar, y un test que da falso positivo termina desactivado. Se parsea el YAML,
que descarta los comentarios, y ademas se limpian los comentarios de shell
dentro de los bloques `run:`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

RAIZ_REPO = Path(__file__).resolve().parents[3]
WORKFLOWS = RAIZ_REPO / ".github" / "workflows"

# Acciones de terceros cuyo proposito ES abrir una sesion contra un servidor.
# Ninguna tiene lugar en este repositorio mientras el VPS sea quien tira.
ACCIONES_PROHIBIDAS = (
    "appleboy/ssh-action",
    "appleboy/scp-action",
    "easingthemes/ssh-deploy",
    "burnett01/rsync-deployments",
    "webfactory/ssh-agent",
    "shimataro/ssh-key-action",
    "azure/k8s-deploy",
    "hashicorp/setup-terraform",
)

# Comandos que alcanzan la maquina de produccion desde el runner.
COMANDOS_PROHIBIDOS = re.compile(
    r"(?:^|[\s;&|(])(?:ssh|scp|sftp|rsync|kubectl|helm|terraform|ansible-playbook)(?:\s|$)"
)

# Nombres de secreto que delatan una credencial de servidor. Se mira el NOMBRE
# porque el valor nunca esta en el repositorio — que es justamente el punto.
SECRETOS_PROHIBIDOS = re.compile(
    r"secrets\.\w*(?:SSH|VPS|DEPLOY_KEY|PRIVATE_KEY|KNOWN_HOSTS|SERVER_HOST|"
    r"KUBE|KUBECONFIG|SUDO|ROOT_PASSWORD)\w*",
    re.IGNORECASE,
)

# `GITHUB_TOKEN` es legitimo: su alcance muere con el job y no da acceso a
# ninguna maquina. Publicar una imagen es exactamente el permiso maximo que
# ADR-023 le concede al pipeline.
SECRETOS_PERMITIDOS = frozenset({"secrets.GITHUB_TOKEN"})


def _sin_comentarios_de_shell(guion: str) -> str:
    """Saca los comentarios `#` de un bloque `run:`.

    El parseo de YAML ya descarto los comentarios del YAML, pero no los de
    adentro de un script: `# no usar ssh aca` sigue siendo texto del valor.
    """
    limpio = []
    for linea in guion.splitlines():
        sin = re.sub(r"#.*$", "", linea)
        limpio.append(sin)
    return "\n".join(limpio)


def _recorrer(nodo: Any, ruta: str = "") -> list[tuple[str, str, Any]]:
    """Aplana el arbol del YAML a `(ruta, clave, valor)` para los strings."""
    encontrados: list[tuple[str, str, Any]] = []
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            sub = f"{ruta}.{clave}" if ruta else str(clave)
            if isinstance(valor, str):
                encontrados.append((sub, str(clave), valor))
            else:
                encontrados.extend(_recorrer(valor, sub))
    elif isinstance(nodo, list):
        for i, valor in enumerate(nodo):
            sub = f"{ruta}[{i}]"
            if isinstance(valor, str):
                encontrados.append((sub, "", valor))
            else:
                encontrados.extend(_recorrer(valor, sub))
    return encontrados


def infracciones(contenido: str) -> list[str]:
    """Devuelve las infracciones del contrato de seguridad del pipeline.

    Publica a proposito: el test negativo la usa contra un workflow sintetico
    para probar que este control detecta algo de verdad.
    """
    documento = yaml.safe_load(contenido)
    problemas: list[str] = []

    for ruta, clave, valor in _recorrer(documento):
        # 1. Acciones de despliegue por sesion remota
        if clave == "uses":
            for accion in ACCIONES_PROHIBIDAS:
                if valor.startswith(accion):
                    problemas.append(f"{ruta}: usa la accion prohibida '{accion}'")

        # 2. Comandos que alcanzan la maquina
        if clave == "run":
            guion = _sin_comentarios_de_shell(valor)
            hallazgo = COMANDOS_PROHIBIDOS.search(guion)
            if hallazgo:
                problemas.append(f"{ruta}: invoca '{hallazgo.group().strip()}' contra un servidor")

        # 3. Secretos de credencial de servidor, en cualquier campo
        for referencia in SECRETOS_PROHIBIDOS.finditer(valor):
            texto = referencia.group()
            if texto not in SECRETOS_PERMITIDOS:
                problemas.append(f"{ruta}: referencia el secreto prohibido '{texto}'")

    return problemas


def _workflows() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))


def test_hay_workflows_que_revisar() -> None:
    """Si el glob deja de encontrar archivos, los demas tests pasan vacios.

    Sin esto, mover el directorio de workflows apagaria el control en silencio.
    """
    assert _workflows(), f"no se encontro ningun workflow en {WORKFLOWS}"


@pytest.mark.parametrize("workflow", _workflows(), ids=lambda p: p.name)
def test_el_workflow_no_alcanza_al_vps(workflow: Path) -> None:
    """Ningun workflow tiene ni necesita credenciales del VPS (tarea 9.14)."""
    problemas = infracciones(workflow.read_text(encoding="utf-8"))
    assert not problemas, (
        f"{workflow.name} rompe la frontera de ADR-015/ADR-023:\n  "
        + "\n  ".join(problemas)
        + "\n\nEl VPS TIRA; el pipeline no EMPUJA. Si de verdad hace falta "
        "invertir esto, se registra como desvio explicito en un ADR antes de "
        "tocar este test."
    )


def test_el_control_detecta_un_workflow_que_si_despliega() -> None:
    """El control atrapa una infraccion real — no es una tautologia.

    Sin este caso, `infracciones()` podria devolver siempre `[]` y los tests de
    arriba pasarian igual.
    """
    malicioso = """
name: Desplegar
on: [push]
jobs:
  desplegar:
    runs-on: ubuntu-latest
    steps:
      - uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
      - run: |
          # este comentario menciona ssh y NO debe contar
          ssh deploy@servidor 'docker compose up -d'
"""
    problemas = infracciones(malicioso)

    assert any("appleboy/ssh-action" in p for p in problemas), problemas
    assert any("SSH_PRIVATE_KEY" in p for p in problemas), problemas
    assert any("VPS_HOST" in p for p in problemas), problemas
    assert any("invoca 'ssh'" in p for p in problemas), problemas


def test_un_comentario_que_menciona_ssh_no_es_infraccion() -> None:
    """Un `run:` que solo NOMBRA ssh en un comentario pasa.

    Es el falso positivo que haria que alguien desactive el test. Los workflows
    reales de este repositorio explican en comentarios por que ssh esta
    prohibido, asi que este caso no es hipotetico.
    """
    inocente = """
name: CI
on: [push]
jobs:
  probar:
    runs-on: ubuntu-latest
    steps:
      - run: |
          # No usamos ssh ni rsync: el VPS tira, el pipeline no empuja.
          pytest -q
"""
    assert infracciones(inocente) == []


def test_github_token_es_un_secreto_legitimo() -> None:
    """`GITHUB_TOKEN` no se marca: su alcance muere con el job."""
    yaml_de_login_legitimo = """
name: Publicar
on: [push]
jobs:
  publicar:
    runs-on: ubuntu-latest
    steps:
      - uses: docker/login-action@v3
        with:
          password: ${{ secrets.GITHUB_TOKEN }}
"""
    assert infracciones(yaml_de_login_legitimo) == []
