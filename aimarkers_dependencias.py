# aimarkers: ignore-file
"""
aimarkers - Dependencias con vulnerabilidades conocidas / Dependencies with known vulnerabilities.

Lee los ficheros de dependencias y de bloqueo (requirements.txt, package-lock.json, yarn.lock,
poetry.lock, uv.lock, Pipfile.lock, composer.lock, Gemfile.lock, go.mod, Cargo.lock,
packages.lock.json) y las librerías JavaScript detectadas en una web, y consulta sus versiones
exactas en OSV.dev, la base abierta de vulnerabilidades de Google que reúne los avisos de GitHub,
PyPI, npm, RustSec, Go y otros.

Solo se envían a OSV.dev el ecosistema, el nombre y la versión de cada paquete; nunca código ni
rutas. Se puede desactivar con --sin-osv / --no-osv.

Solo usa la biblioteca estándar. Autor: Alberto
"""

from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import aimarkers
import cvss4

OSV_API = "https://api.osv.dev/v1"
MAX_PAQUETES = 3000         # paquetes distintos que se consultan como máximo
MAX_AVISOS = 200            # avisos de los que se descarga el detalle
MAX_RESPUESTA = 8_000_000   # bytes por respuesta de OSV.dev
TIEMPO = 20                 # segundos por petición

# Librerías detectadas en webs -> nombre del paquete en npm
NPM_DE_LIBRERIA = {"jquery": "jquery", "jquery ui": "jquery-ui", "bootstrap": "bootstrap", "angularjs": "angular",
                   "lodash": "lodash", "moment.js": "moment", "handlebars": "handlebars"}


# ---------------------------------------------------------------------------
# Lectura de manifiestos y ficheros de bloqueo (solo versiones exactas)
# ---------------------------------------------------------------------------

def _requirements(texto: str) -> list[tuple[str, str, str]]:
    salida = []
    for cruda in texto.splitlines():
        linea = cruda.split("#", 1)[0].strip()
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*===?\s*([A-Za-z0-9.!+_-]+)\s*(?:;.*)?$", linea)
        if m:
            salida.append(("PyPI", m.group(1), m.group(2)))
    return salida


def _bloques_toml(texto: str, ecosistema: str) -> list[tuple[str, str, str]]:
    """[[package]] con name y version (poetry.lock, uv.lock, pdm.lock, Cargo.lock)."""
    salida = []
    for bloque in re.split(r"(?m)^\[\[package\]\]\s*$", texto)[1:]:
        cabecera = re.split(r"(?m)^\[", bloque, maxsplit=1)[0]
        nombre = re.search(r'(?m)^name\s*=\s*"([^"]+)"', cabecera)
        version = re.search(r'(?m)^version\s*=\s*"([^"]+)"', cabecera)
        if nombre and version:
            salida.append((ecosistema, nombre.group(1), version.group(1)))
    return salida


def _json(texto: str):
    try:
        return json.loads(texto)
    except ValueError:
        return None


def _pipfile_lock(texto: str) -> list[tuple[str, str, str]]:
    datos = _json(texto) or {}
    salida = []
    for seccion in ("default", "develop"):
        for nombre, d in (datos.get(seccion) or {}).items():
            version = d.get("version", "") if isinstance(d, dict) else ""
            if isinstance(version, str) and version.startswith("=="):
                salida.append(("PyPI", nombre, version[2:]))
    return salida


def _package_lock(texto: str) -> list[tuple[str, str, str]]:
    datos = _json(texto) or {}
    salida = []
    paquetes = datos.get("packages")
    if isinstance(paquetes, dict):  # lockfileVersion 2 y 3
        for ruta, d in paquetes.items():
            if not ruta or not isinstance(d, dict) or d.get("link") or "node_modules/" not in ruta:
                continue
            version = d.get("version")
            if isinstance(version, str) and re.match(r"\d", version):
                salida.append(("npm", d.get("name") or ruta.rsplit("node_modules/", 1)[1], version))
        return salida

    def recorrer(dependencias: dict, profundidad: int = 0) -> None:  # lockfileVersion 1
        for nombre, d in (dependencias or {}).items():
            if isinstance(d, dict) and profundidad < 30:
                version = d.get("version")
                if isinstance(version, str) and re.match(r"\d", version):
                    salida.append(("npm", nombre, version))
                recorrer(d.get("dependencies") or {}, profundidad + 1)

    recorrer(datos.get("dependencies") or {})
    return salida


