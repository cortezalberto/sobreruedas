# Flujos Principales

> Fuentes: `deRuedas-manual-usuario.md` (comportamiento observable), `deRuedas-historias-usuario.md` (criterios de aceptación), `deRuedas-spec-tecnica.md` y `deRuedas-plan-implementacion.md` (mecánica interna).

---

## Flujo 1 — Autenticación y sesión

**Disparador**: el usuario abre la aplicación.
**Actor**: cualquier usuario del tenant.

**Pasos**:
1. Frontend (Next.js con NextAuth como cliente OIDC) redirige a **Keycloak** (realm `deruedas`).
2. Keycloak autentica (email + password, argon2id) y, si corresponde, solicita el segundo factor TOTP.
3. Keycloak emite un **JWT RS256** (access, 15 min) + refresh token (7 días, rotativo, ligado a la huella del dispositivo).
4. El frontend guarda los tokens y llama a la API con `Authorization: Bearer <JWT>`.
5. El backend valida la firma, extrae el claim `tenant_id` y ejecuta `SET LOCAL app.current_tenant = '<uuid>'` sobre la conexión.
6. Todas las queries de la request quedan automáticamente filtradas por RLS.

```
Usuario → Frontend → Keycloak (OIDC) → JWT
             │
             └─► API Backend ──[extrae tenant_id del claim]──► SET LOCAL app.current_tenant
                        │
                        └─► PostgreSQL (RLS política tenant_isolation) ──► filas del tenant
```

**Casos de error**:
- Token sin firma válida / expirado / con `role` manipulado → **401**.
- Token con `tenant_id` de otro tenant → **403 / 404** (no se filtra la existencia del recurso).
- Refresh token reutilizado después de la rotación → **401** (indicio de robo de token).
- Sin `app.current_tenant` seteado → RLS devuelve 0 filas (falla visible).
- 5 intentos fallidos → 5 min de bloqueo; 10 → 30 min; 20 → 24 h + aviso al usuario.

---

## Flujo 2 — Onboarding de una agencia nueva

**Disparador**: se firma un contrato; el equipo de Customer Success da de alta el tenant desde el backoffice.
**Actor**: `super_admin` (alta) → `manager` de la agencia (configuración).
**Tiempo declarado**: 30-90 minutos según tamaño de la agencia.

**Pasos**:
1. `super_admin` crea el tenant vía `POST /admin/api/v1/tenants` (CUIT, razón social, plan, email del responsable). ⚠️ En el MVP **no hay signup público** — ver `IN-14`.
2. Se envía invitación al `manager`. Caduca a los **7 días**.
3. **Activación de cuenta**: el manager define contraseña (mín. 12 caracteres), configura MFA, completa sus datos y acepta los términos.
4. **Wizard de configuración de la agencia** (5 datos): nombre comercial · razón social + CUIT · dirección de la sucursal principal · teléfono y email comercial · logo (PNG/JPG cuadrado, ≥ 400×400 px).
   ⚠️ Las historias describen el wizard con 4 pasos (datos de la agencia / sucursales / usuarios / integraciones). Ver `IN-26`.
5. **Alta de usuarios del equipo**: nombre, email, rol, sucursal asignada.
6. **Definición del pipeline**: se aceptan las etapas por defecto o se personalizan. ⚠️ Cantidad por defecto en disputa (`IN-10`).
7. **Sucursales** (solo Pro/Enterprise; Starter queda con una).
8. **Conexión de WhatsApp Business**: se vincula el número a la Cloud API de Meta. Nota crítica: el número **no puede seguir usándose en la app de celular**.
9. **Conexión con el portal deRuedas**: habilita la publicación automática.
10. **Carga inicial de inventario**: manual (hasta ~30 vehículos), por planilla CSV, o migración asistida (incluida en Pro/Enterprise; cotizada aparte en Starter).
11. `POST /api/v1/tenant/me/complete-onboarding` marca el onboarding como terminado.

**Casos de error**:
- CUIT ya existente en otro tenant → rechazo.
- Plan Starter intentando crear una segunda sucursal → **422** con oferta de upgrade.
- Exceder `max_users` del plan → **422**.

---

