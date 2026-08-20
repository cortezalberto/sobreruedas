"""Validacion de tokens e identidad — C-02, bloque 3 (`T-013`).

ESTOS TESTS SON LA PUERTA DE ENTRADA AL SISTEMA. Todo lo que este mal aca deja
pasar a alguien que no deberia, o deja afuera a todos.

Unitarios y no de integracion, y no es una excepcion a la regla dura 8: lo que
se prueba es criptografia y logica de claims, no el comportamiento de un motor
externo. El proveedor de identidad se sustituye por uno de prueba —ver
`tests/emisor_de_tokens.py`— porque lo que hay que ejercitar es la aplicacion
RECHAZANDO tokens malos, y un Keycloak de verdad no los emite.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

import pytest

from app.core.auth import (
    ClavesDelProveedor,
    NoAutenticado,
    Sujeto,
    _es_clave_de_firma,
    validar_token,
)

from ..emisor_de_tokens import RECEPTOR, EmisorDePrueba


@pytest.fixture
def proveedor() -> EmisorDePrueba:
    return EmisorDePrueba()


def claves_de(*emisores: EmisorDePrueba, **kwargs: Any) -> ClavesDelProveedor:
    """Caché apuntado a un JWKS de mentira, sin red de por medio."""
    llamadas: list[int] = []

    async def traer() -> dict[str, list[dict[str, Any]]]:
        llamadas.append(1)
        claves: list[dict[str, Any]] = []
        for emisor in emisores:
            claves.extend(emisor.jwks["keys"])
        return {"keys": claves}

    cache = ClavesDelProveedor(url="http://no-se-usa", traer=traer, **kwargs)
    cache.llamadas = llamadas  # type: ignore[attr-defined]  # para contar en los tests
    return cache


async def validar(token: str, claves: ClavesDelProveedor, emisor: str) -> Sujeto:
    return await validar_token(token, claves=claves, emisor=emisor, receptor=RECEPTOR)


# ── 3.1 · Un token bueno pasa ────────────────────────────────────────────────


async def test_un_token_valido_da_el_sujeto(proveedor: EmisorDePrueba) -> None:
    """Contrapeso de todo lo que sigue.

    Sin este, una validacion que rechaza absolutamente todo pasaria los cinco
    tests de rechazo con honores y dejaria la API inutilizable.
    """
    tenant = uuid.uuid4()
    token = proveedor.firmar(sub="usuario-1", tenant_id=tenant, role="manager")

    sujeto = await validar(token, claves_de(proveedor), proveedor.emisor)

    assert sujeto.user_id == "usuario-1"
    assert sujeto.tenant_id == tenant
    assert sujeto.role == "manager"


# ── 3.1 · Los cinco rechazos ─────────────────────────────────────────────────


async def test_firma_invalida_se_rechaza(proveedor: EmisorDePrueba) -> None:
    """El token dice ser del proveedor y lo firmo otro.

    Es el ataque que toda esta maquinaria existe para frenar: el `kid` del
    encabezado apunta a la clave publicada, todos los claims estan bien, y la
    firma no cierra.
    """
    token = proveedor.firmar_con_otra_clave()

    with pytest.raises(NoAutenticado):
        await validar(token, claves_de(proveedor), proveedor.emisor)


async def test_token_expirado_se_rechaza(proveedor: EmisorDePrueba) -> None:
    token = proveedor.firmar(vence_en=timedelta(minutes=-1))

    with pytest.raises(NoAutenticado):
        await validar(token, claves_de(proveedor), proveedor.emisor)


async def test_emisor_distinto_se_rechaza(proveedor: EmisorDePrueba) -> None:
    """Firmado con la clave correcta pero declarando otro emisor.

    Importa mas de lo que parece: si el realm cambia y la aplicacion no lo
    verifica, un token de un realm vecino —de otro producto de la misma
    instalacion de Keycloak— entraria como propio.
    """
    token = proveedor.firmar(emisor="https://keycloak.de-prueba/realms/otro-realm")

    with pytest.raises(NoAutenticado):
        await validar(token, claves_de(proveedor), proveedor.emisor)


async def test_receptor_distinto_se_rechaza(proveedor: EmisorDePrueba) -> None:
    """Un token emitido para OTRO cliente del mismo realm.

    Sin verificar el receptor, un token que el usuario obtuvo para el frontend
    de otra aplicacion serviria contra esta API.
    """
    token = proveedor.firmar(receptor="otro-cliente")

    with pytest.raises(NoAutenticado):
        await validar(token, claves_de(proveedor), proveedor.emisor)


@pytest.mark.parametrize(
    ("token", "por_que"),
    [
        ("", "cadena vacia"),
        ("no-es-un-jwt", "no tiene la forma"),
        ("a.b.c", "tres partes que no son base64 valido"),
    ],
)
async def test_un_token_que_no_es_token_se_rechaza(
    proveedor: EmisorDePrueba, token: str, por_que: str
) -> None:
    with pytest.raises(NoAutenticado):
        await validar(token, claves_de(proveedor), proveedor.emisor)


async def test_un_token_sin_kid_se_rechaza(proveedor: EmisorDePrueba) -> None:
    """Sin `kid` no hay forma de saber contra que clave verificar.

    Probar todas las claves publicadas seria la alternativa, y es justo lo que
    no hay que hacer: convierte cada token basura en tantas verificaciones
    criptograficas como claves tenga el realm.
    """
    import jwt

    token = jwt.encode({"sub": "x"}, proveedor._privada, algorithm="RS256")  # noqa: SLF001

    with pytest.raises(NoAutenticado):
        await validar(token, claves_de(proveedor), proveedor.emisor)


async def test_el_algoritmo_none_se_rechaza(proveedor: EmisorDePrueba) -> None:
    """El ataque clasico: `alg: none` y ninguna firma.

    Si la aplicacion aceptara el algoritmo que declara el token en vez de exigir
    el suyo, cualquiera se emitiria un token de administrador.
    """
    import jwt

    token = jwt.encode(
        {"sub": "x", "iss": proveedor.emisor, "aud": RECEPTOR},
        key="",
        algorithm="none",
        headers={"kid": proveedor.kid},
    )

    with pytest.raises(NoAutenticado):
        await validar(token, claves_de(proveedor), proveedor.emisor)


# ── 3.5 · El sujeto sale del token, y si falta algo se rechaza ───────────────


@pytest.mark.parametrize("falta", ["sub", "tenant_id", "role"])
async def test_un_token_al_que_le_falta_un_dato_se_rechaza(
    proveedor: EmisorDePrueba, falta: str
) -> None:
    """Rechazar y NO suponer.

    Un rol por defecto seria un permiso que nadie otorgo; un tenant por defecto
    seria un tenant al que se le entregan datos de otro (`RN-MT-06`).
    """
    token = proveedor.firmar(omitir=(falta,))

    with pytest.raises(NoAutenticado):
        await validar(token, claves_de(proveedor), proveedor.emisor)


async def test_un_tenant_que_no_es_uuid_se_rechaza(proveedor: EmisorDePrueba) -> None:
    token = proveedor.firmar(extra={"tenant_id": "no-es-uuid"})

    with pytest.raises(NoAutenticado):
        await validar(token, claves_de(proveedor), proveedor.emisor)


async def test_el_rol_no_se_valida_contra_ningun_catalogo(proveedor: EmisorDePrueba) -> None:
    """D-9: `auth.py` extrae el rol, `rbac.py` lo contrasta.

    La separacion es lo que permite avanzar: el catalogo depende de `E-001`, que
    sigue en discusion. Si esta capa enumerara los roles, la traba se comeria
    tambien la identidad — que no tiene por que esperar.
    """
    token = proveedor.firmar(role="un_rol_que_no_existe_en_ningun_catalogo")

    sujeto = await validar(token, claves_de(proveedor), proveedor.emisor)

    assert sujeto.role == "un_rol_que_no_existe_en_ningun_catalogo"


async def test_el_error_nunca_incluye_el_token(proveedor: EmisorDePrueba) -> None:
    """Un token en un mensaje de error termina en un log, y sigue sirviendo."""
    token = proveedor.firmar(vence_en=timedelta(minutes=-1))

    with pytest.raises(NoAutenticado) as capturado:
        await validar(token, claves_de(proveedor), proveedor.emisor)

    assert token not in str(capturado.value)


# ── 3.2 y 3.3 · El caché de claves y la rotacion ─────────────────────────────


async def test_las_claves_se_cachean_entre_validaciones(proveedor: EmisorDePrueba) -> None:
    """Pedirlas en cada peticion ataria la latencia de la API a la de Keycloak."""
    claves = claves_de(proveedor)

    for _ in range(5):
        await validar(proveedor.firmar(), claves, proveedor.emisor)

    assert len(claves.llamadas) == 1  # type: ignore[attr-defined]


async def test_el_cache_se_renueva_al_vencer(proveedor: EmisorDePrueba) -> None:
    """Cachearlas para siempre haria que una rotacion tumbara el servicio."""
    reloj = Reloj()
    claves = claves_de(proveedor, ttl=timedelta(minutes=10), reloj=reloj)

    await validar(proveedor.firmar(), claves, proveedor.emisor)
    reloj.avanzar(timedelta(minutes=11))
    await validar(proveedor.firmar(), claves, proveedor.emisor)

    assert len(claves.llamadas) == 2  # type: ignore[attr-defined]


async def test_una_clave_nueva_se_toma_sin_reiniciar(proveedor: EmisorDePrueba) -> None:
    """La rotacion: el proveedor emite con una clave que el cache no conoce.

    Se resuelve refrescando BAJO DEMANDA ante un `kid` desconocido. Sin eso, una
    rotacion dejaria la API rechazando todo hasta que venciera el cache — o
    hasta que alguien reiniciara el servicio a las tres de la manana.
    """
    rotada = EmisorDePrueba(emisor=proveedor.emisor)
    publicadas = [proveedor]

    llamadas: list[int] = []

    async def traer() -> dict[str, list[dict[str, Any]]]:
        llamadas.append(1)
        return {"keys": [k for e in publicadas for k in e.jwks["keys"]]}

    claves = ClavesDelProveedor(url="http://no-se-usa", traer=traer)

    # Primero anda con la clave vieja.
    await validar(proveedor.firmar(), claves, proveedor.emisor)

    # El proveedor rota: publica la nueva y firma con ella.
    publicadas.append(rotada)
    sujeto = await validar(rotada.firmar(), claves, proveedor.emisor)

    assert sujeto.user_id
    assert len(llamadas) == 2, "no se refresco ante el kid desconocido"


async def test_un_kid_desconocido_no_martilla_al_proveedor(
    proveedor: EmisorDePrueba,
) -> None:
    """El limite de frecuencia de D-8.

    Sin el, mandar tokens con `kid` basura convierte la validacion en un
    martillo contra Keycloak: cada peticion invalida provoca una consulta. Es
    una denegacion de servicio gratuita, y contra la dependencia mas critica.
    """
    reloj = Reloj()
    claves = claves_de(proveedor, minimo_entre_refrescos=timedelta(minutes=5), reloj=reloj)

    await validar(proveedor.firmar(), claves, proveedor.emisor)
    de_arranque = len(claves.llamadas)  # type: ignore[attr-defined]

    impostor = EmisorDePrueba(kid="kid-que-no-existe", emisor=proveedor.emisor)
    for _ in range(20):
        with pytest.raises(NoAutenticado):
            await validar(impostor.firmar(), claves, proveedor.emisor)

    assert len(claves.llamadas) == de_arranque + 1, (  # type: ignore[attr-defined]
        "cada token con kid desconocido provoco una consulta al proveedor"
    )


async def test_pasado_el_limite_se_vuelve_a_intentar(proveedor: EmisorDePrueba) -> None:
    """Contrapeso: el limite acota la frecuencia, no apaga el refresco.

    Si lo apagara, una rotacion que ocurriera justo despues de un `kid` basura
    quedaria sin resolver hasta el vencimiento del cache.
    """
    reloj = Reloj()
    claves = claves_de(proveedor, minimo_entre_refrescos=timedelta(minutes=5), reloj=reloj)
    impostor = EmisorDePrueba(kid="kid-que-no-existe", emisor=proveedor.emisor)

    with pytest.raises(NoAutenticado):
        await validar(impostor.firmar(), claves, proveedor.emisor)
    primeras = len(claves.llamadas)  # type: ignore[attr-defined]

    reloj.avanzar(timedelta(minutes=6))
    with pytest.raises(NoAutenticado):
        await validar(impostor.firmar(), claves, proveedor.emisor)

    assert len(claves.llamadas) == primeras + 1  # type: ignore[attr-defined]


class Reloj:
    """Un reloj que se mueve a mano.

    Los vencimientos se miden en minutos: un test que los espere de verdad tarda
    lo mismo que el vencimiento, y no prueba nada mejor.
    """

    def __init__(self) -> None:
        from datetime import UTC, datetime

        self._ahora = datetime.now(UTC)

    def __call__(self) -> Any:
        return self._ahora

    def avanzar(self, cuanto: timedelta) -> None:
        self._ahora += cuanto


# ── El JWKS de un Keycloak de verdad trae mas de una clave ───────────────────


async def test_una_clave_de_cifrado_en_el_jwks_no_rompe_la_validacion() -> None:
    """El defecto que aparecio la primera vez que se hablo con Keycloak real.

    Un realm publica al menos DOS claves: la de firma y una de CIFRADO
    (`use: "enc"`, `alg: "RSA-OAEP"`). `PyJWK.from_dict` no sabe construir la
    segunda y levanta `PyJWKError`. Como el diccionario se armaba de una sola
    comprension, esa excepcion se llevaba puesto el JWKS entero —incluida la
    clave buena— y **toda** peticion autenticada respondia 500.

    No lo vieron los demas tests porque `EmisorDePrueba` publica un JWKS con una
    sola clave de firma, que es lo razonable para un doble. Este test mete la de
    cifrado a proposito.
    """
    emisor = EmisorDePrueba()
    cifrado = {
        "kid": "clave-de-cifrado",
        "kty": "RSA",
        "alg": "RSA-OAEP",
        "use": "enc",
        # `n` y `e` de relleno: nunca se llega a construirla, y ese es el punto.
        "n": "yLtI0d1fSYp7IuquXlEAkxBTTj",
        "e": "AQAB",
    }

    async def traer() -> dict[str, Any]:
        return {"keys": [cifrado, *emisor.jwks["keys"]]}

    claves = ClavesDelProveedor(url="http://no-se-usa", traer=traer)

    sujeto = await validar(emisor.firmar(), claves, emisor.emisor)

    assert sujeto.role == "manager"


async def test_la_clave_de_cifrado_no_queda_cargada() -> None:
    """Se descarta, no se guarda 'por las dudas'.

    Una clave que no puede verificar una firma en el cache solo sirve para que
    un `kid` malicioso apunte a ella y el fallo aparezca en la validacion en vez
    de en la carga — mas lejos de su causa.
    """
    emisor = EmisorDePrueba()

    async def traer() -> dict[str, Any]:
        return {
            "keys": [
                {"kid": "solo-cifrado", "kty": "RSA", "alg": "RSA-OAEP", "use": "enc"},
                *emisor.jwks["keys"],
            ]
        }

    claves = ClavesDelProveedor(url="http://no-se-usa", traer=traer)
    await validar(emisor.firmar(), claves, emisor.emisor)

    with pytest.raises(NoAutenticado):
        await claves.clave_para("solo-cifrado")


def test_una_clave_sin_use_ni_alg_se_acepta() -> None:
    """La RFC 7517 los marca OPCIONALES.

    Rechazar por ausencia dejaria afuera proveedores que firman perfectamente.
    Lo que se descarta es lo que se declara como otra cosa, no lo que no se
    declara.
    """
    assert _es_clave_de_firma({"kid": "x", "kty": "RSA"})
    assert _es_clave_de_firma({"kid": "x", "kty": "RSA", "use": "sig", "alg": "RS256"})
    assert not _es_clave_de_firma({"kid": "x", "kty": "RSA", "use": "enc"})
    assert not _es_clave_de_firma({"kid": "x", "kty": "RSA", "alg": "RSA-OAEP"})
