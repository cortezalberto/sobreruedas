"""vehicle_status_history — la auditoria que ESC-003 dejo sin tabla

C-14, `T-084`. `StockService.cambiar_estado` muta `vehiculo.status` y emite
`vehicle.status_changed` al outbox desde que existe, pero **no deja rastro en
la base**: el outbox no es la auditoria (`ADR-036` lo describe como el
mecanismo de publicacion, no un registro historico consultable), y hoy si
alguien pregunta "¿quien reservo este auto y cuando?" el sistema no tiene la
respuesta.

Columnas segun `spec-tecnica` §3.4 (N1), que gana sobre `plan-implementacion`
T-084 (N2) — ver `design.md` D-2:

    id · tenant_id · vehicle_id · from_status NULL · to_status NOT NULL
       · changed_by NULL (FK users) · reason TEXT NULL · changed_at NOT NULL

`changed_by`/`changed_at` y NO `changed_by_user_id`/`notes` (N2) ni
`user_id`/`occurred_at` (el schema `HistorialDeEstado` de `schemas.py`, que no
es fuente): `reason` ya existe y ya es donde `POST /vehicles/{id}/status` deja
el motivo, y una segunda columna de texto libre sin regla que las distinga es
garantia de que la mitad de los motivos terminen en la equivocada.

ES APPEND-ONLY POR `REVOKE`, NO POR CONFIANZA (D-1)
──────────────────────────────────────────────────────
El init de la base tiene un `ALTER DEFAULT PRIVILEGES ... GRANT SELECT,
INSERT, UPDATE` que alcanza a TODA tabla nueva, automaticamente — es lo que
`016` descubrio al cerrar C-05, y `009`/`010` antes. Una tabla que nace no es
append-only por defecto: nace escribible y hay que cerrarla.

Un trigger `BEFORE UPDATE ... RAISE` no sirve: lo desactiva quien tenga el
privilegio, y el error llega como excepcion de PL/pgSQL, no como falta de
permiso. El `REVOKE` lo hace cumplir el MOTOR, por la misma via que el resto
del control de acceso, y una auditoria lo ve en `information_schema.role_
table_grants` sin leer codigo.

El rol se identifica consultando el catalogo — `BENEFICIARIOS`, igual que en
`016` — y NUNCA hardcodeado: se llama distinto en desarrollo que en test.

MARCADOR DEL LINT: `# migracion-segura:` POR LINEA, NO `# migracion-contract:`
─────────────────────────────────────────────────────────────────────────────
El de archivo silenciaria TODO este modulo, y este modulo ademas CREA una
tabla — un `drop_column` agregado dentro de seis meses pasaria sin que nadie
lo vea. El de linea exenta solo la operacion de `REVOKE` y deja el gate
encendido para el resto (`test_migraciones_compatibles.py`).

COMPATIBILIDAD HACIA ATRAS (regla dura 13)
────────────────────────────────────────────
Trivial pero hay que decirlo: la version INMEDIATAMENTE ANTERIOR de la
aplicacion no conoce esta tabla, asi que no puede romperse por perder un
privilegio sobre ella. Se reviso `app/` entero: ninguna ruta la escribe,
porque todavia no existe.

FK COMPUESTA EN `changed_by` (D-9)
─────────────────────────────────────
`FOREIGN KEY (changed_by, tenant_id) REFERENCES users (id, tenant_id)`, igual
razonamiento que `018_notifications` y `015_user_branches`: con una FK sobre
`changed_by` solo, una fila de esta agencia podria apuntar a un usuario de
OTRA y pasar la politica RLS igual, porque su `tenant_id` seria el correcto.

Nullable y compuesta conviven con `MATCH SIMPLE` (el default de PostgreSQL):
una FK compuesta con alguna columna en NULL no se verifica, asi que
`changed_by = NULL` (transicion automatica, sin persona detras) pasa sin
necesitar un `tenant_id` nulo, que seria inaceptable.

`RESTRICT` y no `SET NULL`: el espejo local de usuarios no se borra fisico
(`D-6` de C-05 da de baja sin borrar), y si alguna vez alguien intenta el
DELETE fisico, que falle aca. Un historial que pierde a su autor cuando la
persona deja la agencia deja de ser una auditoria.

`vehicle_id` lleva una FK SIMPLE a `vehicles.id` — la spec la declara
"FK NOT NULL" sin composicion, y a diferencia de `users`/`notifications` no
hay hoy un `UNIQUE (id, tenant_id)` sobre `vehicles` contra el cual componerla;
agregarlo esta fuera del alcance de este change (`design.md` no lo pide).

`RESTRICT` en las dos FKs de negocio (`vehicle_id` y `changed_by`): ninguna de
las dos entidades que referencian se borra fisicamente (regla dura 3), asi que
un `ON DELETE` mas permisivo no tiene caso de uso legitimo.

EL INDICE (D-10)
──────────────────
`ix_vehicle_status_history_linea_de_tiempo (tenant_id, vehicle_id, changed_at
DESC)`. `tenant_id` primero por la convencion del proyecto en listados
multi-columna, y porque es la columna del `WHERE` que TODA consulta lleva por
la capa 3 de `ADR-006`. Sin indice sobre `changed_by`: nadie consulta "todo lo
que hizo esta persona" en este change.

Revision ID: 019
Revises: 018
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "vehicle_status_history"
POLITICA = "vehicle_status_history_aislamiento_por_tenant"

CONDICION = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"

# El rol de aplicacion NO se nombra: se llama distinto en desarrollo (`mitutu`)
# que en test (`mitutu` tambien hoy, pero distinto host/puerto/base — el punto
# es que esta migracion no tiene por que saberlo). Es el mismo `BENEFICIARIOS`
# de `016`, acotado a `UPDATE`/`DELETE`: son los dos privilegios que hay que
# revocar para dejar `SELECT, INSERT` — lo unico que el init otorga por
# defecto y que este change SI necesita conservar.
BENEFICIARIOS = sa.text(
    "SELECT DISTINCT grantee FROM information_schema.role_table_grants "
    "WHERE table_name = :tabla "
    "  AND privilege_type IN ('UPDATE', 'DELETE') "
    "  AND grantee <> current_user"
)


def upgrade() -> None:
    estado = postgresql.ENUM(name="vehicle_status_enum", create_type=False)

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
            sa.ForeignKey("tenants.id", name="fk_vehicle_status_history_tenant"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey(
                "vehicles.id", name="fk_vehicle_status_history_vehicle", ondelete="RESTRICT"
            ),
            nullable=False,
        ),
        # NULL es la fila genesis (`D-4`): el alta no tiene estado anterior.
        sa.Column("from_status", estado, nullable=True),
        sa.Column("to_status", estado, nullable=False),
        # Nullable: una transicion automatica no tiene autor (`D-3`, `D-9`).
        sa.Column("changed_by", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # FK COMPUESTA — ver el encabezado, `D-9`. Sin esto una fila de esta
        # agencia podria atribuirse a un usuario de OTRA y pasar la politica
        # RLS igual, porque su `tenant_id` seria el correcto.
        sa.ForeignKeyConstraint(
            ["changed_by", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_vehicle_status_history_autor",
            ondelete="RESTRICT",
        ),
    )

    op.create_index(
        f"ix_{TABLA}_linea_de_tiempo",
        TABLA,
        ["tenant_id", "vehicle_id", sa.text("changed_at DESC")],
    )

    op.execute(f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY")  # ver `011`/`018`
    op.execute(f"CREATE POLICY {POLITICA} ON {TABLA} USING ({CONDICION}) WITH CHECK ({CONDICION})")

    # APPEND-ONLY POR REVOKE, NO POR CONFIANZA — ver el encabezado (`D-1`).
    # `UPDATE`/`DELETE` es lo que el init otorga de mas; `SELECT`/`INSERT`
    # queda intacto porque es lo unico que este change necesita.
    conexion = op.get_bind()
    for rol in conexion.execute(BENEFICIARIOS, {"tabla": TABLA}).scalars().all():
        # Los identificadores no se pueden bindear como parametros. `TABLA` es
        # una constante de este modulo y `rol` sale del catalogo del sistema.
        # migracion-segura: revoca sobre una tabla que NACE en este mismo
        # upgrade — no hay version anterior de la aplicacion que la escriba.
        conexion.execute(sa.text(f'REVOKE UPDATE, DELETE ON {TABLA} FROM "{rol}"'))  # noqa: S608


def downgrade() -> None:
    """Borra lo que este `upgrade` creo.

    No hace falta restituir privilegios antes de borrar: la tabla desaparece
    entera, asi que no queda nada sobre lo que un GRANT de mas importe. La
    danza de "restituir y despues borrar" que hace `016` es para una tabla que
    SOBREVIVE al downgrade — aca no aplica porque la tabla es de este mismo
    archivo.
    """
    op.execute(f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}")
    op.drop_table(TABLA)
