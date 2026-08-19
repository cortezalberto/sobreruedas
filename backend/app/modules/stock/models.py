"""Modelo ORM de Stock — C-14.

`tenant_id` ESTA DECLARADO Y NO SE ASIGNA A MANO EN LOS ENDPOINTS
─────────────────────────────────────────────────────────────────
La columna existe porque es la primera de las tres capas de aislamiento. Quien
la completa es el servicio, con el valor que trajo el token — nunca un schema de
entrada, que ni siquiera lo declara.
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.stock.schemas import Carroceria, Combustible, EstadoDeVehiculo, Transmision

__all__ = ["Vehicle"]

_UUID_NUEVO = sa.text("gen_random_uuid()")
_AHORA = sa.text("now()")

# Los tipos enum los CREA la migracion `011` (y `body_type_enum` la `009`).
# `create_type=False` se los nombra a SQLAlchemy sin que intente crearlos de
# nuevo, y ademas hace que emita el cast: con `String` a secas, asyncpg manda
# `character varying` y PostgreSQL rechaza el INSERT.
#
# ⚠️ LOS VALORES HAY QUE LISTARLOS, aunque el tipo ya exista en la base. El
# primer intento fue `ENUM(name="...", create_type=False)` a secas, con el
# argumento de que la capa de datos no debia importar la de contratos. Escribia
# bien y **fallaba al LEER**: sin los valores, SQLAlchemy no puede mapear lo que
# vuelve de la base y levanta "'diesel' is not among the defined enum values".
#
# Se toman de los `StrEnum` de `schemas.py`. Un `StrEnum` es un objeto de valor,
# no un schema: no arrastra Pydantic ni validacion, solo las etiquetas. Y tener
# UNA sola lista en el codigo es lo que evita que el modelo y el contrato se
# separen. Que esa lista coincida con la de PostgreSQL lo verifica
# `test_stock_router.py`.
_ESTADO = ENUM(*[e.value for e in EstadoDeVehiculo], name="vehicle_status_enum", create_type=False)
_COMBUSTIBLE = ENUM(*[e.value for e in Combustible], name="fuel_type_enum", create_type=False)
_TRANSMISION = ENUM(*[e.value for e in Transmision], name="transmission_enum", create_type=False)
_CARROCERIA = ENUM(*[e.value for e in Carroceria], name="body_type_enum", create_type=False)


class Vehicle(Base):
    """Un vehiculo del stock de una agencia.

    Los enums viajan como `str` en el modelo y no como el `StrEnum` de
    `schemas.py`: la conversion la hace Pydantic al serializar. Tipar la columna
    con el enum de Python obligaria al modelo a importar los schemas, y la capa
    de datos no puede depender de la de contratos.
    """

    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=_UUID_NUEVO
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True))
    branch_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True))
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(sa.UUID(as_uuid=True), nullable=True)

    # Nullable por `ADR-031`. El `CHECK` de la base exige que venga este o el
    # chasis; el schema de entrada lo repite para dar un 422 legible.
    domain_plate: Mapped[str | None] = mapped_column(sa.String(15), nullable=True)
    chassis_number: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)
    engine_number: Mapped[str | None] = mapped_column(sa.String(30), nullable=True)

    brand_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True))
    model_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True))
    version_id: Mapped[uuid.UUID | None] = mapped_column(sa.UUID(as_uuid=True), nullable=True)

    year: Mapped[int] = mapped_column(sa.SmallInteger)
    mileage_km: Mapped[int] = mapped_column(sa.Integer)
    color: Mapped[str] = mapped_column(sa.String(60))
    fuel_type: Mapped[str] = mapped_column(_COMBUSTIBLE)
    transmission: Mapped[str] = mapped_column(_TRANSMISION)
    body_type: Mapped[str] = mapped_column(_CARROCERIA)

    price_ars: Mapped[Decimal] = mapped_column(sa.Numeric(18, 2))
    price_usd: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 2), nullable=True)

    # `RN-ST-12` restringe quien lo VE, no donde se guarda. La proteccion vive en
    # la capa de salida: `VehiculoSalida` no lo declara.
    acquisition_cost_ars: Mapped[Decimal | None] = mapped_column(sa.Numeric(18, 2), nullable=True)

    status: Mapped[str] = mapped_column(_ESTADO, server_default=sa.text("'in_preparation'"))
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    features: Mapped[list[str]] = mapped_column(JSONB, server_default=sa.text("'[]'"))

    acquired_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    sold_at: Mapped[dt.datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )

    # Borrado logico universal (regla dura 3). `db.delete()` esta prohibido.
    deleted_at: Mapped[dt.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
