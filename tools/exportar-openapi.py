"""Exporta el contrato publico a `docs/openapi.yaml` — C-05, tarea 5.12.

    make openapi

Es de donde el frontend genera sus tipos (C-08), asi que el archivo SE VERSIONA:
un contrato que solo existe en la memoria del proceso no se puede revisar en un
diff ni comparar entre ramas, y es justo lo que hay que mirar cuando una ruta
cambia de forma.

⚠️ NO SE EDITA A MANO. `backend/tests/unit/test_openapi_exportado.py` vigila que
los seis endpoints retirados por `ADR-026` §3 no aparezcan nunca: si aparecen,
C-08 genera un cliente que llama a rutas inexistentes y el error sale recien en
runtime, en el navegador de alguien.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
BACKEND = RAIZ / "backend"
SALIDA = RAIZ / "docs" / "openapi.yaml"

# El export NO habla con ningun servicio: solo necesita que `Settings` valide
# para poder construir la app. Valores de relleno, nunca reales — y por eso el
# script no lee `.env`.
_RELLENO = {
    "DATABASE_URL": "postgresql+asyncpg://x:x@localhost:5432/x",
    "KEYCLOAK_CLIENT_SECRET": "x",
    "S3_ACCESS_KEY": "x",
    "S3_SECRET_KEY": "x",
    "TENANT_SECRETS_MASTER_KEY": "x" * 32,
}


def main() -> int:
    for clave, valor in _RELLENO.items():
        os.environ.setdefault(clave, valor)

    sys.path.insert(0, str(BACKEND))
    from app.main import create_app

    esquema = create_app().openapi()

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(
        "# GENERADO POR `make openapi` — NO EDITAR A MANO.\n"
        "# Fuente: los routers de `backend/app/`. Ver `tools/exportar-openapi.py`.\n"
        + yaml.safe_dump(esquema, allow_unicode=True, sort_keys=True),
        encoding="utf-8",
    )
    print(f"escrito {SALIDA} — {len(esquema.get('paths', {}))} rutas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
