# C-05 · Diseño técnico

## D-1 — `users` es un espejo, y hay que decidir qué refleja

`ADR-026` fija que `users` no lleva credenciales. Lo que **no** fija es dónde queda la frontera entre lo que sabe Keycloak y lo que sabemos nosotros, y esa frontera es la decisión de diseño central del change.

| Dato | Dueño | Por qué |
|---|---|---|
| Contraseña, TOTP, sesiones | **Keycloak** | `ADR-026`. Nunca los vemos |
| Email, nombre | **Keycloak**, copiado | Keycloak los usa para autenticar y notificar; los copiamos para poder listar y buscar sin llamarlo en cada request |
| Rol, tenant, sucursales | **Nosotros** | Son dominio de negocio. Keycloak no sabe qué es una sucursal |
| Estado (`invited`/`active`/…) | **Nosotros** | Es ciclo de vida de negocio, no de credencial |

**La copia de email y nombre se desincroniza**, y hay que decir qué pasa cuando eso ocurre. La regla es: **Keycloak gana**. Un espejo que miente sobre a quién pertenece una cuenta es peor que no tener espejo.

> **Dónde se corrige — corregido el 21-ago-2026, al implementarlo.** Esta decisión decía *"en cada request, `get_current_user` compara el email del token contra el espejo y lo actualiza si difiere"*. Al escribirlo apareció que **`get_current_user` no toca la base**: solo verifica la firma del token contra el JWKS. Cumplirlo al pie de la letra obligaría a darle una sesión de base y a sumarle un `SELECT` a **cada request del sistema**, incluidas todas las que no miran `users` para nada.
>
> Se corrige en **`GET /auth/me`**, que ya tiene la fila en la mano. Mismo efecto, costo cero.
>
> **Lo que se pierde, y queda escrito**: el espejo de alguien que nunca abre su perfil sigue viejo para un listado ajeno. Se acepta — el email de una persona cambia rara vez, y quien lo cambia en Keycloak es porque está usando el sistema.
>
> Dos límites que el diseño no había previsto y que los tests fijan:
>
> - **Un token sin `email` no borra el del espejo.** El claim viene del client scope homónimo, que es un *default* del realm y no una garantía del protocolo. Pisar el email con `None` cambiaría un espejo desactualizado —el problema que esta decisión resuelve— por uno vacío, que es peor.
> - **Se corrige el email y nada más.** El token trae el rol que la persona tenía cuando se emitió; arrastrarlo desharía una degradación de permisos sola en el próximo request, con la fuente equivocada mandando sobre la buena.

> **Se evaluó no copiar nada y consultar a Keycloak siempre, y se descartó.** Listar los usuarios de una agencia se convertiría en N llamadas HTTP a Keycloak, y una caída suya dejaría de ser "nadie puede entrar" para pasar a ser "nadie puede ver nada". El acoplamiento se acota a lo que ya existe.

## D-2 — `mfa_secret` tampoco se crea

`spec-tecnica` §3.3 le da a `users` dos columnas de MFA:

| Columna | Decisión | Motivo |
|---|---|---|
| `mfa_secret varchar(255)` | ❌ **no se crea** | Es una credencial. `plan-seguridad` §112 pone la MFA del lado de Keycloak (*"provee auth e MFA opcional"*, *"custodia sus credenciales"*) y `ADR-026` ya retiró `/auth/mfa/enable` y `/auth/mfa/verify` |
| `mfa_enabled boolean` | ❌ **no se crea** | No es credencial, pero es un **hecho de Keycloak**. Copiarlo agrega un espejo que se desincroniza en silencio: el usuario activa TOTP en Keycloak y nuestra columna dice `false` para siempre |

**Es el mismo error que `password_hash`, y nadie lo había marcado.** `IN-06` documentó la contradicción para las contraseñas y pasó de largo por la de al lado. Si la UI necesita mostrar si un usuario tiene MFA, sale del claim del token o de una consulta puntual a Keycloak — no de una columna nuestra que envejece.

`plan-seguridad` §443 exige MFA **obligatoria** para `manager` y `super_admin`. Eso se configura como *required action* del realm, no con una columna.

## D-3 — `super_admins` es tabla, no un valor del enum

Lo fija `ADR-017` y se aplica. Lo que este change agrega es la consecuencia sobre el aislamiento:

