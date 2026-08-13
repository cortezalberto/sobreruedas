**Spec-Driven Development**

**con asistencia de IA**

*Manual del proceso*

Una metodología de desarrollo guiada por especificación

para equipos que trabajan con agentes de IA

*Caso testigo: deRuedas Gestión · Marco conceptual N4*

Versión 1.0 — Mayo de 2026

**1. Introducción**

Este manual describe una metodología de desarrollo de software que llamamos Spec-Driven Development o SDD: el desarrollo guiado por especificación. Lo que la distingue de otras metodologías no es la especificación en sí —toda metodología produce alguna— sino la manera en que las especificaciones se organizan en capas con audiencia, granularidad y criterios de cierre diferentes, la trazabilidad explícita entre capas y, sobre todo, su pensamiento como andamiaje cognitivo para una colaboración productiva entre humanos y agentes de inteligencia artificial.

El manual surge de la práctica, no del laboratorio. Se destila de la aplicación del método al desarrollo de un producto SaaS real, deRuedas Gestión, cuyo cuerpo documental completo en seis capas se utiliza como caso testigo. Las decisiones que aquí se proponen y los formatos que se sugieren no son hipótesis: son lo que efectivamente funcionó en un proceso de desarrollo asistido por IA donde una persona humana dirigió la construcción de aproximadamente dieciocho mil párrafos de documentación, cinco mil páginas de Word equivalentes y doscientas tareas atómicas de implementación, con calidad sostenida y trazabilidad verificable.

**1.1 Audiencia del manual**

Este documento está pensado para tres audiencias que pueden tener uso simultáneo. Para profesionales de software que adoptan agentes de IA en su flujo de trabajo y buscan una metodología disciplinada para no perder control sobre el resultado, el manual propone un proceso reproducible. Para docentes universitarios y formadores que enseñan ingeniería de software en la era de los agentes generativos, ofrece un dispositivo curricular: las cinco capas pueden ser unidades didácticas, las decisiones del caso testigo pueden ser ejercicios, los anti-patrones pueden ser estudios de caso. Para investigadores en el cruce entre educación y desarrollo asistido por IA, el manual propone un marco conceptual —la trazabilidad cognitiva en cuatro niveles, que abreviamos N4— que permite estudiar empíricamente cómo se construye el conocimiento en estos procesos.

**1.2 Qué problema resuelve SDD**

La adopción de agentes de IA en el desarrollo de software produjo, en los primeros años, un fenómeno que la industria empezó a llamar vibe coding: programar conversacionalmente con un agente, aceptar lo que produce sin demasiada fricción, iterar rápido y entregar. La velocidad es real y el efecto inicial es deslumbrante. Pero a medida que los proyectos crecen aparecen tres problemas estructurales. El primero es la pérdida de coherencia: cada conversación con el agente recupera contexto local pero olvida decisiones tomadas en otro hilo, lo que produce contradicciones de arquitectura que solo se descubren tarde. El segundo es la opacidad de las decisiones: nadie puede explicar por qué tal módulo se diseñó así porque la decisión se tomó en una conversación que ya no existe. El tercero es la deuda epistémica: el equipo humano cree saber cómo funciona el sistema porque lo vio funcionar, pero su comprensión es superficial y se desploma cuando hay que modificar algo no trivial.

El SDD ataca los tres problemas con un mecanismo único: forzar al equipo —humano y agente— a externalizar el razonamiento en documentos antes de que se transforme en código. La especificación no es un subproducto del desarrollo: es el desarrollo. El código es la consecuencia. Esta inversión de prioridades parece costosa al principio (uno se pregunta si vale la pena escribir tanto antes de codear) pero pagiza cuando el sistema crece y especialmente cuando hay que cambiarlo. Una decisión documentada se puede revisar, criticar, refactorizar; una decisión que solo existe como bytes ejecutables solo se puede revertir con suerte.

**1.3 Qué no es SDD**

Para evitar confusión vale la pena enumerar lo que SDD no es. No es waterfall. Waterfall asume que las fases se completan secuencialmente y que los cambios entre fases son raros y caros; SDD asume que las capas se refinan iterativamente y que los cambios entre capas son frecuentes y baratos siempre que se hagan disciplinadamente. No es BDUF (Big Design Up Front). BDUF buscaba diseñar todo antes de codear; SDD busca diseñar cada capa antes de la inferior pero acepta que el conocimiento aumenta al implementar y que las capas superiores deben evolucionar.

Tampoco es la documentación posterior al código que muchos equipos ágiles producen como obligación. Esa documentación, escrita ex post, casi nunca refleja las decisiones reales: refleja la racionalización de lo que ya se hizo. SDD invierte la flecha temporal: la documentación es el insumo del código, no su residuo. Y no es la metodología tradicional de “especificación técnica” que muchas organizaciones aplican parcialmente: la diferencia es que SDD distingue capas con audiencia y granularidad propias, lo que evita el documento monolítico que termina siendo demasiado abstracto para los implementadores y demasiado técnico para los stakeholders.

**1.4 Estructura del manual**

El manual está organizado en once capítulos. El segundo capítulo desarrolla el marco conceptual: por qué SDD funciona desde la perspectiva cognitiva, qué es la trazabilidad N4 y cómo se relaciona con marcos de referencia académicos como Design-Based Research. El tercero presenta las cinco capas canónicas del proceso. El cuarto a octavo desarrolla cada capa en profundidad: motivación, audiencia, plantilla, criterios de cierre, ejemplos del caso testigo, errores comunes. El noveno trata las capas complementarias —seguridad, operaciones, testing, GTM— que extienden el cuerpo principal cuando el contexto lo amerita. El décimo aborda la práctica del proceso: cómo dirigir al agente de IA, cómo evaluar la calidad de cada capa, cómo gestionar versiones, qué herramientas funcionan. El décimo primero recoge anti-patrones y errores comunes observados, y discute la adaptación del método a contextos distintos al original. El glosario y la bibliografía cierran el documento.

**1.5 Convenciones del manual**

A lo largo del manual aparecen ejemplos extraídos del caso deRuedas Gestión. Se identifican como tales y se utilizan como ilustración concreta del concepto correspondiente. Las decisiones del caso son las que efectivamente se tomaron; los nombres y las cifras son los reales. Cuando una afirmación admite varias interpretaciones legítimas el manual lo señala y discute las alternativas en lugar de imponer una. Las recomendaciones se presentan sin imperativo cuando son opcionales y con imperativo cuando se consideran fundamentales del método.

**Sobre el lenguaje:** El manual está escrito en español rioplatense neutro, con preferencia por la prosa argumentativa antes que por listas y diagramas. Esa elección es deliberada y refleja una postura del método: el ejercicio de escribir argumentando es lo que produce la claridad de pensamiento que el método busca; las listas y los diagramas son útiles para resumir o visualizar, no para pensar.

**2. Marco conceptual: por qué SDD funciona**

Antes de presentar las capas y los formatos, este capítulo desarrolla por qué el método tiene sentido. La justificación tiene tres dimensiones: una cognitiva (cómo se forma el conocimiento del equipo), una operativa (cómo se mantiene la coherencia del producto en el tiempo) y una epistemológica (cómo se justifican las decisiones tomadas). Las tres dimensiones convergen en una intuición central: la documentación capa por capa no es un costo sino la condición de posibilidad de un desarrollo asistido por IA que sea técnicamente sólido y humanamente comprensible.

**2.1 La trazabilidad cognitiva en cuatro niveles (N4)**

El SDD adopta como marco conceptual la trazabilidad cognitiva en cuatro niveles, abreviada como N4. Es una progresión que describe los estadios por los que pasa la comprensión de un problema cuando se documenta sistemáticamente. Cada nivel responde a una pregunta distinta y produce un tipo distinto de documento. Los niveles son acumulativos: un nivel superior presupone los inferiores; saltearlos produce documentación que parece técnica pero no soporta cambios.

**2.1.1 Nivel N1 — Reconocimiento**

La pregunta de N1 es ¿qué hay? Es el reconocimiento del territorio: qué actores, qué procesos, qué dolor, qué oportunidades, qué restricciones. Es predominantemente descriptivo. La trampa de N1 es confundir reconocimiento con análisis: enumerar problemas no es entenderlos. La salida de N1 es un mapa del territorio, no una hipótesis sobre cómo intervenirlo. En el cuerpo SDD canónico el nivel N1 se materializa parcialmente en la capa de estrategia (mejoras y SaaS) y en el preámbulo de las historias de usuario.

**2.1.2 Nivel N2 — Comprensión**

La pregunta de N2 es ¿por qué? Es la búsqueda de relaciones causales y de principios subyacentes. Por qué este actor tiene este dolor; por qué esta solución no funcionó; por qué esta alternativa es preferible a aquella. N2 es predominantemente argumentativo. La trampa de N2 es la racionalización ex post: convertir una preferencia estética en una explicación causal. La salida de N2 es un conjunto de hipótesis explícitas sobre el comportamiento del sistema y de sus usuarios. En el cuerpo SDD se materializa en la constitución (los principios rectores) y en los ADRs (que justifican decisiones de arquitectura).

**2.1.3 Nivel N3 — Modelado**

