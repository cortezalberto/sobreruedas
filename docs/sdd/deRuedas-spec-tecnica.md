**Especificación Técnica**

**de Diseño**

***deRuedas Gestión***

Software Design Document — SDD

*Arquitectura, modelo de datos, API, ADRs y estrategias*

Versión 1.0 — Mayo de 2026

**1. Introducción**

**1.1 Propósito**

Este documento es la especificación técnica vinculante del producto deRuedas Gestión. Define cómo se construye técnicamente el sistema descripto funcionalmente en el documento de historias de usuario y estratégicamente en el documento de mejoras y plan SaaS. Su contenido es de aplicación obligatoria para el equipo de ingeniería y para los asistentes de inteligencia artificial que colaboren en el desarrollo.

Es deliberadamente exhaustivo en los aspectos que requieren coordinación entre múltiples desarrolladores y entre módulos: arquitectura, modelo de datos, contratos de API y decisiones arquitectónicas. Es deliberadamente más sintético en los aspectos que se documentan principalmente como código y configuración: detalles de despliegue, runbooks, tests específicos. Esto último vive en el repositorio del proyecto, no acá.

**1.2 Audiencia**

Este documento está escrito para tres audiencias. La primera es el equipo de ingeniería del proyecto, que lo usa como referencia de implementación e insumo de refinement de historias y planning. La segunda es el equipo extendido (producto, customer success, dirección), que lo consulta para entender capacidades y limitaciones. La tercera son los asistentes de IA que colaboran en el desarrollo: el documento se diseña para que ellos también lo lean y se orienten, especialmente las secciones de arquitectura, modelo de datos y ADRs.

**1.3 Documentos relacionados**

- Constitución del proyecto: principios y reglas vinculantes.

- Modelo de Mejoras Estratégicas y Plan SaaS: visión, plan de fases, equipo, presupuesto.

- Backlog de Historias de Usuario: especificación funcional con criterios de aceptación.

- Documentación viva en el repositorio: README, ADRs nuevos posteriores a este documento, runbooks operativos.

**1.4 Convenciones del documento**

Los nombres de tablas, campos, endpoints y módulos aparecen siempre en formato monoespaciado. Las decisiones vinculantes se identifican con la sigla “ADR” y un número correlativo. Los requisitos no funcionales con valor cuantitativo aparecen con números explícitos; cuando un valor depende de calibración futura se indica con “objetivo” y rango. Las palabras “debe”, “debería” y “puede” se usan según convención RFC 2119: “debe” es obligatorio, “debería” es recomendado pero admite excepción justificada, “puede” es opcional.

**2. Arquitectura del sistema**

**2.1 Vista de contexto (C4 nivel 1)**

deRuedas Gestión se inserta en un ecosistema de actores y sistemas externos. Los actores principales son el usuario humano del cliente (gerente, vendedor, administrativo) que interactúa a través de la aplicación web y la aplicación móvil; el equipo interno de deRuedas que opera el sistema mediante el backoffice de administración; y los compradores finales, que interactúan indirectamente vía WhatsApp y formularios en el portal de avisos.

Los sistemas externos integrados son: el portal público de deRuedas para publicación de avisos; MercadoLibre Vehículos para publicación cruzada; WhatsApp Business Cloud API de Meta para mensajería; las APIs de las financieras integradas para precalificación y originación crediticia; servicios de OCR para extracción de texto de documentos; servicios de firma electrónica; Mercado Pago para cobros y suscripciones; y proveedores cloud para infraestructura.

**2.2 Vista de contenedores (C4 nivel 2)**

El sistema se descompone en los siguientes contenedores principales:

|  |  |  |
|:---|:---|:---|
| **Contenedor** | **Tecnología** | **Responsabilidad** |
| Frontend Web | Next.js + React + TypeScript | Aplicación web del cliente. SSR para login y SEO de páginas públicas; SPA para la operación autenticada. Consume la API REST. |
| Frontend Móvil | React Native + Expo | Aplicación nativa iOS y Android. Consume la misma API REST. Notificaciones push, captura desde cámara, biometría. |
| Backoffice deRuedas | Next.js + React + TypeScript | Aplicación web interna para Customer Success y Super Admin. Consume la API administrativa con permisos elevados. |
| API Backend | Python 3.12 + FastAPI | Servicio principal que expone la API REST. Aloja la lógica de negocio organizada en módulos delimitados. |
| Worker asíncrono | Python + Celery | Procesamiento background: integraciones con portales, envío de notificaciones, procesamiento de imágenes y documentos, generación de reportes pesados. |
| Base de datos | PostgreSQL 16 | Persistencia principal. Datos relacionales con extensiones pgcrypto, pg_trgm y PostGIS habilitadas. |
| Cache y broker | Redis 7 | Cache de sesiones y datos calientes; broker de Celery; pub-sub para eventos en tiempo real. |
| Búsqueda | OpenSearch | Índice de búsqueda full-text para catálogo de vehículos, documentos y conversaciones. |
| Object Storage | S3-compatible | Fotografías, documentos, archivos exportados. Servido vía CDN. |
| Servicio de Auth | Keycloak | Identidad, autenticación, OAuth2 y OIDC. Gestión de tokens y refresh. |
| Gateway de eventos | Webhooks + colas | Recepción de eventos externos (mensajes WhatsApp, callbacks de financieras, notificaciones de portales). |
| Observabilidad | Prometheus + Grafana + Loki + Jaeger | Métricas, logs centralizados, tracing distribuido, alertas. |

**2.3 Vista de componentes (C4 nivel 3)**

Dentro del contenedor de API Backend, el código se organiza en módulos delimitados que corresponden a los dominios de negocio. Cada módulo tiene su propia capa de routes (HTTP), services (lógica de negocio), repositories (acceso a datos) y schemas (validación de entrada y salida con Pydantic). Los módulos no se llaman directamente entre sí salvo a través de interfaces explícitas; la comunicación entre módulos preferentemente se realiza mediante eventos de dominio publicados en una cola asincrónica.

Los módulos del backend son:

- auth: identidad, autenticación, autorización, gestión de sesiones.

- tenancy: tenants, sucursales, planes, suscripciones, billing.

- users: usuarios, roles, permisos, asignaciones.

- stock: vehículos, marcas, modelos, fotos, equipamiento, estados, historial.

- publishing: integraciones con portales externos.

- crm: leads, pipeline, etapas, actividades, etiquetas, fuentes.

- communication: conversaciones, mensajes, WhatsApp, templates, chatbot.

- trade-in: solicitudes de permuta, valuaciones, inspecciones.

- finance: financieras, solicitudes de crédito, ofertas, originación.

- documents: documentos, tipos, OCR, firma electrónica.

- accounting: cuenta corriente, cobros, pagos, conciliación.

- operations: operaciones de venta, cierre, costos imputados.

- analytics: dashboards, reportes, agregaciones, exportación.

- notifications: notificaciones in-app, email, push.

- audit: registro de auditoría transversal.

- admin: backoffice de deRuedas, multi-tenant cross queries.

**2.4 Estrategia de comunicación entre módulos**

La comunicación entre módulos sigue tres patrones según la naturaleza del flujo. El primero es la llamada sincrónica directa, utilizada cuando la respuesta del módulo llamado afecta el flujo de la operación que origina la llamada. Por ejemplo, el módulo crm consulta a stock para validar que el vehículo asociado a un lead existe y está disponible. Estas llamadas atraviesan interfaces explícitas y no acceden a las tablas internas del módulo destino.

El segundo patrón es el evento de dominio asincrónico, utilizado cuando un módulo necesita reaccionar a algo que ocurrió en otro pero no es necesario esperar la reacción para continuar. Por ejemplo, cuando se carga un vehículo, se publica un evento vehicle.created al que se suscribe el módulo publishing para iniciar la sincronización con portales externos. Los eventos se publican en Redis Streams y son consumidos por workers Celery.

El tercer patrón es la suscripción a webhooks externos, utilizada para recibir eventos generados por servicios externos que afectan el estado del sistema. WhatsApp envía un webhook cuando llega un mensaje, las financieras envían webhooks cuando cambia el estado de una solicitud, los portales notifican operaciones cerradas. Los webhooks ingresan a un endpoint dedicado, se validan, se persisten en una tabla de eventos entrantes para garantizar idempotencia, y se procesan asincrónicamente.

**2.5 Estrategia de multi-tenancy**

La estrategia de multi-tenancy es la decisión arquitectónica de mayor alcance del sistema y se documenta con detalle adicional en el ADR-006. La síntesis es: se utiliza un modelo de discriminator-column con tenant_id presente en todas las tablas de negocio, complementado con Row-Level Security (RLS) de PostgreSQL como capa de defensa en profundidad.

La sesión autenticada del usuario establece el tenant_id como variable de sesión PostgreSQL al inicio de cada conexión mediante SET LOCAL app.current_tenant. Las políticas de RLS aplicadas a cada tabla restringen automáticamente el acceso a las filas cuyo tenant_id coincide con el de la sesión. Adicionalmente, todas las queries del código aplicación incluyen explícitamente la condición tenant_id como filtro, generando defensa redundante. El sistema rechaza el inicio de cualquier consulta donde la variable de sesión no esté establecida.

Las tablas de catálogo (marcas y modelos canónicos, tipos de documentos canónicos, etc.) viven en un schema compartido y son de solo lectura para los tenants. Las tablas administrativas (gestión de tenants, planes, billing) viven en un schema separado con permisos exclusivos del rol Super Admin.

**3. Modelo de datos**

**3.1 Convenciones generales**

El modelo de datos sigue las convenciones siguientes, que aplican a toda tabla del sistema salvo excepción justificada documentada como ADR.

- Los identificadores primarios son UUID versión 7 (ordenables temporalmente), almacenados como uuid nativo de PostgreSQL.

- Los nombres de tablas son plurales en inglés en snake_case. Excepción: entidades específicas del dominio argentino sin traducción razonable mantienen el término en español (por ejemplo, sucursales, permutas).

- Los nombres de columnas son singulares en inglés en snake_case. Las foreign keys siguen el patrón nombre_singular_id.

- Toda tabla de negocio tiene tenant_id NOT NULL como FK a tenants(id), formando parte de los índices más usados.

- Toda tabla tiene created_at, updated_at, ambos timestamp with time zone NOT NULL DEFAULT now(), y deleted_at timestamp with time zone NULL para soft-delete.

- Los enums de dominio se modelan como tipos PostgreSQL CREATE TYPE ... AS ENUM cuando los valores son cerrados y estables; en caso contrario, como tabla de catálogo referenciada por FK.

