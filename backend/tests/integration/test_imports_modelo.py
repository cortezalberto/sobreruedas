"""El modelo `Import` contra la tabla real — C-17, migracion `012`.

POR QUE UN TEST SOLO PARA MAPEAR UNA TABLA
────────────────────────────────────────────
Por un error concreto que ya paso en este proyecto y no da la cara al escribir:
un `ENUM(name=..., create_type=False)` **sin sus valores** guarda perfecto y
**revienta al LEER** (`'diesel' is not among the defined enum values`). Un test
que solo inserta pasa; hay que volver a traer la fila.

Los dos enums de esta migracion —`import_status_enum` e `import_type_enum`— son
nuevos, asi que el riesgo esta abierto de nuevo. Se cierra leyendo.

Y de paso verifica lo que la migracion promete y todavia nadie ejercita: que
`imports` tiene politica RLS de verdad.

Sin mocks de base de datos (regla dura 8).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.db.session import sesion_de_tenant
from app.modules.stock.importacion_modelo import (
    TERMINALES,
    EstadoDeImportacion,
    Import,
    ImportacionSalida,
)

from .soporte import DSN_APLICACION, sesion_de_propietario

pytestmark = pytest.mark.integration


async def _agencia() -> uuid.UUID:
    tenant_id = uuid.uuid4()
    async with sesion_de_propietario() as sesion:
        await sesion.execute(
            text(
                "INSERT INTO tenants (id, name, slug, cuit, billing_email, status) "
                "VALUES (:id, 'Agencia', :s, :c, 'f@example.com', 'active')"
            ),
            {
                "id": tenant_id,
                "s": f"ag-{tenant_id.hex[:8]}",
                "c": f"30{tenant_id.int % 10**9:09d}0"[:11],
            },
        )
    return tenant_id


async def test_una_importacion_se_escribe_y_SE_VUELVE_A_LEER(base_migrada: None) -> None:
    """Lo segundo es lo que importa: sin los valores en el ENUM, esto falla."""
    tenant_id = await _agencia()

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        corrida = Import(
            tenant_id=tenant_id,
            source_filename="stock-agosto.csv",
            status=EstadoDeImportacion.VALIDANDO.value,
            total_rows=120,
            valid_rows=118,
            error_rows=2,
            errors=[{"fila": 7, "columna": "anio", "mensaje": "no es un numero entero"}],
        )
        sesion.add(corrida)
        await sesion.flush()
        corrida_id = corrida.id
        sesion.expunge_all()

        traida = (await sesion.execute(select(Import).where(Import.id == corrida_id))).scalar_one()

    assert traida.status == EstadoDeImportacion.VALIDANDO.value
    assert traida.type == "stock"
    assert traida.errors[0]["columna"] == "anio"


async def test_los_seis_estados_del_flujo_4_entran_en_la_columna(base_migrada: None) -> None:
    """El enum de Python y el de PostgreSQL tienen que decir lo mismo.

    Si divergen, el sintoma no es un error de tipos: es un `InvalidTextRepresentation`
    en produccion la primera vez que una importacion llega al estado que falta.
    """
    tenant_id = await _agencia()

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        for estado in EstadoDeImportacion:
            sesion.add(
                Import(
                    tenant_id=tenant_id,
                    source_filename=f"{estado.value}.csv",
                    status=estado.value,
                )
            )
        await sesion.flush()

        guardados = (await sesion.execute(select(Import.status))).scalars().all()

    assert set(guardados) == {e.value for e in EstadoDeImportacion}


async def test_una_importacion_de_otra_agencia_no_se_ve(base_migrada: None) -> None:
    """La politica RLS de la migracion `012`, ejercitada.

    No es formalidad: `errors` guarda dominios, chasis y precios de las filas que
    fallaron — o sea, el inventario de la agencia tal como lo estaba cargando.
    """
    tenant_a, tenant_b = await _agencia(), await _agencia()

    async with sesion_de_tenant(tenant_a, dsn=DSN_APLICACION) as sesion:
        sesion.add(Import(tenant_id=tenant_a, source_filename="privado.csv"))
        await sesion.flush()

    async with sesion_de_tenant(tenant_b, dsn=DSN_APLICACION) as sesion:
        ajenas = (await sesion.execute(select(Import))).scalars().all()

    assert ajenas == []


async def test_el_polling_para_solo_en_los_dos_estados_terminales() -> None:
    """`TERMINALES` es el contrato del `Flujo 4`, paso 5.

    Se afirma por comprension y no repitiendo el conjunto: escribir
    `{COMPLETADA, FALLIDA}` de nuevo probaria que copie bien, no que la regla
    sea la correcta. Lo que se afirma es *"terminal = ya no avanza"*.
    """
    en_curso = {
        EstadoDeImportacion.PENDIENTE,
        EstadoDeImportacion.PARSEANDO,
        EstadoDeImportacion.VALIDANDO,
        EstadoDeImportacion.IMPORTANDO,
    }

    assert TERMINALES == set(EstadoDeImportacion) - en_curso


async def test_la_salida_no_filtra_columnas_que_no_declara(base_migrada: None) -> None:
    """`ImportacionSalida` es lista blanca, no volcado del modelo.

    `created_by`, `updated_at` y `deleted_at` estan en la tabla y NO tienen por
    que viajar: el primero es un id de usuario y los otros dos son contabilidad
    interna de la fila.
    """
    tenant_id = await _agencia()

    async with sesion_de_tenant(tenant_id, dsn=DSN_APLICACION) as sesion:
        corrida = Import(tenant_id=tenant_id, source_filename="x.csv", created_by=uuid.uuid4())
        sesion.add(corrida)
        await sesion.flush()

        salida = ImportacionSalida.model_validate(corrida)

    campos = salida.model_dump()
    assert "created_by" not in campos
    assert "deleted_at" not in campos
    assert campos["source_filename"] == "x.csv"
