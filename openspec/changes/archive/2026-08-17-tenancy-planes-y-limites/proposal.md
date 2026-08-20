# C-04 · `tenancy-planes-y-limites`

## Why

C-02 dejó el mecanismo de aislamiento multi-tenant funcionando y probado — pero **sobre una tabla testigo**. `platform_probe` existe únicamente para que los catorce escenarios de `platform/tenant-isolation` tengan contra qué correr. No hay todavía una sola fila que represente a una agencia real.

Eso convierte a `tenants` en la primera tabla de negocio del sistema, y en la más cara de equivocar: **toda otra tabla del producto la referencia por `tenant_id`**. Un error en su forma no se corrige con una migración, se corrige con treinta y cinco.

Y hay un segundo motivo, menos obvio. El producto es un SaaS con planes, y los límites de esos planes (*"hasta 80 vehículos"*, *"hasta 5 usuarios"*) no son texto de una landing: son una **verificación en el camino caliente** de cada alta de vehículo y de cada invitación de usuario. Si esa verificación llega después de que existan los módulos que debe frenar, llega tarde — hay que agregarla a mano en cada punto de creación, y el que se olvide no falla, simplemente deja pasar.

Este change escribe la entidad raíz y el guardián de los límites **antes** de que exista el primer módulo de negocio que los necesite.

## What Changes

- **`plans`** — catálogo comercial compartido cross-tenant. Se seedea con los tres planes vigentes, sus límites y los módulos habilitados.
- **`tenants`** — la agencia. Identidad (`slug`, `cuit` con dígito verificador validado), estado del ciclo comercial, plan vigente, preferencias regionales y **soft delete**.
- **`branches`** — sucursales del tenant, con `tenant_id`, política RLS y `FORCE`. Las agencias mono-sucursal tienen una sola fila.
- **`subscriptions`** — histórico de suscripción a planes, con `tenant_id` y RLS. Una vigente por tenant.
- **Módulo `tenancy`** — `models`, `schemas`, `repository` y `service`. **Sin `router.py`**: los endpoints son C-05.
- **`PlanLimitsService`** — `assert_can_add_user`, `assert_can_add_vehicle`, `assert_can_add_branch`. Rechaza con una respuesta RFC 7807 distinguible de un error de permisos.
- **Validador de CUIT argentino** — dígito verificador módulo 11, reutilizable por el resto del producto.

### Decisiones que este change cierra

| Bloqueante | Resolución | Detalle |
|---|---|---|
| **`IN-03`** límites por plan | Los de **`plan-gtm`** | Decisión de Dirección, 17-ago-2026. Ver `D-2`. |
| **`IN-04`** moneda de facturación | Se conserva **`price_ars`** | Decisión de Dirección, 17-ago-2026. Ver `D-3`. |

## Capabilities

### New Capabilities

- `tenancy/organization`: la identidad de la agencia y sus sucursales — unicidad de `slug` y `cuit`, validación del dígito verificador, ciclo de estados, soft delete, y el aislamiento de las sucursales entre tenants.
- `tenancy/plan-limits`: el catálogo de planes y la verificación de cuotas — qué se cuenta, qué no se cuenta, y cómo se distingue un rechazo por límite de plan de un rechazo por permisos.

### Modified Capabilities

Ninguna. `platform/tenant-isolation` no cambia de requisitos: `branches` y `subscriptions` son las primeras tablas de negocio que **se someten** a un contrato que ya existe, y el test introspectivo que recorre `pg_policies` las alcanza sin tocarlo.

## Impact

**Código nuevo**: `backend/app/modules/tenancy/{models,schemas,repository,service,limits}.py`, `backend/app/core/validadores_ar.py`, cinco migraciones de Alembic, y sus tests.

**Código tocado**: `backend/app/core/errors.py` — suma el error de cuota de plan a la jerarquía. Nada más.

**Lo que NO entra**: ningún endpoint, ninguna tabla `users` (es C-05), ninguna integración con Mercado Pago (la columna `mp_subscription_id` se crea vacía y la consume un change posterior).

### Hallazgos al escribir este change

Tres cosas que el corpus no anticipaba y que se resuelven acá:

1. **PostGIS no está instalado.** `branches.geo_point` es `geography(Point,4326)` y la migración de extensiones de C-02 trae `uuid-ossp`, `pg_trgm`, `unaccent` y `btree_gin` — **no `postgis`**. Está disponible en la imagen (`postgis/postgis:16-3.4-alpine`) pero nunca se creó. Se agrega en una migración propia de este change. Ver `D-4`.
2. **Los precios de `plan-gtm` no son representables.** Se adoptaron sus límites, y ese documento cotiza en **USD**. `price_ars` no puede guardarlos. Ver `D-3`.
3. **`branches` no tiene `deleted_at` en la spec**, y el borrado físico está prohibido por el Principio 3 (N0). Se agrega. Ver `D-5`.

### Bloqueantes

| Bloqueante | Estado | Qué frenaba |
|---|---|---|
| `IN-03` límites por plan | ✅ **Resuelto** — 17-ago-2026 | el seed de `plans` y `PlanLimitsService` |
| `IN-04` moneda de facturación | ✅ **Resuelto** — 17-ago-2026 | la forma de `plans` y `subscriptions` |

**Este change no hereda la traba de `E-001`.** El bloque 6 de C-02 (autorización) sigue esperando la enmienda, pero C-04 no expone endpoints y por lo tanto no invoca `require_role` ni `require_permission`. `PlanLimitsService` decide sobre **cuota**, no sobre permiso — son dos preguntas distintas y este change solo responde la primera.
