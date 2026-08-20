# Modelo de Datos

> Fuente primaria: `deRuedas-spec-tecnica.md` §3 (vinculante). Complementado con `deRuedas-plan-implementacion.md` (DDL de detalle del MVP).
> Donde ambos discrepan, se marca ⚠️ y se registra en [10_preguntas_abiertas.md](10_preguntas_abiertas.md).

## Convenciones generales (aplican a toda tabla)

- **PK**: UUID **versión 7** (ordenables temporalmente → mejor performance de inserción en índices), tipo `uuid` nativo de PostgreSQL.
- **Nombres de tabla**: plural, inglés, `snake_case`. Excepción: entidades del dominio argentino sin traducción razonable mantienen el término en español (`sucursales`, `permutas`). ⚠️ En la práctica la spec usa `branches` y `swap_requests` — la excepción se enuncia pero no se ejerce.
- **Nombres de columna**: singular, inglés, `snake_case`. FKs con patrón `nombre_singular_id`.
- **`tenant_id uuid NOT NULL`** FK a `tenants(id)` en **toda tabla de negocio**, y parte de los índices más usados.
- **Timestamps**: `created_at`, `updated_at` (`timestamptz NOT NULL DEFAULT now()`) y `deleted_at timestamptz NULL` para soft-delete.
- **Soft delete universal**: nunca `DELETE` físico. Los índices `UNIQUE` llevan `WHERE deleted_at IS NULL`.
- **Enums**: `CREATE TYPE ... AS ENUM` cuando los valores son cerrados y estables; tabla de catálogo con FK cuando no.
- **Dinero**: `numeric(18,2)` + columna de moneda (`ARS`, `USD`).
- **Fechas**: `date` sin hora; `timestamptz` siempre con timezone.
- **RLS**: política `tenant_isolation` sobre `current_setting('app.current_tenant')` en toda tabla con `tenant_id`.

## Dominios (10)

`Auth y Tenancy` · `Stock` · `CRM` · `Communication` · `Trade-in (Permutas)` · `Finance` · `Documents` · `Accounting` · `Operations` · `Audit`

Las relaciones cruzadas entre dominios se hacen **siempre por identificador**, nunca por inclusión de tablas.

## ERD (textual)

```
tenants ──1:N── branches
   │             └──N:M── users  (via user_branches)
   ├──1:N── users
   ├──1:N── subscriptions ──N:1── plans
   ├──1:N── vehicles ──N:1── branches
   │            ├──N:1── vehicle_brands ──1:N── vehicle_models ──1:N── vehicle_versions
   │            ├──1:N── vehicle_photos
   │            ├──1:N── vehicle_status_history
   │            └──1:N── publishing_status
   ├──1:N── contacts ──1:N── leads
   ├──1:N── pipeline_stages ──1:N── leads
   ├──1:N── leads ──N:1── vehicles (vehículo de interés, nullable)
   │           ├──N:1── users (assigned_user_id)
   │           ├──N:1── loss_reasons
   │           ├──1:N── lead_activities
   │           ├──1:N── lead_stage_history
   │           └──N:M── tags (via lead_tags)
   ├──1:N── conversations ──N:1── contacts, leads(nullable)
   │            └──1:N── messages ──N:1── whatsapp_templates(nullable)
   ├──1:N── swap_requests ──N:1── leads
   │            ├──1:N── swap_valuations
   │            ├──1:N── swap_inspections
   │            └──1:1── vehicles (resulting_vehicle_id: el usado que ingresa a stock)
   ├──1:N── credit_applications ──N:1── contacts, leads(null), operations(null), vehicles(null)
   │            └──1:N── credit_offers ──N:1── financial_partners
   ├──1:N── documents ──N:1── document_types
   │            └──1:N── document_signatures
   ├──1:N── sales_operations ──1:1── vehicles
   │            ├──1:N── operation_costs
   │            └──1:N── payments
   ├──1:N── bank_movements ──0:1── payments (reconciled_payment_id)
   ├──1:N── notifications
   └──1:N── audit_logs   (tenant_id NULLABLE: acciones cross-tenant de super_admin)

Catálogos cross-tenant (sin tenant_id, sin RLS):
   plans · vehicle_brands · vehicle_models · vehicle_versions · document_types
   financial_partners · feature_flags
```

