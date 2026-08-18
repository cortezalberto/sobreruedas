# Reglas de Negocio

> Reglas extraídas y codificadas desde: `constitucion.md`, `spec-tecnica.md`, `plan-implementacion.md`, `historias-usuario.md`, `manual-usuario.md`, `plan-seguridad.md`.
> Cada regla lleva un código `RN-{DOMINIO}-{NN}` para trazabilidad. Las reglas marcadas ⚠️ tienen valores contradictorios entre fuentes — ver [10_preguntas_abiertas.md](10_preguntas_abiertas.md).

---

## Dominio: Multi-tenancy (RN-MT)

- **RN-MT-01**: Toda tabla de negocio tiene `tenant_id NOT NULL`. No existe tabla de negocio sin discriminador de tenant.
- **RN-MT-02**: Toda tabla con `tenant_id` tiene RLS activo con la política `tenant_isolation` que filtra por `current_setting('app.current_tenant')`.
- **RN-MT-03**: El `tenant_id` se obtiene **exclusivamente del claim del JWT**. Nunca del body, query string ni header. Los schemas Pydantic lo excluyen explícitamente de los inputs.
- **RN-MT-04**: Ninguna query se considera correcta si no discrimina por tenant, aunque RLS ya la cubra. La redundancia es deliberada.
- **RN-MT-05**: Ningún cache se considera correcto si su clave no incluye el tenant.
- **RN-MT-06**: Sin `app.current_tenant` seteado, las queries sobre tablas con RLS **no devuelven filas**. La falla debe ser visible, nunca silenciosa.
- **RN-MT-07**: La filtración de datos entre tenants **no es un bug ordinario**: es un incidente **P0** de seguridad que dispara protocolo específico y notificación a la AAIP.
- **RN-MT-08**: La métrica `rls_violations_total` debe ser siempre 0. Cualquier incremento dispara P0 inmediato.
- **RN-MT-09**: Excepciones sin RLS, exhaustivas: `tenants`, `plans`, `vehicle_brands`, `vehicle_models`, `vehicle_versions`, `document_types`, `financial_partners`, `feature_flags`, `audit_logs`. Ninguna otra tabla puede estar exenta.
- **RN-MT-10**: Solo `super_admin` opera cross-tenant, y exclusivamente bajo el prefijo `/admin/api/v1`.

## Dominio: Autenticación y Autorización (RN-AU)

- **RN-AU-01**: La autenticación es estándar OAuth2 con OIDC vía Keycloak. **No se construye autenticación a medida** (regla constitucional).
- **RN-AU-02**: Las contraseñas se almacenan con hash **argon2id**. ⚠️ La constitución admite también bcrypt; la spec y el plan de seguridad exigen argon2id.
- **RN-AU-03**: Access token JWT firmado RS256, vida **15 minutos**. Refresh token vida **7 días**, con **rotación en cada uso** (el anterior se revoca).
- **RN-AU-04**: El refresh token solo es utilizable desde el dispositivo que lo emitió, identificado por su huella.
- **RN-AU-05**: Password mínimo **12 caracteres**, con letras, números y símbolo. Se rechazan contraseñas filtradas conocidas (verificación contra HIBP planificada para Ola 2, no en MVP).
- **RN-AU-06**: Bloqueo por fuerza bruta escalonado: 5 intentos → 5 min; 10 intentos → 30 min; 20 intentos → 24 h + notificación al usuario.
- **RN-AU-07**: El link de reseteo de contraseña caduca a las **2 horas**.
- **RN-AU-08**: Los mensajes de error de login son **genéricos**: no se diferencia "email inexistente" de "contraseña inválida".
- **RN-AU-09**: La contraseña nunca es recuperable, solo reseteable. Ni siquiera deRuedas la conoce.
- **RN-AU-10**: ⚠️ MFA: el manual de usuario la declara **obligatoria para `manager`**; el plan de seguridad la declara "en implementación" para `manager` y `super_admin` en Ola 1, opcional para el resto, y obligatoria para todos recién en Ola 2. La spec la declara simplemente "opcional con TOTP". Ver `IN-17`.
- **RN-AU-11**: La autorización se verifica **siempre en el backend**, con `require_role()` / `require_permission()`. El frontend solo oculta UI por UX.
- **RN-AU-12**: Un usuario pertenece a exactamente un tenant y tiene exactamente un rol.
- **RN-AU-13**: Email único por tenant, case-insensitive: `UNIQUE (tenant_id, lower(email)) WHERE deleted_at IS NULL`.
- **RN-AU-14**: Las invitaciones de usuario caducan a los **7 días**.
- **RN-AU-15**: Desactivar un usuario le corta el acceso inmediatamente; sus leads y operaciones quedan disponibles para reasignación.
- **RN-AU-16**: En el MVP **no hay signup público**: las cuentas se crean por invitación desde el backoffice. ⚠️ Contradicho por el plan GTM (`IN-14`).

