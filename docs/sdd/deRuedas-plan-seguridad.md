**Plan de Seguridad**

**y Compliance**

***deRuedas Gestión***

Modelo de amenazas, controles, privacidad,

respuesta a incidentes y continuidad operativa

*Cumplimiento Ley 25.326 (AR) · Roadmap SOC 2 / ISO 27001*

Versión 1.0 — Mayo de 2026

**1. Introducción y propósito**

Este documento es complementario al cuerpo SDD de deRuedas Gestión y se ocupa de una dimensión que las cinco capas anteriores tocan tangencialmente pero no abordan de manera completa: la seguridad del producto, la privacidad de los datos que gestiona y el cumplimiento normativo aplicable. La Constitución declara principios como la confidencialidad de los datos del tenant, el aislamiento estricto entre tenants y la auditoría completa; el Plan estratégico identifica el cumplimiento de la Ley 25.326 como un requisito comercial; la Especificación Técnica define los controles RLS, el cifrado en reposo, el manejo de secretos. Pero esos contenidos están distribuidos y no constituyen por sí solos un plan accionable de seguridad. Este documento los consolida, los completa y los traduce en un programa operativo.

El documento existe por tres razones simultáneas. La primera es comercial: cuando deRuedas firme el primer contrato con una agencia mediana o grande, la contraparte va a exigir un infosec questionnaire, una política de privacidad publicable y, en algunos casos, un Data Processing Agreement (DPA). Llegar a esa conversación con respuestas estructuradas y documentadas, en lugar de improvisar, es la diferencia entre cerrar el contrato y perderlo. La segunda es regulatoria: Argentina tiene un régimen de protección de datos personales activo —Ley 25.326, Disposición 11/2006 y resoluciones derivadas— que aplica desde el momento en que se procesan datos de personas físicas, lo cual ocurre en el primer minuto de operación del producto. La tercera es operativa: la única manera de no convertir un incidente menor en una crisis existencial es tener procedimientos pensados de antemano, no inventados durante el incidente.

**1.1 Audiencia**

El documento tiene cuatro audiencias claramente diferenciadas. Para el equipo técnico interno —desarrolladores, SRE, responsable de seguridad— funciona como referencia normativa de qué controles deben implementarse, mantenerse y verificarse. Para el equipo comercial —Customer Success, ventas, dirección— funciona como insumo para responder consultas de clientes potenciales sobre seguridad, privacidad y compliance, y como base para los acuerdos contractuales con tenants. Para auditores externos —cuando se inicien procesos formales de certificación SOC 2 o ISO 27001— funciona como evidencia documental del programa de seguridad de la organización. Para autoridades regulatorias —en particular la Agencia de Acceso a la Información Pública en Argentina, AAIP— funciona como demostración de las medidas técnicas y organizativas adoptadas, exigidas por la normativa vigente.

**1.2 Alcance**

El alcance del documento abarca toda la superficie del producto deRuedas Gestión: el backend FastAPI con todos sus módulos de dominio, los frontends web/mobile/admin, la infraestructura cloud subyacente, las integraciones con servicios externos (WhatsApp Cloud API, portal deRuedas, gateways de pago futuros, Keycloak), los procesos internos de la organización deRuedas que tienen impacto en la seguridad de los datos del tenant, y la cadena de subprocessors y vendors. Quedan fuera de alcance los sistemas internos de las agencias clientes (sus propias bases de datos legacy, sus puntos de venta físicos, sus equipos personales): la frontera de responsabilidad termina en la API y los frontends provistos por deRuedas.

El documento describe el estado objetivo del programa al cierre de la Ola 1 del Plan de Implementación, momento en el cual deRuedas opera con sus primeras agencias early adopter. Hay controles que estarán plenamente implementados en ese punto, otros que se implementarán durante la Ola 1 misma, y otros que están explícitamente declarados como roadmap a doce o veinticuatro meses. Cada control declara su estado en una de tres categorías: implementado, en implementación, planificado.

**1.3 Estructura del documento**

El documento está organizado en doce secciones. Las primeras tres establecen la base conceptual: principios rectores, inventario de activos críticos y modelo de amenazas STRIDE. La sección 4 cataloga los controles técnicos que la implementación adopta, agrupados por familia. La sección 5 desarrolla la dimensión de privacidad y cumplimiento de la Ley 25.326, incluyendo el modelo de roles, los derechos de los titulares y las obligaciones contractuales con tenants y subprocessors. La sección 6 aborda la respuesta a incidentes con su taxonomía de severidad, sus runbooks y sus obligaciones de notificación. La sección 7 cubre la continuidad operativa con RTO y RPO declarados por componente. La sección 8 trata la seguridad del ciclo de desarrollo. La sección 9 trata la seguridad operativa y de personal. La sección 10 propone el roadmap de madurez del programa con hitos a SOC 2 Type I e ISO 27001. La sección 11 entrega plantillas de respuesta para infosec questionnaires de clientes. La sección 12 contiene los anexos: inventario de subprocessors, mapa de datos personales y glosario.

**1.4 Posición frente al cuerpo SDD**

Este documento no reemplaza ni contradice ninguna decisión del cuerpo SDD: lo extiende. Cuando hay solapamiento entre lo que dice este Plan de Seguridad y lo que dicen los documentos previos —por ejemplo, sobre las políticas RLS de PostgreSQL, o sobre el manejo de secretos cifrados, o sobre la auditoría append-only— este documento se limita a referenciar y a profundizar, sin reescribir la decisión. Cuando un control de seguridad requiere modificación de la arquitectura técnica que aún no está reflejada en el SDD, se declara explícitamente como propuesta de cambio que debe materializarse mediante un ADR posterior, nunca como decisión adoptada en sombra.

**2. Principios rectores y postura de seguridad**

Esta sección declara la postura de la organización frente a la seguridad: qué se prioriza cuando hay conflicto, qué se considera no negociable, qué nivel de riesgo se acepta. Estos principios son el filtro contra el cual cualquier decisión técnica u operativa posterior debe poder validarse.

**2.1 Principios**

**Principio S1 — Aislamiento entre tenants es no negociable**

Ningún tenant puede ver, modificar ni inferir información de otro tenant en circunstancias normales ni anormales. Esta propiedad se garantiza con tres capas de defensa simultáneas, no con una sola: políticas RLS de PostgreSQL aplicadas a toda tabla con tenant_id, dependencies de FastAPI que setean el contexto de tenant en cada request, y tests automatizados que verifican el aislamiento como parte del pipeline de CI bloqueante. La pérdida de aislamiento entre tenants es un incidente de severidad P0 y dispara notificación regulatoria a la AAIP en plazos definidos.

**Implicancia operativa:** Cualquier feature que requiera consultas cross-tenant —por ejemplo, métricas agregadas para el equipo interno de deRuedas, o catálogos compartidos como brands/models— debe declarar explícitamente en su ADR cómo preserva el aislamiento, qué tabla queda fuera de RLS y por qué, y cómo se audita su acceso.

**Principio S2 — Defensa en profundidad**

Ningún control de seguridad es la única línea de defensa. La autenticación falla con cierta probabilidad; la autorización también; el cifrado también; los controles humanos también. La postura adoptada asume que cada capa tendrá fallas y combina capas redundantes para que la falla simultánea sea improbable. En la práctica esto significa que la autenticación con JWT firmado por Keycloak coexiste con autorización por rol verificada en cada endpoint, que coexiste con RLS a nivel de base de datos, que coexiste con auditoría que detecta accesos anómalos. El costo es complejidad; el beneficio es que un único bug no compromete todo el sistema.

**Principio S3 — Mínimo privilegio por defecto**

Cualquier identidad —usuario, servicio, integración, sistema externo— recibe el mínimo conjunto de permisos necesario para cumplir su función. Los roles del producto (manager, salesperson, admin_staff, super_admin) están diseñados para no acumular permisos de manera ad hoc: cuando un permiso nuevo aparece, se asigna al rol más restrictivo que lo necesita y se concede a roles superiores explícitamente. El acceso de empleados de deRuedas a datos de tenants en producción está estrictamente regulado por procedimientos documentados en la sección 9, no es un acceso libre por el hecho de tener credenciales privilegiadas.

**Principio S4 — Auditabilidad completa de operaciones sensibles**

Toda operación que afecte datos del tenant, configuración del tenant, secretos, identidades o accesos privilegiados deja huella en una bitácora append-only que registra qué se hizo, quién lo hizo, cuándo, desde dónde y, cuando aplica, qué cambió. La bitácora no puede modificarse retroactivamente desde el rol de aplicación: las tablas relevantes tienen revocados UPDATE y DELETE para el rol de aplicación. Las consultas a la bitácora también dejan huella, especialmente las que un empleado de deRuedas realiza sobre datos de un tenant.

**Principio S5 — Cifrado por defecto**

Los datos en tránsito se cifran con TLS 1.2+; las conexiones HTTP planas no son aceptables ni siquiera entre componentes internos. Los datos en reposo se cifran a nivel de almacenamiento (volúmenes, buckets, base de datos). Los secretos —API keys de integraciones de tenants, passwords de servicios, credenciales de webhooks— se cifran con clave maestra y nunca aparecen en claro en código fuente, logs, dumps de base de datos o backups. Cualquier excepción a este principio —por ejemplo, una integración legacy que solo soporta HTTP— requiere ADR específico que justifique la decisión, declare el riesgo residual y plantee plan de remediación.

**Principio S6 — Privacidad por diseño**

Las funcionalidades del producto se diseñan asumiendo que los datos personales de los contactos y leads de las agencias son sensibles y están bajo el régimen legal argentino. Esto significa que se recolecta el mínimo necesario, que se purga lo que ya no se necesita según política de retención, que se permite a los titulares ejercer derechos ARCO mediante mecanismos automatizados o semiautomatizados, y que cualquier nuevo flujo de datos —especialmente uno que cruce fronteras geográficas o que comparta datos con terceros— se evalúa explícitamente para impacto en privacidad antes de implementarse.

**Principio S7 — Resiliencia y degradación elegante**

Ningún componente externo es asumido como siempre disponible. El portal deRuedas puede estar caído; WhatsApp Cloud API puede tener rate limit; Keycloak puede estar lento; S3 puede tener un incidente regional. El producto debe degradarse de manera elegante en estos escenarios: cachear lo cacheable, encolar lo encolable, mostrar al usuario información clara sobre lo que no está disponible temporalmente y, sobre todo, no comprometer la integridad de los datos del tenant durante la indisponibilidad. Los mecanismos concretos —retries con backoff, dead-letter queues, idempotencia, circuit breakers— se especifican en la sección 4.

**Principio S8 — Transparencia con clientes y usuarios**

Cuando ocurre un incidente que afecta datos o disponibilidad del tenant, deRuedas comunica de manera proactiva, oportuna y honesta. La política es informar a los tenants afectados dentro de plazos definidos en la sección 6, no esperar a que pregunten. Se evita el lenguaje vacío del tipo “estamos investigando una incidencia” cuando ya hay información concreta, y también se evita el lenguaje exagerado del tipo “ataque sofisticado” cuando se trata de un error de configuración. El estándar de comunicación es el de un postmortem público: qué pasó, cuándo, qué impacto tuvo, qué se está haciendo, qué se va a cambiar.

**2.2 Postura de riesgo**

El programa de seguridad de deRuedas opera con una postura de riesgo conservadora pero pragmática. La organización no es un banco ni un proveedor de salud, lo que significa que ciertos controles ultraconservadores —segregación física de redes, evaluaciones forenses tras cada login, auditorías trimestrales independientes— están fuera del alcance económico del MVP y no aportan valor proporcional al riesgo. Pero tampoco es un producto de bajo riesgo: maneja datos personales identificables de cientos de personas por agencia (clientes y prospects), datos comerciales sensibles (precios, márgenes, inventario), comunicaciones por canales privados (WhatsApp), y credenciales de integraciones que un atacante podría usar lateralmente. La postura adoptada se ubica en lo que la industria llama nivel de seguridad medio-alto para SaaS B2B vertical: controles maduros para los riesgos materiales, ausencia justificada de controles ultra-conservadores que no aplican.

**2.3 Apetito y aceptación de riesgo**

Hay riesgos que el programa acepta explícitamente como tolerables y declara las razones de la aceptación. Esta lista se revisa cada seis meses y los cambios se aprueban por la dirección.

|  |  |  |
|:---|:---|:---|
| **Riesgo aceptado** | **Razón de la aceptación** | **Revisión** |
| Single-region cloud durante el MVP | El costo de multi-region activo-activo es superior al impacto esperado de un incidente regional de proveedor cloud, dada la base de clientes inicial. RTO 4h con restore desde backup en otra región es aceptable. | 12 meses |
| Sin certificación SOC 2 ni ISO 27001 en MVP | El proceso formal toma 12-18 meses y requiere madurez operativa que se construye durante la Ola 1. Roadmap declarado en sección 10. | 12 meses |
| Sin programa formal de bug bounty | Costo y ruido alto para el tamaño del producto. Se opera con responsible disclosure por canal de seguridad. | 18 meses |
| Backups con retención 30 días, no años | Para la mayoría de los datos, la pérdida más allá de 30 días es operativamente aceptable y los costos de retention prolongada son significativos. Excepciones para audit_logs (24 meses) y datos contables (10 años cuando aplique en olas posteriores). | 12 meses |
| Acceso de empleados de deRuedas a datos de tenants en producción mediante just-in-time access manual, no automatizado por sistema dedicado | El volumen de operaciones es bajo durante el MVP y un sistema PAM (Privileged Access Management) dedicado es overkill. El procedimiento manual con auditoría obligatoria es suficiente y se automatizará al crecer. | 12 meses |
| Sin DPO formal certificado | La normativa argentina no exige DPO certificado para este perfil de empresa. Se designa responsable interno con funciones equivalentes, declarado en sección 5. | 24 meses |

**2.4 Modelo de responsabilidad compartida**

La seguridad del sistema es resultado de la suma de responsabilidades de varios actores. El siguiente cuadro distribuye explícitamente quién es responsable de qué, evitando zonas grises donde un actor asume que otro lo cubre.

|  |  |  |  |  |
|:---|:---|:---|:---|:---|
| **Capa** | **Cloud provider** | **deRuedas** | **Tenant** | **Usuario final** |
| Hardware y datacenters | Total | — | — | — |
| Hipervisor y VMs | Total | — | — | — |
| Sistema operativo de servidores | Compartida | Compartida | — | — |
| Red interna VPC y firewalls | Provee primitivas | Configura | — | — |
| Cifrado en reposo de almacenamiento | Provee KMS y EBS encryption | Configura uso correcto | — | — |
| Cifrado en tránsito TLS | Provee LB con TLS termination | Configura cert y políticas | — | — |
| Aplicación deRuedas Gestión (código) | — | Total | — | — |
| Configuración del tenant | — | Provee defaults seguros | Configura sus opciones | — |
| Identidades de usuarios del tenant | — | Provee auth e MFA opcional | Gestiona altas/bajas/roles | Custodia sus credenciales |
| Datos cargados en el tenant | — | Custodia segura | Decide qué se carga, calidad | — |
| Credenciales de integraciones (WhatsApp, etc.) | — | Cifrado y custodia | Genera y rota cuando corresponde | — |
| Equipos personales (laptops, móviles) que acceden | — | Provee app segura | Define política interna | Mantiene su equipo |
| Sesiones de usuario | — | Provee mecanismo seguro | — | Usa MFA, no comparte |

**Comunicación a tenants:** Esta tabla forma parte del DPA y del manual de usuario. Es explícita con los tenants para evitar la ambigüedad común del SaaS donde el cliente cree que la responsabilidad por todo es del proveedor.

**3. Inventario de activos críticos**

La protección efectiva exige antes que nada saber qué se está protegiendo. Esta sección cataloga los activos relevantes del sistema, los clasifica por sensibilidad y declara para cada uno quién es propietario, qué impacto tendría su compromiso y qué controles base lo protegen. El inventario se mantiene vigente mediante revisiones semestrales y se actualiza cada vez que un cambio arquitectónico introduce un activo nuevo o modifica significativamente uno existente.

**3.1 Esquema de clasificación**

