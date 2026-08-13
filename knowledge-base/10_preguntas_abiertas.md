# Preguntas Abiertas e Inconsistencias

> Este archivo es el **resultado del chequeo de consistencia cruzada** sobre los 11 documentos fuente (~19.900 líneas, leídos íntegramente).
> Se documentaron **54 inconsistencias reales**: **14 bloqueantes** (Parte 1) + **40 no bloqueantes** (Parte 2). Bloqueante significa que no se puede escribir la migración, el enum, el quality gate o el contrato de API correspondiente sin una decisión humana previa.
>
> **Bloqueantes (14):** ~~`IN-01`~~ ✅, ~~`IN-02`~~ ✅, `IN-03`, `IN-04`, `IN-05`, `IN-06`, `IN-07`, `IN-10`, `IN-12`, `IN-13`, ~~`IN-22`~~ ✅, `IN-23`, ~~`IN-29`~~ ✅, ~~`IN-31`~~ ✅. **Quedan 9 abiertos.**
>
> ✅ **Cerrados al 13-ago-2026, con el ADR que los cierra:**
>
> | Entrada | ADR |
> |---|---|
> | `IN-01` · `IN-02` · `PA-02` | [`ADR-017`](../docs/adr/ADR-017-catalogo-de-roles-y-super-admin.md) + [`E-001`](../docs/adr/E-001-enmienda-glosario-super-admin.md) |
> | `IN-15` · `PA-20` (trazas) | [`ADR-016`](../docs/adr/ADR-016-trazas-distribuidas-tempo.md) |
> | `IN-16` · `PA-20` (orquestación) | [`ADR-015`](../docs/adr/ADR-015-orquestacion-kubernetes-y-gitops.md) |
> | **`IN-22`** · `PA-08` | [`ADR-014`](../docs/adr/ADR-014-umbrales-de-cobertura.md) |
> | **`PA-06`** · **`R-3`** | [`ADR-013`](../docs/adr/ADR-013-variables-de-entorno.md) |
> | **`IN-29`** · `PA-14` | [`ADR-018`](../docs/adr/ADR-018-anclas-de-adr-del-plan-de-implementacion.md) |
> | `PA-01` · `IN-31` · `SU-12` | [`ADR-000`](../docs/adr/ADR-000-precedencia-documental.md) |
>
> ⚠️ Las secciones de `IN-01`, `IN-02` e `IN-31` más abajo **todavía no llevan su marca de resuelto** — están cerradas por ADR, pero el texto de la Parte 1 conserva la redacción original. Leer siempre esta tabla primero.
>
> ⚠️ **Defectos de este mismo archivo** (registrados para no repetir el patrón que `IN-37` le denuncia al plan de implementación):
> - `IN-15` (Jaeger vs Tempo) e `IN-16` (Kubernetes con o sin ArgoCD) **se referencian en las Partes 3 y 4 pero nunca se documentan como entradas** en la Parte 2. Eran referencias colgadas. ✅ **Ambas resueltas el 13-ago-2026** — `IN-15` por [`ADR-016`](../docs/adr/ADR-016-trazas-distribuidas-tempo.md) (gana **Tempo**, competencia de dominio de SRE sobre N1) e `IN-16` por [`ADR-015`](../docs/adr/ADR-015-orquestacion-kubernetes-y-gitops.md) (**Kubernetes + ArgoCD**, decisión que llena un vacío: N1 no menciona orquestación).
> - Los identificadores `IN-55` e `IN-56` no existen: la serie salta de `IN-54` a `IN-57`. Es un hueco de numeración, no información faltante.
>
> Criterio de clasificación:
> - 🔴 **BLOQUEANTE** — hay que decidir *antes* de escribir código. Dos documentos vinculantes dicen cosas incompatibles sobre el mismo artefacto.
> - 🟡 **No bloqueante** — se puede avanzar eligiendo una opción y documentándola; el costo de equivocarse es reversible.
>
> ✅ **Precedencia — RESUELTA.** `PA-01` quedó cerrada por [`ADR-000`](../docs/adr/ADR-000-precedencia-documental.md) (2026-08-13): **jerarquía por autoridad con competencia por dominio**.
>
> | Nivel | Documentos | Autoridad |
> |---|---|---|
> | **N0** | `constitucion` | Principios, reglas vinculantes y **glosario canónico**. Gana siempre. Solo cambia por enmienda del Artículo 8. |
> | **N1** | `spec-tecnica` + ADRs | El "cómo" técnico. Autoridad delegada explícitamente por N0. |
> | **N2** | `plan-implementacion` | Orden y descomposición en tareas `T-XXX`. No decide diseño. |
> | **N3** | `plan-seguridad`, `plan-testing`, `plan-sre` | **Prevalecen sobre N1 dentro de su dominio propio**, nunca sobre N0. Cada aplicación se registra como ADR. |
> | **N4** | `plan-gtm`, `manual-usuario`, `brand-book`, `mejoras-y-saas`, `historias-usuario` | No normativos. Insumo e intención. |
>
> ⚠️ **La recencia NO es criterio de desempate.** Los metadatos de los `.docx` originales muestran que los 11 documentos se generaron en una sola sesión de 8 h 41 min (6-may-2026, 14:31→23:12 ART), con `revision=1` y sin edición posterior. El orden de los timestamps es de **generación**, no de deliberación: aplicarlo haría ganar a `plan-gtm` sobre `spec-tecnica`. Ver `ADR-000` §Contexto.
>
> **Corolario**: las 54 inconsistencias **no son decisiones revisadas que no se propagaron** — son deriva de generación. No hay respuesta correcta oculta que recuperar; hay que decidir.
>
> **Empate de nivel ⇒ la regla es muda** y la contradicción escala al decisor humano de la Parte 3.

---

# Parte 1 — Inconsistencias BLOQUEANTES (14)

## 🔴 IN-01 — El catálogo de roles no coincide entre cinco documentos

**`constitucion.md`** (glosario, vinculante): *"Un usuario tiene un rol (Gerente, Vendedor, Administrativo)"* — **3 roles, en español**.
**`spec-tecnica.md`** §3.3 (`user_role_enum`): `manager | salesperson | admin_staff` — **3 roles, en inglés, sin `super_admin`**.
**`spec-tecnica.md`** §8.4: *"Los roles iniciales son Gerente, Vendedor y Administrativo"* — español, dentro del mismo documento que usa inglés en el enum.
**`plan-implementacion.md`** (T-014): *"Catálogo de roles canónicos: `super_admin`, `manager`, `salesperson`, `admin_staff`"* — **4 roles**.
**`plan-seguridad.md`** y **`plan-testing.md`**: idéntico, **4 roles**.
**`historias-usuario.md`**: **5 personas** (P1 Gerente, P2 Vendedor, P3 Administrativo, P4 Customer Success Manager, P5 Super Admin).

**Impacto**: no se puede escribir el `CREATE TYPE user_role_enum`, ni la matriz RBAC, ni los tests de autorización (que el plan de testing declara bloqueantes en CI y que recorren *"los roles `super_admin, manager, salesperson, admin_staff`"*).

**Resolución propuesta**: adoptar los **4 roles en inglés** del plan de implementación como catálogo canónico, con equivalencia documentada Gerente=`manager`, Vendedor=`salesperson`, Administrativo=`admin_staff`, y `super_admin` como rol de plataforma. Enmendar el glosario de la constitución y §8.4 de la spec.

---

## 🔴 IN-02 — `super_admin` tiene endpoints pero no existe en `user_role_enum`

