## Purpose

Expone las sondas que permiten a los orquestadores, balanceadores y pipelines de despliegue distinguir un servicio vivo de uno listo para recibir tráfico, incluido su comportamiento cuando una dependencia externa no responde.

## ADDED Requirements

### Requirement: Sonda de vida

El backend SHALL exponer una sonda de vida que responda con éxito siempre que el proceso esté en funcionamiento, **sin consultar dependencias externas**.

La respuesta MUST incluir la versión desplegada y una marca temporal. La sonda MUST NOT requerir autenticación y MUST responder en menos de 100 ms bajo condiciones normales.

#### Scenario: Servicio en funcionamiento

- **WHEN** se consulta la sonda de vida con el servicio en funcionamiento
- **THEN** la respuesta es exitosa
- **AND** el cuerpo incluye la versión desplegada y una marca temporal

#### Scenario: La sonda de vida ignora las dependencias caídas

- **WHEN** una dependencia externa está caída pero el proceso sigue en funcionamiento
- **THEN** la sonda de vida sigue respondiendo con éxito

#### Scenario: La sonda de vida es pública

- **WHEN** se consulta la sonda de vida sin credenciales
- **THEN** la respuesta es exitosa

### Requirement: Sonda de disponibilidad

El backend SHALL exponer una sonda de disponibilidad que verifique que las dependencias necesarias para atender tráfico responden.

Si todas responden, la sonda MUST indicar disponibilidad. Si alguna no responde, la sonda MUST indicar **no disponible** e identificar **cuál** dependencia falló, sin exponer credenciales ni cadenas de conexión.

#### Scenario: Todas las dependencias responden

- **WHEN** se consulta la sonda de disponibilidad y todas las dependencias responden
- **THEN** la sonda indica que el servicio está disponible

#### Scenario: Una dependencia no responde

- **WHEN** una dependencia requerida deja de responder
- **THEN** la sonda indica que el servicio no está disponible
- **AND** la respuesta identifica la dependencia que falló
- **AND** la respuesta no incluye credenciales ni cadenas de conexión

#### Scenario: Recuperación tras restablecer la dependencia

- **WHEN** una dependencia caída vuelve a responder
- **THEN** la sonda vuelve a indicar disponibilidad sin reiniciar el servicio

### Requirement: La documentación interactiva de la API no se expone en producción

El sistema SHALL servir la documentación interactiva de la API únicamente en ambientes distintos de producción.

En producción, las rutas de documentación MUST NOT estar accesibles.

#### Scenario: Documentación disponible fuera de producción

- **WHEN** se accede a la documentación interactiva en un ambiente de desarrollo
- **THEN** la documentación se sirve correctamente

#### Scenario: Documentación bloqueada en producción

- **WHEN** se accede a la documentación interactiva con el ambiente de producción activo
- **THEN** la ruta no está disponible

### Requirement: Correlación de peticiones

El sistema SHALL asignar a cada petición entrante un identificador de correlación, propagarlo a los registros que la petición genere y devolverlo en la respuesta.

Si la petición llega con un identificador de correlación provisto por el cliente, el sistema MUST reutilizarlo en lugar de generar uno nuevo.

#### Scenario: Petición sin identificador de correlación

- **WHEN** llega una petición sin identificador de correlación
- **THEN** el sistema genera uno
- **AND** lo devuelve en la respuesta
- **AND** los registros generados por esa petición lo incluyen

#### Scenario: Petición con identificador de correlación provisto

- **WHEN** llega una petición con un identificador de correlación
- **THEN** el sistema reutiliza ese identificador
- **AND** lo devuelve sin modificarlo en la respuesta