- Los valores monetarios se almacenan en numeric(18,2) con la moneda como columna asociada (ARS, USD).

- Las fechas sin componente horario se almacenan en date; los timestamps incluyen siempre time zone.

**3.2 Diagrama de dominios**

El modelo de datos se organiza en diez dominios delimitados que corresponden a los módulos del backend. Las relaciones cruzadas entre dominios se hacen siempre por identificador, nunca por inclusión de tablas. Los dominios son: Auth y Tenancy, Stock, CRM, Communication, Trade-in (permutas), Finance, Documents, Accounting, Operations y Audit.

**3.3 Dominio Auth y Tenancy**

Este dominio modela las cuentas de cliente (tenants), sus sucursales, los planes de suscripción, los usuarios humanos y los roles. Es la base sobre la que se construye toda la lógica multi-tenant del sistema.

Tabla: **tenants**

*Una agencia cliente del SaaS. Unidad raíz de aislamiento de datos.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK | Identificador único persistente. |
| **name** | varchar(120) | NOT NULL | Razón social o nombre comercial. |
| **slug** | varchar(60) | UNIQUE NOT NULL | Identificador URL-friendly único global. |
| **cuit** | varchar(13) | UNIQUE NOT NULL | CUIT con guiones, validado por dígito verificador. |
| **billing_email** | varchar(254) | NOT NULL | Email para facturación y notificaciones administrativas. |
| **status** | tenant_status_enum | NOT NULL | active \| suspended \| trial \| cancelled. |
| **plan_id** | uuid | FK plans(id) | Plan vigente. |
| **trial_ends_at** | timestamptz | NULL | Fecha de fin de trial si aplica. |
| **timezone** | varchar(50) | DEFAULT 'America/Argentina/Buenos_Aires' | Zona horaria del tenant. |
| **locale** | varchar(10) | DEFAULT 'es-AR' | Idioma por defecto. |
| **settings** | jsonb | DEFAULT '{}' | Configuración específica del tenant (logo, colores, preferencias). |
| **created_at** | timestamptz | NOT NULL |  |
| **updated_at** | timestamptz | NOT NULL |  |
| **deleted_at** | timestamptz | NULL | Soft delete para cancelaciones recuperables. |

Tabla: **branches**

*Sucursales del tenant. Las agencias mono-sucursal tienen una sola entrada.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **name** | varchar(120) | NOT NULL | Nombre interno (Casa Central, Sucursal Mendoza). |
| **address** | varchar(255) | NULL | Dirección física. |
| **city** | varchar(120) | NOT NULL |  |
| **province** | varchar(120) | NOT NULL | Provincia. |
| **phone** | varchar(40) | NULL |  |
| **business_hours** | jsonb | NULL | Horarios de atención por día. |
| **geo_point** | geography(Point,4326) | NULL | Coordenadas para mapas. PostGIS. |
| **is_active** | boolean | DEFAULT true |  |
| **created_at** | timestamptz |  |  |
| **updated_at** | timestamptz |  |  |

Tabla: **plans**

*Catálogo de planes comerciales del SaaS. Tabla compartida cross-tenant.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **code** | varchar(40) | UNIQUE NOT NULL | Identificador estable (starter, pro, enterprise). |
| **name** | varchar(120) | NOT NULL | Nombre comercial visible. |
| **price_ars** | numeric(18,2) | NOT NULL | Precio mensual en pesos argentinos. |
| **max_users** | integer | NOT NULL | Límite de usuarios. 0 = ilimitado. |
| **max_vehicles** | integer | NOT NULL | Límite de vehículos en stock simultáneo. |
| **max_branches** | integer | NOT NULL | Límite de sucursales. |
| **modules** | jsonb | NOT NULL | Módulos habilitados. Array de strings. |
| **is_active** | boolean | DEFAULT true |  |
| **created_at** | timestamptz |  |  |

Tabla: **users**

*Usuarios humanos del sistema. Cada uno pertenece a exactamente un tenant.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **email** | varchar(254) | NOT NULL | Email único dentro del tenant. |
| **password_hash** | varchar(255) | NOT NULL | Hash argon2id. Nunca se loguea ni serializa. |
| **full_name** | varchar(180) | NOT NULL |  |
| **phone** | varchar(40) | NULL |  |
| **role** | user_role_enum | NOT NULL | manager \| salesperson \| admin_staff. |
| **status** | user_status_enum | NOT NULL | active \| inactive \| invited \| suspended. |
| **last_login_at** | timestamptz | NULL |  |
| **mfa_enabled** | boolean | DEFAULT false |  |
| **mfa_secret** | varchar(255) | NULL | Cifrado simétricamente con KMS. |
| **created_at** | timestamptz |  |  |
| **updated_at** | timestamptz |  |  |
| **deleted_at** | timestamptz | NULL |  |

Índices: UNIQUE (tenant_id, lower(email)) garantiza unicidad case-insensitive dentro del tenant; INDEX (tenant_id, status) para listados activos.

Tabla: **user_branches**

*Asignación de usuarios a sucursales. Permite que un vendedor opere en múltiples sucursales.*

|                |             |                 |                                 |
|:---------------|:------------|:----------------|:--------------------------------|
| **Campo**      | **Tipo**    | **Constraints** | **Notas**                       |
| **user_id**    | uuid        | FK NOT NULL     | Parte de PK compuesta.          |
| **branch_id**  | uuid        | FK NOT NULL     | Parte de PK compuesta.          |
| **is_primary** | boolean     | DEFAULT false   | Sucursal principal del usuario. |
| **created_at** | timestamptz |                 |                                 |

Tabla: **subscriptions**

*Histórico de suscripciones del tenant a planes. Una vigente por tenant.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **plan_id** | uuid | FK NOT NULL |  |
| **status** | subscription_status_enum | NOT NULL | active \| past_due \| cancelled. |
| **start_date** | date | NOT NULL |  |
| **end_date** | date | NULL |  |
| **mp_subscription_id** | varchar(120) | NULL | ID de la suscripción en Mercado Pago. |
| **amount_ars** | numeric(18,2) | NOT NULL | Precio efectivo (puede diferir del plan por descuento histórico). |
| **created_at** | timestamptz |  |  |
| **updated_at** | timestamptz |  |  |

**3.4 Dominio Stock**

Este dominio modela el inventario de vehículos y los catálogos compartidos de marcas, modelos y versiones.

Tabla: **vehicles**

*Una unidad concreta de stock. Un vehículo físico identificable.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **branch_id** | uuid | FK NOT NULL | Sucursal donde está el vehículo. |
| **assigned_user_id** | uuid | FK NULL | Vendedor responsable comercial. |
| **domain_plate** | varchar(15) | NOT NULL | Dominio (patente). Validado por formato AR. |
| **brand_id** | uuid | FK NOT NULL | Catálogo vehicle_brands. |
| **model_id** | uuid | FK NOT NULL |  |
| **version_id** | uuid | FK NULL | Versión específica (opcional). |
| **year** | smallint | NOT NULL CHECK (year BETWEEN 1950 AND extract(year from now())+1) |  |
| **mileage_km** | integer | NOT NULL CHECK (mileage_km \>= 0) |  |
| **color** | varchar(60) | NOT NULL |  |
| **fuel_type** | fuel_type_enum | NOT NULL | gasoline \| diesel \| hybrid \| electric \| gnc \| flex. |
| **transmission** | transmission_enum | NOT NULL | manual \| automatic \| cvt \| dsg. |
| **body_type** | body_type_enum | NOT NULL | sedan \| hatchback \| suv \| pickup \| van \| coupe \| wagon \| other. |
| **chassis_number** | varchar(30) | NULL | Número de chasis (VIN). |
| **engine_number** | varchar(30) | NULL |  |
| **price_ars** | numeric(18,2) | NOT NULL CHECK (price_ars \> 0) | Precio de venta vigente. |
| **price_usd** | numeric(18,2) | NULL | Precio en dólares para vehículos cotizados en moneda dura. |
| **acquisition_cost_ars** | numeric(18,2) | NULL | Costo de adquisición. Restringido a roles que ven margen. |
| **status** | vehicle_status_enum | NOT NULL DEFAULT 'in_preparation' | available \| reserved \| sold \| in_workshop \| in_preparation \| archived. |
| **description** | text | NULL | Descripción extendida usada en publicaciones. |
| **features** | jsonb | DEFAULT '\[\]' | Equipamiento. Array de identificadores normalizados. |
| **acquired_at** | timestamptz | NULL | Fecha de ingreso al stock. |
| **sold_at** | timestamptz | NULL | Fecha de venta efectiva. |
| **created_at** | timestamptz |  |  |
| **updated_at** | timestamptz |  |  |
| **deleted_at** | timestamptz | NULL |  |

Índices: UNIQUE (tenant_id, domain_plate) WHERE deleted_at IS NULL; INDEX (tenant_id, status); INDEX (tenant_id, brand_id, model_id, year); INDEX trigram sobre domain_plate y description para búsqueda full-text.

Tabla: **vehicle_brands**

*Catálogo canónico compartido de marcas (Ford, Toyota, etc.).*

|                    |             |                 |           |
|:-------------------|:------------|:----------------|:----------|
| **Campo**          | **Tipo**    | **Constraints** | **Notas** |
| **id**             | uuid        | PK              |           |
| **name**           | varchar(80) | UNIQUE NOT NULL |           |
| **slug**           | varchar(80) | UNIQUE NOT NULL |           |
| **origin_country** | varchar(60) | NULL            |           |
| **is_active**      | boolean     | DEFAULT true    |           |

Tabla: **vehicle_models**

*Modelos asociados a marcas (Hilux, Corolla, Onix).*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **brand_id** | uuid | FK NOT NULL |  |
| **name** | varchar(120) | NOT NULL |  |
| **body_type** | body_type_enum | NOT NULL |  |
| **year_from** | smallint | NOT NULL | Año de inicio de producción. |
| **year_to** | smallint | NULL | Año de fin de producción si discontinuado. |
| **is_active** | boolean | DEFAULT true |  |

Índices: UNIQUE (brand_id, name).

Tabla: **vehicle_versions**

*Versiones específicas dentro de un modelo (XEi CVT, GLS automática).*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **model_id** | uuid | FK NOT NULL |  |
| **name** | varchar(120) | NOT NULL |  |
| **engine_displacement** | numeric(3,1) | NULL | Cilindrada (1.6, 2.0). |
| **horsepower** | smallint | NULL |  |
| **transmission** | transmission_enum | NULL |  |
| **fuel_type** | fuel_type_enum | NULL |  |

