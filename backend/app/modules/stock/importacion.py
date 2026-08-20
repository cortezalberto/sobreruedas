"""Lectura de la planilla de importacion de stock — C-17, `T-093`.

QUE HACE Y QUE NO
──────────────────
Convierte los bytes que subio una agencia en **filas listas para validar** y en
**errores con numero de linea**. No toca la base, no resuelve marcas contra el
catalogo y no crea nada. Eso es del servicio; esto es el parseo, y esta separado
porque es donde vive casi todo el riesgo del change y porque asi se puede probar
sin PostgreSQL.

CONTRA QUE ARCHIVO SE PROGRAMO ESTO
────────────────────────────────────
El producto compite contra Excel. El archivo que va a llegar no es un CSV de
manual: es un `Guardar como → CSV` de un Excel en español. O sea, con **BOM**,
separador **`;`**, precios **`1.250.000,50`**, encabezados en mayusculas y
—cuando la maquina es vieja— codificado en **cp1252**, donde `Citroën` ni
siquiera es UTF-8 valido.

Un lector que solo entienda el CSV canonico pasa todos sus tests y falla con el
primer cliente. Cada tolerancia de abajo esta por un caso concreto, no por
generosidad.

DOS CLASES DE FALLA, Y LA DIFERENCIA IMPORTA
─────────────────────────────────────────────
  `ArchivoIlegible`  la planilla entera no sirve: falta una columna
                     obligatoria, tiene mas filas que el maximo, no es texto.
                     Un error de estos por cada una de 5.000 filas no es un
                     reporte, es ruido — se corta antes.

  `ErrorDeFila`      esa fila no sirve y las demas si. `RN-ST-13`: una
                     importacion de 5.000 filas con 12 errores es un exito con
                     12 correcciones, no un fracaso.

LIMITES (`RN-ST-13`)
─────────────────────
10 MB, 5.000 filas, lotes de 100 con commit por lote. Los dos primeros se
verifican aca; el tercero es del servicio, que es quien escribe.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.stock.schemas import (
    ANIO_MINIMO,
    Carroceria,
    Combustible,
    Transmision,
    normalizar_chasis,
    normalizar_dominio,
)

__all__ = [
    "COLUMNAS_IDENTIFICATORIAS",
    "COLUMNAS_OBLIGATORIAS",
    "COLUMNAS_OPCIONALES",
    "COLUMNA_DE_CAMPO",
    "LIMITE_DE_BYTES",
    "LIMITE_DE_FILAS",
    "PLANTILLA",
    "TAMANO_DE_LOTE",
    "ArchivoIlegible",
    "ErrorDeFila",
    "FilaLeida",
    "Lectura",
    "leer_planilla",
]

# `RN-ST-13`. Los tres numeros son de la regla, no de una estimacion.
LIMITE_DE_BYTES = 10 * 1024 * 1024
LIMITE_DE_FILAS = 5_000
TAMANO_DE_LOTE = 100

# Los nombres de columna estan en español y en minusculas porque los escribe una
# persona en Excel, no un integrador. `brand_id` seria correcto y no lo llenaria
# nadie: quien completa la planilla conoce "Toyota", no un UUID.
COLUMNAS_OBLIGATORIAS = (
    "marca",
    "modelo",
    "anio",
    "kilometros",
    "color",
    "combustible",
    "transmision",
    "carroceria",
    "precio_ars",
)

# Una de estas dos tiene que estar en la cabecera. Ver `_mapa_de_columnas`.
COLUMNAS_IDENTIFICATORIAS = ("dominio", "chasis")

COLUMNAS_OPCIONALES = (
    *COLUMNAS_IDENTIFICATORIAS,
    "sucursal",
    "version",
    "numero_de_motor",
    "precio_usd",
    "costo_de_adquisicion_ars",
    "descripcion",
)

# Cada columna del CSV y a que campo de `VehiculoCrear` corresponde. Las tres
# que se resuelven contra el catalogo —marca, modelo, version— y la sucursal no
# estan: viajan por nombre y las traduce el servicio.
_CAMPO_DE_COLUMNA = {
    "anio": "year",
    "kilometros": "mileage_km",
    "color": "color",
    "combustible": "fuel_type",
    "transmision": "transmission",
    "carroceria": "body_type",
    "precio_ars": "price_ars",
    "dominio": "domain_plate",
    "chasis": "chassis_number",
    "numero_de_motor": "engine_number",
    "precio_usd": "price_usd",
    "costo_de_adquisicion_ars": "acquisition_cost_ars",
    "descripcion": "description",
}

# La inversa, publica: quien recibe un error de Pydantic tiene el nombre del
# CAMPO (`price_ars`) y necesita el de la COLUMNA (`precio_ars`) para decirle al
# usuario donde mirar. Se deriva y no se escribe a mano — un segundo diccionario
# a mano es un segundo diccionario que alguien va a olvidar de actualizar.
COLUMNA_DE_CAMPO = {campo: columna for columna, campo in _CAMPO_DE_COLUMNA.items()} | {
    # Los tres que el CSV trae por NOMBRE y el schema recibe ya resueltos a id.
    "brand_id": "marca",
    "model_id": "modelo",
    "branch_id": "sucursal",
}

_ENTEROS = {"anio", "kilometros"}
_DECIMALES = {"precio_ars", "precio_usd", "costo_de_adquisicion_ars"}
_ENUMS: dict[str, type[Combustible] | type[Transmision] | type[Carroceria]] = {
    "combustible": Combustible,
    "transmision": Transmision,
    "carroceria": Carroceria,
}

PLANTILLA = (
    ",".join([*COLUMNAS_OBLIGATORIAS, *COLUMNAS_OPCIONALES])
    + "\r\n"
    + "Toyota,Hilux,2021,45000,Blanco,diesel,manual,pickup,25000000.00,"
    + "AA123BB,8AWZZZ377VA123456,Casa central,SRV 4x4,,28000.00,21000000.00,"
    + "Unico dueño con service oficial al dia\r\n"
)


class ArchivoIlegible(Exception):
    """La planilla entera no sirve. No hay filas que rescatar."""


@dataclass(frozen=True)
class ErrorDeFila:
    """Un rechazo con direccion postal: linea y columna.

    Sin la columna, corregir un archivo de 5.000 filas es leer 17 celdas por
    cada error hasta encontrar cual molesta.
    """

    fila: int
    columna: str | None
    mensaje: str


@dataclass(frozen=True)
class FilaLeida:
    """Una fila que ya paso el parseo y todavia no vio la base.

    `marca`, `modelo`, `version` y `sucursal` van por NOMBRE: es lo que hay en
    la planilla. Traducirlos a id es del servicio, que es el que tiene sesion.
    """

    fila: int
    marca: str
    modelo: str
    sucursal: str | None
    version: str | None
    datos: dict[str, Any]


@dataclass
class Lectura:
    filas: list[FilaLeida] = field(default_factory=list)
    errores: list[ErrorDeFila] = field(default_factory=list)


def leer_planilla(contenido: bytes) -> Lectura:
    """Lee la planilla entera. Levanta `ArchivoIlegible` si no hay nada que leer.

    El orden de las verificaciones es deliberado: primero lo que descarta el
    archivo completo —tamaño, codificacion, columnas, cantidad de filas— y
    recien despues el contenido fila por fila. Al reves, un archivo de 50.000
    filas se parsea entero para despues avisar que tiene 45.000 de mas.
    """
    if len(contenido) > LIMITE_DE_BYTES:
        raise ArchivoIlegible(
            f"el archivo pesa mas de {LIMITE_DE_BYTES // (1024 * 1024)} MB (RN-ST-13)"
        )

    texto = _decodificar(contenido)
    lector = csv.reader(io.StringIO(texto, newline=""), delimiter=_separador(texto))
    try:
        cabecera = next(lector)
    except StopIteration:
        raise ArchivoIlegible("el archivo esta vacio") from None

    indice = _mapa_de_columnas(cabecera)
    filas = [f for f in lector]
    if len(filas) > LIMITE_DE_FILAS:
        raise ArchivoIlegible(
            f"la planilla tiene {len(filas)} filas y el maximo es {LIMITE_DE_FILAS} (RN-ST-13)"
        )

    lectura = Lectura()
    for numero, celdas in enumerate(filas, start=2):  # la cabecera es la fila 1
        if not any(celda.strip() for celda in celdas):
            # Excel deja lineas en blanco al final de casi todo archivo. No son
            # filas mal cargadas y contarlas como error asusta sin motivo.
            continue
        _leer_fila(numero, celdas, indice, lectura)
    return lectura


# ── Archivo ─────────────────────────────────────────────────────────────────


def _decodificar(contenido: bytes) -> str:
    """UTF-8 (con o sin BOM) y, si no, cp1252.

    `cp1252` no falla casi nunca —mapea casi todos los bytes— asi que va ultimo
    y a proposito: primero se intenta la interpretacion correcta y solo despues
    la que "siempre anda". Si tampoco eso da algo parecido a texto, el archivo
    no es un CSV (tipicamente: subieron el `.xlsx`).
    """
    for codificacion in ("utf-8-sig", "cp1252"):
        try:
            texto = contenido.decode(codificacion)
        except UnicodeDecodeError:
            continue
        if "\x00" in texto:
            # Un binario decodificado con cp1252 "funciona" y da basura. El byte
            # nulo es la señal barata de que esto no es texto.
            break
        return texto
    raise ArchivoIlegible("el archivo no es un CSV de texto — ¿se subio el .xlsx?")


def _separador(texto: str) -> str:
    """`;` o `,`, decidido por la primera linea.

    Excel en español exporta con `;` porque la coma es el separador decimal del
    sistema. No es una variante exotica: es lo que sale por defecto en la mayor
    parte de las maquinas del mercado al que apunta el producto.
    """
    primera = texto.splitlines()[0] if texto else ""
    return ";" if primera.count(";") > primera.count(",") else ","


def _mapa_de_columnas(cabecera: list[str]) -> dict[str, int]:
    """De nombre de columna a posicion, tolerando mayusculas y espacios.

    Falta una obligatoria ⇒ `ArchivoIlegible`. Es lo unico razonable: sin
    `precio_ars` no hay 5.000 filas mal cargadas, hay una planilla equivocada, y
    el mensaje tiene que nombrar la columna para arreglarla de una sola vez.
    """
    posiciones = {celda.strip().lower(): i for i, celda in enumerate(cabecera)}
    faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in posiciones]
    if faltantes:
        raise ArchivoIlegible("faltan columnas obligatorias: " + ", ".join(faltantes))

    # `ADR-031` a nivel de ARCHIVO. Ninguna de las dos es obligatoria por si
    # sola —un 0 km sin patentar existe, un usado sin chasis a la vista
    # tambien— pero una planilla sin ninguna de las dos columnas no puede
    # producir una sola fila valida: serian 5.000 errores identicos diciendo lo
    # mismo. Es un problema de la planilla, no de los datos.
    if not any(c in posiciones for c in COLUMNAS_IDENTIFICATORIAS):
        raise ArchivoIlegible(
            "hace falta al menos una columna de " + " o ".join(COLUMNAS_IDENTIFICATORIAS)
        )
    return posiciones


# ── Fila ────────────────────────────────────────────────────────────────────


def _leer_fila(numero: int, celdas: list[str], indice: dict[str, int], lectura: Lectura) -> None:
    """Lee una fila y la deja en `lectura`, como dato o como error.

    Se corta en el PRIMER error de la fila y no se acumulan todos: una fila con
    el año mal suele tener el resto bien, y listar siete problemas derivados de
    uno solo entierra el que importa.
    """

    def celda(columna: str) -> str:
        posicion = indice.get(columna)
        if posicion is None or posicion >= len(celdas):
            return ""
        return celdas[posicion].strip()

    datos: dict[str, Any] = {}
    try:
        for columna, campo in _CAMPO_DE_COLUMNA.items():
            datos[campo] = _convertir(columna, celda(columna))

        marca, modelo = celda("marca"), celda("modelo")
        if not marca or not modelo:
            raise _Rechazo("marca" if not marca else "modelo", "no puede estar vacio")

        _verificar_identificable(datos)
        _verificar_anio(datos["year"])
    except _Rechazo as rechazo:
        lectura.errores.append(ErrorDeFila(numero, rechazo.columna, rechazo.mensaje))
        return

    lectura.filas.append(
        FilaLeida(
            fila=numero,
            marca=marca,
            modelo=modelo,
            sucursal=celda("sucursal") or None,
            version=celda("version") or None,
            datos=datos,
        )
    )


class _Rechazo(Exception):
    """Corta el parseo de UNA fila. No sale de este modulo."""

    def __init__(self, columna: str | None, mensaje: str) -> None:
        super().__init__(mensaje)
        self.columna = columna
        self.mensaje = mensaje


def _convertir(columna: str, valor: str) -> Any:
    """Una celda de texto al tipo que espera `VehiculoCrear`.

    Vacio es `None` salvo en las obligatorias, donde el `None` lo rechaza el
    schema mas adelante con su propio mensaje. Duplicar acá esa validacion
    seria tener dos lugares donde decir que el color no puede faltar.
    """
    if columna in _ENUMS:
        return _a_enum(columna, valor)
    if columna in _ENTEROS:
        return _a_entero(columna, valor)
    if columna in _DECIMALES:
        return _a_decimal(columna, valor)
    if columna == "dominio":
        return _normalizado(columna, valor, normalizar_dominio)
    if columna == "chasis":
        return _normalizado(columna, valor, normalizar_chasis)
    return valor or None


def _a_enum(columna: str, valor: str) -> str:
    tipo = _ENUMS[columna]
    try:
        return str(tipo(valor.strip().lower()))
    except ValueError:
        permitidos = ", ".join(sorted(m.value for m in tipo))
        raise _Rechazo(
            columna, f"'{valor}' no es valido — se espera uno de: {permitidos}"
        ) from None


def _a_entero(columna: str, valor: str) -> int:
    # `30.000` es treinta mil en una planilla argentina, no un decimal.
    limpio = valor.replace(".", "").replace(" ", "")
    try:
        return int(limpio)
    except ValueError:
        raise _Rechazo(columna, f"'{valor}' no es un numero entero") from None


def _a_decimal(columna: str, valor: str) -> Decimal | None:
    """`1.250.000,50` y `1250000.50`, las dos formas.

    La regla para distinguirlas: si hay coma, la coma es el separador decimal y
    los puntos son de miles. Es la convencion argentina y la que produce Excel
    en español. Si no hay coma, el punto es decimal — que es lo que produce
    cualquier export en ingles.
    """
    if not valor:
        return None
    limpio = valor.replace(" ", "").replace("$", "")
    if "," in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    try:
        return Decimal(limpio)
    except InvalidOperation:
        raise _Rechazo(columna, f"'{valor}' no es un importe") from None


def _normalizado(columna: str, valor: str, normalizar: Any) -> str | None:
    """Usa el MISMO normalizador que el alta por API, no una copia.

    Dos normalizadores para el mismo dato divergen, y el sintoma es que un
    vehiculo cargado por planilla y otro por formulario no chocan entre si
    aunque tengan la misma patente.
    """
    if not valor:
        return None
    try:
        return str(normalizar(valor))
    except ValueError as fallo:
        raise _Rechazo(columna, str(fallo)) from None


def _verificar_identificable(datos: dict[str, Any]) -> None:
    """`ADR-031`, la misma regla que `VehiculoCrear._identificable`.

    Se repite acá y no se delega al schema porque el mensaje tiene que salir
    con numero de fila; el `ValidationError` de Pydantic no lo tiene y el
    servicio ya no sabe de que linea venia.
    """
    if datos.get("domain_plate") is None and datos.get("chassis_number") is None:
        raise _Rechazo(None, "hace falta al menos el dominio o el numero de chasis")


def _verificar_anio(anio: int) -> None:
    """`RN-ST-03`. El techo se calcula, no es constante: una constante quedaria
    vieja el 1 de enero y el sintoma seria que nadie puede cargar el 0 km."""
    maximo = dt.datetime.now(dt.UTC).year + 1
    if not ANIO_MINIMO <= anio <= maximo:
        raise _Rechazo("anio", f"tiene que estar entre {ANIO_MINIMO} y {maximo}")
