"""Tests del verificador de paridad de configuracion — y su puesta en marcha.

Por que existe este archivo, que es distinto de por que existe el script:

`tools/check-config-parity.py` estaba escrito, funcionaba y daba 0 divergencias
desde el 17-ago-2026. Lo que NO estaba era ejecutandose. No aparecia en
`ci.yml`, ni en `.pre-commit-config.yaml`, ni lo invocaba ningun test. Mientras
tanto `CHANGES.md`, la tarea 4.8 y la 10.4 de C-01 lo describian como el control
que **sostiene** `ADR-013` y cierra el riesgo `R-3`.

Un verificador que nadie corre no es un control: es un documento ejecutable que
nadie ejecuta. Si alguien agregaba una variable a `Settings` sin tocar el ADR,
el repositorio entero seguia en verde y la tabla canonica se volvia mentira en
silencio. Este archivo lo pone a correr en el unico lugar que no se saltea, que
es CI — `tools/tests` ya lo corre el job `test-backend-unit`.

Se invoca el script como PROCESO, por el mismo motivo que en
`test_check_coverage.py`: lo que hace de gate es el codigo de salida.

Los casos negativos NO tocan el repositorio real. Se arma un arbol minimo en
`tmp_path` con la misma forma (`tools/`, `docs/adr/`, `.env.example`,
`backend/app/config.py`) y se copia el script adentro: el script calcula su
raiz desde `__file__`, asi que la copia lee las fuentes falsas y el repositorio
de verdad no se toca. Es lo que permite inyectar divergencias a proposito y ver
al verificador fallar — sin eso, "0 divergencias" no distingue entre un
verificador que anda y uno que devuelve 0 siempre.

Se corren desde la raiz del repositorio:

    python -m pytest tools/tests
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "tools" / "check-config-parity.py"

# Nombres inventados para las fuentes falsas. No coinciden con ninguna variable
# real del proyecto a proposito: si un test fallara, el mensaje deja claro que
# habla de un fixture y no de `ADR-013`.
COMUN = "DEMO_URL_DE_SERVICIO"
SECRETA = "DEMO_CLAVE_DE_FIRMA"


def correr(raiz: Path) -> subprocess.CompletedProcess[str]:
    """Ejecuta el verificador que vive dentro de `raiz`."""
    return subprocess.run(
        [sys.executable, str(raiz / "tools" / "check-config-parity.py")],
        capture_output=True,
        text=True,
        cwd=raiz,
        check=False,
    )


def fila_adr(nombre: str, *, sensible: bool) -> str:
    """Una fila de la tabla canonica de `ADR-013`.

    El candado al final es lo que marca la variable como sensible, y tiene que
    ser la ULTIMA celda: el verificador ancla la expresion al fin de linea.
    """
    return f"| `{nombre}` | descripcion de fixture | {'🔒' if sensible else '—'} |"


def campo_config(nombre: str, *, secreto: bool) -> str:
    tipo = "SecretStr" if secreto else "str"
    return f'    {nombre.lower()}: {tipo} = Field(..., validation_alias="{nombre}")'


def armar_raiz(
    tmp_path: Path,
    *,
    en_adr: list[tuple[str, bool]],
    # `Sequence` y no `list`: una lista es invariante, asi que `list[str]` no
    # entra en `list[str | tuple[str, str]]` y los llamadores de arriba —que
    # solo pasan nombres— dejarian de tipar.
    en_env: Sequence[str | tuple[str, str]],
    en_config: list[tuple[str, bool]],
) -> Path:
    """Arma un arbol con la forma del repositorio y el script adentro.

    Cada parametro es lo que declara UNA de las tres fuentes, para que un test
    pueda desalinearlas de a una y dejar claro cual es la divergencia.
    """
    (tmp_path / "tools").mkdir()
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "backend" / "app").mkdir(parents=True)

    shutil.copy(SCRIPT, tmp_path / "tools" / "check-config-parity.py")

    encabezado = "| Variable | Descripcion | Sensible |\n|---|---|---|\n"
    filas = "\n".join(fila_adr(n, sensible=s) for n, s in en_adr)
    (tmp_path / "docs" / "adr" / "ADR-013-variables-de-entorno.md").write_text(
        f"# ADR-013 (fixture)\n\n{encabezado}{filas}\n", encoding="utf-8"
    )

    # Un elemento suelto declara la variable sin valor; una tupla le pone uno.
    # Casi todos los tests solo necesitan el nombre — los de secretos en claro
    # son los unicos a los que el valor les importa.
    lineas = [f"{n}=" if isinstance(n, str) else f"{n[0]}={n[1]}" for n in en_env]
    (tmp_path / ".env.example").write_text("\n".join(lineas) + "\n", encoding="utf-8")

    campos = "\n".join(campo_config(n, secreto=s) for n, s in en_config)
    (tmp_path / "backend" / "app" / "config.py").write_text(
        f"class Settings(BaseSettings):\n{campos}\n", encoding="utf-8"
    )

    return tmp_path


# ── Lo que este archivo vino a arreglar ──────────────────────────────────────


def test_el_repositorio_real_no_tiene_divergencias() -> None:
    """El gate en si. Es el unico test que mira las fuentes de verdad.

    Si falla, alguien toco `Settings`, `.env.example` o `ADR-013` sin tocar los
    otros dos, y la tabla canonica dejo de describir el sistema.
    """
    resultado = correr(REPO)

    assert resultado.returncode == 0, (
        "`tools/check-config-parity.py` reporta divergencias entre `ADR-013`, "
        f"`.env.example` y `Settings`:\n{resultado.stdout}{resultado.stderr}"
    )


# ── Que el verificador realmente verifique ───────────────────────────────────


def test_tres_fuentes_alineadas_dan_cero_divergencias(tmp_path: Path) -> None:
    """El control del control: sin este, los casos negativos no prueban nada.

    Si el fixture alineado ya diera 1, los tests de abajo pasarian por el
    motivo equivocado.
    """
    raiz = armar_raiz(
        tmp_path,
        en_adr=[(COMUN, False), (SECRETA, True)],
        en_env=[COMUN, SECRETA],
        en_config=[(COMUN, False), (SECRETA, True)],
    )

    resultado = correr(raiz)

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_variable_en_el_adr_y_ausente_de_env_example_falla(tmp_path: Path) -> None:
    raiz = armar_raiz(
        tmp_path,
        en_adr=[(COMUN, False), (SECRETA, True)],
        en_env=[COMUN],  # falta la sensible
        en_config=[(COMUN, False), (SECRETA, True)],
    )

    resultado = correr(raiz)

    assert resultado.returncode == 1, resultado.stdout
    assert "no en .env.example" in resultado.stdout
    assert SECRETA in resultado.stdout


def test_variable_en_settings_y_ausente_del_adr_falla(tmp_path: Path) -> None:
    """El caso que mas importa: agregar configuracion sin registrarla.

    Es la direccion en la que la tabla canonica se vuelve mentira sin que nadie
    lo note — el codigo crece y el ADR se queda quieto.
    """
    raiz = armar_raiz(
        tmp_path,
        en_adr=[(COMUN, False)],
        en_env=[COMUN],
        en_config=[(COMUN, False), (SECRETA, True)],
    )

    resultado = correr(raiz)

    assert resultado.returncode == 1, resultado.stdout
    assert "no en ADR-013" in resultado.stdout
    assert SECRETA in resultado.stdout


def test_sensible_en_el_adr_pero_no_secretstr_falla(tmp_path: Path) -> None:
    """Declararla no alcanza. Si no es `SecretStr` se filtra por `repr`.

    Las tres fuentes cubren aca el mismo conjunto de variables: lo unico que
    diverge es el TIPO. Un verificador que solo comparara nombres pasaria este
    caso, y el enmascarado del secreto seria decorativo.
    """
    raiz = armar_raiz(
        tmp_path,
        en_adr=[(COMUN, False), (SECRETA, True)],
        en_env=[COMUN, SECRETA],
        en_config=[(COMUN, False), (SECRETA, False)],  # sensible sin SecretStr
    )

    resultado = correr(raiz)

    assert resultado.returncode == 1, resultado.stdout
    assert "NO son SecretStr" in resultado.stdout
    assert SECRETA in resultado.stdout


# ── El contrato no filtra secretos ──────────────────────────────────────────
#
# Escenario *"El contrato no filtra secretos"* de `platform/configuration`:
# "todos los campos marcados como sensibles estan vacios o contienen un valor
# evidentemente ficticio".
#
# La otra mitad del escenario —que el escaneo de secretos del pipeline no
# reporte hallazgos sobre el archivo— la sostiene `gitleaks`, y que `gitleaks`
# siga pudiendo bloquear lo sostiene `test_gates_bloqueantes.py`.
#
# Por que hace falta esto y no alcanza con gitleaks: gitleaks encuentra lo que
# PARECE un secreto —alta entropia, formatos conocidos de token—. Un
# `SMTP_PASSWORD=Verano2026` no le llama la atencion a nadie, y es exactamente
# la forma que tiene la contraseña que alguien pega sin pensar mientras hace
# andar su entorno local.


def _alineadas(tmp_path: Path, valor_secreto: str) -> Path:
    """Tres fuentes alineadas, con un valor puesto a mano en la sensible."""
    return armar_raiz(
        tmp_path,
        en_adr=[(COMUN, False), (SECRETA, True)],
        en_env=[COMUN, (SECRETA, valor_secreto)],
        en_config=[(COMUN, False), (SECRETA, True)],
    )


def test_una_sensible_vacia_pasa(tmp_path: Path) -> None:
    resultado = correr(_alineadas(tmp_path, ""))
    assert resultado.returncode == 0, resultado.stdout


def test_una_sensible_con_el_marcador_pasa(tmp_path: Path) -> None:
    """`cambiame` es la convencion del `.env.example` real."""
    resultado = correr(_alineadas(tmp_path, "cambiame"))
    assert resultado.returncode == 0, resultado.stdout


def test_una_sensible_con_el_marcador_adentro_de_un_dsn_pasa(tmp_path: Path) -> None:
    """`DATABASE_URL` no es un secreto suelto: es una URL con el secreto adentro."""
    valor = "postgresql+asyncpg://usuario:cambiame@localhost:5432/base"
    resultado = correr(_alineadas(tmp_path, valor))
    assert resultado.returncode == 0, resultado.stdout


def test_una_sensible_con_un_valor_de_verdad_falla(tmp_path: Path) -> None:
    resultado = correr(_alineadas(tmp_path, "Verano2026"))

    assert resultado.returncode == 1, resultado.stdout
    assert "ni un marcador" in resultado.stdout
    assert SECRETA in resultado.stdout


def test_el_reporte_no_imprime_el_valor_del_secreto(tmp_path: Path) -> None:
    """Denunciar la fuga no puede ser la fuga.

    La salida de este script termina en el log de una corrida de CI, que queda
    guardado y es visible para mas gente que el repositorio. Si el reporte
    imprimiera el valor, un secreto que se colo en un archivo versionado
    pasaria ademas a un log publico — y el arreglo seria peor que el problema.

    Mismo criterio que `_describir` en `app/config.py`, que nombra la variable
    y nunca su valor, y que el `--redact` de gitleaks.
    """
    valor = "Verano2026"
    resultado = correr(_alineadas(tmp_path, valor))

    assert resultado.returncode == 1
    assert valor not in resultado.stdout + resultado.stderr


def test_una_variable_comun_con_valor_de_verdad_no_dispara_nada(tmp_path: Path) -> None:
    """Solo se miran las sensibles.

    El `.env.example` real esta LLENO de valores de verdad que no son secretos
    —`API_BASE_URL=http://localhost:8000`, los puertos, los nombres de base—, y
    borrarlos volveria inservible la plantilla que el dev copia.
    """
    raiz = armar_raiz(
        tmp_path,
        en_adr=[(COMUN, False), (SECRETA, True)],
        en_env=[(COMUN, "http://localhost:8000"), (SECRETA, "cambiame")],
        en_config=[(COMUN, False), (SECRETA, True)],
    )

    resultado = correr(raiz)

    assert resultado.returncode == 0, resultado.stdout
