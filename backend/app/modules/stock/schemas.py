"""Contratos de entrada y salida de Stock — C-14 / C-15.

QUE ES ESTE ARCHIVO Y QUE NO
─────────────────────────────
Son los contratos de los endpoints de `/vehicles`, escritos ANTES de que exista
el router. Se pueden escribir hoy porque un schema no consulta la base ni decide
quien ve que: lo que falta para exponerlos es `rbac.py`, y eso espera a `E-001`.

`tenant_id` NO EXISTE EN NINGUN SCHEMA DE ENTRADA
──────────────────────────────────────────────────
Igual que en `tenancy`: no esta declarado y ademas `extra="forbid"` rechaza la
peticion que lo mande. Sale del token, nunca del body (regla dura 1).

Tampoco entran `assigned_user_id` en el alta ni `status`: el estado inicial lo
fija `RN-ST-04` y la asignacion es una operacion aparte. Dejarlos entrar por el
body permitiria crear un vehiculo ya vendido, o asignado a un vendedor de otra
agencia.
"""

from __future__ import annotations

import datetime as dt
import re
import uuid
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

__all__ = [
    "Combustible",
    "EstadoDeVehiculo",
    "FiltrosDeBusqueda",
    "TRANSICIONES_PERMITIDAS",
    "Transmision",
    "VehiculoCambioDeEstado",
    "VehiculoCrear",
    "VehiculoEditar",
    "VehiculoSalida",
    "VehiculoSalidaConCosto",
    "es_transicion_valida",
]

# El año maximo aceptable es el proximo: las agencias cargan el modelo siguiente
# antes de que termine el año en curso (`RN-ST-03`).
ANIO_MINIMO = 1950


class EstadoDeVehiculo(StrEnum):
    """Los SEIS estados — `ADR-031` cierra `IN-11`.

    `Pausado` no esta y no es un olvido: es el estado de la PUBLICACION, no del
    vehiculo. Un aviso se pausa, un auto no.
    """

    EN_PREPARACION = "in_preparation"
    DISPONIBLE = "available"
    RESERVADO = "reserved"
    VENDIDO = "sold"
    EN_TALLER = "in_workshop"
    ARCHIVADO = "archived"


class Combustible(StrEnum):
    NAFTA = "gasoline"
    DIESEL = "diesel"
    HIBRIDO = "hybrid"
    ELECTRICO = "electric"
    GNC = "gnc"
    FLEX = "flex"


class Transmision(StrEnum):
    MANUAL = "manual"
    AUTOMATICA = "automatic"
    CVT = "cvt"
    DSG = "dsg"


class Carroceria(StrEnum):
    SEDAN = "sedan"
    HATCHBACK = "hatchback"
    SUV = "suv"
    PICKUP = "pickup"
    VAN = "van"
    COUPE = "coupe"
    WAGON = "wagon"
    OTRA = "other"


# `RN-ST-05`, literal. Se transcribe como dato y no como cadena de `if`: una
# maquina de estados escrita en condicionales es imposible de auditar contra la
# regla, y esta tiene que poder leerse al lado del documento.
#
# Lo que NO esta acá tampoco esta permitido — es denegar por defecto.
TRANSICIONES_PERMITIDAS: frozenset[tuple[EstadoDeVehiculo, EstadoDeVehiculo]] = frozenset(
    {
        (EstadoDeVehiculo.EN_PREPARACION, EstadoDeVehiculo.DISPONIBLE),
        (EstadoDeVehiculo.DISPONIBLE, EstadoDeVehiculo.RESERVADO),
        (EstadoDeVehiculo.RESERVADO, EstadoDeVehiculo.VENDIDO),
        (EstadoDeVehiculo.RESERVADO, EstadoDeVehiculo.DISPONIBLE),
        (EstadoDeVehiculo.DISPONIBLE, EstadoDeVehiculo.EN_TALLER),
        (EstadoDeVehiculo.EN_TALLER, EstadoDeVehiculo.DISPONIBLE),
        (EstadoDeVehiculo.VENDIDO, EstadoDeVehiculo.ARCHIVADO),
        (EstadoDeVehiculo.DISPONIBLE, EstadoDeVehiculo.ARCHIVADO),
        (EstadoDeVehiculo.ARCHIVADO, EstadoDeVehiculo.DISPONIBLE),
    }
)


def es_transicion_valida(desde: EstadoDeVehiculo, hacia: EstadoDeVehiculo) -> bool:
    """`RN-ST-05`. Cualquier par que no figure es `invalid_transition`."""
    return (desde, hacia) in TRANSICIONES_PERMITIDAS


# ── Validadores del dominio argentino ───────────────────────────────────────

