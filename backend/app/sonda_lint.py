"""SONDA DESCARTABLE — escenario "Violacion de reglas de linting". NO MERGEAR.

La spec `platform/delivery-pipeline` dice que una violacion de linting bloquea
la integracion. Nunca se comprobo: en todas las corridas hasta ahora el codigo
estaba conforme, asi que lo unico demostrado era que el codigo limpio pasa.

Este modulo importa `json` y no lo usa. Es F401, dentro del `select` del
proyecto (E, W, F, I, B, UP, S). Si `lint-backend` queda en verde, `ruff` no
esta bloqueando.

Se borra junto con la rama.
"""

from __future__ import annotations

import json


def identificar_sonda() -> str:
    """Existe para que el modulo no sea solo el import."""
    return "sonda de linting"
