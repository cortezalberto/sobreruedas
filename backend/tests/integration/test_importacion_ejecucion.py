"""La importacion corriendo de punta a punta — C-17, `T-094`.

QUE SE EJERCITA Y QUE NO
─────────────────────────
Se llama a `ejecutar_importacion()` **directamente**, con `await`, sin worker de
Celery en el medio. Lo que la tarea agrega sobre esta funcion son dos lineas
—el `asyncio.run()` y el reintento— y se prueban aparte, en
`tests/unit/test_tarea_de_importacion.py`.

Todo lo demas es de verdad: PostgreSQL con RLS, Redis con la planilla, los lotes
con commit propio y los SAVEPOINTs por fila.

LA AFIRMACION QUE MAS IMPORTA
───────────────────────────────
**Una fila mala no se lleva puestas a las buenas.** Es lo que separa este flujo
de "subi el Excel y me dijo que algo fallo": si una violacion de constraint
abortara la transaccion del lote, las 99 filas correctas se perderian y el
reporte por fila describiria trabajo deshecho.

Sin mocks de base de datos (regla dura 8).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import pytest
from redis.asyncio import Redis
from sqlalchemy import func, select, text

from app.db.session import sesion_de_tenant
from app.modules.stock.historial import HistorialRepository
from app.modules.stock.importacion_modelo import EstadoDeImportacion, Import
from app.modules.stock.importacion_servicio import (
    ImportacionNoEncontrada,
    ImportService,
    ejecutar_importacion,
)
from app.modules.stock.models import Vehicle
from app.modules.stock.schemas import EstadoDeVehiculo

from .soporte import (
    DSN_APLICACION,
    URL_REDIS,
    agencia_con_sucursal,
    reponer_entorno,
    sesion_de_propietario,
)

pytestmark = pytest.mark.integration

CABECERA = (
    "marca,modelo,anio,kilometros,color,combustible,transmision,"
    "carroceria,precio_ars,dominio,chasis,sucursal"
)


@pytest.fixture(autouse=True)
def _entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    """El worker NO recibe un DSN: lo saca de `Settings`, igual que en produccion.

    Por eso acá se repone el entorno en vez de parchear `_redis` o pasar `dsn=`
    por todos lados. Parchear haria pasar el test sin ejercitar el camino real
    —el `sesion_de_tenant(tenant_id)` sin argumentos que usa la tarea— que es
    justamente donde una configuracion mal leida se nota.
    """
    reponer_entorno(monkeypatch, dsn=DSN_APLICACION)


@pytest.fixture
async def agencia(base_migrada: None) -> tuple[uuid.UUID, str, str]:
    """Una agencia con una sucursal, y una marca/modelo REALES del catalogo.

    Devuelve los NOMBRES de marca y modelo, no sus ids: es lo que va en la
    planilla, que la llena una persona.
    """
    tenant_id, _ = await agencia_con_sucursal()
    async with sesion_de_propietario() as sesion:
        marca, modelo = (
            await sesion.execute(
                text(
                    "SELECT b.name, m.name FROM vehicle_models m "
                    "JOIN vehicle_brands b ON b.id = m.brand_id ORDER BY m.name LIMIT 1"
                )
            )
        ).one()
    return tenant_id, str(marca), str(modelo)


class Planilla:
    """Arma el CSV de prueba. Clase, y no una funcion con atributos colgados.

    El primer intento fue `armar.fila = lambda ...`: andaba, y obligaba a un
    `type: ignore` en cada uso porque mypy no sabe de atributos inventados sobre
    una funcion. Una clase dice lo mismo sin pelearse con el verificador.
    """

    def __init__(self, marca: str, modelo: str) -> None:
        self._marca = marca
        self._modelo = modelo

    def fila(self, dominio: str, **cambios: str) -> str:
        return ",".join(
            [
                cambios.get("marca", self._marca),
                cambios.get("modelo", self._modelo),
                cambios.get("anio", "2021"),
                cambios.get("kilometros", "40000"),
                cambios.get("color", "Blanco"),
                cambios.get("combustible", "diesel"),
                cambios.get("transmision", "manual"),
                cambios.get("carroceria", "pickup"),
                cambios.get("precio_ars", "25000000.00"),
                dominio,
                cambios.get("chasis", ""),
                cambios.get("sucursal", ""),
            ]
        )

    def csv(self, *filas: str) -> bytes:
        return ("\r\n".join([CABECERA, *filas]) + "\r\n").encode("utf-8")


@pytest.fixture
def planilla(agencia: tuple[uuid.UUID, str, str]) -> Planilla:
    _, marca, modelo = agencia
    return Planilla(marca, modelo)


@pytest.fixture
def correr(agencia: tuple[uuid.UUID, str, str]) -> Callable[[bytes], Awaitable[Import]]:
    """Registra la planilla y la ejecuta, como haria el par endpoint + worker."""
    tenant_id, _, _ = agencia

    async def ejecutar(contenido: bytes) -> Import:
        async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
            corrida = await ImportService(sesion, tenant_id).registrar(
                nombre_archivo="stock.csv", contenido=contenido, creado_por=None
            )
            corrida_id = corrida.id

        await ejecutar_importacion(corrida_id, tenant_id)

        async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
            return await ImportService(sesion, tenant_id).obtener(corrida_id)

    return ejecutar


async def _vehiculos(tenant_id: uuid.UUID) -> int:
    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        total = (
            await sesion.execute(
                select(func.count()).select_from(Vehicle).where(Vehicle.deleted_at.is_(None))
            )
        ).scalar_one()
    return int(total)


# ── Camino feliz ────────────────────────────────────────────────────────────


async def test_una_planilla_valida_crea_los_vehiculos(
    agencia: tuple[uuid.UUID, str, str],
    planilla: Planilla,
    correr: Callable[[bytes], Awaitable[Import]],
) -> None:
    tenant_id, _, _ = agencia

    corrida = await correr(
        planilla.csv(planilla.fila("AD100AA"), planilla.fila("AD200AA"), planilla.fila("AD300AA"))
    )

    assert corrida.status == EstadoDeImportacion.COMPLETADA.value
    assert (corrida.total_rows, corrida.valid_rows, corrida.error_rows) == (3, 3, 0)
    assert corrida.completed_at is not None
    assert await _vehiculos(tenant_id) == 3


async def test_la_sucursal_se_deduce_cuando_la_agencia_tiene_una_sola(
    agencia: tuple[uuid.UUID, str, str],
    planilla: Planilla,
    correr: Callable[[bytes], Awaitable[Import]],
) -> None:
    """La columna va vacia en todas las filas y aun asi entran.

    Obligar a repetir "Casa central" en 500 filas es pedir un dato que el
    sistema ya sabe.
    """
    tenant_id, _, _ = agencia

    await correr(planilla.csv(planilla.fila("AD400AA")))

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        vehiculo = (await sesion.execute(select(Vehicle))).scalars().one()

    assert vehiculo.branch_id is not None


# ── Lo que separa esto de "algo fallo" ──────────────────────────────────────


async def test_una_fila_mala_no_se_lleva_puestas_a_las_buenas(
    agencia: tuple[uuid.UUID, str, str],
    planilla: Planilla,
    correr: Callable[[bytes], Awaitable[Import]],
) -> None:
    """El dominio repetido viola un UNIQUE y aborta la transaccion en PostgreSQL.

    Sin el SAVEPOINT por fila, las buenas del lote se irian con ella — y el
    reporte diria "2 creados" describiendo trabajo que se deshizo.
    """
    tenant_id, _, _ = agencia

    corrida = await correr(
        planilla.csv(
            planilla.fila("AD500AA"),
            planilla.fila("AD500AA"),  # repetida a proposito
            planilla.fila("AD600AA"),
        )
    )

    assert corrida.valid_rows == 2
    assert corrida.error_rows == 1
    assert await _vehiculos(tenant_id) == 2


async def test_el_error_de_una_fila_no_repite_el_dominio(
    planilla: Planilla, correr: Callable[[bytes], Awaitable[Import]]
) -> None:
    """Ley 25.326: el texto termina en la fila de `imports` y en el log."""
    corrida = await correr(planilla.csv(planilla.fila("AD700AA"), planilla.fila("AD700AA")))

    assert "AD700AA" not in corrida.errors[0]["mensaje"]


async def test_una_marca_que_no_esta_en_el_catalogo_es_error_de_fila(
    planilla: Planilla, correr: Callable[[bytes], Awaitable[Import]]
) -> None:
    corrida = await correr(
        planilla.csv(planilla.fila("AD800AA"), planilla.fila("AD900AA", marca="Delorean"))
    )

    assert corrida.valid_rows == 1
    assert corrida.errors[0]["columna"] == "marca"


async def test_un_modelo_que_no_es_de_esa_marca_es_error_de_fila(
    planilla: Planilla, correr: Callable[[bytes], Awaitable[Import]]
) -> None:
    """Sin la clave compuesta `(marca, modelo)` esto entraria, y el vehiculo
    quedaria con un `model_id` que no cuelga de su `brand_id`."""
    corrida = await correr(planilla.csv(planilla.fila("AE100AA", modelo="Ninguno")))

    assert corrida.valid_rows == 0
    assert corrida.errors[0]["columna"] == "modelo"


async def test_una_sucursal_que_no_existe_es_error_de_fila(
    planilla: Planilla, correr: Callable[[bytes], Awaitable[Import]]
) -> None:
    corrida = await correr(planilla.csv(planilla.fila("AE150AA", sucursal="Sucursal Fantasma")))

    assert corrida.errors[0]["columna"] == "sucursal"


async def test_un_error_de_parseo_se_reporta_con_su_numero_de_fila(
    planilla: Planilla, correr: Callable[[bytes], Awaitable[Import]]
) -> None:
    """El que viene del lector, no del INSERT. Los dos van al mismo reporte."""
    corrida = await correr(
        planilla.csv(planilla.fila("AE200AA"), planilla.fila("AE300AA", anio="mil novecientos"))
    )

    assert corrida.total_rows == 2
    assert corrida.valid_rows == 1
    assert corrida.errors[0]["fila"] == 3


# ── Aislamiento y limpieza ──────────────────────────────────────────────────


async def test_los_vehiculos_nacen_en_la_agencia_de_la_corrida(
    agencia: tuple[uuid.UUID, str, str],
    planilla: Planilla,
    correr: Callable[[bytes], Awaitable[Import]],
) -> None:
    """El tenant sale de la fila de `imports`, no de la planilla.

    Una planilla no tiene columna para elegir agencia, y esta es la afirmacion
    que lo prueba desde el otro lado.
    """
    tenant_id, _, _ = agencia

    await correr(planilla.csv(planilla.fila("AE400AA")))

    async with sesion_de_tenant(uuid.uuid4(), dsn=DSN_APLICACION) as sesion:
        ajenos = (await sesion.execute(select(Vehicle))).scalars().all()

    assert ajenos == []
    assert await _vehiculos(tenant_id) == 1


async def test_la_planilla_se_borra_de_redis_al_terminar(
    agencia: tuple[uuid.UUID, str, str],
    planilla: Planilla,
    correr: Callable[[bytes], Awaitable[Import]],
) -> None:
    """10 MB por importacion que nadie borra llenan un Redis en una tarde."""
    tenant_id, _, _ = agencia

    corrida = await correr(planilla.csv(planilla.fila("AE500AA")))

    cliente: Redis = Redis.from_url(URL_REDIS, decode_responses=False)
    try:
        assert await cliente.get(f"import:{tenant_id}:{corrida.id}") is None
    finally:
        await cliente.aclose()


# ── Fallas que dejan la corrida en `failed`, y no clavada ───────────────────


async def test_si_el_archivo_ya_no_esta_la_corrida_falla_con_motivo(
    agencia: tuple[uuid.UUID, str, str], planilla: Planilla
) -> None:
    """El TTL vencio o alguien limpio Redis. No puede quedar en `pending`."""
    tenant_id, _, _ = agencia

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        corrida = await ImportService(sesion, tenant_id).registrar(
            nombre_archivo="stock.csv",
            contenido=planilla.csv(planilla.fila("AE600AA")),
            creado_por=None,
        )
        corrida_id = corrida.id

    cliente: Redis = Redis.from_url(URL_REDIS, decode_responses=False)
    try:
        await cliente.delete(f"import:{tenant_id}:{corrida_id}")
    finally:
        await cliente.aclose()

    await ejecutar_importacion(corrida_id, tenant_id)

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        final = await ImportService(sesion, tenant_id).obtener(corrida_id)

    assert final.status == EstadoDeImportacion.FALLIDA.value
    assert final.failure_reason is not None


async def test_una_corrida_que_todavia_no_se_ve_devuelve_falso_y_no_borra_nada(
    base_migrada: None,
) -> None:
    """Es la carrera del endpoint: encola antes de que su transaccion cierre.

    Devolver `False` es lo que hace que la tarea reintente en vez de dar la
    corrida por perdida. Y NO tiene que borrar el archivo de Redis — el
    reintento lo necesita, y sin el fallaria con "el archivo ya no esta
    disponible" en vez de importar.
    """
    tenant_id, corrida_id = uuid.uuid4(), uuid.uuid4()
    cliente: Redis = Redis.from_url(URL_REDIS, decode_responses=False)
    try:
        await cliente.set(f"import:{tenant_id}:{corrida_id}", b"lo que sea", ex=60)

        encontrada = await ejecutar_importacion(corrida_id, tenant_id)

        assert encontrada is False
        assert await cliente.get(f"import:{tenant_id}:{corrida_id}") is not None
    finally:
        await cliente.delete(f"import:{tenant_id}:{corrida_id}")
        await cliente.aclose()


async def test_la_cuota_del_plan_se_verifica_contra_el_total_y_no_fila_por_fila(
    base_migrada: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`RN-ST-13`. Con 3 filas y un plan de 2, NO entran 2 y fallan 1.

    Falla la corrida entera con el motivo. Preguntando de a una, una agencia con
    78 de 80 sube 500 vehiculos, entran 2, y las otras 498 salen como errores
    individuales: un reporte de 498 lineas para un problema que es uno solo — y
    que ademas no es de los datos, sino del plan.

    El plan se crea a medida y se BORRA al final: `plans` es catalogo global sin
    `tenant_id` ni RLS, y dejarlo tirado rompe a los cuatro tests que afirman
    que el catalogo tiene exactamente los tres sembrados.
    """
    reponer_entorno(monkeypatch, dsn=DSN_APLICACION)
    plan_id = uuid.uuid4()
    codigo = f"prueba-{plan_id.hex[:8]}"

    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO plans (id, code, name, price_ars, max_users, max_vehicles, "
                "max_branches, max_whatsapp_messages_month, modules) "
                "VALUES (:id, :c, 'De prueba', 1000, 5, 2, 5, 100, '[]'::jsonb)"
            ),
            {"id": plan_id, "c": codigo},
        )
        marca, modelo = (
            await sesion.execute(
                text(
                    "SELECT b.name, m.name FROM vehicle_models m "
                    "JOIN vehicle_brands b ON b.id = m.brand_id ORDER BY m.name LIMIT 1"
                )
            )
        ).one()

    tenant_id, _ = await agencia_con_sucursal(plan=codigo)

    try:
        armador = Planilla(str(marca), str(modelo))
        contenido = armador.csv(
            armador.fila("AF100AA"), armador.fila("AF200AA"), armador.fila("AF300AA")
        )

        async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
            corrida = await ImportService(sesion, tenant_id).registrar(
                nombre_archivo="stock.csv", contenido=contenido, creado_por=None
            )
            corrida_id = corrida.id

        await ejecutar_importacion(corrida_id, tenant_id)

        async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
            final = await ImportService(sesion, tenant_id).obtener(corrida_id)

        assert final.status == EstadoDeImportacion.FALLIDA.value
        assert final.failure_reason is not None
        assert await _vehiculos(tenant_id) == 0
    finally:
        async with sesion_de_propietario() as sesion:
            # `imports` tambien apunta a `tenants`. Va PRIMERO por eso: la FK
            # no la contempla `ON DELETE`, asi que el orden es la unica garantia.
            await sesion.execute(text("DELETE FROM imports WHERE tenant_id = :t"), {"t": tenant_id})
            # `vehicle_status_history` (C-14) tiene FK `RESTRICT` a `vehicles`:
            # cada alta deja su fila genesis, asi que borrar el vehiculo antes
            # que su historial rompe con `ForeignKeyViolationError`.
            await sesion.execute(
                text("DELETE FROM vehicle_status_history WHERE tenant_id = :t"), {"t": tenant_id}
            )
            await sesion.execute(
                text("DELETE FROM vehicles WHERE tenant_id = :t"), {"t": tenant_id}
            )
            await sesion.execute(
                text("DELETE FROM branches WHERE tenant_id = :t"), {"t": tenant_id}
            )
            await sesion.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": tenant_id})
            await sesion.execute(text("DELETE FROM plans WHERE id = :p"), {"p": plan_id})


