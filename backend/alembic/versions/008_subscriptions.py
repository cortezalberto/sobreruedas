"""subscriptions — historico de suscripcion del tenant a planes

Por que existe (C-04): `tenants.plan_id` dice cual es el plan HOY. Esta tabla
dice cual fue y desde cuando, que es lo que hace falta para facturar un mes que
ya paso con el plan que estaba vigente entonces.

`amount_ars` NO ES REDUNDANTE CON `plans.price_ars`
────────────────────────────────────────────────────
Es el precio EFECTIVO de esta suscripcion, que puede diferir del precio de lista
por un descuento historico (spec-tecnica 3.3). Si se leyera el precio desde
`plans`, subir la lista le subiria retroactivamente la factura a todo cliente
con descuento — y a los que ya pagaron.

`mp_subscription_id` NACE VACIA
────────────────────────────────
La integracion con Mercado Pago es de un change posterior. La columna se crea
ahora, nullable, porque agregarla despues cuesta una migracion sobre datos de
facturacion. No la escribe nadie todavia.

RLS COMO EL RESTO
──────────────────
Lleva `tenant_id`, asi que le corresponde el contrato completo: politica,
`FORCE` y la misma condicion literal que `platform_probe` y `branches`. El test
introspectivo que recorre `pg_policies` la exige sin que haya que anotarla en
ningun lado — que es justamente el punto de ese test.

Revision ID: 008
Revises: 007
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "subscriptions"
POLITICA = "tenant_isolation"
ENUM_ESTADO = "subscription_status_enum"
ESTADOS = ("active", "past_due", "cancelled")

CONDICION = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"


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
        sa.Column(
            "tenant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", name="fk_subscriptions_tenant"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("plans.id", name="fk_subscriptions_plan"),
            nullable=False,
        ),
        sa.Column("status", estado, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("mp_subscription_id", sa.String(120), nullable=True),
        sa.Column("amount_ars", sa.Numeric(18, 2), nullable=False),  # ver encabezado
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
        # Un periodo que termina antes de empezar no es un dato raro: es un dato
        # imposible, y deja la facturacion del mes calculando sobre basura.
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_subscriptions_periodo_coherente",
        ),
        sa.CheckConstraint("amount_ars >= 0", name="ck_subscriptions_amount_no_negativo"),
    )

    op.create_index(f"ix_{TABLA}_tenant_id", TABLA, ["tenant_id", "status"])

    op.execute(f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY {POLITICA} ON {TABLA} USING ({CONDICION}) WITH CHECK ({CONDICION})")


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}")
    op.drop_index(f"ix_{TABLA}_tenant_id", table_name=TABLA)
    op.drop_table(TABLA)
    sa.Enum(name=ENUM_ESTADO).drop(op.get_bind(), checkfirst=True)
