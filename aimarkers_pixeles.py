# aimarkers: ignore-file
"""
aimarkers - Lectura forense de píxeles / Pixel-level forensic reading.

Complementa la lectura de metadatos con medidas sobre la propia imagen. No es un clasificador
entrenado: son tres lecturas clásicas de análisis forense, con umbrales conservadores elegidos para
que una foto real casi nunca dé positivo, a costa de no detectar muchas imágenes generadas.

1. Ruido de sensor: las cámaras dejan un ruido de fondo incluso en zonas lisas. Un residuo casi nulo
   en la mayor parte de la imagen es propio de imágenes generadas, renderizadas o muy retocadas.
2. Huella periódica: los decodificadores que amplían la imagen por bloques (VAE de difusión, GAN)
   dejan picos en el espectro del residuo en la rejilla de 8 píxeles.
3. Resolución: coincide con un tamaño de salida habitual de los generadores. Por sí sola no indica nada.

Además se lee el rastro de cámara (marca y modelo en EXIF): si está, las lecturas no se puntúan.

Los puntos 1 y 2 necesitan Pillow y NumPy (pip install pillow numpy); el 3 y el rastro de cámara,
solo la biblioteca estándar. Autor: Alberto
"""

from __future__ import annotations

import io
import re
import struct

# Umbrales calibrados con 32 fotos reales y 29 imágenes generadas (SD 1.x, SDXL, FLUX, DALL·E 2, ProGAN):
# 0 falsos positivos en las fotos, ~25 % de aciertos en las generadas. Véase el README.
UMBRAL_RUIDO_MEDIANA = 0.8   # desviación típica del residuo en bloques de 16×16 (mediana)
UMBRAL_RUIDO_P10 = 0.5       # y en el 10 % de bloques más lisos
UMBRAL_PERIODICO = 3.5       # pico logarítmico en la rejilla de 8 px frente a su entorno
UMBRAL_GRAFICO = 0.75        # fracción de píxeles con residuo nulo: capturas, logotipos, ilustraciones planas
LADO_MINIMO = 256
LADO_RECORTE = 1024
MAX_PIXELES = 50_000_000

# Tamaños de salida habituales (sin orden de ancho y alto) de Stable Diffusion, SDXL, DALL·E 3, gpt-image,
# Midjourney, Imagen/Gemini y FLUX
RESOLUCIONES_GENERADOR = {frozenset(p) if p[0] != p[1] else frozenset([p[0]]) for p in [
    (512, 512), (512, 768), (768, 768), (1024, 1024), (2048, 2048), (1152, 896), (1216, 832), (1344, 768),
    (1536, 640), (1024, 1792), (1536, 1024), (1456, 816), (1232, 928), (1344, 896), (1664, 928), (1408, 768),
    (1280, 896), (1248, 832), (1184, 864), (1536, 672), (1360, 768), (1440, 1440)]}


# Resoluciones de pantalla de móviles, tabletas y ordenadores habituales (sin orden de ancho y alto)
PANTALLAS = {frozenset(p) for p in [
    # iPhone
    (640, 1136), (750, 1334), (828, 1792), (1080, 1920), (1125, 2436), (1170, 2532), (1179, 2556), (1206, 2622),
    (1242, 2208), (1242, 2688), (1284, 2778), (1290, 2796), (1320, 2868), (1080, 2340), (1260, 2736),
    # iPad
    (1536, 2048), (1620, 2160), (1640, 2360), (1668, 2224), (1668, 2388), (2048, 2732), (1488, 2266), (2064, 2752),
    # Android
    (720, 1280), (720, 1520), (720, 1600), (1080, 2160), (1080, 2220), (1080, 2280), (1080, 2310), (1080, 2400),
    (1080, 2408), (1080, 2412), (1080, 2424), (1440, 2560), (1440, 2960), (1440, 3040), (1440, 3088), (1440, 3120),
    (1440, 3200), (1344, 2992), (1280, 2856), (1220, 2712), (1260, 2800), (1116, 2484), (1240, 2772),
    # Ordenadores
    (1280, 720), (1280, 800), (1366, 768), (1440, 900), (1536, 864), (1600, 900), (1680, 1050), (1920, 1080),
    (1920, 1200), (2560, 1440), (2560, 1600), (2560, 1664), (2880, 1800), (2940, 1912), (3024, 1964), (3456, 2234),
    (3840, 2160), (2736, 1824), (2256, 1504), (2880, 1920), (3000, 2000), (5120, 2880), (3440, 1440)]}

