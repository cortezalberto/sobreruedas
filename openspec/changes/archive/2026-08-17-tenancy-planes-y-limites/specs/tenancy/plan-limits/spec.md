## Purpose

Fija cómo el sistema hace cumplir los límites que el plan comercial de cada agencia promete — qué se cuenta, qué no, y por qué el rechazo por haber llegado al techo del plan tiene que ser distinguible del rechazo por no tener permiso.

## ADDED Requirements

### Requirement: Catálogo de planes disponible desde el arranque

El sistema SHALL disponer del catálogo de planes comerciales sin intervención manual: un entorno recién migrado MUST tener los planes vigentes cargados con sus límites.

Cada plan SHALL declarar su límite de usuarios, de vehículos en stock, de sucursales y de mensajes mensuales, además de los módulos que habilita.

Un límite ausente SHALL representarse de forma explícita y distinguible de un límite de valor cero. El sistema MUST NOT interpretar un plan sin techo como un plan que no permite nada.

#### Scenario: Entorno recién migrado

- **WHEN** se aplican las migraciones sobre una base vacía
- **THEN** el catálogo de planes queda cargado con los planes vigentes y sus límites

#### Scenario: El seed no pisa lo que ya existe

- **WHEN** las migraciones se aplican sobre una base que ya tiene el catálogo cargado y con un precio modificado a mano
- **THEN** el precio modificado se conserva

#### Scenario: Plan sin techo de vehículos

- **WHEN** una agencia con un plan sin techo de vehículos intenta agregar uno
- **THEN** la operación se permite
- **AND** se permite independientemente de cuántos vehículos ya tenga

### Requirement: Verificación de cuota antes de consumirla

El sistema SHALL verificar la cuota del plan **antes** de crear un usuario, un vehículo o una sucursal, y MUST rechazar la creación que dejaría a la agencia por encima de su límite.

El conteo MUST realizarse sobre el estado vigente almacenado, no sobre un valor precalculado que pueda haber quedado desactualizado.

#### Scenario: Alta que llega justo al límite

- **WHEN** una agencia con un vehículo menos que su límite agrega uno
- **THEN** la operación se permite

#### Scenario: Alta que supera el límite

- **WHEN** una agencia que ya alcanzó su límite de vehículos intenta agregar otro
- **THEN** la operación se rechaza
- **AND** el vehículo no queda creado

#### Scenario: Límite de sucursales

- **WHEN** una agencia que ya alcanzó su límite de sucursales intenta agregar otra
- **THEN** la operación se rechaza

#### Scenario: Límite de usuarios

- **WHEN** una agencia que ya alcanzó su límite de usuarios intenta agregar otro
- **THEN** la operación se rechaza

### Requirement: Qué consume cuota y qué no

La cuota SHALL medir ocupación vigente, no actividad histórica.

Un registro dado de baja MUST NOT consumir cuota. Un registro existente pero temporalmente inactivo MUST consumir cuota, porque sigue ocupando su lugar y puede volver a estar activo sin trámite.

#### Scenario: Un registro dado de baja libera su lugar

- **WHEN** una agencia en su límite da de baja un vehículo e intenta agregar otro
- **THEN** la operación se permite

#### Scenario: Un usuario desactivado sigue ocupando su lugar

- **WHEN** una agencia en su límite de usuarios desactiva uno sin darlo de baja e intenta agregar otro
- **THEN** la operación se rechaza

#### Scenario: La cuota de una agencia no la afecta otra

- **WHEN** una agencia alcanzó su límite y otra agencia con el mismo plan está por debajo del suyo
- **THEN** la segunda puede seguir agregando

### Requirement: El rechazo por cuota es distinguible del rechazo por permisos

El rechazo por haber alcanzado el límite del plan SHALL usar un estado de respuesta distinto del rechazo por falta de permisos y del rechazo por falta de autenticación.

La respuesta MUST permitir al cliente comunicar cuál es el recurso agotado y cuál es el techo alcanzado, sin interpretar el texto descriptivo.

El sistema MUST NOT presentar el agotamiento de cuota como un problema de permisos: ningún cambio de rol lo resuelve.

#### Scenario: Un usuario con permiso suficiente llega al techo del plan

- **WHEN** un usuario con permiso para crear vehículos intenta crear uno estando la agencia en su límite
- **THEN** el rechazo se distingue de un rechazo por falta de permisos
- **AND** el cuerpo identifica el recurso agotado y el techo alcanzado

#### Scenario: El código del rechazo no depende del idioma

- **WHEN** un cliente necesita reaccionar al agotamiento de cuota
- **THEN** puede reconocerlo por un código estable, sin interpretar el texto descriptivo
