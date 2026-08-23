## Purpose

Fija cómo se opera el stock de una agencia por HTTP: qué operaciones existen, quién puede cada una, sobre qué campos, y cómo se recorre un listado que crece sin techo.

> **Esta capacidad nace a medias construida.** Listar, obtener, crear, cambiar de estado y dar de baja ya funcionan en `main` desde la rebanada vertical `ESC-003`. Los requisitos de abajo son **los huecos**: la edición, la línea de tiempo, el recorrido por páginas y la protección contra el reintento.

## ADDED Requirements

### Requirement: Editar un vehículo por HTTP

La API SHALL exponer una operación de edición parcial de un vehículo.

La operación MUST exigir el permiso de edición de vehículos y MUST aplicar la restricción de campos que la matriz de permisos le asigne al rol de quien llama: un campo que el rol no tiene concedido MUST ser descartado en silencio, no rechazado.

Un vehículo de otra agencia MUST responder igual que un vehículo inexistente.

#### Scenario: Edición completa por un rol sin restricción de campos

- **WHEN** un rol con edición sin restricción modifica varios campos de un vehículo
- **THEN** todos los campos indicados quedan modificados

#### Scenario: Edición por un rol con campos acotados

- **WHEN** un rol cuya concesión acota los campos editables intenta modificar un campo fuera de su conjunto
- **THEN** ese campo no cambia
- **AND** los campos que sí tiene concedidos cambian

#### Scenario: La edición queda sin efecto tras el recorte

- **WHEN** un rol con campos acotados envía únicamente campos que no tiene concedidos
- **THEN** la respuesta es exitosa, el vehículo no cambia y no se publica ningún hecho de dominio

#### Scenario: Sin el permiso de edición

- **WHEN** un rol sin el permiso de edición intenta editar un vehículo
- **THEN** la petición se rechaza por falta de permiso

#### Scenario: Vehículo de otra agencia

- **WHEN** se intenta editar un vehículo que pertenece a otra agencia
- **THEN** la respuesta es la de un recurso inexistente, indistinguible de la de un identificador que no existe en ningún lado

#### Scenario: La edición no cambia el estado

- **WHEN** una petición de edición intenta incluir el estado del vehículo
- **THEN** la petición se rechaza y el estado no cambia

### Requirement: Consultar la línea de tiempo de un vehículo

La API SHALL exponer una operación que devuelva el historial de cambios de estado de un vehículo, del más reciente al más antiguo.

La operación MUST exigir el permiso de lectura de vehículos, que la matriz concede a todos los roles de la agencia sin restricción de campos sobre este recurso.

La restricción de campos que ese mismo permiso impone sobre **el vehículo** MUST NOT aplicarse a los registros de historial: es una lista blanca definida sobre otro recurso, y aplicarla devolvería registros vacíos en lugar de un error.

El historial MUST NOT exponer ningún dato económico del vehículo. No es una vía lateral para leer lo que la restricción de campos protege.

#### Scenario: Historial de un vehículo con transiciones

- **WHEN** se consulta el historial de un vehículo que se cargó y cambió de estado dos veces
- **THEN** se obtienen los tres registros, empezando por el más reciente

#### Scenario: Historial visto por un rol con campos restringidos

- **WHEN** un rol cuya lectura de vehículos está acotada por campos consulta el historial
- **THEN** recibe los registros completos, con sus estados, motivos, autores y fechas

#### Scenario: El historial no filtra información económica

- **WHEN** se consulta el historial de un vehículo con costo de adquisición cargado
- **THEN** ningún registro incluye precio ni costo

#### Scenario: Historial de un vehículo de otra agencia

- **WHEN** se consulta el historial de un vehículo que pertenece a otra agencia
- **THEN** la respuesta es la de un recurso inexistente

#### Scenario: Vehículo sin historial visible

- **WHEN** se consulta el historial de un vehículo dado de baja lógicamente
- **THEN** la respuesta es la de un recurso inexistente, coherente con el resto de las operaciones sobre vehículos dados de baja

### Requirement: El listado de stock se recorre por páginas

El listado de vehículos SHALL aceptar un cursor y un tamaño de página, y SHALL devolver como máximo el tamaño de página solicitado.

La respuesta MUST indicar cómo pedir la página siguiente y MUST distinguir de forma inequívoca la última página. El tamaño MUST tener valor por defecto y máximo, y pedir más que el máximo MUST acotarse en lugar de fallar.

La paginación MUST convivir con los filtros de búsqueda ya existentes: filtrar y paginar la misma consulta MUST devolver el mismo conjunto que filtrar sin paginar, repartido en páginas.

