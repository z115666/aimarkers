# aimarkers: ignore-file
"""
aimarkers - Documentos de Office y PDF / Office documents and PDF.

Extrae el texto, los metadatos y las imágenes incrustadas de:
- Word, PowerPoint y Excel (.docx, .docm, .pptx, .pptm, .xlsx, .xlsm) y LibreOffice (.odt, .odp, .ods),
  que son ficheros ZIP con XML dentro.
- PDF: diccionario /Info, metadatos XMP, texto de los flujos de contenido e imágenes JPEG.
  Si está instalado pypdf, se usa para extraer el texto, que con fuentes incrustadas es más fiable.

Todo con la biblioteca estándar, leyendo el XML con expresiones regulares (nunca con un analizador
que expanda entidades) y con límites frente a bombas de descompresión.

Autor: Alberto
"""

from __future__ import annotations

import html
import io
import re
import zipfile
import zlib

EXT_OFFICE = {".docx", ".docm", ".pptx", ".pptm", ".xlsx", ".xlsm", ".odt", ".odp", ".ods"}
EXT_PDF = {".pdf"}
EXT_DOCUMENTO = EXT_OFFICE | EXT_PDF

MAX_FICHERO = 60_000_000         # bytes del documento
MAX_ENTRADAS_ZIP = 5000
MAX_DESCOMPRIMIDO = 120_000_000  # bytes descomprimidos en total
MAX_PARTE = 30_000_000           # bytes por parte XML o imagen
MAX_RATIO = 200                  # descomprimido / comprimido por entrada
MAX_IMAGENES = 30
MAX_TEXTO = 3_000_000            # caracteres de texto extraído
MAX_FLUJOS_PDF = 400

EXT_IMAGEN_INCRUSTADA = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff", ".heic", ".avif")


class DocumentoInvalido(Exception):
    pass


# ---------------------------------------------------------------------------
# Office Open XML y OpenDocument
# ---------------------------------------------------------------------------

def _leer_zip(datos: bytes) -> tuple[zipfile.ZipFile, dict[str, zipfile.ZipInfo]]:
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
    except (zipfile.BadZipFile, ValueError) as e:
        raise DocumentoInvalido(str(e)) from e
    entradas = z.infolist()
    if len(entradas) > MAX_ENTRADAS_ZIP:
        raise DocumentoInvalido("demasiadas entradas")
    total = 0
    validas = {}
    for e in entradas:
        if e.flag_bits & 0x1:  # cifrado
            continue
        if e.file_size > MAX_PARTE or e.compress_size and e.file_size / max(e.compress_size, 1) > MAX_RATIO:
            continue  # posible bomba: se ignora esa parte
        total += e.file_size
        if total > MAX_DESCOMPRIMIDO:
            break
        validas[e.filename] = e
    return z, validas


def _parte(z: zipfile.ZipFile, validas: dict, nombre: str) -> str:
    info = validas.get(nombre)
    if info is None:
        return ""
    try:
        with z.open(info) as f:
            crudo = f.read(MAX_PARTE + 1)
    except (zipfile.BadZipFile, OSError, RuntimeError, zlib.error, EOFError):
        return ""
    if len(crudo) > MAX_PARTE:
        return ""
    return crudo.decode("utf-8", "replace")


def _texto_xml(xml: str, parrafo: str, texto: str) -> list[str]:
    """Párrafos de un XML: une el contenido de las etiquetas de texto de cada párrafo."""
    salida = []
    for bloque in re.split(rf"</{parrafo}>", xml):
        trozos = re.findall(rf"<{texto}(?:\s[^>]*)?>([^<]*)</{texto}>", bloque)
        linea = html.unescape("".join(trozos)).strip()
        if linea:
            salida.append(linea)
    return salida


def _numero(nombre: str) -> int:
    m = re.search(r"(\d+)\.xml$", nombre)
    return int(m.group(1)) if m else 0


def _meta_xml(xml: str, etiquetas: dict[str, str]) -> dict[str, str]:
    salida = {}
    for clave, etiqueta in etiquetas.items():
        m = re.search(rf"<{etiqueta}(?:\s[^>]*)?>([^<]{{1,300}})</{etiqueta}>", xml)
        if m and m.group(1).strip():
            salida[clave] = html.unescape(m.group(1).strip())
    return salida


