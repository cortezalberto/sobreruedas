"""Recorrido de las rutas realmente expuestas — soporte de los gates de C-02.

POR QUE VIVE ACA Y NO DENTRO DE UN TEST
────────────────────────────────────────
`_todas_las_rutas` nacio en `tests/unit/test_auth_rutas.py` para el gate de
"ninguna ruta sin token". La tarea 6.9 necesita exactamente el mismo recorrido
para el gate de "ninguna operacion sin declaracion de acceso".

Copiarlo habria sido garantizar que un dia se arregle uno solo. Y este recorrido
en particular ya se rompio una vez —ver la advertencia de `todas_las_rutas`—, asi
que la copia no era una hipotesis: era la repeticion de un fallo conocido.

C-15 SUMA UN TERCER GATE, MISMA RAZON
──────────────────────────────────────
`test_convenciones_de_ruta.py` (`design.md` `D-6` de `vehiculos-api`) necesita
el mismo recorrido para verificar las dos convenciones de
`platform/api-conventions` sobre rutas REALES: idempotencia en las creaciones,
cursor/limit en los listados. `es_creacion`, `es_coleccion`,
`declara_idempotency_key` y `declara_cursor_y_limit` viven aca por el mismo
motivo que las de arriba — un tercer test que reimplemente el recorrido es un
tercer lugar donde se puede romper y no enterarse.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import get_origin, get_type_hints

from fastapi import FastAPI, status
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.rbac import Concesion, Espacio, ExigePermiso, ExigeRol, Rol

__all__ = [
    "alcanzables_por",
    "declara_cursor_y_limit",
    "declara_idempotency_key",
    "es_coleccion",
    "es_creacion",
    "exige_identidad",
    "motivos_faltantes",
    "permisos_de",
    "roles_de",
    "rutas_que_incumplen_convenciones",
    "rutas_sin_declaracion_de_acceso",
    "todas_las_rutas",
]


def todas_las_rutas(contenedor: object) -> Iterator[APIRoute]:
    """Las `APIRoute` del contenedor, ENTRANDO en los routers incluidos.

    ⚠️ ESTE RECORRIDO ES EL CONTROL. Hasta el 18-ago-2026 esta funcion iteraba
    `app.routes` y se quedaba con lo que fuera `APIRoute` — y eso dejaba ciego al
    gate entero.

    FastAPI **no aplana** un `include_router()` dentro de `app.routes`: guarda un
    objeto envoltorio (`_IncludedRouter`) que no es `APIRoute`, con las rutas
    reales colgando de su `original_router`. Como el bucle viejo descartaba todo
    lo que no fuera `APIRoute`, **ninguna ruta montada por `include_router`
    llegaba a mirarse**.

    Y ese es el unico camino por el que entran los routers de dominio. El test
    decia "ninguna ruta de datos se atiende sin token" y habria seguido en verde
    con la API entera abierta: se descubrio cuando el primer router de dominio
    —el catalogo— aparecio sin token y sin estar declarado exento, y el gate no
    dijo nada.
    """
    for ruta in getattr(contenedor, "routes", []):
        if isinstance(ruta, APIRoute):
            yield ruta
            continue
        incluido = getattr(ruta, "original_router", None)
        if incluido is not None:
            yield from todas_las_rutas(incluido)


def _dependencias_de(ruta: APIRoute) -> Iterator[object]:
    """Todo lo que FastAPI va a ejecutar antes del endpoint, en profundidad.

    Se recorre el arbol completo y no solo el primer nivel: una dependency puede
    declarar otras, y `require_role` hace justamente eso —anida la identidad—.
    """
    pendientes = list(ruta.dependant.dependencies)
    while pendientes:
        dependencia = pendientes.pop()
        yield dependencia.call
        pendientes.extend(dependencia.dependencies)


def exige_identidad(ruta: APIRoute) -> bool:
    """Si la ruta va a ejecutar `get_current_user` antes del endpoint.

    Se mira la cadena de dependencias REAL, no una convencion de nombres.
    """
    return any(llamable is get_current_user for llamable in _dependencias_de(ruta))


def permisos_de(ruta: APIRoute) -> set[tuple[str, Espacio]]:
    """Los permisos que la ruta declara, con el espacio de cada uno.

    Se leen de los objetos `ExigePermiso` que cuelgan de la ruta. Por eso
    `require_permission` devuelve una clase y no un cierre: la declaracion tiene
    que poder leerse desde afuera sin hurgar en un `__closure__`.
    """
    return {
        (llamable.permiso, llamable.espacio)
        for llamable in _dependencias_de(ruta)
        if isinstance(llamable, ExigePermiso)
    }


def roles_de(ruta: APIRoute) -> set[Rol]:
    """Los roles que la ruta admite por `require_role`, si declara alguno."""
    admitidos: set[Rol] = set()
    for llamable in _dependencias_de(ruta):
        if isinstance(llamable, ExigeRol):
            admitidos |= set(llamable.admitidos)
    return admitidos


def rutas_sin_declaracion_de_acceso(
    app: FastAPI, *, prefijo: str, exentas: frozenset[str]
) -> set[str]:
    """Las rutas del prefijo que no declaran ni permiso ni rol.

    Una ruta asi la atiende **cualquier sujeto autenticado**, sea cual sea su
    rol. Eso es "abrirse de mas" en el sentido de la tarea 6.9, y es el modo de
    falla que no se ve mirando el codigo: no hay nada escrito que revisar.

    Las operaciones nuevas entran solas — se recorre lo que la app expone, no una
    lista.
    """
    return {
        ruta.path
        for ruta in todas_las_rutas(app)
        if ruta.path.startswith(prefijo)
        and ruta.path not in exentas
        and not permisos_de(ruta)
        and not roles_de(ruta)
    }


def rutas_en_el_espacio_equivocado(app: FastAPI, *, prefijo: str, espacio: Espacio) -> set[str]:
    """Rutas del prefijo que declaran un permiso del OTRO espacio.

    `ADR-024` §2 en su forma mas concreta: un endpoint de `/api/v1` que exija un
    permiso de la matriz de plataforma se lo estaria pidiendo a roles que nunca
    lo van a tener, y uno de `/admin` que exija un permiso de tenant abriria el
    espacio administrativo a los tres roles de agencia.
    """
    return {
        ruta.path
        for ruta in todas_las_rutas(app)
        if ruta.path.startswith(prefijo)
        and any(suyo is not espacio for _, suyo in permisos_de(ruta))
    }


def alcanzables_por(
    app: FastAPI, rol: Rol, celdas: dict[str, Concesion], *, prefijo: str
) -> set[str]:
    """Las rutas del prefijo que ese rol puede atender, segun sus celdas.

    ⚠️ Recibe LAS CELDAS DE UN SOLO ROL y no la matriz entera. Es deliberado:
    `ADR-024` §5 dice que no hay herencia, asi que quien llame tiene que iterar
    los roles uno por uno. Si esta funcion recibiera la matriz completa podria
    —y alguna vez alguien lo haria— resolver "el rol o alguno mas alto", que es
    exactamente la contencion que §5 prohibe asumir.
    """
    return {
        ruta.path
        for ruta in todas_las_rutas(app)
        if ruta.path.startswith(prefijo)
        and (permisos := permisos_de(ruta))
        and all(permiso in celdas for permiso, _ in permisos)
    }


# ── D-6 de `vehiculos-api` — las dos convenciones de plataforma ─────────────


def es_creacion(ruta: APIRoute) -> bool:
    """Si el `POST` declara que CREA un recurso.

    Se lee el `status_code` que el propio endpoint declara, `201 Created`, y no
    la forma del path. La forma es ambigua: `POST /vehicles/import` tambien
    tiene un path sin parametro (`/import`, no `/import/{id}`) y NO es una
    creacion sincronica de un recurso — es `202 Accepted`, con su propio
    mecanismo de progreso. El status code es la unica senal que no admite dos
    lecturas, y es ademas la que los tres endpoints de creacion que existen hoy
    (`POST /vehicles`, `POST /branches`, `POST /users/invitations`) ya
    declaran, cada uno por su cuenta, sin que nadie se lo pidiera para esto.
    """
    return "POST" in (ruta.methods or set()) and ruta.status_code == status.HTTP_201_CREATED


def es_coleccion(ruta: APIRoute) -> bool:
    """Si el `GET` devuelve una lista.

    Se lee el tipo de retorno REAL con `get_type_hints`, y no
    `ruta.endpoint.__annotations__` a secas: todo `app/` lleva
    `from __future__ import annotations`, que convierte las anotaciones en
    texto (`"list[Vehiculo]"` en vez del tipo `list[Vehiculo]`), y
    `get_origin` sobre un string siempre da `None` — el chequeo pasaria
    siempre, calladamente, sobre cualquier endpoint.

    Y NO la forma del path (sin `{param}` final): esa señal marca como
    "coleccion" a `GET /tenant/me`, `GET /auth/me`, `/health` y `/ready`, que
    devuelven un objeto — cuatro excepciones de puro ruido por cada gate que
    corra, y `D-6` es explicito sobre el riesgo: *"sin este test la lista de
    excepciones se vuelve un cajón"*. El tipo de retorno no tiene ese problema:
    a esas cuatro rutas ni las mira.
    """
    if "GET" not in (ruta.methods or set()):
        return False
    return get_origin(get_type_hints(ruta.endpoint).get("return")) is list


def declara_idempotency_key(ruta: APIRoute) -> bool:
    """Si la ruta declara el header `Idempotency-Key` (por su alias HTTP)."""
    return any(
        (campo.alias or campo.name) == "Idempotency-Key" for campo in ruta.dependant.header_params
    )


def _nombres_de_query(ruta: APIRoute) -> set[str]:
    """Los query params que la ruta expone, DESARMANDO modelos anidados.

    `GET /vehicles` no declara `cursor` y `limit` como parametros sueltos:
    viajan como CAMPOS de `FiltrosDeBusqueda` (ver el docstring de
    `listar_vehiculos` en `modules/stock/router.py` — es deliberado, no un
    descuido). FastAPI los desarma en el OpenAPI que genera, pero
    `dependant.query_params` los deja agrupados en UN `ModelField` cuyo nombre
    es el del parametro de Python (`filtros`), no el de sus campos. Sin este
    desarme, cualquier ruta que use el mismo patron se veria sin `cursor` ni
    `limit` aunque los tenga.
    """
    nombres: set[str] = set()
    for campo in ruta.dependant.query_params:
        anotacion = campo.field_info.annotation
        if isinstance(anotacion, type) and issubclass(anotacion, BaseModel):
            nombres |= set(anotacion.model_fields.keys())
        else:
            nombres.add(campo.alias or campo.name)
    return nombres


def declara_cursor_y_limit(ruta: APIRoute) -> bool:
    """Si la ruta declara AMBOS parametros de paginacion por cursor."""
    nombres = _nombres_de_query(ruta)
    return "cursor" in nombres and "limit" in nombres


def rutas_que_incumplen_convenciones(
    app: FastAPI, *, excepciones: dict[tuple[str, str], str]
) -> dict[tuple[str, str], str]:
    """`(metodo, path)` -> que le falta, para cada ruta real que incumple.

    Recibe la app COMPLETA, no un prefijo: las dos convenciones de
    `platform/api-conventions` son de plataforma, no de `vehicles` — el gate
    tiene que poder nombrar un incumplimiento tanto ahi como en cualquier otro
    modulo. `excepciones` es `(metodo, path) -> motivo`; una entrada sin motivo
    (cadena vacia) no excusa nada, la valida `motivos_faltantes`.
    """
    incumplimientos: dict[tuple[str, str], str] = {}
    for ruta in todas_las_rutas(app):
        for metodo in {"GET", "POST"} & (ruta.methods or set()):
            clave = (metodo, ruta.path)
            if excepciones.get(clave, "").strip():
                continue
            if metodo == "POST" and es_creacion(ruta) and not declara_idempotency_key(ruta):
                incumplimientos[clave] = "POST de creacion sin declarar `Idempotency-Key`"
            elif metodo == "GET" and es_coleccion(ruta) and not declara_cursor_y_limit(ruta):
                incumplimientos[clave] = "GET de coleccion sin declarar `cursor`/`limit`"
    return incumplimientos


def motivos_faltantes(excepciones: dict[tuple[str, str], str]) -> set[tuple[str, str]]:
    """Las excepciones SIN motivo — un cajón en formación.

    `D-6`: *"Una excepción con nombre y razón se lee en un diff; un gate que no
    existe, no"*. Una excepción con motivo vacío es exactamente ese cajón —
    pasa la revisión de un diff sin que nadie tenga que justificar nada.
    """
    return {clave for clave, motivo in excepciones.items() if not motivo.strip()}