Tabla: **vehicle_photos**

*Fotografías asociadas a un vehículo.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **vehicle_id** | uuid | FK NOT NULL |  |
| **storage_url** | varchar(500) | NOT NULL | URL en object storage. Servida vía CDN firmada para acceso autorizado. |
| **display_order** | smallint | NOT NULL DEFAULT 0 | Orden de visualización. |
| **is_cover** | boolean | NOT NULL DEFAULT false | Foto de portada. |
| **width_px** | integer | NULL |  |
| **height_px** | integer | NULL |  |
| **size_bytes** | bigint | NULL |  |
| **uploaded_by** | uuid | FK users |  |
| **created_at** | timestamptz |  |  |

Tabla: **vehicle_status_history**

*Histórico de cambios de estado de un vehículo. Append-only.*

|                 |                     |                        |           |
|:----------------|:--------------------|:-----------------------|:----------|
| **Campo**       | **Tipo**            | **Constraints**        | **Notas** |
| **id**          | uuid                | PK                     |           |
| **tenant_id**   | uuid                | FK NOT NULL            |           |
| **vehicle_id**  | uuid                | FK NOT NULL            |           |
| **from_status** | vehicle_status_enum | NULL                   |           |
| **to_status**   | vehicle_status_enum | NOT NULL               |           |
| **changed_by**  | uuid                | FK users               |           |
| **reason**      | text                | NULL                   |           |
| **changed_at**  | timestamptz         | NOT NULL DEFAULT now() |           |

**3.5 Dominio CRM**

Modela contactos, leads, pipeline, etapas, actividades y etiquetas. Es uno de los dominios con mayor volumen de operaciones.

Tabla: **contacts**

*Personas o entidades con las que el tenant interactúa: compradores, vendedores de usados, etc.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **full_name** | varchar(180) | NOT NULL |  |
| **document_type** | doc_type_enum | NULL | dni \| cuit \| passport. |
| **document_number** | varchar(20) | NULL | Validado según tipo. |
| **primary_phone** | varchar(40) | NOT NULL | Normalizado a formato E.164. |
| **secondary_phone** | varchar(40) | NULL |  |
| **email** | varchar(254) | NULL |  |
| **address** | varchar(255) | NULL |  |
| **city** | varchar(120) | NULL |  |
| **province** | varchar(120) | NULL |  |
| **birth_date** | date | NULL |  |
| **created_at** | timestamptz |  |  |
| **updated_at** | timestamptz |  |  |
| **deleted_at** | timestamptz | NULL |  |

Índices: UNIQUE (tenant_id, document_number, document_type) WHERE document_number IS NOT NULL; UNIQUE (tenant_id, primary_phone); INDEX trigram sobre full_name.

Tabla: **leads**

*Oportunidad comercial generada por una consulta de un comprador.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **contact_id** | uuid | FK NOT NULL |  |
| **vehicle_id** | uuid | FK NULL | Vehículo de interés (puede ser búsqueda genérica). |
| **assigned_user_id** | uuid | FK NOT NULL | Vendedor responsable. |
| **branch_id** | uuid | FK NOT NULL |  |
| **pipeline_stage_id** | uuid | FK NOT NULL | Etapa actual. |
| **source** | lead_source_enum | NOT NULL | deruedas_portal \| mercadolibre \| facebook \| walk_in \| phone \| referral \| other. |
| **status** | lead_status_enum | NOT NULL DEFAULT 'open' | open \| won \| lost. |
| **loss_reason_id** | uuid | FK NULL | Motivo de pérdida si status = lost. |
| **estimated_value_ars** | numeric(18,2) | NULL | Valor estimado de operación. |
| **last_activity_at** | timestamptz | NULL | Cuándo fue la última interacción registrada. |
| **closed_at** | timestamptz | NULL |  |
| **notes** | text | NULL |  |
| **created_at** | timestamptz |  |  |
| **updated_at** | timestamptz |  |  |

Índices: INDEX (tenant_id, assigned_user_id, status); INDEX (tenant_id, pipeline_stage_id); INDEX (tenant_id, vehicle_id); INDEX (tenant_id, last_activity_at) para detectar leads sin actividad.

Tabla: **pipeline_stages**

*Etapas configurables del pipeline por tenant.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **name** | varchar(80) | NOT NULL |  |
| **display_order** | smallint | NOT NULL |  |
| **is_initial** | boolean | DEFAULT false | Etapa de entrada por defecto de leads nuevos. |
| **is_won** | boolean | DEFAULT false | Marca etapa de cierre exitoso. |
| **is_lost** | boolean | DEFAULT false | Marca etapa de pérdida. |
| **expected_duration_days** | smallint | NULL | Días esperados en esta etapa antes de alertar. |
| **created_at** | timestamptz |  |  |
| **updated_at** | timestamptz |  |  |

Tabla: **lead_stage_history**

*Histórico de cambios de etapa. Append-only.*

|                   |             |                        |           |
|:------------------|:------------|:-----------------------|:----------|
| **Campo**         | **Tipo**    | **Constraints**        | **Notas** |
| **id**            | uuid        | PK                     |           |
| **tenant_id**     | uuid        | FK NOT NULL            |           |
| **lead_id**       | uuid        | FK NOT NULL            |           |
| **from_stage_id** | uuid        | FK NULL                |           |
| **to_stage_id**   | uuid        | FK NOT NULL            |           |
| **changed_by**    | uuid        | FK users               |           |
| **changed_at**    | timestamptz | NOT NULL DEFAULT now() |           |

Tabla: **lead_activities**

*Actividades planificadas o ejecutadas vinculadas a un lead.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **lead_id** | uuid | FK NOT NULL |  |
| **activity_type** | activity_type_enum | NOT NULL | call \| meeting \| test_drive \| quote \| email \| whatsapp \| note \| other. |
| **scheduled_at** | timestamptz | NULL | Para actividades futuras. |
| **completed_at** | timestamptz | NULL | Para actividades pasadas. |
| **title** | varchar(180) | NOT NULL |  |
| **description** | text | NULL |  |
| **outcome** | text | NULL | Resultado registrado al completar. |
| **created_by** | uuid | FK users |  |
| **created_at** | timestamptz |  |  |
| **updated_at** | timestamptz |  |  |

Tabla: **loss_reasons**

*Catálogo de motivos de pérdida configurable por tenant.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **name** | varchar(120) | NOT NULL |  |
| **category** | varchar(60) | NULL | Agrupación opcional para reportes. |

Tabla: **tags y lead_tags**

*Etiquetado libre de leads. Tabla de tags y tabla pivote.*

|                       |             |                 |            |
|:----------------------|:------------|:----------------|:-----------|
| **Campo**             | **Tipo**    | **Constraints** | **Notas**  |
| **tags.id**           | uuid        | PK              |            |
| **tags.tenant_id**    | uuid        | FK NOT NULL     |            |
| **tags.name**         | varchar(60) | NOT NULL        |            |
| **tags.color**        | varchar(7)  | NULL            | Hex color. |
| **lead_tags.lead_id** | uuid        | FK PK           | Pivote.    |
| **lead_tags.tag_id**  | uuid        | FK PK           |            |

**3.6 Dominio Communication**

Modela las conversaciones con compradores, los mensajes individuales y los templates aprobados de WhatsApp.

Tabla: **conversations**

*Conversación entre la agencia y un contacto, generalmente vía WhatsApp.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **contact_id** | uuid | FK NOT NULL |  |
| **lead_id** | uuid | FK NULL | Lead asociado, si aplica. |
| **channel** | channel_enum | NOT NULL | whatsapp \| facebook_messenger \| sms \| email. |
| **assigned_user_id** | uuid | FK NULL | Vendedor que la atiende. |
| **status** | conversation_status_enum | NOT NULL DEFAULT 'open' | open \| snoozed \| closed. |
| **last_message_at** | timestamptz | NULL |  |
| **last_inbound_at** | timestamptz | NULL | Último mensaje del cliente; usado para ventana 24h de WhatsApp. |
| **unread_count** | integer | NOT NULL DEFAULT 0 |  |
| **created_at** | timestamptz |  |  |
| **updated_at** | timestamptz |  |  |

Índices: UNIQUE (tenant_id, channel, contact_id) WHERE status != 'closed'; INDEX (tenant_id, assigned_user_id, status).

Tabla: **messages**

*Mensaje individual dentro de una conversación.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **conversation_id** | uuid | FK NOT NULL |  |
| **direction** | message_direction_enum | NOT NULL | inbound \| outbound. |
| **sender_user_id** | uuid | FK NULL | NULL si es inbound o automatizado. |
| **external_id** | varchar(120) | NULL | ID del mensaje en la plataforma externa. |
| **body** | text | NULL | Texto del mensaje. |
| **media_url** | varchar(500) | NULL |  |
| **media_type** | varchar(40) | NULL | image \| video \| document \| audio. |
| **template_id** | uuid | FK NULL | Si fue enviado con un template. |
| **status** | message_status_enum | NOT NULL | pending \| sent \| delivered \| read \| failed. |
| **error_detail** | text | NULL | Si status = failed. |
| **sent_at** | timestamptz | NULL |  |
| **delivered_at** | timestamptz | NULL |  |
| **read_at** | timestamptz | NULL |  |
| **created_at** | timestamptz |  |  |

Índices: INDEX (conversation_id, created_at) para reconstrucción del hilo.

Tabla: **whatsapp_templates**

*Templates aprobados por Meta para envíos proactivos.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **name** | varchar(120) | NOT NULL |  |
| **language** | varchar(10) | NOT NULL DEFAULT 'es' |  |
| **category** | varchar(40) | NOT NULL | marketing \| utility \| authentication. |
| **body_template** | text | NOT NULL | Texto con placeholders {{1}}, {{2}}. |
| **meta_status** | template_status_enum | NOT NULL DEFAULT 'pending' | pending \| approved \| rejected. |
| **meta_template_id** | varchar(120) | NULL | ID asignado por Meta. |
| **rejection_reason** | text | NULL |  |
| **approved_at** | timestamptz | NULL |  |
| **created_at** | timestamptz |  |  |

**3.7 Dominio Trade-in (Permutas)**

Modela las solicitudes de permuta, las valuaciones y las inspecciones físicas asociadas.

Tabla: **swap_requests**