## Dominio: Datos y privacidad (RN-DP)

- **RN-DP-01**: Toda entidad relevante para el negocio tiene identificador único persistente (UUID v7) e historial de cambios.
- **RN-DP-02**: **Los borrados son lógicos por defecto** (`deleted_at`), nunca físicos, salvo obligación legal de eliminación.
- **RN-DP-03**: Las migraciones de schema preservan la información existente. Cuando no es posible, la pérdida se documenta explícitamente.
- **RN-DP-04**: Los datos identificatorios personales se cifran en reposo y **se enmascaran en logs** por defecto (los DNI aparecen como `***12345`).
- **RN-DP-05**: Cada tenant es propietario de sus datos. La exportación completa en formato estándar está disponible bajo demanda.
- **RN-DP-06**: Al cancelar el servicio, los datos se conservan **90 días** y luego se eliminan definitivamente. ⚠️ El plan de seguridad dice **30 días** en cold storage. Ver `IN-18`.
- **RN-DP-07**: El uso agregado y **anonimizado** de datos cross-tenant (índice de precios) está permitido, siempre que no permita identificar al tenant de origen.
- **RN-DP-08**: Los datos de un tenant nunca se usan para mejorar la experiencia de otro tenant de manera que pueda inferirse información del primero.
- **RN-DP-09**: Marco legal aplicable: **Ley 25.326** (Argentina), Disposición 11/2006, Resolución 47/2018 de la AAIP. Mantenido "compatible" con principios GDPR, no GDPR-compliant.
- **RN-DP-10**: Roles bajo Ley 25.326: la **agencia tenant es responsable** de los datos de sus contactos/leads; **deRuedas es encargado**. Para los datos de los usuarios del SaaS (empleados del tenant), deRuedas es responsable.
- **RN-DP-11**: Derecho de supresión operacionalizado en `POST /api/v1/contacts/{id}/forget`: anonimiza el nombre (hash), vacía teléfono y email, elimina mensajes y deja constancia en `audit_logs`.
- **RN-DP-12**: Notificación a la AAIP ante brecha: objetivo **72 horas** desde la detección.
- **RN-DP-13**: Prohibido usar dumps de producción o de cliente real en cualquier ambiente de prueba. Todos los datos de test son 100 % sintéticos.

## Dominio: Stock / Vehículos (RN-ST)

