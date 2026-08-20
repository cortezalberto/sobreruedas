# Tareas — C-02 `core-backend-primitives`

> **Gobernanza CRÍTICA.** `db/session.py` es el control de aislamiento multi-tenant y `rbac.py` el mecanismo de autorización. No se escribe código sin aprobación humana explícita.
>
> **TDD estricto.** Cada tarea de implementación empieza por un test que falla. Los tests de aislamiento corren contra PostgreSQL real (regla dura 8).
>
> **Orden no libre.** El bloque 6 está bloqueado por `E-001` (cierre mínimo de discusión: 20-ago-2026). Ver `design.md` · *Migration Plan*.

## 1. Extensiones y contexto de tenant — `T-009`, `T-010` · tramo 1

- [x] 1.1 Escribir la migración `001` que habilita `uuid-ossp`, `pg_trgm`, `unaccent` y `btree_gin`, con `downgrade` que las revierte
- [x] 1.2 Escribir el test que verifica que las cuatro extensiones quedan presentes tras `upgrade head`, consultando `pg_extension` contra PostgreSQL real
- [x] 1.3 Crear el engine asíncrono y el `sessionmaker` en `app/db/session.py`, tomando el DSN y el tamaño de pool de `Settings`
- [x] 1.4 Escribir el test que verifica que el `tenant_id` recibido se valida como UUID **antes** de tocar la base, y que un valor no parseable rechaza la petición sin ejecutar sentencia alguna
- [x] 1.5 Implementar `get_session()`: abre transacción, emite `SELECT set_config('app.current_tenant', :tenant, true)` como primera sentencia con parámetro bindeado, y recién entonces cede la sesión (`design.md` D-1, D-2, D-3)
- [x] 1.6 Implementar `get_platform_session()` sin contexto de tenant, con nombre distinto y no como parámetro de la anterior (D-4)
- [x] 1.7 Escribir la migración `002` con la tabla testigo `platform_probe` (`tenant_id` + carga mínima) y su política `tenant_isolation` filtrando por `current_setting('app.current_tenant')` (D-7)

## 2. Prueba real del aislamiento — `T-010`

> ✅ **Los 13 tests pasan sin marca alguna.** Estuvieron 5 en fallo esperado
> estricto mientras el rol de conexion era superusuario con `BYPASSRLS` y
> salteaba toda politica — un defecto de infraestructura, no del codigo. Lo
> arreglo el change `rol-de-base-sin-bypass-rls` ([`ADR-020`](../../../../docs/adr/ADR-020-rol-de-conexion-sin-bypass-de-rls.md)),
> y la marca estricta hizo lo suyo: al empezar a pasar, pytest los convirtio en
> ERROR y obligo a sacarla. Un `skip` los habria escondido para siempre.

- [x] 2.1 Escribir el test que verifica que una consulta con contexto establecido devuelve solo filas del tenant en contexto
- [x] 2.2 Escribir el test que verifica que **sin** contexto establecido la consulta no devuelve **ninguna** fila, y que no se asume tenant por defecto
- [x] 2.3 Escribir el test que verifica que el parámetro no sobrevive a la transacción: tras cerrarla y devolver la conexión al pool, `current_setting` ya no lo trae
- [x] 2.4 Escribir el test de **concurrencia**: dos sesiones simultáneas de tenants distintos, cada una observa solo lo suyo en todo momento
- [x] 2.5 Escribir el test que verifica que el filtro explícito de la capa de aplicación sigue acotando al tenant **con la política de la base desactivada** (segunda capa por sí sola)
- [x] 2.6 Escribir el test introspectivo que recorre `pg_policies` y falla si alguna tabla con `tenant_id` no tiene política activa, con la lista de exenciones declarada de forma exhaustiva
- [x] 2.7 Escribir el test que verifica que el test introspectivo **detecta** una tabla sin política (probar el detector, no solo usarlo)
- [x] 2.8 Exponer la métrica de violaciones de aislamiento y escribir el test de que vale cero en operación normal y se incrementa ante un intento de acceso cruzado

## 3. Identidad — `T-013` · tramo 2

