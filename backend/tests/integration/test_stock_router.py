"""Los endpoints de stock, con datos de una agencia — C-14 / C-15.

ES EL PRIMER ROUTER DEL SISTEMA QUE DEVUELVE DATOS DE UN TENANT, asi que lo que
se prueba acá no es el CRUD: es el aislamiento, sobre HTTP y contra PostgreSQL
real.

La afirmacion central es una sola y tiene que fallar ruidosamente si alguna vez
deja de ser cierta: **con el token de la agencia A no se ve, ni se toca, nada de
la agencia B** — aunque se pida por su id exacto.

Sin mocks de base de datos (regla dura 8).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import auth
from app.main import create_app
from app.modules.stock.schemas import (
    Carroceria,
    Combustible,
    EstadoDeVehiculo,
    Transmision,
)

from ..emisor_de_tokens import EmisorDePrueba
from .soporte import (
    DSN_APLICACION,
    agencia_con_sucursal,
    reponer_entorno,
    sesion_de_propietario,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def proveedor() -> EmisorDePrueba:
    return EmisorDePrueba()


@pytest.fixture
def cliente(
    monkeypatch: pytest.MonkeyPatch, proveedor: EmisorDePrueba, base_migrada: None
) -> Iterator[TestClient]:
    reponer_entorno(monkeypatch, dsn=DSN_APLICACION)

    async def traer() -> dict[str, Any]:
        return proveedor.jwks

    monkeypatch.setattr(
        auth, "claves_del_proveedor", lambda: auth.ClavesDelProveedor(url="x", traer=traer)
    )
    monkeypatch.setattr(auth, "emisor_esperado", lambda: proveedor.emisor)

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
async def modelo_del_catalogo() -> tuple[uuid.UUID, uuid.UUID]:
    """Una marca y un modelo REALES del catalogo sembrado.

    `vehicles` tiene FK a `vehicle_brands` y `vehicle_models`, asi que un UUID
    inventado no entra. Se toman del seed de la migracion `009` en vez de crear
    filas nuevas: el catalogo es de solo lectura para la aplicacion, y crearlas
    exigiria el rol propietario para algo que ya existe.
    """
    async with sesion_de_propietario() as sesion:
        fila = (
            await sesion.execute(
                text("SELECT brand_id, id FROM vehicle_models ORDER BY name LIMIT 1")
            )
        ).one()
    return uuid.UUID(str(fila[0])), uuid.UUID(str(fila[1]))


@pytest.fixture
async def agencia() -> tuple[uuid.UUID, uuid.UUID]:
    return await agencia_con_sucursal()


@pytest.fixture
async def otra_agencia() -> tuple[uuid.UUID, uuid.UUID]:
    return await agencia_con_sucursal()


def _cabecera(proveedor: EmisorDePrueba, tenant: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {proveedor.firmar(tenant_id=tenant)}"}


def _cuerpo(
    branch_id: uuid.UUID, catalogo: tuple[uuid.UUID, uuid.UUID], **extra: Any
) -> dict[str, Any]:
    marca, modelo = catalogo
    return {
        "branch_id": str(branch_id),
        "brand_id": str(marca),
        "model_id": str(modelo),
        "year": 2021,
        "mileage_km": 30000,
        "color": "Blanco",
        "fuel_type": "diesel",
        "transmission": "manual",
        "body_type": "pickup",
        "price_ars": "25000000.00",
        "chassis_number": "8AWZZZ377VA123456",
        **extra,
    }


# ── Lo que este archivo vino a probar ───────────────────────────────────────


def test_una_agencia_no_ve_el_stock_de_otra(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    otra_agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """La afirmacion central, sobre HTTP.

    Se cargan dos vehiculos con dos tokens distintos y cada uno ve el suyo. Si
    el listado devolviera los dos, el aislamiento no existe.
    """
    tenant_a, sucursal_a = agencia
    tenant_b, sucursal_b = otra_agencia

    cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal_a, modelo_del_catalogo, domain_plate="AA111AA"),
        headers=_cabecera(proveedor, tenant_a),
    )
    cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal_b,
            modelo_del_catalogo,
            domain_plate="BB222BB",
            chassis_number="9BWZZZ377VA654321",
        ),
        headers=_cabecera(proveedor, tenant_b),
    )

    de_a = cliente.get("/api/v1/vehicles", headers=_cabecera(proveedor, tenant_a)).json()
    de_b = cliente.get("/api/v1/vehicles", headers=_cabecera(proveedor, tenant_b)).json()

    assert [v["domain_plate"] for v in de_a] == ["AA111AA"]
    assert [v["domain_plate"] for v in de_b] == ["BB222BB"]


def test_pedir_por_id_un_vehiculo_ajeno_da_404(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    otra_agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """404 y NO 403.

    Son dos respuestas distintas y la diferencia es una fuga: un 403 le
    confirmaria al tenant A que ese id existe en otra agencia. El 404 dice lo
    unico que A tiene derecho a saber — para el, ese vehiculo no existe.
    """
    tenant_a, _ = agencia
    tenant_b, sucursal_b = otra_agencia

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal_b, modelo_del_catalogo, domain_plate="CC333CC"),
        headers=_cabecera(proveedor, tenant_b),
    ).json()

    ajeno = cliente.get(f"/api/v1/vehicles/{creado['id']}", headers=_cabecera(proveedor, tenant_a))

    assert ajeno.status_code == 404


def test_no_se_puede_dar_de_baja_un_vehiculo_ajeno(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    otra_agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """El aislamiento tambien es de ESCRITURA, no solo de lectura."""
    tenant_a, _ = agencia
    tenant_b, sucursal_b = otra_agencia

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal_b, modelo_del_catalogo, domain_plate="DD444DD"),
        headers=_cabecera(proveedor, tenant_b),
    ).json()

    borrado = cliente.delete(
        f"/api/v1/vehicles/{creado['id']}", headers=_cabecera(proveedor, tenant_a)
    )

    assert borrado.status_code == 404
    # Y sigue vivo para su dueño.
    assert (
        cliente.get(
            f"/api/v1/vehicles/{creado['id']}", headers=_cabecera(proveedor, tenant_b)
        ).status_code
        == 200
    )


def test_sin_token_no_se_lista_nada(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/vehicles").status_code == 401


# ── Reglas de negocio sobre el endpoint ─────────────────────────────────────


def test_un_vehiculo_nace_en_preparacion(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """`RN-ST-04`. El cliente no elige el estado inicial."""
    tenant, sucursal = agencia

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="EE555EE"),
        headers=_cabecera(proveedor, tenant),
    )

    assert creado.status_code == 201
    assert creado.json()["status"] == "in_preparation"


def test_el_costo_de_adquisicion_no_sale_en_la_respuesta(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """`RN-ST-12`, y hoy con denegar-por-defecto.

    Se manda el costo al crear y NO vuelve, porque sin `rbac.py` no se puede
    distinguir quien pregunta. Cuando existan los roles, `manager` y
    `admin_staff` van a recibirlo por `VehiculoSalidaConCosto`.
    """
    tenant, sucursal = agencia

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal,
            modelo_del_catalogo,
            domain_plate="FF666FF",
            acquisition_cost_ars="19000000.00",
        ),
        headers=_cabecera(proveedor, tenant),
    ).json()

    assert "acquisition_cost_ars" not in creado


def test_el_dominio_duplicado_se_rechaza(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """`RN-ST-01`, dentro del mismo tenant."""
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)

    cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="GG777GG"),
        headers=cabecera,
    )
    repetido = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal,
            modelo_del_catalogo,
            domain_plate="GG777GG",
            chassis_number="1BWZZZ377VA111111",
        ),
        headers=cabecera,
    )

    assert repetido.status_code == 422


def test_el_mismo_dominio_en_dos_agencias_no_choca(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    otra_agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """La unicidad es POR TENANT (`RN-ST-01`), no global.

    Dos agencias pueden tener cargado el mismo dominio: pasa de verdad cuando un
    auto se vende de una a otra.
    """
    tenant_a, sucursal_a = agencia
    tenant_b, sucursal_b = otra_agencia

    uno = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal_a, modelo_del_catalogo, domain_plate="HH888HH"),
        headers=_cabecera(proveedor, tenant_a),
    )
    dos = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal_b,
            modelo_del_catalogo,
            domain_plate="HH888HH",
            chassis_number="2BWZZZ377VA222222",
        ),
        headers=_cabecera(proveedor, tenant_b),
    )

    assert uno.status_code == 201
    assert dos.status_code == 201


def test_una_transicion_prohibida_se_rechaza(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """`RN-ST-05`: de `in_preparation` no se pasa a `sold`."""
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="II999II"),
        headers=cabecera,
    ).json()

    rechazo = cliente.post(
        f"/api/v1/vehicles/{creado['id']}/status",
        json={"status": "sold", "reason": "venta directa"},
        headers=cabecera,
    )

    assert rechazo.status_code == 422


def test_la_transicion_permitida_se_aplica(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="JJ111JJ"),
        headers=cabecera,
    ).json()

    cambio = cliente.post(
        f"/api/v1/vehicles/{creado['id']}/status", json={"status": "available"}, headers=cabecera
    )

    assert cambio.status_code == 200
    assert cambio.json()["status"] == "available"


def test_dar_de_baja_es_borrado_logico(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Regla dura 3: la fila sobrevive, deja de aparecer en el listado."""
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="KK222KK"),
        headers=cabecera,
    ).json()

    assert cliente.delete(f"/api/v1/vehicles/{creado['id']}", headers=cabecera).status_code == 204
    assert cliente.get(f"/api/v1/vehicles/{creado['id']}", headers=cabecera).status_code == 404
    assert creado["id"] not in [
        v["id"] for v in cliente.get("/api/v1/vehicles", headers=cabecera).json()
    ]


