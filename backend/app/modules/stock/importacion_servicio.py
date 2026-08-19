"""Ejecucion de una importacion masiva de stock — C-17, `T-094`.

EL RECORRIDO COMPLETO
──────────────────────
    POST /vehicles/import
      └─ `registrar()`  ── guarda el CSV en Redis, crea la fila `imports`
                           en `pending` y encola la tarea. Devuelve al toque.
                                   │
    worker de Celery ──────────────┘
      └─ `ejecutar_importacion()` ── parsing → validating → importing
                                     → completed | failed

    GET /imports/{id}  ── el frontend pregunta cada 2 s hasta un estado terminal.

POR QUE EL CSV VA A REDIS Y NO AL MENSAJE DE CELERY
─────────────────────────────────────────────────────
Un archivo de 10 MB en el mensaje viaja en base64 —13 MB— por el broker, y
Celery reencola el mensaje completo en cada reintento. Redis con TTL lo deja en
un solo lugar, con una clave que caduca sola si la tarea nunca corre.

⚠️ Es un ARREGLO PROVISORIO y esta declarado como tal: el lugar correcto es el
object storage de `ADR-008`, que lo construye C-06 y hoy no existe. Cuando
exista, cambia `_guardar_planilla` / `_traer_planilla` y nada mas.

POR QUE VARIAS TRANSACCIONES CORTAS Y NO UNA LARGA
────────────────────────────────────────────────────
La tentacion es abrir una sesion, hacer todo y cerrar. No sirve por dos motivos
que se refuerzan:

  1. **El frontend hace polling.** Con una sola transaccion, `parsing`,
     `validating` e `importing` no son visibles hasta el final: el usuario ve
     `pending` durante dos minutos y despues `completed`. La barra de progreso
     no tiene contra que avanzar.
  2. **`RN-ST-13` pide commit por lote de 100.** Una transaccion de 5.000
     INSERTs que falla en la 4.999 no deja nada — y el reporte por fila, que es
     lo que hace util a este flujo, quedaria describiendo trabajo que se
     deshizo.

Cada `async with sesion_de_tenant(...)` de abajo es una transaccion.

LO QUE UNA FILA MALA NO PUEDE HACER
─────────────────────────────────────
Un INSERT que viola una constraint **aborta la transaccion entera** en
PostgreSQL: las 99 filas buenas del lote se irian con ella. Por eso cada fila va
en su propio `begin_nested()` —un SAVEPOINT—, que se puede deshacer sin tocar
el resto del lote.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence
from typing import Any

from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.errors import DomainError, PlanQuotaExceeded
from app.db.session import sesion_de_tenant
from app.modules.stock.importacion import (
    COLUMNA_DE_CAMPO,
    TAMANO_DE_LOTE,
    ArchivoIlegible,
    ErrorDeFila,
    FilaLeida,
    Lectura,
    leer_planilla,
)
from app.modules.stock.importacion_modelo import EstadoDeImportacion, Import
from app.modules.stock.models import Vehicle
from app.modules.stock.repository import contar_vehiculos
from app.modules.stock.schemas import EstadoDeVehiculo, VehiculoCrear
from app.modules.tenancy.limits import PlanLimitsService, Recurso
from app.modules.tenancy.models import Branch, VehicleBrand, VehicleModel

__all__ = [
    "ImportacionNoEncontrada",
    "ImportService",
    "ejecutar_importacion",
]

# Una hora. Si la tarea no corrio en ese lapso, el worker esta caido y el
# archivo no sirve: la agencia lo va a volver a subir. Sin TTL, un Redis de
# desarrollo junta planillas de meses.
_TTL_PLANILLA = 3600


class ImportacionNoEncontrada(DomainError):
    """No existe, o es de otra agencia. Las dos dan 404, como en vehiculos."""

    status_code = 404


# ── Alta y consulta, desde el request ───────────────────────────────────────


class ImportService:
    """Lo que corre DENTRO del request. No importa nada: registra y encola."""

    def __init__(self, sesion: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._sesion = sesion
        self._tenant_id = tenant_id

    async def registrar(
        self, *, nombre_archivo: str, contenido: bytes, creado_por: uuid.UUID | None
    ) -> Import:
        """Valida lo que descarta el archivo entero y encola el resto.

        El parseo COMPLETO no se hace acá, pero el rechazo de archivo si:
        pesar mas de 10 MB, no ser texto o faltarle una columna obligatoria son
        cosas que se saben en milisegundos, y hacerlas en el worker obligaria al
        usuario a esperar un polling para que le digan que subio el `.xlsx`.

        Lo que si queda para el worker es el parseo fila por fila, que es lo
        unico que escala con el tamaño del archivo.
        """
        leer_planilla(contenido)  # levanta `ArchivoIlegible`; el router lo traduce

        corrida = Import(
            tenant_id=self._tenant_id,
            source_filename=nombre_archivo[:255],
            status=EstadoDeImportacion.PENDIENTE.value,
            created_by=creado_por,
        )
        self._sesion.add(corrida)
        await self._sesion.flush()

        await _guardar_planilla(self._tenant_id, corrida.id, contenido)
        return corrida

    async def obtener(self, importacion_id: uuid.UUID) -> Import:
        corrida = await self._sesion.scalar(
            select(Import).where(
                Import.id == importacion_id,
                Import.tenant_id == self._tenant_id,
                Import.deleted_at.is_(None),
            )
        )
        if corrida is None:
            raise ImportacionNoEncontrada("no existe esa importacion")
        return corrida

    async def listar(self) -> Sequence[Import]:
        return (
            (
                await self._sesion.execute(
                    select(Import)
                    .where(Import.tenant_id == self._tenant_id, Import.deleted_at.is_(None))
                    .order_by(Import.created_at.desc())
                )
            )
            .scalars()
            .all()
        )


# ── Ejecucion, desde el worker ──────────────────────────────────────────────


async def ejecutar_importacion(importacion_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
    """El cuerpo de la tarea de Celery. Nunca levanta.

    Que no levante es deliberado: un fallo tiene que quedar en la FILA, con su
    motivo, porque es lo unico que el frontend puede leer. Una excepcion que
    sube a Celery deja la corrida clavada en `importing` para siempre y al
    navegador preguntando sin fin.

    Devuelve **`False` si la fila todavia no es visible**, y ese valor es el que
    hace que la tarea reintente. La distincion importa: "no la veo" es distinto
    de "fallo", y solo la primera se puede repetir sin duplicar trabajo.

    ⚠️ Cuando devuelve `False` NO borra el archivo de Redis. Borrarlo dejaria al
    reintento sin nada que importar — y el sintoma seria una corrida que falla
    con "el archivo ya no esta disponible" en vez de importar.
    """
    async with sesion_de_tenant(tenant_id) as sesion:
        if await _fila(sesion, importacion_id) is None:
            return False

    try:
        contenido = await _traer_planilla(tenant_id, importacion_id)
        if contenido is None:
            await _marcar_fallida(
                importacion_id, tenant_id, "el archivo subido ya no esta disponible"
            )
            return True

        lectura = await _parsear(importacion_id, tenant_id, contenido)
        if lectura is not None:
            await _importar(importacion_id, tenant_id, lectura)
    except Exception as fallo:  # noqa: BLE001 — ver el docstring
        await _marcar_fallida(importacion_id, tenant_id, f"error inesperado: {fallo}")
    finally:
        await _borrar_planilla(tenant_id, importacion_id)
    return True


async def _parsear(
    importacion_id: uuid.UUID, tenant_id: uuid.UUID, contenido: bytes
) -> Lectura | None:
    """Fase `parsing` → `validating`. Devuelve `None` si el archivo no sirve."""
    await _actualizar(
        importacion_id,
        tenant_id,
        status=EstadoDeImportacion.PARSEANDO.value,
        started_at=_ahora(),
    )

    try:
        lectura = leer_planilla(contenido)
    except ArchivoIlegible as fallo:
        # Doble red: `registrar()` ya rechaza esto dentro del request. Queda
        # igual porque el archivo puede haber viajado por Redis desde una
        # version anterior del lector, y un worker que revienta con un
        # `ArchivoIlegible` deja la corrida clavada en `parsing`.
        await _marcar_fallida(importacion_id, tenant_id, str(fallo))
        return None

    await _actualizar(
        importacion_id,
        tenant_id,
        status=EstadoDeImportacion.VALIDANDO.value,
        total_rows=len(lectura.filas) + len(lectura.errores),
        error_rows=len(lectura.errores),
        errors=[_a_json(e) for e in lectura.errores],
    )
    return lectura


async def _importar(importacion_id: uuid.UUID, tenant_id: uuid.UUID, lectura: Lectura) -> None:
    """Fase `importing`. Lotes de `TAMANO_DE_LOTE` con commit por lote."""
    async with sesion_de_tenant(tenant_id) as sesion:
        try:
            # La cuota se verifica contra el TOTAL de la planilla y no fila por
            # fila (`RN-ST-13`). Preguntando de a una, una agencia con 78 de 80
            # sube 500 vehiculos, entran 2, y las otras 498 salen como errores
            # individuales — un reporte de 498 lineas para un solo problema.
            limites = PlanLimitsService(sesion)
            limites.registrar(Recurso.VEHICLES, contar_vehiculos)
            await limites.assert_can_add_vehicle(tenant_id, len(lectura.filas))
        except PlanQuotaExceeded as fallo:
            await _marcar_fallida(importacion_id, tenant_id, fallo.detail)
            return

        catalogo = await _catalogo(sesion, tenant_id)

    await _actualizar(importacion_id, tenant_id, status=EstadoDeImportacion.IMPORTANDO.value)

    errores = list(lectura.errores)
    creados = 0

    for desde in range(0, len(lectura.filas), TAMANO_DE_LOTE):
        lote = lectura.filas[desde : desde + TAMANO_DE_LOTE]
        async with sesion_de_tenant(tenant_id) as sesion:
            for fila in lote:
                # `rechazo` y no `fallo`: mas arriba hay un `except ... as
                # fallo`, y Python borra ese nombre al salir del bloque —
                # reusarlo acá compila y confunde al leer.
                rechazo = await _insertar(sesion, tenant_id, fila, catalogo)
                if rechazo is None:
                    creados += 1
                else:
                    errores.append(rechazo)

            # El progreso se actualiza en la MISMA transaccion que el lote: si
            # el commit falla, el contador no queda contando filas que no
            # entraron.
            corrida = await _fila(sesion, importacion_id)
            if corrida is not None:
                corrida.valid_rows = creados
                corrida.error_rows = len(errores)
                corrida.errors = [_a_json(e) for e in errores]

    await _actualizar(
        importacion_id,
        tenant_id,
        status=EstadoDeImportacion.COMPLETADA.value,
        completed_at=_ahora(),
        valid_rows=creados,
        error_rows=len(errores),
        errors=[_a_json(e) for e in errores],
    )


async def _insertar(
    sesion: AsyncSession, tenant_id: uuid.UUID, fila: FilaLeida, catalogo: _Catalogo
) -> ErrorDeFila | None:
    """Una fila. Devuelve el error en vez de levantarlo.

    El SAVEPOINT es lo que permite que una fila mala no se lleve puesto el lote:
    sin el, la primera violacion de constraint aborta la transaccion y las 99
    filas buenas que ya estaban adentro se pierden.
    """
    marca = catalogo.marcas.get(_clave(fila.marca))
    if marca is None:
        return ErrorDeFila(fila.fila, "marca", f"'{fila.marca}' no esta en el catalogo")

    modelo = catalogo.modelos.get((marca, _clave(fila.modelo)))
    if modelo is None:
        return ErrorDeFila(fila.fila, "modelo", f"'{fila.modelo}' no es un modelo de {fila.marca}")

    sucursal = _sucursal(fila, catalogo)
    if isinstance(sucursal, ErrorDeFila):
        return sucursal

    try:
        datos = VehiculoCrear(branch_id=sucursal, brand_id=marca, model_id=modelo, **fila.datos)
    except ValidationError as fallo:
        return ErrorDeFila(fila.fila, _columna_de(fallo), _mensaje_de(fallo))

    try:
        async with sesion.begin_nested():
            sesion.add(
                Vehicle(
                    **datos.model_dump(),
                    tenant_id=tenant_id,
                    status=EstadoDeVehiculo.EN_PREPARACION.value,
                )
            )
            await sesion.flush()
    except IntegrityError:
        # El mensaje NO repite el dominio: es dato que identifica a una persona
        # (Ley 25.326) y este texto termina en la fila de `imports` y en el log.
        #
        # Solo se atrapa `IntegrityError`. Un error de base que NO es de
        # integridad —la conexion se cayo, el disco se lleno— no es un problema
        # de esta fila, y reportarlo como tal esconderia una falla de
        # infraestructura entre 5.000 lineas de reporte. Sube al `except` de
        # `ejecutar_importacion`, que marca la corrida entera como fallida.
        return ErrorDeFila(fila.fila, None, "ya hay un vehiculo cargado con ese dominio o chasis")
    return None


# ── Catalogo y sucursales ───────────────────────────────────────────────────


class _Catalogo:
    """Marcas, modelos y sucursales resueltos UNA vez para toda la planilla.

    Consultarlos por fila serian tres queries x 5.000 filas. Se traen enteros:
    el catalogo del mercado argentino son cientos de filas, no millones.
    """

    def __init__(
        self,
        marcas: dict[str, uuid.UUID],
        modelos: dict[tuple[uuid.UUID, str], uuid.UUID],
        sucursales: dict[str, uuid.UUID],
        sucursal_unica: uuid.UUID | None,
    ) -> None:
        self.marcas = marcas
        self.modelos = modelos
        self.sucursales = sucursales
        self.sucursal_unica = sucursal_unica


async def _catalogo(sesion: AsyncSession, tenant_id: uuid.UUID) -> _Catalogo:
    marcas = {
        _clave(nombre): identificador
        for identificador, nombre in (
            await sesion.execute(select(VehicleBrand.id, VehicleBrand.name))
        ).all()
    }
    modelos = {
        (marca, _clave(nombre)): identificador
        for identificador, marca, nombre in (
            await sesion.execute(select(VehicleModel.id, VehicleModel.brand_id, VehicleModel.name))
        ).all()
    }
    filas = (
        await sesion.execute(
            select(Branch.id, Branch.name).where(
                Branch.tenant_id == tenant_id, Branch.deleted_at.is_(None)
            )
        )
    ).all()
    sucursales = {_clave(nombre): identificador for identificador, nombre in filas}
    unica = filas[0][0] if len(filas) == 1 else None
    return _Catalogo(marcas, modelos, sucursales, unica)


def _sucursal(fila: FilaLeida, catalogo: _Catalogo) -> uuid.UUID | ErrorDeFila:
    """La sucursal de la fila, o la unica de la agencia si no se nombro.

    El default existe porque la mayoria de las agencias tienen una sola boca y
    obligarlas a repetir su nombre en 500 filas es pedir un dato que el sistema
    ya sabe. Con dos o mas, adivinar seria peor que preguntar.
    """
    if fila.sucursal is None:
        if catalogo.sucursal_unica is not None:
            return catalogo.sucursal_unica
        return ErrorDeFila(
            fila.fila, "sucursal", "la agencia tiene varias sucursales: hay que indicar cual"
        )
    encontrada = catalogo.sucursales.get(_clave(fila.sucursal))
    if encontrada is None:
        return ErrorDeFila(fila.fila, "sucursal", f"'{fila.sucursal}' no es una sucursal")
    return encontrada


def _clave(nombre: str) -> str:
    """Nombres del catalogo comparados sin mayusculas ni espacios de sobra.

    `TOYOTA`, ` Toyota ` y `toyota` son la misma marca para quien llena una
    planilla, y rechazar la primera por el case seria correcto y ridiculo.
    """
    return " ".join(nombre.split()).casefold()


# ── Redis: el archivo entre el request y el worker ──────────────────────────


def _clave_redis(tenant_id: uuid.UUID, importacion_id: uuid.UUID) -> str:
    """El tenant va EN LA CLAVE aunque el id ya sea unico.

    No es redundancia util contra colisiones —un UUID no colisiona— sino contra
    un bug futuro: si algun dia alguien construye la clave con un id que no
    verifico, el prefijo del tenant hace que el error sea "no encontrado" y no
    "el archivo de otra agencia".
    """
    return f"import:{tenant_id}:{importacion_id}"


def _redis() -> Redis:
    # `decode_responses=False`: acá viajan BYTES, no texto. Con `True`, Redis
    # intenta decodificar en UTF-8 y una planilla en cp1252 se rompe en el
    # camino — justo la que el lector sabe manejar.
    cliente: Redis = Redis.from_url(get_settings().redis.url, decode_responses=False)
    return cliente


async def _guardar_planilla(
    tenant_id: uuid.UUID, importacion_id: uuid.UUID, contenido: bytes
) -> None:
    cliente = _redis()
    try:
        await cliente.set(_clave_redis(tenant_id, importacion_id), contenido, ex=_TTL_PLANILLA)
    finally:
        await cliente.aclose()


async def _traer_planilla(tenant_id: uuid.UUID, importacion_id: uuid.UUID) -> bytes | None:
    cliente = _redis()
    try:
        valor: bytes | None = await cliente.get(_clave_redis(tenant_id, importacion_id))
        return valor
    finally:
        await cliente.aclose()


async def _borrar_planilla(tenant_id: uuid.UUID, importacion_id: uuid.UUID) -> None:
    """El archivo se borra apenas termina, con exito o sin el.

    Tiene TTL igual: el TTL cubre el caso de que el worker nunca corra. Esperar
    una hora para liberar 10 MB de un trabajo ya terminado seria dejar basura
    en el camino caliente de Redis.
    """
    cliente = _redis()
    try:
        await cliente.delete(_clave_redis(tenant_id, importacion_id))
    finally:
        await cliente.aclose()


# ── Auxiliares ──────────────────────────────────────────────────────────────


async def _fila(sesion: AsyncSession, importacion_id: uuid.UUID) -> Import | None:
    """La corrida, acotada por RLS. No hace falta filtrar por tenant acá.

    Y aun asi el `None` se contempla en cada llamador: si la fila desaparecio
    —borrada, o un tenant equivocado en el mensaje de Celery— la tarea termina
    sin escribir en la de otro.
    """
    corrida: Import | None = await sesion.scalar(select(Import).where(Import.id == importacion_id))
    return corrida


async def _marcar_fallida(importacion_id: uuid.UUID, tenant_id: uuid.UUID, motivo: str) -> None:
    await _actualizar(
        importacion_id,
        tenant_id,
        status=EstadoDeImportacion.FALLIDA.value,
        failure_reason=motivo,
        completed_at=_ahora(),
    )


async def _actualizar(importacion_id: uuid.UUID, tenant_id: uuid.UUID, **campos: Any) -> None:
    """Una transaccion corta que escribe unos campos de la corrida.

    ⚠️ EL `if corrida is None` VIVE ACA Y EN UN SOLO LUGAR. Antes estaba
    repetido en las cinco fases, identico, y cuatro de esas cinco copias no las
    ejercitaba ningun test: cinco ramas defensivas de las que solo una se sabia
    que funcionaba.

    Que la corrida desaparezca a mitad de una importacion es raro —alguien la
    borro, o el mensaje traia el tenant de otra— y aun asi hay que contemplarlo:
    sin el guard, el worker revienta con `AttributeError` sobre `None` y la
    tarea muere sin dejar nada escrito.
    """
    async with sesion_de_tenant(tenant_id) as sesion:
        corrida = await _fila(sesion, importacion_id)
        if corrida is None:
            return
        for nombre, valor in campos.items():
            setattr(corrida, nombre, valor)


def _a_json(error: ErrorDeFila) -> dict[str, Any]:
    return {"fila": error.fila, "columna": error.columna, "mensaje": error.mensaje}


def _columna_de(fallo: ValidationError) -> str | None:
    """El campo que Pydantic rechazo, traducido al nombre de la COLUMNA del CSV.

    Devolver `price_ars` al que llena una planilla que dice `precio_ars` lo
    manda a buscar una columna que no existe.
    """
    ubicacion = fallo.errors()[0]["loc"]
    if not ubicacion:
        return None
    return COLUMNA_DE_CAMPO.get(str(ubicacion[0]))


def _mensaje_de(fallo: ValidationError) -> str:
    return str(fallo.errors()[0]["msg"])


def _ahora() -> dt.datetime:
    return dt.datetime.now(dt.UTC)
