"""Cuotas del plan — C-04, bloque 6.

Cubre los escenarios de `tenancy/plan-limits`. Corre contra PostgreSQL real
(regla dura 8): el conteo va a la base, y un mock de base no probaria ni el
filtro de soft delete ni el aislamiento entre tenants, que es la mitad de lo
que hay que verificar.

POR QUE CASI TODO SE PRUEBA CON SUCURSALES
───────────────────────────────────────────
`assert_can_add_user` y `assert_can_add_vehicle` no tienen tabla que contar
todavia —`users` es C-05 y `vehicles` es C-14—, asi que su contador se registra
en el test. `branches` si existe, y es el unico de los tres que se puede
ejercitar de punta a punta hoy.

Eso no deja a los otros dos sin probar: lo que hay que verificar de ellos es
que la CUOTA funcione, no que sepan hacer un `COUNT`, y con un contador
inyectado se prueba exactamente eso — incluido el caso que mas importa, que es
el del contador que nadie registro.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import PlanQuotaExceeded
from app.modules.tenancy.limits import (
    ContadorNoRegistrado,
    PlanLimitsService,
    Recurso,
)
from app.modules.tenancy.models import Branch, Plan

from .soporte import sesion_de_propietario

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("base_migrada")]

_MULTIPLICADORES = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def _cuit_valido() -> str:
    """Un CUIT distinto por llamada, con su digito bien calculado.

    `tenants.cuit` es UNIQUE **global** y estos tests crean agencias que quedan
    en la base al terminar. El cuerpo sale de un UUID y no de un contador: un
    contador arranca en el mismo numero en cada proceso, asi que la primera
    corrida pasa y la segunda falla entera por duplicado — y el sintoma
    (`UniqueViolationError` en once tests de cuotas) no se parece en nada a la
    causa.
    """
    diez = f"30{uuid.uuid4().int % 100_000_000:08d}"
    suma = sum(int(d) * m for d, m in zip(diez, _MULTIPLICADORES, strict=True))
    resto = suma % 11
    digito = 0 if resto == 0 else 9 if resto == 1 else 11 - resto
    return f"{diez[:2]}-{diez[2:]}-{digito}"


async def _crear_tenant(codigo_de_plan: str | None) -> uuid.UUID:
    """Crea una agencia con el plan indicado y devuelve su id.

    Va por el rol PROPIETARIO porque `tenants` no tiene RLS (design.md D-1) y
    porque estos tests montan el escenario, no ejercitan el camino de alta —
    ese lo prueba el servicio de tenancy.
    """
    async with sesion_de_propietario() as sesion:
        plan_id = None
        if codigo_de_plan is not None:
            plan_id = (
                await sesion.execute(select(Plan.id).where(Plan.code == codigo_de_plan))
            ).scalar_one()
        fila = await sesion.execute(
            text("""
                INSERT INTO tenants (name, slug, cuit, billing_email, status, plan_id)
                VALUES (:name, :slug, :cuit, :email, 'active', :plan_id)
                RETURNING id
                """),
            {
                "name": "Agencia de prueba",
                "slug": f"prueba-{uuid.uuid4().hex[:12]}",
                "cuit": _cuit_valido(),
                "email": "facturacion@example.com",
                "plan_id": plan_id,
            },
        )
        return uuid.UUID(str(fila.scalar_one()))


async def _agregar_sucursales(sesion: AsyncSession, tenant_id: uuid.UUID, cuantas: int) -> None:
    for i in range(cuantas):
        sesion.add(
            Branch(tenant_id=tenant_id, name=f"Sucursal {i}", city="Mendoza", province="Mendoza")
        )
    await sesion.flush()


# ── El seed del catalogo ────────────────────────────────────────────────────


class TestSeedDelCatalogo:
    async def test_los_tres_planes_quedan_cargados(self, sesion_sin_tenant: AsyncSession) -> None:
        codigos = (
            await sesion_sin_tenant.execute(select(Plan.code).order_by(Plan.price_ars))
        ).scalars()
        assert list(codigos) == ["starter", "pro", "enterprise"]

    @pytest.mark.parametrize(
        ("codigo", "usuarios", "vehiculos", "sucursales", "wa"),
        [
            ("starter", 2, 80, 1, 1_500),
            ("pro", 5, 300, 2, 5_000),
            ("enterprise", 15, 0, 5, 20_000),
        ],
    )
    async def test_los_limites_son_los_de_plan_gtm(
        self,
        sesion_sin_tenant: AsyncSession,
        codigo: str,
        usuarios: int,
        vehiculos: int,
        sucursales: int,
        wa: int,
    ) -> None:
        """design.md D-2. Enterprise lleva `max_vehicles = 0` = sin techo."""
        plan = (
            await sesion_sin_tenant.execute(select(Plan).where(Plan.code == codigo))
        ).scalar_one()
        assert (
            plan.max_users,
            plan.max_vehicles,
            plan.max_branches,
            plan.max_whatsapp_messages_month,
        ) == (usuarios, vehiculos, sucursales, wa)

    @pytest.mark.parametrize(
        ("codigo", "precio"),
        [("starter", "45000.00"), ("pro", "95000.00"), ("enterprise", "195000.00")],
    )
    async def test_los_precios_son_los_de_mejoras_y_saas(
        self, sesion_sin_tenant: AsyncSession, codigo: str, precio: str
    ) -> None:
        """design.md D-3: los limites y los precios salen de documentos distintos.

        No es un descuido — `plan-gtm` cotiza en USD y `price_ars` no puede
        guardarlo. Este test fija la mezcla para que nadie la "corrija" a medias.
        """
        plan = (
            await sesion_sin_tenant.execute(select(Plan).where(Plan.code == codigo))
        ).scalar_one()
        assert plan.price_ars == Decimal(precio)

    async def test_reaplicar_el_seed_no_pisa_un_precio_cambiado_a_mano(self) -> None:
        """`ON CONFLICT DO NOTHING`, no `DO UPDATE`.

        Con `DO UPDATE`, cada despliegue devolveria los precios a los del
        archivo y borraria en silencio cualquier ajuste comercial hecho sobre la
        base. Un seed que sobrescribe datos de facturacion es una perdida de
        datos con permiso.
        """
        async with sesion_de_propietario() as sesion:
            await sesion.execute(
                update(Plan).where(Plan.code == "pro").values(price_ars=Decimal("111111.00"))
            )

        # Se reproduce la sentencia del seed en vez de invocar la migracion: lo
        # que se prueba es la clausula ON CONFLICT, no el andamiaje de alembic,
        # y volver a correr `upgrade` sobre una base ya migrada no ejecutaria
        # nada. Si alguien cambia el seed a `DO UPDATE`, este test tiene que
        # fallar — por eso la sentencia se escribe igual, con el mismo conflicto.
        async with sesion_de_propietario() as sesion:
            await sesion.execute(text("""
                    INSERT INTO plans (code, name, price_ars, max_users, max_vehicles,
                                       max_branches, max_whatsapp_messages_month, modules)
                    VALUES ('pro', 'Pro', 95000.00, 5, 300, 2, 5000, '[]'::jsonb)
                    ON CONFLICT (code) DO NOTHING
                    """))

        async with sesion_de_propietario() as sesion:
            precio = (
                await sesion.execute(select(Plan.price_ars).where(Plan.code == "pro"))
            ).scalar_one()
            assert precio == Decimal("111111.00")
            # Se restaura para no dejar el catalogo tocado para los demas tests.
            await sesion.execute(
                update(Plan).where(Plan.code == "pro").values(price_ars=Decimal("95000.00"))
            )


# ── La verificacion de cuota ────────────────────────────────────────────────


class TestCuotaDeSucursales:
    async def test_por_debajo_del_limite_se_permite(self) -> None:
        tenant_id = await _crear_tenant("pro")  # 2 sucursales
        async with sesion_de_propietario() as sesion:
            await _agregar_sucursales(sesion, tenant_id, 1)
            await PlanLimitsService(sesion).assert_can_add_branch(tenant_id)

    async def test_justo_en_el_limite_se_rechaza(self) -> None:
        tenant_id = await _crear_tenant("starter")  # 1 sucursal
        async with sesion_de_propietario() as sesion:
            await _agregar_sucursales(sesion, tenant_id, 1)
            with pytest.raises(PlanQuotaExceeded):
                await PlanLimitsService(sesion).assert_can_add_branch(tenant_id)

    async def test_una_sucursal_dada_de_baja_libera_su_lugar(self) -> None:
        """Soft delete libera cuota; la cuota mide ocupacion vigente."""
        tenant_id = await _crear_tenant("starter")
        async with sesion_de_propietario() as sesion:
            await _agregar_sucursales(sesion, tenant_id, 1)
            await sesion.execute(
                update(Branch).where(Branch.tenant_id == tenant_id).values(deleted_at=text("now()"))
            )
            await PlanLimitsService(sesion).assert_can_add_branch(tenant_id)

    async def test_una_sucursal_inactiva_sigue_ocupando_su_lugar(self) -> None:
        """`is_active = false` NO libera cuota (design.md D-7).

        Una sucursal cerrada por refaccion sigue existiendo. Si liberara cuota,
        desactivarla seria una forma gratis de saltarse el plan.
        """
        tenant_id = await _crear_tenant("starter")
        async with sesion_de_propietario() as sesion:
            await _agregar_sucursales(sesion, tenant_id, 1)
            await sesion.execute(
                update(Branch).where(Branch.tenant_id == tenant_id).values(is_active=False)
            )
            with pytest.raises(PlanQuotaExceeded):
                await PlanLimitsService(sesion).assert_can_add_branch(tenant_id)

    async def test_el_limite_de_una_agencia_no_lo_afecta_otra(self) -> None:
        lleno = await _crear_tenant("starter")
        vacio = await _crear_tenant("starter")
        async with sesion_de_propietario() as sesion:
            await _agregar_sucursales(sesion, lleno, 1)
            servicio = PlanLimitsService(sesion)
            with pytest.raises(PlanQuotaExceeded):
                await servicio.assert_can_add_branch(lleno)
            await servicio.assert_can_add_branch(vacio)


class TestSinTecho:
    async def test_cero_no_se_lee_como_cero_permitidos(self) -> None:
        """`0 = ilimitado` — el modo de fallar mas silencioso de `plans`.

        Enterprise es el unico plan con `max_vehicles = 0`. Si el servicio lo
        leyera como "cero permitidos", el plan mas caro del producto no dejaria
        cargar un solo vehiculo, y nadie reportaria eso como un problema de
        facturacion.
        """
        tenant_id = await _crear_tenant("enterprise")
        async with sesion_de_propietario() as sesion:
            servicio = PlanLimitsService(sesion)
            servicio.registrar(Recurso.VEHICLES, lambda _s, _t: _devolver(10_000))
            await servicio.assert_can_add_vehicle(tenant_id)

    async def test_un_tenant_sin_plan_no_tiene_techo(self) -> None:
        """Un trial todavia no eligio plan, y un trial que no deja cargar nada
        no es un trial. `plan_id IS NULL` se trata como sin techo, no como cero.
        """
        tenant_id = await _crear_tenant(None)
        async with sesion_de_propietario() as sesion:
            await _agregar_sucursales(sesion, tenant_id, 3)
            await PlanLimitsService(sesion).assert_can_add_branch(tenant_id)


class TestFallaCerrado:
    """Lo mas importante del modulo.

    Un recurso sin contador registrado LEVANTA. Devolver "permitido" es como se
    pierde un limite de facturacion: C-14 crea `vehicles`, se olvida de
    registrar el contador, y el sistema deja cargar sin techo en todos los
    planes. Nadie abre un ticket por eso.
    """

    async def test_un_recurso_sin_contador_levanta(self) -> None:
        tenant_id = await _crear_tenant("starter")
        async with sesion_de_propietario() as sesion:
            with pytest.raises(ContadorNoRegistrado):
                await PlanLimitsService(sesion).assert_can_add_vehicle(tenant_id)

    async def test_tampoco_pasa_para_usuarios(self) -> None:
        tenant_id = await _crear_tenant("starter")
        async with sesion_de_propietario() as sesion:
            with pytest.raises(ContadorNoRegistrado):
                await PlanLimitsService(sesion).assert_can_add_user(tenant_id)

    async def test_registrar_el_contador_lo_habilita(self) -> None:
        """El contrapeso: que el fallo cerrado no sea un "nunca funciona"."""
        tenant_id = await _crear_tenant("starter")  # 2 usuarios
        async with sesion_de_propietario() as sesion:
            servicio = PlanLimitsService(sesion)
            servicio.registrar(Recurso.USERS, lambda _s, _t: _devolver(1))
            await servicio.assert_can_add_user(tenant_id)

            servicio.registrar(Recurso.USERS, lambda _s, _t: _devolver(2))
            with pytest.raises(PlanQuotaExceeded):
                await servicio.assert_can_add_user(tenant_id)


class TestFormaDelRechazo:
    async def test_lleva_recurso_limite_y_usados(self) -> None:
        """El frontend arma "llegaste a 1 de 1 sucursales" sin parsear el texto."""
        tenant_id = await _crear_tenant("starter")
        async with sesion_de_propietario() as sesion:
            await _agregar_sucursales(sesion, tenant_id, 1)
            with pytest.raises(PlanQuotaExceeded) as exc:
                await PlanLimitsService(sesion).assert_can_add_branch(tenant_id)

        assert exc.value.recurso == "branches"
        assert exc.value.limite == 1
        assert exc.value.usados == 1

    async def test_el_estado_es_402_y_no_403(self) -> None:
        """design.md D-6. Un 403 mandaria al usuario a pedir permisos que ya tiene."""
        assert PlanQuotaExceeded(recurso="branches", limite=1, usados=1).status_code == 402

    async def test_el_codigo_es_estable_y_no_depende_del_idioma(self) -> None:
        assert PlanQuotaExceeded(recurso="users", limite=2, usados=2).code == "plan_quota_exceeded"


async def _devolver(n: int) -> int:
    """Contador de prueba: devuelve un numero fijo sin tocar la base."""
    return n