def test_el_filtro_por_estado_acota(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    tenant, sucursal = agencia
    cabecera = _cabecera(proveedor, tenant)

    primero = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(sucursal, modelo_del_catalogo, domain_plate="LL333LL"),
        headers=cabecera,
    ).json()
    cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal,
            modelo_del_catalogo,
            domain_plate="MM444MM",
            chassis_number="3BWZZZ377VA333333",
        ),
        headers=cabecera,
    )
    cliente.post(
        f"/api/v1/vehicles/{primero['id']}/status", json={"status": "available"}, headers=cabecera
    )

    disponibles = cliente.get(
        "/api/v1/vehicles", params={"status": "available"}, headers=cabecera
    ).json()

    assert [v["id"] for v in disponibles] == [primero["id"]]


def test_el_precio_viaja_como_decimal_exacto(
    cliente: TestClient,
    proveedor: EmisorDePrueba,
    agencia: tuple[uuid.UUID, uuid.UUID],
    modelo_del_catalogo: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Un precio que se redondea solo es un problema de facturacion."""
    tenant, sucursal = agencia

    creado = cliente.post(
        "/api/v1/vehicles",
        json=_cuerpo(
            sucursal, modelo_del_catalogo, domain_plate="NN555NN", price_ars="18500000.10"
        ),
        headers=_cabecera(proveedor, tenant),
    ).json()

    assert Decimal(str(creado["price_ars"])) == Decimal("18500000.10")


@pytest.mark.parametrize(
    ("tipo", "valores"),
    [
        ("vehicle_status_enum", [e.value for e in EstadoDeVehiculo]),
        ("fuel_type_enum", [e.value for e in Combustible]),
        ("transmission_enum", [e.value for e in Transmision]),
        ("body_type_enum", [e.value for e in Carroceria]),
    ],
)
async def test_los_enum_de_la_base_coinciden_con_los_del_codigo(
    base_migrada: None, tipo: str, valores: list[str]
) -> None:
    """La deriva que este test existe para atajar.

    Los valores viven en dos lugares que no se hablan: la migracion —congelada—
    y los `StrEnum` de `schemas.py`, que usan el modelo y el contrato. Agregar un
    estado en el codigo sin migrar, o al reves, no falla al arrancar: falla la
    primera vez que alguien manda ese valor, en produccion.

    Se comparan como CONJUNTOS y no como listas: el orden de las etiquetas en
    PostgreSQL importa para comparar, no para ser correctas.
    """
    async with sesion_de_propietario() as sesion:
        etiquetas = (
            (
                await sesion.execute(
                    text(
                        "SELECT e.enumlabel FROM pg_enum e "
                        "JOIN pg_type t ON t.oid = e.enumtypid WHERE t.typname = :tipo"
                    ),
                    {"tipo": tipo},
                )
            )
            .scalars()
            .all()
        )

    assert set(etiquetas) == set(valores), (
        f"el enum '{tipo}' de PostgreSQL no coincide con el del codigo. "
        "Si agregaste un valor, falta la migracion; si lo sacaste, es una "
        "migracion destructiva y necesita expand/contract (regla dura 13)"
    )
