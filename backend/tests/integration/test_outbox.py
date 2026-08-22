"""El outbox transaccional contra PostgreSQL y Redis reales — [`ADR-036`].

Sin dobles (regla dura 8), y acá no es una formalidad: **lo que se prueba es que
la fila y el cambio compartan transaccion**, y una transaccion no existe en un
diccionario en memoria. Un doble haria pasar en verde exactamente el bug que
este mecanismo existe para impedir.

EL TEST QUE JUSTIFICA TODO EL DISEÑO es `test_un_rollback_no_deja_ni_fila_ni_evento`.
Los demas comprueban partes; ese comprueba la garantia.

[`ADR-036`]: ../../../docs/adr/ADR-036-outbox-transaccional-para-eventos-de-dominio.md
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
import sqlalchemy as sa
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import EventoInvalido, nombre_del_stream
from app.core.outbox import CLAVE_EN_SESION, OutboxEvent, drenar, pendientes, registrar
from app.db.session import sesion_de_tenant

from .soporte import DSN_APLICACION

pytestmark = pytest.mark.integration


@pytest.fixture
def tipo() -> str:
    """Un tipo distinto por test: cada uno estrena su stream y no ve los ajenos."""
    return f"prueba.sucedio_{uuid.uuid4().hex[:8]}"


async def _filas(sesion: AsyncSession) -> list[OutboxEvent]:
    resultado = await sesion.execute(sa.select(OutboxEvent).order_by(OutboxEvent.created_at))
    return list(resultado.scalars())


# ── La fila viaja en la transaccion ──────────────────────────────────────────


async def test_registrar_escribe_la_fila_en_la_misma_transaccion(
    base_migrada: None, sesion: AsyncSession, tenant: uuid.UUID, tipo: str
) -> None:
    """Sin commit todavia, la fila ya se ve DESDE ESTA transaccion."""
    registrar(sesion, tipo, tenant_id=tenant, payload={"vehicle_id": "x"})
    await sesion.flush()

    filas = await _filas(sesion)

    assert len(filas) == 1
    assert filas[0].type == tipo
    assert filas[0].tenant_id == tenant
    assert filas[0].published_at is None, "recien registrada, no puede estar publicada"


async def test_registrar_no_toca_la_red(
    base_migrada: None, sesion: AsyncSession, tenant: uuid.UUID, tipo: str, redis: Redis
) -> None:
    """Registrar NO publica. Si publicara, publicaria antes del commit.

    Es la mitad del contrato que no se ve en la firma: `registrar` no es `async`
    justamente para que no pueda esperar a Redis, pero eso no impediria un
    `create_task`. Esto lo fija como comportamiento.
    """
    registrar(sesion, tipo, tenant_id=tenant, payload={"vehicle_id": "x"})
    await sesion.flush()

    assert await redis.exists(nombre_del_stream(tipo)) == 0


async def test_un_rollback_no_deja_ni_fila_ni_evento(
    base_migrada: None, tenant: uuid.UUID, tipo: str, redis: Redis
) -> None:
    """LA GARANTIA. Es el test por el que existe la tabla.

    Se simula lo que pasa de verdad: el servicio registra, el endpoint levanta
    despues, y la transaccion revierte. Con un `await publicar(...)` en el
    servicio, el evento ya estaria en el stream y no habria forma de sacarlo —
    un stream es append-only.
    """
    with pytest.raises(RuntimeError):
        async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
            registrar(sesion, tipo, tenant_id=tenant, payload={"vehicle_id": "x"})
            await sesion.flush()
            raise RuntimeError("el endpoint se cayo despues del flush")

    # Ni la fila...
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as verificacion:
        assert await _filas(verificacion) == []

    # ...ni el evento.
    assert await redis.exists(nombre_del_stream(tipo)) == 0


# ── El drenaje ───────────────────────────────────────────────────────────────


async def test_drenar_publica_y_marca(
    base_migrada: None, tenant: uuid.UUID, tipo: str, redis: Redis
) -> None:
    """El camino feliz completo, con el commit en el medio."""
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        sesion.info["tenant_id"] = tenant
        sobre = registrar(sesion, tipo, tenant_id=tenant, payload={"vehicle_id": "x"})

    # Acá ya commiteo, igual que cuando la dependency sale de su `async with`.
    assert await drenar(sesion, dsn=DSN_APLICACION, cliente=redis) == 1

    mensajes = await redis.xrange(nombre_del_stream(tipo))
    assert len(mensajes) == 1
    _, campos = mensajes[0]
    assert campos["event_id"] == str(sobre.event_id)
    assert campos["tenant_id"] == str(tenant)

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as verificacion:
        filas = await _filas(verificacion)
        assert filas[0].published_at is not None, "salio y quedo sin marcar"


async def test_drenar_sin_nada_anotado_no_hace_nada(
    base_migrada: None, sesion: AsyncSession, tenant: uuid.UUID
) -> None:
    """La mayoria de las peticiones no publican eventos y no deben pagar nada."""
    sesion.info["tenant_id"] = tenant

    assert await drenar(sesion, dsn=DSN_APLICACION) == 0


async def test_drenar_vacia_lo_anotado_y_no_republica(
    base_migrada: None, tenant: uuid.UUID, tipo: str, redis: Redis
) -> None:
    """Un segundo drenaje sobre la misma sesion no manda el evento dos veces.

    La idempotencia del consumidor existe para las reentregas del transporte, no
    para gastarla tapando un error nuestro.
    """
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        sesion.info["tenant_id"] = tenant
        registrar(sesion, tipo, tenant_id=tenant, payload={"vehicle_id": "x"})

    await drenar(sesion, dsn=DSN_APLICACION, cliente=redis)
    assert await drenar(sesion, dsn=DSN_APLICACION, cliente=redis) == 0
    assert pendientes(sesion) == []
    assert len(await redis.xrange(nombre_del_stream(tipo))) == 1


async def test_si_el_publish_falla_la_peticion_no_rompe_y_la_fila_queda_pendiente(
    base_migrada: None, tenant: uuid.UUID, tipo: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Redis caido despues del commit no puede convertirse en un error.

    La peticion YA termino bien: el vehiculo existe y el usuario tiene su 201.
    Levantar acá le mentiria sobre lo que pasó — y encima el 500 llegaria
    despues de que el recurso se creo, que es el peor mensaje posible.

    Lo que SI tiene que quedar es la evidencia: la fila sin marcar.
    """

    async def _explota(*_args: object, **_kwargs: object) -> None:
        raise ConnectionError("redis se cayo")

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        sesion.info["tenant_id"] = tenant
        registrar(sesion, tipo, tenant_id=tenant, payload={"vehicle_id": "x"})

    monkeypatch.setattr("app.core.outbox.publicar_sobre", _explota)

    assert await drenar(sesion, dsn=DSN_APLICACION) == 0

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as verificacion:
        filas = await _filas(verificacion)
        assert len(filas) == 1
        assert filas[0].published_at is None, "no salio y quedo marcada como publicada"