- `super_admins` **no lleva `tenant_id`** y va **exenta de RLS** — ya está declarada en `EXENTAS_DE_RLS` desde C-02, con el comentario *"`ADR-017`: rol de plataforma, fuera de todo tenant"*.
- `users.tenant_id` es **`NOT NULL`**. Es la diferencia práctica de la decisión: si `super_admin` fuera un valor del enum, esta columna tendría que ser nullable y **toda** consulta del sistema tendría que contemplar el caso "usuario sin tenant". Con la tabla aparte, `users` conserva su invariante.

> ⚠️ **Esto no habilita nada de `/admin/api/v1`.** Los 11 endpoints del espacio administrativo son C-09. Acá solo nace la tabla, para que `users.tenant_id NOT NULL` sea defendible.

## D-4 — Los dos endpoints de `auth` que sobreviven

`ADR-026` §3 los fija; acá se define qué hacen.

### `GET /api/v1/auth/me`

Devuelve **lo que el token no dice**: nombre, estado, sucursales asignadas y cuál es la principal. El `sub`, el `tenant_id` y el `role` ya viajan en el token (`ADR-021`) y se devuelven igual, para que el frontend tenga una sola fuente.

**No acepta ningún parámetro.** El sujeto sale del token y solo del token. Un `GET /auth/me?user_id=…` sería una escalada de privilegios con forma de conveniencia.

### `POST /api/v1/auth/logout`

Invalida la sesión **en Keycloak** (*end-session*) y no guarda nada local. No hay lista de tokens revocados nuestra: un access token vive 15 minutos y mantener una denylist propia sería reimplementar parte de OIDC.

> **Consecuencia asumida y explícita**: entre el `logout` y el vencimiento del access token pueden pasar hasta **15 minutos** en los que ese token sigue siendo válido contra la API. Es el comportamiento estándar de OIDC con tokens de vida corta. Cerrarlo de verdad exige consultar a Keycloak en cada request (introspección), que agrega una llamada de red al camino caliente de **toda** petición. Si algún día hace falta —por ejemplo para revocación inmediata tras un incidente—, el mecanismo es la introspección y está identificado.

## D-5 — La invitación no fija contraseña, y eso cambia el flujo

`ADR-026` §4 achica el alcance de `accept-invitation`. El flujo completo queda así:

| Paso | Quién | Qué pasa |
|---|---|---|
| 1 | Nuestro backend | `POST /users/invitations` crea el usuario en `users` con estado `invited` **y** el usuario en Keycloak, deshabilitado |
| 2 | Keycloak | Manda el mail con *required action* `UPDATE_PASSWORD` |
| 3 | La persona | Fija su contraseña **en la UI de Keycloak**. Nunca en la nuestra |
| 4 | Nuestro backend | `POST /auth/accept-invitation` con el token: activa el espejo local y lo vincula al `sub` |

**El paso 1 escribe en dos sistemas y puede fallar a la mitad.** Si Keycloak falla después de que `users` se grabó, queda un usuario `invited` sin cuenta que nunca va a poder entrar. Se resuelve **creando primero en Keycloak** y después localmente: al revés, el estado inconsistente es invisible; así, un fallo local deja una cuenta huérfana en Keycloak que la reinvitación reutiliza por email.

> No se usa una transacción distribuida. Dos sistemas, dos escrituras y un orden elegido para que el fallo caiga del lado recuperable es la solución proporcionada al problema — un *saga* acá sería más máquina de estados que la que se está protegiendo.

## D-6 — Desactivar no es dar de baja, y la cuota los cuenta distinto

Tres estados que se confunden fácil:

| Acción | Efecto | ¿Consume cuota del plan? |
|---|---|---|
| `status = 'inactive'` | No puede entrar; sigue siendo empleado | **Sí** — ocupa licencia |
| `deleted_at` (baja) | Dejó la empresa | **No** — libera el lugar |
| Baja en Keycloak | No puede autenticarse en ningún lado | — |

Lo fija `D-7` de C-04 y este change lo implementa registrando el contador:

```python
limites.registrar(Recurso.USERS, contar_usuarios)
```

**Sin esa línea, `assert_can_add_user` levanta `ContadorNoRegistrado`.** Es a propósito: C-04 lo dejó fallando cerrado justamente para que este olvido sea imposible de no notar.

**Dar de baja un usuario NO lo borra de Keycloak**, lo deshabilita. Borrarlo liberaría el email para otra cuenta y rompería la trazabilidad de qué hizo esa persona — el mismo criterio que C-04 aplicó al CUIT de una agencia dada de baja.

