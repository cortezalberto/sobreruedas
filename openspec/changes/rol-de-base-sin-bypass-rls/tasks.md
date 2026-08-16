# Tareas — `rol-de-base-sin-bypass-rls`

> **Gobernanza CRÍTICA.** Esto es la capa 2 del aislamiento multi-tenant, que el plan de seguridad llama *"el control más crítico del sistema"*. Implementación aprobada por el usuario el 16-ago-2026; el rol de aplicación se llama **`mitutu`**.
>
> **TDD estricto.** El bloque 1 es el RED de todo el change: el test guardián se escribió y se **vio fallar** contra el defecto real antes de crear el rol. Un guardián escrito después del arreglo nunca se vio fallar y no prueba nada.
>
> **Sin mocks de base** (regla dura 8). Todo lo de acá se probó contra PostgreSQL real.
>
> Decisiones en [`design.md`](design.md) · Diagnóstico en [`ADR-020`](../../../docs/adr/ADR-020-rol-de-conexion-sin-bypass-de-rls.md)

## 1. RED — el guardián, antes del arreglo · D-9

- [x] 1.1 Escribir `tests/integration/test_rol_de_conexion.py` con el test de que `rolsuper` y `rolbypassrls` del `current_user` de la aplicación son ambos falsos
- [x] 1.2 Escribir el test de que el `current_user` de la aplicación **no es** el dueño de las tablas con RLS activo, consultando `pg_class.relowner` (cierra el `ALTER TABLE … NO FORCE` de D-1)
- [x] 1.3 Escribir el test de que un `CREATE TABLE` desde la sesión de aplicación es rechazado por permisos
- [x] 1.4 Correr los tres contra el entorno actual y **verificar que fallan** — los tres fallaron, cada uno por su motivo exacto:
      `rolsuper=t` · `es DUENA de ['platform_probe']` · `DID NOT RAISE`
- [x] 1.5 Verificar que los tres afirman sobre el **rol** y no sobre `platform_probe`, de modo que sigan valiendo el día que esa tabla se retire (D-9)

> **Defecto propio, encontrado al ver el RED**: 1.3 usaba `pytest.raises`, así que cuando el DDL funcionaba —o sea, cuando el test falla— la tabla quedaba **creada y commiteada** en la base. Se reescribió para poder limpiar el residuo antes de reportar el fallo.

## 2. El rol en la infraestructura · D-1, D-2

- [x] 2.1 Escribir `infra/local/postgres/init/02-rol-de-aplicacion.sh` creando el rol con `NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT LOGIN`, tomando `APP_DB_USER` y `APP_DB_PASSWORD` del entorno con defaults de desarrollo
- [x] 2.2 Otorgar en ese mismo init `USAGE ON SCHEMA public` al rol de aplicación, y `REVOKE CREATE ON SCHEMA public FROM PUBLIC` — verificado por el test 1.3
- [x] 2.3 Verificar que el script es agnóstico del nombre del propietario: **verificado en los dos compose**, `deruedas` en desarrollo y `deruedas_test` en el de tests, con el mismo archivo
- [x] 2.4 Encabezar el script con la misma advertencia que `01-extensions.sql`: corre **una sola vez**, al crear el volumen
- [x] 2.5 Declarar `APP_DB_USER` y `APP_DB_PASSWORD` en el servicio `postgres` de `docker-compose.yml` y de `docker-compose.test.yml`, con defaults de desarrollo
- [x] 2.6 Apuntar el `DATABASE_URL` de los servicios `backend` y `worker` al rol de aplicación en `docker-compose.yml`

## 3. Permisos y su verificación · D-3, D-4

