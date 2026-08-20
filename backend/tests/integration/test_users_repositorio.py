"""El padron de la agencia — C-05, tarea 2.6.

El filtro de borrado logico va POR DEFECTO. Es la mitad del Principio 3 que no
se ve: prohibir `db.delete()` no sirve de nada si despues las consultas
devuelven las filas muertas igual.

Sobre base real (regla dura 8).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.db.session import sesion_de_tenant
from app.modules.users.repository import UserRepository

from .soporte import DSN_APLICACION, agencia_con_sucursal, sesion_de_propietario

pytestmark = pytest.mark.integration


async def _persona(tenant: uuid.UUID, email: str, nombre: str) -> uuid.UUID:
    uid = uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, :n, 'salesperson', 'active')"
            ),
            {"id": uid, "t": tenant, "e": email, "n": nombre},
        )
    return uid


async def _dar_de_baja(uid: uuid.UUID) -> None:
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text("UPDATE users SET deleted_at = now() WHERE id = :id"), {"id": uid}
        )


async def test_una_persona_dada_de_baja_no_aparece_en_el_listado_ordinario(
    base_migrada: None,
) -> None:
    tenant, _ = await agencia_con_sucursal()
    await _persona(tenant, "queda@demo.test", "Queda Adentro")
    se_fue = await _persona(tenant, "sefue@demo.test", "Se Fue")
    await _dar_de_baja(se_fue)

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        nombres = [u.full_name for u in await UserRepository(sesion, tenant).listar()]

    assert nombres == ["Queda Adentro"]


async def test_pedirlas_a_proposito_las_devuelve(base_migrada: None) -> None:
    """El contrapeso: si el repositorio nunca devolviera a las dadas de baja, el
    test de arriba pasaria igual con un `WHERE false`."""
    tenant, _ = await agencia_con_sucursal()
    await _persona(tenant, "queda@demo.test", "Queda Adentro")
    se_fue = await _persona(tenant, "sefue@demo.test", "Se Fue")
    await _dar_de_baja(se_fue)

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        nombres = [
            u.full_name
            for u in await UserRepository(sesion, tenant).listar(incluir_dadas_de_baja=True)
        ]

    assert nombres == ["Queda Adentro", "Se Fue"]


async def test_el_listado_no_cruza_agencias(base_migrada: None) -> None:
    """La tercera capa de la regla dura 1: el filtro EXPLICITO.

    La politica RLS ya acota, y el `WHERE tenant_id` se escribe igual. Este test
    no distingue cual de las dos actuo —a proposito: lo que importa es que el
    resultado sea el mismo aunque una falle—.
    """
    una, _ = await agencia_con_sucursal()
    otra, _ = await agencia_con_sucursal()
    await _persona(una, "propia@demo.test", "De La Una")
    await _persona(otra, "ajena@demo.test", "De La Otra")

    async with sesion_de_tenant(una, dsn=DSN_APLICACION) as sesion:
        nombres = [u.full_name for u in await UserRepository(sesion, una).listar()]

    assert nombres == ["De La Una"]
