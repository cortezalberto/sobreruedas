**Plan de Go-To-Market**

**y Pricing**

***deRuedas Gestión***

Estructura de planes, programa de early adopters,

funnel comercial, retención y expansión

*Cierre de la dimensión comercial del SDD · Roadmap GTM*

Versión 1.0 — Mayo de 2026

**1. Introducción y propósito**

Este documento es complementario al cuerpo SDD de deRuedas Gestión y se ocupa de una dimensión que las capas anteriores tocan tangencialmente pero no aterrizan a ejecución concreta: cómo se vende efectivamente el producto. La capa estratégica del SDD declara la hipótesis de negocio, identifica el segmento objetivo y describe el modelo de monetización en términos generales. Pero falta la traducción a tácticas de venta: estructura final de planes con números cerrados, programa formal de early adopters, embudo de adquisición con métricas, ciclo de venta esperado, plan de retención y expansión. Este documento llena ese vacío.

La existencia del documento se justifica por tres razones convergentes. La primera es operativa: cuando el producto está listo técnicamente —al cierre de la Ola 1 según el plan de implementación— el equipo necesita saber qué cobrar, a quién, cómo. Sin estas decisiones tomadas con anticipación, la conversación con el primer prospect se vuelve improvisación; la oferta presentada al primer cliente fija precedente difícil de modificar. La segunda es comercial: las agencias argentinas de vehículos comparan opciones y procesos de compra; un proveedor sin estructura de planes clara, sin programa de incentivos al early adopter, sin material de venta consistente, queda en desventaja frente a competidores que sí los tienen. La tercera es organizacional: el equipo de ventas (cuando exista) y customer success necesitan playbooks que les digan cómo trabajar; sin documento que los explicite, cada persona improvisa según su criterio y la consistencia del trato al cliente se pierde.

**1.1 Audiencia**

El documento tiene cuatro audiencias diferenciadas. Para la dirección de la organización funciona como instrumento de gestión: las métricas de unit economics y de funnel son su tablero de control. Para el equipo comercial —vendedor que se incorpore, customer success, eventual VP de ventas en olas posteriores— funciona como playbook operativo de cómo trabajar el ciclo de venta y la retención. Para los desarrolladores que toman decisiones de producto funciona como recordatorio de los compromisos comerciales adquiridos: qué se prometió a tenants, qué fechas se comprometieron, qué expectativas se generaron. Para inversores, partners y otros stakeholders externos que evalúen la oportunidad, funciona como documento que evidencia rigor en el approach comercial.

**1.2 Posición frente al cuerpo SDD**

El plan GTM no contradice ni reemplaza la capa estratégica del SDD: la baja a tácticas. Las decisiones estratégicas (qué segmento atacar, qué propuesta de valor articular, qué modelo de monetización adoptar) ya están tomadas y este documento las honra. Lo que agrega es traducción a ejecución: pricing concreto, programa concreto, métricas concretas, roles concretos. Cuando una decisión táctica entra en tensión con una decisión estratégica, gana la estratégica y el plan táctico se ajusta; cuando la práctica revela que una decisión estratégica era equivocada, se vuelve a la capa correspondiente del SDD para revisarla, no se contradice silenciosamente desde abajo.

**1.3 Estructura del documento**

El documento está organizado en catorce capítulos. El segundo presenta el posicionamiento comercial sintetizado: segmento, propuesta de valor, diferenciadores. El tercero desarrolla el modelo de pricing con la estructura de planes, los números cerrados y la política de descuentos. El cuarto detalla el programa de early adopters: criterios de selección, beneficios, compromisos. El quinto define las buyer personas con su recorrido de compra. El sexto presenta el funnel completo con etapas, métricas y conversión esperada. El séptimo desarrolla los canales de adquisición. El octavo describe el ciclo de venta con tiempos y materiales. El noveno trata el onboarding comercial diferenciado del técnico. El décimo aborda retención y expansión con métricas y programa de Customer Success. El décimo primero declara las métricas comerciales clave. El décimo segundo trata la estructura del equipo comercial. El décimo tercero presenta el roadmap del programa GTM. El décimo cuarto cierra con anexos: battle cards, plantillas y glosario.

**Aclaración sobre los números:** Los números económicos que aparecen en este documento (precios, costos unitarios, métricas objetivo) son las cifras de planificación al momento de redactar. Se construyen sobre supuestos del Plan estratégico y del Plan SRE, validados parcialmente con investigación de mercado. La política de revisión los actualiza trimestralmente con datos reales del piloto. La economía argentina exige adicionalmente revisión de pricing en pesos cuando la inflación lo requiera; los precios en este documento se expresan en USD para estabilidad y se convierten a ARS al tipo de cambio del momento.

**2. Posicionamiento comercial**

Esta sección sintetiza el posicionamiento del producto en términos accionables para venta. No reemplaza la capa estratégica del SDD ni el Brand Book —ambos cubren posicionamiento desde sus propios ángulos— sino que extrae los elementos directamente útiles para la conversación comercial.

**2.1 Segmento objetivo refinado**

El segmento primario son agencias argentinas de vehículos con tres a quince vendedores activos, stock entre cuarenta y trescientos vehículos según momento, ingresos comerciales mensuales entre treinta y trescientos millones de pesos, ubicadas en ciudades de más de cien mil habitantes con mercado de usados activo. Esta caracterización tiene tres bordes definidos. El borde inferior (agencias muy chicas, uno o dos vendedores) queda fuera porque el ticket que pueden pagar no soporta el costo de adquisición ni de soporte. El borde superior (concesionarias oficiales con cincuenta vendedores y procesos enterprise pesados) queda fuera porque ya tienen software a medida o ERPs corporativos y la decisión de compra es lenta y compleja. El borde geográfico se restringe a Argentina inicialmente porque el producto está optimizado para el contexto argentino (ley 25.326, integración con el portal sectorial argentino, comprobantes fiscales locales, idioma rioplatense).

**2.2 Sub-segmentos identificados**

Dentro del segmento primario se distinguen tres sub-segmentos con dolor distinto y proceso de compra propio.

|  |  |  |
|:---|:---|:---|
| **Sub-segmento** | **Caracterización** | **Dolor dominante** |
| Agencia tradicional digitalizándose | 3-6 vendedores, dueño cercano a la operación, planillas + WhatsApp + portal manual | Cansancio operativo de cargar todo dos veces, perder leads en WhatsApp, no saber qué tiene cada vendedor en mano. |
| Agencia mediana ya con CRM genérico | 5-10 vendedores, gerente comercial dedicado, usa HubSpot/Pipedrive/similar | El CRM no entiende vehículos; falta integración con WhatsApp; falta integración con el portal; pagan caro por features que no usan. |
| Mini-red en crecimiento | 8-15 vendedores entre 2-3 sucursales, dueño con visión de escalar | Falta visibilidad consolidada multi-sucursal; cada sucursal trabaja con su criterio; no se aprovechan leads cross-sucursal. |

**2.3 Propuesta de valor por sub-segmento**

La propuesta de valor se modula según sub-segmento. La voz de marca se mantiene pero el énfasis del mensaje cambia.

|  |  |
|:---|:---|
| **Sub-segmento** | **Propuesta** |
| Tradicional digitalizándose | Pasá de tres herramientas a una. Tu stock, tus leads y tu WhatsApp en un solo lugar, sin que tengas que cargar nada dos veces. Aprenderlo te lleva una mañana. |
| Mediana con CRM genérico | Lo que tu CRM actual no entiende, deRuedas sí. Inventario de vehículos con campos del sector, conversaciones por WhatsApp asociadas al lead automáticamente, publicación al portal sin doble carga. Sin features que no necesitás. |
| Mini-red en crecimiento | Visibilidad consolidada de tu red, ranking de vendedores, leads compartidos cross-sucursal, control central con autonomía local. Lo que necesitás para crecer ordenado. |

**2.4 Diferenciadores accionables**

Los diferenciadores se enuncian aquí en forma operativa: lo que un vendedor de deRuedas puede usar en una conversación concreta cuando un prospect compara con alternativas.

- Vertical específico para agencias argentinas: vocabulario, campos, integraciones diseñadas para el negocio. Ningún CRM genérico cubre esto sin customización costosa.

- WhatsApp Business integrado nativamente con conversaciones asociadas al lead y al vehículo. Ningún competidor argentino lo tiene plenamente integrado al inicio del 2026.

- Publicación al portal sectorial con sincronización automática. Las agencias hoy cargan manualmente o pagan integraciones de terceros frágiles.

- Curva de aprendizaje baja: la app está pensada para vendedores, no para administradores de TI. El alta del primer auto toma cinco minutos.

- Pricing predecible y honesto: sin asteriscos chicos con condiciones ocultas, sin features bloqueadas que parecían incluidas, sin sobrecargo por usuarios.

- Respaldo argentino: factura local, soporte en horario argentino, equipo que entiende el contexto comercial del país.

**2.5 Lo que NO somos (frente a competidores)**

La definición negativa también vale para venta. Los siguientes posicionamientos quedan explícitamente fuera y se aclaran cuando un prospect los proyecta sobre nosotros.

- No somos un ERP automotriz: no llevamos contabilidad, no procesamos pagos, no gestionamos inventario contable. Nos integramos con sistemas que sí lo hacen.

- No somos un marketplace: no exponemos los vehículos a compradores finales fuera del portal sectorial; ese es trabajo del portal.

- No somos un sistema de financiación: no calculamos ni gestionamos préstamos prendarios; eso lo hace el banco con su propio sistema.

- No somos software empresarial pesado: no requerimos consultoría de implementación de meses, no exigimos compromiso plurianual, no facturamos setup fees ocultos.

**Test de venta:** Un vendedor de deRuedas debería poder explicar el producto en menos de tres minutos, articular el dolor que resuelve para el sub-segmento del prospect, mostrar concretamente cómo se diferencia de las alternativas que el prospect mencionó. Si tarda más, falta práctica con el material; si suena igual a otros CRMs, falta entendimiento del posicionamiento.

**3. Modelo de pricing**

Esta sección define la estructura de precios del producto. Las decisiones que aparecen acá tienen consecuencias inmediatas en la conversación comercial y en las métricas de unit economics. La política adoptada privilegia la simplicidad sobre la sofisticación: un modelo claro que el prospect entiende en treinta segundos vale más que un modelo óptimo en una hoja de cálculo que confunde en la conversación.

**3.1 Filosofía de pricing**

