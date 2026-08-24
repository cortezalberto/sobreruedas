# C-14 · Diseño

> Alcance: **solo los huecos**. Lo que `ESC-003` dejó andando —el modelo `Vehicle`, el repositorio, `crear`, `cambiar_estado`, `dar_de_baja`, la máquina de estados, el contador de cuota— no se rediseña. Cada decisión de acá es sobre algo que hoy no existe.

---

## D-1 · La tabla es append-only por `REVOKE`, no por confianza

**Decisión**: `vehicle_status_history` conserva `SELECT, INSERT` y **pierde `UPDATE` y `DELETE`** a nivel de privilegio de PostgreSQL, revocados en la migración `019` sobre los roles que el catálogo del sistema reporte.

**Por qué no alcanza con "nadie escribe eso"**: el init de la base tiene un `ALTER DEFAULT PRIVILEGES ... GRANT SELECT, INSERT, UPDATE` que alcanza a **toda tabla nueva, automáticamente**. Una tabla que nace no es append-only por defecto: nace escribible y hay que cerrarla. Es literalmente lo que la migración [`016`](../../../backend/alembic/versions/016_super_admins_se_lee_y_no_se_escribe.py) descubrió al cerrar C-05, y `009` y `010` antes.

**Por qué no un trigger `BEFORE UPDATE ... RAISE`**: un trigger lo desactiva quien tenga el privilegio, y el error que produce llega como excepción de PL/pgSQL, no como falta de permiso. El `REVOKE` lo hace cumplir el motor por la misma vía que el resto del control de acceso, y una auditoría lo ve en `information_schema.role_table_grants` sin leer código.

**Cómo se identifica el rol**: consultando `information_schema.role_table_grants`, **nunca hardcodeado** — se llama `mitutu` en desarrollo y distinto en test, y una migración que conoce el nombre del entorno donde corre está mal escrita. Es el mismo `BENEFICIARIOS` de `016`, acotado a `UPDATE`/`DELETE`.

**El `downgrade` devuelve `SELECT, INSERT, UPDATE` y no `DELETE`**: es exactamente lo que el init otorga. Devolver `DELETE` le daría a la aplicación un privilegio que nunca tuvo (regla dura 3, soft delete universal), y un downgrade que deja el sistema más abierto que antes del upgrade no es una reversión.

**Marcador del lint**: `REVOKE` está en la lista de DDL destructivo de `test_migraciones_compatibles.py` (línea 127) y **hay que marcarlo**. Va `# migracion-segura:` **por línea**, no `# migracion-contract:`: el marcador de contract silencia el **archivo entero**, y este archivo además crea una tabla — un `drop_column` agregado dentro de seis meses pasaría sin que nadie lo vea. Es la corrección que C-05 ya hizo en su tarea 1.9.

> El argumento de compatibilidad hacia atrás es trivial acá y conviene decirlo igual: la versión inmediatamente anterior de la aplicación **no conoce esta tabla**, así que no puede romperse por perder un privilegio sobre ella. Aun así se revisó `app/` entero: ninguna ruta la escribe, porque todavía no existe.

---

## D-2 · Los nombres de columna salen de N1, y el schema se corrige contra la tabla

**El conflicto** (hallazgo `H-c` del proposal): tres fuentes, tres nombres.

| Fuente | Nivel | Autor | Timestamp | Extra |
|---|---|---|---|---|
| `spec-tecnica` §3.4 | **N1** | `changed_by` | `changed_at` | — |
| `plan-implementacion` T-084 | N2 | `changed_by_user_id` | — | + `notes` |
| `schemas.py:357` | *no es fuente* | `user_id` | `occurred_at` | — |

**Decisión**: la tabla usa **`changed_by` y `changed_at`**, y **no lleva `notes`**.

**Por qué**: por [`ADR-000`](../../../docs/adr/ADR-000-precedencia-documental.md), N1 gana sobre N2 y la recencia no desempata. `notes` sale de N2 y N1 no la tiene; `reason` ya existe y ya es el campo donde el `POST /vehicles/{id}/status` deja el motivo (`RN-ST-06` lo hace obligatorio al vender). Dos columnas de texto libre en una tabla de auditoría, sin ninguna regla que las distinga, es garantía de que la mitad de los motivos queden en la equivocada.

**Y el schema Pydantic se renombra**, no se traduce: `HistorialDeEstado` pasa a declarar `changed_by` y `changed_at`.

