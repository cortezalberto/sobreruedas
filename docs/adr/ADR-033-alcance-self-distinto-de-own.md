# ADR-033 — El alcance `self` es distinto de `own`

- **Estado**: ✅ **Aceptado**
- **Fecha**: 20 de agosto de 2026
- **Change**: `C-02` (`core-backend-primitives`), bloque 6 — `T-014`, gobernanza **CRÍTICA**
- **Enmienda**: [`ADR-024`](ADR-024-matriz-rbac-canonica.md) §3 — agrega un valor al eje *Alcance*
- **Depende de**: [`ADR-000`](ADR-000-precedencia-documental.md) · [`ADR-017`](ADR-017-catalogo-de-roles-y-super-admin.md) · [`ADR-024`](ADR-024-matriz-rbac-canonica.md)

> **Por qué se decide ahora**: la tarea 6.5 manda transcribir las tablas de
> `ADR-024` §6 **literalmente** a `core/rbac.py`. Transcribirlas literalmente
> hoy produce un alcance indefinido en dos tablas. Regla dura 12.

---

## Contexto — `ADR-024` usa `own` con dos significados incompatibles

`ADR-024` §4 no deja lugar a interpretación:

> Un recurso es `own` de un sujeto si, y solo si, su `assigned_user_id` es igual
> al `id` del sujeto **en el momento de la petición**.

Y cierra con **"y nada más"**. Esa precisión es deliberada: es lo que hace que
`RN-CR-13` (*solo el `manager` reasigna*) funcione como control real.

Pero dos tablas de §6 escriben `own` para decir otra cosa:

| Tabla | Celda | Qué dice el propio ADR |
|---|---|---|
| **Auth** | `logout`, `GET /auth/me`, `mfa/enable`, `mfa/verify` → `own` | *"`own` acá significa **sobre sí mismo**: ningún rol opera la sesión ni la MFA de otro usuario"* |
| **Usuarios** | `PATCH /users/{id}` → `own` `[perfil]` para `salesperson` y `admin_staff` | *"el propio usuario puede editar campos no privilegiados"* |

**Ni `users` ni la sesión tienen `assigned_user_id`.** Un usuario no está
asignado a nadie: *es* alguien. La sesión tampoco — pertenece a quien la abrió.

Así que la transcripción literal que pide 6.5 deja `require_permission`
consultando un campo inexistente en esas dos tablas. El resultado no es un error
ruidoso: es un alcance que no se puede evaluar, y que según cómo se implemente
el caso degenerado termina interpretándose como *nadie* (bloqueo silencioso que
parece funcionar hasta que alguien no puede ver su propio perfil) o como
*cualquiera* (agujero). **Son exactamente los dos modos de falla que las tareas
6.3 y 6.8 existen para prohibir.**

Esto no es un defecto de redacción de `ADR-024`. Es una omisión del corpus que
el ADR heredó: las fuentes hablan de *"sus propios leads"* y de *"el propio
usuario"* con la misma palabra, y son dos relaciones distintas.

---

## Decisión

El eje **Alcance** de `ADR-024` §3 pasa a tener **tres** valores concedidos y la
ausencia como denegación:

| Valor | Significado | Comprobación |
|---|---|---|
| `all` | Todos los registros del tenant | — |
| `own` | Solo los asignados al sujeto | `recurso.assigned_user_id == sujeto.user_id` **en el momento de la petición** |
| `self` | Solo el propio sujeto | `recurso.id == sujeto.user_id` |
| *(ausente)* | **Denegado** | La ausencia es la denegación; no hay valor "denegado" explícito |

`own` **queda exactamente como está en §4**, con su "y nada más" intacto. Este
ADR no lo toca: le saca de encima los dos usos que no le correspondían.

### Celdas reetiquetadas

Ninguna celda cambia de permiso. Cambian de **nombre**, para que digan lo que
siempre quisieron decir:

