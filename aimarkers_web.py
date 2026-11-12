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

import http.client
import re
import shutil
import socket
import ssl
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


# ---------------------------------------------------------------------------
# Política TLS: CA adicional y hosts con certificado aceptado a mano
# ---------------------------------------------------------------------------

_TLS: dict = {"ca": None, "confiados": frozenset(), "intermedios": {}, "aia": {}, "intentados": set()}
AIA_MAX_BYTES = 20_000
AIA_NIVELES = 3
# OID id-ad-caIssuers (1.3.6.1.5.5.7.48.2) seguido de una URI (etiqueta [6] IA5String)
_RE_CA_ISSUERS = re.compile(rb"\x06\x08\x2b\x06\x01\x05\x05\x07\x30\x02\x86([\x01-\x7f])")


def fijar_tls(ca: str | None = None, confiados=()) -> None:
    """CA o certificado adicional en el que confiar (PEM) y hosts cuyo certificado no se verifica.

    Los hosts confiados son solo los del objetivo que indica el usuario: nunca terceros, ni OSV.dev ni DNS.
    """
    if ca:
        ssl.create_default_context(cafile=ca)  # falla aquí, y no a mitad del análisis, si el fichero no vale
    _TLS["ca"] = ca or None
    _TLS["confiados"] = frozenset(h.lower() for h in confiados if h)
    _TLS["intermedios"], _TLS["aia"], _TLS["intentados"] = {}, {}, set()


def _urls_emisor(der: bytes) -> list[str]:
    """URL «CA Issuers» de la extensión AIA del certificado: dónde descargar el certificado de su emisor."""
    urls = []
    for m in _RE_CA_ISSUERS.finditer(der):
        largo = m.group(1)[0]
        url = der[m.end():m.end() + largo].decode("ascii", "replace")
        if re.match(r"https?://[\w.-]+(?::\d+)?/", url):
            urls.append(url)
    return urls


def _ips(host: str) -> list:
    import ipaddress
    try:
        return [ipaddress.ip_address(r[4][0].split("%")[0]) for r in socket.getaddrinfo(host, None)]
    except (OSError, ValueError):
        return []


def _aia_permitida(url: str, host_objetivo: str) -> bool:
    """Evita que el certificado de una web externa haga pedir direcciones de la red interna (SSRF)."""
    destino = _ips(urllib.parse.urlsplit(url).hostname or "")
    if not destino:
        return False
    if all(ip.is_global for ip in destino):
        return True
    return not any(ip.is_global for ip in _ips(host_objetivo))  # web interna: su emisor también puede serlo


def completar_cadena(host: str, puerto: int = 443, timeout: int = 10) -> list[str]:
    """Descarga los certificados intermedios que el servidor no envía, como hacen los navegadores.

    Solo se usan para construir la cadena: la verificación sigue exigiendo una raíz de confianza del sistema
    (o de --ca). Devuelve las URL de las que se descargaron, o una lista vacía.
    """
    clave = (host.lower(), puerto)
    if host.lower() in _TLS["aia"]:
        return _TLS["aia"][host.lower()]
    if clave in _TLS["intentados"]:
        return []
    _TLS["intentados"].add(clave)
    lectura = ssl.create_default_context()
    lectura.check_hostname = False
    # Solo para leer el certificado y saber quién lo emitió; por esta conexión no pasa ningún dato
    lectura.verify_mode = ssl.CERT_NONE  # nosec B501
    try:
        with socket.create_connection((host, puerto), timeout=timeout) as s, lectura.wrap_socket(s, server_hostname=host) as t:
            actual = t.getpeercert(binary_form=True) or b""
    except (OSError, ssl.SSLError, ValueError):
        return []
    abridor = urllib.request.build_opener(_SinRedireccion())
    cadena, usadas = [], []
    for _ in range(AIA_NIVELES):
        urls = [u for u in _urls_emisor(actual) if _aia_permitida(u, host)]
        if not urls:
            break
        try:
            with abridor.open(urllib.request.Request(urls[0], headers={"User-Agent": agente()}),  # noqa: S310 - http(s) validado
                              timeout=timeout) as r:  # nosec B310
                datos = r.read(AIA_MAX_BYTES + 1)
        except (urllib.error.URLError, OSError, ValueError):
            break
        if len(datos) > AIA_MAX_BYTES:
            break
        try:
            der = ssl.PEM_cert_to_DER_cert(datos.decode("ascii")) if datos.startswith(b"-----BEGIN") else datos
        except (ValueError, UnicodeDecodeError):
            break
        if der[:1] != b"\x30":  # no es un certificado DER (por ejemplo, un paquete PKCS#7)
            break
        cadena.append(ssl.DER_cert_to_PEM_cert(der))
        usadas.append(urls[0])
        actual = der
    if cadena:
        _TLS["intermedios"][host.lower()] = cadena
        _TLS["aia"][host.lower()] = usadas
    return usadas