- **RN-ST-01**: Un vehículo se identifica unívocamente dentro de un tenant por su **dominio (patente)**: `UNIQUE (tenant_id, domain_plate) WHERE deleted_at IS NULL`. Cargar un dominio duplicado se rechaza, ofreciendo buscar el existente.
- **RN-ST-02**: El número de chasis también es único por tenant: `UNIQUE (tenant_id, chassis_number) WHERE deleted_at IS NULL`.
- **RN-ST-03**: `year` entre 1950 y el año actual + 1. `mileage_km >= 0`. `price_ars > 0`.
- **RN-ST-04**: Estado por defecto al crear un vehículo: **`in_preparation`**.
- **RN-ST-05**: Transiciones de estado permitidas (y solo esas): `in_preparation→available`, `available→reserved`, `reserved→sold`, `reserved→available`, `available→in_workshop`, `in_workshop→available`, `sold→archived`, `available→archived`, `archived→available`. Cualquier otra → `DomainError: invalid_transition`.
- **RN-ST-06**: La transición a `sold` requiere razón obligatoria. La transición a `archived` setea la fecha de salida.
- **RN-ST-07**: No se puede archivar un vehículo con leads activos: se rechaza con **422** hasta resolverlos.
- **RN-ST-08**: Un vehículo con operación cerrada solo se puede **archivar**, nunca borrar.
- **RN-ST-09**: No se puede vender dos veces el mismo vehículo. Ante concurrencia, "el primero que marca como vendido, gana"; el segundo recibe error (`VehicleAlreadySoldError`).
- **RN-ST-10**: ⚠️ **Límite de fotos por vehículo**: cuatro valores en el corpus — 20 (historias y mejoras), 30 (implementación), 4-12 y 8-15 (manual). Ver `IN-09`.
- **RN-ST-11**: Tamaño máximo por foto: **10 MB**. Dimensiones mínimas: **800×600**. Máximo **10 archivos por request** de subida.
- **RN-ST-12**: El precio de costo (`acquisition_cost_ars`) solo lo ven `manager` y `admin_staff`. **Nunca se publica.**
- **RN-ST-13**: Importación masiva CSV: máximo **10 MB**, máximo **5.000 filas**, procesada en batches de 100 con commit por batch. Las fotos **no se importan** por planilla.
- **RN-ST-14**: Las fotos borradas se retienen 30 días en el object storage antes de eliminarse.
- **RN-ST-15**: El catálogo de marcas, modelos y versiones es **cross-tenant y de solo lectura** para los tenants; solo `super_admin` lo edita.

## Dominio: Publicación (RN-PU)

- **RN-PU-01**: Para publicarse, un vehículo requiere **al menos 1 foto y precio > 0**. Si no, error `cannot_publish_incomplete` **sin reintento**.
- **RN-PU-02**: La carga del vehículo dispara los eventos `vehicle.created` / `vehicle.updated`, que el módulo `publishing` consume para sincronizar con portales.
- **RN-PU-03**: Reintentos de publicación: **5 intentos**, base 60 s, factor 2, máximo 30 min, ~60 min de ventana total. Luego, dead-letter queue.
- **RN-PU-04**: Rate limit de republicación manual: **1 request por vehículo por minuto**.
- **RN-PU-05**: Reconciliación de publicaciones contra el portal: cron cada **24 horas**.
- **RN-PU-06**: Un vehículo marcado como vendido se despublica automáticamente.
- **RN-PU-07**: Unicidad de publicación: `UNIQUE (tenant_id, vehicle_id, channel)`.

## Dominio: CRM y Pipeline (RN-CR)

- **RN-CR-01**: Un lead es una oportunidad comercial; se asocia a un contacto, opcionalmente a un vehículo de interés, y **obligatoriamente a un vendedor responsable y a una sucursal**.
- **RN-CR-02**: El pipeline tiene etapas configurables por tenant. Debe haber **mínimo 3 etapas activas**, **exactamente una** `is_won` y **exactamente una** `is_lost`.
- **RN-CR-03**: ⚠️ El pipeline por defecto tiene **5, 6 o 7 etapas** según el documento. Ver `IN-10` (bloqueante).
- **RN-CR-04**: Cada cambio de etapa registra usuario, fecha y comentario en `lead_stage_history` (append-only).
- **RN-CR-05**: Cerrar un lead como perdido requiere `loss_reason_id` **obligatorio**.
- **RN-CR-06**: Cerrar un lead como ganado con vehículo asociado **dispara automáticamente** el pase del vehículo a `sold` (si estaba `available` o `reserved`).
- **RN-CR-07**: No se puede eliminar una etapa del pipeline que tenga leads sin reasignarlos previamente.
- **RN-CR-08**: Los contactos se desduplican dentro del tenant por **teléfono o documento**. `UNIQUE (tenant_id, primary_phone)`.
- **RN-CR-09**: Los teléfonos se normalizan a formato **E.164**.
- **RN-CR-10**: ⚠️ **Umbral de lead inactivo**: 3 días (historias), 5 días configurable (implementación), 24 h o 48 h en estado "Nuevo" (manual, contradictorio consigo mismo). Ver `IN-20`.
- **RN-CR-11**: El cron de detección de leads inactivos corre diariamente, por defecto a las 9:00 hora local del tenant.
- **RN-CR-12**: Un `salesperson` solo ve y opera **sus propios leads**. `manager` ve todos; `admin_staff` los ve en lectura.
- **RN-CR-13**: **Solo el `manager` puede reasignar leads entre vendedores.**
- **RN-CR-14**: Notificación de actividad programada: 30 minutos antes; el cron corre cada 5 minutos.

