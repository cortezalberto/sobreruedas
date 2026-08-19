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

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.stock.models import Vehicle
from app.modules.stock.schemas import FiltrosDeBusqueda

__all__ = ["VehicleRepository"]


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
        """Los vehiculos del tenant, del mas nuevo al mas viejo.

        Por `created_at` descendente: lo que se acaba de cargar es lo que se
        busca. Sin `ORDER BY` explicito PostgreSQL devuelve cualquier orden, y un
        listado que se reordena entre dos cargas es imposible de usar.
        """
        consulta = self._vivos(select(Vehicle))

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

        return (
            (await self._sesion.execute(consulta.order_by(Vehicle.created_at.desc())))
            .scalars()
            .all()
        )

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

    def _vivos(self, consulta: Select[tuple[Vehicle]]) -> Select[tuple[Vehicle]]:
        """Tenant + no borrado. Las dos condiciones que toda consulta lleva."""
        return consulta.where(
            Vehicle.tenant_id == self._tenant_id,
            Vehicle.deleted_at.is_(None),
        )