- [x] 3.1 Agregar al init el `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES` — **sin `FOR ROLE`**, para que aplique al propietario que ejecuta y no dependa de su nombre (D-3)
- [x] 3.2 Agregar el default privilege de `USAGE ON SEQUENCES`
- [x] 3.3 Escribir el test que recorre por catálogo las tablas con `tenant_id` y falla si al rol de aplicación le falta `SELECT`, `INSERT` o `UPDATE` sobre alguna
- [x] 3.4 Escribir el test de que el rol de aplicación **no** tiene `DELETE` ni `TRUNCATE`, y que un `DELETE` real es rechazado con `42501` (D-4, regla dura 3). Verificado en el catálogo: `mitutu=arw/deruedas` — sin `d`
- [x] 3.5 Escribir el test de que el default privilege **alcanza a una tabla nueva** sin `GRANT` explícito — probar el mecanismo, no solo confiar en él
- [ ] ~~3.6 Otorgar en la migración `002` los permisos de `platform_probe` para volúmenes creados antes del default privilege~~
      **Descartada: la premisa era falsa.** Un volumen anterior a este change no tiene el rol `mitutu` en absoluto —lo crea el init—, así que ningún `GRANT` puede alcanzarlo: el único camino es recrear el volumen, que es lo que cubren D-8 y el bloque 8. Y meter el nombre del rol en una migración ataría el esquema a un nombre que elige la infraestructura, no el esquema (ver *Open Questions* del design). Lo que esta tarea buscaba cubrir de verdad —staging y producción— quedó en la tarea 9.2 y en el bloque 9 de C-01.
- [x] 3.7 Documentar el escape hatch de `DELETE` junto a la lista de permisos, con el mismo criterio declarativo que `EXENTAS_DE_RLS`

## 4. Las migraciones con el rol propietario · D-5

- [x] 4.1 Escribir el test de que migrar con la URL del rol de **aplicación** falla por permisos, y con la del propietario funciona
- [x] 4.2 Agregar `DATABASE_MIGRATION_URL` a `DatabaseSettings` como `SecretStr | None`, con la misma validación de forma de DSN que `url`
- [x] 4.3 Escribir el test de que `alembic/env.py` **muere** si las dos URLs difieren en host, puerto o base, y de que el mensaje no incluye las URLs (llevan credenciales)
- [x] 4.4 Implementar esa verificación en `env.py`, actualizando su encabezado: la garantía de "migraciones y runtime nunca apuntan a bases distintas" ahora se **verifica** en vez de derivarse de usar una sola variable
- [x] 4.5 Registrar `DATABASE_MIGRATION_URL` en [`ADR-013`](../../../docs/adr/ADR-013-variables-de-entorno.md): 35 → **36 variables**, 15 → **16 sensibles**, citando `ADR-020`. `tools/check-config-parity.py` da **0 divergencias**
- [x] 4.6 Actualizar `.env.example` con las dos URLs y la nota de por qué son dos
- [x] 4.7 Verificar el target de migración del `Makefile` — **no requiere cambio**: corre alembic dentro del servicio `backend`, que ya recibe las dos URLs, y `env.py` elige la correcta

## 5. Los tests recuperan su puerta de DDL · D-6

- [x] 5.1 Crear `tests/integration/soporte.py` con los dos DSN y `sesion_de_propietario`, **en `tests/` y no en `app/`**
- [x] 5.2 Migrar el test 2.5 al propietario para apagar la política, dejando la consulta en la aplicación
- [x] 5.3 Migrar `test_el_detector_detecta` (2.7) a que el `CREATE TABLE` / `DROP TABLE` vaya por el propietario
- [x] 5.4 Mover `tablas_sin_politica()` al propietario y dejar escrito **por qué** en el docstring (D-7)
- [x] 5.5 Escribir el test que acredita ese hueco: una tabla sin `GRANT` **no aparece** en `information_schema.columns` consultada como aplicación, y **sí** como propietario
- [x] 5.6 Subir la migración a un fixture de **sesión** en `tests/integration/conftest.py`, con la URL del propietario — antes era de módulo y `test_tenant_isolation.py` dependía de él por orden alfabético de archivos
- [x] 5.7 Verificar que el fixture nuevo no rompe el aislamiento de event loops que `engines_limpios` protege (que además dejó de estar duplicado en dos archivos)