## Entidades

### Dominio Auth y Tenancy

#### `tenants`
Una agencia cliente. Unidad raíz de aislamiento de datos, configuración y facturación.

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | uuid | PK | |
| `name` | varchar(120) | NOT NULL | Razón social o nombre comercial |
| `slug` | varchar(60) | UNIQUE NOT NULL | Identificador URL-friendly global |
| `cuit` | varchar(13) | UNIQUE NOT NULL | Con guiones, validado por dígito verificador (`validate_cuit(text)`) |
| `billing_email` | varchar(254) | NOT NULL | |
| `status` | `tenant_status_enum` | NOT NULL | `active \| suspended \| trial \| cancelled` |
| `plan_id` | uuid | FK `plans(id)` | Plan vigente |
| `trial_ends_at` | timestamptz | NULL | |
| `timezone` | varchar(50) | DEFAULT `'America/Argentina/Buenos_Aires'` | |
| `locale` | varchar(10) | DEFAULT `'es-AR'` | |
| `settings` | jsonb | DEFAULT `'{}'` | Logo, colores, preferencias |
| `created_at`/`updated_at`/`deleted_at` | timestamptz | | Soft delete para cancelaciones recuperables |

**Sin RLS** (tabla raíz).

#### `branches`
Sucursales del tenant. Las agencias mono-sucursal tienen una sola entrada.

`id`, `tenant_id` FK NOT NULL, `name` varchar(120) NOT NULL, `address` varchar(255) NULL, `city` varchar(120) NOT NULL, `province` varchar(120) NOT NULL, `phone` varchar(40) NULL, `business_hours` jsonb NULL, `geo_point geography(Point,4326)` NULL (PostGIS), `is_active` boolean DEFAULT true, timestamps.

Índices: `(tenant_id, is_active)`; **GiST** sobre `geo_point`.

#### `plans`
Catálogo comercial. **Tabla compartida cross-tenant, sin RLS.**

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | uuid | PK | |
| `code` | varchar(40) | UNIQUE NOT NULL | `starter \| pro \| enterprise` |
| `name` | varchar(120) | NOT NULL | |
| `price_ars` | numeric(18,2) | NOT NULL | ⚠️ **Solo ARS.** El plan GTM define los precios en USD — el modelo no puede representarlos. Ver `IN-04`. |
| `max_users` | integer | NOT NULL | `0` = ilimitado |
| `max_vehicles` | integer | NOT NULL | `0` = ilimitado |
| `max_branches` | integer | NOT NULL | `0` = ilimitado |
| `modules` | jsonb | NOT NULL | Array de strings |
| `is_active` | boolean | DEFAULT true | |

⚠️ **Los valores concretos de los límites no coinciden entre `mejoras-y-saas` y `plan-gtm`.** Ver [14_pricing_y_gtm.md](14_pricing_y_gtm.md) y `IN-03`.

#### `subscriptions`
Histórico de suscripciones. Una vigente por tenant.

`id`, `tenant_id`, `plan_id`, `status` (`active | past_due | cancelled`), `start_date` date, `end_date` date NULL, `mp_subscription_id` varchar(120) NULL (Mercado Pago), `amount_ars` numeric(18,2) NOT NULL (precio efectivo, puede diferir del plan por descuento histórico), timestamps.

