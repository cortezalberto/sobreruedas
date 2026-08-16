"""El rol de conexion de la aplicacion no puede eludir el aislamiento — ADR-020.

ESTE ARCHIVO ES EL GUARDIAN DEL CHANGE `rol-de-base-sin-bypass-rls`.

Los tests de `test_tenant_isolation.py` prueban COMPORTAMIENTO: que la politica
aisle sobre `platform_probe`. Eso acredita que el aislamiento funciona hoy, en
esa tabla. No alcanza.

El defecto que ADR-020 midio no fue una politica mal escrita: fue que el ROL la
anulaba, con toda la evidencia de catalogo dando verde. El rol de conexion era
superusuario con `rolbypassrls`, y un rol asi ignora toda politica RLS — no la
evalua, pasa de largo. `pg_policies` seguia listando la politica; una auditoria
de cobertura de politicas la daba por buena; y no aislaba nada.

Lo que puede volver es esa CLASE de fallo:

  - un `DATABASE_URL` reapuntado al propietario para destrabar algo en local
  - un Terraform que provisiona un rol de mas
  - una base gestionada cuyo rol administrativo trae BYPASSRLS de fabrica

Ninguna de esas cosas se detecta mirando `platform_probe`. Por eso los tres
tests de aca afirman sobre EL ROL y no sobre una tabla concreta: siguen valiendo
el dia que la tabla testigo se retire, cuando existan tablas de negocio.

Ver `design.md` D-9 del change, y ADR-020.

Se corre con:

    docker compose run --rm backend pytest -m integration
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.session import sesion_de_plataforma

from .soporte import DSN_APLICACION as DSN

pytestmark = pytest.mark.integration

# `current_user` y no un nombre literal: lo que se verifica es el rol con el que
# ESTA conexion esta abierta, sea cual sea. Un nombre hardcodeado probaria que
# cierto rol esta bien configurado, no que la aplicacion se conecte con el.
SQL_ATRIBUTOS_DEL_ROL = text("""
    SELECT rolsuper, rolbypassrls
    FROM pg_roles
    WHERE rolname = current_user
""")

# Tablas con RLS activo y quien es su dueno. `relrowsecurity` es el catalogo
# real, no una lista mantenida a mano.
SQL_DUENOS_DE_TABLAS_CON_RLS = text("""
    SELECT c.relname, pg_get_userbyid(c.relowner) = current_user AS la_tengo_yo
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind = 'r'
      AND c.relrowsecurity
