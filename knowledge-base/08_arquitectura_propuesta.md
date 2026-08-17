# Arquitectura Propuesta

> Fuente primaria: `deRuedas-spec-tecnica.md` §2, §5, §9. Complementado con `deRuedas-plan-implementacion.md` (estructura real de directorios) y `deRuedas-plan-sre.md`.

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| **Monolito modular** | Todo el backend (ADR-001) | Equipo de 4-6 ingenieros, dominio con fronteras aún inmaduras, time-to-market crítico. Microservicios descartados por overhead operacional. |
| **Event-driven asincrónico** | Comunicación inter-módulo (Redis Streams + Celery) | Las integraciones externas (WhatsApp, financieras, portales) son inherentemente asíncronas. Desacopla módulos y permite evolución independiente. |
| **Discriminator column + RLS** | Multi-tenancy (ADR-006) | `tenant_id` en toda tabla + política `tenant_isolation` de PostgreSQL como red de seguridad. Descartados schema-per-tenant y database-per-tenant por complejidad operacional. |
| **Layered architecture por módulo** | `routes → services → repositories → schemas` | Separación de responsabilidades dentro de cada módulo delimitado. |
| **Repository pattern** | Capa `repositories` | Aísla el acceso a datos; facilita tests con dobles. |
| **CQRS light (vistas materializadas)** | Dashboards y analytics | Consultas analíticas sin castigar la performance OLTP. Refresco en background. |
| **Outbox / idempotencia de eventos** | Tabla `processed_events`, header `Idempotency-Key` | Garantiza *exactly-once* efectivo ante reintentos y webhooks duplicados. |
| **Circuit breaker** | Integraciones salientes (WhatsApp, financieras, portal) | Evita cascadas de fallos cuando un tercero se cae. Alerta si queda abierto > 10 min. |
| **Retry con backoff exponencial + DLQ** | Publishing y consumers de eventos | 5 reintentos, factor 2, tope configurable; luego dead-letter stream con alerta. |
| **Strangler fig** | Migración del portal legacy (Classic ASP) | Contexto de `mejoras-y-saas`, no del SaaS en sí. Fachada de API por delante del sistema viejo, migración módulo a módulo. |
| **Feature flags** | Todo despliegue de funcionalidad nueva (ADR-012) | Activación progresiva por tenant sin re-desplegar. Implementación propia (tabla + servicio cacheado). |
| **Blue-green + canary** | Despliegue a producción | Switch atómico, rollback inmediato. |
| **Soft delete universal** | Toda tabla de negocio | Reversibilidad y trazabilidad. Los borrados físicos son la excepción documentada. |
| **Append-only log** | `audit_logs`, `vehicle_status_history`, `lead_stage_history` | Trazabilidad no repudiable. `UPDATE`/`DELETE` revocados a nivel de base. |
| **Table partitioning** | `messages` (mensual), `audit_logs` (RANGE mensual) | Volumen alto con retención por antigüedad. |
| **Índice secundario de búsqueda** | OpenSearch (ADR-011) | PostgreSQL sigue siendo la fuente de verdad; OpenSearch se sincroniza por eventos. |

## Estructura de directorios

