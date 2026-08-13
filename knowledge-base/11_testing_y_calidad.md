# Testing y Calidad

> Fuente primaria: `deRuedas-plan-testing.md`. Complementado con `deRuedas-constitucion.md` (Artículo 2), `deRuedas-spec-tecnica.md` §7 y `deRuedas-plan-implementacion.md` (CI).
> ⚠️ Este es el dominio con más contradicciones numéricas del corpus. Ver `IN-22`, `IN-23`, `IN-32`, `IN-54`.

## Filosofía

La constitución (Principio 6, *Calidad por defecto*) establece que **no hay fase de testing posterior al desarrollo**. Las estimaciones de las historias incluyen tiempo de pruebas, documentación y revisión. Ante presión por entregar más rápido, **se reduce el alcance, no la calidad**.

## Pirámide de testing

⚠️ **Dos formas distintas de la pirámide** (`IN-32`):

| Nivel | `spec-tecnica.md` §7.1 | `plan-testing.md` §3.1 |
|---|---:|---:|
| Unitarias | 70 % | 60 % |
| Integración | 20 % | 25 % |
| **Contract** | *(no existe)* | **10 %** |
| E2E | 10 % | 5 % |
| Exploratorio manual | — | fuera de la pirámide |

El plan de testing introduce una capa de **contract testing** que la spec no contempla. Es una capa real y valiosa (valida el `openapi.yaml` como contrato entre backend y frontend), así que probablemente la spec sea la desactualizada.

## Umbrales de cobertura

🔴 **Cuatro valores incompatibles** — ver `IN-22`. Este es un quality gate que bloquea merges:

| Fuente | Umbral |
|---|---|
| `constitucion.md` Art. 2 (**vinculante**) | **80 %** de líneas, backend, global |
| `spec-tecnica.md` §7.2 | **80 %** módulos core (`auth`, `stock`, `crm`, `communication`, `finance`), **70 %** el resto |
| `plan-implementacion.md` (job `test-backend-unit`) | **80 % global** |
| `plan-testing.md` §3.2, §3.7, §7.4 | **70 % líneas + 60 % branches** en dominio |

Otros umbrales, estos sí consistentes:
- **Contract**: 100 % de endpoints y de eventos publicados.
- **E2E**: entre 5 y 15 flujos críticos del producto (8 identificados para Ola 1).
- **Regla transversal**: la cobertura **no decrece entre commits**. Un PR que la baje no se mergea sin justificación documentada.
- La cobertura por sí sola no se considera indicador suficiente; se complementa con revisión de escenarios de negocio cubiertos.

## Herramientas por nivel

| Nivel | Backend | Frontend |
|---|---|---|
| Unit | `pytest` + `pytest-asyncio` + `factory-boy` + `faker` | `Vitest` + React Testing Library + `msw` |
| Integración | `pytest` + **testcontainers** (PostgreSQL, Redis, MinIO) + `httpx` | — |
| Contract | **`schemathesis`** contra el OpenAPI | tipos generados con `openapi-typescript` |
| E2E web | **Playwright** | Playwright |
| E2E mobile | **Detox** o **Maestro** | — |
| Performance | **k6** o **Locust**; `pytest-benchmark` para microbenchmarks | — |
| Seguridad (DAST) | **OWASP ZAP** (passive scan sobre staging) | — |
| Accesibilidad | `axe-core` integrado en Playwright; `jest-axe` | `jest-axe` |
| Lint / tipos | `ruff`, `mypy --strict` | `eslint`, `Prettier`, `tsc --strict` |
| SAST | `semgrep` | `eslint` con plugin de seguridad |
| SCA | `pip-audit`, `Trivy` | `npm audit` |
| Secretos | `gitleaks`, `trufflehog` | idem |
| Manual (accesibilidad) | NVDA, VoiceOver (+ JAWS según la spec) | idem |

Ninguna herramienta tiene versión declarada en el corpus.

## Tiempos máximos de suite

