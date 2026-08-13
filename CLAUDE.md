# deRuedas Gestión — Instrucciones para Agentes

SaaS vertical **multi-tenant** para agencias de vehículos del mercado argentino. Monolito modular de 16 módulos que se comunican por eventos de dominio en Redis Streams, con aislamiento entre tenants garantizado por tres capas simultáneas: `tenant_id` en toda query, políticas RLS de PostgreSQL y tests de aislamiento bloqueantes en CI.

Compite contra Excel, cuadernos y WhatsApp — no contra CRMs enterprise. Eso condiciona cada decisión: **simplicidad antes que features, verticalidad antes que generalidad.**

> ⚠️ **Antes de escribir una línea de código**: leé [`knowledge-base/10_preguntas_abiertas.md`](knowledge-base/10_preguntas_abiertas.md). Hay **54 inconsistencias documentadas entre los documentos fuente, 14 de ellas bloqueantes**. Cada change de `CHANGES.md` declara cuáles le tocan.

---

## Stack Tecnológico

| Capa | Tecnología | Versión | Ancla |
|---|---|---|---|
| Backend API | Python + FastAPI | **3.12** | ADR-003 |
| ORM | SQLAlchemy | **2.x** (API moderna, no legacy) | — |
| Validación | Pydantic | **v2** | ADR-003 |
| Migraciones | Alembic | — | — |
| Base de datos | PostgreSQL | **16** (`pgcrypto`, `pg_trgm`, `postgis`, `uuid-ossp`) | ADR-002 |
| Cache / broker / pub-sub | Redis | **7** (Streams + Pub/Sub) | ADR-009 |
| Worker asíncrono | Celery | — | ADR-009 |
| Búsqueda full-text | OpenSearch | — | ADR-011 |
| Object storage | S3-compatible (MinIO en dev) | — | ADR-008 |
| Identidad | Keycloak (OAuth2 + OIDC, JWT RS256) | realm `deruedas` | ADR-007 |
| Frontend web | Next.js (App Router) + React + TypeScript | **14+** | ADR-004 |
| Frontend móvil | React Native + Expo (Expo Router) | Expo SDK | ADR-005 |
| Auth en frontend | NextAuth / Auth.js como cliente OIDC | — | — |
| Estilos / UI | Tailwind CSS + Radix UI + Lucide Icons | — | ADR-004 |
| Estado / datos en cliente | TanStack Query · React Hook Form + Zod | — | — |
| Mensajería | WhatsApp Business Cloud API (Meta, directo, sin BSP) | — | ADR-010 |
| Pagos | Mercado Pago | — | — |
| Observabilidad | Prometheus + Grafana + Loki + OpenTelemetry + Sentry | — | — |
| IaC / CI | Terraform + GitHub Actions + Docker Compose | — | — |
| Feature flags | Implementación propia (tabla `feature_flags` + servicio cacheado) | — | ADR-012 |

Dos puntos del stack **no están cerrados**: Jaeger vs Tempo (`IN-15`) y el alcance de Kubernetes/ArgoCD (`IN-16`). No los des por decididos.

---

## Base de Conocimiento

Todo en [`knowledge-base/`](knowledge-base/) está **derivado** de los 11 documentos vinculantes en `docs/`. Nada fue inventado; lo que no se pudo derivar quedó como pregunta abierta.

