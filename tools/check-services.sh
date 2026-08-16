#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Smoke test del entorno local — tarea 3.8 de C-01 (T-002).
#
#   tools/check-services.sh
#
# Pingea cada servicio de docker-compose.yml y reporta OK/FAIL. Sale con codigo
# 1 si algo falla, para que sirva tanto a mano como dentro de un pipeline.
#
# Los tres servicios de aplicacion (backend, worker, frontend-web) se reportan
# como PENDIENTE mientras no exista su codigo: T-005 crea backend/pyproject.toml
# y T-006 crea frontend-web/package.json. Un servicio que todavia no se puede
# construir NO es una falla del entorno, y contarlo como error entrenaria a
# ignorar el rojo — que es la peor cosa que le podes hacer a un chequeo.
#
# Marcadores ASCII a proposito: la consola de Windows es cp1252 y revienta con
# simbolos Unicode.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

FALLAS=0
PENDIENTES=0

# Los puertos del host son configurables en docker-compose.yml. Este script
# tiene que leer los MISMOS overrides: si no, verifica una direccion donde
# puede haber otra aplicacion entera respondiendo, y el resultado es peor que
# no verificar nada.
[ -f .env ] && . ./.env 2>/dev/null
: "${POSTGRES_PORT:=5432}"
: "${REDIS_PORT:=6379}"
: "${OPENSEARCH_PORT:=9200}"
: "${KEYCLOAK_PORT:=8080}"
: "${MINIO_PORT:=9000}"
: "${MAILHOG_WEB_PORT:=8025}"
: "${BACKEND_PORT:=8000}"
: "${FRONTEND_PORT:=3000}"

ok()        { printf '  [OK]        %-14s %s\n' "$1" "$2"; }
fallo()     { printf '  [FAIL]      %-14s %s\n' "$1" "$2"; FALLAS=$((FALLAS + 1)); }
pendiente() { printf '  [PENDIENTE] %-14s %s\n' "$1" "$2"; PENDIENTES=$((PENDIENTES + 1)); }

# Responde 2xx/3xx en la URL indicada.
check_http() {
  local nombre="$1" url="$2" detalle="$3"
  if curl -fsS --max-time 5 "$url" > /dev/null 2>&1; then
    ok "$nombre" "$detalle"
  else
    fallo "$nombre" "sin respuesta en $url"
  fi
}

# Ejecuta un comando adentro de un contenedor del compose.
check_exec() {
  local nombre="$1" servicio="$2" detalle="$3"; shift 3
  if docker compose exec -T "$servicio" "$@" > /dev/null 2>&1; then
    ok "$nombre" "$detalle"
  else
    fallo "$nombre" "el contenedor no respondio"
  fi
}

echo
echo "Entorno local de deRuedas Gestion"
echo "─────────────────────────────────────────────────────────────────"

if ! docker compose version > /dev/null 2>&1; then
  echo "  [FAIL]      docker         'docker compose' no esta disponible"
  echo
  exit 1
fi

if ! docker info > /dev/null 2>&1; then
  echo "  [FAIL]      docker         el daemon no esta corriendo"
  echo "                             arranca Docker Desktop y volve a intentar"
  echo
  exit 1
fi

echo
echo "Infraestructura"
check_exec "postgres"  postgres "acepta conexiones" \
           pg_isready -U "${POSTGRES_USER:-deruedas}" -d "${POSTGRES_DB:-deruedas}"
check_exec "redis"     redis    "responde al ping" redis-cli ping
check_http "opensearch" "http://localhost:${OPENSEARCH_PORT}/_cluster/health" "cluster respondiendo"
check_http "keycloak"   "http://localhost:${KEYCLOAK_PORT}/realms/${KEYCLOAK_REALM:-deruedas-dev}/.well-known/openid-configuration" \
           "realm ${KEYCLOAK_REALM:-deruedas-dev} publicado"
check_http "minio"      "http://localhost:${MINIO_PORT}/minio/health/live" "storage vivo"
check_http "mailhog"    "http://localhost:${MAILHOG_WEB_PORT}/" "interfaz web arriba"

echo
echo "Criterios de done de T-002"

