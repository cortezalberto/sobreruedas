"""El modelo ORM de `vehicle_status_history` — C-14, `T-084` (tarea 2.1).

Se prueba SIN base de datos: que las columnas declaradas coincidan con las
de la tabla y que el enum liste sus valores. Lo que no se puede probar sin
Postgres real —RLS, la FK compuesta, el `REVOKE`— vive en
`tests/integration/test_status_history.py`.

⚠️ LOS VALORES DEL ENUM HAY QUE LISTARLOS, aunque el tipo ya exista en la base.
`models.py` ya documenta por que: sin ellos SQLAlchemy escribe bien y falla al
LEER, con "'reserved' is not among the defined enum values". Este test es el
que se pondria rojo si `historial.py` copiara `ENUM(name=..., create_type=False)`
a secas en vez de repetir la lista de `EstadoDeVehiculo`.
"""

from __future__ import annotations

import datetime as dt
import uuid

from app.modules.stock.historial import VehicleStatusHistory
from app.modules.stock.schemas import EstadoDeVehiculo

COLUMNAS_ESPERADAS = {
    "id",
    "tenant_id",
    "vehicle_id",
    "from_status",
    "to_status",
    "changed_by",
    "reason",
    "changed_at",
}


def test_el_modelo_declara_exactamente_las_columnas_de_la_tabla() -> None:
    """`spec-tecnica` §3.4 / `design.md` D-2: `changed_by` y `changed_at`, sin
    `notes` y sin los nombres de `schemas.py` (`user_id`/`occurred_at`)."""
    assert set(VehicleStatusHistory.__table__.columns.keys()) == COLUMNAS_ESPERADAS


def test_changed_at_es_timestamptz() -> None:
    columna = VehicleStatusHistory.__table__.columns["changed_at"]
    assert columna.type.timezone is True  # type: ignore[attr-defined]


def test_from_status_es_nullable_y_to_status_no() -> None:
    tabla = VehicleStatusHistory.__table__
    assert tabla.columns["from_status"].nullable is True
    assert tabla.columns["to_status"].nullable is False


def test_changed_by_es_nullable() -> None:
    """`D-3`/`D-9`: una transicion automatica no tiene autor."""
    assert VehicleStatusHistory.__table__.columns["changed_by"].nullable is True


def test_el_enum_de_estado_lista_los_seis_valores_de_estadodevehiculo() -> None:
    """El agujero exacto que `models.py` advierte para `Vehicle.status`.

    Sin los valores listados, el tipo se declara bien y SQLAlchemy revienta
    recien al leer una fila de la base — un fallo que este test unitario, sin
    tocar Postgres, no podria disparar si no fuera porque el enum de Python SI
    expone sus miembros sin necesidad de una conexion.
    """
    columna = VehicleStatusHistory.__table__.columns["to_status"]
    valores = set(columna.type.enums)  # type: ignore[attr-defined]
    assert valores == {estado.value for estado in EstadoDeVehiculo}


def test_se_puede_instanciar_sin_tocar_la_base() -> None:
    """Contrapeso minimo: que el ORM mappee sin levantar al construir."""
    fila = VehicleStatusHistory(
        tenant_id=uuid.uuid4(),
        vehicle_id=uuid.uuid4(),
        from_status=None,
        to_status=EstadoDeVehiculo.EN_PREPARACION.value,
        changed_by=None,
        reason=None,
        changed_at=dt.datetime.now(dt.UTC),
    )
    assert fila.from_status is None
    assert fila.to_status == "in_preparation"
