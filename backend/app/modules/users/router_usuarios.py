"""`/api/v1/users` — el padron de la agencia. C-05, tareas 5.9 y 5.11.

UNIFORMEMENTE AUTENTICADO, Y ESO ES UNA DECISION
──────────────────────────────────────────────────
Ningun endpoint de aca es publico. `accept-invitation` vive bajo `/auth`
justamente para que esto valga sin excepciones (`ADR-026` §4): el middleware de
autenticacion necesita una regla, no una lista de casos especiales — y una
excepcion en el middleware de autenticacion es exactamente donde no conviene
tenerlas.

LOS PERMISOS SE TRANSCRIBEN, NO SE INTERPRETAN
────────────────────────────────────────────────
Cada `require_permission` de abajo es una celda de `ADR-024` §6 copiada tal
cual. Donde la matriz distingue por rol, la distincion se lee de la CONCESION y
no del rol: preguntar por el rol aca seria una segunda lectura de la matriz, y
la segunda lectura es donde las dos se despegan. Mismo criterio que
`stock/router.py` con `RN-ST-12`.

    manager        users:read/invite/update/deactivate/assign_branches, alcance ALL
    salesperson    users:read (campos publicos) · users:update (alcance SELF)
    admin_staff    idem salesperson
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.auth import SujetoActual
from app.core.rbac import Concesion, require_permission, verificar_alcance
from app.db.dependencias import SesionDeTenant
from app.modules.users.repository import UserRepository
from app.modules.users.router import KeycloakAdmin, _tenant
from app.modules.users.schemas import (
    AsignarSucursales,
    SucursalAsignada,
    UsuarioCompleto,
    UsuarioEditarPerfil,
    UsuarioInvitar,
    UsuarioPublico,
)
from app.modules.users.service import UserService

__all__ = ["router"]

router = APIRouter(prefix="/api/v1/users", tags=["usuarios"])


def _servicio(sesion: SesionDeTenant, keycloak: KeycloakAdmin) -> UserService:
    """El tenant sale de la SESION, que lo saco del token.

    El router no tiene por donde recibir un tenant distinto — regla dura 1.
    """
    return UserService(sesion, _tenant(sesion), keycloak)


async def _salida(
    persona: object, repositorio: UserRepository, concesion: Concesion
) -> UsuarioPublico:
    """El schema que le corresponde a quien pregunta.

    La eleccion se lee de la CONCESION y no del rol. `rbac.py` ya resolvio que
    campos le tocan a este sujeto; esto solo elige la forma que los lleva.

    Se pregunta por un campo concreto —`email`— y no por `campos is None`: una
    restriccion futura sobre OTRO campo no debe cambiar esta decision.
    """
    identificador: uuid.UUID = persona.id  # type: ignore[attr-defined]
    sucursales = [
        SucursalAsignada(id=s.id, name=s.name, is_primary=p)
        for s, p in await repositorio.sucursales_de(identificador)
    ]

    if concesion.campos is None or "email" in concesion.campos:
        completo = UsuarioCompleto.model_validate(persona)
        return completo.model_copy(update={"branches": sucursales})

    publico = UsuarioPublico.model_validate(persona)
    return publico.model_copy(update={"branches": sucursales})


@router.get("", response_model=None, summary="El padron de la agencia")
async def listar_usuarios(
    sesion: SesionDeTenant,
    concesion: Annotated[Concesion, Depends(require_permission("users:read"))],
) -> list[UsuarioPublico]:
    """Lo que devuelve depende de quien pregunta (`ADR-024` §6).

    Un `manager` ve el padron entero; un `salesperson` ve
    `[id, nombre, rol, sucursales]`. Necesita saber a quien asignarle un lead;
    no necesita el telefono de todos ni quien esta suspendido.
    """
    repositorio = UserRepository(sesion, _tenant(sesion))
    return [await _salida(p, repositorio, concesion) for p in await repositorio.listar()]


@router.get("/{user_id}", response_model=None, summary="Una persona")
async def obtener_usuario(
    user_id: uuid.UUID,
    sesion: SesionDeTenant,
    sujeto: SujetoActual,
    concesion: Annotated[Concesion, Depends(require_permission("users:read"))],
) -> UsuarioPublico:
    repositorio = UserRepository(sesion, _tenant(sesion))
    verificar_alcance(concesion, sujeto=sujeto, recurso_id=user_id)

    persona = await repositorio.obtener(user_id)
    if persona is None:
        from app.modules.users.service import UsuarioNoEncontrado

        raise UsuarioNoEncontrado
    return await _salida(persona, repositorio, concesion)


@router.post(
    "/invitations",
    response_model=UsuarioCompleto,
    status_code=status.HTTP_201_CREATED,
    summary="Invitar a alguien",
    description=(
        "Crea la cuenta en Keycloak y el espejo local en estado `invited`. "
        "**No recibe contrasena** (`ADR-026`) ni `tenant_id` (regla dura 1)."
    ),
    dependencies=[Depends(require_permission("users:invite"))],
)
async def invitar_usuario(
    datos: UsuarioInvitar, sesion: SesionDeTenant, keycloak: KeycloakAdmin
) -> UsuarioCompleto:
    """`D-5`: primero Keycloak, despues local. Ver `service.py`.

    Un rechazo por cuota sale **402 y no 403**: ningun permiso arregla un plan
    lleno, y mandar a pedir permisos seria mandar al lugar equivocado.
    """
    persona = await _servicio(sesion, keycloak).invitar(
        email=datos.email, nombre=datos.full_name, rol=datos.role.value
    )
    return UsuarioCompleto.model_validate(persona)


@router.patch("/{user_id}", response_model=None, summary="Editar el perfil")
async def actualizar_usuario(
    user_id: uuid.UUID,
    datos: UsuarioEditarPerfil,
    sesion: SesionDeTenant,
    sujeto: SujetoActual,
    concesion: Annotated[Concesion, Depends(require_permission("users:update"))],
) -> UsuarioPublico:
    """`[perfil]` de `ADR-024` §6.

    ⚠️ EL ALCANCE ES LO QUE FRENA A UN VENDEDOR DE EDITAR A OTRO. Para
    `salesperson` y `admin_staff` la celda es `SELF`; para `manager`, `ALL`. El
    schema ya impide tocar `role`, `status`, `email` o sucursales — no estan en
    `UsuarioEditarPerfil` y el modelo es `extra="forbid"`.
    """
    repositorio = UserRepository(sesion, _tenant(sesion))
    verificar_alcance(concesion, sujeto=sujeto, recurso_id=user_id)

    persona = await repositorio.obtener(user_id)
    if persona is None:
        from app.modules.users.service import UsuarioNoEncontrado

        raise UsuarioNoEncontrado

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(persona, campo, valor)
    await sesion.flush()

    return await _salida(persona, repositorio, concesion)


@router.post(
    "/{user_id}/deactivation",
    response_model=UsuarioCompleto,
    summary="Suspender",
    description="No puede entrar y **sigue ocupando licencia** del plan (`D-6`).",
    dependencies=[Depends(require_permission("users:deactivate"))],
)
async def desactivar_usuario(
    user_id: uuid.UUID, sesion: SesionDeTenant, keycloak: KeycloakAdmin
) -> UsuarioCompleto:
    persona = await _servicio(sesion, keycloak).desactivar(user_id)
    return UsuarioCompleto.model_validate(persona)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dar de baja",
    description=(
        "Soft delete. Libera cupo del plan y libera el email; en Keycloak "
        "**deshabilita, no borra** (`D-6`)."
    ),
    dependencies=[Depends(require_permission("users:deactivate"))],
)
async def dar_de_baja_usuario(
    user_id: uuid.UUID, sesion: SesionDeTenant, keycloak: KeycloakAdmin
) -> Response:
    await _servicio(sesion, keycloak).dar_de_baja(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{user_id}/branches",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Asignar sucursales",
    description="Reemplaza el conjunto completo. `PUT` y no `POST` porque no suma: reemplaza.",
    dependencies=[Depends(require_permission("users:assign_branches"))],
)
async def asignar_sucursales(
    user_id: uuid.UUID,
    datos: AsignarSucursales,
    sesion: SesionDeTenant,
    keycloak: KeycloakAdmin,
) -> Response:
    await _servicio(sesion, keycloak).asignar_sucursales(
        user_id, [(a.branch_id, a.is_primary) for a in datos.branches]
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
