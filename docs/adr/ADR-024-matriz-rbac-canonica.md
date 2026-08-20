# ADR-024 — Matriz RBAC canónica

- **Estado**: ✅ **Aceptado**
- **Fecha**: 2026-08-17
- **Decisores**: Diseñador del sistema
- **Resuelve**: `R-2` (no existe matriz RBAC canónica)
- **Depende de**: [`ADR-017`](ADR-017-catalogo-de-roles-y-super-admin.md) (catálogo de roles) — ✅ **aceptado pleno** desde que [`E-001`](E-001-enmienda-glosario-super-admin.md) se ratificó el 20-ago-2026
- **Afecta**: `C-02` bloque 6 (`T-014`, `core/rbac.py`), `C-05` (`T-027`), `C-19`, `knowledge-base/03_actores_y_roles.md` §RBAC
- **Governance**: **CRÍTICO** — define quién puede hacer qué en todo el sistema
- **Enmendado por**: [`ADR-033`](ADR-033-alcance-self-distinto-de-own.md) (20-ago-2026) — el eje *Alcance* de §3 gana un tercer valor, `self`. **§3 y §6 no se leen sin ese documento.**
- **Enmendado por**: [`ADR-034`](ADR-034-transiciones-como-tercer-eje-del-permiso.md) (20-ago-2026) — §3 gana un **tercer eje**, *Transiciones*. Lo usa una sola celda: `POST /vehicles/{id}/status` para `salesperson`.

---

## Contexto

`R-2` está registrado como *"no existe la matriz RBAC canónica"*, con la evidencia de que la KB reconstruyó **dos vistas parciales que no coinciden entre sí**. El diagnóstico es incompleto: el corpus tiene **cuatro** fuentes de permisos, y las dos que la KB no cruzó son las de mayor autoridad.

| Fuente | Qué aporta | Nivel |
|---|---|---|
| Vista funcional ([`03` §RBAC](../../knowledge-base/03_actores_y_roles.md)) | 19 acciones × 4 roles, derivada del **manual de usuario** | **N4 — no normativo** |
| Vista por recurso ([`03` §RBAC](../../knowledge-base/03_actores_y_roles.md)) | 20 recursos, derivada del **plan de implementación** | N2 |
| **Reglas `RN-*`** ([`05`](../../knowledge-base/05_reglas_de_negocio.md)) | `RN-MT-10`, `RN-ST-12`, `RN-ST-15`, `RN-CR-12`, `RN-CR-13`, `RN-FI-04`, `RN-AD-06` | derivadas del corpus vinculante |
| **`S3`** ([`12`](../../knowledge-base/12_seguridad_y_compliance.md)) | *"Roles sin acumulación de permisos"* — restringe la **forma** de la matriz | plan-seguridad, **N3** |

Las dos discrepancias que motivaron `R-2` **no eran empates**: la vista funcional viene del manual de usuario, que `ADR-000` clasifica como **N4, no normativo**. Cuando choca con `RN-CR-12` o con el plan de implementación, pierde por precedencia. No hacía falta decidir; hacía falta aplicar `ADR-000`.

Lo que sí faltaba, y este ADR aporta: la **forma** del permiso, la **semántica del alcance**, y las celdas de los módulos cuyos endpoints ya están decididos.

## Decisión

### 1. Este documento es la fuente única de la matriz

`knowledge-base/03_actores_y_roles.md` §RBAC pasa a ser **material derivado** de este ADR y deja de contener dos vistas en conflicto. La definición ejecutable en `core/rbac.py` es la traducción literal de las tablas de acá, y no puede divergir sin un ADR que la enmiende.

### 2. Son dos matrices disjuntas, no una de cuatro columnas

Este es el error de forma que arrastraban las dos vistas de la KB, y la causa de casi toda la confusión.

```
Espacio de tenant  /api/v1/…        Espacio de plataforma  /admin/api/v1/…
├── manager                          └── super_admin
├── salesperson
└── admin_staff
```

