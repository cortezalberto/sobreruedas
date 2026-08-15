"""Los dos escenarios que le faltaban a `platform/configuration`.

Ambos viven bajo el requisito *"Los valores sensibles nunca se exponen"*, y
ninguno estaba cubierto — no por falta de tests, sino porque **la conducta que
tenían que verificar no existía**:

- *"Fallo de arranque por credencial inválida"*: `DATABASE_URL` solo rechazaba
  el valor vacío. Con un valor vacío no se puede demostrar que el mensaje no lo
  filtra: la aserción es vacua. Hace falta una credencial **presente y mal
  formada** para que la prueba diga algo.
- *"Registro de la configuración al arrancar"*: nadie registraba la
  configuración, así que no había registro que auditar.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

import app.config as config_modulo
from app.config import ConfigurationError, get_settings
from app.main import create_app

# Un valor que se reconoce a simple vista en cualquier volcado. Si aparece en un
# mensaje de error o en un log, la fuga es evidente y no hay que interpretarla.
CREDENCIAL = "clave-que-jamas-debe-aparecer"


def variables_sensibles() -> list[str]:
    """Los alias de entorno de todo campo `SecretStr`, leídos del modelo.

    Se derivan del modelo y no de una lista escrita a mano a proposito: una
    lista fija se desactualiza en silencio en cuanto alguien agrega un secreto,
    y el test seguiria pasando sin cubrirlo. Es la forma mas comun de que una
    prueba de no-filtracion deje de probar.
    """
    alias: set[str] = set()
    for nombre in dir(config_modulo):
        grupo = getattr(config_modulo, nombre)
        if not (isinstance(grupo, type) and hasattr(grupo, "model_fields")):
            continue
        for info in grupo.model_fields.values():
            if isinstance(info.validation_alias, str) and "SecretStr" in str(info.annotation):
                alias.add(info.validation_alias)
    return sorted(alias)


# ─────────────────────────────────────────────────────────────────────────────
# Escenario: Fallo de arranque por credencial inválida
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("dsn", "por_que_es_invalido"),
    [
        (f"{CREDENCIAL}@host:5432/deruedas", "sin esquema"),
        (f"postgresql+asyncpg://{CREDENCIAL}", "con esquema pero sin host"),
        (f"://usuario:{CREDENCIAL}@host/deruedas", "esquema vacio"),
    ],
)
def test_credencial_invalida_nombra_la_variable_y_no_filtra_el_valor(
    entorno_valido: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    dsn: str,
    por_que_es_invalido: str,
) -> None:
    """El arranque muere, el mensaje dice CUAL variable, y no dice su valor."""
    monkeypatch.setenv("DATABASE_URL", dsn)
    get_settings.cache_clear()

    with pytest.raises(ConfigurationError) as capturado:
        get_settings()

    mensaje = str(capturado.value)
    assert "DATABASE_URL" in mensaje, f"no nombra la variable ({por_que_es_invalido})"
    assert CREDENCIAL not in mensaje, f"FILTRA la credencial ({por_que_es_invalido})"


def test_un_dsn_bien_formado_sigue_pasando(entorno_valido: dict[str, str]) -> None:
    """Contrapeso del test anterior.

    Sin esto, una validacion demasiado estricta --o directamente rota-- pasaria
    los tres casos invalidos y romperia todos los entornos reales.
    """
    get_settings.cache_clear()
    ajustes = get_settings()
    assert ajustes.database.url.get_secret_value() == entorno_valido["DATABASE_URL"]


# ─────────────────────────────────────────────────────────────────────────────
# Escenario: Registro de la configuración al arrancar
# ─────────────────────────────────────────────────────────────────────────────


def _arrancar_y_capturar(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """Levanta la app entera y devuelve todo lo que se registro al arrancar."""
    caplog.set_level(logging.DEBUG)
    with TestClient(create_app()):
        pass
    return list(caplog.records)


def test_el_arranque_registra_la_configuracion_efectiva(
    entorno_valido: dict[str, str], caplog: pytest.LogCaptureFixture
) -> None:
    """Que quede registro de con que configuracion arranco el proceso.

    Sin esto, diagnosticar "anda distinto en staging" empieza por adivinar que
    variables tenia el proceso, que es donde se va la primera hora.
    """
    registros = _arrancar_y_capturar(caplog)
    texto = "\n".join(r.getMessage() for r in registros)
    assert "DATABASE_URL" in texto, "el arranque no registra la configuracion efectiva"


def test_el_registro_de_arranque_incluye_los_valores_no_sensibles(
    entorno_valido: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Contrapeso imprescindible del test de no-filtracion.

    Un registro vacio no filtra nada y pasaria la prueba de abajo sin esfuerzo.
    Este test exige que el registro efectivamente diga algo.
    """
    monkeypatch.setenv("S3_BUCKET", "bucket-bien-visible")
    get_settings.cache_clear()

    registros = _arrancar_y_capturar(caplog)
    texto = "\n".join(r.getMessage() for r in registros)
    assert "bucket-bien-visible" in texto


def test_el_registro_de_arranque_no_filtra_ningun_valor_sensible(
    entorno_valido: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ni uno de los campos `SecretStr` aparece en claro al arrancar.

    A cada variable sensible se le pone un valor unico y reconocible, asi el
    fallo dice exactamente cual se escapo en vez de "algo se filtro".
    """
    sensibles = variables_sensibles()
    assert sensibles, "no se detecto ningun campo sensible: el test se quedo sin objeto"

    valores = {variable: f"{CREDENCIAL}-{variable}" for variable in sensibles}
    for variable, valor in valores.items():
        monkeypatch.setenv(variable, valor)
    # DATABASE_URL es sensible pero ademas tiene que ser un DSN valido.
    valores["DATABASE_URL"] = f"postgresql+asyncpg://u:{CREDENCIAL}-DATABASE_URL@db:5432/deruedas"
    monkeypatch.setenv("DATABASE_URL", valores["DATABASE_URL"])
    get_settings.cache_clear()

    registros = _arrancar_y_capturar(caplog)
    texto = "\n".join(r.getMessage() for r in registros)

    filtradas = [variable for variable, valor in valores.items() if valor in texto]
    assert not filtradas, f"el registro de arranque filtro: {', '.join(filtradas)}"


def test_la_serializacion_tampoco_filtra_al_registrarse(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """El enmascarado no depende de como se arme el mensaje.

    Verifica el mecanismo en si: cualquier `SecretStr` puesto en un `%s` da su
    forma enmascarada, no el valor.
    """
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", CREDENCIAL)
    get_settings.cache_clear()
    ajustes = get_settings()

    rendido: Any = f"{ajustes.keycloak.client_secret}"
    assert CREDENCIAL not in rendido
    assert isinstance(ajustes.keycloak.client_secret, SecretStr)
