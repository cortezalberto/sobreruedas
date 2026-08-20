**Plan de Operaciones**

**y SRE**

***deRuedas Gestión***

SLOs, observabilidad, on-call, runbooks,

capacity planning y gestión de cambios

*Cierre del cuerpo técnico del SDD · Roadmap de madurez SRE*

Versión 1.0 — Mayo de 2026

**1. Introducción y propósito**

Este documento es complementario al cuerpo SDD de deRuedas Gestión y se ocupa de una dimensión que las capas anteriores tocan tangencialmente pero no consolidan: la operación sostenida del producto en producción. La spec técnica describe la arquitectura del sistema; el plan de implementación lleva esa arquitectura al código; el plan de seguridad cubre lo defensivo; el plan de testing cubre la calidad pre-release. Pero ninguno de esos documentos detalla cómo se mantiene vivo el producto día tras día: cómo se mide su salud, cómo se detecta cuándo empieza a degradarse, quién responde a las alertas, qué se hace cuando algo se rompe a las tres de la mañana, cómo se planifica el crecimiento de la infraestructura en función de la carga real. Este documento llena ese vacío.

La existencia del documento se justifica por tres razones convergentes. La primera es contractual: cuando deRuedas firme contratos con agencias medianas o grandes, el SLA declarado va a ser parte del contrato y necesita estar respaldado por un programa operativo capaz de cumplirlo. Sin SLOs internos más estrictos que el SLA, sin observability adecuada y sin procedimientos de respuesta, el SLA es promesa vacía que el primer incidente desnuda. La segunda es operativa: la operación de un SaaS multi-tenant que procesa datos comerciales sensibles y comunicaciones por WhatsApp tiene complejidad real que no se sostiene con improvisación; cada decisión que se toma en caliente sin marco previo cuesta horas y a veces clientes. La tercera es organizacional: el programa SRE es lo que permite que el equipo crezca sin que cada nueva persona tenga que aprender por accidente cómo funciona la operación; los runbooks documentados, las rotaciones explícitas y las métricas trackeadas son el conocimiento institucional codificado.

**1.1 SRE como filosofía**

El programa adopta la filosofía SRE (Site Reliability Engineering) tal como fue desarrollada por Google y popularizada en los libros homónimos. La idea central es que la confiabilidad del servicio se trata como problema de ingeniería, no como problema de operaciones manuales. Las consecuencias prácticas son varias. Las decisiones sobre disponibilidad se toman cuantitativamente con SLOs declarados, no cualitativamente con “queremos que esté siempre arriba”. La operación se automatiza agresivamente porque el toil manual no escala. Los incidentes se tratan con cultura sin culpa porque la confiabilidad es propiedad del sistema, no responsabilidad individual. La disciplina de operación es tan rigurosa como la disciplina de desarrollo, y los dos roles colaboran en lugar de adversarse.

La adopción es pragmática, no dogmática. deRuedas en su MVP no tiene equipo dedicado de SRE: las funciones se distribuyen entre los desarrolladores con rotación de on-call. Esto cambia algunas prácticas respecto del modelo Google clásico —por ejemplo, no hay un “error budget de SRE” que detiene desarrollo cuando se quema, porque las mismas personas hacen ambas cosas— pero conserva la disciplina central: SLOs declarados, observability explícita, runbooks por alerta, postmortems sin culpa, y mejora continua basada en métricas.

**1.2 Audiencia**

El documento tiene cuatro audiencias diferenciadas. Para el equipo técnico —desarrolladores, eventual SRE dedicado en olas posteriores— funciona como referencia operativa de cómo se observa, alerta, responde y mejora la operación del producto. Para el equipo comercial y customer success funciona como insumo para responder consultas de tenants sobre disponibilidad y para gestionar comunicación durante incidentes. Para tenants enterprise que evaluen el programa de operaciones del proveedor, funciona como documento entregable bajo NDA con detalle suficiente para auditoría. Para la dirección de la organización, funciona como instrumento de gestión: las métricas reportadas dan visibilidad real sobre la salud del producto y del equipo.

**1.3 Posición frente al cuerpo SDD**

El plan de operaciones SRE se diferencia del plan de seguridad por foco aunque ambos toquen temas como respuesta a incidentes y RTO/RPO. La regla operativa es la siguiente: el plan de seguridad cubre lo defensivo (qué hacer cuando hay un atacante o un incidente que afecta confidencialidad, integridad o privacidad regulatoria); el plan SRE cubre la operación normal y los incidentes de disponibilidad o performance que no involucran adversarios. Los dos planos se solapan en algunos puntos —cuando un incidente operativo escala a incidente de seguridad, los procedimientos se entrelazan— y se referencian cruzadamente cuando corresponde.

**1.4 Estructura del documento**

El documento está organizado en catorce capítulos. El segundo establece los principios SRE adoptados. El tercero define el modelo de servicio, los SLAs públicos, los SLOs internos y los SLIs concretos por componente. El cuarto desarrolla la observabilidad: stack adoptado, métricas obligatorias, dashboards canónicos. El quinto trata las alertas con su filosofía de accionabilidad. El sexto cubre el on-call: estructura de rotación, compensación, runbooks por alerta, escalación. El séptimo entrega los runbooks principales del producto. El octavo aborda capacity planning. El noveno trata gestión de cambios y deploys. El décimo cubre la gestión de incidentes operativos diferenciada de la de seguridad. El décimo primero desarrolla toil y automatización. El décimo segundo aborda los costos operativos (FinOps básico). El décimo tercero presenta el roadmap de madurez del programa. El décimo cuarto cierra con anexos: plantillas y glosario.

**2. Principios SRE adoptados**

Esta sección declara los principios que el programa de operaciones adopta. Como en otras dimensiones del cuerpo SDD, los principios son accionables: cada uno se puede usar para evaluar si una decisión operativa concreta lo respeta o lo viola. Algunos derivan directamente del cuerpo SDD —especialmente del principio constitucional P7 de resiliencia y degradación elegante— y se reformulan aquí en términos operativos.

**2.1 Principio O1 — Confiabilidad cuantificada, no aspiracional**

La confiabilidad del producto se declara cuantitativamente con SLOs específicos por componente, medibles automáticamente y reportables. El concepto vago de “está siempre arriba” no es admisible: cada componente tiene su SLO formal con porcentaje de cumplimiento medido en ventana definida. Las decisiones que afectan la confiabilidad —invertir en automatización vs en features, postergar un release, escalar un componente— se toman contra los SLOs y los presupuestos de error, no contra opiniones. Esto produce conversaciones honestas sobre tradeoffs en lugar de discusiones políticas sobre prioridades.

**2.2 Principio O2 — El presupuesto de error es real**

El SLO del 99.5% mensual no significa “queremos cero downtime”: significa explícitamente que se aceptan hasta 3.6 horas de downtime mensuales como costo razonable de seguir entregando valor. Ese tiempo es presupuesto de error que el equipo gasta en releases nuevas, en cambios arquitectónicos, en experimentación. La consecuencia operativa es que cuando el presupuesto se gasta antes del fin del período (un incidente largo se llevó las 3.6 horas en la primera semana del mes), el equipo cambia el modo: prioriza estabilidad sobre features hasta el inicio del próximo período. La decisión no es discrecional: es respuesta automática a la métrica.

**2.3 Principio O3 — Toil eliminado activamente**

El toil es el trabajo manual repetitivo y reactivo que no produce valor permanente: ejecutar un script que debería estar automatizado, contestar la misma consulta del cliente quinta vez, ajustar a mano un valor que debería autoescalar. El programa adopta como norma que el toil se mide, se reporta y se reduce. Cuando un miembro del equipo gasta más del 50% de su tiempo en toil durante un período, se considera disfunción operativa y se actúa: se prioriza un proyecto de automatización, se redistribuye carga, se contrata. La definición operativa de toil y su tracking se desarrollan en el capítulo 11.

**2.4 Principio O4 — Automatización por defecto**

Cualquier tarea operativa que se ejecute más de dos veces es candidata a automatizarse. La política no es ideológica: cuando el costo de automatizar excede el beneficio (tarea que se ejecuta una vez al año, complejidad alta de automatización), la excepción se justifica explícitamente. Pero la presunción es que automatizar es la opción correcta. Esto incluye no solo tareas técnicas (deploys, rotación de credenciales, restore de backups) sino procesos administrativos (creación de tickets, escalado de alertas, generación de reportes mensuales).

**2.5 Principio O5 — Observabilidad como propiedad obligatoria**

Ningún componente entra a producción sin observabilidad adecuada. La política específica es que cada componente debe emitir métricas que permitan responder tres preguntas: ¿el componente está vivo y respondiendo? ¿está respondiendo dentro de SLO? ¿está siendo usado significativamente o está ocioso? Sin estas tres preguntas respondibles desde una métrica, el componente no es deployable. Esta exigencia no es burocrática: es lo que vuelve viable diagnosticar cualquier incidente sin reverse engineering bajo presión.

**2.6 Principio O6 — Alertas accionables, no informativas**

Cada alerta que despierta a una persona debe tener acción concreta esperada. Si la respuesta a una alerta es “sí, ya sé” o “esto pasa siempre, ignorala”, la alerta es ruido y se elimina o se ajusta. La política de alertas se desarrolla en el capítulo 5 pero la regla central es que el ruido es enemigo de la atención: una alerta falsa erosiona la confianza en la siguiente alerta verdadera. El equipo audita el ruido de alertas mensualmente y elimina las que no cumplen accionabilidad.

**2.7 Principio O7 — Postmortems sin culpa**

Todo incidente operativo de severidad media o alta genera postmortem dentro de cinco días hábiles. La cultura es estricta: la pregunta es qué condiciones del sistema permitieron el incidente, no quién lo provocó. Esto se materializa en lenguaje neutro (“la configuración X permitió Y”, no “Juan configuró mal Y”) y en foco en cambios al sistema (cambios de código, runbooks actualizados, alertas mejoradas) en lugar de cambios a las personas. La cultura sin culpa no es complacencia: es la única manera de obtener información honesta sobre qué pasó realmente, sin la cual la mejora es imposible.

**2.8 Principio O8 — Simplicidad como valor**

La complejidad operativa se trata como costo, no como sofisticación. Antes de adoptar una herramienta nueva o introducir un componente más, el programa pregunta: ¿el problema que resuelve justifica la complejidad operativa que agrega? Tres dashboards complejos son peores que uno simple y útil. Una arquitectura con cinco servicios bien observados es mejor que una con doce mal observados. La preferencia por simplicidad atraviesa decisiones de stack, de tooling, de procesos.

**2.9 Principio O9 — Confiabilidad en producción importa más que perfección en diseño**

Un componente que funciona en producción y se monitorea adecuadamente vale más que uno con arquitectura ideal pero opacidad operativa. La política es que si hay tradeoff entre elegancia arquitectónica y observabilidad, gana la observabilidad. Esto puede significar agregar logs verbosos en componentes críticos, exponer métricas que rompen abstracciones, mantener APIs operativas internas que ofenden a los puristas. La justificación es pragmática: cuando algo se rompe a las tres de la mañana, lo que importa es poder diagnosticarlo, no que el código sea bonito.

**2.10 Principio O10 — La operación es responsabilidad compartida**

Los desarrolladores que escriben el código son los mismos que están en on-call para responder cuando ese código falla. La consecuencia es virtuosa: el incentivo para escribir código observable, resiliente y bien instrumentado es directo, porque el costo del código mal instrumentado lo paga el mismo que lo escribió. La política aplica también al agente de IA en la medida en que produce código: las tareas del plan que el agente ejecuta deben incluir, como parte del Definition of Done, la observabilidad correspondiente. Un PR sin métricas adecuadas no es completable.

