"""Sondas contra servicios REALES — T-005, tarea 5.9.

Los unitarios de `tests/unit/test_app_health.py` prueban el CONTRATO de las
sondas con las dependencias sustituidas. Acá se prueban las sondas de verdad:
que abran una conexion a PostgreSQL y a Redis y sepan distinguir una que
responde de una que no.

Sin mocks de base de datos (regla dura 8). Se corre con:

    docker compose run --rm backend pytest -m integration

Las direcciones salen del entorno del contenedor, o sea de los nombres de
servicio del compose.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

pytestmark = pytest.mark.integration


# Direcciones de los servicios reales. Se leen del entorno con default para el
# compose de desarrollo, donde los servicios se resuelven por NOMBRE.
#
# En CI el pytest corre en el runner y los servicios exponen puertos en
# localhost, asi que el workflow las sobreescribe. Hardcodear `postgres:5432`
# haria que estos tests solo pudieran correr adentro de la red del compose.
DSN_POSTGRES = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://deruedas:deruedas@postgres:5432/deruedas"
)
URL_REDIS = os.getenv("TEST_REDIS_URL", "redis://redis:6379/0")

# Host y puerto sueltos para los tests que necesitan apuntar a un puerto cerrado
# o al puerto equivocado a proposito.
HOST_POSTGRES = urlparse(DSN_POSTGRES).hostname or "postgres"
HOST_REDIS = urlparse(URL_REDIS).hostname or "redis"
PUERTO_REDIS = urlparse(URL_REDIS).port or 6379

# Alto en el rango efimero y sin asignar por IANA: nada deberia estar
# escuchando ahi. Es el puerto que se usa para provocar una conexion rechazada
# de verdad, en vez de simular la excepcion.
PUERTO_CERRADO = 59999


def dsn_postgres_apuntando_a(host: str, puerto: int) -> str:
    """Reapunta el DSN de PostgreSQL a otra direccion, conservando el resto.

    Existe porque el `str.replace` que habia antes no servia, y de dos formas
    distintas segun el entorno:

    - En CI, PostgreSQL y Redis viven los dos en `localhost` y solo difieren en
      el puerto, asi que reemplazar el host por el otro host no cambiaba nada.
      El DSN seguia apuntando a la base real y sana.
    - Con los defaults del compose (`postgres` y `redis`), reemplazar la cadena
      "postgres" tambien pisaba el ESQUEMA: `postgresql+asyncpg://` quedaba
      `redisql+asyncpg://`. El DSN malformado fallaba al parsearse y devolvia
      503, asi que la asercion pasaba sin haber probado nunca que la sonda
      abriera una conexion.

    Construir el DSN por partes en vez de parchear texto cierra las dos.
    """
    partes = urlparse(DSN_POSTGRES)
    credenciales = f"{partes.username}:{partes.password}@" if partes.username else ""
    return f"{partes.scheme}://{credenciales}{host}:{puerto}{partes.path}"


@pytest.fixture
def entorno_real(monkeypatch: pytest.MonkeyPatch) -> None:
    """Apunta a los servicios reales.

    El fixture `entorno_limpio` del conftest borra las variables antes de cada
    test; aca se reponen las que hacen falta para hablar con los servicios de
    verdad.
    """
    monkeypatch.setenv("DATABASE_URL", DSN_POSTGRES)
    monkeypatch.setenv("REDIS_URL", URL_REDIS)
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "no-se-usa-en-este-test")
    monkeypatch.setenv("S3_ACCESS_KEY", "no-se-usa-en-este-test")
    monkeypatch.setenv("S3_SECRET_KEY", "no-se-usa-en-este-test")
    monkeypatch.setenv("TENANT_SECRETS_MASTER_KEY", "no-se-usa-en-este-test")
    get_settings.cache_clear()


def test_ready_contra_servicios_reales(entorno_real: None) -> None:
    """PostgreSQL y Redis arriba: la sonda debe dar disponible."""
    with TestClient(create_app()) as cliente:
        respuesta = cliente.get("/ready")
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["status"] == "ready"


def test_la_sonda_hace_mas_que_abrir_el_socket(
    monkeypatch: pytest.MonkeyPatch, entorno_real: None
) -> None:
    """Se apunta la base al puerto de Redis: abierto, pero no habla PostgreSQL.

    Si la sonda solo mirara si el puerto acepta conexiones, esto daria
    disponible. Un PostgreSQL que acepta TCP pero todavia esta recuperandose no
    sirve para atender trafico, y una sonda que solo mira el puerto lo declara
    listo igual — que es la forma mas comun de que una sonda mienta.
    """
    monkeypatch.setenv("DATABASE_URL", dsn_postgres_apuntando_a(HOST_REDIS, PUERTO_REDIS))
    get_settings.cache_clear()
    with TestClient(create_app()) as cliente:
        respuesta = cliente.get("/ready")
    assert respuesta.status_code == 503
    assert "database" in respuesta.json()["failed"]


def test_base_de_datos_inalcanzable_da_no_disponible(
    monkeypatch: pytest.MonkeyPatch, entorno_real: None
) -> None:
    """Puerto cerrado de verdad, no una excepcion simulada."""
    monkeypatch.setenv("DATABASE_URL", dsn_postgres_apuntando_a(HOST_POSTGRES, PUERTO_CERRADO))
    get_settings.cache_clear()
    with TestClient(create_app()) as cliente:
        respuesta = cliente.get("/ready")
    assert respuesta.status_code == 503
    assert "database" in respuesta.json()["failed"]


def test_redis_inalcanzable_da_no_disponible(
    monkeypatch: pytest.MonkeyPatch, entorno_real: None
) -> None:
    monkeypatch.setenv("REDIS_URL", f"redis://{HOST_REDIS}:{PUERTO_CERRADO}/0")
    get_settings.cache_clear()
    with TestClient(create_app()) as cliente:
        respuesta = cliente.get("/ready")
    assert respuesta.status_code == 503
    assert "redis" in respuesta.json()["failed"]


def test_el_503_no_filtra_la_cadena_de_conexion(
    monkeypatch: pytest.MonkeyPatch, entorno_real: None
) -> None:
    """La excepcion de asyncpg suele traer la URL completa con la contrasena."""
    monkeypatch.setenv(
        "DATABASE_URL",
        f"postgresql+asyncpg://usuario_secreto:clave_secreta@{HOST_POSTGRES}:{PUERTO_CERRADO}/deruedas",
    )
    get_settings.cache_clear()
    with TestClient(create_app()) as cliente:
        cuerpo = cliente.get("/ready").text
    assert "clave_secreta" not in cuerpo
    assert "usuario_secreto" not in cuerpo
    assert "postgresql" not in cuerpo


def test_health_responde_aunque_las_dependencias_esten_caidas(
    monkeypatch: pytest.MonkeyPatch, entorno_real: None
) -> None:
    """La sonda de VIDA no mira dependencias. Si lo hiciera, una caida de
    PostgreSQL haria que Kubernetes reinicie el pod en loop sin arreglar nada.
    """
    monkeypatch.setenv("DATABASE_URL", dsn_postgres_apuntando_a(HOST_POSTGRES, PUERTO_CERRADO))
    monkeypatch.setenv("REDIS_URL", f"redis://{HOST_REDIS}:{PUERTO_CERRADO}/0")
    get_settings.cache_clear()
    with TestClient(create_app()) as cliente:
        assert cliente.get("/ready").status_code == 503
        assert cliente.get("/health").status_code == 200
