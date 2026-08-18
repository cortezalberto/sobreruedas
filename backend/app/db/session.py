"""Contexto de tenant y sesiones de base de datos — T-010.

ESTE ES EL CONTROL MAS CRITICO DEL SISTEMA. El plan de seguridad lo dice con
esas palabras. Una falla aca no es un bug: es filtracion de datos entre
agencias, incidente P0 con notificacion a la AAIP (`RN-MT-07`).

LAS TRES CAPAS
──────────────
El aislamiento multi-tenant se sostiene en tres capas simultaneas (ADR-006):

  1. `tenant_id NOT NULL` en toda tabla de negocio
  2. Politica RLS `tenant_isolation` filtrando por `current_setting('app.current_tenant')`
  3. Filtro `tenant_id` explicito tambien en el codigo de aplicacion

Este modulo es lo que hace posible la capa 2: establece el parametro de sesion
que la politica lee. Sin el, RLS no tiene contra que comparar.

POR QUE `set_config` Y NO `SET LOCAL`
────────────────────────────────────
`SET LOCAL app.current_tenant = '<uuid>'` **no admite parametros bindeados**:
el valor va en el texto de la sentencia. Usarlo obligaria a interpolar el uuid,
o sea a construir SQL por concatenacion en el control mas critico del sistema
— exactamente lo que prohibe la regla dura 9.

`set_config(nombre, valor, is_local)` es la forma funcional equivalente y SI
acepta bind. El tercer argumento en `true` es lo que la hace `LOCAL`: el valor
vive hasta el fin de la transaccion.

Ver design.md D-1 y D-2.

POR QUE MUERE CON LA TRANSACCION
────────────────────────────────
`is_local = true` ata el parametro a la transaccion. Al cerrarla, la conexion
vuelve al pool **sin** el valor.

Si fuera `false`, el valor sobreviviria en la conexion, y la conexion se
reutiliza: el proximo request que la tome heredaria el tenant del anterior.
Ese es el modo exacto en que un sistema multi-tenant filtra datos sin que nadie
escriba una linea de codigo incorrecta.

DOS PUERTAS, NO UN BOOLEANO
───────────────────────────
`sesion_de_tenant` exige contexto. `sesion_de_plataforma` no lo establece, y
por eso mismo solo puede usarse bajo el espacio administrativo o en tareas de
plataforma; un test de arquitectura lo verifica (tarea 5.12).

Que se distingan por el NOMBRE y no por `sesion_de_tenant(tenant=None)` es
deliberado: un booleano en la llamada se lee como un detalle en una revision de
codigo, un nombre distinto se lee como una decision (design.md D-4).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

# El nombre es `app.current_tenant`, NO `app.current_tenant_id`. Cita textual
# del plan de seguridad, y lo repiten RN-MT-02, RN-MT-06 y la regla dura 1.
# `CHANGES.md` lo tenia mal; manda el corpus (design.md D-1).
#
# No es cosmetico: `current_setting('app.current_tenant', true)` sobre un nombre
# equivocado devuelve vacio, la politica no matchea ninguna fila, y las
# consultas dejan de traer datos. Eso se lee como "no hay registros", no como
# "el aislamiento esta roto". El sintoma aparece lejos de la causa.
PARAMETRO_TENANT = "app.current_tenant"

# `:tenant` es un parametro bindeado, no una interpolacion. Ver el encabezado.
SENTENCIA_CONTEXTO = text(f"SELECT set_config('{PARAMETRO_TENANT}', :tenant, true)")


class ContextoDeTenantInvalido(RuntimeError):
    """El tenant que llego no es utilizable como contexto de aislamiento.

    Es distinto de "no hay datos para ese tenant": aca ni siquiera se llega a
    consultar. Se levanta ANTES de abrir la conexion, a proposito — un valor
    que no es UUID no tiene por que gastar una conexion del pool, y sobre todo
    no tiene por que acercarse a la base.
    """


def tenant_valido(valor: object) -> uuid.UUID:
    """Normaliza el tenant a UUID o rompe.

    Acepta `uuid.UUID` y cadenas; cualquier otra cosa es invalida. No hay
    fallback ni valor por defecto: un tenant por defecto seria un tenant al que
    se le entregan datos de otro (`RN-MT-06`).
    """
    if isinstance(valor, uuid.UUID):
        return valor
    if not isinstance(valor, str) or not valor:
        raise ContextoDeTenantInvalido(
            f"el contexto de tenant es obligatorio y llego {type(valor).__name__}"
        )
    try:
        return uuid.UUID(valor)
    except ValueError as error:
        # El valor NO se incluye en el mensaje: puede venir de un token y
        # terminar en un log que despues alguien lee sin permisos para verlo.
        raise ContextoDeTenantInvalido("el contexto de tenant no es un UUID") from error


class AccesoCruzado(RuntimeError):
    """Se pidio data de un tenant distinto al que rige el contexto.

    No es un error de programacion cualquiera: es el sintoma de la clase de
    fallo que `RN-MT-07` califica como incidente **P0**. Por eso rompe fuerte y
    se cuenta, en vez de devolver una lista vacia y seguir.
    """


# El tenant que rige el contexto actual. Mismo patron que el identificador de
# correlacion en `core/observability.py`: un ContextVar viaja solo por la tarea
# asincronica, asi que dos requests concurrentes no se pisan.
_tenant_actual: ContextVar[uuid.UUID | None] = ContextVar("tenant_actual", default=None)

# Metrica centinela `rls_violations_total` (RN-MT-08). Debe ser SIEMPRE 0.
# Cualquier incremento dispara P0. Se lleva en memoria del proceso; C-03 la
# expone por Prometheus junto con el resto del instrumental.
_violaciones = 0


def tenant_actual() -> uuid.UUID | None:
    """El tenant del contexto, o None si no hay ninguno establecido."""
    return _tenant_actual.get()


def violaciones_de_aislamiento() -> int:
    """Cuantos intentos de acceso cruzado se detectaron en este proceso."""
    return _violaciones


def registrar_violacion_de_aislamiento() -> None:
    """Suma uno a la metrica centinela `rls_violations_total` (RN-MT-08).

    Publica porque el acceso cruzado no se intenta solo por la via de una
    consulta: un cursor de paginacion emitido para un tenant y presentado en
    otro es exactamente lo mismo, y rechazarlo sin contarlo lo dejaria sin
    registrar. Un ataque de enumeracion se ve en la metrica antes que en
    cualquier otro lado, o no se ve.

    Quien la llama tiene que ademas RECHAZAR la operacion. Contar sin rechazar
    seria peor que no contar.
    """
    global _violaciones
    _violaciones += 1


@contextmanager
def contexto_de_tenant(tenant_id: object) -> Iterator[uuid.UUID]:
    """Establece el tenant que rige, sin abrir ninguna sesion.

    Para trabajo que ocurre FUERA de un ciclo de peticion y respuesta: el
    consumidor de eventos de dominio, sobre todo. El aislamiento no puede
    depender de estar atendiendo un request (D-10).

    OJO CON LO QUE ESTO ES Y LO QUE NO ES
    ─────────────────────────────────────
    Establece la capa 3 —el contexto que `exigir_tenant_del_contexto` compara—,
    NO la capa 2. El parametro `app.current_tenant` de PostgreSQL vive en una
    transaccion, y aca no hay ninguna abierta.

    O sea: esto no reemplaza a `sesion_de_tenant`, la acompana. Quien procese un
    evento igual tiene que pedir sus sesiones con `sesion_de_tenant`, que es lo
    que pone el contexto del lado de la base.
    """
    tenant = tenant_valido(tenant_id)
    testigo = _tenant_actual.set(tenant)
    try:
        yield tenant
    finally:
        # Se restaura aunque el cuerpo haya roto: un contexto que sobrevive es
        # el proximo trabajo heredando el tenant del anterior.
        _tenant_actual.reset(testigo)


def exigir_tenant_del_contexto(tenant_id: object) -> uuid.UUID:
    """Verifica que lo que se va a consultar sea del tenant en contexto.

    Es la **capa 3** del aislamiento: el filtro explicito de la aplicacion. Que
    RLS ya cubra el caso no la hace redundante por gusto — `RN-MT-04` la exige
    justamente para que el aislamiento no dependa de una sola pieza.

    Pedir otro tenant no devuelve vacio: rompe. Un vacio silencioso se lee como
    "no hay datos" y un intento de acceso cruzado quedaria sin registrar.
    """
    pedido = tenant_valido(tenant_id)
    contexto = _tenant_actual.get()

    if contexto is None:
        registrar_violacion_de_aislamiento()
        raise AccesoCruzado("no hay contexto de tenant establecido")
    if pedido != contexto:
        registrar_violacion_de_aislamiento()
        raise AccesoCruzado("se pidio data de un tenant distinto al del contexto")
    return pedido


# Registro explicito y no `lru_cache`: un engine tiene que poder CERRARSE, y
# `lru_cache` no deja recorrer lo que guarda. Un pool de conexiones que nadie
# puede cerrar queda atado al event loop que lo creo; cuando ese loop se cierra
# —entre dos tests, por ejemplo— las conexiones quedan colgadas y el sintoma es
# un "Event loop is closed" a varios tests de distancia de la causa.
_engines: dict[tuple[str, int], AsyncEngine] = {}


def crear_engine(dsn: str, pool_size: int) -> AsyncEngine:
    """Un engine por (DSN, tamano de pool), reutilizado.

    Reutilizado y no global porque los tests necesitan apuntar a otra direccion
    sin reescribir el modulo.
    """
    clave = (dsn, pool_size)
    if clave not in _engines:
        _engines[clave] = create_async_engine(dsn, pool_size=pool_size, pool_pre_ping=True)
    return _engines[clave]


async def cerrar_engines() -> None:
    """Cierra y olvida todos los engines abiertos.

    La usa el apagado de la aplicacion y el aislamiento entre tests. Sin esto,
    reutilizar un engine a traves de dos event loops distintos rompe lejos de
    donde se origina.
    """
    for engine in list(_engines.values()):
        await engine.dispose()
    _engines.clear()


# Pool para cuando el DSN llega explicito. Chico a proposito: quien pasa un DSN
# a mano es un test o una tarea puntual, no el proceso que atiende trafico.
POOL_POR_DEFECTO = 5


def _engine(dsn: str | None) -> AsyncEngine:
    """El engine del DSN pedido, o el de la configuracion del proceso.

    Cuando el DSN llega explicito NO se consulta `Settings`. No es una
    optimizacion: `Settings` exige el conjunto completo de variables
    obligatorias —Keycloak, S3, la master key de tenants— y ninguna de ellas
    tiene nada que ver con abrir una conexion a una base que ya viene nombrada.
    Exigirlas convertiria cualquier fallo de configuracion ajeno en un fallo de
    esta funcion, lejos de su causa.
    """
    if dsn is not None:
        return crear_engine(dsn, POOL_POR_DEFECTO)

    settings = get_settings()
    return crear_engine(settings.database.url.get_secret_value(), settings.database.pool_size)


@asynccontextmanager
async def sesion_de_tenant(
    tenant_id: object, *, dsn: str | None = None
) -> AsyncIterator[AsyncSession]:
    """Sesion con el contexto de tenant establecido en su transaccion.

    El orden importa y es el motivo de que esto sea un context manager y no una
    funcion que devuelve una sesion:

      1. Validar el tenant  ← antes de tocar la base
      2. Abrir la transaccion
      3. Establecer el contexto como PRIMERA sentencia
      4. Recien entonces ceder la sesion

    Un middleware no podria hacer esto: corre antes de que exista la sesion, y
    algo `LOCAL` emitido fuera de una transaccion muere al instante (D-3).
    """
    tenant = tenant_valido(tenant_id)

    fabrica = async_sessionmaker(_engine(dsn), expire_on_commit=False)
    testigo = _tenant_actual.set(tenant)
    try:
        async with fabrica() as sesion:
            async with sesion.begin():
                await sesion.execute(SENTENCIA_CONTEXTO, {"tenant": str(tenant)})
                yield sesion
    finally:
        # Se restaura aunque el cuerpo haya roto: si el ContextVar quedara
        # seteado, la proxima tarea que reutilice este contexto heredaria el
        # tenant. Es la misma clase de fuga que `is_local` evita del lado de
        # PostgreSQL, pero del lado de Python.
        _tenant_actual.reset(testigo)


@asynccontextmanager
async def sesion_de_plataforma(*, dsn: str | None = None) -> AsyncIterator[AsyncSession]:
    """Sesion SIN contexto de tenant. La excepcion, no la regla.

    Legitima solo para migraciones, tareas de plataforma y el backoffice
    cross-tenant bajo `/admin/api/v1`. Fuera de ahi es un agujero en el
    aislamiento, y el test de arquitectura de la tarea 5.12 la busca.

    Sobre tablas con RLS activo esta sesion **no devuelve filas**, que es el
    comportamiento correcto (`RN-MT-06`): sin contexto no hay datos.
    """
    fabrica = async_sessionmaker(_engine(dsn), expire_on_commit=False)
    async with fabrica() as sesion:
        async with sesion.begin():
            yield sesion


@asynccontextmanager
async def sesion_de_catalogo(*, dsn: str | None = None) -> AsyncIterator[AsyncSession]:
    """Sesion para CATALOGOS GLOBALES. Sin contexto de tenant, y sin que falte.

    Existe para no ensanchar `sesion_de_plataforma`, que es otra cosa.

    LA DIFERENCIA, QUE NO ES DE MATIZ
    ──────────────────────────────────
    `sesion_de_plataforma` consulta POR ENCIMA de los tenants: los datos tienen
    dueno y ella lo ignora. Por eso su unico lugar legitimo es el backoffice
    cross-tenant, y por eso el test de arquitectura la persigue.

    Esta consulta tablas que NO TIENEN DUENO. `plans`, `vehicle_brands`,
    `vehicle_models` son catalogo compartido: figuran en `EXENTAS_DE_RLS`
    (`RN-MT-09`), no llevan `tenant_id`, y no hay contexto que establecer porque
    no hay a que acotarlas. Pedirle contexto de tenant a la grilla de precios no
    la haria mas segura: la haria imposible de consultar antes de tener sesion.

    Que sean dos funciones y no un parametro es a proposito. Un
    `sesion_de_plataforma(motivo="catalogo")` se lee igual en el diff que
    cualquier otro uso, y lo que hace falta es exactamente lo contrario: que un
    uso indebido salte a la vista. Cada una tiene su propia lista de lugares
    permitidos en `test_arquitectura.py`.

    ⚠️ NO sirve para tablas con `tenant_id`. Sobre una tabla con RLS activo esta
    sesion no devuelve filas —igual que la de plataforma—, asi que usarla ahi no
    es un agujero, es un listado vacio que alguien va a "arreglar" cambiando la
    sesion. Para datos de un tenant va `sesion_de_tenant`, siempre.
    """
    fabrica = async_sessionmaker(_engine(dsn), expire_on_commit=False)
    async with fabrica() as sesion:
        async with sesion.begin():
            yield sesion