def _yarn_lock(texto: str) -> list[tuple[str, str, str]]:
    salida = []
    for bloque in re.split(r"\n\s*\n", texto):
        lineas = [x for x in bloque.splitlines() if x.strip() and not x.lstrip().startswith("#")]
        if not lineas or lineas[0].startswith(" "):
            continue
        especificacion = lineas[0].rstrip(":").split(",")[0].strip().strip('"')
        corte = especificacion.rfind("@")
        if corte <= 0:
            continue
        nombre = especificacion[:corte]
        version = next((m.group(1) for x in lineas[1:] if (m := re.match(r'^\s+version:?\s+"?([^"\s]+)"?\s*$', x))), None)
        if version and re.match(r"\d", version) and nombre != "__metadata":
            salida.append(("npm", nombre, version))
    return salida


def _composer_lock(texto: str) -> list[tuple[str, str, str]]:
    datos = _json(texto) or {}
    salida = []
    for seccion in ("packages", "packages-dev"):
        for d in datos.get(seccion) or []:
            if isinstance(d, dict) and isinstance(d.get("name"), str) and isinstance(d.get("version"), str):
                version = d["version"].lstrip("vV")
                if re.match(r"\d", version):
                    salida.append(("Packagist", d["name"], version))
    return salida


def _gemfile_lock(texto: str) -> list[tuple[str, str, str]]:
    salida = []
    for m in re.finditer(r"(?m)^ {4}([A-Za-z0-9_.-]+) \(([0-9][^)\s]*)\)\s*$", texto):
        salida.append(("RubyGems", m.group(1), m.group(2).split("-")[0]))
    return salida


def _go_mod(texto: str) -> list[tuple[str, str, str]]:
    salida = []
    for m in re.finditer(r"(?m)^\s*(?:require\s+)?([A-Za-z0-9.~_-]+\.[A-Za-z]{2,}/[^\s]+)\s+v(\d[^\s]*)", texto):
        if not m.group(0).lstrip().startswith(("module", "go ", "replace", "exclude")):
            salida.append(("Go", m.group(1), m.group(2).split("+")[0]))
    return salida


def _nuget_lock(texto: str) -> list[tuple[str, str, str]]:
    datos = _json(texto) or {}
    salida = []
    for marco in (datos.get("dependencies") or {}).values():
        for nombre, d in (marco or {}).items():
            if isinstance(d, dict) and isinstance(d.get("resolved"), str):
                salida.append(("NuGet", nombre, d["resolved"]))
    return salida


def lector(nombre: str):
    """Función que extrae dependencias de un fichero según su nombre, o None si no es de dependencias."""
    base = nombre.lower()
    if base.startswith("requirements") and base.endswith((".txt", ".in")) or base == "constraints.txt":
        return _requirements
    return {
        "poetry.lock": lambda x: _bloques_toml(x, "PyPI"), "uv.lock": lambda x: _bloques_toml(x, "PyPI"),
        "pdm.lock": lambda x: _bloques_toml(x, "PyPI"), "cargo.lock": lambda x: _bloques_toml(x, "crates.io"),
        "pipfile.lock": _pipfile_lock, "package-lock.json": _package_lock, "npm-shrinkwrap.json": _package_lock,
        "yarn.lock": _yarn_lock, "composer.lock": _composer_lock, "gemfile.lock": _gemfile_lock, "go.mod": _go_mod,
        "packages.lock.json": _nuget_lock,
    }.get(base)


