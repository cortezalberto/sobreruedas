## Purpose

Fija qué es una agencia dentro del sistema y qué es una sucursal suya — cómo se la identifica de forma estable, qué datos suyos el sistema se niega a aceptar mal formados, qué significa darla de baja, y por qué una sucursal de una agencia no es alcanzable desde otra.

## ADDED Requirements

### Requirement: Identidad estable y única de la agencia

Cada agencia SHALL tener dos identificadores únicos en todo el sistema, además de su clave interna: uno legible y apto para aparecer en una dirección web, y su identificación fiscal.

La identificación fiscal MUST validarse por su dígito verificador y por su prefijo de categoría antes de aceptarse. Un valor con la forma correcta pero que ningún organismo reconocería MUST rechazarse en el momento de la carga, no más tarde.

La identificación fiscal MUST almacenarse en una forma canónica única, de modo que el mismo número escrito de dos maneras distintas no produzca dos agencias.

#### Scenario: Identificación fiscal con dígito verificador incorrecto

- **WHEN** se intenta registrar una agencia cuya identificación fiscal no supera la verificación del dígito
- **THEN** el registro se rechaza indicando el campo culpable
- **AND** la agencia no queda creada

#### Scenario: Identificación fiscal con prefijo inexistente

- **WHEN** se intenta registrar una agencia cuya identificación fiscal tiene dígito verificador correcto pero un prefijo que no corresponde a ninguna categoría fiscal
- **THEN** el registro se rechaza
- **AND** la agencia no queda creada

#### Scenario: El mismo número escrito de dos formas

- **WHEN** se registra una agencia con la identificación fiscal separada por guiones y luego otra con el mismo número sin separadores
- **THEN** el segundo registro se rechaza por duplicado

#### Scenario: Identificador legible duplicado

- **WHEN** se intenta registrar una agencia con un identificador legible que ya usa otra
- **THEN** el registro se rechaza por duplicado

### Requirement: Ciclo de vida de la agencia sin borrado físico

Una agencia SHALL poder darse de baja de forma recuperable. La baja MUST conservar la fila y todo su histórico.

El sistema MUST excluir por defecto a las agencias dadas de baja de cualquier consulta ordinaria, sin que cada consulta tenga que acordarse de pedirlo.

Una agencia dada de baja MUST seguir ocupando sus identificadores únicos: dar de baja no libera el identificador legible ni la identificación fiscal para que otra los tome.

#### Scenario: Baja de una agencia

- **WHEN** se da de baja una agencia
- **THEN** la fila sigue existiendo con su marca de baja
- **AND** deja de aparecer en las consultas ordinarias

#### Scenario: El identificador no se libera con la baja

- **WHEN** se intenta registrar una agencia con la identificación fiscal de una que fue dada de baja
- **THEN** el registro se rechaza por duplicado

### Requirement: Aislamiento de las sucursales entre agencias

Las sucursales SHALL estar sujetas al mismo contrato de aislamiento que toda tabla del sistema que pertenece a un tenant.

Una consulta emitida en el contexto de una agencia MUST NOT devolver sucursales de otra, aunque la consulta no filtre explícitamente. Una consulta emitida sin contexto de agencia MUST NOT devolver ninguna sucursal.

#### Scenario: Dos agencias con sucursales

- **WHEN** dos agencias tienen sucursales cargadas y se consultan las sucursales en el contexto de una de ellas
- **THEN** solo se devuelven las suyas

#### Scenario: Consulta de sucursales sin contexto

- **WHEN** se consultan las sucursales sin contexto de agencia establecido
- **THEN** no se devuelve ninguna fila

#### Scenario: Escritura de una sucursal en otra agencia

- **WHEN** se intenta crear una sucursal atribuida a una agencia distinta de la del contexto
- **THEN** la escritura se rechaza

### Requirement: Preferencias regionales con valor por defecto argentino

Cada agencia SHALL tener zona horaria e idioma propios, con un valor por defecto correspondiente al mercado argentino, de modo que una agencia recién creada sea usable sin configurarlos.

#### Scenario: Agencia creada sin especificar preferencias regionales

- **WHEN** se crea una agencia sin indicar zona horaria ni idioma
- **THEN** queda con los valores por defecto del mercado argentino
