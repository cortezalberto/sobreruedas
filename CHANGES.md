# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **deRuedas Gestión**.
> Derivado del **plan de implementación vinculante** (`docs/sdd/deRuedas-plan-implementacion.md`, 194 tareas atómicas `T-001`…`T-194`), reordenado donde la base de conocimiento revela dependencias reales que el plan no respeta.
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

**Cobertura verificada: 194/194 tareas `T-XXX`** distribuidas en **32 changes**, sin huecos ni solapamientos (cada `T-XXX` cae en exactamente un change). El grafo de dependencias derivado del propio plan es acíclico y no tiene violaciones de orden.

---

## Cómo usar este documento

1. **Identificá el change**: buscá el primer `C-NN` con estado `[ ]` cuyas dependencias estén todas en `[x]`.
2. **Resolvé sus bloqueantes primero**: leé la sección **"Bloqueantes a resolver"** del change. Los `IN-XX` se deciden **al inicio del change, antes de escribir la primera línea de código que dependa de ellos** — nunca a mitad de camino. Si un bloqueante sigue abierto, el change no arranca.
3. **Leé la KB**: abrí los archivos de **"Leer antes"** y las tareas `T-XXX` del rango en `docs/sdd/deRuedas-plan-implementacion.md`. Las fichas de tarea traen criterios de aceptación, archivos a tocar y tests esperados.
4. **Proponé e implementá**: `/opsx:propose C-NN-<slug>` → `/opsx:apply` → `/opsx:archive`.
5. **Marcá el checkbox** de este archivo al archivar el change.

> **Granularidad**: un change agrupa entre 2 y 10 tareas `T-XXX`. Según §3.4 del plan, **cada `T-XXX` es una sesión de IA** que termina en un pull request. Un change es entonces una capacidad coherente de varias sesiones, no una sola sesión.

---

## ✅ PA-01 — RESUELTA (2026-08-13)

> Cerrada por [`ADR-000 · Precedencia documental`](docs/adr/ADR-000-precedencia-documental.md). Decisores: Tech Lead + Product Manager.

### Lo que se decidió

**Jerarquía por autoridad, con competencia por dominio.** La fecha de creación **no se usa como desempate en ningún caso**.

| Nivel | Documentos | Autoridad |
|---|---|---|
| **N0** | `constitucion` | Principios, reglas vinculantes y **glosario canónico**. Gana siempre. Solo cambia por enmienda del Artículo 8. |
| **N1** | `spec-tecnica` + ADRs | El **"cómo"** técnico. Autoridad delegada explícitamente por N0. |
| **N2** | `plan-implementacion` | Orden y descomposición en `T-XXX`. **No decide diseño.** |
| **N3** | `plan-seguridad`, `plan-testing`, `plan-sre` | **Prevalecen sobre N1 dentro de su dominio propio**, nunca sobre N0. Cada aplicación se registra como ADR. |
| **N4** | `plan-gtm`, `manual-usuario`, `brand-book`, `mejoras-y-saas`, `historias-usuario` | **No normativos.** Insumo e intención. |

### Por qué la recencia quedó descartada

Este roadmap asumía que *"los 11 documentos dicen Versión 1.0 — Mayo de 2026, la fecha no desempata"*. Eso es lo que dice el **texto**. Los metadatos internos de los `.docx` (`docProps/core.xml`) **sí discriminan al milisegundo** — y dicen otra cosa:

- Los 11 se generaron en **una sola sesión de 8 h 41 min** (6-may-2026, 14:31 → 23:12 ART).
- Todos con `cp:revision = 1` y `created == modified`: **nunca editados después de generarse**.
- El orden es de **generación**, no de deliberación. Aplicarlo haría ganar a `plan-gtm` (01:18) sobre `spec-tecnica` (18:17), y a `manual-usuario` (02:12) sobre la constitución (18:05).

**Corolario que corrige la tabla que estaba acá**: las cuatro "señales de decisión revisada" (`IN-04`, `IN-22`, `IN-31`, `IN-23`) **no son revisiones que no se propagaron**. Son **deriva de generación** — cada documento se produjo sin verificar consistencia contra los anteriores. No hay una versión posterior que recuperar; hay que decidir cada caso.

### Efecto inmediato sobre los bloqueantes

| ID | Antes | Ahora |
|---|---|---|
| `IN-22` | 80 % vs 70/60 | ✅ **80 %** — N3 no gana sobre N0. Se enmienda el plan de testing. |
| `IN-29` | Numeración de ADRs en disputa | ✅ **Manda la spec** (N1 > N2). Ejecuta **C-01**. |
| `IN-31` | 99.9/99.9/99.95 vs 99.0/99.5/99.9 | ✅ **99.0 / 99.5 / 99.9** — competencia de dominio de SRE. Compatible con el SLO de 99.7 %. |
| `IN-01`, `IN-02` | 3 roles ES vs 4 roles EN; `super_admin` sin representación posible | 🟡 **DECIDIDOS** por [`ADR-017`](docs/adr/ADR-017-catalogo-de-roles-y-super-admin.md): **4 roles en el sistema, 3 en `user_role_enum`**, `super_admin` en tabla aparte exenta de RLS, `users.tenant_id` **intacto en `NOT NULL`**. ⏳ Condicionados a la enmienda [`E-001`](docs/adr/E-001-enmienda-glosario-super-admin.md), en discusión hasta el **20-ago-2026**. |
| `IN-15`, `IN-16` | Jaeger vs Tempo; Kubernetes con o sin ArgoCD | ✅ **RESUELTOS**: **Tempo** ([`ADR-016`](docs/adr/ADR-016-trazas-distribuidas-tempo.md), competencia de dominio de SRE) y **Kubernetes + ArgoCD** ([`ADR-015`](docs/adr/ADR-015-orquestacion-kubernetes-y-gitops.md)). `T-030` hay que corregirla: hoy pide Jaeger. |
| `IN-03`, `IN-04` | `mejoras-y-saas` vs `plan-gtm` | ⚠️ **Ambos son N4 — empate de nivel, la regla es muda.** Escala a Dirección. |
| `IN-07` | `NOT NULL` (N0+N1) vs nullable (N2) | ⚠️ Ganan N0/N1, pero un 0 km no tiene patente ⇒ decisión de negocio + posible enmienda. |
| `IN-13` | 5 años (N1, invoca ley) vs 24 meses (N3) | ⚠️ La regla no zanja una obligación legal externa. **Legal + Tech Lead**. |

> **Regla operativa vigente**: todo desvío de N1 por competencia de dominio **se registra como ADR** en [`docs/adr/`](docs/adr/). Sin ADR es decisión implícita y, por el Principio 5 de la constitución, **no es vinculante**. Nunca resuelvas un `IN-XX` por omisión eligiendo el primer documento que leíste.

Ver [`knowledge-base/10_preguntas_abiertas.md`](knowledge-base/10_preguntas_abiertas.md) §Parte 3 y `SU-12` (validado) en [`knowledge-base/09_decisiones_y_supuestos.md`](knowledge-base/09_decisiones_y_supuestos.md).

---

## Nomenclatura de fases adoptada — resolución de `IN-05`

**Se adoptan las OLAS.** Este documento usa `OLA 0`, `OLA 1.1` … `OLA 1.5` y **no usa `F1`-`F5` en ningún lado**.

**Por qué**: `IN-05` describe dos sistemas de planificación paralelos sin tabla de traducción — Fases F0-F5 con meses de calendario (`mejoras-y-saas`, `historias-usuario`) contra Olas 0-3 (`plan-implementacion`, `plan-gtm`, `plan-seguridad`, `plan-sre`, `plan-testing`). Se eligen las Olas por tres razones:

1. **Son la unidad del documento operativo.** El plan de implementación —la fuente de las 194 tareas que este roadmap ordena— organiza todo en Olas y bloques (1.1 a 1.5). Usar Fases obligaría a traducir cada tarea.
2. **Las usan 5 de los 11 documentos**, contra 2 que usan Fases.
3. **Las Fases traen calendario, y el calendario está roto.** "Fase 1 = meses 4-7" y "Ola 1 = meses 0-6" designan ambos al MVP con ventanas distintas y desplazadas. Las Olas del plan de implementación **no tienen calendario**, así que no arrastran el conflicto.

**Equivalencia declarada** (para leer los documentos que usan Fases):

| Este roadmap | Bloque del plan | Épica del backlog | Etiqueta F equivalente |
|---|---|---|---|
| OLA 0 | Fundación (42 tareas) | transversal | (sin equivalente; precede a F1) |
| OLA 1.1 | Bloque 1.1 — Onboarding | E1 | F1 |
| OLA 1.2 | Bloque 1.2 — Stock | E2 | F1 |
| OLA 1.3 | Bloque 1.3 — Publicación | E3 (parcial) | F1 |
| OLA 1.4 | Bloque 1.4 — CRM | E4 | F1 |
| OLA 1.5 | Bloque 1.5 — WhatsApp | E5 (núcleo) | F1 |

**Lo que sigue abierto**: la numeración `F1`-`F5` de `historias-usuario` queda degradada a **etiqueta de prioridad, no de calendario**. Las **fechas de calendario del MVP siguen sin definir** — es `PA-11`, y depende de `PA-01`.

---

## Mapa de bloqueantes — quién resuelve qué

Las 14 inconsistencias bloqueantes **no tienen un change dedicado**. Cada una está asignada al change que primero necesita la decisión, y se resuelve **al inicio de ese change**.

> **Nota de conteo** (resuelta): al derivar este roadmap se detectó que [`10_preguntas_abiertas.md`](knowledge-base/10_preguntas_abiertas.md) titulaba la Parte 1 como *"BLOQUEANTES (13)"* pero enumeraba **14**, y la Parte 2 decía *"(28)"* enumerando **40** — el mismo patrón de conteos que no cierran que `IN-37` denuncia en el plan de implementación y que `SU-12` explica. **Ya está corregido**: los encabezados dicen 14 y 40, total **54**. Este roadmap trabaja con los 14 bloqueantes enumerados (`IN-01, 02, 03, 04, 05, 06, 07, 10, 12, 13, 22, 23, 29, 31`). En la misma pasada se registraron dos defectos residuales del archivo: `IN-15` e `IN-16` se referencian pero nunca se documentan como entradas, y los IDs `IN-55`/`IN-56` no existen (hueco de numeración).

| Bloqueante | Qué decide | Change que lo resuelve | Ola |
|---|---|---|---|
| `IN-22` | Umbral de cobertura del quality gate: 80 % (constitución) vs 70/60 (plan de testing). Bloquea merges. | **C-01** | 0 |
| `IN-29` | Numeración de ADRs: ADR-002/005/011 significan cosas distintas en la spec y en el plan. Rompe la trazabilidad de las 194 tareas. | **C-01** | 0 |
| 🟡 ~~`IN-01`~~ | ~~Catálogo de roles~~ **DECIDIDO** (`ADR-017`): 3 valores en `user_role_enum` — `manager`, `salesperson`, `admin_staff` — con equivalencia al glosario. C-02 **aplica**, no re-decide. Pendiente ratificar `E-001`. | **C-02** | 0 |
| 🟡 ~~`IN-02`~~ | ~~`super_admin` sin representación~~ **DECIDIDO** (`ADR-017`): tabla `super_admins` aparte, sin `tenant_id`, exenta de RLS. `users.tenant_id` sigue `NOT NULL`. Pendiente ratificar `E-001`. | **C-02** | 0 |
| `IN-13` | Retención de `audit_logs`: 5 años (spec, con invocación legal) vs 24 meses (seguridad + SRE) vs escalonada por plan (GTM). Define el particionado. | **C-03** | 0 |
| `IN-23` | Objetivos de latencia p95: listado 200 vs 300 ms, búsqueda 500 vs 2.000 ms. Define los umbrales de alerta de Prometheus. | **C-03** | 0 |
| `IN-31` | SLA por plan: 99.9/99.9/99.95 (spec) vs 99.0/99.5/99.9 (SRE + GTM). El SLO interno de 99.7 % es **inferior** al SLA que la spec promete — insostenible. | **C-03** | 0 |
| `IN-03` | Límites por plan (usuarios / vehículos / sucursales) + la **cuota de mensajes de WhatsApp que no existe como columna**. Bloquea el seed de `plans` y `PlanLimitsService`. | **C-04** | 0 |
| `IN-04` | Moneda: ARS vs USD. `plans.price_ars` **no tiene columna de moneda**, así que el esquema no puede representar el pricing del GTM. | **C-04** | 0 |
| `IN-06` | `users.password_hash NOT NULL` contra "la aplicación nunca maneja contraseñas" (ADR-007). Define si `/auth/login` es callback OIDC o proxy de credenciales (ROPC). | **C-05** | 0 |
| `IN-12` (a) | `accept-invitation`: `POST /api/v1/users/…` (T-024) vs `POST /auth/…` (T-054) — **contradicción interna del plan**. | **C-05** | 0 |
| `IN-10` | Etapas del pipeline por defecto: 5 vs 6 vs 7 vs 8. Es seed data que corre en el onboarding de **cada tenant**; cambiarla con clientes vivos es una migración de datos. | **C-11** | 1.1 |
| `IN-12` (b) | Borrado de etapa: `DELETE /pipeline/stages/{id}` vs `POST /pipeline/stages/{id}/archive`. | **C-11** | 1.1 |
| `IN-07` | `vehicles.domain_plate` `NOT NULL` (spec + constitución) vs nullable (plan). Un 0 km o una permuta recién recibida **no tienen patente**. | **C-14** | 1.2 |
| `IN-12` (c) | Fusión de contactos: `POST /contacts/merge` vs `POST /contacts/{primary_id}/merge`. | **C-24** | 1.4 |
| `IN-12` (d) | Cierre de lead: `POST /leads/{id}/close` vs `/won` + `/lost`. Completar actividad: `PATCH /activities/{id}/complete` vs `PATCH /activities/{id}`. | **C-26** | 1.4 |
| `IN-05` | Fases vs Olas. **Resuelto en este documento** (ver arriba): se adoptan las Olas. | *(este roadmap)* | — |

**`IN-12` está repartido en cuatro changes a propósito**: son cuatro pares de endpoints divergentes que viven en módulos distintos. Cada change resuelve el suyo y lo escribe en `docs/openapi.yaml`, que es la fuente única desde la que el frontend genera sus tipos.

---