def extraer(nombre: str, texto: str) -> list[tuple[str, str, str]]:
    funcion = lector(nombre)
    if funcion is None:
        return []
    try:
        return funcion(texto)
    except (ValueError, TypeError, AttributeError, KeyError):  # fichero malformado: se ignora
        return []


# ---------------------------------------------------------------------------
# Consulta a OSV.dev
# ---------------------------------------------------------------------------

def _peticion(ruta: str, datos: dict | None = None):
    """GET o POST JSON a la API de OSV.dev (URL fija en HTTPS, respuesta limitada)."""
    url = OSV_API + ruta
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    peticion = urllib.request.Request(url, data=cuerpo, method="POST" if cuerpo else "GET",  # noqa: S310 - URL fija https
                                      headers={"Content-Type": "application/json", "Accept": "application/json",
                                               "User-Agent": f"aimarkers/{aimarkers.VERSION}"})
    with urllib.request.build_opener().open(peticion, timeout=TIEMPO) as respuesta:  # nosec B310
        crudo = respuesta.read(MAX_RESPUESTA + 1)
    if len(crudo) > MAX_RESPUESTA:
        raise ValueError("respuesta demasiado grande")
    return json.loads(crudo)


def consultar(paquetes: list[tuple[str, str, str]]) -> dict[tuple[str, str, str], list[str]]:
    """Identificadores de aviso que afectan a cada (ecosistema, nombre, versión)."""
    resultado: dict[tuple[str, str, str], list[str]] = {}
    for inicio in range(0, len(paquetes), 1000):
        lote = paquetes[inicio:inicio + 1000]
        aimarkers.informar("dependencias", inicio, len(paquetes) + 1, f"OSV.dev · {len(lote)}")
        datos = _peticion("/querybatch", {"queries": [{"package": {"ecosystem": e, "name": n}, "version": v} for e, n, v in lote]})
        for paquete, r in zip(lote, datos.get("results") or []):
            ids = [str(x.get("id")) for x in (r or {}).get("vulns") or [] if isinstance(x, dict) and x.get("id")]
            if ids:
                resultado[paquete] = ids
    return resultado


def detalle_avisos(ids: list[str]) -> dict[str, dict]:
    validos = [i for i in dict.fromkeys(ids) if re.fullmatch(r"[A-Za-z0-9._:-]{3,80}", i)][:MAX_AVISOS]
    salida: dict[str, dict] = {}
    grupo = ThreadPoolExecutor(max_workers=6)
    try:
        futuros = {grupo.submit(_peticion, f"/vulns/{i}"): i for i in validos}
        for hechos, futuro in enumerate(as_completed(futuros), 1):
            aimarkers.informar("dependencias", hechos, len(validos) + 1, futuros[futuro])
            try:
                datos = futuro.result()
            except (OSError, ValueError, urllib.error.URLError):
                continue
            if isinstance(datos, dict):
                salida[futuros[futuro]] = datos
    finally:  # si el usuario detiene el análisis, no se espera a las consultas pendientes
        grupo.shutdown(wait=False, cancel_futures=True)
    return salida


# ---------------------------------------------------------------------------
# Severidad y versión corregida
# ---------------------------------------------------------------------------

def cvss3_base(vector: str) -> float | None:
    """Puntuación base CVSS v3.x (especificación de FIRST, apartado 7)."""
    m = dict(p.split(":", 1) for p in vector.split("/")[1:] if ":" in p)
    try:
        cambia = m["S"] == "C"
        av = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}[m["AV"]]
        ac = {"L": 0.77, "H": 0.44}[m["AC"]]
        pr = {"N": 0.85, "L": 0.68 if cambia else 0.62, "H": 0.5 if cambia else 0.27}[m["PR"]]
        ui = {"N": 0.85, "R": 0.62}[m["UI"]]
        c, i, a = ({"H": 0.56, "L": 0.22, "N": 0.0}[m[k]] for k in ("C", "I", "A"))
    except KeyError:
        return None
    iss = 1 - (1 - c) * (1 - i) * (1 - a)
    impacto = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15 if cambia else 6.42 * iss
    if impacto <= 0:
        return 0.0
    total = min((1.08 if cambia else 1.0) * (impacto + 8.22 * av * ac * pr * ui), 10)
    entero = round(total * 100000)
    return entero / 100000.0 if entero % 10000 == 0 else (math.floor(entero / 10000) + 1) / 10.0


