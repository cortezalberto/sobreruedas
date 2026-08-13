**Constitución del Proyecto**

***deRuedas Gestión***

*Principios, reglas y convenciones vinculantes del producto*

Versión 1.0 — Mayo de 2026

**Preámbulo**

Este documento contiene los principios, reglas y convenciones vinculantes que rigen el desarrollo del producto deRuedas Gestión. Su propósito no es decir qué construir ni cómo construirlo en detalle —para eso están la especificación funcional y la especificación técnica—, sino fijar las bases inmutables sobre las que se toman todas las decisiones particulares: qué se considera aceptable, qué se considera inaceptable, qué trade-offs ya están resueltos por defecto y qué procedimiento se sigue cuando aparece una decisión nueva.

Como toda constitución, su valor está en su carácter vinculante y estable. Cuando un equipo discute si agregar una funcionalidad que viola un principio, no se discute si conviene o no conviene: se asume que no se hace, salvo que se proponga formalmente una enmienda a esta constitución, con la deliberación correspondiente. Este mecanismo evita que decisiones de fondo se vuelvan a tomar desde cero cada semana, y que las urgencias del corto plazo erosionen las definiciones del largo plazo.

La constitución se aplica a todas las personas que participan del proyecto, sin excepciones: equipo de producto, equipo de ingeniería, customer success, comercial, dirección, contratistas externos. Cuando un asistente de inteligencia artificial colabora en el desarrollo, también se aplica a sus contribuciones, y los humanos responsables de revisar esas contribuciones son responsables de su cumplimiento.

**Parte I — Principios fundamentales**

Los siete principios siguientes son la base de todas las decisiones de producto e ingeniería. Están ordenados aproximadamente por importancia: cuando dos principios entran en tensión, se prefiere el que aparece primero, salvo que medien razones explícitas y documentadas en sentido contrario.

**Principio 1 — Verticalidad antes que generalidad**

deRuedas Gestión es un SaaS vertical específicamente diseñado para agencias de vehículos del mercado argentino. No es un CRM genérico, no es un ERP horizontal, no es una plataforma extensible para cualquier rubro. Cada decisión de producto, de modelo de datos y de interfaz se toma asumiendo el contexto particular de una agencia de autos: el vocabulario, los flujos, las regulaciones, la documentación y las personas reales que usan el sistema.

La consecuencia operativa es que cuando se evalúa agregar una abstracción que generalice una funcionalidad —por ejemplo, hacer que el modelo de “vehículo” pueda representar también “maquinaria agrícola” o “motos”—, la pregunta correcta no es “¿es técnicamente posible?” sino “¿en qué momento concreto del roadmap haría falta?”. Si la respuesta no es del próximo trimestre, se rechaza la abstracción y se construye específicamente para autos. La generalización prematura se considera un anti-patrón explícito.

**Principio 2 — Simplicidad antes que features**

El producto compite contra Excel, cuadernos y WhatsApp. Esto significa que la barrera de adopción no es la potencia funcional del producto sino la simplicidad de la curva de aprendizaje. Una agencia que necesita más de cuatro horas de capacitación para empezar a operar deRuedas Gestión es una agencia que probablemente abandone el producto. Por lo tanto, todas las decisiones de diseño priorizan que las funcionalidades centrales sean obvias, lineales y resueltas en pocos clics, aún cuando esto implique sacrificar opciones avanzadas o flexibilidad.

Cuando aparece la tentación de agregar configurabilidad —por ejemplo, hacer que el pipeline tenga etapas configurables desde el día uno, o que la ficha del vehículo tenga campos personalizables por tenant—, se aplica el criterio del valor por defecto razonable: el sistema debe funcionar bien sin configurar nada, y solo después se permite configurar para casos específicos cuando el costo de no hacerlo sea verificablemente alto. La configurabilidad se gana con datos de uso, no se asume al inicio.

**Principio 3 — Datos como activo de primera clase**

La información que se carga en deRuedas Gestión es propiedad del cliente, pero también es uno de los activos más valiosos del producto: alimenta los reportes de inteligencia, los algoritmos de pricing sugerido, las recomendaciones de la capa de inteligencia artificial y, en agregado anonimizado, los productos de mercado de deRuedas. Por esta razón, el modelado, la calidad y la integridad de los datos son responsabilidades de primera clase, no afterthoughts.

En la práctica esto se traduce en cuatro reglas que aplican siempre. Primero, toda entidad relevante para el negocio tiene un identificador único persistente y un historial de cambios. Segundo, los borrados son lógicos por defecto, no físicos, salvo que medie obligación legal de eliminación. Tercero, las migraciones de schema preservan la información existente; cuando esto no es posible se documenta explícitamente la pérdida. Cuarto, los datos identificatorios personales se manejan con cifrado en reposo y enmascaramiento en logs por defecto.

