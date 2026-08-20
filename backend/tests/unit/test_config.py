"""Contrato de configuracion — T-004, capability `platform/configuration`.

Lo que se prueba acá sale de los criterios de done de T-004 y de la tabla
canonica de docs/adr/ADR-013-variables-de-entorno.md:

  - tipos y valores por defecto
  - muerte temprana con un error que NOMBRA la variable culpable
  - los secretos no se filtran por repr, serializacion ni mensajes de error
  - APP_ENV solo admite local | ci | staging | production
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import get_args

import pytest

from app.config import Ambiente, ConfigurationError, Settings, get_settings

# ─────────────────────────────────────────────────────────────────────────────
# 4.1 — Tipos y defaults
# ─────────────────────────────────────────────────────────────────────────────


def test_construye_con_las_obligatorias(entorno_valido: dict[str, str]) -> None:
    ajustes = Settings()
    # DATABASE_URL esta marcada sensible en ADR-013 porque lleva las
    # credenciales embebidas: el valor solo sale pidiendolo explicitamente.
    assert ajustes.database.url.get_secret_value() == entorno_valido["DATABASE_URL"]


def test_database_url_esta_enmascarada(entorno_valido: dict[str, str]) -> None:
    ajustes = Settings()
    assert entorno_valido["DATABASE_URL"] not in repr(ajustes)
    assert entorno_valido["DATABASE_URL"] not in str(ajustes.model_dump())


@pytest.mark.parametrize(
    ("acceso", "esperado"),
    [
        (lambda s: s.database.pool_size, 20),
        (lambda s: s.app.env, "local"),
        (lambda s: s.observability.log_level, "INFO"),
        (lambda s: str(s.redis.url), "redis://redis:6379/0"),
        (lambda s: s.s3.bucket, "deruedas-media"),
    ],
)
def test_defaults(
    entorno_valido: dict[str, str],
    acceso: Callable[[Settings], object],
    esperado: object,
) -> None:
    assert acceso(Settings()) == esperado


def test_los_tipos_se_convierten(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Una variable de entorno siempre llega como str; el entero debe salir int."""
    monkeypatch.setenv("DATABASE_POOL_SIZE", "42")
    ajustes = Settings()
    assert ajustes.database.pool_size == 42
    assert isinstance(ajustes.database.pool_size, int)