# ── Aislamiento ──────────────────────────────────────────────────────────────


async def test_un_tenant_no_ve_el_outbox_de_otro(
    base_migrada: None, tenant: uuid.UUID, otro_tenant: uuid.UUID, tipo: str
) -> None:
    """La politica RLS de la tabla, ejercida.

    Sin esto, el outbox seria una tabla nueva por la que se filtra todo lo que
    las otras protegen: lleva `tenant_id` y `payload` de cada mutacion del
    sistema.
    """
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as del_primero:
        registrar(del_primero, tipo, tenant_id=tenant, payload={"vehicle_id": "x"})

    async with sesion_de_tenant(otro_tenant, dsn=DSN_APLICACION) as del_segundo:
        assert await _filas(del_segundo) == []


async def test_no_se_puede_escribir_en_el_outbox_de_otro(
    base_migrada: None, tenant: uuid.UUID, otro_tenant: uuid.UUID, tipo: str
) -> None:
    """El `WITH CHECK` de la politica, que es la mitad que se olvida.

    `USING` sin `WITH CHECK` deja LEER solo lo propio y ESCRIBIR cualquier cosa:
    una fila con el `tenant_id` de otro entraria, y el que la escribio despues no
    la veria — asi que ni siquiera se enteraria del error.
    """
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        registrar(sesion, tipo, tenant_id=otro_tenant, payload={"vehicle_id": "x"})

        with pytest.raises(Exception, match="(?i)row-level security"):
            await sesion.flush()


async def test_una_sesion_sin_tenant_no_ve_nada(
    base_migrada: None, tenant: uuid.UUID, tipo: str, sesion_sin_tenant: AsyncSession
) -> None:
    """Fallar CERRADO. `NULLIF(..., '')::uuid` da NULL y nada iguala a NULL.

    Importa porque el relay del futuro va a ser justamente una sesion sin tenant,
    y tiene que descubrir que no puede leer — no leerlo todo por accidente.
    """
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        registrar(sesion, tipo, tenant_id=tenant, payload={"vehicle_id": "x"})

    assert await _filas(sesion_sin_tenant) == []