La pregunta de N3 es ¿cómo se conecta? Es la construcción de modelos formales o semi-formales del dominio: entidades, relaciones, flujos, contratos, invariantes. N3 traduce las hipótesis de N2 en estructuras manipulables. La trampa de N3 es el modelaje desconectado de la realidad: construir abstracciones elegantes que no corresponden con problemas reales. La salida de N3 es un modelo del sistema con suficiente fidelidad para razonar sobre él sin recurrir al código. En el cuerpo SDD se materializa en la especificación técnica con sus dominios, contratos y diagramas.

**2.1.4 Nivel N4 — Operacionalización**

La pregunta de N4 es ¿qué hacer ahora? Es la traducción del modelo en acciones concretas, ejecutables, verificables, ordenadas. N4 cierra el ciclo: convierte el conocimiento en intervención. La trampa de N4 es la microgestión: degradar a esa capa decisiones que pertenecen a niveles superiores y enredarse en detalles operativos perdiendo la dirección. La salida de N4 es un plan de acción con tareas atómicas, criterios de aceptación, dependencias explícitas. En el cuerpo SDD se materializa en el plan de implementación con sus tareas atómicas.

**2.2 La progresión N1 → N4 como dispositivo cognitivo**

La idea fundamental es que la progresión de N1 a N4 no es solo un orden expositivo: es un orden cognitivo. Saltar de N1 a N4 (del reconocimiento del problema a la lista de tareas) sin pasar por N2 y N3 produce un plan que parece operativo pero no se sostiene cuando aparecen las primeras dificultades, porque no hay marco conceptual que permita decidir cómo adaptarlo. Saltar de N2 a N4 sin construir N3 produce decisiones bien argumentadas pero implementación caótica, porque la traducción de los principios a las estructuras concretas se hace ad hoc. La disciplina del SDD es resistir la tentación de saltar niveles incluso cuando la velocidad inicial sería mayor.

**Origen del marco N4:** El marco N4 se desarrolló originalmente en el contexto de la educación universitaria en programación, donde se buscaba una manera de evaluar no solo el resultado producido por el estudiante (el código) sino el proceso cognitivo que lo construyó. Aplicado al desarrollo profesional asistido por IA, el marco mantiene su utilidad: permite distinguir un equipo que entiende lo que está construyendo de uno que solo está iterando con el agente.

**2.3 SDD como andamiaje cognitivo para el agente de IA**

Un agente de IA contemporáneo, en su uso de programación, opera con una ventana de contexto limitada y sin memoria persistente entre conversaciones. Esto significa que cada vez que se le pide colaborar en una tarea, lo que sabe del proyecto es lo que el operador humano le entregó como contexto en ese turno. Si el operador entrega únicamente la pregunta inmediata (“armame este endpoint”), el agente responde sin contexto; lo que produce es plausible pero no necesariamente coherente con el resto del sistema. Si el operador entrega también la documentación relevante de capas superiores (la constitución, los principios rectores, la especificación del dominio afectado), el agente responde con contexto y la coherencia del resultado mejora dramáticamente.

La función de las capas SDD desde esta perspectiva es triple. Primero, sirven como contexto de alta densidad: dan al agente más información útil por token que cualquier dump de código. Segundo, sirven como fuente de verdad: cuando el agente y el operador disienten sobre cómo debería hacerse algo, la documentación arbitra. Tercero, sirven como restricción productiva: forzar al agente a justificar lo que produce contra el documento elimina muchas alucinaciones que aparecerían en una conversación sin ancla.

**2.4 La inversión de la flecha temporal**

En el desarrollo tradicional, la documentación se escribe después: después de tener el código, después de tener el producto funcionando, idealmente antes del onboarding del próximo desarrollador pero realmente cuando alguien la pide. En SDD la documentación se escribe antes y el código es la consecuencia. Esta inversión tiene una propiedad interesante: la documentación, escrita antes, refleja decisiones que aún no fueron contaminadas por las contingencias de la implementación. Es la decisión en su forma más pura. Cuando la implementación expone que la decisión era equivocada, lo correcto no es ajustar la documentación silenciosamente sino producir una decisión nueva, fechada, justificada y trazable.

La inversión también tiene un costo. Escribir antes obliga a tomar decisiones con menos información que la que se tendrá durante la implementación. Algunas de esas decisiones serán incorrectas. El método contempla esto explícitamente: las capas superiores no son inmutables, sino que pueden refactorizarse cuando aparece nueva información. Lo que el método prohíbe es fingir retrospectivamente que la nueva decisión siempre estuvo ahí: cada cambio queda registrado y trazable.

**2.5 Conexión con marcos de referencia académicos**

Para los lectores con contexto académico, vale la pena explicitar las conexiones del SDD con marcos de referencia establecidos. Hay tres particularmente productivas.

**2.5.1 Design-Based Research (DBR)**

DBR es una metodología de investigación educativa que se mueve entre el diseño de intervenciones y la teorización a partir de su implementación. La estructura del SDD —capas que van de lo conceptual a lo operativo, con retroalimentación entre capas— tiene afinidad estructural con los ciclos de DBR. Aplicado a un proyecto de software como deRuedas, el SDD permite que el desarrollo del producto sea simultáneamente un caso de estudio para investigación: cada decisión documentada es un dato; las refactorizaciones entre capas son evidencia del aprendizaje. Esta es la razón por la que el SDD encaja bien con proyectos de investigación universitaria que toman como objeto el propio proceso de desarrollo.

**2.5.2 Architecture Decision Records (ADRs)**

Los ADRs (popularizados por Michael Nygard en 2011) son una práctica de documentación de decisiones arquitectónicas que el SDD incorpora directamente en su capa N3. La diferencia es que en SDD los ADRs no flotan sueltos sino que se anclan a una constitución (capa de N2) que les da marco. Una decisión que viola un principio de la constitución requiere o bien justificación específica de la excepción o bien revisión de la constitución; no puede coexistir silenciosamente.

**2.5.3 Marco CONEAU para evaluación universitaria**

La estructura del SDD —con sus capas, sus criterios de cierre y su trazabilidad explícita— es compatible con los criterios de evaluación que la Comisión Nacional de Evaluación y Acreditación Universitaria utiliza para tesis de posgrado y carreras. Esto significa que un proyecto desarrollado con SDD genera, como subproducto natural, evidencia académica acreditable: dictámenes, planes, especificaciones, cronogramas, todos en formatos profesionales y trazables. Para docentes universitarios que dirigen tesistas en proyectos de software, el SDD ofrece un marco que cumple simultáneamente las exigencias profesionales y las académicas.

**2.6 Limitaciones del método**

Para ser honestos sobre el método, vale la pena enumerar sus limitaciones conocidas. La primera es que SDD requiere un compromiso temporal frontal: las primeras semanas de un proyecto se dedican a construir capas que aún no producen valor visible para el cliente. Equipos con presión extrema de tiempo en sprint cero pueden percibir esto como obstáculo, aunque la inversión recupera con creces cuando el proyecto crece. La segunda es que SDD funciona mejor con uno o pocos directores intelectuales del proyecto y agentes de IA como asistentes; en equipos grandes con múltiples voces igualmente autorizadas se requieren mecanismos adicionales de gobernanza para mantener la coherencia entre capas. La tercera es que SDD es más útil en proyectos con cierta complejidad: para un script de 200 líneas el overhead documental no compensa. La cuarta es que SDD presupone que el operador humano puede pensar a niveles N2 y N3; si el operador es novato y el agente de IA es lo único que provee razonamiento conceptual, el método degrada porque la dirección se pierde.

**Postura del manual frente a las limitaciones:** El método no se vende como universal. Las limitaciones se documentan explícitamente para que cada equipo decida si su contexto justifica adoptarlo. Los criterios de adopción se discuten en el capítulo 11.

**3. Las cinco capas canónicas del SDD**

El cuerpo principal de un proceso SDD se compone de cinco capas que se nombran y numeran de manera estable: estrategia, historias, constitución, especificación técnica y plan de implementación. Cada capa tiene una función específica, una audiencia primaria, un nivel de granularidad propio y criterios de cierre verificables. Las cinco capas conforman el cuerpo mínimo del SDD: si falta alguna, el método no se aplica plenamente. Existen además capas complementarias (seguridad, operaciones, GTM, manual de usuario) que se desarrollan en el capítulo 9 cuando el contexto lo amerita.

**3.1 Vista general de las capas**

|  |  |  |  |
|:---|:---|:---|:---|
| **Capa** | **Pregunta que responde** | **Nivel N4** | **Audiencia primaria** |
| 1\. Estrategia | ¿Qué hacer y por qué? | N1 + N2 inicial | Dirección, inversores, el equipo en su totalidad |
| 2\. Historias | ¿Qué necesitan los usuarios? | N1 detallado | Producto, equipo, validación con usuarios |
| 3\. Constitución | ¿Cuáles son los principios irrenunciables? | N2 | Equipo técnico y producto |
| 4\. Especificación técnica | ¿Cómo se estructura el sistema? | N3 | Equipo técnico, agente de IA |
| 5\. Plan de implementación | ¿Qué hacer la próxima semana, en qué orden? | N4 | Equipo de desarrollo, agente de IA |

**3.2 Por qué exactamente cinco capas**

La elección de cinco capas no es arbitraria pero tampoco es la única posible. Se llegó a ella por descomposición progresiva del problema: una capa estratégica era claramente necesaria; una capa puramente técnica también; entre ambas hacía falta algo que tradujera la estrategia en demanda concreta —las historias— y algo que estableciera principios antes de la especificación detallada —la constitución; debajo de la especificación técnica era necesaria una capa operativa —el plan de implementación— porque sin ella la especificación técnica no llegaba al código. Cinco capas resultaron suficientes para cubrir el espectro y pocas para ser memorables.