def test_cors_origins_se_parte_por_coma(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    assert Settings().app.cors_origins == ["http://a.test", "http://b.test"]


# ─────────────────────────────────────────────────────────────────────────────
# 4.2 — Muerte temprana, con el nombre de la variable en el mensaje
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("faltante", sorted(["DATABASE_URL", "S3_SECRET_KEY"]))
def test_falta_obligatoria_nombra_la_variable(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch, faltante: str
) -> None:
    monkeypatch.delenv(faltante, raising=False)
    with pytest.raises(ConfigurationError) as capturado:
        get_settings.cache_clear()
        get_settings()
    assert faltante in str(capturado.value)


def test_tipo_invalido_nombra_la_variable(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_POOL_SIZE", "no-es-un-numero")
    with pytest.raises(ConfigurationError) as capturado:
        get_settings.cache_clear()
        get_settings()
    assert "DATABASE_POOL_SIZE" in str(capturado.value)


@pytest.mark.parametrize(
    "vacia",
    sorted(
        [
            "DATABASE_URL",
            "KEYCLOAK_CLIENT_SECRET",
            "S3_ACCESS_KEY",
            "S3_SECRET_KEY",
            "TENANT_SECRETS_MASTER_KEY",
        ]
    ),
)
def test_obligatoria_vacia_se_rechaza(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch, vacia: str
) -> None:
    """Una obligatoria presente pero VACIA es peor que una ausente.

    La ausente te frena al arrancar. La vacia te deja arrancar y cifrar con
    nada, conectarte a ninguna base, autenticarte con un secreto de cero bytes.
    `DATABASE_URL=` en un `.env` mal copiado es un accidente comun.
    """
    monkeypatch.setenv(vacia, "")
    with pytest.raises(ConfigurationError) as capturado:
        get_settings.cache_clear()
        get_settings()
    assert vacia in str(capturado.value)


@pytest.mark.parametrize(
    ("opcional", "acceso"),
    [
        ("SENTRY_DSN", lambda s: s.observability.sentry_dsn),
        ("KMS_KEY_ID", lambda s: s.crypto.kms_key_id),
        ("WHATSAPP_APP_SECRET", lambda s: s.whatsapp.app_secret),
        ("SMTP_USER", lambda s: s.mail.user),
    ],
)
def test_opcional_vacia_equivale_a_no_configurada(
    entorno_valido: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    opcional: str,
    acceso: Callable[[Settings], object],
) -> None:
    """`SENTRY_DSN=` significa "desactivado", no "un secreto de cero bytes".

    Sin esto, `if settings.observability.sentry_dsn:` da falso igual, pero
    `.get_secret_value()` devuelve `''` y cualquier cliente que lo reciba
    intenta conectarse a la nada.
    """
    monkeypatch.setenv(opcional, "")
    assert acceso(Settings()) is None


def test_el_error_lista_todas_las_faltantes_no_solo_la_primera(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Que las nombre a todas: arreglar de a una y volver a arrancar es tortura."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("S3_ACCESS_KEY", raising=False)
    with pytest.raises(ConfigurationError) as capturado:
        get_settings.cache_clear()
        get_settings()
    mensaje = str(capturado.value)
    assert "DATABASE_URL" in mensaje
    assert "S3_ACCESS_KEY" in mensaje


# ─────────────────────────────────────────────────────────────────────────────
# 4.3 — Enmascarado de secretos
# ─────────────────────────────────────────────────────────────────────────────

SECRETO = "valor-ultrasecreto-que-no-debe-aparecer"


@pytest.fixture
def ajustes_con_secreto(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> Settings:
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", SECRETO)
    monkeypatch.setenv("S3_SECRET_KEY", SECRETO)
    monkeypatch.setenv("TENANT_SECRETS_MASTER_KEY", SECRETO)
    return Settings()


def test_repr_no_filtra(ajustes_con_secreto: Settings) -> None:
    assert SECRETO not in repr(ajustes_con_secreto)
    assert SECRETO not in repr(ajustes_con_secreto.keycloak)


def test_str_no_filtra(ajustes_con_secreto: Settings) -> None:
    assert SECRETO not in str(ajustes_con_secreto)


def test_model_dump_no_filtra(ajustes_con_secreto: Settings) -> None:
    assert SECRETO not in str(ajustes_con_secreto.model_dump())


def test_json_no_filtra(ajustes_con_secreto: Settings) -> None:
    volcado = ajustes_con_secreto.model_dump_json()
    assert SECRETO not in volcado
    json.loads(volcado)  # y ademas sigue siendo JSON valido


def test_el_secreto_se_puede_leer_a_proposito(ajustes_con_secreto: Settings) -> None:
    """Enmascarar no es esconder: el valor tiene que estar disponible."""
    assert ajustes_con_secreto.keycloak.client_secret.get_secret_value() == SECRETO


def test_mensaje_de_error_no_filtra(
    ajustes_con_secreto: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un fallo en OTRO campo no debe arrastrar los secretos al mensaje."""
    monkeypatch.setenv("DATABASE_POOL_SIZE", "no-es-un-numero")
    with pytest.raises(ConfigurationError) as capturado:
        get_settings.cache_clear()
        get_settings()
    assert SECRETO not in str(capturado.value)


# ─────────────────────────────────────────────────────────────────────────────
# 4.4 — APP_ENV
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("ambiente", ["local", "ci", "staging", "production"])
def test_app_env_acepta_los_cuatro(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch, ambiente: str
) -> None:
    monkeypatch.setenv("APP_ENV", ambiente)
    assert Settings().app.env == ambiente


@pytest.mark.parametrize("invalido", ["development", "prod", "PRODUCTION", "", "qa"])
def test_app_env_rechaza_lo_demas(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch, invalido: str
) -> None:
    monkeypatch.setenv("APP_ENV", invalido)
    with pytest.raises(ConfigurationError) as capturado:
        get_settings.cache_clear()
        get_settings()
    mensaje = str(capturado.value)
    assert "APP_ENV" in mensaje

    # El escenario *"Ambiente no reconocido"* pide que el mensaje ENUMERE los
    # valores permitidos, y no solo que nombre la variable. Hoy lo cumple
    # gratis: es el texto que pydantic arma para un `Literal`. Por eso mismo
    # hace falta afirmarlo — cambiar `Ambiente` por un `str` con un validador a
    # mano deja el test verde por el assert de arriba, y a quien se equivoco
    # escribiendo `prod` sin la lista de lo que si puede escribir.
    #
    # ⚠️ Se busca en la LINEA de APP_ENV, no en el mensaje entero: "ci" es
    # substring de "configuracion", que esta en el encabezado del error. Contra
    # el mensaje completo la afirmacion pasaria sola.
    linea = next(ln for ln in mensaje.splitlines() if "APP_ENV" in ln)
    for permitido in get_args(Ambiente):
        assert permitido in linea, f"el error no enumera '{permitido}': {linea}"


@pytest.mark.parametrize(
    ("ambiente", "es_produccion"),
    [("local", False), ("ci", False), ("staging", False), ("production", True)],
)
def test_is_production(
    entorno_valido: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    ambiente: str,
    es_produccion: bool,
) -> None:
    monkeypatch.setenv("APP_ENV", ambiente)
    assert Settings().app.is_production is es_produccion


# ─────────────────────────────────────────────────────────────────────────────
# JWKS — ADR-013 elige el endpoint por sobre la clave publica embebida,
# porque una clave pegada obliga a un deploy cada vez que Keycloak rota.
# ─────────────────────────────────────────────────────────────────────────────


def test_jwks_endpoint_usa_el_explicito_si_esta(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KEYCLOAK_JWKS_URL", "https://idp.test/otro/jwks")
    assert Settings().keycloak.jwks_endpoint == "https://idp.test/otro/jwks"


def test_jwks_endpoint_se_deduce_del_realm_si_no_esta(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KEYCLOAK_URL", "https://idp.test")
    monkeypatch.setenv("KEYCLOAK_REALM", "deruedas")
    assert (
        Settings().keycloak.jwks_endpoint
        == "https://idp.test/realms/deruedas/protocol/openid-connect/certs"
    )


def test_el_jwks_deducido_coincide_con_el_de_env_example(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si la deduccion y .env.example divergen, uno de los dos miente."""
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8080")
    monkeypatch.setenv("KEYCLOAK_REALM", "deruedas-dev")
    assert Settings().keycloak.jwks_endpoint == (
        "http://localhost:8080/realms/deruedas-dev/protocol/openid-connect/certs"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4.7 — Singleton cacheado
# ─────────────────────────────────────────────────────────────────────────────


def test_get_settings_devuelve_siempre_la_misma_instancia(
    entorno_valido: dict[str, str],
) -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()


def test_cache_clear_fuerza_una_relectura(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    get_settings.cache_clear()
    primera = get_settings()
    monkeypatch.setenv("DATABASE_POOL_SIZE", "77")
    assert get_settings() is primera, "sin limpiar la cache debe devolver la vieja"
    get_settings.cache_clear()
    assert get_settings().database.pool_size == 77


# ── El emisor publico, que no siempre es la URL interna ──────────────────────


def test_el_emisor_se_deduce_del_realm_cuando_no_esta_declarado(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    get_settings.cache_clear()
    assert get_settings().keycloak.emisor == "http://keycloak:8080/realms/deruedas-dev"


def test_el_emisor_declarado_gana_sobre_la_url_interna(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """El caso que importa, y el que rompe el login por navegador.

    Keycloak emite el `iss` con el hostname PUBLICO —por el que el navegador
    pidio el token— y el backend lo alcanza por el nombre interno de la red. Si
    el emisor esperado se dedujera siempre de la URL interna, todo token venido
    de un login real se rechazaria con 401, y el sintoma pareceria un problema
    de firma.
    """
    monkeypatch.setenv("KEYCLOAK_URL", "http://keycloak:8080")
    monkeypatch.setenv("KEYCLOAK_ISSUER", "https://cuentas.deruedas.test/realms/deruedas")
    get_settings.cache_clear()

    keycloak = get_settings().keycloak
    assert keycloak.emisor == "https://cuentas.deruedas.test/realms/deruedas"
    # Y el JWKS sigue saliendo por la red interna: son dos caminos distintos.
    assert keycloak.jwks_endpoint.startswith("http://keycloak:8080")
