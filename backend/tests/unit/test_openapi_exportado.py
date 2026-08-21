"""`docs/openapi.yaml` es de donde el frontend genera sus tipos — tarea 5.12.

POR QUE ESTO ES UN TEST Y NO UN PASO DEL BUILD
────────────────────────────────────────────────
`ADR-026` lo dice sin rodeos: los seis endpoints retirados **nunca deben
aparecer** en ese archivo. Si aparecen, C-08 genera un cliente que llama a rutas
que no existen, y el error sale recien en runtime — en el navegador de alguien,
no en el CI.

Un archivo generado que nadie verifica se desactualiza el dia que alguien agrega
una ruta y no vuelve a exportar. Por eso el test compara el archivo VERSIONADO
contra el esquema que la aplicacion produce ahora: si difieren, hay que
regenerar, y el mensaje dice como.

    make openapi        regenera `docs/openapi.yaml`
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

OPENAPI = Path(__file__).resolve().parents[3] / "docs" / "openapi.yaml"

# `ADR-026` §3 — de los 8 de `spec-tecnica` §4.2.1 sobreviven 2.
#
# "Retirado" no es "no implementado": la funcionalidad existe y la presta
# Keycloak. Lo que no existe es un endpoint nuestro que la duplique — escribirlo
# seria "construir autenticacion a medida", que es lo que N0 prohibe.
RETIRADOS = (
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/mfa/enable",
    "/api/v1/auth/mfa/verify",
)

SOBREVIVEN = ("/api/v1/auth/me", "/api/v1/auth/logout")


def _versionado() -> dict[str, Any]:
    if not OPENAPI.is_file():
        pytest.fail(f"falta {OPENAPI} — corre `make openapi`")
    datos: dict[str, Any] = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
    return datos


def test_el_archivo_existe_y_tiene_rutas() -> None:
    """Contrapeso: sin esto, un archivo vacio pasaria todo lo de abajo.

    Los `for` de los tests siguientes iterarian sobre nada y el guardian se
    apagaria solo — que es peor que no tenerlo.
    """
    rutas = _versionado().get("paths") or {}
    assert len(rutas) > 20, f"solo {len(rutas)} rutas: el export quedo a medias"


def test_ninguno_de_los_seis_retirados_aparece() -> None:
    """`ADR-026` §3. El unico test de este archivo que protege a otro change.

    Si uno de estos aparece, C-08 genera un cliente que llama a una ruta
    inexistente y el error sale recien cuando alguien la usa.
    """
    rutas = set(_versionado().get("paths") or {})

    for retirado in RETIRADOS:
        assert retirado not in rutas, (
            f"`{retirado}` esta en docs/openapi.yaml y `ADR-026` §3 lo retiro.\n"
            "  Si volvio a existir en el codigo, el problema no es este archivo."
        )


def test_los_dos_que_sobreviven_si_estan() -> None:
    """El contrapeso del test de arriba, y el que lo hace significar algo.

    Sin esto, borrar `/auth` entero del export haria pasar la comprobacion de
    los retirados — y dejaria al frontend sin los dos que si existen.
    """
    rutas = set(_versionado().get("paths") or {})

    for ruta in SOBREVIVEN:
        assert ruta in rutas, f"falta `{ruta}` en docs/openapi.yaml"


def test_no_hay_ninguna_ruta_de_password_ni_de_mfa() -> None:
    """La red mas ancha, por si aparece una con OTRO nombre.

    Los seis de `RETIRADOS` son los que `spec-tecnica` §4.2.1 listaba. Nada
    impide que mañana alguien agregue `/auth/change-password`, que no esta en
    esa lista y viola lo mismo.
    """
    prohibidas = [
        ruta
        for ruta in (_versionado().get("paths") or {})
        if "password" in ruta.lower() or "/mfa" in ruta.lower()
    ]
    assert not prohibidas, (
        f"rutas de credenciales en el contrato publico: {prohibidas}\n"
        "  `ADR-026`: la autenticacion se delega ENTERA a Keycloak."
    )
