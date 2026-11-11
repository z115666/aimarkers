#!/usr/bin/env python3
# aimarkers: ignore-file
"""
aimarkers - AI markers analysis for code, documentation, websites, images and Git repositories.
aimarkers - Análisis de marcadores de IA en código, documentación, webs, imágenes y repositorios Git.

Busca indicios de que un contenido se ha generado o asistido con IA y los
puntúa por niveles (explícito, fuerte, medio, débil). No es un detector
infalible: el resultado es una estimación basada en evidencias que hay que
revisar a mano.

Uso / Usage:
    python aimarkers.py ./mi_repo
    python aimarkers.py informe.md script.ps1 foto.jpg
    python aimarkers.py https://ejemplo.com --html informe.html
    python aimarkers.py page.html --json result.json --lang en

Solo usa la biblioteca estándar de Python (3.9+). El módulo subprocess se usa
únicamente para invocar git y, si está instalado, c2patool, siempre con
argumentos en lista y sin shell.
Autor: Alberto
"""

from __future__ import annotations

import argparse
import html
import json
import locale
import os
import re
import shutil
import statistics
import struct
import subprocess  # nosec B404
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

VERSION = "1.5.0"

# ---------------------------------------------------------------------------
# Idioma / Language
# ---------------------------------------------------------------------------

IDIOMAS = ("es", "en")
_ESTADO = {"idioma": "es"}


