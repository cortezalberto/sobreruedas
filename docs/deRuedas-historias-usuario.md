**Backlog de Historias de Usuario**

***deRuedas Gestión***

*SaaS vertical de gestión para agencias de vehículos*

Documento complementario al plan estratégico

Mayo de 2026

**1. Introducción**

**Propósito del documento**

Este documento constituye el backlog inicial de historias de usuario para la construcción del SaaS “deRuedas Gestión”, descripto estratégica y funcionalmente en el documento previo “Modelo de Mejoras Estratégicas para deRuedas.com.ar y Plan de Implementación del SaaS”. Su objetivo es servir como insumo de planificación para los equipos de producto e ingeniería, base para sesiones de refinement y estimación, y referencia trazable de las decisiones de alcance del producto durante las cinco fases de desarrollo previstas.

Las historias se organizan en doce épicas: las ocho funcionales que corresponden a los módulos del producto, más cuatro transversales (onboarding y configuración, publicación multicanal, aplicación móvil, y administración interna de deRuedas). Cada historia incluye narrativa con el formato estándar Como/Quiero/Para, criterios de aceptación en estilo Gherkin (Dado/Cuando/Entonces), prioridad MoSCoW, estimación en puntos de historia, y la fase del roadmap a la que pertenece.

**Convenciones**

**Formato de la historia**

Cada historia tiene un identificador único compuesto por el código de épica (E1 a E12) y un número correlativo dentro de la épica. La narrativa sigue el patrón “Como \[persona\], quiero \[acción\], para \[beneficio\]”. Los criterios de aceptación se redactan en formato Dado / Cuando / Entonces, intentando capturar tanto el flujo principal como los casos de error o validación más relevantes.

**Prioridad MoSCoW**

- Must: imprescindible para que el producto cumpla su propósito en la fase a la que pertenece. Su ausencia bloquea la entrega.

- Should: importante y aporta valor relevante, pero no bloquea la entrega si se posterga.

- Could: deseable, mejora la experiencia o agrega valor incremental. Es candidato natural a recortar si los plazos aprietan.

- Won’t (this time): explícitamente fuera del alcance del SaaS o postergado para una fase posterior; no aparece en este documento, pero se nombra cuando un caso de uso adyacente lo amerita.

**Estimación**

Las estimaciones siguen la escala de Fibonacci (1, 2, 3, 5, 8, 13, 21) habitual en metodologías ágiles. La unidad es “puntos de historia”, una medida relativa de complejidad y esfuerzo, no una conversión directa a horas. Estas estimaciones son orientativas y deben ser revisadas por el equipo de desarrollo en sesiones de planning poker.

**Fases del roadmap**

- F1: MVP funcional. Stock, CRM básico, publicación a deRuedas, mensajería WhatsApp inicial. Meses cuatro a siete.

- F2: CRM avanzado e integraciones de comunicación. Pipelines configurables, multi-canal, otras integraciones de portales. Meses ocho a diez.

- F3: Permutas y financiación integrada. Meses once a trece.

- F4: Documentación, finanzas y BI. Mobile app a paridad. Meses catorce a dieciséis.

- F5: Ecosistema, plataformización, capa de inteligencia artificial. Mes diecisiete en adelante.

**Glosario**

- Tenant: cada cliente del SaaS (cada agencia) es un tenant separado dentro de la arquitectura multi-tenant; sus datos están aislados lógicamente.

- Lead: oportunidad comercial generada por una consulta de un comprador potencial sobre un vehículo específico o sobre un perfil de búsqueda.

- Pipeline: secuencia de etapas configurables por las que avanza un lead hasta convertirse en operación cerrada o lead perdido.

- Permuta: operación en la que el comprador entrega un vehículo usado como parte de pago en la compra de otro vehículo.

- Originación: proceso por el cual se genera y formaliza un crédito a favor de un comprador, mediado por una financiera integrada.

**2. Personas**

El producto se diseña pensando en cinco perfiles de usuario claramente diferenciados. Cada historia hace referencia explícita a la persona destinataria, lo que orienta tanto el diseño de interfaz como las decisiones de permisos y alcance funcional.

**P1 — Gerente o dueño de agencia**

Es el decisor principal y, habitualmente, el comprador del producto. En agencias chicas y medianas suele coincidir con el dueño. Necesita visibilidad sobre la operación completa de su agencia: stock, pipeline comercial, ventas, productividad de cada vendedor, salud financiera. Valora reportes consolidados accesibles desde su teléfono. No siempre es nativo digital, así que la usabilidad y la curva de aprendizaje son críticas. Está frecuentemente fuera de la oficina, por lo que la app móvil le importa.

**P2 — Vendedor**

Es el usuario más frecuente del sistema. Carga vehículos al stock, atiende leads entrantes desde múltiples canales, gestiona conversaciones por WhatsApp, agenda pruebas de manejo, prepara cotizaciones, negocia con compradores y cierra operaciones. Valora la velocidad de las acciones repetitivas, la integración con WhatsApp y la posibilidad de trabajar desde el celular cuando está atendiendo en el local o llevando un auto a probar.

**P3 — Administrativo**

Cubre las funciones de back-office: gestión documental, conciliación de cobros, seguimiento de cuenta corriente, preparación de paquetes documentales para registro automotor y AFIP, interacción con financieras y aseguradoras. No suele participar de la negociación comercial, pero su trabajo es indispensable para cerrar formalmente las operaciones.

**P4 — Customer Success Manager (deRuedas)**

Es interno de deRuedas, no de la agencia cliente. Su rol es onboarding y soporte continuo de las agencias. Necesita un backoffice donde ver el estado de cada cuenta, intervenir cuando una agencia tiene problemas, configurar parámetros que el cliente no puede tocar, y monitorear métricas de adopción y salud.

**P5 — Super Admin (deRuedas)**

Rol técnico y administrativo dentro de deRuedas con acceso transversal a todos los tenants. Realiza tareas de configuración global, mantenimiento, gestión de planes y precios, monitoreo técnico, y resolución de incidencias críticas que exceden las facultades del Customer Success.

**3. Mapa de épicas**

La tabla siguiente sintetiza las doce épicas que componen el backlog del producto. La columna “Fase” indica la fase del roadmap en que se concentra la épica, aunque algunas se distribuyen entre varias. La columna “HU” indica la cantidad de historias contenidas en cada épica.

|  |  |  |  |
|:--:|:---|:---|:--:|
| **ID** | **Épica** | **Objetivo** | **HU** |
| **E1** | Onboarding y configuración | Permitir que una agencia se dé de alta, configure sus datos, sucursales, usuarios y parámetros operativos. | 8 |
| **E2** | Gestión de stock | Administrar el inventario completo de vehículos con sus atributos, fotos, estados y trazabilidad. | 10 |
| **E3** | Publicación multicanal | Publicar y mantener sincronizados los avisos en deRuedas y otros portales sin doble carga. | 6 |
| **E4** | CRM y pipeline comercial | Capturar, calificar y dar seguimiento a los leads desde la consulta hasta el cierre o pérdida. | 11 |
| **E5** | Mensajería y WhatsApp Business | Centralizar las conversaciones con compradores y mantener trazabilidad asociada al lead. | 8 |
| **E6** | Permutas | Estandarizar el flujo de recibir un usado como parte de pago, desde valuación a alta de stock. | 7 |
| **E7** | Financiación integrada | Precalificar, comparar y formalizar créditos con la cartera de financieras integradas. | 8 |
| **E8** | Gestión documental | Organizar la documentación de vehículos y operaciones con búsqueda, vencimientos y firma. | 7 |
| **E9** | Cuenta corriente y conciliación | Llevar el flujo financiero básico de la agencia: cobros, pagos, cuenta corriente, conciliación. | 7 |
| **E10** | Business intelligence | Proveer dashboards y reportes consolidados para la gestión y la toma de decisiones. | 8 |
| **E11** | Aplicación móvil | Habilitar las funciones críticas de operación desde el celular del vendedor o del gerente. | 6 |
| **E12** | Administración y soporte (deRuedas) | Backoffice para que el equipo de deRuedas opere, soporte y monitoree los tenants. | 6 |

El total resultante es de noventa y dos historias de usuario distribuidas entre las cinco fases. Aproximadamente cuarenta y cinco se concentran entre las fases uno y dos (MVP y CRM avanzado), unas veintiocho en las fases tres y cuatro (permutas, financiación, finanzas, BI, mobile), y el resto se distribuye en fase cinco como evolución continua.

**Épica E1 — Onboarding y configuración**

Esta épica cubre el alta inicial de una agencia en la plataforma, la configuración de sus datos básicos, la gestión de usuarios y roles, la configuración de sucursales para clientes que las tengan, y la activación de integraciones con servicios externos. Su correcta ejecución determina la fricción de adopción del producto y, en consecuencia, las tasas de activación tempranas.

**HU-E1-001 — Alta de cuenta de agencia**

Como ***Customer Success Manager***, quiero *crear una nueva cuenta de agencia con datos fiscales, comerciales y de contacto*, para *habilitar la operación inicial del cliente en el sistema.*

**Criterios de aceptación:**

- Dado que ingreso al backoffice de deRuedas, cuando completo el formulario de alta con CUIT, razón social, nombre comercial, email del responsable y teléfono, entonces el sistema crea un tenant nuevo aislado y envía email de activación al responsable.

- Dado que el CUIT ingresado ya existe en otro tenant, cuando intento crear la cuenta, entonces el sistema rechaza la creación con un mensaje claro de duplicidad.

- Dado que la cuenta fue creada, cuando el responsable activa su cuenta desde el email recibido, entonces puede ingresar al sistema con sus credenciales y acceder al asistente de configuración inicial.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F1

**HU-E1-002 — Configuración inicial guiada**

Como ***Gerente de agencia***, quiero *completar un asistente paso a paso de configuración inicial al ingresar por primera vez*, para *tener mi agencia operativa rápidamente sin perderme en menús.*

