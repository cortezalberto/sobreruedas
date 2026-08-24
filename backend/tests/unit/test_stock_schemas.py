"""Los contratos de Stock — C-14 / C-15.

Son schemas sin router todavia, y por eso mismo los tests importan: es lo unico
que hoy los mantiene honestos. Cuando llegue `rbac.py` y se monten los endpoints,
estas afirmaciones ya van a estar fijadas y no habra que rediscutirlas.

Se prueban las REGLAS, no los tipos. Que `year` sea un entero lo garantiza
Pydantic; lo que hay que fijar es que no acepte 2050, que el dominio se
normalice, y que el costo de adquisicion NO pueda salir por el schema comun.
"""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.stock.schemas import (
    TRANSICIONES_PERMITIDAS,
    Carroceria,
    Combustible,
    EstadoDeVehiculo,
    FiltrosDeBusqueda,
    Transmision,
    VehiculoCambioDeEstado,
    VehiculoCrear,
    VehiculoEditar,
    VehiculoSalida,
    VehiculoSalidaConCosto,
    es_transicion_valida,
)

MINIMO = {
    "branch_id": uuid.uuid4(),
    "brand_id": uuid.uuid4(),
    "model_id": uuid.uuid4(),
    "year": 2020,
    "mileage_km": 45_000,
    "color": "Gris",
    "fuel_type": Combustible.NAFTA,
    "transmission": Transmision.MANUAL,
    "body_type": Carroceria.SEDAN,
    "price_ars": Decimal("18500000.00"),
}


def crear(**extra: object) -> VehiculoCrear:
    return VehiculoCrear(**{**MINIMO, **extra})


# ── IN-07: el dominio es opcional, pero algo tiene que identificar al vehiculo ─


def test_un_cero_kilometro_sin_patente_se_puede_cargar() -> None:
    """El caso de negocio que hace que `ADR-031` exista.

    Con `domain_plate NOT NULL` una agencia no podria cargar un 0 km sin
    patentar ni un usado recien recibido en permuta — que es justamente lo que
    el producto tiene que dejar hacer.
    """
    vehiculo = crear(chassis_number="8AWZZZ377VA123456")

    assert vehiculo.domain_plate is None
    assert vehiculo.chassis_number == "8AWZZZ377VA123456"


def test_sin_dominio_y_sin_chasis_se_rechaza() -> None:
    """Un vehiculo sin ninguna forma de identificarse no se distingue de otro."""
    with pytest.raises(ValidationError, match="dominio o el numero de chasis"):
        crear()


def test_alcanza_con_el_dominio() -> None:
    assert crear(domain_plate="AB123CD").chassis_number is None


# ── Normalizacion, por lo mismo que el CUIT en tenancy ──────────────────────


@pytest.mark.parametrize(
    ("escrito", "canonico"),
    [
        ("ab123cd", "AB123CD"),
        ("AB 123 CD", "AB123CD"),
        ("ab-123-cd", "AB123CD"),
        ("aaa999", "AAA999"),
    ],
)
def test_el_dominio_se_normaliza(escrito: str, canonico: str) -> None:
    """El mismo dominio escrito de dos formas no puede producir dos vehiculos.

    Sin normalizar, el `UNIQUE (tenant_id, domain_plate)` no sirve: "AB 123 CD" y
    "ab123cd" son dos cadenas distintas y entran las dos.
    """
    assert crear(domain_plate=escrito).domain_plate == canonico


@pytest.mark.parametrize("invalido", ["ABC12", "A1B2C3", "ABCD1234", "123ABC"])
def test_un_dominio_que_no_es_argentino_se_rechaza(invalido: str) -> None:
    with pytest.raises(ValidationError, match="formato argentino"):
        crear(domain_plate=invalido)


