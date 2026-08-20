# ADR-013 — Tabla canónica de variables de entorno

- **Estado**: Aceptado
- **Fecha**: 2026-08-13
- **Decisores**: Tech Lead
- **Resuelve**: `R-3` · `PA-06`
- **Afecta**: `C-01` (T-004, T-002, T-001), `backend/app/config.py`, `.env.example`, `docker-compose.yml`, ⛔ ~~`infra/k8s/`~~ → el override de producción de Compose ([`ADR-023`](ADR-023-despliegue-sobre-vps-con-docker-compose.md): `infra/k8s/` no se crea)
- **Naturaleza**: **decisión sin fuente en el corpus.** No es un desvío: ningún documento de los 11 contiene una tabla canónica de variables de entorno. Se registra como ADR porque el Principio 5 de la constitución exige que las decisiones sean explícitas para ser vinculantes.
- **Enmendado**: 16-ago-2026 — se agrega `DATABASE_MIGRATION_URL` por [`ADR-020`](ADR-020-rol-de-conexion-sin-bypass-de-rls.md). La tabla pasa de 35 a **36 variables** y de 15 a **16 sensibles**. Solo por adición: ninguna variable existente cambia de nombre, de significado ni de clasificación.

---

## Contexto

`T-004` (plan de implementación, N2) pide un módulo de configuración con Pydantic Settings v2 agrupado en clases por dominio, y nombra los grupos. Pero **ninguna fuente enumera las variables**.

La única tabla existente vive en [`knowledge-base/08_arquitectura_propuesta.md`](../../knowledge-base/08_arquitectura_propuesta.md) §Variables de entorno, y arrastra una advertencia explícita al pie: está **derivada del stack declarado, no transcripta**. La `knowledge-base/` es material derivado — no es fuente de verdad y no puede serlo por sí sola.

Sin esta tabla, `T-004` no se puede implementar y `T-002` no puede escribir `.env.example`. Es el bloqueante `R-3`, y por la regla dura 12 del proyecto se resuelve al arrancar el change, no cuando aparece.

## Decisión

Se adopta como **canónica** la tabla de abajo: la de `08_arquitectura_propuesta.md` reorganizada según los grupos que `T-004` exige, con dos correcciones y un hueco cubierto.

Son **36 variables**, de las cuales **16 son sensibles**.

### `DatabaseSettings`

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `DATABASE_URL` | Conexión a PostgreSQL 16 con el rol de **aplicación** | `postgresql+asyncpg://mitutu:***@db:5432/deruedas` | 🔒 |
| `DATABASE_MIGRATION_URL` | Conexión con el rol **propietario**. Solo la usa Alembic | `postgresql+asyncpg://deruedas:***@db:5432/deruedas` | 🔒 |
| `DATABASE_POOL_SIZE` | Tamaño del pool (headroom ≤ 60 %) | `20` | |

> **Por qué son dos.** [`ADR-020`](ADR-020-rol-de-conexion-sin-bypass-de-rls.md): el rol que atiende tráfico no puede saltear RLS ni tocar el esquema, y crear tablas y políticas es exactamente lo que una migración hace. Las dos URLs deben apuntar a la **misma base** — solo cambia el usuario — y `alembic/env.py` lo verifica al arrancar.
>
> `DATABASE_MIGRATION_URL` es **opcional**: el proceso que atiende peticiones y el worker no migran, y exigírsela les metería adentro la credencial del propietario, que es justamente la que no deben tener.

### `RedisSettings`

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `REDIS_URL` | Cache, Streams y Pub/Sub | `redis://redis:6379/0` | |
| `CELERY_BROKER_URL` | Broker de Celery | `redis://redis:6379/1` | |

### `SearchSettings`

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `OPENSEARCH_URL` | Índice de búsqueda | `http://opensearch:9200` | |
| `OPENSEARCH_USER` | Usuario de OpenSearch | `admin` | 🔒 |
| `OPENSEARCH_PASSWORD` | Contraseña de OpenSearch | — | 🔒 |

