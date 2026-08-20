"""El catalogo de vehiculos: lo lee todo el mundo, no lo escribe nadie — C-13.

`vehicle_brands` y `vehicle_models` son catalogo cross-tenant. La exencion de
RLS es estructural: no hay tenant al que acotar una marca de auto.

LO QUE ESTE ARCHIVO CUIDA, Y QUE NO ES OBVIO
─────────────────────────────────────────────
Que una tabla este exenta de RLS se lee facil como "no tiene proteccion", y de
ahi a que sea escribible hay un paso. No lo es: una agencia que renombra una
marca se la renombra a TODAS. La exencion es sobre la LECTURA, y la escritura
esta negada aparte.

Y negarla exigio revocar, no callar. El init de la base otorga por defecto
`SELECT, INSERT, UPDATE` a toda tabla nueva, asi que estas nacieron escribibles
y la migracion tuvo que quitarles el permiso. Un test que solo comprobara "se
puede leer" habria pasado igual con el catalogo abierto de par en par.

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


# ── Que el seed haya entrado ─────────────────────────────────────────────────


async def test_las_cuarenta_marcas_quedaron_sembradas(
    base_migrada: None, sesion_sin_tenant: AsyncSession
) -> None:
    """`knowledge-base/04` §Seed data inicial pide 40 marcas."""
    total = await sesion_sin_tenant.scalar(text("SELECT count(*) FROM vehicle_brands"))

    assert total == 40


async def test_cada_modelo_cuelga_de_una_marca_que_existe(
    base_migrada: None, sesion_sin_tenant: AsyncSession
) -> None:
    """El seed resuelve `brand_id` por subconsulta contra el slug.

    Si esa subconsulta no encontrara la marca, el INSERT no insertaria nada y el
    modelo desapareceria en silencio — no falla, simplemente no esta. Por eso se
    cuenta: que haya modelos, y que ninguno quede huerfano.
    """
    modelos = await sesion_sin_tenant.scalar(text("SELECT count(*) FROM vehicle_models"))
    huerfanos = await sesion_sin_tenant.scalar(
        text(
            "SELECT count(*) FROM vehicle_models m "
            "LEFT JOIN vehicle_brands b ON b.id = m.brand_id WHERE b.id IS NULL"
        )
    )

    assert modelos > 0
    assert huerfanos == 0


async def test_el_seed_no_pisa_una_correccion_hecha_a_mano(base_migrada: None) -> None:
    """`ON CONFLICT DO NOTHING`, no `DO UPDATE`.

    Este catalogo se va a corregir sobre la base —los años de los modelos son
    dato de mercado— y un seed que sobrescribe devolveria esas correcciones al
    estado del archivo en cada despliegue.

    Va con la sesion del PROPIETARIO y no con la de aplicacion: el seed corre en
    la migracion, y el rol de aplicacion no puede escribir el catalogo. Que este
    test necesite el otro rol es, en si mismo, la revocacion funcionando.
    """
    async with sesion_de_propietario() as propietario:
        # Se reejecuta el INSERT del seed tal como lo hace la migracion.
        await propietario.execute(
            text(
                "INSERT INTO vehicle_brands (name, slug, origin_country) "
                "VALUES ('Toyota Motor Corp', 'toyota', 'Japón') "
                "ON CONFLICT (slug) DO NOTHING"
            )
        )
        nombre = await propietario.scalar(
            text("SELECT name FROM vehicle_brands WHERE slug = 'toyota'")
        )

    assert nombre == "Toyota"


# ── Legible por todos ────────────────────────────────────────────────────────


async def test_el_catalogo_se_lee_sin_contexto_de_tenant(
    base_migrada: None, sesion_sin_tenant: AsyncSession
) -> None:
    """La contracara de `RN-MT-06`.

    Una tabla CON política y sin contexto devuelve cero filas. El catalogo tiene
    que devolver las suyas igual, porque no hay contexto que le falte.
    """
    marcas = await sesion_sin_tenant.scalar(text("SELECT count(*) FROM vehicle_brands"))

    assert marcas == 40


async def test_dos_tenants_distintos_ven_el_mismo_catalogo(
    base_migrada: None, sesion: AsyncSession, otro_tenant: object
) -> None:
    """Es lo contrario de lo que se prueba para las tablas de negocio.

    En `test_tenant_isolation.py` la afirmacion es que un tenant NO ve lo del
    otro. Acá es que ven exactamente lo mismo: un catalogo que variara por
    agencia no seria un catalogo.
    """
    from app.db.session import sesion_de_tenant

    from .soporte import DSN_APLICACION

    desde_el_primero = await sesion.scalar(text("SELECT count(*) FROM vehicle_brands"))

    async with sesion_de_tenant(otro_tenant, dsn=DSN_APLICACION) as otra:
        desde_el_segundo = await otra.scalar(text("SELECT count(*) FROM vehicle_brands"))

    assert desde_el_primero == desde_el_segundo == 40


# ── Escribible por ninguno ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("operacion", "sql"),
    [
        ("INSERT", "INSERT INTO vehicle_brands (name, slug) VALUES ('Inventada', 'inventada')"),
        ("UPDATE", "UPDATE vehicle_brands SET name = 'Otra' WHERE slug = 'toyota'"),
        ("DELETE", "DELETE FROM vehicle_brands WHERE slug = 'toyota'"),
    ],
)
async def test_la_aplicacion_no_puede_escribir_el_catalogo(
    base_migrada: None, sesion: AsyncSession, operacion: str, sql: str
) -> None:
    """El requisito de C-13: "escribibles por ninguno".

    Se prueban las tres operaciones y no solo `INSERT`: el default del init daba
    `INSERT` **y** `UPDATE`, asi que revocar una sola dejaria el agujero abierto
    por la otra. `DELETE` ya venia negado por la regla dura 3 y se comprueba
    igual — depender de que otro archivo lo siga negando no es una garantia.
    """
    with pytest.raises(ProgrammingError) as fallo:
        await sesion.execute(text(sql))

    assert (
        "permission denied" in str(fallo.value).lower()
    ), f"{operacion} sobre el catalogo no fue rechazado por permisos: {fallo.value}"


async def test_los_modelos_tampoco_se_escriben(base_migrada: None, sesion: AsyncSession) -> None:
    """La revocacion se aplica a las DOS tablas, no solo a la primera."""
    with pytest.raises(ProgrammingError) as fallo:
        await sesion.execute(text("UPDATE vehicle_models SET name = 'X'"))

    assert "permission denied" in str(fallo.value).lower()
