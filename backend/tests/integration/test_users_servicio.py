"""El servicio de usuarios — C-05, bloque 4. Sobre base real (regla dura 8).

LO QUE ESTE ARCHIVO PRUEBA, Y POR QUE IMPORTA EL ORDEN
───────────────────────────────────────────────────────
`D-5` decide que invitar escribe en DOS sistemas —Keycloak y `users`— y que el
orden es Keycloak primero. No es estilo: es cual de los dos estados rotos
preferimos cuando se corta a la mitad.

    local primero   una persona `invited` SIN cuenta. Invisible: figura
                    invitada, nunca puede entrar, y nadie se entera hasta que
                    reclama.

    Keycloak primero   una cuenta huerfana, deshabilitada, que la reinvitacion
                    reutiliza por email. Recuperable y silencioso.

Hay una segunda razon que el diseño no menciona y que aparecio al escribir esto:
**`users.id` ES el `sub` de Keycloak** — no hay columna `keycloak_sub`. Sin la
llamada remota no hay id que insertar. El orden no es preferible: es el unico
posible.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy import text

from app.core.errors import DomainError, PlanQuotaExceeded
from app.modules.users.keycloak import ErrorDeKeycloak
from app.modules.users.service import UserService, UsuarioNoEncontrado

from .soporte import agencia_con_sucursal, sesion_de_propietario

pytestmark = pytest.mark.integration


class KeycloakFalso:
    """Un doble que REGISTRA lo que se le pidio y en que orden.

    No mockea la base —eso lo prohibe la regla dura 8— sino el sistema de
    identidad, que es externo y del que aca solo importa QUE LE MANDAMOS.
    `test_keycloak_admin.py` ya prueba el cliente real contra un transporte
    falso; esto prueba al servicio que lo usa.
    """

    def __init__(self, *, falla: bool = False) -> None:
        self.llamadas: list[tuple[str, str]] = []
        self.deshabilitados: list[str] = []
        self.rehabilitados: list[str] = []
        self.borrados: list[str] = []
        self._falla = falla
        self._subs_por_email: dict[str, str] = {}

    async def crear_usuario(
        self, *, email: str, nombre: str, tenant_id: uuid.UUID, rol: str
    ) -> str:
        self.llamadas.append(("crear_usuario", email))
        if self._falla:
            raise ErrorDeKeycloak("crear el usuario", _respuesta(409))
        sub = str(uuid.uuid4())
        self._subs_por_email[email] = sub
        return sub

    async def deshabilitar(self, sub: str) -> None:
        self.llamadas.append(("deshabilitar", sub))
        self.deshabilitados.append(sub)

    async def rehabilitar(self, sub: str) -> None:
        self.llamadas.append(("rehabilitar", sub))
        self.rehabilitados.append(sub)

    async def pedir_que_fije_contrasenia(self, sub: str) -> None:
        self.llamadas.append(("pedir_que_fije_contrasenia", sub))

    async def buscar_por_email(self, email: str) -> str | None:
        self.llamadas.append(("buscar_por_email", email))
        return self._subs_por_email.get(email)


def _respuesta(estado: int) -> httpx.Response:
    return httpx.Response(estado)


async def _filas(tenant: uuid.UUID, email: str) -> int:
    async with sesion_de_propietario() as sesion:
        return int(
            (
                await sesion.execute(
                    text(
                        "SELECT count(*) FROM users "
                        "WHERE tenant_id = :t AND lower(email) = lower(:e)"
                    ),
                    {"t": tenant, "e": email},
                )
            ).scalar_one()
        )


# ── 4.1 y 4.2 · El orden de las escrituras ──────────────────────────────────


async def test_invitar_crea_primero_en_keycloak_y_despues_local() -> None:
    """`D-5`. El orden se comprueba DESDE ADENTRO de la llamada remota.

    El doble consulta la base en el momento en que se lo invoca: si la fila
    local ya existiera ahi, el orden estaria invertido. Comparar timestamps
    despues no distinguiria nada — las dos escrituras ocurren en el mismo
    milisegundo.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    keycloak = KeycloakFalso()

    filas_al_llamar: list[int] = []
    crear_original = keycloak.crear_usuario

    async def espiar(**kwargs: object) -> str:
        filas_al_llamar.append(await _filas(tenant, str(kwargs["email"])))
        return await crear_original(**kwargs)  # type: ignore[arg-type]

    keycloak.crear_usuario = espiar  # type: ignore[method-assign]

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        await servicio.invitar(email="nueva@demo.test", nombre="Nueva", rol="salesperson")

    assert filas_al_llamar == [0], "habia fila local ANTES de llamar a Keycloak"
    assert await _filas(tenant, "nueva@demo.test") == 1