La spec de `platform/authorization` ya lo exige en los dos sentidos: ningún rol de tenant entra al espacio administrativo, y el rol de plataforma **no obtiene acceso cross-tenant fuera de él**. Poner `super_admin` como cuarta columna junto a los roles de tenant sugiere una comparación que el sistema no admite: no hay un solo endpoint donde los cuatro roles compitan.

### 3. Forma del permiso: `recurso:acción` + alcance + campos

Un permiso se identifica con `recurso:acción` en inglés (`leads:assign`, `vehicles:update`). Cada par (rol, permiso) declara:

| Eje | Valores | Significado |
|---|---|---|
| **Alcance** | `all` | Todos los registros del tenant |
| | `own` | Solo los que el sujeto tiene asignados — ver §4 |
| | `self` | Solo el propio sujeto (`recurso.id == sujeto.user_id`) — agregado por [`ADR-033`](ADR-033-alcance-self-distinto-de-own.md) |
| | *(ausente)* | **Denegado.** La ausencia es la denegación; no existe un valor "denegado" explícito |
| **Campos** | conjunto, opcional | Si está presente, la operación se limita a esos campos. Aplica **tanto a escritura como a lectura** |
| **Transiciones** | conjunto de pares `(desde, hasta)`, opcional | Si está presente, la operación se limita a esos cambios de estado — agregado por [`ADR-034`](ADR-034-transiciones-como-tercer-eje-del-permiso.md) |

La restricción de campos **en lectura** no estaba prevista por la spec de `authorization`, que solo describe modificación acotada. `RN-ST-12` la obliga: `acquisition_cost_ars` solo lo ven `manager` y `admin_staff`, sobre un recurso que `salesperson` sí puede leer. Es una omisión de la spec, no de este ADR — se registra en §Consecuencias.

### 4. `own` significa `assigned_user_id`, y nada más

`RN-CR-12` dice que el `salesperson` ve *"sus propios leads"* sin definir "propio". Se adopta la lectura **estricta**:

> Un recurso es `own` de un sujeto si, y solo si, su `assigned_user_id` es igual al `id` del sujeto **en el momento de la petición**.

Consecuencias deliberadas:

- **Crear un recurso no da acceso permanente.** Si al `salesperson` le reasignan un lead que él creó, deja de verlo. Es lo que hace que `RN-CR-13` (*solo el `manager` reasigna*) sirva de algo: si reasignar no quitara el acceso, no sería un control.
- **`user_branches` no participa de la autorización.** La tabla existe y modela la pertenencia N:M a sucursales, pero **no amplía el alcance**. Un `salesperson` no ve los leads de su sucursal por el hecho de compartirla.
- **`own` no existe para `manager` ni `admin_staff`.** Sus alcances son siempre `all` o denegado.

### 5. Denegar por defecto, y sin herencia

- **Denegar por defecto**: un recurso que no aparece en estas tablas está denegado para todos los roles. No hay comodines.
- **Sin herencia** (`S3`): cada celda se enumera. `manager` **no** hereda de `salesperson`. Agregar un permiso a `salesperson` no se lo da a `manager` — y esa es exactamente la trampa que la ausencia de herencia introduce, así que la verificación automática del bloque 6 debe recorrer los tres roles por separado y no asumir contención.

### 6. Matriz — espacio de tenant

Leyenda: `all` · `own` · `—` denegado · `[campos]` restricción de campos · ⚠ celda sin fuente en el corpus, decidida acá.

#### Auth — `/api/v1/auth/*`

| Operación | `manager` | `salesperson` | `admin_staff` |
|---|:--:|:--:|:--:|
| `login`, `refresh`, `forgot-password`, `reset-password` | *ruta pública, sin JWT* | *ruta pública* | *ruta pública* |
| `logout`, `GET /auth/me`, `mfa/enable`, `mfa/verify` | `self` | `self` | `self` |

**Alcance `self`** ([`ADR-033`](ADR-033-alcance-self-distinto-de-own.md)): ningún rol opera la sesión ni la MFA de otro usuario. Estas celdas decían `own`, pero no era el `own` de §4 — la sesión no tiene `assigned_user_id`. La obligatoriedad de MFA para `manager` está en disputa (`IN-17`) y **no es un permiso** — no se decide acá.