Los activos se clasifican según el modelo de tres ejes: confidencialidad, integridad y disponibilidad. Cada eje se evalúa en una escala discreta de tres niveles: bajo, medio y alto. La combinación produce una clasificación global que determina qué controles aplican.

|  |  |
|:---|:---|
| **Nivel** | **Significado** |
| Bajo | Información pública o cuya pérdida tiene impacto operativo limitado y reversible. No exige controles especiales más allá de los del producto. |
| Medio | Información sensible cuyo compromiso afecta a un tenant o a deRuedas pero no implica daño masivo ni obligación regulatoria. Exige controles estándar: cifrado, control de acceso por rol, auditoría. |
| Alto | Información cuyo compromiso implica daño material a personas, obligación legal de notificación o riesgo existencial para la organización. Exige controles reforzados: cifrado de campo cuando aplica, acceso just-in-time auditado, retention restrictiva, monitoreo proactivo. |

**3.2 Catálogo de activos**

Se distinguen cinco familias de activos: datos del producto, credenciales y secretos, infraestructura, código y propiedad intelectual, identidades. La tabla siguiente lista los activos materiales con su clasificación, propietario y referencia a los controles que los protegen.

**3.2.1 Datos del producto**

|  |  |  |  |  |
|:---|:---|:---|:---|:---|
| **Activo** | **Conf.** | **Integ.** | **Disp.** | **Notas y propietario** |
| Datos personales de contactos del tenant (nombre, teléfono, email, DNI opcional) | Alto | Alto | Medio | Bajo Ley 25.326. Propietario: el tenant. deRuedas es encargado del tratamiento. |
| Datos personales de leads (incluye contact + interés y comunicaciones) | Alto | Alto | Medio | Igual marco que contactos. |
| Conversaciones de WhatsApp (mensajes + adjuntos) | Alto | Alto | Medio | Especialmente sensibles por contener comunicaciones privadas potencialmente con datos de salud, financieros o familiares incidentales. |
| Inventario de vehículos (stock completo del tenant) | Medio | Alto | Alto | Datos comerciales sensibles para el tenant pero no sensibles bajo ley AR. |
| Histórico de operaciones de venta y márgenes | Alto | Alto | Medio | Información competitiva del tenant. En MVP, márgenes no se calculan; el activo aplica plenamente desde Olas posteriores. |
| Configuración del tenant (sucursales, pipeline, integraciones) | Medio | Alto | Alto | Compromiso de integridad puede romper la operación; compromiso de confidencialidad expone estructura interna. |
| Métricas y dashboards agregados del tenant | Medio | Medio | Medio | Valor analítico, sensibilidad menor que datos crudos. |
| audit_logs (bitácora de auditoría) | Alto | Alto | Alto | Pieza forense crítica. Append-only por diseño. |
| Catálogo de marcas/modelos/versiones (cross-tenant) | Bajo | Medio | Alto | Información pública que no exige confidencialidad pero cuya integridad afecta a todos los tenants si se corrompe. |

**3.2.2 Credenciales y secretos**

|  |  |  |  |  |
|:---|:---|:---|:---|:---|
| **Activo** | **Conf.** | **Integ.** | **Disp.** | **Notas y propietario** |
| API keys de integraciones del tenant (deRuedas portal, WhatsApp, etc.) | Alto | Alto | Alto | Cifrados por tenant con clave maestra. El tenant puede rotar; deRuedas no puede leerlas en claro fuera del momento de uso. |
| Passwords de usuarios del tenant | Alto | Alto | Alto | Hasheados con argon2id en Keycloak. deRuedas no tiene acceso al hash. |
| Refresh tokens y JWT firmados | Alto | Alto | Alto | Vida corta; rotation automática; revocable. |
| Webhook verify tokens | Alto | Alto | Alto | Cifrados por tenant. Comprometidos = posible spoofing de webhooks. |
| Master encryption key (KMS) | Alto | Alto | Alto | Clave raíz de cifrado de secretos. Bajo control de cloud provider KMS o HSM. |
| Credenciales de servicios internos (DB, Redis, MinIO/S3) | Alto | Alto | Alto | Gestionadas por secret manager del proveedor cloud. |
| Tokens de admin de Keycloak | Alto | Alto | Alto | Acceso administrativo crítico al sistema de identidad. |
| Credenciales de empleados de deRuedas (SSO, VPN, sudo) | Alto | Alto | Alto | MFA obligatoria; auditadas; revocables al instante. |

**3.2.3 Infraestructura**

|  |  |  |  |  |
|:---|:---|:---|:---|:---|
| **Activo** | **Conf.** | **Integ.** | **Disp.** | **Notas y propietario** |
| Cluster PostgreSQL primary + replicas | Alto | Alto | Alto | Persistencia de toda la data. Backup diario a otra región. |
| Redis (cache + streams + idempotencia) | Medio | Alto | Alto | Memoria volátil pero crítica operativamente. Persistencia AOF habilitada. |
| OpenSearch index | Bajo | Medio | Medio | Reconstruible desde PostgreSQL en caso de pérdida total. |
| Object storage (S3 / MinIO) para fotos y documentos | Medio | Alto | Alto | Inmutabilidad versionada habilitada. |
| Cluster de aplicación (containers backend, frontend, workers) | Medio | Alto | Alto | Stateless; reconstruible desde imágenes. |
| Pipeline CI/CD y registry de imágenes | Alto | Alto | Medio | Compromiso permite supply-chain attacks. Firmas obligatorias. |
| Sistema de observabilidad (Prometheus, Grafana, Loki, Sentry) | Medio | Medio | Alto | Crítico para detectar incidentes; comprometerlo es perder visibilidad. |
| DNS y certificados TLS | Bajo | Alto | Alto | Comprometer DNS = potencial MITM masivo. |

**3.2.4 Código, propiedad intelectual y procesos**

|  |  |  |  |  |
|:---|:---|:---|:---|:---|
| **Activo** | **Conf.** | **Integ.** | **Disp.** | **Notas y propietario** |
| Código fuente del producto | Medio | Alto | Medio | Repositorio privado con branch protection y signed commits. |
| Documentación técnica (cuerpo SDD) | Bajo | Medio | Medio | Versión interna sensible; versión pública sanitizada para clientes. |
| Modelos de datos y schemas de base | Medio | Alto | Alto | Cambios mediante migrations versionadas y revisadas. |
| Configuración de infraestructura como código (Terraform) | Medio | Alto | Medio | Cambios mediante pull requests revisados; state cifrado. |

**3.2.5 Identidades**

|  |  |  |  |  |
|:---|:---|:---|:---|:---|
| **Activo** | **Conf.** | **Integ.** | **Disp.** | **Notas y propietario** |
| Identidades de usuarios finales del tenant en Keycloak | Alto | Alto | Alto | Sincronizadas con la tabla users del backend; gestionadas por el manager del tenant. |
| Identidades de empleados de deRuedas en SSO interno | Alto | Alto | Alto | Provider externo (Google Workspace, Okta o equivalente). MFA forzada. |
| Identidades de servicios y workloads (service accounts) | Alto | Alto | Alto | Credenciales rotables; vinculadas a roles IAM mínimos. |

**3.3 Mapa de datos personales (resumen)**

La sección 12 contiene el mapa completo de datos personales (data map) requerido por la normativa. A modo de resumen ejecutivo, los datos personales identificables que el sistema procesa son los siguientes.

- Datos de identificación: nombre completo, DNI opcional, fecha de nacimiento opcional. Procesados para identificar contactos y leads.

- Datos de contacto: teléfono primario, teléfono alternativo, email, dirección postal. Procesados para comunicación comercial dentro del marco de relación con la agencia.

- Datos de comunicación: contenido textual y multimedia de mensajes intercambiados vía WhatsApp con la agencia. Pueden contener incidentalmente datos sensibles que el titular comparte (financieros, familiares, salud) sin que el sistema los solicite.

- Datos comerciales: histórico de leads, vehículos consultados, valores estimados, motivos de pérdida. Asociados a la persona pero no en sí mismos personales bajo Ley 25.326.

- Metadatos técnicos: timestamps, IPs (logueadas en audit_logs), user agents. Tratados como datos personales asociados al usuario.

**Datos sensibles bajo art. 7 de la Ley 25.326:** El sistema no recolecta intencionalmente datos sensibles (origen racial, opiniones políticas, convicciones religiosas, sindicales, salud, vida sexual). Cuando incidentalmente aparezcan en conversaciones de WhatsApp, se aplican las protecciones generales sin tratamiento especial. La política de uso aceptable del producto, que las agencias firman, prohíbe su solicitud sistemática.

**4. Modelo de amenazas**

Esta sección aplica el método STRIDE de Microsoft al sistema deRuedas Gestión. STRIDE es el acrónimo de seis categorías de amenazas: Spoofing (suplantación de identidad), Tampering (manipulación de datos), Repudiation (negación de actos), Information Disclosure (divulgación de información), Denial of Service (denegación de servicio) y Elevation of Privilege (escalada de privilegios). El método se aplica recorriendo cada componente del sistema y preguntando, para cada categoría, qué amenazas son plausibles, qué controles las mitigan y cuál es el riesgo residual.

Para mantener el documento operativo y no convertirlo en un ejercicio académico interminable, se prioriza la profundidad sobre la cobertura: se analizan en detalle los componentes con mayor superficie de ataque y mayor exposición de activos críticos, y se cubren más superficialmente los demás. Las superficies analizadas en detalle son: la API pública, los webhooks entrantes, la base de datos PostgreSQL, el sistema de eventos, la sesión de usuario y los flujos de autenticación. Las superficies cubiertas con menor profundidad son: el portal del backoffice administrativo de deRuedas, las integraciones salientes con terceros y el pipeline de CI/CD.

**4.1 Actores y su capacidad asumida**

El modelo asume actores concretos con capacidades específicas en lugar de un atacante abstracto omnipotente. Esto evita controles de paranoia que no aportan valor y permite priorizar los controles que sí cierran amenazas materiales.

|  |  |
|:---|:---|
| **Actor** | **Capacidades asumidas y motivación** |
| Atacante externo no dirigido | Scans automatizados, intentos de explotación masiva de vulnerabilidades conocidas, credential stuffing con bases de datos filtradas. Sin conocimiento específico del producto. |
| Atacante externo dirigido | Reconocimiento previo del producto y del cliente. Capaz de spear phishing a empleados, de pagar por accesos, de explotar zero-days conocidas en dependencias. Motivación: obtener datos para reventa, ransomware, daño reputacional. |
| Tenant malicioso (insider del producto) | Cliente legítimo de deRuedas que intenta acceder a datos de otros tenants explotando bugs de aislamiento. Capacidades: cualquier interacción legítima con la API; inyección en campos de texto; manipulación de tokens propios. Motivación: espionaje competitivo. |
| Empleado del tenant deshonesto | Vendedor o admin staff de una agencia que abusa de sus permisos legítimos para extraer datos antes de irse a la competencia. No es estrictamente atacante: es comportamiento humano frecuente que el producto debe poder rastrear y limitar. |
| Empleado de deRuedas deshonesto o comprometido | Acceso privilegiado a infraestructura. Motivación variable: extorsión, soborno externo, error tras compromiso de cuenta personal. Es el escenario menos probable pero más dañino. |
| Subprocessor comprometido | Vendor de cadena (cloud provider, Keycloak managed, S3 provider, observability vendor) sufre incidente que impacta deRuedas. Motivación: no aplica (es vector indirecto). |
| Error humano interno | Empleado de deRuedas o tenant comete un error operativo: borra una tabla, expone un bucket, pega un secreto en un canal público. No es malicioso pero produce los mismos efectos que un ataque. |

**4.2 Diagrama lógico del flujo de datos**

El modelo usa el siguiente diagrama lógico como referencia. Las fronteras de confianza están marcadas con líneas dobles y son los puntos donde STRIDE se aplica con mayor rigor: ahí es donde un input no confiable cruza al dominio de control de la organización.

┌──────────────────┐

│ Usuario final │

│ (browser/móvil) │

└────────┬─────────┘

│ HTTPS

╔══════════════════╪═══════════════════════╗

║ FRONTERA DE CONFIANZA: borde público ║

╚══════════════════╪═══════════════════════╝

▼

┌──────────────────────────────────────────────────┐

│ CDN / WAF / Load Balancer (TLS termination) │

└────────────────────────┬─────────────────────────┘

│

┌────────────┬──────────┼──────────┬──────────────┐

▼ ▼ ▼ ▼ ▼

┌─────────┐ ┌─────────┐ ┌──────┐ ┌──────────┐ ┌─────────┐

│ Next.js │ │ FastAPI │ │ Web │ │ Webhooks │ │ Admin │

│ web │ │ API │ │ SSE │ │ entrantes│ │ backoff │

└─────────┘ └────┬────┘ └──────┘ └────┬─────┘ └────┬────┘

│ │ │

▼ ▼ │

┌─────────┐ ┌─────────┐ │

│ Keycloak│ │ HMAC │ │

│ (JWT) │ │ verify │ │

└────┬────┘ └────┬────┘ │

│ │ │

└───────────┬───────────┘ │

│ │

╔══════════════╪══════════════════════╗ │

║ FRONTERA: tenant context required ║ │

╚══════════════╪══════════════════════╝ │

▼ ▼

┌──────────────────────────────────────────────────────┐

│ Capa de servicios de dominio (Stock, CRM, ...) │

└────┬──────────────┬────────────┬──────────┬──────────┘

│ │ │ │

▼ ▼ ▼ ▼

┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐

│PostgreSQL│ │ Redis │ │OpenSearch│ │ Storage │

│ + RLS │ │ Streams │ │ index │ │ (S3-comp)│

└──────────┘ └────┬─────┘ └─────────┘ └──────────┘

│

▼

┌──────────┐

│ Workers │

│ (Celery) │

└────┬─────┘

│

╔══════╪═══════════════════════════╗

║ FRONTERA: salida a terceros ║

╚══════╪═══════════════════════════╝

▼

┌──────────────────────────────────────────────┐

│ WhatsApp Cloud API · Portal deRuedas │

│ Email SMTP · Cloud KMS │

└──────────────────────────────────────────────┘

**4.3 Análisis STRIDE por superficie**

**4.3.1 API pública (FastAPI)**

**Activos expuestos:** datos del producto, sesiones, secretos del tenant a través de operaciones autorizadas

**Exposición:** Internet, accesible desde cualquier IP

**Frontera de confianza:** todo input es no confiable hasta validar JWT y schema Pydantic

|  |  |  |
|:---|:---|:---|
| **Categoría** | **Amenaza** | **Mitigación** |
| S — Spoofing | Atacante presenta JWT falsificado o robado para suplantar a un usuario. | JWT firmado con clave privada Keycloak; validación de firma en cada request; vida corta del access token (15 min); refresh con rotación; logout invalida refresh; detección de uso anómalo (IP nueva, geo distinto). |
| S — Spoofing | Atacante intercepta token vía MITM en red insegura. | TLS 1.2+ obligatorio; HSTS con max-age largo; certificate pinning en clientes móviles. |
| T — Tampering | Atacante modifica payload JSON en POST/PATCH para alterar campos restringidos (ej. tenant_id). | Schema Pydantic estricto rechaza campos extra; tenant_id nunca es campo de entrada, se infiere del JWT; campos restringidos se validan en service. |
| T — Tampering | SQL injection a través de filtros de búsqueda o parámetros. | ORM SQLAlchemy con bindings parametrizados; queries crudas requieren ADR específico; tests de SAST detectan strings concatenados peligrosos. |
| R — Repudiation | Usuario realiza una operación sensible y luego niega haberla hecho. | audit_logs append-only registra: trace_id, user_id, ip, user_agent, action, before/after; revoke UPDATE/DELETE al rol app sobre la tabla; firma cryptográfica del audit como evolución futura. |
| I — Info Disclosure | Endpoint devuelve más información de la necesaria por mal diseño de schemas. | Schemas Read explícitamente listan campos publicados; campos internal_notes solo a roles autorizados; tests verifican que LeadRead no incluye datos de otro tenant ni campos restringidos. |
| I — Info Disclosure | Mensajes de error filtran información (ej. 'usuario no existe' vs 'password incorrecta'). | Mensajes genéricos de auth ('credenciales inválidas'); 404 en vez de 403 cuando se intenta acceder a recurso de otro tenant para no filtrar existencia; trace_id en errores 500 sin stack trace al cliente. |
| I — Info Disclosure | Logs filtran PII o secretos a Loki/Sentry. | Logger custom enmascara campos marcados como secret/PII; tests automáticos buscan patterns de DNI, teléfonos, tokens en outputs de logs en CI. |
| D — DoS | Atacante satura la API con requests para tirar el servicio. | Rate limiting por IP en LB/CDN (configurable, default 100 req/s por IP); rate limit por user en endpoints sensibles (ej. login: 10/min); circuit breaker en queries pesadas; queue management con prioridades. |
| D — DoS | Atacante envía payload gigantesco para agotar memoria. | max_body_size configurado en FastAPI (10MB para JSON, 50MB para multipart); rechazo temprano antes de parsing. |
| E — Elev. Priv. | Atacante con cuenta salesperson logra ejecutar acciones de manager (ej. eliminar usuarios). | Validación de rol en cada endpoint con dependency require_role; tests automáticos por rol que verifican qué endpoints están accesibles; auditoría de accesos negados. |
| E — Elev. Priv. | Tenant malicioso explota bug de aislamiento para acceder a datos de otro tenant. | Defensa en tres capas: tenant_id implícito de JWT en service layer, RLS en PostgreSQL, tests automáticos de aislamiento bloqueantes en CI. Es el caso más crítico, ver Principio S1. |

