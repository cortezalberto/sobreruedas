"""notifications — el canal in-app

C-06, `T-035`. Las columnas son las que fija `knowledge-base/04_modelo_de_datos.md`
§Notifications y Feature Flags, literal:

    id · tenant_id · user_id · type · payload jsonb · read_at · created_at

NO HAY `title` NI `body`, Y ESO ES UNA DECISION DEL CORPUS
───────────────────────────────────────────────────────────
La fila guarda QUE paso (`type`) y CON QUE (`payload`); el texto lo arma la
plantilla al leer. Tiene dos consecuencias que conviene tener presentes:

  - Corregir una redaccion no es una migracion ni un UPDATE masivo. Con el texto
    congelado en la fila, cada arreglo de una palabra dejaria las notificaciones
    viejas con la version anterior.
  - Un `type` cuya plantilla nadie escribio se ve como texto crudo. Es la
    direccion segura: se nota, y no rompe la pantalla.

`user_id` ES NOT NULL — LA NOTIFICACION ES DE UNA PERSONA
──────────────────────────────────────────────────────────
No hay difusion a toda la agencia. El corpus siempre habla de un destinatario
concreto: *"notifica al vendedor"* (flujo 5), *"el vendedor recibe
notificacion"* (flujo 6). Una columna nullable abriria la puerta al broadcast sin
que nadie lo decida, y el dia que haga falta sera una migracion aditiva.

Y la FK es COMPUESTA `(user_id, tenant_id)`, como en `015_user_branches`: con una
FK sobre `user_id` solo, una notificacion de esta agencia podria apuntar a un
usuario de otra y pasar la politica RLS igual, porque su `tenant_id` seria el
correcto.

SIN `deleted_at`, Y NO ES UNA EXCEPCION AL PRINCIPIO 3
───────────────────────────────────────────────────────
El principio 3 prohibe el borrado FISICO de entidades de negocio. Acá no se
borra nada: una notificacion se LEE (`read_at`) y en algun momento la purgara una
politica de retencion que todavia no existe. Agregar `deleted_at` sin que ninguna
operacion de baja lo escriba seria una columna muerta que promete una
reversibilidad que nadie implemento.

⚠️ **Si alguna vez aparece "descartar notificacion", la columna hace falta.** Se
deja dicho para que esa decision se tome mirando, y no se resuelva con un DELETE.

LAS TRES CAPAS
───────────────
`tenant_id NOT NULL` + politica RLS + `FORCE`, copiadas de `011_vehicles` como en
todas las tablas de negocio. Sin esto una agencia veria las notificaciones de
otra — y una notificacion lleva en su `payload` datos del hecho que la origino.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | None = None
depends_on: str | None = None

TABLA = "notifications"
POLITICA = "notifications_aislamiento_por_tenant"

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
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=120), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # FK COMPUESTA, como en `015_user_branches`. Una FK sobre `user_id` solo
        # dejaria crear una notificacion de esta agencia dirigida a un usuario de
        # OTRA: la fila pasaria la politica RLS —su `tenant_id` es el correcto— y
        # apuntaria afuera igual. Comparando las dos columnas contra
        # `uq_users_id_tenant`, la base lo vuelve imposible.
        #
        # `RESTRICT` porque el espejo local no se borra: `D-6` de C-05 da de baja
        # sin borrar. Si alguna vez alguien intenta el DELETE fisico, que falle acá.
        sa.ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_notifications_user",
            ondelete="RESTRICT",
        ),
    )

    # La consulta que la campanita hace en cada carga de pantalla: las NO leidas
    # de una persona, las mas nuevas primero. Parcial por `read_at IS NULL`
    # porque el indice solo tiene que cubrir lo pendiente — lo leido crece sin
    # techo y nadie lo pide ordenado.
    op.execute(
        f"CREATE INDEX ix_{TABLA}_sin_leer ON {TABLA} (tenant_id, user_id, created_at DESC) "
        "WHERE read_at IS NULL"
    )

    op.execute(f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY {POLITICA} ON {TABLA} USING ({CONDICION}) WITH CHECK ({CONDICION})")


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}")
    op.drop_table(TABLA)
