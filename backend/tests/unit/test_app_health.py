"""Sondas, correlacion y gate de documentacion — T-005.

Cubre la capability `platform/service-health`. Cada test apunta a un escenario
de openspec/changes/foundation-setup/specs/platform/service-health/spec.md.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.config import get_settings
from app.main import create_app

CABECERA_CORRELACION = "X-Request-ID"


class CuerpoDePrueba(BaseModel):
    """Modelo de los tests de validacion.

    Va a nivel de MODULO a proposito. Este archivo tiene
    `from __future__ import annotations`, asi que las anotaciones son cadenas y
    FastAPI las resuelve con `get_type_hints()` contra los globals del modulo.
    Un modelo definido adentro de la funcion de test no esta ahi, y FastAPI
    termina interpretando el parametro como algo distinto de un cuerpo JSON.
    """

    cantidad: int


async def _sonda_sana() -> None:
    return None


async def _sonda_caida() -> None:
    raise ConnectionError("simulado")


@pytest.fixture
def cliente(entorno_valido: dict[str, str]) -> Iterator[TestClient]:
    """Cliente con las sondas reales sustituidas por sondas sanas.

    Esta capa prueba el CONTRATO de las sondas, no la conectividad: que
    `/ready` devuelva 503 cuando algo falla, que nombre la dependencia, que se
    recupere. La conectividad real contra PostgreSQL y Redis se prueba en
    `tests/integration/`, contra servicios de verdad y sin mocks (regla dura 8).
    """
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as c:
        for nombre in list(app.state.readiness_checks):
            app.state.readiness_checks[nombre] = _sonda_sana
        yield c


def _romper(cliente: TestClient, dependencia: str) -> None:
    cliente.app.state.readiness_checks[dependencia] = _sonda_caida


def _reparar(cliente: TestClient, dependencia: str) -> None:
    cliente.app.state.readiness_checks[dependencia] = _sonda_sana


# ─────────────────────────────────────────────────────────────────────────────
# 5.1 — Sonda de vida
# ─────────────────────────────────────────────────────────────────────────────


def test_health_responde_con_exito(cliente: TestClient) -> None:
    respuesta = cliente.get("/health")
    assert respuesta.status_code == 200


def test_health_incluye_version_y_marca_temporal(cliente: TestClient) -> None:
    cuerpo = cliente.get("/health").json()
    assert cuerpo["version"]
    assert cuerpo["timestamp"]


def test_health_no_consulta_dependencias(cliente: TestClient) -> None:
    """El escenario dice: dependencia caida, la sonda de vida igual responde.

    Se verifica por comportamiento y no por tiempo: un assert sobre
    milisegundos es intermitente en CI y no prueba lo que importa.
    """
    _romper(cliente, "database")
    _romper(cliente, "redis")
    assert cliente.get("/health").status_code == 200


def test_health_es_publica(cliente: TestClient) -> None:
    """Sin cabecera de autorizacion de ningun tipo."""
    respuesta = cliente.get("/health", headers={})
    assert respuesta.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 5.2 — Sonda de disponibilidad
# ─────────────────────────────────────────────────────────────────────────────


def test_ready_disponible_cuando_todo_responde(cliente: TestClient) -> None:
    respuesta = cliente.get("/ready")
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ready"


@pytest.mark.parametrize("dependencia", ["database", "redis"])
def test_ready_no_disponible_e_identifica_cual_fallo(cliente: TestClient, dependencia: str) -> None:
    _romper(cliente, dependencia)
    respuesta = cliente.get("/ready")
    assert respuesta.status_code == 503
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "not_ready"
    assert dependencia in cuerpo["failed"]


def test_ready_no_filtra_credenciales(cliente: TestClient, entorno_valido: dict[str, str]) -> None:
    """Identificar la dependencia caida NO es motivo para volcar su URL."""
    _romper(cliente, "database")
    cuerpo = cliente.get("/ready").text
    assert entorno_valido["DATABASE_URL"] not in cuerpo
    assert "postgresql" not in cuerpo
    assert entorno_valido["S3_SECRET_KEY"] not in cuerpo


def test_ready_se_recupera_sin_reiniciar(cliente: TestClient) -> None:
    _romper(cliente, "redis")
    assert cliente.get("/ready").status_code == 503
    _reparar(cliente, "redis")
    assert cliente.get("/ready").status_code == 200


def test_ready_reporta_todas_las_caidas_no_solo_la_primera(cliente: TestClient) -> None:
    _romper(cliente, "database")
    _romper(cliente, "redis")
    fallidas = cliente.get("/ready").json()["failed"]
    assert set(fallidas) == {"database", "redis"}


# ─────────────────────────────────────────────────────────────────────────────
# 5.3 — Correlacion de peticiones
# ─────────────────────────────────────────────────────────────────────────────


def test_genera_identificador_si_no_viene(cliente: TestClient) -> None:
    respuesta = cliente.get("/health")
    assert respuesta.headers.get(CABECERA_CORRELACION)


def test_dos_peticiones_reciben_identificadores_distintos(cliente: TestClient) -> None:
    primero = cliente.get("/health").headers[CABECERA_CORRELACION]
    segundo = cliente.get("/health").headers[CABECERA_CORRELACION]
    assert primero != segundo


def test_reutiliza_el_identificador_del_cliente(cliente: TestClient) -> None:
    provisto = "abc-123-del-cliente"
    respuesta = cliente.get("/health", headers={CABECERA_CORRELACION: provisto})
    assert respuesta.headers[CABECERA_CORRELACION] == provisto


def test_el_identificador_llega_a_los_registros(
    cliente: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    provisto = "id-que-debe-aparecer-en-el-log"
    with caplog.at_level("INFO"):
        cliente.get("/health", headers={CABECERA_CORRELACION: provisto})
    assert any(provisto == getattr(r, "correlation_id", None) for r in caplog.records)


# ─────────────────────────────────────────────────────────────────────────────
# 5.4 — Gate de documentacion por ambiente
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("ambiente", ["local", "ci", "staging"])
def test_docs_disponible_fuera_de_produccion(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch, ambiente: str
) -> None:
    monkeypatch.setenv("APP_ENV", ambiente)
    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        assert c.get("/docs").status_code == 200
        assert c.get("/openapi.json").status_code == 200


def test_docs_bloqueada_en_produccion(
    entorno_valido: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    with TestClient(create_app()) as c:
        assert c.get("/docs").status_code == 404
        assert c.get("/openapi.json").status_code == 404
        assert c.get("/redoc").status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 5.8 — Manejo de errores
# ─────────────────────────────────────────────────────────────────────────────


def test_error_de_dominio_responde_problem_details(cliente: TestClient) -> None:
    from app.core.errors import DomainError

    @cliente.app.get("/_prueba/dominio")
    async def _explota() -> None:
        raise DomainError("la patente ya existe", code="patente_duplicada")

    respuesta = cliente.get("/_prueba/dominio")
    assert respuesta.status_code == 422
    assert respuesta.headers["content-type"].startswith("application/problem+json")
    cuerpo = respuesta.json()
    assert cuerpo["detail"] == "la patente ya existe"
    assert cuerpo["code"] == "patente_duplicada"


def test_el_error_lleva_el_identificador_de_correlacion(cliente: TestClient) -> None:
    """Sin esto, un error reportado por un usuario no se puede rastrear."""
    from app.core.errors import DomainError

    @cliente.app.get("/_prueba/correlacion")
    async def _explota() -> None:
        raise DomainError("algo salio mal")

    provisto = "correlacion-del-error"
    respuesta = cliente.get("/_prueba/correlacion", headers={CABECERA_CORRELACION: provisto})
    assert respuesta.json()["correlation_id"] == provisto


def test_http_exception_mantiene_el_formato(cliente: TestClient) -> None:
    respuesta = cliente.get("/ruta-que-no-existe")
    assert respuesta.status_code == 404
    assert respuesta.headers["content-type"].startswith("application/problem+json")
    assert "detail" in respuesta.json()


def test_error_de_validacion_lista_los_campos(cliente: TestClient) -> None:
    @cliente.app.post("/_prueba/validacion")
    async def _recibe(cuerpo: CuerpoDePrueba) -> dict[str, int]:
        return {"cantidad": cuerpo.cantidad}

    respuesta = cliente.post("/_prueba/validacion", json={"cantidad": "no-es-numero"})
    assert respuesta.status_code == 422
    assert respuesta.headers["content-type"].startswith("application/problem+json")
    cuerpo = respuesta.json()
    assert cuerpo["code"] == "validation_error"
    assert any(error["field"].endswith("cantidad") for error in cuerpo["errors"])


def test_el_error_de_validacion_no_devuelve_lo_que_mando_el_cliente(
    cliente: TestClient,
) -> None:
    """`errors()` de pydantic trae `input`. Podria ser una contrasena."""

    @cliente.app.post("/_prueba/sensible")
    async def _recibe(cuerpo: CuerpoDePrueba) -> dict[str, int]:
        return {"cantidad": cuerpo.cantidad}

    secreto = "Contrasena-Que-No-Debe-Volver"
    respuesta = cliente.post("/_prueba/sensible", json={"cantidad": secreto})
    assert respuesta.status_code == 422
    assert secreto not in respuesta.text