**4.3.2 Webhooks entrantes**

**Activos expuestos:** conversaciones de WhatsApp, payloads enviados sin auth previa por terceros

**Exposición:** Internet, sin sesión de usuario

**Frontera de confianza:** el webhook llega de un tercero (Meta) y no de un usuario autenticado; verificación HMAC obligatoria

|  |  |  |
|:---|:---|:---|
| **Categoría** | **Amenaza** | **Mitigación** |
| S — Spoofing | Atacante envía webhook falso simulando ser Meta para inyectar mensajes en una conversación. | Verificación HMAC SHA256 con app_secret de Meta; rechazo 401 si firma no coincide; logging de cada intento fallido. |
| T — Tampering | Atacante intercepta webhook y modifica payload (MITM). | Solo se aceptan webhooks vía HTTPS; HMAC también garantiza integridad; rechazo si HMAC no valida. |
| R — Repudiation | Operador interno niega haber procesado un mensaje recibido. | Persistencia inmediata del mensaje + wa_message_id único; idempotencia por wa_message_id; reconciliación periódica con Meta. |
| I — Info Disclosure | Endpoint del webhook expone información en respuesta de error que ayuda al atacante. | Response 200 OK siempre que la firma sea válida (incluso si payload tiene problemas internos), procesamiento async; respuestas 401 sin información sobre por qué falló la validación. |
| D — DoS | Atacante envía millones de webhooks falsos para saturar. | Rate limit en LB; rechazo barato (HMAC validation antes de cualquier operación pesada); aislamiento de pool de workers para no afectar API principal. |
| E — Elev. Priv. | Atacante envía webhook con datos manipulados para crear contacto en tenant ajeno. | Resolución de tenant a partir de phone_number_id que está en el sistema; el atacante no puede inventar phone_number_id ajenos válidos sin comprometer también la cuenta Meta del tenant. |

**4.3.3 Base de datos PostgreSQL**

**Activos expuestos:** TODOS los datos del producto

**Exposición:** red privada VPC, no expuesta a Internet

**Frontera de confianza:** el rol de aplicación es semi-confiable; el rol de superusuario es restringido a operaciones administrativas auditadas

|  |  |  |
|:---|:---|:---|
| **Categoría** | **Amenaza** | **Mitigación** |
| S — Spoofing | Atacante con acceso a la red privada se conecta como rol app robando credenciales. | Credenciales en secret manager con rotación automática trimestral; conexión solo desde IPs de la subnet de aplicación; logs de conexión auditados. |
| T — Tampering | Atacante modifica datos directamente en BD evitando la capa de servicios. | Acceso directo a producción solo con just-in-time access (sección 9); cambios masivos requieren migration revisada o ticket aprobado; auditoría de queries DDL/DML manuales. |
| T — Tampering | Atacante corrompe audit_logs para borrar evidencia. | audit_logs particionada con UPDATE/DELETE revocados al rol app; solo superuser puede modificar (operación auditada); plan futuro: hash chain entre filas para detección de tampering retroactivo. |
| R — Repudiation | DBA niega haber ejecutado una query manual. | Toda sesión de DBA via gateway que registra cada query con identidad; rotación de credenciales después de uso just-in-time; reportes mensuales de actividad administrativa. |
| I — Info Disclosure | Backup queda en bucket sin cifrar y termina expuesto. | Cifrado en reposo del bucket de backups (KMS managed key); ACLs estrictas (no public); rotation de keys; tests automáticos verifican configuración del bucket. |
| I — Info Disclosure | Read replica en otra región no tiene RLS aplicado y atacante con acceso a la replica lee data cross-tenant. | RLS está activo en el cluster completo (primary + replicas); tests verifican replicas también; replicas usan mismas políticas. |
| D — DoS | Query mal optimizada por usuario con permisos legítimos colapsa la BD. | Query timeout de 30s configurado a nivel de pool; alertas de queries lentas vía pg_stat_statements; circuit breaker en API si BD no responde. |
| E — Elev. Priv. | Bug en RLS o falta de RLS en una tabla expone aislamiento. | Test introspectivo en CI que recorre pg_policies y verifica que toda tabla con tenant_id tiene política activa; revisión obligatoria de policy en code review de migrations. |

**4.3.4 Sistema de eventos (Redis Streams)**

**Activos expuestos:** eventos de dominio que pueden contener datos personales en payload

**Exposición:** red privada

|  |  |  |
|:---|:---|:---|
| **Categoría** | **Amenaza** | **Mitigación** |
| S — Spoofing | Worker malicioso publica eventos falsos. | Solo backend autenticado publica al stream; Redis con auth obligatoria; ACLs por usuario. |
| T — Tampering | Atacante con acceso a Redis modifica eventos en flight. | Acceso solo desde subnet privada; auditoría de comandos de mantenimiento. |
| R — Repudiation | Sistema niega haber publicado un evento o un consumer niega haberlo procesado. | event_id único, event_type, occurred_at; tabla processed_events del lado consumer; logs estructurados de cada publicación y consumo con trace_id. |
| I — Info Disclosure | Eventos con payloads que incluyen datos personales son visibles en la consola Redis. | Acceso a Redis estrictamente restringido; logs no incluyen payload completo; payload sanitizado para audit. |
| D — DoS | Productor inunda el stream y los consumers no procesan a tiempo. | MAXLEN configurado por stream para limitar memoria; alertas de queue lag; backpressure controlado. |
| E — Elev. Priv. | Consumer de un módulo procesa eventos de otro indebidamente. | Consumer registra explícitamente qué event_types acepta; el publisher no puede forzar que sea procesado por consumer ajeno. |

**4.3.5 Sesión de usuario y autenticación**

**Activos expuestos:** credenciales, sesión activa, capacidad de actuar como un usuario

**Frontera de confianza:** la sesión es la base de toda la autorización posterior

|  |  |  |
|:---|:---|:---|
| **Categoría** | **Amenaza** | **Mitigación** |
| S — Spoofing | Phishing roba credenciales del manager de un tenant. | MFA opcional para users regulares pero obligatoria para manager y super_admin; capacitación a tenants vía manual de usuario; alertas al user de logins desde dispositivos nuevos. |
| S — Spoofing | Credential stuffing usando bases de datos filtradas. | Detección de IPs con muchos intentos fallidos; bloqueo temporal exponencial (5min, 30min, 24h, permanente); password policy con check contra haveibeenpwned al setear. |
| T — Tampering | Atacante manipula su propio JWT (cambiar tenant_id, role). | JWT firmado; modificación rompe firma; rechazo automático. |
| R — Repudiation | Usuario niega haber hecho login desde IP X. | Log de cada login con IP, user_agent, geolocalización aproximada, fingerprint del browser; usuario puede consultar su histórico desde su perfil. |
| I — Info Disclosure | Cookie de sesión es accesible vía XSS. | Cookies HttpOnly + Secure + SameSite=Lax; CSP que restringe inline scripts; sanitización de inputs en frontend. |
| D — DoS | Bot intenta crear millones de cuentas. | El producto no permite signup público en MVP (ver Plan estratégico); las cuentas se crean por invitación. CAPTCHA en flujos públicos como reset password si crece el volumen. |
| E — Elev. Priv. | Usuario logra cambiar su rol mediante manipulación de profile. | Cambio de rol solo por endpoint admin con role manager o superior; valor del role nunca se setea desde input directo del usuario sobre sí mismo. |

**4.4 Análisis abreviado de superficies secundarias**

**4.4.1 Backoffice administrativo de deRuedas**

Aplicación interna usada por Customer Success y super admin para gestionar tenants. Mismo modelo de auth que el producto principal pero requiere rol super_admin verificable también vía SSO interno con MFA forzada. Acceso restringido por IP allowlist a oficinas y VPN. Cada acción sobre un tenant queda registrada en audit_logs cross-tenant. Las amenazas predominantes son insider threat y compromiso de cuenta de empleado: el control central es la combinación de MFA + JIT access + auditoría obligatoria + revisión semanal de logs.

**4.4.2 Integraciones salientes (WhatsApp, deRuedas portal, email)**

El sistema actúa como cliente. Las amenazas relevantes son: indisponibilidad del proveedor (DoS sobre nosotros), credenciales comprometidas que permiten enviar a nombre de un tenant, y MITM en la conexión saliente. Las mitigaciones son: TLS obligatorio con verificación de cert; credenciales por tenant cifradas y rotadas; circuit breakers que protegen al producto cuando un proveedor está inestable; reconciliación periódica para detectar mensajes no enviados o no recibidos correctamente.

**4.4.3 Pipeline de CI/CD y supply chain**

La cadena de build es target valioso: comprometerla permite inyectar código malicioso que llega a producción firmado. Las mitigaciones son: branch protection que exige reviews y CI verde antes de merge; signed commits opcionales (obligatorios desde Ola 2); SBOM generado en cada build; scanning de dependencias (pip-audit, npm audit, Trivy para imágenes) bloqueante para vulnerabilidades críticas; imágenes firmadas con cosign almacenadas en registry privado; deploy solo desde imágenes firmadas y verificadas. La cuenta de servicio de CI tiene permisos mínimos en el cloud y se rota.

**4.5 Matriz de riesgos materiales**

La siguiente matriz consolida los riesgos más críticos del análisis anterior, los pondera por probabilidad e impacto, y declara la disposición actual.

|  |  |  |  |  |
|:---|:---|:---|:---|:---|
| **Riesgo** | **Probabilidad** | **Impacto** | **Riesgo neto** | **Disposición** |
| Pérdida de aislamiento entre tenants por bug | Baja | Crítico | Alto | Mitigación reforzada (3 capas + tests) |
| Compromiso de credencial de empleado deRuedas con privilegios | Media | Crítico | Alto | Mitigación reforzada (MFA + JIT + audit) |
| Filtración de PII vía logs o backups expuestos | Baja | Alto | Medio | Mitigación adecuada |
| Indisponibilidad prolongada por incidente cloud regional | Media | Alto | Medio | Aceptado con plan de DR a 4h RTO |
| Credenciales del tenant para integraciones expuestas | Baja | Alto | Medio | Mitigación adecuada (cifrado por tenant) |
| Phishing exitoso a manager de un tenant | Media | Medio | Medio | Mitigación parcial (MFA opcional → forzada) |
| Inyección masiva via webhook falsificado | Baja | Medio | Bajo | Mitigación adecuada (HMAC) |
| DoS volumétrico desde Internet | Baja | Medio | Bajo | Mitigación parcial vía CDN/WAF |
| Supply chain attack vía dependencia comprometida | Baja | Alto | Medio | Mitigación parcial (escaneo + SBOM) |
| Insider threat de empleado tenant que extrae datos antes de irse | Media | Bajo | Bajo | Mitigación basada en auditoría y exportes limitados |

**Revisión:** Esta matriz se revisa cada seis meses por el responsable de seguridad y se actualiza ante cualquier cambio significativo en arquitectura, escala o panorama de amenazas. Los riesgos cuyo neto suba a Alto disparan revisión de controles dentro de 30 días.

**5. Catálogo de controles técnicos**

Esta sección cataloga los controles técnicos que el sistema implementa para mitigar las amenazas identificadas en la sección 4. Los controles están agrupados por familia funcional y cada uno declara identificador, severidad de los riesgos que mitiga, estado actual de implementación, anclaje al cuerpo SDD donde corresponde y evidencia esperable de que el control está funcionando. La columna de estado utiliza tres valores: implementado, en implementación (durante la Ola 1) y planificado (en roadmap explícito de la sección 10).

**5.1 Familia C1 — Identidad y autenticación**

**C1.1 Autenticación centralizada vía Keycloak** *\[alta\]*

**Mitiga:** spoofing de identidad, escalada por credencial débil

**Anclaje SDD:** ADR-007, sección 8.3

**Tareas del Plan:** T-013, T-025, T-026, T-040

**Estado:** implementado en Ola 0

**Descripción**

Toda autenticación de usuarios pasa por Keycloak. La aplicación nunca almacena ni valida passwords directamente: emite credenciales contra el endpoint OIDC de Keycloak y recibe tokens firmados. Esta centralización garantiza políticas de password homogéneas, hashing con argon2id de calidad industrial, y revocación inmediata mediante invalidación de sesión en Keycloak.

**Evidencia**

> • Configuración del realm con political password mínima (12 chars, complejidad).
>
> • Tests de integración que verifican que la aplicación rechaza tokens no emitidos por Keycloak.
>
> • Logs de auditoría de cada login exitoso y fallido.

**C1.2 JWT firmado RS256 con vida corta y refresh con rotación** *\[alta\]*

**Mitiga:** robo de token, reutilización indefinida

**Anclaje SDD:** ADR-007

**Estado:** implementado en Ola 0

**Descripción**

Los access tokens viven 15 minutos; los refresh tokens viven 7 días con rotación automática (cada uso del refresh genera uno nuevo y revoca el anterior). La firma se hace con clave asimétrica RS256, lo que permite que múltiples servicios validen la firma sin compartir secret. La clave pública se cachea con TTL configurable y se refresca al detectar tokens firmados con kid desconocido.

**C1.3 MFA obligatoria para roles privilegiados** *\[alta\]*

**Mitiga:** compromiso de credencial sin segundo factor

**Estado:** manager y super_admin: en implementación; salesperson y admin_staff: opcional desde Ola 1, planificado obligatorio en Ola 2

**Descripción**

Los usuarios con rol manager y super_admin tienen MFA habilitada por configuración del realm de Keycloak. El primer login fuerza configuración de TOTP (compatible con apps estándar como Google Authenticator y 1Password). En MVP no se exige MFA a salesperson y admin_staff porque la fricción operativa en agencias chicas es alta; está planificada como obligatoria a partir de la Ola 2 una vez que el producto esté maduro.

**C1.4 Detección de logins anómalos y bloqueo de fuerza bruta** *\[media\]*

**Mitiga:** credential stuffing, fuerza bruta

**Estado:** implementado en Ola 1

**Descripción**

Bloqueo exponencial por IP y por cuenta tras intentos fallidos: 5 intentos disparan bloqueo de 5 minutos; 10 intentos disparan bloqueo de 30 minutos; 20 intentos disparan bloqueo de 24 horas y notificación al user dueño de la cuenta. Detección de logins desde geolocalizaciones nuevas con notificación al user; el user puede confirmar o reportar. Los intentos se loguean para análisis posterior.

**C1.5 Política de password robusta verificada contra haveibeenpwned** *\[media\]*

**Mitiga:** uso de passwords filtradas en otros breaches

**Estado:** planificado para Ola 2

**Descripción**

