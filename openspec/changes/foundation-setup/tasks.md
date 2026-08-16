# Tareas — `foundation-setup` (C-01)

> **Governance: ALTO.** Se propone y se espera revisión humana antes de escribir código.
> Cobertura de tests aplicable desde el primer commit: **80 % líneas / 60 % ramas** (ver `design.md` D-3).
> Mapeo a las tareas del plan: `T-001` … `T-008`.

## 1. Reubicación documental y siembra de ADRs

Precede a todo lo demás: el §4.1 no se puede materializar mientras `docs/` esté ocupado por el corpus fuente.

- [x] 1.1 Mover los 11 documentos de `docs/*.md` a `docs/sdd/` con `git mv` (preserva historial)
- [x] 1.2 Mover todo el contenido de `decisions/` a `docs/adr/` con `git mv` (`ADR-000`, `ADR-015`, `ADR-016`, `ADR-017` y la enmienda `E-001`) y eliminar el directorio vacío
- [x] 1.3 Actualizar los enlaces a `docs/` en los 16 archivos de `knowledge-base/`
- [x] 1.4 Actualizar los enlaces a `docs/` y a `decisions/` en `CLAUDE.md`, `AGENTS.md` y `CHANGES.md`
- [x] 1.5 Corregir en `CHANGES.md` la referencia a `frontend/`, que en el §4.1 es `frontend-web/`
- [x] 1.6 Verificar automáticamente que no queda ningún enlace markdown roto en el repositorio
- [x] 1.7 Escribir `docs/adr/ADR-013-variables-de-entorno.md` con la tabla canónica de `design.md` D-2 (cierra `R-3` / `PA-06`)
- [x] 1.8 Escribir `docs/adr/ADR-014-umbrales-de-cobertura.md` registrando 80 % líneas / 60 % ramas y la enmienda al plan de testing (cierra `IN-22`)
- [x] 1.9 Corregir las anclas divergentes de `ADR-002`, `ADR-005` y `ADR-011` según `design.md` D-4 (cierra `IN-29`)
  > **Desvío deliberado.** La tarea pedía editar `docs/sdd/deRuedas-plan-implementacion.md`, pero eso rompe la inmutabilidad del corpus fuente (`CLAUDE.md`) y el precedente de `ADR-016`. Se resolvió con [`ADR-018`](../../../docs/adr/ADR-018-anclas-de-adr-del-plan-de-implementacion.md) como registro normativo **más** una anotación delimitada al pie del índice §7.2 del plan, que no altera ni una palabra del texto original. Aprobado por el Tech Lead el 13-ago-2026.
- [x] 1.10 Corregir `ENVIRONMENT` → `APP_ENV` en la tabla de `knowledge-base/08_arquitectura_propuesta.md`

## 2. Estructura del monorepo — `T-001`

- [x] 2.1 Crear el árbol completo del §4.1 con `.gitkeep` en los directorios vacíos
- [x] 2.2 Escribir el `README.md` raíz: descripción, enlaces al cuerpo SDD y cómo levantar el entorno
- [x] 2.3 Extender el `.gitignore` para Python (`__pycache__`, `.venv`, `.pytest_cache`), Node (`node_modules`, `.next`), entornos (`.env`, `.env.local`) e IDEs
- [x] 2.4 Escribir `.env.example` con las ~34 variables de `ADR-013`, valores ficticios y comentarios — sin un solo valor real
- [x] 2.5 Verificar el árbol con `tree -L 3` contra el §4.1, entrada por entrada

## 3. Entorno local — `T-002`

- [x] 3.1 Escribir `docker-compose.yml` con `postgres`, `redis`, `opensearch`, `keycloak`, `minio`, `mailhog`, `backend`, `worker` y `frontend-web`
- [x] 3.2 Configurar el init de PostgreSQL 16 habilitando `pgcrypto`, `pg_trgm`, `postgis` y `uuid-ossp`
- [x] 3.3 Versionar el archivo de importación del realm `deruedas-dev` de Keycloak
- [x] 3.4 Configurar la creación automática del bucket `deruedas-media` en MinIO al arrancar
- [x] 3.5 Definir volúmenes nombrados (`pg_data`, `redis_data`, `minio_data`) y las redes `default` y `observability`
- [x] 3.6 Escribir `backend/Dockerfile` y `frontend-web/Dockerfile` con hot-reload por volume mount
- [x] 3.7 Escribir `docker-compose.test.yml` con servicios efímeros, sin volúmenes persistentes
- [x] 3.8 Escribir `tools/check-services.sh` que pingea cada servicio y reporta OK/FAIL
- [x] 3.9 Verificar que `docker compose up -d` deja todos los servicios `healthy` en menos de tres minutos
  > **Verificado el 13-ago-2026 con Docker 29.4.0.** Arranque en frío hasta los 6 servicios `healthy` más el bucket creado: **99 s** contra un presupuesto de 180 s. Los criterios de done de `T-002` se comprobaron uno por uno: extensiones `pgcrypto` 1.3, `pg_trgm` 1.6, `postgis` 3.4.3 y `uuid-ossp` 1.1 presentes; realm `deruedas-dev` publicando su configuración OIDC; bucket `deruedas-media` creado al arrancar. `tools/check-services.sh` da 0 fallas, y se validó contra servicios caídos a propósito: reporta `[FAIL]` con detalle y sale con código 1.
  >
  > **Alcance de lo verificado**: los **6 servicios de infraestructura**. `backend`, `worker` y `frontend-web` no se pueden construir todavía —les falta `pyproject.toml` (`T-005`) y `package.json` (`T-006`)— así que el criterio *"todos los servicios"* de `T-002` no es alcanzable en el orden en que el plan ordena las tareas. Se completa al cerrar los bloques 5 y 7.
  >
  > **Dos defectos reales encontrados y corregidos al levantarlo**, ninguno visible por inspección: `postgres:16-alpine` **no trae PostGIS** (se pasó a `postgis/postgis:16-3.4-alpine`), y Keycloak **rechaza campos desconocidos** en el JSON del realm, así que la clave `_comentario` hacía fallar el arranque entero (la documentación se movió a `infra/local/keycloak/README.md`).
  >
  > **Puertos del host configurables**: `5432` estaba ocupado por un contenedor de otro proyecto en esta máquina. Los mapeos pasaron a `${VAR:-default}`, manteniendo los defaults que pide `T-002`. La verificación corrió con `POSTGRES_PORT=5442`, así que el criterio literal *"Postgres accesible en localhost:5432"* no se pudo comprobar en esta máquina — lo impide un factor externo, no el compose.

