# ESC-002 — Tres SLO internos son inalcanzables por construcción, y su presupuesto de error congelaría el desarrollo

- **Estado**: ✅ **CERRADA** el 2026-08-17 — **opción A: los tres SLO se alinean al techo del nodo**
  > **Qué se decidió**: frontend web, webhooks entrantes y cola de eventos pasan a **99.7 %**, el mismo SLO que la API principal, porque comparten la máquina y su destino. Los cuatro SLO de disponibilidad quedan con **un único presupuesto de 130 min/mes**.
  >
  > **Por qué esta y no las otras dos**: mismo razonamiento que cerró `ESC-001`. Hoy no hay tráfico que justifique pagar redundancia todos los meses (opción B), y declararlos aspiracionales (opción C) dejaba la tabla diciendo 99.95 % donde el sistema da 99.7 % — la clase de número que después alguien cita en una propuesta comercial.
  >
  > **Lo que NO se perdió**: el compromiso de que la cola sea más confiable que el resto **se movió, no se retiró**. `lag p99 < 60 s` y `DLQ < 0,1 %` ya estaban en la tabla y miden su salud **sin depender de si el nodo estuvo prendido** — son mejores SLI para una cola que su disponibilidad, porque aíslan lo que la cola hace de lo que la máquina hace.
  >
  > **Consecuencia asumida**: el sistema deja de declarar que alguna de sus partes es más confiable que su máquina. Es una pérdida de aspiración, no de capacidad — el comportamiento real no cambió, cambió lo que se afirma sobre él. Y el presupuesto de error vuelve a significar algo: se agota cuando se cae el nodo, que es la única forma en que se cae.
- **Fecha**: 2026-08-17
- **Eleva**: Tech Lead
- **Decide**: **Dirección + SRE** — el decisor registrado para el dominio de disponibilidad (`PA-09`), el mismo de `ESC-001`
  > ⚠️ Hoy Dirección, SRE y Tech Lead son la misma persona. Igual que en `ESC-001`, eso no vacía la escalación: cambia el sombrero con el que se decide. Acá lo que está en juego no es qué infraestructura elegir, sino **qué ritmo de desarrollo se acepta imponerse por regla propia**.
- **Origen**: `ESC-001` cerró el SLA **público**. Los SLO **internos** quedaron anotados como *"sin auditar"* y nunca se miraron.
- **Afecta**: `C-03` (umbrales de Prometheus y catálogo de alertas), `knowledge-base/13`, la política de presupuesto de error

---

## El problema

`ESC-001` bajó el SLA público porque un nodo único no sostiene 99.9 %. **La tabla de SLO internos quedó intacta**, y tiene tres filas con el mismo defecto — más grave, porque estas no son promesas a un cliente: **gobiernan el ritmo de desarrollo del proyecto**.

Todos los servicios corren en **la misma máquina** (`ADR-023`: VPS único con Docker Compose; nueve servicios en un `docker-compose.yml`).

De ahí sale la regla que rompe la tabla:

> **Ningún componente puede estar más disponible que la máquina que lo hospeda.**

| SLI | SLO declarado | Presupuesto | ¿Alcanzable? |
|---|---|---|---|
| API principal | 99.7 % | **130 min/mes** | ✅ Es el techo de facto del nodo |
| Frontend web | 99.8 % | 86 min/mes | ❌ Mismo nodo que la API |
| Webhooks entrantes (Meta) | 99.9 % | 43 min/mes | ❌ Mismo nodo |
| **Cola de eventos** | **99.95 %** | **21,6 min/mes** | ❌ **Mismo nodo — 6× más estricto que la API** |

Redis corre en un contenedor de la misma máquina que el backend. Cuando el nodo se reinicia por una actualización de kernel, se caen **los dos**. La cola no puede acumular 21,6 minutos de caída al año cuando la máquina que la hospeda tiene presupuestados 130 **por mes**.

**No es un número optimista: es aritméticamente imposible.** Es el mismo error que `IN-31` —un SLA por encima del SLO interno— rotado noventa grados: acá son SLO de componentes por encima del SLO del nodo que los contiene.

## Por qué esto es peor que `ESC-001`

`ESC-001` era una promesa a clientes que todavía no existen. **Esta se aplica sola, todos los meses, desde el primer despliegue.**

La política de presupuesto de error dice:

| Presupuesto remanente | Modo |
|---|---|
| > 75 % | Normal — features a ritmo pleno |
| 25-75 % | Precaución |
| < 25 % | **Protección** — solo bugfixes; 30 % del tiempo a hardening |
| Agotado o negativo | **Freeze de releases no críticos** |

