"""Como se cuentan los usuarios para la cuota del plan — C-05, tarea 4.4.

Vive en `modules/users/` y no en `modules/tenancy/limits.py` por la regla que
ese archivo fija: **el contador lo escribe el modulo que POSEE el recurso**.
`tenancy` sabe que hay un techo; solo `users` sabe que es un usuario vivo.

⚠️ SIN EL `registrar()` DE ABAJO, `assert_can_add_user` LEVANTA. No es un
defecto: C-04 lo dejo fallando cerrado justamente para que este olvido sea
imposible de no notar. Devolver "permitido" cuando no se sabe contar es como se
pierde un limite de facturacion sin que nadie abra un ticket.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenancy.limits import PlanLimitsService, Recurso
from app.modules.users.models import User

__all__ = ["contar_usuarios", "registrar_contador_de_usuarios"]


async def contar_usuarios(sesion: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Usuarios que ocupan licencia en el plan del tenant.

    ⚠️ NO MIRA `status`, Y ESA ES LA DECISION. `D-6` distingue tres estados que
    se confunden facil:

        status = 'inactive'   no puede entrar, SIGUE siendo empleado   ocupa
        deleted_at            se fue de la empresa                     libera
        baja en Keycloak      no puede autenticarse en ningun lado       —

    Contar `inactive` como libre le dejaria a una agencia tener cincuenta
    personas suspendidas en un plan de cinco. Contarlo como ocupado es cobrarle
    por una licencia que efectivamente esta reservada: esa persona vuelve
    cuando se la reactiva, sin invitacion de por medio.

    Mismo criterio que `contar_sucursales` con `is_active`: lo que libera lugar
    es la baja, no la inactividad.
    """
    consulta = (
        select(func.count())
        .select_from(User)
        .where(User.tenant_id == tenant_id, User.deleted_at.is_(None))
    )
    return int((await sesion.execute(consulta)).scalar_one())


def registrar_contador_de_usuarios(limites: PlanLimitsService) -> None:
    """La linea que `D-6` pide, en una funcion para que se pruebe sola."""
    limites.registrar(Recurso.USERS, contar_usuarios)