#### `users`

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | uuid | PK | |
| `tenant_id` | uuid | FK NOT NULL | |
| `email` | varchar(254) | NOT NULL | Único dentro del tenant |
| ~~`password_hash`~~ | — | **NO SE CREA** | ✅ **Eliminada por [`ADR-026`](../docs/adr/ADR-026-autenticacion-delegada-sin-password-hash.md)** (17-ago-2026). `users` es el espejo local del usuario de Keycloak: identidad de negocio y **nada de credenciales**. El vínculo es el `sub` del token (`ADR-021`). La columna de la spec §3.3 contradecía a §1546 del mismo documento. |
| `full_name` | varchar(180) | NOT NULL | |
| `phone` | varchar(40) | NULL | |
| `role` | `user_role_enum` | NOT NULL | `manager \| salesperson \| admin_staff` ⚠️ sin `super_admin`. Ver `IN-01`. |
| `status` | `user_status_enum` | NOT NULL | `active \| inactive \| invited \| suspended` |
| `last_login_at` | timestamptz | NULL | |
| ~~`mfa_enabled`~~ | — | **NO SE CREA** | No es credencial, pero es un **hecho de Keycloak**: copiarlo agrega un espejo que se desincroniza en silencio —alguien activa TOTP y la columna dice `false` para siempre—. Sale del claim o de una consulta puntual. Ver C-05 `design.md` `D-2` |
| ~~`mfa_secret`~~ | — | **NO SE CREA** | ⚠️ **El segundo `password_hash`, detectado el 17-ago-2026.** Es una credencial: `plan-seguridad` §112 pone la MFA del lado de Keycloak (*"provee auth e MFA opcional"*, *"custodia sus credenciales"*) y [`ADR-026`](../docs/adr/ADR-026-autenticacion-delegada-sin-password-hash.md) retiró los endpoints `/auth/mfa/*`. **`IN-06` documentó la contradicción de la contraseña y pasó de largo por la de al lado** |
| `created_at`/`updated_at`/`deleted_at` | timestamptz | | |

Índices: `UNIQUE (tenant_id, lower(email)) WHERE deleted_at IS NULL`; `INDEX (tenant_id, status)`.

#### `user_branches`
PK compuesta `(user_id, branch_id)`, `is_primary` boolean DEFAULT false, `created_at`.

### Dominio Stock

#### `vehicles` — entidad central del producto

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| `id` | uuid | PK | |
| `tenant_id` | uuid | FK NOT NULL | |
| `branch_id` | uuid | FK NOT NULL | Sucursal donde está físicamente. FK RESTRICT |
| `assigned_user_id` | uuid | FK NULL | Vendedor responsable. FK SET NULL |
| `domain_plate` | varchar(15) | **NOT NULL** | Dominio/patente, formato AR. ⚠️ El plan de implementación y el manual lo declaran **nullable/opcional**. Ver `IN-07`. |
| `brand_id` | uuid | FK NOT NULL | FK RESTRICT |
| `model_id` | uuid | FK NOT NULL | |
| `version_id` | uuid | FK NULL | |
| `year` | smallint | NOT NULL, CHECK BETWEEN 1950 AND `extract(year from now())+1` | |
| `mileage_km` | integer | NOT NULL, CHECK >= 0 | |
| `color` | varchar(60) | NOT NULL | |
| `fuel_type` | `fuel_type_enum` | NOT NULL | `gasoline \| diesel \| hybrid \| electric \| gnc \| flex` |
| `transmission` | `transmission_enum` | NOT NULL | `manual \| automatic \| cvt \| dsg` |
| `body_type` | `body_type_enum` | NOT NULL | `sedan \| hatchback \| suv \| pickup \| van \| coupe \| wagon \| other` |
| `chassis_number` | varchar(30) | NULL | VIN. 17 caracteres alfanuméricos sin I/O/Q |
| `engine_number` | varchar(30) | NULL | |
| `price_ars` | numeric(18,2) | NOT NULL, CHECK > 0 | |
| `price_usd` | numeric(18,2) | NULL | Para vehículos cotizados en moneda dura |
| `acquisition_cost_ars` | numeric(18,2) | NULL | **Restringido a roles que ven margen** (`manager`, `admin_staff`) |
| `status` | `vehicle_status_enum` | NOT NULL DEFAULT `'in_preparation'` | Ver máquina de estados abajo |
| `description` | text | NULL | Usada en publicaciones |
| `features` | jsonb | DEFAULT `'[]'` | Equipamiento, array de identificadores normalizados |
| `acquired_at` / `sold_at` | timestamptz | NULL | |
| timestamps + `deleted_at` | | | |

Índices: `UNIQUE (tenant_id, domain_plate) WHERE deleted_at IS NULL`; `UNIQUE (tenant_id, chassis_number) WHERE deleted_at IS NULL`; `(tenant_id, status)`; `(tenant_id, brand_id, model_id, year)`; **GIN trigram** sobre `domain_plate` y `description`.

#### Catálogos de vehículos (cross-tenant, sin RLS, escritura solo `super_admin`)

