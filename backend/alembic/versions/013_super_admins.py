"""super_admins — el rol de plataforma, fuera de todo tenant

C-05, `T-024`. `ADR-017` §2 y `design.md` `D-3`.

POR QUE ES UNA TABLA Y NO UN VALOR DEL ENUM
────────────────────────────────────────────
`super_admin` no es un cuarto valor de `user_role_enum`: es un actor de otra
naturaleza. La alternativa —meterlo en el enum con `tenant_id` nullable— rompe
`users.tenant_id NOT NULL`, que `12_seguridad_y_compliance` califica como el
control mas critico del sistema. El costo no seria la migracion: seria que cada
query y cada politica RLS ganan permanentemente un caso nulo que contemplar, y
basta con olvidarlo una vez.

SIN `tenant_id` Y SIN RLS, A PROPOSITO
───────────────────────────────────────
Es la unica tabla de identidad exenta. Ya figuraba en `EXENTAS_DE_RLS` desde
C-02 con el comentario de `ADR-017`, **declarando exenta una tabla que no
existia**. Esta migracion deja de hacer cierta esa mentira por omision.

⚠️ Que la tabla nazca NO habilita nada de `/admin/api/v1`. Los endpoints del
espacio administrativo son C-09. Aca solo se crea la fila para que
`users.tenant_id NOT NULL` de la migracion siguiente sea defendible.

`id` ES EL `sub` DE KEYCLOAK
────────────────────────────
Igual que en `users` — ver el encabezado de `014`, donde esta la justificacion
completa.

Revision ID: 013
Revises: 012
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "super_admins"


def upgrade() -> None:
    op.create_table(
        TABLA,
        # Sin `server_default`: el id lo trae Keycloak, no lo inventa la base.
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("full_name", sa.String(180), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        # Borrado logico, igual que todo el resto (Principio 3).
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # NO se habilita RLS. Ver el encabezado — y la lista `EXENTAS_DE_RLS` de
    # `tests/integration/test_tenant_isolation.py`, que es quien lo verifica.


def downgrade() -> None:
    op.drop_table(TABLA)
