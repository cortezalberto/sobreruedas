# Diseño — C-03 `observabilidad-y-auditoria-base`

## Context

Lo que ya existe, y sobre lo que se construye: [`app/core/observability.py`](../../../backend/app/core/observability.py), 96 líneas escritas por `T-005`. Aporta un `ContextVar` con el identificador de correlación, `configure_logging()` que instala una `LogRecordFactory` —y no un `Filter`, porque los filtros no se propagan a los loggers hijos—, y `CorrelationIdMiddleware`, que lee o genera la cabecera `X-Request-ID`.

Eso es la mitad del pilar de logs y nada de los otros dos.

`ObservabilitySettings` ya declara las cuatro variables que hacen falta. El terreno está preparado; falta construir.

## Goals / Non-Goals

**Goals**

- Los tres pilares correlacionados por un **único** identificador, que sobreviva al salto de proceso por Redis Streams.
- Métricas RED por endpoint **y por tenant**, sin que la etiqueta de tenant se vuelva un canal de fuga ni haga explotar la cardinalidad.
- `rls_violations_total` existiendo y en 0, porque su alerta es P0 y hoy no tiene serie.
- Que la ausencia de backend de observabilidad **no rompa la aplicación**: sin `OTEL_EXPORTER_OTLP_ENDPOINT` la app arranca igual y no exporta.

**Non-Goals**

- `audit_logs` — bloqueada por consulta legal (`ADR-029`).
- Runbooks, Alertmanager, PagerDuty y synthetic monitoring — necesitan el VPS, pausado.
- Dashboards de Grafana versionados como código. Entran cuando haya métricas que dibujar; hacerlos ahora sería dibujar series que no existen.

## Decisions

### D-1 — `correlation_id` se subordina a `trace_id`, no convive con él

**Es la decisión central del change, y la que más cuesta revertir.**

Hoy `CorrelationIdMiddleware` genera un `uuid4()` por petición. Cuando entre OpenTelemetry va a haber un segundo identificador: el `trace_id` del contexto de span, 128 bits en hexadecimal, formato W3C `traceparent`. Dos identificadores por petición es exactamente la clase de duplicación que este proyecto ya pagó cara con las tres listas de secciones del frontend: nadie los obliga a coincidir y se desincronizan sin ruido.

**Se propone**: el `trace_id` de OpenTelemetry es la fuente única. `get_correlation_id()` pasa a devolverlo, y el `uuid4()` queda solo como respaldo para cuando no hay span activo —tareas de Celery arrancadas fuera de una petición, arranque de la app—.

La cabecera `X-Request-ID` **se conserva** de entrada: si el cliente la manda, se usa como semilla y se registra como atributo del span. Quitarla rompería a quien ya la esté logueando del otro lado.

⚠️ **Consecuencia a aceptar**: el identificador deja de ser un UUID con guiones y pasa a ser 32 caracteres hexadecimales. Cualquier cosa que hoy parsee el log esperando un UUID se rompe. Hoy no hay nada — es el momento barato de hacerlo.

### D-2 — La etiqueta de tenant en las métricas es el ID, y nunca el nombre

`knowledge-base/13` pide métricas RED *"por endpoint y tenant"*. Dos riesgos, y el segundo es de seguridad:

- **Cardinalidad**: el techo son 1.000 series únicas por métrica. `http_requests_total{endpoint, method, status, tenant}` multiplica los cuatro ejes. Con 50 endpoints × 4 métodos × 5 códigos × N tenants, el techo se toca en **N = 1**. Hay que acotar: el `endpoint` se etiqueta con la **plantilla de ruta** (`/api/v1/vehicles/{id}`) y nunca con la URL concreta, y el `status` con la clase (`2xx`, `4xx`, `5xx`) y no con el código.
- **Fuga**: `/metrics` es un endpoint sin autenticar por convención. Etiquetar con el **nombre** de la agencia publicaría la cartera de clientes a cualquiera que lo consulte. Va el **UUID** del tenant, que no dice nada por sí mismo.

⚠️ Aun con el UUID, `/metrics` revela **cuántos** tenants hay y cuánto tráfico tiene cada uno. Sobre el VPS único hay que dejarlo accesible solo desde la red interna de Docker, nunca por el reverse proxy. Va como escenario de la delta spec, no como comentario.

### D-3 — Una sola alerta de disponibilidad, y las de la cola miden lo que la cola hace

Aplicación directa de [`ESC-002`](../../../docs/escalaciones/ESC-002-slo-internos-sobre-nodo-unico.md). Había cuatro SLO de disponibilidad —API, frontend, webhooks, cola— y por `ADR-023` los nueve servicios comparten el nodo. **Ningún componente puede estar más disponible que la máquina que lo hospeda**: la cola declaraba 99,95 % (21,6 min/mes) contra una API de 99,7 % (130 min/mes) en el mismo hierro.

