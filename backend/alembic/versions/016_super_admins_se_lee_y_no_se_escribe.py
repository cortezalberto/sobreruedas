"""super_admins se lee y no se escribe desde el espacio de tenant

Por que existe: al cerrar C-05 aparecio que el rol de aplicacion podia INSERT,
UPDATE y DELETE sobre `super_admins`. No fue una decision — es lo que hereda
toda tabla nueva, porque el init de la base tiene un
`ALTER DEFAULT PRIVILEGES ... GRANT SELECT, INSERT, UPDATE`.

Las otras dos tablas exentas de RLS ya habian recibido este mismo tratamiento:

    plans                    migracion 010
    catalogo de vehiculos    migracion 009
    super_admins             quedo afuera  <- esto

QUE ESTABA ABIERTO, SIN EXAGERARLO NI MINIMIZARLO
──────────────────────────────────────────────────
Escribir en esta tabla **no convierte a nadie en `super_admin`**. El rol de
plataforma se decide por el claim `role` del token, que firma Keycloak
(`rol_de_plataforma` en `core/rbac.py`); una fila nueva sin token que la
respalde no habilita nada.

Lo que si estaba abierto era la INTEGRIDAD: un `UPDATE super_admins SET
deleted_at = now()` daba de baja a los administradores de plataforma, y un
`INSERT` ensuciaba el padron. Ninguna ruta de la aplicacion hace eso hoy — pero
la capa de datos lo permitia, y `ADR-024` §2 dice que los dos espacios no se
tocan.

POR QUE NO SE REVOCA TAMBIEN EL `SELECT`
─────────────────────────────────────────
Porque C-09 va a necesitar leer esta tabla, y decidir hoy con que rol accede el
espacio administrativo seria resolver de paso una decision de arquitectura que
merece su propio ADR. La confidencialidad de un email y un nombre es un riesgo
menor que la integridad del padron, y ningun endpoint la expone.

Se cierra lo que se puede cerrar sin decidir de mas.

POR QUE NO SE USA RLS
──────────────────────
`super_admins` esta en `EXENTAS_DE_RLS` por `ADR-017`: no lleva `tenant_id`, asi
que no hay contra que aislarla. Una politica necesitaria un contexto que esta
tabla no tiene por definicion. Lo que la protege es el GRANT.

COMPATIBILIDAD HACIA ATRAS (regla dura 13)
────────────────────────────────────────────
Un `REVOKE` puede romper la version anterior de la aplicacion si esa version
escribia la tabla. Se reviso `app/` entero: la unica mencion de `super_admins`
fuera de este cambio es la **definicion del modelo** en
`modules/users/models.py`. Ningun servicio, repositorio ni router la escribe.
La version inmediatamente anterior sigue funcionando con esta migracion
aplicada, que es lo que la regla exige.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "super_admins"

# El rol de aplicacion NO se nombra: se llama distinto en desarrollo
# (`mitutu`) que en tests, y hardcodearlo obligaria a esta migracion a conocer
# el entorno donde corre. Misma razon por la que el init no usa `FOR ROLE`.
BENEFICIARIOS = sa.text(
    "SELECT DISTINCT grantee FROM information_schema.role_table_grants "
    "WHERE table_name = :tabla "
    "  AND privilege_type IN ('INSERT', 'UPDATE', 'DELETE') "
    "  AND grantee <> current_user"
)


def upgrade() -> None:
    # migracion-contract: se reviso `app/` entero y nada escribe `super_admins`
    # — la unica mencion fuera de este cambio es la definicion del modelo. La
    # version inmediatamente anterior sigue funcionando con esta migracion
    # aplicada, que es lo que exige la regla dura 13.
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
    dura 3, soft delete universal— asi que devolverlo aca le daria a la
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