**Resumen operativo:** Los diez principios anteriores se condensan en una idea: la operación del producto se trata como problema de ingeniería con disciplina cuantitativa, no como reacción manual a problemas que aparecen. Esto exige inversión inicial real (observabilidad, runbooks, automatización) que paga su costo en estabilidad sostenida y en escalabilidad organizacional.

**3. Modelo de servicio: SLAs, SLOs, SLIs**

Esta sección define el modelo cuantitativo de confiabilidad del producto. Distingue tres niveles relacionados pero distintos: el SLA (Service Level Agreement) es el compromiso público con el tenant, parte del contrato; el SLO (Service Level Objective) es el objetivo interno del equipo, más estricto que el SLA, lo que se busca cumplir realmente; el SLI (Service Level Indicator) es la métrica concreta que se mide para evaluar SLO y SLA. Esta sección declara los tres niveles para deRuedas Gestión, los presupuestos de error derivados y las políticas que disparan cuando los presupuestos se gastan.

**3.1 SLAs públicos por plan**

El SLA es lo que deRuedas se compromete a cumplir con el tenant en el contrato. La estructura por plan es la siguiente y se publica en deruedas.com/sla. Los créditos por incumplimiento son automáticos: el tenant no debe pedirlos, deRuedas los acredita proactivamente cuando los detecta.

|  |  |  |  |
|:---|:---|:---|:---|
| **Plan** | **Disponibilidad mensual** | **Downtime aceptable** | **Crédito por incumplimiento** |
| Starter | 99.0% | 7h 12min / mes | 5% de la suscripción mensual |
| Pro | 99.5% | 3h 36min / mes | 10% de la suscripción mensual |
| Enterprise | 99.9% | 43min / mes | 25% de la suscripción mensual |

**Definición de downtime:** Para los SLAs, downtime es el período durante el cual la API principal no responde 200 OK a un health check válido o devuelve 5xx en más del 25% de las requests durante ventanas de 5 minutos consecutivas. Excluyen del cálculo: ventanas de mantenimiento programadas y comunicadas con 72 horas de anticipación; degradación causada por uso fuera del fair use declarado; degradación causada por fallas de proveedores externos no atribuibles a deRuedas (cuando el tenant accede a través de Internet inestable propio).

**3.2 SLOs internos**

Los SLOs son objetivos internos del equipo, sistemáticamente más estrictos que los SLAs públicos. Esto deja margen entre el SLO interno y el SLA externo: cuando el SLO se rompe, el equipo todavía está a salvo del SLA y tiene tiempo de actuar antes de impactar al tenant. La distancia entre SLO y SLA es presupuesto de gestión: la organización busca cumplir el SLO siempre y solo recurre a la holgura del SLA en eventos extraordinarios.

|  |  |  |  |
|:---|:---|:---|:---|
| **SLO** | **Objetivo** | **Ventana** | **SLI asociado** |
| Disponibilidad de la API principal | 99.7% | 30 días rolling | Health check + 5xx rate |
| Latencia p95 de endpoints típicos | \<300 ms | 30 días rolling | histogram de latencia |
| Latencia p95 de búsqueda compleja | \<2.0 s | 30 días rolling | histogram de latencia ruta /search |
| Disponibilidad de webhooks entrantes (Meta) | 99.9% | 30 días rolling | Tasa de 200 OK ante POST de webhook |
| Latencia de procesamiento de mensajes WhatsApp entrantes | p95 \<30 s desde recepción a persistencia | 7 días rolling | Time desde webhook a persisted_at |
| Disponibilidad del frontend web | 99.8% | 30 días rolling | Synthetic check + 5xx en assets críticos |
| Cumplimiento de RPO de PostgreSQL | 100% backups exitosos | 30 días | Backup verification job |
| Disponibilidad de la cola de eventos | 99.95% | 30 días rolling | Redis ping + producer ack rate |
| Lag máximo de consumers de eventos | p99 \<60 s | 7 días rolling | Lag medido por consumer group |
| Tasa de eventos en DLQ | \<0.1% del volumen total | 7 días rolling | DLQ size vs total throughput |

**3.3 SLIs concretos por componente**

Los SLIs son las métricas reales que se miden. Cada SLO se ata a uno o varios SLIs. La política es que los SLIs se obtienen de la perspectiva del usuario cuando es posible: medir lo que el usuario experimenta es más fiel que medir lo que la infraestructura reporta. Por ejemplo, la disponibilidad de la API se mide desde el monitor sintético externo (que ejecuta requests reales contra producción cada 30 segundos desde otra red), no desde el load balancer interno; esto captura problemas que el LB no ve.

**3.3.1 SLIs de la API principal**

|  |  |
|:---|:---|
| **SLI** | **Cálculo** |
| Disponibilidad | % de requests sintéticos a /health/live que devuelven 200 OK en ventana de 5 minutos. Se promedia sobre la ventana del SLO. |
| Tasa de error | % de requests no-2xx (excluyendo 4xx legítimos del cliente) sobre el total. |
| Latencia p95 | Percentil 95 del histograma de latencias por endpoint en ventana de 1 minuto, agregado al período del SLO. |
| Latencia p99 | Percentil 99 del mismo histograma. Se monitorea pero no es SLO directo. |
| Throughput | Requests por segundo agregado, no es SLO pero es señal capacity-related. |

**3.3.2 SLIs de PostgreSQL**

|  |  |
|:---|:---|
| **SLI** | **Cálculo** |
| Disponibilidad del primary | % de tiempo en que el primary acepta conexiones y queries. |
| Replication lag a réplicas | Lag en segundos entre primary y replicas (objetivo \<5s). |
| Query latency p95 | Percentil 95 de duración de queries del rol app, excluyendo queries administrativas. |
| Connection pool utilization | % de conexiones usadas vs configuradas. Alerta si \>80% sostenido. |
| Backup success rate | % de backups diarios exitosos en últimos 30 días (objetivo 100%). |
| Storage utilization | % de disco usado vs aprovisionado por nodo. |

**3.3.3 SLIs de procesamiento async**

|  |  |
|:---|:---|
| **SLI** | **Cálculo** |
| Worker availability | % de workers en estado healthy del total esperado por deployment. |
| Queue lag por stream | Diferencia entre offset publicado y offset consumido por consumer group. |
| Tasa de eventos procesados exitosos | Eventos completados sin error / total publicados, ventana de 1 hora. |
| DLQ size | Cantidad de eventos en DLQ en momento dado y tendencia (creciendo / estable / decreciendo). |
| Tiempo de procesamiento por event_type | p95 de duración desde consumo hasta ack, segmentado por tipo de evento. |

**3.3.4 SLIs de integraciones externas**

|  |  |
|:---|:---|
| **SLI** | **Cálculo** |
| Tasa de éxito de envíos a WhatsApp | Mensajes con respuesta 200 / total enviados. |
| Latencia p95 de envíos a WhatsApp | Tiempo desde request hasta respuesta de WhatsApp Cloud API. |
| Tasa de circuit breaker abierto (WhatsApp) | % de tiempo con CB en estado open en ventana del SLO. |
| Tasa de éxito de publicaciones al portal | Publicaciones exitosas / intentos. |
| Tasa de webhooks entrantes válidos | Webhooks con HMAC válida / total recibidos. |

**3.4 Presupuesto de error**

El presupuesto de error es el complemento del SLO. Si el SLO de disponibilidad es 99.7% mensual, el presupuesto de error es 0.3% mensual, equivalente a aproximadamente 130 minutos de downtime aceptable. Ese presupuesto es activo gestionable: cada incidente lo consume; cuando el presupuesto se gasta, la organización responde de manera diferente a cuando hay holgura. La política operativa es la siguiente, segmentada por porcentaje de presupuesto remanente al cierre de cada semana del período.

|  |  |
|:---|:---|
| **Estado del presupuesto** | **Política operativa** |
| Más del 75% del presupuesto remanente | Modo normal. El equipo puede priorizar features. Releases regulares. Experimentación con cambios riesgosos contemplada. |
| Entre 25% y 75% remanente | Modo precaución. Releases siguen pero los cambios riesgosos requieren justificación adicional. Se prioriza estabilidad incremental sobre features nuevas. |
| Menos del 25% remanente | Modo protección. Solo releases de bugfix y mejoras de estabilidad. Features nuevas se postergan al próximo período. El equipo dedica al menos 30% del tiempo a hardening. |
| Presupuesto agotado o negativo | Freeze de releases no críticos. Solo hotfixes que reduzcan el riesgo de incidentes futuros. Postmortem extendido del período. Revisión de SLO si la situación se repite. |

**Sobre el freeze automático:** El cambio de modo no requiere decisión política: lo dispara la métrica. La transparencia evita que la decisión “se posterga el feature X” se viva como castigo o autoridad arbitraria; es respuesta automática a un instrumento que el propio equipo aceptó.

**3.5 Service tiers**

No todos los componentes del producto requieren el mismo nivel de inversión en confiabilidad. La política adopta tres tiers que orientan dónde concentrar esfuerzo y dónde aceptar holgura.

|  |  |  |
|:---|:---|:---|
| **Tier** | **Componentes** | **Política** |
| Tier 1 — Crítico | API principal, PostgreSQL, autenticación, webhooks WhatsApp | SLOs estrictos, alertas P0, on-call activo, runbooks completos, monitoreo sintético externo, redundancia obligatoria, backups con RPO de minutos. |
| Tier 2 — Importante | Workers de eventos, búsqueda OpenSearch, integraciones salientes, frontend web | SLOs declarados, alertas P1, runbooks principales, monitoreo interno, redundancia recomendada. |
| Tier 3 — Soporte | Pipelines de CI/CD, sistema de observability, herramientas internas | SLOs aspiracionales, alertas P2-P3, runbooks básicos, recuperación manual aceptable. |

**3.6 Reportes públicos de cumplimiento**

Los SLAs cumplidos se reportan mensualmente al tenant en su portal con tres elementos: el porcentaje real de disponibilidad medido en el período, los incidentes ocurridos con sus impactos, los créditos aplicados si los hubo. La transparencia es ventaja competitiva: tenants enterprise valoran proveedores que reportan honestamente sobre proveedores que evitan el tema. Los reportes son automatizados desde las métricas de SLI; ningún humano edita números antes de publicarlos.

**3.7 Revisión de SLOs**

Los SLOs declarados no son inmutables: se revisan trimestralmente con datos reales. Cuando un SLO se cumple consistentemente sin esfuerzo (95%+ del presupuesto remanente al cierre del período durante tres meses seguidos), se considera apretarlo. Cuando un SLO se incumple persistentemente a pesar de inversión razonable, se considera relajarlo y comunicar el cambio al tenant si afecta el SLA. El SLO no es opinión: es contrato del equipo consigo mismo, y un contrato que no refleja la realidad pierde su función orientadora.

**4. Observabilidad**

Esta sección define cómo se observa el sistema en producción: qué se mide, dónde se almacena, cómo se consulta. La premisa es que la observabilidad no es lujo sino requisito operacional. Sin ella la diagnosis de cualquier problema se vuelve arqueología por logs y la mejora del sistema queda librada a la intuición. La política es la inversa: la observabilidad es propiedad obligatoria de cada componente desde su introducción al sistema.

**4.1 Los tres pilares**

