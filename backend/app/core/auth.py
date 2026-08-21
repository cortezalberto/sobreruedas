"""Identidad: de que token viene una peticion — T-013, capability `platform/identity`.

LA APLICACION NO SABE DE CONTRASENAS
────────────────────────────────────
Y no es una simplificacion: es el Articulo 3 de la constitucion y `ADR-007`. Acá
no se hashea, no se verifica y no se recibe ninguna contrasena. Lo unico que
este modulo hace es comprobar que un token lo emitio Keycloak y leer quien es el
sujeto. Si alguna vez aparece un `password` en este archivo, algo se rompio.

QUE SE VERIFICA, Y POR QUE CADA COSA
────────────────────────────────────
  firma      — que lo emitio el proveedor y nadie lo toco.
  vencimiento— que sigue vigente.
  emisor     — que es de NUESTRO realm. Una misma instalacion de Keycloak puede
               tener varios; sin esta verificacion, un token de un realm vecino
               entraria como propio.
  receptor   — que se emitio para ESTA API. Sin esto, el token que un usuario
               obtuvo para otra aplicacion del mismo realm serviria aca.

Y el algoritmo se IMPONE, no se lee del token: aceptar el que el token declara
es el ataque `alg: none`, donde cualquiera se emite un token de administrador.

EL SUJETO SALE DEL TOKEN Y DE NINGUN OTRO LADO
──────────────────────────────────────────────
Identificador, tenant y rol vienen de los claims. No del cuerpo, ni de la ruta,
ni de una cabecera — nada que el cliente pueda escribir (regla dura 1).

Y si falta alguno, la peticion se RECHAZA en vez de suponerlo. Un rol por
defecto seria un permiso que nadie otorgo; un tenant por defecto seria un tenant
al que se le entregan datos de otro (`RN-MT-06`).

EL ROL NO SE VALIDA CONTRA NINGUN CATALOGO (D-9)
────────────────────────────────────────────────
Este modulo lo extrae tal como viene; `rbac.py` lo contrasta. La separacion es
lo que permite avanzar: el catalogo depende de `E-001`, que sigue en discusion.
Si la identidad enumerara los roles, esa traba se comeria tambien la
autenticacion, que no tiene por que esperar.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import httpx
import jwt
from fastapi import Depends, Request
from jwt import PyJWK

from app.config import get_settings
from app.core.errors import AuthenticationError

# ⚠️ NOMBRES DE CLAIM — DECISION DE ESTE CHANGE, A IMPLEMENTAR EN EL REALM
#
# Ningun documento del corpus fija como viaja el tenant ni el rol en el token.
# Se elige que vayan como claims de primer nivel, y NO en `realm_access.roles`
# —que es el default de Keycloak— por dos motivos:
#
#   1. `realm_access.roles` es una LISTA. Un usuario con dos roles obligaria a
#      elegir uno, y esa eleccion no la puede hacer la capa de identidad.
#   2. El tenant no es un rol y no tiene lugar natural en esa estructura.
#
# C-05 configura el realm y tiene que crear los dos mappers correspondientes.
# Hasta entonces esta decision vive solo aca.
CLAIM_TENANT = "tenant_id"
CLAIM_ROL = "role"

# Se impone, no se lee del token. Ver el encabezado.
ALGORITMOS = ["RS256"]


def _es_clave_de_firma(clave: dict[str, Any]) -> bool:
    """Si esa entrada del JWKS sirve para VERIFICAR una firma.

    Un realm de Keycloak publica tambien una clave de cifrado (`use: "enc"`,
    `alg: "RSA-OAEP"`), y PyJWT no puede construirla. Ver `_refrescar`.

    Se acepta la que no declara `use` ni `alg`: la RFC 7517 los marca opcionales,
    y rechazar por ausencia dejaria afuera proveedores que firman bien. Lo que se
    descarta es lo que se declara COMO OTRA COSA.
    """
    uso = clave.get("use")
    if uso is not None and uso != "sig":
        return False

    algoritmo = clave.get("alg")
    return algoritmo is None or algoritmo in ALGORITMOS


# Cuanto vive el JWKS cacheado, y cada cuanto se admite un refresco bajo demanda.
# Sin fuente en el corpus (`design.md` · Open Questions): se arranca conservador
# y se ajusta con datos de operacion. Cambiarlos no toca specs ni tareas.
TTL_DE_CLAVES = timedelta(hours=1)
MINIMO_ENTRE_REFRESCOS = timedelta(minutes=5)


class NoAutenticado(AuthenticationError):
    """El token no sirve, o no vino.

    Un solo error para todas las causas a proposito. Distinguir "firma
    invalida" de "expirado" o de "otro emisor" le confirma a quien esta
    probando cual de las tres cosas acerto, y no le sirve de nada a un cliente
    legitimo — que ante cualquiera de las tres hace lo mismo: pedir un token
    nuevo.

    El motivo real se registra, no se responde.
    """

    def __init__(self, detail: str = "el token no es valido o no fue presentado") -> None:
        super().__init__(detail, code="not_authenticated")


@dataclass(frozen=True)
class Sujeto:
    """Quien hace la peticion, segun el token y nada mas."""

    user_id: str
    tenant_id: uuid.UUID
    role: str
    # OPCIONAL A PROPOSITO, aunque hoy siempre venga. El claim `email` lo aporta
    # el client scope homonimo, que es un DEFAULT del realm y no una garantia
    # del protocolo: un cliente configurado sin ese scope emite tokens sin
    # `email`. Tiparlo `str` obligaria a inventar un valor cuando falta, y el
    # valor inventado terminaria pisando el del espejo (`D-1`).
    email: str | None = None


async def _traer_por_http(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=5.0) as cliente:
        respuesta = await cliente.get(url)
        respuesta.raise_for_status()
        datos: dict[str, Any] = respuesta.json()
        return datos


@dataclass
class ClavesDelProveedor:
    """Las claves publicas del realm, cacheadas (D-8).

    EL EQUILIBRIO QUE RESUELVE
    ──────────────────────────
    Pedirlas en cada peticion ata la latencia de toda la API a la de Keycloak.
    Cachearlas para siempre hace que una rotacion tumbe el servicio hasta que
    alguien reinicie.

    Entonces: vencimiento **y** refresco bajo demanda cuando llega un `kid` que
    no esta. Eso resuelve la rotacion sin esperar al vencimiento.

    Y el refresco bajo demanda tiene LIMITE DE FRECUENCIA, porque si no es un
    agujero: mandar tokens con `kid` basura provocaria una consulta a Keycloak
    por peticion. Denegacion de servicio gratuita, contra la dependencia mas
    critica del sistema.
    """

    url: str
    traer: Callable[[], Awaitable[dict[str, Any]]] | None = None
    ttl: timedelta = TTL_DE_CLAVES
    minimo_entre_refrescos: timedelta = MINIMO_ENTRE_REFRESCOS
    reloj: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))

    _claves: dict[str, PyJWK] = field(default_factory=dict, init=False)
    _vence: datetime | None = field(default=None, init=False)
    # DOS RELOJES, NO UNO
    # ───────────────────
    # El limite de frecuencia acota SOLO los refrescos bajo demanda, y por eso
    # se lleva su propia marca. Con una sola compartida, el refresco programado
    # —el del vencimiento— consumia el presupuesto del otro: una rotacion que
    # ocurriera dentro de los minutos siguientes a un vencimiento quedaba
    # bloqueada por el limite y la API rechazaba todo hasta el vencimiento
    # siguiente. Que es exactamente lo que el refresco bajo demanda existe para
    # evitar.
    _ultimo_bajo_demanda: datetime | None = field(default=None, init=False)

    async def _refrescar(self) -> None:
        """Carga el JWKS, quedandose SOLO con las claves de firma.

        ⚠️ EL FILTRO NO ES UNA OPTIMIZACION: sin el, la aplicacion no puede
        hablar con un Keycloak de verdad.

        Un realm de Keycloak publica al menos DOS claves: la de firma (`RS256`)
        y una de cifrado (`use: "enc"`, `alg: "RSA-OAEP"`). `PyJWK.from_dict`
        no sabe construir la segunda y levanta `PyJWKError: Unable to find an
        algorithm for key`. Como el diccionario se armaba de una, esa excepcion
        se llevaba puesto el JWKS ENTERO — incluida la clave buena— y **toda**
        peticion autenticada moria con 500.

        No lo vieron los tests porque `EmisorDePrueba` publica un JWKS con una
        sola clave de firma, que es lo razonable para un doble. Aparecio la
        primera vez que se pidio un token al Keycloak del compose.

        Se descarta por `use` y por `alg`, no por uno de los dos: `use` es
        opcional en la RFC 7517, y hay proveedores que solo mandan `alg`.
        """
        documento = await (self.traer() if self.traer else _traer_por_http(self.url))
        self._claves = {
            clave["kid"]: PyJWK.from_dict(clave)
            for clave in documento.get("keys", [])
            if "kid" in clave and _es_clave_de_firma(clave)
        }
        self._vence = self.reloj() + self.ttl

    def _vencido(self) -> bool:
        return self._vence is None or self.reloj() >= self._vence

    def _puede_refrescar_bajo_demanda(self) -> bool:
        if self._ultimo_bajo_demanda is None:
            return True
        return self.reloj() - self._ultimo_bajo_demanda >= self.minimo_entre_refrescos

    async def clave_para(self, kid: str) -> PyJWK:
        """La clave publica de ese `kid`, refrescando si hace falta y se puede."""
        if self._vencido():
            await self._refrescar()

        if kid not in self._claves and self._puede_refrescar_bajo_demanda():
            # Rotacion: el proveedor firmo con una clave que todavia no vimos.
            self._ultimo_bajo_demanda = self.reloj()
            await self._refrescar()

        try:
            return self._claves[kid]
        except KeyError as error:
            # El `kid` NO se incluye: viene del token, o sea de afuera.
            raise NoAutenticado from error


def _uuid_del_claim(claims: dict[str, Any], nombre: str) -> uuid.UUID:
    valor = claims.get(nombre)
    if not isinstance(valor, str) or not valor:
        raise NoAutenticado
    try:
        return uuid.UUID(valor)
    except ValueError as error:
        raise NoAutenticado from error


async def validar_token(
    token: str,
    *,
    claves: ClavesDelProveedor,
    emisor: str,
    receptor: str,
) -> Sujeto:
    """Verifica el token y devuelve el sujeto. Rompe con `NoAutenticado` si algo falla.

    El orden importa: primero se saca el `kid` del ENCABEZADO —que no esta
    firmado y por lo tanto no se cree nada de el salvo a que clave apunta—, y
    recien despues se verifica la firma. Nada del contenido se toca antes de
    que la firma cierre.
    """
    try:
        encabezado = jwt.get_unverified_header(token)
    except jwt.PyJWTError as error:
        raise NoAutenticado from error

    kid = encabezado.get("kid")
    if not isinstance(kid, str):
        # Sin `kid` no se sabe contra que clave verificar. La alternativa
        # —probar todas— convierte cada token basura en tantas verificaciones
        # criptograficas como claves tenga el realm.
        raise NoAutenticado

    clave = await claves.clave_para(kid)

    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            key=clave,
            # Impuesto, no leido del token. Ver el encabezado del modulo.
            algorithms=ALGORITMOS,
            audience=receptor,
            issuer=emisor,
            # `require` es lo que hace que un token sin `exp` no sea eterno:
            # sin esto, PyJWT no verifica un vencimiento que no esta.
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as error:
        raise NoAutenticado from error

    sub = claims.get("sub")
    rol = claims.get(CLAIM_ROL)
    if not isinstance(sub, str) or not sub or not isinstance(rol, str) or not rol:
        raise NoAutenticado

    # El email NO se exige en `require`: su ausencia no invalida el token, solo
    # significa que no hay con que corregir el espejo (`D-1`). Un token sin
    # `email` sigue identificando a alguien.
    email = claims.get("email")

    return Sujeto(
        user_id=sub,
        tenant_id=_uuid_del_claim(claims, CLAIM_TENANT),
        role=rol,
        email=email if isinstance(email, str) and email else None,
    )


# El caché vive en el proceso y se comparte entre peticiones — que es
# justamente el punto. Se crea perezosamente para no exigir `Settings` al
# importar el modulo.
_claves_del_proceso: ClavesDelProveedor | None = None


def claves_del_proveedor() -> ClavesDelProveedor:
    global _claves_del_proceso
    if _claves_del_proceso is None:
        _claves_del_proceso = ClavesDelProveedor(url=get_settings().keycloak.jwks_endpoint)
    return _claves_del_proceso


def emisor_esperado() -> str:
    """El `iss` que se exige en el token.

    Sale de `KeycloakSettings.emisor`, que NO siempre es `url`: el navegador
    pide el token por el hostname publico y el backend habla con Keycloak por el
    nombre interno de la red. Ver el docstring de esa propiedad.
    """
    return get_settings().keycloak.emisor


def token_de_la_cabecera(autorizacion: str | None) -> str:
    """El token del `Authorization: Bearer <token>`, o rompe.

    El esquema se compara sin distinguir mayusculas —`RFC 7235` lo pide— pero
    se exige que sea `Bearer`: aceptar cualquier esquema abriria la puerta a que
    un cliente mande `Basic` con credenciales, que es exactamente lo que este
    sistema no hace (Art. 3).
    """
    if not autorizacion:
        raise NoAutenticado

    partes = autorizacion.split(" ", 1)
    if len(partes) != 2 or partes[0].lower() != "bearer" or not partes[1].strip():
        raise NoAutenticado

    return partes[1].strip()


async def get_current_user(request: Request) -> Sujeto:
    """El sujeto de la peticion. La dependency que protege cada endpoint.

    Todo lo que devuelve sale del token verificado. Nada de aca puede
    contradecirse con un valor del cuerpo, de la ruta o de una cabecera: la
    peticion no participa mas que trayendo el token.
    """
    token = token_de_la_cabecera(request.headers.get("Authorization"))
    return await validar_token(
        token,
        claves=claves_del_proveedor(),
        emisor=emisor_esperado(),
        receptor=get_settings().keycloak.client_id,
    )


# El alias que va a usar cada endpoint protegido:
#
#     async def listar(sujeto: SujetoActual) -> ...
#
# `Annotated` y no `= Depends(...)` en el default: el default mutable es un
# vicio que ruff marca con `B008`, y sobre todo un parametro con valor por
# defecto se lee como opcional. La identidad no es opcional.
SujetoActual = Annotated[Sujeto, Depends(get_current_user)]


# ─────────────────────────────────────────────────────────────────────────────
# Rutas exentas — se declaran, no se descubren
#
# La lista se escribe a mano A PROPOSITO. Una exencion que se autodetecta no es
# una exencion: es un agujero que aparece solo. Agregar una entrada aca es una
# decision que se lee en un diff, y el test de `test_auth_rutas.py` verifica que
# ninguna ruta fuera de esta lista se atienda sin token.
#
# El limite es duro: **ninguna ruta que exponga datos de un tenant puede estar
# aca**. Las categorias admitidas son:
#
#   1. Sondas de estado.
#   2. Documentacion — que ademas se bloquea en produccion.
#   3. Receptores de notificaciones externas, que verifican la autenticidad del
#      emisor por su propio mecanismo (firma HMAC del webhook) en vez de token.
#   4. **Catalogos cross-tenant de solo lectura** — agregada el 18-ago-2026.
#
# La categoria 4 merece su justificacion, porque es la unica que devuelve datos
# de negocio. `plans` y el catalogo de vehiculos NO contienen dato de ninguna
# agencia: son los mismos para todas, no llevan `tenant_id`, figuran en
# `EXENTAS_DE_RLS` y la base les tiene REVOCADA la escritura (migraciones `009`
# y `010`). La grilla de precios es informacion publica —es la pagina de
# pricing— y el catalogo de marcas lo necesita el portal publico (C-22/C-23).
#
# ⚠️ Exigir token acá no agregaria aislamiento: no hay nada que aislar. Lo que
# si hace falta y NO esta puesto todavia es limitar la tasa por IP sobre estas
# rutas, que es el control que corresponde a una superficie anonima. Queda
# anotado para C-03.
# ─────────────────────────────────────────────────────────────────────────────
RUTAS_EXENTAS = frozenset(
    {
        "/health",  # sonda de vida
        "/ready",  # sonda de disponibilidad
        "/docs",  # documentacion interactiva
        "/redoc",
        "/openapi.json",
        # Categoria 4 — catalogos cross-tenant de solo lectura. Ver arriba.
        "/api/v1/plans",
        "/api/v1/catalog/brands",
        "/api/v1/catalog/brands/{marca_id}/models",
    }
)
