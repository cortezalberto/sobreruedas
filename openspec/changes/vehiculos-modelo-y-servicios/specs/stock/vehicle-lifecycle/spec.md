## Purpose

Fija qué le pasa a un vehículo a lo largo de su vida en la agencia: qué cambios de estado son legales, qué queda registrado de cada uno, quién puede alterar ese registro, y qué se entera el resto del sistema cuando un vehículo se modifica.

> **Esta capacidad nace a medias construida.** El alta, el cambio de estado, la baja lógica y la máquina de transiciones ya funcionan en `main` desde la rebanada vertical `ESC-003`. Los requisitos de abajo son **los huecos que esa rebanada dejó**: el registro histórico y la edición.

## ADDED Requirements

### Requirement: Todo cambio de estado queda registrado

Cada vez que un vehículo cambia de estado, el sistema SHALL dejar un registro del cambio que conserve el estado anterior, el estado nuevo, el instante en que ocurrió, el motivo si lo hubo, y quién lo hizo.

El registro MUST escribirse en la misma unidad de trabajo que el cambio que documenta. Un cambio de estado que se confirma sin su registro, o un registro que sobrevive a un cambio que se revirtió, MUST NOT ser posible.

Cuando el cambio no lo origina una persona sino un proceso automático, el registro SHALL indicar que no hubo autor, y MUST NOT atribuirlo a nadie.

#### Scenario: Una transición manual

- **WHEN** alguien cambia un vehículo de un estado a otro
- **THEN** queda un registro con el estado del que venía, el estado al que fue, cuándo, y esa persona como autora

#### Scenario: La transición trae motivo

- **WHEN** el cambio de estado se hace indicando un motivo
- **THEN** el motivo queda en el registro

#### Scenario: Una transición sin persona detrás

- **WHEN** un proceso automático cambia el estado de un vehículo
- **THEN** queda el registro y su autor consta como ausente, no como un usuario cualquiera

#### Scenario: El cambio se revierte

- **WHEN** un cambio de estado falla o se revierte antes de confirmarse
- **THEN** no queda ningún registro de ese cambio

#### Scenario: Una transición rechazada

- **WHEN** se intenta un cambio de estado que las transiciones legales no admiten
- **THEN** el cambio se rechaza y no queda registro de nada

### Requirement: El ingreso al stock abre la línea de tiempo

Cuando un vehículo entra al stock, el sistema SHALL abrir su línea de tiempo con un registro cuyo estado anterior consta como inexistente.

Esto SHALL valer para **toda** vía de alta, incluida la carga masiva. Un vehículo del que exista un registro de transición pero no un registro de ingreso MUST NOT ser posible.

#### Scenario: Alta individual

- **WHEN** se carga un vehículo
- **THEN** su línea de tiempo empieza con un registro sin estado anterior y con el estado inicial que la regla de negocio fija

#### Scenario: Alta masiva

- **WHEN** se cargan vehículos por importación masiva
- **THEN** cada uno abre su línea de tiempo igual que si se hubiera cargado de a uno

#### Scenario: La línea de tiempo se lee completa

- **WHEN** se consulta la historia de un vehículo que se cargó y después cambió de estado dos veces
- **THEN** se obtienen tres registros: el ingreso y las dos transiciones

### Requirement: El registro histórico no se altera ni se borra

El sistema SHALL impedir que un registro de cambio de estado, una vez escrito, sea modificado o eliminado.

La prohibición MUST estar impuesta por el motor de base de datos y no depender de que ningún código de aplicación se abstenga. Un intento de modificar o borrar un registro MUST fallar aunque provenga de una consulta legítima ejecutada con las credenciales de la aplicación.

#### Scenario: Intento de modificación

- **WHEN** se intenta modificar un registro histórico con las credenciales de la aplicación
- **THEN** la operación es rechazada por falta de privilegio

#### Scenario: Intento de borrado

- **WHEN** se intenta borrar un registro histórico con las credenciales de la aplicación
- **THEN** la operación es rechazada por falta de privilegio

#### Scenario: La lectura y la escritura siguen disponibles

- **WHEN** la aplicación consulta o agrega registros históricos
- **THEN** ambas operaciones funcionan con normalidad

### Requirement: El registro histórico no cruza agencias

El registro de cambios de estado SHALL estar aislado por tenant con las mismas garantías que cualquier dato de negocio.

