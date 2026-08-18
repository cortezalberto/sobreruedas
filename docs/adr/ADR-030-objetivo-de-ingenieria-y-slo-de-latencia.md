# ADR-030 — Latencia: el objetivo de ingeniería y el umbral de página no son el mismo número

- **Estado**: ✅ **Aceptado**
- **Fecha**: 18 de agosto de 2026
- **Change**: `C-03` (`observabilidad-y-auditoria-base`), gobernanza **ALTA**
- **Cierra**: `IN-23`
- **Depende de**: [`ADR-000`](ADR-000-precedencia-documental.md) — regla 2, *N0 nunca pierde*

> **Quién decidió esto.** Se le ofreció a Dirección elegir entre esta salida y
> abrir una enmienda del Artículo 8, y no marcó preferencia. La decisión es
> técnica y la toma `C-03` bajo su gobernanza; queda registrada acá para que sea
> vinculante por el Principio 5. **Si Dirección prefiere la otra salida, este ADR
> se supersede y se abre la enmienda.**

---

## El conflicto

| Fuente | Nivel | Listado | Búsqueda |
|---|---|---|---|
| `constitucion` Art. 4 + `spec-tecnica` | **N0** | p95 < **200 ms** | p95 < **500 ms** |
| `plan-sre` + `plan-testing` | N3 | p95 < **300 ms** | p95 < **2,0 s** |

El plan de SRE es **4× más permisivo que la norma vinculante** en búsqueda.

### Y hay un tercer número que `IN-23` no cuenta

`knowledge-base/13` §Catálogo de alertas:

> `APILatencyHigh` · P1 · **p95 > 500 ms durante 15 min**

Es **más permisiva que el propio SLO de SRE** (300 ms). O sea: hoy el SLO de
300 ms **no tiene ninguna alerta que lo defienda**, y el número que dispara la
página coincide por casualidad con el objetivo de búsqueda de N0. Tres cifras
para dos conceptos, y ninguna alineada con otra.

---

## Lo que la precedencia permite y lo que no

Por [`ADR-000`](ADR-000-precedencia-documental.md), N3 prevalece sobre N1 dentro
de su dominio. **Pero la regla 2 dice que N0 nunca pierde**, y 200/500 salen de
la constitución. `plan-sre` **no puede** relajarlos por competencia de dominio:
cambiar esos números exige enmienda del Artículo 8.

Así que la pregunta correcta no es *"¿cuál de los dos gana?"* sino *"¿están
midiendo lo mismo?"*.

---

## Decisión

**No miden lo mismo, y se nombran distinto.**

| Concepto | Listado | Búsqueda | Quién lo fija | Dónde se verifica |
|---|---|---|---|---|
| **Objetivo de ingeniería** | 200 ms | 500 ms | **N0** | k6 con tráfico nominal · DoD de las historias |
| **SLO con presupuesto de error** | 300 ms | 2,0 s | N3 | 30 días rolling |
| **Umbral de página** | 300 ms | 2,0 s | este ADR | Prometheus, sostenido 15 min |

La constitución ya escribe esa distinción, aunque nunca la nombró: el Artículo 4
dice *"en condiciones normales de carga"* para el listado. Un objetivo bajo carga
normal y un SLO sobre 30 días rolling —que incluye picos, degradaciones y
mantenimiento— son magnitudes distintas y pueden convivir.

⚠️ **Para búsqueda, N0 NO trae ese calificador**: los 500 ms son incondicionales.
Por eso los 2,0 s de SRE valen **solo** como umbral de página, y **nunca** como
"lo aceptable". Que no despierte a nadie no significa que esté bien.

### Las dos correcciones que esto obliga

1. **`APILatencyHigh` se parte en dos.** Un solo umbral para listado y búsqueda
   no puede servir cuando sus objetivos difieren 2,5×. Van dos alertas, cada una
   contra su propio SLO: listado a 300 ms y búsqueda a 2,0 s, ambas sostenidas
   15 min. Hoy la única alerta existente está en 500 ms, que para listado llega
   tarde y para búsqueda nunca dispara.

2. **Falta una señal que mida el cumplimiento de N0 y NO pagine.** Sin ella, el
   sistema puede vivir permanentemente por encima del objetivo constitucional sin
   que nada lo registre — que es el patrón *"un documento afirma un control que
   no ocurre"* que este proyecto viene encontrando. Va como panel y reporte
   periódico, no como alerta: despertar a alguien por incumplir un objetivo de
   diseño es cómo se entrena a un equipo a ignorar las páginas.

---

## Consecuencias

- Los umbrales de Prometheus de `C-03` salen de la fila **umbral de página**.
- Los thresholds de k6/Locust y la Definición de Terminado de las historias salen
  de la fila **objetivo de ingeniería** — son 200/500, no 300/2000.
- `knowledge-base/13` §36-37 y §46 quedan desactualizadas en su planteo (lo
  registran como contradicción abierta) y se corrigen apuntando acá.
- **Si la brecha entre objetivo y SLO se vuelve permanente**, eso es señal de que
  uno de los dos está mal calibrado, y la salida es la enmienda del Artículo 8 —
  no seguir declarando un objetivo que nadie persigue.