RE_CAPTURA_META = [
    ("macOS / iOS", re.compile(rb"<exif:UserComment>\s*(?:<rdf:Alt>\s*<rdf:li[^>]*>)?\s*Screenshot", 2)),
    ("GNOME", re.compile(rb"gnome-screenshot", 2)),
    ("KDE Spectacle", re.compile(rb"spectacle", 2)),
    ("ShareX", re.compile(rb"sharex", 2)),
    ("Greenshot", re.compile(rb"greenshot", 2)),
    ("Flameshot", re.compile(rb"flameshot", 2)),
    ("Snipping Tool", re.compile(rb"snipping ?tool|snip & sketch|recortes", 2)),
]
RE_CAPTURA_NOMBRE = re.compile(
    r"screen ?shot|captura|pantallazo|screen_?\d|scr_\d|snip|recorte|whatsapp image", 2)


def origen_captura(d: bytes, nombre: str) -> str:
    """Programa o sistema que hizo la captura, según sus metadatos o su nombre de fichero."""
    cabecera = d[:300_000]
    for origen, patron in RE_CAPTURA_META:
        if patron.search(cabecera):
            return origen
    if RE_CAPTURA_NOMBRE.search(nombre.rsplit("/", 1)[-1]):
        return "nombre"
    return ""


def es_pantalla(tam: tuple[int, int] | None) -> bool:
    return bool(tam) and frozenset(tam) in PANTALLAS


def sin_perdida(d: bytes) -> bool:
    """PNG, WebP sin pérdida, TIFF o BMP: formatos en los que no debería haber rastro de JPEG."""
    return (d[:8] == b"\x89PNG\r\n\x1a\n" or (d[:4] == b"RIFF" and d[8:16] == b"WEBPVP8L")
            or d[:4] in (b"II*\x00", b"MM\x00*") or d[:2] == b"BM")


def disponible() -> bool:
    try:
        import numpy  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    return True


# ---------------------------------------------------------------------------
# Solo biblioteca estándar
# ---------------------------------------------------------------------------

