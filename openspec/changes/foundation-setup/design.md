# Diseño técnico — `foundation-setup` (C-01)

## Context

Ver [`proposal.md`](proposal.md) §Why para la motivación. Lo que condiciona el diseño:

- **El §4.1 del plan de implementación es vinculante** (N2 según [`ADR-000`](../../../decisions/ADR-000-precedencia-documental.md)). Define el árbol del monorepo hasta el nivel de archivo. Apartarse exige un ADR.
- **El repositorio ya no está vacío**: tiene `docs/` con los 11 documentos fuente convertidos, `knowledge-base/`, `CHANGES.md`, `decisions/` y `openspec/`. El §4.1 fue escrito asumiendo un repositorio limpio.
- **No hay tabla canónica de variables de entorno** en ningún documento del corpus (`R-3`). La de `08_arquitectura_propuesta.md` está derivada del stack, no transcripta.
- **`IN-22` e `IN-29` ya están resueltos** por `ADR-000`. Este change los ejecuta; no los vuelve a discutir.
- Los tests de integración usan **testcontainers**, no mocks de base de datos (regla dura 8). Eso condiciona la forma de `docker-compose.test.yml` y del job de integración.

## Goals / Non-Goals

**Goals:**

- Que `docker compose up -d` deje el entorno completo funcionando en menos de tres minutos, sin pasos manuales.
- Que el pipeline corra verde de punta a punta sobre un repositorio sin lógica de negocio.
- Que la tabla de variables de entorno quede **canónica y trazable**, cerrando `R-3`.
- Que la estructura quede alineada con el §4.1 **sin desvíos**, para no arrancar el proyecto debiendo un ADR.

**Non-Goals:**

- Ningún modelo de datos, endpoint de dominio ni lógica de negocio. Las migraciones más allá del baseline vacío son C-02.
- El realm de Keycloak se preconfigura solo para desarrollo local. La integración real de identidad es C-05.
- No se resuelve el design system ni la paleta de Tailwind: depende de C-07 (riesgo `R-4`, los primitivos no existen en el corpus).
- No se toca `frontend-mobile/` ni `frontend-admin/` más allá de crear sus directorios con `.gitkeep`.
- No se despliega a producción. `deploy-production.yml` queda como directorio previsto, no como pipeline funcional.

## Decisions

### D-1 — El corpus fuente se muda a `docs/sdd/`; el resto del `docs/` sigue el §4.1

El §4.1 reserva `docs/` para `adr/`, `runbooks/` y `openapi.yaml`. Acá `docs/` ya tiene los 11 `.md` convertidos.

**Decisión**: mover los 11 documentos a `docs/sdd/` y dejar `docs/adr/`, `docs/runbooks/` y `docs/openapi.yaml` exactamente donde el §4.1 los pide. Mover también `decisions/ADR-000-precedencia-documental.md` a `docs/adr/`.

**Por qué**: es la única opción que cumple la norma vinculante **sin desvío**, y por lo tanto sin deber un ADR justificatorio desde el primer commit del proyecto. Separa además dos cosas de naturaleza distinta: corpus fuente inmutable contra artefactos vivos que el proyecto genera.

**Alternativas consideradas**:
- *Convivencia plana* — los 11 `.md` sueltos junto a `adr/` y `runbooks/`. No rompe ningún enlace, pero mezcla corpus inmutable con artefactos vivos en un mismo nivel, y esa distinción importa: uno no se toca nunca, el otro crece con cada change.
- *Mantener `decisions/` en la raíz* — separación conceptual más nítida, pero es desvío de norma vinculante y obliga a C-01 a emitir un ADR justificando por qué no usa `docs/adr/`. Costo alto para un beneficio estético.

**Consecuencia**: hay que actualizar los enlaces de `knowledge-base/` (los 16 archivos referencian `docs/`), `CLAUDE.md`, `AGENTS.md` y `CHANGES.md`. Es mecánico y verificable, pero no es gratis. Se trata como tarea explícita, no como efecto colateral.

> ⚠️ Este punto quedó registrado como **supuesto para revisión** en `proposal.md` §Supuestos. Es el momento más barato para revertirlo.