La observabilidad moderna se apoya en tres pilares complementarios. Las métricas son agregaciones numéricas a lo largo del tiempo (cuántos requests, qué latencia p95, qué tasa de error); responden bien a preguntas cuantitativas y son baratas de almacenar. Los logs son registros discretos de eventos con detalle (qué pasó en este request específico, qué error apareció, qué payload recibió este endpoint); responden bien a preguntas particulares pero son caros de almacenar y consultar. Las trazas distribuidas son el seguimiento del recorrido de una operación a través de múltiples servicios (cuánto tardó cada paso, qué orden tuvieron); responden a preguntas sobre dónde se va el tiempo y qué componentes participan.

Los tres pilares se usan correlacionados: el trace_id propagado por toda la operación enlaza logs específicos con trazas con métricas, lo que permite ir del síntoma agregado (un endpoint con latencia alta) al detalle específico (este request en particular tardó 4 segundos en este componente) sin reverse engineering manual.

**4.2 Stack adoptado**

|  |  |  |
|:---|:---|:---|
| **Capacidad** | **Herramienta** | **Justificación** |
| Métricas | Prometheus + Grafana | Estándar de facto, ecosistema rico, aprendizaje transferible. Self-hosted en Ola 1; managed en Ola 2 si el costo se justifica. |
| Logs | Loki | Integra naturalmente con Grafana, costo razonable, indexa por labels en lugar de full-text (más barato a escala). |
| Trazas distribuidas | Tempo + OpenTelemetry | Tempo se integra con Grafana; OpenTelemetry es el SDK estándar y vendor-agnostic. |
| Errors / excepciones | Sentry (managed) | Captura, deduplicación y triage de excepciones con UX optimizada para developer. SaaS porque el self-hosted agrega complejidad sin valor proporcional. |
| Synthetic monitoring | Servicio externo (UptimeRobot, Pingdom o equivalente) | Externo a la infraestructura para detectar problemas que monitoring interno no ve. |
| Dashboards | Grafana | Centralización en una herramienta visual sobre los datos de Prometheus, Loki y Tempo. |

**Política sobre vendors managed:** Los componentes managed (Sentry, synthetic monitoring) se eligen cuando el costo de operar la alternativa self-hosted excede el beneficio. La regla operativa: si el componente requiere expertise especializado o dedicación constante para mantenerse al día, se prefiere managed. La autonomía operativa se prioriza solo cuando es valor diferencial.

**4.3 Métricas obligatorias por componente**

Cada componente que entra a producción expone, como mínimo, las cuatro métricas RED (Rate, Errors, Duration) más una de saturación, llamadas también las cuatro métricas USE (Utilization, Saturation, Errors).

|  |  |
|:---|:---|
| **Métrica** | **Qué mide** |
| Rate (R) | Cantidad de requests / operaciones por unidad de tiempo, segmentado por endpoint o tipo de operación. |
| Errors (E) | Cantidad de errores por unidad de tiempo, segmentado por tipo de error y severidad. |
| Duration (D) | Distribución de latencias (histograma), permite calcular percentiles p50, p95, p99. |
| Utilization (U) | Uso de recursos del componente: CPU, memoria, conexiones del pool, tamaño de cola. |
| Saturation (S) | Punto en que el componente empieza a degradar: queue lag, espera por recursos, throttling. |

**4.4 Métricas específicas para multi-tenancy**

La naturaleza multi-tenant de deRuedas exige métricas adicionales para detectar problemas que afectan a un tenant específico antes de que escalen a impacto generalizado. Las métricas se etiquetan con tenant_id donde la cardinalidad lo permite, o se agregan en buckets cuando la cardinalidad sería excesiva.

- Latencia p95 por tenant en endpoints críticos (con cardinalidad limitada a tenants activos).

- Tasa de errores por tenant: detecta tenant con configuración rota o uso fuera de fair use.

- Volumen de uso por tenant (operaciones, mensajes, vehículos): detecta tenant que está creciendo y requiere atención de capacity.

- Cantidad de mensajes en DLQ por tenant: detecta tenant con problemas específicos en la integración con WhatsApp.

- Métrica especial “rls_violations_total”: contador absoluto que debe ser cero siempre. Cualquier incremento es incidente P0 inmediato.

**4.5 Política de cardinalidad**

Las métricas con muchas etiquetas distintas (alta cardinalidad) explotan en costo de almacenamiento y consulta. La regla operativa es que ninguna métrica tiene más de mil series temporales únicas activas; cuando una métrica supera ese umbral se reduce: se quita una etiqueta, se agrupa en buckets, o se reemplaza por logs estructurados. La cardinalidad se monitorea con dashboard dedicado y dispara alerta P3 cuando una métrica nueva supera el umbral.

**Antipatrón a evitar:** Etiquetar métricas con identificadores únicos (request_id, user_id en sistemas con muchos usuarios, IPs específicas) explota la cardinalidad. Si esa información es necesaria para diagnóstico, va en logs (donde el costo crece linealmente) o en trazas (con sampling), no en métricas.

**4.6 Logs estructurados**

Todos los logs del producto son JSON estructurados con campos canónicos. La estructura habilita búsqueda eficiente por etiquetas y correlación entre componentes. La política prohíbe logs free-form que mezclan información en strings concatenados.

{

"timestamp": "2026-05-06T22:35:33.123Z",

"level": "info",

"service": "backend",

"trace_id": "01a2b3c4d5e6f7g8h9",

"request_id": "req-abcd1234",

"tenant_id": "tenant-042",

"user_id": "user-1789",

"action": "lead.create",

"route": "POST /api/v1/leads",

"status": 201,

"duration_ms": 142,

"message": "Lead created successfully"

}

**4.7 Sanitización en observabilidad**

Los logs y las trazas pueden capturar incidentalmente información sensible si el equipo no es disciplinado. La política, alineada con el control C3.4 del Plan de Seguridad, es que el SDK de logging tiene filtros que enmascaran automáticamente campos marcados como sensitive: passwords, tokens, números de DNI, teléfonos completos, emails personales. Los tests automáticos del pipeline buscan estos patrones en outputs de logs y fallan el build si los detectan. La sanitización es parte de la salud operativa: un leak por logs es incidente que el programa SRE debe prevenir activamente.

**4.8 Dashboards canónicos**

Cada componente Tier 1 tiene un dashboard canónico mantenido como código (Grafana JSON versionado). La idea es que cualquier persona del equipo, ante un incidente, sabe a qué dashboard ir según el componente afectado. Los dashboards canónicos no son personales: son del equipo. Las customizaciones individuales viven en dashboards privados, no en los compartidos.

**4.8.1 Dashboard canónico de la API principal**

- Panel superior: estado actual del SLO de disponibilidad y de latencia (cumplimiento del período en curso, presupuesto remanente).

- Tasa de requests por segundo, segmentada por endpoint top-10.

- Tasa de errores por segundo, segmentada por código de status.

- Latencia p50, p95, p99 por endpoint top-10.

- Saturación: pool de conexiones a BD, uso de memoria del proceso, CPU.

- Distribución por tenant_id de los top-10 tenants en volumen.

- Conexión a logs de la ventana visible (botón que abre Loki con la query correspondiente).

**4.8.2 Dashboard canónico de PostgreSQL**

- Estado del primary y de las réplicas (up/down, lag).

- Pool de conexiones: utilización, conexiones idle, conexiones esperando.

- Top queries por duración acumulada (pg_stat_statements).

- Top queries por count (las más frecuentes).

- Crecimiento de tablas principales y de índices.

- Backup status: último backup exitoso, tamaño, validación.

- Replication lag por réplica.

**4.8.3 Dashboard canónico de procesamiento async**

- Workers activos por deployment vs esperados.

- Lag por consumer group y stream.

- Tasa de procesamiento por event_type (ack/sec).

- Tasa de errores y reintentos por event_type.

- Tamaño de DLQ y tendencia.

- Latencia desde published_at a ack_at.

**4.9 Trazas distribuidas**

OpenTelemetry instrumenta backend y workers con sampling adaptativo: tasa baja (0.1%) en operaciones normales para limitar costo, tasa alta (10%) en operaciones que tardaron más de un threshold, tasa máxima (100%) en operaciones que fallaron. Las trazas se almacenan en Tempo con retención de 30 días para investigación. La instrumentación cubre: cada request HTTP de la API, cada llamada saliente a servicios externos, cada query de BD significativa, cada publicación y consumo de evento. La consecuencia operativa es que diagnosticar “por qué este request específico tardó tanto” se hace mirando la traza, no leyendo logs y adivinando.

**4.10 Costos de observabilidad**

La observabilidad tiene costo real: storage de métricas, retención de logs, ingesta de trazas, licencias de SaaS managed. La política es trackear el costo como item explícito del presupuesto operativo y mantenerlo razonable respecto al costo total de infraestructura. La regla orientativa es que observability no debería superar el 15% del costo total de infraestructura del producto. Cuando se acerca a ese límite se actúa: reducir retención de logs verbosos, sampling más agresivo de trazas, eliminación de métricas no usadas.

**5. Alertas**

Esta sección desarrolla la política de alertas: qué dispara una alerta, cómo se clasifica, cómo se enruta, cómo se reduce el ruido. Las alertas son la interfaz primaria entre el sistema y el equipo durante la operación; mal diseñadas erosionan la atención del equipo y vuelven invisibles los problemas reales. La política es estricta y se apoya en el principio O6: cada alerta debe ser accionable.

**5.1 Filosofía de alerting**

El programa adopta cuatro reglas centrales sobre alertas. Primera, cada alerta tiene runbook documentado que la persona que la recibe puede ejecutar; sin runbook, la alerta se elimina o se baja a ticket en lugar de paginación. Segunda, la severidad determina la urgencia y el canal: una alerta P0 despierta a alguien a la madrugada; una P3 espera al horario laboral. Tercera, las alertas se basan en síntomas observables por el usuario, no en causas internas: “la API está caída” antes que “una conexión a BD se cerró”, porque el segundo puede ser benigno o sintomático según el contexto. Cuarta, el equipo audita las alertas mensualmente y elimina o ajusta las que generan ruido.

**5.2 Niveles de severidad**

|  |  |  |  |
|:---|:---|:---|:---|
| **Sev.** | **Etiqueta** | **Criterio** | **Canal y urgencia** |
| P0 | Pagar ahora | Servicio caído para múltiples tenants. SLO crítico violado en tiempo real. Pérdida de datos en curso. | Page con teléfono / push, 24/7. Respuesta esperada \<15min. |
| P1 | Pagar dentro de 1h | Degradación significativa para varios tenants. Capacidad de la infraestructura cerca del límite. Backup falló. | Page diurno, ticket prioritario nocturno. Respuesta esperada \<1h diurna. |
| P2 | Atender hoy | Incidente que afecta a un tenant o subsistema secundario. Métrica fuera de SLO pero no crítica. | Slack del equipo, ticket. Atención dentro del día hábil. |
| P3 | Backlog priorizado | Tendencia preocupante, capacity para revisar, configuración subóptima. | Email / ticket. Sin SLA, entra al backlog. |

**5.3 Alertas basadas en burn rate del SLO**

La técnica más sofisticada y a la vez más útil para alertas de disponibilidad y latencia se llama burn rate alerting. La idea es que el presupuesto de error se consume a una velocidad medible; alertar cuando esa velocidad excede un threshold permite detectar problemas antes de que el SLO se rompa. La técnica se prefiere sobre alertas de threshold simple porque captura tanto picos cortos como degradaciones lentas con un único mecanismo.