def dimensiones(d: bytes) -> tuple[int, int] | None:
    """Ancho y alto leídos de la cabecera (JPEG, PNG, WebP), sin decodificar la imagen."""
    if d[:8] == b"\x89PNG\r\n\x1a\n" and d[12:16] == b"IHDR":
        return struct.unpack(">II", d[16:24])
    if d[:4] == b"RIFF" and d[8:12] == b"WEBP":
        tipo = d[12:16]
        if tipo == b"VP8X" and len(d) >= 30:
            return 1 + int.from_bytes(d[24:27], "little"), 1 + int.from_bytes(d[27:30], "little")
        if tipo == b"VP8 " and len(d) >= 30:
            return struct.unpack("<H", d[26:28])[0] & 0x3FFF, struct.unpack("<H", d[28:30])[0] & 0x3FFF
        if tipo == b"VP8L" and len(d) >= 25:
            bits = int.from_bytes(d[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        return None
    if d[:3] == b"\xff\xd8\xff":
        i = 2
        while i + 9 < len(d) and d[i] == 0xFF:
            marcador = d[i + 1]
            if marcador in (0xD8, 0x01) or 0xD0 <= marcador <= 0xD7:
                i += 2
                continue
            largo = struct.unpack(">H", d[i + 2:i + 4])[0]
            if 0xC0 <= marcador <= 0xCF and marcador not in (0xC4, 0xC8, 0xCC):
                alto, ancho = struct.unpack(">HH", d[i + 5:i + 9])
                return ancho, alto
            if marcador == 0xDA or largo < 2:
                break
            i += 2 + largo
    return None


def resolucion_generador(tam: tuple[int, int] | None) -> bool:
    if not tam:
        return False
    clave = frozenset(tam) if tam[0] != tam[1] else frozenset([tam[0]])
    return clave in RESOLUCIONES_GENERADOR


def camara_exif(bloques_exif: list[bytes]) -> str:
    """Marca y modelo de la cámara (IFD0 de EXIF), o cadena vacía."""
    for d in bloques_exif:
        if len(d) < 8 or d[:2] not in (b"II", b"MM"):
            continue
        orden = "<" if d[:2] == b"II" else ">"
        ifd = struct.unpack(orden + "I", d[4:8])[0]
        if ifd + 2 > len(d):
            continue
        valores = {}
        for k in range(min(struct.unpack(orden + "H", d[ifd:ifd + 2])[0], 256)):
            e = ifd + 2 + 12 * k
            if e + 12 > len(d):
                break
            etiqueta, tipo, cuenta = struct.unpack(orden + "HHI", d[e:e + 8])
            if etiqueta in (0x010F, 0x0110) and tipo == 2 and 0 < cuenta < 256:
                pos = e + 8 if cuenta <= 4 else struct.unpack(orden + "I", d[e + 8:e + 12])[0]
                valores[etiqueta] = d[pos:pos + cuenta].split(b"\x00")[0].decode("latin-1").strip()
        marca, modelo = valores.get(0x010F, ""), valores.get(0x0110, "")
        if modelo.lower().startswith(marca.lower().split(" ")[0]) and marca:
            marca = ""
        texto = " ".join(x for x in (marca, modelo) if x)
        if texto:
            return texto[:80]
    return ""


# ---------------------------------------------------------------------------
# Con Pillow y NumPy
# ---------------------------------------------------------------------------

def _residuo(np, g):
    """Residuo de alta frecuencia: cada píxel menos la media de sus cuatro vecinos."""
    return g[1:-1, 1:-1] - 0.25 * (g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:])


def _pico_periodico(np, r, lado: int = 128) -> float:
    """Mayor pico (en escala logarítmica) del espectro medio del residuo en la rejilla de 8 px."""
    ventana = np.outer(np.hanning(lado), np.hanning(lado))
    acumulado, n = np.zeros((lado, lado)), 0
    for y in range(0, r.shape[0] - lado + 1, lado):
        for x in range(0, r.shape[1] - lado + 1, lado):
            b = r[y:y + lado, x:x + lado]
            acumulado += np.abs(np.fft.fft2((b - b.mean()) * ventana)) ** 2
            n += 1
    if not n:
        return 0.0
    log = np.log(acumulado / n + 1e-9)
    k = lado // 8
    picos = []
    for fy, fx in [(k, 0), (0, k), (k, k), (2 * k, 0), (0, 2 * k), (k, 2 * k), (2 * k, k), (2 * k, 2 * k), (3 * k, 0), (0, 3 * k)]:
        entorno = [log[(fy + dy) % lado, (fx + dx) % lado] for dy in range(-3, 4) for dx in range(-3, 4) if max(abs(dy), abs(dx)) >= 2]
        picos.append(log[fy % lado, fx % lado] - float(np.median(entorno)))
    return float(max(picos))


def _ruido(np, r, lado: int = 16) -> tuple[float, float]:
    h, w = r.shape
    desviaciones = [r[y:y + lado, x:x + lado].std() for y in range(0, h - lado, lado) for x in range(0, w - lado, lado)]
    if not desviaciones:
        return 0.0, 0.0
    return float(np.percentile(desviaciones, 50)), float(np.percentile(desviaciones, 10))


# ---------------------------------------------------------------------------
# Rastros de JPEG dentro de una imagen sin pérdida (recortes pegados en capturas)
# ---------------------------------------------------------------------------

UMBRAL_ZONA_JPEG = 0.88   # capturas genuinas: ≤ 0,76 en las pruebas; recortes pegados: ≥ 0,96
LADO_TESELA = 128
MIN_COEFICIENTES = 24   # coeficientes con valor por posición DCT para puntuarla
MIN_POSICIONES = 4      # posiciones DCT puntuables para puntuar la tesela
MAX_PIXELES_COMPOSICION = 6_000_000
CANDIDATOS = 3
_POSICIONES = [(0, 1), (1, 0), (1, 1), (0, 2), (2, 0), (1, 2), (2, 1), (0, 3), (3, 0)]


def _matriz_dct(np):
    k, i = np.arange(8)[:, None], np.arange(8)[None, :]
    c = np.cos(np.pi * (2 * i + 1) * k / 16) * np.sqrt(2 / 8)
    c[0] /= np.sqrt(2)
    return c


def _puntuar_tesela(np, c, t) -> float:
    """Cuánto se agrupan los coeficientes DCT de una tesela en múltiplos de un paso de cuantización (huella de JPEG)."""
    por = t.shape[0] // 8
    bloques = (t - 128).reshape(por, 8, por, 8).transpose(0, 2, 1, 3)
    d = c @ bloques @ c.T                                     # DCT 8×8 de cada bloque
    pasos = np.arange(3, 41, dtype=float)
    esperado = np.minimum(1, 1.5 / pasos)
    puntos = []
    for y, x in _POSICIONES:
        coef = d[:, :, y, x].ravel()
        coef = coef[np.abs(coef) > 2.0]
        if len(coef) < MIN_COEFICIENTES:
            continue
        cerca = np.abs(coef[:, None] - pasos * np.round(coef[:, None] / pasos)) < 0.75
        puntos.append(float(((cerca.mean(0) - esperado) / (1 - esperado)).max()))
    return float(np.median(puntos)) if len(puntos) >= MIN_POSICIONES else -1.0


def _desplazamientos_rejilla(np, t) -> set[tuple[int, int]]:
    """Desplazamientos (dx, dy) candidatos de la rejilla de 8 px: donde más se concentran los saltos entre bloques."""
    dh = np.abs(np.diff(t, axis=1)).mean(0)            # salto entre la columna j y j+1
    dv = np.abs(np.diff(t, axis=0)).mean(1)
    perfil_x = np.array([dh[(np.arange(len(dh)) + 1) % 8 == k].mean() for k in range(8)])
    perfil_y = np.array([dv[(np.arange(len(dv)) + 1) % 8 == k].mean() for k in range(8)])
    return {(int(x), int(y)) for x in np.argsort(-perfil_x)[:CANDIDATOS] for y in np.argsort(-perfil_y)[:CANDIDATOS]} | {(0, 0)}


def zonas_jpeg(np, g) -> dict:
    """Teselas de 128 px cuyo contenido pasó por JPEG, con el desplazamiento de su rejilla."""
    h, w = g.shape
    origen = (0, 0)
    if h * w > MAX_PIXELES_COMPOSICION:  # recorte central para acotar el tiempo
        escala = (MAX_PIXELES_COMPOSICION / (h * w)) ** 0.5
        nh, nw = int(h * escala), int(w * escala)
        origen = ((w - nw) // 2, (h - nh) // 2)
        g = g[origen[1]:origen[1] + nh, origen[0]:origen[0] + nw]
        h, w = g.shape
    c = _matriz_dct(np)
    lado = LADO_TESELA
    con_textura, marcadas = 0, []
    paso = lado // 2  # teselas solapadas: un recorte pegado no tiene por qué caer alineado con ellas
    for y0 in range(0, h - lado - 8 + 1, paso):
        for x0 in range(0, w - lado - 8 + 1, paso):
            zona = g[y0:y0 + lado + 8, x0:x0 + lado + 8]
            if zona.std() < 2:  # lisa: sin información
                continue
            mejor, rejilla = -1.0, (0, 0)
            for dx, dy in _desplazamientos_rejilla(np, zona):
                valor = _puntuar_tesela(np, c, zona[dy:dy + lado, dx:dx + lado])
                if valor > mejor:
                    mejor, rejilla = valor, (dx, dy)
            if mejor > -1:
                con_textura += 1
            if mejor >= UMBRAL_ZONA_JPEG:
                marcadas.append({"x": origen[0] + x0 + rejilla[0], "y": origen[1] + y0 + rejilla[1],
                                 "puntuacion": round(mejor, 2), "rejilla": rejilla})
    return {"teselas": con_textura, "marcadas": marcadas}


def medir(d: bytes) -> dict | None:
    """Lecturas de píxeles de la imagen, o None si no se puede decodificar."""
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = MAX_PIXELES
    try:
        with Image.open(io.BytesIO(d)) as imagen:
            w, h = imagen.size
            if min(h, w) < LADO_MINIMO:
                return {"aplicable": False, "motivo": "pequena"}
            # Recorte central sin reescalar: reducir la imagen borraría el ruido que se quiere medir
            n = min(LADO_RECORTE, h, w)
            n -= n % 8
            y, x = (h - n) // 2 // 8 * 8, (w - n) // 2 // 8 * 8
            recorte = imagen.convert("RGB").crop((x, y, x + n, y + n))
            g = np.asarray(recorte, dtype=np.float64).mean(axis=2)
    except (OSError, ValueError, Image.DecompressionBombError, SyntaxError):
        return None
    r = _residuo(np, g)
    plano = float((np.abs(r) < 0.5).mean())
    mediana, p10 = _ruido(np, r)
    if plano >= UMBRAL_GRAFICO or mediana == 0:
        return {"aplicable": False, "motivo": "grafico", "plano": round(plano, 2)}
    return {"aplicable": True, "ruido_mediana": round(mediana, 2), "ruido_p10": round(p10, 2),
            "periodico": round(_pico_periodico(np, r), 2), "plano": round(plano, 2)}


def _gris_completo(d: bytes):
    """Imagen entera en escala de grises (recortada al centro si es muy grande), o None."""
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = MAX_PIXELES
    try:
        with Image.open(io.BytesIO(d)) as imagen:
            w, h = imagen.size
            if w * h > MAX_PIXELES_COMPOSICION:
                escala = (MAX_PIXELES_COMPOSICION / (w * h)) ** 0.5
                nw, nh = int(w * escala), int(h * escala)
                x0, y0 = (w - nw) // 2, (h - nh) // 2
                recorte = imagen.convert("RGB").crop((x0, y0, x0 + nw, y0 + nh))
                desplazamiento = (x0, y0)
            else:
                recorte, desplazamiento = imagen, (0, 0)
            return np.asarray(recorte.convert("L"), dtype=np.float64), desplazamiento
    except (OSError, ValueError, Image.DecompressionBombError, SyntaxError):
        return None


def _agrupar(marcadas: list[dict]) -> list[dict]:
    """Une teselas marcadas que se tocan y tienen la misma rejilla en rectángulos."""
    grupos: list[dict] = []
    for m in marcadas:
        x1, y1, x2, y2 = m["x"], m["y"], m["x"] + LADO_TESELA, m["y"] + LADO_TESELA
        for g in grupos:
            if g["rejilla"] == m["rejilla"] and x1 <= g["x2"] and x2 >= g["x1"] and y1 <= g["y2"] and y2 >= g["y1"]:
                g.update(x1=min(g["x1"], x1), y1=min(g["y1"], y1), x2=max(g["x2"], x2), y2=max(g["y2"], y2),
                         puntuacion=max(g["puntuacion"], m["puntuacion"]))
                break
        else:
            grupos.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2, "rejilla": m["rejilla"], "puntuacion": m["puntuacion"]})
    return grupos[:8]


