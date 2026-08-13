# Propuesta — `foundation-setup` (C-01)

## Why

El repositorio tiene el cuerpo documental completo y **cero código**: no hay monorepo, ni entorno local reproducible, ni pipeline. Ningún otro change puede arrancar — C-01 es la raíz del árbol de dependencias y de él cuelgan los 31 restantes.

Además fija dos cosas que después salen caras de cambiar: el **quality gate de cobertura**, que bloquea todos los merges del proyecto de acá en adelante, y la **estructura de directorios**, que el §4.1 del plan de implementación declara vinculante.

## What Changes

- **Monorepo según el árbol canónico del §4.1**: `backend/`, `frontend-web/`, `frontend-mobile/`, `frontend-admin/`, `infra/`, `tools/`, `docs/{adr,runbooks,openapi.yaml}`, `.github/workflows/`. Directorios vacíos con `.gitkeep`.
- **Entorno local completo** en `docker-compose.yml`: PostgreSQL 16, Redis 7, OpenSearch, Keycloak (realm `deruedas-dev`), MinIO (bucket `deruedas-media`), Mailhog, backend con hot-reload, worker Celery, `frontend-web`. Más `docker-compose.test.yml` con contenedores efímeros para CI.
- **Contrato de configuración**: `backend/app/config.py` con Pydantic Settings v2 — grupos tipados, validación al arranque con muerte temprana, enmascarado de secretos, singleton cacheado. Y `.env.example` con la tabla completa de variables, sin valores reales.
- **Bootstrap del backend**: FastAPI con middleware base (CORS, GZip, `trace_id`), endpoints `GET /health` y `GET /ready`, handlers de excepción, lifespan asíncrono.
- **Bootstrap del frontend web**: Next.js 14+ App Router, TypeScript estricto, Tailwind, ESLint con `jsx-a11y`, path aliases.
- **Alembic** configurado con migración baseline vacía y convención `NNN_descripcion.py`.
- **`ci.yml`**: lint backend y frontend, tests unitarios con **quality gate de cobertura**, tests de integración, auditoría de dependencias. Bloquea el merge si falla.
- **`deploy-staging.yml`**: despliegue automático a staging con smoke tests post-deploy y rollback automático.

### Bloqueantes — ya resueltos, este change los ejecuta

Ambos venían declarados como "a resolver al inicio". [`ADR-000`](../../../docs/adr/ADR-000-precedencia-documental.md) los cerró antes de empezar:

- **`IN-22` — umbral de cobertura.** Cuatro valores incompatibles. La jerarquía de `ADR-000` hace ganar a N0: **80 % de líneas, backend, global**. Y la evidencia refuerza la decisión más de lo que suponía `CHANGES.md` — el `plan-implementacion` (N2) también dice *"Mínimo 80 % global"* en el job `test-backend-unit`. El 70/60 sale únicamente del `plan-testing` (N3), que no gana sobre N0. **Se enmienda el plan de testing, no la constitución.**
- **`IN-29` — numeración de ADRs.** Manda la numeración de `spec-tecnica` (N1 > N2). Este change corrige las anclas divergentes al sembrar `docs/adr/`.

### Bloqueante resuelto durante la propuesta

- **`IN-16` — sustrato de infraestructura.** Estaba abierto y dejaba a `T-008` sin poder implementarse. Cerrado por [`ADR-015`](../../../docs/adr/ADR-015-orquestacion-kubernetes-y-gitops.md): **Kubernetes con despliegue GitOps vía ArgoCD**. No se resolvió aplicando `ADR-000` sino llenando un vacío — N1 no menciona orquestación, N2 la deja condicional y el único documento que la nombra es N4, no normativo. **Con esto el change es implementable de punta a punta.**

### Riesgo que este change tiene que cerrar

- **`R-3` — no existe tabla canónica de variables de entorno.** Ningún documento del corpus la trae; la de `08_arquitectura_propuesta.md` está **derivada del stack, no transcripta**. C-01 la produce y la promueve a canónica mediante ADR, porque `.env.example` (T-004) y los secretos de staging (T-008) no se pueden escribir sin ella.

## Capabilities

### New Capabilities

- `platform/configuration`: contrato de configuración del sistema — qué variables lee, cuáles son obligatorias, cómo falla si falta una, y la garantía de que ningún secreto se expone en logs, `repr` ni serialización.
- `platform/service-health`: sondas de vida y disponibilidad del backend (`/health`, `/ready`), incluido el comportamiento en modo degradado cuando una dependencia no responde.
- `platform/delivery-pipeline`: garantías que el pipeline impone sobre cada cambio — quality gate de cobertura, lint y tipos, auditoría de dependencias, y el contrato de despliegue a staging con rollback.

### Modified Capabilities

Ninguna. `openspec/specs/` está vacío: este es el primer change del proyecto.

## Impact

- **Superficie**: repositorio completo. Crea el árbol de directorios entero y los archivos raíz.
- **Bloquea**: los 31 changes restantes. C-01 no tiene dependencias y es la raíz del camino crítico.
- **Efecto permanente**: el gate de cobertura al 80 % pasa a bloquear todos los merges desde el primer PR. La estructura del §4.1 queda fijada — desviarse después exige un ADR.
- **Sin impacto en datos ni en APIs de producto**: no hay usuarios, ni esquema, ni endpoints de dominio todavía.
- **Governance: ALTO.** Se propone y se espera revisión humana antes de escribir código.

## Supuestos registrados

Los dos primeros quedaron **confirmados por el Tech Lead el 13-ago-2026**. Los tres restantes siguen abiertos a revisión.

1. ✅ **CONFIRMADO — `docs/` alberga el corpus fuente y la estructura del §4.1 a la vez.** El §4.1 pide `docs/adr/`, `docs/runbooks/` y `docs/openapi.yaml`, pero asumía un `docs/` vacío — acá ya viven los 11 documentos convertidos. **Decisión**: los 11 `.md` se mueven a `docs/sdd/` y el resto queda como manda el §4.1. Se cumple la norma vinculante sin desvío y sin ADR justificatorio. Requiere actualizar los enlaces de `knowledge-base/`, `CLAUDE.md`, `AGENTS.md` y `CHANGES.md`.
2. ✅ **CONFIRMADO — los ADRs se mudan a `docs/adr/`.** El §4.1 describe `docs/adr/` como *"ADRs nuevos posteriores al SDD"*, que es exactamente lo que son. La ubicación original en `decisions/` se eligió antes de leer el §4.1. Se mueve el directorio completo: `ADR-000`, `ADR-015`, `ADR-016`, `ADR-017` y la enmienda `E-001`.
3. **Cobertura de branches: 60 %.** La constitución fija 80 % de líneas y **no dice nada sobre branches**. Ante el silencio de N0, gobierna `plan-testing` (N3) dentro de su dominio propio: 60 % de branches. El 80 % de líneas sigue siendo piso duro.
4. **La tabla de variables de entorno parte de la de `08_arquitectura_propuesta.md`** (~30 variables), reconciliada con los grupos que T-004 exige — `DatabaseSettings`, `RedisSettings`, `KeycloakSettings`, `S3Settings`, `WhatsAppSettings`, `ObservabilitySettings`. **Hueco detectado**: ni la tabla ni los grupos de T-004 contemplan Mercado Pago, que sí está en el stack.
5. **`CHANGES.md` dice `frontend/`; el §4.1 dice `frontend-web/`.** Se sigue el §4.1, que es la fuente vinculante. `CHANGES.md` es un índice derivado — hay que corregir esa imprecisión.
