"""Alta, baja y ciclo de vida de las personas de una agencia — C-05, bloque 4.

ESCRIBE EN DOS SISTEMAS, Y EL ORDEN ES LA DECISION
────────────────────────────────────────────────────
`D-5`: primero Keycloak, despues local. No es estilo — es cual de los dos
estados rotos preferimos cuando la operacion se corta a la mitad:

    local primero      una persona `invited` SIN cuenta. Figura invitada, nunca
                       puede entrar, y nadie se entera hasta que reclama.

    Keycloak primero   una cuenta huerfana y deshabilitada, que la reinvitacion
                       reutiliza por email. Recuperable, y no le miente a nadie.

⚠️ HAY UNA SEGUNDA RAZON QUE EL DISEÑO NO MENCIONA: **`users.id` ES el `sub` de
Keycloak** — no existe una columna `keycloak_sub`. Sin la llamada remota no hay
id que insertar. El orden no es preferible: es el unico posible.

No se usa una transaccion distribuida. Dos sistemas, dos escrituras y un orden
elegido para que el fallo caiga del lado recuperable es la solucion
proporcionada al problema; un *saga* aca seria mas maquina de estados que la que
se esta protegiendo.
"""

from __future__ import annotations

import datetime as dt
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.tenancy.limits import PlanLimitsService
from app.modules.tenancy.models import Branch
from app.modules.users.keycloak import ClienteDeKeycloak
from app.modules.users.limites import registrar_contador_de_usuarios
from app.modules.users.models import User, UserBranch
from app.modules.users.repository import UserRepository

__all__ = ["UserService", "UsuarioNoEncontrado"]


class UsuarioNoEncontrado(DomainError):
    """No existe, o es de otra agencia. Las dos dan 404.

    Distinguirlas le confirmaria a un tenant que cierto id existe en otra
    agencia — fuga de informacion por el codigo de estado, sin devolver un dato.
    Mismo criterio que `VehiculoNoEncontrado`.
    """

    status_code = 404

    def __init__(self, detail: str = "la persona no existe") -> None:
        super().__init__(detail, code="user_not_found")