Renombrarlo cuesta **cero hoy** y cuesta una capa de traducción para siempre si se difiere: el schema **no tiene un solo consumidor** —no hay endpoint, no hay entrada en el espejo de `frontend-web/src/lib/api.ts`, no aparece en `test_vehiculo_espejado.py`—, así que renombrarlo no rompe nada. La alternativa —mapear el atributo ORM `user_id` a la columna `changed_by`— deja para siempre dos vocabularios para la misma fila, y quien depure una consulta SQL contra la salida de la API va a tener que traducir mentalmente en cada lectura.

**El código no es fuente de verdad cuando contradice a N1.** Es la misma regla que el encabezado de `stock/router.py` aplicó al revés y dejó escrita: ahí mandaba el código porque la fuente en conflicto era un plan que nunca se implementó; acá manda la spec porque lo que hay del otro lado es un schema que nunca se usó.

---

## D-3 · El autor llega por parámetro, no por `sesion.info`

**El problema**: `StockService` se construye con `(sesion, tenant_id)` y el `tenant_id` sale de `sesion.info`, que lo dejó puesto `sesion_del_tenant_actual`. Pero `changed_by` necesita **quién**, y el servicio no tiene al sujeto.

**Opciones**:

**(a) Meter `user_id` en `sesion.info`.** Un renglón en [`db/dependencias.py`](../../../backend/app/db/dependencias.py), y todos los servicios lo tendrían gratis para siempre. **Rechazada**: ese archivo es código de **C-02**, gobernanza **CRÍTICA**. Cambiarlo por comodidad de un módulo de negocio convierte una tarea ALTA en una que necesita aprobación de dominio crítico, y el motivo por el que el `tenant_id` está ahí —que es la frontera de aislamiento y no puede haber dos fuentes— **no aplica al autor de una fila de auditoría**.

**(b) El servicio recibe el sujeto al construirse.** `StockService(sesion, tenant_id, actor_id)`. Rechazada por un motivo concreto: `contar_vehiculos` y el consumidor de eventos de C-28 van a querer construir el servicio sin sujeto, y un parámetro obligatorio que la mitad de los llamadores pasa como `None` se vuelve ruido que nadie lee.

**(c) ✅ Los métodos que escriben auditoría reciben el autor.** `cambiar_estado(vehiculo_id, cambio, *, autor)` y `editar(vehiculo_id, datos, *, autor)`. Por palabra clave, obligatorio, `uuid.UUID | None`.

**Por qué gana (c)**: el router de `cambiar_estado` **ya recibe `SujetoActual`** —lo necesita para `verificar_alcance`, `ADR-024` §4— así que el dato ya está en la mano y pasarlo no agrega ninguna dependencia nueva al endpoint. Y el parámetro obligatorio hace que el día que nazca un cuarto camino de transición, quien lo escriba **tenga que decidir** quién es el autor en vez de heredar un `None` silencioso.

`autor=None` es un valor legítimo y significa **transición automática, sin persona detrás** — es exactamente lo que el docstring de `HistorialDeEstado` ya anticipa. Lo va a usar C-28 cuando las automatizaciones cambien estados.

---

## D-4 · La fila génesis existe, y por eso hay que tocar la importación

**Decisión**: el alta escribe una fila con `from_status = NULL` y `to_status = 'in_preparation'`.

**Por qué**: `from_status NULL` está en la spec y **sin la fila génesis no tiene ningún productor** — una columna nullable que nadie puede llenar es una columna muerta que promete algo que no ocurre. Y sin ella la línea de tiempo empieza en el segundo estado: no se puede responder *"¿cuándo entró este auto al stock?"* mirando el historial, que es la primera pregunta que un historial debería contestar.

`T-084` dice *"cada transición de estado escribe una fila"* y el alta no es una transición. Es cierto y no alcanza: la ausencia de estado previo **es** la información que `from_status NULL` codifica.

**La consecuencia incómoda**: [`importacion_servicio.py:319`](../../../backend/app/modules/stock/importacion_servicio.py) construye `Vehicle(...)` **directo**, sin pasar por `StockService.crear`. Si la fila génesis viviera solo dentro de `crear`, los vehículos importados —que son la vía de alta masiva, hasta 5.000 por corrida según `RN-ST-13`— entrarían **sin historial**.

Una auditoría append-only con agujeros es peor que no tenerla, porque se consulta creyéndole. Así que este change **toca `importacion_servicio.py`**, que es código de C-17, y lo declara en el Impact del proposal en vez de deslizarlo.