**Principio 4 — Multi-tenancy estricto desde el día uno**

El producto es multi-tenant. Cada tenant es una agencia separada y su información es estrictamente confidencial respecto de los demás tenants. La filtración de datos entre tenants no es un bug ordinario sino un incidente crítico de seguridad que dispara protocolos específicos. Esta no es una preocupación que se resuelve después: cada query, cada endpoint, cada vista, cada índice, cada cache se diseña asumiendo el aislamiento como condición no negociable.

El mecanismo técnico vinculante para garantizar el aislamiento se especifica en el ADR correspondiente del documento de especificación técnica. Esta constitución solo establece el principio: no hay query que se considere correcta si no incluye discriminación por tenant, no hay cache que se considere correcto si no se invalida con clave que incluya tenant, y no hay endpoint que se considere correcto si no se autoriza en el contexto del tenant del usuario autenticado.

**Principio 5 — Decisiones vinculantes y trazables**

Las decisiones arquitectónicas y de producto que tienen alcance superior al de una historia individual se documentan como Architecture Decision Records (ADRs) y como entradas en el documento de especificación técnica. Las decisiones documentadas como ADR son vinculantes hasta que sean explícitamente reemplazadas por un ADR posterior. Las decisiones implícitas —es decir, las que se aplican sin haber sido documentadas— no son vinculantes y pueden ser cuestionadas en cualquier momento.

Esta regla apunta a un problema concreto y frecuente en proyectos de software: las decisiones tácitas se vuelven invisibles, los nuevos integrantes del equipo las desconocen y las erosionan sin saberlo, y al cabo de unos años nadie sabe por qué el sistema está construido como está. Forzar que toda decisión relevante se escriba protege la coherencia del producto en el tiempo.

**Principio 6 — Calidad por defecto**

El equipo no construye software que después se vuelve calidad. Construye software con calidad incorporada desde el primer commit. Esto significa que no hay una fase de testing posterior al desarrollo, no hay deuda técnica intencional asumida sin un ADR que la justifique, no hay código en producción sin pruebas automatizadas que cubran sus comportamientos críticos, y no hay despliegue que no haya pasado por el pipeline de validación completo.

La consecuencia operativa es que las estimaciones de las historias incluyen el tiempo de pruebas, documentación y revisión, no se consideran adicionales. Cuando aparece presión por entregar más rápido sacrificando calidad, la respuesta vinculante es reducir el alcance de la entrega, no reducir la calidad.

**Principio 7 — Iteración con feedback real de usuarios**

El producto se construye con clientes reales en el loop. Las decisiones de qué construir, en qué orden y con qué nivel de detalle se validan permanentemente con la base de agencias early adopter. Una funcionalidad construida sin haber sido validada con al menos tres usuarios reales se considera especulativa y debe marcarse como tal en su release.

Esto implica que el equipo está en contacto continuo con clientes a través del programa de early adopters, las visitas presenciales del equipo de Customer Success, las sesiones de research, y los datos cuantitativos de uso del producto. Las opiniones internas sobre qué hacer no son evidencia. Lo que dicen los clientes y lo que muestran los datos sí lo son.

**Parte II — Reglas vinculantes**

Las reglas siguientes son aplicaciones concretas de los principios anteriores. Están organizadas por dominio. Son vinculantes y se aplican sin necesidad de discusión particular, salvo que medie una enmienda formal a la constitución.

**Artículo 1. Convenciones de código y estilo**

- El código se escribe en inglés, salvo identificadores que reflejen entidades específicas del dominio argentino sin traducción razonable (por ejemplo, “dominio”, “permuta”, “cuentaCorriente”).

- La nomenclatura de variables y funciones sigue las convenciones del lenguaje (snake_case en Python, camelCase en TypeScript).

- Los archivos no superan las cuatrocientas líneas. Los archivos que las superan se descomponen en archivos más pequeños o se documenta explícitamente el motivo de no hacerlo.

- Las funciones no superan las cincuenta líneas. Las funciones que las superan se descomponen o se documenta el motivo.

- Toda función pública tiene firma tipada. En Python se usan type hints completos; en TypeScript no se usa el tipo any salvo en casos justificados.

- El formateo y el linter son automáticos: la configuración vive en el repositorio y se aplica en pre-commit. El código que no pasa el linter no se mergea.

**Artículo 2. Pruebas automatizadas**

- Toda regla de negocio nueva tiene al menos una prueba unitaria que la verifica.

- Todo flujo principal de una historia de usuario tiene al menos una prueba de extremo a extremo que lo cubre.

- La cobertura mínima del código backend es ochenta por ciento medida sobre líneas, y la cobertura no decrece entre commits, salvo que medie una excepción documentada.

