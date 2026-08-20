#!/usr/bin/env python3
"""Verifica que `.env.example`, `Settings` y `ADR-013` digan lo mismo.

Tarea 4.8 de C-01 (T-004).

Las tres fuentes tienen que cubrir el MISMO conjunto de variables:

  docs/adr/ADR-013-variables-de-entorno.md   la tabla canonica (35)
  .env.example                                la plantilla que copia el dev (35)
  backend/app/config.py                       los 11 grupos de Settings (32)

La diferencia de 3 es el bloque `Frontend` (NEXTAUTH_SECRET, NEXTAUTH_URL,
NEXT_PUBLIC_API_BASE_URL): lo lee Next.js y no pasa por el backend. Esta
excluido a proposito y de forma explicita, no por descuido.

Se parsea `config.py` como TEXTO, con expresiones regulares sobre los
`validation_alias`. Es a proposito: importar el modulo exigiria pydantic
instalado y un entorno valido, y esto tiene que poder correr en cualquier lado,
incluido un hook de pre-commit sin dependencias.

Uso:
    python tools/check-config-parity.py

Salida: 0 si las tres coinciden, 1 si divergen.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ADR = REPO / "docs" / "adr" / "ADR-013-variables-de-entorno.md"
ENV_EXAMPLE = REPO / ".env.example"
CONFIG = REPO / "backend" / "app" / "config.py"

# Las lee Next.js, no el backend. Nunca van a estar en Settings.
SOLO_FRONTEND = {"NEXTAUTH_SECRET", "NEXTAUTH_URL", "NEXT_PUBLIC_API_BASE_URL"}

RE_ADR = re.compile(r"^\| `([A-Z][A-Z0-9_]*)` \|", re.M)
RE_ENV = re.compile(r"^([A-Z][A-Z0-9_]*)=", re.M)
RE_ALIAS = re.compile(r'validation_alias="([A-Z][A-Z0-9_]*)"')
# Fila de tabla del ADR cuya ultima celda es el candado de sensible.
RE_ADR_SENSIBLE = re.compile(r"^\| `([A-Z][A-Z0-9_]*)` \|.*\| \U0001f512 \|$", re.M)
# Campo de config.py declarado SecretStr (opcional o no).
RE_SECRETO = re.compile(
    r"(?:SecretStr|SecretoOpcional)[^=]*=\s*Field\([^)]*validation_alias=\"([A-Z0-9_]+)\"", re.S
)
# Asignacion de `.env.example`, con su valor. `RE_ENV` solo captura el nombre.
RE_ENV_CON_VALOR = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$", re.M)

# El marcador de "esto lo completas vos". Es la convencion del `.env.example`
# real, y vale tambien adentro de un DSN: `DATABASE_URL` no es un secreto
# suelto, es una URL con el secreto adentro.
MARCADOR = "cambiame"

# Sensibles cuyo valor de ejemplo NO es un marcador, una por una y con motivo —
# mismo criterio que las exclusiones de cobertura de ADR-014: una excepcion que
# nadie puede auditar es un agujero. Agregar una entrada acá es un diff visible;
# aflojar la regla, no.
SENSIBLES_CON_VALOR_PUBLICO = {
    # Nombre de usuario del OpenSearch del compose local, no una credencial. La
    # credencial del par, OPENSEARCH_PASSWORD, va con marcador.
    "OPENSEARCH_USER": "admin",
    # Identificador de acceso por defecto de MinIO, publicado en su propia
    # documentacion. El secreto del par, S3_SECRET_KEY, va con marcador.
    "S3_ACCESS_KEY": "minioadmin",
}


def leer(path: Path) -> str:
    if not path.exists():
        sys.exit(f"[FAIL] falta {path.relative_to(REPO)}")
    return path.read_text(encoding="utf-8")


def informar(titulo: str, faltantes: set[str]) -> int:
    if not faltantes:
        return 0
    print(f"  [FAIL] {titulo}")
    for nombre in sorted(faltantes):
        print(f"           {nombre}")
    return 1


def secretos_en_claro(adr_txt: str, env_txt: str) -> set[str]:
    """Sensibles cuyo valor en `.env.example` no es vacio ni un marcador.

    Es la mitad del escenario *"El contrato no filtra secretos"* que `gitleaks`
    no cubre: gitleaks encuentra lo que PARECE un secreto —alta entropia,
    formatos conocidos de token—, y un `SMTP_PASSWORD=Verano2026` no le llama la
    atencion a nadie. Es justo la forma que tiene la contraseña que alguien pega
    sin pensar mientras hace andar su entorno local.

    ⚠️ Devuelve NOMBRES, nunca valores. Ver `informar`.
    """
    sensibles = set(RE_ADR_SENSIBLE.findall(adr_txt))
    valores = dict(RE_ENV_CON_VALOR.findall(env_txt))

    culpables = set()
    for nombre in sensibles:
        valor = valores.get(nombre, "").strip()
        if not valor or MARCADOR in valor.lower():
            continue
        if valor == SENSIBLES_CON_VALOR_PUBLICO.get(nombre):
            continue
        culpables.add(nombre)
    return culpables


def main() -> int:
    adr_txt, env_txt, cfg_txt = leer(ADR), leer(ENV_EXAMPLE), leer(CONFIG)

    adr = set(RE_ADR.findall(adr_txt))
    env = set(RE_ENV.findall(env_txt))
    cfg = set(RE_ALIAS.findall(cfg_txt))
    adr_backend = adr - SOLO_FRONTEND

    print()
    print("Paridad de configuracion")
    print("-----------------------------------------------------------------")
    print(f"  ADR-013 (canonica)      : {len(adr)}")
    print(f"  .env.example            : {len(env)}")
    print(f"  Settings (backend)      : {len(cfg)}")
    print(f"  Solo frontend, excluidas: {len(SOLO_FRONTEND)}")
    print()

    fallas = 0
    fallas += informar("en ADR-013 y no en .env.example", adr - env)
    fallas += informar("en .env.example y no en ADR-013", env - adr)
    fallas += informar("en ADR-013 (backend) y no en Settings", adr_backend - cfg)
    fallas += informar("en Settings y no en ADR-013", cfg - adr)
    fallas += informar("en Settings pero marcadas como solo-frontend", cfg & SOLO_FRONTEND)

    # Que una variable este declarada no alcanza: si ADR-013 la marca sensible,
    # tiene que ser SecretStr. Si no, se filtra por repr y el enmascarado es
    # decorativo.
    adr_sensibles = set(RE_ADR_SENSIBLE.findall(adr_txt)) - SOLO_FRONTEND
    cfg_secretos = set(RE_SECRETO.findall(cfg_txt))
    print(f"  Sensibles en ADR-013    : {len(adr_sensibles)} (backend)")
    print(f"  SecretStr en Settings   : {len(cfg_secretos)}")
    print()
    fallas += informar(
        "marcadas sensibles en ADR-013 pero NO son SecretStr", adr_sensibles - cfg_secretos
    )
    fallas += informar(
        "son SecretStr pero ADR-013 no las marca sensibles", cfg_secretos - adr_sensibles
    )

    # Acá NO se filtra por SOLO_FRONTEND: `NEXTAUTH_SECRET` no pasa por
    # `Settings`, pero vive en el mismo `.env.example` versionado y filtra
    # exactamente igual.
    fallas += informar(
        "sensibles con un valor en .env.example que no es vacio ni un marcador",
        secretos_en_claro(adr_txt, env_txt),
    )

    print("-----------------------------------------------------------------")
    if fallas:
        print(f"  Divergencias: {fallas}  [FAIL]\n")
        return 1
    print("  Divergencias: 0  [OK]\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