## Flujo 3 — Alta de vehículo y publicación automática

**Disparador**: ingresa un vehículo al stock de la agencia.
**Actor**: `manager`, `admin_staff`, o `salesperson` desde el celular.

**Pasos**:
1. `POST /api/v1/vehicles` con los datos básicos. Validaciones: dominio con formato AR y único por tenant; año 1950–actual+1; kilometraje ≥ 0; precio > 0.
2. El vehículo se crea en estado **`in_preparation`**.
3. `POST /api/v1/vehicles/{id}/photos` — subida (máx. 10 MB por foto, mín. 800×600, hasta 10 archivos por request). Un worker Celery genera las variantes `thumb` 200×150, `medium` 800×600 y `original`.
4. Se completa descripción, equipamiento (`features` jsonb) y, opcionalmente, precio de costo (visible solo para `manager` / `admin_staff`).
5. `POST /api/v1/vehicles/{id}/status` → `available`.
6. Se publica el evento de dominio **`vehicle.created`** / **`vehicle.status_changed`** en Redis Streams.
7. El módulo `publishing` consume el evento y sincroniza con el portal deRuedas, creando una fila en `vehicle_publications` con estado `pending` → `published`.

```
Usuario → API ──► PostgreSQL (vehicles)
            │
            ├──► Redis Streams: vehicle.created
            │            │
            │            ▼
            │      Worker Celery (publishing)
            │            │
            │            └──► Portal deRuedas API ──► vehicle_publications.status = published
            │
            └──► Worker Celery (imágenes) ──► S3 (thumb/medium/original) ──► CDN
```

**Tiempos observables**: sincronización inicial completa 15 min – 2 h; un vehículo nuevo aparece en el portal en **5-15 minutos**; un cambio de precio, "en pocos minutos".

**Casos de error**:
- Vehículo sin fotos o sin precio → `cannot_publish_incomplete`, **sin reintento**.
- Falla transitoria del portal → reintento con backoff (5 intentos, base 60 s, factor 2, tope 30 min); tras agotarse, va a **DLQ** y dispara alerta.
- Dominio duplicado → rechazo con opción de abrir el vehículo existente.
- Alerta operativa: tasa de éxito de publicación < 95 % en 30 min → warning; DLQ > 10 → critical.

---

## Flujo 4 — Importación masiva de stock (CSV)

**Disparador**: la agencia migra su Excel al sistema.
**Actor**: `manager` o `admin_staff`.

**Pasos**:
1. Descarga de plantilla: `GET /api/v1/vehicles/import/template`.
2. `POST /api/v1/vehicles/import` con el CSV (máx. **10 MB**, máx. **5.000 filas**).
3. Se crea una fila en `imports` con estado `pending`.
4. Worker Celery: `parsing` → `validating` (vista previa de los primeros 10 vehículos detectados) → `importing` en batches de **100 con commit por batch** → `completed` o `failed`.
5. El frontend hace polling del progreso cada **2 segundos** contra `GET /api/v1/imports/{id}`.
6. Los errores por fila quedan en `imports.errors` (jsonb) para corrección y reintento.

**Objetivo de performance**: 1.000 vehículos importados en **< 2 minutos**.
**Limitación conocida**: las **fotos no se importan** por planilla; hay que asociarlas manualmente después.

---

## Flujo 5 — Ciclo de vida de un lead (el flujo comercial central)

**Disparador**: llega una consulta de un comprador.
**Actor**: `salesperson` (operación), `manager` (supervisión y reasignación).

**Pasos**:
1. **Captura**. Tres vías:
   - Automática desde el portal deRuedas u otro portal integrado (webhook entrante).
   - Automática desde un mensaje entrante de WhatsApp (crea o reutiliza el contacto por teléfono).
   - Manual: `POST /api/v1/leads` (contacto, vehículo de interés, valor estimado, notas, etapa inicial).
