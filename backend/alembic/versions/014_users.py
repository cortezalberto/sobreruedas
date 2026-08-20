"""users — el espejo local del usuario de Keycloak

C-05, `T-023`. `ADR-017`, `ADR-026`, `design.md` `D-1`, `D-2`, `D-3`.

`id` ES EL `sub` DE KEYCLOAK, Y NO ES UN ATAJO
───────────────────────────────────────────────
Sin `server_default`: la base no inventa este id. Lo trae el proveedor de
identidad, que es su dueño (`ADR-007`, `ADR-026`).

Lo que lo hace posible es `design.md` `D-5`: la invitacion **crea primero en
Keycloak y despues localmente**, con ese orden elegido para que un fallo caiga
del lado recuperable. Cuando nace esta fila, el `sub` ya existe.

Y lo que lo hace necesario es el alcance `own` de `ADR-024` §4: `verificar_alcance`
compara `assigned_user_id` contra el `sub` del token. Con un id propio ademas del
`sub`, esa comparacion no cerraria nunca —o habria que resolver el espejo en cada
peticion, y `get_current_user` dejaria de salir puro del token—.

La contrapartida asumida: si alguien borra y recrea la cuenta en Keycloak, el
`sub` cambia y aparece una fila nueva. La vieja sobrevive con `deleted_at`
—nunca hay borrado fisico— asi que el historico de quien hizo que no se pierde.

LO QUE ESTA TABLA **NO** TIENE
───────────────────────────────
`password_hash` (`ADR-026`), `mfa_secret` y `mfa_enabled` (`D-2`). Las tres son
de Keycloak. Las dos de MFA son el mismo error que la contraseña, y `IN-06` lo
documento para una y paso de largo por las otras dos: `mfa_secret` es una
credencial, y `mfa_enabled` es un hecho ajeno que se desincroniza en silencio
—alguien activa TOTP y la columna dice `false` para siempre—.

Un test de arquitectura sobre el AST lo hace cumplir del lado del modelo.

DOS COLUMNAS QUE LA SPEC NO TIENE Y `ADR-024` PRESUPONE
────────────────────────────────────────────────────────
`avatar_url` y `notification_preferences` no figuran en
`knowledge-base/04_modelo_de_datos.md` §users, pero `ADR-024` §6 define
`[perfil]` —lo que un usuario puede editarse a si mismo— como *"`full_name`,
`phone`, `avatar_url`, preferencias de notificacion"*. Declarar editable un
campo que no existe deja la matriz apuntando a la nada.

Se crean. Las dos son aditivas y nullables/con default, asi que no rompen a la
version anterior de la aplicacion (regla dura 13). Es un desvio de N1 en favor
de N1 —un ADR contra la spec derivada—, y queda registrado aca y en `rbac.py`.

`user_role_enum` TIENE EXACTAMENTE TRES VALORES
────────────────────────────────────────────────
`ADR-017` §1 cierra `IN-01`. `super_admin` NO esta: vive en su propia tabla
(migracion `013`).

Revision ID: 014
Revises: 013
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "users"
POLITICA = "tenant_isolation"

# Identica, palabra por palabra, a la de `branches` y `vehicles`. Se copia a
# proposito: una migracion es una foto congelada, y una condicion compartida que
# alguien edite mas adelante cambiaria el pasado.
CONDICION = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"

ROLES = ("manager", "salesperson", "admin_staff")
ESTADOS = ("invited", "active", "inactive", "suspended")


def upgrade() -> None:
    # Los enums se crean UNA vez y despues se referencian con
    # `create_type=False`. Sin eso SQLAlchemy los vuelve a crear al construir la
    # tabla y la migracion muere con `DuplicateObjectError`. Mismo patron que
    # `006_tenants` y `011_vehicles` — ver el comentario de aquel.
    sa.Enum(*ROLES, name="user_role_enum").create(op.get_bind(), checkfirst=True)
    sa.Enum(*ESTADOS, name="user_status_enum").create(op.get_bind(), checkfirst=True)
    rol = postgresql.ENUM(*ROLES, name="user_role_enum", create_type=False)
    estado = postgresql.ENUM(*ESTADOS, name="user_status_enum", create_type=False)

    op.create_table(
        TABLA,
        # Sin `server_default`: lo trae Keycloak. Ver el encabezado.
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", name="fk_users_tenant"),
            # NOT NULL es la consecuencia practica de que `super_admin` viva
            # aparte. Si fuera un valor del enum, esto tendria que ser nullable.
            nullable=False,
        ),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("full_name", sa.String(180), nullable=False),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),  # ver encabezado
        sa.Column(
            "notification_preferences",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("role", rol, nullable=False),
        sa.Column("status", estado, nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Unicidad POR AGENCIA e insensible a mayusculas: el mismo email puede ser
    # de dos personas distintas en dos agencias distintas —un contador que
    # atiende a dos clientes—, y `Ana@x.com` no puede convivir con `ana@x.com`
    # en la misma. Parcial por `deleted_at`: una baja libera el email.
    op.execute(
        f"CREATE UNIQUE INDEX ux_{TABLA}_tenant_email ON {TABLA} "
        f"(tenant_id, lower(email)) WHERE deleted_at IS NULL"
    )
    op.create_index(f"ix_{TABLA}_tenant_status", TABLA, ["tenant_id", "status"])

    op.execute(f"ALTER TABLE {TABLA} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLA} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY {POLITICA} ON {TABLA} USING ({CONDICION}) WITH CHECK ({CONDICION})")


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {POLITICA} ON {TABLA}")
    op.drop_index(f"ix_{TABLA}_tenant_status", table_name=TABLA)
    op.execute(f"DROP INDEX IF EXISTS ux_{TABLA}_tenant_email")
    op.drop_table(TABLA)
    sa.Enum(name="user_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role_enum").drop(op.get_bind(), checkfirst=True)
