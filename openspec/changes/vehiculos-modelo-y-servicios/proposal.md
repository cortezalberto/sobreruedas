# C-14 · `vehiculos-modelo-y-servicios`

> **Este change NO construye el módulo de stock. Lo cierra.**
>
> La mitad de C-14 ya está en `main`: la escribió la rebanada vertical de la demo (`ESC-003`), que salteó el ciclo de OpenSpec para tener pantalla antes que contrato. Lo que quedó afuera no es "lo que falta hacer al final" — es **lo que la demo no necesitaba ver**: la auditoría de estados y la edición.
>
> Este proposal especifica **exclusivamente los huecos**. Lo que ya funciona no se re-especifica ni se toca.

## Why

`backend/app/modules/stock/__init__.py` lo dice sin rodeos en su propio encabezado: *"`VehiculoEditar` espera su `PATCH`, `HistorialDeEstado` espera su tabla, y el listado no pagina"*. Los tres son contratos escritos sin implementación detrás, y llevan así desde que la demo cerró.

De esos tres, **dos son de este change** (el tercero es C-15):

**1. Hay un schema Pydantic para una tabla que no existe.** `HistorialDeEstado` está declarado en [`schemas.py:357`](../../../backend/app/modules/stock/schemas.py) y ninguna migración crea `vehicle_status_history`. `StockService.cambiar_estado` muta `vehiculo.status`, emite `vehicle.status_changed` al outbox y **no deja rastro en la base**.

El outbox no es la auditoría: `ADR-036` lo describe como el mecanismo de publicación de eventos, y `core/outbox.py` marca las filas como publicadas — no es un registro histórico consultable ni append-only, y su payload es deliberadamente mínimo por razones de seguridad (el encabezado de `_evento` lo argumenta). Hoy, si alguien pregunta *"¿quién reservó este auto y cuándo?"*, **el sistema no tiene la respuesta**. Los seis estados de `ADR-031` cambian sin dejar huella.

**2. `vehicle.updated` no se emite porque no hay quién lo emita.** `StockService` tiene `crear`, `cambiar_estado` y `dar_de_baja`. **No tiene `editar`.** El plan lo pide como `T-075` (*"VehicleService.update + evento vehicle.updated"*), y sin ese método el `PATCH` de C-15 no tiene a qué llamar y los consumidores de eventos no se enteran de que un precio cambió.

**Y hay una tercera razón, de proceso**: la máquina de estados de `RN-ST-05` está escrita sin que nadie la ratificara. [`ADR-037`](../../../docs/adr/ADR-037-la-reserva-no-vence-sola.md) la cerró el 23-ago-2026 — la regla de los 7 días no existe, `reserved → available` es manual y `TRANSICIONES_PERMITIDAS` queda ratificada **tal cual está**. Este change es donde ese cierre se registra: hasta ahora era código que nadie había aprobado.

## What Changes

### 1 · La tabla que falta — `vehicle_status_history`

Migración `019`, **append-only**, siguiendo exactamente el patrón de [`016`](../../../backend/alembic/versions/016_super_admins_se_lee_y_no_se_escribe.py): el init de la base otorga `SELECT, INSERT, UPDATE` a toda tabla nueva por `ALTER DEFAULT PRIVILEGES`, así que el append-only **se consigue revocando después**, no declarándolo.

Columnas según [`spec-tecnica`](../../../docs/sdd/deRuedas-spec-tecnica.md) §3.4 (N1), que gana sobre el plan de implementación (N2):

```
id · tenant_id · vehicle_id · from_status NULL · to_status NOT NULL
   · changed_by NULL (FK users) · reason TEXT NULL · changed_at NOT NULL
```

Las tres capas de aislamiento (`tenant_id` + RLS + `FORCE`), FK **compuesta** a `users` como en [`018`](../../../backend/alembic/versions/018_notifications.py), y `REVOKE UPDATE, DELETE` conservando `SELECT, INSERT`.

### 2 · Cada transición escribe su fila

`StockService.cambiar_estado` deja de ser una mutación silenciosa. Y el alta escribe la **fila génesis** (`from_status = NULL`), que es el único productor posible de esa columna nullable que la spec declara: sin ella, la línea de tiempo de un vehículo empieza en su segundo estado.

