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
from fastapi.responses import PlainTextResponse

from app.core.auth import SujetoActual
from app.db.dependencias import SesionDeTenant
from app.modules.stock.importacion import PLANTILLA
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


@router.get(
    "/import/template",
    response_class=PlainTextResponse,
    summary="Plantilla CSV de importacion",
    responses={200: {"content": {"text/csv": {}}}},
    description=(
        "La planilla vacia con una fila de ejemplo. Se descarga, se completa en "
        "Excel y se sube a `POST /vehicles/import`."
    ),
)
async def plantilla_de_importacion(_: SujetoActual) -> PlainTextResponse:
    """`T-096`. Va con token aunque no devuelva datos de nadie.

    Podria ser publica —es texto fijo, sin una sola fila de ninguna agencia—
    pero exentar una ruta es una decision de seguridad, y no se toma para
    ahorrarle un header a un endpoint que solo usa alguien ya logueado.

    ⚠️ El parametro `_: SujetoActual` NO es decorativo, y por eso no se puede
    borrar "porque no se usa": es lo unico que hace que FastAPI resuelva la
    identidad antes de entrar acá. Sin el, la ruta queda abierta — la primera
    version de este endpoint no lo tenia, el docstring ya decia "va con token",
    y quien lo detecto fue el gate de `test_auth_rutas.py`, no la lectura.

    Se pide `SujetoActual` y no `SesionDeTenant` porque no hay nada que
    consultar: abrir una transaccion contra PostgreSQL para devolver una
    constante es gasto sin contrapartida.

    ⚠️ La declaracion va DESPUES de `/{vehiculo_id}` en el archivo y aun asi
    resuelve bien: `import/template` son dos segmentos y aquella ruta toma uno.
    Si alguna vez nace `/vehicles/import` a secas, tiene que quedar ARRIBA de
    `/{vehiculo_id}` o se la come el UUID — y el sintoma seria un 422 diciendo
    que "import" no es un UUID valido.

    `Content-Disposition` para que el navegador ofrezca guardar en vez de
    mostrar el CSV como texto plano en una pestaña.
    """
    return PlainTextResponse(
        content=PLANTILLA,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="plantilla-stock.csv"'},
    )
