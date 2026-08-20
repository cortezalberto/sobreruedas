"""Toda migracion deja funcionando a la version anterior — regla dura 13.

POR QUE ESTA REGLA EXISTE — ADR-025
────────────────────────────────────
El despliegue azul-verde levanta el stack nuevo al lado del viejo y conmuta el
trafico recien cuando el humo pasa. `ADR-023` decia que revertir no hace falta,
que *"basta con no conmutar"*. **Eso vale para el codigo, no para la base.**

Los dos stacks comparten UNA SOLA base de datos: PostgreSQL tiene estado y no se
puede duplicar (`ADR-025` Decision 1). Entonces una migracion que rompa hacia
atras inutiliza el stack VIEJO en el momento en que corre — y el stack viejo es
justamente la red de seguridad del azul-verde. El humo puede pasar, la
conmutacion puede hacerse, y el camino de vuelta ya no existe.

Ademas el agente de despliegue corre las migraciones ANTES de levantar el stack
nuevo, con todo el trafico todavia en el viejo. Ese orden es seguro *solo* si
esta regla se cumple.

QUE SE MIRA — TODO MENOS `downgrade()`
───────────────────────────────────────
`downgrade()` esta LLENO de DDL destructivo, y ahi es correcto: un downgrade
debe borrar lo que su upgrade creo. Se analiza el resto del modulo.

⚠️ **Hasta el 18-ago-2026 esto miraba solo el cuerpo de `upgrade()`, y tenia
CUATRO agujeros por los que pasaba SQL sin ser visto.** Los cuatro se
descubrieron escribiendo las migraciones `009` y `010`, que usan exactamente los
patrones que el analisis no cubria:

  1. **Solo `op.execute()`.** Un `op.get_bind().execute(...)` pasaba entero, y
     por ahi pasa cualquier cosa: `DROP TABLE`, `SET NOT NULL`, lo que sea.
  2. **Solo el cuerpo de `upgrade()`.** El DDL que vive en funciones auxiliares
     —que es como estan escritas estas migraciones— quedaba afuera.
  3. **Solo argumentos literales.** El idioma real es `execute(sa.text("..."))`,
     y el analisis veia una `Call` y leia cadena vacia.
  4. **`REVOKE` no estaba en la lista.** No toca el esquema, pero rompe hacia
     atras igual: si la version anterior escribia esa tabla, deja de poder.

Cada uno tiene su test negativo mas abajo. Un gate ciego pasa igual de verde que
uno que funciona, y este estuvo verde todo ese tiempo.

QUE ES DESTRUCTIVO Y QUE NO
───────────────────────────
No toda operacion de borrado rompe hacia atras. El criterio es si la version
ANTERIOR de la aplicacion sigue funcionando:

  ROMPE      borrar columna o tabla · renombrar · SET NOT NULL · agregar una
             constraint que el dato existente pueda violar · estrechar un tipo
  NO ROMPE   crear tabla · agregar columna nullable · crear indice ·
             BORRAR un indice o una constraint (afloja, no apreta)

LA VALVULA
──────────
La fase *contract* de expand/contract es legitima y necesaria: en algun
despliegue posterior hay que borrar lo viejo. Se habilita con un marcador
explicito en la migracion:

    # migracion-contract: la columna quedo sin uso desde la revision <xxx>

El marcador no debilita el gate. Lo vuelve **deliberado y visible en el diff**,
que es exactamente el punto.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
VERSIONES = RAIZ_BACKEND / "alembic" / "versions"

MARCADOR_CONTRACT = re.compile(r"#\s*migracion-contract:", re.IGNORECASE)

# Exencion POR LINEA, para lo que es seguro por construccion y no por fase.
#
# `migracion-contract` silencia el ARCHIVO entero, y eso es lo correcto para un
# expand/contract —la migracion entera es la fase contract— pero demasiado grueso
# para una sola operacion. Una tabla nueva que ademas necesita un `UNIQUE (id,
# tenant_id)` sobre una tabla vieja no puede silenciar de paso un `drop_column`
# que alguien agregue el mes que viene.
#
#     op.create_unique_constraint(...)  # migracion-segura: `id` ya es la PK
#
# El caso que lo motivo: las FK compuestas contra `(id, tenant_id)` que exigen
# las tablas de union con `tenant_id` propio. PostgreSQL pide un indice unico
# que cubra esas dos columnas, y como `id` ya es unico, la constraint no puede
# ser violada por ningun dato existente. Va a repetirse en cada tabla de union
# que venga —CRM, actividades, documentos—, asi que se resuelve una vez.
MARCADOR_LINEA = re.compile(r"#\s*migracion-segura:", re.IGNORECASE)

_NUMERO_DE_LINEA = re.compile(r"^linea (\d+):")

# Operaciones de Alembic que rompen hacia atras por si solas.
OPERACIONES_DESTRUCTIVAS = {
    "drop_column": "borra una columna que la version anterior puede seguir escribiendo",
    "drop_table": "borra una tabla que la version anterior puede seguir usando",
    "rename_table": "renombrar no es aditivo: la version anterior busca el nombre viejo",
}

# En que argumento posicional viaja el nombre de la tabla. Lo que no figura acá
# la trae primera, que es el caso comun.
POSICION_DE_LA_TABLA = {
    "create_unique_constraint": 1,  # (nombre_constraint, tabla, columnas)
    "create_check_constraint": 1,  # (nombre_constraint, tabla, condicion)
    "create_index": 1,  # (nombre_indice, tabla, columnas)
}

# SQL crudo dentro de op.execute(). Se mira el texto porque no hay AST de SQL.
SQL_DESTRUCTIVO = (
    (re.compile(r"\bDROP\s+(?:TABLE|COLUMN)\b", re.IGNORECASE), "DROP TABLE/COLUMN"),
    (re.compile(r"\bRENAME\s+(?:TO|COLUMN)\b", re.IGNORECASE), "RENAME"),
    (re.compile(r"\bSET\s+NOT\s+NULL\b", re.IGNORECASE), "SET NOT NULL"),
    (re.compile(r"\bADD\s+CONSTRAINT\b", re.IGNORECASE), "ADD CONSTRAINT"),
    # ⚠️ AGREGADO EL 18-AGO-2026, y el gate estuvo ciego a esto hasta entonces.
    #
    # Un `REVOKE` no toca el esquema, asi que no parece DDL destructivo. Pero
    # rompe hacia atras exactamente igual: si la version anterior de la
    # aplicacion escribia esa tabla, deja de poder — y en un despliegue
    # azul-verde el stack viejo sigue sirviendo trafico mientras tanto.
    #
    # Se descubrio escribiendo la migracion `010`, que revoca la escritura de
    # `plans`. Esa revision es segura y se comprobo A MANO que nada en `app/`
    # escribe la tabla; el problema es que **el gate no lo verificaba**, asi que
    # la garantia dependia de que alguien se acordara de mirar.
    (re.compile(r"\bREVOKE\b", re.IGNORECASE), "REVOKE"),
)


def _texto_literal(nodo: ast.AST) -> str:
    """Texto de un `str` o de las partes literales de un f-string.

    Las migraciones de este proyecto arman el SQL con f-strings sobre constantes
    (`op.execute(f"ALTER TABLE {TABLA} ...")`), asi que mirar solo `ast.Constant`
    dejaria pasar casi todo.
    """
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    if isinstance(nodo, ast.JoinedStr):
        return " ".join(
            parte.value
            for parte in nodo.values
            if isinstance(parte, ast.Constant) and isinstance(parte.value, str)
        )
    # Envoltorios tipo `sa.text("...")`. Es el CUARTO nivel del mismo agujero:
    # el SQL no llega como literal sino como argumento de una llamada, asi que
    # sin desenvolver esto el analisis ve una `Call` y devuelve vacio.
    #
    # Se concatenan TODOS los argumentos y no solo el primero: las migraciones
    # de este proyecto parten el SQL en varias cadenas adyacentes, y una palabra
    # como `REVOKE` puede quedar en cualquiera.
    if isinstance(nodo, ast.Call):
        return " ".join(_texto_literal(argumento) for argumento in nodo.args)
    # Cadenas partidas en varias lineas: `"SELECT ..." "FROM ..."` es un `BinOp`
    # cuando llevan `+`, y adyacentes ya las une el parser en un `Constant`.
    if isinstance(nodo, ast.BinOp):
        return f"{_texto_literal(nodo.left)} {_texto_literal(nodo.right)}"
    return ""


def _operacion(llamada: ast.Call) -> str:
    """Nombre de la operacion en `op.<algo>(...)`, o cadena vacia."""
    funcion = llamada.func
    if isinstance(funcion, ast.Attribute) and isinstance(funcion.value, ast.Name):
        if funcion.value.id == "op":
            return funcion.attr
    return ""


def _kwarg(llamada: ast.Call, nombre: str) -> ast.AST | None:
    for palabra in llamada.keywords:
        if palabra.arg == nombre:
            return palabra.value
    return None


def _constantes_de_modulo(arbol: ast.Module) -> dict[str, str]:
    """Constantes `NOMBRE = "texto"` del nivel de modulo.

    Las migraciones de este proyecto nombran la tabla con una constante
    (`TABLA = "claves_de_idempotencia"`) y se la pasan a cada `op.*`. Sin
    resolverlas, el analisis no puede saber a que tabla apunta una operacion.
    """
    constantes: dict[str, str] = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and isinstance(nodo.value, ast.Constant):
            if isinstance(nodo.value.value, str):
                for destino in nodo.targets:
                    if isinstance(destino, ast.Name):
                        constantes[destino.id] = nodo.value.value
    return constantes


def _tabla(nodo: ast.AST | None, constantes: dict[str, str]) -> str | None:
    """Nombre de tabla a partir de un literal o de una constante de modulo."""
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    if isinstance(nodo, ast.Name):
        return constantes.get(nodo.id)
    return None


def infracciones(fuente: str) -> list[str]:
    """Operaciones de `upgrade()` que rompen hacia atras.

    Publica a proposito: los tests negativos la usan contra migraciones
    sinteticas para probar que este control detecta algo de verdad.
    """
    if MARCADOR_CONTRACT.search(fuente):
        # Fase contract declarada. La decision ya quedo visible en el diff.
        return []

    lineas = fuente.splitlines()

    arbol = ast.parse(fuente)

    # `upgrade()` Y TODA FUNCION AUXILIAR DEL MODULO.
    #
    # ⚠️ Hasta el 18-ago-2026 esto miraba SOLO el cuerpo de `upgrade()`, y era el
    # tercer agujero del mismo gate. Una migracion que hace
    #
    #     def upgrade(): _sembrar(); _revocar_escritura()
    #
    # dejaba todo su SQL fuera del analisis, porque el DDL vive en las auxiliares
    # y no en `upgrade()`. Es exactamente la forma de las migraciones `009` y
    # `010`.
    #
    # Se incluyen todas las funciones del modulo MENOS `downgrade()`: alla el DDL
    # destructivo es correcto y esperado — un downgrade que no borra lo que el
    # upgrade creo no revierte nada.
    funciones = [
        nodo
        for nodo in arbol.body
        if isinstance(nodo, ast.FunctionDef) and nodo.name != "downgrade"
    ]
    if not any(nodo.name == "upgrade" for nodo in funciones):
        return []

    constantes = _constantes_de_modulo(arbol)

    # Tablas que NACEN en este upgrade. Apretar una restriccion sobre una tabla
    # recien creada es seguro: no hay dato previo que pueda violarla, y ninguna
    # version anterior de la aplicacion le escribia. La distincion importa —
    # sin ella el gate marca `003_claves_de_idempotencia`, que crea la tabla y
    # su constraint unica en la misma operacion, y es correcta.
    nacidas: set[str] = set()
    nodos = [n for funcion in funciones for n in ast.walk(funcion)]

    for nodo in nodos:
        if isinstance(nodo, ast.Call) and _operacion(nodo) == "create_table":
            nombre = _tabla(nodo.args[0] if nodo.args else None, constantes)
            if nombre:
                nacidas.add(nombre)

    problemas: list[str] = []

    for nodo in nodos:
        if not isinstance(nodo, ast.Call):
            continue

        operacion = _operacion(nodo)
        # No todas las operaciones reciben la tabla en el mismo lugar:
        # `create_unique_constraint(nombre, tabla, cols)` la trae SEGUNDA.
        posicion = POSICION_DE_LA_TABLA.get(operacion, 0)
        objetivo = _tabla(nodo.args[posicion] if len(nodo.args) > posicion else None, constantes)
        sobre_tabla_nueva = objetivo is not None and objetivo in nacidas

        if operacion in OPERACIONES_DESTRUCTIVAS:
            problemas.append(
                f"linea {nodo.lineno}: op.{operacion}() — " f"{OPERACIONES_DESTRUCTIVAS[operacion]}"
            )

        # alter_column es ambiguo: aflojar es seguro, apretar no.
        if operacion == "alter_column" and not sobre_tabla_nueva:
            nullable = _kwarg(nodo, "nullable")
            if isinstance(nullable, ast.Constant) and nullable.value is False:
                problemas.append(
                    f"linea {nodo.lineno}: op.alter_column(nullable=False) — "
                    "la version anterior puede insertar NULL. Backfill primero, "
                    "y NOT NULL en un despliegue posterior."
                )
            if _kwarg(nodo, "new_column_name") is not None:
                problemas.append(
                    f"linea {nodo.lineno}: op.alter_column(new_column_name=...) — "
                    "renombrar no es aditivo. Agregar la nueva, backfillear, "
                    "conmutar la lectura, y borrar la vieja despues."
                )

        # Constraints que el dato existente puede violar. Sobre una tabla que
        # nace en este mismo upgrade no hay dato existente: es seguro.
        if (
            operacion in {"create_check_constraint", "create_unique_constraint"}
            and not sobre_tabla_nueva
        ):
            problemas.append(
                f"linea {nodo.lineno}: op.{operacion}() sobre "
                f"'{objetivo or '?'}' — el dato que ya escribio la version "
                "anterior puede violarla. Validar y limpiar primero, y agregarla "
                "en un despliegue posterior."
            )

        # SQL crudo — por CUALQUIER `.execute(...)`, no solo `op.execute(...)`.
        #
        # ⚠️ HASTA EL 18-AGO-2026 ESTO MIRABA UNICAMENTE `op.execute()`, y ese
        # era un agujero grande: una migracion que hace
        #
        #     conexion = op.get_bind()
        #     conexion.execute(sa.text("DROP TABLE ..."))
        #
        # pasaba entera sin ser vista. No es hipotetico — es el patron que usan
        # las migraciones `009` y `010`, escritas ese mismo dia. Lo que ejecutan
        # es seguro, pero el gate no tenia forma de saberlo: la garantia dependia
        # de que alguien se acordara de mirar el diff.
        #
        # Se mira el nombre del metodo y no el receptor, porque el receptor puede
        # llamarse como sea (`conexion`, `bind`, `sesion`). En un archivo de
        # migracion, todo `.execute()` es SQL.
        es_execute = isinstance(nodo.func, ast.Attribute) and nodo.func.attr == "execute"
        if es_execute and nodo.args:
            sql = _texto_literal(nodo.args[0])
            for patron, etiqueta in SQL_DESTRUCTIVO:
                if patron.search(sql):
                    problemas.append(f"linea {nodo.lineno}: execute() con {etiqueta}")

    return [p for p in problemas if not _exento(p, lineas)]


def _exento(problema: str, lineas: list[str]) -> bool:
    """Si la linea que produjo el hallazgo lleva el marcador `migracion-segura`.

    Se busca en la linea Y en la inmediatamente anterior, y ni una mas.

    ⚠️ La primera version miraba TRES lineas hacia arriba, y era una puerta: en

        # migracion-segura: ...
        op.create_unique_constraint(...)
        op.drop_column(...)

    el marcador alcanzaba tambien al `drop_column`. O sea que declarar una
    constraint segura habilitaba de rebote un borrado que nadie pidio. Lo
    encontro `test_el_marcador_por_linea_NO_silencia_el_resto_del_archivo`.

    Dos lineas alcanzan: `lineno` del AST apunta a la primera linea de la
    llamada, asi que el comentario de arriba queda en `lineno - 1`.
    """
    coincidencia = _NUMERO_DE_LINEA.match(problema)
    if coincidencia is None:
        return False
    numero = int(coincidencia.group(1))
    ventana = lineas[max(0, numero - 2) : numero]
    return any(MARCADOR_LINEA.search(linea) for linea in ventana)


def _migraciones() -> list[Path]:
    return sorted(p for p in VERSIONES.glob("*.py") if p.name != "__init__.py")


def test_hay_migraciones_que_revisar() -> None:
    """Si el glob deja de encontrar archivos, el gate pasa vacio.

    Sin esto, mover el directorio de migraciones apagaria el control en silencio.
    """
    assert _migraciones(), f"no se encontro ninguna migracion en {VERSIONES}"


@pytest.mark.parametrize("migracion", _migraciones(), ids=lambda p: p.name)
def test_la_migracion_no_rompe_hacia_atras(migracion: Path) -> None:
    """Regla dura 13: `upgrade()` deja funcionando a la version anterior."""
    problemas = infracciones(migracion.read_text(encoding="utf-8"))
    assert not problemas, (
        f"{migracion.name} rompe hacia atras (regla dura 13, ADR-025):\n  "
        + "\n  ".join(problemas)
        + "\n\nEl azul-verde comparte UNA base entre los dos stacks: esto deja "
        "al stack viejo sin funcionar y la reversion deja de existir.\n"
        "Si es la fase *contract* de un expand/contract ya desplegado, "
        "declaralo con:\n\n    # migracion-contract: <por que ya es seguro>\n"
    )


# ── Que el control detecta de verdad ─────────────────────────────────────────
# Sin estos casos, `infracciones()` podria devolver siempre [] y los tests de
# arriba pasarian igual.


def test_detecta_drop_column_en_upgrade() -> None:
    malo = """
