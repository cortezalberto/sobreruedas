"""Repositorio y servicio de tenancy — C-04, bloque 5.

Cubre los escenarios de `tenancy/organization` que no son de identidad fiscal
—esos estan en `tests/unit/test_validadores_ar.py`— mas los tres de
aislamiento de sucursales.

Contra PostgreSQL real (regla dura 8). Los tres de aislamiento no se pueden
probar de otra forma: lo que verifican es que la POLITICA RLS actue, y un mock
de base no tiene politicas.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError

from app.core.errors import DomainError, PlanQuotaExceeded
from app.db.session import sesion_de_plataforma, sesion_de_tenant
from app.modules.tenancy.models import Branch, Tenant
from app.modules.tenancy.repository import BranchRepository, TenantRepository
from app.modules.tenancy.schemas import SucursalCrear, TenantCrear
from app.modules.tenancy.service import TenancyService

from .soporte import DSN_APLICACION, sesion_de_propietario

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("base_migrada")]

_MULTIPLICADORES = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def _cuit_valido() -> str:
    """Un CUIT distinto por llamada. Ver el encabezado de `test_plan_limits`."""
    diez = f"30{uuid.uuid4().int % 100_000_000:08d}"
    suma = sum(int(d) * m for d, m in zip(diez, _MULTIPLICADORES, strict=True))
    resto = suma % 11
    digito = 0 if resto == 0 else 9 if resto == 1 else 11 - resto
    return f"{diez[:2]}-{diez[2:]}-{digito}"


def _alta(**cambios: object) -> TenantCrear:
    datos: dict[str, object] = {
        "name": "Automotores del Oeste",
        "slug": f"agencia-{uuid.uuid4().hex[:12]}",
        "cuit": _cuit_valido(),
        "billing_email": "facturacion@example.com",
    }
    datos.update(cambios)
    return TenantCrear(**datos)


# ── Alta de la agencia ──────────────────────────────────────────────────────


class TestAltaDeAgencia:
    async def test_una_agencia_nueva_queda_creada(self) -> None:
        async with sesion_de_propietario() as sesion:
            agencia = await TenancyService(sesion).crear_agencia(_alta())
        assert agencia.id is not None

    async def test_las_preferencias_regionales_son_argentinas_por_defecto(self) -> None:
        """Escenario "Agencia creada sin especificar preferencias regionales"."""
        async with sesion_de_propietario() as sesion:
            agencia = await TenancyService(sesion).crear_agencia(_alta())
            await sesion.refresh(agencia)
        assert agencia.timezone == "America/Argentina/Buenos_Aires"
        assert agencia.locale == "es-AR"

    async def test_una_agencia_nueva_nace_en_trial(self) -> None:
        """Nace sin plan y en trial: elegir plan es un paso posterior, y forzar
        un plan ficticio para satisfacer un NOT NULL seria peor (design.md D-8).
        """
        async with sesion_de_propietario() as sesion:
            agencia = await TenancyService(sesion).crear_agencia(_alta())
            await sesion.refresh(agencia)
        assert agencia.status == "trial"
        assert agencia.plan_id is None


class TestDuplicados:
    async def test_el_cuit_duplicado_se_rechaza(self) -> None:
        cuit = _cuit_valido()
        async with sesion_de_propietario() as sesion:
            await TenancyService(sesion).crear_agencia(_alta(cuit=cuit))
        async with sesion_de_propietario() as sesion:
            with pytest.raises(DomainError) as exc:
                await TenancyService(sesion).crear_agencia(_alta(cuit=cuit))
        assert exc.value.code == "cuit_duplicado"

    async def test_el_mismo_cuit_escrito_de_otra_forma_tambien_se_rechaza(self) -> None:
        """Escenario "El mismo numero escrito de dos formas".

        Es el que hace util a la normalizacion: sin ella el UNIQUE no ve el
        duplicado y quedan dos agencias que para AFIP son la misma.
        """
        cuit = _cuit_valido()
        async with sesion_de_propietario() as sesion:
            await TenancyService(sesion).crear_agencia(_alta(cuit=cuit))
        async with sesion_de_propietario() as sesion:
            with pytest.raises(DomainError) as exc:
                await TenancyService(sesion).crear_agencia(_alta(cuit=cuit.replace("-", "")))
        assert exc.value.code == "cuit_duplicado"

    async def test_el_slug_duplicado_se_rechaza(self) -> None:
        slug = f"agencia-{uuid.uuid4().hex[:12]}"
        async with sesion_de_propietario() as sesion:
            await TenancyService(sesion).crear_agencia(_alta(slug=slug))
        async with sesion_de_propietario() as sesion:
            with pytest.raises(DomainError) as exc:
                await TenancyService(sesion).crear_agencia(_alta(slug=slug))
        assert exc.value.code == "slug_duplicado"

    async def test_el_rechazo_distingue_cual_de_los_dos_choco(self) -> None:
        """Un "ya existe" a secas obliga al usuario a adivinar cual cambiar."""
        cuit, slug = _cuit_valido(), f"agencia-{uuid.uuid4().hex[:12]}"
        async with sesion_de_propietario() as sesion:
            await TenancyService(sesion).crear_agencia(_alta(cuit=cuit, slug=slug))
        async with sesion_de_propietario() as sesion:
            with pytest.raises(DomainError) as exc:
                await TenancyService(sesion).crear_agencia(_alta(cuit=cuit))
            assert exc.value.code == "cuit_duplicado"
        async with sesion_de_propietario() as sesion:
            with pytest.raises(DomainError) as exc:
                await TenancyService(sesion).crear_agencia(_alta(slug=slug))
            assert exc.value.code == "slug_duplicado"


# ── Baja recuperable ────────────────────────────────────────────────────────


class TestBajaDeAgencia:
    async def test_la_fila_sobrevive_a_la_baja(self) -> None:
        """Escenario "Baja de una agencia". Principio 3: nunca borrado fisico."""
        async with sesion_de_propietario() as sesion:
            agencia = await TenancyService(sesion).crear_agencia(_alta())
            agencia_id = agencia.id
            await TenancyService(sesion).dar_de_baja_agencia(agencia_id)

        async with sesion_de_propietario() as sesion:
            fila = (
                await sesion.execute(select(Tenant).where(Tenant.id == agencia_id))
            ).scalar_one()
            assert fila.deleted_at is not None

    async def test_deja_de_aparecer_en_el_listado_ordinario(self) -> None:
        async with sesion_de_propietario() as sesion:
            servicio = TenancyService(sesion)
            agencia = await servicio.crear_agencia(_alta())
            await servicio.dar_de_baja_agencia(agencia.id)
            vivas = await TenantRepository(sesion).listar()
        assert agencia.id not in {a.id for a in vivas}

    async def test_pero_se_puede_pedir_explicitamente(self) -> None:
        """El contrapeso: que "no aparece" sea un filtro y no una desaparicion.

        Sin este test, un repositorio que borrara de verdad pasaria el anterior.
        """
        async with sesion_de_propietario() as sesion:
            servicio = TenancyService(sesion)
            agencia = await servicio.crear_agencia(_alta())
            await servicio.dar_de_baja_agencia(agencia.id)
            todas = await TenantRepository(sesion).listar(incluir_dadas_de_baja=True)
        assert agencia.id in {a.id for a in todas}

    async def test_el_cuit_de_una_agencia_dada_de_baja_sigue_ocupado(self) -> None:
        """Escenario "El identificador no se libera con la baja".

        Reasignar el CUIT de una agencia dada de baja rompe la trazabilidad
        fiscal de lo que esa agencia facturo.
        """
        cuit = _cuit_valido()
        async with sesion_de_propietario() as sesion:
            servicio = TenancyService(sesion)
            agencia = await servicio.crear_agencia(_alta(cuit=cuit))
            await servicio.dar_de_baja_agencia(agencia.id)

        async with sesion_de_propietario() as sesion:
            with pytest.raises(DomainError) as exc:
                await TenancyService(sesion).crear_agencia(_alta(cuit=cuit))
        assert exc.value.code == "cuit_duplicado"

    async def test_dar_de_baja_una_agencia_inexistente_falla_de_forma_legible(self) -> None:
        async with sesion_de_propietario() as sesion:
            with pytest.raises(DomainError) as exc:
                await TenancyService(sesion).dar_de_baja_agencia(uuid.uuid4())
        assert exc.value.code == "tenant_inexistente"


# ── Aislamiento de sucursales ───────────────────────────────────────────────


async def _agencia_con_plan(codigo: str) -> uuid.UUID:
    """Crea una agencia y le asigna un plan, para poder ejercitar la cuota."""
    async with sesion_de_propietario() as sesion:
        servicio = TenancyService(sesion)
        agencia = await servicio.crear_agencia(_alta())
        await servicio.asignar_plan(agencia.id, codigo)
        return agencia.id


class TestAislamientoDeSucursales:
    async def test_una_agencia_solo_ve_sus_sucursales(self) -> None:
        """Escenario "Dos agencias con sucursales"."""
        una = await _agencia_con_plan("pro")
        otra = await _agencia_con_plan("pro")

        async with sesion_de_tenant(una, dsn=DSN_APLICACION) as sesion:
            await TenancyService(sesion).crear_sucursal(
                una, SucursalCrear(name="De una", city="Mendoza", province="Mendoza")
            )
        async with sesion_de_tenant(otra, dsn=DSN_APLICACION) as sesion:
            await TenancyService(sesion).crear_sucursal(
                otra, SucursalCrear(name="De la otra", city="Cordoba", province="Cordoba")
            )

        async with sesion_de_tenant(una, dsn=DSN_APLICACION) as sesion:
            visibles = await BranchRepository(sesion).listar(una)
        assert [s.name for s in visibles] == ["De una"]

    async def test_sin_contexto_no_se_ve_ninguna_sucursal(self) -> None:
        """Escenario "Consulta de sucursales sin contexto" (`RN-MT-06`).

        Sin contexto la respuesta es cero filas, no todas: el fallo es visible
        y no silencioso.
        """
        agencia = await _agencia_con_plan("pro")
        async with sesion_de_tenant(agencia, dsn=DSN_APLICACION) as sesion:
            await TenancyService(sesion).crear_sucursal(
                agencia, SucursalCrear(name="Casa Central", city="Mendoza", province="Mendoza")
            )

        # Primero se comprueba que HAY filas. Sin esto el test es vacuo: una
        # tabla vacia devuelve cero con contexto y sin el, y el verde no
        # probaria que la politica actua — probaria que no hay datos.
        async with sesion_de_propietario() as sesion:
            total = len((await sesion.execute(select(Branch))).scalars().all())
        assert total > 0

        async with sesion_de_plataforma(dsn=DSN_APLICACION) as sesion:
            filas = (await sesion.execute(select(Branch))).scalars().all()
        assert filas == []

    async def test_crear_una_sucursal_para_otro_tenant_se_rechaza(self) -> None:
        """Escenario "Escritura de una sucursal en otra agencia".

        Lo que lo frena es el `WITH CHECK` de la politica, y se verifica que sea
        ESE el motivo: `pytest.raises(Exception)` a secas pasaria igual si la
        peticion muriera por una FK rota, por la cuota del plan o por un typo
        en el test, y el verde no diria nada sobre el aislamiento.
        """
        una = await _agencia_con_plan("pro")
        otra = await _agencia_con_plan("pro")

        async with sesion_de_tenant(una, dsn=DSN_APLICACION) as sesion:
            with pytest.raises(ProgrammingError) as exc:
                await TenancyService(sesion).crear_sucursal(
                    otra, SucursalCrear(name="Intrusa", city="Mendoza", province="Mendoza")
                )
        # `InsufficientPrivilegeError` es como PostgreSQL reporta el rechazo de
        # una politica RLS en la escritura.
        assert "InsufficientPrivilege" in str(exc.value)

        async with sesion_de_tenant(otra, dsn=DSN_APLICACION) as sesion:
            visibles = await BranchRepository(sesion).listar(otra)
        assert [s.name for s in visibles] == []


# ── La cuota se aplica al crear, no solo al preguntar ───────────────────────


class TestLaCuotaFrenaLaCreacion:
    async def test_superar_el_limite_no_crea_la_fila(self) -> None:
        """Segunda mitad de la tarea 6.2.

        `PlanLimitsService` ya tenia probado que RECHAZA. Lo que faltaba probar
        es que el servicio lo consulte ANTES de escribir — un limite que se
        verifica despues del INSERT no es un limite.
        """
        agencia = await _agencia_con_plan("starter")  # 1 sucursal

        async with sesion_de_tenant(agencia, dsn=DSN_APLICACION) as sesion:
            await TenancyService(sesion).crear_sucursal(
                agencia, SucursalCrear(name="Casa Central", city="Mendoza", province="Mendoza")
            )

        async with sesion_de_tenant(agencia, dsn=DSN_APLICACION) as sesion:
            with pytest.raises(PlanQuotaExceeded):
                await TenancyService(sesion).crear_sucursal(
                    agencia, SucursalCrear(name="La segunda", city="Mendoza", province="Mendoza")
                )

        async with sesion_de_tenant(agencia, dsn=DSN_APLICACION) as sesion:
            visibles = await BranchRepository(sesion).listar(agencia)
        assert [s.name for s in visibles] == ["Casa Central"]

    async def test_dar_de_baja_una_sucursal_libera_el_lugar(self) -> None:
        agencia = await _agencia_con_plan("starter")

        async with sesion_de_tenant(agencia, dsn=DSN_APLICACION) as sesion:
            servicio = TenancyService(sesion)
            sucursal = await servicio.crear_sucursal(
                agencia, SucursalCrear(name="Casa Central", city="Mendoza", province="Mendoza")
            )
            await servicio.dar_de_baja_sucursal(agencia, sucursal.id)
            await servicio.crear_sucursal(
                agencia, SucursalCrear(name="La nueva", city="Mendoza", province="Mendoza")
            )

        async with sesion_de_tenant(agencia, dsn=DSN_APLICACION) as sesion:
            visibles = await BranchRepository(sesion).listar(agencia)
        assert [s.name for s in visibles] == ["La nueva"]


class TestExtensionesDeLaBase:
    """Tarea 3.1. La extension existe porque una columna del esquema la exige."""

    async def test_postgis_queda_instalada(self) -> None:
        """`branches.geo_point` es `geography(Point,4326)` y no compila sin PostGIS.

        Estaba DISPONIBLE en la imagen desde el primer dia y nunca creada — es
        el hueco que encontro C-04. Un test lo fija: si alguien reordena las
        migraciones y `004` queda despues de `007`, la de `branches` revienta,
        pero este test dice por que.
        """
        async with sesion_de_propietario() as sesion:
            instalada = (
                await sesion.execute(
                    text("SELECT count(*) FROM pg_extension WHERE extname = 'postgis'")
                )
            ).scalar_one()
        assert instalada == 1

    async def test_la_columna_geografica_existe_con_su_tipo(self) -> None:
        """El contrapeso: la extension instalada no prueba que la columna se creo.

        `geo_point` se agrega con DDL crudo (design.md D-4), fuera del
        `create_table`. Si ese `ALTER` se perdiera en un merge, la extension
        seguiria instalada y el test de arriba pasaria igual.
        """
        async with sesion_de_propietario() as sesion:
            tipo = (
                await sesion.execute(
                    text(
                        "SELECT udt_name FROM information_schema.columns "
                        "WHERE table_name = 'branches' AND column_name = 'geo_point'"
                    )
                )
            ).scalar_one_or_none()
        assert tipo == "geography"


class TestCicloDeEstados:
    """Cobertura de `cambiar_estado` y `asignar_plan`, que la primera pasada
    dejo sin ningun test — lo delato el reporte de cobertura, no una revision.
    """

    @pytest.mark.parametrize("estado", ["active", "suspended", "trial", "cancelled"])
    async def test_los_cuatro_estados_del_enum_se_aceptan(self, estado: str) -> None:
        async with sesion_de_propietario() as sesion:
            servicio = TenancyService(sesion)
            agencia = await servicio.crear_agencia(_alta())
            await servicio.cambiar_estado(agencia.id, estado)
            assert agencia.status == estado

    @pytest.mark.parametrize("estado", ["activo", "ACTIVE", "", "deleted"])
    async def test_un_estado_fuera_del_enum_se_rechaza(self, estado: str) -> None:
        """Sin esto, un estado inventado llegaria al INSERT y saldria como 500.

        El enum de PostgreSQL lo frenaria igual, pero como error tecnico: el
        rechazo tiene que ser de dominio y nombrar el campo.
        """
        async with sesion_de_propietario() as sesion:
            servicio = TenancyService(sesion)
            agencia = await servicio.crear_agencia(_alta())
            with pytest.raises(DomainError) as exc:
                await servicio.cambiar_estado(agencia.id, estado)
        assert exc.value.code == "estado_invalido"

    async def test_cambiar_el_estado_de_una_agencia_inexistente_falla_legible(self) -> None:
        async with sesion_de_propietario() as sesion:
            with pytest.raises(DomainError) as exc:
                await TenancyService(sesion).cambiar_estado(uuid.uuid4(), "active")
        assert exc.value.code == "tenant_inexistente"

    async def test_asignar_plan_deja_la_agencia_activa(self) -> None:
        """Salir del trial es lo que convierte una prueba en un cliente."""
        async with sesion_de_propietario() as sesion:
            servicio = TenancyService(sesion)
            agencia = await servicio.crear_agencia(_alta())
            assert agencia.status == "trial"
            await servicio.asignar_plan(agencia.id, "pro")
        assert agencia.status == "active"
        assert agencia.plan_id is not None

    async def test_asignar_un_plan_que_no_existe_se_rechaza(self) -> None:
        """Un codigo de plan mal escrito dejaria `plan_id` en NULL, y un tenant
        sin plan se trata como SIN TECHO — el typo regalaria el producto entero.
        """
        async with sesion_de_propietario() as sesion:
            servicio = TenancyService(sesion)
            agencia = await servicio.crear_agencia(_alta())
            with pytest.raises(DomainError) as exc:
                await servicio.asignar_plan(agencia.id, "platino")
        assert exc.value.code == "plan_inexistente"


class TestBusquedaYBajasInexistentes:
    async def test_se_encuentra_por_slug(self) -> None:
        async with sesion_de_propietario() as sesion:
            servicio = TenancyService(sesion)
            agencia = await servicio.crear_agencia(_alta())
            hallada = await TenantRepository(sesion).obtener_por_slug(agencia.slug)
        assert hallada is not None
        assert hallada.id == agencia.id

    async def test_una_agencia_dada_de_baja_no_se_encuentra_por_slug(self) -> None:
        """El filtro de soft delete tambien aplica a la busqueda por slug.

        Si no aplicara, el slug de una agencia cancelada seguiria resolviendo a
        su portal.
        """
        async with sesion_de_propietario() as sesion:
            servicio = TenancyService(sesion)
            agencia = await servicio.crear_agencia(_alta())
            await servicio.dar_de_baja_agencia(agencia.id)
            hallada = await TenantRepository(sesion).obtener_por_slug(agencia.slug)
        assert hallada is None

    async def test_dar_de_baja_una_sucursal_inexistente_falla_legible(self) -> None:
        agencia = await _agencia_con_plan("pro")
        async with sesion_de_tenant(agencia, dsn=DSN_APLICACION) as sesion:
            with pytest.raises(DomainError) as exc:
                await TenancyService(sesion).dar_de_baja_sucursal(agencia, uuid.uuid4())
        assert exc.value.code == "sucursal_inexistente"


class TestUnaViolacionDesconocidaNoSeDisfraza:
    async def test_una_fk_rota_no_sale_como_duplicado(self) -> None:
        """`_traducir` solo traduce lo que sabe nombrar.

        Traducir a ciegas convertiria esta FK rota en un "ya existe", que manda
        a mirar el lugar equivocado. Tiene que subir como `IntegrityError`.

        La primera version de este test hacia `sesion.flush()` directo y por lo
        tanto **no pasaba por `_grabar()`**: afirmaba algo cierto sin ejercitar
        el camino que decia cubrir. Lo delato la cobertura, que dejaba viva la
        linea del `raise`.

        Se entra por `crear_sucursal` con un tenant que NO existe: el
        `WITH CHECK` de la politica lo deja pasar —el `tenant_id` coincide con
        el contexto— y despues revienta la FK, que es exactamente la violacion
        que `_traducir` no sabe nombrar.
        """
        from sqlalchemy.exc import IntegrityError

        fantasma = uuid.uuid4()
        async with sesion_de_tenant(fantasma, dsn=DSN_APLICACION) as sesion:
            with pytest.raises(IntegrityError):
                await TenancyService(sesion).crear_sucursal(
                    fantasma, SucursalCrear(name="Huerfana", city="Mendoza", province="Mendoza")
                )