| Archivo | Cuándo leerlo |
|---|---|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Qué se construye y para quién |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack, 16 módulos, catálogo de endpoints |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Roles y matriz RBAC ⚠️ (en disputa, `IN-01`) |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | ~35 entidades, ERD, máquinas de estado, validadores argentinos |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | ~130 reglas `RN-{DOMINIO}-{NN}` |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | 12 épicas, 92 HU, Definition of Done |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | 13 flujos extremo a extremo |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, directorios, seguridad, escalado |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | 7 principios + 12 ADRs + 12 supuestos inferidos |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | **Leelo antes de codear** |
| [11_testing_y_calidad.md](knowledge-base/11_testing_y_calidad.md) | Pirámide, cobertura, quality gates |
| [12_seguridad_y_compliance.md](knowledge-base/12_seguridad_y_compliance.md) | STRIDE, Ley 25.326, retenciones, auditoría |
| [13_observabilidad_y_sre.md](knowledge-base/13_observabilidad_y_sre.md) | SLA/SLO, 18 alertas, runbooks, RTO/RPO |
| [14_pricing_y_gtm.md](knowledge-base/14_pricing_y_gtm.md) | Los **dos** modelos de pricing incompatibles |
| [15_marca_y_ux.md](knowledge-base/15_marca_y_ux.md) | Paleta, tipografía, tono de voz, accesibilidad |

**Precedencia entre fuentes** (a confirmar en `PA-01`): `constitucion` > `spec-tecnica` > `plan-implementacion` > planes especializados > `manual-usuario` / `plan-gtm` / `brand-book`.

`reference/` contiene material del **método** SDD, no del producto. No es fuente de verdad.

---

## Skills Disponibles

| Agente | Rol | Skills que carga |
|---|---|---|
| **Backend Core** | FastAPI, SQLAlchemy 2.x, modelo de datos | `fastapi-templates` ⚠️, `postgresql-table-design`, `postgresql-optimization`, `async-python-patterns` |
| **Backend Auth** | Keycloak, OIDC, JWT, RBAC | `keycloak-fastapi-integration`, `fastapi-templates` ⚠️ |
| **Backend Testing** | pytest, testcontainers, aislamiento multi-tenant | `python-testing-patterns` |
| **Frontend Web** | Next.js 14 App Router, React, TypeScript | `nextjs-app-router-patterns` |
| **Documentación** | Diátaxis, manuales, referencias | `documentation-writer` |
| **Orquestación** | OPSX / SDD | `active-orchestrator`, `kb-creator`, `roadmap-generator`, `agent-instruction`, `skill-registry`, `openspec-*` |

⚠️ **`fastapi-templates` tiene 3 overrides activos en este proyecto** (`O-1`, `O-2`, `O-3`): sus plantillas traen auth local con hash de contraseñas, borrado físico y CRUD single-tenant — las tres cosas **prohibidas acá**. Ver las Reglas Duras. No apliques sus plantillas sin adaptarlas.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo).

No hay skill disponible para **Ley 25.326** (protección de datos, Argentina); ese trabajo de compliance es manual. Tampoco para el design system técnico, porque todavía no existe la especificación (riesgo `R-4`, la produce C-07).

---

## Roadmap de Changes

El índice operativo completo está en [`CHANGES.md`](CHANGES.md): **32 changes (C-01 → C-32)**, derivados de las **194 tareas `T-XXX`** del plan de implementación con cobertura verificada **194/194**, sin huecos ni solapes.

**Nomenclatura: Olas** (`OLA 0` … `OLA 1.5`). Las "Fases F1-F5" quedaron degradadas a etiqueta de prioridad porque arrastran un calendario contradictorio (`IN-05`). Usá Olas.

**Camino crítico — 13 changes, 86 tareas:**
```
C-01 → C-02 → C-04 → C-05 → C-14 → C-15 → C-18 → C-19 → C-23 → C-29 → C-30 → C-31 → C-32
```

**C-05 (`identidad-auth-y-tenant-endpoints`) es el único serializador duro del proyecto.** En GATE 3 todos los agentes convergen ahí y esperan. Lo que se atrase en C-05 atrasa el proyecto entero, uno a uno.

**Primer change: `C-01 · foundation-setup`** (T-001…008, gobernanza ALTA, sin dependencias). Resuelve `IN-22` (umbral de cobertura del CI) e `IN-29` (numeración de ADRs).

**Riesgo dominante `R-1`**: el contrato de la API del portal deRuedas **no existe en ninguno de los 11 documentos**, bloquea 15 tareas y está sobre el camino crítico. No es deuda técnica — es una decisión de Dirección pendiente.