from alembic import op

def upgrade() -> None:
    op.drop_column("vehiculos", "patente_vieja")

def downgrade() -> None:
    pass
"""
    problemas = infracciones(malo)
    assert any("drop_column" in p for p in problemas), problemas


def test_detecta_set_not_null() -> None:
    malo = """
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.alter_column("vehiculos", "dominio", nullable=False)
"""
    problemas = infracciones(malo)
    assert any("nullable=False" in p for p in problemas), problemas


def test_detecta_sql_crudo_destructivo_en_fstring() -> None:
    """El SQL crudo con f-string es la forma que usan las migraciones de acá."""
    malo = """
from alembic import op

TABLA = "vehiculos"

def upgrade() -> None:
    op.execute(f"ALTER TABLE {TABLA} ALTER COLUMN dominio SET NOT NULL")
"""
    problemas = infracciones(malo)
    assert any("SET NOT NULL" in p for p in problemas), problemas


def test_el_ddl_destructivo_de_downgrade_no_cuenta() -> None:
    """Es el falso positivo que marcaria las cuatro migraciones existentes."""
    correcto = """
from alembic import op

TABLA = "claves"

def upgrade() -> None:
    op.create_table(TABLA)
    op.create_index("ix_claves", TABLA, ["tenant_id"])

def downgrade() -> None:
    op.drop_index("ix_claves", table_name=TABLA)
    op.drop_table(TABLA)
    op.execute(f"DROP POLICY IF EXISTS pol ON {TABLA}")
