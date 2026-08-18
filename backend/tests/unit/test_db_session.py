"""Contrato del contexto de tenant — C-02, tareas 1.4 a 1.6.

Que se prueba aca y que NO. Aca se prueba el CONTRATO: que el tenant se valida
antes de tocar la base, que las dos puertas de sesion existen y se distinguen,
y que la sentencia que establece el contexto lleva el valor **bindeado** y no
concatenado. Que el aislamiento realmente aisle se prueba en
`tests/integration/test_tenant_isolation.py`, contra PostgreSQL de verdad
(regla dura 8): eso no es simulable.

TRUCO PARA PROBAR EL ORDEN SIN MOCKS DE BASE
────────────────────────────────────────────
"Se valida antes de tocar la base" es una afirmacion sobre el ORDEN de dos
cosas. Para probarla, el engine de estos tests apunta a una direccion
inalcanzable: si el codigo intentara conectarse primero, el error seria de
conexion. Que el error sea de validacion es la prueba de que ni lo intento.

Un doble de la base habria probado lo mismo, pero probando el doble.
"""

from __future__ import annotations

import inspect

import pytest

from app.db.session import (
    SENTENCIA_CONTEXTO,
    ContextoDeTenantInvalido,
    sesion_de_plataforma,
    sesion_de_tenant,
)

# Puerto cerrado a proposito. Cualquier intento real de conectar falla aca.
DSN_INALCANZABLE = "postgresql+asyncpg://u:p@127.0.0.1:1/nada"

TENANT = "3f1a7c8e-2b4d-4e6f-9a0b-1c2d3e4f5a6b"


# ── El tenant se valida antes de tocar la base ───────────────────────────────


@pytest.mark.parametrize(
    "valor",
    [
        "no-soy-un-uuid",
        "",
        "3f1a7c8e-2b4d-4e6f-9a0b",  # truncado
        "3f1a7c8e2b4d4e6f9a0b1c2d3e4f5a6b'; DROP TABLE users; --",
    ],
)
async def test_un_tenant_no_parseable_falla_por_validacion(valor: str) -> None:
    """El engine apunta a un puerto cerrado: si intentara conectar, el error
    seria de conexion. Que sea de validacion prueba que ni lo intento."""
    with pytest.raises(ContextoDeTenantInvalido):
        async with sesion_de_tenant(valor, dsn=DSN_INALCANZABLE):
            pytest.fail("no deberia haber llegado a abrir la sesion")


async def test_sin_tenant_tampoco_se_toca_la_base() -> None:
    with pytest.raises(ContextoDeTenantInvalido):
        async with sesion_de_tenant(None, dsn=DSN_INALCANZABLE):
            pytest.fail("no deberia haber llegado a abrir la sesion")


async def test_un_tenant_valido_si_llega_a_intentar_la_conexion() -> None:
    """El contrapunto del test de arriba, y la mitad que le da valor.

    Sin este, un `sesion_de_tenant` que rechazara TODO cumpliria los anteriores.
    Con un UUID valido el error tiene que ser de CONEXION.

    Se exige el tipo exacto y no un `Exception` cualquiera: la primera version
    de este test aceptaba cualquier excepcion que no fuera de validacion, y
    pasaba en verde por un `ConfigurationError` — o sea sin haber llegado nunca
    a intentar la conexion. Un test que se cumple por el motivo equivocado es
    peor que no tenerlo: ocupa el lugar del que si probaba algo.
    """
    with pytest.raises(OSError) as capturado:
        async with sesion_de_tenant(TENANT, dsn=DSN_INALCANZABLE):
            pytest.fail("la conexion no puede prosperar contra un puerto cerrado")

    assert not isinstance(capturado.value, ContextoDeTenantInvalido)


# ── La sentencia no se arma por concatenacion (regla dura 9) ─────────────────


def test_la_sentencia_de_contexto_usa_parametro_bindeado() -> None:
    """`SET LOCAL` no admite bind, y por eso se usa `set_config`.

    Este test fija esa decision (design.md D-2). Si alguien vuelve a `SET LOCAL`
    tendria que interpolar el uuid en el texto de la sentencia: concatenar SQL
    en el control mas critico del sistema.
    """
    texto = str(SENTENCIA_CONTEXTO)

    assert "set_config" in texto
    assert ":tenant" in texto
    assert "app.current_tenant" in texto
    # El nombre correcto es `app.current_tenant`, NO `app.current_tenant_id`
    # (design.md D-1). Un nombre mal puesto no falla ruidosamente: devuelve
    # vacio y las consultas dejan de traer filas.
    assert "app.current_tenant_id" not in texto


def test_el_contexto_es_local_a_la_transaccion() -> None:
    """El tercer argumento de `set_config` es `is_local`.

    En `true`, el valor muere con la transaccion. En `false` sobreviviria en la
    conexion, y la conexion vuelve al pool: el proximo request que la tome
    heredaria el tenant del anterior. Eso es una fuga cross-tenant.
    """
    assert "true" in str(SENTENCIA_CONTEXTO).lower()


# ── Las dos puertas se distinguen por el nombre ──────────────────────────────


def test_la_sesion_de_plataforma_es_una_funcion_aparte() -> None:
    """No es `sesion_de_tenant(tenant=None)` (design.md D-4).

    Un booleano en la llamada se lee como un detalle en una revision de codigo.
    Un nombre distinto se lee como una decision.

    La version anterior de este test empezaba con
    `assert sesion_de_plataforma is not sesion_de_tenant`, que **es verdadera
    siempre**: son dos objetos funcion distintos y ninguna implementacion
    posible los volveria el mismo. Lo delato `mypy --strict` con
    `comparison-overlap`, no una revision.

    Lo que hay que verificar no es que sean distintas, sino que la de
    plataforma NO tenga por donde recibir un tenant — que es la forma que
    tendria si alguien la colapsara en `sesion_de_tenant(tenant=None)`.
    """
    parametros_plataforma = set(inspect.signature(sesion_de_plataforma).parameters)
    parametros_tenant = set(inspect.signature(sesion_de_tenant).parameters)

    assert "tenant_id" not in parametros_plataforma
    assert "tenant_id" in parametros_tenant
    assert "plataforma" in sesion_de_plataforma.__name__