**`spec-tecnica.md`** §3.3: `user_role_enum` = `manager | salesperson | admin_staff`. **No incluye `super_admin`.**
**`spec-tecnica.md`** §4.1.3: *"salvo para usuarios con rol Super Admin que tienen un endpoint diferenciado bajo `/admin/api/v1`"*.
**`spec-tecnica.md`** §4.2.11: define 11 endpoints bajo `/admin/api/v1` para Super Admin.
Además, `users.tenant_id` es `FK NOT NULL` — un `super_admin` de deRuedas **no pertenece a ningún tenant**.

**Impacto**: el modelo de datos, como está escrito, **no puede representar al Super Admin**. Es una contradicción interna de la spec técnica, no entre documentos.

**Resolución propuesta**: definir explícitamente si `super_admin` (a) es un cuarto valor del enum con `tenant_id` nullable, (b) vive en una tabla separada `super_admins` — la cual, notablemente, el plan de testing **sí menciona** en su lista de tablas exentas de RLS, o (c) es solo un rol de Keycloak sin fila en `users`. La opción (b) tiene evidencia indirecta a favor.

---

## 🔴 IN-03 — Los límites cuantitativos por plan no coinciden

| | `mejoras-y-saas.md` §10 | `plan-gtm.md` §3.2 |
|---|---|---|
| Starter — usuarios | Hasta **2** | **2** ✅ |
| Starter — vehículos | Hasta **30** | Hasta **80** ❌ |
| Pro — usuarios | Hasta **6** | **5** ❌ |
| Pro — vehículos | Hasta **100** | Hasta **300** ❌ |
| Enterprise — usuarios | **Ilimitados** | **15** ❌ |
| Enterprise — vehículos | **Ilimitados** | Sin límite práctico ✅ |
| Enterprise — sucursales | Multi-sucursal (sin tope) | Hasta **5** ❌ |
| Pro — sucursales | (no especificado) | Hasta **2** |
| Cuota de WhatsApp | (no existe el concepto) | 1.500 / 5.000 / 20.000 msj/mes |

**Impacto**: `PlanLimitsService` (T-059) y el seed de la tabla `plans` no se pueden escribir. `assert_can_add_user` / `assert_can_add_vehicle` / `assert_can_add_branch` necesitan números. Además, el GTM introduce una dimensión de límite (**mensajes de WhatsApp por mes**) que **no existe en el modelo de datos** — `plans` no tiene columna para eso.

**Resolución propuesta**: el `plan-gtm` es el documento comercial más específico y probablemente el más reciente; adoptar sus valores y **agregar `max_whatsapp_messages_month` a `plans`**. Enmendar `mejoras-y-saas` §10 como obsoleto.

---

## 🔴 IN-04 — Moneda de los precios: ARS vs USD (el modelo de datos solo soporta ARS)

**`mejoras-y-saas.md`** §10: Starter **ARS 45.000** · Pro **ARS 95.000** · Enterprise **ARS 195.000**.
**`plan-gtm.md`** §3.2: Starter **USD 49** · Pro **USD 149** · Enterprise **USD 399 (desde)**. Más usuario extra USD 15/12/10 y excedente de WhatsApp USD 0,012/mensaje.
**`spec-tecnica.md`** §3.3: `plans.price_ars numeric(18,2) NOT NULL` y `subscriptions.amount_ars numeric(18,2) NOT NULL` — **solo pesos, sin columna de moneda**, pese a que la convención general del propio documento (§3.1) dice *"los valores monetarios se almacenan en `numeric(18,2)` con la moneda como columna asociada (ARS, USD)"*.
**`mejoras-y-saas.md`** §13 refuerza ARS: *"Pricing en pesos con cláusulas de actualización trimestral según índice CER o IPC"*, como mitigación explícita del riesgo macro.

**Impacto**: **el esquema no puede representar el pricing del plan GTM.** Además, a un tipo de cambio razonable, USD 49 y ARS 45.000 no son el mismo precio: son propuestas comerciales distintas, no una conversión.

**Resolución propuesta**: decidir la moneda de facturación (la contradicción sugiere que la decisión de pasar a USD ya se tomó y no se propagó — ver `SU-11`). Si es USD, renombrar a `price_amount` + `price_currency` y ajustar `subscriptions`, `vehicles.price_ars`/`price_usd` y todos los campos `*_ars` con criterio uniforme.

---

## 🔴 IN-05 — Dos sistemas de planificación paralelos, sin traducción entre ellos

**`mejoras-y-saas.md`** §8 y **`historias-usuario.md`**: **Fases F0-F5** con meses de calendario. F0 discovery = meses 1-3 · **F1 MVP = meses 4-7** · F2 = 8-10 · F3 = 11-13 · F4 = 14-16 · F5 = mes 17+.
**`plan-implementacion.md`**: **Olas 0 y 1**, sin ningún calendario. Ola 0 = fundación (42 tareas), Ola 1 = MVP (152 tareas) = épicas E1-E5.
**`plan-gtm.md`**, **`plan-seguridad.md`**, **`plan-sre.md`**, **`plan-testing.md`**: **Olas 0-3** con meses. **Ola 1 = 0-6 meses** · Ola 2 = 6-12 · Ola 3 = 12-24.

**El conflicto**: "Fase 1 = meses 4-7" y "Ola 1 = meses 0-6" designan ambos el MVP, con ventanas de calendario **distintas y desplazadas**. Ningún documento define la equivalencia. Además `mejoras-y-saas` proyecta 18 meses hasta la versión completa y el GTM proyecta 24 meses hasta Ola 3.

**Impacto**: imposible construir un roadmap único. Cada documento especializado ancla sus compromisos (MFA obligatoria, chaos testing, bug bounty, SLO al 99.9 %) a "Ola 2" o "Ola 3", y no se puede saber a qué mes corresponden.

**Resolución propuesta**: adoptar **Olas** como unidad canónica (la usan 5 de los 11 documentos, incluido el operativo) y publicar una tabla de equivalencia Fase↔Ola. Marcar la numeración de Fases de `historias-usuario` como etiqueta de prioridad, no de calendario.

---

## 🔴 IN-06 — `users.password_hash NOT NULL` contradice la delegación total a Keycloak

**`spec-tecnica.md`** §3.3, tabla `users`: `password_hash varchar(255) NOT NULL` — *"Hash argon2id. Nunca se loguea ni serializa."*
**`spec-tecnica.md`** §8.3: *"La autenticación se delega **íntegramente** a Keycloak. **La aplicación nunca maneja contraseñas** en texto plano."*
**`spec-tecnica.md`** ADR-007: Keycloak es el servicio de identidad; el auth a medida está prohibido por constitución.
**`plan-seguridad.md`**: *"Toda autenticación de usuarios pasa por Keycloak... **nunca password directo en la app**"*. El hash argon2id está **en Keycloak**, no en la aplicación.
Sin embargo, **`spec-tecnica.md`** §4.2.1 y **`plan-implementacion.md`** definen `POST /api/v1/auth/login` — un endpoint de login propio del backend, no un redirect OIDC.

**Impacto**: define si la tabla `users` lleva la columna `password_hash` o no, y si el flujo de login es *redirect a Keycloak* (Authorization Code + PKCE) o *proxy de credenciales* (Resource Owner Password Credentials, un grant desaconsejado y en vías de deprecación en OAuth 2.1).

**Resolución propuesta**: eliminar `password_hash` de `users`, tratar la tabla como espejo local del usuario de Keycloak, y definir `/auth/login` como el callback del flujo OIDC —no como un endpoint que reciba contraseñas.

---

## 🔴 IN-07 — `vehicles.domain_plate`: obligatorio u opcional

