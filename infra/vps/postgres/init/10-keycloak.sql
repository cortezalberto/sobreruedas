-- ─────────────────────────────────────────────────────────────────────────────
-- Base y rol propios para Keycloak — ADR-025 Decision 4
--
-- Lo ejecuta el servicio efimero `keycloak-db-init` del override de produccion,
-- NO el mecanismo de initdb de PostgreSQL.
--
-- POR QUE NO ES UN SCRIPT DE initdb
--
-- Los scripts de /docker-entrypoint-initdb.d corren UNA sola vez, y solo cuando
-- el directorio de datos esta VACIO. La base de Keycloak es un requisito nuevo
-- (ADR-025, 17-ago-2026): sobre una instalacion que ya tiene datos, ese
-- mecanismo no correria nunca y Keycloak arrancaria contra una base inexistente.
--
-- Ademas el montaje era imposible: el archivo base ya monta el directorio
-- /docker-entrypoint-initdb.d de solo lectura, y Docker no puede crear un punto
-- de montaje adentro de un montaje read-only. Detectado el 17-ago-2026
-- reproduciendo la topologia en la maquina local.
--
-- Por eso es idempotente y corre en CADA arranque del stack de datos: la
-- primera vez crea, las siguientes no hace nada. Mismo patron que `minio-init`.
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

\set ON_ERROR_STOP on

\set kc_user  `echo "${KEYCLOAK_DB_USER:?falta KEYCLOAK_DB_USER}"`
\set kc_pass  `echo "${KEYCLOAK_DB_PASSWORD:?falta KEYCLOAK_DB_PASSWORD}"`
\set kc_db    `echo "${KEYCLOAK_DB_NAME:-keycloak}"`

-- El rol. NOSUPERUSER y NOBYPASSRLS por el mismo criterio que ADR-020 le aplica
-- al rol de aplicacion: ningun rol de servicio necesita saltear RLS, y el que
-- puede hacerlo termina haciendolo por accidente.
--
-- `\gexec` ejecuta el texto que devuelve la consulta. Es la forma de tener un
-- "CREATE ROLE IF NOT EXISTS", que PostgreSQL no ofrece.
SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS',
    :'kc_user', :'kc_pass'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'kc_user')
\gexec

-- La clave se re-aplica siempre: si rota en el archivo de secretos, esta linea
-- la sincroniza sin que haya que borrar nada.
SELECT format('ALTER ROLE %I PASSWORD %L', :'kc_user', :'kc_pass')
\gexec

-- CREATE DATABASE no puede ir adentro de una transaccion ni de un bloque DO.
SELECT format('CREATE DATABASE %I OWNER %I', :'kc_db', :'kc_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'kc_db')
\gexec

SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'kc_db')
\gexec

SELECT format('GRANT ALL PRIVILEGES ON DATABASE %I TO %I', :'kc_db', :'kc_user')
\gexec

SELECT format(
    'COMMENT ON DATABASE %I IS %L',
    :'kc_db',
    'Identidad de Keycloak (ADR-025). Separada de la base de negocio; comparte '
    'instancia para quedar cubierta por el archivado de WAL de la tarea 9.21.'
)
\gexec

\echo 'keycloak-db-init: rol y base verificados'