def leer_office(datos: bytes) -> dict:
    z, validas = _leer_zip(datos)
    nombres = list(validas)
    doc = {"formato": "", "meta": {}, "partes": [], "imagenes": [], "autores_revision": []}
    if "word/document.xml" in validas:
        doc["formato"] = "docx"
        orden = ["word/document.xml"] + sorted(n for n in nombres if re.match(r"word/(header|footer)\d*\.xml$", n)) + \
            [n for n in ("word/footnotes.xml", "word/endnotes.xml", "word/comments.xml") if n in validas]
        for n in orden:
            xml = _parte(z, validas, n)
            doc["partes"].append((n, _texto_xml(xml, "w:p", "w:t")))
            doc["autores_revision"] += re.findall(r'<w:(?:ins|del|comment)\b[^>]*\bw:author="([^"]{1,80})"', xml)
        prefijo_media = "word/media/"
    elif any(n.startswith("ppt/slides/slide") for n in nombres):
        doc["formato"] = "pptx"
        diapositivas = sorted((n for n in nombres if re.match(r"ppt/slides/slide\d+\.xml$", n)), key=_numero)
        notas = sorted((n for n in nombres if re.match(r"ppt/notesSlides/notesSlide\d+\.xml$", n)), key=_numero)
        for n in diapositivas + notas:
            doc["partes"].append((n, _texto_xml(_parte(z, validas, n), "a:p", "a:t")))
        prefijo_media = "ppt/media/"
    elif "xl/workbook.xml" in validas:
        doc["formato"] = "xlsx"
        if "xl/sharedStrings.xml" in validas:
            doc["partes"].append(("xl/sharedStrings.xml", _texto_xml(_parte(z, validas, "xl/sharedStrings.xml"), "si", "t")))
        for n in sorted((n for n in nombres if re.match(r"xl/worksheets/sheet\d+\.xml$", n)), key=_numero):
            doc["partes"].append((n, _texto_xml(_parte(z, validas, n), "is", "t")))
        prefijo_media = "xl/media/"
    elif "content.xml" in validas:
        doc["formato"] = "odf"
        xml = _parte(z, validas, "content.xml")
        parrafos = [html.unescape(re.sub(r"<[^>]{0,2000}>", "", p)).strip()
                    for p in re.split(r"</text:(?:p|h)>", xml)]
        doc["partes"].append(("content.xml", [p for p in parrafos if p]))
        meta = _parte(z, validas, "meta.xml")
        doc["meta"].update(_meta_xml(meta, {"aplicacion": "meta:generator", "autor": "meta:initial-creator",
                                            "modificado_por": "dc:creator", "titulo": "dc:title", "descripcion": "dc:description"}))
        prefijo_media = "Pictures/"
    else:
        raise DocumentoInvalido("formato no reconocido")
    if doc["formato"] != "odf":
        doc["meta"].update(_meta_xml(_parte(z, validas, "docProps/core.xml"), {
            "autor": "dc:creator", "modificado_por": "cp:lastModifiedBy", "titulo": "dc:title", "asunto": "dc:subject",
            "descripcion": "dc:description", "palabras_clave": "cp:keywords", "categoria": "cp:category", "revision": "cp:revision"}))
        doc["meta"].update(_meta_xml(_parte(z, validas, "docProps/app.xml"), {
            "aplicacion": "Application", "version_aplicacion": "AppVersion", "empresa": "Company", "plantilla": "Template"}))
        personalizadas = _parte(z, validas, "docProps/custom.xml")
        doc["meta"]["personalizadas"] = " | ".join(
            f"{html.unescape(k)}={html.unescape(v)}" for k, v in
            re.findall(r'<property[^>]*\bname="([^"]{1,80})"[^>]*>\s*<vt:\w+>([^<]{0,120})</vt:\w+>', personalizadas))[:1000]
    for n in nombres:
        if n.startswith(prefijo_media) and n.lower().endswith(EXT_IMAGEN_INCRUSTADA) and len(doc["imagenes"]) < MAX_IMAGENES:
            info = validas[n]
            try:
                with z.open(info) as f:
                    contenido = f.read(MAX_PARTE + 1)
            except (zipfile.BadZipFile, OSError, RuntimeError, zlib.error, EOFError):
                continue
            if len(contenido) <= MAX_PARTE:
                doc["imagenes"].append((n, contenido))
    return doc


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _cadena_pdf(d: bytes, i: int) -> tuple[bytes, int]:
    """Cadena literal PDF que empieza en d[i] == '(' -> (bytes, posición tras el cierre)."""
    salida = bytearray()
    nivel, i = 1, i + 1
    escapes = {ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord("b"): b"\b", ord("f"): b"\f",
               ord("("): b"(", ord(")"): b")", ord("\\"): b"\\"}
    while i < len(d) and len(salida) < 100_000:
        c = d[i]
        if c == 0x5C and i + 1 < len(d):  # barra invertida
            s = d[i + 1]
            if s in escapes:
                salida += escapes[s]
                i += 2
            elif 0x30 <= s <= 0x37:
                m = re.match(rb"[0-7]{1,3}", d[i + 1:i + 4])
                salida.append(int(m.group(0), 8) & 0xFF)
                i += 1 + len(m.group(0))
            elif s in (0x0A, 0x0D):
                i += 2
            else:
                i += 1
            continue
        if c == 0x28:
            nivel += 1
        elif c == 0x29:
            nivel -= 1
            if nivel == 0:
                return bytes(salida), i + 1
        salida.append(c)
        i += 1
    return bytes(salida), i