- Los tests no son lentos: la suite unitaria completa se ejecuta en menos de cinco minutos, la suite de integración en menos de quince minutos, y la suite end-to-end en menos de treinta minutos.

- Los tests son deterministas: no se aceptan tests que fallan intermitentemente. Un test flaky se trata como bug y se arregla o se elimina.

**Artículo 3. Seguridad por defecto**

- Toda contraseña se almacena con hash usando bcrypt o argon2id. No se aceptan funciones de hash débiles ni cifrado simétrico de contraseñas.

- Todo dato identificatorio personal se cifra en reposo y se enmascara en logs.

- Toda comunicación cliente-servidor usa TLS 1.2 como mínimo, y TLS 1.3 cuando esté disponible.

- Los secretos no viven en el repositorio: viven en el gestor de secretos del entorno. Los repositorios incluyen un archivo de ejemplo .env.example sin valores reales.

- Las dependencias se auditan automáticamente en el pipeline de integración. Las vulnerabilidades de severidad alta o crítica bloquean el merge.

- La autenticación es estándar: OAuth2 con OIDC. No se construye autenticación a medida.

- La autorización se basa en roles y se verifica en el backend siempre, nunca solo en el frontend.

**Artículo 4. Performance**

- El percentil noventa y cinco de latencia en endpoints de listado es inferior a doscientos milisegundos en condiciones normales de carga.

- El percentil noventa y cinco de latencia en endpoints de búsqueda es inferior a quinientos milisegundos.

- La carga inicial de la aplicación web mide menos de dos segundos hasta primer contenido en una conexión 4G simulada.

- Las consultas a base de datos que escanean tablas completas con más de cien mil registros están prohibidas en endpoints sincrónicos. Si la operación lo requiere, se ejecuta en background y se notifica al usuario.

**Artículo 5. Despliegue y feature flags**

- Todo cambio en producción pasa por el pipeline de despliegue continuo. No hay despliegues manuales en condiciones normales.

- Toda funcionalidad nueva se despliega detrás de un feature flag controlable por tenant.

- La activación de features para clientes se hace progresivamente: primero internos, después early adopters, después el resto.

- Los rollbacks deben ser posibles en menos de quince minutos para cualquier deploy.

**Artículo 6. Datos y privacidad**

- Cada tenant es propietario de sus datos. La exportación completa de los datos de un tenant en formato estándar está disponible bajo demanda.

- Cuando un tenant cancela el servicio, sus datos se conservan por noventa días y luego se eliminan de manera definitiva, salvo obligación legal en contrario.

- El uso agregado y anonimizado de datos cross-tenant para alimentar productos como el índice de precios está permitido, siempre que sea anónimo, agregado y no permita identificar al tenant de origen.

- Los datos de un tenant nunca se usan para mejorar la experiencia de otro tenant de manera que pueda inferirse información del primero.

**Artículo 7. Procedimiento para tomar decisiones**

Las decisiones se categorizan por su alcance y se manejan según corresponda.

- Decisiones locales (afectan un módulo o una historia): las toma el desarrollador que ejecuta la historia, sujeto a code review. No requieren documentación adicional.

- Decisiones de módulo (afectan el diseño completo de un módulo): las toma el responsable técnico del módulo, con consulta al tech lead. Se documentan en la sección correspondiente del documento técnico.

- Decisiones arquitectónicas (afectan transversalmente al sistema o tienen impacto irreversible relevante): se documentan como ADR y se aprueban por el tech lead más al menos un revisor independiente.

- Decisiones de producto (afectan el qué se construye): las toma el product manager con base en evidencia de usuario, sujeto a la visión estratégica del fundador o equipo directivo.

**Artículo 8. Procedimiento para enmendar esta constitución**

Esta constitución puede modificarse por enmienda formal con el procedimiento siguiente: (a) propuesta escrita identificando el artículo o principio a modificar y la justificación; (b) discusión abierta del equipo durante al menos cinco días hábiles; (c) aprobación por mayoría calificada del equipo técnico y producto, con consulta a dirección si la enmienda afecta principios fundamentales; (d) registro de la enmienda con fecha, motivo y versión; (e) comunicación al equipo y a los stakeholders externos relevantes.

Las enmiendas se acumulan al final del documento como historial. La constitución original nunca se reescribe sin dejar rastro de las versiones previas.

**Parte III — Trade-offs explícitos**

Para evitar discusiones recurrentes sobre los mismos temas, esta sección documenta trade-offs específicos que ya están resueltos por convención del proyecto. Cada trade-off declara qué se prioriza y qué se sacrifica, con la justificación correspondiente.

**Velocidad de desarrollo versus completitud de cobertura**

