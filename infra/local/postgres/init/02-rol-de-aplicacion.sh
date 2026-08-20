#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Rol de aplicacion `mitutu` — sin capacidad de saltear RLS
#
# Ubicacion fijada por docs/adr/ADR-019-ubicacion-de-soporte-del-entorno-local.md
# Decidido por  docs/adr/ADR-020-rol-de-conexion-sin-bypass-de-rls.md
# Change        openspec/changes/rol-de-base-sin-bypass-rls/ (design.md D-1, D-2, D-3)
#
# ⚠️ ESTE ARCHIVO CORRE UNA SOLA VEZ, igual que 01-extensions.sql: el entrypoint
#    de la imagen ejecuta /docker-entrypoint-initdb.d/* SOLO cuando el directorio
#    de datos esta vacio, o sea al CREAR el volumen.
#
#    Si ya tenias el entorno levantado antes de este change, el rol no existe y
#    el backend no va a poder conectarse. Para crearlo:
#
#        docker compose down -v && docker compose up -d
#
#    `tools/check-services.sh` detecta este caso y te lo dice con esas palabras.
#
# ─────────────────────────────────────────────────────────────────────────────
# POR QUE HAY DOS ROLES Y NO UNO
#
# El rol con el que la aplicacion se conectaba era el POSTGRES_USER, o sea
# superusuario con `rolbypassrls`. Un rol asi IGNORA todas las politicas RLS: no
# las evalua, pasa de largo. La capa 2 del aislamiento multi-tenant (ADR-006)
# existia en el catalogo y no hacia nada.
#
# No alcanza con quitarle el atributo al rol actual: seguiria siendo DUENO de
# las tablas, y el dueno puede `ALTER TABLE ... NO FORCE ROW LEVEL SECURITY`
# sin ningun privilegio especial. El aislamiento quedaria a una sentencia de
# distancia de cualquier codigo — o de cualquier inyeccion.
#
#   PROPIETARIO ($POSTGRES_USER)  crea el esquema, corre las migraciones.
#                                 NO atiende trafico.
#   APLICACION  ($APP_DB_USER)    SELECT / INSERT / UPDATE y nada mas.
#                                 Es el del DATABASE_URL del backend.
#
# ─────────────────────────────────────────────────────────────────────────────
# POR QUE .sh Y NO .sql
#
# El nombre y la credencial del rol salen del entorno, y un .sql en
# docker-entrypoint-initdb.d no lee variables de entorno.
#
# APP_DB_USER / APP_DB_PASSWORD son variables DEL CONTENEDOR DE LA BASE, no de
# la aplicacion — mismo estatus que POSTGRES_USER / POSTGRES_PASSWORD. Por eso
# no entran en ADR-013 ni en .env.example, que son el inventario de la
# configuracion de la APLICACION.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROL="${APP_DB_USER:-mitutu}"
CLAVE="${APP_DB_PASSWORD:-mitutu}"

echo "[init] creando el rol de aplicacion '${ROL}' (NOSUPERUSER NOBYPASSRLS)"

# `-v` pasa variables a psql, que las interpola de forma segura:
#   :"nombre"  -> identificador entrecomillado
#   :'valor'   -> literal entrecomillado
#
# Es la unica forma correcta de meter un nombre de rol en DDL: un identificador
# NO puede ser parametro bindeado, asi que la alternativa seria concatenar
# — justo lo que prohibe la regla dura 9.
#
# El heredoc va con 'EOSQL' entrecomillado para que el SHELL no toque nada: las
# sustituciones las hace psql, no bash.
psql -v ON_ERROR_STOP=1 \
     -v rol="$ROL" \
     -v clave="$CLAVE" \
     -v db="$POSTGRES_DB" \
     --username "$POSTGRES_USER" \
     --dbname "$POSTGRES_DB" <<-'EOSQL'

    -- Sin IF NOT EXISTS a proposito: este script corre una sola vez sobre un
    -- cluster recien creado. Si el rol ya existiera, algo no es lo que se cree
    -- que es, y ON_ERROR_STOP corta el init entero. Un init que sigue de largo
    -- ante lo inesperado deja una base a medio configurar que parece sana.
    CREATE ROLE :"rol" WITH
        LOGIN
        PASSWORD :'clave'
        NOSUPERUSER      -- un superusuario saltea RLS aunque NOBYPASSRLS este puesto
        NOBYPASSRLS      -- el atributo exacto que ADR-020 encontro prendido
        NOCREATEDB
        NOCREATEROLE
        NOINHERIT        -- una pertenencia futura a un rol de grupo no le devuelve privilegios
        NOREPLICATION;

    GRANT CONNECT ON DATABASE :"db" TO :"rol";
    GRANT USAGE ON SCHEMA public TO :"rol";

    -- PostgreSQL 15+ ya no le da CREATE en `public` a PUBLIC, pero se revoca
    -- explicitamente: que la garantia dependa del default de la version es
    -- confiar en algo que ninguna imagen promete. Lo verifica el test 1.3.
    REVOKE CREATE ON SCHEMA public FROM PUBLIC;

    -- ── Permisos por defecto (design.md D-3) ─────────────────────────────────
    --
    -- SIN `FOR ROLE`: aplica al rol que ejecuta ESTA sentencia, o sea el
    -- propietario. Eso lo hace agnostico de como se llame — `deruedas` en
    -- desarrollo, `deruedas_test` en el compose de tests — y alcanza a toda
    -- tabla que ese rol cree de aca en adelante.
    --
    -- Asi la friccion que ADR-020 asumia ("cada tabla nueva necesita GRANT")
    -- desaparece. A cambio, un default privilege es SILENCIOSO cuando no se
    -- aplica: por eso hay ademas un test que recorre el catalogo y falla si a
    -- alguna tabla con tenant_id le faltan los permisos.
    --
    -- SIN DELETE NI TRUNCATE (design.md D-4): la regla dura 3 prohibe el
    -- borrado fisico. Negarlo aca convierte esa convencion en garantia de la
    -- base, y cubre el DELETE que llegue por una via no prevista. Si una tabla
    -- lo necesita por retencion legal, se otorga nombrado en SU migracion.
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE ON TABLES TO :"rol";

    -- Hoy los PK son UUID y ninguna secuencia esta en juego. Se otorga igual:
    -- el dia que una tabla use `identity`, el fallo aparecria como un
    -- "permission denied for sequence" lejos de su causa.
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT USAGE ON SEQUENCES TO :"rol";

EOSQL

echo "[init] rol '${ROL}' listo"
