# platform/api-conventions Specification

## Purpose

Fija la forma observable que toda respuesta de la API comparte —cómo se informa un error, cómo se recorre un listado grande y cómo se evita cobrar dos veces por un reintento— para que quien consume la API no tenga que aprender un contrato distinto en cada endpoint.

## Requirements

### Requirement: Formato uniforme de error

Toda respuesta de error de la API SHALL usar el formato Problem Details, con su tipo de contenido propio, sea el error de validación, de regla de negocio, de autorización o de recurso inexistente.

Cada error MUST incluir un identificador de código estable, legible por máquina, que permita al cliente discriminar el caso **sin interpretar el texto descriptivo**. Cada error MUST incluir además el identificador de correlación de la petición.

#### Scenario: Recurso inexistente

- **WHEN** se solicita un recurso que no existe
- **THEN** la respuesta usa el formato Problem Details
- **AND** incluye un código estable y el identificador de correlación

#### Scenario: Regla de negocio incumplida

- **WHEN** una petición es comprensible pero una regla de negocio la rechaza
- **THEN** la respuesta usa el formato Problem Details
- **AND** el estado distingue el rechazo de dominio de un fallo técnico

#### Scenario: El código no depende del idioma

- **WHEN** un cliente discrimina dos errores distintos
- **THEN** puede hacerlo por el código estable, sin interpretar el texto descriptivo

### Requirement: Detalle por campo en los errores de validación

Cuando un error corresponda a la validación de la entrada, la respuesta SHALL incluir una lista con **una entrada por campo inválido**.

Cada entrada MUST identificar el campo, un código estable del motivo, y un mensaje descriptivo. La respuesta MUST NOT incluir el valor que envió el cliente, que puede ser una credencial.

#### Scenario: Varios campos inválidos

- **WHEN** una petición tiene tres campos que no superan la validación
- **THEN** la respuesta lista tres entradas
- **AND** cada una identifica su campo, su código y su mensaje

#### Scenario: El valor rechazado no se devuelve

- **WHEN** un campo que contiene una credencial no supera la validación
- **THEN** la respuesta describe el problema
- **AND** no incluye el valor recibido

### Requirement: Paginación por cursor para listados grandes

La API SHALL ofrecer recorrido por cursor en los listados que pueden crecer sin techo.

Cada página MUST indicar cómo pedir la siguiente y MUST distinguir de forma inequívoca la última página. El tamaño de página MUST tener un valor por defecto y un máximo, y pedir más que el máximo MUST acotarse al máximo en lugar de fallar.

#### Scenario: Recorrido completo sin repetir ni saltear

- **WHEN** se recorre un listado página por página siguiendo los cursores
- **THEN** cada elemento aparece exactamente una vez

#### Scenario: Última página

- **WHEN** se solicita la página que contiene los últimos elementos
- **THEN** la respuesta indica que no hay más páginas

#### Scenario: Tamaño de página por encima del máximo

- **WHEN** se solicita un tamaño de página mayor al máximo permitido
- **THEN** la respuesta usa el máximo permitido

#### Scenario: Cursor inválido

- **WHEN** se presenta un cursor que el sistema no puede interpretar
- **THEN** la petición es rechazada con el formato de error uniforme

#### Scenario: El cursor no cruza tenants

- **WHEN** se presenta un cursor obtenido en el contexto de otro tenant
- **THEN** no se devuelven elementos de ese otro tenant

### Requirement: Idempotencia de las creaciones

Los endpoints de creación SHALL aceptar una clave de idempotencia provista por el cliente y garantizar que un reintento con la misma clave no produzca un segundo recurso.

Una repetición con la **misma clave y el mismo contenido** MUST devolver el resultado original. Una repetición con la **misma clave y contenido distinto** MUST ser rechazada por conflicto. Las claves MUST expirar transcurrido su período de retención, y MUST estar acotadas al tenant que las generó.

#### Scenario: Reintento idéntico

- **WHEN** se repite una creación con la misma clave y el mismo contenido
- **THEN** se devuelve el resultado de la primera
- **AND** no se crea un segundo recurso

#### Scenario: Misma clave, contenido distinto

- **WHEN** se repite una creación con la misma clave y contenido distinto
- **THEN** la petición es rechazada por conflicto

#### Scenario: Clave expirada

- **WHEN** se reutiliza una clave cuyo período de retención ya venció
- **THEN** la petición se trata como una creación nueva

#### Scenario: La misma clave en dos tenants

- **WHEN** dos tenants distintos usan la misma clave de idempotencia
- **THEN** cada uno obtiene su propia creación
- **AND** ninguno recibe el resultado del otro

#### Scenario: Creación sin clave

- **WHEN** se crea un recurso sin presentar clave de idempotencia
- **THEN** la creación se procesa normalmente
