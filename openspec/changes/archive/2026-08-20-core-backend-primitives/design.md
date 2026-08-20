# Diseño — C-02 `core-backend-primitives`

## Context

C-01 dejó `backend/app/` con `config.py`, `main.py`, `core/errors.py` y `core/observability.py`. No hay engine de SQLAlchemy, no hay sesión, no hay una sola tabla de negocio y `alembic/versions/` tiene solo la baseline vacía. Las dependencias ya están declaradas: SQLAlchemy 2.x con `asyncio`, `asyncpg`, `redis` y `celery`.

Ese vacío condiciona el diseño más de lo que parece: **este change tiene que probar el aislamiento multi-tenant sin tener ninguna tabla de negocio que aislar.** Ver *Decisiones · D-7*.

Motivación en [`proposal.md`](proposal.md). Requisitos en [`specs/`](specs/).

## Goals / Non-Goals

**Goals:**

- Que el contexto de tenant sea **imposible de olvidar**: que la forma natural de obtener una sesión ya lo traiga puesto, y que la forma de obtenerla sin contexto sea explícita y ruidosa.
- Que el aislamiento se pruebe con PostgreSQL de verdad, RLS de verdad y concurrencia de verdad.
- Que cada primitiva sea usable por los 16 módulos sin que ninguno tenga que entender su implementación.

**Non-Goals:**

- No se **decide** la matriz de permisos por recurso: la decide [`ADR-024`](../../../../docs/adr/ADR-024-matriz-rbac-canonica.md). Acá se construye el mecanismo que la aplica y se la transcribe **literalmente**; ninguna celda se inventa ni se ajusta en el código.
- No se crea ninguna tabla de negocio ni la tabla `users` (es C-05).
- No se implementa `@audit_action` ni `audit_logs` (es C-03).
- No se resuelve el rate limiting (`IN-19`, sin decidir).

## Decisions

### D-1 · El parámetro de sesión se llama `app.current_tenant`

`CHANGES.md` dice `app.current_tenant_id`. El corpus vinculante dice `app.current_tenant`: es cita textual del plan de seguridad, y lo repiten `RN-MT-02`, `RN-MT-06` y la regla dura 1 del proyecto. **Manda el corpus**; se corrige la ficha del roadmap.

No es cosmético. Un parámetro mal nombrado **no falla ruidosamente**: `current_setting('app.current_tenant', true)` devuelve vacío, la política no matchea ninguna fila y las consultas dejan de traer datos. Eso se lee como "no hay registros", no como "el aislamiento está roto". El síntoma aparece lejos de la causa.

*Alternativa descartada*: soportar los dos nombres. Duplicaría la superficie del control más crítico del sistema para tapar un error de tipeo del roadmap.

### D-2 · El contexto se establece con `set_config`, no interpolando la sentencia

`SET LOCAL` no admite parámetros bindeados: el valor va en el texto de la sentencia. Interpolar el `tenant_id` ahí sería construir SQL por concatenación en **el control de seguridad más crítico del sistema**, exactamente lo que prohíbe la regla dura 9.

Se usa la forma funcional, que **sí** acepta parámetro bindeado:

```
SELECT set_config('app.current_tenant', :tenant, true)
```

El tercer argumento `true` es `is_local`: el valor vive hasta el fin de la transacción, igual que `SET LOCAL`. Además, el `tenant_id` se valida como UUID **antes** de llegar a la base: si no parsea, la petición se rechaza y no se ejecuta nada.

*Alternativa descartada*: interpolar previa validación de UUID. La validación es correcta hoy y sigue siendo una concatenación en el peor lugar posible del sistema — el día que alguien la relaje, no hay segunda línea de defensa.

### D-3 · El contexto se ata a la transacción de la sesión, no a un middleware

Un middleware corre antes de que exista la sesión y no puede emitir algo `LOCAL` a una transacción que todavía no empezó. Si además se emitiera fuera de transacción, `is_local = true` lo haría inútil: el valor moriría al instante.

