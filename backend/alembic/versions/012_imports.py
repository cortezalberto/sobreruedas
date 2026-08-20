"""imports — el registro de cada importacion masiva de stock

C-17, `T-093`. Es la fila contra la que el frontend hace polling mientras el
worker trabaja (`Flujo 4`, paso 5: cada 2 segundos contra
`GET /api/v1/imports/{id}`).

LAS TRES CAPAS, COMO EN `vehicles`
───────────────────────────────────
`tenant_id NOT NULL` + politica RLS + `FORCE`. El contrato se copia de
`011_vehicles` a proposito en vez de factorizarlo: una migracion es una foto
congelada, y una condicion compartida que alguien edite mas adelante cambiaria
el pasado.

Que esta tabla lleve RLS no es formalidad. `imports.errors` guarda **dominios,
numeros de chasis y precios** de las filas que fallaron — o sea, el stock de la
agencia tal como lo estaba cargando. Ver el reporte de errores de otra agencia
es ver su inventario.

`created_by` NO TIENE FK, Y ESO ES A PROPOSITO
────────────────────────────────────────────────
El modelo de datos (`knowledge-base/04` §317) lo define apuntando a `users`, y
`users` **no existe todavia**: es C-05, que espera a `E-001`.

Las tres salidas posibles eran:

  1. Esperar a C-05 — dejaria C-17 detras de un bloqueante que no es suyo.
  2. Poner la FK igual — la migracion no corre.
  3. Guardar el UUID sin FK y agregar la constraint cuando la tabla exista.

Se toma la 3. Es exactamente el patron expand → migrar → contract de `ADR-025`:
agregar una FK a una columna que ya tiene los valores correctos es aditivo y no
rompe hacia atras. El valor que se guarda es el `sub` del token de Keycloak, que
es el mismo identificador con el que C-05 va a poblar `users.id`.

⚠️ Hasta que esa FK exista, nada garantiza a nivel base que el UUID corresponda
a un usuario real. La garantia es que solo se escribe desde el token.

`status` ES UN ENUM Y NO UN TEXTO LIBRE
────────────────────────────────────────
Los seis valores salen del modelo de datos y del `Flujo 4`. Con `String` el dia
que alguien escriba `"complete"` en vez de `"completed"` el polling del
frontend no termina nunca y no falla nada.

Revision ID: 012
Revises: 011
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "imports"
POLITICA = "imports_aislamiento_por_tenant"

CONDICION = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"

ESTADOS = ("pending", "parsing", "validating", "importing", "completed", "failed")
TIPOS = ("stock",)


def upgrade() -> None:
    for nombre, valores in (
        ("import_status_enum", ESTADOS),
        ("import_type_enum", TIPOS),
    ):
        sa.Enum(*valores, name=nombre).create(op.get_bind(), checkfirst=True)

    estado = postgresql.ENUM(*ESTADOS, name="import_status_enum", create_type=False)
    tipo = postgresql.ENUM(*TIPOS, name="import_type_enum", create_type=False)

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
            sa.ForeignKey("tenants.id", name="fk_imports_tenant"),
            nullable=False,
        ),
        # Un solo valor hoy. Es enum y no texto porque `exportacion contable`
        # (`RN-PF-07`) va a caer en esta misma tabla, y agregar un valor a un
        # enum es aditivo — sacarlo no, por eso no se ponen valores de mas.
        sa.Column("type", tipo, nullable=False, server_default=sa.text("'stock'")),
        sa.Column("source_filename", sa.String(255), nullable=False),
        sa.Column("status", estado, nullable=False, server_default=sa.text("'pending'")),
        # Los tres contadores son NOT NULL con default 0 y no NULL-si-todavia-no:
        # el frontend divide `valid_rows` por `total_rows` para la barra de
        # progreso, y un NULL ahi es una division que revienta en el cliente.
        sa.Column("total_rows", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("valid_rows", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("error_rows", sa.Integer, nullable=False, server_default=sa.text("0")),
        # Sin FK: ver el encabezado. Es el `sub` del token.
        sa.Column("created_by", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        # Lista de `{fila, columna, mensaje}`. JSONB y no una tabla aparte: se
        # lee entera o no se lee, nunca se consulta por adentro, y una fila por
        # error convertiria una planilla mala en 5.000 INSERTs.
        sa.Column("errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("failure_reason", sa.Text, nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("total_rows >= 0", name="ck_imports_total_no_negativo"),
        sa.CheckConstraint("valid_rows >= 0", name="ck_imports_validas_no_negativo"),
        sa.CheckConstraint("error_rows >= 0", name="ck_imports_erroneas_no_negativo"),
    )

    # `tenant_id` primero: es el discriminador por el que filtra toda consulta.
    # `created_at DESC` porque el unico listado que existe es "las ultimas
    # importaciones de esta agencia".
    op.execute(
        f"CREATE INDEX ix_{TABLA}_tenant_id ON {TABLA} (tenant_id, created_at DESC) "
        "WHERE deleted_at IS NULL"
    )

    op.execute(f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY")  # ver el encabezado
    op.execute(f"CREATE POLICY {POLITICA} ON {TABLA} USING ({CONDICION}) WITH CHECK ({CONDICION})")


def downgrade() -> None:
    # migracion-contract: el DROP de abajo destruye datos. Va marcado porque el
    # lint de DDL destructivo lo exige, y es correcto que lo exija: revertir
    # esta migracion borra el historial de importaciones de todas las agencias.
    op.execute(f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}")
    op.drop_table(TABLA)
    for nombre in ("import_status_enum", "import_type_enum"):
        sa.Enum(name=nombre).drop(op.get_bind(), checkfirst=True)