### D-2 — Tabla canónica de variables de entorno (cierra `R-3`)

Se adopta como canónica la tabla derivada en `08_arquitectura_propuesta.md`, reorganizada según los grupos que T-004 exige y con los huecos cubiertos. Se documenta en `docs/adr/` como ADR propio, porque es una decisión sin fuente en el corpus y el Principio 5 exige que las decisiones sean explícitas para ser vinculantes.

| Grupo (T-004) | Variables |
|---|---|
| `DatabaseSettings` | `DATABASE_URL` 🔒 · `DATABASE_POOL_SIZE` |
| `RedisSettings` | `REDIS_URL` · `CELERY_BROKER_URL` |
| `SearchSettings` | `OPENSEARCH_URL` · `OPENSEARCH_USER` 🔒 · `OPENSEARCH_PASSWORD` 🔒 |
| `KeycloakSettings` | `KEYCLOAK_URL` · `KEYCLOAK_REALM` · `KEYCLOAK_CLIENT_ID` · `KEYCLOAK_CLIENT_SECRET` 🔒 · `KEYCLOAK_JWKS_URL` |
| `S3Settings` | `S3_ENDPOINT` · `S3_BUCKET` · `S3_ACCESS_KEY` 🔒 · `S3_SECRET_KEY` 🔒 · `CDN_BASE_URL` |
| `WhatsAppSettings` | `WHATSAPP_APP_SECRET` 🔒 · `WHATSAPP_VERIFY_TOKEN` 🔒 |
| `CryptoSettings` | `TENANT_SECRETS_MASTER_KEY` 🔒 · `KMS_KEY_ID` 🔒 |
| `PaymentSettings` **(nuevo)** | `MERCADOPAGO_ACCESS_TOKEN` 🔒 |
| `ObservabilitySettings` | `SENTRY_DSN` 🔒 · `OTEL_EXPORTER_OTLP_ENDPOINT` · `OTEL_TRACES_SAMPLER_ARG` · `LOG_LEVEL` |
| `MailSettings` | `SMTP_HOST` · `SMTP_USER` 🔒 · `SMTP_PASSWORD` 🔒 |
| `AppSettings` | `APP_ENV` · `API_BASE_URL` · `CORS_ORIGINS` |
| Frontend | `NEXTAUTH_SECRET` 🔒 · `NEXTAUTH_URL` · `NEXT_PUBLIC_API_BASE_URL` |

🔒 = sensible: enmascarado obligatorio en logs, `repr` y serialización.

**Dos correcciones sobre las fuentes**, ambas derivadas aplicando `ADR-000`:

1. **`APP_ENV`, no `ENVIRONMENT`.** T-004 (plan de implementación, N2) dice explícitamente *"Settings cambian según `APP_ENV`"*; la tabla de `08_arquitectura_propuesta.md` usa `ENVIRONMENT`, pero la KB es material **derivado**, no fuente. Gana N2.
2. **Se agrega `PaymentSettings`.** Ni la tabla de la KB ni los grupos de T-004 contemplan Mercado Pago, que sí está en el stack declarado. Es un hueco de ambas fuentes, no una contradicción.

Valores permitidos de `APP_ENV`: `local | ci | staging | production`. Cualquier otro se rechaza al arrancar.

### D-3 — Umbrales de cobertura: 80 % líneas / 60 % ramas

Aplicación directa de `ADR-000` sobre `IN-22`. Las cuatro fuentes:

| Fuente | Nivel | Umbral |
|---|---|---|
| `constitucion` Art. 2 | **N0** | 80 % líneas, backend, global |
| `spec-tecnica` §7.2 | N1 | 80 % core, 70 % resto |
| `plan-implementacion` (job `test-backend-unit`) | N2 | **80 % global** |
| `plan-testing` §3.2, §3.7, §7.4 | N3 | 70 % líneas + 60 % ramas |

**Decisión**: **80 % de líneas global** como piso duro. N0 gana y **N2 coincide** — el 70 % sale únicamente de N3, que no prevalece sobre N0 ni en su dominio propio. El *"70 % el resto"* de N1 queda por debajo del piso de N0 y se descarta; el *"80 % core"* es compatible y se satisface solo.