Cuatro alertas con umbrales distintos sobre el mismo hecho físico dispararían juntas y darían **cuatro páginas por un incidente**. Va **una** alerta de disponibilidad del nodo. Las de la cola miden `lag` y `DLQ` —`WorkerQueueLagHigh`, `DLQGrowing`—, que es lo que la cola hace y no se deduce de que la máquina esté viva.

### D-4 — `APILatencyHigh` se parte en dos

Por [`ADR-030`](../../../docs/adr/ADR-030-objetivo-de-ingenieria-y-slo-de-latencia.md). El catálogo la tiene en `p95 > 500 ms durante 15 min`, y eso era **más permisivo que el SLO que debía defender**: el umbral de página del listado es 300 ms.

| Alerta | Umbral de página | Sostenido |
|---|---|---|
| `APIListLatencyHigh` | p95 > **300 ms** | 15 min |
| `APISearchLatencyHigh` | p95 > **2,0 s** | 15 min |

⚠️ Los 2,0 s valen **solo** como umbral de página. El objetivo de ingeniería de búsqueda son **500 ms incondicionales** —N0 no le pone el calificador *"en condiciones normales de carga"* que sí le pone al listado—. Que no despierte a nadie no significa que esté bien, y esa distinción va escrita al lado de la regla o se pierde.

### D-5 — El scrubbing de Sentry es una lista de permitidos, no de prohibidos

Una lista de prohibidos (`password`, `token`, `dni`…) falla en silencio con el primer campo que nadie anticipó, y con Ley 25.326 encima el costo de ese fallo no es un bug: es una notificación de incidente.

**Decidido**: `send_default_pii=False`, y un `before_send` que **descarta el cuerpo de la petición entero** y conserva solo una lista explícita de cabeceras y campos. El `tenant_id` y el `trace_id` se conservan —hacen falta para diagnosticar y no son datos personales—; el sujeto se conserva **seudonimizado**.

#### D-5.1 — Seudónimo por HMAC, no cifrado y no hash pelado

> **Decidido el 19-ago-2026.** El pedido fue: *"que sirva para agrupar «a esta persona le falla siempre lo mismo»"*. Eso se cumple con cualquiera de las tres formas; las tres protegen distinto.

| Forma | Agrupa | Se puede volver atrás |
|---|---|---|
| **Cifrado** | sí | **Sí** — existe la clave. El dato sigue siendo personal, solo que guardado con llave, y ahora la llave también es un problema |
| **Hash pelado** (`sha256(sub)`) | sí | **En la práctica, sí.** El `sub` es un UUID de un conjunto enumerable: cualquiera con la tabla `users` hashea las N filas y arma la tabla de equivalencias en segundos |
| **HMAC con clave del servidor** | sí | **No**, sin la clave. Y la clave no sale del servidor ni viaja a Sentry |

Va **HMAC-SHA256**. Es lo único que cumple "agrupar sin identificar" contra alguien que tenga los datos del otro lado, que es exactamente el escenario que Sentry introduce: el proveedor ve los eventos.

**La clave se deriva, no se agrega.** Se usa HKDF sobre `TENANT_SECRETS_MASTER_KEY` con la etiqueta `sentry-subject-pseudonym`. Dos motivos: no se toca `ADR-013` ni la paridad de variables de entorno, y no se reutiliza la clave maestra tal cual para un segundo propósito —separar claves por uso es lo que evita que comprometer una comprometa la otra—.

⚠️ **Consecuencia asumida**: si la clave maestra rota, los seudónimos anteriores dejan de coincidir con los nuevos y el agrupamiento histórico se corta. Es el precio de que no se puedan revertir, y es el lado correcto del que equivocarse.

### D-7 — El presupuesto de RAM se mide, y si no entra se escala

> **Decidido el 19-ago-2026.** Cuatro servicios de observabilidad más sobre el VPS único, que ya corre PostgreSQL, Redis, OpenSearch, Keycloak, MinIO, backend, worker y frontend.

**No se ajusta por lo bajo.** Si medir dice que no entra, la salida **no** es recortar retenciones, bajar el scrape o apagar un pilar en silencio: eso convertiría una restricción de infraestructura en una pérdida de capacidad que nadie decidió y que después nadie recuerda haber aceptado.

La salida es una **escalación**, con el patrón que el proyecto ya tiene: [`ESC-001`](../../../docs/escalaciones/ESC-001-sla-sobre-nodo-unico.md) y [`ESC-002`](../../../docs/escalaciones/ESC-002-slo-internos-sobre-nodo-unico.md) son los dos precedentes, y los dos nacieron del mismo hecho físico —un solo nodo— con el mismo desenlace: se ajustó lo prometido, explícitamente y por escrito.