### 3 · `StockService.editar` y el evento `vehicle.updated`

El método de dominio que `T-075` pide. Con la edición **parcial de verdad** (`model_dump(exclude_unset=True)`: un campo ausente no es un campo puesto en `NULL`), `updated_at` refrescado, y el evento anotado en el outbox con el **conjunto de campos que cambiaron** — no sus valores, por la misma razón que el resto de los payloads son mínimos.

### 4 · `ADR-037` queda registrado

`TRANSICIONES_PERMITIDAS` pasa de *"escrito sin decidir"* a **ratificado**, con un test que ancla las nueve transiciones de `RN-ST-05` contra el ADR.

### Lo que este change NO hace

| No entra | Por qué |
|---|---|
| `PATCH /vehicles/{id}` | Es `T-079` → **C-15** |
| `GET /vehicles/{id}/history` | Es `T-085` → **C-15** |
| Paginación del listado | Es **C-15** |
| `Idempotency-Key` en el `POST` | Es **C-15** |
| Columna `reserved_at`, tarea de vencimiento de reservas | `ADR-037`: **la regla no existe**. Cero código |
| Columna `internal_notes` | Ver *Hallazgos*, abajo — no bloquea y no se decide acá |
| `RN-ST-07` / `RN-ST-08` (archivar con leads / operación cerrada) | `leads` es C-16 y `operations` es C-19. Ya está declarado en el docstring de `dar_de_baja` |

## Capabilities

### New Capabilities

- **`stock/vehicle-lifecycle`** — qué le pasa a un vehículo a lo largo de su vida en la agencia: qué transiciones son legales, qué queda registrado de cada una, y qué se entera el resto del sistema cuando algo cambia. **Nace con esta capacidad ya a medias construida**: lo que la demo dejó funcionando entra como contexto, y los requisitos que se agregan son los huecos.

### Modified Capabilities

Ninguna. `platform/domain-events` ya fija cómo se publica un evento; este change agrega un tipo de evento, no una regla nueva de publicación.

## Impact

**Código nuevo**
- `backend/alembic/versions/019_vehicle_status_history.py`
- `backend/app/modules/stock/historial.py` — modelo ORM, repositorio y el registrador compartido
- `backend/tests/integration/test_status_history.py` (`T-084`), `test_stock_edicion.py`

**Código tocado**
- `backend/app/modules/stock/service.py` — `crear` y `cambiar_estado` escriben historial; nace `editar`
- `backend/app/modules/stock/schemas.py` — `HistorialDeEstado` se renombra a los nombres de la tabla (ver `D-2`)
- ⚠️ `backend/app/modules/stock/importacion_servicio.py` — **es código de C-17**. Construye `Vehicle(...)` directo en la línea 319, sin pasar por `StockService.crear`, así que sin tocarlo **los 5.000 vehículos de una importación entrarían sin fila génesis** y la auditoría tendría un agujero del tamaño de la vía de alta más usada. Una auditoría append-only incompleta es peor que no tenerla: se consulta creyéndole.

**Nivel de gobernanza: ALTA.** Se propone y se espera revisión humana antes de escribir código. Los dos motivos concretos: la migración revoca privilegios sobre una tabla nueva (`REVOKE` rompe hacia atrás por definición, regla dura 13) y el change toca un archivo de otro change (`importacion_servicio.py`).

### Bloqueantes

| Bloqueante | Estado |
|---|---|
| `IN-07` · `domain_plate` `NOT NULL` vs nullable | ✅ **Resuelto** por [`ADR-031`](../../../docs/adr/ADR-031-dominio-opcional-y-los-seis-estados-del-vehiculo.md) — nullable, con `UNIQUE` parcial y `CHECK`. **Ya implementado** en `011` |
| `IN-11` · cuántos estados | ✅ **Resuelto** por `ADR-031` — seis. **Ya implementado** |
| `IN-11` · la regla de los 7 días | ✅ **Resuelto** por [`ADR-037`](../../../docs/adr/ADR-037-la-reserva-no-vence-sola.md) el 23-ago-2026. **Cero código nuevo** |

