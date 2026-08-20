#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Conmuta el upstream de Caddy entre el stack azul y el verde (tarea 9.10).
#
#   conmutar-upstream.sh azul
#   conmutar-upstream.sh verde
#   conmutar-upstream.sh --actual     imprime el color activo y sale
#
# La recarga de Caddy es graceful: las conexiones establecidas no se cortan y
# las peticiones en vuelo se terminan de atender.
#
# ⚠️ Este script SOLO mueve el upstream. No levanta ni baja stacks, y no escala
#    workers. Eso es responsabilidad de desplegar.sh, que lo invoca. Mantenerlo
#    tonto es a proposito: es la operacion que mas veces se va a correr a mano
#    en un incidente, y tiene que hacer una cosa sola.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

PLANTILLA="${PLANTILLA:-/opt/deruedas/infra/vps/caddy/Caddyfile.tmpl}"
RENDERIZADO="${RENDERIZADO:-/etc/caddy/Caddyfile}"
ESTADO="${ESTADO:-/etc/deruedas/color-activo}"
CONTENEDOR_CADDY="${CONTENEDOR_CADDY:-deruedas-caddy}"

log() { printf '[conmutar] %s\n' "$*" >&2; }
morir() { printf '[conmutar] ERROR: %s\n' "$*" >&2; exit 1; }

color_actual() {
    [[ -f "$ESTADO" ]] && cat "$ESTADO" || echo "ninguno"
}

if [[ "${1:-}" == "--actual" ]]; then
    color_actual
    exit 0
fi

COLOR="${1:-}"
[[ "$COLOR" == "azul" || "$COLOR" == "verde" ]] \
    || morir "color invalido: '${COLOR:-<vacio>}'. Solo 'azul' o 'verde'."

[[ -f "$PLANTILLA" ]] || morir "no existe la plantilla: $PLANTILLA"

ANTERIOR="$(color_actual)"
if [[ "$ANTERIOR" == "$COLOR" ]]; then
    log "el upstream ya apunta a '$COLOR'; no hay nada que hacer"
    exit 0
fi

log "conmutando: $ANTERIOR -> $COLOR"

# Se renderiza a un temporal y recien se mueve si Caddy valida. Asi un error de
# plantilla nunca deja /etc/caddy/Caddyfile a medio escribir.
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

sed "s/__COLOR__/${COLOR}/g" "$PLANTILLA" > "$TMP"

if grep -q '__COLOR__' "$TMP"; then
    morir "quedaron marcadores __COLOR__ sin reemplazar"
fi

# ── Validar ANTES de pisar el archivo vivo ──────────────────────────────────
#
# La config candidata se COPIA DENTRO del contenedor por stdin, no se referencia
# por ruta del host.
#
# Es la diferencia entre andar y no andar: `docker exec` resuelve las rutas
# ADENTRO del contenedor. El archivo `.nuevo` se escribe en el host, y ahi
# adentro no existe — el bind-mount es del ARCHIVO `Caddyfile`, no del
# directorio, asi que ningun hermano suyo es visible. La validacion fallaba
# siempre y el upstream nunca se movia.
#
# Fallaba CERRADO, que es lo correcto. Pero fallaba. Detectado el 17-ago-2026
# reproduciendo la conmutacion en local.
CANDIDATA_EN_CONTENEDOR="/tmp/Caddyfile.candidata"

if ! docker exec -i "$CONTENEDOR_CADDY" \
        sh -c "cat > '$CANDIDATA_EN_CONTENEDOR'" < "$TMP"; then
    morir "no se pudo copiar la configuracion candidata al contenedor"
fi

if ! docker exec "$CONTENEDOR_CADDY" caddy validate \
        --config "$CANDIDATA_EN_CONTENEDOR" --adapter caddyfile >/dev/null 2>&1; then
    log "la configuracion candidata NO valida. Detalle:"
    docker exec "$CONTENEDOR_CADDY" caddy validate \
        --config "$CANDIDATA_EN_CONTENEDOR" --adapter caddyfile || true
    morir "configuracion invalida; el upstream NO se movio"
fi

# Recien con la config validada se pisa el archivo del host, que es el registro
# de que esta sirviendo y lo que Caddy leeria si el contenedor se recrea.
install -m 0644 "$TMP" "$RENDERIZADO"

# La recarga es GRACEFUL: no corta conexiones establecidas ni descarta
# peticiones en vuelo.
if ! docker exec "$CONTENEDOR_CADDY" caddy reload \
        --config "$CANDIDATA_EN_CONTENEDOR" --adapter caddyfile; then
    morir "fallo la recarga de Caddy. La config anterior sigue activa en memoria."
fi

mkdir -p "$(dirname "$ESTADO")"
printf '%s\n' "$COLOR" > "$ESTADO"

log "upstream activo: $COLOR"
