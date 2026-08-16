"""extensiones de PostgreSQL

Por que estan aca y no solo en el init local (`infra/local/postgres/init/`):
ese archivo corre UNA sola vez, al crear el volumen, y **solo en desarrollo**.
En staging y produccion no existe. Una extension que vive nada mas ahi funciona
en la maquina de quien la agrego y falta en todas las demas.

`IF NOT EXISTS` porque en desarrollo el init ya creo dos de estas cuatro: la
migracion tiene que poder correr sobre una base que ya las tiene sin fallar.
El despliegue corre `upgrade head` en cada arranque.

Que hace cada una:

  uuid-ossp   generacion de UUID. `gen_random_uuid()` ya viene en el core desde
              PostgreSQL 13, pero el stack declarado la nombra explicitamente.
  pg_trgm     similitud por trigramas: busqueda difusa e indexado de LIKE.
              Sostiene buscar patente, marca y modelo con errores de tipeo.
  unaccent    normalizacion de acentos. Sin esto "Peugeot" y "Peugéot" son dos
              cosas distintas para la busqueda, y en este mercado se escriben
              las dos.
  btree_gin   indices GIN sobre tipos escalares. Es lo que permite un indice
              unico que combine `tenant_id` con una columna de texto buscada
              por trigramas — o sea, buscar rapido SIN salirse del tenant.

NO se crean aca `pgcrypto` ni `postgis`: las instala Terraform sobre la base
gestionada, y el init las trae en local. Duplicarlas en la migracion no agrega
garantia y agrega un lugar mas donde desincronizarse.

Revision ID: 001
Revises: 000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "001"
down_revision: str | None = "000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXTENSIONES = ("uuid-ossp", "pg_trgm", "unaccent", "btree_gin")


def upgrade() -> None:
    for extension in EXTENSIONES:
        op.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension}"')


def downgrade() -> None:
    # En orden inverso por prolijidad; ninguna de las cuatro depende de otra.
    #
    # Sin CASCADE a proposito: si un indice quedo colgando de `btree_gin`, esto
    # falla y avisa. Con CASCADE se llevaria el indice puesto en silencio, y un
    # downgrade que destruye mas de lo que revierte es peor que uno que falla.
    for extension in reversed(EXTENSIONES):
        op.execute(f'DROP EXTENSION IF EXISTS "{extension}"')