# ── Las ramas defensivas, y el servicio sin HTTP ────────────────────────────


async def test_una_fila_que_el_lector_acepta_y_el_schema_rechaza_es_error_de_fila(
    planilla: Planilla, correr: Callable[[bytes], Awaitable[Import]]
) -> None:
    """Los dos validadores no son el mismo, y el hueco entre ellos existe.

    `-5000` es un entero perfectamente valido para el lector; `VehiculoCrear`
    lo rechaza con `ge=0`. Sin el `except ValidationError` de `_insertar`, esa
    fila voltearia la importacion entera en vez de reportarse sola.

    Y el error tiene que nombrar la columna del CSV —`kilometros`— y no el campo
    del schema —`mileage_km`—, que es una columna que la planilla no tiene.
    """
    corrida = await correr(
        planilla.csv(planilla.fila("AF400AA"), planilla.fila("AF500AA", kilometros="-5000"))
    )

    assert corrida.valid_rows == 1
    assert corrida.errors[0]["columna"] == "kilometros"


async def test_con_varias_sucursales_hay_que_decir_cual(
    agencia: tuple[uuid.UUID, str, str],
    planilla: Planilla,
    correr: Callable[[bytes], Awaitable[Import]],
) -> None:
    """Con una sola se deduce; con dos, adivinar seria peor que preguntar."""
    tenant_id, _, _ = agencia
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO branches (id, tenant_id, name, city, province) "
                "VALUES (:id, :t, 'Sucursal Norte', 'Las Heras', 'Mendoza')"
            ),
            {"id": uuid.uuid4(), "t": tenant_id},
        )

    corrida = await correr(
        planilla.csv(
            planilla.fila("AF600AA"),  # sin sucursal: no se puede deducir
            planilla.fila("AF700AA", sucursal="Sucursal Norte"),
        )
    )

    assert corrida.valid_rows == 1
    assert corrida.errors[0]["columna"] == "sucursal"


