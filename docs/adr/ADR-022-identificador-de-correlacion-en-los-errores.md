# ADR-022 — Los errores llevan `correlation_id`, no `trace_id`

- **Estado**: 🟢 **Aceptado** — 16-ago-2026
- **Decisores**: Tech Lead
- **Afecta**: `backend/app/core/errors.py`, `core/observability.py`, y el contrato público de toda respuesta de error de la API
- **Naturaleza**: **desvío consciente de una convención de N1.** Se registra por la **regla 3 de precedencia documental** ([`ADR-000`](ADR-000-precedencia-documental.md)): todo desvío de N1 se registra como ADR, y sin ADR es decisión implícita que —por el Principio 5— **no es vinculante**.

---

## Contexto

Las convenciones de API de la base de conocimiento nombran `trace_id` como extensión del Problem Details en las respuestas de error.

`core/errors.py`, que C-01 dejó andando, emite `correlation_id`. Ese valor lo alimenta la cabecera `X-Request-ID` a través de `core/observability.py`: se genera uno si el cliente no lo trae, se reutiliza el suyo si lo trae, y viaja a cada línea de log de esa petición.

C-02 completa el formato de error y toca justo ese código. El momento de alinearse con la convención escrita, o de no hacerlo, es este.

## Decisión

**Se mantiene `correlation_id` y no se renombra a `trace_id`.**

Dos motivos, y el segundo pesa más que el primero:

1. **Es lo que hoy correlaciona respuesta y log.** Renombrarlo obligaría a tocar el middleware, el formateador de logs y todo test que lo mire, a cambio de nada observable.

2. **`trace_id` es otra cosa, y llega en C-03.** Ese change introduce trazas distribuidas con OpenTelemetry, donde `trace_id` es el identificador de **la traza** —un árbol de spans que puede atravesar varios servicios—, no el de la petición. Renombrar ahora obligaría a renombrar de nuevo en C-03, o peor: a que dos conceptos distintos compartan nombre y nadie sepa cuál está mirando.

Son identificadores con **ciclos de vida distintos**. Una petición tiene exactamente un `correlation_id`. Una traza puede abarcar la petición, el evento de dominio que dispara y el trabajo del worker que lo consume — tres cosas con `correlation_id` distinto o sin ninguno.

## Consecuencias

- El cuerpo de error de la API expone `correlation_id`. Quien consuma la API y siga la convención escrita de la KB no va a encontrar `trace_id`.
- **C-03 decide si el cuerpo lleva los dos.** Es la decisión correcta para ese change: recién ahí `trace_id` existe y tiene un valor que poner. Este ADR no la prejuzga.
- Si C-03 agrega `trace_id`, será **por adición**: `correlation_id` no se va, porque sigue siendo lo único que identifica la petición.

## Alternativas consideradas

**Renombrar a `trace_id` ahora.** Cumple la convención escrita al pie de la letra y rompe el significado: llamaría "traza" a algo que no lo es, justo antes de que aparezca la traza de verdad.

**Emitir los dos desde ya**, con `trace_id` vacío hasta C-03. Descartada: un campo que siempre viene vacío enseña a ignorarlo, y para cuando tenga valor nadie lo va a estar mirando.
