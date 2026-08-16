"""Las migraciones contra PostgreSQL real — C-02, tareas 1.2 y 1.7.

Por que corren de verdad y no contra un doble: una migracion es un efecto sobre
una base concreta. Un test que "verifica" una migracion sin ejecutarla verifica
el texto del archivo, que es justo lo que nadie necesita comprobar.

Se corre con:

    docker compose run --rm backend pytest -m integration

La base de tests del CI arranca vacia y con el init de extensiones de
desarrollo, que trae `pgcrypto`, `pg_trgm`, `postgis` y `uuid-ossp` pero NO
`unaccent` ni `btree_gin`. Esas dos solo pueden llegar por migracion — que es
exactamente el camino que tienen que recorrer para llegar a staging y a
produccion, donde ese init NO corre.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import asyncpg
import pytest

pytestmark = pytest.mark.integration

RAIZ_BACKEND = Path(__file__).resolve().parent.parent.parent

DSN = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://deruedas:deruedas@postgres:5432/deruedas"
)

# Las cuatro que el stack declara y que T-009 exige. `postgis` y `pgcrypto` no
# entran: las instala el init local y, en los ambientes gestionados, Terraform.
EXTENSIONES_EXIGIDAS = ("uuid-ossp", "pg_trgm", "unaccent", "btree_gin")

# Alembic construye `Settings` a traves de env.py, asi que necesita el conjunto
# minimo de variables obligatorias. En el runner del CI solo estan las TEST_*,
# de modo que las demas se pasan explicitamente con valores de descarte: esta
# corrida migra, no se conecta a Keycloak ni a S3.
ENTORNO_DE_MIGRACION = {
    "KEYCLOAK_CLIENT_SECRET": "no-se-usa-en-esta-corrida",
    "S3_ACCESS_KEY": "no-se-usa-en-esta-corrida",
    "S3_SECRET_KEY": "no-se-usa-en-esta-corrida",
    "TENANT_SECRETS_MASTER_KEY": "no-se-usa-en-esta-corrida",
}


def dsn_asyncpg(url: str) -> str:
    """`postgresql+asyncpg://...` -> `postgresql://...` (asyncpg lo quiere pelado)."""
    return url.replace("+asyncpg", "", 1)


def alembic(*argumentos: str) -> subprocess.CompletedProcess[str]:
    """Corre alembic como PROCESO, igual que `make migrate`.

    Invocarlo por API en vez de por linea de comandos probaria un camino que
    nadie usa: ni el Makefile ni el despliegue llaman a `command.upgrade`.
    """
    # noqa S603: no hay entrada no confiable. El ejecutable es el interprete de
    # este mismo proceso y los argumentos son literales de este archivo. Correr
    # alembic por proceso es justamente el punto del test.
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", *argumentos],
        cwd=RAIZ_BACKEND,
        capture_output=True,
        text=True,
        env={**os.environ, **ENTORNO_DE_MIGRACION, "DATABASE_URL": DSN},
    )


@pytest.fixture(scope="module")
def base_migrada() -> None:
    resultado = alembic("upgrade", "head")
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


async def extensiones_presentes() -> set[str]:
    conexion = await asyncpg.connect(dsn_asyncpg(DSN), timeout=10)
    try:
        filas = await conexion.fetch("SELECT extname FROM pg_extension")
    finally:
        await conexion.close()
    return {fila["extname"] for fila in filas}


@pytest.mark.parametrize("extension", EXTENSIONES_EXIGIDAS)
async def test_la_extension_queda_habilitada(base_migrada: None, extension: str) -> None:
    """Una por una y no todas juntas: si faltan dos, el reporte nombra las dos."""
    assert extension in await extensiones_presentes()


async def test_migrar_dos_veces_no_falla(base_migrada: None) -> None:
    """`upgrade head` sobre una base ya migrada es un no-op, no un error.

    Importa porque el despliegue lo corre en cada arranque: si fallara al no
    tener nada que hacer, todo despliegue sin migraciones nuevas quedaria rojo.
    """
    resultado = alembic("upgrade", "head")
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