Un cursor emitido en el contexto de otra agencia MUST ser rechazado y MUST contabilizarse como intento de acceso cruzado.

#### Scenario: Recorrido completo

- **WHEN** se recorre el listado de una agencia con más vehículos que el tamaño de página, siguiendo los cursores
- **THEN** cada vehículo aparece exactamente una vez

#### Scenario: Última página

- **WHEN** se pide la página que contiene los últimos vehículos
- **THEN** la respuesta indica que no hay más páginas

#### Scenario: Tamaño por encima del máximo

- **WHEN** se pide un tamaño de página mayor al máximo
- **THEN** se devuelve como máximo el tamaño máximo permitido, sin error

#### Scenario: Paginar con filtros

- **WHEN** se recorre por páginas el listado acotado por un filtro de estado
- **THEN** el conjunto recorrido es exactamente el que devuelve ese filtro, y ningún vehículo de otro estado aparece

#### Scenario: Cursor de otra agencia

- **WHEN** se presenta un cursor obtenido en el contexto de otra agencia
- **THEN** la petición se rechaza y el intento queda contabilizado como acceso cruzado

#### Scenario: Cursor ilegible

- **WHEN** se presenta un cursor que no se puede interpretar
- **THEN** la petición se rechaza con el mismo error que un cursor de otra agencia, sin revelar cuál de los dos casos ocurrió

### Requirement: Crear un vehículo es una operación repetible sin daño

La operación de alta de un vehículo SHALL aceptar una clave de idempotencia provista por el cliente, y con ella MUST garantizar que un reintento no produzca un segundo vehículo.

La clave MUST estar acotada en longitud; una clave desmesurada MUST rechazarse como error de validación y MUST NOT llegar a la base de datos.

La reserva de la clave, la creación del vehículo y el registro de la respuesta MUST confirmarse como una sola unidad: MUST NOT existir un estado en el que el vehículo exista y la clave quede reservada sin respuesta asociada.

Cuando una segunda petición con la misma clave llegue mientras la primera todavía está en curso, la operación MUST resolverse en un tiempo acotado y MUST NOT retener recursos de forma indefinida.

#### Scenario: Reintento idéntico

- **WHEN** se repite el alta con la misma clave y el mismo contenido
- **THEN** se devuelve el resultado de la primera y no se crea un segundo vehículo

#### Scenario: Misma clave, contenido distinto

- **WHEN** se repite el alta con la misma clave y un contenido distinto
- **THEN** la petición se rechaza por conflicto

#### Scenario: Alta sin clave

- **WHEN** se crea un vehículo sin presentar clave de idempotencia
- **THEN** el alta se procesa normalmente

#### Scenario: La creación falla

- **WHEN** el alta con clave falla por una regla de negocio
- **THEN** no queda ningún vehículo creado
- **AND** la misma clave puede volver a usarse de inmediato

#### Scenario: Dos peticiones simultáneas con la misma clave

- **WHEN** dos peticiones con la misma clave llegan al mismo tiempo
- **THEN** se crea un solo vehículo
- **AND** la segunda obtiene el resultado de la primera o un rechazo por conflicto, en un tiempo acotado

#### Scenario: La misma clave en dos agencias

- **WHEN** dos agencias usan la misma clave de idempotencia
- **THEN** cada una obtiene su propia creación y ninguna recibe el resultado de la otra

#### Scenario: Clave desmesurada

- **WHEN** se presenta una clave de idempotencia que excede la longitud admitida
- **THEN** la petición se rechaza como error de validación

### Requirement: La respuesta guardada no puede depender de quién preguntó

Una operación de creación que guarde su respuesta para reproducirla ante un reintento MUST producir una respuesta cuya forma **no dependa** de los permisos de quien la originó.

La razón es que la clave de idempotencia está acotada al tenant y no a la persona: quien reintente con una clave ajena de su misma agencia recibirá la respuesta guardada. Si esa respuesta se hubiera armado según los campos concedidos a otro rol, reproducirla sería una fuga por la puerta de atrás de la misma restricción que la lectura protege por la puerta de adelante.

#### Scenario: El alta responde la misma forma para todos los roles

- **WHEN** roles distintos crean un vehículo
- **THEN** todos reciben la misma forma de respuesta, sin los campos que la matriz restringe a algunos

#### Scenario: Reintento con la clave de otra persona de la agencia

- **WHEN** alguien reintenta con una clave usada por otra persona de su misma agencia
- **THEN** la respuesta que recibe no contiene ningún campo que su propio rol no pueda ver