## 🕳️ Riesgos del roadmap — vacíos que ningún documento cubre

Esto **no** son contradicciones entre documentos: es trabajo que **ninguna de las ~19.900 líneas del corpus especifica**. Cada uno necesita que alguien produzca el artefacto antes de que el change que lo consume pueda arrancar.

| # | Vacío | Impacto | Change afectado | Referencia |
|---|---|---|---|---|
| **R-1** | **El contrato de API del portal deRuedas no existe.** Es la integración **más crítica del MVP** —la razón de ser de la épica E3— y ningún documento especifica su API: ni endpoints, ni autenticación, ni esquema de listing, ni códigos de error, ni rate limits. | **Bloqueo duro de C-22 y C-23** (15 tareas, T-115…T-129). `DerRuedasAdapter` (T-117) y el mapping `vehicle→listing` (T-118) son inescribibles sin él. | **C-22** | `PA-25` |
| **R-2** | **No existe la matriz RBAC canónica.** El propio plan de seguridad lo admite. La KB reconstruyó dos vistas parciales —una funcional desde el manual, otra por recurso desde el plan— que **no coinciden entre sí**. | Los tests de autorización son **quality gate bloqueante en CI** según el plan de testing. Sin matriz, no hay contra qué testear. Agravado por `IN-01`/`IN-02`. | **C-02**, **C-05** | `03_actores_y_roles.md` §RBAC |
| **R-3** | **No existe la tabla canónica de variables de entorno.** La de `08_arquitectura_propuesta.md` está **derivada del stack, no transcripta de una fuente**. | Setup de entornos, `.env.example` (T-004), Terraform, secretos de staging (T-008). | **C-01** | `PA-06` |
| **R-4** | **No existe el design system técnico.** El brand book remite a un "design system técnico" que **no está en el corpus**, y los *"13 componentes UI primitivos"* de T-037 **no están enumerados en ningún lado**. | T-036 y T-037 arrancan sin especificación de componentes. Agravado por `IN-44` (contraste AA vs AAA del mismo par de colores) e `IN-45` (el "Rojo crítico" `#974706` es un marrón, visualmente idéntico al "Amarillo atención" `#9C5700`). | **C-07** | `PA-30`, `PA-27` |
| **R-5** | **La marca no tiene tagline.** El brand book estructura *"logo + tagline"* en el footer pero **nunca escribe el texto** en sus 965 líneas. | Layout principal (T-038), piezas de marketing. Bajo impacto técnico. | **C-07** | `IN-58`, `PA-26` |

> **R-1 es el riesgo dominante del MVP.** Recomendación: abrir la conversación con el equipo del portal deRuedas **ahora**, en paralelo con la OLA 0, sin esperar a llegar a C-22. Si el contrato no llega a tiempo, C-22/C-23 se posponen y el MVP sale sin publicación automática — lo que cambia la propuesta de valor.

---

## 🔀 Desvíos respecto del plan de implementación

El orden base es el del plan. Se documentan **todos** los movimientos; no hay reordenamientos silenciosos.

### D-1 — `T-139`…`T-142` (pipeline configurable): de OLA 1.4 (CRM) → OLA 1.1 (Onboarding)

- **Qué se movió**: las cuatro tareas de `pipeline_stages` (migración, seed por defecto, service/endpoints, página de configuración), del bloque 1.4 al 1.1, dentro del change **C-11**.
- **Dependencia que lo fuerza**: la ficha de **T-140 declara dependencia de T-043** (*"Endpoint admin: crear tenant"*, bloque 1.1). El seed del pipeline por defecto **corre durante la creación del tenant**, no durante el CRM. Además `07_flujos_principales.md` §Flujo 2 ubica la configuración inicial del pipeline dentro del onboarding de la agencia.
- **Consecuencia**: el bloqueante `IN-10` (5/6/7/8 etapas) se resuelve en la OLA 1.1, que es donde el seed realmente se ejecuta, y no cuatro changes más tarde.

### D-2 — `T-052` (wizard, paso 4: configuración inicial del pipeline): sigue a `T-139`…`T-142`

- **Qué se movió**: `T-052` sale del change de wizard (**C-10**) y entra en **C-11**, junto al modelo de pipeline.
- **Dependencia que lo fuerza**: el plan le asigna a `T-052` una única dependencia de UI (`T-048`, layout del wizard), pero el paso 4 **renderiza y edita el catálogo de etapas por defecto**, que no existe hasta `T-139`/`T-140`. Construirlo antes obliga a hardcodear una lista de etapas que `IN-10` todavía no definió — exactamente el error que `IN-10` advierte que es caro revertir.
- **Consecuencia**: C-10 entrega los pasos 1, 2, 3 y 5 del wizard; C-11 entrega el paso 4 y lo enchufa. C-11 depende de C-10.

### D-3 — `T-167` (vincular conversación de WhatsApp a lead): de OLA 1.4 (CRM) → OLA 1.5 (WhatsApp)

- **Qué se movió**: `T-167` sale del bloque 1.4 y entra en **C-32**, en la OLA 1.5.
- **Dependencia que lo fuerza**: **la ficha de la propia tarea lo declara**: *"Dependencias: T-146, **T-176** (WhatsApp recepción — declarado como dependencia anticipada de E5)"*. `T-176` es el webhook de recepción, en el bloque 1.5. El plan reconoce el desfase pero deja la tarea en el bloque equivocado.
- **Consecuencia**: ninguna sorpresa a mitad del CRM. C-28 cierra el CRM sin depender de WhatsApp.

### D-4 — `T-059` (`PlanLimitsService`): de OLA 1.1 (Onboarding) → OLA 0 (junto a `plans`)

- **Qué se movió**: `T-059` (detección de límites del plan en hot path) sale del bloque 1.1 y entra en **C-04**, junto a las migraciones de `plans` y `subscriptions`.
- **Dependencia que lo fuerza**: su única dependencia es `T-019` (migración `plans`), y el impacto declarado de `IN-03` los nombra juntos: *"`PlanLimitsService` (T-059) y el seed de la tabla `plans` no se pueden escribir"* sin los números definitivos. Separarlos obliga a resolver `IN-03` dos veces, o a resolverlo en C-04 y esperar dos olas para usarlo.
- **Consecuencia**: `IN-03` e `IN-04` se resuelven una sola vez, en C-04, y el enforcement de límites nace con la tabla que lo define.

### D-5 — `T-013`/`T-014` (`core/auth.py`, `core/rbac.py`): agrupadas con los demás `core/`, no con el módulo de identidad

- **Qué se movió**: quedan en **C-02** (primitivas de backend) en vez de en el change de identidad (**C-05**).
- **Dependencia que lo fuerza**: **T-016 (`core/events.py`) depende de T-013**. Poner `auth.py` en C-05 y `events.py` en C-02 crea una dependencia de C-02 hacia un change posterior — el único ciclo de orden que aparecía en el grafo. Además son literalmente archivos de `backend/app/core/`, igual que `errors.py`, `pagination.py` e `idempotency.py`.
- **Consecuencia**: `IN-01` e `IN-02` se resuelven en C-02, antes de escribir `require_role()`, y C-05 hereda la decisión ya tomada para la migración de `users`.

### D-6 — `T-114` (performance hardening de Stock): agrupada con búsqueda, no al final del bloque

- **Qué se movió**: `T-114` entra en **C-18** (`busqueda-opensearch`) en vez de cerrar la OLA 1.2 después del frontend.
- **Dependencia que lo fuerza**: sus dependencias son `T-080` (listado) y `T-099` (búsqueda) — ambas backend, ninguna frontend. El hardening mide y ajusta los índices y las queries que C-18 acaba de crear; hacerlo tres changes más tarde significa medir sobre código que ya se dio por terminado.
- **Consecuencia**: los objetivos de latencia (`IN-23`, resuelto en C-03) se verifican en el mismo change que los introduce.

### Lo que NO se movió, y por qué

- **El orden de las olas y de los bloques 1.1 → 1.5 se respeta íntegro.** El plan lo justifica y la KB no lo contradice.
- **`T-062` (backoffice de tenants) queda en C-09**, aunque el plan lo lista último del bloque 1.1: sus dependencias (`T-043`, `T-044`, `T-045`) son las tres tareas de admin del mismo change. Agruparlo es cohesión, no reordenamiento.
- **La "cadena de event bus T-040 a T-046"** que declara §3.3 del plan **es incorrecta** (`IN-40`): `T-040` es NextAuth y `T-043`…`T-046` son endpoints de onboarding. La infraestructura real de eventos es `T-016`. Este roadmap ignora esa cadena y usa `T-016` (en C-02) como prerrequisito de toda comunicación asíncrona. No es un desvío de tareas sino la corrección de una referencia rota.

---

## Árbol de dependencias

```
C-01 foundation-setup
├── C-02 core-backend-primitives
│   ├── C-03 observabilidad-y-auditoria-base
│   ├── C-04 tenancy-planes-y-limites
│   │   └── C-05 identidad-auth-y-tenant-endpoints
│   │       ├── C-06 storage-y-notificaciones
│   │       ├── C-08 auth-frontend-y-api-client  (+ C-07)
│   │       ├── C-09 admin-tenants-backoffice
│   │       │   └── C-11 pipeline-configurable   (+ C-10)
│   │       ├── C-10 onboarding-wizard-y-tenant-setup  (+ C-06, C-07, C-08)
│   │       │   └── C-12 usuarios-invitaciones-y-settings
│   │       ├── C-14 vehiculos-modelo-y-servicios  (+ C-13)
│   │       │   ├── C-15 vehiculos-api
│   │       │   │   ├── C-18 busqueda-opensearch
│   │       │   │   │   └── C-19 stock-web-listado-y-detalle  (+ C-08)
│   │       │   │   │       ├── C-21 stock-web-import-y-cierre  (+ C-17, C-20)
│   │       │   │   │       └── C-23 publishing-config-y-seguridad  (+ C-03, C-22)
│   │       │   │   │           └── C-29 whatsapp-canal-y-modelo  (+ C-24)
│   │       │   │   │               └── C-30 whatsapp-mensajeria-core  (+ C-06)
│   │       │   │   │                   ├── C-31 whatsapp-web-inbox-y-templates
│   │       │   │   │                   │   └── C-32 whatsapp-crm-integracion-y-cierre  (+ C-25, C-28)
│   │       │   │   │                   └── ·
│   │       │   │   └── C-20 stock-web-alta-edicion-y-fotos  (+ C-13, C-16)
│   │       │   ├── C-16 fotos-de-vehiculos  (+ C-06)
│   │       │   ├── C-17 importacion-csv-de-stock
│   │       │   └── C-22 publicacion-portal-deruedas          ⚠️ bloqueado por R-1
│   │       └── C-24 contactos-y-deduplicacion  (+ C-06, C-07)
│   │           └── C-25 leads-y-motor-de-pipeline  (+ C-11, C-14)
│   │               └── C-26 leads-api-y-tests
│   │                   └── C-27 crm-web-kanban-y-leads  (+ C-08, C-13)
│   │                       └── C-28 crm-automatizaciones-y-dashboard  (+ C-06)
│   └── C-13 catalogo-de-vehiculos  (+ C-07)
└── C-07 design-system-y-shell-web
```

> `(+ C-NN)` = dependencia adicional fuera de la rama padre. El grafo real es un DAG; el árbol lo aplana por la rama de mayor peso.

### Paralelismo por fase

```
GATE 0: (arranque)
  → C-01 foundation-setup                          [Agente A]

GATE 1: C-01 ✓
  → C-02 core-backend-primitives                   [Agente A]
  → C-07 design-system-y-shell-web                 [Agente C]

GATE 2: C-02 ✓                                                    ← FORK
  → C-03 observabilidad-y-auditoria-base           [Agente B]
  → C-04 tenancy-planes-y-limites                  [Agente A]
  → C-13 catalogo-de-vehiculos                     [Agente C — si C-07 ✓]

GATE 3: C-04 ✓                                                    ← CUELLO DE BOTELLA
  → C-05 identidad-auth-y-tenant-endpoints         [Agente A]
    (nada más se desbloquea hasta que C-05 cierre: es el único
     serializador duro del roadmap — ver "Camino crítico")

GATE 4: C-05 ✓                                                    ← FORK
  → C-06 storage-y-notificaciones                  [Agente B]
  → C-08 auth-frontend-y-api-client                [Agente C — si C-07 ✓]
  → C-09 admin-tenants-backoffice                  [Agente B]
  → C-14 vehiculos-modelo-y-servicios              [Agente A — si C-13 ✓]

GATE 5: C-14 ✓ · C-06 ✓ · C-08 ✓ · C-09 ✓                        ← FORK MAYOR
  → C-10 onboarding-wizard-y-tenant-setup          [Agente C]
  → C-15 vehiculos-api                             [Agente A]
  → C-16 fotos-de-vehiculos                        [Agente B]
  → C-17 importacion-csv-de-stock                  [Agente B]
  → C-22 publicacion-portal-deruedas               [Agente B — ⚠️ solo si R-1 resuelto]
  → C-24 contactos-y-deduplicacion                 [Agente A]

GATE 6: C-15 ✓ · C-10 ✓ · C-16 ✓                                 ← FORK
  → C-11 pipeline-configurable                     [Agente C — si C-09 ✓]
  → C-12 usuarios-invitaciones-y-settings          [Agente C]
  → C-18 busqueda-opensearch                       [Agente A]
  → C-20 stock-web-alta-edicion-y-fotos            [Agente C — si C-13 ✓]

GATE 7: C-18 ✓ · C-11 ✓ · C-24 ✓
  → C-19 stock-web-listado-y-detalle               [Agente C]
  → C-25 leads-y-motor-de-pipeline                 [Agente A]

GATE 8: C-19 ✓ · C-25 ✓ · C-20 ✓ · C-22 ✓
  → C-21 stock-web-import-y-cierre                 [Agente C — si C-17 ✓]
  → C-23 publishing-config-y-seguridad             [Agente B — si C-03 ✓]
  → C-26 leads-api-y-tests                         [Agente A]

GATE 9: C-26 ✓ · C-23 ✓
  → C-27 crm-web-kanban-y-leads                    [Agente C]
  → C-29 whatsapp-canal-y-modelo                   [Agente A]

GATE 10: C-27 ✓ · C-29 ✓
  → C-28 crm-automatizaciones-y-dashboard          [Agente B]
  → C-30 whatsapp-mensajeria-core                  [Agente A]

GATE 11: C-30 ✓
  → C-31 whatsapp-web-inbox-y-templates            [Agente C]

GATE 12: C-31 ✓ · C-28 ✓ · C-25 ✓
  → C-32 whatsapp-crm-integracion-y-cierre         [Agente A]  → MVP lanzable
```