# ── Contrato del registro ────────────────────────────────────────────────────


async def test_un_tipo_mal_formado_rompe_al_registrar_y_no_al_drenar(
    base_migrada: None, sesion: AsyncSession, tenant: uuid.UUID
) -> None:
    """Temprano y dentro de la transaccion, que es donde todavia se puede fallar.

    Descubrirlo en el drenaje seria un error DESPUES del commit: el cambio ya
    ocurrio y el evento se perderia en un log en vez de romper la peticion.
    """
    with pytest.raises(EventoInvalido):
        registrar(sesion, "sinpunto", tenant_id=tenant, payload={})

    assert pendientes(sesion) == []


async def test_el_event_id_es_el_mismo_en_la_fila_y_en_el_stream(
    base_migrada: None, tenant: uuid.UUID, tipo: str, redis: Redis
) -> None:
    """Se genera al REGISTRAR, no al publicar.

    Si se generara en el publish, dos intentos del mismo hecho llevarian
    identificadores distintos y la idempotencia del consumidor —que empareja por
    `event_id`— no los reconoceria como el mismo evento.
    """
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        sesion.info["tenant_id"] = tenant
        sobre = registrar(sesion, tipo, tenant_id=tenant, payload={"vehicle_id": "x"})

    await drenar(sesion, dsn=DSN_APLICACION, cliente=redis)

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as verificacion:
        fila = (await _filas(verificacion))[0]

    _, campos = (await redis.xrange(nombre_del_stream(tipo)))[0]
    assert fila.event_id == sobre.event_id == uuid.UUID(campos["event_id"])


async def test_los_sobres_anotados_viven_en_la_sesion_y_no_en_el_modulo(
    base_migrada: None, tenant: uuid.UUID, otro_tenant: uuid.UUID, tipo: str
) -> None:
    """Dos sesiones concurrentes no se pisan los pendientes.

    Si la lista fuera de modulo —una global— el drenaje de una peticion
    publicaria los eventos de otra, y con el tenant de la primera. Es la clase de
    fuga que no se ve hasta que hay concurrencia real.
    """
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as primera:
        registrar(primera, tipo, tenant_id=tenant, payload={"vehicle_id": "uno"})

        async with sesion_de_tenant(otro_tenant, dsn=DSN_APLICACION) as segunda:
            assert pendientes(segunda) == []
            registrar(segunda, tipo, tenant_id=otro_tenant, payload={"vehicle_id": "dos"})
            assert len(pendientes(segunda)) == 1

        assert len(pendientes(primera)) == 1
        assert primera.info[CLAVE_EN_SESION][0].payload == {"vehicle_id": "uno"}


async def test_el_payload_viaja_como_jsonb_y_vuelve_igual(
    base_migrada: None, sesion: AsyncSession, tenant: uuid.UUID, tipo: str
) -> None:
    """Ida y vuelta por la base sin que se pierda la forma."""
    payload: dict[str, Any] = {"vehicle_id": "x", "from": "available", "to": "reserved"}
    registrar(sesion, tipo, tenant_id=tenant, payload=payload)
    await sesion.flush()

    assert (await _filas(sesion))[0].payload == payload


async def test_si_no_se_puede_marcar_la_fila_el_evento_igual_salio(
    base_migrada: None, tenant: uuid.UUID, tipo: str, redis: Redis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La base cae DESPUES del publish, y eso tampoco puede levantar.

    La consecuencia hay que decirla: la fila queda pendiente de algo que si se
    publico, asi que el relay del futuro lo republicaria. Es "al menos una vez",
    que es el contrato de `ADR-009` y lo que la idempotencia del consumidor ya
    cubre.
    """
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        sesion.info["tenant_id"] = tenant
        registrar(sesion, tipo, tenant_id=tenant, payload={"vehicle_id": "x"})

    def _explota(*_args: object, **_kwargs: object) -> None:
        raise ConnectionError("la base se cayo despues del publish")

    monkeypatch.setattr("app.db.session.sesion_de_tenant", _explota)

    assert await drenar(sesion, dsn=DSN_APLICACION, cliente=redis) == 1
    assert len(await redis.xrange(nombre_del_stream(tipo))) == 1