Al setear o cambiar password, se verifica el hash contra el API público de haveibeenpwned (k-anonymity) y se rechaza si aparece en breaches conocidos. Esto previene que usuarios reutilicen passwords ya comprometidas. La integración usa el modelo k-anonymity para no enviar el hash completo ni la password al servicio externo.

**5.2 Familia C2 — Autorización y control de acceso**

**C2.1 RBAC con roles canónicos y permisos finos** *\[alta\]*

**Mitiga:** escalada de privilegios, acceso indebido

**Anclaje SDD:** sección 8.4

**Tareas del Plan:** T-014

**Estado:** implementado en Ola 0

**Descripción**

Sistema de roles canónicos (super_admin, manager, salesperson, admin_staff) con dependency require_role en cada endpoint. Permisos finos por módulo cuando un rol no es suficiente granularidad: por ejemplo, salesperson tiene acceso de lectura a todos los vehículos del tenant pero solo puede editar internal_notes y assigned_user_id, lo cual se valida con dependency require_permission específica.

**C2.2 Autorización siempre en backend; el frontend solo oculta UI** *\[alta\]*

**Mitiga:** elev. priv. por bypass de UI

**Estado:** implementado por convención + tests

**Descripción**

El frontend puede ocultar botones que un rol no debería ver, pero la autorización efectiva siempre ocurre en el backend. Cualquier endpoint expuesto se protege con require_role o require_permission, sin excepciones. Tests automáticos verifican por rol qué endpoints están accesibles, detectando endpoints olvidados sin protección.

**C2.3 Auditoría obligatoria de operaciones privilegiadas** *\[alta\]*

**Mitiga:** repudio, deteccion tardía de abuso

**Anclaje SDD:** Principio 5, sección 3.9

**Tareas del Plan:** T-011, T-014

**Estado:** implementado en Ola 0

**Descripción**

Decorador @audit_action que se aplica obligatoriamente a endpoints de operaciones sensibles: cambios de configuración del tenant, alta/baja/modificación de users, cambios de plan, accesos a datos de otros tenants por super_admin, exports de datos. La auditoría registra trace_id, user_id, ip, user_agent, action, before/after, timestamp.

**C2.4 Just-in-time access para empleados internos a producción** *\[alta\]*

**Mitiga:** compromiso de cuenta de empleado, abuso interno

**Estado:** implementado como procedimiento manual en Ola 0; automatización con tooling planificada para Ola 2

**Descripción**

Los empleados de deRuedas no tienen acceso permanente a la base de producción ni a datos del tenant. Cuando una operación requiere acceso (debug, soporte autorizado), se sigue el procedimiento JIT documentado en la sección 9: ticket interno con justificación, aprobación de un segundo empleado autorizado, otorgamiento de credencial efímera con TTL máximo de 4 horas, registro completo de la sesión, revocación automática al expirar. Toda actividad queda en audit_logs con tag jit=true.

**C2.5 Principio de mínimo privilegio en service accounts** *\[media\]*

**Mitiga:** lateral movement tras compromiso

**Estado:** implementado en Ola 0

**Descripción**

Cada workload tiene su propia identidad de servicio con permisos IAM mínimos: el backend solo accede al bucket de fotos y a la base; el worker solo accede a Redis y al storage de exports; el job de backups solo escribe al bucket de backups. No hay credenciales compartidas entre workloads. Las credenciales rotan mediante secret manager.

**5.3 Familia C3 — Cifrado**

**C3.1 TLS 1.2+ obligatorio en todo tránsito externo e interno** *\[alta\]*

**Mitiga:** MITM, interception

**Estado:** implementado

**Descripción**

Todo tráfico HTTP, incluyendo el interno entre containers, usa TLS 1.2 mínimo (preferentemente 1.3). Certificados públicos provistos por el LB con renovación automática. Internamente, certificados emitidos por la CA privada del cluster con rotación automática. HSTS configurado con max-age 1 año, includeSubDomains y preload. Plain HTTP redirige a HTTPS y nunca atiende API.

**C3.2 Cifrado en reposo de toda persistencia** *\[alta\]*

**Mitiga:** lectura no autorizada de discos, backups, snapshots

**Estado:** implementado

**Descripción**

Volúmenes de PostgreSQL, Redis y storage cifrados con keys gestionadas por KMS del cloud provider, AES-256. Backups cifrados con la misma clave (o derivada). Snapshots automáticos cifrados. Acceso al KMS auditado. Rotación de keys cada 12 meses con re-cifrado automático en backend del proveedor.

**C3.3 Cifrado de campo para secretos por tenant** *\[alta\]*

**Mitiga:** exposición de credenciales de tenants ante incidente de BD

**Anclaje SDD:** sección 8.5

**Tareas del Plan:** T-126

**Estado:** implementado en Ola 1

**Descripción**

Los secretos del tenant —API keys de integraciones, webhook tokens, MFA seeds— se cifran con AES-GCM usando una clave derivada por tenant a partir de la master key. Esto significa que aún si un atacante obtiene un dump de la base de datos, los secretos siguen ilegibles sin acceso al KMS. La master key vive en KMS gestionado y rota cada 12 meses con recifrado batch.

**C3.4 Sin secretos en código, configuración o logs** *\[alta\]*

**Mitiga:** leakage por error humano

**Estado:** implementado vía CI

**Descripción**

Hooks de pre-commit y job de CI con trufflehog/gitleaks que detectan patterns de secretos en cambios. Si un secret aparece históricamente, no basta con borrarlo: se rota inmediatamente y se reescribe historia si la rama lo permite. Logger custom enmascara campos marcados como sensitive antes de emitir. Tests automáticos buscan en outputs de logs patrones de tokens, keys, DNI, teléfonos completos.

**5.4 Familia C4 — Aislamiento multi-tenant**

**C4.1 Row-Level Security en PostgreSQL como red de seguridad** *\[alta\]*

**Mitiga:** cross-tenant data leakage por bug en aplicación

**Anclaje SDD:** ADR-006

**Tareas del Plan:** T-010, T-027

**Estado:** implementado en Ola 0

**Descripción**

Toda tabla con tenant_id tiene activada RLS con política tenant_isolation que filtra por current_setting('app.current_tenant'). Si por algún bug la aplicación olvidara filtrar, RLS impide leer o modificar filas de otros tenants. Al comienzo de cada request, el middleware setea la variable de sesión con el tenant_id derivado del JWT. Sin tenant context seteado, las queries con RLS no devuelven filas, lo que produce un error visible y testeable, no un silencio peligroso.

**Evidencia**

> • Lista en pg_policies de todas las tablas con política activa.
>
> • Test introspectivo en CI que recorre information_schema y pg_policies y verifica que toda tabla con columna tenant_id tiene política tenant_isolation.
>
> • Tests integration de aislamiento que crean dos tenants y verifican que A no ve B.

**C4.2 Tenant context inferido del JWT, nunca de input del usuario** *\[alta\]*

**Mitiga:** spoofing de tenant

**Estado:** implementado

**Descripción**

El tenant_id de la operación se obtiene exclusivamente del claim del JWT validado, nunca de un campo en el body o query string. Schemas Pydantic explícitamente excluyen tenant_id de los inputs aceptados. Ningún endpoint admite tenant_id por path salvo /admin/api/v1/tenants/{tenant_id}, que requiere rol super_admin.

**C4.3 Tests de aislamiento bloqueantes en CI** *\[alta\]*

**Mitiga:** regresiones que rompen aislamiento

**Estado:** implementado

**Descripción**

Suite específica test_tenant_isolation que setupea dos tenants A y B con datos completos y ejerce todos los endpoints como user de A intentando ver/modificar recursos de B. La suite es bloqueante: si un test falla, el pull request no puede mergearse. Ante cualquier nuevo módulo o tabla con tenant_id, se agrega cobertura específica del módulo.

**5.5 Familia C5 — Validación de entradas y outputs**

**C5.1 Validación estricta con Pydantic en cada entrada** *\[alta\]*

**Mitiga:** tampering, injection, elev. priv. por campos no esperados

**Estado:** implementado

**Descripción**

Toda entrada a la API se valida con schema Pydantic v2 que rechaza campos no declarados (extra='forbid' por default), valida tipos, rangos, formatos. Validators custom para CUIT, DNI, dominios argentinos, chasis, formatos de teléfono. La invalidación produce respuesta 422 con detalle por campo, sin exponer información que ayude al atacante.

**C5.2 Sanitización de outputs y prevención de XSS** *\[alta\]*

**Mitiga:** XSS reflejado o almacenado

**Estado:** implementado

**Descripción**

React escapa por default; cualquier uso de dangerouslySetInnerHTML requiere ADR específico. Para campos donde el tenant ingresa Markdown ligero (notas de leads, descripciones de vehículos), se usa librería de markdown que sanitiza HTML peligroso en parsing, no se confía en CSP solo. CSP estricta configurada en headers HTTP rechaza inline scripts y eval.

**C5.3 Headers de seguridad obligatorios en respuestas** *\[media\]*

**Mitiga:** MITM, clickjacking, sniffing de mime

**Estado:** implementado

**Descripción**

HSTS con preload; X-Content-Type-Options: nosniff; X-Frame-Options: DENY (o frame-ancestors none en CSP); Referrer-Policy: strict-origin-when-cross-origin; Permissions-Policy restrictiva. CSP por entorno: estricta en producción, más laxa en dev. Headers verificados por test automatizado en CI.

**C5.4 Rate limiting por endpoint sensible** *\[media\]*

**Mitiga:** DoS, fuerza bruta, scraping

**Estado:** implementado parcialmente; refinamiento por endpoint en Ola 1

**Descripción**

Rate limit por defecto en LB/CDN (100 req/s por IP). Endpoints sensibles tienen límites adicionales más estrictos: login 10/min por IP y por user, password reset 3/hora por user, webhook republish 1/min por vehicle. Excedente devuelve 429 con header Retry-After.

**5.6 Familia C6 — Auditoría y observabilidad**

**C6.1 audit_logs append-only con datos forenses completos** *\[alta\]*

**Mitiga:** repudio, detección tardía

**Anclaje SDD:** sección 3.9

**Tareas del Plan:** T-011

**Estado:** implementado en Ola 0

**Descripción**

Tabla audit_logs particionada mensualmente, con UPDATE/DELETE revocados al rol app. Cada fila incluye trace_id, user_id, tenant_id, ip, user_agent, action, entity, before/after en jsonb. Retención mínima de 24 meses. Roadmap (Ola 3): hash chain para detección de tampering retroactivo y firma criptográfica periódica del estado de la tabla.

**C6.2 Logging estructurado JSON con propagación de trace_id** *\[alta\]*

**Mitiga:** incapacidad de investigar incidentes

**Tareas del Plan:** T-028

**Estado:** implementado

**Descripción**

structlog emite JSON con campos canónicos: trace_id, request_id, tenant_id, user_id, action, route, method, status, duration_ms. trace_id se genera al borde y se propaga a todo el request, a eventos publicados, a llamadas a servicios externos. Logs centralizados en Loki o equivalente con retención 90 días para logs de aplicación, 24 meses para audit_logs.

**C6.3 Métricas de seguridad en Prometheus + alertas** *\[media\]*

**Mitiga:** ceguera ante anomalías

**Estado:** implementado parcialmente

**Descripción**

Métricas dedicadas a seguridad: auth_failures_total, rls_violations_total (debería ser siempre 0), audit_writes_total, jit_access_grants_total, cross_tenant_403_total. Alertas Prometheus para anomalías: auth_failures spike (\>10x baseline), rls_violations \> 0 jamás, audit_writes_total estancado (sospecha de bug en logging).

**C6.4 Sentry para captura de excepciones con sanitización de PII** *\[media\]*

**Mitiga:** errores que pasan desapercibidos

**Tareas del Plan:** T-031

**Estado:** implementado

**Descripción**

SDK Sentry instrumenta backend y frontend. before_send filter sanitiza payloads antes de enviarlos: enmascara email, dni, teléfono, password, tokens. Tags: release, environment, tenant_id (cuando aplica). Asociación con trace_id propio para correlación con logs.

**5.7 Familia C7 — Gestión de secretos**

**C7.1 Secrets en KMS/secret manager del cloud, no en archivos** *\[alta\]*

**Mitiga:** secret leakage, persistencia tras compromiso

**Estado:** implementado

**Descripción**

Todos los secretos de infraestructura (DB password, Redis password, JWT signing key fallback, Sentry DSN, S3 access keys) se almacenan en el secret manager del cloud provider. Las aplicaciones los obtienen al startup y los mantienen en memoria. Rotación trimestral automatizada para credenciales que lo soportan. Secretos del tenant se cifran adicionalmente con C3.3.

**C7.2 Rotación de secretos documentada y ejercitada** *\[media\]*

**Estado:** documentado en Ola 1; ejercitada al menos 1 vez por año

**Descripción**

Runbooks por tipo de secreto en docs/runbooks/secrets-rotation/. Cada runbook detalla: cuándo se debe rotar, quién aprueba, paso a paso de rotación con cero downtime, plan de rollback, criterio de éxito. Ejercicio anual obligatorio: rotar al menos un secreto crítico fuera de incidente para verificar que el procedimiento funciona en frío.

**C7.3 Detección automática de secretos en cambios de código** *\[alta\]*

**Mitiga:** leak por commit accidental

**Estado:** implementado

**Descripción**

Pre-commit hook con gitleaks que bloquea commit si detecta patrón de secreto. Job de CI con trufflehog que escanea historial completo del PR. Si un secreto se encuentra: no merge, secret rotado inmediatamente, push para reescribir historia si la rama lo permite. Reportes automáticos a security@deruedas.com.

**5.8 Familia C8 — Resiliencia**

**C8.1 Idempotencia obligatoria en operaciones POST sensibles** *\[media\]*

**Mitiga:** duplicación de operaciones por reintento

**Anclaje SDD:** sección 4.1.8

**Tareas del Plan:** T-015

**Estado:** implementado

**Descripción**

POSTs que crean recursos o disparan acciones aceptan header Idempotency-Key (UUID v4). El backend cachea la respuesta por 24 horas vinculada al hash del payload. Misma key + mismo payload devuelve respuesta cacheada. Misma key + payload distinto devuelve 409. Esto permite a clientes reintentar sin duplicar.

**C8.2 Retry con backoff exponencial y dead-letter queue** *\[media\]*

**Mitiga:** pérdida de eventos por falla transitoria

**Anclaje SDD:** sección 2.4, ADR-009

**Tareas del Plan:** T-016, T-122

**Estado:** implementado

**Descripción**

Consumers de eventos reintentan errores transitorios con backoff exponencial: 60s, 120s, 240s, 480s, 960s. Tras agotar reintentos (5 por defecto), evento va a DLQ con razón. DLQ revisada por on-call diariamente. Alertas si DLQ crece más rápido que el threshold.

**C8.3 Circuit breaker en integraciones salientes** *\[media\]*

**Mitiga:** cascading failure por proveedor degradado

**Estado:** implementado

**Descripción**

Cliente HTTP con circuit breaker: tras N fallas consecutivas en una ventana, el circuit se abre y rechaza inmediatamente sin intentar la llamada (devuelve error rápido al caller) durante M segundos antes de probar half-open. Esto protege al producto cuando WhatsApp Cloud API o el portal deRuedas están degradados.

**5.9 Familia C9 — Seguridad de webhooks y APIs entrantes**

**C9.1 Verificación HMAC obligatoria en webhooks** *\[alta\]*

**Mitiga:** spoofing de webhooks

**Tareas del Plan:** T-176

**Estado:** implementado

**Descripción**

Webhooks de Meta verificados con HMAC SHA256 usando app_secret. La verificación es lo primero que ocurre, antes de cualquier procesamiento del payload. Falla → 401 sin pista del motivo. Por canal externo, app_secret específico por tenant cuando aplica.

**C9.2 Procesamiento async de webhooks con respuesta inmediata** *\[media\]*

**Mitiga:** DoS por webhook flood, retries del proveedor

**Estado:** implementado

**Descripción**

Webhook valida HMAC, encola en stream y responde 200 OK en \<300ms. Procesamiento real ocurre asincrónicamente en worker. Esto evita que un proveedor lento del lado nuestro genere reintentos innecesarios desde Meta y limita el impacto de bursts.