El techo del 15 % del costo de infraestructura lo fija `knowledge-base/13`. Sobre nodo único puede ser directamente inalcanzable; si lo es, **es un dato para Dirección, no un parámetro para tocar**.

### D-8 — `/metrics` sin autenticar, y solo de puertas para adentro

> **Confirmado el 19-ago-2026.**

Sin autenticación, porque es lo que el recolector espera y meterle credenciales agrega un secreto más para rotar sin agregar seguridad real. Alcanzable **únicamente desde la red interna de Docker**, y **nunca** publicado por el reverse proxy.

⚠️ **La configuración del proxy es del bloque 9 de C-01, que está pausado.** Hasta que exista, el aislamiento depende de no publicar el puerto en `docker-compose.yml` — que es suficiente en dev y **no** es una garantía en producción. Queda como tarea explícita del bloque 9 cuando el VPS se reanude, no como algo que este change deja resuelto.

### D-6 — Sin backend de observabilidad, la app arranca igual

`OTEL_EXPORTER_OTLP_ENDPOINT` y `SENTRY_DSN` son opcionales en `ObservabilitySettings` y tienen que seguir siéndolo. Un exportador que no puede conectarse **no puede tumbar la aplicación**: la observabilidad es para saber que algo anda mal, no para ser lo que anda mal.

En dev y en la suite de tests eso es lo normal —no hay Tempo—, así que el camino sin exportador es el que más se ejecuta y necesita su propio test.

## Risks / Trade-offs

| Riesgo | Mitigación |
|---|---|
| **Presupuesto de RAM.** Prometheus + Grafana + Loki + Tempo sobre el mismo VPS que PostgreSQL, Redis, OpenSearch, Keycloak y MinIO | Medir antes de fijar retenciones. El techo del 15 % de costo es de `knowledge-base/13` y sobre nodo único puede ser inalcanzable — si lo es, **es una escalación, no un ajuste silencioso** |
| **`pip-audit` bloqueante.** Siete dependencias nuevas en un gate que no se afloja | Auditar antes de cablear. Si una arrastra una vulnerabilidad alta, se elige otra o se escala — el precedente es `@vitejs/plugin-react`, que se sacó del frontend por esto mismo |
| **Cardinalidad.** El techo de 1.000 series se toca fácil | Plantilla de ruta y clase de status. Y un test que cuente series, porque el día que se rompa nadie lo va a ver mirando |
| **Sobrecarga del middleware.** Cada petición mide, correlaciona y crea span | El objetivo de ingeniería del listado son 200 ms. Medir el costo del propio instrumental, y que quede escrito |

## Migration Plan

Sin migración de base —`audit_logs` no entra—, así que la regla dura 13 no aplica.

El orden importa por una razón: **D-1 toca el módulo que ya está en producción de dev**. Va primero, con sus tests, y recién después se cuelgan métricas y trazas encima. Al revés habría que reescribir la correlación con dos consumidores ya enganchados.

1. Dependencias y auditoría (`pip-audit` verde antes de escribir código de aplicación)
2. `T-028` logging JSON + D-1
3. `T-029` métricas
4. `T-030` trazas + propagación por Redis Streams
5. `T-031` Sentry
6. Servicios de compose y `check-services.sh`

## Open Questions

> ✅ **Las tres cerradas el 19-ago-2026 por el decisor humano.** Pasaron a decisiones: `D-7` (presupuesto de RAM), `D-8` (`/metrics`) y `D-5.1` (seudónimo del sujeto). Se conservan acá con su resolución porque el recorrido explica por qué la decisión es la que es.

1. ~~**¿El techo del 15 % de costo es alcanzable sobre nodo único?**~~ → **`D-7`**: se mide, y si no entra **se escala**. No se recortan retenciones por lo bajo.
2. ~~**¿`/metrics` va sin autenticar?**~~ → **`D-8`**: sí, sin autenticar, y **solo** de puertas para adentro. El aislamiento real depende del bloque 9 de C-01, que está pausado; queda dicho y no dado por resuelto.
3. ~~**¿El sujeto en Sentry va hasheado o no va?**~~ → **`D-5.1`**: va, **seudonimizado con HMAC**. El pedido fue poder agrupar *"a esta persona le falla siempre lo mismo"*, y eso se cumple sin que el seudónimo se pueda revertir. ⚠️ **No es cifrado** —eso sería reversible y el dato seguiría siendo personal— **ni hash pelado** —el `sub` es un UUID de conjunto enumerable: con la tabla `users` se arma la equivalencia en segundos—.

Ninguna queda abierta. El bloque 0 de `tasks.md` puede tildarse.
