# C-03 · `observabilidad-y-auditoria-base`

> **Gobernanza ALTA.** Define el audit trail —evidencia de compliance— y los umbrales de alerta que gobiernan la operación. **Se propone y se espera revisión antes de escribir código.**

## Why

El sistema hoy es opaco en producción. `app/core/observability.py` existe desde `T-005` y hace **una** cosa: pone un identificador de correlación en un `ContextVar` y lo mete en cada línea de log. Su propio encabezado dice que las métricas y las trazas *"entran en C-03, sobre este mismo modulo"*.

Eso deja tres huecos que se sienten el día que algo falle:

1. **No hay métricas.** No se puede responder "¿está lento?" ni "¿para qué tenant?". Las 18 alertas del catálogo de `knowledge-base/13` no tienen sobre qué dispararse: ninguna serie de Prometheus existe.
2. **No hay trazas.** Un pedido que cruza HTTP → servicio → Redis Streams → worker de Celery se pierde en el salto. `ADR-016` eligió Tempo hace dos días y no hay nada exportando.
3. **Los logs no son máquina-legibles.** El formato es `%(asctime)s %(levelname)s [%(correlation_id)s] ...`, texto plano. Loki puede ingerirlo pero no puede filtrar por campo sin parsearlo con expresiones regulares frágiles.

Y hay un cuarto, que es el que justifica la gobernanza ALTA: **no existe `rls_violations_total`**, el centinela de seguridad que `knowledge-base/13` declara *"siempre 0"* y cuya alerta `RLSViolationDetected` es **P0 tratada como incidente de seguridad**. El control más crítico del sistema —el aislamiento multi-tenant— no tiene forma de avisar que se rompió.

## What Changes

Cuatro de las cinco tareas del change. **La quinta no entra**, y la razón está abajo.

| # | Tarea | Qué entra |
|---|---|---|
| 1 | `T-028` Logging estructurado | El formateador pasa a **JSON**, con `trace_id` como campo de primer nivel |
| 2 | `T-029` Métricas Prometheus | Middleware RED por endpoint y tenant, endpoint `/metrics`, y el centinela `rls_violations_total` |
| 3 | `T-030` Trazas | OpenTelemetry con exportador OTLP a **Tempo**, y propagación del contexto por Redis Streams |
| 4 | `T-031` Sentry | Inicialización con **scrubbing de PII** antes de enviar |
| — | `T-011` `audit_logs` | **NO ENTRA.** Ver abajo |

### Lo que NO entra, y por qué

**La migración de `audit_logs` queda afuera.** `ADR-029` resolvió la retención —24 meses uniformes— pero dejó el **particionado pendiente de una consulta legal**: si un asiento sobre facturación cuenta como respaldo contable ante AFIP (Resolución 4717/2020), la ventana de retención no es la que fija el ADR. `CHANGES.md` es terminante: *"hasta que haya respuesta no se escribe la migración de `audit_logs`"*.

Escribir la tabla ahora y reparticionarla después chocaría además con la regla dura 13: cambiar el esquema de particionado de una tabla con datos no se hace en un paso, y sería exactamente el tipo de migración destructiva que `ADR-025` prohíbe.

### Tres correcciones que el change arrastra, ya decididas

No son decisiones de este change: son decisiones tomadas que las tareas todavía no reflejan.

| Lo que dice la tarea | Lo vigente | Fuente |
|---|---|---|
| `T-030`: levantar `jaeger` en compose, UI en `:16686`, verificar ahí | **Tempo**, y se verifica desde Grafana | [`ADR-016`](../../../docs/adr/ADR-016-trazas-distribuidas-tempo.md) |
| Cuatro SLO de disponibilidad (API, frontend, webhooks, cola) | **Uno solo**. Los nueve servicios comparten el nodo: cuatro alertas dispararían juntas y darían cuatro páginas por un incidente | [`ESC-002`](../../../docs/escalaciones/ESC-002-slo-internos-sobre-nodo-unico.md) |
| `APILatencyHigh` con umbral único de 500 ms | **Se parte en dos.** Listado y búsqueda tienen objetivos que difieren 2,5×, y 500 ms era *más permisivo que el SLO que debía defender* | [`ADR-030`](../../../docs/adr/ADR-030-objetivo-de-ingenieria-y-slo-de-latencia.md) |

## Capabilities

Una sola delta spec, `platform/observability`, con cuatro grupos de escenarios:

- **Correlación** — un `trace_id` sobrevive al salto de proceso por Redis Streams; el mismo identificador aparece en el log, en la métrica de excepción y en la traza.
- **Métricas** — la etiqueta de tenant existe y **no filtra datos entre tenants**; la cardinalidad se mantiene bajo el techo de 1.000 series por métrica; `rls_violations_total` existe y arranca en 0.
- **Trazas** — el sampling respeta 0,1 % normal / 100 % en fallo; el endpoint OTLP ausente **no rompe la aplicación**, la deja sin exportar.
- **Errores** — Sentry no envía PII: ni cuerpo de la petición, ni cabeceras de autorización, ni email, ni DNI/CUIT.

## Impact

**Dependencias nuevas** — hoy el backend no tiene ninguna de estas:

```
opentelemetry-sdk · opentelemetry-instrumentation-fastapi
opentelemetry-instrumentation-sqlalchemy · opentelemetry-exporter-otlp
prometheus-client · sentry-sdk · python-json-logger
```

⚠️ Entran al mismo `pip-audit` bloqueante del pipeline. Si alguna arrastra una vulnerabilidad alta, el gate corta — y por [`ADR-027`](../../../docs/adr/ADR-027-escaneres-de-seguridad-declarados-vs-reales.md) el gate no se afloja.

**Variables de entorno**: ninguna nueva. `SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_TRACES_SAMPLER_ARG` y `LOG_LEVEL` ya están en `ObservabilitySettings` y en `ADR-013`, con `check-config-parity` en 0 divergencias. **Se usan, no se agregan.**

**Compose**: entran `prometheus`, `grafana`, `loki` y `tempo` como servicios de desarrollo. `check-services.sh` los tiene que conocer o va a reportar de menos.

**Costo**: `knowledge-base/13` fija un techo de **15 % del costo total de infraestructura** para observabilidad. Sobre un VPS único (`ADR-023`), cuatro servicios más compiten por la misma RAM que PostgreSQL, Redis, OpenSearch, Keycloak y MinIO. Está en `design.md` como riesgo abierto.

**Lo que este change NO toca**: `audit_logs`, los runbooks RB-001…RB-017, el synthetic monitoring externo y Alertmanager→PagerDuty. Los tres últimos necesitan el VPS, que está pausado.
