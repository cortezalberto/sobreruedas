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

import uuid

from fastapi import APIRouter, HTTPException

from app.db.session import sesion_de_catalogo
from app.modules.tenancy.repository import PlanRepository, VehicleCatalogRepository
from app.modules.tenancy.schemas import MarcaSalida, ModeloSalida, PlanSalida

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


@router.get(
    "/catalog/brands",
    response_model=list[MarcaSalida],
    summary="Marcas del catalogo",
    description="Catalogo cross-tenant de marcas, en orden alfabetico.",
)
async def listar_marcas() -> list[MarcaSalida]:
    async with sesion_de_catalogo() as sesion:
        marcas = await VehicleCatalogRepository(sesion).listar_marcas()

    return [MarcaSalida.model_validate(marca) for marca in marcas]


@router.get(
    "/catalog/brands/{marca_id}/models",
    response_model=list[ModeloSalida],
    summary="Modelos de una marca",
    description=(
        "Los modelos de una marca, del mas nuevo al mas viejo. "
        "`year_to` en `null` significa que el modelo se sigue vendiendo."
    ),
    responses={404: {"description": "La marca no existe o no esta publicada"}},
)
async def listar_modelos(marca_id: uuid.UUID) -> list[ModeloSalida]:
    """Se busca por ID, que es lo que el catalogo de endpoints documenta.

    ⚠️ La primera version de este endpoint uso el SLUG y vivia en
    `/api/v1/vehicle-brands/{slug}/models`. Las dos cosas estaban mal: el
    catalogo de `knowledge-base/02` —derivado de `spec-tecnica`, que es N1— ya
    documentaba `GET /catalog/brands` y `/catalog/brands/{id}/models`. Se
    invento un contrato que ya estaba escrito, por no cruzarlo antes de escribir
    el router.

    El slug seguia siendo mas lindo en una URL, pero eso no lo decide este
    archivo: apartarse de N1 exige un ADR, y no hay ninguna razon de dominio
    para pedirlo. El frontend mantiene sus URLs legibles resolviendo el slug
    contra el listado de marcas, que ya tiene cargado.

    Una marca inexistente da 404 y no una lista vacia. Son cosas distintas:
    "esta marca no tiene modelos cargados" es un catalogo incompleto, y "esta
    marca no existe" es un error del que pregunta. Devolver `[]` para las dos
    esconde la segunda.
    """
    # La transaccion se cierra antes de decidir el 404, por lo mismo que en
    # `listar_planes`: no se sostiene una conexion del pool mientras se arma la
    # respuesta. Y ademas coverage no marca ejecutadas las lineas por las que
    # una excepcion sale a traves de un `async with`.
    async with sesion_de_catalogo() as sesion:
        repositorio = VehicleCatalogRepository(sesion)
        marca = await repositorio.obtener_marca(marca_id)
        modelos = await repositorio.listar_modelos_de(marca.id) if marca is not None else []

    if marca is None:
        # `HTTPException` y no una excepcion de dominio nueva: el manejador de
        # `StarletteHTTPException` ya la convierte al mismo problem+json que el
        # resto. Una clase propia solo agregaria una taxonomia para decir lo que
        # el 404 ya dice.
        raise HTTPException(status_code=404, detail=f"no existe la marca {marca_id}")

    return [ModeloSalida.model_validate(modelo) for modelo in modelos]