La dependency que provee la sesión abre la transacción, emite `set_config` como **primera sentencia**, y recién entonces cede la sesión. El commit o rollback cierra la transacción y con eso el parámetro desaparece; la conexión vuelve al pool limpia.

Consecuencia deliberada: **no hay forma de obtener la sesión estándar sin contexto de tenant.** Los casos legítimos sin tenant —migraciones, tareas de plataforma, el backoffice cross-tenant— usan una dependency distinta, con otro nombre, que se lee en el código como la excepción que es.

### D-4 · La sesión sin tenant es una puerta aparte y angosta

`get_session()` exige contexto de tenant. `get_platform_session()` no lo establece, y por eso mismo:

- Solo puede usarse en rutas bajo el espacio administrativo o en tareas de plataforma.
- Un test de arquitectura recorre los routers y falla si aparece fuera de ese espacio.

Que las dos formas se distingan **por el nombre** y no por un parámetro booleano es intencional: `get_session(tenant=False)` en una revisión de código se lee como un detalle; `get_platform_session` se lee como una decisión.

### D-5 · La idempotencia se guarda en PostgreSQL, no en Redis

Redis tiene TTL nativo y sería más cómodo. Se descarta: la idempotencia protege **creaciones**, y en este dominio eso incluye operaciones de dinero. Un Redis que se reinicia pierde las claves, y perder una clave de idempotencia significa aceptar como nuevo un reintento que ya se cobró.

Tabla `idempotency_keys` con `tenant_id`, la clave, la huella del cuerpo, la respuesta guardada y su vencimiento. `UNIQUE (tenant_id, key)` — la clave está **acotada al tenant**, así dos agencias que eligen la misma cadena no se pisan. La limpieza de vencidas es una tarea periódica, no un `TTL` de la base.

*Trade-off asumido*: una escritura extra por creación. Es el precio de que la garantía sobreviva a un reinicio.

### D-6 · El cursor es opaco y lleva el tenant adentro

El cursor codifica la posición (`created_at`, `id`) **y** el `tenant_id`, y se entrega como cadena opaca. Al recibirlo, se verifica que el tenant del cursor coincida con el del contexto; si no, se rechaza.

Sin eso, un cursor obtenido en un tenant y presentado en otro es un intento de acceso cruzado que la paginación traduciría en un `WHERE created_at > ...` perfectamente válido. RLS igual lo taparía —esa es la gracia de las tres capas— pero la segunda capa tiene que sostenerse por sí sola.

Se ordena por `(created_at, id)` y no por `created_at` solo: con timestamps iguales el orden sería no determinista y el recorrido saltearía o repetiría elementos.

### D-7 · Para probar el aislamiento hace falta una tabla, y la crea este change

No hay ninguna tabla de negocio todavía, así que los escenarios de `platform/tenant-isolation` no tendrían contra qué correr. Se crea **`platform_probe`**: una tabla mínima con `tenant_id` y su política `tenant_isolation`, en una migración propia de este change.

Es la primera tabla que ejercita el mecanismo completo, y queda como testigo permanente: si alguien rompe el contexto de sesión, los tests de aislamiento fallan aunque no haya ningún módulo escrito todavía.

*Alternativa descartada*: crear tablas de prueba solo dentro de los tests. Serían tablas sin migración, sin política revisada en un PR, y el test introspectivo que recorre `pg_policies` no las vería — probaría un montaje distinto del que corre en producción.

### D-8 · El JWKS se cachea con vencimiento y se refresca ante `kid` desconocido

Pedir las claves públicas en cada petición ataría la latencia de toda la API a la del proveedor de identidad. Cachearlas para siempre haría que una rotación de claves tumbara el servicio.

Se cachean con vencimiento, y además se refresca **bajo demanda** cuando llega un token cuyo `kid` no está en el caché — con un límite de frecuencia, para que un atacante que manda `kid` basura no convierta la validación en un martillo contra Keycloak.

