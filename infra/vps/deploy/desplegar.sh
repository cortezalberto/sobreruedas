#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Agente de despliegue — el VPS TIRA (tareas 9.15 a 9.20)
#
# Lo dispara un timer de systemd cada 2 minutos. Detecta que hay una imagen
# nueva publicada, la despliega en el stack inactivo, la prueba, y recien
# entonces conmuta el trafico.
#
# EL PIPELINE NO EMPUJA. Esta es la mitad que lo hace posible: GitHub Actions
# publica una imagen y termina; toda la autoridad sobre produccion vive aca, en
# la maquina, y nunca sale de ella (ADR-015 conservado por ADR-023).
#
# ─────────────────────────────────────────────────────────────────────────────
# EL ORDEN DE LOS PASOS NO ES ARBITRARIO
#
#   1. Detectar         sondear el registry; si no cambio nada, salir barato
#   2. Verificar firma  ANTES de correr nada de esa imagen
#   3. Migrar           ANTES de levantar el stack nuevo
#   4. Levantar         stack inactivo, worker en CERO replicas
#   5. Humo             5 minutos, con el trafico todavia en el stack viejo
#   6. Conmutar         recien aca se mueve el upstream
#   7. Promover worker  escalar el nuevo, apagar el viejo
#   8. Apagar el viejo  con gracia
#
# El paso 3 antes del 4 depende de la REGLA DURA 13: la migracion es compatible
# hacia atras, asi que el stack VIEJO —que todavia tiene todo el trafico— sigue
# funcionando contra el esquema nuevo. Si esa regla se rompe, este orden deja de
# ser seguro y el azul-verde pierde su red.
#
# El paso 4 con worker en cero es ADR-025 Decision 2: un worker del stack no
# promovido consumiria trabajo real de la cola compartida antes de tiempo, y el
# humo —que solo mira HTTP— no lo veria.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

RAIZ="${RAIZ_DERUEDAS:-/opt/deruedas}"
ETC="${ETC_DERUEDAS:-/etc/deruedas}"
ENV_FILE="${ENV_FILE:-${ETC}/produccion.env}"
ESTADO_COLOR="${ETC}/color-activo"
ESTADO_SHA="${ETC}/sha-desplegado"
BLOQUEO="/var/lock/deruedas-desplegar.lock"

DURACION_HUMO="${DURACION_HUMO:-300}"
GRACIA_APAGADO="${GRACIA_APAGADO:-60}"

cd "$RAIZ"

log() { printf '[desplegar] %s\n' "$*" >&2; }
notificar() { "${RAIZ}/infra/vps/deploy/notificar.sh" "$@" || true; }

morir() {
    log "ERROR: $*"
    notificar fallo "Despliegue abortado: $*"
    exit 1
}

# ── Un despliegue a la vez ───────────────────────────────────────────────────
# El timer corre cada 2 minutos y un despliegue tarda mas de 5 por el humo. Sin
# esto, la segunda corrida pisaria a la primera a mitad de camino.
exec 9>"$BLOQUEO"
if ! flock -n 9; then
    log "ya hay un despliegue en curso; salgo"
    exit 0
fi

[[ -f "$ENV_FILE" ]] || morir "no existe $ENV_FILE (SOPS no lo descifro?)"
# `set -a` exporta todo lo que se defina hasta el `set +a`: asi las variables del
# archivo llegan a `docker compose` sin enumerarlas una por una.
set -a
# Lo descifra SOPS en el VPS, no existe en el repositorio: shellcheck no tiene
# nada que seguir.
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

: "${REGISTRY:?falta REGISTRY en $ENV_FILE}"

compose() {
    local proyecto="$1"; shift
    docker compose -p "$proyecto" \
        -f docker-compose.yml -f docker-compose.prod.yml \
        --env-file "$ENV_FILE" "$@"
}

# ═════════════════════════════════════════════════════════════════════════════
# 1. DETECTAR
# ═════════════════════════════════════════════════════════════════════════════

