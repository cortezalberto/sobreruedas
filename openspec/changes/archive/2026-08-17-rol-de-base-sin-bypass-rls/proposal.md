# `rol-de-base-sin-bypass-rls`

## Why

**La segunda de las tres capas del aislamiento multi-tenant no está aislando nada.** El rol con el que la aplicación se conecta a PostgreSQL es superusuario con `rolbypassrls`, y un rol así **ignora todas las políticas RLS**: no las evalúa, pasa de largo.

Se descubrió implementando los tests del bloque 2 de C-02, contra PostgreSQL real. Misma tabla, misma política, mismo momento:

| Rol | Contexto de tenant | Filas |
|---|---|---|
| `prueba_rls` (`NOSUPERUSER NOBYPASSRLS`) | sin establecer | **0** ✅ |
| `prueba_rls` | establecido | **1** ✅ |
| `deruedas` (superusuario) | irrelevante | **26** ❌ |

La política es correcta; el rol la anula. Decidido en [`ADR-020`](../../../../docs/adr/ADR-020-rol-de-conexion-sin-bypass-de-rls.md).

**Por qué ahora y no cuando aparezca la primera tabla de negocio**: porque para entonces el agujero deja de ser teórico. Hoy la única tabla con `tenant_id` es la testigo que creó C-02; el día que existan `users`, `vehicles` y `leads`, lo mismo es una filtración entre agencias — incidente P0 con notificación a la AAIP (`RN-MT-07`).

Y lo más incómodo: **el test introspectivo sobre `pg_policies` da verde**. La política existe y está listada, así que `RN-MT-02` se cumple al pie de la letra. Cobertura de políticas no es aislamiento, y hoy nada mide la diferencia.

## What Changes

- **Rol de aplicación dedicado**, `NOSUPERUSER` y `NOBYPASSRLS`, distinto del rol propietario del esquema.
- **`DATABASE_URL` de la aplicación apunta a ese rol.** Las migraciones siguen corriendo con el propietario: crear tablas y políticas es exactamente lo que el rol de aplicación no debe poder hacer.
- **`GRANT` explícitos** para el rol de aplicación sobre las tablas que usa.
- **Test bloqueante** que verifica que el rol de conexión **no puede saltear RLS** — consultando `rolsuper` y `rolbypassrls` del `current_user`. Es lo que convierte esto en garantía y no en convención: sin él, cualquier cambio de infraestructura que devuelva el superusuario al `DATABASE_URL` vuelve a pasar desapercibido.
- **Los 5 tests de aislamiento de C-02 se destildan** de su marca de fallo esperado. Están escritos y hoy fallan estrictamente contra este defecto; cuando el rol se arregle, empiezan a pasar.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `platform/tenant-isolation`: se agrega el requisito de que **el rol de conexión de la aplicación no pueda saltear las políticas de aislamiento**. Los requisitos existentes describen qué debe pasar cuando la política aplica; ninguno exige que efectivamente aplique al rol que consulta. Ese hueco es este defecto.

> La capability nace en C-02 y todavía no está promovida a `openspec/specs/` — C-02 no se archivó. El delta se escribe cuando este change se retome, contra la ruta que C-02 ya fijó.

## Impact

**Infraestructura**: `infra/local/postgres/init/` (crear el rol), `docker-compose.yml` y `docker-compose.test.yml` (usuario de la aplicación), `.env.example` y `.env`.

**CI**: el job `test-backend-integration` levanta su propia base efímera y tiene que crear el rol igual.

**Terraform**: staging y producción provisionan los dos roles. Cae dentro del bloque 9 de C-01, hoy sin arrancar por la decisión de proveedor cloud pendiente.

**Migraciones**: cada tabla nueva necesita `GRANT` para el rol de aplicación. Es fricción asumida en `ADR-020` y la contracara de que el rol no sea dueño de todo.

**Entorno local**: hay que recrear el volumen (`docker compose down -v`) para que el init cree el rol.

### Lo que este change NO toca

El mecanismo de contexto de tenant de C-02 (`app/db/session.py`) **es correcto** — lo demuestra la fila del medio de la tabla de arriba. Acá no se cambia una línea de ese código.