Equipos que adopten el método pueden experimentar con composiciones distintas. Algunas variantes razonables: fusionar estrategia e historias en proyectos donde el alcance es claro y conocido; agregar una capa de “diseño de experiencia” entre historias y constitución cuando la dimensión UX es central; subdividir la especificación técnica en dominio funcional y arquitectura técnica cuando el sistema es grande. La recomendación del manual es no experimentar con la composición hasta haber aplicado al menos una vez la versión canónica.

**3.3 Diagrama del flujo entre capas**

┌─────────────────────────┐

│ Realidad / Mercado │

│ Usuarios / Negocio │

└────────────┬────────────┘

│ insumos

▼

┌────────────────────────────┐

Capa 1 → │ ESTRATEGIA │ N1 + N2

│ (visión, mercado, plan) │

└────────────┬───────────────┘

│ baja a

▼

┌────────────────────────────┐

Capa 2 → │ HISTORIAS │ N1 detallado

│ (épicas + user stories) │

└────────────┬───────────────┘

│ informa

▼

┌────────────────────────────┐

Capa 3 → │ CONSTITUCIÓN │ N2

│ (principios irrenunciables)│

└────────────┬───────────────┘

│ enmarca

▼

┌────────────────────────────┐

Capa 4 → │ ESPECIFICACIÓN TÉCNICA │ N3

│ (dominios + ADRs + APIs) │

└────────────┬───────────────┘

│ se concreta en

▼

┌────────────────────────────┐

Capa 5 → │ PLAN DE IMPLEMENTACIÓN │ N4

│ (tareas atómicas con DoD)│

└────────────┬───────────────┘

│

▼

┌────────────────┐

│ CÓDIGO │

│ (consecuencia)│

└────────────────┘

⇕ retroalimentación entre capas: una decisión más abajo

puede invalidar una capa superior y obligar a refactorizarla

**3.4 La trazabilidad ascendente y descendente**

Las capas no solo se leen de arriba hacia abajo. Se leen también de abajo hacia arriba: una tarea del plan de implementación debe poder remontarse a un fragmento de la especificación técnica, que se remonta a un principio de la constitución, que se remonta a una historia, que se remonta a un objetivo estratégico. La trazabilidad bidireccional es la propiedad que vuelve auditable al cuerpo SDD.

Esta trazabilidad se materializa en anclajes explícitos. Una tarea del plan menciona la sección de la spec técnica que la motiva (“T-014 implementa el control C2.1 de RBAC, sección 8.4 de la spec técnica, que cumple el principio P3 de la constitución, derivado de la historia E2-H4”). Un ADR menciona los principios que respeta o las excepciones que justifica. Una historia menciona el objetivo estratégico que persigue. Las referencias bidireccionales no son adornos: son lo que permite que un cambio en cualquier capa se propague disciplinadamente al resto.

**3.5 Criterios de cierre por capa**

Cada capa tiene criterios de cierre que indican cuándo es suficiente para pasar a la siguiente. Los criterios no son tiempo gastado ni cantidad de páginas: son propiedades verificables del documento. Los criterios canónicos son los siguientes.

|  |  |
|:---|:---|
| **Capa** | **Criterio de cierre** |
| Estrategia | Existe una hipótesis articulada sobre quién es el usuario, qué dolor tiene, por qué la solución propuesta resuelve ese dolor, cómo se gana dinero y cuáles son los riesgos. Una persona no involucrada puede leer el documento y reproducir la lógica de negocio. |
| Historias | Toda función del producto a construir tiene al menos una historia que la motiva. Cada historia tiene actor, motivación, criterios de aceptación verificables. Las historias están agrupadas en épicas con relaciones explícitas. No hay historias huérfanas (sin épica) ni épicas sin historias. |
| Constitución | Los principios cubren las dimensiones críticas del producto (usuarios, datos, evolución, calidad, gobernanza). Cada principio tiene formulación accionable, no abstracción vacía. Hay artículos de gobernanza que indican cómo se modifica la constitución y cómo se resuelven conflictos entre principios. |
| Especificación técnica | El sistema está descompuesto en dominios con responsabilidades claras. Hay contratos de API o de evento donde corresponde. Los ADRs cubren las decisiones arquitectónicas no obvias con sus alternativas y razones de rechazo. Una persona técnicamente competente puede implementar el sistema con la spec sola. |
| Plan de implementación | Las tareas están en granularidad atómica (idealmente 4 a 16 horas cada una). Cada tarea tiene definition of done. Las dependencias entre tareas están explícitas. El plan está organizado en olas o sprints con criterios de entrega por ola. |

**3.6 La ola como unidad temporal del plan**

El plan de implementación adopta como unidad temporal la ola, no el sprint. La diferencia es semántica pero importante. Un sprint es una caja de tiempo fija (típicamente dos semanas) donde se completan las tareas que entren. Una ola es un conjunto de tareas que produce un incremento coherente y entregable del producto, con duración variable según las tareas que la compongan. La ola privilegia la coherencia del entregable sobre el tiempo; el sprint privilegia el tiempo sobre la coherencia. Para SDD, donde el agente de IA puede acelerar significativamente algunas tareas, la ola encaja mejor: el plan no se diseña asumiendo velocidad humana constante, sino con criterios de entregable que el equipo cumple en menos tiempo cuando el agente colabora bien.

**Caso testigo:** El plan de implementación de deRuedas está organizado en cuatro olas: Ola 0 (cimientos técnicos: auth, RLS, audit, primeras entidades de dominio), Ola 1 (MVP funcional: catálogo, leads, conversaciones, primer flujo end-to-end), Ola 2 (producto vendible: búsqueda avanzada, reportes, pricing, billing), Ola 3 (escala: optimizaciones, certificaciones, programa de bug bounty). Las olas coinciden con momentos comerciales naturales (firma del primer contrato al cierre de Ola 1, etc.).

**4. Capa 1 — Estrategia**

**Capa 1 Estrategia y visión del producto**

**Pregunta:** ¿Qué construir y por qué? ¿Para quién? ¿Cómo gana dinero?

**Nivel N4:** N1 (reconocimiento) + N2 inicial (comprensión)

**Audiencia:** Dirección, inversores, equipo completo, validadores externos

**Granularidad:** Alta (visión, mercado, hipótesis), no detalle de funcionalidades

**4.1 Función de la capa**

La capa de estrategia es la más alta del cuerpo SDD y la que enmarca todo lo demás. Su función no es decir cómo se construye el producto sino justificar por qué existe, qué problema resuelve, para quién y bajo qué supuestos. Una capa estratégica bien construida produce dos cosas: una hipótesis articulada de negocio que el equipo puede defender ante un externo y un conjunto de prioridades que se transmiten hacia abajo dictando qué historias importan más, qué principios se eligen y qué tareas van primero.

La trampa común al escribir estrategia es la abstracción aspiracional: enunciar visiones bonitas pero no falsables. Una buena estrategia es una hipótesis que admite ser refutada por el mercado. Si el documento estratégico se podría reescribir cambiando el nombre del producto y aún sería verdadero, no es estrategia: es marketing.

**4.2 Plantilla recomendada**

La estructura recomendada para el documento estratégico tiene siete secciones.

|  |  |
|:---|:---|
| **Sección** | **Contenido esperado** |
| Diagnóstico del estado actual | Qué se observa hoy en el dominio elegido. Quiénes son los actores, cómo trabajan, qué funciona, qué no. Predominantemente descriptivo. |
| Tesis del producto | La hipótesis articulada: qué oportunidad existe, por qué nadie la cubre adecuadamente, qué se va a construir, qué cambia para los actores afectados. |
| Segmento objetivo y propuesta de valor | Quién es el usuario primario, cómo se diferencia de otros segmentos cercanos, qué valor recibe específicamente. |
| Modelo de monetización y unit economics | Cómo se cobra, cuánto, qué costos hay por unidad de servicio, qué margen, qué se necesita para ser sostenible. |
| Hipótesis y supuestos críticos | Cuáles son los supuestos sobre los que se apoya la tesis. Cuáles, si fueran falsos, invalidarían el producto. Cómo se planea validarlos. |
| Riesgos y mitigaciones | Riesgos de mercado, técnicos, regulatorios, competitivos. Para cada uno, plan de mitigación o contingencia. |
| Roadmap estratégico de alto nivel | No el plan técnico (capa 5) sino los grandes hitos de negocio: cuándo se valida la hipótesis, cuándo se cobra el primer cliente, cuándo se busca financiamiento, etc. |

**4.3 Criterios de cierre**

La capa estratégica está cerrada cuando se cumplen tres condiciones simultáneas. Primero, una persona no involucrada puede leer el documento y reproducir la lógica de negocio en sus propias palabras: si el lector externo necesita preguntar cosas básicas (“pero entonces ¿quién paga?”, “¿por qué este segmento?”), el documento todavía no está completo. Segundo, las hipótesis críticas están enunciadas como falsables: cada una puede formularse como una predicción que la realidad puede confirmar o refutar. Tercero, hay coherencia interna: las decisiones de segmento son consistentes con las de monetización, los riesgos identificados son reales para el segmento elegido, el roadmap respeta las dependencias entre hitos.

**4.4 Errores comunes**

- Visión aspiracional sin hipótesis: “Cambiar el mundo del transporte” sin decir cómo, para quién, cuándo.

