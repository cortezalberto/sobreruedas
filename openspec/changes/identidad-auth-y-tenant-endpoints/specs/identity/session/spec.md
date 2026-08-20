## Purpose

Fija qué puede saber de sí mismo quien presenta un token válido, y qué significa cerrar sesión cuando la sesión no vive en este sistema.

## ADDED Requirements

### Requirement: El sujeto sale del token y solo del token

La operación que devuelve la información de quien hace la petición SHALL derivar el sujeto exclusivamente del token presentado.

Esa operación MUST NOT aceptar ningún parámetro que permita pedir la información de otra persona, ni por ruta, ni por consulta, ni por cuerpo.

#### Scenario: Consulta de la propia información

- **WHEN** alguien con un token válido consulta su información
- **THEN** recibe la que corresponde al sujeto del token

#### Scenario: Intento de consultar a otra persona

- **WHEN** se intenta indicar otra identidad en la petición
- **THEN** la petición se rechaza o la identidad indicada se ignora, y en ningún caso se devuelve información de esa otra persona

#### Scenario: Sin token

- **WHEN** se consulta la propia información sin presentar un token
- **THEN** la respuesta indica falta de autenticación, distinguible de una falta de permisos

### Requirement: La información propia completa lo que el token no dice

La respuesta SHALL incluir, además de lo que el token ya declara, los datos de negocio que el proveedor de identidad no conoce: el estado de la persona dentro de la agencia y las sucursales que tiene asignadas, indicando cuál es la principal.

#### Scenario: Persona con sucursales asignadas

- **WHEN** alguien asignado a dos sucursales consulta su información
- **THEN** recibe ambas y cuál es la principal

#### Scenario: Persona sin sucursales asignadas

- **WHEN** alguien sin sucursales asignadas consulta su información
- **THEN** la respuesta lo indica sin fallar

### Requirement: El espejo local se corrige contra el proveedor de identidad

Cuando los datos copiados del proveedor de identidad difieran de los del registro local, el sistema SHALL adoptar los del proveedor.

Un registro local que contradiga al proveedor sobre a quién pertenece una cuenta MUST NOT persistir en esa contradicción.

#### Scenario: El email cambió en el proveedor

- **WHEN** alguien presenta un token cuyo email difiere del que tiene el registro local
- **THEN** el registro local queda con el email del token

#### Scenario: El cambio no altera lo que es nuestro

- **WHEN** el registro local se corrige contra el proveedor
- **THEN** el rol, la agencia y las sucursales asignadas no cambian

### Requirement: Cerrar sesión termina la sesión en el proveedor de identidad

La operación de cierre de sesión SHALL terminar la sesión en el proveedor de identidad.

El sistema MUST NOT mantener un registro propio de tokens revocados.

#### Scenario: Cierre de sesión

- **WHEN** alguien cierra sesión
- **THEN** su sesión en el proveedor de identidad queda terminada

#### Scenario: El token vigente sobrevive hasta su vencimiento

- **WHEN** se cierra sesión y se reutiliza el token de acceso que ya se había emitido
- **THEN** ese token sigue siendo aceptado hasta que expire, porque no existe registro propio de revocación

> Este último escenario documenta una consecuencia asumida, no un defecto: es el comportamiento estándar de tokens de vida corta. Cerrarlo exigiría consultar al proveedor en cada petición.
