"""Las plantillas de notificacion — C-06, `T-035`.

EN CODIGO Y NO EN UNA TABLA, Y NO ES PEREZA
────────────────────────────────────────────
Una tabla de plantillas suena mas flexible y es peor acá por tres motivos
concretos:

  1. **Nadie las edita.** No hay pantalla de administracion de plantillas en
     ninguna de las 92 historias de usuario. Una tabla que solo escribe una
     migracion es un archivo de codigo con pasos de mas.
  2. **Un `type` sin plantilla se detecta al compilar**, no en produccion. Con
     una tabla, la unica forma de saber que falta es que alguien reciba el texto
     crudo.
  3. **El texto y el codigo que lo dispara viajan en el mismo commit.** Con la
     tabla, cambiar el payload de un evento y su redaccion son dos despliegues
     que hay que coordinar.

EL FORMATEO ES `str.format_map` Y NO UNA f-string
──────────────────────────────────────────────────
El payload viene de un evento —o sea, de datos— y una f-string sobre datos es
evaluacion de codigo. `format_map` con un diccionario que devuelve un marcador
para lo que falta no ejecuta nada y no levanta: una notificacion a la que le
falta un dato se ve incompleta, que es mucho mejor que no verse.

⚠️ `format_map` SIGUE PERMITIENDO `{a.__class__}`. Por eso las claves del payload
se pasan por `_SoloTexto`, que las convierte a cadena antes de sustituirlas: sobre
una cadena, el acceso a atributos no llega a ningun objeto util.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

__all__ = ["TIPOS_CONOCIDOS", "Plantilla", "redactar"]

_FALTANTE: Final = "—"


class _SoloTexto(dict[str, str]):
    """El mapa que `format_map` consulta. Todo sale como texto; lo que falta, un guion."""

    def __missing__(self, clave: str) -> str:
        return _FALTANTE


class Plantilla:
    """Un titulo y un cuerpo, con marcadores `{clave}` del payload."""

    __slots__ = ("cuerpo", "titulo")

    def __init__(self, titulo: str, cuerpo: str) -> None:
        self.titulo = titulo
        self.cuerpo = cuerpo


# Las plantillas por tipo de notificacion.
#
# ⚠️ EL TIPO DE LA NOTIFICACION NO ES EL TIPO DEL EVENTO. Se parecen y es a
# proposito que no sean lo mismo: un evento es un hecho del dominio y puede
# producir cero, una o varias notificaciones distintas segun a quien le
# corresponda. Atarlos haria imposible mandar dos textos diferentes —al vendedor
# y al gerente— por el mismo hecho.
PLANTILLAS: Final[dict[str, Plantilla]] = {
    "vehiculo.cambio_de_estado": Plantilla(
        titulo="Un vehiculo tuyo cambio de estado",
        cuerpo="El vehiculo {identificador} paso de {desde} a {hasta}.",
    ),
}

TIPOS_CONOCIDOS: Final = frozenset(PLANTILLAS)


def redactar(tipo: str, payload: Mapping[str, Any]) -> tuple[str, str]:
    """El titulo y el cuerpo de una notificacion. Nunca levanta.

    UN TIPO DESCONOCIDO DEVUELVE TEXTO CRUDO EN VEZ DE ROMPER, y es deliberado:
    esta funcion la llama la pantalla que lista las notificaciones, no la que las
    crea. Levantar acá tumbaria el listado entero por una sola fila de un tipo que
    alguien agrego sin su plantilla — y con el listado caido, tampoco se ven las
    que si estan bien.

    El sintoma queda visible igual: la notificacion aparece con su tipo en bruto,
    que es feo y se nota. Ver el mismo criterio en `nombreDeEstado` del frontend.
    """
    plantilla = PLANTILLAS.get(tipo)
    if plantilla is None:
        return tipo, ""

    datos = _SoloTexto({clave: str(valor) for clave, valor in payload.items()})
    return plantilla.titulo.format_map(datos), plantilla.cuerpo.format_map(datos)
