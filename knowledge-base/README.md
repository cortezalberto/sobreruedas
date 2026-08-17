# deRuedas Gestión — Base de Conocimiento

Base de conocimiento generada por ingesta silenciosa de los **11 documentos fuente** del proyecto (`docs/sdd/`, ~19.900 líneas), leídos íntegramente.

**Todo lo que está acá está derivado de las fuentes.** Nada fue inventado: lo que no se pudo derivar quedó registrado como pregunta abierta en [10_preguntas_abiertas.md](10_preguntas_abiertas.md).

---

## ⚠️ Leé esto antes de escribir una línea de código

El chequeo de consistencia cruzada detectó **54 inconsistencias reales entre documentos, 14 de ellas bloqueantes**. No son detalles de redacción: hay contradicciones sobre el catálogo de roles, la moneda de facturación, los límites de los planes, la retención de auditoría, el umbral de cobertura del CI y el SLA contractual.

**Empezá por [10_preguntas_abiertas.md](10_preguntas_abiertas.md).** Hasta resolver `PA-01` a `PA-05`, la migración inicial y el quality gate del CI no se pueden escribir de forma defendible.

---

## Índice de archivos

| Archivo | Contenido |
|---|---|
| [01_vision_y_objetivos.md](01_vision_y_objetivos.md) | Propósito, contexto estratégico, objetivos por actor, alcance del producto y del MVP, fuera de alcance, métricas de éxito |
| [02_descripcion_general.md](02_descripcion_general.md) | Stack tecnológico completo, arquitectura general, 16 módulos, comunicación inter-módulo, multi-tenancy, integraciones externas, convenciones y catálogo de endpoints de la API |
| [03_actores_y_roles.md](03_actores_y_roles.md) | Actores del sistema, catálogo de roles (`ADR-017`), forma de la matriz RBAC (canónica en `ADR-024`), mecanismos de autorización, rutas públicas |
| [04_modelo_de_datos.md](04_modelo_de_datos.md) | Convenciones, ERD, 10 dominios, ~35 entidades con campos/constraints/índices, máquinas de estado, vistas materializadas, seed data, validadores argentinos |
| [05_reglas_de_negocio.md](05_reglas_de_negocio.md) | ~130 reglas codificadas `RN-{DOMINIO}-{NN}` en 12 dominios, más los trade-offs ya resueltos por constitución |
| [06_funcionalidades.md](06_funcionalidades.md) | 12 épicas y 92 historias de usuario con prioridad MoSCoW, estimación Fibonacci y fase; Definition of Done |
| [07_flujos_principales.md](07_flujos_principales.md) | 13 flujos extremo a extremo: auth, onboarding, alta y publicación de vehículo, importación, ciclo del lead, WhatsApp, permuta, financiación, cierre de operación, documentos, cuenta corriente, derechos del titular, deploy |
| [08_arquitectura_propuesta.md](08_arquitectura_propuesta.md) | Patrones aplicados, estructura de directorios, regla de frontera entre módulos, seguridad, observabilidad, infraestructura, variables de entorno, estrategia de escalado |
| [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md) | 7 principios constitucionales, 12 ADRs con alternativas y trade-offs, 5 trade-offs resueltos, **12 supuestos inferidos** con su forma de validación |
| [10_preguntas_abiertas.md](10_preguntas_abiertas.md) | **54 inconsistencias cruzadas** (14 bloqueantes) + 30 preguntas abiertas priorizadas con decisor asignado |
| **Extras** | |
| [11_testing_y_calidad.md](11_testing_y_calidad.md) | Pirámide, umbrales de cobertura, herramientas por nivel, tests de aislamiento multi-tenant, datos sintéticos, quality gates, gestión de flakiness |
| [12_seguridad_y_compliance.md](12_seguridad_y_compliance.md) | STRIDE, autenticación, autorización, aislamiento, cifrado, Ley 25.326, retenciones, auditoría, SSDLC, respuesta a incidentes |
| [13_observabilidad_y_sre.md](13_observabilidad_y_sre.md) | SLA/SLO, presupuesto de error, stack de observabilidad, catálogo de 18 alertas, runbooks, on-call, RTO/RPO, capacidad, deploy y rollback |
| [14_pricing_y_gtm.md](14_pricing_y_gtm.md) | Los **dos** modelos de pricing incompatibles, ICP, unit economics, funnel, early adopters, canales, cobranza, competencia, riesgos |
| [15_marca_y_ux.md](15_marca_y_ux.md) | Identidad, paleta, tipografía, logo, componentes UI, tono de voz y vocabulario controlado, accesibilidad, localización, navegación |

## Quick start para desarrolladores

