# Funcionalidades

> Fuente primaria: `deRuedas-historias-usuario.md` (92 historias en 12 épicas). Complementado con `deRuedas-manual-usuario.md` (comportamiento observable) y `deRuedas-plan-implementacion.md` (mapeo a tareas).

## Estructura del backlog

- **12 épicas**: 8 funcionales (corresponden a los módulos del producto) + 4 transversales.
- **92 historias de usuario**, con IDs de formato `HU-E{n}-{correlativo}`.
- Priorización **MoSCoW** (Must / Should / Could) + estimación **Fibonacci** (1, 2, 3, 5, 8, 13, 21) + asignación a **Fase F1-F5**.
- Criterios de aceptación en formato **Gherkin** (Dado / Cuando / Entonces).

Distribución por fase: F1 = 30 HU · F2 = 16 · F3 = 16 · F4 = 25 · F5 = 5. Total 92. ✅ Consistente internamente.

⚠️ El plan de implementación usa una nomenclatura distinta (**Olas 0 y 1** con 194 tareas atómicas T-001..T-194, sin calendario) y un mapeo E1-E5 = MVP. La relación Fase ↔ Ola no está definida en ningún documento. Ver `IN-05`.

## Mapa de épicas

| ID | Épica | HU | Módulo | En MVP |
|---|---|---:|---|:---:|
| E1 | Onboarding y configuración | 8 | `tenancy`, `users`, `auth` | ✅ |
| E2 | Gestión de stock | 10 | `stock` | ✅ |
| E3 | Publicación multicanal | 6 | `publishing` | ⚠️ parcial (solo portal deRuedas) |
| E4 | CRM y pipeline comercial | 11 | `crm` | ✅ |
| E5 | Mensajería y WhatsApp Business | 8 | `communication` | ✅ núcleo |
| E6 | Permutas | 7 | `trade-in` | ❌ (F3) |
| E7 | Financiación integrada | 8 | `finance` | ❌ (F3) |
| E8 | Gestión documental | 7 | `documents` | ❌ (F4) |
| E9 | Cuenta corriente y conciliación | 7 | `accounting` | ❌ (F4) |
| E10 | Business intelligence | 8 | `analytics` | ❌ (F4) |
| E11 | Aplicación móvil | 6 | (React Native) | ❌ (F3-F4) |
| E12 | Administración y soporte (deRuedas) | 6 | `admin` | ⚠️ parcial |

---

## Épica 1 — Onboarding y configuración (8 HU)

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E1-001 | Alta de cuenta de agencia | Must | 5 | F1 |
| HU-E1-002 | Configuración inicial guiada | Must | 5 | F1 |
| HU-E1-003 | Gestión de sucursales | Must | 5 | F1 |
| HU-E1-004 | Gestión de usuarios y roles | Must | 8 | F1 |
| HU-E1-005 | Conexión con WhatsApp Business | Must | 13 | F1 |
| HU-E1-006 | Conexión con cuenta de deRuedas portal | Must | 8 | F1 |
| HU-E1-007 | Configuración de pipeline de ventas | Should | 5 | F2 |
| HU-E1-008 | Personalización visual de la cuenta | Could | 3 | F2 |

**HU-E1-001 — Alta de cuenta de agencia**
**Como** Gerente de agencia **quiero** dar de alta mi cuenta **para** empezar a operar.
Criterios: CUIT duplicado entre tenants → rechazo · Campos: CUIT, razón social, nombre comercial, email del responsable, teléfono.
Reglas: `RN-PL-01`, `RN-AU-16`.

**HU-E1-003 — Gestión de sucursales**
Criterios: el plan Starter **no permite multi-sucursal**, ofrece upgrade a Pro · No se puede eliminar una sucursal con vehículos asignados sin reasignar.
Reglas: `RN-PL-04`, `RN-PL-05`.

**HU-E1-007 — Configuración de pipeline de ventas**
⚠️ Criterio de aceptación en conflicto: la historia dice que el sistema trae **5 etapas** por defecto; el manual de usuario nombra **7**; el plan de implementación siembra **6**. Ver `IN-10`.

---