El programa adopta seis principios sobre pricing. Primero, pricing por valor antes que por costos: el precio se ancla en el valor que el cliente recibe, no en lo que nos cuesta producirlo. Segundo, transparencia radical: el precio publicado es el precio que paga el tenant; cualquier descuento o variación tiene reglas explícitas y no es discrecional. Tercero, predecibilidad: el cliente puede estimar cuánto pagará el mes siguiente sin sorpresas; las variaciones por uso son acotadas y avisadas. Cuarto, alineación con el tamaño del cliente: cobrar más a quien obtiene más valor (más vendedores, más operaciones) sin convertir esto en castigo al crecimiento. Quinto, simplicidad: tres planes definidos antes que catorce dimensiones combinatorias; la simplicidad acelera ventas. Sexto, anclajes argentinos: precios en USD para estabilidad pero pagables en ARS al tipo de cambio del momento, factura local con IVA discriminado, formas de pago habituales del mercado.

**3.2 Estructura de tres planes**

La estructura adoptada es de tres planes con segmentación clara: Starter para agencias chicas que recién se digitalizan, Pro para el segmento principal del producto, Enterprise para mini-redes y operaciones complejas. La diferencia entre planes no es artificial (mismas features con paywall arbitrario) sino sustantiva: capacidades distintas por necesidades distintas.

|  |  |  |  |
|:---|:---|:---|:---|
|  | **Starter** | **Pro** | **Enterprise** |
| **Precio mensual** | USD 49 / mes | USD 149 / mes | USD 399 / mes (desde) |
| **Vendedores incluidos** | 2 usuarios | 5 usuarios | 15 usuarios |
| **Vendedor extra** | USD 15 / mes c/u | USD 12 / mes c/u | USD 10 / mes c/u |
| **Vehículos en stock** | Hasta 80 | Hasta 300 | Sin límite práctico |
| **Mensajes WhatsApp / mes** | 1,500 incluidos | 5,000 incluidos | 20,000 incluidos |
| **Sucursales** | 1 | Hasta 2 | Hasta 5 |
| **Integración portal sectorial** | Sí | Sí | Sí |
| **WhatsApp Business integrado** | Sí | Sí | Sí |
| **Reportes avanzados** | Básicos | Completos | Completos |
| **Pipeline customizable** | Estándar | Customizable | Customizable |
| **API pública** | No | Read-only | Completa |
| **Single Sign-On (SSO)** | No | No | Sí |
| **DPA personalizable** | Estándar | Estándar | Personalizable |
| **SLA contractual** | 99.0% | 99.5% | 99.9% |
| **Soporte** | Email, hábil | Email + WhatsApp, hábil | Dedicado, 24/7 críticos |
| **Onboarding asistido** | Self-service | 1 sesión guiada | Plan completo |
| **Audit logs** | 30 días | 12 meses | 24 meses |
| **Exports / portabilidad** | Sí | Sí | Sí + API |

**Sobre los precios en USD:** Los precios listados son de planificación al momento de redactar y reflejan la realidad del mercado argentino para SaaS B2B vertical. Las equivalencias en ARS se calculan al tipo de cambio del momento y se actualizan en la página comercial al menos mensualmente. La política de revisión de precios es trimestral; los aumentos respetan los plazos contractuales con tenants vigentes (sin aumento durante el primer año contratado).

**3.3 Componentes del precio**

El precio total que paga un tenant se compone de tres elementos. La suscripción base del plan elegido (Starter, Pro o Enterprise), facturada mensualmente. Los extras por usuarios adicionales sobre los incluidos en el plan, también mensuales. Los consumos variables que excedan los límites incluidos: mensajes de WhatsApp por encima del cupo se cobran a USD 0.012 por mensaje; vehículos por encima del límite del plan obligan a upgrade. La política es que el cliente conoce de antemano todos los componentes y puede simularlos en una calculadora pública en deruedas.com/pricing.

**3.4 Período de prueba**

Todo prospect accede a un período de prueba gratuito de 14 días con todas las features del plan Pro habilitadas, sin requerir tarjeta de crédito al inicio. Los datos cargados durante la prueba se preservan si el tenant se convierte; si no se convierte tras 14 días, los datos se eliminan a los 30 días siguientes con previo aviso por email. La duración de 14 días se eligió por dos razones: es suficiente para que la agencia cargue su stock real y haga operaciones reales (la prueba demuestra valor); es lo suficientemente acotada para forzar decisión sin que se vuelva ambigüedad permanente. La extensión del trial es excepcional y se concede caso por caso cuando el prospect comparte motivo legítimo.

**3.5 Política de descuentos**

Los descuentos son herramienta de venta pero también riesgo de erosión del precio percibido. La política es estricta y conocida por el equipo comercial: las excepciones requieren aprobación del responsable comercial.

|  |  |  |
|:---|:---|:---|
| **Tipo de descuento** | **Magnitud** | **Condiciones** |
| Pago anual anticipado | 15% | Único pago al inicio del año, sin proratéo si baja antes de los 12 meses. |
| Compromiso bianual | 20% | Contrato firmado por 24 meses con condiciones de salida acotadas. |
| Early adopter | 30% sobre el plan elegido | Primeros 10 tenants Pro o Enterprise. Sección 4 detalla. |
| Convenio sectorial | 10% | Tenants miembros de cámara o asociación con la que firmamos convenio. |
| Referido (referral) | 1 mes gratis | Tanto al referidor como al referido cuando este último cierra contrato. |
| Volumen multi-sucursal | Negociable | Mini-redes que firman para 2+ sucursales simultáneamente, evaluado caso por caso. |
| Excepcional caso a caso | Hasta 25% | Aprobación del responsable comercial; documentado en CRM con razón. |

**3.6 Setup fees y costos one-off**

La política operativa es no cobrar setup fees salvo en casos específicos. Esto se diferencia de competidores enterprise que sí lo hacen y simplifica la conversación comercial: no hay shock inicial. Los costos one-off que sí se cobran son los siguientes.

- Migración de datos desde otro sistema: gratis cuando es importable mediante CSV estándar; cobrado a USD 200 a USD 800 cuando requiere desarrollo específico para fuentes no estándar.

- Capacitación in-situ presencial: USD 300 por jornada cuando el tenant la solicita. La capacitación remota está incluida en planes Pro y Enterprise.

- Personalización de campos o flujos específica al tenant que no es feature general del producto: cobrada por hora a tarifa de desarrollo.

- Integración con sistemas legacy del tenant (su ERP custom, etc.): cotizada caso por caso.

**3.7 Pricing público vs negociado**

Los planes Starter y Pro son de pricing público: lo que figura en deruedas.com/pricing es lo que paga el tenant, ajustes via la política de descuentos. El plan Enterprise tiene piso público (USD 399 desde) pero permite negociación: tenants con requirements específicos (más usuarios, más sucursales, integraciones custom, SLA reforzado) acuerdan precio. La política operativa es que ningún Enterprise se cierra a menos del piso publicado salvo aprobación de dirección.

**3.8 Métodos de pago**

Los métodos aceptados son los habituales en el mercado argentino para SaaS B2B. Tarjeta de crédito (recurring) con cargo automático al inicio del período de facturación. Transferencia bancaria con factura electrónica emitida vía AFIP, con plazo de pago de 10 días corridos. Mercado Pago con cargo automático para tenants Starter. Para tenants enterprise se acepta orden de compra con condiciones específicas. Los pagos en USD están disponibles para tenants con cuenta en dólares o cliente del exterior.

**3.9 Política de cobranza**

La cobranza tiene workflow definido. Día 1 del período: emisión de factura y cargo automático cuando aplica. Día 5 si no pagó: recordatorio automático por email. Día 10: segundo recordatorio + intento de cargo automático nuevamente. Día 15: aviso de suspensión inminente; contacto humano de customer success. Día 20: suspensión del servicio (la app entra en modo solo lectura para no perder los datos del tenant). Día 60 sin pago ni acuerdo: cancelación del servicio con eliminación programada de datos a 30 días según procedimiento del Plan de Seguridad.

**3.10 Modelo financiero — supuestos clave**

La sostenibilidad del modelo de pricing depende de supuestos que se trackean para validarlos en la práctica. Los supuestos centrales son los siguientes.

|  |  |  |
|:---|:---|:---|
| **Supuesto** | **Valor planeado** | **Forma de validación** |
| Costo cloud por tenant promedio | USD 12 / mes | Atribución de costos por tenant (FinOps, Plan SRE) |
| Costo de WhatsApp por tenant Pro | USD 18 / mes | Mensajes consumidos x tarifa Meta |
| Costo de soporte por tenant | USD 8 / mes | Tiempo de Customer Success / cantidad tenants |
| Margen bruto por plan Pro | 75% | Cálculo (USD 149 - USD 38) / USD 149 |
| CAC objetivo (Customer Acquisition Cost) | USD 250 - USD 600 | Inversión comercial / clientes cerrados |
| Período de payback de CAC | \<6 meses en Pro | MRR del cliente / CAC dividido para igualar |
| LTV (Lifetime Value) objetivo | USD 4,500 mínimo | Promedio de duración de cliente x MRR |
| Ratio LTV/CAC | ≥ 7 | Métrica derivada |
| Churn mensual objetivo | \<3% | Cancelaciones / base activa al inicio del mes |

**Sobre la validación de supuestos:** La política operativa es revisar trimestralmente los supuestos contra datos reales y ajustar el modelo cuando un supuesto se desvía sistemáticamente. La economía argentina obliga adicionalmente a revisión de pricing en pesos cuando la inflación supera el 10% en el trimestre.

**4. Programa de early adopters**

Esta sección define el programa específico para los primeros tenants que adoptan el producto. El programa cumple tres funciones simultáneas: validar la propuesta de valor con clientes reales, acumular evidencia (testimonios, casos, métricas) que catalice ventas posteriores, y generar inputs cualitativos para refinar el producto antes del lanzamiento general. La estructura del programa busca alinear los incentivos: el early adopter recibe condiciones excepcionales a cambio de asumir el riesgo y aportar feedback estructurado.

**4.1 Definición del programa**

**Tamaño objetivo:** 10 a 12 tenants

**Duración del programa:** 6 meses contados desde el alta del tenant

**Plan elegible:** Pro o Enterprise (no Starter por insuficiencia de uso para validar)

**Período de aceptación de candidaturas:** del lanzamiento de Ola 1 hasta completar los 12 cupos o 90 días, lo que ocurra primero

**Posicionamiento:** exclusivo y limitado, no oferta abierta indefinida

