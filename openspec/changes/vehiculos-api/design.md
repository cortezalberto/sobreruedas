# C-15 · Diseño

> Alcance: **los cuatro huecos**. Los cinco endpoints que `ESC-003` dejó andando —listar, obtener, crear, cambiar estado, dar de baja— y la plantilla de importación de C-17 no se rediseñan.

---

## D-1 · `Idempotency-Key` en el `POST`: la decisión más cara del change

> ⛔ **La opción elegida toca `app/core/idempotency.py`, que es código de C-02, gobernanza CRÍTICA.** El bloque 4 de las tareas no se implementa sin aprobación humana explícita, aunque el resto del change sea MEDIO. Está dicho también en el proposal, porque cambia quién aprueba y no solo cómo se hace.

### El problema, exacto

`ejecutar_idempotente` **abre sus propias sesiones**: una para reservar la clave (`idempotency.py:159`), una para liberarla si `crear()` falla (`:199`), y una para guardar la respuesta (`:203`). Su comentario lo dice y lo justifica: *"FUERA de la transacción de la reserva, y a propósito: si `crear` abre su propia sesión —que es lo normal— compartir transacción la dejaría anidada"*.

Pero en un endpoint de FastAPI de este proyecto **`crear` no abre su propia sesión**: la sesión ya viene abierta por inyección, porque `SesionDeTenant` es lo que exige token, lo valida, saca el tenant del claim y abre la transacción con el contexto puesto. Las dos piezas se escribieron para mundos distintos y hasta hoy nunca se cruzaron: el único caller de `ejecutar_idempotente` en todo `app/` es [`core/events.py:282`](../../../backend/app/core/events.py), que consume Redis Streams y efectivamente **no** tiene sesión.

### Las opciones

#### (a) El router deja de pedir `SesionDeTenant`; `crear` abre la suya

El endpoint tomaría `SujetoActual`, y la callable `crear` haría `async with sesion_de_tenant(sujeto.tenant_id)` adentro.

**Rechazada, y no por estilo: por el outbox.** `sesion_del_tenant_actual` no solo abre la transacción — es el **único punto del sistema** donde la transacción ya commiteó y todavía se sabe de qué tenant se trata, y por eso es donde vive `await drenar(sesion)` (`ADR-036`). Un `POST /vehicles` que no pase por esa dependency **no publica `vehicle.created`**.

Y el modo de fallo es el peor posible: `drenar` **no levanta aunque Redis esté caído**, por diseño. Así que no drenar tampoco levanta. El evento quedaría anotado en el outbox, la petición devolvería 201, el cliente vería su vehículo, y nadie se enteraría de que la publicación dejó de ocurrir hasta que alguien buscara por qué C-18 no indexa.

Se podría replicar el drenaje dentro de `crear`. Eso es duplicar el punto más delicado de `ADR-036` en un módulo de negocio, y garantizar que la próxima copia se olvide de algo.

#### (b) `ejecutar_idempotente` pasa a recibir siempre una sesión

**Rechazada por no ser aditiva.** `core/events.py` la llama sin sesión y con `dsn`, desde el consumidor de eventos, fuera de todo ciclo de petición. Cambiar la firma obliga a tocar el consumidor de eventos —otra pieza crítica— en el mismo movimiento, y a probar dos caminos que hoy funcionan por uno que todavía no existe.

#### (c) Una implementación propia de la reserva en el módulo de stock

Reescribir el `INSERT ... ON CONFLICT DO UPDATE` dentro de `modules/stock/`, sin tocar `core/`.

**Rechazada.** Habría **dos** implementaciones de idempotencia en el sistema, y la garantía no la da el código sino el índice único — así que las dos competirían por la misma tabla con criterios propios de expiración y de huella. El día que la copia y el original diverjan, el síntoma va a aparecer en el endpoint de pagos, que es donde la idempotencia importa de verdad.

#### (d) ✅ Un parámetro opcional: `ejecutar_idempotente(..., sesion=None)`

