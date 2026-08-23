"""`vehicle_status_history` sobre base real — C-14, `T-084`.

QUE SE PRUEBA EN CADA BLOQUE
──────────────────────────────
  1. La migracion `019`: forma de la tabla, las tres capas de aislamiento, el
     append-only por privilegio (no por confianza) y la FK compuesta de
     `changed_by`.
  2. `historial.py`: `registrar_transicion` y el repositorio de lectura.

Sin mocks de base de datos (regla dura 8).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.db.session import sesion_de_tenant
from app.modules.stock.historial import (
    HistorialRepository,
    VehicleStatusHistory,
    registrar_transicion,
)
from app.modules.stock.models import Vehicle
from app.modules.stock.schemas import EstadoDeVehiculo

from .soporte import DSN_APLICACION, agencia_con_sucursal, sesion_de_propietario

pytestmark = pytest.mark.integration

# SQLSTATE 42501 = insufficient_privilege. Mismo criterio que
# `test_rol_de_conexion.py`: se compara el CODIGO, no el texto del mensaje,
# porque PostgreSQL lo traduce segun `lc_messages`.
PERMISO_DENEGADO = "42501"


def sqlstate(error: DBAPIError) -> str | None:
    return getattr(error.orig, "sqlstate", None)


@pytest.fixture
async def escenario(base_migrada: None) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Un tenant con sucursal y UN vehiculo real, para anclar la FK NOT NULL.

    El vehiculo se inserta con el ORM directo y no con `StockService`: este
    archivo prueba la tabla y `historial.py`, que son mas bajos en la pila que
    el servicio (bloque 3 los conecta).
    """
    tenant_id, branch_id = await agencia_con_sucursal()
    async with sesion_de_propietario() as sesion:
        marca, modelo = (
            await sesion.execute(text("SELECT brand_id, id FROM vehicle_models LIMIT 1"))
        ).one()

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        vehiculo = Vehicle(
            tenant_id=tenant_id,
            branch_id=branch_id,
            brand_id=uuid.UUID(str(marca)),
            model_id=uuid.UUID(str(modelo)),
            year=2020,
            mileage_km=10_000,
            color="Blanco",
            fuel_type="diesel",
            transmission="manual",
            body_type="pickup",
            price_ars=Decimal("15000000.00"),
            domain_plate="AB123CD",
        )
        sesion.add(vehiculo)
        await sesion.flush()
        vehiculo_id = vehiculo.id

    return tenant_id, branch_id, vehiculo_id


# ── 1.1 · La forma de la tabla ───────────────────────────────────────────────

COLUMNAS_ESPERADAS = {
    "id",
    "tenant_id",
    "vehicle_id",
    "from_status",
    "to_status",
    "changed_by",
    "reason",
    "changed_at",
}


async def test_la_tabla_tiene_las_ocho_columnas_de_la_spec(base_migrada: None) -> None:
    """`spec-tecnica` §3.4, `design.md` D-2."""
    async with sesion_de_propietario() as sesion:
        columnas = (
            (
                await sesion.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'vehicle_status_history'"
                    )
                )
            )
            .scalars()
            .all()
        )
    assert set(columnas) == COLUMNAS_ESPERADAS


async def test_changed_at_es_timestamptz_y_no_timestamp_pelado(base_migrada: None) -> None:
    async with sesion_de_propietario() as sesion:
        tipo = await sesion.scalar(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'vehicle_status_history' AND column_name = 'changed_at'"
            )
        )
    assert tipo == "timestamp with time zone"


async def test_from_status_y_to_status_usan_el_enum_de_vehiculos(base_migrada: None) -> None:
    """El mismo `vehicle_status_enum` que ya creo la `011`, no uno nuevo."""
    async with sesion_de_propietario() as sesion:
        filas = (
            await sesion.execute(
                text(
                    "SELECT column_name, udt_name FROM information_schema.columns "
                    "WHERE table_name = 'vehicle_status_history' "
                    "  AND column_name IN ('from_status', 'to_status')"
                )
            )
        ).all()
    tipos = {str(nombre): str(tipo) for nombre, tipo in filas}
    assert tipos == {"from_status": "vehicle_status_enum", "to_status": "vehicle_status_enum"}


# ── 1.2 · Las tres capas ─────────────────────────────────────────────────────


async def test_tenant_id_es_not_null(base_migrada: None) -> None:
    async with sesion_de_propietario() as sesion:
        nulo = await sesion.scalar(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'vehicle_status_history' AND column_name = 'tenant_id'"
            )
        )
    assert nulo == "NO"


async def test_la_tabla_tiene_politica_rls_y_force(base_migrada: None) -> None:
    """`FORCE` y no solo `ENABLE`: sin el, la politica no aplica al DUEÑO de la
    tabla, `pg_policies` la lista igual, y una auditoria la da por buena."""
    async with sesion_de_propietario() as sesion:
        fila = (
            await sesion.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity, "
                    "(SELECT count(*) FROM pg_policies p WHERE p.tablename = c.relname) "
                    "FROM pg_class c WHERE c.relname = 'vehicle_status_history'"
                )
            )
        ).one()
    habilitada, forzada, politicas = fila
    assert habilitada is True
    assert forzada is True
    assert politicas == 1


