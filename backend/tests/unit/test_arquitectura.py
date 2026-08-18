"""Reglas de arquitectura que se verifican solas — C-02, tarea 5.12.

POR QUE UN TEST Y NO UNA CONVENCION ESCRITA
────────────────────────────────────────────
`sesion_de_plataforma` no establece contexto de tenant. Es legitima para
migraciones, tareas de plataforma y el backoffice cross-tenant bajo el espacio
administrativo — y en cualquier otro lado es un agujero en el control mas
critico del sistema.

La tentacion de usarla es real y no es malintencionada: cuando una consulta no
anda porque falta el contexto, cambiarla por la version "sin tenant" hace que
ande. El sintoma desaparece y el aislamiento tambien.

Una regla que solo vive en un docstring se rompe el dia que alguien tiene apuro.
Esta se verifica en cada corrida (`design.md` D-4).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ_APP = Path(__file__).resolve().parent.parent.parent / "app"

PUERTA_SIN_TENANT = "sesion_de_plataforma"

# Los UNICOS lugares donde puede aparecer. La lista se escribe a mano a
# proposito: agregar una entrada aca es una decision que se revisa en un diff,
# no algo que se autodetecte.
#
# `db/session.py` no esta en la lista y no hace falta: la define, y definir no
# es usar — el analisis mira referencias, no la declaracion.
PERMITIDOS = (
    # Backoffice cross-tenant. Es el unico espacio de rutas que legitimamente
    # consulta por encima de los tenants (ADR-017: rol de plataforma).
    "modules/admin/",
)

# La SEGUNDA puerta sin contexto de tenant, y no es la misma que la de arriba.
#
# `sesion_de_plataforma` consulta por encima de los tenants: los datos tienen
# dueno y ella lo ignora. `sesion_de_catalogo` consulta tablas SIN dueno —las de
# `EXENTAS_DE_RLS`, que no llevan `tenant_id`—, donde no hay contexto que
# establecer.
#
# Listas separadas a proposito: fundirlas dejaria que un uso de catalogo
# habilite tacitamente uno cross-tenant en la misma carpeta.
PUERTA_DE_CATALOGO = "sesion_de_catalogo"

PERMITIDOS_CATALOGO = (
    # `plans` es catalogo comercial compartido (`RN-MT-09`). El router del
    # modulo lo publica; el resto del modulo trabaja con datos de tenant y usa
    # `sesion_de_tenant`.
    "modules/tenancy/router.py",
)


def usos_de(nombre: str, raiz: Path, *, incluir_definiciones: bool = False) -> set[str]:
    """Rutas de los `.py` bajo `raiz` que REFERENCIAN `nombre`.

    Por AST y no por texto: `grep` marcaria una mencion en un comentario o en un
    docstring, y este test se volveria ruido que alguien termina desactivando.
    Lo que interesa es el uso real — una importacion o una llamada.

    `incluir_definiciones` DISTINGUE DOS CONTROLES QUE NO SON EL MISMO
    ─────────────────────────────────────────────────────────────────
    Para `sesion_de_plataforma` interesa quien la USA: `db/session.py` la define
    y eso no es una infraccion, es su casa. Definir no es usar.

    Para `verify_password` es al reves: que la aplicacion **defina** esa funcion
    ES la infraccion — significa que esta verificando contrasenas, que es lo que
    el Articulo 3 prohibe. Ahi la definicion es justamente lo que hay que cazar.

    Con un solo criterio, uno de los dos controles queda ciego.
    """
    encontrados: set[str] = set()

    for archivo in raiz.rglob("*.py"):
        try:
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover — un .py roto ya rompe otra cosa
            continue

        for nodo in ast.walk(arbol):
            usado = (
                (isinstance(nodo, ast.Name) and nodo.id == nombre)
                or (isinstance(nodo, ast.Attribute) and nodo.attr == nombre)
                or (
                    isinstance(nodo, ast.ImportFrom)
                    and any(alias.name == nombre for alias in nodo.names)
                )
            )
            if not usado and incluir_definiciones:
                usado = (
                    isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
                    and nodo.name == nombre
                )
            if usado:
                encontrados.add(archivo.relative_to(raiz).as_posix())
                break

    return encontrados


def fuera_de_lugar(usos: set[str]) -> set[str]:
    return {ruta for ruta in usos if not any(ruta.startswith(p) for p in PERMITIDOS)}


# ── La regla ─────────────────────────────────────────────────────────────────


def test_la_sesion_sin_tenant_no_se_usa_fuera_del_espacio_administrativo() -> None:
    infractores = fuera_de_lugar(usos_de(PUERTA_SIN_TENANT, RAIZ_APP))

    assert not infractores, (
        f"`{PUERTA_SIN_TENANT}` no establece contexto de tenant y aparece fuera del "
        f"espacio administrativo: {sorted(infractores)}. "
        "Si el uso es legitimo —una tarea de plataforma— agregalo a PERMITIDOS "
        "con su motivo; si no, usa `sesion_de_tenant`"
    )


def test_la_sesion_de_catalogo_no_se_usa_fuera_de_donde_viven_los_catalogos() -> None:
    """La segunda puerta sin contexto de tenant, con su propia lista.

    `sesion_de_catalogo` consulta tablas que no tienen dueno —`plans` y
    companía, todas en `EXENTAS_DE_RLS`—, asi que no hay contexto que
    establecer. Eso la hace legitima donde vive un catalogo y en ningun otro
    lado: sobre una tabla con `tenant_id` no devuelve filas, y el que se
    encuentre con el listado vacio va a "arreglarlo" cambiando la sesion.

    Tiene lista propia y no comparte la de `sesion_de_plataforma` a proposito.
    Fundirlas dejaria que un uso de catalogo habilite tacitamente uno
    cross-tenant en la misma carpeta, que es justo lo que cada lista existe
    para no permitir.
    """
    infractores = {
        ruta
        for ruta in usos_de(PUERTA_DE_CATALOGO, RAIZ_APP)
        if not any(ruta.startswith(p) for p in PERMITIDOS_CATALOGO)
    }

    assert not infractores, (
        f"`{PUERTA_DE_CATALOGO}` aparece fuera de donde viven los catalogos: "
        f"{sorted(infractores)}. Si la tabla lleva `tenant_id`, la sesion correcta "
        "es `sesion_de_tenant` — esta no te va a devolver ninguna fila"
    )


# ── Probar el detector, no solo usarlo ───────────────────────────────────────


def test_el_detector_encuentra_un_uso_infractor_de_catalogo(tmp_path: Path) -> None:
    """El mismo detector, ejercitado sobre la segunda puerta.

    Sin esto, el test de arriba pasaria igual el dia que `usos_de` dejara de
    encontrar la referencia — y una lista de permitidos sobre un detector ciego
    autoriza todo.
    """
    infractor = tmp_path / "modules" / "stock" / "servicio.py"
    infractor.parent.mkdir(parents=True)
    infractor.write_text(
        "from app.db.session import sesion_de_catalogo\n"
        "async def listar():\n"
        "    async with sesion_de_catalogo() as s:\n"
        "        return s\n",
        encoding="utf-8",
    )

    permitido = tmp_path / "modules" / "tenancy" / "router.py"
    permitido.parent.mkdir(parents=True)
    permitido.write_text(
        "from app.db.session import sesion_de_catalogo\n"
        "async def planes():\n"
        "    async with sesion_de_catalogo() as s:\n"
        "        return s\n",
        encoding="utf-8",
    )

    usos = usos_de(PUERTA_DE_CATALOGO, tmp_path)
    infractores = {
        ruta for ruta in usos if not any(ruta.startswith(p) for p in PERMITIDOS_CATALOGO)
    }

    assert infractores == {"modules/stock/servicio.py"}


def test_el_detector_encuentra_un_uso_infractor(tmp_path: Path) -> None:
    """Hoy la regla pasa porque nadie la usa todavia.

    Tambien pasaria si el analisis estuviera roto y devolviera vacio siempre —
    que es como un control de arquitectura se apaga sin que nadie se entere. Aca
    se le pone delante un infractor de verdad.
    """
    modulo = tmp_path / "modules" / "stock" / "servicio.py"
    modulo.parent.mkdir(parents=True)
    modulo.write_text(
        "from app.db.session import sesion_de_plataforma\n"
        "\n"
        "async def listar_todo():\n"
        "    async with sesion_de_plataforma() as sesion:\n"
        "        return sesion\n",
        encoding="utf-8",
    )

    infractores = fuera_de_lugar(usos_de(PUERTA_SIN_TENANT, tmp_path))

    assert infractores == {"modules/stock/servicio.py"}


def test_el_detector_no_marca_el_espacio_administrativo(tmp_path: Path) -> None:
    """Contrapeso: si marcara todo, la regla seria inservible y se desactivaria."""
    modulo = tmp_path / "modules" / "admin" / "servicio.py"
    modulo.parent.mkdir(parents=True)
    modulo.write_text(
        "from app.db.session import sesion_de_plataforma\n"
        "\n"
        "async def listar_tenants():\n"
        "    async with sesion_de_plataforma() as sesion:\n"
        "        return sesion\n",
        encoding="utf-8",
    )

    assert fuera_de_lugar(usos_de(PUERTA_SIN_TENANT, tmp_path)) == set()


@pytest.mark.parametrize(
    ("contenido", "por_que"),
    [
        ('"""Habla de sesion_de_plataforma en el docstring."""\n', "docstring"),
        ("# sesion_de_plataforma va aca algun dia\n", "comentario"),
        ('MENSAJE = "no uses sesion_de_plataforma"\n', "cadena"),
    ],
)
def test_el_detector_no_marca_menciones_que_no_son_usos(
    tmp_path: Path, contenido: str, por_que: str
) -> None:
    """Un detector que marca comentarios se vuelve ruido y termina desactivado."""
    modulo = tmp_path / "modules" / "stock" / "nota.py"
    modulo.parent.mkdir(parents=True)
    modulo.write_text(contenido, encoding="utf-8")

    assert usos_de(PUERTA_SIN_TENANT, tmp_path) == set(), f"marco un {por_que}"


# ── La aplicacion no sabe de contrasenas ─────────────────────────────────────
#
# Regla dura 2 y Articulo 3: la autenticacion se delega ENTERAMENTE a Keycloak.
# La aplicacion nunca recibe, hashea ni verifica una contrasena.
#
# Es una afirmacion sobre lo que NO existe, y esas son justo las que se sostienen
# solas hasta el dia que dejan de hacerlo. La plantilla de `fastapi-templates`
# —que este proyecto usa— trae auth local con hash de contrasenas: el override
# `O-1` la prohibe, y esto es lo que lo verifica en vez de confiar en que nadie
# copie y pegue.

NOMBRES_DE_CONTRASENA = (
    "password_hash",
    "verify_password",
    "get_password_hash",
    "hash_password",
    "check_password",
    # `mfa_secret` se suma el 17-ago-2026, y no es una precaucion abstracta:
    # `spec-tecnica` 3.3 le da a `users` una columna `mfa_secret varchar(255)`
    # ("cifrado simetricamente con KMS"), justo al lado de `password_hash`.
    #
    # `IN-06` documento la contradiccion de la contrasena y paso de largo por la
    # de al lado. Es el mismo error: `plan-seguridad` 112 pone la MFA del lado
    # de Keycloak ("provee auth e MFA opcional", "custodia sus credenciales") y
    # `ADR-026` ya retiro los endpoints `/auth/mfa/*` porque el TOTP es suyo.
    #
    # Un secreto TOTP en nuestra base es una credencial en nuestra base, este
    # cifrada o no. Se agrega ANTES de que exista la migracion de `users`, que
    # es cuando la columna se copiaria de la spec sin que nadie la mire.
    "mfa_secret",
)

# Librerias de hashing de contrasenas. Que aparezca una importada ya es la senal:
# no hay ningun uso legitimo en este backend.
LIBRERIAS_DE_HASHING = ("passlib", "bcrypt", "argon2")


def importaciones_de(raiz: Path) -> dict[str, set[str]]:
    """Modulos importados por cada `.py` bajo `raiz`."""
    por_archivo: dict[str, set[str]] = {}

    for archivo in raiz.rglob("*.py"):
        try:
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue

        importados: set[str] = set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                importados.update(alias.name.split(".")[0] for alias in nodo.names)
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                importados.add(nodo.module.split(".")[0])

        if importados:
            por_archivo[archivo.relative_to(raiz).as_posix()] = importados

    return por_archivo


def test_la_aplicacion_no_maneja_contrasenas() -> None:
    """`platform/identity` · escenario *No hay verificación local de credenciales*."""
    encontrados = {
        nombre: sorted(usos_de(nombre, RAIZ_APP, incluir_definiciones=True))
        for nombre in NOMBRES_DE_CONTRASENA
        if usos_de(nombre, RAIZ_APP, incluir_definiciones=True)
    }

    assert not encontrados, (
        f"la aplicacion maneja contrasenas: {encontrados}. "
        "La autenticacion se delega ENTERAMENTE a Keycloak (regla dura 2, "
        "Art. 3, ADR-007, override O-1)"
    )


def test_la_aplicacion_no_importa_ninguna_libreria_de_hashing_de_contrasenas() -> None:
    """El otro lado del mismo control.

    Los nombres se pueden esquivar llamando a la funcion de otra forma; la
    importacion no. Juntos cubren lo que cada uno deja pasar.
    """
    infractores = {
        archivo: sorted(importados & set(LIBRERIAS_DE_HASHING))
        for archivo, importados in importaciones_de(RAIZ_APP).items()
        if importados & set(LIBRERIAS_DE_HASHING)
    }

    assert not infractores, f"librerias de hashing de contrasenas importadas: {infractores}"


def test_el_detector_de_contrasenas_encuentra_un_infractor(tmp_path: Path) -> None:
    """Probar el detector: hoy los dos de arriba pasan porque no hay nada."""
    modulo = tmp_path / "modules" / "auth" / "servicio.py"
    modulo.parent.mkdir(parents=True)
    modulo.write_text(
        "import passlib\n"
        "\n"
        "def verify_password(plana, hasheada):\n"
        "    return passlib.verify(plana, hasheada)\n",
        encoding="utf-8",
    )

    assert usos_de("verify_password", tmp_path, incluir_definiciones=True) == {
        "modules/auth/servicio.py"
    }
    # Y sin el flag NO aparece: es una definicion, no un uso. Las dos
    # semanticas son distintas y este assert lo deja fijado.
    assert usos_de("verify_password", tmp_path) == set()
    assert "passlib" in importaciones_de(tmp_path)["modules/auth/servicio.py"]


def test_el_detector_encuentra_el_uso_por_atributo(tmp_path: Path) -> None:
    """`from app.db import session` y despues `session.sesion_de_plataforma()`.

    Es la forma de esquivar el detector sin proponerselo: importar el modulo en
    vez del nombre. Si esta via no se cubriera, la regla seria evitable por
    accidente.
    """
    modulo = tmp_path / "modules" / "stock" / "otro.py"
    modulo.parent.mkdir(parents=True)
    modulo.write_text(
        "from app.db import session\n"
        "\n"
        "async def listar():\n"
        "    async with session.sesion_de_plataforma() as s:\n"
        "        return s\n",
        encoding="utf-8",
    )

    assert fuera_de_lugar(usos_de(PUERTA_SIN_TENANT, tmp_path)) == {"modules/stock/otro.py"}
