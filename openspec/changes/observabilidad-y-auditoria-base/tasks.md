# Tareas — C-03 `observabilidad-y-auditoria-base`

> **Gobernanza ALTA.** Define el audit trail —evidencia de compliance— y los umbrales de alerta que gobiernan la operación. **Proponer y esperar revisión: ninguna casilla se tilda sin aprobación humana de `design.md`.**
>
> **TDD estricto.** Cada tarea de implementación empieza por un test que falla. Los tests que tocan Redis van contra Redis real vía testcontainers (regla dura 8).
>
> **Orden no libre.** El bloque 1 va primero: toca `app/core/observability.py`, que ya está en uso. Ver `design.md` · *Migration Plan*.

## 0. Portón de revisión

- [ ] 0.1 `design.md` revisado y aprobado por el decisor humano — **si no, detenerse acá**
- [ ] 0.2 Confirmar las tres preguntas abiertas de `design.md`: techo de costo del 15 %, exposición de `/metrics`, y el `sub` hasheado en Sentry
- [ ] 0.3 Verificar que la consulta legal de `ADR-029` sigue sin respuesta; si llegó, `T-011` (`audit_logs`) vuelve al alcance y este change se replantea

## 1. Dependencias — antes de cualquier código de aplicación

- [ ] 1.1 Agregar a `pyproject.toml`: `python-json-logger`, `prometheus-client`, `sentry-sdk`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-sqlalchemy`
- [ ] 1.2 Correr `pip-audit` y verificar que las siete pasan el gate. **Si alguna arrastra una vulnerabilidad alta o crítica, se elige otra o se escala** — el gate no se afloja (`ADR-027`), y el precedente es `@vitejs/plugin-react` en el frontend
- [ ] 1.3 Verificar que `check-config-parity.py` sigue en 0 divergencias: no se agregan variables de entorno, se usan las cuatro que `ADR-013` ya declara

## 2. Logging estructurado y correlación — `T-028` · decisión `D-1`

- [ ] 2.1 Test: todo registro sale como **JSON válido** y trae `trace_id`, `level`, `logger`, `message` y `timestamp` como campos de primer nivel
- [ ] 2.2 Reemplazar el formateador de texto de `configure_logging()` por uno JSON, conservando la `LogRecordFactory` — los filtros no se propagan a los loggers hijos y por eso no se usan
- [ ] 2.3 Test: con un span de OpenTelemetry activo, `get_correlation_id()` devuelve el **`trace_id` del span** y no un `uuid4()` propio (`D-1`)
- [ ] 2.4 Test: **sin** span activo —una tarea de Celery arrancada fuera de una petición— sigue habiendo identificador, y es el respaldo `uuid4()`. Es el camino que más se ejecuta en la suite
- [ ] 2.5 Test: la cabecera `X-Request-ID` que manda el cliente se conserva y queda como atributo del span. Quitarla rompería a quien ya la loguee del otro lado
- [ ] 2.6 Subordinar `correlation_id` a `trace_id` en `observability.py`, con el `uuid4()` como respaldo
- [ ] 2.7 Verificar que los 367 tests unitarios existentes siguen verdes: `observability.py` está cableado en `main.py` y lo toca toda la suite

## 3. Métricas Prometheus — `T-029` · decisión `D-2`

- [ ] 3.1 Test: `http_requests_total` y `http_request_duration_seconds` existen tras una petición, con las etiquetas `endpoint`, `method`, `status` y `tenant`
- [ ] 3.2 Test: el `endpoint` se etiqueta con la **plantilla de ruta** (`/api/v1/vehicles/{id}`) y no con la URL concreta. Sin esto la cardinalidad es ilimitada por construcción
- [ ] 3.3 Test: el `status` se etiqueta con la **clase** (`2xx`/`4xx`/`5xx`) y no con el código exacto
- [ ] 3.4 Test: la etiqueta de tenant es el **UUID** y **nunca** el nombre de la agencia. `/metrics` no autentica: el nombre publicaría la cartera de clientes
- [ ] 3.5 Test de cardinalidad: tras N peticiones a rutas distintas de M tenants, el conteo de series se mantiene bajo el techo de **1.000 por métrica**
- [ ] 3.6 Implementar el middleware de métricas y exponer `/metrics`
- [ ] 3.7 Test: **`rls_violations_total` existe y arranca en 0.** Es el centinela que `knowledge-base/13` declara *"siempre 0"* y su alerta es P0 tratada como incidente de seguridad
- [ ] 3.8 Implementar `rls_violations_total` y cablearlo donde el guard de aislamiento detecta la violación
- [ ] 3.9 Medir el costo del propio instrumental sobre el objetivo de ingeniería de 200 ms del listado, y dejarlo escrito

## 4. Trazas con OpenTelemetry hacia Tempo — `T-030`

> ⚠️ **La tarea original está mal especificada.** Pide levantar `jaeger` en compose con UI en `:16686` y verificar ahí. La decisión vigente es **Tempo** ([`ADR-016`](../../../docs/adr/ADR-016-trazas-distribuidas-tempo.md), cierra `IN-15`) y la verificación se hace **desde Grafana**. Corregido acá.

- [ ] 4.1 Test: **sin `OTEL_EXPORTER_OTLP_ENDPOINT` la aplicación arranca y sirve peticiones**, sin exportar (`D-6`). Es el estado de dev y de toda la suite
- [ ] 4.2 Test: un endpoint OTLP inalcanzable **no tumba la aplicación** ni bloquea la petición. La observabilidad no puede ser lo que anda mal
- [ ] 4.3 Instrumentar FastAPI y SQLAlchemy, con exportador OTLP apuntando a Tempo
- [ ] 4.4 Test: el sampling respeta `OTEL_TRACES_SAMPLER_ARG`, con **100 % en operaciones fallidas** sea cual sea el ratio configurado
- [ ] 4.5 Test: **el `trace_id` sobrevive al salto por Redis Streams.** Se publica un evento dentro de una petición, lo consume el worker, y la traza del consumidor cuelga de la misma raíz. Contra Redis real
- [ ] 4.6 Implementar la propagación del contexto W3C `traceparent` en el publisher y el consumer de `app/core/events.py`
- [ ] 4.7 Levantar `tempo` y `grafana` en `docker-compose.yml`, y verificar la traza de punta a punta **desde Grafana**

## 5. Sentry con scrubbing de PII — `T-031` · decisión `D-5`

- [ ] 5.1 Test: con `SENTRY_DSN` ausente la aplicación arranca igual y no inicializa nada
- [ ] 5.2 Test: el `before_send` **descarta el cuerpo de la petición entero**. Lista de permitidos, no de prohibidos: una lista de prohibidos falla en silencio con el primer campo que nadie anticipó
- [ ] 5.3 Test: no viajan cabeceras de autorización, ni email, ni DNI/CUIT. Se planta un evento con los cuatro y se verifica que ninguno sale
- [ ] 5.4 Test: **sí** viajan `tenant_id` y `trace_id` —hacen falta para diagnosticar y no son datos personales— y el `sub` del usuario va **hasheado**
- [ ] 5.5 Implementar la inicialización con `send_default_pii=False` y el `before_send`

## 6. Alertas — reglas de Prometheus, sin Alertmanager

> El envío (Alertmanager → PagerDuty), los runbooks RB-001…RB-017 y el synthetic monitoring necesitan el VPS, que está **pausado por decisión de Dirección**. Entran las reglas, que son las que dependen de que existan las series.

- [ ] 6.1 Escribir **una sola** alerta de disponibilidad del nodo (`D-3`). Cuatro SLO sobre el mismo hierro darían cuatro páginas por un incidente (`ESC-002`)
- [ ] 6.2 Partir `APILatencyHigh` en `APIListLatencyHigh` (p95 > **300 ms**) y `APISearchLatencyHigh` (p95 > **2,0 s**), sostenidas 15 min (`ADR-030`, `D-4`)
- [ ] 6.3 Dejar escrito al lado de la regla que los 2,0 s son **umbral de página y no objetivo**: el objetivo de ingeniería de búsqueda son 500 ms incondicionales, porque N0 no le pone el calificador de carga normal que sí le pone al listado
- [ ] 6.4 `RLSViolationDetected` sobre `rls_violations_total`: **P0 ante cualquier incremento**, no ante un umbral
- [ ] 6.5 `WorkerQueueLagHigh` (lag > 2 min) y `DLQGrowing` (> 100 eventos/hora), que miden lo que la cola hace y no se deduce de que la máquina esté viva
- [ ] 6.6 Levantar `prometheus` y `loki` en compose, y enseñarle los cuatro servicios nuevos a `tools/check-services.sh` — si no los conoce, reporta de menos

## 7. Verificación de cierre

- [ ] 7.1 Los escenarios de la delta spec `platform/observability` cubiertos por tests ejecutables
- [ ] 7.2 Cobertura del backend ≥ 80 % de líneas y **sin decrecer** respecto del commit anterior (regla dura 5)
- [ ] 7.3 `ruff` y `mypy --strict` limpios sobre el código nuevo (regla dura 6)
- [ ] 7.4 Dejar registrado que `T-011` (`audit_logs`) **no entró**, con el motivo y qué lo destraba, para que el cierre del change no se lea como cobertura completa