async def test_si_keycloak_falla_no_queda_una_persona_invitada_en_la_base() -> None:
    """`D-5` otra vez, y es la mitad que hace recuperable al fallo parcial.

    Una fila `invited` sin cuenta en Keycloak es una persona que figura
    invitada, nunca puede entrar, y de la que nadie se entera hasta que reclama.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    keycloak = KeycloakFalso(falla=True)

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        with pytest.raises(ErrorDeKeycloak):
            await servicio.invitar(email="fantasma@demo.test", nombre="Fantasma", rol="manager")

    assert await _filas(tenant, "fantasma@demo.test") == 0


# ── 4.5 · La cuota del plan ─────────────────────────────────────────────────


async def test_invitar_superando_el_cupo_no_crea_nada_ni_local_ni_en_keycloak() -> None:
    """402 y no 403, y la diferencia importa: ningun permiso arregla una cuota.

    ⚠️ SE VERIFICA QUE NO SE LLAMO A KEYCLOAK. Es lo que distingue "se rechazo"
    de "se rechazo tarde": si la cuota se mirara despues de crear la cuenta,
    cada intento fallido dejaria una cuenta huerfana en el proveedor de
    identidad. El chequeo va ANTES de la primera escritura.
    """
    # `starter` topea en 2 usuarios.
    tenant, _ = await agencia_con_sucursal(plan="starter")
    keycloak = KeycloakFalso()

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        await servicio.invitar(email="una@demo.test", nombre="Una", rol="manager")
        await servicio.invitar(email="dos@demo.test", nombre="Dos", rol="salesperson")

        llamadas_antes = len(keycloak.llamadas)

        with pytest.raises(PlanQuotaExceeded) as fallo:
            await servicio.invitar(email="tres@demo.test", nombre="Tres", rol="salesperson")

    assert fallo.value.status_code == 402
    assert await _filas(tenant, "tres@demo.test") == 0
    assert len(keycloak.llamadas) == llamadas_antes, "se llamo a Keycloak con la cuota llena"


# ── 4.7 y 4.8 · La baja ─────────────────────────────────────────────────────


async def test_dar_de_baja_deshabilita_en_keycloak_y_no_borra() -> None:
    """`D-6`. Borrar liberaria el email para otra cuenta y romperia la
    trazabilidad de que hizo esa persona — mismo criterio que C-04 con el CUIT.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    keycloak = KeycloakFalso()

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        persona = await servicio.invitar(email="se-va@demo.test", nombre="Se Va", rol="manager")
        await servicio.dar_de_baja(persona.id)

    assert str(persona.id) in keycloak.deshabilitados
    assert keycloak.borrados == [], "el servicio BORRA en Keycloak, y `D-6` dice deshabilitar"


