"""El catalogo de roles y su resolucion estricta.

`ADR-017` fija los cuatro roles del sistema y `ADR-024` §2 fija que NO forman
una lista: forman dos espacios disjuntos. Los tests de aca defienden esa
separacion, porque colapsarla es el error de forma que ya se cometio una vez en
`knowledge-base/03_actores_y_roles.md`.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Annotated, Any

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from app.core import auth
from app.core.auth import RUTAS_EXENTAS, Sujeto, SujetoActual
from app.core.rbac import (
    CAMPOS_DE_PERFIL,
    CAMPOS_DE_VEHICULO_SIN_COSTO,
    EQUIVALENCIA_EN_GLOSARIO,
    MATRIZ_DE_PLATAFORMA,
    MATRIZ_DE_TENANT,
    Alcance,
    AlcanceInsuficiente,
    Concesion,
    DeclaracionVacia,
    Espacio,
    EspacioAmbiguo,
    EspaciosMezclados,
    PermisoNoDeclarado,
    RolDePlataforma,
    RolDesconocido,
    RolDeTenant,
    TransicionNoPermitida,
    recortar,
    require_permission,
    require_role,
    rol_de_plataforma,
    rol_de_tenant,
    verificar_alcance,
    verificar_transicion,
)
from app.main import create_app

from ..emisor_de_tokens import EmisorDePrueba
from ..rutas import (
    alcanzables_por,
    rutas_en_el_espacio_equivocado,
    rutas_sin_declaracion_de_acceso,
)


@pytest.fixture
def proveedor() -> EmisorDePrueba:
    return EmisorDePrueba()


def cabecera(proveedor: EmisorDePrueba, *, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {proveedor.firmar(role=role)}"}


@pytest.fixture
def cliente_rbac(
    entorno_valido: dict[str, str],
    proveedor: EmisorDePrueba,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """App real con dos endpoints de prueba protegidos por rol.

    Se sustituyen las CLAVES y el EMISOR, igual que en `test_auth_rutas.py`, y
    por el mismo motivo: lo que se ejercita es el camino completo de
    autorizacion sobre un token que se valido de verdad. Un `Sujeto` inyectado a
    mano probaria `require_role` contra un doble y no contra el borde.
    """
    from app.config import get_settings

    async def traer() -> dict[str, Any]:
        return proveedor.jwks

    claves = auth.ClavesDelProveedor(url="http://no-se-usa", traer=traer)
    monkeypatch.setattr(auth, "claves_del_proveedor", lambda: claves)
    monkeypatch.setattr(auth, "emisor_esperado", lambda: proveedor.emisor)

    get_settings.cache_clear()
    app = create_app()

    @app.get("/_prueba/solo_manager", dependencies=[Depends(require_role(RolDeTenant.MANAGER))])
    async def _solo_manager() -> dict[str, str]:
        return {"ok": "si"}

    @app.get(
        "/_prueba/manager_o_admin",
        dependencies=[Depends(require_role(RolDeTenant.MANAGER, RolDeTenant.ADMIN_STAFF))],
    )
    async def _manager_o_admin() -> dict[str, str]:
        return {"ok": "si"}

    @app.get(
        "/_prueba/crear_vehiculo",
        dependencies=[Depends(require_permission("vehicles:create"))],
    )
    async def _crear_vehiculo() -> dict[str, str]:
        return {"ok": "si"}

    @app.get(
        "/_prueba/leer_tenant",
        dependencies=[Depends(require_permission("tenants:read", espacio=Espacio.TENANT))],
    )
    async def _leer_tenant() -> dict[str, str]:
        return {"ok": "si"}

    @app.get(
        "/_prueba/salud_de_tenant",
        dependencies=[Depends(require_permission("tenants:health"))],
    )
    async def _salud_de_tenant() -> dict[str, str]:
        return {"ok": "si"}

    @app.get("/_prueba/leer_vehiculos")
    async def _leer_vehiculos(
        concesion: Annotated[Concesion, Depends(require_permission("vehicles:read"))],
    ) -> dict[str, Any]:
        # Devuelve la concesion tal cual para que el test vea lo que ve el
        # endpoint: alcance y campos, no un si o un no.
        return {
            "alcance": concesion.alcance.value,
            "campos": sorted(concesion.campos) if concesion.campos else None,
        }

    with TestClient(app) as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# 6.2 — El catalogo, en un unico lugar consultable
# ─────────────────────────────────────────────────────────────────────────────


def test_el_espacio_de_tenant_tiene_exactamente_tres_roles() -> None:
    """`ADR-017` §1: `user_role_enum` conserva sus TRES valores."""
    assert {rol.value for rol in RolDeTenant} == {
        "manager",
        "salesperson",
        "admin_staff",
    }


def test_el_espacio_de_plataforma_tiene_exactamente_un_rol() -> None:
    assert {rol.value for rol in RolDePlataforma} == {"super_admin"}


def test_los_dos_espacios_no_comparten_ningun_valor() -> None:
    """`ADR-024` §2: son dos matrices disjuntas, no una de cuatro columnas."""
    de_tenant = {rol.value for rol in RolDeTenant}
    de_plataforma = {rol.value for rol in RolDePlataforma}
    assert de_tenant & de_plataforma == set()


def test_cada_rol_tiene_su_equivalencia_en_el_glosario() -> None:
    """`ADR-017` §3. La interfaz muestra los terminos en espanol del glosario.

    Se afirma la tabla completa y no su tamano: un mapa al que le falte una
    entrada tiene el largo mal, pero uno con una entrada equivocada tiene el
    largo bien.
    """
    assert EQUIVALENCIA_EN_GLOSARIO == {
        RolDeTenant.MANAGER: "Gerente",
        RolDeTenant.SALESPERSON: "Vendedor",
        RolDeTenant.ADMIN_STAFF: "Administrativo",
        RolDePlataforma.SUPER_ADMIN: "Super Admin",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6.3 — Un rol fuera del catalogo no se resuelve, se rechaza
# ─────────────────────────────────────────────────────────────────────────────


def test_un_rol_del_catalogo_se_resuelve() -> None:
    assert rol_de_tenant("manager") is RolDeTenant.MANAGER
    assert rol_de_plataforma("super_admin") is RolDePlataforma.SUPER_ADMIN


@pytest.mark.parametrize(
    ("nombre", "por_que"),
    [
        ("gerente", "el termino del glosario, no el valor del enum"),
        ("Manager", "el catalogo no es indiferente a las mayusculas"),
        ("", "la cadena vacia no es un rol"),
        ("  manager  ", "no se recortan espacios: se rechaza lo que no es exacto"),
        ("owner", "un rol que no existe en ningun espacio"),
    ],
)
def test_un_rol_fuera_del_catalogo_de_tenant_se_rechaza(nombre: str, por_que: str) -> None:
    with pytest.raises(RolDesconocido):
        rol_de_tenant(nombre)


def test_el_rol_de_plataforma_no_se_resuelve_en_el_espacio_de_tenant() -> None:
    """El caso mas peligroso: `super_admin` ES un rol real, pero no de aca.

    `ADR-024` §2 lo dice en los dos sentidos. Que exista en el otro espacio es
    justamente lo que vuelve verosimil el error.
    """
    with pytest.raises(RolDesconocido):
        rol_de_tenant("super_admin")


def test_un_rol_de_tenant_no_se_resuelve_en_el_espacio_de_plataforma() -> None:
    with pytest.raises(RolDesconocido):
        rol_de_plataforma("manager")


def test_el_rechazo_dice_que_rol_fallo_y_cual_era_el_catalogo() -> None:
    """Detectable, dice 6.3. Un error mudo no se arregla: se ignora."""
    with pytest.raises(RolDesconocido) as capturado:
        rol_de_tenant("gerente")

    mensaje = str(capturado.value)
    assert "gerente" in mensaje
    assert "manager" in mensaje


# ─────────────────────────────────────────────────────────────────────────────
# 6.4 — `require_role`, y el 403 que no se confunde con el 401
#
# La mitad de 6.3 que falta: que un rol mal declarado rompa ANTES de atender
# peticiones, y que no degenere en "nadie" ni en "cualquiera".
# ─────────────────────────────────────────────────────────────────────────────


def test_declarar_un_rol_fuera_del_catalogo_falla_sin_atender_ninguna_peticion() -> None:
    """El corazon de 6.3: falla al DECLARAR, no al recibir la primera peticion.

    No hay `TestClient` en este test y es a proposito — la afirmacion es que
    nunca hizo falta uno. Si esto fallara recien en la peticion, un endpoint mal
    declarado se descubriria en produccion y no al arrancar.
    """
    with pytest.raises(RolDesconocido):
        require_role("gerente")


def test_mezclar_los_dos_espacios_en_una_declaracion_falla() -> None:
    """`ADR-024` §2: no hay un solo endpoint donde los dos espacios compitan.

    Una declaracion que admite un rol de tenant Y el de plataforma describe un
    endpoint que el sistema no admite. Se rechaza al declararlo y no se resuelve
    dandole la razon a alguno de los dos.
    """
    with pytest.raises(EspaciosMezclados):
        require_role(RolDeTenant.MANAGER, RolDePlataforma.SUPER_ADMIN)


def test_declarar_sin_ningun_rol_falla() -> None:
    """`require_role()` vacio es exactamente la ambiguedad que 6.3 prohibe.

    Un conjunto vacio de admitidos se lee como "nadie" o como "cualquiera"
    segun como este escrita la comprobacion, y las dos lecturas son defendibles.
    Cuando las dos son defendibles, la respuesta correcta es no elegir: se
    rechaza la declaracion.
    """
    with pytest.raises(DeclaracionVacia):
        require_role()


def test_el_rol_admitido_atiende(cliente_rbac: TestClient, proveedor: EmisorDePrueba) -> None:
    respuesta = cliente_rbac.get(
        "/_prueba/solo_manager",
        headers=cabecera(proveedor, role="manager"),
    )
    assert respuesta.status_code == 200


def test_un_rol_del_catalogo_sin_ese_permiso_recibe_403(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    respuesta = cliente_rbac.get(
        "/_prueba/solo_manager",
        headers=cabecera(proveedor, role="salesperson"),
    )
    assert respuesta.status_code == 403


def test_sin_token_es_401_y_no_403(cliente_rbac: TestClient) -> None:
    """La distincion que `errors.py` ya justifica en la docstring de 401.

    Un 403 sin token manda a pedir permisos cuando lo que falta es presentarse;
    un 401 por falta de rol manda a renovar un token que esta perfecto.
    """
    respuesta = cliente_rbac.get("/_prueba/solo_manager")
    assert respuesta.status_code == 401


def test_el_401_y_el_403_se_distinguen_por_codigo_y_no_solo_por_estado(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    sin_token = cliente_rbac.get("/_prueba/solo_manager")
    con_rol_insuficiente = cliente_rbac.get(
        "/_prueba/solo_manager",
        headers=cabecera(proveedor, role="salesperson"),
    )

    assert sin_token.json()["code"] == "not_authenticated"
    assert con_rol_insuficiente.json()["code"] == "insufficient_role"


def test_un_token_con_un_rol_que_no_existe_es_403_y_no_un_error_del_servidor(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    """El token es valido; su rol, no. Eso es "se quien sos y no podes".

    Que no sea 500 es la mitad importante: un rol desconocido en un token es
    algo que un proveedor de identidad mal configurado produce, y tumbar el
    endpoint con una excepcion no atrapada convierte un problema de
    configuracion en una caida.
    """
    respuesta = cliente_rbac.get(
        "/_prueba/solo_manager",
        headers=cabecera(proveedor, role="gerente"),
    )
    assert respuesta.status_code == 403


def test_el_403_no_filtra_el_catalogo_de_roles(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Quien no puede no se entera de quien si.

    El mensaje de `RolDesconocido` enumera el catalogo —sirve para depurar una
    declaracion— pero eso es para el log, no para la respuesta.
    """
    respuesta = cliente_rbac.get(
        "/_prueba/solo_manager",
        headers=cabecera(proveedor, role="salesperson"),
    )
    cuerpo = respuesta.text
    assert "manager" not in cuerpo
    assert "salesperson" not in cuerpo