- [x] 3.1 Escribir los tests de rechazo del token: firma inválida, expirado, emisor distinto, receptor distinto y petición sin token
- [x] 3.2 Implementar la obtención y el cacheo del JWKS del realm, con vencimiento y refresco bajo demanda ante `kid` desconocido, con límite de frecuencia (D-8)
- [x] 3.3 Escribir el test de rotación de claves: el proveedor rota, llega un token con la clave nueva, el sistema lo acepta sin reiniciar
- [x] 3.4 Implementar la dependency `get_current_user` derivando identificador, tenant y rol **del token**, sin validar el rol contra el catálogo (D-9)
- [x] 3.5 Escribir el test que verifica que un token sin rol declarado rechaza la petición en lugar de asignar un rol por defecto
- [x] 3.6 Declarar explícitamente las rutas exentas de autenticación y escribir el test de que ninguna ruta que exponga datos de tenant está exenta

> ✅ **Bloque 3 completo.** `core/auth.py`: validacion RS256 contra el JWKS del realm,
> cache con vencimiento y refresco bajo demanda acotado, `get_current_user` y la lista
> explicita de rutas exentas. 35 tests nuevos.
>
> ⚠️ **Deuda para C-05**: los nombres de claim (`tenant_id`, `role` de primer nivel) no
> tienen fuente en el corpus. Quedan decididos en [`ADR-021`](../../../../docs/adr/ADR-021-claims-de-tenant-y-rol.md)
> y C-05 tiene que crear los dos mappers en el realm, o ningun token va a traerlos.

## 4. Convenciones de API — `T-012`, `T-015` · tramo 2

- [x] 4.1 Escribir el test que verifica que cada entrada de `errors[]` trae `field`, `code` y `message` — hoy falta `code`
- [x] 4.2 Completar `core/errors.py` agregando el código estable por campo, sin reescribir lo que C-01 ya dejó andando
- [x] 4.3 Escribir el test que verifica que el valor rechazado por la validación **no** aparece en la respuesta
- [x] 4.4 Escribir los tests de paginación por cursor: recorrido completo sin repetir ni saltear, última página inequívoca, tamaño por encima del máximo acotado al máximo, cursor inválido rechazado con el formato de error uniforme
- [x] 4.5 Implementar `core/pagination.py` con cursor opaco que codifica `(created_at, id)` y el tenant, y orden determinista por ese par (D-6)
- [x] 4.6 Escribir el test que verifica que un cursor obtenido en otro tenant no devuelve elementos de ese tenant
- [x] 4.7 Escribir la migración `003` con la tabla `idempotency_keys` y su `UNIQUE (tenant_id, key)` (D-5)
- [x] 4.8 Escribir los tests de idempotencia: reintento idéntico devuelve el original sin crear un segundo recurso; misma clave con contenido distinto da conflicto; clave vencida se trata como creación nueva; creación sin clave se procesa normalmente
- [x] 4.9 Implementar `core/idempotency.py` y escribir el test de que la misma clave en dos tenants distintos produce dos creaciones independientes

> ✅ **Bloque 4 completo.** `core/errors.py` con codigo por campo, `core/pagination.py`
> con cursor opaco acotado al tenant, `core/idempotency.py` sobre la migracion `003`.
> 48 tests nuevos. La clave vencida se **pisa en su lugar** y no se borra: el rol de
> aplicacion no tiene `DELETE` (`ADR-020`), y resulto ser mejor solucion que borrar —
> es atomica y no deja ventana.

## 5. Eventos de dominio y andamiaje de tests — `T-016`, `T-032`, `T-033` · tramo 3

