"""Reglas de negocio de Stock — C-14.

DONDE VIVE CADA GARANTIA
─────────────────────────
  - Formato y rangos          → `schemas.py` (Pydantic, 422)
  - Unicidad y aislamiento    → PostgreSQL (indices, RLS)
  - REGLAS DE NEGOCIO         → acá

La distincion importa: que el año no sea 2050 es validacion de entrada, pero que
un vehiculo no pase de `in_preparation` a `sold` es una regla del dominio, y
tiene que estar donde no dependa de por que camino llego la peticion.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.stock.models import Vehicle
from app.modules.stock.repository import VehicleRepository
from app.modules.stock.schemas import (
    EstadoDeVehiculo,
    FiltrosDeBusqueda,
    VehiculoCambioDeEstado,
    VehiculoCrear,
    es_transicion_valida,
)

__all__ = ["StockService", "TransicionInvalida", "VehiculoDuplicado", "VehiculoNoEncontrado"]


class VehiculoNoEncontrado(DomainError):
    """No existe, o es de otra agencia. Las dos dan **404**.

    Distinguirlas —"no existe" contra "no es tuyo"— le confirmaria a un tenant
    que cierto id existe en otra agencia. Seria una fuga de informacion por el
    codigo de estado, sin devolver un solo dato.

    ⚠️ `status_code` se pisa a 404 EXPLICITAMENTE. `DomainError` trae 422, que
    es correcto para una regla de negocio incumplida y equivocado para un
    recurso ausente. La primera version heredaba el 422 y el docstring decia
    "404": el texto prometia algo que el codigo no hacia, y lo encontro el test
    de aislamiento.
    """

    status_code = 404


class VehiculoDuplicado(DomainError):
    """`RN-ST-01`: el dominio ya esta cargado en esta agencia."""


class TransicionInvalida(DomainError):
    """`RN-ST-05`: ese cambio de estado no esta en la tabla de permitidas."""


class StockService:
    """Operaciones de stock, siempre acotadas a un tenant.

    El `tenant_id` se recibe al construir y viene del token. Ningun metodo lo
    toma por parametro: quien tiene el servicio ya decidio de que agencia habla.
    """

    def __init__(self, sesion: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._sesion = sesion
        self._tenant_id = tenant_id
        self._repositorio = VehicleRepository(sesion, tenant_id)

    async def listar(self, filtros: FiltrosDeBusqueda) -> list[Vehicle]:
        return list(await self._repositorio.listar(filtros))

    async def obtener(self, vehiculo_id: uuid.UUID) -> Vehicle:
        vehiculo = await self._repositorio.obtener(vehiculo_id)
        if vehiculo is None:
            raise VehiculoNoEncontrado("no existe ese vehiculo")
        return vehiculo

    async def crear(self, datos: VehiculoCrear) -> Vehicle:
        """Alta. El estado inicial lo fija la regla, no el cliente (`RN-ST-04`)."""
        if datos.domain_plate is not None and await self._repositorio.existe_dominio(
            datos.domain_plate
        ):
            # El mensaje NO repite el dominio: es dato que identifica a una
            # persona (Ley 25.326) y este texto termina en el log.
            raise VehiculoDuplicado("ya hay un vehiculo cargado con ese dominio")

        vehiculo = Vehicle(
            **datos.model_dump(),
            # El tenant lo pone el servicio con el valor del token. Es el unico
            # lugar del sistema donde se escribe, y no llega por el body: el
            # schema de entrada ni siquiera declara el campo.
            tenant_id=self._tenant_id,
            status=EstadoDeVehiculo.EN_PREPARACION.value,
        )
        self._repositorio.agregar(vehiculo)
        await self._sesion.flush()
        return vehiculo

    async def cambiar_estado(
        self, vehiculo_id: uuid.UUID, cambio: VehiculoCambioDeEstado
    ) -> Vehicle:
        """`RN-ST-05` y `RN-ST-06`.

        La transicion se valida contra el estado ACTUAL, que es el dato que el
        schema no puede conocer. Lo que no esta en la tabla de permitidas se
        rechaza: denegar por defecto.
        """
        vehiculo = await self.obtener(vehiculo_id)
        actual = EstadoDeVehiculo(vehiculo.status)

        if not es_transicion_valida(actual, cambio.status):
            raise TransicionInvalida(
                f"no se puede pasar de '{actual.value}' a '{cambio.status.value}'"
            )

        vehiculo.status = cambio.status.value
        # `RN-ST-06`: archivar setea la fecha de salida. Vender la de venta.
        if cambio.status is EstadoDeVehiculo.VENDIDO:
            vehiculo.sold_at = dt.datetime.now(dt.UTC)

        await self._sesion.flush()
        return vehiculo

    async def dar_de_baja(self, vehiculo_id: uuid.UUID) -> None:
        """Borrado LOGICO (regla dura 3). `db.delete()` esta prohibido.

        ⚠️ `RN-ST-07` (no archivar con leads activos) y `RN-ST-08` (una operacion
        cerrada solo se archiva) NO se verifican todavia: `leads` y `operations`
        son C-16 y C-19. Queda dicho para que no se de por cubierto — hoy esto
        da de baja un vehiculo que podria tener un lead abierto.
        """
        vehiculo = await self.obtener(vehiculo_id)
        vehiculo.deleted_at = dt.datetime.now(dt.UTC)
        await self._sesion.flush()