- Mercado total inflado para impresionar: el TAM citado de fuentes prestigiosas pero sin razonamiento sobre qué porción es accesible y por qué.

- Confusión entre producto y empresa: estrategia enfocada en la organización (cómo se va a contratar, cuándo se va a salir a bolsa) en lugar del producto.

- Ausencia de competidores: enumerar 'no hay competencia' es casi siempre falso o un signo de que el segmento no es viable.

- Riesgos genéricos: “riesgo de mercado”, “riesgo regulatorio” sin especificar cuáles son los escenarios concretos.

**Caso testigo:** El documento estratégico de deRuedas Gestión articula la hipótesis de que las agencias de vehículos argentinas medianas tienen una mezcla específica de necesidades CRM (multi-canal por WhatsApp, integración con el portal sectorial) que las soluciones generalistas no cubren bien y para la que pagarían un SaaS vertical. Las hipótesis críticas (que el dolor exista al nivel articulado, que la disposición a pagar alcance el ticket modelado, que el portal sectorial sea integrable) se enuncian explícitamente y se plantea cómo se validarían en la Ola 1.

**5. Capa 2 — Historias y épicas**

**Capa 2 Historias de usuario y épicas**

**Pregunta:** ¿Qué necesitan exactamente los usuarios? ¿En qué situaciones?

**Nivel N4:** N1 detallado (reconocimiento profundizado del comportamiento esperado)

**Audiencia:** Producto, equipo de desarrollo, validadores con usuarios reales

**Granularidad:** Cada historia describe un comportamiento concreto verificable

**5.1 Función de la capa**

Las historias traducen la estrategia abstracta en demanda concreta del producto. Su función es responder a la pregunta “qué tiene que poder hacer esto” con suficiente especificidad para que el equipo técnico no tenga que interpretar. La capa de historias es donde el producto deja de ser una abstracción y empieza a ser un artefacto. Una buena historia describe un actor (quién), una motivación (para qué) y un comportamiento esperado (qué pasa). Las tres dimensiones son necesarias: una historia sin actor es genérica, una historia sin motivación es arbitraria, una historia sin comportamiento esperado es teoría.

La trampa habitual es escribir historias que en realidad son tareas técnicas (“Como desarrollador, quiero un endpoint que devuelva los usuarios”). Esa formulación pertenece a la capa 5 del plan, no a la capa 2 de historias. Una historia auténtica habla del usuario del producto, no del implementador del producto.

**5.2 Estructura de una historia**

La estructura recomendada usa la fórmula clásica de Mike Cohn extendida con criterios de aceptación verificables.

ID: E2-H4

Título: Marcar lead como ganado y registrar venta

Como vendedor de la agencia,

quiero marcar un lead como ganado e indicar el vehículo vendido

para que el inventario refleje la operación y el dashboard mensual

incluya esta venta automáticamente.

Criterios de aceptación:

· Al marcar como ganado, el sistema pide vehículo del catálogo.

· El vehículo seleccionado pasa a estado "vendido" con timestamp.

· Se registra el monto final, opcional las observaciones.

· El dashboard del mes en curso refleja la venta dentro de 1 min.

· La operación queda en audit_logs con datos forenses completos.

· Si el vehículo ya estaba vendido, el sistema rechaza la operación

con mensaje claro y sugiere consultar al manager.

Anclajes:

· Épica: E2 - Gestión de leads y conversiones

· Objetivo estratégico: O3 (cierre asistido del ciclo de venta)

· Principios constitucionales: P3 (auditabilidad), P5 (consistencia)

**5.3 La épica como agrupador**

Las historias se agrupan en épicas que representan áreas funcionales coherentes. La épica no es solo etiqueta de categoría: es una unidad de planificación que se puede priorizar, validar y refinar. Una épica típica tiene entre cinco y quince historias, una hipótesis explícita sobre qué problema resuelve y un criterio de cierre como conjunto (“la épica está completa cuando un usuario puede ejecutar end-to-end el flujo de gestión de leads”).

**Caso testigo:** El cuerpo de historias de deRuedas Gestión tiene 92 historias agrupadas en 12 épicas: catálogo de vehículos, gestión de leads, conversaciones por WhatsApp, dashboard y reportes, configuración del tenant, autenticación y usuarios, integraciones externas, búsqueda y filtros, gestión documental, evaluación, exportes y APIs públicas, y administración multi-tenant. Cada épica tiene su criterio de cierre y su conexión a uno o más objetivos estratégicos.

**5.4 Criterios de cierre**

La capa de historias está cerrada cuando se cumplen tres condiciones. Primero, toda funcionalidad relevante del producto a construir tiene al menos una historia que la motiva: si una funcionalidad aparecerá en el plan de implementación pero no en historias, hay una incoherencia que detectar. Segundo, las historias tienen criterios de aceptación verificables: el criterio se puede convertir en test sin ambigüedad. Tercero, las épicas tienen relaciones explícitas con los objetivos estratégicos: ninguna épica está huérfana de la capa 1, lo cual significaría que no hay justificación de por qué se construye.

**5.5 Errores comunes**

- Historias técnicas: “Como backend, quiero un endpoint REST...” — pertenecen a la capa 5.

- Historias sin criterios de aceptación: el implementador deduce, malinterpreta, produce algo que no era.

- Granularidad inconsistente: algunas historias son enormes (“gestionar todo el ciclo de venta”), otras son micro (“que el botón sea azul”).

- Historias duplicadas en distintas épicas: el mismo comportamiento aparece referenciado dos veces con redacciones distintas.

- Épicas que son simplemente categorías técnicas (“Microservicio de pagos”) en lugar de áreas funcionales para el usuario.

**6. Capa 3 — Constitución**

**Capa 3 Principios rectores y artículos de gobernanza**

**Pregunta:** ¿Cuáles son los principios irrenunciables del producto? ¿Cómo se decide cuando hay conflicto?

**Nivel N4:** N2 (comprensión profunda, hipótesis explicativas)

**Audiencia:** Equipo técnico, equipo de producto, agente de IA

**Granularidad:** Principios de alto nivel, generalmente entre 5 y 10

**6.1 Función de la capa**

La constitución es la capa que más diferencia al SDD de otras metodologías. Su función es establecer los principios que el producto va a respetar incluso cuando sea inconveniente respetarlos. Es lo que el equipo se compromete a no transigir bajo presión de tiempo, presión comercial o tentación de elegancia técnica. Sin constitución, las decisiones se toman caso por caso y la coherencia del producto se erosiona; con constitución, cada decisión técnica posterior se valida contra principios estables.

La paradoja de la constitución es que su valor se manifiesta cuando aparece la presión para violarla. Una constitución que nunca se invoca probablemente sea innecesaria; una constitución que constantemente se invoca para bloquear decisiones tentadoras está cumpliendo su función. La práctica del método incluye que cuando surge la propuesta de violar un principio, el equipo se obliga a ofrecer una de tres respuestas: aceptar el principio (descartar la propuesta), justificar la excepción específica (con argumentos verificables), o modificar el principio (con cambio constitucional explícito y fechado).

**6.2 Anatomía de un principio**

Un principio bien formulado tiene tres componentes: el enunciado (formulación accionable, no aspiración), la justificación (por qué se eligió, qué valor protege) y la implicancia operativa (qué cosas concretas impone o prohíbe). Sin los tres, el principio se degrada a slogan.

PRINCIPIO P3 — Auditabilidad de operaciones sensibles

Enunciado:

Toda operación que afecte datos del tenant, configuración, secretos

o identidades privilegiadas deja huella en una bitácora append-only

que registra qué se hizo, quién lo hizo, cuándo, desde dónde y qué

cambió.

Justificación:

El producto trata datos comerciales sensibles de las agencias y datos

personales de sus contactos. Sin auditabilidad no hay manera de

investigar incidentes, atender derechos de titulares ni cumplir con

obligaciones legales. La auditabilidad es además requisito común de

infosec questionnaires de clientes medianos en adelante.

Implicancias operativas:

· Cualquier endpoint que modifique recursos del tenant debe tener

decorador @audit_action.

· La tabla audit_logs tiene UPDATE/DELETE revocados al rol app.

· La auditoría no es feature opcional: es invariante del producto.

· Excepción permitida: operaciones idempotentes de solo lectura no

requieren auditoría unitaria pero sí auditoría agregada por sesión.

Excepciones registradas:

· Health checks (no auditables individualmente)

· Métricas internas (audit agregado a través de Prometheus)

**6.3 Artículos de gobernanza**

Además de los principios, la constitución incluye artículos de gobernanza que definen cómo se modifica la propia constitución, cómo se resuelven conflictos entre principios y quién tiene autoridad para qué. Sin gobernanza explícita, la constitución se vuelve folklore: principios que todos citan pero que nadie sabe cómo cambiar cuando deben cambiar.

Los artículos típicos son los siguientes. El artículo de modificación define qué proceso requiere un cambio constitucional (típicamente: propuesta escrita, discusión documentada, aprobación con quórum). El artículo de jerarquía define qué hacer cuando dos principios entran en conflicto (típicamente con criterio de precedencia explícito). El artículo de excepciones define cómo se documenta y aprueba una excepción específica sin necesidad de modificar el principio. El artículo de revisión periódica define cuándo la constitución se revisa proactivamente.

**6.4 Criterios de cierre**

