# ADR-025 — Topología de producción: stack partido, Caddy, y migraciones compatibles hacia atrás

- **Estado**: ✅ **Aceptado** — ratificado el 2026-08-17
- **Fecha**: 2026-08-17
- **Decisores**: Tech Lead
- **Governance**: **ALTA** — define el despliegue de producción y agrega una regla vinculante de migraciones
- **Deriva de**: [`ADR-023`](ADR-023-despliegue-sobre-vps-con-docker-compose.md), que dejó tres puntos sin cerrar
- **Afecta**: `C-01` bloque 9, `docker-compose.yml`, `alembic/`, regla dura nueva en `CLAUDE.md`
- **Resuelve**: la elección de reverse proxy que `ADR-023` dejó abierta · la imposibilidad de duplicar servicios con estado · la persistencia de Keycloak en producción

---

## Contexto

`ADR-023` decidió VPS único con Docker Compose y describió el despliegue azul-verde así:

> *"Dos stacks de Compose conviviendo y un reverse proxy cuyo upstream determina cuál recibe tráfico."*

Al bajar eso al `docker-compose.yml` real —diez servicios— la descripción **no se sostiene literalmente**, y aparecen tres decisiones que `ADR-023` no tomó:

1. Dejó el reverse proxy como *"(Caddy o Traefik)"*, sin elegir.
2. Habló de "dos stacks" sin distinguir qué servicios pueden duplicarse y cuáles no.
3. No dijo nada de Keycloak, que hoy corre en un modo que pierde todos los datos al reiniciar.

Este ADR cierra los tres.

## Decisión 1 — El stack se parte en dos: datos y aplicación

**De los diez servicios, cinco tienen estado y no pueden duplicarse.** Levantar un segundo PostgreSQL sobre el mismo volumen no es un despliegue azul-verde: es corrupción de datos.

| Stack | Proyecto Compose | Servicios | Ciclo de vida |
|---|---|---|---|
| **Datos** | `deruedas-datos` | `postgres`, `redis`, `minio`, `opensearch`, `keycloak` | **Uno solo, permanente.** No se toca en un despliegue ordinario. |
| **Aplicación** | `deruedas-azul` / `deruedas-verde` | `backend`, `worker`, `frontend-web` | **Dos, alternándose.** Es lo único que el proxy conmuta. |

Los stacks de aplicación alcanzan al de datos por una red **externa** creada una sola vez (`deruedas_default`), no por una red por proyecto.

`mailhog` no existe en producción: es un capturador de correo de prueba, y dejarlo haría que producción **no envíe un solo mail** —ni recuperación de cuenta ni notificaciones— fallando en silencio.

### Consecuencia que se asume explícitamente: la reversión deja de ser gratis

`ADR-023` afirmaba que revertir no hace falta, *"basta con no conmutar"*. **Eso vale para el código, no para la base.**

Como el stack de datos es único y compartido, una migración de Alembic que rompa hacia atrás **inutiliza el stack viejo en el momento en que corre** — y el stack viejo es justamente la red de seguridad del azul-verde. El humo puede pasar, la conmutación puede hacerse, y el camino de vuelta ya no existe.

Esto no se resuelve con infraestructura. Se resuelve con la Decisión 2.

## Decisión 2 — Toda migración debe ser compatible con la versión anterior de la aplicación (regla vinculante)

**Regla**: una migración solo puede desplegarse si la versión de la aplicación **inmediatamente anterior sigue funcionando** contra el esquema resultante.

En la práctica, *expand / contract* en tres despliegues:

| Fase | Qué se hace | Qué NO se hace |
|---|---|---|
| **Expand** | Agregar columna *nullable* o con default. Agregar tabla. Agregar valor de enum. | `NOT NULL` sin default en un solo paso. |
| **Migrar** | Backfill de datos. Cambiar la aplicación para escribir en lo nuevo y leer de ambos. | Dejar de escribir lo viejo. |
| **Contract** | **En un despliegue posterior**, borrar lo viejo. | Borrar en el mismo despliegue que deja de usarlo. |

