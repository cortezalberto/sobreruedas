# C-15 · Tareas

> **Gobernanza MEDIO — con una excepción.** El **bloque 4** modifica `app/core/idempotency.py`, que es código de **C-02, gobernanza CRÍTICA**: no se escribe una línea de ese bloque sin aprobación humana explícita. El resto del change se implementa con checkpoints, surfaciendo las decisiones no obvias.

> **TDD estricto.** Cada tarea de implementación va precedida de su test, y el test tiene que fallar por la razón correcta. Donde se modifica un archivo existente, la tarea arranca por la **red de seguridad**.

> **Alcance: los cuatro huecos.** Los cinco endpoints que ya funcionan no se rediseñan.

## 0. La puerta

- [x] 0.1 **C-14 tiene que estar cerrado, entero.** Verificar que existe la migración `019_vehicle_status_history` aplicada, que `StockService.editar` existe y emite `vehicle.updated`, y que `cambiar_estado` escribe historial. Sin la tabla no hay endpoint de historial y sin `editar` el `PATCH` no tiene a qué llamar. Si falta algo, **detenerse acá** (regla dura 12)
- [x] 0.2 Leer [`ADR-030`](../../../docs/adr/ADR-030-objetivo-de-ingenieria-y-slo-de-latencia.md) y anotar el número que rige acá: **objetivo de ingeniería del listado = p95 < 200 ms**, no el SLO de 300 ms ni el umbral de página. `IN-23` queda cerrado por ese ADR
- [x] 0.3 Confirmar que las celdas de `ADR-024` que este change ejecuta existen en `rbac.py`: `vehicles:update` en los tres roles (con `CAMPOS_DE_VEHICULO_PARA_VENDEDOR` en `salesperson`) y `vehicles:read` para el historial. Si alguna falta, **no se agrega acá**: sus filas van en `ADR-024` §6 antes que el endpoint
- [x] 0.4 **Red de seguridad global.** Suite completa del backend + baseline de cobertura. Cualquier fallo previo se reporta como **preexistente** y no se arregla acá

## 1. `PATCH /vehicles/{id}` — `T-079`

- [x] 1.1 **Red de seguridad** — correr `tests/integration/test_stock_router.py` y `test_permisos.py`. Anotar el baseline antes de tocar `router.py`
- [x] 1.2 **RED** — `tests/integration/test_vehicles_patch.py`: un `manager` edita varios campos y todos quedan modificados; el resto del vehículo no se mueve
- [x] 1.3 **RED** — un rol **sin** `vehicles:update` recibe 403
- [x] 1.4 **RED** — **aislamiento**: editar un vehículo de otra agencia devuelve **404**, no 403 ni 200. Es el test que `test_stock_router.py:123` ya hace para el listado, aplicado al `PATCH`
- [x] 1.5 **GREEN** — el endpoint, siguiendo el patrón de `tenancy/router_agencia.py:176,198` y `users/router_usuarios.py:142`. `response_model=None` y `_salida(...)` como los demás, porque la forma de la respuesta depende de la concesión
- [x] 1.6 **RED** — **recorte de campos**: un `salesperson` que manda `assigned_user_id` **y** `price_ars` cambia solo el primero, y el segundo queda igual — sin error (`D-3`)
- [x] 1.7 **RED** — el contrapeso: un `manager`, cuya concesión no acota campos, cambia `price_ars` sin problema. Sin este test, un recorte que descarte todo pasaría el 1.6
- [x] 1.8 **GREEN** — aplicar `recortar(datos.model_dump(exclude_unset=True), concesion)` antes de llamar al servicio. **No** hay `if role ==` en el router: `rbac.py` es la única copia de la matriz
- [x] 1.9 **RED** — cuerpo que queda vacío tras el recorte: la respuesta es 200, el vehículo no cambia y **no** se anota ningún evento en el outbox (`D-3`, `D-6` de C-14)
- [x] 1.10 **RED** — **hallazgo `H-a` de C-14**: fijar el comportamiento actual de `internal_notes`. Un `salesperson` que lo mande recibe 422 por campo desconocido (`extra="forbid"` de `_EntradaEstricta`), y el test **documenta en su docstring** que la celda de `ADR-024` §6 apunta a una columna que no existe. El hueco tiene que ser visible en la suite, no silencioso en el código
- [x] 1.11 **RED** — **de punta a punta**: un `PATCH` exitoso deja el `vehicle.updated` publicado. Es lo único que C-14 no podía verificar y este change sí: la fila del outbox tiene que quedar **marcada como publicada** después de que la petición termine, porque el drenaje vive en `sesion_del_tenant_actual`
- [x] 1.12 **RED** — que el `PATCH` **no** puede cambiar el estado: mandar `status` da 422 por campo desconocido
- [x] 1.13 **REFACTOR** — el endpoint tiene que quedar reconocible al lado de `cambiar_estado`. La asimetría deliberada —el `PATCH` **no** llama a `verificar_alcance` porque las tres celdas son `all` (`D-3`)— va comentada en el sitio, o el próximo lector la lee como un olvido

