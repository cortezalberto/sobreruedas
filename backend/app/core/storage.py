"""Object storage S3-compatible — C-06, `T-034`. `ADR-008` / `DD-08`.

EL AISLAMIENTO ACA NO LO DA POSTGRESQL
───────────────────────────────────────
En la base hay tres capas: `tenant_id` en la query, `SET LOCAL app.current_tenant`
y la politica RLS. **En S3 no hay ninguna.** Un bucket es un diccionario plano de
cadenas: si el codigo arma la clave equivocada, el objeto se escribe o se lee
donde no corresponde y nada del otro lado lo impide.

Por eso la unica defensa es la forma de la clave, y por eso este modulo **no
acepta claves completas**. `AlmacenDeTenant` recibe el tenant al construirse
—igual que `StockService`— y todo lo demas es RELATIVO a su prefijo. No hay
metodo que tome una clave absoluta, asi que no hay forma de escribir una por
accidente:

    almacen = AlmacenDeTenant(tenant_id)
    almacen.guardar("vehiculos/abc/frente.jpg", datos, tipo="image/jpeg")
    # -> 11111111-.../vehiculos/abc/frente.jpg

Es el mismo criterio que la regla dura 1 aplica a los schemas de entrada: el
tenant no se recibe, se deriva.

`boto3` Y `asyncio.to_thread`
──────────────────────────────
`DD-08` nombra `boto3` como la mitigacion del lock-in de proveedor, y es
sincronico. Las operaciones de red se corren en un hilo para no bloquear el loop.

`url_firmada` **no** va a un hilo, y no es un descuido: firmar es criptografia
local, no una llamada a S3. Mandarla a un hilo costaria mas que hacerla.

TTL SEGUN LO QUE SE FIRMA — `DD-08`
────────────────────────────────────
Cinco minutos para fotos, treinta para documentos. Van como constantes con
nombre y no como un `expires: int` libre: un entero suelto en la firma invita a
que cada llamador elija, y el dia que alguien ponga 86400 nadie lo va a ver en
la revision.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import get_settings

if TYPE_CHECKING:  # pragma: no cover - solo para los stubs
    from mypy_boto3_s3.client import S3Client

__all__ = [
    "TTL_DE_DOCUMENTO",
    "TTL_DE_FOTO",
    "AlmacenDeTenant",
    "ClaveInvalida",
    "ObjetoNoEncontrado",
    "cliente_s3",
]

# `DD-08`, literal: URL firmada de 5 minutos para fotos y de 30 para documentos.
# El documento vive mas porque se descarga y se lee; la foto la pinta el
# navegador en el momento.
TTL_DE_FOTO: Final = 300
TTL_DE_DOCUMENTO: Final = 1800

# Un segmento de clave: letras, digitos, guion, guion bajo y punto. Nada mas.
#
# ⚠️ LO QUE ESTA LISTA DEJA AFUERA ES EL PUNTO DEL ASUNTO. `..` no matchea
# —tiene solo puntos, y el patron exige al menos un caracter que no lo sea al
# empezar—, asi que `../../otro-tenant/x` no puede construirse. Tampoco entran
# la barra invertida ni los segmentos vacios.
#
# S3 por si mismo no normaliza `a/../b`: guardaria esa cadena literal y no se
# escaparia de ningun lado. El problema es todo lo que hay alrededor —un CDN,
# un proxy, un `rclone` que sincroniza a un disco— donde si se normaliza. Se
# rechaza acá porque acá se sabe que la clave es de UN tenant.
_SEGMENTO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Un objeto no puede pesar mas que esto de una sola vez. No es una regla del
# corpus: es el techo por encima del cual `put_object` deja de ser lo correcto y
# hay que subir en partes. Se declara para que el limite sea visible cuando
# aparezca el primer archivo grande, en vez de descubrirlo como un timeout.
TOPE_DE_SUBIDA_BYTES: Final = 100 * 1024 * 1024


class ClaveInvalida(ValueError):
    """La clave relativa no tiene forma de clave relativa.

    `ValueError` y no un error de peticion: quien arma estas claves es codigo del
    sistema, no un cliente. Un `..` acá es un error de programacion y tiene que
    romper fuerte en desarrollo, no volverse un 400 que alguien mira en
    produccion.
    """


class ObjetoNoEncontrado(KeyError):
    """No hay nada en esa clave, para este tenant."""


def cliente_s3() -> S3Client:
    """El cliente de S3 configurado desde el entorno.

    `signature_version="s3v4"` explicito: MinIO acepta v4 y algunas versiones de
    botocore todavia negocian v2 contra endpoints no-AWS. Una URL firmada con v2
    contra un MinIO moderno da 403, y el sintoma —"la foto no carga"— no dice
    nada de firmas.
    """
    s3 = get_settings().s3
    return boto3.client(
        "s3",
        endpoint_url=s3.endpoint,
        aws_access_key_id=s3.access_key.get_secret_value(),
        aws_secret_access_key=s3.secret_key.get_secret_value(),
        config=Config(signature_version="s3v4"),
    )


@dataclass(frozen=True)
class AlmacenDeTenant:
    """El almacen de UNA agencia. Todo lo que hace queda bajo su prefijo.

    `frozen=True` para que el tenant no se pueda reasignar despues de construido:
    un almacen que cambia de dueño a mitad de una operacion es exactamente el
    error que este diseño existe para impedir.
    """

    tenant_id: uuid.UUID

    @property
    def prefijo(self) -> str:
        return f"{self.tenant_id}/"

    def clave_absoluta(self, relativa: str) -> str:
        """La clave completa, validando que la relativa no se escape del prefijo.

        Es publica porque los tests y el dia de mañana un job de mantenimiento
        necesitan poder preguntarla — pero no hay ningun metodo que ACEPTE una
        clave absoluta, que es lo que importa.
        """
        if not relativa or relativa.startswith("/"):
            raise ClaveInvalida(f"la clave tiene que ser relativa y no vacia, y llego {relativa!r}")

        segmentos = relativa.split("/")
        for segmento in segmentos:
            if not _SEGMENTO.match(segmento):
                raise ClaveInvalida(
                    f"segmento invalido {segmento!r} en {relativa!r}: "
                    "solo letras, digitos, punto, guion y guion bajo"
                )

        return f"{self.prefijo}{relativa}"

    async def guardar(self, relativa: str, contenido: bytes, *, tipo: str) -> str:
        """Sube un objeto y devuelve su clave absoluta."""
        if len(contenido) > TOPE_DE_SUBIDA_BYTES:
            raise ValueError(
                f"el objeto pesa {len(contenido)} bytes y el tope de una subida "
                f"simple es {TOPE_DE_SUBIDA_BYTES}"
            )

        clave = self.clave_absoluta(relativa)
        await asyncio.to_thread(
            cliente_s3().put_object,
            Bucket=get_settings().s3.bucket,
            Key=clave,
            Body=contenido,
            ContentType=tipo,
        )
        return clave

    async def leer(self, relativa: str) -> bytes:
        """Baja un objeto. Levanta `ObjetoNoEncontrado` si no esta."""
        clave = self.clave_absoluta(relativa)

        def _bajar() -> bytes:
            try:
                respuesta = cliente_s3().get_object(Bucket=get_settings().s3.bucket, Key=clave)
            except ClientError as error:
                if error.response["Error"]["Code"] in ("NoSuchKey", "404"):
                    # El mensaje NO repite la clave absoluta: lleva el tenant
                    # adentro y este texto termina en un log.
                    raise ObjetoNoEncontrado(relativa) from error
                raise
            leido: bytes = respuesta["Body"].read()
            return leido

        return await asyncio.to_thread(_bajar)

    async def borrar(self, relativa: str) -> None:
        """Borra un objeto.

        ⚠️ ESTE SI ES UN BORRADO FISICO, y no contradice el principio 3. La regla
        habla de las ENTIDADES de negocio, que viven en PostgreSQL con su
        `deleted_at`: el objeto de storage es el archivo que una de esas filas
        referencia. La fila se da de baja y se conserva; el binario se borra
        cuando alguien decide que ya no hay que guardarlo.

        S3 no distingue "no estaba" de "lo borre": las dos dan 204. Se deja asi
        —borrar es idempotente— en vez de consultar antes, que ademas seria una
        carrera.
        """
        await asyncio.to_thread(
            cliente_s3().delete_object,
            Bucket=get_settings().s3.bucket,
            Key=self.clave_absoluta(relativa),
        )

    def url_firmada(self, relativa: str, *, ttl: int = TTL_DE_FOTO) -> str:
        """Una URL temporal para leer el objeto, sin exponer credenciales.

        NO es `async`: firmar es criptografia local con la clave secreta, sin una
        sola llamada a S3. Un `await` acá prometeria una espera que no existe.

        ⚠️ FIRMA UNA CLAVE QUE PUEDE NO EXISTIR. S3 no lo verifica al firmar, y
        no se agrega una comprobacion: seria un viaje de red por cada URL, y el
        resultado igual podria cambiar antes de que el navegador la use.
        """
        return cliente_s3().generate_presigned_url(
            "get_object",
            Params={"Bucket": get_settings().s3.bucket, "Key": self.clave_absoluta(relativa)},
            ExpiresIn=ttl,
        )