def test_el_mensaje_del_dominio_no_repite_el_valor() -> None:
    """Un dominio identifica a una persona (Ley 25.326) y el mensaje va al log.

    ⚠️ Se afirma sobre `msg` y NO sobre el `str()` de la excepcion. Pydantic
    incluye el valor recibido en `input`, y eso es parte de su contrato — no se
    puede evitar desde acá. Lo que si esta en nuestras manos es el texto que
    escribimos nosotros, que es el que termina en el log de la aplicacion. Es la
    misma distincion que `test_tenancy_schemas.py` documenta para el CUIT.
    """
    with pytest.raises(ValidationError) as fallo:
        crear(domain_plate="ZZZZ9999")

    mensajes = [error["msg"] for error in fallo.value.errors()]
    assert not any("ZZZZ9999" in mensaje for mensaje in mensajes)


@pytest.mark.parametrize("invalido", ["8AWZZZ377VA12345", "8AWZZZ377VA1234I6", "corto"])
def test_un_chasis_mal_formado_se_rechaza(invalido: str) -> None:
    """17 caracteres, sin I, O ni Q — se excluyen para no confundirlas con 1 y 0."""
    with pytest.raises(ValidationError, match="17 caracteres"):
        crear(chassis_number=invalido)


# ── RN-ST-03: rangos ────────────────────────────────────────────────────────


def test_el_anio_maximo_se_calcula_y_no_es_una_constante() -> None:
    """Una constante quedaria vieja el 1 de enero, y el sintoma seria que nadie
    puede cargar el modelo nuevo."""
    proximo = dt.datetime.now(dt.UTC).year + 1

    assert crear(domain_plate="AB123CD", year=proximo).year == proximo
    with pytest.raises(ValidationError, match="no puede ser posterior"):
        crear(domain_plate="AB123CD", year=proximo + 1)


def test_el_precio_tiene_que_ser_positivo() -> None:
    with pytest.raises(ValidationError):
        crear(domain_plate="AB123CD", price_ars=Decimal("0"))


# ── Regla dura 1: el tenant no entra por el body ────────────────────────────


def test_el_tenant_no_se_puede_mandar_en_el_alta() -> None:
    """No esta declarado Y ademas `extra="forbid"` lo rechaza.

    Las dos cosas: no declararlo evita que se aplique, prohibirlo hace que el
    intento sea VISIBLE en un 422 con el nombre del campo.
    """
    with pytest.raises(ValidationError):
        crear(domain_plate="AB123CD", tenant_id=uuid.uuid4())


def test_el_estado_no_se_puede_elegir_al_crear() -> None:
    """`RN-ST-04` fija `in_preparation`. Si entrara por el body, se podria crear
    un vehiculo ya vendido."""
    with pytest.raises(ValidationError):
        crear(domain_plate="AB123CD", status=EstadoDeVehiculo.VENDIDO)


# ── RN-ST-05: la maquina de estados ─────────────────────────────────────────


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        (EstadoDeVehiculo.EN_PREPARACION, EstadoDeVehiculo.DISPONIBLE),
        (EstadoDeVehiculo.DISPONIBLE, EstadoDeVehiculo.RESERVADO),
        (EstadoDeVehiculo.RESERVADO, EstadoDeVehiculo.VENDIDO),
        (EstadoDeVehiculo.ARCHIVADO, EstadoDeVehiculo.DISPONIBLE),
    ],
)
def test_las_transiciones_de_rn_st_05_estan_permitidas(
    desde: EstadoDeVehiculo, hacia: EstadoDeVehiculo
) -> None:
    assert es_transicion_valida(desde, hacia)


@pytest.mark.parametrize(
    ("desde", "hacia"),
    [
        # El salto que `RN-ST-04` y `RN-ST-05` existen para impedir.
        (EstadoDeVehiculo.EN_PREPARACION, EstadoDeVehiculo.VENDIDO),
        # `RN-ST-09`: no se vende dos veces el mismo vehiculo.
        (EstadoDeVehiculo.VENDIDO, EstadoDeVehiculo.DISPONIBLE),
        (EstadoDeVehiculo.VENDIDO, EstadoDeVehiculo.RESERVADO),
        (EstadoDeVehiculo.EN_TALLER, EstadoDeVehiculo.VENDIDO),
    ],
)
def test_lo_que_no_esta_en_la_tabla_esta_prohibido(
    desde: EstadoDeVehiculo, hacia: EstadoDeVehiculo
) -> None:
    """Denegar por defecto. La tabla es la lista blanca completa."""
    assert not es_transicion_valida(desde, hacia)


