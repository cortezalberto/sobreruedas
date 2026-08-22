"""Modelo ORM de Notificaciones — C-06, `T-035`.

Las columnas son las de `knowledge-base/04_modelo_de_datos.md`, y el texto NO
esta entre ellas: la fila guarda `type` y `payload`, y la redaccion la arma
`plantillas.py` al leer. Ver el encabezado de la migracion `018`.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ⚠️ IMPORT POR EFECTO, Y HACE FALTA. La FK compuesta apunta a `users`, y
# SQLAlchemy resuelve ese destino contra `Base.metadata`: si el modelo de
# `users` no se importo, el mapper levanta `NoReferencedTableError` al primer
# `flush()` —no al importar—, o sea en la primera notificacion que alguien cree.
#
# Es la unica dependencia de ORM que este modulo acepta, y es real: sin `users`
# no hay a quien notificar. Lo que NO se importa es el modelo de stock, aunque
# el consumidor lea de `vehicles`: ahi la consulta va en SQL crudo justamente
# para no acoplar los dos modulos por algo que no es una restriccion de la base.
from app.modules.users.models import User as _User  # noqa: F401

__all__ = ["Notification"]

_UUID_NUEVO = sa.text("gen_random_uuid()")
_AHORA = sa.text("now()")


class Notification(Base):
    __tablename__ = "notifications"

    __table_args__ = (
        sa.ForeignKeyConstraint(
            ["user_id", "tenant_id"],
            ["users.id", "users.tenant_id"],
            name="fk_notifications_user",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, primary_key=True, server_default=_UUID_NUEVO)

    # La primera de las tres capas de aislamiento. La completa el servicio con el
    # valor del token — nunca un schema de entrada, que ni lo declara.
    tenant_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, nullable=False)

    # La FK es COMPUESTA `(user_id, tenant_id)` y vive en `__table_args__`: una
    # restriccion sobre dos columnas no se puede declarar en una sola. Ver el
    # encabezado de la migracion `018`.
    user_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, nullable=False)

    type: Mapped[str] = mapped_column(sa.String(length=120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # `None` = sin leer. Es la unica transicion que tiene una notificacion, y por
    # eso se guarda el INSTANTE y no un booleano: "cuando la vio" contesta
    # tambien "si la vio", y al reves no.
    read_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=_AHORA
    )