"""
    assert infracciones(correcto) == []


def test_apretar_una_tabla_que_nace_en_el_mismo_upgrade_es_seguro() -> None:
    """Es el caso real de `003_claves_de_idempotencia`.

    No hay dato previo que pueda violar la constraint, ni version anterior de la
    aplicacion escribiendo en esa tabla: nace acá.
    """
    correcto = """
from alembic import op

TABLA = "claves_de_idempotencia"

def upgrade() -> None:
    op.create_table(TABLA)
    op.create_unique_constraint(f"uq_{TABLA}_tenant_key", TABLA, ["tenant_id", "key"])
"""
    assert infracciones(correcto) == []


def test_apretar_una_tabla_PREEXISTENTE_si_se_marca() -> None:
    """La exencion de arriba no puede volverse un agujero.

    Misma operacion, tabla que NO nace en este upgrade: el dato que ya escribio
    la version anterior puede violarla.
    """
    malo = """
from alembic import op

def upgrade() -> None:
    op.create_unique_constraint("uq_vehiculos_dominio", "vehiculos", ["dominio"])
"""
    problemas = infracciones(malo)
    assert any("create_unique_constraint" in p for p in problemas), problemas
    assert any("vehiculos" in p for p in problemas), problemas


def test_not_null_sobre_tabla_preexistente_se_marca_igual() -> None:
    """La exencion es por tabla, no por operacion."""
    malo = """
