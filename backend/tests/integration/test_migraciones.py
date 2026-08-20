"""Las migraciones contra PostgreSQL real — C-02, tareas 1.2 y 1.7.

Por que corren de verdad y no contra un doble: una migracion es un efecto sobre
una base concreta. Un test que "verifica" una migracion sin ejecutarla verifica
el texto del archivo, que es justo lo que nadie necesita comprobar.

Se corre con:

    docker compose run --rm backend pytest -m integration

La base de tests del CI arranca vacia y con el init de desarrollo, que trae
`pgcrypto`, `pg_trgm`, `postgis` y `uuid-ossp` pero NO `unaccent` ni `btree_gin`.
Esas dos solo pueden llegar por migracion — que es exactamente el camino que
tienen que recorrer para llegar a staging y a produccion, donde ese init NO
corre.

Desde ADR-020 las migraciones corren con el rol PROPIETARIO y no con el de la
aplicacion: crear tablas y politicas es precisamente lo que el rol de aplicacion
no debe poder hacer. Los tests del final de este archivo lo verifican.
"""

from __future__ import annotations

import asyncpg
import pytest

from .soporte import (
    DSN_APLICACION,
    DSN_PROPIETARIO,
    SIN_URL_DE_MIGRACION,
    alembic,
    dsn_asyncpg,
)

pytestmark = pytest.mark.integration

# Las cuatro que el stack declara y que T-009 exige. `postgis` y `pgcrypto` no
# entran: las instala el init local y, en los ambientes gestionados, Terraform.
EXTENSIONES_EXIGIDAS = ("uuid-ossp", "pg_trgm", "unaccent", "btree_gin")


async def extensiones_presentes() -> set[str]:
    """Las extensiones vistas DESDE LA APLICACION.

    Con el DSN de la aplicacion a proposito: de paso acredita que ese rol puede
    conectarse, que es la mitad de lo que este change cambia.
    """
    conexion = await asyncpg.connect(dsn_asyncpg(DSN_APLICACION), timeout=10)
    try:
        filas = await conexion.fetch("SELECT extname FROM pg_extension")
    finally:
        await conexion.close()
    return {fila["extname"] for fila in filas}


@pytest.mark.parametrize("extension", EXTENSIONES_EXIGIDAS)
async def test_la_extension_queda_habilitada(base_migrada: None, extension: str) -> None:
    """Una por una y no todas juntas: si faltan dos, el reporte nombra las dos."""
    assert extension in await extensiones_presentes()


async def test_migrar_dos_veces_no_falla(base_migrada: None) -> None:
    """`upgrade head` sobre una base ya migrada es un no-op, no un error.

    Importa porque el despliegue lo corre en cada arranque: si fallara al no
    tener nada que hacer, todo despliegue sin migraciones nuevas quedaria rojo.
    """
    resultado = alembic("upgrade", "head")
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


# ── 4.1 y 4.3 · Las migraciones son del propietario, y solo de el ────────────


async def test_migrar_con_el_rol_de_la_aplicacion_falla(base_migrada: None) -> None:
    """El rol de aplicacion no puede migrar, y eso es el punto.

    Se corre un `downgrade` y no `upgrade head`: sobre una base ya migrada un
    upgrade no tiene nada que hacer, asi que pasaria sin intentar un solo DDL y
    el test no probaria nada. El downgrade si intenta tocar el esquema.

    ⚠️ EL DESTINO ES EXPLICITO Y NO `-1`, Y ESO COSTO UN FALSO VERDE.

    Con `-1` el test dependia de que la migracion que quede ARRIBA tuviera DDL
    en su `downgrade()`. Eso fue cierto hasta la `010`, que solo revoca
    permisos: su downgrade no crea ni borra nada, corrio sin problemas con el
    rol de aplicacion, y el test fallo — no porque el rol pudiera modificar el
    esquema, sino porque no se le pidio que lo intentara.

    Bajar hasta la `008` cruza el `downgrade` de la `009`, que borra tablas. Eso
    es DDL de verdad y es lo que el rol de aplicacion tiene prohibido. El destino
    fijo acopla este test a que la `009` exista, que es un acoplamiento visible
    y que falla ruidoso — a diferencia del anterior, que fallaba en silencio
    cada vez que alguien agregara una migracion sin DDL.

    Que falle NO deja la base a medias: alembic corre cada migracion en su
    transaccion y el DDL de PostgreSQL es transaccional, asi que el rechazo por
    permisos revierte todo. Lo verifica el `upgrade head` del final.
    """
    resultado = alembic("downgrade", "008", url_de_migracion=DSN_APLICACION)

    assert resultado.returncode != 0, (
        "el rol de la aplicacion pudo modificar el esquema: puede crear tablas "
        "sin politica RLS o alterar las existentes (ADR-020)"
    )
    salida = resultado.stdout + resultado.stderr
    assert (
        "InsufficientPrivilege" in salida or "permission denied" in salida.lower()
    ), f"fallo, pero por un motivo distinto a permisos:\n{salida}"

    # La base queda como estaba.
    assert alembic("upgrade", "head").returncode == 0


async def test_las_dos_urls_deben_apuntar_a_la_misma_base() -> None:
    """Dos variables reabren un descuido que una sola no permitia.

    Antes de ADR-020, `DATABASE_URL` era la unica y por construccion migraciones
    y runtime nunca podian apuntar a bases distintas. Con dos URLs eso vuelve a
    ser posible, asi que la garantia pasa a verificarse en `env.py`.

    Migrar la base equivocada es de los errores mas caros que existen y no
    deberia depender de que nadie se confunda al copiar un `.env`.
    """
    otra_base = DSN_PROPIETARIO.rsplit("/", 1)[0] + "/una_base_que_no_es_esta"

    resultado = alembic("upgrade", "head", url_de_migracion=otra_base)

    assert resultado.returncode != 0, "alembic migro contra una base distinta sin quejarse"
    salida = resultado.stdout + resultado.stderr
    assert (
        "apuntan a bases distintas" in salida
    ), f"fallo, pero no por la verificacion de ADR-020:\n{salida}"
    # El mensaje nombra QUE no coincide, y no las URLs: llevan credenciales.
    assert "base" in salida
    assert "una_base_que_no_es_esta" not in salida


async def test_sin_url_de_migracion_alembic_no_arranca() -> None:
    """Falta la variable: muere nombrandola, no con un error de conexion.

    Sin este mensaje, el sintoma seria un fallo de autenticacion contra el rol
    de aplicacion — que se lee como credencial mal copiada y manda a revisar el
    lugar equivocado.
    """
    resultado = alembic("upgrade", "head", url_de_migracion=SIN_URL_DE_MIGRACION)

    assert resultado.returncode != 0
    assert "DATABASE_MIGRATION_URL" in resultado.stdout + resultado.stderr
