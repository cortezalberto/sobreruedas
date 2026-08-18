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

from app.modules.tenancy.models import Branch, Tenant

__all__ = ["BranchRepository", "TenantRepository"]


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
