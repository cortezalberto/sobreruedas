# Decisiones y Supuestos

> Las **decisiones documentadas** (DD) están tomadas de los ADRs de `deRuedas-spec-tecnica.md` §5 y de los principios y trade-offs de `deRuedas-constitucion.md`.
> Los **supuestos inferidos** (SU) los derivé yo del corpus: no están escritos como tales en ninguna fuente, pero el conjunto de documentos solo tiene sentido si se sostienen. Cada uno indica cómo validarlo.

---

## Parte A — Principios constitucionales (vinculantes, ordenados por precedencia)

Cuando dos principios entran en tensión, **gana el que aparece primero**, salvo razón explícita y documentada en contrario.

1. **Verticalidad antes que generalidad** — deRuedas Gestión es para agencias de autos argentinas. No es un CRM genérico ni una plataforma extensible. Ante la tentación de abstraer ("que `vehículo` también sirva para motos"), la pregunta correcta no es "¿es posible?" sino "¿en qué momento del roadmap haría falta?". Si no es el próximo trimestre, se rechaza. **La generalización prematura es un anti-patrón explícito.**
2. **Simplicidad antes que features** — el producto compite contra Excel, cuadernos y WhatsApp. Una agencia que necesita más de **4 horas** de capacitación probablemente abandone. Se sacrifican opciones avanzadas para que lo central sea obvio, lineal y de pocos clics. *Criterio del valor por defecto razonable*: el sistema debe funcionar bien sin configurar nada.
3. **Datos como activo de primera clase** — identificador persistente + historial de cambios en toda entidad; borrados lógicos por defecto; migraciones que preservan la información; PII cifrada en reposo y enmascarada en logs.
4. **Multi-tenancy estricto desde el día uno** — no hay query, cache ni endpoint correcto sin discriminación por tenant. La filtración cross-tenant no es un bug: es un incidente crítico.
5. **Decisiones vinculantes y trazables** — toda decisión de alcance mayor a una historia se documenta como ADR. Los ADRs son vinculantes hasta ser reemplazados por un ADR posterior. **Las decisiones implícitas no son vinculantes** y pueden cuestionarse en cualquier momento.
6. **Calidad por defecto** — no hay fase de testing posterior al desarrollo. Las estimaciones incluyen tiempo de pruebas, documentación y revisión. Ante presión por entregar rápido, **se reduce el alcance, no la calidad**.
7. **Iteración con feedback real** — una funcionalidad construida sin validarse con al menos **3 usuarios reales** se considera especulativa y debe marcarse como tal en su release. Las opiniones internas no son evidencia; los datos y lo que dicen los clientes, sí.

### Procedimiento de decisión por alcance

| Alcance | Quién decide | Documentación |
|---|---|---|
| Local (un módulo o una historia) | El desarrollador, sujeto a code review | Ninguna adicional |
| De módulo (diseño completo de un módulo) | Responsable técnico del módulo, consultando al tech lead | Sección del documento técnico |
| Arquitectónica (transversal o irreversible) | Tech lead + al menos un revisor independiente | **ADR** |
| De producto (qué se construye) | Product manager con evidencia de usuario | Backlog / visión |

**Enmienda constitucional**: propuesta escrita → discusión abierta ≥ 5 días hábiles → aprobación por mayoría calificada de técnico y producto → registro con fecha, motivo y versión → comunicación. Las enmiendas se acumulan al final del documento; **la constitución original nunca se reescribe sin dejar rastro**.

---

## Parte B — Decisiones documentadas (ADRs)

⚠️ **Advertencia de trazabilidad**: la spec técnica y el plan de implementación asignan **temas distintos a los mismos números de ADR**. Ver `IN-29`, bloqueante para la trazabilidad de tareas.

