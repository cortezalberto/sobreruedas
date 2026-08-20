"""Tipos de PostgreSQL que SQLAlchemy no trae de fabrica — C-04.

POR QUE NO SE USA `geoalchemy2`
───────────────────────────────
Es la libreria estandar para esto y seria lo primero que uno agarra. No es
dependencia de este proyecto, y nada la usa todavia: `branches.geo_point` se
crea en C-04 porque agregarla despues cuesta una migracion sobre una tabla con
datos, pero quien la LEE es el modulo de mapas, varias Olas mas adelante.

Una dependencia que ningun codigo usa no sale gratis: entra al `pip-audit` del
pipeline —que bloquea ante cualquier severidad—, hay que mantenerla al dia, y
su primer uso queda lejos. Trece lineas propias evitan todo eso.

El dia que haya que hacer consultas geograficas de verdad (`ST_DWithin`,
ordenar por distancia), `geoalchemy2` entra y este tipo se retira. Hasta
entonces lo unico que hace falta es que `Base.metadata` describa la columna
igual que la base, para que el autogenerate de Alembic no proponga borrarla.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.types import UserDefinedType

__all__ = ["PuntoGeografico"]


class PuntoGeografico(UserDefinedType[str]):
    """`geography(Point,4326)` — coordenadas WGS 84, el sistema del GPS.

    Opaco a proposito: los valores van y vienen como los entrega el driver. No
    se declara conversion de ida ni de vuelta porque no hay codigo que lo lea, y
    una conversion sin uso es una conversion sin test.
    """

    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return "geography(Point,4326)"
