"""`plans` es catalogo: se lee y no se escribe — migracion `010`.

POR QUE ESTE ARCHIVO EXISTE APARTE
───────────────────────────────────
`test_plan_limits.py` prueba lo que `plans` SIGNIFICA: que el `0` es sin techo,
que la cuota frena el alta. Nada de eso se entera de quien puede escribir la
tabla.

El permiso de mas estuvo desde `005` y nadie lo noto, porque **ningun test
fallaba por tenerlo**. Un permiso que sobra no rompe nada: solo espera. Aparecio
de rebote al escribir el catalogo de vehiculos en `009`, cuando hubo que
descubrir que el init de la base otorga `INSERT` y `UPDATE` a toda tabla nueva.

Estos tests son la unica razon por la que, si alguien vuelve a otorgarlos, algo
se va a poner en rojo.

Sin mocks de base de datos (regla dura 8). Se corre con:

    docker compose run --rm backend pytest -m integration
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from .soporte import sesion_de_propietario

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("operacion", "sql"),
    [
        (
            "INSERT",
            "INSERT INTO plans (code, name, price_ars, max_users, max_vehicles, "
            "max_branches, max_whatsapp_messages_month, modules) "
            "VALUES ('gratis', 'Gratis', 0, 1, 1, 1, 1, '[]'::jsonb)",
        ),
        ("UPDATE", "UPDATE plans SET price_ars = 1 WHERE code = 'starter'"),
        ("DELETE", "DELETE FROM plans WHERE code = 'starter'"),
    ],
)
async def test_la_aplicacion_no_puede_escribir_los_planes(
    base_migrada: None, sesion: AsyncSession, operacion: str, sql: str
) -> None:
    """Las tres, no solo `INSERT`.

    El default del init daba `INSERT` **y** `UPDATE`, asi que revocar una sola
    dejaria el agujero abierto por la otra. Y `UPDATE` es la peor de las dos
    acá: cambia el precio de un plan para TODAS las agencias.
    """
    with pytest.raises(ProgrammingError) as fallo:
        await sesion.execute(text(sql))

    assert (
        "permission denied" in str(fallo.value).lower()
    ), f"{operacion} sobre `plans` no fue rechazado por permisos: {fallo.value}"


async def test_los_planes_se_siguen_leyendo(base_migrada: None, sesion: AsyncSession) -> None:
    """Revocar la escritura no puede llevarse la lectura por delante.

    Es lo que hace `PlanLimitsService` en el camino caliente de cada alta: si
    esto fallara, el sistema entero dejaria de poder verificar cuotas.
    """
    total = await sesion.scalar(text("SELECT count(*) FROM plans"))

    assert total == 3


async def test_el_propietario_sigue_pudiendo_sembrar(base_migrada: None) -> None:
    """El seed corre en la migracion, o sea con el rol propietario.

    Si la revocacion lo hubiera alcanzado tambien, `005` no podria volver a
    aplicarse sobre una base limpia — y eso solo se descubriria al montar un
    entorno nuevo, que es el peor momento.
    """
    async with sesion_de_propietario() as propietario:
        await propietario.execute(
            text(
                "INSERT INTO plans (code, name, price_ars, max_users, max_vehicles, "
                "max_branches, max_whatsapp_messages_month, modules) "
                "VALUES ('starter', 'Starter', 45000.00, 2, 80, 1, 1500, '[]'::jsonb) "
                "ON CONFLICT (code) DO NOTHING"
            )
        )
        total = await propietario.scalar(text("SELECT count(*) FROM plans"))

    assert total == 3
