"""Autorizacion — el catalogo de roles y su resolucion.

`T-014`, bloque 6 de `C-02`. Gobernanza CRITICA: este modulo decide quien puede
hacer que en todo el sistema.

La forma de este archivo la fija `ADR-024` §2, y es lo primero que hay que
entender de el: **los roles no son una lista de cuatro**. Son dos espacios
disjuntos, con superficies de API distintas y ningun endpoint donde compitan.

    Espacio de tenant  /api/v1/...     Espacio de plataforma  /admin/api/v1/...
    |-- manager                        `-- super_admin
    |-- salesperson
    `-- admin_staff

Modelarlos como un solo enum de cuatro valores es el error de forma que
arrastraba `knowledge-base/03_actores_y_roles.md`, y la causa —dice el ADR— de
casi toda la confusion sobre RBAC en el corpus. Dos tipos separados hacen que el
error no se pueda escribir: no hay como pasarle un `super_admin` a algo que
espera un rol de tenant sin que el tipo lo rechace antes de correr.

`ADR-017` §2 lo respalda desde el modelo de datos: `super_admin` no es un cuarto
valor de `user_role_enum`, es un actor que vive en su propia tabla, sin
`tenant_id` y exenta de RLS.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.auth import Sujeto, SujetoActual
from app.core.errors import (
    AlcanceInsuficiente,
    PermisoInsuficiente,
    RolInsuficiente,
    TransicionNoPermitida,
)

__all__ = [
    "CAMPOS_DE_PERFIL",
    "CAMPOS_DE_VEHICULO_PARA_VENDEDOR",
    "CAMPOS_DE_VEHICULO_SIN_COSTO",
    "CAMPOS_PUBLICOS_DE_USUARIO",
    "EQUIVALENCIA_EN_GLOSARIO",
    "MATRIZ_DE_PLATAFORMA",
    "MATRIZ_DE_TENANT",
    "PERMISOS_DECLARADOS",
    "PERMISOS_DE_PLATAFORMA",
    "PERMISOS_DE_TENANT",
    "Alcance",
    "AlcanceInsuficiente",
    "Concesion",
    "ExigePermiso",
    "ExigeRol",
    "DeclaracionVacia",
    "Espacio",
    "EspacioAmbiguo",
    "EspaciosMezclados",
    "Rol",
    "TransicionNoPermitida",
    "RolDePlataforma",
    "RolDeTenant",
    "PermisoNoDeclarado",
    "RolDesconocido",
    "recortar",
    "require_permission",
    "require_role",
    "rol_de_plataforma",
    "rol_de_tenant",
    "verificar_alcance",
    "verificar_transicion",
]


class RolDeTenant(StrEnum):
    """Los tres roles que operan bajo `/api/v1` — `ADR-017` §1.

    Son los tres valores de `user_role_enum` y no hay un cuarto. Sin herencia
    entre ellos (`ADR-024` §5): `manager` NO contiene a `salesperson`.
    """

    MANAGER = "manager"
    SALESPERSON = "salesperson"
    ADMIN_STAFF = "admin_staff"


class RolDePlataforma(StrEnum):
    """El unico rol que opera bajo `/admin/api/v1` — `ADR-017` §2.

    Un enum de un solo valor parece de mas hoy. No lo es: le da al espacio de
    plataforma el mismo tipo que al de tenant, y es lo que permite que la
    separacion de `ADR-024` §2 la sostenga el sistema de tipos en vez de la
    disciplina de quien escribe.
    """

    SUPER_ADMIN = "super_admin"


# La equivalencia con el glosario constitucional — `ADR-017` §3.
#
# Vive aca, junto al catalogo, y no en la capa de presentacion: el glosario es
# N0 y la traduccion es parte de la definicion del rol, no una decoracion de la
# interfaz. Que este al lado del enum es lo que hace que agregar un rol sin su
# termino en espanol se note.
EQUIVALENCIA_EN_GLOSARIO: dict[RolDeTenant | RolDePlataforma, str] = {
    RolDeTenant.MANAGER: "Gerente",
    RolDeTenant.SALESPERSON: "Vendedor",
    RolDeTenant.ADMIN_STAFF: "Administrativo",
    RolDePlataforma.SUPER_ADMIN: "Super Admin",
}


class RolDesconocido(Exception):
    """Un rol que no esta en el catalogo del espacio que se consulto.

    NO hereda de `AuthenticationError` ni de la familia de errores HTTP a
    proposito. Esto no es una peticion que se rechaza: es una declaracion mal
    escrita en el codigo, o un token con un rol que el sistema no reconoce. La
    primera tiene que romper el arranque; la segunda tiene que rechazarse en el
    borde. Ninguna de las dos es "este usuario no puede".
    """

    def __init__(self, nombre: str, *catalogos: type[StrEnum]) -> None:
        conocidos = ", ".join(sorted(rol.value for catalogo in catalogos for rol in catalogo))
        donde = " ni ".join(catalogo.__name__ for catalogo in catalogos)
        super().__init__(
            f"el rol {nombre!r} no esta en el catalogo de {donde}; "
            f"los conocidos son: {conocidos}"
        )
        self.nombre = nombre


def rol_de_tenant(nombre: str) -> RolDeTenant:
    """El rol de tenant con ese nombre exacto, o `RolDesconocido`.

    Exacto quiere decir exacto: ni se recortan espacios ni se normalizan
    mayusculas. Una coincidencia aproximada es una decision de autorizacion
    tomada por una heuristica de cadenas, y no hay forma de auditar eso.

    Devolver `None` ante lo desconocido seria peor que inutil: quien llame se
    olvida de comprobarlo una vez y el rol invalido pasa a valer lo que valga el
    caso degenerado de mas abajo — "nadie" o "cualquiera", segun el dia.
    """
    try:
        return RolDeTenant(nombre)
    except ValueError as exc:
        raise RolDesconocido(nombre, RolDeTenant) from exc


def rol_de_plataforma(nombre: str) -> RolDePlataforma:
    """El rol de plataforma con ese nombre exacto, o `RolDesconocido`.

    Que `rol_de_tenant("super_admin")` falle y esta lo resuelva no es una
    asimetria: es `ADR-024` §2 funcionando. El rol existe; el espacio es otro.
    """
    try:
        return RolDePlataforma(nombre)
    except ValueError as exc:
        raise RolDesconocido(nombre, RolDePlataforma) from exc


# El tipo de un rol, cualquiera sea su espacio. Sirve para las firmas; NO sirve
# para mezclarlos: `require_role` rechaza una declaracion que toque los dos.
Rol = RolDeTenant | RolDePlataforma


class Espacio(StrEnum):
    """Cual de las dos superficies de API — `ADR-024` §2."""

    TENANT = "tenant"
    """`/api/v1/...` — lo deciden los tres roles de tenant."""

    PLATAFORMA = "plataforma"
    """`/admin/api/v1/...` — lo decide `super_admin`, en exclusiva."""


class EspaciosMezclados(Exception):
    """Una declaracion que admite roles de los dos espacios a la vez.

    `ADR-024` §2: no hay un solo endpoint donde los cuatro roles compitan. Una
    operacion o vive bajo `/api/v1` —y entonces la deciden los tres roles de
    tenant— o vive bajo `/admin/api/v1` y la decide `super_admin`. Admitir
    ambos describe una superficie que no existe.
    """


class DeclaracionVacia(Exception):
    """`require_role()` sin ningun rol.

    Es la ambiguedad exacta que la tarea 6.3 manda prohibir. Un conjunto vacio
    de admitidos se lee como "nadie" —ninguna pertenencia es cierta— o como
    "cualquiera" —ninguna condicion falla—, y las dos lecturas salen de escribir
    la comprobacion de una forma o de la otra. Elegir una en silencio significa
    que el sentido de un endpoint depende de un detalle de implementacion.
    """


def _resolver(rol: Rol | str) -> Rol:
    """Un rol declarado, resuelto contra los dos catalogos.

    Se acepta el `str` porque una declaracion escrita a mano es lo normal, y
    porque es justamente ahi donde entra el error que 6.3 persigue. Un enum ya
    resuelto pasa tal cual: no hay nada que validar en algo que el tipo garantiza.
    """
    if isinstance(rol, RolDeTenant | RolDePlataforma):
        return rol
    try:
        return rol_de_tenant(rol)
    except RolDesconocido:
        pass
    try:
        return rol_de_plataforma(rol)
    except RolDesconocido:
        raise RolDesconocido(rol, RolDeTenant, RolDePlataforma) from None


class ExigeRol:
    """La dependency que exige uno de estos roles.

    Es una clase y no un cierre para que la declaracion sea INSPECCIONABLE: la
    verificacion automatica de la tarea 6.9 recorre las rutas realmente
    expuestas y necesita leer que exige cada una. Un cierre guarda lo mismo en
    su `__closure__`, pero leerlo desde afuera es hurgar en un detalle de
    implementacion, y una verificacion que hurga se rompe sola.
    """

    def __init__(self, admitidos: frozenset[Rol]) -> None:
        self.admitidos = admitidos
        self.espacio = (
            Espacio.TENANT if isinstance(next(iter(admitidos)), RolDeTenant) else Espacio.PLATAFORMA
        )
        self._valores = frozenset(rol.value for rol in admitidos)

    async def __call__(self, sujeto: SujetoActual) -> Sujeto:
        # Se comparan los VALORES y no los miembros: `sujeto.role` viene del
        # token como `str`, y aunque un `StrEnum` es igual a su cadena, no
        # comparte su hash — la pertenencia a un conjunto de miembros daria
        # falso siempre, y denegaria a todo el mundo en silencio.
        if sujeto.role not in self._valores:
            raise RolInsuficiente
        return sujeto


def require_role(*roles: Rol | str) -> ExigeRol:
    """Exige que el sujeto tenga uno de estos roles.

        @app.get("/x", dependencies=[Depends(require_role(RolDeTenant.MANAGER))])

    TODO lo que puede estar mal en la declaracion se detecta ACA, al construir
    la dependency —o sea al importar el modulo que la usa, o sea al arrancar la
    aplicacion—, y no cuando llega la primera peticion. Es la exigencia de la
    tarea 6.3, y no es una preferencia de estilo: un endpoint mal declarado que
    solo falla al ser invocado se descubre en produccion, y se descubre por el
    lado que mas duela de los dos —el que deja pasar.

    Sin herencia (`ADR-024` §5): los admitidos se enumeran uno por uno. Que
    `manager` sea "mas" que `salesperson` en la intuicion de cualquiera no lo
    vuelve un superconjunto aca.
    """
    admitidos = frozenset(_resolver(rol) for rol in roles)

    if not admitidos:
        raise DeclaracionVacia(
            "require_role() sin roles no dice si admite a nadie o a cualquiera; "
            "enumera los admitidos"
        )

    espacios = {type(rol) for rol in admitidos}
    if len(espacios) > 1:
        nombres = ", ".join(sorted(espacio.__name__ for espacio in espacios))
        raise EspaciosMezclados(
            f"la declaracion toca dos espacios a la vez ({nombres}); "
            "ADR-024 §2 los define disjuntos"
        )

    return ExigeRol(admitidos)


# ═════════════════════════════════════════════════════════════════════════════
# La matriz — transcripcion de `ADR-024` §6 y §7
#
# COMO SE LEE
# ───────────
# Un permiso se identifica con `recurso:accion` en ingles (`ADR-024` §3). Cada
# par (rol, permiso) declara un alcance y, opcionalmente, un conjunto de campos.
#
#   - Si el permiso NO figura entre las celdas de un rol, ese rol NO lo tiene.
#     La ausencia es la denegacion; no existe un valor "denegado" (§3 y §5).
#   - Sin herencia: `manager` no contiene a `salesperson`. Cada celda se enumera.
#
# LO QUE ESTA DECLARACION ADELANTA AL CODIGO
# ───────────────────────────────────────────
# La mayoria de estos endpoints todavia no existe. Es deliberado: `ADR-024` §8
# dice que el change que traiga cada modulo debe agregar sus filas ANTES de
# exponer el endpoint. Declarar de mas no abre nada —un permiso sin endpoint no
# se puede ejercer—, mientras que exponer sin declarar es lo que la verificacion
# automatica de la tarea 6.9 detecta.
#
# DE LOS ENDPOINTS A LAS CLAVES
# ─────────────────────────────
# `ADR-024` §6 tabula por ENDPOINT y §3 exige claves `recurso:accion`. La
# traduccion se hace fila por fila y una fila puede abrirse en varias claves
# cuando sus celdas difieren por rol. El caso mas claro es Stock: el comentario
# de `modules/stock/router.py` anticipaba `vehicles:write` para crear, editar y
# cambiar de estado, y eso NO se puede transcribir — el `salesperson` tiene tres
# celdas distintas para esas tres operaciones (denegado / `all` con campos /
# `own`). Colapsarlas le concederia la creacion. Se abren.
# ═════════════════════════════════════════════════════════════════════════════


class Alcance(StrEnum):
    """Los tres valores del eje — `ADR-024` §3, enmendado por `ADR-033`."""

    ALL = "all"
    """Todos los registros del tenant."""

    OWN = "own"
    """Solo los asignados: `recurso.assigned_user_id == sujeto.user_id`, evaluado
    EN EL MOMENTO de la peticion (`ADR-024` §4). Crear no da acceso permanente.
    """

    SELF = "self"
    """Solo el propio sujeto: `recurso.id == sujeto.user_id` (`ADR-033`).

    Distinto de `OWN` y no un caso suyo: un usuario no esta asignado a nadie.
    """


@dataclass(frozen=True)
class Concesion:
    """Lo que un rol obtiene sobre un permiso.

    `campos is None` significa SIN restriccion, no "ningun campo". Es la
    distincion que hace que un conjunto vacio nunca aparezca por descuido: si
    alguien escribe `frozenset()`, la operacion no toca ningun campo y eso se
    nota enseguida, en vez de comportarse como si no hubiera restriccion.
    """

    alcance: Alcance
    campos: frozenset[str] | None = None
    transiciones: frozenset[tuple[str, str]] | None = None
    """Pares `(desde, hasta)` admitidos — `ADR-034`. `None` es SIN restriccion.

    Los estados viajan como `str` y no como el enum del dominio porque `core/`
    no depende de `modules/`. Un test compara los pares declarados contra
    `EstadoDeVehiculo` para que la cadena no envejezca sola: un estado renombrado
    dejaria el par apuntando a la nada, y eso denegaria de mas en silencio.
    """


class PermisoNoDeclarado(Exception):
    """Se exigio un permiso que ninguna celda de ninguna matriz concede.

    Se levanta al DECLARAR, y esa es la unica forma de que "denegar por defecto"
    signifique algo. Denegar por defecto es la respuesta correcta cuando un rol
    concreto no tiene una celda; aplicado tambien a los permisos inexistentes se
    vuelve una tapadera: `vehicles:raed` denegaria a todo el mundo y el endpoint
    pareceria estar bien puesto hasta que alguien reporte que no puede entrar.
    """


# ── Conjuntos de campos, nombrados una vez ───────────────────────────────────

CAMPOS_DE_PERFIL = frozenset({"full_name", "phone", "avatar_url", "notification_preferences"})
"""`[perfil]` de `ADR-024` §6 — lo que un usuario puede editarse a si mismo.

