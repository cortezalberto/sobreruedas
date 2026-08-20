# ADR-018 — Anclas de ADR del plan de implementación

- **Estado**: Aceptado
- **Fecha**: 2026-08-13
- **Decisores**: Tech Lead
- **Resuelve**: `IN-29` · `PA-14`
- **Afecta**: `T-007`, `T-098`, `T-099`, y la trazabilidad de las 194 tareas
- **Naturaleza**: **corrección de trazabilidad**, no cambio de diseño. Ninguna decisión técnica se modifica: se corrige a qué ADR apunta cada tarea. El corpus fuente **no se edita** — ver §Por qué no se corrige el documento.

---

## Contexto

`IN-29` es bloqueante: **la numeración de ADRs no coincide entre la spec técnica y el plan de implementación.** Quien lea el plan y salte al ADR que le indica, aterriza en la decisión equivocada.

[`ADR-000`](ADR-000-precedencia-documental.md) ya resolvió *quién* manda: la **spec técnica es N1** y **contiene** los ADRs con contexto, decisión, alternativas y consecuencias. El **plan es N2** y solo los **referencia**. Ante divergencia, gana la spec. Lo que faltaba era ejecutar esa resolución sobre las anclas concretas, y eso es lo que hace este ADR.

## La serie canónica

Los doce ADRs del SDD, tal como los define [`deRuedas-spec-tecnica.md`](../sdd/deRuedas-spec-tecnica.md) §1146–1386. **Esta es la lista de referencia del proyecto**:

| ADR | Título canónico | ¿Referenciado en el plan? |
|---|---|:-:|
| `ADR-001` | Arquitectura modular monolítica con eventos asíncronos | ❌ nunca |
| `ADR-002` | **PostgreSQL** como base de datos relacional principal | ⚠️ mal etiquetado |
| `ADR-003` | Python con FastAPI como stack del backend | ❌ nunca |
| `ADR-004` | Next.js para frontend web | ✅ correcto |
| `ADR-005` | **React Native con Expo** para aplicación móvil | ❌ mal usado |
| `ADR-006` | Multi-tenancy con discriminator + Row-Level Security | ✅ correcto |
| `ADR-007` | Autenticación con OAuth2 / OIDC vía Keycloak | ✅ correcto |
| `ADR-008` | Object storage S3-compatible para multimedia y documentos | ✅ correcto |
| `ADR-009` | Eventos de dominio con Redis Streams + Celery | ✅ correcto |
| `ADR-010` | WhatsApp Business Cloud API como única vía de mensajería | ❌ nunca |
| `ADR-011` | **OpenSearch** para búsqueda full-text y catálogo | ❌ nunca |
| `ADR-012` | Feature flags como herramienta de despliegue progresivo | ❌ nunca |

Los `ADR-013` en adelante son **posteriores al SDD** y viven en este directorio, no en la spec. `ADR-000` es metadocumental y precede a la serie entera.

## Decisión

### Las dos anclas mal apuntadas

**1. `ADR-005` no es OpenSearch. Es React Native con Expo.**

| Dónde | Dice | Debe decir |
|---|---|---|
| §7.2, índice de trazabilidad | `\| ADR-005 OpenSearch \| T-098, T-099 \|` | `ADR-011 OpenSearch` |
| `T-098` (OpenSearch index para vehicles + sync) | *"Spec técnica: SDD ADR-005"* | `SDD ADR-011` |
| `T-099` (endpoint `GET /api/v1/vehicles/search`) | *"P-libre con anchor a ADR-005"* | `anchor a ADR-011` |

Es el error más grave de los dos: manda a quien implemente la búsqueda a leer la decisión sobre la app móvil.

**2. `ADR-002` no es "Migrations". Es PostgreSQL.**

| Dónde | Dice | Debe decir |
|---|---|---|
| §7.2, índice de trazabilidad | `\| ADR-002 Migrations \|` | `ADR-002 PostgreSQL como base principal` |

Acá el problema es de **etiqueta, no de mapeo**: el plan le cambia el nombre a `ADR-002`. Sus tareas asociadas (`T-007` y las migraciones) siguen siendo correctas, porque Alembic existe al servicio de PostgreSQL.

**`T-007` conserva su ancla a `ADR-002`**, entendida como *PostgreSQL*: **ninguno de los doce ADRs cubre Alembic ni la estrategia de migraciones**. No es una referencia perfecta, es la más cercana que existe. Que no haya un ADR de migraciones es un vacío del SDD, no un error del plan.

`T-071` (*"SDD sección 3.4, ADR-002, ADR-006"*) ya es **correcta** y no se toca: una migración de `vehicles` con RLS ancla legítimamente en PostgreSQL y en multi-tenancy.

