"""La auditoria de cambios de estado — C-14, `T-084`.

QUE VIVE ACA Y POR QUE JUNTO
──────────────────────────────
El modelo ORM, el repositorio de lectura y el registrador compartido de
`vehicle_status_history`. Los tres van en el mismo archivo porque
`registrar_transicion` tiene TRES llamadores (`StockService.crear`,
`StockService.cambiar_estado` y la importacion masiva) y uno de ellos —la
importacion— no construye un `StockService`. Un metodo privado del servicio
obligaria a la importacion a instanciarlo solo para llegar al metodo, o a
duplicar el `INSERT` — y la duplicacion en una tabla de auditoria es como se
llega a dos formatos de fila para el mismo hecho (`design.md` D-5).

`registrar_transicion` NO ES `async`, igual que `core/outbox.registrar()`:
agrega la fila a la sesion que recibe y devuelve. El `flush` lo hace quien
llama, cuando ya tiene el `id` del vehiculo — exactamente la misma razon por
la que el evento del outbox se anota despues del flush en `service.py`.

POR QUE NO UN EVENTO DEL OUTBOX QUE UN CONSUMIDOR MATERIALICE
─────────────────────────────────────────────────────────────
Porque el historial tiene que estar en la MISMA transaccion que el cambio que
registra. Un consumidor asincronico introduce una ventana en la que el
vehiculo ya cambio de estado y el historial todavia no lo dice. `ADR-036`
resuelve la publicacion de hechos hacia afuera; la auditoria es un hecho hacia
ADENTRO y no admite eventual consistency.
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.stock.schemas import EstadoDeVehiculo

__all__ = ["HistorialRepository", "VehicleStatusHistory", "registrar_transicion"]

_UUID_NUEVO = sa.text("gen_random_uuid()")
_AHORA = sa.text("now()")

# El tipo lo CREA la migracion `011`. `create_type=False` se lo nombra a
# SQLAlchemy sin que intente crearlo de nuevo, y los valores hay que
# listarlos aunque el tipo ya exista en la base: sin ellos SQLAlchemy escribe
# bien y falla al LEER — ver la advertencia identica en `models.py`.
_ESTADO = ENUM(*[e.value for e in EstadoDeVehiculo], name="vehicle_status_enum", create_type=False)


class VehicleStatusHistory(Base):
    """Una fila de la linea de tiempo de un vehiculo. La crea la migracion `019`.

    `from_status` es NULL en la fila genesis del alta (`design.md` D-4): la
    ausencia de estado previo ES la informacion que esa columna codifica.

    `changed_by` es NULL cuando el cambio lo origina un proceso automatico y
    no una persona (`design.md` D-3) — es un valor LEGITIMO, no un dato
    faltante.

    La tabla es append-only por `REVOKE UPDATE, DELETE` en la migracion, no
    por disciplina de este modelo: ver `019_vehicle_status_history.py`.
    """

    __tablename__ = "vehicle_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, server_default=_UUID_NUEVO
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True))
    from_status: Mapped[str | None] = mapped_column(_ESTADO, nullable=True)
    to_status: Mapped[str] = mapped_column(_ESTADO)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(sa.UUID(as_uuid=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    changed_at: Mapped[dt.datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=_AHORA
    )


def registrar_transicion(
    sesion: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    vehiculo_id: uuid.UUID,
    desde: EstadoDeVehiculo | None,
    hasta: EstadoDeVehiculo,
    razon: str | None,
    autor: uuid.UUID | None,
) -> None:
    """Anota una transicion. NO es `async`: agrega a la sesion y devuelve.

    `desde=None` es la fila genesis del alta (`design.md` D-4). `autor=None`
    es una transicion sin persona detras (`design.md` D-3) — la usara C-28
    cuando las automatizaciones cambien estados.

    El `flush` NO ocurre aca: la sesion todavia puede no tener el `id` del
    vehiculo resuelto cuando se llama desde `StockService.crear`, y forzar un
    flush por linea de historial multiplicaria los viajes a la base en la
    importacion masiva de `RN-ST-13`.
    """
    sesion.add(
        VehicleStatusHistory(
            tenant_id=tenant_id,
            vehicle_id=vehiculo_id,
            from_status=desde.value if desde is not None else None,
            to_status=hasta.value,
            reason=razon,
            changed_by=autor,
        )
    )


class HistorialRepository:
    """Lectura de la linea de tiempo de UN vehiculo, acotada a un tenant.

    El tenant se fija al construir, igual que `VehicleRepository`: quien tiene
    el repositorio ya decidio de que agencia habla, y ese valor vino del
    token — nunca de un parametro que otro llamador pudiera pisar.
    """

    def __init__(self, sesion: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._sesion = sesion
        self._tenant_id = tenant_id

    async def listar_historial(self, vehiculo_id: uuid.UUID) -> Sequence[VehicleStatusHistory]:
        """La linea de tiempo completa, del cambio mas nuevo al mas viejo.

        SIN PAGINAR, A PROPOSITO (`design.md` D-8): la cantidad de filas la
        acota la maquina de estados —nueve transiciones legales, cada una una
        accion humana deliberada—, y el peor caso realista es una decena de
        filas. El dia que haga falta paginar, la salida es una etiqueta en el
        `select` (`VehicleStatusHistory.changed_at.label("created_at")`) y
        `core/pagination.py` no se toca: es codigo de C-02, gobernanza
        CRITICA.

        `(changed_at DESC, id DESC)`: el segundo criterio desempata dos filas
        con el mismo instante — dos transiciones dentro del mismo lote de
        importacion pueden compartir `now()` hasta la resolucion del reloj.

        El filtro de `tenant_id` va EXPLICITO en la consulta ademas de la
        politica RLS: es la capa 3 de la regla dura 1, y la unica que sigue
        funcionando si alguien corre esta misma consulta con el rol
        propietario.
        """
        consulta = (
            select(VehicleStatusHistory)
            .where(
                VehicleStatusHistory.tenant_id == self._tenant_id,
                VehicleStatusHistory.vehicle_id == vehiculo_id,
            )
            .order_by(VehicleStatusHistory.changed_at.desc(), VehicleStatusHistory.id.desc())
        )
        return (await self._sesion.execute(consulta)).scalars().all()