### Camino crítico (13 changes — mínimo irreducible)

```
C-01 → C-02 → C-04 → C-05 → C-14 → C-15 → C-18 → C-19 → C-23 → C-29 → C-30 → C-31 → C-32
```

**13 de 32 changes · 86 de 194 tareas.** Ningún paralelismo acorta esta cadena: los 19 changes restantes caben en los huecos.

Tres observaciones sobre la cadena:

- **C-05 es el único serializador duro.** En GATE 3 no hay nada que hacer en paralelo: los tres agentes convergen y esperan. Es el mejor candidato a subdividirse internamente (sus 7 tareas se pueden repartir: `T-021` tenancy, `T-022`/`T-023`/`T-024` usuarios, `T-025`/`T-026` Keycloak, `T-027` tests).
- **La cadena atraviesa `C-23`**, que arrastra `C-22` — es decir, **el camino crítico pasa por el riesgo R-1**. Si el contrato del portal deRuedas no llega, el camino crítico se corta a la altura de GATE 8. Mitigación: sacar `C-23`→`C-29` del camino resolviendo `T-126` (cifrado de API keys) antes, dentro de `C-03`.
- **Termina en WhatsApp** porque la OLA 1.5 es la última del MVP y su cadena interna (canal → mensajería → inbox → integración) es estrictamente secuencial.

### Plan óptimo con 3 agentes

| Paso | Agente A (Backend Core) | Agente B (Backend Aux / Infra) | Agente C (Frontend) |
|---|---|---|---|
| 1 | **C-01** foundation-setup | — | — |
| 2 | **C-02** core-backend-primitives | — | **C-07** design-system-y-shell-web |
| 3 | **C-04** tenancy-planes-y-limites | **C-03** observabilidad-y-auditoria | **C-13** catalogo-de-vehiculos |
| 4 | **C-05** identidad-auth-y-tenant-endpoints | — ⚠️ | — ⚠️ |
| 5 | **C-14** vehiculos-modelo-y-servicios | **C-06** storage-y-notificaciones | **C-08** auth-frontend-y-api-client |
| 6 | **C-15** vehiculos-api | **C-09** admin-tenants-backoffice | **C-10** onboarding-wizard |
| 7 | **C-17** importacion-csv-de-stock | **C-16** fotos-de-vehiculos | **C-12** usuarios-invitaciones-y-settings |
| 8 | **C-24** contactos-y-deduplicacion | **C-22** publicacion-portal-deruedas ⚠️ | **C-11** pipeline-configurable |
| 9 | **C-18** busqueda-opensearch | — | **C-20** stock-web-alta-edicion-y-fotos |
| 10 | **C-25** leads-y-motor-de-pipeline | — | **C-19** stock-web-listado-y-detalle |
| 11 | **C-26** leads-api-y-tests | **C-23** publishing-config-y-seguridad | **C-21** stock-web-import-y-cierre |
| 12 | **C-29** whatsapp-canal-y-modelo | — | **C-27** crm-web-kanban-y-leads |
| 13 | **C-30** whatsapp-mensajeria-core | **C-28** crm-automatizaciones-y-dashboard | — |
| 14 | — | — | **C-31** whatsapp-web-inbox-y-templates |
| 15 | **C-32** whatsapp-crm-integracion-y-cierre | — | — |

**Paso 4 es el cuello de botella** (⚠️): B y C quedan sin trabajo desbloqueado. Aprovechalo para el trabajo humano que el roadmap no puede hacer solo: abrir la **enmienda del Art. 8 para `IN-01`** (`PA-01` ya está cerrada por `ADR-000`), conseguir el contrato del portal (**R-1**), redactar la matriz RBAC (**R-2**) y enumerar los primitivos del design system (**R-4**).

**Pasos 9, 10, 12 y 14-15**: los huecos de B y C son el momento de subdividir el change del agente A o de adelantar documentación y runbooks.

---

## OLA 0 — Fundación

> 42 tareas (`T-001`…`T-042`) + `T-059` traído desde el bloque 1.1 (ver **D-4**). Es prerrequisito de absolutamente todo lo demás.
> C-02, C-04 y C-05 son la cadena de auth y tenancy que §3.3 del plan declara crítica: *"toda tarea posterior asume que esto funciona"*.

### [C-01] `foundation-setup`
- **Estado**: `[~]` **en curso — 60 de 83 tareas** (actualizado 14-ago-2026, tarea 10.5)
  - ✅ **Bloques 1-8**: reubicación documental, monorepo §4.1, Docker Compose, contrato de configuración, bootstrap de FastAPI, Alembic, frontend Next.js y pipeline de CI. `T-001`, `T-002`, `T-004`, `T-005`, `T-006`, `T-007` cerradas; `T-003` en 7 de 9.
  - ⛔ **Bloque 9 (`T-008`, 16 tareas) — bloqueado.** `ADR-015` fijó Kubernetes + ArgoCD pero **no el proveedor cloud**: dice *"AWS o GCP"*. El Terraform de uno y del otro no comparten casi nada, así que `infra/terraform/staging/` no se puede escribir sin esa decisión. **Decisión pendiente de Dirección.**
  - 🔲 **Bloque 10 (cierre)**: `10.4` y `10.5` hechas. `10.1`, `10.2` y `10.3` abiertas.
  - **C-01 no se puede archivar todavía**: la auditoría de la tarea 10.3 encontró que `platform/delivery-pipeline` tiene **4 de 15 escenarios** con test ejecutable y `platform/configuration` **8 de 10**. Solo `platform/service-health` está entera (10/10). Archivar promovería a spec vigente un contrato sin verificación.
  - Detalle y evidencia por tarea en [`openspec/changes/foundation-setup/tasks.md`](openspec/changes/foundation-setup/tasks.md).
- **Rango**: `T-001` … `T-008` (8 tareas)
- **Scope**:
  - Monorepo con la estructura canónica vinculante de §4.1 del plan: `backend/`, `frontend-web/`, `frontend-mobile/`, `frontend-admin/`, `docs/adr/`, `docs/runbooks/`, `docs/openapi.yaml`, `.github/workflows/`
  - `docker-compose.yml` con el entorno local completo: PostgreSQL 16, Redis 7, OpenSearch, Keycloak, MinIO (S3-compatible) — más `docker-compose.test.yml` con contenedores efímeros para CI
  - `.env.example` + `config.py` con Pydantic Settings (**ver R-3: no existe tabla canónica de variables de entorno; hay que producirla en este change**)
  - Bootstrap de `backend/app/main.py` (FastAPI) y del frontend Next.js 14 con App Router + Tailwind
  - Alembic configurado con migración inicial vacía; convención `NNN_descripcion.py` correlativa
  - `ci.yml`: lint (ruff, mypy, eslint) + tests + **quality gate de cobertura** — el umbral sale de resolver `IN-22`
  - `deploy-staging.yml` con despliegue automático
  - Tests: smoke de arranque de ambos servicios; el pipeline debe correr verde end-to-end
- **Dependencias**: ninguna
- **Governance**: **ALTO** — fija el quality gate que bloquea todos los merges del proyecto y la estructura de repositorio que §4.1 declara vinculante (cambiarla después exige un ADR). Proponer y esperar revisión antes de escribir.
- **Bloqueantes a resolver (al inicio del change)**: ✅ **los dos cerrados** — `IN-22` por [`ADR-014`](docs/adr/ADR-014-umbrales-de-cobertura.md), `IN-29` por [`ADR-018`](docs/adr/ADR-018-anclas-de-adr-del-plan-de-implementacion.md). Texto original abajo, como registro de qué se decidió y contra qué.
  - **`IN-22`** — umbral de cobertura. La constitución (Art. 2, vinculante) exige **80 % de líneas**; el plan de testing fija **70 % líneas / 60 % branches**; la spec técnica dice 80 % core / 70 % resto. **Hoy el CI está especificado en violación de la norma vinculante del proyecto.** O se enmienda formalmente la constitución (Art. 8) o el plan de testing sube a 80. No se puede escribir `ci.yml` sin este número.
  - **`IN-29`** — numeración de ADRs. `ADR-002`, `ADR-005` y `ADR-011` significan cosas distintas en la spec y en el plan (ej.: T-098 dice *"anclada en ADR-005"*, que es **OpenSearch** en el plan y **React Native** en la spec). La constitución (Principio 5) exige que los ADRs sean vinculantes y trazables; con dos numeraciones esa trazabilidad no existe para las 194 tareas. Fijar la numeración de la spec como canónica y corregir las anclas antes de sembrar `docs/adr/`.
- **Riesgos**: ~~**R-3**~~ (tabla de variables de entorno inexistente) — ✅ **cerrado** por [`ADR-013`](docs/adr/ADR-013-variables-de-entorno.md): 35 variables en 12 grupos, sostenidas por `tools/check-config-parity.py` con 0 divergencias entre el ADR, `.env.example` y `Settings`.
- **Leer antes**:
  - `docs/sdd/deRuedas-plan-implementacion.md` §4 (estructura canónica del repositorio — vinculante)
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Variables de entorno, §Infraestructura y despliegue
  - `knowledge-base/11_testing_y_calidad.md` §Umbrales de cobertura, §Quality gates del pipeline `pr-validation`
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico
  - `knowledge-base/09_decisiones_y_supuestos.md` §Parte A (principios constitucionales), `DD-01`…`DD-03`

### [C-02] `core-backend-primitives`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-009`, `T-010`, `T-012`, `T-013`, `T-014`, `T-015`, `T-016`, `T-032`, `T-033` (9 tareas) — ver **D-5**
- **Scope**:
  - Migración de extensiones PostgreSQL (`uuid-ossp`, `pg_trgm`, `unaccent`, `btree_gin`)
  - `db/session.py` con **tenant context**: `SET LOCAL app.current_tenant_id` por request — es el mecanismo sobre el que se apoya toda la RLS (ADR-006)
  - `core/errors.py`: jerarquía `DomainError` + handlers con respuestas **RFC 7807** (`application/problem+json`)
  - `core/auth.py`: dependency `get_current_user` (validación de JWT de Keycloak, extracción de `tenant_id` y rol)
  - `core/rbac.py`: `require_role(...)` y `require_permission(...)` — **enumera el catálogo de roles: no se puede escribir sin `IN-01`/`IN-02`**
  - `core/pagination.py` (cursor-based) + `core/idempotency.py` (header `Idempotency-Key`)
  - `core/events.py`: publisher y consumer base sobre **Redis Streams** (ADR-009) — es la infraestructura real del event bus, no `T-040`…`T-046` (`IN-40`)
  - `tests/conftest.py` con fixtures comunes + factories `factory_boy` de las entidades base
  - Tests: aislamiento de tenant context entre requests concurrentes; publicación y consumo de un evento de prueba; formato RFC 7807 de los errores
- **Dependencias**: `C-01`
- **Governance**: **CRÍTICO** — `db/session.py` es el control de aislamiento multi-tenant, que `12_seguridad_y_compliance.md` califica como *el control más crítico del sistema*. `rbac.py` es el mecanismo de autorización. Solo análisis y propuesta; **no escribir código sin aprobación humana explícita**.
- **Bloqueantes a resolver (al inicio del change)**:
  - **`IN-01`** — catálogo de roles. Cinco documentos discrepan: 3 roles en español (constitución, vinculante), 3 en inglés sin `super_admin` (spec `user_role_enum`), **4** (plan de implementación T-014, plan de seguridad, plan de testing), 5 personas (historias de usuario). `require_role()` los enumera literalmente. Resolución propuesta por la KB: adoptar los 4 en inglés con equivalencia documentada, y enmendar el glosario constitucional.
  - **`IN-02`** — `super_admin` no es representable. La spec define 11 endpoints bajo `/admin/api/v1` para un rol que **no existe en `user_role_enum`**, y `users.tenant_id` es `FK NOT NULL` mientras que un `super_admin` de deRuedas no pertenece a ningún tenant. Hay que elegir: (a) cuarto valor del enum con `tenant_id` nullable, (b) tabla `super_admins` aparte —el plan de testing ya la menciona en su lista de tablas exentas de RLS, evidencia indirecta a favor—, o (c) solo rol de Keycloak sin fila en `users`. La decisión condiciona `rbac.py`, la migración de `users` (C-05) y todo C-09.
- **Riesgos**: **R-2** (no existe matriz RBAC canónica — `rbac.py` se escribe sin especificación de permisos por recurso).
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos, §Cómo se aplica la autorización, §Reglas estructurales de identidad
  - `knowledge-base/02_descripcion_general.md` §Multi-tenancy (ADR-006), §Comunicación entre módulos (3 patrones), §API REST — convenciones
  - `knowledge-base/05_reglas_de_negocio.md` §RN-MT (multi-tenancy), §RN-AU (autenticación y autorización)
  - `knowledge-base/09_decisiones_y_supuestos.md` `DD-06` (RLS), `DD-09` (Redis Streams + Celery)
  - `knowledge-base/12_seguridad_y_compliance.md` §Aislamiento multi-tenant, §Autorización

### [C-03] `observabilidad-y-auditoria-base`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-011`, `T-028`, `T-029`, `T-030`, `T-031` (5 tareas)
- **Scope**:
  - Migración `audit_logs` **particionada por mes** — la política de particionado y el volumen a proyectar dependen de `IN-13`
  - Logging estructurado JSON con `trace_id` propagado por request
  - Middleware de métricas Prometheus: `http_requests_total`, `http_request_duration_seconds` (histograma) por endpoint y tenant
  - Tracing distribuido con OpenTelemetry exportando a **Tempo** — decidido por [`ADR-016`](docs/adr/ADR-016-trazas-distribuidas-tempo.md), cierra `IN-15`. ⚠️ **`T-030` está mal especificada**: pide levantar el servicio `jaeger` en `docker-compose` con UI en `:16686` y verificar la traza en la Jaeger UI. Pasa a Tempo, y la verificación se hace desde Grafana. Corregir al arrancar el change.
  - Sentry para error tracking, con scrubbing de PII
  - Umbrales de alerta (`APILatencyHigh` y compañía) derivados de la resolución de `IN-23`
  - Tests: que el `trace_id` sobreviva a un salto de evento por Redis Streams; que las métricas expongan la etiqueta de tenant sin filtrar datos entre tenants