```
deruedas-gestion/
├── backend/
│   └── app/
│       ├── core/                    # config, db, security, events, errors, logging
│       │   ├── config.py            # Pydantic Settings v2
│       │   ├── db.py                # engine, session, set_tenant_context()
│       │   ├── security.py          # require_role, require_permission, @audit_action
│       │   ├── events.py            # publisher / consumer base (Redis Streams)
│       │   └── errors.py            # DomainError, RFC 7807
│       ├── modules/
│       │   ├── auth/                # identidad, sesiones, MFA
│       │   ├── tenancy/             # tenants, branches, plans, subscriptions, billing
│       │   ├── users/               # usuarios, roles, asignación a sucursales
│       │   ├── stock/               # vehículos, catálogos, fotos, estados, historial
│       │   ├── publishing/          # conectores a portales externos
│       │   ├── crm/                 # leads, pipeline, actividades, tags, fuentes
│       │   ├── communication/       # conversaciones, mensajes, WhatsApp, templates
│       │   ├── trade_in/            # permutas, valuaciones, inspecciones
│       │   ├── finance/             # financieras, solicitudes, ofertas
│       │   ├── documents/           # documentos, OCR, firma electrónica
│       │   ├── accounting/          # cuenta corriente, cobros, conciliación
│       │   ├── operations/          # operaciones de venta, costos, cierre
│       │   ├── analytics/           # dashboards, reportes, exportación
│       │   ├── notifications/       # in-app, email, push
│       │   ├── audit/               # registro de auditoría transversal
│       │   └── admin/               # backoffice, queries cross-tenant
│       │       ├── router.py        # ← único punto de entrada HTTP del módulo
│       │       ├── service.py
│       │       ├── repository.py
│       │       ├── schemas.py
│       │       ├── models.py
│       │       └── __init__.py      # ← exporta la interfaz pública del módulo
│       ├── workers/                 # tasks Celery, consumers de eventos, crons (beat)
│       └── main.py
├── migrations/                      # Alembic
├── tests/
│   ├── unit/
│   ├── integration/                 # testcontainers: PostgreSQL, Redis, MinIO
│   ├── contract/                    # schemathesis contra OpenAPI
│   ├── e2e/                         # Playwright
│   └── factories/                   # factory_boy — único módulo de factories admitido
├── frontend-web/                    # Next.js 14 App Router
│   └── src/
│       ├── app/                     # rutas (App Router)
│       ├── features/                # vertical slices por dominio
│       ├── components/ui/           # 13 primitivos + Storybook
│       ├── lib/                     # cliente API tipado (TanStack Query), auth (NextAuth)
│       └── types/                   # generados con openapi-typescript
├── frontend-mobile/                 # React Native + Expo (Expo Router)
├── frontend-admin/                  # backoffice deRuedas (Next.js)
├── infra/                           # sin terraform/ ni k8s/ — ADR-023 §Notas: "no se crean"
│   ├── local/                       # soporte del entorno local (ADR-019)
│   └── observability/
├── docs/
│   ├── adr/
│   └── runbooks/
├── .github/workflows/               # pr-validation, main-deploy-staging, release-production
├── docker-compose.yml               # entorno completo local en < 3 minutos
└── openapi.yaml
```

### Regla de frontera entre módulos (vinculante, validada en CI)

```python
# ✅ permitido
from app.modules.stock import VehicleService

# ❌ prohibido — se valida con import linter en el pipeline
from app.modules.stock.service import VehicleService
```

Cada módulo expone su interfaz pública en su `__init__.py`. Los módulos **no acceden a las tablas internas de otros módulos**: o llaman a la interfaz explícita, o reaccionan a un evento de dominio.

## Seguridad

Ver el detalle completo en [12_seguridad_y_compliance.md](12_seguridad_y_compliance.md).

- **Autenticación**: OAuth2 + OIDC vía **Keycloak** autohospedado (realm `deruedas`). JWT RS256. Access 15 min, refresh 7 días con rotación. Clients: `backend` (confidential), `frontend-web` / `frontend-mobile` (public + PKCE), `frontend-admin`. Password hashing **argon2id**. MFA con TOTP.
- **Autorización**: RBAC verificado **siempre en el backend** mediante `require_role()` / `require_permission()`. La definición canónica de permisos vive en el módulo `auth` y se exporta como diccionario consultable.
- **Aislamiento multi-tenant**: tres capas simultáneas — `tenant_id` en toda query de la aplicación, **RLS de PostgreSQL** (`tenant_isolation` sobre `current_setting('app.current_tenant')`), y tests de aislamiento bloqueantes en CI (incluido un test introspectivo sobre `pg_policies`).
- **Validación de input**: **Pydantic v2** con validación estricta. `tenant_id` explícitamente excluido de todos los schemas de entrada. Nunca `pickle` de inputs externos.
- **Protección OWASP Top 10**: ORM obligatorio con parámetros bindeados (nunca concatenación de SQL) · escape automático + CSP estricta (XSS) · tokens CSRF y cookies `SameSite=Strict` · lista blanca de dominios para fetch saliente (SSRF) · scanner de dependencias en pipeline · `audit_logs` estructurados con `trace_id`.
- **Cifrado**: TLS 1.2+ en tránsito (preferentemente 1.3), incluso entre containers. AES-256 en reposo ⚠️ ~~vía KMS del cloud provider~~ — **sin resolver** desde [`ADR-023`](../docs/adr/ADR-023-despliegue-sobre-vps-con-docker-compose.md): un VPS no tiene KMS gestionado. El cifrado en reposo del disco queda pendiente de decidir (cifrado a nivel de volumen del proveedor, o `pgcrypto` por campo). `ADR-023` no lo cubre. Cifrado de campo con **AES-GCM** y clave derivada por tenant para secretos sensibles (API keys de WhatsApp, webhook tokens, semillas MFA), rotada cada 12 meses.
- **Secrets management**: ⛔ ~~AWS Secrets Manager / Google Secret Manager según el proveedor~~ → **SOPS + age** desde [`ADR-023`](../docs/adr/ADR-023-despliegue-sobre-vps-con-docker-compose.md): los secretos de despliegue se versionan **cifrados**, y la clave privada vive solo en el VPS. **Nunca en claro en el repositorio** — solo `.env.example` sin valores reales. Detección con `gitleaks` + `trufflehog` en pre-commit y CI, que deben seguir detectando un secreto en claro colocado junto a los cifrados.
- **Webhooks entrantes**: validación **HMAC**, persistencia para idempotencia, respuesta 200 OK en < 300 ms, procesamiento asincrónico.
- **Headers**: HSTS (max-age 1 año, includeSubDomains, preload), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, Permissions-Policy restrictiva, CSP estricta en producción.
- **Rate limiting**: 60 req/min por usuario y 1.000 req/min por tenant (spec) / 100 req/s por IP en el LB (plan de seguridad) · login 10/min · reset de password 3/hora · republish 1/min por vehículo. ⚠️ Ver `IN-19`.

