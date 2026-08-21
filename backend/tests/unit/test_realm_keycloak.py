"""El realm versionado declara lo que hace cumplible a `ADR-026`, y no se afloja.

POR QUE ESTE ARCHIVO EXISTE
────────────────────────────
`D-9` decide que el realm se versiona como archivo y no se configura a mano por
la UI: un realm hecho a mano no es reproducible —el entorno de cada uno diverge,
y el dia que hay que levantarlo de nuevo nadie sabe que tenia—. Mismo criterio
que `ADR-023` le aplico al VPS.

Pero un archivo versionado que nadie verifica es solo un archivo. Estos tests
son la mitad que falta: leen el JSON y comprueban que sigue declarando lo que
las decisiones dicen. Mismo patron que `test_auditoria_de_dependencias.py`
aplica sobre `ci.yml`.

LA REGLA QUE SEPARA ESTE ARCHIVO DE `sembrar_dev.py`
─────────────────────────────────────────────────────
Los dos escriben configuracion de Keycloak, y la division no es arbitraria:

  ESTRUCTURA DEL REALM     va al JSON versionado  (roles, flujos, mappers,
                           vida de los tokens)    iguales en toda maquina

  CONFIGURACION POR        se queda en el seed    el puerto del frontend vive
  MAQUINA                                         en `.env` y cambia por
                                                  escritorio: el seed AGREGA
                                                  ese `redirectUri`, no lo
                                                  reemplaza

Los mappers estaban del lado equivocado hasta el 21-ago-2026: los creaba el
seed por la API de administracion. No era configuracion a mano —el seed es
idempotente— pero era un SEGUNDO lugar donde vivia la verdad, y el JSON decia
menos de lo que el realm realmente tenia.

⚠️ SI ESTO FALLA, LA QUE MANDA ES LA DECISION, NO EL ARCHIVO. El realm se
corrige; no se afloja el test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REALM = (
    Path(__file__).resolve().parents[3] / "infra" / "local" / "keycloak" / "deruedas-dev-realm.json"
)

CLIENTES_PUBLICOS = ("frontend-web", "frontend-mobile", "frontend-admin")

# Los dos claims que `app/core/auth.py` exige de PRIMER NIVEL (`ADR-021`), mas
# la audiencia. La razon de que `role` no salga de `realm_access.roles` esta en
# el comentario de `CLAIM_ROL`: una lista obligaria a elegir uno, y el tenant no
# es un rol.
ATRIBUTOS_MAPEADOS = ("tenant_id", "role")

QUINCE_MINUTOS = 900
SIETE_DIAS = 604_800


def _realm() -> dict[str, Any]:
    datos: dict[str, Any] = json.loads(REALM.read_text(encoding="utf-8"))
    return datos


def _clientes() -> dict[str, dict[str, Any]]:
    return {cliente["clientId"]: cliente for cliente in _realm()["clients"]}


def _mappers(cliente: dict[str, Any]) -> list[dict[str, Any]]:
    mappers: list[dict[str, Any]] = cliente.get("protocolMappers") or []
    return mappers


def _mapper_del_claim(cliente: dict[str, Any], claim: str) -> dict[str, Any] | None:
    """El mapper que emite un claim, buscado POR EL CLAIM y no por su nombre.

    El `name` de un mapper es cosmetico —es lo que se ve en la UI de Keycloak— y
    el proyecto los llama `tenant_id-claim`, con sufijo. Lo que importa, y lo
    unico que el backend lee, es el `claim.name` que termina saliendo en el
    token. Buscar por ahi hace que renombrar un mapper no rompa el test, y que
    cambiar el claim SI lo rompa — que es exactamente al reves de buscar por
    `name`.
    """
    for mapper in _mappers(cliente):
        if mapper.get("config", {}).get("claim.name") == claim:
            return mapper
    return None


# ── Contrapesos ─────────────────────────────────────────────────────────────
#
# Sin estos, un realm que se renombra o se queda sin clientes haria pasar en
# verde a todo lo de abajo: los `for` iterarian sobre nada. Un guardian que se
# apaga solo es peor que ninguno.


def test_el_realm_versionado_existe() -> None:
    assert REALM.is_file(), f"no esta {REALM}"


def test_estan_los_cuatro_clientes() -> None:
    clientes = _clientes()
    for esperado in ("backend", *CLIENTES_PUBLICOS):
        assert esperado in clientes, f"el realm ya no declara el cliente `{esperado}`"


# ── `ADR-026`: nunca manejamos contraseñas ──────────────────────────────────


def test_ningun_cliente_habilita_direct_access_grants() -> None:
    """El flujo que volveria incumplible a `ADR-026`, apagado en los cuatro.

    `Direct Access Grants` es ROPC: usuario y contraseña se cambian por un token
    contra el endpoint del cliente. Con eso habilitado, "la aplicacion nunca ve
    una contraseña" deja de ser una propiedad del sistema y pasa a depender de
    que a nadie se le ocurra usar el flujo que esta ahi, prendido y disponible.

    ⚠️ SE VIGILAN LOS CUATRO, no solo los publicos. El unico que lo tenia
    prendido era `backend`, que es CONFIDENCIAL —lleva secreto—, y esa es
    justamente la trampa: parece que el secreto lo protege. No protege de esto.
    El secreto dice QUE CLIENTE pide el token, no COMO; con ROPC habilitado, lo
    que viaja sigue siendo la contraseña de una persona.
    """
    for nombre, cliente in _clientes().items():
        assert cliente.get("directAccessGrantsEnabled") is False, (
            f"el cliente `{nombre}` habilita Direct Access Grants (ROPC).\n"
            "  Es el flujo que cambia usuario+contraseña por un token, y `ADR-026`\n"
            "  dice que la aplicacion nunca maneja contraseñas."
        )


def test_los_clientes_de_usuario_exigen_pkce() -> None:
    """`Standard Flow` con PKCE `S256`, que es el login que `ADR-026` §4 deja.

    Sin PKCE, un cliente publico —sin secreto, por definicion— entrega su codigo
    de autorizacion a quien logre interceptarlo en el redirect.
    """
    clientes = _clientes()
    for nombre in CLIENTES_PUBLICOS:
        cliente = clientes[nombre]
        assert cliente.get("publicClient") is True, f"`{nombre}` dejo de ser publico"
        assert cliente.get("standardFlowEnabled") is True, f"`{nombre}` no permite el login"
        assert (
            cliente["attributes"].get("pkce.code.challenge.method") == "S256"
        ), f"`{nombre}` no exige PKCE S256"


# ── `ADR-021`: los claims son planos ────────────────────────────────────────


def test_los_mappers_viven_en_el_realm_y_no_en_el_seed() -> None:
    """`tenant_id` y `role` como claims de primer nivel, mas la audiencia.

    Van en LOS DOS clientes que emiten tokens de usuario, y no es redundancia:
    el navegador pide su token por `frontend-web`, no por `backend`. Un mapper
    colgado solo de `backend` no participa de ese flujo y el token del login
    sale sin `role`, sin `tenant_id` y sin `aud: backend` — un 401 en todo, con
    cara de problema de firma.
    """
    clientes = _clientes()
    for nombre in ("backend", "frontend-web"):
        cliente = clientes[nombre]

        for atributo in ATRIBUTOS_MAPEADOS:
            mapper = _mapper_del_claim(cliente, atributo)
            assert mapper is not None, f"`{nombre}` no emite el claim `{atributo}`"
            assert mapper["protocolMapper"] == "oidc-usermodel-attribute-mapper"
            assert (
                mapper["config"]["user.attribute"] == atributo
            ), f"el claim `{atributo}` de `{nombre}` sale de otro atributo del usuario"
            assert (
                mapper["config"]["access.token.claim"] == "true"
            ), f"el claim `{atributo}` de `{nombre}` no viaja en el access token"

        audiencias = [
            mapper
            for mapper in _mappers(cliente)
            if mapper["protocolMapper"] == "oidc-audience-mapper"
        ]
        assert audiencias, f"`{nombre}` no declara el mapper de audiencia"
        assert (
            audiencias[0]["config"]["included.client.audience"] == "backend"
        ), f"la audiencia de `{nombre}` no apunta al backend, que es quien valida el token"


# ── La vida de los tokens ───────────────────────────────────────────────────


def test_los_tokens_duran_lo_que_dice_el_diseño() -> None:
    """15 minutos el access token, 7 dias la sesion (`D-9`).

    ⚠️ EL MAXIMO SOLO NO ALCANZA, y por eso se verifican los dos. Un
    `ssoSessionMaxLifespan` de 7 dias con un `ssoSessionIdleTimeout` de 30
    minutos son, en la practica, 30 minutos: quien vuelve del almuerzo se
    encuentra la sesion caida y los "7 dias" no significan nada. Fijar solo el
    maximo deja pasar exactamente esa configuracion.
    """
    realm = _realm()

    assert realm["accessTokenLifespan"] == QUINCE_MINUTOS
    assert realm["ssoSessionMaxLifespan"] == SIETE_DIAS
    assert realm["ssoSessionIdleTimeout"] == SIETE_DIAS
