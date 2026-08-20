"""Recorrido de las rutas realmente expuestas — soporte de los gates de C-02.

POR QUE VIVE ACA Y NO DENTRO DE UN TEST
────────────────────────────────────────
`_todas_las_rutas` nacio en `tests/unit/test_auth_rutas.py` para el gate de
"ninguna ruta sin token". La tarea 6.9 necesita exactamente el mismo recorrido
para el gate de "ninguna operacion sin declaracion de acceso".

Copiarlo habria sido garantizar que un dia se arregle uno solo. Y este recorrido
en particular ya se rompio una vez —ver la advertencia de `todas_las_rutas`—, asi
que la copia no era una hipotesis: era la repeticion de un fallo conocido.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.core.auth import get_current_user
from app.core.rbac import Espacio, ExigePermiso, ExigeRol, Rol

__all__ = [
    "alcanzables_por",
    "exige_identidad",
    "permisos_de",
    "roles_de",
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


def alcanzables_por(app: FastAPI, rol: Rol, matriz: dict[str, object], *, prefijo: str) -> set[str]:
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
        and all(permiso in matriz for permiso, _ in permisos)
    }