**Criterios de aceptación:**

- Dado que ingreso por primera vez al sistema, cuando se carga la pantalla de inicio, entonces el sistema me presenta un asistente con los pasos: datos de la agencia, sucursales, usuarios, integraciones.

- Dado que estoy en el asistente, cuando salto un paso opcional y avanzo al siguiente, entonces el sistema marca el paso saltado como pendiente y me lo recuerda en el dashboard hasta que lo complete.

- Dado que finalicé el asistente, cuando ingreso nuevamente al sistema, entonces se me muestra el dashboard completo y el asistente queda disponible bajo “Configuración”.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F1

**HU-E1-003 — Gestión de sucursales**

Como ***Gerente de agencia***, quiero *dar de alta múltiples sucursales con sus datos y direcciones*, para *asignar correctamente cada vehículo, vendedor y operación a la sucursal que corresponda.*

**Criterios de aceptación:**

- Dado que estoy en “Configuración → Sucursales”, cuando creo una sucursal con nombre, dirección, teléfono y horario, entonces queda disponible para ser referenciada desde stock, usuarios y operaciones.

- Dado que tengo una sucursal con vehículos asignados, cuando intento eliminarla, entonces el sistema me bloquea la eliminación y me ofrece reasignar los vehículos a otra sucursal antes de continuar.

- Dado que tengo plan Starter, cuando intento crear una segunda sucursal, entonces el sistema me notifica que el plan no permite multi-sucursal y me ofrece upgrade a Pro.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F1

**HU-E1-004 — Gestión de usuarios y roles**

Como ***Gerente de agencia***, quiero *invitar usuarios a la cuenta y asignarles roles con permisos específicos*, para *controlar qué puede ver y hacer cada miembro del equipo según su responsabilidad.*

**Criterios de aceptación:**

- Dado que estoy en “Configuración → Usuarios”, cuando invito a un usuario por email y le asigno un rol entre Vendedor, Administrativo o Gerente, entonces se envía invitación al email indicado y, al aceptarla, el usuario queda activo con esos permisos.

- Dado que un usuario pertenece a una sucursal específica, cuando ingresa al sistema, entonces solo puede ver vehículos y leads asignados a esa sucursal o a él directamente, salvo que tenga rol Gerente con visibilidad total.

- Dado que un vendedor deja la agencia, cuando lo desactivo, entonces sus leads y operaciones en curso quedan disponibles para reasignar y el usuario pierde acceso inmediato.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F1

**HU-E1-005 — Conexión con WhatsApp Business**

Como ***Gerente de agencia***, quiero *conectar el número de WhatsApp Business de la agencia al sistema*, para *centralizar las conversaciones de venta dentro de la plataforma.*

**Criterios de aceptación:**

- Dado que estoy en “Integraciones → WhatsApp”, cuando inicio el flujo de conexión y completo la autorización con Meta Business, entonces el sistema queda autorizado a enviar y recibir mensajes en mi nombre.

- Dado que la conexión es exitosa, cuando ingresa un mensaje a ese número, entonces aparece automáticamente en la bandeja unificada del sistema asociado al lead correspondiente o a uno nuevo si no se encuentra coincidencia.

- Dado que la conexión expira o falla, cuando un usuario intenta enviar un mensaje, entonces el sistema le notifica el error y me alerta como gerente para renovar la autorización.

**Prioridad:** Must **│ Estimación:** 13 pts **│ Fase:** F1

**HU-E1-006 — Conexión con cuenta de deRuedas portal**

Como ***Gerente de agencia***, quiero *vincular la cuenta del SaaS con mi cuenta del portal de deRuedas*, para *que mis vehículos se publiquen automáticamente sin doble carga.*

**Criterios de aceptación:**

- Dado que ya soy cliente del portal de deRuedas, cuando ingreso credenciales o autorizo la vinculación, entonces el sistema valida la cuenta y queda lista para publicar.

- Dado que la vinculación es exitosa, cuando creo un vehículo en el SaaS, entonces se publica automáticamente en mi cuenta del portal en el plan que tenga contratado ahí.

- Dado que el portal devuelve error en una publicación, cuando ocurre el evento, entonces el sistema lo registra, marca el aviso como “pendiente de publicación” y reintenta automáticamente.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F1

**HU-E1-007 — Configuración de pipeline de ventas**

Como ***Gerente de agencia***, quiero *configurar las etapas del pipeline comercial según el flujo de mi agencia*, para *que el sistema refleje cómo trabajamos realmente y no nos imponga un proceso ajeno.*

**Criterios de aceptación:**

- Dado que estoy en “Configuración → Pipeline”, cuando agrego, renombro, reordeno o elimino una etapa, entonces los cambios se reflejan inmediatamente en la visualización del pipeline.

- Dado que tengo leads en una etapa, cuando intento eliminarla, entonces el sistema me obliga a reasignar esos leads a otra etapa antes de proceder.

- Dado que el sistema instalado por defecto trae cinco etapas, cuando creo la cuenta, entonces puedo usarlas tal cual o personalizarlas en cualquier momento.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F2

**HU-E1-008 — Personalización visual de la cuenta**

Como ***Gerente de agencia***, quiero *subir el logo de mi agencia y elegir colores principales*, para *que la imagen institucional se refleje en notificaciones, comprobantes y comunicaciones automáticas.*

**Criterios de aceptación:**

- Dado que estoy en “Configuración → Marca”, cuando subo un logo en formato PNG o JPG y selecciono colores, entonces se previsualiza cómo lucirá en notificaciones y comprobantes.

- Dado que guardo la configuración, cuando se genera una notificación o comprobante, entonces utiliza el logo y los colores configurados.

**Prioridad:** Could **│ Estimación:** 3 pts **│ Fase:** F2

**Épica E2 — Gestión de stock**

Es el corazón operativo del producto. Su ejecución correcta condiciona la utilidad de todos los demás módulos: sin stock cargado, no hay publicación; sin publicación, no hay leads; sin leads, no hay pipeline ni operaciones. Por esta razón, las funcionalidades centrales son Must para el MVP y se priorizó deliberadamente la simplicidad de carga sobre la completitud de campos opcionales.

**HU-E2-001 — Alta de vehículo con datos básicos**

Como ***Vendedor***, quiero *cargar un vehículo nuevo en stock con sus datos esenciales*, para *tenerlo disponible rápidamente para empezar a venderlo.*

**Criterios de aceptación:**

- Dado que estoy en “Stock → Nuevo vehículo”, cuando ingreso marca, modelo, versión, año, kilometraje, color, dominio y precio, entonces el sistema valida los datos y crea el registro del vehículo en estado “en preparación”.

- Dado que el dominio ingresado ya existe en otro vehículo de mi agencia, cuando intento guardar, entonces el sistema rechaza la operación con mensaje claro y opción de buscar el existente.

- Dado que completé los datos básicos, cuando guardo, entonces puedo continuar con foto, equipamiento, descripción extendida y otros datos opcionales sin perder el avance.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F1

**HU-E2-002 — Carga de fotografías del vehículo**

Como ***Vendedor***, quiero *subir hasta veinte fotografías del vehículo desde computadora o celular*, para *ofrecer al comprador una vista completa del estado del vehículo.*

**Criterios de aceptación:**

- Dado que un vehículo está creado, cuando arrastro o selecciono archivos de imagen, entonces se suben en paralelo, se generan miniaturas y se permite reordenarlas con drag and drop.

- Dado que estoy desde un dispositivo móvil, cuando elijo “Tomar foto”, entonces se abre la cámara del dispositivo y la foto se sube directamente al vehículo.

- Dado que un archivo no es una imagen válida o supera diez MB, cuando intento subirlo, entonces el sistema lo rechaza con mensaje específico.

- Dado que tengo más de una foto cargada, cuando defino una como portada, entonces queda señalizada como tal y se utiliza en la publicación a portales.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F1

**HU-E2-003 — Edición y baja del vehículo**

Como ***Vendedor***, quiero *editar los datos de un vehículo o darlo de baja del stock*, para *mantener la información actualizada o retirarlo cuando ya no esté disponible.*

**Criterios de aceptación:**

- Dado que estoy en la ficha de un vehículo, cuando edito un campo y guardo, entonces los cambios quedan registrados con fecha, hora y usuario en el historial.

- Dado que un vehículo no tiene operaciones asociadas, cuando lo doy de baja, entonces queda en estado “archivado” y deja de publicarse en portales pero se conserva en el histórico.

- Dado que un vehículo tiene operación cerrada, cuando intento borrarlo, entonces el sistema lo bloquea y solo permite archivarlo.

**Prioridad:** Must **│ Estimación:** 3 pts **│ Fase:** F1

**HU-E2-004 — Estados del vehículo**

Como ***Vendedor***, quiero *cambiar el estado de un vehículo entre disponible, reservado, vendido, en taller o en preparación*, para *que el resto del equipo y los compradores tengan información veraz sobre la disponibilidad.*

**Criterios de aceptación:**

- Dado que un vehículo está disponible, cuando lo paso a reservado e indico el lead asociado, entonces se oculta de las publicaciones nuevas pero permanece visible en la ficha.

- Dado que un vehículo pasa a vendido, cuando confirmo la operación, entonces se despublica de todos los portales automáticamente y se asocia a la operación de venta.

- Dado que un vehículo pasa a “en taller”, cuando guardo, entonces se solicita causa y fecha estimada de retorno, y queda visible para el gerente en el dashboard de stock.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F1

**HU-E2-005 — Búsqueda y filtrado de stock**

Como ***Vendedor***, quiero *buscar vehículos por marca, modelo, dominio, año, rango de precio o estado*, para *encontrar rápidamente lo que necesito en una operación o consulta.*

**Criterios de aceptación:**

- Dado que estoy en “Stock”, cuando ingreso un texto en el buscador, entonces el sistema busca coincidencias en marca, modelo, versión y dominio en tiempo real.

