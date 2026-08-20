"""Errores de dominio y respuestas Problem Details — T-005.

Todo error que sale de la API tiene el MISMO formato, sea de dominio, de
validacion o un 404. Que cada capa invente su propio JSON de error es lo que
obliga a quien consume la API a escribir un parser por endpoint.

El formato es Problem Details (RFC 9457), con dos extensiones propias:

  code            identificador estable del error, para que el cliente
                  discrimine sin parsear el texto en castellano
  correlation_id  el identificador de la peticion. Sin esto, un usuario que
                  reporta "me dio error" no se puede rastrear en los logs.

Y en los errores de validacion, una tercera:

  errors[]        una entrada por campo invalido, con `field`, `code` y
                  `message`.

DOS `code` EN NIVELES DISTINTOS
───────────────────────────────
El `code` de arriba dice QUE CLASE de error es la respuesta (`validation_error`,
`patente_duplicada`). El `code` de cada entrada de `errors[]` dice QUE LE PASA A
ESE CAMPO (`missing`, `int_parsing`). Son dos preguntas distintas y por eso son
dos campos; colapsarlos obligaria al cliente a leer el mensaje para saber por
que fallo un campo, que es justo lo que este formato evita.

El codigo por campo es el `type` de pydantic. Se usa tal cual y no se traduce a
un vocabulario propio: el de pydantic ya es estable, esta documentado y cubre
todos los casos, mientras que una tabla de equivalencias propia habria que
mantenerla al dia sin ningun consumidor que hoy la pida. Si algun dia el
contrato publico necesita independizarse de la version de pydantic, el lugar
para traducir es este y nada mas que este.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.observability import get_correlation_id

TIPO_CONTENIDO = "application/problem+json"


class DomainError(Exception):
    """Una regla de negocio dijo que no.

    No es un fallo tecnico: la peticion se entendio, pero el dominio la
    rechaza. Por eso 422 y no 500.
    """

    status_code = 422

    def __init__(self, detail: str, *, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code or "domain_error"


class AuthenticationError(Exception):
    """No se pudo establecer quien hace la peticion.

    401 y no 403: son cosas distintas y confundirlas confunde a quien consume la
    API. **401 es "no se quien sos"** —falta el token, o no vale— y se arregla
    presentando uno bueno. **403 es "se quien sos y no podes"** —lo trae
    `rbac.py` en el bloque 6— y no se arregla reintentando.

    Devolver 403 ante un token vencido manda a pedir permisos que ya se tienen;
    devolver 401 ante una falta de permisos manda a renovar un token que esta
    perfecto. En los dos casos se pierde media hora mirando el lugar equivocado.
    """

    status_code = 401

    def __init__(self, detail: str, *, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code or "not_authenticated"


class AuthorizationError(Exception):
    """Se sabe quien hace la peticion, y no le alcanza.

    403, el otro lado de la distincion que `AuthenticationError` explica arriba.
    No se arregla reintentando ni renovando el token: hace falta que otro
    conceda el permiso, o no hace falta nada porque la respuesta es no.

    El detalle es DELIBERADAMENTE generico y no dice que rol hacia falta.
    Enumerar los roles admitidos en la respuesta le regala a quien no puede el
    mapa de quien si — util para depurar, y por eso va al log, no al cuerpo.
    """

    status_code = 403

    def __init__(self, detail: str | None = None, *, code: str | None = None) -> None:
        detalle = detail or "no tenes permisos para esta operacion"
        super().__init__(detalle)
        self.detail = detalle
        self.code = code or "forbidden"


class RolInsuficiente(AuthorizationError):
    """El rol del sujeto no esta entre los admitidos por la operacion.

    Codigo propio y no el generico: el frontend reacciona distinto ante "tu rol
    no llega" (ocultar la accion) que ante un 403 por alcance o por campos, que
    llegan mas adelante en el bloque 6.
    """

    def __init__(self) -> None:
        super().__init__(code="insufficient_role")


class PermisoInsuficiente(AuthorizationError):
    """El rol del sujeto no tiene celda para el permiso que la operacion exige.

    Codigo propio, distinto de `insufficient_role`. Los dos son 403 y para el
    usuario final significan lo mismo, pero para el frontend no: "tu rol no esta
    entre los admitidos" describe la operacion entera, y "no tenes este permiso"
    describe una celda. La segunda convive con que el mismo rol si tenga otras
    operaciones del mismo recurso, y la interfaz decide distinto en cada caso.
    """

    def __init__(self) -> None:
        super().__init__(code="insufficient_permission")


class AlcanceInsuficiente(AuthorizationError):
    """El sujeto tiene el permiso, pero no sobre ESE registro.

    Tercer codigo 403 del bloque, y el mas util de los tres para el frontend:
    "no tenes el permiso" se responde escondiendo la accion, y "no sobre este"
    se responde mostrandola y explicando de quien es. Colapsarlos obligaria a la
    interfaz a adivinar cual de los dos paso.

    ⚠️ El mensaje no dice a quien esta asignado el recurso. Decirlo convertiria
    un 403 en una consulta del padron de usuarios para quien no lo tiene.
    """

    def __init__(self) -> None:
        super().__init__("no tenes acceso a este registro", code="out_of_scope")


class TransicionNoPermitida(AuthorizationError):
    """El cambio de estado es legal, y este rol no lo hace — `ADR-034`.

    **403 y no 422**, y la diferencia no es de matiz. `TransicionInvalida` (422,
    en el servicio de stock) dice que `RN-ST-05` no admite ese cambio PARA
    NADIE: `in_preparation` -> `sold` no lo hace ni el gerente. Esto dice que el
    cambio existe y que quien pregunta no es quien lo hace.

    Un 422 aca mandaria al vendedor a creer que el sistema no permite vender.
    """

    def __init__(self) -> None:
        super().__init__(
            "tu rol no puede hacer ese cambio de estado",
            code="transition_not_allowed",
        )


class PlanQuotaExceeded(Exception):
    """El plan del tenant no da para una creacion mas.

    **402 y no 403**, y la diferencia no es cosmetica (design.md D-6 de C-04):

      - 401  no se quien sos            -> autenticarse
      - 403  se quien sos y no te alcanza el rol -> pedirselo a un manager
      - 402  se quien sos, TENES el permiso, y el plan no da -> subir de plan

    Un 403 aca manda al usuario por el camino equivocado: va a buscar a alguien
    con mas permisos, y no hay permiso que agregue vehiculos por encima de la
    cuota — el manager tampoco puede. Y para el producto la diferencia importa
    todavia mas: un 402 es una senal comercial (un tenant tocando su techo es
    un candidato a upgrade) y un 403 es ruido de soporte.

    Lleva `recurso`, `limite` y `usados` en el cuerpo para que el frontend
    pueda decir "llegaste a 80 de 80 vehiculos de Starter" sin adivinar.
    """

    status_code = 402

    def __init__(self, *, recurso: str, limite: int, usados: int) -> None:
        detalle = f"el plan permite hasta {limite} y ya hay {usados}"
        super().__init__(detalle)
        self.detail = detalle
        self.code = "plan_quota_exceeded"
        self.recurso = recurso
        self.limite = limite
        self.usados = usados


class RequestError(Exception):
    """La peticion no se pudo interpretar, y la validacion no lo atrapo.

    Distinto de `DomainError`: alla la peticion se entendio y el dominio la
    rechazo; aca no se llego a entender. Un cursor de paginacion ilegible es el
    caso tipico — no es una regla de negocio incumplida, es una entrada rota que
    ningun esquema Pydantic puede validar porque su formato es interno.

    400 y no 422 por eso mismo.
    """

    status_code = 400

    def __init__(self, detail: str, *, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code or "invalid_request"


def _problema(
    *, status: int, title: str, detail: str, code: str, extra: dict[str, Any] | None = None
) -> JSONResponse:
    cuerpo: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "correlation_id": get_correlation_id(),
    }
    if extra:
        cuerpo.update(extra)
    return JSONResponse(status_code=status, content=cuerpo, media_type=TIPO_CONTENIDO)


def register_exception_handlers(app: FastAPI) -> None:
    """Cuelga los handlers globales en la aplicacion."""

    @app.exception_handler(DomainError)
    async def _dominio(_: Request, exc: DomainError) -> JSONResponse:
        return _problema(
            status=exc.status_code,
            title="Regla de negocio incumplida",
            detail=exc.detail,
            code=exc.code,
        )

    @app.exception_handler(AuthenticationError)
    async def _autenticacion(_: Request, exc: AuthenticationError) -> JSONResponse:
        return _problema(
            status=exc.status_code,
            title="No autenticado",
            detail=exc.detail,
            code=exc.code,
        )

    @app.exception_handler(AuthorizationError)
    async def _autorizacion(_: Request, exc: AuthorizationError) -> JSONResponse:
        return _problema(
            status=exc.status_code,
            title="Sin permisos",
            detail=exc.detail,
            code=exc.code,
        )

    @app.exception_handler(PlanQuotaExceeded)
    async def _cuota(_: Request, exc: PlanQuotaExceeded) -> JSONResponse:
        return _problema(
            status=exc.status_code,
            title="Limite del plan alcanzado",
            detail=exc.detail,
            code=exc.code,
            # El cliente reacciona por `code` y arma el mensaje con estos tres.
            # Sin ellos tendria que parsear `detail`, que es texto para humanos
            # y cambia con el idioma.
            extra={"resource": exc.recurso, "limit": exc.limite, "used": exc.usados},
        )

    @app.exception_handler(RequestError)
    async def _peticion(_: Request, exc: RequestError) -> JSONResponse:
        return _problema(
            status=exc.status_code,
            title="Peticion no interpretable",
            detail=exc.detail,
            code=exc.code,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problema(
            status=exc.status_code,
            title="Error HTTP",
            detail=str(exc.detail),
            code=f"http_{exc.status_code}",
        )

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        # `errors()` trae `input`, o sea el valor que mando el cliente. Se
        # descarta a proposito: puede ser una contrasena o un token.
        #
        # Se construye entrada por entrada y NO con un `dict(detalle)` filtrado:
        # asi, el dia que pydantic agregue una clave nueva a su salida, esa
        # clave no se cuela sola en la respuesta publica de la API. La lista de
        # lo que sale es esta, y esta escrita.
        campos = [
            {
                "field": ".".join(str(parte) for parte in detalle["loc"]),
                "code": detalle["type"],
                "message": detalle["msg"],
            }
            for detalle in exc.errors()
        ]
        return _problema(
            status=422,
            title="Peticion invalida",
            detail="La peticion no supero la validacion.",
            code="validation_error",
            extra={"errors": campos},
        )