# Formato viejo `AAA999` y Mercosur `AA999AA` (`knowledge-base/04`). Se acepta
# sin separadores y se normaliza: el mismo dominio escrito de dos formas no
# puede producir dos vehiculos, igual que pasa con el CUIT en `tenancy`.
_DOMINIO_VIEJO = re.compile(r"^[A-Z]{3}[0-9]{3}$")
_DOMINIO_MERCOSUR = re.compile(r"^[A-Z]{2}[0-9]{3}[A-Z]{2}$")

# VIN: 17 caracteres, sin I, O ni Q — se excluyen para no confundirlas con 1 y 0.
_CHASIS = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


def normalizar_dominio(valor: str) -> str:
    """Mayusculas y sin separadores. Levanta `ValueError` si no es un formato AR."""
    limpio = re.sub(r"[\s-]", "", valor).upper()
    if not (_DOMINIO_VIEJO.match(limpio) or _DOMINIO_MERCOSUR.match(limpio)):
        # El mensaje NO repite el valor: termina en el log, y un dominio es dato
        # que permite identificar a una persona (Ley 25.326).
        raise ValueError("el dominio no tiene formato argentino (AAA999 o AA999AA)")
    return limpio


def normalizar_chasis(valor: str) -> str:
    limpio = re.sub(r"[\s-]", "", valor).upper()
    if not _CHASIS.match(limpio):
        raise ValueError(
            "el numero de chasis debe tener 17 caracteres alfanumericos, sin I, O ni Q"
        )
    return limpio


