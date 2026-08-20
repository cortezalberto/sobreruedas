"""user_branches — a que sucursales pertenece cada persona

C-05, `T-025`. `design.md` `D-8`.

LA TABLA DE UNION LLEVA SU PROPIO `tenant_id`
──────────────────────────────────────────────
`knowledge-base/04` la define con PK compuesta `(user_id, branch_id)`,
`is_primary` y `created_at`. Nada mas. Aca se le agrega `tenant_id`, y no es
decoracion.

Una tabla de union sin `tenant_id` **no puede tener politica RLS**: la condicion
del sistema entero es `tenant_id = current_setting('app.current_tenant')`, y sin
esa columna no hay contra que compararla. Quedaria fuera del aislamiento por
construccion, y es el agujero clasico — las dos tablas que une estan protegidas,
y el vinculo entre ellas no.

La alternativa seria una politica con subconsulta contra `users`. Se descarta:
cuesta un JOIN en cada fila leida, y sobre todo hace que el aislamiento de esta
tabla dependa del de otra. Tres capas independientes es el punto de la regla
dura 1; encadenarlas las convierte en una.

La redundancia se paga con una constraint: `tenant_id` tiene que coincidir con
el de las dos puntas. Se garantiza con FKs compuestas contra `(id, tenant_id)`
de cada tabla, y por eso hacen falta indices unicos sobre esos pares.

`user_branches` NO PARTICIPA DE LA AUTORIZACION
────────────────────────────────────────────────
`ADR-024` §4 es explicito: la tabla modela la pertenencia N:M pero **no amplia
el alcance**. Un `salesperson` NO ve los leads de su sucursal por el hecho de
compartirla — `own` es `assigned_user_id` y nada mas. Queda escrito aca porque
es exactamente la inferencia que alguien va a hacer al ver esta tabla.

Revision ID: 015
Revises: 014
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "user_branches"
POLITICA = "tenant_isolation"

CONDICION = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"


def upgrade() -> None:
    # Destino de las FKs compuestas de abajo. `UNIQUE (id, tenant_id)` es
    # redundante con la PK —`id` ya es unico— y aun asi hace falta: PostgreSQL
    # exige que la columna destino de una FK tenga un indice unico que la cubra.
    # El gate de DDL destructivo marca `create_unique_constraint` sobre una tabla
    # con datos, y en el caso general tiene razon: el dato que ya escribio la
    # version anterior puede violar la constraint. Acá no puede — `id` es la PK,
    # asi que `(id, tenant_id)` es unico por construccion. Se declara linea a
    # linea, no con `migracion-contract`, para no silenciar el resto del archivo.
    # migracion-segura: `id` ya es la PK de `users`
    op.create_unique_constraint("uq_users_id_tenant", "users", ["id", "tenant_id"])
    # migracion-segura: `id` ya es la PK de `branches`
    op.create_unique_constraint("uq_branches_id_tenant", "branches", ["id", "tenant_id"])

    op.create_table(
        TABLA,
        sa.Column("user_id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("branch_id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Las dos puntas se comparan CON el tenant: asi la fila no puede vincular
        # un usuario de una agencia con una sucursal de otra ni por error de
        # codigo. Es la constraint que paga la redundancia de `tenant_id`.
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

    op.create_index(f"ix_{TABLA}_tenant_id", TABLA, ["tenant_id"])

    # Una sola sucursal principal por persona. Parcial: las no-principales no
    # compiten entre si.
    op.execute(
        f"CREATE UNIQUE INDEX ux_{TABLA}_principal ON {TABLA} (user_id) " f"WHERE is_primary"
    )

    op.execute(f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY {POLITICA} ON {TABLA} USING ({CONDICION}) WITH CHECK ({CONDICION})")


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}")
    op.execute(f"DROP INDEX IF EXISTS ux_{TABLA}_principal")
    op.drop_index(f"ix_{TABLA}_tenant_id", table_name=TABLA)
    op.drop_table(TABLA)
    op.drop_constraint("uq_branches_id_tenant", "branches", type_="unique")
    op.drop_constraint("uq_users_id_tenant", "users", type_="unique")