def test_un_estado_no_transiciona_a_si_mismo() -> None:
    for estado in EstadoDeVehiculo:
        assert not es_transicion_valida(estado, estado)


def test_pausado_no_es_un_estado_del_vehiculo() -> None:
    """`ADR-031`: es el estado de la PUBLICACION. Un aviso se pausa, un auto no."""
    assert "paused" not in {estado.value for estado in EstadoDeVehiculo}
    assert len(EstadoDeVehiculo) == 6


# ── RN-ST-06: vender exige razon ────────────────────────────────────────────


def test_marcar_como_vendido_exige_razon() -> None:
    with pytest.raises(ValidationError, match="exige una razon"):
        VehiculoCambioDeEstado(status=EstadoDeVehiculo.VENDIDO)


def test_los_demas_estados_no_exigen_razon() -> None:
    assert VehiculoCambioDeEstado(status=EstadoDeVehiculo.DISPONIBLE).reason is None


# ── RN-ST-12: el costo de adquisicion no puede filtrarse ────────────────────


def test_el_schema_comun_no_declara_el_costo_de_adquisicion() -> None:
    """La garantia es del TIPO, no de la disciplina.

    Con un campo opcional que el servicio borra, basta un `model_dump()` olvidado
    en cualquier camino de salida para filtrar el margen de la agencia. Con dos
    schemas, el que no lo tiene no puede filtrarlo.
    """
    assert "acquisition_cost_ars" not in VehiculoSalida.model_fields
    assert "acquisition_cost_ars" in VehiculoSalidaConCosto.model_fields


def test_el_schema_con_costo_sigue_trayendo_todo_lo_demas() -> None:
    """Hereda: dos schemas no pueden divergir campo a campo con el tiempo."""
    assert set(VehiculoSalida.model_fields) <= set(VehiculoSalidaConCosto.model_fields)


# ── Filtros de busqueda ─────────────────────────────────────────────────────


def test_un_rango_de_anios_invertido_se_rechaza() -> None:
    """Devolveria siempre vacio, y un listado vacio se lee como "no hay stock"
    en lugar de "preguntaste mal"."""
    with pytest.raises(ValidationError, match="año inicial"):
        FiltrosDeBusqueda(year_from=2022, year_to=2018)


def test_un_rango_de_precios_invertido_se_rechaza() -> None:
    with pytest.raises(ValidationError, match="precio minimo"):
        FiltrosDeBusqueda(price_from=Decimal("9000000"), price_to=Decimal("1000000"))


def test_los_filtros_son_todos_opcionales() -> None:
    """`GET /vehicles` sin parametros lista todo el stock del tenant."""
    assert FiltrosDeBusqueda().status is None


# ── C-14 · `VehiculoEditar`: el `null` explicito se decide campo por campo ──
#
# `design.md` D-7: `exclude_unset` distingue "campo ausente" de "campo puesto
# en null" en el JSON de entrada, pero nada impide mandar `{"color": null}` y
# `color` es `NOT NULL` en la base. Sin defensa, eso seria un `IntegrityError`
# de PostgreSQL llegandole al cliente como 500.


@pytest.mark.parametrize("campo", ["branch_id", "mileage_km", "color", "price_ars", "features"])
def test_editar_rechaza_el_null_explicito_sobre_campos_obligatorios(campo: str) -> None:
    with pytest.raises(ValidationError) as fallo:
        VehiculoEditar(**{campo: None})

    errores = fallo.value.errors()
    assert any(error["loc"] == (campo,) for error in errores)
    assert any(campo in error["msg"] for error in errores)


@pytest.mark.parametrize(
    "campo",
    ["assigned_user_id", "version_id", "price_usd", "acquisition_cost_ars", "description"],
)
def test_editar_acepta_el_null_explicito_sobre_campos_que_admiten_vacio(campo: str) -> None:
    """El contrapeso: sin este test, un validador que rechace TODO `null`
    pasaria igual el test de arriba."""
    editado = VehiculoEditar(**{campo: None})
    assert getattr(editado, campo) is None


