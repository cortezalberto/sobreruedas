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
> arreglo el change `rol-de-base-sin-bypass-rls` ([`ADR-020`](../../../docs/adr/ADR-020-rol-de-conexion-sin-bypass-de-rls.md)),
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
> tienen fuente en el corpus. Quedan decididos en [`ADR-021`](../../../docs/adr/ADR-021-claims-de-tenant-y-rol.md)
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

## 6. Autorización — `T-014` · tramo 4 · ⛔ BLOQUEADO POR `E-001`

> **No empezar hasta que `E-001` complete los pasos (c), (d) y (e) del Artículo 8.** Cierre mínimo de discusión: 20-ago-2026. `ADR-017` está aceptado *condicionado* a esa ratificación. Regla dura 12.

- [ ] 6.1 Verificar que `E-001` está ratificada y registrada; si no, **detenerse acá**
- [ ] 6.2 Definir el catálogo de roles en un único lugar consultable, con la equivalencia al glosario que `ADR-017` documenta
- [ ] 6.3 Escribir el test de que declarar un rol fuera del catálogo falla de forma detectable antes de atender peticiones, y no se interpreta como "nadie" ni como "cualquiera"
- [ ] 6.4 Implementar `require_role(...)` devolviendo rechazo por falta de permisos, distinguible del rechazo por falta de autenticación
- [ ] 6.5 Implementar `require_permission(...)` y transcribir la definición de permisos **literalmente** de las tablas de [`ADR-024`](../../../docs/adr/ADR-024-matriz-rbac-canonica.md) §6 y §7: permiso `recurso:acción`, alcance `all`/`own`, conjunto de campos opcional. Los 9 módulos que el ADR no declara **quedan denegados por denegar-por-defecto** — no se les inventa una entrada
- [ ] 6.6 Escribir los tests de alcance fino: modificación acotada a ciertos campos deja el recurso intacto al rechazar; **lectura** acotada a ciertos campos no devuelve los excluidos (`RN-ST-12`, `acquisition_cost_ars`); alcance acotado a lo asignado rechaza lo no asignado
- [ ] 6.7 Implementar la separación cross-tenant: rol de tenant nunca accede a otro tenant; rol de plataforma solo bajo el espacio administrativo; rol de tenant rechazado en ese espacio
- [ ] 6.8 Escribir el test de denegar por defecto: una operación sin declaración de acceso no autoriza a nadie
- [ ] 6.9 Escribir la verificación automática que recorre las operaciones realmente expuestas contra cada rol del catálogo, detecta una operación que se abre de más e incluye las operaciones nuevas sin lista a mano. **Son dos recorridos disjuntos** (`ADR-024` §2): los tres roles de tenant contra `/api/v1`, y el rol de plataforma contra `/admin/api/v1`
- [ ] 6.10 Escribir el test de que **`own` es `assigned_user_id` en el momento de la petición**: reasignar un recurso le quita el acceso al sujeto anterior aunque lo haya creado (`ADR-024` §4 — es lo que le da sentido a `RN-CR-13`)
- [ ] 6.11 Escribir el test de que **no hay herencia entre roles** (`S3`): un permiso concedido a un rol no queda concedido a ningún otro, y 6.9 recorre los tres roles de tenant por separado sin asumir contención

## 7. Cierre

- [x] 7.1 Corregido en `CHANGES.md` (línea 371). Se escribió además la forma real (`set_config(...)`) y no `SET LOCAL`, que tampoco era lo que el código hace — ver D-2.
- [x] 7.2 [`ADR-022`](../../../docs/adr/ADR-022-identificador-de-correlacion-en-los-errores.md). Sin él, por el Principio 5, el desvío no era vinculante.
- [x] 7.3 **97.27 % líneas · 92.00 % ramas**, sin decrecimiento. 236 tests.
- [x] 7.4 [`cobertura-de-escenarios.md`](cobertura-de-escenarios.md): **52 de 72** escenarios con test ejecutable, con el motivo de cada uno de los 20 restantes. Al auditar aparecieron 2 que no dependían de nada y se cubrieron en el acto.
