"""Verificacion de las cuotas del plan — C-04, `T-059`.

Los limites de un plan ("hasta 80 vehiculos") no son texto de una landing: son
una verificacion en el camino caliente de cada alta. Si llega despues de que
existan los modulos que debe frenar, hay que agregarla a mano en cada punto de
creacion — y el que se olvide no falla, simplemente deja pasar.

POR QUE ESTE SERVICIO NO SABE CONTAR USUARIOS NI VEHICULOS
───────────────────────────────────────────────────────────
`users` es C-05 y `vehicles` es C-14. Ninguna de las dos tablas existe todavia.

Escribir hoy `SELECT count(*) FROM users` seria codigo que revienta en runtime
contra un esquema que no lo tiene, y "congruente" era justamente lo contrario.
Escribir un stub que devuelva 0 seria peor: la verificacion pasaria siempre y
el dia que `users` naciera, nadie se acordaria de venir a sacarlo.

La salida es que este servicio sepa de PLANES Y LIMITES —que es su tema— y no
de la forma de las tablas ajenas. Cada modulo registra como se cuenta lo suyo
cuando nace:

    limites.registrar(Recurso.BRANCHES, contar_sucursales)   # C-04, aca
    limites.registrar(Recurso.USERS,    contar_usuarios)     # C-05
    limites.registrar(Recurso.VEHICLES, contar_vehiculos)    # C-14

FALLA CERRADO, Y ESTO ES LO MAS IMPORTANTE DEL ARCHIVO
───────────────────────────────────────────────────────
Pedir la cuota de un recurso sin contador registrado **levanta**. No devuelve
"permitido".

Es tentador lo contrario —"si todavia no se como contarlo, dejalo pasar"— y es
exactamente como se pierde un limite de facturacion: C-14 crea `vehicles`, se
olvida de registrar el contador, y el sistema deja cargar vehiculos sin techo
en todos los planes. Nadie abre un ticket por eso. Con el fallo cerrado, el
primer alta de vehiculo revienta en los tests de C-14 y el olvido dura minutos.
"""

from __future__ import annotations

import enum
import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import PlanQuotaExceeded
from app.modules.tenancy.models import Branch, Plan, Tenant

__all__ = ["ContadorNoRegistrado", "PlanLimitsService", "Recurso"]


class Recurso(enum.StrEnum):
    """Lo que un plan puede limitar. El valor viaja en la respuesta de error."""

    USERS = "users"
    VEHICLES = "vehicles"
    BRANCHES = "branches"


class ContadorNoRegistrado(RuntimeError):
    """Se pidio la cuota de un recurso que nadie sabe contar.

    Es un error de programacion, no de datos: significa que un modulo creo su
    tabla y no registro su contador. Por eso es `RuntimeError` y no un
    `DomainError` — no tiene respuesta HTTP, tiene que romper el test.
    """


# Recibe el tenant y devuelve cuantos hay vivos. La sesion la cierra cada
# contador por su cuenta, que es lo que permite que C-05 y C-14 los escriban
# sin tocar este archivo.
Contador = Callable[[AsyncSession, uuid.UUID], Awaitable[int]]

# `max_*` de `Plan` por recurso. Se escribe una vez acá para que agregar un
# recurso nuevo sea una linea y no una cadena de `if`.
_COLUMNA_DE_LIMITE: dict[Recurso, str] = {
    Recurso.USERS: "max_users",
    Recurso.VEHICLES: "max_vehicles",
    Recurso.BRANCHES: "max_branches",
}