| Tabla | Operación | Roles | Antes | Ahora |
|---|---|---|---|---|
| Auth | `logout`, `GET /auth/me`, `mfa/enable`, `mfa/verify` | los tres | `own` | `self` |
| Usuarios | `PATCH /users/{id}` | `salesperson`, `admin_staff` | `own` `[perfil]` | `self` `[perfil]` |

`PATCH /users/{id}` para `manager` sigue siendo `all`, sin cambio. Y `[perfil]`
sigue siendo lo que §6 define: `full_name`, `phone`, `avatar_url` y preferencias
de notificación — con `role`, `status`, `tenant_id`, `email` y la asignación de
sucursales del lado privilegiado, nunca autoeditables.

**Ninguna otra celda de §6 ni de §7 se toca.** Las celdas `own` de CRM, Stock y
Communication siguen siendo `own` en el sentido estricto de §4.

### `self` no relaja el aislamiento

La comprobación de tenant corre igual, y **antes**. `self` acota dentro del
tenant del sujeto; no es una puerta lateral para alcanzar un usuario de otro
tenant que casualmente compartiera identificador. Las tres capas de la regla
dura 1 siguen aplicando sin excepción.

---

## Alternativas consideradas

**Dejar Auth y Usuarios fuera de `require_permission`**, resueltas por su propia
comprobación de identidad. Más chico de escribir. Descartada porque abre un
**segundo mecanismo de autorización** en paralelo al de la matriz, y porque la
verificación automática de la tarea 6.9 —la que recorre las operaciones
expuestas contra el catálogo de roles— tendría que exceptuar esas rutas a mano.
Una lista de excepciones escrita a mano dentro del control que existe para que
no haya excepciones a mano se degrada sola.

**Estirar `own`** a *"`assigned_user_id`, o `id` si la tabla no tiene
`assigned_user_id`"*. Es la de menor diff. Descartada por dos motivos: contradice
el "y nada más" de §4, y sobre todo introduce un **fallback implícito por forma
de la tabla**. El día que una entidad nueva olvide su `assigned_user_id`, su
alcance `own` se convierte en `self` sin que nadie lo decida ni lo vea en un
diff. La regla se volvería dependiente del esquema en lugar del contrato.

**Enmendar `ADR-024` reescribiendo §4** para que `own` cubra los dos casos.
Descartada porque §4 es lo que le da sentido a `RN-CR-13`: si `own` se ablanda,
reasignar un lead deja de quitar el acceso, y el único control sobre reasignación
del sistema deja de controlar algo.

---

## Consecuencias

### A favor

- §4 sobrevive literal, y con él el control de `RN-CR-13`.
- `require_permission` no necesita ningún caso degenerado ni fallback: los tres
  valores se evalúan, la ausencia deniega, y no hay cuarta rama.
- El test de la tarea 6.10 —que `own` es `assigned_user_id` al momento de la
  petición— puede afirmarlo **sin recortes ni salvedades**, porque ya no hay dos
  familias de celdas `own` con semánticas distintas conviviendo.
- Las dos tablas afectadas quedan diciendo en el código lo mismo que su prosa ya
  decía en el ADR.

### En contra — asumidas

- **Un valor más en el eje.** Cada comprobación de alcance gana una rama, y
  quien lea la matriz tiene que distinguir `own` de `self`. Se asume porque la
  distinción es real: son dos relaciones distintas entre sujeto y recurso, y
  colapsarlas es lo que produjo este ADR.
- **`ADR-024` deja de leerse solo.** Sus §3 y §6 hay que leerlas junto con este
  documento. Se mitiga con el puntero en el encabezado, no se elimina.

---

## Lo que este ADR NO cierra

- **`IN-17`** (MFA obligatoria para `manager`) sigue abierto. `ADR-024` §6 ya
  dice que no es un permiso; reetiquetar la celda de `mfa/enable` no lo vuelve
  uno.
- **Los 9 módulos no declarados** de `ADR-024` §8 siguen denegados por ausencia.
  Este ADR no agrega ni quita filas.
- **`IN-08`** (contrato de `/leads/close` y transporte del stream) no se toca:
  las celdas afectadas no cambian de alcance.
