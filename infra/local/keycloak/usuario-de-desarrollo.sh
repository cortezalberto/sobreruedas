#!/usr/bin/env bash
#
# Deja el Keycloak de DESARROLLO listo para emitir un token que la API acepte.
#
# ⚠️ SOLO DESARROLLO. Crea un usuario con contraseña conocida y habilita los
# atributos no gestionados del realm. Nada de esto va a un entorno real: ahí los
# usuarios los crea C-05 y los atributos se declaran en el perfil del realm.
#
# POR QUE EXISTE ESTE ARCHIVO
# ────────────────────────────
# El realm importado (`deruedas-dev-realm.json`) trae los clientes pero NO trae
# usuario ni mappers, así que recién importado no puede emitir un token con los
# claims que la API exige. Configurarlo a mano funciona una vez y se pierde con
# el próximo `docker compose down -v`.
#
# QUE CONFIGURA, Y POR QUE CADA COSA
# ───────────────────────────────────
#   1. `unmanagedAttributePolicy=ENABLED` — Keycloak 26 descarta EN SILENCIO
#      cualquier atributo que el perfil del realm no declare. Sin esto, el
#      usuario se crea, los atributos se "guardan" y el token sale sin ellos.
#   2. Mapper de AUDIENCIA — por defecto un token del grant directo trae
#      `aud: account`, y la API exige `aud: backend`. Sin este mapper el token
#      es válido y aun así se rechaza.
#   3. Mappers de `tenant_id` y `role` — los dos claims que `core/auth.py`
#      exige. La decisión de que vayan de primer nivel está en ese archivo.
#   4. Un usuario con esos atributos.
#
# Uso:
#     bash infra/local/keycloak/usuario-de-desarrollo.sh
#
# Después, para pedir el token, ver el bloque final que imprime.
set -euo pipefail

REALM=deruedas-dev
CLIENTE=backend
USUARIO=${USUARIO_DEV:-vendedor}
CLAVE=${CLAVE_DEV:-vendedor}

# El mismo tenant que siembra `agencia-de-desarrollo.sql`. Fijo y no aleatorio:
# tiene que coincidir con la fila de `tenants`, y un valor estable hace que los
# `curl` de ejemplo sigan sirviendo entre reinicios.
TENANT=${TENANT_DEV:-11111111-1111-1111-1111-111111111111}
ROL=${ROL_DEV:-manager}

kc() { MSYS_NO_PATHCONV=1 docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh "$@"; }

echo "▸ autenticando contra Keycloak…"
kc config credentials --server http://localhost:8080 --realm master \
  --user "${KEYCLOAK_ADMIN:-admin}" --password "${KEYCLOAK_ADMIN_PASSWORD:-admin}" >/dev/null

echo "▸ habilitando atributos no gestionados en el realm…"
kc update users/profile -r "$REALM" -s 'unmanagedAttributePolicy=ENABLED' >/dev/null

CID=$(kc get clients -r "$REALM" -q clientId="$CLIENTE" --fields id --format csv --noquotes | tr -d '\r')

# Los mappers se crean si faltan. `|| true` porque kcadm devuelve error cuando
# el nombre ya existe, y volver a correr este script tiene que ser inofensivo.
crear_mapper() {
  local nombre=$1; shift
  if kc get "clients/$CID/protocol-mappers/models" -r "$REALM" --fields name | grep -q "\"$nombre\""; then
    echo "  · mapper '$nombre' ya estaba"
    return
  fi
  kc create "clients/$CID/protocol-mappers/models" -r "$REALM" -s "name=$nombre" "$@" >/dev/null
  echo "  · mapper '$nombre' creado"
}

echo "▸ mappers del cliente $CLIENTE…"
crear_mapper audiencia-backend -s protocol=openid-connect -s protocolMapper=oidc-audience-mapper \
  -s 'config."included.client.audience"=backend' -s 'config."access.token.claim"=true'
crear_mapper tenant-id -s protocol=openid-connect -s protocolMapper=oidc-usermodel-attribute-mapper \
  -s 'config."user.attribute"=tenant_id' -s 'config."claim.name"=tenant_id' \
  -s 'config."jsonType.label"=String' -s 'config."access.token.claim"=true'
crear_mapper rol -s protocol=openid-connect -s protocolMapper=oidc-usermodel-attribute-mapper \
  -s 'config."user.attribute"=role' -s 'config."claim.name"=role' \
  -s 'config."jsonType.label"=String' -s 'config."access.token.claim"=true'

echo "▸ usuario '$USUARIO'…"
UID_KC=$(kc get users -r "$REALM" -q username="$USUARIO" --fields id --format csv --noquotes | tr -d '\r' || true)
if [ -z "$UID_KC" ]; then
  UID_KC=$(kc create users -r "$REALM" -s "username=$USUARIO" -s enabled=true \
    -s "email=$USUARIO@agencia-demo.test" -i | tr -d '\r')
  echo "  · creado"
else
  echo "  · ya existía"
fi

# Los atributos se mandan como JSON y no con `-s attributes.x=y`: en Keycloak 26
# esa forma corta no los aplica y el usuario queda sin ellos, sin decir nada.
kc update "users/$UID_KC" -r "$REALM" \
  -s "attributes={\"tenant_id\":[\"$TENANT\"],\"role\":[\"$ROL\"]}" >/dev/null
kc set-password -r "$REALM" --username "$USUARIO" --new-password "$CLAVE" >/dev/null

cat <<FIN

✔ Listo. Usuario '$USUARIO' / '$CLAVE', tenant $TENANT, rol $ROL.

⚠️ EL TOKEN SE PIDE DESDE ADENTRO DE LA RED DE DOCKER, no desde el host.

   La API espera \`iss = http://keycloak:8080/realms/$REALM\`, y Keycloak arma
   el emisor con el host de la petición: pedido desde el host sale
   \`localhost:8080\` y la validación lo rechaza. El token en sí después sirve
   contra \`localhost:8010\` sin problema — lo que importa es dónde se emite.

   docker compose exec -T backend python -c "
   import json,urllib.parse,urllib.request
   d=urllib.parse.urlencode({'grant_type':'password','client_id':'$CLIENTE',
     'client_secret':'\${KEYCLOAK_CLIENT_SECRET:-cambiame}',
     'username':'$USUARIO','password':'$CLAVE'}).encode()
   print(json.load(urllib.request.urlopen(
     'http://keycloak:8080/realms/$REALM/protocol/openid-connect/token', d))['access_token'])"

FIN