Una agencia MUST NOT poder leer, ni por consulta directa ni a través de ninguna operación, el historial de un vehículo de otra agencia. Un registro MUST NOT poder atribuirse a una persona que pertenece a otra agencia.

#### Scenario: Historial de otra agencia

- **WHEN** una agencia consulta el historial de un vehículo que pertenece a otra
- **THEN** no obtiene ningún registro, y la respuesta no revela que el vehículo exista

#### Scenario: Autor de otra agencia

- **WHEN** se intenta registrar un cambio atribuido a una persona de otra agencia
- **THEN** la operación es rechazada por la base de datos

### Requirement: Un vehículo se edita de forma parcial y sin tocar su estado

El sistema SHALL ofrecer una operación de dominio que modifique un vehículo campo por campo, aplicando únicamente los campos que la petición trae.

Un campo ausente MUST dejarse como está. Un campo presente con valor vacío SHALL vaciarse, siempre que el campo admita quedar vacío; si no lo admite, la petición MUST rechazarse indicando cuál es el campo, y MUST NOT llegar a la base de datos.

La operación MUST NOT poder cambiar el estado del vehículo. El estado se cambia por su propia operación, que es la única que verifica las transiciones legales, exige motivo cuando corresponde y evalúa el permiso por transición.

#### Scenario: Edición de un solo campo

- **WHEN** se edita un vehículo indicando únicamente su precio
- **THEN** el precio cambia y ningún otro campo se altera

#### Scenario: Vaciar un campo que admite estar vacío

- **WHEN** se edita un vehículo pidiendo explícitamente vaciar el vendedor asignado
- **THEN** el vehículo queda sin vendedor asignado

#### Scenario: Vaciar un campo que no admite estar vacío

- **WHEN** se edita un vehículo pidiendo explícitamente vaciar un campo obligatorio
- **THEN** la petición se rechaza indicando el campo, y el vehículo no cambia

#### Scenario: Intento de cambiar el estado por la vía de edición

- **WHEN** una petición de edición incluye el estado del vehículo
- **THEN** la petición se rechaza y el estado no cambia

#### Scenario: Edición de un vehículo de otra agencia

- **WHEN** se intenta editar un vehículo que pertenece a otra agencia
- **THEN** la respuesta es la misma que para un vehículo inexistente, y nada se modifica

### Requirement: La edición anuncia qué cambió, no cuánto vale

Cuando una edición modifica al menos un campo, el sistema SHALL publicar un hecho de dominio que identifique al vehículo y enumere **los nombres** de los campos modificados.

El hecho MUST NOT llevar los valores, ni los anteriores ni los nuevos. La restricción existe porque un hecho de dominio no tiene quien pregunta: llevar valores dejaría datos de acceso restringido —el costo de adquisición, entre ellos— al alcance de cualquier consumidor presente o futuro, sin la evaluación de permisos que la API sí hace.

Una edición que no modifica ningún campo MUST NOT publicar nada.

#### Scenario: Edición efectiva

- **WHEN** se edita el precio y el color de un vehículo
- **THEN** se publica un hecho que nombra a esos dos campos

#### Scenario: El hecho no lleva valores

- **WHEN** se edita el costo de adquisición de un vehículo
- **THEN** el hecho publicado nombra al campo y no incluye su valor

#### Scenario: Edición sin efecto

- **WHEN** se edita un vehículo con los mismos valores que ya tenía
- **THEN** no se publica ningún hecho

#### Scenario: La edición falla

- **WHEN** una edición se revierte antes de confirmarse
- **THEN** no se publica ningún hecho

### Requirement: Las reservas no vencen solas

Un vehículo reservado SHALL permanecer reservado hasta que una persona decida lo contrario.

El sistema MUST NOT liberar reservas por el paso del tiempo, ni ofrecer configuración para hacerlo. Volver de reservado a disponible es una transición manual, ya contemplada entre las transiciones legales.

#### Scenario: La reserva sobrevive al calendario

- **WHEN** un vehículo lleva reservado más tiempo del que cualquier convención sugeriría
- **THEN** sigue reservado

#### Scenario: Liberar la reserva

- **WHEN** alguien devuelve un vehículo reservado al estado disponible
- **THEN** la transición se acepta y queda registrada como cualquier otra
