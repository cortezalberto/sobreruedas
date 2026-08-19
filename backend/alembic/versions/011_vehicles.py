"""vehicles — la entidad central del producto

C-14, `T-071`. Es la tabla que CRM, publicacion, permutas y operaciones
referencian, asi que su forma condiciona a la mitad del sistema.

LAS TRES CAPAS, COMO EN `branches`
───────────────────────────────────
`tenant_id NOT NULL` + politica RLS + `FORCE`. El contrato es identico al de
`007_branches` y se copia a proposito en vez de factorizarlo: una migracion es
una foto congelada, y una condicion compartida que alguien edite mas adelante
cambiaria el pasado.

`FORCE` no es opcional: `ENABLE ROW LEVEL SECURITY` deja las politicas sin
aplicar al DUENO de la tabla, y sin `FORCE` la migracion y cualquier tarea que
corra con ese rol verian todo.

`ADR-031` — LO QUE ESTA MIGRACION NO PUDO ESQUIVAR
───────────────────────────────────────────────────
`domain_plate` es **NULLABLE**, contra lo que dice `spec-tecnica` §3.4. Un 0 km
sin patentar y un usado recien recibido en permuta no tienen dominio, y con
`NOT NULL` la agencia no podria cargarlos. Lo que el `NOT NULL` pretendia
garantizar lo dan dos constraints:

  - `UNIQUE (tenant_id, domain_plate) WHERE deleted_at IS NULL AND domain_plate
    IS NOT NULL` — sigue sin haber dos vehiculos con el mismo dominio.
  - `CHECK (domain_plate IS NOT NULL OR chassis_number IS NOT NULL)` — ninguno
    entra sin alguna forma de identificarse.

El enum de estado tiene los SEIS de `RN-ST-05`. `Pausado` no esta: es el estado
de la publicacion, no del vehiculo.

EL `CHECK` DEL AÑO NO PUEDE SER UNA CONSTANTE
──────────────────────────────────────────────
`RN-ST-03` pide "hasta el año actual + 1", y eso en PostgreSQL exige una
expresion, no un literal: con un literal, el 1 de enero nadie podria cargar el
modelo nuevo. Se usa `EXTRACT(YEAR FROM now())`, que **no es inmutable** — por
eso va como `CHECK` de tabla escrito a mano y no por `sa.CheckConstraint` con
`sa.func`, que intentaria indexarlo.

`acquisition_cost_ars` VIVE ACA Y SE PROTEGE ARRIBA
────────────────────────────────────────────────────
`RN-ST-12` restringe quien lo VE, no donde se guarda. La columna es normal; la
proteccion es de la capa de salida —dos schemas distintos— y de `rbac.py` cuando
exista. Guardarlo en otra tabla para "protegerlo" complicaria toda consulta de
margen sin agregar garantia: el que puede leer una tabla puede leer la otra.

Revision ID: 011
Revises: 010
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "vehicles"
POLITICA = "vehicles_aislamiento_por_tenant"

CONDICION = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"

ESTADOS = (
    "in_preparation",
    "available",
    "reserved",
    "sold",
    "in_workshop",
    "archived",
)
COMBUSTIBLES = ("gasoline", "diesel", "hybrid", "electric", "gnc", "flex")
TRANSMISIONES = ("manual", "automatic", "cvt", "dsg")


def upgrade() -> None:
    # Los enums se crean una vez y se referencian con `create_type=False`. Sin
    # eso SQLAlchemy vuelve a emitir el `CREATE TYPE` al ver la columna, y la
    # migracion muere con "type already exists" — pasó en la `009`.
    for nombre, valores in (
        ("vehicle_status_enum", ESTADOS),
        ("fuel_type_enum", COMBUSTIBLES),
        ("transmission_enum", TRANSMISIONES),
    ):
        sa.Enum(*valores, name=nombre).create(op.get_bind(), checkfirst=True)

    estado = postgresql.ENUM(*ESTADOS, name="vehicle_status_enum", create_type=False)
    combustible = postgresql.ENUM(*COMBUSTIBLES, name="fuel_type_enum", create_type=False)
    transmision = postgresql.ENUM(*TRANSMISIONES, name="transmission_enum", create_type=False)
    # `body_type_enum` ya lo creo la `009` para el catalogo de modelos.
    carroceria = postgresql.ENUM(name="body_type_enum", create_type=False)

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
            sa.ForeignKey("tenants.id", name="fk_vehicles_tenant"),
            nullable=False,
        ),
        # RESTRICT: una sucursal con vehiculos no se borra por accidente.
        sa.Column(
            "branch_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("branches.id", name="fk_vehicles_branch", ondelete="RESTRICT"),
            nullable=False,
        ),
        # SET NULL y no RESTRICT: si el vendedor se va, el vehiculo queda sin
        # asignar — no bloquea la baja de la persona.
        sa.Column("assigned_user_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("domain_plate", sa.String(15), nullable=True),  # ADR-031
        sa.Column(
            "brand_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_brands.id", name="fk_vehicles_brand", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "model_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_models.id", name="fk_vehicles_model", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("year", sa.SmallInteger, nullable=False),
        sa.Column("mileage_km", sa.Integer, nullable=False),
        sa.Column("color", sa.String(60), nullable=False),
        sa.Column("fuel_type", combustible, nullable=False),
        sa.Column("transmission", transmision, nullable=False),
        sa.Column("body_type", carroceria, nullable=False),
        sa.Column("chassis_number", sa.String(30), nullable=True),
        sa.Column("engine_number", sa.String(30), nullable=True),
        sa.Column("price_ars", sa.Numeric(18, 2), nullable=False),
        sa.Column("price_usd", sa.Numeric(18, 2), nullable=True),
        sa.Column("acquisition_cost_ars", sa.Numeric(18, 2), nullable=True),
        sa.Column(
            "status", estado, nullable=False, server_default=sa.text("'in_preparation'")
        ),  # RN-ST-04
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("features", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=True),
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
        # `RN-ST-03`. El techo del año es una expresion y no un literal: con un
        # literal, el 1 de enero nadie podria cargar el modelo nuevo.
        sa.CheckConstraint(
            "year BETWEEN 1950 AND EXTRACT(YEAR FROM now())::int + 1",
            name="ck_vehicles_year",
        ),
        sa.CheckConstraint("mileage_km >= 0", name="ck_vehicles_mileage"),
        sa.CheckConstraint("price_ars > 0", name="ck_vehicles_price"),
        # `ADR-031`: lo que reemplaza al `NOT NULL` del dominio.
        sa.CheckConstraint(
            "domain_plate IS NOT NULL OR chassis_number IS NOT NULL",
            name="ck_vehicles_identificable",
        ),
    )

    # `tenant_id` primero: es el discriminador por el que filtra toda consulta.
    op.create_index(f"ix_{TABLA}_tenant_id", TABLA, ["tenant_id", "deleted_at"])
    op.create_index(f"ix_{TABLA}_estado", TABLA, ["tenant_id", "status"])
    op.create_index(f"ix_{TABLA}_modelo", TABLA, ["tenant_id", "brand_id", "model_id", "year"])

    # Unicidad PARCIAL: solo entre los vivos y solo cuando el valor existe. Un
    # vehiculo dado de baja no bloquea el alta de otro con el mismo dominio, y
    # dos sin patentar no chocan entre si (`RN-ST-01`, `RN-ST-02`).
    op.execute(
        f"CREATE UNIQUE INDEX uq_{TABLA}_dominio ON {TABLA} (tenant_id, domain_plate) "
        "WHERE deleted_at IS NULL AND domain_plate IS NOT NULL"
    )
    op.execute(
        f"CREATE UNIQUE INDEX uq_{TABLA}_chasis ON {TABLA} (tenant_id, chassis_number) "
        "WHERE deleted_at IS NULL AND chassis_number IS NOT NULL"
    )

    op.execute(f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY")  # ver el encabezado
    op.execute(f"CREATE POLICY {POLITICA} ON {TABLA} USING ({CONDICION}) WITH CHECK ({CONDICION})")


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}")
    op.drop_table(TABLA)
    for nombre in ("vehicle_status_enum", "fuel_type_enum", "transmission_enum"):
        sa.Enum(name=nombre).drop(op.get_bind(), checkfirst=True)