## 2. `GET /vehicles/{id}/history` — `T-085`

- [x] 2.1 **RED** — `tests/integration/test_vehicles_history.py`: un vehículo cargado y con dos transiciones devuelve **tres** registros, del más nuevo al más viejo, con la fila génesis (`from_status` nulo) al final
- [x] 2.2 **RED** — **aislamiento**: el historial de un vehículo de otra agencia devuelve 404
- [x] 2.3 **RED** — un vehículo dado de baja lógicamente responde igual que uno inexistente, coherente con el resto de las operaciones
- [x] 2.4 **GREEN** — el endpoint con `require_permission("vehicles:read")`, respondiendo `list[HistorialDeEstado]`
- [x] 2.5 **RED** — `D-4`: un `salesperson` —cuya concesión de `vehicles:read` trae `CAMPOS_DE_VEHICULO_SIN_COSTO`— recibe los registros **completos**, con `from_status`, `to_status`, `changed_by` y `changed_at`. Si alguien aplicara `recortar()` a ciegas, este test devuelve registros en blanco y se pone rojo
- [x] 2.6 **RED** — el historial **no** filtra información económica: sobre un vehículo con `acquisition_cost_ars` cargado, ningún registro trae precio ni costo (`D-4`)
- [x] 2.7 **RED** — la ruta resuelve bien: `/vehicles/{uuid}/history` no se la come `/{vehiculo_id}`. Es el mismo cuidado que el docstring de `plantilla_de_importacion` documenta para `import/template`

## 3. `GET /vehicles` pagina — `T-080`

- [x] 3.1 **RED** — `tests/integration/test_vehicles_listado_paginado.py`: recorrido completo de 25 vehículos con `limit=10` — tres páginas, cada vehículo exactamente una vez, y la tercera sin header `X-Next-Cursor` (`D-2`)
- [x] 3.2 **RED** — el cuerpo sigue siendo un **array**, no un sobre. Es el test que protege a `frontend-web/src/lib/api.ts` de romperse
- [x] 3.3 **RED** — `limit` por encima del máximo **se acota, no falla** (`acotar_tamano` ya lo hace; el test verifica que el endpoint no lo revalide por su cuenta con otro criterio)
- [x] 3.4 **RED** — **aislamiento**: un cursor emitido para otra agencia se rechaza **y** `violaciones_de_aislamiento()` sube en uno. Contar sin rechazar sería peor que no contar, y rechazar sin contar deja un barrido de cursores ajenos sin rastro (`RN-MT-08`)
- [x] 3.5 **RED** — cursor ilegible: mismo error que el cursor de otra agencia, sin revelar cuál de los dos casos fue
- [x] 3.6 **RED** — **paginar con filtros**: recorrer por páginas el listado filtrado por estado devuelve exactamente el mismo conjunto que el filtro sin paginar. Es el test que detecta el error clásico —aplicar el cursor antes que el filtro— que de otro modo aparece como "faltan autos" mucho después
- [x] 3.7 **GREEN** — `VehicleRepository.listar` gana su variante paginada con `select(Vehicle, Vehicle.created_at.label("created_at"), Vehicle.id.label("id"))` y recupera las entidades con `fila[0]`. **Con el comentario que explique el contrato de `paginar` en el sitio** (`D-2`): sin él, la primera refactorización lo "simplifica" a `select(Vehicle)` y rompe
- [x] 3.8 **RED** — test de que la página trae instancias de `Vehicle` y no `Row`, para que el 3.7 no se pueda deshacer en silencio
- [x] 3.9 **RED** — el filtro de tenant sigue en la consulta y no lo pone `paginar` (su docstring lo dice explícitamente): verificar que `_vivos()` está en el camino paginado. Capa 3, regla dura 1
- [x] 3.10 **GREEN** — el endpoint toma `cursor` y `limit` por query y devuelve `X-Next-Cursor` cuando hay página siguiente
- [x] 3.11 **GREEN** — ajustar `frontend-web/src/lib/api.ts` para que el listado **no se trunque en silencio** al pasar de "todo" a "una página" (`D-2`). La paginación de la UI es C-19; acá solo se evita la regresión invisible
- [x] 3.12 Correr `test_vehiculo_espejado.py` y `test_alta_espejada.py`: el espejo no debería moverse —no cambia ningún schema expuesto— y si se mueve es un efecto que nadie previó