## 4. Contrato de configuración — `T-004`

Cubre la capability `platform/configuration`. Los tests van primero.

- [x] 4.1 Escribir los tests de validación de tipos y defaults de `Settings`
- [x] 4.2 Escribir los tests de fallo temprano: variable obligatoria ausente y valor con tipo inválido, verificando que el error **nombra la variable**
- [x] 4.3 Escribir los tests de enmascarado de secretos en serialización, `repr` y mensajes de error
- [x] 4.4 Escribir el test de rechazo de `APP_ENV` fuera de `local | ci | staging | production`
- [x] 4.5 Implementar `backend/app/config.py` con Pydantic Settings v2 y los grupos de `design.md` D-2
- [x] 4.6 Implementar la validación al arranque con muerte temprana y mensaje que nombra la variable
- [x] 4.7 Implementar el enmascarado de campos sensibles y el singleton `get_settings()` cacheado
- [x] 4.8 Verificar que `.env.example` y los grupos de `Settings` cubren exactamente el mismo conjunto de variables
  > Automatizado en [`tools/check-config-parity.py`](../../../tools/check-config-parity.py), que cruza **tres** fuentes: `ADR-013` (35), `.env.example` (35) y `Settings` (32). La diferencia de 3 es el bloque `Frontend`, excluido de forma explícita porque lo lee Next.js. Además verifica que **toda variable marcada sensible en `ADR-013` sea `SecretStr`** en `Settings`: declararla no alcanza, si no es `SecretStr` se filtra por `repr` y el enmascarado es decorativo. Validado contra divergencias inyectadas a propósito.
  >
  > **Nota sobre `pyproject.toml`**: está en el árbol del §4.1 pero ninguna tarea `T-XXX` lo declara — ni `T-004` ni `T-005` lo nombran. Se atribuyó a `T-001`, dueña de la estructura, y se creó acá porque sin él no hay forma de correr un test.

> **Evidencia del ciclo TDD** — `pytest` corre en el contenedor con **Python 3.12.14** (`ADR-003`), no con el 3.14 del host.
>
> | Tarea | Archivo de test | Capa | RED | GREEN | TRIANGULACIÓN | REFACTOR |
> |---|---|---|---|---|---|---|
> | 4.1 | `tests/unit/test_config.py` | Unit | ✅ `ModuleNotFoundError: app.config` | ✅ | ✅ 5 defaults parametrizados + coerción de tipos | ✅ `black` |
> | 4.2 | ídem | Unit | ✅ | ✅ | ✅ falta 1 variable, faltan 2, tipo inválido | ✅ |
> | 4.3 | ídem | Unit | ✅ | ✅ | ✅ `repr`, `str`, `model_dump`, JSON, mensaje de error | ✅ |
> | 4.4 | ídem | Unit | ✅ | ✅ | ✅ los 4 válidos + 5 inválidos + `is_production` | ✅ |
>
> **Resultado: 37 tests, 100 % de líneas y de ramas** sobre `app/config.py` (umbral de `ADR-014`: 80/60). `ruff`, `black --check` y `mypy --strict` en verde.
>
> **Un test estaba mal y se corrigió en RED**: comparaba `DATABASE_URL` en claro, pero `ADR-013` la marca sensible — tiene que ser `SecretStr`. El test habría forzado una implementación que filtra la credencial.

## 5. Bootstrap del backend — `T-005`

Cubre la capability `platform/service-health`. Los tests van primero.

- [x] 5.1 Escribir los tests de la sonda de vida: respuesta exitosa, presencia de versión y marca temporal, acceso sin credenciales
- [x] 5.2 Escribir los tests de la sonda de disponibilidad en condiciones normales y degradadas, incluida la recuperación sin reinicio
- [x] 5.3 Escribir los tests de correlación de peticiones: identificador generado y provisto por el cliente
- [x] 5.4 Escribir el test de que la documentación interactiva no se sirve con `APP_ENV=production`
- [x] 5.5 Implementar `backend/app/main.py`: aplicación, middleware de CORS y GZip, lifespan asíncrono
- [x] 5.6 Implementar el middleware de identificador de correlación
- [x] 5.7 Implementar las sondas de vida y disponibilidad
- [x] 5.8 Implementar los handlers de excepción globales y el gate de documentación por ambiente
- [x] 5.9 Verificar que el servicio arranca y que detener Redis alterna la sonda de disponibilidad y la restablece
  > **Verificado el 13-ago-2026 contra el entorno real**, no solo con tests:
  >
  > ```
  > /health                    200  {"status":"alive","version":"0.1.0","timestamp":"..."}
  > /ready  (todo arriba)      200  {"status":"ready",...}
  > docker compose stop redis
  > /ready                     503  {"status":"not_ready","failed":["redis"],...}
  > /health  mientras tanto    200   <- la sonda de vida ignora dependencias
  > docker compose start redis
  > /ready                     200  {"status":"ready",...}
  > backend: Up 25 seconds     <- NO se reinicio
  > ```
  >
  > Correlación verificada en vivo: identificador provisto por el cliente devuelto sin modificar, generado cuando no viene, y presente en el log — `INFO [mi-id-de-prueba] app.request: GET /health (0.5 ms)`. `/docs` responde 200 con `APP_ENV=local`. Un 404 sale en `application/problem+json`.
  >
  > **El contrato de configuración del bloque 4 encontró un defecto del bloque 3**: el servicio `backend` del compose no pasaba `TENANT_SECRETS_MASTER_KEY`, que es obligatoria. El proceso murió al arrancar nombrando la variable, exactamente como `T-004` especifica. Corregido en `docker-compose.yml` para `backend` y `worker`.
  >
  > **Dos correcciones más en `tools/check-services.sh`**: tenía los puertos del host hardcodeados y no leía los overrides del compose — con `BACKEND_PORT=8010`, verificaba `localhost:8000`, donde en esta máquina responde **otra aplicación entera**. Y reportaba el `worker` como `FAIL` cuando en realidad no puede arrancar hasta que exista `app/core/events.py` (`T-016`); ahora es `PENDIENTE`.