2. **Desduplicación de contacto**: se busca por teléfono normalizado a E.164 (o por documento). Si existe, se reutiliza; no se crean contactos duplicados.
3. **Asignación**: por reglas de asignación automática (round-robin, por sucursal, por disponibilidad) o manual. El lead entra en la etapa marcada `is_initial`.
4. **Trabajo del lead**: el vendedor contacta, registra actividades (`call`, `whatsapp`, `test_drive`, `quote`, `meeting`, `note`), agenda visitas, mueve el lead de etapa. Cada movimiento registra usuario, fecha y motivo en `lead_stage_history`.
5. **Recordatorios automáticos**: un cron diario detecta leads sin actividad más allá del umbral y notifica al vendedor. ⚠️ Umbral en disputa (`IN-20`).
6. **Cierre**:
   - **Ganado** → `POST /api/v1/leads/{id}/won` (o `/close` según la fuente — ver `IN-12`). Se registra vehículo vendido, monto final, forma de pago (contado / financiado / parte de pago + saldo), fecha estimada de entrega y observaciones. **Dispara automáticamente** el pase del vehículo a `sold` y su despublicación del portal.
   - **Perdido** → `POST /api/v1/leads/{id}/lost` con `loss_reason_id` **obligatorio**.
7. Un lead perdido puede reabrirse (comportamiento del manual, no reflejado en las historias).

```
Portal / WhatsApp / Manual
          │
          ▼
   [desduplicación por teléfono]
          │
          ▼
    contacts ──► leads (etapa is_initial, assigned_user_id)
          │
          ├─► lead_activities (call, whatsapp, test_drive…)
          ├─► lead_stage_history (cada movimiento)
          │
          ├─► WON  ──► evento lead.closed ──► vehicles.status = sold ──► despublicar
          └─► LOST ──► loss_reason_id obligatorio
```

**Casos de error**:
- Cerrar como perdido sin motivo → **422**.
- Un `salesperson` intentando ver un lead que no le pertenece → **403 / 404**.
- Un `salesperson` intentando reasignar → **403** (solo `manager`).
- Cerrar como ganado un vehículo ya vendido por otro lead → se registra warning; no se revierte el estado.

---

## Flujo 6 — Conversación de WhatsApp

**Disparador**: entra un mensaje del comprador, o el vendedor inicia contacto.
**Actor**: `salesperson` (asignado), `manager` / `admin_staff` (ven todas).

**Entrante**:
1. Meta envía `POST /webhooks/whatsapp` → validación **HMAC** → se persiste para idempotencia → respuesta **200 OK en < 300 ms**.
2. Worker asincrónico: busca o crea el `contact` por teléfono; busca o crea la `conversation` abierta para ese `(channel, contact)`; inserta el `message` con `direction = inbound`.
3. Actualiza `conversations.last_inbound_at` (crítico: **reinicia la ventana de 24 h**) y `unread_count`.
4. Si no existe lead asociado, se crea o se sugiere crearlo.
5. Se publica en **Redis Pub/Sub** y se empuja al frontend por el canal en tiempo real `GET /api/v1/conversations/stream` (⚠️ SSE en el plan de implementación, WebSocket en `mejoras-y-saas` — ver `IN-08`). Heartbeat cada 30 s.
6. **Objetivo**: el mensaje visible en pantalla en **< 1 segundo**.

**Saliente**:
1. El vendedor escribe en la bandeja unificada.
2. **Chequeo de la ventana de 24 h**: si pasaron más de 24 h desde `last_inbound_at`, se rechaza el texto libre con error `use_template` y se ofrecen los templates aprobados.
3. `POST /api/v1/conversations/{id}/messages` → mensaje en estado `pending` → worker lo envía a la Cloud API → `sent` → webhook de Meta actualiza a `delivered` → `read`.
4. Imágenes > 1 MB se comprimen antes de enviar. Límites: audio < 16 MB, imagen < 5 MB.

**Casos de error**:
- Fuera de la ventana de 24 h con texto libre → `use_template`.
- Template no aprobado por Meta → rechazo (la aprobación tarda 24-48 h).
- Mensaje atascado en `queued` > 1 hora → timeout.
- Alertas: tasa de error de envío > 5 % en 30 min; p95 del webhook > 1 s; circuit breaker de WhatsApp abierto > 10 min (P2, runbook RB-012).

---

## Flujo 7 — Permuta (Fase 3)

**Disparador**: el comprador ofrece su usado como parte de pago.
**Actor**: `salesperson` inicia; `manager` aprueba el valor; inspector realiza la inspección.

