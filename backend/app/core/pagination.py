"""Paginacion por cursor — T-012, capability `platform/api-conventions`.

POR QUE CURSOR Y NO `OFFSET`
────────────────────────────
`OFFSET n` hace que la base recorra y descarte n filas antes de devolver nada:
la pagina 500 cuesta 500 veces la pagina 1. Y es incorrecto ademas de lento —
si alguien inserta una fila mientras se recorre, todo se corre un lugar y el
recorrido repite o saltea elementos sin que nada falle de forma visible.

El cursor apunta a una POSICION, no a una cantidad. Insertar no la mueve.

EL ORDEN ES POR `(created_at, id)`, NO POR FECHA SOLA
─────────────────────────────────────────────────────
Con `created_at` repetido —dos filas creadas en el mismo milisegundo, que en una
importacion masiva son muchas— el orden por fecha sola queda a criterio del
motor y puede cambiar entre dos consultas identicas. El recorrido entonces
repite o saltea. El `id` desempata y hace el orden total.

EL CURSOR ES OPACO, NO ES SEGURO
────────────────────────────────
Va en base64 de un JSON con claves cortas. Eso lo hace ilegible de un vistazo,
que es todo lo que se busca: que su contenido no se vuelva parte del contrato y
que nadie empiece a construirlo a mano.

**No esta firmado y no pretende estarlo.** Cualquiera puede fabricar uno. Se
puede vivir con eso porque las dos cosas que podria falsear estan cubiertas:

  - el TENANT — se compara contra el del contexto y se rechaza si difiere, y
    ademas se cuenta como intento de acceso cruzado (D-6, `RN-MT-08`).
  - la POSICION — falsearla solo permite saltear o repetir datos PROPIOS, que
    el cliente ya puede leer.

Firmarlo agregaria una clave que rotar y no cerraria ningun agujero que hoy
este abierto.

Ver `design.md` D-6 de C-02.
"""

from __future__ import annotations

import base64
import binascii
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Row, Select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RequestError
from app.db.session import registrar_violacion_de_aislamiento

# Toda tabla del sistema los tiene: la `Base` declarativa lo exige y el test
# introspectivo de `pg_policies` lo verifica. Que los nombres esten aca y no en
# cada llamada es lo que permite que `paginar` sirva para cualquier `select` sin
# que quien la usa repita la convencion.
CAMPO_FECHA = "created_at"
CAMPO_ID = "id"

# Sin fuente en el corpus: ningun documento fija estos numeros. 20 entra en una
# pantalla sin scroll infinito; 100 es lo que una importacion o un export
# pueden pedir sin que una sola consulta bloquee una conexion del pool.
TAMANO_POR_DEFECTO = 20
TAMANO_MAXIMO = 100


class CursorInvalido(RequestError):
    """El cursor no se pudo interpretar, o no es de este tenant.

    Los dos casos dan el MISMO error a proposito. Distinguirlos —"cursor
    ilegible" contra "cursor de otro tenant"— le confirmaria a quien prueba
    cursores ajenos que acerto el formato, que es media pista regalada.
    """

    def __init__(self, detail: str = "el cursor de paginacion no es valido") -> None:
        super().__init__(detail, code="cursor_invalido")


@dataclass(frozen=True)
class Posicion:
    """El ultimo elemento entregado. La proxima pagina empieza despues de esto."""

    created_at: datetime
    id: uuid.UUID


@dataclass(frozen=True)
class Pagina:
    """Un tramo del listado, y como pedir el siguiente.

    `cursor_siguiente is None` significa **ultima pagina**, y se sabe al
    recibirla. La alternativa —darse cuenta al pedir una pagina mas y que venga
    vacia— gasta una consulta por recorrido y deja ambiguo el caso de un
    listado cuyo total es multiplo exacto del tamano de pagina.
    """

    items: list[Row[Any]]
    cursor_siguiente: str | None


def acotar_tamano(pedido: int | None) -> int:
    """El tamano de pagina efectivo.

    Pedir mas que el maximo **se acota, no falla**: el maximo es una defensa del
    servidor, no una regla que el cliente incumple. Devolver un error obligaria
    a cada cliente a conocer un numero que puede cambiar.

    Un pedido de cero o negativo tambien se acota: un tamano cero pagina para
    siempre sin avanzar nunca.
    """
    if pedido is None:
        return TAMANO_POR_DEFECTO
    return max(1, min(pedido, TAMANO_MAXIMO))


