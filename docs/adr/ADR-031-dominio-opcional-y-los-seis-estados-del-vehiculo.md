# ADR-031 — El dominio del vehículo es opcional, y los estados son seis

- **Estado**: ✅ **Aceptado**
- **Fecha**: 18 de agosto de 2026
- **Change**: `C-14` (`vehiculos-modelo-y-servicios`), gobernanza **ALTA**
- **Cierra**: `IN-07` (dominio `NOT NULL`) e `IN-11` (cuántos estados)
- **Depende de**: [`ADR-000`](ADR-000-precedencia-documental.md)

> **Por qué se decide ahora**: los schemas Pydantic de Stock no se pueden
> escribir sin esto. `domain_plate` obligatorio u opcional cambia el contrato de
> entrada, y la lista de estados cambia el enum de salida. Regla dura 12.

---

## `IN-07` — El dominio es **opcional**, con una condición

`spec-tecnica` §3.4 declara `domain_plate` **NOT NULL**, y el glosario
constitucional lo refuerza: *"un vehículo se identifica unívocamente dentro de
un tenant por su dominio"*. El plan de implementación (`T-071`) lo declara
**nullable**, y `manual-usuario` §2.7.1 dice *"patente **o** chasis (opcional)"*.

### La decisión

**`domain_plate` es nullable**, con dos garantías que reemplazan lo que el
`NOT NULL` pretendía dar:

```sql
UNIQUE (tenant_id, domain_plate) WHERE deleted_at IS NULL AND domain_plate IS NOT NULL
CHECK  (domain_plate IS NOT NULL OR chassis_number IS NOT NULL)
```

### Por qué la spec está equivocada acá

No es una preferencia de modelado: **hay vehículos reales que no tienen patente
todavía**. Un 0 km sin patentar y un usado recién recibido en permuta son los
dos casos más comunes del negocio, y con `NOT NULL` una agencia no podría
cargarlos — que es exactamente lo que el producto existe para hacer.

El glosario dice que el dominio **identifica** al vehículo, y eso se conserva:
el índice único sigue garantizando que no haya dos con el mismo dominio. Lo que
cambia es que la identificación puede llegar después del alta. El `CHECK`
asegura que ningún vehículo entre sin **ninguna** forma de identificarse.

⚠️ **Esto no contradice a N0.** El glosario define qué identifica a un vehículo,
no exige que ese dato exista en el momento del alta. Si alguien lee que sí, la
salida es el Artículo 8 — pero la lectura natural no lo pide.

---

## `IN-11` — Son **seis** estados, y lo resuelve una regla que ya estaba escrita

Tres listas distintas en el corpus:

| Fuente | Nivel | Estados |
|---|---|---|
| `spec-tecnica` + plan | N1 + N2 | **6**: `in_preparation` · `available` · `reserved` · `sold` · `in_workshop` · `archived` |
| `historias-usuario` HU-E2-004 | N4 | 5 — sin `archived` |
| `manual-usuario` §4.2.3 | N4 | 5 distintos — sin `in_workshop`, con `Pausado` |

### La decisión

**Los seis.** Y no hace falta desempatar por precedencia —aunque también
alcanzaría, porque las dos listas de cinco son **N4, no normativo**—: lo resuelve
`RN-ST-05`, que enumera las transiciones permitidas y **usa `archived` en tres de
ellas** (`sold→archived`, `available→archived`, `archived→available`). Una lista
de estados que no incluya `archived` deja esa regla sin sentido.

### `Pausado` no es un estado del vehículo

Es casi con seguridad el estado de la **publicación**: un aviso se pausa, un auto
no. El manual mezcla los dos conceptos. Se descarta del enum del vehículo y se
deja anotado para el dominio de publicación (C-22/C-23), que es donde
corresponde.

---

## ⚠️ Una regla de negocio que aparece en un solo documento — pregunta abierta

`manual-usuario` §4.2.3 agrega que **"la reserva se libera automáticamente a los
7 días"**. Esa regla **no está en ningún otro documento**: no en `RN-ST`, no en
la spec, no en el plan.

Por precedencia no es vinculante — `manual-usuario` es **N4**. Pero no es un
detalle de redacción: si esa regla existe, hace falta un proceso que libere
reservas vencidas, y eso es trabajo que hoy no está en ningún change.

**Se implementa SIN la liberación automática**, y queda la pregunta para
Dirección: *¿la reserva vence sola a los 7 días, o la libera un humano?* Si la
respuesta es que vence sola, entra como regla `RN-ST` nueva y como tarea de
C-14, no como un arreglo silencioso.

---

## Consecuencias

- Los schemas de entrada de Stock **no** exigen `domain_plate`, y validan que
  venga al menos uno de dominio o chasis.
- El enum de salida tiene los seis estados; las transiciones salen de `RN-ST-05`.
- ⛔ **Los schemas de fotos NO se escriben todavía**: `IN-09` sigue abierto y
  tiene **cuatro** valores para el límite por vehículo (20, 30, 4-12, 8-15). Un
  contrato de subida sin ese número es un contrato incompleto.
