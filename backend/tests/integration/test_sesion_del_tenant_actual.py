"""El puente entre el token y la base — `db/dependencias.py`.

ES EL TEST DE LA REGLA DURA 1 EN SU FORMA MAS DIRECTA
──────────────────────────────────────────────────────
Todo lo que se probo hasta ahora sobre aislamiento fue a nivel de SESION: que la
politica RLS acote, que sin contexto no haya filas. Esto prueba el eslabon que
faltaba y que es donde se cometen los errores de verdad: **que el tenant que
termina en la base sea el del TOKEN**, y no uno que vino por la ruta, el cuerpo o
una cabecera.

Se monta una app de prueba con endpoints que reciben `SesionDeTenant`, se firman
tokens de dos tenants distintos, y se verifica contra PostgreSQL real.

Sin mocks de base de datos (regla dura 8). Se corre con:

    docker compose run --rm backend pytest -m integration
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import auth
from app.db.dependencias import SesionDeTenant
from app.main import create_app

from ..emisor_de_tokens import EmisorDePrueba
from .soporte import DSN_APLICACION, reponer_entorno

pytestmark = pytest.mark.integration


@pytest.fixture
def proveedor() -> EmisorDePrueba:
    return EmisorDePrueba()


@pytest.fixture
def cliente(
    monkeypatch: pytest.MonkeyPatch, proveedor: EmisorDePrueba, base_migrada: None
) -> Iterator[TestClient]:
    """App real con dos endpoints de prueba, contra la base de verdad.

    Se sustituyen las CLAVES y el EMISOR del proveedor de identidad, no la
    validacion: lo que se ejercita es el camino completo —cabecera, firma,
    claims, contexto en PostgreSQL—. Sustituir `validar_token` probaria el mock.
    """
    reponer_entorno(monkeypatch, dsn=DSN_APLICACION)

    async def traer() -> dict[str, Any]:
        return proveedor.jwks

    monkeypatch.setattr(
        auth, "claves_del_proveedor", lambda: auth.ClavesDelProveedor(url="x", traer=traer)
    )
    monkeypatch.setattr(auth, "emisor_esperado", lambda: proveedor.emisor)

    app = create_app()

    @app.get("/_prueba/contexto")
    async def _contexto(sesion: SesionDeTenant) -> dict[str, str | None]:
        """Devuelve el tenant que PostgreSQL tiene puesto en la transaccion."""
        puesto = await sesion.scalar(text("SELECT current_setting('app.current_tenant', true)"))
        return {"tenant_en_la_base": puesto}

    @app.get("/_prueba/contexto/{tenant_del_path}")
    async def _contexto_con_path(
        tenant_del_path: uuid.UUID, sesion: SesionDeTenant
    ) -> dict[str, str | None]:
        """El endpoint recibe un tenant por la ruta Y una sesion.

        Existe para probar que el de la ruta NO influye. Es el error que la
        regla dura 1 previene, escrito a proposito.
        """
        puesto = await sesion.scalar(text("SELECT current_setting('app.current_tenant', true)"))
        return {"tenant_en_la_base": puesto}

    with TestClient(app) as c:
        yield c


def _cabecera(proveedor: EmisorDePrueba, tenant: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {proveedor.firmar(tenant_id=tenant)}"}


# ── Lo que la dependency garantiza ──────────────────────────────────────────


def test_el_contexto_de_la_base_es_el_tenant_del_token(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """El eslabon completo: claim → dependency → `SET LOCAL` → PostgreSQL."""
    tenant = uuid.uuid4()

    respuesta = cliente.get("/_prueba/contexto", headers=_cabecera(proveedor, tenant))

    assert respuesta.status_code == 200
    assert respuesta.json()["tenant_en_la_base"] == str(tenant)


def test_dos_tokens_distintos_abren_contextos_distintos(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Si el contexto se filtrara entre peticiones, este test lo veria.

    Es el modo de fallar que un `ContextVar` mal manejado produce: la segunda
    peticion hereda el tenant de la primera y devuelve datos ajenos.
    """
    primero, segundo = uuid.uuid4(), uuid.uuid4()

    uno = cliente.get("/_prueba/contexto", headers=_cabecera(proveedor, primero))
    dos = cliente.get("/_prueba/contexto", headers=_cabecera(proveedor, segundo))

    assert uno.json()["tenant_en_la_base"] == str(primero)
    assert dos.json()["tenant_en_la_base"] == str(segundo)


def test_el_tenant_de_la_ruta_no_influye(cliente: TestClient, proveedor: EmisorDePrueba) -> None:
    """EL TEST QUE JUSTIFICA QUE ESTA DEPENDENCY EXISTA.

    El endpoint recibe un `tenant_id` por la ruta y una sesion. La sesion se
    acota al del TOKEN, y el de la ruta se ignora — no porque el endpoint se
    acuerde de ignorarlo, sino porque la dependency nunca se lo pregunta.
    """
    del_token = uuid.uuid4()
    otro = uuid.uuid4()

    respuesta = cliente.get(f"/_prueba/contexto/{otro}", headers=_cabecera(proveedor, del_token))

    assert respuesta.json()["tenant_en_la_base"] == str(del_token)
    assert respuesta.json()["tenant_en_la_base"] != str(otro)


# ── Sin identidad no hay sesion ─────────────────────────────────────────────


def test_sin_token_no_se_abre_ninguna_sesion(cliente: TestClient) -> None:
    """401 y no 500.

    Importa el codigo: la dependency de identidad corre ANTES de tocar la base,
    asi que una peticion sin token no llega a abrir una transaccion. Un 500
    significaria que se intento consultar y fallo despues.
    """
    assert cliente.get("/_prueba/contexto").status_code == 401


def test_un_token_de_otro_emisor_no_abre_sesion(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Firmado con otras claves. La validacion es real, no una convencion."""
    impostor = EmisorDePrueba()

    respuesta = cliente.get(
        "/_prueba/contexto",
        headers={"Authorization": f"Bearer {impostor.firmar(tenant_id=uuid.uuid4())}"},
    )

    assert respuesta.status_code == 401
