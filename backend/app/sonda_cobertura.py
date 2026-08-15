"""SONDA DESCARTABLE — tarea 8.9. NO MERGEAR.

Este modulo existe para provocar EXACTAMENTE el agujero que `fail_under`
deja pasar y que `tools/check-coverage.py` tiene que atrapar.

Sus 60 condicionales se ejecutan enteros desde el test, asi que la cobertura
de LINEAS queda altisima. Pero el test recorre una sola rama de cada `if`, asi
que la cobertura de RAMAS se desploma.

Con `branch = true`, el numero que compara `fail_under` es el promedio ponderado
de lineas y ramas juntas, y ese promedio queda por ENCIMA del 80: `fail_under`
deja pasar este archivo sin decir nada. ADR-014 pide 80 % de lineas Y 60 % de
ramas por separado, y el piso de ramas es el que este modulo rompe.

Si la corrida sale verde, el gate de ADR-014 no esta bloqueando.

Se borra junto con la rama `sonda/8.9-el-gate-bloquea`.
"""

from __future__ import annotations


def contar_umbrales_superados(umbral: int) -> int:
    """Cuenta cuantos de los 60 umbrales supera `umbral`."""
    alcanzados = 0
    if umbral > 0:
        alcanzados += 1

    if umbral > 1:
        alcanzados += 1

    if umbral > 2:
        alcanzados += 1

    if umbral > 3:
        alcanzados += 1

    if umbral > 4:
        alcanzados += 1

    if umbral > 5:
        alcanzados += 1

    if umbral > 6:
        alcanzados += 1

    if umbral > 7:
        alcanzados += 1

    if umbral > 8:
        alcanzados += 1

    if umbral > 9:
        alcanzados += 1

    if umbral > 10:
        alcanzados += 1

    if umbral > 11:
        alcanzados += 1

    if umbral > 12:
        alcanzados += 1

    if umbral > 13:
        alcanzados += 1

    if umbral > 14:
        alcanzados += 1

    if umbral > 15:
        alcanzados += 1

    if umbral > 16:
        alcanzados += 1

    if umbral > 17:
        alcanzados += 1

    if umbral > 18:
        alcanzados += 1

    if umbral > 19:
        alcanzados += 1

    if umbral > 20:
        alcanzados += 1

    if umbral > 21:
        alcanzados += 1

    if umbral > 22:
        alcanzados += 1

    if umbral > 23:
        alcanzados += 1

    if umbral > 24:
        alcanzados += 1

    if umbral > 25:
        alcanzados += 1

    if umbral > 26:
        alcanzados += 1

    if umbral > 27:
        alcanzados += 1

    if umbral > 28:
        alcanzados += 1

    if umbral > 29:
        alcanzados += 1

    if umbral > 30:
        alcanzados += 1

    if umbral > 31:
        alcanzados += 1

    if umbral > 32:
        alcanzados += 1

    if umbral > 33:
        alcanzados += 1

    if umbral > 34:
        alcanzados += 1

    if umbral > 35:
        alcanzados += 1

    if umbral > 36:
        alcanzados += 1

    if umbral > 37:
        alcanzados += 1

    if umbral > 38:
        alcanzados += 1

    if umbral > 39:
        alcanzados += 1

    if umbral > 40:
        alcanzados += 1

    if umbral > 41:
        alcanzados += 1

    if umbral > 42:
        alcanzados += 1

    if umbral > 43:
        alcanzados += 1

    if umbral > 44:
        alcanzados += 1

    if umbral > 45:
        alcanzados += 1

    if umbral > 46:
        alcanzados += 1

    if umbral > 47:
        alcanzados += 1

    if umbral > 48:
        alcanzados += 1

    if umbral > 49:
        alcanzados += 1

    if umbral > 50:
        alcanzados += 1

    if umbral > 51:
        alcanzados += 1

    if umbral > 52:
        alcanzados += 1

    if umbral > 53:
        alcanzados += 1

    if umbral > 54:
        alcanzados += 1

    if umbral > 55:
        alcanzados += 1

    if umbral > 56:
        alcanzados += 1

    if umbral > 57:
        alcanzados += 1

    if umbral > 58:
        alcanzados += 1

    if umbral > 59:
        alcanzados += 1
    return alcanzados