from alembic import op

def upgrade() -> None:
    op.create_table("otra")
    op.alter_column("vehiculos", "dominio", nullable=False)
"""
    problemas = infracciones(malo)
    assert any("nullable=False" in p for p in problemas), problemas


def test_el_marcador_contract_habilita_la_fase_de_borrado() -> None:
    contract = """
from alembic import op

# migracion-contract: la columna quedo sin uso desde la revision 007
def upgrade() -> None:
    op.drop_column("vehiculos", "patente_vieja")
"""
    assert infracciones(contract) == []


def test_lo_aditivo_pasa() -> None:
    """Crear y aflojar es seguro; el gate no debe estorbar el trabajo normal."""
    aditivo = """
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.create_table("nueva")
    op.add_column("vehiculos", sa.Column("color", sa.String(), nullable=True))
    op.create_index("ix_color", "vehiculos", ["color"])
    op.drop_index("ix_viejo", table_name="vehiculos")
    op.drop_constraint("uq_viejo", "vehiculos", type_="unique")
    op.alter_column("vehiculos", "notas", nullable=True)
"""
    assert infracciones(aditivo) == []


# ── Los cuatro agujeros que este gate tuvo hasta el 18-ago-2026 ─────────────
#
# Los cuatro se descubrieron escribiendo las migraciones `009` y `010`, que usan
# exactamente el patron que el analisis no veia. Cada uno tiene su test porque
# un gate ciego pasa igual de verde que uno que funciona.


def test_detecta_revoke() -> None:
    """Un `REVOKE` no toca el esquema, pero rompe hacia atras igual.

    Si la version anterior escribia esa tabla, deja de poder — y en azul-verde
    el stack viejo sigue sirviendo trafico mientras tanto.
    """
    fuente = "def upgrade():\n" "    op.execute('REVOKE INSERT, UPDATE ON plans FROM \"app\"')\n"

    assert any("REVOKE" in problema for problema in infracciones(fuente))


def test_detecta_sql_ejecutado_fuera_de_op() -> None:
    """`op.get_bind().execute(...)` es la puerta que dejaba pasar TODO.

    No solo el `REVOKE`: por esta via pasaban `DROP TABLE`, `SET NOT NULL` y
    cualquier otra cosa, porque el analisis solo reconocia `op.<algo>()`.
    """
    fuente = (
        "def upgrade():\n"
        "    conexion = op.get_bind()\n"
        "    conexion.execute('DROP TABLE vehiculos')\n"
    )

    assert any("DROP TABLE" in problema for problema in infracciones(fuente))


def test_detecta_sql_en_una_funcion_auxiliar() -> None:
    """El DDL de estas migraciones vive en auxiliares, no en `upgrade()`."""
    fuente = (
        "def upgrade():\n"
        "    _limpiar()\n"
        "\n"
        "def _limpiar():\n"
        "    op.execute('ALTER TABLE vehiculos ALTER COLUMN dominio SET NOT NULL')\n"
    )

    assert any("SET NOT NULL" in problema for problema in infracciones(fuente))


def test_detecta_sql_envuelto_en_sa_text() -> None:
    """El idioma real del proyecto: `conexion.execute(sa.text("..."))`.

    Sin desenvolver la llamada, el analisis ve una `Call` y lee cadena vacia.
    """
    fuente = "def upgrade():\n" "    op.get_bind().execute(sa.text('DROP TABLE vehiculos'))\n"

    assert any("DROP TABLE" in problema for problema in infracciones(fuente))


def test_el_downgrade_sigue_sin_contar_aunque_tenga_auxiliares() -> None:
    """Ampliar el analisis a las auxiliares no puede arrastrar al downgrade.

    Alla el DDL destructivo es correcto: un downgrade que no borra lo que su
    upgrade creo no revierte nada.
    """
    fuente = (
        "def upgrade():\n"
        "    op.create_table('vehiculos')\n"
        "\n"
        "def downgrade():\n"
        "    op.execute('DROP TABLE vehiculos')\n"
    )

    assert infracciones(fuente) == []


# ── El marcador por linea, y que no sea una puerta abierta ───────────────────

_CON_MARCADOR = """
def upgrade() -> None:
    # migracion-segura: `id` ya es la PK
    op.create_unique_constraint("uq", "users", ["id", "tenant_id"])
