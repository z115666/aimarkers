# aimarkers: ignore-file
"""
Descarga y rastreo de webs para aimarkers / Website fetching and crawling for aimarkers.

- Solo http(s), también tras redirecciones, y solo el mismo sitio que la URL inicial.
- Respeta robots.txt (salvo con autorización expresa sobre una web propia).
- Pausa entre peticiones, tiempo máximo por petición y límites de tamaño.
- Todo lo descargado va a una carpeta temporal que se borra al terminar (también si hay errores).
Autor: Alberto
"""

from __future__ import annotations

import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import deque
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path

import aimarkers

MAX_PAGINA = 5_000_000
MAX_TOTAL_POR_DEFECTO = 2_000_000_000
MAX_PAGINAS_RASTREO = 2000
EXT_NO_PAGINA = re.compile(
    r"\.(?:jpe?g|png|gif|webp|avif|heic|svg|ico|bmp|tiff?|pdf|zip|gz|tgz|rar|7z|tar|mp[34]|m4a|mov|avi|mkv|webm|wav|ogg|"
    r"woff2?|ttf|otf|eot|css|js|mjs|map|json|xml|rss|atom|txt|csv|xlsx?|docx?|pptx?|odt|ods|exe|dmg|pkg|msi|apk|iso)$", re.I)
