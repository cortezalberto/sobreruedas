# C-15 · `vehiculos-api`

> **Change de cierre, no de construcción.** Cinco de los nueve endpoints de stock ya están en `main` desde la rebanada vertical `ESC-003`: listar, obtener, crear, cambiar estado, dar de baja, y la plantilla de importación. Este proposal especifica **los cuatro huecos** y nada más.

## Why

Este change tiene un problema distinto al de C-14. Allá faltaba una tabla; acá **la infraestructura está construida y ningún endpoint la usa**.

**`app/core/pagination.py` existe desde C-02 y no lo llama nadie.** El único caller en todo el repositorio son sus propios tests (`tests/integration/test_paginacion.py`). `GET /vehicles` ([`router.py:112`](../../../backend/app/modules/stock/router.py)) no toma `cursor` ni `limit`: devuelve la lista entera. Una agencia con 800 autos recibe 800 objetos en una respuesta, y el objetivo de ingeniería del listado es **p95 < 200 ms** por [`ADR-030`](../../../docs/adr/ADR-030-objetivo-de-ingenieria-y-slo-de-latencia.md) — un número que N0 fija y que nada mide hoy.

**`app/core/idempotency.py` existe desde C-02 y ningún endpoint HTTP lo usa.** Su único caller en `app/` es [`core/events.py:282`](../../../backend/app/core/events.py), que deduplica por `event_id` al consumir Redis Streams. El `POST /vehicles` no declara el header `Idempotency-Key`. Y la spec de `platform/api-conventions` ya dice —requisito *"Idempotencia de las creaciones"*— que *"los endpoints de creación SHALL aceptar una clave de idempotencia"*. **Hoy ninguno lo hace.**

Es el patrón que este proyecto viene encontrando y que [`ADR-030`](../../../docs/adr/ADR-030-objetivo-de-ingenieria-y-slo-de-latencia.md) nombró: *"un documento afirma un control que no ocurre"*. Acá no es un documento: es una **spec activa** en `openspec/specs/platform/api-conventions/spec.md` que describe un comportamiento que ninguna ruta tiene. La convención está escrita, probada en aislamiento y desconectada.

Y los otros dos huecos son contratos sin ruta: `VehiculoEditar` ([`schemas.py:222`](../../../backend/app/modules/stock/schemas.py)) espera un `PATCH` que no existe, y `HistorialDeEstado` espera el `GET /vehicles/{id}/history` que C-14 recién ahora hace posible.

## What Changes

### 1 · `PATCH /vehicles/{id}` — `T-079`

El endpoint que llama a `StockService.editar` (que **entrega C-14**). Permiso `vehicles:update`, ya declarado en las tres celdas de `rbac.py`. Con **recorte de campos**: el `salesperson` tiene la celda `Concesion(Alcance.ALL, CAMPOS_DE_VEHICULO_PARA_VENDEDOR)` y `recortar()` es el helper que ya existe para aplicarla.

### 2 · `GET /vehicles/{id}/history` — `T-085`

La línea de tiempo completa de un vehículo, del cambio más nuevo al más viejo. Permiso `vehicles:read`, `all` para los tres roles según [`ADR-024`](../../../docs/adr/ADR-024-matriz-rbac-canonica.md) §3 (misma fila que `GET /vehicles` y `/{id}`).

⚠️ **Con una salvedad que hay que decidir y no heredar**: la concesión de `vehicles:read` para el `salesperson` trae `campos = CAMPOS_DE_VEHICULO_SIN_COSTO`, que es la lista blanca de columnas **de un vehículo**. Aplicarla a una fila de historial la vaciaría —`from_status` y `to_status` no están en esa lista— y el vendedor recibiría registros en blanco. Ver `D-4`.

### 3 · `GET /vehicles` pagina — `T-080`

Gana `?cursor=` y `?limit=`, usando `app/core/pagination.py` **sin tocarlo**.

**El cuerpo de la respuesta no cambia de forma**: sigue siendo un array de vehículos, y el cursor de la página siguiente viaja en un **header** (`X-Next-Cursor`). Es la convención que el propio corpus escribe —`knowledge-base/02` §148 pone la metadata de paginación en headers `X-…`, no en un sobre— y además es lo único que no rompe a [`frontend-web/src/lib/api.ts:312`](../../../frontend-web/src/lib/api.ts), que hoy valida que la respuesta sea un array.

### 4 · `POST /vehicles` acepta `Idempotency-Key` — `T-078`

**Este es el punto delicado del change y el que más lejos llega.** No hay un solo precedente HTTP: C-15 **sienta el patrón para todos los `POST` de creación que vengan después** — leads, contactos, operaciones, pagos. Los pagos son la razón por la que la idempotencia existe.

Y hay una fricción real en el código: `ejecutar_idempotente` **abre su propia sesión de tenant** (`idempotency.py:159, 199, 203`), mientras que el router de stock ya recibe una `SesionDeTenant` abierta por inyección. Las dos transacciones **no componen** tal como está el código hoy.

### ⛔ La decisión de diseño cambia el nivel de aprobación de este change

La opción elegida (`D-1`) **modifica `app/core/idempotency.py`**, que es código de **C-02**, gobernanza **CRÍTICA**.

C-15 está declarado como gobernanza **MEDIO** en `CHANGES.md`. **Eso deja de ser exacto en cuanto se acepta `D-1`.** El bloque 4 de las tareas —y solo ese bloque— pasa a exigir aprobación humana explícita antes de escribir código, igual que cualquier cambio en el dominio de plataforma. El resto del change sigue siendo MEDIO.