> **Evidencia del ciclo TDD** — `pytest` en el contenedor con Python 3.12.14.
>
> | Tarea | Archivo de test | Capa | RED | GREEN | TRIANGULACIÓN | REFACTOR |
> |---|---|---|---|---|---|---|
> | 5.1 | `tests/unit/test_app_health.py` | Unit | ✅ `ModuleNotFoundError: app.main` | ✅ | ✅ éxito, versión y marca temporal, dependencias caídas, sin credenciales | ✅ `black` |
> | 5.2 | ídem | Unit | ✅ | ✅ | ✅ normal, degradada por cada dependencia, todas a la vez, recuperación | ✅ |
> | 5.3 | ídem | Unit | ✅ | ✅ | ✅ generado, único por petición, reutilizado, presente en el log | ✅ |
> | 5.4 | ídem | Unit | ✅ | ✅ | ✅ los 3 ambientes no productivos + producción sobre `/docs`, `/redoc` y `/openapi.json` | ✅ |
> | 5.7 | `tests/integration/test_app_health.py` | Integración | ✅ | ✅ | ✅ PostgreSQL y Redis **reales**, sin mocks (regla dura 8) | ✅ |
>
> **Resultado: 60 tests unitarios + 6 de integración. Cobertura 96.85 %** de líneas y de ramas (umbral de `ADR-014`: 80/60). `ruff`, `black --check` y `mypy --strict` en verde.
>
> Las 8 líneas sin cubrir de `main.py` son las sondas reales, que por diseño solo ejercitan los tests de integración — esos corren en su propio job (`8.6`) y no en la corrida unitaria.
>
> **Dos hallazgos del ciclo:**
> - **La app no se construye al importar el módulo.** Había un `app = create_app()` de nivel de módulo, así que importar `app.main` —para un test, una herramienta o leer un docstring— exigía un entorno válido. La muerte temprana corresponde al arrancar el **proceso**, no al importar. Se pasó a `uvicorn app.main:create_app --factory`.
> - **`from __future__ import annotations` rompe los modelos Pydantic locales.** Las anotaciones quedan como cadenas y FastAPI las resuelve con `get_type_hints()` contra los globals del módulo; un modelo definido dentro de una función de test no está ahí. Los modelos de prueba van a nivel de módulo.

## 6. Alembic — `T-007`

- [x] 6.1 Escribir `backend/alembic.ini` con `script_location`, `file_template` (`NNN_descripcion.py`) y timezone
- [x] 6.2 Escribir `alembic/env.py` leyendo la Base declarativa y la configuración desde `Settings`
- [x] 6.3 Crear la migración baseline `000_baseline.py` vacía
- [x] 6.4 Agregar los objetivos `make migrate` y `make migrate-down-one`
- [x] 6.5 Verificar `upgrade head` sobre base limpia y `downgrade base` en sentido inverso
  > **Verificado el 13-ago-2026 contra PostgreSQL real**, no en seco:
  >
  > ```
  > alembic upgrade head      Running upgrade -> 000, baseline
  > alembic current           000 (head)
  > SELECT version_num        000
  > alembic downgrade base    Running downgrade 000 -> , baseline
  > SELECT count(*)           0
  > make migrate / make migrate-down-one   ambos OK
  > make migration name=agrega_vehiculos   -> 001_agrega_vehiculos.py, Revises: 000
  > ```

> **Dos defectos del plan, declarados y no tapados**
>
> **`T-007` depende de un artefacto de otro change.** Su especificación pide que `env.py` importe *"la Base declarativa de `db/base.py`"*, pero ese archivo lo crea **`T-010`, que cae en C-02**. `T-007` declara depender de `T-002` y `T-005`, no de `T-010`: es una inversión de dependencia.
> **Resolución**: `env.py` intenta el import y, si falta, deja `target_metadata = None` con un aviso **ruidoso** por `stderr`. Alcanza para C-01, cuya única migración es la baseline vacía, y el día que `T-010` aterrice `autogenerate` funciona sin tocar el archivo. El aviso es a gritos a propósito: un `autogenerate` silencioso contra `None` produce migraciones vacías sin avisar, y eso se descubre en producción.
>
> **`T-007` exige `make migrate` pero el §4.1 no tiene `Makefile`.** No lleva ADR, y la distinción importa: `infra/local/` (ADR-019) era una **elección entre alternativas**; acá el propio plan, en el mismo documento, manda el comando. Es una inconsistencia interna de N2, no un desvío elegido. Es el mismo patrón que `backend/pyproject.toml`, que tampoco lo reclama ninguna tarea.

> **Notas de implementación**
>
> - **La URL de la base NO va en `alembic.ini`.** Sale de `Settings`, igual que la aplicación. Escribirla en el `.ini` la versionaría con la contraseña adentro (Art. 3), y además garantiza que migraciones y runtime nunca apunten a bases distintas por descuido.
> - **Motor asíncrono** con la receta oficial de Alembic (`run_sync` sobre un engine async). La alternativa era agregar un driver sincrónico solo para migrar: una segunda ruta de conexión a la base que nadie ejercita en producción.
> - **Revisiones correlativas `NNN`, no hashes.** Con una revisión por PR, el orden se lee del `ls` y un conflicto sobre el mismo número salta en el diff en lugar de producir dos cabezas silenciosas. `make migration name=...` calcula el siguiente número solo.
> - **Gotcha de `ruff`**: existe un directorio `backend/alembic/`, así que isort infería que `alembic` era módulo propio del proyecto y quería agruparlo con `app`. Se declaró `known-third-party` en la config, no con un `noqa`.

## 7. Bootstrap del frontend web — `T-006`

- [x] 7.1 Inicializar `frontend-web/` con Next.js 14+ y App Router
- [x] 7.2 Configurar TypeScript con `strict`, `noImplicitAny` y `noUncheckedIndexedAccess`
- [x] 7.3 Configurar Tailwind con la paleta por defecto y el punto de extensión marcado `TODO(C-07)`
- [x] 7.4 Configurar los alias de rutas `@/components`, `@/lib` y `@/hooks`
- [x] 7.5 Configurar ESLint con `next/core-web-vitals` más `jsx-a11y`, y Prettier compartido
- [x] 7.6 Escribir el layout raíz con metadatos y la página home placeholder
- [x] 7.7 Verificar `npm run dev`, `npm run build` y `tsc --noEmit` sin errores
  > **Verificado el 14-ago-2026.** `tsc --noEmit` sin errores · `eslint .` 0 errores y 0 warnings · `prettier --check` limpio · `npm run build` produce build de producción (123 s, rutas `/` y `/_not-found` estáticas) · `npm run dev` sirviendo **HTTP 200 en 67 ms** desde el contenedor, `healthy`. Página verificada: `lang="es-AR"`, `robots: noindex, nofollow`, `og:locale: es_AR`.
  >
  > Los alias `@/lib`, `@/hooks` y `@/components` se comprobaron con módulos de prueba temporales que `tsc` resolvió; se eliminaron después. Configurar un alias no es lo mismo que probar que resuelve.