### D-9 · `get_current_user` no valida el rol contra el catálogo

`auth.py` extrae el rol tal como viene en el token. Es `rbac.py` quien lo contrasta contra el catálogo.

La separación es lo que permitió avanzar: el catálogo dependía de `E-001`, que estuvo en discusión hasta el **20-ago-2026** (ver *Migration Plan*). Si `auth.py` enumerara los roles, la traba se habría comido también la identidad, que no tenía por qué esperar. ✅ **La enmienda ya está ratificada**, pero la separación se conserva: no era andamiaje para la espera, es la razón por la que un cambio de catálogo toca un archivo y no la identidad entera.

### D-10 · Un evento es un hecho, y su consumo restablece el contexto de tenant

Los tipos se nombran en pasado (`vehicle.created`), no en imperativo: quien publica informa lo que pasó, no ordena lo que hay que hacer.

El consumidor **restablece el contexto de tenant** con el `tenant_id` del sobre antes de tocar la base — el aislamiento no puede depender de estar dentro de un ciclo de petición y respuesta. Un evento sin `tenant_id` se rechaza en la publicación, no en el consumo: fallar cerca de la causa.

Se usan **consumer groups** de Redis Streams para tener confirmación explícita: un consumidor que cae sin confirmar deja el mensaje pendiente y otro lo retoma. Eso da "al menos una vez"; la no duplicación de efecto la aporta el consumidor reconociendo el `event_id` ya procesado.

Agotados los reintentos, el mensaje se copia a un stream de irrecuperables **con el motivo del último fallo** y se confirma en el original, para que uno malo no tape la cola.

### D-11 · El identificador que viaja en los errores sigue siendo el de correlación

Las convenciones de API de la KB nombran `trace_id` como extensión del Problem Details. `core/errors.py` ya emite `correlation_id`, alimentado por la cabecera `X-Request-ID`.

Se mantiene `correlation_id` en C-02 y **no se renombra**, por dos razones: es lo que hoy correlaciona respuesta y log, y C-03 introduce trazas distribuidas con un `trace_id` que es **otra cosa** —el identificador de la traza, no el de la petición—. Renombrar ahora obligaría a renombrar de nuevo en C-03, o peor, a que dos conceptos distintos compartan nombre.

C-03 decidirá si el cuerpo lleva los dos. Queda registrado como desvío consciente de la convención escrita.

### D-12 · Los tests de aislamiento corren contra servicios reales

Regla dura 8: sin mocks de base de datos. El aislamiento multi-tenant **no es simulable** — probarlo contra un doble prueba el doble. Los escenarios de concurrencia levantan dos sesiones simultáneas contra el PostgreSQL real del entorno de tests.

## Risks / Trade-offs