**5.10 Mapping de controles a riesgos**

Vista de cobertura: para cada riesgo material de la sección 4.5, qué controles lo mitigan. Esto permite identificar gaps.

|  |  |
|:---|:---|
| **Riesgo** | **Controles que aplican** |
| Pérdida de aislamiento entre tenants | C4.1, C4.2, C4.3, C2.3 (audit), C6.3 (alerta rls_violations_total) |
| Compromiso de credencial de empleado privilegiado | C1.3, C2.4 (JIT), C2.3 (audit), C6.3 (alertas), C7.1 (rotación), C9 personal interno |
| Filtración PII vía logs/backups | C3.2, C3.4, C6.4 (sanitización), C7.3 |
| Indisponibilidad regional | C8.x (resiliencia), backups multi-region (sección 7), DR plan |
| Credenciales de tenant expuestas | C3.3, C7.1, C7.3 |
| Phishing exitoso a manager | C1.3, C1.4, C2.3 |
| Inyección via webhook | C9.1, C9.2 |
| DoS volumétrico | C5.4, CDN/WAF |
| Supply chain attack | C7.3, sección 8 (SSDLC) |
| Insider tenant deshonesto | C2.3 (audit), C5.4 (rate limit en exports), límites en exports masivos |

**6. Privacidad y compliance regulatorio**

Esta sección desarrolla las obligaciones de protección de datos personales bajo el régimen argentino y traduce esas obligaciones en prácticas operativas concretas. La normativa aplicable principal es la Ley 25.326 de Protección de los Datos Personales, su decreto reglamentario, la Disposición 11/2006 sobre medidas de seguridad y las resoluciones de la AAIP (Agencia de Acceso a la Información Pública). El tratamiento descrito se mantiene compatible con los principios del marco europeo (GDPR), lo cual facilita la expansión futura del producto y la firma de DPAs con clientes que exijan ese estándar.

**Aclaración legal:** Este documento describe el programa de privacidad de la organización pero no constituye asesoramiento legal. Las decisiones de cumplimiento específicas, los textos de política de privacidad publicados al usuario final y los términos contractuales con tenants se elaboran y validan con asesoramiento legal calificado.

**6.1 Modelo de roles bajo Ley 25.326**

La Ley 25.326 distingue principalmente entre dos roles: el responsable del tratamiento, que decide sobre la finalidad y los medios del tratamiento de datos personales; y el encargado del tratamiento (en terminología argentina, el “responsable” contratado para tratar datos a nombre de otro), que trata datos por cuenta del responsable. La Disposición 47/2018 también introduce conceptos análogos al GDPR.

La distribución de roles entre deRuedas y sus tenants es la siguiente.

|  |  |
|:---|:---|
| **Tipo de dato** | **Rol de cada actor** |
| Datos personales de contactos y leads de la agencia | Responsable: la agencia tenant. Encargado: deRuedas. La agencia decide qué datos recolectar, con qué finalidad, a quién compartir; deRuedas los trata por cuenta de la agencia conforme al DPA. |
| Datos de los usuarios del SaaS (manager, salespersons del tenant) | Responsable: deRuedas (necesarios para prestar el servicio). Las agencias no son responsables de los datos de identificación de sus propios empleados frente a deRuedas. |
| Datos de empleados de deRuedas | Responsable: deRuedas. Régimen laboral aplicable. |
| Datos de prospects de deRuedas (leads de venta del SaaS) | Responsable: deRuedas. |

**6.2 Bases de licitud del tratamiento**

Toda operación de tratamiento se realiza bajo una base de licitud expresa. La siguiente tabla mapea cada categoría de tratamiento a su base.

|  |  |  |
|:---|:---|:---|
| **Tratamiento** | **Base de licitud** | **Notas** |
| Tratamiento de contactos y leads por la agencia | Consentimiento del titular o interés legítimo de la agencia (relación comercial) | Es la agencia (responsable) quien debe asegurarse de tener base lícita; deRuedas se obliga contractualmente a asistirla. |
| Comunicación a contactos vía WhatsApp | Consentimiento + interés legítimo en relación comercial existente | WhatsApp aplica adicionalmente sus propias políticas de plantillas y opt-in. |
| Tratamiento de datos de empleados del tenant | Ejecución del contrato con el tenant (acceso al SaaS) | Datos mínimos necesarios para autenticar y dar trazabilidad. |
| Auditoría y seguridad | Interés legítimo del responsable | Justificable por necesidad de prevención de fraude y trazabilidad. |
| Backup y respaldo | Ejecución del contrato + interés legítimo | Necesario para la continuidad del servicio. |
| Métricas técnicas y producto agregadas | Interés legítimo | Datos pseudonimizados/agregados, no asociados a personas individuales. |

**6.3 Principios de privacidad aplicados**

**6.3.1 Minimización**

El producto recolecta solo los datos necesarios para su finalidad. Los formularios de alta de contacto piden nombre y teléfono como mínimos; email, DNI y otros campos son opcionales. No se recolectan datos sensibles (origen racial, opiniones políticas, religión, salud, vida sexual) salvo que un titular los aporte voluntariamente en una conversación de WhatsApp, en cuyo caso se aplican las protecciones generales sin tratamiento especial. La política de uso aceptable que las agencias aceptan al contratar prohíbe el uso del producto para procesamiento sistemático de datos sensibles.

**6.3.2 Finalidad limitada**

Los datos de un tenant no se usan para finalidades distintas a las del servicio prestado. deRuedas no comercializa, comparte ni cruza datos de un tenant con otro. Las analíticas internas usan datos agregados o pseudonimizados, nunca identificables. Los datos no se usan para entrenar modelos de IA cross-tenant: cualquier uso futuro de datos para entrenamiento se limita al ámbito del tenant que aporta los datos, requiere consentimiento explícito del tenant y se documenta en un anexo del DPA.

**6.3.3 Exactitud**

El producto provee mecanismos para que el responsable (la agencia) actualice y rectifique datos en cualquier momento. Las inconsistencias detectadas (duplicados de contacto por teléfono, registros con campos vacíos críticos) se señalan en la UI. La merge de contactos (T-132 del Plan de Implementación) permite consolidar duplicados. El derecho de rectificación del titular se atiende por el procedimiento descrito en 6.5.

**6.3.4 Conservación limitada**

Los datos no se conservan más tiempo del necesario. La sección 6.6 detalla la política de retención por categoría. La purga automática mediante crons se implementa para mensajes de WhatsApp más antiguos que el límite, audit_logs particionada con DROP de particiones expiradas, eventos antiguos del stream.

**6.3.5 Integridad y confidencialidad**

Los controles técnicos de la sección 5 implementan este principio: cifrado en tránsito y reposo, control de acceso, auditoría, prevención de leaks.

**6.4 Política de retención por categoría de dato**

|  |  |  |
|:---|:---|:---|
| **Categoría** | **Retención** | **Justificación** |
| Contactos activos del tenant | Mientras el tenant los mantenga | El tenant decide; deRuedas los archivó al borrar y purgó tras 24 meses inactivos. |
| Leads cerrados (won/lost) | Mínimo 5 años desde cierre | Período típico de retención comercial argentina. El tenant puede eliminar antes solicitando. |
| Mensajes de WhatsApp | 24 meses desde occurred_at | Balance entre utilidad de histórico y proporcionalidad. Cron mensual elimina particiones expiradas. |
| Conversaciones cerradas | 60 meses (referencia, sin mensajes) | El registro de que existió la conversación pero sin contenido. |
| audit_logs | 24 meses | Mínimo necesario para investigación forense y cumplimiento. |
| Backups | 30 días para backup operativo; 12 meses para snapshot mensual | Recuperación operativa ante incidente reciente; recuperación regulatoria a más largo plazo. |
| Logs de aplicación | 90 días | Período típico de troubleshooting; agregados se mantienen en métricas. |
| Datos de tenant tras cancelación de servicio | 30 días en cold storage | Período de gracia para reactivación o exportación; pasados los 30 días, eliminación. |
| Datos vinculados a operaciones contables (futuras Olas) | 10 años | Resolución 4717/2020 AFIP y normas mercantiles. |

**6.5 Derechos de los titulares**

La Ley 25.326 reconoce derechos de los titulares: acceso, rectificación, actualización y supresión, complementados por la posibilidad de oposición a tratamientos específicos y la información sobre el responsable. La estructura del producto permite operacionalizar estos derechos a través del responsable (la agencia tenant).

**6.5.1 Derecho de acceso**

El titular puede solicitar a la agencia conocer qué datos se tratan sobre él, con qué finalidad y a quién se comparten. La agencia, como responsable, atiende la solicitud. deRuedas provee al manager del tenant un endpoint y una pantalla en el backoffice del tenant que exporta todos los datos asociados a un teléfono o email del titular: contacto, leads, mensajes, actividades. El export es estructurado (JSON o CSV) y entregable directamente al titular.

**6.5.2 Derecho de rectificación**

La agencia, vía la UI, puede actualizar datos del titular en cualquier momento. La trazabilidad del cambio queda en audit_logs.

**6.5.3 Derecho de supresión y oposición**

El titular puede solicitar eliminación de sus datos cuando ya no haya base lícita para el tratamiento. deRuedas provee al manager un endpoint POST /api/v1/contacts/{id}/forget que ejecuta la eliminación: anonimización de los campos identificables del contacto (nombre se reemplaza por hash, teléfono y email se vacían), eliminación de mensajes asociados, marcado en audit_logs de “right to be forgotten executed” con justificación. Lo que se preserva: registros agregados (estadísticas), audit_logs de auditoría (sin datos identificables del titular). El procedimiento está documentado en docs/runbooks/data-subject-rights.md.

**6.5.4 Mecanismo de canalización**

Los titulares ejercen derechos directamente ante la agencia (responsable). Si un titular se dirige a deRuedas en lugar de a la agencia, deRuedas redirige al titular hacia el responsable correcto y notifica al tenant para que cumpla. Si no es posible identificar al tenant, deRuedas atiende la solicitud directamente y notifica al titular del proveedor que está actuando por cuenta de otro.

**6.6 Transferencia internacional de datos**

Una porción de los datos se procesa fuera de Argentina debido a que algunos componentes de infraestructura son provistos por proveedores cloud globales. La sección 12.1 contiene el inventario completo de subprocessors. Las transferencias internacionales se documentan transparentemente y se cubren bajo cláusulas contractuales tipo cuando aplican.

|  |  |  |
|:---|:---|:---|
| **Componente** | **Región** | **Comentario** |
| Cluster PostgreSQL primario | South America (São Paulo) | Datos en reposo en la región principal. |
| Backup PostgreSQL replicado | South America (Santiago) o segunda región | Para DR; mismo esquema legal que primary. |
| Object storage de fotos | South America | Cifrado por KMS. |
| Sentry / observability | United States o Europa, según vendor | Datos sanitizados (sin PII bruta); cobertura por SCC. |
| WhatsApp Cloud API | Estados Unidos / Irlanda (Meta) | Procesamiento de mensajes según términos de Meta; el titular es informado por la agencia que la comunicación es por WhatsApp. |
| Keycloak managed (cuando aplique) | Región contratada | Solo datos de identidad. |
| Email provider (Sendgrid / equivalente) | United States o Europa | Solo asuntos y destinatarios; cuerpo enmascarado en logs. |

**6.7 Acuerdo de procesamiento de datos (DPA) con tenants**

El DPA es contrato accesorio al de servicio que regula específicamente la relación de tratamiento de datos personales. Los tenants firman un DPA al contratar deRuedas. El contenido mínimo es el siguiente.

- Identificación de las partes y rol (responsable / encargado).

- Objeto, naturaleza y finalidad del tratamiento.

- Categorías de titulares y datos.

- Duración del tratamiento (vinculada al contrato de servicio).

- Obligaciones del encargado (deRuedas): tratar datos solo según instrucciones documentadas, garantizar confidencialidad de quienes acceden, implementar medidas técnicas y organizativas (las de este documento), asistir al responsable en derechos de titulares y en notificación de incidentes, colaborar en evaluaciones de impacto, eliminar o devolver datos al término.

- Subprocessors autorizados y procedimiento de actualización (la lista de la sección 12.1 con notificación previa al tenant ante incorporaciones).

- Notificación de incidentes en plazo de 72 horas desde detección, con detalle de procedimiento.

- Auditoría: derecho del responsable a auditar (con preaviso razonable, una vez por año, bajo NDA, sin acceso a datos de otros tenants).

- Transferencia internacional autorizada según sección 6.6.

- Cláusulas adicionales sobre confidencialidad y propiedad.

**6.8 Notificación de incidentes a la AAIP**

La normativa argentina, sin imponer literalmente las 72 horas del GDPR, establece que las brechas que afecten datos personales deben notificarse a la AAIP cuando exista riesgo significativo a los derechos de los titulares. La Resolución 47/2018 de la AAIP detalla el contenido de la notificación. La política de deRuedas adopta el estándar de 72 horas desde la detección, alineado con buenas prácticas internacionales. La notificación incluye: descripción del incidente, naturaleza y volumen estimado de datos afectados, posibles consecuencias, medidas adoptadas y datos de contacto del responsable de privacidad. La sección 7 detalla el flujo operativo.

**6.9 Responsable interno de protección de datos**

La organización designa un responsable interno de protección de datos (figura análoga al DPO europeo, sin la formalidad estatutaria). Sus funciones son: supervisar el cumplimiento del programa de privacidad descrito en este documento, ser punto de contacto con la AAIP y con responsables tenants, liderar respuestas a derechos de titulares cuando lleguen al canal central, coordinar revisiones periódicas y entrenamiento al equipo, mantener actualizado el inventario de tratamientos. El responsable se identifica internamente y su correo (privacidad@deruedas.com) se publica en la política de privacidad pública.

**7. Respuesta a incidentes de seguridad**

Esta sección define el programa de respuesta a incidentes de seguridad: cómo se clasifican, cómo se escalan, quiénes intervienen, qué se comunica, en qué plazo y qué se hace después. El objetivo no es prevenir todos los incidentes —los incidentes ocurrirán— sino contenerlos rápidamente, comunicar de manera transparente, restaurar el servicio y aprender.

**7.1 Definiciones**

Un incidente de seguridad es cualquier evento confirmado o sospechado que comprometa la confidencialidad, integridad o disponibilidad de datos del producto, datos del tenant, infraestructura, identidades o procesos críticos. Distinguir incidente de evento de seguridad es importante: un evento es una observación que requiere análisis (por ejemplo, un spike de auth_failures); un incidente es un evento confirmado como adverso (por ejemplo, una cuenta comprometida).

**7.2 Taxonomía de severidad**

La severidad determina la respuesta. Las clasificaciones son las siguientes y se asignan al inicio del incidente con la información disponible; pueden re-evaluarse durante el incidente conforme aparece más información.

|  |  |  |  |
|:---|:---|:---|:---|
| **Sev.** | **Etiqueta** | **Criterio** | **Tiempo de respuesta** |
| P0 | Crítico | Compromiso confirmado de aislamiento entre tenants, exposición pública confirmada de PII de múltiples tenants, ransomware activo, pérdida de control de identidades privilegiadas. Servicio totalmente caído por más de 30 minutos. | Inmediato (\<15min) |
| P1 | Mayor | Compromiso confirmado de un tenant individual, exposición confirmada de datos de un solo tenant a otro, falla de seguridad reproducible que requiere despliegue urgente, pérdida parcial significativa del servicio (\>50% usuarios afectados). | \<1 hora |
| P2 | Significativo | Sospecha fundada de incidente bajo investigación, vulnerabilidad crítica detectada en producción no explotada, pérdida menor del servicio (\<10% usuarios), error operativo recuperable. | \<4 horas |
| P3 | Menor | Vulnerabilidad de severidad media o baja en producción, evento de seguridad sospechoso pero no concluyente, error que afecta a un solo usuario. | \<24 horas (días hábiles) |
| P4 | Informativo | Hallazgo informativo, mejora identificada, configuración subóptima sin impacto inmediato. | Backlog priorizado |

**7.3 Roles durante un incidente**

Durante un incidente activo se asignan roles claros para evitar confusión y duplicación de esfuerzos.

