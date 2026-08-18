"""plans es catalogo: se lee y no se escribe

Por que existe: al escribir la migracion `009` aparecio que el init de la base
tiene un `ALTER DEFAULT PRIVILEGES ... GRANT SELECT, INSERT, UPDATE`, asi que
**toda tabla nueva nace escribible por el rol de aplicacion**. `009` revoco esos
permisos sobre `vehicle_brands` y `vehicle_models`, y al hacerlo dejo a la vista
que `plans` —creada en `005`, catalogo igual que ellas— nunca los perdio.

Nadie los estaba usando. Es un permiso de mas, no un defecto en curso: por eso
esta migracion no arregla un incidente, cierra una puerta.

POR QUE `plans` Y NO `tenants`
───────────────────────────────
Las dos figuran en `EXENTAS_DE_RLS`, pero por motivos distintos y eso cambia
todo:

  - `plans` es un CATALOGO. Lo mismo para todas las agencias, y lo cambia
    Direccion cuando cambia la grilla comercial — no una peticion HTTP.
  - `tenants` es DATO DE NEGOCIO sin politica RLS (design.md D-1 de C-04). La
    aplicacion crea agencias, y C-05 va a necesitar escribirla.

Revocar sobre `tenants` romperia el alta de agencias antes de que exista.

QUE PASA CON EL SEED
─────────────────────
Sigue funcionando. El seed de `005` corre DENTRO de la migracion, o sea con el
rol propietario, que conserva todos sus permisos. Lo que pierde el `INSERT` es
el rol de aplicacion, que nunca lo uso.

Tambien sigue funcionando `test_plan_limits.py`, que inserta un plan a mano:
usa `sesion_de_propietario()`, no la sesion de aplicacion. Verificado antes de
escribir esto, no despues.

COMPATIBILIDAD HACIA ATRAS (regla dura 13)
────────────────────────────────────────────
Un `REVOKE` puede romper la version anterior de la aplicacion si esa version
escribia la tabla. Esta no: se reviso `app/` entero y la unica mencion de `Plan`
fuera de lecturas es la definicion del modelo. La version inmediatamente
anterior sigue funcionando con esta migracion aplicada, que es lo que la regla
exige.

⚠️ El lint de DDL destructivo NO mira los `REVOKE` — cubre `DROP TABLE/COLUMN`,
`RENAME`, `SET NOT NULL` y `ADD CONSTRAINT`. O sea que esta comprobacion la hizo
una persona y no el gate. Queda anotado como hueco del control.

Revision ID: 010
Revises: 009
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "plans"

# El rol de aplicacion NO se nombra: se llama distinto en desarrollo
# (`deruedas`) que en tests (`deruedas_test`), y hardcodearlo obligaria a esta
# migracion a conocer el entorno donde corre. Es la misma razon por la que el
# init de la base no usa `FOR ROLE`.
BENEFICIARIOS = sa.text(
    "SELECT DISTINCT grantee FROM information_schema.role_table_grants "
    "WHERE table_name = :tabla "
    "  AND privilege_type IN ('INSERT', 'UPDATE', 'DELETE') "
    "  AND grantee <> current_user"
)


def upgrade() -> None:
    conexion = op.get_bind()

    for rol in conexion.execute(BENEFICIARIOS, {"tabla": TABLA}).scalars().all():
        # Los identificadores no se pueden bindear como parametros. `TABLA` es
        # una constante de este modulo y `rol` sale del catalogo del sistema.
        conexion.execute(
            sa.text(f'REVOKE INSERT, UPDATE, DELETE ON {TABLA} FROM "{rol}"')  # noqa: S608
        )


def downgrade() -> None:
    """Devuelve exactamente lo que el init de la base otorga por defecto.

    `SELECT, INSERT, UPDATE` y NO `DELETE`: el default nunca dio borrado —regla
    dura 3, soft delete universal— asi que devolverlo acá le daria a la
    aplicacion un permiso que jamas tuvo. Un downgrade que deja el sistema mas
    abierto que antes del upgrade no es una reversion.
    """
    conexion = op.get_bind()

    rol_de_aplicacion = conexion.execute(
        sa.text(
            "SELECT DISTINCT grantee FROM information_schema.role_table_grants "
            "WHERE table_name = :tabla AND privilege_type = 'SELECT' "
            "  AND grantee <> current_user"
        ),
        {"tabla": TABLA},
    ).scalars()

    for rol in rol_de_aplicacion.all():
        conexion.execute(
            sa.text(f'GRANT SELECT, INSERT, UPDATE ON {TABLA} TO "{rol}"')  # noqa: S608
        )
