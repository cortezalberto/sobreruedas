# Observabilidad y SRE

> Fuente primaria: `deRuedas-plan-sre.md` (1.223 líneas). Complementado con `deRuedas-spec-tecnica.md` §9 y `deRuedas-plan-seguridad.md` §8.

## SLAs públicos por plan

🔴 **Contradicción bloqueante con la spec técnica** — ver `IN-31`.

| Plan | Disponibilidad | Downtime aceptable/mes | Crédito |
|---|---|---|---|
| Starter | **99.0 %** | 7 h 12 min | 5 % de la suscripción |
| Pro | **99.5 %** | 3 h 36 min | 10 % de la suscripción |
| Enterprise | **99.9 %** | 43 min | 25 % de la suscripción |

La `spec-tecnica.md` §6.2 y §9.7 dicen en cambio **99.9 % para Starter y Pro, 99.95 % para Enterprise** — cifras que además son **superiores al SLO interno** de 99.7 %, lo cual es matemáticamente insostenible.

## SLOs internos

Todos declarados "más estrictos que el SLA".

| SLI | SLO | Ventana |
|---|---|---|
| Disponibilidad de la API principal | **99.7 %** | 30 días rolling |
| Latencia p95, endpoints típicos | **< 300 ms** ⚠️ `IN-23` | 30 días rolling |
| Latencia p95, búsqueda compleja | **< 2,0 s** ⚠️ `IN-23` | 30 días rolling |
| Disponibilidad de webhooks entrantes (Meta) | 99.9 % | 30 días rolling |
| Latencia de procesamiento de mensajes WhatsApp | p95 < 30 s (recepción → persistencia) | 7 días rolling |
| Disponibilidad del frontend web | 99.8 % | 30 días rolling |
| Cumplimiento de RPO de PostgreSQL | 100 % de backups exitosos | 30 días |
| Disponibilidad de la cola de eventos | 99.95 % | 30 días rolling |
| Lag máximo de consumers | p99 < 60 s | 7 días rolling |
| Tasa de eventos en DLQ | < 0,1 % del volumen total | 7 días rolling |

⚠️ La constitución y la spec exigen **p95 < 200 ms** en listados y **< 500 ms** en búsqueda. El SLO de SRE es más laxo en ambos casos (y **4× más laxo en búsqueda**). Ver `IN-23`.

## Presupuesto de error

SLO 99.7 % → presupuesto **0,3 % mensual ≈ 130 minutos/mes**.

| Presupuesto remanente | Modo |
|---|---|
| > 75 % | **Normal** — desarrollo de features a ritmo pleno |
| 25-75 % | **Precaución** |
| < 25 % | **Protección** — solo bugfixes; 30 % del tiempo del equipo a hardening |
| Agotado o negativo | **Freeze** de releases no críticos |

## Service tiers

| Tier | Componentes | Severidad de alerta |
|---|---|---|
| **Tier 1** | API, PostgreSQL, auth, webhooks de WhatsApp | P0 |
| **Tier 2** | Workers, OpenSearch, integraciones salientes, frontend | P1 |
| **Tier 3** | CI/CD, observabilidad, herramientas internas | P2-P3 |

## Stack de observabilidad

| Capacidad | Herramienta (`plan-sre`) | Herramienta (`spec-tecnica`) |
|---|---|---|
| Métricas | Prometheus + Grafana | ✅ igual |
| Logs | Loki | ✅ igual |
| **Trazas** | **Tempo + OpenTelemetry** | **Jaeger + OpenTelemetry** ⚠️ `IN-15` |
| Errores | Sentry (managed) | ✅ igual |
| Synthetic monitoring | Servicio externo (UptimeRobot, Pingdom o equivalente) | — |
| Dashboards | Grafana (versionados como código, JSON) | ✅ igual |
| Alerting | Alertmanager → PagerDuty o equivalente | ✅ igual |

Los tres pilares (métricas, logs, trazas) se correlacionan por **`trace_id`**.

