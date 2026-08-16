"""Emisor de tokens de prueba — C-02, tareas 3.1 a 3.3 y 5.10.

POR QUE NO SE LEVANTA KEYCLOAK
──────────────────────────────
Lo que hay que probar es que **la aplicacion valida bien**: que rechace una
firma que no verifica, un token vencido, uno de otro emisor. Para eso hace falta
poder EMITIR tokens malos a voluntad, y un Keycloak de verdad se niega — emite
tokens buenos, que es su trabajo.

Un proveedor real en la suite tampoco probaria mejor: probaria a Keycloak, que
ya esta probado, y ataria cada corrida a que un contenedor arranque. El compose
de tests no lo incluye justamente por eso.

Aca se genera un par de claves RSA en memoria y se firma con el. La aplicacion
no distingue este emisor de Keycloak: recibe un JWKS y un token RS256, que es
todo lo que mira.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

EMISOR = "https://keycloak.de-prueba/realms/deruedas-test"
RECEPTOR = "backend"


class EmisorDePrueba:
    """Un proveedor de identidad de mentira, con su par de claves.

    Cada instancia tiene su propia clave. Dos instancias sirven para probar la
    ROTACION: el proveedor "rota" cuando aparece un emisor nuevo con otro `kid`.
    """

    def __init__(self, kid: str | None = None, *, emisor: str = EMISOR) -> None:
        self.kid = kid or f"clave-{uuid.uuid4().hex[:8]}"
        self.emisor = emisor
        # 2048 y no 4096: es suficiente para una firma de prueba y generar la
        # clave es lo mas lento de estos tests. Con 4096 la suite se duplica.
        self._privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    @property
    def jwks(self) -> dict[str, list[dict[str, Any]]]:
        """El documento que la aplicacion se baja del proveedor."""
        clave = jwt.algorithms.RSAAlgorithm.to_jwk(self._privada.public_key(), as_dict=True)
        return {"keys": [{**clave, "kid": self.kid, "use": "sig", "alg": "RS256"}]}

    def firmar(
        self,
        *,
        sub: str | None = None,
        tenant_id: uuid.UUID | str | None = None,
        role: str | None = "manager",
        emisor: str | None = None,
        receptor: str | None = RECEPTOR,
        vence_en: timedelta = timedelta(minutes=5),
        extra: dict[str, Any] | None = None,
        omitir: tuple[str, ...] = (),
    ) -> str:
        """Un token a medida. Todo es parametrizable porque todo hay que probarlo.

        `vence_en` negativo produce un token ya vencido; `omitir` saca claims
        para probar que la aplicacion los exige en vez de suponerlos.
        """
        ahora = datetime.now(UTC)
        claims: dict[str, Any] = {
            "sub": sub or str(uuid.uuid4()),
            "iss": emisor if emisor is not None else self.emisor,
            "aud": receptor,
            "iat": ahora,
            "exp": ahora + vence_en,
            "tenant_id": str(tenant_id) if tenant_id is not None else str(uuid.uuid4()),
            "role": role,
            **(extra or {}),
        }
        for clave in omitir:
            claims.pop(clave, None)
        # `role=None` se trata como ausente: un rol nulo no es un rol.
        if claims.get("role") is None:
            claims.pop("role", None)

        return jwt.encode(claims, self._privada, algorithm="RS256", headers={"kid": self.kid})

    def firmar_con_otra_clave(self, **kwargs: Any) -> str:
        """Un token que DICE ser de este emisor pero lo firmo otro.

        Es el ataque, no un descuido: el `kid` del encabezado apunta a la clave
        publicada, y la firma no cierra contra ella.
        """
        impostor = EmisorDePrueba(kid=self.kid, emisor=self.emisor)
        return impostor.firmar(**kwargs)
