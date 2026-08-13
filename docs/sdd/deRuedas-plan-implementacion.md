**Plan de Implementación**

**con Tareas Atómicas**

***deRuedas Gestión***

Capa Tasks del cuerpo SDD

*Ola 0 (Fundación) + Ola 1 (MVP funcional)*

*Épicas E1 a E5 · ~190 tareas atómicas*

Versión 1.0 — Mayo de 2026

**1. Introducción y propósito**

Este documento es la cuarta capa del cuerpo SDD del proyecto deRuedas Gestión, complementaria a la Constitución, al Plan estratégico y SaaS, al Backlog de historias de usuario y a la Especificación Técnica de Diseño. Mientras esos cuatro documentos responden las preguntas “qué reglas se aplican”, “qué se construye y por qué” y “cómo se diseña técnicamente”, este documento responde la pregunta “con qué tareas concretas se ejecuta”.

Es la única capa del cuerpo SDD diseñada como input directo para sesiones de codificación con asistentes de inteligencia artificial. Cada tarea atómica está pensada para ser ejecutada de extremo a extremo en una sesión de IA bien guiada, sin que el agente tenga que reconstruir el contexto del proyecto desde cero ni inferir convenciones. Esto se logra mediante tres mecanismos: el formato uniforme de las fichas de tarea con campos fijos; las plantillas canónicas de prompts en la sección 5 que el agente reutiliza con variables; y la trazabilidad bidireccional con el resto del cuerpo documental, que le permite al agente consultar la Constitución, las historias o la Especificación Técnica cuando una tarea lo refiere.

**1.1 Audiencia**

El documento tiene tres audiencias. La primera son las sesiones de IA que ejecutan las tareas, que lo consumen como entrada principal junto con los demás documentos del cuerpo SDD. La segunda son los desarrolladores humanos que orquestan el proceso: crean las sesiones, eligen qué tarea ejecutar, revisan el código producido y mergean. La tercera son los responsables de planificación (tech lead, product manager) que usan el documento para entender el orden de ejecución, el progreso y las dependencias críticas.

**1.2 Alcance de esta versión**

Esta primera versión cubre las dos olas iniciales del desarrollo. La Ola 0 es la fundación técnica del proyecto: estructura del repositorio, infraestructura de pruebas y observabilidad, autenticación, gestión de tenants y de usuarios, design system base. La Ola 1 es el MVP funcional, equivalente a las épicas E1 a E5 del backlog: onboarding y configuración de la agencia, gestión de stock de vehículos, publicación al portal deRuedas, CRM básico de leads y comunicación por WhatsApp.

Las olas posteriores —que cubren CRM avanzado, multi-canal, permutas, financiación, documentación electrónica, contabilidad, BI, mobile, administración interna— se especificarán en versiones posteriores del documento, una vez que la Ola 1 esté estabilizada. Esta decisión se justifica por dos razones: las olas tempranas siempre alteran las decisiones de las posteriores, por lo que detallar 600 tareas anticipadamente sería trabajo desperdiciado; y el documento se vuelve operativamente inmanejable si excede las 200 tareas vivas en simultáneo.

**1.3 Cómo leerlo**

Una sesión de IA que va a ejecutar una tarea no necesita leer todo el documento. El flujo recomendado es: el operador humano selecciona la tarea (por ejemplo T-046), el agente lee la ficha de la tarea en la sección 6, lee la plantilla de prompt referenciada en la sección 5, y consulta las secciones específicas de la Especificación Técnica y de la Constitución que la ficha cita. Las secciones 1 a 4 (introducción, convenciones, mapa de dependencias, estructura del repositorio) se leen una sola vez al ingresar al proyecto y se internalizan como contexto base.

**2. Convenciones del documento**

**2.1 Identificadores de tarea**

Los identificadores son correlativos globales del formato T-XXX, donde XXX es un número de tres o cuatro dígitos. Los identificadores son inmutables: una vez asignados, no se reutilizan ni se renombran. Cuando una tarea se cancela, su identificador queda reservado. Cuando se agregan tareas posteriormente, se les asignan los siguientes identificadores libres, sin reordenar los existentes.

**2.2 Tipos de tarea**

La taxonomía de tipos es cerrada y refleja la capa arquitectónica del trabajo. Permite que el operador humano filtre tareas por tipo cuando le conviene paralelizar (por ejemplo, varias migrations independientes pueden hacerse en simultáneo en sesiones distintas).

|  |  |
|:---|:---|
| **Tipo** | **Significado** |
| migration | Crear o modificar schema de base de datos vía Alembic. Generalmente fusionada con el modelo ORM correspondiente cuando son inseparables. |
| repository | Capa de acceso a datos. CRUD básico sobre una entidad usando el ORM. |
| service | Lógica de negocio orquestadora. Valida reglas de dominio, llama a repositories y publica eventos. |
| schema | Definición de schemas Pydantic para entrada y salida de la API. |
| endpoint | Endpoint REST en FastAPI: routing, auth, autorización, traducción de errores. |
| event | Publicador o consumidor de evento de dominio en Redis Streams. |
| frontend-component | Componente React reutilizable (formulario, tabla, badge, etc.). |
| frontend-page | Página o ruta de Next.js que orquesta varios componentes y hace fetch. |
| test-unit | Suite de pruebas unitarias para una unidad lógica (típicamente un service). |
| test-integration | Pruebas que tocan base de datos o servicios reales en contenedor. |
| test-e2e | Prueba de extremo a extremo con Playwright que ejecuta un flujo completo. |
| infra | Configuración de infraestructura, CI/CD, Docker, observabilidad. |
| docs | Documentación viva en repositorio (README, ADR posterior, runbook). |

**2.3 Estimación**

La estimación es relativa, expresada en talla. Cada talla corresponde aproximadamente al tiempo de una sesión bien guiada de IA, considerando que la sesión incluye codificación, tests, validación y refinamientos.

|  |  |  |
|:---|:---|:---|
| **Talla** | **Tiempo IA aprox.** | **Casos típicos** |
| XS | 20-40 minutos | Cambios pequeños, helpers, configs, una migration simple. |
| S | 40-80 minutos | Repository CRUD, endpoint REST simple, componente React medio. |
| M | 80-150 minutos | Service con lógica de dominio compleja, página completa con fetch y forms. |
| L | 150-240 minutos | Tareas que tocan tres o más capas, integraciones con servicios externos. |

Las tareas de talla XL no existen en este documento. Si una tarea pareciera necesitar más de cuatro horas, es señal de que debe partirse en dos o más tareas atómicas. Esa partición se realiza durante el refinamiento.

**2.4 Estados de la tarea**

Los estados son los siguientes y se llevan en una herramienta externa al documento (Linear, Jira, GitHub Projects, planilla).

- todo: tarea creada, sin trabajar.

- ready: dependencias cumplidas, lista para ejecutarse.

- in_progress: hay una sesión activa trabajando en la tarea.

- blocked: detenida por un impedimento externo (decisión pendiente, dependencia que no se cumplió como se esperaba).

- done: criterios de aceptación cumplidos, código mergeado.

- cancelled: descartada por cambio de alcance.

**2.5 Dependencias**

Las dependencias entre tareas son estrictas: una tarea no puede pasar a estado in_progress hasta que todas sus dependencias estén en estado done. Cuando una tarea se cancela, sus dependientes se replanifican. El mapa de dependencias se mantiene actualizado en el sistema de gestión externo y debe coincidir con el listado declarado en cada ficha de este documento.

**2.6 Trazabilidad con el resto del cuerpo SDD**

Cada tarea declara explícitamente qué historias del backlog ayuda a cumplir, qué secciones de la Especificación Técnica respeta, y qué artículos de la Constitución le aplican con particular relevancia. Esto permite navegar en ambas direcciones: desde una historia se pueden encontrar las tareas que la implementan, y desde una tarea se puede consultar la base normativa que justifica sus decisiones.

**3. Mapa de dependencias y olas**

**3.1 Olas de desarrollo**

Las olas son agrupaciones temporales y temáticas de tareas. Las tareas dentro de una ola pueden paralelizarse respetando dependencias internas; las tareas entre olas son secuenciales: la Ola N no arranca hasta que la Ola N-1 esté en estado done.

**Ola 0 — Fundación**

Cubre la infraestructura del proyecto y los módulos transversales que todo el resto del sistema usa: estructura del repositorio, Docker Compose para entorno local, pipeline de CI base, infraestructura de testing con factories y contenedores efímeros, observabilidad mínima con logs estructurados y métricas Prometheus, autenticación con Keycloak, gestión de tenants, gestión de usuarios y roles, design system base con tokens y componentes primitivos. Aproximadamente cuarenta tareas. Es prerrequisito de todo lo demás.

**Ola 1 — MVP funcional**

Cubre las épicas E1 a E5 del backlog. Una vez completa, el producto es lanzable a las primeras agencias early adopter. Aproximadamente ciento cincuenta tareas distribuidas en cinco bloques internos.

|  |  |  |  |
|:---|:---|:---|:---|
| **Bloque** | **Alcance** | **Tareas aprox.** | **Épica del backlog** |
| 1.1 | Onboarding y configuración de tenant: creación de cuenta, alta de sucursales, invitación de usuarios, configuración inicial. | 20 | E1 |
| 1.2 | Stock de vehículos: catálogos canónicos, alta y edición de vehículos, fotos, estados, importación CSV. | 50 | E2 |
| 1.3 | Publicación al portal deRuedas: integración del conector, sincronización inicial, manejo de errores y reintentos. | 15 | E3 (parcial) |
| 1.4 | CRM básico: contactos, leads, pipeline configurable, actividades, asignación a vendedores. | 40 | E4 |
| 1.5 | WhatsApp básico: alta del canal, conversaciones, envío y recepción de mensajes, templates aprobados. | 25 | E5 (núcleo) |

**3.2 Recortes deliberados respecto del backlog**

Esta versión del Plan recorta deliberadamente algunas funcionalidades del backlog que están dentro de las épicas E1 a E5 pero se postergan a una versión posterior del documento. Los recortes son los siguientes.

- E3 — Multicanal: incluido solo el conector a deRuedas. Conectores a MercadoLibre Vehículos y a Marketplace de Facebook se posponen a Ola 2.

- E5 — WhatsApp: incluido el flujo conversacional de extremo a extremo (envío, recepción, asignación, plantillas). Se posponen los chatbots conversacionales avanzados, los flujos automáticos de calificación con IA y los multi-númeropor sucursal.

- E2 — Stock: incluida la gestión completa pero sin el motor de pricing sugerido por IA, que se pospone hasta tener masa crítica de datos.

- E1 — Onboarding: incluido el flujo de setup vía interfaz administrativa. Se pospone el self-service de signup público que requiere integración con cobros recurrentes en producción.

**3.3 Paralelismo y críticas tempranas**

Dentro de cada ola, varias cadenas de tareas pueden ejecutarse en paralelo si hay capacidad de sesiones de IA. Las cadenas críticas, las que conviene priorizar porque son prerrequisito de muchas otras, son las siguientes:

- Cadena de auth y tenancy (Ola 0): T-001 a T-022. Toda tarea posterior asume que esto funciona.

- Cadena de stock core (Ola 1): T-064 a T-090. Es prerrequisito de CRM y publishing.

- Cadena de event bus (Ola 0): T-040 a T-046. Es prerrequisito de cualquier comunicación inter-módulo asíncrona.

**3.4 Asignación a sesiones de IA**

Recomendación operativa: una sesión de IA toma una sola tarea, la ejecuta hasta completarla con tests pasando, abre un pull request, y termina. La revisión humana ocurre fuera de la sesión. Las sesiones no se reutilizan para múltiples tareas porque el contexto se vuelve inestable y empiezan a aparecer derivas (decisiones inconsistentes, refactors innecesarios, regresiones). Si una tarea resulta más larga que su talla estimada, se interrumpe, se replantea (posiblemente partiéndola), y se reasigna.

**4. Estructura canónica del repositorio**

La estructura siguiente es vinculante. Todas las tareas que crean archivos respetan esta estructura, y ninguna sesión de IA puede inventar nuevas convenciones. Los cambios a la estructura requieren un ADR específico y se aplican como tarea explícita de tipo infra.

**4.1 Árbol del monorepo**

deruedas-gestion/

├── README.md

├── docker-compose.yml \# entorno local completo

├── docker-compose.test.yml \# contenedores efímeros para CI

├── .env.example \# variables de entorno con valores ficticios

├── .github/

│ └── workflows/ \# pipelines CI/CD

│ ├── ci.yml \# lint + tests en cada PR

│ ├── deploy-staging.yml

│ └── deploy-production.yml

├── docs/

│ ├── adr/ \# ADRs nuevos posteriores al SDD

│ ├── runbooks/ \# procedimientos operativos por componente

│ └── openapi.yaml \# spec OpenAPI generada y versionada

├── backend/

│ ├── pyproject.toml

│ ├── alembic.ini

│ ├── alembic/

│ │ └── versions/ \# migrations correlativas NNN_descripcion.py

│ ├── app/

│ │ ├── main.py \# bootstrap FastAPI, registro de routers

│ │ ├── config.py \# settings con Pydantic

│ │ ├── db/

│ │ │ ├── base.py \# Base declarativa SQLAlchemy

│ │ │ ├── session.py \# session factory + tenant context

│ │ │ └── enums.py \# enums PostgreSQL como Python Enum

│ │ ├── core/

│ │ │ ├── auth.py \# dependency get_current_user

│ │ │ ├── rbac.py \# require_role, permisos

│ │ │ ├── tenancy.py \# set_tenant_context

│ │ │ ├── errors.py \# DomainError + handlers Problem Details

│ │ │ ├── pagination.py

│ │ │ ├── idempotency.py

│ │ │ ├── events.py \# publisher / consumer de Redis Streams

│ │ │ ├── storage.py \# adapter S3-compatible

│ │ │ └── observability.py \# tracing, metrics, structured logs

│ │ └── modules/ \# un subdirectorio por dominio

│ │ ├── auth/

│ │ ├── tenancy/

│ │ ├── users/

│ │ ├── stock/

│ │ ├── publishing/

│ │ ├── crm/

│ │ ├── communication/

│ │ ├── trade_in/

│ │ ├── finance/

│ │ ├── documents/

│ │ ├── accounting/

│ │ ├── operations/

│ │ ├── analytics/

│ │ ├── notifications/

│ │ ├── audit/

│ │ └── admin/

│ └── tests/

│ ├── conftest.py \# fixtures comunes

│ ├── factories/ \# factory_boy por entidad

│ ├── unit/

│ ├── integration/

│ └── e2e/

├── frontend-web/ \# Next.js app del cliente

│ ├── package.json

│ ├── next.config.js

│ ├── tsconfig.json

│ ├── tailwind.config.ts

│ ├── src/

│ │ ├── app/ \# App Router

│ │ ├── components/ \# componentes reutilizables

│ │ │ ├── ui/ \# primitivos del design system

│ │ │ └── domain/ \# componentes específicos de dominio

│ │ ├── lib/

│ │ │ ├── api.ts \# cliente HTTP tipado

│ │ │ ├── auth.ts

│ │ │ └── i18n.ts

│ │ └── hooks/

│ └── tests/

│ ├── unit/

│ └── e2e/ \# Playwright

├── frontend-mobile/ \# React Native + Expo

│ ├── package.json

│ ├── app.json

│ ├── app/ \# Expo Router

│ ├── components/

│ └── lib/

├── frontend-admin/ \# Backoffice deRuedas

│ └── (estructura espejo de frontend-web)

├── infra/

│ ├── terraform/ \# IaC del entorno cloud

│ ├── k8s/ \# manifests si aplica

│ └── observability/

│ ├── prometheus.yml

│ ├── grafana/dashboards/

│ └── loki/

└── tools/

├── seed.py \# carga de datos demo

└── benchmark/ \# scripts de benchmark

**4.2 Estructura interna de un módulo backend**

Cada módulo del backend sigue una estructura interna idéntica. Esto permite que cualquier sesión de IA que trabaje sobre un módulo nuevo o modifique uno existente sepa dónde buscar y dónde escribir sin ambigüedad.

backend/app/modules/\<module\>/

├── \_\_init\_\_.py \# exports públicos del módulo

├── models.py \# ORM SQLAlchemy

├── schemas.py \# Pydantic in/out

├── repository.py \# acceso a datos

├── service.py \# lógica de negocio

├── routes.py \# router FastAPI con endpoints

├── events.py \# eventos de dominio (publishers + consumers)

├── exceptions.py \# DomainError específicos del módulo

└── permissions.py \# opcional: permisos finos del módulo

**4.3 Convenciones de nombres**

- Archivos Python: snake_case. Clases: PascalCase. Funciones y variables: snake_case.

- Archivos TypeScript: kebab-case para archivos de componentes (vehicle-form.tsx); PascalCase para nombres de componentes en código.

- Endpoints REST: kebab-case en paths, plural en recursos: /api/v1/sales-operations no /api/v1/salesOperation.

- Eventos de dominio: namespace.verb_past, ejemplo vehicle.created, lead.stage_changed.

- Migrations: NNN_descripcion_corta.py, donde NNN es el correlativo asignado por Alembic.

- Tablas: plurales en inglés, snake_case. Excepciones del dominio argentino sin traducción razonable: sucursales, permutas (siempre que el SDD lo declare así).

**4.4 Imports y barrel files**

Los módulos del backend exponen su superficie pública a través del archivo \_\_init\_\_.py. Los demás módulos solo importan desde la superficie pública, nunca desde archivos internos. Por ejemplo, está permitido from app.modules.stock import VehicleService pero está prohibido from app.modules.stock.service import VehicleService desde fuera del módulo. Esta regla es vinculante y se valida en CI mediante una regla de import linter.

**5. Plantillas de prompts canónicas**

Esta sección define las doce plantillas de prompts que cubren los tipos recurrentes de tarea. Cuando una ficha de tarea referencia una plantilla con el formato P-NN, la sesión de IA expande la plantilla con las variables específicas de la ficha y la ejecuta. Las plantillas evitan que cada ficha repita contexto, fuerzan consistencia entre tareas del mismo tipo y reducen la probabilidad de derivas.

**5.1 Estructura común a todas las plantillas**

Toda plantilla, al expandirse, produce un prompt con tres bloques. El primer bloque es el contexto base, idéntico para todas: cita la Constitución y la spec técnica del proyecto, declara el rol del agente, lista las convenciones generales del repositorio. El segundo bloque es la instrucción específica de la plantilla: qué hay que hacer, en qué archivos, con qué reglas particulares. El tercer bloque es el bloque de variables, que la ficha de tarea completa con valores concretos.

El contexto base que toda sesión recibe al inicio es el siguiente.

Sos un asistente de programación que ejecuta una tarea atómica del Plan

de Implementación de deRuedas Gestión.

Documentos de contexto que debés respetar (en orden de precedencia):

1\. Constitución del proyecto: principios y reglas vinculantes.

2\. Especificación Técnica de Diseño: arquitectura, datos, API, ADRs.

3\. Backlog de historias de usuario: criterios de aceptación funcionales.

4\. Plan de Implementación: este documento, secciones 1-4 (convenciones).

Reglas no negociables:

\- Multi-tenancy estricto: tenant_id en todas las queries y modelos.

\- Snake_case en backend Python; kebab-case en archivos TypeScript.

\- Tests obligatorios para toda regla de negocio nueva.

\- Cobertura no decrece. Tests deterministas (no flaky).

\- Imports solo desde la superficie pública de los módulos.

\- Logging estructurado con trace_id en toda operación significativa.

Tu output esperado:

\- Código que compile y pase tests.

\- Tests que cumplan los criterios declarados en la ficha.

\- Sin TODOs salvo los que la ficha autorice explícitamente.

\- Pull request con descripción que refiera a la ficha (T-XXX).

**5.2 P-01 — create-migration**

Plantilla para crear una migration de Alembic que cree o modifique tablas.

**Variables**

> • table: nombre de la tabla a crear o modificar.
>
> • ddd_section: sección del SDD donde está la especificación de la tabla (ej. “3.4”).
>
> • adrs: lista de ADRs aplicables (ej. “002, 006”).
>
> • dependencies: migrations previas requeridas.

**Contenido del prompt**

Crear una migration Alembic en backend/alembic/versions/ que cree la tabla

{{table}} siguiendo exactamente la especificación de la sección {{ddd_section}}

del SDD. Debe respetar los ADRs {{adrs}}.

Requisitos:

\- Todos los campos, tipos, constraints e índices de la sección {{ddd_section}}.

\- tenant_id NOT NULL con FK a tenants(id), salvo que el SDD declare otra cosa.

\- Timestamps timestamptz NOT NULL DEFAULT now(); deleted_at timestamptz NULL.

\- Habilitar RLS con política tenant_isolation que use

current_setting('app.current_tenant').

\- Crear índices declarados en el SDD; UNIQUE adicionales con WHERE deleted_at IS NULL.

\- Función downgrade() que revierta limpiamente.

\- Crear o modificar también el modelo SQLAlchemy en models.py del módulo.

\- Verificar con alembic check --autogenerate que no propone cambios adicionales.

**5.3 P-02 — create-pydantic-schema**

Plantilla para crear los schemas Pydantic de entrada y salida de una entidad.

**Variables**

> • entity: nombre de la entidad (ej. Vehicle).
>
> • module: módulo destino (ej. stock).
>
> • variants: variantes a generar (Create, Update, Read, ListItem).

**Contenido del prompt**

Crear los schemas Pydantic v2 de la entidad {{entity}} en

backend/app/modules/{{module}}/schemas.py.

Variantes a generar: {{variants}}.

Reglas:

\- Read incluye id, timestamps y deleted_at.

\- Create excluye id, timestamps, tenant_id (se infiere del contexto auth).

\- Update marca todos los campos como Optional con valor default = None,

para permitir PATCH parcial.

\- ListItem es subset compacto de Read (campos para listados, sin lo pesado).

\- Validators con field_validator y model_validator donde el SDD lo requiera

(formato de dominio, CUIT con dígito verificador, año en rango, etc.).

\- Configurar from_attributes=True para mapeo desde ORM.

\- Toda Optional debe tener su default explícito.

**5.4 P-03 — create-repository**

Plantilla para crear el repositorio CRUD de una entidad.

**Variables**

> • entity, module: como en P-02.
>
> • methods: métodos a generar (default: get, list, create, update, soft_delete, exists).
>
> • filters: filtros aceptados por list (ej. status, branch_id, q full-text).

**Contenido del prompt**

Crear la clase {{entity}}Repository en backend/app/modules/{{module}}/repository.py.

Métodos: {{methods}}.

Reglas:

\- Todas las queries filtran por tenant_id implícito mediante session context.

\- list acepta paginación (page, page_size) o cursor (last_id, limit).

\- list acepta filtros: {{filters}}.

\- list acepta ordenamiento (sort param con prefijo - para descendente).

\- get/list/exists ignoran filas con deleted_at IS NOT NULL.

\- soft_delete setea deleted_at = now(), no DELETE físico.

\- Usar SQLAlchemy 2.x select() / scalars(), no la API legacy.

\- No incluir lógica de negocio: solo acceso a datos.

\- Devolver siempre instancias del modelo ORM, no schemas Pydantic.

**5.5 P-04 — create-service-method**

Plantilla para implementar un método de servicio con lógica de dominio.

**Variables**

> • entity, module.
>
> • method: nombre del método (create, update, transition_status, etc.).
>
> • publishes_events: lista de eventos que el método publica.
>
> • validations: validaciones de dominio que el método aplica.

**Contenido del prompt**

Implementar {{entity}}Service.{{method}} en backend/app/modules/{{module}}/service.py.

Validaciones de dominio: {{validations}}.

Eventos a publicar: {{publishes_events}}.

Reglas:

\- Recibir AuthContext explícito como parámetro; no buscar user actual

desde un global thread-local.

\- Validaciones que fallan: levantar DomainError con código machine-readable

(ej. 'plate_exists', 'branch_not_in_tenant').

\- Llamar al repository para persistir; no escribir SQL directamente.

\- Publicar eventos AL FINAL, después de commit exitoso, no antes.

\- Devolver siempre el schema Read serializado, no la entidad ORM.

\- Logging estructurado con trace_id, tenant_id, action, entity_id.

**5.6 P-05 — create-rest-endpoint**

Plantilla para implementar un endpoint REST en FastAPI.

**Variables**

> • method: GET, POST, PATCH, DELETE.
>
> • path: path completo (ej. /api/v1/vehicles/{id}).
>
> • service_call: método del service que el endpoint invoca.
>
> • roles: roles autorizados (ej. \["manager", "admin_staff"\]).
>
> • idempotent: bool, si soporta Idempotency-Key (típico en POST).

**Contenido del prompt**

Implementar el endpoint {{method}} {{path}} en backend/app/modules/\<m\>/routes.py.

Llama al service: {{service_call}}.

Roles autorizados: {{roles}}.

Soporta Idempotency-Key: {{idempotent}}.

Reglas:

\- Auth con dependency get_current_user (lanza 401 si falta token).

\- Autorización con dependency require_role (lanza 403 si rol incorrecto).

\- Validación con schema Pydantic correspondiente a la entidad.

\- DomainError → 422 con Problem Details (RFC 7807) automático mediante handler.

\- Si idempotent: clave en cache Redis 24h; misma key + mismo payload = misma respuesta;

misma key + payload distinto = 409.

\- Logging estructurado.

\- Métricas Prometheus automáticas mediante middleware (no manual).

\- Status codes según convención sección 4.1.7 del SDD.

**5.7 P-06 — publish-domain-event**

Plantilla para publicar un evento de dominio en Redis Streams.

**Variables**

> • event_type: nombre del evento (ej. vehicle.created).
>
> • payload_fields: campos del payload data.
>
> • stream: stream destino (ej. stock-events).

**Contenido del prompt**

Definir el evento {{event_type}} en backend/app/modules/\<m\>/events.py.

Crear:

\- dataclass {{EventName}}Event con los campos {{payload_fields}}.

\- función publish\_{{event_name}}(payload, ctx) que llama al publisher

central de core/events.py.

Reglas:

\- Formato del envelope según sección 4.3 del SDD: event_id, event_type,

event_version, tenant_id, occurred_at, data.

\- event_id: UUID v7.

\- event_version: '1.0' inicialmente; incrementar mayor si cambian semantics.

\- tenant_id: del AuthContext.

\- occurred_at: timestamp del momento de publicación.

\- Stream destino: {{stream}}.

\- El publisher es idempotente: si el cliente reintenta con el mismo event_id,

no se duplica.

**5.8 P-07 — consume-domain-event**

Plantilla para implementar un consumidor de eventos en un worker Celery.

**Variables**

> • event_type, stream.
>
> • handler: lógica que se ejecuta al recibir el evento.
>
> • retry_policy: política de reintentos (default: 5 intentos con backoff exponencial).

**Contenido del prompt**

Implementar el consumidor del evento {{event_type}} desde el stream {{stream}}.

Reglas:

\- Suscripción mediante Celery beat consumer registrado en startup.

\- Idempotencia obligatoria: chequear que event_id no se procesó antes

en una tabla de processed_events o cache; si ya fue procesado, ack y skip.

\- Errores transitorios → reintento con backoff exponencial.

\- Errores permanentes (ej. payload inválido) → DLQ inmediato, no reintento.

\- Setear contexto multi-tenant antes de cualquier operación de DB:

set_tenant_context(payload.tenant_id).

\- Logging del trace_id propagado desde el evento publicador.

\- Métrica de duración del handler y de errores.

**5.9 P-08 — create-react-component**

Plantilla para crear un componente React reutilizable del design system.

**Variables**

> • name: nombre del componente (PascalCase).
>
> • file: ruta relativa dentro de frontend-web/src/components/.
>
> • props: contrato de props con tipos.

**Contenido del prompt**

Crear el componente React {{name}} en frontend-web/src/{{file}}.

Reglas:

\- Componente funcional con TypeScript estricto. No usar any.

\- Props interface explícita con todos los campos tipados.

\- Estilos exclusivamente con Tailwind y los tokens del design system

(sin colores hardcoded fuera de la paleta del proyecto).

\- Accesibilidad: roles ARIA correctos, navegable por teclado.

\- Sin dependencias en componentes externos al design system salvo Radix UI.

\- Storybook story en el mismo directorio: {{name}}.stories.tsx.

\- Test unitario con Testing Library.

**5.10 P-09 — create-form-component**

Plantilla para crear un componente de formulario con validación cliente.

**Variables**

> • name, file: como en P-08.
>
> • entity: entidad cuyo Create/Update implementa.
>
> • schema: schema Zod para validación cliente.

**Contenido del prompt**

Crear el formulario {{name}} en {{file}}.

Reglas:

\- React Hook Form con zodResolver({{schema}}).

\- Validación cliente espejo de la del backend; los mensajes en es-AR.

\- onSubmit recibe handler async; mostrar estado de loading.

\- Manejo de errores 422 del backend: mapear errors\[\].field a campos visibles.

\- Layout responsive: una columna en mobile, dos en desktop a partir de md.

\- Botones primarios y secundarios del design system.

\- Campos requeridos marcados visualmente.

\- Tab order coherente.

**5.11 P-10 — create-list-page**

Plantilla para crear una página de listado con paginación, filtros y búsqueda.

**Variables**

> • entity, route: ruta App Router (ej. /stock/vehicles).
>
> • filters: filtros visibles.
>
> • columns: columnas de la tabla.

**Contenido del prompt**

Crear la página de listado de {{entity}} en frontend-web/src/app{{route}}/page.tsx.

Reglas:

\- Server Component que hace fetch inicial, hidrata Client Component de tabla.

\- Paginación con query params en URL (page, page_size).

\- Filtros con query params; debounce 300ms en inputs de texto.

\- Tabla con columnas {{columns}}; sortable las que tienen sort en API.

\- Skeleton loader mientras carga.

\- Estado vacío con CTA para crear el primer registro.

\- Acciones por fila (editar, archivar) con confirmación.

\- Botón global de “Nuevo” que navega a la página de creación.

**5.12 P-11 — create-test-suite**

Plantilla para crear una suite de pruebas unitarias o de integración.

**Variables**

