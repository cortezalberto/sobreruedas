# Pricing y Go-To-Market

> Fuentes: `deRuedas-plan-gtm.md` (fuente primaria) y `deRuedas-mejoras-y-saas.md` §10-§14.
> ⚠️ **Estos dos documentos presentan dos modelos de pricing incompatibles**: distinta moneda, distintos precios y distintos límites. Ver `IN-03`, `IN-04`, `IN-21`, `IN-41`, `IN-42`, `IN-50`.

## Advertencia previa

No existe un pricing canónico en el corpus. Lo que sigue documenta **ambas versiones** en paralelo. Cualquier implementación de facturación o de `PlanLimitsService` requiere resolver `PA-03` y `PA-04` primero.

---

## Versión A — `plan-gtm.md` (más detallada y probablemente más reciente)

| | **Starter** | **Pro** | **Enterprise** |
|---|---|---|---|
| **Precio mensual** | **USD 49** | **USD 149** | **USD 399 (desde)** |
| Vendedores incluidos | 2 usuarios | 5 usuarios | 15 usuarios |
| Vendedor extra | USD 15/mes c/u | USD 12/mes c/u | USD 10/mes c/u |
| Vehículos en stock | Hasta 80 | Hasta 300 | Sin límite práctico |
| Mensajes WhatsApp/mes | 1.500 | 5.000 | 20.000 |
| Sucursales | 1 | Hasta 2 | Hasta 5 |
| Portal sectorial | Sí | Sí | Sí |
| WhatsApp Business | Sí | Sí | Sí |
| Reportes avanzados | Básicos | Completos | Completos |
| Pipeline customizable | Estándar | Customizable | Customizable |
| API pública | No | Read-only | Completa |
| SSO | No | No | Sí |
| DPA | Estándar | Estándar | Personalizable |
| **SLA contractual** | **99.0 %** | **99.5 %** | **99.5 %** ⬇️ |
| Soporte | Email, día hábil | Email + WhatsApp, horas hábiles | Dedicado, 24/7 para críticos |
| Onboarding | **Self-service** ⚠️ | 1 sesión guiada (60 min) | Plan completo (kickoff 90 min + 3 sesiones + CSM) |
| Audit logs | 30 días | 12 meses | 24 meses ⚠️ |
| Exports | Sí | Sí | Sí + API |

> ⬇️ **El SLA de Enterprise bajó de 99.9 % a 99.5 % el 17-ago-2026** por decisión de Dirección + SRE, cerrando [`ESC-001`](../docs/escalaciones/ESC-001-sla-sobre-nodo-unico.md) / `PA-30`. La infraestructura de [`ADR-023`](../docs/adr/ADR-023-despliegue-sobre-vps-con-docker-compose.md) —un VPS único sin redundancia— no sostiene 43 minutos de caída al mes. **También se retiró la promesa de recuperación en región alternativa**, que directamente no existía.
>
> **Consecuencia comercial asumida**: Enterprise y Pro tienen ahora **el mismo SLA**, así que la disponibilidad deja de ser diferencial de Enterprise. Se diferencia por lo que sí se puede cumplir: usuarios y stock ilimitados, multi-sucursal, SSO, API completa, CSM dedicado, soporte 24/7 para críticos y 24 meses de auditoría. Los créditos por incumplimiento **no** cambian (5 / 10 / 25 %).
>
> Se sube de nuevo cuando haya segundo nodo y réplica, no antes. Ver el detalle en [`13_observabilidad_y_sre.md`](13_observabilidad_y_sre.md) §SLAs públicos por plan.

- Excedente de WhatsApp: **USD 0,012 por mensaje**.
- **Trial: 14 días**, con todas las features de Pro, **sin tarjeta**. Los datos de un trial no convertido se eliminan a los 30 días, con aviso previo.

## Versión B — `mejoras-y-saas.md` §10

| Plan | Precio mensual | Usuarios | Vehículos en stock | Target |
|---|---|---|---|---|
| **Starter** | **ARS 45.000** | Hasta 2 | Hasta 30 | Agencias chicas, hasta 2 vendedores |
| **Pro** | **ARS 95.000** | Hasta 6 | Hasta 100 | Agencias medianas, multi-vendedor |
| **Enterprise** | **ARS 195.000** | **Ilimitados** | **Ilimitados** | Concesionarios y multi-sucursal |

