# ESC-001 — La infraestructura elegida no sostiene los SLA publicados

- **Estado**: 🔴 **ABIERTA** — requiere decisión
- **Fecha**: 2026-08-17
- **Eleva**: Tech Lead
- **Decide**: **Dirección + SRE** (decisor registrado para el dominio de disponibilidad)
- **Origen**: [`ADR-023`](../adr/ADR-023-despliegue-sobre-vps-con-docker-compose.md) §Conflicto declarado con N3 — trabajo derivado 4
- **Registrada como**: `PA-30` en [`knowledge-base/10_preguntas_abiertas.md`](../../knowledge-base/10_preguntas_abiertas.md)
- **Bloquea**: nada en el corto plazo. **No frena la implementación.** Frena la *venta* de lo que no se puede cumplir.

---

## Qué se decidió y por qué esto aparece ahora

El 17-ago-2026 `ADR-023` cambió el despliegue de un cluster gestionado a un **VPS único en Hostinger con Docker Compose**. La decisión se tomó por costo y simplicidad operativa, y es sólida para la etapa del producto: no hay un solo cliente todavía, y un cluster gestionado factura todos los meses desde antes del primero.

Esa decisión es **N1** (técnica). Los SLA son **N3** (`plan-sre`), y por `ADR-000` **N3 prevalece sobre N1 dentro de su dominio propio**. Un ADR no puede modificar el SLA, y `ADR-023` no lo intentó: dejó el conflicto declarado y lo escaló acá.

**Nada de esto es un error de `ADR-023`.** Es la consecuencia esperada de la decisión, registrada en el momento de tomarla en vez de descubrirse cuando un cliente reclame.

## El conflicto, en concreto

Los SLA vigentes quedaron fijados por `ADR-000` al resolver `PA-09` (**99.0 / 99.5 / 99.9**). Ese número ya está decidido y **esta escalación no lo reabre**. Lo que se pregunta es distinto: **la infraestructura no alcanza los números que ya están decididos.**

| Compromiso vigente (N3) | Qué pasa sobre un nodo único |
|---|---|
| **Enterprise 99.9 %** — 43 min de caída al mes | Sin redundancia, **una sola** ventana de mantenimiento del proveedor o un reinicio de kernel consume el presupuesto del mes entero. |
| **DR en región alternativa** — RTO 4 h, RPO 1 h | **No existe región alternativa.** El compromiso no está ajustado: es inalcanzable por construcción. |
| PostgreSQL replicas — RTO 30 min | Presupone una réplica. Sobre un nodo único **no hay ninguna**. |
| PostgreSQL primary — RTO 1 h, RPO 5 min | ✅ **Alcanzable** — con archivado de WAL fuera del VPS y restauración probada (tareas 9.21 y 9.22). |
| Backup *cross-region* semanal + snapshots con *object lock* | Requiere un segundo destino de almacenamiento. Hoy no está previsto. |
| Ola 3 — *"multi-región activo con RTO < 30 min"* | Incompatible por diseño con un nodo único. |

Pro (99.5 %, 3 h 36 min de presupuesto mensual) y Starter (99.0 %, 7 h 12 min) son **defendibles** sobre un VPS bien operado. El problema se concentra en **Enterprise** y en **DR**.

## La exposición es contractual, no solo técnica

Los tres planes tienen **crédito por incumplimiento** escrito contra estos números. El SLA aparece como fila **"SLA contractual"** en la **Versión A** del pricing (`plan-gtm.md`), así que es contra los precios de esa versión que hay que medir la exposición:

| Plan | Precio (Versión A) | SLA | Crédito si se incumple | Exposición por tenant y mes |
|---|---|---|---|---|
| Starter | USD 49 | 99.0 % | 5 % | USD 2,45 |
| Pro | USD 149 | 99.5 % | 10 % | USD 14,90 |
| **Enterprise** | **USD 399 (desde)** | **99.9 %** | **25 %** | **USD 99,75 (desde)** |

Con 43 minutos de presupuesto mensual y cero redundancia, el incumplimiento de Enterprise no es un riesgo de cola: es el escenario probable de cualquier mes con mantenimiento del proveedor.

> ⚠️ **Dos precisiones que conviene corregir antes de que esto circule:**
>
> 1. `ADR-023` describe la exposición como *"planes con **devolución de dinero**"*. No es exacto: lo que existe son **créditos de servicio** sobre la suscripción, no reembolsos. La exposición es real pero **menor y de distinta naturaleza** que un *money-back*.
> 2. La exposición **no se puede calcular contra la Versión B** del pricing (`mejoras-y-saas.md`: Starter ARS 45.000 / Pro ARS 95.000 / Enterprise ARS 195.000). Esa versión **no tiene fila de SLA**. Cruzar el SLA de una versión con los precios de la otra mezcla los **dos modelos de pricing incompatibles** que `14_pricing_y_gtm.md` documenta sin resolver (`PA-03`, `PA-04`) — que es exactamente el error que esta escalación pide no cometer.
>
> El orden de magnitud de la decisión no cambia con ninguna de las dos correcciones. La precisión sí importa si el documento va a Dirección.

## Qué se pide decidir

No hay una respuesta técnicamente correcta: es un trade-off entre costo y compromiso comercial, y por eso lo decide Dirección con SRE, no el Tech Lead.

**Opción A — Ajustar lo publicado a lo que la infraestructura sostiene.**
Bajar el SLA de Enterprise, retirar el compromiso de DR en región alternativa, y no ofrecer Enterprise hasta tener redundancia. Costo cero de infraestructura. Costo comercial: Enterprise pierde su diferencial de disponibilidad, y el primer cliente multi-sucursal es un objetivo declarado de Ola 2.

**Opción B — Dotar de redundancia antes de vender Enterprise.**
Un segundo VPS y una réplica de PostgreSQL. Enterprise se sigue vendiendo como está. Costo: infraestructura adicional recurrente más el trabajo de operarla, que sobre Compose es manual.

**Opción C — Vender Enterprise solo bajo contrato con SLA negociado individualmente**, distinto del publicado, hasta que exista redundancia. Preserva el canal comercial y acota la exposición, a costa de que cada venta Enterprise pase por revisión.

**Lo que no es opción**: dejarlo como está. Hoy hay números publicados que la infraestructura no puede cumplir, con crédito asociado. Cada mes que pasa sin decidir es exposición acumulada sobre cada contrato Enterprise que se firme.

## Qué pasa mientras tanto

- La implementación **no se frena**. El bloque 9 de `C-01` despliega sobre el VPS igual, y las tareas que sí protegen (archivado de WAL fuera del VPS, ejercicio de restauración fechado) están dentro del alcance actual.
- Lo que **sí conviene frenar hasta la decisión** es publicar o firmar el SLA de Enterprise.
- El conflicto queda visible en `ADR-023`, en `PA-30` y acá. No se cierra ni se esconde hasta que el decisor se pronuncie.

## Registro de la decisión

> Completar cuando Dirección + SRE se pronuncien.

| Fecha | Participante | Postura | Comentario |
|---|---|---|---|
| 2026-08-17 | Tech Lead | Eleva | Apertura de la escalación, derivada de `ADR-023` |
