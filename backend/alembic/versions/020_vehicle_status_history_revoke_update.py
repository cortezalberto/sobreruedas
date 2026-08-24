"""vehicle_status_history — el contract que cierra el append-only (D-1)

C-14. Segunda mitad del par expand/contract descripto en
`019_vehicle_status_history.py` §"EN DOS DESPLIEGUES" (regla dura 13,
`ADR-025`). Esta migracion revoca `UPDATE` sobre `vehicle_status_history`,
que `019` dejo otorgado a proposito para no romper el gate `migraciones-
compatibles` (que corre la suite del commit ANTERIOR contra el esquema
NUEVO, y esa suite anterior a `019` no conocia `SIN_UPDATE_A_PROPOSITO` en
`test_permisos.py`).

POR QUE ES SEGURO REVOCAR AHORA
─────────────────────────────────
La version INMEDIATAMENTE ANTERIOR de la aplicacion (el commit de `019`,
que ya fusiono a `main`) SI conoce esta tabla y SI podria en teoria emitir
un `UPDATE` sobre ella con las credenciales de la aplicacion — a diferencia
de lo que paso con `019`, donde la tabla nacia en ese mismo `upgrade` y
ninguna version anterior podia haberla escrito nunca. La diferencia real
que hace esto seguro no es esa: es que esa version anterior YA TRAE, en su
propio `test_permisos.py`, la excepcion declarada `SIN_UPDATE_A_PROPOSITO
= {"vehicle_status_history"}` (ver el comentario ahi, y `019` §"EN DOS
DESPLIEGUES"). El gate `migraciones-compatibles` corre exactamente esa
suite contra el esquema con este `REVOKE` aplicado, y esa suite ya sabe que
UPDATE ausente en esta tabla es intencional — no hay falso positivo posible
esta vez porque la excepcion viaja con el commit que el gate va a usar
como "anterior".

Ninguna ruta de `app/` emite `UPDATE` sobre `vehicle_status_history` —se
reviso para esta migracion igual que para `019`— asi que tampoco hay
riesgo funcional, solo el riesgo teorico de permiso que la excepcion ya
cubre.

El rol se identifica por catalogo — `BENEFICIARIOS`, mismo patron que
`016` y `019` — y NUNCA hardcodeado: se llama distinto en desarrollo que en
test.

MARCADOR DEL LINT: `# migracion-segura:` POR LINEA, NO `# migracion-
contract:` DE ARCHIVO
─────────────────────────────────────────────────────────────────────────
El de archivo silenciaria el gate de DDL destructivo para el RESTO del
modulo — cualquier `DROP`/`RENAME`/etc que alguien agregue aca dentro de
seis meses pasaria sin que el gate lo vea. Este archivo no tiene mas DDL
que el `REVOKE`, pero el criterio del proyecto (ver `019` y la regla dura
13 del `CLAUDE.md` raiz) es usar siempre el marcador angosto cuando
alcanza, para no dejar la puerta abierta de mas.

Revision ID: 020
Revises: 019
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "020"
down_revision: str | None = "019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "vehicle_status_history"

# El rol de aplicacion NO se nombra: se llama distinto en desarrollo
# (`mitutu`) que en test, y hardcodearlo obligaria a esta migracion a
# conocer el entorno donde corre. Mismo patron que `016` y `019`.
BENEFICIARIOS = sa.text(
    "SELECT DISTINCT grantee FROM information_schema.role_table_grants "
    "WHERE table_name = :tabla "
    "  AND privilege_type = 'UPDATE' "
    "  AND grantee <> current_user"
)


def upgrade() -> None:
    conexion = op.get_bind()

    for rol in conexion.execute(BENEFICIARIOS, {"tabla": TABLA}).scalars().all():
        # Los identificadores no se pueden bindear como parametros. `TABLA`
        # es una constante de este modulo y `rol` sale del catalogo del
        # sistema. La version inmediatamente anterior de la aplicacion no
        # emite UPDATE sobre esta tabla, y su propio test_permisos.py ya
        # declara la excepcion SIN_UPDATE_A_PROPOSITO para ella — el gate
        # migraciones-compatibles corre esa misma suite contra este esquema
        # y no la va a leer como un permiso ausente por error (ver el
        # encabezado de este archivo).
        # migracion-segura: cierra el append-only de D-1.
        conexion.execute(sa.text(f'REVOKE UPDATE ON {TABLA} FROM "{rol}"'))  # noqa: S608


def downgrade() -> None:
    """Restituye exactamente el UPDATE que este upgrade revoco.

    No hace falta tocar SELECT/INSERT/DELETE: esta migracion nunca los
    toco, asi que quedan como estaban (DELETE sigue revocado por `019`).
    Se busca el rol por SELECT —que ninguna migracion de esta tabla revoca
    nunca— para encontrar al mismo beneficiario aunque ya no tenga UPDATE
    para filtrar por el (a diferencia de `upgrade`, que si puede filtrar
    por UPDATE porque ahi todavia esta otorgado).
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
        conexion.execute(sa.text(f'GRANT UPDATE ON {TABLA} TO "{rol}"'))  # noqa: S608
