"""Las tres tablas de identidad, sobre base real — C-05, bloque 1.

QUE SE PRUEBA ACA
──────────────────
Las invariantes que las migraciones `013`, `014` y `015` prometen y que
`alembic upgrade` no verifica: que las politicas RLS existan de verdad, que la
unicidad del email sea POR AGENCIA e insensible a mayusculas, y que la tabla de
union aisle igual que las dos que une.

`super_admins` se prueba por lo que **no** tiene: es la unica tabla de identidad
sin `tenant_id` y sin RLS, y esa excepcion tiene que ser visible.

Sin mocks (regla dura 8).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from .soporte import agencia_con_sucursal, sesion_de_propietario

pytestmark = pytest.mark.integration

TABLAS_CON_RLS = ("users", "user_branches")


@pytest.fixture
async def agencia(base_migrada: None) -> tuple[uuid.UUID, uuid.UUID]:
    return await agencia_con_sucursal()


async def _alta(
    tenant: uuid.UUID, email: str, *, identificador: uuid.UUID | None = None
) -> uuid.UUID:
    """Una persona, escrita con el rol PROPIETARIO.

    Es andamiaje: lo que se prueba son las constraints de la tabla, no el
    servicio que todavia no existe.
    """
    uid = identificador or uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Persona', 'salesperson', 'active')"
            ),
            {"id": uid, "t": tenant, "e": email},
        )
    return uid


# ── 1.2 · La excepcion de `super_admins` es visible ──────────────────────────


async def test_super_admins_no_tiene_tenant_id_ni_politica(base_migrada: None) -> None:
    """`ADR-017` §2. Es la unica tabla de identidad fuera del aislamiento, y por
    eso su ausencia de RLS tiene que estar afirmada en algun lado."""
    async with sesion_de_propietario() as sesion:
        columnas = set(
            (
                await sesion.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'super_admins'"
                    )
                )
            )
            .scalars()
            .all()
        )
        rls = await sesion.scalar(
            text("SELECT relrowsecurity FROM pg_class WHERE relname = 'super_admins'")
        )

    assert "tenant_id" not in columnas
    assert rls is False


@pytest.mark.parametrize("tabla", TABLAS_CON_RLS)
async def test_las_tablas_de_identidad_con_tenant_tienen_politica_y_force(
    base_migrada: None, tabla: str
) -> None:
    """`FORCE` y no solo `ENABLE`: sin el, las politicas no se aplican al DUEÑO
    de la tabla — `pg_policies` la lista, cualquier auditoria la da por buena, y
    no filtra nada para el."""
    async with sesion_de_propietario() as sesion:
        fila = (
            await sesion.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity, "
                    "(SELECT count(*) FROM pg_policies p WHERE p.tablename = c.relname) "
                    "FROM pg_class c WHERE c.relname = :t"
                ),
                {"t": tabla},
            )
        ).one()

    habilitada, forzada, politicas = fila
    assert habilitada is True
    assert forzada is True
    assert politicas == 1


# ── 1.4 · `users.tenant_id` es NOT NULL ──────────────────────────────────────


async def test_una_persona_sin_agencia_se_rechaza(base_migrada: None) -> None:
    """La consecuencia practica de que `super_admin` viva aparte (`D-3`).

    Si fuera un valor del enum, esta columna tendria que ser nullable y **toda**
    consulta del sistema tendria que contemplar el caso "usuario sin tenant".
    """
    async with sesion_de_propietario() as sesion:
        with pytest.raises(Exception, match="null value|not-null|NotNullViolation"):
            await sesion.execute(
                text(
                    "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                    "VALUES (:id, NULL, 'x@y.test', 'X', 'manager', 'active')"
                ),
                {"id": uuid.uuid4()},
            )


async def test_el_enum_de_roles_tiene_exactamente_los_tres(base_migrada: None) -> None:
    """`ADR-017` §1 cierra `IN-01`. `super_admin` NO es un cuarto valor."""
    async with sesion_de_propietario() as sesion:
        valores = set(
            (
                await sesion.execute(
                    text(
                        "SELECT enumlabel FROM pg_enum e JOIN pg_type t "
                        "ON t.oid = e.enumtypid WHERE t.typname = 'user_role_enum'"
                    )
                )
            )
            .scalars()
            .all()
        )
    assert valores == {"manager", "salesperson", "admin_staff"}


# ── 1.6 · Unicidad del email: por agencia e insensible a mayusculas ──────────


async def test_el_mismo_email_en_dos_agencias_se_acepta(base_migrada: None) -> None:
    """Un contador que atiende a dos agencias es una persona en cada una."""
    una, _ = await agencia_con_sucursal()
    otra, _ = await agencia_con_sucursal()

    await _alta(una, "contador@estudio.test")
    await _alta(otra, "contador@estudio.test")  # no explota: son agencias distintas


async def test_el_mismo_email_repetido_en_la_agencia_se_rechaza(
    agencia: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, _ = agencia
    await _alta(tenant, "ana@demo.test")

    with pytest.raises(Exception, match="duplicate key|UniqueViolation"):
        await _alta(tenant, "ana@demo.test")


async def test_el_email_no_distingue_mayusculas_dentro_de_la_agencia(
    agencia: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """`Ana@x.com` y `ana@x.com` son la misma persona.

    Sin `lower()` en el indice, dos filas distintas comparten identidad ante
    Keycloak, que si normaliza — y ahi el espejo empieza a mentir.
    """
    tenant, _ = agencia
    await _alta(tenant, "Ana@demo.test")

    with pytest.raises(Exception, match="duplicate key|UniqueViolation"):
        await _alta(tenant, "ana@demo.test")


async def test_dar_de_baja_libera_el_email(
    agencia: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """El indice es parcial por `deleted_at`. Si no lo fuera, el email de alguien
    que se fue quedaria tomado para siempre y la reincorporacion seria imposible.
    """
    tenant, _ = agencia
    uid = await _alta(tenant, "vuelve@demo.test")

    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text("UPDATE users SET deleted_at = now() WHERE id = :id"), {"id": uid}
        )

    await _alta(tenant, "vuelve@demo.test")  # el lugar quedo libre


# ── 1.8 · La tabla de union ──────────────────────────────────────────────────


async def test_no_se_puede_vincular_una_persona_con_la_sucursal_de_otra_agencia(
    base_migrada: None,
) -> None:
    """Las FK compuestas contra `(id, tenant_id)` son lo que paga la redundancia
    de `tenant_id` en la tabla de union. Sin ellas la columna podria decir
    cualquier cosa y la politica RLS aislaria por un dato inventado."""
    una, sucursal_de_una = await agencia_con_sucursal()
    otra, _ = await agencia_con_sucursal()
    ajena = await _alta(otra, "ajena@demo.test")

    async with sesion_de_propietario() as sesion:
        with pytest.raises(Exception, match="violates foreign key|ForeignKeyViolation"):
            await sesion.execute(
                text(
                    "INSERT INTO user_branches (user_id, branch_id, tenant_id) "
                    "VALUES (:u, :b, :t)"
                ),
                {"u": ajena, "b": sucursal_de_una, "t": otra},
            )


async def test_una_persona_tiene_una_sola_sucursal_principal(
    agencia: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal = agencia
    uid = await _alta(tenant, "doble@demo.test")

    async with sesion_de_propietario() as sesion:
        segunda = uuid.uuid4()
        await sesion.execute(
            text(
                "INSERT INTO branches (id, tenant_id, name, city, province) "
                "VALUES (:id, :t, 'Segunda', 'Mendoza', 'Mendoza')"
            ),
            {"id": segunda, "t": tenant},
        )
        await sesion.execute(
            text(
                "INSERT INTO user_branches (user_id, branch_id, tenant_id, is_primary) "
                "VALUES (:u, :b, :t, true)"
            ),
            {"u": uid, "b": sucursal, "t": tenant},
        )

        with pytest.raises(Exception, match="duplicate key|UniqueViolation"):
            await sesion.execute(
                text(
                    "INSERT INTO user_branches (user_id, branch_id, tenant_id, is_primary) "
                    "VALUES (:u, :b, :t, true)"
                ),
                {"u": uid, "b": segunda, "t": tenant},
            )
