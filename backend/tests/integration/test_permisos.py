"""Los permisos del rol de aplicacion — ADR-020, design.md D-3 y D-4.

POR QUE ESTE ARCHIVO EXISTE
───────────────────────────
Los permisos del rol `mitutu` no se otorgan tabla por tabla: el init de
PostgreSQL deja puesto un `ALTER DEFAULT PRIVILEGES`, asi que toda tabla que
cree el propietario ya nace con SELECT/INSERT/UPDATE otorgados. Eso elimina la
friccion de acordarse de un GRANT por cada tabla nueva.

Pero un default privilege es **silencioso cuando no se aplica**. No se aplica si
el volumen se creo antes de este change, si la tabla la creo otro rol, o si
aparece un esquema nuevo. Y el sintoma es un `permission denied` en runtime,
lejos de su causa — la misma clase de fallo que ADR-020 vino a arreglar.

Entonces: el default privilege es la ergonomia, y estos tests son la garantia.

RELACION CON `test_tenant_isolation.py`
───────────────────────────────────────
Aquel recorre el catalogo buscando tablas SIN POLITICA. Este recorre el catalogo
buscando tablas SIN PERMISOS. Ninguno de los dos alcanza solo, y hay un motivo
concreto: `information_schema` solo muestra objetos sobre los que el usuario
tiene privilegios, asi que una tabla sin permisos podria volverse invisible para
el otro test. Se cubren mutuamente.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.session import sesion_de_plataforma, sesion_de_tenant

from .soporte import DSN_APLICACION as DSN
from .soporte import sesion_de_propietario

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _con_la_base_migrada(base_migrada: None) -> None:
    """Sin migraciones no hay tablas sobre las que verificar permiso alguno."""


TABLA = "platform_probe"

# Lo que la aplicacion necesita para operar, y nada mas.
#
# DELETE no esta, y no es un olvido: la regla dura 3 prohibe el borrado fisico
# (soft delete universal). Negarlo en la base convierte esa convencion en
# garantia, y cubre el DELETE que llegue por una via no prevista — una inyeccion,
# por ejemplo, que ninguna revision de codigo va a ver.
#
# ESCAPE HATCH, declarado (design.md D-4)
# ───────────────────────────────────────
# Si una tabla necesita borrado fisico por obligacion de retencion legal
# —`audit_logs` a los 5 anios, `idempotency_keys` vencidas—, el GRANT DELETE se
# otorga NOMBRADO en la migracion de ESA tabla, y este test se actualiza para
# declararla como excepcion.
#
# Mismo criterio que la lista `EXENTAS_DE_RLS` de `test_tenant_isolation.py`: se
# escribe a mano a proposito, porque una excepcion que se autodetecta no es una
# excepcion. Otorgarlo global "por las dudas" seria devolver la regla dura 3 al
# terreno de la convencion, que es de donde este change la saco.
PERMISOS_NECESARIOS = ("SELECT", "INSERT", "UPDATE")
PERMISOS_PROHIBIDOS = ("DELETE", "TRUNCATE")

# ESCAPE HATCH, declarado — el mismo criterio de arriba, para el otro sentido.
#
# `vehicle_status_history` (C-14, `design.md` D-1) es APPEND-ONLY por diseño: su
# propia migracion (`019`) REVOCA `UPDATE` sobre si misma, a proposito, para que
# un registro escrito no se pueda alterar ni con las credenciales de la
# aplicacion. Sin esta excepcion DECLARADA, este test leeria esa revocacion
# deliberada como el mismo "permiso que el init olvido otorgar" que el resto del
# archivo persigue — exactamente lo contrario de lo que `019` hizo a proposito.
#
# Escrita a mano, como `EXENTAS_DE_RLS`: una excepcion que se autodetecta no es
# una excepcion.
#
# HOY TODAVIA NO TIENE EFECTO — y eso es correcto, no un error de este archivo.
# La migracion `019` (expand, este PR) revoca `DELETE` pero **deja `UPDATE`
# otorgado**: el `REVOKE UPDATE` se movio a una migracion de contract posterior
# (regla dura 13, `ADR-025` — ver `019_vehicle_status_history.py`
# §"EN DOS DESPLIEGUES"). Esta linea se ADELANTA a proposito: es permisiva
# (solo perdona un permiso ausente, nunca exige que falte), asi que no rompe
# nada mientras `UPDATE` sigue otorgado, y va a ser lo que haga pasar este
# mismo gate el dia que el contract llegue y revoque `UPDATE` de verdad.
SIN_UPDATE_A_PROPOSITO = {"vehicle_status_history"}

PERMISO_DENEGADO = "42501"


async def rol_de_la_aplicacion() -> str:
    """El nombre del rol con el que la aplicacion esta conectada.

    Se pregunta en vez de hardcodear `mitutu`: lo que se verifica es el rol que
    la aplicacion USA, no que cierto rol este bien configurado. Si alguien
    reapunta el DSN, estos tests tienen que hablar del rol nuevo.
    """
    async with sesion_de_plataforma(dsn=DSN) as sesion:
        return str((await sesion.execute(text("SELECT current_user"))).scalar_one())


async def tablas_con_tenant_id() -> list[str]:
    """Las tablas sujetas a aislamiento, vistas por el PROPIETARIO.

    Como propietario a proposito, por el mismo motivo que en
    `test_tenant_isolation.tablas_sin_politica`: consultado como aplicacion,
    `information_schema.columns` esconderia justo las tablas sin permisos, que
    son las que este archivo busca.
    """
    consulta = text("""
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN information_schema.columns col
          ON col.table_name = c.relname
         AND col.table_schema = n.nspname
         AND col.column_name = 'tenant_id'
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
        """)
    async with sesion_de_propietario() as sesion:
        return sorted(fila[0] for fila in await sesion.execute(consulta))


async def permisos_sobre(rol: str, tabla: str, permisos: tuple[str, ...]) -> dict[str, bool]:
    """Que puede `rol` sobre `tabla`, segun el catalogo.

    Se pregunta por catalogo y no intentando la operacion: intentar un DELETE
    para saber si se puede lo dejaria hecho cuando la respuesta es que si, que
    es exactamente el caso en el que menos conviene.
    """
    consulta = text(
        " UNION ALL ".join(
            f"SELECT '{permiso}' AS permiso, "
            f"has_table_privilege(:rol, :tabla, '{permiso}') AS lo_tiene"
            for permiso in permisos
        )
    )
    async with sesion_de_propietario() as sesion:
        filas = await sesion.execute(consulta, {"rol": rol, "tabla": tabla})
        return {nombre: lo_tiene for nombre, lo_tiene in filas}


# ── 3.3 · Ninguna tabla se queda sin los permisos que necesita ───────────────


async def test_toda_tabla_con_tenant_id_es_operable_por_la_aplicacion() -> None:
    """La red debajo del default privilege.

    Por catalogo y no por lista a mano: una lista se queda corta en silencio en
    cuanto alguien agrega una tabla, y este test seguiria pasando sin cubrirla.
    """
    rol = await rol_de_la_aplicacion()
    tablas = await tablas_con_tenant_id()

    assert tablas, (
        "no hay ninguna tabla con tenant_id: este test no esta probando nada. "
        "Corre las migraciones antes"
    )

    faltantes = {
        tabla: [
            p
            for p, lo_tiene in (await permisos_sobre(rol, tabla, PERMISOS_NECESARIOS)).items()
            if not lo_tiene and not (p == "UPDATE" and tabla in SIN_UPDATE_A_PROPOSITO)
        ]
        for tabla in tablas
    }
    faltantes = {tabla: permisos for tabla, permisos in faltantes.items() if permisos}

    assert not faltantes, (
        f"al rol '{rol}' le faltan permisos: {faltantes}. "
        "El ALTER DEFAULT PRIVILEGES del init no alcanzo a estas tablas — "
        "probablemente el volumen se creo antes de ADR-020, o las creo otro rol"
    )


# ── 3.4 · La aplicacion no puede borrar ──────────────────────────────────────


async def test_la_aplicacion_no_tiene_permiso_de_borrado() -> None:
    """La regla dura 3 dejando de ser convencion y pasando a ser garantia."""
    rol = await rol_de_la_aplicacion()

    otorgados = await permisos_sobre(rol, TABLA, PERMISOS_PROHIBIDOS)
    de_mas = [permiso for permiso, lo_tiene in otorgados.items() if lo_tiene]

    assert not de_mas, (
        f"el rol '{rol}' tiene {de_mas} sobre {TABLA}. El sistema hace borrado "
        "logico universal (regla dura 3): ningun camino legitimo necesita esto"
    )


async def test_un_delete_desde_la_aplicacion_es_rechazado(tenant: uuid.UUID) -> None:
    """El catalogo dice que no puede; esto comprueba que efectivamente no puede.

    Los dos tests no son el mismo: el de arriba lee `has_table_privilege`, y una
    lectura de catalogo puede estar bien y el motor comportarse distinto —
    justamente lo que paso con `pg_policies` en ADR-020.
    """
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        await sesion.execute(
            text(f"INSERT INTO {TABLA} (tenant_id, etiqueta) VALUES (:t, :e)"),  # noqa: S608
            {"t": str(tenant), "e": "no-me-vas-a-poder-borrar"},
        )

    with pytest.raises(DBAPIError) as capturado:
        async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
            await sesion.execute(text(f"DELETE FROM {TABLA}"))  # noqa: S608

    assert getattr(capturado.value.orig, "sqlstate", None) == PERMISO_DENEGADO

    # Y la fila sigue ahi: el rechazo no es cosmetico.
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        total = await sesion.execute(text(f"SELECT count(*) FROM {TABLA}"))  # noqa: S608
        assert total.scalar_one() == 1


# ── 3.5 · El default privilege alcanza a lo que todavia no existe ────────────


async def test_una_tabla_nueva_nace_con_los_permisos_puestos() -> None:
    """Probar el mecanismo, no confiar en el.

    Los tests de arriba pasan hoy porque `platform_probe` esta bien otorgada.
    Tambien pasarian si el `ALTER DEFAULT PRIVILEGES` no existiera y alguien
    hubiera hecho el GRANT a mano una vez. Aca se crea una tabla NUEVA y se
    verifica que nace operable sin que nadie otorgue nada: eso es lo que hace
    que agregar una tabla en una migracion futura no requiera acordarse de nada.
    """
    rol = await rol_de_la_aplicacion()
    nombre = f"probe_permisos_{uuid.uuid4().hex[:8]}"

    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(f"CREATE TABLE {nombre} (id serial PRIMARY KEY, tenant_id uuid NOT NULL)")
        )
    try:
        otorgados = await permisos_sobre(rol, nombre, PERMISOS_NECESARIOS)
        assert all(otorgados.values()), (
            f"la tabla nueva {nombre} no nacio operable para '{rol}': {otorgados}. "
            "El ALTER DEFAULT PRIVILEGES del init 02 no esta puesto"
        )

        prohibidos = await permisos_sobre(rol, nombre, PERMISOS_PROHIBIDOS)
        assert not any(
            prohibidos.values()
        ), f"la tabla nueva {nombre} nacio con permisos de borrado: {prohibidos}"
    finally:
        async with sesion_de_propietario() as sesion:
            await sesion.execute(text(f"DROP TABLE {nombre}"))


# ── 5.5 · Por que la introspeccion NO puede correr como aplicacion ───────────


async def columnas_visibles_para(nombre: str, como_propietario: bool) -> int:
    """Cuantas columnas de `nombre` ve `information_schema.columns`."""
    consulta = text("SELECT count(*) FROM information_schema.columns WHERE table_name = :t")
    if como_propietario:
        async with sesion_de_propietario() as sesion:
            return int((await sesion.execute(consulta, {"t": nombre})).scalar_one())
    async with sesion_de_plataforma(dsn=DSN) as sesion:
        return int((await sesion.execute(consulta, {"t": nombre})).scalar_one())


async def test_una_tabla_sin_permisos_es_invisible_para_la_aplicacion() -> None:
    """El hueco que obliga a que los tests introspectivos corran como propietario.

    `information_schema.columns` **solo muestra columnas de tablas sobre las que
    el usuario actual tiene algun privilegio**. Consultada con el rol de
    aplicacion, una tabla sin GRANT simplemente no existe.

    Consecuencia: si `tablas_sin_politica()` de `test_tenant_isolation.py`
    corriera como aplicacion, la tabla peor configurada del esquema —sin
    politica Y sin permisos— seria justo la que ese test no puede encontrar. Un
    control que el catalogo da por puesto y no esta, que es exactamente la falla
    que ADR-020 documenta, corrida un nivel.

    Este test es la evidencia de ese hueco. Sin el, la decision de usar el
    propietario en la introspeccion es una afirmacion en un comentario.
    """
    rol = await rol_de_la_aplicacion()
    nombre = f"probe_invisible_{uuid.uuid4().hex[:8]}"

    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(f"CREATE TABLE {nombre} (id serial PRIMARY KEY, tenant_id uuid NOT NULL)")
        )
    try:
        # El default privilege ya la otorgo al crearla, asi que primero se
        # verifica que la aplicacion SI la ve. Sin este paso, un cero al final
        # podria significar "la tabla no se creo" en vez de "no la ve".
        assert await columnas_visibles_para(nombre, como_propietario=False) > 0

        async with sesion_de_propietario() as sesion:
            await sesion.execute(text(f"REVOKE ALL ON {nombre} FROM {rol}"))

        assert await columnas_visibles_para(nombre, como_propietario=False) == 0, (
            "la aplicacion sigue viendo una tabla sobre la que no tiene permisos: "
            "si esto cambia, revisar por que la introspeccion corre como propietario"
        )
        assert await columnas_visibles_para(nombre, como_propietario=True) > 0, (
            "el propietario tampoco la ve: entonces el problema no es de permisos "
            "y este test dejo de probar lo que dice"
        )
    finally:
        async with sesion_de_propietario() as sesion:
            await sesion.execute(text(f"DROP TABLE {nombre}"))
