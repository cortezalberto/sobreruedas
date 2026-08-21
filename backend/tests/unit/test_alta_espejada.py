"""Lo que el formulario de alta copia de `schemas.py` no se despega del original.

POR QUE EXISTEN ESTAS COPIAS
─────────────────────────────
`frontend-web/src/lib/vehiculo-nuevo.ts` copia seis cosas de `VehiculoCrear`:
los tres catalogos cerrados (combustible, transmision, carroceria), el año
minimo, los dos largos maximos y los formatos de dominio y chasis.

Se copian por la misma division que `ADR-034` fija para las transiciones —y que
`test_transiciones_espejadas.py` ya vigila—: QUE combustibles existen es
conocimiento de DOMINIO, igual para todos los roles, y hace falta del lado del
cliente para poder armar un desplegable. QUIEN puede dar de alta es la MATRIZ, y
eso no se copia nunca.

Los formatos y los largos tienen ademas un motivo propio, medido contra el
backend corriendo el 21-ago-2026: las reglas de `ADR-031` y la del año viven en
`model_validator(mode="after")`, que corre sobre el modelo YA armado y por eso
atribuye el error al CUERPO ENTERO —`field: "body"`, no `body.domain_plate`—. El
backend no sabe decir que campo esta mal, asi que el formulario tiene que
saberlo por su cuenta o mostrar "hay algo mal" sobre catorce campos.

POR QUE LA DERIVA ACA ES PEOR QUE EN LAS TRANSICIONES
──────────────────────────────────────────────────────
Alla, una copia atrasada deja un boton de menos: visible. Aca es mudo en las dos
direcciones. Si el backend agrega `hidrogeno` al enum, el desplegable
simplemente no lo ofrece y nadie se entera de que falta. Y si alguien AFLOJA un
limite —`color` a 100—, el frontend sigue rechazando en 60 y el usuario ve un
error por una regla que ya no existe.

POR QUE EL TEST VIVE DEL LADO DEL BACKEND
──────────────────────────────────────────
Porque aca esta el original — mismo argumento que en `test_transiciones_
espejadas.py`. Leer un literal de TypeScript desde Python es un `re` de cinco
lineas; al reves habria que leer Python desde TypeScript.

Si esto falla, **la que manda es la de `schemas.py`**: el frontend se corrige.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.modules.stock.schemas import (
    _CHASIS,
    _DOMINIO_MERCOSUR,
    _DOMINIO_VIEJO,
    ANIO_MINIMO,
    Carroceria,
    Combustible,
    Transmision,
    VehiculoCrear,
)

ESPEJO = Path(__file__).resolve().parents[3] / "frontend-web" / "src" / "lib" / "vehiculo-nuevo.ts"

# `{ valor: 'gasoline', texto: 'Nafta' },`
_OPCION = re.compile(r"\{\s*valor:\s*'([^']+)'")

# `export const LARGO_MAXIMO_COLOR = 60;`
_CONSTANTE = re.compile(r"export const (\w+) = (\d+);")

# `const DOMINIO_VIEJO = /^[A-Z]{3}[0-9]{3}$/;`
_REGEX = re.compile(r"const (\w+) = /(.+?)/[a-z]*;")


def _fuente() -> str:
    return ESPEJO.read_text(encoding="utf-8")


def _catalogo(nombre: str) -> list[str]:
    """Los `valor` de un catalogo del frontend, EN ORDEN.

    En orden y no como conjunto: el orden es lo que ve el usuario en el
    desplegable, y ademas hace que el mensaje de un fallo diga exactamente donde
    difieren.
    """
    bloque = _fuente().split(f"export const {nombre}")[1].split("];")[0]
    return [coincidencia.group(1) for coincidencia in _OPCION.finditer(bloque)]


def _constantes() -> dict[str, int]:
    return {
        coincidencia.group(1): int(coincidencia.group(2))
        for coincidencia in _CONSTANTE.finditer(_fuente())
    }


def _regexes() -> dict[str, str]:
    return {
        coincidencia.group(1): coincidencia.group(2) for coincidencia in _REGEX.finditer(_fuente())
    }


def _largo_maximo(campo: str) -> int:
    """El `maxLength` de un campo, leido del JSON Schema y no de la anotacion.

    `engine_number` es `Annotated[str, Field(max_length=30)] | None`, asi que su
    constraint queda ADENTRO de un `anyOf` y no en `model_fields[...].metadata`.
    El JSON Schema aplana las dos formas y sirve para los dos campos.
    """
    esquema = VehiculoCrear.model_json_schema()["properties"][campo]
    if "maxLength" in esquema:
        return int(esquema["maxLength"])
    for rama in esquema["anyOf"]:
        if "maxLength" in rama:
            return int(rama["maxLength"])
    raise AssertionError(f"`{campo}` no declara `maxLength` en el schema")


# ── Contrapesos ─────────────────────────────────────────────────────────────
#
# Sin estos, un parseo que deja de matchear compara dos cosas vacias y pasa en
# verde. Un guardian que se apaga solo es peor que ninguno: el otro al menos se
# nota que falta.


def test_el_archivo_del_espejo_existe() -> None:
    assert ESPEJO.is_file(), f"no esta {ESPEJO}"


def test_los_catalogos_del_frontend_no_estan_vacios() -> None:
    assert len(_catalogo("COMBUSTIBLES")) == len(Combustible)
    assert len(_catalogo("TRANSMISIONES")) == len(Transmision)
    assert len(_catalogo("CARROCERIAS")) == len(Carroceria)


def test_el_frontend_declara_las_constantes_que_se_comparan() -> None:
    declaradas = _constantes()
    for nombre in ("ANIO_MINIMO", "LARGO_MAXIMO_COLOR", "LARGO_MAXIMO_MOTOR"):
        assert nombre in declaradas, f"el frontend ya no declara `{nombre}`"


def test_el_frontend_declara_los_formatos_que_se_comparan() -> None:
    declarados = _regexes()
    for nombre in ("DOMINIO_VIEJO", "DOMINIO_MERCOSUR", "CHASIS"):
        assert nombre in declarados, f"el frontend ya no declara `{nombre}`"


# ── Las comparaciones ───────────────────────────────────────────────────────


def test_los_tres_catalogos_dicen_lo_mismo() -> None:
    """Los `StrEnum` de `schemas.py`, valor por valor y en orden."""
    for nombre, enumeracion in (
        ("COMBUSTIBLES", Combustible),
        ("TRANSMISIONES", Transmision),
        ("CARROCERIAS", Carroceria),
    ):
        backend = [miembro.value for miembro in enumeracion]
        frontend = _catalogo(nombre)

        assert frontend == backend, (
            f"`{nombre}` se despego de `{enumeracion.__name__}`.\n"
            f"  backend:  {backend}\n"
            f"  frontend: {frontend}\n"
            f"  solo en el backend:  {sorted(set(backend) - set(frontend))}\n"
            f"  solo en el frontend: {sorted(set(frontend) - set(backend))}"
        )


def test_el_anio_minimo_es_el_mismo() -> None:
    assert _constantes()["ANIO_MINIMO"] == ANIO_MINIMO


def test_los_largos_maximos_son_los_mismos() -> None:
    """`color` y `engine_number`.

    Que el frontend sea MAS estricto tampoco esta bien, aunque no produzca un
    rechazo del backend: seria un error por una regla que no existe, y quien lo
    ve no tiene forma de saber que la regla se aflojo.
    """
    declaradas = _constantes()

    assert declaradas["LARGO_MAXIMO_COLOR"] == _largo_maximo("color")
    assert declaradas["LARGO_MAXIMO_MOTOR"] == _largo_maximo("engine_number")


def test_los_formatos_de_dominio_y_chasis_son_los_mismos() -> None:
    """Comparacion TEXTUAL de los patrones.

    Las dos sintaxis coinciden para lo que estos patrones usan —clases,
    cuantificadores y anclas—, asi que comparar el texto es exacto y no una
    aproximacion. Si algun dia hiciera falta algo que se escriba distinto en
    Python y en JavaScript, este test lo va a marcar, y eso tambien es correcto:
    esa diferencia hay que mirarla a mano.
    """
    declarados = _regexes()

    assert declarados["DOMINIO_VIEJO"] == _DOMINIO_VIEJO.pattern
    assert declarados["DOMINIO_MERCOSUR"] == _DOMINIO_MERCOSUR.pattern
    assert declarados["CHASIS"] == _CHASIS.pattern


def test_el_formulario_no_copia_la_matriz_de_permisos() -> None:
    """La otra mitad de `ADR-034`, y la que importa mas.

    Se vigilan los DOS archivos del alta: el modulo de logica y el componente.
    El desplegable de combustible es dominio; un `if (rol === 'manager')` para
    esconder el boton de guardar seria una segunda fuente de verdad sobre
    permisos, y la del cliente es la que se edita con las herramientas del
    navegador.
    """
    componente = (
        Path(__file__).resolve().parents[3]
        / "frontend-web"
        / "src"
        / "components"
        / "FormularioDeVehiculo.tsx"
    )
    assert componente.is_file(), f"no esta {componente}"

    for archivo in (ESPEJO, componente):
        # Se busca en el CODIGO, no en los comentarios: los encabezados explican
        # por que los permisos no se copian, y para explicarlo los nombran.
        codigo = "\n".join(
            linea
            for linea in archivo.read_text(encoding="utf-8").splitlines()
            if not linea.lstrip().startswith(("*", "//", "/*"))
        )

        for rol in ("manager", "salesperson", "admin_staff", "super_admin"):
            assert rol not in codigo, f"{archivo.name} decide permisos: menciona '{rol}'"