**4.2 Criterios de selección**

No todo prospect califica como early adopter. Los criterios son explícitos y se evalúan al inicio de la conversación, no al final.

- Pertenece al segmento objetivo definido en sección 2.1: agencia argentina con 3-15 vendedores, stock 40-300 vehículos.

- Tiene operación real activa: vende vehículos efectivamente, no es startup en gestación ni operación dormida.

- Tiene capacidad de adopción: alguien dentro del tenant tiene tiempo y disposición para liderar la implementación.

- Acepta firmar el acuerdo de early adopter con sus términos específicos (sección 4.5).

- Tiene perfil de comunicador o referente sectorial: agencias visibles en cámaras, asociaciones, redes profesionales del sector. La visibilidad multiplica el valor del testimonio futuro.

- Acepta el rol de feedback estructurado: una sesión mensual de 30-45 minutos con el equipo durante el programa.

**4.3 Beneficios para el early adopter**

|  |  |
|:---|:---|
| **Beneficio** | **Detalle** |
| 30% de descuento sobre el plan elegido | Aplicado durante los primeros 12 meses de uso. A partir del mes 13 se reajusta a tarifa estándar con preaviso. |
| Setup y onboarding completo sin costo | Sesiones de configuración, capacitación remota, importación de datos asistida. Equivalente a USD 600-1500 según complejidad. |
| Línea directa con el equipo | Canal Slack o WhatsApp dedicado con respuesta en horas hábiles, no horario estándar de soporte. |
| Influencia sobre el roadmap | Las features que el early adopter solicita y son consistentes con la dirección del producto, se priorizan. No se prometen features arbitrarias pero se escucha activamente. |
| Reconocimiento como early adopter | Cuando el tenant lo acepta, mención pública en deruedas.com/customers. Visibilidad sectorial. |
| Bloqueo de tarifa por 12 meses | Cualquier aumento general de pricing no afecta al early adopter durante el primer año contratado. |
| Garantía extendida de retención de datos | Si el tenant decide no continuar tras el programa, los datos se exportan completamente y se preservan 90 días en lugar de los 30 estándar. |

**4.4 Compromisos del early adopter**

Para que el programa sea recíproco, el early adopter acepta compromisos específicos. La voluntariedad y el sentido común de estos compromisos son lo que diferencia un early adopter genuino de un cliente que solo busca el descuento.

- Sesión mensual de feedback estructurado de 30-45 minutos con el equipo de producto durante los 6 meses del programa.

- Reporte cualitativo al cierre del programa: una conversación de 60 minutos donde el tenant comparte qué funcionó, qué no, qué le gustaría que cambiara.

- Disposición a ser referencia para otros prospects: aceptar 2-3 llamadas durante el primer año donde un prospect consulta sobre la experiencia. La frecuencia se acuerda.

- Autorización para mencionar el nombre y logo del tenant como cliente, salvo objeción explícita por motivos competitivos.

- Aceptación de que el producto está en evolución activa: pueden aparecer bugs, features pueden cambiar, downtime planificado puede ocurrir con más frecuencia que en operación madura.

**4.5 Acuerdo formal**

El programa se formaliza con acuerdo escrito que el tenant firma junto con el contrato del servicio. El acuerdo enuncia explícitamente los beneficios y los compromisos, las condiciones de fin del programa y la transición al pricing regular. El acuerdo es contractual: no es promesa verbal, no es flexibilidad indefinida. La formalidad protege a las dos partes y evita la confusión común en programas similares donde, ante un desencuentro, ninguno recuerda exactamente qué se acordó.

**4.6 Cronograma del programa**

Mes 0 Firma del acuerdo + onboarding intensivo

· Sesión 1: configuración + carga inicial

· Sesión 2: training a vendedores

· Setup completo en 2 semanas máx.

Mes 1 Operación supervisada + primer feedback

· Acompañamiento estrecho

· 1ra sesión de feedback estructurado

· Identificación de bloqueos tempranos

Mes 2 Operación con autonomía creciente

· 2da sesión de feedback

· Métricas de adopción medidas

Mes 3 Mid-term review

· Revisión cuantitativa de uso

· Ajustes acordados al producto si los hay

· 3ra sesión de feedback

Mes 4-5 Operación madura del tenant

· 4ta y 5ta sesión de feedback

· Identificación de oportunidades de expansión

Mes 6 Cierre del programa

· Reporte final cualitativo del tenant

· Decisión de continuidad y transición pricing

· Caso de éxito documentado si el tenant lo aprueba

**4.7 Transición a cliente regular**

Al cierre del programa, el tenant tiene tres opciones, comunicadas con 30 días de anticipación. Continuar como cliente regular: el descuento del 30% se mantiene en una rampa graduada (15% el segundo año, sin descuento desde el tercero), el resto del beneficio se mantiene mientras el tenant esté activo. Continuar con condiciones renegociadas: si el tenant tiene volumen significativamente mayor al planeado o requirements que justifican plan diferente, se renegocia. Discontinuar: el tenant puede no continuar; se ejecuta el procedimiento de offboarding con preservación extendida de datos.

**4.8 Métricas del programa**

La efectividad del programa se mide con métricas concretas que se reportan al cierre.

- Tasa de retención al cierre del programa (objetivo: ≥75%).

- NPS de los early adopters al cierre (objetivo: ≥50).

- Cantidad de casos de éxito documentados con autorización del tenant.

- Cantidad de referencias proporcionadas a prospects (llamadas aceptadas durante primer año).

- Cantidad de prospects cerrados con referencia de early adopter (atribución directa).

- Cantidad de features priorizadas por feedback de early adopters efectivamente entregadas.

**Disciplina del programa:** El tamaño limitado del programa (10-12 tenants) es deliberado. Programas más grandes diluyen la atención y convierten a los early adopters en clientes que reciben descuento sin beneficio organizacional. La política operativa es no aceptar más tenants en el programa una vez completados los 12 cupos, aunque el prospect sea atractivo: para esos casos se ofrece pricing standard con eventual descuento estándar.

**5. Buyer personas**

Esta sección describe a las personas que intervienen en la decisión de compra y posterior uso del producto. La distinción de personas no es académica: cada una tiene preocupaciones distintas, lenguaje distinto, criterios de éxito distintos. Una conversación comercial efectiva habla a la persona adecuada en cada momento. Vender al usuario final cuando hay que convencer al decisor es ineficaz; vender al decisor cuando el usuario final tiene veto es contraproducente.

**5.1 Persona 1 — Eduardo, dueño de agencia mediana**

**Edad:** 45-58 años

**Rol:** Dueño y gerente comercial al mismo tiempo

**Background:** 20-30 años en el rubro automotor, conoce el negocio en detalle, tiene relaciones comerciales sólidas

**Tecnología:** Usuario habitual de WhatsApp y Excel; menos cómodo con software complejo; valora simpleza y ahorro de tiempo

**Decisión de compra:** Es decisor final. Consulta a su contador y a un vendedor de confianza pero la firma es suya.

**Qué le importa**

Eduardo se preocupa por que el negocio funcione: que los autos roten, que los vendedores cierren, que los gastos no se descontrolen. Le importa el flujo de caja más que las métricas avanzadas; le importa que su equipo trabaje cómodo más que las features tecnológicas brillantes. Le importa especialmente la confiabilidad: software que se cae cuando lo necesita es desastre operativo.

**Qué le preocupa**

Eduardo ha sido prometido y decepcionado por software antes. Le preocupa el costo total que no aparece al inicio (“me van a empezar a cobrar más cuando me enganche”). Le preocupa que sus vendedores resistan el cambio. Le preocupa que sus datos comerciales sensibles —márgenes, listas de clientes, históricos— queden expuestos.

**Cómo se le habla**

Conversación directa, en su lenguaje sectorial, sin jerga tecnológica. Casos concretos antes que abstracciones (“si un Toyota Hilux entra al lote, en cinco minutos está publicado en el portal y disponible para tus vendedores”). Honestidad sobre limitaciones: prometer menos y entregar más. Demostraciones con su propio inventario simulado vale más que demos genéricas.

**Cómo se le pierde**

Lenguaje corporativo o tecnológico que no entiende. Promesas exageradas que cualquier persona del rubro detecta como marketing inflado. Vendedor agresivo que apura el cierre. Costos que aparecen tras la firma. Setup complicado que requiere consultor externo.

**5.2 Persona 2 — Marcos, gerente comercial de mini-red**

**Edad:** 35-48 años

**Rol:** Gerente comercial profesional, no propietario

**Background:** Carrera en ventas, posiblemente con paso por concesionaria oficial o multinacional del sector

**Tecnología:** Cómodo con software, ha usado CRMs como HubSpot o Pipedrive en otras posiciones

**Decisión de compra:** Decide o influencia mucho en la decisión. Reporta al dueño/director y necesita justificar la elección con números.

**Qué le importa**

Marcos quiere visibilidad sobre la operación: cuántos leads cada vendedor, qué etapa del pipeline, qué se está cayendo. Le importa la productividad medible de su equipo. Le importa profesionalizar el proceso comercial de su organización. Le importa también su propia carrera: implementar bien deRuedas le da credibilidad interna.

**Qué le preocupa**

Le preocupa que el producto no sea suficientemente sofisticado y le quede chico al crecer. Le preocupa la integración con el resto del stack del tenant (eventual ERP, sistemas contables). Le preocupa que sus vendedores no adopten.

**Cómo se le habla**

Conversación profesional con métricas concretas, casos de mejora medible, comparación honesta con alternativas. Demos que muestren reportes y dashboards. Énfasis en cómo el producto le da control y visibilidad. Mencionar API y customización para futuro le da tranquilidad de que el producto puede crecer con su organización.

**5.3 Persona 3 — Carla, vendedora del lote**

**Edad:** 25-50 años

**Rol:** Vendedora con clientela propia, paga por comisión

**Background:** Variable: desde profesionales con carrera en ventas hasta personas que aprendieron en el rubro

**Tecnología:** Vive en su WhatsApp, usa Excel a regañadientes, no le interesa la tecnología por la tecnología

**Decisión de compra:** No decide pero puede vetar de hecho: si Carla no usa el producto, el tenant no lo usa.

**Qué le importa**

A Carla le importa cerrar ventas. Cualquier herramienta que la ayude a cerrar más rápido o más, le interesa. Cualquier herramienta que la haga perder tiempo cargando datos en lugar de vendiendo, la rechaza. Le importa que sus contactos y conversaciones queden con ella, no se evaporen si cambia de agencia.

