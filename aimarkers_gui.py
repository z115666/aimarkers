# aimarkers: ignore-file
"""
Interfaz gráfica local de aimarkers / aimarkers local graphical interface.

Arranca un servidor HTTP solo en 127.0.0.1 y abre la interfaz en el navegador.
Starts an HTTP server on 127.0.0.1 only and opens the interface in the browser.

Medidas de seguridad:
- Escucha solo en la interfaz de bucle local, en un puerto aleatorio.
- Token aleatorio de 256 bits en el fragmento de la URL (no viaja en peticiones
  ni en el historial del servidor); la API lo exige en una cabecera.
- Comprobación de Host y Origin frente a DNS rebinding y peticiones de otras webs.
- Política de seguridad de contenido estricta: sin scripts en línea ni recursos externos.
- Ficheros estáticos servidos desde una lista cerrada, sin rutas del cliente.
- Subidas limitadas en tamaño y número, con rutas saneadas, a una carpeta temporal
  que se borra al salir.
Autor: Alberto
"""

from __future__ import annotations

import atexit
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath

import aimarkers

DIR_GUI = Path(__file__).resolve().parent / "gui"
ESTATICOS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/icon.svg": ("icon.svg", "image/svg+xml"),
    "/fonts/redaction-400.woff2": ("fonts/redaction-latin-400-normal.woff2", "font/woff2"),
    "/fonts/redaction-700.woff2": ("fonts/redaction-latin-700-normal.woff2", "font/woff2"),
    "/fonts/redaction-20-700.woff2": ("fonts/redaction-20-latin-700-normal.woff2", "font/woff2"),
    "/fonts/redaction-50-700.woff2": ("fonts/redaction-50-latin-700-normal.woff2", "font/woff2"),
    "/fonts/redaction-100-700.woff2": ("fonts/redaction-100-latin-700-normal.woff2", "font/woff2"),
    "/fonts/martian-mono-400.woff2": ("fonts/martian-mono-latin-400-normal.woff2", "font/woff2"),
}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

MAX_CUERPO_JSON = 1_000_000
MAX_FICHERO_SUBIDO = 50_000_000
MAX_TOTAL_SUBIDO = 500_000_000
MAX_FICHEROS_SUBIDOS = 5_000
MAX_RESULTADOS = 50


class Estado:
    """Estado del servidor: token, carpeta temporal, subidas y resultados para exportar."""

    def __init__(self) -> None:
        self.token = secrets.token_urlsafe(32)
        self.temporal = Path(tempfile.mkdtemp(prefix="aimarkers-gui-"))
        self.lote_bytes: dict[str, int] = {}
        self.lote_ficheros: dict[str, int] = {}
        self.resultados: dict[str, list] = {}
        self.cerrojo = threading.Lock()
        self.contador = threading.Lock()
        self.puerto = 0
        self.progreso: dict = {}
        self.plan: list[tuple[str, float]] = []
        self.idioma_forzado = False
        self.analizando = 0  # peticiones de análisis en curso (incluidas las que esperan turno)

    def limpiar(self) -> None:
        shutil.rmtree(self.temporal, ignore_errors=True)


ESTADO = Estado()


def ruta_relativa_segura(texto: str) -> PurePosixPath | None:
    """Normaliza la ruta relativa de un fichero subido; None si intenta salir de la carpeta."""
    texto = texto.replace("\\", "/").strip()
    if not texto or texto.startswith("/") or len(texto) > 1000 or "\x00" in texto or re.match(r"^[a-zA-Z]:", texto):
        return None
    partes = [p for p in texto.split("/") if p not in ("", ".")]
    if not partes or any(p == ".." for p in partes):
        return None
    return PurePosixPath(*partes)


