"""La sesion de base que usa un endpoint protegido — C-02.

QUE PROBLEMA RESUELVE
──────────────────────
Habia dos piezas sueltas y ningun puente entre ellas:

  - `core/auth.py` valida el token y devuelve un `Sujeto` con su `tenant_id`.
  - `db/session.py` abre una sesion con el contexto de tenant establecido.

Cada endpoint tendria que haberlas unido a mano, y ese es exactamente el lugar
donde se comete el error que la regla dura 1 existe para impedir: alguien toma
el tenant de un parametro de la ruta "porque es mas comodo de probar", y el
aislamiento se cae sin que nada falle.

Acá se unen UNA vez, y los endpoints piden el resultado.

EL TENANT SALE DEL TOKEN Y DE NINGUN OTRO LADO
───────────────────────────────────────────────
Esta funcion no recibe un `tenant_id`. No se lo puede pasar. Lo unico que toma
es `SujetoActual`, y de ahi lee el claim que el token ya trajo verificado.

No es una convencion: es la forma del tipo. Un endpoint que quisiera acotar a
otro tenant no tiene por donde pedirlo.

⚠️ POR QUE VIVE EN `db/` Y NO EN `core/`
─────────────────────────────────────────
Lo que entrega es una sesion de base. `core/auth.py` no puede importar `db/`
—quedaria un ciclo, porque la sesion no sabe nada de tokens— asi que el puente
tiene que estar de este lado. `db/session.py` tampoco: importar `auth` desde ahi
ataria la capa de datos a la de identidad, y la sesion de tenant se usa tambien
desde tests y migraciones, donde no hay token.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import SujetoActual
from app.db.session import sesion_de_tenant

__all__ = ["SesionDeTenant", "sesion_del_tenant_actual"]


async def sesion_del_tenant_actual(sujeto: SujetoActual) -> AsyncIterator[AsyncSession]:
    """Sesion acotada al tenant del token.

    Es una dependency GENERADORA —`yield` y no `return`— a proposito: asi
    FastAPI ejecuta el cierre del context manager cuando la peticion termina,
    incluso si el endpoint levanta. Con un `return` la transaccion quedaria
    abierta y la conexion no volveria al pool.

    El `SET LOCAL` del contexto lo emite `sesion_de_tenant` como primera
    sentencia de la transaccion, que es la unica forma de que la politica RLS lo
    vea (`design.md` D-3 de C-02).
    """
    async with sesion_de_tenant(sujeto.tenant_id) as sesion:
        # El tenant queda en `sesion.info` para que el router no tenga que pedir
        # el sujeto por separado. Es deliberado: con dos parametros —la sesion y
        # el sujeto— un endpoint podria acotar la consulta a uno y leer el otro,
        # y esa incoherencia no la detecta nadie. Asi hay una sola fuente.
        #
        # `.info` es el diccionario que SQLAlchemy reserva para esto y vive con
        # la sesion, o sea con la transaccion: no puede sobrevivirla ni filtrarse
        # a otra peticion.
        sesion.info["tenant_id"] = sujeto.tenant_id
        yield sesion


# El alias que va a usar cada endpoint con datos de una agencia:
#
#     async def listar_vehiculos(sesion: SesionDeTenant) -> list[VehiculoSalida]:
#
# Pedir esto es, en un solo parametro: exigir token, validarlo, sacar el tenant
# del claim y abrir la transaccion con el contexto puesto. Un endpoint que lo
# declara no puede olvidarse de ninguno de los cuatro pasos.
SesionDeTenant = Annotated[AsyncSession, Depends(sesion_del_tenant_actual)]