## D-7 — Qué se conserva cuando alguien se va

`users` lleva `deleted_at` (soft delete, Principio 3), y con él una pregunta que el corpus no responde: **las filas que referencian a ese usuario.**

- `user_branches` **se conserva**. Saber en qué sucursal trabajaba alguien es parte del histórico.
- Todo lo que en el futuro tenga `assigned_user_id` **se conserva y no se reasigna sola**. Reasignar automáticamente al dar de baja parece una cortesía y es una pérdida de información: nadie sabría después quién atendió realmente ese lead.
- `ADR-024` §4 define que `own` es `assigned_user_id` **en el momento de la petición**, así que un recurso de alguien dado de baja simplemente deja de ser `own` de nadie. No hace falta nada más.

## D-8 — El orden de las migraciones, y por qué `super_admins` va primero

| Rev | Qué crea | Por qué ahí |
|---|---|---|
| `009` | `super_admins` | No depende de nada y deja `EXENTAS_DE_RLS` sin mentir: hoy declara exenta una tabla que no existe |
| `010` | `user_role_enum` + `users` + RLS + `FORCE` | Necesita `tenants` (C-04) |
| `011` | `user_branches` + RLS + `FORCE` | Necesita `users` y `branches` |

Las tres son **aditivas** (regla dura 13). `user_branches` lleva `tenant_id` propio además de las dos FK: sin él la política RLS no tiene contra qué comparar, y una tabla de unión sin política es el agujero clásico — las dos puntas están protegidas y el vínculo no.

> ⛔ **Ninguna de las tres se escribe antes del 20-ago-2026.** `E-001` nombra la *"migración inicial de `users`"* entre lo que bloquea, y `ADR-017` —que fija los tres valores del enum— está aceptado **condicionado** a esa ratificación. Si se rechaza, el catálogo cambia, y **quitar un valor de un enum es destructivo**: la regla dura 13 lo prohíbe en un paso. Regla dura 12.

## D-9 — El realm de Keycloak se versiona como archivo

`infra/local/keycloak/deruedas-dev-realm.json`, importado al arrancar. No se configura a mano por la UI.

> **Corregido el 21-ago-2026.** Esta decisión había escrito `infra/keycloak/realm-deruedas.json`, una ruta que nunca existió. El archivo real vive bajo `infra/local/`, y esa separación —`local/`, `vps/`, `observability/`— ya existía en el repositorio y dice algo que la ruta plana no: **qué realm es de qué entorno**. Se acepta la ruta real y se corrige el texto, en vez de mover el archivo para que le dé la razón a un renglón.
>
> Va con una regla que el diseño no había explicitado y que hacía falta al mover los *mappers*:
>
> | Qué | Dónde | Por qué |
> |---|---|---|
> | Estructura del realm — roles, flujos, mappers, vida de los tokens | **El JSON versionado** | Es igual en toda máquina |
> | Configuración por máquina — el `redirectUri` del puerto del frontend | **`sembrar_dev.py`** | El puerto vive en `.env` y cambia por escritorio; el seed lo **agrega**, no lo reemplaza |
>
> Los mappers estaban del lado equivocado: los creaba el seed por la API de administración. No era configuración a mano —el seed es idempotente— pero era un segundo lugar donde vivía la verdad, y el JSON declaraba menos de lo que el realm realmente tenía.

Un realm configurado a mano no es reproducible: el entorno local de cada uno diverge, staging diverge del local, y el día que hay que levantarlo de nuevo nadie sabe qué tenía. Es el mismo criterio que `ADR-023` le aplicó al VPS.

**Lo que el archivo declara**: el cliente público con PKCE obligatorio y `Standard Flow` (nunca `Direct Access Grants`, que es ROPC), los tres roles de tenant más `super_admin`, los *mappers* que ponen `tenant_id` y `role` como claims planos (`ADR-021`), la vida de los tokens (15 min / 7 días) y MFA como *required action* para `manager`.

> ⚠️ **`Direct Access Grants` desactivado no es un detalle de configuración: es lo que hace que `ADR-026` sea cumplible.** Con ese flujo habilitado, cualquiera con el `client_id` puede cambiar usuario y contraseña por un token — y el "nunca manejamos contraseñas" pasa a depender de que a nadie se le ocurra usarlo. Un test lo verifica sobre el JSON, igual que `test_auditoria_de_dependencias` verifica el `ci.yml`.