- **Dependencias**: `C-01`, `C-02`
- **Governance**: **ALTO** — define el audit trail (evidencia de compliance) y los umbrales de alerta que gobiernan la operación. Proponer y esperar revisión.
- **Bloqueantes a resolver (al inicio del change)**:
  - **`IN-13`** — retención de `audit_logs`: **5 años** (spec §3.9, §6.5 y §8.8, repetido tres veces con justificación contable) vs **24 meses** (plan de seguridad §6.4 y plan de SRE §4) vs **escalonada por plan** (GTM: Starter 30 días / Pro 12 meses / Enterprise 24 meses). Triple impacto: particionado y storage a 5 años; una afirmación de **compliance legal** que el propio documento de compliance contradice; y el GTM convirtiendo la auditoría en feature comercial, incompatible con un mínimo legal uniforme. **Un mínimo legal no puede ser un feature de plan** — lo que sí puede variar por plan es cuánto histórico ve el cliente en la UI. Hay una pregunta legal previa (¿aplica la Resolución 4717/2020 de AFIP a `audit_logs`?).
  - **`IN-23`** — objetivos de latencia p95. Listado: **200 ms** (constitución Art. 4 + spec) vs **300 ms** (SRE + testing). Búsqueda full-text: **500 ms** (constitución + spec) vs **2.000 ms** (SRE + testing) — el plan de SRE es **4× más permisivo que la norma vinculante**. Define los umbrales de Prometheus, los thresholds de k6/Locust y la Definición de Terminado de las historias. La KB sugiere que son dos cosas distintas nunca escritas como tales: **objetivo de ingeniería** (constitución/spec) vs **SLO comprometido con presupuesto de error** (SRE). Decidir y documentar la relación.
  - ✅ ~~**`IN-31`**~~ — **RESUELTO** por `ADR-000`: **99.0 / 99.5 / 99.9**, por competencia de dominio de SRE. C-03 lo aplica, no lo re-decide. El análisis original se conserva abajo porque explica *por qué* la escala de SRE es la única internamente coherente. SLA de disponibilidad por plan: **99.9 / 99.9 / 99.95** (spec §6.2 y §9.7) vs **99.0 / 99.5 / 99.9** (SRE §3.1 + GTM). Es un compromiso contractual con créditos económicos (5 %, 10 %, 25 % de la suscripción). Para Starter la diferencia es **43 minutos vs 7h12min** de downtime mensual aceptable. Y el **SLO interno del SRE (99.7 %) es inferior al SLA que la spec le promete a Starter y Pro (99.9 %)** — matemáticamente insostenible: nunca se promete un SLA por encima del SLO interno. La escala del SRE/GTM es la única internamente coherente.
- **Leer antes**:
  - `knowledge-base/13_observabilidad_y_sre.md` §SLAs públicos por plan, §SLOs internos, §Presupuesto de error, §Stack de observabilidad, §Catálogo de alertas
  - `knowledge-base/12_seguridad_y_compliance.md` §Auditoría, §Tabla de retenciones, §Protección de datos personales
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AD (auditoría), §RN-PF (performance)
  - `knowledge-base/04_modelo_de_datos.md` §Convenciones generales
  - `knowledge-base/09_decisiones_y_supuestos.md` §Parte A (Art. 4 de la constitución)

### [C-04] `tenancy-planes-y-limites`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-017`, `T-018`, `T-019`, `T-020`, `T-059` (5 tareas) — ver **D-4**
- **Scope**:
  - Migración `tenants`: `id`, `name`, `slug`, `cuit`, `billing_email`, `status`, `plan_id` (FK temporal NULL hasta T-019), `trial_ends_at`, `timezone`, `locale`, `settings`, timestamps, `deleted_at`
  - Migración `branches` (sucursales) con FK a `tenants`
  - Migración `plans` + `subscriptions`; resuelve la FK pendiente `tenants.plan_id → plans.id`
  - **Seed de `plans`** con los límites definitivos por plan — inescribible sin `IN-03`
  - Módulo `tenancy`: schemas Pydantic, repository, service
  - `PlanLimitsService` en hot path: `assert_can_add_user`, `assert_can_add_vehicle`, `assert_can_add_branch`
  - Tests: que superar el límite del plan devuelva `402`/`403` con problem+json; que un tenant no vea las sucursales de otro
- **Dependencias**: `C-02`
- **Governance**: **CRÍTICO** — `tenants` es la entidad raíz que toda otra tabla referencia vía `tenant_id`, y `plans`/`subscriptions` son datos de facturación. Solo análisis; no escribir sin aprobación.
- **Bloqueantes a resolver (al inicio del change)**:
  - **`IN-03`** — límites cuantitativos por plan. `mejoras-y-saas` §10 y `plan-gtm` §3.2 discrepan en casi todas las celdas: vehículos Starter **30 vs 80**, usuarios Pro **6 vs 5**, vehículos Pro **100 vs 300**, Enterprise **ilimitado vs 15 usuarios / 5 sucursales** (ver también `IN-50`). Y el GTM introduce una dimensión que **no existe en el modelo de datos**: cuota de mensajes de WhatsApp por mes (1.500 / 5.000 / 20.000) — `plans` no tiene columna para eso. Sin números no hay seed ni `PlanLimitsService`. Si se adopta el GTM, **agregar `max_whatsapp_messages_month` a `plans`** (lo consume C-29/C-30).
  - **`IN-04`** — moneda de facturación: **ARS 45.000 / 95.000 / 195.000** (`mejoras-y-saas` §10, reforzado en §13 con cláusulas de actualización por CER/IPC) vs **USD 49 / 149 / 399** (`plan-gtm` §3.2, más usuario extra y excedente de WhatsApp en USD). Pero `spec-tecnica` §3.3 define `plans.price_ars numeric(18,2) NOT NULL` y `subscriptions.amount_ars` — **sin columna de moneda**, contradiciendo su propia convención de §3.1 (*"la moneda como columna asociada (ARS, USD)"*). **El esquema no puede representar el pricing del GTM.** Y a un tipo de cambio razonable USD 49 y ARS 45.000 no son el mismo precio: son propuestas comerciales distintas, no una conversión. Si es USD: renombrar a `price_amount` + `price_currency` y aplicar el mismo criterio a `subscriptions`, `vehicles.price_ars`/`price_usd` y todos los campos `*_ars` del esquema (afecta C-14).
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Dominio Auth y Tenancy, §Convenciones generales, §Seed data inicial
  - `knowledge-base/14_pricing_y_gtm.md` §Advertencia previa, §Versión A, §Versión B
  - `knowledge-base/05_reglas_de_negocio.md` §RN-PL (planes y límites), §RN-MT
  - `knowledge-base/02_descripcion_general.md` §Multi-tenancy (ADR-006)
  - `knowledge-base/01_vision_y_objetivos.md` §Alcance del MVP

### [C-05] `identidad-auth-y-tenant-endpoints`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-021`, `T-022`, `T-023`, `T-024`, `T-025`, `T-026`, `T-027` (7 tareas)
- **Scope**:
  - Migración `users` + `user_branches` (N:M usuario↔sucursal) con `user_role_enum` — la forma del enum sale de `IN-01`/`IN-02` (resueltos en C-02) y la columna `password_hash` de `IN-06`
  - Módulo `users`: schemas, repository, service (invitación, aceptación, desactivación)
  - Endpoints `users` — incluye `accept-invitation`, cuyo path resuelve `IN-12(a)`
  - Endpoints `tenancy`: gestión de sucursales y configuración del tenant
  - Endpoints de auth: `login`, `refresh`, `logout`, `me` — su naturaleza (callback OIDC vs proxy de credenciales) sale de `IN-06`
  - Realm de Keycloak configurado + sincronización bidireccional de usuarios (ADR-007)
  - **Tests críticos de aislamiento multi-tenant** (`T-027`) — quality gate bloqueante según el plan de testing
- **Dependencias**: `C-01`, `C-02`, `C-04`
- **Governance**: **CRÍTICO** — es el dominio de autenticación y autorización completo. Solo análisis y propuesta; ningún código sin aprobación humana explícita.
- **Bloqueantes a resolver (al inicio del change)**:
  - **`IN-06`** — `users.password_hash NOT NULL`. `spec-tecnica` §3.3 define la columna (*"hash argon2id"*), pero §8.3 y ADR-007 dicen que la autenticación **se delega íntegramente a Keycloak** y que *"la aplicación nunca maneja contraseñas"*; el plan de seguridad confirma que el hash argon2id vive **en Keycloak**. Sin embargo spec §4.2.1 y el plan definen `POST /api/v1/auth/login` como endpoint propio. Decide dos cosas: (a) si `users` lleva `password_hash`, y (b) si el login es **redirect OIDC (Authorization Code + PKCE)** o **proxy de credenciales (ROPC)** —este último desaconsejado y en vías de deprecación en OAuth 2.1—. Resolución propuesta: eliminar la columna, tratar `users` como espejo local del usuario de Keycloak, y definir `/auth/login` como callback OIDC.
  - **`IN-12(a)`** — `accept-invitation` tiene **dos paths en el mismo documento**: `POST /api/v1/users/accept-invitation` (T-024) y `POST /auth/accept-invitation` (T-054, que consume C-12). Distinto prefijo y distinto namespace. Es una contradicción interna del plan de implementación. Elegir uno y escribirlo en `docs/openapi.yaml` — de ahí el frontend genera sus tipos.
  - *Heredados de C-02, ya decididos*: `IN-01` (catálogo de roles) e `IN-02` (`super_admin`) determinan el `CREATE TYPE user_role_enum` y la nulabilidad de `users.tenant_id` de este change. **No re-decidir: aplicar.**
- **Riesgos**: **R-2** (matriz RBAC canónica inexistente — los tests de autorización de `T-027` no tienen especificación contra la cual escribirse).
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` (completo — incluye la advertencia previa sobre el catálogo de roles)
  - `knowledge-base/07_flujos_principales.md` §Flujo 1 — Autenticación y sesión
  - `knowledge-base/05_reglas_de_negocio.md` §RN-AU, §RN-MT
  - `knowledge-base/12_seguridad_y_compliance.md` §Autenticación, §Autorización, §Aislamiento multi-tenant
  - `knowledge-base/11_testing_y_calidad.md` §Pruebas críticas de aislamiento multi-tenant, §Pruebas de autorización (RBAC)

### [C-06] `storage-y-notificaciones`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-034`, `T-035` (2 tareas)
- **Scope**:
  - Adapter de object storage S3-compatible (ADR-008): `put`, `get`, `delete`, URLs prefirmadas, layout de claves por tenant
  - Módulo `notifications`: canal in-app + email base, plantillas, consumo de eventos de dominio desde Redis Streams
  - Tests: que las claves de storage no permitan cruzar tenants; que una notificación se dispare desde un evento publicado
- **Dependencias**: `C-01`, `C-02`, `C-05`
- **Governance**: **MEDIO** — servicios compartidos con estado; el layout de claves de storage tiene implicancia de aislamiento.
- **Bloqueantes a resolver**: ninguno.
- **Nota**: change chico pero habilitante — desbloquea C-16 (fotos), C-30 (adjuntos) y todas las notificaciones de C-10, C-24 y C-28.
- **Leer antes**:
  - `knowledge-base/09_decisiones_y_supuestos.md` `DD-08` (ADR-008: object storage), `DD-09` (ADR-009: eventos)
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados
  - `knowledge-base/02_descripcion_general.md` §Comunicación entre módulos, §Integraciones externas
  - `knowledge-base/05_reglas_de_negocio.md` §RN-DP (datos y privacidad)

### [C-07] `design-system-y-shell-web`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-036`, `T-037`, `T-038` (3 tareas)
- **Scope**:
  - Design tokens + configuración de Tailwind derivados del brand book: paleta, tipografía, escala jerárquica, espaciado
  - Los **13 componentes UI primitivos** (**R-4: no están enumerados en ningún documento — hay que definir la lista en este change**)
  - Layout principal: navegación, sidebar, header, breadcrumbs, slots de contenido
  - Accesibilidad: contraste verificado, foco visible, navegación por teclado, atajos del producto
  - Tests: snapshot de los primitivos; auditoría de contraste automatizada
- **Dependencias**: `C-01`
- **Governance**: **BAJO** — capa de presentación sin lógica crítica. Autonomía completa si los tests pasan.
- **Bloqueantes a resolver**: ninguno de los 14 bloqueantes.
- **Riesgos**: **R-4** (no existe design system técnico ni la lista de primitivos), **R-5** (la marca no tiene tagline y el layout lo asume en el footer).
- **No bloqueantes que igual hay que decidir acá**: `IN-44` (el brand book dice **AA** en §5.6 y **AAA** en §6.4.4 sobre el mismo par de colores) e `IN-45` (**el "Rojo crítico" `#974706` no es rojo** — es un marrón anaranjado, visualmente casi idéntico al "Amarillo atención" `#9C5700`, lo que rompe la regla del propio documento de tener un color distinto por estado; muy probablemente un error de transcripción del `.docx`). Los dos colores funcionales de error y advertencia **no se pueden distinguir**: verificar contra la fuente antes de cablearlos en los tokens.
- **Leer antes**:
  - `knowledge-base/15_marca_y_ux.md` (completo — §Paleta de colores, §Tipografía, §Componentes UI, §Accesibilidad, §Navegación del producto)
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios (frontend)
  - `knowledge-base/06_funcionalidades.md` §Atajos de teclado (producto web), §Definición de terminado
  - `knowledge-base/09_decisiones_y_supuestos.md` `DD-04` (ADR-004: Next.js 14)

### [C-08] `auth-frontend-y-api-client`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-039`, `T-040`, `T-041`, `T-042` (4 tareas)
- **Scope**:
  - Cliente API tipado con TanStack Query, generado desde `docs/openapi.yaml`; interceptor de refresh de token; manejo de `problem+json`
  - NextAuth conectado al realm de Keycloak (OIDC) — el flujo concreto depende de cómo se haya resuelto `IN-06` en C-05
  - Página de login + recuperación de contraseña
  - Dashboard placeholder y middleware de rutas protegidas por rol
  - Tests: que una ruta protegida redirija sin sesión; que el refresh de token no dispare un bucle
