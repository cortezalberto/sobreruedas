# platform/tenant-isolation Specification

## Purpose

Define cómo el sistema garantiza que los datos de una agencia jamás sean visibles para otra: de dónde sale la identidad del tenant, cuándo se establece su contexto, con qué privilegios se conecta la aplicación a la base de datos, qué debe ocurrir cuando alguna de esas condiciones falta, y qué pasa cuando dos peticiones de tenants distintos se atienden al mismo tiempo.

## Requirements

### Requirement: El rol de conexión no puede eludir el aislamiento

El rol con el que la aplicación se conecta a la base de datos MUST estar sujeto a las políticas de aislamiento por tenant. Ese rol MUST NOT poseer la capacidad de omitir la evaluación de dichas políticas.

Los requisitos existentes de esta capability describen qué debe ocurrir **cuando la política aplica**. Ninguno exige que efectivamente aplique al rol que consulta, y esa distinción no es teórica: una política presente y listada en el catálogo, sobre un rol que la elude, satisface toda verificación de cobertura de políticas y **no aísla nada**.

El rol de conexión de la aplicación tampoco MUST poder alterar el esquema ni las políticas de aislamiento. En particular, MUST NOT ser propietario de las tablas sujetas a aislamiento: la propiedad de una tabla habilita, por sí sola, desactivar la aplicación de sus políticas.

La verificación de estos requisitos MUST ejercitarse de forma automática y bloqueante, sobre los atributos del rol de conexión y no únicamente sobre el comportamiento observado en una tabla concreta. Un cambio de configuración que devuelva un rol privilegiado a la conexión de la aplicación MUST ser detectado.

#### Scenario: El rol de la aplicación está sujeto a las políticas

- **WHEN** se inspecciona el rol con el que la aplicación mantiene su conexión
- **THEN** ese rol no posee privilegios de superusuario
- **AND** ese rol no posee la capacidad de omitir las políticas de aislamiento

#### Scenario: El rol de la aplicación no es dueño de lo que consulta

- **WHEN** se inspecciona la propiedad de una tabla sujeta a aislamiento
- **THEN** su propietario es distinto del rol con el que la aplicación se conecta

#### Scenario: La aplicación no puede alterar el esquema

- **WHEN** la aplicación intenta crear, eliminar o modificar la estructura de una tabla
- **THEN** la operación es rechazada por falta de permisos

#### Scenario: Un rol privilegiado en la conexión se detecta

- **WHEN** la conexión de la aplicación queda configurada con un rol capaz de eludir las políticas
- **THEN** la verificación automática falla
- **AND** la falla es bloqueante

### Requirement: El acceso de la aplicación se limita a lo que necesita

El rol de conexión de la aplicación SHALL disponer únicamente de los permisos de datos que su operación requiere sobre las tablas que utiliza.

El borrado físico de filas MUST NOT estar entre esos permisos. El sistema practica borrado lógico universal, de modo que ningún camino legítimo de la aplicación elimina registros; negarlo en la base convierte esa regla en una garantía que también cubre el borrado que llegue por una vía no prevista.

Toda tabla sujeta a aislamiento MUST tener otorgados al rol de aplicación los permisos que su operación requiere. La ausencia de esos permisos MUST detectarse de forma automática y bloqueante, recorriendo el catálogo de la base y no una lista mantenida a mano.

Cuando una tabla requiera borrado físico por obligación de retención legal, ese permiso MUST otorgarse de forma explícita y nominada para esa tabla, quedando registrado como excepción declarada.

#### Scenario: La aplicación no puede borrar filas

- **WHEN** la aplicación intenta eliminar físicamente una fila de una tabla sujeta a aislamiento
- **THEN** la operación es rechazada por falta de permisos

#### Scenario: Una tabla nueva queda accesible sin intervención manual

- **WHEN** se incorpora al esquema una tabla sujeta a aislamiento
- **THEN** el rol de aplicación dispone sobre ella de los permisos que su operación requiere

#### Scenario: Una tabla sin permisos otorgados se detecta

- **WHEN** una tabla sujeta a aislamiento carece de los permisos necesarios para el rol de aplicación
- **THEN** la verificación automática la reporta
- **AND** la falla es bloqueante

### Requirement: Las migraciones no usan el acceso de la aplicación

Los cambios de esquema y de políticas SHALL ejecutarse con un rol distinto del que la aplicación utiliza para atender peticiones.

La configuración de ambos accesos MUST verificarse al iniciar el proceso de migración: si el acceso de migración y el de la aplicación no se dirigen a la misma base de datos, el proceso MUST detenerse antes de aplicar cambio alguno.

#### Scenario: La migración se ejecuta con el rol propietario

- **WHEN** se aplica un cambio de esquema
- **THEN** se ejecuta con el rol propietario y no con el de la aplicación

#### Scenario: Los dos accesos apuntan a bases distintas

- **WHEN** el acceso de migración y el de la aplicación se dirigen a bases de datos distintas
- **THEN** el proceso de migración se detiene
- **AND** no se aplica ningún cambio de esquema

### Requirement: El tenant se deriva exclusivamente del token

