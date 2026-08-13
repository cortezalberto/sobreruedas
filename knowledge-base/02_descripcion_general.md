# Descripción General

> Fuentes: `deRuedas-spec-tecnica.md` (fuente primaria y vinculante), `deRuedas-plan-implementacion.md`, `deRuedas-mejoras-y-saas.md`, `deRuedas-plan-sre.md`, `deRuedas-plan-seguridad.md`.
> Cuando la spec técnica y otro documento discrepan, acá se documenta la spec y la discrepancia queda registrada en [10_preguntas_abiertas.md](10_preguntas_abiertas.md).

## Stack tecnológico

| Capa | Tecnología | Versión mínima declarada | Ancla |
|---|---|---|---|
| Frontend web | Next.js (App Router) + React + TypeScript | **14+** | ADR-004 |
| Frontend móvil | React Native + Expo (Expo Router) | Expo SDK | ADR-005 |
| Backoffice interno | Next.js + React + TypeScript | 14+ | — |
| Backend API | Python + FastAPI | **Python 3.12** | ADR-003 |
| ORM | SQLAlchemy | **2.x** (API moderna, no legacy) | — |
| Validación | Pydantic | **v2** | ADR-003 |
| Migraciones | Alembic | — | — |
| Worker asíncrono | Celery | — | ADR-009 |
| Base de datos | PostgreSQL | **16** (ext.: `pgcrypto`, `pg_trgm`, `postgis`, `uuid-ossp`) | ADR-002 |
| Cache / broker / pub-sub | Redis | **7** (Streams + Pub/Sub) | ADR-009 |
| Búsqueda full-text | OpenSearch | — | ADR-011 |
| Object storage | S3-compatible (S3 / GCS; MinIO en dev) | — | ADR-008 |
| CDN | CloudFront / Cloud CDN | — | — |
| Identidad | Keycloak (OAuth2 + OIDC, JWT RS256) | realm `deruedas` | ADR-007 |
| Auth en frontend | NextAuth / Auth.js como cliente OIDC | — | — |
| Mensajería | WhatsApp Business Cloud API (Meta, directo, sin BSP) | — | ADR-010 |
| Pagos / suscripciones | Mercado Pago (+ Modo/Bind mencionado) | — | — |
| Estilos / UI | Tailwind CSS + Radix UI + Lucide Icons | — | ADR-004 |
| Estado / datos en cliente | TanStack Query; React Hook Form + Zod | — | — |
| Observabilidad | Prometheus + Grafana + Loki + **Jaeger** ⚠️ + OpenTelemetry + Sentry | — | — |
| IaC / CI | Terraform + GitHub Actions + Docker / Docker Compose | — | — |
| Orquestación | Kubernetes ⚠️ (alcance no cerrado) | — | — |
| Feature flags | Implementación propia (tabla `feature_flags` + servicio cacheado) | — | ADR-012 |

⚠️ **Jaeger vs Tempo**: la spec técnica y `mejoras-y-saas` dicen **Jaeger**; el plan de SRE dice **Tempo + OpenTelemetry**. Ver `IN-15`.
⚠️ **Kubernetes / ArgoCD**: `mejoras-y-saas` declara "Kubernetes + Terraform + ArgoCD"; el plan de implementación marca `infra/k8s/` como *condicional* y **nunca menciona ArgoCD**. Ver `IN-16`.

## Arquitectura general

**Monolito modular con eventos asíncronos** (ADR-001). Todo el backend vive en un repositorio y corre en un único proceso, organizado internamente en módulos delimitados con interfaces explícitas. Se descartaron microservicios por overhead operacional para un equipo de 4-6 ingenieros y por inmadurez de fronteras del dominio.