#### Tenancy y sucursales

| Operación | `manager` | `salesperson` | `admin_staff` |
|---|:--:|:--:|:--:|
| `GET /tenant/me` | `all` | `all` | `all` |
| `PATCH /tenant/me` | `all` | — | — |
| `POST /tenant/me/complete-onboarding` | `all` | — | — |
| `GET /branches`, `GET /branches/{id}` | `all` | `all` ⚠ | `all` ⚠ |
| `POST /branches`, `PATCH /branches/{id}`, `deactivate` | `all` | — | — |
| **Cambio de plan contratado** | — | — | — |

**Cambio de plan (K-3):** el único endpoint del catálogo es `PATCH /admin/api/v1/tenants/{id}/plan`, que vive en el espacio de plataforma. `RN-MT-10` no admite excepciones, así que **ningún rol de tenant cambia el plan**; se pide por soporte. Esto contradice el autoservicio del plan GTM, que es **N4 y no normativo**. Si Dirección quiere autoservicio, necesita un endpoint nuevo bajo `/api/v1` y su propio ADR — no una excepción a `RN-MT-10`.

⚠ La lectura de sucursales por `salesperson` y `admin_staff` no tiene fuente. Se concede porque sin ella no se puede ni mostrar a qué sucursal pertenece el usuario, y es lectura de datos no sensibles del propio tenant.

#### Usuarios

| Operación | `manager` | `salesperson` | `admin_staff` |
|---|:--:|:--:|:--:|
| `GET /users` | `all` | ⚠ `all` `[id, nombre, rol, sucursales]` | ⚠ `all` `[id, nombre, rol, sucursales]` |
| `POST /users/invite` | `all` | — | — |
| `PATCH /users/{id}` | `all` | `self` `[perfil]` | `self` `[perfil]` |
| `POST /users/{id}/deactivate` | `all` | — | — |
| `POST /users/{id}/branches` | `all` | — | — |

La vista por recurso decía *"el propio usuario puede editar campos no privilegiados"* sin definir el conjunto. Se define acá:

> **`[perfil]`** = `full_name`, `phone`, `avatar_url`, preferencias de notificación.
> **Privilegiados, nunca autoeditables**: `role`, `status`, `tenant_id`, `email`, asignación de sucursales.

`email` queda del lado privilegiado porque es el identificador contra Keycloak (`ADR-007`) y cambiarlo desde la API abriría un camino de escritura sobre la identidad que la regla dura 2 mantiene fuera de la aplicación.

⚠ La lectura del padrón de usuarios por `salesperson` y `admin_staff` no tiene fuente, pero es necesaria para poblar cualquier selector de asignación. Se concede **acotada a campos no sensibles**.

#### Stock

| Operación | `manager` | `salesperson` | `admin_staff` |
|---|:--:|:--:|:--:|
| `GET /vehicles`, `/{id}`, `/search`, `/suggest`, `/{id}/history` | `all` | `all` | `all` |
| ↳ campo `acquisition_cost_ars` | ✅ | **❌ `RN-ST-12`** | ✅ |
| `GET /vehicles/{id}/price-suggestion` | `all` | ⚠ — | `all` |
| `POST /vehicles` | `all` | — | `all` |
| `PATCH /vehicles/{id}` | `all` | `all` `[internal_notes, assigned_user_id]` | `all` |
| `POST /vehicles/{id}/status` | `all` | `own`, solo `available`→`reserved` | — |
| `DELETE /vehicles/{id}` (archivar) | `all` | — | — |
| `POST /vehicles/{id}/photos` | `all` | `own` | `all` |
| `DELETE` foto, `PATCH /photos/order` | `all` | — | `all` |
| `POST /vehicles/import` | `all` | — | `all` |
| `GET /vehicles/import/template`, `GET /imports`, `GET /imports/{id}` | `all` | — | `all` |
| `GET /catalog/*` (marcas, modelos, versiones) | `all` | `all` | `all` |
| Escritura de catálogo | — | — | — |