def lectura_captura(d: bytes, nombre: str, tam, grafico: bool, con_pixeles: bool) -> dict:
    """Lectura propia de capturas de pantalla: origen, tamaño de pantalla y zonas que pasaron por JPEG."""
    salida = {"origen": origen_captura(d, nombre), "pantalla": es_pantalla(tam), "parece_captura": grafico,
              "sin_perdida": sin_perdida(d), "zonas_jpeg": [], "jpeg_completa": False, "analizada": False}
    salida["parece_captura"] = grafico or bool(salida["origen"]) or salida["pantalla"]
    if con_pixeles and salida["sin_perdida"] and tam and min(tam) >= LADO_TESELA + 8:
        import numpy as np
        gris = _gris_completo(d)
        if gris is not None:
            resultado = zonas_jpeg(np, gris[0])
            salida["analizada"] = True
            marcadas = resultado["marcadas"]
            if marcadas and resultado["teselas"] and len(marcadas) / resultado["teselas"] >= 0.5:
                salida["jpeg_completa"] = True  # toda la imagen pasó por JPEG antes: no apunta a un pegado
            else:
                dx, dy = gris[1]
                for m in marcadas:
                    m["x"] += dx
                    m["y"] += dy
                salida["zonas_jpeg"] = _agrupar(marcadas)
    return salida


def lectura(d: bytes, bloques_exif: list[bytes], con_pixeles: bool, nombre: str = "") -> dict:
    """Todas las lecturas y la conclusión: señales que apuntan a imagen sintética."""
    tam = dimensiones(d)
    salida = {"ancho": tam[0] if tam else None, "alto": tam[1] if tam else None,
              "resolucion_generador": resolucion_generador(tam), "camara": camara_exif(bloques_exif),
              "pixeles": None, "senales": [], "captura": None}
    if con_pixeles:
        salida["pixeles"] = medir(d)
    grafico = (salida["pixeles"] or {}).get("motivo") == "grafico"
    salida["captura"] = lectura_captura(d, nombre, tam, grafico, con_pixeles)
    p = salida["pixeles"] or {}
    if p.get("aplicable"):
        if p["ruido_mediana"] < UMBRAL_RUIDO_MEDIANA and p["ruido_p10"] < UMBRAL_RUIDO_P10:
            salida["senales"].append("ruido")
        if p["periodico"] >= UMBRAL_PERIODICO:
            salida["senales"].append("periodico")
    if salida["resolucion_generador"]:
        salida["senales"].append("resolucion")
    return salida
