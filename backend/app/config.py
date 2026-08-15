"""Contrato de configuracion — T-004, capability `platform/configuration`.

Tabla canonica: docs/adr/ADR-013-variables-de-entorno.md. Los 11 grupos de acá
son los 12 del ADR menos el bloque `Frontend`, que lo lee Next.js y nunca pasa
por el backend.

Tres decisiones que gobiernan este modulo:

1. **Todo secreto es `SecretStr`.** No es cosmetico: es lo que impide que un
   `repr()` en un traceback, un log estructurado o un reporte de Sentry se lleve
   una credencial puesta. Los 15 campos marcados con candado en ADR-013 son
   `SecretStr` sin excepcion.

2. **Muerte temprana, y el error nombra la variable.** Un proceso que arranca
   con la configuracion rota y explota tres semanas despues, un martes a las 3
   de la manana, es peor que uno que no arranca.

3. **El mensaje de error NUNCA incluye el valor.** Solo el nombre de la
   variable y el motivo. Un error de configuracion se loguea, y un log con el
   secreto adentro es exactamente lo que el punto 1 evita.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import BeforeValidator, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Ambiente = Literal["local", "ci", "staging", "production"]


def _vacio_es_ausente(valor: object) -> object:
    """Una variable presente pero vacia equivale a no configurada.

    `SENTRY_DSN=` en un `.env` significa "desactivado", no "un secreto de cero
    bytes". Sin esta conversion el campo queda como `SecretStr('')`, cualquier
    chequeo de verdad da falso igual, pero un cliente que reciba el valor
    intenta conectarse a la nada.
    """
    return None if valor == "" else valor


# Para las OBLIGATORIAS el criterio es el opuesto: vacia se rechaza. Una
# obligatoria ausente te frena al arrancar; una vacia te deja arrancar y cifrar
# con nada. `DATABASE_URL=` en un .env mal copiado es un accidente comun.
SecretoOpcional = Annotated[SecretStr | None, BeforeValidator(_vacio_es_ausente)]
TextoOpcional = Annotated[str | None, BeforeValidator(_vacio_es_ausente)]

# `extra="ignore"`: el entorno real trae PATH, HOME y decenas mas. Cada grupo
# lee lo suyo y no se ofende por el resto.
_CONFIG = SettingsConfigDict(extra="ignore", case_sensitive=True)


# ─────────────────────────────────────────────────────────────────────────────
# Grupos
# ─────────────────────────────────────────────────────────────────────────────


class AppSettings(BaseSettings):
    model_config = _CONFIG

    env: Ambiente = Field(default="local", validation_alias="APP_ENV")
    api_base_url: str = Field(default="http://localhost:8000", validation_alias="API_BASE_URL")
    # Se guarda crudo y se parte en la propiedad: pydantic-settings intenta
    # decodificar JSON para los tipos compuestos, y "a.test, b.test" no es JSON.
    cors_origins_raw: str = Field(default="http://localhost:3000", validation_alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> list[str]:
        return [origen.strip() for origen in self.cors_origins_raw.split(",") if origen.strip()]

    @property
    def is_production(self) -> bool:
        return self.env == "production"


class DatabaseSettings(BaseSettings):
    model_config = _CONFIG

    # Sensible: lleva usuario y contrasena embebidos en la URL.
    url: SecretStr = Field(min_length=1, validation_alias="DATABASE_URL")
    pool_size: int = Field(default=20, ge=1, validation_alias="DATABASE_POOL_SIZE")

    @field_validator("url")
    @classmethod
    def _dsn_bien_formado(cls, valor: SecretStr) -> SecretStr:
        """Rechaza un DSN mal formado al arrancar, no al primer query.

        `min_length=1` solo atrapa el valor vacio. Una URL con un typo pasaba la
        validacion, el proceso arrancaba sano y el problema recien aparecia como
        una sonda de disponibilidad en rojo, lejos de su causa.

        Se valida la FORMA --esquema, host y nombre de base-- y no el driver: el
        objetivo es cazar el typo, no imponer politica de motor, que ya la fija
        ADR-002.

        El mensaje describe que se esperaba y **nunca incluye el valor**: es una
        credencial, y este error va a parar a los logs de arranque.
        """
        partes = urlparse(valor.get_secret_value())
        if not partes.scheme or not partes.hostname or partes.path.strip("/") == "":
            raise ValueError(
                "no es un DSN valido; se espera "
                "esquema://[usuario:clave@]host[:puerto]/nombre_de_base"
            )
        return valor


class RedisSettings(BaseSettings):
    model_config = _CONFIG

    # Los defaults apuntan a los nombres de servicio del compose, que es como
    # corre el backend por default. Para correrlo en el host, .env.example trae
    # las variantes con localhost.
    url: str = Field(default="redis://redis:6379/0", validation_alias="REDIS_URL")
    celery_broker_url: str = Field(
        default="redis://redis:6379/1", validation_alias="CELERY_BROKER_URL"
    )


class SearchSettings(BaseSettings):
    model_config = _CONFIG

    url: str = Field(default="http://opensearch:9200", validation_alias="OPENSEARCH_URL")
    user: SecretoOpcional = Field(default=None, validation_alias="OPENSEARCH_USER")
    password: SecretoOpcional = Field(default=None, validation_alias="OPENSEARCH_PASSWORD")


class KeycloakSettings(BaseSettings):
    model_config = _CONFIG

    url: str = Field(default="http://keycloak:8080", validation_alias="KEYCLOAK_URL")
    realm: str = Field(default="deruedas-dev", validation_alias="KEYCLOAK_REALM")
    client_id: str = Field(default="backend", validation_alias="KEYCLOAK_CLIENT_ID")
    client_secret: SecretStr = Field(min_length=1, validation_alias="KEYCLOAK_CLIENT_SECRET")
    jwks_url: TextoOpcional = Field(default=None, validation_alias="KEYCLOAK_JWKS_URL")

    @property
    def jwks_endpoint(self) -> str:
        """El JWKS explicito si esta; si no, el que se deduce del realm.

        Se usa el endpoint y no una clave publica embebida para que Keycloak
        pueda rotar su par de claves sin obligar a un deploy (ADR-013).
        """
        if self.jwks_url:
            return self.jwks_url
        return f"{self.url}/realms/{self.realm}/protocol/openid-connect/certs"


class S3Settings(BaseSettings):
    model_config = _CONFIG

    endpoint: str = Field(default="http://minio:9000", validation_alias="S3_ENDPOINT")
    bucket: str = Field(default="deruedas-media", validation_alias="S3_BUCKET")
    access_key: SecretStr = Field(min_length=1, validation_alias="S3_ACCESS_KEY")
    secret_key: SecretStr = Field(min_length=1, validation_alias="S3_SECRET_KEY")
    cdn_base_url: TextoOpcional = Field(default=None, validation_alias="CDN_BASE_URL")


class WhatsAppSettings(BaseSettings):
    model_config = _CONFIG

    # Opcionales: la mensajeria entra en C-19, no en la Ola 0. Exigirlas ahora
    # obligaria a inventar valores para arrancar, que es como se normaliza el
    # habito de poner cualquier cosa en una variable de entorno.
    app_secret: SecretoOpcional = Field(default=None, validation_alias="WHATSAPP_APP_SECRET")
    verify_token: SecretoOpcional = Field(default=None, validation_alias="WHATSAPP_VERIFY_TOKEN")


class CryptoSettings(BaseSettings):
    model_config = _CONFIG

    # Obligatoria: cifra los secretos de cada tenant. Sin esto no hay
    # aislamiento real, y el aislamiento es el Principio 4.
    tenant_secrets_master_key: SecretStr = Field(
        min_length=1, validation_alias="TENANT_SECRETS_MASTER_KEY"
    )
    kms_key_id: SecretoOpcional = Field(default=None, validation_alias="KMS_KEY_ID")


class PaymentSettings(BaseSettings):
    model_config = _CONFIG

    mercadopago_access_token: SecretoOpcional = Field(
        default=None, validation_alias="MERCADOPAGO_ACCESS_TOKEN"
    )


class ObservabilitySettings(BaseSettings):
    model_config = _CONFIG

    sentry_dsn: SecretoOpcional = Field(default=None, validation_alias="SENTRY_DSN")
    # Apunta a Tempo, no a Jaeger (ADR-016). El nombre no cambia porque
    # OpenTelemetry es agnostico del backend.
    otel_exporter_otlp_endpoint: TextoOpcional = Field(
        default=None, validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_traces_sampler_arg: float = Field(
        default=1.0, ge=0.0, le=1.0, validation_alias="OTEL_TRACES_SAMPLER_ARG"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", validation_alias="LOG_LEVEL"
    )


class MailSettings(BaseSettings):
    model_config = _CONFIG

    host: str = Field(default="mailhog:1025", validation_alias="SMTP_HOST")
    user: SecretoOpcional = Field(default=None, validation_alias="SMTP_USER")
    password: SecretoOpcional = Field(default=None, validation_alias="SMTP_PASSWORD")


# ─────────────────────────────────────────────────────────────────────────────
# Raiz
# ─────────────────────────────────────────────────────────────────────────────


class Settings(BaseSettings):
    """Configuracion completa del backend. Se arma sola desde el entorno."""

    model_config = _CONFIG

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    keycloak: KeycloakSettings = Field(default_factory=KeycloakSettings)
    s3: S3Settings = Field(default_factory=S3Settings)
    whatsapp: WhatsAppSettings = Field(default_factory=WhatsAppSettings)
    crypto: CryptoSettings = Field(default_factory=CryptoSettings)
    payment: PaymentSettings = Field(default_factory=PaymentSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    mail: MailSettings = Field(default_factory=MailSettings)


_GRUPOS: tuple[type[BaseSettings], ...] = (
    AppSettings,
    DatabaseSettings,
    RedisSettings,
    SearchSettings,
    KeycloakSettings,
    S3Settings,
    WhatsAppSettings,
    CryptoSettings,
    PaymentSettings,
    ObservabilitySettings,
    MailSettings,
)


ENMASCARADO = "***"
SIN_CONFIGURAR = "(sin configurar)"


def describir_configuracion(settings: Settings) -> list[str]:
    """La configuracion efectiva como lineas `VARIABLE=valor`, sin secretos.

    Se recorre el modelo, no una lista escrita a mano: un secreto nuevo queda
    enmascarado por ser `SecretStr`, sin que nadie tenga que acordarse de
    agregarlo a ningun lado. Una lista paralela es justo lo que se desactualiza
    en silencio, y acá el costo de olvidarse es publicar una credencial.

    Se emiten los nombres de las VARIABLES DE ENTORNO y no los de los campos
    Python: quien lee esto en un incidente va a ir a cambiar una variable.
    """
    lineas: list[str] = []
    for nombre_grupo in Settings.model_fields:
        grupo = getattr(settings, nombre_grupo)
        for campo, info in type(grupo).model_fields.items():
            alias = info.validation_alias
            if not isinstance(alias, str):
                continue
            valor = getattr(grupo, campo)
            if isinstance(valor, SecretStr):
                rendido = ENMASCARADO
            elif valor is None:
                rendido = SIN_CONFIGURAR
            else:
                rendido = str(valor)
            lineas.append(f"{alias}={rendido}")
    return sorted(lineas)


class ConfigurationError(RuntimeError):
    """La configuracion del entorno esta rota. El proceso no debe seguir."""


def _describir(error: ValidationError) -> list[str]:
    """Convierte un ValidationError en lineas legibles, SIN los valores.

    `loc` trae el `validation_alias`, o sea el nombre real de la variable de
    entorno, que es lo unico que le sirve a quien tiene que arreglarla.
    """
    lineas = []
    for detalle in error.errors():
        variable = ".".join(str(parte) for parte in detalle["loc"]) or "(desconocida)"
        lineas.append(f"  - {variable}: {detalle['msg']}")
    return lineas


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la configuracion, cacheada.

    Valida los 11 grupos y junta TODOS los problemas antes de fallar. Arreglar
    de a una variable y volver a arrancar es tortura innecesaria.

    Raises:
        ConfigurationError: si algo falta o no valida. El mensaje nombra cada
            variable culpable y nunca incluye su valor.
    """
    problemas: list[str] = []
    for grupo in _GRUPOS:
        try:
            grupo()
        except ValidationError as error:
            problemas.extend(_describir(error))

    if problemas:
        raise ConfigurationError(
            "La configuracion del entorno es invalida:\n"
            + "\n".join(problemas)
            + "\n\nRevisa tu .env contra .env.example "
            "(tabla canonica: docs/adr/ADR-013-variables-de-entorno.md)."
        )

    return Settings()