- Dado que aplico múltiples filtros simultáneos, cuando los combino, entonces los resultados respetan la conjunción de todos los filtros.

- Dado que tengo una vista filtrada útil, cuando la guardo como favorita, entonces queda disponible en el menú lateral para acceso rápido.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F1

**HU-E2-006 — Importación masiva de stock**

Como ***Administrativo***, quiero *importar un archivo Excel o CSV con muchos vehículos a la vez*, para *no tener que cargar uno por uno cuando migramos desde nuestro sistema anterior.*

**Criterios de aceptación:**

- Dado que estoy en “Stock → Importar”, cuando descargo la plantilla y la completo, entonces puedo subirla y el sistema valida fila por fila los campos obligatorios y formatos.

- Dado que hay errores de validación, cuando se procesa el archivo, entonces el sistema muestra un reporte línea por línea de los errores y permite descargar las filas válidas para reintentar.

- Dado que la importación es exitosa, cuando finaliza, entonces los vehículos quedan creados en estado “en preparación” y se notifica al usuario por email.

**Prioridad:** Should **│ Estimación:** 8 pts **│ Fase:** F2

**HU-E2-007 — Histórico del vehículo**

Como ***Gerente de agencia***, quiero *consultar el historial completo de un vehículo dentro del sistema*, para *saber cuánto tiempo lleva en stock, qué precios tuvo y qué actividad generó.*

**Criterios de aceptación:**

- Dado que estoy en la ficha de un vehículo, cuando abro la pestaña “Historial”, entonces veo línea de tiempo con cambios de estado, modificaciones de precio, leads asociados y publicaciones.

- Dado que el vehículo lleva más tiempo del configurado en “rotación esperada”, cuando consulto el historial, entonces el sistema lo destaca con un indicador de “rotación lenta”.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F2

**HU-E2-008 — Sugerencia de precio basado en mercado**

Como ***Vendedor***, quiero *ver una sugerencia de precio cuando cargo un vehículo*, para *fijar un precio competitivo sin tener que investigar manualmente cada vez.*

**Criterios de aceptación:**

- Dado que cargo un vehículo con marca, modelo, año y kilometraje, cuando completo esos datos, entonces el sistema muestra rango de precios sugerido (mínimo, mediano, máximo) basado en datos de mercado de deRuedas.

- Dado que el precio que ingreso queda fuera del rango sugerido, cuando guardo, entonces el sistema muestra una alerta no bloqueante para confirmar.

- Dado que el modelo es muy poco frecuente y no hay datos suficientes, cuando consulto la sugerencia, entonces el sistema indica que no puede sugerir precio con confiabilidad y muestra el dato de “sin referencia”.

**Prioridad:** Could **│ Estimación:** 13 pts **│ Fase:** F4

**HU-E2-009 — API pública de stock**

Como ***Sistema externo de la agencia***, quiero *consultar y actualizar stock vía API REST*, para *integrar el SaaS con sistemas legados sin doble carga manual.*

**Criterios de aceptación:**

- Dado que tengo credenciales de API válidas, cuando hago GET a /api/v1/vehicles, entonces obtengo el listado paginado de vehículos del tenant.

- Dado que hago POST a /api/v1/vehicles con datos válidos, cuando se ejecuta el llamado, entonces se crea el vehículo y se devuelve su identificador único.

- Dado que excedo el rate limit de la API, cuando hago un nuevo llamado, entonces recibo error 429 con header Retry-After.

**Prioridad:** Could **│ Estimación:** 13 pts **│ Fase:** F5

**HU-E2-010 — Asignación de vendedor responsable**

Como ***Gerente de agencia***, quiero *asignar un vendedor responsable a cada vehículo*, para *saber quién es el dueño comercial de cada unidad y atribuir correctamente la productividad.*

**Criterios de aceptación:**

- Dado que estoy en la ficha del vehículo, cuando selecciono un vendedor de la sucursal, entonces queda asociado y los leads entrantes para ese vehículo se asignan a él por defecto.

- Dado que cambio el vendedor responsable, cuando guardo, entonces los leads ya asignados no migran automáticamente pero los nuevos van al nuevo vendedor.

**Prioridad:** Must **│ Estimación:** 3 pts **│ Fase:** F1

**Épica E3 — Publicación multicanal**

Esta épica es donde el SaaS materializa una de sus promesas centrales para el cliente: “cargá una vez, publicá en todos lados”. La integración con el portal de deRuedas se desarrolla en la fase uno; las integraciones con otros portales se incorporan progresivamente, comenzando por MercadoLibre Vehículos en la fase dos por su volumen de tráfico.

**HU-E3-001 — Publicación automática en deRuedas**

Como ***Vendedor***, quiero *que el vehículo cargado en el SaaS se publique automáticamente en el portal de deRuedas*, para *no tener que cargar el mismo vehículo en dos lugares.*

**Criterios de aceptación:**

- Dado que un vehículo pasa a estado “disponible”, cuando se completa el guardado, entonces se dispara automáticamente la publicación al portal de deRuedas con todos sus datos y fotos.

- Dado que la publicación se completa, cuando se actualiza, entonces la ficha del vehículo en el SaaS muestra el enlace público al aviso y su estado.

- Dado que edito un dato del vehículo, cuando guardo, entonces el aviso publicado se actualiza automáticamente sin intervención manual.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F1

**HU-E3-002 — Pausar y reanudar publicación**

Como ***Vendedor***, quiero *pausar la publicación de un vehículo sin sacarlo del stock*, para *manejar situaciones temporales como prueba de manejo prolongada o reserva sin perder el aviso.*

**Criterios de aceptación:**

- Dado que estoy en la ficha del vehículo, cuando pulso “Pausar publicación”, entonces el aviso se despublica de todos los portales pero el vehículo permanece en estado disponible internamente.

- Dado que un vehículo está pausado, cuando pulso “Reanudar publicación”, entonces el aviso se vuelve a publicar con los datos actuales en todos los portales activos.

**Prioridad:** Must **│ Estimación:** 3 pts **│ Fase:** F1

**HU-E3-003 — Publicación a MercadoLibre Vehículos**

Como ***Gerente de agencia***, quiero *publicar mis vehículos también en MercadoLibre Vehículos*, para *ampliar el alcance comercial sin esfuerzo adicional de carga.*

**Criterios de aceptación:**

- Dado que conecté mi cuenta de MercadoLibre y elegí qué plan usar, cuando un vehículo pasa a disponible, entonces se publica automáticamente en MercadoLibre con el plan configurado.

- Dado que MercadoLibre rechaza la publicación por algún motivo, cuando ocurre el rechazo, entonces el sistema notifica el motivo al vendedor y permite reintento manual.

- Dado que el vehículo se vende en MercadoLibre, cuando recibo notificación de venta vía API, entonces el sistema marca el vehículo como reservado e impide publicar nuevas operaciones sin confirmar.

**Prioridad:** Should **│ Estimación:** 13 pts **│ Fase:** F2

**HU-E3-004 — Publicación a Marketplace de Facebook**

Como ***Gerente de agencia***, quiero *publicar en Marketplace de Facebook desde el SaaS*, para *alcanzar el volumen de demanda informal sin tener que operar manualmente la red social.*

**Criterios de aceptación:**

- Dado que conecté mi página de Facebook y autoricé los permisos correspondientes, cuando publico un vehículo, entonces se genera automáticamente la publicación en Marketplace.

- Dado que recibo un mensaje desde Marketplace, cuando entra al sistema, entonces se asocia al vehículo correspondiente y aparece en la bandeja unificada.

**Prioridad:** Could **│ Estimación:** 13 pts **│ Fase:** F5

**HU-E3-005 — Vista de estado de publicaciones**

Como ***Vendedor***, quiero *ver en qué portales está publicado cada vehículo y con qué estado*, para *diagnosticar rápidamente cuando un aviso no aparece donde debería.*

**Criterios de aceptación:**

- Dado que estoy en la ficha del vehículo, cuando abro la pestaña “Publicaciones”, entonces veo el estado en cada portal (publicado, pausado, error, pendiente) con fecha de última actualización.

- Dado que un portal devolvió error, cuando hago click sobre el estado, entonces veo el detalle del error y opciones para reintentar o corregir.

**Prioridad:** Must **│ Estimación:** 3 pts **│ Fase:** F1

**HU-E3-006 — Plantillas de descripción**

Como ***Gerente de agencia***, quiero *crear plantillas de descripción reutilizables con variables*, para *que las publicaciones tengan un texto profesional consistente sin reescribir cada vez.*

**Criterios de aceptación:**

- Dado que estoy en “Configuración → Plantillas”, cuando creo una plantilla con variables como {{marca}} {{modelo}} {{año}} {{kilometraje}}, entonces queda disponible para asignar a vehículos.

- Dado que un vehículo usa una plantilla, cuando se publica, entonces las variables se reemplazan con los datos reales del vehículo en cada portal.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F2

**Épica E4 — CRM y pipeline comercial**

Esta épica es el segundo pilar del producto, junto con la gestión de stock. Su valor central es transformar contactos dispersos en oportunidades trazables, asegurar que ningún lead se pierda por falta de seguimiento y proveer al gerente visibilidad sobre el estado real del negocio. El pipeline configurable se introduce en la fase dos, después de validar el flujo básico en el MVP.

**HU-E4-001 — Captura automática de leads desde portales**

Como ***Vendedor***, quiero *que los leads de los portales conectados ingresen automáticamente al CRM*, para *no perder consultas por descargar manualmente desde cada portal.*

**Criterios de aceptación:**

- Dado que tengo conectados los portales, cuando un comprador deja una consulta sobre un vehículo, entonces se crea automáticamente un lead asociado al vehículo y al vendedor responsable.

- Dado que la consulta proviene de un comprador con datos coincidentes con un lead anterior, cuando ingresa la nueva consulta, entonces se asocia al lead existente como nueva interacción.

- Dado que ingresa un nuevo lead, cuando se crea, entonces el vendedor asignado recibe notificación push y por email.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F1