Prohibiciones concretas que se derivan:

- **Nunca renombrar** una columna o tabla en un paso. Se agrega la nueva, se backfillea, se conmuta la lectura, y se borra después.
- **Nunca borrar** una columna o tabla en el mismo despliegue en que la aplicación deja de usarla.
- **Nunca quitar** un valor de enum en el mismo despliegue en que deja de emitirse.
- **Nunca** agregar una constraint que el dato existente no cumpla, sin backfill previo.

> Esta regla es **nueva** y no está hoy en ningún documento del proyecto. Si se ratifica este ADR, entra como **regla dura** en `CLAUDE.md`.

### Cómo se hace cumplir — dos gates, no buena voluntad

Una regla de proceso que depende de que alguien se acuerde no es un gate. Es el mismo criterio que `ADR-023` le aplicó a `gitleaks`. Se implementa en dos capas, barata primero:

**Gate 1 — lint de DDL destructivo (barato, atrapa la mayoría).** Un test recorre las migraciones nuevas respecto de `main` y falla ante `DROP COLUMN`, `DROP TABLE`, `RENAME`, `SET NOT NULL` y `ALTER COLUMN ... TYPE` que estreche el tipo. La fase *contract* es legítima, así que el gate se levanta con un marcador explícito en la migración:

```python
# migracion-contract: la columna quedó sin uso desde <revisión anterior>
```

El marcador no debilita el gate: lo convierte en **deliberado y revisable en el diff**, que es el punto. Sin marcador, falla.

**Gate 2 — la suite anterior contra el esquema nuevo (caro, atrapa el resto).** En CI: aplicar las migraciones de la rama, y correr **los tests de integración del commit anterior** contra ese esquema. Si la versión previa de la aplicación deja de funcionar, el azul-verde perdió su red de seguridad y el gate lo dice antes de mergear, no en producción.

El gate 2 es la definición operativa de la regla —dice exactamente lo que la regla afirma— pero cuesta una corrida extra de integración (~1m15s hoy). El gate 1 atrapa barato el caso común. Van los dos.

### El worker no puede consumir mientras espera

Detectado al bajar el diseño: durante los **cinco minutos de humo**, el stack nuevo está levantado pero el proxy todavía no conmutó. Si el `worker` del stack inactivo se conecta al broker compartido, **empieza a consumir trabajo real de producción antes de ser promovido**. Un despliegue malo afectaría los trabajos en segundo plano aunque el upstream nunca se mueva, y el humo —que solo mira HTTP— no lo detectaría.

**El stack inactivo levanta con `worker` en cero réplicas.** Se escala al promover, y se baja el del stack saliente. El humo corre contra `backend` y `frontend-web` únicamente.

> ⚠️ **Hoy esto es preventivo**: Celery **no está implementado**. Solo existe el campo `celery_broker_url` en `config.py:138`; el servicio `worker` del `docker-compose.yml` invoca `celery -A app.core.events`, y `app/core/events.py` es el publisher de Redis Streams, sin app de Celery. **Ese servicio no arranca hoy.** Es deuda preexistente, ajena a este ADR, pero la topología se diseña ya para cuando exista.

## Decisión 3 — Caddy como reverse proxy

`ADR-023` dejó *"Caddy o Traefik"*. Se elige **Caddy**, por tres razones específicas de este caso:

- **TLS automático sin configuración**, que es literalmente lo que pide la tarea 9.4.
- **Su recarga de configuración es *graceful*: no corta conexiones establecidas ni descarta peticiones en vuelo.** Es exactamente la primitiva que el azul-verde necesita. La conmutación se implementa renderizando el `Caddyfile` desde una plantilla con el color activo y recargando — el cambio queda visible en un diff, que es preferible a un `PATCH` por índice contra la API de administración, frágil ante cualquier reordenamiento de rutas.
- El `Caddyfile` de este caso entra en unas veinte líneas. El equivalente en Traefik son labels repartidas por cada servicio, que acoplan la configuración del proxy al archivo de cada stack.

