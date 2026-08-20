"""claves de idempotencia

Por que en PostgreSQL y no en Redis (design.md D-5): la idempotencia protege
CREACIONES, y en este dominio eso incluye operaciones de dinero. Redis tiene TTL
nativo y seria mas comodo, pero un Redis que se reinicia pierde las claves, y
perder una clave de idempotencia significa aceptar como nuevo un reintento que
ya se cobro.

`UNIQUE (tenant_id, key)` Y NO `UNIQUE (key)`
────────────────────────────────────────────
La clave la elige el CLIENTE. Dos agencias que usan la misma libreria y la misma
convencion van a generar la misma cadena mas temprano que tarde, y con un unico
global la segunda recibiria la respuesta guardada de la primera: filtracion
entre tenants por la puerta de servicio.

El unico es ademas lo que hace la garantia: dos peticiones concurrentes con la
misma clave chocan contra el indice, y una de las dos pierde. Sin el, dos hilos
podrian mirar "no existe" al mismo tiempo y crear dos recursos.

LA HUELLA DEL CUERPO
────────────────────
Se guarda un hash y no el cuerpo: el cuerpo de una creacion puede tener datos
personales, y esta tabla vive mas que el recurso que creo. Para lo unico que se
necesita es para distinguir "el mismo reintento" de "otra cosa con la misma
clave", y un hash alcanza para eso.

Revision ID: 003
Revises: 002
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "idempotency_keys"
POLITICA = "tenant_isolation"

CONDICION = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        TABLA,
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        # La clave que manda el cliente. Texto y no UUID: la convencion la elige
        # quien consume la API y no hay motivo para imponerle un formato.
        sa.Column("key", sa.Text(), nullable=False),
        # Hash del cuerpo. Ver el encabezado.
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("status_code", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    # El unico ES la garantia, no una optimizacion. Ver el encabezado.
    op.create_unique_constraint(f"uq_{TABLA}_tenant_key", TABLA, ["tenant_id", "key"])

    # Para la tarea periodica de limpieza: sin esto, barrer vencidas recorre la
    # tabla entera justo cuando mas grande es.
    op.create_index(f"ix_{TABLA}_expires_at", TABLA, ["expires_at"])

    op.execute(f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY {POLITICA} ON {TABLA} USING ({CONDICION}) WITH CHECK ({CONDICION})")


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}")
    op.drop_index(f"ix_{TABLA}_expires_at", table_name=TABLA)
    op.drop_constraint(f"uq_{TABLA}_tenant_key", TABLA, type_="unique")
    op.drop_table(TABLA)
