# ADR-016 — Trazas distribuidas con Grafana Tempo

- **Estado**: Aceptado
- **Fecha**: 2026-08-13
- **Decisores**: Tech Lead (con la competencia de dominio de SRE)
- **Resuelve**: `IN-15` · `PA-20` (mitad de trazas)
- **Afecta**: `C-03` (T-030), `docker-compose.yml`, `backend/app/core/observability.py`
- **Naturaleza**: **desvío de N1 por competencia de dominio.** Registrado como ADR según la regla 3 de [`ADR-000`](ADR-000-precedencia-documental.md) — sin este registro sería decisión implícita y, por el Principio 5 de la constitución, no vinculante.

---

## Contexto

`IN-15` (Jaeger contra Tempo) figuraba en `knowledge-base/10_preguntas_abiertas.md` como una de las dos **"referencias colgadas"**: se mencionaba en las Partes 3 y 4 pero nunca se documentaba como entrada de la Parte 2. Apareció al buscar evidencia para `IN-16`, porque ambos comparten decisor en `PA-20`.

### Qué dice cada fuente

| Documento | Nivel | Trazas distribuidas |
|---|---|---|
| `spec-tecnica` §65 y §1628 | **N1** | **Jaeger** — *"Jaeger recolecta trazas distribuidas con OpenTelemetry"* |
| `plan-implementacion` T-030 | N2 | **Jaeger** — servicio en `docker-compose`, UI accesible en `localhost:16686` |
| `plan-sre` §219, §222, §347 | **N3** | **Tempo** — *"Tempo se integra con Grafana"*; retención de 30 días; sampling adaptativo |
| `mejoras-y-saas` §200 | N4 | Jaeger |

**Tres documentos dicen Jaeger y uno dice Tempo.** Por conteo, gana Jaeger de forma abrumadora.

## Decisión

**Grafana Tempo**, con OpenTelemetry como SDK de instrumentación.

`ADR-000` no cuenta documentos: reparte autoridad. Y las **trazas distribuidas son dominio propio de `plan-sre`** — la regla de competencia por dominio establece que un N3 prevalece sobre N1 dentro de su dominio, y nunca sobre N0. La constitución no se pronuncia sobre trazas, así que no hay N0 en juego.

Este es el caso testigo de por qué la regla existe. Si la jerarquía fuera estricta, ganaría la spec técnica (N1) y el proyecto arrancaría con una decisión que el equipo que va a operar el sistema ya identificó como peor.

### El argumento sustantivo de SRE

No es formalismo: el plan de SRE tiene una razón concreta que la spec técnica no consideró.

El stack de observabilidad ya incluye **Grafana** (tableros), **Prometheus** (métricas) y **Loki** (logs). Tempo se integra nativamente con Grafana:

- **Con Tempo** → métricas, logs y trazas en **una sola interfaz**. Desde un pico en un tablero de Prometheus se salta al log en Loki y de ahí a la traza en Tempo, sin cambiar de herramienta ni de sesión.
- **Con Jaeger** → una interfaz separada solo para trazas. La correlación entre las tres señales queda a cargo de la persona que investiga, copiando identificadores entre pestañas.

A las tres de la mañana, durante un incidente, esa diferencia no es estética.

Además, `plan-sre` §347 especifica el comportamiento operativo completo —sampling adaptativo del 0,1 % en operaciones normales, 10 % en las lentas, 100 % en las fallidas, retención de 30 días— que ningún otro documento describe. La fuente que más sabe del tema es la que quedó en minoría numérica.

## Consecuencias

- **`T-030` está mal especificada** y hay que corregirla: hoy pide *"servicio `jaeger` en `docker-compose` accesible en `localhost:16686`"* y *"traza visible en Jaeger UI"*. Pasa a Tempo, y la verificación se hace desde Grafana, no desde una UI propia. Cae en **C-03**, no en C-01.
- **`spec-tecnica` §65 y §1628 quedan desactualizadas.** No se editan: son corpus fuente inmutable. Este ADR es el registro del desvío, y el Principio 5 establece que un ADR posterior reemplaza lo anterior.
- **La variable `OTEL_EXPORTER_OTLP_ENDPOINT`** de la tabla de `ADR-013` apunta a Tempo. El nombre no cambia: OpenTelemetry es agnóstico del backend, que es precisamente lo que hace esta decisión reversible.
- **Se reduce el inventario de herramientas** en uno: Grafana cubre las tres señales.

## Alternativas consideradas

**Jaeger**, siguiendo la spec técnica y la mayoría numérica. Es una herramienta madura y ampliamente adoptada, y tiene a favor la coherencia con tres de los cuatro documentos. Descartada porque fragmenta la observabilidad en dos interfaces sin dar nada a cambio en este stack, y porque la fuente que la contradice es la que tiene competencia sobre el tema.

**Diferir la decisión a C-03.** Descartada porque `T-030` no se puede escribir sin ella, y porque el propósito de resolver bloqueantes al inicio es que no reaparezcan como "bloqueantes olvidados" (regla dura 12 del proyecto).

## Nota sobre el precedente

Este es el **primer desvío de N1 por competencia de dominio** del proyecto. Sirve como referencia de cómo se aplica la regla:

1. Verificar que el tema cae dentro del dominio propio del documento N3 (acá: observabilidad y trazas, dominio de SRE).
2. Verificar que **no hay una regla N0 en juego** (acá: la constitución no habla de trazas).
3. Verificar que el N3 aporta un **argumento sustantivo**, no solo una preferencia (acá: integración con el Grafana que ya está en el stack).
4. **Registrarlo como ADR.** Sin este paso, la decisión no es vinculante.

Los cuatro pasos se cumplieron. Un desvío que no supere alguno de ellos no procede.
