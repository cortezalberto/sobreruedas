## Purpose

Fija el ciclo de vida de una persona dentro de una agencia — cómo entra, cómo se le asignan sucursales, qué significa desactivarla y qué significa que deje la empresa — y por qué el sistema nunca conoce su contraseña.

## ADDED Requirements

### Requirement: La aplicación no custodia credenciales

El sistema SHALL delegar íntegramente la custodia de credenciales al proveedor de identidad. El almacenamiento propio MUST NOT contener contraseñas, hashes de contraseña, ni secretos de segundo factor, ni en claro ni cifrados.

El registro local de una persona SHALL contener únicamente identidad de negocio y su vínculo con el sujeto del proveedor de identidad.

#### Scenario: Alta de una persona

- **WHEN** se da de alta a una persona en una agencia
- **THEN** su registro local queda sin ningún dato de credencial
- **AND** la credencial queda bajo el proveedor de identidad

#### Scenario: Ningún camino escribe una credencial

- **WHEN** se recorren las operaciones que escriben el registro local de una persona
- **THEN** ninguna acepta ni persiste una contraseña o un secreto de segundo factor

### Requirement: Invitación sin que el sistema vea la contraseña

Invitar a una persona SHALL crearla en estado pendiente, sin acceso, y disparar que el proveedor de identidad le solicite establecer su credencial.

La aceptación de la invitación MUST activar el registro local y vincularlo al sujeto del proveedor, y MUST NOT recibir ni establecer la credencial.

La creación en el proveedor de identidad SHALL ocurrir **antes** que la creación local, de modo que una falla parcial deje un estado recuperable en lugar de una persona invitada que nunca podrá entrar.

#### Scenario: Invitación enviada

- **WHEN** se invita a una persona con un email todavía no usado en esa agencia
- **THEN** queda registrada en estado pendiente y sin acceso
- **AND** el proveedor de identidad le solicita establecer su credencial

#### Scenario: Aceptación de la invitación

- **WHEN** una persona invitada acepta su invitación con un token válido
- **THEN** su registro local queda activo y vinculado al sujeto del proveedor
- **AND** la operación no recibe ninguna contraseña

#### Scenario: Token de invitación inválido o vencido

- **WHEN** se intenta aceptar una invitación con un token que no corresponde o que expiró
- **THEN** la operación se rechaza
- **AND** el registro local sigue en estado pendiente

#### Scenario: Falla al crear en el proveedor de identidad

- **WHEN** la creación en el proveedor de identidad falla
- **THEN** no queda una persona invitada en el registro local

#### Scenario: Email repetido dentro de la agencia

- **WHEN** se invita a una persona con un email que ya usa otra de la misma agencia
- **THEN** la invitación se rechaza por duplicado

#### Scenario: El mismo email en dos agencias distintas

- **WHEN** se invita con un email que ya se usa en otra agencia
- **THEN** la invitación se acepta, porque la unicidad es por agencia y no global

### Requirement: Desactivar y dar de baja son cosas distintas

El sistema SHALL distinguir a una persona que no puede acceder pero sigue perteneciendo a la agencia, de una persona que dejó de pertenecer.

Una persona desactivada MUST seguir consumiendo cupo del plan; una dada de baja MUST NOT consumirlo.

Dar de baja MUST conservar la fila y su historial, y MUST NOT liberar su email para que otra persona lo tome dentro de la misma agencia.

#### Scenario: Persona desactivada

- **WHEN** se desactiva a una persona
- **THEN** deja de poder acceder
- **AND** sigue ocupando cupo del plan

#### Scenario: Persona dada de baja

- **WHEN** se da de baja a una persona
- **THEN** su fila y su historial se conservan
- **AND** libera cupo del plan

#### Scenario: El email no se libera con la baja

- **WHEN** se intenta invitar a alguien con el email de una persona dada de baja en esa agencia
- **THEN** la invitación se rechaza por duplicado

#### Scenario: La baja no borra la identidad en el proveedor

- **WHEN** se da de baja a una persona
- **THEN** su identidad en el proveedor queda deshabilitada y no eliminada

### Requirement: El cupo de personas del plan se verifica antes de invitar

El sistema SHALL verificar el cupo de personas del plan **antes** de crear la invitación, y MUST rechazar la que dejaría a la agencia por encima de su límite.

El rechazo por cupo MUST ser distinguible del rechazo por permisos.

#### Scenario: Invitación que supera el cupo

- **WHEN** una agencia que alcanzó su límite de personas intenta invitar a otra
- **THEN** la operación se rechaza de forma distinguible de un rechazo por permisos
- **AND** no queda ninguna persona invitada ni creada en el proveedor de identidad

#### Scenario: Una baja libera cupo para invitar

- **WHEN** una agencia en su límite da de baja a una persona e invita a otra
- **THEN** la invitación se acepta

### Requirement: Asignación de personas a sucursales

Una persona SHALL poder estar asignada a varias sucursales de su agencia, con a lo sumo una marcada como principal.

Una asignación MUST NOT poder referirse a una sucursal de otra agencia.

El historial de asignaciones MUST conservarse cuando la persona se da de baja.

#### Scenario: Asignación a varias sucursales

- **WHEN** se asigna a una persona a dos sucursales de su agencia y se marca una como principal
- **THEN** ambas asignaciones quedan registradas con una sola principal

#### Scenario: Cambio de sucursal principal

- **WHEN** se marca como principal una sucursal distinta
- **THEN** la anterior deja de serlo

#### Scenario: Asignación a una sucursal de otra agencia

- **WHEN** se intenta asignar a una persona a una sucursal que no pertenece a su agencia
- **THEN** la operación se rechaza

#### Scenario: El historial sobrevive a la baja

- **WHEN** se da de baja a una persona asignada a sucursales
- **THEN** sus asignaciones se conservan

### Requirement: Aislamiento de las personas entre agencias

El registro de personas SHALL estar sujeto al mismo contrato de aislamiento que toda tabla del sistema que pertenece a un tenant.

Una consulta emitida en el contexto de una agencia MUST NOT devolver personas de otra, aunque la consulta no filtre explícitamente. Una consulta emitida sin contexto MUST NOT devolver ninguna.

#### Scenario: Listado de personas de una agencia

- **WHEN** dos agencias tienen personas cargadas y se listan en el contexto de una
- **THEN** solo se devuelven las suyas

#### Scenario: Consulta sin contexto de agencia

- **WHEN** se consultan las personas sin contexto de agencia establecido
- **THEN** no se devuelve ninguna fila

#### Scenario: Alta atribuida a otra agencia

- **WHEN** se intenta crear una persona atribuida a una agencia distinta de la del contexto
- **THEN** la escritura se rechaza
