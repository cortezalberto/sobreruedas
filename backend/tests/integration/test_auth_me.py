"""`GET /api/v1/auth/me` y el aislamiento de identidad — C-05, bloques 5 y 6.

`T-027` es quality gate BLOQUEANTE: sin estos tests, `users` es una tabla mas
con `tenant_id` y nadie verifico que la agencia A no vea las personas de la B.

Sobre base real (regla dura 8).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import auth
from app.main import create_app

from ..emisor_de_tokens import EmisorDePrueba
from .soporte import (
    DSN_APLICACION,
    agencia_con_sucursal,
    reponer_entorno,
    sesion_de_propietario,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def proveedor() -> EmisorDePrueba:
    return EmisorDePrueba()


@pytest.fixture
def cliente(
    monkeypatch: pytest.MonkeyPatch, proveedor: EmisorDePrueba, base_migrada: None
) -> Iterator[TestClient]:
    reponer_entorno(monkeypatch, dsn=DSN_APLICACION)

    async def traer() -> dict[str, Any]:
        return proveedor.jwks

    monkeypatch.setattr(
        auth, "claves_del_proveedor", lambda: auth.ClavesDelProveedor(url="x", traer=traer)
    )
    monkeypatch.setattr(auth, "emisor_esperado", lambda: proveedor.emisor)

    with TestClient(create_app()) as c:
        yield c


def _cabecera(
    proveedor: EmisorDePrueba,
    tenant: uuid.UUID,
    sub: uuid.UUID,
    *,
    role: str = "manager",
) -> dict[str, str]:
    return {
        "Authorization": (f"Bearer {proveedor.firmar(tenant_id=tenant, sub=str(sub), role=role)}")
    }


async def _persona(
    tenant: uuid.UUID,
    *,
    sub: uuid.UUID | None = None,
    email: str = "persona@demo.test",
    nombre: str = "Persona Demo",
    rol: str = "manager",
    sucursal: uuid.UUID | None = None,
) -> uuid.UUID:
    """Una fila en el espejo. Andamiaje: la invitacion es del bloque 4."""
    uid = sub or uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, :n, :r, 'active')"
            ),
            {"id": uid, "t": tenant, "e": email, "n": nombre, "r": rol},
        )
        if sucursal is not None:
            await sesion.execute(
                text(
                    "INSERT INTO user_branches (user_id, branch_id, tenant_id, is_primary) "
                    "VALUES (:u, :b, :t, true)"
                ),
                {"u": uid, "b": sucursal, "t": tenant},
            )
    return uid


# ── 5.1 a 5.4 · El endpoint ──────────────────────────────────────────────────


async def test_devuelve_lo_que_el_token_no_dice(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """`design.md` `D-4`: nombre, estado y sucursales.

    El `sub`, el `tenant_id` y el `role` viajan igual — no por redundancia, sino
    para que el frontend tenga UNA fuente y no tenga que decodificar el JWT.
    """
    tenant, sucursal = await agencia_con_sucursal()
    sub = await _persona(tenant, nombre="Gabriela Gerente", sucursal=sucursal)

    respuesta = cliente.get("/api/v1/auth/me", headers=_cabecera(proveedor, tenant, sub))

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["full_name"] == "Gabriela Gerente"
    assert cuerpo["status"] == "active"
    assert cuerpo["id"] == str(sub)
    assert cuerpo["tenant_id"] == str(tenant)
    assert [s["name"] for s in cuerpo["branches"]] == ["Casa central"]
    assert cuerpo["branches"][0]["is_primary"] is True


async def test_no_falla_con_cero_sucursales(cliente: TestClient, proveedor: EmisorDePrueba) -> None:
    """Tarea 5.4. Una persona recien invitada no tiene ninguna, y eso NO es un
    error — devolver 500 ahi convertiria el estado normal de un usuario nuevo en
    una caida."""
    tenant, _ = await agencia_con_sucursal()
    sub = await _persona(tenant)

    respuesta = cliente.get("/api/v1/auth/me", headers=_cabecera(proveedor, tenant, sub))

    assert respuesta.status_code == 200
    assert respuesta.json()["branches"] == []


async def test_la_respuesta_no_trae_nada_de_mfa_ni_de_credenciales(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """`D-2`. Ni siquiera como `null`: la clave no existe."""
    tenant, _ = await agencia_con_sucursal()
    sub = await _persona(tenant)

    cuerpo = cliente.get("/api/v1/auth/me", headers=_cabecera(proveedor, tenant, sub)).json()

    assert {"mfa_enabled", "mfa_secret", "password_hash"}.isdisjoint(cuerpo)


def test_sin_token_es_401_y_no_403(cliente: TestClient) -> None:
    """Tarea 5.3. La distincion que `errors.py` justifica: 401 se arregla
    presentando un token; 403 no se arregla reintentando."""
    respuesta = cliente.get("/api/v1/auth/me")
    assert respuesta.status_code == 401
    assert respuesta.json()["code"] == "not_authenticated"


async def test_no_hay_forma_de_pedir_la_identidad_de_otro(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Tarea 5.2, y el motivo de que el endpoint no reciba parametros.

    Se prueban las tres formas en que alguien lo intentaria: por query string,
    por path y por cabecera. Ninguna devuelve al otro — las dos primeras porque
    el endpoint las ignora o no existe, la tercera porque la identidad sale del
    token y de ningun otro lado.
    """
    tenant, _ = await agencia_con_sucursal()
    yo = await _persona(tenant, email="yo@demo.test", nombre="Yo Mismo")
    otro = await _persona(tenant, email="otro@demo.test", nombre="Otro Distinto")

    cabecera = _cabecera(proveedor, tenant, yo)

    por_query = cliente.get(f"/api/v1/auth/me?user_id={otro}", headers=cabecera)
    assert por_query.status_code == 200
    assert por_query.json()["full_name"] == "Yo Mismo"

    assert cliente.get(f"/api/v1/auth/{otro}", headers=cabecera).status_code == 404

    por_cabecera = cliente.get("/api/v1/auth/me", headers={**cabecera, "X-User-Id": str(otro)})
    assert por_cabecera.json()["full_name"] == "Yo Mismo"