**`spec-tecnica.md`** §3.4: `domain_plate varchar(15) **NOT NULL**`. Además es el identificador natural del vehículo dentro del tenant.
**`constitucion.md`** (glosario): *"Un vehículo se identifica unívocamente dentro de un tenant por su dominio"* — refuerza que es obligatorio.
**`plan-implementacion.md`** (T-071): `domain_plate (nullable)`.
**`manual-usuario.md`** §2.7.1: campo *"Patente **o** chasis (opcional)"*.

**Impacto**: es una columna `NOT NULL` en una migración. No se puede escribir sin decidir. Y hay un caso de negocio real detrás: **un vehículo 0 km o recién ingresado en permuta puede no tener patente todavía**, lo que sugiere que la spec está equivocada y el plan de implementación tiene razón.

**Resolución propuesta**: hacer `domain_plate` nullable, mantener el índice `UNIQUE (tenant_id, domain_plate) WHERE deleted_at IS NULL AND domain_plate IS NOT NULL`, y exigir a nivel de aplicación que exista *patente o chasis* (constraint `CHECK (domain_plate IS NOT NULL OR chassis_number IS NOT NULL)`).

---

## 🔴 IN-10 — El pipeline por defecto tiene 5, 6 o 7 etapas según el documento

**`historias-usuario.md`** HU-E1-007: *"el sistema instalado por defecto trae **cinco** etapas"* — sin nombrarlas.
**`plan-implementacion.md`** T-140: seed de **6 etapas** nombradas: `Nuevo(1)`, `Contactado(2)`, `En negociación(3)`, `Permuta/Test drive(4)`, `Ganado(5, is_won)`, `Perdido(6, is_lost)`.
**`manual-usuario.md`** §2.5 y glosario §13.1: **7 etapas** nombradas: `Nuevo`, `Calificado`, `Visita programada`, `Negociación`, `Acuerdo`, `Ganado`, `Perdido`.
**`mejoras-y-saas.md`** §7.2 sugiere una octava variante en prosa: *"nueva consulta", "contacto realizado", "prueba programada", "prueba realizada", "cotización entregada", "negociación", "operación cerrada", "perdida"* — **8 etapas**.
**`constitucion.md`** (glosario): *"El sistema provee un pipeline por defecto con **cinco** etapas"*.

**Impacto**: es seed data que se ejecuta en el onboarding de **cada tenant nuevo**. Cambiarla después de tener clientes es una migración de datos con leads ya distribuidos entre etapas. Además, el manual de usuario ya documenta las 7 etapas para el cliente final.

**Resolución propuesta**: la constitución y las historias coinciden en **5**; el manual documenta **7** al usuario. Dado que el manual es lo que el cliente lee, y que el plan de implementación siembra 6, hay que elegir explícitamente. Recomendación: adoptar las **7 del manual** (son las que el cliente ya tiene documentadas) y enmendar el glosario constitucional.

---

## 🔴 IN-12 — Contratos de API divergentes para las mismas operaciones

| Operación | `spec-tecnica.md` §4.2 | `plan-implementacion.md` |
|---|---|---|
| Cerrar lead | `POST /leads/{id}/close` (ganado o perdido, un solo endpoint) | `POST /leads/{id}/won` **y** `POST /leads/{id}/lost` (dos endpoints) |
| Fusionar contactos | `POST /contacts/merge` | `POST /contacts/{primary_id}/merge` |
| Eliminar etapa de pipeline | `DELETE /pipeline/stages/{id}` | `POST /pipeline/stages/{id}/archive` |
| Completar actividad | `PATCH /activities/{id}/complete` | `PATCH /activities/{id}` |
| Aceptar invitación | `POST /api/v1/users/accept-invitation` (T-024) | `POST /auth/accept-invitation` (T-054) — **contradicción dentro del mismo documento**, distinto prefijo y distinto namespace |

**Impacto**: el frontend genera sus tipos desde el `openapi.yaml`. Estos son contratos incompatibles, no variaciones de estilo. El caso de `accept-invitation` es especialmente grave porque es una **contradicción interna del plan de implementación**: dos tareas del mismo documento declaran paths distintos para la misma acción.

**Resolución propuesta**: la spec técnica es la fuente vinculante de contratos de API (§1.1 lo declara). Pero `won`/`lost` como endpoints separados es mejor diseño (evita un payload polimórfico) y es lo que se va a implementar. Decidir uno y actualizar el `openapi.yaml` como fuente única.

---

## 🔴 IN-13 — Retención de `audit_logs`: 5 años vs 24 meses vs escalonada por plan

**`spec-tecnica.md`** §3.9: *"Conservación **mínima de cinco años**."*
**`spec-tecnica.md`** §6.5 y §8.8: *"retención **mínima cinco años** por obligaciones contables"* — repetido tres veces, con justificación legal.
**`plan-seguridad.md`** §6.4 (tabla de retenciones): `audit_logs`: **24 meses**.
**`plan-sre.md`** §4: confirma **24 meses** para audit_logs.
**`plan-gtm.md`** §3.2: audit logs **por plan** — Starter 30 días · Pro 12 meses · Enterprise 24 meses.

**Impacto**: triple. (a) Define la política de particionado y el volumen de almacenamiento a 5 años. (b) Es una afirmación de **compliance legal** — la spec invoca obligaciones contables, y el plan de seguridad, que es el documento de compliance, la contradice. (c) El GTM convierte la auditoría en **feature comercial diferenciada por plan**, lo que es incompatible con un mínimo legal uniforme: no se puede borrar el audit log de un cliente Starter a los 30 días si la ley exige 5 años.

**Resolución propuesta**: resolver primero la cuestión legal (¿la Resolución 4717/2020 de AFIP, citada en el plan de seguridad para datos contables a 10 años, aplica a `audit_logs`?). El mínimo legal no puede ser un feature de plan. Lo que sí puede diferenciarse por plan es **cuánto histórico ve el cliente en la UI**, no cuánto se conserva.

---

## ✅ ~~🔴 IN-22~~ — Umbral de cobertura de tests: cuatro valores distintos — **RESUELTA**

> ✅ **Cerrada el 13-ago-2026** por [`ADR-014`](../docs/adr/ADR-014-umbrales-de-cobertura.md): **80 % de líneas y 60 % de ramas**, ambos globales sobre el backend, bloqueantes en CI, más la verificación de que la cobertura no decrece respecto de `main`.
> Líneas: gana N0 (y N2 coincide). Ramas: N0 guarda silencio, así que gobierna `plan-testing` (N3) por competencia de dominio. Se enmienda el **plan de testing**, no la constitución. Lo que sigue es el registro del conflicto original.

**`constitucion.md`** Artículo 2: *"La cobertura mínima del código backend es **ochenta por ciento** medida sobre líneas."* — vinculante.
**`spec-tecnica.md`** §7.2: *"mínimo **80 %** para módulos core (auth, stock, crm, communication, finance), **70 %** para los demás."*
**`plan-implementacion.md`** (job `test-backend-unit`): *"pytest con coverage. Mínimo **80 % global**."*
**`plan-testing.md`** §3.2, §3.7 y §7.4: ***70 % líneas y 60 % branches*** en código de dominio, *"menor en infraestructura"*.

**Impacto**: es un **quality gate del CI que bloquea merges**. El plan de testing —el documento que *debería* ser autoritativo en esto— fija el umbral **más bajo** de los cuatro y contradice directamente a la constitución, que es el documento de mayor jerarquía. Un PR que pase el gate del plan de testing (70 %) viola la constitución (80 %).