Con el SLO de la cola de eventos en 99.95 %, **su presupuesto se agota el primer mes y todos los siguientes**. Y si el proyecto aplica su propia política, entra en **freeze permanente** — un freeze que no responde a ningún problema real de calidad, sino a un número mal puesto en una tabla.

El resultado previsible es peor que el freeze: **la política se deja de mirar.** Un semáforo que está siempre en rojo deja de ser un semáforo, y el día que se ponga rojo por un problema de verdad, nadie va a frenar.

## Lo que NO está en discusión

- **El SLO de la API en 99.7 %** es coherente con el SLA de 99.5 % de `ESC-001` y con la infraestructura. Se conserva.
- **Los SLO que no son de disponibilidad** —lag de consumers, tasa de DLQ, cumplimiento de RPO— no dependen del nodo de la misma forma y no se tocan acá.
- **La latencia p95** es `IN-23` y se decide aparte: es un conflicto entre documentos, no una imposibilidad física.

## Opciones

### A — Alinear los tres SLO al techo del nodo *(recomendada)*

Frontend, webhooks y cola de eventos pasan a **99.7 %**, el mismo que la API, porque comparten la máquina y su destino.

- ✅ La tabla pasa a describir la realidad. El presupuesto de error vuelve a significar algo y la política puede aplicarse de verdad.
- ✅ Costo cero.
- ⚠️ Se pierde la señal de que la cola *debería* ser más confiable que la API. Se recupera con un SLI distinto —lag y DLQ, que ya están— que mide la salud de la cola sin depender del nodo.

### B — Dar redundancia a los componentes que lo justifiquen

Un segundo nodo para Redis y para el ingreso de webhooks.

- ✅ Los números quedan como están y pasan a ser alcanzables.
- ❌ Cuesta plata todos los meses, desde ya, por un volumen de tráfico que hoy es cero. Es exactamente el argumento por el que `ESC-001` eligió la opción A.
- ❌ Contradice `ADR-023` sin un motivo de negocio que lo sostenga.

### C — Declarar los tres SLO como objetivos aspiracionales, fuera del presupuesto de error

Se conservan los números y se los saca del cálculo que gobierna el modo de trabajo.

- ✅ Conserva la intención documentada.
- ❌ Un SLO que no consume presupuesto **no es un SLO** — es un comentario. Y deja la tabla diciendo 99.95 % donde el sistema da 99.7 %, que es la clase de número que después alguien cita en una propuesta comercial.

## Recomendación

**Opción A**, por el mismo razonamiento que cerró `ESC-001`: hoy no hay tráfico que justifique redundancia, y un número que no se puede cumplir no protege nada — solo desgasta el instrumento que debería avisar cuando hay un problema real.

El compromiso de que la cola sea más confiable que el resto **no se pierde, se mueve**: `lag p99 < 60 s` y `DLQ < 0,1 %` ya están en la tabla y miden la salud de la cola sin depender de si el nodo estuvo prendido.

---

## Ejecución del cierre

| Paso | Estado |
|---|---|
| 1. Elegir entre A, B y C | ✅ **A**, decidido el 17-ago-2026 |
| 2. Actualizar la tabla de SLO de `knowledge-base/13_observabilidad_y_sre.md` | ✅ los tres a **99.7 %**, con el valor anterior a la vista |
| 3. Registrarlo donde C-03 lo va a leer | ✅ `CHANGES.md`, ficha de C-03 |

**El presupuesto de error no cambia de número, cambia de alcance.** Seguía y sigue en **130 min/mes** (0,3 % de 43.200), pero antes era el presupuesto de *la API* y ahora es el de los **cuatro** SLO de disponibilidad, que comparten máquina. La tabla de modos —normal / precaución / protección / freeze— queda igual.

**Lo que hay que recordar al escribir las alertas en C-03**: hay **un solo** SLO de disponibilidad con cuatro nombres. Cuatro alertas de disponibilidad con umbrales distintos dispararían las cuatro juntas ante el mismo evento —el nodo caído— y producirían cuatro páginas para un incidente. Conviene **una** alerta de disponibilidad del nodo, y que las de la cola midan lo que la cola hace: `lag` y `DLQ`.

> **No bloqueaba nada y sigue sin bloquear.** C-03 todavía no empezó, y sus otros dos bloqueantes (`IN-13`, `IN-23`) siguen abiertos.
