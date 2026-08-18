# ADR-029 — Retención de `audit_logs`: 24 meses uniformes, y la ventana de la UI varía por plan

- **Estado**: ✅ **Aceptado** — decidido por Dirección el 18 de agosto de 2026
- **Change**: `C-03` (`observabilidad-y-auditoria-base`), gobernanza **ALTA**; el dominio de auditoría es **CRÍTICO**
- **Cierra**: `IN-13`
- **Depende de**: [`ADR-000`](ADR-000-precedencia-documental.md) — competencia por dominio

> ⚠️ **Este ADR fija la RETENCIÓN. No habilita el particionado.** Ver la pregunta
> legal abierta al final: Dirección decidió que va a asesoramiento **antes** de
> fijar el particionado de la tabla.

---

## El conflicto

`IN-13` registra tres respuestas incompatibles en documentos vinculantes:

| Fuente | Nivel | Retención |
|---|---|---|
| `spec-tecnica` §3.9, §6.5, §8.8 | N1 | **5 años**, "por obligaciones contables" — repetido tres veces |
| `plan-seguridad` §6.4 · `plan-sre` §4 | N3 | **24 meses** |
| `plan-gtm` | N4 (no normativo) | **Escalonada**: Starter 30 días · Pro 12 meses · Enterprise 24 meses |

El impacto es triple: define el particionado y el storage a proyectar; es una
afirmación de **compliance legal** que el propio documento de compliance
contradice; y el GTM convierte la auditoría en feature comercial.

---

## Decisión

**24 meses, uniformes para todos los tenants.**

**La variación por plan se aplica a la ventana de historia que el cliente ve en
la UI, no a lo que el sistema guarda.** Starter ve 30 días, Pro 12 meses,
Enterprise 24 — y los tres tienen 24 meses almacenados.

### Por qué 24 y no 5 años

Por [`ADR-000`](ADR-000-precedencia-documental.md), **N3 prevalece sobre N1
dentro de su dominio propio**. La retención de un rastro de auditoría es dominio
de seguridad y compliance, o sea de `plan-seguridad`. No hace falta desempatar
por otra vía: la regla de competencia ya resuelve.

### Por qué la invocación contable no alcanza a esta tabla

La spec justifica los 5 años "por obligaciones contables". Pero
`knowledge-base/12` §Tabla de retenciones **ya tiene una fila separada** para eso:

> `Datos contables (olas futuras)` — **10 años** (Resolución 4717/2020 de AFIP)

La obligación contable ya está asignada a los datos contables, y con un plazo
distinto del que la spec le pide a `audit_logs`. Y por `RN-AD-02` esta tabla
guarda **usuario, tenant, timestamp, IP, user-agent, tipo de acción, entidad
afectada, valores anteriores y posteriores, y `trace_id`**: es un rastro de
seguridad, no un libro contable. La spec parece haber fundido las dos cosas.

### Por qué el GTM no se rompe

Un mínimo de compliance **no puede ser un feature de plan**: si 24 meses es lo
que seguridad exige, un tenant Starter con 30 días quedaría por debajo del piso
de la propia organización.

Lo que sí puede variar por plan es **cuánto histórico ve el cliente**, y eso es
exactamente lo que el GTM vende sin decirlo así. `knowledge-base/13` ya lo
insinúa cuando lista "retención de auditoría" entre las cosas por las que
Enterprise se diferencia. La diferencia comercial se conserva; el piso, también.

---

## ⚠️ Pregunta legal abierta — bloquea el particionado

**¿Un asiento de `audit_logs` sobre una acción de facturación cuenta como
respaldo de un registro contable ante AFIP?**

Si la respuesta es que sí, esos asientos concretos caerían bajo el plazo de la
Resolución 4717/2020 y la retención de la tabla —o de una partición suya— tendría
que acompañar. Eso cambia el particionado y el volumen a proyectar.

**Dirección decidió el 18-ago-2026 que esto va a asesoramiento ANTES de fijar el
particionado.** Hasta que haya respuesta:

- ✅ La retención de 24 meses queda **decidida** y se puede documentar, diseñar y
  usar para dimensionar.
- ⛔ **NO se escribe la migración de `audit_logs`.** Crear la tabla particionada
  con una ventana que después haya que cambiar es, por la regla dura 13, una
  migración destructiva en potencia sobre la tabla de evidencia de compliance.

Quien retome esto: la pregunta es acotada y no requiere revisar todo el modelo.
Alcanza con determinar si el rastro de una acción de facturación constituye
comprobante o registro contable en los términos de esa resolución.

---

## Consecuencias

- El particionado mensual sigue siendo la forma prevista; **la cantidad de
  particiones vivas** queda sin fijar hasta la respuesta legal.
- La ventana por plan es lógica de consulta, no de almacenamiento: se implementa
  como filtro en el servicio de auditoría, y **el filtro es del servidor** — un
  cliente no puede pedir más historia que la de su plan.
- `knowledge-base/05` `RN-AD-04` queda desactualizada (registra el conflicto como
  abierto) y se corrige apuntando acá.
