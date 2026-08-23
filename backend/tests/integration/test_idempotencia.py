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
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.idempotency import (
    LOCK_TIMEOUT_RESERVA_MS,
    ClaveEnConflicto,
    ejecutar_idempotente,
    huella,
)
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


async def crear_recurso_en(sesion: AsyncSession, tenant: uuid.UUID, etiqueta: str) -> None:
    """La MISMA forma que `crear_recurso`, pero sobre una sesion YA ABIERTA.

    Es la que hace que un test de `sesion` compartida pruebe algo real: si
    `crear()` abriera su PROPIA sesion (como `crear_recurso`), estaria
    probando el modo SIN sesion sin querer — la creacion comitearia sola,
    sin importar que la reserva de `ejecutar_idempotente` este en otra
    transaccion todavia abierta.
    """
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


# ═════════════════════════════════════════════════════════════════════════════
# C-15, bloque 4 — `sesion` compartida (`design.md` D-1, CODIGO CRITICO)
#
# `POST /vehicles` no puede llamar a `ejecutar_idempotente` con sus tres
# transacciones propias: el router ya recibe una `SesionDeTenant` abierta, y
# el drenaje del outbox (`ADR-036`) vive DESPUES de que esa transaccion
# commitea, fuera de esta funcion. El parametro `sesion` es ADITIVO — con
# `sesion=None` el camino de arriba (el que usa `core/events.py`) no cambia
# ni una linea.
# ═════════════════════════════════════════════════════════════════════════════


# ── 4.2 · No-regresion: SIN `sesion`, todo sigue igual ───────────────────────


async def test_sin_el_parametro_sesion_el_comportamiento_es_identico_al_de_antes(
    tenant: uuid.UUID, clave: str
) -> None:
    """Este test se escribe ANTES de tocar el modulo (`T-078`) y tiene que
    seguir pasando despues: `core/events.py` es el unico llamador existente y
    NUNCA pasa `sesion` — su camino no puede cambiar de comportamiento."""
    contador = Contador("sin-el-parametro-nuevo")
    cuerpo = {"a": 1}

    primera = await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo=cuerpo, crear=contador, dsn=DSN
    )
    segunda = await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo=cuerpo, crear=contador, dsn=DSN
    )

    assert contador.veces == 1, "reservo, ejecuto, guardo: el reintento no debe re-ejecutar"
    assert primera == segunda


async def test_sin_sesion_una_creacion_que_falla_sigue_liberando_la_clave(
    tenant: uuid.UUID, clave: str
) -> None:
    """El camino de `_LIBERAR` — que en modo compartido NO corre — tiene que
    seguir intacto cuando no hay sesion."""

    async def crear_que_falla() -> tuple[dict[str, str], int]:
        raise RuntimeError("fallo de siempre")

    with pytest.raises(RuntimeError):
        await ejecutar_idempotente(
            tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=crear_que_falla, dsn=DSN
        )

    contador = Contador("reutilizada")
    respuesta, estado = await ejecutar_idempotente(
        tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=contador, dsn=DSN
    )
    assert estado == 201
    assert contador.veces == 1


# ── 4.3 / 4.4 · Con `sesion`: todo en una transaccion, sin ventana de caida ──


