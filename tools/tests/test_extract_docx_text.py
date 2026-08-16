"""Tests del extractor de texto OOXML — punto ciego de gitleaks en C-01.

Por que existe este archivo: el job `security` corre `gitleaks detect` sobre el
repositorio, y gitleaks lee la historia con `git log -p`. Los `.docx` salen ahi
como "Binary files ... differ", asi que el escaner los declara limpios **sin
leer un byte**. Son 13 documentos y ~1,5 MB de texto sobre los que el gate de
secretos hoy no dice nada, aunque la spec de `delivery-pipeline` exija bloquear
ante *cualquier* deteccion.

Este extractor no busca secretos: convierte los documentos en texto plano para
que el escaner de siempre, con su version fijada, pueda hacer su trabajo.

Se invoca el script como PROCESO, no importando funciones, por el mismo motivo
que en `test_check_coverage.py`: lo que el pipeline consume es el codigo de
salida y los archivos que quedan en disco, y eso es lo que hay que probar.

Se corren desde la raiz del repositorio:

    python -m pytest tools/tests
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "tools" / "extract-docx-text.py"

# La clave de ejemplo de la documentacion de AWS. Se elige a proposito porque
# gitleaks la tiene en su ALLOWLIST y no la marca: este archivo se commitea al
# repositorio, y un valor con forma de credencial de verdad haria fallar el job
# de seguridad contra su propio test.
#
# Que este allowlisteada no debilita nada de lo que se prueba aca: estos tests
# verifican la EXTRACCION, no la deteccion. Que gitleaks bloquee sobre el texto
# extraido se comprobo aparte, con credenciales no allowlisteadas plantadas en
# un .docx real — ver el comentario del paso "gitleaks — documentos OOXML" en
# `.github/workflows/ci.yml`.
SECRETO = "AKIAIOSFODNN7EXAMPLE"


def documento_ooxml(destino: Path, partes: dict[str, str]) -> Path:
    """Escribe un zip con la forma minima de un archivo OOXML.

    Un `.docx` real trae decenas de partes; para este contrato solo importa que
    sea un zip con XML adentro. Se le pasan las partes que el test necesita.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w") as zf:
        for nombre, contenido in partes.items():
            zf.writestr(nombre, contenido)
    return destino


def parrafos(*textos: str) -> str:
    """Arma el `word/document.xml` de un docx con un parrafo por texto."""
    cuerpo = "".join(f"<w:p><w:r><w:t>{texto}</w:t></w:r></w:p>" for texto in textos)
    return f'<?xml version="1.0"?><w:document><w:body>{cuerpo}</w:body></w:document>'


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Un repositorio git de verdad: el extractor solo mira lo versionado."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def versionar(repo: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)


def correr(repo: Path, destino: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--destino", str(destino)],
        capture_output=True,
        text=True,
        cwd=REPO,
    )


def texto_extraido(destino: Path) -> str:
    """Todo lo que quedo en el directorio de salida, concatenado."""
    return "\n".join(
        archivo.read_text(encoding="utf-8") for archivo in sorted(destino.rglob("*.txt"))
    )


# ── Lo que el gate tiene que ver ──────────────────────────────────────────────


def test_el_texto_de_un_docx_queda_legible_para_el_escaner(
    repo: Path, tmp_path: Path
) -> None:
    """El caso que hoy pasa inadvertido: un secreto adentro de un documento."""
    documento_ooxml(
        repo / "docs" / "constitucion.docx",
        {"word/document.xml": parrafos("Credencial de servicio", SECRETO)},
    )
    versionar(repo)
    destino = tmp_path / "salida"

    resultado = correr(repo, destino)

    assert resultado.returncode == 0, resultado.stderr
    assert SECRETO in texto_extraido(destino)


