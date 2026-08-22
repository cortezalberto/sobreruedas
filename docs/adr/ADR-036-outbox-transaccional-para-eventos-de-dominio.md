# ADR-036 — Los eventos de dominio salen por un outbox transaccional

- **Estado**: Aceptado
- **Fecha**: 2026-08-22
- **Decide sobre**: `ADR-009` ([`DD-09`](../../knowledge-base/09_decisiones_y_supuestos.md) — no tiene archivo propio: es uno de los 12 originales del corpus) · `T-016` (`platform/domain-events`) · C-14 (`VehicleService` → eventos)
- **Corrige**: `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados, fila *"Outbox / idempotencia de eventos"*

## Contexto

`app/core/events.py` está construido, probado y **conectado a nada**: sus únicos importadores son sus propios tests de integración. Ningún módulo de producción publica un evento. C-06 (notificaciones), C-16 (fotos), C-28 (automatizaciones del CRM) y C-30 (WhatsApp) esperan escuchar `vehicle.*`, y hoy la entidad central del sistema muta en silencio.

Al enchufar el primer productor apareció el problema de siempre con dos almacenes: **la escritura doble.**

`sesion_de_tenant` abre `async with sesion.begin()` y el commit ocurre **cuando termina la petición**, después del endpoint. `StockService` solo hace `flush()`. Un `await publicar(...)` dentro del servicio publica *antes* de que el vehículo exista: una violación de constraint posterior, un 500 en el router o una conexión caída dejan el evento en el stream y ningún vehículo en la base. **Un stream es append-only: no hay forma de retractarlo.** El consumidor de C-06 mandaría "se cargó un vehículo" por uno que no existe.

### El corpus nombra el patrón y describe otro

`knowledge-base/08_arquitectura_propuesta.md` lista **"Outbox / idempotencia de eventos"** como patrón aplicado, pero su columna de implementación dice *"Tabla `processed_events`, header `Idempotency-Key`"*. Eso es idempotencia **del consumidor**, no un outbox: un outbox es una tabla del **productor**, escrita en la misma transacción que el cambio que la origina. La fila funde dos mecanismos que resuelven problemas opuestos.

La mitad del consumidor **ya está hecha y bien**: `events.py` reusa `idempotency_keys` para reconocer un `event_id` reentregado, con la misma garantía `UNIQUE (tenant_id, key)` y sin migración nueva. Lo que no existe, y el corpus no especifica, es la mitad del productor.

### Las tres formas

| | Qué es | Falla |
|---|---|---|
| **A** | `await publicar(...)` en el servicio | Eventos fantasma, y **silenciosos** |
| **B** | Outbox: fila en la misma transacción, drenada después | — |
| **C** | Publicar después del commit, sin tabla | Pierde el evento si el proceso muere entre commit y publish |

C parece el punto medio barato y es el peor de los tres: cambia un fallo ruidoso por uno **silencioso**, y el que se pierde es peor porque nadie se entera.

## Decisión

**B.** Los eventos de dominio se escriben en `outbox_events` dentro de la misma transacción que el cambio que los origina, y se publican a Redis **después del commit**.

El argumento no es la pureza — es el momento. **Este es el primer productor de eventos del sistema**, y la forma que tome acá la copian C-16, C-19, C-24, C-27, C-28 y C-30. Migrar seis módulos después cuesta mucho más que la migración de hoy.

### Cómo se drena sin romper el aislamiento

El drenaje **no descubre las filas con una consulta**. El servicio anota los sobres pendientes en `sesion.info` al escribirlos, y la dependencia de sesión publica *esos* cuando la transacción ya commiteó, con el tenant todavía en contexto.

Eso importa por una razón concreta: **un drenaje que buscara filas pendientes tendría que leer el outbox de todos los tenants**, y eso choca con la regla dura 1 y con [`ADR-020`](ADR-020-rol-de-conexion-sin-bypass-de-rls.md) — el rol de aplicación es `NOSUPERUSER NOBYPASSRLS` y no puede, ni debe poder.

La tabla lleva las tres capas como cualquier otra: `tenant_id NOT NULL`, política RLS y `FORCE`.

### Si el commit no ocurre

El drenaje va **después** del `async with` de la sesión. Si el endpoint levanta, la excepción atraviesa el context manager, la transacción revierte y el código del drenaje **no corre**. La fila del outbox se fue con el rollback junto al vehículo. No hay evento fantasma posible.

## Lo que esta decisión NO cierra

**La recuperación automática queda pendiente, y está escrita acá para que no se dé por cubierta.**

Si el publish falla o el proceso muere entre el commit y el drenaje, la fila queda con `published_at IS NULL`. **El evento no se pierde** —queda una lista consultable de lo que no salió, que es estrictamente mejor que la opción C— pero **nadie la vuelve a intentar**. Hace falta un relay.

Y el relay necesita leer el outbox **cruzando tenants**, que es justamente lo que el rol de aplicación no puede hacer. **Es la misma pregunta que C-05 ya difirió**: cuando dejó `super_admins` legible por el rol de aplicación, lo escribió como *"con qué rol es arquitectura del espacio administrativo"* y la mandó a C-09.

Un rol `relay` dedicado —`NOBYPASSRLS`, con una política `FOR SELECT, UPDATE TO relay` acotada a esta única tabla— es la forma esperable, y el patrón para crearlo ya existe en [`infra/local/postgres/init/02-rol-de-aplicacion.sh`](../../infra/local/postgres/init/02-rol-de-aplicacion.sh). Lo que lo bloquea no es el diseño: **el init de PostgreSQL solo corre sobre un volumen vacío**, así que el rol no existiría ni en las bases de desarrollo actuales ni en el VPS, cuyo init es la tarea `9.2.b` de `foundation-setup` — hoy sin hacer y diferida por [`ESC-003`](../escalaciones/ESC-003-alcance-de-la-demo-de-tres-dias.md).

**Se resuelve junto con `super_admins`, no antes**: son la misma decisión sobre el mismo espacio.

## Consecuencias

- **Nunca un evento por algo que no pasó.** Es la garantía que se compró, y es la que no se puede agregar después sin reescribir a los seis productores.
- **Una traza de lo publicado que hoy no existe en ningún lado.** `outbox_events` responde "¿qué eventos emitió esta agencia y cuáles no salieron?", que ni Redis ni los logs contestan.
- **Sigue siendo "al menos una vez".** El drenaje puede publicar y morir antes de marcar la fila; el reintento futuro republicaría. Eso ya está cubierto por la idempotencia del consumidor que `events.py` implementa — no es deuda nueva, es el contrato de `ADR-009`.
- **Un `INSERT` más por mutación.** En la misma transacción y sin viaje de red extra. El costo real es el drenaje, que agrega un `XADD` por evento al final de la petición.
- **La fila del corpus queda corregida por este ADR**, no por una edición: `docs/sdd/` es inmutable y `knowledge-base/` es material derivado de él.
