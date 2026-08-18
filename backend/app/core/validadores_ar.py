"""Validadores de identificadores del mercado argentino — C-04, `D-9`.

Hoy solo CUIT. Vive en `core` y no en `tenancy` porque `tenants.cuit` es el
primer uso y no el ultimo: `contacts` (C-24) y las operaciones de venta lo
necesitan igual, y un validador por modulo termina siendo tres implementaciones
que difieren justo en los bordes.

EL PREFIJO IMPORTA TANTO COMO EL DIGITO
────────────────────────────────────────
Validar solo el digito verificador deja pasar numeros que ningun organismo
reconoce: `99-12345678-1` supera el modulo 11 y no es CUIT de nadie. Los dos
primeros digitos codifican la categoria fiscal y solo hay siete valores
posibles. Un CUIT mal aceptado no falla al cargarlo — falla meses despues,
cuando hay que facturar.
"""

from __future__ import annotations

import re

__all__ = ["CATEGORIAS_AFIP", "CuitInvalido", "cuit_es_valido", "normalizar_cuit"]


class CuitInvalido(ValueError):
    """El valor no es un CUIT.

    NUNCA lleva el valor rechazado en el mensaje: un CUIT es dato
    identificatorio personal y la Ley 25.326 obliga a enmascararlo en logs.
    Un `raise CuitInvalido(f"CUIT invalido: {valor}")` lo deposita en el
    stacktrace, que termina en Sentry.
    """


# Prefijos que AFIP asigna. `20 23 24 27` son personas fisicas (el 23 y el 24
# aparecen cuando el calculo del digito de un 20 o un 27 da 10) y `30 33 34`
# personas juridicas. Cualquier otro par no corresponde a ninguna categoria.
CATEGORIAS_AFIP = frozenset({"20", "23", "24", "27", "30", "33", "34"})

# La serie es fija y su orden es parte del algoritmo: aplicada al reves da otro
# resultado y aceptaria otro conjunto de numeros.
_MULTIPLICADORES = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)

# Las DOS formas que existen de verdad, y ninguna mas.
#
# Se acepta el separador guion, punto o espacio porque un CUIT se copia y pega
# de mil lados, pero solo EN SU LUGAR: entre los grupos 2-8-1.
#
# La version anterior de esto quitaba separadores de cualquier posicion, y con
# eso `-33693450239` era un CUIT valido — el guion inicial se borraba y
# quedaban once digitos correctos. Tambien lo era `3-3-6-9-3-4-5-0-2-3-9`.
# Un separador suelto adelante no es una variante de formato: es un error de
# carga, o el signo de un numero negativo que alguien exporto mal.
_FORMAS = re.compile(r"^(?:(\d{11})|(\d{2})[-.\s](\d{8})[-.\s](\d))$")


def _digitos(valor: str) -> str | None:
    """Devuelve los 11 digitos, o None si la entrada no tiene una forma valida."""
    coincidencia = _FORMAS.match(valor.strip())
    if coincidencia is None:
        return None
    pelado, prefijo, cuerpo, verificador = coincidencia.groups()
    return pelado if pelado else f"{prefijo}{cuerpo}{verificador}"


def _digito_verificador(diez: str) -> int:
    """Calcula el verificador de los primeros diez digitos (modulo 11).

    Los dos bordes son donde toda implementacion de CUIT se equivoca, porque
    `11 - resto` puede dar un numero de dos cifras:

      - resto 0  ->  11 - 0 = 11, que no es un digito  ->  se usa 0
      - resto 1  ->  11 - 1 = 10, que no es un digito  ->  se usa 9

    El caso del resto 1 es ademas el motivo de que existan los prefijos 23 y
    24: AFIP no emite un CUIT cuyo calculo dé 10 con prefijo 20 o 27, le cambia
    el prefijo. Aca se acepta el 9 porque es lo que traen los CUIT reales ya
    emitidos, que es contra lo que hay que validar.
    """
    suma = sum(int(d) * m for d, m in zip(diez, _MULTIPLICADORES, strict=True))
    resto = suma % 11
    if resto == 0:
        return 0
    if resto == 1:
        return 9
    return 11 - resto


def _digitos_validos(valor: str) -> str | None:
    """Los 11 digitos si el valor es un CUIT completo, o None.

    Un solo lugar decide que es valido. Antes esto vivia repartido entre
    `cuit_es_valido` y `normalizar_cuit`, y la segunda terminaba con un
    `assert` para convencer a mypy de que los digitos existian — un `assert`
    que `python -O` borra, dejando el `None` suelto justo en produccion.
    """
    digitos = _digitos(valor)
    if digitos is None:
        return None
    if digitos[:2] not in CATEGORIAS_AFIP:
        return None
    if int(digitos[10]) != _digito_verificador(digitos[:10]):
        return None
    return digitos


def cuit_es_valido(valor: str) -> bool:
    """`True` si el valor es un CUIT: forma, prefijo de categoria y digito."""
    return _digitos_validos(valor) is not None


def normalizar_cuit(valor: str) -> str:
    """Devuelve el CUIT en la forma canonica `XX-XXXXXXXX-X`.

    Es la forma que espera `tenants.cuit varchar(13)`, y normalizar ANTES de
    guardar es lo que hace que la constraint UNIQUE sirva: sin esto el mismo
    numero con y sin guiones entra dos veces y son dos agencias distintas.

    Explota en vez de devolver una cadena con forma de CUIT para una entrada
    invalida — devolver basura normalizada seria peor que fallar, porque la
    basura entraria a la base con el aspecto correcto.
    """
    digitos = _digitos_validos(valor)
    if digitos is None:
        raise CuitInvalido("el CUIT no es valido: revise digito verificador y prefijo")
    return f"{digitos[:2]}-{digitos[2:10]}-{digitos[10]}"