def codificar_cursor(*, tenant: uuid.UUID, created_at: datetime, id: uuid.UUID) -> str:
    """La posicion y su tenant, en una cadena opaca.

    Claves de una letra y `separators` sin espacios: el cursor viaja en la query
    string de cada pagina y no hay motivo para engordarlo.
    """
    crudo = json.dumps(
        {"t": str(tenant), "c": created_at.isoformat(), "i": str(id)},
        separators=(",", ":"),
    )
    # Sin el relleno `=`: en una query string se escapa como %3D y ensucia la
    # URL. Se repone al decodificar.
    return base64.urlsafe_b64encode(crudo.encode()).decode().rstrip("=")


def decodificar_cursor(cursor: str, *, tenant: uuid.UUID) -> Posicion:
    """La posicion que el cursor codifica, si es de este tenant.

    Rechaza sin devolver el cursor en el mensaje: lleva el tenant adentro y este
    error termina en un log.
    """
    try:
        relleno = "=" * (-len(cursor) % 4)
        datos = json.loads(base64.urlsafe_b64decode(cursor + relleno))
        del_cursor = uuid.UUID(datos["t"])
        posicion = Posicion(
            created_at=datetime.fromisoformat(datos["c"]),
            id=uuid.UUID(datos["i"]),
        )
    except (ValueError, TypeError, KeyError, binascii.Error) as error:
        raise CursorInvalido() from error

    if del_cursor != tenant:
        # Se CUENTA ademas de rechazarse. Un cursor emitido para un tenant y
        # presentado en otro es un intento de acceso cruzado igual que una
        # consulta: si solo se rechazara, un barrido de cursores ajenos no
        # dejaria rastro en ningun lado (`RN-MT-08`).
        registrar_violacion_de_aislamiento()
        raise CursorInvalido()

    return posicion


async def paginar(
    sesion: AsyncSession,
    consulta: Select[Any],
    *,
    tenant: uuid.UUID,
    cursor: str | None = None,
    tamano: int | None = None,
) -> Pagina:
    """Una pagina de `consulta`, ordenada y acotada por cursor.

    `consulta` tiene que seleccionar `created_at` e `id`: son las dos columnas
    del orden y las que arman el cursor de la pagina siguiente. Si faltan es un
    error de programacion —no de quien llama a la API— y por eso rompe con
    `LookupError` y no con el error de peticion.

    El filtro por tenant va en `consulta`, no aca: es la capa 3 de `ADR-006` y
    le corresponde a quien construye el listado. `tenant` se usa para acotar el
    cursor, que es un problema distinto.
    """
    try:
        fecha = consulta.selected_columns[CAMPO_FECHA]
        identificador = consulta.selected_columns[CAMPO_ID]
    except KeyError as error:
        raise LookupError(
            f"la consulta a paginar tiene que seleccionar '{CAMPO_FECHA}' e "
            f"'{CAMPO_ID}': son el orden y el contenido del cursor"
        ) from error

    limite = acotar_tamano(tamano)

    if cursor is not None:
        desde = decodificar_cursor(cursor, tenant=tenant)
        # Comparacion de tuplas y no `fecha > x OR (fecha = x AND id > y)`: es
        # la misma condicion, la escribe PostgreSQL sola, y sobre todo puede
        # usar el indice compuesto que la forma con OR no aprovecha.
        consulta = consulta.where(tuple_(fecha, identificador) > (desde.created_at, desde.id))

    # Se pide UNO MAS del que se va a devolver. Ese elemento no se entrega:
    # existe solo para saber si hay pagina siguiente sin gastar una consulta de
    # conteo, que sobre una tabla grande cuesta mas que la pagina misma.
    filas = list(
        (await sesion.execute(consulta.order_by(fecha, identificador).limit(limite + 1))).all()
    )

    hay_mas = len(filas) > limite
    items = filas[:limite]

    siguiente = None
    if hay_mas:
        ultima = items[-1]
        siguiente = codificar_cursor(
            tenant=tenant,
            created_at=getattr(ultima, CAMPO_FECHA),
            id=getattr(ultima, CAMPO_ID),
        )

    return Pagina(items=items, cursor_siguiente=siguiente)