def _decodificar_texto_pdf(b: bytes) -> str:
    if b.startswith(b"\xfe\xff"):
        return b[2:].decode("utf-16-be", "replace")
    if b.startswith(b"\xef\xbb\xbf"):
        return b[3:].decode("utf-8", "replace")
    return b.decode("cp1252", "replace")


def _valor_pdf(d: bytes, clave: bytes) -> str | None:
    m = re.search(rb"/" + clave + rb"\s*(\(|<(?!<))", d)
    if not m:
        return None
    if m.group(1) == b"(":
        crudo, _ = _cadena_pdf(d, m.start(1))
    else:
        fin = d.find(b">", m.end(1))
        try:
            crudo = bytes.fromhex(re.sub(rb"\s", b"", d[m.end(1):fin]).decode("ascii"))
        except ValueError:
            return None
    texto = _decodificar_texto_pdf(crudo).strip()
    return texto[:300] or None


def _flujos(d: bytes):
    """(diccionario, contenido descomprimido) de cada flujo, con límites."""
    total = 0
    for n, m in enumerate(re.finditer(rb"<<((?:[^<>]|<<[^<>]*>>|<[^<>]*>){0,4000}?)>>\s*stream\r?\n", d)):
        if n >= MAX_FLUJOS_PDF or total > MAX_DESCOMPRIMIDO:
            return
        dic = m.group(1)
        inicio = m.end()
        largo = re.search(rb"/Length\s+(\d+)\b(?!\s+\d+\s+R)", dic)
        fin = inicio + int(largo.group(1)) if largo else d.find(b"endstream", inicio)
        if fin < inicio or fin > len(d):
            fin = d.find(b"endstream", inicio)
            if fin < 0:
                return
        crudo = d[inicio:fin]
        if b"/DCTDecode" in dic:
            yield dic, crudo
            continue
        if b"/FlateDecode" in dic and not re.search(rb"/Filter\s*\[[^\]]*/\w+[^\]]*/\w+", dic):
            try:
                o = zlib.decompressobj()
                contenido = o.decompress(crudo, MAX_PARTE)
            except zlib.error:
                continue
            total += len(contenido)
            yield dic, contenido
        elif b"/Filter" not in dic:
            total += len(crudo)
            yield dic, crudo


def _texto_contenido(c: bytes) -> list[str]:
    """Texto de un flujo de contenido (operadores Tj, TJ, ' y \")."""
    if b"BT" not in c:
        return []
    lineas, actual = [], []
    i = 0
    for m in re.finditer(rb"\((?:\\.|[^\\)])*\)|\[[^\]]{0,20000}\]\s*TJ|T\*|\bTd\b|\bTD\b|\bET\b|'|\"", c):
        token = m.group(0)
        if m.start() < i:
            continue
        if token.startswith(b"("):
            crudo, i = _cadena_pdf(c, m.start())
            actual.append(crudo.decode("cp1252", "replace"))
        elif token.startswith(b"["):
            partes = []
            j = m.start() + 1
            while j < m.end():
                if c[j] == 0x28:
                    crudo, j = _cadena_pdf(c, j)
                    partes.append(crudo.decode("cp1252", "replace"))
                    continue
                n = re.match(rb"-?\d+(?:\.\d+)?", c[j:j + 12])
                if n:
                    if float(n.group(0)) < -200:  # separación grande entre palabras
                        partes.append(" ")
                    j += len(n.group(0))
                    continue
                j += 1
            actual.append("".join(partes))
            i = m.end()
        else:
            if actual:
                lineas.append("".join(actual).strip())
                actual = []
    if actual:
        lineas.append("".join(actual).strip())
    return [x for x in lineas if x]


