"""Contratos de identidad — C-05.

`tenant_id` NO SE DECLARA EN NINGUNA ENTRADA
─────────────────────────────────────────────
Regla dura 1. Se deriva del token y lo pone el servicio. Un schema de entrada
que lo aceptara convertiria el aislamiento en algo que el cliente puede pedir,
y las otras dos capas —RLS y filtro explicito— existen justamente porque una
sola no alcanza.

`extra="forbid"` EN TODA ENTRADA
─────────────────────────────────
`D-10` de C-04. Un campo de mas en el body se rechaza en vez de ignorarse: el
cliente que manda `tenant_id` se entera de que no corresponde, en lugar de creer
que funciono.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "EstadoDeUsuario",
    "PerfilPropio",
    "RolDeUsuario",
    "SucursalAsignada",
    "UsuarioEditarPerfil",
]


class RolDeUsuario(StrEnum):
    """Los tres de `ADR-017`. `super_admin` no esta: vive en otra tabla."""

    MANAGER = "manager"
    SALESPERSON = "salesperson"
    ADMIN_STAFF = "admin_staff"


class EstadoDeUsuario(StrEnum):
    INVITADO = "invited"
    ACTIVO = "active"
    INACTIVO = "inactive"
    SUSPENDIDO = "suspended"


class _EntradaEstricta(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Salida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SucursalAsignada(_Salida):
    """Una sucursal del usuario, con si es la principal.

    `is_primary` viaja aunque el frontend pueda deducirlo comparando contra otro
    campo: deducir una relacion que el backend ya conoce es la clase de logica
    que despues difiere entre la web y el movil.
    """

    id: uuid.UUID
    name: str
    is_primary: bool


class PerfilPropio(_Salida):
    """La respuesta de `GET /api/v1/auth/me` — `design.md` `D-4`.

    Trae **lo que el token no dice**: nombre, estado y sucursales. El `sub`, el
    `tenant_id` y el `role` ya viajan en el token (`ADR-021`) y se devuelven
    igual — no por redundancia, sino para que el frontend tenga UNA sola fuente y
    no tenga que decodificar el JWT para armar su estado.

    ⚠️ No trae nada de MFA. Es un hecho de Keycloak (`D-2`): sale del claim o de
    una consulta puntual, no de una columna nuestra que envejece.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    role: RolDeUsuario
    status: EstadoDeUsuario
    branches: list[SucursalAsignada] = Field(default_factory=list)


class UsuarioEditarPerfil(_EntradaEstricta):
    """`[perfil]` de `ADR-024` §6 — lo unico que alguien puede editarse a si mismo.

    NO estan, y no es un olvido: `role`, `status`, `tenant_id`, `email` y la
    asignacion de sucursales son privilegiados. `email` en particular porque es
    el identificador contra Keycloak (`ADR-007`), y escribirlo desde la API
    abriria un camino sobre la identidad que la regla dura 2 mantiene afuera.

    Que este schema y `CAMPOS_DE_PERFIL` de `rbac.py` digan lo mismo lo verifica
    un test: son dos declaraciones de la misma celda del ADR.
    """

    full_name: str | None = Field(default=None, min_length=1, max_length=180)
    phone: str | None = Field(default=None, max_length=40)
    avatar_url: str | None = Field(default=None, max_length=500)
    notification_preferences: dict[str, bool] | None = None