**Configuración**:
- Scrape de Prometheus: cada **15 segundos**.
- Cardinalidad máxima: **1.000 series temporales únicas** por métrica.
- Sampling de trazas: **0,1 %** normal · **10 %** en operaciones lentas (sobre threshold) · **100 %** en operaciones fallidas. En dev y staging, 100 %.
- Retención: trazas **30 días** (Tempo) · logs de aplicación **90 días** · `audit_logs` **24 meses**.
- **Restricción de costo**: la observabilidad no debe superar el **15 % del costo total de infraestructura**.

**Métricas obligatorias**:
- **RED** por endpoint: Rate, Errors (% de 5xx), Duration (p50/p95/p99).
- **USE** por recurso: Utilization, Saturation, Errors — sobre CPU, memoria, disco, red y conexiones de base.
- **De negocio**: vehículos y leads creados por hora, mensajes enviados, tasa de error de WhatsApp, latencia de las financieras.
- **De calidad de datos**: filas con `tenant_id` NULL (**debe ser cero**), conversaciones huérfanas, leads sin actividad > 30 días.
- **Centinela de seguridad**: `rls_violations_total` — siempre 0.

## Alertas

### Severidades operativas (O0-O3)

Taxonomía **paralela y deliberadamente distinta** de la de seguridad (P0-P4). El propio documento lo explicita.

| Sev. | Etiqueta | Criterio |
|---|---|---|
| **O0** | Operativo crítico | Servicio caído > 5 min, o afecta a > 50 % de los tenants, o el SLO mensual está en riesgo de quemar todo el presupuesto |
| **O1** | Operativo mayor | Funcionalidad central degradada para un subset significativo |
| **O2** | Operativo significativo | Tenants específicos; Tier 2 caído |
| **O3** | Operativo menor | Degradación limitada; Tier 3 caído |

### Severidades de paging

| Sev. | Etiqueta | Respuesta |
|---|---|---|
| P0 | Pagar ahora | Page 24/7, < 15 min |
| P1 | Pagar dentro de 1 h | Page diurno / ticket nocturno, < 1 h diurna |
| P2 | Atender hoy | Slack + ticket, dentro del día hábil |
| P3 | Backlog priorizado | Email / ticket, sin SLA |

### Burn rate alerting

- **Fast burn** (consume el presupuesto de 30 días en 1 hora): multiplicador **14.4**, `for: 5m`, severidad **P0**.
- **Slow burn** (en 6 horas): multiplicador **6**, `for: 15m`, severidad **P1**.

### Catálogo de alertas

| Alerta | Sev. | Condición | Runbook |
|---|:---:|---|---|
| `APIDown` | P0 | — | RB-001 |
| `APIBurnRateFast` | P0 | fast burn | RB-002 |
| `APILatencyHigh` | P1 | p95 > 500 ms durante 15 min | RB-003 |
| **`RLSViolationDetected`** | **P0** | cualquier incremento | **RB-004** (escalada inmediata, tratada como incidente de seguridad) |
| `PostgreSQLPrimaryDown` | P0 | — | RB-005 |
| `PostgreSQLReplicationLag` | P1 | lag > 30 s durante 5 min | RB-006 |
| `PostgreSQLBackupFailed` | P1 | — | RB-007 |
| `RedisDown` | P0 | — | RB-008 |
| `RedisHighMemory` | P1 | > 85 % | RB-009 |
| `WorkerQueueLagHigh` | P1 | lag > 2 min | RB-010 |
| `DLQGrowing` | P1 | > 100 eventos/hora | RB-011 |
| `WhatsAppCircuitBreakerOpen` | P2 | abierto > 10 min | RB-012 |
| `WhatsAppErrorRateHigh` | P2 | > 5 % durante 15 min | RB-013 |
| `PortalSyncFailing` | P2 | — | RB-014 |
| `TLSCertificateExpiringSoon` | P3 | < 30 días | RB-015 |
| `DiskUsageHigh` | P2 | > 85 % | RB-016 |
| `AnomalousAuthFailures` | P1 | spike 10× | RB-017 |
| `SyntheticCheckFailed` | P0 | — | RB-001 |