*Solicitud de permuta vinculada a una operación o lead.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **lead_id** | uuid | FK NOT NULL |  |
| **incoming_brand_id** | uuid | FK NOT NULL | Marca del usado a recibir. |
| **incoming_model_id** | uuid | FK NOT NULL |  |
| **incoming_year** | smallint | NOT NULL |  |
| **incoming_mileage_km** | integer | NOT NULL |  |
| **incoming_domain_plate** | varchar(15) | NOT NULL |  |
| **status** | swap_status_enum | NOT NULL DEFAULT 'requested' | requested \| valuated \| inspected \| accepted \| rejected \| closed. |
| **accepted_value_ars** | numeric(18,2) | NULL | Valor finalmente aceptado. |
| **resulting_vehicle_id** | uuid | FK NULL | Vehículo creado en stock al cerrar. |
| **created_at** | timestamptz |  |  |
| **updated_at** | timestamptz |  |  |

Tabla: **swap_valuations**

*Valuaciones realizadas sobre una solicitud (puede haber varias iteraciones).*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **swap_request_id** | uuid | FK NOT NULL |  |
| **min_value_ars** | numeric(18,2) | NOT NULL | Mínimo del rango sugerido. |
| **mid_value_ars** | numeric(18,2) | NOT NULL | Mediana del mercado. |
| **max_value_ars** | numeric(18,2) | NOT NULL |  |
| **proposed_value_ars** | numeric(18,2) | NOT NULL | Valor propuesto al cliente. |
| **data_source** | varchar(60) | NOT NULL | deruedas_index \| manual \| external_api. |
| **created_by** | uuid | FK users |  |
| **created_at** | timestamptz |  |  |

Tabla: **swap_inspections**

*Inspección física de cien puntos sobre el vehículo a recibir.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **swap_request_id** | uuid | FK NOT NULL |  |
| **mechanical_score** | smallint | CHECK (BETWEEN 0 AND 100) |  |
| **electrical_score** | smallint | CHECK (BETWEEN 0 AND 100) |  |
| **body_score** | smallint | CHECK (BETWEEN 0 AND 100) |  |
| **mileage_verified** | boolean | NOT NULL DEFAULT false |  |
| **structural_damage** | boolean | NOT NULL DEFAULT false |  |
| **taxi_remis_history** | boolean | NULL |  |
| **details** | jsonb | NULL | Detalle de los 100 puntos. |
| **inspector_user_id** | uuid | FK users |  |
| **inspected_at** | timestamptz | NOT NULL |  |
| **created_at** | timestamptz |  |  |

**3.8 Dominio Finance**

Modela las financieras integradas y el ciclo de vida de las solicitudes de crédito.

Tabla: **financial_partners**

*Catálogo de financieras integradas, configurable por Super Admin.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **name** | varchar(120) | NOT NULL |  |
| **api_endpoint** | varchar(500) | NOT NULL |  |
| **origination_fee_pct** | numeric(5,2) | NOT NULL | Comisión de originación a deRuedas. |
| **max_ltv_pct** | numeric(5,2) | NOT NULL | Loan-to-value máximo. |
| **max_term_months** | smallint | NOT NULL |  |
| **min_amount_ars** | numeric(18,2) | NOT NULL |  |
| **is_active** | boolean | DEFAULT true |  |

Tabla: **credit_applications**

*Solicitud de crédito vinculada a un lead u operación.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **lead_id** | uuid | FK NULL |  |
| **operation_id** | uuid | FK NULL |  |
| **contact_id** | uuid | FK NOT NULL |  |
| **vehicle_id** | uuid | FK NULL |  |
| **amount_ars** | numeric(18,2) | NOT NULL | Monto solicitado. |
| **down_payment_ars** | numeric(18,2) | NOT NULL | Entrega. |
| **term_months** | smallint | NOT NULL |  |
| **status** | credit_status_enum | NOT NULL DEFAULT 'pre_qualifying' | pre_qualifying \| submitted \| approved \| rejected \| signed \| disbursed \| cancelled. |
| **selected_offer_id** | uuid | FK NULL | Oferta elegida por el cliente. |
| **submitted_at** | timestamptz | NULL |  |
| **resolved_at** | timestamptz | NULL |  |
| **created_at** | timestamptz |  |  |
| **updated_at** | timestamptz |  |  |

Tabla: **credit_offers**

*Cada oferta concreta de una financiera para una solicitud.*

|  |  |  |  |
|:---|:---|:---|:---|
| **Campo** | **Tipo** | **Constraints** | **Notas** |
| **id** | uuid | PK |  |
| **tenant_id** | uuid | FK NOT NULL |  |
| **application_id** | uuid | FK NOT NULL |  |
| **partner_id** | uuid | FK NOT NULL |  |
| **status** | offer_status_enum | NOT NULL | pending \| offered \| accepted \| rejected \| expired. |
| **monthly_payment_ars** | numeric(18,2) | NOT NULL | Cuota. |
| **nominal_rate_pct** | numeric(6,2) | NOT NULL | TNA. |
| **effective_rate_pct** | numeric(6,2) | NOT NULL | TEA. |
| **total_cost_ars** | numeric(18,2) | NOT NULL | Costo financiero total. |
| **expires_at** | timestamptz | NULL |  |
| **external_offer_id** | varchar(120) | NULL | ID de la oferta en la financiera. |
| **created_at** | timestamptz |  |  |

**3.9 Dominios restantes**

Los dominios siguientes se documentan con menor detalle por brevedad. Sus tablas siguen las mismas convenciones generales: tenant_id NOT NULL, soft delete, timestamps, FK indexadas.

**Documents**

- documents: documento único con campos id, tenant_id, document_type_id, related_entity_type (vehicle, contact, operation), related_entity_id, storage_url, file_size, mime_type, ocr_text (full-text indexed), expires_at, uploaded_by, status, created_at.

- document_types: catálogo cross-tenant con id, code, name, has_expiration, requires_renewal.

- document_signatures: id, tenant_id, document_id, signer_contact_id, signature_provider, external_signature_id, signed_at, status.

**Accounting**

- payments: cobros recibidos. id, tenant_id, operation_id, contact_id, amount_ars, currency, payment_method, reference_number, paid_at.

- vendor_payments: pagos a proveedores (talleres, financieras). Misma estructura que payments con vendor_id en vez de operation/contact.

- bank_movements: movimientos bancarios importados. id, tenant_id, bank_account_id, amount_ars, movement_date, description, reconciled_payment_id (FK NULL).

- account_balances: vista materializada de saldos por contacto.

**Operations**

- sales_operations: operación de venta cerrada. id, tenant_id, vehicle_id, buyer_contact_id, sale_price_ars, sold_at, lead_id, swap_request_id, credit_application_id, status.

- operation_costs: costos imputables a una operación (taller, comisión interna, financiera). id, operation_id, cost_type, amount_ars, description.

- publishing_status: estado de publicación de un vehículo en cada portal. vehicle_id + portal + status + published_at + external_url + last_error.

**Audit**

- audit_logs: registro append-only de operaciones sensibles. id, tenant_id, user_id, action, entity_type, entity_id, before_data, after_data, ip, user_agent, occurred_at.

- Particionada por mes para retención y performance. Conservación mínima de cinco años.

**Notifications y Feature Flags**

- notifications: notificaciones in-app. id, tenant_id, user_id, type, payload, read_at, created_at.

- feature_flags: id, name, scope (global, tenant, user), target_id, is_enabled, conditions (jsonb).

**3.10 Vistas materializadas**

El sistema mantiene un conjunto pequeño de vistas materializadas para soportar dashboards y queries analíticas sin afectar la performance OLTP. Las vistas se refrescan en background con cadencia por minuto u hora según el caso de uso.

- mv_pipeline_summary: agregaciones por tenant y etapa para dashboards de pipeline.

- mv_stock_aging: vehículos con días en stock para reportes de rotación.

- mv_sales_monthly: ventas agregadas por mes, marca, modelo y vendedor.

- mv_lead_conversion: tasa de conversión por etapa y por canal.

- mv_outstanding_receivables: cuentas por cobrar agrupadas por antigüedad.

**4. Contratos de API**

**4.1 Convenciones generales**

La API es REST sobre HTTPS. Toda comunicación entre clientes y servidor pasa por esta API; no existen accesos directos a la base de datos desde clientes. La especificación completa de cada endpoint se mantiene en formato OpenAPI 3.1 dentro del repositorio del proyecto, en el archivo openapi.yaml. Esta sección establece las convenciones generales y describe los endpoints más relevantes a modo de referencia.

**4.1.1 Versionado**

La API se versiona en el path: /api/v1/. Los cambios incompatibles requieren incrementar la versión mayor. Los cambios compatibles (agregar campos opcionales, agregar endpoints nuevos, agregar valores a enums) no requieren cambio de versión pero se documentan en el changelog.

**4.1.2 Autenticación**

Todos los endpoints requieren autenticación, salvo los marcados explícitamente como públicos. La autenticación se realiza mediante un JWT emitido por Keycloak, enviado en el header Authorization.

Authorization: Bearer eyJhbGciOiJSUzI1NiIs...

El token tiene un tiempo de vida corto (quince minutos) y se renueva mediante refresh token, que tiene un tiempo de vida más largo (siete días). El refresh token solo es utilizable desde el dispositivo desde el cual se emitió, identificado por su huella.

**4.1.3 Identificación del tenant**

El tenant del usuario está embebido en el JWT como claim. El backend extrae el tenant_id del token y lo establece como variable de sesión PostgreSQL antes de ejecutar cualquier query. No es posible operar sobre datos de un tenant distinto del propio bajo ningún circunstancia, salvo para usuarios con rol Super Admin que tienen un endpoint diferenciado bajo /admin/api/v1.

**4.1.4 Formato de payloads**

Todos los payloads de request y response son JSON UTF-8. Las fechas usan ISO 8601 con timezone (formato 2026-05-06T14:30:00-03:00). Los identificadores son UUID en formato canónico. Los valores monetarios son números decimales con dos posiciones (no strings, salvo que el cliente lo solicite explícitamente vía Accept-Encoding-Numeric: string para evitar pérdida de precisión).

**4.1.5 Paginación**

Los endpoints de listado usan paginación basada en cursor para listados grandes y paginación numerada para listados con cuenta total. Los parámetros estándar son:

GET /api/v1/vehicles?page=1&page_size=50

GET /api/v1/messages?cursor=eyJpZCI6...&limit=100

Response headers:

X-Total-Count: 1342 (solo en paginación numerada)

X-Page: 1

X-Page-Size: 50