La capa constitucional está cerrada cuando se cumplen tres condiciones. Primero, los principios cubren las dimensiones críticas del producto: usuarios y experiencia, datos y privacidad, evolución y arquitectura, calidad y operación, gobernanza interna. Segundo, cada principio está formulado de manera accionable, no como aspiración: se puede usar para bloquear o aprobar una decisión concreta. Tercero, hay artículos de gobernanza que indican cómo se modifica la constitución; sin ellos, las modificaciones se harán de hecho sin trazabilidad.

**Caso testigo:** La constitución de deRuedas Gestión tiene 7 principios (centralidad del usuario, independencia tecnológica del agente, auditabilidad, mínimo privilegio, consistencia eventual aceptada, evolución con cambios trazables, sostenibilidad económica del producto) y 8 artículos de gobernanza. La extensión total es de 121 párrafos. La constitución se citó explícitamente en la justificación de 47 de los 194 elementos del plan de implementación.

**6.5 Errores comunes**

- Principios genéricos: “Calidad ante todo”, “El usuario es lo primero” — no son accionables.

- Demasiados principios: si hay 25, en la práctica no hay ninguno; el equipo no los recuerda.

- Constitución sin gobernanza: principios sin artículos sobre cómo modificarlos.

- Principios contradictorios sin jerarquía declarada: cuando entran en conflicto, las decisiones se vuelven políticas.

- Constitución olvidada: documento creado al inicio que nadie revisa después; principios fósiles.

**7. Capa 4 — Especificación técnica**

**Capa 4 Especificación técnica del sistema**

**Pregunta:** ¿Cómo se estructura el sistema? ¿Cuáles son sus dominios, contratos e invariantes?

**Nivel N4:** N3 (modelado formal del sistema)

**Audiencia:** Equipo técnico, agente de IA implementador, futuros mantenedores

**Granularidad:** Detalle técnico suficiente para implementar sin reinterpretar

**7.1 Función de la capa**

La especificación técnica es el primer documento del cuerpo SDD que tiene contenido predominantemente técnico. Su función es traducir los principios constitucionales y las historias en una arquitectura concreta: dominios funcionales con responsabilidades claras, contratos de API y de eventos, modelos de datos, decisiones arquitectónicas justificadas. La especificación técnica es el documento contra el que el agente de IA implementa: si está bien hecho, las tareas del plan son traducción mecánica; si está mal hecho, el agente improvisa y la coherencia se pierde.

La trampa más común es la especificación que parece detallada pero no es implementable: tiene diagramas bonitos pero las relaciones entre componentes están subespecificadas, los contratos son ambiguos, las decisiones difíciles fueron evitadas. La práctica del método es someter la spec a la prueba del implementador externo: ¿podría una persona técnicamente competente que no participó del diseño implementar el sistema con la spec sola? Si la respuesta es no, la spec todavía no está cerrada.

**7.2 Estructura recomendada**

|  |  |
|:---|:---|
| **Sección** | **Contenido** |
| Visión arquitectónica | El sistema en una página: estilo arquitectónico (monolito modular, microservicios, eventos, etc.), tecnologías base, principios arquitectónicos derivados de la constitución. |
| Dominios funcionales | Descomposición del sistema en dominios con responsabilidades, dependencias entre dominios, modelo de datos por dominio. |
| Contratos de API | Endpoints expuestos con paths, métodos, schemas de entrada y salida, códigos de error, ejemplos. |
| Eventos de dominio | Eventos publicados, sus payloads, los consumers esperados, las garantías de entrega y orden. |
| Capas transversales | Autenticación, autorización, multi-tenancy, cifrado, observabilidad, resiliencia: cómo se aplican homogéneamente. |
| ADRs (decisiones arquitectónicas) | Decisiones no obvias con sus alternativas consideradas, criterios de evaluación y razones de elección. |
| Modelo de despliegue | Topología de containers, redes, almacenamiento. Pipelines de CI/CD. |
| Estrategias de evolución | Cómo se versionan los contratos, cómo se hacen migraciones, cómo se introduce un cambio incompatible. |

**7.3 Los Architecture Decision Records (ADRs)**

Los ADRs son la pieza más distintiva de la spec técnica y la que más valor agrega en el largo plazo. Un ADR documenta una decisión arquitectónica concreta con tres componentes: el contexto (qué motivó tomar la decisión, qué fuerzas estaban en juego), las alternativas consideradas (cuáles se evaluaron y por qué se descartaron), la decisión adoptada con su justificación y sus consecuencias previsibles. Los ADRs se numeran (ADR-001, ADR-002...) y nunca se editan retroactivamente: si una decisión cambia, se crea un ADR nuevo que supersede al anterior y la línea de superseding queda visible.

ADR-006 — Aislamiento multi-tenant con Row-Level Security

Estado: Aceptado

Fecha: 2026-02-14

Anclaje constitucional: P1 (aislamiento), P3 (auditabilidad)

Contexto:

El producto es multi-tenant: distintas agencias comparten

infraestructura pero sus datos no deben mezclarse. Necesitamos

garantizar aislamiento estricto incluso ante bugs de aplicación.

Alternativas consideradas:

1\. Una base de datos por tenant (database-per-tenant)

2\. Schema por tenant (schema-per-tenant)

3\. Tabla compartida con tenant_id + filtrado en aplicación

4\. Tabla compartida con tenant_id + RLS en PostgreSQL

Decisión: opción 4 (tabla compartida + RLS)

Razones de la elección:

· Defensa en profundidad: incluso si la aplicación olvida filtrar,

PostgreSQL impide leer datos de otro tenant.

· Costo operativo: una sola base es más simple de operar que N bases.

· Backups y migraciones: triviales con una sola base.

Razones de descartar las alternativas:

· Database-per-tenant: costo de mantenimiento crece linealmente,

backups y migraciones se vuelven una pesadilla.

· Schema-per-tenant: similares costos sin garantía adicional sobre RLS.

· Solo tenant_id sin RLS: depende totalmente de no olvidar el filtro,

lo cual contradice el principio de defensa en profundidad.

Consecuencias:

· Toda tabla con datos del tenant debe tener tenant_id NOT NULL

y política RLS activa.

· Tests de aislamiento bloqueantes en CI son obligatorios.

· El acceso administrativo (super_admin) cruza tenants y debe

tener auditoría reforzada (ver ADR-008).

**7.4 Criterios de cierre**

La especificación técnica está cerrada cuando un implementador competente externo puede leerla y reproducir el sistema sin necesidad de preguntar al diseñador original. Esta es una vara alta que rara vez se cumple en una primera versión: la spec técnica típicamente atraviesa varias revisiones a medida que aparece la evidencia de que cierto fragmento es ambiguo o subespecificado. La práctica del método es no tratar como cerrada una spec que aún no soportó esta prueba.

**Caso testigo:** La spec técnica de deRuedas tiene 10 dominios funcionales (catálogo, leads, conversaciones, etc.), 12 ADRs sobre decisiones no obvias (multi-tenancy, eventos, cifrado, identidad, etc.), contratos completos para 87 endpoints REST y 14 tipos de eventos. La extensión total es de 2085 elementos en el documento. El plan de implementación se construyó referenciando explícitamente las secciones de la spec; cada tarea declara qué fragmento de spec materializa.

**7.5 Errores comunes**

- Spec demasiado abstracta: diagramas de cajas pero sin contratos concretos.

- Spec demasiado prematura: detalles de implementación que pertenecen al plan.

- ADRs decorativos: documentan la elección pero no las alternativas; no aportan valor cuando hay que reconsiderar.

- Falta de ADRs: las decisiones no obvias se toman pero no se documentan, y nadie recuerda por qué un mes después.

- Spec desconectada de la constitución: se introduce algo que viola un principio sin explicitarlo.

**8. Capa 5 — Plan de implementación**

**Capa 5 Plan de implementación con tareas atómicas**

**Pregunta:** ¿Qué hacer la próxima semana, en qué orden, con qué criterio de hecho?

**Nivel N4:** N4 (operacionalización)

**Audiencia:** Equipo de desarrollo, agente de IA implementador, gerente de producto

**Granularidad:** Tareas atómicas de 4 a 16 horas con definition of done

**8.1 Función de la capa**

El plan de implementación es la última capa del cuerpo principal y la que más cerca está del código. Su función es descomponer la especificación técnica en tareas atómicas ejecutables, ordenarlas según dependencias y agruparlas en olas que producen entregables coherentes. El plan es lo que el equipo de desarrollo y el agente de IA usan día a día; las capas superiores se consultan cuando surge una duda conceptual, pero el plan es el documento de trabajo cotidiano.

La tentación con el plan es saltarlo: una vez que la spec técnica está clara, parece tentador empezar a implementar directamente. El método sostiene que el costo de saltar el plan es alto: sin tareas atómicas con criterios explícitos de hecho, el agente de IA improvisa el alcance y produce implementaciones que tocan demasiadas cosas simultáneamente, perdiendo la atomicidad que vuelve auditables a los cambios. Y sin orden de dependencias el equipo se traba en bloqueos evitables.

**8.2 Anatomía de una tarea atómica**

T-027 — Implementar políticas RLS en tablas de leads y conversaciones

Ola: 0 — Cimientos

Estimación: 8 horas

Asignable a: agente de IA con revisión humana

Anclaje:

· Spec técnica: sección 8.4 (multi-tenancy)

· ADR: ADR-006 (RLS como aislamiento)

· Principio constitucional: P1 (aislamiento estricto)

· Historias afectadas: E2-H1 a E2-H8 (todas las de leads)

Dependencias:

