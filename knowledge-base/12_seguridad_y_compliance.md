# Seguridad y Compliance

> Fuente primaria: `deRuedas-plan-seguridad.md` (1.820 líneas). Complementado con `deRuedas-constitucion.md` (Artículos 3 y 6), `deRuedas-spec-tecnica.md` §8 y §6.5, y `deRuedas-plan-sre.md`.

## Principios de seguridad del producto

- **S1 — Aislamiento entre tenants garantizado por tres capas simultáneas**: políticas RLS de PostgreSQL, dependencies de FastAPI que setean el contexto de tenant en cada request, y tests automatizados de aislamiento bloqueantes en CI.
- **S3 — Roles sin acumulación de permisos**: los roles (`manager`, `salesperson`, `admin_staff`, `super_admin`) están diseñados para no acumular privilegios.
- Seguridad **por defecto**, no como capa posterior (Principio 6 de la constitución).
- La autorización se verifica **siempre en el backend**. El frontend solo oculta UI.

## Modelo de amenazas

Framework: **STRIDE** (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege).

**Superficies analizadas en profundidad**: API pública (FastAPI), webhooks entrantes, PostgreSQL, sistema de eventos (Redis Streams), sesión y autenticación.
**Superficies analizadas de forma abreviada**: backoffice admin, integraciones salientes (WhatsApp, portal, email), pipeline CI/CD.

**Actores modelados** (7): atacante externo no dirigido · atacante externo dirigido · **tenant malicioso** (insider del producto) · empleado del tenant deshonesto · **empleado de deRuedas deshonesto o comprometido** · subprocessor comprometido · error humano interno.

**Riesgos netos más altos** (probabilidad × impacto):

| Riesgo | Prob. | Impacto | Riesgo neto |
|---|---|---|---|
| Pérdida de aislamiento entre tenants por bug | Baja | **Crítico** | **Alto** |
| Compromiso de credencial de empleado deRuedas con privilegios | Media | **Crítico** | **Alto** |

Threat model resumido de la spec técnica (§8.1), consistente: filtración cross-tenant · takeover de cuenta · inyección · abuso de API (scraping, DoS, abuso de cuotas) · compromiso de servicios externos · errores del personal con acceso elevado.

## Autenticación

| Aspecto | Valor |
|---|---|
| Mecanismo | **OIDC vía Keycloak centralizado** (autohospedado, realm `deruedas`) |
| Hashing de password | **argon2id** (en Keycloak) ⚠️ la constitución admite además bcrypt — `IN-53` |
| Firma de JWT | **RS256** |
| Vida del access token | **15 minutos** |
| Vida del refresh token | **7 días**, con **rotación en cada uso** (el anterior se revoca) |
| Vinculación de dispositivo | El refresh token solo es usable desde el dispositivo que lo emitió (huella) |
| Password mínimo | **12 caracteres** + complejidad |
| Verificación contra HIBP (k-anonymity) | **Planificado para Ola 2** — no está en el MVP |
| MFA | TOTP (Google Authenticator, 1Password). ⚠️ Obligatoriedad en disputa — `IN-17` |
| Signup público | **No existe en el MVP.** Las cuentas se crean por invitación ⚠️ `IN-14` |
| Mensajes de error de login | **Genéricos** — no se distingue email inexistente de password inválida |

**Bloqueo por fuerza bruta** (escalonado): 5 intentos → 5 min · 10 intentos → 30 min · 20 intentos → **24 h + notificación al usuario**.

✅ **Tensión resuelta el 17-ago-2026 por [`ADR-026`](../docs/adr/ADR-026-autenticacion-delegada-sin-password-hash.md)**: `users` **no lleva** `password_hash`. El plan de seguridad tenía razón — el hash argon2id vive en Keycloak y *"deRuedas no tiene acceso al hash"* (§160). Consecuencia para esta sección: **no hay superficie propia de credenciales que auditar** — ni hash que filtrar, ni endpoint de login que sufra *credential stuffing*, ni lógica de reseteo propia.

## Autorización

Roles canónicos: **`super_admin`, `manager`, `salesperson`, `admin_staff`** — decididos por [`ADR-017`](../docs/adr/ADR-017-catalogo-de-roles-y-super-admin.md), **sin condición desde el 20-ago-2026**, cuando se ratificó `E-001`. Cuatro en el sistema, **tres en `user_role_enum`**: `super_admin` vive en `super_admins`, fuera de `users`.