```
                      ┌──────────────┐  ┌──────────────┐  ┌────────────────┐
  Actores             │ Frontend Web │  │ App Móvil    │  │ Backoffice     │
                      │ Next.js 14   │  │ React Native │  │ deRuedas       │
                      └──────┬───────┘  └──────┬───────┘  └───────┬────────┘
                             │  JWT (Bearer)   │                  │
                             └────────┬────────┴──────────────────┘
                                      ▼
                        ┌─────────────────────────────┐        ┌──────────┐
                        │  API Backend                │◄──────►│ Keycloak │
                        │  Python 3.12 + FastAPI      │  OIDC  └──────────┘
                        │  /api/v1  ·  /admin/api/v1  │
                        │  16 módulos delimitados     │
                        └───┬───────────┬─────────┬───┘
             SET LOCAL      │           │         │
        app.current_tenant  │           │         │  publish
                            ▼           ▼         ▼
                   ┌────────────┐ ┌─────────┐ ┌──────────────┐
                   │PostgreSQL16│ │  Redis 7│ │ OpenSearch   │
                   │ + RLS      │ │ Streams │ │ (índice sec.)│
                   └────────────┘ │ + Cache │ └──────────────┘
                                  └────┬────┘
                                       │ consume
                                       ▼
                              ┌─────────────────┐      ┌──────────────────┐
                              │ Workers Celery  │─────►│ S3-compatible    │
                              └────────┬────────┘      │ (fotos, docs)→CDN│
                                       │               └──────────────────┘
                                       ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ Integraciones externas                                            │
   │ Portal deRuedas · MercadoLibre · WhatsApp Cloud API · Financieras │
   │ OCR · Firma electrónica · Mercado Pago · Registro automotor       │
   └──────────────────────────────────────────────────────────────────┘
                    ▲
                    │ webhooks entrantes (HMAC + idempotencia)
```

### Módulos del backend (16, según spec técnica §2.3)

`auth` · `tenancy` · `users` · `stock` · `publishing` · `crm` · `communication` · `trade-in` · `finance` · `documents` · `accounting` · `operations` · `analytics` · `notifications` · `audit` · `admin`

Cada módulo tiene sus propias capas: `routes` (HTTP) → `services` (lógica de negocio) → `repositories` (acceso a datos) → `schemas` (Pydantic).

**Regla de importación vinculante**: se importa desde el paquete del módulo (`from app.modules.stock import VehicleService`), nunca desde su interior (`from app.modules.stock.service import ...`). Se valida en CI con un *import linter*.

### Comunicación entre módulos (3 patrones)

1. **Llamada sincrónica directa** — cuando la respuesta afecta el flujo. Ej.: `crm` consulta a `stock` para validar que el vehículo existe y está disponible. Siempre a través de interfaces explícitas; **nunca** accediendo a las tablas internas del otro módulo.
2. **Evento de dominio asincrónico** — cuando no hace falta esperar. Se publican en **Redis Streams** (`stock-events`, `crm-events`, …) y los consumen workers Celery. Con backoff exponencial y dead-letter stream tras agotar reintentos.
3. **Webhook externo entrante** — WhatsApp, financieras, portales. Endpoint dedicado → validación HMAC → persistencia en tabla de eventos entrantes (idempotencia) → procesamiento asincrónico.

Formato canónico de evento:

```json
{
  "event_id": "evt_01F3K...",
  "event_type": "vehicle.created",
  "event_version": "1.0",
  "tenant_id": "uuid",
  "occurred_at": "2026-05-06T14:30:00-03:00",
  "data": { }
}
```

Eventos principales: `vehicle.created`, `vehicle.updated`, `vehicle.status_changed`, `lead.created`, `lead.stage_changed`, `lead.closed`, `message.received`, `message.sent`, `swap.closed`, `credit.application_submitted`, `credit.application_resolved`, `operation.closed`, `payment.recorded`.

### Multi-tenancy (ADR-006) — la decisión de mayor alcance del sistema

**Patrón `discriminator-column` + Row-Level Security de PostgreSQL como defensa en profundidad.**

Capas simultáneas (el plan de seguridad las llama "tres capas de defensa"):

1. Columna `tenant_id NOT NULL` en toda tabla de negocio, FK a `tenants(id)`, y parte de los índices más usados.
2. **RLS de PostgreSQL** con política llamada exactamente **`tenant_isolation`**, que filtra por `current_setting('app.current_tenant')`. La sesión se establece con `SET LOCAL app.current_tenant = '<uuid>'` al inicio de cada request.
3. Filtro `tenant_id` **explícito también en el código de aplicación** (redundancia deliberada).
4. Tests automatizados de aislamiento, **bloqueantes en CI**, incluyendo un test introspectivo que recorre `pg_policies` verificando que toda tabla con `tenant_id` tenga la política activa.

El `tenant_id` se infiere **exclusivamente del claim del JWT** — nunca del body ni del query string. Los schemas Pydantic lo excluyen explícitamente de los inputs.

Sin `app.current_tenant` seteado, las queries sobre tablas con RLS **no devuelven filas** (falla visible, no silenciosa).

Métrica centinela: `rls_violations_total` debe ser **siempre 0**. Cualquier incremento es incidente **P0 inmediato**.

