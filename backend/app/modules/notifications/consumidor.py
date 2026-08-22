"""De un evento de dominio a una notificacion — C-06, `T-035`.

ES UN REGISTRO, NO UNA CADENA DE `if`
──────────────────────────────────────
Cada modulo declara qué evento le interesa y a quién notifica. C-06 construye el
mecanismo; C-19, C-24, C-27 y C-28 le cuelgan los suyos sin tocar este archivo.

Con un `if sobre.type == ...` acá adentro, la regla de negocio de cada dominio
terminaria viviendo en el modulo de notificaciones — que es donde nadie la va a
buscar cuando cambie.

⚠️ A QUIEN SE NOTIFICA POR UN EVENTO DE STOCK NO ESTA DEFINIDO EN EL CORPUS
────────────────────────────────────────────────────────────────────────────
Los dos unicos destinatarios que el corpus nombra son de OTROS changes: *"notifica
al vendedor"* (flujo 5, leads sin actividad, C-27) y *"el vendedor recibe
notificacion"* (flujo 6, respuesta de la financiera, C-26). Para `vehicle.*` no
hay ninguno.

El manejador que se registra abajo elige **la persona asignada al vehiculo**, y
la eleccion se apoya en dos cosas y no en una preferencia: `vehicles.assigned_user_id`
existe justamente para nombrar a esa persona, y los dos casos documentados
notifican al vendedor a cargo. Si el vehiculo no tiene asignado, **no se notifica
a nadie** — antes que elegir un destinatario por descarte.

Es la unica regla de negocio que este change inventa, y queda escrita acá para
que se pueda discutir en una linea en vez de descubrirse leyendo el codigo.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Final

import sqlalchemy as sa

from app.core.events import Sobre
from app.db.session import sesion_de_tenant
from app.modules.notifications.service import NotificationService

__all__ = [
    "GRUPO",
    "manejador_de_notificaciones",
    "registrar_manejador",
    "tipos_escuchados",
]

_log = logging.getLogger(__name__)

# El consumer group. Uno solo para todas las notificaciones: lo que reparte el
# trabajo entre procesos es el nombre del CONSUMIDOR dentro del grupo, no el
# grupo. Un grupo por proceso haria que cada uno recibiera una copia de todo.
GRUPO: Final = "notificaciones"

Manejador = Callable[[Sobre, str | None], Awaitable[None]]

_REGISTRO: Final[dict[str, Manejador]] = {}


def registrar_manejador(tipo_de_evento: str, manejador: Manejador) -> None:
    """Declara qué hacer con un tipo de evento.

    Levanta si el tipo ya tiene manejador. Sobrescribir en silencio dejaria dos
    modulos peleandose el mismo evento y ganando el que se importe ultimo — un
    orden que depende de los imports y cambia sin que nadie lo toque.
    """
    if tipo_de_evento in _REGISTRO:
        raise ValueError(f"`{tipo_de_evento}` ya tiene manejador registrado")
    _REGISTRO[tipo_de_evento] = manejador


async def manejador_de_notificaciones(sobre: Sobre, dsn: str | None = None) -> None:
    """El punto de entrada que `consumir` invoca por cada evento.

    UN TIPO SIN MANEJADOR NO ES UN ERROR. Se registra y se sigue: el consumidor
    puede estar suscripto a un stream cuyo manejador todavia no existe, y
    levantar haria que `consumir` lo reintentara cinco veces y terminara
    mandandolo a irrecuperables. Un evento que a nadie le interesa no es un
    evento fallido.
    """
    manejador = _REGISTRO.get(sobre.type)
    if manejador is None:
        _log.debug("[notificaciones] sin manejador para %s", sobre.type)
        return
    await manejador(sobre, dsn)


# ── El manejador de stock ────────────────────────────────────────────────────


async def _notificar_cambio_de_estado(sobre: Sobre, dsn: str | None = None) -> None:
    """`vehicle.status_changed` -> notificacion a la persona asignada.

    NO LEVANTA SI NO HAY ASIGNADO, y esa es la diferencia entre "no habia a quien
    avisarle" y "fallo el aviso". Levantar mandaria el evento a reintentos y de
    ahi a irrecuperables, ensuciando la cola con hechos perfectamente normales:
    la mayoria de los vehiculos no tiene vendedor asignado.

    El `dsn` viaja hasta acá porque los tests corren contra otra base. Es el mismo
    parametro que `consumir` y `drenar` ya llevan por el mismo motivo.
    """
    vehiculo_id = sobre.payload.get("vehicle_id")
    if vehiculo_id is None:
        _log.warning("[notificaciones] %s sin `vehicle_id` en el payload", sobre.type)
        return

    async with sesion_de_tenant(sobre.tenant_id, dsn=dsn) as sesion:
        # Consulta cruda y no `select(Vehicle)`: el modulo de notificaciones no
        # importa el modelo de stock. Acoplar los dos modulos por su ORM haria
        # que un cambio en `Vehicle` rompiera esto sin razon — lo unico que se
        # necesita de ahi son dos columnas.
        fila = (
            await sesion.execute(
                sa.text(
                    "SELECT assigned_user_id, COALESCE(domain_plate, chassis_number) "
                    "FROM vehicles WHERE id = :id AND deleted_at IS NULL"
                ),
                {"id": vehiculo_id},
            )
        ).first()

        if fila is None or fila[0] is None:
            return

        await NotificationService(sesion, sobre.tenant_id).crear(
            user_id=uuid.UUID(str(fila[0])),
            tipo="vehiculo.cambio_de_estado",
            payload={
                "identificador": fila[1] or "sin identificar",
                "desde": sobre.payload.get("from", ""),
                "hasta": sobre.payload.get("to", ""),
            },
        )


registrar_manejador("vehicle.status_changed", _notificar_cambio_de_estado)


def tipos_escuchados() -> tuple[str, ...]:
    """Los streams a los que este consumidor se suscribe hoy.

    FUNCION Y NO CONSTANTE, y la diferencia no es de estilo: una constante se
    evalua al importar ESTE modulo y se quedaria con lo que hubiera registrado
    hasta ese instante. Los manejadores de C-19, C-24 y C-28 se registran al
    importar SUS modulos, que ocurre despues — asi que la constante los dejaria
    afuera y el sintoma seria un manejador que existe, esta bien escrito, y nunca
    corre porque nadie se suscribio a su stream.
    """
    return tuple(_REGISTRO)
