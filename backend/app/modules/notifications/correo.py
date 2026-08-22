"""El canal de email — C-06, `T-035`.

`smtplib` DE LA BIBLIOTECA ESTANDAR, EN UN HILO
────────────────────────────────────────────────
Mismo criterio que `core/storage.py` con `boto3`: `pip-audit` bloquea ante
CUALQUIER vulnerabilidad porque no expone severidad (`ADR-027`), asi que cada
paquete de mas es una chance de mas de dejar el pipeline en rojo. `aiosmtplib`
daria `await` nativo sobre lo mismo que `asyncio.to_thread` ya resuelve.

EL ENVIO NO PUEDE TUMBAR LO QUE LO ORIGINO
───────────────────────────────────────────
`enviar` no levanta: registra y devuelve `False`. Un servidor de correo caido no
tiene por qué voltear el consumo de un evento —ni, mas adelante, una peticion— y
sobre todo no tiene que hacer que el evento se reintente cinco veces mandando
cinco copias del mismo mail a quien si lo recibio.

⚠️ LO QUE ESTO NO TIENE ES REINTENTO. Un mail que no salio, no salio: no queda
fila ni cola. Es distinto del outbox, que si deja evidencia. Se acepta porque la
notificacion in-app —que si es transaccional— es el canal de registro, y el mail
es la copia de cortesia. **El dia que haya un mail que no se pueda perder
—recuperar una cuenta, un aviso de facturacion— esto no alcanza.**

EN DESARROLLO VA A MAILHOG Y NADA SALE A INTERNET
──────────────────────────────────────────────────
`SMTP_HOST` apunta a `mailhog:1025` en el compose. No hay autenticacion ni TLS
contra mailhog, y por eso los dos son condicionales: exigirlos volveria
inutilizable el entorno local, y ponerlos siempre en produccion es lo correcto.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

__all__ = ["REMITENTE", "enviar"]

_log = logging.getLogger(__name__)

# Sin fuente en el corpus: `MailSettings` declara host, usuario y clave, y ningun
# documento fija el remitente. Se elige uno explicito en vez de dejar que el
# servidor invente el suyo, que produce direcciones distintas por entorno.
REMITENTE = "notificaciones@deruedas.com.ar"

# Un servidor que no contesta no puede colgar el consumo de un evento. Diez
# segundos es holgado para un SMTP sano y corto para uno muerto.
TIMEOUT_SEGUNDOS = 10


def _armar(destinatario: str, asunto: str, cuerpo: str) -> EmailMessage:
    mensaje = EmailMessage()
    mensaje["From"] = REMITENTE
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)
    return mensaje


def _enviar_bloqueante(mensaje: EmailMessage) -> None:
    mail = get_settings().mail
    host, _, puerto = mail.host.partition(":")

    with smtplib.SMTP(host, int(puerto or 25), timeout=TIMEOUT_SEGUNDOS) as servidor:
        if mail.user is not None and mail.password is not None:
            # `starttls` antes del login y no despues: sin eso la credencial
            # viaja en claro por la red. Solo se intenta cuando hay credencial,
            # porque mailhog no ofrece TLS.
            servidor.starttls()
            servidor.login(mail.user.get_secret_value(), mail.password.get_secret_value())
        servidor.send_message(mensaje)


async def enviar(destinatario: str, asunto: str, cuerpo: str) -> bool:
    """Manda un mail. Devuelve si salio; NO levanta.

    El destinatario no se registra en el log: es un dato personal (Ley 25.326,
    `RN-DP-04`) y este texto termina en Loki.
    """
    try:
        await asyncio.to_thread(_enviar_bloqueante, _armar(destinatario, asunto, cuerpo))
    except Exception:
        # `Exception` a secas: abajo hay DNS, TCP, TLS y un servidor ajeno.
        # Ninguno de los cuatro puede voltear a quien pidio el envio.
        _log.exception("[notificaciones] no se pudo enviar el mail %r", asunto)
        return False
    return True
