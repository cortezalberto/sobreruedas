"""Eventos de dominio contra Redis real — C-02, tareas 5.1 y 5.3.

Sin doble de Redis (regla dura 8): lo que se prueba es el comportamiento de
Redis Streams con consumer groups —confirmacion explicita, pendientes,
reentrega—, y ninguna de esas cosas existe en un diccionario en memoria.

Ver `design.md` D-10 de C-02.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from redis.asyncio import Redis

from app.core.events import (
    EventoInvalido,
    Sobre,
    nombre_del_stream,
    publicar,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def tipo() -> str:
    """Un tipo distinto por test: cada uno estrena su stream y no ve los ajenos."""
    return f"prueba.sucedio_{uuid.uuid4().hex[:8]}"


# ── 5.1 · El sobre canonico ──────────────────────────────────────────────────


async def test_el_sobre_lleva_las_seis_cosas(redis: Redis, tenant: uuid.UUID, tipo: str) -> None:
    """Identificador, tipo, version, tenant, instante con zona y contenido."""
    sobre = await publicar(tipo, tenant_id=tenant, payload={"patente": "AB123CD"}, cliente=redis)

    assert isinstance(sobre.event_id, uuid.UUID)
    assert sobre.type == tipo
    assert sobre.version >= 1
    assert sobre.tenant_id == tenant
    assert sobre.payload == {"patente": "AB123CD"}

    # Con zona horaria y no ingenuo: un instante sin zona es ambiguo apenas
    # cruza una maquina, y estos eventos los consume otro proceso.
    assert sobre.occurred_at.tzinfo is not None


async def test_dos_publicaciones_del_mismo_hecho_llevan_identificadores_distintos(
    redis: Redis, tenant: uuid.UUID, tipo: str
) -> None:
    """El `event_id` identifica la PUBLICACION, no el hecho.

    Es lo que le permite al consumidor reconocer una reentrega: si dos
    publicaciones compartieran identificador, "ya procese este" no distinguiria
    un reintento de un hecho nuevo idéntico.
    """
    payload = {"patente": "AB123CD"}

    uno = await publicar(tipo, tenant_id=tenant, payload=payload, cliente=redis)
    otro = await publicar(tipo, tenant_id=tenant, payload=payload, cliente=redis)

    assert uno.event_id != otro.event_id


async def test_el_sobre_sobrevive_la_ida_y_vuelta_por_redis(
    redis: Redis, tenant: uuid.UUID, tipo: str
) -> None:
    """Lo que se lee del stream tiene que ser lo que se publico.

    Sin esto, los tests de arriba probarian el constructor del dataclass y no la
    serializacion, que es donde se pierden las zonas horarias y los UUID.
    """
    original = await publicar(
        tipo,
        tenant_id=tenant,
        payload={"anidado": {"a": 1}, "lista": [1, 2]},
        cliente=redis,
    )

    entradas = await redis.xrange(nombre_del_stream(tipo))
    assert len(entradas) == 1
    _, campos = entradas[0]

    recuperado = Sobre.desde_redis(campos)
    assert recuperado == original


# ── 5.1 · Un evento sin tenant se rechaza AL PUBLICAR ────────────────────────


@pytest.mark.parametrize("sin_tenant", [None, "", "no-es-uuid", 42])
async def test_publicar_sin_tenant_se_rechaza(redis: Redis, tipo: str, sin_tenant: object) -> None:
    """Se rechaza en la publicacion y no en el consumo: fallar cerca de la causa.

    Un evento sin tenant que llega al consumidor ya perdio el contexto de quien
    lo origino, y ahi no hay forma de reconstruirlo — solo de descartarlo con un
    error lejos de quien lo produjo.
    """
    with pytest.raises(EventoInvalido):
        await publicar(tipo, tenant_id=sin_tenant, payload={"a": 1}, cliente=redis)


async def test_el_evento_rechazado_no_llega_al_stream(redis: Redis, tipo: str) -> None:
    """Rechazar no alcanza: no tiene que quedar nada publicado."""
    with pytest.raises(EventoInvalido):
        await publicar(tipo, tenant_id=None, payload={"a": 1}, cliente=redis)

    assert await redis.exists(nombre_del_stream(tipo)) == 0


# ── 5.1 · El tipo nombra un hecho, no una orden ──────────────────────────────


@pytest.mark.parametrize(
    "mal_formado",
    ["sin_punto", "DOMINIO.Hecho", "dominio..hecho", "", "dominio.hecho.de_mas", " x.y"],
)
async def test_un_tipo_mal_formado_se_rechaza(
    redis: Redis, tenant: uuid.UUID, mal_formado: str
) -> None:
    """`dominio.hecho`, en minusculas y en dos partes.

    La forma se verifica; el TIEMPO VERBAL no. Que `vehicle.created` sea pasado
    y `vehicle.create` imperativo es una convencion de `D-10` que ningun test
    puede comprobar sin conjugar castellano e ingles. Se revisa leyendo.
    """
    with pytest.raises(EventoInvalido):
        await publicar(mal_formado, tenant_id=tenant, payload={}, cliente=redis)


async def test_un_tipo_bien_formado_se_acepta(redis: Redis, tenant: uuid.UUID) -> None:
    """Contrapeso: una validacion demasiado estricta rechazaria todo."""
    sobre = await publicar("vehicle.created", tenant_id=tenant, payload={}, cliente=redis)
    assert sobre.type == "vehicle.created"


# ── 5.3 · Publicar no depende de que haya alguien escuchando ─────────────────


async def test_publicar_sin_consumidores_es_exitoso(
    redis: Redis, tenant: uuid.UUID, tipo: str
) -> None:
    """Nadie suscrito, y la publicacion igual funciona.

    Es la diferencia entre eventos y llamadas: quien publica informa un hecho y
    sigue. Si necesitara que alguien lo escuche, seria una llamada disfrazada y
    la caida de un consumidor voltearia la peticion que origino el evento.
    """
    sobre = await publicar(tipo, tenant_id=tenant, payload={"a": 1}, cliente=redis)

    assert await redis.xlen(nombre_del_stream(tipo)) == 1
    assert sobre.event_id


async def test_cada_tipo_tiene_su_propio_stream(redis: Redis, tenant: uuid.UUID) -> None:
    """Un stream por tipo: un consumidor se suscribe a lo que le importa.

    Con un unico stream compartido, todo consumidor recibiria todo y tendria que
    descartar la mayor parte — y un tipo ruidoso marcaria el ritmo de los demas.
    """
    sufijo = uuid.uuid4().hex[:8]
    uno, otro = f"a.hecho_{sufijo}", f"b.hecho_{sufijo}"

    await publicar(uno, tenant_id=tenant, payload={}, cliente=redis)

    assert await redis.xlen(nombre_del_stream(uno)) == 1
    assert await redis.exists(nombre_del_stream(otro)) == 0


async def test_el_instante_es_el_de_la_publicacion_y_avanza(
    redis: Redis, tenant: uuid.UUID, tipo: str
) -> None:
    antes = datetime.now(UTC)
    sobre = await publicar(tipo, tenant_id=tenant, payload={}, cliente=redis)
    despues = datetime.now(UTC)

    assert antes <= sobre.occurred_at <= despues
