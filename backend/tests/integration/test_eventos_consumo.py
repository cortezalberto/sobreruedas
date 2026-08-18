"""Consumo de eventos de dominio — C-02, tareas 5.4 a 5.9.

Contra Redis y PostgreSQL reales (regla dura 8). Lo que se prueba —consumer
groups, mensajes pendientes, reentrega tras una caida— **solo existe en Redis**:
un doble en memoria probaria el doble.

Ver `design.md` D-10 de C-02.
"""

from __future__ import annotations

import uuid
from typing import Any, cast

import pytest
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.events import (
    STREAM_IRRECUPERABLES,
    Sobre,
    consumir,
    crear_grupo,
    espera_del_intento,
    nombre_del_stream,
    publicar,
)
from app.db.session import sesion_de_tenant, tenant_actual

from .soporte import DSN_APLICACION as DSN

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _con_la_base_migrada(base_migrada: None) -> None:
    """El consumidor deduplica contra `idempotency_keys` (migracion 003)."""


@pytest.fixture
def tipo() -> str:
    return f"prueba.sucedio_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def grupo() -> str:
    return f"grupo-{uuid.uuid4().hex[:8]}"


async def sin_dormir(_: float) -> None:
    """Sustituye la espera real. Ver el docstring de `consumir`."""


class ManejadorQueAnota:
    """Anota cada sobre que recibe y bajo que contexto de tenant lo recibio."""

    def __init__(self) -> None:
        self.recibidos: list[Sobre] = []
        self.contextos: list[uuid.UUID | None] = []

    async def __call__(self, sobre: Sobre) -> None:
        self.recibidos.append(sobre)
        self.contextos.append(tenant_actual())


class ManejadorQueFalla:
    """Falla las primeras `veces_que_falla` invocaciones y despues anda."""

    def __init__(self, veces_que_falla: int) -> None:
        self.veces_que_falla = veces_que_falla
        self.invocaciones = 0

    async def __call__(self, sobre: Sobre) -> None:
        self.invocaciones += 1
        if self.invocaciones <= self.veces_que_falla:
            raise RuntimeError(f"fallo numero {self.invocaciones}")


# ── 5.4 · Se consume, se confirma, y el pendiente queda en cero ──────────────


