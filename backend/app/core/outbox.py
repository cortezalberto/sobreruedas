"""Outbox transaccional — [`ADR-036`](../../../docs/adr/ADR-036-outbox-transaccional-para-eventos-de-dominio.md).

DOS PASOS, Y EL ORDEN ES LA GARANTIA
─────────────────────────────────────
1. `registrar(...)` — dentro de la transaccion del cambio. Escribe la fila y
   anota el sobre en `sesion.info`.
2. `drenar(...)` — DESPUES del commit. Publica lo anotado y marca las filas.

Si la transaccion revierte, el paso 2 no corre y la fila se fue con el rollback.
**No hay forma de publicar un evento por algo que no pasó**, que es la unica
razon por la que esta tabla existe: publicar directo desde el servicio ocurriria
antes del commit, porque `sesion_de_tenant` commitea recien al terminar la
peticion.

EL DRENAJE NO BUSCA, RECUERDA
──────────────────────────────
No hay un `SELECT ... WHERE published_at IS NULL`. Los sobres viajan en
`sesion.info["outbox"]`, que vive con la sesion y por lo tanto con la
transaccion. La razon es de aislamiento, no de rendimiento: **buscar pendientes
obligaria a leer el outbox de todos los tenants**, y el rol de aplicacion es
`NOBYPASSRLS` por `ADR-020`. El que si va a buscar es el relay, y por eso el
relay necesita un rol propio que hoy no existe en ninguna instalacion — ver
`ADR-036` §"Lo que esta decision NO cierra".

QUE PASA SI EL PUBLISH FALLA
─────────────────────────────
La fila queda con `published_at IS NULL` y `drenar` no levanta. Es deliberado:
la peticion YA commiteo —el vehiculo existe, el usuario recibio su 201— y
convertir un fallo de Redis en un 500 le mentiria sobre lo que pasó. El fallo se
registra en el log y queda la fila como evidencia consultable. Lo que NO hay
todavia es quien la reintente.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from redis.asyncio import Redis
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.events import VERSION_ACTUAL, EventoInvalido, Sobre, publicar_sobre
from app.db.base import Base

__all__ = ["CLAVE_EN_SESION", "OutboxEvent", "drenar", "pendientes", "registrar"]

_log = logging.getLogger(__name__)

# La clave de `sesion.info` donde viajan los sobres pendientes. Es una constante
# y no un literal suelto porque la escriben los servicios y la lee la dependencia
# de sesion: dos lados, y un typo en uno de ellos no fallaria — simplemente no
# se publicaria nada, en silencio.
CLAVE_EN_SESION = "outbox"


class OutboxEvent(Base):
    """La fila del outbox. La crea la migracion `017`.

    Es una COLA y no una entidad de negocio, y por eso no tiene `deleted_at`: una
    fila publicada no se da de baja, se purga por antiguedad. Ver el encabezado
    de la migracion.
    """

    __tablename__ = "outbox_events"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, nullable=False, unique=True)
    type: Mapped[str] = mapped_column(sa.String(length=120), nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    )
    published_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)


def pendientes(sesion: AsyncSession) -> list[Sobre]:
    """Los sobres anotados en esta sesion. Lista vacia si no hay ninguno."""
    anotados = sesion.info.get(CLAVE_EN_SESION)
    return list(anotados) if anotados else []


def registrar(
    sesion: AsyncSession,
    tipo: str,
    *,
    tenant_id: uuid.UUID,
    payload: dict[str, Any],
    version: int = VERSION_ACTUAL,
) -> Sobre:
    """Anota un hecho para publicar cuando la transaccion commitee.

    NO es `async` y no toca la red: agrega la fila a la sesion y devuelve el
    sobre. El `event_id` se genera ACA y no al publicar — si se generara en el
    publish, dos intentos del mismo evento llevarian identificadores distintos y
    la idempotencia del consumidor no los reconoceria como el mismo hecho.

    `occurred_at` es cuando pasó el hecho, no cuando se publica. Un evento
    drenado tarde no puede mentir sobre su momento.
    """
    if not tipo or "." not in tipo:
        # El chequeo fino lo hace `publicar`, con su regex. Acá alcanza con
        # romper temprano: un tipo mal formado descubierto recien en el drenaje
        # seria un error DESPUES del commit, o sea un evento perdido en un log en
        # vez de una peticion que falla.
        raise EventoInvalido(f"el tipo de evento tiene que ser 'dominio.hecho', y llego {tipo!r}")

    sobre = Sobre(
        event_id=uuid.uuid4(),
        type=tipo,
        version=version,
        tenant_id=tenant_id,
        occurred_at=datetime.now(UTC),
        payload=payload,
    )

    sesion.add(
        OutboxEvent(
            tenant_id=sobre.tenant_id,
            event_id=sobre.event_id,
            type=sobre.type,
            version=sobre.version,
            payload=sobre.payload,
            occurred_at=sobre.occurred_at,
        )
    )

    sesion.info.setdefault(CLAVE_EN_SESION, []).append(sobre)
    return sobre


async def drenar(
    sesion: AsyncSession, *, dsn: str | None = None, cliente: Redis | None = None
) -> int:
    """Publica los sobres anotados y marca sus filas. Devuelve cuantos salieron.

    ⚠️ SE LLAMA DESPUES DEL COMMIT, con la transaccion ya cerrada. Por eso abre
    la suya propia para marcar —`sesion_de_tenant`, con el contexto puesto, como
    cualquier otra escritura— en vez de reusar la sesion que recibio, que ya no
    tiene transaccion viva.

    NO LEVANTA SI EL PUBLISH FALLA. La peticion ya commiteo y el usuario ya
    recibio su respuesta; convertir una caida de Redis en un error le mentiria
    sobre lo que pasó. Queda la fila sin marcar y el motivo en el log.

    `cliente` es el mismo parametro que `publicar` ya tenia, y por el mismo
    motivo. Sin el, esta funcion resolvia el cliente desde `get_settings()`, y en
    los tests eso es una dependencia INVISIBLE: `entorno_limpio` borra las
    variables antes de cada test, asi que `drenar` solo funcionaba si otro archivo
    de la suite ya habia dejado un `Settings` valido en la cache `lru_cache`. Los
    tres tests del drenaje **pasaban en la suite completa y fallaban solos** —el
    reverso exacto del problema que documenta `reponer_entorno`, y igual de
    engañoso.
    """
    sobres = pendientes(sesion)
    if not sobres:
        return 0

    # EL TENANT SALE DE `sesion.info`, QUE LO PUSO LA DEPENDENCY CON EL CLAIM.
    # No de `sobres[0].tenant_id`, aunque hoy valgan lo mismo: leerlo del sobre
    # haria que el dato que decide el aislamiento venga de la carga util que se
    # esta drenando, y la cadena que hay que poder auditar es token -> claim ->
    # sesion. Con una sola lectura, esa cadena tiene un eslabon menos y ninguna
    # rama donde un sobre mal construido elija la transaccion.
    tenant_id = sesion.info["tenant_id"]

    # Se limpia ANTES de publicar. Si `drenar` corriera dos veces sobre la misma
    # sesion —hoy no puede, pero el dia que alguien lo llame de mas— el segundo
    # no republicaria: un evento duplicado es trabajo para la idempotencia del
    # consumidor, y no hace falta gastarla en un error nuestro.
    sesion.info[CLAVE_EN_SESION] = []

    publicados: list[uuid.UUID] = []
    for sobre in sobres:
        try:
            # `publicar_sobre` y NO `publicar`: este sobre ya existe desde que se
            # registro, con su `event_id` guardado en la fila. `publicar` armaria
            # uno nuevo, y el identificador del stream dejaria de coincidir con
            # el de la base — que es justo lo que empareja una reentrega.
            await publicar_sobre(sobre, cliente=cliente)
        except Exception:
            # `Exception` a secas y no `RedisError`: acá abajo hay red, DNS y
            # serializacion, y lo que importa es que NADA de eso tumbe una
            # peticion que ya termino bien. El sobre queda sin marcar.
            _log.exception(
                "[outbox] no se pudo publicar %s (event_id=%s); la fila queda pendiente",
                sobre.type,
                sobre.event_id,
            )
            continue
        publicados.append(sobre.event_id)

    if publicados:
        await _marcar_publicados(tenant_id, publicados, dsn=dsn)

    return len(publicados)


async def _marcar_publicados(
    tenant_id: uuid.UUID, event_ids: list[uuid.UUID], *, dsn: str | None = None
) -> None:
    """Sella las filas que salieron, en su propia transaccion con contexto.

    Un fallo acá tampoco levanta, y la consecuencia hay que decirla: la fila
    queda pendiente de algo que **si se publico**, asi que el relay del futuro la
    republicaria. Es "al menos una vez", que es exactamente el contrato de
    `ADR-009` y lo que la idempotencia del consumidor ya cubre.
    """
    # Import local: `db.session` importa configuracion y motor, y este modulo lo
    # importan los servicios. Arriba crearia un ciclo por `db.base`.
    from app.db.session import sesion_de_tenant

    try:
        async with sesion_de_tenant(tenant_id, dsn=dsn) as sesion:
            await sesion.execute(
                sa.update(OutboxEvent)
                .where(OutboxEvent.event_id.in_(event_ids))
                .values(published_at=datetime.now(UTC))
            )
    except Exception:
        _log.exception(
            "[outbox] se publicaron %d eventos y no se pudieron marcar; el relay los repetiria",
            len(event_ids),
        )