async def test_dar_de_baja_libera_el_email_y_reinvitar_rehabilita_la_cuenta() -> None:
    """Tarea 4.8, **corregida el 21-ago-2026** — decia lo contrario.

    El indice `ux_users_tenant_email` es parcial por `deleted_at`, y eso es una
    decision del bloque 1 con su razon escrita: si el email quedara tomado para
    siempre, la reincorporacion de un empleado seria imposible.

    La divergencia con Keycloak —donde la cuenta sigue existiendo, deshabilitada—
    no se resuelve ocupando el email local sino REUTILIZANDO la cuenta remota,
    que es lo que `D-5` ya insinuaba. Sin esto, reinvitar rebotaria con un 409
    de Keycloak que el usuario veria como un fallo generico.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    keycloak = KeycloakFalso()

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        primera = await servicio.invitar(email="vuelve@demo.test", nombre="Vuelve", rol="manager")
        await servicio.dar_de_baja(primera.id)

        segunda = await servicio.invitar(
            email="vuelve@demo.test", nombre="Vuelve Otra Vez", rol="salesperson"
        )

    # ⚠️ LA MISMA FILA, Y NO ES UN DETALLE — lo obliga el esquema. `users.id` ES
    # el `sub` de Keycloak. Si se rehabilita la cuenta remota, el `sub` es el
    # mismo, asi que una fila NUEVA tendria el mismo id que la vieja y chocaria
    # contra la clave primaria. Reinvitar RESUCITA la fila.
    #
    # Y eso resuelve `4.11` de paso: `user_branches` cuelga de `user_id`, asi
    # que las asignaciones vuelven con la persona sin reasignar nada a mano.
    assert segunda.id == primera.id, "la reinvitacion creo una fila nueva con el mismo `sub`"
    assert segunda.deleted_at is None, "la fila resucitada sigue dada de baja"
    assert segunda.role == "salesperson", "resucitar no tomo el rol de la nueva invitacion"
    assert (
        str(primera.id) in keycloak.rehabilitados
    ), "se creo una cuenta NUEVA en Keycloak en vez de rehabilitar la que ya existia"


# ── 4.9, 4.10 y 4.11 · Las sucursales ───────────────────────────────────────


async def _sucursal_extra(tenant: uuid.UUID, nombre: str) -> uuid.UUID:
    bid = uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO branches (id, tenant_id, name, city, province, is_active) "
                "VALUES (:id, :t, :n, 'Mendoza', 'Mendoza', true)"
            ),
            {"id": bid, "t": tenant, "n": nombre},
        )
    return bid


async def _asignaciones(user_id: uuid.UUID) -> list[tuple[uuid.UUID, bool]]:
    async with sesion_de_propietario() as sesion:
        filas = await sesion.execute(
            text(
                "SELECT branch_id, is_primary FROM user_branches "
                "WHERE user_id = :u ORDER BY is_primary DESC"
            ),
            {"u": user_id},
        )
        return [(f.branch_id, f.is_primary) for f in filas]


async def test_marcar_otra_principal_desmarca_la_anterior() -> None:
    """Tarea 4.9. La base tiene `ux_user_branches_principal UNIQUE (user_id)
    WHERE is_primary`, pero una constraint RECHAZA — no desmarca.

    Sin el desmarcado explicito, cambiarle a alguien la sucursal principal
    reventaria con un `duplicate key` que ademas no le dice nada al usuario. El
    indice es la red que garantiza el invariante; el servicio es el que hace que
    la operacion normal funcione.
    """
    tenant, primera = await agencia_con_sucursal(plan="pro")
    segunda = await _sucursal_extra(tenant, "Sucursal Norte")
    keycloak = KeycloakFalso()

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        persona = await servicio.invitar(email="con-sucursal@demo.test", nombre="X", rol="manager")

        await servicio.asignar_sucursales(persona.id, [(primera, True)])
        await servicio.asignar_sucursales(persona.id, [(primera, False), (segunda, True)])

    asignadas = await _asignaciones(persona.id)
    principales = [b for b, principal in asignadas if principal]

    assert principales == [segunda], f"principales: {principales}"
    assert len(asignadas) == 2


async def test_asignar_una_sucursal_de_otra_agencia_se_rechaza() -> None:
    """Tarea 4.10 — el agujero clasico: las dos puntas protegidas y el vinculo no.

    La FK compuesta contra `(id, tenant_id)` ya lo impide en la base, y eso es
    lo que paga la redundancia de `tenant_id` en la tabla de union. Lo que el
    servicio agrega es que el rechazo se PAREZCA a un error de negocio en vez de
    a un `IntegrityError` crudo con un mensaje de PostgreSQL adentro.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    otra, sucursal_de_otra = await agencia_con_sucursal(plan="pro")
    keycloak = KeycloakFalso()

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        persona = await servicio.invitar(email="ajena@demo.test", nombre="X", rol="manager")

        with pytest.raises(DomainError) as fallo:
            await servicio.asignar_sucursales(persona.id, [(sucursal_de_otra, True)])

    assert fallo.value.code == "branch_not_found"
    assert await _asignaciones(persona.id) == []


async def test_las_asignaciones_sobreviven_a_la_baja() -> None:
    """Tarea 4.11 (`D-7`). Saber en que sucursal trabajaba alguien es historico.

    Y tiene una consecuencia practica que aparecio al implementar 4.8: como
    reinvitar RESUCITA la fila —mismo `id`, porque es el `sub`—, las
    asignaciones vuelven con la persona sin que nadie las reasigne.
    """
    tenant, sucursal = await agencia_con_sucursal(plan="pro")
    keycloak = KeycloakFalso()

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        persona = await servicio.invitar(email="historial@demo.test", nombre="X", rol="manager")
        await servicio.asignar_sucursales(persona.id, [(sucursal, True)])
        await servicio.dar_de_baja(persona.id)

    assert await _asignaciones(persona.id) == [(sucursal, True)], "la baja borro el historico"

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        vuelta = await servicio.invitar(
            email="historial@demo.test", nombre="X Vuelve", rol="manager"
        )

    assert vuelta.id == persona.id
    assert await _asignaciones(vuelta.id) == [
        (sucursal, True)
    ], "al volver perdio las sucursales que ya tenia"