**Tablas exentas de RLS**: `tenants` (raíz), catálogos cross-tenant (`vehicle_brands`, `vehicle_models`, `vehicle_versions`, `plans`, `document_types`) y `audit_logs` (tiene `tenant_id` nullable y se filtra en capa de aplicación, porque el `super_admin` necesita lectura cross-tenant).

## Integraciones externas

| Servicio | Propósito | Tipo |
|---|---|---|
| Portal deRuedas | Publicación automática de avisos desde el stock | REST (conector propio) |
| MercadoLibre Vehículos | Publicación cruzada | REST — **fase posterior** |
| Marketplace de Facebook | Publicación cruzada | REST — **fase posterior** |
| WhatsApp Business Cloud API (Meta) | Canal comercial principal, entrante y saliente | REST + webhook (HMAC) |
| APIs de financieras | Precalificación, ofertas, originación de crédito | REST + webhook por partner |
| Servicios de OCR | Extracción de texto de fotos de documentos | REST |
| Firma electrónica | Firma de documentos de cierre | REST |
| Mercado Pago | Cobros y suscripciones recurrentes | REST + webhook |
| Registro automotor / DNRPA | Validación de dominio y titularidad | REST |
| Keycloak | Identidad (autohospedado) | OIDC |
| KMS del cloud provider | Claves de cifrado de campo | SDK |

## API REST — convenciones

- **Versionado en el path**: `/api/v1/`. Backoffice de Super Admin: `/admin/api/v1/`. Webhooks: `/webhooks/...` (sin prefijo de versión).
- **Autenticación**: `Authorization: Bearer <JWT>` emitido por Keycloak, firmado RS256. Access token **15 min**, refresh token **7 días** con rotación en cada uso. El refresh token solo es usable desde el dispositivo que lo emitió (huella).
- **Payloads**: JSON UTF-8. Fechas ISO 8601 con timezone (`2026-05-06T14:30:00-03:00`). IDs UUID canónico. Montos decimales con dos posiciones.
- **Paginación**: numerada (`?page=1&page_size=50`, headers `X-Total-Count`, `X-Page`, `X-Page-Size`) para listados con cuenta total; **cursor** (`?cursor=...&limit=100`) para listados grandes como mensajes. Default `page_size=20`, máximo 100.
- **Filtros**: query params directos (`?status=available`), con sufijos de operador (`?price_ars__gte=5000000`, `?year__in=2020,2021`), orden con `?sort=-created_at,price_ars`, búsqueda libre con `?q=`.
- **Errores**: **RFC 7807 Problem Details** (`application/problem+json`) con extensión `trace_id` y array `errors[]` con `field`/`code`/`message`.
- **Idempotencia**: header `Idempotency-Key` en endpoints de creación. TTL **24 h**. Misma clave + mismo payload = misma respuesta; misma clave + payload distinto = **409**.
- **Rate limiting**: 60 req/min por usuario y 1.000 req/min por tenant (spec técnica); header `X-RateLimit-Remaining`. ⚠️ El plan de seguridad declara límites en otro eje (100 req/s por IP) — ver `IN-19`.
- **OpenAPI 3.1** generado desde el código, en `openapi.yaml` del repositorio. Los tipos del frontend se generan con `openapi-typescript`.

### Endpoints principales por dominio

**Auth** — `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/mfa/enable`, `/auth/mfa/verify`, `GET /auth/me`.

**Tenancy / Users** — `GET|PATCH /tenant/me`, `POST /tenant/me/complete-onboarding`, `GET|POST /branches`, `GET|PATCH /branches/{id}`, `POST /branches/{id}/deactivate`, `GET /users`, `POST /users/invite`, `PATCH /users/{id}`, `POST /users/{id}/deactivate`, `POST /users/{id}/branches`.

**Stock** — `GET|POST /vehicles`, `GET|PATCH|DELETE /vehicles/{id}`, `POST /vehicles/{id}/status`, `GET /vehicles/{id}/history`, `POST|DELETE /vehicles/{id}/photos[/{photo_id}]`, `PATCH /vehicles/{id}/photos/order`, `POST /vehicles/import`, `GET /vehicles/search`, `GET /vehicles/suggest`, `GET /vehicles/{id}/price-suggestion`, `GET /catalog/brands`, `/catalog/brands/{id}/models`, `/catalog/models/{id}/versions`.

**Publishing** — `GET /vehicles/{id}/publications`, `POST /vehicles/{id}/publications/republish`.

