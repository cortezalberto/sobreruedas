"""extension postgis

Por que existe (C-04, design.md D-4): `branches.geo_point` es
`geography(Point,4326)` — spec-tecnica 3.3 — y ese tipo no existe sin PostGIS.
Un `CREATE TABLE` con esa columna falla antes de crear nada.

POR QUE NO SE AGREGA A `001_extensiones`
─────────────────────────────────────────
`001` ya esta aplicada en todos los entornos. Editarla no la vuelve a correr:
la deja diciendo que instala algo que en las bases existentes nunca instalo.
Una migracion aplicada es historia, no configuracion.

DISPONIBLE PERO NO CREADA
──────────────────────────
La imagen del proyecto es `postgis/postgis:16-3.4-alpine`, asi que la extension
estaba en `pg_available_extensions` desde el primer dia — solo que nadie la
habia creado. Es el tipo de hueco que no se ve leyendo el compose: la imagen
dice PostGIS, y uno asume que PostGIS esta.

Es aditiva, y por lo tanto compatible hacia atras (regla dura 13): la version
anterior de la aplicacion no conoce la extension y no le molesta que exista.

Revision ID: 004
Revises: 003
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXTENSION = "postgis"


def upgrade() -> None:
    op.execute(f'CREATE EXTENSION IF NOT EXISTS "{EXTENSION}"')


def downgrade() -> None:
    # Sin CASCADE a proposito. Si quedara alguna columna `geography` viva, este
    # DROP tiene que fallar y no llevarsela por delante en silencio.
    op.execute(f'DROP EXTENSION IF EXISTS "{EXTENSION}"')