## Dominio: Mensajería / WhatsApp (RN-WA)

- **RN-WA-01**: **Ventana de 24 horas de Meta**: fuera de las 24 h desde el último mensaje *entrante* del contacto, solo se pueden enviar **templates aprobados**. Enviar texto libre fuera de la ventana → error `use_template`. Se controla con el campo `conversations.last_inbound_at`.
- **RN-WA-02**: Los templates deben estar aprobados por Meta antes de usarse. La aprobación tarda **24-48 horas**.
- **RN-WA-03**: Una sola conversación abierta por `(tenant, channel, contact)` de forma simultánea: `UNIQUE (tenant_id, channel, contact_id) WHERE status != 'closed'`.
- **RN-WA-04**: Las conversaciones se cierran automáticamente tras **30 días** sin actividad.
- **RN-WA-05**: Los mensajes en estado `queued` timeoutean tras **1 hora**.
- **RN-WA-06**: Rate limit de Meta: **250 mensajes/segundo** por número.
- **RN-WA-07**: Límites de adjuntos: audio < 16 MB, imagen < 5 MB. Las imágenes > 1 MB se comprimen antes de enviar.
- **RN-WA-08**: Un número de WhatsApp **no puede usarse simultáneamente** en la app de celular y en la API.
- **RN-WA-09**: En el MVP hay **un solo canal de WhatsApp activo por tenant** (multi-número por sucursal queda fuera de alcance).
- **RN-WA-10**: Retención de mensajes: **24 meses** por defecto, con cron mensual de borrado. Se borran solo los `messages`, no los `contacts` ni las `conversations`.
- **RN-WA-11**: Los webhooks entrantes se validan por **HMAC**, se persisten para idempotencia y se procesan asincrónicamente. El webhook debe responder 200 OK en **< 300 ms**.
- **RN-WA-12**: Toda conversación queda vinculada al lead y al vehículo de interés, para reconstruir el contexto con un clic.

## Dominio: Permutas (RN-PE)

- **RN-PE-01**: Una permuta es la operación en la que el comprador entrega un usado como parte de pago.
- **RN-PE-02**: El flujo tiene 4 etapas: solicitud inicial → valuación (con apoyo de la base de mercado, opcionalmente inspección física) → propuesta formal al cliente → cierre con documentación.
- **RN-PE-03**: Al cerrar la permuta, se **crea automáticamente** un registro de vehículo en stock por el usado recibido, con trazabilidad bidireccional (`swap_requests.resulting_vehicle_id`) hacia la venta original.
- **RN-PE-04**: El vehículo recibido ingresa en estado `in_preparation`.
- **RN-PE-05**: La inspección es de **100 puntos**, con scores 0-100 para mecánica, electricidad y carrocería, más flags de kilometraje verificado, daño estructural e historial de taxi/remis.
- **RN-PE-06**: Puede haber múltiples valuaciones iterativas sobre una misma solicitud.

## Dominio: Financiación (RN-FI)

- **RN-FI-01**: La precalificación crediticia debe responder en **menos de 30 segundos**.
- **RN-FI-02**: Las ofertas se comparan por cuota, plazo, **TNA, TEA y CFT**.
- **RN-FI-03**: Cada financiera define su `origination_fee_pct` (comisión a deRuedas), `max_ltv_pct`, `max_term_months` y `min_amount_ars`.
- **RN-FI-04**: Las financieras las configura exclusivamente el `super_admin` desde el backoffice.
- **RN-FI-05**: Las ofertas tienen fecha de expiración (`expires_at`).
- **RN-FI-06**: Los callbacks de las financieras entran por `POST /webhooks/finance/{partner}`, validados con HMAC e idempotentes.
- **RN-FI-07**: El plan Pro incluye integración con hasta 2 financieras; financieras adicionales se cobran por tarifa mensual de integración activa.

