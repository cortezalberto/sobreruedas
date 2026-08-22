"""Modulo de stock — C-14 y C-15.

Schemas, modelo ORM, repositorio, servicio y router. Los contratos se
escribieron por adelantado —un schema Pydantic no consulta la base ni decide
quien ve que— y el resto llego cuando `rbac.py` existio.

⚠️ **El change figura PARCIAL en `CHANGES.md`, y lo que falta esta ahi.** Tres
schemas de este modulo no tienen consumidor y no es olvido de nadie: la rebanada
de la demo (`ESC-003`) construyo la mitad visible y se detuvo. `VehiculoEditar`
espera su `PATCH`, `HistorialDeEstado` espera su tabla, y el listado no pagina.
"""