**Fila agregada el 20-ago-2026.** La plantilla, el listado de corridas y el progreso de una importación se expusieron en `C-17` sin fila en esta matriz — exactamente lo que §8 prohíbe. Las trae la verificación automática del bloque 6 de `C-02`, que recorre las operaciones realmente expuestas. Se les asignan los **mismos actores** que a `POST /vehicles/import`: son facetas de la misma capacidad, no una capacidad nueva. En el código comparten la clave `vehicles:import`.

El catálogo es **cross-tenant y de solo lectura para los tenants**; solo `super_admin` lo edita (`RN-ST-15`). Es la única tabla que los tres roles leen sin que `tenant_id` intervenga, y está en la lista de exentas de RLS.

⚠ `price-suggestion` no tiene fuente. Se deniega a `salesperson` **por alineación con `RN-ST-12`**: una sugerencia de precio expone el margen por diferencia contra el precio publicado, así que concederla anularía la restricción sobre el costo.

`PATCH /vehicles/{id}` para `salesperson` es `all` **con campos acotados**, no `own`: `12_seguridad` es explícito en que lee todos los vehículos del tenant, y la autoasignación (`assigned_user_id`) sería imposible si solo pudiera tocar los que ya tiene.

#### Publishing

| Operación | `manager` | `salesperson` | `admin_staff` |
|---|:--:|:--:|:--:|
| `GET /vehicles/{id}/publications` | `all` | ⚠ `all` | `all` |
| `POST /vehicles/{id}/publications/republish` | `all` | — | `all` |

#### CRM

| Operación | `manager` | `salesperson` | `admin_staff` |
|---|:--:|:--:|:--:|
| `GET /leads`, `GET /leads/{id}`, `/{id}/history` | `all` | `own` | `all` **(lectura)** |
| `POST /leads` | `all` | `all` | ⚠ — |
| `PATCH /leads/{id}` | `all` | `own` | — |
| `POST /leads/{id}/stage` | `all` | `own` | — |
| `POST /leads/{id}/assign` | `all` | — | — |
| `POST /leads/{id}/close` | `all` | `own` | — |
| `GET`/`POST /leads/{lead_id}/activities`, `PATCH /activities/{id}` | `all` | `own` | ⚠ `all` (lectura) |
| `GET`/`POST /contacts`, `GET`/`PATCH /contacts/{id}` | `all` | `own` | `all` |
| `POST /contacts/merge` | `all` | — | `all` |
| `POST /contacts/{id}/forget` | `all` | — | ⚠ — |
| `GET /pipeline/stages`, `GET /loss-reasons` | `all` | `all` | `all` |
| `POST`/`PATCH` pipeline stages, reorder, loss reasons | `all` | — | — |
| `GET /crm/dashboard/*` | `all` | `own` | `all` |

- **`admin_staff` sobre leads es solo lectura** (`RN-CR-12`). La vista funcional le daba escritura; venía del manual de usuario, **N4**. Resuelto por precedencia, no por decisión.
- **Solo `manager` reasigna** (`RN-CR-13`). Es la regla que le da sentido al alcance `own` estricto de §4.
- ⚠ **`admin_staff` no crea leads.** `RN-CR-12` dice "los ve en lectura", que literalmente habla de ver, no de crear. Se opta por lo restrictivo porque denegar de más es reversible y conceder de más no. **Es la fricción más probable de este ADR** — ver §Fricciones.
- ⚠ **`contacts/{id}/forget`** (derecho de supresión, Ley 25.326) queda solo en `manager`: es irreversible sobre datos personales y ninguna fuente lo asigna.
- El contrato de `/leads/{id}/close` está en disputa (`IN-08`: `/close` vs `/won` + `/lost`). El **permiso es el mismo** cualquiera sea la forma que gane; esta celda no depende de `IN-08`.

#### Communication

