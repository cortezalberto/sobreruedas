# Visión y Objetivos

> Fuentes: `deRuedas-constitucion.md`, `deRuedas-mejoras-y-saas.md`, `deRuedas-spec-tecnica.md`, `deRuedas-plan-gtm.md`, `deRuedas-historias-usuario.md`, `deRuedas-brand-book.md`.
> Todo lo que está acá está derivado de las fuentes. Lo que no se pudo derivar está en [10_preguntas_abiertas.md](10_preguntas_abiertas.md).

## Propósito del sistema

**deRuedas Gestión es un SaaS vertical multi-tenant, diseñado específicamente para la operación integral de agencias y concesionarias de vehículos del mercado argentino.**

La visión declarada es "convertirse en la espina dorsal operativa de las agencias clientes, gestionando desde el alta del vehículo en stock hasta la conciliación financiera de la venta, pasando por el contacto comercial, la gestión documental, las permutas y la financiación".

El contexto estratégico importa para entender las decisiones de producto: deRuedas.com.ar es un portal de clasificados de vehículos con más de 17 años de operación, ~550 agencias activas y fuerte presencia en el interior argentino. Su modelo de monetización lineal por aviso está bajo presión de MercadoLibre Vehículos, Kavak/OLX Autos (modelo transaccional) y Marketplace de Facebook (gratuito). Los antecedentes de DeMotores (cierre, 2021) y DeAutos (venta al Banco Supervielle, 2019) se citan explícitamente como el destino a evitar.

El SaaS **no es un producto auxiliar**: es la pieza central de la transformación del modelo de negocio. Su función estratégica es generar **lock-in** — una vez que la agencia carga su stock, sus leads históricos y su configuración operativa, el costo de cambio crece dramáticamente. Esa es, según la fuente, "la única defensa estructural realmente sostenible".

**Contra quién compite realmente**: Excel, cuadernos y WhatsApp. No compite contra CRMs enterprise. Esto condiciona todo el diseño (ver Principio 2 en [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md)).

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|---|---|---|
| **Gerente / dueño de agencia** (`manager`) | Tener visibilidad real del negocio: qué stock tiene, qué rota, cuánto margen deja cada operación, qué hace cada vendedor | Reducir trabajo manual, controlar el equipo sin microgestión, decidir sobre datos y no sobre intuición, consultar todo desde el celular |
| **Vendedor** (`salesperson`) | No perder ningún lead y responder rápido | Tener el historial completo del cliente a mano, cargar vehículos desde el celular, cerrar más operaciones |
| **Administrativo/a** (`admin_staff`) | Ordenar la documentación y la cobranza de cada operación | Generar comprobantes, exportar a contabilidad, conciliar pagos |
| **Customer Success (deRuedas)** | Que la agencia adopte el producto y no churnee | Onboarding asistido, detectar señales tempranas de abandono, soporte |
| **Super Admin (deRuedas)** | Operar la plataforma multi-tenant | Alta/suspensión de tenants, gestión de planes, salud técnica del sistema, soporte de segundo nivel |
| **deRuedas como empresa** | Convertir una relación transaccional por aviso en una relación de plataforma con lock-in | Ingreso recurrente predecible, datos de stock en tiempo real para el portal, insumo para la capa de datos y de IA |
| **Comprador final** | (Actor indirecto) Recibir respuesta rápida por WhatsApp | No interactúa directamente con el sistema |

> ⚠️ Los nombres de los roles **no son consistentes entre documentos** (Gerente/Vendedor/Administrativo vs `manager`/`salesperson`/`admin_staff`, y `super_admin` existe o no según el documento). Ver `IN-01` en [10_preguntas_abiertas.md](10_preguntas_abiertas.md).

## Alcance del producto completo (v1.0, horizonte 18 meses)

El producto completo se descompone en **8 módulos funcionales** (según `mejoras-y-saas`) / **16 módulos de backend** (según `spec-tecnica`) / **12 épicas** (según `historias-usuario`). Ver `IN-30`.