def detectar_idioma() -> str:
    """Idioma por defecto: AIMARKERS_LANG, después las variables de locale del sistema; inglés si no es español."""
    for var in ("AIMARKERS_LANG", "LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        valor = os.environ.get(var, "").strip().lower()
        if valor and valor not in ("c", "posix", "c.utf-8"):
            return "es" if valor.startswith("es") else "en"
    try:
        actual = (locale.getlocale()[0] or "").lower()
    except ValueError:
        actual = ""
    return "es" if actual.startswith(("es", "spanish")) else "en"


def fijar_idioma(idioma: str) -> None:
    _ESTADO["idioma"] = idioma if idioma in IDIOMAS else "en"


def idioma() -> str:
    return _ESTADO["idioma"]


TEXTOS: dict[str, tuple[str, str]] = {
    # Niveles y valoraciones
    "nivel.explicito": ("Explícito", "Explicit"),
    "nivel.fuerte": ("Fuerte", "Strong"),
    "nivel.medio": ("Medio", "Medium"),
    "nivel.debil": ("Débil", "Weak"),
    "banda.alta": ("Alta probabilidad de generación o asistencia intensa con IA",
                   "High likelihood of AI generation or heavy AI assistance"),
    "banda.media": ("Probable asistencia de IA en parte del contenido",
                    "Likely AI assistance in part of the content"),
    "banda.baja": ("Indicios débiles: rasgos compatibles, nada concluyente",
                   "Weak signs: compatible traits, nothing conclusive"),
    "banda.nula": ("Sin indicios relevantes", "No relevant signs"),
    "banda.indeterminada": ("No se puede determinar: la imagen no conserva metadatos",
                            "Cannot be determined: the image has no metadata left"),
    # Tipos de objetivo
    "tipo.dir": ("directorio", "directory"),
    "tipo.repo": ("repositorio git", "git repository"),
    "tipo.url": ("web (URL)", "website (URL)"),
    "tipo.html": ("web (HTML)", "web page (HTML)"),
    "tipo.texto": ("texto", "text"),
    "tipo.codigo": ("código", "code"),
    "tipo.imagen": ("imagen", "image"),
    "tipo.fichero": ("fichero", "file"),
    "tipo.desconocido": ("desconocido", "unknown"),
    # Interfaz
    "ui.objetivo": ("Objetivo  ", "Target    "),
    "ui.tipo": ("Tipo      ", "Type      "),
    "ui.puntuacion": ("Puntuación", "Score     "),
    "ui.ficheros_1": ("1 fichero analizado", "1 file analysed"),
    "ui.ficheros_n": ("{n} ficheros analizados", "{n} files analysed"),
    "ui.explicita": ("ATRIBUCIÓN EXPLÍCITA: el propio contenido declara una herramienta de IA.",
                     "EXPLICIT ATTRIBUTION: the content itself declares an AI tool."),
    "ui.ninguno": ("No se han encontrado marcadores.", "No markers found."),
    "ui.notas": ("Notas", "Notes"),
    "ui.mas": ("… {n} más", "… {n} more"),
    "ui.notas_mas": ("… {n} notas más", "… {n} more notes"),
    "ui.prevalencia": ("{p} de los ficheros", "{p} of files"),
    "ui.aviso": ("Los marcadores son indicios, no pruebas. Revisa cada evidencia antes de sacar conclusiones; "
                 "la ausencia de marcadores tampoco demuestra autoría humana.",
                 "Markers are signs, not proof. Review every piece of evidence before drawing conclusions; "
                 "the absence of markers does not prove human authorship either."),
    "ui.titulo": ("Informe de marcadores de IA", "AI markers report"),
    "ui.generado": ("Generado con aimarkers {v} el {fecha}.", "Generated with aimarkers {v} on {fecha}."),
    "ui.si": ("sí", "yes"),
    "ui.no": ("no", "no"),
    "ui.col_nivel": ("Nivel", "Level"),
    "ui.col_marcador": ("Marcador", "Marker"),
    "ui.col_veces": ("Veces", "Count"),
    "ui.col_ubicacion": ("Ubicación", "Location"),
    "ui.col_evidencia": ("Evidencia", "Evidence"),
    "ui.col_evidencias": ("Evidencias", "Evidence"),
    "ui.md_tipo": ("Tipo", "Type"),
    "ui.md_ficheros": ("Ficheros analizados", "Files analysed"),
    "ui.md_puntuacion": ("Puntuación", "Score"),
    "ui.md_explicita": ("Atribución explícita", "Explicit attribution"),
    "ui.formato_fecha": ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"),
    # Ubicaciones
    "ub.datos": ("datos embebidos", "embedded data"),
    "ub.historial": ("historial", "history"),
    "ub.ramas": ("ramas", "branches"),
    "ub.pagina": ("página", "page"),
    "ub.visible": ("{u} (texto visible)", "{u} (visible text)"),
    # Notas
    "nota.muestra": ("{u}: {n} palabras; muestra insuficiente para valorar el estilo.",
                     "{u}: {n} words; sample too small to assess writing style."),
    "nota.ignorado": ("{u}: omitido por la directiva «aimarkers: ignore-file».",
                      "{u}: skipped because of the «aimarkers: ignore-file» directive."),
    "nota.git_vacio": ("Repositorio Git sin commits o git no disponible.", "Git repository without commits, or git not available."),
    "nota.git_commits": ("Git: {n} commits analizados.", "Git: {n} commits analysed."),
    "nota.git_mas": ("Git: {n} commits con marcador «{c}» (se muestran 5).", "Git: {n} commits with marker «{c}» (5 shown)."),
    "nota.generator": ("{u}: meta generator = «{g}»", "{u}: meta generator = «{g}»"),
    "nota.no_descarga": ("No se pudo descargar: {e}", "Could not download: {e}"),
    "nota.no_reconocido": ("Tipo de fichero no reconocido o binario; no se ha analizado.",
                           "Unrecognised or binary file type; not analysed."),
    "nota.no_existe": ("No existe el fichero o directorio.", "File or directory not found."),
    "nota.solo_http": ("solo se admiten URLs http(s)", "only http(s) URLs are allowed"),
    "nota.redireccion": ("redirección rechazada a un esquema no permitido: {u}", "redirect to a disallowed scheme rejected: {u}"),
    "nota.imagenes_web": ("{n} imágenes de la página analizadas.", "{n} images from the page analysed."),
    "nota.imagenes_limite": ("Se analizan como máximo {n} imágenes por página.", "At most {n} images per page are analysed."),
    "nota.c2pa_sin_ia": ("{u}: credenciales C2PA sin declaración de IA ({d}).", "{u}: C2PA credentials without an AI declaration ({d})."),
    "nota.c2patool_no": ("c2patool no está instalado: las firmas C2PA no se han verificado (brew install c2patool).",
                         "c2patool is not installed: C2PA signatures were not verified (brew install c2patool)."),
    "nota.sin_metadatos": ("{u}: la imagen ({f}) no conserva metadatos (ni C2PA, ni XMP, ni EXIF). Pasa con capturas, "
                           "miniaturas de buscadores y redes sociales. Busca el original con una búsqueda inversa de imágenes.",
                           "{u}: the image ({f}) has no metadata left (no C2PA, XMP or EXIF). This happens with screenshots, "
                           "search engine thumbnails and social networks. Look for the original with a reverse image search."),
    "nota.limite_paginas": ("Rastreo detenido al llegar a {n} páginas (usa --max-paginas para cambiar el límite; -1 sin límite).",
                            "Crawl stopped at {n} pages (use --max-pages to change the limit; -1 for no limit)."),
    "nota.paginas_rastreadas": ("{n} páginas descargadas del sitio (borradas al terminar).",
                                "{n} pages downloaded from the site (deleted afterwards)."),
    "nota.estado_http": ("La web respondió con el estado HTTP {n}: el análisis corresponde a esa página de error.",
                         "The website answered with HTTP status {n}: the analysis covers that error page."),
    "nota.robots": ("Se ha respetado robots.txt.", "robots.txt was respected."),
    "fase.subida": ("Preparando ficheros", "Preparing files"),
    "fase.descarga": ("Descargando el sitio", "Downloading the site"),
    "fase.ia": ("Buscando marcadores de IA", "Looking for AI markers"),
    "fase.imagenes": ("Leyendo metadatos de imágenes", "Reading image metadata"),
    "fase.ficheros": ("Analizando ficheros", "Analysing files"),
    "fase.git": ("Revisando el historial de Git", "Reviewing Git history"),
    "fase.scripts": ("Descargando JavaScript del sitio", "Downloading site JavaScript"),
    "fase.seguridad": ("Comprobando la seguridad", "Checking security"),
    "fase.dns": ("Consultando DNS del dominio", "Querying the domain's DNS"),
    "fase.activo": ("Comprobando rutas sensibles", "Checking sensitive paths"),
    "fase.codigo": ("Revisando la seguridad del código", "Reviewing code security"),
    "prog.paginas": ("Rastreando: {n} páginas", "Crawling: {n} pages"),
    "prog.scripts": ("Descargando JavaScript del sitio: {n}", "Downloading site JavaScript: {n}"),
    "prog.imagenes": ("Analizando imágenes: {n} de {t}", "Analysing images: {n} of {t}"),
    "nota.imagen_grande": ("{u}: imagen demasiado grande; no se ha analizado.", "{u}: image too large; not analysed."),
    # Evidencias generadas
    "ev.muletillas": ("{n} apariciones ({d}/1000 palabras): {l}", "{n} occurrences ({d}/1000 words): {l}"),
    "ev.rayas": ("{n} rayas en {p} palabras", "{n} em dashes in {p} words"),
    "ev.vinetas": ("{a} de {b} viñetas", "{a} of {b} bullets"),
    "ev.titulos": ("{n} títulos", "{n} headings"),
    "ev.ritmo": ("{n} frases, media {m} palabras, coef. de variación {cv}",
                 "{n} sentences, mean {m} words, coefficient of variation {cv}"),
    "ev.pasos": ("{n} comentarios de paso; p. ej. {e}", "{n} step comments; e.g. {e}"),
    "ev.lineas_1": ("1 línea; p. ej. {e}", "1 line; e.g. {e}"),
    "ev.lineas_n": ("{n} líneas; p. ej. {e}", "{n} lines; e.g. {e}"),
    "ev.funciones": ("{a} de {b} funciones", "{a} of {b} functions"),
    "ev.bloques": ("{n} bloques", "{n} blocks"),
    "ev.densidad": ("{p} de las líneas son comentarios", "{p} of lines are comments"),
    "ev.rafaga": ("{n} registros entre {a} y {b} (hora local), separación mediana {s} s",
                  "{n} records between {a} and {b} (local time), median gap {s} s"),
    "ev.coordenadas": ("{b} con ≤6 decimales, {a} con ≥7 decimales, {r} casi redondas, de {n}",
                       "{b} with ≤6 decimals, {a} with ≥7 decimals, {r} near-round, out of {n}"),
    "ev.stack": ("{n} de 3 rasgos presentes", "{n} of 3 traits present"),
    "ev.commits_grandes": ("{n} commits; mayor: {h} (+{l} líneas)", "{n} commits; largest: {h} (+{l} lines)"),
    "ev.mensajes": ("{a}/{b} Conventional Commits, {c} con viñetas", "{a}/{b} Conventional Commits, {c} with bullet lists"),
    "ev.c2pa": ("origen: {o}; herramienta: {h}; firmante: {f}; firma: {s}",
                "source: {o}; tool: {h}; signer: {f}; signature: {s}"),
    "ev.desconocido": ("desconocido", "unknown"),
    "firma.no_verificada": ("no verificada (instala c2patool)", "not verified (install c2patool)"),
    "firma.confianza": ("válida, certificado de confianza", "valid, trusted certificate"),
    "firma.valida": ("válida, certificado no reconocido", "valid, unrecognised certificate"),
    "firma.invalida": ("NO VÁLIDA: la imagen o el manifiesto se han modificado", "INVALID: image or manifest was modified"),
    "origen.trainedAlgorithmicMedia": ("generada con IA", "AI-generated"),
    "origen.compositeWithTrainedAlgorithmicMedia": ("composición o edición con IA", "composite or edit with AI"),
    "origen.algorithmicMedia": ("algorítmica, sin IA entrenada", "algorithmic, no trained AI"),
    "origen.compositeSynthetic": ("composición con elementos sintéticos", "composite with synthetic elements"),
    "origen.digitalCapture": ("captura digital (cámara)", "digital capture (camera)"),
    "origen.composite": ("composición", "composite"),
    "origen.screenCapture": ("captura de pantalla", "screen capture"),
    # CLI
    "cli.descripcion": ("Analiza marcadores de IA en código, documentación, webs (fichero o URL), imágenes y repositorios Git.",
                        "Analyse AI markers in code, documentation, websites (file or URL), images and Git repositories."),
    "cli.objetivos": ("Ficheros, directorios, repositorios o URLs a analizar", "Files, directories, repositories or URLs to analyse"),
    "cli.json": ("Guardar el resultado en JSON", "Save the result as JSON"),
    "cli.md": ("Guardar el informe en Markdown", "Save the report as Markdown"),
    "cli.html": ("Guardar el informe en HTML", "Save the report as HTML"),
    "cli.evidencias": ("Evidencias a mostrar por marcador (por defecto 3)", "Evidence items shown per marker (default 3)"),
    "cli.sin_color": ("Desactivar colores en consola", "Disable console colours"),
    "cli.silencioso": ("No imprimir el informe en consola", "Do not print the report to the console"),
    "cli.umbral": ("Salir con código 2 si algún objetivo alcanza esta puntuación (útil en CI)",
                   "Exit with code 2 if any target reaches this score (useful in CI)"),
    "cli.sin_imagenes": ("No descargar ni analizar las imágenes enlazadas en las webs",
                         "Do not download or analyse images linked from web pages"),
    "cli.lang": ("Idioma de la salida: es o en (por defecto, el del sistema)",
                 "Output language: es or en (default: system language)"),
    "cli.fichero": ("FICHERO", "FILE"),
    "cli.rastrear": ("Rastrear todo el sitio (mismo dominio) en lugar de solo la página indicada",
                     "Crawl the whole site (same domain) instead of just the given page"),
    "cli.max_paginas": ("Máximo de páginas al rastrear (por defecto 2000; -1 sin límite)",
                        "Maximum pages when crawling (default 2000; -1 for no limit)"),
    "cli.max_imagenes": ("Máximo de imágenes de webs a analizar (por defecto 15, o todas al rastrear; 0 sin límite)",
                         "Maximum website images to analyse (default 15, or all when crawling; 0 for no limit)"),
    "cli.retardo": ("Pausa en segundos entre peticiones al rastrear (por defecto 0.3)",
                    "Pause in seconds between requests when crawling (default 0.3)"),
    "cli.seguridad": ("Añadir el análisis de seguridad (OWASP Top 10, MITRE ATT&CK, CVSS v4.0, matriz de riesgos CID)",
                      "Add the security analysis (OWASP Top 10, MITRE ATT&CK, CVSS v4.0, CIA risk matrix)"),
    "cli.detenido": ("Análisis detenido. No se ha generado ningún informe y los ficheros temporales se han borrado.",
                     "Analysis stopped. No report was written and temporary files were deleted."),
    "cli.sin_dns": ("No consultar SPF, DMARC, DNSSEC ni CAA (se consultan por DNS sobre HTTPS)",
                    "Do not query SPF, DMARC, DNSSEC or CAA (queried over DNS over HTTPS)"),
    "cli.activo": ("Seguridad en modo activo: comprueba rutas sensibles conocidas (exige --autorizado)",
                   "Active security mode: checks known sensitive paths (requires --authorized)"),
    "cli.autorizado": ("Declaras que tienes autorización para analizar la web en modo activo",
                       "You declare you are authorised to test the website in active mode"),
    "cli.solo_seguridad": ("Solo el análisis de seguridad, sin marcadores de IA", "Security analysis only, without AI markers"),
    "cli.umbral_cvss": ("Salir con código 3 si algún hallazgo de seguridad alcanza este CVSS",
                        "Exit with code 3 if any security finding reaches this CVSS score"),
    "cli.gui": ("Abrir la interfaz gráfica en el navegador (solo en este equipo)",
                "Open the graphical interface in the browser (this computer only)"),
    "cli.port": ("Puerto local de la interfaz gráfica (por defecto, uno libre al azar)",
                 "Local port for the graphical interface (default: a random free one)"),
    "cli.no_browser": ("No abrir el navegador automáticamente con --gui", "Do not open the browser automatically with --gui"),
    "cli.sin_objetivos": ("indica al menos un fichero, carpeta o URL, o usa --gui",
                          "give at least one file, folder or URL, or use --gui"),
}

DESCRIPCIONES: dict[str, tuple[str, str]] = {
    "firma-generador": ("Firma de herramienta de IA en el contenido", "AI tool signature in the content"),
    "firma-robot": ("Pie «🤖 Generated with…» de un agente", "Agent footer «🤖 Generated with…»"),
    "coautor-ia": ("Coautoría declarada a una IA", "Co-authorship declared to an AI"),
    "citas-chatgpt": ("Rastro de citas de ChatGPT copiado del chat", "ChatGPT citation residue pasted from the chat"),
    "utm-chatgpt": ("Enlace copiado desde un asistente de IA (utm_source=chatgpt.com…)",
                    "Link copied from an AI assistant (utm_source=chatgpt.com…)"),
    "autodeclaracion-modelo": ("El texto se declara modelo de lenguaje", "The text declares itself a language model"),
    "resto-chat": ("Frase de chat copiada dentro del fichero", "Chat phrase pasted into the file"),
    "cierre-chat": ("Cierre típico de respuesta de chat", "Typical chat-reply closing line"),
    "hueco-plantilla": ("Hueco de plantilla sin rellenar", "Unfilled template placeholder"),
    "comentario-demo": ("Comentario de código de demostración", "Demo-style code comment"),
    "placeholder": ("Valor de ejemplo sin sustituir", "Example value left unreplaced"),
    "comentarios-paso": ("Comentarios numerados por pasos («# Step 1:»)", "Numbered step comments («# Step 1:»)"),
    "emoji-logs": ("Emojis en mensajes de consola o log", "Emojis in console or log messages"),
    "valla-markdown": ("Fichero envuelto en una valla Markdown (```) copiada del chat",
                       "File wrapped in a Markdown fence (```) pasted from the chat"),
    "docstrings-uniformes": ("Docstrings Args/Returns en casi todas las funciones", "Args/Returns docstrings on almost every function"),
    "errores-genericos": ("Manejo de errores genérico repetido («An error occurred»)", "Repeated generic error handling («An error occurred»)"),
    "tipografia-codigo": ("Caracteres tipográficos en código (raya, comillas curvas, invisibles)",
                          "Typographic characters in code (em dash, curly quotes, invisible characters)"),
    "densidad-comentarios": ("Densidad de comentarios muy alta", "Very high comment density"),
    "muletillas": ("Densidad alta de muletillas típicas de LLM", "High density of typical LLM stock phrases"),
    "rayas": ("Uso intensivo de la raya (—)", "Heavy use of em dashes (—)"),
    "vinetas-negrita": ("Viñetas con «**Término:** explicación» de forma sistemática",
                        "Systematic «**Term:** explanation» bullet points"),
    "emoji-titulos": ("Títulos que empiezan con emoji", "Headings that start with an emoji"),
    "ritmo-uniforme": ("Frases de longitud muy uniforme (baja burstiness)", "Very uniform sentence length (low burstiness)"),
    "gen-lovable": ("Huella de Lovable (data-lov-*, gptengineer, lovable-tagger)", "Lovable fingerprint (data-lov-*, gptengineer, lovable-tagger)"),
    "gen-v0": ("Huella de v0 (Vercel)", "v0 (Vercel) fingerprint"),
    "gen-bolt": ("Huella de Bolt.new", "Bolt.new fingerprint"),
    "gen-otros": ("Huella de otro constructor web con IA", "Fingerprint of another AI website builder"),
    "imagen-ia": ("Imagen con nombre de generador de IA", "Image named after an AI generator"),
    "framework-ia": ("Framework construido con IA (vinext de Cloudflare)", "Framework built with AI (Cloudflare vinext)"),
    "stack-generador": ("Stack por defecto de los generadores (shadcn/ui, lucide, degradados)",
                        "Default stack of AI builders (shadcn/ui, lucide, gradients)"),
    "rafaga-datos": ("Ráfaga de registros creados cada pocos segundos (carga automatizada)",
                     "Burst of records created seconds apart (automated load)"),
    "coordenadas-mixtas": ("Precisión de coordenadas mezclada (dos orígenes de datos)",
                           "Mixed coordinate precision (two data sources)"),
    "llms-txt": ("El dominio publica /llms.txt (preparado para agentes)", "The domain publishes /llms.txt (prepared for agents)"),
    "autor-bot": ("Commit firmado por un agente o bot de IA", "Commit authored by an AI agent or bot"),
    "rama-agente": ("Rama con prefijo de agente de IA", "Branch with an AI agent prefix"),
    "commits-grandes": ("Varios commits con más de 1.000 líneas añadidas", "Several commits adding more than 1,000 lines"),
    "mensajes-uniformes": ("Mensajes de commit perfectamente uniformes con cuerpo en viñetas",
                           "Perfectly uniform commit messages with bulleted bodies"),
    "fichero-agente": ("Fichero de instrucciones para agentes de IA", "Instruction file for AI agents"),
    "carpeta-agente": ("Carpeta de configuración de agentes de IA", "Configuration folder for AI agents"),
    # Imágenes
    "c2pa-ia": ("Credenciales de contenido C2PA declaran generación con IA", "C2PA Content Credentials declare AI generation"),
    "c2pa-edicion-ia": ("Credenciales C2PA declaran edición o composición con IA",
                        "C2PA Content Credentials declare AI editing or compositing"),
    "c2pa-herramienta-ia": ("Credenciales C2PA emitidas por una herramienta de IA", "C2PA Content Credentials issued by an AI tool"),
    "xmp-origen-ia": ("Metadatos IPTC declaran contenido generado con IA (DigitalSourceType)",
                      "IPTC metadata declare AI-generated content (DigitalSourceType)"),
    "parametros-generacion": ("Parámetros de generación de Stable Diffusion/ComfyUI/InvokeAI en la imagen",
                              "Stable Diffusion/ComfyUI/InvokeAI generation parameters in the image"),
    "metadatos-generador": ("Nombre de un generador de IA en los metadatos (EXIF/XMP/PNG)",
                            "AI generator name in metadata (EXIF/XMP/PNG)"),
}


def t(clave: str, **valores) -> str:
    textos = TEXTOS.get(clave)
    if textos is None:
        return clave
    texto = textos[0] if _ESTADO["idioma"] == "es" else textos[1]
    return texto.format(**valores) if valores else texto


def describir(regla: str) -> str:
    textos = DESCRIPCIONES.get(regla, (regla, regla))
    return textos[0] if _ESTADO["idioma"] == "es" else textos[1]


def t_ficheros(n: int) -> str:
    return t("ui.ficheros_1") if n == 1 else t("ui.ficheros_n", n=n)


def t_lineas(n: int, ejemplo: str) -> str:
    return t("ev.lineas_1", e=ejemplo) if n == 1 else t("ev.lineas_n", n=n, e=ejemplo)


# ---------------------------------------------------------------------------
# Avance del análisis (para la barra de progreso de la interfaz y la consola)
# ---------------------------------------------------------------------------

FASES = ("subida", "descarga", "ia", "imagenes", "ficheros", "git", "scripts", "seguridad", "dns", "activo", "codigo")
_AVANCE: dict = {"f": None}
_PARAR = threading.Event()


class Cancelado(BaseException):
    """El usuario ha detenido el análisis.

    Hereda de BaseException, como KeyboardInterrupt, para que los ``except Exception`` que toleran fallos
    puntuales (una imagen corrupta, una página que no responde) no la absorban y el análisis se corte de verdad.
    """


def pedir_parada() -> None:
    """Pide detener el análisis en curso; se atiende en el siguiente aviso de avance."""
    _PARAR.set()


def anular_parada() -> None:
    _PARAR.clear()


def fijar_avance(funcion) -> None:
    _AVANCE["f"] = funcion if callable(funcion) else None


def informar(fase: str, hecho: int = 0, total: int = 0, detalle: str = "") -> None:
    """Comunica el avance de una fase y atiende la petición de parada.

    Si el receptor del progreso falla, el análisis sigue; si el usuario ha pedido parar, lanza Cancelado.
    """
    if _PARAR.is_set():
        raise Cancelado()
    funcion = _AVANCE["f"]
    if funcion is None:
        return
    try:
        funcion({"fase": fase, "hecho": int(hecho), "total": int(total), "detalle": str(detalle)[:160]})
    except Exception:  # noqa: BLE001 - el progreso es informativo: si el receptor falla, se desactiva
        _AVANCE["f"] = None


# ---------------------------------------------------------------------------
# Escala de pesos y límites
# ---------------------------------------------------------------------------

PESOS = {"explicito": 40, "fuerte": 20, "medio": 8, "debil": 3}
ORDEN_NIVEL = ["explicito", "fuerte", "medio", "debil"]
MAX_REPETICION = 3.0          # un marcador repetido suma como máximo 3 veces su peso
MIN_PALABRAS_ESTILO = 150     # por debajo no se puntúa el estilo del texto
MAX_TAMANO_FICHERO = 3_000_000
MAX_TAMANO_IMAGEN = 50_000_000
MAX_IMAGEN_WEB = 15_000_000
MAX_IMAGENES_WEB = 15
MAX_TEXTO_COMPRIMIDO = 2_000_000  # límite al descomprimir bloques zTXt/iTXt de PNG
PREVALENCIA_PLENA = 0.10      # medio/débil puntúan completos si afectan al 10 % de los ficheros
# Marcadores de nivel de proyecto o de datos: no se escalan por número de ficheros
SIN_PREVALENCIA = {"commits-grandes", "mensajes-uniformes", "rafaga-datos", "coordenadas-mixtas",
                   "stack-generador", "llms-txt", "framework-ia"}

UMBRALES_BANDA = [(70, "banda.alta"), (40, "banda.media"), (15, "banda.baja"), (0, "banda.nula")]

EXT_CODIGO = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".ps1", ".psm1", ".psd1", ".sh", ".bash",
    ".zsh", ".bat", ".cmd", ".java", ".kt", ".swift", ".go", ".rs", ".rb", ".php", ".c", ".h",
    ".cpp", ".hpp", ".cs", ".vb", ".lua", ".r", ".sql", ".scala", ".dart", ".vue", ".svelte",
    ".css", ".scss", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".json",
}
EXT_TEXTO = {".md", ".markdown", ".txt", ".rst", ".adoc", ".org", ".tex"}
EXT_HTML = {".html", ".htm", ".xhtml"}
EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".avif", ".tif", ".tiff", ".jxl", ".gif", ".dng"}

DIRS_IGNORADOS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build", ".next",
    ".nuxt", "out", "target", "vendor", ".tox", ".mypy_cache", ".pytest_cache", "coverage",
    ".idea", ".vscode-test", "bower_components", "site-packages",
}

# Ficheros y carpetas que solo existen para dar instrucciones a agentes de IA
FICHEROS_AGENTE = {
    "CLAUDE.md": "Claude Code", "CLAUDE.local.md": "Claude Code", "AGENTS.md": "Codex / AGENTS.md",
    "GEMINI.md": "Gemini CLI", ".cursorrules": "Cursor", ".windsurfrules": "Windsurf",
    ".clinerules": "Cline", ".roomodes": "Roo Code", "copilot-instructions.md": "GitHub Copilot",
    ".aider.conf.yml": "Aider", ".aider.chat.history.md": "Aider", ".aider.input.history": "Aider",
    "CONVENTIONS.md": "Aider", ".replit": "Replit", "replit.nix": "Replit",
}
DIRS_AGENTE = {
    ".claude": "Claude Code", ".cursor": "Cursor", ".windsurf": "Windsurf", ".kiro": "Kiro",
    ".clinerules": "Cline", ".roo": "Roo Code", ".continue": "Continue", ".opencode": "OpenCode",
    ".junie": "JetBrains Junie", ".amazonq": "Amazon Q", ".gemini": "Gemini CLI",
    ".specstory": "SpecStory",
}

