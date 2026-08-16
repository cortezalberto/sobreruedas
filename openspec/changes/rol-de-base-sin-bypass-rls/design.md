# Diseño — `rol-de-base-sin-bypass-rls`

## Context

C-02 dejó el mecanismo de aislamiento multi-tenant escrito y probado contra PostgreSQL real: `app/db/session.py` establece `app.current_tenant` como primera sentencia de la transacción, la migración `002` creó `platform_probe` con su política `tenant_isolation` y `FORCE ROW LEVEL SECURITY`, y hay 13 tests de integración que lo ejercitan.

Cinco de esos tests están en **fallo esperado estricto**. No porque el código esté mal, sino porque el rol con el que la aplicación se conecta —`deruedas`, el `POSTGRES_USER` del compose— es superusuario con `rolbypassrls`, y un rol así ignora toda política RLS. Diagnóstico completo y evidencia medida en [`ADR-020`](../../../docs/adr/ADR-020-rol-de-conexion-sin-bypass-de-rls.md).

Motivación en [`proposal.md`](proposal.md). La decisión ya está tomada y aceptada; este documento define **cómo** se implementa.

Un punto que conviene tener presente antes de leer las decisiones: hoy `DATABASE_URL` cumple tres papeles a la vez —conectar la aplicación, correr las migraciones y darles DDL a los tests— y funciona solo porque el rol es superusuario. Separar el rol de aplicación no es agregarle una restricción a una pieza: es **desarmar esa conflación en tres caminos con permisos distintos**. Casi todo lo que sigue es consecuencia de eso.

## Goals / Non-Goals

**Goals:**

- Que la capa 2 del aislamiento (`ADR-006`) efectivamente aísle, y que los 5 tests en fallo esperado pasen sin tocar una línea de `app/db/session.py`.
- Que el defecto **no pueda volver en silencio**: un cambio de infraestructura que devuelva el superusuario al `DATABASE_URL` tiene que romper el pipeline, no pasar desapercibido.
- Que el rol de aplicación no pueda desactivar su propio aislamiento ni alterar el esquema, para que una inyección SQL tenga techo.
- Que la fricción de mantener permisos no dependa de que alguien se acuerde.

**Non-Goals:**

- No se toca el mecanismo de contexto de tenant de C-02. Es correcto: con un rol sin bypass, aísla. Ver la tabla de evidencia de `ADR-020`.
- No se implementa el Terraform de staging y producción. Cae en el bloque 9 de C-01, hoy sin arrancar por la decisión de proveedor cloud pendiente (`IN-16`). Este change deja escrito **qué** debe provisionar.
- No se define política de rotación de la credencial del rol de aplicación. Es operación, y vive con el gestor de secretos.
- No se avanza sobre ningún bloque pendiente de C-02.

## Decisions

### D-1 · Dos roles con responsabilidades distintas, no un rol al que se le quita un atributo

Lo más barato sería `ALTER ROLE deruedas NOSUPERUSER NOBYPASSRLS`. Tapa el agujero medido y no toca nada más.

Se descarta por lo que ya anticipa `ADR-020` en sus alternativas: ese rol **sigue siendo el dueño de las tablas**, y el dueño puede `ALTER TABLE platform_probe NO FORCE ROW LEVEL SECURITY`. El aislamiento quedaría a una sentencia de distancia de cualquier código de aplicación —o de cualquier inyección— y esa sentencia no requiere ningún privilegio especial: alcanza con ser dueño.

Entonces son dos roles con papeles separados:

| Rol | Quién es | Qué puede |
|---|---|---|
| **Propietario** — `deruedas` (el actual) | Dueño del esquema | DDL, migraciones, políticas. **No** atiende tráfico. |
| **Aplicación** — `deruedas_app` (nuevo) | El del `DATABASE_URL` de la app | `SELECT`, `INSERT`, `UPDATE` sobre las tablas otorgadas. Nada más. |

`NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT LOGIN`. El `NOINHERIT` es barato y cierra la puerta a que una pertenencia futura a un rol de grupo le devuelva privilegios sin que nadie lo note.

### D-2 · El rol lo crea la infraestructura; los permisos, la migración

Son dos objetos de naturaleza distinta y se les nota en el alcance: un **rol** es del cluster de PostgreSQL, un **permiso** es sobre una tabla concreta. Meterlos en el mismo lugar obliga a elegir mal en uno de los dos.