**CRM** — `GET|POST /leads`, `GET|PATCH /leads/{id}`, `POST /leads/{id}/stage`, `/assign`, `/close` ⚠️, `GET /leads/{id}/history`, `GET|POST /leads/{lead_id}/activities`, `PATCH /activities/{id}`, `GET|POST /contacts`, `GET|PATCH|DELETE /contacts/{id}`, `POST /contacts/merge` ⚠️, `POST /contacts/{id}/forget`, `GET|POST /pipeline/stages`, `PATCH /pipeline/stages/{id}`, `POST /pipeline/stages/reorder`, `GET /loss-reasons`, `GET /crm/dashboard/{pipeline-summary|by-user|by-source|idle-leads}`.

**Communication** — `GET|POST /conversations`, `GET /conversations/{id}`, `GET|POST /conversations/{id}/messages`, `POST /conversations/{id}/{read|assign|close}`, **`GET /conversations/stream`** (canal en tiempo real ⚠️), `GET|POST /whatsapp/templates`, `POST /whatsapp/templates/sync`, `POST /webhooks/whatsapp`.

**Trade-in** — `GET|POST /swaps`, `GET /swaps/{id}`, `POST /swaps/{id}/{valuations|inspections|proposal|close}`.

**Finance** — `GET|POST /credit/applications`, `GET /credit/applications/{id}`, `POST /credit/applications/{id}/{pre-qualify|select-offer|submit|sign}`, `GET /credit/applications/{id}/{offers|status}`, `POST /webhooks/finance/{partner}`.

**Documents** — `GET|POST /documents`, `GET|DELETE /documents/{id}`, `GET /documents/{id}/download`, `POST /documents/search`, `POST /documents/{id}/sign`, `POST /operations/{id}/document-package`.

**Accounting** — `GET|POST /payments`, `GET /payments/{id}/receipt`, `GET /contacts/{id}/account`, `POST /bank/import`, `GET /bank/movements`, `POST /bank/reconcile`, `GET /accounting/export?format=tango`.

**Operations** — `GET|POST /operations`, `GET /operations/{id}`, `POST /operations/{id}/{close|costs}`.

**Analytics** — `GET /dashboards/{stock|pipeline|sales|productivity|financial}`, `GET /reports/{report_id}`, `POST /reports/custom`, `POST /reports/{id}/export?format=xlsx`.

**Admin (Super Admin)** — `GET|POST /admin/api/v1/tenants`, `GET|PATCH /admin/api/v1/tenants/{id}`, `POST /admin/api/v1/tenants/{id}/{impersonate|suspend|reactivate}`, `PATCH /admin/api/v1/tenants/{id}/plan`, `GET /admin/api/v1/tenants/{id}/health`, `GET|POST /admin/api/v1/plans`, `PATCH /admin/api/v1/plans/{id}`, `GET /admin/api/v1/support/tickets`, `POST /admin/api/v1/support/tickets/{id}/reply`.

**Infra** — `GET /health`, `/health/live`, `/ready`, `/metrics`.

⚠️ Los endpoints marcados tienen **contratos divergentes entre la spec técnica y el plan de implementación** (`/leads/{id}/close` vs `/won`+`/lost`; `/contacts/merge` vs `/contacts/{primary_id}/merge`; `DELETE /pipeline/stages/{id}` vs `POST /pipeline/stages/{id}/archive`; canal en tiempo real WebSocket vs SSE). Ver `IN-08` y `IN-12`.

## Capacidad y escalado objetivo

- **Capacidad inicial**: 200 tenants, 1.000 usuarios concurrentes, 50.000 vehículos en stock simultáneo, 500.000 leads activos, 5 millones de mensajes mensuales.
- **Crecimiento sin re-arquitectura**: hasta 1.000 tenants y 10× los volúmenes iniciales, vía escalado vertical de la base y horizontal del backend.
- Más allá: sharding, réplicas de lectura y eventual extracción de servicios.

Perfiles de carga por tamaño de tenant (plan SRE):

| Métrica | Chico | Medio | Grande |
|---|---|---|---|
| Vendedores activos | 1-2 | 3-5 | 6-15 |
| Vehículos en stock | 20-50 | 50-150 | 150-500 |
| Leads abiertos simultáneos | 10-30 | 30-100 | 100-300 |
| Mensajes WhatsApp/día | 20-50 | 100-300 | 500-1.500 |
| Requests API/día | 1k-5k | 5k-20k | 20k-100k |
