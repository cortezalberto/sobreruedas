#!/usr/bin/env python3
"""Gate de cobertura del pipeline — tareas 8.2 y 8.4 de C-01 (`T-003`).

POR QUE NO ALCANZA `fail_under` DE COVERAGE.PY
──────────────────────────────────────────────
`fail_under` compara un solo numero. Con `branch = true` ese numero es

    (lineas cubiertas + ramas cubiertas) / (sentencias + ramas)

o sea un promedio ponderado. ADR-014 no pide un promedio: pide **80 % de
lineas Y 60 % de ramas**, cada uno por su lado. Un modulo con 95 % de lineas y
20 % de ramas da 82 % combinado y pasa `fail_under = 80` sin que nadie lo note,
que es justo la forma en que la logica condicional se cuela sin tests.

`fail_under = 80` sigue en pyproject.toml como red de contencion para quien
corra `pytest --cov` a mano. El gate de verdad, el que bloquea la integracion,
es este script.

NO DECRECIMIENTO (Art. 2 de la constitucion)
────────────────────────────────────────────
Con `--base` se compara contra la medicion de `main`. Cumplir el piso no
alcanza: la cobertura tampoco puede bajar. Y al reves, no bajar tampoco alcanza
si no se llega al piso — los dos controles son independientes y ambos bloquean.

Si la base no existe o esta rota **no se bloquea**: la primera corrida no tiene
contra que comparar, y ausencia de base no es evidencia de retroceso. Se avisa
en el log y se sigue.

USO
───
    python tools/check-coverage.py --coverage-json backend/coverage.json
    python tools/check-coverage.py --coverage-json cobertura.json --base base.json
    python tools/check-coverage.py ... --min-lineas 70 --min-ramas 50

CODIGOS DE SALIDA
─────────────────
    0  se cumplen los umbrales y no hubo retroceso
    1  umbral incumplido o cobertura en baja  -> falta escribir tests
    2  no se pudo medir (archivo ausente, roto o sin ramas) -> pipeline roto

El 1 y el 2 se distinguen a proposito: confundirlos manda a buscar tests que no
faltan cuando en realidad lo que fallo fue el paso anterior del workflow.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple, NoReturn

MIN_LINEAS_POR_DEFECTO = 80.0  # Constitucion Art. 2
MIN_RAMAS_POR_DEFECTO = 60.0  # ADR-014


class Medicion(NamedTuple):
    """Los dos porcentajes que ADR-014 mide por separado."""

    lineas: float
    ramas: float


def porcentaje(cubierto: int, total: int) -> float:
    """Redondeado a 2 decimales, igual que lo que se imprime.

    Comparar contra el valor redondeado y no contra el crudo evita el reporte
    absurdo de "79.995 % < 80 %" mostrado en pantalla como "80.00 % < 80.00 %".

    Total 0 devuelve 100: no hay nada que cubrir, asi que no hay nada que
    reprochar. Un proyecto sin una sola bifurcacion tiene 0 ramas, y 0/0 no es
    0 % — es "no aplica".
    """
    if total == 0:
        return 100.0
    return round(cubierto / total * 100, 2)


def salir_sin_medir(motivo: str) -> NoReturn:
    print(f"[ERROR] {motivo}")
    print("        No se pudo medir la cobertura. Esto es un fallo del pipeline.")
    sys.exit(2)


def leer_medicion(ruta: Path) -> Medicion:
    """Lee el `coverage.json` que emite `coverage json`.

    Sale con codigo 2 ante cualquier problema: que no se pueda medir es un
    pipeline roto, no un umbral incumplido.
    """
    if not ruta.exists():
        salir_sin_medir(f"no existe el archivo de cobertura: {ruta}")

    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        salir_sin_medir(f"{ruta} no es JSON valido: {error}")

    totales = datos.get("totals")
    if not isinstance(totales, dict):
        salir_sin_medir(f"{ruta} no trae la clave 'totals'")

    # Sin `branch = true` en la configuracion de coverage, el JSON viene sin
    # num_branches. Dar la corrida por buena apagaria el gate de ramas en
    # silencio, que es peor que fallar: nadie se entera hasta que la deuda ya
    # esta adentro.
    if "num_branches" not in totales or "covered_branches" not in totales:
        salir_sin_medir(
            f"{ruta} no trae medicion de ramas. "
            "Falta `branch = true` en [tool.coverage.run] — sin eso el umbral "
            "de ramas de ADR-014 no se puede verificar."
        )

    return Medicion(
        lineas=porcentaje(totales["covered_lines"], totales["num_statements"]),
        ramas=porcentaje(totales["covered_branches"], totales["num_branches"]),
    )


def umbral(texto: str) -> float:
    """Un porcentaje. Fuera de 0-100 es error de uso, no cobertura insuficiente."""
    try:
        valor = float(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{texto!r} no es un numero") from None
    if not 0 <= valor <= 100:
        raise argparse.ArgumentTypeError(f"{valor} esta fuera del rango 0-100")
    return valor


def consola_tolerante() -> None:
    """Que un caracter que la consola no sabe representar no mate al gate.

    Un gate que se cae al IMPRIMIR miente dos veces: no informa la cobertura, y
    sale con un codigo que se lee identico a "la cobertura no alcanza". El
    diagnostico arranca mirando los tests equivocados.

    Todo lo que este script imprime es ASCII a proposito —misma decision que
    `tools/check-services.sh`, por el mismo motivo: la consola de Windows es
    cp1252—, asi que esto no deberia activarse nunca. Existe por lo que venga
    despues: el dia que alguien agregue un simbolo lindo, el gate tiene que
    seguir diciendo su numero en vez de morir escribiendolo.
    """
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is not None:
            reconfigurar(errors="replace")


def main() -> int:
    consola_tolerante()

    analizador = argparse.ArgumentParser(
        description="Verifica lineas y ramas por separado, como pide ADR-014.",
    )
    analizador.add_argument(
        "--coverage-json",
        type=Path,
        default=Path("backend/coverage.json"),
        help="salida de `coverage json` (por defecto: backend/coverage.json)",
    )
    analizador.add_argument("--min-lineas", type=umbral, default=MIN_LINEAS_POR_DEFECTO)
    analizador.add_argument("--min-ramas", type=umbral, default=MIN_RAMAS_POR_DEFECTO)
    analizador.add_argument(
        "--base",
        type=Path,
        default=None,
        help="cobertura de `main` para verificar que no decrece (Art. 2)",
    )
    analizador.add_argument(
        "--etiqueta",
        default="backend",
        help="nombre que se muestra en el informe (backend, frontend, ...)",
    )
    args = analizador.parse_args()

    actual = leer_medicion(args.coverage_json)

    print(f"-- Cobertura de {args.etiqueta} " + "-" * 40)
    print(f"   lineas : {actual.lineas:6.2f} %   (piso {args.min_lineas:.2f} %)")
    print(f"   ramas  : {actual.ramas:6.2f} %   (piso {args.min_ramas:.2f} %)")

    fallos: list[str] = []

    # ── Umbrales absolutos. Se evaluan los dos: cortar en el primero obliga a
    #    dos corridas para enterarse de que faltaban las dos cosas.
    if actual.lineas < args.min_lineas:
        fallos.append(
            f"cobertura de lineas {actual.lineas:.2f} % por debajo del piso "
            f"{args.min_lineas:.2f} % (Constitucion Art. 2)"
        )
    if actual.ramas < args.min_ramas:
        fallos.append(
            f"cobertura de ramas {actual.ramas:.2f} % por debajo del piso "
            f"{args.min_ramas:.2f} % (ADR-014)"
        )

    # ── No decrecimiento contra main.
    if args.base is not None:
        base = leer_base(args.base)
        if base is None:
            print("   base   : sin base con que comparar - no se verifica el decrecimiento")
        else:
            print(f"   base   : lineas {base.lineas:.2f} %  ramas {base.ramas:.2f} %")
            if actual.lineas < base.lineas:
                fallos.append(
                    f"la cobertura de lineas decrece: {base.lineas:.2f} % -> "
                    f"{actual.lineas:.2f} %"
                )
            if actual.ramas < base.ramas:
                fallos.append(
                    f"la cobertura de ramas decrece: {base.ramas:.2f} % -> {actual.ramas:.2f} %"
                )

    if fallos:
        print()
        for fallo in fallos:
            print(f"   [FAIL] {fallo}")
        print()
        print("   La integracion queda bloqueada. Escribi los tests que faltan.")
        return 1

    print("   [OK] se cumplen los umbrales y la cobertura no decrece")
    return 0


def leer_base(ruta: Path) -> Medicion | None:
    """Como `leer_medicion` pero tolerante: ante cualquier problema devuelve
    None en vez de abortar.

    La asimetria es deliberada. Que falte la medicion ACTUAL es un pipeline
    roto; que falte la de `main` es, la mayoria de las veces, la primera vez.
    """
    if not ruta.exists():
        return None
    try:
        totales = json.loads(ruta.read_text(encoding="utf-8"))["totals"]
        return Medicion(
            lineas=porcentaje(totales["covered_lines"], totales["num_statements"]),
            ramas=porcentaje(totales["covered_branches"], totales["num_branches"]),
        )
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError):
        return None


if __name__ == "__main__":
    sys.exit(main())