def test_extrae_todos_los_formatos_ooxml_no_solo_docx(
    repo: Path, tmp_path: Path
) -> None:
    """Triangulacion: una planilla esconde un secreto igual de bien que un texto."""
    documento_ooxml(
        repo / "planilla.xlsx",
        {
            "xl/sharedStrings.xml": (
                f"<sst><si><t>usuario</t></si><si><t>{SECRETO}</t></si></sst>"
            )
        },
    )
    documento_ooxml(
        repo / "presentacion.pptx",
        {"ppt/slides/slide1.xml": "<p:sld><a:t>token=abc123</a:t></p:sld>"},
    )
    versionar(repo)
    destino = tmp_path / "salida"

    resultado = correr(repo, destino)

    assert resultado.returncode == 0, resultado.stderr
    extraido = texto_extraido(destino)
    assert SECRETO in extraido
    assert "token=abc123" in extraido


def test_el_nombre_del_archivo_extraido_apunta_al_documento_original(
    repo: Path, tmp_path: Path
) -> None:
    """Un hallazgo sirve solo si se puede rastrear hasta el documento fuente."""
    documento_ooxml(
        repo / "autos" / "deRuedas-constitucion.docx",
        {"word/document.xml": parrafos(SECRETO)},
    )
    versionar(repo)
    destino = tmp_path / "salida"

    correr(repo, destino)

    nombres = [archivo.name for archivo in destino.rglob("*.txt")]
    assert len(nombres) == 1
    assert "autos" in nombres[0]
    assert "deRuedas-constitucion.docx" in nombres[0]


def test_las_etiquetas_xml_no_sobreviven_a_la_extraccion(
    repo: Path, tmp_path: Path
) -> None:
    """Sin esto el escaner leeria markup en vez de prosa, y el ruido tapa la senal."""
    documento_ooxml(
        repo / "documento.docx",
        {"word/document.xml": parrafos("clave y valor")},
    )
    versionar(repo)
    destino = tmp_path / "salida"

    correr(repo, destino)

    extraido = texto_extraido(destino)
    assert "clave y valor" in extraido
    assert "<w:t>" not in extraido
    assert "w:document" not in extraido


def test_un_secreto_partido_en_dos_runs_queda_en_una_sola_linea(
    repo: Path, tmp_path: Path
) -> None:
    """Word parte una palabra en varios `<w:t>` sin avisar.

    Si la extraccion metiera un salto de linea entre runs, el secreto quedaria
    cortado en dos y ningun escaner de lineas lo reconoceria. El corte va en el
    limite de parrafo, no en el de run.
    """
    mitad, resto = SECRETO[:8], SECRETO[8:]
    documento_ooxml(
        repo / "partido.docx",
        {
            "word/document.xml": (
                '<?xml version="1.0"?><w:document><w:body>'
                f"<w:p><w:r><w:t>{mitad}</w:t></w:r><w:r><w:t>{resto}</w:t></w:r></w:p>"
                "</w:body></w:document>"
            )
        },
    )
    versionar(repo)
    destino = tmp_path / "salida"

    correr(repo, destino)

    lineas = texto_extraido(destino).splitlines()
    assert any(SECRETO in linea for linea in lineas)


def test_los_parrafos_distintos_no_se_pegan_en_una_sola_linea(
    repo: Path, tmp_path: Path
) -> None:
    """El reverso del test anterior: el limite de parrafo si corta."""
    documento_ooxml(
        repo / "parrafos.docx",
        {"word/document.xml": parrafos("primero", "segundo")},
    )
    versionar(repo)
    destino = tmp_path / "salida"

    correr(repo, destino)

    lineas = [linea.strip() for linea in texto_extraido(destino).splitlines()]
    assert "primero" in lineas
    assert "segundo" in lineas


def test_el_destino_de_un_hipervinculo_tambien_se_extrae(
    repo: Path, tmp_path: Path
) -> None:
    """Word no guarda las URLs en el texto: las guarda en atributos de un `.rels`.

    Un token pegado en la query de un enlace no aparece entre etiquetas, asi que
    quedaria afuera si la extraccion solo mirara el texto de los elementos.
    """
    documento_ooxml(
        repo / "con-enlace.docx",
        {
            "word/document.xml": parrafos("ver el panel"),
            "word/_rels/document.xml.rels": (
                '<?xml version="1.0"?><Relationships>'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org'
                '/officeDocument/2006/relationships/hyperlink"'
                f' Target="https://panel.example.com/?token={SECRETO}"'
                ' TargetMode="External"/>'
                "</Relationships>"
            ),
        },
    )
    versionar(repo)
    destino = tmp_path / "salida"

    resultado = correr(repo, destino)

    assert resultado.returncode == 0, resultado.stderr
    assert SECRETO in texto_extraido(destino)


