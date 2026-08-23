# ADR-037 — La reserva no vence sola: la libera una persona

- **Estado**: ✅ **Aceptado**
- **Fecha**: 23 de agosto de 2026
- **Change**: `C-14` (`vehiculos-modelo-y-servicios`), gobernanza **ALTA**
- **Cierra**: la pregunta abierta que [`ADR-031`](ADR-031-dominio-opcional-y-los-seis-estados-del-vehiculo.md) dejó para Dirección al resolver `IN-11`
- **Depende de**: [`ADR-000`](ADR-000-precedencia-documental.md), [`ADR-031`](ADR-031-dominio-opcional-y-los-seis-estados-del-vehiculo.md)

> **Por qué se decide ahora**: la máquina de estados **ya está escrita** sin esta
> regla. Mientras la pregunta siga abierta, `TRANSICIONES_PERMITIDAS` es código
> que nadie ratificó. Cerrar C-14 con un bloqueante vivo adentro es exactamente
> lo que la regla dura 12 prohíbe.

---

## La pregunta que quedó abierta

`manual-usuario` §4.2.3 afirma que **"la reserva se libera automáticamente a los
7 días"**. `ADR-031` verificó que esa regla **no está en ningún otro documento**
del corpus —ni en `RN-ST`, ni en `spec-tecnica`, ni en el plan de
implementación— e implementó la máquina de estados sin ella, dejando la decisión
para Dirección en vez de resolverla por descarte.

## La decisión

**La regla no existe.** `reserved → available` es una transición **manual**, y
ya está en `TRANSICIONES_PERMITIDAS` (`RN-ST-05`). No se agrega ningún proceso
que libere reservas vencidas.

No se escribe código nuevo. Lo que cambia es que el código existente pasa de
*"escrito sin decidir"* a **ratificado**.

## Por qué

Tres razones, en orden de peso:

1. **`manual-usuario` es N4, no normativo.** Por [`ADR-000`](ADR-000-precedencia-documental.md)
   es insumo e intención comercial, no fuente de diseño. Es la única de las once
   fuentes que menciona los 7 días, y es la de menor autoridad de todas.
2. **No hay empate que desempatar.** No es que dos documentos digan cosas
   distintas: es que **diez documentos no dicen nada** y uno afirma algo. El
   silencio de `RN-ST` —que enumera las reglas de stock una por una— es
   significativo, no accidental.
3. **Un vencimiento silencioso es peor producto que uno manual.** Que el sistema
   suelte una reserva sin que nadie lo pida convierte una operación comercial en
   un efecto de calendario. El vendedor que reservó el auto se entera cuando el
   auto ya no está reservado. Contra Excel y el cuaderno, la ventaja no es
   automatizar más: es que el estado del auto sea el que alguien decidió.

## Lo que esto NO decide

No decide que una reserva **no pueda** tener vencimiento nunca. Decide que hoy
no lo tiene, y que si mañana lo tiene, entra por la puerta correcta: como regla
`RN-ST` nueva, con su columna de fecha, su proceso y sus tests — no como un
comportamiento que aparece porque alguien leyó el manual de usuario.

Si Dirección cambia de opinión, el costo es una migración (`reserved_at`) y una
tarea periódica. Ese costo es el mismo hoy que en seis meses: nada de lo que se
escribe ahora lo encarece.

## Consecuencias

- `TRANSICIONES_PERMITIDAS` queda **ratificada tal como está**. Cero cambios de
  código en la máquina de estados.
- `vehicles` **no** lleva columna `reserved_at`, y no se agrega tarea Celery de
  liberación.
- `IN-11` queda **cerrado por completo**: `ADR-031` resolvió cuántos estados hay,
  este resuelve la única regla que ese ADR no pudo cerrar.
- La afirmación de `manual-usuario` §4.2.3 queda registrada como **descartada**,
  no como pendiente. Si reaparece en una revisión del manual, este ADR es la
  respuesta.