# ---------------------------------------------------------------------------
# Modelos de datos
# ---------------------------------------------------------------------------


@dataclass
class Hallazgo:
    regla: str
    nivel: str
    ubicacion: str
    extracto: str = ""

    @property
    def peso(self) -> int:
        return PESOS[self.nivel]

    @property
    def descripcion(self) -> str:
        return describir(self.regla)


@dataclass
class Resultado:
    objetivo: str
    tipo: str  # clave: dir, repo, url, html, texto, codigo, imagen, fichero, desconocido
    hallazgos: list[Hallazgo] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)
    ficheros_analizados: int = 0
    imagenes_sin_metadatos: int = 0
    seguridad: object = None  # InformeSeguridad del módulo aimarkers_seguridad
    solo_seguridad: bool = False

    def anadir(self, regla: str, nivel: str, ubicacion: str, extracto: str = "") -> None:
        extracto = re.sub(r"\s+", " ", extracto).strip()
        if len(extracto) > 160:
            extracto = extracto[:157] + "..."
        self.hallazgos.append(Hallazgo(regla, nivel, ubicacion, extracto))

    def es_proyecto(self) -> bool:
        return self.tipo in ("dir", "repo")

    # --- puntuación -------------------------------------------------------
    def por_regla(self) -> dict[str, list[Hallazgo]]:
        grupos: dict[str, list[Hallazgo]] = {}
        for h in self.hallazgos:
            grupos.setdefault(h.regla, []).append(h)
        return grupos

    def prevalencia(self, lista: list[Hallazgo]) -> float:
        """Fracción de ficheros afectados por un marcador (1.0 si se analizan pocos ficheros)."""
        if self.ficheros_analizados < 10:
            return 1.0
        ficheros = {h.ubicacion.split(":")[0] for h in lista}
        return len(ficheros) / self.ficheros_analizados

    def contribucion(self, lista: list[Hallazgo]) -> float:
        n = len(lista)
        total = lista[0].peso * min(MAX_REPETICION, 1 + 0.5 * (n - 1))
        if lista[0].nivel in ("medio", "debil") and lista[0].regla not in SIN_PREVALENCIA:
            # En proyectos grandes, un rasgo aislado pesa menos: escala lineal hasta el 10 % de ficheros
            total *= min(1.0, self.prevalencia(lista) / PREVALENCIA_PLENA)
        return total

    def puntuacion(self) -> int:
        total = sum(self.contribucion(lista) for lista in self.por_regla().values())
        return int(min(100, round(total)))

    def clave_banda(self) -> str:
        p = self.puntuacion()
        if (self.tipo == "imagen" and not self.hallazgos and self.imagenes_sin_metadatos
                and self.imagenes_sin_metadatos == self.ficheros_analizados):
            return "banda.indeterminada"  # sin metadatos no hay nada que leer: ni a favor ni en contra
        if p < 15 and any(h.nivel in ("medio", "fuerte") for h in self.hallazgos):
            return "banda.baja"  # hay algún indicio concreto aunque puntúe poco
        for umbral, clave in UMBRALES_BANDA:
            if p >= umbral:
                return clave
        return "banda.nula"

    def banda(self) -> str:
        return t(self.clave_banda())

    def atribucion_explicita(self) -> bool:
        return any(h.nivel == "explicito" for h in self.hallazgos)

    def a_dict(self) -> dict:
        return {
            "objetivo": self.objetivo,
            "tipo": t(f"tipo.{self.tipo}"),
            "puntuacion": self.puntuacion(),
            "valoracion": self.banda(),
            "atribucion_explicita": self.atribucion_explicita(),
            "ficheros_analizados": self.ficheros_analizados,
            "idioma": idioma(),
            "notas": self.notas,
            "seguridad": self.seguridad.a_dict() if self.seguridad is not None else None,
            "hallazgos": [{"regla": h.regla, "nivel": h.nivel, "descripcion": h.descripcion,
                           "ubicacion": h.ubicacion, "extracto": h.extracto, "peso": h.peso} for h in self.hallazgos],
            "resumen_por_marcador": {
                k: {"nivel": v[0].nivel, "veces": len(v), "puntos": round(self.contribucion(v), 1),
                    "prevalencia": round(self.prevalencia(v), 4)}
                for k, v in self.por_regla().items()},
        }


# ---------------------------------------------------------------------------
# Reglas basadas en expresiones regulares: (id, nivel, patrón)
# ---------------------------------------------------------------------------

I = re.IGNORECASE
M = re.MULTILINE

# Aplicables a cualquier contenido (código, texto, HTML)
REGLAS_GENERALES = [
    ("firma-generador", "explicito",
     re.compile(r"(?:generated|created|written|built)\s+(?:with|by|using)\s+\[?(?:claude(?:\s+code)?|chatgpt|gpt-?[345o][\w.-]*|github\s+copilot|copilot|cursor|gemini|codeium|windsurf|devin|aider|lovable|bolt\.new|v0(?:\.dev|\.app)?)\b", I)),
    ("firma-robot", "explicito", re.compile(r"🤖\s*Generated\s+with", I)),
    ("coautor-ia", "explicito",
     re.compile(r"Co-?authored-?by:\s*[^\n<]{0,120}(?:claude|anthropic|copilot|cursor\s*agent|devin|aider|openai|codex|gemini|jules)", I)),
    ("citas-chatgpt", "explicito",
     re.compile(r"contentReference\[oaicite:\d+\]|oaicite:\d+|\ue200cite|turn\d+(?:search|news|view|fetch)\d+", I)),
    ("utm-chatgpt", "explicito",
     re.compile(r"utm_source=(?:chatgpt\.com|chatgpt|openai|perplexity|copilot\.microsoft|gemini)", I)),
    ("autodeclaracion-modelo", "explicito",
     re.compile(r"as an ai (?:language )?model|as a large language model|como (?:un )?modelo de (?:lenguaje|ia)|(?:my|mi) (?:knowledge cutoff|fecha de corte de conocimiento)", I)),
]
RE_COAUTOR = REGLAS_GENERALES[2][2]
RE_FIRMAS_COMMIT = (REGLAS_GENERALES[0][2], REGLAS_GENERALES[1][2])

# Restos de conversación con el chat
REGLAS_CHAT = [
    ("resto-chat", "fuerte",
     re.compile(r"^\W{0,6}(?:certainly!|sure! here|of course! here|here(?:'s| is) (?:the|your) (?:updated|complete|full|revised|corrected|improved|final|refactored)|claro,? aquí (?:tienes|está)|¡claro! aquí|por supuesto,? aquí (?:tienes|está)|aquí tienes (?:el|la|tu) (?:código|script|versión) (?:actualizad|complet|corregid|mejorad))", I | M)),
    ("cierre-chat", "fuerte",
     re.compile(r"(?:i hope this helps|hope this helps!|let me know if you(?:'d| would) like me to|would you like me to (?:add|create|write|generate|expand|adjust|make)|espero que (?:esto )?te (?:sea|resulte) (?:de )?(?:útil|ayuda)|¿quieres que (?:te )?(?:lo|la|añada|prepare|genere|adapte|amplíe|redacte)|si quieres,? (?:también )?puedo (?:prepararte|generarte|añadir|crear|redactar|adaptar))", I)),
]

# Huecos de plantilla: solo en texto, con mayúscula inicial y sin ser enlace Markdown
REGLA_HUECO = ("hueco-plantilla", "fuerte",
               re.compile(r"\[(?:Insert|Insertar|Inserte|Añadir|Add|Your|YOUR|Tu|TU|Su|Nombre|NOMBRE|Company|Empresa|EMPRESA|Fecha|FECHA|Date|Name)\b[^\]\n]{0,40}\](?![(:\[])"))

# Específicas de código
RE_COMENTARIO = re.compile(r"^\s*(?:#|//|/\*|\*|--|<!--|REM\b|')", I)
REGLAS_CODIGO_LINEA = [
    ("comentario-demo", "medio",
     re.compile(r"in a real(?:-world)? (?:application|app|implementation|scenario|project|system|environment)|for (?:demonstration|demo|illustration) purposes|this is a (?:simplified|basic|placeholder|mock) (?:version|implementation|example)|you would (?:typically|normally|usually)|placeholder (?:implementation|logic)|en (?:un|una) (?:entorno|aplicación|proyecto|caso|implementación) real|con fines (?:de demostración|demostrativos|ilustrativos)|esto es una (?:versión|implementación) simplificada|aquí (?:iría|irá) (?:la|tu) lógica", I)),
    ("placeholder", "medio",
     re.compile(r"your[_-]?api[_-]?key(?:[_-]?here)?|YOUR_(?:API_KEY|TOKEN|SECRET|PASSWORD|CLIENT_ID)|<YOUR_[A-Z_]+>|replace (?:this )?with your (?:actual|own|real)|reempla(?:za|ce|zar) (?:esto )?(?:con|por) (?:tu|su|el valor real)|TU_(?:API_KEY|TOKEN|CLAVE)", I)),
]
RE_PASO = re.compile(r"^\s*(?:#|//|--|REM)\s*(?:step|paso)\s*\d+\s*[:.)-]", I)
RE_EMOJI_LOG = re.compile(r"(?:print\s*\(|console\.(?:log|error|warn|info)|Write-(?:Host|Output|Warning)|logger\.\w+\(|logging\.\w+\(|echo\s)[^\n]*[✅❌🚀⚠✨🔥📊🎉💡🔍📁🔧⏳🛑📝🔄👉✔✓🎯📦🧹]")
RE_EXCEPT_GENERICO = re.compile(r"except\s+Exception(?:\s+as\s+\w+)?\s*:\s*\n\s*(?:print|logger\.\w+|logging\.\w+)\s*\(\s*f?[\"'](?:an? )?(?:unexpected )?error(?: occurred)?|catch\s*\(\s*\w+\s*\)\s*\{\s*\n\s*console\.error\(\s*[\"'`](?:an? )?error(?: occurred)?", I)
RE_TIPOGRAFICO = re.compile(r"[—“”’\u00a0\u200b\u200c\u200d\u2060\ufeff]")
RE_VALLA = re.compile(r"^```[a-zA-Z0-9_+-]*\s*$", M)

# Muletillas
MULETILLAS_EN = [
    r"\bdelve(?:s|d)?\b", r"\btapestry\b", r"\btestament to\b", r"\bseamless(?:ly)?\b", r"\brobust\b",
    r"\bleverag(?:e|es|ing)\b", r"it(?:'s| is) (?:worth noting|important to note)", r"in today's (?:fast-paced|digital|ever-evolving)",
    r"navigat(?:e|ing) the (?:complexities|landscape)", r"\bever-evolving\b", r"\brealm of\b", r"\bunlock(?:s|ing)? the (?:power|potential)\b",
    r"\bin conclusion\b", r"\bplays? a (?:crucial|pivotal|vital) role\b", r"\bcutting-edge\b", r"\bmeticulous(?:ly)?\b",
    r"\bfoster(?:s|ing)?\b", r"\bunderscore(?:s|d)?\b", r"\bholistic\b", r"\bgame-changer\b", r"\bembark\b",
]
MULETILLAS_ES = [
    r"\bcabe (?:destacar|señalar|mencionar|resaltar)\b", r"\bes importante (?:señalar|destacar|tener en cuenta|recordar)\b",
    r"\ben el (?:panorama|contexto|mundo) actual\b", r"\bdesempeña(?:n)? un papel (?:crucial|fundamental|clave|esencial)\b",
    r"\bun (?:amplio )?abanico de\b", r"\ben definitiva\b", r"\bsin lugar a dudas\b", r"\bprofundizar en\b",
    r"\bun testimonio de\b", r"\ben resumen\b", r"\bfomentar\b", r"\bpotenciar\b", r"\bde manera (?:eficiente|efectiva|integral)\b",
    r"\bsinergia(?:s)?\b", r"\bpanorama\b", r"\bnavegar (?:por )?(?:las complejidades|el panorama)\b", r"\bes fundamental\b",
    r"\ben última instancia\b", r"\bno solo\b[^.]{1,80}\bsino también\b", r"\bal fin y al cabo\b", r"\bclave para\b",
]
RE_MULETILLAS = [re.compile(p, I) for p in MULETILLAS_EN + MULETILLAS_ES]
RE_VINETA_NEGRITA = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\*\*[^*\n]{1,60}:?\*\*:?", M)
RE_VINETA = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\S", M)
RE_EMOJI_TITULO = re.compile(r"^#{1,6}\s*[\U0001F300-\U0001FAFF\u2600-\u27BF]", M)

# HTML / web
REGLAS_HTML = [
    ("gen-lovable", "fuerte",
     re.compile(r"data-lov-(?:id|name)|gptengineer(?:\.js)?|cdn\.gpteng\.co|lovable-tagger|lovable\.(?:dev|app)/|edit with lovable", I)),
    ("gen-v0", "fuerte",
     re.compile(r"<meta[^>]{0,200}name=[\"']generator[\"'][^>]{0,200}content=[\"']v0(?:\.dev|\.app)?[\"']|made with v0|v0\.(?:dev|app)/chat", I)),
    ("gen-bolt", "fuerte", re.compile(r"bolt\.new|made in bolt|built with bolt", I)),
    ("gen-otros", "fuerte",
     re.compile(r"readdy\.ai|base44\.(?:app|com)|durable\.co|10web\.io/ai|same\.(?:dev|new)/|create\.xyz|tempo\.new|framer\.ai|hostinger[^\"'<]{0,30}ai builder|wix(?:[^\"'<]{0,20})adi\b", I)),
    ("imagen-ia", "fuerte",
     re.compile(r"(?:src|href|content|srcset)=[\"'][^\"']{0,300}?(?:dall[·\-_ %c2b7]*e|chatgpt[ _-]?image|gemini_generated_image|midjourney|mj_|firefly|leonardo[_.-]ai|ideogram|stable[-_]?diffusion|sdxl|flux[-_]?(?:dev|schnell|pro))[^\"']{0,300}[\"']", I)),
    ("framework-ia", "debil", re.compile(r"vinext", I)),
]
RE_META_GENERATOR = re.compile(r"<meta[^>]{0,200}name=[\"']generator[\"'][^>]{0,200}content=[\"']([^\"']{1,200})[\"']", I)
RE_TIMESTAMP = re.compile(
    r"\\?[\"'](?:created_?at|createdAt|inserted_?at|insertedAt|date_?created|dateCreated|published_?at|publishedAt|creado_?en|fecha_?alta)\\?[\"']\s*:\s*\\?[\"']"
    r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)", I)
