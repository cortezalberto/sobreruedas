"""La copia de `RN-ST-05` en el frontend no se despega de la de acá.

POR QUE EXISTE ESTA COPIA
──────────────────────────
`frontend-web/src/lib/stock.ts` tiene la tabla de transiciones para poder
ofrecer botones que tengan sentido: sin ella, la interfaz o no ofrece nada o
ofrece los seis estados y cinco fallan.

Lo que el frontend **NO** copia es la matriz de permisos. La division la fija
`ADR-034`: que transiciones existen es dominio —igual para todos, gerente
incluido— y quien puede hacer cada una lo decide `rbac.py`. Copiar la maquina de
estados deja, en el peor caso, un boton de mas que el backend rechaza. Copiar la
matriz daria una segunda fuente de verdad sobre permisos, editable desde las
herramientas del navegador.

POR QUE EL TEST VIVE DEL LADO DEL BACKEND
──────────────────────────────────────────
Porque aca esta el original. Un test en el frontend compararia su copia contra
si misma, o tendria que leer Python desde TypeScript — al reves, leer un literal
de TypeScript desde Python es un `re` de cinco lineas.

Si esto falla, **la que manda es la de `schemas.py`**: el frontend se corrige.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.modules.stock.schemas import TRANSICIONES_PERMITIDAS

ESPEJO = Path(__file__).resolve().parents[3] / "frontend-web" / "src" / "lib" / "stock.ts"

# `['available', ['reserved', 'in_workshop', 'archived']],`
_FILA = re.compile(r"\['(\w+)',\s*\[([^\]]*)\]\]")


def _tabla_del_backend() -> dict[str, set[str]]:
    tabla: dict[str, set[str]] = {}
    for desde, hasta in TRANSICIONES_PERMITIDAS:
        tabla.setdefault(desde.value, set()).add(hasta.value)
    return tabla


def _tabla_del_frontend() -> dict[str, set[str]]:
    fuente = ESPEJO.read_text(encoding="utf-8")
    # Se acota al literal de `TRANSICIONES` para no capturar cualquier arreglo
    # que aparezca en el archivo.
    bloque = fuente.split("export const TRANSICIONES")[1].split("]);")[0]

    return {
        coincidencia.group(1): {
            valor.strip().strip("'") for valor in coincidencia.group(2).split(",") if valor.strip()
        }
        for coincidencia in _FILA.finditer(bloque)
    }


def test_el_archivo_del_espejo_existe() -> None:
    """Si el frontend se mueve, este test avisa en vez de pasar en verde.

    Un test que lee un archivo inexistente y no lo verifica se convierte en
    ninguno — sin ruido y sin que nadie se entere.
    """
    assert ESPEJO.is_file(), f"no esta {ESPEJO}"


def test_la_tabla_del_frontend_no_esta_vacia() -> None:
    """Contrapeso del parseo. Si el `re` deja de matchear —porque alguien
    reformatea el literal— la comparacion de abajo compararia dos cosas vacias y
    pasaria."""
    assert len(_tabla_del_frontend()) == 6


def test_las_dos_tablas_de_transiciones_dicen_lo_mismo() -> None:
    """`RN-ST-05`, de los dos lados.

    Si difieren, la que manda es la de `schemas.py`: el frontend se corrige.
    """
    backend = _tabla_del_backend()
    frontend = _tabla_del_frontend()

    assert frontend == backend, (
        "la tabla de transiciones del frontend se despego de la del backend.\n"
        f"  solo en el backend:  { {k: sorted(backend[k] - frontend.get(k, set())) for k in backend if backend[k] - frontend.get(k, set())} }\n"
        f"  solo en el frontend: { {k: sorted(frontend[k] - backend.get(k, set())) for k in frontend if frontend[k] - backend.get(k, set())} }"
    )


def test_el_frontend_no_copia_la_matriz_de_permisos() -> None:
    """La otra mitad de `ADR-034`, y la que importa mas.

    La maquina de estados se copia; la matriz NO. Si algun dia aparece un rol
    escrito en el modulo de stock del frontend, es que alguien empezo a decidir
    permisos del lado del cliente — y eso se edita con las herramientas del
    navegador.
    """
    fuente = ESPEJO.read_text(encoding="utf-8")
    # Se busca en el CODIGO, no en los comentarios: el encabezado del archivo
    # explica por que no se copian y nombra los roles al hacerlo.
    codigo = "\n".join(
        linea for linea in fuente.splitlines() if not linea.lstrip().startswith(("*", "//", "/*"))
    )

    for rol in ("manager", "salesperson", "admin_staff", "super_admin"):
        assert rol not in codigo, f"el frontend decide permisos: menciona '{rol}'"
