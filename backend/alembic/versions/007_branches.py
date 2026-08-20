"""branches — sucursales del tenant, primera tabla de negocio bajo RLS

Por que existe (C-04): las agencias mono-sucursal tienen una sola fila, y las
multi-sucursal son el diferencial de Enterprise.

ES LA PRIMERA TABLA DE NEGOCIO CON `tenant_id`
───────────────────────────────────────────────
Hasta aca la unica tabla con politica RLS era `platform_probe`, el testigo que
C-02 creo para que los escenarios de `platform/tenant-isolation` tuvieran contra
que correr. `branches` es la primera que ademas contiene datos de un cliente.

El contrato NO cambia: misma condicion, mismo `FORCE`, mismo `NULLIF`. Se copia
literal de `002_tabla_testigo_de_aislamiento` a proposito. Una segunda tabla con
una politica "parecida pero mejorada" es como empiezan las divergencias que
despues nadie sabe si son intencionales.

`FORCE` NO ES OPCIONAL
───────────────────────
`ENABLE ROW LEVEL SECURITY` deja las politicas sin aplicar para el DUENO de la
tabla: la politica existe, `pg_policies` la lista, cualquier auditoria la da por
buena, y no filtra nada para el. Desde `ADR-020` la aplicacion ya no es la
dueña, pero `FORCE` sigue cubriendo a las migraciones y a cualquier tarea que
corra con el propietario. Sacarlo porque "ya no es el agujero" es quedarse con
una sola linea de defensa.

`deleted_at` NO ESTA EN LA SPEC, Y VA IGUAL
────────────────────────────────────────────
`spec-tecnica` 3.3 define `branches` con `is_active` y sin `deleted_at`. No son
lo mismo y el producto necesita los dos: `is_active` es una sucursal que existe
y no esta operando (cerrada por refaccion, reabre en marzo); `deleted_at` es una
que dejo de existir. Sin `deleted_at`, dar de baja obliga a DELETE, que el
Principio 3 prohibe — y una sucursal borrada se lleva por delante el historico
de que vehiculo estuvo donde. Es un desvio de N1 en favor de N0, la unica
direccion permitida por ADR-000. Registrado en design.md D-5.

LA COLUMNA GEOGRAFICA VA CON DDL CRUDO, SIN DEPENDENCIA NUEVA
──────────────────────────────────────────────────────────────
`geo_point` es `geography(Point,4326)` (spec-tecnica 3.3). Mapear ese tipo
desde SQLAlchemy pide `geoalchemy2`, que NO es dependencia de este proyecto —
y nada en C-04 lee ni escribe esa columna: la consume el modulo de mapas, mucho
mas adelante.

Agregar hoy una dependencia que ningun codigo usa tiene costo real y ningun
beneficio: entra al `pip-audit` del pipeline, hay que mantenerla al dia, y su
primer uso queda a Olas de distancia. La columna SI se crea ahora, porque
agregarla despues cuesta una migracion sobre una tabla con datos.

El `ALTER TABLE` va aparte del `create_table` para que la migracion quede
AUTOCONTENIDA: no importa nada de `app/`, que es lo que evita que una migracion
vieja se rompa el dia que el codigo de la aplicacion evolucione debajo de ella.

El lado ORM lo resuelve un tipo propio en `app/core/tipos_pg.py`, para que
`Base.metadata` describa la columna igual que la base y el autogenerate de
Alembic no proponga borrarla.

Revision ID: 007
Revises: 006
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "branches"
POLITICA = "tenant_isolation"

# Identica a la de `platform_probe`. Ver el encabezado: el `NULLIF` convierte
# tanto el parametro sin setear como el seteado en vacio en NULL, y NULL no
# matchea nada — cero filas, que es fallo visible y no silencioso (RN-MT-06).
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
        sa.Column(
            "tenant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", name="fk_branches_tenant"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("province", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("business_hours", sa.dialects.postgresql.JSONB(), nullable=True),
        # `geo_point` NO se declara aca: se agrega abajo con DDL crudo. Ver el
        # bloque "LA COLUMNA GEOGRAFICA" del encabezado.
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),  # ver encabezado
    )

    # `tenant_id` primero: es el discriminador por el que filtra absolutamente
    # toda consulta del sistema. `deleted_at` segundo porque el filtro de soft
    # delete lo aplica el repositorio en TODA consulta ordinaria.
    op.create_index(f"ix_{TABLA}_tenant_id", TABLA, ["tenant_id", "deleted_at"])

    # `ADD COLUMN` de una columna nullable es aditivo: no reescribe la tabla ni
    # rompe a la version anterior de la aplicacion (regla dura 13).
    op.execute(f"ALTER TABLE {TABLA} ADD COLUMN geo_point geography(Point,4326)")

    op.execute(f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY")  # ver el encabezado
    op.execute(f"CREATE POLICY {POLITICA} ON {TABLA} USING ({CONDICION}) WITH CHECK ({CONDICION})")


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}")
    op.drop_index(f"ix_{TABLA}_tenant_id", table_name=TABLA)
    op.drop_table(TABLA)