## 4. ⛔ `Idempotency-Key` en `POST /vehicles` — `T-078` · **CÓDIGO CRÍTICO**

> **Detenerse antes de empezar este bloque.** Toca `app/core/idempotency.py` (C-02, gobernanza CRÍTICA). Requiere aprobación humana explícita sobre `D-1`, no sobre este listado.

- [x] 4.1 **Red de seguridad, obligatoria** — correr `tests/integration/test_idempotencia.py`, `test_eventos.py` y `test_eventos_consumo.py` **antes de tocar nada**. Anotar el baseline. El consumidor de eventos es el único caller existente de `ejecutar_idempotente` y no puede cambiar de comportamiento
- [x] 4.2 **RED** — test de no-regresión de C-02: `ejecutar_idempotente` **sin** el parámetro `sesion` se comporta exactamente como hoy — reserva, ejecuta, guarda, y libera si falla. Este test se escribe **primero** y tiene que pasar antes y después del cambio
- [x] 4.3 **RED** — con `sesion` provista, la reserva, la creación y el guardado de la respuesta ocurren **en esa transacción**: si la transacción revierte, no queda ni el recurso ni la clave reservada (`D-1`)
- [x] 4.4 **RED** — la ventana de caída queda cerrada: no existe un estado en el que el recurso exista y la clave quede reservada con `status_code IS NULL`
- [x] 4.5 **GREEN** — el parámetro opcional `sesion: AsyncSession | None = None` en `ejecutar_idempotente`, **aditivo**: con `sesion=None` no cambia una línea del camino existente. `_LIBERAR` **no** corre en modo compartido — el rollback ya libera la reserva, y un `UPDATE` sobre una transacción abortada no es una operación
- [x] 4.6 **RED** — dos peticiones **concurrentes reales** (no simuladas) con la misma clave: se crea **un** vehículo, y la segunda obtiene el resultado de la primera o un 409, **en tiempo acotado**
- [x] 4.7 **GREEN** — `SET LOCAL lock_timeout` antes de la reserva, con el valor como **constante nombrada** del módulo y no un número suelto. Al vencer se traduce a la `ClaveEnConflicto` que el módulo **ya tiene escrita** para el caso en vuelo: la semántica documentada no cambia, cambia cómo se detecta
- [x] 4.8 **RED** — el endpoint: reintento idéntico devuelve el resultado de la primera y **no** crea un segundo vehículo
- [x] 4.9 **RED** — misma clave, cuerpo distinto → **409** con `code = "idempotency_key_conflict"`
- [x] 4.10 **RED** — **sin** clave, el alta se procesa normalmente. La idempotencia se ofrece, no se impone
- [x] 4.11 **RED** — la misma clave en **dos agencias** crea dos vehículos y ninguna ve el resultado de la otra
- [x] 4.12 **RED** — un alta que falla por regla de negocio (dominio duplicado, cuota de plan agotada) **no** deja vehículo **y** deja la clave reutilizable de inmediato
- [x] 4.13 **RED** — clave de longitud desmesurada → **422**, y no llega a la base. La columna `key` de la migración `003` es `TEXT`, sin techo (`D-1`)
- [x] 4.14 **GREEN** — el header en el endpoint: `Annotated[str | None, Header()] = None`, con la validación de longitud, y `cuerpo = datos.model_dump(mode="json")` — el modelo validado, **no** los bytes crudos (`D-1`, punto 3)
- [x] 4.15 **RED** — **la precondición del patrón** (`D-1`): `POST /vehicles` responde la misma forma para todos los roles y **nunca** `VehiculoSalidaConCosto`. Si alguna vez empieza a elegir schema por concesión, este test se pone rojo **antes** de que la respuesta guardada se convierta en una fuga
- [x] 4.16 **RED** — el evento sigue saliendo: un alta con clave deja `vehicle.created` publicado igual que un alta sin clave. Es el riesgo que hizo descartar la opción (a) y hay que probar que la opción elegida no lo tiene
- [x] 4.17 Correr el baseline de 4.1 completo. **Cero cambios** en el comportamiento del consumidor de eventos

