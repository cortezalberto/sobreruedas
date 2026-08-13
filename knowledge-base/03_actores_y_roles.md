# Actores y Roles

> Fuentes: `deRuedas-constitucion.md`, `deRuedas-spec-tecnica.md`, `deRuedas-plan-implementacion.md`, `deRuedas-plan-seguridad.md`, `deRuedas-plan-testing.md`, `deRuedas-historias-usuario.md`, `deRuedas-manual-usuario.md`, `deRuedas-plan-gtm.md`.

## ⚠️ Advertencia previa: el catálogo de roles NO es consistente en el corpus

Este es uno de los puntos **bloqueantes** de la base documental. Cuatro versiones distintas conviven:

| Fuente | Catálogo declarado |
|---|---|
| `constitucion.md` (glosario, vinculante) | **Gerente, Vendedor, Administrativo** (3, en español) |
| `spec-tecnica.md` §3.3 (`user_role_enum`) | **`manager`, `salesperson`, `admin_staff`** (3, en inglés — **sin `super_admin`**) |
| `spec-tecnica.md` §8.4 | **Gerente, Vendedor, Administrativo** (3, en español) |
| `spec-tecnica.md` §4.1.3 y §4.2.11 | Menciona el **rol Super Admin** con endpoints `/admin/api/v1` |
| `plan-implementacion.md`, `plan-seguridad.md`, `plan-testing.md` | **`super_admin`, `manager`, `salesperson`, `admin_staff`** (4, catálogo "canónico") |
| `historias-usuario.md` | 5 *personas*: P1 Gerente, P2 Vendedor, P3 Administrativo, P4 Customer Success Manager, P5 Super Admin |
| `manual-usuario.md` | Solo `manager`, `salesperson`, `admin_staff` (es el manual del cliente) |

Ver `IN-01` y `IN-02` en [10_preguntas_abiertas.md](10_preguntas_abiertas.md). **No se puede implementar `users.role` sin resolver esto.**

Interpretación de trabajo adoptada en esta KB (a confirmar): existen **4 roles**, de los cuales 3 son roles *dentro del tenant* y 1 es un rol *de la plataforma*. La equivalencia con el español de la constitución es: Gerente = `manager`, Vendedor = `salesperson`, Administrativo = `admin_staff`.

## Actores del sistema

| Actor | Rol técnico | Descripción | Cómo interactúa |
|---|---|---|---|
| **Gerente / dueño de agencia** | `manager` | Rol de máximo acceso *dentro del tenant*. Típicamente el dueño o el gerente comercial. Persona GTM: "Eduardo" (45-58 años, decisor final) y "Marcos" (35-48, gerente de mini-red). | Web + móvil. Configura todo, ve todo, decide sobre datos. |
| **Vendedor** | `salesperson` | Opera el día a día comercial. Persona GTM: "Carla" (25-50, tiene veto de facto sobre la adopción). | Principalmente móvil y WhatsApp. Ve **solo sus** leads. |
| **Administrativo/a** | `admin_staff` | Documentación, cobranza, conciliación, reportes. Persona GTM: "Ana" (30-55). | Web. Acceso pleno a reportes, exports y documentación; **no** cierra ventas ni configura. |
| **Customer Success (deRuedas)** | usa `super_admin` en el backoffice | Personal interno de deRuedas. Onboarding, soporte, prevención de churn. **No es un rol de sistema separado.** | Backoffice `/admin`. |
| **Super Admin (deRuedas)** | `super_admin` | Personal interno de deRuedas con privilegios de plataforma. Alta/suspensión de tenants, planes, feature flags, financieras, catálogos canónicos. | Backoffice `/admin/api/v1`. Único rol con acceso cross-tenant. |
| **Comprador final** | (sin cuenta) | Actor externo. No accede al sistema. | Indirectamente vía WhatsApp y formularios del portal. |
| **Sistemas externos** | (service account) | Portal deRuedas, WhatsApp Cloud API, financieras, Mercado Pago. | Webhooks entrantes con HMAC + API keys cifradas por tenant. |

## RBAC — Matriz de permisos

⚠️ **No existe en el corpus una matriz RBAC canónica y completa.** El plan de seguridad lo dice explícitamente. Lo que sigue está **reconstruido** cruzando la tabla del manual de usuario (§2.4) con los permisos declarados ficha por ficha en el plan de implementación. Cualquier celda es candidata a revisión.

### Vista funcional (derivada del manual de usuario)

| Acción | `manager` | `salesperson` | `admin_staff` | `super_admin` |
|---|:---:|:---:|:---:|:---:|
| Ver dashboard ejecutivo | ✅ | ❌ (solo el propio) | ✅ | ✅ (cross-tenant) |
| Cargar y editar vehículos | ✅ | ⚠️ limitado | ✅ | — |
| Ver precio de costo / margen | ✅ | ❌ | ✅ | — |
| Ver leads de toda la agencia | ✅ | ❌ (solo los propios) | ✅ (lectura) | — |
| Crear y editar leads | ✅ | ✅ | ✅ | — |
| Marcar venta como ganada | ✅ | ✅ (los propios) | ❌ | — |
| Reasignar leads entre vendedores | ✅ | ❌ | ❌ | — |
| Configurar pipeline y reglas | ✅ | ❌ | ❌ | — |
| Crear / editar usuarios | ✅ | ❌ | ❌ | — |
| Configurar integraciones (WhatsApp, portal) | ✅ | ❌ | ❌ | — |
| Gestionar sucursales | ✅ | ❌ | ❌ | — |
| Ver reportes ejecutivos | ✅ | ❌ | ✅ | — |
| Generar exports de datos | ✅ | ❌ | ✅ | — |
| Cambiar el plan contratado | ✅ | ❌ | ❌ | ✅ |
| Gestión documental | ✅ | ⚠️ parcial | ✅ | — |
| Alta / suspensión de tenants | ❌ | ❌ | ❌ | ✅ |
| Gestionar planes y precios | ❌ | ❌ | ❌ | ✅ |
| Impersonar un tenant | ❌ | ❌ | ❌ | ✅ (auditado) |
| Editar catálogos canónicos (marcas/modelos) | ❌ | ❌ | ❌ | ✅ |
| Administrar feature flags | ❌ | ❌ | ❌ | ✅ |

