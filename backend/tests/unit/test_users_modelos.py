"""Los modelos de identidad, por lo que NO tienen — C-05, tarea 2.2.

El guardian de AST de `test_arquitectura.py` ya recorre `app/` entero buscando
nombres de credencial —`password_hash`, `mfa_secret` y compania— y cubre a estas
tres clases sin que haga falta nada mas.

Lo que ese guardian NO puede cubrir es `mfa_enabled`, y la razon importa:
**no es una credencial**. Es un HECHO de Keycloak, y meterlo en una lista
llamada "nombres de contraseña" seria mentir sobre por que esta prohibido.

`design.md` `D-2` lo prohibe por otro motivo: copiarlo agrega un espejo que se
desincroniza en silencio. Alguien activa TOTP en Keycloak y nuestra columna dice
`false` para siempre — y a diferencia del email, que se corrige en cada peticion
porque viaja en el token, este dato no viaja y nadie se entera.
"""

from __future__ import annotations

import pytest

from app.db.base import Base
from app.modules.users.models import (
    ESTADOS_USUARIO,
    ROLES_DE_TENANT,
    SuperAdmin,
    User,
    UserBranch,
)

TABLAS = (User, UserBranch, SuperAdmin)

# Todo lo que Keycloak sabe y nosotros NO copiamos. Los primeros por credencial
# (`ADR-026`), `mfa_enabled` por espejo que envejece (`D-2`).
DE_KEYCLOAK_Y_NO_NUESTRO = (
    "password_hash",
    "password",
    "mfa_secret",
    "mfa_enabled",
    "totp_secret",
)


@pytest.mark.parametrize("modelo", TABLAS, ids=lambda m: str(m.__tablename__))
def test_ninguna_tabla_de_identidad_copia_lo_que_es_de_keycloak(
    # `type[Base]` y no `type` a secas: `__table__` y `__tablename__` los aporta
    # la base declarativa, y `mypy --strict` no los encuentra en `type`.
    modelo: type[Base],
) -> None:
    columnas = {c.name for c in modelo.__table__.columns}
    assert columnas.isdisjoint(DE_KEYCLOAK_Y_NO_NUESTRO), (
        f"{modelo.__tablename__} declara un campo que pertenece a Keycloak: "
        f"{columnas & set(DE_KEYCLOAK_Y_NO_NUESTRO)}"
    )


def test_el_control_detecta_una_columna_prohibida() -> None:
    """Contrapeso. Un control que nunca marco nada no es un control — y este
    afirma una AUSENCIA, que es la clase de afirmacion que se sostiene sola
    hasta el dia que deja de hacerlo."""
    columnas = {"id", "email", "mfa_enabled"}
    assert not columnas.isdisjoint(DE_KEYCLOAK_Y_NO_NUESTRO)


# ── La forma que las migraciones prometieron ─────────────────────────────────


def test_users_tiene_tenant_id_y_super_admins_no() -> None:
    """`ADR-017` §2 y `D-3`, del lado del modelo.

    Es la diferencia practica entre las dos: si `super_admin` fuera un valor del
    enum, `users.tenant_id` tendria que ser nullable.
    """
    assert "tenant_id" in {c.name for c in User.__table__.columns}
    assert User.__table__.c.tenant_id.nullable is False
    assert "tenant_id" not in {c.name for c in SuperAdmin.__table__.columns}


def test_la_tabla_de_union_tiene_tenant_id_propio() -> None:
    """Sin esta columna no hay politica RLS posible, y el vinculo entre dos
    tablas protegidas quedaria fuera del aislamiento."""
    assert "tenant_id" in {c.name for c in UserBranch.__table__.columns}
    assert UserBranch.__table__.c.tenant_id.nullable is False


def test_el_catalogo_de_roles_del_modelo_coincide_con_el_de_rbac() -> None:
    """Los dos se escriben por separado a proposito: este modulo describe la
    FORMA de la columna, `rbac.py` la matriz de permisos. Que sean listas
    distintas es correcto; que digan cosas distintas, no."""
    from app.core.rbac import RolDeTenant

    assert set(ROLES_DE_TENANT) == {rol.value for rol in RolDeTenant}


def test_los_estados_del_usuario_son_los_cuatro_de_la_spec() -> None:
    assert set(ESTADOS_USUARIO) == {"invited", "active", "inactive", "suspended"}


def test_ninguna_tabla_de_identidad_se_borra_fisicamente() -> None:
    """Principio 3. `UserBranch` es la excepcion y tiene su motivo: es un
    vinculo, no una entidad — desasignar una sucursal no es dar de baja a nadie,
    y conservar filas muertas ahi solo complica la unicidad de la principal."""
    assert "deleted_at" in {c.name for c in User.__table__.columns}
    assert "deleted_at" in {c.name for c in SuperAdmin.__table__.columns}