- [x] 5.1 Escribir el test del sobre canónico: identificador único, tipo, versión, tenant, instante con zona horaria y contenido; y que dos publicaciones del mismo hecho llevan identificadores distintos
- [x] 5.2 Implementar el publisher sobre Redis Streams, rechazando en la publicación todo evento sin `tenant_id` (D-10)
- [x] 5.3 Escribir el test de que publicar no depende del consumidor: sin consumidores la publicación es exitosa, y un consumidor que falla no afecta a la petición que originó el evento
- [x] 5.4 Implementar el consumer base con consumer groups y confirmación explícita, **restableciendo el contexto de tenant** del sobre antes de tocar la base
- [x] 5.5 Escribir el test de que el consumidor procesa bajo el contexto correcto y no ve datos de otro tenant
- [x] 5.6 Implementar el reintento con espera creciente y techo acotado, y escribir los tests de fallo transitorio, de espera que crece y de reintentos acotados
- [x] 5.7 Implementar el stream de irrecuperables y escribir los tests de que el evento agotado queda registrado con el motivo del último fallo y de que la cola sigue avanzando
- [x] 5.8 Escribir el test de entrega repetida: el consumidor reconoce el `event_id` ya procesado y el efecto no se aplica dos veces
- [x] 5.9 Escribir el test de caída antes de confirmar: el evento vuelve a entregarse y no queda sin procesar
- [x] 5.10 Fixtures comunes en `tests/integration/conftest.py` (no en `tests/conftest.py`: las de base necesitan DSN y ahí solo viven las unitarias): `tenant`, `otro_tenant`, `sesion`, `sesion_sin_tenant` y `redis`. Las cinco duplicadas que había en los archivos de test se eliminaron.
      ⚠️ **`cliente autenticado` y `emisor de tokens de prueba` NO están**: dependen de `core/auth.py`, que es el bloque 3 — gobernanza CRÍTICA, sin aprobación todavía. Escribirlos ahora sería inventar la forma de los claims antes de decidirla.
- [x] 5.11 (parcial) `factory_boy` agregada a las dependencias de desarrollo.
      ⚠️ **`tests/factories/` NO se creó.** No hay ninguna entidad de negocio: la única tabla con `tenant_id` es la testigo `platform_probe`, y `Base` no tiene un solo modelo registrado. Una fábrica base sin nada que fabricar es andamiaje que hay que adivinar dos veces — se escribe junto a la primera entidad real (`users`, C-05), que es cuando se sabe qué convención necesita.
- [x] 5.12 Test de arquitectura en `tests/unit/test_arquitectura.py`: analiza el **AST** de todo `app/**.py` y falla si `sesion_de_plataforma` se referencia fuera de `modules/admin/`. Por AST y no por texto para no marcar comentarios ni docstrings — un detector ruidoso termina desactivado. Se prueba el detector en cuatro variantes: infractor, espacio permitido, menciones que no son usos, y el uso por atributo (`session.sesion_de_plataforma()`), que es la forma de esquivarlo sin proponérselo.

## 6. Autorización — `T-014` · tramo 4 · ✅ DESBLOQUEADO

> ✅ **`E-001` ratificada el 20-ago-2026.** Pasos (c) y (d) del Artículo 8 completos; el (e) es la comunicación y su envío es del usuario, no bloquea la implementación. `ADR-017` pasó a **aceptado pleno** y el catálogo de roles quedó firme en sus tres valores — `manager`, `salesperson`, `admin_staff`. La constitución es **v1.1**.
>
> ✅ **`ADR-033` (20-ago-2026)** — al transcribir §6 apareció que `ADR-024` usa `own` con dos sentidos: el de §4 (`assigned_user_id`, "y nada más") y "sobre sí mismo" en las tablas de Auth y Usuarios, que no tienen `assigned_user_id`. Se agrega el alcance **`self`** como tercer valor; ninguna celda cambia de permiso, dos cambian de nombre. `own` queda intacto y con él el control de `RN-CR-13`.
>
> ⚠️ **Sigue vigente la gobernanza CRÍTICA**: `rbac.py` es el mecanismo de autorización del sistema. Que el bloqueante documental esté resuelto no convierte esto en trabajo autónomo.