|  |  |
|:---|:---|
| **Rol** | **Responsabilidad** |
| Incident Commander (IC) | Coordinación general. Decide acciones, prioriza, comunica con stakeholders. No es necesariamente quien más sabe técnicamente sino quien dirige. Rota cada cuatro horas en incidentes prolongados. |
| Tech Lead | Lidera la mitigación técnica. Decide qué se cambia, qué se rolbackea, qué evidencia se preserva. |
| Communications | Maneja comunicación interna y externa: status page, emails a tenants afectados, notificaciones a la AAIP cuando aplique. No improvisa: usa plantillas de la sección 7.7. |
| Scribe | Toma notas en vivo: cronología, decisiones tomadas, evidencia preservada. La documentación generada es insumo del postmortem. |
| Subject Matter Experts (SMEs) | Aportan conocimiento específico (BD, networking, módulo afectado). Son consultados; no toman decisiones por su cuenta. |
| Legal/Compliance | Cuando el incidente activa obligaciones regulatorias (notificación a AAIP, contacto con autoridades). En MVP, este rol lo cubre el responsable de privacidad asistido por asesoría legal externa. |

**7.4 Workflow de respuesta**

DETECCIÓN

↓

· Alerta automática (Prometheus, Sentry, Loki, RLS_violations)

· Reporte de empleado

· Reporte de tenant

· Reporte de tercero / responsible disclosure

↓

TRIAGE INICIAL (max 15min)

↓ ¿es incidente real?

└─ NO → cerrar como evento, documentar

└─ SÍ → continuar

↓

CLASIFICACIÓN DE SEVERIDAD

↓

· Asignar IC, Tech Lead, Scribe