Privilegiados y NUNCA autoeditables: `role`, `status`, `tenant_id`, `email` y la
asignacion de sucursales. `email` esta del lado privilegiado porque es el
identificador contra Keycloak (`ADR-007`), y escribirlo desde la API abriria un
camino sobre la identidad que la regla dura 2 mantiene fuera de la aplicacion.

⚠️ `notification_preferences` es el unico nombre que el ADR no da como columna
—dice "preferencias de notificacion"—. La tabla `users` llega en `C-05`; si al
modelarla el nombre resulta otro, se corrige aca y no en el endpoint.
"""

CAMPOS_PUBLICOS_DE_USUARIO = frozenset({"id", "full_name", "role", "branches"})
"""`[id, nombre, rol, sucursales]` de §6, con los nombres de columna.

La lectura del padron por `salesperson` y `admin_staff` no tiene fuente en el
corpus: `ADR-024` la concede acotada porque sin ella no se puede poblar ningun
selector de asignacion.
"""

CAMPOS_DE_VEHICULO_SIN_COSTO = frozenset(
    {
        "acquired_at",
        "assigned_user_id",
        "body_type",
        "branch_id",
        "brand_id",
        "chassis_number",
        "color",
        "created_at",
        "description",
        "domain_plate",
        "features",
        "fuel_type",
        "id",
        "mileage_km",
        "model_id",
        "price_ars",
        "price_usd",
        "sold_at",
        "status",
        "tenant_id",
        "transmission",
        "version_id",
        "year",
    }
)
"""`RN-ST-12` — todo lo que el `salesperson` lee de un vehiculo.

