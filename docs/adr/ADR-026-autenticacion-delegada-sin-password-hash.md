# ADR-026 — Autenticación delegada por completo: sin `password_hash`, con Authorization Code + PKCE

- **Estado**: ✅ **Aceptado** — ratificado el 2026-08-17
- **Fecha**: 2026-08-17
- **Decisores**: Tech Lead
- **Governance**: **CRÍTICA** — es el dominio de autenticación
- **Resuelve**: `IN-06` (¿lleva `users` una columna `password_hash`? ¿el login es OIDC o proxy de credenciales?) · `IN-12(a)` (el path de `accept-invitation`)
- **Afecta**: `C-05` (migración de `users`, endpoints de `auth`), `C-08` (auth en el frontend), `C-12` (invitaciones), `docs/openapi.yaml`
- **Deriva de**: `ADR-007` (corpus fuente, ver [`DD-07`](../../knowledge-base/09_decisiones_y_supuestos.md)) — lo lleva hasta sus consecuencias sobre el esquema y sobre el catálogo de endpoints

---

## Contexto

`IN-06` estaba planteado como una decisión abierta con dos lados. **Al ir al corpus no lo era.**

| Lado | Quién lo sostiene | Nivel |
|---|---|---|
| **La aplicación nunca ve la contraseña** | `constitucion` L105 · `spec-tecnica` §1546 · `plan-seguridad` §160 y §503 · `plan-implementacion` T-040 | N0 · N1 · N3 · N2 |
| **La aplicación guarda el hash y hace login** | `spec-tecnica` §221 (una columna) · `spec-tecnica` §4.2.1 (una línea de endpoint) | N1 |

Citas textuales del lado que gana:

> **N0** — *"La autenticación es estándar: OAuth2 con OIDC. **No se construye autenticación a medida.**"*
>
> **N1 §1546** — *"La autenticación se delega **íntegramente** a Keycloak. La aplicación **nunca maneja contraseñas en texto plano**."*
>
> **N3 §160** — *"Hasheados con argon2id **en Keycloak**. **deRuedas no tiene acceso al hash**."*
>
> **N2 T-040** — *"NextAuth con Keycloak provider; **PKCE habilitado**."*

**La `spec-tecnica` se contradice a sí misma**: §1546 dice que la aplicación nunca maneja contraseñas y §221 le da una columna para guardar su hash. No hace falta desempatar entre documentos — alcanza con leer el documento completo.

La regla dura 2 del proyecto ya había codificado esto (*"si ves `password_hash`, está mal"*). Lo que faltaba era el ADR que lo hiciera vinculante para el esquema y para el catálogo de endpoints.

---

## Decisión

### 1. `users` no lleva `password_hash`

La columna de `spec-tecnica` §3.3 **no se crea**. `users` es el **espejo local** del usuario de Keycloak: guarda identidad de negocio (nombre, rol, tenant, sucursales asignadas, estado) y **nada de credenciales**.

El vínculo con Keycloak es el `sub` del token, que ya fija [`ADR-021`](ADR-021-claims-de-tenant-y-rol.md).

### 2. El login es Authorization Code + PKCE, y el backend no participa

El **cliente OIDC es el frontend**: NextAuth en web (T-040), `expo-auth-session` en móvil. El backend **solo valida el JWT** que le llega.

Se descarta explícitamente **ROPC** (*Resource Owner Password Credentials*, el "proxy de credenciales"), por dos motivos independientes: obligaría a que la aplicación reciba la contraseña —contra N0, N1 §1546 y N3 §503— y está en vías de deprecación en OAuth 2.1.

### 3. De los 8 endpoints de `/auth` de `spec-tecnica` §4.2.1, sobreviven 2

| Endpoint | Destino | Por qué |
|---|---|---|
| `GET /api/v1/auth/me` | ✅ **backend** | Es el espejo local: usuario, rol, tenant y sucursales. Keycloak no lo sabe |
| `POST /api/v1/auth/logout` | ✅ **backend** | Dispara el *end-session* de Keycloak y limpia lo local |
| `POST /api/v1/auth/login` | ❌ retirado | Sería el proxy de credenciales. Lo reemplaza el redirect a Keycloak |
| `POST /api/v1/auth/refresh` | ❌ retirado | Lo maneja el cliente OIDC contra Keycloak |
| `POST /api/v1/auth/forgot-password` | ❌ retirado | Lo provee Keycloak |
| `POST /api/v1/auth/reset-password` | ❌ retirado | Lo provee Keycloak |
| `POST /api/v1/auth/mfa/enable` | ❌ retirado | Lo provee Keycloak (TOTP) |
| `POST /api/v1/auth/mfa/verify` | ❌ retirado | Lo provee Keycloak (TOTP) |

