"""Contratos de entrada y salida del modulo tenancy — C-04.

`tenant_id` NO EXISTE EN NINGUN SCHEMA DE ENTRADA
──────────────────────────────────────────────────
No esta declarado, y ademas `extra="forbid"` rechaza la peticion que lo mande.
Las dos cosas, porque protegen de cosas distintas: no declararlo evita que se
aplique; prohibir el extra hace que el intento sea VISIBLE.

Ignorarlo en silencio —que es el default de Pydantic— tambien cumple la regla
dura 1, pero le devuelve 200 a un cliente que acaba de intentar escribir en
otro tenant y no deja rastro. Con `forbid` queda un 422 con el nombre del campo
en el log. Ver design.md D-10.

El beneficio de arrastre pesa igual: `forbid` atrapa los errores de tipeo. Un
`billing_emial` con `ignore` se descarta sin decir nada y la agencia queda sin
email de facturacion, con la peticion en verde.

LA VALIDACION DEL CUIT VIVE ACA, NO SOLO EN LA BASE
────────────────────────────────────────────────────
El schema normaliza a la forma canonica. Sin eso el UNIQUE de `tenants.cuit` no
sirve: el mismo numero con y sin guiones son dos cadenas distintas y entran las
dos.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validadores_ar import CuitInvalido, normalizar_cuit

__all__ = [
    "SucursalCrear",
    "SucursalSalida",
    "TenantCrear",
    "TenantSalida",
]

# `[a-z0-9-]`, sin extremos en guion. Va en una URL: si acepta mayusculas o
# espacios, la URL se rompe o se duplica (`/Mi-Agencia` y `/mi-agencia`).
_SLUG = Annotated[str, Field(min_length=3, max_length=60, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
_NOMBRE = Annotated[str, Field(min_length=1, max_length=120)]

# Chequeo de FORMA, y nada mas. No es `EmailStr`, y es deliberado.
#
# `EmailStr` arrastra la dependencia `email-validator`, que seria la primera del
# proyecto solo para este campo. Lo que compra es conformidad con RFC 5322 — y
# eso NO es lo que hace falta: una direccion puede ser perfectamente valida
# segun el RFC y no existir, o rebotar, o ser de otra persona.
#
# Una direccion de facturacion se verifica MANDANDO UN MAIL y esperando que
# alguien lo confirme. Ese paso lo tiene el onboarding (C-10), y es el unico que
# prueba algo. Aca alcanza con frenar la basura evidente: sin arroba, sin
# dominio, sin punto en el dominio, con espacios.
#
# Si mas adelante hace falta RFC de verdad, entra la dependencia con un motivo
# concreto en vez de por costumbre.
_EMAIL = Annotated[str, Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]


class _EntradaEstricta(BaseModel):
    """Base de todo schema de ENTRADA. Ver el encabezado del modulo."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TenantCrear(_EntradaEstricta):
    """Alta de una agencia.

    No lleva `status` ni `plan_id`: una agencia nace en trial y sin plan, y eso
    lo decide el servicio. Dejarlos entrar por el body permitiria darse de alta
    directamente en Enterprise.
    """

    name: _NOMBRE
    slug: _SLUG
    cuit: str
    billing_email: _EMAIL
    timezone: str = "America/Argentina/Buenos_Aires"
    locale: str = "es-AR"

    @field_validator("cuit")
    @classmethod
    def _normalizar(cls, valor: str) -> str:
        try:
            return normalizar_cuit(valor)
        except CuitInvalido as exc:
            # Se re-levanta como ValueError para que Pydantic lo reporte en el
            # campo. El mensaje NO repite el valor: un CUIT es dato personal
            # (Ley 25.326) y este texto termina en el log.
            raise ValueError(str(exc)) from exc


class SucursalCrear(_EntradaEstricta):
    """Alta de una sucursal.

    `tenant_id` no esta ni puede estar: lo pone el servicio desde el contexto.
    """

    name: _NOMBRE
    city: Annotated[str, Field(min_length=1, max_length=120)]
    province: Annotated[str, Field(min_length=1, max_length=120)]
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    business_hours: dict[str, Any] | None = None


class _Salida(BaseModel):
    """Base de todo schema de SALIDA. Lee desde el modelo ORM."""

    model_config = ConfigDict(from_attributes=True)


class TenantSalida(_Salida):
    id: uuid.UUID
    name: str
    slug: str
    cuit: str
    billing_email: str
    status: str
    plan_id: uuid.UUID | None
    timezone: str
    locale: str
    created_at: dt.datetime


class SucursalSalida(_Salida):
    """Salida de una sucursal.

    Incluye `tenant_id` a proposito: en SALIDA no es un riesgo —el cliente solo
    recibe lo suyo, que es lo que garantiza la politica RLS— y le sirve para
    correlacionar. Lo que nunca se acepta es en la ENTRADA.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    city: str
    province: str
    address: str | None
    phone: str | None
    is_active: bool
    created_at: dt.datetime
