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

✅ **`IN-01` e `IN-02` están decididos** por [`ADR-017`](../docs/adr/ADR-017-catalogo-de-roles-y-super-admin.md), **condicionado a la ratificación de [`E-001`](../docs/adr/E-001-enmienda-glosario-super-admin.md)** (cierre de discusión: 20-ago-2026). La tabla de arriba queda como registro de la discrepancia original.

**Catálogo vigente**: **4 roles en el sistema, 3 en `user_role_enum`.** Los tres roles *de tenant* viven en `users`; `super_admin` es un rol *de plataforma* y vive en su propia tabla `super_admins`, sin `tenant_id` y exenta de RLS. `users.tenant_id` sigue **`NOT NULL` sin excepciones**.

Equivalencia con el español de la constitución: Gerente = `manager`, Vendedor = `salesperson`, Administrativo = `admin_staff`. Los identificadores en código son en inglés; la interfaz muestra los términos en español del glosario.

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

> ✅ **La matriz canónica vive en [`ADR-024`](../docs/adr/ADR-024-matriz-rbac-canonica.md)**, que cierra el riesgo `R-2`. Esta sección es **material derivado**: resume la forma y remite al ADR para las celdas. Ante cualquier diferencia, **gana el ADR**.

Hasta el 17-ago-2026 esta sección contenía **dos vistas parciales en conflicto** —una funcional derivada del manual de usuario, otra por recurso derivada del plan de implementación—. `ADR-024` las reconcilió y encontró que **no eran un empate**: la vista funcional venía del manual de usuario, que [`ADR-000`](../docs/adr/ADR-000-precedencia-documental.md) clasifica como **N4, no normativo**. Donde chocaba con `RN-CR-12` o con el plan de implementación, perdía por precedencia.

El ADR también incorporó **dos fuentes que ninguna de las dos vistas había cruzado**: las reglas `RN-*` de [05_reglas_de_negocio.md](05_reglas_de_negocio.md) (`RN-MT-10`, `RN-ST-12`, `RN-ST-15`, `RN-CR-12`, `RN-CR-13`, `RN-FI-04`, `RN-AD-06`) y el principio **`S3`** del plan de seguridad (N3), que **prohíbe la herencia entre roles**.

### Forma de la matriz

**Son dos matrices disjuntas, no una de cuatro columnas.** No existe un solo endpoint donde los cuatro roles compitan: ningún rol de tenant entra al espacio administrativo, y el rol de plataforma no obtiene acceso cross-tenant fuera de él.

```
Espacio de tenant  /api/v1/…        Espacio de plataforma  /admin/api/v1/…
├── manager                          └── super_admin
├── salesperson
└── admin_staff
```

Un permiso se identifica con `recurso:acción` y cada par (rol, permiso) declara un **alcance** y, opcionalmente, un **conjunto de campos**:

| Eje | Valores |
|---|---|
| **Alcance** | `all` (todo el tenant) · `own` (ver abajo) · *ausente* = **denegado** |
| **Campos** | Si está presente, la operación se limita a esos campos — **tanto en escritura como en lectura** |

- **Denegar por defecto**: un recurso que el ADR no declara está denegado para todos. **Nueve de los 16 módulos** están hoy en esa situación, deliberadamente.
- **Sin herencia** (`S3`): `manager` **no** hereda de `salesperson`. Cada celda se enumera.
- **`own` = `assigned_user_id` estricto**: solo lo asignado al sujeto *en el momento de la petición*. Crear un recurso no da acceso permanente, y **`user_branches` no participa de la autorización**.

### Reglas de negocio que la gobiernan

| Regla | Qué fija |
|---|---|
| `RN-MT-10` | Solo `super_admin` opera cross-tenant, y solo bajo `/admin/api/v1`. Sin excepciones — ni siquiera para el cambio de plan. |
| `RN-ST-12` | `acquisition_cost_ars` solo lo ven `manager` y `admin_staff`. Es el caso que obliga a restringir **campos en lectura**. |
| `RN-ST-15` | El catálogo de marcas/modelos/versiones es cross-tenant y de solo lectura para los tenants; solo `super_admin` lo edita. |
| `RN-CR-12` | `salesperson` solo ve y opera sus propios leads; `manager` ve todos; **`admin_staff` los ve en lectura**. |
| `RN-CR-13` | **Solo el `manager` reasigna leads.** Es lo que le da sentido al alcance `own` estricto. |
| `RN-FI-04` | Las financieras las configura exclusivamente el `super_admin`. |
| `RN-AD-06` | La impersonación de un tenant por `super_admin` queda auditada — y es la **única** vía por la que llega a datos reales de un tenant. |

## Cómo se aplica la autorización

Regla vinculante de la constitución (Artículo 3): **la autorización se verifica siempre en el backend, nunca solo en el frontend.**

Mecanismos concretos:

- `require_role(*roles)` — dependency factory de FastAPI. Devuelve **403** si el rol no matchea.
- `require_permission(perm)` — permisos finos por módulo, con **alcance** (`all` / `own`) y **restricción de campos**, para casos como "`salesperson` puede leer todos los vehículos del tenant pero solo editar `internal_notes` y `assigned_user_id`".
- `@audit_action(action_name)` — decorador obligatorio en endpoints sensibles; escribe en `audit_logs`.
- El frontend **solo oculta UI** por UX; no es una defensa.
- La definición canónica de permisos vive en el módulo `auth` y se exporta como diccionario consultable. Es la **traducción literal de las tablas de [`ADR-024`](../docs/adr/ADR-024-matriz-rbac-canonica.md)** y no puede divergir de ellas sin un ADR que las enmiende.
- Tests de autorización por introspección del router de FastAPI, verificando 200/403 exacto. **Bloqueantes en CI.** Recorren los **3 roles de tenant** contra `/api/v1`, y `super_admin` contra `/admin/api/v1` — son dos espacios disjuntos, no una matriz de 4 columnas.
- Una operación que no declara acceso **no autoriza a nadie**, y la inspección automática la reporta como operación sin declarar.

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