\# Ejemplo de alerta burn rate para SLO de 99.7%

\# Burn rate fast: gasta el presupuesto de 30 días en 1 hora

\# Si pasa, en 1h habremos consumido todo el presupuesto mensual

alert: APIBurnRateFast

expr: \|

(sum(rate(http_requests_total{status=~"5.."}\[1h\]))

/ sum(rate(http_requests_total\[1h\])))

\> 14.4 \* 0.003 \# burn rate \* (1 - SLO)

for: 5m

severity: P0

\# Burn rate slow: gasta el presupuesto en 6h

alert: APIBurnRateSlow

expr: \|

(sum(rate(http_requests_total{status=~"5.."}\[6h\]))

/ sum(rate(http_requests_total\[6h\])))

\> 6 \* 0.003

for: 15m

severity: P1

**5.4 Catálogo de alertas principales**

La siguiente tabla enumera las alertas principales del sistema. Cada una tiene su runbook documentado en el repositorio operacional con estructura canónica que se desarrolla en el capítulo 7.

|  |  |  |  |
|:---|:---|:---|:---|
| **Alerta** | **Sev.** | **Disparador** | **Runbook** |
| APIDown | P0 | Health check externo falla 3 veces consecutivas | RB-001 |
| APIBurnRateFast (5xx) | P0 | Burn rate \>14.4 sobre presupuesto de error | RB-002 |
| APILatencyHigh | P1 | p95 sostenido \>500ms durante 15min | RB-003 |
| RLSViolationDetected | P0 | Métrica rls_violations_total \> 0 | RB-004 (escalada inmediata) |
| PostgreSQLPrimaryDown | P0 | Primary no responde por 1min | RB-005 |
| PostgreSQLReplicationLag | P1 | Lag \>30s sostenido por 5min | RB-006 |
| PostgreSQLBackupFailed | P1 | Backup diario no se completó | RB-007 |
| RedisDown | P0 | Redis no responde | RB-008 |
| RedisHighMemory | P1 | Memoria \>85% usada | RB-009 |
| WorkerQueueLagHigh | P1 | Lag de consumer group \>2min sostenido | RB-010 |
| DLQGrowing | P1 | DLQ crece más de 100 eventos/hora | RB-011 |
| WhatsAppCircuitBreakerOpen | P2 | CB de WhatsApp en estado open \>10min | RB-012 |
| WhatsAppErrorRateHigh | P2 | Tasa de error con WhatsApp \>5% en 15min | RB-013 |
| PortalSyncFailing | P2 | Sincronización con portal falla repetidamente | RB-014 |
| TLSCertificateExpiringSoon | P3 | Cert vence en menos de 30 días | RB-015 |
| DiskUsageHigh | P2 | Disco \>85% en cualquier nodo persistente | RB-016 |
| AnomalousAuthFailures | P1 | Spike de 10x en auth failures | RB-017 |
| SyntheticCheckFailed | P0 | Synthetic externo reporta caída | RB-001 (relacionada) |

**5.5 Reducción de ruido**

La fatiga de alertas es el peor enemigo del programa. Las alertas que llegan demasiado y no son accionables se vuelven ruido que oculta las verdaderas. La política operativa contra el ruido tiene varias prácticas concretas.

**5.5.1 Inhibición y agrupación**

Cuando una alerta padre dispara, las alertas hijas que serían su consecuencia se inhiben automáticamente. Si la API está down (APIDown), las alertas de latencia y de errores se inhiben porque ya están explicadas. Las alertas relacionadas que ocurren juntas se agrupan en una sola notificación con todas sus señales: el on-call ve un panorama, no un bombardeo de mensajes inconexos.

**5.5.2 Auditoría mensual de alertas**

El primer lunes de cada mes el equipo revisa las alertas que se dispararon en el mes anterior. Para cada alerta recurrente se pregunta: ¿la respuesta fue acción real o “ya sé”? Si la respuesta fue siempre “ya sé”, la alerta no es accionable y se elimina o se ajusta. ¿La acción fue siempre la misma? Si sí, se automatiza la acción. ¿La alerta disparó pero el problema se autorresolvió antes de actuar? Si sí, el threshold está mal calibrado y se ajusta.

**5.5.3 Métricas de salud del programa de alertas**

- Cantidad de alertas P0 y P1 disparadas por mes (objetivo: tendencia descendente).

- Porcentaje de alertas P0/P1 que requirieron acción real (objetivo: \>80%; si baja, hay ruido).

- Tiempo medio de resolución por severidad.

- Cantidad de alertas eliminadas o ajustadas por mes (señal de salud del programa).

- Cantidad de alertas activas vs el límite del catálogo (objetivo: catálogo manejable, no creciendo sin control).

**5.6 Notificación silenciosa (silences)**

Durante mantenimientos planeados o cuando se está investigando un incidente activo se silencian temporalmente las alertas afectadas para no agregar ruido. Los silences siempre son temporales con expiración explícita —máximo 4 horas en ventana normal, 24 horas en mantenimiento programado— y dejan registro auditable de quién silenció qué y por qué. Los silences sin expiración están prohibidos.

**6. On-call**

Esta sección define la práctica del on-call: la rotación que garantiza cobertura para responder a alertas, los procedimientos de handoff entre turnos, la compensación de quienes están de guardia y los criterios de escalación cuando el on-call solo no puede resolver. El on-call es punto sensible del programa porque toca calidad de vida del equipo: mal diseñado produce burnout y rotación de personal; bien diseñado se vuelve sostenible y formativo.

**6.1 Estructura de la rotación**

La rotación adoptada en MVP cubre las 24 horas con un on-call primario que recibe las alertas y un on-call secundario que actúa como backup si el primario no responde dentro del SLA de respuesta. La rotación es semanal de lunes a lunes, con cambio a las 10:00 horas para evitar handoffs en horarios complicados. Cada miembro del equipo de desarrollo participa de la rotación, incluyendo al tech lead. El agente de IA no participa de la rotación on-call: las alertas requieren juicio humano para decidir respuestas, especialmente cuando los runbooks no cubren el caso exacto.

|  |  |
|:---|:---|
| **Rol** | **Responsabilidad** |
| On-call primario | Recibe alertas P0 y P1 a través del canal correspondiente (page, push). Ejecuta runbook si lo hay. Decide si escalar. Actualiza el ticket del incidente. Comunica al equipo y al canal correspondiente. |
| On-call secundario | Recibe alerta automática si el primario no acknowledga en 10 minutos. Disponible como backup si el primario necesita ayuda o no puede atender por causa mayor. Toma el rol de Incident Commander en incidentes que escalan. |
| Tech Lead (escalación) | Recibe escalado del on-call primario o secundario cuando el incidente excede su autoridad o conocimiento. Toma decisiones de mayor impacto (rollback, degradación, comunicación pública). |

**6.2 Cantidad mínima de personas en rotación**

La rotación viable requiere mínimo cuatro personas: con tres, cada persona está de guardia una semana de cada tres, lo que es agotador en el largo plazo y deja al equipo sin holgura para vacaciones, enfermedad o tiempo personal. Con cuatro, cada persona está de guardia una semana de cada cuatro, lo cual es sostenible. Con cinco o más, la guardia es excepcional y el costo individual es bajo. Cuando el equipo crece por debajo de cuatro personas con capacidad on-call, la organización debe contemplar contratar pronto o aceptar guardia compartida con menor SLA. La política prohíbe sostener rotación viable con menos de tres personas durante períodos prolongados: el costo organizacional es invisible pero real.

**6.3 Compensación del on-call**

La política de compensación reconoce que estar de guardia tiene costo aunque no se dispare ningún incidente: el on-call no puede planificar libremente actividades, no puede beber alcohol, no puede alejarse de internet. La compensación tiene tres componentes.

- Bono fijo por semana de guardia, independiente de si hubo incidentes. Reconoce el costo de disponibilidad.

- Pago por intervención efectiva fuera de horario laboral, calculado por hora real trabajada con multiplicador de horas extras.

- Día libre compensatorio cuando una intervención nocturna o de fin de semana excede dos horas continuas.

**Recomendación organizacional:** La organización publica el esquema de compensación en políticas internas. La transparencia evita que el on-call se viva como obligación silenciosa cuya compensación depende de buena voluntad. Equipos donde el on-call no se compensa adecuadamente experimentan rotación silenciosa: las personas más capaces se van primero porque tienen más opciones.

**6.4 Onboarding al on-call**

Una persona nueva no entra a la rotación inmediatamente. La progresión típica es la siguiente. Durante las primeras dos semanas en el equipo, observación pasiva: lee runbooks, recibe alertas en modo silencioso, asiste a postmortems sin protagonizar. Durante las dos semanas siguientes, on-call shadowing: acompaña al on-call activo en sus respuestas, ejecuta runbooks bajo supervisión. Después de cuatro semanas, on-call activo con backup reforzado: el on-call secundario es el tech lead y se monitorea más estrechamente. Después de ocho semanas, on-call estándar.

**6.5 Equipamiento y disponibilidad del on-call**

Una persona en on-call necesita equipamiento mínimo: laptop con acceso al stack operativo, conexión a internet razonable, teléfono cargado para recibir páginas. La política operativa exige que durante la guardia la persona esté en condiciones de responder en menos de 15 minutos a una alerta P0; esto implica restricciones razonables (no estar en avión, no estar conduciendo, no estar en zona sin cobertura). Cuando una restricción es inevitable (un viaje planeado, un evento personal), se intercambia la guardia con otro miembro del equipo con anticipación suficiente.

**6.6 Handoff entre turnos**

Los lunes a las 10:00, el on-call saliente y el entrante hacen handoff de 15 minutos donde se transfieren tres elementos: el estado actual de cualquier incidente abierto, los issues conocidos que requieren atención durante la semana entrante, los aprendizajes del turno anterior. El handoff queda documentado en el canal del equipo como mensaje estandarizado.

🔄 Handoff on-call — 6 mayo 2026

Saliente: María

Entrante: Juan

Backup entrante: Carlos

Incidentes abiertos:

· INC-2026-0508 — Lag intermitente de procesamiento de webhooks

de WhatsApp. Mitigado escalando workers. Investigación abierta.

· ningún otro abierto.

Issues conocidos a vigilar:

· Tenant-042 reportó lentitud en su dashboard de leads.

Investigación pendiente, no es bloqueante.

· El backup de PostgreSQL del jueves tardó 40% más de lo habitual.

No falló pero merece atención si se repite.

Aprendizajes de la semana:

· El runbook RB-010 (worker queue lag) tenía un paso desactualizado.

Lo corregí; revisar PR \#1247.

🤝 Buena guardia, Juan.

**6.7 Escalación**

El on-call primario tiene autoridad para responder a la mayoría de los incidentes con los runbooks documentados. Cuando aparece una situación que excede su autoridad, conocimiento o capacidad de resolución sola, se escala. La escalación no es señal de debilidad: es uso correcto del sistema. Las situaciones que disparan escalación son las siguientes.

- Incidente P0 cuya resolución requiere decisiones de impacto comercial (comunicación pública, rollback de producto).

- Incidente que requiere conocimiento técnico que el on-call no tiene (migración de schema en BD, cambio de configuración de red de bajo nivel).

- Incidente que excede en duración el tiempo en que el on-call puede mantener atención (más de 4 horas continuas).

- Incidente que se sospecha vinculado a seguridad (potencial intrusión, compromiso de credenciales). Se escala al responsable de seguridad además del tech lead.

