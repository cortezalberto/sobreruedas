"""Acceso a datos de identidad — C-05.

DOS FILTROS EN TODA CONSULTA ORDINARIA
───────────────────────────────────────
`tenant_id` explicito **y** `deleted_at IS NULL`. El primero es la tercera capa
de la regla dura 1 —la politica RLS ya filtra, y el filtro explicito se escribe
igual porque una sola capa no es aislamiento—. El segundo es el Principio 3: una
persona dada de baja no aparece salvo que se la pida a proposito.

Mismo contrato que `tenancy/repository.py`, y se copia el criterio en vez de
factorizarlo: un repositorio base compartido es donde despues alguien agrega un
metodo sin filtro y lo hereda todo el sistema.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenancy.models import Branch
from app.modules.users.models import User, UserBranch

__all__ = ["UserRepository"]


class UserRepository:
    """Consultas de `users`, siempre acotadas a un tenant.

    El `tenant_id` se recibe al construir y viene del token. Ningun metodo lo
    toma por parametro: quien tiene el repositorio ya decidio de que agencia
    habla.
    """

    def __init__(self, sesion: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._sesion = sesion
        self._tenant_id = tenant_id

    def _vivos(self, consulta: sa.Select[tuple[User]]) -> sa.Select[tuple[User]]:
        return consulta.where(User.tenant_id == self._tenant_id, User.deleted_at.is_(None))

    async def obtener(self, user_id: uuid.UUID) -> User | None:
        """Una persona por su id — que es el `sub` de su token."""
        return (
            await self._sesion.execute(self._vivos(sa.select(User)).where(User.id == user_id))
        ).scalar_one_or_none()

    async def corregir_email(self, persona: User, email_del_token: str | None) -> bool:
        """`D-1`: si el email del token difiere del espejo, gana el token.

        Devuelve si hubo correccion, que sirve para no escribir de mas: el caso
        normal es que coincidan, y un UPDATE incondicional en cada lectura del
        perfil escribiria una fila por request sin cambiar un solo dato.

        ⚠️ CORRIGE EL EMAIL Y NADA MAS. Rol, agencia y sucursales son dominio de
        NEGOCIO —Keycloak no sabe que es una sucursal— y el token trae el rol
        que la persona tenia cuando se emitio. Arrastrarlo aca desharia una
        degradacion de permisos sola en el proximo request, con la fuente
        equivocada mandando sobre la buena.

        ⚠️ UN TOKEN SIN `email` NO BORRA EL DEL ESPEJO. El claim viene del client
        scope homonimo, que es un default del realm y no una garantia: si falta,
        no hay con que corregir. Pisarlo con `None` cambiaria un espejo
        desactualizado —el problema que `D-1` resuelve— por uno vacio, que es
        peor.
        """
        if not email_del_token or email_del_token == persona.email:
            return False

        persona.email = email_del_token
        await self._sesion.flush()
        return True

    async def listar(self, *, incluir_dadas_de_baja: bool = False) -> Sequence[User]:
        """El padron de la agencia.

        `incluir_dadas_de_baja` es explicito y por palabra clave: pedir a los
        muertos tiene que leerse en el sitio de la llamada, no adivinarse.
        """
        consulta = sa.select(User).where(User.tenant_id == self._tenant_id)
        if not incluir_dadas_de_baja:
            consulta = consulta.where(User.deleted_at.is_(None))
        return (await self._sesion.execute(consulta.order_by(User.full_name))).scalars().all()

    async def sucursales_de(self, user_id: uuid.UUID) -> Sequence[tuple[Branch, bool]]:
        """Las sucursales asignadas y si cada una es la principal.

        Devuelve una lista, que puede estar vacia: una persona recien invitada no
        tiene ninguna, y eso NO es un error — `GET /auth/me` tiene que responder
        igual. Es el caso que la tarea 5.4 pide afirmar.

        Se filtra por `tenant_id` en las dos tablas aunque el JOIN ya lo ataria:
        la politica RLS de cada una compara contra esa columna, y escribirlo
        explicito mantiene las tres capas independientes.
        """
        consulta = (
            sa.select(Branch, UserBranch.is_primary)
            .join(UserBranch, UserBranch.branch_id == Branch.id)
            .where(
                UserBranch.user_id == user_id,
                UserBranch.tenant_id == self._tenant_id,
                Branch.tenant_id == self._tenant_id,
                Branch.deleted_at.is_(None),
            )
            # La principal primero: es la que la interfaz muestra por defecto.
            .order_by(UserBranch.is_primary.desc(), Branch.name)
        )
        return [(fila[0], fila[1]) for fila in (await self._sesion.execute(consulta))]