- **Dependencias**: `C-01`, `C-05`, `C-07`
- **Governance**: **ALTO** — es el manejo de sesión y tokens del cliente. Proponer y esperar revisión antes de escribir.
- **Bloqueantes a resolver**: ninguno propio; **aplica** la resolución de `IN-06` tomada en C-05 (si el login es callback OIDC, esta capa no toca contraseñas nunca).
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 1 — Autenticación y sesión
  - `knowledge-base/03_actores_y_roles.md` §Cómo se aplica la autorización, §Rutas públicas (sin autenticación)
  - `knowledge-base/02_descripcion_general.md` §API REST — convenciones
  - `knowledge-base/12_seguridad_y_compliance.md` §Autenticación
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad

---

## OLA 1.1 — Onboarding y configuración de tenant

> Épica E1. Rango nativo `T-043`…`T-062` menos `T-059` (movido a C-04, **D-4**), más `T-139`…`T-142` traídas desde el bloque 1.4 (**D-1**).
> C-09, C-10 y C-12 pueden avanzar en paralelo con toda la OLA 1.2 una vez cerrado C-05.

### [C-09] `admin-tenants-backoffice`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-043`, `T-044`, `T-045`, `T-062` (4 tareas)
- **Scope**:
  - `POST /admin/api/v1/tenants` — alta de tenant, creación del realm/grupo en Keycloak, usuario `manager` inicial, disparo del seed
  - `PATCH /admin/api/v1/tenants/{id}/plan` — cambio de plan con revalidación de límites contra el uso actual
  - `POST /admin/api/v1/tenants/{id}/suspend` y `/reactivate`
  - Backoffice: página de tenants con listado, filtros, detalle y acciones
  - Tests: que los endpoints `/admin` rechacen a cualquier rol que no sea `super_admin`; que bajar de plan con uso por encima del nuevo límite falle con un error explícito
- **Dependencias**: `C-04`, `C-05`
- **Governance**: **ALTO** — controla el ciclo de vida de la cuenta del cliente; suspender un tenant corta el acceso a sus datos. Proponer y esperar revisión.
- **Bloqueantes a resolver**: ninguno propio. **Aplica** `IN-02` (resuelto en C-02): si `super_admin` terminó siendo tabla aparte o rol solo-Keycloak, la protección de estos 11 endpoints se implementa distinto.
- **No bloqueante relevante**: `IN-14` — **¿existe signup público self-service?** El plan de implementación lo declara *"postergado"* y el plan de seguridad dice *"NO existe en MVP; las cuentas se crean por invitación"*, pero `plan-gtm` §9.2 vende el onboarding de Starter como **"self-service"** con trial de 14 días sin tarjeta. **El GTM está vendiendo un funnel que el MVP no implementa** (`PA-12`). Si la respuesta es que sí existe, este change crece.
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 2 — Onboarding de una agencia nueva
  - `knowledge-base/06_funcionalidades.md` §Épica 12 — Administración y soporte (deRuedas)
  - `knowledge-base/03_actores_y_roles.md` §Actores del sistema
  - `knowledge-base/05_reglas_de_negocio.md` §RN-PL (planes y límites), §RN-MT
  - `knowledge-base/14_pricing_y_gtm.md` §Onboarding y adopción, §Cobranza y morosidad

### [C-10] `onboarding-wizard-y-tenant-setup`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-046`, `T-047`, `T-048`, `T-049`, `T-050`, `T-051`, `T-053`, `T-058`, `T-060` (9 tareas) — sin `T-052`, ver **D-2**
- **Scope**:
  - `OnboardingService.complete` + `POST /api/v1/onboarding/complete`
  - Layout del wizard con progreso persistente y reanudable
  - Paso 1 — datos de la agencia (nombre comercial, razón social, CUIT, dirección, contacto, logo)
  - Paso 2 — alta de sucursales
  - Paso 3 — invitación de usuarios con asignación de rol y sucursales
  - Paso 5 — finalización y marcado de onboarding completo
  - Badge persistente *"complete su onboarding"* mientras esté incompleto
  - Notificación de bienvenida al completar
  - Tests E2E parciales: retomar el wizard a mitad de camino sin perder estado
- **Dependencias**: `C-04`, `C-05`, `C-06`, `C-07`, `C-08`
- **Governance**: **MEDIO** — flujo con estado y máquina de progreso; implementar por pasos y exponer las decisiones no obvias.
- **Bloqueantes a resolver**: ninguno de los 14.
- **No bloqueantes relevantes**: `IN-26` (el wizard tiene **4 pasos** según `historias-usuario` HU-E1-002 y **5** según el plan; el manual §2.2 lista 5 *campos* que probablemente sean el paso 1 — las tres fuentes están confundidas) e `IN-21` (**trial de 14 vs 30 días**, que impacta `tenants.trial_ends_at` y toda la cadencia comercial del GTM). El paso 4 (pipeline) llega en C-11.
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 2 — Onboarding de una agencia nueva
  - `knowledge-base/06_funcionalidades.md` §Épica 1 — Onboarding y configuración (8 HU)
  - `knowledge-base/04_modelo_de_datos.md` §Dominio Auth y Tenancy
  - `knowledge-base/15_marca_y_ux.md` §Tono de voz, §Vocabulario controlado (obligatorio)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-MT, §RN-PL

### [C-11] `pipeline-configurable`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-052`, `T-139`, `T-140`, `T-141`, `T-142` (5 tareas) — movidas desde el bloque 1.4, ver **D-1** y **D-2**
- **Scope**:
  - Migración `pipeline_stages` (`tenant_id`, `name`, `position`, `is_won`, `is_lost`, `deleted_at`)
  - **Seed del pipeline por defecto al crear el tenant** — el catálogo de etapas sale de `IN-10`
  - Repository + service + endpoints de etapas: crear, renombrar, reordenar, archivar/eliminar (`IN-12(b)`)
  - Página de configuración del pipeline con reordenamiento
  - Paso 4 del wizard de onboarding: configuración inicial del pipeline
  - Tests: que no se pueda archivar una etapa `is_won`/`is_lost`; que reordenar mantenga `position` consistente; que el seed corra exactamente una vez por tenant
- **Dependencias**: `C-05`, `C-07`, `C-09`, `C-10`
- **Governance**: **MEDIO** — es seed data que corre para **cada tenant nuevo** y define la máquina de estados del CRM. Implementar con checkpoints.
- **Bloqueantes a resolver (al inicio del change)**:
  - **`IN-10`** — cuántas etapas trae el pipeline por defecto y cómo se llaman. **Cuatro respuestas**: **5** sin nombrar (constitución + `historias-usuario` HU-E1-007), **6** nombradas (plan T-140: `Nuevo`, `Contactado`, `En negociación`, `Permuta/Test drive`, `Ganado`, `Perdido`), **7** nombradas (`manual-usuario` §2.5 y §13.1: `Nuevo`, `Calificado`, `Visita programada`, `Negociación`, `Acuerdo`, `Ganado`, `Perdido`) y **8** en prosa (`mejoras-y-saas` §7.2). Es seed data del onboarding de cada tenant: **cambiarla con clientes vivos es una migración de datos con leads ya distribuidos entre etapas**. Además el manual —lo que el cliente ya lee— documenta las 7.
  - **`IN-12(b)`** — borrado de etapa: `DELETE /pipeline/stages/{id}` (spec) vs `POST /pipeline/stages/{id}/archive` (plan). No es estilo: una borra y la otra preserva el histórico de leads que pasaron por esa etapa.
- **No bloqueante que conviene decidir**: `IN-24` — **el pipeline configurable en el MVP tensiona el Principio 2 de la constitución**, que usa *exactamente este caso* como ejemplo de lo que no hay que hacer (*"hacer que el pipeline tenga etapas configurables desde el día uno"*). Pero el glosario de la misma constitución define el pipeline como *"configurables"* y `historias-usuario` lo ubica en F2. Si se implementa igual (que es lo que hace el plan), hace falta **justificación documentada** (`PA-21`).
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §`lead_status_enum` y pipeline, §Seed data inicial
  - `knowledge-base/05_reglas_de_negocio.md` §RN-CR (CRM y pipeline)
  - `knowledge-base/07_flujos_principales.md` §Flujo 5 — Ciclo de vida de un lead
  - `knowledge-base/06_funcionalidades.md` §Épica 4 — CRM y pipeline comercial
  - `knowledge-base/09_decisiones_y_supuestos.md` §Parte A (Principio 2)

### [C-12] `usuarios-invitaciones-y-settings`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-054`, `T-055`, `T-056`, `T-057`, `T-061` (5 tareas)
- **Scope**:
  - Página pública de aceptación de invitación (sin sesión) — consume el path que C-05 fijó al resolver `IN-12(a)`
  - Página de configuración de la agencia
  - Página de gestión de sucursales
  - Página de gestión de usuarios: invitar, cambiar rol, asignar sucursales, desactivar
  - **Test E2E del flujo completo de onboarding** (`T-061`): alta de tenant → wizard → invitación → aceptación → primer login
- **Dependencias**: `C-05`, `C-07`, `C-10`
- **Governance**: **MEDIO** — la gestión de roles desde la UI es superficie de autorización, aunque el enforcement viva en el backend.
- **Bloqueantes a resolver**: ninguno propio; **aplica** `IN-12(a)` (path de `accept-invitation`, resuelto en C-05). Si el frontend y el backend no coinciden acá, el E2E de `T-061` falla.
- **Riesgos**: **R-2** — la página de gestión de usuarios expone los roles al cliente final sin una matriz RBAC canónica que diga qué puede hacer cada uno.
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos, §Rutas públicas
  - `knowledge-base/06_funcionalidades.md` §Épica 1 — Onboarding y configuración
  - `knowledge-base/07_flujos_principales.md` §Flujo 2 — Onboarding de una agencia nueva
  - `knowledge-base/11_testing_y_calidad.md` §Tipos de prueba (10), §Definition of Done — tarea
  - `knowledge-base/15_marca_y_ux.md` §Navegación del producto

---

## OLA 1.2 — Stock de vehículos

> Épica E2. `T-063`…`T-114` (52 tareas). Es el bloque más grande del MVP y **prerrequisito de CRM y de publicación** según §3.3 del plan.
> C-13 puede arrancar apenas cierren C-02 y C-07, muy antes que el resto de la ola.

### [C-13] `catalogo-de-vehiculos`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-063` … `T-070` (8 tareas)
- **Scope**:
  - Migraciones `vehicle_brands`, `vehicle_models` (FK a brands), `vehicle_versions` y `trims` — **catálogo cross-tenant**, exento de RLS
  - Seed inicial: marcas + modelos top del mercado argentino
  - Repository y service de catálogos con cache
  - Endpoints públicos de catálogos (lectura, sin tenant)
  - Backoffice de gestión del catálogo (`super_admin`)
  - Componente de selector en cascada `brand → model → version`
  - Tests: que las tablas de catálogo sean legibles por todos los tenants y escribibles por ninguno; cascada del selector
- **Dependencias**: `C-02`, `C-07`
- **Governance**: **BAJO** — catálogo de referencia, cross-tenant y de solo lectura para los tenants. Autonomía completa si los tests pasan.
- **Bloqueantes a resolver**: ninguno.
- **Nota de aislamiento**: son de las pocas tablas **sin `tenant_id`**. Documentar explícitamente su exención de RLS junto a `audit_logs` y —según cómo se resuelva `IN-02`— `super_admins`, para que los tests de aislamiento de C-05 no las marquen como falso positivo.
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Dominio Stock, §Seed data inicial, §Convenciones generales
  - `knowledge-base/06_funcionalidades.md` §Épica 2 — Gestión de stock (10 HU)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-ST (stock / vehículos)
  - `knowledge-base/02_descripcion_general.md` §Multi-tenancy (ADR-006)

### [C-14] `vehiculos-modelo-y-servicios`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-071`…`T-077`, `T-084`, `T-086` (9 tareas)
- **Scope**:
  - Migración `vehicles` + enums asociados (`vehicle_status_enum`, condición, combustible, transmisión) — **`domain_plate` nullable o no sale de `IN-07`**
  - `VehicleRepository` (CRUD) + schemas Pydantic de Vehicle
  - `VehicleService.create` → evento `vehicle.created`; `.update` → `vehicle.updated`
  - `VehicleService.transition_status` con **máquina de estados** validada
  - `VehicleService.soft_delete` (archivar) + evento
  - Migración `vehicle_status_history` (auditoría de cambios de estado)
  - Validadores del dominio argentino: **patente** (formatos viejo `AAA000` y Mercosur `AA000AA`) y número de chasis
  - Tests: transiciones inválidas rechazadas; unicidad de dominio por tenant; que cada mutación emita su evento
- **Dependencias**: `C-02`, `C-04`, `C-05`, `C-13`
- **Governance**: **ALTO** — `vehicles` es la entidad central que CRM, publicación y permutas referencian, y la máquina de estados gobierna el ciclo comercial. Proponer y esperar revisión.
- **Bloqueantes a resolver (al inicio del change)**:
  - **`IN-07`** — `vehicles.domain_plate` **`NOT NULL`** (`spec-tecnica` §3.4, reforzado por el glosario constitucional: *"un vehículo se identifica unívocamente dentro de un tenant por su dominio"*) vs **nullable** (plan T-071) vs *"patente **o** chasis (opcional)"* (`manual-usuario` §2.7.1). Es una columna `NOT NULL` en una migración: no se puede escribir sin decidir. Y hay un caso de negocio real detrás: **un 0 km o un usado recién recibido en permuta todavía no tiene patente**, lo que sugiere que la spec está equivocada. Resolución propuesta: nullable, con índice `UNIQUE (tenant_id, domain_plate) WHERE deleted_at IS NULL AND domain_plate IS NOT NULL` y un `CHECK (domain_plate IS NOT NULL OR chassis_number IS NOT NULL)`.
  - *Heredado de C-04*: si `IN-04` se resolvió en USD, los campos `vehicles.price_ars`/`price_usd` se renombran acá con el mismo criterio uniforme.