**No hay bloqueantes abiertos.** Por regla dura 12, este change puede implementarse apenas se apruebe.

## Hallazgos de la auditoría

Cuatro cosas que aparecieron al leer el código y que **no estaban en el encargo**. Ninguna entra al scope sin decirlo primero.

### H-a · `internal_notes` es una celda de la matriz que apunta a una columna inexistente

[`rbac.py:427`](../../../backend/app/core/rbac.py) declara `CAMPOS_DE_VEHICULO_PARA_VENDEDOR = {"internal_notes", "assigned_user_id"}`, con `ADR-024` §6 detrás, y su propio docstring avisa: *"⚠️ `internal_notes` todavía no es una columna del modelo (llega con `C-14`)"*. **No llegó.** No está en `models.py`, ni en `VehiculoEditar`, ni en ninguna migración.

**No bloquea a C-15** y por eso no se agrega acá: `recortar()` sobre un cuerpo de `VehiculoEditar` —que no declara el campo— deja al `salesperson` con `assigned_user_id` y nada más, que es un comportamiento correcto y seguro. Lo que falta es una funcionalidad que nadie pidió todavía.

**Lo que sí hace falta decidir antes de agregarla**, y por eso no se resuelve de paso: `ADR-024` le da al `salesperson` permiso de **escritura** sobre `internal_notes`, pero el conjunto de **lectura** (`CAMPOS_DE_VEHICULO_SIN_COSTO`) **no lo incluye**. Tal como están escritas las dos celdas, el vendedor podría escribir un campo que no puede leer. Eso es una inconsistencia de `ADR-024`, no un detalle de implementación, y se cierra con una enmienda a ese ADR — no con una columna.

→ Queda registrado. C-15 agrega un test que **fija el comportamiento de hoy** para que el hueco sea visible en vez de silencioso.

### H-b · El test que `rbac.py` dice tener no existe

`CAMPOS_DE_VEHICULO_SIN_COSTO` afirma en su docstring: *"un test lo compara contra el esquema para que la copia no se despegue"*. Un `grep` sobre `backend/tests/` no encuentra **ninguna** referencia a esa constante. El test no existe, y la lista de 23 campos puede despegarse de `VehiculoSalida` sin que nada se ponga rojo.

→ Es el patrón *"un documento afirma un control que no ocurre"* que `ADR-030` ya nombró. **Sí entra**, como tarea 5.3: el guardián cuesta diez líneas y el riesgo que cubre es `RN-ST-12`.

### H-c · Tres nombres distintos para las mismas dos columnas

| Fuente | Autor | Timestamp |
|---|---|---|
| `spec-tecnica` §3.4 (**N1**) | `changed_by` | `changed_at` |
| `plan-implementacion` T-084 (N2) | `changed_by_user_id` | — (+ una columna `notes` que N1 no tiene) |
| `schemas.py:357` (código) | `user_id` | `occurred_at` |

Por `ADR-000`, **N1 gana sobre N2**, y el código no es fuente. Se resuelve en `D-2`.

### H-d · `dar_de_baja` no escribe historial, y está bien

La baja lógica escribe `deleted_at` y **no toca `status`** — el propio docstring del servicio advierte que `vehicle.archived` (el evento) y el estado `archived` son cosas distintas. Como no hay transición, no hay fila. Se deja escrito para que nadie lo lea como un olvido.

## Orden de implementación

**C-14 entero antes que C-15.** No es preferencia: `GET /vehicles/{id}/history` (C-15) no tiene tabla que consultar hasta que `019` exista, y el `PATCH` (C-15) no tiene método al que llamar hasta que `StockService.editar` exista.

La dependencia inversa —*"`vehicle.updated` necesita el `PATCH`"*— **es aparente**. `editar` es la capa de servicio (`T-075`, rango de C-14) y el `PATCH` es la capa HTTP (`T-079`, rango de C-15). C-14 prueba el evento **a nivel de servicio**, contra la fila del outbox en PostgreSQL real; C-15 lo prueba de punta a punta por HTTP. Lo único que no se puede verificar hasta C-15 es que el camino completo esté enchufado, y eso es exactamente lo que C-15 tiene que demostrar.
