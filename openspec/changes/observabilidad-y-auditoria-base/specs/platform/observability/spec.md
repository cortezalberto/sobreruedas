## Purpose

Define cómo el sistema se deja observar en producción: un identificador único que correlaciona logs, métricas y trazas a través de los saltos de proceso; métricas por endpoint y tenant que no filtran datos entre agencias ni desbordan la cardinalidad; trazas que sobreviven al paso por la cola de eventos; y reporte de errores que no exporta datos personales.

No cubre el registro de auditoría (`audit_logs`), cuyo particionado espera una consulta legal, ni el envío de alertas, que necesita infraestructura no provisionada.

## ADDED Requirements

### Requirement: Identificador único de correlación

El backend SHALL correlacionar logs, métricas y trazas con **un único** identificador por petición.

Cuando exista un contexto de traza distribuida activo, el identificador MUST ser el de esa traza. Cuando no exista —trabajo en segundo plano iniciado fuera de una petición, arranque del proceso—, el sistema MUST generar uno propio, de modo que **nunca** haya registro sin identificador.

El sistema MUST NOT mantener dos identificadores independientes para la misma petición.

Si el cliente provee un identificador de petición en la cabecera acordada, el sistema MUST conservarlo y asociarlo a la traza.

#### Scenario: Petición con contexto de traza activo

- **WHEN** se atiende una petición con un contexto de traza activo
- **THEN** el identificador de correlación es el de esa traza
- **AND** el mismo valor aparece en los registros de log de esa petición

#### Scenario: Trabajo fuera de una petición

- **WHEN** se ejecuta trabajo en segundo plano sin contexto de traza activo
- **THEN** el registro emitido igualmente lleva un identificador de correlación

#### Scenario: El cliente provee su propio identificador

- **WHEN** el cliente envía un identificador de petición en la cabecera acordada
- **THEN** ese valor se conserva y queda asociado a la traza

### Requirement: Registros legibles por máquina

El backend SHALL emitir todo registro de log como un documento estructurado, con el identificador de correlación, el nivel, el origen, el mensaje y la marca temporal como **campos de primer nivel**.

Los registros MUST NOT requerir análisis de texto libre para filtrar por cualquiera de esos campos.

#### Scenario: Formato de un registro

- **WHEN** el sistema emite un registro de log
- **THEN** el registro es un documento estructurado válido
- **AND** expone el identificador de correlación, el nivel, el origen, el mensaje y la marca temporal como campos de primer nivel

### Requirement: Métricas de tráfico por endpoint y tenant

El backend SHALL exponer, para cada petición atendida, un contador de peticiones y una distribución de duración, etiquetados por endpoint, método, clase de resultado y tenant.

El endpoint MUST etiquetarse con la **plantilla de la ruta** y nunca con la ruta concreta. La clase de resultado MUST etiquetarse por familia y no por código exacto. Sin ambas restricciones la cardinalidad es ilimitada por construcción.

El número de series temporales por métrica MUST mantenerse por debajo del techo establecido para el sistema.

#### Scenario: Una petición produce sus métricas

- **WHEN** se atiende una petición
- **THEN** el contador de peticiones y la distribución de duración quedan disponibles
- **AND** llevan las etiquetas de endpoint, método, clase de resultado y tenant

#### Scenario: La ruta concreta no genera series nuevas

- **WHEN** se atienden peticiones a la misma plantilla de ruta con distintos identificadores de recurso
- **THEN** todas contribuyen a la misma serie temporal

#### Scenario: La cardinalidad se mantiene acotada

- **WHEN** se atienden peticiones a múltiples rutas desde múltiples tenants
- **THEN** el número de series por métrica permanece por debajo del techo establecido

### Requirement: Las métricas no identifican a las agencias

El endpoint de métricas SHALL exponerse **sin autenticación** para que el recolector lo consuma, y por lo tanto MUST NOT revelar información que identifique a un tenant.

La etiqueta de tenant MUST ser su identificador opaco. El sistema MUST NOT etiquetar métricas con el nombre comercial de la agencia ni con ningún otro dato que permita reconocerla.

El endpoint de métricas MUST ser alcanzable únicamente desde la red interna del despliegue, y MUST NOT publicarse a través del proxy de entrada.

#### Scenario: La etiqueta de tenant es opaca

- **WHEN** se consulta el endpoint de métricas
- **THEN** las series identifican a cada tenant por su identificador opaco
- **AND** ninguna etiqueta contiene el nombre comercial de la agencia

