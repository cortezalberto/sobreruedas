"""tenants — la agencia, unidad raiz de aislamiento

Por que existe (C-04): es la primera tabla de negocio del sistema y la mas cara
de equivocar. Toda otra tabla del producto la referencia por `tenant_id`, asi
que un error en su forma no se corrige con una migracion: se corrige con ~35.

SIN `tenant_id`, SIN RLS — Y ESO TIENE UN COSTO QUE SE ASUME
─────────────────────────────────────────────────────────────
`tenants.id` ES el tenant, asi que la politica canonica del proyecto
(`tenant_id = current_setting('app.current_tenant')`) no tiene contra que
compararse. La tabla figura en `EXENTAS_DE_RLS` por `RN-MT-09`.

Se evaluo ponerle una politica sobre `id` y se descarto (design.md D-1): crear
una agencia ocurre ANTES de que exista contexto —no hay `app.current_tenant`
para una fila que todavia no existe— y ocurre desde el espacio administrativo,
fuera de todo tenant. Con `FORCE`, esa politica volveria imposible dar de alta
un cliente. Y abrir la politica cuando el contexto esta vacio es exactamente el
agujero que `RN-MT-06` prohibe: convertiria "sin contexto" en "todo permitido".

⚠️ Consecuencia: `tenants` queda protegida por DOS capas en vez de tres. El
hueco lo cubre C-05 al montar el endpoint — toda lectura desde el espacio de
tenant filtra por el `id` del token y nunca por un `id` del path. Es el unico
lugar del sistema donde el aislamiento no tiene red.

`plan_id` NACE NULLABLE, A PROPOSITO
─────────────────────────────────────
`plans` se crea en la migracion anterior, asi que la FK apunta desde el primer
dia y el "NULL temporal" que preveia el roadmap ya no hace falta. Se conserva
nullable por otra razon: un tenant en `status = 'trial'` todavia no eligio plan,
y forzar un plan ficticio para satisfacer un NOT NULL es peor que un NULL que
dice la verdad.

`cuit` SE GUARDA NORMALIZADO
────────────────────────────
La columna es `varchar(13)` y espera la forma canonica `XX-XXXXXXXX-X`
(`core/validadores_ar.normalizar_cuit`). Sin normalizar antes de guardar, el
UNIQUE no sirve: el mismo numero con y sin guiones entra dos veces y son dos
agencias distintas para el sistema, y la misma para AFIP.

Revision ID: 006
Revises: 005
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "tenants"
ENUM_ESTADO = "tenant_status_enum"
ESTADOS = ("active", "suspended", "trial", "cancelled")


def upgrade() -> None:
    # El tipo se crea EXPLICITAMENTE y la columna lo referencia con
    # `create_type=False`. Sin eso SQLAlchemy lo crea una segunda vez al
    # procesar la columna y la migracion muere con DuplicateObjectError.
    sa.Enum(*ESTADOS, name=ENUM_ESTADO).create(op.get_bind(), checkfirst=True)
    estado = postgresql.ENUM(*ESTADOS, name=ENUM_ESTADO, create_type=False)

    op.create_table(
        TABLA,
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(60), nullable=False, unique=True),
        sa.Column("cuit", sa.String(13), nullable=False, unique=True),
        sa.Column("billing_email", sa.String(254), nullable=False),
        sa.Column("status", estado, nullable=False),
        sa.Column(
            "plan_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("plans.id", name="fk_tenants_plan"),
            nullable=True,  # ver el encabezado
        ),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "timezone",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'America/Argentina/Buenos_Aires'"),
        ),
        sa.Column("locale", sa.String(10), nullable=False, server_default=sa.text("'es-AR'")),
        sa.Column(
            "settings",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Soft delete universal (Principio 3). Dar de baja NO libera `slug` ni
        # `cuit`: los UNIQUE son sobre la columna entera, no parciales. Es
        # deliberado — reasignar el CUIT de una agencia dada de baja a otra
        # rompe la trazabilidad fiscal de lo que la primera facturo.
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Listados del backoffice: las agencias vivas por estado. `deleted_at`
    # primero descarta de entrada las dadas de baja, que es el filtro que TODA
    # consulta ordinaria aplica.
    op.create_index(f"ix_{TABLA}_vivos", TABLA, ["deleted_at", "status"])


def downgrade() -> None:
    op.drop_index(f"ix_{TABLA}_vivos", table_name=TABLA)
    op.drop_table(TABLA)
    sa.Enum(name=ENUM_ESTADO).drop(op.get_bind(), checkfirst=True)