**Qué le preocupa**

Le preocupa la curva de aprendizaje: si tiene que tomarse tres días para aprender el sistema, perdió tres días de comisiones. Le preocupa el control: que su jefe vea exactamente qué hace y qué no hace puede sentirse invasivo. Le preocupa la tecnología fallando justo cuando está cerrando una venta.

**Cómo se le habla**

Hablar de cómo el producto la ayuda a ella, no a su jefe. Mostrar que es rápida, que se aprende en una hora, que se ve linda en el celular. Reconocer que su trabajo principal es vender y que el producto es asistente, no supervisor. Cuando Carla siente que el producto la respeta como profesional, lo adopta; cuando se siente fiscalizada, lo rechaza.

**5.4 Persona 4 — Ana, administrativa contable**

**Edad:** 30-55 años

**Rol:** Maneja papeles, contratos, documentación, contabilidad

**Background:** Suele tener formación contable o administrativa, valora orden y trazabilidad

**Tecnología:** Usuaria avanzada de Excel, cómoda con software cuando es claro y predecible

**Decisión de compra:** Influencia importante en aspectos de gestión documental, fiscal y de procesos.

**Qué le importa**

Ana valora trazabilidad: saber qué pasó, cuándo, quién lo hizo. Le importa que la documentación esté ordenada, que los contratos estén accesibles, que las operaciones queden registradas. Es la primera en pedir reportes y exports y la primera que detecta inconsistencias.

**Cómo se le habla**

Demostrar capacidades de export, audit log, reportes contables. Hablar de DPA y cumplimiento de privacidad le habla directamente. Mostrar que el producto se integra (o se va a integrar) con sistemas contables vale mucho. Ana suele convertirse en aliada interna del producto cuando ve que respeta sus criterios profesionales.

**5.5 Mapa de involucramiento por etapa de venta**

|  |  |  |  |  |  |
|:---|:---|:---|:---|:---|:---|
| **Etapa** | **Eduardo (dueño)** | **Marcos (gerente)** | **Carla (vendedora)** | **Ana (admin)** | **Foco** |
| Awareness | Bajo | Medio | — | — | Marcos |
| Evaluación | Medio | Alto | — | — | Marcos |
| Demo | Alto | Alto | Medio | Medio | Todos |
| Decisión | Alto | Alto | Bajo (veto) | Medio | Eduardo + Marcos |
| Onboarding | Bajo | Alto | Alto | Alto | Marcos + usuarios |
| Adopción | Bajo | Medio | Alto | Alto | Carla + Ana |
| Renovación | Alto | Alto | — | Medio | Marcos + Eduardo |

**6. Funnel de adquisición**

Esta sección define el embudo desde que un prospect oye hablar de deRuedas por primera vez hasta que se convierte en cliente activo y referente. La definición explícita del funnel permite medir conversión por etapa, identificar dónde se pierden prospects, e invertir esfuerzo donde mueve la aguja.

**6.1 Etapas del funnel**

UNIVERSO TOTAL

Agencias del segmento (~5,000 en AR)

↓

AWARENESS

Conocen que deRuedas existe

↓

INTEREST

Visitan la web, dejan contacto

↓

EVALUATION

Demo agendada y realizada

↓

TRIAL

Período de prueba activo de 14 días

↓

DECISION

Conversión a plan pago

↓

ONBOARDING

Setup completo y uso productivo en 30 días

↓

RETENTION

Cliente activo a 6 meses

↓

EXPANSION / REFERRAL

Upgrade de plan o referencia a otro tenant

**6.2 Conversión esperada por etapa**

Las tasas que siguen son objetivos planificados al inicio del programa. Reflejan benchmarks típicos de SaaS B2B vertical en mercados similares y se ajustarán con datos reales del piloto. La política operativa es revisar trimestralmente las conversiones reales y actuar sobre las etapas con peor performance.

|  |  |  |  |
|:---|:---|:---|:---|
| **Transición** | **Tasa objetivo** | **Volumen ejemplo** | **Notas** |
| Awareness → Interest | 5% | 1000 → 50 | Depende fuertemente del canal: contenido orgánico tiene 2-3%, eventos sectoriales 10-15%. |
| Interest → Evaluation (demo) | 30% | 50 → 15 | Depende de calidad de la web y del proceso de captación. |
| Evaluation → Trial | 60% | 15 → 9 | Depende de la calidad de la demo y del fit del prospect. |
| Trial → Decision (close) | 40% | 9 → 4 | Métrica más sensible al producto en sí: si el trial demuestra valor, convierte; si no, no. |
| Decision → Onboarding completo | 90% | 4 → 3.6 | Lo que se pierde son tenants que firman pero no llegan a usar realmente. |
| Onboarding → Retention 6m | 80% | 3.6 → 2.9 | Métrica core de salud del producto. |
| Retention → Referral | 30% | Referidos generan nuevos prospects | Multiplicador del embudo cuando el producto es bueno. |

**Lectura del ejemplo:** De 1,000 agencias que oyen hablar de deRuedas, planificadamente alrededor de 4 cierran y 2.9 se mantienen activas a los 6 meses. La conversión total awareness → cliente activo es de aproximadamente 0.3%. Estos números justifican esfuerzo razonable de top-of-funnel: no es realista vender 100 tenants nuevos por mes con conversación uno a uno; se requieren canales que escalen.

**6.3 Métricas por etapa**

|  |  |
|:---|:---|
| **Etapa** | **Métricas trackeadas** |
| Awareness | Visitas únicas a deruedas.com / mes; menciones en redes profesionales; impresiones en eventos sectoriales. |
| Interest | Leads generados / mes; fuente del lead; tiempo desde primer contacto hasta primer follow-up del equipo. |
| Evaluation | Demos agendadas; demos efectivamente realizadas; show rate (% que efectivamente atiende). |
| Trial | Trials activos; activación dentro del trial (si efectivamente se cargaron datos y se usaron features clave); engagement durante el trial. |
| Decision | Cierres; ciclo de venta promedio; razones de no cierre (pricing, timing, fit, otra opción elegida). |
| Onboarding | Tenants en onboarding; tiempo desde firma hasta uso productivo; eventos de adopción de features clave. |
| Retention | Tasa de retención mensual; churn por cohorte; NPS; tickets de soporte por tenant. |
| Expansion | Upsells (Starter → Pro, Pro → Enterprise); cross-sells (más usuarios, más sucursales); revenue por tenant. |

**6.4 Identificación de bloqueos**

La política operativa es revisar el funnel semanalmente para detectar bloqueos. Una etapa se considera bloqueada cuando su conversión cae más de 30% respecto al objetivo durante dos semanas consecutivas. La acción depende de la etapa. Si Interest cae: revisar la web, los canales de adquisición, el match del mensaje con la audiencia. Si Evaluation cae: revisar la calidad de los leads (¿son del segmento?), el proceso de captación, el discurso comercial. Si Trial → Decision cae: revisar el producto (¿el trial demuestra valor real?), el seguimiento del trial, el pricing percibido. Si Retention cae: revisar el onboarding, el éxito temprano del cliente, la calidad del producto.

**7. Canales de adquisición**

Esta sección desarrolla los canales por los que se atrae a prospects. La política operativa adopta una mezcla equilibrada en lugar de apostar todo a un solo canal: la concentración en un canal único produce vulnerabilidad cuando ese canal cambia su economía o su efectividad. La regla es priorizar 2-3 canales activos al mismo tiempo y rotar el énfasis según los datos.

**7.1 Mapa de canales**

|  |  |  |  |
|:---|:---|:---|:---|
| **Canal** | **Volumen esperado** | **Costo unitario** | **Características** |
| Outbound directo (cold call/email) | Bajo | Alto | Conversión alta cuando el prospect coincide con segmento, lento de escalar. |
| Inbound vía web + contenido | Medio | Medio | Construcción lenta inicial pero composición sostenida en el tiempo. |
| Eventos sectoriales | Bajo-Medio | Alto puntual | Calidad de leads alta, exposición a decisores, frecuencia limitada. |
| Referidos de clientes existentes | Medio (cuando hay base) | Bajo | Conversión muy alta, multiplicador potente, requiere base instalada. |
| Partnerships sectoriales | Variable | Variable | Apalancamiento sobre relaciones existentes, requiere acuerdo formal. |
| Publicidad pagada (Meta, Google) | Medio | Medio-Alto | Resultados rápidos pero costo creciente con la competencia. |

**7.2 Canal: Outbound directo**

Es el canal principal en los primeros meses cuando todavía no hay tracción inbound. Consiste en identificar agencias del segmento, contactarlas con propuesta personalizada y agendar conversación. La calidad importa más que el volumen: un email personalizado a una agencia investigada vale más que cien emails genéricos. La política operativa para outbound es la siguiente.

- Investigación previa antes de contactar: ver el sitio web del prospect, su perfil en redes profesionales, su presencia en el portal sectorial, eventuales menciones de prensa.

- Mensaje inicial personalizado que demuestre que se conoce al prospect (“vi que tienen 47 vehículos publicados en el portal”) y propone valor concreto.

- Cadencia de seguimiento de tres toques en dos semanas: si tras el tercer intento no hubo respuesta, se cierra el prospect como “no responde” y se reintenta en 6 meses.

- LinkedIn como canal complementario al email: conexiones contextuales preceden o suceden al email, no se duplican.

- WhatsApp Business como canal de seguimiento cuando el prospect ya respondió: respeta la cultura comunicativa argentina.

**7.3 Canal: Inbound vía web y contenido**

La página comercial deruedas.com es activo crítico del programa GTM. La política es construirla con disciplina y mantenerla viva con contenido sectorial relevante. La estructura mínima requerida en Ola 1 es la siguiente.

- Landing principal con propuesta de valor clara, demo en video corto, calculadora de pricing, formulario de contacto sin fricción.

- Página de pricing con planes detallados, calculadora interactiva, FAQ sobre pricing.

- Página de seguridad y privacidad con compromiso de Ley 25.326 y resumen del programa de seguridad.

- Páginas de casos de uso por sub-segmento con copy adaptado.

- Blog con contenido sectorial: artículos sobre gestión de leads, productividad de vendedores, tendencias del mercado de vehículos en Argentina, integración entre canales.

- Página de status y de subprocessors públicas que comunican madurez.

**7.3.1 SEO sectorial**

