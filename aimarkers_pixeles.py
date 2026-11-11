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


def lectura(d: bytes, bloques_exif: list[bytes], con_pixeles: bool) -> dict:
    """Todas las lecturas y la conclusión: señales que apuntan a imagen sintética."""
    tam = dimensiones(d)
    salida = {"ancho": tam[0] if tam else None, "alto": tam[1] if tam else None,
              "resolucion_generador": resolucion_generador(tam), "camara": camara_exif(bloques_exif),
              "pixeles": None, "senales": []}
    if con_pixeles:
        salida["pixeles"] = medir(d)
    p = salida["pixeles"] or {}
    if p.get("aplicable"):
        if p["ruido_mediana"] < UMBRAL_RUIDO_MEDIANA and p["ruido_p10"] < UMBRAL_RUIDO_P10:
            salida["senales"].append("ruido")
        if p["periodico"] >= UMBRAL_PERIODICO:
            salida["senales"].append("periodico")
    if salida["resolucion_generador"]:
        salida["senales"].append("resolucion")
    return salida