Se dice acá, en el proposal, y no enterrado en el diseño, porque es información que cambia **quién** tiene que aprobar, no **cómo** se implementa.

> El cambio propuesto es **estrictamente aditivo**: un parámetro opcional. Con el parámetro ausente, `ejecutar_idempotente` se comporta exactamente como hoy, y el único caller existente (`core/events.py`) no se toca ni cambia de comportamiento. Eso no lo saca del dominio crítico — lo hace revisable en una lectura.

### Lo que este change NO hace

| No entra | Por qué |
|---|---|
| `GET /vehicles/search`, `/suggest` | Es **C-18** (OpenSearch) |
| `GET /vehicles/{id}/price-suggestion` | Es **C-21**, y su celda para `salesperson` está marcada ⚠ en `ADR-024` |
| Fotos, publicación, permutas | C-16, C-22, C-23 |
| Paginación de la UI de stock | Es **C-19**. Acá se ajusta el cliente HTTP para que no trunque en silencio, nada más |
| La columna `internal_notes` | Hallazgo `H-a` de C-14. **No bloquea**: `recortar()` sobre un cuerpo que no declara el campo deja al vendedor con `assigned_user_id`, que es correcto y seguro. Se agrega un test que fija ese comportamiento para que el hueco sea visible |
| Paginación del historial | `D-5` — la línea de tiempo de un vehículo está acotada por la máquina de estados |

## Capabilities

### New Capabilities

- **`stock/vehicle-api`** — cómo se opera el stock por HTTP: qué operaciones existen, quién puede cada una, sobre qué campos, y cómo se recorre un listado que crece. Nace con la mitad ya construida por `ESC-003`; los requisitos que se agregan son los huecos.

### Modified Capabilities

- **`platform/api-conventions`** — la spec ya describe la paginación por cursor y la idempotencia de las creaciones, y las describe **como si los endpoints las cumplieran**. Nada las obliga: los dos módulos existen, están probados en aislamiento y no los llama nadie. Este change agrega el requisito que faltaba —que la convención sea **exigible sobre las rutas realmente expuestas**, verificada por un gate automático como el que `test_auth_rutas.py` ya hace con los permisos— y con eso convierte la spec en algo que puede fallar.

## Impact

**Código nuevo**
- `backend/tests/integration/test_vehicles_patch.py`, `test_vehicles_history.py`, `test_vehicles_listado_paginado.py`, `test_vehicles_idempotencia.py`
- `backend/tests/unit/test_convenciones_de_ruta.py` — el gate nuevo

**Código tocado**
- `backend/app/modules/stock/router.py` — dos endpoints nuevos, dos modificados
- `backend/app/modules/stock/repository.py` — `listar` gana su variante paginada
- ⛔ `backend/app/core/idempotency.py` — **código de C-02, gobernanza CRÍTICA**. Un parámetro opcional, aditivo (`D-1`)
- `frontend-web/src/lib/api.ts` — para que el listado no se trunque en silencio al pasar de "todo" a "una página"

**Deuda que este change paga sin que se la haya pedido**: el diseño actual de `ejecutar_idempotente` tiene una **ventana de caída** que la opción elegida cierra de rebote. Ver `D-1`, *"El bug que aparece al mirar de cerca"*.

### Bloqueantes

| Bloqueante | Estado |
|---|---|
| `IN-23` · latencias p95 contradictorias | ✅ **Resuelto** por [`ADR-030`](../../../docs/adr/ADR-030-objetivo-de-ingenieria-y-slo-de-latencia.md) en C-03. C-15 lo **aplica**: el listado va contra el **objetivo de ingeniería, 200 ms**, no contra el SLO de 300 ms ni contra el umbral de página |

**No hay bloqueantes abiertos.**

### Dependencia dura: C-14 primero, entero

- `GET /vehicles/{id}/history` **no tiene tabla que consultar** hasta que exista `019_vehicle_status_history`.
- `PATCH /vehicles/{id}` **no tiene método al que llamar** hasta que exista `StockService.editar`.

La dependencia inversa que el roadmap sugiere —*"`vehicle.updated` necesita el `PATCH`"*— es aparente y se resuelve por capas: `editar` y su evento son `T-075`, rango de C-14; el `PATCH` es `T-079`, rango de C-15. C-14 prueba el evento contra la fila del outbox a nivel de servicio; **C-15 tiene que probarlo de punta a punta por HTTP**, y esa es la parte que hasta ahora nadie podía verificar.

## Cambios sugeridos a `CHANGES.md`

No se editan acá (otro agente tiene el archivo). Van al reporte:

1. **C-15 deja de ser gobernanza MEDIO uniforme.** El bloque de idempotencia toca código CRÍTICO de C-02. Sugerencia: `MEDIO (⚠️ un bloque CRÍTICO — `app/core/idempotency.py`)`.
2. **C-14 y C-15 son changes de cierre, no de construcción.** Las entradas ya dicen "Falta:"; conviene que digan además que la mitad restante **está en `main` sin haber pasado por OpenSpec** — es lo que explica por qué las delta specs cubren solo una parte de la capacidad.
3. **`IN-11` se puede tachar por completo**: `ADR-031` cerró los estados y `ADR-037` cerró la regla de los 7 días el 23-ago-2026.
4. **Hallazgo nuevo para la lista de abiertos**: `internal_notes` es una celda de `ADR-024` §6 que apunta a una columna que no existe, y sus celdas de lectura y escritura se contradicen (escribible por `salesperson`, no listada en su conjunto de lectura). No bloquea; necesita enmienda de `ADR-024`, no una migración.
