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

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def entorno_real(monkeypatch: pytest.MonkeyPatch) -> None:
    """Apunta a los servicios del compose, no a los valores de prueba.

    El fixture `entorno_limpio` del conftest borra las variables antes de cada
    test; acá se reponen las que hacen falta para hablar con los servicios de
    verdad.
    """
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://deruedas:deruedas@postgres:5432/deruedas"
    )
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
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
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://deruedas:deruedas@redis:6379/deruedas")
    get_settings.cache_clear()
    with TestClient(create_app()) as cliente:
        respuesta = cliente.get("/ready")
    assert respuesta.status_code == 503
    assert "database" in respuesta.json()["failed"]


def test_base_de_datos_inalcanzable_da_no_disponible(
    monkeypatch: pytest.MonkeyPatch, entorno_real: None
) -> None:
    """Puerto cerrado de verdad, no una excepcion simulada."""
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://deruedas:deruedas@postgres:59999/deruedas"
    )
    get_settings.cache_clear()
    with TestClient(create_app()) as cliente:
        respuesta = cliente.get("/ready")
    assert respuesta.status_code == 503
    assert "database" in respuesta.json()["failed"]


def test_redis_inalcanzable_da_no_disponible(
    monkeypatch: pytest.MonkeyPatch, entorno_real: None
) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://redis:59999/0")
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
        "postgresql+asyncpg://usuario_secreto:clave_secreta@postgres:59999/deruedas",
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
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://deruedas:deruedas@postgres:59999/deruedas"
    )
    monkeypatch.setenv("REDIS_URL", "redis://redis:59999/0")
    get_settings.cache_clear()
    with TestClient(create_app()) as cliente:
        assert cliente.get("/ready").status_code == 503
        assert cliente.get("/health").status_code == 200