## 5. El gate: la convención deja de ser opcional — `D-6`

- [x] 5.1 **RED** — `tests/unit/test_convenciones_de_ruta.py`: una ruta `POST` de creación sin `Idempotency-Key`, y fuera de la lista de excepciones, hace fallar la verificación. Probarlo con una app de juguete, como hacen `test_auth_rutas.py` y `test_migraciones_compatibles.py`
- [x] 5.2 **RED** — una ruta `GET` de colección sin `cursor`/`limit`, fuera de excepciones, hace fallar
- [x] 5.3 **RED** — una excepción **sin motivo** hace fallar. Sin este test la lista de excepciones se vuelve un cajón
- [x] 5.4 **RED** — el contrapeso: una excepción **con** motivo pasa
- [x] 5.5 **GREEN** — el gate, recorriendo las rutas realmente registradas en la aplicación, con la lista de excepciones justificadas: `GET /vehicles/{id}/history` (`D-5`), `GET /vehicles/import/template` (no es colección), y las que aparezcan al correrlo
- [x] 5.6 **Correr el gate contra la aplicación real y anotar qué encuentra.** Va a nombrar endpoints de otros módulos que tampoco cumplen. **No se arreglan acá**: se listan en el reporte y se declaran como excepción temporal con motivo `"pendiente — <change que lo cubre>"`, para que la deuda quede contada en vez de escondida

## 6. Latencia, cierre y reporte

- [x] 6.1 **`ADR-030`, objetivo de ingeniería del listado: p95 < 200 ms.** Medir con datos sembrados a escala realista (una agencia con ~1.000 vehículos), tráfico nominal, y **anotar el resultado**. No va como assert de milisegundos dentro de `pytest`: eso mide la máquina del CI, no el sistema (`D-7`)
- [x] 6.2 Si el número no se alcanza, verificar que el plan de consulta usa el índice y **reportarlo**; no rediseñar el índice dentro de este change sin decirlo
- [x] 6.3 `ruff` y `mypy --strict` limpios sobre todo lo tocado, backend y frontend (`eslint`, `tsc --strict`, cero `any`)
- [x] 6.4 Verificar que `openapi.yaml` refleja los dos endpoints nuevos y los dos parámetros nuevos (`test_openapi_exportado.py`)
- [x] 6.5 **Cobertura** ≥ 80 % global **y sin bajar** respecto del baseline de 0.4 (regla dura 5)
- [x] 6.6 Suite completa contra el baseline de 0.4. Cero regresiones
- [x] 6.7 **Reporte**: qué encontró el gate de 5.6 en el resto de los módulos, el número real de latencia de 6.1, y los cambios sugeridos a `CHANGES.md` que el proposal enumera
