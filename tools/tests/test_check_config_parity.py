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
    en_env: list[str],
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

    (tmp_path / ".env.example").write_text(
        "\n".join(f"{n}=" for n in en_env) + "\n", encoding="utf-8"
    )

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