- **`vehicle_brands`**: `id`, `name` varchar(80) UNIQUE, `slug` UNIQUE, `origin_country`, `is_active`.
- **`vehicle_models`**: `id`, `brand_id` FK, `name` varchar(120), `body_type`, `year_from` smallint NOT NULL, `year_to` smallint NULL, `is_active`. `UNIQUE (brand_id, name)`.
- **`vehicle_versions`**: `id`, `model_id` FK, `name`, `engine_displacement numeric(3,1)`, `horsepower` smallint, `transmission`, `fuel_type`.

Seed inicial: **40 marcas, 300 modelos, 800 versiones**.

#### `vehicle_photos`
`id`, `tenant_id`, `vehicle_id` FK, `storage_url` varchar(500) NOT NULL (URL firmada vía CDN), `display_order` smallint NOT NULL DEFAULT 0, `is_cover` boolean NOT NULL DEFAULT false, `width_px`, `height_px`, `size_bytes` bigint, `uploaded_by` FK `users`, `created_at`.

Variantes generadas: `thumb` 200×150, `medium` 800×600, `original` (JPEG 85 %). Dimensiones mínimas de subida: 800×600. Tamaño máximo por foto: 10 MB.

⚠️ **El límite de fotos por vehículo tiene cuatro valores distintos en el corpus** (20 / 30 / 4-12 / 8-15). Ver `IN-09`.

#### `vehicle_status_history` (append-only)
`id`, `tenant_id`, `vehicle_id`, `from_status` NULL, `to_status` NOT NULL, `changed_by` FK `users`, `reason` text NULL, `changed_at`.

### Dominio CRM

#### `contacts`
`id`, `tenant_id`, `full_name` varchar(180) NOT NULL, `document_type` (`dni | cuit | passport`) NULL, `document_number` varchar(20) NULL, `primary_phone` varchar(40) NOT NULL (normalizado a **E.164**), `secondary_phone`, `email` varchar(254) NULL, `address`, `city`, `province`, `birth_date` date, timestamps + `deleted_at`.

Índices: `UNIQUE (tenant_id, document_number, document_type) WHERE document_number IS NOT NULL`; `UNIQUE (tenant_id, primary_phone)`; trigram sobre `full_name`.

Campos adicionales que aparecen solo en el plan de implementación: `source`, `tags text[]`, `notes`, `do_not_contact` boolean, `assigned_user_id`, `created_by_user_id`.

**Desduplicación**: por teléfono o documento, dentro del tenant (regla de la constitución).

#### `leads`

| Campo | Tipo | Notas |
|---|---|---|
| `id`, `tenant_id` | uuid | |
| `contact_id` | uuid FK NOT NULL | |
| `vehicle_id` | uuid FK NULL | Vehículo de interés (puede ser búsqueda genérica) |
| `assigned_user_id` | uuid FK NOT NULL | Vendedor responsable |
| `branch_id` | uuid FK NOT NULL | |
| `pipeline_stage_id` | uuid FK NOT NULL | Etapa actual |
| `source` | `lead_source_enum` | `deruedas_portal \| mercadolibre \| facebook \| walk_in \| phone \| referral \| other` |
| `status` | `lead_status_enum` DEFAULT `'open'` | `open \| won \| lost` |
| `loss_reason_id` | uuid FK NULL | Obligatorio si `status = lost` |
| `estimated_value_ars` | numeric(18,2) NULL | |
| `last_activity_at` | timestamptz NULL | Para detectar leads inactivos |
| `closed_at` | timestamptz NULL | |
| `notes` | text NULL | |

Índices: `(tenant_id, assigned_user_id, status)`, `(tenant_id, pipeline_stage_id)`, `(tenant_id, vehicle_id)`, `(tenant_id, last_activity_at)`.

#### `pipeline_stages`
`id`, `tenant_id`, `name` varchar(80) NOT NULL, `display_order` smallint NOT NULL, `is_initial` boolean, `is_won` boolean, `is_lost` boolean, `expected_duration_days` smallint NULL, timestamps.

Constraints de negocio: exactamente **una** etapa `is_won` y **una** `is_lost` por tenant; mínimo **3 etapas activas**.