**HU-E4-002 — Captura manual de leads**

Como ***Vendedor***, quiero *crear manualmente un lead a partir de un contacto que llegó por teléfono o presencial*, para *registrar todas las consultas en el sistema, no solo las web.*

**Criterios de aceptación:**

- Dado que estoy en “CRM → Nuevo lead”, cuando ingreso datos de contacto y vehículo de interés, entonces se crea el lead y queda asociado a mí como vendedor.

- Dado que el contacto ingresado coincide con un lead existente, cuando guardo, entonces el sistema me ofrece asociar la nueva consulta al lead anterior en lugar de crear uno nuevo.

**Prioridad:** Must **│ Estimación:** 3 pts **│ Fase:** F1

**HU-E4-003 — Vista Kanban del pipeline**

Como ***Vendedor***, quiero *ver mis leads organizados en un tablero por etapa del pipeline*, para *tener visión rápida del estado de mis oportunidades y avanzar leads con drag and drop.*

**Criterios de aceptación:**

- Dado que estoy en “CRM → Pipeline”, cuando carga la pantalla, entonces veo columnas por cada etapa con tarjetas de leads ordenadas por antigüedad o valor potencial.

- Dado que arrastro una tarjeta a otra columna, cuando suelto, entonces el lead cambia de etapa y se registra el evento con fecha, hora y usuario.

- Dado que mi pipeline tiene más de cien leads, cuando carga la vista, entonces se aplica paginación o virtualización para mantener performance.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F1

**HU-E4-004 — Detalle del lead**

Como ***Vendedor***, quiero *ver toda la información del lead en una sola pantalla*, para *tener contexto completo antes de cualquier interacción comercial.*

**Criterios de aceptación:**

- Dado que abro un lead, cuando carga la pantalla, entonces veo datos de contacto, vehículo de interés, etapa actual, historial de interacciones, mensajes de WhatsApp y notas.

- Dado que ingreso una nota, cuando la guardo, entonces queda registrada con fecha, hora y autor en el historial.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F1

**HU-E4-005 — Reasignación de lead**

Como ***Gerente de agencia***, quiero *reasignar un lead de un vendedor a otro*, para *redistribuir carga cuando un vendedor está saturado o se ausenta.*

**Criterios de aceptación:**

- Dado que abro un lead, cuando cambio el vendedor asignado, entonces el lead pasa al nuevo vendedor y ambos reciben notificación.

- Dado que reasigno varios leads en lote, cuando confirmo la acción, entonces todos cambian de asignación atómicamente.

**Prioridad:** Must **│ Estimación:** 3 pts **│ Fase:** F1

**HU-E4-006 — Recordatorios automáticos de seguimiento**

Como ***Vendedor***, quiero *que el sistema me recuerde reseguir un lead que lleva días sin contacto*, para *no perder oportunidades por falta de seguimiento.*

**Criterios de aceptación:**

- Dado que un lead lleva más de tres días sin actividad en su etapa, cuando se ejecuta la rutina diaria, entonces se genera un recordatorio para el vendedor asignado.

- Dado que recibo un recordatorio, cuando ingreso al sistema, entonces lo veo destacado en el dashboard y en la tarjeta del lead en el pipeline.

- Dado que reseguí el lead, cuando registro la interacción, entonces el recordatorio se cierra automáticamente.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F2

**HU-E4-007 — Reglas de asignación automática**

Como ***Gerente de agencia***, quiero *configurar reglas de asignación automática de leads*, para *distribuir consultas de manera equitativa o según criterios de especialización.*

**Criterios de aceptación:**

- Dado que estoy en “Configuración → Reglas de asignación”, cuando defino criterios como round-robin, sucursal del vehículo, marca del vehículo o disponibilidad horaria del vendedor, entonces los leads nuevos se asignan según las reglas.

- Dado que ningún vendedor cumple los criterios, cuando ingresa un lead, entonces queda en bandeja “por asignar” y se notifica al gerente.

**Prioridad:** Should **│ Estimación:** 8 pts **│ Fase:** F2

**HU-E4-008 — Cierre de lead con motivo de pérdida**

Como ***Vendedor***, quiero *cerrar un lead como ganado o perdido indicando el motivo*, para *que la agencia pueda analizar las causas de pérdida y mejorar.*

**Criterios de aceptación:**

- Dado que estoy en un lead, cuando lo paso a estado “perdido”, entonces el sistema solicita seleccionar un motivo de una lista predefinida o ingresar uno personalizado.

- Dado que cierro un lead como ganado, cuando confirmo, entonces el sistema enlaza el lead con la operación de venta correspondiente y registra fecha de cierre.

- Dado que un gerente consulta los leads perdidos del mes, cuando filtra por motivo, entonces ve la distribución de pérdidas por causa.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F1

**HU-E4-009 — Etiquetado de leads**

Como ***Vendedor***, quiero *etiquetar leads con palabras clave personalizadas*, para *segmentar y filtrar mi cartera con criterios propios.*

**Criterios de aceptación:**

- Dado que abro un lead, cuando agrego una etiqueta, entonces queda asociada al lead y disponible para filtrar.

- Dado que filtro leads por etiqueta, cuando aplico el filtro, entonces veo solo los leads que la tienen.

**Prioridad:** Could **│ Estimación:** 3 pts **│ Fase:** F2

**HU-E4-010 — Identificación de leads duplicados**

Como ***Vendedor***, quiero *que el sistema detecte cuando un nuevo lead es probablemente el mismo contacto que uno existente*, para *evitar trabajar el mismo cliente en paralelo desde dos vendedores.*

**Criterios de aceptación:**

- Dado que ingresa un lead nuevo, cuando comparte teléfono, email o dominio del vehículo de interés con un lead existente activo, entonces el sistema lo marca como posible duplicado.

- Dado que un lead está marcado como duplicado, cuando lo abro, entonces puedo unirlo al lead original o descartarlo como falso positivo.

**Prioridad:** Should **│ Estimación:** 8 pts **│ Fase:** F2

**HU-E4-011 — Programación de actividades**

Como ***Vendedor***, quiero *agendar actividades futuras asociadas a un lead, como llamadas o pruebas de manejo*, para *no olvidar compromisos comerciales con clientes.*

**Criterios de aceptación:**

- Dado que estoy en un lead, cuando creo una actividad con tipo, fecha, hora y descripción, entonces queda visible en mi agenda y como recordatorio en el lead.

- Dado que se acerca el horario de una actividad, cuando faltan quince minutos, entonces recibo notificación push.

- Dado que completo una actividad, cuando la marco como hecha, entonces queda en el historial del lead con resultado opcional.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F2

**Épica E5 — Mensajería y WhatsApp Business**

WhatsApp es el canal dominante de comunicación comercial en agencias argentinas. La integración nativa con la API oficial de WhatsApp Business es uno de los diferenciales más valorados del producto frente a los CRM genéricos. La fase uno habilita recepción y respuesta manual; la fase dos incorpora templates aprobados, chatbot inicial y bandeja multi-vendedor.

**HU-E5-001 — Bandeja de entrada unificada**

Como ***Vendedor***, quiero *ver todas mis conversaciones de WhatsApp en una sola pantalla*, para *no tener que cambiar entre ventanas y mantener contexto.*

**Criterios de aceptación:**

- Dado que estoy en “Mensajes”, cuando carga la pantalla, entonces veo todas las conversaciones que me corresponden, ordenadas por última actividad.

- Dado que selecciono una conversación, cuando se abre, entonces veo el historial completo de mensajes y los datos del lead asociado en panel lateral.

- Dado que escribo un mensaje y lo envío, cuando se confirma, entonces queda registrado en el historial con timestamp y estado de entrega.

**Prioridad:** Must **│ Estimación:** 13 pts **│ Fase:** F1

**HU-E5-002 — Asociación automática de conversación a lead**

Como ***Vendedor***, quiero *que las conversaciones de WhatsApp se asocien automáticamente al lead correcto*, para *tener trazabilidad sin trabajo manual.*

**Criterios de aceptación:**

- Dado que ingresa un mensaje desde un número conocido, cuando el sistema lo recibe, entonces lo asocia al lead activo de ese contacto si existe.

- Dado que el número no coincide con ningún lead, cuando llega el mensaje, entonces se crea un lead nuevo y se asocia la conversación.

- Dado que un contacto tiene múltiples leads activos, cuando ingresa un mensaje, entonces el sistema asocia al lead más reciente y permite reasignar manualmente.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F1

**HU-E5-003 — Templates de mensaje aprobados**

Como ***Gerente de agencia***, quiero *crear y usar templates aprobados por Meta para mensajes salientes proactivos*, para *comunicar fuera de la ventana de veinticuatro horas y mantener buena reputación del número.*

**Criterios de aceptación:**

- Dado que estoy en “Configuración → Templates”, cuando creo un template y lo envío para aprobación, entonces queda en estado “pendiente” hasta que Meta lo aprueba o rechaza.

- Dado que un template está aprobado, cuando un vendedor inicia conversación con un cliente fuera de la ventana, entonces puede usar el template seleccionándolo de una lista.

- Dado que un template fue rechazado, cuando consulto su estado, entonces veo el motivo de rechazo y puedo editarlo y resubirlo.

**Prioridad:** Should **│ Estimación:** 8 pts **│ Fase:** F2

**HU-E5-004 — Chatbot de respuesta inicial**

Como ***Gerente de agencia***, quiero *configurar respuestas automáticas iniciales para consultas entrantes*, para *atender al cliente las veinticuatro horas y filtrar leads antes de que lleguen al vendedor.*

**Criterios de aceptación:**

- Dado que estoy en “Configuración → Chatbot”, cuando configuro un mensaje de bienvenida y respuestas a preguntas frecuentes como precio, kilometraje y disponibilidad, entonces el chatbot las responde automáticamente.

