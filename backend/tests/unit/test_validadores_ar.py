"""Validadores del mercado argentino — C-04, bloque 2.

Cubre los escenarios de identidad fiscal de `tenancy/organization`:

  - "Identificacion fiscal con digito verificador incorrecto"
  - "Identificacion fiscal con prefijo inexistente"
  - "El mismo numero escrito de dos formas"

POR QUE EL VALIDADOR VIVE EN `core` Y NO EN `tenancy`
──────────────────────────────────────────────────────
`tenants.cuit` es el primer uso, no el ultimo: `contacts` (C-24) y las
operaciones de venta lo necesitan igual. Un validador por modulo termina siendo
tres implementaciones que difieren en los bordes (design.md D-9).

POR QUE NO ALCANZA CON VALIDAR EL DIGITO
──────────────────────────────────────────
Un numero puede tener digito verificador correcto y no ser un CUIT de nadie: el
prefijo codifica la categoria fiscal, y solo hay siete validos. `99-12345678-1`
pasa el modulo 11 y no lo reconoce ningun organismo. Si se acepta, el error no
aparece al cargarlo: aparece meses despues, en la factura.
"""

from __future__ import annotations

import pytest

from app.core.validadores_ar import (
    CuitInvalido,
    cuit_es_valido,
    normalizar_cuit,
)

# CUIT real de AFIP. Se usa a proposito uno verificable contra la realidad y no
# uno inventado: un caso de prueba fabricado con el mismo algoritmo que se esta
# probando no prueba que el algoritmo sea el correcto, solo que es consistente
# consigo mismo.
AFIP = "33-69345023-9"


class TestFormasDeEscribirlo:
    """El mismo numero, escrito distinto, es el mismo CUIT."""

    @pytest.mark.parametrize(
        "entrada",
        [
            "33-69345023-9",
            "33693450239",
            "  33-69345023-9  ",
            "33.69345023.9",
        ],
    )
    def test_se_normaliza_a_la_forma_canonica(self, entrada: str) -> None:
        assert normalizar_cuit(entrada) == "33-69345023-9"

    def test_la_forma_canonica_entra_en_la_columna(self) -> None:
        """`tenants.cuit` es varchar(13) — la forma canonica mide exactamente eso."""
        assert len(normalizar_cuit(AFIP)) == 13


class TestDigitoVerificador:
    @pytest.mark.parametrize("cuit", ["33-69345023-9", "20-12345678-6"])
    def test_cuit_valido_se_acepta(self, cuit: str) -> None:
        assert cuit_es_valido(cuit)

    @pytest.mark.parametrize("dv", [str(d) for d in range(10) if d != 9])
    def test_cualquier_otro_digito_verificador_se_rechaza(self, dv: str) -> None:
        """No basta con probar UN digito equivocado.

        Un validador roto que devolviera siempre True pasaria el test del caso
        valido. Recorrer los nueve digitos incorrectos deja sin lugar a esa
        implementacion.
        """
        assert not cuit_es_valido(f"33-69345023-{dv}")


class TestBordesDelAlgoritmo:
    """Los dos casos donde toda implementacion de CUIT se equivoca.

    El algoritmo hace `11 - (suma % 11)`, y ese resultado puede dar 11 o 10,
    que no son digitos. Cada uno tiene su regla:

      - resto 0  ->  11 - 0 = 11  ->  el digito es 0
      - resto 1  ->  11 - 1 = 10  ->  el digito es 9

    Una implementacion que ignore estos dos casos anda bien en 9 de cada 11
    CUIT, que es suficiente para que nadie lo note hasta que un cliente real no
    puede darse de alta.
    """

    def test_resto_cero_da_digito_cero(self) -> None:
        assert cuit_es_valido("20-10000013-0")

    def test_resto_uno_da_digito_nueve(self) -> None:
        assert cuit_es_valido("20-10000005-9")

    def test_el_borde_de_resto_cero_no_acepta_cualquier_cosa(self) -> None:
        """Contrapeso: que el caso de borde no se haya resuelto aceptando todo."""
        assert not cuit_es_valido("20-10000013-1")

    def test_el_borde_de_resto_uno_no_acepta_cualquier_cosa(self) -> None:
        assert not cuit_es_valido("20-10000005-0")


class TestPrefijoDeCategoria:
    """Solo siete prefijos existen. El resto no es CUIT de nadie."""

    @pytest.mark.parametrize("prefijo", ["20", "23", "24", "27", "30", "33", "34"])
    def test_los_prefijos_de_afip_se_aceptan(self, prefijo: str) -> None:
        assert cuit_es_valido(_con_digito(prefijo + "12345678"))

    def test_prefijo_inexistente_se_rechaza_aunque_el_digito_sea_correcto(self) -> None:
        """`99-12345678-1` supera el modulo 11 y no lo reconoce ningun organismo."""
        assert not cuit_es_valido("99-12345678-1")

    @pytest.mark.parametrize("prefijo", ["00", "01", "19", "21", "25", "31", "35", "99"])
    def test_los_prefijos_fuera_del_catalogo_se_rechazan(self, prefijo: str) -> None:
        assert not cuit_es_valido(_con_digito(prefijo + "12345678"))


class TestEntradasMalFormadas:
    @pytest.mark.parametrize(
        "entrada",
        [
            "",
            "   ",
            "33-69345023",  # 10 digitos
            "33-69345023-99",  # 12 digitos
            "AB-69345023-9",  # letras
            "33-6934502X-9",
            # Los dos que aceptaba la primera implementacion, que quitaba
            # separadores de cualquier posicion en vez de exigirlos en su lugar.
            "-33693450239",
            "3-3-6-9-3-4-5-0-2-3-9",
            "33693450239-",
            "33-693450239",  # separador en el lugar equivocado
            "336934502-39",
        ],
    )
    def test_se_rechazan(self, entrada: str) -> None:
        assert not cuit_es_valido(entrada)

    @pytest.mark.parametrize("entrada", ["", "33-69345023", "AB-69345023-9"])
    def test_normalizar_una_entrada_invalida_explota(self, entrada: str) -> None:
        """`normalizar_cuit` no devuelve basura normalizada.

        Devolver una cadena con forma de CUIT para una entrada invalida seria
        peor que fallar: la basura entraria a la base con la forma correcta.
        """
        with pytest.raises(CuitInvalido):
            normalizar_cuit(entrada)

    def test_el_mensaje_del_error_no_repite_el_valor(self) -> None:
        """Un CUIT es dato personal (Ley 25.326): no viaja en un mensaje de error."""
        with pytest.raises(CuitInvalido) as exc:
            normalizar_cuit("99-12345678-1")
        assert "99-12345678-1" not in str(exc.value)
        assert "99123456781" not in str(exc.value)


# ── Ayudante de los tests, no del codigo de produccion ───────────────────────

_MULTIPLICADORES = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def _con_digito(diez: str) -> str:
    """Completa diez digitos con su verificador.

    Se usa SOLO para los tests de prefijo, donde lo que se prueba es el
    catalogo de categorias y el digito tiene que estar bien para que el
    rechazo —cuando ocurre— sea atribuible al prefijo y no al digito.

    Deliberadamente NO se importa del codigo de produccion: si compartieran la
    implementacion, un error en el calculo se cancelaria contra si mismo y los
    tests seguirian verdes.
    """
    suma = sum(int(d) * m for d, m in zip(diez, _MULTIPLICADORES, strict=True))
    resto = suma % 11
    digito = 0 if resto == 0 else 9 if resto == 1 else 11 - resto
    return f"{diez[:2]}-{diez[2:]}-{digito}"
