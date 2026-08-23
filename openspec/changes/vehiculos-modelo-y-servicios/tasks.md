# C-14 · Tareas

> **Gobernanza ALTA.** Se propone y se espera revisión humana. No se escribe código hasta que la propuesta esté aprobada: la migración revoca privilegios (`REVOKE` rompe hacia atrás por definición, regla dura 13) y el change toca un archivo que pertenece a C-17.

> **TDD estricto.** Cada tarea de implementación va precedida de su test, y el test tiene que **fallar por la razón correcta** antes de escribir el código. Donde se modifica un archivo existente, la tarea arranca por la **red de seguridad**: correr la suite que ya cubre ese archivo y anotar el baseline.

> **Alcance: solo los huecos.** Nada de lo que `ESC-003` dejó funcionando se reescribe. Si al implementar aparece la tentación de "arreglar de paso", va al reporte, no al diff.

## 0. La puerta

- [x] 0.1 Confirmar que [`ADR-037`](../../../docs/adr/ADR-037-la-reserva-no-vence-sola.md) está **Aceptado** (23-ago-2026 ✅) y que `IN-11` queda cerrado por completo entre él y `ADR-031`. Si no, **detenerse acá** (regla dura 12)
- [x] 0.2 Confirmar que `IN-07` está resuelto por `ADR-031` y **ya implementado** en la migración `011` — `domain_plate` nullable, `UNIQUE` parcial y `CHECK` de identificabilidad. Es verificación, no trabajo: si el código no coincide con el ADR, eso es un hallazgo antes que una tarea
- [x] 0.3 Verificar que la cabeza de Alembic sigue siendo `018` (`018_notifications`). Si otro change encadenó primero, la nueva migración toma el número siguiente y `down_revision` apunta a la cabeza real, no a `"018"` a ciegas
- [x] 0.4 **Red de seguridad global.** Correr la suite completa del backend y anotar el baseline (`N pasan / M fallan`). Cualquier fallo previo se reporta como **fallo preexistente** y **no se arregla acá**

## 1. Migración `019_vehicle_status_history`

- [x] 1.1 **RED** — `tests/integration/test_status_history.py`: la tabla existe con las ocho columnas de `spec-tecnica` §3.4 (`D-2`), `changed_at` es `TIMESTAMPTZ` (nunca `TIMESTAMP` pelado) y `from_status`/`to_status` usan el enum `vehicle_status_enum` que ya creó `011`
- [x] 1.2 **RED** — test de las tres capas: `tenant_id NOT NULL`, política `vehicle_status_history_aislamiento_por_tenant` presente en `pg_policies`, **y `FORCE`**. `FORCE` y no solo `ENABLE`: sin él las políticas no se aplican al dueño de la tabla, `pg_policies` la lista igual y una auditoría la da por buena
- [x] 1.3 **RED** — test del append-only **sobre el privilegio, no sobre el `REVOKE`**: consultar `information_schema.role_table_grants` y verificar que el rol de aplicación tiene `SELECT` e `INSERT` y **no** tiene `UPDATE` ni `DELETE`. Probar que la migración ejecutó el `REVOKE` no prueba que la tabla haya quedado cerrada
- [x] 1.4 **RED** — contrapeso del anterior: un `UPDATE` real contra la tabla desde `DSN_APLICACION` falla por permiso, y un `INSERT` funciona. Sin el contrapeso, el test 1.3 pasaría igual con una tabla que nadie puede ni leer
- [x] 1.5 **RED** — test de la FK compuesta (`D-9`): una fila que apunta a un usuario de **otra** agencia es rechazada por la base, y una fila con `changed_by = NULL` se acepta
- [x] 1.6 **GREEN** — escribir `backend/alembic/versions/019_vehicle_status_history.py` con `down_revision = "018"` (o la cabeza real de 0.3). Docstring largo en español explicando **por qué** existe la tabla y por qué es append-only, no solo qué crea. Copiar el contrato de RLS de `011`/`018` literal, sin factorizar: una migración es una foto congelada
- [x] 1.7 **GREEN** — el `REVOKE` identifica los roles por `information_schema.role_table_grants` (`BENEFICIARIOS` de `016`), **nunca hardcodeados**, y va con `# noqa: S608` porque los identificadores no se pueden bindear
- [x] 1.8 **GREEN** — el `downgrade()` restituye exactamente `SELECT, INSERT, UPDATE` y **no `DELETE`** (`D-1`), y borra política y tabla. Test que lo verifique: un downgrade que deja el sistema más abierto que el upgrade no es una reversión
- [x] 1.9 **GREEN** — índice `ix_vehicle_status_history_linea_de_tiempo (tenant_id, vehicle_id, changed_at DESC)` (`D-10`)
- [x] 1.10 **Gate de migraciones compatibles.** El `REVOKE` está en la lista de DDL destructivo de `test_migraciones_compatibles.py`. Marcarlo con **`# migracion-segura:` por línea**, no con `# migracion-contract:` — el de contract silencia el archivo entero y este archivo además crea una tabla (`D-1`, y es la corrección que C-05 ya hizo en su tarea 1.9). Correr el gate y verificar que pasa
- [x] 1.11 **REFACTOR** — releer la migración contra `016` y `018` lado a lado: los nombres de política, la condición literal de RLS y la forma del `downgrade` tienen que ser reconocibles como el mismo patrón