**4.1.6 Filtros y ordenamiento**

Los filtros simples se expresan como query params con el nombre del campo. Los filtros con operadores se expresan con sufijos. El ordenamiento usa el parámetro sort con coma para múltiples campos y prefijo - para descendente.

GET /api/v1/vehicles?status=available

GET /api/v1/vehicles?price_ars\_\_gte=5000000&price_ars\_\_lte=15000000

GET /api/v1/vehicles?year\_\_in=2020,2021,2022

GET /api/v1/vehicles?sort=-created_at,price_ars

GET /api/v1/vehicles?q=onix

**4.1.7 Manejo de errores**

Los errores siguen el formato Problem Details for HTTP APIs (RFC 7807) con extensiones de campo. Los códigos de status HTTP se usan según semántica estándar.

HTTP/1.1 422 Unprocessable Entity

Content-Type: application/problem+json

{

"type": "https://docs.deruedas.com/errors/validation",

"title": "Validation failed",

"status": 422,

"detail": "One or more fields are invalid",

"trace_id": "01F3K2H...",

"errors": \[

{

"field": "domain_plate",

"code": "format_invalid",

"message": "El dominio no tiene un formato válido"

}

\]

}

**4.1.8 Idempotencia**

Los endpoints de creación que pueden generar duplicados aceptan el header Idempotency-Key. Si dos requests llegan con la misma clave dentro de las veinticuatro horas, el segundo devuelve la misma respuesta del primero sin re-ejecutar la operación.

**4.1.9 Rate limiting**

Los endpoints están protegidos por rate limiting por usuario y por tenant. Los límites estándar son sesenta requests por minuto por usuario y mil requests por minuto por tenant. Los endpoints de webhook y de procesamiento masivo tienen límites específicos. El header X-RateLimit-Remaining indica cuántos requests quedan disponibles.

**4.2 Endpoints principales por dominio**

**4.2.1 Auth**

POST /api/v1/auth/login

POST /api/v1/auth/refresh

POST /api/v1/auth/logout

POST /api/v1/auth/forgot-password

POST /api/v1/auth/reset-password

POST /api/v1/auth/mfa/enable

POST /api/v1/auth/mfa/verify

GET /api/v1/auth/me \# info del usuario actual

**4.2.2 Stock**

GET /api/v1/vehicles \# listado paginado con filtros

GET /api/v1/vehicles/{id} \# detalle completo

POST /api/v1/vehicles \# crear vehículo

PATCH /api/v1/vehicles/{id} \# editar campos parcialmente

DELETE /api/v1/vehicles/{id} \# soft-delete

POST /api/v1/vehicles/{id}/photos \# subir foto

DELETE /api/v1/vehicles/{id}/photos/{photo_id}

PATCH /api/v1/vehicles/{id}/photos/order \# reordenar fotos

POST /api/v1/vehicles/{id}/status \# cambiar estado

GET /api/v1/vehicles/{id}/history \# histórico de cambios

POST /api/v1/vehicles/import \# importación masiva CSV

GET /api/v1/vehicles/{id}/price-suggestion

Catálogos:

GET /api/v1/catalog/brands

GET /api/v1/catalog/brands/{id}/models

GET /api/v1/catalog/models/{id}/versions

**4.2.3 CRM**

GET /api/v1/leads \# con filtros por etapa, vendedor, etc.

GET /api/v1/leads/{id}

POST /api/v1/leads \# creación manual

PATCH /api/v1/leads/{id}

POST /api/v1/leads/{id}/stage \# cambio de etapa

POST /api/v1/leads/{id}/assign \# reasignación

POST /api/v1/leads/{id}/close \# ganado o perdido

GET /api/v1/leads/{id}/activities

POST /api/v1/leads/{id}/activities

PATCH /api/v1/activities/{id}/complete

GET /api/v1/contacts

GET /api/v1/contacts/{id}

POST /api/v1/contacts

PATCH /api/v1/contacts/{id}

POST /api/v1/contacts/merge \# merge de duplicados

GET /api/v1/pipeline/stages

POST /api/v1/pipeline/stages

PATCH /api/v1/pipeline/stages/{id}

DELETE /api/v1/pipeline/stages/{id} \# con reasignación obligatoria

**4.2.4 Communication**

GET /api/v1/conversations

GET /api/v1/conversations/{id}

GET /api/v1/conversations/{id}/messages

POST /api/v1/conversations/{id}/messages

POST /api/v1/conversations/{id}/read \# marcar como leída

POST /api/v1/conversations/{id}/assign

POST /api/v1/conversations/{id}/close

GET /api/v1/whatsapp/templates

POST /api/v1/whatsapp/templates

GET /api/v1/whatsapp/templates/{id}/status

POST /webhooks/whatsapp \# endpoint público con HMAC

**4.2.5 Trade-in (Permutas)**

GET /api/v1/swaps

POST /api/v1/swaps \# crear solicitud

GET /api/v1/swaps/{id}

POST /api/v1/swaps/{id}/valuations \# nueva valuación

POST /api/v1/swaps/{id}/inspections \# registrar inspección

POST /api/v1/swaps/{id}/proposal \# generar propuesta PDF

POST /api/v1/swaps/{id}/close \# cerrar y crear vehículo en stock

**4.2.6 Finance**

GET /api/v1/credit/applications

POST /api/v1/credit/applications

GET /api/v1/credit/applications/{id}

POST /api/v1/credit/applications/{id}/pre-qualify \# consulta a financieras

GET /api/v1/credit/applications/{id}/offers

POST /api/v1/credit/applications/{id}/select-offer

POST /api/v1/credit/applications/{id}/submit \# solicitud formal

GET /api/v1/credit/applications/{id}/status

POST /api/v1/credit/applications/{id}/sign \# iniciar firma electrónica

POST /webhooks/finance/{partner} \# callbacks de financieras

**4.2.7 Documents**

GET /api/v1/documents

POST /api/v1/documents \# subida con multipart

GET /api/v1/documents/{id} \# metadata

GET /api/v1/documents/{id}/download \# url firmada temporal

DELETE /api/v1/documents/{id}

POST /api/v1/documents/search \# búsqueda full-text

POST /api/v1/documents/{id}/sign \# solicitar firma electrónica

POST /api/v1/operations/{id}/document-package \# paquete documental

**4.2.8 Accounting**

GET /api/v1/payments

POST /api/v1/payments

GET /api/v1/payments/{id}/receipt \# comprobante PDF

GET /api/v1/contacts/{id}/account \# cuenta corriente

POST /api/v1/bank/import \# importar extracto

GET /api/v1/bank/movements

POST /api/v1/bank/reconcile \# asociar movimiento con pago

GET /api/v1/accounting/export?format=tango&from=...&to=...

**4.2.9 Operations**

GET /api/v1/operations

GET /api/v1/operations/{id}

POST /api/v1/operations \# crear venta

POST /api/v1/operations/{id}/close \# cerrar operación

POST /api/v1/operations/{id}/costs \# imputar costo

**4.2.10 Analytics**

GET /api/v1/dashboards/stock

GET /api/v1/dashboards/pipeline

GET /api/v1/dashboards/sales

GET /api/v1/dashboards/productivity

GET /api/v1/dashboards/financial

GET /api/v1/reports/{report_id}

POST /api/v1/reports/custom \# reporte personalizado

POST /api/v1/reports/{id}/export?format=xlsx

**4.2.11 Admin (Super Admin)**

GET /admin/api/v1/tenants

GET /admin/api/v1/tenants/{id}

POST /admin/api/v1/tenants

PATCH /admin/api/v1/tenants/{id}

POST /admin/api/v1/tenants/{id}/impersonate

GET /admin/api/v1/tenants/{id}/health

GET /admin/api/v1/plans

POST /admin/api/v1/plans

PATCH /admin/api/v1/plans/{id}

GET /admin/api/v1/support/tickets

POST /admin/api/v1/support/tickets/{id}/reply

**4.3 Eventos y webhooks**

El sistema publica eventos de dominio internos en Redis Streams y eventos externos como webhooks salientes hacia URLs configurables por el cliente. Los eventos siguen un formato consistente:

{

"event_id": "evt_01F3K...",

"event_type": "vehicle.created",

"event_version": "1.0",

"tenant_id": "uuid",

"occurred_at": "2026-05-06T14:30:00-03:00",

"data": { ... payload específico ... }

}

Los eventos principales son: vehicle.created, vehicle.updated, vehicle.status_changed, lead.created, lead.stage_changed, lead.closed, message.received, message.sent, swap.closed, credit.application_submitted, credit.application_resolved, operation.closed, payment.recorded.

**5. Architecture Decision Records (ADRs)**

Los ADRs documentan las decisiones arquitectónicas vinculantes del proyecto. Cada ADR sigue una estructura estándar: contexto que explica por qué surge la decisión, decisión que registra qué se elige, alternativas evaluadas y descartadas con su razón, y consecuencias positivas y negativas previsibles. Los ADRs son inmutables una vez aprobados; cuando una decisión cambia, se escribe un ADR posterior que la supersede.

**ADR-001 — Arquitectura modular monolítica con eventos asíncronos** *\[Aceptado\]*

**Contexto**

El equipo de desarrollo inicial es pequeño (entre cuatro y seis ingenieros en la fase MVP), el dominio es relativamente acotado, y el time-to-market es crítico. Las dos arquitecturas candidatas en mercado son: monolito modular (un único proceso con módulos delimitados internamente) y microservicios (múltiples procesos comunicados por red).

**Decisión**

Se adopta una arquitectura modular monolítica con eventos asíncronos para la comunicación entre módulos. Todo el código backend vive en un único repositorio y se ejecuta en un único proceso de aplicación, organizado internamente en módulos delimitados con interfaces explícitas. Las comunicaciones que admiten asincronía pasan por una cola con Redis Streams y workers Celery.

**Alternativas consideradas**

- Microservicios desde el día uno: descartado por overhead operacional excesivo para el tamaño del equipo y por la inmadurez del dominio, que aún no tiene fronteras claras.

- Monolito puro sincrónico: descartado porque las integraciones externas (WhatsApp, financieras, portales) son inherentemente asíncronas y forzar sincronía limitaría la performance.

**Consecuencias**

- Positiva: simpleza operacional y de despliegue.

- Positiva: refactorización entre módulos es de bajo costo mientras siguen siendo internos.

- Positiva: trazas distribuidas más simples por viajar dentro del mismo proceso para flujos sincrónicos.

- Negativa: el escalado es vertical hasta que se decida extraer servicios.

