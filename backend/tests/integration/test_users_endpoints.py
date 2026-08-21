"""`/api/v1/users` — C-05, tareas 5.9 y 5.11. Sobre base real (regla dura 8).

CADA TEST DE ACA ES UNA CELDA DE `ADR-024` §6
───────────────────────────────────────────────
No se prueba "que el endpoint ande": se prueba que la matriz este transcripta
sin interpretar. Un permiso mal copiado no rompe nada visible — deja a un
vendedor viendo el telefono de todos, o editando a un compañero, y eso no se
nota hasta que alguien lo usa.

    manager        users:read/invite/update/deactivate/assign_branches   ALL
    salesperson    users:read (campos publicos) · users:update           SELF
    admin_staff    idem salesperson
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import auth
from app.main import create_app
from app.modules.users.router import cliente_de_keycloak

from ..emisor_de_tokens import EmisorDePrueba
from .soporte import (
    DSN_APLICACION,
    agencia_con_sucursal,
    reponer_entorno,
    sesion_de_propietario,
)

pytestmark = pytest.mark.integration


class KeycloakFalso:
    """No mockea la base —eso lo prohibe la regla dura 8— sino el sistema de
    identidad, que es externo y del que aca solo importa que se lo llame."""

    def __init__(self) -> None:
        self.deshabilitados: list[str] = []

    async def crear_usuario(
        self, *, email: str, nombre: str, tenant_id: uuid.UUID, rol: str
    ) -> str:
        return str(uuid.uuid4())

    async def deshabilitar(self, sub: str) -> None:
        self.deshabilitados.append(sub)

    async def rehabilitar(self, sub: str) -> None: ...

    async def pedir_que_fije_contrasenia(self, sub: str) -> None: ...

    async def cerrar_sesion(self, sub: str) -> None: ...


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
        app = cast(FastAPI, c.app)
        app.dependency_overrides[cliente_de_keycloak] = lambda: KeycloakFalso()
        yield c
        app.dependency_overrides.clear()


def _cabecera(
    proveedor: EmisorDePrueba, tenant: uuid.UUID, sub: uuid.UUID, *, role: str = "manager"
) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {proveedor.firmar(tenant_id=tenant, sub=str(sub), role=role)}"
    }


async def _persona(
    tenant: uuid.UUID, *, email: str = "p@demo.test", rol: str = "manager"
) -> uuid.UUID:
    uid = uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Persona Demo', :r, 'active')"
            ),
            {"id": uid, "t": tenant, "e": email, "r": rol},
        )
    return uid


# ── 5.9 · El padron ─────────────────────────────────────────────────────────


async def test_un_manager_ve_el_padron_entero(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    tenant, _ = await agencia_con_sucursal(plan="pro")
    jefa = await _persona(tenant, email="jefa@demo.test")
    await _persona(tenant, email="vende@demo.test", rol="salesperson")

    respuesta = cliente.get("/api/v1/users", headers=_cabecera(proveedor, tenant, jefa))

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert len(cuerpo) == 2
    assert all("email" in fila for fila in cuerpo)
    assert all("status" in fila for fila in cuerpo)


async def test_un_vendedor_ve_el_padron_SIN_email_ni_telefono_ni_estado(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """`CAMPOS_PUBLICOS_DE_USUARIO` = `[id, nombre, rol, sucursales]`.

    Un vendedor necesita saber a quien asignarle un lead; no necesita el
    telefono de todos ni quien esta suspendido. Es la misma decision que
    `RN-ST-12` toma sobre el costo de un vehiculo, aplicada a las personas.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    await _persona(tenant, email="jefa@demo.test")
    vende = await _persona(tenant, email="vende@demo.test", rol="salesperson")

    respuesta = cliente.get(
        "/api/v1/users", headers=_cabecera(proveedor, tenant, vende, role="salesperson")
    )

    assert respuesta.status_code == 200, respuesta.text
    for fila in respuesta.json():
        assert set(fila) == {"id", "full_name", "role", "branches"}, fila