# ── Lo que el gate NO tiene que tocar ─────────────────────────────────────────


def test_ignora_los_archivos_que_el_escaner_ya_lee(repo: Path, tmp_path: Path) -> None:
    """Un `.md` o un `.png` no necesitan extraccion: uno ya es texto, el otro no lo tiene."""
    (repo / "README.md").write_text(f"esto no es un secreto: {SECRETO}", encoding="utf-8")
    (repo / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    versionar(repo)
    destino = tmp_path / "salida"

    resultado = correr(repo, destino)

    assert resultado.returncode == 0, resultado.stderr
    assert list(destino.rglob("*.txt")) == []


def test_ignora_los_documentos_sin_versionar(repo: Path, tmp_path: Path) -> None:
    """Lo que no esta en git no esta en el repositorio, y el gate cubre el repositorio."""
    documento_ooxml(
        repo / "borrador.docx",
        {"word/document.xml": parrafos(SECRETO)},
    )
    # A proposito no se llama a `versionar`.
    destino = tmp_path / "salida"

    resultado = correr(repo, destino)

    assert resultado.returncode == 0, resultado.stderr
    assert texto_extraido(destino) == ""


def test_un_repositorio_sin_documentos_sale_limpio(repo: Path, tmp_path: Path) -> None:
    """Cero documentos es cero riesgo: no hay nada sin escanear."""
    (repo / "codigo.py").write_text("print('hola')\n", encoding="utf-8")
    versionar(repo)
    destino = tmp_path / "salida"

    resultado = correr(repo, destino)

    assert resultado.returncode == 0, resultado.stderr


# ── Lo que tiene que romper ───────────────────────────────────────────────────


def test_un_documento_ilegible_rompe_el_gate(repo: Path, tmp_path: Path) -> None:
    """Un documento que no se puede abrir es un documento que no se escaneo.

    Salir con 0 aca seria exactamente el agujero que este script viene a tapar,
    pero disfrazado de verde. Se distingue del 1 igual que en check-coverage.py:
    esto no es "hay un secreto", es "el gate no pudo mirar".
    """
    (repo / "roto.docx").write_bytes(b"esto no es un zip")
    versionar(repo)
    destino = tmp_path / "salida"

    resultado = correr(repo, destino)

    assert resultado.returncode == 2
    assert "roto.docx" in resultado.stdout + resultado.stderr


def test_un_documento_ilegible_entre_otros_sanos_igual_rompe(
    repo: Path, tmp_path: Path
) -> None:
    """Triangulacion: que la mayoria se haya leido no salva a la que no."""
    documento_ooxml(repo / "sano.docx", {"word/document.xml": parrafos("hola")})
    (repo / "roto.docx").write_bytes(b"tampoco es un zip")
    versionar(repo)
    destino = tmp_path / "salida"

    resultado = correr(repo, destino)

    salida = resultado.stdout + resultado.stderr
    assert resultado.returncode == 2
    assert "roto.docx" in salida
    # El sano se extrajo igual: el 2 es "no pude mirar todo", no "no mire nada".
    assert "hola" in texto_extraido(destino)


# ── Lo que tiene que quedar en el log ─────────────────────────────────────────


def test_informa_cuantos_documentos_y_cuanto_texto_extrajo(
    repo: Path, tmp_path: Path
) -> None:
    """Un gate que no dice cuanto miro es indistinguible de uno que no miro nada.

    Este es el sintoma original: el job daba verde sin leer 1,5 MB. El resumen
    en el log es lo que hace auditable la corrida.
    """
    documento_ooxml(repo / "uno.docx", {"word/document.xml": parrafos("texto uno")})
    documento_ooxml(repo / "dos.docx", {"word/document.xml": parrafos("texto dos")})
    versionar(repo)
    destino = tmp_path / "salida"

    resultado = correr(repo, destino)

    assert "2" in resultado.stdout
    assert "uno.docx" in resultado.stdout
    assert "dos.docx" in resultado.stdout
