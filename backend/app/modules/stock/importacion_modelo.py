"""Modelo, schemas y estados de una importacion masiva — C-17.

POR QUE ESTA TODO EN UN ARCHIVO Y NO REPARTIDO COMO EN `vehicles`
──────────────────────────────────────────────────────────────────
`vehicles` tiene `models.py`, `schemas.py`, `repository.py` y `service.py` por
tamaño: son ~35 campos, seis estados y ocho filtros. `imports` es una tabla de
seguimiento con doce columnas y ningun filtro. Partirla en cuatro archivos de
veinte lineas haria que leer el flujo entero cueste cuatro saltos.

Se parte el dia que crezca — hoy la division seria ceremonia.

EL ENUM DE ESTADO ES EL CONTRATO DEL POLLING
──────────────────────────────────────────────
`Flujo 4` describe el frontend preguntando cada 2 segundos hasta que el estado
sea terminal. Entonces "cual estado es terminal" no es un detalle interno: es
lo que decide si el navegador deja de preguntar. Por eso `TERMINALES` esta acá,
al lado del enum, y no como un `if` repartido por el codigo.
"""

from __future__ import annotations

import datetime as dt
import uuid
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = [
    "TERMINALES",
    "EstadoDeImportacion",
    "Import",
    "ImportacionSalida",
    "TipoDeImportacion",
]

_UUID_NUEVO = sa.text("gen_random_uuid()")
_AHORA = sa.text("now()")


class EstadoDeImportacion(StrEnum):
    """Los seis del `Flujo 4`. El orden es el del avance real."""

    PENDIENTE = "pending"
    PARSEANDO = "parsing"
    VALIDANDO = "validating"
    IMPORTANDO = "importing"
    COMPLETADA = "completed"
    FALLIDA = "failed"


class TipoDeImportacion(StrEnum):
    STOCK = "stock"


# Donde el frontend deja de preguntar. Que este acá y no disperso es lo que
# evita el bug clasico: agregar un septimo estado terminal, olvidar una de las
# tres comparaciones, y dejar al navegador consultando para siempre.
TERMINALES = frozenset({EstadoDeImportacion.COMPLETADA, EstadoDeImportacion.FALLIDA})

# Los valores hay que listarlos aunque el tipo ya exista en la base: sin ellos
# SQLAlchemy escribe bien y falla AL LEER. Es el mismo tropiezo que documenta
# `models.py` y por eso se repite el patron en vez de inventar otro.
_ESTADO = ENUM(
    *[e.value for e in EstadoDeImportacion], name="import_status_enum", create_type=False
)
_TIPO = ENUM(*[t.value for t in TipoDeImportacion], name="import_type_enum", create_type=False)


class Import(Base):
    """Una corrida de importacion. La fila contra la que se hace polling."""

    __tablename__ = "imports"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=_UUID_NUEVO
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True))

    type: Mapped[str] = mapped_column(_TIPO, server_default=sa.text("'stock'"))
    source_filename: Mapped[str] = mapped_column(sa.String(255))
    status: Mapped[str] = mapped_column(_ESTADO, server_default=sa.text("'pending'"))

    total_rows: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))
    valid_rows: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))
    error_rows: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))

    # Sin FK a `users`: esa tabla es C-05. Ver el encabezado de la migracion 012.
    created_by: Mapped[uuid.UUID | None] = mapped_column(sa.UUID(as_uuid=True), nullable=True)

    started_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default=sa.text("'[]'"))
    failure_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )
    deleted_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )


class ImportacionSalida(BaseModel):
    """Lo que devuelve `GET /imports/{id}` en cada vuelta del polling.

    Lleva `errors` COMPLETO y no un recuento: el usuario baja el reporte, corrige
    la planilla y la vuelve a subir. Un contador diciendo "12 errores" sin decir
    cuales obligaria a un segundo endpoint para algo que ya esta en la fila.

    ⚠️ Un JSONB de 5.000 errores son cientos de KB devueltos **cada dos
    segundos** mientras el frontend hace polling. Hoy se acepta: el caso
    frecuente es cero o pocas decenas de errores, y la alternativa —paginar el
    reporte— agrega un endpoint y estado en el cliente para un caso que casi no
    ocurre. Si aparece, el arreglo es devolver `errors` solo cuando el estado ya
    es terminal.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    type: str
    source_filename: str
    status: str
    total_rows: int
    valid_rows: int
    error_rows: int
    started_at: dt.datetime | None
    completed_at: dt.datetime | None
    errors: list[dict[str, Any]]
    failure_reason: str | None
    created_at: dt.datetime
