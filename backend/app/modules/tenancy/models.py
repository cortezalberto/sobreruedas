"""Modelos del dominio de tenancy — C-04.

`Plan`, `Tenant`, `Branch` y `Subscription`. La forma sale de spec-tecnica 3.3,
con los tres desvios registrados en design.md:

  - D-2  `plans.max_whatsapp_messages_month` es columna nueva
  - D-3  se conserva `price_ars`; el precio no sale del mismo documento que los limites
  - D-5  `branches.deleted_at` no esta en la spec y va igual (Principio 3 > N1)

QUE LLEVA `tenant_id` Y QUE NO
──────────────────────────────
`Plan` no: es catalogo compartido. `Tenant` tampoco: su `id` ES el tenant.
`Branch` y `Subscription` si, y por eso estan bajo politica RLS con `FORCE`.
La razon estructural esta en design.md D-1; el test introspectivo que recorre
`pg_policies` lo hace cumplir sin que nadie tenga que acordarse.

`tenant_id` NO SE ESCRIBE DESDE EL BODY
────────────────────────────────────────
Estos modelos lo tienen como columna, pero ningun schema de ENTRADA lo expone
(regla dura 1). Se deriva del token y lo pone el servicio.
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.tipos_pg import PuntoGeografico
from app.db.base import Base

__all__ = ["Branch", "Plan", "Subscription", "Tenant"]

ESTADOS_TENANT = ("active", "suspended", "trial", "cancelled")
ESTADOS_SUSCRIPCION = ("active", "past_due", "cancelled")

# `create_type=False`: los tipos los crean las migraciones 006 y 008. Sin esto
# SQLAlchemy intentaria crearlos de nuevo al emitir DDL desde los modelos.
_TENANT_STATUS = sa.Enum(*ESTADOS_TENANT, name="tenant_status_enum", create_type=False)
_SUBSCRIPTION_STATUS = sa.Enum(
    *ESTADOS_SUSCRIPCION, name="subscription_status_enum", create_type=False
)

_UUID_NUEVO = sa.text("gen_random_uuid()")
_AHORA = sa.text("now()")


class Plan(Base):
    """Catalogo comercial. Compartido entre todos los tenants."""

    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=_UUID_NUEVO
    )
    code: Mapped[str] = mapped_column(sa.String(40), unique=True)
    name: Mapped[str] = mapped_column(sa.String(120))
    price_ars: Mapped[Decimal] = mapped_column(sa.Numeric(18, 2))

    # `0 = ilimitado`, convencion de spec-tecnica 3.3. NO es `NULL`, y no es
    # "cero permitidos": `PlanLimitsService` tiene un test dedicado a que no lo
    # confunda, porque ese error bloquearia entero el plan mas caro sin que
    # nadie lo reporte como un problema de facturacion.
    max_users: Mapped[int] = mapped_column(sa.Integer)
    max_vehicles: Mapped[int] = mapped_column(sa.Integer)
    max_branches: Mapped[int] = mapped_column(sa.Integer)
    max_whatsapp_messages_month: Mapped[int] = mapped_column(sa.Integer)

    modules: Mapped[list[str]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("true"))
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )

    # `0 = ilimitado`. Se nombra la constante en vez de repartir literales `0`
    # por el codigo: `if limite == 0` no dice si el plan no permite nada o si no
    # tiene tope, y son lo opuesto.
    #
    # Hubo aca un metodo `sin_techo(limite)` que NADIE llamaba —`limits.py`
    # compara contra la constante directamente— y la cobertura lo delato. Se
    # borro en vez de escribirle un test: un test para codigo muerto deja el
    # codigo muerto y ademas lo protege.
    SIN_TECHO = 0


class Tenant(Base):
    """La agencia. Unidad raiz de aislamiento: su `id` es el `tenant_id` de todo lo demas."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=_UUID_NUEVO
    )
    name: Mapped[str] = mapped_column(sa.String(120))
    slug: Mapped[str] = mapped_column(sa.String(60), unique=True)
    # Forma canonica `XX-XXXXXXXX-X`. Lo normaliza el servicio ANTES de guardar:
    # sin eso el UNIQUE no sirve y el mismo numero entra dos veces.
    cuit: Mapped[str] = mapped_column(sa.String(13), unique=True)
    billing_email: Mapped[str] = mapped_column(sa.String(254))
    status: Mapped[str] = mapped_column(_TENANT_STATUS)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=True
    )
    trial_ends_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    timezone: Mapped[str] = mapped_column(
        sa.String(50), server_default=sa.text("'America/Argentina/Buenos_Aires'")
    )
    locale: Mapped[str] = mapped_column(sa.String(10), server_default=sa.text("'es-AR'"))
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=sa.text("'{}'::jsonb"))
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )
    # Soft delete (Principio 3). Dar de baja NO libera `slug` ni `cuit`.
    deleted_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )


class Branch(Base):
    """Sucursal. Primera tabla de negocio del sistema bajo politica RLS."""

    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=_UUID_NUEVO
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(sa.String(120))
    address: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    city: Mapped[str] = mapped_column(sa.String(120))
    province: Mapped[str] = mapped_column(sa.String(120))
    phone: Mapped[str | None] = mapped_column(sa.String(40), nullable=True)
    business_hours: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    geo_point: Mapped[str | None] = mapped_column(PuntoGeografico, nullable=True)

    # `is_active` y `deleted_at` NO son lo mismo, y el producto necesita los dos:
    # una sucursal cerrada por refaccion existe y no opera; una cerrada
    # definitivamente dejo de existir. Ver design.md D-5.
    is_active: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("true"))
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )
    deleted_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )


class Subscription(Base):
    """Historico de suscripcion a planes. Una vigente por tenant."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=_UUID_NUEVO
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id"))
    plan_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True), sa.ForeignKey("plans.id"))
    status: Mapped[str] = mapped_column(_SUBSCRIPTION_STATUS)
    start_date: Mapped[dt.date] = mapped_column(sa.Date)
    end_date: Mapped[dt.date | None] = mapped_column(sa.Date, nullable=True)
    mp_subscription_id: Mapped[str | None] = mapped_column(sa.String(120), nullable=True)
    # Precio EFECTIVO, que puede diferir del de lista por descuento historico.
    # Leerlo de `plans` haria que subir la lista suba retroactivamente la
    # factura de todo cliente con descuento.
    amount_ars: Mapped[Decimal] = mapped_column(sa.Numeric(18, 2))
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )
