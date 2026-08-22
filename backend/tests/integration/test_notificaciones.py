"""Notificaciones contra PostgreSQL, Redis y MailHog reales — C-06, `T-035`.

EL TEST QUE EL CHANGE EXIGE es `test_una_notificacion_se_dispara_desde_un_evento_publicado`:
recorre el camino entero —mutacion de stock, outbox, commit, drenaje a Redis,
consumo, notificacion en la base— sin un solo doble. Es el unico que prueba que
las cinco piezas encajan; los demas prueban cada una por separado.

Sin mocks (regla dura 8). Un doble de Redis Streams no tiene consumer groups, y
sin consumer groups no hay nada que probar del consumo.
"""

from __future__ import annotations

import uuid
from functools import partial

import pytest
import sqlalchemy as sa
from redis.asyncio import Redis

from app.core.events import Sobre, consumir, nombre_del_stream, publicar
from app.core.outbox import drenar
from app.db.session import sesion_de_tenant
from app.modules.notifications.consumidor import (
    GRUPO,
    manejador_de_notificaciones,
    registrar_manejador,
    tipos_escuchados,
)
from app.modules.notifications.models import Notification
from app.modules.notifications.plantillas import redactar
from app.modules.notifications.service import NotificationService
from app.modules.stock.schemas import EstadoDeVehiculo, VehiculoCambioDeEstado, VehiculoCrear
from app.modules.stock.service import StockService

from .soporte import DSN_APLICACION, agencia_con_sucursal, sesion_de_propietario

pytestmark = pytest.mark.integration


@pytest.fixture
def manejador() -> object:
    """El manejador con el DSN de los tests ya atado.

    `consumir` invoca al manejador con UN argumento —el sobre—, asi que el `dsn`
    no puede viajar por ahi. `partial` lo fija sin obligar a `core/events.py` a
    conocer un parametro que solo los tests necesitan.
    """
    return partial(manejador_de_notificaciones, dsn=DSN_APLICACION)


# El unico tipo con manejador registrado, y por eso el unico stream compartido
# entre los tests que ejercen el consumo.
TIPO_DE_STOCK = "vehicle.status_changed"


@pytest.fixture
async def stream_limpio(redis: Redis) -> None:
    """Borra el stream de stock ANTES del test, con sus consumer groups.

    NO ES HIGIENE, ES CORRECCION. El Redis de desarrollo persiste entre corridas
    y este stream tiene nombre fijo —lo determina el tipo de evento, no el test—,
    asi que arrastra todo lo que dejaron las corridas anteriores. `consumir` lee
    hasta `max_mensajes` (10 por defecto) empezando por los pendientes: con
    backlog, se los lleva a ellos y **nunca llega al mensaje de este test**.

    Asi fallo la primera version: la notificacion se creaba de verdad —habia diez
    en la base— y el test las contaba en cero, porque el consumidor estaba
    procesando eventos de otro dia.

    Se borra al ENTRAR y no al salir: si un test se cae a mitad de camino, lo que
    dejo tiene que poder mirarse.
    """
    await redis.delete(nombre_del_stream(TIPO_DE_STOCK))


async def _usuario(tenant: uuid.UUID, email: str) -> uuid.UUID:
    """Un usuario del padron, creado con el rol PROPIETARIO.

    Es andamiaje: `users` lo escribe C-05 y acá solo hace falta un destinatario
    con el que la clave foranea sea satisfacible.
    """
    usuario_id = uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            # ⚠️ NO HAY `keycloak_sub`: `users.id` ES el `sub` del token. Es el
            # espejo local de `ADR-026`, vinculado por el identificador de
            # Keycloak y no por una columna aparte.
            sa.text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :tenant, :email, 'Prueba Prueba', 'salesperson', 'active')"
            ),
            {"id": usuario_id, "tenant": tenant, "email": email},
        )
    return usuario_id


# ── Las plantillas ───────────────────────────────────────────────────────────


def test_la_plantilla_arma_titulo_y_cuerpo() -> None:
    titulo, cuerpo = redactar(
        "vehiculo.cambio_de_estado",
        {"identificador": "AB123CD", "desde": "available", "hasta": "reserved"},
    )

    assert titulo == "Un vehiculo tuyo cambio de estado"
    assert cuerpo == "El vehiculo AB123CD paso de available a reserved."


def test_un_tipo_sin_plantilla_no_rompe_el_listado() -> None:
    """Levantar acá tumbaria la pantalla entera por una sola fila.

    Y con la pantalla caida tampoco se verian las notificaciones que SI tienen
    plantilla, que son todas las demas.
    """
    titulo, cuerpo = redactar("inventado.sin_plantilla", {"x": 1})

    assert titulo == "inventado.sin_plantilla"
    assert cuerpo == ""


def test_un_dato_que_falta_deja_un_guion_y_no_levanta() -> None:
    """Una notificacion incompleta se ve; una que levanta, no.

    El payload viene de un evento y los eventos evolucionan: el dia que alguien
    saque una clave, esto tiene que degradar, no romper.
    """
    _, cuerpo = redactar("vehiculo.cambio_de_estado", {"identificador": "AB123CD"})

    assert cuerpo == "El vehiculo AB123CD paso de — a —."


def test_el_payload_no_puede_alcanzar_atributos_del_objeto() -> None:
    """`format_map` deja pasar `{a.__class__}`, y por eso todo se pasa a texto.

    Sobre una cadena, el acceso a atributos no llega a nada util. Sin esto, un
    payload que viniera de afuera podria pasear por el arbol de objetos de Python
    desde una plantilla.
    """
    _, cuerpo = redactar(
        "vehiculo.cambio_de_estado",
        {"identificador": object(), "desde": "a", "hasta": "b"},
    )

    assert "__class__" not in cuerpo
    assert cuerpo.startswith("El vehiculo <object object at")


# ── El servicio ──────────────────────────────────────────────────────────────


async def test_crear_y_listar_sin_leer(base_migrada: None) -> None:
    tenant, _ = await agencia_con_sucursal()
    usuario = await _usuario(tenant, f"{uuid.uuid4().hex}@demo.test")

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = NotificationService(sesion, tenant)
        await servicio.crear(user_id=usuario, tipo="vehiculo.cambio_de_estado", payload={"x": "1"})

        pendientes = await servicio.sin_leer(usuario)

        assert len(pendientes) == 1
        assert pendientes[0].read_at is None


async def test_marcar_leida_la_saca_de_las_pendientes(base_migrada: None) -> None:
    tenant, _ = await agencia_con_sucursal()
    usuario = await _usuario(tenant, f"{uuid.uuid4().hex}@demo.test")

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = NotificationService(sesion, tenant)
        creada = await servicio.crear(user_id=usuario, tipo="vehiculo.cambio_de_estado", payload={})

        assert await servicio.marcar_leida(creada.id, user_id=usuario) is True
        assert await servicio.sin_leer(usuario) == []


async def test_marcar_dos_veces_no_mueve_la_fecha(base_migrada: None) -> None:
    """ "Cuando la vio" es la primera vez, no la ultima."""
    tenant, _ = await agencia_con_sucursal()
    usuario = await _usuario(tenant, f"{uuid.uuid4().hex}@demo.test")

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = NotificationService(sesion, tenant)
        creada = await servicio.crear(user_id=usuario, tipo="vehiculo.cambio_de_estado", payload={})
        await servicio.marcar_leida(creada.id, user_id=usuario)

        assert await servicio.marcar_leida(creada.id, user_id=usuario) is False


async def test_nadie_marca_la_notificacion_de_un_companero(base_migrada: None) -> None:
    """RLS acota por AGENCIA, no por persona — esta condicion la pone el servicio.

    Sin el `user_id` en el WHERE, dos empleados de la misma agencia podrian
    marcarse las notificaciones entre si y la politica lo dejaria pasar sin
    parpadear: para PostgreSQL son filas del mismo tenant.
    """
    tenant, _ = await agencia_con_sucursal()
    destinatario = await _usuario(tenant, f"{uuid.uuid4().hex}@demo.test")
    companero = await _usuario(tenant, f"{uuid.uuid4().hex}@demo.test")

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        servicio = NotificationService(sesion, tenant)
        creada = await servicio.crear(
            user_id=destinatario, tipo="vehiculo.cambio_de_estado", payload={}
        )

        assert await servicio.marcar_leida(creada.id, user_id=companero) is False
        assert len(await servicio.sin_leer(destinatario)) == 1


async def test_una_agencia_no_ve_las_notificaciones_de_otra(base_migrada: None) -> None:
    """La politica RLS de la tabla, ejercida.

    El `payload` lleva datos del hecho que la origino: patentes, estados, y el dia
    de mañana nombres de contactos. Es una tabla mas por la que se filtraria todo.
    """
    tenant, _ = await agencia_con_sucursal()
    otro, _ = await agencia_con_sucursal()
    usuario = await _usuario(tenant, f"{uuid.uuid4().hex}@demo.test")

    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        await NotificationService(sesion, tenant).crear(
            user_id=usuario, tipo="vehiculo.cambio_de_estado", payload={}
        )

    async with sesion_de_tenant(otro, dsn=DSN_APLICACION) as del_otro:
        filas = (await del_otro.execute(sa.select(Notification))).scalars().all()
        assert list(filas) == []


# ── El registro de manejadores ───────────────────────────────────────────────


def test_no_se_puede_pisar_un_manejador_registrado() -> None:
    """Dos modulos peleandose un evento ganaria el que se importe ultimo.

    Y el orden de los imports cambia sin que nadie lo toque, asi que el sintoma
    seria intermitente entre despliegues.
    """

    async def _otro(sobre: Sobre, dsn: str | None = None) -> None:  # pragma: no cover
        return None

    with pytest.raises(ValueError, match="ya tiene manejador"):
        registrar_manejador("vehicle.status_changed", _otro)


def test_el_manejador_de_stock_esta_suscripto() -> None:
    assert "vehicle.status_changed" in tipos_escuchados()


async def test_un_evento_sin_manejador_no_es_un_error(redis: Redis, tenant: uuid.UUID) -> None:
    """Se ignora y se confirma; no va a reintentos ni a irrecuperables.

    Un evento que a nadie le interesa no es un evento fallido, y tratarlo como tal
    llenaria el stream de irrecuperables de hechos perfectamente normales.
    """
    tipo = f"prueba.nadie_escucha_{uuid.uuid4().hex[:8]}"
    await publicar(tipo, tenant_id=tenant, payload={}, cliente=redis)

    resultado = await consumir(
        redis,
        tipo,
        grupo=GRUPO,
        consumidor="test",
        manejador=manejador_de_notificaciones,
        dsn=DSN_APLICACION,
    )

    assert resultado.procesados == 1
    assert resultado.irrecuperables == 0


# ── El camino completo ───────────────────────────────────────────────────────