## Observabilidad

- **Métricas**: Prometheus (scrape cada 15 s) + Grafana. RED por endpoint (Rate, Errors, Duration p50/p95/p99), USE por recurso (CPU, memoria, disco, red, conexiones de DB), métricas de negocio (vehículos y leads creados por hora, mensajes enviados, tasa de error de WhatsApp, latencia de financieras) y métricas de calidad de datos (**filas con `tenant_id` NULL — debe ser cero**, conversaciones huérfanas, leads sin actividad > 30 días).
- **Logs**: Loki. Estructurados en JSON (`structlog`), siempre con `trace_id`, `tenant_id`, `user_id`, `request_id`. Retención 90 días.
- **Tracing**: OpenTelemetry → **Jaeger** (spec, `mejoras-y-saas`) / **Tempo** (plan de SRE). ⚠️ Ver `IN-15`. Sampling: 100 % en dev/staging; en producción 0,1 % normal, 10 % operaciones lentas, 100 % operaciones fallidas.
- **Errores**: Sentry (managed), agrupación por similaridad, asignación nominal y SLA de respuesta.
- **Alertas**: Alertmanager sobre reglas de Prometheus. Las críticas paginan vía PagerDuty o equivalente. Detalle del catálogo en [13_observabilidad_y_sre.md](13_observabilidad_y_sre.md).
- **Dashboards**: versionados como código (Grafana JSON) para API, PostgreSQL y procesamiento asincrónico.
- **Métrica centinela de seguridad**: `rls_violations_total` — debe ser 0 siempre.

## Infraestructura y despliegue

> ⛔ **Sección superada el 17-ago-2026** por [`ADR-023`](../docs/adr/ADR-023-despliegue-sobre-vps-con-docker-compose.md). Lo que sigue es lo que declaraba el corpus; abajo, lo vigente.

- ~~**Contenedores** Docker, orquestados con **Kubernetes**~~ (declarado en `mejoras-y-saas`, N4 y no normativo; el plan de implementación lo marcaba como condicional y no mencionaba ArgoCD).
- ~~**IaC**: Terraform.~~
- **CI/CD**: GitHub Actions. Tres workflows: `pr-validation` (< 15 min), `main-deploy-staging` (< 20 min), `release-production` (< 60 min).
- ~~**Cloud**: AWS o GCP, multi-zona dentro de una región sudamericana (São Paulo o Santiago)~~. **Single-region** era un riesgo aceptado con revisión cada 12 meses.

**Vigente (`ADR-023`)**: **VPS único en Hostinger con Docker Compose**, reverse proxy con TLS automático, y servicios de datos autoalojados. Sin Terraform, sin Kubernetes, sin ArgoCD y sin nube gestionada.

⚠️ El riesgo de *single-region* **se agravó y cambió de naturaleza**: ya no es una región sin réplica, es un **nodo único**. Los compromisos de *"DR en región alternativa"* (RTO 4 h) y el 99.9 % de Enterprise quedaban sin sustento. ✅ **Resuelto el 17-ago-2026** por [`ESC-001`](../docs/escalaciones/ESC-001-sla-sobre-nodo-unico.md) / `PA-30`: Dirección + SRE decidió **ajustar lo publicado** en vez de dotar de redundancia — Enterprise baja a **99.5 %** y el DR en región alternativa **se retira**. El riesgo técnico no desaparece; lo que desaparece es la promesa que no lo cubría.
- **Ambientes**: Local (Docker Compose, todo el entorno en < 3 min) · CI (efímeros, se descartan al finalizar) · Staging (persistente, datos sintéticos, espejo de producción) · Producción (solo accesible vía pipeline).
- **Autoscaling**: API backend con HPA por CPU + RPS custom, **min 2 / max 10** réplicas. Workers con HPA por lag de cola, min 1 por consumer group. PostgreSQL y Redis con scaling manual planificado.
- **Failover de PostgreSQL**: Patroni o equivalente.