· T-010 (RLS framework establecido en tablas base)

· T-014 (RBAC completo y auth funcionando)

Definition of Done:

· Tablas leads, conversations, messages tienen RLS habilitada.

· Política tenant_isolation activa en cada tabla.

· Tests de aislamiento (suite test_tenant_isolation_leads) pasan.

· Migration aplicable y reversible documentada.

· Code review aprobado por security reviewer.

Riesgos identificados:

· Si el set de current_setting falla, las queries devuelven 0 filas

y el bug puede confundirse con datos faltantes. Mitigación:

middleware lanza error explícito si no hay tenant context.

Notas para el agente de IA:

· Seguir el patrón de T-010, no inventar variantes.

· No mergear sin que tests de aislamiento estén verdes.

**8.3 La organización en olas**

Las tareas se agrupan en olas. Cada ola es un conjunto coherente que produce un entregable verificable. Las olas se ordenan por dependencia: la ola 0 establece los cimientos técnicos, la ola 1 entrega el MVP funcional, las olas siguientes agregan capacidades. Dentro de cada ola las tareas se ordenan por dependencia interna pero pueden paralelizarse cuando no la hay.

La regla de oro de las olas es que el corte entre olas debe corresponder a un momento natural del producto: una ola termina cuando hay algo demostrable y el equipo puede pausar sin que queden cosas a medias. La olaola 0 termina cuando hay auth, multi-tenancy y observabilidad funcionando; la ola 1 termina con el primer flujo end-to-end completo; etc. Sin esta disciplina las olas se vuelven sprints disfrazados.

**8.4 Criterios de cierre**

La capa de plan está cerrada cuando se cumplen tres condiciones simultáneas. Primero, todas las tareas tienen granularidad atómica entre 4 y 16 horas: las tareas más grandes se subdividen, las más pequeñas se fusionan. Segundo, cada tarea tiene definition of done verificable: el implementador (humano o agente) sabe exactamente qué tiene que entregar. Tercero, las dependencias entre tareas son explícitas y consistentes: no hay ciclos, no hay tareas huérfanas, no hay dependencias implícitas que se descubren al ejecutar.

**Caso testigo:** El plan de implementación de deRuedas tiene 194 tareas atómicas distribuidas en 4 olas. La extensión total es de 4661 párrafos. Cada tarea incluye anclaje a la spec técnica, dependencias, DoD y notas para el agente de IA. La trazabilidad es explícita: el 100% de las tareas referencia al menos una sección de la spec técnica.

**8.5 Errores comunes**

- Tareas demasiado grandes (“implementar el módulo de leads”): el alcance se vuelve subjetivo y el DoD imposible.

- Tareas sin DoD: el implementador entrega algo plausible que después no satisface.

- Dependencias implícitas: la tarea X requiere que Y esté hecho pero el plan no lo dice; se descubre al ejecutar.

- Mezclar tareas técnicas con tareas de negocio: “refactorizar X” y “decidir el pricing del plan Pro” no son del mismo tipo.

- Olas que no corresponden a entregables verificables: la ola termina pero nadie puede demostrar nada nuevo.

**9. Capas complementarias**

El cuerpo principal de cinco capas es suficiente para construir un producto de software. Pero hay dimensiones que no encajan plenamente en ninguna de las cinco capas y que conviene desarrollar en documentos propios cuando el contexto del proyecto lo amerita. Llamamos a estos documentos capas complementarias porque siguen las mismas convenciones del cuerpo principal —audiencia clara, granularidad propia, criterios de cierre, trazabilidad— pero atienden dimensiones específicas. La decisión de incluir una capa complementaria depende del contexto: no todo proyecto las necesita todas.

**9.1 Plan de seguridad y compliance**

La seguridad y la privacidad regulatoria atraviesan transversalmente las cinco capas principales —la constitución la enuncia como principio, la spec técnica la implementa, el plan la materializa— pero su contenido es lo suficientemente denso y específico como para diluirse si no tiene documento propio. La capa de seguridad consolida modelo de amenazas, controles técnicos catalogados, política de privacidad regulatoria, plan de respuesta a incidentes, plan de continuidad y SSDLC. Es lo que se le presenta a un cliente que pide infosec questionnaire o a un auditor.

La capa de seguridad es claramente recomendable cuando el producto procesa datos personales bajo régimen regulado, cuando los clientes objetivo son organizaciones con compras profesionales, cuando se persigue certificación formal en algún horizonte temporal. Es opcional cuando el producto es interno, experimental o de muy bajo riesgo.

**9.2 Plan de operaciones (SRE)**

La operación sostenida del producto en producción exige un plan que define SLOs y SLIs, política de on-call, runbooks por componente, gestión de capacity, observability obligatoria por componente, proceso de cambios y deploys. Tiene solapamiento con la capa de seguridad pero el foco es distinto: seguridad atiende lo defensivo, SRE atiende la calidad sostenida del servicio en operación normal. La capa SRE es recomendable cuando el producto está en producción con SLA explícito, cuando hay equipo dedicado a operación, cuando la disponibilidad es propuesta de valor diferenciada.

**9.3 Plan de testing y QA**

Aunque la spec técnica menciona estrategia de testing y el plan incluye tareas de testing, una capa formal de QA aporta valor cuando el contexto lo requiere: estrategia piramidal explícita (unit / integration / e2e), cobertura objetivo por dominio, gestión de datos de prueba, ambientes y promociones, automatización de regresión, criterios de release. Es claramente recomendable cuando el producto tiene compliance que exige trazabilidad de pruebas, cuando hay equipo dedicado de QA, cuando se prevé certificación. Es opcional para productos pequeños donde el testing está naturalmente integrado al desarrollo.

**9.4 Plan de Go-To-Market y pricing**

La estrategia comercial menciona el modelo de monetización pero no baja a tácticas. Un GTM completo incluye estructura final de planes con números cerrados, programa de early adopters formalizado, funnel de adquisición, ciclo de venta esperado, métricas de éxito por segmento, plan de retención y expansión, competitive positioning. Es recomendable para productos B2B con ciclo de venta no trivial. Es menos crítico para productos B2C de adopción autónoma.

**9.5 Manual de usuario y plan de onboarding**

Para productos donde la curva de aprendizaje del usuario impacta el éxito comercial, una capa dedicada al manual de usuario y al onboarding es justificable. Incluye guías por flujo crítico, FAQs, video-tutoriales de referencia, gamificación de los primeros días, criterios de éxito del usuario en cada milestone temprano. Es claramente recomendable en productos verticales B2B donde la base de usuarios no es nativa digital. Es opcional en productos cuya UX está pensada para autoaprendizaje.

**9.6 Brand book**

Cuando el producto va a tercerizar comunicación o marketing, o cuando el equipo no tiene cultura de diseño establecida, un brand book formaliza paleta, tipografías, tono de voz, lineamientos de copy, reglas de uso del logo. Es complemento del design system técnico que la spec puede contener: el design system define tokens y componentes; el brand book define la voz y el alma.

**9.7 Cuándo agregar una capa complementaria**

La regla práctica es la siguiente: una capa complementaria se agrega cuando el contenido específico empieza a aparecer disperso en las capas principales sin lograr cobertura completa. Si la spec técnica tiene secciones de seguridad inconexas, si el plan menciona tareas de testing sin una estrategia que las enmarque, si la estrategia tiene fragmentos de pricing que no terminan de bajar a números: el síntoma es que falta una capa complementaria. La decisión de agregarla se toma explícitamente y la capa nueva se construye con la misma disciplina que las cinco principales.

**Caso testigo:** El proyecto deRuedas Gestión incluye seis documentos: las cinco capas canónicas más el plan de seguridad y compliance. Las restantes capas complementarias (operaciones, testing/QA, GTM, manual de usuario, brand book) están planificadas para etapas posteriores según el momento del producto: el manual de usuario coincide con el primer contrato real, el plan de operaciones se construye al cierre de Ola 1 cuando hay carga real para diseñar SLOs, el GTM y pricing se afinan tras los aprendizajes de los primeros tenants.

**10. La práctica del proceso**

Este capítulo aborda cuestiones operativas que el método deja abiertas a propósito en los capítulos anteriores: cómo se dirige al agente de IA durante la construcción de cada capa, cómo se evalúa la calidad de un documento, cómo se gestiona el versionado, qué herramientas funcionan en la práctica.

**10.1 Cómo dirigir al agente de IA durante la construcción**

La interacción productiva con un agente de IA durante la construcción de una capa SDD tiene cinco principios prácticos. El primero es que el operador humano dirige conceptualmente y el agente ejecuta densamente. El operador tiene la dirección (qué se quiere lograr, qué tono, qué límites); el agente tiene la capacidad de producir prosa densa, tablas correctas, código sin typos. La división del trabajo no es “yo escribo, vos corregís” ni “vos escribís, yo corrijo”: es “yo dirijo, vos densificás bajo mi dirección, yo audito”.

El segundo es que el contexto se entrega progresivamente. En la construcción del documento N, el agente recibe los documentos previos (1 a N-1) como contexto. Esto es no negociable: sin las capas previas el agente improvisa decisiones que ya estaban tomadas. La inversión inicial de cargar contexto pagiza inmediatamente.

El tercero es que las correcciones sustantivas se hacen en el documento, no en la conversación. Si el agente produce algo que no encaja, la corrección se aplica en el archivo (el operador edita o pide la edición específica) y queda persistida. Las correcciones que solo viven en la conversación se pierden cuando la conversación termina.

