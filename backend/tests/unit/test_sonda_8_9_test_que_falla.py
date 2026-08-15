"""SONDA DESCARTABLE — tarea 8.9. NO MERGEAR.

Existe para responder una sola pregunta: ¿un test que falla **bloquea** de
verdad la integracion, o el pipeline lo reporta y sigue?

Una corrida verde no puede contestarla. La tarea 8.9 pide exactamente esto y
no se puede tildar sin la evidencia de un rojo real.

Este archivo se borra en el commit siguiente.
"""

from __future__ import annotations


def test_sonda_este_test_falla_a_proposito() -> None:
    """Falla siempre. Si el job de tests queda en verde, el gate no bloquea."""
    resultado = 2 + 2
    assert resultado == 5, "sonda de 8.9: fallo deliberado, esto tiene que romper el CI"