- **Stock**: alta de vehículos con ficha técnica completa, fotos, estados, multi-sucursal, importación masiva, historial.
- **Publicación multicanal**: sincronización automática hacia el portal deRuedas; MercadoLibre Vehículos y Marketplace de Facebook en fases posteriores.
- **CRM y pipeline comercial**: leads con pipeline por etapas, asignación, actividades, recordatorios, motivos de pérdida, reportes de conversión.
- **Mensajería / WhatsApp Business**: bandeja unificada multi-vendedor, templates aprobados por Meta, chatbot inicial, ventana de 24 h.
- **Permutas** (`trade-in`): solicitud, valuación con apoyo de mercado, inspección de 100 puntos, propuesta, cierre con alta automática del usado en stock.
- **Financiación integrada**: precalificación, comparación de ofertas de financieras, solicitud formal, firma electrónica, seguimiento, comisión de originación.
- **Gestión documental**: carga, OCR y auto-clasificación, alertas de vencimiento, búsqueda full-text, paquete documental para el registro automotor.
- **Cuenta corriente y conciliación**: cobros, cuenta corriente por cliente, conciliación bancaria, comprobantes, exportación a Tango/Bejerman, margen por operación.
- **Business intelligence**: dashboards de stock, pipeline, ventas, productividad por vendedor y financiero.
- **Aplicación móvil** (React Native): login persistente, carga con cámara, gestión de leads, push, mensajería.
- **Administración y soporte interno** (backoffice deRuedas): tenants, planes, tickets, métricas de salud, monitoreo técnico.

## Alcance del MVP

⚠️ **Hay dos definiciones de MVP en el corpus y no coinciden en su encuadre temporal.** Ver `IN-05`.

El alcance funcional del MVP sí es consistente: **épicas E1 a E5**.

- **E1 — Onboarding y configuración**: alta de cuenta, wizard de configuración, sucursales, usuarios y roles, conexión con WhatsApp Business, conexión con el portal deRuedas.
- **E2 — Gestión de stock**: alta/edición/baja de vehículo, fotos, estados, búsqueda y filtrado, asignación de vendedor. **Sin** motor de pricing sugerido por IA.
- **E3 — Publicación** (parcial): solo el conector al portal deRuedas. MercadoLibre y Facebook postergados.
- **E4 — CRM y pipeline**: captura automática y manual de leads, Kanban, detalle, reasignación, cierre con motivo de pérdida.
- **E5 — WhatsApp Business** (núcleo): bandeja unificada, asociación conversación↔lead, envío de multimedia, indicadores de leído.

## Fuera de alcance (explícito)

- **Extensibilidad a otros verticales** (motos, maquinaria agrícola, embarcaciones). Declarado anti-patrón: la generalización prematura se rechaza por constitución.
- **ERP contable completo**. El módulo de cuenta corriente cubre lo operativo mínimo y se integra con Tango/Bejerman; no los reemplaza.
- **Autenticación construida a medida** — prohibido por constitución (ADR-007: Keycloak).
- **Configurabilidad amplia desde el día uno**. Se privilegian valores por defecto razonables; la configurabilidad se gana con datos de uso.
- **Signup público self-service con cobro recurrente** — postergado; en el MVP las cuentas se crean por invitación desde el backoffice. ⚠️ Contradicho por el plan GTM (`IN-14`).
- **Chatbots conversacionales avanzados y calificación automática de leads con IA** — fuera del MVP.
- **Multi-número de WhatsApp por sucursal** — fuera del MVP.
- **Microservicios** — descartado en ADR-001 a favor de monolito modular.
- **API pública y marketplace de plugins** — Fase 5 / Ola 3.

## Métricas de éxito

Métricas de producto (meta a 24 meses, según `mejoras-y-saas`):

| Métrica | Meta |
|---|---|
| Cuentas activas | 220 agencias |
| Tasa de activación (≥5 vehículos en 14 días) | 65 % |
| Adherencia DAU/MAU | 55 % |
| Churn mensual | < 3 % |
| ARPU | ARS 140.000 |
| LTV/CAC | > 3,5 |
| NPS | > 45 |
| MRR | ARS 30 millones |
| Tiempo mediano de resolución de soporte | < 8 h hábiles |
| Operaciones financiadas por mes | > 300 |

Métricas comerciales (según `plan-gtm`, **en USD y con otros valores** — ver `IN-04`):

| Métrica | Objetivo |
|---|---|
| CAC | USD 250-600 |
| Payback de CAC (Pro) | < 6 meses |
| LTV | ≥ USD 4.500 |
| LTV/CAC | ≥ 7 |
| Churn mensual | < 3 % |
| Margen bruto plan Pro | 75 % |
| NPS | > 40 (MVP), > 50 (madurez) |
| Win rate | > 25 % |
| NRR | > 100 % |

Dos **métricas estratégicas** propias (`mejoras-y-saas`):

1. **Tasa de retención de avisos**: las agencias que además son clientes del SaaS deben retener su suscripción al portal por encima del 90 % anual, contra ~70 % de las que solo tienen avisos. Ese diferencial *es* la materialización del lock-in que justifica la inversión.
2. **Participación de mercado entre agencias del interior**: > 15 % en provincias seleccionadas a 36 meses.
