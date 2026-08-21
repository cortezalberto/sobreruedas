"""El cliente de administracion de Keycloak, y lo que NUNCA manda.

`ADR-026` dice que la aplicacion no maneja contraseñas. La tarea 3.2 lo hizo
cumplible del lado del REALM —apagando `Direct Access Grants`—; este archivo lo
vigila del lado del CODIGO, que es la otra mitad y la que se rompe con un commit
distraido.

POR QUE UN GUARDIAN Y NO SOLO REVISION DE CODIGO
─────────────────────────────────────────────────
Crear un usuario en Keycloak CON contraseña es UN CAMPO de diferencia:
`credentials` en el cuerpo del POST. No rompe nada, no falla ningun test
existente, y deja a la aplicacion fijando contraseñas — exactamente lo que la
constitucion prohibe. Nada se pone rojo.

`test_pipeline_sin_credenciales.py` ya vigila que no haya secretos EN EL
REPOSITORIO; esto vigila que no SALGAN POR LA RED.

POR QUE `MockTransport` Y NO UN KEYCLOAK DE VERDAD
───────────────────────────────────────────────────
La regla dura 8 prohibe mockear la BASE DE DATOS, y por una razon concreta: los
tests de aislamiento multi-tenant solo prueban algo contra PostgreSQL real. Aca
no se prueba que Keycloak haga su trabajo — se prueba QUE MANDAMOS NOSOTROS, y
para eso hay que interceptar la peticion, que es justo lo que un servidor real
no deja hacer. El transporte falso no reemplaza al sistema: lo observa.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx
import pytest

from app.modules.users.keycloak import ClienteDeKeycloak

TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
SUB = "9d1f0c4e-0000-4000-8000-000000000001"

# Las CLAVES con que Keycloak recibe una contraseña. `credentials` es el
# vehiculo —es como se fija una al crear un usuario— y las otras tres son los
# campos de adentro de ese objeto.
#
# ⚠️ SE BUSCAN CLAVES, NO SUBSTRINGS, y la primera version buscaba substrings.
# Fallaba con `["UPDATE_PASSWORD"]`: el nombre de la *required action* contiene
# la palabra "password" y no es una contraseña — es, literalmente, la orden de
# que la fije OTRO. Un guardian con ese falso positivo obliga a elegir entre
# desactivarlo o no poder disparar la invitacion, y esa eleccion siempre termina
# igual.
#
# Lo que esto NO detecta: una contraseña viajando como valor suelto, sin una
# clave que la nombre. Se acepta el limite. Keycloak no tiene ninguna API que
# reciba credenciales asi, de modo que llegar ahi exigiria inventar una forma
# nueva de hacer lo que ya esta prohibido por el camino directo.
CLAVES_DE_CONTRASENIA = ("credentials", "password", "temporary", "secret")


def _claves(dato: object) -> list[str]:
    """Todas las claves de un JSON, a cualquier profundidad."""
    if isinstance(dato, dict):
        halladas = []
        for clave, valor in dato.items():
            halladas.append(str(clave))
            halladas.extend(_claves(valor))
        return halladas
    if isinstance(dato, list):
        return [clave for elemento in dato for clave in _claves(elemento)]
    return []


class Espia:
    """Un transporte que responde lo minimo y GUARDA TODO lo que se le pidio."""

    def __init__(self) -> None:
        self.peticiones: list[httpx.Request] = []

    def transporte(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._responder)

    def _responder(self, peticion: httpx.Request) -> httpx.Response:
        self.peticiones.append(peticion)

        if peticion.url.path.endswith("/protocol/openid-connect/token"):
            return httpx.Response(200, json={"access_token": "token-de-servicio"})

        if peticion.method == "POST" and peticion.url.path.endswith("/users"):
            # Keycloak devuelve el id en `Location`, no en el cuerpo.
            return httpx.Response(
                201, headers={"Location": f"http://keycloak/admin/realms/x/users/{SUB}"}
            )

        return httpx.Response(204)

    def cuerpos(self) -> list[dict[str, Any]]:
        cuerpos: list[dict[str, Any]] = []
        for peticion in self.peticiones:
            crudo = peticion.content
            if not crudo:
                continue
            try:
                cargado = json.loads(crudo)
            except json.JSONDecodeError:
                # El pedido del token va como formulario, no como JSON.
                cuerpos.append({"__formulario__": crudo.decode()})
                continue
            if isinstance(cargado, dict):
                cuerpos.append(cargado)
        return cuerpos


def _cliente(espia: Espia) -> ClienteDeKeycloak:
    return ClienteDeKeycloak(
        httpx.AsyncClient(transport=espia.transporte(), base_url="http://keycloak:8080"),
        realm="deruedas-dev",
        client_id="backend",
        # `noqa` con motivo: `S106` avisa de una contraseña hardcodeada y el
        # aviso es CORRECTO como regla — este valor no se usa para nada porque
        # el transporte falso responde sin mirarlo. Se silencia aca, en una
        # linea, y no se afloja la regla para todo el proyecto: en `app/` ese
        # mismo aviso tiene que seguir sonando.
        client_secret="da-igual",  # noqa: S106
    )


# ── 3.4 — las tres operaciones ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_crear_usuario_devuelve_el_sub_que_keycloak_asigno() -> None:
    """El `sub` sale de `Location`, que es donde Keycloak lo pone.

    No viene en el cuerpo: un 201 de Keycloak trae el cuerpo VACIO. Leerlo de
    ahi devolveria `None` sin fallar, y el espejo local quedaria sin vinculo con
    la cuenta — invisible hasta el primer login, que fallaria sin decir por que.
    """
    espia = Espia()
    sub = await _cliente(espia).crear_usuario(
        email="nuevo@agencia.test", nombre="Nueva Persona", tenant_id=TENANT, rol="salesperson"
    )

    assert sub == SUB


@pytest.mark.asyncio
async def test_crear_usuario_lo_deja_deshabilitado() -> None:
    """`D-5`: nace deshabilitado y lo habilita el flujo de invitacion.

    Si naciera habilitado y sin contraseña, existiria una cuenta activa que
    nadie reclamo todavia.
    """
    espia = Espia()
    await _cliente(espia).crear_usuario(
        email="nuevo@agencia.test", nombre="Nueva Persona", tenant_id=TENANT, rol="salesperson"
    )

    creacion = [cuerpo for cuerpo in espia.cuerpos() if "email" in cuerpo]
    assert creacion, "no se mando ningun cuerpo con el email"
    assert creacion[0]["enabled"] is False


@pytest.mark.asyncio
async def test_crear_usuario_manda_tenant_y_rol_como_atributos() -> None:
    """Sin esto el token sale sin `tenant_id` ni `role` y la API rechaza todo.

    Los mappers del realm leen ATRIBUTOS DEL USUARIO. Un mapper sin atributo que
    leer no falla: emite el token sin el claim, y el sintoma es un 401 con cara
    de problema de firma.
    """
    espia = Espia()
    await _cliente(espia).crear_usuario(
        email="nuevo@agencia.test", nombre="Nueva Persona", tenant_id=TENANT, rol="salesperson"
    )

    creacion = [cuerpo for cuerpo in espia.cuerpos() if "email" in cuerpo][0]
    assert creacion["attributes"]["tenant_id"] == [str(TENANT)]
    assert creacion["attributes"]["role"] == ["salesperson"]


@pytest.mark.asyncio
async def test_deshabilitar_no_borra() -> None:
    """`D-6`: dar de baja DESHABILITA en Keycloak, no borra.

    Borrar liberaria el email para otra cuenta y romperia la trazabilidad de que
    hizo esa persona — mismo criterio que C-04 le aplico al CUIT de una agencia.
    """
    espia = Espia()
    await _cliente(espia).deshabilitar(SUB)

    metodos = {peticion.method for peticion in espia.peticiones}
    assert "DELETE" not in metodos, "el cliente BORRA en Keycloak, y `D-6` dice deshabilitar"
    assert any(cuerpo.get("enabled") is False for cuerpo in espia.cuerpos())


@pytest.mark.asyncio
async def test_pedir_que_fije_contrasenia_dispara_la_accion_en_keycloak() -> None:
    """`D-5` paso 2: la persona fija su contraseña EN LA UI DE KEYCLOAK.

    Nosotros solo disparamos la *required action*; el formulario donde se
    escribe la contraseña es de ellos, no nuestro. Esa es toda la diferencia
    entre delegar la autenticacion y decir que se delega.
    """
    espia = Espia()
    await _cliente(espia).pedir_que_fije_contrasenia(SUB)

    ejecuciones = [p for p in espia.peticiones if "execute-actions-email" in p.url.path]
    assert ejecuciones, "no se disparo ninguna required action"
    assert json.loads(ejecuciones[0].content) == ["UPDATE_PASSWORD"]


# ── 3.5 — EL GUARDIAN ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ninguna_llamada_lleva_una_contrasenia_de_persona() -> None:
    """El test que hace de `ADR-026` una propiedad del codigo y no una promesa.

    Se ejercitan LAS TRES operaciones y se revisa todo lo que salio por el cable.

    ⚠️ LA DISTINCION QUE ESTE TEST TIENE QUE HACER BIEN. El pedido del token SI
    lleva un `client_secret`, y eso es correcto: es la credencial de la
    APLICACION, la forma en que el backend se identifica ante Keycloak.
    `ADR-026` no prohibe eso — prohibe que manejemos la contraseña de una
    PERSONA. Un test que confundiera las dos seria imposible de satisfacer, y el
    final de esa historia es que alguien lo borra por molesto.

    Por eso el pedido del token se excluye POR SU RUTA y no por su contenido: si
    mañana alguien mete la contraseña de un usuario en cualquier otra llamada, no
    hay forma de que caiga dentro de la excepcion.
    """
    espia = Espia()
    cliente = _cliente(espia)

    await cliente.crear_usuario(
        email="nuevo@agencia.test", nombre="Nueva Persona", tenant_id=TENANT, rol="salesperson"
    )
    await cliente.deshabilitar(SUB)
    await cliente.pedir_que_fije_contrasenia(SUB)

    assert espia.peticiones, "no se ejercito ninguna llamada: el test no probaria nada"

    revisadas = 0
    for peticion in espia.peticiones:
        if peticion.url.path.endswith("/protocol/openid-connect/token"):
            continue

        revisadas += 1
        if not peticion.content:
            continue

        claves = {clave.lower() for clave in _claves(json.loads(peticion.content))}
        prohibidas = claves & set(CLAVES_DE_CONTRASENIA)
        assert not prohibidas, (
            f"{peticion.method} {peticion.url.path} manda {sorted(prohibidas)} en el cuerpo.\n"
            "  `ADR-026`: la aplicacion nunca maneja la contraseña de una persona."
        )

    # Contrapeso: si el dia de mañana todas las llamadas cayeran en la excepcion
    # del token, el `for` de arriba no miraria nada y el test pasaria en verde.
    assert revisadas >= 3, f"solo se revisaron {revisadas} llamadas, y son tres operaciones"
