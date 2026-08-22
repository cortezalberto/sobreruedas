"""outbox_events — el evento y el cambio commitean juntos o no commitea ninguno

[`ADR-036`](../../../docs/adr/ADR-036-outbox-transaccional-para-eventos-de-dominio.md).
C-14, el primer productor de eventos del sistema.

POR QUE UNA TABLA Y NO UN `await publicar(...)`
────────────────────────────────────────────────
`sesion_de_tenant` commitea cuando TERMINA LA PETICION, no cuando el servicio
hace `flush()`. Publicar en el servicio publica antes de que el vehiculo exista:
un constraint que revienta despues, un 500 en el router o una conexion caida
dejan el evento en el stream y ningun vehiculo en la base. Un stream es
append-only — no hay forma de retractarlo.

Con la fila acá, el evento viaja en la misma transaccion que el cambio. Si la
transaccion revierte, se lleva los dos.

LAS TRES CAPAS, COMO EN `vehicles`
───────────────────────────────────
`tenant_id NOT NULL` + politica RLS + `FORCE`. La condicion se copia literal de
`011_vehicles` en vez de factorizarse: una migracion es una foto congelada, y
una condicion compartida que alguien edite mas adelante cambiaria el pasado.

Y acá el aislamiento no es ceremonia. El drenaje NO descubre filas con una
consulta —el servicio anota los sobres pendientes en `sesion.info` y se publican
esos—, justamente porque buscar pendientes obligaria a leer el outbox de todos
los tenants. El rol de aplicacion es `NOBYPASSRLS` por `ADR-020` y no puede, ni
debe poder.

`published_at` NULLABLE, Y ESO ES LO QUE HACE UTIL A LA TABLA
──────────────────────────────────────────────────────────────
Una fila con `published_at IS NULL` es un evento que se escribio y no salio. Hoy
**nadie la reintenta** —el relay necesita el rol cross-tenant que `ADR-036`
difiere junto a `super_admins`— pero el evento no se perdio: queda una lista
consultable de lo que falta publicar, que es exactamente lo que un publish
directo no deja.

SIN `deleted_at`
────────────────
No es un olvido ni una excepcion al principio 3. Esto no es una entidad de
negocio: es una cola. Una fila publicada no se "da de baja", se purga por
antiguedad cuando exista la politica de retencion. Darle soft delete seria
prometer que se puede recuperar algo que nadie va a querer recuperar.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: str | None = "016"
branch_labels: str | None = None
depends_on: str | None = None

TABLA = "outbox_events"
POLITICA = "outbox_events_aislamiento_por_tenant"

# Identica a la de `011_vehicles`. `NULLIF(..., '')` es lo que la hace fallar
# CERRADO: una sesion sin `app.current_tenant` puesto compara contra NULL, y
# `tenant_id = NULL` no es verdadero para ninguna fila. Sin tenant no se ve nada.
CONDICION = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        TABLA,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        # El `event_id` del sobre, generado al registrar y NO al publicar. Es lo
        # que le permite al consumidor reconocer una reentrega: si se generara
        # en el publish, dos intentos del mismo evento llevarian identificadores
        # distintos y la idempotencia del consumidor no los emparejaria.
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        # `dominio.hecho`. No se declara como enum: los tipos los agrega cada
        # modulo y un enum obligaria a una migracion por evento nuevo, que es
        # exactamente la friccion que haria que alguien no publique el evento.
        sa.Column("type", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        # Cuando paso EL HECHO, no cuando se escribio la fila. Es el campo del
        # sobre y viaja tal cual: si se recalculara al publicar, un evento
        # drenado tarde mentiria sobre cuando ocurrio.
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )

    # PARCIAL, sobre los pendientes. El indice que le va a servir al relay el dia
    # que exista, y mientras tanto responde "que no salio" sin recorrer la tabla
    # entera — que crece con cada mutacion del sistema y nunca se achica sola.
    op.execute(
        f"CREATE INDEX ix_{TABLA}_pendientes ON {TABLA} (created_at) " "WHERE published_at IS NULL"
    )

    op.execute(f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY")  # ver el encabezado
    op.execute(f"CREATE POLICY {POLITICA} ON {TABLA} USING ({CONDICION}) WITH CHECK ({CONDICION})")


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}")
    op.drop_table(TABLA)