### Los cinco ADRs huérfanos

`ADR-001`, `ADR-003`, `ADR-010`, `ADR-011` y `ADR-012` **no aparecen ni una vez en el plan**. El índice de §7.2 cubre 7 de 12.

No se inventan anclas para taparlo. Se registra como lo que es: **el índice de trazabilidad del plan es parcial**, y quien busque el fundamento de una decisión va a la spec, no al índice.

### El hallazgo que nadie esperaba: `ADR-005` no tiene dónde anclar

Al buscar a qué tareas *debería* apuntar `ADR-005` una vez liberado de OpenSearch, apareció esto:

**El plan de implementación no tiene ni una sola tarea de aplicación móvil.** `frontend-mobile/` figura dos veces en 8.900 líneas: en el árbol del §4.1 y como client de Keycloak (§1989). Cero tareas `T-XXX`.

O sea: las 194 tareas **no cubren la app móvil**, aunque el stack la declara y `ADR-005` la decide. `ADR-005` queda correctamente sin anclas — no por error de referencia, sino porque **su alcance está fuera del plan**.

Esto excede a `IN-29` y no se resuelve acá. Se registra para que aparezca cuando corresponda: es alcance de producto, y el decisor es Dirección, no el Tech Lead. Emparenta con `R-1` (el contrato del portal deRuedas): **un vacío documental es un riesgo abierto, no una licencia para inferir** (regla 4 de [`ADR-000`](ADR-000-precedencia-documental.md)).

## Por qué no se corrige el documento

`tasks.md` de C-01 pedía, en su tarea 1.9, *"corregir en `docs/sdd/deRuedas-plan-implementacion.md` las anclas divergentes"*. **No se hace, y el motivo importa.**

`docs/sdd/` es **corpus fuente inmutable**. La regla está en `CLAUDE.md` y [`ADR-016`](ADR-016-trazas-distribuidas-tempo.md) ya la aplicó ante un caso idéntico: *"No se editan: son corpus fuente inmutable. Este ADR es el registro del desvío, y el Principio 5 establece que un ADR posterior reemplaza lo anterior."*

Editar el plan lo haría un documento **fuente y derivado a la vez**: nadie podría distinguir qué escribió el equipo original de qué corrigió un change posterior. Se pierde la trazabilidad que el corpus existe para dar.

Lo que sí se hace: **una anotación delimitada** al pie del índice de §7.2, que no altera ni una palabra del texto original y remite acá. Es el compromiso deliberado entre inmutabilidad y descubribilidad — porque un ADR que solo existe en `docs/adr/` depende de que alguien se acuerde de buscarlo, y a las tres de la mañana nadie se acuerda.

## Consecuencias

- **`T-098` y `T-099` se implementan contra `ADR-011`.** Caen en C-14 según [`CHANGES.md`](../../CHANGES.md); el change que las tome lee este ADR primero.
- **`T-007` mantiene `ADR-002`**, leído como *PostgreSQL*. Cae en C-01, bloque 6.
- **El índice de §7.2 del plan es parcial y queda marcado como tal.** No es fuente de trazabilidad completa: para eso está la tabla de este ADR.
- **`IN-29` y `PA-14` quedan cerrados.** La numeración canónica es la de la spec, y las divergencias están inventariadas con archivo y línea.
- **Falta un ADR de estrategia de migraciones.** Vacío del SDD, no de este change. Si C-02 necesita fijar convenciones de Alembic más allá de lo que `T-007` especifica, sale por ADR propio.
- **La ausencia de tareas móviles queda registrada** como asunto de alcance para Dirección. No bloquea ningún change de la Ola 0.

## Alternativas consideradas

**Editar el plan directamente**, como pedía la tarea 1.9. Deja la corrección donde el lector ya está mirando, sin saltos. Descartada porque rompe la inmutabilidad del corpus y desautoriza el precedente que `ADR-016` sentó apenas un día antes. Un principio que se abandona en su primera aplicación incómoda no es un principio.

**Solo el ADR, sin tocar el plan.** Máxima pureza: el corpus queda intacto de verdad. Descartada porque depende enteramente de que quien lea `T-098` se acuerde de que existe un ADR que lo corrige. La probabilidad de que eso pase, seis meses después y bajo presión, es baja — y el costo de equivocarse es leer la decisión sobre React Native para implementar una búsqueda.

**Regenerar el índice de §7.2 completo, con los 12 ADRs.** Tentador: arregla también los cinco huérfanos. Descartada porque sería **escribir contenido nuevo dentro del corpus fuente**, que es más invasivo todavía que corregir dos etiquetas. La tabla de este ADR cumple la misma función sin esa contradicción.
