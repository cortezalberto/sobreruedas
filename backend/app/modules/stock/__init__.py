"""Modulo de stock — C-14 y C-15.

Schemas, modelo ORM, repositorio, servicio y router. Los contratos se
escribieron por adelantado —un schema Pydantic no consulta la base ni decide
quien ve que— y el resto llego cuando `rbac.py` existio.

⚠️ **El change figuraba PARCIAL en `CHANGES.md`, y C-14 cerro dos de los tres
huecos que dejo la demo** (`ESC-003`, que construyo la mitad visible y se
detuvo). Estado actual:

  - `vehicle_status_history` YA EXISTE (migracion `019`) y
    `StockService.crear`/`cambiar_estado` escriben en ella. `HistorialDeEstado`
    (el schema de salida) sigue sin consumidor: `GET /vehicles/{id}/history`
    es `T-085`, y llega con **C-15**.
  - `StockService.editar` YA EXISTE y emite `vehicle.updated`. El `PATCH`
    que lo expone por HTTP tambien es `T-079` → **C-15**.
  - El listado TODAVIA no pagina. Sigue siendo **C-15**.
"""