**Resolución propuesta**: la constitución solo se modifica por enmienda formal (Artículo 8). O se enmienda a 70 %/60 %, o el plan de testing sube a 80 %. **No se puede dejar así**: hoy el CI está especificado en violación de la norma vinculante del proyecto.

---

## 🔴 IN-23 — Objetivos de latencia: la spec y el plan de SRE fijan números incompatibles

| Endpoint | `constitucion.md` Art. 4 | `spec-tecnica.md` §6.1 y §9.7 | `plan-sre.md` §3.2 (SLO) | `plan-testing.md` (threshold) |
|---|---|---|---|---|
| Listado | p95 **< 200 ms** | p95 **< 200 ms**, p99 < 500 ms | p95 **< 300 ms** ❌ | p95 < 300 ms ❌ |
| Búsqueda full-text | p95 **< 500 ms** | p95 **< 500 ms**, p99 < 1,5 s | p95 **< 2,0 s** ❌ | p95 < 2 s ❌ |
| Detalle | — | p95 < 150 ms | — | — |
| Escritura simple | — | p95 < 300 ms | — | — |

**Impacto**: define los umbrales de las alertas de Prometheus (`APILatencyHigh` dispara a p95 > 500 ms/15 min), los thresholds de los tests de carga con k6/Locust, y el criterio de "Definición de terminado" de las historias (que exige < 200 ms p95). **El plan de SRE es 4× más permisivo que la constitución en búsqueda** (2.000 ms vs 500 ms).

Notablemente, el plan de implementación fija objetivos *aún más estrictos* que la constitución para casos concretos: vehicle search p95 < 150 ms, suggest p95 < 50 ms — lo que sugiere que los números del plan de SRE son SLOs de servicio "con margen" y los de la constitución son objetivos de ingeniería. Pero eso **no está escrito en ningún lado**.

**Resolución propuesta**: distinguir explícitamente **objetivo de ingeniería** (constitución/spec) de **SLO comprometido con presupuesto de error** (SRE), y documentar la relación. Si no, las alertas y los tests van a medir cosas distintas de lo que la Definición de Terminado exige.

---

## ✅ ~~🔴 IN-29~~ — La numeración de ADRs no coincide entre la spec y el plan de implementación — **RESUELTA**

> ✅ **Cerrada el 13-ago-2026** por [`ADR-018`](../docs/adr/ADR-018-anclas-de-adr-del-plan-de-implementacion.md): manda la numeración de `spec-tecnica` (N1 > N2). Dos anclas mal apuntadas — `ADR-002` está etiquetado "Migrations" cuando es **PostgreSQL**, y `ADR-005` está usado como "OpenSearch" cuando es **React Native con Expo** (OpenSearch es `ADR-011`). El plan **no se edita**: lleva una anotación delimitada que remite al ADR. Lo que sigue es el registro del conflicto original.

| ADR | `spec-tecnica.md` §5 | `plan-implementacion.md` (anclas de tareas) |
|---|---|---|
| ADR-002 | **PostgreSQL** como base principal | **Migrations (Alembic)** — ancla de T-007 y todas las migraciones |
| ADR-005 | **React Native con Expo** | **OpenSearch** — ancla de T-098, T-099 |
| ADR-011 | **OpenSearch** | *(no referenciado; su tema está en ADR-005)* |

Los ADR-004, 006, 007, 008 y 009 **sí coinciden**. Los ADR-001, 003, 010 y 012 no son referenciados por el plan de implementación.

**Impacto**: **la trazabilidad tarea → decisión arquitectónica está rota**. Una tarea que dice "anclada en ADR-005" apunta a *React Native* en un documento y a *OpenSearch* en el otro. La constitución establece (Principio 5) que los ADRs son vinculantes y trazables; con dos numeraciones distintas, esa trazabilidad no existe.

**Resolución propuesta**: la spec técnica es la que **contiene** los ADRs completos (contexto/decisión/alternativas/consecuencias); el plan de implementación solo los referencia. Corregir las referencias del plan de implementación contra la numeración de la spec. Nota adicional: el plan de implementación nunca referencia ADR-001 ni ADR-003 — huecos sin explicación.

---

## 🔴 IN-31 — El SLA de disponibilidad por plan difiere entre la spec y los documentos comerciales

**`spec-tecnica.md`** §6.2 y §9.7: *"SLA de disponibilidad mensual: **99.9 % para los planes Starter y Pro, 99.95 % para Enterprise**."*
**`plan-sre.md`** §3.1 (tabla de SLA públicos): Starter **99.0 %** · Pro **99.5 %** · Enterprise **99.9 %**. Con créditos del 5 %, 10 % y 25 % de la suscripción.
**`plan-gtm.md`** §3.2: Starter **99.0 %** · Pro **99.5 %** · Enterprise **99.9 %** — coincide con SRE.
**`plan-seguridad.md`** §12.2 (respuesta a cuestionario de infosec): *"SLA de 99.5 % mensual en plan estándar y 99.9 % en plan enterprise"* — menciona **solo dos planes**, omitiendo Starter.

**Impacto**: es un **compromiso contractual con créditos económicos asociados**. La spec compromete 99.9 % para Starter, donde el SRE ofrece 99.0 % — la diferencia es 7h12min de downtime mensual aceptable vs 43 minutos. Con la cifra de la spec, un cliente Starter podría reclamar créditos por caídas que el equipo de SRE considera dentro del presupuesto de error. Además, el SLO interno del SRE (99.7 %) es **inferior** al SLA que la spec promete a Starter y Pro (99.9 %) — matemáticamente insostenible: nunca se promete un SLA por encima del SLO interno.

**Resolución propuesta**: adoptar la escala del SRE/GTM (99.0/99.5/99.9), que es la única internamente coherente con un SLO interno de 99.7 % y con el presupuesto de error de 130 min/mes. Corregir §6.2 y §9.7 de la spec. Corregir también la FAQ del plan de seguridad para que mencione los tres planes.

---

# Parte 2 — Inconsistencias no bloqueantes (40)

## Modelo de datos y dominio

**🟡 IN-08 — Canal en tiempo real: WebSocket vs SSE vs Redis Pub/Sub.**
`mejoras-y-saas` §5: *"La capa de API expone los servicios mediante REST y **WebSocket**"*. `spec-tecnica` §2.2: Redis *"pub-sub para eventos en tiempo real"* (sin definir el transporte al cliente). `plan-implementacion`: explícitamente **SSE** — *"NO es WebSocket"* — vía `GET /api/v1/conversations/stream`, con auth por token corto en query param y heartbeat cada 30 s.
→ El plan de implementación es el más específico y probablemente el correcto. SSE es unidireccional, lo cual alcanza para la bandeja de mensajes. Confirmar y actualizar `mejoras-y-saas`.

**🟡 IN-09 — Límite de fotos por vehículo: cuatro valores.**
`mejoras-y-saas` §7.1 y `historias-usuario` HU-E2-002: **hasta 20**. `plan-implementacion`: **máx. 30**. `manual-usuario` §2.7.1: *"Subí entre **4 y 12**"*. `manual-usuario` §10.2: *"la cantidad recomendada es entre **8 y 15**: más de 20 satura"*. `manual-usuario` §12.3: *"mínimo **8-10** fotos"* con 10 ángulos listados.
→ Hay que distinguir **límite duro del sistema** (candidatos: 20 o 30) de **recomendación de buena práctica** (4-12 / 8-15 / 8-10). El manual se contradice a sí mismo tres veces.

