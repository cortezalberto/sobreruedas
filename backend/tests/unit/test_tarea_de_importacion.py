"""La tarea de Celery — C-17, `T-094`.

QUE PRUEBA ESTE ARCHIVO Y QUE NO
─────────────────────────────────
`importar_stock` es fina a proposito: llama a `ejecutar_importacion()`, que es
donde vive todo el trabajo y que se prueba contra PostgreSQL y Redis reales en
`tests/integration/test_importacion_ejecucion.py`.

Lo que queda para acá son las tres cosas que la tarea agrega, y ninguna necesita
infraestructura:

  1. **El puente sincronico → asincronico.** Celery corre funciones comunes; la
     capa de datos es `async`. El `asyncio.run()` es la costura, y una costura
     que se descosa deja al worker sin hacer nada sin decir nada.
  2. **Los ids como texto.** Viajan `str` por el mensaje JSON y tienen que
     llegar `UUID` a la funcion. Un `str` que se cuele acota por un tenant que
     no existe y devuelve cero filas, sin error.
  3. **El reintento acotado.** Solo cuando la corrida todavia no es visible.

Tambien se verifica que importar el modulo NO exija el entorno, porque de eso
depende que la suite entera pueda armar la aplicacion.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.core import tasks


@pytest.fixture
def espia(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    """Reemplaza `ejecutar_importacion` y anota con que la llamaron.

    Se parchea en el modulo del SERVICIO y no en `tasks`, porque la tarea lo
    importa adentro de la funcion —a proposito, ver su encabezado— y para
    cuando corre, el nombre ya se resolvio contra el modulo de origen.
    """
    llamadas: list[tuple[Any, ...]] = []

    async def falso(importacion_id: Any, tenant_id: Any) -> bool:
        llamadas.append((importacion_id, tenant_id))
        return True

    from app.modules.stock import importacion_servicio

    monkeypatch.setattr(importacion_servicio, "ejecutar_importacion", falso)
    return llamadas


def test_los_ids_llegan_como_uuid_y_no_como_texto(espia: list[tuple[Any, ...]]) -> None:
    """Viajan `str` en el mensaje JSON; la funcion espera `UUID`.

    Si pasara el `str`, la consulta compara `uuid = text` y PostgreSQL lo
    rechaza — o peor, en otro contexto acota por un tenant inexistente y
    devuelve cero filas sin quejarse.
    """
    importacion_id, tenant_id = uuid.uuid4(), uuid.uuid4()

    tasks.importar_stock.apply(args=[str(importacion_id), str(tenant_id)])

    assert espia == [(importacion_id, tenant_id)]


def test_la_tarea_corre_la_corrutina_hasta_el_final(espia: list[tuple[Any, ...]]) -> None:
    """El `asyncio.run()`, que es lo unico que hace de puente.

    Sin el, la llamada devolveria una corrutina sin ejecutar: la tarea
    terminaria "bien", el espia quedaria vacio y nadie importaria nada.
    """
    resultado = tasks.importar_stock.apply(args=[str(uuid.uuid4()), str(uuid.uuid4())])

    assert resultado.successful()
    assert len(espia) == 1


def test_reintenta_cuando_la_corrida_todavia_no_se_ve(monkeypatch: pytest.MonkeyPatch) -> None:
    """Es la carrera del endpoint: encola antes de que su transaccion cierre.

    Reintentar es seguro **porque no se hizo nada**: `ejecutar_importacion`
    devuelve `False` antes de tocar una sola fila. Cualquier otro fallo queda
    escrito en la corrida y no vuelve por acá — importar dos veces duplicaria
    trabajo y llenaria el reporte de dominios repetidos.
    """

    async def nunca_la_encuentra(importacion_id: Any, tenant_id: Any) -> bool:
        return False

    from app.modules.stock import importacion_servicio

    monkeypatch.setattr(importacion_servicio, "ejecutar_importacion", nunca_la_encuentra)

    # Se espia `retry` en vez de mirar el estado del resultado. En modo eager
    # —que es como corre `.apply()`— Celery no lleva la cuenta de reintentos y
    # convierte el `retry()` en `MaxRetriesExceededError`: el estado final
    # dice `FAILURE` y no distingue "pidio reintentar" de "reviento". Lo que se
    # quiere afirmar es la DECISION de la tarea, no como la traduce el modo
    # eager.
    pedidos: list[dict[str, Any]] = []

    def espiar_retry(**argumentos: Any) -> Exception:
        pedidos.append(argumentos)
        return RuntimeError("reintento pedido")

    monkeypatch.setattr(tasks.importar_stock, "retry", espiar_retry)

    resultado = tasks.importar_stock.apply(args=[str(uuid.uuid4()), str(uuid.uuid4())])

    assert pedidos == [{"countdown": 2}]
    # Y ademas NO puede quedar como exitosa: una corrida que no se ejecuto y
    # figura como hecha es una importacion que nadie va a volver a mirar.
    assert not resultado.successful()


def test_no_reintenta_cuando_la_corrida_si_estaba(espia: list[tuple[Any, ...]]) -> None:
    """La contracara. Sin esta afirmacion, un `raise self.retry()` incondicional
    pasaria el test de arriba y reimportaria todo cada vez."""
    resultado = tasks.importar_stock.apply(args=[str(uuid.uuid4()), str(uuid.uuid4())])

    assert resultado.state == "SUCCESS"


def test_importar_el_modulo_no_exige_el_entorno() -> None:
    """El broker se resuelve TARDE, y de eso depende que la suite arranque.

    `app/core/tasks.py` lo importa el router de importacion, que lo importa
    `main.py`. Si leyera `Settings` al importarse, cualquier test que arme la
    aplicacion con el entorno limpio —o sea, todos— moriria antes de su primera
    linea. Y el fallo dependeria de que archivo importe primero, porque un
    modulo se importa una sola vez por proceso: verde solo, rojo en la suite.

    Que este test corra bajo `entorno_limpio` y encuentre la app construida es
    exactamente la afirmacion.
    """
    assert tasks.app.main == "deruedas"
    assert tasks.app.conf.task_serializer == "json"