> **Subida de Next 14 a 16.3.1 — forzada por seguridad**
>
> Con `next@14.2.5`, `npm audit` reportaba **5 vulnerabilidades altas** con **21 advisories** contra Next: SSRF, XSS en App Router, cache poisoning, HTTP request smuggling y varios DoS. La tarea 8.5 hace que `npm audit` **bloquee el merge** en severidad alta, así que quedarse en 14 era arrancar con el pipeline en rojo por diseño.
>
> El rango vulnerable llega hasta `16.3.0-preview.10`; **`16.3.1` es la versión que lo cierra**. No es un desvío: el stack declara *"Next.js **14+**"* y 16 está dentro. Arrastra `react` 19, `eslint` 9 y la migración de `.eslintrc.json` a **flat config**.
>
> Resultado: `npm audit` → **0 vulnerabilidades**.

> **Tres defectos de los Dockerfiles del bloque 3, encontrados al construir**
>
> 1. **Faltaban los `.dockerignore`.** `COPY . .` intentaba copiar `node_modules` y el build moría con `invalid file request node_modules/.bin/acorn` — symlinks que el contexto de build no resuelve desde un montaje de Windows. Y aunque funcionara estaría mal: esos binarios se compilan para la plataforma del host. Se agregaron para `frontend-web/` y `backend/`.
> 2. **Volumen anónimo con dueño equivocado.** El compose monta `/app/.next`, y Docker inicializa el volumen con el dueño que ese directorio tenga **en la imagen**. Como no existía al construir, nacía de root y el proceso —que corre como `node`— moría con `EACCES` al primer `mkdir`. Se crean los directorios en la imagen antes del `chown`.
> 3. **Archivos root dentro del bind mount.** Correr un contenedor descartable como root contra el montaje deja archivos `root:root 644` que el usuario `node` después no puede escribir (`next-env.d.ts`, `package-lock.json`). Los que vienen del host Windows aparecen `777`; los que crea root adentro, no. **Los contenedores descartables sobre el bind mount deben correr con `--user 1000:1000`.**

> **Fuera de alcance, declarado**
>
> `T-006` pide además que la home *"redirija a `/login` si no hay sesión"*. **No se implementa**: no existe ni el mecanismo de sesión ni la ruta `/login`. La autenticación se delega enteramente a Keycloak (`ADR-007`) y su integración con NextAuth es **C-05**. La tarea 7.6 de este change ya lo había dejado afuera. Un redirect a una ruta inexistente es un 404 disfrazado de feature.
>
> La paleta de Tailwind queda en la de por defecto con el punto de extensión marcado `TODO(C-07)`: los primitivos del design system no están en ninguno de los 11 documentos fuente (riesgo `R-4`).

## 8. Pipeline de integración — `T-003`

Cubre la capability `platform/delivery-pipeline`.

- [x] 8.1 Escribir `.github/workflows/ci.yml` con los seis jobs de `design.md` D-6
- [x] 8.2 Configurar el gate de cobertura al **80 % de líneas y 60 % de ramas**, con fallo bloqueante
- [x] 8.3 Configurar las exclusiones de cobertura para archivos de scaffolding sin lógica, de forma explícita y auditable
- [x] 8.4 Configurar la comprobación de que la cobertura no decrece respecto de `main`
- [x] 8.5 Configurar el job de seguridad: `pip-audit`, `npm audit` y `gitleaks`, bloqueante en alta o crítica y ante cualquier secreto
- [x] 8.6 Configurar el job de integración levantando `docker-compose.test.yml`
- [x] 8.7 Configurar la caché de dependencias de `pip` y `npm`
- [x] 8.8 Verificar con una propuesta de cambio de prueba: pasa en verde en menos de 15 minutos
- [x] 8.9 Verificar que un test que falla y una cobertura insuficiente bloquean efectivamente la integración

> **`fail_under` no implementaba el umbral de ADR-014, y esa es la razón de ser de este bloque.**
>
> Con `branch = true`, el número que compara `fail_under` es
> `(líneas cubiertas + ramas cubiertas) / (sentencias + ramas)` — un promedio
> ponderado. ADR-014 pide **80 % de líneas Y 60 % de ramas, cada uno por su
> lado**. Un módulo con 95 % de líneas y 20 % de ramas da 82,14 % combinado y
> pasaba el `fail_under = 80` sin que nadie se enterara: exactamente la forma en
> que la lógica condicional entra sin tests.
>
> El gate real es `tools/check-coverage.py`, con **19 tests en TDD estricto**
> (`tools/tests/test_check_coverage.py`). `fail_under = 80` queda en
> `pyproject.toml` como red de contención para quien corra `pytest --cov` a mano.
>
> Distingue código 1 (umbral incumplido → faltan tests) de código 2 (no se pudo
> medir → pipeline roto). Confundirlos manda a buscar tests que no faltan.

> **Verificado contra una salida genuina de `coverage json`**, no solo con los
> JSON sintéticos de los tests: las claves `covered_lines`, `num_statements`,
> `num_branches` y `covered_branches` existen y tienen la forma asumida
> (coverage 7.14.1). Era el riesgo real de un verificador probado solo con
> diccionarios escritos a mano.

> **Tarea 8.4 — el costo del no decrecimiento, dicho de frente.** La base se
> mide en un `git worktree` del commit base, reusando las dependencias ya
> instaladas de la rama en vez de reinstalar el entorno de `main`. Duplicar el
> job por una diferencia de dependencias que casi nunca existe no se paga. Si la
> base no se puede medir, **no bloquea**: se reporta "sin base". Ausencia de
> base no es evidencia de retroceso, y la primera corrida nunca tiene contra qué
> comparar.

> **Tarea 8.5 — dos desvíos deliberados de D-6.** `pip-audit` **no expone la
> severidad** de cada hallazgo, así que bloquea ante *cualquier* vulnerabilidad:
> es más estricto que el "alta o crítica" que pide D-6. Filtrar por una
> severidad que la herramienta no reporta exigiría mantener una lista a mano.
> `npm audit --audit-level=high` sí distingue y hace literalmente lo pedido.
> `gitleaks` va con versión fijada (`v8.28.0`) y `--redact`: un escáner en
> `latest` hace que el mismo commit pase hoy y falle mañana, y un hallazgo sin
> redactar imprime el secreto en un log que queda guardado — detectar la fuga la
> empeoraría.

