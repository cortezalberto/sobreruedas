#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Notificacion de despliegue (tarea 9.19).
#
#   notificar.sh ok|fallo|aviso "<mensaje>"
#
# POR QUE TELEGRAM Y NO CORREO — ADR-025
#
# El canal NO PUEDE depender del SMTP de la aplicacion. Un despliegue roto es
# exactamente lo que puede romper el envio de mail, y entonces la notificacion
# del fallo se pierde junto con el fallo. Un bot de Telegram es un `curl` desde
# el VPS: sin infraestructura propia, sin costo, y —lo que importa— por un
# camino independiente del que se acaba de romper.
#
# Falla en silencio a proposito (`|| true` en quien lo llama): que no se pueda
# notificar no debe abortar ni revertir un despliegue que por lo demas salio
# bien. El resultado se ve igual en el journal.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

ESTADO="${1:-aviso}"
MENSAJE="${2:-sin mensaje}"

: "${TELEGRAM_BOT_TOKEN:=}"
: "${TELEGRAM_CHAT_ID:=}"

case "$ESTADO" in
    ok)     ICONO="✅" ;;
    fallo)  ICONO="🔴" ;;
    *)      ICONO="⚠️" ;;
esac

HOST="$(hostname)"
TEXTO="${ICONO} *deRuedas · ${HOST}*
${MENSAJE}"

# Siempre al journal: es el registro que sobrevive aunque Telegram este caido.
printf '[notificar:%s] %s\n' "$ESTADO" "$MENSAJE" >&2

if [[ -z "$TELEGRAM_BOT_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]]; then
    printf '[notificar] sin TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID; solo journal\n' >&2
    exit 0
fi

curl --silent --show-error --max-time 10 \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${TEXTO}" \
    --data-urlencode "parse_mode=Markdown" \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    >/dev/null 2>&1 \
    || printf '[notificar] no se pudo enviar a Telegram\n' >&2

exit 0