| ADR | Tema según `spec-tecnica.md` | Tema según `plan-implementacion.md` | ¿Coinciden? |
|---|---|---|:---:|
| ADR-001 | Arquitectura modular monolítica | *(no referenciado)* | — |
| ADR-002 | **PostgreSQL** como base principal | **Migrations (Alembic)** | ❌ |
| ADR-003 | Python + FastAPI | *(no referenciado)* | — |
| ADR-004 | Next.js para frontend web | Frontend (Next.js) | ✅ |
| ADR-005 | **React Native con Expo** | **OpenSearch** | ❌ |
| ADR-006 | Multi-tenancy: discriminator + RLS | RLS | ✅ |
| ADR-007 | Autenticación OAuth2/OIDC con Keycloak | Auth con Keycloak | ✅ |
| ADR-008 | Object storage S3-compatible | Storage (S3-compatible) | ✅ |
| ADR-009 | Eventos con Redis Streams + Celery | Event bus (Redis Streams) | ✅ |
| ADR-010 | WhatsApp Business Cloud API directa | *(no referenciado)* | — |
| ADR-011 | OpenSearch para búsqueda full-text | *(referenciado como ADR-005)* | ❌ |
| ADR-012 | Feature flags con backend propio | *(no referenciado)* | — |

### DD-01 — ADR-001: Arquitectura modular monolítica con eventos asíncronos *[Aceptado]*

**Decisión**: un único repositorio, un único proceso de aplicación, organizado internamente en módulos delimitados con interfaces explícitas. Las comunicaciones que admiten asincronía pasan por Redis Streams + workers Celery.
**Contexto**: equipo inicial de 4-6 ingenieros, dominio acotado, time-to-market crítico.
**Alternativas**: *Microservicios desde el día uno* — descartado por overhead operacional excesivo para el tamaño del equipo y por la inmadurez de las fronteras del dominio. *Monolito puro sincrónico* — descartado porque las integraciones externas son inherentemente asíncronas.
**Trade-offs aceptados**: el escalado es vertical hasta que se decida extraer servicios. Mitigación: fronteras de módulo limpias para hacer factible la extracción futura.

### DD-02 — ADR-002: PostgreSQL 16 como base relacional principal *[Aceptado]*

**Decisión**: PostgreSQL 16 con extensiones `pgcrypto` (cifrado de campos), `pg_trgm` (búsqueda fuzzy), `PostGIS` (geolocalización de sucursales) y RLS nativo.
**Alternativas**: *MySQL* — descartado por menor robustez en tipos avanzados (JSONB, arrays, geo), políticas RLS más limitadas y menor familiaridad del equipo. *MongoDB* — descartado porque el dominio es predominantemente relacional, con muchos joins.
**Trade-offs**: el escalado horizontal de escrituras requiere sharding manual o migración futura. Aceptable para el volumen proyectado a 3 años.

### DD-03 — ADR-003: Python 3.12 + FastAPI *[Aceptado]*

**Decisión**: Python 3.12 con FastAPI, tipado con Pydantic v2, OpenAPI generado desde el código.
**Alternativas**: *Node.js + NestJS* — técnicamente viable, descartado principalmente por **menor alineamiento con la capa de IA** prevista para fases posteriores. *Go* — mejor performance bruta, descartado por menor productividad en MVP y menor disponibilidad de talento.
**Justificación estratégica clave**: la continuidad del stack hacia la capa de IA (índice de precios, recomendaciones, generación automática de avisos) sin saltos tecnológicos.
**Trade-offs**: menor performance bruta que Go o Rust. Mitigación: optimización selectiva de hotspots.

### DD-04 — ADR-004: Next.js 14+ para frontend web *[Aceptado]*

**Decisión**: Next.js 14+ con App Router, React, TypeScript, Tailwind CSS y sistema de componentes propio basado en Radix UI.
**Alternativas**: *React puro con Vite* — descartado por requerir SSR adicional para SEO. *SvelteKit* — descartado por base de talento más chica en Argentina.
**Trade-offs**: la complejidad del modelo dual server/client components requiere disciplina. Mitigación: convenciones documentadas en el repositorio.

