#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Pruebas de humo contra un stack que TODAVIA NO recibe trafico (tarea 9.17).
#
#   humo.sh <color> [duracion_segundos]
#
# Corre contra los alias de red del stack indicado, no contra el dominio
# publico: el objetivo es probar el stack NUEVO, y el dominio publico todavia
# apunta al viejo.
#
# POR QUE CINCO MINUTOS Y NO UNA PASADA
#
# Una sola pasada atrapa "arranco y responde". No atrapa lo que mas duele en un
# despliegue: fugas de memoria, pools de conexiones que se agotan, y arranques
# perezosos que fallan recien cuando expira el primer token. Cinco minutos de
# sondeo sostenido es el presupuesto que fija la tarea 9.17.
#
# ⚠️ NO prueba el worker a proposito: durante el humo el worker del stack nuevo
#    esta en CERO replicas (ADR-025 Decision 2), porque si consumiera de la cola
#    compartida estaria procesando trabajo real antes de ser promovido.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

COLOR="${1:-}"
DURACION="${2:-300}"
INTERVALO="${INTERVALO_HUMO:-10}"
RED="${RED_DOCKER:-deruedas_default}"

[[ "$COLOR" == "azul" || "$COLOR" == "verde" ]] \
    || { echo "[humo] ERROR: color invalido '${COLOR:-<vacio>}'" >&2; exit 2; }

log() { printf '[humo:%s] %s\n' "$COLOR" "$*" >&2; }

# Se sondea desde un contenedor efimero DENTRO de la red de Docker. Desde el
# host los alias con color no resuelven.
#
# SONDA_CMD existe para poder PROBAR este script. Si esta seteada, se invoca con
# la URL como unico argumento y su codigo de salida decide. Sin ella, el
# comportamiento es exactamente el de siempre.
#
# No es un agujero: el escenario "las pruebas de humo posteriores fallan" de
# `platform/delivery-pipeline` exige verificar que un humo fallido NO conmuta el
# trafico. Sin poder inyectar la sonda, ese test necesitaria levantar stacks de
# verdad, y un gate que solo se puede probar a mano no se prueba nunca — que es
# el mismo criterio que ADR-023 le aplico a gitleaks.
sondear() {
    local url="$1"
    if [[ -n "${SONDA_CMD:-}" ]]; then
        "$SONDA_CMD" "$url"
        return $?
    fi
    docker run --rm --network "$RED" curlimages/curl:latest \
        --silent --show-error --fail --max-time 5 "$url" >/dev/null 2>&1
}

# ── Los tres sondeos ────────────────────────────────────────────────────────
# /ready del backend es el que manda: dice "puede atender trafico", no solo
# "el proceso vive". Si /ready pasa pero /health no, algo muy raro pasa y
# conviene saberlo.
declare -A SONDEOS=(
    ["backend /ready"]="http://backend-${COLOR}:8000/ready"
    ["backend /health"]="http://backend-${COLOR}:8000/health"
    ["frontend /"]="http://web-${COLOR}:3000/"
)

log "arrancando: ${DURACION}s, sondeo cada ${INTERVALO}s"

FIN=$(( SECONDS + DURACION ))
VUELTA=0
FALLOS=0

while (( SECONDS < FIN )); do
    VUELTA=$(( VUELTA + 1 ))
    for nombre in "${!SONDEOS[@]}"; do
        if ! sondear "${SONDEOS[$nombre]}"; then
            FALLOS=$(( FALLOS + 1 ))
            log "FALLO en '${nombre}' (vuelta ${VUELTA}, fallo #${FALLOS})"

            # Un solo fallo aborta. No se toleran intermitencias: si el stack
            # nuevo parpadea sin trafico, con trafico va a ser peor. Es mas
            # barato no conmutar que conmutar y volver.
            log "ABORTA. El upstream NO se mueve."
            exit 1
        fi
    done
    sleep "$INTERVALO"
done

log "OK — ${VUELTA} vueltas sin un solo fallo en ${DURACION}s"