| Operación | `manager` | `salesperson` | `admin_staff` |
|---|:--:|:--:|:--:|
| `GET`/`POST /conversations`, `GET /conversations/{id}` | `all` | `own` | `all` |
| `GET`/`POST /conversations/{id}/messages` | `all` | `own` | `all` |
| `POST /conversations/{id}/read`, `/close` | `all` | `own` | `all` |
| `POST /conversations/{id}/assign` | `all` | ⚠ — | ⚠ — |
| `GET /conversations/stream` | `all` | `own` | `all` |
| `GET`/`POST /whatsapp/templates`, `POST /templates/sync` | `all` | — | `all` |
| `POST`/`GET /webhooks/whatsapp` | *ruta pública, HMAC* | *ruta pública* | *ruta pública* |

⚠ **Asignar conversación queda solo en `manager`**, por simetría con `RN-CR-13`. Ninguna fuente lo dice, y es una restricción fuerte: una conversación entrante de WhatsApp puede llegar antes de que exista el lead. Ver §Fricciones.

`GET /conversations/stream` hereda el alcance de la lectura: el canal en tiempo real **filtra por el mismo alcance** que el listado. Un `salesperson` no recibe eventos de conversaciones que no tiene asignadas. El transporte está en disputa (`IN-08`, WebSocket vs SSE) y no afecta el permiso.

### 7. Matriz — espacio de plataforma

Un solo rol, `super_admin`, y **todo** `/admin/api/v1/*` le pertenece en exclusiva (`RN-MT-10`). Alta y suspensión de tenants, planes y precios, feature flags, financieras (`RN-FI-04`), catálogos canónicos (`RN-ST-15`), tickets de soporte e impersonación (auditada, `RN-AD-06`).

**K-4 — cómo llega el `super_admin` a los datos de un tenant.**

> Bajo `/admin/api/v1` el `super_admin` ve **solo agregados y salud** (`/tenants/{id}/health`). Para ver datos reales **impersona**, lo que abre una sesión con el `tenant_id` de ese tenant y queda auditada por `RN-AD-06`.

El motivo es acotar la exención de RLS. `ADR-017` dejó `super_admins` fuera de RLS; si además `/admin` leyera datos de negocio directamente, esa exención sería una puerta permanente y ancha en lugar de un rodeo estrecho y trazado. La contrapartida asumida: soporte necesita un paso extra para diagnosticar.

La vista funcional daba al `super_admin` un *"dashboard ejecutivo cross-tenant"*. No existe tal endpoint en el catálogo, y `/tenants/{id}/health` es lo más cercano. **Se descarta como celda de la matriz**: era una expectativa del manual, no un contrato.

### 8. Los módulos no declarados están denegados, y eso es una decisión

Nueve módulos no tienen **ninguna** fuente de permisos en el corpus: `trade-in`, `finance`, `documents`, `accounting`, `operations`, `analytics`, `notifications`, `audit`, y la mayor parte de `publishing`.

Por §5, sus operaciones **quedan denegadas para todos los roles**. La matriz no queda incompleta: queda **cerrada con denegación explícita**. El change que traiga cada módulo debe agregar sus filas acá y no puede exponer un endpoint sin declararlas, porque la verificación automática del bloque 6 lo detecta como operación sin declarar.

Esto es deliberado: escribir hoy las celdas de esos módulos sería fijar permisos sobre endpoints cuyos contratos siguen en disputa (`IN-08`, `IN-12`).

## Fricciones previstas

Celdas que se decidieron por el lado restrictivo sin fuente, y que son las candidatas a que el primer uso real las contradiga. Se listan para que revisarlas sea barato y trazable, no para dejarlas a medias:

| # | Celda | Riesgo |
|---|---|---|
| **F-1** | `admin_staff` no crea leads | Un lead que entra por teléfono lo carga el administrativo. Si pasa, se enmienda con un ADR de una línea. |
| **F-2** | `salesperson` no asigna conversaciones | Una conversación entrante sin dueño queda esperando al `manager`. Puede volverse cuello de botella operativo. |
| **F-3** | `admin_staff` no ejecuta `contacts/forget` | La gestión documental y de datos personales es su trabajo; concentrarlo en `manager` puede no escalar. |
| **F-4** | `salesperson` sin `price-suggestion` | Es quien negocia el precio. La restricción es correcta respecto de `RN-ST-12` pero puede ser contraproducente comercialmente. |
| **F-5** | `own` estricto sin sucursal | En una agencia de varias sucursales, ningún `salesperson` ve el trabajo de un colega ausente. |