### DD-05 — ADR-005: React Native con Expo *[Aceptado]*

**Decisión**: React Native con Expo SDK y Expo Router. Módulos nativos solo cuando Expo no cubra la funcionalidad (ej.: escaneo OCR de dominio).
**Alternativas**: *Nativas separadas (Swift/Kotlin)* — descartado por costo y velocidad. *Flutter* — descartado por requerir aprender Dart y no capitalizar el conocimiento de React del equipo.

### DD-06 — ADR-006: Multi-tenancy con discriminator column + RLS *[Aceptado]*

**Decisión**: `tenant_id NOT NULL` en toda tabla de negocio + Row-Level Security de PostgreSQL como defensa en profundidad. `SET LOCAL app.current_tenant` al inicio de cada request.
**Alternativas**: *Schema-per-tenant* — descartado por complejidad operacional de mantener cientos de schemas y migrarlos todos, y por límites prácticos de PostgreSQL. *Database-per-tenant* — descartado por costo y por dificultad de queries cross-tenant para reportes y administración.
**Trade-offs aceptados**: el riesgo de olvidar el filtro en una query está siempre presente. Mitigación: RLS como red de seguridad + auditoría automatizada en code review + tests de aislamiento bloqueantes en CI.
**Es la decisión de mayor alcance del sistema.**

### DD-07 — ADR-007: Autenticación OAuth2/OIDC con Keycloak autohospedado *[Aceptado]*

**Decisión**: Keycloak como servicio de identidad, autohospedado. JWT RS256.
**Alternativas**: *Auth a medida* — descartado por regla constitucional (Artículo 3). *Auth0 / Cognito* — descartado por costo a escala y dependencia de proveedor.
**Trade-offs**: operar Keycloak agrega carga operacional. Mitigación: documentación operativa específica.
✅ **Tensión resuelta el 17-ago-2026 por [`ADR-026`](../docs/adr/ADR-026-autenticacion-delegada-sin-password-hash.md)**: la columna `password_hash` **no se crea**. `users` es el espejo local del usuario de Keycloak, y el login es Authorization Code + PKCE con el frontend como cliente OIDC. La spec se contradecía a sí misma (§221 daba la columna, §1546 decía que la aplicación nunca maneja contraseñas); ganó §1546, respaldada por N0, N3 y T-040.

### DD-08 — ADR-008: Object storage S3-compatible *[Aceptado]*

**Decisión**: S3 o GCS según el proveedor cloud. URLs firmadas con TTL corto: **5 minutos** para fotos, **30 minutos** para documentos. CDN para fotos públicas; URL firmada directa para documentos privados.
**Trade-offs**: dependencia del proveedor. Mitigación: SDK genérico S3 (`boto3`) que permite migrar a otro proveedor compatible. En desarrollo local se usa **MinIO**.

### DD-09 — ADR-009: Eventos de dominio con Redis Streams + Celery *[Aceptado]*

**Decisión**: Redis Streams como broker de eventos, Celery como worker framework. Streams nombrados por dominio (`stock-events`, `crm-events`, …). Reintentos con backoff exponencial; dead-letter stream tras agotarlos.
**Alternativas**: *RabbitMQ* — descartado por complejidad operacional adicional frente al beneficio. *Kafka* — descartado por overkill para el volumen proyectado.
**Justificación**: Redis ya está presente para cache; se reutiliza infraestructura.
**Trade-offs**: Streams no ofrece las garantías ni las herramientas de Kafka. Suficiente para el alcance proyectado.

### DD-10 — ADR-010: WhatsApp Business Cloud API directa, sin BSP *[Aceptado]*

