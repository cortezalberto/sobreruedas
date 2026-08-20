"""Modelos de identidad — C-05.

`User`, `UserBranch` y `SuperAdmin`. La forma sale de las migraciones `013`,
`014` y `015`; los desvios respecto de `spec-tecnica` 3.3 estan justificados en
los encabezados de esas migraciones y en `design.md` `D-1`, `D-2`, `D-3`.

`User` ES UN ESPEJO, NO LA FUENTE
──────────────────────────────────
`design.md` `D-1` reparte quien sabe que:

    Contraseña, TOTP, sesiones     Keycloak. Nunca los vemos
    Email, nombre                  Keycloak, COPIADO aca
    Rol, tenant, sucursales        nosotros — Keycloak no sabe que es una sucursal
    Estado del ciclo de vida       nosotros

La copia de email y nombre se desincroniza, y la regla es que **gana Keycloak**:
un espejo que miente sobre a quien pertenece una cuenta es peor que no tenerlo.

`id` ES EL `sub` DEL TOKEN
───────────────────────────
Sin `default`: no lo genera la aplicacion ni la base. Ver el encabezado de la
migracion `014`, donde estan las dos razones —lo que lo hace posible y lo que lo
hace necesario—.

LO QUE ESTAS CLASES NO DECLARAN
────────────────────────────────
Ningun campo de credencial: `password_hash` (`ADR-026`), `mfa_secret` y
`mfa_enabled` (`D-2`). Los dos primeros los vigila el guardian de AST de
`test_arquitectura.py` sobre `app/` entero. El tercero no es una credencial
—es un HECHO de Keycloak— asi que no entra en esa lista y tiene su propio test
sobre estas tablas.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["ESTADOS_USUARIO", "ROLES_DE_TENANT", "SuperAdmin", "User", "UserBranch"]

# Se repiten aca los valores de `core/rbac.py` a proposito: este modulo describe
# la FORMA de la columna y aquel la matriz de permisos. Un test compara los dos
# conjuntos, que es mejor que importar —el modelo de datos no deberia depender
# del modulo de autorizacion para saber que tipo tiene una columna—.
ROLES_DE_TENANT = ("manager", "salesperson", "admin_staff")
ESTADOS_USUARIO = ("invited", "active", "inactive", "suspended")

# `create_type=False`: los tipos los crea la migracion `014`. Sin esto SQLAlchemy
# intentaria crearlos de nuevo al emitir DDL desde los modelos.
_ROL = sa.Enum(*ROLES_DE_TENANT, name="user_role_enum", create_type=False)
_ESTADO = sa.Enum(*ESTADOS_USUARIO, name="user_status_enum", create_type=False)


class User(Base):
    """Una persona de una agencia. Ver el encabezado del modulo."""

    __tablename__ = "users"

    # Sin `default=uuid4`: este id es el `sub` de Keycloak y lo trae quien crea
    # la fila. Poner un default aca invitaria a olvidarse de pasarlo, y el
    # sintoma seria una fila que nunca coincide con ningun token.
    id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False
    )

    email: Mapped[str] = mapped_column(sa.String(254), nullable=False)
    full_name: Mapped[str] = mapped_column(sa.String(180), nullable=False)
    phone: Mapped[str | None] = mapped_column(sa.String(40), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    notification_preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
    )

    # Los enums viajan como `str` en el modelo, igual que en `stock`: el
    # `StrEnum` vive en `schemas.py` y es quien valida el borde.
    role: Mapped[str] = mapped_column(_ROL, nullable=False)
    status: Mapped[str] = mapped_column(_ESTADO, nullable=False)

    last_login_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    # Borrado logico universal (Principio 3). `db.delete()` esta prohibido.
    deleted_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )


class UserBranch(Base):
    """A que sucursales pertenece una persona.

    ⚠️ NO participa de la autorizacion. `ADR-024` §4 es explicito: la tabla
    modela la pertenencia N:M pero **no amplia el alcance**. Un `salesperson` no
    ve los leads de su sucursal por el hecho de compartirla.
    """

    __tablename__ = "user_branches"

    user_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True), primary_key=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True), primary_key=True)
    # Propio, y no derivado de las puntas. Sin el no hay politica RLS posible:
    # ver el encabezado de la migracion `015`.
    tenant_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True), nullable=False)

    is_primary: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_user_branches_user",
        ),
        sa.ForeignKeyConstraint(
            ["branch_id", "tenant_id"],
            ["branches.id", "branches.tenant_id"],
            name="fk_user_branches_branch",
        ),
    )


class SuperAdmin(Base):
    """El rol de plataforma — `ADR-017` §2.

    SIN `tenant_id` y **exenta de RLS**, que es la unica excepcion entre las
    tablas de identidad. Es lo que permite que `users.tenant_id` sea `NOT NULL`:
    si `super_admin` fuera un valor del enum, esa columna tendria que aceptar
    nulos y toda consulta del sistema ganaria un caso que contemplar.

    ⚠️ Que la clase exista NO habilita nada de `/admin/api/v1`. Esos endpoints
    son C-09.
    """

    __tablename__ = "super_admins"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(sa.String(254), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(sa.String(180), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    last_login_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    deleted_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