def _legible(texto: str) -> bool:
    if len(texto) < 40:
        return False
    letras = sum(ch.isalpha() for ch in texto)
    espacios = texto.count(" ")
    raros = sum(1 for ch in texto if ord(ch) < 32 and ch not in "\n\t" or 0x80 <= ord(ch) < 0xA0 or ch == "�")
    return letras / len(texto) > 0.55 and espacios / len(texto) > 0.08 and raros / len(texto) < 0.02


def _texto_pypdf(datos: bytes) -> list[str] | None:
    try:
        import logging

        from pypdf import PdfReader
        logging.getLogger("pypdf").setLevel(logging.CRITICAL)  # los PDF malformados no deben llenar la consola
    except ImportError:
        return None
    try:
        lector = PdfReader(io.BytesIO(datos))
        if lector.is_encrypted:
            return None
        lineas: list[str] = []
        for pagina in lector.pages[:300]:
            lineas += [x.strip() for x in (pagina.extract_text() or "").splitlines() if x.strip()]
            if sum(map(len, lineas)) > MAX_TEXTO:
                break
        return lineas
    except Exception:  # noqa: BLE001 - pypdf puede fallar de muchas formas con PDF malformados
        return None


def leer_pdf(datos: bytes) -> dict:
    if not datos.lstrip()[:5].startswith(b"%PDF"):
        raise DocumentoInvalido("no es un PDF")
    doc = {"formato": "pdf", "meta": {}, "partes": [], "imagenes": [], "autores_revision": [], "texto_legible": True,
           "cifrado": b"/Encrypt" in datos[-4096:] or b"/Encrypt" in datos[:4096]}
    fuentes = [datos]
    lineas: list[str] = []
    for dic, contenido in _flujos(datos):
        if b"/DCTDecode" in dic:
            if len(doc["imagenes"]) < MAX_IMAGENES and contenido[:3] == b"\xff\xd8\xff":
                doc["imagenes"].append((f"imagen-{len(doc['imagenes']) + 1}.jpg", contenido))
            continue
        if b"/ObjStm" in dic or b"/Metadata" in dic or b"x:xmpmeta" in contenido[:4000]:
            fuentes.append(contenido)
        elif not re.search(rb"/Subtype\s*/(?:Image|Type1C|CIDFontType0C|OpenType|Form)|/Length1", dic):
            lineas += _texto_contenido(contenido)
    for fuente in fuentes:
        for clave, pdf in (("aplicacion", b"Creator"), ("productor", b"Producer"), ("autor", b"Author"),
                           ("titulo", b"Title"), ("asunto", b"Subject"), ("palabras_clave", b"Keywords")):
            if clave not in doc["meta"]:
                valor = _valor_pdf(fuente, pdf)
                if valor:
                    doc["meta"][clave] = valor
        xmp = re.search(rb"<x:xmpmeta.{0,200000}?</x:xmpmeta>", fuente, re.S)
        if xmp:
            texto = xmp.group(0).decode("utf-8", "replace")
            for clave, etiqueta in (("aplicacion", "xmp:CreatorTool"), ("productor", "pdf:Producer")):
                m = re.search(rf"<{etiqueta}>([^<]{{1,300}})</{etiqueta}>|{etiqueta}=\"([^\"]{{1,300}})\"", texto)
                if m and clave not in doc["meta"]:
                    doc["meta"][clave] = html.unescape((m.group(1) or m.group(2)).strip())
            doc["meta"]["xmp"] = texto[:20000]
    alternativo = _texto_pypdf(datos)
    if alternativo:
        lineas = alternativo
    texto = "\n".join(lineas)
    doc["texto_legible"] = _legible(texto)
    if doc["texto_legible"]:
        doc["partes"].append(("texto", lineas))
    return doc


