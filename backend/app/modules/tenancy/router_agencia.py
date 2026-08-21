"""Endpoints de la agencia y sus sucursales — parte de C-05.

QUE ENTRA ACA Y QUE NO, Y POR QUE
──────────────────────────────────
C-05 declara que **nada de su archivo de tareas se implementa antes del
20-ago**, y el motivo esta escrito ahi: `ADR-017` fija los tres valores de
`user_role_enum` condicionado a `E-001`, y si la enmienda se rechaza, quitar un
valor de un enum es una migracion destructiva prohibida en un paso.

Ese motivo alcanza a `users` y NO a esto. `tenants` y `branches` existen desde
C-04, sus migraciones estan aplicadas, y el servicio tiene su cobertura al
100 % — lo unico que faltaba era la puerta HTTP. Ninguno de estos endpoints
toca el catalogo de roles.

Los de `/users` siguen siendo C-05 y siguen esperando.

⚠️ NO HAY `require_permission` TODAVIA
───────────────────────────────────────
Igual que en stock: cualquier usuario autenticado de la agencia puede hacer
todo lo de aca. Cuando `rbac.py` exista hay que colgar:

    tenant:read      en `GET /tenant/me`
    branches:read    en listar y obtener
    branches:write   en crear y dar de baja

`ADR-024` §6 restringe la creacion de sucursales a `manager`. Hoy no se puede
distinguir quien pregunta, asi que la restriccion no esta puesta.

LO QUE FALTA DEL CATALOGO DE ENDPOINTS, Y POR QUE
──────────────────────────────────────────────────
`PATCH /tenant/me` y `PATCH /branches/{id}` estan documentados y **no se
implementan**: el servicio no tiene metodos de edicion, y escribirlos es
decidir que campos de una agencia se pueden cambiar en caliente —el CUIT no, el
slug tampoco sin romper URLs— y eso es una decision de dominio, no un `UPDATE`.
Queda para cuando C-05 se retome entero.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.errors import DomainError
from app.core.rbac import Espacio, require_permission
from app.db.dependencias import SesionDeTenant
from app.modules.tenancy.repository import BranchRepository, TenantRepository
from app.modules.tenancy.schemas import (
    SucursalCrear,
    SucursalEditar,
    SucursalSalida,
    TenantConfigurar,
    TenantSalida,
)
from app.modules.tenancy.service import TenancyService

__all__ = ["router"]

router = APIRouter(prefix="/api/v1", tags=["agencia"])


def _tenant(sesion: SesionDeTenant) -> uuid.UUID:
    """El tenant de la sesion, que lo puso la dependency desde el token.

    Se lee de `sesion.info` y no de un parametro: asi un endpoint no puede
    acotar la consulta a un tenant y leer otro.
    """
    identificador: uuid.UUID = sesion.info["tenant_id"]
    return identificador


@router.get(
    "/tenant/me",
    response_model=TenantSalida,
    summary="La agencia del token",
    description="No recibe id: la agencia es la del token y no hay otra que pedir.",
    dependencies=[Depends(require_permission("tenants:read", espacio=Espacio.TENANT))],
)
async def mi_agencia(sesion: SesionDeTenant) -> TenantSalida:
    """`GET /tenant/me`.

    ⚠️ NO existe `GET /tenant/{id}`, y no es un olvido. Un endpoint que reciba
    el id de la agencia por la ruta invita a probar con el de otra, y aunque el
    aislamiento lo frene, la invitacion no deberia existir. La agencia se lee
    del token o no se lee.
    """
    agencia = await TenantRepository(sesion).obtener(_tenant(sesion))
    if agencia is None:
        # Solo pasa si el token trae un tenant que no existe en la base: token
        # de un entorno contra la base de otro. Es 404 y no 500 — la peticion
        # esta bien formada, el recurso no esta.
        raise _no_encontrada()
    return TenantSalida.model_validate(agencia)


@router.get(
    "/branches",
    response_model=list[SucursalSalida],
    summary="Sucursales",
    dependencies=[Depends(require_permission("branches:read"))],
)
async def listar_sucursales(sesion: SesionDeTenant) -> list[SucursalSalida]:
    sucursales = await BranchRepository(sesion).listar(_tenant(sesion))
    return [SucursalSalida.model_validate(s) for s in sucursales]


@router.get(
    "/branches/{sucursal_id}",
    response_model=SucursalSalida,
    summary="Una sucursal",
    dependencies=[Depends(require_permission("branches:read"))],
)
async def obtener_sucursal(sucursal_id: uuid.UUID, sesion: SesionDeTenant) -> SucursalSalida:
    sucursal = await BranchRepository(sesion).obtener(_tenant(sesion), sucursal_id)
    if sucursal is None:
        raise _no_encontrada()
    return SucursalSalida.model_validate(sucursal)


@router.post(
    "/branches",
    response_model=SucursalSalida,
    status_code=status.HTTP_201_CREATED,
    summary="Abrir una sucursal",
    description=(
        "Verifica la cuota del plan **antes** de crear. Si la agencia llego a su "
        "techo responde **402**, no 403: ningun cambio de rol lo resuelve."
    ),
    dependencies=[Depends(require_permission("branches:create"))],
)
async def crear_sucursal(datos: SucursalCrear, sesion: SesionDeTenant) -> SucursalSalida:
    """El limite de plan se verifica solo.

    `TenancyService.crear_sucursal` llama a `assert_can_add_branch` antes del
    INSERT, asi que este endpoint no repite la regla — y no puede olvidarsela.
    """
    sucursal = await TenancyService(sesion).crear_sucursal(_tenant(sesion), datos)
    return SucursalSalida.model_validate(sucursal)


@router.post(
    "/branches/{sucursal_id}/deactivate",
    response_model=SucursalSalida,
    summary="Dar de baja una sucursal",
    description="Baja recuperable: libera cuota del plan y la fila sobrevive.",
    dependencies=[Depends(require_permission("branches:deactivate"))],
)
async def dar_de_baja_sucursal(sucursal_id: uuid.UUID, sesion: SesionDeTenant) -> SucursalSalida:
    """Traduce "esa sucursal no esta" a 404, que sobre HTTP es lo que es.

    El servicio levanta `DomainError`, y `DomainError` responde 422 — correcto
    para "la regla dice que no", equivocado para "pediste un id que no existe":
    422 manda a revisar el CUERPO de la peticion, y acá el cuerpo esta vacio.

    La traduccion vive en el router y no en el servicio a proposito: el codigo
    HTTP es asunto de la puerta, y el servicio lo usan tambien C-10 (onboarding)
    y los tests, que no hablan HTTP.
    """
    try:
        sucursal = await TenancyService(sesion).dar_de_baja_sucursal(_tenant(sesion), sucursal_id)
    except DomainError as fallo:
        if fallo.code == "sucursal_inexistente":
            raise _no_encontrada() from fallo
        raise
    return SucursalSalida.model_validate(sucursal)


def _no_encontrada() -> HTTPException:
    """404 para "no existe" y para "es de otra agencia", igual que en stock.

    Distinguirlas confirmaria que cierto id existe en otro tenant.
    """
    return HTTPException(status_code=404, detail="no existe")


@router.patch(
    "/tenant/me",
    response_model=TenantSalida,
    summary="Configurar la agencia",
    description=(
        "Ajusta lo que una agencia puede ajustarse a si misma. **No acepta `cuit` ni "
        "`slug`**: son identidad, no configuracion — cambiarlos rompe la facturacion y "
        "las publicaciones ya emitidas."
    ),
    dependencies=[Depends(require_permission("tenants:update"))],
)
async def configurar_agencia(datos: TenantConfigurar, sesion: SesionDeTenant) -> TenantSalida:
    """El tenant sale de la SESION, que lo saco del token — regla dura 1.

    No hay `PATCH /tenants/{id}`: el unico tenant que alguien puede configurar
    es el suyo, y un endpoint que aceptara un id invitaria a probar con el de
    otro. Mismo criterio que `GET /tenant/me`.
    """
    agencia = await TenancyService(sesion).configurar_agencia(_tenant(sesion), datos)
    return TenantSalida.model_validate(agencia)


@router.patch(
    "/branches/{sucursal_id}",
    response_model=SucursalSalida,
    summary="Editar una sucursal",
    description=(
        "No acepta `is_active`: dar de baja tiene su propio endpoint, y mezclarlo aca "
        "dejaria que un cliente cierre una sucursal creyendo que le corrige el telefono."
    ),
    dependencies=[Depends(require_permission("branches:update"))],
)
async def editar_sucursal(
    sucursal_id: uuid.UUID, datos: SucursalEditar, sesion: SesionDeTenant
) -> SucursalSalida:
    # Misma traduccion que en la baja, y por lo mismo: `DomainError` responde
    # 422 —correcto para "la regla dice que no"— y aca el problema es un id que
    # no existe. Un 422 mandaria a revisar el cuerpo, que esta bien.
    try:
        sucursal = await TenancyService(sesion).actualizar_sucursal(
            _tenant(sesion), sucursal_id, datos
        )
    except DomainError as fallo:
        if fallo.code == "sucursal_inexistente":
            raise _no_encontrada() from fallo
        raise
    return SucursalSalida.model_validate(sucursal)