**Decisión**: integración directa con la Cloud API oficial de Meta, evitando proveedores BSP intermediarios.
**Justificación**: reduce costos y elimina un eslabón en la cadena de fallos.
**Trade-offs**: mayor responsabilidad operacional (gestión de templates, calidad del número, políticas de Meta). Declarado aceptable.
**Riesgo asociado reconocido**: dependencia de Meta. Mitigación declarada: diseño multi-canal desde el inicio (SMS, email), contratos directos con Meta, monitoreo de alternativas.

### DD-11 — ADR-011: OpenSearch para búsqueda full-text *[Aceptado]*

**Decisión**: OpenSearch (fork open-source de Elasticsearch) como motor de búsqueda **secundario**. **PostgreSQL sigue siendo la fuente de verdad**; OpenSearch se sincroniza por eventos de dominio.
**Trade-offs**: complejidad operacional adicional. Mitigación: usar el servicio gestionado del proveedor cloud.

### DD-12 — ADR-012: Feature flags con backend propio *[Aceptado]*

**Decisión**: tabla `feature_flags` + servicio de evaluación cacheado, con API `is_enabled(flag, context)`. Administrados desde el backoffice por el Super Admin.
**Alternativas**: *LaunchDarkly y similares* — descartado por costo en esta etapa. Reconsiderable en Fase 5.

---

## Parte C — Trade-offs explícitos ya resueltos por convención

No se rediscuten sin enmienda formal a la constitución.

| Trade-off | Se prioriza | Se sacrifica | Justificación |
|---|---|---|---|
| Velocidad vs. completitud | Liberar funcionalidad útil rápido | Cobertura de casos borde teóricos | La exhaustividad anticipada ralentiza el aprendizaje y produce código que se descarta antes de usarse |
| Build vs. buy | **Comprar/integrar** componentes maduros | Control total | Se compra: auth, observabilidad, mensajería, OCR, firma electrónica, cloud, DB. Se construye: stock, CRM, permutas, integración con financieras, motor de inteligencia |
| Configurabilidad vs. opinión fuerte | **Defaults razonables** | Flexibilidad amplia | La configurabilidad se gana con datos de uso, no se asume al inicio |
| Verticalidad vs. extensibilidad | **Diseñar solo para autos** | Reutilización en otros verticales | Si se expande a motos/maquinaria/embarcaciones, se evaluará entonces si extender o construir productos paralelos |
| Performance vs. pureza arquitectónica | **Performance percibida** | Limpieza del modelo | Se aceptan desnormalizaciones, vistas materializadas y caches específicos en lecturas frecuentes, documentándolos explícitamente |

---

## Parte D — Supuestos inferidos

Ninguno de estos está escrito como supuesto en las fuentes. Son las condiciones que el corpus **da por sentadas** y que, de ser falsas, invalidan partes del plan.

### SU-01 — Las 550 agencias del portal son un canal de adquisición efectivo para el SaaS
**Supuesto**: la relación comercial existente por avisos se traduce en acceso privilegiado y conversión superior a la de un entrante desde cero.
**Origen**: `mejoras-y-saas` §12 ("asimetría favorable"), `plan-gtm` (funnel y metas de Ola 1-2).
**Riesgo si es falso**: el CAC real supera el rango USD 250-600 y la proyección financiera completa se cae. Es el supuesto de mayor apalancamiento del plan de negocio.
**Cómo validar**: medir la tasa de conversión del Programa Pionero / early adopters contra un grupo de control de agencias fuera de la base del portal.

### SU-02 — Las agencias van a pagar una suscripción *adicional* a la del portal
**Supuesto**: la suscripción del SaaS **se suma, no reemplaza** al ingreso por avisos.
**Origen**: `mejoras-y-saas` Iniciativa 7 (explícito: "se suma —no reemplaza—").
**Riesgo si es falso**: canibalización del ingreso actual; el modelo de composición de ingresos a 3 años no se cumple.
**Cómo validar**: seguir el ARPU combinado (avisos + SaaS) de los primeros 20 clientes convertidos, contra su ARPU histórico de avisos.

