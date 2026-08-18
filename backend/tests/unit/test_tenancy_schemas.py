"""Schemas del modulo tenancy — C-04, bloque 4.

Lo que se prueba aca es el contrato de ENTRADA: que valide lo que tiene que
validar y que rechace lo que nunca puede venir del cliente.

`tenant_id` NO SE ACEPTA DESDE EL BODY, Y SE RECHAZA EN VEZ DE IGNORARSE
─────────────────────────────────────────────────────────────────────────
La regla dura 1 dice que `tenant_id` se deriva del token y nunca del body. Hay
dos formas de cumplirla y no son equivalentes:

  - `extra="ignore"`  -> el campo se descarta en silencio, la peticion sigue
  - `extra="forbid"`  -> la peticion se rechaza con 422

Se eligio **`forbid`**. Ignorar en silencio cumple la regla —el valor no llega
a la base— pero le devuelve 200 a un cliente que acaba de intentar escribir en
otro tenant, y no deja rastro de que lo intento. Con `forbid` el intento es
visible: queda en los logs como un 422 con el nombre del campo.

El beneficio de arrastre es igual de importante: `forbid` tambien atrapa los
errores de tipeo. Un `billing_emial` con `ignore` se descarta sin decir nada y
la agencia queda sin email de facturacion, con la peticion en verde.

⚠️ Esto se desvia de como estaba redactada la tarea 4.4 ("lo ignora, no lo
aplica"). El cambio es a mas estricto y esta registrado en design.md D-10.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.tenancy.schemas import SucursalCrear, TenantCrear

CUIT_VALIDO = "33-69345023-9"


def _datos_de_agencia(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "name": "Automotores del Oeste",
        "slug": "automotores-del-oeste",
        "cuit": CUIT_VALIDO,
        "billing_email": "facturacion@example.com",
    }
    base.update(cambios)
    return base


class TestTenantCrear:
    def test_los_datos_minimos_alcanzan(self) -> None:
        agencia = TenantCrear(**_datos_de_agencia())
        assert agencia.name == "Automotores del Oeste"

    def test_el_cuit_se_normaliza_en_el_schema(self) -> None:
        """La validacion vive en el borde, no solo en la base.

        Sin esto el CUIT llega crudo al repositorio y el UNIQUE decide: el mismo
        numero con y sin guiones entra dos veces.
        """
        agencia = TenantCrear(**_datos_de_agencia(cuit="33693450239"))
        assert agencia.cuit == CUIT_VALIDO

    @pytest.mark.parametrize("cuit", ["33-69345023-0", "99-12345678-1", "no-es-un-cuit", ""])
    def test_un_cuit_invalido_no_construye_el_schema(self, cuit: str) -> None:
        with pytest.raises(ValidationError) as exc:
            TenantCrear(**_datos_de_agencia(cuit=cuit))
        assert "cuit" in str(exc.value)

    def test_el_error_de_cuit_no_repite_el_valor(self) -> None:
        """Ley 25.326: el CUIT es dato personal y no viaja en un mensaje de error.

        Pydantic incluye el valor en `input` del detalle, que es parte de su
        contrato; lo que se verifica es que el MENSAJE que escribimos nosotros
        no lo repita, porque ese es el que termina en el log.
        """
        with pytest.raises(ValidationError) as exc:
            TenantCrear(**_datos_de_agencia(cuit="99-12345678-1"))
        mensajes = [e["msg"] for e in exc.value.errors()]
        assert not any("99-12345678-1" in m for m in mensajes)

    @pytest.mark.parametrize("email", ["sin-arroba", "a@", "@example.com", ""])
    def test_un_email_de_facturacion_invalido_se_rechaza(self, email: str) -> None:
        with pytest.raises(ValidationError):
            TenantCrear(**_datos_de_agencia(billing_email=email))

    @pytest.mark.parametrize("slug", ["Con Mayusculas", "con espacios", "con_guion_bajo", "", "a"])
    def test_un_slug_mal_formado_se_rechaza(self, slug: str) -> None:
        """El slug va en una URL: si acepta cualquier cosa, la URL se rompe despues."""
        with pytest.raises(ValidationError):
            TenantCrear(**_datos_de_agencia(slug=slug))

    def test_las_preferencias_regionales_tienen_valor_argentino_por_defecto(self) -> None:
        agencia = TenantCrear(**_datos_de_agencia())
        assert agencia.timezone == "America/Argentina/Buenos_Aires"
        assert agencia.locale == "es-AR"


class TestElBodyNoDecideElTenant:
    """El unico test de este archivo que protege contra un ataque y no un typo."""

    def test_tenant_id_en_el_body_se_rechaza(self) -> None:
        with pytest.raises(ValidationError) as exc:
            SucursalCrear(  # type: ignore[call-arg]
                name="Sucursal Centro",
                city="Mendoza",
                province="Mendoza",
                tenant_id="00000000-0000-0000-0000-000000000001",
            )
        assert "tenant_id" in str(exc.value)

    def test_tampoco_al_crear_una_agencia(self) -> None:
        with pytest.raises(ValidationError):
            TenantCrear(**_datos_de_agencia(tenant_id="00000000-0000-0000-0000-000000000001"))

    def test_el_schema_de_entrada_no_declara_el_campo(self) -> None:
        """El contrapeso de los dos de arriba.

        Aquellos pasarian igual si `tenant_id` estuviera declarado y `forbid` no
        aplicara — el rechazo vendria de otro lado. Este fija que el campo
        directamente NO existe en el contrato de entrada.
        """
        assert "tenant_id" not in SucursalCrear.model_fields
        assert "tenant_id" not in TenantCrear.model_fields

    def test_un_campo_mal_escrito_tambien_se_rechaza(self) -> None:
        """`forbid` atrapa el typo, no solo el ataque.

        Con `ignore`, `billing_emial` se descarta sin decir nada y la agencia
        queda sin email de facturacion con la peticion en verde.
        """
        with pytest.raises(ValidationError) as exc:
            TenantCrear(  # type: ignore[call-arg]
                name="Automotores del Oeste",
                slug="automotores-del-oeste",
                cuit=CUIT_VALIDO,
                billing_emial="facturacion@example.com",
            )
        assert "billing_emial" in str(exc.value)


class TestSucursalCrear:
    def test_los_datos_minimos_alcanzan(self) -> None:
        sucursal = SucursalCrear(name="Casa Central", city="Mendoza", province="Mendoza")
        assert sucursal.name == "Casa Central"

    @pytest.mark.parametrize("campo", ["name", "city", "province"])
    def test_los_campos_obligatorios_lo_son(self, campo: str) -> None:
        datos = {"name": "Casa Central", "city": "Mendoza", "province": "Mendoza"}
        del datos[campo]
        with pytest.raises(ValidationError):
            SucursalCrear(**datos)

    @pytest.mark.parametrize("vacio", ["", "   "])
    def test_un_nombre_en_blanco_no_es_un_nombre(self, vacio: str) -> None:
        with pytest.raises(ValidationError):
            SucursalCrear(name=vacio, city="Mendoza", province="Mendoza")