> • level: unit \| integration.
>
> • target: módulo y unidad bajo prueba (ej. stock.VehicleService.create).
>
> • scenarios: lista de escenarios a cubrir.

**Contenido del prompt**

Crear suite de pruebas {{level}} para {{target}} en tests/{{level}}/.

Escenarios a cubrir: {{scenarios}}.

Reglas:

\- pytest con fixtures de conftest.py.

\- Datos generados con factories (factory_boy), no hardcoded.

\- Cada test es independiente, no comparte estado con otros.

\- Para integración: contenedor PostgreSQL efímero con testcontainers;

transacción que se hace rollback al final del test.

\- Aserciones específicas: assert_called_with, valores exactos,

no solo “no levanta excepción”.

\- Tests de happy path + tests de error path obligatorios.

\- Sin mocks de la unidad bajo prueba; sí mocks de dependencias externas.

**5.13 P-12 — create-e2e-test**

Plantilla para crear una prueba de extremo a extremo con Playwright.

**Variables**

> • flow: nombre del flujo (ej. create_vehicle_with_photos).
>
> • steps: pasos del usuario en el flujo.
>
> • assertions: qué se verifica al final.

**Contenido del prompt**

Crear test E2E {{flow}} en frontend-web/tests/e2e/{{flow}}.spec.ts.

Pasos: {{steps}}.

Aserciones: {{assertions}}.

Reglas:

\- Login como usuario manager del tenant demo en beforeEach.

\- Selectores estables: data-testid o roles ARIA, nunca clases CSS.

\- waitFor para elementos dinámicos, no setTimeout.

\- Datos de prueba específicos del test, sin depender de state previo.

\- Cleanup explícito en afterEach si el test crea recursos.

\- Screenshot automático en fallo.

\- Test independiente del orden de ejecución.

**6. Tareas detalladas**

Esta sección contiene las fichas de las tareas atómicas, agrupadas por ola y bloque temático. Cada ficha sigue el formato definido en la sección 2 y referencia plantillas de la sección 5 cuando aplica.

**6.1 Ola 0 — Fundación**

Esta ola construye la infraestructura técnica del proyecto y los módulos transversales que todas las funcionalidades posteriores requieren. Su finalización es prerrequisito de la Ola 1.

**6.1.1 Infraestructura del proyecto**

**T-001 Crear estructura inicial del monorepo** *\[infra · S\]*

**Épica:** Fundación

**Spec técnica:** Plan de Implementación sección 4 (estructura canónica)

**Constitución:** Art. 1, 7

**Dependencias:** ninguna

**Archivos:** crear todo el árbol de directorios de la sección 4.1; README.md raíz; .gitignore; .env.example

**Descripción**

Crea la estructura de carpetas vacías del monorepo y los archivos raíz mínimos. No incluye código de aplicación. Es el punto de partida físico del proyecto.

**Especificación**

> • Crear todos los directorios del árbol de la sección 4.1, con archivos .gitkeep en los vacíos.
>
> • README.md con: descripción del proyecto, links a los cuatro documentos del cuerpo SDD, instrucciones de cómo levantar el entorno (apuntando a tareas posteriores).
>
> • .gitignore que cubre Python (\_\_pycache\_\_, .venv, .pytest_cache), Node (node_modules, .next), entornos (.env, .env.local), IDEs.
>
> • .env.example con todas las variables que el sistema lee, con valores ficticios y comentarios.

**Criterios done**

> • git init && primer commit ejecutado.
>
> • Árbol completo verificable con tree -L 3 .
>
> • README incluye los cuatro links a documentos del SDD.

**Tests requeridos**

> • No aplica (tarea de scaffolding).

**Prompt:** P-libre (no plantilla; usa la sección 4 del Plan como referencia única)

