"""Siembra el entorno LOCAL de desarrollo: agencia demo + usuarios en Keycloak.

    make seed

PARA QUE EXISTE
───────────────
Hasta el 20-ago-2026 el realm `deruedas-dev` se importaba **sin un solo
usuario**, asi que no habia forma de entrar al sistema: ni por el frontend ni
con `curl`. Cada quien se armaba un token a mano, o no probaba.

Es idempotente: se puede correr las veces que haga falta.

⚠️ HAY QUE VOLVER A CORRERLO CADA VEZ QUE SE RECREE EL CONTENEDOR DE KEYCLOAK,
no solo despues de un `docker compose down -v`. `start-dev` guarda todo en una
H2 EN MEMORIA, asi que cualquier cambio en el servicio —una variable de entorno
nueva, por ejemplo— se lleva puestos los usuarios y los mappers. El realm se
reimporta del JSON, que no tiene ninguno de los dos.

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

import asyncio
import json
import os
import sys
import uuid

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Por entorno para que sirva desde el host (`localhost`) y desde dentro de la red
# de compose (`keycloak`), que es como lo corre `make seed`.
KEYCLOAK = os.getenv("KEYCLOAK_ADMIN_URL", "http://localhost:8080")
REALM = "deruedas-dev"
CLIENTE = "backend"

# Los mappers van en LOS DOS clientes, y no es redundancia.
#
# El navegador pide su token por `frontend-web`, no por `backend`. Un mapper
# colgado solo del cliente `backend` no participa de ese flujo: el token del
# login sale sin `role`, sin `tenant_id` y sin `aud: backend`, y el API lo
# rechaza con 401 — otra vez el sintoma que parece de firma y no lo es.
CLIENTES_CON_MAPPERS = ("backend", "frontend-web")

# El puerto del frontend de ESTA maquina. El realm versionado declara el 3000,
# que es el default; si `.env` lo corre a otro lado, el redirect de Keycloak
# apunta al lugar equivocado y el login termina en una pagina en blanco.
PUERTO_DEL_FRONTEND = os.getenv("FRONTEND_PORT", "3000")

# Fijos y reconocibles a proposito: un UUID de `1`s se distingue de un dato real
# de un vistazo, y hace que los ejemplos de la documentacion no envejezcan.
TENANT = "11111111-1111-1111-1111-111111111111"
SUCURSAL = "22222222-2222-2222-2222-222222222222"

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


def _abrir_el_puerto_del_frontend(
    cliente: httpx.Client, base: str, cabecera: dict[str, str]
) -> None:
    """Agrega el origen local a los redirect URIs de `frontend-web`.

    El realm versionado declara `http://localhost:3000/*`, que es el default.
    Cuando `.env` corre el frontend a otro puerto —en esta maquina, 3010— el
    login termina con `invalid_redirect_uri` y una pagina en blanco.

    Se AGREGA, no se reemplaza: el 3000 sigue valiendo para quien no tenga
    override.
    """
    origen = f"http://localhost:{PUERTO_DEL_FRONTEND}"
    interno = cliente.get(
        f"{base}/clients", headers=cabecera, params={"clientId": "frontend-web"}
    ).json()[0]

    redirects = set(interno.get("redirectUris") or [])
    origenes = set(interno.get("webOrigins") or [])
    if f"{origen}/*" in redirects and origen in origenes:
        print(f"frontend-web: {origen} ya estaba permitido")
        return

    interno["redirectUris"] = sorted(redirects | {f"{origen}/*"})
    interno["webOrigins"] = sorted(origenes | {origen})
    cliente.put(
        f"{base}/clients/{interno['id']}", headers=cabecera, content=json.dumps(interno)
    ).raise_for_status()
    print(f"frontend-web: {origen} permitido")


def _declarar_atributos(cliente: httpx.Client, base: str, cabecera: dict[str, str]) -> None:
    """Declara `tenant_id` y `role` en el *user profile* del realm.

    ⚠️ SIN ESTO KEYCLOAK LOS DESCARTA EN SILENCIO. Desde la version 24 el perfil
    de usuario es declarativo y la politica de atributos NO declarados viene
    deshabilitada: se le mandan los atributos al crear el usuario, responde 201,
    y despues el token sale sin `tenant_id` ni `role`.

    El sintoma es cruel: la firma verifica, el `aud` coincide, el `iss` coincide,
    y aun asi todo da 401 — porque `core/auth.py` RECHAZA la peticion cuando
    falta el rol en vez de suponerlo, que es lo correcto.

    Se declaran los dos en vez de habilitar los atributos libres
    (`unmanagedAttributePolicy: ENABLED`): esa politica acepta cualquier cosa que
    alguien mande, y estos dos no son cualquier cosa.

    `edit` SOLO para admin. Que un usuario pueda editarse su propio `tenant_id`
    o su `role` seria escalada de privilegios en un campo de texto.
    """
    perfil = cliente.get(f"{base}/users/profile", headers=cabecera).json()
    declarados = {atributo["name"] for atributo in perfil.get("attributes", [])}

    faltantes = [nombre for nombre in ("tenant_id", "role") if nombre not in declarados]
    if not faltantes:
        print("perfil de usuario: tenant_id y role ya declarados")
        return

    for nombre in faltantes:
        perfil.setdefault("attributes", []).append(
            {
                "name": nombre,
                "displayName": nombre,
                "multivalued": False,
                "permissions": {"view": ["admin", "user"], "edit": ["admin"]},
                "validations": {},
            }
        )

    cliente.put(
        f"{base}/users/profile", headers=cabecera, content=json.dumps(perfil)
    ).raise_for_status()
    print(f"perfil de usuario: declarados {', '.join(faltantes)}")


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

        _declarar_atributos(cliente, base, cabecera)

        for nombre_de_cliente in CLIENTES_CON_MAPPERS:
            identificador = cliente.get(
                f"{base}/clients", headers=cabecera, params={"clientId": nombre_de_cliente}
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
                    continue
                cliente.post(
                    f"{base}/clients/{identificador}/protocol-mappers/models",
                    headers=cabecera,
                    content=json.dumps(mapper),
                ).raise_for_status()
            print(f"mappers de {nombre_de_cliente}: al dia")

        _abrir_el_puerto_del_frontend(cliente, base, cabecera)

        creados: list[tuple[str, str, str]] = []

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
                creados.append((existente, email, rol))
            else:
                respuesta.raise_for_status()
                # El `sub` NO viene en el cuerpo: Keycloak lo devuelve en la
                # cabecera `Location` de la respuesta 201. Se consulta por
                # username, que es lo unico que conocemos de antemano.
                nuevo = cliente.get(
                    f"{base}/users", headers=cabecera, params={"username": email}
                ).json()[0]["id"]
                creados.append((nuevo, email, rol))
                print(f"usuario {email} ({rol}): creado")

    asyncio.run(_espejar(creados))

    print()
    print(f"agencia demo: {TENANT}")
    print(f"clave de los tres usuarios: {CLAVE_DE_DESARROLLO}")
    return 0


async def _espejar(personas: list[tuple[str, str, str]]) -> None:
    """Crea la fila local de cada usuario, con el `sub` de Keycloak como `id`.

    Sin esto `GET /auth/me` devuelve 404 para los tres: el token es valido y el
    espejo no tiene la fila. Es el estado real de alguien que existe en Keycloak
    y todavia no acepto la invitacion — correcto como respuesta, inutil como
    entorno de desarrollo.

    `users.id` ES el `sub`. Ver el encabezado de la migracion `014`.
    """
    dsn = os.getenv(
        "SEED_DATABASE_URL",
        "postgresql+asyncpg://deruedas:deruedas@postgres:5432/deruedas",
    )
    motor = create_async_engine(dsn)
    try:
        async with motor.begin() as conexion:
            for sub, email, rol in personas:
                # Recrear el contenedor de Keycloak regenera los usuarios con
                # `sub` NUEVOS, y el espejo conserva las filas viejas con el
                # mismo email. Es el escenario que documenta el encabezado de la
                # migracion `014`: la fila vieja sobrevive con `deleted_at`, y
                # como el indice unico es PARCIAL sobre `deleted_at IS NULL`,
                # eso libera el email para la nueva.
                #
                # Sin esto el sembrador muere con una violacion de unicidad la
                # segunda vez que se levanta el entorno.
                await conexion.execute(
                    text(
                        "UPDATE users SET deleted_at = now() "
                        "WHERE tenant_id = :t AND lower(email) = lower(:e) "
                        "AND id <> :id AND deleted_at IS NULL"
                    ),
                    {"t": uuid.UUID(TENANT), "e": email, "id": uuid.UUID(sub)},
                )
                await conexion.execute(
                    text(
                        "INSERT INTO users "
                        "(id, tenant_id, email, full_name, role, status) "
                        "VALUES (:id, :t, :e, :n, :r, 'active') "
                        "ON CONFLICT (id) DO UPDATE SET "
                        "email = EXCLUDED.email, role = EXCLUDED.role, "
                        "status = 'active', deleted_at = NULL"
                    ),
                    {
                        "id": uuid.UUID(sub),
                        "t": uuid.UUID(TENANT),
                        "e": email,
                        "n": email.split("@")[0].capitalize(),
                        "r": rol,
                    },
                )
                # Todos a la casa central, y es la principal. Una persona sin
                # sucursal es un estado valido pero no sirve para probar nada.
                await conexion.execute(
                    text(
                        "INSERT INTO user_branches "
                        "(user_id, branch_id, tenant_id, is_primary) "
                        "VALUES (:u, :b, :t, true) ON CONFLICT DO NOTHING"
                    ),
                    {
                        "u": uuid.UUID(sub),
                        "b": uuid.UUID(SUCURSAL),
                        "t": uuid.UUID(TENANT),
                    },
                )
                print(f"espejo local de {email}: ok")
    finally:
        await motor.dispose()


if __name__ == "__main__":
    sys.exit(main())