⚠️ **El número de etapas por defecto tiene tres valores en el corpus: 5, 6 y 7.** Ver `IN-10`. Es el punto de contradicción más visible del corpus.

#### `lead_stage_history` (append-only)
`id`, `tenant_id`, `lead_id`, `from_stage_id` NULL, `to_stage_id` NOT NULL, `changed_by` FK `users`, `changed_at`.

#### `lead_activities`
`id`, `tenant_id`, `lead_id`, `activity_type` (`call | meeting | test_drive | quote | email | whatsapp | note | other`), `scheduled_at` NULL, `completed_at` NULL, `title` varchar(180) NOT NULL, `description` text, `outcome` text, `created_by`, timestamps.

#### `loss_reasons`
`id`, `tenant_id`, `name` varchar(120), `category` varchar(60) NULL.
Seed por defecto (6): Precio · Eligió otra marca · Compró usado · No conseguía financiación · Sin respuesta · Otra.

#### `tags` y `lead_tags`
`tags`: `id`, `tenant_id`, `name` varchar(60), `color` varchar(7) (hex).
`lead_tags`: pivote `(lead_id, tag_id)`.

### Dominio Communication

#### `conversations`
`id`, `tenant_id`, `contact_id` FK NOT NULL, `lead_id` FK NULL, `channel` (`whatsapp | facebook_messenger | sms | email`), `assigned_user_id` FK NULL, `status` (`open | snoozed | closed`) DEFAULT `'open'`, `last_message_at`, `last_inbound_at` (⭐ usado para la **ventana de 24 h de WhatsApp**), `unread_count` integer DEFAULT 0, timestamps.

Índices: `UNIQUE (tenant_id, channel, contact_id) WHERE status != 'closed'`; `(tenant_id, assigned_user_id, status)`.

#### `messages`
`id`, `tenant_id`, `conversation_id` FK, `direction` (`inbound | outbound`), `sender_user_id` FK NULL, `external_id` varchar(120) (ID en la plataforma externa), `body` text, `media_url` varchar(500), `media_type` (`image | video | document | audio`), `template_id` FK NULL, `status` (`pending | sent | delivered | read | failed`), `error_detail` text, `sent_at`, `delivered_at`, `read_at`, `created_at`.

**Particionada por mes.** Índice `(conversation_id, created_at)`.

#### `whatsapp_templates`
`id`, `tenant_id`, `name` varchar(120), `language` varchar(10) DEFAULT `'es'`, `category` (`marketing | utility | authentication`), `body_template` text (placeholders `{{1}}`, `{{2}}`), `meta_status` (`pending | approved | rejected`), `meta_template_id`, `rejection_reason`, `approved_at`, `created_at`.

#### `whatsapp_channels` (solo en el plan de implementación)
`id`, `tenant_id`, `phone_number_id`, `display_phone_number`, `business_account_id`, `access_token` (cifrado), `webhook_verify_token` (cifrado), `status` (`active | paused | disconnected`), `last_health_check_at`. **Una sola fila activa por tenant en el MVP.**

### Dominio Trade-in (Permutas)

#### `swap_requests`
`id`, `tenant_id`, `lead_id` FK NOT NULL, `incoming_brand_id`, `incoming_model_id`, `incoming_year`, `incoming_mileage_km`, `incoming_domain_plate`, `status` (`requested | valuated | inspected | accepted | rejected | closed`) DEFAULT `'requested'`, `accepted_value_ars`, `resulting_vehicle_id` FK NULL (**el vehículo creado en stock al cerrar**), timestamps.

#### `swap_valuations`
`id`, `tenant_id`, `swap_request_id`, `min_value_ars`, `mid_value_ars` (mediana de mercado), `max_value_ars`, `proposed_value_ars`, `data_source` (`deruedas_index | manual | external_api`), `created_by`, `created_at`.

#### `swap_inspections`
Inspección de **100 puntos**. `id`, `tenant_id`, `swap_request_id`, `mechanical_score`/`electrical_score`/`body_score` smallint CHECK 0-100, `mileage_verified` boolean, `structural_damage` boolean, `taxi_remis_history` boolean NULL, `details` jsonb (detalle de los 100 puntos), `inspector_user_id`, `inspected_at`.

### Dominio Finance