## Consecuencias

### A favor

- **`R-2` se cierra** y con él el último riesgo que bloqueaba el bloque 6 de `C-02` y `T-027` de `C-05`.
- **La verificación automática pasa a tener contra qué correr.** El quality gate bloqueante de CI que recorre cada operación expuesta × cada rol necesitaba un esperado; ahora lo tiene.
- **Cada celda es trazable a su fuente o está marcada ⚠.** No hay permisos de origen desconocido.
- **La exención de RLS de `super_admins` queda con la superficie mínima**: solo agregados y salud bajo `/admin`, y datos reales únicamente por impersonación auditada.

### En contra — asumidas

- **La spec de `platform/authorization` queda corta**: describe modificación acotada a campos, pero no **lectura** acotada a campos, que `RN-ST-12` obliga. El delta de `C-02` necesita un requisito más, o un escenario adicional en el existente. Es trabajo que este ADR crea.
- **11 celdas ⚠ sin fuente**, sobre 6 tablas. Todas resueltas por el lado restrictivo, pero son decisiones de este ADR y no derivaciones del corpus.
- **Sin herencia, la matriz es verbosa y se desincroniza fácil.** Se compensa con que la definición ejecutable sea la traducción literal de estas tablas y con la verificación automática.
- **Nueve módulos denegados en bloque** obligan a que cada change futuro vuelva acá. Es fricción deliberada.

## Alternativas consideradas

**Adoptar la vista funcional del manual de usuario tal cual.** Es la única de las cuatro fuentes que ya viene en forma de matriz rol × acción. Descartada porque es **N4 no normativo** y contradice a `RN-CR-12` y al plan de implementación en dos celdas; adoptarla habría invertido la precedencia de `ADR-000`.

**Matriz de cuatro columnas incluyendo `super_admin`.** Es la forma que tenían las dos vistas de la KB. Descartada porque no existe un solo endpoint donde los cuatro roles compitan: la spec de `authorization` prohíbe explícitamente ambos cruces. La tabla sugería comparaciones imposibles y fue el origen de casi toda la confusión de `R-2`.

**Roles jerárquicos (`manager` ⊃ `admin_staff` ⊃ `salesperson`).** Mucho menos verboso y más fácil de mantener. Descartada porque `S3` lo prohíbe explícitamente, y porque la jerarquía es falsa: `salesperson` puede cerrar una venta y `admin_staff` no, así que no hay contención real entre ellos.

**Escribir las celdas de los 16 módulos ahora.** Cerraría `R-2` de una vez. Descartada porque `IN-08` e `IN-12` declaran contratos divergentes sin resolver en CRM, contactos, pipeline y el canal en tiempo real: escribir permisos sobre endpoints cuya forma no está decidida fija por la puerta de atrás una decisión que corresponde a otro proceso.

## Lo que este ADR NO cierra

- **`IN-17`** — obligatoriedad de MFA por rol. Es política de autenticación, no un permiso.
- **Exports y Ley 25.326** — `analytics` está denegado en bloque, así que el problema queda contenido, pero cuando llegue su change hay que decidir auditoría, límite de tasa y alcance de la exportación de datos personales.
- **El inventario completo de permisos de campo.** Solo hay tres en todo el sistema (`acquisition_cost_ars`, `internal_notes`/`assigned_user_id`, `[perfil]` de usuarios). Los módulos con datos sensibles que faltan — `finance`, `documents`, `accounting` — van a sumar los suyos.
- **`E-001`.** Este ADR **hereda su condicionalidad**: si la enmienda se rechaza el 20-ago-2026, el catálogo de roles cambia y esta matriz se revisa.
