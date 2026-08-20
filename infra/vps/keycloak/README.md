# Realm de producción de Keycloak

Este directorio se monta en `/opt/keycloak/data/import` del contenedor de Keycloak en producción (`docker-compose.prod.yml`).

## Está vacío a propósito, y eso es un pendiente declarado

**Hoy no hay ningún realm de producción versionado acá.** El directorio existía sin un solo archivo, y Docker lo montaba vacío sin quejarse: Keycloak arrancaba bien, y el realm sencillamente **no existía**. Nadie se enteraría hasta el primer intento de login.

Detectado el 17-ago-2026 reproduciendo la topología en la máquina local. Se agrega este archivo para que el hueco sea visible en el repositorio en vez de ser un directorio vacío que nadie mira.

## Por qué no se copia el de desarrollo

[`infra/local/keycloak/`](../../local/keycloak/) tiene el realm `deruedas-dev`, y **no sirve tal cual**:

- Los clientes apuntan a `localhost`, no al dominio de producción.
- Trae secretos de desarrollo, que por la regla dura 4 no pueden ser los de producción.
- `start-dev` importa en cada arranque; producción usa `start` e importa **una sola vez**.

Copiarlo sin adaptarlo pondría credenciales de desarrollo en producción.

## Qué falta hacer

Es trabajo de **`C-05`**, el change que trae identidad y autenticación de verdad. Hasta entonces esto queda vacío y declarado.

Cuando se haga:

1. Exportar el realm con `kc.sh export`, ya adaptado al dominio de producción.
2. Versionar el JSON **sin secretos** — los secretos de cliente van por variable de entorno, cifrados con SOPS.
3. Importarlo una vez, según el runbook de [`../README.md`](../README.md).
4. Verificar que el descubrimiento OIDC responde:
   `curl https://<dominio-auth>/realms/deruedas/.well-known/openid-configuration`

> ⚠️ Mientras este directorio esté vacío, **el espacio de identidad de producción no existe**. El backend valida tokens contra un realm inexistente y todo login falla. No es un problema mientras no haya usuarios; sí lo es el día que se despliegue `C-05`.