✅ **La matriz RBAC canónica es [`ADR-024`](../docs/adr/ADR-024-matriz-rbac-canonica.md)**, que cierra el riesgo `R-2`. El corpus no la tenía: el plan de seguridad solo listaba los 4 roles y daba ejemplos puntuales, y las dos vistas parciales que la KB había reconstruido en [03_actores_y_roles.md](03_actores_y_roles.md) no coincidían entre sí. `ADR-024` las reconcilió aplicando la precedencia de `ADR-000` e incorporó las reglas `RN-*` y el principio `S3`, que ninguna de las dos había cruzado.

`S3` **prohíbe la herencia entre roles**: cada celda se enumera, `manager` no hereda de `salesperson`, y agregar un permiso a uno no se lo da al otro.

Ejemplos de permiso fino, que en `ADR-024` dejan de ser ejemplos y pasan a ser celdas: `salesperson` lee todos los vehículos del tenant pero **solo edita `internal_notes` y `assigned_user_id`**, y **no ve `acquisition_cost_ars`** (`RN-ST-12`) — este último obliga a restringir campos **también en lectura**, no solo en escritura.

Endpoint especial: `/admin/api/v1/tenants/{tenant_id}` requiere `super_admin` y es el **único que admite `tenant_id` por path**.

## Aislamiento multi-tenant (el control más crítico)

Cita textual del plan de seguridad:

> "Toda tabla con `tenant_id` tiene activada RLS con política **`tenant_isolation`** que filtra por `current_setting('app.current_tenant')`."

Controles:

1. `tenant_id` se infiere **exclusivamente del claim JWT**, nunca de body ni de query. Los schemas Pydantic lo excluyen explícitamente de los inputs.
2. Sin contexto de tenant seteado, las queries con RLS **no devuelven filas** — falla visible, no silenciosa.
3. RLS activo **también en las réplicas de lectura**, verificado por test.
4. Test introspectivo en CI que recorre `pg_policies` / `information_schema` verificando que toda tabla con `tenant_id` tenga política activa. **Bloqueante en PR.**
5. Métrica centinela **`rls_violations_total`** — debe ser siempre 0. Cualquier incremento es **incidente P0 inmediato** (runbook RB-004, tratado como incidente de seguridad, con escalada inmediata).
6. Pérdida de aislamiento → P0 → dispara notificación a la **AAIP** dentro de los plazos definidos.

## Cifrado

**En tránsito**: **TLS 1.2+ obligatorio** (preferentemente 1.3), incluso en comunicaciones internas entre containers. HSTS con `max-age` de 1 año, `includeSubDomains` y `preload`.

**En reposo**:
- **AES-256** a nivel de volumen (PostgreSQL, Redis, object storage) vía KMS del cloud provider. Rotación de claves **cada 12 meses** con recifrado automático.
- **Cifrado de campo** para secretos por tenant (API keys de WhatsApp, webhook tokens, semillas MFA): **AES-GCM** con clave derivada por tenant a partir de una master key en KMS. Rotación cada 12 meses.
- PII específica cifrada adicionalmente a nivel aplicación: DNI, CUIT, fotos de DNI.

**Enmascaramiento en logs**: obligatorio para toda PII. Los DNI aparecen como `***12345`.

**Sin secretos en código, config ni logs**: **`gitleaks` en CI** —historia completa + texto de los `.docx`— y en `pre-commit` como conveniencia. **`trufflehog` descartado** por [`ADR-027`](../docs/adr/ADR-027-escaneres-de-seguridad-declarados-vs-reales.md) §3.

## Protección de datos personales

**Marco legal**: **Ley 25.326** (Argentina), su decreto reglamentario, **Disposición 11/2006** y **Resolución 47/2018 de la AAIP**. Se mantiene *compatible* con los principios de GDPR — el documento aclara que **no es GDPR-compliant**, sino compatible.

**Roles bajo Ley 25.326**:
- Datos de contactos y leads → la **agencia tenant es responsable**; **deRuedas es encargado**.
- Datos de los usuarios del SaaS (empleados del tenant) → **deRuedas es responsable**.

**No se colectan datos sensibles del art. 7** (origen racial, salud, etc.) de forma intencional, salvo los incidentales que puedan aparecer en conversaciones de WhatsApp.

### Tabla de retenciones