- **No bloqueante relevante**: `IN-11` — los estados del vehículo no coinciden: **6** en spec y plan (`available`, `reserved`, `sold`, `in_workshop`, `in_preparation`, `archived`), **5** en `historias-usuario` HU-E2-004 (sin `archived`), **5 distintos** en `manual-usuario` §4.2.3 (sin `en taller`, con `Pausado`). `Pausado` es casi seguro el **estado de publicación**, no del vehículo — el manual confunde ambos conceptos. El manual además agrega una regla que no está en ningún otro documento: *"la reserva se libera automáticamente a los 7 días"*. Decidir si esa regla existe **antes** de escribir la máquina de estados.
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Dominio Stock, §`vehicle_status_enum`, §Validadores específicos del dominio argentino
  - `knowledge-base/05_reglas_de_negocio.md` §RN-ST (stock / vehículos)
  - `knowledge-base/07_flujos_principales.md` §Flujo 3 — Alta de vehículo y publicación automática
  - `knowledge-base/06_funcionalidades.md` §Épica 2 — Gestión de stock
  - `knowledge-base/02_descripcion_general.md` §Comunicación entre módulos (eventos de dominio)

### [C-15] `vehiculos-api`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-078`…`T-083`, `T-085`, `T-087` (8 tareas)
- **Scope**:
  - `POST /api/v1/vehicles` (con `Idempotency-Key`), `PATCH /api/v1/vehicles/{id}`, `DELETE /api/v1/vehicles/{id}` (archivar)
  - `GET /api/v1/vehicles` — listado con filtros, orden y paginación por cursor
  - `GET /api/v1/vehicles/{id}` y `GET /api/v1/vehicles/{id}/history`
  - `POST /api/v1/vehicles/{id}/status` — transición de estado
  - **Tests de integración de todos los endpoints de stock core** (`T-087`), incluyendo aislamiento entre tenants
- **Dependencias**: `C-02`, `C-14`
- **Governance**: **MEDIO** — superficie de API sobre una entidad central; el enforcement de límites de plan (`PlanLimitsService`) se engancha en el `POST`.
- **Bloqueantes a resolver**: ninguno propio. **Aplica** `IN-23` (resuelto en C-03) para los objetivos de latencia del listado.
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §API REST — convenciones, §Endpoints principales por dominio
  - `knowledge-base/04_modelo_de_datos.md` §Dominio Stock
  - `knowledge-base/05_reglas_de_negocio.md` §RN-ST, §RN-PL (límites de plan)
  - `knowledge-base/11_testing_y_calidad.md` §Pruebas críticas de aislamiento multi-tenant
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Vista por recurso

### [C-16] `fotos-de-vehiculos`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-088` … `T-092` (5 tareas)
- **Scope**:
  - Migración `vehicle_photos` (`position`, `is_cover`, metadatos, claves de storage)
  - `PhotoService.upload` con **resize automático** a múltiples tamaños y validación de tipo/peso
  - `PhotoService.delete` y `.reorder`
  - `POST /api/v1/vehicles/{id}/photos`, `DELETE` de foto y `PATCH` de reorder
  - Tests: que el resize genere todas las variantes; que las claves de storage estén namespaceadas por tenant
- **Dependencias**: `C-06`, `C-14`
- **Governance**: **MEDIO** — subida de archivos con procesamiento; superficie de validación de entrada.
- **Bloqueantes a resolver**: ninguno de los 14.
- **No bloqueante que hay que decidir acá**: `IN-09` — **límite de fotos por vehículo, con cuatro valores**: hasta **20** (`mejoras-y-saas` §7.1 y `historias-usuario` HU-E2-002), máx. **30** (plan de implementación), *"entre 4 y 12"* (`manual-usuario` §2.7.1), *"entre 8 y 15"* (§10.2), *"mínimo 8-10"* (§12.3) — **el manual se contradice a sí mismo tres veces**. Hay que separar el **límite duro del sistema** (20 o 30, es una validación en código) de la **recomendación de buena práctica** (que es texto de UI). Ver `PA-16`.
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Dominio Stock
  - `knowledge-base/05_reglas_de_negocio.md` §RN-ST
  - `knowledge-base/07_flujos_principales.md` §Flujo 3 — Alta de vehículo y publicación automática
  - `knowledge-base/09_decisiones_y_supuestos.md` `DD-08` (ADR-008: object storage)
  - `knowledge-base/06_funcionalidades.md` §Épica 2 — Gestión de stock

### [C-17] `importacion-csv-de-stock`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-093` … `T-097` (5 tareas)
- **Scope**:
  - Migración `imports` + `ImportService.parse_csv` con validación fila a fila y reporte de errores por línea
  - `ImportService.execute` en background con **Celery**, con progreso y resumen
  - `POST /api/v1/vehicles/import` y `GET /api/v1/imports/{id}`
  - Template de CSV descargable + endpoint
  - Tests: import parcialmente inválido que no deja el lote a medias; que el enforcement de límites de plan aplique al total importado, no fila por fila
- **Dependencias**: `C-14`
- **Governance**: **MEDIO** — escritura masiva con procesamiento asíncrono; un import mal validado corrompe el stock del cliente.
- **Bloqueantes a resolver**: ninguno propio; **aplica** `IN-07` (si `domain_plate` quedó opcional, el validador del CSV tiene que aceptar filas sin patente pero con chasis).
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 4 — Importación masiva de stock (CSV)
  - `knowledge-base/04_modelo_de_datos.md` §Dominio Stock, §Validadores específicos del dominio argentino
  - `knowledge-base/05_reglas_de_negocio.md` §RN-ST, §RN-PL
  - `knowledge-base/06_funcionalidades.md` §Épica 2 — Gestión de stock
  - `knowledge-base/09_decisiones_y_supuestos.md` `DD-09` (ADR-009: Celery)

### [C-18] `busqueda-opensearch`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-098`, `T-099`, `T-100`, `T-114` (4 tareas) — ver **D-6**
- **Scope**:
  - Índice de OpenSearch para `vehicles` + sincronización dirigida por eventos de dominio (`vehicle.created/updated/deleted`), con reindex completo como fallback
  - `GET /api/v1/vehicles/search` — full-text con facetas y filtros
  - Endpoint de search-as-you-type (autocomplete)
  - **Performance hardening del módulo Stock**: índices de PostgreSQL, análisis de planes de query, caché
  - Tests: que el índice nunca devuelva documentos de otro tenant; consistencia eventual tras un update; tests de carga contra los objetivos de latencia
- **Dependencias**: `C-14`, `C-15`
- **Governance**: **ALTO** — infraestructura de búsqueda con una copia de los datos **fuera de PostgreSQL**, o sea fuera del alcance de la RLS. El filtro por tenant pasa a ser responsabilidad exclusiva de la aplicación.
- **Bloqueantes a resolver**: ninguno propio. **Aplica** `IN-23` (resuelto en C-03) — y este es el caso más filoso: **búsqueda full-text p95 < 500 ms (constitución + spec) vs < 2.000 ms (SRE + testing)**, mientras el propio plan de implementación fija objetivos *aún más estrictos* (`vehicle search` p95 < 150 ms, `suggest` p95 < 50 ms). `T-114` no se puede dar por terminada sin saber contra qué número se mide.
- **No bloqueante**: `IN-29` — las fichas `T-098`/`T-099` se anclan a *"ADR-005"*, que en la spec es **React Native**. El ADR de OpenSearch es `ADR-011` (`DD-11`). Corregir las anclas (ya decidido en C-01).
- **Leer antes**:
  - `knowledge-base/09_decisiones_y_supuestos.md` `DD-11` (ADR-011: OpenSearch)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-PF (performance), §RN-ST
  - `knowledge-base/02_descripcion_general.md` §Arquitectura general, §Capacidad y escalado objetivo
  - `knowledge-base/13_observabilidad_y_sre.md` §SLOs internos, §Capacidad y escalado
  - `knowledge-base/11_testing_y_calidad.md` §Pruebas de performance

### [C-19] `stock-web-listado-y-detalle`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-101`, `T-102`, `T-103`, `T-110`, `T-111` (5 tareas)
- **Scope**:
  - Página de listado de stock: tabla con filtros, orden, paginación y acciones masivas
  - `VehicleCard` — vista grid alternativa
  - Página de detalle de vehículo
  - Barra de búsqueda global con quick search (consume el autocomplete de C-18)
  - `VehicleStatusBadge` + `StatusTransitionModal` con las transiciones válidas
- **Dependencias**: `C-07`, `C-08`, `C-15`, `C-18`
- **Governance**: **BAJO** — presentación sobre endpoints ya validados. Autonomía completa si los tests pasan.
- **Bloqueantes a resolver**: ninguno.
- **No bloqueante**: `IN-11` (los badges de estado deben usar el enum canónico de 6 valores decidido en C-14, no los 5 del manual) e `IN-43` (**umbral de "stock antiguo": 90 días en `manual-usuario` §4.4 y 60 días en §8.2.5** — contradicción interna del manual que define el filtro y la alerta de esta pantalla).
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 2 — Gestión de stock, §Atajos de teclado (producto web)
  - `knowledge-base/15_marca_y_ux.md` §Componentes UI, §Navegación del producto, §Vocabulario controlado
  - `knowledge-base/04_modelo_de_datos.md` §`vehicle_status_enum`
  - `knowledge-base/05_reglas_de_negocio.md` §RN-ST
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Vista funcional

### [C-20] `stock-web-alta-edicion-y-fotos`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-104`, `T-105`, `T-106`, `T-107` (4 tareas)
- **Scope**:
  - Página de alta de vehículo con el selector en cascada de C-13 y subida de fotos integrada
  - Página de edición
  - `PhotoUploader` con drag & drop, progreso y previsualización
  - `PhotoGallery` con reordenamiento y selección de portada
  - Tests: alta completa con fotos; validación del dominio argentino en el cliente coherente con la del backend
- **Dependencias**: `C-07`, `C-13`, `C-15`, `C-16`
- **Governance**: **BAJO** — formularios sobre endpoints validados.
- **Bloqueantes a resolver**: ninguno; **aplica** `IN-07` (si `domain_plate` es opcional, el formulario exige "patente **o** chasis") e `IN-09` (el uploader necesita el límite duro de fotos, decidido en C-16).
- **No bloqueante**: `IN-47` — el botón se llama *"Nuevo vehículo"* en `historias-usuario` HU-E2-001 y *"Agregar vehículo"* en `manual-usuario` §2.7.1. Trivial salvo por un detalle: el manual es lo que lee el cliente y las historias son los criterios de aceptación de los tests E2E de C-21.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §Épica 2 — Gestión de stock
  - `knowledge-base/04_modelo_de_datos.md` §Validadores específicos del dominio argentino, §Dominio Stock
  - `knowledge-base/15_marca_y_ux.md` §Componentes UI, §Vocabulario controlado (obligatorio)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-ST
  - `knowledge-base/07_flujos_principales.md` §Flujo 3 — Alta de vehículo

### [C-21] `stock-web-import-y-cierre`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-108`, `T-109`, `T-112`, `T-113` (4 tareas)
- **Scope**:
  - Página de importación CSV: subida, previsualización de errores por fila, progreso del job
  - Vista de imports recientes con su resultado
  - **Tests E2E del flujo completo de stock** (`T-112`): alta → fotos → edición → cambio de estado → import
  - Documentación de uso del módulo Stock para usuarios finales
- **Dependencias**: `C-17`, `C-19`, `C-20`
- **Governance**: **BAJO** — UI y documentación sobre funcionalidad ya cerrada.
- **Bloqueantes a resolver**: ninguno.
- **Nota**: `T-113` documenta para el usuario final. Alinear el vocabulario con `manual-usuario`, teniendo presentes `IN-47` (nombre del botón), `IN-11` (nombres de estados) e `IN-43` (umbral de stock antiguo) para no propagar las contradicciones a la documentación del cliente.
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 4 — Importación masiva de stock (CSV)
  - `knowledge-base/11_testing_y_calidad.md` §Pirámide de testing, §Tipos de prueba (10), §Definition of Done — tarea
  - `knowledge-base/06_funcionalidades.md` §Épica 2, §Definición de terminado
  - `knowledge-base/15_marca_y_ux.md` §Tono de voz, §Vocabulario controlado

---

## OLA 1.3 — Publicación al portal deRuedas

> Épica E3 (parcial). `T-115`…`T-129` (15 tareas). Conectores a MercadoLibre y Facebook Marketplace **quedan fuera del MVP** (pospuestos a Ola 2 por §3.2 del plan).
>
> ⚠️ **Toda esta ola está bloqueada por R-1**: el contrato de la API del portal deRuedas **no existe en ningún documento del corpus**. Es la integración más crítica del MVP y la razón de ser de la épica. **No arranques C-22 sin él.**

### [C-22] `publicacion-portal-deruedas`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-115`…`T-122`, `T-128`, `T-129` (10 tareas)
- **Scope**:
  - Migración `vehicle_publications` (estado por canal, `external_id`, timestamps de sincronización, último error)
  - `PublishingService` orquestador (agnóstico del canal, para admitir ML/Facebook en Ola 2)
  - **`DerRuedasAdapter`** — cliente HTTP del portal ⚠️ **R-1**
  - **`DerRuedasPublisher`** con mapping `vehicle → listing` ⚠️ **R-1**
  - Consumer de eventos `vehicle.*` → publicación automática (alta, actualización, pausa, baja)
  - `GET /api/v1/vehicles/{id}/publications` y `POST .../publications/republish`
  - **Backoff exponencial + DLQ + alerta** del módulo
  - Reconciliación periódica con el portal (detección de divergencias)
  - Documentación: contrato de la API deRuedas + runbook operativo
- **Dependencias**: `C-14`
- **Governance**: **ALTO** — integración con un sistema externo que publica el stock del cliente de cara al público. Un mapping mal hecho publica precios o datos equivocados en el portal. Proponer y esperar revisión.
- **Bloqueantes a resolver**: ninguno de los 14 `IN-XX`.
- **Riesgo dominante — R-1 (`PA-25`)**: **el contrato exacto del conector con el portal deRuedas no está especificado en ninguno de los 11 documentos.** Faltan: endpoints, método de autenticación, esquema del listing, códigos de error, política de rate limit, semántica de idempotencia y comportamiento ante republicación. `T-117` y `T-118` son literalmente inescribibles sin esto. **Acción previa obligatoria**: obtener el contrato del equipo del portal y versionarlo en `docs/` antes de proponer el change. Nótese que `T-129` pide *documentar* el contrato — pero documentar no es lo mismo que definirlo, y definirlo no le corresponde a este equipo en soledad.
  - **Plan de contingencia**: si el contrato no llega, C-22 y C-23 se posponen y el MVP sale **sin publicación automática**. Eso cambia la propuesta de valor del producto y hay que decidirlo con Dirección, no absorberlo como deuda técnica.
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-PU (publicación)
  - `knowledge-base/07_flujos_principales.md` §Flujo 3 — Alta de vehículo y publicación automática
  - `knowledge-base/06_funcionalidades.md` §Épica 3 — Publicación multicanal (6 HU)
  - `knowledge-base/02_descripcion_general.md` §Integraciones externas, §Comunicación entre módulos
  - `knowledge-base/10_preguntas_abiertas.md` §Parte 3 (`PA-25`)