async def test_el_padron_no_cruza_agencias(cliente: TestClient, proveedor: EmisorDePrueba) -> None:
    """El contrapeso: sin esto, el test de arriba pasaria sobre una base vacia."""
    una, _ = await agencia_con_sucursal(plan="pro")
    otra, _ = await agencia_con_sucursal(plan="pro")

    jefa = await _persona(una, email="de-una@demo.test")
    await _persona(otra, email="de-otra@demo.test")
    await _persona(otra, email="otra-mas@demo.test")

    respuesta = cliente.get("/api/v1/users", headers=_cabecera(proveedor, una, jefa))

    assert respuesta.status_code == 200, respuesta.text
    assert [f["id"] for f in respuesta.json()] == [str(jefa)]


# ── 5.11 · Las celdas de la matriz ──────────────────────────────────────────


async def test_un_vendedor_no_puede_invitar(cliente: TestClient, proveedor: EmisorDePrueba) -> None:
    """`users:invite` solo la tiene `manager`.

    403 y no 404: el recurso existe, lo que falta es el permiso — y el mensaje
    tiene que mandar a pedirselo a alguien, no a buscar una ruta que si existe.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    vende = await _persona(tenant, email="vende@demo.test", rol="salesperson")

    respuesta = cliente.post(
        "/api/v1/users/invitations",
        json={"email": "nueva@demo.test", "full_name": "Nueva", "role": "salesperson"},
        headers=_cabecera(proveedor, tenant, vende, role="salesperson"),
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "insufficient_permission"


async def test_un_manager_invita_y_la_persona_nace_invited(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    tenant, _ = await agencia_con_sucursal(plan="pro")
    jefa = await _persona(tenant, email="jefa@demo.test")

    respuesta = cliente.post(
        "/api/v1/users/invitations",
        json={"email": "nueva@demo.test", "full_name": "Nueva Persona", "role": "salesperson"},
        headers=_cabecera(proveedor, tenant, jefa),
    )

    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "invited"
    assert cuerpo["role"] == "salesperson"


async def test_invitar_no_acepta_tenant_id_en_el_cuerpo(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Regla dura 1. El `tenant_id` se deriva del token, NUNCA del cuerpo.

    Aceptarlo le daria a quien invita la posibilidad de invitar a otra agencia.
    El schema es `extra="forbid"`, asi que el rechazo es 422 y no un silencio.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    jefa = await _persona(tenant, email="jefa@demo.test")

    respuesta = cliente.post(
        "/api/v1/users/invitations",
        json={
            "email": "nueva@demo.test",
            "full_name": "Nueva",
            "role": "salesperson",
            "tenant_id": str(uuid.uuid4()),
        },
        headers=_cabecera(proveedor, tenant, jefa),
    )

    assert respuesta.status_code == 422


async def test_invitar_no_acepta_una_contrasenia(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """`ADR-026`: la aplicacion nunca maneja contraseñas, tampoco al invitar."""
    tenant, _ = await agencia_con_sucursal(plan="pro")
    jefa = await _persona(tenant, email="jefa@demo.test")

    respuesta = cliente.post(
        "/api/v1/users/invitations",
        json={
            "email": "nueva@demo.test",
            "full_name": "Nueva",
            "role": "salesperson",
            "password": "bienvenido123",
        },
        headers=_cabecera(proveedor, tenant, jefa),
    )

    assert respuesta.status_code == 422


async def test_un_vendedor_se_edita_a_si_mismo_pero_no_a_otro(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """El alcance `SELF` de `users:update`, que es lo que separa las dos cosas.

    Sin `verificar_alcance`, el permiso alcanzaria para editar a cualquiera de
    la agencia — y el sintoma seria que un vendedor le cambia el nombre a otro,
    que nadie mira hasta que pasa.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    vende = await _persona(tenant, email="vende@demo.test", rol="salesperson")
    otra = await _persona(tenant, email="otra@demo.test", rol="salesperson")
    cabecera = _cabecera(proveedor, tenant, vende, role="salesperson")

    propia = cliente.patch(
        f"/api/v1/users/{vende}", json={"full_name": "Me Cambio El Nombre"}, headers=cabecera
    )
    assert propia.status_code == 200, propia.text
    assert propia.json()["full_name"] == "Me Cambio El Nombre"

    ajena = cliente.patch(
        f"/api/v1/users/{otra}", json={"full_name": "Le Cambio El Nombre"}, headers=cabecera
    )
    assert ajena.status_code == 403
    assert ajena.json()["code"] == "out_of_scope"


