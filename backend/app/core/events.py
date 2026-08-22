"""Eventos de dominio sobre Redis Streams — T-016, capability `platform/domain-events`.

QUE ES UN EVENTO ACA
────────────────────
Un HECHO que ya paso. Los tipos se nombran en pasado —`vehicle.created`, no
`vehicle.create`— porque quien publica **informa**, no ordena. La diferencia no
es de estilo: un tipo en imperativo invita a que el publicador sepa quien lo va
a ejecutar y que espere un resultado, y ahi el evento dejo de ser un evento y es
una llamada disfrazada.

Consecuencia directa: **publicar no depende de que haya alguien escuchando.** Un
stream sin consumidores acepta la publicacion igual, y un consumidor que falla
no afecta a la peticion que origino el evento. Si lo afectara, la caida de un
modulo secundario voltearia operaciones del modulo principal.

EL TENANT SE EXIGE AL PUBLICAR, NO AL CONSUMIR
──────────────────────────────────────────────
Un evento sin `tenant_id` que llega al consumidor ya perdio el contexto de quien
lo origino: ahi no hay forma de reconstruirlo, solo de descartarlo con un error
lejos de quien lo produjo. Se rechaza en la publicacion — fallar cerca de la
causa (D-10).

UN STREAM POR TIPO
──────────────────
`eventos:vehicle.created`, `eventos:lead.won`. Con un unico stream compartido,
todo consumidor recibiria todo y descartaria la mayor parte, y un tipo ruidoso
marcaria el ritmo de los demas.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.config import get_settings
from app.core.idempotency import ejecutar_idempotente
from app.db.session import contexto_de_tenant

# `dominio.hecho`, minusculas, exactamente dos partes.
#
# El TIEMPO VERBAL no se valida: distinguir `created` de `create` pide conjugar,
# y el corpus mezcla castellano e ingles. La convencion de D-10 se revisa
# leyendo el diff, que es donde una regla de nombres se sostiene de verdad.
_TIPO = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")

STREAM_PREFIJO = "eventos"

# Version del contrato del sobre. Le permite a un consumidor viejo distinguir
# dos formas del mismo tipo en vez de romper contra un campo que no conoce.
VERSION_ACTUAL = 1


class EventoInvalido(ValueError):
    """El evento no se puede publicar tal como vino.

    `ValueError` y no un error de peticion: quien publica es codigo del sistema,
    no un cliente de la API. Un tipo mal formado o un evento sin tenant son
    errores de programacion y tienen que romper fuerte en desarrollo, no
    convertirse en un 400 que alguien mira en produccion.
    """


def nombre_del_stream(tipo: str) -> str:
    return f"{STREAM_PREFIJO}:{tipo}"


@dataclass(frozen=True)
class Sobre:
    """El evento tal como viaja: seis campos, ni uno mas.

    `event_id` identifica LA PUBLICACION y no el hecho. Es lo que le permite al
    consumidor reconocer una reentrega: si dos publicaciones compartieran
    identificador, "ya procese este" no distinguiria un reintento de un hecho
    nuevo identico.
    """

    event_id: uuid.UUID
    type: str
    version: int
    tenant_id: uuid.UUID
    occurred_at: datetime
    payload: dict[str, Any]

    def a_redis(self) -> dict[str, str]:
        """Aplanado a texto: Redis Streams guarda pares de cadenas, no objetos.

        El `payload` va como JSON en UN campo y no desplegado en varios: sus
        claves las elige cada dominio, y mezclarlas con las del sobre haria que
        un `payload` con una clave `type` pisara la del sobre.
        """
        return {
            "event_id": str(self.event_id),
            "type": self.type,
            "version": str(self.version),
            "tenant_id": str(self.tenant_id),
            "occurred_at": self.occurred_at.isoformat(),
            "payload": json.dumps(self.payload, default=str),
        }

    @classmethod
    def desde_redis(cls, campos: dict[str, str]) -> Sobre:
        """La vuelta del aplanado. Rompe si falta algo: un sobre a medias no sirve."""
        try:
            return cls(
                event_id=uuid.UUID(campos["event_id"]),
                type=campos["type"],
                version=int(campos["version"]),
                tenant_id=uuid.UUID(campos["tenant_id"]),
                occurred_at=datetime.fromisoformat(campos["occurred_at"]),
                payload=json.loads(campos["payload"]),
            )
        except (KeyError, ValueError, TypeError) as error:
            raise EventoInvalido(
                f"el sobre leido del stream no es interpretable: {error}"
            ) from error


def _tenant_valido(valor: object) -> uuid.UUID:
    """El tenant del evento, o rompe. Sin defaults."""
    if isinstance(valor, uuid.UUID):
        return valor
    if not isinstance(valor, str) or not valor:
        raise EventoInvalido(f"un evento de dominio necesita tenant y llego {type(valor).__name__}")
    try:
        return uuid.UUID(valor)
    except ValueError as error:
        # Sin incluir el valor: puede venir de un token.
        raise EventoInvalido("el tenant del evento no es un UUID") from error


def _cliente_por_defecto() -> Redis:
    cliente: Redis = Redis.from_url(get_settings().redis.url, decode_responses=True)
    return cliente


async def publicar(
    tipo: str,
    *,
    tenant_id: object,
    payload: dict[str, Any],
    version: int = VERSION_ACTUAL,
    cliente: Redis | None = None,
) -> Sobre:
    """Publica un hecho y devuelve el sobre que quedo en el stream.

    Las dos validaciones ocurren ANTES de tocar Redis: un evento rechazado no
    tiene que dejar rastro a medias en la cola.
    """
    if not _TIPO.match(tipo):
        raise EventoInvalido(
            f"el tipo de evento tiene que ser 'dominio.hecho' en minusculas, y llego {tipo!r}"
        )

    return await publicar_sobre(
        Sobre(
            event_id=uuid.uuid4(),
            type=tipo,
            version=version,
            tenant_id=_tenant_valido(tenant_id),
            occurred_at=datetime.now(UTC),
            payload=payload,
        ),
        cliente=cliente,
    )


async def publicar_sobre(sobre: Sobre, *, cliente: Redis | None = None) -> Sobre:
    """Manda al stream un sobre YA ARMADO, sin tocarle ni un campo.

    Existe para el outbox (`ADR-036`), y la diferencia con `publicar` es la que
    hace que el mecanismo sirva: el outbox arma el sobre al REGISTRAR, dentro de
    la transaccion, y lo publica despues del commit. Si el publish le generara un
    `event_id` nuevo —como hace `publicar`, que arma el sobre en el momento— el
    identificador de la fila y el del stream no coincidirian, y la idempotencia
    del consumidor, que empareja por `event_id`, no reconoceria una reentrega.

    Tampoco recalcula `occurred_at`: un evento drenado tarde tiene que decir
    cuando paso el hecho, no cuando salio.

    ⚠️ NO REVALIDA EL TIPO. Quien arma el sobre ya paso por esa puerta: `publicar`
    con su regex, y `registrar` con su chequeo temprano. Validar de nuevo acá
    seria una segunda copia de la regla, y la que se olvide de actualizarse
    despues es siempre la de mas adentro.
    """
    redis = cliente or _cliente_por_defecto()
    # El `cast` es por los stubs de redis-py: declaran la clave del mapping
    # como `bytes | str | int | float`, y `Mapping` es invariante en la clave,
    # asi que un `dict[str, str]` --que es perfectamente valido en tiempo de
    # ejecucion-- no encaja. Se afirma lo que ya se sabe, no se afloja nada.
    await redis.xadd(nombre_del_stream(sobre.type), cast("dict[Any, Any]", sobre.a_redis()))
    return sobre


# ─────────────────────────────────────────────────────────────────────────────
# Consumo
#
# CONSUMER GROUPS Y CONFIRMACION EXPLICITA
# ────────────────────────────────────────
# Un consumidor que cae sin confirmar deja el mensaje PENDIENTE, y otro lo
# retoma. Eso da "al menos una vez": el evento no se pierde, pero puede llegar
# dos veces.
#
# La no duplicacion del EFECTO no la da el transporte — la da el consumidor
# reconociendo un `event_id` que ya proceso. Se reusa `idempotency_keys` para
# eso: misma garantia (`UNIQUE (tenant_id, key)`), misma tabla, ninguna
# migracion nueva. Un evento es, a estos fines, una creacion con clave.
# ─────────────────────────────────────────────────────────────────────────────

STREAM_IRRECUPERABLES = f"{STREAM_PREFIJO}:irrecuperables"

# Cinco intentos con espera que duplica: 1, 2, 4, 8 segundos entre medio.
# Sin fuente en el corpus; `ADR-009` fija el patron, no los numeros.
REINTENTOS_MAXIMOS = 5
ESPERA_BASE_SEGUNDOS = 1.0

Manejador = Callable[[Sobre], Awaitable[None]]


@dataclass(frozen=True)
class Resultado:
    """Que paso con un lote."""

    procesados: int
    irrecuperables: int


async def crear_grupo(cliente: Redis, tipo: str, grupo: str) -> None:
    """Crea el consumer group si no existe. Idempotente a proposito.

    `mkstream` porque un consumidor puede arrancar antes que el primer
    publicador: sin eso, suscribirse a un tipo que todavia nadie publico seria
    un error, y el orden de arranque de los procesos pasaria a importar.

    Desde `0` y no desde `$`: `$` entrega solo lo que llegue DESPUES de crear el
    grupo, asi que todo evento publicado mientras el consumidor no existia se
    perderia en silencio.
    """
    try:
        await cliente.xgroup_create(nombre_del_stream(tipo), grupo, id="0", mkstream=True)
    except ResponseError as error:
        # El grupo ya existe. Es el caso normal en todo arranque menos el
        # primero, y no es un problema.
        if "BUSYGROUP" not in str(error):
            raise


def espera_del_intento(intento: int, base: float = ESPERA_BASE_SEGUNDOS) -> float:
    """Espera creciente: duplica en cada intento.

    Reintentar de inmediato contra una dependencia caida le agrega carga justo
    cuando menos lo tolera, y convierte un problema transitorio en uno
    sostenido.
    """
    return float(base * (2 ** (intento - 1)))


async def _procesar_una_vez(sobre: Sobre, manejador: Manejador, dsn: str | None) -> None:
    """Corre el manejador bajo el contexto del tenant del sobre, una sola vez.

    Las dos cosas que hace y que el manejador no deberia tener que recordar:

      - **restablece el contexto de tenant** (D-10). El aislamiento no puede
        depender de estar dentro de un ciclo de peticion y respuesta.
      - **deduplica por `event_id`**. Si este evento ya se proceso, el manejador
        no vuelve a correr.
    """

    async def correr() -> tuple[dict[str, str], int]:
        await manejador(sobre)
        return {"event_id": str(sobre.event_id)}, 200

    with contexto_de_tenant(sobre.tenant_id):
        await ejecutar_idempotente(
            tenant=sobre.tenant_id,
            # Prefijo para que no pueda chocar con una clave que eligio un
            # cliente de la API: las dos viven en la misma tabla.
            clave=f"evento:{sobre.event_id}",
            cuerpo={"event_id": str(sobre.event_id)},
            crear=correr,
            dsn=dsn,
        )


async def _a_irrecuperables(cliente: Redis, sobre: Sobre, motivo: str) -> None:
    """Copia el evento agotado al stream de irrecuperables, con el motivo.

    Con el motivo del ULTIMO fallo y no solo el evento: sin eso, quien revise la
    cola tiene el que pero no el por que, y reconstruirlo obliga a cruzar logs
    por marca de tiempo.
    """
    # Anotado y no desempaquetado en un literal: los stubs de redis-py declaran
    # la clave del mapping como una union ancha, y `Mapping` es invariante en la
    # clave. Un `dict[str, str]` es valido en tiempo de ejecucion pero no encaja
    # en la firma, y con `**` dentro de un literal mypy tampoco lo ensancha solo.
    campos: dict[Any, Any] = dict(sobre.a_redis())
    campos["motivo"] = motivo
    campos["stream_original"] = nombre_del_stream(sobre.type)

    await cliente.xadd(STREAM_IRRECUPERABLES, campos)


async def consumir(
    cliente: Redis,
    tipo: str,
    *,
    grupo: str,
    consumidor: str,
    manejador: Manejador,
    dsn: str | None = None,
    max_mensajes: int = 10,
    reintentos: int = REINTENTOS_MAXIMOS,
    espera_base: float = ESPERA_BASE_SEGUNDOS,
    dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
    incluir_pendientes: bool = True,
) -> Resultado:
    """Procesa un lote y devuelve cuantos salieron bien y cuantos se descartaron.

    Un LOTE y no un bucle infinito: quien orquesta decide cuando volver a
    llamar. Un bucle adentro seria imposible de terminar de forma ordenada y
    obligaria a cada test a inventar una condicion de corte.

    `dormir` es parametro para que los tests puedan medir las esperas sin
    esperarlas. Un test que duerme 15 segundos de verdad para comprobar un
    backoff no prueba mejor: prueba lo mismo, mas tarde.

    `incluir_pendientes` retoma primero lo que quedo sin confirmar de una caida
    anterior. Es lo que hace que un consumidor que murio a mitad de camino no
    deje eventos varados.
    """
    await crear_grupo(cliente, tipo, grupo)
    stream = nombre_del_stream(tipo)

    mensajes: list[tuple[str, dict[str, str]]] = []

    if incluir_pendientes:
        # `0` devuelve los pendientes de ESTE consumidor: los que tomo y nunca
        # confirmo. Van primero, porque son los que llevan mas esperando.
        pendientes = await cliente.xreadgroup(grupo, consumidor, {stream: "0"}, count=max_mensajes)
        for _, entradas in pendientes:
            mensajes.extend(entradas)

    if len(mensajes) < max_mensajes:
        nuevos = await cliente.xreadgroup(
            grupo, consumidor, {stream: ">"}, count=max_mensajes - len(mensajes)
        )
        for _, entradas in nuevos:
            mensajes.extend(entradas)

    procesados = 0
    irrecuperables = 0

    for id_mensaje, campos in mensajes:
        sobre = Sobre.desde_redis(campos)
        ultimo_error = ""

        for intento in range(1, reintentos + 1):
            try:
                await _procesar_una_vez(sobre, manejador, dsn)
            except Exception as error:  # noqa: BLE001 — cualquier fallo del manejador se reintenta
                ultimo_error = f"{type(error).__name__}: {error}"
                if intento < reintentos:
                    await dormir(espera_del_intento(intento, espera_base))
                continue
            await cliente.xack(stream, grupo, id_mensaje)
            procesados += 1
            break
        else:
            # Agotados los intentos: se copia a irrecuperables y se CONFIRMA en
            # el original. Dejarlo pendiente haria que un solo evento malo tape
            # la cola para siempre y frene a todos los que vienen atras.
            await _a_irrecuperables(cliente, sobre, ultimo_error)
            await cliente.xack(stream, grupo, id_mensaje)
            irrecuperables += 1

    return Resultado(procesados=procesados, irrecuperables=irrecuperables)