**Traefik sería mejor** si hubiera descubrimiento dinámico de muchos servicios, o múltiples nodos. Sobre un nodo único con tres servicios conmutables es complejidad sin contrapartida — el mismo argumento con el que `ADR-023` descartó k3s.

## Decisión 4 — Keycloak con base propia dentro del mismo PostgreSQL

**Hoy Keycloak corre con `start-dev`, que usa una H2 embebida en el contenedor.** En local está bien. En producción significa que **usuarios, realms y credenciales se pierden en cada reinicio del contenedor**. No es un riesgo teórico: es la primera vez que se reinicie.

Producción usa:

- `start` en lugar de `start-dev`
- `KC_DB=postgres`, con **base y rol propios dentro de la misma instancia de PostgreSQL** — no un contenedor de PostgreSQL aparte
- `KC_HOSTNAME` explícito y `KC_PROXY_HEADERS=xforwarded`, con TLS terminado en Caddy
- Realm importado **una sola vez**, no en cada arranque

**Por qué la misma instancia y no una separada**: sobre un nodo único, un segundo PostgreSQL duplica memoria y superficie de backup sin agregar aislamiento real —comparten disco, kernel y destino—. Y hay un argumento positivo: al vivir en la misma instancia, **la identidad queda cubierta por el archivado de WAL de la tarea 9.21 sin trabajo adicional**. Perder los datos de identidad es tan grave como perder los de negocio, y así se respalda por construcción.

Se mantiene el aislamiento que sí importa: base y rol propios, sin acceso al esquema de la aplicación.

## Consecuencias

### A favor

- El azul-verde queda **descrito con precisión** y es implementable. La descripción de `ADR-023` no lo era.
- La regla de migraciones convierte la reversión en algo real en vez de una promesa que la primera migración destructiva rompe.
- Caddy da conmutación sin cortar conexiones, que era el punto.
- Keycloak deja de perder la identidad en cada reinicio.

### En contra — asumidas

- **El stack de datos es punto único de fallo dentro del punto único de fallo.** Un despliegue no lo toca, pero tampoco lo protege. Se suma a lo ya escalado en [`ESC-001`](../escalaciones/ESC-001-sla-sobre-nodo-unico.md).
- **La regla de migraciones agrega fricción real** a todo cambio de esquema: lo que era una migración pasa a ser tres despliegues. Es el precio de que la reversión exista.
- **Tres archivos de Compose** en vez de uno. Se mitiga manteniendo `docker-compose.yml` como base única y las diferencias como override, según `ADR-023` §Notas.
- Caddy tiene comunidad menor que Traefik y menos ejemplos para casos raros.

## Alternativas consideradas

**Duplicar el stack completo, datos incluidos.** Sería azul-verde de verdad, con reversión intacta. Descartada porque exige replicación de PostgreSQL y un mecanismo de promoción, que es la redundancia que `ADR-023` decidió no pagar. Además no cabe en un nodo.

**No hacer azul-verde: `docker compose up` y listo.** Más simple, pero incumple el requisito de reversión de `platform/delivery-pipeline` y deja una ventana de caída en cada despliegue, contra un presupuesto Enterprise de 43 minutos al mes.

**Keycloak con PostgreSQL propio en contenedor separado.** Más aislamiento nominal. Descartada por el argumento de arriba: sobre un nodo único el aislamiento es aparente y el costo de backup es real.

**Migraciones sin regla, revirtiendo la base con backup.** Descartada: restaurar un backup pierde todo lo escrito desde el despliegue. Convierte una reversión de minutos en un incidente con pérdida de datos.

## Impacto sobre el bloque 9

Las 22 tareas actuales no cubren la persistencia de Keycloak, el retiro de `mailhog`, la seguridad de OpenSearch ni la regla de migraciones. Si se ratifica:

- Bloque 9 pasa de **22 a ~26 tareas**
- `C-01` pasa de **66/91 a 66/95**
- Entra una **regla dura nueva** en `CLAUDE.md` (migraciones compatibles hacia atrás), con su test