async def test_con_sesion_compartida_reserva_creacion_y_guardado_van_juntos(
    tenant: uuid.UUID, clave: str
) -> None:
    """`design.md` D-1(d): las tres cosas ocurren en la transaccion que YA
    trae `sesion` — no se abre ninguna transaccion nueva.

    Se verifica que nada es visible desde AFUERA mientras la transaccion
    sigue abierta (otra conexion, `recursos_con`, bajo READ COMMITTED no ve
    cambios no comiteados) y que SI es visible una vez que termina — es la
    prueba de que la ventana de caida del modo de tres transacciones
    (recurso creado, clave reservada, `status_code IS NULL` durante 24 h) no
    puede existir: o comitean las tres cosas juntas, o ninguna.
    """
    etiqueta = f"compartido-{uuid.uuid4().hex[:8]}"

    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:

        async def crear() -> tuple[dict[str, str], int]:
            # `crear_recurso_en(sesion, ...)` y NO `crear_recurso(tenant, ...)`:
            # tiene que insertar en ESTA sesion, no en una nueva — si no, la
            # creacion comitearia sola y este test no probaria nada de lo que
            # dice probar.
            await crear_recurso_en(sesion, tenant, etiqueta)
            return {"etiqueta": etiqueta}, 201

        respuesta, estado = await ejecutar_idempotente(
            tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=crear, sesion=sesion
        )
        assert estado == 201
        assert respuesta["etiqueta"] == etiqueta

        # Todavia no comiteo esta transaccion: desde AFUERA no se ve nada.
        assert await recursos_con(tenant, etiqueta) == 0
        async with sesion_de_tenant(tenant, dsn=DSN) as otra:
            fila = (
                await otra.execute(
                    text("SELECT status_code FROM idempotency_keys WHERE key = :k"),
                    {"k": clave},
                )
            ).first()
        assert fila is None, "la reserva no puede ser visible antes del commit del endpoint"

    # Recien AHORA, con la transaccion del `async with` de arriba cerrada
    # (commiteada), las tres cosas son visibles juntas.
    assert await recursos_con(tenant, etiqueta) == 1
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        guardado = (
            await sesion.execute(
                text("SELECT status_code, response FROM idempotency_keys WHERE key = :k"),
                {"k": clave},
            )
        ).one()
    assert guardado.status_code == 201


async def test_con_sesion_compartida_si_la_transaccion_revierte_no_queda_nada(
    tenant: uuid.UUID, clave: str
) -> None:
    """El escenario que cierra la ventana de caida por el otro lado: si algo
    de la peticion falla DESPUES de `ejecutar_idempotente` pero ANTES de que
    el endpoint termine, la transaccion entera revierte — ni el recurso
    queda creado, ni la clave queda reservada. `test_si_la_creacion_falla_...`
    (modo sin sesion) prueba la creacion que falla; este prueba que ADEMAS
    de eso, la reserva desaparece con el rollback."""
    etiqueta = f"se-revierte-{uuid.uuid4().hex[:8]}"

    with pytest.raises(RuntimeError):
        async with sesion_de_tenant(tenant, dsn=DSN) as sesion:

            async def crear() -> tuple[dict[str, str], int]:
                await crear_recurso_en(sesion, tenant, etiqueta)
                return {"etiqueta": etiqueta}, 201

            await ejecutar_idempotente(
                tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=crear, sesion=sesion
            )
            # Simula el resto de la peticion fallando DESPUES: ej. un `flush`
            # de otra parte del endpoint que levanta.
            raise RuntimeError("algo mas de la peticion fallo despues")

    assert await recursos_con(tenant, etiqueta) == 0
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        quedo_reservada = (
            await sesion.execute(
                text("SELECT count(*) FROM idempotency_keys WHERE key = :k"), {"k": clave}
            )
        ).scalar_one()
    assert (
        quedo_reservada == 0
    ), "la clave sobrevivio al rollback: la ventana de caida sigue abierta"

    # Y por eso la clave se puede reusar de inmediato.
    contador = Contador("tras-el-rollback")
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        respuesta, estado = await ejecutar_idempotente(
            tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=contador, sesion=sesion
        )
    assert estado == 201
    assert contador.veces == 1


# ── 4.6 / 4.7 · Concurrencia real, acotada por `lock_timeout` ────────────────


async def test_dos_peticiones_concurrentes_con_sesion_compartida_resuelven_acotado(
    tenant: uuid.UUID, clave: str
) -> None:
    """`design.md` D-1, punto 1: con sesion compartida, la SEGUNDA peticion
    con la misma clave se bloquea en el lock de la fila en vez de recibir
    "no volvio ninguna fila" — y sin `lock_timeout` ese bloqueo seria
    indefinido. `asyncio.wait_for` es el limite del TEST: si `lock_timeout`
    no estuviera puesto, esta prueba se queda colgada (o tarda mucho mas que
    el limite) en vez de resolverse rapido, que es la forma en que un test de
    concurrencia real detecta la ausencia de un timeout.
    """
    etiqueta = f"concurrente-compartido-{uuid.uuid4().hex[:8]}"
    contador = Contador(etiqueta)

    async def intentar() -> object:
        try:
            async with sesion_de_tenant(tenant, dsn=DSN) as sesion:

                async def crear() -> tuple[dict[str, str], int]:
                    # Una demora real, para que las dos transacciones se
                    # solapen de verdad y la segunda tenga que esperar el
                    # lock de la primera.
                    await asyncio.sleep(0.2)
                    await crear_recurso_en(sesion, tenant, etiqueta)
                    return await contador()

                return await ejecutar_idempotente(
                    tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=crear, sesion=sesion
                )
        except ClaveEnConflicto as conflicto:
            return conflicto

    resultados = await asyncio.wait_for(asyncio.gather(intentar(), intentar()), timeout=10.0)

    assert contador.veces == 1, f"la creacion corrio {contador.veces} veces"
    assert await recursos_con(tenant, etiqueta) == 1
    assert len(resultados) == 2