"""

_MARCADOR_Y_ADEMAS_UN_DROP = """
def upgrade() -> None:
    # migracion-segura: `id` ya es la PK
    op.create_unique_constraint("uq", "users", ["id", "tenant_id"])
    op.drop_column("users", "telefono")
"""


def test_el_marcador_por_linea_exenta_esa_operacion() -> None:
    assert infracciones(_CON_MARCADOR) == []


def test_el_marcador_por_linea_NO_silencia_el_resto_del_archivo() -> None:
    """La diferencia con `migracion-contract`, y el motivo de que exista.

    El marcador de archivo devuelve `[]` para todo. Este exenta una operacion y
    deja el gate encendido para las demas — si no, declarar una constraint segura
    abriria la puerta a un `drop_column` que nadie pidio.
    """
    problemas = infracciones(_MARCADOR_Y_ADEMAS_UN_DROP)
    assert len(problemas) == 1
    assert "drop_column" in problemas[0]


def test_sin_marcador_la_misma_constraint_se_reporta() -> None:
    """Contrapeso: si el detector no marcara nunca esta operacion, los dos tests
    de arriba pasarian sin probar que la exencion hace algo."""
    sin_marcador = _CON_MARCADOR.replace("    # migracion-segura: `id` ya es la PK\n", "")
    assert len(infracciones(sin_marcador)) == 1