**Pasos**:
1. `POST /api/v1/swaps` desde el lead — datos del usado a recibir (marca, modelo, año, kilometraje, dominio). Estado: `requested`.
2. `POST /api/v1/swaps/{id}/valuations` — valuación con apoyo de la base de mercado (`deruedas_index`) o manual. Devuelve rango min/mid/max y un valor propuesto. Estado: `valuated`. Puede haber varias iteraciones.
3. `POST /api/v1/swaps/{id}/inspections` — inspección de **100 puntos**: scores 0-100 de mecánica, electricidad y carrocería, kilometraje verificado, daño estructural, historial de taxi/remis, fotos. Estado: `inspected`.
4. `POST /api/v1/swaps/{id}/proposal` — genera propuesta formal en PDF para el cliente.
5. El cliente acepta → estado `accepted`.
6. `POST /api/v1/swaps/{id}/close` → **alta automática del usado en `vehicles`** (estado `in_preparation`), con `resulting_vehicle_id` apuntando al nuevo registro. Trazabilidad bidireccional entre la venta original y el ingreso del usado. Se publica el evento `swap.closed`.

**Casos de error**: cliente rechaza la propuesta → estado `rejected`. Dominio del usado ya existente en el stock del tenant → conflicto de unicidad.

---

## Flujo 8 — Financiación (Fase 3)

**Disparador**: el comprador necesita crédito.
**Actor**: `salesperson`.

**Pasos**:
1. `POST /api/v1/credit/applications` con contacto, vehículo, monto, entrega y plazo. Estado `pre_qualifying`.
2. `POST /api/v1/credit/applications/{id}/pre-qualify` — consulta en paralelo a las financieras integradas y compatibles (según `max_ltv_pct`, `min_amount_ars`, `max_term_months`). **Debe responder en < 30 segundos.**
3. Se crean `credit_offers` con cuota, TNA, TEA, CFT y fecha de expiración.
4. `POST /api/v1/credit/applications/{id}/select-offer` — el cliente elige.
5. `POST /api/v1/credit/applications/{id}/submit` — solicitud formal con documentación (DNI, recibo de sueldo, comprobantes). Estado `submitted`.
6. La financiera responde por `POST /webhooks/finance/{partner}` → `approved` o `rejected`. El vendedor recibe notificación.
7. `POST /api/v1/credit/applications/{id}/sign` — firma electrónica. Estado `signed` → `disbursed`.
8. Se registra la comisión de originación para deRuedas (`origination_fee_pct`).

**Casos de error**: financiera caída → circuit breaker; la oferta expira → estado `expired`; precalificación negativa en todas las financieras → se informa al vendedor sin bloquear la operación en contado.

---

## Flujo 9 — Cierre de operación de venta

**Disparador**: se concreta la venta.
**Actor**: `salesperson` (marca ganado), `admin_staff` (documentación y cobranza).

**Pasos**:
1. Se cierra el lead como ganado (Flujo 5).
2. Se crea `sales_operations` vinculando vehículo, comprador, precio de venta y, si aplica, `swap_request_id` y `credit_application_id`.
3. El vehículo pasa a `sold` y se despublica de los portales.
4. `admin_staff` carga la documentación de la operación (Flujo 10) y registra los cobros.
5. Se imputan los `operation_costs` (taller, comisión interna, gastos de la financiera).
6. `POST /api/v1/operations/{id}/close` — cierre definitivo; se calcula el margen bruto.
7. Se publica el evento `operation.closed`, que alimenta los dashboards de BI.

**Condición de carrera conocida**: dos vendedores cerrando el mismo vehículo simultáneamente. Resolución: "el primero que marca como vendido, gana"; el segundo recibe `VehicleAlreadySoldError`.

---

## Flujo 10 — Gestión documental (Fase 4)

