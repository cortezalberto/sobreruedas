"""Notificaciones — C-06, `T-035`.

DOS CANALES CON GARANTIAS DISTINTAS, Y LA DIFERENCIA IMPORTA
─────────────────────────────────────────────────────────────
  - **In-app** es transaccional: la fila entra en la transaccion de quien la
    crea. Es el canal de REGISTRO — si esta la fila, la notificacion existe.
  - **Email** es mejor-esfuerzo: se manda despues, no levanta si falla y no se
    reintenta. Es la copia de cortesia.

Ponerlos al mismo nivel seria mentir sobre el segundo. Ver `correo.py`.

EL SERVICIO NO DECIDE A QUIEN NOTIFICAR
────────────────────────────────────────
Recibe el `user_id`. Quien lo elige es el manejador del evento —`consumidor.py`—
porque esa es una regla de negocio del dominio que origina el hecho, y va a ser
distinta para stock, para leads y para facturacion. Un servicio que resolviera
destinatarios acumularia las reglas de todos los modulos en un solo `if`.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications import correo
from app.modules.notifications.models import Notification
from app.modules.notifications.plantillas import redactar

__all__ = ["NotificationService"]


class NotificationService:
    """Operaciones de notificacion, siempre acotadas a un tenant.

    Misma forma que `StockService`: el `tenant_id` se recibe al construir y viene
    del token o del sobre del evento. Ningun metodo lo toma por parametro.
    """

    def __init__(self, sesion: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._sesion = sesion
        self._tenant_id = tenant_id

    async def crear(
        self, *, user_id: uuid.UUID, tipo: str, payload: Mapping[str, object]
    ) -> Notification:
        """Crea la notificacion in-app. NO manda el mail.

        Separado a proposito de `avisar_por_mail`: esto corre dentro de una
        transaccion y el envio de correo es red. Fundirlos haria que un SMTP
        lento sostuviera abierta una transaccion de base.
        """
        notificacion = Notification(
            tenant_id=self._tenant_id,
            user_id=user_id,
            type=tipo,
            # `dict(...)` y no el `Mapping` tal cual: la columna es un
            # `dict` mutable del ORM, y guardar el objeto del llamador lo dejaria
            # compartido — si despues lo modifica, cambiaria la fila.
            payload=dict(payload),
        )
        self._sesion.add(notificacion)
        await self._sesion.flush()
        return notificacion

    async def sin_leer(self, user_id: uuid.UUID) -> list[Notification]:
        """Las pendientes de una persona, las mas nuevas primero.

        `tenant_id` en el WHERE aunque la politica RLS ya lo garantice: son las
        tres capas de la regla dura 1, y la de la query es la que se lee en el
        codigo.
        """
        resultado = await self._sesion.execute(
            sa.select(Notification)
            .where(
                Notification.tenant_id == self._tenant_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .order_by(Notification.created_at.desc())
        )
        return list(resultado.scalars())

    async def marcar_leida(self, notificacion_id: uuid.UUID, *, user_id: uuid.UUID) -> bool:
        """Marca una como leida. Devuelve si habia algo que marcar.

        `user_id` EN EL WHERE, y no es redundante con la politica RLS: RLS acota
        por AGENCIA, no por persona. Sin esta condicion, un usuario podria marcar
        como leida la notificacion de un companero — misma agencia, otro
        destinatario, y la politica lo dejaria pasar.

        `read_at IS NULL` tambien: marcar dos veces no tiene que mover la fecha,
        porque "cuando la vio" es la primera vez, no la ultima.
        """
        resultado = await self._sesion.execute(
            sa.update(Notification)
            .where(
                Notification.id == notificacion_id,
                Notification.tenant_id == self._tenant_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=sa.func.now())
            # `RETURNING id` y no `rowcount`: el `Result` de un `update` con
            # `AsyncSession` no expone `rowcount` con tipo, y afirmarselo a mypy
            # seria taparle los ojos sobre algo que la API si contesta bien por
            # otro lado. Devolver la clave es la forma tipada de preguntar
            # "¿toco alguna fila?".
            .returning(Notification.id)
        )
        return resultado.scalar_one_or_none() is not None

    @staticmethod
    async def avisar_por_mail(destinatario: str, tipo: str, payload: Mapping[str, object]) -> bool:
        """La copia de cortesia, con el mismo texto que la in-app.

        `staticmethod` porque no toca la base: es red pura. Lo dice la firma en
        vez de dejar que alguien lo descubra al ver una transaccion abierta
        esperando a un SMTP.

        Usa `redactar` —la misma plantilla que la pantalla— para que el mail y la
        campanita no digan cosas distintas del mismo hecho.
        """
        asunto, cuerpo = redactar(tipo, payload)
        return await correo.enviar(destinatario, asunto, cuerpo)