**🟡 IN-11 — Los estados del vehículo no coinciden.**
`spec-tecnica` y `plan-implementacion` (`vehicle_status_enum`): **6 valores** — `available`, `reserved`, `sold`, `in_workshop`, `in_preparation`, `archived`.
`historias-usuario` HU-E2-004: **5** — `disponible, reservado, vendido, **en taller**, en preparación` (sin `archived`, aunque HU-E2-003 sí habla de archivar).
`manual-usuario` §4.2.3: **5** — `Disponible, Reservado, En preparación, Vendido, **Pausado**` (sin `en taller`, sin `archived`).
Además el manual agrega una regla que no está en ningún otro lado: *"la reserva se libera automáticamente a los **7 días** si no se concreta"*.
→ `Pausado` probablemente sea el *estado de publicación*, no del vehículo (HU-E3-002 es "Pausar y reanudar **publicación**"). El manual confunde ambos conceptos. Confirmar y corregir el manual.

**🟡 IN-51 — `conversation_status_enum`: `snoozed` existe o no.**
`spec-tecnica`: `open | snoozed | closed` (3 valores) y el índice único es `WHERE status != 'closed'`.
`plan-implementacion`: `open | closed` (2 valores) y el índice único es `WHERE status = 'open'`.
→ Con 3 estados, los dos índices no son equivalentes: una conversación `snoozed` sería única bajo la regla de la spec pero no bajo la del plan.

**🟡 IN-57 — Constraints de unicidad de `contacts` divergentes.**
`spec-tecnica`: `UNIQUE (tenant_id, primary_phone)` **sin** `WHERE deleted_at IS NULL`, más `UNIQUE (tenant_id, document_number, document_type) WHERE document_number IS NOT NULL`.
`plan-implementacion`: solo `UNIQUE (tenant_id, phone) WHERE deleted_at IS NULL` — sin la unicidad por documento.
→ Sin el `WHERE deleted_at IS NULL` de la spec, un contacto borrado lógicamente bloquea para siempre la reutilización de su teléfono. Es un bug latente. La constitución exige desduplicar *"por número telefónico **o** documento"*, lo que respalda la versión de la spec.

**🟡 IN-30 — El conteo de módulos varía: 8, 10, 12 o 16.**
`mejoras-y-saas` §7: *"**ocho** módulos funcionales"*. `spec-tecnica` §2.3: **16** módulos de backend. `spec-tecnica` §3.2: *"**diez** dominios delimitados"* del modelo de datos. `historias-usuario`: **12** épicas (*"las ocho funcionales que corresponden a los módulos del producto, más cuatro transversales"* — esto reconcilia el 8 con el 12).
→ Reconciliable: 8 módulos *de cara al cliente*, 16 *paquetes de código*, 10 *dominios de datos*, 12 *épicas de backlog*. Pero ningún documento explicita la relación, y el vocabulario "módulo" se usa para las cuatro cosas.

## Seguridad, compliance y operación

**🟡 IN-14 — ¿Existe signup público self-service?**
`plan-implementacion` §3.2: *"self-service signup público (con cobros recurrentes) **postergado**"*. `plan-seguridad`: *"Signup público: **NO existe en MVP**; cuentas se crean por invitación"*.
`plan-gtm` §9.2: onboarding del plan Starter = **"Self-service"**. Trial de 14 días *"sin tarjeta"*.
→ El GTM está vendiendo un flujo de adquisición que el MVP no implementa. Afecta directamente el funnel comercial y la meta de conversión de Ola 1.

**🟡 IN-17 — Obligatoriedad de MFA.**
`manual-usuario` §2.1: MFA **obligatorio para `manager`**, presentado como hecho consumado al cliente.
`plan-seguridad` §2: MFA para `manager` y `super_admin` *"en implementación"* (Ola 1); opcional para el resto; **obligatoria para todos recién en Ola 2**.
`spec-tecnica` §8.3: *"MFA **opcional** con TOTP"*.
→ El manual promete al cliente algo que el plan de seguridad todavía no garantiza.

**🟡 IN-18 — Retención de datos tras la cancelación: 90 vs 30 días.**
`constitucion.md` Artículo 6: *"sus datos se conservan por **noventa días** y luego se eliminan de manera definitiva"*.
`plan-seguridad` §6.4: *"Datos tras cancelación de servicio: **30 días** en cold storage"*.
`plan-gtm` §3.9: la cancelación ocurre al día 60 de mora, *"+ eliminación programada a 30 días"*.
→ La constitución es vinculante y dice 90. Los otros dos documentos dicen 30 de forma consistente entre sí. Requiere enmienda constitucional o corrección de los planes.

**🟡 IN-19 — Rate limiting expresado en ejes incompatibles.**
`spec-tecnica` §4.1.9: **60 req/min por usuario** y **1.000 req/min por tenant**.
`plan-seguridad` §10: **100 req/s por IP** en el load balancer; login 10/min; reset de password 3/hora.
→ No son estrictamente contradictorios (LB vs aplicación), pero no hay un documento que los integre, y 100 req/s por IP (=6.000/min) es dos órdenes de magnitud más laxo que 60/min por usuario. Falta definir en qué capa se aplica cada uno.

**🟡 IN-33 — Ventana de mantenimiento.**
`spec-tecnica` §6.2: *"como máximo **dos horas por mes**, en horario nocturno argentino, con aviso previo de **cuarenta y ocho horas**"*.
`plan-sre` §9: *"domingos **06:00-09:00** hora AR"* (3 horas) *"aviso **72 horas** de anticipación mínimo"*.
→ Distinta duración, distinto horario (06:00-09:00 no es "nocturno") y distinta anticipación. Ambos son compromisos que se comunican al cliente.

**🟡 IN-34 — RTO global: 1 hora vs 4 horas.**
`spec-tecnica` §6.4: *"RTO: tiempo máximo de recuperación de **una hora** ante caída total"*. §6.2: *"Recuperación ante caída de zona de disponibilidad: **menor a una hora**"*.
`plan-sre` §8.2 y `plan-seguridad` §8.2 (tablas idénticas entre sí): PostgreSQL primary RTO **1 hora** ✅, pero **sistema completo DR en región alternativa: RTO 4 horas, RPO 1 hora** ❌.
→ Reconciliable si "caída total" de la spec significa solo el primary y no un desastre regional, pero la spec dice "caída total". El RPO también difiere: 5 min (spec) vs 1 hora (DR cross-region).

**🟡 IN-35 — Política de backups: el archivado a 7 años solo aparece en un documento.**
`spec-tecnica` §6.4: snapshots diarios 30 días · semanales 12 semanas · mensuales 12 meses · **archivado anual por 7 años** para cumplimiento contable.
`plan-sre` §8 y `plan-seguridad` §6.4: 30 días operativo + snapshot mensual preservado **12 meses**. **Sin archivado anual ni mención de 7 años.**
→ Coherente con `IN-13`: la spec asume obligaciones contables de largo plazo que los planes especializados no recogen. Es la misma pregunta legal de fondo.

**🟡 IN-49 — Los audit logs como feature comercial por plan.**
`plan-gtm` §3.2: audit logs Starter 30 días / Pro 12 meses / Enterprise 24 meses.
Ningún documento técnico contempla retención de auditoría variable por tenant.
→ Sub-caso de `IN-13`, pero merece nota propia: implementar retención por plan requiere lógica de particionado y purga *por tenant*, que hoy no está diseñada (`audit_logs` se particiona por mes, no por tenant).

**🟡 IN-52 — La FAQ de infosec omite el plan Starter.**
`plan-seguridad` §12.2 responde a un cuestionario de cliente mencionando *"plan estándar"* y *"plan enterprise"*, como si hubiera dos planes. Hay tres.
→ Documento de cara al cliente con información incompleta.