async def test_una_notificacion_se_dispara_desde_un_evento_publicado(
    base_migrada: None, redis: Redis, manejador: object, stream_limpio: None
) -> None:
    """EL TEST DEL CHANGE. Cinco piezas, ningun doble.

    stock muta -> outbox escribe en la misma transaccion -> commit -> drenaje a
    Redis -> el consumidor lo toma -> aparece la notificacion en la base.

    Cada pieza tiene su propio test. Este es el unico que prueba que ENCAJAN, que
    es una propiedad distinta: los cinco pueden estar bien por separado y fallar
    juntos por un nombre de evento que no coincide.
    """
    tenant, sucursal = await agencia_con_sucursal()
    vendedor = await _usuario(tenant, f"{uuid.uuid4().hex}@demo.test")

    async with sesion_de_propietario() as sesion:
        marca, modelo = (
            await sesion.execute(sa.text("SELECT brand_id, id FROM vehicle_models LIMIT 1"))
        ).one()

    # 1 y 2 — la mutacion y el outbox, en la misma transaccion.
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as sesion:
        sesion.info["tenant_id"] = tenant
        servicio = StockService(sesion, tenant)
        vehiculo = await servicio.crear(
            VehiculoCrear(
                branch_id=sucursal,
                brand_id=uuid.UUID(str(marca)),
                model_id=uuid.UUID(str(modelo)),
                year=2021,
                mileage_km=10_000,
                color="Gris",
                fuel_type="diesel",
                transmission="manual",
                body_type="pickup",
                price_ars="25000000.00",
                domain_plate="AB999CD",
            )
        )
        # El vendedor a cargo: es a quien el manejador va a notificar.
        vehiculo.assigned_user_id = vendedor
        await servicio.cambiar_estado(
            vehiculo.id, VehiculoCambioDeEstado(status=EstadoDeVehiculo.DISPONIBLE)
        )

    # 3 — el drenaje, ya con la transaccion commiteada.
    assert await drenar(sesion, dsn=DSN_APLICACION, cliente=redis) == 2

    # 4 — el consumo.
    resultado = await consumir(
        redis,
        "vehicle.status_changed",
        grupo=GRUPO,
        consumidor="test",
        manejador=manejador,  # type: ignore[arg-type]
        dsn=DSN_APLICACION,
    )
    assert resultado.procesados == 1, "el consumidor no tomo el evento de este test"
    assert resultado.irrecuperables == 0

    # 5 — la notificacion existe, es del vendedor, y dice lo que pasó.
    async with sesion_de_tenant(tenant, dsn=DSN_APLICACION) as verificacion:
        pendientes = await NotificationService(verificacion, tenant).sin_leer(vendedor)

    assert len(pendientes) == 1
    assert pendientes[0].type == "vehiculo.cambio_de_estado"
    assert pendientes[0].payload["identificador"] == "AB999CD"
    assert pendientes[0].payload["desde"] == "in_preparation"
    assert pendientes[0].payload["hasta"] == "available"


async def test_un_vehiculo_sin_asignado_no_notifica_a_nadie(
    base_migrada: None, redis: Redis, manejador: object, stream_limpio: None
) -> None:
    """No hay a quien avisarle, y eso NO es un fallo.

    La mayoria de los vehiculos no tiene vendedor asignado. Si esto levantara, el
    evento iria a cinco reintentos y de ahi a irrecuperables — llenando la cola de
    errores con el caso mas comun del sistema.
    """
    tenant, _ = await agencia_con_sucursal()
    await publicar(
        "vehicle.status_changed",
        tenant_id=tenant,
        payload={"vehicle_id": str(uuid.uuid4()), "from": "available", "to": "reserved"},
        cliente=redis,
    )

    resultado = await consumir(
        redis,
        "vehicle.status_changed",
        grupo=GRUPO,
        consumidor="test",
        manejador=manejador,  # type: ignore[arg-type]
        dsn=DSN_APLICACION,
    )

    assert resultado.procesados == 1
    assert resultado.irrecuperables == 0


# ── El canal de email ────────────────────────────────────────────────────────