### [C-23] `publishing-config-y-seguridad`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-123` … `T-127` (5 tareas)
- **Scope**:
  - Página de configuración del conector deRuedas en settings (credenciales, modo automático/manual, mapeo de sucursales)
  - `PublicationBadge` + panel de publicaciones en el detalle del vehículo
  - Test E2E del flujo de publishing
  - **Cifrado de las API keys de integraciones** en reposo (envelope encryption, sin claves en claro en la base ni en logs)
  - Métricas y alertas del módulo publishing (tasa de error, latencia, profundidad de la DLQ)
- **Dependencias**: `C-03`, `C-07`, `C-19`, `C-22`
- **Governance**: **ALTO** — maneja credenciales de terceros. `T-126` es el mecanismo de cifrado que después reutiliza el canal de WhatsApp (C-29). Proponer y esperar revisión.
- **Bloqueantes a resolver**: ninguno propio; **aplica** `IN-23`/`IN-31` (C-03) para los umbrales de las alertas de este módulo.
- **Nota de camino crítico**: `T-126` (cifrado de API keys) es lo que **C-29 realmente necesita** de este change. Si C-22 se demora por R-1, considerá adelantar `T-126` a C-03 para sacar la OLA 1.5 de detrás del riesgo del portal.
- **Leer antes**:
  - `knowledge-base/12_seguridad_y_compliance.md` §Cifrado, §Gestión de personal y accesos
  - `knowledge-base/05_reglas_de_negocio.md` §RN-PU (publicación)
  - `knowledge-base/13_observabilidad_y_sre.md` §Catálogo de alertas, §Runbooks
  - `knowledge-base/06_funcionalidades.md` §Épica 3 — Publicación multicanal
  - `knowledge-base/15_marca_y_ux.md` §Componentes UI

---

## OLA 1.4 — CRM y pipeline comercial

> Épica E4. Rango nativo `T-130`…`T-169`, menos `T-139`…`T-142` (movidas a C-11, **D-1**) y menos `T-167` (movida a C-32, **D-3**).
> Es el flujo comercial central del producto: `07_flujos_principales.md` §Flujo 5.

### [C-24] `contactos-y-deduplicacion`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-130` … `T-138` (9 tareas)
- **Scope**:
  - Migración `contacts` con normalización de teléfono a E.164 y constraints de unicidad
  - `ContactRepository` + schemas + service
  - `ContactService.merge` — **de-duplicación** con reasignación de leads, actividades y conversaciones al contacto primario
  - Detección de duplicados al crear (por teléfono y por documento)
  - Endpoints de contactos, incluido el de merge (`IN-12(c)`)
  - Frontend: listado, detalle/edición, modal de merge con previsualización del resultado
  - Notificación: contacto asignado al usuario
  - Tests: que el merge no pierda relaciones; unicidad respetada tras un borrado lógico
- **Dependencias**: `C-05`, `C-06`, `C-07`
- **Governance**: **MEDIO** — el merge es una operación destructiva sobre datos personales de clientes. Implementar con checkpoints y exponer las decisiones de resolución de conflictos.
- **Bloqueantes a resolver (al inicio del change)**:
  - **`IN-12(c)`** — fusión de contactos: `POST /contacts/merge` (spec) vs `POST /contacts/{primary_id}/merge` (plan). Elegir y fijar en `docs/openapi.yaml`.
- **No bloqueante importante**: `IN-57` — **constraints de unicidad divergentes**. La spec define `UNIQUE (tenant_id, primary_phone)` **sin** `WHERE deleted_at IS NULL`, más `UNIQUE (tenant_id, document_number, document_type) WHERE document_number IS NOT NULL`; el plan define solo `UNIQUE (tenant_id, phone) WHERE deleted_at IS NULL`, **sin la unicidad por documento**. Sin el `WHERE deleted_at IS NULL`, **un contacto borrado lógicamente bloquea para siempre la reutilización de su teléfono — es un bug latente**. Y la constitución exige desduplicar *"por número telefónico **o** documento"*, lo que respalda la versión de la spec. Conviene resolverlo con el mismo rigor que un bloqueante: es una migración.
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Dominio CRM
  - `knowledge-base/05_reglas_de_negocio.md` §RN-CR (CRM y pipeline), §RN-DP (datos y privacidad)
  - `knowledge-base/07_flujos_principales.md` §Flujo 5 — Ciclo de vida de un lead, §Flujo 12 — Ejercicio de derechos del titular (Ley 25.326)
  - `knowledge-base/06_funcionalidades.md` §Épica 4 — CRM y pipeline comercial (11 HU)
  - `knowledge-base/12_seguridad_y_compliance.md` §Protección de datos personales

### [C-25] `leads-y-motor-de-pipeline`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-143` … `T-150` (8 tareas)
- **Scope**:
  - Migración `leads` + `lead_stage_history`; migración `lead_activities` + `loss_reasons`
  - `LeadRepository` + schemas + filtros compuestos (etapa, vendedor, sucursal, vehículo, antigüedad)
  - `LeadService.create` con **auto-asignación** de vendedor (round-robin o regla configurada) + evento
  - `LeadService.transition_stage` con registro de histórico + evento
  - `LeadService.assign` / `.reassign` **con auditoría** de quién reasignó y por qué
  - `LeadActivityService` completo (llamada, visita, test drive, nota, tarea con vencimiento)
  - `LeadService.close_won` y `.close_lost` con motivo de pérdida
  - Tests: transiciones respetando las etapas configuradas del tenant; que el histórico registre toda transición; auto-asignación determinista bajo concurrencia
- **Dependencias**: `C-02`, `C-11`, `C-14`, `C-24`
- **Governance**: **ALTO** — máquina de estados del flujo comercial y auditoría de asignación (afecta comisiones de vendedores). Proponer y esperar revisión.
- **Bloqueantes a resolver**: ninguno propio; **aplica** `IN-10` (las etapas por las que transiciona salen de C-11) e `IN-12(d)` (la semántica de cierre se fija en C-26, pero los servicios `close_won`/`close_lost` se escriben acá — coordinar).
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 5 — Ciclo de vida de un lead (el flujo comercial central), §Flujo 9 — Cierre de operación de venta
  - `knowledge-base/04_modelo_de_datos.md` §Dominio CRM, §`lead_status_enum` y pipeline
  - `knowledge-base/05_reglas_de_negocio.md` §RN-CR
  - `knowledge-base/06_funcionalidades.md` §Épica 4 — CRM y pipeline comercial
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Vista por recurso (visibilidad de leads por rol)

### [C-26] `leads-api-y-tests`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-151`, `T-152`, `T-153`, `T-160`, `T-169` (5 tareas)
- **Scope**:
  - Endpoints de leads: CRUD + transiciones de etapa + asignación + cierre (`IN-12(d)`)
  - Endpoints de actividades (`IN-12(d)`)
  - Endpoints de `loss_reasons` (catálogo por tenant)
  - Tests unitarios y de integración del CRM core
  - **Tests de aislamiento multi-tenant en CRM** (`T-169`) — quality gate bloqueante
- **Dependencias**: `C-25`
- **Governance**: **MEDIO** — superficie de API sobre servicios ya validados, con enforcement de visibilidad por rol.
- **Bloqueantes a resolver (al inicio del change)**:
  - **`IN-12(d)`** — dos pares divergentes: **cierre de lead**, `POST /leads/{id}/close` con payload polimórfico (spec) vs `POST /leads/{id}/won` **y** `POST /leads/{id}/lost` (plan); y **completar actividad**, `PATCH /activities/{id}/complete` (spec) vs `PATCH /activities/{id}` (plan). La spec técnica es la fuente vinculante de contratos de API (§1.1 lo declara), pero `won`/`lost` separados es mejor diseño —evita el payload polimórfico— y es lo que el plan implementa. Decidir explícitamente y actualizar `docs/openapi.yaml`, del que el frontend de C-27 genera sus tipos.
- **Leer antes**:
  - `knowledge-base/02_descripcion_general.md` §API REST — convenciones, §Endpoints principales por dominio
  - `knowledge-base/05_reglas_de_negocio.md` §RN-CR
  - `knowledge-base/11_testing_y_calidad.md` §Pruebas críticas de aislamiento multi-tenant, §Pruebas de autorización (RBAC)
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Vista por recurso
  - `knowledge-base/04_modelo_de_datos.md` §Dominio CRM

### [C-27] `crm-web-kanban-y-leads`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-154` … `T-159` (6 tareas)
- **Scope**:
  - **Kanban del pipeline con drag & drop** entre etapas, con actualización optimista y rollback ante error
  - Detalle de lead con timeline de actividades y cambios de etapa
  - Formulario de actividad
  - Listado de leads alternativo al kanban (tabla con filtros)
  - Formulario de creación de lead (con el selector de vehículo de C-13)
  - Agenda diaria de actividades del vendedor
- **Dependencias**: `C-07`, `C-08`, `C-13`, `C-26`
- **Governance**: **BAJO** — presentación sobre endpoints validados. El drag & drop es UX, no autorización.
- **Bloqueantes a resolver**: ninguno; el kanban renderiza las etapas configuradas del tenant (`IN-10`, resuelto en C-11) y consume los endpoints fijados por `IN-12(d)` en C-26.
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 5 — Ciclo de vida de un lead
  - `knowledge-base/06_funcionalidades.md` §Épica 4 — CRM y pipeline comercial, §Atajos de teclado
  - `knowledge-base/15_marca_y_ux.md` §Componentes UI, §Navegación del producto, §Vocabulario controlado
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Vista funcional
  - `knowledge-base/04_modelo_de_datos.md` §`lead_status_enum` y pipeline

### [C-28] `crm-automatizaciones-y-dashboard`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-161`…`T-166`, `T-168` (7 tareas)
- **Scope**:
  - Consumer `lead.won` → transición automática del vehículo a `sold` (cierra el lazo entre CRM y Stock)
  - Notificación: actividad próxima a vencer (cron)
  - Notificación: lead idle sin actividad (cron diario)
  - `PipelineSummaryService`: métricas por vendedor, por etapa, tasa de conversión, tiempo por etapa
  - Endpoints de dashboard CRM
  - Dashboard CRM con widgets
  - **Tests E2E del flujo completo de CRM** (`T-168`)
- **Dependencias**: `C-06`, `C-07`, `C-14`, `C-25`, `C-27`
- **Governance**: **MEDIO** — automatizaciones que mutan estado sin intervención humana (`lead.won` cambia el estado de un vehículo). Implementar con checkpoints.
- **Bloqueantes a resolver**: ninguno de los 14.
- **No bloqueante que hay que decidir acá**: `IN-20` — **el umbral de "lead sin atención" tiene cuatro valores**: **3 días** (`historias-usuario` HU-E4-006 y `mejoras-y-saas` §7.2), **5 días** configurable con cron a las 9:00 (plan de implementación), **24 horas** (`manual-usuario` §4.4) y **48 horas** (§4.4 vs §5.3 — **contradicción interna del manual**). La KB observa que probablemente sean **dos conceptos distintos mezclados**: *lead nuevo sin primer contacto* (24-48 h) y *lead sin actividad en su etapa* (3-5 días). Ningún documento los distingue. Definirlos como **dos alertas separadas** antes de escribir los crons (`PA-17`).
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 5 — Ciclo de vida de un lead, §Flujo 9 — Cierre de operación de venta
  - `knowledge-base/05_reglas_de_negocio.md` §RN-CR, §RN-ST (transición a `sold`)
  - `knowledge-base/06_funcionalidades.md` §Épica 4 — CRM y pipeline comercial
  - `knowledge-base/01_vision_y_objetivos.md` §Métricas de éxito
  - `knowledge-base/11_testing_y_calidad.md` §Tipos de prueba (10)

---

## OLA 1.5 — Mensajería y WhatsApp Business

> Épica E5 (núcleo). `T-170`…`T-194` + `T-167` traída desde el bloque 1.4 (**D-3**). 26 tareas.
> Quedan fuera del MVP: chatbots conversacionales avanzados, calificación automática con IA y multi-número por sucursal (§3.2 del plan).
> La cadena interna es estrictamente secuencial (canal → mensajería → inbox → integración), por eso cierra el camino crítico.

### [C-29] `whatsapp-canal-y-modelo`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-170` … `T-175` (6 tareas)
- **Scope**:
  - Migración `whatsapp_channels` (credenciales cifradas con el mecanismo de `T-126`, número, `phone_number_id`, estado de verificación)
  - Migración `conversations` + `messages` con índice único de conversación abierta por contacto
  - Migración `whatsapp_templates` (nombre, categoría, idioma, estado de aprobación de Meta)
  - `WhatsAppCloudAdapter` — cliente de la Meta Cloud API directa, **sin BSP** (ADR-010)
  - `ConversationRepository` + `MessageRepository`
  - Schemas de conversaciones y mensajes
  - Tests: que las credenciales nunca se serialicen; unicidad de conversación abierta bajo concurrencia
- **Dependencias**: `C-05`, `C-23`, `C-24`
- **Governance**: **ALTO** — credenciales de un canal externo y datos personales de conversaciones con clientes finales. Proponer y esperar revisión.
- **Bloqueantes a resolver**: ninguno propio. **Aplica** `IN-03` (si se adoptó la cuota de mensajes del GTM, `max_whatsapp_messages_month` tiene que existir en `plans` desde C-04 y el enforcement se engancha acá).
- **No bloqueante que hay que decidir acá**: `IN-51` — **`conversation_status_enum`**: la spec define `open | snoozed | closed` con índice único `WHERE status != 'closed'`; el plan define `open | closed` con índice único `WHERE status = 'open'`. **Con tres estados los dos índices no son equivalentes**: una conversación `snoozed` sería única bajo la regla de la spec pero no bajo la del plan. Es una migración con un índice parcial: decidir antes de escribirla.
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Dominio Communication, §`conversation_status_enum`, §`message_status_enum`
  - `knowledge-base/09_decisiones_y_supuestos.md` `DD-10` (ADR-010: WhatsApp Cloud API directa, sin BSP)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-WA (mensajería / WhatsApp)
  - `knowledge-base/12_seguridad_y_compliance.md` §Cifrado, §Protección de datos personales
  - `knowledge-base/06_funcionalidades.md` §Épica 5 — Mensajería y WhatsApp Business (8 HU)