## 2. `historial.py` — modelo, repositorio y registrador

- [x] 2.1 **RED** — `tests/unit/test_historial_modelo.py`: el modelo declara exactamente las columnas de la tabla, con los nombres de `D-2` (`changed_by`, `changed_at`), y el enum usa `ENUM(..., create_type=False)` con los valores tomados de `EstadoDeVehiculo`. Los valores hay que listarlos aunque el tipo exista: sin ellos SQLAlchemy escribe bien y **falla al leer**, como documenta `models.py`
- [x] 2.2 **GREEN** — `backend/app/modules/stock/historial.py`: modelo ORM `VehicleStatusHistory` heredando de `Base`
- [x] 2.3 **RED** — `test_status_history.py`: `registrar_transicion(...)` agrega la fila a la sesión que recibe, **no es `async`** y no hace `flush` por su cuenta (`D-5`)
- [x] 2.4 **RED** — test del aislamiento: `listar_historial` de un vehículo ajeno devuelve vacío, y el filtro explícito de `tenant_id` está en la consulta además de la política RLS (capa 3, regla dura 1)
- [x] 2.5 **GREEN** — `registrar_transicion` y el repositorio de lectura, con el orden `(changed_at DESC, id DESC)` de `D-8` y **sin paginación** (dejar el motivo en el docstring, incluido el escape hatch del `label("created_at")`)
- [x] 2.6 **TRIANGULAR** — segundo caso con `autor=None` y tercero con `razon=None`: ninguno de los dos puede caer en el mismo camino de código que el caso completo

## 3. El servicio escribe historial

- [x] 3.1 **Red de seguridad** — correr `tests/integration/test_stock_service.py` y `test_stock_router.py` antes de tocar `service.py`. Anotar el baseline
- [x] 3.2 **RED** — test: `cambiar_estado` deja una fila con `from_status` = el estado del que venía, `to_status` = el nuevo, `reason` = el motivo recibido, `changed_by` = el autor
- [x] 3.3 **RED** — test: una transición **rechazada** por `es_transicion_valida` no deja fila. Es el contrapeso de 3.2 — sin él, un registrador que escribe siempre pasaría los dos
- [x] 3.4 **GREEN** — `cambiar_estado(vehiculo_id, cambio, *, autor)` con el autor por palabra clave y obligatorio (`D-3`), llamando a `registrar_transicion` **antes** del `flush` final
- [x] 3.5 **RED** — test: `crear` deja la fila génesis con `from_status = NULL` y `to_status = 'in_preparation'` (`D-4`)
- [x] 3.6 **GREEN** — `crear` registra la génesis, después del `flush` que asigna el `id` (misma razón por la que el evento va después: registrar antes anotaría un `None`)
- [x] 3.7 **RED** — test: un vehículo creado por **importación masiva** también tiene su fila génesis. Es el hueco de `D-4`: `importacion_servicio.py:319` construye `Vehicle(...)` directo
- [x] 3.8 **GREEN** — ⚠️ **tocar `importacion_servicio.py`, que es código de C-17.** Registrar la génesis en el mismo batch, con `changed_by` = el usuario de la corrida si la corrida lo conoce y `NULL` si no. Correr la suite completa de C-17 después (`test_importacion_ejecucion.py`, `test_importacion_router.py`) y comparar contra el baseline de 3.1
- [x] 3.9 **RED** — test: `dar_de_baja` **no** deja fila de historial (`H-d` del proposal). No es un olvido, es la ausencia de transición: la baja lógica escribe `deleted_at` y no toca `status`
- [x] 3.10 **RED** — test transaccional: si la transacción se revierte después de `cambiar_estado`, **ni el cambio ni la fila de historial** sobreviven. Es el requisito de atomicidad de la spec y lo único que distingue la auditoría de un evento

## 4. `StockService.editar` y `vehicle.updated`