- Incidente con efectos sobre datos del tenant (corrupción posible, exposición potencial). Escalación al responsable de privacidad y al tech lead.

**6.8 War room durante incidentes P0**

Cuando un incidente P0 se prolonga más allá de 30 minutos, se abre war room virtual: canal Slack dedicado \#inc-YYYY-MM-DD-tag, llamada continua si las personas están en distintos lugares, documento compartido con cronología en vivo. Los roles del incidente —Incident Commander, Tech Lead, Comms, Scribe, SMEs— se asignan explícitamente y se rotan cada cuatro horas si el incidente persiste. El detalle del proceso está en el capítulo 10 y se alinea con la sección 7 del Plan de Seguridad.

**6.9 Cultura: cuidado del on-call**

La organización vela por que el on-call no se vuelva tóxico. Esto se materializa en prácticas concretas. Las alertas se auditan mensualmente para reducir ruido (lo que mejora la experiencia del on-call). El equipo no espera que el on-call mantenga ritmo de trabajo normal durante una guardia con incidentes; el día siguiente al incidente nocturno se respeta como recuperación. Los postmortems se centran en el sistema, no en la persona, lo que vuelve seguro reportar honestamente. La rotación se intercambia sin fricción cuando las condiciones personales lo requieren.

**7. Runbooks principales**

Esta sección presenta la plantilla canónica de runbook y desarrolla los runbooks principales del producto. Un runbook es la secuencia de pasos que el on-call ejecuta cuando se dispara una alerta específica. La calidad de los runbooks es la diferencia entre un equipo que resuelve incidentes con disciplina y un equipo que improvisa bajo presión. Los runbooks viven en el repositorio operacional, versionados como código, con revisión periódica.

**7.1 Plantilla canónica de runbook**

RB-XXX — \[Nombre descriptivo de la alerta\]

Severidad: \[P0/P1/P2/P3\]

Última revisión: YYYY-MM-DD

Dueño: \[persona o rol responsable de mantener el runbook\]

\## Síntomas observables

Descripción de qué se ve cuando esta alerta dispara:

qué métricas están fuera, qué reporta el dashboard,

qué experiencia tiene el usuario.

\## Diagnóstico inicial (primeros 5 minutos)

Pasos para confirmar la alerta y localizar el componente:

1\. \[comando o consulta concreta\]

2\. \[siguiente paso\]

3\. ...

\## Mitigación (acción inmediata para detener el daño)

Si el problema es A:

1\. \[acción\]

Si el problema es B:

1\. \[acción\]

\## Comunicación

· Si afecta a múltiples tenants: actualizar status page

con plantilla \[PT-001\]

· Si afecta a un tenant específico: email al manager

con plantilla \[PT-002\]

· Si dura \>30min: war room en \#inc-YYYY-MM-DD-XXX

\## Resolución (acción para corregir la causa raíz)

Una vez mitigado el síntoma, los pasos para resolver:

1\. \[acción\]

2\. ...

\## Validación post-resolución

· Verificar que \[métrica X\] vuelve a \[rango Y\]

· Verificar que \[endpoint Z\] responde correctamente

· Monitorear durante \[tiempo\] antes de cerrar el incidente

\## Escalación

Si los pasos anteriores no resuelven en \[tiempo\],

escalar a \[persona/rol\] siguiendo procedimiento del cap. 6.

\## Postmortem

· Si severidad es P0 o P1: postmortem obligatorio dentro de 5 días

· Action items derivados al backlog del programa SRE

\## Historial de modificaciones

· YYYY-MM-DD: descripción del cambio - autor

**7.2 RB-001 — APIDown**

**Severidad:** P0

**Síntoma:** Health check externo falla; los tenants no pueden acceder al producto

**Diagnóstico inicial**

El primer paso es confirmar el alcance. El monitor sintético externo reporta caída pero el monitor interno puede reportar OK si el problema está entre el frontend y el backend. Los pasos canónicos son los siguientes.

- Confirmar desde otra red (red móvil personal) que el endpoint /health/live no responde.

- Verificar dashboard canónico de la API: tasa de requests, tasa de 5xx, latencia.

- Revisar Sentry: ¿hay spike de excepciones recientes? ¿Patrón identificable?

- Revisar logs de los containers del backend: ¿están vivos? ¿Restart loop? ¿OOMKilled?

- Verificar que el load balancer está enrutando: dashboard del LB.

**Mitigación**

Las mitigaciones se eligen según el diagnóstico. Si los containers del backend están en restart loop, se intenta rollback al último deploy estable conocido (procedimiento del capítulo 9). Si el LB no enruta a containers vivos, se verifica health check del LB y se ajusta si es incorrecto. Si la BD está caída (alerta concurrente esperada), se sigue runbook de PostgreSQL antes de volver a este. Si todos los componentes están vivos pero responden lento, se evalúa rate limiting agresivo temporal para reducir carga mientras se diagnostica.

**Comunicación**

Status page se actualiza dentro de 15 minutos del confirmado. Email a tenants afectados con plantilla de primer aviso del Plan de Seguridad sección 7.7.1. Actualización al canal del equipo cada 15 minutos durante el incidente.

**Resolución**

Una vez identificada la causa raíz, los pasos varían. La resolución persistente requiere postmortem y action items: agregar protección contra el modo de falla observado, mejorar la detección, ajustar capacity si fue overload.

**7.3 RB-004 — RLSViolationDetected**

**Severidad:** P0

**Síntoma:** La métrica rls_violations_total se incrementó por encima de cero. Esto indica que se detectó un caso donde una query devolvió o intentó devolver datos de un tenant distinto al esperado.

**Tratamiento especial:** Esta alerta es la más crítica del programa. La pérdida de aislamiento entre tenants es violación del compromiso central del producto. Se trata como incidente de seguridad inmediatamente, escalando al responsable de seguridad además del tech lead.

**Diagnóstico inicial**

- Confirmar la lectura de la métrica desde Prometheus directamente.

- Identificar qué endpoint disparó el incremento (label de la métrica).

- Identificar qué tenants están involucrados (acceso al log estructurado del request específico).

- Determinar si la violación fue “intento bloqueado” (RLS hizo su trabajo y la query devolvió 0 filas) o “datos efectivamente expuestos” (la query devolvió filas de otro tenant). El segundo escenario es brecha real.

**Mitigación**

- Si la violación es “datos expuestos”: detener inmediatamente el endpoint afectado mediante feature flag o rate limiting agresivo.

- Identificar todos los requests del usuario o tenant afectado en las últimas 48 horas.

- Determinar el alcance: cuántos tenants potencialmente afectados, qué datos quedaron expuestos.

- Notificar al responsable de privacidad para evaluación de notificación a la AAIP.

**Comunicación**

Esta es de las pocas situaciones donde la comunicación pública puede preceder a la resolución completa. La comunicación inicial es a los tenants afectados (no genérica) con detalle del alcance preliminar. Se sigue el procedimiento del Plan de Seguridad sección 7.5 con plazos y plantillas. La notificación a la AAIP en 72 horas es responsabilidad del responsable de privacidad.

**7.4 RB-005 — PostgreSQLPrimaryDown**

**Severidad:** P0

**Síntoma:** El primary de PostgreSQL no responde a conexiones. La aplicación no puede leer ni escribir.

**Diagnóstico inicial**

- Confirmar conexión imposible desde un cliente psql (acceso JIT auditado).

- Revisar dashboard de PostgreSQL: ¿proceso vivo? ¿Réplica está OK?

- Revisar logs del primary: shutdown limpio, panic, OOMKilled, disco lleno.

- Verificar estado del orquestador de failover (Patroni / equivalente).

**Mitigación**

- Si el orquestador está activo y la réplica está OK, esperar 30 segundos: el failover automático debería ocurrir y promover una réplica.

- Si el failover automático no ocurre o falla, ejecutar el procedimiento de promoción manual documentado en el repositorio operacional.

- Una vez promovida la réplica, verificar que la aplicación se conecta al nuevo primary (las connection strings deberían apuntar a un alias DNS que el orquestador actualiza).

- Si ni el failover automático ni el manual funcionan, escalar al tech lead inmediatamente y considerar restore desde backup como última opción.

**Resolución**

Una vez restablecido el servicio, investigar la causa de la caída del primary original. Las causas típicas son: out of memory por query mal optimizada, disco lleno por backup que no rotó, falla de hardware del cloud provider, bug en una migration. La resolución persistente puede requerir scale-up del nodo, ajuste de límites de recursos, o cambio en políticas de backup.

**7.5 RB-010 — WorkerQueueLagHigh**

**Severidad:** P1

**Síntoma:** El lag de un consumer group de Redis Streams supera 2 minutos sostenidos. Los eventos se acumulan más rápido de lo que se procesan.

**Diagnóstico inicial**

- Identificar qué consumer group está retrasado y qué tipo de eventos procesa.

- Verificar cantidad de workers activos vs esperados.

- Revisar dashboard de errores de workers: ¿hay tasa elevada de excepciones?

- Revisar latencia de servicios externos que el worker llama (WhatsApp, portal).

**Mitigación**

- Si los workers están vivos pero abrumados: escalar horizontalmente (incrementar replicas del deployment).

- Si los workers están fallando con tasa alta: identificar causa específica (servicio externo down, payload malformado, bug). Mientras se diagnostica, considerar pausar el consumer group para evitar que los eventos vayan a DLQ por exceso de reintentos.

- Si los eventos van a DLQ pero el problema es transitorio externo: esperar que el servicio externo se recupere y reintentar desde DLQ con runbook RB-011.

**7.6 RB-012 — WhatsAppCircuitBreakerOpen**

**Severidad:** P2

**Síntoma:** El circuit breaker de la integración con WhatsApp Cloud API está en estado open por más de 10 minutos. Esto significa que el sistema está rechazando inmediatamente los intentos de envío sin contactar a Meta.

**Diagnóstico inicial**

- Verificar status page de Meta para WhatsApp Business Platform.

- Revisar logs recientes del circuit breaker: qué fallas dispararon la apertura.

- Probar manualmente un request a WhatsApp Cloud API desde un tenant de prueba.

**Mitigación**

- Si Meta está caído (status page lo confirma): no hay acción técnica posible. Comunicar a tenants afectados con plantilla de incidente externo. Esperar restablecimiento. El circuit breaker se cerrará automáticamente cuando los probes sean exitosos.

- Si el problema es nuestro (credenciales rotadas mal, throttling por uso excesivo): rotar credenciales o ajustar rate limiting interno.

- Si el problema es de un tenant específico (su token expiró): notificar al tenant para que renueve su autorización.

**7.7 Mantenimiento de runbooks**

Los runbooks no son artefactos estables: evolucionan con el sistema y con los aprendizajes de cada incidente. La política operativa exige tres prácticas. Primera, todo postmortem que genera action items relevantes para detección o mitigación actualiza al menos un runbook (existente o nuevo). Segunda, cada vez que un on-call ejecuta un runbook y descubre que un paso es incorrecto u obsoleto, abre PR para corregirlo en el momento; no se pospone. Tercera, una revisión trimestral del catálogo completo verifica que no hay runbooks fósiles (alertas que ya no existen con sus runbooks colgando) y que los runbooks vigentes tienen información actualizada.

**8. Capacity planning**

Esta sección define cómo se anticipa, modela y gestiona el crecimiento de la infraestructura en función de la carga real. Sin capacity planning, la organización oscila entre dos modos disfuncionales: sobreaprovisionamiento crónico que consume costos sin necesidad, o subaprovisionamiento que dispara incidentes evitables. La política adoptada es modelar carga, observar ratio de uso, anticipar tendencias y actuar con anticipación razonable.

