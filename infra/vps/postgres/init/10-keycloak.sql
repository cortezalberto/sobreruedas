-- ─────────────────────────────────────────────────────────────────────────────
-- Base y rol propios para Keycloak — ADR-025 Decision 4
--
-- Corre UNA SOLA VEZ, al crear el volumen de PostgreSQL, despues de los init
-- del entorno base (01-extensions, 02-rol-de-aplicacion) porque el prefijo `10`
-- ordena despues. Docker ejecuta /docker-entrypoint-initdb.d en orden
-- alfabetico y monta este directorio en el subdirectorio `vps`.
--
-- POR QUE EN LA MISMA INSTANCIA Y NO EN UN POSTGRESQL APARTE
--
-- Sobre un nodo unico, un segundo PostgreSQL duplica memoria y superficie de
-- backup sin agregar aislamiento real: comparten disco, kernel y destino. Y hay
-- un argumento positivo — al vivir aca, la identidad queda cubierta por el
-- archivado de WAL de la tarea 9.21 SIN TRABAJO ADICIONAL. Perder los datos de
-- identidad es tan grave como perder los de negocio.
--
-- El aislamiento que si importa se mantiene: base y rol propios, sin ningun
-- acceso al esquema de la aplicacion.
-- ─────────────────────────────────────────────────────────────────────────────

\set keycloak_user `echo "$KEYCLOAK_DB_USER"`
\set keycloak_password `echo "$KEYCLOAK_DB_PASSWORD"`
\set keycloak_db `echo "${KEYCLOAK_DB_NAME:-keycloak}"`

-- Rol de Keycloak. NOSUPERUSER y NOBYPASSRLS por el mismo criterio que ADR-020
-- le aplica al rol de aplicacion: ningun rol de servicio necesita saltear RLS,
-- y el que puede hacerlo termina haciendolo por accidente.
CREATE ROLE :"keycloak_user"
    LOGIN
    PASSWORD :'keycloak_password'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOBYPASSRLS;

CREATE DATABASE :"keycloak_db" OWNER :"keycloak_user";

COMMENT ON DATABASE :"keycloak_db" IS
    'Identidad de Keycloak (ADR-025). Separada de la base de negocio; comparte '
    'instancia para quedar cubierta por el archivado de WAL de la tarea 9.21.';

-- Keycloak es dueno de SU base y de nada mas. Sin esto, el rol podria leer el
-- catalogo de la base de negocio.
REVOKE ALL ON DATABASE :"keycloak_db" FROM PUBLIC;
GRANT ALL PRIVILEGES ON DATABASE :"keycloak_db" TO :"keycloak_user";