El cuarto es que el operador resiste la tentación de aceptar como suficiente lo que es solo plausible. Un agente de IA produce prosa que suena bien aunque sea genérica o circular. La práctica del SDD exige preguntar después de cada bloque: “¿esto es específico de este proyecto o podría aplicar a cualquier producto de la misma categoría?”. Si la respuesta es la segunda, el bloque se reemplaza.

El quinto es que el operador reserva las decisiones N2 (porque) para sí mismo. El agente puede ayudar a articular argumentos, a explorar alternativas, a redactar; pero la decisión sobre qué principio adoptar, qué excepción admitir, qué prioridad asignar es del operador. Delegar las decisiones N2 al agente produce documentación correcta pero sin alma; el resultado se nota.

**10.2 Cómo evaluar la calidad de una capa**

La evaluación de la calidad de un documento SDD se hace con criterios tanto formales como sustantivos. Los criterios formales son verificables mecánicamente: la estructura está completa, los anclajes son consistentes, las tablas cierran. Los criterios sustantivos requieren juicio: la prosa es específica del proyecto, las decisiones difíciles fueron tomadas en lugar de evadidas, la trazabilidad bidireccional con las capas adyacentes funciona.

|  |  |
|:---|:---|
| **Criterio** | **Cómo se verifica** |
| Estructura completa según plantilla de la capa | Checklist contra el capítulo correspondiente del manual. |
| Anclaje a la capa superior | Cada sección puede mencionar qué fragmento de la capa superior la motiva. |
| Anclaje desde la capa inferior | Cada decisión es referenciada explícitamente desde la capa inferior. |
| Especificidad del contenido | Si se reemplaza el nombre del proyecto por otro, ¿qué porcentaje del documento sigue siendo verdadero? Si es alto, hay genericidad excesiva. |
| Decisiones difíciles tomadas | Hay momentos donde dos alternativas razonables compiten. ¿El documento elige una y justifica? ¿O las dos quedan abiertas para 'decidir después'? |
| Lectura limpia por terceros | Una persona externa al proceso lee y reproduce la lógica. Si necesita preguntar lo básico, falta densidad. |
| Coherencia interna | Las afirmaciones del documento no se contradicen entre sí; los números cierran; los identificadores son consistentes. |

**10.3 Versionado y evolución de los documentos**

Los documentos SDD viven en el repositorio del proyecto, no fuera. Esto significa: control de versiones con git, ramas para cambios sustantivos, pull requests con review, mismas convenciones que el código. La práctica recomendada es que cada cambio sustantivo a una capa pase por PR explícito, no por edición silenciosa. La razón es la misma que para el código: la trazabilidad de quién decidió qué y cuándo se vuelve crítica cuando hay que entender por qué el sistema es como es.

Cuando una capa superior cambia, hay que evaluar el impacto en las inferiores. La práctica es no propagar automáticamente: el cambio en la constitución se anuncia, el equipo evalúa qué partes de la spec técnica se afectan y qué tareas del plan se reordenan, y se hace en una sesión explícita. Propagar automáticamente lleva a inconsistencias que solo se descubren al ejecutar.

**10.4 Herramientas y toolchain**

La pregunta práctica de qué herramienta usar para producir los documentos admite varias respuestas legítimas. La elección que se hizo en el caso testigo de deRuedas y que demostró funcionar es un pipeline en Node.js usando la librería docx-js para generar archivos Word con formato profesional desde código JavaScript. Las ventajas son varias: el documento es codigo versionable; los helpers (h1, h2, bullet, tabla, callout) se reutilizan entre capas; el formato es consistente automáticamente; los cambios masivos son triviales (cambiar una paleta de colores requiere editar un valor).

Alternativas razonables son: Markdown puro (con conversión a PDF/DOCX al final, ventaja de simplicidad, desventaja de menos control sobre el formato), AsciiDoc (similar a Markdown pero más expresivo), LaTeX (control total de formato, costo de aprendizaje alto, mejor para documentación académica), o herramientas wysiwyg como Notion o Google Docs (rapidez de edición, dificultad para versionado serio). Cada elección tiene tradeoffs; el manual no prescribe una específica pero sí recomienda que la herramienta elegida soporte versionado robusto.

// Helpers típicos del pipeline Node.js + docx-js

const para = (text, opts) =\> new Paragraph({

spacing: { after: 140, line: 290 },

alignment: opts?.align \|\| AlignmentType.JUSTIFIED,

children: \[new TextRun({ text, font: 'Calibri', size: 22 })\],

});

const h1 = (text) =\> new Paragraph({

heading: HeadingLevel.HEADING_1,

spacing: { before: 360, after: 240 },

children: \[new TextRun({

text, font: 'Calibri', size: 36, bold: true, color: '1F3864'

})\],

});

// ... helpers para tablas, código, callouts, etc.

// El cuerpo del documento es array de elementos

const C = \[\];

C.push(h1('1. Introducción'));

C.push(para('Este documento describe...'));

// ... más bloques

// Construcción final

const doc = new Document({ sections: \[{ children: C }\] });

Packer.toBuffer(doc).then(buf =\> fs.writeFileSync('output.docx', buf));

**10.5 Métricas de proceso**

Para equipos que quieran medir su práctica del SDD, las métricas útiles son las siguientes. Tiempo promedio por capa en horas-persona-equivalente, distinguiendo el tiempo del operador humano del tiempo de procesamiento del agente. Densidad de cada documento (párrafos, tablas, decisiones documentadas) por capa. Tasa de retrabajo: porcentaje de cada capa que se modifica después de cerrarse, distinguiendo modificaciones por descubrimientos genuinos de modificaciones por errores de cierre prematuro. Trazabilidad: porcentaje de elementos de capa N que tienen anclaje verificable a capa N-1. Tiempo desde estrategia hasta primera ola completa.

**Caso testigo: métricas observadas:** El cuerpo SDD de deRuedas se construyó en aproximadamente 60 horas-operador distribuidas en cuatro semanas. Las cinco capas canónicas más el plan de seguridad totalizan unos 18.000 párrafos en seis archivos Word. La trazabilidad medida: 100% de las tareas del plan referencian al menos una sección de la spec técnica; 100% de los ADRs declaran su anclaje constitucional; 100% de las épicas declaran su anclaje a un objetivo estratégico. La tasa de retrabajo medida en la primera revisión interna fue del 8% para la spec técnica y del 3% para el plan de implementación.

**11. Anti-patrones y adaptación a otros contextos**

**11.1 Anti-patrones del proceso**

La aplicación del método admite varios anti-patrones recurrentes. Los más frecuentes y los más costosos en términos de daño al producto son los siguientes.

**11.1.1 Saltar capas**

El operador, presionado por tiempo, empieza el plan de implementación sin haber cerrado la spec técnica, o escribe la spec técnica sin tener constitución. El resultado es que las capas faltantes se reconstruyen implícitamente y mal: las decisiones se toman ad hoc, no se documentan, y aparecen como inconsistencias semanas después.

**11.1.2 Documentación post-hoc disfrazada de SDD**

El equipo desarrolla código sin documentación, y al final escribe documentos que parecen SDD pero son retrospectivos: la spec técnica se construye observando el código existente. Los documentos resultantes son técnicamente correctos pero no aportan: no anticipan, no orientan, no funcionan como contexto para el agente de IA. Es la versión cara de la documentación que nadie lee.

**11.1.3 Capas inconsistentes que no se reconcilian**

La capa superior se modifica pero la inferior no se actualiza. La spec técnica menciona una decisión que ya fue revisada en un ADR posterior; el plan de implementación incluye tareas que ya no son necesarias porque la historia que las motivaba se descartó. La consecuencia es que el equipo deja de creerle a las capas y vuelve a improvisar.

**11.1.4 Sobre-documentación que paraliza**

El equipo, queriendo ser riguroso, documenta cada decisión menor con el aparato pesado del SDD: cada función auxiliar tiene su ADR, cada componente UI tiene su sección en la spec. La consecuencia es que la documentación se vuelve inmanejable y el equipo deja de leerla. La regla operativa es que cada nivel del SDD documenta solo lo no obvio: si una decisión se infiere claramente del nivel superior, no requiere documentación propia.

**11.1.5 Confiar al agente las decisiones N2**

El operador, agotado, le pide al agente que decida cuál de dos alternativas adoptar. El agente da una respuesta defendible. La decisión se toma. Pero la responsabilidad intelectual sobre el porqué se diluye: nadie en el equipo humano sabe genuinamente por qué se eligió esa alternativa. Cuando el supuesto subyacente cambia, nadie reconsidera la decisión. El método sostiene que las decisiones N2 son las que el operador humano debe poder defender en una conversación cara a cara.

**11.1.6 Documento monolítico que mezcla niveles**

El equipo, queriendo ahorrar archivos, fusiona estrategia, historias y spec técnica en un solo documento. El resultado es ilegible: la audiencia se desorienta, los criterios de cierre se diluyen, la trazabilidad se pierde. La separación en capas no es burocrática: es lo que vuelve manejable cada documento.

**11.2 Adaptación a contextos distintos**

**11.2.1 Proyectos pequeños**

Para proyectos de menos de 20 horas-persona, el cuerpo SDD completo es desproporcionado. La adaptación recomendada es colapsar a tres capas: una hoja con estrategia + historias compactadas, un README arquitectónico con principios + spec, una checklist con plan. Lo que no se debe colapsar es la función de cada capa: estrategia + historias siguen respondiendo qué y para qué; el README sigue respondiendo cómo; la checklist sigue respondiendo qué hacer ahora.