- Dado que el chatbot no puede responder, cuando detecta complejidad o el usuario pide hablar con un humano, entonces deriva la conversación al vendedor asignado e indica que está fuera del flujo automático.

- Dado que un mensaje fue respondido por chatbot, cuando aparece en la conversación, entonces se identifica visualmente como mensaje automático.

**Prioridad:** Should **│ Estimación:** 13 pts **│ Fase:** F2

**HU-E5-005 — Compartir conversaciones entre vendedores**

Como ***Gerente de agencia***, quiero *transferir una conversación de un vendedor a otro*, para *manejar ausencias o redistribución de carga sin perder el hilo.*

**Criterios de aceptación:**

- Dado que estoy en una conversación como gerente, cuando la transfiero a otro vendedor, entonces el nuevo vendedor recibe acceso completo al historial y notificación.

- Dado que el vendedor original tenía la conversación abierta, cuando se transfiere, entonces pierde acceso de escritura pero conserva acceso de lectura para referencia.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F2

**HU-E5-006 — Envío de archivos y multimedia**

Como ***Vendedor***, quiero *enviar fotos, videos y documentos por WhatsApp desde el SaaS*, para *compartir información completa del vehículo o documentación.*

**Criterios de aceptación:**

- Dado que estoy en una conversación, cuando adjunto una imagen, video o PDF, entonces se envía vía WhatsApp y queda en el historial visible para ambas partes.

- Dado que quiero enviar las fotos del vehículo del lead, cuando elijo “Compartir vehículo”, entonces el sistema arma un mensaje con título, precio y fotos principales y lo envía.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F1

**HU-E5-007 — Búsqueda en historial de mensajes**

Como ***Vendedor***, quiero *buscar texto dentro de las conversaciones*, para *encontrar rápidamente referencias de operaciones anteriores.*

**Criterios de aceptación:**

- Dado que estoy en “Mensajes”, cuando ingreso texto en el buscador, entonces el sistema busca en todas las conversaciones a las que tengo acceso y muestra coincidencias resaltadas.

- Dado que selecciono un resultado, cuando hago click, entonces se abre la conversación posicionada en el mensaje encontrado.

**Prioridad:** Could **│ Estimación:** 5 pts **│ Fase:** F2

**HU-E5-008 — Indicadores de leídos y respuesta**

Como ***Vendedor***, quiero *saber qué mensajes me llegaron y cuáles tengo pendientes de responder*, para *manejar mi volumen de conversaciones sin que se pierdan respuestas.*

**Criterios de aceptación:**

- Dado que ingresa un mensaje no leído, cuando entro a la bandeja, entonces lo veo destacado y la conversación queda al tope del listado.

- Dado que un mensaje del cliente queda sin responder más de una hora durante mi horario laboral, cuando ocurre el evento, entonces se marca con un indicador visual de “pendiente urgente”.

**Prioridad:** Must **│ Estimación:** 3 pts **│ Fase:** F1

**Épica E6 — Permutas**

La permuta es uno de los flujos más caóticos en una agencia tradicional y uno de los espacios donde el SaaS aporta más valor estructurando el proceso. Esta épica se desarrolla integralmente en la fase tres del roadmap. Incluye desde la solicitud inicial hasta la generación automática del nuevo registro de stock por el usado recibido.

**HU-E6-001 — Iniciar solicitud de permuta**

Como ***Vendedor***, quiero *registrar que un cliente quiere entregar un usado como parte de pago*, para *iniciar el flujo de valuación y negociación de la permuta.*

**Criterios de aceptación:**

- Dado que estoy en un lead, cuando indico que el cliente quiere permutar y completo datos básicos del usado (marca, modelo, año, kilometraje, dominio), entonces se crea una solicitud de permuta asociada al lead.

- Dado que la solicitud se crea, cuando consulto el lead, entonces veo el estado de la permuta como una sección destacada.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F3

**HU-E6-002 — Valuación con apoyo de mercado**

Como ***Vendedor***, quiero *que el sistema me sugiera un rango de valuación para el vehículo a recibir*, para *negociar con el cliente desde una referencia objetiva.*

**Criterios de aceptación:**

- Dado que tengo una solicitud de permuta con datos del usado, cuando consulto la valuación, entonces el sistema muestra rango sugerido con base en datos de mercado.

- Dado que ingreso datos adicionales como estado general, equipamiento o detalles, cuando recalculo, entonces el rango se ajusta.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F3

**HU-E6-003 — Inspección física del usado**

Como ***Vendedor***, quiero *registrar la inspección física del vehículo a recibir en permuta*, para *ajustar la valuación al estado real y dejar evidencia para la operación.*

**Criterios de aceptación:**

- Dado que tengo una permuta en curso, cuando completo el formulario de inspección con campos sobre estado mecánico, eléctrico, carrocería, kilometraje verificado y detalles, entonces queda registrada en el sistema.

- Dado que adjunto fotos a la inspección, cuando guardo, entonces las fotos quedan asociadas al registro de inspección.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F3

**HU-E6-004 — Propuesta formal al cliente**

Como ***Vendedor***, quiero *generar una propuesta formal de permuta con valuación final y números de la operación*, para *que el cliente vea con claridad la composición del precio total.*

**Criterios de aceptación:**

- Dado que tengo valuación e inspección completas, cuando genero la propuesta, entonces el sistema produce un documento PDF con datos de ambos vehículos, valuación, saldo a pagar y condiciones.

- Dado que el cliente acepta la propuesta, cuando registro la aceptación, entonces la permuta avanza a estado “aceptada” y queda lista para cierre.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F3

**HU-E6-005 — Cierre de permuta y alta automática de stock**

Como ***Administrativo***, quiero *que al cerrar una permuta se cree automáticamente el registro de stock del usado recibido*, para *evitar doble carga y mantener trazabilidad bidireccional.*

**Criterios de aceptación:**

- Dado que cierro una permuta, cuando confirmo el cierre, entonces se crea automáticamente un nuevo vehículo en stock en estado “en preparación” con los datos del usado recibido.

- Dado que se crea el nuevo stock, cuando lo abro, entonces veo el enlace a la permuta original y a la operación de venta del vehículo entregado.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F3

**HU-E6-006 — Histórico de permutas**

Como ***Gerente de agencia***, quiero *consultar el historial de permutas realizadas*, para *analizar volumen, valuaciones promedio y rotación del inventario originado en permutas.*

**Criterios de aceptación:**

- Dado que estoy en “Permutas”, cuando filtro por periodo y estado, entonces veo el listado con datos relevantes y opción de exportar.

- Dado que abro una permuta histórica, cuando la consulto, entonces veo todo el flujo desde solicitud hasta cierre con sus documentos asociados.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F4

**HU-E6-007 — Permuta múltiple**

Como ***Vendedor***, quiero *manejar permutas donde un cliente entrega más de un vehículo*, para *atender casos del segmento empresa o particulares con múltiples unidades.*

**Criterios de aceptación:**

- Dado que tengo una solicitud de permuta, cuando agrego un segundo vehículo a entregar por el cliente, entonces el sistema permite valuación y propuesta consolidada.

- Dado que la permuta múltiple se cierra, cuando confirmo, entonces se generan automáticamente registros de stock para cada vehículo recibido.

**Prioridad:** Could **│ Estimación:** 8 pts **│ Fase:** F5

**Épica E7 — Financiación integrada**

La financiación integrada es uno de los motores de mayor captura de valor del producto y, a la vez, una de las funcionalidades más atractivas para el cliente final del comprador, que multiplica la tasa de conversión de leads. Su implementación depende de los acuerdos comerciales con financieras, que deben preceder al desarrollo técnico. La épica se concentra en fase tres.

**HU-E7-001 — Conexión con financiera**

Como ***Customer Success Manager***, quiero *configurar la integración del SaaS con una financiera específica*, para *habilitar la oferta de crédito a las agencias clientes.*

**Criterios de aceptación:**

- Dado que estoy en el backoffice, cuando configuro las credenciales de API de una financiera nueva, entonces queda disponible para activarla en cualquier tenant.

- Dado que un tenant activa una financiera, cuando se aplica la activación, entonces los vendedores pueden usarla en simulaciones y solicitudes.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F3

**HU-E7-002 — Precalificación crediticia rápida**

Como ***Vendedor***, quiero *precalificar a un comprador con datos básicos sin lanzar solicitud formal*, para *saber rápidamente si la operación es financieramente viable.*

**Criterios de aceptación:**

- Dado que estoy en un lead, cuando ingreso DNI, ingresos declarados y monto a financiar, entonces el sistema consulta a las financieras integradas y devuelve resultado de precalificación en menos de treinta segundos.

- Dado que la precalificación es positiva, cuando se completa, entonces veo qué financieras están dispuestas a operar y con qué condiciones aproximadas.

- Dado que la precalificación es negativa en todas las financieras, cuando se completa, entonces el sistema sugiere alternativas como mayor entrega, plazo más largo o cambio de vehículo.

**Prioridad:** Must **│ Estimación:** 13 pts **│ Fase:** F3

**HU-E7-003 — Comparación de ofertas de crédito**

Como ***Vendedor***, quiero *comparar las ofertas de las distintas financieras lado a lado*, para *ofrecer al cliente la mejor opción objetivamente.*

**Criterios de aceptación:**

- Dado que tengo precalificaciones de múltiples financieras, cuando consulto la comparación, entonces veo en una tabla cuota, plazo, tasa nominal anual, tasa efectiva y costo financiero total de cada oferta.

- Dado que el cliente elige una oferta, cuando la marco como seleccionada, entonces se habilita la solicitud formal con esa financiera.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F3

**HU-E7-004 — Solicitud formal de crédito**

Como ***Administrativo***, quiero *lanzar la solicitud formal de crédito a la financiera elegida*, para *formalizar la operación crediticia con la documentación correcta.*

**Criterios de aceptación:**

- Dado que tengo oferta seleccionada, cuando inicio solicitud formal, entonces el sistema solicita los documentos requeridos por la financiera (DNI, recibo de sueldo, comprobantes) y los envía vía API.

