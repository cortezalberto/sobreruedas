"""SONDA DESCARTABLE — escenario "Error de tipado estatico". NO MERGEAR.

La regla dura 6 exige `mypy --strict` sobre el codigo de aplicacion, y la spec
`platform/delivery-pipeline` dice que un error de tipado bloquea la
integracion. Tampoco se comprobo nunca.

La funcion esta anotada `-> int` y devuelve un `str`. Es un error de tipado
limpio, sin trucos: mypy lo marca como [return-value].

Tiene que pasar `ruff` y `black` para que el control llegue a `mypy`. Si el
rojo cae en cualquier otro step, la sonda no prueba el escenario.

Se borra junto con la rama.
"""

from __future__ import annotations


def vehiculos_en_stock() -> int:
    """Anotada como int, devuelve str. `mypy --strict` debe rechazarlo."""
    return "tres"
