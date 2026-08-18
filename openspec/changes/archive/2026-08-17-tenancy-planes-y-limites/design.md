# C-04 · Diseño técnico

## D-1 — `tenants` y `plans` quedan exentas de RLS; `branches` y `subscriptions` no

`EXENTAS_DE_RLS` en [`test_tenant_isolation.py`](../../../../backend/tests/integration/test_tenant_isolation.py) ya nombra a `tenants` y `plans`, por `RN-MT-09`. **No se re-decide: se aplica.**

El motivo es estructural, no una concesión. La política canónica del proyecto compara `tenant_id` contra `app.current_tenant`, y ninguna de las dos tablas tiene esa columna:

| Tabla | Por qué no lleva `tenant_id` | Cómo se aísla |
|---|---|---|
| `tenants` | `tenants.id` **es** el tenant | Filtro explícito por `id` en el repositorio |
| `plans` | Catálogo comercial compartido, igual para todos | No requiere aislamiento: no contiene dato de nadie |
| `branches` | Sí lo lleva | RLS + `FORCE` + filtro explícito |
| `subscriptions` | Sí lo lleva | RLS + `FORCE` + filtro explícito |

**Se evaluó ponerle RLS a `tenants` con una política sobre `id`, y se descartó con razón concreta**: la creación de un tenant ocurre **antes** de que exista contexto de tenant —no hay `app.current_tenant` que setear para una fila que todavía no existe— y ocurre desde el espacio administrativo, fuera de todo tenant. Con `FORCE`, esa política dejaría la creación de agencias imposible incluso para el propietario del esquema. La alternativa —una política que se abra cuando el contexto está vacío— es exactamente el agujero que `RN-MT-06` prohíbe: convertiría "sin contexto" en "todo permitido", cuando la regla es que sin contexto **no se devuelve ninguna fila**.

> ⚠️ **Consecuencia asumida, y dónde se paga.** `tenants` queda protegida por **dos** capas en vez de tres. Ese hueco lo cubre C-05 al montar el endpoint: toda lectura de `tenants` desde el espacio de tenant filtra por el `id` del token, nunca por un `id` del path. El día que alguien escriba `GET /tenants/{id}` sin ese filtro, **RLS no lo va a salvar**. Queda dicho acá porque es el único lugar del sistema donde el aislamiento no tiene red.

## D-2 — `IN-03` resuelto: los límites de `plan-gtm`

Decisión de Dirección del 17-ago-2026. **Los dos documentos que discrepaban son N4 — no normativos**, así que la resolución no fue por precedencia documental: fue una decisión comercial tomada por el único decisor del proyecto.

| | Starter | Pro | Enterprise |
|---|---|---|---|
| `max_users` | 2 | 5 | 15 |
| `max_vehicles` | 80 | 300 | **0** (ilimitado) |
| `max_branches` | 1 | 2 | 5 |
| `max_whatsapp_messages_month` | 1.500 | 5.000 | 20.000 |

Dos cosas que van con eso:

**`0 = ilimitado`, y no `NULL`.** Es la convención que fija la propia `spec-tecnica` §3.3 (*"Límite de usuarios. 0 = ilimitado"*). Se conserva. `plan-gtm` dice *"sin límite práctico"* para los vehículos de Enterprise, que es exactamente ese caso. El riesgo obvio —que `PlanLimitsService` lea el 0 como "cero permitidos" y bloquee todo en Enterprise— tiene test propio, porque es el modo de fallar más silencioso de esta tabla: nadie reporta "no puedo cargar vehículos" como un bug de facturación.

**`max_whatsapp_messages_month` es una columna nueva.** `plan-gtm` cuota los mensajes de WhatsApp por mes y el modelo de datos no tenía dónde ponerlo. Se agrega ahora, vacía de uso: **la consumen C-29 y C-30**. Agregar la columna hoy cuesta una línea; agregarla en la Ola 1.5 cuesta una migración sobre una tabla con datos de facturación.

