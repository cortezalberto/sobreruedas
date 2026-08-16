#!/usr/bin/env python3
"""Extractor de texto de documentos OOXML — tapa el punto ciego de gitleaks.

EL AGUJERO QUE ESTE SCRIPT CIERRA
─────────────────────────────────
El job `security` corre `gitleaks detect` sobre el repositorio, y gitleaks lee
los cambios con `git log -p`. Un `.docx` es un zip, o sea un binario: git lo
emite como "Binary files a/... and b/... differ" y el escaner lo declara limpio
**sin leer un byte**. En este repositorio son 13 documentos, unos 1,5 MB de
texto, entre ellos la constitucion y los planes de seguridad y de SRE.

Un gate que da verde sin mirar es peor que no tener gate: da confianza falsa.

Este script no busca secretos. Convierte cada documento en texto plano para que
el escaner de siempre —con su version fijada— pueda hacer su trabajo:

    python tools/extract-docx-text.py --destino /tmp/ooxml
    gitleaks detect --no-git --source /tmp/ooxml --redact

ALCANCE — LEER ESTO ANTES DE CONFIAR EN EL GATE
───────────────────────────────────────────────
Se extrae **el arbol de trabajo**, no la historia: los documentos versionados
tal como estan hoy. Un secreto que se haya commiteado adentro de un `.docx` y
borrado despues NO se detecta por esta via. Fue una decision explicita de
alcance; ampliarlo es recorrer los blobs de `git rev-list --objects --all`.

Tampoco se leen los objetos incrustados (un `.xlsx` pegado adentro de un
`.docx`) ni el texto dentro de imagenes.

DECISIONES DE FORMATO
─────────────────────
El corte de linea va en el limite de PARRAFO, no en el de run. Word parte una
palabra en varios `<w:t>` sin avisar; si cada run terminara en salto de linea,
un secreto quedaria cortado en dos y ningun escaner de lineas lo reconoceria.

De las partes `.rels` se extraen ademas los valores de atributo: ahi es donde
Word guarda los hipervinculos, y un token en la query de una URL no aparece en
ningun lado del texto.

CODIGOS DE SALIDA
─────────────────
    0  se extrajo todo lo que habia (aunque no hubiera nada: cero documentos
       es cero riesgo, no hay nada sin escanear)
    2  algun documento versionado no se pudo abrir -> el gate no pudo mirar

No hay codigo 1: este script no juzga contenido. Quien bloquea es gitleaks.
El 2 se distingue a proposito, igual que en `check-coverage.py`: manda a
arreglar el pipeline, no a buscar un secreto que nadie reporto.
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import NamedTuple

# Los formatos de Office que son zip con XML adentro. Los `.doc` viejos y los
# `.pdf` no entran: no son OOXML y necesitarian otro extractor.
EXTENSIONES_OOXML = frozenset(
    {".docx", ".docm", ".xlsx", ".xlsm", ".pptx", ".pptm"}
)

# Partes que vale la pena leer. El resto de un OOXML son imagenes, fuentes y
# temas: binarios sin texto que aportar.
SUFIJOS_DE_TEXTO = (".xml", ".rels")

# Limites que SI cortan linea: parrafo de Word, fila de tabla, cadena compartida
# de Excel, fila de hoja y salto explicito. Todo lo demas se descarta sin dejar
# separador, para que los runs partidos vuelvan a pegarse.
CORTES = re.compile(
    r"</(?:[^\s:>]+:)?(?:p|tr|si|row|br)\s*>|<(?:[^\s:>]+:)?br\s*/?>",
    re.IGNORECASE,
)
ETIQUETAS = re.compile(r"<[^>]*>", re.DOTALL)
VALORES_DE_ATRIBUTO = re.compile(r'="([^"]*)"')

# Los `.rels` estan tapizados de URLs de esquema de Microsoft: son la definicion
# del formato, no contenido del documento. Sin este filtro cada documento sumaria
# decenas de lineas de ruido identico.
NAMESPACES_CONOCIDOS = (
    "http://schemas.openxmlformats.org",
    "http://schemas.microsoft.com",
    "http://purl.oclc.org",
    "http://www.w3.org",
)


class Documento(NamedTuple):
    """Un documento versionado y lo que se pudo sacar de el."""

    ruta: str
    caracteres: int


def documentos_versionados(repo: Path) -> list[str]:
    """Las rutas OOXML que git tiene versionadas, en orden estable.

    Se pregunta a git y no al sistema de archivos a proposito: lo que no esta
    versionado no esta en el repositorio, y el gate cubre el repositorio. Un
    borrador suelto en el directorio de trabajo no viaja a ningun lado.
    """
    salida = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    rutas = [ruta for ruta in salida.split("\0") if ruta]
    return sorted(
        ruta for ruta in rutas if Path(ruta).suffix.lower() in EXTENSIONES_OOXML
    )


def texto_de_parte(xml: str, *, con_atributos: bool) -> str:
    """Convierte una parte XML de OOXML en lineas de texto plano."""
    lineas: list[str] = []

    if con_atributos:
        lineas.extend(
            valor
            for valor in VALORES_DE_ATRIBUTO.findall(xml)
            if valor and not valor.startswith(NAMESPACES_CONOCIDOS)
        )

    cortado = CORTES.sub("\n", xml)
    lineas.extend(html.unescape(ETIQUETAS.sub("", cortado)).splitlines())

    return "\n".join(linea.strip() for linea in lineas if linea.strip())


def texto_de_documento(ruta: Path) -> str:
    """Todo el texto legible de un documento OOXML, parte por parte.

    Propaga `zipfile.BadZipFile` si el archivo no es un zip: quien llama decide
    que hacer, y lo que hace es romper el gate.
    """
    fragmentos: list[str] = []
    with zipfile.ZipFile(ruta) as documento:
        for parte in sorted(documento.namelist()):
            if not parte.lower().endswith(SUFIJOS_DE_TEXTO):
                continue
            crudo = documento.read(parte).decode("utf-8", errors="replace")
            texto = texto_de_parte(crudo, con_atributos=parte.lower().endswith(".rels"))
            if texto:
                fragmentos.append(texto)
    return "\n".join(fragmentos)


def nombre_de_salida(ruta: str) -> str:
    """`autos/plan.docx` -> `autos__plan.docx.txt`.

    La ruta original queda entera en el nombre: un hallazgo del escaner apunta
    al archivo extraido, y desde ahi tiene que poder rastrearse hasta el
    documento de verdad sin adivinar.
    """
    return ruta.replace("/", "__").replace("\\", "__") + ".txt"


def extraer(repo: Path, destino: Path) -> tuple[list[Documento], list[str]]:
    """Extrae todos los documentos versionados. Devuelve (extraidos, ilegibles)."""
    destino.mkdir(parents=True, exist_ok=True)
    extraidos: list[Documento] = []
    ilegibles: list[str] = []

    for ruta in documentos_versionados(repo):
        origen = repo / ruta
        if not origen.is_file():
            # Versionado pero ausente del arbol de trabajo (un rebase a medias,
            # un checkout parcial). No hay contenido que mirar, no hay riesgo.
            print(f"[aviso] {ruta}: versionado pero ausente del arbol de trabajo")
            continue
        try:
            texto = texto_de_documento(origen)
        except (zipfile.BadZipFile, OSError) as error:
            print(f"[ERROR] {ruta}: no se pudo leer como documento OOXML ({error})")
            ilegibles.append(ruta)
            continue
        (destino / nombre_de_salida(ruta)).write_text(texto, encoding="utf-8")
        extraidos.append(Documento(ruta, len(texto)))

    return extraidos, ilegibles


def informar(extraidos: list[Documento], ilegibles: list[str], destino: Path) -> None:
    """Deja en el log cuanto texto se miro.

    Es la parte que no se puede omitir: un gate que no dice cuanto leyo es
    indistinguible de uno que no leyo nada, que es exactamente como este job
    daba verde sobre 1,5 MB sin abrirlos.
    """
    for documento in extraidos:
        print(f"  {documento.ruta}: {documento.caracteres} caracteres")
    total = sum(documento.caracteres for documento in extraidos)
    print(
        f"[ok] {len(extraidos)} documentos OOXML extraidos "
        f"({total} caracteres) a {destino}"
    )
    if ilegibles:
        print(f"[ERROR] {len(ilegibles)} documentos ilegibles: {', '.join(ilegibles)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extrae a texto plano los documentos OOXML versionados, para que un "
            "escaner de secretos pueda leerlos."
        )
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="raiz del repositorio a inspeccionar (por defecto, el directorio actual)",
    )
    parser.add_argument(
        "--destino",
        type=Path,
        required=True,
        help="directorio donde dejar el texto extraido",
    )
    argumentos = parser.parse_args()

    extraidos, ilegibles = extraer(argumentos.repo, argumentos.destino)
    informar(extraidos, ilegibles, argumentos.destino)

    return 2 if ilegibles else 0


if __name__ == "__main__":
    sys.exit(main())