def test_editar_sin_nada_no_levanta() -> None:
    """`{}` es un `PATCH` legitimo que no toca ningun campo."""
    editado = VehiculoEditar()
    assert editado.model_fields_set == set()


# ── `ADR-037`: la maquina de estados queda RATIFICADA, no solo escrita ──────
#
# `ADR-037-la-reserva-no-vence-sola.md`, decidido el 23-ago-2026: la regla de
# los 7 dias NO EXISTE, `reserved -> available` es manual, y
# `TRANSICIONES_PERMITIDAS` queda ratificada TAL CUAL ESTA. Hasta este ADR, la
# tabla era codigo que nadie habia aprobado — este test es donde ese cierre
# queda anclado: fija el CONJUNTO completo, no una muestra.


def test_transiciones_permitidas_tiene_exactamente_las_nueve_de_rn_st_05() -> None:
    """`ADR-037`. Ni una transicion de mas, ni una de menos.

    Los tests de arriba (`test_las_transiciones_de_rn_st_05_estan_permitidas`,
    `test_lo_que_no_esta_en_la_tabla_esta_prohibido`) verifican una MUESTRA.
    Este fija el CONJUNTO: lo que decide `RN-ST-05` es la lista completa, no
    unos pares sueltos.
    """
    E = EstadoDeVehiculo
    assert TRANSICIONES_PERMITIDAS == {
        (E.EN_PREPARACION, E.DISPONIBLE),
        (E.DISPONIBLE, E.RESERVADO),
        (E.RESERVADO, E.VENDIDO),
        (E.RESERVADO, E.DISPONIBLE),
        (E.DISPONIBLE, E.EN_TALLER),
        (E.EN_TALLER, E.DISPONIBLE),
        (E.VENDIDO, E.ARCHIVADO),
        (E.DISPONIBLE, E.ARCHIVADO),
        (E.ARCHIVADO, E.DISPONIBLE),
    }
    assert len(TRANSICIONES_PERMITIDAS) == 9


# ── `ADR-037`: la ausencia es la decision ────────────────────────────────────
#
# Un test sobre algo que NO existe se lee raro, y es exactamente lo que impide
# que la regla de los 7 dias vuelva por la puerta de atras — el ADR mismo lo
# advierte. Sin este test, alguien podria agregar `reserved_at` o una tarea de
# vencimiento sin que nada se ponga rojo, y la "decision" de `ADR-037` seria
# solo un parrafo en un documento que el codigo no respalda.


def test_no_existe_la_columna_reserved_at() -> None:
    """`ADR-037`: la reserva no vence sola. Sin la columna, no hay dato que
    respalde ningun vencimiento por tiempo — el `CHECK` mas fuerte posible."""
    from app.modules.stock.models import Vehicle

    assert "reserved_at" not in Vehicle.__table__.columns.keys()


def test_no_existe_ninguna_tarea_periodica_de_liberacion_de_reservas() -> None:
    """`ADR-037`: cero codigo nuevo. `stock.importar` (C-17) es la UNICA tarea
    de Celery del sistema, y no hay `beat_schedule` configurado."""
    from app.core.tasks import app as celery_app

    nombres_de_dominio = {nombre for nombre in celery_app.tasks if not nombre.startswith("celery.")}
    assert nombres_de_dominio == {"stock.importar"}
    assert not celery_app.conf.beat_schedule


# ── C-14 · `HistorialDeEstado` usa los nombres de la TABLA (`design.md` D-2) ─


def test_historial_de_estado_usa_changed_by_y_changed_at() -> None:
    """N1 (`spec-tecnica` §3.4) gana sobre el schema viejo (`user_id`/
    `occurred_at`), que nunca tuvo un consumidor."""
    from app.modules.stock.schemas import HistorialDeEstado

    assert {"changed_by", "changed_at"} <= set(HistorialDeEstado.model_fields)
    assert "user_id" not in HistorialDeEstado.model_fields
    assert "occurred_at" not in HistorialDeEstado.model_fields