```
async def ejecutar_idempotente(
    *, tenant, clave, cuerpo, crear, dsn=None, sesion: AsyncSession | None = None
) -> tuple[Any, int]
```

- **`sesion is None`** → **exactamente** el comportamiento de hoy, línea por línea. `core/events.py` no se toca y no cambia de comportamiento.
- **`sesion` provista** → la reserva, la ejecución de `crear` y el guardado de la respuesta ocurren **en esa transacción**.

**Por qué gana**: es el único camino que deja el ciclo de petición intacto —`SesionDeTenant` sigue siendo el único parámetro del endpoint, el drenaje del outbox sigue donde está, `ADR-036` no se replica— y el único cuyo diff en código crítico se revisa en una lectura, porque no modifica ninguna ruta existente.

### El bug que aparece al mirar de cerca

El diseño actual, con sus tres transacciones, tiene una **ventana de caída** que no está documentada en ningún lado:

```
txn1: reservar la clave            ✓ commit
txn2: crear()                      ✓ commit  ← el recurso YA EXISTE
      ☠ el proceso muere acá
txn3: guardar (response, status)   ✗ nunca corre
```

La fila queda con la clave reservada y `status_code IS NULL` durante las 24 h de retención. El cliente, que recibió un error de red, reintenta con la misma clave —que es exactamente lo que la idempotencia existe para permitirle— y recibe `409 "hay una petición con esta misma clave todavía en curso"`. **Durante 24 horas.** El recurso existe y el cliente no tiene forma de averiguarlo por esa vía.

Con la sesión compartida las tres cosas commitean juntas o no commitea ninguna, y la ventana **desaparece**. No es el motivo por el que se elige (d), pero es la razón por la que (d) no es solo el menor de los males.

### Lo que hay que resolver dentro de (d)

**1. La concurrencia deja de contestar y pasa a esperar.** Con sesión compartida, la segunda petición con la misma clave se queda **bloqueada en el lock de la fila** en vez de recibir "no volvió ninguna fila". Un bloqueo indefinido retiene una conexión del pool, y bajo una tormenta de reintentos eso es una caída.

Se acota con `SET LOCAL lock_timeout` antes de la reserva. Al vencer, PostgreSQL levanta y se traduce a la `ClaveEnConflicto` que el módulo **ya tiene escrita** para este caso: *"hay una petición con esta misma clave todavía en curso"*. La semántica documentada se conserva intacta; lo que cambia es cómo se detecta.

**2. `_LIBERAR` no corre en modo compartido, y no debe.** Si `crear()` falla, la transacción entera revierte y la reserva se va con ella. Intentar liberarla sería un `UPDATE` sobre una transacción abortada.

**3. Qué se hashea.** El `cuerpo` es `datos.model_dump(mode="json")` —el modelo Pydantic ya validado—, **no** los bytes crudos de la petición.

Con los bytes crudos, un cliente que reintenta y vuelve a serializar con las claves en otro orden, o con `2000.0` donde antes escribió `2000.00`, recibiría un 409 por una petición idéntica. `huella()` ya normaliza el orden con `sort_keys`; validar primero normaliza además la forma de decimales, UUIDs y enums. La contracara —dos cuerpos crudos distintos que validan al mismo modelo se consideran la misma petición— es el comportamiento correcto: son la misma petición.

**4. La clave se acota en el borde.** La columna `key` de la migración `003` es `TEXT`, sin techo. Un `Idempotency-Key` de un megabyte llegaría a la base. Se valida en el header: entre 1 y 255 caracteres, o 422.

### ⚠️ La precondición del patrón, que hay que escribir ahora y no descubrir después

La respuesta guardada se devuelve tal cual en el reintento. La clave es única **por `(tenant_id, key)`** — no por usuario. Así que **una persona puede reproducir la respuesta que se guardó para otra persona de su misma agencia**.