## Dominio: Documentos (RN-DO)

- **RN-DO-01**: Los documentos se asocian a un vehículo, un contacto o una operación (`related_entity_type` + `related_entity_id`).
- **RN-DO-02**: Los documentos con vencimiento generan alerta a **30 días** antes, y notificación urgente cuando faltan **menos de 5 días**.
- **RN-DO-03**: La búsqueda dentro del módulo es **full-text sobre el texto extraído por OCR** (`documents.ocr_text`).
- **RN-DO-04**: Tamaño máximo de documento: **50 MB** (contra 10 MB de las fotos).
- **RN-DO-05**: URLs firmadas: **5 minutos** para fotos, **30 minutos** para documentos.
- **RN-DO-06**: Tipos de documento canónicos del dominio argentino: tarjeta verde, cédula azul, formulario 08, certificado de transferencia, comprobante de patentamiento, libre deuda, certificado de dominio.

## Dominio: Planes y límites (RN-PL)

- **RN-PL-01**: Un plan es la combinación de límites cuantitativos (usuarios, vehículos, sucursales) y módulos habilitados.
- **RN-PL-02**: Los límites se validan **antes** de agregar un usuario, una sucursal o un vehículo (`PlanLimitsService.assert_can_add_*`). Cache con TTL de 60 segundos.
- **RN-PL-03**: Un **downgrade** de plan se rechaza con **422** si el tenant excedería los límites del plan destino.
- **RN-PL-04**: **El plan Starter no soporta multi-sucursal.** Intentar crear una segunda sucursal ofrece upgrade a Pro.
- **RN-PL-05**: No se puede eliminar una sucursal con vehículos asignados sin reasignarlos.
- **RN-PL-06**: ⚠️ Los valores concretos de los límites por plan **no coinciden** entre `mejoras-y-saas` y `plan-gtm`, ni la moneda. Ver `IN-03` y `IN-04` (bloqueantes).
- **RN-PL-07**: ⚠️ Duración del trial: **30 días** (`mejoras-y-saas`) vs **14 días** (`plan-gtm`). Ver `IN-21`.

## Dominio: Auditoría (RN-AD)

- **RN-AD-01**: Toda acción que afecte datos sensibles deja rastro en `audit_logs`, vía el decorador `@audit_action`.
- **RN-AD-02**: El registro incluye: usuario, tenant, timestamp, IP, user-agent, tipo de acción, entidad afectada, valores anteriores y posteriores en JSON, y `trace_id`.
- **RN-AD-03**: Los logs son **append-only**. `UPDATE` y `DELETE` están **revocados** al rol de aplicación. No existen endpoints para modificarlos.
- **RN-AD-04**: **Retención: 24 meses**, uniformes para todos los tenants — decidido por Dirección el 18-ago-2026, [`ADR-029`](../docs/adr/ADR-029-retencion-de-audit-logs.md). Lo que varía por plan es la **ventana de historia que el cliente ve en la UI** (Starter 30 días · Pro 12 meses · Enterprise 24), no lo que el sistema guarda: un mínimo de compliance no puede ser un feature de plan. ⛔ **El particionado NO está habilitado**: hay una pregunta legal abierta —si un asiento sobre una acción de facturación cuenta como respaldo contable ante AFIP— que va a asesoramiento antes de fijarlo.
- **RN-AD-05**: Los accesos JIT de personal de deRuedas llevan tag `jit=true` en `audit_logs`. TTL máximo del acceso JIT: 4 horas.
- **RN-AD-06**: La impersonación de un tenant por `super_admin` queda auditada.

## Dominio: Calidad e ingeniería (RN-CA)

*(Reglas constitucionales vinculantes — ver también [11_testing_y_calidad.md](11_testing_y_calidad.md))*