RE_LATITUD = re.compile(r"\\?[\"'](?:latitude|lat)\\?[\"']\s*:\s*(-?\d{1,3}(?:\.\d+)?)", I)
RE_STACK_GENERADOR = [
    re.compile(r"data-slot=[\"']"),                                                     # shadcn/ui
    re.compile(r"class=[\"'][^\"']{0,300}lucide lucide-"),                              # iconos lucide
    re.compile(r"from-(?:purple|violet|indigo)-\d{3}[^\"']{0,200}to-(?:blue|pink|cyan)-\d{3}"),  # degradado por defecto
]
RE_IMG_HTML = re.compile(
    r"<img\b[^>]{0,500}?\bsrc=[\"']([^\"'>\s]{1,1000})[\"']"
    r"|<meta[^>]{0,200}(?:property|name)=[\"'](?:og:image|twitter:image)[\"'][^>]{0,200}content=[\"']([^\"'>\s]{1,1000})[\"']", I)

# Git
RE_BOT_AUTOR = re.compile(r"copilot-swe-agent|copilot\[bot\]|devin-ai-integration|google-labs-jules|claude\[bot\]|cursor(?:agent|-agent)|openai-codex|codex\[bot\]|sweep-ai|\(aider\)", I)
RE_RAMA_AGENTE = re.compile(r"^(?:remotes/)?(?:origin/)?(?:claude|copilot|cursor|codex|devin|jules|aider|sweep|windsurf)[/-]", I)
RE_CONVENTIONAL = re.compile(r"^(?:feat|fix|chore|docs|refactor|test|style|perf|build|ci|revert)(?:\([^)]+\))?!?: ")

# Imágenes: nombres de generadores en metadatos de texto
RE_GENERADOR_META = re.compile(
    r"midjourney|dall[·\-\s]?e\b|chatgpt|openai|stable[ -]?diffusion|automatic1111|comfyui|invokeai|novelai|"
    r"adobe firefly|\bfirefly\b|google imagen|\bimagen [0-9]|gemini|nano[ -]?banana|leonardo\.ai|ideogram|flux\.1|"
    r"black forest labs|bing image creator|image creator from microsoft|meta ai|\bgrok\b|\bkrea\b|playground ?ai|"
    r"dreamstudio|nightcafe|craiyon|\bsora\b|runwayml|\brecraft\b", I)
RE_ORIGEN_DIGITAL = re.compile(r"digitalsourcetype/([A-Za-z]+)", I)
ORIGENES_IA = {"trainedAlgorithmicMedia"}
ORIGENES_EDICION_IA = {"compositeWithTrainedAlgorithmicMedia"}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def contar_palabras(texto: str) -> int:
    return len(re.findall(r"\w+", texto))


def num_linea(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos) + 1


def leer_fichero(ruta: Path) -> str | None:
    try:
        if ruta.stat().st_size > MAX_TAMANO_FICHERO:
            return None
        datos = ruta.read_bytes()
    except OSError:
        return None
    if b"\x00" in datos[:4096]:
        return None  # binario
    for codificacion in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return None


def es_minificado(texto: str) -> bool:
    lineas = texto.splitlines() or [""]
    return len(lineas) < 5 and len(texto) > 5000 or max(len(l) for l in lineas) > 3000 and len(lineas) < 50


def aplicar_reglas(res: Resultado, texto: str, reglas, ubic: str, max_por_regla: int = 5) -> None:
    for regla, nivel, patron in reglas:
        limite = 1 if nivel == "debil" else max_por_regla
        lineas_vistas: set[int] = set()
        for m in patron.finditer(texto):
            linea = num_linea(texto, m.start())
            if linea in lineas_vistas:
                continue
            lineas_vistas.add(linea)
            inicio = max(0, m.start() - 30)
            res.anadir(regla, nivel, f"{ubic}:{linea}", texto[inicio:m.end() + 40])
            if len(lineas_vistas) >= limite:
                break


def parsear_fecha(valor: str) -> float | None:
    v = valor.replace(" ", "T")
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    m = re.match(r"(.*[T]\d{2}:\d{2}:\d{2})(\.\d+)?(.*)$", v)
    if m and m.group(2):
        # Python 3.9/3.10 (el de macOS) solo acepta exactamente 6 decimales
        v = m.group(1) + "." + m.group(2)[1:7].ljust(6, "0") + m.group(3)
    try:
        return datetime.fromisoformat(v).timestamp()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Análisis de texto (documentación, Markdown, texto visible de webs)
# ---------------------------------------------------------------------------


def analizar_estilo(res: Resultado, texto: str, ubic: str) -> None:
    palabras = contar_palabras(texto)
    if palabras < MIN_PALABRAS_ESTILO:
        if palabras >= 50 and not res.es_proyecto():
            res.notas.append(t("nota.muestra", u=ubic, n=palabras))
        return

    # Muletillas: solo cuentan por densidad
    encontradas: list[str] = []
    for patron in RE_MULETILLAS:
        encontradas += [m.group(0) for m in patron.finditer(texto)]
    densidad = len(encontradas) * 1000 / palabras
    if len(encontradas) >= 3 and densidad >= 3:
        unicas = sorted({e.lower() for e in encontradas})
        res.anadir("muletillas", "debil", ubic,
                   t("ev.muletillas", n=len(encontradas), d=f"{densidad:.1f}", l=", ".join(unicas[:10])))

    # Raya tipográfica
    rayas = texto.count("—")
    if rayas >= 5 and rayas * 100 / palabras > 1:
        res.anadir("rayas", "debil", ubic, t("ev.rayas", n=rayas, p=palabras))

    # Viñetas con término en negrita
    vinetas = len(RE_VINETA.findall(texto))
    negritas = len(RE_VINETA_NEGRITA.findall(texto))
    if negritas >= 5 and vinetas and negritas / vinetas >= 0.5:
        res.anadir("vinetas-negrita", "debil", ubic, t("ev.vinetas", a=negritas, b=vinetas))

    # Emojis en títulos
    titulos_emoji = len(RE_EMOJI_TITULO.findall(texto))
    if titulos_emoji >= 3:
        res.anadir("emoji-titulos", "debil", ubic, t("ev.titulos", n=titulos_emoji))

    # Ritmo de frases (burstiness)
    prosa = re.sub(r"```.*?```", " ", texto, flags=re.DOTALL)
    prosa = "\n".join(l for l in prosa.splitlines() if not RE_VINETA.match(l) and not l.lstrip().startswith(("#", "|")))
    frases = [f for f in re.split(r"(?<=[.!?])\s+", prosa) if contar_palabras(f) >= 3]
    if len(frases) >= 15:
        longitudes = [contar_palabras(f) for f in frases]
        media = statistics.mean(longitudes)
        cv = statistics.pstdev(longitudes) / media if media else 1
        if cv < 0.35:
            res.anadir("ritmo-uniforme", "debil", ubic, t("ev.ritmo", n=len(frases), m=f"{media:.1f}", cv=f"{cv:.2f}"))


def analizar_texto(res: Resultado, texto: str, ubic: str) -> None:
    aplicar_reglas(res, texto, REGLAS_GENERALES, ubic)
    aplicar_reglas(res, texto, [*REGLAS_CHAT, REGLA_HUECO], ubic, max_por_regla=3)
    analizar_estilo(res, texto, ubic)


# ---------------------------------------------------------------------------
# Análisis de código
# ---------------------------------------------------------------------------


def analizar_codigo(res: Resultado, texto: str, ubic: str, extension: str) -> None:
    aplicar_reglas(res, texto, REGLAS_GENERALES, ubic)
    aplicar_reglas(res, texto, [r for r in REGLAS_CHAT if r[0] == "resto-chat"], ubic, max_por_regla=3)

    lineas = texto.splitlines()
    comentarios = [(i + 1, l) for i, l in enumerate(lineas) if RE_COMENTARIO.match(l) or "#" in l or "//" in l]

    for regla, nivel, patron in REGLAS_CODIGO_LINEA:
        vistos = 0
        lista = comentarios if regla == "comentario-demo" else list(enumerate(lineas, 1))
        for n, l in lista:
            if patron.search(l):
                res.anadir(regla, nivel, f"{ubic}:{n}", l)
                vistos += 1
                if vistos >= 5:
                    break

    pasos = [(n, l) for n, l in enumerate(lineas, 1) if RE_PASO.match(l)]
    if len(pasos) >= 3:
        res.anadir("comentarios-paso", "debil", f"{ubic}:{pasos[0][0]}", t("ev.pasos", n=len(pasos), e=pasos[0][1].strip()))

    emojis = [(n, l) for n, l in enumerate(lineas, 1) if RE_EMOJI_LOG.search(l)]
    if emojis:
        res.anadir("emoji-logs", "medio", f"{ubic}:{emojis[0][0]}", t_lineas(len(emojis), emojis[0][1].strip()))

    if extension not in {".md", ".json", ".yml", ".yaml", ".toml"}:
        # Solo cuenta si envuelve el fichero (rastro de copiar del chat), no si está en un docstring
        no_vacias = [(n, l) for n, l in enumerate(lineas, 1) if l.strip()]
        candidato = None
        # Al principio: primera línea, o segunda tras una frase de chat, y fuera de un docstring
        for i, (n, l) in enumerate(no_vacias[:2]):
            previo = "\n".join(x for _, x in no_vacias[:i])
            if RE_VALLA.match(l) and '"""' not in previo and "'''" not in previo:
                candidato = (n, l)
                break
        # Al final: última línea no vacía, sin docstring abierto
        if not candidato and no_vacias and RE_VALLA.match(no_vacias[-1][1]) \
                and texto.count('"""') % 2 == 0 and texto.count("'''") % 2 == 0 \
                and not re.search(r'(?:"""|\'\'\')\s*$', "\n".join(l for _, l in no_vacias[-4:-1])):
            # exige que no esté cerrando un bloque de ejemplo dentro de un comentario o docstring
            ultimas = [l for _, l in no_vacias[-12:-1]]
            if not any(RE_VALLA.match(l) for l in ultimas):
                candidato = no_vacias[-1]
        if candidato:
            res.anadir("valla-markdown", "fuerte", f"{ubic}:{candidato[0]}", candidato[1])

    if extension == ".py":
        funciones = re.findall(r"^\s*def \w+\(", texto, M)
        docs_args = re.findall(r"\"\"\"[^\"]*?\n\s*(?:Args|Parameters|Returns):", texto)
        if len(funciones) >= 5 and len(docs_args) / len(funciones) >= 0.8:
            res.anadir("docstrings-uniformes", "debil", ubic, t("ev.funciones", a=len(docs_args), b=len(funciones)))

    genericos = RE_EXCEPT_GENERICO.findall(texto)
    if len(genericos) >= 3:
        res.anadir("errores-genericos", "debil", ubic, t("ev.bloques", n=len(genericos)))

    if extension not in {".md", ".txt", ".json"}:
        tip = [(n, l) for n, l in enumerate(lineas, 1) if RE_TIPOGRAFICO.search(l)]
        if len(tip) >= 2:
            res.anadir("tipografia-codigo", "debil", f"{ubic}:{tip[0][0]}", t_lineas(len(tip), tip[0][1].strip()))

    # Densidad de comentarios, sin contar la cabecera inicial (licencia, shebang)
    cuerpo = list(lineas)
    while cuerpo and (not cuerpo[0].strip() or RE_COMENTARIO.match(cuerpo[0])):
        cuerpo.pop(0)
    cuerpo = [l for l in cuerpo if l.strip()]
    if len(cuerpo) >= 40:
        densidad = sum(1 for l in cuerpo if RE_COMENTARIO.match(l)) / len(cuerpo)
        if densidad >= 0.4:
            res.anadir("densidad-comentarios", "debil", ubic, t("ev.densidad", p=f"{densidad:.0%}"))


# ---------------------------------------------------------------------------
# Imágenes: C2PA (JUMBF + CBOR + COSE), XMP, EXIF y textos PNG
# ---------------------------------------------------------------------------


class ErrorFormato(ValueError):
    """Estructura binaria no válida o fuera de los límites de seguridad."""


class LectorCBOR:
    """Decodificador CBOR (RFC 8949) mínimo y acotado: profundidad, número de elementos y límites del búfer."""

    MAX_PROFUNDIDAD = 64
    MAX_ELEMENTOS = 200_000

    def __init__(self, datos: bytes) -> None:
        self.d = datos
        self.i = 0
        self.elementos = 0

    def _byte(self) -> int:
        if self.i >= len(self.d):
            raise ErrorFormato("cbor truncado")
        b = self.d[self.i]
        self.i += 1
        return b

    def _bytes(self, n: int) -> bytes:
        if n < 0 or self.i + n > len(self.d):
            raise ErrorFormato("cbor truncado")
        b = self.d[self.i:self.i + n]
        self.i += n
        return b

    def _argumento(self, info: int) -> int | None:
        if info < 24:
            return info
        if info in (24, 25, 26, 27):
            return int.from_bytes(self._bytes(1 << (info - 24)), "big")
        if info == 31:
            return None  # longitud indefinida
        raise ErrorFormato("cbor: argumento reservado")

    def leer(self, profundidad: int = 0):
        if profundidad > self.MAX_PROFUNDIDAD:
            raise ErrorFormato("cbor demasiado profundo")
        self.elementos += 1
        if self.elementos > self.MAX_ELEMENTOS:
            raise ErrorFormato("cbor demasiado grande")
        inicial = self._byte()
        tipo, info = inicial >> 5, inicial & 0x1F
        if tipo == 7:
            if info == 20:
                return False
            if info == 21:
                return True
            if info in (22, 23):
                return None
            if info == 25:
                return struct.unpack(">e", self._bytes(2))[0]
            if info == 26:
                return struct.unpack(">f", self._bytes(4))[0]
            if info == 27:
                return struct.unpack(">d", self._bytes(8))[0]
            if info < 24:
                return info
            raise ErrorFormato("cbor: valor simple no admitido")
        valor = self._argumento(info)
        if tipo == 0:
            return valor
        if tipo == 1:
            return -1 - (valor or 0)
        if tipo in (2, 3):
            if valor is None:  # cadena por trozos
                trozos = []
                while self.i < len(self.d) and self.d[self.i] != 0xFF:
                    trozos.append(self.leer(profundidad + 1))
                self._byte()
                crudo = b"".join(x if isinstance(x, bytes) else str(x).encode() for x in trozos)
            else:
                crudo = self._bytes(valor)
            return crudo if tipo == 2 else crudo.decode("utf-8", "replace")
        if tipo == 4:
            lista = []
            if valor is None:
                while self.i < len(self.d) and self.d[self.i] != 0xFF:
                    lista.append(self.leer(profundidad + 1))
                self._byte()
            else:
                for _ in range(valor):
                    lista.append(self.leer(profundidad + 1))
            return lista
        if tipo == 5:
            mapa = {}
            pares = 0
            while (valor is None and self.i < len(self.d) and self.d[self.i] != 0xFF) or (valor is not None and pares < valor):
                clave = self.leer(profundidad + 1)
                if isinstance(clave, (list, dict)):
                    clave = repr(clave)
                mapa[clave] = self.leer(profundidad + 1)
                pares += 1
            if valor is None:
                self._byte()
            return mapa
        # tipo 6: etiqueta; se devuelve el valor etiquetado
        return self.leer(profundidad + 1)