Hoy eso no filtra nada, y por un motivo concreto que hay que verificar y no suponer: `POST /vehicles` responde **siempre** `VehiculoSalida`, nunca `VehiculoSalidaConCosto` — no llama a `_salida()` ni mira la concesión ([`router.py:143`](../../../backend/app/modules/stock/router.py)). La forma de su respuesta no depende de quién pregunta, así que reproducirla no le muestra a nadie nada que no pudiera ver.

**Eso es una precondición del patrón, no una propiedad de la idempotencia.** El día que un endpoint de creación devuelva una forma que dependa de la concesión de quien llama, guardar la respuesta y reproducirla **es una fuga por la puerta de atrás**, exactamente del tipo que `RN-ST-12` intenta cerrar por la puerta de adelante.

Va escrito en el requisito de la spec y va con un test: si `POST /vehicles` alguna vez empieza a elegir schema por concesión, ese test se pone rojo antes de que la fuga exista.

---

## D-2 · El listado pagina sin cambiar la forma de su respuesta

**Decisión**: `GET /vehicles` gana `?cursor=` y `?limit=`. El cuerpo sigue siendo un **array de vehículos**; el cursor de la página siguiente viaja en el header **`X-Next-Cursor`**, y **su ausencia significa última página**.

**Por qué un header y no un sobre `{items, next_cursor}`**:

1. **Es la convención del corpus.** `knowledge-base/02` §148 describe la metadata de paginación como headers (`X-Total-Count`, `X-Page`, `X-Page-Size`). El sobre no aparece en ningún documento.
2. **No rompe al cliente que ya existe.** [`frontend-web/src/lib/api.ts:312`](../../../frontend-web/src/lib/api.ts) valida `Array.isArray(datos) && datos.every(esVehiculo)`. Un sobre lo rompe en tiempo de ejecución; un header lo deja funcionando.
3. **No obliga a decidir la forma del sobre para los otros quince módulos** en el change que da la casualidad de ser el primero que pagina.

**Cursor y no paginación numerada**, aunque §148 ofrezca las dos: la numerada exige un `COUNT` total, y `core/pagination.py` documenta en su encabezado por qué lo evitó —sobre una tabla grande el conteo cuesta más que la página—. El corpus ofrece un menú y no asigna un mecanismo a `GET /vehicles`; se elige el que existe, está probado y no lo usa nadie.

**Lo que sí cambia de comportamiento**: hoy el listado devuelve **todo**; mañana devuelve **20 por defecto**. Un cliente que no sepa de cursores va a ver menos autos que antes, sin ningún error. Por eso el ajuste de `frontend-web/src/lib/api.ts` **entra en este change** aunque sea frontend: dejarlo truncando en silencio es peor que romperlo.

### El detalle técnico que no es obvio

`paginar()` exige que la consulta **seleccione explícitamente** `created_at` e `id`, y devuelve `list[Row[Any]]`. Un `select(Vehicle)` a secas no sirve: la `Row` que vuelve tiene un solo elemento —la entidad— y `getattr(fila, "created_at")` falla.

La consulta va así:

```
select(Vehicle, Vehicle.created_at.label("created_at"), Vehicle.id.label("id"))
```

La entidad **más** las dos columnas del orden, etiquetadas. `paginar` encuentra lo que su contrato pide en `selected_columns`, y el repositorio recupera los objetos con `fila[0]`, así que el router sigue recibiendo instancias de `Vehicle` y `_salida()` no cambia.

Es raro de leer y por eso va con un comentario que lo explique en el sitio. **La alternativa —tocar `core/pagination.py` para que acepte entidades— es código de C-02 y no vale un `label`.**

El índice que sostiene el orden es el `ix_vehicles_tenant_id (tenant_id, deleted_at)` que ya existe más el orden por `(created_at, id)`; si el plan de consulta no lo aprovecha, eso es un hallazgo de la tarea de latencia, no un rediseño acá.

⚠️ **`paginar` no agrega el filtro por tenant** —lo dice su docstring: *"El filtro por tenant va en `consulta`"*—. El repositorio ya lo pone en `_vivos()`. Se verifica con un test, no con la lectura.