RE_ENLACE = re.compile(r"<(?:a|area|iframe|frame)\b[^>]{0,1000}?\b(?:href|src)\s*=\s*[\"']([^\"'<>\s]{1,2000})[\"']", re.I)
RE_SCRIPT_SRC = re.compile(r"<script\b([^>]{0,1500})>", re.I)
RE_ATRIBUTO = re.compile(r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*(?:=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'>]+)))?")
RE_META_ROBOTS = re.compile(r"<meta[^>]{0,200}name=[\"']robots[\"'][^>]{0,200}content=[\"'][^\"']*nofollow", re.I)


def agente() -> str:
    return f"aimarkers/{aimarkers.VERSION} (+https://github.com/z115666/aimarkers)"


def atributos(etiqueta: str) -> dict[str, str]:
    """Atributos de una etiqueta HTML en un diccionario (nombres en minúsculas)."""
    datos: dict[str, str] = {}
    for m in RE_ATRIBUTO.finditer(etiqueta):
        datos.setdefault(m.group(1).lower(), unescape(m.group(2) or m.group(3) or m.group(4) or ""))
    return datos


@dataclass
class Pagina:
    url: str
    estado: int
    cabeceras: dict[str, list[str]]
    tipo: str
    redirecciones: list[str] = field(default_factory=list)
    ruta: Path | None = None
    tamano: int = 0
    _cuerpo: bytes | None = None

    def cabecera(self, nombre: str) -> str:
        valores = self.cabeceras.get(nombre.lower(), [])
        return valores[-1] if valores else ""

    def todas(self, nombre: str) -> list[str]:
        return self.cabeceras.get(nombre.lower(), [])

    @property
    def cuerpo(self) -> bytes:
        if self._cuerpo is not None:
            return self._cuerpo
        if self.ruta and self.ruta.exists():
            return self.ruta.read_bytes()
        return b""

    def texto(self) -> str:
        juego = re.search(r"charset=([\w-]+)", self.tipo, re.I)
        try:
            return self.cuerpo.decode(juego.group(1) if juego else "utf-8", errors="replace")
        except LookupError:
            return self.cuerpo.decode("utf-8", errors="replace")

    @property
    def es_html(self) -> bool:
        if "html" in self.tipo.lower():
            return True
        inicio = self.cuerpo[:400].lstrip().lower()
        return not self.tipo and inicio.startswith((b"<!doctype html", b"<html"))


class _Redirecciones(urllib.request.HTTPRedirectHandler):
    """Sigue redirecciones solo a http(s) y guarda la cadena."""

    def __init__(self) -> None:
        super().__init__()
        self.cadena: list[str] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not re.match(r"https?://", newurl, re.I):
            raise urllib.error.URLError(aimarkers.t("nota.redireccion", u=newurl[:80]))
        self.cadena.append(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def obtener(url: str, maximo: int = MAX_PAGINA, timeout: int = 20, metodo: str = "GET",
            cabeceras: dict[str, str] | None = None, seguir: bool = True) -> tuple[Pagina | None, str]:
    """Hace una petición http(s) y devuelve la respuesta (también si es 4xx/5xx) o un mensaje de error."""
    if not re.match(r"https?://", url, re.I):
        return None, aimarkers.t("nota.solo_http")
    manejador = _Redirecciones()
    abridor = urllib.request.build_opener(manejador) if seguir else urllib.request.build_opener(_SinRedireccion())
    peticion = urllib.request.Request(url, method=metodo,  # noqa: S310 - esquema http(s) validado arriba
                                      headers={"User-Agent": agente(), "Accept": "*/*", **(cabeceras or {})})
    try:
        respuesta = abridor.open(peticion, timeout=timeout)  # nosec B310
    except urllib.error.HTTPError as e:
        respuesta = e
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        return None, str(getattr(e, "reason", e))
    try:
        cuerpo = respuesta.read(maximo + 1) if metodo != "HEAD" else b""
    except (OSError, ValueError):
        cuerpo = b""
    finally:
        respuesta.close()
    cabeceras_resp: dict[str, list[str]] = {}
    for clave, valor in (respuesta.headers.items() if respuesta.headers else []):
        cabeceras_resp.setdefault(clave.lower(), []).append(valor)
    pagina = Pagina(url=respuesta.geturl() or url, estado=getattr(respuesta, "status", None) or respuesta.getcode() or 0,
                    cabeceras=cabeceras_resp, tipo=cabeceras_resp.get("content-type", [""])[-1],
                    redirecciones=manejador.cadena if seguir else [], tamano=len(cuerpo[:maximo]), _cuerpo=cuerpo[:maximo])
    return pagina, ""


class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def mismo_sitio(a: str, b: str) -> bool:
    """Mismo host, ignorando el prefijo www."""
    ha = (urllib.parse.urlsplit(a).hostname or "").lower().removeprefix("www.")
    hb = (urllib.parse.urlsplit(b).hostname or "").lower().removeprefix("www.")
    return bool(ha) and ha == hb


def normalizar(url: str) -> str:
    partes = urllib.parse.urlsplit(url)
    ruta = partes.path or "/"
    return urllib.parse.urlunsplit((partes.scheme.lower(), partes.netloc.lower(), ruta, partes.query, ""))


@dataclass
class Opciones:
    rastrear: bool = False
    max_paginas: int = 0            # 0: por defecto (1 sin rastreo, MAX_PAGINAS_RASTREO con rastreo); <0: sin límite
    max_imagenes: int | None = None  # None: por defecto; 0: sin límite
    retardo: float = 0.3
    imagenes: bool = True
    seguridad: bool = False
    activo: bool = False
    autorizado: bool = False
    ignorar_robots: bool = False
    solo_seguridad: bool = False
    dns: bool = True
    osv: bool = True                 # contrastar dependencias con OSV.dev
    pixeles: bool = True             # lectura de píxeles de las imágenes (Pillow y NumPy)
    max_total: int = MAX_TOTAL_POR_DEFECTO
    progreso: object = None          # función(texto) para informar del avance


class Rastreo:
    """Descarga una página o un sitio completo a una carpeta temporal que se borra al salir."""

    def __init__(self, url: str, opciones: Opciones) -> None:
        self.inicio = url
        self.op = opciones
        self.carpeta = Path(tempfile.mkdtemp(prefix="aimarkers-web-"))
        self.paginas: list[Pagina] = []
        self.recursos: list[Pagina] = []     # JS del propio sitio, robots.txt, etc.
        self.notas: list[str] = []
        self.error = ""
        self.total = 0
        self.robots: urllib.robotparser.RobotFileParser | None = None
        self.robots_txt = ""
        self.limite_alcanzado = False

    def __enter__(self) -> Rastreo:
        return self

    def __exit__(self, *exc) -> None:
        self.cerrar()

    def cerrar(self) -> None:
        shutil.rmtree(self.carpeta, ignore_errors=True)


    def _guardar(self, pagina: Pagina, nombre: str) -> None:
        pagina.ruta = self.carpeta / nombre
        pagina.ruta.write_bytes(pagina._cuerpo or b"")
        self.total += pagina.tamano
        pagina._cuerpo = None

    def _cargar_robots(self, base: str) -> None:
        url = urllib.parse.urljoin(base, "/robots.txt")
        pagina, _ = obtener(url, maximo=500_000, timeout=10)
        self.robots = urllib.robotparser.RobotFileParser()
        if pagina and pagina.estado == 200 and not pagina.es_html:
            self.robots_txt = pagina.texto()
            self.robots.parse(self.robots_txt.splitlines())
            pagina.url = url
            self.recursos.append(pagina)
        else:
            self.robots.parse([])

    def permitido(self, url: str) -> bool:
        if self.op.ignorar_robots and self.op.autorizado:
            return True
        return self.robots is None or self.robots.can_fetch(agente(), url)

    def max_paginas(self) -> int:
        if not self.op.rastrear:
            return 1
        if self.op.max_paginas < 0:
            return 10 ** 9
        return self.op.max_paginas or MAX_PAGINAS_RASTREO

    def ejecutar(self) -> None:
        aimarkers.informar("descarga", 0, 1, self.inicio)
        primera, error = obtener(self.inicio)
        if primera is None:
            self.error = error
            return
        base = primera.url
        if self.op.rastrear:
            self._cargar_robots(base)
        self._guardar(primera, "p0.html")
        self.paginas.append(primera)
        if not (self.op.rastrear and primera.es_html):
            return
        vistas = {normalizar(self.inicio), normalizar(base)}
        cola: deque[str] = deque(self._enlaces(primera, base, vistas))
        limite = self.max_paginas()
        while cola:
            if len(self.paginas) >= limite or self.total >= self.op.max_total:
                self.limite_alcanzado = True
                break
            url = cola.popleft()
            if not self.permitido(url):
                continue
            time.sleep(max(0.0, self.op.retardo))
            pagina, _ = obtener(url)
            if pagina is None or not mismo_sitio(pagina.url, base):
                continue
            vistas.add(normalizar(pagina.url))
            if not pagina.es_html:
                continue
            self._guardar(pagina, f"p{len(self.paginas)}.html")
            self.paginas.append(pagina)
            aimarkers.informar("descarga", len(self.paginas), min(limite, len(self.paginas) + len(cola)), pagina.url)
            if not RE_META_ROBOTS.search(pagina.texto()[:20000]) or self.op.ignorar_robots:
                cola.extend(self._enlaces(pagina, pagina.url, vistas))
        if self.limite_alcanzado:
            self.notas.append(aimarkers.t("nota.limite_paginas", n=len(self.paginas)))

    def _enlaces(self, pagina: Pagina, base: str, vistas: set[str]) -> list[str]:
        nuevos = []
        for m in RE_ENLACE.finditer(pagina.texto()):
            url = urllib.parse.urljoin(base, unescape(m.group(1)).strip())
            if not re.match(r"https?://", url, re.I) or not mismo_sitio(url, base):
                continue
            url = normalizar(url)
            ruta = urllib.parse.urlsplit(url).path
            if url in vistas or EXT_NO_PAGINA.search(ruta) or re.search(r"/(?:wp-json|feed|xmlrpc\.php|wp-login\.php)", ruta):
                continue
            vistas.add(url)
            nuevos.append(url)
        return nuevos

    def scripts_propios(self, maximo: int = 200) -> list[Pagina]:
        """Descarga los JavaScript del propio sitio que cargan las páginas (lo mismo que haría un navegador)."""
        urls: list[str] = []
        for pagina in self.paginas:
            for m in RE_SCRIPT_SRC.finditer(pagina.texto()):
                src = atributos(m.group(1)).get("src")
                if not src:
                    continue
                url = urllib.parse.urljoin(pagina.url, src)
                if re.match(r"https?://", url, re.I) and mismo_sitio(url, pagina.url) and url not in urls:
                    urls.append(url)
        descargados = []
        for i, url in enumerate(urls[:maximo]):
            aimarkers.informar("scripts", i, min(len(urls), maximo), url)
            time.sleep(max(0.0, self.op.retardo) / 2)
            js, _ = obtener(url, maximo=3_000_000)
            if js and js.estado == 200:
                self._guardar(js, f"s{i}.js")
                descargados.append(js)
        self.recursos.extend(descargados)
        return descargados

    def urls_imagenes(self) -> list[str]:
        urls: list[str] = []
        for pagina in self.paginas:
            for u in aimarkers.urls_imagenes(pagina.texto()):
                absoluta = urllib.parse.urljoin(pagina.url, u)
                if re.match(r"https?://", absoluta, re.I) and absoluta not in urls:
                    urls.append(absoluta)
        return urls