def decodificar_cbor(datos: bytes):
    try:
        return LectorCBOR(datos).leer()
    except (ErrorFormato, IndexError, struct.error, RecursionError):
        return None


def _cajas_jumbf(d: bytes, ini: int, fin: int):
    """Recorre cajas ISO BMFF/JUMBF: (tipo, inicio_contenido, fin)."""
    while ini + 8 <= fin:
        largo = struct.unpack(">I", d[ini:ini + 4])[0]
        tipo = d[ini + 4:ini + 8]
        cabecera = 8
        if largo == 1:
            if ini + 16 > fin:
                return
            largo = struct.unpack(">Q", d[ini + 8:ini + 16])[0]
            cabecera = 16
        elif largo == 0:
            largo = fin - ini
        if largo < cabecera or ini + largo > fin:
            return
        yield tipo, ini + cabecera, ini + largo
        ini += largo


def leer_superbox(d: bytes, ini: int, fin: int, profundidad: int = 0) -> dict | None:
    """Convierte una superbox JUMBF ('jumb') en {'etiqueta', 'hijos', 'contenido'}."""
    if profundidad > 16:
        return None
    nodo: dict = {"etiqueta": "", "hijos": [], "contenido": []}
    primera = True
    for tipo, a, b in _cajas_jumbf(d, ini, fin):
        if primera:
            primera = False
            if tipo != b"jumd" or b - a < 17:
                return None
            conmutadores = d[a + 16]
            if conmutadores & 0x02:
                fin_etiqueta = d.find(b"\x00", a + 17, b)
                if fin_etiqueta == -1:
                    fin_etiqueta = b
                nodo["etiqueta"] = d[a + 17:fin_etiqueta].decode("utf-8", "replace")
            continue
        if tipo == b"jumb":
            hijo = leer_superbox(d, a, b, profundidad + 1)
            if hijo:
                nodo["hijos"].append(hijo)
        else:
            nodo["contenido"].append((tipo, d[a:b]))
    return None if primera else nodo


def buscar_almacen_c2pa(d: bytes) -> dict | None:
    """Localiza el almacén de manifiestos C2PA (superbox con etiqueta 'c2pa') dentro de un bloque JUMBF."""
    for tipo, a, b in _cajas_jumbf(d, 0, len(d)):
        if tipo == b"jumb":
            nodo = leer_superbox(d, a, b)
            if nodo and nodo["etiqueta"] == "c2pa":
                return nodo
    return None


def buscar_c2pa_suelto(d: bytes) -> dict | None:
    """Plan B para formatos sin lector propio (HEIC, AVIF, TIFF…): busca una caja 'jumb' con etiqueta c2pa."""
    pos = d.find(b"jumb")
    intentos = 0
    while pos != -1 and intentos < 64:
        intentos += 1
        if pos >= 4:
            largo = struct.unpack(">I", d[pos - 4:pos])[0]
            if 16 < largo <= len(d) - (pos - 4):
                nodo = leer_superbox(d, pos + 4, pos - 4 + largo)
                if nodo and nodo["etiqueta"] == "c2pa":
                    return nodo
        pos = d.find(b"jumb", pos + 4)
    return None


def _tlv_der(d: bytes, i: int) -> tuple[int, int, int]:
    if i + 2 > len(d):
        raise ErrorFormato("der truncado")
    etiqueta, largo = d[i], d[i + 1]
    inicio = i + 2
    if largo & 0x80:
        n = largo & 0x7F
        if n == 0 or n > 4 or inicio + n > len(d):
            raise ErrorFormato("der: longitud no admitida")
        largo = int.from_bytes(d[inicio:inicio + n], "big")
        inicio += n
    if inicio + largo > len(d):
        raise ErrorFormato("der truncado")
    return etiqueta, inicio, inicio + largo


def _hijos_der(d: bytes, ini: int, fin: int) -> list[tuple[int, int, int]]:
    hijos = []
    while ini < fin:
        etiqueta, a, b = _tlv_der(d, ini)
        hijos.append((etiqueta, a, b))
        ini = b
    return hijos


def _nombre_der(d: bytes, ini: int, fin: int) -> dict[str, str]:
    """Extrae CN y O de un Name X.509 (SEQUENCE OF SET OF SEQUENCE {OID, valor})."""
    oids = {b"\x55\x04\x03": "CN", b"\x55\x04\x0a": "O"}
    nombre: dict[str, str] = {}
    for _, a, b in _hijos_der(d, ini, fin):
        for _, a2, b2 in _hijos_der(d, a, b):
            partes = _hijos_der(d, a2, b2)
            if len(partes) == 2 and partes[0][0] == 0x06:
                clave = oids.get(d[partes[0][1]:partes[0][2]])
                if clave:
                    etiqueta, va, vb = partes[1]
                    codificacion = "utf-16-be" if etiqueta == 0x1E else "utf-8"
                    nombre[clave] = d[va:vb].decode(codificacion, "replace")
    return nombre


def sujeto_certificado(der: bytes) -> dict[str, str]:
    """Devuelve el CN y la O del sujeto de un certificado X.509 en DER (sin verificarlo)."""
    try:
        _, a, b = _tlv_der(der, 0)                  # Certificate
        _, a, b = _tlv_der(der, a)                  # TBSCertificate
        campos = _hijos_der(der, a, b)
        if campos and campos[0][0] == 0xA0:         # versión opcional
            campos = campos[1:]
        if len(campos) < 5:
            return {}
        _, sa, sb = campos[4]                       # serial, algoritmo, emisor, validez, SUJETO
        return _nombre_der(der, sa, sb)
    except (ErrorFormato, IndexError):
        return {}


def _contenido(nodo: dict):
    for tipo, datos in nodo["contenido"]:
        if tipo == b"cbor":
            valor = decodificar_cbor(datos)
            if valor is not None:
                return valor
        elif tipo == b"json":
            try:
                return json.loads(datos.decode("utf-8", "replace"))
            except ValueError:
                continue
    return None


def _nombre_agente(valor) -> str:
    if isinstance(valor, dict):
        nombre = str(valor.get("name", "")).strip()
        version = str(valor.get("version", "")).strip()
        return f"{nombre} {version}".strip()
    return str(valor or "").strip()


def interpretar_c2pa(almacen: dict) -> dict:
    """Resume un almacén C2PA: herramientas, orígenes digitales, acciones y firmante del manifiesto activo."""
    info: dict = {"manifiestos": len(almacen["hijos"]), "herramientas": [], "origenes": [], "acciones": [], "firmante": ""}
    for indice, manifiesto in enumerate(almacen["hijos"]):
        activo = indice == len(almacen["hijos"]) - 1
        for hijo in manifiesto["hijos"]:
            etiqueta = hijo["etiqueta"]
            if etiqueta.startswith("c2pa.claim"):
                reclamacion = _contenido(hijo)
                if isinstance(reclamacion, dict):
                    generadores = reclamacion.get("claim_generator_info")
                    if isinstance(generadores, dict):
                        generadores = [generadores]
                    for g in generadores if isinstance(generadores, list) else []:
                        nombre = _nombre_agente(g)
                        if nombre and nombre not in info["herramientas"]:
                            info["herramientas"].append(nombre)
                    generador = reclamacion.get("claim_generator")
                    if isinstance(generador, str) and generador and generador not in info["herramientas"]:
                        info["herramientas"].append(generador)
            elif etiqueta == "c2pa.assertions":
                for asercion in hijo["hijos"]:
                    nombre = re.sub(r"__\d+$", "", asercion["etiqueta"])
                    datos = _contenido(asercion)
                    if nombre.startswith("c2pa.actions") and isinstance(datos, dict):
                        for accion in datos.get("actions", []) if isinstance(datos.get("actions"), list) else []:
                            if not isinstance(accion, dict):
                                continue
                            info["acciones"].append(str(accion.get("action", "")))
                            for m in RE_ORIGEN_DIGITAL.finditer(str(accion.get("digitalSourceType", ""))):
                                info["origenes"].append(m.group(1))
                            agente = _nombre_agente(accion.get("softwareAgent"))
                            if agente and agente not in info["herramientas"]:
                                info["herramientas"].append(agente)
                    elif nombre.startswith("stds.iptc") and datos is not None:
                        info["origenes"] += [m.group(1) for m in RE_ORIGEN_DIGITAL.finditer(json.dumps(datos, default=str))]
            elif etiqueta == "c2pa.signature" and activo:
                info["firmante"] = firmante_cose(_contenido(hijo))
    return info


def firmante_cose(cose) -> str:
    """Obtiene el sujeto del certificado firmante de un COSE_Sign1 (cabecera x5chain, etiqueta 33)."""
    if not isinstance(cose, list) or len(cose) < 2:
        return ""
    cabeceras = []
    if isinstance(cose[0], bytes):
        protegida = decodificar_cbor(cose[0])
        if isinstance(protegida, dict):
            cabeceras.append(protegida)
    if isinstance(cose[1], dict):
        cabeceras.append(cose[1])
    for cabecera in cabeceras:
        cadena = cabecera.get(33)
        hoja = cadena[0] if isinstance(cadena, list) and cadena else cadena
        if isinstance(hoja, bytes):
            sujeto = sujeto_certificado(hoja)
            partes = [sujeto.get("O", ""), sujeto.get("CN", "")]
            if partes[0] and partes[1] and partes[0] != partes[1]:
                return f"{partes[0]} ({partes[1]})"
            return partes[0] or partes[1]
    return ""


def _textos_exif(d: bytes) -> list[str]:
    """Lee cadenas ASCII de IFD0 y de la subIFD Exif (descripción, marca, modelo, software, autor, comentario)."""
    if len(d) < 8 or d[:2] not in (b"II", b"MM"):
        return []
    orden = "<" if d[:2] == b"II" else ">"
    etiquetas_texto = {0x010E, 0x010F, 0x0110, 0x0131, 0x013B, 0x8298, 0x9286}
    textos: list[str] = []
    pendientes = [struct.unpack(orden + "I", d[4:8])[0]]
    visitados: set[int] = set()
    while pendientes and len(visitados) < 4:
        ifd = pendientes.pop()
        if ifd in visitados or ifd + 2 > len(d):
            continue
        visitados.add(ifd)
        n = struct.unpack(orden + "H", d[ifd:ifd + 2])[0]
        for k in range(min(n, 512)):
            e = ifd + 2 + 12 * k
            if e + 12 > len(d):
                break
            etiqueta, tipo, cuenta = struct.unpack(orden + "HHI", d[e:e + 8])
            if etiqueta == 0x8769:  # puntero a la subIFD Exif
                pendientes.append(struct.unpack(orden + "I", d[e + 8:e + 12])[0])
            elif etiqueta in etiquetas_texto and tipo in (2, 7) and 0 < cuenta < 65536:
                pos = e + 8 if cuenta <= 4 else struct.unpack(orden + "I", d[e + 8:e + 12])[0]
                valor = d[pos:pos + cuenta]
                if etiqueta == 0x9286 and valor[:8] in (b"ASCII\x00\x00\x00", b"UNICODE\x00"):
                    valor = valor[8:]
                textos.append(valor.replace(b"\x00", b" ").decode("utf-8", "replace").strip())
    return [x for x in textos if x]


def _texto_png(tipo: bytes, datos: bytes) -> tuple[str, str] | None:
    """Decodifica un bloque tEXt, zTXt o iTXt de PNG con límite de descompresión."""
    separador = datos.find(b"\x00")
    if separador <= 0:
        return None
    clave = datos[:separador].decode("latin-1", "replace")
    resto = datos[separador + 1:]
    try:
        if tipo == b"tEXt":
            return clave, resto.decode("latin-1", "replace")
        if tipo == b"zTXt":
            return clave, zlib.decompressobj().decompress(resto[1:], MAX_TEXTO_COMPRIMIDO).decode("latin-1", "replace")
        if tipo == b"iTXt" and len(resto) >= 2:
            comprimido, cuerpo = resto[0], resto[2:]
            cuerpo = cuerpo.split(b"\x00", 2)[-1] if cuerpo.count(b"\x00") >= 2 else cuerpo
            if comprimido:
                cuerpo = zlib.decompressobj().decompress(cuerpo, MAX_TEXTO_COMPRIMIDO)
            return clave, cuerpo.decode("utf-8", "replace")
    except zlib.error:
        return None
    return None


def extraer_metadatos(d: bytes) -> dict:
    """Separa por formato los bloques JUMBF, EXIF, XMP y textos de una imagen."""
    meta: dict = {"jumbf": [], "exif": [], "xmp": [], "textos": {}, "formato": "?"}
    if d[:3] == b"\xff\xd8\xff":
        meta["formato"] = "JPEG"
        app11: dict[bytes, bytearray] = {}
        i = 2
        while i + 4 <= len(d) and d[i] == 0xFF:
            marcador = d[i + 1]
            if marcador in (0xD8, 0x01) or 0xD0 <= marcador <= 0xD7:
                i += 2
                continue
            if marcador in (0xD9, 0xDA):
                break
            largo = struct.unpack(">H", d[i + 2:i + 4])[0]
            if largo < 2:
                break
            segmento = d[i + 4:i + 2 + largo]
            if marcador == 0xEB and segmento[:2] == b"JP" and len(segmento) >= 16:
                instancia = segmento[2:4]
                if instancia not in app11:
                    app11[instancia] = bytearray(segmento[8:])
                else:  # continuación: se salta la cabecera LBox/TBox repetida
                    cabecera = 16 if struct.unpack(">I", segmento[8:12])[0] == 1 else 8
                    app11[instancia] += segmento[8 + cabecera:]
            elif marcador == 0xE1 and segmento.startswith(b"Exif\x00\x00"):
                meta["exif"].append(segmento[6:])
            elif marcador == 0xE1 and segmento.startswith(b"http://ns.adobe.com/xap/1.0/\x00"):
                meta["xmp"].append(segmento[29:].decode("utf-8", "replace"))
            elif marcador == 0xFE:
                meta["textos"]["Comment"] = segmento.decode("utf-8", "replace")
            i += 2 + largo
        meta["jumbf"] += [bytes(v) for v in app11.values()]
    elif d[:8] == b"\x89PNG\r\n\x1a\n":
        meta["formato"] = "PNG"
        i = 8
        while i + 12 <= len(d):
            largo = struct.unpack(">I", d[i:i + 4])[0]
            tipo = d[i + 4:i + 8]
            datos = d[i + 8:i + 8 + largo]
            if tipo == b"caBX":
                meta["jumbf"].append(datos)
            elif tipo == b"eXIf":
                meta["exif"].append(datos)
            elif tipo in (b"tEXt", b"zTXt", b"iTXt"):
                par = _texto_png(tipo, datos)
                if par:
                    if par[0] == "XML:com.adobe.xmp":
                        meta["xmp"].append(par[1])
                    else:
                        meta["textos"][par[0]] = par[1]
            elif tipo == b"IEND":
                break
            i += 12 + largo
    elif d[:4] == b"RIFF" and d[8:12] == b"WEBP":
        meta["formato"] = "WebP"
        i = 12
        while i + 8 <= len(d):
            tipo = d[i:i + 4]
            largo = struct.unpack("<I", d[i + 4:i + 8])[0]
            datos = d[i + 8:i + 8 + largo]
            if tipo == b"C2PA":
                meta["jumbf"].append(datos)
            elif tipo == b"XMP ":
                meta["xmp"].append(datos.decode("utf-8", "replace"))
            elif tipo == b"EXIF":
                meta["exif"].append(datos[6:] if datos.startswith(b"Exif\x00\x00") else datos)
            i += 8 + largo + (largo & 1)
    if not meta["xmp"]:  # otros formatos: paquetes XMP en claro
        for m in re.finditer(rb"<x:xmpmeta[\s\S]{0,1000000}?</x:xmpmeta>", d[:8_000_000]):
            meta["xmp"].append(m.group(0).decode("utf-8", "replace"))
            if len(meta["xmp"]) >= 3:
                break
    return meta