**Pasos**:
1. `POST /api/v1/documents` (multipart, máx. 50 MB), asociado a un vehículo, contacto u operación.
2. Worker Celery envía el archivo a **OCR** → el texto extraído se guarda en `documents.ocr_text` e indexa en OpenSearch.
3. Auto-clasificación del tipo de documento. Si el OCR falla, queda "por clasificar" para revisión manual.
4. Si el tipo tiene vencimiento (`document_types.has_expiration`), se registra `expires_at` y se programan alertas: **30 días** antes, y urgente cuando faltan **menos de 5 días**.
5. `POST /api/v1/operations/{id}/document-package` genera el paquete completo para presentar ante el registro automotor.
6. Opcional: `POST /api/v1/documents/{id}/sign` inicia la firma electrónica con el proveedor externo.

Acceso: siempre por **URL firmada** con TTL de 30 minutos.

---

## Flujo 11 — Cuenta corriente y conciliación (Fase 4)

**Pasos**:
1. `POST /api/v1/payments` — registro de cobro (monto, fecha, medio de pago, comprobante, cotización si es moneda extranjera), asociado a la operación y al contacto.
2. `GET /api/v1/contacts/{id}/account` — cuenta corriente del cliente (señas, saldos financiados directamente con la agencia).
3. `POST /api/v1/bank/import` — importación del extracto bancario a `bank_movements`.
4. `POST /api/v1/bank/reconcile` — asociación movimiento ↔ pago (`reconciled_payment_id`).
5. `GET /api/v1/payments/{id}/receipt` — comprobante en PDF.
6. `GET /api/v1/accounting/export?format=tango` — exportación a Tango, Bejerman o Excel.
7. La vista materializada `mv_outstanding_receivables` alimenta el dashboard financiero.

---

## Flujo 12 — Ejercicio de derechos del titular (Ley 25.326)

**Disparador**: un contacto ejerce su derecho de supresión ante la agencia.
**Actor**: `manager` o `admin_staff` del tenant (la agencia es el **responsable**; deRuedas es el **encargado**).

**Pasos**:
1. `POST /api/v1/contacts/{id}/forget`.
2. El nombre se reemplaza por un hash; se vacían teléfono y email.
3. Se eliminan los mensajes asociados.
4. Se registra la acción en `audit_logs` **sin PII**.
5. El contacto desaparece de exports y de los índices de búsqueda.

Runbook asociado: `docs/runbooks/data-subject-rights.md`.
Derechos cubiertos: acceso, rectificación y supresión. La exportación completa de los datos del tenant está disponible bajo demanda.

---

## Flujo 13 — Deploy a producción

**Disparador**: merge a `main`.

**Pasos (pipeline de 10 etapas)**:
1. Lint y formato (bloqueante).
2. Pruebas unitarias (backend + frontend) con umbral de cobertura.
3. Pruebas de integración con servicios efímeros (testcontainers: PostgreSQL, Redis, MinIO).
4. **SAST + SCA** — vulnerabilidades altas o críticas **bloquean**.
5. Build de imágenes Docker firmadas, etiquetadas con el hash del commit.
6. Deploy automático a **staging**.
7. Pruebas E2E en staging contra el deploy recién hecho.
8. **Aprobación humana** (manual gate).
9. Deploy **blue-green** en producción, con canary opcional (5 % → escalado gradual). ⚠️ El plan de SRE declara **rolling** como estrategia por defecto y blue-green solo para cambios de mayor riesgo, con canary 1 % → 5 % → 25 % → 50 % → 100 %. Ver `IN-27`.
10. Smoke tests post-deploy y monitoreo de métricas durante **15 minutos**; rollback automático si las métricas se desvían.

**Rollback**: switch al pool anterior, **< 1 minuto** con blue-green. ⚠️ La constitución exige "< 15 minutos" y el plan de SRE fija el objetivo en "< 30 minutos" — tres cifras distintas para el mismo compromiso. Ver `IN-28`.

**Feature flags**: toda funcionalidad nueva sale detrás de un flag por tenant. Activación progresiva: internos → early adopters (5-10 tenants) → olas de 25 %, 50 %, 100 %, con **mínimo 48 horas** por ola.

**Migraciones**: retro-compatibles con la versión anterior durante al menos un release. Las no retro-compatibles requieren ADR y plan documentado. Las que afectan más de 1 millón de filas corren en background con monitoreo de bloqueos. **Nunca se ejecutan automáticamente en producción sin aprobación humana.**
