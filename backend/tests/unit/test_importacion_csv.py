"""El lector de planillas de stock — C-17, `T-093`.

POR QUE ESTOS TESTS SON DE UNIDAD Y NO DE INTEGRACION
──────────────────────────────────────────────────────
Leer la planilla no toca la base. Resolver marca, modelo y sucursal contra el
catalogo si, y eso vive en otro lado. La separacion no es estetica: **el riesgo
de este change esta casi entero en el parseo**, y un test que necesita
PostgreSQL para probar que "1.250.000,50" es un millon doscientos cincuenta mil
tarda diez veces mas y falla por motivos que no son el que se prueba.

CONTRA QUE SE PRUEBA, DE VERDAD
────────────────────────────────
El producto compite contra Excel. Entonces el archivo que va a llegar no es un
CSV de manual: es un `Guardar como → CSV` de un Excel en español, con BOM,
separador `;`, precios con punto de miles y coma decimal, y encabezados con
mayusculas y acentos puestos a mano. Un lector que solo entienda el CSV canonico
funciona en los tests y falla con el primer cliente.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.stock.importacion import (
    COLUMNAS_OBLIGATORIAS,
    LIMITE_DE_BYTES,
    LIMITE_DE_FILAS,
    PLANTILLA,
    ArchivoIlegible,
    leer_planilla,
)

CABECERA = "marca,modelo,anio,kilometros,color,combustible,transmision,carroceria,precio_ars,dominio,chasis,sucursal,version,numero_de_motor,precio_usd,costo_de_adquisicion_ars,descripcion"

FILA = "Toyota,Hilux,2021,30000,Blanco,diesel,manual,pickup,25000000.00,AA123BB,,,,,,,"


def _planilla(*filas: str, cabecera: str = CABECERA) -> bytes:
    return ("\r\n".join([cabecera, *filas]) + "\r\n").encode("utf-8")


# ── El camino feliz, y lo que "feliz" significa ─────────────────────────────


def test_una_fila_valida_se_lee_entera() -> None:
    lectura = leer_planilla(_planilla(FILA))

    assert lectura.errores == []
    assert len(lectura.filas) == 1
    fila = lectura.filas[0]
    assert (fila.marca, fila.modelo) == ("Toyota", "Hilux")
    assert fila.datos["year"] == 2021
    assert fila.datos["price_ars"] == Decimal("25000000.00")
    assert fila.datos["domain_plate"] == "AA123BB"


def test_la_plantilla_que_se_descarga_se_puede_volver_a_leer() -> None:
    """La prueba mas barata de que la plantilla no quedo vieja.

    Si alguien agrega una columna obligatoria y se olvida de la plantilla, el
    cliente descarga un archivo que el sistema rechaza. Acá eso falla.
    """
    lectura = leer_planilla(PLANTILLA.encode("utf-8"))

    assert lectura.errores == []
    assert len(lectura.filas) >= 1


# ── Lo que manda Excel de verdad ────────────────────────────────────────────


def test_el_csv_de_excel_en_espanol_se_entiende() -> None:
    """BOM, separador `;`, precio `1.250.000,50` y encabezados con mayusculas.

    Los cuatro juntos, porque asi llegan: es un solo `Guardar como` de Excel y
    no cuatro variantes independientes.
    """
    cabecera = CABECERA.upper().replace(",", ";")
    fila = "Toyota;Hilux;2021;30.000;Blanco;diesel;manual;pickup;1.250.000,50;AA123BB;;;;;;;"
    contenido = ("\r\n".join([cabecera, fila]) + "\r\n").encode("utf-8-sig")

    lectura = leer_planilla(contenido)

    assert lectura.errores == []
    assert lectura.filas[0].datos["price_ars"] == Decimal("1250000.50")
    assert lectura.filas[0].datos["mileage_km"] == 30000


def test_un_archivo_en_windows_1252_no_se_rechaza() -> None:
    """Excel viejo guarda en la codificacion del sistema, no en UTF-8.

    `Citroën` en cp1252 no es UTF-8 valido. Reventar ahi seria rechazar el
    archivo entero por un acento.
    """
    contenido = ("\r\n".join([CABECERA, FILA.replace("Blanco", "Marrón")])).encode("cp1252")

    lectura = leer_planilla(contenido)

    assert lectura.errores == []
    assert lectura.filas[0].datos["color"] == "Marrón"


def test_las_columnas_opcionales_pueden_no_estar() -> None:
    """Basta con las obligatorias mas UNA identificatoria."""
    cabecera = ",".join([*COLUMNAS_OBLIGATORIAS, "dominio"])
    fila = "Toyota,Hilux,2021,30000,Blanco,diesel,manual,pickup,25000000.00,AA123BB"

    lectura = leer_planilla(_planilla(fila, cabecera=cabecera))

    assert lectura.errores == []
    assert lectura.filas[0].datos["chassis_number"] is None
    assert lectura.filas[0].sucursal is None


def test_una_planilla_sin_dominio_ni_chasis_en_la_cabecera_se_rechaza_entera() -> None:
    """`ADR-031` a nivel de archivo.

    Sin ninguna de las dos columnas no hay una fila que pueda salir bien: serian
    5.000 errores identicos. Es un problema de la planilla, y decirlo una vez
    vale mas que decirlo cinco mil.
    """
    cabecera = ",".join(COLUMNAS_OBLIGATORIAS)
    fila = "Toyota,Hilux,2021,30000,Blanco,diesel,manual,pickup,25000000.00"

    with pytest.raises(ArchivoIlegible, match="dominio"):
        leer_planilla(_planilla(fila, cabecera=cabecera))


# ── Errores por fila: la planilla no se rechaza entera ──────────────────────


def test_una_fila_mala_no_arrastra_a_las_buenas() -> None:
    """`RN-ST-13`. 5.000 filas con 12 errores es un exito con 12 correcciones."""
    mala = FILA.replace("2021", "no-es-un-anio")

    lectura = leer_planilla(_planilla(FILA, mala, FILA.replace("AA123BB", "AA124BB")))

    assert len(lectura.filas) == 2
    assert len(lectura.errores) == 1


def test_el_numero_de_fila_es_el_que_muestra_excel() -> None:
    """La cabecera es la fila 1, asi que el primer dato es la 2.

    Contar desde 0 obligaria al usuario a hacer la traduccion en la cabeza
    mientras corrige un archivo de miles de lineas.
    """
    lectura = leer_planilla(_planilla(FILA, FILA.replace("2021", "x")))

    assert lectura.errores[0].fila == 3


def test_el_error_nombra_la_columna() -> None:
    lectura = leer_planilla(_planilla(FILA.replace("diesel", "querosene")))

    assert lectura.errores[0].columna == "combustible"


def test_una_fila_sin_dominio_ni_chasis_se_rechaza() -> None:
    """`ADR-031`: el dominio es opcional, pero identificarse no."""
    sin_ninguno = FILA.replace(",AA123BB,", ",,")

    lectura = leer_planilla(_planilla(sin_ninguno))

    assert lectura.filas == []
    assert "dominio" in lectura.errores[0].mensaje


def test_una_fila_sin_dominio_pero_con_chasis_pasa() -> None:
    con_chasis = FILA.replace(",AA123BB,,", ",,8AWZZZ377VA123456,")

    lectura = leer_planilla(_planilla(con_chasis))

    assert lectura.errores == []
    assert lectura.filas[0].datos["chassis_number"] == "8AWZZZ377VA123456"


def test_una_fila_vacia_se_saltea_sin_ser_un_error() -> None:
    """Excel deja lineas en blanco al final. No son filas mal cargadas."""
    lectura = leer_planilla(_planilla(FILA, "", ",,,,,,,,,,,,,,,,"))

    assert len(lectura.filas) == 1
    assert lectura.errores == []


# ── Lo que si rechaza el archivo entero ─────────────────────────────────────


def test_falta_una_columna_obligatoria_y_no_se_lee_nada() -> None:
    """Un error por fila x 5.000 filas no es un reporte, es ruido.

    Si falta `precio_ars` no fallan algunas filas: falla la planilla, y el
    mensaje tiene que decir cual columna para que se pueda arreglar de una.
    """
    cabecera = CABECERA.replace("precio_ars,", "")

    with pytest.raises(ArchivoIlegible, match="precio_ars"):
        leer_planilla(_planilla(FILA, cabecera=cabecera))


def test_mas_filas_que_el_maximo_se_rechaza_antes_de_parsear() -> None:
    """`RN-ST-13`: 5.000 filas. Se cuenta antes de validar nada."""
    contenido = _planilla(*[FILA] * (LIMITE_DE_FILAS + 1))

    with pytest.raises(ArchivoIlegible, match=str(LIMITE_DE_FILAS)):
        leer_planilla(contenido)


def test_un_archivo_vacio_se_rechaza_con_un_mensaje_util() -> None:
    with pytest.raises(ArchivoIlegible):
        leer_planilla(b"")


def test_un_archivo_binario_no_revienta_con_un_error_de_codificacion() -> None:
    """Alguien sube el .xlsx en vez del .csv. Tiene que ser un rechazo legible."""
    with pytest.raises(ArchivoIlegible):
        leer_planilla(b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + bytes(range(256)) * 4)


def test_un_csv_guardado_como_unicode_por_excel_se_rechaza() -> None:
    """UTF-16 es el caso que ninguna codificacion detecta por su cuenta.

    Excel ofrece "Texto Unicode (*.txt)" y eso sale en UTF-16LE. Como cp1252
    mapea casi cualquier byte, decodifica **sin error** y devuelve
    `m\x00a\x00r\x00c\x00a` — texto valido para Python y basura para quien lo
    subio. El resultado seria una planilla "leida" con cero filas y ningun
    mensaje: la peor forma de fallar, que es en silencio.

    Lo que lo delata es el byte nulo. Y lo que se afirma acá es EL MENSAJE, no
    que levante: sin el chequeo del nulo el archivo igual se rechaza —los
    encabezados quedan como `m\x00a\x00r\x00c\x00a` y no matchean— pero
    diciendo *"faltan columnas obligatorias: marca, modelo, anio…"*. O sea,
    mandando a agregar nueve columnas que ya estan. Ese mensaje cuesta una
    tarde.
    """
    contenido = (CABECERA + "\r\n" + FILA + "\r\n").encode("utf-16-le")

    with pytest.raises(ArchivoIlegible) as fallo:
        leer_planilla(contenido)

    assert "columnas" not in str(fallo.value)


# ── Normalizacion ───────────────────────────────────────────────────────────


def test_el_dominio_se_normaliza_como_en_el_alta_por_api() -> None:
    """Misma funcion que `VehiculoCrear`, no una copia.

    Dos normalizadores para un mismo dato terminan divergiendo, y el sintoma es
    que un vehiculo cargado por planilla y otro por formulario no chocan entre
    si aunque tengan la misma patente.
    """
    lectura = leer_planilla(_planilla(FILA.replace("AA123BB", " aa 123 bb ")))

    assert lectura.filas[0].datos["domain_plate"] == "AA123BB"


def test_los_espacios_de_sobra_no_rompen_los_enums() -> None:
    lectura = leer_planilla(_planilla(FILA.replace(",diesel,", ", Diesel ,")))

    assert lectura.errores == []
    assert lectura.filas[0].datos["fuel_type"] == "diesel"


def test_la_sucursal_y_la_version_viajan_por_nombre() -> None:
    """La planilla la llena una persona, que no conoce ningun UUID."""
    fila = FILA.replace("AA123BB,,,", "AA123BB,,Casa central,SRV,")

    lectura = leer_planilla(_planilla(fila))

    assert lectura.filas[0].sucursal == "Casa central"
    assert lectura.filas[0].version == "SRV"


# ── Los rechazos que faltaban ───────────────────────────────────────────────


def test_un_archivo_de_mas_de_10_mb_se_rechaza_sin_leerlo() -> None:
    """`RN-ST-13`. Se mide en bytes, antes de decodificar: un archivo de 200 MB
    no se pasa a `str` para despues avisar que era muy grande."""
    with pytest.raises(ArchivoIlegible, match="10 MB"):
        leer_planilla(b"x" * (LIMITE_DE_BYTES + 1))


@pytest.mark.parametrize("columna", ["marca", "modelo"])
def test_sin_marca_o_sin_modelo_la_fila_se_rechaza(columna: str) -> None:
    """Sin estos dos no hay contra que resolver el catalogo. No es un default
    razonable: es una fila que no describe ningun vehiculo."""
    valor = "Toyota" if columna == "marca" else "Hilux"

    lectura = leer_planilla(_planilla(FILA.replace(valor, "", 1)))

    assert lectura.filas == []
    assert lectura.errores[0].columna == columna


def test_un_precio_que_no_es_numero_nombra_su_columna() -> None:
    lectura = leer_planilla(_planilla(FILA.replace("25000000.00", "a consultar")))

    assert lectura.errores[0].columna == "precio_ars"
    assert "a consultar" in lectura.errores[0].mensaje


def test_un_dominio_con_formato_invalido_se_rechaza_por_fila() -> None:
    """Y no revienta la planilla: es un dato malo, no un archivo malo."""
    lectura = leer_planilla(_planilla(FILA, FILA.replace("AA123BB", "PATENTE-1")))

    assert len(lectura.filas) == 1
    assert lectura.errores[0].columna == "dominio"


def test_un_chasis_con_formato_invalido_se_rechaza_por_fila() -> None:
    """El VIN no lleva I, O ni Q — se confunden con 1 y 0."""
    con_chasis = FILA.replace(",AA123BB,,", ",,IOQZZZ377VA123456,")

    lectura = leer_planilla(_planilla(con_chasis))

    assert lectura.errores[0].columna == "chasis"


@pytest.mark.parametrize("anio", ["1900", "2999"])
def test_un_anio_fuera_de_rango_se_rechaza(anio: str) -> None:
    """`RN-ST-03`. El piso es fijo; el techo se calcula sobre el año en curso."""
    lectura = leer_planilla(_planilla(FILA.replace("2021", anio)))

    assert lectura.filas == []
    assert lectura.errores[0].columna == "anio"