def validar_con_c2patool(ruta: Path) -> str | None:
    """Valida firma y cadena de confianza con c2patool si está instalado. Devuelve Trusted, Valid, Invalid o None."""
    ejecutable = shutil.which("c2patool")
    if not ejecutable:
        return None
    try:
        r = subprocess.run(  # nosec B603
            [ejecutable, str(ruta.resolve())], capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60, check=False)
        datos = json.loads(r.stdout) if r.stdout.strip().startswith("{") else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    if not isinstance(datos, dict):
        return None
    estado = datos.get("validation_state")
    if isinstance(estado, str) and estado:
        return estado
    codigos = [str(s.get("code", "")) for s in datos.get("validation_status", []) if isinstance(s, dict)]
    graves = [c for c in codigos if c != "signingCredential.untrusted"]
    if any(re.search(r"mismatch|invalid|revoked|expired|missing|malformed", c, I) for c in graves):
        return "Invalid"
    return "Valid" if "signingCredential.untrusted" in codigos else "Trusted"


def texto_origen(codigo: str) -> str:
    traducido = t(f"origen.{codigo}")
    return codigo if traducido == f"origen.{codigo}" else traducido


def analizar_imagen(res: Resultado, d: bytes, ubic: str, ruta_validacion: Path | None, avisos: set[str]) -> None:
    meta = extraer_metadatos(d)
    res.ficheros_analizados += 1
    if not (meta["jumbf"] or meta["exif"] or meta["xmp"] or meta["textos"]):
        res.imagenes_sin_metadatos += 1
        res.notas.append(t("nota.sin_metadatos", u=ubic, f=meta["formato"]))
        if meta["formato"] in ("JPEG", "PNG", "WebP"):
            return

    # 1. C2PA
    almacen = None
    for bloque in meta["jumbf"]:
        almacen = buscar_almacen_c2pa(bloque)
        if almacen:
            break
    if almacen is None and not meta["jumbf"] and meta["formato"] not in ("JPEG", "PNG", "WebP"):
        almacen = buscar_c2pa_suelto(d)
    if almacen:
        info = interpretar_c2pa(almacen)
        estado = validar_con_c2patool(ruta_validacion) if ruta_validacion else None
        if estado is None:
            if "c2patool" not in avisos:
                avisos.add("c2patool")
                res.notas.append(t("nota.c2patool_no"))
            texto_firma = t("firma.no_verificada")
        else:
            texto_firma = {"Trusted": t("firma.confianza"), "Valid": t("firma.valida")}.get(estado, t("firma.invalida"))
        origenes = list(dict.fromkeys(info["origenes"]))
        detalle = t("ev.c2pa", o=", ".join(texto_origen(o) for o in origenes) or t("ev.desconocido"),
                    h=", ".join(info["herramientas"][:3]) or t("ev.desconocido"),
                    f=info["firmante"] or t("ev.desconocido"), s=texto_firma)
        herramienta_ia = any(RE_GENERADOR_META.search(h) for h in info["herramientas"])
        if any(o in ORIGENES_IA for o in origenes):
            res.anadir("c2pa-ia", "explicito", f"{ubic}:C2PA", detalle)
        elif any(o in ORIGENES_EDICION_IA for o in origenes):
            res.anadir("c2pa-edicion-ia", "explicito", f"{ubic}:C2PA", detalle)
        elif herramienta_ia:
            res.anadir("c2pa-herramienta-ia", "explicito", f"{ubic}:C2PA", detalle)
        else:
            res.notas.append(t("nota.c2pa_sin_ia", u=ubic, d=detalle))

    # 2. XMP: IPTC DigitalSourceType y herramienta creadora
    for xmp in meta["xmp"]:
        origenes = [m.group(1) for m in RE_ORIGEN_DIGITAL.finditer(xmp)]
        ia = [o for o in origenes if o in ORIGENES_IA | ORIGENES_EDICION_IA]
        if ia and not almacen:
            res.anadir("xmp-origen-ia", "explicito", f"{ubic}:XMP", f"DigitalSourceType = {ia[0]} ({texto_origen(ia[0])})")
        m = RE_GENERADOR_META.search(xmp)
        if m:
            inicio = max(0, m.start() - 60)
            res.anadir("metadatos-generador", "fuerte", f"{ubic}:XMP", re.sub(r"<[^>]{0,200}>", " ", xmp[inicio:m.end() + 60]))
            break

    # 3. Textos PNG: parámetros de Stable Diffusion (A1111/Forge), ComfyUI, InvokeAI, NovelAI
    textos = meta["textos"]
    for clave in ("parameters", "prompt", "workflow", "Dream", "sd-metadata", "invokeai_metadata", "invokeai_graph"):
        valor = textos.get(clave, "")
        if not valor:
            continue
        parece_sd = clave == "parameters" and re.search(r"Steps:\s*\d+.*Sampler:", valor, re.DOTALL)
        parece_comfy = clave in ("prompt", "workflow") and re.search(r'"class_type"|"nodes"\s*:', valor)
        if parece_sd or parece_comfy or clave in ("Dream", "sd-metadata", "invokeai_metadata", "invokeai_graph"):
            res.anadir("parametros-generacion", "explicito", f"{ubic}:{meta['formato']} «{clave}»", valor[:150])
            break
    candidatos = [f"{k}: {v}" for k, v in textos.items() if k not in ("parameters", "prompt", "workflow")]
    for bloque in meta["exif"]:
        candidatos += _textos_exif(bloque)
    for texto in candidatos:
        m = RE_GENERADOR_META.search(texto)
        if m:
            res.anadir("metadatos-generador", "fuerte", f"{ubic}:EXIF/{meta['formato']}", texto[:150])
            break


def analizar_fichero_imagen(res: Resultado, ruta: Path, ubic: str, avisos: set[str]) -> None:
    try:
        if ruta.stat().st_size > MAX_TAMANO_IMAGEN:
            res.notas.append(t("nota.imagen_grande", u=ubic))
            return
        datos = ruta.read_bytes()
    except OSError:
        return
    analizar_imagen(res, datos, ubic, ruta, avisos)


# ---------------------------------------------------------------------------
# Análisis de HTML / web
# ---------------------------------------------------------------------------


class ExtractorTexto(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.partes: list[str] = []
        self._ignorar = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self._ignorar += 1
        elif tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "tr"}:
            self.partes.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg", "template"} and self._ignorar:
            self._ignorar -= 1

    def handle_data(self, data):
        if not self._ignorar:
            self.partes.append(data)

    def texto(self) -> str:
        t_ = "".join(self.partes)
        t_ = re.sub(r"[ \t]+", " ", t_)
        return re.sub(r"\n\s*\n+", "\n", t_).strip()


def detectar_rafagas(res: Resultado, crudo: str, ubic: str) -> None:
    marcas = sorted({x for x in (parsear_fecha(v) for v in RE_TIMESTAMP.findall(crudo)) if x is not None})
    if len(marcas) < 10:
        return
    rafagas = []
    inicio = 0
    for i in range(1, len(marcas) + 1):
        if i == len(marcas) or marcas[i] - marcas[i - 1] > 5:
            if i - inicio >= 10:
                rafagas.append(marcas[inicio:i])
            inicio = i
    for r in rafagas:
        huecos = [b - a for a, b in zip(r, r[1:])]
        desde = datetime.fromtimestamp(r[0], tz=timezone.utc).astimezone().isoformat(sep=" ", timespec="seconds")
        hasta = datetime.fromtimestamp(r[-1], tz=timezone.utc).astimezone().strftime("%H:%M:%S")
        res.anadir("rafaga-datos", "medio", f"{ubic}:{t('ub.datos')}",
                   t("ev.rafaga", n=len(r), a=desde, b=hasta, s=f"{statistics.median(huecos):.1f}"))


def analizar_coordenadas(res: Resultado, crudo: str, ubic: str) -> None:
    valores = RE_LATITUD.findall(crudo)
    if len(valores) < 20:
        return
    decimales = [len(v.split(".")[1]) if "." in v else 0 for v in valores]
    bajos = sum(1 for d in decimales if d <= 6)
    altos = sum(1 for d in decimales if d >= 7)
    redondos = sum(1 for d in decimales if d <= 2)
    if bajos / len(valores) >= 0.15 and altos / len(valores) >= 0.15:
        res.anadir("coordenadas-mixtas", "debil", f"{ubic}:{t('ub.datos')}",
                   t("ev.coordenadas", b=bajos, a=altos, r=redondos, n=len(valores)))


def urls_imagenes(crudo: str) -> list[str]:
    vistas: list[str] = []
    for m in RE_IMG_HTML.finditer(crudo):
        url = html.unescape(m.group(1) or m.group(2) or "").strip()
        if url and not url.startswith("data:") and url not in vistas:
            vistas.append(url)
    return vistas


def analizar_html(res: Resultado, crudo: str, ubic: str) -> None:
    aplicar_reglas(res, crudo, REGLAS_GENERALES, ubic)
    aplicar_reglas(res, crudo, REGLAS_HTML, ubic, max_por_regla=3)

    gen = RE_META_GENERATOR.search(crudo)
    if gen:
        res.notas.append(t("nota.generator", u=ubic, g=gen.group(1)))

    coincidencias_stack = sum(1 for p in RE_STACK_GENERADOR if p.search(crudo))
    if coincidencias_stack >= 2:
        res.anadir("stack-generador", "debil", ubic, t("ev.stack", n=coincidencias_stack))

    detectar_rafagas(res, crudo, ubic)
    analizar_coordenadas(res, crudo, ubic)

    extractor = ExtractorTexto()
    try:
        extractor.feed(crudo)
        visible = extractor.texto()
    except Exception:  # noqa: BLE001 - HTML malformado: seguimos sin texto visible
        visible = ""
    if visible:
        aplicar_reglas(res, visible, [*REGLAS_CHAT, REGLA_HUECO], t("ub.visible", u=ubic), max_por_regla=3)
        analizar_estilo(res, visible, t("ub.visible", u=ubic))


def analizar_imagenes_locales(res: Resultado, crudo: str, html_ruta: Path, avisos: set[str]) -> None:
    """Analiza las imágenes de una página guardada, solo si están dentro de su carpeta (sin salir con ../)."""
    base = html_ruta.parent.resolve()
    analizadas = 0
    for url in urls_imagenes(crudo):
        if analizadas >= MAX_IMAGENES_WEB * 2:
            break
        if re.match(r"[a-z][a-z0-9+.-]*:", url, I):
            continue  # URL absoluta: no se descarga al analizar un fichero local
        ruta = (base / urllib.parse.unquote(url.split("?")[0].split("#")[0])).resolve()
        try:
            ruta.relative_to(base)
        except ValueError:
            continue
        if ruta.is_file() and not ruta.is_symlink():
            analizar_fichero_imagen(res, ruta, str(ruta.relative_to(base)), avisos)
            analizadas += 1