## Épica 2 — Gestión de stock (10 HU)

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E2-001 | Alta de vehículo con datos básicos | Must | 5 | F1 |
| HU-E2-002 | Carga de fotografías del vehículo | Must | 8 | F1 |
| HU-E2-003 | Edición y baja del vehículo | Must | 3 | F1 |
| HU-E2-004 | Estados del vehículo | Must | 5 | F1 |
| HU-E2-005 | Búsqueda y filtrado de stock | Must | 5 | F1 |
| HU-E2-006 | Importación masiva de stock | Should | 8 | F2 |
| HU-E2-007 | Histórico del vehículo | Should | 5 | F2 |
| HU-E2-008 | Sugerencia de precio basado en mercado | Could | 13 | F4 |
| HU-E2-009 | API pública de stock | Could | 13 | F5 |
| HU-E2-010 | Asignación de vendedor responsable | Must | 3 | F1 |

**HU-E2-001 — Alta de vehículo**
Campos: marca, modelo, versión, año, kilometraje, color, dominio, precio. El manual detalla 14 campos del formulario, incluyendo combustible, caja, patente **o** chasis, precio de costo interno, estado, fotos y descripción.
Criterio: dominio duplicado en la misma agencia → rechazo con opción de buscar el existente (`RN-ST-01`).

**HU-E2-002 — Carga de fotografías**
⚠️ "hasta veinte fotografías" según la historia; el plan de implementación permite 30; el manual recomienda 4-12 en un lugar y 8-15 en otro. Ver `IN-09`.
Criterio: archivo inválido o > 10 MB → rechazado (`RN-ST-11`).

**HU-E2-004 — Estados del vehículo**
⚠️ La historia enumera 5 estados: `disponible, reservado, vendido, en taller, en preparación`. El enum real tiene 6 (agrega `archived`). El manual sustituye `en taller` por `Pausado`. Ver `IN-11`.

**HU-E2-009 — API pública de stock**
Criterio: exceso de rate limit → **429** con header `Retry-After`.
⚠️ Disponibilidad por plan contradictoria: el GTM la da como *read-only en Pro y completa en Enterprise*; el manual la restringe a *solo Enterprise*. Ver `IN-25`.

---

## Épica 3 — Publicación multicanal (6 HU)

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E3-001 | Publicación automática en deRuedas | Must | 8 | F1 |
| HU-E3-002 | Pausar y reanudar publicación | Must | 3 | F1 |
| HU-E3-003 | Publicación a MercadoLibre Vehículos | Should | 13 | F2 |
| HU-E3-004 | Publicación a Marketplace de Facebook | Could | 13 | F5 |
| HU-E3-005 | Vista de estado de publicaciones | Must | 3 | F1 |
| HU-E3-006 | Plantillas de descripción | Should | 5 | F2 |

Estados de publicación (HU-E3-005): `publicado`, `pausado`, `error`, `pendiente`.
Tiempos observables (manual): sincronización inicial 15 min – 2 h; vehículo nuevo aparece en el portal en 5-15 min.

---

## Épica 4 — CRM y pipeline comercial (11 HU)

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E4-001 | Captura automática de leads desde portales | Must | 8 | F1 |
| HU-E4-002 | Captura manual de leads | Must | 3 | F1 |
| HU-E4-003 | Vista Kanban del pipeline | Must | 8 | F1 |
| HU-E4-004 | Detalle del lead | Must | 5 | F1 |
| HU-E4-005 | Reasignación de lead | Must | 3 | F1 |
| HU-E4-006 | Recordatorios automáticos de seguimiento | Should | 5 | F2 |
| HU-E4-007 | Reglas de asignación automática | Should | 8 | F2 |
| HU-E4-008 | Cierre de lead con motivo de pérdida | Must | 5 | F1 |
| HU-E4-009 | Etiquetado de leads | Could | 3 | F2 |
| HU-E4-010 | Identificación de leads duplicados | Should | 8 | F2 |
| HU-E4-011 | Programación de actividades | Should | 5 | F2 |

**HU-E4-004 — Detalle del lead**: datos de contacto, vehículo de interés, etapa actual, historial de interacciones, mensajes de WhatsApp, notas — todo en una vista.
**HU-E4-005 — Reasignación**: solo el `manager` puede reasignar (`RN-CR-13`).
**HU-E4-006 — Recordatorios**: ⚠️ el umbral de inactividad varía entre 3 días, 5 días, 24 h y 48 h según la fuente. Ver `IN-20`.
**HU-E4-008 — Cierre**: `loss_reason_id` obligatorio al perder (`RN-CR-05`); al ganar, el vehículo pasa a `sold` (`RN-CR-06`).