Cada change de `CHANGES.md` declara: scope, nivel de gobernanza, dependencias, rango `T-XXX`, **bloqueantes `IN-XX` que debe resolver** y punteros "Leer antes" a la KB.

---

## Reglas Duras (específicas del proyecto)

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador OPSX, governance por dominio, TDD estricto, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubre.

### Vinculantes por constitución — no son negociables

1. **NUNCA una query sin contexto de tenant** → `SET LOCAL app.current_tenant` + política RLS + `tenant_id` en la query. Las tres capas, siempre. `tenant_id` va **excluido de todo schema Pydantic de entrada** — se deriva del token, nunca del body.
   *Principio 4 · ADR-006 · override `O-3`*
2. **NUNCA hashear ni verificar contraseñas en la aplicación** → la autenticación se delega **enteramente** a Keycloak. Si ves `password_hash`, `get_password_hash` o `verify_password`, está mal.
   *Art. 3 · ADR-007 · override `O-1` · bloqueante `IN-06`*
3. **NUNCA borrado físico** → soft delete universal. `db.delete(obj)` está prohibido.
   *Principio 3 · override `O-2`*
4. **NUNCA secretos en el repositorio** → solo `.env.example` sin valores reales. Los secretos viven en AWS Secrets Manager / Google Secret Manager. `gitleaks` + `trufflehog` corren en pre-commit y en CI.
   *Art. 3*
5. **Cobertura de tests: 80 % de líneas, backend, global** — y **no decrece entre commits**. Un PR que la baje no se mergea sin justificación documentada.
   *Art. 2 — esto resuelve `IN-22` a favor de la constitución, contra el 70 %/60 % del plan de testing*

### De estilo y tooling

6. **Backend**: todo código Python pasa `ruff` y `mypy --strict` antes de commitear. Type hints obligatorios.
7. **Frontend**: `eslint` + `Prettier` + `tsc --strict`. **`any` prohibido** — si no sabés el tipo, es `unknown` y lo estrechás.
8. **NUNCA mocks de base de datos** → los tests de integración usan PostgreSQL, Redis y MinIO reales vía **testcontainers**. Es la única forma de que los tests de aislamiento multi-tenant prueben algo real.
9. **NUNCA concatenación de strings para armar SQL** → SQLAlchemy 2.x con parámetros bindeados, siempre.

### De proceso

10. **NUNCA commitear ni pushear sin pedido explícito** del usuario.
11. **Conventional commits** (`tipo(scope): descripción`) + firma `Co-Authored-By` en los commits generados por agente.
12. **NUNCA implementar sobre un bloqueante sin resolver** → si el change declara un `IN-XX`, se resuelve **al arrancar**, antes de escribir el código que depende de él. Sin esto, "bloqueantes distribuidos" se convierte en "bloqueantes olvidados".

---

## Flujo de Trabajo

```
knowledge-base/  →  CHANGES.md  →  /opsx:propose <change>  →  /opsx:apply  →  /opsx:archive
   (qué es)         (en qué orden)      (qué y cómo)          (código)        (cierre)
```

1. **Ubicate**: `openspec list --json` y `openspec status --change "<nombre>" --json`. Nunca adivines el estado de un artefacto.
2. **Leé antes de proponer**: los punteros "Leer antes" del change en `CHANGES.md`, y los `IN-XX` que ese change debe resolver.
3. **Resolvé los bloqueantes primero** (regla 12).
4. **Proponé**: `/opsx:propose <change-name>` genera proposal, design y tasks.
5. **Implementá**: `/opsx:apply <change-name>`, respetando el nivel de gobernanza declarado — en CRÍTICO no se escribe código sin aprobación humana explícita.
6. **Cerrá**: `/opsx:archive <change-name>` sincroniza las delta specs contra `openspec/specs/`.

---

*Generado por `agent-instruction`. Las reglas duras fueron confirmadas por el usuario; las vinculantes derivan de `docs/deRuedas-constitucion.md`.*
