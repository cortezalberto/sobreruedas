# Realm de Keycloak — desarrollo local

`deruedas-dev-realm.json` se importa al arrancar el contenedor `keycloak` del [`docker-compose.yml`](../../../docker-compose.yml) raíz, vía `--import-realm`. Ubicación fijada por [`ADR-019`](../../../docs/adr/ADR-019-ubicacion-de-soporte-del-entorno-local.md).

> ⚠️ **No agregues comentarios dentro del JSON.** Keycloak deserializa con Jackson y **rechaza todo campo desconocido**: una clave extra, aunque empiece con guion bajo, hace fallar el arranque entero con `Unrecognized field`. Verificado a la mala el 13-ago-2026. Lo que haya que explicar, va acá.

## No es el realm de producción

Las políticas están relajadas a propósito para que el entorno local arranque sin fricción:

| Ajuste | Valor en local | Por qué |
|---|---|---|
| `sslRequired` | `none` | No hay certificados en `localhost` |
| `registrationAllowed` | `false` | No hay alta pública en el MVP: las cuentas se crean por invitación |
| `accessTokenLifespan` | 900 s | 15 minutos, cómodo para desarrollar |

La integración real de identidad la define **C-05**, que va a modificar este archivo. Se versiona justamente para que ese cambio se revise en un diff y no en clicks de una consola web que nadie recuerda haber hecho.

## Clients

| Client | Tipo | Redirect |
|---|---|---|
| `backend` | confidential, service account | — |
| `frontend-web` | public + PKCE (S256) | `http://localhost:3000/*` |
| `frontend-mobile` | public + PKCE (S256) | `deruedas://auth/*`, `exp://127.0.0.1:19000/*` |
| `frontend-admin` | public + PKCE (S256) | `http://localhost:3001/*` |

El único confidential es `backend`. Los tres frontends son públicos con PKCE porque corren en el dispositivo del usuario: un secreto embebido en un bundle de JavaScript o en un `.apk` no es un secreto.

## Roles

Según [`ADR-017`](../../../docs/adr/ADR-017-catalogo-de-roles-y-super-admin.md), el catálogo del sistema tiene **cuatro** roles, pero solo **tres** son de tenant:

```
Roles de tenant  → user_role_enum, tabla users
├── manager       ≡ Gerente
├── salesperson   ≡ Vendedor
└── admin_staff   ≡ Administrativo

Rol de plataforma → tabla super_admins, exenta de RLS
└── super_admin
```

`super_admin` **no es un cuarto valor del enum**. Es un actor de naturaleza distinta: no pertenece a ningún tenant, y por eso `users.tenant_id` puede seguir siendo `FK NOT NULL` sin excepciones. Acá es un rol de realm que discrimina el flujo de autenticación.

## Secretos

El `secret` del client `backend` es **ficticio** y solo vale en esta máquina (Constitución Art. 3). El de cada ambiente real vive en el gestor de secretos del proveedor y nunca se versiona.

## Cómo aplicar un cambio

El realm se importa **solo al arrancar**. Después de editar el JSON:

```bash
docker compose restart keycloak
```

Si el cambio no aparece, el import corrió pero Keycloak ya tenía el realm en su base embebida. Para forzar desde cero:

```bash
docker compose rm -sf keycloak && docker compose up -d keycloak
```
