## Purpose

Define cómo el sistema garantiza que los datos de una agencia jamás sean visibles para otra: de dónde sale la identidad del tenant, cuándo se establece su contexto en la base de datos, y qué debe ocurrir cuando ese contexto falta o cuando dos peticiones de tenants distintos se atienden al mismo tiempo.

## ADDED Requirements

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
