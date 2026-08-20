"""Siembra el entorno LOCAL de desarrollo: agencia demo + usuarios en Keycloak.

    make seed

PARA QUE EXISTE
───────────────
Hasta el 20-ago-2026 el realm `deruedas-dev` se importaba **sin un solo
usuario**, asi que no habia forma de entrar al sistema: ni por el frontend ni
con `curl`. Cada quien se armaba un token a mano, o no probaba.

Es idempotente: se puede correr las veces que haga falta, y hay que volver a
correrlo despues de `docker compose down -v`, porque eso borra el volumen de
Keycloak y la base.

⚠️ SOLO PARA LOCAL. La clave de abajo es una constante de desarrollo sobre un
realm que solo levanta `docker-compose.yml` en esta maquina. No es un secreto:
es el equivalente a `postgres/postgres`. Nada de esto toca staging ni produccion
—sus secretos van cifrados con SOPS (`ADR-023`, regla dura 4)— y este archivo no
se importa desde `app/` ni desde los tests.

LOS DOS MAPPERS QUE HACEN FALTA, Y POR QUE
───────────────────────────────────────────
`app/core/auth.py` exige `tenant_id` y `role` como claims de PRIMER NIVEL, no
dentro de `realm_access.roles` — la razon esta escrita en el comentario de
`CLAIM_ROL`: una lista obligaria a elegir uno, y el tenant no es un rol.
Keycloak no los emite solo: hay que mapear atributos del usuario a claims.

Y la audiencia: el backend valida que el token sea PARA EL, y un direct grant
emite `aud: account`. Sin el mapper de audiencia, todo token se rechaza con un
401 que parece un problema de firma y no lo es.
"""

from __future__ import annotations

import json
import os
import sys

import httpx

# Por entorno para que sirva desde el host (`localhost`) y desde dentro de la red
# de compose (`keycloak`), que es como lo corre `make seed`.
KEYCLOAK = os.getenv("KEYCLOAK_ADMIN_URL", "http://localhost:8080")
REALM = "deruedas-dev"
CLIENTE = "backend"

# Fijos y reconocibles a proposito: un UUID de `1`s se distingue de un dato real
# de un vistazo, y hace que los ejemplos de la documentacion no envejezcan.
TENANT = "11111111-1111-1111-1111-111111111111"

CLAVE_DE_DESARROLLO = "demo1234"  # noqa: S105 — ver la advertencia del docstring

USUARIOS = [
    ("gerente@demo.test", "Gabriela", "Gerente", "manager"),
    ("vendedor@demo.test", "Vicente", "Vendedor", "salesperson"),
    ("admin@demo.test", "Ana", "Administrativa", "admin_staff"),
]


def _token_de_admin(cliente: httpx.Client) -> str:
    respuesta = cliente.post(
        f"{KEYCLOAK}/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": "admin",
            "password": "admin",
            "grant_type": "password",
        },
    )
    respuesta.raise_for_status()
    return str(respuesta.json()["access_token"])


def _mapper_de_atributo(nombre: str) -> dict[str, object]:
    return {
        "name": f"{nombre}-claim",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "config": {
            "user.attribute": nombre,
            "claim.name": nombre,
            "jsonType.label": "String",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        },
    }


MAPPERS: list[dict[str, object]] = [
    _mapper_de_atributo("tenant_id"),
    _mapper_de_atributo("role"),
    {
        "name": "audiencia-backend",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-audience-mapper",
        "config": {
            "included.client.audience": CLIENTE,
            "id.token.claim": "false",
            "access.token.claim": "true",
        },
    },
]


def main() -> int:
    with httpx.Client(timeout=30) as cliente:
        try:
            cabecera = {
                "Authorization": f"Bearer {_token_de_admin(cliente)}",
                "Content-Type": "application/json",
            }
        except httpx.HTTPError as error:
            print(f"no se pudo hablar con Keycloak en {KEYCLOAK}: {error}")
            print("levanta el entorno primero:  make up")
            return 1

        base = f"{KEYCLOAK}/admin/realms/{REALM}"

        identificador = cliente.get(
            f"{base}/clients", headers=cabecera, params={"clientId": CLIENTE}
        ).json()[0]["id"]

        puestos = {
            m["name"]
            for m in cliente.get(
                f"{base}/clients/{identificador}/protocol-mappers/models",
                headers=cabecera,
            ).json()
        }
        for mapper in MAPPERS:
            nombre = str(mapper["name"])
            if nombre in puestos:
                print(f"mapper {nombre}: ya estaba")
                continue
            cliente.post(
                f"{base}/clients/{identificador}/protocol-mappers/models",
                headers=cabecera,
                content=json.dumps(mapper),
            ).raise_for_status()
            print(f"mapper {nombre}: creado")

        for email, nombre, apellido, rol in USUARIOS:
            cuerpo = {
                "username": email,
                "email": email,
                "firstName": nombre,
                "lastName": apellido,
                "enabled": True,
                "emailVerified": True,
                "attributes": {"tenant_id": [TENANT], "role": [rol]},
                "credentials": [
                    {
                        "type": "password",
                        "value": CLAVE_DE_DESARROLLO,
                        "temporary": False,
                    }
                ],
            }
            respuesta = cliente.post(
                f"{base}/users", headers=cabecera, content=json.dumps(cuerpo)
            )
            if respuesta.status_code == 409:
                existente = cliente.get(
                    f"{base}/users", headers=cabecera, params={"username": email}
                ).json()[0]["id"]
                cliente.put(
                    f"{base}/users/{existente}",
                    headers=cabecera,
                    content=json.dumps(cuerpo),
                )
                cliente.put(
                    f"{base}/users/{existente}/reset-password",
                    headers=cabecera,
                    content=json.dumps(
                        {
                            "type": "password",
                            "value": CLAVE_DE_DESARROLLO,
                            "temporary": False,
                        }
                    ),
                )
                print(f"usuario {email} ({rol}): actualizado")
            else:
                respuesta.raise_for_status()
                print(f"usuario {email} ({rol}): creado")

    print()
    print(f"agencia demo: {TENANT}")
    print(f"clave de los tres usuarios: {CLAVE_DE_DESARROLLO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