# ── 1.3 / 1.4 · Append-only por PRIVILEGIO, con su contrapeso ────────────────


async def test_el_rol_de_aplicacion_tiene_select_e_insert_y_no_update_ni_delete(
    base_migrada: None,
) -> None:
    """Sobre el PRIVILEGIO, no sobre si el `REVOKE` corrio.

    Probar que la migracion ejecuto el `REVOKE` no prueba que la tabla haya
    quedado cerrada — hay que consultar el catalogo real.
    """
    async with sesion_de_propietario() as sesion:
        privilegios = set(
            (
                await sesion.execute(
                    text(
                        "SELECT privilege_type FROM information_schema.role_table_grants "
                        "WHERE table_name = 'vehicle_status_history' AND grantee <> current_user"
                    )
                )
            )
            .scalars()
            .all()
        )
    assert {"SELECT", "INSERT"} <= privilegios
    assert "UPDATE" not in privilegios
    assert "DELETE" not in privilegios


async def test_un_update_real_falla_por_permiso_y_un_insert_funciona(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """El contrapeso de arriba: sin el, un test que verificara el privilegio de
    una tabla que nadie puede ni LEER pasaria igual de bien."""
    tenant_id, _, vehiculo_id = escenario
    fila_id = uuid.uuid4()

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        await sesion.execute(
            text(
                "INSERT INTO vehicle_status_history "
                "(id, tenant_id, vehicle_id, from_status, to_status, changed_at) "
                "VALUES (:id, :t, :v, NULL, 'in_preparation', now())"
            ),
            {"id": fila_id, "t": tenant_id, "v": vehiculo_id},
        )

    with pytest.raises(DBAPIError) as fallo:
        async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
            await sesion.execute(
                text("UPDATE vehicle_status_history SET reason = 'manipulado' WHERE id = :id"),
                {"id": fila_id},
            )

    assert sqlstate(fallo.value) == PERMISO_DENEGADO


# ── 1.5 · La FK compuesta de `changed_by` ────────────────────────────────────


async def test_changed_by_de_otra_agencia_se_rechaza(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    tenant_id, _, vehiculo_id = escenario
    otro_tenant, _ = await agencia_con_sucursal()
    usuario_ajeno = uuid.uuid4()

    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Ajeno', 'salesperson', 'active')"
            ),
            {"id": usuario_ajeno, "t": otro_tenant, "e": f"{usuario_ajeno}@example.com"},
        )

    with pytest.raises(IntegrityError):
        async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
            await sesion.execute(
                text(
                    "INSERT INTO vehicle_status_history "
                    "(id, tenant_id, vehicle_id, to_status, changed_by, changed_at) "
                    "VALUES (:id, :t, :v, 'in_preparation', :u, now())"
                ),
                {"id": uuid.uuid4(), "t": tenant_id, "v": vehiculo_id, "u": usuario_ajeno},
            )


async def test_changed_by_nulo_se_acepta(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """`MATCH SIMPLE`: una FK compuesta con alguna columna en NULL no se
    verifica, asi que la transicion automatica pasa sin autor."""
    tenant_id, _, vehiculo_id = escenario

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        await sesion.execute(
            text(
                "INSERT INTO vehicle_status_history "
                "(id, tenant_id, vehicle_id, to_status, changed_by, changed_at) "
                "VALUES (:id, :t, :v, 'in_preparation', NULL, now())"
            ),
            {"id": uuid.uuid4(), "t": tenant_id, "v": vehiculo_id},
        )


# ── 2.3 · `registrar_transicion` agrega sin flush propio (el caso COMPLETO) ──


async def test_registrar_transicion_agrega_la_fila_sin_hacer_flush(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """`D-5`: agrega a la sesion que recibe y devuelve. El `flush` lo hace quien
    llama, cuando ya tiene el `id` del vehiculo.

    Es el caso COMPLETO —autor y razon presentes—: los dos casos de 2.6
    (autor ausente, razon ausente) tienen que verse DISTINTOS de este.
    """
    tenant_id, _, vehiculo_id = escenario
    autor = uuid.uuid4()

    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Autora', 'manager', 'active')"
            ),
            {"id": autor, "t": tenant_id, "e": f"{autor}@example.com"},
        )

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        registrar_transicion(
            sesion,
            tenant_id=tenant_id,
            vehiculo_id=vehiculo_id,
            desde=EstadoDeVehiculo.EN_PREPARACION,
            hasta=EstadoDeVehiculo.DISPONIBLE,
            razon="listo para exhibir",
            autor=autor,
        )
        # No hubo flush todavia y la fila ya esta en la identity map de la
        # sesion: es lo que demuestra que `registrar_transicion` NO es async y
        # no toca la red por su cuenta.
        pendientes = [obj for obj in sesion.new if isinstance(obj, VehicleStatusHistory)]
        assert len(pendientes) == 1

        await sesion.flush()

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        filas = await HistorialRepository(sesion, tenant_id).listar_historial(vehiculo_id)
    assert len(filas) == 1
    assert filas[0].from_status == EstadoDeVehiculo.EN_PREPARACION.value
    assert filas[0].to_status == EstadoDeVehiculo.DISPONIBLE.value
    assert filas[0].reason == "listo para exhibir"
    assert filas[0].changed_by == autor