- Mitigación: se diseña con fronteras de módulo limpias para que la extracción futura sea factible si la escala lo demanda.

**ADR-002 — PostgreSQL como base de datos relacional principal** *\[Aceptado\]*

**Contexto**

El sistema requiere una base de datos transaccional fiable, con soporte para multi-tenancy, búsqueda eficiente, datos geográficos y JSON estructurado. La decisión se evalúa en el contexto de las opciones más maduras del mercado argentino y de la disponibilidad de servicios gestionados en proveedores cloud.

**Decisión**

Se adopta PostgreSQL versión 16 como base de datos relacional principal. Se utilizan las extensiones pgcrypto para cifrado de campos sensibles, pg_trgm para búsqueda fuzzy, PostGIS para datos geográficos de sucursales, y la funcionalidad nativa de Row-Level Security para aislamiento multi-tenant.

**Alternativas consideradas**

- MySQL: descartado por menor robustez del soporte a tipos avanzados (JSONB, arrays, geo), políticas RLS más limitadas, y menor familiaridad del equipo.

- MongoDB: descartado porque el dominio es predominantemente relacional con muchas joins entre entidades vinculadas, donde un modelo documental introduciría complejidad sin beneficio.

**Consecuencias**

- Positiva: ecosistema maduro con ORMs robustos, herramientas de migración (Alembic) y monitoreo.

- Positiva: PostgreSQL gestionado disponible en todos los proveedores cloud relevantes.

- Negativa: escalado horizontal de escrituras requiere sharding manual o migración futura. Se considera aceptable dado el volumen proyectado para los primeros tres años.

**ADR-003 — Python con FastAPI como stack del backend** *\[Aceptado\]*

**Contexto**

Se evalúa el stack del backend considerando productividad del equipo, performance, ecosistema, disponibilidad de talento en el mercado argentino y alineamiento con las funcionalidades estratégicas del producto, particularmente la capa futura de inteligencia artificial.

**Decisión**

Se adopta Python 3.12 con FastAPI como stack del backend. La elección se justifica en: tipado estático con Pydantic v2 que mejora la robustez frente a Python tradicional; performance asincrónica adecuada para el volumen esperado; ecosistema rico para integraciones (WhatsApp, financieras, OCR, IA); generación automática de OpenAPI desde el código; y disponibilidad amplia de talento en el mercado argentino.

**Alternativas consideradas**

- Node.js + NestJS + TypeScript: técnicamente viable, ecosistema maduro, buena performance. Descartado principalmente por menor alineamiento con la capa de IA y procesamiento de datos prevista en fases posteriores, donde Python tiene ventaja sustancial.

- Go: mejor performance bruta, descartado por menor productividad para iteración rápida en MVP y por menor disponibilidad de talento.

**Consecuencias**

- Positiva: mayor velocidad de desarrollo en MVP.

- Positiva: continuidad de stack hacia capa de IA sin saltos tecnológicos.

- Negativa: menor performance bruta que Go o Rust. Mitigación: optimización selectiva de hotspots si la métrica lo demanda.

**ADR-004 — Next.js para frontend web** *\[Aceptado\]*

**Contexto**

El frontend web requiere render del lado del servidor para SEO de páginas públicas (landing del SaaS, simulador público), comportamiento SPA para la operación autenticada, y disponibilidad amplia de talento.

**Decisión**

Se adopta Next.js 14+ con React y TypeScript. Se utiliza el App Router para rutas modernas con server components donde aporta valor, y client components para la operación interactiva. Se aplica Tailwind CSS para estilos junto con un sistema de componentes propio basado en Radix UI.

**Alternativas consideradas**

- React puro con Vite: descartado por requerir SSR adicional para SEO.

- SvelteKit: descartado por base de talento más pequeña en Argentina.

**Consecuencias**

- Positiva: SSR nativo, optimización automática de imágenes, ecosistema dominante.

- Negativa: complejidad del modelo dual server/client components requiere disciplina del equipo. Mitigación: convenciones documentadas en repositorio.

**ADR-005 — React Native con Expo para aplicación móvil** *\[Aceptado\]*

**Contexto**

La aplicación móvil debe estar disponible en iOS y Android, compartir lógica con la web, soportar funcionalidades nativas como cámara, biometría, notificaciones push, y poder ser desarrollada por un equipo que ya conoce React.

**Decisión**

Se adopta React Native con Expo SDK. Se utiliza Expo Router para navegación, y se mantienen módulos nativos solo cuando una funcionalidad concreta no esté disponible en Expo (escaneo OCR de dominio, por ejemplo).

**Alternativas consideradas**

- Aplicaciones nativas separadas (Swift y Kotlin): descartado por costo y velocidad.

- Flutter: descartado por requerir aprender Dart y por menor capitalización del conocimiento de React del equipo.

**Consecuencias**

- Positiva: una sola base de código para iOS y Android.

- Positiva: reutilización de patrones y conocimiento del frontend web.

- Negativa: el bridge a nativo agrega un nivel de complejidad para integraciones específicas. Mitigación: priorizar Expo SDK; cuando no alcance, considerar módulos nativos puntuales.

**ADR-006 — Multi-tenancy con discriminator + Row-Level Security** *\[Aceptado\]*

**Contexto**

El sistema es multi-tenant. Las opciones principales para implementar el aislamiento son: schema-per-tenant (cada agencia tiene su esquema), database-per-tenant (cada agencia tiene su propia base), o discriminator-column (todas las tablas tienen tenant_id y se filtra).

**Decisión**

Se adopta el patrón discriminator-column con tenant_id NOT NULL en todas las tablas de negocio, complementado con Row-Level Security de PostgreSQL como capa de defensa en profundidad. La sesión de aplicación establece la variable PostgreSQL app.current_tenant al inicio de cada request, y las políticas RLS automáticamente restringen el acceso a las filas correspondientes.

**Alternativas consideradas**

- Schema-per-tenant: descartado por complejidad operacional al tener que mantener decenas o cientos de schemas, ejecutar migraciones en todos, y por límites prácticos de PostgreSQL.

- Database-per-tenant: descartado por costo y por dificultad de queries cross-tenant para reportes y administración.

**Consecuencias**

- Positiva: simplicidad operacional, una sola base, una sola migración.

- Positiva: queries cross-tenant para administración son triviales.

- Negativa: el riesgo de error en una query (olvidar el filtro) es presente. Mitigación: RLS como red de seguridad, auditoría automatizada de queries en code review.

**ADR-007 — Autenticación con OAuth2 / OIDC vía Keycloak** *\[Aceptado\]*

**Contexto**

El sistema requiere autenticación robusta, soporte para multi-factor authentication, posibilidad futura de single sign-on con clientes empresa, y manejo de tokens según estándares modernos.

**Decisión**

Se adopta Keycloak como servicio de identidad. La aplicación cliente y el backend se comunican con Keycloak mediante OAuth2 con OIDC. Los tokens son JWT firmados con RS256. Keycloak se autohospeda en la infraestructura propia para evitar dependencia de un proveedor externo.

**Alternativas consideradas**

- Auth construido a medida: descartado por la regla de la Constitución de no construir autenticación a medida.

- Auth0 / Cognito gestionados: descartado en esta etapa por costo a escala y por dependencia de proveedor.

**Consecuencias**

- Positiva: estándares maduros, configuración rica, soporte SSO empresarial.

- Negativa: operar Keycloak agrega carga operacional. Mitigación: documentación operativa específica.

**ADR-008 — Object storage S3-compatible para multimedia y documentos** *\[Aceptado\]*

**Contexto**

El sistema almacena un volumen significativo de fotografías de vehículos y documentos. El almacenamiento debe ser durable, escalable, accesible vía URL firmada, y con costos marginales bajos.

**Decisión**

Se adopta object storage S3-compatible (Amazon S3 o Google Cloud Storage según el proveedor cloud principal elegido). Las URLs de acceso se firman con tiempo de vida corto (cinco minutos para fotos, treinta minutos para documentos descargados). La distribución se hace vía CDN para fotos públicas y via URL firmada directa para documentos privados.

**Consecuencias**

- Positiva: durabilidad y escalabilidad nativa.

- Positiva: ecosistema maduro de SDKs.

- Negativa: dependencia del proveedor cloud. Mitigación: usar SDK genérico S3 que permita migración a otro proveedor compatible.

**ADR-009 — Eventos de dominio con Redis Streams + Celery** *\[Aceptado\]*

**Contexto**

La comunicación asincrónica entre módulos y el procesamiento background requieren un mecanismo de cola fiable, con persistencia, soporte para retry y dead-letter queue.

**Decisión**

Se adopta Redis Streams como broker de eventos y Celery como worker framework. Los eventos de dominio se publican en streams con nombre por dominio (stock-events, crm-events, etc.) y son consumidos por workers especializados. Las tareas con reintento se manejan con backoff exponencial y se enrutan a una dead-letter stream tras agotar reintentos.

**Alternativas consideradas**

- RabbitMQ: descartado por complejidad operacional adicional vs. el beneficio en este caso de uso.

- Kafka: descartado por overkill dado el volumen proyectado.

**Consecuencias**

- Positiva: Redis ya está presente para cache; reutilización de infraestructura.

- Negativa: Streams no es tan rica como Kafka en garantías y herramientas. Suficiente para el alcance proyectado.

**ADR-010 — WhatsApp Business Cloud API como única vía de mensajería** *\[Aceptado\]*

**Contexto**

WhatsApp es el canal dominante de comunicación comercial. Las opciones de integración son: WhatsApp Business Cloud API (oficial de Meta, recientemente disponible) o proveedores BSP (Business Solution Providers) intermediarios.

**Decisión**

Se adopta integración directa con WhatsApp Business Cloud API oficial. Se evita la dependencia de proveedores BSP intermediarios para reducir costos y eliminar un eslabón en la cadena de fallos.

**Consecuencias**

- Positiva: relación directa con Meta, mejor pricing a escala.

- Negativa: mayor responsabilidad operacional al manejar templates, calidad del número, etc. Aceptable.

**ADR-011 — OpenSearch para búsqueda full-text y catálogo** *\[Aceptado\]*

**Contexto**

La búsqueda en el catálogo de vehículos, en mensajes de conversaciones y en documentos OCRizados requiere capacidades full-text avanzadas, ranking, facetado y agregaciones que exceden lo razonable para una base SQL.

**Decisión**