## D-3 — `IN-04` resuelto: se conserva `price_ars`, y el precio no sale de `plan-gtm`

Decisión de Dirección del 17-ago-2026: el esquema mantiene `price_ars numeric(18,2)` tal como lo escriben las tablas de `spec-tecnica` §3.3.

**De esto se sigue algo que hay que decir, porque si no parece un descuido.** Los límites salen de `plan-gtm` (`D-2`), y ese documento cotiza en **USD 49 / 149 / 399**. Una columna `price_ars` no puede guardar dólares. Así que el seed toma:

- **límites** de `plan-gtm` — la decisión de `D-2`
- **precios** de `mejoras-y-saas`: **ARS 45.000 / 95.000 / 195.000** — la única cifra en pesos que existe en el corpus

No es una conversión: a cualquier tipo de cambio razonable, USD 49 y ARS 45.000 no son el mismo precio. **Son dos propuestas comerciales distintas y el seed toma una de cada una.** Es representable y es coherente, pero es una mezcla deliberada, no una derivación.

> **Lo que se acepta al conservar `price_ars`.** La propia `spec-tecnica` se contradice: §3.1 fija como convención general que *"los valores monetarios se almacenan en `numeric(18,2)` con la moneda como columna asociada (ARS, USD)"*, y después ~10 tablas usan `*_ars` sin columna de moneda. La única que cumple la convención es `payments` (`amount_ars, currency`).
>
> Conservar `price_ars` alinea el código con las tablas y **no** con la convención. El costo queda anotado, no escondido: facturar en USD más adelante exige una migración sobre tablas con datos, y `vehicles` ya necesita `price_usd` (spec §3.3), así que el producto va a terminar con dos columnas ad hoc donde la convención pedía una. **No es deuda oculta: es una decisión tomada con el costo a la vista.**

## D-4 — PostGIS se instala en este change

`branches.geo_point` es `geography(Point,4326)`. La extensión está **disponible** en la imagen (`postgis/postgis:16-3.4-alpine`) pero **no creada**: la migración `001_extensiones` de C-02 instala `uuid-ossp`, `pg_trgm`, `unaccent` y `btree_gin`, y PostGIS no está en esa lista.

Se agrega en una migración propia de C-04 y **no** editando `001`, que ya está aplicada en todos los entornos. Editar una migración aplicada no la vuelve a correr: la deja mintiendo.

La migración va **antes** de la de `branches`, porque `CREATE TABLE` con una columna `geography` falla si el tipo no existe. Es aditiva y por lo tanto compatible hacia atrás (regla dura 13): la versión anterior de la aplicación no conoce la extensión y no le molesta que exista.

## D-5 — `branches` lleva `deleted_at` aunque la spec no lo diga

`spec-tecnica` §3.3 define `branches` con `is_active boolean` y **sin `deleted_at`**. Se agrega igual.

`is_active` y `deleted_at` no son lo mismo y el producto necesita los dos:

| Campo | Significa | Caso real |
|---|---|---|
| `is_active` | Sucursal existente que no está operando | Cerrada por refacción, reabre en marzo |
| `deleted_at` | Sucursal que dejó de existir | Se cerró definitivamente |

Sin `deleted_at`, dar de baja una sucursal obliga a `DELETE`, que el **Principio 3** de la constitución prohíbe — y una sucursal borrada físicamente se lleva por delante el histórico de qué vehículo estuvo dónde.

Es un desvío de N1 en favor de N0, que es la dirección permitida por `ADR-000`: **N0 nunca pierde**. Se registra acá, que es lo que el Principio 5 exige para que la decisión sea vinculante.

## D-6 — El rechazo por cuota de plan es `402`, no `403`

La ficha de C-04 en `CHANGES.md` dice *"devuelva `402`/`403`"*, dejando la elección abierta. Se elige **`402 Payment Required`**, y la distinción no es cosmética.

