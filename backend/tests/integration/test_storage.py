"""El almacen de objetos contra MinIO real — C-06, `T-034`.

Sin doble de S3 (regla dura 8), y acá el motivo es especifico: **lo que se prueba
es que el aislamiento entre agencias funcione sin RLS que lo respalde**. Un doble
en memoria implementaria el prefijo tal como lo entiende quien escribe el doble,
que es la misma persona que escribio el adapter — y las dos copias del
malentendido coincidirian.

EL TEST QUE IMPORTA es `test_un_tenant_no_puede_leer_el_objeto_de_otro`. En la
base ese escenario lo corta PostgreSQL; acá no hay nada abajo, solo la forma de
la clave.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from botocore.exceptions import ClientError

from app.core.storage import (
    TOPE_DE_SUBIDA_BYTES,
    TTL_DE_DOCUMENTO,
    TTL_DE_FOTO,
    AlmacenDeTenant,
    ClaveInvalida,
    ObjetoNoEncontrado,
)

from .soporte import reponer_entorno_de_s3

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def entorno_de_minio(monkeypatch: pytest.MonkeyPatch) -> None:
    """`entorno_limpio` borra todo `S3_*` antes de cada test; acá se repone.

    `autouse` porque acordarse de pedirlo es el error que produciria un fallo
    ilegible: sin credenciales, `Settings` no valida y el mensaje habla de
    variables de entorno en un test que dice llamarse "borrar saca el objeto".
    """
    reponer_entorno_de_s3(monkeypatch)


@pytest.fixture
def almacen(tenant: uuid.UUID) -> AlmacenDeTenant:
    return AlmacenDeTenant(tenant)


@pytest.fixture
def relativa() -> str:
    """Una clave distinta por test: el bucket es compartido y persiste."""
    return f"vehiculos/{uuid.uuid4().hex}/frente.jpg"


# ── La forma de la clave ─────────────────────────────────────────────────────


def test_la_clave_queda_bajo_el_prefijo_del_tenant(
    almacen: AlmacenDeTenant, tenant: uuid.UUID
) -> None:
    assert almacen.clave_absoluta("vehiculos/abc/frente.jpg") == (
        f"{tenant}/vehiculos/abc/frente.jpg"
    )


@pytest.mark.parametrize(
    "intento",
    [
        "../otro/x.jpg",
        "vehiculos/../../otro/x.jpg",
        "..",
        "vehiculos/../x.jpg",
    ],
)
def test_no_se_puede_salir_del_prefijo(almacen: AlmacenDeTenant, intento: str) -> None:
    """EL ATAQUE. Es la unica forma de tocar el almacen de otra agencia.

    En PostgreSQL esto lo corta la politica RLS aunque el codigo se equivoque. En
    S3 no hay politica: la clave es una cadena y el bucket la acepta. Si el
    adapter dejara pasar un `..`, un llamador podria leer y sobrescribir los
    archivos de cualquier tenant, y nada del otro lado lo notaria.
    """
    with pytest.raises(ClaveInvalida):
        almacen.clave_absoluta(intento)


@pytest.mark.parametrize(
    "intento",
    [
        "",
        "/absoluta/x.jpg",
        "vehiculos//x.jpg",
        "vehiculos\\otro\\x.jpg",
        "vehiculos/ x.jpg",
        "vehiculos/x?y.jpg",
    ],
)
def test_las_claves_mal_formadas_se_rechazan(almacen: AlmacenDeTenant, intento: str) -> None:
    """Lista blanca y no lista negra.

    Prohibir `..` y nada mas dejaria pasar la barra invertida —que Windows y
    algunos clientes normalizan a `/`— y los segmentos vacios, que producen
    claves con `//` que despues no coinciden con lo que se guardo.
    """
    with pytest.raises(ClaveInvalida):
        almacen.clave_absoluta(intento)


async def test_un_tenant_no_puede_leer_el_objeto_de_otro(
    tenant: uuid.UUID, otro_tenant: uuid.UUID, relativa: str
) -> None:
    """El aislamiento, ejercido contra el bucket de verdad.

    Los dos usan LA MISMA clave relativa. Si el prefijo no se aplicara, el
    segundo leeria el archivo del primero — y como la clave relativa suele salir
    de un id de vehiculo, dos agencias con el mismo dato la compartirian.
    """
    primero = AlmacenDeTenant(tenant)
    segundo = AlmacenDeTenant(otro_tenant)

    await primero.guardar(relativa, b"la foto del primero", tipo="image/jpeg")

    with pytest.raises(ObjetoNoEncontrado):
        await segundo.leer(relativa)

    # Y el del primero sigue intacto: el segundo no lo piso ni lo borro.
    assert await primero.leer(relativa) == b"la foto del primero"


# ── Ida y vuelta ─────────────────────────────────────────────────────────────


async def test_lo_que_se_guarda_es_lo_que_se_lee(almacen: AlmacenDeTenant, relativa: str) -> None:
    contenido = b"\x89PNG\r\n\x1a\n" + b"bytes binarios, no texto"

    clave = await almacen.guardar(relativa, contenido, tipo="image/png")

    assert clave.startswith(almacen.prefijo)
    assert await almacen.leer(relativa) == contenido


async def test_leer_lo_que_no_esta_levanta_y_no_devuelve_vacio(
    almacen: AlmacenDeTenant, relativa: str
) -> None:
    """`b""` y "no existe" son cosas distintas.

    Un objeto vacio es legitimo —una foto de cero bytes es un archivo roto que
    igual hay que poder detectar— asi que aplanar el faltante a `b""` haria
    indistinguibles los dos casos.
    """
    with pytest.raises(ObjetoNoEncontrado):
        await almacen.leer(relativa)


async def test_el_mensaje_del_faltante_no_lleva_el_tenant(
    almacen: AlmacenDeTenant, relativa: str, tenant: uuid.UUID
) -> None:
    """Este texto termina en un log, y la clave absoluta lleva el tenant adentro.

    Mismo criterio que `VehiculoDuplicado`, que no repite el dominio.
    """
    with pytest.raises(ObjetoNoEncontrado) as capturado:
        await almacen.leer(relativa)

    assert str(tenant) not in str(capturado.value)


async def test_borrar_saca_el_objeto(almacen: AlmacenDeTenant, relativa: str) -> None:
    await almacen.guardar(relativa, b"efimero", tipo="text/plain")

    await almacen.borrar(relativa)

    with pytest.raises(ObjetoNoEncontrado):
        await almacen.leer(relativa)


async def test_borrar_dos_veces_no_rompe(almacen: AlmacenDeTenant, relativa: str) -> None:
    """S3 no distingue "no estaba" de "lo borre", y se deja asi.

    Consultar antes para dar un error seria un viaje de red mas y una carrera:
    entre la consulta y el borrado otro proceso puede haberlo sacado.
    """
    await almacen.guardar(relativa, b"efimero", tipo="text/plain")

    await almacen.borrar(relativa)
    await almacen.borrar(relativa)


async def test_borrar_no_alcanza_al_objeto_de_otro(
    tenant: uuid.UUID, otro_tenant: uuid.UUID, relativa: str
) -> None:
    """La mitad destructiva del aislamiento, que es la que no se puede deshacer.

    Leer de mas es una fuga; borrar de mas es una perdida. El segundo caso merece
    su propio test porque `borrar` es idempotente y **no falla** cuando la clave
    no existe: sin esto, un prefijo mal aplicado se veria exactamente igual que
    un borrado exitoso.
    """
    primero = AlmacenDeTenant(tenant)
    segundo = AlmacenDeTenant(otro_tenant)
    await primero.guardar(relativa, b"la foto del primero", tipo="image/jpeg")

    await segundo.borrar(relativa)

    assert await primero.leer(relativa) == b"la foto del primero"


# ── URLs firmadas — `DD-08` ──────────────────────────────────────────────────


async def test_la_url_firmada_sirve_para_bajar_el_objeto(
    almacen: AlmacenDeTenant, relativa: str
) -> None:
    """Se ejerce la URL de verdad, no se le mira la forma.

    Verificar que "tiene `X-Amz-Signature`" pasaria en verde con una firma
    invalida — que es justo lo que produce negociar la version equivocada contra
    MinIO, y el sintoma seria un 403 recien en el navegador.
    """
    await almacen.guardar(relativa, b"contenido firmado", tipo="text/plain")

    url = almacen.url_firmada(relativa)

    async with httpx.AsyncClient() as cliente:
        respuesta = await cliente.get(url)

    assert respuesta.status_code == 200
    assert respuesta.content == b"contenido firmado"


def test_la_url_firmada_lleva_el_prefijo_del_tenant(
    almacen: AlmacenDeTenant, tenant: uuid.UUID
) -> None:
    assert str(tenant) in almacen.url_firmada("vehiculos/abc/frente.jpg")


def test_no_se_puede_firmar_una_clave_de_otro(almacen: AlmacenDeTenant) -> None:
    """Firmar es la operacion mas peligrosa: produce un permiso que viaja solo.

    Una URL firmada la usa cualquiera que la tenga, sin token y sin sesion. Si
    aceptara una clave con `..`, el resultado seria un permiso de lectura sobre
    el archivo de otra agencia, valido por minutos y sin nada que lo revoque.
    """
    with pytest.raises(ClaveInvalida):
        almacen.url_firmada("../otro/x.jpg")


def test_los_dos_ttl_son_los_del_corpus() -> None:
    """`DD-08`: 5 minutos para fotos, 30 para documentos.

    Se fija el numero porque es una decision del corpus y no una preferencia.
    Alargar el de la foto a una hora "porque tarda en cargar" es la clase de
    cambio que se hace sin pensar y no lo detiene ningun otro test.
    """
    assert TTL_DE_FOTO == 300
    assert TTL_DE_DOCUMENTO == 1800


# ── Los caminos de error ─────────────────────────────────────────────────────


async def test_un_objeto_mas_grande_que_el_tope_se_rechaza_antes_de_subirlo(
    almacen: AlmacenDeTenant, relativa: str
) -> None:
    """El limite se verifica ANTES del viaje de red, no despues.

    Por encima de este tamaño `put_object` deja de ser lo correcto y hay que
    subir en partes. Descubrirlo como un timeout —que es lo que pasa sin esta
    verificacion— manda a buscar el problema en la red.
    """
    with pytest.raises(ValueError, match="tope"):
        await almacen.guardar(relativa, b"x" * (TOPE_DE_SUBIDA_BYTES + 1), tipo="text/plain")


async def test_un_error_de_s3_que_no_es_un_faltante_se_propaga(
    almacen: AlmacenDeTenant, relativa: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un bucket inexistente NO es `ObjetoNoEncontrado`.

    Aplanar todo `ClientError` a "no esta" convertiria un bucket mal configurado
    —o unas credenciales revocadas— en "esa foto no existe", y nadie iria a mirar
    la configuracion de S3 por un objeto faltante.
    """
    monkeypatch.setenv("S3_BUCKET", f"bucket-que-no-existe-{uuid.uuid4().hex[:12]}")

    from app.config import get_settings

    get_settings.cache_clear()

    with pytest.raises(ClientError):
        await almacen.leer(relativa)