Se adopta OpenSearch (fork open-source de Elasticsearch) como motor de búsqueda secundario. PostgreSQL sigue siendo la fuente de verdad; OpenSearch se mantiene sincronizado mediante eventos de dominio.

**Consecuencias**

- Positiva: capacidades de búsqueda y agregación muy superiores a SQL nativo.

- Negativa: complejidad operacional adicional. Mitigación: usar servicio gestionado del proveedor cloud.

**ADR-012 — Feature flags como herramienta de despliegue progresivo** *\[Aceptado\]*

**Contexto**

Toda funcionalidad nueva debe poder activarse o desactivarse en producción sin re-desplegar, y debe poder activarse progresivamente por tenant, por usuario o globalmente, según los principios de la Constitución.

**Decisión**

Se adopta una solución de feature flags con backend propio basado en una tabla feature_flags y un servicio de evaluación cacheado. La biblioteca cliente expone una función simple is_enabled(flag, context) usable desde cualquier punto del código. Los flags se administran desde el backoffice por el Super Admin.

**Alternativas consideradas**

- LaunchDarkly y similares gestionados: descartado en esta etapa por costo. Reconsiderable en fase 5 si la complejidad lo amerita.

**6. Requisitos no funcionales (NFRs)**

Los requisitos no funcionales fijan los umbrales cuantitativos que el sistema debe cumplir en producción. Los valores siguientes son objetivos para condiciones normales de carga; las excepciones puntuales se documentan como incidentes operacionales.

**6.1 Performance**

- Endpoints de listado: percentil 95 menor a 200 ms y percentil 99 menor a 500 ms en condiciones normales.

- Endpoints de búsqueda full-text: percentil 95 menor a 500 ms y percentil 99 menor a 1.5 s.

- Endpoints de detalle: percentil 95 menor a 150 ms.

- Endpoints de escritura simple (crear, actualizar): percentil 95 menor a 300 ms.

- Carga inicial de la web: time-to-interactive menor a 2 segundos en conexión 4G simulada.

- Operaciones bulk (importación de stock, exportación contable): tiempo objetivo proporcional al volumen, ejecutadas en background con feedback de progreso al usuario.

**6.2 Disponibilidad**

- SLA de disponibilidad mensual: 99.9% para los planes Starter y Pro, 99.95% para Enterprise.

- Ventanas de mantenimiento programadas: como máximo dos horas por mes, en horario nocturno argentino, con aviso previo de cuarenta y ocho horas.

- Recuperación ante caída completa de un nodo: menor a quince minutos hasta restablecimiento del servicio.

- Recuperación ante caída de zona de disponibilidad: menor a una hora con failover a zona secundaria.

**6.3 Capacidad y escalado**

- Capacidad inicial: 200 tenants, 1000 usuarios concurrentes, 50.000 vehículos en stock simultáneo, 500.000 leads activos, 5 millones de mensajes mensuales.

- Capacidad de crecimiento sin re-arquitectura: hasta 1000 tenants y 10x los volúmenes iniciales mediante escalado vertical de la base y horizontal del backend.

- Más allá de esos umbrales, se reevalúa la arquitectura con sharding, lectura replicada y eventual extracción de servicios.

**6.4 Recuperabilidad**

- RPO (Recovery Point Objective): pérdida máxima aceptable de datos de cinco minutos. Se cumple con replicación sincrónica y backups continuos.

- RTO (Recovery Time Objective): tiempo máximo de recuperación de una hora ante caída total.

- Backups: snapshots diarios completos retenidos por 30 días; snapshots semanales por 12 semanas; snapshots mensuales por 12 meses; archivado anual por 7 años para cumplimiento contable.

- Pruebas de recuperación: ensayo trimestral de restauración completa en ambiente de staging.

**6.5 Seguridad**

- Cifrado en tránsito: TLS 1.2 mínimo, TLS 1.3 cuando esté disponible. HSTS obligatorio en todas las respuestas.

- Cifrado en reposo: discos cifrados a nivel infraestructura; PII y secretos cifrados adicionalmente a nivel aplicación con KMS.

- Hashing de contraseñas: argon2id con parámetros revisados anualmente.

- Auditoría: todas las acciones sensibles dejan rastro en audit_logs con retención mínima de cinco años.

- Penetration testing: evaluación externa anual y al lanzamiento de cambios mayores.

**6.6 Accesibilidad**

- Cumplimiento WCAG 2.1 nivel AA en la aplicación web.

- Soporte completo para navegación por teclado en todos los flujos.

- Contraste mínimo 4.5:1 para texto, 3:1 para elementos gráficos.

- Etiquetas ARIA correctas en componentes interactivos.

- Compatibilidad probada con lectores de pantalla NVDA, JAWS y VoiceOver.

**6.7 Localización**

- Idioma por defecto: español de Argentina.

- Formatos de fecha (dd/mm/aaaa), número (separador de miles con punto, decimal con coma) y moneda (ARS y USD) según convenciones argentinas.

- Validaciones específicas argentinas: CUIT con dígito verificador, dominio (formato AA999AA o AAA999), DNI.

- Zona horaria por defecto: America/Argentina/Buenos_Aires, configurable por tenant.

**6.8 Compatibilidad de cliente**

- Navegadores web: últimas dos versiones mayores de Chrome, Firefox, Safari y Edge.

- iOS: 15 y posteriores.

- Android: API 26 (Android 8.0) y posteriores.

- Resoluciones desktop: a partir de 1280x720; mobile a partir de 360x640.

**7. Estrategia de testing**

**7.1 Pirámide de pruebas**

La estrategia se basa en la pirámide de testing clásica con énfasis en pruebas rápidas y deterministas. La proporción objetivo es: 70% pruebas unitarias, 20% pruebas de integración, 10% pruebas de extremo a extremo. La cobertura se mide tanto en líneas de código como en escenarios de negocio.

**7.1.1 Pruebas unitarias**

Verifican funciones, métodos y clases aisladas, sin dependencias externas reales. Las dependencias se sustituyen por mocks o fakes. Las pruebas unitarias se ejecutan en cada commit y deben completarse en menos de cinco minutos para la suite completa. Cada regla de negocio nueva tiene al menos una prueba unitaria que la verifica.

**7.1.2 Pruebas de integración**

Verifican la interacción entre componentes con dependencias reales: base de datos PostgreSQL real (en contenedor descartable), Redis real, Object storage real (con bucket de test). No se mockea la base, sí se mockean servicios externos como WhatsApp y financieras. Se ejecutan en cada pull request antes de mergear, con tiempo total objetivo menor a quince minutos.

**7.1.3 Pruebas de extremo a extremo**

Verifican flujos completos a través de la interfaz de usuario, simulando un usuario real. Se implementan con Playwright para web y Detox para mobile. Cubren los flujos críticos: login, alta de vehículo, captura de lead, conversación WhatsApp, cierre de operación. Tiempo objetivo menor a treinta minutos. Se ejecutan en el pipeline de release y al menos una vez al día contra staging.

**7.2 Cobertura mínima**

- Cobertura de líneas en backend: mínimo 80% para módulos core (auth, stock, crm, communication, finance), 70% para los demás.

- La cobertura no decrece entre commits: si un PR introduce código que reduce cobertura por debajo del umbral, no se mergea sin justificación documentada.

- La cobertura por sí sola no es indicador suficiente. Se complementa con revisión de escenarios de negocio cubiertos.

**7.3 Datos de prueba**

Las pruebas usan factories programáticas (con biblioteca tipo factory_boy) que generan datos realistas con valores aleatorios pero controlados. No se utilizan dumps de producción ni de cliente real bajo ninguna circunstancia. Para pruebas exploratorias se mantiene un dataset sintético llamado “agencia demo” que reproduce la complejidad de un cliente real con datos enteramente ficticios.

**7.4 Ambientes**

- Local: cada desarrollador con su entorno completo levantado en Docker Compose.

- CI: ambientes efímeros que se levantan por cada pipeline y se descartan al finalizar.

- Staging: ambiente persistente con datos sintéticos, espejo de producción. Se usa para pruebas E2E, validación de releases, demos a clientes.

- Producción: solo accesible vía pipeline de despliegue.

**7.5 Tests determinísticos**

Los tests no flaky son innegociables. Un test que falla intermitentemente se trata como bug del propio test, no como característica del sistema. Se arregla o se elimina. Si una funcionalidad no es testeable de manera determinista (por ejemplo por dependencias temporales), se rediseña hasta que lo sea.

**8. Estrategia de seguridad**

**8.1 Threat model resumido**

Las amenazas principales identificadas para el sistema son: filtración de datos entre tenants (un usuario de tenant A accede a datos de tenant B); takeover de cuenta (un atacante roba credenciales y opera como usuario legítimo); inyección de código (SQL, scripts, comandos); abuso de la API (scraping, DoS, abuso de cuotas); compromiso de servicios externos integrados; y errores internos del personal con acceso elevado. La estrategia se diseña con mitigaciones específicas para cada amenaza.

**8.2 Aislamiento multi-tenant**

La filtración de datos entre tenants se considera el incidente de seguridad más crítico. Las mitigaciones son cuatro y se aplican en simultáneo. Primero, todas las queries del código incluyen explícitamente la condición tenant_id como filtro. Segundo, las políticas de Row-Level Security de PostgreSQL aplican el filtro en la base de datos automáticamente, como red de seguridad. Tercero, en cada conexión a la base se establece la variable app.current_tenant en función del JWT del usuario; sin esa variable, las políticas RLS bloquean el acceso. Cuarto, hay tests automatizados que intentan acceder a datos de otro tenant y deben fallar con error de autorización.

**8.3 Autenticación**

La autenticación se delega íntegramente a Keycloak. La aplicación nunca maneja contraseñas en texto plano. Los flujos soportados son: login estándar con email y password, MFA opcional con TOTP, recuperación de contraseña mediante email firmado, y futuro SSO empresarial vía OIDC para clientes Enterprise.

**8.4 Autorización**

La autorización se basa en roles dentro del tenant. Los roles iniciales son Gerente, Vendedor y Administrativo, con permisos diferenciados sobre operaciones, información financiera, edición de catálogos y gestión de usuarios. Los permisos se evalúan siempre en el backend mediante decoradores en los endpoints; el frontend respeta los permisos para fines de UX (ocultar botones), pero no se confía en él como única defensa. La definición canónica de permisos vive en el módulo auth y se exporta como diccionario consultable.

**8.5 Manejo de secretos**

- Los secretos no viven en el repositorio. Se gestionan con AWS Secrets Manager / Google Secret Manager según proveedor cloud.