- [x] 4.1 **RED** — `tests/unit/test_stock_schemas.py`: `VehiculoEditar` rechaza el `null` explícito sobre `branch_id`, `mileage_km`, `color`, `price_ars` y `features`, con un 422 que nombra el campo (`D-7`)
- [x] 4.2 **RED** — el contrapeso: `VehiculoEditar` **acepta** el `null` explícito sobre `assigned_user_id`, `version_id`, `price_usd`, `acquisition_cost_ars` y `description`. Sin este test, un validador que rechace todo `null` pasaría el 4.1
- [x] 4.3 **GREEN** — el validador en `VehiculoEditar`
- [x] 4.4 **RED** — test: `editar` con un solo campo cambia ese campo y **ningún otro** (`exclude_unset`, `D-7`)
- [x] 4.5 **RED** — test: `editar` con `{"assigned_user_id": null}` desasigna. Es lo que distingue `exclude_unset` de `exclude_none`, y sin este test las dos implementaciones pasan igual
- [x] 4.6 **RED** — test: `editar` sobre un vehículo de otra agencia levanta `VehiculoNoEncontrado` (404, no 403 — distinguirlos confirmaría que el id existe en otra agencia)
- [x] 4.7 **GREEN** — `editar(vehiculo_id, datos, *, autor)` en `StockService`, con `updated_at` refrescado
- [x] 4.8 **RED** — test: `editar` anota en el outbox un `vehicle.updated` cuyo payload trae `vehicle_id` y la lista **ordenada de nombres** de campos cambiados
- [x] 4.9 **RED** — test de seguridad: editar `acquisition_cost_ars` produce un payload que **nombra el campo y no lleva su valor** (`D-6`, `RN-ST-12`). Verificar sobre la fila real del outbox, no sobre un mock
- [x] 4.10 **RED** — test: `editar` con los mismos valores que el vehículo ya tenía **no** anota ningún evento (`D-6`)
- [x] 4.11 **GREEN** — la emisión del evento vía `self._evento("vehicle.updated", ...)`
- [x] 4.12 **REFACTOR** — releer `service.py` entero: `crear`, `editar`, `cambiar_estado` y `dar_de_baja` tienen que quedar con la misma forma (traer, validar, mutar, `flush`, registrar historial si corresponde, anotar evento)

## 5. Guardianes y cierre

- [x] 5.1 **`ADR-037` queda anclado en un test.** `tests/unit/test_transiciones_espejadas.py` (o un test nuevo si ese archivo tiene otro propósito): `TRANSICIONES_PERMITIDAS` contiene exactamente las nueve transiciones de `RN-ST-05`, ni una más. El test cita el ADR en su docstring: lo que fija el conjunto es la decisión, no la costumbre
- [x] 5.2 **`ADR-037` queda anclado en una ausencia.** Test de que **no existe** ninguna columna `reserved_at` en `vehicles` ni tarea periódica de liberación de reservas. Un test sobre una ausencia parece raro y es lo único que impide que la regla de los 7 días vuelva por la puerta de atrás, como advierte el ADR
- [x] 5.3 **Hallazgo `H-b`: escribir el guardián que `rbac.py` dice tener.** `CAMPOS_DE_VEHICULO_SIN_COSTO` afirma en su docstring que un test lo compara contra `VehiculoSalida`, y ese test no existe en ningún lado. Escribirlo: el conjunto tiene que ser exactamente el de los campos de `VehiculoSalida`. Diez líneas, y cubre `RN-ST-12`
- [x] 5.4 Renombrar `HistorialDeEstado` a los nombres de la tabla — `changed_by`, `changed_at` (`D-2`) — y correr `mypy --strict` sobre todo el backend: si algo lo importaba, no compila
- [x] 5.5 Verificar que el **espejo del frontend** no se rompió: `test_vehiculo_espejado.py` y `test_alta_espejada.py` siguen verdes. Ninguno de los cambios de este change toca `VehiculoSalida`, así que si alguno se pone rojo es un efecto que nadie previó
- [x] 5.6 `ruff` y `mypy --strict` limpios sobre todo lo tocado
- [x] 5.7 **Cobertura**: verificar que el global del backend sigue en ≥ 80 % **y que no bajó** respecto del baseline de 0.4 (regla dura 5)
- [x] 5.8 Suite completa contra el baseline de 0.4. Cero regresiones, incluidas las de C-17
- [x] 5.9 **Escribir el reporte de hallazgos**: `H-a` (`internal_notes`), `H-b` (guardián ausente, ya resuelto en 5.3), `H-c` (los tres nombres) y `H-d` (la baja no registra). Lo que corresponda se propone como ADR o como línea nueva de `CHANGES.md`; nada se aplica de paso