---

## Épica 5 — Mensajería y WhatsApp Business (8 HU)

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E5-001 | Bandeja de entrada unificada | Must | 13 | F1 |
| HU-E5-002 | Asociación automática de conversación a lead | Must | 8 | F1 |
| HU-E5-003 | Templates de mensaje aprobados | Should | 8 | F2 |
| HU-E5-004 | Chatbot de respuesta inicial | Should | 13 | F2 |
| HU-E5-005 | Compartir conversaciones entre vendedores | Should | 5 | F2 |
| HU-E5-006 | Envío de archivos y multimedia | Must | 8 | F1 |
| HU-E5-007 | Búsqueda en historial de mensajes | Could | 5 | F2 |
| HU-E5-008 | Indicadores de leídos y respuesta | Must | 3 | F1 |

Reglas asociadas: `RN-WA-01` a `RN-WA-12`. La ventana de 24 h de Meta es la restricción dominante del módulo.
Objetivo de latencia percibida: un mensaje entrante debe verse en el frontend en **< 1 segundo** (canal en tiempo real; ⚠️ SSE vs WebSocket, ver `IN-08`).

---

## Épica 6 — Permutas (7 HU) — Fase 3

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E6-001 | Iniciar solicitud de permuta | Must | 5 | F3 |
| HU-E6-002 | Valuación con apoyo de mercado | Must | 8 | F3 |
| HU-E6-003 | Inspección física del usado | Must | 5 | F3 |
| HU-E6-004 | Propuesta formal al cliente | Must | 5 | F3 |
| HU-E6-005 | Cierre de permuta y alta automática de stock | Must | 8 | F3 |
| HU-E6-006 | Histórico de permutas | Should | 5 | F4 |
| HU-E6-007 | Permuta múltiple | Could | 8 | F5 |

Reglas: `RN-PE-01` a `RN-PE-06`. ⚠️ El manual de usuario **no cubre permutas** — laguna de documentación de cara al usuario final.

---

## Épica 7 — Financiación integrada (8 HU) — Fase 3

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E7-001 | Conexión con financiera | Must | 8 | F3 |
| HU-E7-002 | Precalificación crediticia rápida | Must | 13 | F3 |
| HU-E7-003 | Comparación de ofertas de crédito | Must | 8 | F3 |
| HU-E7-004 | Solicitud formal de crédito | Must | 13 | F3 |
| HU-E7-005 | Seguimiento de estado de solicitud | Must | 5 | F3 |
| HU-E7-006 | Firma electrónica de documentos | Should | 13 | F3 |
| HU-E7-007 | Reporte de comisiones de originación | Should | 5 | F4 |
| HU-E7-008 | Simulador público de crédito | Could | 8 | F5 |

Reglas: `RN-FI-01` a `RN-FI-07`. Precalificación en < 30 s con DNI, ingresos declarados y monto.
⚠️ El manual de usuario **no menciona financiación en absoluto**.

---

## Épica 8 — Gestión documental (7 HU) — Fase 4

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E8-001 | Carga de documentos del vehículo | Must | 5 | F4 |
| HU-E8-002 | OCR y auto-clasificación | Should | 13 | F4 |
| HU-E8-003 | Alertas de vencimiento | Should | 5 | F4 |
| HU-E8-004 | Búsqueda full-text | Should | 8 | F4 |
| HU-E8-005 | Paquete documental para registro | Must | 5 | F4 |
| HU-E8-006 | Firma electrónica básica | Could | 13 | F5 |
| HU-E8-007 | Documentación del cliente comprador | Must | 5 | F4 |

Reglas: `RN-DO-01` a `RN-DO-06`. Documento sin OCR exitoso queda en estado "por clasificar".

---

## Épica 9 — Cuenta corriente y conciliación (7 HU) — Fase 4

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E9-001 | Registro de cobros de operación | Must | 5 | F4 |
| HU-E9-002 | Cuenta corriente de cliente | Must | 5 | F4 |
| HU-E9-003 | Conciliación con extracto bancario | Should | 13 | F4 |
| HU-E9-004 | Generación de comprobantes de pago | Must | 3 | F4 |
| HU-E9-005 | Exportación a contabilidad | Should | 8 | F4 |
| HU-E9-006 | Pagos a proveedores | Should | 5 | F4 |
| HU-E9-007 | Cálculo de margen por operación | Should | 8 | F4 |

