# E-002 — Propuesta de enmienda a la constitución

## Adecuar el Artículo 8 al tamaño real del equipo, sin bajar sus garantías

- **Estado**: 🟡 **EN DISCUSIÓN** — paso (b) del Artículo 8
- **Apertura**: lunes 17 de agosto de 2026
- **Cierre mínimo de discusión**: **lunes 24 de agosto de 2026** (5 días hábiles)
- **Proponente**: Tech Lead
- **Decide**: Tech Lead como **decisor único declarado** (ver la Nota sobre la circularidad)
- **Bloquea**: nada. Ninguna tarea del roadmap espera esta enmienda
- **Origen**: [`E-001`](E-001-enmienda-glosario-super-admin.md), que registró el problema y lo dejó fuera de su alcance a propósito

---

## Por qué existe

`E-001` chocó con esto al tramitarse, lo resolvió para su propio caso, y dejó dicho que excedía su alcance:

> *"El Artículo 8 asume un equipo técnico y de producto que pueda formar mayoría. **Ese cuerpo no existe hoy**, y no va a existir para la próxima enmienda tampoco. […] cada enmienda futura va a chocar con lo mismo, y va a resolverse igual de a una, **o alguien va a terminar escribiendo "mayoría calificada" sin pensarlo**."*

Esa última frase es el motivo real de esta propuesta. El riesgo no es que el trámite se trabe — `E-001` demostró que no se traba: se registra como decisión unipersonal y sigue. **El riesgo es que se cumpla de mentira.** Una enmienda aprobada por una persona y firmada como *"mayoría calificada del equipo técnico y de producto"* es una decisión implícita disfrazada de procedimiento, y el **Principio 5** es terminante con eso.

Un procedimiento que obliga a mentir para cumplirse se deja de cumplir. Primero en la firma, después en el resto.

## Qué se propone modificar

**Artículo 8, inciso (c).** Únicamente ese inciso. Los incisos (a), (b), (d) y (e) **no se tocan**, y el párrafo de cierre sobre acumulación de enmiendas tampoco.

### Texto vigente

> (c) aprobación por **mayoría calificada del equipo técnico y producto**, con consulta a dirección si la enmienda afecta principios fundamentales;

### Texto propuesto

> (c) aprobación por **mayoría calificada del equipo técnico y de producto**, con consulta a dirección si la enmienda afecta principios fundamentales. **Cuando el equipo técnico y de producto esté compuesto por una sola persona, la aprobación se registra como decisión unipersonal, identificando por nombre y rol a quien decide; nunca como mayoría. La consulta a dirección se mantiene en los mismos términos.** El registro del inciso (d) MUST indicar cuál de las dos formas se aplicó y cuántas personas integraban el cuerpo decisor en ese momento;

## Qué NO se propone

Tres cosas que están adentro del mismo artículo y que deliberadamente quedan afuera:

| | Por qué no |
|---|---|
| **Acortar los cinco días hábiles** | Es el período de enfriamiento, y es la garantía que **no** depende del tamaño del equipo. Con un solo decisor es *más* importante, no menos: es lo único que separa una enmienda de un cambio de opinión. `E-001` ya rechazó acortarlo por este motivo |
| **Eliminar la consulta a dirección** | Es un control externo al equipo técnico. Que el equipo sea de una persona no lo vuelve innecesario — lo vuelve el único control que queda |
| **Bajar el umbral cuando el equipo sea de dos o tres** | La enmienda cubre el caso de **una** persona, que es el que se dio. Un umbral inventado para tamaños que el proyecto no tiene sería exactamente el tipo de regla especulativa que después nadie sabe de dónde salió |

## Nota sobre la circularidad, que hay que decir en voz alta

**Esta enmienda se aprueba con el procedimiento que ella misma quiere corregir.** No hay forma de evitarlo, y disimularlo sería peor que nombrarlo.

Se tramita así: el paso (c) se registra como **decisión unipersonal del Tech Lead**, con esas palabras, exactamente como `E-001` resolvió su propio caso. Es decir, **la práctica que la enmienda quiere volver explícita ya es la que se está usando** — la enmienda no la inventa, la escribe.

Si alguien objeta que un decisor único no puede enmendar el artículo que define quién decide, la objeción vale igual para `E-001` y para cualquier decisión del proyecto. El proyecto lo lleva una persona; eso no es un defecto del procedimiento, es el hecho al que el procedimiento tiene que ajustarse.

