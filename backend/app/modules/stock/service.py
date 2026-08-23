"""Reglas de negocio de Stock — C-14.

DONDE VIVE CADA GARANTIA
─────────────────────────
  - Formato y rangos          → `schemas.py` (Pydantic, 422)
  - Unicidad y aislamiento    → PostgreSQL (indices, RLS)
  - REGLAS DE NEGOCIO         → acá

La distincion importa: que el año no sea 2050 es validacion de entrada, pero que
un vehiculo no pase de `in_preparation` a `sold` es una regla del dominio, y
tiene que estar donde no dependa de por que camino llego la peticion.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.core.outbox import registrar
from app.modules.stock.historial import registrar_transicion
from app.modules.stock.models import Vehicle
from app.modules.stock.repository import PaginaDeVehiculos, VehicleRepository, contar_vehiculos
from app.modules.stock.schemas import (
    EstadoDeVehiculo,
    FiltrosDeBusqueda,
    VehiculoCambioDeEstado,
    VehiculoCrear,
    VehiculoEditar,
    es_transicion_valida,
)
from app.modules.tenancy.limits import PlanLimitsService, Recurso

__all__ = ["StockService", "TransicionInvalida", "VehiculoDuplicado", "VehiculoNoEncontrado"]


class VehiculoNoEncontrado(DomainError):
    """No existe, o es de otra agencia. Las dos dan **404**.

    Distinguirlas —"no existe" contra "no es tuyo"— le confirmaria a un tenant
    que cierto id existe en otra agencia. Seria una fuga de informacion por el
    codigo de estado, sin devolver un solo dato.

    ⚠️ `status_code` se pisa a 404 EXPLICITAMENTE. `DomainError` trae 422, que
    es correcto para una regla de negocio incumplida y equivocado para un
    recurso ausente. La primera version heredaba el 422 y el docstring decia
    "404": el texto prometia algo que el codigo no hacia, y lo encontro el test
    de aislamiento.
    """

    status_code = 404


class VehiculoDuplicado(DomainError):
    """`RN-ST-01`: el dominio ya esta cargado en esta agencia.

    ⚠️ EL `code` SE DECLARA, no se hereda. `DomainError` trae `domain_error`,
    que dice "alguna regla de negocio se incumplio" y no cual. Con el generico,
    el frontend traducia este rechazo a "dominio repetido" POR DESCARTE: era el
    unico `DomainError` que el alta podia levantar. Andaba, y venia con fecha de
    vencimiento — el dia que el alta levantara un segundo, el usuario leeria que
    repitio un dominio cuando el problema fuese otro, y ningun test se pondria
    rojo porque los dos casos devuelven el mismo codigo.

    `test_alta_espejada.py` vigila que este valor sea el mismo que el frontend
    espera, igual que vigila los enums y los formatos.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail, code="vehicle_duplicate")


class TransicionInvalida(DomainError):
    """`RN-ST-05`: ese cambio de estado no esta en la tabla de permitidas."""