log "sondeando ${REGISTRY}/backend:main"
docker pull --quiet "${REGISTRY}/backend:main" >/dev/null 2>&1 \
    || { log "no se pudo bajar la imagen; reintento en la proxima vuelta"; exit 0; }

# El SHA viene en la etiqueta OCI que pone el pipeline. Es como el VPS sabe QUE
# commit trae la imagen sin que nadie se lo empuje.
SHA_NUEVO="$(docker inspect --format \
    '{{index .Config.Labels "org.opencontainers.image.revision"}}' \
    "${REGISTRY}/backend:main" 2>/dev/null || true)"

[[ -n "$SHA_NUEVO" && "$SHA_NUEVO" != "<no value>" ]] \
    || morir "la imagen no trae org.opencontainers.image.revision"

SHA_ACTUAL="$( [[ -f "$ESTADO_SHA" ]] && cat "$ESTADO_SHA" || echo "ninguno" )"

if [[ "$SHA_NUEVO" == "$SHA_ACTUAL" ]]; then
    log "sin cambios (${SHA_NUEVO:0:12}); salgo"
    exit 0
fi

log "hay despliegue nuevo: ${SHA_ACTUAL:0:12} -> ${SHA_NUEVO:0:12}"

COLOR_ACTUAL="$( [[ -f "$ESTADO_COLOR" ]] && cat "$ESTADO_COLOR" || echo "verde" )"
COLOR_NUEVO=$( [[ "$COLOR_ACTUAL" == "azul" ]] && echo "verde" || echo "azul" )
log "stack activo: ${COLOR_ACTUAL} · desplegando en: ${COLOR_NUEVO}"

export IMAGE_TAG="$SHA_NUEVO"

# ═════════════════════════════════════════════════════════════════════════════
# 2. VERIFICAR LA FIRMA — antes de ejecutar nada de esa imagen
# ═════════════════════════════════════════════════════════════════════════════

if command -v cosign >/dev/null 2>&1; then
    for componente in backend frontend-web; do
        log "verificando firma de ${componente}"
        cosign verify \
            --certificate-identity-regexp \
                "^https://github.com/${REPO_GITHUB:?falta REPO_GITHUB}/.github/workflows/" \
            --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
            "${REGISTRY}/${componente}:${SHA_NUEVO}" >/dev/null 2>&1 \
            || morir "firma invalida o ausente en ${componente}:${SHA_NUEVO:0:12}"
    done
else
    # No se silencia: que falte cosign es una degradacion real del control de
    # cadena de suministro, y tiene que verse.
    log "AVISO: cosign no esta instalado; se despliega SIN verificar firma"
    notificar aviso "Desplegando sin verificar firma: falta cosign en el VPS"
fi

docker pull --quiet "${REGISTRY}/frontend-web:${SHA_NUEVO}" >/dev/null \
    || morir "no se pudo bajar frontend-web:${SHA_NUEVO:0:12}"

# ═════════════════════════════════════════════════════════════════════════════
# 3. MIGRAR — antes de levantar el stack nuevo
# ═════════════════════════════════════════════════════════════════════════════
# Con DATABASE_MIGRATION_URL (rol propietario), no con el de aplicacion: el rol
# de aplicacion no tiene DDL a proposito (ADR-020).
#
# Es seguro correrlas con el stack viejo sirviendo PORQUE la regla dura 13
# obliga a que sean compatibles hacia atras. Ese es todo el argumento.

log "aplicando migraciones"
if ! compose "deruedas-migracion" run --rm --no-deps \
        -e DATABASE_URL="${DATABASE_MIGRATION_URL:?falta DATABASE_MIGRATION_URL}" \
        backend alembic upgrade head; then
    morir "fallaron las migraciones. El stack ${COLOR_ACTUAL} sigue sirviendo."
fi

# ═════════════════════════════════════════════════════════════════════════════
# 4. LEVANTAR EL STACK INACTIVO — worker en CERO replicas
# ═════════════════════════════════════════════════════════════════════════════