1. **Entender qué se construye y para quién** → [01](01_vision_y_objetivos.md) y [03](03_actores_y_roles.md)
2. **Entender los datos** → [04](04_modelo_de_datos.md)
3. **Entender las reglas** → [05](05_reglas_de_negocio.md)
4. **Entender la arquitectura** → [02](02_descripcion_general.md) y [08](08_arquitectura_propuesta.md)
5. **Entender cómo se ejecuta** → [07](07_flujos_principales.md) y [06](06_funcionalidades.md)
6. **Entender qué se te exige** → [11](11_testing_y_calidad.md) y [12](12_seguridad_y_compliance.md)
7. **⚠️ Antes de codificar** → [10](10_preguntas_abiertas.md)

### Si vas a operar el sistema
[13](13_observabilidad_y_sre.md) → [12](12_seguridad_y_compliance.md) → [08](08_arquitectura_propuesta.md)

### Si vas a construir interfaz
[15](15_marca_y_ux.md) → [06](06_funcionalidades.md) → [07](07_flujos_principales.md)

### Si vas a vender o hacer onboarding
[14](14_pricing_y_gtm.md) → [01](01_vision_y_objetivos.md) → [06](06_funcionalidades.md)

## Resumen ejecutivo

**deRuedas Gestión** es un SaaS vertical multi-tenant para agencias de vehículos del mercado argentino, construido sobre **Python 3.12 + FastAPI + PostgreSQL 16 (con RLS) + Redis 7 + Celery + OpenSearch**, con frontend en **Next.js 14** y app móvil en **React Native**, e identidad delegada a **Keycloak** (OAuth2/OIDC). Su arquitectura es un **monolito modular de 16 módulos** que se comunican por eventos de dominio en Redis Streams, con aislamiento entre tenants garantizado por tres capas simultáneas: `tenant_id` en toda query, políticas RLS de PostgreSQL y tests de aislamiento bloqueantes en CI.

Funcionalmente cubre el ciclo completo de una agencia —stock, publicación al portal, CRM con pipeline, WhatsApp Business, permutas, financiación, documentación, cuenta corriente y BI— organizado en 12 épicas y 92 historias, de las cuales las épicas E1 a E5 constituyen el MVP.

Estratégicamente, el producto no es una herramienta más del catálogo de deRuedas: es la apuesta para transformar un portal de clasificados con monetización lineal por aviso —bajo presión de MercadoLibre, Kavak y Marketplace de Facebook— en una plataforma con **lock-in por datos**, aprovechando la relación existente con ~550 agencias del interior argentino. El producto compite contra Excel, cuadernos y WhatsApp, no contra CRMs enterprise, y eso condiciona cada decisión de diseño: simplicidad antes que features, verticalidad antes que generalidad.

---

## Fuentes

Todas fechadas *"Versión 1.0 — Mayo de 2026"*:

| Documento | Líneas | Rol en la KB |
|---|---:|---|
| `deRuedas-constitucion.md` | 231 | **Norma vinculante** — principios, reglas, trade-offs, glosario canónico |
| `deRuedas-spec-tecnica.md` | 1.748 | **Fuente técnica primaria** — arquitectura, modelo de datos, API, 12 ADRs, NFRs |
| `deRuedas-plan-implementacion.md` | 8.827 | 194 tareas atómicas del MVP con DDL, contratos y criterios de aceptación |
| `deRuedas-historias-usuario.md` | 1.376 | 12 épicas, 92 HU con Gherkin, MoSCoW y estimación |
| `deRuedas-manual-usuario.md` | 1.086 | Comportamiento observable del producto de cara al cliente |
| `deRuedas-plan-seguridad.md` | 1.820 | STRIDE, compliance Ley 25.326, SSDLC, respuesta a incidentes |
| `deRuedas-plan-sre.md` | 1.223 | SLA/SLO, observabilidad, alertas, runbooks, DR, capacidad |
| `deRuedas-plan-testing.md` | 1.128 | Pirámide, cobertura, herramientas, quality gates |
| `deRuedas-plan-gtm.md` | 1.130 | Pricing, ICP, funnel, canales, unit economics |
| `deRuedas-mejoras-y-saas.md` | 366 | Contexto estratégico, 9 iniciativas, fases, pricing (versión alternativa) |
| `deRuedas-brand-book.md` | 965 | Identidad, paleta, tipografía, tono de voz, accesibilidad |

**No ingeridos como verdad del producto**: `reference/justificacion.md` y `reference/manual-sdd.md` describen el *método* SDD, no el producto.

---

*Generada por `kb-creator` en Mode A (ingesta silenciosa). Rioplatense.*
