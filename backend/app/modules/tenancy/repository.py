"""Acceso a datos del modulo tenancy — C-04.

EL FILTRO DE SOFT DELETE ES EL DEFAULT, NO UNA OPCION
──────────────────────────────────────────────────────
`listar()` excluye las filas dadas de baja sin que nadie tenga que pedirlo, y
para verlas hay que decir `incluir_dadas_de_baja=True`. Al reves —que el
default traiga todo y cada consulta se acuerde de filtrar— es la forma segura
de que una agencia cancelada reaparezca en un listado seis meses despues.

Es la misma logica del `EXENTAS_DE_RLS` de C-02: lo excepcional se declara, lo
normal no se pide.

DOS CAPAS PARA `tenants`, TRES PARA `branches`
───────────────────────────────────────────────
`branches` tiene politica RLS, asi que la base ya filtra por tenant — y aun asi
`BranchRepository` pone `tenant_id` en el WHERE. Es la regla dura 1: las tres
capas siempre, y el filtro explicito es la que sigue funcionando si alguien
corre la consulta con el rol propietario.

`tenants` NO tiene politica (design.md D-1), asi que ahi el filtro explicito no
es redundancia: es la unica barrera. Por eso `obtener()` recibe el id y nunca
hay un "traeme todos" sin acotar desde el espacio de tenant.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenancy.models import Branch, Plan, Tenant, VehicleBrand, VehicleModel

__all__ = [
    "BranchRepository",
    "PlanRepository",
    "TenantRepository",
    "VehicleCatalogRepository",
]


class TenantRepository:
    """Agencias. Sin politica RLS: el acotamiento es responsabilidad de aca."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener(
        self, tenant_id: uuid.UUID, *, incluir_dadas_de_baja: bool = False
    ) -> Tenant | None:
        consulta = select(Tenant).where(Tenant.id == tenant_id)
        return (
            await self._sesion.execute(self._vivos(consulta, incluir_dadas_de_baja))
        ).scalar_one_or_none()

    async def obtener_por_slug(self, slug: str) -> Tenant | None:
        consulta = self._vivos(select(Tenant).where(Tenant.slug == slug), False)
        return (await self._sesion.execute(consulta)).scalar_one_or_none()

    async def listar(self, *, incluir_dadas_de_baja: bool = False) -> Sequence[Tenant]:
        consulta = self._vivos(select(Tenant).order_by(Tenant.created_at), incluir_dadas_de_baja)
        return (await self._sesion.execute(consulta)).scalars().all()

    def agregar(self, agencia: Tenant) -> Tenant:
        self._sesion.add(agencia)
        return agencia

    @staticmethod
    def _vivos(consulta: Select[tuple[Tenant]], incluir: bool) -> Select[tuple[Tenant]]:
        return consulta if incluir else consulta.where(Tenant.deleted_at.is_(None))


class BranchRepository:
    """Sucursales. Con politica RLS, y con el filtro explicito igual."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener(
        self, tenant_id: uuid.UUID, sucursal_id: uuid.UUID, *, incluir_dadas_de_baja: bool = False
    ) -> Branch | None:
        consulta = select(Branch).where(Branch.tenant_id == tenant_id, Branch.id == sucursal_id)
        return (
            await self._sesion.execute(self._vivas(consulta, incluir_dadas_de_baja))
        ).scalar_one_or_none()

    async def listar(
        self, tenant_id: uuid.UUID, *, incluir_dadas_de_baja: bool = False
    ) -> Sequence[Branch]:
        consulta = select(Branch).where(Branch.tenant_id == tenant_id).order_by(Branch.created_at)
        return (
            (await self._sesion.execute(self._vivas(consulta, incluir_dadas_de_baja)))
            .scalars()
            .all()
        )

    def agregar(self, sucursal: Branch) -> Branch:
        self._sesion.add(sucursal)
        return sucursal

    @staticmethod
    def _vivas(consulta: Select[tuple[Branch]], incluir: bool) -> Select[tuple[Branch]]:
        return consulta if incluir else consulta.where(Branch.deleted_at.is_(None))


class PlanRepository:
    """Catalogo comercial. Sin `tenant_id`: es compartido (`RN-MT-09`)."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def listar_activos(self) -> Sequence[Plan]:
        """Los planes publicables, del mas barato al mas caro.

        El `ORDER BY` no es cosmetico. Sin el, PostgreSQL puede devolver las
        filas en cualquier orden, y una grilla de precios que se reordena sola
        entre dos cargas de la pagina no es una grilla de precios.

        Se ordena por precio y no por `code`: el orden comercial es el que el
        cliente espera leer, y alfabeticamente `enterprise` vendria primero.
        """
        consulta = select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_ars)
        return (await self._sesion.execute(consulta)).scalars().all()


class VehicleCatalogRepository:
    """Marcas y modelos. Catalogo compartido: sin `tenant_id` y de solo lectura.

    No tiene metodos de escritura, y no es un pendiente. La base ya niega
    `INSERT`, `UPDATE` y `DELETE` al rol de aplicacion sobre estas tablas
    (migracion `009`); un metodo `agregar()` acá solo serviria para descubrir esa
    negativa en tiempo de ejecucion.
    """

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def listar_marcas(self) -> Sequence[VehicleBrand]:
        """Las marcas publicables, en orden alfabetico.

        Alfabetico y no por `created_at`: quien busca una marca en una lista de
        40 la busca por nombre. El orden de insercion es del seed, no del que
        mira la pantalla.
        """
        consulta = (
            select(VehicleBrand).where(VehicleBrand.is_active.is_(True)).order_by(VehicleBrand.name)
        )
        return (await self._sesion.execute(consulta)).scalars().all()

    async def obtener_marca(self, marca_id: uuid.UUID) -> VehicleBrand | None:
        consulta = select(VehicleBrand).where(
            VehicleBrand.id == marca_id, VehicleBrand.is_active.is_(True)
        )
        return (await self._sesion.execute(consulta)).scalars().first()

    async def listar_modelos_de(self, marca_id: uuid.UUID) -> Sequence[VehicleModel]:
        """Los modelos de una marca, del mas nuevo al mas viejo.

        Por `year_from` descendente y despues por nombre: al cargar stock lo que
        se busca casi siempre es un modelo reciente, y dejarlo al final de una
        lista alfabetica obliga a recorrerla entera.
        """
        consulta = (
            select(VehicleModel)
            .where(VehicleModel.brand_id == marca_id, VehicleModel.is_active.is_(True))
            .order_by(VehicleModel.year_from.desc(), VehicleModel.name)
        )
        return (await self._sesion.execute(consulta)).scalars().all()