| Código | Qué le dice a quien llama | Qué puede hacer |
|---|---|---|
| `401` | No sé quién sos | Autenticarse |
| `403` | Sé quién sos y no te alcanza el rol | Pedirle a un manager que lo haga |
| **`402`** | Sé quién sos, **tenés el permiso**, y el plan no da | **Subir de plan** |

Un `403` acá manda al usuario por el camino equivocado: va a buscar a alguien con más permisos, y no hay permiso que agregue vehículos por encima de la cuota. **El manager tampoco puede.** Y para el producto la diferencia importa todavía más: un `402` es una señal comercial —un tenant tocando su techo es un candidato a upgrade— y un `403` es ruido de soporte.

`PlanLimitsService` levanta `PlanQuotaExceeded`, con su propio `type` RFC 7807 y el límite alcanzado en el cuerpo, para que el frontend pueda decir *"llegaste a 80 de 80 vehículos de Starter"* sin adivinar.

## D-7 — Qué cuenta `PlanLimitsService`, y qué no

Los tres `assert_can_add_*` cuentan **filas vivas**, no filas históricas:

- `assert_can_add_user` → usuarios con `deleted_at IS NULL`. Un usuario desactivado (`status = inactive`) **sí cuenta**: sigue ocupando una licencia y puede reactivarse sin fricción. Un usuario borrado, no.
- `assert_can_add_vehicle` → vehículos en stock con `deleted_at IS NULL`. El límite es *"vehículos en stock simultáneo"* (spec §3.3), no vehículos vendidos en la historia. **Vender no debe consumir cuota**, o el plan se agota solo con el tiempo y el cliente no entiende por qué.
- `assert_can_add_branch` → sucursales con `deleted_at IS NULL`, sin mirar `is_active`. Una sucursal cerrada por refacción sigue existiendo.

**El conteo va contra la base, no contra un contador cacheado.** Un contador denormalizado se desincroniza y falla del lado peligroso: deja crear de más. Si el `COUNT` llega a pesar, se resuelve con índice — es un problema de rendimiento, y el otro es un problema de facturación.

> ⚠️ **Límite conocido de esta implementación: la condición de carrera.** Dos altas simultáneas con 79 de 80 vehículos pueden pasar las dos verificaciones y dejar 81. Cerrarlo de verdad exige un bloqueo sobre la fila del tenant o una constraint de exclusión, y las dos cosas cuestan latencia en el camino caliente de **toda** creación del sistema.
>
> **Se asume, con el número a la vista**: el desborde máximo es la cantidad de altas concurrentes, sobre planes cuyo límite se mide en decenas o centenas. No se disimula — `assert_can_add_vehicle` deja el hueco documentado en su docstring, y el día que un tenant Enterprise cargue por API en paralelo, el arreglo es un `SELECT ... FOR UPDATE` sobre `tenants` y está identificado de antemano.

## D-8 — Orden de las migraciones y compatibilidad hacia atrás

Cinco migraciones, en este orden, encadenadas desde `003`:

| Rev | Qué crea | Por qué va acá |
|---|---|---|
| `004` | Extensión PostGIS | `branches.geo_point` no compila sin el tipo |
| `005` | `plans` + seed | `tenants.plan_id` la referencia |
| `006` | `tenant_status_enum` + `tenants` | Raíz de todo lo demás |
| `007` | `branches` + RLS + `FORCE` | Necesita `tenants` |
| `008` | `subscription_status_enum` + `subscriptions` + RLS + `FORCE` | Necesita `tenants` y `plans` |

**Las cinco son puramente aditivas**: crean tipos, tablas, índices y políticas, y no tocan nada existente. No hay renombre, ni borrado, ni `SET NOT NULL` sobre columna preexistente, ni constraint nueva sobre datos viejos. Por lo tanto la versión inmediatamente anterior de la aplicación sigue funcionando contra el esquema nuevo, que es lo que exige la **regla dura 13** — y lo verifica el job `migraciones-compatibles` de CI, no la palabra de este documento.