Alertas específicas del plan de implementación: tasa de éxito de publicación < 95 % en 30 min (warning) · DLQ de publishing > 10 (critical) · error rate de envío de WhatsApp > 5 % en 30 min · p95 del webhook > 1 s.

**Higiene de alertas**: silences de máximo **4 horas** en ventana normal, **24 horas** en mantenimiento programado. **Los silences sin expiración están prohibidos.** Auditoría mensual de ruido con objetivo de **> 80 % de las alertas P0/P1 con acción real asociada**.

## Runbooks

Plantilla canónica: *Síntomas · Diagnóstico en 5 minutos · Mitigación · Comunicación · Resolución · Validación · Escalación · Postmortem · Historial.*

**Desarrollados en detalle (5)**: RB-001 (APIDown, P0) · **RB-004 (RLSViolationDetected, P0)** · RB-005 (PostgreSQLPrimaryDown, P0) · RB-010 (WorkerQueueLagHigh, P1) · RB-012 (WhatsAppCircuitBreakerOpen, P2).
El catálogo referencia hasta RB-017, pero **los 12 restantes son solo entradas de tabla sin desarrollar**.

Los runbooks se mantienen vivos: se actualizan cada vez que se aprende algo de un incidente real.

## On-call

- **Rotación semanal**, con cambio a las 10:00 h.
- El secundario recibe la alerta si el primario no responde en **10 minutos**.
- Mínimo de personas en rotación: **4** para que sea viable; 3 es agotador; **menos de 3 de forma prolongada está prohibido**.
- Respuesta P0: **< 15 minutos**.
- **Día libre compensatorio** si hubo intervención nocturna o de fin de semana de más de 2 horas continuas.
- **Onboarding a on-call**: 2 semanas de observación → 2 semanas de shadowing → 4 semanas con backup reforzado → 8 semanas en modo estándar.
- Escalación automática si un incidente supera **4 horas continuas**.
- **War room** si un P0 supera **30 minutos**; los roles del war room rotan cada 4 horas.

## Backup y recuperación ante desastres

### RTO / RPO por componente

| Componente | RTO | RPO |
|---|---|---|
| API backend | 15 min | 0 |
| Frontend Next.js | 5 min | 0 |
| **PostgreSQL primary** | **1 hora** | **5 min** |
| PostgreSQL replicas | 30 min | 5 min |
| Redis | 10 min | 1 min (AOF) |
| OpenSearch | 4 horas | Reconstruible |
| Object storage | 1 hora | 0 |
| Workers Celery | 15 min | 0 |
| Eventos Redis Streams | 1 hora | 5 min |
| `audit_logs` | 4 horas | 0 |
| Pipeline CI/CD | 8 horas | — |
| **Sistema completo (DR en región alternativa)** | **4 horas** | **1 hora** |

Esta tabla es **idéntica** en el plan de SRE y en el plan de seguridad ✅. ⚠️ Pero la spec técnica declara *"RTO de una hora ante caída total"* — ver `IN-34`.

### Estrategia de backup

- PostgreSQL: **full diario** en la región primaria + **full semanal cross-region** + **WAL archive continuo** → **PITR de 30 días con granularidad de segundos**.
- Snapshots mensuales preservados **12 meses**, con **object lock** (inmutables).
- ⚠️ La spec agrega *"archivado anual por 7 años para cumplimiento contable"*, ausente en el plan de SRE. Ver `IN-35`.

### Pruebas de recuperación

| Prueba | Cadencia |
|---|---|
| Restore de PostgreSQL aislado | **Mensual** |
| PITR a un punto arbitrario | Trimestral |
| Failover automático primary → réplica | Semestral |
| **DR completo** (región alternativa, operar 1 hora desde ahí) | **Anual** |
| Tabletop exercise | Semestral |
| Verificación de inmutabilidad de backups | Trimestral |

Failover de PostgreSQL orquestado con **Patroni** o equivalente.

## Capacidad y escalado

### Perfiles de carga por tamaño de tenant