> **Tarea 8.6 — la tensión testcontainers vs compose, resuelta.** La regla dura 8
> del proyecto manda testcontainers; la tarea 8.6 pide `docker-compose.test.yml`.
> No hay conflicto real: lo que la regla prohíbe son los **mocks de base de
> datos**, y el compose de tests levanta PostgreSQL con PostGIS, Redis,
> OpenSearch y MinIO de verdad. Se usa el compose porque **ya existe desde
> `T-002` y es el mismo que se usa en local**; duplicar la definición de
> servicios adentro del workflow es la forma clásica de que CI y local se
> desincronicen. Los tests ya leían las direcciones de
> `TEST_DATABASE_URL`/`TEST_REDIS_URL`, así que corren en el runner contra los
> puertos publicados (5433 y 6380) sin tocar una línea.

> ### ✅ Tarea 8.8 — verde en el pipeline real, y las cuatro corridas que costó
>
> El pipeline nunca había corrido. `ci.yml` dispara en `pull_request → main` y
> `push → main`, así que ningún push a la rama de trabajo lo activaba. Abrir el
> **PR #1** fue el primer disparo real, y destapó cuatro fallos en cadena —
> todos en cosas que hasta ese momento **nunca se habían ejecutado**.
>
> | # | Run | Resultado | Qué se rompió |
> |---|---|---|---|
> | 1 | `31901096819` | ❌ 3 m 32 s | `pip-audit` bloqueó por 4 CVEs; OpenSearch nunca arrancó |
> | 2 | `31902572855` | ❌ 1 m 00 s | `up --wait` fallaba por un contenedor de un solo uso |
> | 3 | `31902708220` | ❌ 59 s | `test_la_sonda_hace_mas_que_abrir_el_socket` |
> | 4 | `31902935253` | ✅ **1 m 04 s** | — |
>
> **Los 6 jobs en verde en 1 m 04 s.** El presupuesto de D-6 es de 15 minutos:
> quedan **13 m 56 s de margen**, y la corrida 1 midió 3 m 32 s con la caché
> **fría**, así que el margen no depende de la caché para sostenerse.
>
> Las cuatro causas, para que no se repitan:
>
> 1. **`pip-audit` bloqueó por 4 CVEs** en `black` y `pytest`, ambas de
>    desarrollo. **El gate hizo exactamente lo que debía.** Los pines tenían
>    techo de major, así que el arreglo obligó a cruzarlo. `pytest-asyncio` subió
>    a la serie 1.x en el mismo movimiento: con el techo `<1`, pip retrocedía
>    hasta 0.23.3 para poder instalar pytest 9, que es cambiar una
>    vulnerabilidad conocida por compatibilidad accidental.
> 2. **OpenSearch moría con `AccessDeniedException`**: el tmpfs se montaba con
>    dueño root y el proceso corre como uid 1000. Resuelto con `mode=1777`.
> 3. **`up --wait` no puede esperar a `minio-init`**, que crea el bucket y
>    termina: un contenedor que salió no está ni *running* ni *healthy*, así que
>    el éxito se leía como fallo. Los servicios de larga vida van nombrados uno
>    por uno y el bucket se crea en su propio step con `run --rm`, que **propaga
>    el código de salida** — colgado del `up` nunca se verificaba.
> 4. **Un test que nunca probó lo que decía probar.** Ver el bloque 5.
>
> #### Lo que la corrida verde deja demostrado de `platform/delivery-pipeline`
>
> Cuatro escenarios pasan de "solo verificable corriendo el pipeline" a
> verificados, con evidencia de corridas reales:
>
> | Escenario | Evidencia |
> |---|---|
> | Una propuesta de cambio dispara el pipeline | PR #1 disparó las 4 corridas |
> | El pipeline termina bajo el presupuesto de 15 min | 1 m 04 s, margen de 13 m 56 s |
> | Código conforme atraviesa los controles de estilo | `lint-backend` y `lint-frontend` en verde |
> | Una vulnerabilidad bloquea la integración | `pip-audit` frenó la corrida 1 |
>
> **Los otros escenarios siguen sin evidencia** y no se pueden marcar: linting
> que bloquea, error de tipado que bloquea, secreto filtrado que bloquea, y
> vulnerabilidad baja que solo reporta. Los cuatro exigen provocar el fallo a
> propósito — es la tarea 8.9.