El SEO se enfoca en términos del sector argentino: “CRM agencias de vehículos”, “gestión de leads concesionaria”, “integrar WhatsApp con portal sectorial”, “software para venta de autos usados Argentina”. La inversión es de mediano plazo: el SEO no produce resultados en el primer mes pero compone consistentemente. La política es publicar al menos dos artículos de calidad por mes durante el primer año.

**7.4 Canal: Eventos sectoriales**

Los eventos del sector automotor argentino —exposiciones, congresos de cámaras como ACARA, ferias regionales— son canales de alta calidad. La calidad del lead es alta porque la audiencia es del segmento; la conversión esperada es 10-15% awareness → interest, mucho mejor que la mayoría de canales online. Los costos varían: stand en evento grande puede ser USD 3000-8000 con costo de oportunidad significativo. La política operativa es seleccionar 2-3 eventos por año donde tener presencia diferenciada y priorizar charlas o ponencias antes que stand pasivo, por la visibilidad y credibilidad que aportan.

**7.5 Canal: Referidos**

El canal de referidos es el más rentable cuando hay base de clientes felices. Un referido tiene tasa de conversión muchas veces superior a un lead frío porque viene con confianza preinstalada. El programa formal de referidos se lanza junto con la transición de los early adopters a clientes regulares (mes 6 del primer cliente). La estructura es: el cliente que refiere obtiene 1 mes gratis cuando el referido firma y completa su primer mes de uso; el referido obtiene 1 mes gratis adicional al trial estándar. El tracking se hace con código de referencia único por cliente que se incluye en su panel de tenant.

**7.6 Canal: Partnerships sectoriales**

Los partnerships con actores del ecosistema son canales potentes pero requieren tiempo y trabajo de cierre. Los partnerships objetivo son los siguientes.

- El portal sectorial argentino (la integración propia que el producto ya tiene): el portal puede recomendar deRuedas a sus agencias clientes como herramienta de gestión que se integra con su plataforma.

- Cámaras del sector (ACARA y similares): convenios institucionales que ofrecen descuento a miembros y posicionamiento como proveedor recomendado.

- Estudios contables especializados en agencias: relaciones donde el contador recomienda deRuedas a sus clientes que enfrentan crecimiento o digitalización.

- Banks o proveedores de financiación prendaria: integraciones bidireccionales donde el flujo de leads va y viene.

- Marcas o concesionarias oficiales que tienen red de revendedores oficiales y necesitan dar a esos revendedores una herramienta de gestión común.

**7.7 Canal: Publicidad pagada**

La publicidad pagada en Meta (Facebook + Instagram) y Google Ads es canal complementario, no central. Su rol es acelerar volumen del top of funnel cuando el inbound orgánico aún es bajo, y refuerzo de campañas específicas (lanzamiento de feature, evento, oferta del programa de early adopters). La política es comenzar con presupuestos chicos (USD 500-1000 / mes) en la Ola 1 y escalar solo cuando los datos demuestren CAC razonable. El targeting es estricto: por intereses sectoriales y geografía argentina; los anuncios se diseñan con material del Brand Book y mensajes específicos del segmento.

**7.8 Atribución multitouch**

Un prospect típicamente toca múltiples canales antes de convertir: lee un artículo del blog, ve un anuncio en Instagram, recibe un email de outbound, finalmente hace clic. La atribución de un solo canal a la conversión simplifica la realidad y conduce a decisiones equivocadas. La política operativa es trackear el primer toque (qué canal abrió el conocimiento), el último toque (qué canal cerró la conversión), y los toques intermedios. La atribución equitativa entre todos los toques es más fiel pero más compleja; en Ola 1 se usa first-touch + last-touch como aproximación; en Ola 2 se introduce modelado más sofisticado.

**8. Ciclo de venta**

Esta sección detalla el proceso desde que un lead calificado llega al equipo comercial hasta que firma el contrato. La definición explícita del ciclo permite estimar tiempos, identificar bloqueos y entrenar a personas nuevas que se incorporen al equipo.

**8.1 Etapas del ciclo**

|  |  |  |
|:---|:---|:---|
| **Etapa** | **Tiempo típico** | **Actividad principal** |
| Calificación inicial (qualification) | 1-2 días | Confirmar que el lead está en el segmento, identificar persona principal de contacto, confirmar interés genuino vs curiosidad. |
| Discovery | 2-5 días | Entender la situación actual del prospect, sus dolores reales, sus criterios de éxito, su proceso de compra. |
| Demo | 1-3 días | Demostración personalizada al prospect con datos representativos de su contexto. Foco en sus dolores específicos, no en showcasing genérico de features. |
| Trial | 14 días | Período de prueba con seguimiento estructurado del equipo: día 3 check-in, día 7 mid-trial, día 12 conversación de cierre. |
| Propuesta y negociación | 3-7 días | Propuesta formal con plan recomendado, pricing efectivo, términos. Negociación de descuentos legítimos si los hay. |
| Cierre | 1-3 días | Firma del contrato, primer pago, comienzo del onboarding. |

**Tiempo total esperado:** El ciclo típico de un cliente Pro toma de 3 a 6 semanas desde primer contacto hasta firma. El ciclo Enterprise puede llegar a 8-12 semanas. Ciclos significativamente más cortos (cliente que firma en una semana) suelen indicar prospect ya muy convencido o decisión apresurada que no asume bien; ciclos más largos suelen indicar prospect que no terminará cerrando.

**8.2 Calificación: el filtro temprano**

La política operativa adopta calificación BANT modificada: Budget (¿tiene capacidad de pagar el plan correspondiente?), Authority (¿estamos hablando con quien decide?), Need (¿el dolor es real y articulable?), Timeline (¿tiene urgencia o es exploración indefinida?). Cuando uno de los cuatro elementos es NO claramente, el prospect se descalifica o se pone en seguimiento de mediano plazo, no se invierte tiempo en demos prematuras. El equipo comercial trackea las descalificaciones por razón para identificar patrones (¿el segmento real es distinto al planeado? ¿el pricing está mal calibrado?).

**8.3 Discovery: la conversación que más vale**

La conversación de discovery es donde el vendedor decide si el prospect califica para inversión y cómo será el resto del ciclo. Las preguntas guía son las siguientes y se hacen en formato conversacional, no checklist mecánico.

- “¿Cómo gestionan hoy el inventario y los leads?” — abre la situación actual con sus dolores.

- “¿Qué los llevó a buscar algo distinto en este momento?” — identifica el trigger event que activó la búsqueda.

- “¿Qué probaron antes y por qué no funcionó?” — entiende objeciones a futuro y evita repetir patrones fallidos.

- “¿Qué pasaría si esto no se resuelve?” — articula el costo del status quo y crea sentido de urgencia.

- “¿Cómo decidirían que la solución funcionó?” — define criterios de éxito que después se ajustan al onboarding.

- “¿Quiénes participan en la decisión?” — identifica decisores e influenciadores que el vendedor debe involucrar.

**8.4 La demo efectiva**

La demo es momento crítico del ciclo. La política privilegia demos personalizadas sobre demos genéricas. Antes de la demo, el vendedor confirma con el prospect dos o tres dolores específicos que el discovery reveló y prepara la demo para mostrar exactamente cómo el producto los resuelve. La estructura recomendada es la siguiente.

DEMO ESTRUCTURA (45 minutos)

0-5min Recap del discovery

· 'En la conversación anterior identificamos que

tu mayor dolor es X. Voy a mostrarte exactamente

cómo deRuedas resuelve eso.'

5-30min Demo guiada de los flujos relevantes

· Cargar un vehículo (5min)

· Recibir un mensaje de WhatsApp y crear lead (10min)

· Ver el pipeline y mover el lead (5min)

· Marcar venta y ver cómo el dashboard se actualiza (5min)

30-40min Preguntas y respuestas

· Espacio amplio para que el prospect indague

40-45min Próximos pasos

· 'Si querés probarlo en tu propia operación,

el siguiente paso es activar el trial. Te lleva

5 minutos. ¿Lo hacemos juntos ahora?'

**8.5 Manejo de objeciones frecuentes**

|  |  |
|:---|:---|
| **Objeción** | **Respuesta sugerida** |
| “Es muy caro” | Reframe a valor: “¿Cuánto te cuesta hoy un lead perdido en WhatsApp? Si recuperás dos por mes, deRuedas se paga sola.” Si la objeción persiste con datos, evaluar plan menor o descuento legítimo. |
| “Ya tengo Excel/HubSpot/lo que sea” | No criticar la herramienta actual. Reconocer su valor: “Excel funciona muchísimo, especialmente al principio. Lo que pasa es que cuando el negocio crece, deja de escalar. La pregunta es: ¿cuándo te conviene migrar?” |
| “Mis vendedores no van a adoptar” | Reconocer la preocupación legítima. Ofrecer plan de adopción concreto: capacitación remota, app móvil para vendedores, que el primer vendedor que lo use se vuelva campeón interno. Eventualmente ofrecer demo a los propios vendedores. |
| “Déjame pensarlo” | Buscar la objeción real detrás. “¿Qué necesitarías para tomar la decisión?”. A veces el prospect necesita consultar a alguien específico; conviene saberlo y proponer call con esa persona. |
| “Mi sobrino me hace algo a medida” | Honrar la lealtad familiar pero plantear costo total: tiempo de desarrollo, mantenimiento, evolución, riesgo de single-point-of-failure si el sobrino no sigue disponible. “deRuedas no compite con tu sobrino, le saca la presión.” |
| “Dejé que me lo presenten en seis meses” | Aceptar gracias y mantener relación. No insistir agresivamente. Mantener al prospect en cadencia de seguimiento de bajo costo (newsletter, contenido relevante, novedades de producto). |

**8.6 Trial: el período crítico**

El trial de 14 días es donde el producto se vende solo o se cae. La política operativa es seguimiento estructurado del trial, no abandono. El equipo comercial mantiene tres puntos de contacto: día 3 para check-in (“¿pudiste cargar tus primeros vehículos?”), día 7 para mid-trial (“¿qué viste hasta ahora? ¿Hay algo que te resulta confuso?”), día 12 para conversación de cierre (“Te queda menos de una semana del trial. ¿Hablamos de cómo seguir?”). Sin estos contactos, los trials terminan vencidos sin decisión y se pierden.

**8.7 Propuesta y cierre**