async def test_la_sucursal_nombrada_se_resuelve_sin_importar_mayusculas(
    planilla: Planilla, correr: Callable[[bytes], Awaitable[Import]]
) -> None:
    """`CASA CENTRAL` y ` Casa  central ` son la misma para quien llena la
    planilla. Rechazar por el case seria correcto y ridiculo."""
    corrida = await correr(planilla.csv(planilla.fila("AF800AA", sucursal="  CASA   CENTRAL  ")))

    assert corrida.valid_rows == 1
    assert corrida.errors == []


async def test_si_la_corrida_desaparece_a_mitad_el_worker_no_revienta(
    agencia: tuple[uuid.UUID, str, str], planilla: Planilla
) -> None:
    """La rama defensiva de `_actualizar`, que antes estaba repetida cinco veces
    y ninguna probada.

    Sin el guard, el worker levanta `AttributeError` sobre `None` y la tarea
    muere sin dejar nada escrito — el peor final posible para un trabajo en
    background, porque no hay a quien preguntarle que paso.
    """
    tenant_id, _, _ = agencia

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        corrida = await ImportService(sesion, tenant_id).registrar(
            nombre_archivo="stock.csv",
            contenido=planilla.csv(planilla.fila("AF900AA")),
            creado_por=None,
        )
        corrida_id = corrida.id

    async with sesion_de_propietario() as sesion:
        await sesion.execute(text("DELETE FROM imports WHERE id = :id"), {"id": corrida_id})

    # No levanta. Devuelve `False` —la fila no esta— y no deja basura.
    assert await ejecutar_importacion(corrida_id, tenant_id) is False


