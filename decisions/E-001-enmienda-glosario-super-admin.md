# E-001 — Propuesta de enmienda a la constitución

## Incorporar *"Super Admin"* al glosario canónico y ratificar la equivalencia de identificadores de rol

- **Estado**: 🟡 **EN DISCUSIÓN** — paso (b) del Artículo 8
- **Apertura**: jueves 13 de agosto de 2026
- **Cierre mínimo de discusión**: **jueves 20 de agosto de 2026** (5 días hábiles)
- **Proponente**: Tech Lead
- **Decide**: mayoría calificada del equipo técnico y de producto
- **Bloquea**: `C-02` (`core/rbac.py`, T-014), `R-2` (matriz RBAC), migración inicial de `users`
- **ADR asociado**: [`ADR-017`](ADR-017-catalogo-de-roles-y-super-admin.md), aceptado *condicionado a esta ratificación*

---

## Procedimiento — Artículo 8

| Paso | Estado |
|---|---|
| (a) Propuesta escrita identificando el artículo a modificar y la justificación | ✅ **Este documento** |
| (b) Discusión abierta del equipo, mínimo 5 días hábiles | 🟡 Abierta hasta el 20-ago-2026 |
| (c) Aprobación por mayoría calificada del equipo técnico y de producto | ⬜ Pendiente |
| (d) Registro de la enmienda con fecha, motivo y versión | ⬜ Pendiente |
| (e) Comunicación al equipo y a los stakeholders externos relevantes | ⬜ Pendiente |

> **¿Requiere consulta a Dirección?** El Artículo 8 la exige *"si la enmienda afecta principios fundamentales"*. Esta enmienda **no toca ningún principio**: agrega una definición a la Parte IV (Glosario) sin modificar ninguna existente. **Se propone que no requiere consulta a Dirección.** Este punto se somete a la discusión junto con el resto.

## Qué se propone modificar

**Parte IV — Glosario y definiciones canónicas.** Únicamente por **adición**. Ninguna definición existente se modifica ni se elimina.

### Adición 1 — Nuevo término canónico: *Super Admin*

> **Super Admin**
>
> Persona del equipo de deRuedas con atribuciones de administración de la plataforma. **No es un Usuario**: no pertenece a ningún tenant y no aparece en el padrón de usuarios de ninguna agencia. Opera exclusivamente sobre los endpoints de administración de plataforma y sus acciones quedan registradas en la auditoría con su identidad propia. La distinción es sustantiva: un Usuario existe dentro de un tenant, un Super Admin existe por encima de todos.

### Adición 2 — Nota de equivalencia en la definición de *Usuario*

La definición de **Usuario** se conserva **textualmente sin cambios**. Se le agrega debajo, como nota:

> *Nota de equivalencia.* Los identificadores de rol en código y en la base de datos son `manager` ≡ Gerente, `salesperson` ≡ Vendedor, `admin_staff` ≡ Administrativo. La interfaz de usuario emplea siempre los términos en español de este glosario.

## Justificación

### 1. El modelo actual no puede representar un actor que la propia spec técnica ya define

`spec-tecnica` §4.1.3 y §4.2.11 definen **11 endpoints bajo `/admin/api/v1`** para el Super Admin. Al mismo tiempo, `users.tenant_id` es `FK NOT NULL`.

Son dos afirmaciones incompatibles dentro del mismo documento vinculante. Es `IN-02`, y sin resolverlo `C-02` no puede escribir `core/rbac.py`, ni la migración inicial de `users`, ni los tests de autorización que `plan-testing` declara bloqueantes en CI.

### 2. La adición **preserva** el glosario en lugar de contradecirlo

Este es el punto central de la propuesta, y la razón por la que se pide una adición y no una modificación.

El planteo original de `IN-01` sugería reemplazar el catálogo de tres roles del glosario por uno de cuatro. Eso **sí** habría sido una modificación contenciosa.

Al decidir que el Super Admin vive en una tabla propia (`ADR-017`), las dos definiciones del glosario quedan intactas:

| Definición vigente | Efecto de esta enmienda |
|---|---|
| *"Un usuario pertenece exactamente a un tenant"* | **Intacta.** `users.tenant_id` sigue `NOT NULL`. |
| *"Un usuario tiene un rol (Gerente, Vendedor, Administrativo)"* | **Intacta.** Siguen siendo esos tres. |

La enmienda **no cambia qué es un Usuario**. Define un término distinto que hoy falta y que el resto del corpus ya usa sin haberlo declarado.

### 3. Cierra una divergencia entre cinco documentos

`IN-01` es una de las 14 inconsistencias bloqueantes. Con `ADR-017` más esta enmienda, el catálogo queda unívoco: **cuatro roles en el sistema, tres en `user_role_enum`**, y el cuarto en su propia tabla.

### 4. La nota de equivalencia elimina una ambigüedad, no crea una

El glosario establece que un término *"se asume con el **significado** aquí establecido"*: fija significados, no lexemas. Bajo esa lectura, `manager` con el significado de Gerente no contradice nada.

Pero esa lectura hoy es **implícita**, y el Principio 5 es terminante: *"las decisiones implícitas no son vinculantes y pueden ser cuestionadas en cualquier momento"*. Ratificar la equivalencia la vuelve vinculante y evita que la discusión se reabra en cada revisión de código.

## Impacto si se ratifica

- `user_role_enum` se crea con **tres** valores: `manager`, `salesperson`, `admin_staff`.
- Se crea la tabla `super_admins`, sin `tenant_id`, **exenta de RLS**.
- `users.tenant_id` permanece `FK NOT NULL`, sin excepciones.
- `audit_logs` referencia al actor de forma polimórfica: `(tipo_de_actor, id)`.
- Se desbloquean `C-02` y la redacción de la matriz RBAC (`R-2`).
- La constitución pasa a versión 1.1, con la enmienda acumulada al final del documento como historial, según el Artículo 8.

## Impacto si se rechaza

- `ADR-017` se revisa y hay que elegir entre las alternativas descartadas: `tenant_id` nullable (rompe el invariante de aislamiento) o Super Admin solo en Keycloak (pierde trazabilidad de auditoría).
- Los 11 endpoints de `/admin/api/v1` quedan sin rol que los autorice.
- `C-02` sigue bloqueado, y con él el camino crítico completo.

## Alternativas al texto propuesto

Se someten a discusión junto con la propuesta:

1. **Llamarlo *"Administrador de Plataforma"*** en lugar de *"Super Admin"*, por coherencia con un glosario íntegramente en español. Contra: los cinco documentos que ya lo mencionan usan "Super Admin", y renombrarlo obliga a corregir todos.
2. **Omitir la nota de equivalencia** y dejar la lectura de "significado, no lexema" como interpretación. Contra: el Principio 5 la volvería no vinculante y reabrible.
3. **Definir además *"Customer Success Manager"***, la quinta persona de `historias-usuario`. Contra: ese documento es N4, no normativo, y no hay ningún endpoint ni permiso asociado. Se propone **no** incluirlo, y tratarlo si alguna vez aparece en un documento normativo.

---

## Registro de la discusión

> Completar durante el período de discusión. Las intervenciones se acumulan acá para dejar rastro, como exige el Artículo 8 para la constitución misma.

| Fecha | Participante | Postura | Comentario |
|---|---|---|---|
| 2026-08-13 | Tech Lead | Propone | Apertura de la discusión |
