## Purpose

Define el contrato de configuración del sistema: qué variables de entorno lee, cuáles son obligatorias, cómo falla cuando falta alguna, y la garantía de que ningún valor sensible se exponga por logs, trazas o serialización.

## ADDED Requirements

### Requirement: Contrato declarado de variables de entorno

El sistema SHALL declarar en el repositorio la lista completa de variables de entorno que lee, cada una con descripción, valor de ejemplo ficticio y marca de si es sensible. Este archivo declarativo MUST NOT contener valores reales de ningún ambiente.

Toda variable que el código lea MUST estar declarada. Una variable declarada que ningún componente lee MUST eliminarse del contrato.

#### Scenario: El contrato cubre todo lo que el código lee

- **WHEN** se comparan las variables leídas por el código contra el archivo de contrato
- **THEN** no existe ninguna variable leída que falte en el contrato
- **AND** no existe ninguna variable en el contrato que nadie lea

#### Scenario: El contrato no filtra secretos

- **WHEN** se inspecciona el archivo de contrato versionado
- **THEN** todos los campos marcados como sensibles están vacíos o contienen un valor evidentemente ficticio
- **AND** el escaneo de secretos del pipeline no reporta hallazgos sobre él

### Requirement: Fallo temprano ante configuración incompleta o inválida

El sistema SHALL validar la configuración completa durante el arranque, antes de aceptar tráfico. Si falta una variable obligatoria o un valor no satisface su tipo o formato, el proceso MUST terminar inmediatamente con un error que **nombre la variable concreta** y la razón del rechazo.

El sistema MUST NOT arrancar en estado degradado ni diferir la validación al primer uso de la variable.

#### Scenario: Falta una variable obligatoria

- **WHEN** el servicio arranca sin una variable obligatoria definida
- **THEN** el proceso termina con código de salida distinto de cero
- **AND** el mensaje de error nombra la variable ausente
- **AND** el servicio no queda escuchando en su puerto

#### Scenario: Una variable tiene un valor con tipo inválido

- **WHEN** una variable numérica recibe un valor no numérico
- **THEN** el proceso termina durante el arranque
- **AND** el mensaje de error nombra la variable y el tipo esperado

#### Scenario: Configuración completa y válida

- **WHEN** todas las variables obligatorias están definidas con valores válidos
- **THEN** el servicio completa el arranque y acepta tráfico

### Requirement: Los valores sensibles nunca se exponen

El sistema SHALL enmascarar todo valor marcado como sensible en cualquier representación textual de la configuración: logs, mensajes de error, trazas, respuestas de la API y serialización a estructuras de datos.

Un valor sensible MUST NOT aparecer en claro fuera del componente que lo consume, ni siquiera en modo de desarrollo o depuración.

#### Scenario: Serialización de la configuración

- **WHEN** la configuración se serializa a una estructura de datos
- **THEN** los campos sensibles aparecen enmascarados
- **AND** ningún valor sensible en claro está presente en el resultado

#### Scenario: Fallo de arranque por credencial inválida

- **WHEN** el arranque falla porque una credencial es inválida
- **THEN** el mensaje de error nombra la variable
- **AND** el mensaje no incluye el valor de la credencial

#### Scenario: Registro de la configuración al arrancar

- **WHEN** el servicio registra su configuración efectiva durante el arranque
- **THEN** las entradas correspondientes a campos sensibles aparecen enmascaradas

### Requirement: El ambiente activo condiciona el comportamiento

El sistema SHALL derivar su comportamiento sensible al ambiente de una única variable que identifique el ambiente activo, con valores acotados a un conjunto cerrado.

Un valor fuera de ese conjunto MUST rechazarse durante el arranque. En el ambiente de producción, las facilidades de desarrollo y depuración MUST estar deshabilitadas.

#### Scenario: Ambiente no reconocido

- **WHEN** la variable de ambiente recibe un valor fuera del conjunto permitido
- **THEN** el proceso termina durante el arranque
- **AND** el mensaje de error enumera los valores permitidos

#### Scenario: Producción deshabilita las facilidades de desarrollo

- **WHEN** el servicio arranca con el ambiente de producción activo
- **THEN** las facilidades de desarrollo y depuración no están accesibles