- [x] 6.1 Verificar que `E-001` está ratificada y registrada; si no, **detenerse acá** — ✅ **20-ago-2026**: ratificada, registrada como apéndice *append-only* en [`deRuedas-constitucion.md`](../../../../docs/sdd/deRuedas-constitucion.md) §Historial de enmiendas, y `ADR-017` sin condición. El portón se abre
- [x] 6.2 [`core/rbac.py`](../../../../backend/app/core/rbac.py): **dos tipos separados**, `RolDeTenant` (3 valores) y `RolDePlataforma` (1), no un enum de cuatro — `ADR-024` §2 los define disjuntos y dos tipos hacen que la mezcla no se pueda escribir. `EQUIVALENCIA_EN_GLOSARIO` vive junto al catálogo y no en presentación: el glosario es N0, la traducción es parte de la definición del rol
- [x] 6.3 `rol_de_tenant()` / `rol_de_plataforma()` resuelven **exacto** —sin recortar espacios ni normalizar mayúsculas— y levantan `RolDesconocido` con el nombre que falló y el catálogo. `require_role("gerente")` falla **al declarar**, y el test que lo afirma no monta ningún `TestClient`: la afirmación es que nunca hizo falta uno. Los dos modos de falla quedan cerrados por construcción — `require_role()` sin roles levanta `DeclaracionVacia` en vez de elegir en silencio entre "nadie" y "cualquiera"
- [x] 6.4 `AuthorizationError` (403) + `RolInsuficiente` (`insufficient_role`) en [`core/errors.py`](../../../../backend/app/core/errors.py), donde la docstring de `AuthenticationError` ya los anunciaba. Se distinguen **por código y no solo por estado**, y el 403 no enumera los roles admitidos: eso va al log, no al cuerpo. Verificado además que `_exige_identidad` del gate de rutas **sí** ve esta forma de protección (`require_role` anida `get_current_user`), así que el agujero de `fa9a79d` no se reabre
- [x] 6.5 Matriz transcrita: **59 claves de tenant + 11 de plataforma**, con `Alcance` (`all`/`own`/`self`) y `Concesion(alcance, campos)`. `require_permission` **devuelve la concesión, no un booleano** — §3 extiende la restricción de campos a la LECTURA (`RN-ST-12`) y un portón sí/no no puede recortar una respuesta. Los 9 módulos de §8 sin una sola entrada, verificado recorriendo la matriz y no contra una lista a mano.
      ✅ **La celda que no era transcribible ya lo es** — [`ADR-034`](../../../../docs/adr/ADR-034-transiciones-como-tercer-eje-del-permiso.md) le da a §3 un tercer eje, *Transiciones*, y `vehicles:change_status` para `salesperson` declara `{(available, reserved)}` completo. Cerró una concesión que **estaba corriendo**: el vendedor mandaba un vehículo propio al taller, y **lo vendía en dos pasos** —reservar, que sí le toca, y después `reserved`→`sold`, que `RN-ST-05` admite—. `RN-ST-05` acota qué transiciones existen, no quién las hace, así que componer dos permitidas no encontraba ningún control en el medio.
      ⚠️ `notification_preferences` (dentro de `[perfil]`) e `internal_notes` son nombres que el ADR da en prosa y todavía no son columnas — `users` llega en C-05, `internal_notes` en C-14.
- [x] 6.6 Dos mecanismos reutilizables en `rbac.py` —`verificar_alcance()` y `recortar()`— más su aplicación real, en [`tests/integration/test_alcance_fino.py`](../../../../backend/tests/integration/test_alcance_fino.py).
      **`RN-ST-12` sobre HTTP**: el vendedor lee el vehículo y la clave `acquisition_cost_ars` **no está** (no viene en `null` — un `null` afirma "este campo existe y está vacío", que es información que la regla no le concede), y sigue viendo todo lo demás. Se prueban **los dos sentidos**: `manager` y `admin_staff` sí lo reciben. Sin esa mitad, el test seguiría verde el día que el costo no se le devolviera a nadie — que es justo el estado del que se venía. Y se prueba en **detalle y listado**: un recorte que solo cubre el detalle deja el costo saliendo por el endpoint que más se llama.
      El router elige el schema preguntando por el **campo concreto** y no por `campos is None`, para que una restricción futura sobre otro campo no apague el costo de rebote. `response_model=None`: un `response_model` fijo recortaría el costo también a quien sí puede verlo.
      **Rechazo sin efecto**: `verificar_alcance` corre entre el SELECT y el UPDATE. Si corriera después, el estado ya habría cambiado y el 403 sería una mentira cortés.
- [x] 6.7 **Lo encontró la cobertura, no el plan**: `tenants:read` existe en las **dos** matrices (el `manager` sobre su agencia, el `super_admin` sobre todas). Resolver "la primera que matchee" habría convertido el orden de dos diccionarios en una decisión de autorización. `require_permission` pasa a llevar `espacio`: se deduce para las 69 claves que viven en una sola matriz y se **exige** para la que vive en las dos (`EspacioAmbiguo`, al declarar). `_celdas_en()` mira **una** matriz, y eso implementa los dos sentidos de §2 a la vez sin una regla por sentido.
      Reparto de las tres cláusulas: *plataforma solo bajo `/admin`* y *tenant rechazado ahí* las defiende `rbac.py`; *un rol de tenant nunca accede a otro tenant* la defienden las tres capas de la regla dura 1 (bloques 1-2), no esta matriz.