def selector_nativo(tipo: str) -> str | None:
    """Abre el selector de ficheros del sistema y devuelve la ruta elegida (o None)."""
    carpeta = tipo == "folder"
    try:
        if sys.platform == "darwin":
            orden = "choose folder" if carpeta else "choose file"
            r = subprocess.run(  # nosec B603 B607
                ["osascript", "-e", f"POSIX path of ({orden} with prompt \"aimarkers\")"],
                capture_output=True, text=True, timeout=600, check=False)
        else:
            script = ("import tkinter as t, tkinter.filedialog as f; r = t.Tk(); r.withdraw(); "
                      "r.attributes('-topmost', True); "
                      f"print(f.{'askdirectory' if carpeta else 'askopenfilename'}() or '')")
            r = subprocess.run(  # nosec B603
                [sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=600, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    ruta = r.stdout.strip()
    return ruta if r.returncode == 0 and ruta else None


def hay_selector_nativo() -> bool:
    if sys.platform == "darwin":
        return shutil.which("osascript") is not None
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return False
    return True


def resultado_para_interfaz(res: aimarkers.Resultado, nombre: str | None = None) -> dict:
    """Añade al JSON del CLI lo que necesita la interfaz: banda, grupos por nivel y descripciones."""
    datos = res.a_dict()
    if nombre:
        datos["objetivo"] = nombre
    datos["banda"] = res.clave_banda().split(".")[1]
    grupos = []
    for nivel in aimarkers.ORDEN_NIVEL:
        marcadores = []
        for regla, lista in res.por_regla().items():
            if lista[0].nivel != nivel:
                continue
            marcadores.append({
                "regla": regla, "descripcion": lista[0].descripcion, "veces": len(lista),
                "puntos": round(res.contribucion(lista), 1),
                "evidencias": [{"ubicacion": h.ubicacion, "extracto": h.extracto} for h in lista[:25]],
            })
        if marcadores:
            grupos.append({"nivel": nivel, "nombre": aimarkers.t("nivel." + nivel), "peso": aimarkers.PESOS[nivel],
                           "marcadores": marcadores})
    datos["grupos"] = grupos
    datos["tipo_nombre"] = aimarkers.t("tipo." + res.tipo)
    datos["valoracion"] = res.banda()
    datos["solo_seguridad"] = res.solo_seguridad
    datos["pixeles"] = aimarkers.tabla_pixeles(res)
    datos.pop("lecturas_imagen", None)
    ubicaciones: dict[str, dict] = {}
    for h in res.hallazgos:
        clave = h.ubicacion.rsplit(":", 1)[0] if re.search(r":\d+$", h.ubicacion) else h.ubicacion
        dato = ubicaciones.setdefault(clave, {"ubicacion": clave, "veces": 0, "peso": 0, "peor": "debil"})
        dato["veces"] += 1
        dato["peso"] += h.peso
        if aimarkers.ORDEN_NIVEL.index(h.nivel) < aimarkers.ORDEN_NIVEL.index(dato["peor"]):
            dato["peor"] = h.nivel
    datos["por_ubicacion"] = sorted(ubicaciones.values(), key=lambda x: (-x["peso"], x["ubicacion"]))[:40]
    return datos


class Manejador(BaseHTTPRequestHandler):
    server_version = "aimarkers"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # --- utilidades -------------------------------------------------------
    def log_message(self, formato, *args):  # silencioso: no registrar rutas analizadas
        return

    def _cabeceras_comunes(self, tipo: str, largo: int, extra: dict | None = None) -> None:
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(largo))
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        for clave, valor in (extra or {}).items():
            self.send_header(clave, valor)

    def _enviar(self, estado: int, cuerpo: bytes, tipo: str, extra: dict | None = None) -> None:
        self.send_response(estado)
        self._cabeceras_comunes(tipo, len(cuerpo), extra)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(cuerpo)

    def _json(self, datos, estado: int = 200) -> None:
        self._enviar(estado, json.dumps(datos, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _error(self, estado: int, mensaje: str) -> None:
        self._json({"error": mensaje}, estado)

    def _host_valido(self) -> bool:
        host = self.headers.get("Host", "")
        return host in (f"127.0.0.1:{ESTADO.puerto}", f"localhost:{ESTADO.puerto}")

    def _origen_valido(self) -> bool:
        origen = self.headers.get("Origin")
        return origen is None or origen in (f"http://127.0.0.1:{ESTADO.puerto}", f"http://localhost:{ESTADO.puerto}")

    def _autorizado(self) -> bool:
        return hmac.compare_digest(self.headers.get("X-Aimarkers-Token", ""), ESTADO.token)

    def _leer_cuerpo(self, maximo: int) -> bytes | None:
        try:
            largo = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if largo < 0 or largo > maximo:
            return None
        return self.rfile.read(largo)

    # --- GET --------------------------------------------------------------
    def do_GET(self):
        if not self._host_valido():
            return self._error(HTTPStatus.MISDIRECTED_REQUEST, "host")
        ruta = self.path.split("?", 1)[0]
        if ruta in ESTATICOS:
            fichero, tipo = ESTATICOS[ruta]
            try:
                cuerpo = (DIR_GUI / fichero).read_bytes()
            except OSError:
                return self._error(HTTPStatus.NOT_FOUND, "not found")
            extra = {"Cache-Control": "max-age=86400"} if fichero.startswith("fonts/") else None
            return self._enviar(200, cuerpo, tipo, extra)
        if ruta == "/api/progress":
            if not self._autorizado():
                return self._error(HTTPStatus.FORBIDDEN, "token")
            return self._json(ESTADO.progreso or {"fase": "", "porcentaje": 0})
        if ruta == "/api/config":
            if not self._autorizado():
                return self._error(HTTPStatus.FORBIDDEN, "token")
            return self._json({"version": aimarkers.VERSION, "idioma": aimarkers.idioma(), "forzado": ESTADO.idioma_forzado,
                               "c2patool": shutil.which("c2patool") is not None,
                               "pixeles": __import__("aimarkers_pixeles").disponible(),
                               "selector": hay_selector_nativo()})
        return self._error(HTTPStatus.NOT_FOUND, "not found")

    do_HEAD = do_GET

    # --- POST -------------------------------------------------------------
    def do_POST(self):
        if not self._host_valido() or not self._origen_valido():
            return self._error(HTTPStatus.FORBIDDEN, "origin")
        if not self._autorizado():
            return self._error(HTTPStatus.FORBIDDEN, "token")
        ruta, _, consulta = self.path.partition("?")
        if ruta == "/api/upload":
            return self._subir(consulta)
        cuerpo = self._leer_cuerpo(MAX_CUERPO_JSON)
        if cuerpo is None:
            return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body")
        try:
            datos = json.loads(cuerpo or b"{}")
        except ValueError:
            return self._error(HTTPStatus.BAD_REQUEST, "json")
        if not isinstance(datos, dict):
            return self._error(HTTPStatus.BAD_REQUEST, "json")
        if ruta == "/api/analyze":
            return self._analizar(datos)
        if ruta == "/api/pick":
            return self._json({"ruta": selector_nativo("folder" if datos.get("tipo") == "folder" else "file")})
        if ruta == "/api/export":
            return self._exportar(datos)
        if ruta == "/api/cancel":
            return self._cancelar(datos)
        return self._error(HTTPStatus.NOT_FOUND, "not found")

    def _subir(self, consulta: str) -> None:
        params = dict(p.split("=", 1) for p in consulta.split("&") if "=" in p)
        lote = params.get("batch", "")
        relativa = ruta_relativa_segura(_decodificar(params.get("path", "")))
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", lote) or relativa is None:
            return self._error(HTTPStatus.BAD_REQUEST, "path")
        cuerpo = self._leer_cuerpo(MAX_FICHERO_SUBIDO)
        if cuerpo is None:
            return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "size")
        with ESTADO.cerrojo:
            total = ESTADO.lote_bytes.get(lote, 0) + len(cuerpo)
            cuenta = ESTADO.lote_ficheros.get(lote, 0) + 1
            if total > MAX_TOTAL_SUBIDO or cuenta > MAX_FICHEROS_SUBIDOS:
                return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "batch")
            ESTADO.lote_bytes[lote], ESTADO.lote_ficheros[lote] = total, cuenta
        base = (ESTADO.temporal / lote).resolve()
        destino = (base / Path(*relativa.parts)).resolve()
        try:
            destino.relative_to(base)
        except ValueError:
            return self._error(HTTPStatus.BAD_REQUEST, "path")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(cuerpo)
        return self._json({"ok": True})

    def _analizar(self, datos: dict) -> None:
        idioma = datos.get("idioma") if datos.get("idioma") in aimarkers.IDIOMAS else aimarkers.detectar_idioma()
        import aimarkers_seguridad  # noqa: F401 - registra los textos del módulo de seguridad
        import aimarkers_web
        opciones = aimarkers_web.Opciones(
            imagenes=bool(datos.get("imagenes", True)), rastrear=bool(datos.get("rastrear")),
            max_paginas=_entero(datos.get("max_paginas"), 0, -1, 1_000_000), retardo=0.3,
            seguridad=bool(datos.get("seguridad")) or bool(datos.get("solo_seguridad")),
            solo_seguridad=bool(datos.get("solo_seguridad")), activo=bool(datos.get("activo")),
            autorizado=bool(datos.get("autorizado")), dns=bool(datos.get("consultas", True)),
            osv=bool(datos.get("consultas", True)), progreso=_avance)
        if opciones.activo and not opciones.autorizado:
            return self._error(HTTPStatus.BAD_REQUEST, "authorization")
        objetivos = []
        if isinstance(datos.get("lote"), str) and re.fullmatch(r"[A-Za-z0-9_-]{8,64}", datos["lote"]):
            carpeta = ESTADO.temporal / datos["lote"]
            nombre = str(datos.get("nombre") or "")[:200]
            elementos = list(carpeta.iterdir()) if carpeta.is_dir() else []
            if len(elementos) == 1:
                objetivos.append((str(elementos[0]), nombre or elementos[0].name))
            elif elementos:
                objetivos.append((str(carpeta), nombre or "…"))
        elif isinstance(datos.get("objetivo"), str) and datos["objetivo"].strip():
            objetivo = datos["objetivo"].strip()[:4000]
            if not re.match(r"https?://", objetivo, re.I):
                objetivo = os.path.expanduser(objetivo)
            objetivos.append((objetivo, None))
        if not objetivos:
            return self._error(HTTPStatus.BAD_REQUEST, "target")
        with ESTADO.contador:
            ESTADO.analizando += 1
        try:
            return self._ejecutar(objetivos, opciones, idioma)
        except aimarkers.Cancelado:
            return self._error(HTTPStatus.CONFLICT, "cancelled")
        finally:
            with ESTADO.contador:
                ESTADO.analizando -= 1
                if ESTADO.analizando == 0:
                    aimarkers.anular_parada()  # una parada pedida sin análisis en curso no afecta al siguiente

    def _ejecutar(self, objetivos: list, opciones, idioma: str) -> None:
        with ESTADO.cerrojo:  # el idioma es global en aimarkers: un análisis cada vez
            aimarkers.fijar_idioma(idioma)
            es_url = bool(re.match(r"https?://", objetivos[0][0], re.I))
            ESTADO.plan = plan_fases(es_url, opciones)
            ESTADO.progreso = {"fase": ESTADO.plan[0][0], "hecho": 0, "total": 0, "detalle": "", "porcentaje": 0.0,
                               "plan": [f for f, _ in ESTADO.plan]}
            try:
                resultados = [(aimarkers.analizar_objetivo(o, opciones=opciones), n) for o, n in objetivos]
            finally:
                ESTADO.progreso = {}
            for res, nombre in resultados:
                if nombre:
                    res.objetivo = nombre
            salida = [resultado_para_interfaz(r) for r, _ in resultados]
            ident = secrets.token_urlsafe(9)
            ESTADO.resultados[ident] = [r for r, _ in resultados]
            while len(ESTADO.resultados) > MAX_RESULTADOS:
                ESTADO.resultados.pop(next(iter(ESTADO.resultados)))
        return self._json({"id": ident, "resultados": salida})

    def _cancelar(self, datos: dict) -> None:
        """Detiene el análisis en curso y, si se indica, borra los ficheros de una subida interrumpida."""
        lote = datos.get("lote")
        if isinstance(lote, str) and re.fullmatch(r"[A-Za-z0-9_-]{8,64}", lote):
            shutil.rmtree(ESTADO.temporal / lote, ignore_errors=True)
            with ESTADO.cerrojo:
                ESTADO.lote_bytes.pop(lote, None)
                ESTADO.lote_ficheros.pop(lote, None)
        with ESTADO.contador:
            en_curso = ESTADO.analizando > 0
            if en_curso:
                aimarkers.pedir_parada()
        return self._json({"detenido": en_curso})

    def _exportar(self, datos: dict) -> None:
        resultados = ESTADO.resultados.get(str(datos.get("id", "")))
        formato = datos.get("formato")
        if not resultados or formato not in ("html", "md", "json"):
            return self._error(HTTPStatus.NOT_FOUND, "result")
        with ESTADO.cerrojo:
            if datos.get("idioma") in aimarkers.IDIOMAS:
                aimarkers.fijar_idioma(datos["idioma"])
            if formato == "html":
                cuerpo, tipo = aimarkers.informe_html(resultados, 5), "text/html; charset=utf-8"
            elif formato == "md":
                cuerpo, tipo = aimarkers.informe_markdown(resultados, 5), "text/markdown; charset=utf-8"
            else:
                cuerpo = json.dumps([r.a_dict() for r in resultados], ensure_ascii=False, indent=2)
                tipo = "application/json; charset=utf-8"
        nombre = {"html": "report.html", "md": "report.md", "json": "report.json"}[formato]
        return self._enviar(200, cuerpo.encode("utf-8"), tipo, {"Content-Disposition": f'attachment; filename="{nombre}"'})


def plan_fases(es_url: bool, op) -> list[tuple[str, float]]:
    """Fases previstas y su peso aproximado en el tiempo total, para calcular el porcentaje."""
    ia = not op.solo_seguridad
    if es_url:
        fases = [("descarga", 40 if op.rastrear else 12), ("ia", 8 if ia else 0), ("imagenes", 25 if ia and op.imagenes else 0),
                 ("scripts", 10 if op.seguridad else 0), ("seguridad", 10 if op.seguridad else 0),
                 ("dependencias", 4 if op.seguridad and op.osv else 0),
                 ("dns", 6 if op.seguridad and op.dns else 0), ("activo", 20 if op.activo and op.autorizado else 0)]
    else:
        fases = [("ficheros", 60 if ia else 0), ("git", 15 if ia else 0), ("codigo", 30 if op.seguridad else 0),
                 ("dependencias", 12 if op.seguridad and op.osv else 0)]
    fases = [(f, w) for f, w in fases if w]
    total = sum(w for _, w in fases) or 1
    return [(f, w / total) for f, w in fases]


def _avance(dato) -> None:
    if not isinstance(dato, dict) or not ESTADO.plan:
        return
    fases = [f for f, _ in ESTADO.plan]
    fase = dato.get("fase", "")
    anterior = ESTADO.progreso.get("porcentaje", 0.0) if ESTADO.progreso else 0.0
    if fase in fases:
        indice = fases.index(fase)
        hecho_antes = sum(w for _, w in ESTADO.plan[:indice])
        total = max(1, int(dato.get("total") or 0))
        fraccion = min(1.0, int(dato.get("hecho") or 0) / total) if dato.get("total") else 0.0
        porcentaje = 100 * (hecho_antes + ESTADO.plan[indice][1] * fraccion)
    else:
        porcentaje = anterior
    ESTADO.progreso = {"fase": fase, "hecho": int(dato.get("hecho") or 0), "total": int(dato.get("total") or 0),
                       "detalle": str(dato.get("detalle", ""))[:160], "porcentaje": round(max(anterior, min(99.0, porcentaje)), 1),
                       "plan": fases}


def _entero(valor, por_defecto: int, minimo: int, maximo: int) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return por_defecto
    return max(minimo, min(maximo, numero))


def _decodificar(texto: str) -> str:
    from urllib.parse import unquote
    return unquote(texto)


def crear_servidor(puerto: int = 0) -> ThreadingHTTPServer:
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
    servidor.daemon_threads = True
    ESTADO.puerto = servidor.server_address[1]
    return servidor


def iniciar(puerto: int = 0, abrir_navegador: bool = True, idioma_forzado: bool = False) -> int:
    ESTADO.idioma_forzado = idioma_forzado
    atexit.register(ESTADO.limpiar)
    try:
        servidor = crear_servidor(puerto)
    except OSError as e:
        print(f"aimarkers --gui: {e}", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{ESTADO.puerto}/#t={ESTADO.token}"
    es = aimarkers.idioma() == "es"
    print(("Interfaz de aimarkers en " if es else "aimarkers interface at ") + url)
    print("Pulsa Ctrl+C para cerrarla." if es else "Press Ctrl+C to close it.")
    if abrir_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
        ESTADO.limpiar()
    return 0
