"""Reglas de negocio del modulo tenancy — C-04.

LOS DUPLICADOS SE DETECTAN POR LA CONSTRAINT, NO CONSULTANDO ANTES
──────────────────────────────────────────────────────────────────
La forma intuitiva es `SELECT` y despues `INSERT` si no habia nada. Tiene una
carrera: dos altas simultaneas con el mismo CUIT consultan las dos, las dos ven
libre, y las dos insertan — con suerte una revienta igual por el UNIQUE y con
mala suerte el codigo la trata como un error inesperado y devuelve 500.

Aca se intenta el INSERT y se traduce la violacion de UNIQUE. La base es el
unico arbitro que no tiene carrera, y el mensaje que sale distingue CUAL de los
dos identificadores choco: un "ya existe" a secas obliga al usuario a adivinar
cual de los dos campos cambiar.

LA CUOTA SE CONSULTA ANTES DE ESCRIBIR
───────────────────────────────────────
`crear_sucursal` llama a `PlanLimitsService` antes del INSERT. Un limite que se
verifica despues no es un limite: la fila ya esta.

`tenant_id` NUNCA SALE DEL BODY
────────────────────────────────
Los metodos lo reciben como PARAMETRO, separado del schema de entrada. Es lo
que hace que la regla dura 1 se cumpla por construccion y no por disciplina:
para escribir en otro tenant habria que pasarlo explicitamente, y quien lo
haga tiene enfrente la politica RLS con su `WITH CHECK`.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.tenancy.limits import PlanLimitsService
from app.modules.tenancy.models import Branch, Plan, Tenant
from app.modules.tenancy.repository import BranchRepository, TenantRepository
from app.modules.tenancy.schemas import SucursalCrear, TenantCrear

__all__ = ["TenancyService"]

# Nombre de la constraint -> (codigo estable, mensaje). El codigo es lo que el
# cliente usa para reaccionar; el mensaje es para humanos y NO repite el valor
# rechazado, que en el caso del CUIT es dato personal (Ley 25.326).
_CHOQUES: dict[str, tuple[str, str]] = {
    "tenants_cuit_key": ("cuit_duplicado", "ya existe una agencia con ese CUIT"),
    "tenants_slug_key": ("slug_duplicado", "ya existe una agencia con ese identificador"),
}


class TenancyService:
    """Alta, baja y configuracion de agencias y sucursales."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion
        self._agencias = TenantRepository(sesion)
        self._sucursales = BranchRepository(sesion)
        self._limites = PlanLimitsService(sesion)

    # ── Agencias ────────────────────────────────────────────────────────────

    async def crear_agencia(self, datos: TenantCrear) -> Tenant:
        """Da de alta una agencia en trial y sin plan.

        Nace en `trial` porque elegir plan es un paso posterior del onboarding,
        y `plan_id` queda NULL a proposito: forzar un plan ficticio para
        satisfacer un NOT NULL seria peor que un NULL que dice la verdad
        (design.md D-8). Un tenant sin plan se trata como sin techo, que es lo
        que corresponde a un trial.
        """
        agencia = Tenant(
            name=datos.name,
            slug=datos.slug,
            cuit=datos.cuit,  # ya normalizado por el schema
            billing_email=datos.billing_email,
            status="trial",
            timezone=datos.timezone,
            locale=datos.locale,
        )
        self._agencias.agregar(agencia)
        await self._grabar()
        return agencia

    async def asignar_plan(self, tenant_id: uuid.UUID, codigo_de_plan: str) -> Tenant:
        """Pasa la agencia al plan indicado y la deja activa."""
        agencia = await self._agencia_viva(tenant_id)
        plan_id = (
            await self._sesion.execute(select(Plan.id).where(Plan.code == codigo_de_plan))
        ).scalar_one_or_none()
        if plan_id is None:
            raise DomainError("el plan indicado no existe", code="plan_inexistente")

        agencia.plan_id = plan_id
        agencia.status = "active"
        agencia.updated_at = _ahora()
        await self._sesion.flush()
        return agencia

    async def cambiar_estado(self, tenant_id: uuid.UUID, estado: str) -> Tenant:
        """Mueve la agencia por su ciclo comercial.

        `cancelled` NO es lo mismo que dar de baja: una agencia cancelada dejo
        de pagar y sigue existiendo con sus datos: para eso esta `dar_de_baja`,
        que marca `deleted_at`.
        """
        if estado not in {"active", "suspended", "trial", "cancelled"}:
            raise DomainError(f"estado desconocido: {estado}", code="estado_invalido")
        agencia = await self._agencia_viva(tenant_id)
        agencia.status = estado
        agencia.updated_at = _ahora()
        await self._sesion.flush()
        return agencia

    async def dar_de_baja_agencia(self, tenant_id: uuid.UUID) -> Tenant:
        """Baja recuperable. La fila y su historico sobreviven (Principio 3).

        NO libera `slug` ni `cuit`: los UNIQUE son sobre la columna entera.
        Reasignar el CUIT de una agencia dada de baja rompe la trazabilidad
        fiscal de lo que esa agencia facturo.
        """
        agencia = await self._agencia_viva(tenant_id)
        agencia.deleted_at = _ahora()
        agencia.status = "cancelled"
        agencia.updated_at = agencia.deleted_at
        await self._sesion.flush()
        return agencia

    # ── Sucursales ──────────────────────────────────────────────────────────

    async def crear_sucursal(self, tenant_id: uuid.UUID, datos: SucursalCrear) -> Branch:
        """Da de alta una sucursal, si el plan da.

        `tenant_id` llega por PARAMETRO y no dentro de `datos`: el schema de
        entrada ni siquiera declara el campo. Ver el encabezado del modulo.
        """
        await self._limites.assert_can_add_branch(tenant_id)  # antes del INSERT

        sucursal = Branch(
            tenant_id=tenant_id,
            name=datos.name,
            city=datos.city,
            province=datos.province,
            address=datos.address,
            phone=datos.phone,
            business_hours=datos.business_hours,
        )
        self._sucursales.agregar(sucursal)
        await self._grabar()
        return sucursal

    async def configurar_agencia(self, tenant_id: uuid.UUID, datos: object) -> Tenant:
        """Ajusta lo que una agencia puede ajustarse a si misma — tarea 5.10.

        Lo que NO entra por aca lo decide el schema, no este metodo: `cuit` y
        `slug` son identidad, y `plan_id` y `status` los mueven la facturacion y
        la plataforma. Que la restriccion viva en el schema y no en un `if` es
        lo que hace que mandarlos de 422 en vez de ignorarlos en silencio.
        """
        agencia = await self._agencia_viva(tenant_id)

        for campo, valor in datos.model_dump(exclude_unset=True).items():  # type: ignore[attr-defined]
            setattr(agencia, campo, valor)

        await self._grabar()
        return agencia

    async def actualizar_sucursal(
        self, tenant_id: uuid.UUID, sucursal_id: uuid.UUID, datos: object
    ) -> Branch:
        """Edita una sucursal DE ESTA AGENCIA.

        El `tenant_id` va en la consulta y no solo en la politica RLS: son las
        tres capas de la regla dura 1, y la de aplicacion es la unica que
        produce un 404 con sentido en vez de "cero filas afectadas".
        """
        sucursal = await self._sucursales.obtener(tenant_id, sucursal_id)
        if sucursal is None:
            raise DomainError("la sucursal no existe", code="sucursal_inexistente")

        for campo, valor in datos.model_dump(exclude_unset=True).items():  # type: ignore[attr-defined]
            setattr(sucursal, campo, valor)

        await self._grabar()
        return sucursal

    async def dar_de_baja_sucursal(self, tenant_id: uuid.UUID, sucursal_id: uuid.UUID) -> Branch:
        """Baja recuperable de una sucursal. Libera cuota del plan.

        Distinto de `is_active = false`, que es "existe y no opera" y **sigue**
        ocupando cuota (design.md D-7).
        """
        sucursal = await self._sucursales.obtener(tenant_id, sucursal_id)
        if sucursal is None:
            raise DomainError("la sucursal no existe", code="sucursal_inexistente")
        sucursal.deleted_at = _ahora()
        sucursal.updated_at = sucursal.deleted_at
        await self._sesion.flush()
        return sucursal

    # ── Interno ─────────────────────────────────────────────────────────────

    async def _agencia_viva(self, tenant_id: uuid.UUID) -> Tenant:
        agencia = await self._agencias.obtener(tenant_id)
        if agencia is None:
            raise DomainError("la agencia no existe", code="tenant_inexistente")
        return agencia

    async def _grabar(self) -> None:
        """Empuja lo pendiente y traduce el choque de UNIQUE a un error de dominio.

        Sin esta traduccion, un CUIT repetido sale como `IntegrityError` — un
        500 con el SQL adentro. Es un rechazo de negocio perfectamente
        previsible, y quien lo recibe tiene que poder distinguir cual de los dos
        identificadores choco.
        """
        try:
            await self._sesion.flush()
        except IntegrityError as exc:
            codigo, mensaje = _traducir(exc)
            raise DomainError(mensaje, code=codigo) from exc


def _traducir(exc: IntegrityError) -> tuple[str, str]:
    """Mapea la constraint violada a (codigo, mensaje).

    Se busca el NOMBRE de la constraint en el texto del error en vez de mirar
    el valor: el nombre lo fija la migracion y no cambia con los datos, y asi
    el mensaje nunca termina repitiendo el CUIT rechazado.
    """
    texto = str(getattr(exc, "orig", exc))
    for constraint, resultado in _CHOQUES.items():
        if constraint in texto:
            return resultado
    # Una violacion que no sabemos nombrar no se disfraza de duplicado: se deja
    # subir como lo que es. Traducir a ciegas convertiria, por ejemplo, una FK
    # rota en un "ya existe" que manda a mirar el lugar equivocado.
    raise exc


def _ahora() -> dt.datetime:
    return dt.datetime.now(dt.UTC)