# ── 4.3 · Aceptar la invitacion ─────────────────────────────────────────────


async def test_aceptar_la_invitacion_activa_el_espejo_sin_recibir_contrasenia() -> None:
    """`D-5` paso 4. La contraseña ya se fijo EN KEYCLOAK, no aca.

    Este metodo solo mueve el estado local de `invited` a `active`: es el
    reconocimiento de que la persona completo su parte. `ADR-026` §4 le saco a
    `accept-invitation` la unica razon por la que habria recibido una
    contraseña.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    keycloak = KeycloakFalso()

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        persona = await servicio.invitar(email="acepta@demo.test", nombre="Acepta", rol="manager")
        assert persona.status == "invited"

        activa = await servicio.aceptar_invitacion(persona.id)

    assert activa.status == "active"


async def test_aceptar_dos_veces_no_rompe_ni_cambia_nada() -> None:
    """El doble clic del mail de invitacion, que va a pasar.

    Si la segunda vez levantara, la persona veria un error habiendo hecho todo
    bien. Es idempotente a proposito.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    keycloak = KeycloakFalso()

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        persona = await servicio.invitar(email="dosveces@demo.test", nombre="Dos", rol="manager")
        await servicio.aceptar_invitacion(persona.id)
        otra_vez = await servicio.aceptar_invitacion(persona.id)

    assert otra_vez.status == "active"


# ── 4.6 (la otra mitad) · Desactivar ────────────────────────────────────────


async def test_desactivar_suspende_aca_y_tambien_en_keycloak() -> None:
    """`D-6`: no puede entrar, sigue siendo empleado, sigue ocupando cupo.

    ⚠️ TAMBIEN SE DESHABILITA EN KEYCLOAK, y sin eso la suspension seria una
    marca decorativa: la persona podria seguir autenticandose y obteniendo
    tokens validos, y lo unico que la frenaria seria nuestra aplicacion
    mirando una columna. Cualquier otro consumidor del mismo Keycloak la
    dejaria pasar.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    keycloak = KeycloakFalso()

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        persona = await servicio.invitar(email="suspende@demo.test", nombre="X", rol="manager")
        suspendida = await servicio.desactivar(persona.id)

    assert suspendida.status == "inactive"
    assert suspendida.deleted_at is None, "desactivar dio de baja, y son cosas distintas"
    assert str(persona.id) in keycloak.deshabilitados


async def test_desactivar_no_libera_cupo_y_dar_de_baja_si() -> None:
    """La consecuencia de `D-6` sobre la facturacion, medida contra el plan real.

    `starter` topea en 2. Con una suspendida el cupo sigue lleno; recien la baja
    hace lugar. Es lo que separa "no puede entrar" de "ya no trabaja aca".
    """
    tenant, _ = await agencia_con_sucursal(plan="starter")
    keycloak = KeycloakFalso()

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]
        una = await servicio.invitar(email="u1@demo.test", nombre="U1", rol="manager")
        await servicio.invitar(email="u2@demo.test", nombre="U2", rol="salesperson")

        await servicio.desactivar(una.id)
        with pytest.raises(PlanQuotaExceeded):
            await servicio.invitar(email="u3@demo.test", nombre="U3", rol="salesperson")

        await servicio.dar_de_baja(una.id)
        await servicio.invitar(email="u3@demo.test", nombre="U3", rol="salesperson")

    assert await _filas(tenant, "u3@demo.test") == 1


async def test_operar_sobre_alguien_de_otra_agencia_da_404_y_no_confirma_que_existe() -> None:
    """Distinguir "no existe" de "no es tuyo" le confirmaria a un tenant que
    cierto id existe en otra agencia — una fuga por el codigo de estado, sin
    devolver un solo dato. Las dos dan 404, y las tres operaciones igual.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")
    otra, _ = await agencia_con_sucursal(plan="pro")
    keycloak = KeycloakFalso()

    async with sesion_de_propietario() as sesion:
        de_otra = await UserService(sesion, otra, keycloak).invitar(  # type: ignore[arg-type]
            email="deotra@demo.test", nombre="De Otra", rol="manager"
        )

    async with sesion_de_propietario() as sesion:
        servicio = UserService(sesion, tenant, keycloak)  # type: ignore[arg-type]

        for operacion in (servicio.desactivar, servicio.dar_de_baja, servicio.aceptar_invitacion):
            with pytest.raises(UsuarioNoEncontrado) as fallo:
                await operacion(de_otra.id)
            assert fallo.value.status_code == 404
            assert fallo.value.code == "user_not_found"
