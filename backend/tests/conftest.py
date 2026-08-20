"""Fixtures comunes de la suite del backend."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

# Conjunto minimo de variables con el que Settings debe construirse sin fallar.
# Solo las obligatorias: el resto tiene default y se prueba aparte.
ENTORNO_MINIMO: dict[str, str] = {
    "DATABASE_URL": "postgresql+asyncpg://u:p@db:5432/deruedas",
    "KEYCLOAK_CLIENT_SECRET": "secreto-de-keycloak",
    "S3_ACCESS_KEY": "clave-de-acceso",
    "S3_SECRET_KEY": "clave-secreta",
    "TENANT_SECRETS_MASTER_KEY": "master-key-de-tenants",
}

# Prefijos de toda variable que Settings pueda llegar a leer. Se limpian antes
# de cada test para que el entorno de quien corre la suite no la contamine: un
# test que pasa porque el desarrollador tiene exportada una variable es un test
# que miente.
PREFIJOS = (
    "APP_",
    "API_",
    "CORS_",
    "DATABASE_",
    "REDIS_",
    "CELERY_",
    "OPENSEARCH_",
    "KEYCLOAK_",
    "S3_",
    "CDN_",
    "WHATSAPP_",
    "TENANT_",
    "KMS_",
    "MERCADOPAGO_",
    "SENTRY_",
    "OTEL_",
    "LOG_",
    "SMTP_",
)


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Borra toda variable del proyecto antes de cada test.

    `autouse` a proposito: olvidarse de pedir el aislamiento es exactamente el
    error que este fixture existe para evitar.
    """
    for nombre in list(os.environ):
        if nombre.startswith(PREFIJOS):
            monkeypatch.delenv(nombre, raising=False)
    yield


@pytest.fixture
def entorno_valido(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Carga el conjunto minimo de variables obligatorias."""
    for nombre, valor in ENTORNO_MINIMO.items():
        monkeypatch.setenv(nombre, valor)
    return dict(ENTORNO_MINIMO)