- Dado que la financiera responde con observaciones, cuando llegan, entonces se registran en el lead y se notifica al vendedor y administrativo.

- Dado que la financiera aprueba, cuando llega la aprobación, entonces se notifica al cliente y se generan los documentos para firma.

**Prioridad:** Must **│ Estimación:** 13 pts **│ Fase:** F3

**HU-E7-005 — Seguimiento de estado de solicitud**

Como ***Administrativo***, quiero *ver el estado actualizado de cada solicitud de crédito en curso*, para *no perder de vista operaciones que dependen de aprobación crediticia.*

**Criterios de aceptación:**

- Dado que estoy en “Financiación → Solicitudes”, cuando carga la pantalla, entonces veo todas las solicitudes con estado, financiera, fecha de inicio, próxima acción y responsable.

- Dado que una solicitud cambia de estado en la financiera, cuando llega el evento vía API, entonces se actualiza automáticamente en el sistema y se notifica al responsable.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F3

**HU-E7-006 — Firma electrónica de documentos**

Como ***Administrativo***, quiero *que el cliente firme los documentos del crédito electrónicamente*, para *evitar idas y vueltas físicas y acelerar el cierre.*

**Criterios de aceptación:**

- Dado que la solicitud está aprobada, cuando solicito firma, entonces el cliente recibe link por email y WhatsApp para firmar los documentos.

- Dado que el cliente firma, cuando se completa, entonces los documentos firmados quedan disponibles en gestión documental y se notifica al administrativo.

**Prioridad:** Should **│ Estimación:** 13 pts **│ Fase:** F3

**HU-E7-007 — Reporte de comisiones de originación**

Como ***Gerente de agencia***, quiero *ver el reporte de operaciones financiadas y las comisiones generadas*, para *controlar los ingresos por intermediación crediticia y la salud del canal.*

**Criterios de aceptación:**

- Dado que estoy en “Financiación → Reportes”, cuando filtro por periodo, entonces veo total de operaciones financiadas, monto total, tasa de aprobación y comisión correspondiente.

- Dado que exporto el reporte, cuando elijo formato, entonces puedo descargar Excel o PDF con el detalle.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F4

**HU-E7-008 — Simulador público de crédito**

Como ***Comprador***, quiero *simular un crédito desde una landing pública sin estar logueado*, para *evaluar viabilidad antes de iniciar el contacto con la agencia.*

**Criterios de aceptación:**

- Dado que estoy en una landing pública del vehículo, cuando ingreso entrega y plazo deseado, entonces veo cuotas estimadas con condiciones vigentes.

- Dado que decido avanzar, cuando completo formulario de contacto, entonces se crea un lead en la agencia con la simulación adjunta.

**Prioridad:** Could **│ Estimación:** 8 pts **│ Fase:** F5

**Épica E8 — Gestión documental**

La gestión documental ataca uno de los puntos de dolor menos visibles pero más persistentes de las agencias: la dispersión y pérdida de documentación crítica. La épica se desarrolla en fase cuatro y combina almacenamiento estructurado con OCR para auto-clasificación, búsqueda full-text y, opcionalmente, firma electrónica.

**HU-E8-001 — Carga de documentos del vehículo**

Como ***Administrativo***, quiero *subir los documentos legales y técnicos de cada vehículo*, para *tener en un solo lugar toda la documentación necesaria para vender.*

**Criterios de aceptación:**

- Dado que abro un vehículo, cuando subo un documento (tarjeta verde, formulario 08, certificado de transferencia, libre deuda) en PDF o imagen, entonces queda asociado al vehículo y categorizado.

- Dado que subo desde el celular, cuando elijo “Tomar foto del documento”, entonces se aplica auto-recorte y mejora de imagen antes de guardar.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F4

**HU-E8-002 — OCR y auto-clasificación**

Como ***Administrativo***, quiero *que el sistema reconozca automáticamente el tipo de documento que cargué*, para *no perder tiempo categorizando manualmente cada archivo.*

**Criterios de aceptación:**

- Dado que subo un documento, cuando se procesa, entonces el sistema aplica OCR e intenta identificar el tipo (tarjeta verde, libre deuda, etc.) sugiriendo categoría.

- Dado que el sistema acierta, cuando reviso el documento, entonces puedo confirmar la categoría con un click.

- Dado que el sistema no logra identificar, cuando se procesa, entonces queda en categoría “por clasificar” y debo asignarla manualmente.

**Prioridad:** Should **│ Estimación:** 13 pts **│ Fase:** F4

**HU-E8-003 — Alertas de vencimiento**

Como ***Administrativo***, quiero *recibir alertas anticipadas cuando un documento de un vehículo en stock va a vencer*, para *renovar documentación antes de que afecte la posibilidad de vender.*

**Criterios de aceptación:**

- Dado que un documento tiene fecha de vencimiento registrada, cuando faltan treinta días, entonces el sistema genera alerta visible en el dashboard.

- Dado que el documento vence en menos de cinco días, cuando se ejecuta la rutina, entonces se envía notificación urgente al administrativo.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F4

**HU-E8-004 — Búsqueda full-text**

Como ***Administrativo***, quiero *buscar texto dentro del contenido de los documentos cargados*, para *encontrar rápidamente referencias específicas sin abrir archivo por archivo.*

**Criterios de aceptación:**

- Dado que estoy en “Documentos”, cuando ingreso texto en el buscador, entonces el sistema busca en el contenido OCRizado de todos los documentos a los que tengo acceso.

- Dado que aparecen resultados, cuando selecciono uno, entonces se abre el documento en la página o sección con la coincidencia resaltada.

**Prioridad:** Should **│ Estimación:** 8 pts **│ Fase:** F4

**HU-E8-005 — Paquete documental para registro**

Como ***Administrativo***, quiero *generar un paquete con todos los documentos necesarios para presentar en registro automotor*, para *ahorrar tiempo en la preparación de carpetas físicas o digitales.*

**Criterios de aceptación:**

- Dado que tengo una operación cerrada, cuando solicito “Paquete documental”, entonces el sistema arma un PDF unificado con todos los documentos del vehículo y la operación en orden.

- Dado que falta algún documento obligatorio, cuando intento generar el paquete, entonces el sistema me indica cuáles faltan antes de generar.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F4

**HU-E8-006 — Firma electrónica básica**

Como ***Administrativo***, quiero *solicitar firma electrónica al cliente sobre documentos de la operación*, para *evitar coordinar firmas presenciales y reducir tiempos de cierre.*

**Criterios de aceptación:**

- Dado que tengo un documento listo, cuando solicito firma, entonces el cliente recibe link y firma desde su dispositivo con validación de identidad.

- Dado que el cliente firma, cuando se completa, entonces el documento firmado queda en el sistema con sello de tiempo y queda visible para el administrativo.

**Prioridad:** Could **│ Estimación:** 13 pts **│ Fase:** F5

**HU-E8-007 — Documentación del cliente comprador**

Como ***Administrativo***, quiero *almacenar la documentación del cliente (DNI, recibos, comprobantes)*, para *tener todo lo necesario para una operación o crédito en un solo lugar.*

**Criterios de aceptación:**

- Dado que estoy en un lead u operación, cuando subo documentos del cliente, entonces quedan asociados al cliente y a la operación.

- Dado que el mismo cliente vuelve a operar, cuando creo una nueva operación, entonces el sistema sugiere reutilizar los documentos previos vigentes.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F4

**Épica E9 — Cuenta corriente y conciliación**

Esta épica cubre las necesidades financieras básicas de la agencia sin pretender ser un ERP completo. El alcance se limita deliberadamente a los flujos directamente vinculados a operaciones de venta y compra de vehículos, dejando explícitamente fuera la gestión contable plena, los libros legales y la liquidación impositiva, que se delegan en sistemas externos integrados.

**HU-E9-001 — Registro de cobros de operación**

Como ***Administrativo***, quiero *registrar los cobros recibidos por una operación de venta*, para *llevar control del cobro completo de la operación, incluyendo señas y pagos parciales.*

**Criterios de aceptación:**

- Dado que tengo una operación abierta, cuando registro un cobro con monto, fecha, medio de pago y comprobante, entonces se asocia a la operación y suma al total cobrado.

- Dado que registro un cobro en moneda extranjera, cuando guardo, entonces el sistema permite registrar la cotización aplicada y mantiene ambos montos.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F4

**HU-E9-002 — Cuenta corriente de cliente**

Como ***Administrativo***, quiero *ver la cuenta corriente de cada cliente con saldo, movimientos y estado*, para *saber cuánto debe o tiene a favor cada cliente sin dudas.*

**Criterios de aceptación:**

- Dado que abro la ficha de un cliente, cuando consulto la cuenta corriente, entonces veo saldo actual, listado de operaciones y movimientos en orden cronológico.

- Dado que un cliente tiene saldo a favor, cuando inicio una nueva operación con él, entonces el sistema sugiere aplicar el saldo a favor.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F4

**HU-E9-003 — Conciliación con extracto bancario**

Como ***Administrativo***, quiero *subir el extracto bancario y conciliar movimientos con cobros registrados*, para *asegurar que los registros del sistema reflejen lo que efectivamente entró al banco.*

**Criterios de aceptación:**

- Dado que estoy en “Conciliación”, cuando subo extracto en formato CSV o Excel, entonces el sistema intenta matchear automáticamente cada movimiento con cobros del sistema.

- Dado que un movimiento del extracto no tiene match automático, cuando lo reviso, entonces puedo asociarlo manualmente o marcarlo como “no corresponde a operación”.

- Dado que termino la conciliación, cuando consulto el reporte, entonces veo total conciliado, no conciliado y diferencias.

**Prioridad:** Should **│ Estimación:** 13 pts **│ Fase:** F4

**HU-E9-004 — Generación de comprobantes de pago**