def severidad(aviso: dict) -> tuple[str, float | None]:
    """(critica|alta|media|baja|desconocida, puntuación CVSS si la hay)."""
    puntuacion = None
    for s in aviso.get("severity") or []:
        if not isinstance(s, dict) or not isinstance(s.get("score"), str):
            continue
        try:
            if s.get("type") == "CVSS_V4":
                puntuacion = cvss4.puntuacion(s["score"])
                break
            if s.get("type") == "CVSS_V3":
                puntuacion = cvss3_base(s["score"])
        except (ValueError, KeyError):
            continue
    if puntuacion is not None:
        nivel = "critica" if puntuacion >= 9 else "alta" if puntuacion >= 7 else "media" if puntuacion >= 4 else "baja"
        return nivel, puntuacion
    texto = str((aviso.get("database_specific") or {}).get("severity", "")).upper()
    nivel = {"CRITICAL": "critica", "HIGH": "alta", "MODERATE": "media", "MEDIUM": "media", "LOW": "baja"}.get(texto)
    return nivel or "desconocida", None


def _clave_version(texto: str) -> tuple:
    return tuple(int(x) if x.isdigit() else x for x in re.findall(r"\d+|[A-Za-z]+", texto))


def version_corregida(aviso: dict, ecosistema: str, nombre: str, actual: str) -> str | None:
    candidatas = []
    for afectado in aviso.get("affected") or []:
        paquete = afectado.get("package") or {}
        if str(paquete.get("ecosystem", "")).split(":")[0] != ecosistema or \
                str(paquete.get("name", "")).lower() != nombre.lower():
            continue
        for rango in afectado.get("ranges") or []:
            for evento in rango.get("events") or []:
                if isinstance(evento, dict) and isinstance(evento.get("fixed"), str):
                    candidatas.append(evento["fixed"].lstrip("v"))
    posteriores = [v for v in candidatas if _clave_version(v) > _clave_version(actual)]
    try:
        return min(posteriores, key=_clave_version) if posteriores else None
    except TypeError:  # versiones con formatos que no se pueden comparar
        return posteriores[0]


ORDEN_SEV = ["critica", "alta", "media", "baja", "desconocida"]
# Vectores base CVSS v4.0 tipo por severidad publicada (la explotabilidad real depende de si se usa la parte afectada)
VECTOR_SEV = {
    "critica": "AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
    "alta": "AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:L/VA:L/SC:N/SI:N/SA:N",
    "media": "AV:N/AC:L/AT:P/PR:N/UI:P/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N",
    "baja": "AV:N/AC:H/AT:P/PR:L/UI:P/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N",
}
VECTOR_SEV["desconocida"] = VECTOR_SEV["media"]


def resumen(paquete: tuple[str, str, str], ids: list[str], avisos: dict[str, dict]) -> dict:
    """Agrupa los avisos de un paquete: peor severidad, CVE, versión mínima que los corrige todos."""
    ecosistema, nombre, version = paquete
    peor, cves, arreglos, puntuaciones = "desconocida", [], [], []
    for i in ids:
        aviso = avisos.get(i, {"id": i})
        nivel, puntos = severidad(aviso)
        if ORDEN_SEV.index(nivel) < ORDEN_SEV.index(peor):
            peor = nivel
        if puntos is not None:
            puntuaciones.append(puntos)
        alias = [a for a in aviso.get("aliases") or [] if isinstance(a, str) and a.startswith("CVE-")]
        cves.extend(alias or [i])
        fijo = version_corregida(aviso, ecosistema, nombre, version)
        if fijo:
            arreglos.append(fijo)
    try:
        arreglo = max(arreglos, key=_clave_version) if arreglos else None
    except TypeError:
        arreglo = arreglos[0]
    return {"severidad": peor, "ids": list(dict.fromkeys(cves)), "arreglo": arreglo,
            "cvss": max(puntuaciones) if puntuaciones else None, "avisos": len(ids)}