| Dato | Retención declarada |
|---|---|
| Contactos activos | Mientras el tenant los mantenga; purga a **24 meses** de inactividad |
| Leads cerrados (won/lost) | Mínimo **5 años** desde el cierre |
| Mensajes de WhatsApp | **24 meses** desde `occurred_at` |
| Conversaciones cerradas (sin mensajes) | **60 meses** |
| `audit_logs` | **24 meses** ⚠️ la spec dice 5 años — `IN-13` **bloqueante** |
| Backups | **30 días** operativo; snapshot mensual **12 meses** ⚠️ la spec agrega archivado anual a 7 años — `IN-35` |
| Logs de aplicación | **90 días** |
| Datos tras cancelación del servicio | **30 días** en cold storage ⚠️ la constitución dice 90 días — `IN-18` |
| Datos contables (olas futuras) | **10 años** (Resolución 4717/2020 de AFIP) |

### Derechos del titular

- **Supresión**: `POST /api/v1/contacts/{id}/forget` — anonimiza el nombre (hash), vacía teléfono y email, elimina mensajes, deja constancia en `audit_logs`. Runbook: `docs/runbooks/data-subject-rights.md`.
- **Acceso y rectificación**: operacionalizados mediante endpoints de gestión disponibles para el tenant.
- **Portabilidad**: exportación completa de los datos del tenant en formato estándar, bajo demanda (Artículo 6 de la constitución).
- **Obligación contractual del tenant**: obtener el consentimiento de sus propios contactos.

### Notificación de brechas

Objetivo: **72 horas** desde la detección hacia la AAIP. El documento aclara que **no es una exigencia literal de la ley argentina**, sino la adopción voluntaria de una buena práctica internacional alineada a GDPR.

### Gaps de compliance reconocidos y aceptados

| Gap | Mitigación | Revisión |
|---|---|---|
| Sin DPO certificado formal | "Responsable interno" equivalente (`privacidad@deruedas.com`) | 24 meses |
| Sin SOC 2 ni ISO 27001 | Roadmap: SOC 2 Type I a 18 meses; Type II / ISO 27001 a 24-36 meses | 12 meses |
| Single-region | Ejercicio anual de DR | 12 meses |
| Sin bug bounty formal | Canal de responsible disclosure | 18 meses |
| Sin PAM dedicado | Accesos JIT auditados | 12 meses |

## Auditoría

Entidad: **`audit_logs`** — append-only, particionada mensualmente, con `UPDATE` y `DELETE` **revocados** al rol de aplicación.

Campos: `trace_id`, `user_id`, `tenant_id`, `ip`, `user_agent`, `action`, `entity`, `before`/`after` (jsonb), `timestamp`.

- Decorador **`@audit_action`** obligatorio en endpoints sensibles.
- Accesos JIT del personal de deRuedas llevan tag `jit=true`. TTL máximo del acceso JIT: **4 horas**.
- La impersonación de tenants por `super_admin` queda auditada.
- **Roadmap (Ola 3)**: hash chain para detectar tampering retroactivo + firma criptográfica periódica.

## Seguridad del ciclo de desarrollo (SSDLC)

| Herramienta | Alcance | Bloqueo |
|---|---|---|
| `ruff` | Lint + security, Python | **Bloqueante** |
| `mypy --strict` | Tipos, Python | **Bloqueante** |
| `semgrep` | SAST | **Bloqueante** en *high*; warning en *medium* |
| `eslint` + plugin de seguridad | TypeScript | **Bloqueante** |
| `pip-audit` | SCA Python | **Bloqueante** en crítico; warning en alto |
| `npm audit` | SCA JS | **Bloqueante** en crítico |
| `Trivy` | Imágenes Docker | **Bloqueante** en crítico |
| `gitleaks` | Secretos | **Bloqueante** ante cualquier detección. `trufflehog` descartado — `ADR-027` §3 |
| `sbom-generator` | SPDX, por release | — |
| `cosign` (Sigstore) | Firma de imágenes | — |
| **OWASP ZAP** | DAST, passive scan sobre staging con el tráfico de los tests E2E | *high* bloquea |

Regla constitucional: **las vulnerabilidades de severidad alta o crítica bloquean el merge**.

**Gestión de secretos**: ⛔ ~~KMS / secret manager del cloud provider (AWS Secrets Manager o Google Secret Manager)~~ → **SOPS + age** desde [`ADR-023`](../docs/adr/ADR-023-despliegue-sobre-vps-con-docker-compose.md). Rotación **trimestral automatizada** para las credenciales que lo soportan; ejercicio anual obligatorio de rotación de secretos de tenant.

