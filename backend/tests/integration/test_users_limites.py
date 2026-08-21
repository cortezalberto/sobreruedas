"""El contador de usuarios, y la diferencia entre desactivar y dar de baja.

C-05, tareas 4.4 y 4.6. Sobre base real (regla dura 8).

POR QUE ESTE ARCHIVO EXISTE ANTES QUE EL SERVICIO
──────────────────────────────────────────────────
`assert_can_add_user` YA existe desde C-04 y hoy **levanta**
`ContadorNoRegistrado`: nadie registro como se cuentan los usuarios. C-04 lo
dejo fallando cerrado a proposito — el encabezado de `limits.py` lo explica:
devolver "permitido" cuando no se sabe contar es exactamente como se pierde un
limite de facturacion sin que nadie lo note.

Asi que el contador no es un detalle del bloque 4: es lo que lo desbloquea.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.modules.tenancy.limits import ContadorNoRegistrado, PlanLimitsService
from app.modules.users.limites import contar_usuarios, registrar_contador_de_usuarios

from .soporte import agencia_con_sucursal, sesion_de_propietario

pytestmark = pytest.mark.integration


async def _persona(
    tenant: uuid.UUID, email: str, *, estado: str = "active", baja: bool = False
) -> uuid.UUID:
    """Una fila en el espejo. Andamiaje: el alta de verdad es del servicio.

    La baja va en un `UPDATE` aparte y no como parametro del `INSERT`: `now()`
    es una funcion de SQL, y pasarla como valor bindeado la manda como el texto
    `'now()'`, que PostgreSQL rechaza por tipo.
    """
    uid = uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Persona', 'salesperson', :s)"
            ),
            {"id": uid, "t": tenant, "e": email, "s": estado},
        )
        if baja:
            await sesion.execute(
                text("UPDATE users SET deleted_at = now() WHERE id = :id"), {"id": uid}
            )
    return uid


async def test_desactivar_sigue_consumiendo_cupo_y_la_baja_lo_libera() -> None:
    """`D-6`, que son tres estados que se confunden facil.

    `inactive` es alguien que no puede entrar y SIGUE SIENDO EMPLEADO — ocupa su
    licencia igual. `deleted_at` es alguien que se fue de la empresa, y ahi si
    libera el lugar.

    Contarlos igual seria cobrarle a la agencia por gente que ya no trabaja ahi;
    contar `inactive` como libre le dejaria tener 50 personas suspendidas en un
    plan de 5.
    """
    tenant, _ = await agencia_con_sucursal()

    await _persona(tenant, "activa@demo.test")
    await _persona(tenant, "suspendida@demo.test", estado="inactive")
    await _persona(tenant, "se-fue@demo.test", baja=True)

    async with sesion_de_propietario() as sesion:
        cuantos = await contar_usuarios(sesion, tenant)

    assert cuantos == 2, "la activa y la suspendida cuentan; la dada de baja no"


async def test_el_contador_no_cruza_agencias() -> None:
    """El contrapeso obvio, y el que hace que el test de arriba pruebe algo.

    Sin esto, un contador que ignorara `tenant_id` pasaria el primer test
    siempre que la base estuviera limpia.
    """
    una, _ = await agencia_con_sucursal()
    otra, _ = await agencia_con_sucursal()

    await _persona(una, "de-una@demo.test")
    await _persona(otra, "de-otra@demo.test")
    await _persona(otra, "otra-mas@demo.test")

    async with sesion_de_propietario() as sesion:
        assert await contar_usuarios(sesion, una) == 1
        assert await contar_usuarios(sesion, otra) == 2


async def test_el_contador_queda_registrado_y_assert_can_add_user_deja_de_levantar() -> None:
    """Tarea 4.4 — la linea sin la cual el bloque entero no funciona.

    Antes de esto, `assert_can_add_user` levantaba `ContadorNoRegistrado`, que
    es un `RuntimeError` y no un `DomainError`: no tiene respuesta HTTP porque
    no es un error de datos sino de programacion. Tenia que romper el test, y
    rompia.
    """
    tenant, _ = await agencia_con_sucursal(plan="pro")

    async with sesion_de_propietario() as sesion:
        limites = PlanLimitsService(sesion)

        # El estado de partida, y el que hace que este test pruebe algo: sin
        # registrar, LEVANTA. Si esto dejara de levantar, el resto del test
        # pasaria en verde sin que nadie hubiera registrado nada.
        with pytest.raises(ContadorNoRegistrado):
            await limites.assert_can_add_user(tenant)

        registrar_contador_de_usuarios(limites)
        await limites.assert_can_add_user(tenant)