log "levantando ${COLOR_NUEVO} (worker en 0 replicas)"
STACK_COLOR="$COLOR_NUEVO" WORKER_REPLICAS=0 \
    compose "deruedas-${COLOR_NUEVO}" up -d --wait --wait-timeout 180 \
        backend frontend-web \
    || {
        STACK_COLOR="$COLOR_NUEVO" compose "deruedas-${COLOR_NUEVO}" logs --tail 80 || true
        STACK_COLOR="$COLOR_NUEVO" compose "deruedas-${COLOR_NUEVO}" down || true
        morir "el stack ${COLOR_NUEVO} no llego a estado saludable"
    }

# ═════════════════════════════════════════════════════════════════════════════
# 5. HUMO — el trafico sigue en el stack viejo
# ═════════════════════════════════════════════════════════════════════════════

log "humo sobre ${COLOR_NUEVO} durante ${DURACION_HUMO}s"
if ! "${RAIZ}/infra/vps/deploy/humo.sh" "$COLOR_NUEVO" "$DURACION_HUMO"; then
    log "el humo fallo; desmontando ${COLOR_NUEVO}"
    STACK_COLOR="$COLOR_NUEVO" compose "deruedas-${COLOR_NUEVO}" logs --tail 80 || true
    STACK_COLOR="$COLOR_NUEVO" compose "deruedas-${COLOR_NUEVO}" down || true
    morir "humo fallido en ${SHA_NUEVO:0:12}. El upstream NO se movio; ${COLOR_ACTUAL} sigue sirviendo."
fi

# ═════════════════════════════════════════════════════════════════════════════
# 6. CONMUTAR
# ═════════════════════════════════════════════════════════════════════════════

log "conmutando el upstream a ${COLOR_NUEVO}"
"${RAIZ}/infra/vps/deploy/conmutar-upstream.sh" "$COLOR_NUEVO" \
    || morir "fallo la conmutacion. ${COLOR_ACTUAL} sigue sirviendo; ${COLOR_NUEVO} quedo levantado."

printf '%s\n' "$SHA_NUEVO" > "$ESTADO_SHA"

# ═════════════════════════════════════════════════════════════════════════════
# 7. PROMOVER EL WORKER
# ═════════════════════════════════════════════════════════════════════════════
# Recien ahora el worker nuevo puede tocar la cola compartida. Primero se apaga
# el viejo y despues se levanta el nuevo: al reves, por un instante habria dos
# generaciones de codigo consumiendo la misma cola.

log "apagando el worker de ${COLOR_ACTUAL}"
STACK_COLOR="$COLOR_ACTUAL" WORKER_REPLICAS=0 \
    compose "deruedas-${COLOR_ACTUAL}" up -d --no-recreate --scale worker=0 worker \
    2>/dev/null || true

log "promoviendo el worker de ${COLOR_NUEVO}"
STACK_COLOR="$COLOR_NUEVO" WORKER_REPLICAS="${WORKER_REPLICAS_OBJETIVO:-1}" \
    compose "deruedas-${COLOR_NUEVO}" up -d --no-recreate worker \
    || notificar aviso "El trafico ya esta en ${COLOR_NUEVO} pero el worker no levanto"

# ═════════════════════════════════════════════════════════════════════════════
# 8. APAGAR EL STACK VIEJO
# ═════════════════════════════════════════════════════════════════════════════
# Con gracia: las peticiones que Caddy ya habia entregado al stack viejo se
# terminan de atender antes de bajarlo.

log "esperando ${GRACIA_APAGADO}s antes de apagar ${COLOR_ACTUAL}"
sleep "$GRACIA_APAGADO"
STACK_COLOR="$COLOR_ACTUAL" compose "deruedas-${COLOR_ACTUAL}" down || true

log "listo: ${COLOR_NUEVO} sirviendo ${SHA_NUEVO:0:12}"
notificar ok "Desplegado \`${SHA_NUEVO:0:12}\` en *${COLOR_NUEVO}*. Humo OK, upstream conmutado."
