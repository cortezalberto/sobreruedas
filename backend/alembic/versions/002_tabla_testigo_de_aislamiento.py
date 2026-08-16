"""tabla testigo de aislamiento

Por que existe (design.md D-7): C-02 escribe el mecanismo de aislamiento
multi-tenant pero NO crea ninguna tabla de negocio — la primera es la de
`users`, que cae en C-05. Sin una sola tabla con `tenant_id` y politica, los
catorce escenarios de `platform/tenant-isolation` no tendrian contra que
correr, y el control mas critico del sistema se entregaria sin prueba.

`platform_probe` es esa tabla. Queda como testigo permanente: el dia que
alguien rompa el contexto de sesion, los tests de aislamiento fallan aunque
todavia no exista ningun modulo de negocio.

La alternativa —crear tablas de prueba dentro de los tests— se descarto: serian
tablas sin migracion, sin politica revisada en un PR, y el test introspectivo
que recorre `pg_policies` no las veria. Probaria un montaje distinto del que
corre en produccion.

⚠️ `FORCE ROW LEVEL SECURITY` NO ES OPCIONAL
────────────────────────────────────────────
`ENABLE ROW LEVEL SECURITY` deja las politicas SIN aplicar para el DUENO de la
tabla: la politica existe, `pg_policies` la lista, cualquier auditoria la da por
buena — y no filtra nada para el. Es el modo mas silencioso de tener RLS que no
aisla, y `FORCE` es lo que la aplica tambien al dueno.

Cuando se escribio esta migracion, la aplicacion se conectaba con el rol que
creo el esquema, o sea el dueno, y `FORCE` era lo unico que la ponia bajo la
politica. Desde ADR-020 ya no: hay un rol de aplicacion aparte y la propiedad
quedo del lado del que migra.

`FORCE` sigue siendo obligatorio igual. Ahora cubre a las migraciones y a
cualquier tarea que corra con el propietario, que sin el verian todo. Es una
linea de defensa que no cuesta nada mantener puesta, y sacarla porque "ya no es
el agujero" seria quedarse con una sola.

Revision ID: 002
Revises: 001
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "platform_probe"
POLITICA = "tenant_isolation"

# `NULLIF(..., '')` antes del cast: `current_setting(nombre, true)` devuelve
# NULL si el parametro no esta seteado, pero cadena vacia si alguien lo seteo
# en vacio, y '' no castea a uuid — reventaria la consulta en vez de no
# devolver filas. Con NULLIF, los dos casos terminan en NULL, la comparacion da
# NULL, y NULL no matchea: cero filas. Falla visible y no silenciosa (RN-MT-06).
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
        sa.Column("etiqueta", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # `tenant_id` primero en el indice: es el discriminador por el que filtra
    # absolutamente toda consulta del sistema.
    op.create_index(f"ix_{TABLA}_tenant_id", TABLA, ["tenant_id", "created_at"])

    op.execute(f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY")  # ver el encabezado
    op.execute(
        f"CREATE POLICY {POLITICA} ON {TABLA} " f"USING ({CONDICION}) WITH CHECK ({CONDICION})"
    )


def downgrade() -> None:
    # La politica y el RLS se van con la tabla; se borran igual para que el
    # downgrade sea explicito sobre lo que deshace.
    op.execute(f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}")
    op.drop_index(f"ix_{TABLA}_tenant_id", table_name=TABLA)
    op.drop_table(TABLA)