> ### ✅ Tarea 8.9 — el pipeline bloquea, probado rompiéndolo a propósito
>
> 8.8 demuestra que el pipeline deja pasar lo bueno; **no dice nada sobre si
> frena lo malo**. Para eso hace falta el rojo. Se hizo en una rama descartable
> con su propio borrador (PR #2, cerrado y rama borrada al terminar) para no
> dejar commits deliberadamente rotos en la historia del PR #1.
>
> **Sonda A — un test que falla bloquea.** Corrida `31912256633`:
>
> ```
> FAILED tests/unit/test_sonda_8_9_test_que_falla.py::test_sonda_este_test_falla_a_proposito
> 1 failed, 69 passed, 6 deselected
> ```
>
> `test-backend-unit` en rojo, los otros cinco jobs en verde, conclusión global
> *failure*.
>
> **Sonda B — la cobertura insuficiente bloquea, y la bloquea el gate.** Acá el
> diseño de la sonda importa más que el resultado.
>
> `fail_under = 80` corre dentro de `pytest`, **antes** que
> `tools/check-coverage.py`. Una sonda que bajara la cobertura de líneas habría
> muerto en `fail_under`, y la evidencia habría demostrado la red de contención
> en lugar del gate. Así que la sonda provoca exactamente el caso que este
> bloque documenta como el agujero de `fail_under`: un módulo con 60
> condicionales que el test ejecuta enteros —líneas altas— recorriendo una sola
> rama de cada uno —ramas por el piso.
>
> Corrida `31912401468`, los dos steps del job cuentan la historia entera:
>
> | Step | Resultado | Salida |
> |---|---|---|
> | `pytest unitario con cobertura` | ✅ | `Required test coverage of 80.0% reached. Total coverage: 86.45%` · 70 passed |
> | `Gate de cobertura` | ❌ | `[FAIL] cobertura de ramas 55.88 % por debajo del piso 60.00 % (ADR-014)` |
>
> | Métrica | Medido | Piso | |
> |---|---|---|---|
> | Líneas | 97.81 % | 80 % | pasa |
> | Ramas | **55.88 %** | 60 % | **bloquea** |
> | `fail_under` combinado | 86.45 % | 80 % | pasa |
>
> **`fail_under` dejó pasar el archivo.** Lo frenó `check-coverage.py`, y por
> ramas. Es la prueba directa del argumento con el que se justificó todo este
> bloque: sin ese gate, un módulo con la mitad de sus ramas sin ejercitar entra
> sin que nadie se entere.

> ### ⚠️ 8.9 no mueve el conteo de escenarios, y conviene decirlo
>
> La tarea queda cumplida: sus dos mitades tienen evidencia de corridas reales.
> Pero los dos escenarios que las sondas ejercitan —*"Cobertura por debajo del
> umbral de ramas"* y el bloqueo por tests— **ya estaban contados** entre los 4
> del quality gate, cubiertos por los 19 tests de
> `tools/tests/test_check_coverage.py`. Lo que agrega 8.9 es **confirmarlos en
> el pipeline real** en vez de solo en el verificador aislado, que no es poco:
> un gate que funciona en sus tests unitarios pero no está cableado al workflow
> se ve idéntico desde afuera.
>
> `platform/delivery-pipeline` no se mueve por 8.9: sigue en **8 de 15** por esa
> tarea. Lo que sí lo mueve son las dos sondas de calidad estática de abajo.

> ### ✅ Los dos escenarios de calidad estática, con evidencia
>
> *"Violación de reglas de linting"* y *"Error de tipado estático"* seguían sin
> verificar después del PR #1. Lo único demostrado era su complementario,
> *"Código conforme"*: que el código limpio pasa. **Que lo sucio se frene es una
> afirmación distinta**, y no estaba probada. Mismo método que 8.9: rama
> descartable con borrador propio (PR #3, cerrado y rama borrada).
>
> **Sonda de linting** — corrida `31913272452`, un `import json` sin usar:
>
> ```
> F401 [*] `json` imported but unused
>   --> app/sonda_lint.py:16:8
> ```
>
> **Sonda de tipado** — corrida `31913363813`, función anotada `-> int` que
> devuelve `str`:
>
> ```
> app/sonda_tipado.py:21: error: Incompatible return value type (got "str", expected "int")  [return-value]
> ```
>
> | Step de `lint-backend` | Sonda de linting | Sonda de tipado |
> |---|---|---|
> | `ruff` | ❌ **failure** | ✅ success |
> | `black --check` | ⊘ skipped | ✅ success |
> | `mypy --strict` | ⊘ skipped | ❌ **failure** |
>
> **Los dos controles viven en el mismo job y corren en cadena, así que el
> primero que falla corta el resto.** Por eso hicieron falta dos corridas: una
> sola con las dos violaciones habría dejado un escenario sin evidencia
> *aparentando tenerla*. Los steps saltados de la primera columna son la prueba.
>
> Cada sonda se verificó en local antes de gastar una corrida, para que el rojo
> cayera en el control correcto: un rojo en el step equivocado no prueba el
> escenario.

> #### Sonda del escenario *"Secreto filtrado en el cambio"*
>
> Este escenario venía sin acreditar con un motivo anotado: plantar un secreto
> falso en un repositorio **público** puede activar la protección de push de
> GitHub, y el push ni siquiera llegaría al pipeline.
>
> **La salida fue plantarlo también adentro de un `.docx`.** La protección de
> push escanea texto y no lee binarios — el mismo punto ciego que el commit
> `07b910f` cierra en nuestro propio gate, usado a favor. El push entró sin que
> GitHub lo frenara.
>
> Dos corridas sobre el PR #4 (cerrado, rama borrada). Credenciales fabricadas,
> ninguna real, y ninguna igual a `AKIAIOSFODNN7EXAMPLE`: ese valor está en la
> allowlist de gitleaks y daría falso negativo.
>
> | Corrida | Secreto en | `gitleaks` | `gitleaks — documentos OOXML` |
> |---|---|---|---|
> | `31944844892` | `.txt` | ❌ `generic-api-key` | ⊘ el job aborta en el primer rojo |
> | `31944989894` | `.docx` | ✅ `no leaks found` sobre 2,35 MB | ❌ `aws-access-token` |
>
> **La segunda fila es el punto ciego en vivo, dentro del pipeline real**: el
> escáner recorrió 2,35 MB de historia y declaró limpio un repositorio que tenía
> una credencial adentro de un documento versionado. El paso agregado la
> encontró, sobre 14 documentos y 1.068.562 caracteres extraídos.
>
> Hicieron falta dos corridas por lo mismo que en las sondas de linting y
> tipado: los steps de un job corren en cadena y el primero que falla corta el
> resto. Con las dos credenciales juntas, la ruta OOXML nunca se habría
> ejercitado y el escenario habría quedado *aparentando* evidencia que no tenía.
> Aislarla exigió reescribir la rama descartable, no solo borrar el `.txt`: el
> paso principal escanea la **historia**, y un borrado en un commit posterior lo
> habría seguido encontrando.
>
> En las dos corridas los otros 5 jobs quedaron en verde. El rojo cayó en el
> step correcto.

> ### Estado de `platform/delivery-pipeline`: **11 de 15**
>
> | Escenario | Evidencia o motivo |
> |---|---|
> | Cobertura bajo el umbral de líneas | 19 tests de `check-coverage.py` |
> | Cobertura bajo el umbral de ramas | Ídem, **y** corrida `31912401468` en el pipeline real |
> | Cobertura que decrece | 19 tests de `check-coverage.py` |
> | Cambio que cumple los umbrales | Corrida verde `31902935253` |
> | Violación de reglas de linting | Corrida `31913272452` |
> | Error de tipado estático | Corrida `31913363813` |
> | Código conforme | Corrida verde `31902935253` |
> | Dependencia con vulnerabilidad crítica | Corrida `31901096819`, `pip-audit` |
> | Propuesta de cambio abierta | PR #1 disparó las corridas |
> | Duración de la ejecución | 1 m 04 s contra un presupuesto de 15 min |
> | Secreto filtrado en el cambio | Corridas `31944844892` (texto plano) y `31944989894` (OOXML) |
> | **Vulnerabilidad de severidad baja (solo reporta)** | ⛔ Hay que hallar un paquete con vulnerabilidad baja y **solo** baja |
> | **Integración exitosa a la rama principal** | ⛔ Bloque 9 |
> | **Fallo de las pruebas de humo** | ⛔ Bloque 9 |
> | **Trazabilidad del despliegue** | ⛔ Bloque 9 |

## 9. Despliegue a staging — `T-008` · Kubernetes + ArgoCD

> **Desbloqueado.** `IN-16` cerrado por `ADR-015` el 13-ago-2026: Kubernetes con GitOps vía ArgoCD.
> Frontera de seguridad no negociable: **GitHub Actions no recibe credenciales del cluster.** Su permiso máximo es escribir un tag de imagen en el repositorio de manifests.

**Infraestructura (Terraform)**

- [ ] 9.1 Escribir `infra/terraform/staging/` provisionando el cluster de Kubernetes con disponibilidad multi-zona
- [ ] 9.2 Provisionar con Terraform la red, la base gestionada, los buckets, el registry, el DNS y los certificados
- [ ] 9.3 Instalar ArgoCD en el cluster y configurar su acceso de solo lectura al repositorio de manifests

**Cargas de trabajo (manifests)**

- [ ] 9.4 Escribir en `infra/k8s/` los manifests de `backend`, `worker` y `frontend-web`: `Deployment`, `Service`, `Ingress` y `ConfigMap`
- [ ] 9.5 Configurar los `Secret` desde el gestor de secretos del proveedor — **nunca en el repositorio** (regla dura 4)
- [ ] 9.6 Configurar las sondas `readinessProbe` y `livenessProbe` de Kubernetes apuntando a `/ready` y `/health`
- [ ] 9.7 Configurar la mecánica azul-verde: dos `ReplicaSet` y un `Service` cuyo selector determina el pool activo

**Pipeline (GitHub Actions)**

- [ ] 9.8 Escribir `.github/workflows/deploy-staging.yml` disparado por push a `main` tras CI en verde
- [ ] 9.9 Configurar el build, la firma y el push de imágenes etiquetadas con el SHA del commit
- [ ] 9.10 Configurar la actualización del tag en el repositorio de manifests — el pipeline **termina acá**
- [ ] 9.11 Verificar que el pipeline no tiene ni necesita `kubeconfig` ni credenciales del cluster en sus secretos

**Verificación y reversión**

- [ ] 9.12 Configurar las pruebas de humo contra el pool nuevo **antes** de conmutar el selector, durante cinco minutos
- [ ] 9.13 Verificar que un fallo en las pruebas de humo deja el selector sin mover y el pool anterior sirviendo
- [ ] 9.14 Configurar la notificación al equipo ante un despliegue fallido
- [ ] 9.15 Verificar que ArgoCD detecta y reporta la deriva ante un cambio manual en el cluster
- [ ] 9.16 Verificar el despliegue automático extremo a extremo y la reversión por `git revert` de los manifests

## 10. Verificación de cierre

- [x] 10.1 Verificar que el pipeline corre verde de punta a punta sobre el repositorio completo
- [x] 10.2 Verificar que ningún valor sensible real quedó versionado (`gitleaks` sobre todo el historial del change)
- [ ] 10.3 Verificar que las tres capabilities tienen sus escenarios cubiertos por tests ejecutables
- [x] 10.4 Verificar que `IN-22`, `IN-29` y `R-3` quedaron cerrados con su ADR correspondiente
- [x] 10.5 Actualizar el estado de C-01 en `CHANGES.md`

> **Tarea 10.4 — los tres cerrados, verificado archivo por archivo.**
>
> | Bloqueante | ADR que lo cierra | Estado |
> |---|---|---|
> | `IN-22` umbral de cobertura del CI | [`ADR-014`](../../../docs/adr/ADR-014-umbrales-de-cobertura.md) | ✅ 80 % líneas / 60 % ramas, y el gate existe y bloquea |
> | `IN-29` numeración de ADRs del plan | [`ADR-018`](../../../docs/adr/ADR-018-anclas-de-adr-del-plan-de-implementacion.md) | ✅ corpus inmutable con anotación al pie |
> | `R-3` no existe tabla canónica de variables | [`ADR-013`](../../../docs/adr/ADR-013-variables-de-entorno.md) | ✅ 35 variables en 12 grupos, sostenido por `tools/check-config-parity.py` con **0 divergencias** entre ADR, `.env.example` y `Settings` |

> ### ⚠️ Tarea 10.3 — auditoría hecha, y **no da para tildar**
>
> Se cruzaron los **35 escenarios** de las tres delta specs contra los tests que
> existen de verdad. Resultado:
>
> | Capability | Escenarios | Con test ejecutable | Estado |
> |---|---|---|---|
> | `platform/service-health` | 10 | **10** | ✅ completa |
> | `platform/configuration` | 10 | **10** | ✅ completa |
> | `platform/delivery-pipeline` | 15 | **11** | ⚠️ faltan 4 |
>
> > **Actualizado.** Esta auditoría cerró con `delivery-pipeline` en 10 y un
> > total de 30. La sonda del secreto filtrado (corridas `31944844892` y
> > `31944989894`, más arriba) subió la capability a **11** y el total a
> > **31 de 35**. Los párrafos de abajo ya están corregidos; se deja dicho el
> > movimiento para que el número no parezca haber sido siempre este.
>
> **`service-health` está entera**: los 10 escenarios tienen test, y 6 de ellos
> además corren contra servicios reales en `tests/integration/`.
>
> **`configuration` quedó entera, y los 2 que faltaban no eran un olvido de
> tests: la conducta que tenían que verificar no existía.** Están en
> `tests/unit/test_secretos_no_se_exponen.py`, con la implementación que
> necesitaban:
>
> - *"Fallo de arranque por credencial inválida"*: `DATABASE_URL` solo rechazaba
>   el valor **vacío**, y con un valor vacío la aserción *"el mensaje no filtra
>   el valor"* es **vacua** — no hay valor que filtrar. Hacía falta que una
>   credencial *presente y mal formada* también matara el arranque. Se agregó la
>   validación de forma del DSN (esquema, host y nombre de base) con un mensaje
>   que nombra la variable y nunca su valor. Cierra además un agujero de fallo
>   tardío: un DSN con un typo arrancaba sano y recién aparecía como sonda de
>   disponibilidad en rojo, lejos de su causa.
> - *"Registro de la configuración al arrancar"*: **nadie registraba la
>   configuración**, así que no había registro que auditar. Se agregó al
>   `lifespan`, con los secretos enmascarados por recorrido del modelo — un
>   campo `SecretStr` nuevo queda enmascarado sin que nadie tenga que acordarse
>   de sumarlo a una lista.
>
> > **Corrección: son 14 campos sensibles, no 15.** La auditoría anterior decía
> > 15. El número correcto sale del modelo — y el test lo **deriva del modelo**
> > en vez de fijar la lista, justamente para que no vuelva a desincronizarse:
> > una lista escrita a mano se queda corta en silencio en cuanto alguien agrega
> > un secreto, y el test seguiría pasando sin cubrirlo.
>
> **`delivery-pipeline` — 4 de 15 sin cubrir.** Los 11 cubiertos se reparten en
> cuatro grupos: los **4 del gate de cobertura**, por los 19 tests de
> `tools/tests/test_check_coverage.py`; **4 que la corrida verde del PR #1
> demostró en el pipeline real** (una propuesta de cambio lo dispara, termina
> bajo el presupuesto de 15 minutos, el código conforme atraviesa los controles
> de estilo, y una vulnerabilidad bloquea la integración — esto último lo probó
> `pip-audit` frenando la primera corrida); **2 de las sondas de calidad
> estática** (linting que bloquea, tipado que bloquea); y **1 de la sonda del
> secreto filtrado**. El desglose escenario por escenario está en la tabla del
> bloque 8.
>
> Los 4 que faltan se separan en dos causas, porque no se arreglan igual:
>
> - **1 exige provocar un fallo que no es trivial de provocar**: una
>   vulnerabilidad de severidad baja, que exige hallar un paquete con
>   vulnerabilidad baja y **solo** baja.
> - **3 son del bloque 9** (despliegue a staging, reversión por fallo de pruebas
>   de humo, trazabilidad del commit desplegado). No implementados, y bloqueados
>   por el proveedor cloud sin decidir.
>
> > **Corrección a la auditoría anterior.** Decía "7 escenarios describen
> > comportamiento del workflow" pero enumeraba **8**, y de ahí salía un total
> > de 14 sobre 15. Los grupos correctos son 4 + 8 + 3 = 15.
>
> **Consecuencia: C-01 sigue sin poder archivarse — 31 de 35.** No es una
> formalidad de proceso: `openspec archive` sincroniza las delta specs contra
> `openspec/specs/`, y promover a spec vigente un contrato con escenarios sin
> verificación es declarar cubierto lo que no lo está.
>
> Dos de los tres capabilities ya están enteros. **Lo único que falta son 4
> escenarios de `delivery-pipeline`, y ninguno depende de escribir un test**:
> 3 esperan el bloque 9 —o sea la decisión de proveedor cloud— y el otro exige
> provocar un fallo que no es trivial de provocar. Es un límite distinto al de
> ayer, cuando lo que faltaba era trabajo de tests.

> ### ✅ Tarea 10.2 — historial escaneado y limpio, con un punto ciego cerrado a mano
>
> `gitleaks` **v8.28.0** instalado en la máquina — la **misma versión** que fija
> el job de seguridad de `ci.yml:303`. Escanear con una versión distinta de la
> del pipeline mediría otra cosa.
>
> ```
> gitleaks detect --source . --redact --no-banner --verbose
> → 17 commits scanned · ~3.32 MB · no leaks found · exit 0
> ```
>
> **El 17 de 18 no es un hueco.** `gitleaks` solo escanea **líneas agregadas**;
> el commit que falta es `0059fe9` (*elimina .gitkeep de alembic/versions*), que
> tiene **+0 líneas**. No hay nada que escanear ahí.
>
> #### El punto ciego: 13 `.docx` que gitleaks nunca vio
>
> `detect` recorre la historia con `git log -p`. Un `.docx` es binario, así que
> git emite `Binary files differ` y **su contenido jamás llega al escáner**. En
> este repo eso son los **13 documentos fuente** de `autos/*.docx` — 1,52 MB de
> texto, incluida la constitución y los planes de seguridad. Nunca se escanearon.
>
> **El mismo agujero existe en el CI**, y ahí es peor: el job corre gitleaks en
> un contenedor Linux, donde no aparece ni el error de `astextplain` que lo
> delató en local. Falla en silencio.
>
> Cerrado a mano: se extrajeron los **13 blobs `.docx` de toda la historia**
> (`git rev-list --objects --all`, no solo el árbol de trabajo), se convirtieron
> a texto todas sus partes XML — documento, headers, footers, notas, comentarios,
> propiedades y `.rels`, donde suele esconderse una URL con credencial — y se
> escanearon con `gitleaks dir`:
>
> ```
> → 13 blobs · ~1.52 MB · no leaks found · exit 0
> ```
>
> #### El escáner se verificó, no se asumió
>
> Un `exit 0` solo vale si la herramienta detecta cuando hay algo. Se plantó un
> token de alta entropía con forma de GitHub PAT en cuatro repositorios sonda:
>
> | Sonda | Dónde está el secreto | Resultado |
> |---|---|---|
> | B | commit **raíz**, nunca borrado | ✅ detecta · exit 1 |
> | C | commit 2, nunca borrado | ✅ detecta · exit 1 |
> | D | commit 2, **borrado** en el commit 3 | ✅ detecta · exit 1 |
> | E | commit **raíz**, **borrado** después | ✅ detecta · exit 1 |
>
> Las cuatro salen con **código 1**. Queda probado lo que importaba: el commit
> raíz **sí** se escanea, y borrar el archivo después **no** esconde el secreto.
>
> > **Una sonda descartada, por si alguien la repite.** El primer intento usó
> > `AKIAIOSFODNN7EXAMPLE` y gitleaks devolvió *"no leaks found"*. No es un fallo
> > del escáner: ese valor es el ejemplo de la documentación de AWS y está en la
> > **allowlist** por defecto. Una sonda con un secreto allowlisteado prueba lo
> > contrario de lo que parece — habría hecho declarar roto un gate que funciona.
>
> #### Complementos ya verificados
>
> `.env` ignorado (`.gitignore:48`), los 35 valores de `.env.example` en
> `cambiame` o ficticios, y ningún otro archivo de entorno trackeado.

> **✅ Tarea 10.1 — pipeline verde de punta a punta.** Corrida `31902935253`
> sobre el PR #1, commit `299d485`: **los 6 jobs en verde en 1 m 04 s**, sobre
> el repositorio completo. Costó cuatro corridas y tres arreglos; el detalle
> está en la auditoría de 8.8.