**🟡 IN-53 — Algoritmo de hashing de contraseñas.**
`constitucion.md` Artículo 3: *"hash usando **bcrypt o argon2id**"*.
`spec-tecnica` §6.5, `plan-seguridad`, `plan-implementacion`: **argon2id** exclusivamente.
→ Menor: los planes son más estrictos que la norma, lo cual es aceptable. Vale unificar.

## Testing y calidad

**🟡 IN-32 — La pirámide de testing tiene distinta forma en cada documento.**
`spec-tecnica` §7.1: **70 % unit / 20 % integration / 10 % E2E** (3 niveles).
`plan-testing` §3.1: **60 % unit / 25 % integration / 10 % contract / 5 % E2E** (4 niveles + exploratorio manual).
→ El plan de testing introduce una capa de **contract testing** (schemathesis contra OpenAPI, con exigencia de 100 % de endpoints y eventos) que la spec no contempla en absoluto.

**🟡 IN-54 — Tiempo máximo de la suite unitaria.**
`constitucion.md` Artículo 2 y `spec-tecnica` §7.1.1: *"menos de **cinco minutos**"*.
`plan-testing` §5: suite unitaria completa **< 60 segundos**; test individual < 5 ms.
→ El plan de testing es 5× más estricto. No es contradicción real (cumplir 60 s cumple 5 min), pero conviene unificar el número que se comunica como compromiso.

**🟡 IN-46 — Conteo de capítulos declarado vs real.**
`plan-testing` línea 35: *"El documento está organizado en **doce** capítulos"* — la estructura real llega al capítulo 14.
→ Trivial, pero indica que los documentos se editaron después de escribir su propia introducción, lo que refuerza `SU-12`.

## Planificación y conteos internos

**🟡 IN-37 — Conteos internos del plan de implementación no cierran.**
Portada: *"~190 tareas atómicas"*. Cierre §7.6: *"**ciento noventa y cuatro**"*. Rango real T-001..T-194 = **194**. ✅ el cierre tiene razón.
Bloque 1.2 (Stock): la tabla de §3.1 declara **50 tareas**; la tabla de trazabilidad de §7.1 declara el rango T-063..T-114 = **52 tareas**. ❌
Ola 0: *"aproximadamente cuarenta"* vs T-001..T-042 = 42.

**🟡 IN-38 — "Ola 2" y "F2" usados como sinónimos sin definirlo.**
`plan-implementacion` §3.2: los conectores a MercadoLibre y Facebook *"se posponen a **Ola 2**"*. §6.2.3: *"se posponen a la fase **F2**"*. El documento nunca define "F2" ni aclara la equivalencia.
→ Manifestación local del problema mayor de `IN-05`.

**🟡 IN-39 — Referencia a la tarea T-235, que no existe.**
`plan-implementacion` T-021: *"Los endpoints de creación de tenant viven en `/admin` (**T-235** en olas posteriores)"*. El documento llega hasta T-194. No hay explicación de qué ocupa T-195..T-234.

**🟡 IN-40 — La "cadena crítica de event bus" apunta a tareas equivocadas.**
`plan-implementacion` §3.3: *"Cadena de event bus (Ola 0): **T-040 a T-046**"*, declarada prerrequisito de toda comunicación inter-módulo asíncrona.
Pero T-040 es *"Setup de auth en frontend con NextAuth"* y T-043..T-046 son endpoints de onboarding de tenant. La infraestructura real de eventos es **T-016** (`core/events.py`, Redis Streams).
→ Rango mal referenciado. Un agente que siga esa cadena implementaría lo incorrecto.

**🟡 IN-41 — Tamaño del programa de early adopters: 10-15 vs 15 vs 10-12.**
`mejoras-y-saas` §8 (Fase 0): *"entre **diez y quince** agencias"*. §12 (Programa Pionero): *"**quince** agencias seleccionadas"*. `plan-gtm` §4: *"Tamaño objetivo: **10 a 12** tenants"*; hito de Ola 1: *"**12** early adopters firmados"*. `spec-tecnica` §9.4 (feature flags): *"agencias early adopter (**cinco a diez** tenants)"*.
→ Cuatro cifras. La de la spec (5-10) es la que gobierna el rollout progresivo de features, así que importa técnicamente.

**🟡 IN-42 — Las metas comerciales de los dos documentos de negocio no son la misma proyección.**
`mejoras-y-saas` §11: **220 agencias** activas y **MRR ARS 30 millones** a 24 meses. §14: 150 cuentas al cierre del año 2, 260 al cierre del año 3.
`plan-gtm` §13: Ola 2 (6-12 m) = **50-80 tenants**, MRR **USD 8.000-15.000**; Ola 3 (12-24 m) = **200+ tenants**, MRR **USD 35.000-60.000**.
→ Los órdenes de magnitud de tenants son compatibles (~200-220 a 24 meses), pero el MRR está en monedas distintas y no es convertible sin fijar un tipo de cambio. Ver `IN-04`.

## Producto, UX y marca

**🟡 IN-20 — Umbral de "lead sin atención": cuatro valores.**
`historias-usuario` HU-E4-006: *"más de **tres días** sin actividad en su etapa"*.
`plan-implementacion`: *"lead idle threshold: **5 días** (default, configurable)"*, cron diario a las 9:00.
`manual-usuario` §4.4: reporte de leads no contactados = estado Nuevo con más de **24 horas**.
`manual-usuario` §5.3: *"Leads que llevan más de **48 horas** en estado Nuevo sin contactar: son la primera causa de pérdida"* — **contradicción interna del manual**.
`mejoras-y-saas` §7.2: *"recordar al vendedor reseguir un lead que lleva **tres días** sin contacto"*.
→ Son probablemente dos conceptos distintos mezclados: *lead nuevo sin primer contacto* (24-48 h) y *lead sin actividad en su etapa* (3-5 días). Ningún documento los distingue.

**🟡 IN-21 — Duración del trial: 30 días vs 14 días.**
`mejoras-y-saas` §10: *"periodo de prueba gratuita de **treinta días** con onboarding asistido"*, repetido en §12.
`plan-gtm` §3.2: *"Trial: **14 días**, todas las features Pro, sin tarjeta"*, con touchpoints comerciales al día 3, 7 y 12.
→ Afecta `tenants.trial_ends_at`, la lógica de conversión y toda la cadencia comercial del GTM.

**🟡 IN-24 — El pipeline configurable desde el MVP tensiona el Principio 2.**
`constitucion.md` Principio 2 usa *exactamente este caso* como ejemplo de lo que **no** hay que hacer: *"hacer que el pipeline tenga etapas configurables desde el día uno"* aparece citado como la tentación a resistir.
Sin embargo, el glosario de la misma constitución define pipeline como *"secuencia ordenada de etapas **configurables**"*, y `plan-implementacion` implementa `pipeline_stages` configurable en el MVP (T-139 a T-153, épica E4).
→ Contradicción **dentro de la constitución** y entre la constitución y la implementación. `historias-usuario` la ubica en F2 (Should), lo que sería coherente con el principio; el plan de implementación la mete en el MVP.

**🟡 IN-25 — Disponibilidad de la API pública por plan.**
`plan-gtm` §3.2: API pública = **No / Read-only / Completa** (Starter/Pro/Enterprise).
`manual-usuario` §9.6: API pública **solo Enterprise**.
`historias-usuario` HU-E2-009: API pública de stock es *Could*, **Fase 5** — es decir, no existe todavía en ninguno de los dos.
→ El GTM está vendiendo como diferencial de plan Pro algo que el backlog ubica en la última fase.