| Suite | Objetivo |
|---|---|
| Test unitario individual | < 5 ms |
| **Suite unitaria completa** | **< 60 s** ⚠️ (constitución y spec dicen "< 5 minutos" — `IN-54`) |
| Test de integración individual | < 2 s |
| Suite de integración completa | < 10 min (constitución y spec: < 15 min) |
| Suite de contract | < 5 min |
| **Suite E2E completa** | **< 30 min** ✅ consistente en las tres fuentes |
| E2E de flujos críticos selectos | < 5 min |
| Pre-commit hooks | < 10 s |
| Pipeline `pr-validation` | < 15 min |
| `main-deploy-staging` | < 20 min |
| `release-production` | < 60 min |
| `docker compose up` (entorno completo local) | < 3 min |

## Tipos de prueba (10)

Funcional · **aislamiento multi-tenant** · seguridad · performance · resiliencia · privacidad/PII · accesibilidad · compatibilidad · regresión · exploratorio manual.

### Pruebas críticas de aislamiento multi-tenant

Son las más importantes del proyecto. Ancladas al **Principio 1** de la constitución, al control de seguridad **C4.1** y a **ADR-006**.

1. **Suite `test_tenant_isolation`**: crea los tenants A y B con datos completos y ejerce **todos** los endpoints como usuario de A intentando ver, modificar y eliminar recursos de B. **Bloqueante en CI, severidad P0.** Cero violaciones toleradas.
2. **Test introspectivo `test_every_tenant_table_has_rls_policy`**: recorre `information_schema.columns` buscando la columna `tenant_id` y verifica en `pg_policies` que exista una política llamada exactamente **`tenant_isolation`**.
   Tablas exentas declaradas: `brands`, `models`, `versions` (catálogo cross-tenant), `audit_logs` (política especial), `tenants` y `super_admins` (administrativas).
   > Nota: la mención de una tabla **`super_admins`** acá es la única evidencia en todo el corpus de que el Super Admin podría vivir en tabla propia. Relevante para `IN-02`.
3. **RLS activo también en las réplicas de lectura**, verificado por test.
4. Métrica centinela `rls_violations_total` monitoreada en producción; cualquier incremento es P0.

### Pruebas de autorización (RBAC)

Recorren los cuatro roles (`super_admin`, `manager`, `salesperson`, `admin_staff`) contra cada endpoint mediante introspección del router de FastAPI, verificando el código **200 o 403 exacto** esperado.

### Pruebas de autenticación

- Firma de JWT manipulada → 401
- Token expirado → 401
- Token con `tenant_id` de otro tenant → 403 / 404
- Claim `role` manipulado → 401
- Sin token → 401
- Refresh token reutilizado después de la rotación → 401

### Pruebas de inyección y validación

SQL clásico rechazado · inputs > 10 MB rechazados antes del parsing · campos no declarados en el schema → 422.

### Pruebas de privacidad

Sobre `POST /api/v1/contacts/{id}/forget`: verifican anonimización del nombre, eliminación de mensajes, ausencia de PII en `audit_logs`, y desaparición del contacto de exports y búsquedas.

## Datos de prueba

- **Política dura**: datos **100 % sintéticos**. Está **prohibido** usar dumps de producción o de cliente real, incluso anonimizados, en cualquier ambiente.
- **Factories**: `factory-boy` (Python) y `fishery` (TypeScript). Único módulo admitido: `tests/factories`.
  Ejemplo: `LeadFactory` con `Faker('es_AR')` y `estimated_value` entre 5.000.000 y 30.000.000.
- **Seeds por ambiente**: 2-3 tenants ficticios idempotentes, nombrados **"Agencia Norte"** y **"Automotores del Sur"**. La spec menciona además un dataset **"agencia demo"** que reproduce la complejidad de un cliente real.
- **Convenciones de PII sintética**: DNI con prefijo `TEST-`, teléfonos `+54 9 9999...`, emails en el dominio `test.deruedas.com`.
- **Aislamiento entre tests**: transacciones revertidas en integración; base efímera por test vía testcontainers cuando no aplica.
- **E2E**: endpoint `/test/reset`, habilitado **solo en ambientes no productivos**.

## Pruebas de performance

