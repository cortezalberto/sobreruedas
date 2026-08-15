"""SONDA DESCARTABLE — tarea 8.9. NO MERGEAR.

Ejercita `contar_umbrales_superados` con un valor que supera TODOS los umbrales.
Efecto buscado: se ejecutan todas las sentencias --cobertura de lineas alta-- y
se toma una sola rama de cada `if` --cobertura de ramas por el piso.

Es la forma exacta en que la logica condicional entra sin tests: un archivo que
parece cubierto porque sus lineas se ejecutan.
"""

from __future__ import annotations

from app.sonda_cobertura import contar_umbrales_superados


def test_sonda_todas_las_lineas_una_sola_rama() -> None:
    """Pasa y deja el archivo con 60 ramas sin ejercitar."""
    assert contar_umbrales_superados(1000) == 60