def test_una_declaracion_con_varios_roles_admite_a_los_dos_y_rechaza_al_tercero(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Sin herencia (`ADR-024` §5): los admitidos se enumeran, uno por uno."""
    for rol in ("manager", "admin_staff"):
        assert (
            cliente_rbac.get(
                "/_prueba/manager_o_admin", headers=cabecera(proveedor, role=rol)
            ).status_code
            == 200
        )

    assert (
        cliente_rbac.get(
            "/_prueba/manager_o_admin", headers=cabecera(proveedor, role="salesperson")
        ).status_code
        == 403
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6.8 — Denegar por defecto
# ─────────────────────────────────────────────────────────────────────────────

# Los nueve modulos que `ADR-024` §8 deja SIN ninguna fuente de permisos. No
# estan incompletos: estan cerrados con denegacion explicita.
MODULOS_NO_DECLARADOS = (
    "trade_in",
    "finance",
    "documents",
    "accounting",
    "operations",
    "analytics",
    "notifications",
    "audit",
)


@pytest.mark.parametrize("modulo", MODULOS_NO_DECLARADOS)
def test_ningun_rol_tiene_permisos_de_los_modulos_no_declarados(modulo: str) -> None:
    """`ADR-024` §8. Se recorre la matriz entera, no una lista a mano."""
    concedidos = {
        permiso
        for celdas in (*MATRIZ_DE_TENANT.values(), *MATRIZ_DE_PLATAFORMA.values())
        for permiso in celdas
    }
    assert {p for p in concedidos if p.startswith(f"{modulo}:")} == set()


def test_un_permiso_que_ningun_rol_tiene_no_se_puede_exigir() -> None:
    """Un permiso sin una sola celda es una operacion que no autoriza a nadie.

    Se rechaza al DECLARAR y no al atender, por el mismo motivo que un rol
    invalido: un permiso que nadie tiene y que nadie escribio a proposito es un
    error de tipeo, y su efecto —bloquear a todos— es indistinguible de haberlo
    querido. `ADR-024` §8 lo pide desde el otro lado: el change que traiga un
    modulo debe agregar sus filas ANTES de exponer el endpoint.
    """
    with pytest.raises(PermisoNoDeclarado):
        require_permission("documents:read")


def test_un_permiso_mal_escrito_no_pasa_por_denegar_por_defecto() -> None:
    """El modo de falla que 6.8 tiene que evitar sin romper la regla.

    "Denegar por defecto" es la respuesta correcta en tiempo de PETICION. En
    tiempo de declaracion seria una tapadera: `vehicles:raed` denegaria a todos
    y el endpoint pareceria estar funcionando bien.
    """
    with pytest.raises(PermisoNoDeclarado):
        require_permission("vehicles:raed")


def test_un_rol_sin_esa_celda_recibe_403(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    """`salesperson` no tiene `vehicles:create`. La ausencia es la denegacion."""
    respuesta = cliente_rbac.get(
        "/_prueba/crear_vehiculo", headers=cabecera(proveedor, role="salesperson")
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "insufficient_permission"


def test_el_403_por_permiso_se_distingue_del_403_por_rol(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    por_rol = cliente_rbac.get(
        "/_prueba/solo_manager", headers=cabecera(proveedor, role="salesperson")
    )
    por_permiso = cliente_rbac.get(
        "/_prueba/crear_vehiculo", headers=cabecera(proveedor, role="salesperson")
    )
    assert por_rol.json()["code"] == "insufficient_role"
    assert por_permiso.json()["code"] == "insufficient_permission"


# ─────────────────────────────────────────────────────────────────────────────
# 6.5 — La matriz, transcrita de `ADR-024` §6 y §7
#
# Estos tests NO reescriben la matriz celda por celda: eso seria copiarla dos
# veces y que las dos copias se equivoquen igual. Afirman las reglas de negocio
# que la matriz existe para hacer cumplir, cada una con su `RN-XX`.
# ─────────────────────────────────────────────────────────────────────────────


def test_cada_matriz_solo_contiene_roles_de_su_espacio() -> None:
    """`ADR-024` §2, verificado sobre la estructura y no sobre la intencion."""
    assert set(MATRIZ_DE_TENANT) == set(RolDeTenant)
    assert set(MATRIZ_DE_PLATAFORMA) == set(RolDePlataforma)


def test_own_no_existe_para_manager_ni_para_admin_staff() -> None:
    """`ADR-024` §4, ultimo punto: sus alcances son siempre `all` o denegado."""
    for rol in (RolDeTenant.MANAGER, RolDeTenant.ADMIN_STAFF):
        alcances = {c.alcance for c in MATRIZ_DE_TENANT[rol].values()}
        assert Alcance.OWN not in alcances


def test_las_celdas_de_auth_y_de_perfil_usan_self_y_no_own() -> None:
    """`ADR-033`. `own` es `assigned_user_id`, y un usuario no esta asignado."""
    for rol in RolDeTenant:
        assert MATRIZ_DE_TENANT[rol]["auth:read_me"].alcance is Alcance.SELF

    for rol in (RolDeTenant.SALESPERSON, RolDeTenant.ADMIN_STAFF):
        celda = MATRIZ_DE_TENANT[rol]["users:update"]
        assert celda.alcance is Alcance.SELF
        assert celda.campos == CAMPOS_DE_PERFIL


def test_solo_el_manager_reasigna_leads() -> None:
    """`RN-CR-13`. Es la regla que le da sentido al `own` estricto de §4."""
    tienen = {rol for rol in RolDeTenant if "leads:assign" in MATRIZ_DE_TENANT[rol]}
    assert tienen == {RolDeTenant.MANAGER}


def test_admin_staff_lee_leads_pero_no_los_escribe() -> None:
    """`RN-CR-12`. La vista funcional le daba escritura, pero venia de N4."""
    celdas = MATRIZ_DE_TENANT[RolDeTenant.ADMIN_STAFF]
    assert "leads:read" in celdas
    for escritura in ("leads:create", "leads:update", "leads:change_stage", "leads:close"):
        assert escritura not in celdas


def test_el_vendedor_no_ve_el_costo_de_adquisicion() -> None:
    """`RN-ST-12`, sobre un recurso que si puede leer.

    De ahi que `ADR-024` §3 tuviera que extender la restriccion de campos a la
    LECTURA, que la spec de authorization no preveia.
    """
    vendedor = MATRIZ_DE_TENANT[RolDeTenant.SALESPERSON]["vehicles:read"]
    assert vendedor.campos is not None
    assert "acquisition_cost_ars" not in vendedor.campos

    for rol in (RolDeTenant.MANAGER, RolDeTenant.ADMIN_STAFF):
        assert MATRIZ_DE_TENANT[rol]["vehicles:read"].campos is None


def test_la_lista_blanca_del_vendedor_es_el_esquema_de_salida_vigente() -> None:
    """Contra la deriva.

    El dia que `VehiculoSalida` gane un campo, este test falla y obliga a
    decidir si el vendedor lo ve. Un conjunto escrito a mano que nadie compara
    envejece en silencio, y envejece hacia el lado que abre.
    """
    from app.modules.stock.schemas import VehiculoSalida

    vendedor = MATRIZ_DE_TENANT[RolDeTenant.SALESPERSON]["vehicles:read"]
    assert vendedor.campos == frozenset(VehiculoSalida.model_fields)


def test_campos_de_vehiculo_sin_costo_es_exactamente_vehiculo_salida() -> None:
    """`H-b` de C-14: el guardian que el docstring de `CAMPOS_DE_VEHICULO_SIN_COSTO`
    afirma tener y que un `grep` sobre la constante no encontraba.

    El test de arriba (`test_la_lista_blanca_del_vendedor_es_el_esquema_de_
    salida_vigente`) YA ejercita esta misma garantia, pero pasando por la celda
    de la matriz — nunca importa la constante por nombre. Este la nombra
    explicitamente: `RN-ST-12` se rompe si las dos listas se despegan, y tiene
    que poder encontrarse buscando el nombre de la constante, no solo su efecto.
    """
    from app.modules.stock.schemas import VehiculoSalida

    assert CAMPOS_DE_VEHICULO_SIN_COSTO == frozenset(VehiculoSalida.model_fields)


def test_ningun_rol_de_tenant_cambia_el_plan_contratado() -> None:
    """`RN-MT-10` sin excepciones (K-3). El autoservicio del plan GTM es N4."""
    for rol in RolDeTenant:
        assert "tenants:update_plan" not in MATRIZ_DE_TENANT[rol]
    assert "tenants:update_plan" in MATRIZ_DE_PLATAFORMA[RolDePlataforma.SUPER_ADMIN]


def test_el_catalogo_lo_leen_todos_y_lo_escribe_solo_la_plataforma() -> None:
    """`RN-ST-15`. La unica tabla que los tres leen sin que `tenant_id` medie."""
    for rol in RolDeTenant:
        assert MATRIZ_DE_TENANT[rol]["catalog:read"].alcance is Alcance.ALL
        assert "catalog:write" not in MATRIZ_DE_TENANT[rol]
    assert "catalog:write" in MATRIZ_DE_PLATAFORMA[RolDePlataforma.SUPER_ADMIN]


def test_el_derecho_de_supresion_es_solo_del_manager() -> None:
    """Ley 25.326. Irreversible sobre datos personales, sin fuente que lo asigne."""
    tienen = {rol for rol in RolDeTenant if "contacts:forget" in MATRIZ_DE_TENANT[rol]}
    assert tienen == {RolDeTenant.MANAGER}


def test_require_permission_entrega_la_concesion_y_no_un_si_o_no(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    """El porton no alcanza: la restriccion de campos aplica a LECTURA.

    Un endpoint que solo sabe "podes" no puede recortar la respuesta. Necesita
    el alcance y el conjunto de campos que le tocan a quien pregunta.
    """
    respuesta = cliente_rbac.get(
        "/_prueba/leer_vehiculos", headers=cabecera(proveedor, role="salesperson")
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["alcance"] == "all"
    assert "acquisition_cost_ars" not in cuerpo["campos"]


def test_la_concesion_del_manager_no_recorta_campos(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    respuesta = cliente_rbac.get(
        "/_prueba/leer_vehiculos", headers=cabecera(proveedor, role="manager")
    )
    assert respuesta.json()["campos"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 6.7 — Separacion cross-tenant, en el eje de los permisos
#
# `ADR-024` §2 lo exige en los DOS sentidos: ningun rol de tenant entra al
# espacio administrativo, y el rol de plataforma no obtiene acceso cross-tenant
# fuera de el. Lo que hace verosimil el error es que una clave puede existir en
# las dos matrices — hoy `tenants:read`, que el `manager` tiene sobre su propia
# agencia y el `super_admin` sobre todas.
# ─────────────────────────────────────────────────────────────────────────────


def test_hay_al_menos_una_clave_en_las_dos_matrices() -> None:
    """El supuesto sobre el que descansan los tests de abajo.

    Si algun dia no quedara ninguna clave compartida, estos tests seguirian
    pasando sin probar nada — y este test avisaria de que ya no hacen falta.
    """
    de_tenant = {p for celdas in MATRIZ_DE_TENANT.values() for p in celdas}
    de_plataforma = {p for celdas in MATRIZ_DE_PLATAFORMA.values() for p in celdas}
    assert de_tenant & de_plataforma


def test_una_clave_que_existe_en_los_dos_espacios_exige_declarar_cual() -> None:
    """No se resuelve por defecto ni por orden de busqueda.

    Resolver "el primero que matchee" convierte el orden de dos diccionarios en
    una decision de autorizacion. Se rechaza al declarar, como todo lo demas.
    """
    with pytest.raises(EspacioAmbiguo):
        require_permission("tenants:read")


def test_declarar_un_permiso_en_el_espacio_equivocado_falla() -> None:
    """`catalog:write` solo lo tiene la plataforma (`RN-ST-15`)."""
    with pytest.raises(PermisoNoDeclarado):
        require_permission("catalog:write", espacio=Espacio.TENANT)


def test_el_super_admin_no_alcanza_un_permiso_del_espacio_de_tenant(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    """El sentido menos intuitivo de `ADR-024` §2, y el mas peligroso.

    `super_admin` es el rol mas poderoso del sistema y aun asi no llega a
    `/api/v1`: para ver datos de un tenant IMPERSONA (K-4), lo que abre una
    sesion con el `tenant_id` de ese tenant y queda auditada por `RN-AD-06`.
    Concederselo directo convertiria la exencion de RLS de `ADR-017` en una
    puerta permanente en lugar de un rodeo trazado.
    """
    respuesta = cliente_rbac.get(
        "/_prueba/leer_tenant", headers=cabecera(proveedor, role="super_admin")
    )
    assert respuesta.status_code == 403


def test_un_rol_de_tenant_no_alcanza_un_permiso_del_espacio_de_plataforma(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    for rol in ("manager", "salesperson", "admin_staff"):
        respuesta = cliente_rbac.get(
            "/_prueba/salud_de_tenant", headers=cabecera(proveedor, role=rol)
        )
        assert respuesta.status_code == 403, rol


def test_el_super_admin_alcanza_su_propio_espacio(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Contrapeso: si nada de `/admin` funcionara, los tests de arriba pasarian
    igual y no probarian la separacion sino una denegacion total."""
    respuesta = cliente_rbac.get(
        "/_prueba/salud_de_tenant", headers=cabecera(proveedor, role="super_admin")
    )
    assert respuesta.status_code == 200


def test_el_manager_alcanza_la_clave_compartida_en_su_propio_espacio(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    respuesta = cliente_rbac.get(
        "/_prueba/leer_tenant", headers=cabecera(proveedor, role="manager")
    )
    assert respuesta.status_code == 200


def test_un_rol_desconocido_en_el_token_es_403_y_no_un_error_del_servidor(
    cliente_rbac: TestClient, proveedor: EmisorDePrueba
) -> None:
    """Un proveedor de identidad mal configurado es un problema de
    configuracion; devolver 500 lo asciende a caida."""
    respuesta = cliente_rbac.get(
        "/_prueba/leer_vehiculos", headers=cabecera(proveedor, role="gerente")
    )
    assert respuesta.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# 6.11 — Sin herencia entre roles
#
# `ADR-024` §5. La trampa que la ausencia de herencia introduce no es que los
# roles sean distintos: es que HOY PARECEN anidados. `manager` contiene por
# clave a los otros dos, y esa contencion accidental invita a escribir una
# verificacion que recorra "el rol y los de arriba". El dia que alguien le
# agregue una celda a `salesperson` sin agregarsela al `manager`, esa
# verificacion sigue en verde y miente.
# ─────────────────────────────────────────────────────────────────────────────


def _claves(rol: RolDeTenant) -> set[str]:
    return set(MATRIZ_DE_TENANT[rol])


def test_los_roles_de_tenant_no_forman_una_cadena() -> None:
    """`salesperson` y `admin_staff` son MUTUAMENTE incomparables.

    Cada uno tiene celdas que el otro no: el vendedor mueve leads y estados de
    vehiculo, el administrativo importa stock y opera plantillas de WhatsApp.
    Con eso alcanza para descartar cualquier orden total entre los tres, y por
    lo tanto cualquier recorrido que asuma contencion.
    """
    vendedor, administrativo = _claves(RolDeTenant.SALESPERSON), _claves(RolDeTenant.ADMIN_STAFF)
    assert vendedor - administrativo
    assert administrativo - vendedor


def test_la_contencion_del_manager_es_por_clave_y_no_por_concesion() -> None:
    """El manager contiene a los otros dos por CLAVE, y eso confunde.

    Este test fija esa apariencia por escrito para que nadie la lea como
    herencia: las claves coinciden, las concesiones no. `leads:read` es `all`
    para el manager y `own` para el vendedor — el mismo nombre, dos permisos.
    """
    gerente = _claves(RolDeTenant.MANAGER)
    assert _claves(RolDeTenant.SALESPERSON) <= gerente
    assert _claves(RolDeTenant.ADMIN_STAFF) <= gerente

    de_gerente = MATRIZ_DE_TENANT[RolDeTenant.MANAGER]["leads:read"]
    de_vendedor = MATRIZ_DE_TENANT[RolDeTenant.SALESPERSON]["leads:read"]
    assert de_gerente.alcance is Alcance.ALL
    assert de_vendedor.alcance is Alcance.OWN


def test_agregarle_una_celda_a_un_rol_no_se_la_da_a_ningun_otro() -> None:
    """El mecanismo, no los datos de hoy — es lo que §5 advierte literalmente.

    Se le agrega un permiso inventado a una COPIA de las celdas del vendedor y
    se comprueba que el recorrido de los otros dos roles no lo ve. Sobre copias
    y no sobre la matriz real: un test que mute el estado del modulo le cambia
    la autorizacion a todos los tests que corran despues.
    """
    copia = {rol: dict(celdas) for rol, celdas in MATRIZ_DE_TENANT.items()}
    copia[RolDeTenant.SALESPERSON]["inventado:hacer"] = Concesion(Alcance.OWN)

    assert "inventado:hacer" in copia[RolDeTenant.SALESPERSON]
    for otro in (RolDeTenant.MANAGER, RolDeTenant.ADMIN_STAFF):
        assert "inventado:hacer" not in copia[otro]


# ─────────────────────────────────────────────────────────────────────────────
# 6.9 — La verificacion automatica sobre las operaciones realmente expuestas
#
# Dos recorridos DISJUNTOS (`ADR-024` §2): los tres roles de tenant contra
# `/api/v1`, y el rol de plataforma contra `/admin/api/v1`.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def app_real(entorno_valido: dict[str, str]) -> FastAPI:
    """La aplicacion de verdad, con todos sus routers montados.

    Sin `TestClient`: no se manda ni una peticion. Lo que se inspecciona es la
    DECLARACION de cada ruta, y ejercitar las respuestas seria otra cosa.
    """
    from app.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    return create_app()


def test_ninguna_operacion_de_tenant_se_expone_sin_declarar_su_acceso(
    app_real: FastAPI,
) -> None:
    """El recorrido del espacio de tenant.

    Una ruta sin declaracion la atiende CUALQUIER sujeto autenticado, sea cual
    sea su rol. Es el modo de falla que no se ve leyendo el codigo: no hay nada
    escrito que revisar, solo algo que falta.

    Las operaciones nuevas entran solas: se recorre lo que la app expone.
    """
    assert (
        rutas_sin_declaracion_de_acceso(app_real, prefijo="/api/v1", exentas=RUTAS_EXENTAS) == set()
    )


def test_ninguna_operacion_de_tenant_exige_un_permiso_de_plataforma(
    app_real: FastAPI,
) -> None:
    """`ADR-024` §2. Un endpoint de `/api/v1` que exija una celda de la matriz
    de plataforma se la estaria pidiendo a roles que nunca la van a tener."""
    assert (
        rutas_en_el_espacio_equivocado(app_real, prefijo="/api/v1", espacio=Espacio.TENANT) == set()
    )


def test_el_recorrido_de_tenant_va_rol_por_rol_y_da_alcances_distintos(
    app_real: FastAPI,
) -> None:
    """Los tres roles por separado, sin asumir contencion (`ADR-024` §5).

    Que los tres conjuntos NO sean iguales es lo que prueba que el recorrido
    distingue: si la verificacion colapsara los roles, los tres darian lo mismo
    y estaria pasando sin mirar nada.
    """
    alcance = {
        rol: alcanzables_por(app_real, rol, MATRIZ_DE_TENANT[rol], prefijo="/api/v1")
        for rol in RolDeTenant
    }

    assert len({frozenset(rutas) for rutas in alcance.values()}) > 1
    # El vendedor no crea stock ni importa planillas; el administrativo si.
    assert "/api/v1/vehicles" in alcance[RolDeTenant.SALESPERSON]
    assert "/api/v1/imports" not in alcance[RolDeTenant.SALESPERSON]
    assert "/api/v1/imports" in alcance[RolDeTenant.ADMIN_STAFF]


def test_el_recorrido_de_plataforma_no_alcanza_nada_del_espacio_de_tenant(
    app_real: FastAPI,
) -> None:
    """El otro recorrido, y es disjunto de verdad: hoy `/admin/api/v1` no tiene
    una sola ruta montada, y aun asi el `super_admin` no alcanza `/api/v1`."""
    del app_real  # el recorrido de abajo no necesita la app: es sobre la matriz
    celdas = MATRIZ_DE_PLATAFORMA[RolDePlataforma.SUPER_ADMIN]
    de_tenant = {p for c in MATRIZ_DE_TENANT.values() for p in c}
    # La unica clave compartida es `tenants:read`, y vive en otro espacio: por
    # eso `require_permission` obliga a declararlo y `_celdas_en` mira una sola
    # matriz. Sin esas dos cosas, esta interseccion seria una puerta.
    assert de_tenant & set(celdas) == {"tenants:read"}


def test_el_detector_encuentra_una_operacion_expuesta_sin_declarar() -> None:
    """Control positivo. Un detector que nunca detecto nada no es un detector.

    Se monta una ruta con identidad pero sin permiso —el caso realista: alguien
    se acuerda del token y se olvida del rol— y se comprueba que la delata.
    """
    app = FastAPI()

    @app.get("/api/v1/colada")
    async def _colada(sujeto: SujetoActual) -> dict[str, str]:
        return {}

    assert rutas_sin_declaracion_de_acceso(app, prefijo="/api/v1", exentas=frozenset()) == {
        "/api/v1/colada"
    }


def test_el_detector_ve_las_rutas_montadas_por_include_router() -> None:
    """La ceguera que costo el bugfix de `fa9a79d`, sobre el gate nuevo.

    `include_router` no aplana las rutas en `app.routes`. El detector nuevo usa
    el mismo recorrido corregido; este test lo fija para que la correccion no se
    pierda al moverla de archivo.
    """
    app = FastAPI()
    interno = APIRouter(prefix="/api/v1")

    @interno.get("/adentro")
    async def _adentro(sujeto: SujetoActual) -> dict[str, str]:
        return {}

    app.include_router(interno)

    assert rutas_sin_declaracion_de_acceso(app, prefijo="/api/v1", exentas=frozenset()) == {
        "/api/v1/adentro"
    }


def test_el_detector_no_marca_una_operacion_declarada() -> None:
    """Contrapeso: un detector que marca todo tampoco sirve."""
    app = FastAPI()

    @app.get(
        "/api/v1/declarada",
        dependencies=[Depends(require_permission("vehicles:read"))],
    )
    async def _declarada() -> dict[str, str]:
        return {}

    assert rutas_sin_declaracion_de_acceso(app, prefijo="/api/v1", exentas=frozenset()) == set()


def test_el_detector_encuentra_un_permiso_del_espacio_equivocado() -> None:
    app = FastAPI()

    @app.get(
        "/api/v1/administrativa",
        dependencies=[Depends(require_permission("tenants:health"))],
    )
    async def _administrativa() -> dict[str, str]:
        return {}

    assert rutas_en_el_espacio_equivocado(app, prefijo="/api/v1", espacio=Espacio.TENANT) == {
        "/api/v1/administrativa"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6.6 / 6.10 — Los mecanismos de alcance fino
#
# La matriz dice QUE le toca a cada rol. Estas dos funciones son lo que lo hace
# cumplir: una acota el conjunto de registros, la otra el conjunto de campos.
# Se prueban aca, sin base; su aplicacion sobre endpoints reales va en
# `tests/integration/test_alcance_fino.py`.
# ─────────────────────────────────────────────────────────────────────────────

UN_SUJETO = uuid.uuid4()
OTRO_SUJETO = uuid.uuid4()


def _sujeto(identificador: uuid.UUID = UN_SUJETO, rol: str = "salesperson") -> Sujeto:
    return Sujeto(user_id=str(identificador), tenant_id=uuid.uuid4(), role=rol)


def test_el_alcance_all_no_mira_a_quien_esta_asignado_el_recurso() -> None:
    verificar_alcance(Concesion(Alcance.ALL), sujeto=_sujeto(), assigned_user_id=OTRO_SUJETO)


def test_el_alcance_own_admite_lo_asignado_al_sujeto() -> None:
    verificar_alcance(Concesion(Alcance.OWN), sujeto=_sujeto(), assigned_user_id=UN_SUJETO)


def test_el_alcance_own_rechaza_lo_asignado_a_otro() -> None:
    with pytest.raises(AlcanceInsuficiente):
        verificar_alcance(Concesion(Alcance.OWN), sujeto=_sujeto(), assigned_user_id=OTRO_SUJETO)


def test_el_alcance_own_rechaza_lo_que_no_esta_asignado_a_nadie() -> None:
    """`ADR-024` §4: `own` es "su `assigned_user_id` es igual al `id` del
    sujeto". Un `NULL` no es igual a nada — no es de todos, es de nadie."""
    with pytest.raises(AlcanceInsuficiente):
        verificar_alcance(Concesion(Alcance.OWN), sujeto=_sujeto(), assigned_user_id=None)


def test_el_alcance_self_admite_solo_al_propio_sujeto() -> None:
    """`ADR-033`."""
    verificar_alcance(Concesion(Alcance.SELF), sujeto=_sujeto(), recurso_id=UN_SUJETO)
    with pytest.raises(AlcanceInsuficiente):
        verificar_alcance(Concesion(Alcance.SELF), sujeto=_sujeto(), recurso_id=OTRO_SUJETO)


def test_un_sub_que_no_es_un_uuid_nunca_es_dueno_de_nada() -> None:
    """El caso degenerado, resuelto hacia el lado que cierra.

    Keycloak emite `sub` como UUID. Si algun dia llegara otra cosa, `own` no
    puede compararse — y lo que no se puede comparar no se concede.
    """
    raro = Sujeto(user_id="no-soy-un-uuid", tenant_id=uuid.uuid4(), role="salesperson")
    with pytest.raises(AlcanceInsuficiente):
        verificar_alcance(Concesion(Alcance.OWN), sujeto=raro, assigned_user_id=UN_SUJETO)


def test_una_concesion_sin_campos_no_recorta_nada() -> None:
    datos = {"id": 1, "acquisition_cost_ars": 900}
    assert recortar(datos, Concesion(Alcance.ALL)) == datos


def test_una_concesion_con_campos_deja_afuera_lo_no_declarado() -> None:
    """`RN-ST-12` en su forma general."""
    datos = {"id": 1, "price_ars": 100, "acquisition_cost_ars": 900}
    recortado = recortar(datos, Concesion(Alcance.ALL, frozenset({"id", "price_ars"})))
    assert recortado == {"id": 1, "price_ars": 100}
    assert "acquisition_cost_ars" not in recortado


def test_recortar_no_inventa_los_campos_declarados_que_faltan() -> None:
    """Un campo declarado que el dato no trae no aparece como `None`.

    Rellenarlo seria agregar informacion —"este campo existe y esta vacio"—
    donde el dato no dice nada.
    """
    recortado = recortar({"id": 1}, Concesion(Alcance.ALL, frozenset({"id", "phone"})))
    assert recortado == {"id": 1}


# ─────────────────────────────────────────────────────────────────────────────
# `ADR-034` — Transiciones, el tercer eje del permiso
# ─────────────────────────────────────────────────────────────────────────────

RESERVAR = frozenset({("available", "reserved")})


def test_una_concesion_sin_transiciones_no_acota_ninguna() -> None:
    verificar_transicion(Concesion(Alcance.ALL), desde="available", hasta="sold")


def test_la_transicion_declarada_pasa() -> None:
    verificar_transicion(
        Concesion(Alcance.OWN, transiciones=RESERVAR),
        desde="available",
        hasta="reserved",
    )


@pytest.mark.parametrize(
    ("desde", "hasta"),
    [
        ("available", "sold"),
        ("available", "archived"),
        ("reserved", "available"),
        ("in_preparation", "available"),
    ],
)
def test_toda_transicion_no_declarada_se_rechaza(desde: str, hasta: str) -> None:
    """Es un par, no un destino.

    `reserved`→`available` deshace la reserva: mismo destino que otras celdas
    permiten, y aun asi fuera de lo declarado. Acotar solo por destino le daria
    al vendedor la vuelta atras de cualquier estado.
    """
    with pytest.raises(TransicionNoPermitida):
        verificar_transicion(
            Concesion(Alcance.OWN, transiciones=RESERVAR), desde=desde, hasta=hasta
        )


def test_la_celda_del_vendedor_declara_exactamente_lo_que_dice_el_adr() -> None:
    """`ADR-024` §6: "`own`, solo `available`→`reserved`"."""
    celda = MATRIZ_DE_TENANT[RolDeTenant.SALESPERSON]["vehicles:change_status"]
    assert celda.alcance is Alcance.OWN
    assert celda.transiciones == RESERVAR


def test_ninguna_otra_celda_declara_transiciones() -> None:
    """`ADR-034`: el eje lo usa UNA celda. Si aparece una segunda sin pasar por
    un ADR, esto lo delata."""
    con_eje = {
        (rol, permiso)
        for rol, celdas in MATRIZ_DE_TENANT.items()
        for permiso, celda in celdas.items()
        if celda.transiciones is not None
    }
    assert con_eje == {(RolDeTenant.SALESPERSON, "vehicles:change_status")}


def test_los_estados_declarados_existen_en_el_enum_real() -> None:
    """Contra la deriva de cadenas.

    `core/` no puede importar `modules/`, asi que el par viaja como `str`. El
    test si puede mirar los dos lados: si alguien renombra un estado, la cadena
    de la matriz queda apuntando a la nada y el permiso deja de coincidir con
    nada — que denegaria de mas, en silencio.
    """
    from app.modules.stock.schemas import EstadoDeVehiculo

    validos = {estado.value for estado in EstadoDeVehiculo}
    celda = MATRIZ_DE_TENANT[RolDeTenant.SALESPERSON]["vehicles:change_status"]
    assert celda.transiciones is not None
    for desde, hasta in celda.transiciones:
        assert desde in validos
        assert hasta in validos


# ─────────────────────────────────────────────────────────────────────────────
# El campo excluido, pedido por otra puerta
#
# La delta spec de `platform/authorization` lo pide explicitamente: "el valor del
# campo no se revela POR NINGUN MEDIO". Recortar la respuesta no alcanza — un
# filtro por rango sobre un campo que no se puede ver lo revela igual, por
# busqueda binaria y sin mostrarlo nunca.
#
# Hoy no hay por donde: el orden del listado es fijo y ningun filtro toca el
# costo. Estos tests son el guardian de esa ausencia, que es lo unico que la
# sostiene.
# ─────────────────────────────────────────────────────────────────────────────


def test_ningun_filtro_de_busqueda_nombra_un_campo_que_el_vendedor_no_ve() -> None:
    from app.modules.stock.schemas import FiltrosDeBusqueda, VehiculoSalidaConCosto

    vendedor = MATRIZ_DE_TENANT[RolDeTenant.SALESPERSON]["vehicles:read"]
    assert vendedor.campos is not None
    excluidos = set(VehiculoSalidaConCosto.model_fields) - set(vendedor.campos)
    assert excluidos, "si no hay campos excluidos, este test no prueba nada"

    # Se compara por raices y no por igualdad: el filtro que abriria el agujero
    # no se llamaria `acquisition_cost_ars` sino `cost_from` o `cost_to`.
    raices = {
        parte
        for campo in excluidos
        for parte in campo.split("_")
        if len(parte) > 3 and parte not in {"ars", "usd"}
    }
    for parametro in FiltrosDeBusqueda.model_fields:
        assert not any(raiz in parametro for raiz in raices), parametro


def test_el_listado_no_acepta_orden_ni_proyeccion_a_pedido() -> None:
    """La forma generica del mismo agujero.

    Un `sort_by` o un `fields` de texto libre revelan cualquier columna sin
    devolverla: alcanza con ordenar por ella y leer las posiciones. El dia que
    hagan falta, tienen que nacer acotados a los campos de la concesion — y este
    test es el que va a obligar a acordarse.
    """
    from app.modules.stock.schemas import FiltrosDeBusqueda

    a_pedido = {"sort", "sort_by", "order", "order_by", "fields", "select", "expand"}
    assert a_pedido & set(FiltrosDeBusqueda.model_fields) == set()