**🟡 IN-26 — Pasos del wizard de onboarding: 4 vs 5.**
`historias-usuario` HU-E1-002: asistente con **4 pasos** — datos de la agencia, sucursales, usuarios, integraciones.
`manual-usuario` §2.2: **5 datos** — nombre comercial, razón social + CUIT, dirección de sucursal principal, teléfono/email, logo.
`plan-implementacion`: *"pasos del wizard onboarding: **5**"*.
→ Probablemente el manual describa los campos del *paso 1* y las historias los pasos completos. Confundido en las tres fuentes.

**🟡 IN-27 — Estrategia de despliegue por defecto: blue-green vs rolling.**
`spec-tecnica` §9.1-§9.2: **blue-green** como estrategia estándar (etapa 9 del pipeline), con canary opcional al **5 %**.
`plan-sre` §9.1: **rolling** como *default*; blue-green solo para cambios de mayor riesgo; canary con progresión **1 % → 5 % → 25 % → 50 % → 100 %**.
→ Distinta estrategia por defecto y distinta progresión de canary.

**🟡 IN-28 — Tiempo objetivo de rollback: tres cifras.**
`constitucion.md` Artículo 5: *"Los rollbacks deben ser posibles en **menos de quince minutos**"*.
`spec-tecnica` §9.2: el switch blue-green *"toma **menos de un minuto**"*.
`plan-sre` §9.7: *"tiempo medio de rollback objetivo **< 30 min**"*.
→ El plan de SRE fija un objetivo **el doble de laxo** que la norma constitucional.

**🟡 IN-36 — El ICP del GTM y el del Brand Book describen agencias distintas.**
`plan-gtm` §2.1: *"agencias argentinas de vehículos con **tres a quince** vendedores activos, stock entre **cuarenta y trescientos** vehículos"*, ingresos $30M-$300M ARS/mes, ciudades > 100.000 habitantes.
`brand-book` §2: *"agencia... mediana o chica, con entre **uno y cuatro** vendedores activos, con stock entre **veinte y doscientos** vehículos"*.
→ Los rangos apenas se solapan. Ambos documentos declaran derivar de la misma capa estratégica. Esto afecta el tono de voz, el diseño de la UI, el pricing y la segmentación comercial: no se le habla igual a una agencia de 2 vendedores que a una de 15.

**🟡 IN-43 — Umbral de "stock antiguo" dentro del manual: 90 vs 60 días.**
`manual-usuario` §4.4: *"Stock antiguo: vehículos que llevan más de **90 días** sin moverse"*.
`manual-usuario` §8.2.5: *"Pasados los **60 días**, las probabilidades de venta caen significativamente"*.
→ Contradicción interna del manual. Define el umbral de un reporte y de una alerta.

**🟡 IN-44 — Nivel de contraste WCAG del color institucional: AA vs AAA.**
`brand-book` §5.6 (tabla): azul institucional sobre blanco = *"AA cumplido"*.
`brand-book` §6.4.4: *"El azul institucional sobre blanco cumple **AAA** (más de 7:1)"*.
→ Contradicción interna del brand book sobre el mismo par de colores.

**🟡 IN-45 — El "Rojo crítico" del brand book no es rojo.**
`brand-book` §6.2 y §12.1: **Rojo crítico = `#974706`** (RGB 151,71,6) — es un marrón anaranjado oscuro.
Y **Amarillo atención = `#9C5700`** (RGB 156,87,0) — también un ocre oscuro.
→ Los dos colores funcionales de *error* y *advertencia* son visualmente casi idénticos, lo que rompe la propia regla del documento de tener colores distintos por estado. Muy probablemente sea un error de transcripción del `.docx`.

**🟡 IN-47 — Nombre del botón de alta de vehículo.**
`historias-usuario` HU-E2-001: *"Stock → **Nuevo vehículo**"*. `manual-usuario` §2.7.1: *"Stock → **Agregar vehículo**"*.
→ Trivial, pero el manual es lo que lee el cliente y las historias son los criterios de aceptación de los tests E2E.

**🟡 IN-48 — El manual de usuario no documenta dos módulos completos.**
El manual **no cubre permutas** (épica E6, 7 HU) ni **financiación** (épica E7, 8 HU) — ni siquiera en el glosario. Tampoco cuenta corriente ni conciliación bancaria (E9), y menciona la gestión documental (E8) solo de pasada.
→ Coherente si el manual documenta únicamente el alcance del MVP, pero eso **no está declarado en ninguna parte** y el manual se presenta como completo. Deja al cliente sin documentación de los tres módulos que constituyen el diferencial vertical del producto.

**🟡 IN-50 — Sucursales de Enterprise: ilimitadas o hasta 5.**
`mejoras-y-saas` §10: Enterprise = *"soporte multi-sucursal"* sin tope; usuarios y vehículos *"Ilimitados"*.
`plan-gtm` §3.2: Enterprise = **hasta 5 sucursales**, **15 usuarios**.
→ Sub-caso de `IN-03`, pero con implicancia comercial propia: "Enterprise ilimitado" y "Enterprise con topes" son propuestas de valor distintas.

**🟡 IN-58 — El brand book estructura un tagline pero nunca lo define.**
`brand-book` §9.2 lista *"logo + tagline"* como elemento del footer, pero el texto del tagline no aparece en ninguna parte de las 965 líneas del documento.
→ Falta un activo de marca que el propio documento da por existente.

---

# Parte 3 — Preguntas abiertas priorizadas

