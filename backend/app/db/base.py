"""Base declarativa de SQLAlchemy — T-010.

`alembic/env.py` importa `Base.metadata` desde aca para el autogenerate. Hasta
que este archivo existio, env.py avisaba en cada corrida que autogenerate
estaba desactivado.

TODO modelo de negocio tiene que heredar de esta `Base` **y** llevar
`tenant_id`. La regla no la impone este archivo: la verifica el test
introspectivo que recorre `pg_policies` (tarea 2.6). Una convencion que solo
vive en un docstring se rompe el dia que alguien tiene apuro.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Raiz de todos los modelos del backend."""
