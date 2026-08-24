"""Acceso a datos de Stock — C-14.

LA TERCERA CAPA DE AISLAMIENTO VIVE ACA
────────────────────────────────────────
`vehicles` tiene politica RLS, asi que la base ya filtra por tenant. Aun asi
**toda** consulta de este archivo pone `tenant_id` en el `WHERE`.

No es redundancia decorativa: es la capa que sigue funcionando si alguien corre
la misma consulta con el rol propietario, o si una politica se cae en una
migracion mal escrita. La regla dura 1 pide las tres, y esta es la unica que
vive en el codigo de la aplicacion.

EL FILTRO DE SOFT DELETE ES EL DEFAULT
───────────────────────────────────────
Igual que en `tenancy`: `listar()` excluye lo dado de baja sin que nadie lo pida.
Al reves —que el default traiga todo y cada consulta se acuerde de filtrar— es la
forma segura de que un vehiculo archivado reaparezca en el listado de stock.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import paginar
from app.modules.stock.models import Vehicle
from app.modules.stock.schemas import EstadoDeVehiculo, FiltrosDeBusqueda

__all__ = ["PaginaDeVehiculos", "VehicleRepository", "contar_vehiculos"]


@dataclass(frozen=True)
class PaginaDeVehiculos:
    """Una pagina de `listar_paginado`, con instancias de `Vehicle` y no
    `Row` (`design.md` D-2, riesgo de refactorizacion).

    No se reusa `app.core.pagination.Pagina` tal cual: su `items` es
    `list[Row[Any]]`, y devolver `Vehicle` bajo esa firma seria mentirle a
    mypy sobre lo que hay adentro. Este tipo propio del modulo es lo que hace
    que `router.py` reciba vehiculos de verdad sin que el repositorio finja
    ser el `Row` que `core/pagination.py` (C-02, CRITICO) nunca prometio dar.
    """

    items: list[Vehicle]
    cursor_siguiente: str | None


# `_vivos` y `_filtrar` se aplican tanto a `select(Vehicle)` (una columna) como
# a `select(Vehicle, Vehicle.created_at.label(...), Vehicle.id.label(...))`
# (tres, para `listar_paginado`). El `TypeVar` preserva la forma exacta de la
# consulta en cada sitio de llamada en vez de ensancharla a `Any`.
_Fila = TypeVar("_Fila", bound=tuple[Any, ...])


class VehicleRepository:
    def __init__(self, sesion: AsyncSession, tenant_id: uuid.UUID) -> None:
        """El tenant se fija al construir, no por llamada.

        Asi ningun metodo puede recibir uno distinto: quien arma el repositorio
        ya decidio de que agencia habla, y ese valor vino del token.
        """
        self._sesion = sesion
        self._tenant_id = tenant_id

    async def obtener(self, vehiculo_id: uuid.UUID) -> Vehicle | None:
        consulta = self._vivos(select(Vehicle)).where(Vehicle.id == vehiculo_id)
        return (await self._sesion.execute(consulta)).scalars().first()

    async def listar(self, filtros: FiltrosDeBusqueda) -> Sequence[Vehicle]:
        """Los vehiculos del tenant, del mas nuevo al mas viejo, SIN paginar.

        ⚠️ Sigue existiendo por compatibilidad con quien ya lo llama sin
        cursor —`test_cuota_de_vehiculos.py`, `test_stock_service.py`— y no
        por el endpoint: `GET /vehicles` usa `listar_paginado` desde C-15
        (`T-080`). Devolver TODO sin techo es justo lo que ese change vino a
        cerrar; este metodo queda para quien opera a nivel de servicio y sabe
        que esta pidiendo el conjunto completo.

        Por `created_at` descendente: lo que se acaba de cargar es lo que se
        busca. Sin `ORDER BY` explicito PostgreSQL devuelve cualquier orden, y un
        listado que se reordena entre dos cargas es imposible de usar.
        """
        consulta = self._filtrar(self._vivos(select(Vehicle)), filtros)
        return (
            (await self._sesion.execute(consulta.order_by(Vehicle.created_at.desc())))
            .scalars()
            .all()
        )

    async def listar_paginado(
        self,
        filtros: FiltrosDeBusqueda,
        *,
        tenant: uuid.UUID,
        cursor: str | None = None,
        tamano: int | None = None,
    ) -> PaginaDeVehiculos:
        """`GET /vehicles` — `T-080`, `design.md` D-2.

        ⚠️ EL DETALLE QUE NO ES OBVIO (`D-2`): `paginar()` exige que la
        consulta seleccione EXPLICITAMENTE `created_at` e `id` — son las dos
        columnas del orden y las que arman el cursor de la pagina siguiente.
        Un `select(Vehicle)` a secas no alcanza: la `Row` que vuelve tiene UN
        solo elemento (la entidad), y `getattr(fila, "created_at")` -que es lo
        que `paginar` hace para armar el cursor- falla.

        Por eso la consulta selecciona la ENTIDAD MAS las dos columnas del
        orden, etiquetadas (`Vehicle.created_at.label("created_at")`,
        `Vehicle.id.label("id")`): `paginar` encuentra lo que su contrato pide
        en `selected_columns`, y este metodo recupera la entidad con `fila[0]`
        para que quien llama siga recibiendo instancias de `Vehicle` — no
        `Row`. La PRIMERA refactorizacion que "simplifica" esto de vuelta a
        `select(Vehicle)` rompe `paginar` en silencio (riesgo de
        `design.md`); `test_vehicles_listado_paginado.py` lo pone en rojo.

        `paginar` NO agrega el filtro de tenant —lo dice su propio
        docstring—: va en `consulta`, y acá lo pone `self._vivos()`, igual que
        en `listar`. Capa 3 de la regla dura 1.
        """
        consulta = self._filtrar(
            self._vivos(
                select(
                    Vehicle,
                    Vehicle.created_at.label("created_at"),
                    Vehicle.id.label("id"),
                )
            ),
            filtros,
        )
        pagina = await paginar(self._sesion, consulta, tenant=tenant, cursor=cursor, tamano=tamano)
        return PaginaDeVehiculos(
            items=[fila[0] for fila in pagina.items],
            cursor_siguiente=pagina.cursor_siguiente,
        )

    def _filtrar(self, consulta: Select[_Fila], filtros: FiltrosDeBusqueda) -> Select[_Fila]:
        """Los filtros de busqueda de `FiltrosDeBusqueda`, comunes a `listar`
        y `listar_paginado`: una sola copia, para que paginar y no paginar la
        misma consulta de negocio siga siendo, de verdad, la misma consulta.
        """
        if filtros.status is not None:
            consulta = consulta.where(Vehicle.status == filtros.status.value)
        if filtros.brand_id is not None:
            consulta = consulta.where(Vehicle.brand_id == filtros.brand_id)
        if filtros.model_id is not None:
            consulta = consulta.where(Vehicle.model_id == filtros.model_id)
        if filtros.branch_id is not None:
            consulta = consulta.where(Vehicle.branch_id == filtros.branch_id)
        if filtros.year_from is not None:
            consulta = consulta.where(Vehicle.year >= filtros.year_from)
        if filtros.year_to is not None:
            consulta = consulta.where(Vehicle.year <= filtros.year_to)
        if filtros.price_from is not None:
            consulta = consulta.where(Vehicle.price_ars >= filtros.price_from)
        if filtros.price_to is not None:
            consulta = consulta.where(Vehicle.price_ars <= filtros.price_to)
        return consulta

    async def existe_dominio(self, dominio: str) -> bool:
        """`RN-ST-01`. Se pregunta ANTES de insertar para dar un error legible.

        El `UNIQUE` parcial de la base es la garantia; esto es la cortesia. Sin
        esta consulta el cliente recibiria un error de constraint que no puede
        interpretar, en vez de "ese dominio ya esta cargado".

        ⚠️ No cierra la carrera: entre esta consulta y el INSERT puede entrar
        otro. La garantia sigue siendo el indice, y el servicio traduce su
        violacion. Esto solo mejora el caso comun.
        """
        consulta = self._vivos(select(Vehicle.id)).where(Vehicle.domain_plate == dominio)
        return (await self._sesion.execute(consulta)).first() is not None

    def agregar(self, vehiculo: Vehicle) -> Vehicle:
        self._sesion.add(vehiculo)
        return vehiculo

    def _vivos(self, consulta: Select[_Fila]) -> Select[_Fila]:
        """Tenant + no borrado. Las dos condiciones que toda consulta lleva."""
        return consulta.where(
            Vehicle.tenant_id == self._tenant_id,
            Vehicle.deleted_at.is_(None),
        )


async def contar_vehiculos(sesion: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Vehiculos que OCUPAN cuota del plan. Lo llama `PlanLimitsService`.

    Es funcion suelta y no metodo del repositorio porque la firma la fija
    `limits.py` (`Contador = (AsyncSession, UUID) -> int`) y quien la invoca no
    tiene —ni debe tener— un repositorio construido con un tenant adentro.

    QUE NO CUENTA, Y POR QUE CADA EXCLUSION
    ────────────────────────────────────────
      - **Dados de baja** (`deleted_at`): la fila sobrevive por la regla dura 3,
        pero un vehiculo borrado no esta en el stock de nadie.
      - **Vendidos** (`sold`): lo promete `assert_can_add_vehicle` desde C-04.
        Si vender consumiera cuota, el plan se agotaria solo con el tiempo y el
        cliente que mas vende seria el primero en quedarse sin lugar.

    `archived` SI cuenta: es "lo saque de la vitrina", no "ya no lo tengo". El
    dia que eso se discuta, la respuesta esta en `RN-ST-05`, no acá.
    """
    consulta = (
        select(func.count())
        .select_from(Vehicle)
        .where(
            Vehicle.tenant_id == tenant_id,
            Vehicle.deleted_at.is_(None),
            Vehicle.status != EstadoDeVehiculo.VENDIDO.value,
        )
    )
    return int((await sesion.execute(consulta)).scalar_one())
