"""Cliente de administracion de Keycloak: lo unico que la aplicacion le pide.

TRES OPERACIONES Y NINGUNA MAS, y la lista corta es el diseño:

    crear_usuario             deshabilitado y sin credencial
    deshabilitar              `D-6` — dar de baja no borra
    pedir_que_fije_contrasenia  dispara la *required action*

⚠️ NO HAY `fijar_contrasenia`, Y NO ES UN OLVIDO. `ADR-026` delega la
autenticacion entera a Keycloak: la persona escribe su contraseña en el
formulario DE KEYCLOAK, al que llega por el mail que dispara
`pedir_que_fije_contrasenia`. Agregar aca un metodo que mande `credentials`
seria una linea, no rompe nada, y convertiria a esta aplicacion en algo que
maneja contraseñas. `tests/unit/test_keycloak_admin.py` lo vigila revisando lo
que sale por el cable.

QUE SABE KEYCLOAK Y QUE SABEMOS NOSOTROS
─────────────────────────────────────────
`D-1` fija la frontera: credenciales y sesiones son de Keycloak; rol, tenant y
sucursales son nuestros. El email vive en los dos lados y **gana el del token**.

Lo unico que este cliente le manda a Keycloak de lo nuestro son `tenant_id` y
`role` COMO ATRIBUTOS, y no por gusto: los *mappers* del realm los leen de ahi
para emitirlos como claims planos (`ADR-021`). Un mapper sin atributo que leer
no falla — emite el token sin el claim, y el sintoma es un 401 en todo con cara
de problema de firma.
"""

from __future__ import annotations

import uuid
from types import TracebackType

import httpx

__all__ = ["ClienteDeKeycloak", "ErrorDeKeycloak"]


class ErrorDeKeycloak(RuntimeError):
    """Keycloak rechazo la operacion.

    Se distingue de un error nuestro a proposito: `D-5` ordena las escrituras
    —primero Keycloak, despues local— justamente para que un fallo de este lado
    ocurra ANTES de tocar la base, y no deje a nadie invitado sin cuenta.
    """

    def __init__(self, operacion: str, respuesta: httpx.Response) -> None:
        super().__init__(f"Keycloak rechazo `{operacion}` con {respuesta.status_code}")
        self.operacion = operacion
        self.status_code = respuesta.status_code


class ClienteDeKeycloak:
    """Habla con la API de administracion usando el service account del backend.

    El token se pide con `client_credentials` —la credencial de la APLICACION,
    no la de una persona—, que es el unico flujo que le queda al cliente
    `backend` desde que la tarea 3.2 apago `Direct Access Grants`.
    """

    def __init__(
        self,
        cliente: httpx.AsyncClient,
        *,
        realm: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._cliente = cliente
        self._realm = realm
        self._client_id = client_id
        self._client_secret = client_secret

    async def __aenter__(self) -> ClienteDeKeycloak:
        return self

    async def __aexit__(
        self,
        tipo: type[BaseException] | None,
        valor: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        await self._cliente.aclose()

    # ── El token de servicio ────────────────────────────────────────────────

    async def _token(self) -> str:
        """`client_credentials`, que NO es la contraseña de nadie.

        Es la unica llamada de esta clase que lleva un secreto, y es el de la
        aplicacion. El guardian de `test_keycloak_admin.py` la excluye por su
        RUTA y no por su contenido, para que la excepcion no pueda cubrir a otra.
        """
        respuesta = await self._cliente.post(
            f"/realms/{self._realm}/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        if respuesta.status_code != httpx.codes.OK:
            raise ErrorDeKeycloak("obtener el token de servicio", respuesta)

        token: str = respuesta.json()["access_token"]
        return token

    async def _cabecera(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {await self._token()}"}

    def _usuarios(self) -> str:
        return f"/admin/realms/{self._realm}/users"

    # ── Las tres operaciones ────────────────────────────────────────────────

    async def crear_usuario(
        self, *, email: str, nombre: str, tenant_id: uuid.UUID, rol: str
    ) -> str:
        """Crea la cuenta DESHABILITADA y sin credencial. Devuelve el `sub`.

        Deshabilitada porque `D-5` la habilita recien cuando la persona acepta
        la invitacion: una cuenta activa que nadie reclamo todavia es una cuenta
        de mas.

        ⚠️ EL `sub` SALE DE `Location`. Un 201 de Keycloak trae el cuerpo vacio,
        asi que buscarlo ahi devolveria `None` sin fallar y el espejo local
        quedaria sin vinculo con la cuenta — invisible hasta el primer login.
        """
        respuesta = await self._cliente.post(
            self._usuarios(),
            headers=await self._cabecera(),
            json={
                "email": email,
                "username": email,
                "firstName": nombre,
                "enabled": False,
                "emailVerified": False,
                "attributes": {"tenant_id": [str(tenant_id)], "role": [rol]},
            },
        )
        if respuesta.status_code != httpx.codes.CREATED:
            raise ErrorDeKeycloak("crear el usuario", respuesta)

        # Anotado porque `headers.get` de httpx devuelve `Any`, y sin esto
        # `mypy --strict` marca el `return` de abajo como devolucion de `Any`.
        ubicacion: str = respuesta.headers.get("Location", "")
        sub = ubicacion.rstrip("/").rsplit("/", 1)[-1]
        if not sub:
            raise ErrorDeKeycloak("leer el id del usuario creado", respuesta)

        return sub

    async def deshabilitar(self, sub: str) -> None:
        """`D-6`: la baja deshabilita, no borra.

        Borrar liberaria el email para otra cuenta y romperia la trazabilidad de
        que hizo esa persona — mismo criterio que C-04 le aplico al CUIT de una
        agencia dada de baja.
        """
        respuesta = await self._cliente.put(
            f"{self._usuarios()}/{sub}",
            headers=await self._cabecera(),
            json={"enabled": False},
        )
        if respuesta.status_code not in (httpx.codes.OK, httpx.codes.NO_CONTENT):
            raise ErrorDeKeycloak("deshabilitar el usuario", respuesta)

    async def rehabilitar(self, sub: str) -> None:
        """La otra mitad de `D-6`, y la que hace posible la reincorporacion.

        Como la baja DESHABILITA en vez de borrar, la cuenta sigue existiendo
        con su email tomado. Cuando esa persona vuelve, crear una cuenta nueva
        reboteria con 409 — hay que reactivar la que ya esta.

        No toca credenciales: la persona vuelve a fijar su contraseña por el
        mail de la *required action*, igual que en la primera invitacion.
        """
        respuesta = await self._cliente.put(
            f"{self._usuarios()}/{sub}",
            headers=await self._cabecera(),
            json={"enabled": True},
        )
        if respuesta.status_code not in (httpx.codes.OK, httpx.codes.NO_CONTENT):
            raise ErrorDeKeycloak("rehabilitar el usuario", respuesta)

    async def pedir_que_fije_contrasenia(self, sub: str) -> None:
        """Dispara `UPDATE_PASSWORD` — el mail lo manda Keycloak, no nosotros.

        Este metodo es la razon por la que no hace falta ninguno que mande una
        contraseña: la persona la escribe en el formulario de Keycloak, al que
        llega por ese mail. Nosotros no vemos ni el formulario ni el valor.
        """
        respuesta = await self._cliente.put(
            f"{self._usuarios()}/{sub}/execute-actions-email",
            headers=await self._cabecera(),
            json=["UPDATE_PASSWORD"],
        )
        if respuesta.status_code not in (httpx.codes.OK, httpx.codes.NO_CONTENT):
            raise ErrorDeKeycloak("pedir que fije la contrasenia", respuesta)