La propuesta formal se entrega tras el trial cuando el prospect manifestó interés en continuar. Es documento PDF estructurado con plan recomendado, pricing efectivo (incluyendo descuentos aplicables), términos contractuales clave, próximos pasos. La propuesta no es enviada por email y olvidada: el vendedor agenda call de revisión donde la lee con el prospect, atiende objeciones finales, propone fecha de firma. La política prohíbe propuestas verbales: si el prospect no recibe un documento formal, no hay base de cierre.

**9. Onboarding comercial**

Esta sección desarrolla el onboarding como proceso comercial que se diferencia y se complementa con el onboarding técnico (manual de usuario). El onboarding comercial es lo que asegura que el cliente que firmó efectivamente llega a uso productivo y a éxito en sus métricas; sin él, hay tenants que firman y nunca usan, lo que produce churn temprano disfrazado de “cliente activo” en el CRM mientras la realidad es desuso silencioso.

**9.1 Diferencia con onboarding técnico**

El onboarding técnico (cubierto por el manual de usuario que está pendiente como capa complementaria) responde a la pregunta “cómo se usa la app”. El onboarding comercial responde a la pregunta “cómo el tenant logra el resultado por el cual contrató”. Son distintos: el primero es operacional (qué botón apretar), el segundo es estratégico (qué workflow adoptar para resolver el dolor que motivó la compra). Ambos son necesarios pero ninguno reemplaza al otro.

**9.2 Plan de onboarding por plan contratado**

|  |  |
|:---|:---|
| **Plan** | **Plan de onboarding** |
| Starter | Self-service. El cliente recibe un correo con el plan de los primeros pasos, accede al manual de usuario, tiene soporte por email durante hábil. El equipo comercial no agenda sesiones individuales pero el customer success monitorea adopción y interviene si detecta tenant inactivo a 7 días. |
| Pro | Una sesión guiada de 60 minutos con customer success en la primera semana. La sesión cubre: configuración inicial del tenant, importación de datos del cliente, definición del pipeline de ventas, integración de WhatsApp Business, training rápido de los usuarios. Seguimiento estructurado durante los primeros 30 días. |
| Enterprise | Plan completo con kickoff de 90 minutos, hasta 3 sesiones de configuración avanzada, training específico para administrativos y para vendedores, definición de KPIs de éxito que el customer success trackea y reporta mensualmente. Customer success dedicado durante el primer trimestre. |

**9.3 Kickoff con el cliente**

El kickoff es la sesión que da el tono al onboarding. Su estructura recomendada cubre: presentación de las personas de cada lado (quién hace qué del lado del cliente, quién es el customer success de deRuedas), recordatorio de los criterios de éxito que se acordaron en la conversación de discovery o de venta, plan concreto de las próximas semanas con hitos específicos, intercambio de canales de contacto y expectativas de respuesta, primeros pasos a ejecutar inmediatamente después de la sesión. Un kickoff bien hecho deja al cliente con claridad y a deRuedas con compromiso explícito.

**9.4 Hitos de adopción**

La salud del onboarding se mide con hitos concretos que el cliente debe alcanzar en plazos definidos. Cuando un hito no se cumple, customer success interviene proactivamente para entender por qué y desbloquear.

|  |  |  |
|:---|:---|:---|
| **Hito** | **Plazo** | **Verificación** |
| Configuración del tenant completada | Día 3 | Sucursal cargada, usuarios creados, pipeline configurado. |
| Integración WhatsApp Business activa | Día 7 | Token verificado, primer mensaje recibido vía webhook. |
| Primer vehículo cargado | Día 7 | Stock con al menos 5 vehículos. |
| Primer lead creado | Día 14 | Lead en el sistema asociado a un contacto y a un vehículo. |
| Primer usuario distinto del manager activo | Día 14 | Vendedor o administrativa con login en últimos 7 días. |
| Primera operación cerrada (won o lost) | Día 30 | Lead movido a estado terminal. |
| Uso productivo establecido | Día 60 | Al menos 5 leads activos, todos los usuarios usan semanalmente, dashboard se consulta regularmente. |

**9.5 Indicadores de fricción temprana**

Customer success monitorea métricas que indican que un tenant está enfrentando fricción incluso si no se queja explícitamente. Las señales son las siguientes.

- Tenant que no completó la configuración inicial pasados 14 días: probablemente se confundió o lo abandonó.

- Solo el manager usa la app; los usuarios secundarios nunca loguearon: indica resistencia interna a la adopción.

- Cargaron datos pero no hay actividad transaccional (creación de leads, mensajes): probablemente no entendieron el flujo.

- Tickets de soporte sobre conceptos básicos pasado el primer mes: el onboarding no logró traspaso de conocimiento.

- Reducción de uso semana a semana en el primer trimestre: la novedad pasó y el valor no quedó claro.

**Política de intervención:** Cuando una señal aparece, customer success contacta proactivamente al cliente con propuesta concreta: una sesión de 30 minutos, un video tutorial específico, un cambio de configuración recomendado. La proactividad temprana evita que la fricción se vuelva churn.

**10. Retención y expansión**

Esta sección desarrolla las prácticas de retener clientes existentes y expandir su consumo. El SaaS B2B vertical depende crucialmente de retención: el costo de adquirir un cliente nuevo es múltiples veces el de mantener uno existente, y la rentabilidad real proviene del ciclo prolongado del cliente, no del primer cobro. Sin programa explícito de retención, el churn silencioso erosiona el negocio incluso cuando las métricas de adquisición se ven bien.

**10.1 Health score del cliente**

La retención se gestiona proactivamente en función del health score: una métrica compuesta que indica qué tan saludable está cada tenant. Un tenant con score alto está usando bien el producto y satisfecho; uno con score bajo está en riesgo aunque no se haya quejado todavía. La política operativa es revisar mensualmente la salud de toda la base y actuar sobre los tenants en riesgo antes de que se manifieste como cancelación.

|  |  |
|:---|:---|
| **Componente del health score** | **Cómo se mide** |
| Engagement de uso | Frecuencia de login, cantidad de usuarios activos vs licencias, días desde última operación significativa. |
| Adopción de features clave | Uso de WhatsApp integrado, publicación al portal, uso de pipeline customizado, uso de reportes. |
| Volumen relativo a su tamaño | Operaciones / vendedor / mes vs benchmarks por sub-segmento. |
| Soporte y feedback | Tickets cerrados con satisfacción, NPS reciente, sentiment del último contacto con customer success. |
| Salud comercial | Pagos al día, ausencia de disputas, indicadores de que el negocio del tenant funciona (no solo que paga la suscripción). |

**10.2 Programa de Customer Success**

Customer Success es función dedicada cuyo objetivo es que el cliente alcance el valor por el que contrató. Es distinto de soporte: soporte responde a preguntas reactivas; customer success conduce activamente al éxito del cliente. La estructura de actividades de customer success a lo largo del año del cliente es la siguiente.

|  |  |
|:---|:---|
| **Momento** | **Actividad** |
| Onboarding (mes 1-2) | Plan de onboarding según plan contratado (sección 9). |
| Adopción inicial (mes 3-4) | Check-in mensual de 30 min para revisar uso, identificar features no adoptadas, sugerir mejoras. |
| Quarterly Business Review (cada trimestre) | Para Pro y Enterprise: revisión de 60 min con métricas de uso, valor obtenido, plan para el siguiente trimestre. |
| Renovation prep (60 días antes) | Conversación previa a la renovación para asegurar que el cliente está satisfecho y abordar dudas o cambios de plan. |
| Detection de riesgo (continuo) | Monitoreo automático de health score; intervención proactiva cuando baja. |
| Expansion opportunity (continuo) | Identificación de tenants que crecen y podrían beneficiarse de upgrade de plan o features adicionales. |

**10.3 Triggers de expansión**

La expansión se gestiona con disciplina similar a la retención. Los triggers que indican oportunidad de expansión son los siguientes.

- El tenant alcanzó el límite de usuarios incluidos en su plan: oportunidad de expansion con usuarios extras o upgrade de plan.

- El tenant alcanzó el límite de vehículos: requiere upgrade obligatorio.

- El tenant excede mensajes de WhatsApp incluidos sistemáticamente: oportunidad de upgrade de plan o ajuste de cupo.

- El tenant abrió una segunda sucursal: oportunidad de expansion (especialmente si está en Starter o Pro).

- El tenant solicita features que están solo en Enterprise (API completa, SSO, DPA personalizado): oportunidad de upgrade.

- El tenant tiene engagement alto y crecimiento: candidato natural a upsell.

**10.4 Política de renovación**

La renovación se trata como nueva venta light: requiere conversación, no es automática. La política operativa es contactar al tenant 60 días antes del vencimiento del contrato (anual) o cada 6 meses (mensual). La conversación cubre: revisión del valor obtenido en el período, ajustes de plan si aplican, eventual aumento de pricing, firma de renovación. Cuando el tenant renueva, hay reconocimiento explícito (“gracias por seguir con nosotros otro año”); cuando no renueva, hay conversación de salida que captura aprendizaje sin presionar al cliente.

**10.5 Política frente al churn**

Cuando un tenant cancela, el procedimiento operativo es el siguiente. Conversación de salida con honestidad: por qué se va, qué falló, qué hubiera evitado el churn. Procesamiento de export y portabilidad de sus datos según política del Plan de Seguridad. Sin presión para retenerlo a último momento con descuentos: si la decisión está tomada, intentar retenerlo erosiona la marca. Documentación de la razón en CRM con análisis de patrones a nivel agregado. Posibilidad de regreso: la puerta queda abierta, y los tenants que se fueron y vuelven son señal positiva si se manejaron bien.

**Churn como información:** Un programa maduro de retención no busca churn cero, busca churn justificado y comprendido. El churn que ocurre por razones del cliente (cerró el negocio, lo compró otra empresa) es inevitable; el churn que ocurre por razones del producto (no funcionó, no se adoptó) es señal de mejora. La distinción entre los dos es la diferencia entre programa que mejora y programa que culpa al mercado.

**11. Métricas comerciales**

Esta sección consolida las métricas comerciales clave del programa. Las métricas se reportan en cadencias distintas según su volatilidad y sirven distintos propósitos: algunas son para gestión diaria del equipo comercial, otras para gestión mensual del negocio, otras para análisis estratégico trimestral.

**11.1 Métricas de revenue**

