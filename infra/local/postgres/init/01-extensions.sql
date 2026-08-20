-- ─────────────────────────────────────────────────────────────────────────────
-- Extensiones de PostgreSQL 16 — entorno local
--
-- Ubicacion fijada por docs/adr/ADR-019-ubicacion-de-soporte-del-entorno-local.md
-- Tarea 3.2 de C-01 (T-002).
--
-- ⚠️ ESTE ARCHIVO CORRE UNA SOLA VEZ: el entrypoint de la imagen oficial de
--    PostgreSQL ejecuta /docker-entrypoint-initdb.d/*.sql SOLO cuando el
--    directorio de datos esta vacio, es decir al crear el volumen pg_data.
--
--    Si agregas una extension aca despues del primer arranque, NO se aplica.
--    Para aplicarla, una de dos:
--      a) docker compose down -v   (destruye los datos locales y recrea)
--      b) CREATE EXTENSION a mano, y ademas en una migracion de Alembic para
--         que llegue a staging y produccion — donde este archivo no corre.
--
--    En staging y produccion las extensiones las instala Terraform sobre la
--    base gestionada (design.md D-7). Este archivo es SOLO para desarrollo.
-- ─────────────────────────────────────────────────────────────────────────────

-- Funciones criptograficas: hashes y gen_random_bytes.
-- OJO: NO se usa para contrasenas de usuario. La autenticacion se delega
-- enteramente a Keycloak (ADR-007, Art. 3) y la aplicacion nunca las toca.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Similitud trigram: busqueda difusa y LIKE indexado.
-- Sostiene la busqueda por patente, marca y modelo con errores de tipeo.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Tipos y operadores geoespaciales: ubicacion de sucursales y radio de busqueda.
CREATE EXTENSION IF NOT EXISTS postgis;

-- Generacion de UUID. gen_random_uuid() ya viene en el core desde PostgreSQL 13,
-- pero el stack declarado la nombra explicitamente y se habilita por paridad.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