""")

# SQLSTATE 42501 = insufficient_privilege.
PERMISO_DENEGADO = "42501"


def sqlstate(error: DBAPIError) -> str | None:
    """El codigo SQLSTATE del error, o None si el driver no lo expone.

    Se compara el CODIGO y no el texto del mensaje: los mensajes de PostgreSQL
    se traducen segun `lc_messages`, asi que un assert sobre "permission denied"
    pasa o falla segun el locale del servidor. El SQLSTATE es parte del
    protocolo y no cambia.
    """
    return getattr(error.orig, "sqlstate", None)


# ── 1.1 · El rol no tiene con que saltear las politicas ──────────────────────


async def test_el_rol_de_la_aplicacion_no_puede_saltear_rls() -> None:
    """El defecto exacto que ADR-020 midio.

    `rolbypassrls` es el atributo que hace que la capa 2 del aislamiento no
    exista. `rolsuper` se verifica ademas porque un superusuario saltea RLS
    tenga o no el atributo puesto — son dos caminos al mismo agujero.
    """
    async with sesion_de_plataforma(dsn=DSN) as sesion:
        fila = await sesion.execute(SQL_ATRIBUTOS_DEL_ROL)
        superusuario, saltea_rls = fila.one()

    assert not superusuario, (
        "la aplicacion se conecta con un SUPERUSUARIO: saltea toda politica RLS "
        "aunque `rolbypassrls` este en falso (ADR-020)"
    )
    assert not saltea_rls, (
        "el rol de conexion tiene BYPASSRLS: las politicas de aislamiento existen "
        "en el catalogo y no se evaluan (ADR-020)"
    )


# ── 1.2 · El rol no es dueno de lo que consulta ──────────────────────────────


async def test_el_rol_de_la_aplicacion_no_es_dueno_de_las_tablas_con_rls(
    base_migrada: None,
) -> None:
    """Ser dueno alcanza para desactivarse el aislamiento uno mismo.

    `ALTER TABLE ... NO FORCE ROW LEVEL SECURITY` no pide ningun privilegio
    especial: alcanza con ser dueno de la tabla. Si la aplicacion fuera duena,
    el aislamiento quedaria a una sentencia de distancia de cualquier codigo
    —o de cualquier inyeccion—, aunque el rol no tuviera BYPASSRLS.

    Por eso ADR-020 decide DOS roles y no un rol al que se le quita un atributo.
    """
    async with sesion_de_plataforma(dsn=DSN) as sesion:
        filas = (await sesion.execute(SQL_DUENOS_DE_TABLAS_CON_RLS)).all()

    # Sin esta guarda el test pasaria por vacio si un dia no hubiera ninguna
    # tabla con RLS, que es justo el escenario en el que menos deberia pasar.
    assert filas, (
        "no hay ninguna tabla con RLS activo: este test no esta probando nada. "
        "Corre las migraciones antes (`alembic upgrade head`)"
    )

    propias = [nombre for nombre, la_tengo_yo in filas if la_tengo_yo]
    assert not propias, (
        f"la aplicacion es DUENA de tablas con RLS: {sorted(propias)}. "
        "Puede desactivarles el FORCE cuando quiera (ADR-020, design.md D-1)"
    )


# ── 1.3 · El rol no puede tocar el esquema ───────────────────────────────────


async def intentar_crear_tabla(nombre: str) -> DBAPIError | None:
    """Intenta el DDL. Devuelve el error, o None si —mal— funciono.

    Devolver el resultado en vez de usar `pytest.raises` no es estilo: cuando
    este test falla es porque el DDL SI funciono, y entonces la tabla quedo
    creada y commiteada. Hay que poder limpiarla ANTES de reportar el fallo, y
    `pytest.raises` no deja meterse en el medio.
    """
    try:
        async with sesion_de_plataforma(dsn=DSN) as sesion:
            await sesion.execute(text(f"CREATE TABLE {nombre} (id int)"))  # noqa: S608
    except DBAPIError as error:
        return error
    return None


async def test_la_aplicacion_no_puede_crear_tablas() -> None:
    """Acredita la contencion ante inyeccion SQL.

    Separar el rol propietario del de aplicacion no solo arregla RLS: le pone
    techo a lo que una inyeccion puede hacer. Un rol que no puede crear ni
    alterar tablas tampoco puede fabricarse una tabla sin politica para
    escribir ahi, ni tocar las politicas existentes.
    """
    nombre = f"intento_de_ddl_{uuid.uuid4().hex[:8]}"

    error = await intentar_crear_tabla(nombre)

    if error is None:
        # La tabla existe y esta commiteada. Se limpia antes de fallar: un test
        # que deja residuo en la base le pasa el problema al que corre despues,
        # y ese lo va a diagnosticar lejos de aca.
        #
        # Que este DROP funcione no es contradictorio: si el CREATE funciono, el
        # rol tiene DDL, asi que tambien puede deshacerlo.
        async with sesion_de_plataforma(dsn=DSN) as sesion:
            await sesion.execute(text(f"DROP TABLE {nombre}"))  # noqa: S608
        pytest.fail(
            "la aplicacion pudo crear una tabla: puede fabricarse una sin politica "
            "RLS y escribir ahi, o alterar las politicas existentes (ADR-020)"
        )

    assert sqlstate(error) == PERMISO_DENEGADO, (
        "el DDL fallo, pero por un motivo distinto a falta de permisos: "
        f"sqlstate={sqlstate(error)}"
    )