**Ramas: 60 %.** La constitución **no se pronuncia** sobre cobertura de ramas. Ante el silencio de N0, gobierna `plan-testing` (N3) dentro de su dominio propio. Es la regla de competencia de dominio de `ADR-000` funcionando como corresponde: no rebaja nada de N0, cubre un vacío.

**Consecuencia documental**: se enmienda el **plan de testing**, no la constitución. Queda registrado en el ADR de este change.

### D-4 — Numeración de ADRs y siembra de `docs/adr/`

Aplicación de `ADR-000` sobre `IN-29`: manda la numeración de `spec-tecnica` (N1 > N2). El plan de implementación solo **referencia** ADRs; la spec los **contiene** con contexto, decisión, alternativas y consecuencias.

Correcciones a aplicar en las anclas del plan:

| ADR | Significado canónico (spec) | Anclas del plan a corregir |
|---|---|---|
| `ADR-002` | PostgreSQL como base principal | El plan lo usa como "Migrations (Alembic)" en T-007 y todas las migraciones |
| `ADR-005` | React Native con Expo | El plan lo usa como "OpenSearch" en T-098 y T-099 |
| `ADR-011` | OpenSearch | El plan no lo referencia; su tema está bajo `ADR-005` |

`docs/adr/` se siembra con `ADR-000` (mudado) más los dos ADRs que este change produce: la tabla de variables de entorno (D-2) y la resolución de umbrales de cobertura (D-3). Los `ADR-001`…`ADR-012` de la spec **no se copian**: viven en `docs/sdd/deRuedas-spec-tecnica.md` y `docs/adr/` es para *"ADRs nuevos posteriores al SDD"*, como dice el §4.1.

**Numeración**: los ADRs nuevos continúan desde `ADR-013` para no colisionar con la serie de la spec. `ADR-000` es la única excepción, y es deliberada: es metadocumental y precede a la serie entera.

### D-5 — Composición del entorno local

Un solo `docker-compose.yml` con perfiles, no varios archivos por escenario. Servicios: `postgres` (16, con extensiones habilitadas al init), `redis` (7), `opensearch`, `keycloak` (realm `deruedas-dev` importado al arranque), `minio` (bucket `deruedas-media` creado al startup), `mailhog`, `backend` (hot-reload por volume mount), `worker` (Celery, comparte imagen con backend), `frontend-web` (hot-reload).

Volúmenes nombrados `pg_data`, `redis_data`, `minio_data` para persistir entre reinicios. Redes separadas: `default` para aplicaciones y `observability` prevista para cuando entren Prometheus y Grafana en C-03.

`docker-compose.test.yml` es un archivo aparte, **sin volúmenes persistentes**: los contenedores nacen y mueren con la corrida de CI. Es la contrapartida de la regla dura 8 — los tests de integración corren contra PostgreSQL, Redis y MinIO reales.

**Alternativa considerada**: un único compose con perfiles `dev`/`test`. Descartada porque el §4.1 nombra los dos archivos explícitamente, y porque mezclar la definición persistente con la efímera es una fuente conocida de tests que pasan en local y fallan en CI por estado remanente.

### D-6 — Estructura de jobs del pipeline

Seis jobs paralelos donde se puede, con dependencias mínimas:

| Job | Qué corre | Bloquea |
|---|---|---|
| `lint-backend` | `ruff` · `black --check` · `mypy --strict` | Sí |
| `lint-frontend` | `eslint` · `prettier --check` · `tsc --noEmit` | Sí |
| `test-backend-unit` | `pytest -m 'not integration'` con cobertura — **gate 80 % / 60 %** | Sí |
| `test-backend-integration` | `docker compose -f docker-compose.test.yml up` + `pytest -m integration` | Sí |
| `test-frontend` | `vitest run` con cobertura | Sí |
| `security` | `pip-audit` · `npm audit` · `gitleaks` | Sí (alta/crítica; **cualquier** secreto) |