async def test_un_token_valido_sin_espejo_local_es_404_y_no_500(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Existe en Keycloak y todavia no acepto la invitacion.

    404 y no 403: no es una cuestion de permisos, y mandarlo a pedir acceso lo
    mandaria por el camino equivocado.
    """
    tenant, _ = await agencia_con_sucursal()
    respuesta = cliente.get("/api/v1/auth/me", headers=_cabecera(proveedor, tenant, uuid.uuid4()))
    assert respuesta.status_code == 404


# ── Bloque 6 · `T-027`, el gate bloqueante ───────────────────────────────────


async def test_el_token_de_una_agencia_no_alcanza_a_la_persona_de_otra(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """El escenario que `T-027` existe para cubrir.

    Se pide el perfil con el `sub` REAL de alguien de la otra agencia, montado
    en un token de la propia. El aislamiento tiene que responder 404 —no existe
    para vos— y no filtrar ni el nombre.
    """
    una, _ = await agencia_con_sucursal()
    otra, _ = await agencia_con_sucursal()

    ajeno = await _persona(otra, email="ajeno@demo.test", nombre="Persona Ajena")
    await _persona(una, email="propio@demo.test")

    respuesta = cliente.get("/api/v1/auth/me", headers=_cabecera(proveedor, una, ajeno))

    assert respuesta.status_code == 404
    assert "Ajena" not in respuesta.text


async def test_los_tests_de_aislamiento_no_son_vacios(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Tarea 6.4, y no es ceremonia.

    Un test que afirma "no ve nada" pasa igual si la tabla esta vacia. Aca se
    cuenta que las filas EXISTEN antes de afirmar que no se alcanzan — sin esto,
    los dos tests de arriba serian verdes sobre una base sin datos.
    """
    una, _ = await agencia_con_sucursal()
    otra, _ = await agencia_con_sucursal()
    await _persona(una, email="a@demo.test")
    await _persona(otra, email="b@demo.test")

    async with sesion_de_propietario() as sesion:
        de_una = await sesion.scalar(
            text("SELECT count(*) FROM users WHERE tenant_id = :t"), {"t": una}
        )
        de_otra = await sesion.scalar(
            text("SELECT count(*) FROM users WHERE tenant_id = :t"), {"t": otra}
        )

    assert de_una == 1
    assert de_otra == 1


async def test_la_tabla_de_union_aisla_igual_que_las_dos_que_une(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Tarea 6.5. Es el agujero clasico: las dos puntas protegidas y el vinculo
    no. Se comprueba que el perfil no lista la sucursal de la otra agencia."""
    una, sucursal_de_una = await agencia_con_sucursal()
    otra, sucursal_de_otra = await agencia_con_sucursal()

    yo = await _persona(una, email="yo@demo.test", sucursal=sucursal_de_una)
    await _persona(otra, email="vecino@demo.test", sucursal=sucursal_de_otra)

    cuerpo = cliente.get("/api/v1/auth/me", headers=_cabecera(proveedor, una, yo)).json()

    asignadas = {s["id"] for s in cuerpo["branches"]}
    assert asignadas == {str(sucursal_de_una)}
    assert str(sucursal_de_otra) not in asignadas


async def test_los_tres_roles_de_tenant_alcanzan_su_propio_perfil(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """`ADR-024` §6: `auth:read_me` es `self` para los tres.

    Contrapeso de los tests de arriba: si el endpoint denegara a todos, aquellos
    pasarian igual y no probarian aislamiento sino una puerta cerrada.
    """
    tenant, _ = await agencia_con_sucursal()

    for rol in ("manager", "salesperson", "admin_staff"):
        sub = await _persona(tenant, email=f"{rol}@demo.test", rol=rol)
        respuesta = cliente.get(
            "/api/v1/auth/me", headers=_cabecera(proveedor, tenant, sub, role=rol)
        )
        assert respuesta.status_code == 200, f"{rol}: {respuesta.text}"
        assert respuesta.json()["role"] == rol
