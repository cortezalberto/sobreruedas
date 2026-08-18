"""La dependency de identidad y las rutas exentas — C-02, tareas 3.4 y 3.6.

Acá se prueba el borde HTTP: que un endpoint protegido rechace sin token, que
acepte con uno bueno, y que la lista de rutas que se atienden sin autenticacion
sea **explicita** y nadie pueda agrandarla por descuido.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core import auth
from app.core.auth import (
    RUTAS_EXENTAS,
    NoAutenticado,
    SujetoActual,
    get_current_user,
    token_de_la_cabecera,
)
from app.main import create_app

from ..emisor_de_tokens import EmisorDePrueba


@pytest.fixture
def proveedor() -> EmisorDePrueba:
    return EmisorDePrueba()


@pytest.fixture
def cliente(
    entorno_valido: dict[str, str], proveedor: EmisorDePrueba, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """App real, con el proveedor de identidad sustituido por el de prueba.

    Se sustituyen las CLAVES y el EMISOR, no la validacion: lo que se ejercita
    es el camino completo —cabecera, token, firma, claims—, con el unico cambio
    de quien firma. Sustituir `validar_token` probaria el mock.
    """
    from app.config import get_settings

    async def traer() -> dict[str, Any]:
        return proveedor.jwks

    claves = auth.ClavesDelProveedor(url="http://no-se-usa", traer=traer)
    monkeypatch.setattr(auth, "claves_del_proveedor", lambda: claves)
    monkeypatch.setattr(auth, "emisor_esperado", lambda: proveedor.emisor)

    get_settings.cache_clear()
    app = create_app()

    @app.get("/_prueba/protegida")
    async def _protegida(sujeto: SujetoActual) -> dict[str, str]:
        return {"user_id": sujeto.user_id, "tenant_id": str(sujeto.tenant_id), "role": sujeto.role}

    with TestClient(app) as c:
        yield c


# ── 3.4 · La dependency ──────────────────────────────────────────────────────


def test_con_un_token_valido_la_peticion_se_atiende(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    tenant = uuid.uuid4()
    token = proveedor.firmar(sub="u-1", tenant_id=tenant, role="manager", receptor="backend")

    respuesta = cliente.get("/_prueba/protegida", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "user_id": "u-1",
        "tenant_id": str(tenant),
        "role": "manager",
    }


def test_sin_token_la_peticion_se_rechaza_con_401(cliente: TestClient) -> None:
    respuesta = cliente.get("/_prueba/protegida")

    assert respuesta.status_code == 401
    assert respuesta.headers["content-type"].startswith("application/problem+json")
    cuerpo = respuesta.json()
    assert cuerpo["code"] == "not_authenticated"
    assert "correlation_id" in cuerpo


def test_el_401_no_devuelve_el_token(cliente: TestClient, proveedor: EmisorDePrueba) -> None:
    """Un token en la respuesta termina en un log de acceso, y sigue sirviendo."""
    from datetime import timedelta

    token = proveedor.firmar(vence_en=timedelta(minutes=-1), receptor="backend")

    respuesta = cliente.get("/_prueba/protegida", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 401
    assert token not in respuesta.text


@pytest.mark.parametrize(
    ("cabecera", "por_que"),
    [
        ("", "vacia"),
        ("el-token-pelado", "sin esquema"),
        ("Basic dXN1YXJpbzpjbGF2ZQ==", "esquema Basic: esta API no recibe credenciales"),
        ("Bearer", "esquema sin token"),
        ("Bearer    ", "esquema con espacios"),
    ],
)
def test_una_cabecera_mal_formada_se_rechaza(cabecera: str, por_que: str) -> None:
    with pytest.raises(NoAutenticado):
        token_de_la_cabecera(cabecera or None)


def test_el_esquema_no_distingue_mayusculas(proveedor: EmisorDePrueba) -> None:
    """`RFC 7235` pide comparar el esquema sin distinguir mayusculas."""
    assert token_de_la_cabecera("bearer abc") == "abc"
    assert token_de_la_cabecera("BEARER abc") == "abc"


# ── 3.6 · Rutas exentas ──────────────────────────────────────────────────────


def rutas_desprotegidas(app: FastAPI) -> set[str]:
    """Rutas que no exigen identidad y no estan declaradas exentas.

    Se mira la cadena de dependencias REAL de cada ruta, no una convencion de
    nombres: lo que importa es si FastAPI va a ejecutar `get_current_user` antes
    del endpoint, no como se llame la funcion.
    """
    desprotegidas: set[str] = set()

    for ruta in app.routes:
        if not isinstance(ruta, APIRoute) or ruta.path in RUTAS_EXENTAS:
            continue
        if not _exige_identidad(ruta):
            desprotegidas.add(ruta.path)

    return desprotegidas


def _exige_identidad(ruta: APIRoute) -> bool:
    pendientes = list(ruta.dependant.dependencies)
    while pendientes:
        dependencia = pendientes.pop()
        if dependencia.call is get_current_user:
            return True
        pendientes.extend(dependencia.dependencies)
    return False


def test_ninguna_ruta_de_datos_se_atiende_sin_token(cliente: TestClient) -> None:
    """La regla, verificada sobre la aplicacion de verdad.

    Hoy la unica ruta protegida es la de prueba que monta el fixture. Cuando
    empiecen a entrar los routers de dominio en C-05, este test es lo que va a
    avisar si alguno queda abierto.
    """
    assert rutas_desprotegidas(cast(FastAPI, cliente.app)) == set()


def test_las_sondas_responden_sin_token(cliente: TestClient) -> None:
    """Contrapeso: si todo exigiera token, Kubernetes no podria sondear nada.

    Se afirma que NO dan 401, y no que den 200. Son dos cosas distintas y solo
    una es de este archivo: `/ready` consulta PostgreSQL y Redis de verdad, asi
    que su codigo depende de si estan arriba. Exigir 200 aca ataria un test de
    autenticacion al estado de la infraestructura, y lo volveria intermitente
    por un motivo que no tiene nada que ver con lo que prueba.

    Que las sondas ademas respondan bien lo cubre `test_app_health.py`.
    """
    assert cliente.get("/health").status_code == 200  # no toca dependencias
    assert cliente.get("/ready").status_code != 401


def test_el_detector_encuentra_una_ruta_abierta() -> None:
    """Probar el detector, no solo usarlo.

    El test de arriba pasa hoy. Tambien pasaria si `_exige_identidad` devolviera
    `True` siempre — que es como un control se apaga sin que nadie se entere.
    """
    app = FastAPI()

    @app.get("/vehiculos")
    async def _abierta() -> dict[str, str]:
        return {}

    assert rutas_desprotegidas(app) == {"/vehiculos"}


def test_el_detector_no_marca_una_ruta_protegida() -> None:
    app = FastAPI()

    @app.get("/vehiculos")
    async def _protegida(sujeto: SujetoActual) -> dict[str, str]:
        return {}

    assert rutas_desprotegidas(app) == set()


def test_las_exentas_son_solo_sondas_y_documentacion() -> None:
    """El limite duro: ninguna ruta de datos de tenant puede estar exenta.

    No se puede verificar por analisis que una ruta "exponga datos de tenant",
    asi que se acota por el otro lado: la lista es corta, cerrada, y este test
    falla si alguien le agrega algo que no sea una sonda o documentacion. El
    dia que entre un webhook, se agrega aca **y** con su verificacion de firma.
    """
    permitidas = {"/health", "/ready", "/docs", "/redoc", "/openapi.json"}

    assert RUTAS_EXENTAS == permitidas, (
        "cambio la lista de rutas exentas. Si es un webhook, tiene que verificar "
        "la firma del emisor por su propio mecanismo; si expone datos de un "
        "tenant, no puede estar exento (spec `platform/identity`)"
    )