### Vista por recurso (derivada del plan de implementación)

| Recurso / acción | Roles autorizados |
|---|---|
| `POST /vehicles` | `manager`, `admin_staff` |
| `PATCH /vehicles/{id}` | `manager`, `admin_staff`; `salesperson` solo `internal_notes` y auto-asignación |
| `POST /vehicles/{id}/status` | `manager`; `salesperson` transición limitada (`available`→`reserved`, si está asignado) |
| `DELETE /vehicles/{id}` (archivar) | `manager` |
| `POST /vehicles/{id}/photos` | `manager`, `admin_staff`, `salesperson` asignado |
| Borrar / reordenar fotos | `manager`, `admin_staff` |
| `POST /vehicles/import` | `manager`, `admin_staff` |
| `POST /vehicles/{id}/publications/republish` | `manager`, `admin_staff` |
| Contactos (lectura/escritura) | `manager`, `admin_staff`, `salesperson` (solo asignados) |
| `POST /contacts/merge` | `manager`, `admin_staff` |
| Pipeline stages (escritura) | `manager` |
| Leads | `manager` (todo), `salesperson` (solo asignados), `admin_staff` (lectura de todo) |
| Loss reasons (escritura) | `manager` |
| Dashboard CRM | `manager`, `admin_staff` (todo); `salesperson` (solo su data) |
| Conversaciones | `salesperson` (asignadas), `manager` y `admin_staff` (todas) |
| WhatsApp templates | `manager`, `admin_staff` |
| Branches (CRUD) | `manager` |
| Users (invitar / editar / desactivar) | `manager`; el propio usuario puede editar campos no privilegiados |
| Integraciones (settings) | `manager` |
| `/admin/api/v1/*` | `super_admin` exclusivamente |

## Cómo se aplica la autorización

Regla vinculante de la constitución (Artículo 3): **la autorización se verifica siempre en el backend, nunca solo en el frontend.**

Mecanismos concretos:

- `require_role(*roles)` — dependency factory de FastAPI. Devuelve **403** si el rol no matchea.
- `require_permission(perm)` — permisos finos por módulo, para casos como "`salesperson` puede leer todos los vehículos del tenant pero solo editar `internal_notes` y `assigned_user_id`".
- `@audit_action(action_name)` — decorador obligatorio en endpoints sensibles; escribe en `audit_logs`.
- El frontend **solo oculta UI** por UX; no es una defensa.
- La definición canónica de permisos vive en el módulo `auth` y se exporta como diccionario consultable.
- Tests de autorización recorren los 4 roles contra cada endpoint (introspección del router de FastAPI) verificando 200/403 exacto. **Bloqueantes en CI.**

## Reglas estructurales de identidad

- **Un usuario pertenece a exactamente un tenant.** No hay usuarios cross-tenant (excepto `super_admin`, que opera en un plano distinto).
- Un usuario tiene **un** rol.
- Un usuario puede estar asignado a **una o más sucursales** del tenant (tabla `user_branches`, con flag `is_primary`).
- Unicidad de email: `UNIQUE (tenant_id, lower(email)) WHERE deleted_at IS NULL` — case-insensitive, **dentro del tenant**. El mismo email puede existir en dos tenants distintos.
- Estados de usuario: `active | inactive | invited | suspended`.
- Desactivar un usuario le quita el acceso inmediatamente; sus leads y operaciones quedan disponibles para reasignar.
- Las invitaciones caducan a los **7 días**.
- No hay signup público en el MVP: las cuentas se crean por invitación. ⚠️ Contradicho por el plan GTM (`IN-14`).

## Rutas públicas (sin autenticación)

- `POST /webhooks/whatsapp` y `GET /webhooks/whatsapp` (verificación de Meta) — protegido por **HMAC**, no por JWT.
- `POST /webhooks/finance/{partner}` — protegido por HMAC.
- `POST /api/v1/auth/login`, `/auth/refresh`, `/auth/forgot-password`, `/auth/reset-password`.
- `POST /api/v1/users/accept-invitation` (público con token de invitación). ⚠️ El plan de implementación declara **dos paths distintos** para esta misma acción (`/api/v1/users/accept-invitation` vs `/auth/accept-invitation`) — ver `IN-12`.
- `GET /health`, `/health/live`, `/ready`, `/metrics` (endpoints de infraestructura).
- Landing pública del SaaS y simulador público de crédito (Fase 5) — SSR con Next.js.

**Todo el resto de la API requiere JWT válido.**
