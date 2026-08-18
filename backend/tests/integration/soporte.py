"""Soporte comun de los tests de integracion — ADR-020.

DOS CONEXIONES, PORQUE HAY DOS ROLES
────────────────────────────────────
Desde ADR-020 la aplicacion se conecta con un rol que **no puede** crear tablas,
alterar politicas ni saltear RLS. Eso es lo que hace que la capa 2 del
aislamiento multi-tenant exista de verdad, y tambien lo que rompe a los tests
que hasta ahora hacian DDL por la misma puerta que consultaban.

    DSN_APLICACION   lo que se PRUEBA. Rol `mitutu`: SELECT/INSERT/UPDATE.
    DSN_PROPIETARIO  ANDAMIAJE de los tests. Crea y destruye tablas, prende y
                     apaga politicas.

POR QUE `sesion_de_propietario` VIVE ACA Y NO EN `app/`
──────────────────────────────────────────────────────
Porque no es codigo de la aplicacion. En `app/db/session.py` seria una funcion
que ningun camino de produccion usa y que cualquiera podria llamar — o sea, un
agujero con nombre amable. Aca es lo que realmente es: andamiaje de prueba.

Ojo con la tentacion de usarla para "arreglar" un test que falla por permisos:
si un test de aplicacion necesita el propietario, lo que esta mal es el test o
el permiso, no la puerta que usa.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import sesion_de_plataforma

RAIZ_BACKEND = Path(__file__).resolve().parent.parent.parent

# Rol de aplicacion (`mitutu`): NOSUPERUSER, NOBYPASSRLS, sin DDL y sin DELETE.
# Es con el que corren los tests que prueban comportamiento del sistema.
DSN_APLICACION = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://mitutu:mitutu@postgres:5432/deruedas"
)

# Rol propietario: dueno del esquema. Solo para migrar y para el andamiaje.
DSN_PROPIETARIO = os.getenv(
    "TEST_DATABASE_OWNER_URL", "postgresql+asyncpg://deruedas:deruedas@postgres:5432/deruedas"
)

# Redis real para los tests de eventos de dominio. Sin doble: Redis Streams con
# consumer groups es lo que se prueba, y un doble probaria el doble.
URL_REDIS = os.getenv("TEST_REDIS_URL", "redis://redis:6379/0")

# Alembic construye `Settings` a traves de env.py, asi que necesita el conjunto
# minimo de variables obligatorias. En el runner del CI solo estan las TEST_*,
# de modo que las demas se pasan con valores de descarte: esta corrida migra, no
# se conecta a Keycloak ni a S3.
ENTORNO_DE_MIGRACION = {
    "KEYCLOAK_CLIENT_SECRET": "no-se-usa-en-esta-corrida",
    "S3_ACCESS_KEY": "no-se-usa-en-esta-corrida",
    "S3_SECRET_KEY": "no-se-usa-en-esta-corrida",
    "TENANT_SECRETS_MASTER_KEY": "no-se-usa-en-esta-corrida",
}


def dsn_asyncpg(url: str) -> str:
    """`postgresql+asyncpg://...` -> `postgresql://...` (asyncpg lo quiere pelado)."""
    return url.replace("+asyncpg", "", 1)


SIN_URL_DE_MIGRACION = object()


def alembic(
    *argumentos: str,
    url_de_migracion: str | object = DSN_PROPIETARIO,
) -> subprocess.CompletedProcess[str]:
    """Corre alembic como PROCESO, igual que `make migrate`.

    Invocarlo por API en vez de por linea de comandos probaria un camino que
    nadie usa: ni el Makefile ni el despliegue llaman a `command.upgrade`.

    `DATABASE_URL` y `DATABASE_MIGRATION_URL` van las dos porque env.py verifica
    que apunten a la misma base (ADR-020, design.md D-5). `url_de_migracion` es
    parametro para que un test pueda pasar la URL equivocada a proposito y
    comprobar que esa verificacion existe; con `SIN_URL_DE_MIGRACION` la
    variable directamente no se define, que es distinto de definirla vacia.
    """
    entorno = {**os.environ, **ENTORNO_DE_MIGRACION, "DATABASE_URL": DSN_APLICACION}
    if isinstance(url_de_migracion, str):
        entorno["DATABASE_MIGRATION_URL"] = url_de_migracion
    else:
        entorno.pop("DATABASE_MIGRATION_URL", None)

    # noqa S603: no hay entrada no confiable. El ejecutable es el interprete de
    # este mismo proceso y los argumentos son literales de los tests.
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", *argumentos],
        cwd=RAIZ_BACKEND,
        capture_output=True,
        text=True,
        env=entorno,
    )


@asynccontextmanager
async def sesion_de_propietario() -> AsyncIterator[AsyncSession]:
    """Sesion con el rol PROPIETARIO. Solo para andamiaje de tests.

    Es `sesion_de_plataforma` —la sesion sin contexto de tenant— apuntada al
    otro rol. Que hasta ahora `sesion_de_plataforma` pudiera hacer DDL era un
    accidente de que su DSN daba a un superusuario, no algo que su contrato
    prometiera. Ver el encabezado de este modulo.
    """
    async with sesion_de_plataforma(dsn=DSN_PROPIETARIO) as sesion:
        yield sesion


def reponer_entorno(monkeypatch: pytest.MonkeyPatch, *, dsn: str) -> None:
    """Repone las variables que `entorno_limpio` borro, y descachea `Settings`.

    LAS DOS COSAS, Y NINGUNA ES OPCIONAL.

    1. `entorno_limpio` (autouse, conftest raiz) borra TODA variable del proyecto
       antes de cada test. Un test que llegue a la base **a traves de la
       configuracion de la aplicacion** —y no con un DSN explicito— necesita
       reponerlas.

    2. `get_settings` es `lru_cache(maxsize=1)`, y los tests de sondas de
       `test_app_health.py` lo envenenan a proposito apuntando `DATABASE_URL` a
       un puerto cerrado para probar el 503. `monkeypatch` restaura la variable
       al terminar; el objeto `Settings` mal construido se queda en la cache. Sin
       el `cache_clear()`, los tests que dependen de la configuracion **pasan
       solos y fallan en la suite completa**, conectandose al puerto muerto que
       dejo otro archivo.

    EL `dsn` ES PARAMETRO Y NO UNA CONSTANTE DE ACA, que es el motivo de que esto
    sea una funcion y no un fixture compartido: las sondas de salud corren con el
    rol PROPIETARIO y los routers con el de APLICACION. Un fixture unico tendria
    que elegir uno, y elegir el equivocado no falla — hace que un test pruebe con
    permisos que la aplicacion no tiene.

    Aparecio con el tercer archivo que lo necesitaba. Con dos estaba duplicado a
    proposito; al tercero, la duplicacion ya era la fuente de verdad.
    """
    monkeypatch.setenv("DATABASE_URL", dsn)
    monkeypatch.setenv("REDIS_URL", URL_REDIS)
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "no-se-usa-en-este-test")
    monkeypatch.setenv("S3_ACCESS_KEY", "no-se-usa-en-este-test")
    monkeypatch.setenv("S3_SECRET_KEY", "no-se-usa-en-este-test")
    monkeypatch.setenv("TENANT_SECRETS_MASTER_KEY", "no-se-usa-en-este-test")
    get_settings.cache_clear()