async def test_el_mail_usa_la_misma_plantilla_que_la_pantalla(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si divergieran, la campanita y el mail contarian dos historias del mismo hecho."""
    capturado: dict[str, str] = {}

    async def _capturar(destinatario: str, asunto: str, cuerpo: str) -> bool:
        capturado.update(destinatario=destinatario, asunto=asunto, cuerpo=cuerpo)
        return True

    monkeypatch.setattr("app.modules.notifications.correo.enviar", _capturar)
    payload = {"identificador": "AB123CD", "desde": "available", "hasta": "reserved"}

    await NotificationService.avisar_por_mail(
        "quien@demo.test", "vehiculo.cambio_de_estado", payload
    )

    titulo, cuerpo = redactar("vehiculo.cambio_de_estado", payload)
    assert capturado["asunto"] == titulo
    assert capturado["cuerpo"] == cuerpo


async def test_un_smtp_caido_no_levanta(monkeypatch: pytest.MonkeyPatch) -> None:
    """El correo es la copia de cortesia: no puede voltear lo que lo origino.

    Si levantara, un servidor de mail caido haria que `consumir` reintentara el
    evento cinco veces — y cada reintento volveria a intentar el mail, mandando
    cinco copias a todo el que si lo recibe.
    """

    def _explota(*_args: object, **_kwargs: object) -> None:
        raise ConnectionRefusedError("no hay servidor de correo")

    monkeypatch.setattr("app.modules.notifications.correo._enviar_bloqueante", _explota)

    assert await NotificationService.avisar_por_mail("quien@demo.test", "x", {}) is False


async def test_el_mail_sale_de_verdad_a_mailhog(monkeypatch: pytest.MonkeyPatch) -> None:
    """Contra el SMTP real del compose, no contra un doble.

    Un doble confirmaria que se llamo a `send_message`, que es lo unico que este
    codigo hace mal dificilmente. Lo que puede fallar de verdad es el armado del
    mensaje o el `partition` del host con puerto — y eso solo lo dice un servidor.
    """
    from .soporte import reponer_entorno_de_s3

    reponer_entorno_de_s3(monkeypatch)
    monkeypatch.setenv("SMTP_HOST", "mailhog:1025")

    from app.config import get_settings

    get_settings.cache_clear()

    assert await NotificationService.avisar_por_mail(
        "destino@demo.test",
        "vehiculo.cambio_de_estado",
        {"identificador": "AB123CD", "desde": "available", "hasta": "reserved"},
    )


async def test_un_evento_sin_vehicle_id_no_notifica_ni_rompe(
    base_migrada: None, redis: Redis, manejador: object, stream_limpio: None, tenant: uuid.UUID
) -> None:
    """Un payload al que le falta la clave se registra y se sigue.

    Es lo que veria el consumidor si alguien cambiara el payload del evento sin
    tocar el manejador. Levantar lo mandaria a cinco reintentos y a
    irrecuperables; ignorarlo en silencio lo dejaria invisible. Se registra un
    aviso y se confirma el mensaje.
    """
    await publicar(TIPO_DE_STOCK, tenant_id=tenant, payload={"from": "a", "to": "b"}, cliente=redis)

    resultado = await consumir(
        redis,
        TIPO_DE_STOCK,
        grupo=GRUPO,
        consumidor="test",
        manejador=manejador,  # type: ignore[arg-type]
        dsn=DSN_APLICACION,
    )

    assert resultado.procesados == 1
    assert resultado.irrecuperables == 0


class _SmtpDePrueba:
    """Un SMTP que solo anota el orden en que lo usan.

    No simula un servidor de correo —para eso esta mailhog, y hay un test que lo
    usa—. Lo que verifica es NUESTRA secuencia: que `starttls` ocurra antes del
    `login`. Si se invirtiera, la credencial viajaria en claro por la red, y
    ningun servidor de pruebas se quejaria de eso.
    """

    def __init__(self, orden: list[str]) -> None:
        self._orden = orden

    def __enter__(self) -> _SmtpDePrueba:
        return self

    def __exit__(self, *_excepcion: object) -> None:
        return None

    def starttls(self) -> None:
        self._orden.append("starttls")

    def login(self, usuario: str, clave: str) -> None:
        self._orden.append("login")

    def send_message(self, mensaje: object) -> None:
        self._orden.append("send")


async def test_con_credenciales_el_tls_va_antes_del_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`starttls` primero. Al reves, la clave del SMTP sale en claro por el cable.

    Mailhog no ofrece TLS ni pide credencial, asi que este camino —el de
    produccion— no lo ejerce ningun test contra el servidor real.
    """
    from .soporte import reponer_entorno_de_s3

    reponer_entorno_de_s3(monkeypatch)
    monkeypatch.setenv("SMTP_HOST", "servidor:587")
    monkeypatch.setenv("SMTP_USER", "usuario")
    monkeypatch.setenv("SMTP_PASSWORD", "clave")

    from app.config import get_settings

    get_settings.cache_clear()

    orden: list[str] = []
    monkeypatch.setattr(
        "app.modules.notifications.correo.smtplib.SMTP",
        lambda *_a, **_k: _SmtpDePrueba(orden),
    )

    assert await NotificationService.avisar_por_mail("quien@demo.test", "x", {})
    assert orden == ["starttls", "login", "send"]
