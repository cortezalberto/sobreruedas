"""baseline

Punto cero del historial de migraciones. Vacia a proposito (T-007).

Existe para que `alembic downgrade base` tenga hasta donde bajar y para que la
primera migracion real tenga un `down_revision` al que apuntar. Sin una
baseline, la migracion 001 seria la raiz del historial y no habria forma de
revertirla del todo.

Las EXTENSIONES de PostgreSQL no van aca: en local las habilita
infra/local/postgres/init/01-extensions.sql (ADR-019) y en staging y
produccion las instala Terraform. La migracion que las verifica es T-009, que
cae en C-02.

Revision ID: 000
Revises:
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "000"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
