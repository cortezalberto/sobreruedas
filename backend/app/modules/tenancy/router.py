"""Endpoints HTTP del modulo tenancy.

EL PRIMER ROUTER DE DOMINIO DEL SISTEMA, Y POR QUE EMPIEZA POR EL CATALOGO
──────────────────────────────────────────────────────────────────────────
Hasta acá la aplicacion exponia solo `/health` y `/ready`. El modulo `tenancy`
tenia modelos, repositorios y servicio al 100 % de cobertura, y ninguna forma de
consultarlo desde afuera: los endpoints estaban asignados a C-05, que hoy espera
el cierre de `E-001`.

Este router NO adelanta C-05. Publica una sola cosa —el catalogo de planes— que
queda fuera de todo lo que `E-001` traba:

  - `plans` no lleva `tenant_id` y figura en `EXENTAS_DE_RLS` (`RN-MT-09`), asi
    que no hay contexto de tenant que establecer ni aislamiento que violar.
  - Es la grilla comercial: la misma informacion que se publica en la web. No
    hay identidad que verificar porque no hay nada privado que proteger.

Los endpoints de agencias, sucursales y usuarios siguen siendo C-05, y siguen
esperando. Este archivo no los toca.

⚠️ LO QUE ESTE ROUTER TODAVIA NO TIENE, Y HAY QUE SABERLO
─────────────────────────────────────────────────────────
No hay autenticacion, y no es un olvido: este endpoint no la necesita. Pero
tampoco existe todavia el mecanismo para los que SI la van a necesitar — eso
llega con C-05 y Keycloak (`ADR-007`). Agregar un endpoint privado a este
archivo sin esa pieza seria exponerlo sin control.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.db.session import sesion_de_catalogo
from app.modules.tenancy.repository import PlanRepository
from app.modules.tenancy.schemas import PlanSalida

__all__ = ["router"]

router = APIRouter(prefix="/api/v1", tags=["planes"])


@router.get(
    "/plans",
    response_model=list[PlanSalida],
    summary="Catalogo de planes",
    description=(
        "La grilla comercial, del plan mas barato al mas caro. "
        "En los limites, `0` significa **sin techo**, no cero permitidos."
    ),
)
async def listar_planes() -> list[PlanSalida]:
    # La transaccion se cierra ANTES de serializar. Convertir a schema no toca
    # la base —la fabrica de sesiones usa `expire_on_commit=False`, asi que los
    # atributos ya cargados siguen ahi—, y sostener la transaccion mientras se
    # arma la respuesta ocupa una conexion del pool sin necesidad.
    async with sesion_de_catalogo() as sesion:
        planes = await PlanRepository(sesion).listar_activos()

    return [PlanSalida.model_validate(plan) for plan in planes]
