"""Idempotencia de las creaciones — T-015, capability `platform/api-conventions`.

EL PROBLEMA
───────────
Un cliente manda `POST /vehiculos`, la respuesta se pierde en el camino, el
cliente reintenta. Sin idempotencia hay dos vehiculos. Con una operacion de
dinero de por medio, hay dos cobros.

LA GARANTIA ES EL INDICE UNICO, NO ESTE CODIGO
──────────────────────────────────────────────
Dos peticiones simultaneas con la misma clave pueden mirar "no existe" al mismo
tiempo. Ninguna cantidad de `if` en Python arregla eso: lo unico que puede
desempatar dos procesos es la base. `UNIQUE (tenant_id, key)` es lo que hace
que una de las dos pierda, y todo este modulo esta escrito alrededor de esa
sentencia.

Por eso la reserva y la creacion van en ese orden: **primero se gana la clave,
despues se crea**. Al reves, dos peticiones crearian dos recursos y recien
despues descubririan que una sobra — y el recurso de mas ya existiria.

POR QUE POSTGRESQL Y NO REDIS (design.md D-5)
─────────────────────────────────────────────
Redis tiene TTL nativo y seria mas comodo. Un Redis que se reinicia pierde las
claves, y perder una clave de idempotencia significa aceptar como nuevo un
reintento que ya se cobro.

LA CLAVE VENCIDA SE REUSA, NO SE BORRA
──────────────────────────────────────
El rol de aplicacion no tiene `DELETE` (ADR-020, design.md D-4 de ese change):
el sistema hace borrado logico universal. Asi que una clave vencida no se borra
para volver a insertarla — se **pisa en su lugar** con un `ON CONFLICT DO
UPDATE`, que ademas es atomico y no tiene la ventana que tendria borrar y
reinsertar.

La purga de vencidas es una tarea periodica de plataforma y no vive aca.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RequestError
from app.db.session import sesion_de_tenant

# Sin fuente en el corpus. 24 h cubre de sobra el reintento de un cliente movil
# que quedo sin senal, y acota el crecimiento de la tabla.
RETENCION = timedelta(hours=24)


class ClaveEnConflicto(RequestError):
    """La clave ya se uso para otra cosa.

    409 y no 422: el pedido es valido, lo que falla es su relacion con algo que
    ya paso. Devolver el resultado de la primera operacion seria peor que
    fallar — el cliente pidio otra cosa, y contestarle con el resultado de una
    operacion que no pidio le da por hecho algo que nunca ocurrio.
    """

    status_code = 409

    def __init__(
        self, detail: str = "la clave de idempotencia ya se uso con otro contenido"
    ) -> None:
        super().__init__(detail, code="idempotency_key_conflict")


def huella(cuerpo: Any) -> str:
    """Hash estable del contenido de la peticion.

    `sort_keys` porque un cliente que reintenta serializando de nuevo puede
    mandar las claves en otro orden. Tratar eso como conflicto convertiria la
    idempotencia en una trampa en vez de una garantia.

    Se guarda el HASH y no el cuerpo: un cuerpo de creacion puede tener datos
    personales, y esta tabla vive mas que el recurso que creo. Para distinguir
    "el mismo reintento" de "otra cosa con la misma clave" alcanza con el hash.
    """
    crudo = json.dumps(cuerpo, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(crudo.encode()).hexdigest()


# Gana la clave o no devuelve nada. Un solo viaje a la base, y atomico.
#
# El `WHERE` del `DO UPDATE` es lo que distingue vencida de vigente: si la fila
# que ya existe todavia no vencio, la actualizacion no se aplica y no vuelve
# ninguna fila. Ahi hay que ir a mirar que guardaba.
_RESERVAR = text("""
    INSERT INTO idempotency_keys (tenant_id, key, fingerprint, expires_at)
    VALUES (:tenant, :clave, :huella, now() + :retencion)
    ON CONFLICT (tenant_id, key) DO UPDATE
        SET fingerprint = EXCLUDED.fingerprint,
            expires_at  = EXCLUDED.expires_at,
            response    = NULL,
            status_code = NULL
        WHERE idempotency_keys.expires_at <= now()
    RETURNING id
""")

# El `tenant_id` explicito NO sobra porque RLS ya acote: es la capa 3 de
# `ADR-006` y la regla dura 1 la exige en TODA query, sin excepciones para las
# que "ya estan cubiertas". El dia que alguien ejecute esto desde una sesion sin
# contexto —una tarea de plataforma, una migracion de datos— la unica capa que
# quedaria en pie es esta.
_LEER = text("""
    SELECT fingerprint, response, status_code
    FROM idempotency_keys
    WHERE tenant_id = :tenant AND key = :clave