async def test_si_la_primera_no_termina_antes_del_lock_timeout_la_segunda_recibe_conflicto(
    tenant: uuid.UUID, clave: str
) -> None:
    """El otro lado del 4.6/4.7: si la PRIMERA tarda mas que
    `LOCK_TIMEOUT_RESERVA_MS`, la segunda no puede esperarla para siempre —
    eso retendria una conexion del pool indefinidamente. Postgres corta la
    espera con `lock_timeout` (SQLSTATE `55P03`) y
    `_ejecutar_con_sesion_compartida` lo traduce a la MISMA `ClaveEnConflicto`
    que ya usa para "hay una peticion en curso" (`design.md` D-1, punto 1):
    la semantica documentada no cambia, cambia como se detecta.

    El test anterior (con una demora de `0.2s`, muy por debajo del limite)
    prueba que la segunda ESPERA y se resuelve. Este prueba el otro extremo:
    que la espera esta ACOTADA y no es infinita. Ninguno de los dos por si
    solo prueba que el limite este puesto donde el codigo dice que esta.
    """
    etiqueta = f"lock-timeout-{uuid.uuid4().hex[:8]}"
    contador = Contador(etiqueta)
    # Margen sobre el limite real y no un numero adivinado: si alguna vez se
    # cambia la constante del modulo, este test se sigue moviendo con ella.
    demora_de_la_primera = (LOCK_TIMEOUT_RESERVA_MS / 1000) + 1.0

    async def primera() -> object:
        async with sesion_de_tenant(tenant, dsn=DSN) as sesion:

            async def crear() -> tuple[dict[str, str], int]:
                await asyncio.sleep(demora_de_la_primera)
                await crear_recurso_en(sesion, tenant, etiqueta)
                return await contador()

            return await ejecutar_idempotente(
                tenant=tenant, clave=clave, cuerpo={"a": 1}, crear=crear, sesion=sesion
            )

    async def segunda() -> ClaveEnConflicto:
        # Arranca despues: tiene que encontrar la fila de la primera YA
        # reservada (INSERT en vuelo) para bloquearse en su lock, no ganar la
        # carrera de quien inserta primero.
        await asyncio.sleep(0.3)
        async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
            with pytest.raises(ClaveEnConflicto) as info:
                await ejecutar_idempotente(
                    tenant=tenant,
                    clave=clave,
                    cuerpo={"a": 1},
                    crear=contador,
                    sesion=sesion,
                )
            return info.value

    _, conflicto = await asyncio.wait_for(
        asyncio.gather(primera(), segunda()), timeout=demora_de_la_primera + 5.0
    )

    assert conflicto.code == "idempotency_key_conflict"
    # La primera SI corrio — no perdio su turno por el timeout de la segunda.
    assert contador.veces == 1, f"la creacion corrio {contador.veces} veces"
    assert await recursos_con(tenant, etiqueta) == 1


# ── Cierre del hueco de cobertura de C-15 (lineas 211 y 231) ────────────────
#
# Las dos son parte de `_ejecutar_con_sesion_compartida` y NINGUNA es
# alcanzable por concurrencia simultanea dentro del propio camino de sesion
# compartida — ese caso ya lo cubren los tests 4.6/4.7 de arriba. Las dos SI
# son alcanzables por un camino distinto, y por eso van en su propia seccion.