### Requirement: Centinela de violaciones de aislamiento

El backend SHALL exponer un contador de violaciones de aislamiento multi-tenant, cuyo valor esperado es **siempre cero**.

El contador MUST existir desde el arranque, con valor cero, y no solo cuando ocurra la primera violación: una serie ausente no se distingue de una serie en cero, y sobre esa ambigüedad no se puede alertar.

Cualquier incremento MUST tratarse como incidente de seguridad, no como degradación de servicio.

#### Scenario: El contador existe desde el arranque

- **WHEN** el sistema arranca y no se ha producido ninguna violación
- **THEN** el contador de violaciones de aislamiento está expuesto con valor cero

#### Scenario: Una violación queda registrada

- **WHEN** el mecanismo de aislamiento detecta un acceso fuera del tenant en contexto
- **THEN** el contador se incrementa

### Requirement: Trazas que sobreviven al salto de proceso

El backend SHALL propagar el contexto de traza a través de la cola de eventos, de modo que el trabajo disparado por un evento quede colgado de la misma traza que la petición que lo originó.

#### Scenario: Un evento consumido conserva la traza

- **WHEN** una petición publica un evento y otro proceso lo consume
- **THEN** la traza del consumidor pertenece a la misma traza que la petición que lo publicó

#### Scenario: Muestreo de operaciones fallidas

- **WHEN** una operación falla
- **THEN** su traza se registra, cualquiera sea la proporción de muestreo configurada

### Requirement: La observabilidad no puede ser lo que falla

El backend SHALL arrancar y atender peticiones **aunque no haya destino de trazas ni de errores configurado**, y aunque el configurado no responda.

Un fallo del instrumental MUST NOT impedir el arranque, ni bloquear una petición, ni alterar su resultado.

#### Scenario: Sin destino configurado

- **WHEN** el sistema arranca sin destino de trazas ni de errores configurado
- **THEN** arranca correctamente y atiende peticiones sin exportar

#### Scenario: Destino configurado que no responde

- **WHEN** el destino de trazas está configurado pero no responde
- **THEN** las peticiones se atienden con normalidad y su resultado no cambia

### Requirement: El reporte de errores no exporta datos personales

El backend SHALL descartar el cuerpo de la petición **completo** antes de enviar un evento de error a un servicio externo, conservando únicamente los campos declarados explícitamente como permitidos.

El sistema MUST NOT enviar credenciales, cabeceras de autorización, direcciones de correo ni documentos de identidad. MAY enviar el identificador de tenant y el de correlación, que son necesarios para diagnosticar y no constituyen datos personales. Si envía el identificador del sujeto, MUST hacerlo de forma no reversible.

El filtrado MUST implementarse como lista de permitidos: una lista de prohibidos falla en silencio ante el primer campo no anticipado.

#### Scenario: El cuerpo de la petición no viaja

- **WHEN** se produce un error durante una petición con datos personales en el cuerpo
- **THEN** el evento enviado al servicio externo no contiene el cuerpo de la petición

#### Scenario: Los identificadores de diagnóstico sí viajan

- **WHEN** se produce un error durante una petición de un tenant
- **THEN** el evento enviado conserva el identificador de tenant y el de correlación

#### Scenario: El sujeto no es reconocible

- **WHEN** el evento enviado incluye al sujeto de la petición
- **THEN** lo hace de forma no reversible

### Requirement: Umbrales de alerta coherentes con lo comprometido

El sistema SHALL definir umbrales de página que **nunca sean más permisivos** que el objetivo que pretenden defender.

Las operaciones de listado y de búsqueda MUST tener umbrales separados, por tener objetivos de distinta magnitud. La documentación de cada umbral MUST distinguir el **umbral de página** del **objetivo de ingeniería**, que es más exigente.

Debe existir **una sola** alerta de disponibilidad para los servicios que comparten nodo: varias alertas sobre el mismo hecho físico producen múltiples notificaciones por un único incidente. Las alertas de la cola MUST medir su retraso y su cola de fallidos, que no se deducen de que el nodo esté vivo.

#### Scenario: Listado y búsqueda alertan por separado

- **WHEN** se definen los umbrales de latencia
- **THEN** existe un umbral para listado y otro distinto para búsqueda

#### Scenario: Un solo incidente, una sola notificación

- **WHEN** los servicios que comparten nodo dejan de responder
- **THEN** se emite una única notificación de disponibilidad
