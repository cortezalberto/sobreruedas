"""La traduccion de campo del schema a columna del CSV — C-17.

POR QUE MERECE UN ARCHIVO
──────────────────────────
Es dos lineas, y las dos deciden si un mensaje de error sirve o no. Pydantic
rechaza `price_ars`; la planilla dice `precio_ars`. Devolver el nombre del campo
manda a buscar una columna que no existe en el archivo que el usuario tiene
abierto.

La rama del `loc` vacio no se puede provocar desde una planilla —el lector ya
filtra todo lo que llegaria asi— y aun asi tiene que estar: un validador de
MODELO (no de campo) levanta con `loc = ()`, y sin el guard esto seria un
`IndexError` dentro del manejo de otro error.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.stock.importacion_servicio import _columna_de, _mensaje_de
from app.modules.stock.schemas import VehiculoCrear


def _fallo(**cambios: object) -> ValidationError:
    campos: dict[str, object] = {
        "branch_id": "11111111-1111-1111-1111-111111111111",
        "brand_id": "22222222-2222-2222-2222-222222222222",
        "model_id": "33333333-3333-3333-3333-333333333333",
        "year": 2021,
        "mileage_km": 30_000,
        "color": "Blanco",
        "fuel_type": "diesel",
        "transmission": "manual",
        "body_type": "pickup",
        "price_ars": Decimal("25000000.00"),
        "domain_plate": "AA123BB",
    }
    with pytest.raises(ValidationError) as capturado:
        VehiculoCrear(**{**campos, **cambios})
    return capturado.value


def test_el_campo_del_schema_se_traduce_a_la_columna_de_la_planilla() -> None:
    assert _columna_de(_fallo(price_ars=Decimal("-1"))) == "precio_ars"
    assert _columna_de(_fallo(mileage_km=-1)) == "kilometros"
    assert _columna_de(_fallo(year=1800)) == "anio"


def test_los_campos_que_el_csv_trae_por_nombre_tambien_se_traducen() -> None:
    """`brand_id` no es una columna de la planilla: la columna es `marca`."""
    assert _columna_de(_fallo(brand_id="no-es-un-uuid")) == "marca"


def test_un_error_de_modelo_y_no_de_campo_no_nombra_ninguna_columna() -> None:
    """`_identificable` es un `model_validator`: su `loc` viene vacio.

    Devolver `None` es lo correcto — el problema no esta en una celda, esta en
    la combinacion de dos. Sin el guard esto seria un `IndexError` levantado
    mientras se maneja otro error, que es la peor forma de perder un mensaje.
    """
    fallo = _fallo(domain_plate=None, chassis_number=None)

    assert _columna_de(fallo) is None
    assert "dominio" in _mensaje_de(fallo)