async def test_con_sesion_compartida_una_reserva_del_camino_viejo_sin_respuesta_da_conflicto(
    tenant: uuid.UUID, clave: str
) -> None:
    """Cubre la linea 231 — el caso CRUZADO, no el concurrente.

    Dos peticiones simultaneas por el camino de `sesion` compartida nunca
    llegan a la linea 231: la segunda se bloquea en el lock de la fila y sale
    por `lock_timeout` (linea 217) antes de leer nada. Eso es lo que prueban
    4.6/4.7 y es correcto.

    Lo que si llega es el camino CRUZADO: `core/events.py:282` sigue llamando
    sin `sesion`, y en ese modo la reserva COMITEA en su propia transaccion
    antes de que `crear()` corra (ver el encabezado del modulo). Si ese
    camino muere entre la reserva y el guardado, queda una fila COMITEADA
    con `status_code IS NULL` durante las 24 h de `RETENCION`. Una peticion
    posterior con la MISMA clave y la MISMA huella que entre por el camino de
    `sesion` compartida encuentra esa fila en la linea 222, la huella
    coincide (linea 224), y `status_code IS NULL` (linea 227) dispara la
    linea 231.

    La precondicion se arma con SQL real desde una sesion aparte, COMITEADA
    antes de llamar a la funcion bajo prueba — no con un mock (regla dura 8):
    es exactamente lo que el camino viejo dejaria en la tabla.
    """
    cuerpo = {"a": 1}

    async with sesion_de_tenant(tenant, dsn=DSN) as sesion_ajena:
        await sesion_ajena.execute(
            text(
                "INSERT INTO idempotency_keys (tenant_id, key, fingerprint, expires_at) "
                "VALUES (:t, :k, :h, now() + interval '1 hour')"
            ),
            {"t": str(tenant), "k": clave, "h": huella(cuerpo)},
        )
    # El `async with` de arriba ya comiteo al salir (D-3 del modulo de
    # sesiones): la fila es visible para cualquier otra conexion, tal cual la
    # dejaria el camino sin `sesion` si muriera antes de guardar la respuesta.

    contador = Contador("no-debe-correr")
    async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
        with pytest.raises(ClaveEnConflicto) as info:
            await ejecutar_idempotente(
                tenant=tenant, clave=clave, cuerpo=cuerpo, crear=contador, sesion=sesion
            )

    assert info.value.code == "idempotency_key_conflict"
    assert "todavia en curso" in str(info.value)
    assert contador.veces == 0, "no debia ejecutar la creacion sobre una reserva ajena"


async def test_con_sesion_compartida_un_dbapierror_con_otro_sqlstate_se_repropaga_sin_traducir(
    tenant: uuid.UUID, otro_tenant: uuid.UUID, clave: str
) -> None:
    """Cubre la linea 211 — el re-raise de un `DBAPIError` que NO es `lock_timeout`.

    La traduccion a `ClaveEnConflicto` es SOLO para `55P03` (`lock_timeout`,
    lineas 209-217): cualquier otro error de Postgres tiene que atravesar la
    funcion tal cual — traducirlo tambien escondería un error real detras de
    un 409 que no tiene nada que ver.

    Se provoca un `DBAPIError` REAL, sin mockear nada (regla dura 8): la
    sesion trae el contexto de tenant puesto en `tenant` (`SET LOCAL
    app.current_tenant`, D-3), pero se llama a `ejecutar_idempotente` con
    `tenant=otro_tenant` — el valor que la `_RESERVAR` de la linea 200 usa
    como columna `tenant_id` de la fila a insertar. Esos dos valores
    distintos son exactamente lo que la politica RLS de escritura (migracion
    003, `WITH CHECK`) esta hecha para rechazar: Postgres devuelve
    `InsufficientPrivilegeError`, `sqlstate` `42501` — verificado contra la
    base real de este test, no supuesto — que es un `sqlstate` distinto de
    `55P03` y por lo tanto tiene que re-lanzarse tal cual.
    """

    async def crear_que_no_debe_correr() -> tuple[dict[str, str], int]:
        raise AssertionError("no debia llegar a ejecutarse: la reserva tiene que fallar antes")

    with pytest.raises(DBAPIError) as info:
        async with sesion_de_tenant(tenant, dsn=DSN) as sesion:
            await ejecutar_idempotente(
                tenant=otro_tenant,
                clave=clave,
                cuerpo={"a": 1},
                crear=crear_que_no_debe_correr,
                sesion=sesion,
            )

    sqlstate = getattr(info.value.orig, "sqlstate", None)
    assert sqlstate is not None
    # 55P03 = lock_not_available: el UNICO sqlstate que la funcion traduce a
    # `ClaveEnConflicto`. Cualquier otro, incluido este, tiene que salir sin
    # traducir.
    assert sqlstate != "55P03"