|  |  |  |
|:---|:---|:---|
| **Métrica** | **Cadencia** | **Definición y uso** |
| MRR (Monthly Recurring Revenue) | Mensual | Suma de las suscripciones mensualizadas vigentes. Métrica core del SaaS. |
| ARR (Annual Recurring Revenue) | Mensual | MRR x 12. Métrica de orientación inversora y de planificación a 12 meses. |
| New MRR | Mensual | MRR generado por nuevos contratos en el mes. |
| Expansion MRR | Mensual | MRR generado por upgrades, agregado de usuarios, expansión de tenants existentes. |
| Contraction MRR | Mensual | MRR perdido por downgrades de tenants existentes. |
| Churned MRR | Mensual | MRR perdido por cancelaciones. |
| Net New MRR | Mensual | New + Expansion - Contraction - Churned. Indicador de crecimiento real. |
| NRR (Net Revenue Retention) | Trimestral | (MRR de cohorte hace 12m + expansion - churn - contraction) / MRR original. Objetivo: \>100% es señal de SaaS saludable. |

**11.2 Métricas de adquisición**

|  |  |  |
|:---|:---|:---|
| **Métrica** | **Cadencia** | **Definición y uso** |
| CAC (Customer Acquisition Cost) | Mensual / trimestral | Inversión total comercial (salarios + marketing + tooling) / clientes nuevos cerrados. Objetivo: USD 250-600 según canal. |
| CAC payback period | Trimestral | CAC / MRR del cliente. Tiempo en meses para recuperar el costo de adquisición. Objetivo: \<6 meses en Pro, \<12 meses en Enterprise. |
| Conversión por etapa del funnel | Mensual | Ver sección 6.2. Diagnóstico de dónde se pierde el funnel. |
| Sales cycle length | Mensual | Días desde primer contacto a firma. Indicador de eficiencia del proceso. |
| Win rate (oportunidades cerradas) | Mensual | % de oportunidades calificadas que terminan en cliente. Objetivo: \>25%. |
| Pipeline coverage | Mensual | Oportunidades abiertas en pipeline / objetivo de cierre del mes. Objetivo: cobertura 3x del objetivo. |

**11.3 Métricas de retención y expansión**

|  |  |  |
|:---|:---|:---|
| **Métrica** | **Cadencia** | **Definición y uso** |
| Logo churn rate | Mensual | % de tenants que cancelan en el mes / base activa al inicio. Objetivo: \<3% mensual. |
| Revenue churn rate | Mensual | % del MRR que se pierde por cancelaciones / MRR al inicio del mes. |
| LTV (Lifetime Value) | Trimestral | ARPU mensual / churn rate. Valor estimado de un cliente a lo largo de su vida. |
| LTV / CAC ratio | Trimestral | Ratio entre LTV y CAC. Salud unitaria del negocio. Objetivo: ≥7. |
| NPS (Net Promoter Score) | Trimestral | Encuesta a tenants. Objetivo: \>40 en MVP; \>50 en operación madura. |
| Tasa de upsell | Trimestral | % de tenants que suben de plan o agregan usuarios en el período. |
| Tasa de referidos | Trimestral | % de tenants que recomendaron y generaron al menos un nuevo cliente. |

**11.4 Dashboards de métricas comerciales**

Las métricas se consolidan en tres dashboards con audiencias distintas. El dashboard semanal del equipo comercial muestra pipeline activo, oportunidades por etapa, actividades de cada vendedor, win rate del trimestre. El dashboard mensual de dirección muestra MRR, ARR, churn, CAC, LTV, salud por cohorte. El dashboard trimestral estratégico muestra tendencias de unit economics, salud del programa GTM, performance por canal de adquisición, evolución del NRR.

**11.5 Salud por cohorte**

La salud del producto se mide adicionalmente por cohortes: el comportamiento de los tenants que se sumaron en un mes específico a lo largo de los meses siguientes. La cohorte de enero a 12 meses, comparada con la cohorte de junio a 6 meses, muestra si el producto está mejorando, estable, o degradando. Las cohortes tempranas (early adopters) suelen tener mejor retención que cohortes posteriores (clientes regulares); cuando ocurre lo opuesto, el producto está madurando bien.

**12. Equipo comercial**

Esta sección define la estructura del equipo comercial: roles, responsabilidades, modelo de compensación y crecimiento del equipo en función de la madurez del programa. La estructura adoptada en MVP es liviana y se densifica progresivamente conforme el negocio crece y los datos justifican la inversión.

**12.1 Roles del equipo comercial**

|  |  |
|:---|:---|
| **Rol** | **Responsabilidad** |
| Founder / responsable comercial | En MVP, lidera el ciclo de venta personalmente para los primeros tenants. Cierra los Enterprise, supervisa los Pro, define estrategia. Transición a rol director conforme se contrata equipo. |
| Account Executive (AE) | Maneja el ciclo de venta desde calificación a cierre. Responsable de oportunidades en pipeline. Métricas: revenue cerrado, win rate, sales cycle length. |
| SDR / Inside Sales | Genera y califica leads, agenda demos para AEs. Foco en outbound y en seguimiento de leads inbound. Métricas: cantidad de demos agendadas, conversión Interest → Evaluation. |
| Customer Success Manager (CSM) | Onboarding y retención de tenants existentes. No factura ventas pero su éxito se mide en NRR y churn. Métricas: NPS, tasa de retención, tasa de expansión. |
| Marketing | Generación de demanda, contenido, web, eventos. Inicialmente función mixta con responsable comercial; rol dedicado en olas posteriores. |
| Channel Partner Manager | Gestión de partnerships sectoriales y referidos. Rol dedicado solo si los canales de partner se vuelven significativos. |

**12.2 Estructura por ola**

|  |  |
|:---|:---|
| **Ola** | **Equipo comercial** |
| Ola 0 (pre-MVP) | Solo founder/responsable comercial. Outbound personal a los primeros 12 prospects. |
| Ola 1 (primeros 12 tenants) | Founder + 1 customer success / agente de ventas híbrido. Foco en cerrar a los early adopters y darles éxito. |
| Ola 2 (escalado) | 1 AE dedicado + 1 SDR + 1 CSM. Foco en escalar adquisición y profesionalizar retención. |
| Ola 3 (consolidación) | 2 AEs (uno mid-market, uno enterprise) + 1-2 SDRs + 2 CSMs + 1 marketing dedicado. Especialización por sub-segmento. |

**12.3 Modelo de compensación**

La compensación del equipo comercial combina sueldo base con variable atado a métricas. La política operativa adopta esquemas conocidos del mercado argentino para SaaS B2B vertical, ajustándolos a la realidad de la organización.

|  |  |  |
|:---|:---|:---|
| **Rol** | **Mix base / variable** | **Métricas que disparan variable** |
| AE | 60% base / 40% variable | Quota de revenue cerrado. Aceleradores arriba de 100% del quota. |
| SDR | 70% base / 30% variable | Cantidad de demos calificadas que llegaron a evaluation. Bonus por demos que cierran. |
| CSM | 80% base / 20% variable | Tasa de retención de la cartera y NRR. Bonus por expansiones generadas. |
| Marketing | 90% base / 10% variable | Métricas de funnel top: leads calificados generados, costo por lead. |

**12.4 Quota y target**

La asignación de quota a roles comerciales se hace con disciplina: un quota realista pero exigente que la mayoría del equipo cumple en un trimestre saludable. Política operativa: el quota se ajusta cada 6 meses con datos reales del mercado y del producto. Los aceleradores arriba de 100% incentivan superar el quota sin recompensar exclusivamente a top performers extremos. La política prohíbe quotas inalcanzables que erosionan moral y favorecen rotación; cuando un AE cumple \<50% del quota durante dos trimestres seguidos sin causa justificada, se evalúa fit del rol.

**12.5 Cultura del equipo comercial**

La cultura del equipo comercial alinea con los principios del cuerpo SDD. Honestidad antes que cierre forzado: prefiero perder una venta que cerrarla con prospects que no van a tener éxito. Conocimiento profundo del producto: cada vendedor puede explicar técnicamente cómo funciona la integración con WhatsApp, cómo trabaja el aislamiento multi-tenant, cómo se maneja la privacidad. Trabajo en equipo: el revenue es del equipo, no individual; los AEs comparten leads cuando uno tiene cartera saturada. Aprendizaje sin culpa: postmortems de oportunidades perdidas para mejorar el proceso, no para asignar responsabilidades.

**13. Roadmap del programa GTM**

Esta sección declara la evolución prevista del programa comercial, alineada con las olas del plan de implementación general.

**13.1 Estado al cierre de Ola 0**

El programa GTM en Ola 0 tiene los siguientes elementos vigentes: estructura de tres planes definida con números cerrados; programa de early adopters formalizado con criterios y acuerdo escrito; web institucional con landing, pricing, FAQs, formulario de contacto; posicionamiento articulado con sub-segmentos identificados; buyer personas documentadas; ciclo de venta declarado con etapas y tiempos esperados; CRM básico configurado para trackear pipeline; pricing calculator disponible; primer responsable comercial activo (founder). Hay gaps reconocidos: no hay equipo comercial ampliado todavía; los canales de adquisición están incipientes; las métricas comerciales se trackean manualmente; los partnerships sectoriales son aspiracionales.

**13.2 Horizonte 0-6 meses (Ola 1)**

Foco: validar el motor comercial con los primeros 12 early adopters, cerrar los primeros casos de éxito, refinar el ciclo de venta con datos reales.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| 12 early adopters firmados y en producción | Programa formal completo, contratos firmados, tenants activos. |
| Primeros 3 casos de éxito documentados con autorización del cliente | Casos publicados en web; testimonios audiovisuales. |
| Ciclo de venta ajustado con datos reales | Tiempos por etapa medidos; tasas de conversión observadas; ajustes documentados. |
| CAC inicial medido | Cálculo concreto incluido en reportes mensuales. |
| Primer evento sectorial con presencia diferenciada | Charla, ponencia o stand en evento ACARA o similar. |
| Programa de referidos activado | Sistema de referencia codificable con tracking en CRM. |
| Primer convenio sectorial | Acuerdo formal con cámara, asociación o portal sectorial. |
| Webinar mensual sobre temas del sector | Calendario establecido, audiencia recurrente. |

**13.3 Horizonte 6-12 meses (Ola 2)**

Foco: escalar adquisición, profesionalizar el equipo, transitar de venta artesanal a venta repetible.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| 50-80 tenants activos pagando | Base instalada que permite economía de programa. |
| MRR de USD 8,000 a 15,000 | Métrica core de tracción. |
| Equipo comercial: AE + SDR + CSM dedicados | Roles cubiertos, no más founder solo. |
| Playbook de venta documentado | Procesos repetibles para vendedores nuevos. |
| 3+ canales de adquisición activos con métricas | Diversificación que reduce vulnerabilidad. |
| NPS medido sistemáticamente con respuesta a baja | Programa de feedback maduro. |
| Programa de referidos generando 10%+ del nuevo MRR | Canal de bajo costo establecido. |
| Primer cliente Enterprise multi-sucursal cerrado | Validación del segmento alto. |
| Atribución multitouch implementada | Decisiones de inversión informadas por datos. |

