"""Endpoints de Stock — C-15.

EL PRIMER ROUTER CON DATOS DE UNA AGENCIA
──────────────────────────────────────────
Todo lo anterior era catalogo compartido. Estos endpoints devuelven el stock de
UN tenant, y por eso cada uno pide `SesionDeTenant`: ese unico parametro exige
token, lo valida, saca el tenant del claim y abre la transaccion con el contexto
puesto. No hay forma de escribir acá un endpoint que se olvide de alguno de los
cuatro pasos.

LOS PERMISOS YA ESTAN COLGADOS
───────────────────────────────
Cada endpoint declara el suyo, y `rbac.py` es la unica copia de la matriz:

    vehicles:read           listar y obtener
    vehicles:create         crear
    vehicles:change_status  cambiar de estado
    vehicles:archive        dar de baja
    vehicles:import         importacion masiva

⚠️ LOS NOMBRES NO SON LOS QUE ESTE ENCABEZADO ANUNCIABA. Hasta el 22-ago-2026
decia `vehicles:write` para crear, editar y cambiar de estado, y `vehicles:delete`
para la baja — y describia un router sin `require_permission`, que dejo de ser
cierto cuando llego `rbac.py`. La implementacion ademas PARTIO la escritura:
crear, cambiar de estado y archivar son celdas distintas de `ADR-024`, y
`ADR-034` suma la transicion como tercer eje. Un permiso unico de escritura
habria juntado tres decisiones que la matriz separa.

Queda escrito y no borrado porque el plan viejo y el codigo no coincidian, y el
que manda es el codigo.

`RN-ST-12` — EL COSTO SI SE DEVUELVE, Y A QUIEN CORRESPONDE
───────────────────────────────────────────────────────────
Estos endpoints responden `VehiculoSalida` o `VehiculoSalidaConCosto` segun lo
que diga la CONCESION, no el rol: `_salida` lo elige leyendo `concesion.campos`.
Preguntar por el rol acá seria una segunda lectura de la matriz, y la segunda
lectura es donde las dos se despegan.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Response, status
from fastapi.responses import PlainTextResponse

from app.core.auth import SujetoActual
from app.core.idempotency import ejecutar_idempotente
from app.core.rbac import (
    Concesion,
    recortar,
    require_permission,
    verificar_alcance,
    verificar_transicion,
)
from app.db.dependencias import SesionDeTenant
from app.modules.stock.historial import HistorialRepository, VehicleStatusHistory
from app.modules.stock.importacion import PLANTILLA
from app.modules.stock.schemas import (
    FiltrosDeBusqueda,
    HistorialDeEstado,
    VehiculoCambioDeEstado,
    VehiculoCrear,
    VehiculoEditar,
    VehiculoSalida,
    VehiculoSalidaConCosto,
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


def _salida(vehiculo: object, concesion: Concesion) -> VehiculoSalida:
    """El schema que le corresponde a quien pregunta — `RN-ST-12`.

    La eleccion se lee de la concesion y no del rol: preguntar por el rol
    aca seria una SEGUNDA lectura de la matriz, y la segunda lectura es
    donde las dos se despegan. `rbac.py` ya resolvio que campos le tocan a
    este sujeto; esto solo elige la forma que los lleva.

    Se pregunta por el campo concreto y no por `campos is None`: una
    restriccion futura sobre OTRO campo no debe apagar el costo de rebote.
    """
    if concesion.campos is None or "acquisition_cost_ars" in concesion.campos:
        return VehiculoSalidaConCosto.model_validate(vehiculo)
    return VehiculoSalida.model_validate(vehiculo)


def _servicio(sesion: SesionDeTenant) -> StockService:
    """El tenant sale de la sesion, que lo saco del token.

    `sesion.info` lo deja puesto `sesion_de_tenant` al abrir la transaccion, asi
    que el router no tiene que volver a pedir el sujeto — y sobre todo, no tiene
    por donde recibir un tenant distinto.
    """
    return StockService(sesion, sesion.info["tenant_id"])


@router.get(
    "",
    # `response_model=None`: la forma de la respuesta depende de la
    # concesion, y un `response_model` fijo recortaria el costo tambien a
    # quien SI puede verlo.
    response_model=None,
    summary="Listar el stock",
)
async def listar_vehiculos(
    respuesta: Response,
    sesion: SesionDeTenant,
    concesion: Annotated[Concesion, Depends(require_permission("vehicles:read"))],
    # `Query()` explicito: sin eso FastAPI leeria el modelo del CUERPO, y un GET
    # con cuerpo es una peticion que ningun cliente HTTP normal manda.
    #
    # `cursor` y `limit` viajan COMO CAMPOS de `FiltrosDeBusqueda` (ver su
    # docstring) y no como parametros sueltos de esta funcion: agregarlos
    # sueltos hace que FastAPI deje de desarmar el modelo en query params
    # individuales, y `status`, `brand_id`, etc. empiezan a volver `None` en
    # silencio. No es una preferencia de estilo — es una limitacion medida de
    # la version de FastAPI instalada.
    filtros: Annotated[FiltrosDeBusqueda, Query()] = SIN_FILTROS,
) -> list[VehiculoSalida]:
    """`T-080`, `design.md` D-2. El cuerpo sigue siendo un ARRAY de vehiculos
    —no un sobre `{items, next_cursor}`— porque
    `frontend-web/src/lib/api.ts:312` valida `Array.isArray` y un sobre lo
    rompe en tiempo de ejecucion. El cursor de la pagina siguiente viaja en el
    header `X-Next-Cursor`; su ausencia es la ultima pagina.

    `app/core/pagination.py` no se toca (C-02, CRITICO): `filtros.limit`
    llega tal cual a `acotar_tamano` adentro de `paginar`, sin revalidarlo
    acá con otro criterio — pedir mas del maximo se acota, no falla.
    """
    pagina = await _servicio(sesion).listar_paginado(
        filtros, cursor=filtros.cursor, tamano=filtros.limit
    )
    if pagina.cursor_siguiente is not None:
        respuesta.headers["X-Next-Cursor"] = pagina.cursor_siguiente
    return [_salida(v, concesion) for v in pagina.items]


@router.get(
    "/{vehiculo_id}",
    response_model=None,
    summary="Un vehiculo",
)
async def obtener_vehiculo(
    vehiculo_id: uuid.UUID,
    sesion: SesionDeTenant,
    concesion: Annotated[Concesion, Depends(require_permission("vehicles:read"))],
) -> VehiculoSalida:
    return _salida(await _servicio(sesion).obtener(vehiculo_id), concesion)


@router.get(
    "/{vehiculo_id}/history",
    response_model=list[HistorialDeEstado],
    summary="La linea de tiempo de un vehiculo",
    description=(
        "Del cambio mas reciente al mas viejo. Mismo permiso que listar/obtener "
        "(`vehicles:read`), pero SIN el recorte de campos que ese permiso le "
        "aplica al VEHICULO (`D-4`, design.md): es una lista blanca de otro "
        "recurso, y aplicarla acá devolveria registros en blanco en vez de un "
        "error."
    ),
)
async def historial_de_vehiculo(
    vehiculo_id: uuid.UUID,
    sesion: SesionDeTenant,
    _: Annotated[Concesion, Depends(require_permission("vehicles:read"))],
) -> list[VehicleStatusHistory]:
    """`T-085`.

    `_servicio(sesion).obtener(...)` primero, y no directo al repositorio de
    historial: es lo que hace que un vehiculo inexistente O de otra agencia O
    dado de baja de la 404 identica de `VehiculoNoEncontrado` — la misma
    respuesta que ya dan `obtener_vehiculo` y `editar_vehiculo` para los
    mismos tres casos, sin escribir la comprobacion una segunda vez.

    NO se llama a `_salida()` ni a `recortar()`: el conjunto de campos de la
    concesion esta definido sobre el VEHICULO (`RN-ST-12`), y el historial es
    otro recurso — `ADR-024` §3 no le pone restriccion de campos a ninguno de
    los tres roles sobre esta fila.
    """
    await _servicio(sesion).obtener(vehiculo_id)
    return list(
        await HistorialRepository(sesion, sesion.info["tenant_id"]).listar_historial(vehiculo_id)
    )


@router.post(
    "",
    response_model=VehiculoSalida,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar un vehiculo",
    description=(
        "Acepta `Idempotency-Key` (`T-078`): un reintento con la misma clave y el "
        "mismo contenido devuelve el vehiculo ya creado en vez de crear un segundo."
    ),
    dependencies=[Depends(require_permission("vehicles:create"))],
)
async def crear_vehiculo(
    datos: VehiculoCrear,
    sesion: SesionDeTenant,
    # `Header(alias=...)`: HTTP no distingue mayusculas en los nombres de
    # cabecera, pero el nombre del parametro Python si necesita ser un
    # identificador valido. `max_length=255` es el borde de `design.md`
    # D-1 punto 4: la columna `key` de la migracion `003` es `TEXT`, sin
    # techo, y una clave de un megabyte NO puede llegar a la base.
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=1, max_length=255)
    ] = None,
) -> VehiculoSalida:
    """`T-078`, `design.md` D-1. CODIGO QUE TOCA `core/idempotency.py` (CRITICO).

    `sesion` se pasa a `ejecutar_idempotente`: es la MISMA transaccion que ya
    abrio `SesionDeTenant`, y por eso `drenar()` en `db/dependencias.py` sigue
    publicando `vehicle.created` normalmente cuando la peticion termina — la
    opcion descartada en `design.md` (el router pidiendo su propia sesion)
    dejaba de pasar por ahi y el evento se perdia en silencio.

    `cuerpo = datos.model_dump(mode="json")`: el modelo YA VALIDADO, no los
    bytes crudos de la peticion — dos serializaciones distintas del mismo
    contenido (orden de claves, `2000.0` vs `2000.00`) tienen que contar
    como el MISMO reintento, y validar primero normaliza eso.

    La respuesta se guarda como el `dict` que produce `VehiculoSalida`, y
    NUNCA `VehiculoSalidaConCosto`: `_salida()` no interviene acá, a
    proposito (`D-1`, la precondicion del patron —
    `test_post_vehicles_responde_la_misma_forma_para_todos_los_roles`).
    """

    async def crear() -> tuple[dict[str, Any], int]:
        vehiculo = await _servicio(sesion).crear(datos)
        salida = VehiculoSalida.model_validate(vehiculo).model_dump(mode="json")
        return salida, status.HTTP_201_CREATED

    respuesta, _codigo = await ejecutar_idempotente(
        tenant=sesion.info["tenant_id"],
        clave=idempotency_key,
        cuerpo=datos.model_dump(mode="json"),
        crear=crear,
        sesion=sesion,
    )
    return VehiculoSalida.model_validate(respuesta)


@router.patch(
    "/{vehiculo_id}",
    # `response_model=None`, igual que `listar`/`obtener`: la forma depende de
    # la concesion (`RN-ST-12`), y un `response_model` fijo recortaria el
    # costo tambien a quien SI puede verlo.
    response_model=None,
    summary="Editar un vehiculo",
    description=(
        "Edicion PARCIAL (`PATCH`). No admite `status`: el cambio de estado "
        "tiene su propio endpoint porque `RN-ST-05`/`RN-ST-06` lo restringen."
    ),
)
async def editar_vehiculo(
    vehiculo_id: uuid.UUID,
    datos: VehiculoEditar,
    sesion: SesionDeTenant,
    sujeto: SujetoActual,
    concesion: Annotated[Concesion, Depends(require_permission("vehicles:update"))],
) -> VehiculoSalida:
    """`T-079`, `design.md` D-3.

    ⚠️ ASIMETRIA DELIBERADA CON `cambiar_estado`: acá NO se llama a
    `verificar_alcance`. Las tres celdas de `vehicles:update` son `all`
    (`ADR-024` §3) — el `salesperson` es `all` con campos acotados y no `own`,
    porque la autoasignacion (`assigned_user_id`) seria imposible si solo
    pudiera tocar los vehiculos que ya tiene asignados. No es un olvido: es
    que acá no hay alcance que verificar.

    El recorte de campos SI aplica, y se hace ANTES de llamar al servicio:
    `recortar()` es la unica lectura de `ADR-024` (via la concesion que ya
    trajo `rbac.py`), y no hay un `if sujeto.role ==` en este router — esa
    seria la SEGUNDA lectura de la matriz, y la segunda es la que se despega.
    """
    recortado = recortar(datos.model_dump(exclude_unset=True), concesion)
    editado = await _servicio(sesion).editar(
        vehiculo_id,
        VehiculoEditar.model_construct(**recortado),
        autor=uuid.UUID(sujeto.user_id),
    )
    return _salida(editado, concesion)


@router.post(
    "/{vehiculo_id}/status",
    response_model=VehiculoSalida,
    summary="Cambiar el estado",
    description="Solo las transiciones de `RN-ST-05`. Vender exige razon.",
)
async def cambiar_estado(
    vehiculo_id: uuid.UUID,
    cambio: VehiculoCambioDeEstado,
    sesion: SesionDeTenant,
    sujeto: SujetoActual,
    concesion: Annotated[Concesion, Depends(require_permission("vehicles:change_status"))],
) -> VehiculoSalida:
    servicio = _servicio(sesion)
    # El alcance se verifica CON el registro en la mano y no antes:
    # `ADR-024` §4 define `own` sobre el `assigned_user_id` que el
    # vehiculo tiene EN ESTE MOMENTO. Traerlo, comprobar y recien
    # entonces escribir es lo que hace que reasignar quite el acceso.
    vehiculo = await servicio.obtener(vehiculo_id)
    verificar_alcance(concesion, sujeto=sujeto, assigned_user_id=vehiculo.assigned_user_id)
    # El orden es parte de la regla (`ADR-034`): alcance, despues transicion
    # por rol, y recien en el servicio la maquina de estados. Quien no
    # alcanza el registro no se entera de en que estado esta.
    verificar_transicion(concesion, desde=vehiculo.status, hasta=cambio.status.value)
    return VehiculoSalida.model_validate(
        await servicio.cambiar_estado(vehiculo_id, cambio, autor=uuid.UUID(sujeto.user_id))
    )


@router.delete(
    "/{vehiculo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dar de baja",
    description="Borrado logico: la fila sobrevive con `deleted_at` (regla dura 3).",
    dependencies=[Depends(require_permission("vehicles:archive"))],
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
    dependencies=[Depends(require_permission("vehicles:import"))],
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