# ── 2.4 · Aislamiento en la lectura ──────────────────────────────────────────


async def test_listar_historial_de_un_vehiculo_ajeno_devuelve_vacio(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """El filtro EXPLICITO de tenant_id esta en la consulta, ademas de RLS."""
    tenant_id, _, vehiculo_id = escenario

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        registrar_transicion(
            sesion,
            tenant_id=tenant_id,
            vehiculo_id=vehiculo_id,
            desde=None,
            hasta=EstadoDeVehiculo.EN_PREPARACION,
            razon=None,
            autor=None,
        )
        await sesion.flush()

    otro_tenant = uuid.uuid4()
    async with sesion_de_tenant(otro_tenant, dsn=DSN_APLICACION) as sesion:
        filas = await HistorialRepository(sesion, otro_tenant).listar_historial(vehiculo_id)

    assert filas == []


# ── 2.5 / 2.6 · Orden y triangulacion (autor / razon ausentes) ───────────────


async def test_el_orden_es_changed_at_desc_y_no_pagina(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """Dos TRANSACCIONES separadas, como en produccion.

    `now()` de PostgreSQL devuelve el instante de INICIO de la transaccion, no
    el de cada sentencia. Dos filas escritas en la misma transaccion
    comparten `changed_at` exactamente — y ahi el segundo criterio de orden
    (`id DESC`, un UUID aleatorio) no reconstruye la secuencia real. Eso nunca
    pasa en produccion: cada peticion abre su propia transaccion
    (`sesion_de_tenant` por request, `db/dependencias.py`), asi que dos
    transiciones del mismo vehiculo SIEMPRE llegan en transacciones distintas.
    """
    tenant_id, _, vehiculo_id = escenario

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        registrar_transicion(
            sesion,
            tenant_id=tenant_id,
            vehiculo_id=vehiculo_id,
            desde=None,
            hasta=EstadoDeVehiculo.EN_PREPARACION,
            razon=None,
            autor=None,
        )
        await sesion.flush()

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        registrar_transicion(
            sesion,
            tenant_id=tenant_id,
            vehiculo_id=vehiculo_id,
            desde=EstadoDeVehiculo.EN_PREPARACION,
            hasta=EstadoDeVehiculo.DISPONIBLE,
            razon="listo para exhibir",
            autor=None,
        )
        await sesion.flush()

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        filas = await HistorialRepository(sesion, tenant_id).listar_historial(vehiculo_id)

    assert [f.to_status for f in filas] == [
        EstadoDeVehiculo.DISPONIBLE.value,
        EstadoDeVehiculo.EN_PREPARACION.value,
    ]


async def test_registrar_transicion_con_autor_ausente(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """Triangulacion: `autor=None` es transicion automatica, no un error."""
    tenant_id, _, vehiculo_id = escenario

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        registrar_transicion(
            sesion,
            tenant_id=tenant_id,
            vehiculo_id=vehiculo_id,
            desde=None,
            hasta=EstadoDeVehiculo.EN_PREPARACION,
            razon=None,
            autor=None,
        )
        await sesion.flush()

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        (fila,) = await HistorialRepository(sesion, tenant_id).listar_historial(vehiculo_id)
    assert fila.changed_by is None


async def test_registrar_transicion_con_razon_ausente(
    escenario: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    """Tercer caso: `razon=None` no puede caer en el mismo camino que el
    completo — una transicion sin motivo es legitima fuera de vender."""
    tenant_id, _, vehiculo_id = escenario
    autor = uuid.uuid4()

    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO users (id, tenant_id, email, full_name, role, status) "
                "VALUES (:id, :t, :e, 'Autora', 'manager', 'active')"
            ),
            {"id": autor, "t": tenant_id, "e": f"{autor}@example.com"},
        )

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        registrar_transicion(
            sesion,
            tenant_id=tenant_id,
            vehiculo_id=vehiculo_id,
            desde=None,
            hasta=EstadoDeVehiculo.EN_PREPARACION,
            razon=None,
            autor=autor,
        )
        await sesion.flush()

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        (fila,) = await HistorialRepository(sesion, tenant_id).listar_historial(vehiculo_id)
    assert fila.reason is None
    assert fila.changed_by is not None