Como ***Administrativo***, quiero *generar un comprobante de pago para entregar al cliente*, para *que el cliente tenga constancia formal del pago realizado.*

**Criterios de aceptación:**

- Dado que registro un cobro, cuando genero el comprobante, entonces el sistema produce un PDF con datos de la agencia, cliente, operación, monto y forma de pago.

- Dado que el comprobante se genera, cuando termino, entonces puedo enviarlo por email o WhatsApp al cliente directamente desde el sistema.

**Prioridad:** Must **│ Estimación:** 3 pts **│ Fase:** F4

**HU-E9-005 — Exportación a contabilidad**

Como ***Administrativo***, quiero *exportar los movimientos del periodo a un sistema contable externo*, para *que el contador tenga la información necesaria sin doble carga.*

**Criterios de aceptación:**

- Dado que estoy en “Exportar”, cuando elijo periodo y formato (Tango, Bejerman o Excel genérico), entonces se genera archivo descargable con los movimientos del periodo.

- Dado que ya exporté un periodo, cuando consulto, entonces veo histórico de exportaciones realizadas para evitar duplicaciones.

**Prioridad:** Should **│ Estimación:** 8 pts **│ Fase:** F4

**HU-E9-006 — Pagos a proveedores**

Como ***Administrativo***, quiero *registrar pagos a proveedores como talleres, financieras o terminales*, para *tener visibilidad completa del flujo de caja de la agencia.*

**Criterios de aceptación:**

- Dado que estoy en “Pagos”, cuando registro un pago con proveedor, monto, fecha y concepto, entonces se asocia al periodo y suma a las salidas.

- Dado que el pago es por un servicio asociado a un vehículo (taller), cuando vinculo, entonces el costo queda imputado al vehículo y al cálculo de margen final.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F4

**HU-E9-007 — Cálculo de margen por operación**

Como ***Gerente de agencia***, quiero *ver el margen real obtenido en cada operación de venta*, para *tomar decisiones de pricing y rotación con datos objetivos.*

**Criterios de aceptación:**

- Dado que una operación se cierra, cuando consulto su detalle, entonces veo precio de venta, costo de adquisición, gastos imputados (taller, comisiones, financieras) y margen bruto.

- Dado que filtro el reporte de operaciones por periodo, cuando consulto, entonces veo margen agregado y promedio por marca, modelo y vendedor.

**Prioridad:** Should **│ Estimación:** 8 pts **│ Fase:** F4

**Épica E10 — Business intelligence**

Esta épica consolida los datos de los demás módulos en dashboards y reportes accionables. Su valor para el cliente está principalmente del lado del gerente o dueño, que finalmente puede tomar decisiones basadas en datos en lugar de intuición. Se desarrolla en fase cuatro, cuando ya hay suficiente volumen histórico para que los reportes tengan valor real.

**HU-E10-001 — Dashboard de stock**

Como ***Gerente de agencia***, quiero *ver un panel consolidado del estado del stock*, para *saber al instante composición, antigüedad y rotación del inventario.*

**Criterios de aceptación:**

- Dado que ingreso al dashboard de stock, cuando carga, entonces veo totales por estado, distribución por marca y rango de precio, antigüedad promedio en stock y vehículos con rotación lenta destacados.

- Dado que aplico filtros por sucursal o vendedor, cuando los aplico, entonces el dashboard se recalcula con esos parámetros.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F4

**HU-E10-002 — Dashboard de pipeline**

Como ***Gerente de agencia***, quiero *ver un panel del pipeline comercial agregado*, para *entender la salud del embudo y dónde se traban los leads.*

**Criterios de aceptación:**

- Dado que ingreso al dashboard de pipeline, cuando carga, entonces veo cantidad de leads por etapa, valor potencial agregado, tasa de conversión por etapa y tiempo promedio en cada etapa.

- Dado que veo una etapa con tiempo promedio anómalo, cuando hago click, entonces accedo al listado de leads en esa etapa para diagnóstico.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F4

**HU-E10-003 — Dashboard de ventas**

Como ***Gerente de agencia***, quiero *ver un panel de ventas con KPIs comerciales del periodo*, para *evaluar performance del periodo y comparar con periodos anteriores.*

**Criterios de aceptación:**

- Dado que ingreso al dashboard de ventas, cuando carga, entonces veo cantidad y monto total de ventas del mes, ticket promedio, comparación con mes anterior y mes del año previo.

- Dado que cambio el rango temporal, cuando aplico, entonces los KPIs se recalculan dinámicamente.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F4

**HU-E10-004 — Dashboard de productividad**

Como ***Gerente de agencia***, quiero *ver el rendimiento individual de cada vendedor*, para *identificar quién está vendiendo bien y quién necesita apoyo o capacitación.*

**Criterios de aceptación:**

- Dado que ingreso al dashboard de productividad, cuando carga, entonces veo por vendedor los leads asignados, tasa de conversión, ventas cerradas, ticket promedio y tiempo promedio de cierre.

- Dado que comparo dos vendedores, cuando los selecciono, entonces el dashboard los muestra lado a lado.

**Prioridad:** Should **│ Estimación:** 8 pts **│ Fase:** F4

**HU-E10-005 — Dashboard financiero**

Como ***Gerente de agencia***, quiero *ver un panel del estado financiero básico de la agencia*, para *tener visión rápida del flujo y de las cuentas por cobrar y pagar.*

**Criterios de aceptación:**

- Dado que ingreso al dashboard financiero, cuando carga, entonces veo cobros y pagos del periodo, cuentas por cobrar agrupadas por antigüedad, cuentas por pagar y saldo aproximado.

- Dado que tengo cuentas por cobrar muy vencidas, cuando ingreso al dashboard, entonces se destacan visualmente para acción.

**Prioridad:** Should **│ Estimación:** 8 pts **│ Fase:** F4

**HU-E10-006 — Reportes personalizables**

Como ***Gerente de agencia***, quiero *construir reportes a medida con campos y filtros que elija*, para *responder preguntas específicas que los reportes estándar no cubren.*

**Criterios de aceptación:**

- Dado que estoy en “Reportes → Nuevo reporte personalizado”, cuando selecciono campos, filtros, agrupaciones y orden, entonces el sistema arma el reporte y lo muestra en pantalla.

- Dado que un reporte me resulta útil, cuando lo guardo, entonces queda disponible en “Mis reportes” para futuras consultas.

**Prioridad:** Could **│ Estimación:** 13 pts **│ Fase:** F5

**HU-E10-007 — Exportación de reportes**

Como ***Gerente de agencia***, quiero *exportar cualquier reporte o vista del sistema a Excel o PDF*, para *compartir información con socios, auditores o asesores externos.*

**Criterios de aceptación:**

- Dado que estoy en cualquier reporte o listado, cuando elijo “Exportar”, entonces el sistema genera archivo descargable con los datos de la vista actual.

- Dado que el volumen es grande, cuando se procesa, entonces la exportación se hace en background y se notifica cuando está lista.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F4

**HU-E10-008 — Reporte de canales de origen de leads**

Como ***Gerente de agencia***, quiero *ver de qué canal vinieron mis leads y cuál convierte mejor*, para *asignar mejor el presupuesto de marketing a los canales más efectivos.*

**Criterios de aceptación:**

- Dado que estoy en el reporte de canales, cuando selecciono periodo, entonces veo tabla con cantidad de leads, conversión, ticket promedio y costo por lead por cada canal.

- Dado que un canal tiene costo registrado, cuando consulto, entonces puedo ver retorno de inversión por canal.

**Prioridad:** Should **│ Estimación:** 8 pts **│ Fase:** F4

**Épica E11 — Aplicación móvil**

La aplicación móvil es indispensable para los vendedores que trabajan en piso de venta y para los gerentes que necesitan visibilidad fuera de la oficina. Comparte la base funcional con la web pero prioriza las funciones de uso intensivo en movilidad: carga de stock con cámara, gestión de leads, mensajería y consulta de dashboards. Se desarrolla en paralelo con la fase tres y alcanza paridad funcional al cierre de la fase cuatro.

**HU-E11-001 — Login y sesión persistente en móvil**

Como ***Vendedor***, quiero *ingresar a la app desde mi celular y mantener sesión*, para *no tener que loguearme cada vez que abro la app.*

**Criterios de aceptación:**

- Dado que descargo la app y abro por primera vez, cuando ingreso credenciales, entonces puedo loguearme y la sesión se mantiene activa hasta logout explícito.

- Dado que tengo biometría disponible en mi dispositivo, cuando configuro huella o face id, entonces puedo desbloquear la app sin escribir contraseña.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F3

**HU-E11-002 — Carga de vehículo desde celular con cámara**

Como ***Vendedor***, quiero *cargar un vehículo nuevo en stock desde la app del celular usando la cámara*, para *ahorrar tiempo cuando estoy revisando un auto y no necesito volver a la computadora.*

**Criterios de aceptación:**

- Dado que estoy en la app, cuando inicio carga de vehículo, entonces puedo tomar fotos directamente con la cámara del celular y se asocian al vehículo.

- Dado que escaneo el dominio del auto con la cámara, cuando se procesa, entonces el sistema sugiere precarga de marca, modelo y año si tiene match en su base de datos.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F3

**HU-E11-003 — Gestión de leads en móvil**

Como ***Vendedor***, quiero *ver y gestionar mis leads desde el celular*, para *trabajar mientras estoy fuera del local o atendiendo un comprador.*

**Criterios de aceptación:**

- Dado que abro la app, cuando entro a leads, entonces veo mi pipeline en formato adaptado a pantalla chica con cards.

- Dado que abro un lead, cuando registro una nota o cambio de etapa, entonces se sincroniza inmediatamente con la web.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F3

**HU-E11-004 — Notificaciones push**

Como ***Vendedor***, quiero *recibir notificaciones push en mi celular ante eventos relevantes*, para *no perderme leads nuevos, mensajes urgentes o recordatorios.*

**Criterios de aceptación:**