**13.4 Horizonte 12-24 meses (Ola 3)**

Foco: consolidación como líder de la categoría en Argentina, expansión a segmentos adyacentes, eventual expansión geográfica.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| 200+ tenants activos | Base que justifica programa maduro. |
| MRR de USD 35,000 a 60,000 | Operación rentable y autosostenible. |
| Equipo comercial de 6-8 personas | Especialización por rol y por segmento. |
| Programa de partnerships con 3+ alianzas activas generando \>15% de leads | Canal estructural establecido. |
| Expansion revenue \>25% del nuevo MRR | Indicador de SaaS saludable. |
| NPS sostenido \>50 | Producto querido por la base. |
| Primera expansión geográfica (Uruguay, Chile o México) | Validación de la propuesta más allá de Argentina. |
| Posicionamiento de líder en categoría documentado por terceros | Menciones en prensa sectorial, awards, rankings. |
| Marketing y producto colaborando en product-led growth | Features que generan leads (export con marca, viralidad de WhatsApp Business). |

**13.5 Madurez objetivo en 24 meses**

Al cierre de Ola 3 el programa GTM es ventaja competitiva consolidada. La organización tiene playbook reproducible que vendedores nuevos asimilan rápido. Las métricas de unit economics están en niveles que permiten escalar inversión comercial con retorno predecible. La marca tiene reconocimiento sectorial. El programa de partnerships genera ingresos sin proporcional inversión en outbound. La retención y expansión generan más MRR que la adquisición pura, lo que es señal madura del SaaS. Las decisiones comerciales se toman con datos, no con intuición.

**14. Anexos**

**14.1 Battle cards: deRuedas vs alternativas**

Estas battle cards son material de venta interno que el equipo comercial usa para preparar conversaciones donde el prospect compara con alternativas específicas. No son ataques al competidor sino articulación honesta de las diferencias.

**14.1.1 vs HubSpot CRM**

|  |  |
|:---|:---|
| **Aspecto** | **Posición de deRuedas** |
| Vertical sector | deRuedas es vertical específico; HubSpot es horizontal y exige adaptación significativa para vehículos. |
| WhatsApp | deRuedas tiene WhatsApp Business nativamente integrado; HubSpot requiere addons de terceros con costos adicionales. |
| Portal sectorial | deRuedas integra directamente; HubSpot no tiene integración nativa con el portal argentino. |
| Pricing por usuario | deRuedas tiene precio plano por plan con usuarios incluidos; HubSpot escala lineal con usuarios y se vuelve caro rápido. |
| Curva de aprendizaje | deRuedas se aprende en una mañana; HubSpot exige formación más extensa. |
| Soporte argentino | deRuedas tiene equipo en horario argentino; HubSpot soporta en inglés con horarios USA. |
| Customización | HubSpot tiene customización más profunda para procesos custom; deRuedas tiene customización suficiente para el sector. |

**14.1.2 vs Pipedrive**

|  |  |
|:---|:---|
| **Aspecto** | **Posición de deRuedas** |
| Pipeline visual | Ambos tienen pipeline visual potente; ventaja pareja. |
| Vertical sector | deRuedas habla del rubro; Pipedrive es genérico. |
| Mensajes | deRuedas integra WhatsApp; Pipedrive no nativamente. |
| Pricing | Pipedrive tiene plan más barato de entrada (USD 19) pero crece rápido con features y usuarios; deRuedas está más caro al inicio pero el costo total es competitivo en Pro. |
| Inventario | deRuedas modela vehículos como entidad central; Pipedrive trata productos como genéricos. |
| Reportes sectoriales | deRuedas tiene KPIs específicos del rubro; Pipedrive solo genéricos. |

**14.1.3 vs desarrollo a medida (Excel + algo)**

|  |  |
|:---|:---|
| **Aspecto** | **Posición de deRuedas** |
| Costo inicial percibido | Excel parece gratis; deRuedas tiene pricing visible. La conversación pivota a costo total. |
| Costo real total | Excel tiene costos ocultos: tiempo de mantenimiento, errores, datos perdidos, no escalabilidad. deRuedas reduce todos. |
| Mantenimiento | Excel depende del que lo armó (frecuentemente sobrino o vendedor que se va); deRuedas tiene equipo dedicado. |
| Seguridad | Excel suele estar en pendrive o email sin protección; deRuedas tiene programa formal de seguridad y compliance. |
| Escalabilidad | Excel funciona hasta cierto tamaño; pasado ese punto se vuelve insostenible. deRuedas escala. |
| Acceso multi-usuario | Excel concurrente es disfuncional; deRuedas multi-usuario es nativo. |

**14.2 Plantilla de propuesta comercial**

PROPUESTA COMERCIAL

deRuedas Gestión para \[Nombre de la agencia\]

Fecha: DD-MM-YYYY

1\. CONTEXTO

En la conversación de \[fecha\] identificamos que \[Nombre\]

busca resolver \[dolor 1\] y \[dolor 2\], y que el equipo

actual está compuesto por \[N\] vendedores con un stock

típico de \[N\] vehículos.

2\. PLAN RECOMENDADO

Plan: \[Pro / Enterprise\]

Justificación: \[por qué este plan y no otro\]

3\. INVERSIÓN

Suscripción mensual: USD XXX

Vendedores extra (si aplican): USD XX

Descuentos aplicables: \[si los hay\]

Total mensual estimado: USD XXX

Setup: sin costo

4\. ALCANCE DEL ONBOARDING

· \[Sesiones específicas según plan\]

· \[Plazos comprometidos\]

5\. SLA Y COMPROMISOS DE SERVICIO

· Disponibilidad: \[%\]

· Soporte: \[canales y horarios\]

· DPA y compliance: incluidos por defecto

6\. PRÓXIMOS PASOS

· Activación del trial / firma del contrato

· Kickoff de onboarding agendado para \[fecha\]

7\. VALIDEZ

Esta propuesta es válida durante 30 días.

Cualquier consulta, escribime directamente.

\[Nombre\]

deRuedas Gestión

**14.3 Glosario**

|  |  |
|:---|:---|
| **Término** | **Definición** |
| AE | Account Executive. Rol comercial responsable del ciclo de venta desde calificación hasta cierre. |
| ARR | Annual Recurring Revenue. Suma anualizada de las suscripciones recurrentes vigentes. |
| BANT | Marco de calificación de prospects: Budget, Authority, Need, Timeline. |
| Battle card | Material interno que articula las diferencias del producto vs competidores específicos para preparar conversaciones comerciales. |
| CAC | Customer Acquisition Cost. Inversión total comercial dividida por nuevos clientes cerrados. |
| Cohort | Grupo de tenants que se incorporaron en el mismo período, analizado a lo largo del tiempo. |
| Contraction MRR | MRR perdido por downgrades de clientes existentes (sin cancelación). |
| CRM | Customer Relationship Management. Software que el equipo comercial usa para trackear oportunidades y clientes. |
| CSM | Customer Success Manager. Rol que gestiona retención y expansión de la base de clientes. |
| Demo | Demostración del producto ante un prospect calificado, idealmente personalizada a sus dolores específicos. |
| Discovery | Conversación temprana del ciclo de venta donde se entienden los dolores y criterios del prospect. |
| Early adopter | Cliente temprano que adopta el producto cuando aún está madurando, a cambio de condiciones especiales. |
| Expansion MRR | MRR generado por upgrades, agregado de usuarios, o expansión de tenants existentes. |
| Funnel / embudo | Modelo del proceso desde awareness hasta conversion con sus etapas y tasas de conversión. |
| GTM | Go-To-Market. Estrategia y operación de cómo se vende el producto. |
| Inbound | Modelo de adquisición donde el prospect llega al producto (web, contenido, referencia). |
| Lead | Persona u organización que ha mostrado interés inicial en el producto. |
| Logo churn | Pérdida de clientes medida en cantidad (logos), independiente de su MRR. |
| LTV | Lifetime Value. Valor total estimado que un cliente aportará a lo largo de su vida como cliente. |
| MQL / SQL | Marketing Qualified Lead / Sales Qualified Lead. Etapas de calificación del lead. |
| MRR | Monthly Recurring Revenue. Suma mensual de las suscripciones recurrentes vigentes. |
| NPS | Net Promoter Score. Métrica de satisfacción y probabilidad de recomendación. |
| NRR | Net Revenue Retention. Indicador del SaaS que mide cómo evoluciona el revenue de una cohorte tras 12 meses. |
| Onboarding | Proceso de incorporar al cliente al producto, desde firma hasta uso productivo. |
| Outbound | Modelo de adquisición donde el equipo contacta proactivamente a prospects. |
| Pipeline | Conjunto de oportunidades comerciales en distintas etapas del ciclo de venta. |
| Quota | Objetivo asignado a un rol comercial, típicamente expresado como revenue cerrado. |
| Revenue churn | % del MRR que se pierde por cancelaciones. |
| SDR | Sales Development Representative. Rol comercial dedicado a generar y calificar leads para AEs. |
| Trial | Período de prueba gratuito del producto antes de la decisión de compra. |
| Upsell | Cliente existente que cambia a un plan superior. |
| Win rate | Porcentaje de oportunidades calificadas que terminan en cliente cerrado. |

**14.4 Control de versiones del documento**

|  |  |  |  |
|:---|:---|:---|:---|
| **Versión** | **Fecha** | **Autor** | **Cambios** |
| 1.0 | Mayo 2026 | Equipo comercial deRuedas | Versión inicial. Estructura de planes, programa early adopter, funnel, ciclo de venta, retención, equipo, métricas. |

La próxima revisión está prevista para noviembre de 2026 al cierre de la Ola 1, donde se actualizarán: pricing ajustado con datos del mercado argentino y de los primeros tenants, conversiones reales del funnel, ciclo de venta efectivamente medido, casos de éxito documentados, lessons learned del programa de early adopters, ajustes a roles y compensación según experiencia. La próxima revisión también incorporará la equivalencia de pricing en pesos argentinos al tipo de cambio vigente y eventuales ajustes de pricing por inflación local.