**T-002 docker-compose.yml para entorno local completo** *\[infra · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 2.2 (contenedores)

**Constitución:** Art. 1

**Dependencias:** T-001

**Archivos:** crear docker-compose.yml; docker-compose.test.yml; backend/Dockerfile; frontend-web/Dockerfile

**Descripción**

Define todos los servicios necesarios para levantar el entorno completo localmente con un solo comando docker compose up.

**Especificación**

> • Servicios: postgres-16 con extensiones habilitadas, redis-7, opensearch, minio (S3-compatible local), keycloak con realm preconfigurado, mailhog para emails de prueba.
>
> • Servicio backend con hot-reload contra el código local mediante volume mount.
>
> • Servicio frontend-web con hot-reload similar.
>
> • Servicio worker (Celery) que comparte código con backend.
>
> • Networks separadas: default para apps, observability network para Prometheus/Grafana cuando se sumen.
>
> • Volúmenes nombrados para persistir datos entre restarts: pg_data, redis_data, minio_data.
>
> • Variables de entorno provienen de .env raíz; defaults conservadores en docker-compose.yml.
>
> • docker-compose.test.yml con servicios efímeros (sin volúmenes persistentes) para CI.

**Criterios done**

> • docker compose up -d levanta todos los servicios sin errores en menos de tres minutos.
>
> • docker compose ps muestra todos los servicios en estado healthy.
>
> • Postgres accesible en localhost:5432 con extensiones pgcrypto, pg_trgm y postgis presentes.
>
> • Keycloak admin accesible en localhost:8080 con realm deruedas-dev creado.
>
> • MinIO admin accesible en localhost:9001 con bucket deruedas-media creado al startup.

**Tests requeridos**

> • Smoke test: script tools/check-services.sh que pingea cada servicio y reporta OK/FAIL.

**Prompt:** P-libre (basarse en SDD sección 2.2)

**T-003 Pipeline CI base con lint y tests** *\[infra · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 9.1

**Constitución:** Art. 1, 2

**Dependencias:** T-001

**Archivos:** .github/workflows/ci.yml

**Descripción**

Define el pipeline mínimo que se ejecuta en cada pull request. Bloquea el merge si falla.

**Especificación**

> • Job lint-backend: ruff + black --check + mypy. Falla si hay errores.
>
> • Job lint-frontend: eslint + prettier --check + tsc --noEmit.
>
> • Job test-backend-unit: pytest -m 'not integration' con coverage. Mínimo 80% global.
>
> • Job test-backend-integration: docker compose -f docker-compose.test.yml up + pytest -m integration.
>
> • Job test-frontend: vitest run con coverage.
>
> • Job security: pip-audit + npm audit (severidad alta o crítica falla).
>
> • Trigger: pull_request a main + push a main.
>
> • Cache de dependencias: pip cache y npm cache.

**Criterios done**

> • PR de prueba sin cambios pasa el pipeline en menos de quince minutos.
>
> • PR con un test que falla queda bloqueado por el pipeline.
>
> • PR con vulnerabilidad crítica simulada en dependencia queda bloqueado.

**Tests requeridos**

> • No aplica (es infra de tests).

**Prompt:** P-libre

**T-004 Configuración Pydantic Settings con .env** *\[infra · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 8.5 (secretos)

**Constitución:** Art. 3 (secretos), 6

**Dependencias:** T-001, T-002

**Archivos:** backend/app/config.py

**Descripción**

Define la clase Settings que centraliza la lectura de configuración desde variables de entorno con tipos y valores por defecto.

**Especificación**

> • Pydantic Settings v2 con validación de tipos.
>
> • Grupos: DatabaseSettings, RedisSettings, KeycloakSettings, S3Settings, WhatsAppSettings, ObservabilitySettings.
>
> • Carga desde variables de entorno; archivo .env como fallback en dev.
>
> • Singleton get_settings() cacheado con lru_cache.
>
> • Modos: development, staging, production. Settings cambian según APP_ENV.
>
> • Secretos NUNCA se loguean: \_\_repr\_\_ enmascara campos marcados como secret.
>
> • Validación al startup: si falta variable obligatoria, error claro y muerte temprana.

**Criterios done**

> • Settings importable desde cualquier módulo.
>
> • Faltar una variable obligatoria genera error de startup que la nombra.
>
> • settings.dict() no expone los valores de los campos secretos.

**Tests requeridos**

> • unit/test_config.py: validación de defaults, validación de tipos, masking de secretos.

**Prompt:** P-libre

**T-005 Bootstrap FastAPI app principal** *\[infra · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 2.3, 4.1

**Constitución:** Art. 1

**Dependencias:** T-004

**Archivos:** backend/app/main.py; backend/app/\_\_init\_\_.py

**Descripción**

Crea la aplicación FastAPI con configuración base, middleware estándar, registro de routers (vacío inicialmente) y endpoints de salud.

**Especificación**

> • FastAPI con title, version, description.
>
> • OpenAPI generado automáticamente; servido en /docs solo en non-production.
>
> • Middleware: CORS según settings.cors_origins; GZip; trace_id mediante middleware propio.
>
> • Endpoint GET /health → 200 con timestamp y version.
>
> • Endpoint GET /ready → 200 si DB y Redis responden, 503 si no.
>
> • Exception handlers globales para DomainError → 422 Problem Details, HTTPException con formato consistente.
>
> • Lifespan async para inicializar conexiones a Redis y cerrarlas al shutdown.

**Criterios done**

> • uvicorn app.main:app levanta sin errores.
>
> • GET /health responde 200 con payload válido.
>
> • GET /ready responde 503 si paramos Redis y vuelve a 200 al levantarlo.

**Tests requeridos**

> • integration/test_app_health.py: ambos endpoints en condiciones normales y degradadas.

**Prompt:** P-libre

**T-006 Bootstrap Next.js con App Router y Tailwind** *\[infra · S\]*

**Épica:** Fundación

**Spec técnica:** SDD ADR-004

**Constitución:** Art. 1

**Dependencias:** T-001

**Archivos:** frontend-web/package.json; frontend-web/next.config.js; frontend-web/tailwind.config.ts; frontend-web/tsconfig.json; frontend-web/src/app/layout.tsx; frontend-web/src/app/page.tsx

**Descripción**

Inicializa el proyecto Next.js 14+ con TypeScript estricto, Tailwind y configuración base.

**Especificación**

> • Next.js 14+ con App Router.
>
> • TypeScript con strict: true, noImplicitAny: true, noUncheckedIndexedAccess: true.
>
> • Tailwind con la paleta del design system (colores definidos en T-036).
>
> • Path aliases: @/components, @/lib, @/hooks.
>
> • ESLint con next/core-web-vitals + reglas de accesibilidad jsx-a11y.
>
> • Prettier con configuración compartida.
>
> • Layout root con metadatos OG y favicon.
>
> • Página home placeholder que redirige a /login si no hay sesión.

**Criterios done**

> • npm run dev levanta en localhost:3000 sin errores.
>
> • npm run build produce build de producción exitoso.
>
> • tsc --noEmit no reporta errores.

**Tests requeridos**

> • No aplica (sin lógica testeable aún).

**Prompt:** P-libre

**T-007 Setup Alembic con migration inicial vacía** *\[migration · XS\]*

**Épica:** Fundación

**Spec técnica:** SDD ADR-002

**Constitución:** Art. 1

**Dependencias:** T-002, T-005

**Archivos:** backend/alembic.ini; backend/alembic/env.py; backend/alembic/versions/000_baseline.py

**Descripción**

Configura Alembic apuntando a la base de datos de development y crea una migration baseline vacía para fijar el punto cero.

**Especificación**

> • alembic.ini con script_location, file_template (NNN_descripcion.py), timezone.
>
> • env.py que importa la Base declarativa de db/base.py y la configuración desde settings.
>
> • Migration 000_baseline.py vacía (upgrade y downgrade pass).
>
> • Comando make migrate que ejecuta alembic upgrade head.
>
> • Comando make migrate-down-one que ejecuta alembic downgrade -1.

**Criterios done**

> • alembic upgrade head en base limpia ejecuta sin errores.
>
> • alembic downgrade base revierte sin errores.

**Tests requeridos**

> • No aplica.

**Prompt:** P-libre

**T-008 Pipeline de despliegue a staging** *\[infra · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 9.1, 9.2

**Constitución:** Art. 5

**Dependencias:** T-003

**Archivos:** .github/workflows/deploy-staging.yml; infra/terraform/staging/

**Descripción**

Implementa el pipeline que despliega cada merge a main al ambiente de staging automáticamente.

**Especificación**

> • Trigger: push a main después de pasar CI.
>
> • Etapas: build de imágenes Docker firmadas y etiquetadas con SHA del commit; push a registry; despliegue blue-green a staging mediante Terraform o kubectl según infra elegida.
>
> • Smoke tests post-deploy: 5 minutos de verificación con health/ready endpoints y un E2E mínimo.
>
> • Rollback automático si los smoke tests fallan: switch al pool anterior.
>
> • Notificación a Slack o equivalente del equipo.

**Criterios done**

> • Merge a main dispara despliegue automático a staging.
>
> • Staging refleja el cambio en menos de quince minutos.
>
> • Falla simulada en smoke test dispara rollback automático.

**Tests requeridos**

> • No aplica.

**Prompt:** P-libre

**6.1.2 Base de datos y core utilities**

**T-009 Migration de extensiones PostgreSQL** *\[migration · XS\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 2.2, 3.1

**Constitución:** Principio 3, Principio 4

**Dependencias:** T-007

**Archivos:** backend/alembic/versions/001_extensions.py

**Descripción**

Habilita las extensiones PostgreSQL que el resto del proyecto requiere.

**Especificación**

> • CREATE EXTENSION IF NOT EXISTS pgcrypto (cifrado de campos sensibles).
>
> • CREATE EXTENSION IF NOT EXISTS pg_trgm (búsqueda fuzzy).
>
> • CREATE EXTENSION IF NOT EXISTS postgis (datos geográficos para sucursales).
>
> • CREATE EXTENSION IF NOT EXISTS "uuid-ossp" (UUIDs).
>
> • downgrade drops las extensiones en orden inverso.

**Criterios done**

> • alembic upgrade head ejecuta sin errores.
>
> • SELECT extname FROM pg_extension lista las cuatro extensiones.

**Tests requeridos**

> • integration/test_extensions.py: presencia y versión mínima de cada extensión.

**Prompt:** P-01 con table=\_\_none\_\_ (caso especial de migration sin tabla)

**T-010 Helper db/session.py con tenant context** *\[infra · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 2.5, ADR-006

**Constitución:** Principio 4 (multi-tenancy estricto)

**Dependencias:** T-009

**Archivos:** backend/app/db/base.py; backend/app/db/session.py

**Descripción**

Configura SQLAlchemy 2.x con session factory y mecanismo para establecer el tenant_id como variable de sesión PostgreSQL al inicio de cada request.

**Especificación**

> • Engine SQLAlchemy con pool_pre_ping=True, pool_size razonable.
>
> • Session factory con scoped_session.
>
> • Función set_tenant_context(session, tenant_id) que ejecuta SET LOCAL app.current_tenant = '\<uuid\>'.
>
> • Context manager get_db() que abre sesión, setea tenant context si está disponible, y cierra al salir.
>
> • Bloqueo: si se intenta ejecutar query sin tenant_id seteado y la tabla tiene RLS, la propia política de PostgreSQL bloquea (esto se verifica en test).
>
> • Base declarativa con naming convention para constraints (ix\_, uq\_, ck\_, fk\_, pk\_).

**Criterios done**

> • Session factory utilizable como dependency en FastAPI.
>
> • set_tenant_context propaga la variable a la sesión PostgreSQL.
>
> • Hooks de lifecycle: rollback automático en excepción, commit explícito.

**Tests requeridos**

> • integration/test_session.py: setear tenant context, ejecutar query, verificar que el filtro RLS funciona.
>
> • integration/test_session.py: query sin tenant context contra tabla con RLS levanta InsufficientPrivilege.

**Prompt:** P-libre con anchor a ADR-006

**T-011 Migration tabla audit_logs** *\[migration · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 3.9 (Audit), 8.8

**Constitución:** Principio 5, Art. 3

**Dependencias:** T-010

**Archivos:** backend/alembic/versions/002_audit_logs.py; backend/app/modules/audit/models.py

**Descripción**

Crea la tabla de auditoría que será escrita por todo el sistema. Particionada por mes para retención y performance.

**Especificación**

> • Tabla audit_logs particionada por RANGE en occurred_at, partición mensual.
>
> • Campos: id (uuid PK), tenant_id (uuid, NULL admite acciones cross-tenant del super admin), user_id, action, entity_type, entity_id, before_data jsonb, after_data jsonb, ip inet, user_agent text, trace_id, occurred_at timestamptz.
>
> • Sin RLS (super admin debe poder leer cross-tenant); el filtrado es responsabilidad de la aplicación.
>
> • Append-only: revocar UPDATE y DELETE al rol de aplicación.
>
> • Crear partición del mes corriente automáticamente; función para crear las próximas tres particiones por adelantado.
>
> • Índices: (tenant_id, occurred_at), (entity_type, entity_id), (user_id, occurred_at), (trace_id).

**Criterios done**

> • Migration ejecuta y crea la tabla particionada.
>
> • INSERT funciona; UPDATE y DELETE están bloqueados por permisos.
>
> • Una segunda partición se crea automáticamente con la función de mantenimiento.

**Tests requeridos**

> • integration/test_audit_logs_migration.py.

**Prompt:** P-01 con table=audit_logs

**T-012 Core errors.py - DomainError y handlers RFC 7807** *\[infra · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 4.1.7

**Constitución:** Art. 1

**Dependencias:** T-005

**Archivos:** backend/app/core/errors.py

**Descripción**

Define la jerarquía de errores de dominio y los exception handlers de FastAPI que los traducen a Problem Details.

**Especificación**

> • Clase base DomainError(code, message, status_code, field_errors=None).
>
> • Subclases comunes: NotFoundError (404), ValidationError (422), ConflictError (409), AuthorizationError (403).
>
> • Exception handler global que serializa DomainError a Problem Details con campos type, title, status, detail, trace_id, errors\[\].
>
> • Handler para HTTPException que mantiene el formato consistente.
>
> • Handler para Exception genérica que loguea con stack trace y devuelve 500 con trace_id en el cuerpo.
>
> • Type es URI estable: https://docs.deruedas.com/errors/\<code\>.

**Criterios done**

> • Levantar DomainError desde un endpoint produce respuesta 422 con formato Problem Details.
>
> • Errores 500 incluyen trace_id en respuesta y en logs.

**Tests requeridos**

> • integration/test_error_handling.py: cada subclase y el catch-all.

**Prompt:** P-libre

**T-013 Core auth.py - get_current_user dependency** *\[infra · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 4.1.2, 4.1.3, ADR-007

**Constitución:** Art. 3 (auth)

**Dependencias:** T-005, T-012

**Archivos:** backend/app/core/auth.py

**Descripción**

Implementa la dependency de FastAPI que valida el JWT, extrae el AuthContext (user, tenant, roles, permissions) y lo provee a los endpoints.

**Especificación**

> • Dependency get_current_user que toma Authorization header.
>
> • Validación del JWT contra la JWK pública de Keycloak (cacheada con TTL).
>
> • Extracción de claims: sub (user_id), tenant (tenant_id), roles, email.
>
> • Construcción del AuthContext (Pydantic model).
>
> • Errores: token ausente → 401; token expirado → 401 con body que indica refresh; token inválido → 401.
>
> • Establece el tenant context en la sesión PostgreSQL al inicio del request via middleware.

**Criterios done**

> • Endpoint protegido devuelve 401 sin token.
>
> • Endpoint con token válido recibe AuthContext correcto.
>
> • Token expirado devuelve 401 con código 'token_expired' en el body.

**Tests requeridos**

> • integration/test_auth_dependency.py con varios casos.

**Prompt:** P-libre con anchor a ADR-007

**T-014 Core rbac.py - require_role y require_permission** *\[infra · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 8.4

**Constitución:** Art. 3 (autorización en backend siempre)

**Dependencias:** T-013

**Archivos:** backend/app/core/rbac.py

**Descripción**

Implementa las dependencies de autorización por rol y por permiso fino, usables en endpoints.

**Especificación**

> • Dependency factory require_role(\*roles) que devuelve 403 si el rol del usuario no está en la lista.
>
> • Dependency factory require_permission(perm) que verifica permisos finos (definidos por módulo).
>
> • Catálogo de roles canónicos: super_admin, manager, salesperson, admin_staff.
>
> • Decorador @audit_action(action_name) que registra automáticamente en audit_logs cuando se ejecuta exitosamente.

**Criterios done**

> • Endpoint con require_role('manager') devuelve 403 a un salesperson.
>
> • Auditoría se escribe correctamente al ejecutar acción decorada.

**Tests requeridos**

> • unit/test_rbac.py.

**Prompt:** P-libre

**T-015 Core pagination.py + idempotency.py** *\[infra · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 4.1.5, 4.1.8

**Constitución:** Art. 4

**Dependencias:** T-005

**Archivos:** backend/app/core/pagination.py; backend/app/core/idempotency.py

**Descripción**

Implementa los helpers de paginación numerada y por cursor, y el middleware de idempotencia para POSTs.

**Especificación**

> • PaginationParams con page, page_size; defaults 1 y 20; máximo 100.
>
> • CursorParams con cursor (base64 del último id) y limit.
>
> • Helper paginate(query, params) que devuelve PaginatedResult(items, total, page, page_size).
>
> • Headers de respuesta: X-Total-Count, X-Page, X-Page-Size para paginación numerada.
>
> • Idempotency middleware que: detecta header Idempotency-Key (UUID v4); si existe en cache Redis (TTL 24h), devuelve la respuesta cacheada; si no, ejecuta el endpoint y cachea la respuesta vinculada al hash del payload.
>
> • Conflict 409 si misma key con payload distinto.

**Criterios done**

> • Endpoint paginado responde correctamente con headers.
>
> • POST con misma Idempotency-Key + mismo payload devuelve la misma respuesta sin re-ejecutar.
>
> • POST con misma key + payload distinto devuelve 409.

**Tests requeridos**

> • integration/test_pagination.py; integration/test_idempotency.py.

**Prompt:** P-libre

**T-016 Core events.py - publisher y consumer base** *\[infra · L\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 2.4, 4.3, ADR-009

**Constitución:** Art. 1, 6

**Dependencias:** T-005, T-013

**Archivos:** backend/app/core/events.py

**Descripción**

Implementa la infraestructura común de eventos de dominio sobre Redis Streams y la integración con Celery para consumers.

**Especificación**

> • Función publish_event(stream, event_type, data, ctx) que serializa el envelope de la sección 4.3 y lo escribe en Redis Streams.
>
> • Idempotencia del publisher: si el caller pasa event_id explícito y ya existe, no se duplica.
>
> • Decorador @event_handler(event_type) para registrar consumers Celery con dead-letter queue automática.
>
> • Backoff exponencial configurable: max_retries por defecto 5, backoff base 30s, factor 2, max 1h.
>
> • Tabla processed_events para idempotencia del consumer (event_id procesado se ignora en futuros reintentos).
>
> • Métricas: events_published_total, events_consumed_total, event_handler_duration_seconds, events_dead_letter_total.

**Criterios done**

> • Publicar un evento desde un service lo deja en el stream observable con XREAD.
>
> • Consumer registrado con el decorador procesa el evento y marca processed.
>
> • Falla transitoria del consumer dispara reintento con backoff; falla permanente envía a DLQ.

**Tests requeridos**

> • integration/test_events.py con escenarios de happy path, retry, DLQ, idempotencia.

**Prompt:** P-libre con anchor a ADR-009

**6.1.3 Auth y Tenancy**

**T-017 Migration tabla tenants** *\[migration · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 3.3

**Constitución:** Principio 4

**Dependencias:** T-009, T-010

**Archivos:** backend/alembic/versions/003_tenants.py; backend/app/modules/tenancy/models.py (Tenant)

**Descripción**

Crea la tabla tenants. No aplica RLS porque es la tabla raíz que define los tenants.

**Especificación**

> • Todos los campos de la sección 3.3 del SDD: id, name, slug, cuit, billing_email, status, plan_id (FK temporal NULL hasta T-019), trial_ends_at, timezone, locale, settings, timestamps, deleted_at.
>
> • Constraints: UNIQUE(slug), UNIQUE(cuit). CHECK validez del CUIT con dígito verificador (función pgsql).
>
> • Sin RLS en esta tabla (es la raíz).
>
> • Modelo SQLAlchemy correspondiente con relationships pendientes (declaradas como string para evitar circular imports).
>
> • Función pgsql validate_cuit(text) returns boolean.

**Criterios done**

> • Migration up/down funciona; INSERT con CUIT inválido es rechazado por CHECK.

**Tests requeridos**

> • integration/test_tenants_migration.py.

**Prompt:** P-01 con table=tenants

**T-018 Migration tabla branches (sucursales)** *\[migration · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 3.3

**Constitución:** Principio 4

**Dependencias:** T-017

**Archivos:** backend/alembic/versions/004_branches.py; backend/app/modules/tenancy/models.py (Branch)

**Descripción**

Crea la tabla branches con FK a tenants y RLS.

**Especificación**

> • Campos según SDD: id, tenant_id (FK NOT NULL), name, address, city, province, phone, business_hours jsonb, geo_point geography(Point,4326), is_active, timestamps.
>
> • Habilitar RLS con política tenant_isolation.
>
> • Índices: (tenant_id, is_active); GiST sobre geo_point para queries geográficas.

**Criterios done**

> • Migration funciona; insertar branch sin tenant context es rechazado por RLS.

**Tests requeridos**

> • integration/test_branches_migration.py incluyendo verificación de RLS.

**Prompt:** P-01 con table=branches

**T-019 Migration tablas plans y subscriptions** *\[migration · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 3.3

**Constitución:** —

**Dependencias:** T-017

**Archivos:** backend/alembic/versions/005_plans_subscriptions.py; backend/app/modules/tenancy/models.py (Plan, Subscription)

**Descripción**

Crea las tablas plans (catálogo cross-tenant) y subscriptions (vinculación tenant-plan vigente).

**Especificación**

> • plans según SDD sección 3.3: id, code (UNIQUE), name, price_ars, max_users, max_vehicles, max_branches, modules jsonb, is_active, timestamps. Sin RLS.
>
> • subscriptions según SDD: id, tenant_id, plan_id, status, start_date, end_date, mp_subscription_id, amount_ars, timestamps. RLS activo.
>
> • FK tenants.plan_id → plans.id (resuelve la FK pendiente de T-017).
>
> • Seed inicial de tres planes: starter, pro, enterprise con valores ficticios pero realistas.

**Criterios done**

> • Migration aplica; los tres planes seed están presentes.

**Tests requeridos**

> • integration/test_plans_migration.py.

**Prompt:** P-01 con table=plans + subscriptions (compuesto)

**T-020 Tenancy module: schemas, repository, service** *\[service · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 3.3

**Constitución:** Principio 4

**Dependencias:** T-017, T-018, T-019

**Archivos:** backend/app/modules/tenancy/{schemas,repository,service}.py

**Descripción**

Implementa el módulo tenancy con CRUD básico y la lógica de gestión de sucursales.

**Especificación**

> • TenantSchemas: TenantCreate, TenantUpdate, TenantRead, TenantListItem.
>
> • BranchSchemas con validación de coordenadas (lat/lng en rangos válidos).
>
> • TenantRepository y BranchRepository (CRUD + filtros + soft delete).
>
> • TenantService.create (sólo para super admin; valida unicidad de slug y cuit).
>
> • BranchService.create (valida que el tenant no exceda max_branches del plan).
>
> • BranchService.deactivate (en vez de delete).

**Criterios done**

> • Crear tenant; crear branch; intentar crear branch que excede el plan devuelve 422.

**Tests requeridos**

> • unit/test_tenancy_service.py + integration/test_tenancy_endpoints (en T-021).

**Prompt:** P-03 + P-04 (repository + service)

**T-021 Endpoints tenancy: branches y configuración del tenant** *\[endpoint · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 4.2

**Constitución:** Art. 3

**Dependencias:** T-020, T-013, T-014

**Archivos:** backend/app/modules/tenancy/routes.py

**Descripción**

Expone los endpoints REST para que un tenant gestione sus sucursales y configuración. Los endpoints de creación de tenant viven en /admin (T-235 en olas posteriores; placeholder no incluido en MVP).

**Especificación**

> • GET /api/v1/tenant/me — info del tenant del user autenticado.
>
> • PATCH /api/v1/tenant/me — actualizar settings del tenant (rol manager).
>
> • GET /api/v1/branches — listado de sucursales del tenant.
>
> • GET /api/v1/branches/{id} — detalle.
>
> • POST /api/v1/branches — alta (rol manager).
>
> • PATCH /api/v1/branches/{id} — edición.
>
> • POST /api/v1/branches/{id}/deactivate — desactivación.

**Criterios done**

> • Todos los endpoints responden según contrato; tests pasan.

**Tests requeridos**

> • integration/test_tenancy_routes.py.

**Prompt:** P-05 para cada endpoint

**T-022 Migration tabla users + user_branches** *\[migration · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 3.3

**Constitución:** Principio 4, Art. 3

**Dependencias:** T-018

**Archivos:** backend/alembic/versions/006_users.py; backend/app/modules/users/models.py

**Descripción**

Crea las tablas users y user_branches con RLS y constraints.

**Especificación**

> • users según SDD sección 3.3: id, tenant_id, email, password_hash, full_name, phone, role enum, status enum, last_login_at, mfa_enabled, mfa_secret (encrypted), timestamps, deleted_at.
>
> • Enums user_role_enum y user_status_enum.
>
> • UNIQUE (tenant_id, lower(email)) WHERE deleted_at IS NULL.
>
> • user_branches: PK compuesta (user_id, branch_id), is_primary, created_at.
>
> • RLS en ambas tablas.

**Criterios done**

> • Migration aplica; UNIQUE case-insensitive de email funciona.

**Tests requeridos**

> • integration/test_users_migration.py.

**Prompt:** P-01 con table=users + user_branches

**T-023 Users module: schemas, repository, service** *\[service · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 3.3, 8.3

**Constitución:** Art. 3 (auth), Principio 4

**Dependencias:** T-022

**Archivos:** backend/app/modules/users/{schemas,repository,service}.py

**Descripción**

Implementa la lógica de gestión de usuarios y la asociación con sucursales.

**Especificación**

> • UserCreate, UserUpdate, UserRead, UserInvite (subset para invitaciones).
>
> • UserService.create (sólo invitación; password se genera al aceptar).
>
> • UserService.invite (crea con status=invited y dispara email).
>
> • UserService.accept_invitation(token) — valida token, setea password, status=active.
>
> • UserService.assign_to_branches(user_id, branch_ids).
>
> • Password hashing con argon2id.
>
> • Validación: tenant no excede max_users del plan al crear.

**Criterios done**

> • Invitar usuario crea fila con status=invited.
>
> • Aceptar invitación con token válido cambia status a active.
>
> • Aceptar con token inválido o expirado devuelve 422.

**Tests requeridos**

> • unit/test_users_service.py.

**Prompt:** P-03 + P-04

**T-024 Endpoints users** *\[endpoint · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 4.2

**Constitución:** Art. 3

**Dependencias:** T-023, T-014

**Archivos:** backend/app/modules/users/routes.py

**Descripción**

Endpoints REST para gestión de usuarios dentro del tenant.

**Especificación**

> • GET /api/v1/users — listado.
>
> • GET /api/v1/users/{id} — detalle.
>
> • POST /api/v1/users/invite — invitar (rol manager).
>
> • PATCH /api/v1/users/{id} — editar (manager o el propio user para datos no privilegiados).
>
> • POST /api/v1/users/{id}/deactivate.
>
> • POST /api/v1/users/{id}/branches — asignar a sucursales.
>
> • POST /api/v1/users/accept-invitation (público con token).

**Criterios done**

> • Todos los endpoints; tests pasan.

**Tests requeridos**

> • integration/test_users_routes.py.

**Prompt:** P-05

**T-025 Auth endpoints: login, refresh, logout, me** *\[endpoint · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 4.2.1

**Constitución:** Art. 3

**Dependencias:** T-013

**Archivos:** backend/app/modules/auth/routes.py

**Descripción**

Endpoints de autenticación que delegan a Keycloak la emisión de tokens.

**Especificación**

> • POST /api/v1/auth/login (body: email, password) → llama a Keycloak token endpoint, devuelve access_token + refresh_token.
>
> • POST /api/v1/auth/refresh (body: refresh_token) → renueva tokens.
>
> • POST /api/v1/auth/logout (body: refresh_token) → invalida refresh en Keycloak.
>
> • GET /api/v1/auth/me → info del user autenticado.
>
> • POST /api/v1/auth/forgot-password — envía email con link.
>
> • POST /api/v1/auth/reset-password — completa cambio de password.

**Criterios done**

> • Login con credenciales válidas devuelve tokens; con inválidas devuelve 401.

**Tests requeridos**

> • integration/test_auth_endpoints.py.

**Prompt:** P-libre con anchor a ADR-007

**T-026 Configuración Keycloak realm + sincronización** *\[infra · L\]*

**Épica:** Fundación

**Spec técnica:** SDD ADR-007

**Constitución:** Art. 3

**Dependencias:** T-002, T-022

**Archivos:** infra/keycloak/realm-export.json; backend/app/core/keycloak_sync.py

**Descripción**

Configura el realm de Keycloak con clients, roles, mappers, y mantiene sincronización entre la tabla users del backend y los users de Keycloak.

**Especificación**

> • Realm deruedas con clients: backend (confidential), frontend-web (public + PKCE), frontend-mobile (public + PKCE), frontend-admin.
>
> • Realm roles: super_admin, manager, salesperson, admin_staff.
>
> • Custom JWT mapper que incluye tenant_id como claim.
>
> • Sincronización: al crear/actualizar/desactivar user en backend, se replica a Keycloak vía Admin API.
>
> • Idempotencia de la sincronización (eventos en cola con retry).

**Criterios done**

> • Login con un user creado en backend funciona en Keycloak.
>
> • Desactivar user en backend lo bloquea en Keycloak.
>
> • JWT recibido tiene claim tenant_id correcto.

**Tests requeridos**

> • integration/test_keycloak_sync.py.

**Prompt:** P-libre con anchor a ADR-007

**T-027 Tests críticos de aislamiento multi-tenant** *\[test-integration · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 8.2, ADR-006

**Constitución:** Principio 4 (no negociable)

**Dependencias:** T-022, T-023, T-024

**Archivos:** backend/tests/integration/test_tenant_isolation.py

**Descripción**

Suite específica que verifica que un tenant no puede ver, modificar ni inferir datos de otro tenant. Es el test más crítico de la Ola 0.

**Especificación**

> • Setup: dos tenants (A y B) cada uno con sucursales, usuarios y un branch propio.
>
> • Test: user de A no puede leer branches de B (lista solo devuelve los de A).
>
> • Test: user de A no puede actualizar branch de B (404, no 403, para no filtrar existencia).
>
> • Test: user de A no puede asignarse a branch de B.
>
> • Test: query SQL directa sin tenant context contra tabla con RLS falla con InsufficientPrivilege.
>
> • Test: query con tenant context de A sobre tabla con RLS no devuelve filas de B aún si se intentara explícitamente.
>
> • Test: validación de que toda tabla que el SDD declara con RLS efectivamente tiene la política activa (introspección de pg_policies).

**Criterios done**

> • Toda la suite pasa en CI; agregar una nueva tabla con RLS no rompe el test introspectivo.

**Tests requeridos**

> • —

**Prompt:** P-11 con level=integration

**6.1.4 Observabilidad y testing base**

**T-028 Logging estructurado con trace_id** *\[infra · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 9.5, 9.6

**Constitución:** Art. 1

**Dependencias:** T-005

**Archivos:** backend/app/core/observability.py (logging part)

**Descripción**

Configura logging estructurado JSON con propagación de trace_id a través de todo el request.

**Especificación**

> • structlog configurado para emitir JSON.
>
> • Middleware que genera trace_id (UUID v4) si no viene en header X-Trace-Id; lo propaga al ContextVar; lo agrega al response header.
>
> • Cada log automáticamente incluye: trace_id, tenant_id (si auth context disponible), user_id, request_id, route, method.
>
> • Niveles: DEBUG, INFO, WARNING, ERROR. INFO es default en producción.
>
> • Excepciones se loguean con stack trace estructurado.
>
> • Loki-friendly: campos plano, sin nesting profundo.

**Criterios done**

> • Hacer un request loguea entradas con trace_id consistente; los logs son JSON válido.

**Tests requeridos**

> • unit/test_logging.py: estructura del log; integration con request real.

**Prompt:** P-libre

**T-029 Métricas Prometheus middleware** *\[infra · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 9.5, 9.6

**Constitución:** Art. 4

**Dependencias:** T-005

**Archivos:** backend/app/core/observability.py (metrics part); infra/observability/prometheus.yml

**Descripción**

Expone métricas Prometheus de la aplicación y configura el scraper.

**Especificación**

> • Endpoint /metrics que expone formato Prometheus.
>
> • Middleware que mide cada request: http_requests_total{method, route, status}, http_request_duration_seconds (histogram con buckets razonables).
>
> • Métricas de DB: db_connections_active, db_query_duration_seconds.
>
> • Métricas custom para events: ya implementadas en T-016.
>
> • prometheus.yml con scrape config del backend cada quince segundos.
>
> • Reglas de alerta básicas en prometheus/rules.yml (latencia p95 alta, error rate alto).

**Criterios done**

> • GET /metrics devuelve formato Prometheus válido; Prometheus en docker-compose lo scrapea.

**Tests requeridos**

> • integration/test_metrics.py.

**Prompt:** P-libre

**T-030 Tracing distribuido con OpenTelemetry** *\[infra · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 9.5

**Constitución:** —

**Dependencias:** T-028

**Archivos:** backend/app/core/observability.py (tracing part); docker-compose.yml (jaeger service)

**Descripción**

Instrumenta el backend con OpenTelemetry para trazas distribuidas exportadas a Jaeger.

**Especificación**

> • Instrumentación automática de FastAPI, SQLAlchemy, Redis, requests/httpx.
>
> • Spans manuales en services con atributos relevantes (entity_id, action).
>
> • Propagación de contexto a través de eventos (trace_id viaja en el envelope).
>
> • Sampler: 100% en dev y staging; 10% probabilístico en prod.
>
> • Servicio jaeger en docker-compose accesible en localhost:16686.

**Criterios done**

> • Hacer un request genera traza visible en Jaeger UI con spans de DB, Redis y service calls.

**Tests requeridos**

> • No aplica (verificación visual + smoke).

**Prompt:** P-libre

**T-031 Sentry para error tracking** *\[infra · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 9.5

**Constitución:** Art. 6

**Dependencias:** T-028

**Archivos:** backend/app/core/observability.py (sentry init); frontend-web/src/sentry.client.config.ts

**Descripción**

Integra Sentry para captura de excepciones no manejadas en backend y frontend.

**Especificación**

> • SDK Sentry inicializado con DSN desde settings (None = deshabilitado).
>
> • Filtro de PII: enmascarar email, dni, password en payloads de Sentry.
>
> • Asociación con trace_id propio para correlación.
>
> • Tags automáticos: release (SHA del commit), environment.
>
> • Backend: integración con FastAPI. Frontend: integración con Next.js.

**Criterios done**

> • Excepción no manejada llega a Sentry con trace_id y contexto correcto.

**Tests requeridos**

> • No aplica (smoke con excepción artificial).

**Prompt:** P-libre

**T-032 tests/conftest.py con fixtures comunes** *\[test-integration · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 7

**Constitución:** Art. 2

**Dependencias:** T-010

**Archivos:** backend/tests/conftest.py; backend/tests/factories/\_\_init\_\_.py

**Descripción**

Define las fixtures pytest compartidas por toda la suite: app, db, auth contexts, factories.

**Especificación**

> • Fixture session que provee SQLAlchemy session con savepoint y rollback automático al final del test.
>
> • Fixture client que provee TestClient FastAPI con la session inyectada.
>
> • Fixture postgres_container que levanta contenedor efímero para integration tests (testcontainers).
>
> • Fixture redis_container similar.
>
> • Fixture tenant_factory, user_factory, branch_factory que generan datos válidos.
>
> • Fixture authed_client_manager, authed_client_salesperson que devuelven TestClient con JWT pre-armado.
>
> • Markers personalizados: integration, e2e, slow.

**Criterios done**

> • Tests pueden usar las fixtures; cada test corre aislado con rollback al final.

**Tests requeridos**

> • —

**Prompt:** P-libre

**T-033 Factories (factory_boy) para entidades base** *\[test-integration · S\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 7.3

**Constitución:** Art. 2

**Dependencias:** T-032

**Archivos:** backend/tests/factories/{tenant,user,branch,plan}.py

**Descripción**

Crea factories que generan instancias válidas con datos aleatorios pero realistas para todas las entidades de la Ola 0.

**Especificación**

> • TenantFactory con CUIT válido generado, slug único, plan starter por defecto.
>
> • BranchFactory ligada al tenant del scope.
>
> • UserFactory con role manager por defecto, email único.
>
> • PlanFactory para los tres planes canónicos (StarterPlan, ProPlan, EnterprisePlan).
>
> • Faker con localization es_AR para nombres, ciudades, teléfonos.
>
> • Sub-factories: TenantWithBranchesAndUsers para escenarios completos.

**Criterios done**

> • Las factories generan instancias persistibles; los datos pasan validaciones del dominio.

**Tests requeridos**

> • unit/factories/test_factories.py: cada factory produce entidad válida.

**Prompt:** P-libre

**T-034 Storage adapter S3-compatible** *\[infra · M\]*

**Épica:** Fundación

**Spec técnica:** SDD ADR-008

**Constitución:** Art. 3, 6

**Dependencias:** T-002, T-004

**Archivos:** backend/app/core/storage.py

**Descripción**

Implementa la abstracción StorageAdapter sobre boto3 (compatible con S3, MinIO, GCS).

**Especificación**

> • Interface StorageAdapter con upload(key, data, content_type), download(key), delete(key), get_signed_url(key, ttl_seconds).
>
> • Implementación S3StorageAdapter usando boto3.
>
> • Validación: tamaños máximos (10MB foto, 50MB documento), content-type whitelist.
>
> • URLs firmadas: 5 minutos para fotos, 30 minutos para documentos.
>
> • Compresión y resize automático para imágenes (genera variantes thumbnail, medium, original).
>
> • Storage en MinIO local en dev, en S3/GCS en prod (selección por settings).

**Criterios done**

> • Subir un archivo en dev lo deja accesible en MinIO.
>
> • URL firmada caduca a los 5 minutos.
>
> • Imagen subida tiene variantes thumb y medium creadas.

**Tests requeridos**

> • integration/test_storage.py con MinIO container.

**Prompt:** P-libre con anchor a ADR-008

**T-035 Notifications module - in-app + email base** *\[service · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 3.9 (Notifications)

**Constitución:** Art. 6

**Dependencias:** T-022, T-016

**Archivos:** backend/alembic/versions/007_notifications.py; backend/app/modules/notifications/{models,schemas,repository,service,routes}.py

**Descripción**

Implementa el módulo de notificaciones que el resto del sistema usa para avisar a usuarios.

**Especificación**

> • Migration tabla notifications: id, tenant_id, user_id, type (string code), payload jsonb, read_at, created_at. RLS activo.
>
> • NotificationService.create(user_id, type, payload).
>
> • NotificationService.mark_read.
>
> • NotificationRepository con filtros por user, leído/no leído, paginación.
>
> • Endpoints: GET /api/v1/notifications, POST /api/v1/notifications/{id}/read, POST /api/v1/notifications/mark-all-read.
>
> • Email backend: SMTP configurable; templates Jinja2 en backend/app/templates/email/.
>
> • Función send_email(to, subject, template, context) con cola asíncrona.
>
> • Templates iniciales: invitation.html, password_reset.html.

**Criterios done**

> • Service crea notificación; endpoint la lista; marcar como leída funciona.
>
> • Email de invitación se envía a MailHog en dev.

**Tests requeridos**

> • unit/test_notifications_service.py.

**Prompt:** P-03 + P-04 + P-05

**6.1.5 Design system base y bootstrap del frontend**

**T-036 Design tokens y configuración de Tailwind** *\[frontend-component · S\]*

**Épica:** Fundación

**Spec técnica:** SDD ADR-004

**Constitución:** Principio 2 (simplicidad), Art. 1

**Dependencias:** T-006

**Archivos:** frontend-web/tailwind.config.ts; frontend-web/src/styles/tokens.css

**Descripción**

Define los tokens visuales del producto (paleta, tipografía, espaciados, radii, sombras) y los configura en Tailwind.

**Especificación**

> • Paleta primaria: azul corporativo (50-900), neutros (gray 50-900), feedback (success, warning, danger, info).
>
> • Tipografía: Inter como fuente principal, escala tipográfica documentada (xs a 4xl).
>
> • Spacing scale: múltiplos de 4px estándar.
>
> • Radii: sm (4px), md (8px), lg (12px), full (rounded).
>
> • Shadows: sm, md, lg con valores específicos.
>
> • Modo oscuro NO incluido en MVP (postergado).
>
> • Tokens documentados en docs/design-system.md como referencia para nuevos componentes.

**Criterios done**

> • Tokens disponibles vía clases Tailwind; ejemplo visual en una storybook story.

**Tests requeridos**

> • No aplica (visual).

**Prompt:** P-libre

**T-037 Componentes UI primitivos del design system** *\[frontend-component · L\]*

**Épica:** Fundación

**Spec técnica:** SDD ADR-004

**Constitución:** Principio 2, Art. 1

**Dependencias:** T-036

**Archivos:** frontend-web/src/components/ui/\*.tsx (Button, Input, Select, Modal, Card, Badge, Toast, Spinner, Skeleton, Avatar, Dropdown, Tabs, Tooltip)

**Descripción**

Crea los componentes primitivos reutilizables del design system, basados en Radix UI para accesibilidad.

**Especificación**

> • Trece componentes: Button (variants primary/secondary/ghost/danger; sizes sm/md/lg), Input (text/email/password/number con label, helper, error), Select (con búsqueda), Modal (Dialog Radix), Card, Badge, Toast (Sonner), Spinner, Skeleton, Avatar, Dropdown (Radix), Tabs (Radix), Tooltip (Radix).
>
> • Cada uno con TypeScript estricto, props tipadas, sin dependencias externas al design system.
>
> • Story de Storybook por componente con todas las variantes.
>
> • Tests de accesibilidad con jest-axe.

**Criterios done**

> • Trece componentes con stories; CI pasa lint, axe y tests.

**Tests requeridos**

> • unit/components/ui/\* con cobertura de variants y a11y.

**Prompt:** P-08 por componente

**T-038 Layout principal de la aplicación** *\[frontend-component · M\]*

**Épica:** Fundación

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-037

**Archivos:** frontend-web/src/components/layout/{AppShell,Sidebar,Topbar,UserMenu,TenantSwitcher}.tsx

**Descripción**

Construye el shell de la aplicación: sidebar con navegación, topbar con menú de user, breadcrumbs, contenedor principal.

**Especificación**

> • AppShell con tres regiones: sidebar (colapsable en mobile), topbar, content.
>
> • Sidebar con secciones por módulo (Stock, CRM, Comunicaciones, etc.); items con icono lucide-react.
>
> • Active route resaltado.
>
> • Topbar: breadcrumbs, search bar global (placeholder), notification bell, user menu.
>
> • UserMenu con avatar, nombre, link a perfil, link a settings, logout.
>
> • Mobile: sidebar como drawer; navegación bottom bar opcional.
>
> • Tenant switcher solo visible para super_admin (oculto en MVP para usuarios regulares).

**Criterios done**

> • Layout responsivo; navegación funciona; toggle mobile/desktop.

**Tests requeridos**

> • unit/components/layout.

**Prompt:** P-08 por subcomponente

**T-039 Cliente API tipado con TanStack Query** *\[infra · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 4.1

**Constitución:** Art. 1

**Dependencias:** T-006, T-040

**Archivos:** frontend-web/src/lib/api.ts; frontend-web/src/lib/queryClient.ts

**Descripción**

Implementa el cliente HTTP tipado y la integración con TanStack Query para cache, refetch y optimistic updates.

**Especificación**

> • Wrapper sobre fetch con interceptors: agregar Authorization header automáticamente, refresh token en 401.
>
> • Tipos generados automáticamente desde openapi.yaml con openapi-typescript.
>
> • Hooks: useQueryX, useMutationX para cada recurso (helpers reutilizables).
>
> • Manejo de errores: traducir Problem Details a errores de TanStack.
>
> • QueryClient con defaults razonables (staleTime, retry policy).
>
> • Optimistic updates para mutations cuando aplica.

**Criterios done**

> • Hacer un fetch a un endpoint protegido funciona automáticamente con auth.
>
> • Token expirado dispara refresh automático.
>
> • Tipos generados se actualizan al cambiar OpenAPI.

**Tests requeridos**

> • unit/lib/api.test.ts.

**Prompt:** P-libre

**T-040 Setup de auth en frontend con NextAuth** *\[infra · M\]*

**Épica:** Fundación

**Spec técnica:** SDD ADR-007

**Constitución:** Art. 3

**Dependencias:** T-026, T-006

**Archivos:** frontend-web/src/lib/auth.ts; frontend-web/src/app/api/auth/\[...nextauth\]/route.ts

**Descripción**

Integra NextAuth con Keycloak como provider OIDC, manejando session, refresh y middleware de protección de rutas.

**Especificación**

> • NextAuth con Keycloak provider; PKCE habilitado.
>
> • Session storage: encrypted JWT cookies.
>
> • Refresh token rotation: refresh automático antes de expirar.
>
> • Middleware de Next.js que protege rutas /dashboard/\*\* redirigiendo a /login si no hay sesión.
>
> • Hook useAuth() que devuelve user, isAuthenticated, hasRole.
>
> • Logout limpia session y redirige a Keycloak logout endpoint.

**Criterios done**

> • Login con credenciales válidas establece sesión y redirige a /dashboard.
>
> • Acceso a ruta protegida sin sesión redirige a /login.
>
> • Logout limpia todo y redirige.

**Tests requeridos**

> • e2e/auth.spec.ts: login, logout, protección de rutas.

**Prompt:** P-libre con anchor a ADR-007

**T-041 Página de login y recuperación de password** *\[frontend-page · M\]*

**Épica:** Fundación

**Spec técnica:** SDD sección 4.2.1

**Constitución:** Art. 3, Principio 2

**Dependencias:** T-040, T-037

**Archivos:** frontend-web/src/app/(public)/login/page.tsx; frontend-web/src/app/(public)/forgot-password/page.tsx; frontend-web/src/app/(public)/reset-password/page.tsx

**Descripción**

Crea las páginas públicas de autenticación con buenos defaults de UX y manejo de errores claros.

**Especificación**

> • Login con email + password, opción “recordarme”, link a recuperación.
>
> • Errores de credenciales: mensaje genérico (no diferenciar email no existe vs password inválida) por seguridad.
>
> • Forgot password: input de email, mensaje genérico de confirmación independiente de si existe.
>
> • Reset password: input de password con validación de fuerza, repetición.
>
> • Diseño limpio centrado, logo, color del producto.
>
> • Form errors con feedback inmediato.

**Criterios done**

> • Flujo completo login → dashboard funciona; flujo de recuperación funciona end-to-end con email mock.

**Tests requeridos**

> • e2e/auth.spec.ts (cubierto en T-040 + nuevos casos).

**Prompt:** P-09 (login) + P-09 (forgot) + P-09 (reset)

**T-042 Dashboard placeholder y rutas protegidas** *\[frontend-page · S\]*

**Épica:** Fundación

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-040, T-038

**Archivos:** frontend-web/src/app/(authed)/dashboard/page.tsx; frontend-web/src/app/(authed)/layout.tsx

**Descripción**

Crea el grupo de rutas autenticadas con su layout y un dashboard placeholder que muestra el estado básico del tenant.

**Especificación**

> • Layout del grupo (authed) que envuelve con AppShell.
>
> • Dashboard placeholder con saludo, info del tenant y plan, links rápidos a las secciones principales.
>
> • Skeleton mientras carga.
>
> • Manejo de error: si la sesión es inválida, redirect a /login.

**Criterios done**

> • Login redirige a dashboard; dashboard muestra info del user logueado.

**Tests requeridos**

> • e2e/dashboard.spec.ts: smoke test.

**Prompt:** P-10 (página simple)

**6.2 Ola 1 — MVP funcional**

Esta ola completa el producto mínimo viable: las épicas E1 a E5 del backlog, con los recortes declarados en la sección 3.2. Una vez completa, deRuedas Gestión es lanzable a un programa cerrado de agencias early adopter.

**6.2.1 E1 — Onboarding y configuración del tenant**

**T-043 Endpoint admin: crear tenant** *\[endpoint · M\]*

**Épica:** E1

**Historias:** E1.1

**Spec técnica:** SDD sección 4.2.11

**Constitución:** Art. 3 (super_admin only)

**Dependencias:** T-020, T-026

**Archivos:** backend/app/modules/admin/routes.py (POST /admin/api/v1/tenants)

**Descripción**

Endpoint privilegiado para que el super admin de deRuedas cree un nuevo tenant durante el onboarding asistido.

**Especificación**

> • POST /admin/api/v1/tenants con payload TenantCreate + initial_user_email + initial_user_full_name + plan_code.
>
> • Crea: el tenant, una sucursal por defecto (“Casa Central”), un usuario manager invitado, una suscripción al plan indicado, los pipeline_stages por defecto.
>
> • Operación atómica: si falla cualquier paso, rollback completo.
>
> • Envía email de invitación al manager.
>
> • Audit log con detalle de la creación.

**Criterios done**

> • Crear tenant deja el sistema con todo lo necesario para que el manager acepte invitación y arranque.

**Tests requeridos**

> • integration/test_admin_create_tenant.py: happy path, atomicidad ante falla.

**Prompt:** P-05 + P-04 (creación atómica multi-entidad)

**T-044 Endpoint admin: cambiar plan de tenant** *\[endpoint · S\]*

**Épica:** E1

**Historias:** E1.6

**Spec técnica:** SDD sección 4.2.11

**Constitución:** Art. 3

**Dependencias:** T-043

**Archivos:** backend/app/modules/admin/routes.py (PATCH plan)

**Descripción**

Permite al super admin cambiar el plan de un tenant (upgrade o downgrade).

**Especificación**

> • PATCH /admin/api/v1/tenants/{id}/plan body: {plan_code}.
>
> • Valida: si el downgrade dejaría al tenant excediendo límites del plan nuevo (más usuarios o vehículos), retorna 422 con detalle.
>
> • Crea nueva subscription, marca la anterior como cancelled.
>
> • Audit log obligatorio.
>
> • Evento tenant.plan_changed publicado.

**Criterios done**

> • Upgrade funciona instantáneo; downgrade que excede falla con mensaje claro.

**Tests requeridos**

> • integration/test_change_plan.py.

**Prompt:** P-05 + P-04

**T-045 Endpoint admin: suspender y reactivar tenant** *\[endpoint · S\]*

**Épica:** E1

**Historias:** E1.7

**Spec técnica:** SDD sección 4.2.11

**Constitución:** Art. 3

**Dependencias:** T-043

**Archivos:** backend/app/modules/admin/routes.py

**Descripción**

Permite suspender un tenant (impago, fraude) y reactivarlo. Suspendido bloquea acceso de todos sus usuarios.

**Especificación**

> • POST /admin/api/v1/tenants/{id}/suspend body: {reason}.
>
> • POST /admin/api/v1/tenants/{id}/reactivate.
>
> • Suspendido: status=suspended; al login los users reciben 403 con código account_suspended.
>
> • Audit log obligatorio.

**Criterios done**

> • Suspender bloquea login; reactivar restablece.

**Tests requeridos**

> • integration/test_suspend_reactivate.py.

**Prompt:** P-05

**T-046 Service: completar onboarding del tenant** *\[service · S\]*

**Épica:** E1

**Historias:** E1.2

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-020

**Archivos:** backend/app/modules/tenancy/service.py (TenantService.complete_setup)

**Descripción**

Marca el tenant como onboarding completo cuando el manager terminó el wizard inicial.

**Especificación**

> • Método TenantService.complete_setup(tenant_id, ctx).
>
> • Flag onboarding_completed_at en settings del tenant.
>
> • Validación: ya hay al menos una sucursal, al menos un user activo, al menos una etapa de pipeline.
>
> • Si validación falla, devuelve DomainError con código onboarding_incomplete y lista de qué falta.

**Criterios done**

> • Marcar onboarding completo solo funciona con prerequisitos cumplidos.

**Tests requeridos**

> • unit/test_complete_onboarding.py.

**Prompt:** P-04

**T-047 Endpoint: completar onboarding desde frontend** *\[endpoint · XS\]*

**Épica:** E1

**Historias:** E1.2

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-046

**Archivos:** backend/app/modules/tenancy/routes.py

**Descripción**

Expone el endpoint que el wizard de onboarding llama al finalizar.

**Especificación**

> • POST /api/v1/tenant/me/complete-onboarding.
>
> • Solo accesible por manager.
>
> • Valida y dispara TenantService.complete_setup.

**Criterios done**

> • Endpoint funciona; tests pasan.

**Tests requeridos**

> • integration/test_complete_onboarding_endpoint.py.

**Prompt:** P-05

**T-048 Frontend: layout del wizard de onboarding** *\[frontend-component · M\]*

**Épica:** E1

**Historias:** E1.2

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-038, T-039

**Archivos:** frontend-web/src/components/onboarding/{OnboardingWizard,OnboardingStep,OnboardingProgress}.tsx

**Descripción**

Componentes reutilizables que estructuran el wizard multi-paso del onboarding.

**Especificación**

> • OnboardingWizard: contenedor con step actual, navegación, progress bar.
>
> • OnboardingStep: contenedor de cada paso con título, descripción, contenido, botones siguiente/atrás/saltar.
>
> • Persistencia del estado en localStorage para retomar si el usuario sale.
>
> • Skip permitido en pasos opcionales.
>
> • Confetti al completar (sutil).

**Criterios done**

> • Wizard navega entre pasos; estado se persiste.

**Tests requeridos**

> • unit/components/onboarding.

**Prompt:** P-08

**T-049 Frontend: paso 1 del wizard - datos de la agencia** *\[frontend-page · S\]*

**Épica:** E1

**Historias:** E1.2

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-048

**Archivos:** frontend-web/src/app/(authed)/onboarding/page.tsx (paso 1: datos del tenant)

**Descripción**

Formulario para que el manager complete los datos básicos de la agencia: razón social, CUIT (preview), zona horaria, logo opcional.

**Especificación**

> • Formulario con: nombre, CUIT (readonly, viene de la creación), email de contacto, teléfono, dirección, sitio web (opcional), upload de logo.
>
> • Validación: email formato; teléfono argentino.
>
> • Submit: PATCH /api/v1/tenant/me con los cambios.
>
> • Al guardar, avanza al paso 2.

**Criterios done**

> • Paso 1 completable; datos se guardan y refrescan en el contexto.

**Tests requeridos**

> • e2e: cubierto en T-061.

**Prompt:** P-09

**T-050 Frontend: paso 2 - alta de sucursales** *\[frontend-page · M\]*

**Épica:** E1

**Historias:** E1.3

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-021, T-048

**Archivos:** frontend-web/src/app/(authed)/onboarding/branches.tsx (paso 2)

**Descripción**

Permite al manager agregar las sucursales que tiene la agencia. Mínimo una.

**Especificación**

> • Lista de sucursales agregadas; botón agregar nueva.
>
> • Form modal por sucursal con: nombre, dirección, ciudad, provincia, teléfono, horarios de atención.
>
> • Geocoding automático al guardar (si dirección+ciudad+provincia válidos).
>
> • Edición y eliminación inline.
>
> • Validación: al menos una sucursal antes de avanzar.
>
> • Si el plan limita branches y se intenta exceder, mensaje claro.

**Criterios done**

> • Paso 2 permite agregar/editar/eliminar sucursales.

**Tests requeridos**

> • e2e: cubierto en T-061.

**Prompt:** P-09 + P-08

**T-051 Frontend: paso 3 - invitar usuarios** *\[frontend-page · M\]*

**Épica:** E1

**Historias:** E1.4

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-024, T-048

**Archivos:** frontend-web/src/app/(authed)/onboarding/users.tsx (paso 3)

**Descripción**

Permite al manager invitar a su equipo durante el wizard. Es opcional (puede saltarse).

**Especificación**

> • Lista de usuarios invitados con su estado (pending, accepted).
>
> • Form para agregar invitación: email, nombre, rol (manager/salesperson/admin_staff), sucursales asignadas (multi-select).
>
> • Bulk add: textarea con emails uno por línea, asigna rol salesperson por defecto.
>
> • Validación de emails únicos dentro del tenant.
>
> • Posibilidad de saltar este paso (“invitaré después”).

**Criterios done**

> • Paso 3 funcional con invitaciones individuales y bulk.

**Tests requeridos**

> • e2e: cubierto en T-061.

**Prompt:** P-09 + P-08

**T-052 Frontend: paso 4 - configuración inicial del pipeline** *\[frontend-page · S\]*

**Épica:** E1

**Historias:** E1.5

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-048

**Archivos:** frontend-web/src/app/(authed)/onboarding/pipeline.tsx (paso 4)

**Descripción**

Muestra al manager el pipeline default y le permite hacer ajustes mínimos antes de finalizar el wizard.

**Especificación**

> • Visualización del pipeline default (5 etapas).
>
> • Permite renombrar etapas inline.
>
> • Permite agregar una etapa adicional (no más, para mantener simplicidad inicial).
>
> • Botón “usar pipeline default” para skip.
>
> • Al guardar, llama al endpoint correspondiente del módulo CRM (pendiente de E4) o lo skipea si E4 no está implementado todavía.

**Criterios done**

> • Paso 4 funcional; permite seguir aún si E4 no está mergeado.

**Tests requeridos**

> • e2e: cubierto en T-061.

**Prompt:** P-09

**T-053 Frontend: paso 5 - finalización y completar onboarding** *\[frontend-page · S\]*

**Épica:** E1

**Historias:** E1.2

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-047, T-048

**Archivos:** frontend-web/src/app/(authed)/onboarding/complete.tsx (paso 5)

**Descripción**

Pantalla final del wizard que dispara la marca de onboarding completo y lleva al dashboard.

**Especificación**

> • Resumen de lo configurado.
>
> • Mensaje de bienvenida con próximos pasos sugeridos (cargar primer vehículo, importar stock).
>
> • Botón “ir al dashboard” que llama POST /tenant/me/complete-onboarding y redirige.

**Criterios done**

> • Onboarding queda marcado como completo; dashboard se ve.

**Tests requeridos**

> • e2e: cubierto en T-061.

**Prompt:** P-10

**T-054 Frontend: página pública de aceptación de invitación** *\[frontend-page · M\]*

**Épica:** E1

**Historias:** E1.4

**Spec técnica:** —

**Constitución:** Art. 3

**Dependencias:** T-024

**Archivos:** frontend-web/src/app/(public)/accept-invitation/page.tsx

**Descripción**

Página a la que llega el usuario invitado desde el email para completar su cuenta.

**Especificación**

> • Lee token del query param.
>
> • Muestra info del tenant y rol al que fue invitado (consulta endpoint público).
>
> • Form: nombre completo (prefilled), password (con validación), repetir password, opción de habilitar MFA.
>
> • Token expirado o inválido: mensaje claro y opción de pedir reinvitación al manager.
>
> • Submit: POST /auth/accept-invitation; al éxito, login automático y redirect a /dashboard.

**Criterios done**

> • Flujo completo invitación → email → click → form → login funciona end-to-end.

**Tests requeridos**

> • e2e/accept_invitation.spec.ts.

**Prompt:** P-09 + P-10

**T-055 Frontend: página de configuración de la agencia** *\[frontend-page · M\]*

**Épica:** E1

**Historias:** E1.2

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-021, T-038

**Archivos:** frontend-web/src/app/(authed)/settings/agency/page.tsx

**Descripción**

Página de settings donde el manager edita los datos de la agencia post-onboarding.

**Especificación**

> • Form con los mismos campos del paso 1 del wizard.
>
> • Sección separada para cambio de logo.
>
> • Botón guardar habilitado solo si hay cambios.
>
> • Mostrar plan vigente y fecha de renovación (sin permitir cambio; eso es endpoint admin).

**Criterios done**

> • Edición funcional con validación y feedback visual.

**Tests requeridos**

> • e2e/settings_agency.spec.ts.

**Prompt:** P-09

**T-056 Frontend: página de gestión de sucursales** *\[frontend-page · M\]*

**Épica:** E1

**Historias:** E1.3

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-021, T-038

**Archivos:** frontend-web/src/app/(authed)/settings/branches/page.tsx

**Descripción**

Listado de sucursales con CRUD post-onboarding.

**Especificación**

> • Tabla con columnas: nombre, ciudad, teléfono, estado (activa/inactiva), acciones.
>
> • Botón “nueva sucursal” abre modal con form.
>
> • Acciones por fila: editar (modal), desactivar (confirm dialog).
>
> • Mapa pequeño con todas las sucursales activas usando geo_point.

**Criterios done**

> • CRUD completo funcional.

**Tests requeridos**

> • e2e/settings_branches.spec.ts.

**Prompt:** P-10 + P-09 (form modal)

**T-057 Frontend: página de gestión de usuarios** *\[frontend-page · M\]*

**Épica:** E1

**Historias:** E1.4

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-024, T-038

**Archivos:** frontend-web/src/app/(authed)/settings/users/page.tsx

**Descripción**

Listado de usuarios del tenant con CRUD y gestión de invitaciones.

**Especificación**

> • Tabla con columnas: nombre, email, rol, sucursales asignadas, estado, último login, acciones.
>
> • Filtro por estado y por rol.
>
> • Botón “invitar usuario”.
>
> • Acciones por fila: editar (rol y sucursales), desactivar, reenviar invitación si está pending.
>
> • Indicador de cuántos usuarios consume del plan (3/10).

**Criterios done**

> • Lista, invita, edita, desactiva.

**Tests requeridos**

> • e2e/settings_users.spec.ts.

**Prompt:** P-10 + P-09

**T-058 Frontend: badge "complete su onboarding" si está incompleto** *\[frontend-component · S\]*

**Épica:** E1

**Historias:** E1.2

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-038

**Archivos:** frontend-web/src/components/onboarding/OnboardingBanner.tsx

**Descripción**

Banner persistente que aparece en el dashboard mientras el onboarding no esté completo, con link al wizard.

**Especificación**

> • Banner amarillo con icono y texto “Termine de configurar su agencia”.
>
> • Link al wizard.
>
> • Solo visible si onboarding_completed_at IS NULL en el contexto del tenant.
>
> • Dismissible solo de manera temporal (vuelve a aparecer en próximo login).

**Criterios done**

> • Banner aparece y desaparece correctamente.

**Tests requeridos**

> • unit/components/OnboardingBanner.test.tsx.

**Prompt:** P-08

**T-059 Service: detección de límites del plan en hot path** *\[service · S\]*

**Épica:** E1

**Historias:** E1.6

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-019

**Archivos:** backend/app/modules/tenancy/service.py (PlanLimitsService)

**Descripción**

Helper que se invoca antes de operaciones potencialmente bloqueantes por plan (crear user, crear branch, crear vehículo).

**Especificación**

> • Métodos: assert_can_add_user, assert_can_add_branch, assert_can_add_vehicle.
>
> • Cada uno consulta el plan vigente y el conteo actual; si excede, levanta DomainError con código plan_limit_exceeded y detalle del límite y el plan superior sugerido.
>
> • Cacheable con TTL corto (60s) para no consultar plan en cada operación.

**Criterios done**

> • Llamadas funcionan; tests verifican happy path y límites.

**Tests requeridos**

> • unit/test_plan_limits.py.

**Prompt:** P-04

**T-060 Notificación: bienvenida al completar onboarding** *\[service · XS\]*

**Épica:** E1

**Historias:** E1.2

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-035, T-046

**Archivos:** backend/app/modules/tenancy/service.py (extend complete_setup)

**Descripción**

Al completar onboarding, generar notificación in-app y email de bienvenida con tips iniciales.

**Especificación**

> • Hook en TenantService.complete_setup que crea Notification para el manager.
>
> • Email con template welcome.html que incluye links a docs y video tutorial (URLs placeholder).

**Criterios done**

> • Completar onboarding genera ambas notificaciones.

**Tests requeridos**

> • integration/test_welcome_notification.py.

**Prompt:** P-04

**T-061 E2E test: flujo completo de onboarding** *\[test-e2e · M\]*

**Épica:** E1

**Historias:** E1.1, E1.2, E1.3, E1.4, E1.5

**Spec técnica:** —

**Constitución:** Art. 2

**Dependencias:** T-053, T-054, T-057

**Archivos:** frontend-web/tests/e2e/onboarding.spec.ts

**Descripción**

Test E2E que ejecuta el flujo desde la creación del tenant por el super admin hasta el dashboard del manager con onboarding completo.

**Especificación**

> • Setup: super admin crea tenant + invita manager via API.
>
> • Manager recibe email (mailhog), click en link.
>
> • Acepta invitación, setea password.
>
> • Wizard 5 pasos completados con datos válidos.
>
> • Llega al dashboard con onboarding marcado completo.
>
> • Banner de “complete onboarding” NO aparece.

**Criterios done**

> • Test pasa de extremo a extremo en CI.

**Tests requeridos**

> • —

**Prompt:** P-12

**T-062 Backoffice admin: página de tenants** *\[frontend-page · L\]*

**Épica:** E1

**Historias:** E1.1, E1.6, E1.7

**Spec técnica:** SDD sección 4.2.11

**Constitución:** Art. 3

**Dependencias:** T-043, T-044, T-045

**Archivos:** frontend-admin/src/app/tenants/\* (página y subrutas)

**Descripción**

Backoffice deRuedas con la pantalla de gestión de tenants para Customer Success y Super Admin.

**Especificación**

> • Listado de tenants con filtros (status, plan, fecha de alta).
>
> • Detalle por tenant: info, plan, métricas (users, vehículos, last activity), acciones.
>
> • Acciones: crear nuevo, cambiar plan, suspender, reactivar, ver historial.
>
> • Modal de creación: form completo + plan + email del manager.
>
> • Login del backoffice usa el mismo Keycloak pero con rol super_admin obligatorio.

**Criterios done**

> • Customer Success puede crear tenants nuevos sin abrir tickets a ingeniería.

**Tests requeridos**

> • e2e/admin_tenants.spec.ts.

**Prompt:** P-10 + P-09

**6.2.2 E2 — Stock de vehículos**

Es la épica más grande del MVP por ser el dominio central del producto. Cubre catálogos canónicos de marcas/modelos/versiones, alta y edición de vehículos, fotos, transiciones de estado, importación masiva, búsqueda y todo el frontend asociado.

**Catálogos canónicos (marcas, modelos, versiones)**

**T-063 Migration vehicle_brands (catálogo cross-tenant)** *\[migration · S\]*

**Épica:** E2

**Historias:** E2.1

**Spec técnica:** SDD sección 3.4

**Constitución:** Principio 3 (datos como activo)

**Dependencias:** T-009

**Archivos:** alembic/versions/010_vehicle_brands.py; modules/stock/models.py (VehicleBrand)

**Descripción**

Tabla vehicle_brands compartida entre tenants. Sin RLS porque el catálogo es canónico. Solo super_admin puede modificarla.

**Especificación**

> • Campos: id, name (UNIQUE case-insensitive), slug (UNIQUE), country_origin (ISO), logo_url, is_active, created_at, updated_at.
>
> • Sin tenant_id ni RLS: catálogo cross-tenant.
>
> • Índices: lower(name) para búsqueda, slug.

**Criterios done**

> • Migration aplica; INSERT duplicado case-insensitive es rechazado.

**Tests requeridos**

> • integration/test_brands_migration.py.

**Prompt:** P-01 con table=vehicle_brands

**T-064 Migration vehicle_models con FK a brands** *\[migration · S\]*

**Épica:** E2

**Historias:** E2.1

**Spec técnica:** SDD sección 3.4

**Constitución:** Principio 3

**Dependencias:** T-063

**Archivos:** alembic/versions/011_vehicle_models.py; modules/stock/models.py (VehicleModel)

**Descripción**

Tabla vehicle_models con FK a brands. También cross-tenant.

**Especificación**

> • Campos: id, brand_id (FK NOT NULL), name, slug, body_type (enum), generation, year_from, year_to (nullable), is_active, timestamps.
>
> • UNIQUE (brand_id, lower(name)).
>
> • Índice (brand_id, is_active).

**Criterios done**

> • Migration aplica; UNIQUE por brand respeta case-insensitive.

**Tests requeridos**

> • integration/test_models_migration.py.

**Prompt:** P-01 con table=vehicle_models

**T-065 Migration vehicle_versions y trims** *\[migration · XS\]*

**Épica:** E2

**Historias:** E2.1

**Spec técnica:** SDD sección 3.4

**Constitución:** Principio 3

**Dependencias:** T-064

**Archivos:** alembic/versions/012_vehicle_versions.py; modules/stock/models.py (VehicleVersion)

**Descripción**

Tabla vehicle_versions con FK a models. Representa los “trims” o versiones específicas (ej. “XEi 2.0 AT”).

**Especificación**

> • Campos: id, model_id (FK), name, fuel_type (enum), transmission (enum), engine_displacement_cc, hp, doors, is_active, timestamps.
>
> • UNIQUE (model_id, lower(name)).

**Criterios done**

> • Migration aplica.

**Tests requeridos**

> • integration/test_versions_migration.py.

**Prompt:** P-01 con table=vehicle_versions

**T-066 Seed inicial de catálogo (brands + top models AR)** *\[infra · M\]*

**Épica:** E2

**Historias:** E2.1

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-063, T-064, T-065

**Archivos:** tools/seed_catalog.py; backend/data/catalog/brands.csv; models.csv; versions.csv

**Descripción**

Script de seed que carga el catálogo inicial con las marcas relevantes para el mercado argentino y los modelos top vendedores.

**Especificación**

> • CSVs versionados en repo con datos curados (40 marcas mínimas, 300 modelos top, 800 versiones top).
>
> • Script idempotente: ejecutar dos veces no duplica.
>
> • Comando make seed-catalog disponible.
>
> • Datos basados en publicaciones públicas de ACARA/ADEFA (sin copiar verbatim, solo datos factual).

**Criterios done**

> • Ejecutar seed deja la base con 40 marcas, 300 modelos, 800 versiones.

**Tests requeridos**

> • integration/test_seed_idempotency.py.

**Prompt:** P-libre

**T-067 Repository y service de catálogos** *\[service · S\]*

**Épica:** E2

**Historias:** E2.1

**Spec técnica:** SDD sección 3.4

**Constitución:** —

**Dependencias:** T-066

**Archivos:** modules/stock/{repository,service}.py (sección catálogo)

**Descripción**

Capa de acceso a datos y servicio para los catálogos. Solo lectura para tenants regulares; escritura para super_admin.

**Especificación**

> • BrandRepository, ModelRepository, VersionRepository con list (filtros active, search por nombre), get.
>
> • Búsqueda fuzzy con pg_trgm para autocompletes.
>
> • Cache Redis con TTL 1 hora porque cambia poco.

**Criterios done**

> • list_models(brand_id) devuelve modelos activos del brand; búsqueda fuzzy funciona.

**Tests requeridos**

> • unit/test_catalog_service.py.

**Prompt:** P-03

**T-068 Endpoints públicos de catálogos** *\[endpoint · S\]*

**Épica:** E2

**Historias:** E2.1

**Spec técnica:** SDD sección 4.2.2

**Constitución:** Art. 3

**Dependencias:** T-067

**Archivos:** modules/stock/routes.py (/api/v1/catalog/\*)

**Descripción**

Endpoints REST de solo lectura para que el frontend popule selects en cascada.

**Especificación**

> • GET /api/v1/catalog/brands?q=&active=true.
>
> • GET /api/v1/catalog/brands/{id}/models?q=.
>
> • GET /api/v1/catalog/models/{id}/versions.
>
> • Auth requerida pero accesible para todos los roles.
>
> • Cache HTTP con ETag (datos cambian poco).

**Criterios done**

> • Endpoints responden con paginación y filtros.

**Tests requeridos**

> • integration/test_catalog_endpoints.py.

**Prompt:** P-05

**T-069 Backoffice admin: gestión del catálogo** *\[frontend-page · M\]*

**Épica:** E2

**Historias:** E2.1

**Spec técnica:** —

**Constitución:** Art. 3

**Dependencias:** T-068

**Archivos:** frontend-admin/src/app/catalog/\* (brands, models, versions)

**Descripción**

Páginas en el backoffice deRuedas para que el equipo de catalog mantenga marcas, modelos y versiones.

**Especificación**

> • Tres listados con CRUD (solo super_admin).
>
> • Importación masiva CSV en cada uno.
>
> • Marcado active/inactive sin borrado físico.
>
> • Audit log de cambios.

**Criterios done**

> • Equipo de catálogo puede agregar un modelo nuevo sin tocar SQL.

**Tests requeridos**

> • e2e/admin_catalog.spec.ts.

**Prompt:** P-10 + P-09

**T-070 Frontend: selector cascada brand→model→version** *\[frontend-component · M\]*

**Épica:** E2

**Historias:** E2.1, E2.3

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-068, T-037

**Archivos:** frontend-web/src/components/domain/VehicleSelector.tsx

**Descripción**

Componente reutilizable que se usa en todas las pantallas que requieren elegir un vehículo del catálogo.

**Especificación**

> • Tres Combobox (Radix Combobox sobre Select del design system) en cascada.
>
> • Búsqueda con debounce 200ms.
>
> • Al elegir brand, model se habilita; al elegir model, version se habilita.
>
> • Permite no elegir version (algunos vehículos no tienen version detallada).
>
> • Devuelve {brand_id, model_id, version_id, year} via onChange.
>
> • Soporta valores iniciales (modo edición).

**Criterios done**

> • Componente funciona aislado en Storybook; integrable en formularios.

**Tests requeridos**

> • unit/components/VehicleSelector.test.tsx.

**Prompt:** P-08

**Vehicles - core de stock**

**T-071 Migration vehicles + enums asociados** *\[migration · M\]*

**Épica:** E2

**Historias:** E2.3, E2.4, E2.5, E2.7

**Spec técnica:** SDD sección 3.4, ADR-002, ADR-006

**Constitución:** Art. 1, 4, Principio 3, 4

**Dependencias:** T-018, T-022, T-064, T-065

**Archivos:** alembic/versions/013_vehicles.py; modules/stock/models.py (Vehicle)

**Descripción**

Tabla central del módulo Stock. Es la entidad sobre la que pivota el resto del producto.

**Especificación**

> • Enums: fuel_type_enum (gasoline, diesel, hybrid, electric, gnc, flex), transmission_enum, body_type_enum, vehicle_status_enum (available, reserved, sold, in_workshop, in_preparation, archived).
>
> • Campos según SDD 3.4: id, tenant_id, branch_id, assigned_user_id (nullable), brand_id, model_id, version_id (nullable), year, mileage_km, color, domain_plate (nullable), chassis_number, engine_number, fuel_type, transmission, body_type, doors, price_ars, status, condition (new/used/demo), description, internal_notes, source (string), source_id (string nullable), entry_date, exit_date (nullable), timestamps, deleted_at.
>
> • FKs con ON DELETE apropiado: branch RESTRICT, brand RESTRICT, assigned_user SET NULL.
>
> • CHECKs: year between 1950 and extract(year from now())+1, mileage_km \>= 0, price_ars \> 0.
>
> • UNIQUE (tenant_id, domain_plate) WHERE deleted_at IS NULL.
>
> • UNIQUE (tenant_id, chassis_number) WHERE deleted_at IS NULL.
>
> • Índices: (tenant_id, status), (tenant_id, brand_id, model_id, year), GIN trgm sobre description.
>
> • RLS activo con tenant_isolation policy.

**Criterios done**

> • Migration aplica; constraints se respetan; RLS bloquea cross-tenant.

**Tests requeridos**

> • integration/test_vehicles_migration.py: estructura, constraints, RLS, soft-delete vs UNIQUE.

**Prompt:** P-01 con table=vehicles

**T-072 VehicleRepository CRUD básico** *\[repository · M\]*

**Épica:** E2

**Historias:** E2.2, E2.3, E2.4

**Spec técnica:** SDD sección 3.4, 4.2.2

**Constitución:** Principio 4

**Dependencias:** T-071

**Archivos:** modules/stock/repository.py (VehicleRepository)

**Descripción**

Capa de acceso a datos sobre vehicles con todas las operaciones CRUD y filtros.

**Especificación**

> • Métodos: get, list, create, update, soft_delete, exists, count_by_status.
>
> • list acepta filtros: status, branch_id, brand_id, model_id, year_min/max, price_min/max, mileage_max, fuel_type, transmission, body_type, condition, search (full-text), assigned_user_id.
>
> • list paginado con cursor (last_id).
>
> • Sort por: created_at, price_ars, year, mileage_km (asc/desc).
>
> • Eager loading de brand, model, version, branch para evitar N+1.
>
> • Tenant isolation via session context (no manual).

**Criterios done**

> • Operaciones funcionan con filtros combinados; performance aceptable con 10k vehículos.

**Tests requeridos**

> • integration/test_vehicle_repository.py.

**Prompt:** P-03 con entity=Vehicle, filters=...

**T-073 Schemas Pydantic de Vehicle** *\[schema · S\]*

**Épica:** E2

**Historias:** E2.3, E2.4, E2.2

**Spec técnica:** SDD sección 4.1.4

**Constitución:** Art. 1

**Dependencias:** T-071

**Archivos:** modules/stock/schemas.py

**Descripción**

Schemas para todas las variantes de Vehicle.

**Especificación**

> • VehicleCreate, VehicleUpdate, VehicleRead, VehicleListItem (subset compacto).
>
> • VehicleStatusTransition: {to_status, reason (opcional), notes (opcional)}.
>
> • VehicleFilters para query params del listado.
>
> • Validators: dominio AR formato (T-089 implementa el validator), chassis 17 chars alfanumérico, year en rango.
>
> • Read incluye nested BrandRead, ModelRead, VersionRead opcional, BranchRead, photos\[\].
>
> • ListItem es liviano: solo id, brand_name, model_name, year, price, status, primary_photo_url.

**Criterios done**

> • Schemas validan correctamente; ListItem es ~5x más liviano que Read.

**Tests requeridos**

> • unit/test_vehicle_schemas.py.

**Prompt:** P-02 con entity=Vehicle, variants=Create,Update,Read,ListItem,StatusTransition

**T-074 VehicleService.create + evento vehicle.created** *\[service · M\]*

**Épica:** E2

**Historias:** E2.3

**Spec técnica:** SDD sección 3.4, 2.4

**Constitución:** Art. 4, Principio 6

**Dependencias:** T-072, T-073, T-016

**Archivos:** modules/stock/service.py (VehicleService.create); modules/stock/events.py (VehicleCreatedEvent)

**Descripción**

Implementa la lógica de alta de vehículo con validaciones de dominio y publicación de evento.

**Especificación**

> • Validaciones: branch del tenant, assigned_user del tenant, brand-model-version coherentes, dominio único en tenant (incluyendo soft-deleted: si existe archivado, mensaje específico).
>
> • Si no se especifica status, default es 'in_preparation'.
>
> • Llamada a PlanLimitsService.assert_can_add_vehicle.
>
> • Publicación de evento vehicle.created al stream stock-events.
>
> • Logging estructurado.

**Criterios done**

> • Crear vehículo válido funciona; las cinco validaciones rechazan correctamente.

**Tests requeridos**

> • unit/test_vehicle_service.py: create happy path + cinco casos de error.

**Prompt:** P-04 + P-06 (publica evento)

**T-075 VehicleService.update + evento vehicle.updated** *\[service · M\]*

**Épica:** E2

**Historias:** E2.4

**Spec técnica:** SDD sección 3.4

**Constitución:** Principio 6

**Dependencias:** T-074

**Archivos:** modules/stock/service.py (extend)

**Descripción**

Update parcial del vehículo respetando reglas de transición de campos.

**Especificación**

> • PATCH semantics: solo cambia campos enviados.
>
> • Restricciones: status no se cambia por update (eso es transition_status); chassis_number no se cambia post-creación; tenant_id nunca cambia.
>
> • Si cambia branch_id, validar pertenencia al tenant.
>
> • Cálculo de diff antes/después para audit.
>
> • Publicación de evento vehicle.updated con before/after en payload.

**Criterios done**

> • Update parcial funciona; intentar cambiar campo restringido devuelve 422.

**Tests requeridos**

> • unit/test_vehicle_service.py: update casos válidos y bloqueados.

**Prompt:** P-04

**T-076 VehicleService.transition_status con máquina de estados** *\[service · M\]*

**Épica:** E2

**Historias:** E2.5

**Spec técnica:** SDD sección 3.4

**Constitución:** Principio 1, 6

**Dependencias:** T-074

**Archivos:** modules/stock/service.py (extend); modules/stock/state_machine.py

**Descripción**

Implementa la máquina de transiciones de estado de vehicles con reglas de negocio.

**Especificación**

> • Transiciones permitidas declarativas: in_preparation→available, available→reserved, reserved→sold, reserved→available, available→in_workshop, in_workshop→available, sold→archived, available→archived, archived→available.
>
> • Transición 'sold' requiere razón obligatoria.
>
> • Transición a 'archived' setea exit_date si aún no está.
>
> • Cualquier transición publica vehicle.status_changed con from/to/reason.
>
> • Transición no permitida → DomainError con código invalid_transition y lista de transiciones válidas desde el estado actual.

**Criterios done**

> • Transiciones válidas funcionan; inválidas devuelven 422 con orientación.

**Tests requeridos**

> • unit/test_state_machine.py: matriz completa de transiciones.

**Prompt:** P-04 con publishes_events=\[vehicle.status_changed\]

**T-077 VehicleService.soft_delete (archivar) + evento** *\[service · S\]*

**Épica:** E2

**Historias:** E2.5

**Spec técnica:** SDD sección 3.4

**Constitución:** Principio 3 (datos como activo, no borrado físico)

**Dependencias:** T-074

**Archivos:** modules/stock/service.py (extend)

**Descripción**

Archivado del vehículo (soft delete). Es la única forma de “borrar”.

**Especificación**

> • Setea deleted_at, status='archived'.
>
> • Razón obligatoria.
>
> • Publica vehicle.archived.
>
> • Si el vehículo tiene leads activos, retorna 422 con cantidad de leads (a resolver primero).

**Criterios done**

> • Archivar funciona; con leads activos da error claro.

**Tests requeridos**

> • unit/test_archive_vehicle.py.

**Prompt:** P-04

**T-078 Endpoint POST /api/v1/vehicles** *\[endpoint · S\]*

**Épica:** E2

**Historias:** E2.3

**Spec técnica:** SDD sección 4.2.2

**Constitución:** Art. 3, 4

**Dependencias:** T-074, T-014, T-015

**Archivos:** modules/stock/routes.py (POST)

**Descripción**

Endpoint REST de alta de vehículo.

**Especificación**

> • Roles: manager, admin_staff.
>
> • Soporta Idempotency-Key.
>
> • Mapea DomainError a Problem Details.
>
> • 201 + header Location.

**Criterios done**

> • Crear funciona end-to-end; tests de auth/autz pasan.

**Tests requeridos**

> • integration/test_vehicles_post.py.

**Prompt:** P-05 con method=POST, idempotent=true

**T-079 Endpoint PATCH /api/v1/vehicles/{id}** *\[endpoint · S\]*

**Épica:** E2

**Historias:** E2.4

**Spec técnica:** SDD sección 4.2.2

**Constitución:** Art. 3

**Dependencias:** T-075

**Archivos:** modules/stock/routes.py (PATCH)

**Descripción**

Endpoint de update parcial.

**Especificación**

> • Roles: manager, admin_staff. Salesperson solo puede cambiar internal_notes y assigned_user_id (a sí mismo).
>
> • Validación de permisos finos en service.
>
> • 200 con VehicleRead actualizado.

**Criterios done**

> • Edición funciona con permisos diferenciados.

**Tests requeridos**

> • integration/test_vehicles_patch.py.

**Prompt:** P-05 con method=PATCH

**T-080 Endpoint GET /api/v1/vehicles (listado con filtros)** *\[endpoint · M\]*

**Épica:** E2

**Historias:** E2.2, E2.8

**Spec técnica:** SDD sección 4.2.2, 4.1.5

**Constitución:** Art. 4 (performance)

**Dependencias:** T-072

**Archivos:** modules/stock/routes.py (GET list)

**Descripción**

Listado paginado con filtros y ordenamiento.

**Especificación**

> • Query params según VehicleFilters schema.
>
> • Paginación por cursor (recomendado para listas grandes) y por página.
>
> • Devuelve VehicleListItem\[\] (no VehicleRead) para perf.
>
> • p95 \< 200ms con 10k vehículos en el tenant.
>
> • ETag para cacheo HTTP en cliente.

**Criterios done**

> • Lista responde rápido; filtros combinados funcionan.

**Tests requeridos**

> • integration/test_vehicles_list.py + perf test simple.

**Prompt:** P-05 con method=GET

**T-081 Endpoint GET /api/v1/vehicles/{id}** *\[endpoint · S\]*

**Épica:** E2

**Historias:** E2.4

**Spec técnica:** SDD sección 4.2.2

**Constitución:** Art. 3

**Dependencias:** T-072

**Archivos:** modules/stock/routes.py (GET detail)

**Descripción**

Detalle completo del vehículo con relaciones.

**Especificación**

> • VehicleRead completo con brand/model/version/branch/photos\[\]/status_history\[\].
>
> • 404 si no existe (404 también si pertenece a otro tenant; no diferenciar por seguridad).

**Criterios done**

> • Detalle devuelve todo el contexto necesario para la UI.

**Tests requeridos**

> • integration/test_vehicles_get.py.

**Prompt:** P-05

**T-082 Endpoint POST /api/v1/vehicles/{id}/status** *\[endpoint · S\]*

**Épica:** E2

**Historias:** E2.5

**Spec técnica:** SDD sección 4.2.2

**Constitución:** Art. 3

**Dependencias:** T-076

**Archivos:** modules/stock/routes.py

**Descripción**

Endpoint dedicado a transiciones de estado (no se hace por PATCH para forzar el flow correcto).

**Especificación**

> • Body: {to_status, reason, notes}.
>
> • Roles: manager. Salesperson puede solo transiciones limitadas (available→reserved si está asignado).
>
> • Errores con orientación (qué transiciones son válidas desde el estado actual).

**Criterios done**

> • Cambio de estado funcional con permisos.

**Tests requeridos**

> • integration/test_vehicles_status.py.

**Prompt:** P-05

**T-083 Endpoint DELETE /api/v1/vehicles/{id} (archivar)** *\[endpoint · XS\]*

**Épica:** E2

**Historias:** E2.5

**Spec técnica:** SDD sección 4.2.2

**Constitución:** Art. 3, Principio 3

**Dependencias:** T-077

**Archivos:** modules/stock/routes.py

**Descripción**

Endpoint que dispara soft delete. Body opcional con razón.

**Especificación**

> • DELETE no es destructivo: dispara archivado.
>
> • Body opcional: {reason}.
>
> • Roles: manager.

**Criterios done**

> • Archivar funciona; recurso pasa a estado archived.

**Tests requeridos**

> • integration/test_vehicles_delete.py.

**Prompt:** P-05

**T-084 Migration vehicle_status_history (auditoría de cambios)** *\[migration · S\]*

**Épica:** E2

**Historias:** E2.5, E2.9

**Spec técnica:** SDD sección 3.4

**Constitución:** Principio 3, 5

**Dependencias:** T-071

**Archivos:** alembic/versions/014_vehicle_status_history.py

**Descripción**

Tabla append-only que registra toda transición de estado. Permite reconstruir línea de tiempo del vehículo.

**Especificación**

> • Campos: id, tenant_id, vehicle_id (FK), from_status, to_status, reason, notes, changed_by_user_id, changed_at.
>
> • RLS activo.
>
> • Índice (vehicle_id, changed_at desc).
>
> • Append-only: revoke UPDATE/DELETE.

**Criterios done**

> • Migration aplica; cada transición de estado escribe una fila (vía VehicleService).

**Tests requeridos**

> • integration/test_status_history.py.

**Prompt:** P-01 con table=vehicle_status_history

**T-085 Endpoint GET /api/v1/vehicles/{id}/history** *\[endpoint · XS\]*

**Épica:** E2

**Historias:** E2.9

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-084

**Archivos:** modules/stock/routes.py

**Descripción**

Devuelve el historial completo de cambios de estado del vehículo.

**Especificación**

> • Lista ordenada cronológicamente.
>
> • Incluye user_id que hizo el cambio (con nombre denormalizado para la UI).

**Criterios done**

> • Endpoint funcional.

**Tests requeridos**

> • integration/test_vehicle_history.py.

**Prompt:** P-05

**T-086 Validador de dominio argentino y chassis number** *\[infra · S\]*

**Épica:** E2

**Historias:** E2.3, E2.4

**Spec técnica:** —

**Constitución:** Art. 1

**Dependencias:** T-073

**Archivos:** core/validators.py (vehicle validators)

**Descripción**

Funciones de validación específicas del dominio AR.

**Especificación**

> • validate_argentine_plate(s): acepta formato viejo (XXX 999) y nuevo Mercosur (XX 999 XX); retorna versión normalizada.
>
> • validate_chassis_number(s): 17 caracteres alfanuméricos sin I, O, Q.
>
> • validate_engine_number(s): formato libre pero alfanumérico.
>
> • Reutilizable en schemas y servicios.

**Criterios done**

> • Validadores prueban variantes de input.

**Tests requeridos**

> • unit/test_validators.py.

**Prompt:** P-libre

**T-087 Tests integración endpoints de stock core** *\[test-integration · M\]*

**Épica:** E2

**Historias:** E2.2, E2.3, E2.4, E2.5

**Spec técnica:** —

**Constitución:** Art. 2

**Dependencias:** T-078, T-079, T-080, T-081, T-082, T-083

**Archivos:** tests/integration/test_stock_endpoints.py

**Descripción**

Suite ampliada que verifica el comportamiento end-to-end de los endpoints de vehicles.

**Especificación**

> • Casos: alta + edición + transición + archivado.
>
> • Cross-tenant isolation: vehículo de A no es visible para B.
>
> • Idempotencia.
>
> • Permisos por rol.
>
> • Performance smoke: lista con 1000 vehículos en menos de 500ms.

**Criterios done**

> • Suite completa pasa en CI.

**Tests requeridos**

> • —

**Prompt:** P-11 con level=integration

**T-088 Migration vehicle_photos** *\[migration · S\]*

**Épica:** E2

**Historias:** E2.6

**Spec técnica:** SDD sección 3.4

**Constitución:** Art. 3

**Dependencias:** T-071

**Archivos:** alembic/versions/015_vehicle_photos.py

**Descripción**

Tabla de fotos asociadas a vehículos.

**Especificación**

> • Campos: id, tenant_id, vehicle_id, position (int), original_url, thumb_url, medium_url, alt_text, mime_type, size_bytes, uploaded_by_user_id, uploaded_at.
>
> • UNIQUE (vehicle_id, position) WHERE deleted_at IS NULL.
>
> • RLS activo.
>
> • ON DELETE CASCADE desde vehicles (raro porque vehicles no se borra fisico, pero pp aplica si se hace cleanup admin).

**Criterios done**

> • Migration aplica.

**Tests requeridos**

> • integration/test_photos_migration.py.

**Prompt:** P-01 con table=vehicle_photos

**T-089 PhotoService.upload con resize automático** *\[service · L\]*

**Épica:** E2

**Historias:** E2.6

**Spec técnica:** SDD sección 3.4, ADR-008

**Constitución:** Art. 3, 6

**Dependencias:** T-088, T-034

**Archivos:** modules/stock/photo_service.py

**Descripción**

Servicio que orquesta la subida de fotos: validación, generación de variantes, persistencia.

**Especificación**

> • Validación: mime image/jpeg\|png\|webp; tamaño máximo 10MB; dimensiones mínimas 800x600.
>
> • Genera variantes: thumb 200x150, medium 800x600, original (preservado pero con compresión a 85% si es JPEG).
>
> • Stripe EXIF GPS para privacidad.
>
> • Asignación de position automática (siguiente al máximo existente).
>
> • Update de Vehicle.primary_photo_url denormalizado al primer upload.
>
> • Publicación de evento vehicle.photo_uploaded.

**Criterios done**

> • Upload genera tres variantes y devuelve URLs firmadas.

**Tests requeridos**

> • integration/test_photo_upload.py.

**Prompt:** P-04 con anchor a ADR-008

**T-090 PhotoService.delete y reorder** *\[service · S\]*

**Épica:** E2

**Historias:** E2.6

**Spec técnica:** SDD sección 3.4

**Constitución:** —

**Dependencias:** T-089

**Archivos:** modules/stock/photo_service.py (extend)

**Descripción**

Operaciones de mantenimiento de fotos.

**Especificación**

> • delete: marca deleted_at, mantiene archivos en S3 30 días por reversión, después limpia cron.
>
> • reorder(vehicle_id, ordered_photo_ids): reasigna position según el array.
>
> • Si cambia la primera foto, actualiza Vehicle.primary_photo_url.

**Criterios done**

> • Delete y reorder funcionan.

**Tests requeridos**

> • unit/test_photo_service.py.

**Prompt:** P-04

**Fotos, importación y búsqueda**

**T-091 Endpoint POST /api/v1/vehicles/{id}/photos** *\[endpoint · S\]*

**Épica:** E2

**Historias:** E2.6

**Spec técnica:** SDD sección 4.2.2

**Constitución:** Art. 3

**Dependencias:** T-089

**Archivos:** modules/stock/routes.py (photos)

**Descripción**

Subida de fotos en multipart/form-data; soporta múltiples archivos por request.

**Especificación**

> • multipart/form-data con files\[\] (max 10 por request).
>
> • Cada archivo procesado independientemente; respuesta lista con results por archivo (success o error con razón).
>
> • Roles: manager, salesperson asignado, admin_staff.
>
> • Límite total de fotos por vehículo: 30.

**Criterios done**

> • Subida múltiple funciona; errores parciales reportados correctamente.

**Tests requeridos**

> • integration/test_photos_upload.py.

**Prompt:** P-05

**T-092 Endpoint DELETE foto y PATCH reorder** *\[endpoint · S\]*

**Épica:** E2

**Historias:** E2.6

**Spec técnica:** SDD sección 4.2.2

**Constitución:** —

**Dependencias:** T-090

**Archivos:** modules/stock/routes.py

**Descripción**

Endpoints de mantenimiento de fotos.

**Especificación**

> • DELETE /api/v1/vehicles/{id}/photos/{photo_id}.
>
> • PATCH /api/v1/vehicles/{id}/photos/order body: {photo_ids: \[uuid, ...\]}.
>
> • Roles: manager, admin_staff.

**Criterios done**

> • Endpoints funcionales.

**Tests requeridos**

> • integration/test_photo_endpoints.py.

**Prompt:** P-05

**T-093 Migration imports + ImportService.parse_csv** *\[service · M\]*

**Épica:** E2

**Historias:** E2.7

**Spec técnica:** —

**Constitución:** Principio 6

**Dependencias:** T-074

**Archivos:** alembic/versions/016_imports.py; modules/stock/import_service.py

**Descripción**

Tabla de imports + servicio que parsea CSV de vehículos.

**Especificación**

> • Migration imports: id, tenant_id, type ('vehicles'), source_filename, status (pending\|parsing\|validating\|importing\|completed\|failed), total_rows, valid_rows, error_rows, created_by, started_at, completed_at, errors jsonb.
>
> • RLS activo.
>
> • parse_csv: lee CSV, detecta encoding, mapea columnas según template publicado, valida fila por fila.
>
> • Acepta archivos hasta 10MB; máximo 5000 filas por import.
>
> • Output: lista de filas válidas + lista de errores por número de fila.

**Criterios done**

> • Parser maneja CSV bien formado y detecta errores comunes (encoding, separador, columnas faltantes).

**Tests requeridos**

> • unit/test_csv_parser.py con CSVs de fixture.

**Prompt:** P-01 + P-04

**T-094 ImportService.execute (background con Celery)** *\[service · M\]*

**Épica:** E2

**Historias:** E2.7

**Spec técnica:** —

**Constitución:** Principio 6

**Dependencias:** T-093

**Archivos:** modules/stock/import_service.py (extend); modules/stock/tasks.py (Celery task)

**Descripción**

Ejecuta el import en background, fila por fila, llamando a VehicleService.create.

**Especificación**

> • Task Celery import_vehicles_task(import_id) que actualiza estado en cada fase.
>
> • Procesa filas en batches de 100 con commit por batch (no transaction única).
>
> • Errores parciales: continúa con las demás filas; al final, status=completed con errors si los hay.
>
> • Notificación al usuario al completar (in-app + email).
>
> • Idempotencia: si se reintenta el mismo import_id, salta filas ya procesadas.

**Criterios done**

> • Import de 1000 vehículos válidos completa en menos de 2 minutos; errores parciales se reportan.

**Tests requeridos**

> • integration/test_import_execute.py.

**Prompt:** P-04

**T-095 Endpoint POST /api/v1/vehicles/import** *\[endpoint · S\]*

**Épica:** E2

**Historias:** E2.7

**Spec técnica:** —

**Constitución:** Art. 3

**Dependencias:** T-094

**Archivos:** modules/stock/routes.py

**Descripción**

Endpoint que recibe el CSV y dispara el import en background.

**Especificación**

> • POST multipart/form-data con file.
>
> • Valida tamaño y mime; crea fila imports en estado pending.
>
> • Encola task Celery; devuelve 202 Accepted con import_id y URL para consultar estado.
>
> • Roles: manager, admin_staff.

**Criterios done**

> • Endpoint dispara el import correctamente.

**Tests requeridos**

> • integration/test_import_endpoint.py.

**Prompt:** P-05

**T-096 Endpoint GET /api/v1/imports/{id}** *\[endpoint · XS\]*

**Épica:** E2

**Historias:** E2.7

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-095

**Archivos:** modules/stock/routes.py

**Descripción**

Estado y resultado del import; útil para que la UI hagaa polling.

**Especificación**

> • GET con detalle completo: status, total/valid/error, errors\[\] con detalle por fila, created_by, timestamps.
>
> • Roles: manager, admin_staff (y el creador del import).

**Criterios done**

> • Endpoint devuelve estado actualizado.

**Tests requeridos**

> • integration/test_import_status.py.

**Prompt:** P-05

**T-097 Template de CSV descargable + endpoint** *\[endpoint · S\]*

**Épica:** E2

**Historias:** E2.7

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-095

**Archivos:** modules/stock/routes.py; backend/data/templates/vehicles_import_template.csv

**Descripción**

Provee al usuario el template CSV con columnas correctas y ejemplos.

**Especificación**

> • GET /api/v1/vehicles/import/template devuelve CSV con headers + 2 filas de ejemplo.
>
> • Headers documentados con comentarios en la doc de la API.

**Criterios done**

> • Descarga funciona; template es válido para reimportarse.

**Tests requeridos**

> • integration/test_template_download.py.

**Prompt:** P-05

**T-098 OpenSearch index para vehicles + sync** *\[infra · L\]*

**Épica:** E2

**Historias:** E2.8

**Spec técnica:** SDD ADR-005

**Constitución:** Art. 4

**Dependencias:** T-074

**Archivos:** core/search.py; modules/stock/search_indexer.py; infra/opensearch/vehicles_mapping.json

**Descripción**

Configura el índice OpenSearch y mantiene sincronización event-driven con la tabla vehicles.

**Especificación**

> • Mapping con campos analizados (description con análisis español + sinónimos comunes), keyword (status, brand, model), numéricos (year, price, mileage), geo_point (location de branch).
>
> • Indexer que se suscribe a eventos vehicle.created, .updated, .archived y refleja cambios en el índice.
>
> • Bootstrap inicial: comando que reindexa toda la tabla vehicles del tenant.
>
> • Idempotencia mediante version_seq.
>
> • Filter context para multi-tenancy (term tenant_id en cada query).

**Criterios done**

> • Crear vehículo lo deja indexado en menos de 5 segundos; búsqueda devuelve resultados.

**Tests requeridos**

> • integration/test_search_indexer.py con OpenSearch container.

**Prompt:** P-libre con anchor a ADR-005

**T-099 Endpoint GET /api/v1/vehicles/search** *\[endpoint · M\]*

**Épica:** E2

**Historias:** E2.8

**Spec técnica:** SDD sección 4.2.2

**Constitución:** Art. 4

**Dependencias:** T-098

**Archivos:** modules/stock/routes.py; modules/stock/search_service.py

**Descripción**

Endpoint dedicado a búsqueda full-text con relevancia, complementario al GET /vehicles tradicional.

**Especificación**

> • Query params: q (texto libre), filters (status, price range, year range, etc.), sort (relevance\|price\|year).
>
> • Relevancia: pesos altos para brand+model+version, medios para description, bajos para color/notas.
>
> • Retorna VehicleListItem\[\] + score + highlights (snippets resaltados).
>
> • Pagination con from/size, max from+size = 1000.
>
> • Roles: cualquier usuario autenticado del tenant.

**Criterios done**

> • Búsqueda devuelve resultados relevantes; tiempo p95 \< 150ms.

**Tests requeridos**

> • integration/test_search.py.

**Prompt:** P-05

**T-100 Endpoint search-as-you-type (autocomplete)** *\[endpoint · S\]*

**Épica:** E2

**Historias:** E2.8

**Spec técnica:** SDD sección 4.2.2

**Constitución:** Art. 4

**Dependencias:** T-099

**Archivos:** modules/stock/routes.py

**Descripción**

Endpoint optimizado para sugerencias en tiempo real durante la escritura.

**Especificación**

> • GET /api/v1/vehicles/suggest?q= con debounce esperado del lado cliente.
>
> • Devuelve hasta 10 resultados livianos: id, brand_name + model_name + year + price.
>
> • Use OpenSearch search_as_you_type field type.
>
> • p95 \< 50ms.

**Criterios done**

> • Endpoint responde rápido; integración cliente útil.

**Tests requeridos**

> • integration/test_suggest.py.

**Prompt:** P-05

**Frontend de Stock**

**T-101 Página listado de stock** *\[frontend-page · L\]*

**Épica:** E2

**Historias:** E2.2, E2.8

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-080, T-099, T-038, T-039

**Archivos:** frontend-web/src/app/(authed)/stock/page.tsx; components/domain/VehicleTable.tsx; VehicleFiltersPanel.tsx

**Descripción**

Página principal del módulo Stock. Lista vehículos con tabla, filtros laterales, búsqueda, paginación y acciones.

**Especificación**

> • Layout: filtros laterales (colapsables en mobile como drawer), tabla central, top bar con búsqueda + ordenamiento + botón “nuevo vehículo” + import CSV.
>
> • Filtros: status (chips), branch, brand+model cascada, year range slider, price range slider, mileage max, fuel_type, transmission.
>
> • URL state: filtros y orden persisten en query params.
>
> • Tabla con columnas: foto, brand-model-version, año, km, color, precio, estado, asignado a, acciones (...). Sortable.
>
> • Vista alternativa: grid de cards (toggle en topbar).
>
> • Paginación: por defecto cursor; opción “cargar más” al final.
>
> • Skeleton loader mientras carga.
>
> • Estado vacío con CTA si no hay vehículos.

**Criterios done**

> • Listado funcional con todos los filtros; toggle vista; performance buena con 5000 vehículos.

**Tests requeridos**

> • e2e/stock_list.spec.ts.

**Prompt:** P-10

**T-102 Componente VehicleCard (vista grid alternativa)** *\[frontend-component · M\]*

**Épica:** E2

**Historias:** E2.2

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-037, T-101

**Archivos:** components/domain/VehicleCard.tsx

**Descripción**

Card compacta para vista grid del listado.

**Especificación**

> • Foto principal (lazy load con blurhash placeholder).
>
> • Brand + model + version + año destacados.
>
> • Precio formato AR (\$XXX.XXX).
>
> • Badge de estado.
>
> • Datos secundarios: km, transmisión, combustible.
>
> • Hover muestra acciones quick: editar, ver detalle.
>
> • Click navega a detalle.
>
> • Responsive: 4 cols en xl, 3 en lg, 2 en md, 1 en sm.

**Criterios done**

> • Card lookea bien en todos los breakpoints.

**Tests requeridos**

> • unit/components/VehicleCard.test.tsx.

**Prompt:** P-08

**T-103 Página detalle de vehículo** *\[frontend-page · L\]*

**Épica:** E2

**Historias:** E2.4, E2.5, E2.6, E2.9

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-081, T-101

**Archivos:** frontend-web/src/app/(authed)/stock/\[id\]/page.tsx

**Descripción**

Página de detalle con galería, datos, historial y acciones del vehículo.

**Especificación**

> • Layout dos columnas: izquierda galería de fotos (componente PhotoGallery), derecha datos + acciones.
>
> • Galería con foto principal grande + thumbnails; carrusel; full-screen al click.
>
> • Datos organizados por secciones: Identificación (brand/model/version/year), Técnicos (km/combustible/transmisión/etc), Comercial (precio/estado/sucursal/asignado), Descripción, Notas internas (visible solo para roles autorizados).
>
> • Acciones: editar, cambiar estado (modal con dropdown + razón), archivar, asignar vendedor.
>
> • Tabs adicionales: Historial (timeline con cambios de estado y eventos), Leads asociados, Documentos (placeholder).
>
> • Botón “ver en deRuedas” si está publicado (link al portal con publishing_id de E3).

**Criterios done**

> • Detalle muestra todo; acciones funcionan; historial se ve cronológico.

**Tests requeridos**

> • e2e/stock_detail.spec.ts.

**Prompt:** P-10

**T-104 Página alta de vehículo** *\[frontend-page · L\]*

**Épica:** E2

**Historias:** E2.3

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-078, T-070, T-091

**Archivos:** frontend-web/src/app/(authed)/stock/new/page.tsx; components/domain/VehicleForm.tsx

**Descripción**

Formulario completo para alta de vehículo.

**Especificación**

> • Form en secciones colapsables: Identificación (VehicleSelector + año), Técnicos (km, fuel, transmission, body, doors, color), Comercial (precio, sucursal, asignado, estado inicial), Identificadores (dominio, chasis, motor), Descripción, Fotos (subida drag&drop después de crear).
>
> • Validación inline con Zod schema espejo del backend.
>
> • Botón “guardar y agregar otro” que limpia el form.
>
> • Botón “guardar y volver al listado”.
>
> • Submit hace POST + (si hay fotos) sube cada una; si la subida de alguna foto falla, el vehículo queda creado y se muestra error de la foto.
>
> • Atajos de teclado: Ctrl+Enter para guardar.

**Criterios done**

> • Alta completa funciona; experiencia fluida; validación clara.

**Tests requeridos**

> • e2e/stock_create.spec.ts.

**Prompt:** P-09

**T-105 Página edición de vehículo** *\[frontend-page · M\]*

**Épica:** E2

**Historias:** E2.4

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-104

**Archivos:** frontend-web/src/app/(authed)/stock/\[id\]/edit/page.tsx

**Descripción**

Reutiliza VehicleForm en modo edición con valores cargados.

**Especificación**

> • GET inicial del vehículo, pre-cargar form.
>
> • Campos no editables marcados como readonly (chassis_number).
>
> • Submit hace PATCH con diff.
>
> • Si hay cambios sin guardar, advertir al navegar fuera.

**Criterios done**

> • Edición funciona; cambios persisten.

**Tests requeridos**

> • e2e/stock_edit.spec.ts.

**Prompt:** P-09

**T-106 Componente PhotoUploader con drag & drop** *\[frontend-component · M\]*

**Épica:** E2

**Historias:** E2.6

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-091, T-037

**Archivos:** components/domain/PhotoUploader.tsx

**Descripción**

Componente reutilizable para subir fotos al detalle de vehículo.

**Especificación**

> • Zone drag & drop + button alternativo.
>
> • Preview thumbnail mientras sube; barra de progreso por archivo.
>
> • Validación cliente: tamaño, mime, dimensiones (resize en cliente para reducir upload time si \> 2MB usando canvas).
>
> • Errores parciales por foto reportados.
>
> • Cancel de upload en progreso.
>
> • Soporta paste desde portapapeles (mobile no aplica).

**Criterios done**

> • Subida múltiple funciona; UX clara durante uploads largos.

**Tests requeridos**

> • unit/components/PhotoUploader.test.tsx.

**Prompt:** P-08

**T-107 Componente PhotoGallery con reorder** *\[frontend-component · M\]*

**Épica:** E2

**Historias:** E2.6

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-092, T-037

**Archivos:** components/domain/PhotoGallery.tsx

**Descripción**

Galería visual de las fotos del vehículo con reordenamiento drag & drop.

**Especificación**

> • Grid de thumbnails con primera marcada como “principal”.
>
> • Drag & drop para reordenar (dnd-kit).
>
> • Click abre lightbox full-screen con navegación.
>
> • Delete con confirmación.
>
> • Indicador visual del cambio: thumbnail destacado mientras se está moviendo.
>
> • Save automatic al soltar (debounced 500ms).

**Criterios done**

> • Reordenamiento funciona; primera foto se actualiza visiblemente.

**Tests requeridos**

> • unit/components/PhotoGallery.test.tsx + e2e.

**Prompt:** P-08

**T-108 Página importación CSV de vehículos** *\[frontend-page · M\]*

**Épica:** E2

**Historias:** E2.7

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-095, T-096, T-097

**Archivos:** frontend-web/src/app/(authed)/stock/import/page.tsx

**Descripción**

Wizard de importación masiva: descargar template, subir, ver progreso, ver resultado.

**Especificación**

> • Paso 1: explicación + botón descargar template.
>
> • Paso 2: drag & drop de CSV; preview de primeras 5 filas con detección de errores comunes.
>
> • Paso 3: confirmar e iniciar import; redirige a página de progreso.
>
> • Paso 4: progreso en tiempo real (polling cada 2s); al completar, muestra resumen (X importados, Y errores) con tabla descargable de errores por fila.
>
> • Persistencia: si el usuario navega fuera y vuelve, ve el último import en progreso.

**Criterios done**

> • Flujo completo de importación de 100 filas funciona end-to-end.

**Tests requeridos**

> • e2e/stock_import.spec.ts.

**Prompt:** P-10

**T-109 Vista pública de imports recientes** *\[frontend-page · S\]*

**Épica:** E2

**Historias:** E2.7

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-108

**Archivos:** frontend-web/src/app/(authed)/stock/imports/page.tsx

**Descripción**

Listado de los imports realizados por el tenant para auditoría.

**Especificación**

> • Tabla con: fecha, archivo, filas válidas/error, estado, creado por, acciones (ver detalle, descargar errores).
>
> • Filtro por status.

**Criterios done**

> • Listado funcional.

**Tests requeridos**

> • —

**Prompt:** P-10

**T-110 Frontend: barra de búsqueda global con quick search** *\[frontend-component · M\]*

**Épica:** E2

**Historias:** E2.8

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-100, T-038

**Archivos:** components/layout/GlobalSearch.tsx

**Descripción**

Búsqueda global accesible desde la topbar (cmd+k) que pega contra el endpoint suggest de vehicles + más adelante leads y contactos.

**Especificación**

> • Atajo Cmd+K / Ctrl+K para abrir.
>
> • Input con debounce 200ms.
>
> • Resultados agrupados por tipo (Vehicles, Leads, Contacts cuando E4 esté).
>
> • Para MVP solo Vehicles activo.
>
> • Click en resultado navega.
>
> • Recientes guardados en localStorage.

**Criterios done**

> • Búsqueda global funciona; resultados son rápidos.

**Tests requeridos**

> • unit/components/GlobalSearch.test.tsx.

**Prompt:** P-08

**T-111 Componente VehicleStatusBadge + StatusTransitionModal** *\[frontend-component · S\]*

**Épica:** E2

**Historias:** E2.5

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-082, T-037

**Archivos:** components/domain/VehicleStatusBadge.tsx; VehicleStatusTransitionModal.tsx

**Descripción**

Componentes reutilizables para mostrar el estado y permitir transiciones.

**Especificación**

> • Badge con color por estado (available verde, reserved amarillo, sold gris, in_workshop azul, in_preparation naranja, archived rojo).
>
> • Modal con select de estado destino (solo válidos según estado actual + máquina del backend) + razón obligatoria/opcional según transición + notas.
>
> • Mensaje del backend si la transición es inválida.

**Criterios done**

> • Componentes reutilizables; usados en detalle y tabla.

**Tests requeridos**

> • unit/components.

**Prompt:** P-08

**T-112 Tests E2E del flujo completo de stock** *\[test-e2e · M\]*

**Épica:** E2

**Historias:** E2.3, E2.4, E2.5, E2.6, E2.7, E2.8

**Spec técnica:** —

**Constitución:** Art. 2

**Dependencias:** T-104, T-105, T-103, T-108

**Archivos:** frontend-web/tests/e2e/stock_full_flow.spec.ts

**Descripción**

Test E2E que ejercita el flujo completo del módulo Stock.

**Especificación**

> • Login como manager.
>
> • Crear vehículo con datos completos.
>
> • Subir 3 fotos.
>
> • Editar datos.
>
> • Cambiar estado a available.
>
> • Buscar el vehículo en el listado.
>
> • Ver detalle.
>
> • Importar 5 vehículos por CSV.
>
> • Verificar que aparecen en el listado.
>
> • Archivar uno.
>
> • Verificar que el archivado no aparece en lista por default.

**Criterios done**

> • Test pasa de extremo a extremo en CI.

**Tests requeridos**

> • —

**Prompt:** P-12

**T-113 Documentación de uso del módulo Stock para usuarios** *\[docs · S\]*

**Épica:** E2

**Historias:** E2.\*

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-112

**Archivos:** docs/user-guide/stock.md

**Descripción**

Manual de usuario del módulo Stock con screenshots y casos de uso típicos.

**Especificación**

> • Cómo cargar el primer vehículo.
>
> • Cómo subir fotos.
>
> • Cómo importar masivamente.
>
> • Cómo cambiar estados y qué significan.
>
> • Cómo buscar y filtrar.
>
> • FAQ con casos comunes.

**Criterios done**

> • Documento legible para un usuario no técnico.

**Tests requeridos**

> • —

**Prompt:** P-libre

**T-114 Performance hardening del módulo Stock** *\[infra · M\]*

**Épica:** E2

**Historias:** E2.2, E2.8

**Spec técnica:** SDD sección 6 (NFRs)

**Constitución:** Art. 4

**Dependencias:** T-080, T-099

**Archivos:** tests/perf/stock_load_test.py (k6 o locust); tuning de queries

**Descripción**

Test de carga + ajustes de performance en queries críticas del módulo.

**Especificación**

> • Test de carga con 50 usuarios concurrentes haciendo lista + búsqueda + creación durante 5 minutos.
>
> • Targets: lista p95 \< 200ms con 10k vehículos; búsqueda p95 \< 150ms; creación p95 \< 300ms.
>
> • Identificar queries lentas con pg_stat_statements; agregar índices o reescribir si necesario.
>
> • Documentar resultados en docs/runbooks/stock-perf.md.

**Criterios done**

> • Targets se cumplen en ambiente de staging.

**Tests requeridos**

> • —

**Prompt:** P-libre

**6.2.3 E3 — Publicación al portal deRuedas**

Esta versión del MVP incluye solamente el conector al portal propio deRuedas. Los conectores a MercadoLibre Vehículos y a Marketplace de Facebook se posponen a la fase F2 según se declaró en la sección 3.2.

**T-115 Migration vehicle_publications** *\[migration · S\]*

**Épica:** E3

**Historias:** E3.1, E3.2

**Spec técnica:** SDD sección 3.5

**Constitución:** Principio 4, 5

**Dependencias:** T-071

**Archivos:** alembic/versions/017_vehicle_publications.py; modules/publishing/models.py

**Descripción**

Tabla que registra la relación entre un vehículo y su publicación en cada canal externo.

**Especificación**

> • Campos: id, tenant_id, vehicle_id, channel ('deruedas'), external_id (str), status (pending\|published\|updating\|failed\|unpublished), last_synced_at, last_error, retry_count, payload_hash (para detectar cambios), timestamps.
>
> • UNIQUE (tenant_id, vehicle_id, channel) — una publicación por vehículo por canal.
>
> • Índices: (tenant_id, status), (channel, status, last_synced_at).
>
> • RLS activo.

**Criterios done**

> • Migration aplica.

**Tests requeridos**

> • integration/test_publications_migration.py.

**Prompt:** P-01 con table=vehicle_publications

**T-116 PublishingService orquestador** *\[service · M\]*

**Épica:** E3

**Historias:** E3.1

**Spec técnica:** SDD sección 3.5

**Constitución:** Principio 6

**Dependencias:** T-115

**Archivos:** modules/publishing/{repository,service}.py

**Descripción**

Servicio que orquesta operaciones de publicación, decoupled del conector específico.

**Especificación**

> • Métodos: schedule_publish(vehicle_id, channel), schedule_update, schedule_unpublish, get_status(vehicle_id, channel).
>
> • Lógica: insertar fila en vehicle_publications con status=pending; encolar task Celery hacia el adapter del canal.
>
> • Determina el adapter correcto por channel (“deruedas” → DerRuedasPublisher).
>
> • Maneja el estado: actualiza según resultado del adapter.
>
> • Settings del tenant: si publishing.deruedas.enabled = false, no publica.

**Criterios done**

> • schedule_publish encola correctamente; get_status devuelve estado actual.

**Tests requeridos**

> • unit/test_publishing_service.py.

**Prompt:** P-04

**T-117 DerRuedasAdapter (cliente HTTP del portal)** *\[infra · M\]*

**Épica:** E3

**Historias:** E3.1

**Spec técnica:** SDD sección 3.5

**Constitución:** Art. 3, 6

**Dependencias:** T-116

**Archivos:** modules/publishing/adapters/deruedas_adapter.py

**Descripción**

Cliente HTTP tipado contra la API del portal deRuedas con autenticación y manejo de errores.

**Especificación**

> • Cliente httpx async con timeout (10s) y retry interno básico (3 con backoff).
>
> • Auth: API key del tenant en header X-Tenant-API-Key (lookup desde tenant settings cifrados).
>
> • Métodos: create_listing(payload), update_listing(external_id, payload), delete_listing(external_id), get_listing(external_id).
>
> • Manejo de errores: mapea HTTP errors a excepciones tipadas (DerRuedasUnauthorizedError, DerRuedasNotFoundError, DerRuedasValidationError, DerRuedasTransientError, DerRuedasFatalError).
>
> • Logging de cada llamada con duración y status.

**Criterios done**

> • Cliente funciona contra API mock del portal en dev.

**Tests requeridos**

> • integration/test_deruedas_adapter.py con httpx-mock o respx.

**Prompt:** P-libre

**T-118 DerRuedasPublisher con mapping vehicle→listing** *\[service · M\]*

**Épica:** E3

**Historias:** E3.1, E3.2

**Spec técnica:** SDD sección 3.5

**Constitución:** Principio 6

**Dependencias:** T-117

**Archivos:** modules/publishing/publishers/deruedas_publisher.py

**Descripción**

Publisher específico de deRuedas que toma un Vehicle y lo traduce al payload de la API del portal.

**Especificación**

> • Función map_vehicle_to_listing(vehicle, photos, branch) que produce el payload exacto de la API.
>
> • Mapeo de fields: brand_name + model_name + version_name + year → title; description (con fallback automático si está vacía); fotos (URLs originales con CDN del portal); precio; ubicación (ciudad/provincia desde branch).
>
> • publish(vehicle_id): obtiene vehicle + photos, mapea, llama adapter.create_listing, persiste external_id en vehicle_publications.
>
> • update(vehicle_id): mismo mapeo; si payload_hash no cambió, skip; si cambió, adapter.update_listing.
>
> • unpublish(vehicle_id): adapter.delete_listing + status='unpublished'.
>
> • Validaciones: vehículo debe tener al menos 1 foto y precio \> 0; si no, falla con código 'cannot_publish_incomplete' (sin reintento).

**Criterios done**

> • Publicar un vehículo lo deja con external_id en la tabla y registrado del lado del portal.

**Tests requeridos**

> • integration/test_deruedas_publisher.py.

**Prompt:** P-04

**T-119 Consumer eventos vehicle.\* → publishing** *\[event · M\]*

**Épica:** E3

**Historias:** E3.1, E3.2

**Spec técnica:** SDD sección 2.4, 4.3

**Constitución:** Principio 6

**Dependencias:** T-118

**Archivos:** modules/publishing/event_handlers.py

**Descripción**

Suscriptores a eventos del módulo stock que disparan acciones de publicación correspondientes.

**Especificación**

> • Handler vehicle.created: si tenant tiene deruedas enabled y status=available, schedule_publish.
>
> • Handler vehicle.updated: si está publicado, schedule_update.
>
> • Handler vehicle.status_changed: si pasa a available, schedule_publish; si sale de available (reserved/sold/archived), schedule_unpublish.
>
> • Handler vehicle.photo_uploaded: schedule_update si publicado (para reflejar nueva foto).
>
> • Idempotencia: cada handler usa event_id como dedup key.
>
> • Errores transitorios → reintento con backoff; permanentes → DLQ + notificación al manager del tenant.

**Criterios done**

> • Crear vehículo dispara publicación; cambiar a sold dispara unpublish.

**Tests requeridos**

> • integration/test_publishing_consumers.py.

**Prompt:** P-07

**T-120 Endpoint GET /api/v1/vehicles/{id}/publications** *\[endpoint · XS\]*

**Épica:** E3

**Historias:** E3.3

**Spec técnica:** —

**Constitución:** Art. 3

**Dependencias:** T-115

**Archivos:** modules/publishing/routes.py

**Descripción**

Devuelve el estado de publicación del vehículo en cada canal.

**Especificación**

> • GET /api/v1/vehicles/{id}/publications.
>
> • Respuesta: lista de PublicationRead con channel, status, external_id, last_synced_at, last_error si aplica, link al portal cuando published.
>
> • Roles: cualquier user del tenant.

**Criterios done**

> • Endpoint devuelve estado correcto.

**Tests requeridos**

> • integration/test_publication_status.py.

**Prompt:** P-05

**T-121 Endpoint POST /api/v1/vehicles/{id}/publications/republish** *\[endpoint · S\]*

**Épica:** E3

**Historias:** E3.3

**Spec técnica:** —

**Constitución:** Art. 3

**Dependencias:** T-119

**Archivos:** modules/publishing/routes.py

**Descripción**

Permite forzar una republicación manual cuando el flujo automático falló o se sospecha desincronización.

**Especificación**

> • Body: {channel}.
>
> • Encola schedule_publish forzado, ignorando payload_hash.
>
> • Roles: manager, admin_staff.
>
> • Rate limit: 1 request por vehículo por minuto.

**Criterios done**

> • Republish manual funciona.

**Tests requeridos**

> • integration/test_republish.py.

**Prompt:** P-05

**T-122 Backoff exponencial + DLQ + alerta del módulo** *\[infra · M\]*

**Épica:** E3

**Historias:** E3.4

**Spec técnica:** SDD sección 2.4, 9.5

**Constitución:** Principio 6

**Dependencias:** T-119

**Archivos:** modules/publishing/event_handlers.py (extend); modules/publishing/dlq_handler.py

**Descripción**

Política de reintentos para errores transitorios y manejo de DLQ con notificación al manager del tenant.

**Especificación**

> • Política: 5 reintentos, backoff base 60s, factor 2, max 30min. Total ~60min.
>
> • Después de agotar reintentos, fila va a DLQ table y status='failed' con last_error explicativo.
>
> • Notificación in-app al manager del tenant: “Publicación fallida: \<vehículo\>” con link al detalle.
>
> • Cron diario que reintenta DLQ items con error transient (recoverable manual).
>
> • Métrica publishing_dlq_total para alertar.

**Criterios done**

> • Falla transiente reintenta y recupera; falla persistente termina en DLQ con notificación.

**Tests requeridos**

> • integration/test_publishing_dlq.py.

**Prompt:** P-libre

**T-123 Configuración del conector deRuedas en settings** *\[frontend-page · M\]*

**Épica:** E3

**Historias:** E3.1, E3.5

**Spec técnica:** —

**Constitución:** Art. 3, Principio 2

**Dependencias:** T-117, T-038

**Archivos:** frontend-web/src/app/(authed)/settings/integrations/deruedas/page.tsx

**Descripción**

Pantalla en settings donde el manager activa la integración con el portal y guarda la API key.

**Especificación**

> • Toggle activar/desactivar.
>
> • Input para API key (write-only; muestra solo últimos 4 chars una vez guardada).
>
> • Botón “probar conexión” que ejecuta un test contra el portal.
>
> • Configuraciones adicionales: condiciones por defecto a publicar (ej. precio mínimo, sucursales habilitadas).
>
> • Roles: manager.

**Criterios done**

> • Activar conector funciona; test connection devuelve OK/FAIL claro.

**Tests requeridos**

> • e2e/integration_deruedas.spec.ts.

**Prompt:** P-09 + P-10

**T-124 Componente PublicationBadge + panel en detalle** *\[frontend-component · S\]*

**Épica:** E3

**Historias:** E3.3

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-120, T-103, T-037

**Archivos:** components/domain/PublicationBadge.tsx; PublicationsPanel.tsx

**Descripción**

Componentes visuales que muestran el estado de publicación.

**Especificación**

> • PublicationBadge: chip pequeño con color por estado (published verde, pending amarillo, failed rojo).
>
> • Usado en VehicleListItem (esquina superior derecha de la card).
>
> • PublicationsPanel: panel con tabla por canal mostrando estado, link al portal, botón “republicar”, botón “despublicar”, mensaje de error si failed.
>
> • Usado en página de detalle de vehículo (T-103).

**Criterios done**

> • Badge se ve en lista; panel funcional en detalle.

**Tests requeridos**

> • unit/components/Publication\*.test.tsx.

**Prompt:** P-08

**T-125 Test E2E flujo publishing** *\[test-e2e · M\]*

**Épica:** E3

**Historias:** E3.1, E3.2, E3.3

**Spec técnica:** —

**Constitución:** Art. 2

**Dependencias:** T-124

**Archivos:** frontend-web/tests/e2e/publishing.spec.ts

**Descripción**

Test E2E con mock del adapter de deRuedas que verifica el flujo completo.

**Especificación**

> • Setup: tenant con conector deRuedas activado (mock).
>
> • Crear vehículo con foto y precio.
>
> • Cambiar status a available.
>
> • Esperar (con waitFor) que el badge en la lista pase a published.
>
> • Verificar en panel de detalle el external_id.
>
> • Editar precio.
>
> • Verificar que se republicó (badge updating → published, last_synced_at actualizado).
>
> • Cambiar status a sold.
>
> • Verificar que pasa a unpublished.

**Criterios done**

> • Test pasa con mock del portal.

**Tests requeridos**

> • —

**Prompt:** P-12

**T-126 Cifrado de API keys de integraciones** *\[infra · S\]*

**Épica:** E3

**Historias:** E3.5

**Spec técnica:** SDD sección 8.5

**Constitución:** Art. 3 (secretos)

**Dependencias:** T-123

**Archivos:** core/secrets.py; modules/tenancy/service.py (extender para encrypted secrets)

**Descripción**

Mecanismo de cifrado simétrico para secretos por tenant (API keys de conectores).

**Especificación**

> • Cifrado AES-GCM con clave maestra desde KMS o variable de entorno.
>
> • Helper encrypt_for_tenant(plaintext, tenant_id), decrypt_for_tenant.
>
> • Almacenamiento en columna jsonb con campos {ciphertext, nonce, version}.
>
> • Rotación de clave: comando administrativo que recifra todos los secretos con nueva clave.
>
> • Logging: nunca loguear plaintext; los logs muestran solo “\[REDACTED\]” para campos secretos.

**Criterios done**

> • API key se guarda cifrada; se descifra solo al usarse.

**Tests requeridos**

> • unit/test_secrets.py.

**Prompt:** P-libre

**T-127 Métricas y alertas del módulo publishing** *\[infra · S\]*

**Épica:** E3

**Historias:** E3.4

**Spec técnica:** SDD sección 9.5

**Constitución:** Principio 6

**Dependencias:** T-122, T-029

**Archivos:** modules/publishing/metrics.py; infra/observability/grafana/dashboards/publishing.json

**Descripción**

Métricas Prometheus específicas del módulo + dashboard Grafana + reglas de alerta.

**Especificación**

> • publishing_publish_total{channel, result}, publishing_publish_duration_seconds, publishing_dlq_total.
>
> • Dashboard con: rate de publicaciones, success rate, latencia, queue lag, DLQ size.
>
> • Alerta: success rate \< 95% en últimos 30min → warning; DLQ \> 10 items → critical.

**Criterios done**

> • Dashboard se ve en Grafana; alertas dispararían correctamente con datos sintéticos.

**Tests requeridos**

> • —

**Prompt:** P-libre

**T-128 Reconciliación periódica con el portal** *\[service · M\]*

**Épica:** E3

**Historias:** E3.4

**Spec técnica:** —

**Constitución:** Principio 6

**Dependencias:** T-118

**Archivos:** modules/publishing/reconcile.py; cron job

**Descripción**

Job nocturno que compara el estado local con el del portal y detecta desincronizaciones.

**Especificación**

> • Cron Celery beat cada 24h por tenant con conector activo.
>
> • Por cada publication local en status='published', llama get_listing y verifica que existe.
>
> • Si no existe en portal: marca como out_of_sync; encola republish.
>
> • Si existe pero datos clave difieren (precio, status): encola update.
>
> • Métrica reconcile_diffs_total para monitoreo.

**Criterios done**

> • Job detecta y corrige desincronizaciones simuladas.

**Tests requeridos**

> • integration/test_reconcile.py.

**Prompt:** P-04

**T-129 Documentación: contrato API deRuedas + runbook** *\[docs · S\]*

**Épica:** E3

**Historias:** —

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-128

**Archivos:** docs/runbooks/publishing-deruedas.md; docs/integrations/deruedas-api-contract.md

**Descripción**

Documentación operativa del módulo publishing y contrato de la API del portal.

**Especificación**

> • Contrato API: endpoints, payloads, errores, rate limits.
>
> • Runbook: qué hacer si DLQ crece, cómo forzar republish masivo, cómo rotar API keys.
>
> • Diagrama de secuencia del flujo de publicación.

**Criterios done**

> • Docs accesibles para on-call.

**Tests requeridos**

> • —

**Prompt:** P-libre

**6.2.4 E4 — CRM básico**

Cubre la gestión de contactos, leads, pipeline configurable, actividades y la integración interna con stock (vehículo asociado) y comunicación (conversaciones de WhatsApp vinculadas a leads).

**Contactos**

**T-130 Migration contacts** *\[migration · S\]*

**Épica:** E4

**Historias:** E4.1

**Spec técnica:** SDD sección 3.6

**Constitución:** Principio 4, Art. 3

**Dependencias:** T-022

**Archivos:** alembic/versions/018_contacts.py; modules/crm/models.py (Contact)

**Descripción**

Tabla central de contactos del CRM. Es la entidad personal sobre la que se construye el pipeline.

**Especificación**

> • Campos: id, tenant_id, full_name, phone (E.164), phone_alt, email, dni (nullable), source (string code), tags text\[\], notes, do_not_contact (bool), assigned_user_id (nullable), birthday (nullable), created_by_user_id, timestamps, deleted_at.
>
> • UNIQUE (tenant_id, phone) WHERE deleted_at IS NULL — un contacto por teléfono por tenant.
>
> • Índices: (tenant_id, assigned_user_id), GIN sobre tags, trgm sobre full_name.
>
> • RLS activo.

**Criterios done**

> • Migration aplica; UNIQUE de phone funciona.

**Tests requeridos**

> • integration/test_contacts_migration.py.

**Prompt:** P-01 con table=contacts

**T-131 ContactRepository + schemas + service** *\[service · M\]*

**Épica:** E4

**Historias:** E4.1, E4.2

**Spec técnica:** SDD sección 3.6

**Constitución:** —

**Dependencias:** T-130

**Archivos:** modules/crm/{repository,schemas,service}.py (sección contacts)

**Descripción**

CRUD de contactos con búsqueda y deduplicación.

**Especificación**

> • Repository con CRUD + filtros: assigned_user, tags, search (full-text por name+phone+email).
>
> • Schemas: ContactCreate, ContactUpdate, ContactRead, ContactListItem.
>
> • Service: create con dedup por phone (si existe, devuelve conflicto + opción de merge); update; soft_delete.
>
> • Validación: phone en formato E.164 (asumir AR si no tiene country code).
>
> • Validación: si DNI presente, formato válido AR.

**Criterios done**

> • Crear contacto con phone duplicado da 409 con sugerencia de merge.

**Tests requeridos**

> • unit/test_contact_service.py.

**Prompt:** P-02 + P-03 + P-04

**T-132 ContactService.merge (de-duplicación)** *\[service · M\]*

**Épica:** E4

**Historias:** E4.3

**Spec técnica:** —

**Constitución:** Principio 3, 5

**Dependencias:** T-131

**Archivos:** modules/crm/service.py (extend)

**Descripción**

Lógica de fusión de contactos duplicados que combina datos y reasigna referencias.

**Especificación**

> • merge(primary_id, secondary_id, ctx): combina datos, marca secondary como deleted_at, mueve leads y conversaciones de secondary a primary.
>
> • Estrategia de combinación: primary mantiene fields no-null; donde primary tiene null, copia de secondary; tags se unen; notas se concatenan con separador.
>
> • Audit log obligatorio: registra ambos IDs y el detalle del merge.
>
> • Evento contact.merged publicado para que otros módulos reaccionen.
>
> • Solo manager o admin_staff pueden mergear.

**Criterios done**

> • Merge funciona; leads del secondary aparecen en primary; secondary queda archivado.

**Tests requeridos**

> • unit/test_contact_merge.py + integration.

**Prompt:** P-04

**T-133 Endpoints contactos** *\[endpoint · S\]*

**Épica:** E4

**Historias:** E4.1, E4.2, E4.3

**Spec técnica:** SDD sección 4.2.4

**Constitución:** Art. 3

**Dependencias:** T-131, T-132

**Archivos:** modules/crm/routes.py (contacts)

**Descripción**

Endpoints CRUD + search + merge para contactos.

**Especificación**

> • GET /api/v1/contacts (list con filtros, paginación).
>
> • GET /api/v1/contacts/{id}.
>
> • POST /api/v1/contacts.
>
> • PATCH /api/v1/contacts/{id}.
>
> • DELETE /api/v1/contacts/{id} (soft).
>
> • POST /api/v1/contacts/{primary_id}/merge body: {secondary_id}.
>
> • GET /api/v1/contacts/search?phone= (lookup por teléfono normalizado para usar desde otros módulos).
>
> • Roles: manager, salesperson (los suyos asignados), admin_staff.

**Criterios done**

> • Todos los endpoints; tests pasan.

**Tests requeridos**

> • integration/test_contacts_routes.py.

**Prompt:** P-05

**T-134 Detección de duplicados al crear contacto** *\[service · S\]*

**Épica:** E4

**Historias:** E4.3

**Spec técnica:** —

**Constitución:** Principio 6

**Dependencias:** T-131

**Archivos:** modules/crm/duplicate_detector.py

**Descripción**

Lógica fuzzy de detección de posibles duplicados al crear un contacto, antes de la check estricta de UNIQUE phone.

**Especificación**

> • Endpoint side: al hacer POST contact, si phone normalizado no es duplicado exacto pero hay candidatos por similitud (mismo email, o nombre similar + dni igual, o phone con últimos 8 dígitos iguales), devolver 200 con flag possible_duplicates: \[...\].
>
> • El cliente decide: confirmar creación con flag override=true, o llevar a la pantalla de merge.
>
> • Heurísticas configurables por tenant en settings.

**Criterios done**

> • Crear con datos similares a otro contacto sugiere posibles duplicados.

**Tests requeridos**

> • unit/test_duplicate_detector.py.

**Prompt:** P-04

**T-135 Frontend: listado de contactos** *\[frontend-page · M\]*

**Épica:** E4

**Historias:** E4.1, E4.2

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-133, T-038

**Archivos:** frontend-web/src/app/(authed)/crm/contacts/page.tsx

**Descripción**

Tabla de contactos con filtros, búsqueda y acciones.

**Especificación**

> • Columnas: nombre, teléfono, email, asignado, tags, último lead, acciones.
>
> • Filtros: asignado, tags (multi-select), do_not_contact.
>
> • Búsqueda por nombre/teléfono/email.
>
> • Botón “nuevo contacto” abre modal o navega a /new.
>
> • Acción quick: ver detalle, crear lead nuevo.

**Criterios done**

> • Listado funcional.

**Tests requeridos**

> • e2e/contacts_list.spec.ts.

**Prompt:** P-10

**T-136 Frontend: detalle/edición de contacto** *\[frontend-page · M\]*

**Épica:** E4

**Historias:** E4.2

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-133, T-038

**Archivos:** frontend-web/src/app/(authed)/crm/contacts/\[id\]/page.tsx

**Descripción**

Página con datos del contacto, sus leads asociados, conversaciones, actividades.

**Especificación**

> • Header: nombre + foto/iniciales + acciones (editar, mergear, archivar, contactar por WhatsApp).
>
> • Tabs: Datos, Leads (lista), Conversaciones (de WhatsApp, link al módulo Communication), Timeline (todas las actividades cronológicas).
>
> • Edición inline para fields rápidos (notes); modal para edición completa.

**Criterios done**

> • Detalle muestra todo el contexto del contacto.

**Tests requeridos**

> • e2e/contact_detail.spec.ts.

**Prompt:** P-10 + P-09

**T-137 Frontend: modal de merge de contactos** *\[frontend-component · M\]*

**Épica:** E4

**Historias:** E4.3

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-132, T-037

**Archivos:** components/domain/ContactMergeModal.tsx

**Descripción**

UI para resolver merge de contactos: dos columnas (primary, secondary), preview del resultado, botón de confirmación.

**Especificación**

> • Dos columnas con datos de ambos contactos resaltando diferencias.
>
> • Tercera columna preview del resultado con field-level toggle (de qué contact tomar cada field).
>
> • Confirmación con texto explícito.
>
> • Aviso: “secondary será archivado y sus leads/conversaciones se moverán a primary”.

**Criterios done**

> • Merge UX claro; manager puede mergear sin confusión.

**Tests requeridos**

> • unit/components/ContactMergeModal.test.tsx + e2e.

**Prompt:** P-08

**T-138 Notificación: contacto asignado al usuario** *\[service · XS\]*

**Épica:** E4

**Historias:** —

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-131, T-035

**Archivos:** modules/crm/event_handlers.py

**Descripción**

Cuando se asigna un contacto a un user, generar notificación in-app.

**Especificación**

> • Hook en update con assigned_user_id que dispara Notification con type='contact_assigned'.

**Criterios done**

> • Asignar contacto genera notificación.

**Tests requeridos**

> • integration/test_contact_assignment_notification.py.

**Prompt:** P-04

**Pipeline y leads**

**T-139 Migration pipeline_stages** *\[migration · S\]*

**Épica:** E4

**Historias:** E4.4

**Spec técnica:** SDD sección 3.6

**Constitución:** Principio 4

**Dependencias:** T-022

**Archivos:** alembic/versions/019_pipeline_stages.py; modules/crm/models.py (PipelineStage)

**Descripción**

Tabla configurable de etapas del pipeline por tenant.

**Especificación**

> • Campos: id, tenant_id, name, slug, position (int), color, is_won (bool), is_lost (bool), is_active, timestamps.
>
> • Constraint: solo una etapa con is_won=true por tenant; solo una con is_lost=true; restantes son intermedias.
>
> • Constraint: al menos 3 etapas activas (no permitir borrar si quedan menos de 3).
>
> • RLS activo.

**Criterios done**

> • Migration aplica.

**Tests requeridos**

> • integration/test_pipeline_stages_migration.py.

**Prompt:** P-01 con table=pipeline_stages

**T-140 Seed default de pipeline al crear tenant** *\[service · XS\]*

**Épica:** E4

**Historias:** E4.4

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-139, T-043

**Archivos:** modules/crm/service.py (seed_default_pipeline)

**Descripción**

Helper que se llama desde la creación de tenant (T-043) para sembrar las etapas default.

**Especificación**

> • Etapas default: 'Nuevo' (1), 'Contactado' (2), 'En negociación' (3), 'Permuta/Test drive' (4), 'Ganado' (5, is_won=true), 'Perdido' (6, is_lost=true).
>
> • Llamar desde T-043 dentro de la transacción atómica.

**Criterios done**

> • Crear tenant deja 6 etapas seed.

**Tests requeridos**

> • integration: cubierto en T-043 test.

**Prompt:** P-04

**T-141 PipelineStage repository + service + endpoints** *\[service · M\]*

**Épica:** E4

**Historias:** E4.4

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-139

**Archivos:** modules/crm/{repository,service,routes}.py (pipeline)

**Descripción**

Gestión completa del catálogo de etapas: lista, crear, renombrar, reordenar, archivar.

**Especificación**

> • GET /api/v1/pipeline/stages.
>
> • POST /api/v1/pipeline/stages (manager).
>
> • PATCH /api/v1/pipeline/stages/{id} (renombrar, color).
>
> • POST /api/v1/pipeline/stages/reorder body: {ordered_ids}.
>
> • POST /api/v1/pipeline/stages/{id}/archive (no se puede archivar is_won/is_lost).
>
> • Validación: posiciones únicas; constraints declarados en T-139.

**Criterios done**

> • Manager puede personalizar el pipeline.

**Tests requeridos**

> • integration/test_pipeline_stages.py.

**Prompt:** P-03 + P-04 + P-05

**T-142 Frontend: configuración del pipeline** *\[frontend-page · M\]*

**Épica:** E4

**Historias:** E4.4

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-141, T-038

**Archivos:** frontend-web/src/app/(authed)/settings/pipeline/page.tsx

**Descripción**

Editor visual de etapas con drag & drop para reordenamiento, edición inline de nombres y colores.

**Especificación**

> • Columnas en horizontal con cada etapa.
>
> • Drag & drop con dnd-kit; salvado optimista al soltar.
>
> • Click en etapa abre popover de edición (nombre, color).
>
> • Botones para agregar etapa intermedia y archivar etapa.
>
> • Etapas is_won/is_lost marcadas visualmente y no se pueden archivar.

**Criterios done**

> • Manager configura pipeline sin tocar SQL.

**Tests requeridos**

> • e2e/pipeline_settings.spec.ts.

**Prompt:** P-10 + P-08

**T-143 Migration leads + lead_stage_history** *\[migration · M\]*

**Épica:** E4

**Historias:** E4.5

**Spec técnica:** SDD sección 3.6

**Constitución:** Principio 4, 5

**Dependencias:** T-130, T-139, T-071

**Archivos:** alembic/versions/020_leads.py

**Descripción**

Tablas leads (entidad central) y lead_stage_history (auditoría).

**Especificación**

> • leads: id, tenant_id, contact_id (FK), assigned_user_id (FK), branch_id (FK), pipeline_stage_id, vehicle_of_interest_id (FK nullable), source (string), expected_close_date, value_ars, lost_reason_id (nullable), tags text\[\], notes, created_by_user_id, last_activity_at, won_at, lost_at, timestamps, deleted_at.
>
> • lead_stage_history: id, tenant_id, lead_id, from_stage_id, to_stage_id, reason, changed_by, changed_at. Append-only.
>
> • Índices: (tenant_id, pipeline_stage_id, assigned_user_id), (tenant_id, last_activity_at).
>
> • RLS activo en ambas.

**Criterios done**

> • Migration aplica.

**Tests requeridos**

> • integration/test_leads_migration.py.

**Prompt:** P-01 con table=leads + lead_stage_history

**T-144 Migration lead_activities + loss_reasons** *\[migration · S\]*

**Épica:** E4

**Historias:** E4.6, E4.7

**Spec técnica:** SDD sección 3.6

**Constitución:** Principio 4

**Dependencias:** T-143

**Archivos:** alembic/versions/021_activities_loss_reasons.py

**Descripción**

Tablas auxiliares: actividades de leads y motivos de pérdida configurables.

**Especificación**

> • lead_activities: id, tenant_id, lead_id, type (call\|whatsapp\|visit\|test_drive\|email\|note\|other), title, notes, due_at (nullable), completed_at (nullable), created_by, timestamps.
>
> • loss_reasons: id, tenant_id, name, slug, is_active. Catálogo por tenant.
>
> • Seed default loss_reasons: 'Precio', 'Eligió otra marca', 'Compró usado', 'No conseguía financiación', 'Sin respuesta', 'Otra'.
>
> • RLS activo.

**Criterios done**

> • Migration aplica con seed.

**Tests requeridos**

> • integration/test_activities_migration.py.

**Prompt:** P-01 con table=lead_activities + loss_reasons

**T-145 LeadRepository + schemas + filtros** *\[repository · M\]*

**Épica:** E4

**Historias:** E4.5, E4.8

**Spec técnica:** SDD sección 3.6

**Constitución:** Art. 4

**Dependencias:** T-143

**Archivos:** modules/crm/{repository,schemas}.py (sección leads)

**Descripción**

Acceso a datos de leads con filtros ricos.

**Especificación**

> • Filtros: stage, assigned_user, branch, vehicle_of_interest, tags, source, value range, has_no_activity_for_days, idle_days_min/max.
>
> • Schemas: LeadCreate, LeadUpdate, LeadRead (con nested contact + vehicle compactos), LeadListItem, LeadKanbanItem (subset minimal para vista kanban).
>
> • Eager loading de relaciones para evitar N+1.

**Criterios done**

> • Filtros combinados funcionan.

**Tests requeridos**

> • unit/test_lead_repository.py.

**Prompt:** P-02 + P-03

**T-146 LeadService.create con auto-asignación** *\[service · M\]*

**Épica:** E4

**Historias:** E4.5

**Spec técnica:** SDD sección 3.6

**Constitución:** Principio 4, 6

**Dependencias:** T-145, T-016

**Archivos:** modules/crm/service.py (LeadService.create)

**Descripción**

Lógica de creación de lead con resolución de contacto y auto-asignación a vendedor.

**Especificación**

> • Si contact_id no se provee pero hay contact_data, intentar lookup por phone; si no existe, crear.
>
> • Auto-asignación: si no se provee assigned_user_id, aplicar regla del tenant (round-robin por sucursal, o por carga, o vendedor por default).
>
> • Stage inicial = primera etapa del pipeline (position 1).
>
> • Validación: vehicle_of_interest debe pertenecer al tenant y estar available o reserved.
>
> • Publicación de evento lead.created.

**Criterios done**

> • Crear lead sin contact crea contact; auto-asign asigna correctamente.

**Tests requeridos**

> • unit/test_lead_create.py.

**Prompt:** P-04

**T-147 LeadService.transition_stage + history + evento** *\[service · M\]*

**Épica:** E4

**Historias:** E4.5

**Spec técnica:** SDD sección 3.6

**Constitución:** Principio 5, 6

**Dependencias:** T-146

**Archivos:** modules/crm/service.py (extend)

**Descripción**

Mover lead entre etapas con registro en history y eventos.

**Especificación**

> • transition_stage(lead_id, to_stage_id, reason, ctx).
>
> • Validación: stage destino existe y pertenece al tenant; lead no está en ganado/perdido (cerrado).
>
> • Registra entrada en lead_stage_history.
>
> • Si destino is_won: setea won_at; publica lead.won. Si destino is_lost: requiere loss_reason_id; setea lost_at; publica lead.lost.
>
> • En todo caso publica lead.stage_changed.
>
> • Update last_activity_at.

**Criterios done**

> • Mover etapa funciona; ganar/perder dispara eventos correctos.

**Tests requeridos**

> • unit/test_transition_stage.py + matriz de transiciones.

**Prompt:** P-04

**T-148 LeadService.assign + reassign con auditoría** *\[service · S\]*

**Épica:** E4

**Historias:** E4.9

**Spec técnica:** —

**Constitución:** Principio 5

**Dependencias:** T-146

**Archivos:** modules/crm/service.py (extend)

**Descripción**

Asignar/reasignar lead a otro vendedor con notificación.

**Especificación**

> • assign(lead_id, user_id, reason, ctx).
>
> • Validación: user pertenece al tenant; permisos del que reasigna (manager o el propio asignado para liberarlo).
>
> • Audit log obligatorio.
>
> • Notificación al nuevo asignado.
>
> • Evento lead.assigned.

**Criterios done**

> • Asignar funciona; notificación llega.

**Tests requeridos**

> • unit/test_lead_assign.py.

**Prompt:** P-04

**T-149 LeadActivityService completo** *\[service · M\]*

**Épica:** E4

**Historias:** E4.6

**Spec técnica:** SDD sección 3.6

**Constitución:** —

**Dependencias:** T-144

**Archivos:** modules/crm/activity_service.py

**Descripción**

CRUD de actividades con notificaciones y update de last_activity_at.

**Especificación**

> • create: crea actividad; si due_at en futuro, programa notificación; actualiza lead.last_activity_at = now si type != 'note' (las notas no cuentan como contacto).
>
> • complete(activity_id, notes): marca completed_at, actualiza lead.last_activity_at, publica activity.completed.
>
> • list(lead_id) con filtros por type, completada/pending.
>
> • Validación: due_at no puede ser pasado al crear.

**Criterios done**

> • Crear actividad y completarla funciona; last_activity_at se actualiza.

**Tests requeridos**

> • unit/test_activity_service.py.

**Prompt:** P-04

**T-150 LeadService.close_won y close_lost** *\[service · S\]*

**Épica:** E4

**Historias:** E4.5

**Spec técnica:** —

**Constitución:** Principio 5

**Dependencias:** T-147

**Archivos:** modules/crm/service.py (extend)

**Descripción**

Métodos específicos de cierre con sus reglas de negocio.

**Especificación**

> • close_won(lead_id, vehicle_id, sale_value, ctx): mueve a stage is_won; setea vehicle_of_interest si no estaba; publica lead.won con sale_value.
>
> • close_lost(lead_id, loss_reason_id, notes, ctx): mueve a stage is_lost; obligatorio loss_reason_id; publica lead.lost.
>
> • Si lead.won: el vehicle asociado puede transicionar automáticamente a sold (handler en T-161).

**Criterios done**

> • Ambos cierres funcionan.

**Tests requeridos**

> • unit/test_close_lead.py.

**Prompt:** P-04

**T-151 Endpoints leads (CRUD + transiciones)** *\[endpoint · M\]*

**Épica:** E4

**Historias:** E4.5, E4.8, E4.9

**Spec técnica:** SDD sección 4.2.4

**Constitución:** Art. 3

**Dependencias:** T-146, T-147, T-148, T-150

**Archivos:** modules/crm/routes.py (leads)

**Descripción**

Endpoints REST de leads.

**Especificación**

> • GET /api/v1/leads (con filtros), GET /api/v1/leads/{id}, POST, PATCH.
>
> • POST /api/v1/leads/{id}/stage body: {to_stage_id, reason}.
>
> • POST /api/v1/leads/{id}/assign body: {user_id, reason}.
>
> • POST /api/v1/leads/{id}/won body: {vehicle_id, sale_value}.
>
> • POST /api/v1/leads/{id}/lost body: {loss_reason_id, notes}.
>
> • GET /api/v1/leads/{id}/history.
>
> • Roles: manager (todo), salesperson (solo asignados), admin_staff (lectura todo).

**Criterios done**

> • Endpoints funcionan; permisos correctos.

**Tests requeridos**

> • integration/test_leads_routes.py.

**Prompt:** P-05

**T-152 Endpoints activities** *\[endpoint · S\]*

**Épica:** E4

**Historias:** E4.6

**Spec técnica:** SDD sección 4.2.4

**Constitución:** Art. 3

**Dependencias:** T-149

**Archivos:** modules/crm/routes.py (activities)

**Descripción**

Endpoints de actividades de leads.

**Especificación**

> • GET /api/v1/leads/{lead_id}/activities.
>
> • POST /api/v1/leads/{lead_id}/activities.
>
> • PATCH /api/v1/activities/{id} (incluye complete: completed_at).
>
> • DELETE /api/v1/activities/{id} (soft).

**Criterios done**

> • Endpoints funcionan.

**Tests requeridos**

> • integration/test_activities.py.

**Prompt:** P-05

**T-153 Endpoints loss_reasons (catálogo)** *\[endpoint · XS\]*

**Épica:** E4

**Historias:** E4.7

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-144

**Archivos:** modules/crm/routes.py

**Descripción**

CRUD de motivos de pérdida (manager).

**Especificación**

> • GET /api/v1/loss-reasons.
>
> • POST/PATCH/POST archive.
>
> • Manager only para escritura.

**Criterios done**

> • Manager configura motivos.

**Tests requeridos**

> • integration/test_loss_reasons.py.

**Prompt:** P-05

**T-154 Frontend: kanban del pipeline con drag & drop** *\[frontend-page · L\]*

**Épica:** E4

**Historias:** E4.5

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-151, T-038, T-039

**Archivos:** frontend-web/src/app/(authed)/crm/pipeline/page.tsx; components/domain/Kanban\*.tsx

**Descripción**

Vista kanban del pipeline. Es la vista principal del CRM en muchos productos similares.

**Especificación**

> • Columnas por stage con header (nombre + count + suma de value_ars).
>
> • Cards de leads compactas: contact name, vehicle of interest (brand+model), value, asignado, last_activity_at relativo, badges (idle warning si \> 5 días sin actividad).
>
> • Drag & drop entre columnas dispara transition_stage; modal de razón si la transición lo requiere (won/lost).
>
> • Filtros top: assigned_user, branch, source, idle_days. Persistidos en URL.
>
> • Búsqueda global del kanban.
>
> • Click en card abre detalle del lead.
>
> • Optimistic update con rollback en falla.

**Criterios done**

> • Kanban funcional; drag funciona suave; modal de won/lost integra cerrar lead.

**Tests requeridos**

> • e2e/pipeline_kanban.spec.ts.

**Prompt:** P-10 + P-08

**T-155 Frontend: detalle de lead con timeline** *\[frontend-page · L\]*

**Épica:** E4

**Historias:** E4.5, E4.6

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-151, T-152

**Archivos:** frontend-web/src/app/(authed)/crm/leads/\[id\]/page.tsx

**Descripción**

Página de detalle del lead con timeline integrado de actividades, conversaciones y cambios de estado.

**Especificación**

> • Header: contact (con link), vehicle (con link), valor, stage actual, asignado, badges.
>
> • Acciones rápidas: cambiar stage (popover con próximas etapas), reasignar, ganar/perder, contactar (link a WhatsApp).
>
> • Timeline cronológico: activities, conversaciones (vinculadas al lead vía contact), stage changes, notas de sistema.
>
> • Sección de actividades pendientes destacada (próximas due_at).
>
> • Form rápido para agregar activity inline.
>
> • Sidebar derecha: datos del contact, datos del vehicle of interest, notas del lead.

**Criterios done**

> • Detalle muestra todo el contexto necesario para vender.

**Tests requeridos**

> • e2e/lead_detail.spec.ts.

**Prompt:** P-10

**T-156 Frontend: form de actividad** *\[frontend-component · S\]*

**Épica:** E4

**Historias:** E4.6

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-152, T-037

**Archivos:** components/domain/ActivityForm.tsx

**Descripción**

Form para crear/editar actividades; usado en detalle de lead y en agenda.

**Especificación**

> • Type select (call/whatsapp/visit/test_drive/email/note/other).
>
> • Title obligatorio.
>
> • Notas opcionales (markdown light).
>
> • due_at opcional (datepicker + timepicker).
>
> • Completed_at opcional para crear ya completada.
>
> • Validation: due_at no en pasado al crear.

**Criterios done**

> • Form reutilizable con validación.

**Tests requeridos**

> • unit/components/ActivityForm.test.tsx.

**Prompt:** P-09

**T-157 Frontend: listado de leads alternativo a kanban** *\[frontend-page · M\]*

**Épica:** E4

**Historias:** E4.8

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-151, T-038

**Archivos:** frontend-web/src/app/(authed)/crm/leads/page.tsx

**Descripción**

Vista tabla de leads con todos los filtros, alternativa al kanban para análisis.

**Especificación**

> • Tabla con columnas: contact, vehicle, stage, asignado, value, source, days_in_stage, last_activity, acciones.
>
> • Filtros completos: stage, assigned, branch, source, value range, idle days, fechas.
>
> • Sortable columns.
>
> • Bulk actions: reasignar masivamente, archivar masivamente (manager).
>
> • Export a CSV.

**Criterios done**

> • Lista funcional.

**Tests requeridos**

> • e2e/leads_list.spec.ts.

**Prompt:** P-10

**T-158 Frontend: form de creación de lead** *\[frontend-page · M\]*

**Épica:** E4

**Historias:** E4.5

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-151, T-070

**Archivos:** frontend-web/src/app/(authed)/crm/leads/new/page.tsx

**Descripción**

Pantalla de alta de lead con autocomplete de contactos existentes.

**Especificación**

> • Sección 1: Contact (autocomplete por phone/name; si no existe, modal de creación rápida con name+phone+email).
>
> • Sección 2: Vehicle of interest (autocomplete sobre /vehicles/suggest).
>
> • Sección 3: Detalles (source, value, expected_close_date, notas).
>
> • Default: assigned_user_id = user actual; stage = primera etapa.
>
> • Submit crea el lead y navega al detalle.

**Criterios done**

> • Alta funcional con autocomplete fluido.

**Tests requeridos**

> • e2e/lead_create.spec.ts.

**Prompt:** P-09

**T-159 Frontend: agenda diaria de actividades** *\[frontend-page · M\]*

**Épica:** E4

**Historias:** E4.6, E4.10

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-152, T-038

**Archivos:** frontend-web/src/app/(authed)/crm/agenda/page.tsx

**Descripción**

Vista “hoy” del vendedor con sus actividades pendientes ordenadas.

**Especificación**

> • Default: actividades del user actual con due_at hoy, ordenadas por hora.
>
> • Toggle: hoy / esta semana / pendientes vencidas.
>
> • Tarjetas con contact + lead + tipo + hora + acción “completar” inline (con notas opcionales).
>
> • Manager puede ver agenda de otros vendedores (selector).
>
> • Indicador de actividades atrasadas (rojo).

**Criterios done**

> • Agenda funcional; vendedores ven su día claro.

**Tests requeridos**

> • e2e/agenda.spec.ts.

**Prompt:** P-10

**T-160 Tests unitarios e integración del CRM core** *\[test-integration · M\]*

**Épica:** E4

**Historias:** E4.5, E4.6, E4.7, E4.8, E4.9

**Spec técnica:** —

**Constitución:** Art. 2

**Dependencias:** T-151, T-152

**Archivos:** tests/integration/test_crm_core.py

**Descripción**

Suite ampliada que verifica el flujo completo de un lead desde alta hasta cierre.

**Especificación**

> • Crear contact + lead.
>
> • Asignar a vendedor.
>
> • Agregar tres actividades.
>
> • Completarlas.
>
> • Mover entre etapas (varias).
>
> • Ganar el lead con vehículo asociado.
>
> • Verificar que vehículo pasa a sold (T-161).
>
> • Verificar history completo.
>
> • Cross-tenant: no puede leer leads de otro tenant.

**Criterios done**

> • Suite completa pasa.

**Tests requeridos**

> • —

**Prompt:** P-11

**Integraciones internas y dashboard**

**T-161 Consumer lead.won → vehicle.sold automático** *\[event · S\]*

**Épica:** E4

**Historias:** E4.11

**Spec técnica:** —

**Constitución:** Principio 6

**Dependencias:** T-150, T-076

**Archivos:** modules/crm/event_handlers.py (extend)

**Descripción**

Handler que cuando un lead se gana con vehicle asociado, transiciona automáticamente el vehículo a sold.

**Especificación**

> • Suscriptor de lead.won.
>
> • Si payload incluye vehicle_id y el vehículo está en estado available o reserved, llama VehicleService.transition_status(to=sold, reason='lead won').
>
> • Si el vehículo ya está sold (por otro lead), warning log y no acción.
>
> • Notificación al manager.

**Criterios done**

> • Ganar lead con vehículo lo deja vendido en stock.

**Tests requeridos**

> • integration/test_lead_won_to_sold.py.

**Prompt:** P-07

**T-162 Notificación: actividad próxima a vencer** *\[service · S\]*

**Épica:** E4

**Historias:** E4.6

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-149, T-035

**Archivos:** modules/crm/scheduled_tasks.py

**Descripción**

Cron Celery que envía notificación 30 min antes de actividad due_at al vendedor asignado.

**Especificación**

> • Beat cron cada 5 minutos.
>
> • Query: actividades pendientes con due_at en próximos 30 min y sin notificación enviada.
>
> • Crea Notification + email.
>
> • Marca activity como notification_sent_at.

**Criterios done**

> • Notificación llega antes de la actividad.

**Tests requeridos**

> • integration/test_activity_reminder.py.

**Prompt:** P-04

**T-163 Notificación: lead idle (sin actividad)** *\[service · S\]*

**Épica:** E4

**Historias:** E4.10

**Spec técnica:** —

**Constitución:** Principio 6

**Dependencias:** T-145, T-035

**Archivos:** modules/crm/scheduled_tasks.py (extend)

**Descripción**

Cron diario que detecta leads sin actividad por X días y notifica al asignado y/o manager.

**Especificación**

> • Cron diario a hora configurable por tenant (default 9:00 hora local).
>
> • Threshold default 5 días sin activity.completed_at; configurable por tenant.
>
> • Excluir leads en stages cerrados (won/lost) y archived.
>
> • Notificación al assigned_user con lista de sus leads idle.
>
> • Notificación resumen al manager con tabla de idle leads por vendedor.

**Criterios done**

> • Cron envía notificaciones esperadas en escenarios sintéticos.

**Tests requeridos**

> • integration/test_idle_leads.py.

**Prompt:** P-04

**T-164 Métricas: pipeline summary por vendedor** *\[service · M\]*

**Épica:** E4

**Historias:** E4.12

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-145

**Archivos:** modules/crm/analytics_service.py

**Descripción**

Service que calcula KPIs del pipeline para mostrar en dashboard.

**Especificación**

> • pipeline_summary(filters): para cada stage, cuenta de leads + suma de value_ars.
>
> • by_user(filters): por usuario, cuenta de leads activos, ganados últimos 30 días, perdidos, conversion rate.
>
> • by_source(filters): leads por fuente y conversión.
>
> • leads_idle(filters): conteo y lista por threshold.
>
> • Filtros comunes: branch, fecha, source.
>
> • Cache TTL 5 minutos para queries pesadas.

**Criterios done**

> • Cálculos correctos verificables con dataset fijo.

**Tests requeridos**

> • unit/test_analytics_service.py.

**Prompt:** P-04

**T-165 Endpoints de dashboard CRM** *\[endpoint · S\]*

**Épica:** E4

**Historias:** E4.12

**Spec técnica:** —

**Constitución:** Art. 3

**Dependencias:** T-164

**Archivos:** modules/crm/routes.py (dashboard)

**Descripción**

Endpoints para alimentar widgets del dashboard.

**Especificación**

> • GET /api/v1/crm/dashboard/pipeline-summary.
>
> • GET /api/v1/crm/dashboard/by-user.
>
> • GET /api/v1/crm/dashboard/by-source.
>
> • GET /api/v1/crm/dashboard/idle-leads.
>
> • Manager y admin_staff ven todo; salesperson ve solo su data.

**Criterios done**

> • Endpoints devuelven KPIs correctos.

**Tests requeridos**

> • integration/test_dashboard_crm.py.

**Prompt:** P-05

**T-166 Frontend: dashboard CRM con widgets** *\[frontend-page · L\]*

**Épica:** E4

**Historias:** E4.12

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-165, T-038

**Archivos:** frontend-web/src/app/(authed)/dashboard/page.tsx (extend); components/dashboard/\*

**Descripción**

Refactor del dashboard placeholder de la Ola 0 (T-042) ahora con widgets reales.

**Especificación**

> • Widget Pipeline Summary: barras horizontales por stage con count + value.
>
> • Widget Conversion Rate (últimos 30 días).
>
> • Widget Top Vendedores (manager).
>
> • Widget Idle Leads (alerta).
>
> • Widget Próximas Actividades (mías).
>
> • Date range picker arriba (default últimos 30 días).
>
> • Filtro de sucursal para manager.

**Criterios done**

> • Dashboard muestra KPIs realistas con datos seed.

**Tests requeridos**

> • e2e/dashboard_crm.spec.ts.

**Prompt:** P-10

**T-167 Vincular conversación de WhatsApp a lead automáticamente** *\[event · M\]*

**Épica:** E4

**Historias:** E4.13

**Spec técnica:** —

**Constitución:** Principio 6

**Dependencias:** T-146, T-176 (WhatsApp recepción - declarado como dependencia anticipada de E5)

**Archivos:** modules/crm/event_handlers.py (extend)

**Descripción**

Handler que cuando llega un mensaje de WhatsApp con contact existente, vincula la conversación a un lead activo si lo hay.

**Especificación**

> • Suscriptor de message.received del módulo Communication.
>
> • Lookup de contact por phone normalizado.
>
> • Si existe contact y tiene lead activo (no cerrado): vincular conversation a lead.
>
> • Si existe contact pero sin lead activo: opcional crear lead automático con stage=Nuevo (configurable).
>
> • Si no existe contact: crear contact y lead automático.
>
> • Notificación al assigned_user.

**Criterios done**

> • Mensaje entrante de un contacto conocido aparece en su lead.

**Tests requeridos**

> • integration/test_whatsapp_lead_link.py (mockeando E5).

**Prompt:** P-07

**T-168 Tests E2E del flujo completo CRM** *\[test-e2e · M\]*

**Épica:** E4

**Historias:** E4.5, E4.6, E4.11

**Spec técnica:** —

**Constitución:** Art. 2

**Dependencias:** T-154, T-155, T-159, T-161

**Archivos:** frontend-web/tests/e2e/crm_full_flow.spec.ts

**Descripción**

E2E del ciclo completo de venta.

**Especificación**

> • Login como salesperson.
>
> • Crear contact + lead con vehicle of interest.
>
> • Agendar 2 actividades.
>
> • Completarlas.
>
> • Mover entre 3 etapas.
>
> • Cerrar como won con vehicle.
>
> • Verificar que vehicle aparece sold en stock.
>
> • Verificar history y timeline completos.

**Criterios done**

> • Test pasa en CI.

**Tests requeridos**

> • —

**Prompt:** P-12

**T-169 Tests de aislamiento multi-tenant en CRM** *\[test-integration · S\]*

**Épica:** E4

**Historias:** —

**Spec técnica:** SDD sección 8.2

**Constitución:** Principio 4

**Dependencias:** T-151, T-152

**Archivos:** tests/integration/test_crm_isolation.py

**Descripción**

Verificación específica de que el CRM respeta aislamiento entre tenants.

**Especificación**

> • Setup: dos tenants con leads, contacts, activities.
>
> • Tests: lookup de contact por phone solo encuentra dentro del tenant; lead detail de otro tenant retorna 404; merge cross-tenant rechazado; transition_stage con stage de otro tenant retorna 422.

**Criterios done**

> • Suite pasa.

**Tests requeridos**

> • —

**Prompt:** P-11

**6.2.5 E5 — WhatsApp básico**

Cubre la integración con WhatsApp Cloud API: alta del canal, recepción y envío de mensajes, gestión de plantillas, vinculación con contactos y leads. Los chatbots conversacionales avanzados y la calificación automática con IA están fuera del alcance del MVP.

**T-170 Migration whatsapp_channels** *\[migration · S\]*

**Épica:** E5

**Historias:** E5.1

**Spec técnica:** SDD sección 3.7

**Constitución:** Principio 4, Art. 3

**Dependencias:** T-022, T-126

**Archivos:** alembic/versions/022_whatsapp_channels.py; modules/communication/models.py

**Descripción**

Tabla que registra el canal de WhatsApp asociado al tenant.

**Especificación**

> • Campos: id, tenant_id, phone_number_id (META), display_phone_number, business_account_id, access_token (encrypted), webhook_verify_token (encrypted), status (active\|paused\|disconnected), last_health_check_at, timestamps.
>
> • Una sola fila activa por tenant en MVP.
>
> • RLS activo.

**Criterios done**

> • Migration aplica.

**Tests requeridos**

> • integration/test_whatsapp_channels_migration.py.

**Prompt:** P-01 con table=whatsapp_channels

**T-171 Migration conversations + messages** *\[migration · M\]*

**Épica:** E5

**Historias:** E5.2, E5.3

**Spec técnica:** SDD sección 3.7

**Constitución:** Principio 4, 5

**Dependencias:** T-130, T-170

**Archivos:** alembic/versions/023_conversations_messages.py

**Descripción**

Tablas centrales del módulo Communication.

**Especificación**

> • conversations: id, tenant_id, channel_id (FK whatsapp_channels), contact_id (FK), lead_id (nullable FK leads), assigned_user_id, status (open\|closed), last_message_at, unread_count, timestamps. UNIQUE (tenant_id, channel_id, contact_id) WHERE status='open'.
>
> • messages: id, tenant_id, conversation_id, direction (in\|out), wa_message_id (UNIQUE), type (text\|template\|image\|audio\|document\|location), content jsonb, sent_by_user_id (nullable, NULL para entrantes y para outbound automáticos), status (queued\|sent\|delivered\|read\|failed), error_code (nullable), occurred_at, timestamps.
>
> • Particionar messages por mes en occurred_at (volumen alto esperado).
>
> • Índices: (conversation_id, occurred_at), (tenant_id, status, occurred_at).
>
> • RLS activo.

**Criterios done**

> • Migration aplica con particionamiento.

**Tests requeridos**

> • integration/test_messages_migration.py.

**Prompt:** P-01 con table=conversations + messages

**T-172 Migration whatsapp_templates** *\[migration · S\]*

**Épica:** E5

**Historias:** E5.4

**Spec técnica:** SDD sección 3.7

**Constitución:** Principio 4

**Dependencias:** T-170

**Archivos:** alembic/versions/024_whatsapp_templates.py

**Descripción**

Catálogo de templates aprobadas por Meta para envío de mensajes salientes fuera de ventana de 24h.

**Especificación**

> • Campos: id, tenant_id, channel_id, meta_template_name, language, category, status (pending\|approved\|rejected), components jsonb (estructura aprobada por Meta), variables_count, last_synced_at, timestamps.
>
> • UNIQUE (channel_id, meta_template_name, language).
>
> • RLS activo.

**Criterios done**

> • Migration aplica.

**Tests requeridos**

> • integration/test_templates_migration.py.

**Prompt:** P-01 con table=whatsapp_templates

**T-173 WhatsAppCloudAdapter (cliente Meta API)** *\[infra · L\]*

**Épica:** E5

**Historias:** E5.2, E5.3, E5.4

**Spec técnica:** SDD sección 3.7

**Constitución:** Art. 3, 6

**Dependencias:** T-170

**Archivos:** modules/communication/adapters/whatsapp_cloud_adapter.py

**Descripción**

Cliente HTTP contra Meta Cloud API con autenticación, rate limiting, manejo de errores tipados.

**Especificación**

> • httpx async client con timeout, retry con backoff.
>
> • Auth: Bearer access_token (descifrado del channel).
>
> • Métodos: send_text, send_template, send_media, mark_as_read, get_template_status, list_templates, submit_template.
>
> • Rate limiting: aplicar el rate limit de Meta (250 mensajes/segundo por número aprobado por defecto); leaky bucket en Redis.
>
> • Errores: mapeo a excepciones tipadas (WhatsAppRateLimitError, WhatsAppTemplateRejectedError, WhatsAppOutsideWindowError, etc.).
>
> • Idempotencia con biz_opaque_callback_data para reconciliación posterior.

**Criterios done**

> • Adapter funciona con sandbox de Meta o mock.

**Tests requeridos**

> • integration/test_whatsapp_adapter.py con respx.

**Prompt:** P-libre

**T-174 ConversationRepository + MessageRepository** *\[repository · M\]*

**Épica:** E5

**Historias:** E5.2, E5.3

**Spec técnica:** SDD sección 3.7

**Constitución:** Art. 4

**Dependencias:** T-171

**Archivos:** modules/communication/repository.py

**Descripción**

Acceso a datos de conversaciones y mensajes con queries optimizadas.

**Especificación**

> • ConversationRepository: list (filtros por status, assigned_user, unread, search), get_or_create_open(channel_id, contact_id).
>
> • MessageRepository: list_by_conversation(cursor pagination), insert, update_status, mark_conversation_read.
>
> • Tenant context implícito.
>
> • Eager loading de contact y last_message para listado.

**Criterios done**

> • Queries eficientes con dataset de prueba.

**Tests requeridos**

> • unit/test_communication_repos.py.

**Prompt:** P-03

**T-175 Schemas conversaciones y mensajes** *\[schema · S\]*

**Épica:** E5

**Historias:** E5.2, E5.3

**Spec técnica:** —

**Constitución:** Art. 1

**Dependencias:** T-171

**Archivos:** modules/communication/schemas.py

**Descripción**

Pydantic schemas para todas las variantes.

**Especificación**

> • ConversationListItem, ConversationRead, ConversationFilters.
>
> • MessageRead.
>
> • OutboundMessageRequest: {type, content, template_name (si type=template), variables}.
>
> • Validators por type: text requiere body; template requiere template_name + variables que matchean el template.

**Criterios done**

> • Schemas validan correctamente.

**Tests requeridos**

> • unit/test_comm_schemas.py.

**Prompt:** P-02

**T-176 Webhook endpoint para recibir mensajes y status updates** *\[endpoint · L\]*

**Épica:** E5

**Historias:** E5.2

**Spec técnica:** SDD sección 3.7, 8.6

**Constitución:** Art. 3 (HMAC verification)

**Dependencias:** T-170, T-174

**Archivos:** modules/communication/webhooks.py

**Descripción**

Endpoint que recibe webhooks de Meta para mensajes entrantes y actualizaciones de status. Verificación HMAC obligatoria.

**Especificación**

> • GET /webhooks/whatsapp para verificación inicial (devuelve hub.challenge si verify_token coincide).
>
> • POST /webhooks/whatsapp para recepción.
>
> • Verificación HMAC SHA256 con app_secret de Meta. Falla → 401.
>
> • Resolución del tenant: del phone_number_id en payload buscar el channel y por ende el tenant; setear tenant context.
>
> • Procesamiento async via Celery: recibir, validar, encolar, responder 200 \< 300ms.
>
> • Soporta tipos de mensaje: text, image, audio, document, location.
>
> • Soporta status updates: sent, delivered, read, failed.
>
> • Idempotencia: si wa_message_id ya existe, ack y skip.

**Criterios done**

> • Webhook procesa mensajes entrantes en sandbox de Meta; HMAC verificado.

**Tests requeridos**

> • integration/test_whatsapp_webhook.py con payloads reales de Meta.

**Prompt:** P-libre

**T-177 ConversationService.upsert_from_webhook** *\[service · M\]*

**Épica:** E5

**Historias:** E5.2

**Spec técnica:** SDD sección 3.7

**Constitución:** Principio 6

**Dependencias:** T-176, T-131

**Archivos:** modules/communication/service.py

**Descripción**

Service que toma un mensaje entrante del webhook y lo persiste, creando contact y conversation si necesario.

**Especificación**

> • Lookup contact por phone normalizado; si no existe, crear con name='WhatsApp \<phone\>' (mejora posterior con perfil de WhatsApp).
>
> • Lookup conversation abierta para (channel, contact); si no existe, crear.
>
> • Crear message con direction=in, status=delivered (en webhooks ya viene confirmado).
>
> • Update conversation.last_message_at y unread_count++.
>
> • Publicar evento message.received para que el CRM enganche (T-167).

**Criterios done**

> • Mensaje entrante deja contact, conversation y message correctos.

**Tests requeridos**

> • integration/test_inbound_message.py.

**Prompt:** P-04

**T-178 MessageService.send (saliente)** *\[service · L\]*

**Épica:** E5

**Historias:** E5.3, E5.4

**Spec técnica:** SDD sección 3.7

**Constitución:** Principio 6

**Dependencias:** T-173, T-174

**Archivos:** modules/communication/service.py (extend)

**Descripción**

Service que envía mensaje saliente, con manejo de la ventana de 24h y templates.

**Especificación**

> • send_message(conversation_id, payload, ctx).
>
> • Validación: si la última mensaje entrante fue hace \> 24h, solo se permiten templates aprobadas (regla de Meta).
>
> • Si type=text: enviar via adapter.send_text.
>
> • Si type=template: validar template aprobada y variables; enviar via adapter.send_template.
>
> • Si type=image/audio/document: subir a storage primero (si es local file), enviar URL.
>
> • Persistir message con status=queued; al recibir confirmación de Meta (sync response o async webhook), update a sent.
>
> • Errores: rate limit → encolar reintento; template rejected → DomainError; outside_window con type!=template → DomainError 'use_template'.

**Criterios done**

> • Envío de texto en ventana funciona; envío de template fuera de ventana funciona; texto fuera de ventana es rechazado con guía.

**Tests requeridos**

> • unit/test_message_send.py + integration.

**Prompt:** P-04

**T-179 Endpoints de conversaciones y mensajes** *\[endpoint · M\]*

**Épica:** E5

**Historias:** E5.2, E5.3, E5.5

**Spec técnica:** SDD sección 4.2.5

**Constitución:** Art. 3

**Dependencias:** T-174, T-178

**Archivos:** modules/communication/routes.py

**Descripción**

Endpoints REST.

**Especificación**

> • GET /api/v1/conversations (filtros, paginación).
>
> • GET /api/v1/conversations/{id}.
>
> • GET /api/v1/conversations/{id}/messages (cursor pagination, orden cronológico ASC).
>
> • POST /api/v1/conversations/{id}/messages (enviar saliente).
>
> • POST /api/v1/conversations/{id}/assign body: {user_id}.
>
> • POST /api/v1/conversations/{id}/close.
>
> • POST /api/v1/conversations/{id}/read (marca todos los mensajes como leídos, unread_count=0).
>
> • Roles: salesperson (asignadas); manager y admin_staff (todas).

**Criterios done**

> • Endpoints completos.

**Tests requeridos**

> • integration/test_communication_routes.py.

**Prompt:** P-05

**T-180 Endpoints de templates** *\[endpoint · M\]*

**Épica:** E5

**Historias:** E5.4

**Spec técnica:** —

**Constitución:** Art. 3

**Dependencias:** T-172, T-173

**Archivos:** modules/communication/routes.py (templates)

**Descripción**

Gestión de templates de WhatsApp.

**Especificación**

> • GET /api/v1/whatsapp/templates (lista del tenant con filtros por status, idioma).
>
> • POST /api/v1/whatsapp/templates body: estructura WhatsApp + variables → submit a Meta.
>
> • POST /api/v1/whatsapp/templates/sync — re-pull de Meta para refrescar status.
>
> • DELETE /api/v1/whatsapp/templates/{id} — solicitud de eliminación a Meta.
>
> • Roles: manager, admin_staff.

**Criterios done**

> • CRUD de templates funcional contra Meta sandbox.

**Tests requeridos**

> • integration/test_templates_routes.py.

**Prompt:** P-05

**T-181 Configuración del canal de WhatsApp en settings** *\[frontend-page · L\]*

**Épica:** E5

**Historias:** E5.1

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-179, T-126

**Archivos:** frontend-web/src/app/(authed)/settings/integrations/whatsapp/page.tsx

**Descripción**

Pantalla de configuración del canal con OAuth con Meta o paste manual de credenciales.

**Especificación**

> • Estado actual: conectado / desconectado.
>
> • Botón “conectar con WhatsApp” (Meta Embedded Signup en futuro; en MVP paste manual).
>
> • Campos: phone_number_id, business_account_id, access_token, webhook_verify_token.
>
> • Botón “probar conexión” que llama un endpoint de health-check.
>
> • Configuración: webhook URL para que el manager copie a Meta dashboard.
>
> • Pausa/reanuda canal.
>
> • Roles: manager.

**Criterios done**

> • Manager puede conectar canal end-to-end.

**Tests requeridos**

> • e2e/whatsapp_settings.spec.ts.

**Prompt:** P-09 + P-10

**T-182 Frontend: bandeja de conversaciones (inbox)** *\[frontend-page · L\]*

**Épica:** E5

**Historias:** E5.2

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-179, T-038

**Archivos:** frontend-web/src/app/(authed)/communications/page.tsx; components/domain/ConversationList.tsx

**Descripción**

Lista de conversaciones con preview, similar a interfaz de email/messenger.

**Especificación**

> • Layout: lista a la izquierda, hilo a la derecha (master-detail).
>
> • Lista: avatar contact + nombre + preview del último mensaje + timestamp + badge unread.
>
> • Filtros: status (open/closed), unread only, assigned to me, all.
>
> • Búsqueda por nombre/teléfono.
>
> • Refetch cada 10 segundos para mensajes nuevos (mejora con SSE en T-186).
>
> • Click selecciona conversation; muestra hilo a la derecha.

**Criterios done**

> • Inbox funcional.

**Tests requeridos**

> • e2e/inbox.spec.ts.

**Prompt:** P-10

**T-183 Frontend: hilo de conversación con composer** *\[frontend-component · L\]*

**Épica:** E5

**Historias:** E5.2, E5.3

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-179, T-180, T-037

**Archivos:** components/domain/ConversationThread.tsx; ConversationComposer.tsx

**Descripción**

Vista del hilo con mensajes y composer abajo, similar a apps de mensajería.

**Especificación**

> • Mensajes con bubbles según direction; status indicator (sent ✓, delivered ✓✓, read ✓✓ azul).
>
> • Auto-scroll al último mensaje al cargar y al recibir nuevo.
>
> • Cargar más al scroll arriba (cursor pagination).
>
> • Header con contact info, lead asociado (link), botón asignar/cerrar.
>
> • Composer: textarea + botón adjuntar (imagen/documento) + botón template + send.
>
> • Si fuera de ventana 24h, composer muestra mensaje y solo permite templates.
>
> • Selector de template con preview de variables a completar.
>
> • Markdown light en texto.

**Criterios done**

> • Hilo funcional; envío de texto y template funciona.

**Tests requeridos**

> • e2e/conversation_thread.spec.ts + unit.

**Prompt:** P-08

**T-184 Frontend: gestión de templates en settings** *\[frontend-page · M\]*

**Épica:** E5

**Historias:** E5.4

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-180, T-038

**Archivos:** frontend-web/src/app/(authed)/settings/whatsapp-templates/page.tsx

**Descripción**

Lista de templates aprobadas + form de submit nuevas a Meta.

**Especificación**

> • Lista con status badges, lenguaje, cuerpo preview.
>
> • Form de creación: nombre, idioma, categoría, body con placeholders {{1}}, {{2}}, etc., header opcional, footer opcional.
>
> • Preview en tiempo real con valores de ejemplo.
>
> • Submit dispara solicitud a Meta; status=pending hasta aprobación.
>
> • Botón sync para refrescar status.

**Criterios done**

> • Manager submitea template y la ve aprobada/rechazada.

**Tests requeridos**

> • e2e/templates.spec.ts.

**Prompt:** P-09 + P-10

**T-185 Frontend: enviar WhatsApp desde detalle de lead/contact** *\[frontend-component · S\]*

**Épica:** E5

**Historias:** E5.6

**Spec técnica:** —

**Constitución:** Principio 2

**Dependencias:** T-183

**Archivos:** components/domain/SendWhatsAppButton.tsx

**Descripción**

Botón “enviar WhatsApp” en detalle de lead o contact que abre o crea conversation y navega al hilo con el composer enfocado.

**Especificación**

> • Si conversation abierta existe → navegar a ella.
>
> • Si no existe → crear con conversation_id implícito y enviar template inicial (selección de template aprobada).
>
> • Tras enviar, navegar al hilo.

**Criterios done**

> • Botón funciona desde lead detail y contact detail.

**Tests requeridos**

> • unit/components/SendWhatsAppButton.test.tsx.

**Prompt:** P-08

**T-186 SSE para mensajes en tiempo real** *\[infra · M\]*

**Épica:** E5

**Historias:** E5.2

**Spec técnica:** —

**Constitución:** Art. 4

**Dependencias:** T-179

**Archivos:** modules/communication/sse.py; frontend-web/src/hooks/useConversationStream.ts

**Descripción**

Endpoint SSE que pushea eventos de nuevos mensajes/cambios de status a clientes conectados, evitando polling.

**Especificación**

> • GET /api/v1/conversations/stream con auth via query param token (SSE no soporta headers fácil; aceptar token corto generado del JWT).
>
> • Backend: conexión a Redis Pub/Sub; suscriptor por tenant_id.
>
> • Eventos: message_received, message_status_changed, conversation_updated.
>
> • Heartbeat cada 30s.
>
> • Hook React useConversationStream que actualiza queryClient cache automáticamente.

**Criterios done**

> • Mensaje recibido aparece en frontend en menos de 1s.

**Tests requeridos**

> • e2e: cubierto en T-188.

**Prompt:** P-libre

**T-187 Auto-respuesta out-of-hours configurable** *\[service · S\]*

**Épica:** E5

**Historias:** E5.7

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-178

**Archivos:** modules/communication/auto_responder.py

**Descripción**

Si llega mensaje fuera del horario comercial del tenant, responder automáticamente con template configurable.

**Especificación**

> • Settings del tenant: out_of_hours_enabled, schedule (días + horas), template_name.
>
> • Hook en message.received: si fuera de horario y no se respondió aún en esta conversation hoy, enviar template.
>
> • Idempotencia: marker en conversation para evitar respuestas duplicadas.

**Criterios done**

> • Mensaje fuera de hora dispara auto-respuesta una vez por día.

**Tests requeridos**

> • integration/test_auto_responder.py.

**Prompt:** P-04

**T-188 Tests E2E del flujo completo de WhatsApp** *\[test-e2e · L\]*

**Épica:** E5

**Historias:** E5.2, E5.3, E5.6

**Spec técnica:** —

**Constitución:** Art. 2

**Dependencias:** T-183, T-185, T-186

**Archivos:** frontend-web/tests/e2e/whatsapp.spec.ts

**Descripción**

E2E con webhook simulado de Meta.

**Especificación**

> • Setup: tenant con canal mockeado, contact con phone, lead asignado.
>
> • Simular mensaje entrante via webhook.
>
> • Verificar conversation aparece en bandeja en tiempo real (SSE).
>
> • Abrir hilo, verificar mensaje.
>
> • Responder con texto.
>
> • Verificar status en hilo (sent → delivered → read en mocks).
>
> • Cerrar conversation.
>
> • Verificar que conversation aparece como vinculada al lead correcto.

**Criterios done**

> • Test pasa.

**Tests requeridos**

> • —

**Prompt:** P-12

**T-189 Cron de limpieza y archivado de conversaciones** *\[service · S\]*

**Épica:** E5

**Historias:** E5.8

**Spec técnica:** —

**Constitución:** Principio 6

**Dependencias:** T-174

**Archivos:** modules/communication/scheduled_tasks.py

**Descripción**

Mantenimiento operativo del módulo.

**Especificación**

> • Cron diario.
>
> • Conversations sin actividad \> 30 días pasan a status=closed automáticamente.
>
> • Mensajes con status=queued \> 1 hora se reintentan o marcan failed.
>
> • Particiones futuras de messages se crean con 1 mes de anticipación.

**Criterios done**

> • Cron ejecuta y aplica acciones esperadas.

**Tests requeridos**

> • integration/test_communication_cron.py.

**Prompt:** P-04

**T-190 Métricas y dashboard de WhatsApp** *\[infra · S\]*

**Épica:** E5

**Historias:** E5.9

**Spec técnica:** —

**Constitución:** Principio 6

**Dependencias:** T-178

**Archivos:** modules/communication/metrics.py; infra/observability/grafana/dashboards/whatsapp.json

**Descripción**

Dashboard operativo del canal.

**Especificación**

> • Métricas: messages_inbound_total, messages_outbound_total{type, status}, message_send_latency, webhook_processing_duration, queue_lag.
>
> • Dashboard Grafana con throughput, error rate, latencias, top conversations activas.
>
> • Alertas: error rate de envío \> 5% en 30min; webhook processing p95 \> 1s.

**Criterios done**

> • Dashboard accesible con métricas reales.

**Tests requeridos**

> • —

**Prompt:** P-libre

**T-191 Tests críticos: unicidad de conversación abierta** *\[test-integration · S\]*

**Épica:** E5

**Historias:** E5.2

**Spec técnica:** —

**Constitución:** Principio 6

**Dependencias:** T-177

**Archivos:** tests/integration/test_conversation_uniqueness.py

**Descripción**

Verifica que nunca haya dos conversaciones abiertas simultáneas para mismo (channel, contact).

**Especificación**

> • Test: simulación de race condition con dos webhooks simultáneos del mismo contact.
>
> • Verificar que el resultado sea una sola conversation con dos messages.
>
> • Test: cerrar conversation y abrir nueva funciona correctamente.
>
> • Cross-tenant: el mismo phone en dos tenants tiene dos conversations independientes.

**Criterios done**

> • Suite pasa.

**Tests requeridos**

> • —

**Prompt:** P-11

**T-192 Privacy: stripe de PII en logs y retention** *\[infra · S\]*

**Épica:** E5

**Historias:** —

**Spec técnica:** SDD sección 8.7, 8.8

**Constitución:** Art. 3

**Dependencias:** T-178

**Archivos:** modules/communication/privacy.py

**Descripción**

Asegurar que el contenido de mensajes no aparezca en logs y configurar retención.

**Especificación**

> • Logger custom para el módulo que enmascara content de messages a \[REDACTED\].
>
> • Settings: message_retention_days (default 24 meses por SDD); cron mensual que elimina mensajes más antiguos (no contacts ni conversations, solo messages).
>
> • Right to be forgotten: endpoint POST /api/v1/contacts/{id}/forget que elimina mensajes del contact y anonimiza el contact.

**Criterios done**

> • Logs no contienen contenido; retention funciona.

**Tests requeridos**

> • unit/test_privacy.py.

**Prompt:** P-libre

**T-193 Manejo de adjuntos (imagen/audio/documento)** *\[service · M\]*

**Épica:** E5

**Historias:** E5.3

**Spec técnica:** —

**Constitución:** Art. 3

**Dependencias:** T-178, T-034

**Archivos:** modules/communication/media_service.py

**Descripción**

Subida y descarga de adjuntos en mensajes.

**Especificación**

> • Inbound: cuando llega media, descargar de Meta CDN (URLs caducan), guardar en storage interno, persistir reference.
>
> • Outbound: subir a storage interno, obtener URL pública/firmada, enviar a Meta.
>
> • Validación: tamaños y mime types soportados por WhatsApp (audio \< 16MB, imagen \< 5MB, etc.).
>
> • Compresión de imágenes outbound si \> 1MB.

**Criterios done**

> • Adjuntos entrantes y salientes funcionan.

**Tests requeridos**

> • integration/test_media.py.

**Prompt:** P-04

**T-194 Documentación: setup y operación del canal** *\[docs · S\]*

**Épica:** E5

**Historias:** —

**Spec técnica:** —

**Constitución:** —

**Dependencias:** T-181

**Archivos:** docs/integrations/whatsapp-setup.md; docs/runbooks/whatsapp-ops.md

**Descripción**

Documentación para Customer Success y on-call sobre el canal de WhatsApp.

**Especificación**

> • Setup: cómo crear app en Meta, obtener credenciales, configurar webhook.
>
> • Troubleshooting común: token expirado, número no aprobado, templates rechazadas.
>
> • Runbook: qué hacer si rate limit; cómo recuperar mensajes perdidos; cómo migrar canal.

**Criterios done**

> • Docs accesibles.

**Tests requeridos**

> • —

**Prompt:** P-libre

**7. Glosario y trazabilidad**

Esta sección final consolida la trazabilidad del Plan con el resto del cuerpo SDD y resuelve los términos del dominio que se usan a lo largo del documento. Es material de referencia, no se lee linealmente.

**7.1 Trazabilidad tareas ↔ épicas del backlog**

Mapa que permite navegar desde una épica del Backlog de historias hacia las tareas atómicas que la implementan en esta versión del Plan. Las épicas no incluidas en esta versión (E6 a E12) se especificarán en olas posteriores.

|  |  |  |
|:---|:---|:---|
| **Épica** | **Cobertura en MVP** | **Tareas** |
| E1 | Onboarding completo desde creación de tenant hasta dashboard funcional. Self-service signup público postergado. | T-043 a T-062 |
| E2 | Stock completo: catálogos, vehículos, fotos, importación CSV, búsqueda. Pricing IA postergado. | T-063 a T-114 |
| E3 | Publicación al portal deRuedas con manejo de errores y reconciliación. MercadoLibre y Facebook postergados a F2. | T-115 a T-129 |
| E4 | CRM básico: contactos, leads, pipeline configurable, actividades, dashboard. Vinculación con WhatsApp incluida. | T-130 a T-169 |
| E5 | WhatsApp Cloud API: recepción, envío, templates, ventana 24h, vinculación con leads. Chatbots avanzados postergados. | T-170 a T-194 |
| E6 a E12 | Fuera del alcance del MVP. Cubrirán CRM avanzado, multi-canal completo, permutas, financiación, documentación electrónica, contabilidad, BI, mobile. | (olas posteriores del Plan) |

**7.2 Trazabilidad tareas ↔ secciones del SDD**

Las tareas referencian las secciones de la Especificación Técnica de Diseño cuyas decisiones implementan. Esta vista inversa muestra qué secciones del SDD se traducen en código durante esta ola.

|  |  |
|:---|:---|
| **Sección SDD** | **Tareas que la implementan** |
| 2.2 Contenedores | T-002, T-009, T-029 |
| 2.4 Eventos de dominio | T-016, T-119, T-167, T-177 |
| 2.5 Multi-tenancy | T-010, T-027, T-169, T-191 |
| 3.3 Tenants/Users/Branches | T-017 a T-024, T-043 a T-062 |
| 3.4 Stock | T-063 a T-114 |
| 3.5 Publishing | T-115 a T-129 |
| 3.6 CRM | T-130 a T-169 |
| 3.7 Communication | T-170 a T-194 |
| 3.9 Audit y Notifications | T-011, T-014 (audit decorator), T-035 |
| 4.1 Convenciones API | T-012, T-013, T-014, T-015 |
| 4.2 Endpoints | todos los endpoints del Plan |
| 4.3 Eventos | T-016, todos los publishers/consumers |
| 6 NFRs (performance) | T-080, T-098, T-099, T-114, T-186 |
| 7 Estrategia de testing | T-027, T-032, T-033, T-061, T-112, T-125, T-160, T-168, T-169, T-188, T-191 |
| 8.2 Aislamiento multi-tenant | T-027, T-169, T-191 |
| 8.3 Auth | T-013, T-025, T-026, T-040 |
| 8.4 Autorización | T-014, T-079, T-082, T-151, T-179 |
| 8.5 Secretos | T-004, T-126, T-192 |
| 8.6 Webhooks (HMAC) | T-176 |
| 8.7-8.8 Privacy y retention | T-011, T-189, T-192 |
| 9.1 CI/CD | T-003, T-008 |
| 9.5 Observabilidad | T-028 a T-031, T-127, T-190 |
| ADR-002 Migrations | T-007, todas las migrations |
| ADR-004 Frontend | T-006, T-036, T-037, T-038 |
| ADR-005 OpenSearch | T-098, T-099 |
| ADR-006 RLS | T-010, T-027 |
| ADR-007 Auth con Keycloak | T-013, T-025, T-026, T-040 |
| ADR-008 Storage | T-034, T-089 |
| ADR-009 Event bus | T-016 |

<!-- ══════════════ ANOTACIÓN DEL PROYECTO — NO FORMA PARTE DEL DOCUMENTO ORIGINAL ══════════════ -->

> ⚠️ **Anotación editorial (2026-08-13, change `C-01`).** El texto de arriba es el original y **no fue modificado** — `docs/sdd/` es corpus fuente inmutable. Esta nota se agrega para que la corrección sea visible desde acá.
>
> **Dos anclas de este índice apuntan al ADR equivocado.** La numeración canónica es la de `deRuedas-spec-tecnica.md` §1146–1386, que es quien **contiene** los ADRs; este plan solo los referencia. Manda la spec ([`ADR-000`](../adr/ADR-000-precedencia-documental.md), N1 > N2).
>
> | Dice acá | Es en realidad | Corrección |
> |---|---|---|
> | `ADR-002 Migrations` | `ADR-002` es **PostgreSQL** como base principal | Etiqueta equivocada; el mapeo a `T-007` y migraciones se mantiene |
> | `ADR-005 OpenSearch` | `ADR-005` es **React Native con Expo**; OpenSearch es `ADR-011` | `T-098` y `T-099` anclan a **`ADR-011`** |
>
> Alcanza además a los cuerpos de `T-098` (*"SDD ADR-005"*) y `T-099` (*"anchor a ADR-005"*): en ambos, léase **`ADR-011`**.
>
> Este índice es **parcial**: cubre 7 de los 12 ADRs. `ADR-001`, `ADR-003`, `ADR-010`, `ADR-011` y `ADR-012` no se referencian en ninguna parte del plan.
>
> 📄 Inventario completo, evidencia y fundamento: [`ADR-018 — Anclas de ADR del plan de implementación`](../adr/ADR-018-anclas-de-adr-del-plan-de-implementacion.md). Cierra `IN-29` / `PA-14`.

<!-- ══════════════════════════════ FIN DE LA ANOTACIÓN ══════════════════════════════ -->

**7.3 Trazabilidad tareas ↔ Constitución**

Los principios y artículos de la Constitución se aplican transversalmente; algunos se materializan en tareas específicas que actúan como guardarraíl o verificación. La siguiente tabla destaca esas tareas.

|  |  |
|:---|:---|
| **Principio o Artículo** | **Tareas con anclaje fuerte** |
| Principio 1 (claridad antes que cleverness) | T-001, T-004 (settings explícitos), T-076 (state machine declarativa) |
| Principio 2 (simplicidad) | Toda tarea de frontend; T-036 a T-038 (design system) |
| Principio 3 (datos como activo) | T-011 (audit), T-077 (soft delete), T-084 (history), T-132 (merge) |
| Principio 4 (multi-tenancy estricto) | T-010, T-027, T-169, T-191 — verificación obligatoria |
| Principio 5 (auditoría) | T-011, T-014 (decorator), T-084, T-143 (lead history), T-148 |
| Principio 6 (resiliencia) | T-016, T-122 (DLQ), T-128 (reconciliación), T-187 (auto-respuesta) |
| Art. 1 (estructura del repo) | T-001 + todas las que crean archivos respetan T-001 |
| Art. 2 (tests obligatorios) | Todas las tareas con criterio de done que incluya tests |
| Art. 3 (auth y secretos) | T-013, T-014, T-025, T-026, T-126, T-192 |
| Art. 4 (performance) | T-080, T-098, T-114, T-186 |
| Art. 5 (despliegue seguro) | T-008 |
| Art. 6 (operación) | T-028 a T-031, T-127, T-190 |
| Art. 7 (gobernanza) | T-001 (README + links a SDD), T-129, T-194 (runbooks) |

**7.4 Plantillas ↔ tareas que las usan**

Vista útil para evolucionar las plantillas: cuando una plantilla cambia, hay que considerar qué tareas se ven afectadas. Solo se cuentan tareas cuyo prompt es la plantilla misma, no las que la combinan.

|  |  |  |
|:---|:---|:---|
| **Plantilla** | **Tareas (resumen)** | **Total** |
| P-01 create-migration | T-009, T-011, T-017 a T-019, T-022, T-063 a T-065, T-071, T-084, T-088, T-093, T-115, T-130, T-139, T-143, T-144, T-170 a T-172 | ~22 |
| P-02 create-pydantic-schema | T-073, T-131, T-145, T-175 + combinadas | ~5 |
| P-03 create-repository | T-020, T-023, T-067, T-072, T-131, T-141, T-145, T-174 + combinadas | ~10 |
| P-04 create-service-method | T-020, T-023, T-046, T-059, T-074 a T-077, T-089, T-090, T-093, T-094, T-116, T-118, T-128, T-131 a T-134, T-141, T-146 a T-150, T-161 a T-164, T-177, T-178, T-187, T-189, T-193 | ~38 |
| P-05 create-rest-endpoint | T-021, T-024, T-025, T-043 a T-045, T-047, T-068, T-078 a T-083, T-085, T-091, T-092, T-095 a T-097, T-099 a T-100, T-120, T-121, T-133, T-141, T-151 a T-153, T-165, T-179, T-180 | ~38 |
| P-06 publish-domain-event | Combinada en T-074, T-075, T-076 (vehicle events) y T-146, T-147 (lead events) | ~8 implícitas |
| P-07 consume-domain-event | T-119, T-161, T-167 | 3 |
| P-08 create-react-component | T-037, T-038, T-058, T-070, T-102, T-106, T-107, T-110, T-111, T-124, T-137, T-156, T-183, T-185 | ~14 |
| P-09 create-form-component | T-041, T-049 a T-053, T-104, T-105, T-181, T-184, T-185 + combinadas | ~12 |
| P-10 create-list-page | T-042, T-055 a T-057, T-062, T-069, T-101, T-103, T-108, T-109, T-135, T-136, T-142, T-154, T-155, T-157 a T-159, T-166, T-181 a T-184, T-186 + combinadas | ~24 |
| P-11 create-test-suite | T-027, T-160, T-169, T-191 | 4 |
| P-12 create-e2e-test | T-061, T-112, T-125, T-168, T-188 | 5 |

**7.5 Glosario de términos del dominio**

Términos específicos del dominio argentino y del producto que se usan a lo largo del cuerpo SDD.

|  |  |
|:---|:---|
| **Término** | **Definición** |
| Agencia | Cliente del SaaS. Concesionaria, multimarca o usado de vehículos. En el modelo se llama tenant. |
| Tenant | Cliente único del SaaS, equivalente a una agencia. Tiene una o más sucursales y N usuarios. |
| Sucursal (branch) | Punto físico de venta de la agencia. Una agencia tiene al menos una. Se usa para asignación de stock y vendedores, y como filtro analítico. |
| Stock | El conjunto de vehículos en inventario del tenant disponibles para venta. La gestión de stock es el dominio E2 (módulo central). |
| Lead | Persona interesada en comprar un vehículo. Tiene un contact asociado y opcionalmente un vehicle of interest. Avanza por el pipeline hasta ganarse o perderse. |
| Pipeline | Secuencia configurable de etapas (pipeline_stages) por las que pasa un lead desde su creación hasta su cierre. |
| Permuta (trade-in) | Operación de venta donde el comprador entrega un vehículo usado como parte de pago. Dominio postergado a olas posteriores. |
| Dominio (en patente) | Identificador alfanumérico de la patente del vehículo. Formato viejo (XXX 999) o Mercosur (XX 999 XX). |
| Chasis | Identificador único del vehículo (VIN). 17 caracteres alfanuméricos sin I, O, Q. |
| CUIT | Clave Única de Identificación Tributaria (AR). Identificador fiscal de personas jurídicas. 11 dígitos con dígito verificador. |
| DNI | Documento Nacional de Identidad (AR). Identificador de personas físicas. |
| Manager | Rol del usuario administrador de un tenant. Configura agencia, sucursales, usuarios, pipeline, integraciones. |
| Salesperson | Rol del usuario vendedor. Gestiona sus leads asignados y vehículos en su sucursal. |
| Admin staff | Rol del usuario administrativo. Apoya gestión de stock e información sin permisos comerciales. |
| Super admin | Rol global de deRuedas (no del tenant). Accede al backoffice administrativo. Puede crear y suspender tenants. |
| Onboarding | Proceso inicial de setup de un tenant tras su creación: completar datos, agregar sucursales, invitar usuarios, configurar pipeline. |
| Conector / Publisher | Adapter que sincroniza vehículos del stock con un canal externo de publicación (deRuedas portal, MercadoLibre, etc.). |
| Ventana 24h | En WhatsApp Business: período tras el último mensaje entrante del usuario durante el cual se puede responder con cualquier tipo de mensaje. Pasada la ventana, solo se permiten templates aprobadas. |
| Template (WhatsApp) | Mensaje pre-aprobado por Meta para envíos fuera de la ventana 24h. |
| DLQ (dead-letter queue) | Cola de eventos o mensajes que no pudieron procesarse tras agotar reintentos. Requieren intervención manual. |
| RLS (row-level security) | Mecanismo de PostgreSQL que filtra filas según una política configurable. Se usa para garantizar el aislamiento entre tenants. |
| Idempotency-Key | Header HTTP en POSTs que garantiza que reintentos no produzcan operaciones duplicadas. |
| Soft delete | Marcado de fila como eliminada (deleted_at) sin DELETE físico. Preserva trazabilidad. |
| Trace ID | Identificador único de un request que se propaga a logs, métricas y eventos para correlación. |

**7.6 Cierre**

Esta versión del Plan de Implementación cubre la fundación técnica del proyecto y el MVP funcional, con un total de ciento noventa y cuatro tareas atómicas distribuidas en dos olas. Su completitud habilita el lanzamiento controlado del producto a un grupo cerrado de agencias early adopter, según la estrategia declarada en el documento Plan estratégico y SaaS.

Las olas posteriores —que cubren el resto del backlog desde E6 hasta E12— se especificarán como extensiones de este documento una vez que la Ola 1 esté estabilizada en producción y se haya recogido suficiente feedback de uso real para refinar prioridades. La estructura de fichas, plantillas y trazabilidad establecida en estas páginas es la plantilla operativa que se replicará en esas extensiones.

El presente documento, junto con la Constitución, el Plan estratégico, el Backlog de historias y la Especificación Técnica de Diseño, conforma el cuerpo SDD completo de deRuedas Gestión y constituye la base normativa, funcional y operativa sobre la que se ejecuta el desarrollo del producto.