Cobro: monto, fecha, medio de pago, comprobante, cotización si es moneda extranjera.
Exportación a **Tango, Bejerman o Excel**. Explícitamente **no reemplaza un ERP**.

---

## Épica 10 — Business intelligence (8 HU) — Fase 4

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E10-001 | Dashboard de stock | Must | 8 | F4 |
| HU-E10-002 | Dashboard de pipeline | Must | 8 | F4 |
| HU-E10-003 | Dashboard de ventas | Must | 5 | F4 |
| HU-E10-004 | Dashboard de productividad | Should | 8 | F4 |
| HU-E10-005 | Dashboard financiero | Should | 8 | F4 |
| HU-E10-006 | Reportes personalizables | Could | 13 | F5 |
| HU-E10-007 | Exportación de reportes | Should | 5 | F4 |
| HU-E10-008 | Reporte de canales de origen de leads | Should | 8 | F4 |

Métricas: composición y rotación de stock por marca/modelo/antigüedad · pipeline por etapa con valor potencial y probabilidad ponderada · ventas por período con margen bruto y comparación interanual · productividad por vendedor (leads asignados, conversiones, ticket promedio) · fuentes de leads con costo y conversión por canal · salud financiera (cuentas por cobrar/pagar, flujo proyectado).

Restricciones observables (manual): exports limitados a **50.000 filas** por archivo, disponibles para descarga durante **30 días**. Reportes programables (cadencia + destinatarios + formato PDF/Excel/link) — solo Enterprise para los personalizados.

---

## Épica 11 — Aplicación móvil (6 HU) — Fase 3-4

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E11-001 | Login y sesión persistente en móvil | Must | 5 | F3 |
| HU-E11-002 | Carga de vehículo desde celular con cámara | Must | 8 | F3 |
| HU-E11-003 | Gestión de leads en móvil | Must | 8 | F3 |
| HU-E11-004 | Notificaciones push | Must | 5 | F3 |
| HU-E11-005 | Dashboard móvil para gerente | Should | 5 | F4 |
| HU-E11-006 | Mensajería en móvil | Must | 8 | F3 |

La app alcanza paridad funcional con la web en la Fase 4. El plan de implementación **no tiene tareas de mobile** en las olas 0-1.

---

## Épica 12 — Administración y soporte (deRuedas) (6 HU)

| ID | Título | Prioridad | Est. | Fase |
|---|---|---|---:|:---:|
| HU-E12-001 | Listado y búsqueda de tenants | Must | 5 | F1 |
| HU-E12-002 | Vista detallada de tenant | Must | 8 | F1 |
| HU-E12-003 | Gestión de planes y precios | Must | 8 | F1 |
| HU-E12-004 | Gestión de tickets de soporte | Must | 8 | F1 |
| HU-E12-005 | Métricas de salud de tenant | Should | 13 | F4 |
| HU-E12-006 | Monitoreo técnico del sistema | Should | 13 | F2 |

---

## Definición de terminado (Definition of Done)

Toda historia, para considerarse terminada, cumple:

- [ ] Al menos **1 prueba E2E** del flujo principal.
- [ ] Al menos **1 prueba unitaria por regla de negocio nueva**.
- [ ] Cobertura del módulo no disminuye.
- [ ] Toda query incluye condición de tenant y las políticas RLS están activas.
- [ ] Checklist **OWASP Top 10** aplicado a los endpoints nuevos.
- [ ] Accesibilidad **WCAG 2.1 nivel AA**.
- [ ] Consultas de listado nuevas responden **< 200 ms p95**.
- [ ] CI en verde, docs actualizadas, review de otro autor.
- [ ] Migración reversible; anclaje al SDD declarado.

## Atajos de teclado (producto web)

`G+D` Dashboard · `G+S` Stock · `G+L` Leads · `G+M` Mensajes · `G+R` Reportes · `Ctrl+K` buscador global · `Ctrl+N` crear nuevo · `Ctrl+S` guardar · `Esc` cerrar modal · `?` ayuda contextual.
