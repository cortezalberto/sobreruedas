"""Endpoints de Stock — C-15.

EL PRIMER ROUTER CON DATOS DE UNA AGENCIA
──────────────────────────────────────────
Todo lo anterior era catalogo compartido. Estos endpoints devuelven el stock de
UN tenant, y por eso cada uno pide `SesionDeTenant`: ese unico parametro exige
token, lo valida, saca el tenant del claim y abre la transaccion con el contexto
puesto. No hay forma de escribir acá un endpoint que se olvide de alguno de los
cuatro pasos.

⚠️ LO QUE FALTA, Y NO ES UN OLVIDO
───────────────────────────────────
**No hay `require_permission`.** El bloque 6 de C-02 espera a `E-001`, asi que
hoy CUALQUIER usuario autenticado de la agencia puede hacer todo lo de acá. El
aislamiento entre agencias esta completo; la separacion de roles DENTRO de una
agencia, no.

Concretamente, cuando `rbac.py` exista hay que colgar:

    vehicles:read    en listar y obtener
    vehicles:write   en crear, editar y cambiar de estado
    vehicles:delete  en dar de baja

Y lo mas importante — `RN-ST-12`: **`acquisition_cost_ars` no se devuelve a
nadie todavia**. Estos endpoints responden con `VehiculoSalida`, que no declara
el campo. Cuando haya roles, `manager` y `admin_staff` pasan a recibir
`VehiculoSalidaConCosto` y el resto sigue con este. Denegar por defecto: mientras
no se pueda distinguir quien pregunta, no lo ve nadie.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.db.dependencias import SesionDeTenant
from app.modules.stock.schemas import (
    FiltrosDeBusqueda,
    VehiculoCambioDeEstado,
    VehiculoCrear,
    VehiculoSalida,
)
from app.modules.stock.service import StockService

__all__ = ["router"]

router = APIRouter(prefix="/api/v1/vehicles", tags=["stock"])

# Singleton de modulo y no `= FiltrosDeBusqueda()` en el default del parametro.
# `B008` marca la llamada en el default con razon: se evalua UNA vez al importar,
# asi que un default mutable quedaria compartido entre todas las peticiones. Este
# schema es inmutable en la practica —nadie le escribe— pero el singleton lo
# vuelve explicito en vez de depender de esa costumbre.
SIN_FILTROS = FiltrosDeBusqueda()


def _servicio(sesion: SesionDeTenant) -> StockService:
    """El tenant sale de la sesion, que lo saco del token.

    `sesion.info` lo deja puesto `sesion_de_tenant` al abrir la transaccion, asi
    que el router no tiene que volver a pedir el sujeto — y sobre todo, no tiene
    por donde recibir un tenant distinto.
    """
    return StockService(sesion, sesion.info["tenant_id"])


@router.get("", response_model=list[VehiculoSalida], summary="Listar el stock")
async def listar_vehiculos(
    sesion: SesionDeTenant,
    # `Query()` explicito: sin eso FastAPI leeria el modelo del CUERPO, y un GET
    # con cuerpo es una peticion que ningun cliente HTTP normal manda.
    filtros: Annotated[FiltrosDeBusqueda, Query()] = SIN_FILTROS,
) -> list[VehiculoSalida]:
    vehiculos = await _servicio(sesion).listar(filtros)
    return [VehiculoSalida.model_validate(v) for v in vehiculos]


@router.get("/{vehiculo_id}", response_model=VehiculoSalida, summary="Un vehiculo")
async def obtener_vehiculo(vehiculo_id: uuid.UUID, sesion: SesionDeTenant) -> VehiculoSalida:
    return VehiculoSalida.model_validate(await _servicio(sesion).obtener(vehiculo_id))


@router.post(
    "",
    response_model=VehiculoSalida,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar un vehiculo",
)
async def crear_vehiculo(datos: VehiculoCrear, sesion: SesionDeTenant) -> VehiculoSalida:
    return VehiculoSalida.model_validate(await _servicio(sesion).crear(datos))


@router.post(
    "/{vehiculo_id}/status",
    response_model=VehiculoSalida,
    summary="Cambiar el estado",
    description="Solo las transiciones de `RN-ST-05`. Vender exige razon.",
)
async def cambiar_estado(
    vehiculo_id: uuid.UUID, cambio: VehiculoCambioDeEstado, sesion: SesionDeTenant
) -> VehiculoSalida:
    return VehiculoSalida.model_validate(
        await _servicio(sesion).cambiar_estado(vehiculo_id, cambio)
    )


@router.delete(
    "/{vehiculo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dar de baja",
    description="Borrado logico: la fila sobrevive con `deleted_at` (regla dura 3).",
)
async def dar_de_baja(vehiculo_id: uuid.UUID, sesion: SesionDeTenant) -> None:
    await _servicio(sesion).dar_de_baja(vehiculo_id)
