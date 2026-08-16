"""Idempotencia de las creaciones — C-02, tareas 4.8 y 4.9.

Contra PostgreSQL real y no contra un doble (regla dura 8): la garantia de este
modulo ES el indice unico `(tenant_id, key)`. Un doble en memoria probaria un
diccionario de Python, que es justamente lo que no protege de dos peticiones
concurrentes.

Ver `design.md` D-5 de C-02.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.core.idempotency import ClaveEnConflicto, ejecutar_idempotente
from app.db.session import sesion_de_tenant

from .soporte import DSN_APLICACION as DSN

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _con_la_base_migrada(base_migrada: None) -> None:
    """`idempotency_keys` la crea la migracion 003."""


@pytest.fixture
def clave() -> str:
    return f"clave-{uuid.uuid4().hex[:12]}"


SQL_CONTAR_RECURSOS = text("SELECT count(*) FROM platform_probe WHERE etiqueta = :e")


class Contador:
    """Una creacion observable: cuenta cuantas veces se ejecuto de verdad.

    Es lo que distingue "devolvio el resultado guardado" de "volvio a crear y
    dio lo mismo porque el test es determinista". Sin esto, un modulo de
    idempotencia que no hace nada pasaria casi todos los tests de este archivo.
    """

    def __init__(self, etiqueta: str) -> None:
        self.etiqueta = etiqueta
        self.veces = 0

    async def __call__(self) -> tuple[dict[str, str], int]:
        self.veces += 1
        return {"etiqueta": self.etiqueta, "intento": str(self.veces)}, 201


async def crear_recurso(tenant: uuid.UUID, etiqueta: str) -> None:
    """Efecto colateral real en la base, para contar recursos creados."""
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        await sesion.execute(
            text("INSERT INTO platform_probe (tenant_id, etiqueta) VALUES (:t, :e)"),
            {"t": str(tenant), "e": etiqueta},
        )


async def recursos_con(tenant: uuid.UUID, etiqueta: str) -> int:
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        return int((await sesion.execute(SQL_CONTAR_RECURSOS, {"e": etiqueta})).scalar_one())


# ── Reintento identico ───────────────────────────────────────────────────────


async def test_el_reintento_identico_devuelve_el_original_y_no_crea_otro(
    tenant: uuid.UUID, clave: str
) -> None:
    etiqueta = f"recurso-{uuid.uuid4().hex[:8]}"
    cuerpo = {"etiqueta": etiqueta}

    async def crear() -> tuple[dict[str, str], int]:
        await crear_recurso(tenant, etiqueta)
        return {"etiqueta": etiqueta}, 201

    primera = await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo=cuerpo, crear=crear, dsn=DSN
    )
    segunda = await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo=cuerpo, crear=crear, dsn=DSN
    )

    assert primera == segunda
    assert await recursos_con(tenant, etiqueta) == 1, "se creo un segundo recurso"


async def test_el_reintento_no_vuelve_a_ejecutar_la_creacion(tenant: uuid.UUID, clave: str) -> None:
    """No alcanza con que el resultado coincida: la creacion no debe correr."""
    contador = Contador("da-igual")
    cuerpo = {"a": 1}

    primera = await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo=cuerpo, crear=contador, dsn=DSN
    )
    segunda = await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo=cuerpo, crear=contador, dsn=DSN
    )

    assert contador.veces == 1
    assert primera == segunda
    # El `intento` guardado es el de la PRIMERA. Si dijera "2", habria corrido
    # de nuevo y el test anterior no lo habria notado.
    assert primera[0]["intento"] == "1"


# ── Misma clave, contenido distinto ──────────────────────────────────────────


async def test_misma_clave_con_contenido_distinto_es_conflicto(
    tenant: uuid.UUID, clave: str
) -> None:
    """Devolver el resultado de la primera seria peor que fallar.

    El cliente pidio una cosa distinta. Contestarle con el resultado de otra
    operacion —porque reutilizo la clave— es darle por hecho algo que nunca
    ocurrio.
    """
    await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=Contador("uno"), dsn=DSN
    )

    with pytest.raises(ClaveEnConflicto):
        await ejecutar_idempotente(
            tenant=tenant, clave=clave, cuerpo={"a": 2}, crear=Contador("dos"), dsn=DSN
        )


async def test_el_conflicto_no_ejecuta_la_creacion(tenant: uuid.UUID, clave: str) -> None:
    await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=Contador("uno"), dsn=DSN
    )
    contador = Contador("dos")

    with pytest.raises(ClaveEnConflicto):
        await ejecutar_idempotente(
            tenant=tenant, clave=clave, cuerpo={"a": 2}, crear=contador, dsn=DSN
        )

    assert contador.veces == 0


async def test_el_orden_de_las_claves_del_cuerpo_no_cambia_la_huella(
    tenant: uuid.UUID, clave: str
) -> None:
    """Mismo contenido escrito distinto sigue siendo el mismo reintento.

    Un cliente que reintenta serializando de nuevo puede mandar las claves en
    otro orden. Tratarlo como conflicto convertiria la idempotencia en una
    trampa en vez de una garantia.
    """
    contador = Contador("igual")

    await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo={"a": 1, "b": 2}, crear=contador, dsn=DSN
    )
    await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo={"b": 2, "a": 1}, crear=contador, dsn=DSN
    )

    assert contador.veces == 1


# ── Clave vencida ────────────────────────────────────────────────────────────


async def test_una_clave_vencida_se_trata_como_creacion_nueva(
    tenant: uuid.UUID, clave: str
) -> None:
    contador = Contador("nuevo")
    cuerpo = {"a": 1}

    await ejecutar_idempotente(tenant=tenant, clave=clave, cuerpo=cuerpo, crear=contador, dsn=DSN)

    # Se vence a mano en vez de esperar: la retencion es de horas y un test que
    # duerme para probar un vencimiento no es un test, es una demora.
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        await sesion.execute(
            text(
                "UPDATE idempotency_keys SET expires_at = now() - interval '1 second' "
                "WHERE key = :k"
            ),
            {"k": clave},
        )

    segunda = await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo=cuerpo, crear=contador, dsn=DSN
    )

    assert contador.veces == 2, "la clave vencida no habilito una creacion nueva"
    assert segunda[0]["intento"] == "2"


async def test_una_clave_vencida_admite_un_cuerpo_distinto(tenant: uuid.UUID, clave: str) -> None:
    """Vencida es vencida: ya no hay con que comparar, asi que no hay conflicto."""
    await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=Contador("uno"), dsn=DSN
    )
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        await sesion.execute(
            text(
                "UPDATE idempotency_keys SET expires_at = now() - interval '1 second' "
                "WHERE key = :k"
            ),
            {"k": clave},
        )

    respuesta, estado = await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo={"a": 2}, crear=Contador("dos"), dsn=DSN
    )

    assert estado == 201
    assert respuesta["etiqueta"] == "dos"


# ── La creacion que falla libera la clave ────────────────────────────────────


async def test_si_la_creacion_falla_la_clave_queda_reutilizable(
    tenant: uuid.UUID, clave: str
) -> None:
    """El peor de los dos errores posibles seria dejarla tomada.

    El cliente recibio un fallo y no sabe si el recurso existe. La unica forma
    segura de averiguarlo es reintentar con la MISMA clave — y si la reserva
    quedara tomada por la retencion entera, esa via le quedaria bloqueada 24 h
    justo cuando mas la necesita.
    """
    fallos = 0

    async def crear_que_falla() -> tuple[dict[str, str], int]:
        nonlocal fallos
        fallos += 1
        raise RuntimeError("la base se cayo a la mitad")

    with pytest.raises(RuntimeError):
        await ejecutar_idempotente(
            tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=crear_que_falla, dsn=DSN
        )

    # Mismo cuerpo, misma clave: tiene que poder volver a intentarlo.
    contador = Contador("al-fin")
    respuesta, estado = await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=contador, dsn=DSN
    )

    assert fallos == 1
    assert contador.veces == 1, "la clave quedo tomada por la creacion que fallo"
    assert estado == 201
    assert respuesta["etiqueta"] == "al-fin"


async def test_la_creacion_que_falla_no_deja_respuesta_guardada(
    tenant: uuid.UUID, clave: str
) -> None:
    """Contrapeso: liberar no puede significar guardar una respuesta a medias."""

    async def crear_que_falla() -> tuple[dict[str, str], int]:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await ejecutar_idempotente(
            tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=crear_que_falla, dsn=DSN
        )

    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        guardado = (
            await sesion.execute(
                text("SELECT response, status_code FROM idempotency_keys WHERE key = :k"),
                {"k": clave},
            )
        ).one()

    assert guardado.response is None
    assert guardado.status_code is None


# ── Acotada al tenant ────────────────────────────────────────────────────────


async def test_la_misma_clave_en_dos_tenants_da_dos_creaciones(
    tenant: uuid.UUID, otro_tenant: uuid.UUID, clave: str
) -> None:
    """El motivo por el que el unico es `(tenant_id, key)` y no `(key)`.

    La clave la elige el cliente. Dos agencias con la misma libreria van a
    generar la misma cadena, y con un unico global la segunda recibiria la
    respuesta guardada de la primera: filtracion entre tenants por la puerta de
    servicio.
    """
    uno = Contador("del-primero")
    otro = Contador("del-segundo")

    respuesta_uno, _ = await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=uno, dsn=DSN
    )
    respuesta_otro, _ = await ejecutar_idempotente(
        tenant=otro_tenant, clave=clave, cuerpo={"a": 1}, crear=otro, dsn=DSN
    )

    assert uno.veces == 1
    assert otro.veces == 1
    assert respuesta_uno["etiqueta"] == "del-primero"
    assert respuesta_otro["etiqueta"] == "del-segundo"


# ── Sin clave ────────────────────────────────────────────────────────────────


async def test_sin_clave_la_creacion_se_procesa_normalmente(tenant: uuid.UUID) -> None:
    """La idempotencia se ofrece, no se impone."""
    contador = Contador("sin-clave")

    primera = await ejecutar_idempotente(
        tenant=tenant, clave=None, cuerpo={"a": 1}, crear=contador, dsn=DSN
    )
    segunda = await ejecutar_idempotente(
        tenant=tenant, clave=None, cuerpo={"a": 1}, crear=contador, dsn=DSN
    )

    assert contador.veces == 2, "sin clave no hay nada que deduplicar"
    assert primera[0]["intento"] == "1"
    assert segunda[0]["intento"] == "2"


async def test_sin_clave_no_se_guarda_nada(tenant: uuid.UUID) -> None:
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        antes = (await sesion.execute(text("SELECT count(*) FROM idempotency_keys"))).scalar_one()

    await ejecutar_idempotente(
        tenant=tenant, clave=None, cuerpo={"a": 1}, crear=Contador("x"), dsn=DSN
    )

    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        despues = (await sesion.execute(text("SELECT count(*) FROM idempotency_keys"))).scalar_one()
    assert despues == antes


# ── Concurrencia: la garantia es el indice unico ─────────────────────────────


async def test_dos_peticiones_simultaneas_con_la_misma_clave_crean_una_sola_vez(
    tenant: uuid.UUID, clave: str
) -> None:
    """El caso que un diccionario en memoria no cubre.

    Dos peticiones simultaneas miran "no existe" al mismo tiempo. Lo unico que
    puede desempatar es la base: una de las dos choca contra
    `UNIQUE (tenant_id, key)` y pierde.
    """
    etiqueta = f"concurrente-{uuid.uuid4().hex[:8]}"
    contador = Contador(etiqueta)

    async def intentar() -> object:
        try:
            return await ejecutar_idempotente(
                tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=contador, dsn=DSN
            )
        except ClaveEnConflicto as conflicto:
            return conflicto

    resultados = await asyncio.gather(intentar(), intentar())

    assert contador.veces == 1, f"la creacion corrio {contador.veces} veces"
    # La que perdio recibe un resultado utilizable o un conflicto explicito;
    # lo que NO puede pasar es que ejecute la creacion.
    assert len(resultados) == 2


# ── Retencion ────────────────────────────────────────────────────────────────


async def test_la_clave_guardada_tiene_vencimiento(tenant: uuid.UUID, clave: str) -> None:
    """Sin vencimiento la tabla crece para siempre (D-5)."""
    from app.core.idempotency import RETENCION

    await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=Contador("x"), dsn=DSN
    )

    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        vence_en = (
            await sesion.execute(
                text("SELECT expires_at - now() FROM idempotency_keys WHERE key = :k"),
                {"k": clave},
            )
        ).scalar_one()

    assert timedelta(seconds=0) < vence_en <= RETENCION
