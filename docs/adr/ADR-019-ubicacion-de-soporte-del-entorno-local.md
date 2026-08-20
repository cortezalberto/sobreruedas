# ADR-019 — Ubicación de los archivos de soporte del entorno local

- **Estado**: Aceptado
- **Fecha**: 2026-08-13
- **Decisores**: Tech Lead
- **Resuelve**: hueco del §4.1 detectado al implementar `T-002`
- **Afecta**: `C-01` (T-002), `docker-compose.yml`, `docker-compose.test.yml`
- **Naturaleza**: **extensión de la estructura vinculante del §4.1.** El propio §4.1 establece que *"los cambios a la estructura requieren un ADR específico"*. Este es ese ADR.

---

## Contexto

`T-002` declara cuatro archivos a crear: `docker-compose.yml`, `docker-compose.test.yml`, `backend/Dockerfile` y `frontend-web/Dockerfile`. Pero sus **criterios de done exigen tres cosas más** que ninguno de esos cuatro archivos puede lograr por sí solo:

> • *Postgres accesible en `localhost:5432` con extensiones `pgcrypto`, `pg_trgm` y `postgis` presentes.*
> • *Keycloak admin accesible en `localhost:8080` con realm `deruedas-dev` creado.*
> • *MinIO admin accesible en `localhost:9001` con bucket `deruedas-media` creado al startup.*

Las tres necesitan artefactos de configuración:

| Necesidad | Qué hace falta |
|---|---|
| Extensiones de PostgreSQL | Un `.sql` en `/docker-entrypoint-initdb.d/` del contenedor |
| Realm de Keycloak | Un `.json` de importación montado, y `--import-realm` al arrancar |
| Bucket de MinIO | Resoluble **sin archivo**: un servicio efímero con el cliente `mc` |

Los dos primeros exigen archivos versionados. La tarea 3.3 de `tasks.md` lo dice explícitamente: *"versionar el archivo de importación del realm"*.

**Y el §4.1 no tiene dónde ponerlos.** Su rama `infra/` enumera exactamente tres hijos: `terraform/`, `k8s/` y `observability/`. Ninguno corresponde: los tres primeros son infraestructura *desplegada*; esto es configuración del entorno *local*, que según `design.md` D-7 nunca sale de Docker Compose.

Esto **no es una contradicción entre fuentes**. Es un hueco: `T-002` pide un resultado y no dice dónde viven los insumos.

## Decisión

Se extiende `infra/` con un cuarto hijo, **`infra/local/`**, para los archivos de soporte del entorno de desarrollo:

```
infra/
├── terraform/                       # §4.1 — IaC del entorno cloud
├── k8s/                             # §4.1 — manifests
├── observability/                   # §4.1 — prometheus, grafana, loki
└── local/                           # ← este ADR
    ├── postgres/
    │   └── init/
    │       └── 01-extensions.sql    # extensiones habilitadas al primer arranque
    └── keycloak/
        └── deruedas-dev-realm.json  # realm importado al arrancar
```

El bucket de MinIO **no lleva archivo**: lo crea un servicio efímero `minio-init` en el compose, con la imagen `minio/mc`. Menos superficie versionada para el mismo resultado.

### Por qué `infra/local/` y no otra cosa

**Es extensión, no contradicción.** Los tres hijos que el §4.1 nombra siguen existiendo, con su contenido y su propósito intactos. Se agrega un cuarto hermano; no se mueve ni se reinterpreta nada.

**El criterio de agrupación de `infra/` se sostiene**: todo lo que no es código de aplicación y define dónde y cómo corren las cosas. `local/` es exactamente eso para la máquina del desarrollador.

**El nombre dice la frontera.** `design.md` D-7 fija que Docker Compose es el entorno de desarrollo y Kubernetes empieza en staging. Que el directorio se llame `local` hace visible esa línea: nadie va a confundir `infra/local/` con algo que se despliega.

> ⚠️ **Nota del 17-ago-2026**: [`ADR-023`](ADR-023-despliegue-sobre-vps-con-docker-compose.md) eliminó Kubernetes — staging también corre Docker Compose. **La decisión de este ADR no cambia** (el directorio sigue llamándose `infra/local/`), pero su justificación sí: la frontera ya no es entre dos tecnologías, es entre dos entornos de la misma. El nombre pasa a valer más, no menos, porque ahora nada distingue local de staging salvo el nombre y el override.

## Consecuencias

- **`docker-compose.yml` monta desde `infra/local/`.** Las rutas quedan explícitas en el compose, no escondidas en imágenes propias.
- **El init de PostgreSQL corre una sola vez**, en la creación del volumen `pg_data`. Si se agregan extensiones después, hay que recrear el volumen (`docker compose down -v`) o aplicarlas por migración. Queda documentado en el propio `.sql`.
- **El realm `deruedas-dev` es de desarrollo, no de producción.** C-05 lo va a modificar; se versiona para que ese cambio sea revisable en un diff y no un click en una consola web que nadie recuerda haber hecho.
- **El §4.1 queda extendido, no violado.** Cualquier lector que compare el árbol real contra el plan encuentra este ADR como explicación del cuarto directorio.
- **No se toca `docs/sdd/`.** El plan sigue diciendo lo que dijo siempre; este ADR es el registro, igual que en [`ADR-016`](ADR-016-trazas-distribuidas-tempo.md) y [`ADR-018`](ADR-018-anclas-de-adr-del-plan-de-implementacion.md).

## Alternativas consideradas

**Colgar los archivos de `tools/`.** No requiere ADR, porque `tools/` ya existe en el §4.1. Descartada porque el §4.1 le da a `tools/` un propósito distinto —`seed.py` y `benchmark/`, o sea utilidades ejecutables— y meter ahí configuración declarativa de contenedores diluye el criterio de ambos directorios. Un directorio que aloja cualquier cosa deja de informar.

**Ponerlos en la raíz del repositorio** (`postgres-init/`, `keycloak/`). Es lo que hacen muchos proyectos y no requiere anidar. Descartada porque el §4.1 define la raíz de forma cerrada y explícita; agregar dos directorios de primer nivel es mucho más invasivo que agregar un hermano dentro de `infra/`, que ya es el lugar conceptualmente correcto.

**Evitar los archivos por completo.** Las extensiones se pueden crear desde la migración baseline de Alembic, y el realm se puede armar por API con un script. Descartada por dos razones: la tarea 3.3 pide explícitamente **versionar el archivo** del realm, y la baseline `000_baseline.py` está especificada como **vacía** en la tarea 6.3. Además, un realm construido por llamadas a la API es mucho más difícil de revisar que un JSON que diffea.

**Un `Dockerfile` propio de PostgreSQL con las extensiones ya adentro.** Evita el montaje y garantiza el estado. Descartada porque obliga a construir y mantener una imagen propia para algo que la imagen oficial resuelve con un archivo montado, y porque alarga el arranque en frío contra el presupuesto de tres minutos de `T-002`.
