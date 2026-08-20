"""Endpoints de identidad — C-05, bloque 5.

`GET /api/v1/auth/me` — `design.md` `D-4`.

NO RECIBE NINGUN PARAMETRO, Y ESO ES EL CONTRATO
──────────────────────────────────────────────────
No hay `GET /auth/{id}` ni `?user_id=`. La identidad sale del token y de ningun
otro lado. Un endpoint que aceptara un id invitaria a probar con el de otro, y
aunque el aislamiento lo frene, la invitacion no deberia existir — el mismo
criterio que `GET /tenant/me` de `router_agencia.py`.

QUE PERMISO EXIGE
──────────────────
`auth:read_me` con alcance `self` ([`ADR-033`](../../../../docs/adr/ADR-033-alcance-self-distinto-de-own.md)).
No hace falta `verificar_alcance`: el recurso ES el sujeto por construccion,
porque el id con el que se busca sale del token. El alcance queda declarado en la
matriz igual, para que la verificacion automatica de rutas lo vea.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import SujetoActual
from app.core.rbac import require_permission
from app.db.dependencias import SesionDeTenant
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import PerfilPropio, SucursalAsignada

__all__ = ["router"]

router = APIRouter(prefix="/api/v1/auth", tags=["identidad"])


def _tenant(sesion: SesionDeTenant) -> uuid.UUID:
    identificador: uuid.UUID = sesion.info["tenant_id"]
    return identificador


@router.get(
    "/me",
    response_model=PerfilPropio,
    summary="Quien soy",
    description=(
        "No recibe id: la identidad es la del token y no hay otra que pedir. "
        "Devuelve lo que el token no dice — nombre, estado y sucursales."
    ),
    dependencies=[Depends(require_permission("auth:read_me"))],
)
async def mi_perfil(sujeto: SujetoActual, sesion: SesionDeTenant) -> PerfilPropio:
    repositorio = UserRepository(sesion, _tenant(sesion))
    persona = await repositorio.obtener(uuid.UUID(sujeto.user_id))

    if persona is None:
        # El token es valido y el espejo no tiene la fila. Pasa cuando alguien
        # existe en Keycloak y todavia no acepto la invitacion, o cuando se usa
        # un token de un entorno contra la base de otro.
        #
        # 404 y no 500: la peticion esta bien formada y el recurso no esta. Y no
        # 403 — no es una cuestion de permisos, y mandarlo a pedir acceso seria
        # mandarlo por el camino equivocado.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no hay un perfil local para esta identidad",
        )

    sucursales = await repositorio.sucursales_de(persona.id)

    return PerfilPropio(
        id=persona.id,
        tenant_id=persona.tenant_id,
        email=persona.email,
        full_name=persona.full_name,
        phone=persona.phone,
        avatar_url=persona.avatar_url,
        # Se leen del ESPEJO y no del token a proposito: el token dice que rol
        # tenia cuando se emitio, y esto dice cual tiene ahora. Si difieren, el
        # que manda para autorizar sigue siendo el token —es lo que `rbac.py`
        # mira— y esta respuesta es lo que la interfaz muestra.
        role=persona.role,
        status=persona.status,
        branches=[
            SucursalAsignada(id=sucursal.id, name=sucursal.name, is_primary=principal)
            for sucursal, principal in sucursales
        ],
    )
