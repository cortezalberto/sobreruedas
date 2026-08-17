# C-02 · `core-backend-primitives`

## Why

C-01 dejó una aplicación que arranca, se configura sola y se sabe sana — pero **no tiene dónde apoyar un solo endpoint de negocio**. `backend/app/modules/` son 16 carpetas vacías, y van a seguir vacías hasta que exista el piso común: cómo se aísla un tenant, cómo se identifica quien llama, cómo se pagina, cómo se responde un error y cómo viaja un evento entre módulos.

Ese piso no se puede improvisar por módulo. Si cada uno resuelve el aislamiento a su manera, la promesa de las tres capas simultáneas (`tenant_id` en la query + política RLS + contexto de sesión) se cumple en el módulo que se acordó y se rompe en el que no — y `RN-MT-07` es explícito en que una filtración entre tenants **no es un bug ordinario, es un incidente P0** con notificación a la AAIP.

Este change escribe ese piso una sola vez, con tests que lo prueban, antes de que exista el primer módulo que pueda hacerlo mal.

## What Changes

- **Contexto de tenant por request** — `db/session.py` emite `SET LOCAL app.current_tenant` en la transacción de cada request, con el UUID tomado **exclusivamente del claim del JWT**. Es el mecanismo sobre el que se apoya toda la RLS del sistema (ADR-006, `RN-MT-02`).
- **Migración de extensiones de PostgreSQL** — `uuid-ossp`, `pg_trgm`, `unaccent`, `btree_gin`, verificadas por migración y no solo por el script de arranque local.
- **Identificación de quien llama** — `core/auth.py` con la dependency `get_current_user`: valida el JWT de Keycloak contra el JWKS del realm (RS256) y extrae `tenant_id` y rol.
- **Autorización** — `core/rbac.py` con `require_role(...)` y `require_permission(...)`. ⚠️ **Enumera literalmente el catálogo de roles, y ese catálogo depende de una enmienda constitucional todavía en discusión** — ver *Bloqueantes*.
- **Convenciones de API** — paginación por cursor, idempotencia por header `Idempotency-Key` (TTL 24 h; misma clave + payload distinto ⇒ **409**), y completar el contrato de errores que C-01 dejó a medias.
- **Bus de eventos de dominio** — `core/events.py`: publisher y consumer base sobre Redis Streams con el sobre canónico (`event_id`, `event_type`, `event_version`, `tenant_id`, `occurred_at`, `data`), backoff exponencial y dead-letter stream.
- **Andamiaje de tests** — fixtures comunes y factories `factory_boy`, para que los tests de aislamiento de los 16 módulos no empiecen cada uno de cero.

### Lo que este change corrige de lo ya escrito

- **`core/errors.py` ya existe** (lo creó T-005 en C-01) y le falta parte del contrato: el array `errors[]` emite `field` y `message` pero **no `code`**, que las convenciones de API exigen. Este change lo completa; no lo reescribe.
- **El nombre del parámetro de sesión está en disputa.** La ficha de C-02 en `CHANGES.md` dice `app.current_tenant_id`; el corpus vinculante dice `app.current_tenant` — cita textual del plan de seguridad, `RN-MT-02`, `RN-MT-06` y la regla dura 1 del proyecto. **Se adopta `app.current_tenant`** y se corrige la ficha del roadmap. Un parámetro mal nombrado no falla ruidosamente: `current_setting()` devuelve vacío y las queries dejan de traer filas, que es indistinguible de "no hay datos".

## Capabilities

### New Capabilities

- `platform/tenant-isolation`: el contexto de tenant por request y su contrato con RLS — de dónde sale el `tenant_id`, cuándo se setea, qué pasa si falta, y qué se garantiza entre requests concurrentes.
- `platform/api-conventions`: forma observable de toda respuesta de la API — errores RFC 7807, paginación por cursor e idempotencia de las creaciones.
- `platform/identity`: validación del token de Keycloak y derivación del sujeto que hace la petición.
- `platform/authorization`: verificación de rol y permiso en el backend. **Se especifica en este change; su implementación queda condicionada a `E-001`.**
- `platform/domain-events`: publicación y consumo de eventos de dominio, incluido el comportamiento ante fallo repetido.

### Modified Capabilities

Ninguna. Las tres capabilities de C-01 (`platform/service-health`, `platform/configuration`, `platform/delivery-pipeline`) no cambian de requisitos. El retoque de `core/errors.py` completa un contrato que **ninguna spec de C-01 declaraba**, así que entra como requisito nuevo de `platform/api-conventions`, no como modificación.

## Impact

**Código nuevo**: `backend/app/db/session.py`, `backend/app/core/{auth,rbac,pagination,idempotency,events}.py`, `backend/alembic/versions/001_*.py`, `backend/tests/factories/`.

**Código tocado**: `backend/app/core/errors.py` (agrega `code` por campo), `backend/app/main.py` (registra las dependencies nuevas), `backend/tests/conftest.py` (fixtures comunes).

**Dependencias nuevas**: validación de JWT contra JWKS, `factory_boy`. Redis ya está en el stack desde C-01.

**Lo que NO entra**: ninguna tabla de negocio, ninguna migración de `users` (es C-05), ningún endpoint de dominio. Este change produce primitivas, no funcionalidad visible.

### Bloqueantes

| Bloqueante | Estado | Qué frena |
|---|---|---|
| `IN-01` catálogo de roles | Decidido por `ADR-017` — **condicionado** | `core/rbac.py` |
| `IN-02` representación de `super_admin` | Decidido por `ADR-017` — **condicionado** | `core/rbac.py`, migración de `users` (C-05) |
| `E-001` enmienda al glosario | 🟡 **EN DISCUSIÓN**, cierre mínimo **20-ago-2026** | ratifica lo anterior |

`ADR-017` está aceptado *condicionado a que se ratifique `E-001`*, que hoy está en el paso (b) del Artículo 8 y todavía le faltan los pasos (c) aprobación, (d) registro y (e) comunicación. Por la **regla dura 12** no se implementa sobre un bloqueante sin resolver.

**Alcance de la traba: una de las nueve tareas.** El contexto de tenant, las extensiones, la identidad, las convenciones de API, los eventos y las factories no dependen del catálogo de roles. `platform/authorization` se especifica ahora —para que la ratificación no encuentre una hoja en blanco— y se implementa después.

### Riesgo cerrado

~~**`R-2` — no existe matriz RBAC canónica.**~~ ✅ **Cerrado el 17-ago-2026 por [`ADR-024`](../../../docs/adr/ADR-024-matriz-rbac-canonica.md).**

`require_permission()` ya tiene contra qué construirse: el ADR fija la forma del permiso (`recurso:acción` + alcance `all`/`own` + conjunto de campos), el criterio de **denegar por defecto**, la **ausencia de herencia** entre roles (`S3`) y las celdas de siete módulos. La **definición ejecutable de este change debe ser la traducción literal de esas tablas.**

Dos consecuencias del ADR que caen sobre este change:

1. **La restricción de campos aplica también en lectura**, no solo en escritura — `RN-ST-12` lo obliga. La spec de `platform/authorization` solo cubría escritura; se le agrega el requisito faltante.
2. **`E-001` sigue siendo el bloqueante.** `ADR-024` **hereda su condicionalidad**: si la enmienda se rechaza el 20-ago-2026, el catálogo de roles cambia y la matriz se revisa. La regla dura 12 sigue vigente sobre el bloque 6.