| Métrica | Chico | Medio | Grande |
|---|---|---|---|
| Vendedores activos | 1-2 | 3-5 | 6-15 |
| Vehículos en stock | 20-50 | 50-150 | 150-500 |
| Leads abiertos simultáneos | 10-30 | 30-100 | 100-300 |
| Mensajes WhatsApp/día | 20-50 | 100-300 | 500-1.500 |
| Requests API/día | 1k-5k | 5k-20k | 20k-100k |

### Headroom obligatorio

| Recurso | Umbral |
|---|---|
| API backend, utilización p95 | ≤ **60 %** |
| Pool de conexiones de PostgreSQL | ≤ 60 % |
| CPU de PostgreSQL | ≤ 50 % promedio |
| Disco de PostgreSQL | ≥ 30 % libre |
| Memoria de Redis | ≤ 70 % |
| Workers | capacidad para **3×** el throughput actual |
| Storage | ≥ 30 % libre; planificar scaling al 80 % con 30 días de anticipación |

### Autoscaling

- **API backend**: HPA por CPU + RPS custom. **min 2, max 10** réplicas.
- **Workers async**: HPA por lag de cola. Mínimo 1 por consumer group.
- **PostgreSQL y Redis**: scaling manual planificado.

## Deploy y rollback

**Estrategias** (plan de SRE):
- **Rolling** — por defecto ⚠️ la spec declara blue-green como estándar (`IN-27`).
- **Blue-green** — para cambios de mayor riesgo.
- **Canary** — progresión 1 % → 5 % → 25 % → 50 % → 100 % ⚠️ la spec dice canary al 5 % con escalado gradual.
- **Feature flag** — para activación progresiva por tenant.

**Migraciones**: forward-compatible obligatorio. Las destructivas se hacen en dos pasos separados por al menos un release. Nunca se ejecutan automáticamente en producción sin aprobación humana.

**Ventanas de mantenimiento**: domingos **06:00-09:00** hora AR, con aviso de **72 horas** de anticipación mínima. ⚠️ La spec dice *"máximo 2 horas por mes, en horario nocturno, con aviso de 48 horas"* — `IN-33`.

### Métricas de cambio (DORA-like)

| Métrica | Objetivo |
|---|---|
| Frecuencia de deploy | ≥ 1/semana |
| Lead time | < 24 h |
| Tasa de rollback | < 5 % |
| **Tiempo medio de rollback** | **< 30 min** ⚠️ la constitución exige < 15 min y la spec dice < 1 min — `IN-28` |

## Ambientes

⚠️ El plan de SRE **no tiene una sección dedicada a ambientes**; solo menciona *staging* (para DAST y chaos testing) y *producción*. La lista completa viene de la spec técnica §7.4:

- **Local** — cada desarrollador con el entorno completo en Docker Compose (levanta en < 3 min).
- **CI** — ambientes efímeros por pipeline, descartados al finalizar.
- **Staging** — persistente, con datos sintéticos, espejo de producción. Se usa para E2E, validación de releases y demos.
- **Producción** — solo accesible vía pipeline de despliegue.

## Toil y automatización

- **Umbral de alarma de toil**: 25 % del tiempo del equipo.
- **Inversión mínima en automatización**: 20 % del tiempo del equipo.
- **Alarma de costo**: se dispara si el costo proyectado excede el presupuesto en más del 10 %.
- Configuración aplicada durante un incidente: debe reconciliarse en **48 horas**.

## Comunicación de incidentes

| Sev. | Canal y plazo |
|---|---|
| **O0** multi-tenant | Status page en **15 min** · actualizaciones cada **30 min** · email a la hora si persiste |
| **O1** | Email en **2 horas** |
| **O2 / O3** | Post-resolución; reporte mensual |

**Postmortem**: obligatorio para O0 y O1 dentro de **5 días hábiles** (mismo plazo que los P0-P2 de seguridad).

## Roadmap de madurez SRE

- **Ola 2**: chaos testing mensual.
- **Ola 3**: SLO de API elevado a **99.9 %** para Pro y Enterprise · **multi-región activo** con RTO < 30 min.