- **El rol** se crea donde se crea el cluster: `infra/local/postgres/init/` en local y en CI, Terraform en staging y producción. Una migración de Alembic no puede crearlo de forma confiable: correría con el rol propietario, y en una base gestionada ese rol no tiene `CREATEROLE`.
- **Los permisos** se otorgan donde nace la tabla: en su migración. Es el único lugar que sabe que la tabla existe, y viaja a todos los entornos por el mismo camino que la tabla.

El init es un `.sh` y no un `.sql` por una razón concreta: el nombre y la credencial del rol de aplicación tienen que salir del entorno (`APP_DB_USER`, `APP_DB_PASSWORD`, con defaults de desarrollo), y un `.sql` en `docker-entrypoint-initdb.d` no lee variables de entorno. Sigue el precedente de `POSTGRES_USER`/`POSTGRES_PASSWORD`: son variables **del contenedor de la base**, no de la aplicación, así que no entran en `ADR-013` ni en `.env.example`.

*Consecuencia asumida*: el init de PostgreSQL corre **una sola vez**, al crear el volumen. Quien ya tenga el entorno levantado necesita `docker compose down -v`. Ver D-8.

### D-3 · Los permisos se otorgan por defecto, y un test verifica que estén

`ADR-020` asume como costo que *"cada tabla nueva necesita `GRANT` para el rol de aplicación"*. Esa fricción se puede eliminar casi por completo sin resignar nada:

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE ON TABLES TO deruedas_app;
```

Sin `FOR ROLE`, aplica al rol que ejecuta la sentencia —el propietario— y alcanza a **toda tabla que ese rol cree de ahí en adelante**. Además es agnóstico del nombre del propietario, que en el compose de tests es `deruedas_test` y no `deruedas`.

Pero un default privilege es silencioso por naturaleza: si el volumen es viejo, si alguien crea una tabla con otro rol, o si se agrega un esquema nuevo, no se aplica y **nadie se entera hasta el primer `permission denied` en runtime**. Es la misma clase de fallo que este change vino a arreglar, un nivel más arriba.

Entonces el default privilege es la ergonomía, y la garantía es un test: recorre las tablas con `tenant_id` y falla si el rol de aplicación no tiene sobre alguna los privilegios que necesita. Hermano exacto del test introspectivo de `pg_policies` que ya existe, y con el mismo criterio — **cobertura por catálogo, no lista a mano**.

### D-4 · El rol de aplicación no tiene `DELETE`

La regla dura 3 prohíbe el borrado físico: soft delete universal, `db.delete(obj)` prohibido. Hoy eso es una convención que se sostiene con revisión de código.

No otorgar `DELETE` la convierte en una garantía de la base. Es gratis —ningún camino legítimo de la aplicación borra filas— y cubre el caso que la revisión de código no ve: el `DELETE` que llega por una inyección SQL.

Tampoco `TRUNCATE` ni `REFERENCES`.

*Escape hatch declarado*: si una tabla necesita borrado real por retención legal (`audit_logs` a los 5 años, `idempotency_keys` vencidas), el `GRANT DELETE` se otorga **en la migración de esa tabla**, nombrado y revisable en el diff. Mismo criterio que la lista `EXENTAS_DE_RLS`: una excepción que se autodetecta no es una excepción.

### D-5 · Las migraciones corren con una URL propia, y se verifica que sea la misma base

Si la aplicación se conecta con un rol sin DDL, las migraciones no pueden usar su URL. Va una variable nueva:

```
DATABASE_URL             → rol de aplicación   (la app, el worker)
DATABASE_MIGRATION_URL   → rol propietario     (alembic, y solo alembic)
```

Esto reabre un riesgo que `alembic/env.py` había cerrado a propósito: su encabezado documenta que la URL sale de `Settings` *"así que migraciones y runtime nunca apuntan a bases distintas por descuido"*. Con dos URLs, el descuido vuelve a ser posible.

Se recupera la garantía verificándola: `env.py` compara las dos URLs y **muere si difieren en host, puerto o nombre de base**. Solo puede diferir el usuario. Migrar la base equivocada es de los errores más caros que existen y no debería depender de que nadie se confunda al copiar un `.env`.

*Alternativa descartada*: derivar la URL de migración de la de aplicación sustituyendo el usuario. Menos variables, pero mete la credencial del propietario en el código o exige que las dos compartan contraseña. En staging y producción son dos secretos distintos del gestor de secretos, y así debe ser.

`ADR-013` es la tabla canónica de variables de entorno y pasa de 35 a 36. Se actualiza ahí, citando este change como origen.

### D-6 · Los tests que hacen DDL dejan de usar `sesion_de_plataforma`

Acá está el trabajo real de este change, y no es infraestructura.

`sesion_de_plataforma` **no es una puerta de administración**: es la sesión *sin contexto de tenant*, para el backoffice cross-tenant y las tareas de plataforma (`design.md` D-4 de C-02). Que hoy pueda hacer `CREATE TABLE` y `ALTER TABLE` es un accidente de que su DSN apunta a un superusuario, no una capacidad que su contrato prometa.

Tres tests se apoyan en ese accidente:

| Test | Qué DDL necesita |
|---|---|
| `test_el_filtro_explicito_acota_aunque_la_politica_no_aplique` (2.5) | apagar la política y restaurarla |
| `test_el_detector_detecta` (2.7) | `CREATE TABLE` / `DROP TABLE` |
| `tablas_sin_politica()` (helper de 2.6 y 2.7) | lectura de catálogos — ver D-7 |

Con el rol de aplicación esos tests dejan de poder correr, y **está bien que así sea**: es la prueba de que el rol quedó acotado. Se les da una puerta propia, `sesion_de_propietario`, como fixture en `tests/` y no en `app/`. En `app/` sería una función que ningún camino de producción usa y que cualquiera podría llamar; en `tests/` es exactamente lo que es: andamiaje de prueba.

**El test 2.5 además cambia de palanca, y eso no es cosmético.** Hoy neutraliza la política con `ALTER TABLE … NO FORCE`, que desactiva RLS **solo para el dueño de la tabla** — funcionaba porque la aplicación era la dueña. Con la aplicación fuera de la propiedad, `NO FORCE` no la afecta: la política le sigue aplicando y el test dejaría de medir lo que dice medir. Pasa a `DISABLE ROW LEVEL SECURITY`, que apaga RLS para todos y por lo tanto neutraliza más fuerte que antes.

Con eso el test conserva su sentido —que la capa 3 acota sola con la capa 2 apagada— y gana precisión: quien apaga es el propietario, quien consulta es la aplicación, que es la separación real del sistema.

### D-7 · La introspección de políticas corre como propietario, o deja de ver lo que debe

Esto no es una consecuencia mecánica; es un agujero que el cambio de rol destapa.

`tablas_sin_politica()` cruza `pg_class` con **`information_schema.columns`**, y esa vista **solo muestra columnas de tablas sobre las que el usuario actual tiene algún privilegio**. Ejecutada con el rol de aplicación, una tabla a la que le falte el `GRANT` simplemente **no aparece** — y el test que busca tablas sin política la daría por inexistente en vez de por descubierta.

O sea: la tabla peor configurada del esquema sería justo la invisible para el test que existe para encontrarla. Es, otra vez, la falla de `ADR-020` —un control que el catálogo da por puesto y no está— corrida un nivel.

Por eso la introspección va con el propietario. Y por eso D-3 pide un test de permisos aparte: los dos juntos cubren el hueco que cada uno deja.

### D-8 · Que el rol falte tiene que leerse como lo que es

El init corre solo al crear el volumen. Todo el que tenga el entorno levantado va a hacer `git pull` y encontrarse con que la aplicación no conecta. Sin ayuda, el síntoma es un `FATAL: password authentication failed for user "deruedas_app"` que se lee como credencial mal copiada, y la reacción natural —editar el `.env`— no arregla nada.

`tools/check-services.sh` ya existe y ya es el lugar donde se verifica que cada servicio responda. Verifica también que el rol exista y, si no está, dice literalmente qué hacer: `docker compose down -v`. Un mensaje de veinte palabras contra media hora de cada persona del equipo, una sola vez.

### D-9 · El guardián mira los atributos del rol, no solo el comportamiento

Los 5 tests que hoy fallan prueban **comportamiento**: que la política aísle sobre `platform_probe`. Cuando pasen, prueban que el aislamiento funciona hoy, en esa tabla.

No alcanza. El defecto de `ADR-020` no fue que una política estuviera mal escrita: fue que el rol la anulaba, con toda la evidencia de catálogo dando verde. Lo que puede volver es esa **clase** de fallo —un `DATABASE_URL` reapuntado, un Terraform que provisiona un rol de más, una base gestionada cuyo rol administrativo trae `BYPASSRLS`— y ninguna de esas cosas se detecta mirando `platform_probe`.

El test bloqueante mira la conexión de la aplicación y verifica tres cosas:

1. `rolsuper` y `rolbypassrls` de `current_user` son ambos falsos → el defecto exacto de `ADR-020`.
2. `current_user` **no es** el dueño de las tablas con RLS → cierra el `NO FORCE` de D-1.
3. Un `CREATE TABLE` desde la aplicación es rechazado → acredita la contención ante inyección.

Los tres son afirmaciones sobre el rol, no sobre una tabla. Sobreviven a que `platform_probe` desaparezca el día que existan tablas de negocio.

## Risks / Trade-offs

| Riesgo | Mitigación |
|---|---|
| **El default privilege no se aplica** (volumen viejo, tabla creada por otro rol, esquema nuevo) y una tabla queda sin permisos. El síntoma es un `permission denied` en runtime, lejos de la causa. | El test de D-3 recorre el catálogo y falla en CI antes de que llegue a runtime. Es la razón de que exista además del default privilege. |
| **Alguien apunta `DATABASE_URL` al propietario** para destrabar algo en local, y el aislamiento se apaga sin que nadie lo note — exactamente lo que pasó. | El test guardián de D-9 corre en CI y falla. Es el punto 4 de la decisión de `ADR-020` y la única razón por la que esto es una garantía y no una convención. |
| **Un flujo legítimo necesita `DELETE`** y se descubre tarde, con el `permission denied` en producción. | Hoy no existe: la regla dura 3 prohíbe el borrado físico. El escape hatch de D-4 está declarado y es una línea en la migración de la tabla que lo necesite. |
| **Las dos URLs se desincronizan** y las migraciones corren contra otra base. | `env.py` compara host, puerto y base, y muere si difieren (D-5). Solo puede variar el usuario. |
| **Staging y producción quedan con el rol viejo** porque Terraform es el bloque 9 de C-01, sin arrancar. | El test guardián corre contra cualquier entorno con `TEST_DATABASE_URL` apuntado ahí, y este change deja escrito qué debe provisionar Terraform. Es una dependencia real y queda anotada como tal en la ficha de C-01, no tapada. |
| **`test_migraciones.py` migra por fixture de módulo**, y `test_tenant_isolation.py` depende de que esa migración ya haya corrido — hoy funciona por orden alfabético de archivos. Al mover la migración al rol propietario esa fragilidad queda expuesta. | Se sube a un fixture de sesión en `conftest.py`, con la URL del propietario. Estaba latente antes de este change; se arregla acá porque este change la toca de todos modos. |
| **La suite de integración necesita ahora dos DSN** (`TEST_DATABASE_URL` y `TEST_DATABASE_OWNER_URL`) y correrla mal configurada da errores confusos. | Ambos con default coherente en `conftest.py`, y el CI los pasa explícitos. |

## Migration Plan

Este change no despliega nada: corrige la configuración del acceso a la base. No hay migración de datos ni ventana de indisponibilidad.

**Orden de implementación.** El bloque 1 va primero a propósito: escribe el test guardián de D-9 **antes** de crear el rol, para verlo fallar contra el defecto real. Es el RED del ciclo, y es lo que acredita que el test detecta algo. Un guardián escrito después del arreglo nunca se vio fallar y no prueba nada.

Los 5 `xfail` de C-02 son el otro extremo: se destildan **al final**, cuando el rol ya está puesto. La marca es `strict=True`, así que si el change funciona esos tests pasan y pytest convierte el fallo esperado en **error**, obligando a sacar la marca. El propio pipeline avisa cuándo corresponde el bloque 6; no hay que acordarse.

**Reversión.** Volver atrás es apuntar `DATABASE_URL` al propietario y devolver los `xfail`. El rol de más en el cluster es inofensivo. Lo que **no** se revierte con eso es el trabajo de D-6 y D-7 sobre los tests: esos cambios son correctos con cualquiera de los dos roles y no hay motivo para deshacerlos.

**Entornos.** Local y CI quedan cubiertos por este change. Staging y producción dependen del bloque 9 de C-01: hasta que exista, ningún entorno gestionado tiene el rol, y este change no puede pretender lo contrario.

## Open Questions

- **Nombre del rol de aplicación.** Se propone `deruedas_app`. Ningún documento del corpus nombra roles de base; si Terraform impone una convención al encarar el bloque 9, cambiarlo es una variable de entorno.
- **Un rol de solo lectura para reporting.** El mismo mecanismo lo soporta y en algún momento va a hacer falta. Fuera de alcance: no hay consumidor todavía y agregarlo sin caso de uso es inventar superficie.
- **Si la base gestionada del proveedor permite `NOBYPASSRLS` en el rol que crea el esquema.** RDS y Cloud SQL restringen el superusuario real y esto normalmente sale bien, pero depende del proveedor y ese está sin decidir (`IN-16`). Se verifica al encarar el bloque 9, y el test guardián es justamente lo que lo va a decir sin ambigüedad.

> **Lo que NO es una pregunta abierta**: si el rol de aplicación debe tener `DELETE`. La regla dura 3 lo responde, y D-4 lo implementa.
