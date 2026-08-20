# platform/domain-events Specification

## Purpose

Establece cómo un módulo le avisa a los demás que algo pasó sin quedarse esperando respuesta, y qué garantiza el sistema sobre ese aviso: qué forma tiene, qué pasa si el consumidor falla, y qué pasa si el mismo aviso llega dos veces.

## Requirements

### Requirement: Sobre canónico del evento

Todo evento de dominio SHALL publicarse con un sobre común que incluya un identificador único del evento, su tipo, la versión de su contrato, el tenant al que pertenece, el instante en que ocurrió y su contenido.

El instante MUST incluir zona horaria. El tipo MUST identificar el hecho ocurrido, no la acción a ejecutar. La versión MUST permitir que un consumidor distinga dos formas del mismo tipo.

#### Scenario: Publicación de un evento

- **WHEN** un módulo publica un evento de dominio
- **THEN** el evento lleva identificador único, tipo, versión, tenant, instante con zona horaria y contenido

#### Scenario: Dos publicaciones del mismo hecho

- **WHEN** el mismo hecho se publica dos veces
- **THEN** cada publicación lleva un identificador de evento distinto

#### Scenario: Evento sin tenant

- **WHEN** se intenta publicar un evento de dominio sin tenant
- **THEN** la publicación es rechazada

### Requirement: El evento no cruza tenants

Un evento SHALL entregarse únicamente a consumidores que lo procesen en el contexto del tenant que lo originó.

El procesamiento de un evento MUST establecer el mismo contexto de tenant que rige para una petición, de modo que las mismas garantías de aislamiento apliquen fuera del ciclo de petición y respuesta.

#### Scenario: Procesamiento bajo el contexto correcto

- **WHEN** un consumidor procesa un evento
- **THEN** lo hace bajo el contexto del tenant que lo originó

#### Scenario: El consumidor no ve datos de otro tenant

- **WHEN** un consumidor procesa un evento y consulta datos
- **THEN** obtiene exclusivamente datos del tenant del evento

### Requirement: Reintento con espera creciente

Cuando el procesamiento de un evento falle, el sistema SHALL reintentarlo, esperando cada vez más entre intentos.

La espera creciente es deliberada: reintentar de inmediato contra una dependencia caída agrega carga justo cuando menos lo tolera. El número de reintentos MUST estar acotado.

#### Scenario: Fallo transitorio

- **WHEN** el procesamiento de un evento falla y el siguiente intento tiene éxito
- **THEN** el evento queda procesado

#### Scenario: La espera crece entre intentos

- **WHEN** un evento falla varias veces seguidas
- **THEN** cada reintento espera más que el anterior

#### Scenario: Reintentos acotados

- **WHEN** un evento falla de forma persistente
- **THEN** los reintentos se detienen tras un número acotado

### Requirement: Los eventos irrecuperables no se pierden

Agotados los reintentos, el evento SHALL conservarse en un destino aparte en lugar de descartarse.

Ese destino MUST permitir inspeccionar qué evento falló y por qué. Un evento irrecuperable MUST NOT bloquear el procesamiento de los siguientes.

#### Scenario: Evento agotado

- **WHEN** un evento agota sus reintentos
- **THEN** queda registrado en el destino de irrecuperables junto con el motivo del último fallo

#### Scenario: La cola sigue avanzando

- **WHEN** un evento agota sus reintentos
- **THEN** los eventos siguientes se procesan normalmente

### Requirement: Entrega al menos una vez, procesamiento sin duplicar efecto

El sistema SHALL garantizar que un evento publicado se entregue al menos una vez, y MUST permitir que un consumidor detecte que ya procesó un evento para no repetir su efecto.

La garantía es "al menos una vez", no "exactamente una vez": el consumidor MUST poder reconocer el identificador del evento como ya visto.

#### Scenario: Entrega repetida

- **WHEN** el mismo evento se entrega dos veces a un consumidor
- **THEN** el consumidor puede reconocer que ya lo procesó
- **AND** el efecto no se aplica dos veces

#### Scenario: Caída antes de confirmar

- **WHEN** un consumidor procesa un evento y cae antes de confirmarlo
- **THEN** el evento vuelve a entregarse
- **AND** no queda sin procesar

### Requirement: El publicador no depende del consumidor

Publicar un evento SHALL desacoplarse de su procesamiento: quien publica MUST NOT quedar esperando a que se procese.

Que no haya ningún consumidor MUST NOT hacer fallar la publicación. Que un consumidor falle MUST NOT propagar el fallo a la petición que originó el evento.

#### Scenario: Sin consumidores

- **WHEN** se publica un evento que ningún consumidor atiende
- **THEN** la publicación es exitosa

#### Scenario: El consumidor falla

- **WHEN** el consumidor de un evento falla al procesarlo
- **THEN** la petición que originó el evento no se ve afectada