El sistema SHALL derivar la identidad del tenant de una petición **únicamente** del token de acceso presentado.

El sistema MUST NOT aceptar la identidad del tenant desde el cuerpo de la petición, la cadena de consulta, la ruta ni una cabecera. Los esquemas de entrada MUST excluir el discriminador de tenant, de modo que enviarlo no tenga efecto alguno.

#### Scenario: El tenant viaja en el token

- **WHEN** llega una petición autenticada cuyo token declara un tenant
- **THEN** la petición se atiende bajo el contexto de ese tenant

#### Scenario: El cuerpo intenta declarar otro tenant

- **WHEN** una petición autenticada incluye en su cuerpo un discriminador de tenant distinto al del token
- **THEN** el valor del cuerpo se ignora
- **AND** la petición se atiende bajo el tenant del token

#### Scenario: El token no declara tenant

- **WHEN** llega una petición cuyo token no declara ningún tenant
- **THEN** la petición es rechazada
- **AND** no se ejecuta ninguna consulta contra tablas sujetas a aislamiento

### Requirement: Contexto de tenant en la transacción

El sistema SHALL establecer el contexto de tenant en la sesión de base de datos al comienzo de cada petición autenticada, **dentro de la transacción que esa petición utiliza**, de modo que las políticas de aislamiento de la base puedan filtrar por él.

El contexto MUST quedar acotado a la transacción: al terminarla, MUST NOT permanecer visible para trabajo posterior que reutilice la misma conexión.

#### Scenario: El contexto se establece antes de la primera consulta

- **WHEN** una petición autenticada ejecuta su primera consulta
- **THEN** el contexto de tenant ya está establecido en esa sesión

#### Scenario: El contexto no sobrevive a la transacción

- **WHEN** termina la transacción de una petición y la conexión vuelve al pool
- **THEN** el contexto de tenant deja de estar establecido en esa conexión

#### Scenario: Peticiones concurrentes de tenants distintos

- **WHEN** dos peticiones de tenants distintos se atienden simultáneamente
- **THEN** cada una observa exclusivamente los datos de su propio tenant
- **AND** ninguna observa datos de la otra en ningún momento

### Requirement: Sin contexto no hay filas

Cuando el contexto de tenant no esté establecido, las consultas sobre tablas sujetas a aislamiento MUST NOT devolver filas.

La falla MUST ser visible y nunca silenciosa: el sistema MUST NOT sustituir el contexto ausente por un valor por defecto, ni omitir el filtro, ni devolver el conjunto completo.

#### Scenario: Consulta sin contexto establecido

- **WHEN** se consulta una tabla sujeta a aislamiento sin contexto de tenant establecido
- **THEN** no se devuelve ninguna fila

#### Scenario: No hay tenant por defecto

- **WHEN** el contexto de tenant no está establecido
- **THEN** el sistema no asume ningún tenant
- **AND** no devuelve datos de ningún tenant

### Requirement: Filtro explícito además del aislamiento de la base

Toda consulta sobre una tabla de negocio SHALL discriminar por tenant **también** en la capa de aplicación, de forma redundante con el aislamiento que aplica la base de datos.

La redundancia es deliberada: es la segunda de las tres capas y MUST sostenerse aunque la política de la base ya cubra el caso.

#### Scenario: La redundancia sobrevive a la desactivación de la política

- **WHEN** se consulta una tabla de negocio con la política de aislamiento de la base desactivada
- **THEN** la consulta sigue devolviendo únicamente filas del tenant en contexto

### Requirement: Cobertura verificable del aislamiento

El sistema SHALL permitir verificar automáticamente que **toda** tabla que porta discriminador de tenant tiene su política de aislamiento activa.

La verificación MUST recorrer el catálogo real de la base y no una lista mantenida a mano. Las tablas exentas MUST estar declaradas de forma exhaustiva y justificada; ninguna otra puede estar exenta.

#### Scenario: Una tabla nueva sin política

- **WHEN** existe una tabla con discriminador de tenant y sin política de aislamiento activa
- **THEN** la verificación falla e identifica la tabla

#### Scenario: Tabla exenta declarada

- **WHEN** una tabla figura en la lista exhaustiva de exenciones
- **THEN** la verificación no la reporta como falta

#### Scenario: Exención no declarada

- **WHEN** una tabla sin discriminador de tenant no figura en la lista de exenciones y tampoco tiene política
- **THEN** la verificación falla e identifica la tabla

### Requirement: Las violaciones de aislamiento son observables

El sistema SHALL exponer una métrica que cuente los intentos de acceso a datos fuera del tenant en contexto.

Esa métrica MUST valer cero en operación normal. Cualquier incremento MUST ser observable para disparar el protocolo de incidente correspondiente.

#### Scenario: Operación normal

- **WHEN** el sistema opera sin intentos de acceso cruzado
- **THEN** la métrica de violaciones vale cero

#### Scenario: Intento de acceso cruzado

- **WHEN** se intenta acceder a datos de un tenant distinto al del contexto
- **THEN** el acceso no devuelve datos
- **AND** la métrica de violaciones se incrementa