**8.1 Unidades de carga**

La carga del sistema se modela en unidades observables. Para deRuedas, las dos unidades principales son: tenants activos (agencias con uso real en la última semana) y volumen de operaciones por tenant (mensajes, leads, vehículos creados, requests). El producto se aprovisiona en función de las dos unidades combinadas: un tenant activo grande consume varios órdenes de magnitud más que un tenant chico.

|  |  |  |  |
|:---|:---|:---|:---|
| **Métrica** | **Tenant chico** | **Tenant medio** | **Tenant grande** |
| Vendedores activos | 1-2 | 3-5 | 6-15 |
| Vehículos en stock | 20-50 | 50-150 | 150-500 |
| Leads abiertos simultáneos | 10-30 | 30-100 | 100-300 |
| Mensajes WhatsApp / día | 20-50 | 100-300 | 500-1500 |
| Requests API / día | 1k-5k | 5k-20k | 20k-100k |

**8.2 Modelado de capacidad por componente**

Cada componente Tier 1 tiene un modelo de capacidad documentado que relaciona la unidad de carga con el recurso aprovisionado. El modelo se construye con datos reales de operación, no con estimaciones teóricas. Las relaciones típicas son las siguientes.

- API backend: capacidad medida en requests por segundo soportados por replica. Relación con tenants activos: aproximadamente lineal pero con factor de no-concurrencia (no todos los tenants usan al mismo tiempo).

- PostgreSQL: capacidad medida en queries por segundo y en almacenamiento. Relación con tenants: lineal en almacenamiento, sublineal en QPS por amortización del cache.

- Redis: capacidad medida en memoria. Relación con tenants: lineal, dominada por sesiones activas y por buffers de eventos no procesados.

- Workers async: capacidad medida en eventos procesados por segundo. Relación con volumen de operaciones: directamente proporcional.

- Storage de objetos: capacidad medida en GB. Relación con vehículos y conversaciones: lineal con crecimiento dominado por fotos de vehículos.

**8.3 Headroom objetivo**

El sistema se mantiene con holgura suficiente para absorber picos sin degradar y para tolerar fallas parciales sin colapsar. La política de headroom es la siguiente.

|  |  |
|:---|:---|
| **Componente** | **Política de headroom** |
| API backend | Replicas suficientes para que la utilización p95 de cualquier replica no supere 60% durante operación normal. Esto da capacidad de absorber 1 replica caída sin degradar. |
| PostgreSQL primary | Conexiones del pool al 60% máximo en operación normal. CPU al 50% promedio. Disco con 30% libre mínimo. |
| Redis | Memoria al 70% máximo en operación normal. Resto reservado para picos. |
| Workers async | Capacidad de procesar 3x el throughput actual sin lag. Absorbe spikes y permite catch-up tras incidentes. |
| Storage | 30% libre mínimo. Cuando llega a 80% se planifica scaling con 30 días de anticipación. |

**8.4 Scaling automático y manual**

Algunos componentes escalan automáticamente con triggers basados en utilización; otros escalan manualmente con planificación. La política asigna cada modo según el tipo de componente.

|  |  |  |
|:---|:---|:---|
| **Componente** | **Modo** | **Detalles** |
| Replicas de API backend | Auto | HPA con métrica de CPU y custom metric de RPS. Min 2, max 10. |
| Workers async | Auto | HPA con métrica de queue lag. Min 1 por consumer group, max según tipo. |
| PostgreSQL nodos | Manual | Vertical scaling planificado. Lectura del crecimiento mensual y ventana de 30 días para preparar. |
| Redis nodos | Manual | Cluster scaling planificado. Aumento de memoria por nodo o agregado de shard. |
| Storage | Auto | Buckets sin límite duro; el costo crece linealmente con el uso. |

**8.5 Forecasts trimestrales**

Cada trimestre el responsable de operaciones produce un forecast de capacidad para el siguiente trimestre con la siguiente estructura. Tendencia observada de tenants activos y de volumen de operaciones por tenant. Proyección para los siguientes 90 días basada en el pipeline comercial (tenants firmados que aún no entraron) y el churn esperado. Capacidad actual versus proyección: identificación de componentes que se acercarán a su límite. Acciones recomendadas: scaling planeado, optimizaciones, decisión de aceptar holgura menor o invertir en aprovisionamiento.

**8.6 Decisiones difíciles de capacity**

Hay momentos donde la capacity se vuelve política y requiere decisión explícita. Cuando un tenant nuevo grande está por entrar y consumiría una porción significativa de la capacidad actual: se decide entre scaling proactivo, segregación del tenant a infraestructura dedicada, o pricing diferencial. Cuando el costo de mantener el headroom objetivo excede el beneficio: se documenta la decisión de aceptar headroom menor con plan de monitoreo reforzado. Cuando un componente legacy genera carga desproporcionada respecto al valor que aporta: se decide entre invertir en optimizarlo o eliminarlo. Estas decisiones se documentan como ADRs operacionales en el repositorio del programa SRE.

**9. Gestión de cambios y deploys**

Esta sección define cómo se introducen cambios en producción de manera segura. Los cambios son la principal causa de incidentes en sistemas de software: la mayoría de los outages ocurren tras un deploy o un cambio de configuración. La gestión disciplinada de cambios es lo que permite mantener la velocidad de entrega sin sacrificar estabilidad.

**9.1 Estrategias de deploy**

|  |  |
|:---|:---|
| **Estrategia** | **Cuándo se usa** |
| Rolling deploy | Default para cambios menores: actualización incremental de replicas, una a la vez, con health check entre cada una. |
| Blue-green | Cambios de mayor riesgo: dos ambientes paralelos, switch atómico de tráfico, rollback inmediato si algo falla. |
| Canary | Cambios cuyo impacto es difícil de evaluar pre-deploy: 1% del tráfico al nuevo código, escalado progresivo (5%, 25%, 50%, 100%) con monitoreo de SLIs en cada paso. |
| Feature flag | Cambios que requieren validación operativa con tráfico real antes de exponerse: el código está en producción pero detrás de flag, se activa para usuarios internos primero, luego para tenants seleccionados, luego para todos. |

**9.2 Cambios de schema de base**

Los cambios de schema son los más sensibles porque pueden producir corrupción o downtime si están mal hechos. La política operativa adoptada para migrations es la siguiente. Las migrations son siempre forward-compatible: el código viejo sigue funcionando contra el schema nuevo. Esto permite que el deploy sea incremental sin downtime. Las migrations destructivas (drop column, drop table) se hacen en dos pasos separados por al menos un release: primero se deja de usar la columna desde código y se mergea esa versión; después, en un release posterior, se hace el drop. Las migrations bloqueantes que requieren tomar locks largos se evitan; cuando son inevitables, se programa ventana de mantenimiento. Toda migration tiene script de rollback explícito y ejercitado.

**9.3 Cambios de configuración**

Los cambios de configuración son menos visibles que los cambios de código pero igualmente capaces de causar incidentes. La política exige que toda configuración productiva esté como código (Infrastructure as Code, GitOps cuando aplique), versionada y revisada en pull request con la misma disciplina que el código. La configuración aplicada manualmente “por un momento” queda explícitamente prohibida, salvo en respuesta a incidente activo donde la inmediatez justifica saltarse el proceso pero el cambio se reconcilia al repositorio dentro de las 48 horas siguientes.

**9.4 Procedimiento de rollback**

Todo cambio significativo a producción se hace con plan de rollback explícito documentado en el ticket de release. El plan responde a tres preguntas. ¿Qué señales indican que el cambio fue malo y hay que revertir? Métricas específicas que se monitorean post-deploy. ¿Cómo se ejecuta el rollback técnicamente? Pasos concretos: deploy de imagen anterior, reversión de migration, restore de configuración. ¿Cuánto tiempo toma el rollback? Estimación realista; si excede el SLO de impacto aceptable, el plan no es viable y el cambio requiere otra estrategia (canary, feature flag).

**La regla de oro del rollback:** Un cambio que no se puede revertir limpiamente no se hace. La irreversibilidad es señal de que el cambio requiere ser dividido en pasos reversibles independientes. La excepción legítima son ciertos cambios de schema destructivos donde la reversibilidad estricta es imposible; en esos casos se ejecutan después de varios releases sin necesidad de revertir y bajo extremo cuidado.

**9.5 Ventanas de mantenimiento**

Cuando un cambio requiere downtime planificado o riesgo elevado, se programa ventana de mantenimiento. La política operativa es las siguientes. Las ventanas se programan en horarios de bajo uso para Argentina (típicamente domingos entre 06:00 y 09:00 hora local). Se notifican a tenants con 72 horas de anticipación mínimo. Se documentan en status page con detalle de qué se va a hacer y qué impacto se espera. El downtime durante la ventana no cuenta contra el SLA. Una vez ejecutada, se publica resumen con resultado y duración real.

**9.6 Aprobación de releases**

La promoción a producción no es automática: requiere aprobación humana documentada. La aprobación se basa en la checklist del Plan de Testing capítulo 14.2 más consideraciones operativas adicionales. El responsable de release de la semana es quien aprueba; rota junto con la rotación on-call. Su responsabilidad incluye verificar el contexto operativo: ¿hay incidente activo? ¿estamos en modo presupuesto agotado? ¿coincide con un período crítico para los tenants? Cuando alguna de estas condiciones se da, el release se posterga aunque técnicamente esté listo.

**9.7 Métricas de cambios**

|  |  |
|:---|:---|
| **Métrica** | **Uso** |
| Frecuencia de deploys a producción | Indicador de velocidad del equipo. Objetivo: al menos uno por semana en operación madura. |
| Tiempo medio de release (lead time) | Desde merge a main hasta producción. Objetivo: \<24h en operación madura. |
| Tasa de rollback | % de releases que requirieron rollback. Objetivo: \<5%. |
| Tiempo medio de rollback cuando se requiere | Desde detección del problema hasta servicio restaurado. Objetivo: \<30min. |
| Cantidad de hotfixes por mes | Releases fuera del proceso normal por urgencia. Objetivo: tendencia descendente. |

**10. Gestión de incidentes operativos**

Esta sección desarrolla la gestión de incidentes operativos —los que afectan disponibilidad, performance o experiencia de usuario sin involucrar adversarios o brechas de seguridad. Comparte estructura con la respuesta a incidentes del Plan de Seguridad (sección 7) pero se diferencia en alcance y procedimiento.

**10.1 Diferencia respecto a incidentes de seguridad**

|  |  |
|:---|:---|
| **Aspecto** | **Incidente operativo vs incidente de seguridad** |
| Causa típica | Operativo: bug de software, cambio mal aplicado, falla de proveedor, capacity insuficiente. Seguridad: actor malicioso, vulnerabilidad explotada, leak de datos. |
| Notificación regulatoria | Operativo: no requiere salvo si afecta datos personales. Seguridad: AAIP en 72h si afecta PII. |
| Coordinación | Operativo: liderado por SRE / on-call con tech lead. Seguridad: liderado por responsable de seguridad con apoyo SRE. |
| Postmortem | Operativo: foco en mejorar el sistema, los runbooks, las alertas. Seguridad: foco en cerrar vector, evaluar impacto en datos, evaluar daño residual. |
| Comunicación | Operativo: status page + email proactivo a tenants afectados. Seguridad: status page si corresponde + comunicación legal a tenants y eventualmente a autoridades. |

