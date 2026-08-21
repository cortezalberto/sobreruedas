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
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

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


# ── 6.2, 6.3 y 6.6 · Lo que la politica RLS hace cumplir sola ────────────────


async def test_sin_contexto_de_tenant_no_se_ve_una_sola_fila() -> None:
    """Tarea 6.2. La politica compara `tenant_id` contra `app.current_tenant`.

    Sin ese ajuste la comparacion es contra `NULL` y **no devuelve nada** — que
    es exactamente lo que tiene que pasar. El modo peligroso seria el opuesto:
    una politica que ante la falta de contexto dejara ver todo, y ahi cualquier
    consulta que se olvide del `SET LOCAL` se convierte en una fuga.

    ⚠️ SE CUENTA CON EL PROPIETARIO PRIMERO. Sin eso, este test pasaria sobre
    una base vacia sin probar absolutamente nada.
    """
    tenant, _ = await agencia_con_sucursal()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, 'existe@demo.test', 'Existe', 'manager', 'active')"
            ),
            {"id": uuid.uuid4(), "t": tenant},
        )
        hay = (
            await sesion.execute(
                text("SELECT count(*) FROM users WHERE tenant_id = :t"), {"t": tenant}
            )
        ).scalar_one()
    assert hay == 1, "el andamiaje no dejo la fila: el test no probaria nada"

    motor = create_async_engine(DSN_APLICACION)
    try:
        async with motor.connect() as conexion:
            # Sin `SET LOCAL app.current_tenant`, a proposito.
            vistas = (await conexion.execute(text("SELECT count(*) FROM users"))).scalar_one()
    finally:
        await motor.dispose()

    assert vistas == 0, f"sin contexto se vieron {vistas} filas"


async def test_crear_una_persona_atribuida_a_OTRA_agencia_se_rechaza() -> None:
    """Tarea 6.3. El `WITH CHECK` de la politica, que es la mitad que se olvida.

    `USING` filtra lo que se LEE; `WITH CHECK` valida lo que se ESCRIBE. Sin la
    segunda, un tenant no puede ver las filas de otro pero si puede CREARLE
    filas — y esas filas despues son invisibles para quien las escribio, asi que
    el error no se descubre nunca desde este lado.

    ⚠️ SE EXIGE `InsufficientPrivilegeError` Y NO `Exception` A SECAS. Un
    `pytest.raises(Exception)` pasaria tambien con un `NotNullViolation`, un
    error de tipeo en el SQL o una conexion caida — o sea, pasaria sin que la
    politica exista.
    """
    una, _ = await agencia_con_sucursal()
    otra, _ = await agencia_con_sucursal()

    async with sesion_de_tenant(una, dsn=DSN_APLICACION) as sesion:
        with pytest.raises(DBAPIError) as fallo:
            await sesion.execute(
                text(
                    "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                    "VALUES (:id, :t, 'colada@demo.test', 'Colada', 'manager', 'active')"
                ),
                {"id": uuid.uuid4(), "t": otra},
            )

    # ⚠️ SE EXIGE EL MOTIVO, no "que falle". SQLAlchemy envuelve la excepcion de
    # asyncpg, asi que `isinstance` contra `InsufficientPrivilegeError` no sirve
    # — pero exigir el texto de la politica es MAS especifico que el tipo: ese
    # mensaje solo lo produce un `WITH CHECK` incumplido, mientras que
    # `InsufficientPrivilegeError` tambien lo levanta un permiso de tabla que
    # falta. Un `pytest.raises(Exception)` a secas pasaria hasta con un error de
    # tipeo en el SQL.
    assert "row-level security policy" in str(
        fallo.value.orig
    ), f"la base rechazo por otro motivo: {fallo.value.orig}"

    async with sesion_de_propietario() as sesion:
        coladas = (
            await sesion.execute(
                text("SELECT count(*) FROM users WHERE tenant_id = :t"), {"t": otra}
            )
        ).scalar_one()
    assert coladas == 0


def test_las_dos_matrices_son_disjuntas_por_ROL() -> None:
    """Tarea 6.6 — `ADR-024` §2: "son dos matrices disjuntas, no una de cuatro
    columnas".

    ⚠️ LA SEPARACION ES DE ROLES, NO DE NOMBRES DE PERMISO, y la primera version
    de este test se equivoco justo ahi: exigia que ningun permiso apareciera en
    los dos espacios, y fallo con `tenants:read`. Ese solapamiento es correcto —
    un `manager` lee SU agencia y un `super_admin` lee CUALQUIERA. Mismo nombre,
    distinto alcance.

    Lo que §2 prohibe es poner a `super_admin` como cuarta columna junto a los
    roles de tenant: "no hay un solo endpoint donde los cuatro roles compitan".

    El espacio administrativo son las rutas `/admin/api/v1/…`, que son de C-09 y
    todavia no existen. Cuando existan, esto sigue siendo la garantia de que
    ningun rol de tenant tiene una fila en esa matriz.
    """
    from app.core.rbac import MATRIZ_DE_PLATAFORMA, MATRIZ_DE_TENANT

    assert MATRIZ_DE_TENANT, "la matriz de tenant esta vacia: el test no probaria nada"
    assert MATRIZ_DE_PLATAFORMA, "la matriz de plataforma esta vacia"

    roles_de_tenant = {str(r) for r in MATRIZ_DE_TENANT}
    roles_de_plataforma = {str(r) for r in MATRIZ_DE_PLATAFORMA}

    compartidos = roles_de_tenant & roles_de_plataforma
    assert not compartidos, f"hay roles en las dos matrices: {compartidos}"

    assert (
        "super_admin" not in roles_de_tenant
    ), "`super_admin` figura como rol de tenant, y `ADR-017` lo saco del enum a proposito"