### `KeycloakSettings`

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `KEYCLOAK_URL` | Base del servidor de identidad | `https://auth.deruedas.com` | |
| `KEYCLOAK_REALM` | Realm | `deruedas` | |
| `KEYCLOAK_CLIENT_ID` | Client del backend (confidential) | `backend` | |
| `KEYCLOAK_CLIENT_SECRET` | Secreto del client | — | 🔒 |
| `KEYCLOAK_JWKS_URL` | Endpoint de claves públicas para verificar RS256 | `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/certs` | |
| `KEYCLOAK_ISSUER` | El `iss` que traen los tokens — el hostname **público**, que no siempre es `KEYCLOAK_URL` | `https://auth.deruedas.com/realms/deruedas` | |

### `S3Settings`

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `S3_ENDPOINT` | Object storage (MinIO en dev) | `http://minio:9000` | |
| `S3_BUCKET` | Bucket de fotos y documentos | `deruedas-media` | |
| `S3_ACCESS_KEY` | Credencial de storage | — | 🔒 |
| `S3_SECRET_KEY` | Credencial de storage | — | 🔒 |
| `CDN_BASE_URL` | Base del CDN para assets | `https://cdn.deruedas.com` | |

### `WhatsAppSettings`

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `WHATSAPP_APP_SECRET` | Validación HMAC de webhooks de Meta | — | 🔒 |
| `WHATSAPP_VERIFY_TOKEN` | Verificación del webhook | — | 🔒 |

### `CryptoSettings`

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `TENANT_SECRETS_MASTER_KEY` | Master key AES-GCM para secretos por tenant | (en KMS) | 🔒 |
| `KMS_KEY_ID` | Clave de cifrado en el proveedor cloud | — | 🔒 |

### `PaymentSettings` — grupo nuevo

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `MERCADOPAGO_ACCESS_TOKEN` | Cobros y suscripciones | — | 🔒 |

### `ObservabilitySettings`

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `SENTRY_DSN` | Reporte de errores | — | 🔒 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Exportador de trazas (apunta a Tempo, ver [`ADR-016`](ADR-016-trazas-distribuidas-tempo.md)) | `http://tempo:4317` | |
| `OTEL_TRACES_SAMPLER_ARG` | Ratio de sampling | `0.001` en producción | |
| `LOG_LEVEL` | Nivel de log | `INFO` | |

### `MailSettings`

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `SMTP_HOST` | Servidor de correo (Mailhog en dev) | `mailhog:1025` | |
| `SMTP_USER` | Usuario SMTP | — | 🔒 |
| `SMTP_PASSWORD` | Contraseña SMTP | — | 🔒 |

### `AppSettings`

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `APP_ENV` | Ambiente activo | `local` \| `ci` \| `staging` \| `production` | |
| `API_BASE_URL` | Base pública de la API | `https://api.deruedas.com` | |
| `CORS_ORIGINS` | Orígenes permitidos, separados por coma | `http://localhost:3000` | |

### Frontend (`frontend-web/`)

| Variable | Para qué | Ejemplo | 🔒 |
|---|---|---|:-:|
| `NEXTAUTH_SECRET` | Firma de la sesión de NextAuth | — | 🔒 |
| `NEXTAUTH_URL` | Base pública del frontend | `https://app.deruedas.com` | |
| `NEXT_PUBLIC_API_BASE_URL` | Base de la API visible desde el navegador | `http://localhost:8000` | |

🔒 = **sensible**. Enmascarado obligatorio en logs, en `repr`, en serialización y en mensajes de error. Su valor real nunca se versiona: `.env.example` lleva valores ficticios y los reales viven en el gestor de secretos del proveedor (regla dura 4).

## Las dos correcciones y el hueco

### 1. `APP_ENV`, no `ENVIRONMENT`

La tabla de la KB nombra la variable `ENVIRONMENT`. `T-004` dice, textualmente, *"Settings cambian según `APP_ENV`"*.