`changed_by` en una importación es el usuario que lanzó la corrida si la corrida lo conoce, y `NULL` si no: importar es una acción de una persona, pero el procesamiento ocurre en una tarea Celery y el sujeto ya no está en contexto.

---

## D-5 · Un registrador compartido, no un método del servicio

**Decisión**: el modelo, el repositorio y la función que escribe la fila viven en `backend/app/modules/stock/historial.py`, con una única entrada:

```
registrar_transicion(sesion, *, tenant_id, vehiculo_id, desde, hasta, razon, autor) -> None
```

**Por qué no un método privado de `StockService`**: tiene **tres** llamadores y uno de ellos —la importación— no construye un `StockService`. Un método privado obligaría a la importación a instanciar el servicio solo para llegar al método, o a duplicar el `INSERT`. La duplicación en una tabla de auditoría es cómo se llega a dos formatos de fila para el mismo hecho.

**Por qué no un evento del outbox que un consumidor materialice**: porque el historial tiene que estar en la **misma transacción** que el cambio que registra. Un consumidor asincrónico introduce una ventana en la que el vehículo ya cambió de estado y el historial todavía no lo dice — y si el consumidor falla, la ventana no se cierra nunca. `ADR-036` resuelve la publicación de hechos hacia afuera; la auditoría es un hecho hacia adentro y no admite eventual consistency.

**No es `async`**, igual que `registrar()` del outbox: agrega la fila a la sesión que recibe y devuelve. El `flush` lo hace quien llama, cuando ya tiene el `id` del vehículo.

---

## D-6 · `vehicle.updated` lleva los nombres de los campos, no sus valores

**Decisión**: `payload = {"vehicle_id": ..., "campos": ["price_ars", "color"]}`. Ordenado, sin valores viejos ni nuevos.

**Por qué**: es la misma decisión de seguridad que el encabezado de `StockService._evento` ya argumenta para los otros tres eventos. **Un evento no tiene quien pregunta.** Si el payload llevara valores, `acquisition_cost_ars` —que `RN-ST-12` restringe a `manager` y `admin_staff` por la API— quedaría en un stream de Redis legible por cualquier consumidor presente o futuro, y la regla se evaporaría por la puerta de atrás.

**Por qué los nombres sí y no solo el `vehicle_id`**: porque las automatizaciones de C-28 y la reindexación de C-18 se disparan por **qué** cambió. Un consumidor que solo recibe "algo cambió" tiene que releer el vehículo entero en cada edición, y el índice de OpenSearch se reconstruiría por un cambio de color.

**Un `PATCH` que no cambia nada no emite evento.** Mandar el mismo precio dos veces no es un hecho: un consumidor que reindexa por cada `vehicle.updated` haría trabajo por una petición que no movió una sola columna.

---

## D-7 · Edición parcial de verdad: `exclude_unset`, y el `null` explícito se decide campo por campo

**Decisión**: `datos.model_dump(exclude_unset=True)`.

**Por qué no `exclude_none`**: `exclude_none` haría imposible **borrar** un valor. Los dos casos se ven distintos en el cuerpo JSON y tienen que seguir viéndose distintos adentro:

```
{}                            -> no toques assigned_user_id
{"assigned_user_id": null}    -> desasignalo
```

Con `exclude_none` el segundo caso se pierde, y desasignar a un vendedor de un vehículo pasaría a ser imposible por la API.

**La contracara**: `VehiculoEditar` declara **todos** sus campos como `X | None = None`, así que hoy nada impide mandar `{"color": null}` — y `color` es `NOT NULL` en la base. Sin defensa, eso es un `IntegrityError` de PostgreSQL llegándole al cliente como 500.

Va un validador en `VehiculoEditar` que rechaza el `null` explícito sobre los campos que la tabla no admite nulos: `branch_id`, `mileage_km`, `color`, `price_ars`, `features`. Los que **sí** lo admiten —`assigned_user_id`, `version_id`, `price_usd`, `acquisition_cost_ars`, `description`— siguen aceptándolo, porque para ellos borrar es una operación legítima.

Se valida en el schema y no en el servicio por el mismo criterio que el resto del módulo: formato y rangos son de Pydantic (422 legible), reglas de negocio son del servicio. "Este campo no puede quedar vacío" es forma, no negocio.

**`status` no está en `VehiculoEditar` y no se agrega.** El schema ya lo argumenta: el cambio de estado tiene su propio endpoint porque `RN-ST-05` restringe las transiciones, `RN-ST-06` exige razón para algunas y `ADR-034` suma el eje de permiso por transición. Dejarlo entrar por el `PATCH` saltearía las tres cosas de una.