| Tipo | Configuración | Cadencia |
|---|---|---|
| Carga normal | 10 usuarios concurrentes | por release |
| Pico de promoción | 50 usuarios concurrentes, 5 min | por release |
| Soak | 24 horas sostenidas | semestral |
| Stress | hasta el punto de quiebre | trimestral |
| Chaos testing | inyección de fallos en staging | mensual, desde Ola 2 |

Thresholds del plan de testing: p95 < 300 ms en endpoints típicos, p95 < 2 s en búsqueda compleja, error rate < 0,1 %. ⚠️ Estos números **no coinciden** con la constitución ni con la spec (`IN-23`).

Objetivos puntuales del plan de implementación (más estrictos): listado de vehículos p95 < 200 ms con 10k vehículos · búsqueda p95 < 150 ms · suggest p95 < 50 ms · creación p95 < 300 ms · importación de 1.000 vehículos < 2 min · indexación en OpenSearch < 5 s.

## Gestión de tests flaky

Regla constitucional: **los tests deterministas no son negociables**. Un test que falla intermitentemente se trata como bug del test, no como característica del sistema.

- Retry automático: **1 vez**.
- Flakiness > 2 % → se abre ticket.
- 2 semanas sin corregir → **el test se elimina**.
- Quality gate: flakiness global **< 1 % en 30 días**.
- Si una funcionalidad no es testeable de forma determinista (por ejemplo, por dependencias temporales), **se rediseña hasta que lo sea**.

## Severidades de defecto

| Sev. | Tiempo de resolución |
|---|---|
| S0 | < 4 h |
| S1 | < 24 h |
| S2 | < 1 semana |
| S3 | backlog |
| S4 | sin SLA |

Triage inicial: máximo **4 horas hábiles**. Postmortem obligatorio para S0/S1 dentro de **5 días hábiles**.

## Quality gates del pipeline `pr-validation`

Todos bloqueantes salvo indicación en contrario:

- [ ] Linting y formateo (`ruff`, `eslint`, `Prettier`)
- [ ] Tipos estrictos (`mypy --strict`, `tsc --strict`)
- [ ] Tests unitarios con umbral de cobertura
- [ ] Tests de integración con testcontainers
- [ ] Contract tests (`schemathesis`)
- [ ] **Tests de aislamiento multi-tenant** — cero violaciones
- [ ] **Tests introspectivos de RLS**
- [ ] SAST (`semgrep`) — bloquea en severidad *high*, warning en *medium*
- [ ] SCA (`pip-audit`, `npm audit`, `Trivy`) — bloquea en crítico
- [ ] Secretos (`gitleaks`) — bloquea ante cualquier detección
- [ ] Accesibilidad básica — findings *serious* bloquean el release
- [ ] Import linter (fronteras entre módulos)
- [ ] Build de imagen Docker
- [ ] **Aprobación humana de un reviewer distinto del autor**

DAST (OWASP ZAP) corre sobre staging capturando el tráfico de los tests E2E: severidad *high* bloquea, *medium* va a backlog.

## Definition of Done — tarea

- [ ] Tests escritos en los niveles que correspondan
- [ ] La cobertura del módulo no disminuye
- [ ] CI en verde
- [ ] Documentación actualizada
- [ ] Review de un autor distinto
- [ ] Migración reversible
- [ ] Anclaje al SDD declarado (ADR o sección)

## Definition of Ready — cierre de ola / release

- [ ] Todas las tareas de la ola completadas
- [ ] Suite en verde en staging por al menos un ciclo E2E nocturno
- [ ] Criterios de cierre de las épicas verificables
- [ ] **Sin bugs S0 ni S1 abiertos**
- [ ] Exploratorios manuales ejecutados
- [ ] Release notes preparadas

## Monitoreo continuo de calidad

- **Synthetic monitoring**: cada 5 minutos contra `/health/live`.
- **Smoke tests** contra staging: cada hora.
- **E2E completo** contra staging: al menos una vez por día.
- Auditoría mensual de ruido de alertas: objetivo, > 80 % de las alertas P0/P1 con acción real asociada.