def falta_intermedio(error) -> bool:
    texto = f"{error} {getattr(error, 'reason', '')}"  # URLError guarda el SSLError en reason; SSLError, un código
    return "unable to get local issuer certificate" in texto or "unable to verify the first certificate" in texto


def contexto_tls(host: str | None) -> ssl.SSLContext:
    if host and host.lower() in _TLS["confiados"]:
        contexto = ssl.create_default_context()
        contexto.check_hostname = False
        # Solo para el host que el usuario ha decidido confiar de forma expresa
        contexto.verify_mode = ssl.CERT_NONE  # nosec B501
        return contexto
    contexto = ssl.create_default_context()
    if _TLS["ca"]:
        contexto.load_verify_locations(cafile=_TLS["ca"])
        # --ca puede ser el propio certificado del servidor (no una raíz): se acepta como anclaje
        contexto.verify_flags |= getattr(ssl, "VERIFY_X509_PARTIAL_CHAIN", 0)
    intermedios = _TLS["intermedios"].get((host or "").lower())
    if intermedios:
        anadir_intermedios(contexto, intermedios)
    return contexto


def anadir_intermedios(contexto: ssl.SSLContext, intermedios: list[str]) -> None:
    """Añade intermedios solo para construir la cadena: la raíz tiene que seguir siendo de confianza.

    Python 3.13 activa por defecto VERIFY_X509_PARTIAL_CHAIN, que convertiría cualquier certificado del almacén
    (también un intermedio descargado) en anclaje de confianza. Se desactiva aquí.
    """
    contexto.verify_flags &= ~getattr(ssl, "VERIFY_X509_PARTIAL_CHAIN", 0)
    contexto.load_verify_locations(cadata="".join(intermedios))


class HTTPSConPolitica(urllib.request.HTTPSHandler):
    """Elige el contexto TLS según el host de cada petición (también tras una redirección)."""

    def https_open(self, req):
        return self.do_open(http.client.HTTPSConnection, req, context=contexto_tls(req.host.split(":")[0].strip("[]")))


def obtener(url: str, maximo: int = MAX_PAGINA, timeout: int = 20, metodo: str = "GET",
            cabeceras: dict[str, str] | None = None, seguir: bool = True) -> tuple[Pagina | None, str]:
    """Hace una petición http(s) y devuelve la respuesta (también si es 4xx/5xx) o un mensaje de error."""
    if not re.match(r"https?://", url, re.I):
        return None, aimarkers.t("nota.solo_http")
    manejador = _Redirecciones()
    abridor = urllib.request.build_opener(manejador if seguir else _SinRedireccion(), HTTPSConPolitica())
    peticion = urllib.request.Request(url, method=metodo,  # noqa: S310 - esquema http(s) validado arriba
                                      headers={"User-Agent": agente(), "Accept": "*/*", **(cabeceras or {})})
    try:
        try:
            respuesta = abridor.open(peticion, timeout=timeout)  # nosec B310
        except urllib.error.URLError as e:
            partes = urllib.parse.urlsplit(peticion.full_url)
            if isinstance(e, urllib.error.HTTPError) or not falta_intermedio(e) or partes.scheme != "https" \
                    or not completar_cadena(partes.hostname or "", partes.port or 443):
                raise
            respuesta = abridor.open(peticion, timeout=timeout)  # nosec B310 - reintento con la cadena completada
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
    confiar_certificado: bool = False  # aceptar el certificado del host analizado aunque no sea válido
    ca: str | None = None              # CA o certificado adicional (PEM) en el que confiar


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