**11.2.2 Proyectos académicos y educativos**

Para tesis de grado o posgrado, ejercicios de cátedra o investigación aplicada, el SDD se adapta agregando una capa explícita de marco teórico antes de la estrategia. Esa capa adicional sitúa el proyecto en el campo académico, declara las preguntas de investigación y enmarca las decisiones técnicas posteriores con respecto a la literatura. El resto del cuerpo SDD funciona como evidencia documental del proceso de diseño y desarrollo.

**11.2.3 Equipos sin agente de IA**

El SDD funciona también sin agente de IA: lo que se gana es coherencia y trazabilidad, lo que no se gana es la velocidad de densificación que el agente proporciona. Equipos sin agente típicamente producen documentos más cortos pero igualmente valiosos. La advertencia es no degradar la disciplina: la tentación de “escribir solo lo necesario” suele convertirse en “no escribir nada”.

**11.2.4 Proyectos legacy**

Adaptar SDD a un proyecto legacy es un caso especial. Se hace inverso: primero se reconstruye la documentación capa por capa observando el sistema existente, sabiendo que la capa estratégica probablemente fue implícita y se reconstruye por inducción. El producto de este ejercicio no es perfecto pero proporciona algo valioso: un mapa explícito que el equipo puede usar para evolucionar el sistema con disciplina.

**11.2.5 Equipos grandes con múltiples voces**

En equipos grandes el SDD requiere mecanismos adicionales de gobernanza: quién aprueba un cambio constitucional, cómo se sincronizan modificaciones a la spec técnica entre subequipos, cómo se priorizan tareas competidoras del plan. La constitución del proyecto se complementa con un documento de governance específico del equipo. La capa de plan tiende a fragmentarse por subequipo con un meta-plan que reconcilia.

**11.3 Cuándo no usar SDD**

Para honestidad metodológica, vale la pena enumerar cuándo SDD es desaconsejado. Proyectos exploratorios cuya hipótesis principal es averiguar si vale la pena construir algo: el costo de documentar capa por capa es alto si el proyecto va a descartarse en una semana. Productos de muy corta vida: prototipos para demostración, scripts ad hoc, automatizaciones que se usan dos veces. Proyectos donde el código es trivial respecto al producto: campañas de marketing donde el sitio es un detalle, instalaciones físicas donde el software es un complemento. Equipos en pánico: cuando hay un incendio operativo o presión existencial sobre el negocio, el método disciplinado se posterga hasta que la organización pueda volver a invertir en proceso.

**11.4 Madurez progresiva en la adopción**

Equipos que adoptan SDD por primera vez no llegan a la versión completa de inmediato. Una progresión observada que funciona es la siguiente: en el primer proyecto se construye solo el plan de implementación con disciplina (capa 5); en el segundo se agrega la spec técnica (capa 4); en el tercero se incorpora la constitución (capa 3); etc. Esta adopción progresiva permite que el equipo experimente el valor de cada capa antes de comprometerse con el cuerpo completo. La advertencia es no quedarse en versiones parciales del método: las versiones parciales son útiles pero no producen los beneficios completos.

**12. Glosario y referencias**

**12.1 Glosario**

|  |  |
|:---|:---|
| **Término** | **Definición** |
| ADR | Architecture Decision Record. Documento que captura una decisión arquitectónica con su contexto, alternativas consideradas, decisión adoptada y consecuencias previsibles. |
| Anclaje | Referencia explícita entre capas que materializa la trazabilidad: una tarea ancla a una sección de spec, que ancla a un principio constitucional, etc. |
| Capa | Cada uno de los niveles del cuerpo SDD: estrategia, historias, constitución, spec técnica, plan de implementación. También se usa para capas complementarias (seguridad, etc.). |
| Constitución | Capa 3 del cuerpo SDD. Documento que enuncia los principios irrenunciables del producto y los artículos de gobernanza para modificarlos. |
| DBR | Design-Based Research. Metodología de investigación educativa que se mueve entre el diseño de intervenciones y la teorización a partir de su implementación. |
| Definition of Done (DoD) | Criterio explícito y verificable que indica cuándo una tarea atómica puede considerarse completada. |
| Estrategia | Capa 1 del cuerpo SDD. Documento que articula la hipótesis de negocio: qué construir, para quién, por qué, cómo se gana dinero. |
| Épica | Agrupador de historias de usuario que representa un área funcional coherente del producto. |
| Especificación técnica | Capa 4 del cuerpo SDD. Documento que define dominios funcionales, contratos, ADRs, modelo de datos, modelo de despliegue. |
| Granularidad atómica | Tamaño de una tarea del plan de implementación tal que puede completarse en una unidad de trabajo coherente (típicamente 4-16 horas) con un Definition of Done verificable. |
| Historia de usuario | Unidad de demanda funcional formulada como “como X, quiero Y, para Z”, con criterios de aceptación verificables. Componente de la capa 2 del SDD. |
| N1, N2, N3, N4 | Los cuatro niveles de la trazabilidad cognitiva. N1 es reconocimiento, N2 es comprensión, N3 es modelado, N4 es operacionalización. |
| N4 (marco) | Marco conceptual de cuatro niveles de trazabilidad cognitiva adoptado por el SDD. |
| Ola | Unidad temporal del plan de implementación. Conjunto de tareas que produce un incremento coherente y entregable del producto. Se distingue del sprint por privilegiar coherencia sobre tiempo fijo. |
| Plan de implementación | Capa 5 del cuerpo SDD. Documento que descompone la spec técnica en tareas atómicas ordenadas por dependencia y agrupadas en olas. |
| Principio rector | Enunciado de la constitución que el producto se compromete a respetar incluso bajo presión adversa. Tiene formulación accionable, justificación e implicancias operativas. |
| SDD | Spec-Driven Development. Metodología de desarrollo guiada por especificación documentada en capas, con trazabilidad explícita entre capas y diseñada para colaboración productiva con agentes de IA. |
| Trazabilidad | Propiedad del cuerpo SDD por la cual cada elemento de cada capa puede remontarse a elementos de capas adyacentes mediante anclajes explícitos. |
| Vibe coding | Estilo de desarrollo donde el operador interactúa conversacionalmente con un agente de IA aceptando lo que produce sin marco metodológico. SDD es la respuesta disciplinada al vibe coding. |

**12.2 Referencias bibliográficas**

Las siguientes referencias son anclas conceptuales del método. No son lectura obligatoria pero proveen el contexto teórico de las prácticas adoptadas.

- Cohn, M. (2004). User Stories Applied: For Agile Software Development. Addison-Wesley. Referencia clásica para la estructura de historias de usuario.

- Nygard, M. (2011). Documenting Architecture Decisions. Blog post seminal que popularizó los ADRs. Disponible en cognitect.com.

- Wang, F. & Hannafin, M. (2005). Design-Based Research and Technology-Enhanced Learning Environments. Educational Technology Research and Development. Marco DBR aplicado a investigación educativa.

- Newman, S. (2021). Building Microservices, 2nd ed. O'Reilly. Referencia para descomposición en dominios funcionales.

- Kleppmann, M. (2017). Designing Data-Intensive Applications. O'Reilly. Referencia para decisiones arquitectónicas sobre persistencia y consistencia.

- Beyer, B. et al. (eds.) (2016). Site Reliability Engineering. O'Reilly. Referencia para la capa complementaria de operaciones.

- Documentación oficial de Anthropic sobre patrones de uso de agentes de IA en desarrollo de software.

**12.3 Notas finales**

Este manual describe una metodología que está en evolución. Su versión actual refleja la práctica madura al momento de su publicación pero deja explícitamente abiertas tres líneas de desarrollo. La primera es la métrica del proceso: el manual menciona métricas posibles pero no propone aún un sistema de evaluación cuantitativo; un trabajo futuro consistirá en proponer indicadores estandarizados que permitan comparar aplicaciones del método entre proyectos. La segunda es la integración con prácticas de DevOps maduras: la articulación entre capas SDD y procesos de CI/CD, infrastructure as code y observability merece desarrollo propio. La tercera es la dimensión pedagógica: cómo se enseña SDD a estudiantes universitarios, qué andamiaje requiere su adopción por equipos novatos, qué evaluaciones son apropiadas en formación inicial.

La invitación del manual es que cada equipo que aplique el método registre su experiencia y la comparta. La metodología gana profundidad cuando hay variedad de casos: aplicaciones a proyectos B2B y B2C, a productos verticales y horizontales, a equipos de distintos tamaños, a contextos académicos y comerciales. La acumulación de casos es lo que va a permitir, en algún momento, escribir una segunda edición de este manual con base empírica más robusta que la actual.

**12.4 Control de versiones del manual**

|  |  |  |  |
|:---|:---|:---|:---|
| **Versión** | **Fecha** | **Autor** | **Cambios** |
| 1.0 | Mayo 2026 | Autor del manual | Versión inicial. Cinco capas canónicas, trazabilidad N4, capas complementarias, anti-patrones y adaptación. Caso testigo: deRuedas Gestión. |

La próxima revisión del manual está prevista cuando se acumulen al menos tres casos completos adicionales aplicando la metodología, momento en el cual será posible incorporar variaciones observadas, refinar los anti-patrones identificados y consolidar las métricas de proceso con datos empíricos comparables.
