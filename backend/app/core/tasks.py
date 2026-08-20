"""La aplicacion de Celery — C-17, `T-094`. Primera tarea del sistema.

POR QUE ESTE ARCHIVO NACE RECIEN AHORA
────────────────────────────────────────
`ADR-009` fija Celery desde el arranque del proyecto, pero hasta hoy **no habia
una sola tarea que ejecutar**. El servicio `worker` del compose apuntaba a
`app.core.events`, que no es una app de Celery y nunca va a serlo —es el
publicador y consumidor de eventos de dominio sobre Redis Streams— asi que el
contenedor moria al arrancar y quedo detras de un profile.

C-17 es la primera necesidad real: importar 5.000 filas no puede pasar dentro de
un request (`RN-PF-07`). Con esta app, el `worker` sale del profile y arranca
con el resto del entorno.

CELERY ES SINCRONO Y EL RESTO DEL SISTEMA NO
──────────────────────────────────────────────
Toda la capa de datos es `async`: `AsyncSession`, asyncpg, `sesion_de_tenant`
como context manager asincronico. Una tarea de Celery, en cambio, es una funcion
comun que corre en un hilo del pool del worker.

El puente es `asyncio.run()` **dentro** de la tarea. Es correcto acá y seria un
error en la aplicacion web: en el worker cada tarea es dueña de su hilo y no hay
loop corriendo del que colgarse; en FastAPI si lo hay, y `asyncio.run()` desde
adentro revienta con "cannot be called from a running event loop".

⚠️ Y CADA TAREA TIENE QUE CERRAR SUS ENGINES. No es higiene: es lo unico que
hace que la SEGUNDA importacion funcione.

`app/db/session.py` cachea el engine por DSN en un diccionario de modulo, que
sobrevive al `asyncio.run()`. La primera tarea lo crea con conexiones asyncpg
atadas a SU event loop; ese loop muere al terminar. La segunda tarea abre un
loop nuevo, recibe el engine cacheado con conexiones del loop muerto, y revienta
con `RuntimeError: got Future attached to a different loop` — un mensaje que no
menciona ni a Celery ni a la importacion.

Se detecto corriendo dos importaciones seguidas contra el entorno local. La
primera anduvo perfecto. Ninguno de los tests lo agarraba: todos comparten un
solo loop, que es justamente la condicion que oculta el problema.

El costo es armar el pool una vez por tarea. Esta asumido — una importacion dura
segundos o minutos, no milisegundos. Para tareas cortas y frecuentes habria que
sostener un loop por proceso en vez de uno por tarea.

QUE NO HACE ESTE ARCHIVO
─────────────────────────
No conoce el dominio. Importa el servicio adentro de la tarea, no arriba, y esto
NO es por prolijidad: el worker tiene que poder arrancar aunque un modulo de
dominio tenga un import roto — si no, un error en `stock` deja al worker sin
consumir ninguna cola, incluidas las que no tienen nada que ver.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any

from celery import Celery

from app.config import get_settings
from app.db.session import cerrar_engines

__all__ = ["app", "importar_stock"]


def _crear_app() -> Celery:
    """La app de Celery. El broker se resuelve TARDE, y eso no es un detalle.

    ⚠️ La primera version hacia `Celery("deruedas", broker=get_settings()...)`
    acá mismo, o sea **al importar el modulo**. Y este modulo lo importa el
    router de importacion, que lo importa `main.py`: cualquier test que armara
    la aplicacion con el entorno limpio —que es como corre toda la suite— moria
    con `ConfigurationError` antes de la primera linea del test.

    Peor todavia: el fallo depende de QUE archivo importe primero, porque el
    import de un modulo pasa una sola vez por proceso. O sea, verde solo y rojo
    en la suite, o al reves.

    `add_defaults` con un callable difiere la lectura hasta que Celery necesite
    el broker de verdad — que es cuando se encola o cuando arranca el worker, y
    ahi el entorno siempre esta.

    El broker va a Redis base 1: la 0 es la de eventos de dominio y cache, y
    mezclarlas hace que un `FLUSHDB` de una se lleve puesta a la otra.
    """
    celery = Celery("deruedas")
    celery.conf.add_defaults(lambda: {"broker_url": get_settings().redis.celery_broker_url})
    celery.conf.update(
        # El resultado de una importacion vive en la fila de `imports`, que es
        # contra lo que el frontend hace polling. Guardarlo tambien en Redis
        # seria una segunda fuente de verdad que puede quedar desincronizada.
        result_backend=None,
        task_track_started=True,
        # Sin esto, una tarea que muere con el worker se pierde en silencio.
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        # Serializacion explicita: los defaults de Celery cambiaron entre
        # versiones mayores y "el default" no es una decision documentada.
        task_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
    )
    return celery


app = _crear_app()


@app.task(name="stock.importar", bind=True, max_retries=3, default_retry_delay=2)
def importar_stock(self: Any, importacion_id: str, tenant_id: str) -> None:
    """Ejecuta una importacion ya registrada. Los ids viajan como texto.

    ⚠️ NO recibe el archivo. Recibe el ID de una fila de `imports` que ya
    existe, y el contenido lo levanta de Redis. Mandar 10 MB en el mensaje de
    Celery los pondria en el broker, en base64, para cada reintento.

    ⚠️ LOS REINTENTOS CUBREN UN SOLO CASO, Y NO ES "FALLO".
    Reintentar una importacion NO es idempotente: la segunda corrida encontraria
    los vehiculos de la primera y los reportaria como dominios duplicados. Por
    eso `ejecutar_importacion` **nunca levanta** — un fallo queda escrito en la
    fila, con su motivo, y no vuelve por acá.

    Lo unico que reintenta es que la fila todavia no sea VISIBLE. El endpoint
    encola antes de que su transaccion cierre, asi que el worker puede llegar
    primero; en ese momento no se hizo ni una linea de trabajo, y volver a
    intentar es seguro justamente porque no hay nada hecho que repetir.

    `tenant_id` viaja aparte y no se lee de la fila: sin contexto de tenant no
    se puede leer NINGUNA fila de `imports`, ni siquiera la propia. Es la
    politica RLS funcionando, no una redundancia.
    """
    # Import adentro de la funcion: ver el encabezado del modulo.
    from app.modules.stock.importacion_servicio import ejecutar_importacion

    encontrada = asyncio.run(
        _con_engines_propios(ejecutar_importacion(uuid.UUID(importacion_id), uuid.UUID(tenant_id)))
    )
    if not encontrada:
        raise self.retry(countdown=2)


async def _con_engines_propios(trabajo: Coroutine[Any, Any, bool]) -> bool:
    """Corre el trabajo y deja los engines cerrados, pase lo que pase.

    El `finally` es la parte importante: si la tarea falla y NO se cierran, la
    siguiente hereda conexiones de un loop muerto y falla por un motivo que no
    tiene nada que ver con ella. El sintoma seria "la primera importacion anda y
    las demas no", que es carisimo de diagnosticar.

    Envuelve acá y no dentro de `ejecutar_importacion` porque el dueño del event
    loop es la tarea: los tests llaman a esa funcion dentro de su propio loop
    compartido, y cerrarles los engines desde adentro seria que el trabajo de
    dominio decida sobre infraestructura que no abrio.
    """
    try:
        return await trabajo
    finally:
        await cerrar_engines()