class _RedireccionSegura(urllib.request.HTTPRedirectHandler):
    """Solo sigue redirecciones a http/https (evita file://, ftp://...)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not re.match(r"https?://", newurl, I):
            raise urllib.error.URLError(t("nota.redireccion", u=newurl[:80]))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_ABRIDOR = urllib.request.build_opener(_RedireccionSegura)


def descargar_bytes(url: str, maximo: int, timeout: int = 20) -> tuple[bytes | None, str, str]:
    """Descarga hasta `maximo` bytes. Devuelve (datos, url_final, error); solo http(s)."""
    if not re.match(r"https?://", url, I):
        return None, url, t("nota.solo_http")
    cabeceras = {"User-Agent": f"aimarkers/{VERSION} (+https://github.com/z115666/aimarkers)"}
    peticion = urllib.request.Request(url, headers=cabeceras)  # noqa: S310 - esquema http(s) validado arriba
    try:
        with _ABRIDOR.open(peticion, timeout=timeout) as r:  # nosec B310
            return r.read(maximo + 1), r.geturl(), ""
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        return None, url, str(e)


def descargar(url: str, timeout: int = 20) -> tuple[str | None, str, str]:
    datos, final, error = descargar_bytes(url, MAX_TAMANO_FICHERO, timeout)
    if datos is None:
        return None, final, error
    return datos[:MAX_TAMANO_FICHERO].decode("utf-8", errors="replace"), final, ""


def analizar_imagenes_remotas(res: Resultado, urls: list[str], avisos: set[str], limite: int = MAX_IMAGENES_WEB,
                              carpeta: Path | None = None, progreso=None, retardo: float = 0.0) -> None:
    """Descarga y analiza imágenes de una web. limite=0: todas. Se guardan en una carpeta temporal que se borra."""
    if limite and len(urls) > limite:
        res.notas.append(t("nota.imagenes_limite", n=limite))
        urls = urls[:limite]
    analizadas = 0
    with tempfile.TemporaryDirectory(prefix="aimarkers-img-", dir=carpeta) as temporal_dir:
        for indice, url in enumerate(urls):
            informar("imagenes", indice, len(urls), url)
            if retardo and indice:
                time.sleep(retardo / 2)
            datos, _, _ = descargar_bytes(url, MAX_IMAGEN_WEB, timeout=15)
            if not datos or len(datos) > MAX_IMAGEN_WEB:
                continue
            temporal = Path(temporal_dir) / f"imagen{indice}"
            temporal.write_bytes(datos)
            analizar_imagen(res, datos, url[:120], temporal, avisos)
            analizadas += 1
            temporal.unlink(missing_ok=True)
    if analizadas:
        res.notas.append(t("nota.imagenes_web", n=analizadas))


# ---------------------------------------------------------------------------
# Análisis de repositorios Git
# ---------------------------------------------------------------------------


def git(repo: Path, *args: str) -> str:
    try:
        # Configuración defensiva: un repositorio analizado puede ser hostil (.git/config manipulado)
        seguro = ["-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "diff.external=",
                  "-c", "core.pager=cat", "-c", "safe.directory=*"]
        entorno = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0", GIT_PAGER="cat")
        r = subprocess.run(  # nosec B603 B607
            ["git", *seguro, "-C", str(repo), *args], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120, env=entorno, check=False)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def analizar_git(res: Resultado, repo: Path, max_commits: int = 3000) -> None:
    log = git(repo, "log", "--all", f"-n{max_commits}", "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%at%x1f%B%x1e")
    if not log:
        res.notas.append(t("nota.git_vacio"))
        return
    commits = []
    for bloque in log.split("\x1e"):
        partes = bloque.strip("\n").split("\x1f")
        if len(partes) == 7:
            commits.append(partes)
    res.notas.append(t("nota.git_commits", n=len(commits)))

    contadores: dict[str, int] = {}
    for h, an, ae, cn, ce, _fecha, cuerpo in commits:
        corto = h[:8]
        quien = f"{an} <{ae}> / {cn} <{ce}>"
        if RE_BOT_AUTOR.search(quien):
            contadores["bot"] = contadores.get("bot", 0) + 1
            if contadores["bot"] <= 5:
                res.anadir("autor-bot", "explicito", f"commit {corto}", quien)
        for linea in cuerpo.splitlines():
            if re.match(r"\s*Co-?authored-?by:", linea, I) and RE_COAUTOR.search(linea):
                contadores["coautor"] = contadores.get("coautor", 0) + 1
                if contadores["coautor"] <= 5:
                    res.anadir("coautor-ia", "explicito", f"commit {corto}", linea)
            elif any(p.search(linea) for p in RE_FIRMAS_COMMIT):
                contadores["pie"] = contadores.get("pie", 0) + 1
                if contadores["pie"] <= 5:
                    res.anadir("firma-robot", "explicito", f"commit {corto}", linea)
    for clave, total in contadores.items():
        if total > 5:
            res.notas.append(t("nota.git_mas", n=total, c=clave))

    ramas = git(repo, "branch", "-a", "--format=%(refname:short)").splitlines()
    agentes = [r for r in ramas if RE_RAMA_AGENTE.match(r.strip())]
    for r in agentes[:5]:
        res.anadir("rama-agente", "fuerte", t("ub.ramas"), r.strip())

    # Commits muy grandes
    numstat = git(repo, "log", "--all", f"-n{max_commits}", "--no-merges", "--no-ext-diff", "--no-textconv",
                  "--format=@@%h", "--numstat")
    grandes, actual, suma = [], None, 0
    for linea in [*numstat.splitlines(), "@@fin"]:
        if linea.startswith("@@"):
            if actual and suma > 1000:
                grandes.append((actual, suma))
            actual, suma = linea[2:], 0
        else:
            partes = linea.split("\t")
            if len(partes) == 3 and partes[0].isdigit():
                suma += int(partes[0])
    if len(grandes) >= 3:
        mayor = max(grandes, key=lambda x: x[1])
        res.anadir("commits-grandes", "medio", t("ub.historial"), t("ev.commits_grandes", n=len(grandes), h=mayor[0], l=mayor[1]))

    # Mensajes uniformes
    if len(commits) >= 20:
        conv = sum(1 for c in commits if RE_CONVENTIONAL.match(c[6]))
        con_vinetas = sum(1 for c in commits if len(re.findall(r"^\s*[-*] ", c[6], M)) >= 3)
        if conv / len(commits) >= 0.9 and con_vinetas / len(commits) >= 0.5:
            res.anadir("mensajes-uniformes", "debil", t("ub.historial"),
                       t("ev.mensajes", a=conv, b=len(commits), c=con_vinetas))


# ---------------------------------------------------------------------------
# Recorrido de ficheros y orquestación
# ---------------------------------------------------------------------------


def comprobar_ficheros_agente(res: Resultado, raiz: Path, rutas: Iterable[Path]) -> None:
    vistos = set()
    for ruta in rutas:
        rel = ruta.relative_to(raiz) if ruta != raiz else ruta
        nombre = ruta.name
        herramienta = FICHEROS_AGENTE.get(nombre)
        if nombre == "copilot-instructions.md" and ruta.parent.name != ".github":
            herramienta = None
        if herramienta and str(rel) not in vistos:
            vistos.add(str(rel))
            res.anadir("fichero-agente", "fuerte", str(rel), f"{nombre} → {herramienta}")


def analizar_fichero(res: Resultado, ruta: Path, ubic: str, avisos: set[str]) -> None:
    ext = ruta.suffix.lower()
    if ext in EXT_IMAGEN:
        analizar_fichero_imagen(res, ruta, ubic, avisos)
        return
    texto = leer_fichero(ruta)
    if texto is None:
        return
    if "aimarkers: ignore-file" in texto[:2000]:
        res.notas.append(t("nota.ignorado", u=ubic))
        return
    res.ficheros_analizados += 1
    if ext in EXT_HTML:
        analizar_html(res, texto, ubic)
    elif ext in EXT_TEXTO:
        analizar_texto(res, texto, ubic)
    elif ext in EXT_CODIGO:
        if ext in {".js", ".css", ".json"} and es_minificado(texto):
            res.ficheros_analizados -= 1
            return
        analizar_codigo(res, texto, ubic, ext)
    else:
        res.ficheros_analizados -= 1


def analizar_directorio(res: Resultado, raiz: Path, avisos: set[str]) -> list[Path]:
    rutas: list[Path] = []
    for actual, dirs, ficheros in os.walk(raiz):
        base = Path(actual)
        for d in list(dirs):
            if d in DIRS_AGENTE:
                res.anadir("carpeta-agente", "fuerte", str((base / d).relative_to(raiz)), f"{d}/ → {DIRS_AGENTE[d]}")
        dirs[:] = [d for d in dirs if d not in DIRS_IGNORADOS and d not in DIRS_AGENTE]
        rutas += [base / f for f in ficheros if not (base / f).is_symlink()]
    if res.solo_seguridad:
        return rutas
    comprobar_ficheros_agente(res, raiz, rutas)
    for indice, ruta in enumerate(rutas):
        if indice % 10 == 0:
            informar("ficheros", indice, len(rutas), str(ruta.relative_to(raiz)))
        analizar_fichero(res, ruta, str(ruta.relative_to(raiz)), avisos)
    if (raiz / ".git").exists():
        res.tipo = "repo"
        informar("git", 0, 1)
        analizar_git(res, raiz)
    return rutas


def _ubicacion_web(url: str, inicio: str) -> str:
    partes = urllib.parse.urlsplit(url)
    if not inicio or urllib.parse.urlsplit(inicio).netloc.lower().removeprefix("www.") == partes.netloc.lower().removeprefix("www."):
        return (partes.path or "/") + (f"?{partes.query}" if partes.query else "")
    return url


def analizar_web_objetivo(objetivo: str, opciones) -> Resultado:
    import aimarkers_web as web
    avisos: set[str] = set()
    res = Resultado(objetivo, "url")
    res.solo_seguridad = getattr(opciones, "solo_seguridad", False)
    with web.Rastreo(objetivo, opciones) as rastreo:
        rastreo.ejecutar()
        if not rastreo.paginas:
            res.notas.append(t("nota.no_descarga", e=rastreo.error))
            return res
        res.notas.extend(rastreo.notas)
        if rastreo.paginas[0].estado >= 400:
            res.notas.insert(0, t("nota.estado_http", n=rastreo.paginas[0].estado))
        if opciones.rastrear:
            res.notas.append(t("nota.paginas_rastreadas", n=len(rastreo.paginas)))
            if not opciones.ignorar_robots:
                res.notas.append(t("nota.robots"))
        if not res.solo_seguridad:
            for indice, pagina in enumerate(rastreo.paginas):
                informar("ia", indice, len(rastreo.paginas), pagina.url)
                if pagina.es_html:
                    res.ficheros_analizados += 1
                    analizar_html(res, pagina.texto(), _ubicacion_web(pagina.url, objetivo) if opciones.rastrear else t("ub.pagina"))
            if opciones.imagenes:
                limite = opciones.max_imagenes if opciones.max_imagenes is not None else (0 if opciones.rastrear else MAX_IMAGENES_WEB)
                analizar_imagenes_remotas(res, rastreo.urls_imagenes(), avisos, limite, rastreo.carpeta,
                                          opciones.progreso, opciones.retardo if opciones.rastrear else 0.0)
            m = re.match(r"(https?://[^/]+)", rastreo.paginas[0].url, I)
            if m:
                llms, _, _ = descargar(m.group(1) + "/llms.txt", timeout=10)
                if llms and not llms.lstrip().lower().startswith(("<!doctype", "<html")):
                    res.anadir("llms-txt", "debil", "/llms.txt", llms[:120])
        if opciones.seguridad:
            import aimarkers_seguridad
            res.seguridad = aimarkers_seguridad.analizar_web(rastreo, opciones)
            if res.solo_seguridad:
                res.ficheros_analizados = sum(1 for p in rastreo.paginas if p.es_html)
    return res


def analizar_objetivo(objetivo: str, imagenes_web: bool = True, opciones=None) -> Resultado:
    import aimarkers_web as web
    if opciones is None:
        opciones = web.Opciones(imagenes=imagenes_web)
    fijar_avance(opciones.progreso)
    avisos: set[str] = set()
    if re.match(r"https?://", objetivo, I):
        return analizar_web_objetivo(objetivo, opciones)

    solo = getattr(opciones, "solo_seguridad", False)
    ruta = Path(objetivo)
    if ruta.is_dir():
        res = Resultado(str(ruta.resolve()), "dir")
        res.solo_seguridad = solo
        rutas = analizar_directorio(res, ruta, avisos)
        if opciones.seguridad:
            import aimarkers_seguridad
            res.seguridad = aimarkers_seguridad.analizar_ficheros(rutas, ruta)
            if solo:
                res.ficheros_analizados = len(rutas)
        return res
    if ruta.is_file():
        ext = ruta.suffix.lower()
        tipo = ("html" if ext in EXT_HTML else "texto" if ext in EXT_TEXTO else "codigo" if ext in EXT_CODIGO
                else "imagen" if ext in EXT_IMAGEN else "fichero")
        res = Resultado(str(ruta), tipo)
        res.solo_seguridad = solo
        if not solo:
            comprobar_ficheros_agente(res, ruta.parent, [ruta])
            analizar_fichero(res, ruta, ruta.name, avisos)
            if tipo == "html" and opciones.imagenes:
                crudo = leer_fichero(ruta)
                if crudo:
                    analizar_imagenes_locales(res, crudo, ruta, avisos)
        if opciones.seguridad:
            import aimarkers_seguridad
            res.seguridad = aimarkers_seguridad.analizar_ficheros([ruta], ruta.parent)
            if solo:
                res.ficheros_analizados = 1
        if res.ficheros_analizados == 0 and not res.notas and not solo:
            res.notas.append(t("nota.no_reconocido"))
        return res

    res = Resultado(objetivo, "desconocido")
    res.notas.append(t("nota.no_existe"))
    return res


# ---------------------------------------------------------------------------
# Informes
# ---------------------------------------------------------------------------

COLORES = {"explicito": "\033[1;31m", "fuerte": "\033[31m", "medio": "\033[33m", "debil": "\033[36m"}
RESET = "\033[0m"


def _fecha_actual() -> str:
    return datetime.now(timezone.utc).astimezone().strftime(t("ui.formato_fecha"))


def _seccion_seguridad_consola(res: Resultado, color: bool, max_ev: int) -> list[str]:
    if res.seguridad is None:
        return []
    import aimarkers_seguridad
    lineas = aimarkers_seguridad.informe_consola(res.seguridad.a_dict(), color, max_ev)
    if res.solo_seguridad and res.notas:
        lineas += [f"  - {n}" for n in res.notas[:15]]
    return lineas


def informe_consola(resultados: list[Resultado], max_ev: int, color: bool) -> str:
    c = (lambda nivel, texto: f"{COLORES[nivel]}{texto}{RESET}") if color else (lambda nivel, texto: texto)
    salida = []
    for res in resultados:
        salida.append("=" * 78)
        salida.append(f"{t('ui.objetivo')}: {res.objetivo}")
        salida.append(f"{t('ui.tipo')}: {t('tipo.' + res.tipo)}   ·   {t_ficheros(res.ficheros_analizados)}")
        if res.solo_seguridad:
            salida += _seccion_seguridad_consola(res, color, max_ev)
            continue
        salida.append(f"{t('ui.puntuacion')}: {res.puntuacion()}/100  →  {res.banda()}")
        if res.atribucion_explicita():
            salida.append(c("explicito", t("ui.explicita")))
        grupos = res.por_regla()
        for nivel in ORDEN_NIVEL:
            reglas = [v for v in grupos.values() if v[0].nivel == nivel]
            if not reglas:
                continue
            salida.append("")
            salida.append(c(nivel, f"[{t('nivel.' + nivel)} · {PESOS[nivel]} pts]"))
            for lista in reglas:
                extra = ""
                if res.ficheros_analizados >= 10 and nivel in ("medio", "debil") and lista[0].regla not in SIN_PREVALENCIA:
                    extra = ", " + t("ui.prevalencia", p=f"{res.prevalencia(lista):.1%}")
                salida.append(f"  • {lista[0].descripcion} ({len(lista)}{extra}) → +{res.contribucion(lista):.1f}")
                salida.extend(f"      {h.ubicacion}  {h.extracto}" for h in lista[:max_ev])
                if len(lista) > max_ev:
                    salida.append("      " + t("ui.mas", n=len(lista) - max_ev))
        if not res.hallazgos:
            salida.append("\n" + t("ui.ninguno"))
        if res.notas:
            salida.append(f"\n{t('ui.notas')}:")
            salida += [f"  - {n}" for n in res.notas[:15]]
            if len(res.notas) > 15:
                salida.append("  - " + t("ui.notas_mas", n=len(res.notas) - 15))
        salida += _seccion_seguridad_consola(res, color, max_ev)
    salida.append("=" * 78)
    salida.append(t("ui.aviso"))
    return "\n".join(salida)


def informe_markdown(resultados: list[Resultado], max_ev: int) -> str:
    md = [f"# {t('ui.titulo')}", "", t("ui.generado", v=VERSION, fecha=_fecha_actual()), "", f"> {t('ui.aviso')}", ""]
    for res in resultados:
        md += [f"## {res.objetivo}", "",
               f"- **{t('ui.md_tipo')}:** {t('tipo.' + res.tipo)}",
               f"- **{t('ui.md_ficheros')}:** {res.ficheros_analizados}"]
        if res.solo_seguridad:
            md.append("")
            md += _seccion_seguridad_md(res)
            continue
        md += [f"- **{t('ui.md_puntuacion')}:** {res.puntuacion()}/100 — {res.banda()}",
               f"- **{t('ui.md_explicita')}:** {t('ui.si') if res.atribucion_explicita() else t('ui.no')}", ""]
        if res.hallazgos:
            md += [f"| {t('ui.col_nivel')} | {t('ui.col_marcador')} | {t('ui.col_veces')} | {t('ui.col_ubicacion')} | "
                   f"{t('ui.col_evidencia')} |", "| --- | --- | --- | --- | --- |"]
            for nivel in ORDEN_NIVEL:
                for lista in res.por_regla().values():
                    if lista[0].nivel != nivel:
                        continue
                    for i, h in enumerate(lista[:max_ev]):
                        ev = html.escape(h.extracto).replace("|", "\\|")
                        md.append(f"| {t('nivel.' + nivel) if i == 0 else ''} | {h.descripcion if i == 0 else ''} | "
                                  f"{len(lista) if i == 0 else ''} | `{h.ubicacion}` | {ev} |")
            md.append("")
        else:
            md += [t("ui.ninguno"), ""]
        if res.notas:
            md += [f"**{t('ui.notas')}**", ""] + [f"- {html.escape(n)}" for n in res.notas] + [""]
        md += _seccion_seguridad_md(res)
    return "\n".join(md)


def _seccion_seguridad_md(res: Resultado) -> list[str]:
    if res.seguridad is None:
        return []
    import aimarkers_seguridad
    return aimarkers_seguridad.informe_markdown(res.seguridad.a_dict())


def informe_html(resultados: list[Resultado], max_ev: int) -> str:
    e = html.escape
    bloques = []
    for res in resultados:
        p = res.puntuacion()
        clase = "alta" if p >= 70 else "media" if p >= 40 else "baja" if p >= 15 else "nula"
        filas = []
        for nivel in ORDEN_NIVEL:
            for lista in res.por_regla().values():
                if lista[0].nivel != nivel:
                    continue
                evid = "".join(f"<li><code>{e(h.ubicacion)}</code> {e(h.extracto)}</li>" for h in lista[:max_ev])
                if len(lista) > max_ev:
                    evid += f"<li class='mas'>{e(t('ui.mas', n=len(lista) - max_ev))}</li>"
                filas.append(f"<tr><td><span class='nivel {nivel}'>{e(t('nivel.' + nivel))}</span></td>"
                             f"<td>{e(lista[0].descripcion)}</td><td class='num'>{len(lista)}</td><td><ul>{evid}</ul></td></tr>")
        tabla = (f"<table><thead><tr><th>{e(t('ui.col_nivel'))}</th><th>{e(t('ui.col_marcador'))}</th>"
                 f"<th>{e(t('ui.col_veces'))}</th><th>{e(t('ui.col_evidencias'))}</th></tr></thead>"
                 f"<tbody>{''.join(filas)}</tbody></table>") if filas else f"<p>{e(t('ui.ninguno'))}</p>"
        notas = (f"<details><summary>{e(t('ui.notas'))}</summary><ul>" + "".join(f"<li>{e(n)}</li>" for n in res.notas)
                 + "</ul></details>") if res.notas else ""
        explicita = f"<p class='explicita'>{e(t('ui.explicita'))}</p>" if res.atribucion_explicita() else ""
        seguridad = ""
        if res.seguridad is not None:
            import aimarkers_seguridad
            seguridad = aimarkers_seguridad.informe_html(res.seguridad.a_dict())
        if res.solo_seguridad:
            bloques.append(f"<section><div class='cabecera'><div><h2>{e(res.objetivo)}</h2><p class='meta'>"
                           f"{e(t('tipo.' + res.tipo))} · {e(t_ficheros(res.ficheros_analizados))}</p></div></div>{seguridad}{notas}</section>")
            continue
        bloques.append(f"""
