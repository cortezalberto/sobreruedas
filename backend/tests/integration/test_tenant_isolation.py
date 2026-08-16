"""Aislamiento multi-tenant contra PostgreSQL real — C-02, bloque 2.

ESTOS SON LOS TESTS MAS IMPORTANTES DEL REPOSITORIO. No prueban una feature:
prueban que los datos de una agencia no lleguen a otra. `RN-MT-07` califica esa
falla como incidente **P0** con notificacion a la AAIP.

Sin mocks, y no por dogma (regla dura 8): RLS es una funcionalidad **de
PostgreSQL**. Un doble de la base probaria el doble. El unico modo de saber si
la politica aisla es preguntarle a un PostgreSQL que la tenga puesta.

Se corre con:

    docker compose run --rm backend pytest -m integration
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.session import (
    AccesoCruzado,
    cerrar_engines,
    exigir_tenant_del_contexto,
    sesion_de_plataforma,
    sesion_de_tenant,
    violaciones_de_aislamiento,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def engines_limpios() -> AsyncIterator[None]:
    """Cierra los engines al terminar cada test.

    pytest-asyncio abre un event loop por test. Un engine reutilizado entre dos
    loops arrastra conexiones del anterior, ya cerrado, y el sintoma —"Event
    loop is closed"— aparece en un test que no tiene nada que ver.

    `autouse` a proposito: acordarse de pedirlo es exactamente el error que
    este fixture existe para evitar.
    """
    yield
    await cerrar_engines()


DSN = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://deruedas:deruedas@postgres:5432/deruedas"
)

TABLA = "platform_probe"

# Las consultas se arman UNA vez, aca, y no en cada test.
#
# Sobre el `noqa`: lo interpolado es `TABLA`, una constante de este modulo — no
# entra dato de usuario por ningun lado. Y un nombre de tabla NO puede ser
# parametro bindeado: los binds de SQL son VALORES, nunca identificadores, asi
# que interpolar es la unica forma posible de nombrar la tabla. Todo lo que si
# es dato —el tenant, la etiqueta— va bindeado sin excepcion, que es lo que la
# regla dura 9 pide de verdad.
SQL_INSERTAR = text(f"INSERT INTO {TABLA} (tenant_id, etiqueta) VALUES (:t, :e)")  # noqa: S608
SQL_ETIQUETAS = text(f"SELECT etiqueta FROM {TABLA}")  # noqa: S608
SQL_CONTAR = text(f"SELECT count(*) FROM {TABLA}")  # noqa: S608
SQL_ETIQUETAS_DEL_TENANT = text(f"SELECT etiqueta FROM {TABLA} WHERE tenant_id = :t")  # noqa: S608
SQL_CONTEXTO_ACTUAL = text("SELECT current_setting('app.current_tenant', true)")

# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ EL AISLAMIENTO NO ESTA ACTIVO TODAVIA — ADR-020
#
# El rol con el que la aplicacion se conecta es superusuario con `rolbypassrls`,
# y un rol asi IGNORA todas las politicas RLS. Medido sobre esta misma tabla,
# con esta misma politica, en el mismo momento:
#
#     prueba_rls (NOSUPERUSER NOBYPASSRLS), sin contexto ->  0 filas  OK
#     prueba_rls,                           con contexto ->  1 fila   OK
#     deruedas   (superusuario)                          -> 26 filas  MAL
#
# La politica es correcta; el rol la anula. El arreglo toca compose, el init de
# PostgreSQL, .env, el CI y Terraform: va en el change `rol-de-base-sin-bypass-rls`.
#
# `strict=True` a proposito: el dia que el rol se arregle, estos tests pasan y
# pytest convierte el "fallo esperado" en ERROR, obligando a sacar la marca. Un
# `skip` los habria escondido para siempre, que es como una capa de seguridad
# se apaga sin que nadie se entere.
# ─────────────────────────────────────────────────────────────────────────────
SIN_AISLAMIENTO_REAL = pytest.mark.xfail(
    strict=True,
    reason="ADR-020: el rol de conexion es superusuario con BYPASSRLS y saltea toda politica",
)

# Tablas legitimamente exentas de RLS, exhaustivas segun RN-MT-09. Ninguna otra
# puede estarlo. La lista se escribe a mano A PROPOSITO: es la declaracion de
# una excepcion, y una excepcion que se autodetecta no es una excepcion.
EXENTAS_DE_RLS = frozenset(
    {
        "tenants",
        "plans",
        "vehicle_brands",
        "vehicle_models",
        "vehicle_versions",
        "document_types",
        "financial_partners",
        "feature_flags",
        "audit_logs",
        "super_admins",  # ADR-017: rol de plataforma, fuera de todo tenant
        "alembic_version",  # metadata de migraciones, sin tenant_id
    }
)


@pytest.fixture
def tenant_a() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def tenant_b() -> uuid.UUID:
    return uuid.uuid4()


async def sembrar(tenant: uuid.UUID, etiqueta: str) -> None:
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        await sesion.execute(
            SQL_INSERTAR,
            {"t": str(tenant), "e": etiqueta},
        )


async def etiquetas_visibles(tenant: uuid.UUID) -> list[str]:
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        filas = await sesion.execute(SQL_ETIQUETAS)
        return sorted(fila[0] for fila in filas)


# ── 2.1 · Con contexto se ve lo propio, y solo lo propio ─────────────────────


@SIN_AISLAMIENTO_REAL
async def test_solo_se_ven_las_filas_del_tenant_en_contexto(
    tenant_a: uuid.UUID, tenant_b: uuid.UUID
) -> None:
    await sembrar(tenant_a, "de-a")
    await sembrar(tenant_b, "de-b")

    assert await etiquetas_visibles(tenant_a) == ["de-a"]
    assert await etiquetas_visibles(tenant_b) == ["de-b"]


@SIN_AISLAMIENTO_REAL
async def test_la_politica_tambien_gobierna_la_escritura(tenant_a: uuid.UUID) -> None:
    """`WITH CHECK`: no alcanza con no VER lo ajeno, tampoco se puede ESCRIBIR
    una fila a nombre de otro tenant."""
    ajeno = uuid.uuid4()
    # `DBAPIError` y no `Exception`: lo que tiene que romper es la BASE
    # rechazando el INSERT por la politica, no un TypeError nuestro camino
    # arriba. Con `Exception` el test pasaria igual si el codigo del test
    # estuviera roto, que es la forma mas comun de tener un test que no prueba.
    with pytest.raises(DBAPIError):
        async with sesion_de_tenant(tenant_a, dsn=DSN) as sesion:
            await sesion.execute(
                SQL_INSERTAR,
                {"t": str(ajeno), "e": "contrabando"},
            )


# ── 2.2 · Sin contexto no hay filas ──────────────────────────────────────────


@SIN_AISLAMIENTO_REAL
async def test_sin_contexto_no_se_devuelve_ninguna_fila(tenant_a: uuid.UUID) -> None:
    await sembrar(tenant_a, "de-a")

    async with sesion_de_plataforma(dsn=DSN) as sesion:
        filas = await sesion.execute(SQL_ETIQUETAS)
        assert filas.all() == []


@SIN_AISLAMIENTO_REAL
async def test_sin_contexto_no_se_asume_ningun_tenant(
    tenant_a: uuid.UUID, tenant_b: uuid.UUID
) -> None:
    """El contrapunto que le da valor al test de arriba.

    Cero filas podria significar "la tabla esta vacia". Aca hay filas de DOS
    tenants y siguen siendo cero: no se eligio ninguno por defecto.
    """
    await sembrar(tenant_a, "de-a")
    await sembrar(tenant_b, "de-b")

    async with sesion_de_plataforma(dsn=DSN) as sesion:
        total = await sesion.execute(SQL_CONTAR)
        assert total.scalar_one() == 0


# ── 2.3 · El contexto no sobrevive a la transaccion ──────────────────────────


async def test_el_parametro_no_sobrevive_a_la_transaccion(tenant_a: uuid.UUID) -> None:
    """La fuga que este test descarta es la peor de todas.

    Si el parametro sobreviviera, la conexion volveria al pool con el tenant
    puesto y el proximo request que la tomara heredaria datos ajenos — sin que
    nadie haya escrito una linea de codigo incorrecta.
    """
    async with sesion_de_tenant(tenant_a, dsn=DSN) as sesion:
        adentro = await sesion.execute(SQL_CONTEXTO_ACTUAL)
        assert adentro.scalar_one() == str(tenant_a)

    async with sesion_de_plataforma(dsn=DSN) as sesion:
        despues = await sesion.execute(SQL_CONTEXTO_ACTUAL)
        assert despues.scalar_one() in (None, "")


# ── 2.4 · Concurrencia ───────────────────────────────────────────────────────


@SIN_AISLAMIENTO_REAL
async def test_dos_tenants_concurrentes_no_se_pisan(
    tenant_a: uuid.UUID, tenant_b: uuid.UUID
) -> None:
    """Dos sesiones simultaneas, cada una ve lo suyo EN TODO MOMENTO.

    Las lecturas se intercalan a proposito con esperas: si el contexto viviera
    en la conexion en vez de en la transaccion, o si el ContextVar se
    compartiera entre tareas, el solapamiento lo destapa. Una version
    secuencial de este test pasaria igual estando roto.
    """
    await sembrar(tenant_a, "de-a")
    await sembrar(tenant_b, "de-b")

    async def leer_intercalado(tenant: uuid.UUID, esperado: str) -> None:
        async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
            for _ in range(5):
                filas = await sesion.execute(SQL_ETIQUETAS)
                assert sorted(f[0] for f in filas) == [esperado]
                await asyncio.sleep(0)  # cede el control a la otra tarea

    # `return_exceptions=True` NO es para tragarse el fallo — se relanza abajo.
    # Es para que las DOS tareas terminen antes de salir. Sin esto, gather
    # propaga la primera excepcion y deja la otra tarea viva, con su
    # transaccion abierta y su lock puesto: el proximo test que necesite un
    # lock exclusivo sobre la tabla se cuelga, y el rojo aparece en un test que
    # no tiene nada que ver.
    resultados = await asyncio.gather(
        leer_intercalado(tenant_a, "de-a"),
        leer_intercalado(tenant_b, "de-b"),
        return_exceptions=True,
    )
    for resultado in resultados:
        if isinstance(resultado, BaseException):
            raise resultado


# ── 2.5 · La capa de aplicacion se sostiene sola ─────────────────────────────


async def test_el_filtro_explicito_acota_aunque_la_politica_no_aplique(
    tenant_a: uuid.UUID, tenant_b: uuid.UUID
) -> None:
    """La segunda capa, probada CON LA PRIMERA DESACTIVADA.

    `NO FORCE` deja de aplicar la politica al dueno de la tabla, que es como se
    conecta la aplicacion. Con RLS asi neutralizado, el filtro explicito de la
    consulta tiene que seguir acotando al tenant — eso es lo que `RN-MT-04`
    pide y lo unico que hace que la redundancia valga algo.
    """
    await sembrar(tenant_a, "de-a")
    await sembrar(tenant_b, "de-b")

    # `ALTER TABLE` toma un lock exclusivo: si otra conexion quedo con una
    # transaccion abierta, espera. Sin techo esperaria para siempre, y un test
    # colgado es peor que uno rojo — no dice nada y ademas frena la suite.
    async with sesion_de_plataforma(dsn=DSN) as sesion:
        await sesion.execute(text("SET LOCAL lock_timeout = '5s'"))
        await sesion.execute(text(f"ALTER TABLE {TABLA} NO FORCE ROW LEVEL SECURITY"))
    try:
        async with sesion_de_tenant(tenant_a, dsn=DSN) as sesion:
            # Sin politica aplicando, una consulta SIN filtro ve todo:
            todas = await sesion.execute(SQL_ETIQUETAS)
            assert len(todas.all()) >= 2

            # ...y una consulta CON el filtro explicito sigue acotada.
            propias = await sesion.execute(
                SQL_ETIQUETAS_DEL_TENANT,
                {"t": str(tenant_a)},
            )
            assert sorted(f[0] for f in propias) == ["de-a"]
    finally:
        # En `finally` a proposito: dejar la tabla sin FORCE por un test que
        # fallo a la mitad convertiria este test en el que rompe todos los
        # demas, y el diagnostico empezaria por el lugar equivocado.
        async with sesion_de_plataforma(dsn=DSN) as sesion:
            await sesion.execute(text("SET LOCAL lock_timeout = '5s'"))
            await sesion.execute(text(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY"))


# ── 2.6 y 2.7 · Cobertura introspectiva de las politicas ─────────────────────


async def tablas_sin_politica() -> set[str]:
    """Tablas con `tenant_id` y sin politica activa. Deberia ser vacio siempre.

    Recorre el catalogo REAL y no una lista mantenida a mano: una lista se
    queda corta en silencio en cuanto alguien agrega una tabla, y el test
    seguiria pasando sin cubrirla.
    """
    consulta = text(
        """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN information_schema.columns col
          ON col.table_name = c.relname
         AND col.table_schema = n.nspname
         AND col.column_name = 'tenant_id'
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
          AND NOT EXISTS (
              SELECT 1 FROM pg_policies p
              WHERE p.schemaname = n.nspname AND p.tablename = c.relname
          )
        """
    )
    async with sesion_de_plataforma(dsn=DSN) as sesion:
        filas = await sesion.execute(consulta)
        return {fila[0] for fila in filas}


async def test_toda_tabla_con_tenant_id_tiene_politica() -> None:
    faltantes = await tablas_sin_politica() - EXENTAS_DE_RLS
    assert not faltantes, f"tablas con tenant_id y sin politica RLS: {sorted(faltantes)}"


async def test_el_detector_detecta() -> None:
    """Probar el detector, no solo usarlo.

    El test de arriba pasa hoy porque hay una sola tabla y esta bien puesta.
    Tambien pasaria si la consulta estuviera rota y devolviera vacio siempre.
    Aca se crea una tabla con `tenant_id` y sin politica: si el detector no la
    encuentra, el test de arriba no vale nada.
    """
    nombre = f"probe_sin_politica_{uuid.uuid4().hex[:8]}"
    async with sesion_de_plataforma(dsn=DSN) as sesion:
        await sesion.execute(
            text(f"CREATE TABLE {nombre} (id serial PRIMARY KEY, tenant_id uuid NOT NULL)")
        )
    try:
        assert nombre in await tablas_sin_politica()
    finally:
        async with sesion_de_plataforma(dsn=DSN) as sesion:
            await sesion.execute(text(f"DROP TABLE {nombre}"))


async def test_la_tabla_testigo_tiene_force_activo() -> None:
    """`ENABLE` sin `FORCE` deja la politica sin aplicar al dueno de la tabla.

    La aplicacion se conecta justamente como dueno. Con solo ENABLE, la
    politica existe, `pg_policies` la lista, cualquier auditoria la da por
    buena — y no aisla nada. Es el modo mas silencioso de tener RLS que no RLS.
    """
    async with sesion_de_plataforma(dsn=DSN) as sesion:
        fila = await sesion.execute(
            text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = :t"),
            {"t": TABLA},
        )
        habilitado, forzado = fila.one()
    assert habilitado, "RLS no esta habilitado en la tabla testigo"
    assert forzado, "RLS esta habilitado pero NO forzado: no aplica al dueno"


# ── 2.8 · La violacion se detecta y se cuenta ────────────────────────────────


async def test_operacion_normal_no_incrementa_la_metrica(tenant_a: uuid.UUID) -> None:
    antes = violaciones_de_aislamiento()
    async with sesion_de_tenant(tenant_a, dsn=DSN):
        exigir_tenant_del_contexto(tenant_a)
    assert violaciones_de_aislamiento() == antes


async def test_pedir_otro_tenant_rompe_y_cuenta(tenant_a: uuid.UUID, tenant_b: uuid.UUID) -> None:
    antes = violaciones_de_aislamiento()
    async with sesion_de_tenant(tenant_a, dsn=DSN):
        with pytest.raises(AccesoCruzado):
            exigir_tenant_del_contexto(tenant_b)
    assert violaciones_de_aislamiento() == antes + 1


async def test_pedir_datos_sin_contexto_rompe_y_cuenta(tenant_a: uuid.UUID) -> None:
    antes = violaciones_de_aislamiento()
    with pytest.raises(AccesoCruzado):
        exigir_tenant_del_contexto(tenant_a)
    assert violaciones_de_aislamiento() == antes + 1
