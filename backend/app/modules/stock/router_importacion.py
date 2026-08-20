"""Endpoints de importacion masiva de stock — C-17, `T-095`.

    POST /api/v1/vehicles/import   sube la planilla, encola y devuelve al toque
    GET  /api/v1/imports           las corridas de la agencia
    GET  /api/v1/imports/{id}      el progreso — el frontend pregunta cada 2 s

⚠️ NO HAY `require_permission` TODAVIA
───────────────────────────────────────
Igual que el resto de stock: cualquier usuario autenticado de la agencia puede
importar. `ADR-024` reserva esto a `manager` y `admin_staff` —un vendedor no
carga stock masivo— y la restriccion se cuelga cuando exista `rbac.py`
(C-02 bloque 6, esperando a `E-001`).

Es de las que mas importa poner: una importacion escribe cientos de filas de
una y no hay "deshacer".

POR QUE EL POST DEVUELVE 202 Y NO 201
───────────────────────────────────────
Cuando responde, **no hay ningun vehiculo creado todavia**. Lo que existe es una
corrida encolada. Un 201 con `Location` al recurso importado mentiria: ese
recurso no esta, y el cliente que lo consulte va a encontrar cero filas y
concluir que fallo.

202 con la fila de seguimiento es exactamente lo que paso: *aceptado, todavia no
hecho, mira acá*.

LO QUE ESTA PLANILLA NO IMPORTA
────────────────────────────────
  - **Fotos** — limitacion conocida del `Flujo 4`; se asocian despues a mano.
  - **Versiones** — la columna `version` se parsea y **se ignora**: la tabla
    `vehicle_versions` es de C-13 y todavia no existe, asi que no hay contra que
    resolver el nombre. Por eso tampoco figura en la plantilla que se descarga:
    lo que no se puede guardar, no se pide.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.auth import SujetoActual
from app.core.rbac import require_permission
from app.core.tasks import importar_stock
from app.db.dependencias import SesionDeTenant
from app.modules.stock.importacion import LIMITE_DE_BYTES, ArchivoIlegible
from app.modules.stock.importacion_modelo import ImportacionSalida
from app.modules.stock.importacion_servicio import ImportService

__all__ = ["router"]

router = APIRouter(prefix="/api/v1", tags=["stock"])

# Singleton de modulo: `File(...)` en el default del parametro es una llamada a
# funcion evaluada al importar (B008). FastAPI lo entiende igual desde acá.
ARCHIVO = File(..., description="CSV exportado de Excel")


def _servicio(sesion: SesionDeTenant) -> ImportService:
    """El tenant sale de `sesion.info`, que lo puso la dependency desde el token.

    Nunca de un parametro: un endpoint que reciba el tenant puede recibir el
    equivocado, y la consulta andaria igual — acotando a la agencia de otro.
    """
    return ImportService(sesion, sesion.info["tenant_id"])


@router.post(
    "/vehicles/import",
    response_model=ImportacionSalida,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Importar stock desde una planilla",
    dependencies=[Depends(require_permission("vehicles:import"))],
    description=(
        "Acepta el CSV, lo encola y devuelve la corrida en `pending`. El "
        "progreso se sigue con `GET /imports/{id}`. Maximo **10 MB** y **5.000 "
        "filas** (`RN-ST-13`)."
    ),
)
async def importar(
    sujeto: SujetoActual,
    sesion: SesionDeTenant,
    archivo: UploadFile = ARCHIVO,
) -> ImportacionSalida:
    """Sube y encola. No importa nada dentro del request.

    El archivo se lee **con tope**: `await archivo.read()` a secas cargaria en
    memoria lo que el cliente mande, y el limite de 10 MB dejaria de ser un
    limite para pasar a ser una comprobacion que llega tarde.

    `created_by` guarda el `sub` del token. Es el mismo identificador con el que
    C-05 va a poblar `users.id`, asi que la FK se agrega despues sin migrar
    datos — ver el encabezado de la migracion `012`.
    """
    contenido = await archivo.read(LIMITE_DE_BYTES + 1)
    if len(contenido) > LIMITE_DE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"el archivo supera los {LIMITE_DE_BYTES // (1024 * 1024)} MB (RN-ST-13)",
        )

    try:
        corrida = await _servicio(sesion).registrar(
            nombre_archivo=archivo.filename or "planilla.csv",
            contenido=contenido,
            creado_por=_usuario(sujeto.user_id),
        )
    except ArchivoIlegible as fallo:
        # 422 y no 400: la peticion esta bien formada, el CONTENIDO no sirve.
        raise HTTPException(status_code=422, detail=str(fallo)) from fallo

    salida = ImportacionSalida.model_validate(corrida)

    # ⚠️ ACA HAY UNA CARRERA, Y ESTA CUBIERTA DEL LADO DEL WORKER.
    #
    # La fila todavia NO esta commiteada: la transaccion la cierra la dependency
    # cuando termina el request, y para entonces el worker ya puede haber
    # tomado el mensaje. Si mira antes, no encuentra nada.
    #
    # La tarea contempla ese caso y **reintenta**: mientras la fila no sea
    # visible no hizo ningun trabajo, asi que reintentar es seguro (ver
    # `importar_stock`). Sin eso, la corrida quedaria clavada en `pending` y el
    # frontend preguntando para siempre.
    #
    # La solucion definitiva es la bandeja de salida transaccional que C-03 trae
    # para los eventos de dominio: encolar en la MISMA transaccion. Cuando
    # exista, este `delay()` se reemplaza por una fila en esa tabla.
    importar_stock.delay(str(corrida.id), str(corrida.tenant_id))
    return salida


@router.get(
    "/imports",
    response_model=list[ImportacionSalida],
    summary="Importaciones de la agencia",
    dependencies=[Depends(require_permission("vehicles:import"))],
)
async def listar_importaciones(sesion: SesionDeTenant) -> list[ImportacionSalida]:
    corridas = await _servicio(sesion).listar()
    return [ImportacionSalida.model_validate(c) for c in corridas]


@router.get(
    "/imports/{importacion_id}",
    response_model=ImportacionSalida,
    summary="Progreso de una importacion",
    dependencies=[Depends(require_permission("vehicles:import"))],
    description=(
        "El frontend consulta cada 2 s hasta que `status` sea `completed` o "
        "`failed`. `errors` trae el reporte por fila para corregir la planilla."
    ),
)
async def obtener_importacion(
    importacion_id: uuid.UUID, sesion: SesionDeTenant
) -> ImportacionSalida:
    corrida = await _servicio(sesion).obtener(importacion_id)
    return ImportacionSalida.model_validate(corrida)


def _usuario(sub: str) -> uuid.UUID | None:
    """El `sub` de Keycloak, si es un UUID.

    Keycloak emite UUIDs, pero `sub` es texto libre en el estandar y otro
    proveedor podria mandar cualquier cosa. Guardar `NULL` es mejor que romper
    una importacion valida por no poder anotar quien la pidio.
    """
    try:
        return uuid.UUID(sub)
    except ValueError:
        return None
