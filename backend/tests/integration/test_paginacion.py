"""Paginacion por cursor contra PostgreSQL real — C-02, tareas 4.4 y 4.6.

Contra la base de verdad y no contra listas en memoria (regla dura 8): lo que se
prueba aca es el comportamiento de un `WHERE (created_at, id) > (:c, :i)` con
`ORDER BY` sobre datos concretos. Una lista de Python probaria el `sorted` de
Python.

Se usa `platform_probe` como tabla de trabajo: tiene `tenant_id`, `id`,
`created_at` y politica RLS, que es exactamente la forma de toda tabla de
negocio que va a existir. Para eso quedo como testigo permanente.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import Column, DateTime, MetaData, Select, Table, Uuid, select, text

from app.core.pagination import (
    TAMANO_MAXIMO,
    CursorInvalido,
    acotar_tamano,
    codificar_cursor,
    decodificar_cursor,
    paginar,
)
from app.db.session import sesion_de_tenant, violaciones_de_aislamiento

from .soporte import DSN_APLICACION as DSN

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _con_la_base_migrada(base_migrada: None) -> None:
    """`platform_probe` la crea la migracion 002."""


# Definicion Core de la tabla testigo. No es un modelo ORM a proposito: la
# paginacion tiene que servir para cualquier `select`, y atarla a una `Base`
# declarativa la haria depender de algo que todavia no existe.
_metadata = MetaData()
PROBE = Table(
    "platform_probe",
    _metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, nullable=False),
    Column("etiqueta", type_=None),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

SQL_INSERTAR = text(
    "INSERT INTO platform_probe (tenant_id, etiqueta, created_at) "
    "VALUES (:t, :e, :c) RETURNING id"
)


async def sembrar(tenant: uuid.UUID, cuantos: int, *, mismo_instante: bool = False) -> list[str]:
    """Crea `cuantos` registros y devuelve sus etiquetas en orden de creacion.

    `mismo_instante` fuerza `created_at` identico en todos: es el caso que
    distingue ordenar por `(created_at, id)` de ordenar solo por `created_at`.
    """
    etiquetas = [f"item-{numero:03d}" for numero in range(cuantos)]
    base = datetime.fromisoformat("2026-01-01T00:00:00+00:00")

    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        for numero, etiqueta in enumerate(etiquetas):
            instante = base if mismo_instante else base + timedelta(seconds=numero)
            await sesion.execute(SQL_INSERTAR, {"t": str(tenant), "e": etiqueta, "c": instante})
    return etiquetas


def consulta_del_tenant(tenant: uuid.UUID) -> Select[Any]:
    """El `select` que la aplicacion haria: con su filtro explicito de tenant.

    El filtro va aunque RLS ya acote: es la capa 3 de `ADR-006`, y la
    paginacion no es una excepcion a las tres capas.
    """
    return select(PROBE.c.id, PROBE.c.created_at, PROBE.c.etiqueta).where(
        PROBE.c.tenant_id == tenant
    )


async def recorrer_todo(tenant: uuid.UUID, tamano: int) -> tuple[list[str], int]:
    """Recorre el listado entero siguiendo los cursores. Devuelve (etiquetas, paginas)."""
    vistas: list[str] = []
    cursor: str | None = None
    paginas = 0

    while True:
        async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
            pagina = await paginar(
                sesion,
                consulta_del_tenant(tenant),
                tenant=tenant,
                cursor=cursor,
                tamano=tamano,
            )
        paginas += 1
        vistas.extend(fila.etiqueta for fila in pagina.items)
        if pagina.cursor_siguiente is None:
            return vistas, paginas
        cursor = pagina.cursor_siguiente
        assert paginas < 100, "el recorrido no termina: el cursor no avanza"


# ── 4.4 · Recorrido completo, sin repetir ni saltear ─────────────────────────


async def test_el_recorrido_completo_ve_cada_elemento_exactamente_una_vez(
    tenant: uuid.UUID,
) -> None:
    esperadas = await sembrar(tenant, 25)

    vistas, paginas = await recorrer_todo(tenant, tamano=10)

    assert vistas == esperadas, "el recorrido saltea, repite o desordena"
    assert len(vistas) == len(set(vistas))
    assert paginas == 3, f"25 elementos de a 10 son 3 paginas, no {paginas}"


async def test_con_instantes_iguales_el_recorrido_sigue_siendo_exacto(
    tenant: uuid.UUID,
) -> None:
    """El caso que justifica ordenar por `(created_at, id)` y no solo por fecha.

    Con `created_at` identico en todas las filas, ordenar solo por fecha deja el
    orden a criterio del motor: dos paginas consecutivas pueden traer la misma
    fila o saltearse una, sin que nada falle de forma visible.
    """
    esperadas = await sembrar(tenant, 12, mismo_instante=True)

    vistas, _ = await recorrer_todo(tenant, tamano=5)

    assert sorted(vistas) == sorted(esperadas)
    assert len(vistas) == len(set(vistas)), "hay elementos repetidos entre paginas"


# ── 4.4 · La ultima pagina se distingue sin ambiguedad ───────────────────────


async def test_la_ultima_pagina_no_ofrece_cursor(tenant: uuid.UUID) -> None:
    """`None` y no una lista vacia: la ultima pagina se sabe al recibirla.

    Si la unica forma de saber que se termino fuera pedir una pagina mas y que
    viniera vacia, todo recorrido gastaria una consulta de mas.
    """
    await sembrar(tenant, 5)

    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        pagina = await paginar(sesion, consulta_del_tenant(tenant), tenant=tenant, tamano=10)

    assert len(pagina.items) == 5
    assert pagina.cursor_siguiente is None


async def test_una_pagina_exactamente_llena_sabe_que_es_la_ultima(
    tenant: uuid.UUID,
) -> None:
    """El borde clasico: tantos elementos como el tamano de pagina.

    Sin traerse un elemento de mas para mirar, este caso ofreceria un cursor a
    una pagina siguiente que esta vacia.
    """
    await sembrar(tenant, 10)

    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        pagina = await paginar(sesion, consulta_del_tenant(tenant), tenant=tenant, tamano=10)

    assert len(pagina.items) == 10
    assert pagina.cursor_siguiente is None


async def test_listado_vacio(tenant: uuid.UUID) -> None:
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        pagina = await paginar(sesion, consulta_del_tenant(tenant), tenant=tenant)

    assert pagina.items == []
    assert pagina.cursor_siguiente is None


# ── 4.4 · El tamano se acota, no falla ───────────────────────────────────────


def test_pedir_mas_que_el_maximo_se_acota_al_maximo() -> None:
    assert acotar_tamano(TAMANO_MAXIMO + 500) == TAMANO_MAXIMO


def test_no_pedir_nada_usa_el_tamano_por_defecto() -> None:
    from app.core.pagination import TAMANO_POR_DEFECTO

    assert acotar_tamano(None) == TAMANO_POR_DEFECTO


@pytest.mark.parametrize("pedido", [0, -1, -100])
def test_un_tamano_absurdo_se_acota_en_vez_de_romper(pedido: int) -> None:
    """Un tamano de cero pagina para siempre sin avanzar."""
    assert acotar_tamano(pedido) >= 1


async def test_el_tamano_acotado_gobierna_la_consulta_de_verdad(tenant: uuid.UUID) -> None:
    """`acotar_tamano` podria estar bien y `paginar` ignorarlo igual."""
    await sembrar(tenant, TAMANO_MAXIMO + 5)

    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        pagina = await paginar(
            sesion,
            consulta_del_tenant(tenant),
            tenant=tenant,
            tamano=TAMANO_MAXIMO + 500,
        )

    assert len(pagina.items) == TAMANO_MAXIMO


# ── 4.4 · Cursor invalido ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("cursor", "por_que"),
    [
        ("no-es-base64-!!!", "caracteres fuera del alfabeto"),
        ("YWJjZA", "base64 valido que no es JSON"),
        ("eyJ0IjogIm5vLWVzLXV1aWQifQ", "JSON valido con un tenant que no es UUID"),
        ("", "cadena vacia"),
    ],
)
def test_un_cursor_que_no_se_puede_interpretar_se_rechaza(cursor: str, por_que: str) -> None:
    with pytest.raises(CursorInvalido):
        decodificar_cursor(cursor, tenant=uuid.uuid4())


def test_el_rechazo_no_incluye_el_cursor_recibido() -> None:
    """El cursor lleva el tenant adentro. No tiene por que volver en un log."""
    cursor = codificar_cursor(
        tenant=uuid.uuid4(), created_at=datetime.now(tz=None).astimezone(), id=uuid.uuid4()
    )
    with pytest.raises(CursorInvalido) as capturado:
        decodificar_cursor(cursor, tenant=uuid.uuid4())

    assert cursor not in str(capturado.value)


# ── 4.6 · El cursor no cruza tenants ─────────────────────────────────────────


async def test_un_cursor_de_otro_tenant_no_devuelve_nada_de_ese_tenant(
    tenant: uuid.UUID, otro_tenant: uuid.UUID
) -> None:
    """La capa 2 sosteniendose sola.

    RLS igual taparia esto —esa es la gracia de las tres capas—, pero la
    paginacion no puede depender de que la de abajo funcione: si el cursor de un
    tenant sirviera en otro, seria un `WHERE created_at > ...` perfectamente
    valido y el unico que lo frenaria seria el motor.
    """
    await sembrar(otro_tenant, 5)

    async with sesion_de_tenant(otro_tenant, dsn=DSN) as sesion:
        pagina_ajena = await paginar(
            sesion, consulta_del_tenant(otro_tenant), tenant=otro_tenant, tamano=2
        )
    cursor_ajeno = pagina_ajena.cursor_siguiente
    assert cursor_ajeno is not None

    with pytest.raises(CursorInvalido):
        decodificar_cursor(cursor_ajeno, tenant=tenant)


async def test_presentar_un_cursor_ajeno_cuenta_como_intento_de_acceso_cruzado(
    tenant: uuid.UUID, otro_tenant: uuid.UUID
) -> None:
    """No alcanza con rechazarlo: hay que contarlo.

    `RN-MT-08` pide que la metrica centinela de violaciones de aislamiento sea
    siempre cero, y un cursor de otro tenant es precisamente un intento de
    acceso cruzado. Rechazarlo en silencio lo dejaria sin registrar, que es como
    un ataque de enumeracion pasa desapercibido.
    """
    cursor_ajeno = codificar_cursor(
        tenant=otro_tenant,
        created_at=datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
        id=uuid.uuid4(),
    )

    antes = violaciones_de_aislamiento()
    with pytest.raises(CursorInvalido):
        decodificar_cursor(cursor_ajeno, tenant=tenant)

    assert violaciones_de_aislamiento() == antes + 1


# ── El cursor es opaco ───────────────────────────────────────────────────────


def test_el_cursor_no_expone_su_contenido_a_simple_vista() -> None:
    """Opaco: quien lo recibe no deberia poder leerlo ni construirlo a mano.

    No es una defensa criptografica y no pretende serlo — ver el encabezado de
    `core/pagination.py`. Es que el contenido no sea parte del contrato: un
    cliente que aprenda a parsearlo empieza a depender de un formato interno.
    """
    tenant = uuid.uuid4()
    cursor = codificar_cursor(
        tenant=tenant,
        created_at=datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
        id=uuid.uuid4(),
    )

    assert str(tenant) not in cursor
    assert "created_at" not in cursor


def test_el_cursor_sobrevive_la_ida_y_vuelta() -> None:
    tenant = uuid.uuid4()
    identificador = uuid.uuid4()
    instante = datetime.fromisoformat("2026-03-15T12:34:56.789+00:00")

    posicion = decodificar_cursor(
        codificar_cursor(tenant=tenant, created_at=instante, id=identificador),
        tenant=tenant,
    )

    assert posicion.created_at == instante
    assert posicion.id == identificador