---

## D-3 · El `PATCH` recorta campos con el helper que ya existe

**Decisión**: el endpoint pide `require_permission("vehicles:update")`, recibe la `Concesion`, y aplica `recortar(datos.model_dump(exclude_unset=True), concesion)` antes de llamar al servicio.

**Por qué `recortar` y no una segunda lectura de la matriz**: `rbac.py` es la única copia de `ADR-024`, y `recortar()` existe justamente para esto — *"aplica tanto a escritura como a LECTURA"*, dice su docstring. Un `if sujeto.role == "salesperson"` en el router sería la segunda lectura, y la segunda lectura es donde las dos se despegan.

**El alcance no se verifica**: las tres celdas de `PATCH /vehicles/{id}` son `all` (`ADR-024` §3, línea 136), y el propio ADR explica por qué el `salesperson` es `all` con campos acotados y no `own` — la autoasignación sería imposible si solo pudiera tocar los que ya tiene. Así que **no** va `verificar_alcance` acá, a diferencia de `POST /{id}/status`. Se deja dicho para que la asimetría con el endpoint de al lado no se lea como un olvido.

**Recortar deja el cuerpo vacío**: es lo que pasa si un `salesperson` manda solo `{"price_ars": ...}`. No es un error de permiso —tiene el permiso, y `ADR-024` no le da ese campo—: la edición simplemente no cambia nada. Se responde el vehículo sin tocar, sin evento (`D-6` de C-14). Rechazar con 403 revelaría, campo por campo, la forma de la matriz.

**`internal_notes`** (hallazgo `H-a` de C-14): no es columna del modelo ni campo de `VehiculoEditar`, así que `recortar` con `CAMPOS_DE_VEHICULO_PARA_VENDEDOR` deja al vendedor con `assigned_user_id` y nada más. Correcto y seguro. Va un test que **fija ese comportamiento** para que el hueco sea visible en la suite en vez de silencioso en el código.

**404 y no 403 para un vehículo de otra agencia**: `VehiculoNoEncontrado` ya pisa el status a 404 por la razón que su docstring argumenta — distinguir "no existe" de "no es tuyo" le confirmaría a un tenant que cierto id existe en otra agencia.

---

## D-4 · El recorte de campos de `vehicles:read` NO se aplica al historial

**Decisión**: `GET /vehicles/{id}/history` exige `vehicles:read` y **devuelve la fila de historial completa**, sin pasarla por `recortar()`.

**Por qué hay que decidirlo y no heredarlo**: la concesión de `vehicles:read` para el `salesperson` es `Concesion(Alcance.ALL, CAMPOS_DE_VEHICULO_SIN_COSTO)`, y esa lista blanca es —campo por campo— el esquema `VehiculoSalida`. Contiene `status`, `color`, `price_ars`. **No contiene `from_status`, `to_status`, `changed_by` ni `changed_at`**, porque son columnas de otra tabla.

Aplicar el recorte a ciegas devolvería registros en blanco. Y "en blanco" es el peor resultado posible: no falla, no avisa, y el vendedor concluye que el auto no tiene historia.

**El conjunto de campos de una concesión está definido sobre un recurso**, y el recurso de esa celda es el vehículo. El historial es otra forma y `ADR-024` §3 no le asigna restricción de campos a ninguno de los tres roles — la fila 132 les da `all` a los tres, sin corchetes.

**Lo que sí hay que verificar**: que el historial no se convierta en una vía lateral para leer lo que `RN-ST-12` restringe. No lo es: la fila lleva estados, un motivo, un autor y una fecha. **Ningún precio, ningún costo.** Va como test explícito, no como observación.

---

## D-5 · El historial no pagina

Decidido en `D-8` de C-14 y se repite acá porque es el endpoint el que lo hace visible: la cantidad de filas está acotada por la máquina de estados —seis estados, nueve transiciones legales, cada una una acción humana—, así que el peor caso realista entra en una pantalla.