Aplicando [`ADR-000`](ADR-000-precedencia-documental.md): el plan de implementación es **N2, fuente normativa**; la `knowledge-base/` es **material derivado, sin nivel**. No hay empate — gana N2. La tabla de `08_arquitectura_propuesta.md` se corrige en este mismo change.

Valores permitidos: `local | ci | staging | production`. **Cualquier otro se rechaza al arrancar**, con muerte temprana del proceso.

### 2.b `KEYCLOAK_ISSUER` separado de `KEYCLOAK_URL` — agregado el 20-ago-2026

Keycloak emite el `iss` con el hostname por el que se **pidió** el token, y el
backend lo alcanza por el nombre interno de la red. En desarrollo son
`localhost:8080` y `keycloak:8080`; en producción, el dominio público y el del
contenedor. Deducir el emisor de `KEYCLOAK_URL` funciona solo mientras
coincidan, y deja de funcionar exactamente cuando entra el primer login por
navegador.

**El síntoma engaña**: 401 en todo, y parece un problema de firma cuando es una
cadena que no coincide. Mismo criterio que `KEYCLOAK_JWKS_URL`: explícito si
está, deducido si no.

### 2. `KEYCLOAK_JWKS_URL`, no `JWT_PUBLIC_KEY`

La KB registra la entrada ambigua *"`JWT_PUBLIC_KEY` / JWKS URL"*, que son dos mecanismos distintos, no sinónimos: una clave pegada en una variable contra un endpoint que se consulta y rota solo.

Se adopta **JWKS URL**. La clave pública embebida obliga a un despliegue cada vez que Keycloak rota su par de claves; el endpoint de JWKS lo resuelve el cliente OIDC sin intervención. Es además lo que `ADR-007` presupone al delegar la identidad enteramente a Keycloak.

### 3. Se agrega `PaymentSettings`

Mercado Pago está en el stack declarado y `MERCADOPAGO_ACCESS_TOKEN` está en la tabla de la KB, pero **`T-004` no contempla ningún grupo de pagos**. No es una contradicción entre fuentes: es un hueco de las dos. Se cubre con un grupo propio en vez de colgar la variable de `AppSettings`, para que el día que Mercado Pago necesite más configuración (webhook, sandbox, cuenta) tenga dónde ir.

## Consecuencias

- **`.env.example` y los grupos de `Settings` cubren exactamente el mismo conjunto.** Se verifica de forma automatizada (tarea 4.8): si alguien agrega una variable a `Settings` y se olvida del ejemplo, falla.
- **La tabla de `08_arquitectura_propuesta.md` se corrige** (`ENVIRONMENT` → `APP_ENV`) y pasa a apuntar acá. Deja de ser derivación y pasa a ser reflejo de una decisión registrada.
- **`PA-06` queda cerrada.** La pregunta era *"¿cuál es el conjunto canónico de variables de entorno?"*. Esta es la respuesta, y es enmendable por ADR posterior como cualquier otra.
- **`08_arquitectura_propuesta.md` no es fuente.** Que la tabla haya nacido ahí no le da autoridad; se la da este ADR.
- **Toda variable nueva exige actualizar esta tabla**, `Settings` y `.env.example` en el mismo commit. Es la contrapartida de tener una tabla canónica: si se desincroniza, deja de serlo.

## Alternativas consideradas

**Derivar las variables en cada change, a medida que hagan falta.** Menos trabajo por adelantado y sin riesgo de especificar de más. Descartada porque `T-002` necesita `.env.example` completo *ahora* y porque una tabla que crece sin registro central termina siendo treinta variables sin dueño, que es exactamente el estado que `PA-06` denuncia.

**Tomar la tabla de la KB tal cual, sin ADR.** Es lo más rápido. Descartada por el Principio 5: una decisión no registrada no es vinculante, y el proyecto arrancaría con su contrato de configuración apoyado en un documento que se autodeclara derivado.

**Un solo `Settings` plano, sin grupos.** Más simple de leer. Descartada porque `T-004` (N2) especifica los grupos, y apartarse exigiría un ADR justificatorio para un beneficio nulo.