## Impacto si se ratifica

- El Artículo 8 pasa a describir cómo se decide de verdad en este proyecto.
- Toda enmienda futura tiene una forma de registrar su aprobación **sin mentir**.
- El registro del inciso (d) gana un dato que hoy no pide: **cuántas personas integraban el cuerpo decisor**. Es lo que va a permitir, dentro de dos años, leer una enmienda vieja y saber si "unipersonal" era la situación normal o una excepción.
- La constitución pasa a **versión 1.2**. ✅ **Confirmado**: `E-001` se ratificó el 20-ago-2026 y la llevó efectivamente a **1.1**, así que la hipótesis de este inciso ya no es hipótesis. La rama en que `E-001` se rechazaba —y esta quedaba como 1.1— no ocurrió.
- Se acumula como apéndice al final de `docs/sdd/deRuedas-constitucion.md`, en modo *append-only*, con el mismo criterio que `E-001` fijó (opción A).

## Impacto si se rechaza

Ninguno inmediato: **ninguna tarea del roadmap espera esta enmienda.** Lo que queda es el problema original — cada enmienda futura vuelve a chocar con el supuesto incumplido y se resuelve a mano, con el riesgo de que alguna termine firmada como "mayoría calificada" sin que nadie lo piense.

## Alternativas al texto propuesto

Se someten a discusión junto con la propuesta:

1. **Reemplazar *"mayoría calificada"* por *"aprobación del cuerpo decisor vigente"***, definiendo ese cuerpo en el glosario. Más limpio y no necesita un caso especial. **Contra**: mueve la definición fuera del artículo, y hay que enmendar el glosario también — dos cambios donde alcanza uno. Se propone **no** adoptarla, pero es la alternativa más seria.
2. **No enmendar y dejar la resolución de `E-001` como precedente.** **Contra**: por el Principio 5 un precedente no registrado como norma no es vinculante, y el próximo que tramite una enmienda no tiene por qué encontrarlo.
3. **Enmendar además el inciso (b) para que el plazo se cuente desde la publicación y no desde la redacción.** **Contra**: es un problema distinto y no se dio todavía. Mezclarlo obligaría a discutir dos cosas y aprobar una sola.

---

## Registro de la discusión

> Completar durante el período de discusión. Las intervenciones se acumulan acá para dejar rastro, como exige el Artículo 8 para la constitución misma.

| Fecha | Participante | Postura | Comentario |
|---|---|---|---|
| 2026-08-17 | Tech Lead | Propone | Apertura. El problema lo registró `E-001` y lo dejó fuera de su alcance; se abre hoy y no el 20-ago porque el plazo de cinco días hábiles corre desde la apertura, y demorarla solo corre el cierre. |

---

## Procedimiento — Artículo 8

| Paso | Estado |
|---|---|
| (a) Propuesta escrita identificando el artículo a modificar y la justificación | ✅ **Este documento** |
| (b) Discusión abierta, mínimo 5 días hábiles | 🟡 Abierta hasta el **24-ago-2026** |
| (c) Aprobación — **decisión unipersonal del Tech Lead** | ⬜ Pendiente |
| (d) Registro de la enmienda con fecha, motivo y versión | ⬜ Pendiente |
| (e) Comunicación al equipo y a los stakeholders externos relevantes | ⬜ Pendiente |

> **¿Requiere consulta a Dirección?** El Artículo 8 la exige *"si la enmienda afecta principios fundamentales"*. Esta enmienda **modifica el procedimiento de enmienda**, que no es un principio de las Partes I o II — pero es el mecanismo que los protege. **Se propone que sí requiere consulta a Dirección**, por prudencia y porque el costo de consultar es nulo cuando Dirección y Tech Lead son la misma persona. Este punto se somete a la discusión junto con el resto.
>
> Se propone el criterio inverso al de `E-001`, y a propósito: aquella agregaba una definición al glosario sin tocar nada; esta toca la regla que gobierna a todas las demás.

> ⚠️ **NADA DE LOS PASOS (c), (d) Y (e) ESTÁ EJECUTADO**, y no pueden ejecutarse antes del **24-ago-2026** sin violar el plazo del Artículo 8. Redactarlos por anticipado —como hizo `E-001`— es legítimo; ejecutarlos, no.