Disparadores: propuesta de cambio contra `main` y push a `main`. Caché de dependencias de `pip` y `npm` para sostener el presupuesto de 15 minutos.

`gitleaks` corre además en pre-commit (regla dura 4), pero se repite en CI: un hook local es una cortesía, no un control.

### D-7 — Despliegue a staging

Imágenes Docker etiquetadas con el SHA del commit, empujadas a un registry, desplegadas en azul-verde. Pruebas de humo posteriores contra `/health` y `/ready` durante cinco minutos; si fallan, conmutación automática al pool anterior.

**El sustrato de infraestructura queda abierto** — ver Open Questions.

## Risks / Trade-offs

| Riesgo | Mitigación |
|---|---|
| **La mudanza de `docs/` rompe enlaces** en 16 archivos de `knowledge-base/`, `CLAUDE.md`, `AGENTS.md` y `CHANGES.md`. | Tarea explícita en `tasks.md`, con verificación automatizada de que no queden enlaces rotos. No se trata como efecto colateral. |
| **El gate de cobertura al 80 % sobre un repositorio casi vacío** puede fallar de entrada: pocos archivos, cualquier línea sin cubrir pesa mucho. | Los archivos de scaffolding sin lógica (`__init__.py`, config de Alembic) se excluyen del cómputo con una configuración explícita y auditable, no con exclusiones amplias. |
| **La paleta de Tailwind depende de C-07**, que todavía no existe (riesgo `R-4`). | Se configura Tailwind con la paleta por defecto y un punto de extensión marcado con `TODO(C-07)`. No bloquea T-006. |
| **`APP_ENV` contradice la tabla de la KB.** Si alguien lee solo la KB, escribe `ENVIRONMENT` y el arranque falla. | La corrección se registra en el ADR de variables de entorno y se corrige la tabla de `08_arquitectura_propuesta.md` en el mismo change. |
| **El realm de Keycloak preconfigurado puede divergir** del que C-05 necesite. | El realm de desarrollo se versiona como archivo de importación, no se configura a mano. C-05 lo modifica versionando el cambio. |
| **Presupuesto de 15 minutos del pipeline** con seis jobs y testcontainers. | Paralelismo máximo y caché de dependencias. Si se excede, el job de integración es el primer candidato a separarse a un disparador distinto — decisión para C-03, no para acá. |

## Migration Plan

No hay datos ni usuarios: no hay migración de estado. La única mudanza es de archivos.

1. Mover `docs/*.md` → `docs/sdd/` y `decisions/ADR-000-*.md` → `docs/adr/` con `git mv`, preservando historial.
2. Actualizar todos los enlaces internos y verificar que no quede ninguno roto.
3. Crear el resto del árbol del §4.1 con `.gitkeep` en los directorios vacíos.
4. El resto del change es aditivo.

**Reversión**: `git revert` del commit de mudanza. Como no hay estado externo, la reversión es total y sin efectos residuales.

## Open Questions

**`IN-16` — sustrato de infraestructura para el despliegue a staging (afecta solo a T-008).**

T-008 dice *"despliegue azul-verde a staging mediante Terraform o kubectl **según infra elegida**"*. Esa elección no está hecha en ningún documento: `IN-16` (Kubernetes con o sin ArgoCD) figura entre las referencias que el corpus menciona pero nunca documenta, y `PA-20` lo asigna a SRE.

**Recomendación**: para la Ola 0, Terraform sobre contenedores gestionados, **sin Kubernetes**. Adoptar Kubernetes después es aditivo — se cambia el destino del despliegue, no el pipeline — mientras que arrancar con Kubernetes carga complejidad operativa sobre un equipo que todavía no tiene un solo endpoint de dominio en producción.

**Alcance del impacto**: T-001 a T-007 no dependen de esta decisión y pueden implementarse completos. **T-008 es la única tarea bloqueada**, y queda marcada como tal en `tasks.md`.

Esto no cambia las specs: `platform/delivery-pipeline` describe el despliegue en términos de comportamiento observable —se despliega, se verifica, se revierte si falla— sin comprometerse con el sustrato.
