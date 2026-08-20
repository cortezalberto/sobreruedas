# platform/identity Specification

## Purpose

Establece cómo el sistema determina quién hace cada petición a partir del token emitido por el proveedor de identidad externo, sin verificar credenciales por su cuenta y sin confiar en nada que el cliente pueda escribir.

## Requirements

### Requirement: La identidad se delega al proveedor externo

El sistema SHALL delegar la autenticación **enteramente** al proveedor de identidad, aceptando únicamente tokens que ese proveedor emitió.

El sistema MUST NOT almacenar, derivar ni verificar contraseñas por su cuenta.

#### Scenario: Token emitido por el proveedor

- **WHEN** se presenta un token válido emitido por el proveedor de identidad
- **THEN** la petición se atiende con el sujeto que ese token declara

#### Scenario: No hay verificación local de credenciales

- **WHEN** se presenta un par de credenciales directamente a la API
- **THEN** el sistema no las verifica
- **AND** no existe ningún camino que autentique sin pasar por el proveedor

### Requirement: Validación del token

El sistema SHALL rechazar toda petición cuyo token no sea verificable contra las claves públicas publicadas por el proveedor.

El sistema MUST rechazar tokens con firma inválida, expirados, emitidos por otro emisor o destinados a otro receptor. Las claves de verificación MUST obtenerse del proveedor y MUST poder renovarse sin reiniciar el servicio, para que una rotación de claves no cause una caída.

#### Scenario: Firma inválida

- **WHEN** se presenta un token cuya firma no verifica
- **THEN** la petición es rechazada por falta de autenticación

#### Scenario: Token expirado

- **WHEN** se presenta un token cuya validez ya venció
- **THEN** la petición es rechazada por falta de autenticación

#### Scenario: Emisor distinto

- **WHEN** se presenta un token correctamente firmado pero emitido por otro emisor
- **THEN** la petición es rechazada por falta de autenticación

#### Scenario: Rotación de claves del proveedor

- **WHEN** el proveedor rota sus claves y emite un token con la clave nueva
- **THEN** el sistema obtiene la clave nueva y acepta el token
- **AND** no hace falta reiniciar el servicio

#### Scenario: Petición sin token

- **WHEN** se accede a un recurso protegido sin presentar token
- **THEN** la petición es rechazada por falta de autenticación

### Requirement: Sujeto de la petición

De un token válido el sistema SHALL derivar el sujeto que hace la petición, incluyendo su identificador, su tenant y su rol.

Esos datos MUST provenir del token y MUST NOT tomarse de ninguna parte de la petición que el cliente controle. Si el token no declara los datos necesarios, la petición MUST ser rechazada en lugar de atenderse con valores supuestos.

#### Scenario: Token completo

- **WHEN** se presenta un token que declara identificador, tenant y rol
- **THEN** la petición se atiende con ese sujeto

#### Scenario: Token sin rol declarado

- **WHEN** se presenta un token válido que no declara rol
- **THEN** la petición es rechazada
- **AND** no se le asigna un rol por defecto

### Requirement: Rutas exentas de autenticación

El sistema SHALL declarar de forma explícita qué rutas se atienden sin token.

Las rutas exentas MUST estar acotadas a las sondas de estado y a los receptores de notificaciones externas, y estas últimas MUST verificar la autenticidad del emisor por su propio mecanismo. Ninguna ruta que exponga datos de un tenant puede ser exenta.

#### Scenario: Sonda de estado sin token

- **WHEN** se consulta una sonda de estado sin presentar token
- **THEN** la respuesta es exitosa

#### Scenario: Receptor de notificaciones externas

- **WHEN** llega una notificación externa sin token pero con firma válida del emisor
- **THEN** la notificación se acepta

#### Scenario: Notificación externa con firma inválida

- **WHEN** llega una notificación externa cuya firma no verifica
- **THEN** es rechazada

#### Scenario: Ninguna ruta de datos es exenta

- **WHEN** se accede sin token a una ruta que expone datos de un tenant
- **THEN** la petición es rechazada