`ADR-024` §6 escribe la regla como una EXCLUSION (`acquisition_cost_ars` ❌) y
§3 modela el eje como una lista blanca. Se transcribe como lista blanca, que es
la forma que denega por defecto: una columna nueva no la ve el vendedor hasta
que alguien la agregue acá a proposito.

Es, campo por campo, el esquema `VehiculoSalida` que los endpoints ya devuelven
—y un test lo compara contra el esquema para que la copia no se despegue—. No
se importa el esquema: `core/` no depende de `modules/`.
"""

CAMPOS_DE_VEHICULO_PARA_VENDEDOR = frozenset({"internal_notes", "assigned_user_id"})
"""Lo unico que el `salesperson` edita de un vehiculo — `ADR-024` §6.

Su alcance es `all` y NO `own`: `12_seguridad` es explicito en que lee todos los
vehiculos del tenant, y la autoasignacion (`assigned_user_id`) seria imposible
si solo pudiera tocar los que ya tiene.

⚠️ `internal_notes` todavia no es una columna del modelo (llega con `C-14`).
"""

# Azucar para las celdas sin restriccion de campos, que son la mayoria.
_TODO = Concesion(Alcance.ALL)
_PROPIOS = Concesion(Alcance.OWN)
_UNO_MISMO = Concesion(Alcance.SELF)


MATRIZ_DE_TENANT: dict[RolDeTenant, dict[str, Concesion]] = {
    # ── manager ≡ Gerente ────────────────────────────────────────────────────
    RolDeTenant.MANAGER: {
        # Auth — `self` y no `own` (`ADR-033`): nadie opera la sesion de otro.
        "auth:logout": _UNO_MISMO,
        "auth:read_me": _UNO_MISMO,
        "auth:enable_mfa": _UNO_MISMO,
        "auth:verify_mfa": _UNO_MISMO,
        # Tenancy y sucursales
        "tenants:read": _TODO,
        "tenants:update": _TODO,
        "tenants:complete_onboarding": _TODO,
        "branches:read": _TODO,
        "branches:create": _TODO,
        "branches:update": _TODO,
        "branches:deactivate": _TODO,
        # Usuarios
        "users:read": _TODO,
        "users:invite": _TODO,
        "users:update": _TODO,
        "users:deactivate": _TODO,
        "users:assign_branches": _TODO,
        # Stock
        "vehicles:read": _TODO,
        "vehicles:price_suggestion": _TODO,
        "vehicles:create": _TODO,
        "vehicles:update": _TODO,
        "vehicles:change_status": _TODO,
        "vehicles:archive": _TODO,
        "vehicles:import": _TODO,
        "vehicle_photos:create": _TODO,
        "vehicle_photos:delete": _TODO,
        "vehicle_photos:reorder": _TODO,
        "catalog:read": _TODO,
        # Publishing
        "publications:read": _TODO,
        "publications:republish": _TODO,
        # CRM
        "leads:read": _TODO,
        "leads:create": _TODO,
        "leads:update": _TODO,
        "leads:change_stage": _TODO,
        "leads:assign": _TODO,
        "leads:close": _TODO,
        "activities:read": _TODO,
        "activities:create": _TODO,
        "activities:update": _TODO,
        "contacts:read": _TODO,
        "contacts:create": _TODO,
        "contacts:update": _TODO,
        "contacts:merge": _TODO,
        "contacts:forget": _TODO,
        "pipeline_stages:read": _TODO,
        "pipeline_stages:write": _TODO,
        "loss_reasons:read": _TODO,
        "loss_reasons:write": _TODO,
        "crm_dashboard:read": _TODO,
        # Communication
        "conversations:read": _TODO,
        "conversations:create": _TODO,
        "conversations:mark_read": _TODO,
        "conversations:close": _TODO,
        "conversations:assign": _TODO,
        "conversations:stream": _TODO,
        "messages:read": _TODO,
        "messages:create": _TODO,
        "whatsapp_templates:read": _TODO,
        "whatsapp_templates:create": _TODO,
        "whatsapp_templates:sync": _TODO,
    },
    # ── salesperson ≡ Vendedor ───────────────────────────────────────────────
    RolDeTenant.SALESPERSON: {
        "auth:logout": _UNO_MISMO,
        "auth:read_me": _UNO_MISMO,
        "auth:enable_mfa": _UNO_MISMO,
        "auth:verify_mfa": _UNO_MISMO,
        # Tenancy — lee, no escribe. `branches:read` es una de las celdas ⚠ del
        # ADR: sin fuente, concedida porque sin ella no se puede ni mostrar a
        # que sucursal pertenece el usuario.
        "tenants:read": _TODO,
        "branches:read": _TODO,
        # Usuarios — el padron acotado, y su propio perfil.
        "users:read": Concesion(Alcance.ALL, CAMPOS_PUBLICOS_DE_USUARIO),
        "users:update": Concesion(Alcance.SELF, CAMPOS_DE_PERFIL),
        # Stock — `RN-ST-12` recorta la lectura; la edicion recorta los campos.
        #
        # `vehicles:price_suggestion` NO esta, y es una celda ⚠ del ADR: se
        # deniega por alineacion con `RN-ST-12`, porque una sugerencia de precio
        # expone el margen por diferencia contra el precio publicado.
        "vehicles:read": Concesion(Alcance.ALL, CAMPOS_DE_VEHICULO_SIN_COSTO),
        "vehicles:update": Concesion(Alcance.ALL, CAMPOS_DE_VEHICULO_PARA_VENDEDOR),
        # La celda completa de `ADR-024` §6: "`own`, solo `available`->`reserved`".
        # El segundo eje lo agrega `ADR-034` — sin el, esta celda quedaba mas
        # ancha que el ADR y el vendedor podia vender un vehiculo propio.
        "vehicles:change_status": Concesion(
            Alcance.OWN, transiciones=frozenset({("available", "reserved")})
        ),
        "vehicle_photos:create": _PROPIOS,
        "catalog:read": _TODO,
        # Publishing — celda ⚠ del ADR, sin fuente.
        "publications:read": _TODO,
        # CRM — `own` estricto: `assigned_user_id` al momento de la peticion.
        "leads:read": _PROPIOS,
        "leads:create": _TODO,
        "leads:update": _PROPIOS,
        "leads:change_stage": _PROPIOS,
        "leads:close": _PROPIOS,
        "activities:read": _PROPIOS,
        "activities:create": _PROPIOS,
        "activities:update": _PROPIOS,
        "contacts:read": _PROPIOS,
        "contacts:create": _PROPIOS,
        "contacts:update": _PROPIOS,
        "pipeline_stages:read": _TODO,
        "loss_reasons:read": _TODO,
        "crm_dashboard:read": _PROPIOS,
        # Communication — el stream hereda el alcance de la lectura.
        "conversations:read": _PROPIOS,
        "conversations:create": _PROPIOS,
        "conversations:mark_read": _PROPIOS,
        "conversations:close": _PROPIOS,
        "conversations:stream": _PROPIOS,
        "messages:read": _PROPIOS,
        "messages:create": _PROPIOS,
    },
    # ── admin_staff ≡ Administrativo ─────────────────────────────────────────
    RolDeTenant.ADMIN_STAFF: {
        "auth:logout": _UNO_MISMO,
        "auth:read_me": _UNO_MISMO,
        "auth:enable_mfa": _UNO_MISMO,
        "auth:verify_mfa": _UNO_MISMO,
        "tenants:read": _TODO,
        "branches:read": _TODO,
        "users:read": Concesion(Alcance.ALL, CAMPOS_PUBLICOS_DE_USUARIO),
        "users:update": Concesion(Alcance.SELF, CAMPOS_DE_PERFIL),
        # Stock — ve el costo, y opera casi todo el stock.
        "vehicles:read": _TODO,
        "vehicles:price_suggestion": _TODO,
        "vehicles:create": _TODO,
        "vehicles:update": _TODO,
        "vehicles:import": _TODO,
        "vehicle_photos:create": _TODO,
        "vehicle_photos:delete": _TODO,
        "vehicle_photos:reorder": _TODO,
        "catalog:read": _TODO,
        "publications:read": _TODO,
        "publications:republish": _TODO,
        # CRM — SOLO LECTURA sobre leads (`RN-CR-12`). La vista funcional le
        # daba escritura, pero venia del manual de usuario, que es N4. Resuelto
        # por precedencia, no por decision.
        #
        # `leads:create` tampoco esta: es la celda ⚠ mas friccionable del ADR.
        # `RN-CR-12` dice "los ve en lectura", que literalmente habla de ver.
        # Se opta por lo restrictivo porque denegar de mas es reversible.
        "leads:read": _TODO,
        "activities:read": _TODO,
        "contacts:read": _TODO,
        "contacts:create": _TODO,
        "contacts:update": _TODO,
        "contacts:merge": _TODO,
        "pipeline_stages:read": _TODO,
        "loss_reasons:read": _TODO,
        "crm_dashboard:read": _TODO,
        "conversations:read": _TODO,
        "conversations:create": _TODO,
        "conversations:mark_read": _TODO,
        "conversations:close": _TODO,
        "conversations:stream": _TODO,
        "messages:read": _TODO,
        "messages:create": _TODO,
        "whatsapp_templates:read": _TODO,
        "whatsapp_templates:create": _TODO,
        "whatsapp_templates:sync": _TODO,
    },
}


MATRIZ_DE_PLATAFORMA: dict[RolDePlataforma, dict[str, Concesion]] = {
    # `ADR-024` §7: todo `/admin/api/v1/*` le pertenece en exclusiva
    # (`RN-MT-10`). "Todo" NO se transcribe como un comodin —§5 dice que no hay
    # comodines— sino enumerando los dominios que §7 nombra. Un endpoint
    # administrativo que no este acá queda denegado, que es exactamente lo que
    # §5 quiere y lo que la verificacion de 6.9 detecta.
    RolDePlataforma.SUPER_ADMIN: {
        "tenants:read": _TODO,
        "tenants:create": _TODO,
        "tenants:suspend": _TODO,
        "tenants:update_plan": _TODO,
        # K-4: bajo `/admin` ve agregados y SALUD, no datos de negocio. Para ver
        # datos reales impersona, y eso queda auditado (`RN-AD-06`). El motivo es
        # acotar la exencion de RLS de `ADR-017` a un rodeo estrecho y trazado en
        # vez de una puerta permanente y ancha.
        "tenants:health": _TODO,
        "impersonation:start": _TODO,
        "plans:write": _TODO,
        "feature_flags:write": _TODO,
        "financing_entities:write": _TODO,  # `RN-FI-04`
        "catalog:write": _TODO,  # `RN-ST-15` — catalogos canonicos
        "support_tickets:write": _TODO,
    },
}


class EspacioAmbiguo(Exception):
    """La clave existe en las dos matrices y la declaracion no dijo en cual.

    Hoy pasa con `tenants:read`: el `manager` lo tiene sobre su propia agencia y
    el `super_admin` sobre todas. Son dos permisos distintos con el mismo
    nombre, y elegir "el que aparezca primero" convertiria el orden de dos
    diccionarios en una decision de autorizacion.

    No se resuelve renombrando una de las dos claves: los nombres salen de
    `ADR-024`, y cambiarlos por comodidad de implementacion es exactamente el
    tipo de deriva que §1 prohibe.
    """


PERMISOS_DE_TENANT: frozenset[str] = frozenset(
    permiso for celdas in MATRIZ_DE_TENANT.values() for permiso in celdas
)

PERMISOS_DE_PLATAFORMA: frozenset[str] = frozenset(
    permiso for celdas in MATRIZ_DE_PLATAFORMA.values() for permiso in celdas
)

# La union. Se calcula y no se escribe: una segunda lista a mano se
# desincroniza, y lo hace hacia el lado que deja pasar.
PERMISOS_DECLARADOS: frozenset[str] = PERMISOS_DE_TENANT | PERMISOS_DE_PLATAFORMA


def _celdas_en(espacio: Espacio, role: str) -> dict[str, Concesion]:
    """Las celdas del rol DENTRO de ese espacio, o nada.

    Se busca en UNA matriz y no en las dos. Es lo que implementa la separacion
    de `ADR-024` §2 en los dos sentidos a la vez: un `super_admin` que pregunta
    por el espacio de tenant no encuentra su rol en `MATRIZ_DE_TENANT`, y un
    `manager` que pregunta por el de plataforma no lo encuentra en la otra. No
    hace falta una regla aparte para cada sentido — hace falta no mirar donde no
    corresponde.

    Un rol que no esta en ningun catalogo termina igual que un rol del espacio
    equivocado: sin celdas, o sea 403. Y no una excepcion sin atrapar: un
    proveedor de identidad mal configurado es un problema de configuracion, y
    convertirlo en un 500 lo asciende a caida.
    """
    try:
        if espacio is Espacio.TENANT:
            return MATRIZ_DE_TENANT[rol_de_tenant(role)]
        return MATRIZ_DE_PLATAFORMA[rol_de_plataforma(role)]
    except RolDesconocido:
        raise PermisoInsuficiente from None


class ExigePermiso:
    """La dependency que exige un permiso y DEVUELVE la concesion.

    Clase y no cierre, por lo mismo que `ExigeRol`: la verificacion de 6.9
    recorre las rutas expuestas y lee `permiso` y `espacio` de aca.
    """

    def __init__(self, permiso: str, espacio: Espacio) -> None:
        self.permiso = permiso
        self.espacio = espacio

    async def __call__(self, sujeto: SujetoActual) -> Concesion:
        concesion = _celdas_en(self.espacio, sujeto.role).get(self.permiso)
        if concesion is None:
            raise PermisoInsuficiente
        return concesion


def require_permission(permiso: str, *, espacio: Espacio | None = None) -> ExigePermiso:
    """Exige un permiso, y entrega la concesion que le toca al sujeto.

        @app.get("/vehicles")
        async def listar(
            concesion: Annotated[Concesion, Depends(require_permission("vehicles:read"))],
        ) -> ...

    Devuelve la concesion y no un booleano, y eso no es comodidad: `ADR-024` §3
    extiende la restriccion de campos a la LECTURA (`RN-ST-12`), y un porton que
    solo sabe decir "podes" no puede recortar una respuesta. Con el alcance y el
    conjunto de campos, el repositorio filtra la query y el serializador recorta
    la salida. Sin ellos habria que volver a consultar la matriz mas adentro, y
    esa segunda consulta es donde se pierden las reglas.

    `espacio` es OPCIONAL a proposito y obligatorio cuando importa: se deduce
    solo para las claves que viven en una sola matriz —69 de 70 hoy— y se exige
    para las que viven en las dos. Pedirlo siempre seria ruido en cada endpoint;
    deducirlo siempre seria adivinar justo donde no se puede.

    Todo lo que puede estar mal en la declaracion se detecta al construir la
    dependency, o sea al arrancar la aplicacion: un permiso que ninguna celda
    concede, uno declarado en el espacio equivocado, y uno ambiguo.
    """
    en_tenant = permiso in PERMISOS_DE_TENANT
    en_plataforma = permiso in PERMISOS_DE_PLATAFORMA

    if espacio is None:
        if en_tenant and en_plataforma:
            raise EspacioAmbiguo(f"{permiso!r} existe en las dos matrices; declara el espacio")
        if not (en_tenant or en_plataforma):
            raise PermisoNoDeclarado(
                f"ninguna celda de la matriz concede {permiso!r}; si el modulo "
                "es nuevo, sus filas van en ADR-024 §6 antes que el endpoint"
            )
        resuelto = Espacio.TENANT if en_tenant else Espacio.PLATAFORMA
    else:
        esta = en_tenant if espacio is Espacio.TENANT else en_plataforma
        if not esta:
            raise PermisoNoDeclarado(
                f"ninguna celda del espacio {espacio.value} concede {permiso!r}"
            )
        resuelto = espacio

    return ExigePermiso(permiso, resuelto)


# ═════════════════════════════════════════════════════════════════════════════
# Hacer cumplir la concesion
#
# La matriz dice QUE le toca a cada rol; estas dos funciones son lo que lo
# ejecuta. Van juntas porque son las dos mitades del mismo recorte: una acota el
# conjunto de REGISTROS (alcance) y la otra el de CAMPOS.
#
# Estan aca y no en cada modulo por una razon concreta: escritas una vez por
# recurso, la segunda o la tercera copia se olvida un caso —tipicamente el
# `NULL`— y el olvido abre en vez de cerrar.
# ═════════════════════════════════════════════════════════════════════════════


def _es_el_sujeto(valor: uuid.UUID | None, sujeto: Sujeto) -> bool:
    """Si ese identificador es el del sujeto de la peticion.

    Un `sub` que no sea un UUID no se puede comparar, y lo que no se puede
    comparar no se concede. Keycloak emite `sub` como UUID (`ADR-007`), asi que
    esto es defensa contra un proveedor mal configurado, no un caso esperado —
    pero el caso degenerado se resuelve hacia el lado que cierra.
    """
    if valor is None:
        return False
    try:
        return valor == uuid.UUID(sujeto.user_id)
    except ValueError:
        return False


def verificar_alcance(
    concesion: Concesion,
    *,
    sujeto: Sujeto,
    assigned_user_id: uuid.UUID | None = None,
    recurso_id: uuid.UUID | None = None,
) -> None:
    """Comprueba que la concesion alcance a ESTE registro, o levanta 403.

    Se llama DESPUES de traer el registro y con los datos del registro, porque
    `own` no se puede evaluar antes: `ADR-024` §4 lo define como "su
    `assigned_user_id` es igual al `id` del sujeto **en el momento de la
    peticion**". Evaluarlo con lo que el sujeto creo, o con lo que tenia
    asignado al abrir sesion, seria otra regla —y una que vaciaria a `RN-CR-13`
    de contenido, porque reasignar dejaria de quitar el acceso.

    Un `assigned_user_id` nulo NO es de todos: no es de nadie. `NULL` no es
    igual a nada, y `own` pide igualdad.
    """
    if concesion.alcance is Alcance.ALL:
        return

    if concesion.alcance is Alcance.OWN:
        if not _es_el_sujeto(assigned_user_id, sujeto):
            raise AlcanceInsuficiente
        return

    if not _es_el_sujeto(recurso_id, sujeto):
        raise AlcanceInsuficiente


def recortar(datos: Mapping[str, Any], concesion: Concesion) -> dict[str, Any]:
    """Deja solo los campos que la concesion declara.

    `campos is None` significa SIN restriccion y devuelve todo. Aplica tanto a
    escritura como a LECTURA (`ADR-024` §3): es lo que hace que `RN-ST-12` sea
    ejecutable sobre un recurso que el vendedor si puede leer.

    Un campo declarado que el dato no trae NO aparece como `None`: rellenarlo
    seria afirmar "este campo existe y esta vacio" donde el dato no dice nada.
    """
    if concesion.campos is None:
        return dict(datos)
    return {clave: valor for clave, valor in datos.items() if clave in concesion.campos}


def verificar_transicion(concesion: Concesion, *, desde: str, hasta: str) -> None:
    """Comprueba que la concesion admita ESE cambio de estado — `ADR-034`.

    Se evalua con el registro en la mano, igual que el alcance, y por el mismo
    motivo: `desde` es el estado que el recurso tiene ahora.

    El par completo y no solo el destino: `reserved`->`available` deshace una
    reserva y comparte destino con transiciones que otras celdas si permiten.
    Acotar por destino le daria al vendedor la vuelta atras de cualquier estado.

    Corre DESPUES del alcance y ANTES de la maquina de estados: quien no alcanza
    el registro no se entera de en que estado esta, y quien no puede hacer el
    cambio no necesita saber si ademas era legal.
    """
    if concesion.transiciones is None:
        return
    if (desde, hasta) not in concesion.transiciones:
        raise TransicionNoPermitida