#### `financial_partners` (cross-tenant, configurable por Super Admin)
`id`, `name`, `api_endpoint`, `origination_fee_pct numeric(5,2)` (comisión a deRuedas), `max_ltv_pct`, `max_term_months`, `min_amount_ars`, `is_active`.

#### `credit_applications`
`id`, `tenant_id`, `lead_id` NULL, `operation_id` NULL, `contact_id` NOT NULL, `vehicle_id` NULL, `amount_ars`, `down_payment_ars`, `term_months`, `status` (`pre_qualifying | submitted | approved | rejected | signed | disbursed | cancelled`), `selected_offer_id` FK NULL, `submitted_at`, `resolved_at`, timestamps.

#### `credit_offers`
`id`, `tenant_id`, `application_id`, `partner_id`, `status` (`pending | offered | accepted | rejected | expired`), `monthly_payment_ars` (cuota), `nominal_rate_pct` (TNA), `effective_rate_pct` (TEA), `total_cost_ars` (CFT), `expires_at`, `external_offer_id`, `created_at`.

### Dominios restantes (documentados con menor detalle en la fuente)

**Documents**
- `documents`: `id`, `tenant_id`, `document_type_id`, `related_entity_type` (`vehicle | contact | operation`), `related_entity_id`, `storage_url`, `file_size`, `mime_type`, `ocr_text` (full-text indexed), `expires_at`, `uploaded_by`, `status`, `created_at`.
- `document_types` (cross-tenant): `id`, `code`, `name`, `has_expiration`, `requires_renewal`.
- `document_signatures`: `id`, `tenant_id`, `document_id`, `signer_contact_id`, `signature_provider`, `external_signature_id`, `signed_at`, `status`.

**Accounting**
- `payments`: `id`, `tenant_id`, `operation_id`, `contact_id`, `amount_ars`, `currency`, `payment_method`, `reference_number`, `paid_at`.
- `vendor_payments`: igual estructura con `vendor_id`.
- `bank_movements`: `id`, `tenant_id`, `bank_account_id`, `amount_ars`, `movement_date`, `description`, `reconciled_payment_id` FK NULL.
- `account_balances`: vista materializada de saldos por contacto.

**Operations**
- `sales_operations`: `id`, `tenant_id`, `vehicle_id`, `buyer_contact_id`, `sale_price_ars`, `sold_at`, `lead_id`, `swap_request_id`, `credit_application_id`, `status`.
- `operation_costs`: `id`, `operation_id`, `cost_type`, `amount_ars`, `description`.
- `publishing_status` / `vehicle_publications`: `vehicle_id` + `portal`/`channel` + `status` (`pending | published | updating | failed | unpublished`) + `published_at` + `external_url` + `last_error` + `retry_count` + `payload_hash`. `UNIQUE (tenant_id, vehicle_id, channel)`.

**Audit**
- `audit_logs`: `id`, `tenant_id` (**NULLABLE** — acciones cross-tenant de `super_admin`), `user_id`, `action`, `entity_type`, `entity_id`, `before_data` jsonb, `after_data` jsonb, `ip inet`, `user_agent`, `trace_id`, `occurred_at`.
  - **Particionada por RANGE mensual** sobre `occurred_at`, con 3 particiones creadas por adelantado.
  - **Append-only**: `UPDATE`/`DELETE` revocados al rol de aplicación.
  - **Sin RLS** (el filtrado es responsabilidad de la app).
  - Índices: `(tenant_id, occurred_at)`, `(entity_type, entity_id)`, `(user_id, occurred_at)`, `(trace_id)`.
  - ⚠️ **Retención**: la spec dice **mínimo 5 años** ("por obligaciones contables"); el plan de seguridad dice **24 meses**; el plan GTM la vende como escalonada por plan (30 días / 12 meses / 24 meses). Ver `IN-13`, **bloqueante**.

**Notifications y Feature Flags**
- `notifications`: `id`, `tenant_id`, `user_id`, `type`, `payload` jsonb, `read_at`, `created_at`.
- `feature_flags` (cross-tenant): `id`, `name`, `scope` (`global | tenant | user`), `target_id`, `is_enabled`, `conditions` jsonb.