- **Starter** incluye: stock, CRM básico, mensajería con WhatsApp limitada a un número, reportes esenciales.
- **Pro** suma: permutas, financiación integrada con hasta 2 financieras, mensajería multi-canal, reportes avanzados.
- **Enterprise**: todos los módulos sin limitaciones, multi-sucursal, integración con sistemas contables externos, CSM dedicado, acceso anticipado a nuevas funcionalidades.
- Sobre cualquier plan: financieras adicionales por tarifa mensual de integración activa, más **comisión sobre las operaciones de crédito originadas**.
- **Trial: 30 días** con onboarding asistido.

### Descuentos declarados por cada versión

| Descuento | `plan-gtm` | `mejoras-y-saas` |
|---|---|---|
| Pago anual anticipado | 15 % | 50 % los primeros 3 meses con contrato anual |
| Compromiso bianual | 20 % | — |
| Early adopter | 30 % los primeros 12 meses (rampa: 15 % año 2, 0 % año 3+) | — |
| Base instalada del portal | — | **20 % permanente durante el primer año** |
| Convenio sectorial | 10 % | — |
| Referido | 1 mes gratis para ambas partes | — |
| Volumen multi-sucursal | Negociable | — |
| Excepcional | Hasta 25 %, caso a caso | — |

**Servicios adicionales** (`plan-gtm`): setup fee sin costo por defecto · migración de datos gratis vía CSV estándar, **USD 200-800** si requiere desarrollo · capacitación in-situ **USD 300/jornada**.

---

## Segmento objetivo (ICP)

⚠️ **El GTM y el Brand Book describen agencias distintas** — ver `IN-36`.

| Dimensión | `plan-gtm` §2.1 | `brand-book` §2 |
|---|---|---|
| Vendedores activos | **3 a 15** | **1 a 4** |
| Stock de vehículos | **40 a 300** | **20 a 200** |
| Ingresos comerciales | $30M-$300M ARS/mes | — |
| Geografía | Ciudades > 100.000 habitantes | Argentina, agencia "mediana o chica" |

**Universo total del mercado**: ~5.000 agencias en Argentina (GTM). La base instalada del portal deRuedas es de ~550 agencias.

### Sub-segmentos (GTM §2.2)

1. **Agencia tradicional digitalizándose** — 3-6 vendedores.
2. **Agencia mediana que ya usa un CRM genérico** — 5-10 vendedores.
3. **Mini-red en crecimiento** — 8-15 vendedores, 2-3 sucursales.

### Buyer personas

| Persona | Perfil | Rol en la decisión |
|---|---|---|
| **Eduardo** | Dueño, 45-58 años | **Decisor final** |
| **Marcos** | Gerente comercial de mini-red, 35-48 años | Influenciador técnico-operativo |
| **Carla** | Vendedora, 25-50 años | **Veto de facto** — si no lo adopta, el producto falla |
| **Ana** | Administrativa contable, 30-55 años | Usuaria de reportes y documentación |

> El reconocimiento explícito de que la vendedora tiene "veto de facto" es coherente con el Principio 2 de la constitución (simplicidad antes que features): el producto se pierde en el piso de venta, no en la reunión con el dueño.

---

## Unit economics y metas comerciales

| Métrica | Objetivo (`plan-gtm`) |
|---|---|
| CAC | USD 250-600 |
| Payback de CAC | < 6 meses (Pro), < 12 meses (Enterprise) |
| LTV | ≥ USD 4.500 |
| **Ratio LTV/CAC** | **≥ 7** ⚠️ `mejoras-y-saas` fija la meta en > 3,5 |
| Churn mensual | < 3 % ✅ coincide en ambos |
| Margen bruto plan Pro | 75 % |
| Costo cloud por tenant | USD 12/mes |
| Costo de WhatsApp por tenant Pro | USD 18/mes |
| Costo de soporte por tenant | USD 8/mes |
| NPS | > 40 (MVP), > 50 (madurez) ⚠️ `mejoras-y-saas` dice > 45 |
| Win rate | > 25 % |
| Pipeline coverage | 3× el objetivo mensual |
| NRR | > 100 % |

### Metas de `mejoras-y-saas` (en ARS, a 24 meses)

Cuentas activas 220 · Tasa de activación 65 % · DAU/MAU 55 % · ARPU ARS 140.000 · MRR ARS 30 millones · Operaciones financiadas > 300/mes · Tiempo de soporte < 8 h hábiles.

### Proyección financiera (`mejoras-y-saas` §14, escenario base, ARS millones)

