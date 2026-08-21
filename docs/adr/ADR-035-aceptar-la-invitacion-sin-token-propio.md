# ADR-035 — Aceptar la invitación no usa un token nuestro

- **Estado**: Aceptado
- **Fecha**: 2026-08-21
- **Decide sobre**: [`ADR-026`](ADR-026-autenticacion-delegada-sin-password-hash.md) §4 · C-05 tareas 5.7 y 5.8
- **Regla de negocio tocada**: `RN-AU-14` (las invitaciones caducan a los 7 días)

## Contexto

`ADR-026` §4 fija que `POST /api/v1/auth/accept-invitation` es **público** y que *"se llama con un token de invitación y sin sesión"*. Al implementarlo apareció que **ningún documento del corpus define de dónde sale ese token**: ni su formato, ni quién lo emite, ni cómo se revoca. Lo único fijado es que la invitación caduca a los 7 días (`RN-AU-14`).

Las tres formas de producirlo tienen costos distintos:

| Mecanismo | Costo |
|---|---|
| JWT propio firmado | Una clave de firma nueva de la aplicación — hoy **no existe ninguna** — que además va cifrada con SOPS (regla dura 4) |
| Token opaco en base | Migración aditiva y un secreto guardado en la base, hasheado, con su rotación y su auditoría |
| Delegarlo a Keycloak | Ninguno: **ya existe** |

## Decisión

**No se emite ningún token de invitación propio.** El flujo queda así:

| Paso | Quién | Qué pasa |
|---|---|---|
| 1 | Backend | `POST /users/invitations` crea la cuenta en Keycloak (deshabilitada, sin credencial) y el espejo local en estado `invited` |
| 2 | Backend | Dispara la *required action* `UPDATE_PASSWORD` — **Keycloak manda el mail, con su propio token, que ya caduca** |
| 3 | La persona | Fija su contraseña en la UI de Keycloak y entra por el login normal |
| 4 | Backend | `POST /api/v1/auth/accept-invitation`, **autenticado**, activa el espejo local |

En consecuencia, el endpoint pasa de **público** a **autenticado**.

## Por qué

**Un access token válido de Keycloak ya es la prueba de que la persona aceptó la invitación.** Para tenerlo tuvo que fijar su contraseña y autenticarse — que es exactamente lo que "aceptar" significa en este flujo. Un segundo token que pruebe lo mismo es una prueba redundante con su propia superficie de ataque.

**Y un token de invitación nuestro contradice el propósito declarado de `ADR-026`.** Ese ADR justifica toda la delegación diciendo que el sistema queda sin *"endpoint de login que sufra credential stuffing, ni lógica de reseteo propia que auditar"*. Un token de invitación **es** una credencial propia: hay que emitirla, expirarla, revocarla, auditarla y protegerla de reenvíos. Emitir una para completar el flujo que existe para no tener credenciales propias sería cumplir la letra del ADR contra su intención.

**`RN-AU-14` se sigue cumpliendo, y en un solo lugar.** Los 7 días los hace valer la *required action* de Keycloak, que ya tiene vencimiento configurable. Con un token nuestro habría **dos** relojes que mantener sincronizados, y el día que difieran nadie sabría cuál manda.

## Lo que cambia respecto de `ADR-026`

Esto **desvía** de `ADR-026` §4 en un punto y por eso se registra como ADR, según la regla 3 de precedencia — sin ADR sería decisión implícita y, por el Principio 5, no vinculante.

| `ADR-026` §4 decía | Queda |
|---|---|
| Endpoint **público** | **Autenticado** |
| *"se llama con un token de invitación"* | Se llama con el access token normal |
| Activa el espejo y lo vincula al sujeto | **Solo activa el espejo** |

Ese último renglón no es un recorte: el vínculo **ya existe por construcción**. `users.id` **es** el `sub` de Keycloak — no hay columna `keycloak_sub`—, así que la fila nace vinculada. No hay nada que vincular después.

**Lo que NO cambia**: el endpoint sigue en `/auth` y no en `/users`, sigue sin recibir ni ver una contraseña, y `/api/v1/users/*` sigue uniformemente autenticado. Los dos motivos de `ADR-026` §4 para elegir ese path siguen valiendo — el segundo, más que antes.

## Consecuencias

**A favor.** Cero credenciales propias, un solo reloj de caducidad, y ninguna clave nueva que cifrar ni rotar. La tarea 5.8 —*"token inválido o vencido se rechaza y deja el estado en `invited`"*— la cumple la validación de token que ya existe: un token vencido da **401** y el espejo no se toca.

**En contra, asumido.** La persona tiene que **entrar** antes de que su espejo se active, así que entre el paso 3 y el 4 figura como `invited` para quien mire el listado de la agencia. Es una ventana de segundos y refleja la realidad: todavía no usó el sistema.

**El endpoint es idempotente.** El doble clic sobre el mail va a pasar; si la segunda llamada levantara, la persona vería un error habiendo hecho todo bien.

## Alternativas descartadas

**JWT propio firmado a 7 días.** Cumple `ADR-026` al pie. Se descartó por lo de arriba: agrega la credencial que el ADR existe para no tener, y exige una clave de firma que hoy no existe en `config.py` y que habría que sumar al circuito de SOPS.

**Token opaco en base.** Revocable de verdad, sin clave nueva. Se descartó porque el problema que resuelve —revocar una invitación— ya se resuelve mejor: **dar de baja al usuario deshabilita la cuenta en Keycloak**, y sin cuenta no hay login ni invitación que aceptar. Una tabla de tokens sería un segundo mecanismo de revocación para lo mismo.

**Dejar que `/auth/me` active el espejo solo.** Ahorra el endpoint entero. Se descartó porque el frontend genera su cliente desde `docs/openapi.yaml` (C-08): un `GET` que además muta estado es exactamente la clase de efecto que nadie encuentra cuando lo busca.