**Infraestructura**
- `processed_events`: tabla de idempotencia del lado consumer de Redis Streams.
- `imports`: `id`, `tenant_id`, `type`, `source_filename`, `status` (`pending | parsing | validating | importing | completed | failed`), `total_rows`, `valid_rows`, `error_rows`, `created_by`, `started_at`, `completed_at`, `errors` jsonb.

## Máquinas de estado

### `vehicle_status_enum`

Valores: `available` · `reserved` · `sold` · `in_workshop` · `in_preparation` · `archived`

```
        (alta)
           │
           ▼
   in_preparation ──► available ──► reserved ──► sold ──► archived
                         ▲   │         │
                         │   │         └────► available   (se cae la reserva)
                         │   ├────► in_workshop ──► available
                         │   └────► archived
                         └──────────────────────────┘ (desarchivar)
```

- Transición a `sold`: **razón obligatoria**.
- Transición a `archived`: setea `exit_date` / `sold_at`.
- Transición inválida → `DomainError: invalid_transition`.
- No se puede archivar un vehículo con leads activos (422) hasta resolverlos.
- Un vehículo ya `sold` no se puede volver a vender: "el primero que marca como vendido, gana".

⚠️ El manual de usuario declara un estado **`Pausado`** que no existe en el enum, y omite `in_workshop` y `archived`; las historias de usuario omiten `archived`. Ver `IN-11`.

### `lead_status_enum` y pipeline

`status`: `open` · `won` · `lost` (independiente de `pipeline_stage_id`, que es configurable por tenant).

- Cerrar como `lost` requiere `loss_reason_id` obligatorio.
- **Integración cross-módulo**: `lead.won` con vehículo asociado → el vehículo pasa automáticamente a `sold` (si estaba `available` o `reserved`; si ya estaba `sold` por otro lead, solo se loguea un warning).

### `swap_status_enum`
`requested` → `valuated` → `inspected` → `accepted` → `closed` (o `rejected` en cualquier punto).
Al cerrar, se crea automáticamente el vehículo en stock (`resulting_vehicle_id`), en estado `in_preparation`, con trazabilidad bidireccional.

### `credit_status_enum`
`pre_qualifying` → `submitted` → `approved` → `signed` → `disbursed`. Ramas: `rejected`, `cancelled`.

### `message_status_enum`
`pending` → `sent` → `delivered` → `read`. Rama: `failed` (con `error_detail`).

### `conversation_status_enum`
`open` ↔ `snoozed` → `closed`. Cierre automático a los **30 días** sin actividad.

## Vistas materializadas

Refrescadas en background con cadencia por minuto u hora según el caso.

- `mv_pipeline_summary` — agregaciones por tenant y etapa.
- `mv_stock_aging` — días en stock por vehículo (reportes de rotación).
- `mv_sales_monthly` — ventas por mes, marca, modelo y vendedor.
- `mv_lead_conversion` — tasa de conversión por etapa y por canal.
- `mv_outstanding_receivables` — cuentas por cobrar por antigüedad.

## Seed data inicial

| Qué | Cantidad / valores |
|---|---|
| Marcas de vehículos | 40 |
| Modelos | 300 |
| Versiones | 800 |
| Planes | 3 (`starter`, `pro`, `enterprise`) |
| Etapas de pipeline por tenant nuevo | ⚠️ 5 / 6 / 7 según documento. La versión del plan de implementación (6): Nuevo(1), Contactado(2), En negociación(3), Permuta/Test drive(4), Ganado(5, `is_won`), Perdido(6, `is_lost`) |
| Motivos de pérdida por tenant nuevo | 6 (Precio, Eligió otra marca, Compró usado, No conseguía financiación, Sin respuesta, Otra) |
| Tenants de prueba (no producción) | 2-3 ficticios: "Agencia Norte", "Automotores del Sur" |

## Validadores específicos del dominio argentino

- **CUIT**: 11 dígitos con dígito verificador. Función PL/pgSQL `validate_cuit(text)`.
- **Dominio (patente)**: formato viejo `AAA 999` o Mercosur `AA 999 AA`.
- **Chasis (VIN)**: 17 caracteres alfanuméricos, sin `I`, `O` ni `Q`.
- **DNI**: validado según tipo de documento.
- **Teléfono**: normalizado a E.164.