async def test_el_evento_publicado_se_consume_y_se_confirma(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    sobre = await publicar(tipo, tenant_id=tenant, payload={"a": 1}, cliente=redis)
    manejador = ManejadorQueAnota()

    resultado = await consumir(
        redis, tipo, grupo=grupo, consumidor="c1", manejador=manejador, dsn=DSN
    )

    assert resultado.procesados == 1
    assert [s.event_id for s in manejador.recibidos] == [sobre.event_id]

    # Confirmado: nada pendiente. Es lo que distingue "se proceso" de "se leyo".
    pendientes = await redis.xpending(nombre_del_stream(tipo), grupo)
    assert pendientes["pending"] == 0


async def test_el_payload_llega_intacto(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    await publicar(tipo, tenant_id=tenant, payload={"anidado": {"x": [1, 2]}}, cliente=redis)
    manejador = ManejadorQueAnota()

    await consumir(redis, tipo, grupo=grupo, consumidor="c1", manejador=manejador, dsn=DSN)

    assert manejador.recibidos[0].payload == {"anidado": {"x": [1, 2]}}


# ── 5.5 · El consumidor procesa bajo el contexto del tenant del sobre ────────


async def test_el_manejador_corre_bajo_el_contexto_del_tenant_del_evento(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    """El aislamiento no puede depender de estar atendiendo una peticion (D-10)."""
    await publicar(tipo, tenant_id=tenant, payload={}, cliente=redis)
    manejador = ManejadorQueAnota()

    await consumir(redis, tipo, grupo=grupo, consumidor="c1", manejador=manejador, dsn=DSN)

    assert manejador.contextos == [tenant], "el manejador corrio sin el contexto del sobre"


async def test_el_consumidor_no_ve_datos_de_otro_tenant(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    """La prueba que importa: consulta de verdad y solo trae lo suyo."""
    otro = uuid.uuid4()
    etiqueta_ajena = f"del-otro-{uuid.uuid4().hex[:8]}"

    async with sesion_de_tenant(otro, dsn=DSN) as sesion:
        await sesion.execute(
            text("INSERT INTO platform_probe (tenant_id, etiqueta) VALUES (:t, :e)"),
            {"t": str(otro), "e": etiqueta_ajena},
        )

    visto: list[int] = []

    async def manejador(sobre: Sobre) -> None:
        async with sesion_de_tenant(sobre.tenant_id, dsn=DSN) as sesion:
            total = await sesion.execute(text("SELECT count(*) FROM platform_probe"))
            visto.append(int(total.scalar_one()))

    await publicar(tipo, tenant_id=tenant, payload={}, cliente=redis)
    await consumir(redis, tipo, grupo=grupo, consumidor="c1", manejador=manejador, dsn=DSN)

    assert visto == [0], "el consumidor vio filas de otro tenant"


async def test_el_contexto_no_sobrevive_al_consumo(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    """Si sobreviviera, el proximo trabajo heredaria el tenant del anterior."""
    await publicar(tipo, tenant_id=tenant, payload={}, cliente=redis)

    await consumir(
        redis, tipo, grupo=grupo, consumidor="c1", manejador=ManejadorQueAnota(), dsn=DSN
    )

    assert tenant_actual() is None


# ── 5.6 · Reintento con espera creciente y acotada ───────────────────────────


async def test_un_fallo_transitorio_termina_procesado(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    await publicar(tipo, tenant_id=tenant, payload={}, cliente=redis)
    manejador = ManejadorQueFalla(veces_que_falla=2)

    resultado = await consumir(
        redis,
        tipo,
        grupo=grupo,
        consumidor="c1",
        manejador=manejador,
        dsn=DSN,
        dormir=sin_dormir,
    )

    assert manejador.invocaciones == 3
    assert resultado.procesados == 1
    assert resultado.irrecuperables == 0


async def test_la_espera_crece_entre_intentos(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    """Reintentar de inmediato contra algo caido le agrega carga."""
    await publicar(tipo, tenant_id=tenant, payload={}, cliente=redis)
    esperas: list[float] = []

    async def anotar(segundos: float) -> None:
        esperas.append(segundos)

    await consumir(
        redis,
        tipo,
        grupo=grupo,
        consumidor="c1",
        manejador=ManejadorQueFalla(veces_que_falla=3),
        dsn=DSN,
        dormir=anotar,
    )

    assert len(esperas) == 3
    assert esperas == sorted(esperas), f"la espera no crece: {esperas}"
    assert len(set(esperas)) == len(esperas), f"la espera se repite: {esperas}"


def test_la_espera_duplica_y_arranca_en_la_base() -> None:
    """Probar la formula aparte: en el test de arriba solo se ve que crece."""
    assert espera_del_intento(1, base=1.0) == 1.0
    assert espera_del_intento(2, base=1.0) == 2.0
    assert espera_del_intento(3, base=1.0) == 4.0


async def test_los_reintentos_estan_acotados(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    """Sin techo, un evento que siempre falla reintenta para siempre."""
    await publicar(tipo, tenant_id=tenant, payload={}, cliente=redis)
    manejador = ManejadorQueFalla(veces_que_falla=999)

    await consumir(
        redis,
        tipo,
        grupo=grupo,
        consumidor="c1",
        manejador=manejador,
        dsn=DSN,
        reintentos=4,
        dormir=sin_dormir,
    )

    assert manejador.invocaciones == 4


# ── 5.7 · Irrecuperables ─────────────────────────────────────────────────────


async def test_el_evento_agotado_queda_registrado_con_el_motivo(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    """Con el motivo del ULTIMO fallo: sin eso hay el que, pero no el por que."""
    sobre = await publicar(tipo, tenant_id=tenant, payload={}, cliente=redis)
    antes = await redis.xlen(STREAM_IRRECUPERABLES)

    async def siempre_falla(_: Sobre) -> None:
        raise ValueError("la dependencia no vuelve")

    resultado = await consumir(
        redis,
        tipo,
        grupo=grupo,
        consumidor="c1",
        manejador=siempre_falla,
        dsn=DSN,
        reintentos=2,
        dormir=sin_dormir,
    )

    assert resultado.irrecuperables == 1
    assert await redis.xlen(STREAM_IRRECUPERABLES) == antes + 1

    _, campos = (await redis.xrevrange(STREAM_IRRECUPERABLES, count=1))[0]
    assert campos["event_id"] == str(sobre.event_id)
    assert "la dependencia no vuelve" in campos["motivo"]
    assert campos["stream_original"] == nombre_del_stream(tipo)


async def test_uno_malo_no_tapa_la_cola(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    """El motivo por el que el agotado se confirma en el original.

    Si quedara pendiente, el proximo lote lo volveria a tomar antes que a nadie
    y los que vienen atras no avanzarian nunca.
    """
    malo = await publicar(tipo, tenant_id=tenant, payload={"malo": True}, cliente=redis)
    bueno = await publicar(tipo, tenant_id=tenant, payload={"malo": False}, cliente=redis)

    procesados: list[uuid.UUID] = []

    async def falla_con_el_malo(sobre: Sobre) -> None:
        if sobre.payload.get("malo"):
            raise RuntimeError("este nunca va a andar")
        procesados.append(sobre.event_id)

    resultado = await consumir(
        redis,
        tipo,
        grupo=grupo,
        consumidor="c1",
        manejador=falla_con_el_malo,
        dsn=DSN,
        reintentos=2,
        dormir=sin_dormir,
    )

    assert resultado.irrecuperables == 1
    assert procesados == [bueno.event_id]
    assert malo.event_id not in procesados

    # Y la cola quedo limpia: nada pendiente trabando el proximo lote.
    pendientes = await redis.xpending(nombre_del_stream(tipo), grupo)
    assert pendientes["pending"] == 0


# ── 5.8 · Entrega repetida: el efecto no se aplica dos veces ─────────────────


async def test_el_mismo_evento_entregado_dos_veces_se_procesa_una(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    """Redis Streams garantiza "al menos una vez"; la no duplicacion es de aca.

    Se publica el MISMO sobre dos veces en el stream —que es lo que pasa cuando
    un publicador reintenta— y el manejador tiene que correr una sola.
    """
    sobre = await publicar(tipo, tenant_id=tenant, payload={"a": 1}, cliente=redis)
    await redis.xadd(nombre_del_stream(tipo), cast("dict[Any, Any]", sobre.a_redis()))

    manejador = ManejadorQueAnota()
    resultado = await consumir(
        redis, tipo, grupo=grupo, consumidor="c1", manejador=manejador, dsn=DSN
    )

    assert resultado.procesados == 2, "los dos mensajes tienen que confirmarse"
    assert len(manejador.recibidos) == 1, "el efecto se aplico dos veces"


# ── 5.9 · Caida antes de confirmar ───────────────────────────────────────────


async def test_si_el_consumidor_cae_antes_de_confirmar_el_evento_vuelve(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    """El evento no se pierde: queda pendiente y se retoma.

    Se simula la caida leyendo el mensaje con `xreadgroup` y no confirmandolo,
    que es exactamente el estado en que queda un proceso que murio a mitad de
    camino.
    """
    await publicar(tipo, tenant_id=tenant, payload={}, cliente=redis)
    await crear_grupo(redis, tipo, grupo)

    # El consumidor "c1" toma el mensaje y muere sin confirmar.
    tomados = await redis.xreadgroup(grupo, "c1", {nombre_del_stream(tipo): ">"}, count=10)
    assert tomados, "no se tomo ningun mensaje"

    pendientes = await redis.xpending(nombre_del_stream(tipo), grupo)
    assert pendientes["pending"] == 1

    # El mismo consumidor vuelve a levantar y retoma lo suyo.
    manejador = ManejadorQueAnota()
    resultado = await consumir(
        redis, tipo, grupo=grupo, consumidor="c1", manejador=manejador, dsn=DSN
    )

    assert resultado.procesados == 1, "el evento quedo varado"
    assert len(manejador.recibidos) == 1

    pendientes = await redis.xpending(nombre_del_stream(tipo), grupo)
    assert pendientes["pending"] == 0


async def test_sin_pendientes_no_se_reprocesa_lo_ya_confirmado(
    redis: Redis, tenant: uuid.UUID, tipo: str, grupo: str
) -> None:
    """Contrapeso del anterior: retomar pendientes no puede traer lo confirmado."""
    await publicar(tipo, tenant_id=tenant, payload={}, cliente=redis)
    manejador = ManejadorQueAnota()

    primera = await consumir(
        redis, tipo, grupo=grupo, consumidor="c1", manejador=manejador, dsn=DSN
    )
    segunda = await consumir(
        redis, tipo, grupo=grupo, consumidor="c1", manejador=manejador, dsn=DSN
    )

    assert primera.procesados == 1
    assert segunda.procesados == 0
    assert len(manejador.recibidos) == 1