## Variables de entorno

Derivadas de las tecnologías declaradas. El repositorio incluye `.env.example` **sin valores reales** (regla constitucional).

| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|:---:|
| `DATABASE_URL` | Conexión a PostgreSQL 16 | `postgresql+asyncpg://app:***@db:5432/deruedas` | **Sí** |
| `DATABASE_POOL_SIZE` | Tamaño del pool (headroom ≤ 60 %) | `20` | No |
| `REDIS_URL` | Cache, Streams y Pub/Sub | `redis://redis:6379/0` | No |
| `CELERY_BROKER_URL` | Broker de Celery (Redis) | `redis://redis:6379/1` | No |
| `OPENSEARCH_URL` | Índice de búsqueda | `http://opensearch:9200` | No |
| `OPENSEARCH_USER` / `OPENSEARCH_PASSWORD` | Credenciales de OpenSearch | — | **Sí** |
| `KEYCLOAK_URL` | Base del servidor de identidad | `https://auth.deruedas.com` | No |
| `KEYCLOAK_REALM` | Realm | `deruedas` | No |
| `KEYCLOAK_CLIENT_ID` | Client del backend (confidential) | `backend` | No |
| `KEYCLOAK_CLIENT_SECRET` | Secreto del client | — | **Sí** |
| `JWT_PUBLIC_KEY` / JWKS URL | Verificación de firma RS256 | — | No |
| `S3_ENDPOINT` | Object storage (MinIO en dev) | `http://minio:9000` | No |
| `S3_BUCKET` | Bucket de fotos y documentos | `deruedas-media` | No |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Credenciales de storage | — | **Sí** |
| `CDN_BASE_URL` | Base del CDN para assets | `https://cdn.deruedas.com` | No |
| `WHATSAPP_APP_SECRET` | Validación HMAC de webhooks de Meta | — | **Sí** |
| `WHATSAPP_VERIFY_TOKEN` | Verificación del webhook | — | **Sí** |
| `TENANT_SECRETS_MASTER_KEY` | Master key AES-GCM para secretos por tenant | (en KMS) | **Sí** |
| `KMS_KEY_ID` | Clave de cifrado en el proveedor cloud | — | **Sí** |
| `MERCADOPAGO_ACCESS_TOKEN` | Cobros y suscripciones | — | **Sí** |
| `SENTRY_DSN` | Reporte de errores | — | **Sí** |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Exportador de trazas | — | No |
| `OTEL_TRACES_SAMPLER_ARG` | Ratio de sampling | `0.001` (prod) | No |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Envío de emails (Mailhog en dev) | — | **Sí** |
| `APP_ENV` | Ambiente activo | `local \| ci \| staging \| production` | No |
| `LOG_LEVEL` | Nivel de log | `INFO` | No |
| `API_BASE_URL` | Base pública de la API | `https://api.deruedas.com` | No |
| `NEXTAUTH_SECRET` / `NEXTAUTH_URL` | Sesión del frontend | — | **Sí** |

⚠️ Esta tabla nació **derivada** del stack declarado, no transcripta: ningún documento del corpus incluye una tabla canónica de variables de entorno. Desde el 13-ago-2026 la tabla canónica es [`ADR-013`](../docs/adr/ADR-013-variables-de-entorno.md), que cierra `PA-06` / `R-3` — **ante cualquier divergencia, manda el ADR**. La corrección `ENVIRONMENT` → `APP_ENV` ya está aplicada acá. Ver `PA-06` en [10_preguntas_abiertas.md](10_preguntas_abiertas.md).

## Estrategia de escalado

1. **Hoy → 200 tenants**: escalado vertical de PostgreSQL + horizontal del backend (HPA 2-10 réplicas).
2. **200 → 1.000 tenants** (10× volúmenes): réplicas de lectura de PostgreSQL (con **RLS activo también en las réplicas**, verificado por tests), particionado de las tablas de alto volumen, cache más agresivo.
3. **Más allá**: sharding por tenant, extracción de servicios de los módulos con fronteras ya maduras (el monolito modular está diseñado para hacer esa extracción factible), multi-región activo (Ola 3, con RTO objetivo < 30 min).

**Headroom operativo obligatorio**: API p95 de utilización ≤ 60 % · pool de PostgreSQL ≤ 60 %, CPU ≤ 50 %, disco ≥ 30 % libre · memoria de Redis ≤ 70 % · workers con capacidad para **3×** el throughput actual · storage ≥ 30 % libre, con planificación de scaling al 80 % y 30 días de anticipación.