> **Hallazgo al correr**: el test 2.5 apagaba la política con `ALTER TABLE … NO FORCE`, que desactiva RLS **solo para el dueño**. Con la aplicación fuera de la propiedad, esa palanca dejó de neutralizar nada y el test medía otra cosa. Pasa a `DISABLE ROW LEVEL SECURITY`, que apaga RLS para todos — neutralización más fuerte que la anterior. Corregido también en `design.md` D-6.

## 6. CI · D-2, D-9

- [x] 6.1 Pasar `TEST_DATABASE_URL` (aplicación) y `TEST_DATABASE_OWNER_URL` (propietario) en el paso de pytest del job `test-backend-integration`
- [x] 6.2 Verificar que el init del rol corre en el compose de tests sin agregar un paso al workflow — verificado levantando `docker-compose.test.yml`: rol `mitutu` creado, otorgante `deruedas_test`
- [x] 6.3 Pasar las dos variables también al paso que mide la cobertura de la base
- [ ] 6.4 Correr el pipeline entero y verificar que el guardián pasa en CI — **requiere push**, no se puede acreditar localmente

## 7. Cierre del fallo esperado · C-02, bloque 2

- [x] 7.1 Correr la suite y verificar que los 5 tests marcados dan **ERROR por `xfail` estricto que pasó** — los 5 dieron `XPASS(strict)`, que es exactamente la señal
- [x] 7.2 Quitar la marca `SIN_AISLAMIENTO_REAL` de los 5 tests y borrar su definición y el bloque de comentario
- [x] 7.3 Quitar la advertencia del bloque 2 de `core-backend-primitives/tasks.md`
- [x] 7.4 Actualizar el docstring de `test_la_tabla_testigo_tiene_force_activo`
- [x] 7.5 Revisar el encabezado de la migración `002`: su advertencia sobre `FORCE` sigue valiendo, pero por otro motivo — ahora cubre a las migraciones y a las tareas de plataforma
- [x] 7.6 Correr la suite completa: **35 tests de integración pasan sin marca alguna**

## 8. Ergonomía local · D-8

- [x] 8.1 Agregar a `tools/check-services.sh` la verificación de que el rol existe y no tiene `rolbypassrls`
- [x] 8.2 Hacer que, cuando el rol falta, diga literalmente `docker compose down -v`. Detector probado en sus **tres** estados: rol sano, rol que puede saltear RLS, y rol ausente
- [ ] 8.3 Escribir el test de ese chequeo en `tools/tests/` — **no hecho**: `tools/tests/` solo tiene tests de scripts Python y no hay armado para probar shell; hacerlo bien pide mockear `docker compose`. El detector se verificó a mano en sus tres estados (8.2). Queda como deuda declarada, no como cubierto.
- [x] 8.4 Documentar en el `README.md` que este change exige recrear el volumen local, y por qué

## 9. Cierre

- [x] 9.1 Escribir el delta de `platform/tenant-isolation` en `specs/` — 3 requisitos, 9 escenarios. `openspec validate --strict` pasa
- [x] 9.2 Anotar en el bloque 9 de C-01 que Terraform debe provisionar **los dos roles** (tareas 9.2.b y 9.2.c), y que el guardián es lo que lo va a verificar contra el entorno gestionado
- [x] 9.3 Verificar cobertura contra [`ADR-014`](../../../docs/adr/ADR-014-umbrales-de-cobertura.md): **98.83 % líneas · 95.45 % ramas**, sin decrecimiento
- [x] 9.4 Verificar `ruff`, `black` y `mypy --strict` — los tres en verde
- [x] 9.5 Dejar registrado en `ADR-020` que la fricción de mantener `GRANT` por tabla quedó resuelta por default privileges, y no como el ADR la había asumido

---

### Efecto colateral corregido

`tests/unit/test_secretos_no_se_exponen.py` derivaba los secretos del modelo (bien) pero tenía a `DATABASE_URL` como **excepción escrita a mano**, porque necesita forma de DSN. Al aparecer el segundo secreto con forma de DSN, ese test se rompió. Se generalizó por sufijo `_URL` en vez de agregar una segunda excepción, y de paso la comprobación de fuga pasó a buscar el **marcador** en vez del valor entero — que detecta también el caso de que se filtre solo la contraseña.
