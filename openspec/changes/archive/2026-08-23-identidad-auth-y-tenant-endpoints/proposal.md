# C-05 · `identidad-auth-y-tenant-endpoints`

## Why

C-04 dejó la agencia y sus sucursales, pero **no hay una sola persona en el sistema**. Todo lo que C-02 construyó para identificar a quien llama —`get_current_user`, los claims de `ADR-021`, el contexto de tenant— valida hoy tokens de usuarios que no existen en ninguna tabla.

Este change crea esa tabla, y con ella el **primer endpoint de negocio del producto**. Es el punto donde el backend deja de ser infraestructura y empieza a ser API.

Es además el **único serializador duro del proyecto**: en GATE 3 los tres agentes convergen acá y esperan. Lo que se atrase en C-05 atrasa el proyecto entero, uno a uno.

## What Changes

- **`users`** — espejo local del usuario de Keycloak: identidad de negocio, rol, tenant, estado. **Sin credenciales de ninguna clase.**
- **`user_branches`** — asignación N:M de usuarios a sucursales, con sucursal principal.
- **`super_admins`** — el rol de plataforma, en su propia tabla y fuera de todo tenant (`ADR-017`).
- **Módulo `users`** — schemas, repository, service: invitación, aceptación, desactivación, asignación a sucursales.
- **Endpoints** de `users`, de `tenancy` (los de C-04, que quedaron sin router) y los **dos** de `auth` que sobreviven.
- **Realm de Keycloak** configurado, con sincronización del espejo local.
- **Tests críticos de aislamiento multi-tenant** (`T-027`) — quality gate bloqueante del plan de testing.

### Decisiones ya cerradas que este change aplica

| Decisión | Dónde | Qué fija |
|---|---|---|
| [`ADR-026`](../../../../docs/adr/ADR-026-autenticacion-delegada-sin-password-hash.md) | `IN-06`, `IN-12(a)` | sin `password_hash`; login PKCE; 2 de 8 endpoints de `/auth`; path de `accept-invitation` |
| [`ADR-017`](../../../../docs/adr/ADR-017-catalogo-de-roles-y-super-admin.md) | `IN-01`, `IN-02` | `user_role_enum` con **3** valores; `super_admin` en tabla propia |
| [`ADR-021`](../../../../docs/adr/ADR-021-claims-de-tenant-y-rol.md) | — | `tenant_id` y `role` como claims planos |
| [`ADR-024`](../../../../docs/adr/ADR-024-matriz-rbac-canonica.md) | `R-2` | las celdas de permisos de `users`, `branches` y `tenant` |

**No se re-deciden. Se aplican.**

## Capabilities

### New Capabilities

- `identity/user-management`: el ciclo de vida de una persona dentro de una agencia — invitación, aceptación, desactivación, reasignación de sucursales — y qué se conserva cuando alguien deja de trabajar ahí.
- `identity/session`: qué puede saber de sí mismo quien presenta un token válido, y qué significa cerrar sesión cuando la sesión no vive en nuestro sistema.

### Modified Capabilities

- `tenancy/organization`: gana los requisitos de **exposición HTTP** que C-04 no podía escribir por no tener endpoints. Los requisitos de dominio no cambian.

## Impact

**Código nuevo**: `backend/app/modules/users/*`, `backend/app/modules/tenancy/router.py`, `backend/app/modules/auth/router.py`, tres migraciones, `infra/keycloak/realm-deruedas.json`.

**Código tocado**: `app/main.py` (registra los routers), `app/modules/tenancy/limits.py` (registra el contador de usuarios).

**Lo que NO entra**: ningún endpoint del espacio `/admin/api/v1` (es C-09), ninguna pantalla (C-08), ningún módulo de negocio.

### Bloqueantes

| Bloqueante | Estado |
|---|---|
| `IN-06` · `password_hash` y forma del login | ✅ **Resuelto** por `ADR-026` |
| `IN-12(a)` · path de `accept-invitation` | ✅ **Resuelto** por `ADR-026` §4 |
| **`E-001`** · enmienda del glosario | 🟡 **EN DISCUSIÓN** — cierre mínimo **20-ago-2026** |

> ⛔ **`E-001` bloquea la mitad de este change, y lo dice literalmente.** Su ficha declara: *"**Bloquea**: `C-02` (`core/rbac.py`, T-014), `R-2` (matriz RBAC), **migración inicial de `users`**"*.
>
> El motivo es concreto: `ADR-017` fija los tres valores de `user_role_enum` y está *"Aceptado **condicionado** a la ratificación de `E-001`"*. Si la enmienda se rechaza el 20-ago, el catálogo cambia — y **quitar un valor de un enum es una migración destructiva**, prohibida en un paso por la regla dura 13. Escribirla antes es apostar a que el resultado ya se conoce.
>
> Por la **regla dura 12**, este change se especifica ahora y se implementa después.

**Alcance de la traba — nueve de las diez tareas.** No es que "casi todo se pueda hacer igual": `users`, `user_branches` y `super_admins` llevan el enum; el módulo `users` opera sobre esas tablas; los endpoints necesitan `require_role`, que es el bloque 6 de C-02 y espera la misma enmienda; y el realm de Keycloak declara los roles del catálogo.

**Lo único genuinamente libre es el contrato**: las dos delta specs y el diseño. Por eso este change entrega hoy la especificación completa y ninguna línea de código — de modo que el 20-ago la implementación sea una sola pasada contra un contrato ya revisado, y no un arranque desde cero con el proyecto entero esperando.

### Hallazgo al escribir el diseño

**`mfa_secret` es el segundo `password_hash`, y nadie lo había marcado.** `spec-tecnica` §3.3 le da a `users` una columna `mfa_secret varchar(255)` — *"cifrado simétricamente con KMS"*. Es una credencial, y el mismo razonamiento de `ADR-026` la excluye: `plan-seguridad` §112 asigna a Keycloak *"provee auth e MFA opcional"* y *"custodia sus credenciales"*, y `ADR-026` ya retiró los endpoints `/auth/mfa/*` porque el TOTP es de Keycloak. Guardar el secreto TOTP en nuestra base sería exactamente el error que `IN-06` documentó para las contraseñas. Ver `D-2`.
