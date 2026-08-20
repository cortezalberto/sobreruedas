# ADR-020 — El rol de conexión de la aplicación no puede saltear RLS

- **Estado**: 🟢 **Aceptado** — 16-ago-2026
- **Origen**: hallazgo durante la implementación del bloque 2 de C-02 (`core-backend-primitives`)
- **Impacta**: `docker-compose.yml`, `docker-compose.test.yml`, `infra/local/postgres/init/`, `.env.example`, el job `test-backend-integration` del CI, y el aprovisionamiento de staging y producción (bloque 9 de C-01, sin arrancar)
- ⚠️ **Nota del 17-ago-2026**: este ADR **sigue vigente**, pero su ruta de aprovisionamiento cambió. Decía *"Terraform de staging y producción"*; con [`ADR-023`](ADR-023-despliegue-sobre-vps-con-docker-compose.md) no hay Terraform — los dos roles se crean en el **init de PostgreSQL** del VPS, igual que en local y en CI. La decisión de fondo (dos roles, aplicación sin `BYPASSRLS`) no se toca. Y **su pregunta abierta desapareció**: preguntaba si una base gestionada permitiría un rol de esquema sin `BYPASSRLS`, y con PostgreSQL autoalojado el `initdb` es nuestro.
- **Se implementa en**: change propio `rol-de-base-sin-bypass-rls` — **no** en C-02

---

## Contexto

`ADR-006` sostiene el aislamiento multi-tenant en tres capas simultáneas:

1. `tenant_id NOT NULL` en toda tabla de negocio
2. Política RLS `tenant_isolation` filtrando por `current_setting('app.current_tenant')`
3. Filtro `tenant_id` explícito también en el código de aplicación

`12_seguridad_y_compliance.md` llama a esto *"el control más crítico del sistema"*, y `RN-MT-07` califica una filtración entre tenants como incidente **P0** con notificación a la AAIP.

Al escribir los tests de la capa 2 contra PostgreSQL real, la capa 2 no aisló.

## El problema

**El rol con el que la aplicación se conecta a PostgreSQL es superusuario.**

```
SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user;

 current_user | rolsuper | rolbypassrls
--------------+----------+--------------
 deruedas     | t        | t
```

Un rol con `rolbypassrls` **ignora todas las políticas RLS**. No las evalúa, no las aplica: pasa de largo. La capa 2 existe en el catálogo y no hace nada.

### Evidencia

Misma tabla (`platform_probe`), misma política, mismo momento, tres consultas:

| Rol | Contexto de tenant | Filas devueltas |
|---|---|---|
| `prueba_rls` (`NOSUPERUSER NOBYPASSRLS`) | sin establecer | **0** ✅ |
| `prueba_rls` | establecido | **1** ✅ |
| `deruedas` (superusuario) | irrelevante | **26** ❌ |

La política es correcta. El rol la anula.

### Por qué no se detectaba

- **El test introspectivo sobre `pg_policies` da verde.** La política existe y está listada. `RN-MT-02` pide que toda tabla con `tenant_id` tenga la política `tenant_isolation`, y la tiene. **Cobertura de políticas no es aislamiento.**
- Ningún documento del corpus dice con qué rol debe conectarse la aplicación. La imagen oficial de PostgreSQL crea `POSTGRES_USER` como superusuario, y eso es lo que el compose le pasa al backend.
- Sin tablas de negocio ni tests de aislamiento —el estado hasta este change— no había nada que pudiera fallar.

### El agujero hermano, ya tapado

`ENABLE ROW LEVEL SECURITY` deja las políticas **sin aplicar al dueño de la tabla**, aunque el dueño no sea superusuario. Hace falta además `FORCE ROW LEVEL SECURITY`.

Son dos agujeros distintos. `FORCE` ya quedó en la migración `002` de C-02; este ADR trata el otro.

## Decisión

**La aplicación se conecta con un rol dedicado, `NOSUPERUSER` y `NOBYPASSRLS`, distinto del dueño del esquema.**

1. El rol propietario (el que crea tablas y corre migraciones) sigue siendo el actual.
2. Se agrega un rol de aplicación sin privilegios de administración y **sin capacidad de saltear RLS**, con `GRANT` sobre las tablas que necesita.
3. `DATABASE_URL` de la aplicación apunta al rol de aplicación. Las **migraciones** siguen corriendo con el rol propietario: crear tablas y políticas es justamente lo que el rol de aplicación no debe poder hacer.
4. Un test bloqueante verifica que el rol de conexión de la aplicación **no puede saltear RLS**, consultando `rolsuper` y `rolbypassrls` del `current_user`.

El punto 4 es el que convierte esto en una garantía y no en una convención: sin él, cualquier cambio de infraestructura que devuelva el superusuario al `DATABASE_URL` pasa desapercibido otra vez.

## Consecuencias

### A favor

- La capa 2 del aislamiento pasa a existir de verdad.
- Separar el rol propietario del rol de aplicación limita también el daño de una inyección SQL: el rol de aplicación no puede alterar políticas ni tablas.
- El test del punto 4 cubre una clase de fallo que la cobertura de políticas no ve.

### En contra — asumidas

- ~~Los `GRANT` hay que mantenerlos: cada tabla nueva necesita permisos explícitos para el rol de aplicación.~~ **Resuelto al implementar** (16-ago-2026): el init deja puesto un `ALTER DEFAULT PRIVILEGES` **sin `FOR ROLE`**, que aplica al rol que lo ejecuta —el propietario— y por lo tanto alcanza a toda tabla que ese rol cree de ahí en adelante. Además es agnóstico de cómo se llame el propietario, que en el compose de tests es otro. La fricción anticipada acá no existe.

  Con una salvedad que la sustituye, más chica: un default privilege es **silencioso cuando no se aplica** —volumen viejo, tabla creada por otro rol, esquema nuevo— y el síntoma sería un `permission denied` en runtime. Por eso va acompañado de un test que recorre el catálogo y falla si a alguna tabla con `tenant_id` le faltan permisos. Ver `design.md` D-3 del change.
- El entorno local necesita recrear el volumen (`docker compose down -v`) para que el init cree el rol nuevo.
- Terraform tendrá que provisionar los dos roles cuando se encare el bloque 9 de C-01.

## Alternativas consideradas

**Dejar el superusuario y confiar en las capas 1 y 3.** Descartada: contradice `ADR-006`, que declara las tres capas *simultáneas*, y deja el sistema con una defensa documentada que no existe. Peor que no tenerla, porque se la cuenta como puesta.

**Quitarle `BYPASSRLS` al rol actual sin separar propietario de aplicación.** Más barato, y tapa el agujero principal. Se descartó porque el rol seguiría siendo dueño de las tablas: alcanzaría un `ALTER TABLE ... NO FORCE` desde la aplicación para desactivar el aislamiento. Se pierde el beneficio de contención ante inyección.

**Resolverlo dentro de C-02.** Se descartó por alcance: toca compose, init de PostgreSQL, `.env`, CI y Terraform, mientras que C-02 declara producir primitivas de backend. Va en change propio.

## Mientras tanto

Los 5 tests de aislamiento que dependen de esto quedan marcados como fallo esperado **estricto** en la suite de C-02, apuntando a este ADR. Estrictos a propósito: el día que el rol se arregle, el fallo esperado se convierte en error y obliga a sacar la marca. Un `skip` los habría escondido.