class UserService:
    """Operaciones sobre las personas de UNA agencia.

    El `tenant_id` se recibe al construir y viene del token. Ningun metodo lo
    toma por parametro: quien tiene el servicio ya decidio de que agencia habla.
    """

    def __init__(
        self, sesion: AsyncSession, tenant_id: uuid.UUID, keycloak: ClienteDeKeycloak
    ) -> None:
        self._sesion = sesion
        self._tenant_id = tenant_id
        self._keycloak = keycloak
        self._repositorio = UserRepository(sesion, tenant_id)
        self._limites = PlanLimitsService(sesion)

        # Tarea 4.4. Sin esta linea `assert_can_add_user` levanta
        # `ContadorNoRegistrado`: C-04 lo dejo fallando cerrado justamente para
        # que el olvido sea imposible de no notar.
        registrar_contador_de_usuarios(self._limites)

    async def invitar(self, *, email: str, nombre: str, rol: str) -> User:
        """Crea la cuenta y el espejo. Devuelve la fila local.

        ⚠️ LA CUOTA SE MIRA ANTES DE LA PRIMERA ESCRITURA, y no despues. Si se
        verificara al final, cada intento con el plan lleno dejaria una cuenta
        huerfana en Keycloak — el rechazo seria correcto y el efecto colateral
        no.
        """
        await self._limites.assert_can_add_user(self._tenant_id)

        dormida = await self._dada_de_baja_con_ese_email(email)
        if dormida is not None:
            return await self._resucitar(dormida, nombre=nombre, rol=rol)

        sub = await self._keycloak.crear_usuario(
            email=email, nombre=nombre, tenant_id=self._tenant_id, rol=rol
        )

        persona = User(
            id=uuid.UUID(sub),
            tenant_id=self._tenant_id,
            email=email,
            full_name=nombre,
            role=rol,
            status="invited",
        )
        self._sesion.add(persona)
        await self._sesion.flush()

        await self._keycloak.pedir_que_fije_contrasenia(sub)
        return persona

    async def aceptar_invitacion(self, user_id: uuid.UUID) -> User:
        """`D-5` paso 4: la persona ya fijo su contraseña EN KEYCLOAK.

        Este metodo solo mueve el estado local de `invited` a `active`. No
        recibe ni ve una contraseña — `ADR-026` §4 le saco a
        `accept-invitation` la unica razon por la que habria recibido una.

        ⚠️ ES IDEMPOTENTE A PROPOSITO. El doble clic sobre el mail de
        invitacion va a pasar; si la segunda vez levantara, la persona veria un
        error habiendo hecho todo bien.
        """
        persona = await self._viva(user_id)
        if persona.status != "active":
            persona.status = "active"
            await self._sesion.flush()
        return persona

    async def desactivar(self, user_id: uuid.UUID) -> User:
        """`D-6`: no puede entrar, SIGUE siendo empleado y SIGUE ocupando cupo.

        Se deshabilita tambien en Keycloak. Dejarla habilitada alla convertiria
        la suspension en una marca decorativa: la persona seguiria pudiendo
        autenticarse y solo nuestra aplicacion la frenaria.
        """
        persona = await self._viva(user_id)
        await self._keycloak.deshabilitar(str(persona.id))
        persona.status = "inactive"
        await self._sesion.flush()
        return persona

    async def dar_de_baja(self, user_id: uuid.UUID) -> User:
        """Se fue de la empresa: libera cupo y libera el email (`D-6`).

        ⚠️ EN KEYCLOAK SE DESHABILITA, NO SE BORRA. Borrar liberaria el email
        para otra cuenta y romperia la trazabilidad de que hizo esa persona —
        mismo criterio que C-04 le aplico al CUIT de una agencia dada de baja.

        `user_branches` se CONSERVA (`D-7`): saber en que sucursal trabajaba
        alguien es parte del historico, y ademas es lo que hace que una
        reincorporacion recupere sus asignaciones sin tocar nada.
        """
        persona = await self._viva(user_id)
        await self._keycloak.deshabilitar(str(persona.id))
        persona.deleted_at = _ahora()
        await self._sesion.flush()
        return persona

    async def asignar_sucursales(
        self, user_id: uuid.UUID, asignaciones: list[tuple[uuid.UUID, bool]]
    ) -> None:
        """Agrega o actualiza las sucursales de una persona. **No borra ninguna.**

        ⚠️ LA PRIMERA VERSION BORRABA Y REESCRIBIA, Y ESTABA MAL POR DOS LADOS.
        Lo encontro el rol de aplicacion: `mitutu` tiene `SELECT`, `INSERT` y
        `UPDATE` sobre `user_branches` y **no tiene `DELETE`** — no es un grant
        olvidado, es la regla dura 3 (soft delete universal) hecha cumplir por
        la base. El test pasaba porque usaba la sesion del PROPIETARIO, que si
        puede; el primer camino que llego por la API se choco con el permiso.

        Y `D-7` decia lo mismo desde el diseño: `user_branches` se conserva,
        porque saber en que sucursal trabajaba alguien es parte del historico.
        Borrar la fila al reasignar tiraba justamente ese dato.

        ⚠️ LAS PRINCIPALES SE DESMARCAN ANTES, TODAS. La base tiene
        `ux_user_branches_principal UNIQUE (user_id) WHERE is_primary`, y una
        constraint RECHAZA — no desmarca. Sin este `UPDATE` previo, mover la
        principal revienta con un `duplicate key` que no le explica nada a quien
        lo ve.

        ⚠️ DESASIGNAR NO EXISTE TODAVIA, y es deliberado no improvisarlo:
        `user_branches` no tiene `deleted_at`, asi que quitarle una sucursal a
        alguien conservando el historico necesita una migracion y una decision
        sobre que significa "ya no trabaja ahi" contra "nunca trabajo ahi".
        Queda anotado, no resuelto a medias.
        """
        persona = await self._viva(user_id)

        for sucursal_id, _ in asignaciones:
            if not await self._sucursal_propia(sucursal_id):
                # El agujero clasico —las dos puntas protegidas y el vinculo no—
                # ya lo tapa la FK compuesta contra `(id, tenant_id)`. Esto es
                # para que el rechazo se parezca a un error de negocio y no a un
                # `IntegrityError` con un mensaje de PostgreSQL adentro.
                raise DomainError("la sucursal no existe en esta agencia", code="branch_not_found")

        await self._sesion.execute(
            sa.update(UserBranch)
            .where(UserBranch.user_id == persona.id, UserBranch.tenant_id == self._tenant_id)
            .values(is_primary=False)
        )
        await self._sesion.flush()

        ya_asignadas = set(
            (
                await self._sesion.execute(
                    sa.select(UserBranch.branch_id).where(
                        UserBranch.user_id == persona.id,
                        UserBranch.tenant_id == self._tenant_id,
                    )
                )
            )
            .scalars()
            .all()
        )

        for sucursal_id, principal in asignaciones:
            if sucursal_id in ya_asignadas:
                await self._sesion.execute(
                    sa.update(UserBranch)
                    .where(
                        UserBranch.user_id == persona.id,
                        UserBranch.branch_id == sucursal_id,
                    )
                    .values(is_primary=principal)
                )
            else:
                self._sesion.add(
                    UserBranch(
                        user_id=persona.id,
                        branch_id=sucursal_id,
                        tenant_id=self._tenant_id,
                        is_primary=principal,
                    )
                )

        await self._sesion.flush()

    # ── Interno ─────────────────────────────────────────────────────────────

    async def _sucursal_propia(self, sucursal_id: uuid.UUID) -> bool:
        consulta = (
            sa.select(sa.func.count())
            .select_from(Branch)
            .where(
                Branch.id == sucursal_id,
                Branch.tenant_id == self._tenant_id,
                Branch.deleted_at.is_(None),
            )
        )
        return int((await self._sesion.execute(consulta)).scalar_one()) == 1

    async def _dada_de_baja_con_ese_email(self, email: str) -> User | None:
        """La fila dormida de alguien que se fue y podria estar volviendo.

        El indice `ux_users_tenant_email` es parcial por `deleted_at`, asi que
        el email quedo libre y un `INSERT` nuevo pasaria. Lo que NO pasaria es
        la clave primaria: `users.id` es el `sub`, y rehabilitar la cuenta de
        Keycloak devuelve el MISMO `sub`. Una fila nueva chocaria contra la
        vieja.

        Por eso se resucita en vez de insertar. Ver la tarea 4.8, corregida.
        """
        consulta = sa.select(User).where(
            User.tenant_id == self._tenant_id,
            sa.func.lower(User.email) == sa.func.lower(email),
            User.deleted_at.is_not(None),
        )
        return (await self._sesion.execute(consulta)).scalars().first()

    async def _resucitar(self, persona: User, *, nombre: str, rol: str) -> User:
        """Vuelve a la vida a quien se habia ido, con su id y sus sucursales.

        El nombre y el rol se toman de la INVITACION NUEVA, no de los viejos:
        quien vuelve puede volver a otro puesto, y la invitacion es la que sabe
        a cual. Lo que no se toca son las asignaciones de sucursal — cuelgan de
        `user_id`, que no cambia, asi que vuelven solas (`D-7`).
        """
        await self._keycloak.rehabilitar(str(persona.id))

        persona.deleted_at = None
        persona.full_name = nombre
        persona.role = rol
        persona.status = "invited"
        await self._sesion.flush()

        await self._keycloak.pedir_que_fije_contrasenia(str(persona.id))
        return persona

    async def _viva(self, user_id: uuid.UUID) -> User:
        persona = await self._repositorio.obtener(user_id)
        if persona is None:
            raise UsuarioNoEncontrado
        return persona


def _ahora() -> dt.datetime:
    return dt.datetime.now(dt.UTC)