<section>
  <div class="cabecera">
    <div class="marcador {clase}"><span>{p}</span><small>/100</small></div>
    <div><h2>{e(res.objetivo)}</h2>
      <p class="meta">{e(t('tipo.' + res.tipo))} · {e(t_ficheros(res.ficheros_analizados))}</p>
      <p class="banda">{e(res.banda())}</p></div>
  </div>
  {explicita}{tabla}{notas}{seguridad}
</section>""")
    veces = t("ui.col_veces").replace('"', "")
    css_seguridad = ""
    if any(r.seguridad is not None for r in resultados):
        import aimarkers_seguridad
        css_seguridad = aimarkers_seguridad.CSS_HTML
    return f"""<!doctype html>
<html lang="{idioma()}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>aimarkers · {e(t('ui.titulo'))}</title>
<style>
:root {{ --bg:#f7f7f5; --card:#fff; --txt:#1d1d1f; --sub:#6b6b70; --borde:#e2e2e0;
  --exp:#b3261e; --fue:#d9480f; --med:#b7791f; --deb:#2b6cb0; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141416; --card:#1e1e21; --txt:#ececee; --sub:#9a9aa0;
  --borde:#2e2e33; --exp:#ff6b62; --fue:#ff8a4c; --med:#f2b84b; --deb:#6aa8ff; }} }}
* {{ box-sizing:border-box }} body {{ margin:0; background:var(--bg); color:var(--txt);
  font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; padding:24px 16px }}
main {{ max-width:1000px; margin:0 auto }} h1 {{ font-size:22px; margin:0 0 4px }}
.aviso {{ color:var(--sub); margin:0 0 24px }}
section {{ background:var(--card); border:1px solid var(--borde); border-radius:12px; padding:20px; margin-bottom:20px }}
.cabecera {{ display:flex; gap:18px; align-items:center; margin-bottom:12px }}
.cabecera h2 {{ font-size:16px; margin:0; word-break:break-all }} .meta {{ color:var(--sub); margin:2px 0 }}
.banda {{ margin:2px 0; font-weight:600 }}
.marcador {{ flex:0 0 92px; width:92px; height:92px; border-radius:50%; display:flex; flex-direction:column;
  align-items:center; justify-content:center; border:6px solid var(--borde); line-height:1 }}
.marcador span {{ font-size:26px; font-weight:700 }} .marcador small {{ color:var(--sub); font-size:11px; margin-top:3px }}
.alta {{ border-color:var(--exp) }} .media {{ border-color:var(--fue) }}
.baja {{ border-color:var(--med) }} .nula {{ border-color:var(--deb) }}
.explicita {{ color:var(--exp); font-weight:600 }}
table {{ width:100%; border-collapse:collapse; font-size:14px }} th,td {{ text-align:left; vertical-align:top;
  padding:8px; border-top:1px solid var(--borde) }} th {{ color:var(--sub); font-weight:600 }}
td ul {{ margin:0; padding-left:16px }} code {{ font-size:12px; color:var(--sub); word-break:break-all }} .num {{ text-align:right }}
td {{ overflow-wrap:anywhere }} section {{ overflow:hidden }} a {{ color:var(--deb) }} a:visited {{ color:var(--deb) }}
.nivel {{ font-size:12px; font-weight:700; padding:2px 8px; border-radius:99px; color:#fff; white-space:nowrap }}
.explicito {{ background:var(--exp) }} .fuerte {{ background:var(--fue) }} .medio {{ background:var(--med) }}
.debil {{ background:var(--deb) }} .mas {{ color:var(--sub); list-style:none }}
details {{ margin-top:12px; color:var(--sub) }}
@media (max-width:640px) {{ table, tbody, tr, td {{ display:block }} thead {{ display:none }}
  td {{ border:none; padding:4px 0 }} tr {{ border-top:1px solid var(--borde); padding:8px 0 }}
  td.num {{ text-align:left; color:var(--sub) }} td.num::before {{ content:"{veces}: " }} }}
{css_seguridad}
</style></head>
<body><main>
<h1>{e(t('ui.titulo'))}</h1>
<p class="aviso">aimarkers {VERSION} · {e(_fecha_actual())} · {e(t('ui.aviso'))}</p>
{''.join(bloques)}
</main></body></html>"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def activar_ansi_windows() -> None:
    """Activa las secuencias de color ANSI en la consola clásica de Windows."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        manejador = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        modo = ctypes.c_uint32()
        if kernel32.GetConsoleMode(manejador, ctypes.byref(modo)):
            kernel32.SetConsoleMode(manejador, modo.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except (AttributeError, OSError):
        pass


def _idioma_argv(argv: list[str]) -> str | None:
    for i, arg in enumerate(argv):
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1].lower()
        if arg == "--lang" and i + 1 < len(argv):
            return argv[i + 1].lower()
    return None


def main(argv: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argv is None else list(argv)
    fijar_idioma(_idioma_argv(argumentos) or detectar_idioma())
    fichero = t("cli.fichero")

    ap = argparse.ArgumentParser(prog="aimarkers", description=t("cli.descripcion"))
    ap.add_argument("objetivos", nargs="*", metavar="TARGET", help=t("cli.objetivos"))
    ap.add_argument("--gui", action="store_true", help=t("cli.gui"))
    ap.add_argument("--port", type=int, default=0, help=t("cli.port"))
    ap.add_argument("--no-browser", dest="sin_navegador", action="store_true", help=t("cli.no_browser"))
    ap.add_argument("--json", metavar=fichero, help=t("cli.json"))
    ap.add_argument("--md", metavar=fichero, help=t("cli.md"))
    ap.add_argument("--html", metavar=fichero, help=t("cli.html"))
    ap.add_argument("--lang", choices=IDIOMAS, help=t("cli.lang"))
    ap.add_argument("--evidencias", "--evidence", dest="evidencias", type=int, default=3, help=t("cli.evidencias"))
    ap.add_argument("--sin-color", "--no-color", dest="sin_color", action="store_true", help=t("cli.sin_color"))
    ap.add_argument("--silencioso", "--quiet", dest="silencioso", action="store_true", help=t("cli.silencioso"))
    ap.add_argument("--sin-imagenes", "--no-images", dest="sin_imagenes", action="store_true", help=t("cli.sin_imagenes"))
    ap.add_argument("--umbral", "--threshold", dest="umbral", type=int, default=None, help=t("cli.umbral"))
    ap.add_argument("--rastrear", "--crawl", dest="rastrear", action="store_true", help=t("cli.rastrear"))
    ap.add_argument("--max-paginas", "--max-pages", dest="max_paginas", type=int, default=0, help=t("cli.max_paginas"))
    ap.add_argument("--max-imagenes", "--max-images", dest="max_imagenes", type=int, default=None, help=t("cli.max_imagenes"))
    ap.add_argument("--retardo", "--delay", dest="retardo", type=float, default=0.3, help=t("cli.retardo"))
    ap.add_argument("--seguridad", "--security", dest="seguridad", action="store_true", help=t("cli.seguridad"))
    ap.add_argument("--solo-seguridad", "--security-only", dest="solo_seguridad", action="store_true", help=t("cli.solo_seguridad"))
    ap.add_argument("--sin-dns", "--no-dns", dest="sin_dns", action="store_true", help=t("cli.sin_dns"))
    ap.add_argument("--activo", "--active", dest="activo", action="store_true", help=t("cli.activo"))
    ap.add_argument("--autorizado", "--authorized", dest="autorizado", action="store_true", help=t("cli.autorizado"))
    ap.add_argument("--umbral-cvss", "--cvss-threshold", dest="umbral_cvss", type=float, default=None, help=t("cli.umbral_cvss"))
    ap.add_argument("--version", action="version", version=f"aimarkers {VERSION}")
    args = ap.parse_args(argumentos)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.modules.setdefault("aimarkers", sys.modules[__name__])  # los módulos auxiliares usan este mismo módulo
    if args.gui:
        import aimarkers_gui
        return aimarkers_gui.iniciar(args.port, abrir_navegador=not args.sin_navegador,
                                     idioma_forzado=bool(args.lang or os.environ.get("AIMARKERS_LANG")))
    if not args.objetivos:
        ap.error(t("cli.sin_objetivos"))

    if args.activo and not args.autorizado:
        import aimarkers_seguridad
        ap.error(t("seg.activo_sin_autorizacion"))
    import aimarkers_web

    def progreso(dato) -> None:
        if sys.stderr.isatty() and not args.silencioso:
            if isinstance(dato, dict):
                total = f" {dato['hecho']}/{dato['total']}" if dato.get("total") else ""
                dato = f"{t('fase.' + dato['fase'])}{total}  {dato.get('detalle', '')}"
            sys.stderr.write("\r\033[K" + str(dato)[:100])
            sys.stderr.flush()

    opciones = aimarkers_web.Opciones(
        rastrear=args.rastrear, max_paginas=args.max_paginas, max_imagenes=args.max_imagenes, retardo=max(0.0, args.retardo),
        imagenes=not args.sin_imagenes, seguridad=args.seguridad or args.solo_seguridad or args.activo, activo=args.activo,
        autorizado=args.autorizado, solo_seguridad=args.solo_seguridad, dns=not args.sin_dns, progreso=progreso)
    if opciones.seguridad:
        import aimarkers_seguridad  # noqa: F401 - registra sus textos para el informe
    try:
        resultados = [analizar_objetivo(o, opciones=opciones) for o in args.objetivos]
    except KeyboardInterrupt:  # Ctrl+C: las carpetas temporales ya se han borrado al salir de cada análisis
        sys.stderr.write("\r\033[K" + t("cli.detenido") + "\n")
        return 130
    if sys.stderr.isatty() and not args.silencioso:
        sys.stderr.write("\r\033[K")

    if not args.silencioso:
        color = sys.stdout.isatty() and not args.sin_color and os.environ.get("NO_COLOR") is None
        if color and os.name == "nt":
            activar_ansi_windows()
        try:
            print(informe_consola(resultados, args.evidencias, color))
        except UnicodeEncodeError:
            sys.stdout.reconfigure(encoding="utf-8")  # consolas cp1252
            print(informe_consola(resultados, args.evidencias, color))
    if args.json:
        Path(args.json).write_text(json.dumps([r.a_dict() for r in resultados], ensure_ascii=False, indent=2), encoding="utf-8")
    if args.md:
        Path(args.md).write_text(informe_markdown(resultados, args.evidencias), encoding="utf-8")
    if args.html:
        Path(args.html).write_text(informe_html(resultados, args.evidencias), encoding="utf-8")

    if args.umbral is not None and any(r.puntuacion() >= args.umbral for r in resultados):
        return 2
    if args.umbral_cvss is not None and any(
            h["cvss"] is not None and h["cvss"] >= args.umbral_cvss
            for r in resultados if r.seguridad is not None for h in r.seguridad.a_dict()["hallazgos"]):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