class _EntradaEstricta(BaseModel):
    """Base de todo schema de ENTRADA. Ver el encabezado del modulo."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class VehiculoCrear(_EntradaEstricta):
    """Alta de un vehiculo.

    ⚠️ `domain_plate` es OPCIONAL — `ADR-031` cierra `IN-07`. Un 0 km sin
    patentar y un usado recien recibido en permuta no tienen dominio todavia, y
    con el campo obligatorio una agencia no podria cargarlos.

    Lo que si se exige es que venga **al menos uno** de dominio o chasis: un
    vehiculo sin ninguna forma de identificarse no se puede distinguir de otro.
    """

    branch_id: uuid.UUID
    brand_id: uuid.UUID
    model_id: uuid.UUID
    version_id: uuid.UUID | None = None

    domain_plate: str | None = None
    chassis_number: str | None = None
    engine_number: Annotated[str, Field(max_length=30)] | None = None

    year: Annotated[int, Field(ge=ANIO_MINIMO)]
    mileage_km: Annotated[int, Field(ge=0)]
    color: Annotated[str, Field(min_length=1, max_length=60)]
    fuel_type: Combustible
    transmission: Transmision
    body_type: Carroceria

    price_ars: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
    price_usd: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)] | None = None
    acquisition_cost_ars: (
        Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)] | None
    ) = None

    description: str | None = None
    features: list[str] = Field(default_factory=list)
    acquired_at: dt.datetime | None = None

    @model_validator(mode="after")
    def _identificable(self) -> VehiculoCrear:
        """`ADR-031`: el `CHECK` de la base, tambien en el contrato.

        Se valida acá ademas de en PostgreSQL a proposito: la base devuelve un
        error de constraint que el cliente no puede leer, y este devuelve un 422
        que nombra el problema.
        """
        if self.domain_plate is None and self.chassis_number is None:
            raise ValueError("hace falta al menos el dominio o el numero de chasis")

        if self.domain_plate is not None:
            self.domain_plate = normalizar_dominio(self.domain_plate)
        if self.chassis_number is not None:
            self.chassis_number = normalizar_chasis(self.chassis_number)
        return self

    @model_validator(mode="after")
    def _anio_no_futuro(self) -> VehiculoCrear:
        """`RN-ST-03`: hasta el año que viene.

        El techo se calcula en tiempo de validacion y no es una constante: una
        constante quedaria vieja el 1 de enero, y el sintoma seria que nadie
        puede cargar el modelo nuevo.
        """
        maximo = dt.datetime.now(dt.UTC).year + 1
        if self.year > maximo:
            raise ValueError(f"el año no puede ser posterior a {maximo}")
        return self


class VehiculoEditar(_EntradaEstricta):
    """Edicion parcial. Todo opcional: es un `PATCH`.

    `status` NO esta: el cambio de estado tiene su propio endpoint porque
    `RN-ST-05` restringe las transiciones y `RN-ST-06` exige razon para algunas.
    Dejarlo entrar acá permitiria saltar de `in_preparation` a `sold` sin pasar
    por ninguna validacion.

    EL `null` EXPLICITO SE DECIDE CAMPO POR CAMPO (`design.md` D-7)
    ───────────────────────────────────────────────────────────────
    Todo campo es `X | None = None` porque el servicio usa
    `model_dump(exclude_unset=True)`: un campo AUSENTE del cuerpo no se toca,
    y uno presente con `null` se vacia — son dos casos distintos en el JSON de
    entrada y tienen que seguir viendose distintos aca.

    Pero eso deja la puerta abierta a `{"color": null}`, y `color` es
    `NOT NULL` en la base: sin defensa, ese `PATCH` seria un `IntegrityError`
    de PostgreSQL llegandole al cliente como 500. Los `field_validator` de
    abajo cierran esa puerta SOLO para los campos que la tabla no admite
    nulos — `branch_id`, `mileage_km`, `color`, `price_ars`, `features` — y
    dejan pasar el `null` en los que si lo admiten (`assigned_user_id`,
    `version_id`, `price_usd`, `acquisition_cost_ars`, `description`), donde
    vaciar es una operacion legitima.

    Por que esto funciona sin tocar `exclude_unset`: Pydantic NO corre un
    `field_validator` sobre el DEFAULT de un campo ausente —solo sobre lo que
    el cuerpo realmente trae—, asi que `{}` nunca dispara estos validadores y
    `{"color": null}` si.
    """

    branch_id: uuid.UUID | None = None
    assigned_user_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    mileage_km: Annotated[int, Field(ge=0)] | None = None
    color: Annotated[str, Field(min_length=1, max_length=60)] | None = None
    price_ars: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)] | None = None
    price_usd: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)] | None = None
    acquisition_cost_ars: (
        Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)] | None
    ) = None
    description: str | None = None
    features: list[str] | None = None

    @field_validator("branch_id", "mileage_km", "color", "price_ars", "features")
    @classmethod
    def _no_admite_vaciarse(cls, valor: object, info: ValidationInfo) -> object:
        """Rechaza el `null` explicito sobre un campo `NOT NULL` de la tabla.

        Se dispara SOLO si el campo vino en el cuerpo: un default ausente no
        pasa por aca (ver el docstring de la clase). El mensaje nombra el
        campo — via `loc` (el nombre del `field_validator`) y via texto — para
        que el 422 sea legible sin tener que adivinar cual de los cinco fue.
        """
        if valor is None:
            raise ValueError(f"el campo '{info.field_name}' no admite quedar vacío")
        return valor


class VehiculoCambioDeEstado(_EntradaEstricta):
    """`POST /vehicles/{id}/status`.

    La razon es obligatoria al vender (`RN-ST-06`). No se valida acá que la
    transicion sea legal: eso necesita el estado ACTUAL, que el schema no
    conoce — lo hace el servicio con `es_transicion_valida`.
    """

    status: EstadoDeVehiculo
    reason: Annotated[str, Field(min_length=1, max_length=500)] | None = None

    @model_validator(mode="after")
    def _vender_exige_razon(self) -> VehiculoCambioDeEstado:
        if self.status is EstadoDeVehiculo.VENDIDO and not self.reason:
            raise ValueError("marcar como vendido exige una razon")
        return self


class FiltrosDeBusqueda(_EntradaEstricta):
    """Parametros de `GET /vehicles`.

    Los rangos se validan cruzados: un `precio_desde` mayor que el `precio_hasta`
    devuelve siempre vacio, y un listado vacio se lee como "no hay stock" en
    lugar de "preguntaste mal".

    ⚠️ `cursor` Y `limit` VIVEN ACA, Y NO COMO PARAMETROS SUELTOS DEL ENDPOINT
    ───────────────────────────────────────────────────────────────────────────
    No es una cuestion de gusto: es una limitacion real de FastAPI (probada,
    no leida) en la version instalada (`0.141.1`). `Annotated[Modelo,
    Query()]` "desarma" el modelo en query params individuales SOLO si es el
    UNICO parametro de ese tipo en la funcion — apenas aparece OTRO parametro
    resuelto por query (otro modelo, o un escalar suelto como
    `cursor: str | None = None`), FastAPI deja de desarmarlo y empieza a
    esperar el modelo entero como un UNICO parametro JSON llamado `filtros`.
    El sintoma es silencioso: cada campo del modelo vuelve `None` sin que
    nada falle ni loguee nada.

    La consecuencia es que `cursor` y `limit` de `GET /vehicles` (`T-080`)
    tienen que declararse ACA, en el mismo modelo que `status` y el resto —no
    en un segundo modelo de paginacion, y no como parametros sueltos del
    endpoint— para seguir siendo UN solo modelo de query. `T-080` no inventa
    esto: lo hereda de una restriccion de FastAPI que este proposal no puede
    rediseñar, y que `test_vehicles_listado_paginado.py` fija en un test para
    que la proxima persona que "limpie" esto no vuelva a romperlo en silencio.
    """

    status: EstadoDeVehiculo | None = None
    brand_id: uuid.UUID | None = None
    model_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    year_from: Annotated[int, Field(ge=ANIO_MINIMO)] | None = None
    year_to: Annotated[int, Field(ge=ANIO_MINIMO)] | None = None
    price_from: Annotated[Decimal, Field(ge=0)] | None = None
    price_to: Annotated[Decimal, Field(ge=0)] | None = None
    q: Annotated[str, Field(min_length=2, max_length=120)] | None = None
    cursor: str | None = None
    limit: int | None = None

    @model_validator(mode="after")
    def _rangos_coherentes(self) -> FiltrosDeBusqueda:
        if (
            self.year_from is not None
            and self.year_to is not None
            and self.year_from > self.year_to
        ):
            raise ValueError("el año inicial no puede ser mayor que el final")
        if (
            self.price_from is not None
            and self.price_to is not None
            and self.price_from > self.price_to
        ):
            raise ValueError("el precio minimo no puede ser mayor que el maximo")
        return self


class _Salida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class VehiculoSalida(_Salida):
    """Lo que ve CUALQUIER rol con acceso al vehiculo.

    ⚠️ `acquisition_cost_ars` NO ESTA ACA, y es el punto de que existan dos
    schemas de salida. `RN-ST-12` dice que el precio de costo solo lo ven
    `manager` y `admin_staff`, y que **nunca se publica**.

    Se resuelve con dos schemas y no con un campo opcional que el servicio
    borra: un campo que a veces viaja depende de que alguien se acuerde de
    borrarlo en cada camino de salida, y basta un `model_dump()` olvidado para
    filtrar el margen de la agencia. Con dos tipos, el que no lo tiene no puede
    filtrarlo — lo garantiza el tipo, no la disciplina.
    """

    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID
    assigned_user_id: uuid.UUID | None

    domain_plate: str | None
    chassis_number: str | None
    brand_id: uuid.UUID
    model_id: uuid.UUID
    version_id: uuid.UUID | None

    year: int
    mileage_km: int
    color: str
    fuel_type: Combustible
    transmission: Transmision
    body_type: Carroceria

    price_ars: Decimal
    price_usd: Decimal | None
    status: EstadoDeVehiculo
    description: str | None
    features: list[str]

    acquired_at: dt.datetime | None
    sold_at: dt.datetime | None
    created_at: dt.datetime


class VehiculoSalidaConCosto(VehiculoSalida):
    """Lo mismo, mas el costo. **Solo para `manager` y `admin_staff`** (`RN-ST-12`).

    Quien elige entre este schema y `VehiculoSalida` es la capa de autorizacion,
    no el servicio de stock: el alcance por campos es cosa de `rbac.py`
    (`ADR-024` §6, conjunto de campos opcional), y este archivo solo ofrece las
    dos formas.
    """

    acquisition_cost_ars: Decimal | None


class HistorialDeEstado(_Salida):
    """Una entrada de `GET /vehicles/{id}/history`.

    `changed_by` y `changed_at`, y NO `user_id`/`occurred_at` — `design.md`
    D-2 (C-14) los renombra contra los nombres de la TABLA (`spec-tecnica`
    §3.4, N1), que gana sobre este schema por `ADR-000`: el schema nunca tuvo
    un consumidor —ni endpoint, ni entrada en el espejo del frontend, ni en
    `test_vehiculo_espejado.py`— asi que renombrarlo no rompe nada, y mapear
    el atributo a la columna habria dejado dos vocabularios para la misma fila
    para siempre.

    `changed_by` puede ser nulo: una transicion automatica —la que dispara un
    evento de dominio, no una persona— no tiene autor.
    """

    id: uuid.UUID
    vehicle_id: uuid.UUID
    from_status: EstadoDeVehiculo | None
    to_status: EstadoDeVehiculo
    reason: str | None
    changed_by: uuid.UUID | None
    changed_at: dt.datetime


class ResultadoDeImportacion(_Salida):
    """`POST /vehicles/import` — `RN-ST-13`.

    Informa por FILA y no solo un total: una importacion de 5.000 filas donde
    fallan 12 es un exito con 12 correcciones, y decir "fallo" obligaria a
    reprocesar todo. `errores` trae el numero de fila para poder arreglarla.
    """

    filas_leidas: int
    creados: int
    rechazados: int
    errores: list[dict[str, Any]]