def leer(nombre: str, datos: bytes) -> dict:
    if len(datos) > MAX_FICHERO:
        raise DocumentoInvalido("documento demasiado grande")
    if nombre.lower().endswith(".pdf") or datos[:5] == b"%PDF-":
        return leer_pdf(datos)
    return leer_office(datos)


# ---------------------------------------------------------------------------
# Huellas en los metadatos
# ---------------------------------------------------------------------------

# Herramientas de IA que pueden figurar como aplicación, productor o autor
RE_HERRAMIENTA_IA = re.compile(
    r"chatgpt|openai|\bclaude\b|anthropic|copilot|gemini|\bgamma(?:\.app)?\b|beautiful\.ai|\btome\b|decktopus|"
    r"plus ai|presentations\.ai|slidesai|magicslides|\bjasper\b|notebooklm|perplexity|mistral|le chat|deepseek|\bgrok\b",
    re.I)

# Librerías con las que los asistentes crean ficheros desde código (también las usa cualquier automatización)
LIBRERIAS = [
    ("python-docx", re.compile(r"python-docx", re.I)),
    ("python-pptx", re.compile(r"python-pptx", re.I)),
    ("openpyxl", re.compile(r"\bopenpyxl\b", re.I)),
    ("XlsxWriter", re.compile(r"xlsxwriter", re.I)),
    ("PptxGenJS", re.compile(r"pptxgenjs", re.I)),
    ("docx (npm)", re.compile(r"^un-named$", re.I)),
    ("ReportLab", re.compile(r"reportlab", re.I)),
    ("FPDF", re.compile(r"\b(?:py)?fpdf2?\b", re.I)),
    ("pdf-lib", re.compile(r"\bpdf-lib\b", re.I)),
    ("jsPDF", re.compile(r"\bjspdf\b", re.I)),
    ("PDFKit", re.compile(r"^pdfkit\b", re.I)),
    ("WeasyPrint", re.compile(r"weasyprint", re.I)),
    ("wkhtmltopdf", re.compile(r"wkhtmltopdf", re.I)),
    ("xhtml2pdf", re.compile(r"xhtml2pdf|pisa", re.I)),
    ("Chrome sin interfaz", re.compile(r"headlesschrome|puppeteer|playwright", re.I)),
    ("Typst", re.compile(r"^typst\b", re.I)),
]

CAMPOS_HERRAMIENTA = ("aplicacion", "productor", "autor", "modificado_por", "descripcion", "palabras_clave", "plantilla",
                      "empresa", "personalizadas")


def huellas(meta: dict, autores_revision: list[str]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(herramientas de IA [(campo, valor)], librerías [(nombre, campo=valor)])."""
    ia, libs = [], []
    for campo in CAMPOS_HERRAMIENTA:
        valor = meta.get(campo, "")
        if not valor:
            continue
        if RE_HERRAMIENTA_IA.search(valor):
            ia.append((campo, valor))
        for nombre, patron in LIBRERIAS:
            if patron.search(valor) and nombre not in [n for n, _ in libs]:
                libs.append((nombre, f"{campo}: {valor}"))
    for autor in dict.fromkeys(autores_revision):
        if RE_HERRAMIENTA_IA.search(autor):
            ia.append(("revision", autor))
    # python-pptx y python-docx dejan títulos por defecto aunque se borre el autor
    if meta.get("titulo") in ("PowerPoint Presentation", "Word Document") and meta.get("revision") == "1" \
            and not any(n.startswith("python-") for n, _ in libs):
        libs.append(("python-pptx" if meta["titulo"].startswith("Power") else "python-docx", f"titulo: {meta['titulo']}"))
    return ia, libs


RE_MARKDOWN = re.compile(r"^\s{0,3}#{1,4} \S|\*\*[^*\n]{2,80}\*\*|^\s{0,3}(?:[-*] ){1}\*\*|^\|.+\|\s*$|^```", re.M)


def restos_markdown(lineas: list[str]) -> list[tuple[int, str]]:
    """Líneas con Markdown literal: en un documento de Office o PDF suele venir de pegar la respuesta de un chat."""
    return [(n, l) for n, l in enumerate(lineas, 1) if RE_MARKDOWN.search(l)]