""")

_GUARDAR = text("""
    UPDATE idempotency_keys
    SET response = CAST(:respuesta AS json), status_code = :estado
    WHERE tenant_id = :tenant AND key = :clave
""")

# Vence la reserva en el acto. Se usa cuando la creacion FALLA: sin esto la
# clave queda tomada por toda la retencion, y el cliente que recibio un 500 no
# puede reintentar con la misma clave — que es exactamente lo que la
# idempotencia existe para permitirle.
#
# Se vence en vez de borrarse porque el rol de aplicacion no tiene DELETE
# (ADR-020). Da lo mismo: una clave vencida se pisa en el proximo intento.
_LIBERAR = text("""
    UPDATE idempotency_keys
    SET expires_at = now() - interval '1 second'
    WHERE tenant_id = :tenant AND key = :clave AND status_code IS NULL
""")


# ═════════════════════════════════════════════════════════════════════════════
# `sesion` COMPARTIDA — C-15, `T-078`, `design.md` D-1. CODIGO CRITICO (C-02).
#
# QUE PROBLEMA CIERRA
# ────────────────────
# `POST /vehicles` no puede llamar a la version de arriba tal cual: el router
# ya recibe una `SesionDeTenant` abierta por inyeccion, y el drenaje del
# outbox (`ADR-036`) vive DESPUES de que esa transaccion commitea —fuera de
# este modulo, en `db/dependencias.py`—. Si este modulo abriera sus propias
# transacciones, el `POST` dejaria de publicar `vehicle.created` sin que nada
# lo avise: `drenar()` no levanta aunque Redis este caido, por diseño.
#
# Por eso `ejecutar_idempotente` gana un parametro OPCIONAL, ADITIVO:
# `sesion=None` dispara EXACTAMENTE el camino de arriba, sin tocar una linea.
# `sesion` PROVISTA hace que la reserva, la ejecucion de `crear` y el guardado
# de la respuesta ocurran en ESA transaccion — la del endpoint — y de rebote
# cierra una ventana de caida que el modo de tres transacciones tenia sin
# documentar (ver el encabezado del modulo).
#
# `_LIBERAR` NO SE LLAMA EN ESTE CAMINO
# ────────────────────────────────────────
# Si `crear()` falla, la excepcion atraviesa esta funcion sin atraparse: la
# transaccion del endpoint entera revierte, y la reserva se va con ella. Un
# `UPDATE` sobre una transaccion ya abortada no seria una operacion — seria
# un segundo error tapando al primero.
# ═════════════════════════════════════════════════════════════════════════════

# Mayor que el p99 esperado del `POST` (`design.md` D-1, punto 1). Constante
# nombrada y no un numero suelto: el valor se revisa en un solo lugar, y el
# nombre dice por que existe sin tener que ir a buscar el ADR.
LOCK_TIMEOUT_RESERVA_MS = 2_000

# SQLSTATE `lock_not_available`, la que Postgres levanta cuando `lock_timeout`
# vence. Se compara el CODIGO y no el texto del mensaje, igual criterio que
# `test_rol_de_conexion.py` y `test_status_history.py`: el texto lo traduce
# `lc_messages`.
_LOCK_NO_DISPONIBLE = "55P03"


async def _ejecutar_con_sesion_compartida(
    sesion: AsyncSession,
    *,
    tenant: uuid.UUID,
    clave: str,
    cuerpo: Any,
    crear: Callable[[], Awaitable[tuple[Any, int]]],
) -> tuple[Any, int]:
    """La reserva, `crear` y el guardado, los tres en la transaccion de `sesion`.

    `SET LOCAL lock_timeout` va ANTES de la reserva y no antes de toda la
    funcion: es la sentencia que puede bloquearse en el lock de la fila si hay
    otra peticion con la misma clave en vuelo, y es la unica.
    """
    await sesion.execute(
        text("SELECT set_config('lock_timeout', :valor, true)"),
        {"valor": f"{LOCK_TIMEOUT_RESERVA_MS}ms"},
    )

    try:
        reservada = (
            await sesion.execute(
                _RESERVAR,
                {
                    "tenant": str(tenant),
                    "clave": clave,
                    "huella": huella(cuerpo),
                    "retencion": RETENCION,
                },
            )
        ).first()
    except DBAPIError as error:
        if getattr(error.orig, "sqlstate", None) != _LOCK_NO_DISPONIBLE:
            raise
        # Vencio el `lock_timeout`: no se puede saber si la peticion en vuelo
        # va a terminar bien o mal, y esperar mas retendria una conexion del
        # pool. Es la MISMA `ClaveEnConflicto` que el caso "reservada pero sin
        # respuesta" de abajo — la semantica documentada no cambia, cambia
        # como se detecta (`design.md` D-1, punto 1).
        raise ClaveEnConflicto("hay una peticion con esta misma clave todavia en curso") from error

    if reservada is None:
        # La clave ya esta tomada y vigente. Puede ser el mismo reintento
        # —y entonces se devuelve lo guardado— o algo distinto.
        guardado = (await sesion.execute(_LEER, {"tenant": str(tenant), "clave": clave})).one()

        if guardado.fingerprint != huella(cuerpo):
            raise ClaveEnConflicto

        if guardado.status_code is None:
            # Reservada pero sin respuesta: hay otra peticion identica
            # todavia corriendo. No se puede devolver un resultado que
            # nadie produjo; se rechaza para que el cliente reintente.
            raise ClaveEnConflicto("hay una peticion con esta misma clave todavia en curso")

        return guardado.response, guardado.status_code

    # Misma transaccion que la reserva de arriba: si esto levanta, la reserva
    # se va con el rollback del endpoint. Adentro.
    respuesta, estado = await crear()

    await sesion.execute(
        _GUARDAR,
        {
            "tenant": str(tenant),
            "clave": clave,
            "respuesta": json.dumps(respuesta, default=str),
            "estado": estado,
        },
    )

    return respuesta, estado


async def ejecutar_idempotente(
    *,
    tenant: uuid.UUID,
    clave: str | None,
    cuerpo: Any,
    crear: Callable[[], Awaitable[tuple[Any, int]]],
    dsn: str | None = None,
    sesion: AsyncSession | None = None,
) -> tuple[Any, int]:
    """Ejecuta `crear` a lo sumo una vez por (tenant, clave).

    Devuelve lo que devuelve `crear`: `(respuesta, codigo de estado)`.

    Sin `clave` no hay nada que deduplicar y se ejecuta y punto — la
    idempotencia se **ofrece**, no se impone. Imponerla obligaria a cada cliente
    a generar una clave incluso para operaciones que puede repetir sin dano.

    Levanta `ClaveEnConflicto` si la clave ya se uso con otro contenido, o si
    hay otra peticion con la misma clave todavia en vuelo.

    `sesion` es OPCIONAL y ADITIVO (`T-078`, `design.md` D-1): con `sesion=None`
    el comportamiento es EXACTAMENTE el de antes de C-15, linea por linea —
    `core/events.py`, el unico llamador de C-02, no pasa este parametro y no
    cambia de comportamiento. Con `sesion` provista, la reserva, `crear` y el
    guardado ocurren en esa transaccion — ver `_ejecutar_con_sesion_compartida`.
    """
    if clave is None:
        return await crear()

    if sesion is not None:
        return await _ejecutar_con_sesion_compartida(
            sesion, tenant=tenant, clave=clave, cuerpo=cuerpo, crear=crear
        )

    async with sesion_de_tenant(tenant, dsn=dsn) as sesion:
        reservada = (
            await sesion.execute(
                _RESERVAR,
                {
                    "tenant": str(tenant),
                    "clave": clave,
                    "huella": huella(cuerpo),
                    "retencion": RETENCION,
                },
            )
        ).first()

        if reservada is None:
            # La clave ya esta tomada y vigente. Puede ser el mismo reintento
            # —y entonces se devuelve lo guardado— o algo distinto.
            guardado = (await sesion.execute(_LEER, {"tenant": str(tenant), "clave": clave})).one()

            if guardado.fingerprint != huella(cuerpo):
                raise ClaveEnConflicto

            if guardado.status_code is None:
                # Reservada pero sin respuesta: hay otra peticion identica
                # todavia corriendo. No se puede devolver un resultado que
                # nadie produjo, y esperar la bloquearia; se rechaza para que
                # el cliente reintente.
                raise ClaveEnConflicto("hay una peticion con esta misma clave todavia en curso")

            return guardado.response, guardado.status_code

    # FUERA de la transaccion de la reserva, y a proposito: si `crear` abre su
    # propia sesion —que es lo normal— compartir transaccion la dejaria anidada.
    #
    # Si `crear` falla se LIBERA la reserva. Dejarla tomada seria el peor de los
    # dos errores posibles: el cliente recibio un fallo, no sabe si el recurso
    # existe, y la unica forma segura de averiguarlo —reintentar con la misma
    # clave— le quedaria bloqueada por 24 h.
    try:
        respuesta, estado = await crear()
    except BaseException:
        async with sesion_de_tenant(tenant, dsn=dsn) as sesion:
            await sesion.execute(_LIBERAR, {"tenant": str(tenant), "clave": clave})
        raise

    async with sesion_de_tenant(tenant, dsn=dsn) as sesion:
        await sesion.execute(
            _GUARDAR,
            {
                "tenant": str(tenant),
                "clave": clave,
                "respuesta": json.dumps(respuesta, default=str),
                "estado": estado,
            },
        )

    return respuesta, estado
