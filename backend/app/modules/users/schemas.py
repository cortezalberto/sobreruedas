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
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "AsignacionDeSucursal",
    "AsignarSucursales",
    "EstadoDeUsuario",
    "PerfilPropio",
    "RolDeUsuario",
    "SucursalAsignada",
    "UsuarioCompleto",
    "UsuarioEditarPerfil",
    "UsuarioInvitar",
    "UsuarioPublico",
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


# Chequeo de FORMA y nada mas — el MISMO criterio que `tenancy/schemas.py`, y
# por la misma razon: `EmailStr` arrastraria `email-validator`, que seria la
# primera dependencia del proyecto solo para esto, y lo que compra es
# conformidad con RFC 5322 — que no es lo que hace falta. Una direccion puede
# ser valida segun el RFC y no existir.
#
# Aca ademas hay una segunda prueba, y es la de verdad: Keycloak manda el mail
# de la invitacion. Una direccion que no existe se descubre ahi, no en un regex.
_EMAIL = Annotated[str, Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]


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


class UsuarioInvitar(_EntradaEstricta):
    """`POST /api/v1/users/invitations` — `D-5`.

    ⚠️ NO RECIBE CONTRASEÑA NI `tenant_id`, y las dos ausencias son estructura.
    La contraseña la fija la persona en Keycloak (`ADR-026`); el `tenant_id`
    sale del token y nunca del cuerpo (regla dura 1) — aceptarlo seria darle a
    quien invita la posibilidad de invitar a OTRA agencia.

    Tampoco recibe `status`: quien invita no elige en que estado nace la
    persona. Nace `invited` y la activa el flujo, no el cliente.
    """

    email: _EMAIL
    full_name: str = Field(min_length=1, max_length=180)
    role: RolDeUsuario


class AsignacionDeSucursal(_EntradaEstricta):
    """Una sucursal y si es la principal.

    A lo sumo una principal por persona; lo garantiza el indice
    `ux_user_branches_principal` y lo hace usable el servicio, que desmarca la
    anterior antes de marcar la nueva.
    """

    branch_id: uuid.UUID
    is_primary: bool = False


class AsignarSucursales(_EntradaEstricta):
    """El conjunto COMPLETO de sucursales de una persona.

    Reemplaza, no agrega: mandar una lista parcial creyendo que suma es un error
    facil, y la unica forma de que no sea ambiguo es que el verbo lo diga. Por
    eso es `PUT` y no `POST`.
    """

    branches: list[AsignacionDeSucursal] = Field(default_factory=list)


class UsuarioPublico(_Salida):
    """`[id, nombre, rol, sucursales]` — lo que ve un `salesperson` o un
    `admin_staff` de sus compañeros, segun `CAMPOS_PUBLICOS_DE_USUARIO`.

    ⚠️ NO TRAE `email`, `phone` NI `status`. Un vendedor necesita saber a quien
    asignarle un lead; no necesita el telefono de todos ni quien esta
    suspendido. Que el listado del padron sea distinto segun quien pregunta es
    la misma decision que `RN-ST-12` toma sobre el costo de un vehiculo.
    """

    id: uuid.UUID
    full_name: str
    role: RolDeUsuario
    branches: list[SucursalAsignada] = Field(default_factory=list)


class UsuarioCompleto(UsuarioPublico):
    """Lo que ve un `manager`: el padron entero.

    Hereda de `UsuarioPublico` a proposito — asi es imposible que un campo
    publico exista aca y no alla, que es como los dos schemas se despegan.
    """

    email: str
    phone: str | None = None
    avatar_url: str | None = None
    status: EstadoDeUsuario