La salida técnica, si algún día hace falta, está escrita en C-14 y no obliga a tocar `core/`: `Historial.changed_at.label("created_at")` y `paginar` funciona.

---

## D-6 · El gate: la convención deja de ser opcional

**Decisión**: un test de arquitectura nuevo, `tests/unit/test_convenciones_de_ruta.py`, que **recorre las rutas realmente expuestas** por la aplicación y exige:

1. Toda ruta `POST` que cree un recurso **declara el parámetro `Idempotency-Key`**.
2. Toda ruta `GET` que devuelva una colección **declara `cursor` y `limit`**.
3. Ningún endpoint de creación con clave de idempotencia elige su schema de respuesta según la concesión (`D-1`, la precondición del patrón).

**Por qué un gate y no disciplina**: porque la disciplina ya falló, de forma documentada. `platform/api-conventions` describe las dos convenciones **como si los endpoints las cumplieran** desde C-02, y hasta hoy no las cumple ninguno. Los dos módulos están escritos, probados y desconectados, y nada se puso rojo.

El precedente existe y funciona: `test_auth_rutas.py` recorre las rutas y encontró un endpoint sin token que la lectura había dado por bueno —lo cuenta el docstring de `plantilla_de_importacion`—, y la verificación del bloque 6 de C-02 recorre las operaciones expuestas y encontró tres que no tenían fila en `ADR-024`.

**Con lista de excepciones explícita y justificada**, como las de `test_arquitectura.py`. Un endpoint que legítimamente no pagina —el historial, por `D-5`— figura ahí con su motivo. Una excepción con nombre y razón se lee en un diff; un gate que no existe, no.

---

## D-7 · La latencia se verifica contra el objetivo, no contra el SLO

`ADR-030` separa tres números para el listado y este change usa **el de arriba**:

| | Listado | Quién lo fija | Dónde se verifica |
|---|---|---|---|
| **Objetivo de ingeniería** | **200 ms** | **N0** | k6 con tráfico nominal · **DoD de las historias** ← *acá* |
| SLO con presupuesto de error | 300 ms | N3 | 30 días rolling |
| Umbral de página | 300 ms | este ADR | Prometheus, 15 min |

El ADR es explícito: *"los thresholds de k6/Locust y la Definición de Terminado de las historias salen de la fila objetivo de ingeniería — son 200/500, no 300/2000"*.

La tarea correspondiente **no** es un test de performance en la suite unitaria: se mide con datos sembrados a escala realista y se anota el resultado. Un assert de milisegundos dentro de `pytest` mide la máquina del CI, no el sistema.

---

## Riesgos

| Riesgo | Mitigación |
|---|---|
| ⛔ La modificación de `core/idempotency.py` rompe el consumidor de eventos, que es la otra pieza crítica | El parámetro es opcional y `events.py` no lo pasa: el camino existente queda **idéntico**. Se verifica corriendo `test_eventos_consumo.py` y `test_idempotencia.py` **antes** de tocar el archivo y comparando contra el baseline |
| El `lock_timeout` queda corto y un `POST` legítimo bajo carga se rechaza con 409 | El timeout se elige mayor que el p99 esperado del `POST` y se deja como constante nombrada del módulo, no como número suelto. El caso se prueba con dos peticiones concurrentes reales, no simuladas |
| El listado empieza a truncar y una pantalla muestra menos autos sin avisar | El ajuste del cliente HTTP entra en este change (`D-2`), y la paginación de la UI queda declarada como C-19 |
| El `select(Vehicle, ...)` con columnas etiquetadas se "simplifica" en una refactorización futura y `paginar` empieza a fallar | Comentario en el sitio explicando el contrato de `paginar`, y un test que verifica que la página trae instancias de `Vehicle` |
| El gate de `D-6` se vuelve un obstáculo y alguien lo apaga | Lista de excepciones **con motivo obligatorio**, igual que `test_arquitectura.py`. Apagarlo entero se ve en el diff; agregar una excepción también |
