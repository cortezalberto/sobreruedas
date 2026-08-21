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
from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.config import get_settings
from app.core.auth import SujetoActual
from app.core.rbac import require_permission
from app.db.dependencias import SesionDeTenant
from app.modules.users.keycloak import ClienteDeKeycloak
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import PerfilPropio, SucursalAsignada

__all__ = ["router"]

router = APIRouter(prefix="/api/v1/auth", tags=["identidad"])


async def cliente_de_keycloak() -> AsyncIterator[ClienteDeKeycloak]:
    """El cliente de administracion, armado desde la configuracion.

    Es una dependencia y no un singleton de modulo para que los tests puedan
    sustituirlo con `dependency_overrides` — la alternativa seria levantar un
    Keycloak entero para probar que el logout llama a Keycloak, que es probar
    el sistema de otro.

    El `AsyncClient` se cierra al terminar la peticion: sin eso, cada logout
    filtraria una conexion.
    """
    ajustes = get_settings().keycloak
    async with ClienteDeKeycloak(
        httpx.AsyncClient(base_url=ajustes.url, timeout=5.0),
        realm=ajustes.realm,
        client_id=ajustes.client_id,
        client_secret=ajustes.client_secret.get_secret_value(),
    ) as admin:
        yield admin


KeycloakAdmin = Annotated[ClienteDeKeycloak, Depends(cliente_de_keycloak)]


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

    # `D-1`: Keycloak es dueño del email y acá es donde el espejo se pone al día.
    #
    # El diseño decía "en cada request, `get_current_user` compara". No se hace
    # ahí: `get_current_user` solo verifica la firma y no toca la base, así que
    # cumplirlo al pie le agregaría una sesión y un SELECT a CADA request del
    # sistema —incluidas las que no miran `users`—. Este endpoint ya tiene la
    # fila en la mano, así que el mismo efecto cuesta cero.
    #
    # Lo que se pierde, y queda dicho: el espejo de alguien que nunca abre su
    # perfil sigue viejo para un listado ajeno.
    await repositorio.corregir_email(persona, sujeto.email)

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


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesion",
    description=(
        "Invalida la sesion en Keycloak. **El access token ya emitido sigue siendo valido "
        "hasta que venza** (hasta 15 minutos): es el comportamiento estandar de OIDC con "
        "tokens de vida corta, y esta asumido en `design.md` D-4."
    ),
    dependencies=[Depends(require_permission("auth:logout"))],
)
async def cerrar_sesion(sujeto: SujetoActual, keycloak: KeycloakAdmin) -> Response:
    """`D-4`. Cierra la sesion en Keycloak y NO guarda nada local.

    No hay lista de tokens revocados nuestra. Un access token vive 15 minutos y
    mantener una denylist propia seria reimplementar parte de OIDC — con el
    costo de que ese estado hay que replicarlo, expirarlo y consultarlo en cada
    request.

    ⚠️ EL SUJETO SALE DEL TOKEN, igual que en `/me`. No recibe un id: un
    `logout?user_id=...` seria un boton para tirar la sesion de otro.
    """
    await keycloak.cerrar_sesion(sujeto.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
