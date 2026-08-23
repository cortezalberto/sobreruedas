## ADDED Requirements

### Requirement: Las convenciones se verifican sobre las rutas expuestas

Las convenciones de esta capacidad SHALL ser exigibles sobre las rutas que la aplicación realmente expone, y no únicamente sobre los módulos que las implementan.

El sistema MUST verificar automáticamente, recorriendo las rutas registradas:

- que toda operación de creación acepte una clave de idempotencia;
- que toda operación que devuelva una colección acepte cursor y tamaño de página;
- que ninguna operación de creación con clave de idempotencia elija la forma de su respuesta según los permisos de quien llama.

Una ruta que legítimamente no cumpla alguna de estas condiciones MUST figurar en una lista de excepciones **con su motivo**, y MUST NOT quedar exenta por omisión.

> **Por qué este requisito existe**: los mecanismos de paginación por cursor e idempotencia estaban implementados, probados en aislamiento y **sin un solo consumidor** en toda la aplicación. Los requisitos que los describen se leían como si las rutas los cumplieran, y ninguna los cumplía. Una convención que solo vive en una spec se rompe el día que alguien tiene apuro; el precedente de que un recorrido de rutas encuentra lo que la lectura da por bueno ya existe en este sistema, tanto para la exigencia de token como para la cobertura de la matriz de permisos.

#### Scenario: Creación sin clave de idempotencia

- **WHEN** se expone una operación de creación que no acepta clave de idempotencia y no figura entre las excepciones
- **THEN** la verificación falla nombrando la ruta

#### Scenario: Colección sin paginación

- **WHEN** se expone una operación que devuelve una colección sin aceptar cursor y tamaño de página, y no figura entre las excepciones
- **THEN** la verificación falla nombrando la ruta

#### Scenario: Excepción declarada con motivo

- **WHEN** una ruta que no pagina figura en la lista de excepciones con su motivo
- **THEN** la verificación pasa

#### Scenario: Excepción sin motivo

- **WHEN** una ruta figura entre las excepciones sin motivo declarado
- **THEN** la verificación falla

#### Scenario: Respuesta de creación dependiente del rol

- **WHEN** una operación de creación con clave de idempotencia elige la forma de su respuesta según los permisos de quien llama
- **THEN** la verificación falla