### [C-30] `whatsapp-mensajeria-core`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-176`…`T-180`, `T-187`, `T-189`, `T-191`, `T-192`, `T-193` (10 tareas)
- **Scope**:
  - **Webhook** de recepción de mensajes y status updates, con verificación de firma de Meta y respuesta idempotente
  - `ConversationService.upsert_from_webhook` — crea o reabre conversación, resuelve o crea el contacto
  - `MessageService.send` (saliente) con ventana de 24 h y fallback a template
  - Endpoints de conversaciones y mensajes; endpoints de templates
  - Auto-respuesta out-of-hours configurable
  - Cron de limpieza y archivado de conversaciones
  - **Tests críticos: unicidad de conversación abierta** (`T-191`)
  - **Privacy: stripe de PII en logs y política de retención** (`T-192`)
  - Manejo de adjuntos (imagen, audio, documento) sobre el storage de C-06
- **Dependencias**: `C-06`, `C-24`, `C-29`
- **Governance**: **CRÍTICO** — el webhook es un **endpoint público sin sesión** que recibe datos personales de terceros (los clientes de la agencia, que no son usuarios del sistema). `T-192` es control de privacidad bajo Ley 25.326. Solo análisis y propuesta; no escribir sin aprobación humana explícita.
- **Bloqueantes a resolver**: ninguno propio. **Aplica** `IN-13` (`T-192` define la retención de mensajes, que es la misma pregunta legal de fondo que la de `audit_logs`, resuelta en C-03) e `IN-51` (el índice de unicidad que `T-191` testea, decidido en C-29).
- **Nota de seguridad**: el webhook es superficie de ataque directa. Verificación de firma, rate limiting propio e idempotencia por `message_id` de Meta no son opcionales.
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 6 — Conversación de WhatsApp
  - `knowledge-base/05_reglas_de_negocio.md` §RN-WA, §RN-DP (datos y privacidad)
  - `knowledge-base/12_seguridad_y_compliance.md` §Protección de datos personales, §Tabla de retenciones, §Protección contra OWASP Top 10, §Rate limiting, WAF y headers
  - `knowledge-base/04_modelo_de_datos.md` §Dominio Communication
  - `knowledge-base/03_actores_y_roles.md` §Rutas públicas (sin autenticación)

### [C-31] `whatsapp-web-inbox-y-templates`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-181` … `T-186` (6 tareas)
- **Scope**:
  - Configuración del canal de WhatsApp en settings (alta del número, verificación, credenciales)
  - **Bandeja de conversaciones (inbox)** con filtros por asignación, estado y sucursal
  - Hilo de conversación con composer, indicadores de estado de mensaje y selector de template
  - Gestión de templates en settings (alta, envío a aprobación, estado)
  - Envío de WhatsApp desde el detalle de lead/contacto
  - **SSE para mensajes en tiempo real** (`GET /api/v1/conversations/stream`) con heartbeat cada 30 s
- **Dependencias**: `C-07`, `C-23`, `C-30`
- **Governance**: **MEDIO** — flujo con estado en tiempo real; el composer envía mensajes reales a clientes finales.
- **Bloqueantes a resolver**: ninguno de los 14.
- **No bloqueante que hay que confirmar antes de `T-186`**: `IN-08` — **canal en tiempo real: SSE vs WebSocket vs Redis Pub/Sub**. `mejoras-y-saas` §5 dice **WebSocket**; `spec-tecnica` §2.2 menciona Redis pub-sub sin definir el transporte al cliente; el plan de implementación dice **SSE explícitamente** (*"NO es WebSocket"*), con auth por token corto en query param. El plan es el más específico y SSE alcanza —la bandeja es unidireccional— pero confirmarlo antes de construir (`PA-19`). **Nota de seguridad**: el token en query param queda en logs de acceso; coordinar con el stripe de PII de `T-192`.
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 6 — Conversación de WhatsApp
  - `knowledge-base/06_funcionalidades.md` §Épica 5 — Mensajería y WhatsApp Business, §Atajos de teclado
  - `knowledge-base/15_marca_y_ux.md` §Componentes UI, §Tono de voz, §Navegación del producto
  - `knowledge-base/05_reglas_de_negocio.md` §RN-WA
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados

### [C-32] `whatsapp-crm-integracion-y-cierre`
- **Estado**: `[ ]` pendiente
- **Rango**: `T-167`, `T-188`, `T-190`, `T-194` (4 tareas) — `T-167` movida desde el bloque 1.4, ver **D-3**
- **Scope**:
  - **Vincular conversación de WhatsApp a lead automáticamente** (`T-167`): al llegar un mensaje de un contacto con lead abierto, adjuntar la conversación; si no hay lead, crear uno según la regla configurada
  - **Tests E2E del flujo completo de WhatsApp** (`T-188`): recepción → asignación → respuesta → vinculación a lead → cierre
  - Métricas y dashboard de WhatsApp (volumen, tiempo de primera respuesta, tasa de entrega, uso contra la cuota del plan)
  - Documentación: setup y operación del canal
- **Dependencias**: `C-25`, `C-30`, `C-31`
- **Governance**: **MEDIO** — automatización que crea y modifica leads a partir de eventos externos. Implementar con checkpoints.
- **Bloqueantes a resolver**: ninguno.
- **Nota**: **es el último change del MVP.** Al archivarlo, la OLA 1 está completa y el producto es lanzable a los early adopters. `T-190` cierra el lazo con `IN-03`: si se adoptó la cuota de mensajes por plan, el dashboard es donde el cliente la ve.
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 5 — Ciclo de vida de un lead, §Flujo 6 — Conversación de WhatsApp
  - `knowledge-base/05_reglas_de_negocio.md` §RN-WA, §RN-CR
  - `knowledge-base/06_funcionalidades.md` §Épica 5, §Definición de terminado (Definition of Done)
  - `knowledge-base/11_testing_y_calidad.md` §Definition of Ready — cierre de ola / release
  - `knowledge-base/01_vision_y_objetivos.md` §Alcance del MVP, §Métricas de éxito

---

## Tabla resumen

| # | Change | Ola | Rango `T-XXX` | Tareas | Gov. | Dependencias | Bloqueantes que resuelve |
|---|---|---|---|---|---|---|---|
| C-01 | `foundation-setup` | 0 | T-001…T-008 | 8 | ALTO | — | `IN-22`, `IN-29` |
| C-02 | `core-backend-primitives` | 0 | T-009…T-016, T-032, T-033 | 9 | **CRÍTICO** | C-01 | `IN-01`, `IN-02` |
| C-03 | `observabilidad-y-auditoria-base` | 0 | T-011, T-028…T-031 | 5 | ALTO | C-01, C-02 | `IN-13`, `IN-23`, `IN-31` |
| C-04 | `tenancy-planes-y-limites` | 0 | T-017…T-020, T-059 | 5 | **CRÍTICO** | C-02 | `IN-03`, `IN-04` |
| C-05 | `identidad-auth-y-tenant-endpoints` | 0 | T-021…T-027 | 7 | **CRÍTICO** | C-01, C-02, C-04 | `IN-06`, `IN-12(a)` |
| C-06 | `storage-y-notificaciones` | 0 | T-034, T-035 | 2 | MEDIO | C-01, C-02, C-05 | — |
| C-07 | `design-system-y-shell-web` | 0 | T-036…T-038 | 3 | BAJO | C-01 | — |
| C-08 | `auth-frontend-y-api-client` | 0 | T-039…T-042 | 4 | ALTO | C-01, C-05, C-07 | — |
| C-09 | `admin-tenants-backoffice` | 1.1 | T-043…T-045, T-062 | 4 | ALTO | C-04, C-05 | — |
| C-10 | `onboarding-wizard-y-tenant-setup` | 1.1 | T-046…T-051, T-053, T-058, T-060 | 9 | MEDIO | C-04, C-05, C-06, C-07, C-08 | — |
| C-11 | `pipeline-configurable` | 1.1 | T-052, T-139…T-142 | 5 | MEDIO | C-05, C-07, C-09, C-10 | `IN-10`, `IN-12(b)` |
| C-12 | `usuarios-invitaciones-y-settings` | 1.1 | T-054…T-057, T-061 | 5 | MEDIO | C-05, C-07, C-10 | — |
| C-13 | `catalogo-de-vehiculos` | 1.2 | T-063…T-070 | 8 | BAJO | C-02, C-07 | — |
| C-14 | `vehiculos-modelo-y-servicios` | 1.2 | T-071…T-077, T-084, T-086 | 9 | ALTO | C-02, C-04, C-05, C-13 | `IN-07` |
| C-15 | `vehiculos-api` | 1.2 | T-078…T-083, T-085, T-087 | 8 | MEDIO | C-02, C-14 | — |
| C-16 | `fotos-de-vehiculos` | 1.2 | T-088…T-092 | 5 | MEDIO | C-06, C-14 | — |
| C-17 | `importacion-csv-de-stock` | 1.2 | T-093…T-097 | 5 | MEDIO | C-14 | — |
| C-18 | `busqueda-opensearch` | 1.2 | T-098…T-100, T-114 | 4 | ALTO | C-14, C-15 | — |
| C-19 | `stock-web-listado-y-detalle` | 1.2 | T-101…T-103, T-110, T-111 | 5 | BAJO | C-07, C-08, C-15, C-18 | — |
| C-20 | `stock-web-alta-edicion-y-fotos` | 1.2 | T-104…T-107 | 4 | BAJO | C-07, C-13, C-15, C-16 | — |
| C-21 | `stock-web-import-y-cierre` | 1.2 | T-108, T-109, T-112, T-113 | 4 | BAJO | C-17, C-19, C-20 | — |
| C-22 | `publicacion-portal-deruedas` | 1.3 | T-115…T-122, T-128, T-129 | 10 | ALTO | C-14 | — ⚠️ **R-1** |
| C-23 | `publishing-config-y-seguridad` | 1.3 | T-123…T-127 | 5 | ALTO | C-03, C-07, C-19, C-22 | — |
| C-24 | `contactos-y-deduplicacion` | 1.4 | T-130…T-138 | 9 | MEDIO | C-05, C-06, C-07 | `IN-12(c)` |
| C-25 | `leads-y-motor-de-pipeline` | 1.4 | T-143…T-150 | 8 | ALTO | C-02, C-11, C-14, C-24 | — |
| C-26 | `leads-api-y-tests` | 1.4 | T-151…T-153, T-160, T-169 | 5 | MEDIO | C-25 | `IN-12(d)` |
| C-27 | `crm-web-kanban-y-leads` | 1.4 | T-154…T-159 | 6 | BAJO | C-07, C-08, C-13, C-26 | — |
| C-28 | `crm-automatizaciones-y-dashboard` | 1.4 | T-161…T-166, T-168 | 7 | MEDIO | C-06, C-07, C-14, C-25, C-27 | — |
| C-29 | `whatsapp-canal-y-modelo` | 1.5 | T-170…T-175 | 6 | ALTO | C-05, C-23, C-24 | — |
| C-30 | `whatsapp-mensajeria-core` | 1.5 | T-176…T-180, T-187, T-189, T-191…T-193 | 10 | **CRÍTICO** | C-06, C-24, C-29 | — |
| C-31 | `whatsapp-web-inbox-y-templates` | 1.5 | T-181…T-186 | 6 | MEDIO | C-07, C-23, C-30 | — |
| C-32 | `whatsapp-crm-integracion-y-cierre` | 1.5 | T-167, T-188, T-190, T-194 | 4 | MEDIO | C-25, C-30, C-31 | — |

**Totales**: 32 changes · **194/194 tareas** (verificado: sin huecos, sin solapamientos) · 6 olas · 13 gates de paralelismo · camino crítico de 13 changes (86 tareas).

**Por governance**: 4 CRÍTICO (C-02, C-04, C-05, C-30) · 9 ALTO · 12 MEDIO · 7 BAJO.

---

## Antes de empezar

Tres cosas que **no** son código y que conviene arrancar ya, porque bloquean o encarecen el roadmap:

1. 🟡 **Llevar la enmienda [`E-001`](docs/adr/E-001-enmienda-glosario-super-admin.md) hasta su ratificación.** Abierta el 13-ago-2026; la discusión cierra el **20-ago-2026** (5 días hábiles, Art. 8). Incorpora *"Super Admin"* al glosario canónico. **Mientras no se ratifique, `C-02` no puede escribir la migración de `users` ni `rbac.py`.** El contenido técnico ya está decidido en `ADR-017` — lo que falta es el procedimiento, no la decisión.
2. **Conseguir el contrato de la API del portal deRuedas** (**R-1**). Bloquea 15 tareas y está sobre el camino crítico. Arrancar la conversación con el equipo del portal ahora, no en el paso 8.
3. **Escribir la matriz RBAC canónica** (**R-2**). C-02 la necesita para `rbac.py` y el plan de testing la convierte en quality gate bloqueante de CI. **Ya se puede escribir**: `ADR-017` fijó el catálogo de roles.

> ✅ Cerrados durante la propuesta de C-01: `PA-01` ([`ADR-000`](docs/adr/ADR-000-precedencia-documental.md)), `IN-16` ([`ADR-015`](docs/adr/ADR-015-orquestacion-kubernetes-y-gitops.md)), `IN-15` ([`ADR-016`](docs/adr/ADR-016-trazas-distribuidas-tempo.md)), `IN-01` e `IN-02` ([`ADR-017`](docs/adr/ADR-017-catalogo-de-roles-y-super-admin.md), condicionados a `E-001`).

**Primer change**: `C-01` (`foundation-setup`) — `IN-22` (80 %) e `IN-29` (manda la spec) ya vienen resueltos por `ADR-000`; C-01 los **ejecuta**, no los decide.

```
/opsx:propose C-01-foundation-setup
```