⚠️ **La rotación automatizada queda sin mecanismo.** La ofrecía el gestor del proveedor; SOPS cifra pero no rota. El compromiso trimestral sigue siendo exigible y hoy no tiene con qué cumplirse — o se implementa el procedimiento, o se declara la excepción. `ADR-023` no lo cubre.

**Pentesting**: **anual** con vendor externo, más bajo demanda tras cambios mayores. La primera auditoría externa de seguridad técnica es un hito de Ola 1 (horizonte 0-6 meses).

**Responsible disclosure**: `security@deruedas.com` con PGP, respuesta inicial en **48 horas**, safe harbor, inspirado en disclose.io. Bug bounty formal con recompensas: planificado para Ola 3.

**Roadmap de hardening**: MFA obligatoria para todos los roles y commits firmados en Ola 2; SLSA nivel 2 en Ola 3.

## Protección contra OWASP Top 10

| Riesgo | Mitigación |
|---|---|
| Inyección | ORM obligatorio con parámetros bindeados; **nunca** concatenación de SQL |
| XSS | Escape automático en plantillas; CSP estricta; React escapa por defecto |
| CSRF | Tokens en operaciones de cambio de estado; cookies `SameSite=Strict` |
| SSRF | Lista blanca de dominios para fetch saliente desde el backend; validación de URLs |
| Deserialización insegura | Pydantic con validación estricta; **nunca** `pickle` de inputs externos |
| Componentes vulnerables | Scanner automatizado en pipeline (Trivy, Snyk) |
| Logging insuficiente | `audit_logs` estructurados con `trace_id` para correlación |

## Rate limiting, WAF y headers

| Control | Valor |
|---|---|
| Rate limit default (LB / CDN) | **100 req/s por IP** ⚠️ la spec dice 60 req/min por usuario y 1.000 req/min por tenant — `IN-19` |
| Login | 10/min por IP y por usuario |
| Reset de password | 3/hora por usuario |
| Republish de vehículo | 1/min por vehículo |
| `max_body_size` | **10 MB** JSON, **50 MB** multipart |
| Respuesta de webhook | **< 300 ms** (200 OK; procesamiento asincrónico) |
| Timeout de query en BD | 30 s |
| Cache de `Idempotency-Key` | 24 horas |
| Backoff de reintentos de eventos | 60 s, 120 s, 240 s, 480 s, 960 s (5 reintentos) → DLQ |

**Headers de respuesta**: HSTS (preload) · `X-Content-Type-Options: nosniff` · `X-Frame-Options: DENY` · `Referrer-Policy: strict-origin-when-cross-origin` · `Permissions-Policy` restrictiva · CSP estricta en producción.

## Respuesta a incidentes de seguridad

⚠️ Existen **dos taxonomías de severidad paralelas y deliberadas**: **P0-P4** para incidentes de **seguridad** (este documento) y **O0-O3** para incidentes **operativos** (plan de SRE). El propio plan de SRE lo explicita, así que **no es una contradicción**.

| Sev. | Etiqueta | Tiempo de respuesta |
|---|---|---|
| **P0** | Crítico | **Inmediato (< 15 min)** |
| **P1** | Mayor | < 1 hora |
| **P2** | Significativo | < 4 horas |
| **P3** | Menor | < 24 horas (días hábiles) |
| **P4** | Informativo | Backlog priorizado |

**Comunicación a los tenants**: P0 → primer aviso en **30 minutos** · P1 → **2 horas** · P2 → al cierre o a las 24 h (lo que ocurra primero) · P3-P4 → reporte mensual agregado.

**Objetivos de detección y atención**: MTTD < 15 min para P0/P1 · MTTA < 5 min para P0, < 30 min para P1 · triage inicial máximo **15 minutos**.

**Postmortem**: obligatorio para P0, P1 y P2, dentro de **5 días hábiles**, con **cultura sin culpa**.

## Gestión de personal y accesos

- **Onboarding**: MFA configurada antes del primer login.
- **Offboarding**: revocación de accesos dentro de **1 día hábil**.
- **Rotación de security reviewers**: trimestral.
- **Auditoría de subprocessors críticos**: anual.
- **Accesos JIT**: TTL máximo 4 horas, auditados con tag `jit=true`.