| Prioridad | Pregunta | Bloquea | Decisor |
|---|---|---|---|
| ✅ ~~Crítica~~ | ~~`PA-01` — ¿Cuál es el orden de precedencia entre documentos cuando se contradicen?~~ **RESUELTA** por [`ADR-000`](../docs/adr/ADR-000-precedencia-documental.md) (2026-08-13): jerarquía N0→N4 con competencia por dominio; recencia descartada por evidencia de los metadatos `.docx`. `SU-12` validado. Resuelve mecánicamente `IN-22`, `IN-29` e `IN-31`. | ~~Todo~~ | Tech Lead + Product Manager |
| 🟡 ~~Crítica~~ | ~~`PA-02` — ¿4 roles o 3? ¿`super_admin` va en `user_role_enum`, en tabla aparte, o solo en Keycloak?~~ **DECIDIDA** por [`ADR-017`](../docs/adr/ADR-017-catalogo-de-roles-y-super-admin.md): **4 roles en el sistema, 3 en `user_role_enum`**; `super_admin` en **tabla aparte** exenta de RLS, con `users.tenant_id` intacto en `NOT NULL`. ⏳ **Condicionada a la ratificación de la enmienda [`E-001`](../docs/adr/E-001-enmienda-glosario-super-admin.md)** — discusión abierta hasta el 20-ago-2026. (`IN-01`, `IN-02`) | Migración inicial, RBAC, tests de autorización | Tech Lead |
| **Crítica** | `PA-03` — ¿La facturación es en ARS o en USD? (`IN-04`) | Esquema de `plans`/`subscriptions`, integración con Mercado Pago, todo el GTM | Dirección |
| **Crítica** | `PA-04` — ¿Cuáles son los límites definitivos por plan, y se agrega la cuota de mensajes de WhatsApp al modelo? (`IN-03`, `IN-50`) | `PlanLimitsService`, seed de `plans` | Product Manager + Dirección |
| **Crítica** | `PA-05` — ¿`audit_logs` se retiene 24 meses o 5 años? ¿Qué obligación legal aplica realmente? (`IN-13`, `IN-35`, `IN-49`) | Particionado, costo de storage, compliance | Legal + Tech Lead |
| ✅ ~~Alta~~ | ~~`PA-06` — ¿Existe una tabla canónica de variables de entorno?~~ **RESUELTA** por [`ADR-013`](../docs/adr/ADR-013-variables-de-entorno.md) (2026-08-13): **35 variables en 12 grupos**, 15 sensibles. Dos correcciones sobre la KB (`APP_ENV` en vez de `ENVIRONMENT`, JWKS URL en vez de clave embebida) y un grupo nuevo (`PaymentSettings`). Cierra también `R-3`. | Setup de entornos, Terraform | Tech Lead |
| **Alta** | `PA-07` — ¿Cuántas etapas trae el pipeline por defecto y cómo se llaman? (`IN-10`) | Seed de onboarding de cada tenant | Product Manager |
| ✅ ~~Alta~~ | ~~`PA-08` — ¿Cuál es el umbral de cobertura del quality gate?~~ **RESUELTA** por `ADR-000`: **80 %** — N3 (`plan-testing`) no gana sobre N0 ni en su dominio propio. Se enmienda el **plan de testing**, no la constitución. (`IN-22`) | CI (bloquea merges) | Tech Lead |
| ✅ ~~Alta~~ | ~~`PA-09` — ¿El SLA es 99.0/99.5/99.9 o 99.9/99.9/99.95?~~ **RESUELTA** por `ADR-000`: **99.0 / 99.5 / 99.9** — competencia de dominio, disponibilidad es dominio propio de `plan-sre` (N3 > N1). Compatible con el SLO interno de 99.7 %. (`IN-31`) | Contratos, créditos, alertas | Dirección + SRE |
| **Alta** | `PA-10` — ¿Los objetivos de latencia de la constitución son SLOs o son objetivos de ingeniería con margen? (`IN-23`) | Alertas, tests de carga, Definición de Terminado | Tech Lead + SRE |
| **Alta** | `PA-11` — ¿Fases o Olas? Falta la tabla de equivalencia y las fechas de calendario del plan de implementación. (`IN-05`, `IN-38`) | Roadmap, compromisos comerciales | Product Manager |
| **Alta** | `PA-12` — ¿Existe signup público self-service en el MVP? El GTM lo vende; los planes técnicos lo postergan. (`IN-14`) | Funnel comercial, alcance del MVP | Product Manager |
| **Alta** | `PA-13` — ¿`domain_plate` es obligatorio? ¿Qué pasa con un 0 km o un usado recién recibido en permuta? (`IN-07`) | Migración de `vehicles` | Product Manager + Tech Lead |
| ✅ ~~Alta~~ | ~~`PA-14` — ¿Se corrige la numeración de ADRs del plan de implementación?~~ **RESUELTA** por `ADR-000` y **ejecutada** por [`ADR-018`](../docs/adr/ADR-018-anclas-de-adr-del-plan-de-implementacion.md) (2026-08-13): manda la numeración de `spec-tecnica` (N1 > N2). El plan solo referencia; la spec contiene. Las dos anclas divergentes quedan inventariadas con archivo y línea. (`IN-29`) | Trazabilidad de las 194 tareas | Tech Lead |
| **Media** | `PA-15` — ¿Cuál es el ICP real: 1-4 vendedores o 3-15? (`IN-36`) | Diseño de UI, pricing, mensaje comercial | Product Manager + Marketing |
| **Media** | `PA-16` — ¿Cuál es el límite duro de fotos por vehículo, separado de la recomendación de buena práctica? (`IN-09`) | Validación en `stock`, costo de storage | Product Manager |
| **Media** | `PA-17` — ¿Se distinguen "lead nuevo sin primer contacto" y "lead sin actividad en su etapa" como dos alertas distintas? (`IN-20`) | Crons de CRM | Product Manager |
| **Media** | `PA-18` — ¿El trial dura 14 o 30 días? (`IN-21`) | `trial_ends_at`, cadencia comercial | Dirección |
| **Media** | `PA-19` — ¿Canal en tiempo real: SSE o WebSocket? (`IN-08`) | Módulo `communication`, frontend | Tech Lead |
| ✅ ~~Media~~ | ~~`PA-20` — ¿Jaeger o Tempo? ¿Kubernetes con o sin ArgoCD?~~ **RESUELTA**: **Tempo** ([`ADR-016`](../docs/adr/ADR-016-trazas-distribuidas-tempo.md)) y **Kubernetes + ArgoCD** ([`ADR-015`](../docs/adr/ADR-015-orquestacion-kubernetes-y-gitops.md)). Obliga a corregir `T-030`, que hoy pide levantar Jaeger en `docker-compose`. (`IN-15`, `IN-16`) | Terraform, stack de observabilidad | SRE |
| **Media** | `PA-21` — El pipeline configurable en el MVP contradice el Principio 2 de la constitución. ¿Se acepta la excepción o se posterga a F2? (`IN-24`) | Alcance del MVP | Product Manager (requiere justificación documentada) |
| **Media** | `PA-22` — ¿Se unifican los contratos de API divergentes en un único `openapi.yaml` antes de empezar? (`IN-12`) | Generación de tipos del frontend | Tech Lead |
| **Media** | `PA-23` — ¿Quién es el proveedor concreto de OCR y de firma electrónica? Los documentos los nombran como categorías, nunca como productos. | Fase 4 (épica E8) | Tech Lead |
| **Media** | `PA-24` — ¿Con qué financieras concretas se firmó o se va a firmar? El plan exige "al menos dos al inicio" de la Fase 3, sin nombrarlas. | Fase 3 (épica E7) | Dirección |
| **Media** | `PA-25` — ¿Cuál es el contrato exacto del conector con el portal deRuedas? Es la integración más crítica del MVP y ningún documento especifica su API. | Épica E3 (MVP) | Tech Lead + equipo del portal |
| **Baja** | `PA-26` — ¿Cuál es el tagline de la marca? (`IN-58`) | Piezas de marketing | Marketing |
| **Baja** | `PA-27` — ¿`#974706` es realmente el "Rojo crítico"? Es visualmente indistinguible del "Amarillo atención" `#9C5700`. (`IN-45`) | Design system | Diseño |
| **Baja** | `PA-28` — ¿El manual de usuario debe cubrir permutas, financiación y cuenta corriente, o se declara explícitamente que documenta solo el MVP? (`IN-48`) | Documentación de cliente | Customer Success |
| **Baja** | `PA-29` — ¿Se corrigen los conteos internos del plan de implementación (194 tareas, bloque 1.2 = 52, cadena de event bus, T-235)? (`IN-37`, `IN-39`, `IN-40`) | Ejecución por agentes de IA | Tech Lead |
| **Baja** | `PA-30` — ¿Qué son los "13 componentes UI primitivos" que menciona el plan de implementación? No están enumerados en ningún documento, y el brand book remite al "design system técnico" que tampoco existe en el corpus. | Frontend | Diseño + Frontend |

---

# Parte 4 — Notas de discovery

Los seis campos de `discovery` del hook de estado se pudieron inferir **con alta confianza** de las fuentes. No se aplicó la regla de baja confianza a ninguno.

Única salvedad, para dejarla registrada:

```
[DISCOVERY] `stack` — el núcleo del stack (Python 3.12 + FastAPI, PostgreSQL 16, Redis 7,
Celery, OpenSearch, Next.js 14, React Native/Expo, Keycloak, S3-compatible) está declarado
de forma consistente en spec-tecnica.md y confirmado por plan-implementacion.md.
La capa de infraestructura NO: Kubernetes aparece como definitivo en un documento y como
condicional en otro, ArgoCD solo aparece en uno, y la herramienta de tracing es Jaeger o
Tempo según el documento. Ver IN-15 e IN-16.
El valor registrado en el estado cubre solo el núcleo confirmado.
```