# Extensiones de PostgreSQL. Se piden las tres que el plan nombra explicitamente.
EXT_SQL="SELECT count(*) FROM pg_extension WHERE extname IN ('pgcrypto','pg_trgm','postgis');"
EXT=$(docker compose exec -T postgres \
        psql -tAU "${POSTGRES_USER:-deruedas}" -d "${POSTGRES_DB:-deruedas}" -c "$EXT_SQL" 2>/dev/null | tr -d '[:space:]')
if [ "$EXT" = "3" ]; then
  ok "extensiones" "pgcrypto, pg_trgm y postgis presentes"
else
  fallo "extensiones" "se esperaban 3, hay '${EXT:-ninguna}' — recrea el volumen con 'docker compose down -v'"
fi

# Rol de aplicacion sin BYPASSRLS (ADR-020). Lo crea el init 02, que —igual que
# el de extensiones— corre UNA SOLA VEZ, al crear el volumen.
#
# Sin este chequeo, quien tenga el entorno de antes de ADR-020 se encuentra con
# un "password authentication failed for user mitutu" al levantar el backend.
# Eso se lee como credencial mal copiada y manda a editar el .env, que no tiene
# la culpa y donde no hay nada que arreglar.
#
# El nombre del rol NO se interpola en el SQL: se traen todos los roles y se
# filtra en el shell. Ademas de evitar armar SQL por concatenacion (regla dura
# 9), esquiva que `psql -c` no sustituya variables `-v` — que es como este
# chequeo dio un falso "no existe" la primera vez que se escribio.
ROL_APP="${APP_DB_USER:-mitutu}"
ROL_SQL="SELECT rolname, rolsuper::int + rolbypassrls::int FROM pg_roles;"
ROL=$(docker compose exec -T postgres \
        psql -tAU "${POSTGRES_USER:-deruedas}" -d "${POSTGRES_DB:-deruedas}" \
             -c "$ROL_SQL" 2>/dev/null | tr -d '[:blank:]' | grep "^${ROL_APP}|" | cut -d'|' -f2)
if [ -z "$ROL" ]; then
  fallo "rol de app" "'$ROL_APP' no existe — recrea el volumen con 'docker compose down -v' (ADR-020)"
elif [ "$ROL" = "0" ]; then
  ok "rol de app" "'$ROL_APP' existe y no puede saltear RLS"
else
  fallo "rol de app" "'$ROL_APP' puede saltear RLS: el aislamiento multi-tenant no aisla (ADR-020)"
fi

# Bucket de MinIO, creado por el servicio efimero minio-init.
if docker compose run --rm --entrypoint sh minio-init -c \
     "mc alias set c http://minio:9000 ${S3_ACCESS_KEY:-minioadmin} ${S3_SECRET_KEY:-minioadmin} > /dev/null && mc ls c/${S3_BUCKET:-deruedas-media}" \
     > /dev/null 2>&1; then
  ok "bucket" "${S3_BUCKET:-deruedas-media} existe"
else
  fallo "bucket" "${S3_BUCKET:-deruedas-media} no existe"
fi

echo
echo "Aplicacion"
if [ -f backend/app/main.py ]; then
  check_http "backend" "http://localhost:${BACKEND_PORT}/health" "sonda de vida respondiendo"
else
  pendiente "backend" "falta backend/app/main.py (lo crea T-005)"
fi

# El worker de Celery necesita app.core.events, que crea T-016 (C-02 en
# adelante). Comparte imagen con backend, pero no arranca sin ese modulo.
if [ -f backend/app/core/events.py ]; then
  if docker compose ps --status running --services 2>/dev/null | grep -qx worker; then
    ok "worker" "contenedor corriendo"
  else
    fallo "worker" "el contenedor no esta corriendo"
  fi
else
  pendiente "worker" "falta backend/app/core/events.py (lo crea T-016)"
fi

if [ -f frontend-web/package.json ]; then
  check_http "frontend-web" "http://localhost:${FRONTEND_PORT}/" "sirviendo"
else
  pendiente "frontend-web" "falta frontend-web/package.json (lo crea T-006)"
fi

echo
echo "─────────────────────────────────────────────────────────────────"
if [ "$FALLAS" -eq 0 ]; then
  echo "  Fallas: 0  [OK]${PENDIENTES:+   Pendientes: $PENDIENTES}"
  echo
  exit 0
fi
echo "  Fallas: $FALLAS  [FAIL]${PENDIENTES:+   Pendientes: $PENDIENTES}"
echo
exit 1