- Dado que la app tiene permisos de notificación, cuando ingresa un lead, mensaje o recordatorio que me corresponde, entonces recibo push con resumen.

- Dado que toco la notificación, cuando se abre, entonces voy directo a la pantalla relevante dentro de la app.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F3

**HU-E11-005 — Dashboard móvil para gerente**

Como ***Gerente de agencia***, quiero *consultar los dashboards principales desde mi celular*, para *tener visibilidad cuando estoy fuera de la agencia.*

**Criterios de aceptación:**

- Dado que abro la app, cuando ingreso al dashboard, entonces veo versión optimizada para móvil con KPIs principales de stock, pipeline, ventas y financiero.

- Dado que toco un KPI, cuando se expande, entonces accedo al detalle correspondiente.

**Prioridad:** Should **│ Estimación:** 5 pts **│ Fase:** F4

**HU-E11-006 — Mensajería en móvil**

Como ***Vendedor***, quiero *responder WhatsApp y otros mensajes desde la app*, para *no tener que cambiar entre apps cuando estoy con un cliente.*

**Criterios de aceptación:**

- Dado que abro la app, cuando entro a mensajes, entonces veo bandeja unificada en formato móvil.

- Dado que respondo un mensaje, cuando se envía, entonces el comportamiento es idéntico al de la versión web.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F3

**Épica E12 — Administración y soporte (deRuedas)**

Esta épica cubre las herramientas internas que el equipo de deRuedas utiliza para operar el SaaS: gestión de tenants, configuración de planes y precios, soporte interno, monitoreo de salud técnica y de adopción comercial. Es invisible para el cliente pero crítica para el equipo de Customer Success y para la sostenibilidad operativa del producto.

**HU-E12-001 — Listado y búsqueda de tenants**

Como ***Customer Success Manager***, quiero *ver el listado de todas las cuentas de agencia con sus datos clave*, para *tener acceso rápido a cualquier cliente para soporte o seguimiento.*

**Criterios de aceptación:**

- Dado que ingreso al backoffice, cuando carga la pantalla, entonces veo listado de tenants con nombre, plan, estado, fecha de alta, última actividad y vendedores activos.

- Dado que busco por nombre, CUIT o email, cuando ingreso el texto, entonces el sistema filtra resultados en tiempo real.

**Prioridad:** Must **│ Estimación:** 5 pts **│ Fase:** F1

**HU-E12-002 — Vista detallada de tenant**

Como ***Customer Success Manager***, quiero *ver el detalle completo de una cuenta de agencia*, para *diagnosticar el estado de adopción y problemas potenciales.*

**Criterios de aceptación:**

- Dado que abro un tenant, cuando carga, entonces veo configuración, sucursales, usuarios, integraciones activas, métricas de uso, estado de pagos y tickets abiertos.

- Dado que necesito intervenir, cuando hago “impersonar usuario”, entonces accedo a la cuenta del cliente con marca de auditoría visible.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F1

**HU-E12-003 — Gestión de planes y precios**

Como ***Super Admin***, quiero *configurar los planes disponibles, sus precios y funcionalidades incluidas*, para *ajustar la oferta comercial sin necesidad de despliegue de código.*

**Criterios de aceptación:**

- Dado que estoy en “Planes”, cuando creo o edito un plan con sus límites de usuarios, vehículos, módulos habilitados y precio, entonces queda disponible para asignar a tenants.

- Dado que cambio el precio de un plan, cuando guardo, entonces se aplica a nuevos tenants pero los existentes mantienen su precio hasta renovación.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F1

**HU-E12-004 — Gestión de tickets de soporte**

Como ***Customer Success Manager***, quiero *atender los tickets de soporte abiertos por agencias*, para *resolver consultas e incidencias con trazabilidad.*

**Criterios de aceptación:**

- Dado que un cliente abre un ticket, cuando ingresa al sistema, entonces aparece en mi bandeja de tickets y se asigna según reglas configuradas.

- Dado que respondo un ticket, cuando envío, entonces el cliente recibe email y notificación in-app, y queda registrado el intercambio en el historial.

- Dado que cierro un ticket, cuando confirmo, entonces se solicita encuesta de satisfacción al cliente.

**Prioridad:** Must **│ Estimación:** 8 pts **│ Fase:** F1

**HU-E12-005 — Métricas de salud de tenant**

Como ***Customer Success Manager***, quiero *ver indicadores tempranos de churn riesgoso por tenant*, para *intervenir antes de que un cliente se vaya.*

**Criterios de aceptación:**

- Dado que un tenant tiene caída sostenida en uso (login, vehículos cargados, leads gestionados) en las últimas dos semanas, cuando se ejecuta la rutina, entonces aparece en mi tablero de “atención requerida”.

- Dado que un tenant cumple criterios de “saludable”, cuando consulto, entonces aparece en categoría “estable” y libera mi atención.

**Prioridad:** Should **│ Estimación:** 13 pts **│ Fase:** F4

**HU-E12-006 — Monitoreo técnico del sistema**

Como ***Super Admin***, quiero *ver el estado técnico de la plataforma en tiempo real*, para *identificar y resolver problemas de infraestructura antes de que afecten masivamente.*

**Criterios de aceptación:**

- Dado que ingreso al panel de monitoreo, cuando carga, entonces veo estado de servicios, latencia promedio, errores recientes, uso de recursos y alertas activas.

- Dado que hay una alerta crítica, cuando ingreso al sistema, entonces se destaca con color y notificación push al equipo de guardia.

**Prioridad:** Should **│ Estimación:** 13 pts **│ Fase:** F2

**4. Backlog priorizado por fase**

La tabla siguiente sintetiza la distribución de las noventa y dos historias entre las cinco fases del roadmap, mostrando la cantidad por épica y por fase. Este corte permite planificar capacidad de desarrollo, validar que las dependencias entre módulos están respetadas (por ejemplo, financiación depende de leads que dependen de stock que depende de onboarding) y asegurar que el alcance del MVP es realista.

|  |  |  |  |  |  |
|:---|:--:|:--:|:--:|:--:|:--:|
| **Épica** | **F1 MVP** | **F2 CRM avz** | **F3 Permu/Fin** | **F4 Doc/BI** | **F5 Ecosist** |
| E1 Onboarding | 6 | 2 |  |  |  |
| E2 Stock | 7 | 2 |  | 1 |  |
| E3 Publicación multicanal | 3 | 2 |  |  | 1 |
| E4 CRM | 6 | 5 |  |  |  |
| E5 WhatsApp | 4 | 4 |  |  |  |
| E6 Permutas |  |  | 5 | 1 | 1 |
| E7 Financiación |  |  | 6 | 1 | 1 |
| E8 Documental |  |  |  | 6 | 1 |
| E9 Cuenta corriente |  |  |  | 7 |  |
| E10 BI |  |  |  | 7 | 1 |
| E11 Mobile |  |  | 5 | 1 |  |
| E12 Admin | 4 | 1 |  | 1 |  |
| **Total por fase** | **30** | **16** | **16** | **25** | **5** |

La fase uno concentra treinta historias, la mayoría Must, lo que es coherente con la naturaleza fundacional del MVP. La fase dos suma dieciséis historias, mayoritariamente Should, que profundizan los módulos centrales sin agregar verticales nuevas. Las fases tres y cuatro suman cuarenta y una historias entre ambas, donde aparecen las verticales más diferenciadoras (permutas, financiación, BI). La fase cinco se reserva para iniciativas de plataformización y ecosistema, y deliberadamente queda con pocas historias detalladas en este documento porque su definición concreta debe surgir del feedback de operación de las fases previas.

**5. Definición de “terminado”**

Toda historia se considera completada cuando cumple los criterios siguientes, además de los criterios de aceptación específicos. Esta lista se aplica de manera uniforme a todas las historias del backlog y se utiliza como checklist en las ceremonias de review.

- Funcional: la historia cumple todos sus criterios de aceptación verificados con pruebas manuales o automatizadas.

- Calidad de código: el código pasa el linter, las pruebas unitarias del módulo afectado y la cobertura no decrece respecto del baseline.

- Pruebas automatizadas: cada historia agrega al menos una prueba end-to-end que cubre el flujo principal y al menos una prueba unitaria por nueva regla de negocio.

- Documentación: el endpoint de API, el cambio de modelo de datos o el flujo de UI quedan documentados en la wiki técnica del producto.

- Accesibilidad: las pantallas nuevas cumplen con los estándares mínimos WCAG 2.1 nivel AA en contraste, navegación por teclado y etiquetas ARIA.

- Rendimiento: las consultas de listado nuevas tienen tiempo de respuesta inferior a doscientos milisegundos para volúmenes representativos del p95 de los tenants.

- Multi-tenancy: cada query incluye la condición de tenant correspondiente y queda cubierta por las políticas de seguridad a nivel de fila.

- Internacionalización: todos los textos visibles para el usuario están en archivos de traducción y no codificados directamente.

- Seguridad: las nuevas endpoints pasan la revisión de checklist OWASP top diez y, si manejan datos sensibles, se documentan los flujos de tratamiento.

- Despliegue: la historia llega a producción mediante el pipeline de despliegue continuo y queda disponible detrás de un feature flag controlable por tenant.

- Observabilidad: los nuevos eventos de negocio relevantes son registrados en el sistema de telemetría y disponibles en los dashboards operativos.

**Cierre**

Este backlog constituye el insumo de partida para iniciar la planificación detallada del producto. Es deliberadamente extenso pero no exhaustivo: muchas historias surgirán durante el descubrimiento con usuarios reales, otras serán reescritas o consolidadas en sesiones de refinement, y algunas serán descartadas cuando confronten con la realidad de los primeros clientes. Como toda lista viva de producto, su valor está en abrir conversaciones, no en cerrarlas. Los noventa y dos elementos aquí descriptos representan el alcance proyectado para los primeros dieciocho meses de desarrollo y son consistentes con los recursos, la economía y los plazos del plan estratégico del que este documento es complemento.