| | Año 1 | Año 2 | Año 3 |
|---|---:|---:|---:|
| Cuentas activas (cierre) | 55 | 150 | 260 |
| MRR final del año | 5,5 | 18 | 36 |
| Ingresos anuales SaaS | 30 | 140 | 320 |
| Comisiones de financiación | 0 | 45 | 120 |
| **Ingresos totales** | 30 | 185 | 440 |
| Costos operativos | 180 | 260 | 340 |
| **Resultado operativo** | **(150)** | **(75)** | **100** |

Punto de equilibrio operativo en el **año 3**. Inversión acumulada ~**ARS 225 millones** en términos reales.
Escenario optimista: 360 clientes al cierre del año 3, con resultado positivo desde el 2° semestre del año 2.
Escenario pesimista: 180 clientes al cierre del año 3, aún negativo — requeriría una segunda ronda o ajuste del plan.

⚠️ Estas cifras y las del `plan-gtm` (Ola 3 = 200+ tenants, MRR USD 35.000-60.000) **no son convertibles entre sí** sin fijar un tipo de cambio. Ver `IN-42`.

---

## Funnel comercial (`plan-gtm` §6)

| Etapa | Conversión | Ejemplo sobre 1.000 |
|---|---:|---:|
| Awareness → Interest | 5 % | 50 |
| Interest → Evaluation | 30 % | 15 |
| Evaluation → Trial | 60 % | 9 |
| Trial → Decision | 40 % | 4 |
| Decision → Onboarding | 90 % | 3,6 |
| Onboarding → Retención a 6 m | 80 % | **2,9** |
| Retención → Referral | 30 % | — |

**Conversión total del funnel: ~0,3 %.**

Ciclo de venta: **3-6 semanas** para Pro, **8-12 semanas** para Enterprise. Demo estructurada de **45 minutos**. Propuesta comercial válida 30 días.
Touchpoints durante el trial de 14 días: días **3, 7 y 12**.

---

## Programa de early adopters

⚠️ **Cuatro tamaños distintos declarados** — ver `IN-41`.

| Fuente | Tamaño |
|---|---|
| `mejoras-y-saas` Fase 0 | 10 a 15 agencias |
| `mejoras-y-saas` §12 (Programa Pionero) | 15 agencias |
| `plan-gtm` §4 | 10 a 12 tenants; hito de Ola 1: **12 firmados** |
| `spec-tecnica` §9.4 (rollout de feature flags) | **5 a 10 tenants** ← este gobierna el despliegue técnico |

Condiciones (`plan-gtm`): duración **6 meses** · elegibilidad Pro o Enterprise · período de aceptación de candidaturas 90 días o hasta completar cupos · descuento **30 %** los primeros 12 meses · objetivo de retención al cierre **≥ 75 %** · NPS objetivo **≥ 50**.

Contrapartida esperada: testimonios, casos de éxito documentados y disponibilidad para visitas de prospects.

---

## Fases de lanzamiento comercial

| Ola | Ventana | Metas |
|---|---|---|
| **Ola 0** | — | 3 planes definidos · programa de early adopters formalizado · web con landing, pricing y FAQ · el founder como único comercial |
| **Ola 1** | 0-6 meses | **12 early adopters** firmados y en producción · 3 casos de éxito · CAC inicial medido · primer evento ACARA · programa de referidos activo · ≥ 2 artículos de blog/mes |
| **Ola 2** | 6-12 meses | **50-80 tenants activos** · MRR **USD 8.000-15.000** · equipo AE + SDR + CSM · ≥ 3 canales activos · primer cliente Enterprise multi-sucursal |
| **Ola 3** | 12-24 meses | **200+ tenants activos** · MRR **USD 35.000-60.000** · equipo de 6-8 personas · partnerships ≥ 3 generando > 15 % de los leads · expansion revenue > 25 % del nuevo MRR · primera expansión geográfica (Uruguay, Chile o México) |

La estrategia de `mejoras-y-saas` §12 describe en cambio **4 etapas**: Programa Pionero (15 agencias) → lanzamiento controlado a la base instalada (meta 90-120 clientes al cierre del primer año) → expansión geográfica fuera de la base (año 2) → alianzas estratégicas.

---

## Canales

- **Outbound directo** sobre la base instalada de 550 agencias del portal (la ventaja estructural declarada).
- **Inbound** web + contenidos. SEO sobre búsquedas como *"sistema para agencia de autos"*, *"gestión de concesionaria de usados"*.
- **Eventos sectoriales** — **ACARA**, **CADAM**, cámaras provinciales. Conversión awareness→interest **10-15 %**. Stand: USD 3.000-8.000.
- **Referidos** — 1 mes gratis para ambas partes.
- **Partnerships sectoriales** — terminales automotrices, bancos con cartera prendaria, proveedores de sistemas contables y de pago.
- **Publicidad pagada** — Meta y Google Ads, presupuesto inicial USD 500-1.000/mes.