El proyecto privilegia liberar funcionalidad útil en producción rápidamente sobre cubrir todos los casos de uso teóricos. Cuando una funcionalidad nueva tiene un flujo principal claro y casos borde infrecuentes, se libera primero el flujo principal con manejo de errores razonable y los casos borde se atienden por iteración. La exhaustividad anticipada ralentiza el aprendizaje y produce código que se descarta antes de ser usado.

**Build versus buy**

El proyecto privilegia comprar o integrar componentes maduros antes que construir a medida, salvo que el componente sea parte del núcleo competitivo del producto. Esto significa que se compran soluciones para autenticación, observabilidad, mensajería, OCR, firma electrónica, infraestructura cloud, base de datos. Se construyen a medida los componentes específicos del dominio: gestión de stock, CRM, permutas, integración con financieras, motor de inteligencia.

**Configurabilidad versus opinión fuerte**

El proyecto privilegia opciones por defecto razonables sobre configurabilidad amplia. Esto se enmarca dentro del principio de simplicidad. La configurabilidad se introduce solo cuando hay evidencia concreta de que múltiples clientes la necesitan, no antes.

**Verticalidad versus extensibilidad**

El proyecto privilegia diseñar específicamente para agencias de autos sobre construir un sistema extensible para múltiples verticales. La extensibilidad se considera explícitamente fuera del alcance. Si en el futuro se decide expandir a otros verticales (motos, maquinaria, embarcaciones), se evaluará si conviene extender el sistema actual o construir productos paralelos que reutilicen infraestructura, pero no se anticipa esa decisión en el diseño actual.

**Performance versus pureza arquitectónica**

Cuando la arquitectura limpia entra en tensión con la performance percibida por el usuario, el proyecto privilegia la performance. Esto se aplica especialmente a operaciones frecuentes de lectura, donde se aceptan denormalizaciones, vistas materializadas y caches específicos aún cuando complican el modelo. Las soluciones de performance se documentan explícitamente.

**Parte IV — Glosario y definiciones canónicas**

Las definiciones siguientes son canónicas para el proyecto. Cuando un término aparece en cualquier documento, código, comunicación o interfaz, se asume con el significado aquí establecido. Las divergencias se tratan como errores y se corrigen.

**Tenant**

Cada agencia cliente de deRuedas Gestión es un tenant. Un tenant es la unidad de aislamiento de datos, configuración y facturación. Un tenant tiene uno o más usuarios, una o más sucursales, y un plan de suscripción asociado.

**Usuario**

Una persona física que accede al sistema con credenciales propias. Un usuario pertenece exactamente a un tenant. Un usuario tiene un rol (Gerente, Vendedor, Administrativo) que define su perfil de permisos. Un usuario puede estar asignado a una o más sucursales del tenant.

**Vehículo**

Una unidad concreta de stock. No confundir con “modelo”, que es una categoría. Un vehículo se identifica unívocamente dentro de un tenant por su dominio, y globalmente por su identificador interno persistente.

**Lead**

Una oportunidad comercial creada a partir de una consulta entrante de un comprador potencial. Un lead se asocia a un contacto (comprador), opcionalmente a un vehículo de interés y a un vendedor responsable. Un lead avanza por las etapas del pipeline hasta cerrarse como ganado o perdido.

**Contacto**

La persona física o jurídica que aparece del otro lado de una operación: comprador, vendedor de un usado en permuta, etcétera. Los contactos se desduplican dentro del tenant por número telefónico o documento.

**Operación**

Una transacción comercial concreta: la venta de un vehículo, la compra en permuta de un usado, la venta más permuta combinada. Una operación tiene un estado, un valor monetario, costos asociados y una o más transacciones financieras vinculadas.

**Permuta**

Operación en la que un comprador entrega un vehículo usado como parte del pago de otro vehículo. Genera una valuación, eventualmente una inspección, y al cierre crea automáticamente un nuevo registro de stock por el vehículo recibido.

**Sucursal**

Subunidad geográfica de un tenant. Las agencias multi-sucursal asignan vehículos, vendedores y operaciones a sucursales específicas. Los planes Starter no soportan multi-sucursal.

**Pipeline**

Secuencia ordenada de etapas configurables por las que avanzan los leads. El sistema provee un pipeline por defecto con cinco etapas que cada tenant puede modificar.

**Plan**

Combinación de límites cuantitativos (usuarios, vehículos, sucursales) y módulos habilitados que define el alcance de uso permitido a un tenant según su suscripción.

**Feature flag**

Mecanismo técnico que permite habilitar o deshabilitar una funcionalidad en producción sin re-desplegar, controlado por tenant, por usuario o globalmente.

**ADR**

Architecture Decision Record. Documento corto y estructurado que registra una decisión arquitectónica con su contexto, las opciones evaluadas, la decisión tomada y sus consecuencias previsibles.
