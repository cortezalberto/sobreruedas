#!/usr/bin/env python3
"""Verifica que todo enlace markdown relativo del repositorio apunte a algo que existe.

Tarea 1.6 de `foundation-setup` (C-01). La mudanza de `docs/` a `docs/sdd/` y de
`decisions/` a `docs/adr/` toca enlaces en decenas de archivos; sin verificación
automatizada, un enlace roto pasa desapercibido hasta que alguien lo clickea.

Uso:
    python tools/check-md-links.py

Salida: 0 si no hay enlaces rotos, 1 si hay al menos uno.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parent.parent

# Directorios que no se auditan: dependencias, artefactos de build y control de versiones.
EXCLUDED_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".next", ".pytest_cache"}

# `[texto](destino)` — se descartan las imágenes `![...]` mirando el carácter previo.
LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)")

# Enlaces que no apuntan al sistema de archivos y por lo tanto no se resuelven acá.
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in REPO.rglob("*.md")
        if not EXCLUDED_DIRS & set(path.relative_to(REPO).parts)
    )


def target_exists(source: Path, target: str) -> bool:
    # Se descarta el ancla: `archivo.md#seccion` se verifica solo como archivo.
    path_part = unquote(target.split("#", 1)[0]).strip()
    if not path_part:
        return True  # ancla dentro del mismo archivo
    if path_part.startswith("/"):
        resolved = REPO / path_part.lstrip("/")
    else:
        resolved = (source.parent / path_part).resolve()
    return resolved.exists()


def main() -> int:
    broken: list[tuple[Path, int, str]] = []
    checked = 0
    files = markdown_files()

    for path in files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for target in LINK_RE.findall(line):
                if target.startswith(EXTERNAL_PREFIXES):
                    continue
                checked += 1
                if not target_exists(path, target):
                    broken.append((path.relative_to(REPO), lineno, target))

    # Solo ASCII: la consola de Windows por defecto es cp1252 y no encodea marcas Unicode.
    print(f"Archivos .md auditados : {len(files)}")
    print(f"Enlaces relativos      : {checked}")

    if not broken:
        print("Enlaces rotos          : 0  [OK]")
        return 0

    print(f"Enlaces rotos          : {len(broken)}  [FAIL]\n")
    for rel_path, lineno, target in broken:
        print(f"  {rel_path}:{lineno}  ->  {target}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