- [x] 6.8 Denegar por defecto **en tiempo de petición**, y `PermisoNoDeclarado` **en tiempo de declaración**. La distinción es el punto: aplicar denegar-por-defecto también a los permisos inexistentes lo vuelve una tapadera — `vehicles:raed` denegaría a todos y el endpoint parecería bien puesto hasta que alguien reporte que no entra. Alineado con §8, que pide las filas **antes** que el endpoint.
- [x] 6.9 [`tests/rutas.py`](../../../../backend/tests/rutas.py) — el recorrido se **movió** desde `test_auth_rutas.py` en vez de copiarse: ya se había roto una vez (`fa9a79d`, la ceguera a `include_router`), así que la copia no era una hipótesis sino la repetición de un fallo conocido. Para poder leer las declaraciones sin hurgar en un `__closure__`, `require_role`/`require_permission` pasan a devolver `ExigeRol`/`ExigePermiso` (refactor, 55 tests siguieron verdes).
      **El recorrido encontró 14 rutas expuestas sin ninguna declaración de acceso** — hoy cualquier usuario autenticado, de cualquier rol, podía archivar un vehículo. Se cablearon las 14 contra sus celdas del ADR. Los tests de integración firman sin `role=` y el default de `firmar` es `manager`, que tiene las 59 claves, así que el cableo no los altera — pero **eso no está verificado**: sin Docker la suite de integración no corre.
      ✅ `GET /vehicles/import/template`, `GET /imports` y `GET /imports/{id}` **ya tienen su fila** en `ADR-024` §6, con los mismos actores que `POST /vehicles/import`. Agregarlas no fue un desvío: §8 dice literalmente que el change que trae un módulo debe agregar sus filas ahí, y `C-17` las había omitido.
- [x] 6.10 El mismo sujeto, el mismo vehículo: **200 antes de la reasignación, `AlcanceInsuficiente` después**. Más `NULL` no es de nadie (la lectura contraria —"sin dueño, de todos"— convertiría el olvido de asignar en una concesión) y el contrapeso del `manager`, cuyo `all` no mira la asignación — sin él, los otros tests pasarían igual si `own` denegara siempre.
      La concesión se toma de **la celda real de la matriz**, no se arma a mano. Los tests llaman la corrutina del router **directamente**: `TestClient` corre el endpoint en su propio portal y `coverage` no traza lo de adentro, y reasignar a mitad de camino con un cliente síncrono obligaría a un `asyncio.run()` sobre un engine cacheado en otro loop — el fallo que documenta `test_tarea_dos_corridas.py`.
- [x] 6.11 Tres ángulos, porque el dato de hoy engaña: **`manager` contiene por clave a los otros dos**, y esa contención accidental invita a escribir un recorrido de "el rol y los de arriba". (a) `salesperson` y `admin_staff` son **mutuamente incomparables** — descarta cualquier orden total; (b) la contención del `manager` es **por clave y no por concesión** (`leads:read` es `all` para uno y `own` para el otro: mismo nombre, dos permisos); (c) el mecanismo — agregar una celda a un rol **sobre una copia** no se la da a ningún otro. Sobre copia y no sobre la matriz real: un test que mute el módulo le cambia la autorización a todo lo que corra después.
      `alcanzables_por()` recibe **las celdas de un solo rol**, no la matriz — para que nadie pueda resolver "el rol o alguno más alto" ni queriendo.

## 7. Cierre

- [x] 7.1 Corregido en `CHANGES.md` (línea 371). Se escribió además la forma real (`set_config(...)`) y no `SET LOCAL`, que tampoco era lo que el código hace — ver D-2.
- [x] 7.2 [`ADR-022`](../../../../docs/adr/ADR-022-identificador-de-correlacion-en-los-errores.md). Sin él, por el Principio 5, el desvío no era vinculante.
- [x] 7.3 **97.27 % líneas · 92.00 % ramas**, sin decrecimiento. 236 tests.
- [x] 7.4 [`cobertura-de-escenarios.md`](cobertura-de-escenarios.md): **52 de 72** escenarios con test ejecutable, con el motivo de cada uno de los 20 restantes. Al auditar aparecieron 2 que no dependían de nada y se cubrieron en el acto.