---

## D-8 · El historial no pagina, y hay una salida si algún día hace falta

**Decisión**: `listar_historial(vehiculo_id)` devuelve la línea de tiempo completa, ordenada por `(changed_at DESC, id DESC)`.

**Por qué**: la cantidad de filas está acotada por la máquina de estados. Seis estados, nueve transiciones legales, y cada una es una acción humana deliberada — el peor caso realista es una decena de filas. Ponerle un cursor a eso le pide al cliente que aprenda un protocolo de recorrido para una lista que entra en una pantalla.

**Y hay un motivo técnico que conviene dejar anotado**: `core/pagination.py` fija `CAMPO_FECHA = "created_at"` como constante de módulo y su encabezado lo justifica con *"toda tabla del sistema los tiene"*. Esta tabla tiene `changed_at`, porque así lo escribe N1. **Eso no es un problema y no obliga a nada**: el día que el historial necesite paginar, la salida es una etiqueta en el `select` —`Historial.changed_at.label("created_at")`— y `paginar` funciona sin que se toque una línea de `core/`, que es código de C-02 y gobernanza CRÍTICA.

Queda escrito acá para que nadie lo descubra bajo presión y "resuelva" renombrando la columna.

---

## D-9 · `changed_by` es nullable y su FK es compuesta

**Decisión**: `FOREIGN KEY (changed_by, tenant_id) REFERENCES users (id, tenant_id) ON DELETE RESTRICT`, con `changed_by` nullable.

**Por qué compuesta**: es exactamente el razonamiento de [`018_notifications`](../../../backend/alembic/versions/018_notifications.py) y de `015_user_branches`. Con una FK sobre `changed_by` solo, una fila de historial de **esta** agencia podría apuntar a un usuario de **otra** y pasar la política RLS igual, porque su `tenant_id` sería el correcto. Comparando las dos columnas contra `uq_users_id_tenant`, la base lo vuelve imposible.

**Nullable y compuesta conviven**: con `MATCH SIMPLE`, que es el default de PostgreSQL, una FK compuesta con alguna columna en `NULL` **no se verifica**. Así que `changed_by = NULL` (transición automática) pasa sin necesitar un `tenant_id` nulo, que sería inaceptable.

**`RESTRICT` y no `SET NULL`**: el espejo local de usuarios no se borra —`D-6` de C-05 da de baja sin borrar—, y si alguna vez alguien intenta el `DELETE` físico, que falle acá. Un historial que pierde a su autor cuando la persona deja la agencia deja de ser una auditoría.

---

## D-10 · Los índices

```
ix_vehicle_status_history_linea_de_tiempo  (tenant_id, vehicle_id, changed_at DESC)
```

`T-084` pide `(vehicle_id, changed_at desc)`. Se antepone `tenant_id` por la convención del proyecto en listados multi-columna, y porque es la columna del `WHERE` que **toda** consulta lleva por la capa 3 de `ADR-006`.

Un segundo índice sobre `changed_by` **no va**: nadie consulta "todo lo que hizo esta persona" en este change, y un índice que ninguna consulta usa es escritura más lenta en la vía caliente a cambio de nada. Cuando C-11 (audit log) o un reporte de productividad lo necesiten, se agrega ahí con la consulta que lo justifica delante.

---

## Riesgos

| Riesgo | Mitigación |
|---|---|
| El `REVOKE` se aplica sobre un rol que el catálogo no reporta (entorno nuevo, rol distinto) y la tabla queda escribible sin que nadie lo note | Test de integración que **verifica el privilegio en `information_schema`**, no que el `REVOKE` corrió. Es la diferencia entre probar la migración y probar el resultado |
| Tocar `importacion_servicio.py` (C-17) rompe la importación | La suite de C-17 (`test_importacion_ejecucion.py`, `test_importacion_router.py`) corre como red de seguridad **antes** de tocar el archivo, y el baseline se registra en la tarea |
| El renombre de `HistorialDeEstado` rompe algo que el `grep` no vio | `test_stock_schemas.py` y `mypy --strict` sobre todo el backend. Si algo lo importaba, no compila |
| La fila génesis duplica volumen de escritura en la importación de 5.000 filas | Se escribe en el mismo batch de 100 que ya usa `RN-ST-13`, dentro de la misma transacción. No agrega viajes a la base |