### SU-03 — El lock-in por datos efectivamente frena el churn
**Supuesto**: cargar stock, leads e histórico eleva el costo de cambio lo suficiente como para elevar la retención de avisos del ~70 % al >90 % anual.
**Origen**: `mejoras-y-saas` §11 (métrica estratégica declarada) — es la hipótesis que *justifica la inversión completa*.
**Riesgo si es falso**: el producto pierde su razón estratégica de ser; queda como un CRM vertical más, compitiendo por precio contra Pipedrive.
**Cómo validar**: cohortes. Comparar el churn anual de avisos entre agencias con SaaS y sin SaaS, a partir del mes 12.

### SU-04 — WhatsApp es el canal comercial dominante y va a seguir siéndolo
**Supuesto**: el 80-90 % de las comunicaciones comerciales de una agencia pasa por WhatsApp, y las políticas de Meta se mantienen viables en costo y acceso.
**Origen**: `mejoras-y-saas` §7.3 (la cifra), ADR-010 (la apuesta técnica).
**Riesgo si es falso**: el diferencial más valorado del producto se degrada. La ventana de 24 h y el costo por template ya son fricciones reales.
**Cómo validar**: monitorear el costo por conversación de Meta trimestralmente y la proporción de leads por canal en los tenants activos.

### SU-05 — Un equipo de 4-6 ingenieros puede sostener este alcance
**Supuesto**: el alcance de 12 épicas / 92 historias / 194 tareas atómicas es ejecutable con el equipo dimensionado (9 personas totales para el MVP, de las cuales ~5 son ingenieros).
**Origen**: ADR-001 ("cuatro y seis ingenieros"), `mejoras-y-saas` §9 (equipo de 9 personas).
**Riesgo si es falso**: el MVP se estira más allá de los 7 meses y la ventana de oportunidad declarada como "estrecha" se cierra.
**Cómo validar**: medir el throughput real de tareas completadas en las primeras 4 semanas de Ola 0 contra la estimación por tallas (XS/S/M/L).

### SU-06 — Redis Streams alcanza como event bus para el volumen proyectado
**Supuesto**: 5 millones de mensajes mensuales y los eventos de dominio asociados caben en Redis Streams sin necesidad de Kafka.
**Origen**: ADR-009 ("Kafka descartado por overkill"), NFR de capacidad.
**Riesgo si es falso**: pérdida de eventos o lag de consumers bajo carga; migración forzada del bus con el sistema en producción.
**Cómo validar**: test de carga sostenido al 3× del volumen proyectado, midiendo el lag p99 de consumers (SLO: < 60 s) y la tasa de DLQ (SLO: < 0,1 %).

### SU-07 — El monolito modular se puede descomponer si hace falta
**Supuesto**: las fronteras de módulo, sostenidas por la regla de import validada en CI, van a permitir extraer servicios sin una reescritura.
**Origen**: ADR-001 ("se diseña con fronteras de módulo limpias para que la extracción futura sea factible").
**Riesgo si es falso**: al llegar al techo de escalado (>1.000 tenants), la extracción resulta inviable y hay que reescribir.
**Cómo validar**: auditar trimestralmente las violaciones de frontera detectadas por el import linter y el acoplamiento real entre módulos.

### SU-08 — Las agencias pueden operar el producto con ≤ 4 horas de capacitación
**Supuesto**: la curva de aprendizaje es tan corta que la barrera de adopción se disuelve.
**Origen**: Principio 2 de la constitución (el umbral de 4 horas es explícito); el manual promete "operativo en menos de 20 minutos".
**Riesgo si es falso**: churn temprano en el segmento de agencias tradicionales, que es justamente el segmento objetivo.
**Cómo validar**: medir tiempo real hasta el primer vehículo cargado y hasta el primer lead cerrado en el programa de early adopters, contra los hitos declarados (día 3 config, día 7 primer vehículo, día 14 primer lead, día 30 primera operación).

