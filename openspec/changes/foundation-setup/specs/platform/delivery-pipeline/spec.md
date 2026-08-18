## Purpose

Define las garantías que el pipeline impone sobre todo cambio antes de llegar a la rama principal y a staging: umbrales de cobertura, calidad estática, seguridad de dependencias y el contrato de despliegue con reversión automática.

## ADDED Requirements

### Requirement: Quality gate de cobertura

El pipeline SHALL bloquear la integración de todo cambio cuya cobertura de tests del backend quede por debajo de **80 % de líneas a nivel global**.

Este umbral deriva del Artículo 2 de la constitución, que es norma vinculante de nivel N0 según `ADR-000`. Ningún documento de menor nivel puede rebajarlo.

Complementariamente, el pipeline MUST exigir un mínimo de **60 % de cobertura de ramas**. La constitución no se pronuncia sobre ramas, por lo que rige el plan de testing dentro de su dominio propio.

La cobertura MUST NOT decrecer respecto de la rama principal. Un cambio que la reduzca MUST quedar bloqueado, y solo puede integrarse con una justificación documentada de forma explícita.

#### Scenario: Cobertura por debajo del umbral de líneas

- **WHEN** un cambio deja la cobertura de líneas del backend por debajo del 80 % global
- **THEN** el pipeline falla
- **AND** el cambio no puede integrarse a la rama principal
- **AND** el reporte indica la cobertura obtenida y el umbral exigido

#### Scenario: Cobertura por debajo del umbral de ramas

- **WHEN** un cambio deja la cobertura de ramas por debajo del 60 %
- **THEN** el pipeline falla

#### Scenario: Cobertura que decrece sin quedar bajo el umbral

- **WHEN** un cambio reduce la cobertura respecto de la rama principal pero se mantiene sobre el 80 %
- **THEN** el pipeline señala el descenso y bloquea la integración
- **AND** la integración solo procede con una justificación documentada

#### Scenario: Cambio que cumple los umbrales

- **WHEN** un cambio mantiene la cobertura en o por encima de los umbrales y no la reduce
- **THEN** el gate de cobertura pasa

### Requirement: Calidad estática bloqueante

El pipeline SHALL bloquear todo cambio que no satisfaga las reglas de formato, linting y tipado estático, tanto en el backend como en el frontend.

El tipado MUST verificarse en modo estricto en ambos. Un error de tipos MUST tratarse igual que un test que falla: bloquea.

#### Scenario: Violación de reglas de linting

- **WHEN** un cambio introduce una violación de las reglas de linting
- **THEN** el pipeline falla e identifica el archivo y la regla violada

#### Scenario: Error de tipado estático

- **WHEN** un cambio introduce un error detectable por el verificador de tipos en modo estricto
- **THEN** el pipeline falla
- **AND** el cambio no puede integrarse

#### Scenario: Código conforme

- **WHEN** un cambio satisface formato, linting y tipado en backend y frontend
- **THEN** los jobs de calidad estática pasan

### Requirement: Seguridad de dependencias y secretos

El pipeline SHALL auditar las dependencias de backend y frontend en cada cambio, y MUST bloquear ante vulnerabilidades de severidad alta o crítica.

Ese umbral es un **piso, no un techo**: un auditor MAY bloquear también por debajo de él. Lo que ningún auditor puede es quedar por encima — ni con una excepción puntual por hallazgo, ni neutralizando su código de salida, ni declarándose no bloqueante.

Cuando un auditor no expone la severidad de sus hallazgos, MUST bloquear ante cualquiera. La alternativa —mantener a mano una lista de excepciones— convierte cada build rojo en una invitación a agregar una entrada, y no hay forma de saber si esa entrada tapaba una crítica.

El pipeline MUST además escanear el cambio en busca de secretos filtrados y bloquear ante **cualquier** detección, sin umbral de severidad.

#### Scenario: Dependencia con vulnerabilidad crítica

- **WHEN** un cambio introduce o mantiene una dependencia con vulnerabilidad crítica
- **THEN** el pipeline falla e identifica la dependencia y la vulnerabilidad

#### Scenario: Secreto filtrado en el cambio

- **WHEN** un cambio incluye un valor que el escáner identifica como secreto
- **THEN** el pipeline falla
- **AND** el cambio no puede integrarse

#### Scenario: Severidad por debajo del piso

- **WHEN** un auditor expone la severidad de sus hallazgos y solo encuentra vulnerabilidades de severidad baja o media
- **THEN** el pipeline las reporta sin bloquear
- **WHEN** un auditor no expone la severidad de sus hallazgos
- **THEN** el pipeline bloquea ante cualquier hallazgo

#### Scenario: Auditor que afloja por debajo del piso

- **WHEN** un auditor de dependencias se configura con una excepción por hallazgo, con su código de salida neutralizado, o como no bloqueante
- **THEN** la verificación del pipeline falla e identifica el auditor aflojado

### Requirement: Ejecución del pipeline en cada propuesta de cambio

El pipeline SHALL ejecutarse automáticamente sobre toda propuesta de cambio dirigida a la rama principal, y sobre cada integración a esa rama.

La ejecución completa MUST terminar en menos de 15 minutos para un cambio sin modificaciones sustantivas.

#### Scenario: Propuesta de cambio abierta

- **WHEN** se abre una propuesta de cambio contra la rama principal
- **THEN** el pipeline se ejecuta automáticamente

#### Scenario: Duración de la ejecución

- **WHEN** el pipeline corre sobre un cambio sin modificaciones sustantivas
- **THEN** la ejecución completa termina en menos de 15 minutos

### Requirement: Despliegue automático a staging con reversión

Toda integración a la rama principal que haya superado el pipeline SHALL desplegarse automáticamente al ambiente de staging.

El despliegue MUST verificarse con pruebas de humo posteriores que comprueben las sondas de vida y disponibilidad. Si esas pruebas fallan, el sistema MUST revertir automáticamente a la versión anterior y notificar al equipo.

Un despliegue MUST identificarse unívocamente con el identificador del commit que lo originó.

#### Scenario: Integración exitosa a la rama principal

- **WHEN** un cambio se integra a la rama principal tras superar el pipeline
- **THEN** se despliega automáticamente a staging
- **AND** staging refleja el cambio en menos de 15 minutos

#### Scenario: Las pruebas de humo posteriores fallan

- **WHEN** las pruebas de humo posteriores al despliegue fallan
- **THEN** el sistema revierte automáticamente a la versión anterior
- **AND** notifica al equipo
- **AND** staging queda sirviendo la versión anterior en estado consistente

#### Scenario: Trazabilidad del despliegue

- **WHEN** se inspecciona una versión desplegada en staging
- **THEN** puede identificarse unívocamente el commit que la originó
