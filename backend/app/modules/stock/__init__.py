"""Modulo de stock — C-14.

⚠️ TODAVIA NO HAY ROUTER, NI MODELOS ORM, NI SERVICIO. Solo los contratos.

Se escribieron los schemas por adelantado porque no tocan aislamiento: un schema
Pydantic no consulta la base ni decide quien ve que. Lo que falta para que esto
sea un endpoint es `rbac.py` (bloque 6 de C-02), y eso espera a `E-001`.

Cuando llegue, el trabajo es colgar `require_permission` y escribir el servicio
contra estos contratos — no rediscutirlos.
"""
