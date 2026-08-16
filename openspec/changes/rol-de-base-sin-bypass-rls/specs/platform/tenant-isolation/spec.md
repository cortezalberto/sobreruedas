## ADDED Requirements

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