- Las claves de cifrado a nivel aplicación se gestionan con KMS y se rotan anualmente.

- Las APIs keys de servicios externos (WhatsApp, financieras) se almacenan cifradas y se rotan al término de cada contrato o al detectar compromiso.

**8.6 Protección contra OWASP Top 10**

- Inyección: uso obligatorio del ORM, parámetros bindeados; nunca string concatenation de SQL.

- XSS: escape automático en plantillas; CSP estricto; React escapa por defecto.

- CSRF: tokens en cambios de estado; cookies SameSite Strict.

- SSRF: lista blanca de dominios para fetch saliente desde el backend; validación de URLs.

- Deserialización insegura: Pydantic con validación estricta, nunca pickle de inputs externos.

- Componentes con vulnerabilidades: scanner automatizado en pipeline (Trivy, Snyk).

- Logging insuficiente: audit_logs estructurados con trace_id para correlación.

**8.7 Protección de datos personales**

La aplicación opera con datos personales sujetos a la Ley 25.326 de Protección de Datos Personales de Argentina. Las medidas vinculantes son: cifrado en reposo de DNI, CUIT, fotos de DNI; enmascaramiento en logs (los DNI aparecen como \*\*\*12345); consentimiento documentado para uso de datos de contactos; derecho de acceso, rectificación y eliminación operacionalizado mediante endpoints de gestión disponibles para el tenant; obligación contractual del tenant de obtener consentimiento de sus contactos.

**8.8 Auditoría**

Toda acción que afecte datos sensibles se registra en audit_logs. El registro incluye: usuario que ejecutó la acción, tenant, timestamp, IP, user-agent, tipo de acción, entidad afectada, valores anteriores y posteriores en formato JSON, y trace_id para correlación. Los logs son append-only; no existen endpoints para modificarlos. La retención mínima es cinco años por obligaciones contables.

**9. Despliegue y observabilidad**

**9.1 Pipeline de integración y despliegue continuo**

Todo cambio pasa por el siguiente pipeline antes de llegar a producción. La automatización completa del pipeline es regla vinculante; no hay despliegues manuales en producción salvo en respuesta a incidentes con procedimiento de excepción documentado.

- Etapa 1 - Lint y formato: ejecuta linters y formatters; bloquea si hay errores.

- Etapa 2 - Pruebas unitarias: ejecuta toda la suite unitaria de backend y frontend.

- Etapa 3 - Pruebas de integración: levanta servicios efímeros y ejecuta pruebas que tocan base, cache, storage.

- Etapa 4 - Análisis estático de seguridad: SAST sobre código y SCA sobre dependencias; bloquea si hay vulnerabilidades de severidad alta o crítica.

- Etapa 5 - Build de imágenes: construye imágenes Docker firmadas, etiquetadas con hash de commit.

- Etapa 6 - Despliegue automático a staging.

- Etapa 7 - Pruebas de extremo a extremo en staging contra el deploy recién hecho.

- Etapa 8 - Aprobación humana para producción (manual gate).

- Etapa 9 - Despliegue blue-green en producción con canary opcional.

- Etapa 10 - Smoke tests post-deploy y monitoreo de métricas durante quince minutos. Rollback automático si las métricas desviarán.

**9.2 Estrategia de despliegue blue-green con canary**

La aplicación se despliega con estrategia blue-green: dos pools de instancias (azul y verde), con un load balancer redirigiendo el tráfico a uno u otro. El nuevo despliegue se hace al pool inactivo, se valida con smoke tests y se hace switch del tráfico de manera atómica. El rollback consiste simplemente en hacer switch al pool anterior, lo que toma menos de un minuto. Para releases riesgosos se aplica adicionalmente canary: se redirige inicialmente solo el 5% del tráfico al nuevo deploy y se monitorea, escalando gradualmente al 100% si las métricas se mantienen sanas.

**9.3 Migraciones de base de datos**

Las migraciones se aplican con Alembic. Las reglas vinculantes son: las migraciones son retro-compatibles con la versión anterior del código durante al menos un release; las migraciones que no son retro-compatibles requieren ADR específico y plan de despliegue documentado; las migraciones que afectan más de un millón de filas se ejecutan en background con monitoreo de bloqueos; las migraciones nunca se ejecutan automáticamente en producción sin aprobación humana.

**9.4 Feature flags**

Toda funcionalidad nueva se despliega detrás de un feature flag controlable por tenant. La activación sigue el patrón de despliegue progresivo: primero usuarios internos del equipo, después agencias early adopter (cinco a diez tenants), después el resto en olas de 25%, 50% y 100%. La duración mínima de cada ola es de 48 horas para detectar problemas que se manifiesten con uso real.

**9.5 Stack de observabilidad**

- Métricas: Prometheus recolecta métricas de aplicación y de infraestructura. Grafana las visualiza en dashboards estandarizados.

- Logs: Loki agrega logs estructurados de toda la aplicación. Cada log incluye trace_id, tenant_id (cuando aplica), user_id, request_id.

- Tracing: Jaeger recolecta trazas distribuidas con OpenTelemetry. Cada request HTTP tiene una traza completa con spans por componente.

- Errores: Sentry captura excepciones no manejadas, las agrupa por similaridad y notifica al equipo. Cada error en producción tiene asignación nominal y SLA de respuesta.

- Alertas: Alertmanager con reglas sobre Prometheus. Las alertas críticas notifican vía PagerDuty o equivalente.

**9.6 Métricas mínimas monitoreadas**

- Métricas RED por endpoint: Rate (requests por segundo), Errors (porcentaje de errores 5xx), Duration (latencias p50, p95, p99).

- Métricas USE por recurso: Utilization, Saturation, Errors. Aplicadas a CPU, memoria, disco, red, conexiones de DB.

- Métricas de negocio: vehículos creados por hora, leads creados por hora, mensajes enviados, tasa de error de WhatsApp, latencia de las financieras.

- Métricas de calidad de datos: filas con tenant_id NULL (debe ser cero), conversaciones huérfanas, leads sin actividad por más de 30 días.

**9.7 SLOs (Service Level Objectives)**

- Disponibilidad mensual de la API: 99.9% para Starter/Pro, 99.95% para Enterprise.

- Latencia p95 endpoints listado: por debajo de 200 ms el 95% de los días del mes.

- Tasa de error 5xx: por debajo de 0.1% mensual.

- Tasa de éxito de envío de mensajes WhatsApp: superior a 98% mensual.

**9.8 Runbooks**

Cada componente crítico tiene un runbook asociado en el repositorio que documenta los procedimientos de respuesta a incidentes comunes: caída de la base de datos, saturación del cache, fallas en la integración con WhatsApp, errores masivos en una financiera, agotamiento de espacio en disco. Los runbooks se mantienen vivos: se actualizan cada vez que se aprende algo nuevo por un incidente real.

**10. Glosario técnico**

Términos técnicos utilizados a lo largo del documento, con su significado canónico para el proyecto.

**ADR**

Architecture Decision Record. Documento corto y estructurado que registra una decisión arquitectónica con su contexto, alternativas, decisión y consecuencias. En este proyecto los ADRs son inmutables una vez aprobados.

**Blue-green deployment**

Estrategia de despliegue con dos pools de instancias (azul y verde) que se alternan como pool activo. Permite cambio atómico de versión y rollback inmediato.

**C4 Model**

Notación para diagramas de arquitectura en cuatro niveles: Contexto, Contenedores, Componentes, Código. Solo se usan los tres primeros niveles en este documento.

**Canary deployment**

Despliegue progresivo en el que una parte del tráfico se dirige al nuevo deploy mientras el resto sigue al deploy anterior, escalando gradualmente.

**Discriminator column**

Patrón de multi-tenancy donde una columna (tenant_id) identifica al tenant dueño de cada fila. Todas las queries deben filtrar por esta columna.

**Event-driven**

Patrón de comunicación en el que componentes publican eventos al ocurrir cambios y otros componentes reaccionan asincrónicamente.

**Feature flag**

Mecanismo técnico que permite activar o desactivar una funcionalidad en producción sin redeploy, configurable por tenant, usuario o globalmente.

**HMAC**

Hash-based Message Authentication Code. Mecanismo de verificación de integridad y autenticidad de mensajes mediante una clave compartida. Usado para validar webhooks entrantes.

**Idempotencia**

Propiedad de una operación según la cual ejecutarla una o múltiples veces produce el mismo resultado. Esencial para webhooks y para garantizar consistencia ante reintentos.

**JWT**

JSON Web Token. Token compacto y firmado que transporta información de identidad y autorización del usuario. Usado como bearer token en la API.

**KMS**

Key Management Service. Servicio que gestiona claves de cifrado en infraestructura cloud, permitiendo cifrar datos sin exponer las claves a la aplicación.

**MFA / 2FA**

Multi-Factor Authentication / Two-Factor Authentication. Autenticación que requiere dos factores: algo que sabés (contraseña) y algo que tenés (TOTP en una app).

**OIDC**

OpenID Connect. Capa de identidad sobre OAuth2 que estandariza la autenticación y la entrega de claims del usuario.

**ORM**

Object-Relational Mapping. Capa que mapea entidades del lenguaje de programación a tablas relacionales. En este proyecto se utiliza SQLAlchemy 2.x.

**PII**

Personally Identifiable Information. Datos que permiten identificar a una persona física: nombre, DNI, CUIT, dirección, teléfono, email, fotos. Sujeta a Ley 25.326 en Argentina.

**Pydantic**

Biblioteca de validación de datos para Python basada en type hints. Núcleo de FastAPI.

**RLS**

Row-Level Security. Funcionalidad de PostgreSQL que aplica políticas de filtrado a nivel fila, transparente para el código aplicación.

**RPO / RTO**

Recovery Point Objective: pérdida máxima aceptable de datos en un incidente. Recovery Time Objective: tiempo máximo aceptable para recuperar el servicio.

**SLO / SLA**

Service Level Objective: objetivo interno de calidad del servicio. Service Level Agreement: compromiso contractual con el cliente sobre el SLO.

**Soft delete**

Eliminación lógica de un registro mediante una columna deleted_at, sin borrarlo físicamente. Permite reversión y trazabilidad.

**Trace ID**

Identificador único que correlaciona logs, métricas y trazas pertenecientes a una misma request a través de todos los componentes del sistema.

**UUID v7**

Identificador único universal versión 7. A diferencia de UUID v4, UUID v7 incluye un timestamp como prefijo, lo que permite ordenarlos cronológicamente y mejora la performance de inserciones en índices.