## Equipo comercial y compensación

| Rol | Base / Variable |
|---|---|
| Account Executive (AE) | 60 / 40 |
| SDR / Inside Sales | 70 / 30 |
| Customer Success Manager (CSM) | 80 / 20 |
| Marketing | 90 / 10 |

Un AE por debajo del 50 % de su cuota durante 2 trimestres dispara una revisión de fit.

## Onboarding y adopción

**Hitos de adopción de un tenant nuevo**: día 3 configuración completa · día 7 WhatsApp conectado + primer vehículo cargado · día 14 primer lead + segundo usuario activo · día 30 primera operación cerrada · día 60 uso productivo con ≥ 5 leads activos.

**Indicadores de adopción saludable** (manual de usuario §11.7): login ≥ 4 días por semana en el segundo mes · notas actualizadas en > 80 % de los leads activos de los últimos 7 días · > 70 % de las conversaciones de WhatsApp asociadas a contacto o lead · dashboard revisado ≥ 3 veces por semana por el manager.

**QBR con el CSM**: trimestral. Preparación de renovación: 60 días antes.

## Cobranza y morosidad (`plan-gtm` §3.9)

| Día | Acción |
|---|---|
| 1 | Factura / cargo |
| 5 | Recordatorio |
| 10 | Segundo intento de cobro |
| 15 | Aviso de suspensión |
| 20 | **Suspensión** (modo solo lectura) |
| 60 | **Cancelación** + eliminación programada a 30 días |

⚠️ La constitución (Artículo 6) dice que los datos se conservan **90 días** tras la cancelación. Ver `IN-18`.

## Competencia

**Battle cards documentadas**: **HubSpot CRM** · **Pipedrive** (precio de entrada USD 19) · **"desarrollo a medida"** (Excel + el sobrino programador).
**Salesforce** se menciona solo como categoría de CRM generalista internacional, sin battle card.

Del análisis estratégico de `mejoras-y-saas`, en el mercado del portal (no del SaaS): MercadoLibre Vehículos (~210.000 publicaciones, ~3M visitas diarias al rubro, comisión 5-7 %) · Kavak y OLX Autos (transaccionales, margen 5-15 %) · Autocosmos (clasificados + contenido editorial) · Marketplace de Facebook · MarketplaceMotor y Heiwork (freemium agresivo).

**Diferenciación declarada frente a los CRM genéricos**: verticalidad. Incorpora el lenguaje, los flujos y las particularidades regulatorias del rubro automotor argentino, lo que acorta la curva de adopción y sube la productividad inicial.

## Riesgos comerciales y mitigaciones (`mejoras-y-saas` §13)

| Riesgo | Mitigación declarada |
|---|---|
| **Adopción lenta** (agencias tradicionales, gerentes acostumbrados a Excel) | Onboarding presencial gratuito en la primera fase, capacitación dedicada, simplificación radical del MVP, incentivos económicos para los primeros adoptantes |
| **Competencia genérica** (HubSpot, Pipedrive, Zoho a bajo costo) | Profundizar la verticalización, integraciones únicas con el portal y las financieras, precio competitivo + onboarding superior |
| **Cambio regulatorio** (AFIP, DNRPA, normativa provincial) | Arquitectura modular que aísla la lógica regulatoria, monitoreo activo, relaciones con cámaras del sector |
| **Costos de infraestructura** | Compresión y tiering de almacenamiento, uso eficiente de CDN, revisión trimestral de costo por tenant |
| **Dependencia de WhatsApp** (políticas de Meta) | Diseño multi-canal desde el inicio (SMS, email), contratos directos con Meta, monitoreo de alternativas |
| **Talento técnico** | Equity o bonos diferidos, cultura técnica, modalidad remota, alianzas con universidades (**UNSL**, **UTN-FRM**) |
| **Macro Argentina** (inflación, devaluación) | **Pricing en pesos con actualización trimestral por CER o IPC** ⚠️ contradice el pricing en USD del GTM — `IN-04` · diversificación geográfica · contratos de mediano plazo con descuento |
| **Disrupción por IA** | Arquitectura abierta a integraciones de modelos, equipo de innovación desde la fase 4, alianzas académicas |