**`tenants.plan_id` nace `NULL`** aunque conceptualmente todo tenant tiene plan. La ficha de C-04 lo llamaba *"FK temporal NULL hasta T-019"*, y en este change `plans` se crea **antes**, así que la FK apunta desde el primer día. Se conserva nullable igual por una razón que sobrevive al orden de las migraciones: un tenant en `status = 'trial'` todavía no eligió plan, y forzar un plan ficticio para satisfacer un `NOT NULL` es peor que un `NULL` que dice la verdad.

## D-10 — Los schemas de entrada **rechazan** el campo de más, no lo ignoran

La regla dura 1 dice que `tenant_id` se deriva del token y nunca del body. Hay dos formas de cumplirla y **no son equivalentes**:

| Configuración | Qué pasa con `tenant_id` en el body | Qué ve el atacante |
|---|---|---|
| `extra="ignore"` (default de Pydantic) | Se descarta en silencio | **200 OK** |
| `extra="forbid"` | La petición se rechaza | **422**, con el nombre del campo |

Se elige **`forbid`**. Ignorar en silencio *cumple* la regla —el valor nunca llega a la base— pero le devuelve un 200 a un cliente que acaba de intentar escribir en otro tenant, y no deja rastro de que lo intentó. Con `forbid` el intento queda en el log.

**El beneficio de arrastre pesa igual.** `forbid` atrapa los errores de tipeo: un `billing_emial` con `ignore` se descarta sin decir nada y la agencia queda sin email de facturación, con la petición en verde. Ese es el modo de fallar silencioso que más veces aparece en la práctica — bastante más que el ataque.

Además de prohibir el extra, **`tenant_id` no está declarado** en ningún schema de entrada. Las dos cosas, porque protegen de cosas distintas: no declararlo evita que se aplique, prohibir el extra hace que el intento sea visible. Hay un test que fija que el campo no exista en `model_fields`, para que los otros dos no puedan pasar por el motivo equivocado.

> Esto se desvía de cómo estaba redactada la tarea `4.4` (*"lo ignora, no lo aplica"*). El cambio es hacia **más estricto**, y se registra acá porque por el Principio 5 una decisión implícita no es vinculante.

## D-11 — `billing_email` se valida por forma, sin dependencia nueva

`EmailStr` de Pydantic arrastra `email-validator`, que sería la **primera dependencia del proyecto agregada solo para un campo**. Lo que compra es conformidad con RFC 5322 — y eso no es lo que hace falta.

**Una dirección puede ser perfectamente válida según el RFC y no existir, rebotar, o ser de otra persona.** Una dirección de facturación se verifica **mandando un mail** y esperando confirmación; ese paso vive en el onboarding (C-10) y es el único que prueba algo. Acá alcanza con frenar la basura evidente: sin arroba, sin dominio, sin punto en el dominio, con espacios.

Es el mismo criterio que `D-4` aplicó a `geoalchemy2`: una dependencia entra cuando hay un motivo concreto, no por costumbre. Si más adelante hace falta RFC de verdad, entra con ese motivo escrito.

## D-9 — El validador de CUIT vive en `core`, no en `tenancy`

`tenants.cuit` es el primer uso, pero no el último: `contacts` (C-24) y las operaciones de venta lo van a necesitar. Va en `app/core/validadores_ar.py`.

Valida **dígito verificador módulo 11** con la serie de multiplicadores `5 4 3 2 7 6 5 4 3 2`, y acepta el CUIT con o sin guiones normalizando a la forma canónica `XX-XXXXXXXX-X` que la columna `varchar(13)` espera.

**Rechaza el prefijo inválido.** Un CUIT bien formado con dígito correcto pero prefijo `99` no corresponde a ninguna categoría de AFIP. Los válidos son `20`, `23`, `24`, `27` (persona física), `30`, `33`, `34` (persona jurídica). Validar solo el dígito deja pasar números que ningún organismo va a reconocer, y el error aparece meses después, en la factura.