| Riesgo | Mitigación |
|---|---|
| ~~**`R-2` — no existe matriz RBAC canónica.**~~ ✅ Cerrado por [`ADR-024`](../../../../docs/adr/ADR-024-matriz-rbac-canonica.md). | La definición de permisos deja de ser vacía: se transcriben literalmente las celdas de los 7 módulos que el ADR declara. Los otros 9 **quedan denegados por denegar-por-defecto**, que es la decisión del ADR y no una omisión. |
| **La transcripción del ADR al código se desincroniza** con el tiempo, y nadie lo nota hasta que un endpoint autoriza de más. | La definición ejecutable es la traducción **literal** de las tablas, sin reinterpretación. La verificación automática de 6.9 detecta toda operación que se abra de más, y el ADR es el esperado contra el cual se compara. |
| **Sin herencia (`S3`), agregar un permiso a un rol no se lo da a los demás** — y es intuitivo suponer que `manager` los tiene todos. | La verificación recorre los tres roles de tenant **por separado**, sin asumir contención. `manager` no es superconjunto de `salesperson`: `salesperson` cierra ventas y `admin_staff` no, así que la jerarquía sería falsa. |
| ~~**`E-001` no ratifica, o ratifica distinto.** El catálogo de roles cambiaría.~~ ✅ **No se materializó**: ratificada el 20-ago-2026 **sin modificaciones al texto propuesto**, así que el catálogo quedó en los tres valores previstos. | La mitigación se conserva igual, porque nunca fue solo para este riesgo: `platform/authorization` se especifica en términos de comportamiento, no de nombres de rol, y el catálogo vive en un único lugar (spec: *"fuente única"*). Un cambio de valores toca un archivo y sus tests, no cada endpoint. |
| **El contexto de tenant se filtra entre requests por reutilización de conexión.** Sería una fuga cross-tenant, incidente P0. | `is_local = true` lo ata a la transacción, y hay un escenario dedicado que lo verifica: tras cerrar la transacción, el parámetro ya no está en esa conexión. |
| **Un módulo futuro usa `get_platform_session` por comodidad** y se saltea el aislamiento. | Test de arquitectura que recorre los routers y falla si aparece fuera del espacio administrativo. |
| **La tabla `platform_probe` queda para siempre** ocupando lugar en el esquema. | Es deliberado y está documentado: es el testigo que mantiene vivos los tests de aislamiento. Cuando existan tablas de negocio puede reevaluarse, pero eliminarla sin reemplazo dejaría el mecanismo sin prueba. |
| **La escritura extra de idempotencia** agrega latencia a cada creación. | Asumido en D-5. Es una fila por creación con clave, indexada por `(tenant_id, key)`. |

## Migration Plan

Este change no despliega nada: produce primitivas. La única migración de base es la de extensiones más la tabla `idempotency_keys` y `platform_probe`, todas reversibles.

~~**El orden de implementación no es libre.**~~ ✅ **Resuelto el 20-ago-2026**: `E-001` quedó ratificada y registrada (pasos (c) y (d) del Artículo 8; el (e), la comunicación, lo envía el usuario y no condiciona el código). La regla dura 12 queda satisfecha y **`core/rbac.py` ya se puede escribir**. El tramo 4 deja de estar bloqueado.

| Tramo | Contenido | Bloqueado por |
|---|---|---|
| **1** | Extensiones · `db/session.py` · `platform_probe` y sus tests de aislamiento | — |
| **2** | `core/auth.py` · completar `core/errors.py` · `pagination.py` · `idempotency.py` | — |
| **3** | `core/events.py` · `conftest.py` y factories | — |
| **4** | `core/rbac.py` y sus tests de autorización | ~~**`E-001`**~~ → ✅ **nada, desde el 20-ago-2026** |

Los tramos 1 a 3 son 8 de las 9 tareas. **El tramo 4 ya no espera**: `E-001` quedó ratificada y es lo único que lo frenaba.

**Reversión**: `alembic downgrade -1` por migración. Las primitivas son código nuevo sin consumidores todavía, así que revertirlas no rompe nada existente — es la ventaja de escribirlas antes del primer módulo.

## Open Questions

- **Vencimiento del caché de JWKS.** Ningún documento lo fija. Se arranca con un valor conservador y se ajusta con datos de operación; cambiarlo no toca specs ni tareas.
- **Techo de reintentos y base del backoff de eventos.** `ADR-009` fija el patrón, no los números. Se eligen valores iniciales razonables y quedan configurables.
- **Nombre definitivo del stream de irrecuperables.** Cosmético; no afecta el comportamiento especificado.

> **Lo que NO es una pregunta abierta**: la matriz de permisos —decidida por [`ADR-024`](../../../../docs/adr/ADR-024-matriz-rbac-canonica.md), se aplica y no se re-decide— ni el catálogo de roles (`E-001`, todavía bloqueante). Los dos cambiarían las tareas, así que están tratados arriba como bloqueante y riesgo, no diferidos acá.