**10.2 Severidad operativa**

La taxonomía de severidad para incidentes operativos coincide en estructura con la del Plan de Seguridad pero con criterios específicos.

|  |  |  |
|:---|:---|:---|
| **Sev.** | **Etiqueta** | **Criterio operativo** |
| O0 | Operativo crítico | Servicio totalmente caído \>5min o degradación que afecta a \>50% de tenants. SLO mensual en riesgo de quemar todo el presupuesto. |
| O1 | Operativo mayor | Funcionalidad central degradada para subset significativo. Latencia muy alta sostenida. Componente Tier 1 en estado degradado. |
| O2 | Operativo significativo | Funcionalidad afectada para tenants específicos. Componente Tier 2 caído. Lag elevado en procesamiento async. |
| O3 | Operativo menor | Degradación detectable pero impacto limitado. Componente Tier 3 caído. |

**10.3 Roles durante el incidente**

Los roles durante un incidente operativo significativo son los mismos que se enuncian en el Plan de Seguridad sección 7.3 (Incident Commander, Tech Lead, Communications, Scribe, SMEs) con la adaptación de que el rol de Communications en incidentes operativos puede recaer en customer success en lugar del responsable de privacidad. La asignación se hace explícitamente al iniciar el war room.

**10.4 Comunicación a tenants en incidentes operativos**

La política de comunicación a tenants durante incidentes operativos se adapta a la severidad. Para O0 con impacto multi-tenant: status page actualizada dentro de 15 minutos del incidente confirmado, con actualizaciones cada 30 minutos hasta resolución. Email a manager de cada tenant afectado dentro de 1 hora si el incidente persiste. Para O1: status page si afecta a más de un tenant; email a tenants afectados dentro de 2 horas. Para O2 y O3: comunicación post-resolución, incluida en reporte mensual de servicio.

**10.5 Postmortem operativo**

Todo incidente O0 y O1 genera postmortem dentro de 5 días hábiles con la estructura general definida en el Plan de Seguridad sección 7.8. Para incidentes operativos, el postmortem tiene énfasis particular en aspectos técnicos de detección y respuesta. ¿Las alertas dispararon a tiempo? ¿Los runbooks fueron útiles? ¿Hubo tooling que faltó y hubiera acelerado la resolución? ¿La comunicación fue oportuna? Los action items resultantes alimentan el programa: nuevos runbooks, métricas adicionales, alertas mejoradas, automatización de respuestas que se hicieron a mano.

**10.6 Aprendizaje organizacional**

Los postmortems individuales se consolidan trimestralmente en una revisión de patrones. Tres incidentes con causas distintas pero síntomas comunes pueden indicar problema sistémico que un postmortem por separado no detecta. La revisión trimestral identifica esos patrones y genera proyectos de mejora estructural: cambios de arquitectura, inversión en herramientas, ajustes de procesos. Este meta-aprendizaje es la diferencia entre un equipo que apaga incendios y un equipo que reduce la frecuencia con que ocurren.

**11. Toil y automatización**

Esta sección desarrolla el principio O3 sobre eliminación de toil y la práctica concreta de automatización derivada del principio O4. El toil es enemigo silencioso de los programas SRE: crece sin ser percibido, consume capacidad humana sin producir mejora del sistema, y cuando llega al umbral del 50% del tiempo del equipo ya es tarde para revertirlo sin dolor.

**11.1 Definición operativa de toil**

Toil es trabajo operativo con cinco propiedades simultáneas que lo distinguen del trabajo productivo. Es manual: requiere intervención humana en lugar de ejecutarse solo. Es repetitivo: el mismo tipo de tarea se hace una y otra vez. Es automatizable en principio: la dificultad técnica de eliminarlo no es prohibitiva. Es tactico (reactivo): responde a problemas o necesidades inmediatas, no construye capacidad futura. Carece de valor permanente: una vez ejecutado no deja huella que mejore el sistema.

Trabajo que es manual pero estratégico (diseñar arquitectura, entrevistar tenants, tomar decisiones de capacity) no es toil. Trabajo que es repetitivo pero no automatizable razonablemente (review de PRs, postmortems) tampoco es toil. La definición es restrictiva a propósito: el objetivo es identificar exactamente lo que se debe atacar.

**11.2 Ejemplos típicos de toil en deRuedas**

- Ejecutar manualmente backups que deberían correr automáticamente.

- Reiniciar containers que entran en estado inconsistente periódicamente.

- Generar reportes mensuales de uso copiando datos entre dashboards.

- Procesar a mano emails de tenants que reportan el mismo problema con la misma respuesta.

- Aplicar patches de configuración en cada deploy en lugar de codificarlos.

- Investigar manualmente cada DLQ event en lugar de tener triage automático.

- Ajustar a mano valores que deberían autoescalar.

**11.3 Medición del toil**

La política operativa exige medir el porcentaje del tiempo del equipo dedicado a toil. La medición se hace mensualmente con encuesta breve donde cada miembro estima qué porción de su tiempo del mes se fue en toil identificable. La métrica resultante se reporta al equipo y a dirección. El umbral de alarma es 25%: cuando el equipo en promedio dedica más del cuarto de su tiempo a toil, hay disfunción operativa que se trata como prioridad.

**11.4 Reducción sistemática de toil**

Una vez identificado, el toil se reduce mediante prácticas concretas. La automatización es la principal: cualquier tarea operativa que se ejecuta más de dos veces es candidata a script o tooling. La eliminación es alternativa: a veces la tarea no debería existir en absoluto y la respuesta correcta es eliminarla. La auto-resolución es elegante: arquitecturas donde el problema desaparece (por ejemplo, autoscaling en lugar de scaling manual). La delegación al usuario es a veces apropiada: tareas que el tenant puede hacer por sí mismo si se le da la herramienta.

**11.5 Proyectos de automatización priorizados**

El equipo dedica al menos 20% de su tiempo a proyectos de automatización que reducen toil futuro. Esta inversión continua es lo que evita que el toil crezca sin control. Los proyectos se priorizan con criterio de retorno: cuánto toil eliminan vs cuánto cuesta automatizarlos. Los proyectos típicos en olas iniciales son los siguientes.

|  |  |  |
|:---|:---|:---|
| **Proyecto** | **Toil que elimina** | **Esfuerzo estimado** |
| Auto-rotación de credenciales con secret manager | Rotación manual trimestral de credenciales en múltiples lugares | 1 sprint |
| Alertas auto-cerrantes cuando la métrica vuelve al rango | On-call cerrando manualmente tickets de alertas resueltas | 0.5 sprint |
| Self-service de exports para tenants | Customer success procesando manualmente solicitudes de exports | 2 sprints |
| Auto-triage de DLQ por tipo de error | Investigación manual de cada DLQ event | 1 sprint |
| Status page automática desde métricas | Actualización manual de status page durante incidentes | 1 sprint |

**12. Costos operativos**

Esta sección desarrolla la práctica básica de FinOps aplicada a la operación del producto: cómo se observa, atribuye y optimiza el costo de la infraestructura. Para un SaaS multi-tenant en MVP la disciplina de costos no es luxury sino requisito de viabilidad: el costo unitario por tenant determina si el plan de pricing es sostenible.

**12.1 Categorías de costo**

|  |  |
|:---|:---|
| **Categoría** | **Componentes típicos y consideraciones** |
| Cómputo | VMs / containers para backend, frontend, workers. Suele ser el costo principal en operación. Optimización: rightsizing, autoscaling agresivo, instancias spot/preemptibles para cargas tolerantes. |
| Base de datos | Nodo primary, réplicas, backups. Crece con tenants y con retención. Optimización: tier de almacenamiento adecuado, retención por categoría según política. |
| Almacenamiento de objetos | Fotos de vehículos, exports, documentos. Crece linealmente con vehículos y conversaciones. Optimización: lifecycle policies que mueven a tier frío, compresión donde aplica. |
| Red y CDN | Egress de tráfico, requests al CDN. Suele ser proporcional al uso del frontend. Optimización: cache agresivo de assets estáticos. |
| Observabilidad | Métricas, logs, trazas, errors. Puede crecer desproporcionadamente. Política del 15% del total declarada en sección 4.10. |
| Servicios externos managed | Sentry, monitoring sintético, eventual managed services (Keycloak, BD) |
| Subprocessors comerciales | WhatsApp Cloud API por mensaje, eventual gateway de pagos por transacción. |

**12.2 Atribución de costos por tenant**

Para que el modelo de pricing sea informado, el equipo conoce el costo aproximado de servir a un tenant promedio. La atribución se hace por una combinación de costos directos (mensajes WhatsApp consumidos por el tenant, almacenamiento de fotos del tenant) y costos prorrateados (cómputo, BD, observabilidad) según un proxy razonable de uso. La precisión no necesita ser perfecta: lo que importa es la magnitud y la tendencia. Cuando el costo por tenant crece más rápido que el ingreso por tenant, hay problema en el modelo de unit economics que requiere atención antes de escalar.

**12.3 Alarmas de costo**

La política operativa incluye alarmas automáticas sobre costo, paralelas a las alarmas operativas. Se monitorean el costo total mensual proyectado contra el presupuesto, el costo por categoría con sus límites, y los spikes anómalos respecto a la línea base. Una alarma se dispara cuando el costo proyectado del mes excede el presupuesto en más de 10%, lo que da tiempo de actuar antes del cierre del período. La automatización tiene gates de seguridad: ningún script puede crear recursos cuyo costo proyectado supere ciertos thresholds sin aprobación humana.

**12.4 Optimización continua**

La revisión de costos es trimestral y produce items concretos de optimización. Las optimizaciones más habituales en este tipo de productos son las siguientes.

- Rightsizing de instancias: nodos sobredimensionados respecto a su uso real.

- Retención de logs y trazas: ajustar retención según valor real de los datos antiguos.

- Compresión y lifecycle de storage: mover datos viejos a tier frío más barato.

- Reserva de capacidad: para cargas estables, instancias reservadas o committed-use vs on-demand.

- Limpieza de recursos huérfanos: snapshots viejos, volúmenes desconectados, ambientes de testing olvidados.

**13. Roadmap de madurez del programa**

Esta sección declara la evolución prevista del programa SRE. Como en los planes paralelos de seguridad y testing, los hitos se declaran en horizontes con resultados verificables que permiten auditar el progreso del programa.

**13.1 Estado al cierre de Ola 0**

El programa tiene en Ola 0 los siguientes elementos vigentes: SLOs declarados para componentes Tier 1, observabilidad básica con métricas RED en todos los componentes, dashboards canónicos de los Tier 1, alertas P0/P1 con runbooks documentados, on-call con rotación entre 3-4 personas, deploys con estrategia rolling y canary disponible, infrastructure as code con state versionado, status page activa. Hay gaps reconocidos: la observabilidad en componentes Tier 2-3 es desigual; los runbooks son menos de los necesarios; el burn rate alerting no está implementado todavía; el toil no se mide formalmente; FinOps es básico.

**13.2 Horizonte 0-6 meses (Ola 1)**