**Retirado no es "no implementado".** La funcionalidad existe y la presta Keycloak; lo que no existe es un endpoint nuestro que la duplique. Escribir esos seis sería *"construir autenticación a medida"*, que es literalmente lo que N0 prohíbe.

### 4. `accept-invitation` va bajo `/auth`, y hace menos de lo que su nombre sugiere

**Path elegido**: `POST /api/v1/auth/accept-invitation`, resolviendo `IN-12(a)` a favor de T-054 sobre T-024 — y corrigiendo que T-054 lo escribía **sin el prefijo `/api/v1`**.

Dos motivos:

1. Es un endpoint **público**: se llama con un token de invitación y sin sesión. Todo lo pre-autenticación vive bajo `/auth`.
2. Deja `/api/v1/users/*` **uniformemente autenticado**. El middleware necesita una regla en vez de una excepción, y una excepción en el middleware de autenticación es justo donde no conviene tenerlas.

**Lo que cambia de su alcance**: aceptar una invitación normalmente incluye *fijar la contraseña*, y eso pasa a ser trabajo de Keycloak (*required action* / `execute-actions-email`). El endpoint del backend **activa el espejo local y lo vincula al sujeto de Keycloak**. No recibe ni fija contraseña.

---

## Consecuencias

**A favor.** El sistema deja de tener dos fuentes de verdad sobre credenciales. La superficie de ataque de la aplicación baja: no hay hash que filtrar, ni endpoint de login que sufra *credential stuffing*, ni lógica de reseteo propia que auditar. MFA y SSO empresarial —el diferencial de Enterprise— salen de Keycloak sin código nuestro.

**En contra, asumido.** El backend **depende de Keycloak para que alguien pueda entrar**: si Keycloak no está, nadie se loguea. Ya era así por `ADR-007`; este ADR lo hace explícito. La mitigación es la de `ADR-025` — Keycloak con base propia en la misma instancia, cubierto por el archivado de WAL.

**Costo de migración: ninguno.** No hay usuarios en producción. Si los hubiera, retirar `password_hash` sería una migración destructiva y por la regla dura 13 iría en tres despliegues.

**Sobre `docs/openapi.yaml`.** Es de donde el frontend genera sus tipos. Los seis endpoints retirados **nunca deben aparecer ahí**: si aparecen, C-08 genera un cliente que llama a rutas que no existen, y el error sale recién en runtime.

> ⚠️ **Lo que este ADR NO decide.** La forma del `sub` y de los claims la fija `ADR-021`. La matriz de permisos la fija `ADR-024`. ~~El catálogo de roles sigue condicionado a `E-001`~~ — ✅ **`E-001` se ratificó el 20-ago-2026** y el catálogo quedó firme; el bloque de autorización de C-02 está destrabado. **Este ADR nunca destrabó `E-001`**: es ortogonal, decide de dónde sale la identidad, no qué puede hacer cada rol.

---

## Alternativas descartadas

**Conservar `password_hash` "por si acaso".** Una columna de credenciales que nadie escribe es peor que ninguna: aparece en cada revisión de esquema, en cada auditoría de compliance hay que explicar por qué está vacía, y el día que alguien la vea vacía va a querer llenarla. Además `plan-seguridad` §160 afirma que *"deRuedas no tiene acceso al hash"*, y una columna para guardarlo convierte esa afirmación en falsa aunque esté vacía.

**Los 8 endpoints como fachada que reenvía a Keycloak.** Mantiene el contrato de §4.2.1 intacto y le ahorra al frontend aprender dónde vive cada cosa. Se descartó porque son seis endpoints de código propio, con sus tests y su mantenimiento, cuyo único aporte es no cambiar una tabla de un documento — y porque una fachada sobre el flujo de credenciales es exactamente el lugar donde después alguien "optimiza" agregando un `POST` que sí recibe la contraseña.