class StockService:
    """Operaciones de stock, siempre acotadas a un tenant.

    El `tenant_id` se recibe al construir y viene del token. Ningun metodo lo
    toma por parametro: quien tiene el servicio ya decidio de que agencia habla.
    """

    def __init__(self, sesion: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._sesion = sesion
        self._tenant_id = tenant_id
        self._repositorio = VehicleRepository(sesion, tenant_id)

        # El contador de vehiculos lo registra ESTE modulo, que es el dueño de
        # la tabla. `limits.py` sabe de planes y de cuotas, no de la forma de
        # `vehicles` — asi C-05 y C-17 pueden registrar los suyos sin tocarlo.
        #
        # ⚠️ Que esta linea faltara es como el sistema quedo sin techo de
        # facturacion: `assert_can_add_vehicle` existia desde C-04 y nadie lo
        # llamaba, asi que la falla-cerrado de `limits.py` nunca tuvo ocasion
        # de dispararse. Ver `tests/integration/test_cuota_de_vehiculos.py`.
        self._limites = PlanLimitsService(sesion)
        self._limites.registrar(Recurso.VEHICLES, contar_vehiculos)

    def _evento(self, tipo: str, vehiculo: Vehicle, extra: dict[str, object]) -> None:
        """Anota un hecho en el outbox. Sale cuando la transaccion commitee.

        ⚠️ EL PAYLOAD ES MINIMO, Y ESO ES UNA DECISION DE SEGURIDAD. `RN-ST-12`
        hace que `acquisition_cost_ars` no le viaje a un `salesperson` por la
        API — pero **un evento no tiene quien pregunta**. Si el payload llevara
        el vehiculo entero, el costo quedaria en un stream de Redis legible por
        cualquier consumidor futuro, y la regla se evaporaria por la puerta de
        atras. Quien necesite mas datos los pide por la API, con el rol de quien
        pregunta.

        `registrar` no es `async` ni toca la red: agrega la fila a esta misma
        transaccion. Ver `ADR-036`.
        """
        registrar(
            self._sesion,
            tipo,
            tenant_id=self._tenant_id,
            payload={"vehicle_id": str(vehiculo.id), **extra},
        )

    async def listar(self, filtros: FiltrosDeBusqueda) -> list[Vehicle]:
        return list(await self._repositorio.listar(filtros))

    async def listar_paginado(
        self,
        filtros: FiltrosDeBusqueda,
        *,
        cursor: str | None = None,
        tamano: int | None = None,
    ) -> PaginaDeVehiculos:
        """`GET /vehicles` — `T-080`. El tenant lo pone ESTE servicio, con el
        valor que ya tiene guardado (viene del token), no un parametro nuevo
        que otro llamador pudiera pisar."""
        return await self._repositorio.listar_paginado(
            filtros, tenant=self._tenant_id, cursor=cursor, tamano=tamano
        )

    async def obtener(self, vehiculo_id: uuid.UUID) -> Vehicle:
        vehiculo = await self._repositorio.obtener(vehiculo_id)
        if vehiculo is None:
            raise VehiculoNoEncontrado("no existe ese vehiculo")
        return vehiculo

    async def crear(self, datos: VehiculoCrear) -> Vehicle:
        """Alta. El estado inicial lo fija la regla, no el cliente (`RN-ST-04`).

        La cuota del plan se verifica ANTES del INSERT y antes del chequeo de
        duplicados: si la agencia llego a su techo, que el dominio este repetido
        o no da lo mismo, y un 422 de duplicado escondiendo un 402 de cuota
        manda a corregir la patente en vez de a subir de plan.
        """
        await self._limites.assert_can_add_vehicle(self._tenant_id)

        if datos.domain_plate is not None and await self._repositorio.existe_dominio(
            datos.domain_plate
        ):
            # El mensaje NO repite el dominio: es dato que identifica a una
            # persona (Ley 25.326) y este texto termina en el log.
            raise VehiculoDuplicado("ya hay un vehiculo cargado con ese dominio")

        vehiculo = Vehicle(
            **datos.model_dump(),
            # El tenant lo pone el servicio con el valor del token. Es el unico
            # lugar del sistema donde se escribe, y no llega por el body: el
            # schema de entrada ni siquiera declara el campo.
            tenant_id=self._tenant_id,
            status=EstadoDeVehiculo.EN_PREPARACION.value,
        )
        self._repositorio.agregar(vehiculo)
        # El `flush` va ANTES del registro porque el evento lleva el id, y el id
        # lo asigna la base: registrarlo antes anotaria un `None`.
        await self._sesion.flush()
        # La fila GENESIS (`design.md` D-4): `from_status = NULL` es el unico
        # productor posible de esa columna nullable — sin esta fila, la linea
        # de tiempo de un vehiculo empezaria en su segundo estado.
        #
        # `autor=None`: `crear` no recibe un sujeto (a diferencia de
        # `cambiar_estado`, cuyo router ya trae `SujetoActual` por
        # `verificar_alcance`). Hilar el autor hasta acá es una decision de
        # `design.md` D-3 que este change no toma.
        registrar_transicion(
            self._sesion,
            tenant_id=self._tenant_id,
            vehiculo_id=vehiculo.id,
            desde=None,
            hasta=EstadoDeVehiculo.EN_PREPARACION,
            razon=None,
            autor=None,
        )
        self._evento("vehicle.created", vehiculo, {"status": vehiculo.status})
        return vehiculo

    async def cambiar_estado(
        self, vehiculo_id: uuid.UUID, cambio: VehiculoCambioDeEstado, *, autor: uuid.UUID | None
    ) -> Vehicle:
        """`RN-ST-05` y `RN-ST-06`.

        La transicion se valida contra el estado ACTUAL, que es el dato que el
        schema no puede conocer. Lo que no esta en la tabla de permitidas se
        rechaza: denegar por defecto.

        `autor` es OBLIGATORIO por palabra clave (`design.md` D-3): `None` es
        un valor legitimo — transicion automatica, sin persona detras — y no
        un default silencioso. El router YA tiene `SujetoActual` para
        `verificar_alcance`, asi que pasarlo no agrega ninguna dependencia
        nueva al endpoint.
        """
        vehiculo = await self.obtener(vehiculo_id)
        actual = EstadoDeVehiculo(vehiculo.status)

        if not es_transicion_valida(actual, cambio.status):
            raise TransicionInvalida(
                f"no se puede pasar de '{actual.value}' a '{cambio.status.value}'"
            )

        vehiculo.status = cambio.status.value
        # `RN-ST-06`: archivar setea la fecha de salida. Vender la de venta.
        if cambio.status is EstadoDeVehiculo.VENDIDO:
            vehiculo.sold_at = dt.datetime.now(dt.UTC)

        # ANTES del flush final: la fila de historial tiene que estar en la
        # MISMA unidad de trabajo que el cambio que documenta (`design.md`
        # D-5) — si la transaccion se revierte despues de esta linea, ni el
        # cambio de estado ni el registro sobreviven.
        registrar_transicion(
            self._sesion,
            tenant_id=self._tenant_id,
            vehiculo_id=vehiculo.id,
            desde=actual,
            hasta=cambio.status,
            razon=cambio.reason,
            autor=autor,
        )

        await self._sesion.flush()
        # `from` y `to` en el payload: un consumidor que solo recibiera el estado
        # nuevo no podria distinguir "se reservo" de "volvio a estar disponible
        # y despues se reservo", y las automatizaciones de C-28 se disparan por
        # la transicion, no por el estado.
        self._evento(
            "vehicle.status_changed",
            vehiculo,
            {"from": actual.value, "to": cambio.status.value},
        )
        return vehiculo

    async def editar(
        self, vehiculo_id: uuid.UUID, datos: VehiculoEditar, *, autor: uuid.UUID | None
    ) -> Vehicle:
        """`T-075`. Edicion parcial DE VERDAD (`design.md` D-7).

        `model_dump(exclude_unset=True)` y no `exclude_none`: un campo AUSENTE
        del cuerpo no se toca, y uno presente en `null` se vacia — cuando la
        tabla lo admite. Lo que la tabla no admite ya lo rechazo el schema, con
        un 422 legible, antes de llegar aca.

        NO puede tocar el estado: `status` no esta en `VehiculoEditar` y no se
        agrega. El cambio de estado tiene su propio endpoint porque `RN-ST-05`
        restringe las transiciones y `RN-ST-06` exige razon para algunas —
        dejarlo entrar por aca saltearia las dos de un tiron.

        `autor` es obligatorio por palabra clave, igual que en
        `cambiar_estado` (`design.md` D-3) — consistencia de firma entre los
        metodos que auditan una mutacion, aunque esta no escriba una fila de
        historial (no hay transicion que registrar) ni lo lleve el evento
        (`D-6`: el payload nombra los campos que cambiaron, nunca quien ni con
        que valor).
        """
        vehiculo = await self.obtener(vehiculo_id)

        cambios = datos.model_dump(exclude_unset=True)
        # Ordenados: un consumidor del evento no puede depender del orden de
        # insercion de un dict, y dos ediciones con los mismos campos tienen
        # que producir el MISMO payload.
        campos_modificados = sorted(
            campo for campo, valor in cambios.items() if getattr(vehiculo, campo) != valor
        )
        if not campos_modificados:
            # `D-6`: un PATCH que no cambia nada no es un hecho. Mandar el
            # mismo precio dos veces no tiene que disparar una reindexacion.
            return vehiculo

        for campo in campos_modificados:
            setattr(vehiculo, campo, cambios[campo])
        vehiculo.updated_at = dt.datetime.now(dt.UTC)

        await self._sesion.flush()
        # Los NOMBRES de los campos, nunca sus valores (`D-6`, `RN-ST-12`): un
        # evento no tiene quien pregunta, y `acquisition_cost_ars` es dato
        # restringido por la API.
        self._evento("vehicle.updated", vehiculo, {"campos": campos_modificados})
        return vehiculo

    async def dar_de_baja(self, vehiculo_id: uuid.UUID) -> None:
        """Borrado LOGICO (regla dura 3). `db.delete()` esta prohibido.

        ⚠️ `RN-ST-07` (no archivar con leads activos) y `RN-ST-08` (una operacion
        cerrada solo se archiva) NO se verifican todavia: `leads` y `operations`
        son C-16 y C-19. Queda dicho para que no se de por cubierto — hoy esto
        da de baja un vehiculo que podria tener un lead abierto.
        """
        vehiculo = await self.obtener(vehiculo_id)
        vehiculo.deleted_at = dt.datetime.now(dt.UTC)
        await self._sesion.flush()
        # ⚠️ `vehicle.archived` es la BAJA LOGICA, no el estado `archived`. Son
        # dos cosas distintas que comparten nombre: `dar_de_baja` escribe
        # `deleted_at` y no toca `status`, mientras que pasar a `archived` es una
        # transicion de `RN-ST-05` que deja el vehiculo vivo. Un consumidor que
        # las confunda va a borrar de su indice vehiculos que siguen existiendo.
        self._evento("vehicle.archived", vehiculo, {"status": vehiculo.status})