Foco: cerrar gaps básicos del programa y consolidar la operación con los primeros tenants reales en producción.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| SLOs publicados a tenants y reportados mensualmente | Reporte automatizado en portal del tenant; SLA contractual respaldado. |
| Burn rate alerting implementado para SLOs principales | Alertas burn rate fast y slow operativas para API, BD, workers. |
| Catálogo completo de runbooks para alertas activas | Cada alerta tiene runbook; auditoría mensual cierra gaps. |
| Tracking del toil con encuesta mensual | Métrica reportada al equipo y a dirección, target \<25%. |
| Synthetic monitoring externo en producción | Monitor en proveedor reputado con cobertura de endpoints críticos cada 30s. |
| Procedimiento de rollback ejercitado en simulacro | Al menos un simulacro completo documentado con tiempos reales. |
| Atribución de costos por tenant operativa | Dashboard con costo aproximado por tenant; reportable a dirección. |
| Postmortems de todos los incidentes O0/O1 dentro del SLA | 100% de cumplimiento; action items en sistema de tracking. |
| DR ejercitado: failover de PostgreSQL completo | Ejercicio anual documentado; RTO real medido. |

**13.3 Horizonte 6-12 meses (Ola 2)**

Foco: maduración del programa, automatización profunda, primer rol SRE dedicado si la escala lo justifica.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| Incorporación de SRE engineer dedicado | Si la escala lo justifica; alternativa: rol distribuido con 30% del tiempo de un dev senior. |
| Chaos testing programado mensual | Inyecciones controladas en staging; lessons learned al backlog. |
| Auto-remediation de incidentes recurrentes | Al menos 5 alertas con remediación automática (restart, scale, etc). |
| Tooling para self-service de tenants en operaciones comunes | Tenants pueden hacer exports, reset 2FA, etc., sin involucrar soporte. |
| Capacity planning trimestral con forecast pipeline-based | Documento estructurado producido cada trimestre. |
| FinOps maduro: revisión trimestral con optimizaciones priorizadas | Reducción medible del costo unitario por tenant. |
| Multi-region pasivo: backups y DR cross-region | Capacidad demostrada de recuperar en otra región en \<4h. |
| Profiling de performance con producción shadow traffic | Capacidad de evaluar cambios contra tráfico real sin afectar tenants. |

**13.4 Horizonte 12-24 meses (Ola 3)**

Foco: confiabilidad como ventaja competitiva, certificaciones formales, escala probada.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| SLOs upgraded: 99.9% en API principal para Pro y Enterprise | Track record medido durante 6 meses cumpliendo el SLO mejorado. |
| Multi-region activo-activo o activo-pasivo con failover automático | RTO \<30 min ejercitado y validado. |
| Observability como producto interno con SDK propio | Componentes nuevos instrumentados con esfuerzo marginal mínimo. |
| Plataforma SRE consolidada con runbooks ejecutables | Runbooks no son documentos sino scripts ejecutables con dry-run. |
| SRE como input en el ciclo de desarrollo | Reviews de SRE en cambios arquitectónicos; capacity y observability evaluadas pre-merge. |
| Programa formal de Game Days | Ejercicios trimestrales donde el equipo enfrenta escenarios de incidente simulados. |
| Reportes públicos de confiabilidad como ventaja comercial | Página deruedas.com/reliability con métricas históricas y compromisos. |

**13.5 Madurez objetivo en 24 meses**

Al cierre de Ola 3 el programa SRE es ventaja competitiva del producto, no solo función operativa. La confiabilidad declarada se cumple con margen consistente; los incidentes son raros, breves y bien comunicados; el equipo tiene cultura de ingeniería con foco en confiabilidad incorporada al diseño; el costo unitario es competitivo y trackeable; los procesos están automatizados al punto donde la operación normal no consume tiempo humano significativo. El producto se vende parcialmente por su reputación de confiabilidad: las agencias eligen deRuedas sabiendo que está cuando lo necesitan.

**14. Anexos**

**14.1 Plantilla SLO doc**

Para cada SLO formalmente declarado, se mantiene un documento estructurado en el repositorio operacional con la siguiente plantilla.

SLO — \[Nombre del SLO\]

Componente: \[Componente del sistema\]

Tier: \[1/2/3\]

Owner: \[persona o rol responsable\]

Última revisión: YYYY-MM-DD

Próxima revisión: YYYY-MM-DD

\## Definición

Objetivo: \[99.7%, p95 \<300ms, etc.\]

Ventana: \[30 días rolling, 7 días, etc.\]

\## SLI(s) asociado(s)

· Métrica X: \[cálculo concreto\]

· Métrica Y: \[cálculo concreto\]

\## Justificación del objetivo

\[Por qué este número y no otro. Datos históricos, expectativas de tenant,

comparación con SLA público.\]

\## Presupuesto de error

\[Cantidad concreta para la ventana: por ej. 130 minutos / mes\]

\## Política de burn rate

· Fast burn (1h): alerta P0

· Slow burn (6h): alerta P1

\## Histórico de cumplimiento

\[Tabla de últimos N períodos con porcentaje real cumplido\]

\## Acciones cuando se viola

\[Pasos concretos cuando el SLO se rompe\]

\## Historial de modificaciones

· YYYY-MM-DD: descripción del cambio - autor

**14.2 Métricas del programa SRE consolidadas**

Las métricas que el programa reporta consolidadas. Se publican en cadencias distintas según su volatilidad y se usan para distintos fines.

|  |  |  |
|:---|:---|:---|
| **Métrica** | **Cadencia** | **Uso** |
| Cumplimiento de SLOs por componente | Mensual | Health del programa; visible al equipo y a dirección. |
| Presupuesto de error remanente por SLO | Continua | Decisiones de modo (normal/precaución/protección/freeze). |
| Cantidad de incidentes O0/O1 por mes | Mensual | Tendencia de estabilidad. |
| MTTD por severidad | Mensual | Eficacia del alerting. |
| MTTR por severidad | Mensual | Eficacia del runbook y on-call. |
| % de incidentes con postmortem en plazo | Mensual | Salud del proceso de aprendizaje. |
| % de action items de postmortem cerrados a 30 días | Mensual | Capacidad de mejora real. |
| Toil promedio del equipo | Mensual | Salud del programa de automatización. |
| Tiempo medio de release (lead time) | Semanal | Velocidad del equipo. |
| Tasa de rollback de releases | Mensual | Calidad de los cambios. |
| Cantidad de runbooks vigentes / actualizados | Trimestral | Salud de la base de conocimiento. |
| Costo total mensual y por tenant | Mensual | FinOps; insumo para pricing. |
| Cantidad de alertas P0/P1 disparadas | Mensual | Salud del alerting; tendencia esperada descendente. |
| % de alertas que requirieron acción real | Mensual | Salud del programa de alertas; objetivo \>80%. |

**14.3 Glosario**

|  |  |
|:---|:---|
| **Término** | **Definición** |
| Auto-remediation | Capacidad del sistema de responder automáticamente a alertas con acciones predefinidas (reinicio, scale-up, failover). |
| Burn rate | Velocidad a la que se consume el presupuesto de error de un SLO. Burn rate alto significa que el presupuesto se gastaría antes del fin del período si la velocidad se mantiene. |
| Canary deploy | Estrategia de release donde la nueva versión se expone primero a una fracción pequeña del tráfico (1%, luego 5%, etc.) antes del 100%. |
| Capacity planning | Práctica de anticipar y aprovisionar la capacidad necesaria del sistema en función de la carga proyectada. |
| Chaos testing | Práctica de inyectar fallas controladas en sistemas (en staging o producción) para verificar resiliencia y comportamiento bajo estrés. |
| Circuit breaker | Patrón que abre el circuito tras N fallas consecutivas hacia un servicio externo, rechazando inmediatamente nuevas llamadas durante M segundos. |
| DLQ | Dead Letter Queue. Cola donde van los eventos que no pudieron procesarse tras agotar reintentos. |
| Error budget / Presupuesto de error | Complemento del SLO. Si el SLO es 99.7%, el presupuesto de error es 0.3% del tiempo. Es activo gestionable que la organización gasta deliberadamente. |
| FinOps | Disciplina de gestión financiera de operaciones cloud, atendiendo a observabilidad de costos, atribución y optimización. |
| Game Day | Ejercicio donde el equipo enfrenta un escenario de incidente simulado para practicar respuesta sin riesgo real. |
| GitOps | Práctica donde el estado de la infraestructura se declara en git y un agente sincroniza el estado real con la declaración. |
| Handoff | Transferencia de responsabilidad entre turnos de on-call con documentación del estado del sistema y de incidentes abiertos. |
| IaC | Infrastructure as Code. Práctica de declarar la infraestructura en código versionado (Terraform, Pulumi). |
| IC | Incident Commander. Rol coordinador durante un incidente activo. |
| MTTD | Mean Time To Detect. Tiempo medio desde inicio de incidente hasta detección. |
| MTTR | Mean Time To Resolve / Repair. Tiempo medio desde detección hasta resolución. |
| Observabilidad | Capacidad de inferir el estado interno de un sistema a partir de sus outputs externos (métricas, logs, trazas). |
| On-call | Persona o rotación responsable de responder a alertas operativas en una ventana de tiempo específica. |
| OpenTelemetry | Framework estándar y vendor-agnostic para instrumentar aplicaciones con métricas, logs y trazas. |
| PagerDuty / Opsgenie | Plataformas de gestión de alertas y on-call con escalación, rotación y reporting. |
| Postmortem | Análisis posterior a un incidente que documenta cronología, causa raíz, lessons learned y action items. Se hace sin culpa. |
| Rate / Errors / Duration (RED) | Las tres métricas mínimas que cada componente debe exponer: tasa de requests, tasa de errores, distribución de duración. |
| Rollback | Reversión a una versión anterior del software o configuración tras detectar un problema. |
| Runbook | Documento que detalla la respuesta operativa esperada para una alerta o procedimiento específico. |
| Saturation | Métrica que indica cuán cerca está un componente de su capacidad límite. Cuello de botella inminente. |
| Service tier | Clasificación de componentes según su criticidad: Tier 1 crítico, Tier 2 importante, Tier 3 soporte. |
| Silence | Inhibición temporal de alertas durante mantenimientos planificados o investigación de incidente. |
| SLA | Service Level Agreement. Compromiso público con el tenant, parte del contrato. Tiene consecuencias contractuales si se incumple. |
| SLI | Service Level Indicator. Métrica concreta que se mide para evaluar el cumplimiento del SLO. |
| SLO | Service Level Objective. Objetivo interno del equipo, sistemáticamente más estricto que el SLA público. |
| SRE | Site Reliability Engineering. Disciplina de aplicar principios de ingeniería a la operación de sistemas. |
| Synthetic monitoring | Ejecución programada de requests reales contra producción desde monitores externos para detectar caídas que el monitoreo interno no percibe. |
| Toil | Trabajo operativo manual, repetitivo, automatizable, táctico y sin valor permanente. Enemigo del programa SRE. |
| USE (Utilization, Saturation, Errors) | Las tres métricas para componentes de infraestructura: uso, saturación, errores. |
| War room | Espacio virtual o físico donde el equipo coordina la respuesta a un incidente activo. |

**14.4 Control de versiones del documento**

|  |  |  |  |
|:---|:---|:---|:---|
| **Versión** | **Fecha** | **Autor** | **Cambios** |
| 1.0 | Mayo 2026 | Equipo SRE deRuedas | Versión inicial. Cubre programa de Olas 0 y 1 con roadmap a Ola 3. |

La próxima revisión está prevista para noviembre de 2026 al cierre de la Ola 1, donde se actualizarán: estado real del programa respecto al roadmap, SLOs ajustados con datos reales del primer semestre operativo, métricas observadas de cumplimiento, lecciones aprendidas de los primeros incidentes en producción con tenants reales, ajustes al catálogo de alertas y runbooks según experiencia acumulada.