async def test_un_fallo_inesperado_deja_la_corrida_en_failed(
    agencia: tuple[uuid.UUID, str, str], planilla: Planilla, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El `except Exception` de `ejecutar_importacion`, que parece paranoia.

    No lo es: si una excepcion sube a Celery, la corrida queda clavada en el
    ultimo estado que alcanzo a escribir y el frontend hace polling para
    siempre. Un trabajo en background sin final visible es peor que uno que
    falla.
    """
    tenant_id, _, _ = agencia

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        corrida = await ImportService(sesion, tenant_id).registrar(
            nombre_archivo="stock.csv",
            contenido=planilla.csv(planilla.fila("AG100AA")),
            creado_por=None,
        )
        corrida_id = corrida.id

    from app.modules.stock import importacion_servicio

    def reventar(*_: object, **__: object) -> None:
        raise RuntimeError("el catalogo se cayo")

    monkeypatch.setattr(importacion_servicio, "_catalogo", reventar)

    assert await ejecutar_importacion(corrida_id, tenant_id) is True

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        final = await ImportService(sesion, tenant_id).obtener(corrida_id)

    assert final.status == EstadoDeImportacion.FALLIDA.value
    assert "el catalogo se cayo" in (final.failure_reason or "")


async def test_el_servicio_no_encuentra_una_corrida_ajena(
    agencia: tuple[uuid.UUID, str, str], planilla: Planilla
) -> None:
    """Sin pasar por HTTP: es el `raise` que el router traduce a 404.

    Va acá y no solo en el test del router porque el codigo que corre dentro
    del portal de `TestClient` no lo traza coverage — probado por HTTP y
    figurando como muerto, que es como se esconde lo que de verdad falta.
    """
    tenant_id, _, _ = agencia

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        servicio = ImportService(sesion, tenant_id)
        corrida = await servicio.registrar(
            nombre_archivo="stock.csv",
            contenido=planilla.csv(planilla.fila("AG200AA")),
            creado_por=None,
        )

        assert (await servicio.obtener(corrida.id)).id == corrida.id
        assert [c.id for c in await servicio.listar()] == [corrida.id]

        with pytest.raises(ImportacionNoEncontrada):
            await servicio.obtener(uuid.uuid4())


async def test_un_archivo_que_se_rompio_en_el_camino_deja_la_corrida_en_failed(
    agencia: tuple[uuid.UUID, str, str], planilla: Planilla
) -> None:
    """La segunda red del lector, dentro del worker.

    `registrar()` ya rechaza los archivos ilegibles dentro del request, asi que
    esta rama parece muerta. No lo es: entre el POST y la tarea, el contenido
    viaja por Redis y puede haberlo dejado ahi una version anterior del lector.
    Se simula reemplazando lo guardado.

    Lo que importa es el final: **failed con motivo**, y no el worker
    reventando con un `ArchivoIlegible` que deja la corrida clavada en
    `parsing`.
    """
    tenant_id, _, _ = agencia

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        corrida = await ImportService(sesion, tenant_id).registrar(
            nombre_archivo="stock.csv",
            contenido=planilla.csv(planilla.fila("AG300AA")),
            creado_por=None,
        )
        corrida_id = corrida.id

    cliente: Redis = Redis.from_url(URL_REDIS, decode_responses=False)
    try:
        await cliente.set(f"import:{tenant_id}:{corrida_id}", b"una,dos\r\n1,2\r\n", ex=60)
    finally:
        await cliente.aclose()

    assert await ejecutar_importacion(corrida_id, tenant_id) is True

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        final = await ImportService(sesion, tenant_id).obtener(corrida_id)

    assert final.status == EstadoDeImportacion.FALLIDA.value
    assert "columnas" in (final.failure_reason or "")


async def test_actualizar_una_corrida_que_ya_no_esta_no_hace_nada(base_migrada: None) -> None:
    """El guard de `_actualizar`, llamado derecho.

    Llegar acá por el camino normal exige que la fila desaparezca ENTRE dos
    fases de la misma corrida, que es una carrera real y muy poco probable.
    Probar la funcion directamente afirma lo mismo sin montar la carrera.
    """
    from app.modules.stock.importacion_servicio import _actualizar

    await _actualizar(uuid.uuid4(), uuid.uuid4(), status="completed")


# ── C-14 · La fila genesis (`design.md` D-4) ─────────────────────────────────
#
# `importacion_servicio.py:319` construye `Vehicle(...)` directo, sin pasar
# por `StockService.crear`. Sin tocar este archivo, los vehiculos importados
# -la via de alta masiva, hasta 5.000 por corrida (RN-ST-13)- entrarian sin
# fila de historial, y una auditoria append-only con agujeros es peor que no
# tenerla: se consulta creyendole.


async def test_los_vehiculos_importados_tienen_fila_genesis(
    agencia: tuple[uuid.UUID, str, str],
    planilla: Planilla,
    correr: Callable[[bytes], Awaitable[Import]],
) -> None:
    tenant_id, _, _ = agencia

    await correr(planilla.csv(planilla.fila("AE100AA"), planilla.fila("AE200AA")))

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        vehiculos = (await sesion.execute(select(Vehicle))).scalars().all()
        assert len(vehiculos) == 2
        historial = HistorialRepository(sesion, tenant_id)
        for vehiculo in vehiculos:
            filas = await historial.listar_historial(vehiculo.id)
            assert len(filas) == 1, f"vehiculo {vehiculo.id} sin fila genesis"
            assert filas[0].from_status is None
            assert filas[0].to_status == EstadoDeVehiculo.EN_PREPARACION.value


async def test_la_fila_genesis_de_la_importacion_es_null_cuando_no_se_conoce_el_usuario(
    agencia: tuple[uuid.UUID, str, str],
    planilla: Planilla,
    correr: Callable[[bytes], Awaitable[Import]],
) -> None:
    """`correr` registra con `creado_por=None`: el procesamiento ocurre en un
    worker de Celery donde el sujeto ya no esta en contexto."""
    tenant_id, _, _ = agencia

    await correr(planilla.csv(planilla.fila("AE400AA")))

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        vehiculo = (await sesion.execute(select(Vehicle))).scalars().one()
        (fila,) = await HistorialRepository(sesion, tenant_id).listar_historial(vehiculo.id)

    assert fila.changed_by is None


async def test_la_fila_genesis_de_la_importacion_lleva_el_usuario_que_la_lanzo(
    agencia: tuple[uuid.UUID, str, str],
    planilla: Planilla,
) -> None:
    """Contrapeso del anterior: `changed_by` es el usuario de la corrida
    CUANDO la corrida lo conoce."""
    tenant_id, _, _ = agencia
    lanzador = uuid.uuid4()

    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Lanzadora', 'manager', 'active')"
            ),
            {"id": lanzador, "t": tenant_id, "e": f"{lanzador}@example.com"},
        )

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        corrida = await ImportService(sesion, tenant_id).registrar(
            nombre_archivo="stock.csv",
            contenido=planilla.csv(planilla.fila("AE500AA")),
            creado_por=lanzador,
        )
        corrida_id = corrida.id

    await ejecutar_importacion(corrida_id, tenant_id)

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        vehiculo = (await sesion.execute(select(Vehicle))).scalars().one()
        (fila,) = await HistorialRepository(sesion, tenant_id).listar_historial(vehiculo.id)

    assert fila.changed_by == lanzador