async def contar_sucursales(sesion: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Sucursales vivas del tenant.

    NO mira `is_active`: una sucursal cerrada por refaccion sigue existiendo y
    sigue ocupando su lugar en el plan (design.md D-7). Lo que libera lugar es
    la baja, no la inactividad.
    """
    consulta = (
        select(func.count())
        .select_from(Branch)
        .where(Branch.tenant_id == tenant_id, Branch.deleted_at.is_(None))
    )
    return int((await sesion.execute(consulta)).scalar_one())


class PlanLimitsService:
    """Decide si una creacion cabe en el plan del tenant.

    Decide sobre CUOTA, no sobre permiso. Son dos preguntas distintas y las
    responden dos servicios distintos: un usuario puede tener permiso de sobra
    para crear un vehiculo y no caber en el plan. Por eso el rechazo es 402 y
    no 403 — ver design.md D-6.
    """

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion
        self._contadores: dict[Recurso, Contador] = {
            # C-04 registra el unico recurso cuya tabla existe hoy.
            Recurso.BRANCHES: contar_sucursales,
        }

    def registrar(self, recurso: Recurso, contador: Contador) -> None:
        """Declara como se cuenta un recurso. Lo llama el modulo que lo posee."""
        self._contadores[recurso] = contador

    async def assert_can_add_user(self, tenant_id: uuid.UUID) -> None:
        """Un usuario desactivado SIGUE ocupando licencia; uno dado de baja, no."""
        await self._assert_cabe(tenant_id, Recurso.USERS)

    async def assert_can_add_vehicle(self, tenant_id: uuid.UUID) -> None:
        """El limite es de vehiculos EN STOCK, no de vehiculos vendidos en la historia.

        Vender no debe consumir cuota, o el plan se agota solo con el tiempo y
        el cliente no entiende por que.

        ⚠️ CONDICION DE CARRERA ASUMIDA (design.md D-7). Dos altas simultaneas
        con 79 de 80 pueden pasar las dos verificaciones y dejar 81. Cerrarlo
        exige un `SELECT ... FOR UPDATE` sobre `tenants` o una constraint de
        exclusion, y las dos cosas cuestan latencia en el camino caliente de
        TODA creacion del sistema.

        Se asume con el numero a la vista: el desborde maximo es la cantidad de
        altas concurrentes, sobre planes cuyo techo se mide en decenas o
        centenas. El arreglo esta identificado de antemano — el dia que un
        tenant Enterprise cargue por API en paralelo, es ese `FOR UPDATE`.
        """
        await self._assert_cabe(tenant_id, Recurso.VEHICLES)

    async def assert_can_add_branch(self, tenant_id: uuid.UUID) -> None:
        await self._assert_cabe(tenant_id, Recurso.BRANCHES)

    async def _assert_cabe(self, tenant_id: uuid.UUID, recurso: Recurso) -> None:
        contador = self._contadores.get(recurso)
        if contador is None:
            # Falla cerrado. Ver el encabezado: devolver "permitido" acá es como
            # se pierde un limite de facturacion sin que nadie lo note.
            raise ContadorNoRegistrado(
                f"no hay contador registrado para '{recurso.value}': "
                "el modulo que posee ese recurso tiene que llamar a registrar()"
            )

        limite = await self._limite_del_plan(tenant_id, recurso)
        if limite == Plan.SIN_TECHO:
            # `0 = ilimitado` (spec-tecnica 3.3). Leerlo como "cero permitidos"
            # bloquearia entero el plan Enterprise, que es el unico con 0 en
            # `max_vehicles`. Es el modo de fallar mas silencioso de esta tabla.
            return

        usados = await contador(self._sesion, tenant_id)
        if usados >= limite:
            raise PlanQuotaExceeded(recurso=recurso.value, limite=limite, usados=usados)

    async def _limite_del_plan(self, tenant_id: uuid.UUID, recurso: Recurso) -> int:
        """El techo vigente del tenant para ese recurso.

        Un tenant sin plan —`status = 'trial'`, `plan_id IS NULL`— no tiene
        techo declarado. Se trata como sin techo y NO como cero: el trial
        promete "todas las features de Pro por 14 dias", y un trial que no deja
        cargar nada no es un trial.
        """
        columna = getattr(Plan, _COLUMNA_DE_LIMITE[recurso])
        consulta = (
            select(columna)
            .select_from(Tenant)
            .join(Plan, Tenant.plan_id == Plan.id)
            .where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None))
        )
        limite = (await self._sesion.execute(consulta)).scalar_one_or_none()
        return Plan.SIN_TECHO if limite is None else int(limite)