- **RN-CA-01**: Toda regla de negocio nueva tiene al menos una prueba unitaria que la verifica.
- **RN-CA-02**: Todo flujo principal de una historia de usuario tiene al menos una prueba E2E.
- **RN-CA-03**: ⚠️ **Cobertura mínima de backend**: 80 % global (constitución y CI del plan de implementación) vs 80 % core / 70 % resto (spec) vs 70 % líneas + 60 % branches (plan de testing). **Cuatro valores.** Ver `IN-22` (bloqueante).
- **RN-CA-04**: La cobertura **no decrece entre commits**, salvo excepción documentada.
- **RN-CA-05**: Los tests son deterministas. Un test *flaky* se trata como bug: se arregla o se elimina. No es negociable.
- **RN-CA-06**: Los archivos no superan **400 líneas**; las funciones no superan **50 líneas**. Superarlas exige descomponer o documentar el motivo.
- **RN-CA-07**: Toda función pública tiene firma tipada. Python con type hints completos; TypeScript sin `any` salvo justificación.
- **RN-CA-08**: El código no pasa el linter → no se mergea. Formateo y lint automáticos en pre-commit.
- **RN-CA-09**: El código se escribe en inglés, salvo identificadores del dominio argentino sin traducción razonable (`dominio`, `permuta`, `cuentaCorriente`).
- **RN-CA-10**: Las vulnerabilidades de severidad **alta o crítica bloquean el merge**.
- **RN-CA-11**: Los secretos no viven en el repositorio. Solo `.env.example` sin valores reales.
- **RN-CA-12**: Toda funcionalidad nueva se despliega detrás de un **feature flag controlable por tenant**.
- **RN-CA-13**: Los rollbacks deben ser posibles en **menos de 15 minutos** para cualquier deploy.
- **RN-CA-14**: No hay despliegues manuales en producción en condiciones normales.
- **RN-CA-15**: Regla de importación entre módulos: se importa del paquete (`from app.modules.stock import VehicleService`), nunca del interior (`from app.modules.stock.service import ...`). Validado en CI con import linter.
- **RN-CA-16**: No hay deuda técnica intencional sin un ADR que la justifique.

## Dominio: Performance (RN-PF)

- **RN-PF-01**: p95 de endpoints de listado **< 200 ms**; p99 < 500 ms. ⚠️ El plan de SRE fija el SLO en **< 300 ms**. Ver `IN-23` (bloqueante).
- **RN-PF-02**: p95 de endpoints de búsqueda full-text **< 500 ms**; p99 < 1,5 s. ⚠️ El plan de SRE fija **< 2,0 s**. Ver `IN-23`.
- **RN-PF-03**: p95 de endpoints de detalle < 150 ms. p95 de escritura simple < 300 ms.
- **RN-PF-04**: Carga inicial de la web: time-to-interactive **< 2 segundos** en 4G simulada.
- **RN-PF-05**: **Prohibidas** las consultas que escanean tablas completas con más de 100.000 registros en endpoints sincrónicos. Si la operación lo requiere, se ejecuta en background con notificación al usuario.
- **RN-PF-06**: Timeout de query en base de datos: 30 s.
- **RN-PF-07**: Las operaciones bulk (importación de stock, exportación contable) se ejecutan siempre en background con feedback de progreso.
- **RN-PF-08**: Tasa de error 5xx **< 0,1 % mensual**.
- **RN-PF-09**: Tasa de éxito de envío de mensajes WhatsApp **> 98 % mensual**.

## Dominio: Excepciones globales y trade-offs resueltos

Estos trade-offs ya están decididos por constitución y **no se rediscuten** sin enmienda formal:

- **Velocidad > completitud**: se libera el flujo principal con manejo de errores razonable; los casos borde se atienden por iteración.
- **Comprar > construir**, salvo en el núcleo competitivo. Se compra: autenticación, observabilidad, mensajería, OCR, firma electrónica, cloud, base de datos. Se construye: stock, CRM, permutas, integración con financieras, motor de inteligencia.
- **Opinión fuerte > configurabilidad**. El sistema debe funcionar bien sin configurar nada. ⚠️ Tensión: el pipeline es configurable desde el MVP, lo que roza el Principio 2. Ver `IN-24`.
- **Verticalidad > extensibilidad**. Diseñar para autos, no para "vehículos genéricos". Explícitamente fuera de alcance.
- **Performance > pureza arquitectónica**. Se aceptan desnormalizaciones, vistas materializadas y caches específicos en operaciones frecuentes de lectura, documentándolos.