· Crear war room (canal Slack dedicado \#inc-YYYY-MM-DD-tag)

· Iniciar timeline en doc compartido

↓

CONTENCIÓN

↓

· Aislar componente comprometido

· Revocar credenciales sospechosas

· Bloquear IPs maliciosas

· Detener flujo si es necesario

↓

ERRADICACIÓN

↓

· Identificar causa raíz

· Eliminar acceso del atacante / corregir bug

· Verificar no haya persistencia

↓

RECUPERACIÓN

↓

· Restaurar servicio

· Validar integridad de datos

· Monitoreo reforzado por 48h

↓

COMUNICACIÓN

↓

· Status page actualizada continuamente durante el incidente

· Email a tenants afectados según plazos sección 7.5

· Notificación AAIP en 72h si aplica (sección 7.6)

↓

POSTMORTEM

↓

· Reunión sin culpa dentro de 5 días hábiles

· Cronología, root cause, action items

· Publicación interna; público sanitizado opcional

↓

SEGUIMIENTO

· Action items con dueños y plazos en sistema de tracking

· Revisión a 30 días

**7.5 Comunicación a tenants**

La comunicación a tenants es uno de los aspectos donde se ha visto más diferencia entre programas maduros y improvisados. La política de deRuedas privilegia la comunicación temprana sobre la comunicación perfecta: un email al tenant diciendo “detectamos incidente, estamos investigando, vamos a actualizar en 4 horas” es siempre mejor que silencio durante 18 horas para entregar un reporte completo.

|  |  |  |
|:---|:---|:---|
| **Sev.** | **Plazo de primer aviso** | **Contenido del primer aviso** |
| P0 | 30 minutos desde clasificación | Aviso de incidente activo, alcance preliminar, próxima actualización en 1 hora. Status page activa. |
| P1 | 2 horas desde clasificación | Aviso de incidente confirmado afectando al tenant, próximos pasos. Status page activa si afecta a múltiples tenants. |
| P2 | Al cierre del incidente o 24h, lo que ocurra primero | Aviso post-resolución con detalle. Status page si fue visible al usuario. |
| P3 - P4 | Mensual en reporte de servicio agregado | Sin alerta individual. |

**Principio de comunicación:** Lo que se comunica al tenant: qué pasó (de manera entendible para no técnicos), qué impacto puede tener para él específicamente, qué se hizo, qué tiene que hacer el tenant si algo. Lo que NO se comunica antes de tiempo: detalles forenses sensibles que ayuden al atacante o a otros atacantes mientras el sistema está aún siendo cerrado.

**7.6 Notificación regulatoria a la AAIP**

Cuando un incidente afecta datos personales y existe riesgo significativo para los titulares, se notifica a la AAIP. El responsable de privacidad evalúa la procedencia de la notificación con apoyo legal. El plazo objetivo es 72 horas desde la detección. La notificación, conforme a Resolución 47/2018, incluye: identificación del responsable, descripción del incidente, naturaleza y volumen aproximado de datos afectados, consecuencias probables para titulares, medidas implementadas para mitigar y contener, datos de contacto del responsable de privacidad.

Si el plazo de 72 horas no es realista por complejidad del incidente, la notificación se hace en plazo extendido pero se documenta la justificación. La política privilegia notificar pronto con información parcial actualizable, antes que esperar a tener el reporte definitivo.

**7.7 Plantillas de comunicación**

**7.7.1 Plantilla email tenant — primer aviso de incidente**

Asunto: \[Importante\] Incidente de servicio en deRuedas Gestión

Estimado/a \[nombre del manager\],

Le escribimos para informarle que estamos investigando un incidente

que afecta el servicio de deRuedas Gestión y que tiene un impacto

potencial en su agencia.

Lo que sabemos hasta este momento:

· \[Descripción factual breve\]

· \[Componente afectado\]

· \[Impacto observable para usted\]

· Inicio: \[hora\]

Lo que estamos haciendo:

· Equipo de respuesta activo investigando.

· \[Acciones concretas tomadas hasta ahora\]

Lo que necesitamos de usted en este momento:

· \[Acción concreta o ninguna\]

Próxima actualización en \[tiempo\]. Si tiene preguntas urgentes,

responda este email o contacte a soporte@deruedas.com.

Mantenemos transparencia activa en https://status.deruedas.com

\[Nombre del responsable\]

deRuedas Gestión

**7.7.2 Plantilla email tenant — resolución y postmortem**

Asunto: \[Resuelto\] Incidente del \[fecha\] - resumen y próximos pasos

Estimado/a \[nombre\],

El incidente reportado el \[fecha y hora\] ha sido resuelto. Le

compartimos el resumen completo:

QUÉ PASÓ:

\[Descripción técnica accesible\]

IMPACTO PARA SU AGENCIA:

\[Específico al tenant: qué datos, qué funcionalidad, qué duración\]

DURACIÓN:

Inicio: \[hora\]

Detección: \[hora\]

Mitigación: \[hora\]

Resolución: \[hora\]

CAUSA RAÍZ:

\[Explicación técnica clara, sin culpar a personas\]

QUÉ HACEMOS PARA QUE NO SE REPITA:

· \[Acción 1\] — completada / planificada para \[fecha\]

· \[Acción 2\]

· \[Acción 3\]

Si tiene dudas o quiere conversar sobre el incidente, podemos

agendar una llamada. Responda este email.

Lamentamos las molestias.

\[Nombre\]

deRuedas Gestión

**7.8 Postmortems sin culpa**

Toda incidencia de severidad P0, P1 o P2 genera un postmortem dentro de los 5 días hábiles posteriores a la resolución. El postmortem es sin culpa: la pregunta no es “quién tiene la culpa” sino “qué condiciones del sistema permitieron que esto ocurriera”. La cultura de postmortem sin culpa es el mecanismo principal por el cual la organización aprende y mejora. El postmortem incluye:

- Cronología detallada con timestamps.

- Detección: qué disparó la conciencia del incidente; ¿podríamos haberlo detectado antes?

- Causa raíz: análisis con técnica de los 5 porqués o equivalente.

- Causas contributivas: factores que amplificaron el impacto.

- Lo que funcionó bien: importante reconocer, no solo lo que falló.

- Action items: con dueño y deadline en sistema de tracking.

- Decisión sobre publicación: interna siempre, externa según relevancia.

**7.9 Métricas de respuesta a incidentes**

La calidad del programa se mide con métricas que se reportan trimestralmente.

- MTTD (Mean Time To Detect): tiempo entre el inicio del incidente y su detección. Objetivo: \<15 minutos para P0 y P1.

- MTTA (Mean Time To Acknowledge): tiempo entre la detección y la asignación a un IC. Objetivo: \<5 minutos para P0, \<30 min para P1.

- MTTR (Mean Time To Resolve): tiempo entre detección y resolución. Objetivo según severidad.

- Incident rate por mes/trimestre, normalizada por carga.

- Porcentaje de incidentes con postmortem completado en plazo.

- Porcentaje de action items de postmortems cerrados a 30 días.

**8. Continuidad operativa y recuperación ante desastres**

Esta sección define el plan de continuidad ante eventos disruptivos —desde la pérdida de un container hasta la indisponibilidad de una región completa del cloud— y los objetivos de recuperación que cada componente debe cumplir.

**8.1 Definiciones**

RTO (Recovery Time Objective) es el tiempo máximo que se acepta que un componente esté indisponible antes de ser restaurado. RPO (Recovery Point Objective) es la pérdida máxima de datos aceptable, medida en tiempo: un RPO de 1 hora significa que en el peor caso se pierden los datos del último diálogo, hora antes del evento.

**8.2 Objetivos por componente**

|  |  |  |  |
|:---|:---|:---|:---|
| **Componente** | **RTO** | **RPO** | **Estrategia** |
| API backend | 15 minutos | 0 | Stateless, auto-scaling, blue-green deploy. |
| Frontend Next.js | 5 minutos | 0 | CDN, build inmutable; rollback simple. |
| PostgreSQL primary | 1 hora | 5 minutos | Replicación streaming sync; PITR habilitado; failover automático con orquestador. |
| PostgreSQL replicas read-only | 30 minutos | 5 minutos | Reconstruibles desde primary. |
| Redis | 10 minutos | 1 minuto (AOF) | AOF habilitado; cluster con failover. |
| OpenSearch | 4 horas | Reconstruible | Reindexación desde PostgreSQL; cluster con réplicas. |
| Object storage (fotos, exports) | 1 hora | 0 | Replicación cross-region; versioning habilitado. |
| Workers Celery | 15 minutos | 0 | Stateless; tareas re-encoladas mediante visibility timeout. |
| Eventos Redis Streams | 1 hora | 5 minutos | Persistencia AOF; consumers idempotentes. |
| audit_logs (auditoría) | 4 horas | 0 | Replicación + backups inmutables; reconstrucción desde logs centralizados como fuente alternativa. |
| Pipeline CI/CD | 8 horas | — | Reconstruible desde IaC; menor criticidad operativa. |
| Sistema completo en región alternativa (DR) | 4 horas | 1 hora | Snapshots periódicos a otra región; runbook de promoción documentado. |

**8.3 Estrategia de backups**

**8.3.1 PostgreSQL**

Backup full diario en bucket de la región primaria. Backup full semanal cross-region. WAL archive continuo a bucket cifrado. Esto permite point-in-time recovery (PITR) de cualquier instante de los últimos 30 días con granularidad de segundos. Snapshots mensuales preservados 12 meses para cumplimiento. Cifrado en reposo con KMS gestionado. Bucket inmutable (object lock) para los snapshots mensuales: ni un atacante con credenciales máximas puede borrar los backups recientes.

**8.3.2 Object storage**

Bucket con versioning habilitado: cada modificación o borrado es soft delete. Replicación cross-region asíncrona. Lifecycle policy que mueve versiones antiguas a tier frío después de 30 días y elimina después de 12 meses (excepto fotos vinculadas a operaciones contables, regla específica).

**8.3.3 Configuración y secretos**

Configuración como código (Terraform) versionada en repo. State de Terraform en bucket cifrado con state lock. Secretos en KMS/secret manager con rotación automatizada y backups del propio servicio.

**8.4 Pruebas de recuperación**

Los backups que no se prueban no existen. La política exige los siguientes ejercicios.

|  |  |
|:---|:---|
| **Ejercicio** | **Frecuencia** |
| Restore de backup PostgreSQL en entorno aislado y verificación de integridad | Mensual |
| PITR a un punto arbitrario en las últimas 24 horas | Trimestral |
| Failover automático del primary PostgreSQL a réplica | Semestral |
| DR completo: levantar el sistema en región alternativa desde backups y operar 1 hora | Anual |
| Tabletop exercise: simulación de incidente sin tocar sistema | Semestral |
| Verificación de inmutabilidad de backups críticos (intento de borrado debe fallar) | Trimestral |

**8.5 Continuidad de personal**

La organización es pequeña en MVP, lo cual significa concentración de conocimiento. Las medidas para mitigar el riesgo de bus factor son: documentación viva de runbooks por componente, rotación obligatoria de on-call entre miembros del equipo, pair programming en operaciones críticas, retrospectivas que incluyen “qué pasaría si X no estuviera mañana”. La auditoría externa al cuerpo SDD que se realiza periódicamente cumple además este propósito: obliga a documentar.

**9. Seguridad en el ciclo de desarrollo**

Esta sección describe cómo la seguridad se integra al ciclo de desarrollo del producto desde el diseño hasta el despliegue, no como capa agregada al final sino como práctica continua.

**9.1 Threat modeling en fase de diseño**

Para todo cambio significativo de arquitectura —nueva integración con tercero, nuevo flujo que toca datos personales, nueva superficie expuesta a Internet— se realiza una sesión de threat modeling antes de comenzar la implementación. La salida es un anexo del ADR correspondiente con tres elementos: amenazas STRIDE identificadas, controles necesarios, riesgo residual aceptado. Lo que no se requiere para cambios menores: agregar un endpoint similar a otro existente, ajustar un schema, modificar una página de UI sin nuevo input.

**9.2 Code review obligatorio**

Branch protection rules en main exigen al menos un approver distinto del autor para todo merge. Reviews de cambios sensibles —migrations, configuración de seguridad, integraciones nuevas, cambios a auth o RLS— requieren approver con etiqueta de “security reviewer”. La lista de security reviewers se actualiza trimestralmente y mantiene al menos dos personas activas. El propio agente de IA, cuando ejecuta tareas del Plan de Implementación, no puede mergear: produce el PR para revisión humana.

**9.3 Análisis estático y composición**

|  |  |  |
|:---|:---|:---|
| **Herramienta** | **Aplicado a** | **Política** |
| ruff (lint + security rules) | Backend Python | Bloqueante en CI; configuración estricta para reglas de seguridad. |
| mypy (type checking) | Backend Python | Bloqueante en CI; strict mode. |
| semgrep | Backend + frontend | Bloqueante en CI para findings de severidad high; warning para medium. |
| eslint con plugin seguridad | Frontend TypeScript | Bloqueante en CI. |
| pip-audit | Dependencias Python | Bloqueante para vulnerabilidades críticas; warning para altas. |
| npm audit | Dependencias Node | Bloqueante para críticas. |
| trivy | Imágenes Docker | Bloqueante para vulnerabilidades críticas en imagen final. |
| gitleaks / trufflehog | Historia de commits | Bloqueante si detecta secretos en cambio. |
| sbom-generator | Cada release | Genera SBOM en formato SPDX para cumplimiento y supply chain. |

**9.4 Análisis dinámico**

DAST automatizado en staging mediante OWASP ZAP en modo passive scan dentro del pipeline. Tests E2E ejecutan flujos típicos y ZAP captura tráfico para detectar issues de configuración (headers faltantes, cookies inseguras, etc.). Penetration testing manual contratado anualmente con vendor reputado, scope acordado, reporte que entra como input al programa.

**9.5 Política de dependencias**

Dependencias se actualizan proactivamente, no solo cuando una vulnerabilidad lo fuerza. Renovate o Dependabot crean PRs automáticos para actualizaciones disponibles. Los PRs siguen el proceso normal de review. Las dependencias mayores (frameworks, librerías core) se mantienen al menos en versión LTS soportada. Las dependencias transitivas con vulnerabilidades se manejan con overrides específicos cuando el upstream no tiene fix, y se documenta el riesgo en SBOM.

**9.6 Branch protection y signed commits**

|  |  |
|:---|:---|
| **Política** | **Estado** |
| Branch protection en main: required reviews ≥1, dismiss stale reviews on push, status checks obligatorios, conversations resolved | implementado |
| No force push, no delete del default branch | implementado |
| Signed commits opcionales | implementado |
| Signed commits obligatorios para todo el equipo | planificado para Ola 2 |
| Tags de release firmados con cosign | planificado para Ola 2 |
| Provenance con SLSA level 2 | planificado para Ola 3 |

**9.7 Entrenamiento de seguridad para developers**

Cada desarrollador completa al onboarding un curso de seguridad introductorio (OWASP Top 10, principios de la organización, manejo de incidentes), refrescado anualmente. Sesiones semestrales internas sobre temas específicos relevantes: secure coding en Python/TypeScript, threat modeling, lessons learned de incidentes industria. La inversión es modesta pero compuesta: la calidad de las decisiones de diseño mejora cuando todo el equipo comparte vocabulario.

**10. Seguridad operativa y de personal**

Esta sección cubre los aspectos no técnicos de la seguridad: cómo se maneja el personal, los accesos, los proveedores, el equipamiento. Es el área donde más fácilmente se introducen vulnerabilidades por descuido organizacional aunque la tecnología esté bien.

**10.1 Onboarding y offboarding de empleados**

**10.1.1 Onboarding**

Al ingresar un empleado se ejecutan los siguientes pasos en orden, documentados como checklist firmable. Creación de identidad en SSO interno con MFA obligatoria activada antes del primer login. Asignación a grupos según rol (engineering, ops, customer success, sales) con permisos mínimos del rol. Firma de NDA y políticas internas (uso aceptable, manejo de información). Aceptación documentada del Plan de Seguridad. Capacitación inicial: este documento, OWASP Top 10, manejo de incidentes, proceso de just-in-time access. Equipamiento: laptop con disco cifrado obligatorio (FileVault, BitLocker, LUKS), antivirus actualizado, MDM cuando aplique. Provisión de password manager corporativo. Briefing del equipo y del responsable directo.

**10.1.2 Offboarding**

Al egreso de un empleado, dentro de un día hábil del último día efectivo: revocación de identidad SSO, lo que cascade revoca todos los servicios federados (Keycloak admin, observability, repos privados, cloud consoles); revocación de credenciales no federadas si hubiera (raro); recuperación de equipamiento; recordatorio de obligaciones contractuales post-empleo (confidencialidad, no competencia donde aplique); auditoría de actividad reciente del empleado para verificar que no se ejecutaron operaciones inusuales antes de la salida; confirmación de que no quedaron tokens activos.

**10.2 Acceso de empleados a producción**

El acceso de empleados a producción es uno de los puntos más sensibles. Las reglas son:

- Acceso permanente a producción: ninguno. La cuenta del empleado en cloud no tiene permisos directos de acceso.

- Acceso just-in-time: cuando se necesita acceso a producción para debug o soporte autorizado, se sigue el procedimiento JIT documentado. El empleado abre ticket interno con justificación; otro empleado autorizado lo aprueba; se otorga rol con TTL máximo 4 horas; toda actividad se registra; al expirar, se revoca automáticamente.

- Acceso a datos del tenant solo con autorización explícita del tenant (ticket de soporte donde el tenant pide el acceso) o por incidente activo de seguridad. La actividad queda en audit_logs con tag jit=true y se reporta al tenant en el resumen mensual de actividad.

- Sin shared accounts: cada empleado actúa con su propia identidad. Las service accounts existen para workloads, no para empleados.

- MFA obligatoria para SSO interno y para todo paso de privilege escalation.

**10.3 Equipamiento y dispositivos**

Política de equipos: los empleados pueden usar equipos personales (BYOD) o corporativos. En cualquier caso se exige: disco cifrado, OS actualizado, antivirus activo, screen lock automático en menos de 10 minutos, no compartir el equipo con familia para tareas de trabajo. Equipos corporativos están bajo MDM cuando aplique. Equipos personales operan bajo política de uso aceptable firmada. La conexión a recursos sensibles requiere SSO + MFA por sesión, lo cual neutraliza buena parte del riesgo de equipo perdido.

**10.4 Gestión de proveedores y subprocessors**

Antes de incorporar un nuevo subprocessor (proveedor que procesará datos del tenant) se realiza evaluación de seguridad y privacidad: revisión de su propia documentación de seguridad, certificaciones vigentes, cláusulas contractuales (DPA), región de procesamiento. La sección 12.1 contiene el inventario actual. Cambios a la lista se notifican a tenants con preaviso razonable, con derecho del tenant a oponerse motivadamente.

**10.5 Gestión de cambios**

Cambios a infraestructura productiva siguen workflow estándar: PR con código IaC, review, plan de despliegue, ejecución supervisada, validación post-cambio. Cambios de emergencia (incidente activo, vulnerabilidad zero-day) pueden saltearse parcialmente la revisión, pero requieren retrospectiva post-incidente y documentación obligatoria del cambio aplicado. La política prohíbe cambios manuales en producción sin trazabilidad.

**10.6 Política de uso aceptable de IA y herramientas externas**

Dado que el desarrollo del producto se apoya intensivamente en agentes de IA y herramientas de productividad externas, la política regula explícitamente qué se puede y qué no se puede compartir con esas herramientas.

- Permitido: código del producto, ADRs, documentación, planes técnicos, datos de prueba sintéticos.

- No permitido: dumps de base de datos productiva, payloads reales con PII de tenants, secretos en cualquier forma, configuración con credenciales.

- Caso límite (logs de producción para debug): solo después de sanitización, preferentemente con datos sintéticos equivalentes.

- Herramientas usadas se enumeran en política y se revisan trimestralmente; se prefieren las que ofrecen modo zero-data-retention o análogo.

**10.7 Capacitación continua**

Sesiones internas trimestrales de seguridad: lecciones aprendidas de incidentes propios y de industria, novedades regulatorias, refresh de procedimientos. Asistencia obligatoria. Las sesiones se graban para quienes no puedan asistir y se mantienen en repositorio interno con TTL de 12 meses.

**11. Roadmap de madurez del programa**

Esta sección declara la evolución prevista del programa de seguridad: qué controles que hoy son procedimentales o manuales se automatizarán, qué certificaciones se persiguen, en qué horizonte temporal y con qué hitos verificables. El roadmap no es una lista de deseos: es un compromiso público con tenants, asesores y eventualmente auditores. Su revisión es semestral; los desvíos se justifican por escrito y se comunican.

**11.1 Modelo de madurez asumido**

La organización adopta como referencia un modelo de madurez de cinco niveles —inicial, repetible, definido, gestionado, optimizado— compatible con CMMI y con los estadíos típicos de programas de seguridad descritos en BSIMM y SAMM. La autoevaluación al cierre de Ola 0 ubica a deRuedas en el límite entre los niveles repetible y definido en la mayoría de las áreas: hay procesos documentados pero no todos están automatizados ni medidos sistemáticamente. La meta a 24 meses es alcanzar nivel gestionado, con métricas de programa estables y revisión continua.

**11.2 Hitos por horizonte**

**11.2.1 Horizonte 0-6 meses (Ola 1)**

Foco: cubrir los gaps críticos para operar con tenants reales y para sostener conversaciones de infosec con clientes medianos.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| Política de privacidad pública publicada | Documento publicado en deruedas.com/privacidad con versionado público. |
| Términos de servicio actualizados a régimen B2B SaaS | ToS firmable por tenants al alta. |
| DPA estandar para tenants | Plantilla aprobada por asesoría legal; firmada por todos los tenants Ola 1. |
| Inventario completo de subprocessors publicado | Sección 12.1 mantenida y publicada en deruedas.com/subprocessors. |
| Procedimiento JIT documentado y ejercitado | Runbook + 3 ejecuciones reales documentadas. |
| Status page pública | status.deruedas.com con incidentes históricos visibles. |
| Tabletop exercise de respuesta a incidente P0 | Reporte interno con findings y action items. |
| Primera auditoría externa de seguridad técnica | Vendor reputado realiza pentest blackbox y graybox; report con findings clasificados. |
| Política de bug bounty/responsible disclosure publicada | Página deruedas.com/security con canal y SLA de respuesta. |

**11.2.2 Horizonte 6-12 meses (Ola 2)**

Foco: automatización de controles que hoy son manuales, refuerzo de cifrado y autenticación, primera certificación formal.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| MFA obligatoria para todos los roles del producto | Configuración del realm Keycloak. Comunicación previa a tenants. |
| Signed commits obligatorios y signatures verificadas en CI | Branch protection actualizada; CI rechaza commits sin firma. |
| Imágenes Docker firmadas con cosign y verificadas en deploy | Policy del registry y del orquestador. |
| Tooling de PAM (Privileged Access Management) para JIT | Sistema dedicado reemplaza el procedimiento manual. |
| SIEM/correlación de logs de seguridad | Reglas de detección activas; runbooks por alerta. |
| Inicio formal de auditoría SOC 2 Type I | Vendor de auditoría contratado, gap analysis cerrado, plan de remediación. |
| Hash chain en audit_logs con verificación periódica | Implementado y verificado en CI. |
| DPIA (evaluación de impacto a la privacidad) para flujos sensibles | Documento por flujo sensible; revisión semestral. |
| Penetration testing externo anual | Reporte; findings cerrados o con plan de remediación. |

**11.2.3 Horizonte 12-24 meses (Ola 3 y posteriores)**

Foco: certificaciones formales, programa de bug bounty, supply chain madura.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| SOC 2 Type I obtenido | Reporte de auditor independiente; publicación bajo NDA a tenants. |
| SOC 2 Type II en preparación | Período de observación iniciado (mínimo 6 meses). |
| ISO 27001 alcance definido y gap analysis | Plan de implementación con roadmap a 18 meses. |
| Programa de bug bounty público | Plataforma activa (HackerOne, Intigriti o equivalente); recompensas y scope publicados. |
| SLSA level 2 en supply chain | Provenance verificable en cada release. |
| DR completo cross-region ejercitado anualmente con éxito | Reporte del ejercicio. |
| Cifrado de campo extendido a más PII (no solo secretos) | Búsquedas con tokenización; anclaje en ADR específico. |
| Programa de privacy by design formalizado | DPIA obligatoria para todo nuevo flujo que toca PII; revisión por privacy champion. |

**11.3 Métricas del programa**

Las siguientes métricas se reportan trimestralmente al equipo de dirección y semestralmente a tenants enterprise que lo soliciten contractualmente.

- Cobertura: porcentaje de tablas con tenant_id que tienen política RLS activa (objetivo: 100%, siempre); porcentaje de endpoints con dependency de auth (objetivo: 100% excepto health/metrics declarados); porcentaje de operaciones sensibles con auditoría (objetivo: 100%).

- Calidad de detección: MTTD por severidad; cantidad de incidentes detectados por automatización vs por reporte manual.

- Calidad de respuesta: MTTR por severidad; porcentaje de incidentes con postmortem en plazo; porcentaje de action items de postmortem cerrados a 30/90 días.

- Higiene de identidades: porcentaje de empleados con MFA activa (objetivo: 100%); cantidad de cuentas inactivas \>90 días (objetivo: 0); cantidad de credenciales sin rotar en \>12 meses (objetivo: 0).

- Higiene de dependencias: cantidad de vulnerabilidades críticas en producción (objetivo: 0); SLA de remediación; edad media de dependencias respecto a última versión.

- Continuidad: éxito de pruebas de restore mensuales (objetivo: 100%); RTO real medido en ejercicios anuales vs RTO declarado.

- Privacidad: cantidad de derechos de titulares atendidos; tiempo medio de respuesta; cantidad de notificaciones a AAIP.

**11.4 Auditorías externas**

La organización se compromete a las siguientes auditorías externas periódicas, ejecutadas por terceros independientes.

|  |  |  |
|:---|:---|:---|
| **Auditoría** | **Frecuencia** | **Output esperado** |
| Penetration test técnico | Anual + bajo demanda tras cambios mayores | Reporte ejecutivo y técnico; findings clasificados; plan de remediación. |
| Revisión de privacidad y compliance | Anual | Reporte legal sobre cumplimiento Ley 25.326 y eventual GDPR. |
| Auditoría SOC 2 Type I | Una vez al alcanzar el hito | Reporte SOC 2 entregable a tenants enterprise. |
| Auditoría SOC 2 Type II | Anual una vez certificado | Reporte tipo II. |
| Code audit independiente de módulos críticos | Bajo demanda | Revisión específica de módulos de auth, RLS, cifrado, multi-tenant. |
| Vendor security assessment a subprocessors críticos | Anual | Confirmación documentada de que sus controles siguen vigentes. |

**11.5 Programa de responsible disclosure y bug bounty**

Mientras el programa formal de bug bounty no esté operativo, deRuedas mantiene un canal de responsible disclosure: la página deruedas.com/security publica el correo security@deruedas.com (cifrado con PGP cuyas claves se publican), un compromiso de respuesta inicial en 48 horas, un compromiso de no acciones legales contra investigadores que actúen de buena fe y un safe harbor explícito. La política se inspira en el estándar disclose.io y se mantiene compatible para una transición sin fricción a un programa público con recompensas a partir de Ola 3.

**12. Plantillas de respuesta a infosec questionnaires de clientes**

Cuando una agencia mediana o grande evalúa contratar deRuedas, su equipo de IT o seguridad suele enviar un cuestionario estructurado de seguridad y privacidad. Las preguntas se repiten significativamente entre cuestionarios. Esta sección consolida respuestas pre-aprobadas para las preguntas más frecuentes, listas para copiar-adaptar, y enumera los documentos públicos que deRuedas pone a disposición de manera estable.

**Aplicación:** Las respuestas siguientes describen el estado objetivo al cierre de Ola 1. Antes de enviar respuestas a un cliente, el responsable comercial valida con el responsable de seguridad que las afirmaciones siguen vigentes y agrega evidencia específica donde el cliente la solicite (logs reales sanitizados, capturas de configuración, certificaciones vigentes).

**12.1 Documentos públicos disponibles**

La organización mantiene los siguientes documentos públicos accesibles a tenants existentes y prospects bajo NDA cuando aplica.

|  |  |
|:---|:---|
| **Documento** | **Disponibilidad** |
| Política de privacidad | Pública, deruedas.com/privacidad |
| Términos del servicio | Pública, deruedas.com/terminos |
| Resumen ejecutivo de seguridad | Pública, deruedas.com/security |
| Lista actual de subprocessors | Pública, deruedas.com/subprocessors |
| Programa de responsible disclosure | Pública, deruedas.com/security/disclosure |
| Contacto del responsable de privacidad | Pública, privacidad@deruedas.com |
| DPA estándar (Data Processing Agreement) | A solicitud, firmable digital |
| Plan de Seguridad y Compliance (este documento, sanitizado) | Bajo NDA a tenants enterprise que lo soliciten |
| Reportes SOC 2 (cuando estén disponibles) | Bajo NDA, a tenants existentes y prospects calificados |
| Resultados de penetration test reciente, sanitizados | Bajo NDA, resumen ejecutivo |

**12.2 Respuestas a preguntas frecuentes**

**Datos y residencia**

**¿Dónde se almacenan los datos del tenant?**

Los datos productivos se almacenan en infraestructura cloud en la región de Sudamérica (São Paulo). Los backups se replican adicionalmente a una segunda región de Sudamérica (Santiago) para fines de continuidad ante desastres. Algunos componentes auxiliares de observabilidad y mensajería pueden procesar metadatos sanitizados en otras regiones; la lista completa con regiones está publicada en deruedas.com/subprocessors.

**¿Los datos están cifrados en reposo?**

Sí. Todos los volúmenes de base de datos, almacenamiento de objetos y backups están cifrados con AES-256 mediante claves gestionadas por el KMS del proveedor cloud. Adicionalmente, los secretos del tenant (API keys de integraciones, tokens de webhooks) se cifran con cifrado de campo usando una clave derivada por tenant a partir de una master key que reside en KMS y rota anualmente.

**¿Los datos están cifrados en tránsito?**

Sí. Todo el tráfico HTTP usa TLS 1.2 mínimo, con preferencia por TLS 1.3. Esto incluye el tráfico interno entre componentes del cluster, no solo el público. HSTS está habilitado con preload.

**Control de acceso y autenticación**

**¿Cómo se autentican los usuarios?**

La autenticación es centralizada vía Keycloak con OIDC. Las credenciales se hashean con argon2id. Los access tokens (JWT firmados RS256) tienen vida 15 minutos; los refresh tokens viven 7 días con rotación en cada uso. MFA es obligatoria para roles privilegiados (manager y super_admin) y opcional pero disponible para todos los demás usuarios. El intento de login fallido repetido dispara bloqueo temporal exponencial.

**¿Cómo se controla el acceso a los datos?**

Tres capas. Primero, autorización explícita en cada endpoint con dependencies de FastAPI que verifican rol y permisos. Segundo, aislamiento estricto entre tenants mediante Row-Level Security (RLS) de PostgreSQL: políticas activas en toda tabla con tenant_id que filtran automáticamente por el tenant del usuario autenticado. Tercero, tests de aislamiento bloqueantes en CI que verifican el comportamiento entre dos tenants antes de permitir cualquier merge.

**¿Cómo se gestiona el acceso de empleados de deRuedas a los datos del tenant?**

Ningún empleado tiene acceso permanente a datos productivos del tenant. El acceso se otorga mediante un procedimiento de just-in-time con justificación, aprobación por un segundo empleado, TTL máximo de 4 horas y registro completo de la actividad en una bitácora de auditoría que el tenant puede consultar. La política y el runbook están disponibles bajo NDA.

**Privacidad y datos personales**

**¿deRuedas cumple con la Ley 25.326?**

Sí. La sección 6 del Plan de Seguridad detalla el cumplimiento. La organización tiene un responsable interno de protección de datos, un mapa documentado de tratamientos, política de retención por categoría, mecanismos para atender derechos de titulares, plantillas de notificación a la AAIP en caso de incidente y DPA estándar firmable con tenants. La política de privacidad pública detalla bases de licitud y derechos.

**¿deRuedas firma DPAs?**

Sí. La organización tiene una plantilla estándar de Data Processing Agreement compatible con la Ley 25.326 y con principios GDPR, firmable digitalmente al inicio de la relación o a solicitud posterior. Tenants enterprise pueden negociar adendas específicas mediante asesoría legal.

**¿En cuánto tiempo se notifican brechas?**

La política de notificación de incidentes que afectan datos personales es de 72 horas desde la detección, alineada con buenas prácticas internacionales. Los detalles de procedimiento están en la sección 7 del Plan de Seguridad.

**¿Qué subprocessors procesan datos del tenant?**

La lista actual está publicada en deruedas.com/subprocessors. Cambios se notifican a tenants con preaviso razonable y derecho a oposición motivada según los términos del DPA.

**Continuidad y disponibilidad**

**¿Cuáles son los SLAs de disponibilidad?**

La organización ofrece SLA de 99.5% mensual en plan estándar y 99.9% mensual en plan enterprise. La status page pública mantiene historial de incidentes y porcentajes de uptime. Los créditos por incumplimiento están definidos en los términos del servicio.

**¿Cuáles son los RTO/RPO?**

RTO de 1 hora para PostgreSQL primary y 4 horas para DR completo cross-region. RPO de 5 minutos para PostgreSQL con replicación streaming y WAL archive continuo. Detalles por componente en sección 8 del Plan de Seguridad.

**¿Con qué frecuencia se hacen backups y se prueban restores?**

Backups full diarios; WAL archive continuo; snapshot mensual preservado 12 meses; replicación cross-region. Restores se prueban mensualmente en entorno aislado; PITR a punto arbitrario cada trimestre; ejercicio DR cross-region anual.

**Seguridad de aplicación y desarrollo**

**¿Qué prácticas de SSDLC se siguen?**

Code review obligatorio con al menos un approver. Branch protection en main. SAST con ruff y semgrep. SCA con pip-audit, npm audit y Trivy en imágenes. DAST con OWASP ZAP en staging. SBOM generado por release. Gitleaks/trufflehog para detectar secretos. Threat modeling en cambios de arquitectura. Detalles en sección 9 del Plan de Seguridad.

**¿Hay penetration testing periódico?**

Sí. Vendor externo realiza penetration test al menos anualmente y bajo demanda tras cambios arquitectónicos significativos. Reportes se mantienen confidenciales; resumen sanitizado disponible bajo NDA.

**¿Hay programa de bug bounty?**

La organización mantiene un canal de responsible disclosure activo en deruedas.com/security con SLA de respuesta inicial de 48 horas y safe harbor explícito para investigadores. Programa formal de bug bounty con recompensas planificado para Ola 3 según roadmap publicado.

**Certificaciones y auditorías**

**¿deRuedas tiene certificaciones SOC 2 / ISO 27001?**

Las certificaciones formales no están vigentes al momento del MVP. El roadmap está publicado: SOC 2 Type I previsto a 18 meses; SOC 2 Type II y trabajo hacia ISO 27001 a 24-36 meses. Mientras tanto, los controles del programa cumplen sustancialmente con los criterios subyacentes; el Plan de Seguridad detalla los controles vigentes y permite a tenants y auditores verificar el alcance del programa.

**¿El cuestionario de seguridad CAIQ / SIG / VSAQ está completado?**

Sí. Versiones actualizadas trimestralmente del CAIQ Lite, SIG Core o VSAQ se entregan a solicitud bajo NDA. La organización privilegia el formato preferido del solicitante.

**Respuesta a incidentes**

**¿Cómo se notifica al tenant ante un incidente?**

Los plazos de notificación inicial dependen de la severidad: 30 minutos para incidentes críticos, 2 horas para mayores, post-resolución para significativos. La comunicación se hace por email al manager registrado y mediante actualización en status page cuando aplica. Las plantillas de comunicación están en sección 7 del Plan de Seguridad.

**¿Qué información se entrega después de un incidente?**

Resumen post-incidente con cronología, impacto específico para el tenant, causa raíz y plan de remediación. Postmortems internos se realizan dentro de 5 días hábiles bajo cultura sin culpa; resúmenes públicos sanitizados se comparten con tenants afectados.

**13. Anexos**

**13.1 Inventario de subprocessors**

Lista completa de subprocessors que procesan datos del tenant o metadatos asociados. Esta lista se mantiene viva y se publica en deruedas.com/subprocessors. Cambios disparan notificación a tenants con derecho de oposición motivada según los términos del DPA.

|  |  |  |  |
|:---|:---|:---|:---|
| **Subprocessor** | **Función** | **Región** | **Cobertura legal** |
| Cloud provider primario (AWS / GCP / Azure) | Infraestructura: cómputo, BD, storage, KMS | São Paulo (BR) | DPA del proveedor + SCC para transferencia internacional cuando aplique. |
| Cloud provider secundario (DR) | Replicación cross-region | Santiago (CL) o equivalente | DPA del proveedor. |
| Keycloak managed o equivalente | Identidad y autenticación | Región contratada | DPA del proveedor. |
| Meta WhatsApp Cloud API | Mensajería WhatsApp | Estados Unidos / Irlanda | Términos del servicio Meta + DPA aplicable. |
| Sentry o equivalente | Captura de excepciones (sanitizadas) | Estados Unidos / UE | DPA del proveedor + SCC. |
| Loki / observability | Logs centralizados | Región principal | Misma cobertura que cloud provider. |
| SendGrid / proveedor SMTP | Envío de emails transaccionales | Estados Unidos / UE | DPA del proveedor. |
| Cloudflare o equivalente | CDN / WAF / DDoS protection | Edge global | DPA del proveedor. |
| Stripe / proveedor de pagos (futuro) | Procesamiento de cobros del SaaS a tenants | Estados Unidos | DPA del proveedor; PCI-DSS compliance. |

**13.2 Mapa de datos personales (data map)**

Inventario de categorías de datos personales tratados, su finalidad y régimen aplicable.

|  |  |  |  |  |
|:---|:---|:---|:---|:---|
| **Categoría** | **Finalidad** | **Base lícita** | **Retención** | **Destinatarios** |
| Identificación contacto/lead (nombre, DNI opcional) | CRM de la agencia | Consentimiento o interés legítimo (responsable: agencia) | Mientras agencia mantenga; 24m si inactivo | Empleados autorizados del tenant |
| Datos de contacto (tel, email) | Comunicación comercial | Misma que anterior | Misma que anterior | Empleados autorizados del tenant; canales WhatsApp/email |
| Mensajes WhatsApp (contenido + media) | Histórico de comunicación | Misma que anterior + términos Meta | 24 meses | Empleados del tenant; Meta como subprocessor |
| Vehículos consultados, leads | Operación CRM | Interés legítimo | 5 años desde cierre | Empleados del tenant |
| Identidad de usuarios SaaS | Autenticación al producto | Ejecución del contrato (responsable: deRuedas) | Mientras servicio activo + 30 días | deRuedas; Keycloak (subprocessor) |
| Audit logs (incluye IP, user agent) | Trazabilidad y seguridad | Interés legítimo | 24 meses | deRuedas; auditores externos bajo NDA |
| Logs de aplicación (sin PII bruta) | Operación y troubleshooting | Interés legítimo | 90 días | deRuedas; observability provider |
| Datos de empleados deRuedas | Relación laboral | Ejecución del contrato laboral | Por la legislación | RRHH; sistemas internos |

**13.3 Glosario**

Términos técnicos, regulatorios y operativos utilizados en el documento.

|  |  |
|:---|:---|
| **Término** | **Definición** |
| AAIP | Agencia de Acceso a la Información Pública. Autoridad de aplicación de la Ley 25.326 en Argentina. |
| AOF | Append Only File. Mecanismo de persistencia de Redis que registra cada operación para reconstruir el estado tras reinicio. |
| Argon2id | Algoritmo moderno de hashing de passwords, ganador de la Password Hashing Competition. Resistente a ataques con GPU y ASIC. |
| audit_logs | Tabla de auditoría append-only del producto donde se registran las operaciones sensibles. |
| Branch protection | Reglas en el repositorio que restringen merges directos al branch principal y exigen reviews y CI verde. |
| Bug bounty | Programa formal de recompensas por reporte responsable de vulnerabilidades. |
| Bus factor | Cantidad de personas en un equipo cuya pérdida simultánea pondría en jaque la operación. Cuanto más alto, mejor. |
| CAIQ | Consensus Assessments Initiative Questionnaire. Cuestionario estandarizado de seguridad para SaaS, gestionado por la Cloud Security Alliance. |
| Circuit breaker | Patrón que aísla fallas en un servicio externo abriendo el circuito tras N fallas consecutivas y rechazando llamadas inmediatamente durante M segundos. |
| CMMI | Capability Maturity Model Integration. Modelo de madurez de procesos en cinco niveles. |
| Cosign | Herramienta de Sigstore para firma criptográfica de artefactos de software, especialmente imágenes Docker. |
| CSP | Content Security Policy. Header HTTP que restringe qué recursos puede cargar el navegador y reduce el riesgo de XSS. |
| DAST | Dynamic Application Security Testing. Análisis de seguridad sobre la aplicación corriendo, no sobre código fuente. |
| DPA | Data Processing Agreement. Contrato entre responsable y encargado del tratamiento de datos personales. |
| DPIA | Data Protection Impact Assessment. Evaluación formal del impacto sobre la privacidad de un nuevo tratamiento. |
| DPO | Data Protection Officer. Figura del marco europeo análoga al responsable de privacidad. |
| DR | Disaster Recovery. Plan y procedimientos para recuperar el servicio ante eventos disruptivos mayores. |
| DLQ | Dead-Letter Queue. Cola donde van los eventos que no pudieron procesarse tras agotar reintentos, para revisión manual. |
| GDPR | General Data Protection Regulation. Regulación europea de protección de datos personales. |
| HMAC | Hash-based Message Authentication Code. Mecanismo para verificar integridad y autenticidad de un mensaje usando una clave compartida. |
| HSTS | HTTP Strict Transport Security. Header que fuerza al navegador a usar HTTPS para el dominio. |
| IaC | Infrastructure as Code. La infraestructura se declara en código versionado (Terraform, Pulumi, etc.) en lugar de configurarse manualmente. |
| IC | Incident Commander. Rol que coordina la respuesta a un incidente activo. |
| JIT access | Just-In-Time access. Modelo donde no hay accesos permanentes a recursos sensibles; cada uso requiere otorgamiento puntual con TTL. |
| JWT | JSON Web Token. Formato estándar para tokens de identidad firmados criptográficamente. |
| KMS | Key Management Service. Servicio del cloud provider para custodia y rotación de claves criptográficas. |
| MFA | Multi-Factor Authentication. Autenticación que combina algo que el usuario sabe (password) con algo que tiene (token) o algo que es (biometría). |
| MTTD | Mean Time To Detect. Tiempo medio entre el inicio de un incidente y su detección. |
| MTTR | Mean Time To Resolve. Tiempo medio entre la detección y la resolución. |
| OIDC | OpenID Connect. Capa de identidad sobre OAuth 2.0. |
| OWASP | Open Worldwide Application Security Project. Comunidad y conjunto de proyectos de referencia en seguridad de aplicaciones. |
| PAM | Privileged Access Management. Categoría de herramientas para gestión de accesos privilegiados con grabación, aprobación y rotación. |
| PII | Personally Identifiable Information. Datos que permiten identificar a una persona. |
| Pitr | Point-In-Time Recovery. Capacidad de restaurar una base a un instante exacto, no solo a snapshots. |
| RBAC | Role-Based Access Control. Modelo de control de accesos basado en roles. |
| RLS | Row-Level Security. Capacidad de PostgreSQL para filtrar filas a nivel de motor según una política. |
| RPO | Recovery Point Objective. Pérdida máxima de datos aceptable, medida en tiempo. |
| RTO | Recovery Time Objective. Tiempo máximo aceptable de indisponibilidad de un componente. |
| SAST | Static Application Security Testing. Análisis de seguridad sobre código fuente. |
| SBOM | Software Bill of Materials. Inventario de los componentes (incluyendo dependencias transitivas) que componen un software. |
| SCA | Software Composition Analysis. Análisis de las dependencias de software para detectar vulnerabilidades conocidas. |
| SCC | Standard Contractual Clauses. Cláusulas contractuales tipo aprobadas para legitimar transferencias internacionales de datos. |
| SDLC / SSDLC | Secure Software Development Life Cycle. Ciclo de desarrollo con seguridad integrada en cada fase. |
| SIEM | Security Information and Event Management. Plataforma de correlación y análisis de eventos de seguridad. |
| SLA | Service Level Agreement. Compromiso contractual de nivel de servicio. |
| SLO | Service Level Objective. Objetivo interno de nivel de servicio, generalmente más estricto que el SLA. |
| SOC 2 | Service Organization Control 2. Reporte de auditoría sobre controles de una organización de servicios. Type I es a un punto en el tiempo; Type II es a lo largo de un período. |
| SSO | Single Sign-On. Autenticación única que da acceso a múltiples servicios federados. |
| STRIDE | Modelo de Microsoft para clasificar amenazas: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege. |
| TLS | Transport Layer Security. Protocolo de cifrado en tránsito (sucesor de SSL). |
| TOTP | Time-based One-Time Password. Algoritmo estándar de generación de códigos OTP usado en apps de MFA. |
| WAF | Web Application Firewall. Firewall específico para tráfico web HTTP/HTTPS. |
| XSS | Cross-Site Scripting. Vulnerabilidad que permite inyectar JavaScript que se ejecuta en el navegador de otros usuarios. |

**13.4 Control de versiones del documento**

|  |  |  |  |
|:---|:---|:---|:---|
| **Versión** | **Fecha** | **Autor** | **Cambios** |
| 1.0 | Mayo 2026 | Equipo de seguridad deRuedas | Versión inicial. Cubre Olas 0 y 1 con roadmap a Ola 3. |

La próxima revisión está prevista para noviembre de 2026 al cierre de la Ola 1, donde se actualizarán: estado real de cada control respecto a lo planificado, hallazgos del primer pentest externo, ajustes de la matriz de riesgos según incidentes ocurridos y feedback de tenants Ola 1, avance del roadmap hacia SOC 2 Type I.