async def test_nadie_se_cambia_el_rol_a_si_mismo(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """La escalada de privilegios mas obvia, y por eso tiene test propio.

    `role` no esta en `UsuarioEditarPerfil` y el schema es `extra="forbid"`: no
    hay que acordarse de filtrarlo en ningun lado, porque no entra.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    vende = await _persona(tenant, email="vende@demo.test", rol="salesperson")

    respuesta = cliente.patch(
        f"/api/v1/users/{vende}",
        json={"role": "manager"},
        headers=_cabecera(proveedor, tenant, vende, role="salesperson"),
    )

    assert respuesta.status_code == 422


async def test_solo_un_manager_da_de_baja_y_asigna_sucursales(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    tenant, sucursal = await agencia_con_sucursal(plan="pro")
    jefa = await _persona(tenant, email="jefa@demo.test")
    vende = await _persona(tenant, email="vende@demo.test", rol="salesperson")
    de_vendedor = _cabecera(proveedor, tenant, vende, role="salesperson")

    assert cliente.delete(f"/api/v1/users/{vende}", headers=de_vendedor).status_code == 403
    assert (
        cliente.put(
            f"/api/v1/users/{vende}/branches",
            json={"branches": [{"branch_id": str(sucursal), "is_primary": True}]},
            headers=de_vendedor,
        ).status_code
        == 403
    )

    de_jefa = _cabecera(proveedor, tenant, jefa)
    assert (
        cliente.put(
            f"/api/v1/users/{vende}/branches",
            json={"branches": [{"branch_id": str(sucursal), "is_primary": True}]},
            headers=de_jefa,
        ).status_code
        == 204
    )
    assert cliente.delete(f"/api/v1/users/{vende}", headers=de_jefa).status_code == 204


async def test_ver_a_una_persona_y_el_404_de_la_que_no_existe(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """`GET /users/{id}`. El 404 es el mismo para "no existe" y "no es tuya".

    Distinguirlos le confirmaria a un tenant que cierto id existe en otra
    agencia — una fuga por el codigo de estado, sin devolver un solo dato.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    otra, _ = await agencia_con_sucursal(plan="pro")
    jefa = await _persona(tenant, email="jefa@demo.test")
    ajena = await _persona(otra, email="ajena@demo.test")
    cabecera = _cabecera(proveedor, tenant, jefa)

    propia = cliente.get(f"/api/v1/users/{jefa}", headers=cabecera)
    assert propia.status_code == 200, propia.text
    assert propia.json()["email"] == "jefa@demo.test"

    inexistente = cliente.get(f"/api/v1/users/{uuid.uuid4()}", headers=cabecera)
    de_otra_agencia = cliente.get(f"/api/v1/users/{ajena}", headers=cabecera)

    assert inexistente.status_code == 404
    assert de_otra_agencia.status_code == 404
    assert inexistente.json()["code"] == de_otra_agencia.json()["code"] == "user_not_found"


async def test_suspender_por_el_endpoint_no_da_de_baja(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    """`D-6`: suspender y dar de baja son dos cosas, y comparten victima.

    Por eso son dos endpoints distintos y no un `PATCH` con un `status`: un
    cliente que se equivoca de valor no debe poder dar de baja creyendo que
    suspende.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    jefa = await _persona(tenant, email="jefa@demo.test")
    vende = await _persona(tenant, email="vende@demo.test", rol="salesperson")

    respuesta = cliente.post(
        f"/api/v1/users/{vende}/deactivation", headers=_cabecera(proveedor, tenant, jefa)
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["status"] == "inactive"

    async with sesion_de_propietario() as sesion:
        baja = (
            await sesion.execute(text("SELECT deleted_at FROM users WHERE id = :id"), {"id": vende})
        ).scalar_one()
    assert baja is None, "suspender dio de baja"


async def test_editar_a_alguien_que_no_existe_da_404(
    cliente: TestClient, proveedor: EmisorDePrueba
) -> None:
    tenant, _ = await agencia_con_sucursal(plan="pro")
    jefa = await _persona(tenant, email="jefa@demo.test")

    respuesta = cliente.patch(
        f"/api/v1/users/{uuid.uuid4()}",
        json={"full_name": "Nadie"},
        headers=_cabecera(proveedor, tenant, jefa),
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "user_not_found"