### SU-09 — La base histórica del portal alcanza para valuar permutas
**Supuesto**: 17 años de avisos con precios pedidos (y en menor medida de cierre) permiten construir un `deruedas_index` con precisión suficiente para valuar un usado.
**Origen**: `mejoras-y-saas` Iniciativa 8, `swap_valuations.data_source = 'deruedas_index'`, Fase 3.
**Riesgo si es falso**: el módulo de permutas —diferencial vertical clave— pierde su ventaja frente a una tasación manual. Los precios *pedidos* no son precios *de cierre*.
**Cómo validar**: backtesting del índice contra un conjunto de operaciones reales cerradas, midiendo el error absoluto medio.

### SU-10 — Una sola región cloud es aceptable
**Supuesto**: operar en una única región sudamericana con multi-zona cumple los SLA comprometidos.
**Origen**: `mejoras-y-saas` §5 (São Paulo o Santiago), `plan-seguridad` lo declara **riesgo aceptado con revisión cada 12 meses**.
**Riesgo si es falso**: una caída regional excede el SLA de Enterprise y activa créditos contractuales.
**Cómo validar**: es el único supuesto que la fuente ya reconoce como riesgo. El ejercicio anual de DR completo (RTO 4 h) es la prueba.

### SU-11 — Los precios en pesos son sostenibles en el contexto macro argentino
**Supuesto**: se puede cobrar en ARS con actualización trimestral por CER/IPC sin destruir la unidad económica.
**Origen**: `mejoras-y-saas` §13 (mitigación del riesgo macro), `plans.price_ars`.
**Riesgo si es falso**: erosión del ARPU real, o migración forzada a USD — que es justamente lo que hace el plan GTM, generando la contradicción `IN-04`.
**Cómo validar**: la contradicción entre ARS y USD en los dos documentos comerciales **sugiere que este supuesto ya fue revisado sin actualizar toda la documentación**. Requiere confirmación explícita.

### SU-12 — El corpus documental está en el mismo momento de madurez ✅ *[VALIDADO — 2026-08-13]*
**Supuesto** (metadocumental): los 11 documentos, todos fechados "Versión 1.0 — Mayo de 2026", describen el mismo producto en el mismo estado.
**Origen**: las fechas de versión idénticas en todos los documentos.
**Riesgo si es falso**: las contradicciones catalogadas en [10_preguntas_abiertas.md](10_preguntas_abiertas.md) no son errores sino **versiones sucesivas del mismo diseño que no se sincronizaron**. En ese caso, resolverlas requiere saber cuál documento se escribió último, no cuál está "bien".
**Cómo validar**: revisar el historial de los `.docx` originales o preguntar a los autores. **Esta validación debería hacerse antes de resolver cualquier otra inconsistencia**, porque cambia el criterio de desempate.

**✅ Resultado de la validación** — se extrajo `docProps/core.xml` de los 13 `.docx` originales. El supuesto **queda CONFIRMADO**: los 11 documentos vinculantes se generaron en una única sesión de 8 h 41 min (6-may-2026, 14:31 → 23:12 ART), todos con `cp:revision = 1` y `created == modified`, es decir, **nunca editados después de generarse**. El único `.docx` con edición humana real es `justificacion.docx`, que no es vinculante.

**Consecuencia (contraintuitiva)**: al estar confirmado el supuesto, **la recencia queda descartada como criterio de desempate**. Los timestamps ordenan por *generación*, no por *deliberación* — y los últimos por fecha (`plan-gtm` 01:18, `manual-usuario` 02:12) son los menos autoritativos por contenido. El escenario de riesgo descrito arriba **no se cumple**: las contradicciones son deriva de generación, no revisiones sin propagar. No hay respuesta oculta que recuperar por arqueología; cada una exige una decisión.

Formalizado en [`ADR-000`](../docs/adr/ADR-000-precedencia-documental.md), que también cierra `PA-01`.