# ---------------------------------------------------------------------------
# Integración con el informe de seguridad
# ---------------------------------------------------------------------------

def revisar(informe, paquetes: dict[tuple[str, str, str], str]) -> None:
    """Consulta en OSV.dev los paquetes {(ecosistema, nombre, versión): ubicación} y añade los hallazgos."""
    if not paquetes:
        return
    lista = list(paquetes)[:MAX_PAQUETES]
    try:
        afectados = consultar(lista)
        avisos = detalle_avisos([i for ids in afectados.values() for i in ids]) if afectados else {}
    except (OSError, ValueError, urllib.error.URLError) as e:
        informe.notas.append(aimarkers.t("seg.osv_error", e=str(getattr(e, "reason", e))[:120]))
        return
    for paquete, ids in afectados.items():
        datos = resumen(paquete, ids, avisos)
        ecosistema, nombre, version = paquete
        extracto = aimarkers.t("seg.dep_evidencia", n=datos["avisos"], ids=", ".join(datos["ids"][:6]),
                               f=datos["arreglo"] or "—", e=ecosistema)
        informe.anadir("dependencia-vulnerable", paquetes[paquete], extracto, clave=f"{ecosistema}:{nombre}@{version}",
                       detalle=f"{nombre} {version}", cve=datos["ids"][:12], vector=VECTOR_SEV[datos["severidad"]], e="P")
    informe.notas.append(aimarkers.t("seg.osv_resumen", n=len(lista), v=len(afectados)))
    if len(paquetes) > MAX_PAQUETES:
        informe.notas.append(aimarkers.t("seg.osv_limite", n=MAX_PAQUETES))


def revisar_librerias_web(informe) -> None:
    """Contrasta con OSV.dev las librerías JavaScript detectadas en la web y completa sus CVE."""
    paquetes = {}
    for comp in informe.inventario.values():
        npm = NPM_DE_LIBRERIA.get(comp["nombre"].lower())
        if comp["tipo"] == "libreria" and npm and comp["version"]:
            paquetes[("npm", npm, comp["version"])] = comp
    if not paquetes:
        return
    try:
        afectados = consultar(list(paquetes))
        avisos = detalle_avisos([i for ids in afectados.values() for i in ids]) if afectados else {}
    except (OSError, ValueError, urllib.error.URLError) as e:
        informe.notas.append(aimarkers.t("seg.osv_error", e=str(getattr(e, "reason", e))[:120]))
        return
    for paquete, ids in afectados.items():
        comp = paquetes[paquete]
        datos = resumen(paquete, ids, avisos)
        clave = f"{comp['nombre']} {comp['version']}"
        previo = informe.hallazgos.get(f"libreria-vulnerable|{clave}")
        detalle = clave + (f" → {datos['arreglo']}" if datos["arreglo"] else "")
        if previo is not None:  # la lista interna se queda corta: OSV.dev manda
            previo.cve = list(dict.fromkeys(datos["ids"] + previo.cve))[:12]
            previo.detalle = detalle
        else:
            informe.anadir("libreria-vulnerable", comp["fuente"] or comp["nombre"], f"{comp['nombre']} {comp['version']}",
                           clave=clave, detalle=detalle, cve=datos["ids"][:12])
    informe.notas.append(aimarkers.t("seg.osv_web", n=len(paquetes), v=len(afectados)))


def ficheros_de_dependencias(rutas: list[Path]) -> list[Path]:
    return [r for r in rutas if lector(r.name)]
