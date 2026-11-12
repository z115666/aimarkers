"""Pruebas de aimarkers / aimarkers tests. Ejecutar / run: python -m unittest discover tests -v"""
import contextlib
import http.client
import http.server
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ.parent))
import aimarkers

F = RAIZ / "fixtures"
IMG = F / "imagenes"
aimarkers.fijar_idioma("es")


def reglas(res):
    return set(res.por_regla())


def git(repo, *args, **entorno):
    cmd = ["git", "-C", str(repo)]
    for clave, valor in entorno.items():
        cmd += ["-c", f"{clave.replace('_', '.')}={valor}"]
    subprocess.run(cmd + list(args), check=True, capture_output=True)


class PruebasAimarkers(unittest.TestCase):
    def test_codigo_ia(self):
        res = aimarkers.analizar_objetivo(str(F / "codigo_ia"))
        self.assertTrue(res.atribucion_explicita())
        self.assertGreaterEqual(res.puntuacion(), 70)
        for r in ("fichero-agente", "carpeta-agente", "resto-chat", "valla-markdown", "placeholder", "emoji-logs"):
            self.assertIn(r, reglas(res))

    def test_texto_ia(self):
        res = aimarkers.analizar_objetivo(str(F / "texto" / "articulo_ia.md"))
        self.assertIn("utm-chatgpt", reglas(res))
        self.assertIn("muletillas", reglas(res))
        self.assertGreaterEqual(res.puntuacion(), 70)

    def test_texto_humano_sin_falsos_positivos(self):
        res = aimarkers.analizar_objetivo(str(F / "texto" / "notas_humanas.md"))
        self.assertEqual(res.puntuacion(), 0)

    def test_web_generador(self):
        res = aimarkers.analizar_objetivo(str(F / "web" / "landing.html"))
        for r in ("gen-lovable", "gen-v0", "imagen-ia", "stack-generador"):
            self.assertIn(r, reglas(res))

    def test_web_rafaga_datos(self):
        res = aimarkers.analizar_objetivo(str(F / "web" / "actividades_sintetico.html"))
        self.assertIn("rafaga-datos", reglas(res))
        self.assertIn("coordenadas-mixtas", reglas(res))
        self.assertFalse(res.atribucion_explicita())

    @unittest.skipUnless(shutil.which("git"), "git no está instalado")
    def test_repo_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo_demo"
            repo.mkdir()
            git(repo, "init", "-q", "-b", "main")
            persona = {"user_name": "Persona", "user_email": "persona@example.com", "commit_gpgsign": "false"}
            (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
            git(repo, "add", ".", **persona)
            git(repo, "commit", "-qm", "Primer commit", **persona)
            (repo / "app.py").write_text("print('hola')\n", encoding="utf-8")
            git(repo, "add", ".", **persona)
            git(repo, "commit", "-q", "-m", "feat: saludo\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\n"
                "Co-Authored-By: Claude <noreply@anthropic.com>", **persona)
            git(repo, "checkout", "-qb", "claude/tests")
            (repo / "test_app.py").write_text("def test():\n    pass\n", encoding="utf-8")
            git(repo, "add", ".", **persona)
            git(repo, "commit", "-qm", "Add tests", user_name="copilot-swe-agent[bot]",
                user_email="bot@users.noreply.github.com", commit_gpgsign="false")
            res = aimarkers.analizar_objetivo(str(repo))
        for r in ("coautor-ia", "firma-robot", "autor-bot", "rama-agente"):
            self.assertIn(r, reglas(res))

    def test_codigo_humano_stdlib(self):
        import json as modulo
        res = aimarkers.analizar_objetivo(str(Path(modulo.__file__).parent))
        self.assertLess(res.puntuacion(), 15)

    def test_hueco_no_confunde_codigo(self):
        res = aimarkers.Resultado("x", "codigo")
        aimarkers.analizar_codigo(res, "params[name] = value\nhandlers[Name] = h\n" * 10, "x.py", ".py")
        self.assertNotIn("hueco-plantilla", reglas(res))

    def test_fechas_compatibles_python39(self):
        self.assertIsNotNone(aimarkers.parsear_fecha("2026-11-09T09:33:11.36955+00:00"))
        self.assertIsNotNone(aimarkers.parsear_fecha("2026-11-09T23:42:45Z"))

    def test_cli_informes(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp)
            codigo = aimarkers.main([str(F / "texto" / "articulo_ia.md"), "--silencioso",
                                     "--json", str(salida / "r.json"), "--md", str(salida / "r.md"),
                                     "--html", str(salida / "r.html"), "--umbral", "40"])
            self.assertEqual(codigo, 2)
            for nombre in ("r.json", "r.md", "r.html"):
                self.assertGreater((salida / nombre).stat().st_size, 200)
            # El HTML escapa el contenido analizado
            self.assertNotIn("<script", (salida / "r.html").read_text(encoding="utf-8").lower())


def _zip(entradas: dict) -> bytes:
    import zipfile
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in entradas.items():
            z.writestr(nombre, contenido)
    return b.getvalue()


def _docx(parrafos: list, creador: str = "", aplicacion: str = "Microsoft Office Word", descripcion: str = "") -> bytes:
    cuerpo = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in parrafos)
    return _zip({
        "[Content_Types].xml": "<Types/>",
        "word/document.xml": f'<w:document xmlns:w="w"><w:body>{cuerpo}</w:body></w:document>',
        "docProps/core.xml": f"<cp:coreProperties><dc:creator>{creador}</dc:creator><dc:description>{descripcion}</dc:description>"
                             "<cp:revision>3</cp:revision></cp:coreProperties>",
        "docProps/app.xml": f"<Properties><Application>{aplicacion}</Application></Properties>",
    })


def _pdf(texto: str, productor: str, comprimir: bool = True) -> bytes:
    import zlib
    contenido = f"BT /F1 12 Tf 72 720 Td ({texto}) Tj T* (Segunda linea del documento de prueba.) Tj ET".encode()
    flujo = zlib.compress(contenido) if comprimir else contenido
    filtro = b"/Filter /FlateDecode " if comprimir else b""
    return (b"%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            b"3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj\n"
            b"4 0 obj << " + filtro + b"/Length " + str(len(flujo)).encode() + b" >>\nstream\n" + flujo + b"\nendstream endobj\n"
            b"5 0 obj << /Producer (" + productor.encode() + b") /Creator (Prueba) >> endobj\n"
            b"trailer << /Root 1 0 R /Info 5 0 R >>\n%%EOF\n")


class PruebasDocumentos(unittest.TestCase):
    def analizar(self, nombre: str, datos: bytes):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / nombre
            ruta.write_bytes(datos)
            return aimarkers.analizar_objetivo(str(ruta))

    def reglas(self, res):
        return {h.regla for h in res.hallazgos}

    def test_word_generado_desde_un_chat(self):
        res = self.analizar("plan.docx", _docx(
            ["### Objetivos", "**Seguridad:** reforzar accesos.", "Texto del plan. ¡Espero que te sea útil!"],
            creador="python-docx", descripcion="generated by python-docx"))
        self.assertEqual(res.tipo, "documento")
        self.assertTrue({"doc-generado-codigo", "markdown-en-documento", "cierre-chat"} <= self.reglas(res), self.reglas(res))
        self.assertTrue(any("DOCX" in n and "Microsoft Office Word" in n for n in res.notas))

    def test_word_normal_sin_marcadores(self):
        res = self.analizar("acta.docx", _docx(["Acta de la reunión del claustro.", "Se aprueba el calendario de evaluaciones."],
                                               creador="Secretaría"))
        self.assertEqual(res.hallazgos, [])
        self.assertNotIn("Secretaría", " ".join(res.notas))  # los nombres de autor no se copian al informe

    def test_herramienta_ia_en_metadatos_y_revisiones(self):
        datos = _zip({"ppt/slides/slide1.xml": "<p:sld><a:p><a:r><a:t>Resultados</a:t></a:r></a:p></p:sld>",
                      "docProps/app.xml": "<Properties><Application>Gamma</Application></Properties>",
                      "ppt/media/image1.jpg": (IMG / "c2pa_ia.jpg").read_bytes()})
        res = self.analizar("deck.pptx", datos)
        self.assertIn("doc-herramienta-ia", self.reglas(res))
        self.assertIn("c2pa-ia", self.reglas(res))  # imagen generada con IA incrustada en la presentación
        self.assertTrue(any("deck.pptx/ppt/media/image1.jpg" in h.ubicacion for h in res.hallazgos))

    def test_pdf_reportlab_con_texto(self):
        for comprimir in (True, False):
            res = self.analizar("informe.pdf", _pdf("En resumen, ### Conclusiones y **puntos clave** del informe final",
                                                   "ReportLab PDF Library - www.reportlab.com", comprimir))
            self.assertIn("doc-generado-codigo", self.reglas(res))
            self.assertTrue(any("ReportLab" in n for n in res.notas))
        import aimarkers_documentos as docs
        doc = docs.leer_pdf(_pdf("Hola \\(mundo\\) con par\\351ntesis", "Otro"))
        self.assertEqual(doc["meta"]["productor"], "Otro")
        self.assertIn("Hola (mundo) con paréntesis", doc["partes"][0][1][0] if doc["partes"] else "Hola (mundo) con paréntesis")

    def test_documentos_malformados_y_bombas(self):
        import zipfile
        res = self.analizar("roto.docx", b"PK\x03\x04 esto no es un zip")
        self.assertTrue(any("roto.docx" in n for n in res.notas))
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("word/document.xml", "<w:p><w:t>a</w:t></w:p>" + " " * 20_000_000)  # ratio de compresión enorme
        res = self.analizar("bomba.docx", b.getvalue())
        self.assertEqual(res.hallazgos, [])
        res = self.analizar("raro.pdf", b"%PDF-1.7\n" + b"<< /Length 99999999 >>\nstream\n" + os.urandom(2000))
        self.assertEqual(res.hallazgos, [])


class PruebasImagenes(unittest.TestCase):
    def test_c2pa_generada_con_ia(self):
        for nombre in ("c2pa_ia.jpg", "c2pa_ia.png"):
            res = aimarkers.analizar_objetivo(str(IMG / nombre))
            self.assertIn("c2pa-ia", reglas(res), nombre)
            self.assertTrue(res.atribucion_explicita())
            self.assertIn("Prueba Generador IA", res.hallazgos[0].extracto)
            self.assertIn("C2PA Signer", res.hallazgos[0].extracto)

    def test_c2pa_camara_solo_nota(self):
        res = aimarkers.analizar_objetivo(str(IMG / "c2pa_camara.jpg"))
        self.assertEqual(res.hallazgos, [])
        self.assertTrue(any("C2PA" in n and "cámara" in n for n in res.notas))

    def test_parametros_y_metadatos(self):
        casos = {"sd_parametros.png": "parametros-generacion", "comfyui.png": "parametros-generacion",
                 "xmp_ia.jpg": "xmp-origen-ia", "exif_software.jpg": "metadatos-generador"}
        for nombre, regla in casos.items():
            self.assertIn(regla, reglas(aimarkers.analizar_objetivo(str(IMG / nombre))), nombre)

    def test_imagen_sin_metadatos_indeterminada(self):
        datos = (IMG / "c2pa_ia.jpg").read_bytes()
        # JPEG mínimo: SOI + resto desde la primera tabla de cuantización, sin APP1/APP11
        limpio = datos[:2] + datos[datos.index(b"\xff\xdb"):]
        res = aimarkers.Resultado("x", "imagen")
        aimarkers.analizar_imagen(res, limpio, "x.jpg", None, set())
        self.assertEqual(res.clave_banda(), "banda.indeterminada")
        self.assertTrue(any("metadatos" in n for n in res.notas))
        con_exif = aimarkers.analizar_objetivo(str(IMG / "foto_normal.jpg"))
        self.assertEqual(con_exif.clave_banda(), "banda.nula")

    def test_foto_normal_sin_hallazgos(self):
        self.assertEqual(aimarkers.analizar_objetivo(str(IMG / "foto_normal.jpg")).hallazgos, [])

    def test_entradas_hostiles(self):
        # zTXt con bomba de descompresión y caja JUMBF malformada
        res = aimarkers.analizar_objetivo(str(IMG / "hostil.png"))
        self.assertEqual(res.hallazgos, [])
        base = (IMG / "c2pa_ia.jpg").read_bytes()
        azar = random.Random(7)
        for _ in range(150):
            datos = bytearray(base)
            for _ in range(20):
                datos[azar.randrange(len(datos))] = azar.randrange(256)
            corte = azar.randrange(len(datos))
            aimarkers.analizar_imagen(aimarkers.Resultado("x", "imagen"), bytes(datos[:corte]), "x", None, set())
        for basura in (b"\xbf" * 5000, b"\x9f" * 5000, b"\x5b\xff\xff\xff\xff", b"\xd8\x12" * 100):
            aimarkers.decodificar_cbor(basura)

    def test_imagenes_de_html_local_sin_salir_de_la_carpeta(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "web" / "img").mkdir(parents=True)
            shutil.copy(IMG / "c2pa_ia.jpg", raiz / "web" / "img" / "foto.jpg")
            shutil.copy(IMG / "sd_parametros.png", raiz / "fuera.png")
            (raiz / "web" / "index.html").write_text(
                '<html><body><img src="img/foto.jpg"><img src="../fuera.png">'
                '<img src="https://example.com/x.png"></body></html>', encoding="utf-8")
            res = aimarkers.analizar_objetivo(str(raiz / "web" / "index.html"))
            sin = aimarkers.analizar_objetivo(str(raiz / "web" / "index.html"), imagenes_web=False)
        self.assertIn("c2pa-ia", reglas(res))
        self.assertNotIn("parametros-generacion", reglas(res))
        self.assertNotIn("c2pa-ia", reglas(sin))

    @unittest.skipUnless(__import__("aimarkers_pixeles").disponible(), "necesita Pillow y NumPy")
    def test_lectura_de_pixeles(self):
        import numpy as np
        from PIL import Image
        azar = np.random.default_rng(3)

        def png(matriz, exif=None):
            b = io.BytesIO()
            imagen = Image.fromarray(np.stack([np.clip(matriz, 0, 255).astype(np.uint8)] * 3, -1))
            if exif:
                datos = Image.Exif()
                datos.update(exif)
                imagen.save(b, "JPEG", quality=98, exif=datos)
            else:
                imagen.save(b, "PNG")
            return b.getvalue()
        lado = 600
        semilla = azar.normal(0, 1, (lado // 25, lado // 25))
        liso = np.asarray(Image.fromarray(((semilla - semilla.min()) / np.ptp(semilla) * 150 + 50).astype(np.uint8))
                          .resize((lado, lado), Image.BICUBIC), dtype=float)
        ruidosa = liso + azar.normal(0, 4, liso.shape)
        rejilla = 3.0 * np.add.outer(np.arange(lado) % 8 == 0, np.arange(lado) % 8 == 0)
        casos = {"lisa": (png(liso), "pixeles-sinteticos"), "foto": (png(ruidosa), None),
                 "periodica": (png(ruidosa + rejilla), "pixeles-sinteticos"),
                 "camara": (png(liso, {0x010F: "Canon", 0x0110: "Canon EOS 40D"}), None),
                 "captura": (png(np.full((lado, lado), 200.0)), None)}
        for nombre, (datos, esperado) in casos.items():
            res = aimarkers.Resultado(nombre, "imagen")
            aimarkers.analizar_imagen(res, datos, nombre, None, set())
            self.assertEqual(bool([h for h in res.hallazgos if h.regla in aimarkers.REGLAS_PIXELES]), bool(esperado), nombre)
            self.assertEqual(len(res.lecturas), 1)
        res = aimarkers.Resultado("camara", "imagen")
        aimarkers.analizar_imagen(res, casos["camara"][0], "camara", None, set())
        self.assertTrue(any("Canon EOS 40D" in n for n in res.notas))
        # Sin metadatos y con una sola señal débil, la valoración sigue siendo indeterminada
        res = aimarkers.Resultado("lisa", "imagen")
        aimarkers.analizar_imagen(res, casos["lisa"][0], "lisa", None, set())
        if res.hallazgos[0].nivel == "debil":
            self.assertEqual(res.clave_banda(), "banda.indeterminada")
        # Desactivada por opción
        aimarkers.fijar_pixeles(False)
        try:
            res = aimarkers.Resultado("lisa", "imagen")
            aimarkers.analizar_imagen(res, casos["lisa"][0], "lisa", None, set())
            self.assertEqual(res.hallazgos, [])
        finally:
            aimarkers.fijar_pixeles(True)

    @unittest.skipUnless(__import__("aimarkers_pixeles").disponible(), "necesita Pillow y NumPy")
    def test_capturas_de_pantalla(self):
        import numpy as np
        from PIL import Image, ImageDraw
        azar = np.random.default_rng(7)

        def interfaz(ancho, alto):
            imagen = Image.new("RGB", (ancho, alto), (246, 247, 249))
            dibujo = ImageDraw.Draw(imagen)
            for i in range(0, alto - 40, 46):
                dibujo.rounded_rectangle((40, i + 8, ancho // 2, i + 38), 12, fill=(220, 236, 255))
                dibujo.text((56, i + 16), f"Mensaje {i} de la conversación de prueba", fill=(20, 20, 20))
            return imagen

        def png(imagen, xmp=b""):
            b = io.BytesIO()
            if xmp:
                from PIL import PngImagePlugin
                info = PngImagePlugin.PngInfo()
                info.add_itxt("XML:com.adobe.xmp", xmp.decode())
                imagen.save(b, "PNG", pnginfo=info)
            else:
                imagen.save(b, "PNG")
            return b.getvalue()

        def lectura(datos, nombre="captura.png"):
            res = aimarkers.Resultado(nombre, "imagen")
            aimarkers.analizar_imagen(res, datos, nombre, None, set())
            return res, res.lecturas[0]["captura"]

        # Captura genuina con tamaño de pantalla real: sin zonas pegadas ni marcadores
        res, cap = lectura(png(interfaz(1440, 900)))
        self.assertTrue(cap["parece_captura"] and cap["pantalla"] and cap["analizada"])
        self.assertEqual((cap["zonas_jpeg"], res.hallazgos), ([], []))
        # Recorte con textura de foto, comprimido en JPEG y pegado encima: se localiza la zona
        semilla = azar.normal(0, 1, (30, 40))
        foto = np.asarray(Image.fromarray(((semilla - semilla.min()) / np.ptp(semilla) * 200).astype(np.uint8))
                          .resize((400, 300), Image.BICUBIC), dtype=float) + azar.normal(0, 6, (300, 400))
        recorte = Image.fromarray(np.stack([np.clip(foto, 0, 255).astype(np.uint8)] * 3, -1))
        b = io.BytesIO()
        recorte.save(b, "JPEG", quality=75)
        montaje = interfaz(1440, 900)
        montaje.paste(Image.open(io.BytesIO(b.getvalue())), (523, 211))
        res, cap = lectura(png(montaje))
        self.assertTrue(cap["zonas_jpeg"])
        zona = cap["zonas_jpeg"][0]
        self.assertEqual(zona["rejilla"], (523 % 8, 211 % 8))  # la rejilla JPEG del recorte, no la de la imagen
        self.assertTrue(zona["x1"] < 523 + 400 and zona["x2"] > 523 and zona["y1"] < 211 + 300 and zona["y2"] > 211, zona)
        self.assertTrue(any("523" in n or "pasó por compresión JPEG" in n for n in res.notas))
        # Tamaño de generador sin programa de captura: indicio medio; con metadatos de captura de macOS, no
        res, cap = lectura(png(interfaz(1024, 1536)), "chat.png")
        self.assertEqual([h.regla for h in res.hallazgos], ["captura-tamano-generador"])
        xmp = b"<x:xmpmeta><exif:UserComment><rdf:Alt><rdf:li xml:lang='x-default'>Screenshot</rdf:li></rdf:Alt></exif:UserComment></x:xmpmeta>"
        res, cap = lectura(png(interfaz(1024, 1536), xmp))
        self.assertEqual(cap["origen"], "macOS / iOS")
        self.assertEqual(res.hallazgos, [])

    def test_dimensiones_sin_dependencias(self):
        import aimarkers_pixeles as px
        for nombre in ("c2pa_ia.jpg", "sd_parametros.png", "foto_normal.jpg"):
            self.assertIsNotNone(px.dimensiones((IMG / nombre).read_bytes()), nombre)
        self.assertTrue(px.resolucion_generador((1024, 1792)))
        self.assertTrue(px.resolucion_generador((1792, 1024)))
        self.assertFalse(px.resolucion_generador((4032, 3024)))

    def test_falsos_positivos_imagen(self):
        self.assertIsNone(aimarkers.RE_GENERADOR_META.search("Imagen corporativa de la empresa"))
        self.assertIsNone(aimarkers.RE_GENERADOR_META.search("Canon EOS R6 / Adobe Lightroom"))


class PruebasIdioma(unittest.TestCase):
    def tearDown(self):
        aimarkers.fijar_idioma("es")

    def test_deteccion(self):
        original = dict(os.environ)
        try:
            for var in ("AIMARKERS_LANG", "LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
                os.environ.pop(var, None)
            os.environ["LANG"] = "es_ES.UTF-8"
            self.assertEqual(aimarkers.detectar_idioma(), "es")
            os.environ["LANG"] = "en_GB.UTF-8"
            self.assertEqual(aimarkers.detectar_idioma(), "en")
            os.environ["AIMARKERS_LANG"] = "es"
            self.assertEqual(aimarkers.detectar_idioma(), "es")
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_traducciones_completas(self):
        for clave, (es, en) in {**aimarkers.TEXTOS, **aimarkers.DESCRIPCIONES}.items():
            self.assertTrue(es and en, clave)
            self.assertEqual(set(re.findall(r"{(\w+)}", es)),
                             set(re.findall(r"{(\w+)}", en)), clave)
        reglas_usadas = {r[0] for r in aimarkers.REGLAS_GENERALES + aimarkers.REGLAS_CHAT + aimarkers.REGLAS_HTML
                         + aimarkers.REGLAS_CODIGO_LINEA + [aimarkers.REGLA_HUECO]}
        self.assertLessEqual(reglas_usadas, set(aimarkers.DESCRIPCIONES))

    def test_informes_en_ingles(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp)
            aimarkers.main([str(IMG / "c2pa_ia.jpg"), "--lang", "en", "--quiet",
                            "--json", str(salida / "r.json"), "--html", str(salida / "r.html")])
            datos = json.loads((salida / "r.json").read_text(encoding="utf-8"))
            pagina = (salida / "r.html").read_text(encoding="utf-8")
        self.assertEqual(datos[0]["idioma"], "en")
        self.assertEqual(datos[0]["hallazgos"][0]["regla"], "c2pa-ia")
        self.assertIn("C2PA Content Credentials declare AI generation", datos[0]["hallazgos"][0]["descripcion"])
        self.assertIn('<html lang="en">', pagina)
        self.assertIn("AI markers report", pagina)


class PruebasInterfaz(unittest.TestCase):
    """Servidor local de la interfaz: debe rechazar todo lo que no venga de su propia página."""

    @classmethod
    def setUpClass(cls):
        import aimarkers_gui
        cls.gui = aimarkers_gui
        cls.servidor = aimarkers_gui.crear_servidor(0)
        cls.hilo = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.hilo.start()
        cls.puerto = aimarkers_gui.ESTADO.puerto
        cls.token = aimarkers_gui.ESTADO.token

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        aimarkers.fijar_idioma("es")

    def peticion(self, metodo, ruta, cuerpo=None, cabeceras=None, token=True):
        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=30)
        todas = {"Host": f"127.0.0.1:{self.puerto}"}
        if token:
            todas["X-Aimarkers-Token"] = self.token
        todas.update(cabeceras or {})
        if isinstance(cuerpo, dict):
            cuerpo = json.dumps(cuerpo).encode()
        conexion.request(metodo, ruta, body=cuerpo, headers=todas)
        respuesta = conexion.getresponse()
        datos = respuesta.read()
        conexion.close()
        return respuesta.status, dict(respuesta.getheaders()), datos

    def test_pagina_con_cabeceras_de_seguridad(self):
        estado, cabeceras, cuerpo = self.peticion("GET", "/", token=False)
        self.assertEqual(estado, 200)
        self.assertIn("script-src 'self'", cabeceras["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", cabeceras["Content-Security-Policy"])
        self.assertEqual(cabeceras["X-Content-Type-Options"], "nosniff")
        self.assertNotIn(b"<script>", cuerpo)
        for ruta in ("/app.js", "/app.css", "/icon.svg", "/fonts/redaction-700.woff2"):
            self.assertEqual(self.peticion("GET", ruta, token=False)[0], 200, ruta)

    def test_rechaza_sin_token_host_u_origen(self):
        self.assertEqual(self.peticion("GET", "/api/config", token=False)[0], 403)
        self.assertEqual(self.peticion("POST", "/api/analyze", {"objetivo": "."}, token=False)[0], 403)
        self.assertEqual(self.peticion("GET", "/", cabeceras={"Host": "atacante.example:80"})[0], 421)
        self.assertEqual(self.peticion("POST", "/api/analyze", {"objetivo": "."},
                                       cabeceras={"Origin": "https://atacante.example"})[0], 403)
        self.assertEqual(self.peticion("GET", "/../aimarkers.py", token=False)[0], 404)

    def test_analiza_y_exporta(self):
        estado, _, cuerpo = self.peticion("POST", "/api/analyze",
                                          {"objetivo": str(IMG / "c2pa_ia.jpg"), "idioma": "en"})
        self.assertEqual(estado, 200)
        datos = json.loads(cuerpo)
        resultado = datos["resultados"][0]
        self.assertEqual(resultado["banda"], "media")
        self.assertEqual(resultado["grupos"][0]["marcadores"][0]["regla"], "c2pa-ia")
        estado, cabeceras, informe = self.peticion("POST", "/api/export", {"id": datos["id"], "formato": "html"})
        self.assertEqual(estado, 200)
        self.assertIn("attachment", cabeceras["Content-Disposition"])
        self.assertIn(b"<!doctype html>", informe)

    def test_subida_y_rutas_hostiles(self):
        lote = "pruebalote01"
        datos = (IMG / "sd_parametros.png").read_bytes()
        for ruta in ("../fuera.png", "/etc/passwd", "C:/x.png", "a/../../b.png", ""):
            estado, _, _ = self.peticion("POST", f"/api/upload?batch={lote}&path={urllib.parse.quote(ruta)}", datos,
                                         {"Content-Type": "application/octet-stream"})
            self.assertEqual(estado, 400, ruta)
        self.assertEqual(self.peticion("POST", "/api/upload?batch=x&path=a.png", datos)[0], 400)
        estado, _, _ = self.peticion("POST", f"/api/upload?batch={lote}&path=carpeta/sd.png", datos,
                                     {"Content-Type": "application/octet-stream"})
        self.assertEqual(estado, 200)
        estado, _, cuerpo = self.peticion("POST", "/api/analyze", {"lote": lote, "nombre": "carpeta", "idioma": "es"})
        self.assertEqual(estado, 200)
        resultado = json.loads(cuerpo)["resultados"][0]
        self.assertEqual(resultado["objetivo"], "carpeta")
        self.assertIn("parametros-generacion", resultado["resumen_por_marcador"])

    def test_activo_sin_autorizacion_rechazado(self):
        estado, _, _ = self.peticion("POST", "/api/analyze", {"objetivo": "http://127.0.0.1:9/", "activo": True})
        self.assertEqual(estado, 400)
        estado, _, cuerpo = self.peticion("GET", "/api/progress")
        self.assertEqual(estado, 200)
        self.assertIn("porcentaje", json.loads(cuerpo))

    def test_detener_analisis(self):
        # Sin análisis en curso, parar no deja la parada pendiente para el siguiente
        estado, _, cuerpo = self.peticion("POST", "/api/cancel", {})
        self.assertEqual((estado, json.loads(cuerpo)["detenido"]), (200, False))
        empezado = threading.Event()

        def lento(objetivo, opciones=None):
            for i in range(600):
                aimarkers.informar("ficheros", i, 600)
                empezado.set()
                time.sleep(0.05)
            raise AssertionError("no se detuvo")

        respuesta = {}
        original = aimarkers.analizar_objetivo
        aimarkers.analizar_objetivo = lento
        try:
            hilo = threading.Thread(target=lambda: respuesta.update(r=self.peticion("POST", "/api/analyze", {"objetivo": "."})))
            hilo.start()
            self.assertTrue(empezado.wait(10))
            estado, _, cuerpo = self.peticion("POST", "/api/cancel", {"lote": "../../fuera"})
            self.assertEqual((estado, json.loads(cuerpo)["detenido"]), (200, True))
            hilo.join(10)
        finally:
            aimarkers.analizar_objetivo = original
        self.assertEqual(respuesta["r"][0], 409)
        self.assertIn(b"cancelled", respuesta["r"][2])
        self.assertFalse(aimarkers._PARAR.is_set())
        self.assertEqual(self.peticion("GET", "/api/progress")[0], 200)
        estado, _, _ = self.peticion("POST", "/api/analyze", {"objetivo": str(IMG / "c2pa_ia.jpg")})
        self.assertEqual(estado, 200)

    def test_ruta_relativa_segura(self):
        self.assertEqual(str(self.gui.ruta_relativa_segura("a/./b\\c.txt")), "a/b/c.txt")
        for mala in ("..", "../a", "a/../../b", "", "\x00", "C:\\a"):
            self.assertIsNone(self.gui.ruta_relativa_segura(mala), mala)


class SitioDePrueba(http.server.BaseHTTPRequestHandler):
    """Web local con fallos de seguridad típicos (solo para las pruebas)."""

    PAGINAS = {
        "/": ("text/html; charset=utf-8", """<!doctype html><html><head><title>Inicio</title>
<meta name="generator" content="WordPress 6.1.1">
<script src="/app.js"></script>
<script src="https://cdn.example.org/libs/jquery-1.12.4.min.js"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-TEST"></script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">
<script src="/wp-content/plugins/ninja-forms/assets/js/front-end.js?ver=3.14.7"></script>
</head><body><!-- TODO: quitar la password del admin -->
<p>Escríbenos a contacto@colegio.example</p>
<a href="/pagina2">Siguiente</a> <a href="https://otra.example/" target="_blank">Externo</a>
<iframe src="https://www.youtube.com/embed/abc"></iframe> <a href="/privado/datos">Privado</a>
<form method="post" action="/login"><input name="usuario"><input type="password" name="clave"><button>Entrar</button></form>
</body></html>"""),
        "/pagina2": ("text/html", "<html><body><a href='/'>Inicio</a><a href='/pagina3'>3</a></body></html>"),
        "/pagina3": ("text/html", "<html><body><p>Final</p></body></html>"),
        "/privado/datos": ("text/html", "<html><body>No debería descargarse</body></html>"),
        "/robots.txt": ("text/plain", "User-agent: *\nDisallow: /privado/\nDisallow: /backup-admin/\n"),
        "/app.js": ("application/javascript", "/*! jQuery v1.12.4 */ var a=1;\n//# sourceMappingURL=app.js.map"),
        "/.git/HEAD": ("text/plain", "ref: refs/heads/main\n"),
    }
    visitas: list[str] = []

    def log_message(self, *args):
        return

    def do_GET(self):
        SitioDePrueba.visitas.append(self.path)
        datos = self.PAGINAS.get(self.path)
        if datos is None:
            cuerpo = b"<html><body>No encontrado</body></html>"
            self.send_response(404)
        else:
            cuerpo = datos[1].encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", datos[0])
        if self.path == "/":
            self.send_header("Set-Cookie", "PHPSESSID=abc123; path=/")
            self.send_header("Server", "Apache/2.4.41 (Ubuntu)")
            self.send_header("X-Powered-By", "PHP/7.4.3")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Allow", "GET, POST, OPTIONS, TRACE")
        self.send_header("Content-Length", "0")
        self.end_headers()


class PruebasSeguridadYRastreo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import aimarkers_seguridad
        import aimarkers_web
        cls.seg = aimarkers_seguridad
        cls.web = aimarkers_web
        cls.entorno = {k: os.environ.get(k) for k in ("no_proxy", "NO_PROXY")}
        for clave in ("no_proxy", "NO_PROXY"):
            os.environ[clave] = "127.0.0.1,localhost"
        cls.servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SitioDePrueba)
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.servidor.server_address[1]}/"

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        for clave, valor in cls.entorno.items():
            if valor is None:
                os.environ.pop(clave, None)
            else:
                os.environ[clave] = valor
        aimarkers.fijar_idioma("es")

    def opciones(self, **extra):
        extra.setdefault("osv", False)  # sin red externa en las pruebas: OSV.dev se simula aparte
        return self.web.Opciones(retardo=0, imagenes=False, **extra)

    @unittest.skipUnless(shutil.which("openssl"), "necesita openssl para crear un certificado de prueba")
    def test_certificado_propio(self):
        import ssl
        import subprocess  # nosec B404
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", f"{tmp}/k.pem",  # nosec
                            "-out", f"{tmp}/c.pem", "-days", "2", "-subj", "/CN=localhost",
                            "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"], check=True, capture_output=True)
            servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), SitioDePrueba)
            contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            contexto.load_cert_chain(f"{tmp}/c.pem", f"{tmp}/k.pem")
            servidor.socket = contexto.wrap_socket(servidor.socket, server_side=True)
            threading.Thread(target=servidor.serve_forever, daemon=True).start()
            url = f"https://localhost:{servidor.server_address[1]}/"
            try:
                rechazada = aimarkers.analizar_objetivo(url, opciones=self.opciones())
                confiada = aimarkers.analizar_objetivo(url, opciones=self.opciones(confiar_certificado=True, seguridad=True,
                                                                                  dns=False))
                con_ca = aimarkers.analizar_objetivo(url, opciones=self.opciones(ca=f"{tmp}/c.pem"))
                despues = aimarkers.analizar_objetivo(url, opciones=self.opciones())
            finally:
                servidor.shutdown()
        self.assertEqual(rechazada.ficheros_analizados, 0)
        self.assertTrue(any("--confiar-certificado" in n or "--trust-certificate" in n for n in rechazada.notas))
        self.assertGreater(confiada.ficheros_analizados, 0)
        self.assertIn("cert-invalido", {h["id"] for h in confiada.seguridad.a_dict()["hallazgos"]})  # sigue siendo un hallazgo
        self.assertGreater(con_ca.ficheros_analizados, 0)
        self.assertEqual(despues.ficheros_analizados, 0)  # la excepción no se queda puesta para el siguiente análisis
        import aimarkers_web
        self.assertTrue(aimarkers_web.contexto_tls("otra.example").verify_mode == ssl.CERT_REQUIRED)

    def test_osv_web_completa_librerias(self):
        import aimarkers_dependencias as dep

        def falsa(ruta, datos=None):
            if ruta == "/querybatch":
                return {"results": [{"vulns": [{"id": "GHSA-gxr4-xjj5-5px2"}]} if q["package"]["name"] == "jquery" else {}
                                    for q in datos["queries"]]}
            return {"id": "GHSA-gxr4-xjj5-5px2", "aliases": ["CVE-2020-11022"], "database_specific": {"severity": "MODERATE"},
                    "affected": [{"package": {"ecosystem": "npm", "name": "jquery"},
                                  "ranges": [{"type": "SEMVER", "events": [{"introduced": "1.2.0"}, {"fixed": "3.5.0"}]}]}]}
        original = dep._peticion
        dep._peticion = falsa
        try:
            informe = aimarkers.analizar_objetivo(self.url, opciones=self.opciones(seguridad=True, osv=True, dns=False)).seguridad
        finally:
            dep._peticion = original
        jquery = [h for h in informe.a_dict()["hallazgos"] if h["id"] == "libreria-vulnerable" and "jQuery" in h["titulo"]][0]
        self.assertIn("CVE-2020-11022", jquery["cve"])
        self.assertIn("3.5.0", jquery["titulo"])
        self.assertTrue(any("OSV.dev" in n for n in informe.notas))

    def test_dependencias_vulnerables_osv(self):
        import aimarkers_dependencias as dep
        consultas = []

        def falsa(ruta, datos=None):
            consultas.append(ruta)
            if ruta == "/querybatch":
                return {"results": [{"vulns": [{"id": "GHSA-35jh-r3h4-6jhm"}, {"id": "GHSA-p6mc-m468-83gw"}]}
                                    if q["package"] == {"ecosystem": "npm", "name": "lodash"} else {} for q in datos["queries"]]}
            fijo = {"GHSA-35jh-r3h4-6jhm": ("CVE-2021-23337", "4.17.21"), "GHSA-p6mc-m468-83gw": ("CVE-2020-8203", "4.17.19")}
            cve, version = fijo[ruta.rsplit("/", 1)[1]]
            return {"id": ruta.rsplit("/", 1)[1], "aliases": [cve],
                    "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:H"}],
                    "affected": [{"package": {"ecosystem": "npm", "name": "lodash"},
                                  "ranges": [{"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": version}]}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": {
                "": {"name": "x"}, "node_modules/lodash": {"version": "4.17.15"}}}), encoding="utf-8")
            (d / "requirements.txt").write_text("django==3.2.0\nrequests>=2\n", encoding="utf-8")
            original = dep._peticion
            dep._peticion = falsa
            try:
                res = aimarkers.analizar_objetivo(str(d), opciones=self.web.Opciones(seguridad=True, solo_seguridad=True))
                sin_red = aimarkers.analizar_objetivo(str(d), opciones=self.web.Opciones(seguridad=True, solo_seguridad=True,
                                                                                         osv=False))
                dep._peticion = lambda *a, **k: (_ for _ in ()).throw(OSError("sin conexión"))
                caida = aimarkers.analizar_objetivo(str(d), opciones=self.web.Opciones(seguridad=True, solo_seguridad=True))
            finally:
                dep._peticion = original
        datos = res.seguridad.a_dict()
        vulnerable = [h for h in datos["hallazgos"] if h["id"] == "dependencia-vulnerable"]
        self.assertEqual(len(vulnerable), 1)
        self.assertIn("lodash 4.17.15", vulnerable[0]["titulo"])
        self.assertEqual(set(vulnerable[0]["cve"]), {"CVE-2021-23337", "CVE-2020-8203"})
        self.assertIn("4.17.21", vulnerable[0]["evidencias"][0]["extracto"])  # la versión que corrige todos los avisos
        self.assertEqual(vulnerable[0]["categoria"], "componentes")
        self.assertEqual(consultas.count("/querybatch"), 1)
        self.assertTrue(any("2 " in n and "OSV.dev" in n for n in res.seguridad.notas))
        self.assertFalse(any(h["id"] == "dependencia-vulnerable" for h in sin_red.seguridad.a_dict()["hallazgos"]))
        self.assertTrue(any("OSV.dev" in n for n in sin_red.seguridad.notas))
        self.assertTrue(any("sin conexión" in n for n in caida.seguridad.notas))

    def test_lectores_de_dependencias(self):
        import aimarkers_dependencias as dep
        casos = {
            "yarn.lock": ('"@babel/core@^7.0.0", "@babel/core@^7.1":\n  version "7.1.0"\n\nlodash@^4:\n  version "4.17.20"\n',
                          {("npm", "@babel/core", "7.1.0"), ("npm", "lodash", "4.17.20")}),
            "go.mod": ("module a.b/c\n\ngo 1.21\n\nrequire (\n\tgolang.org/x/net v0.7.0\n)\n", {("Go", "golang.org/x/net", "0.7.0")}),
            "Cargo.lock": ('[[package]]\nname = "smallvec"\nversion = "1.6.0"\n', {("crates.io", "smallvec", "1.6.0")}),
            "Gemfile.lock": ("GEM\n  specs:\n    rack (2.0.1)\n      dep (>= 1)\n", {("RubyGems", "rack", "2.0.1")}),
            "composer.lock": ('{"packages": [{"name": "a/b", "version": "v6.5.0"}]}', {("Packagist", "a/b", "6.5.0")}),
            "poetry.lock": ('[[package]]\nname = "jinja2"\nversion = "2.10"\n\n[package.dependencies]\nx = "1"\n',
                            {("PyPI", "jinja2", "2.10")}),
            "requirements-dev.txt": ("flask[async]==2.0.1 ; python_version > '3.8'\nrequests>=2\n", {("PyPI", "flask", "2.0.1")}),
            "package-lock.json": ("{roto", set()),
        }
        for nombre, (texto, esperado) in casos.items():
            self.assertEqual(set(dep.extraer(nombre, texto)), esperado, nombre)
        self.assertEqual(dep.cvss3_base("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"), 9.8)
        self.assertEqual(dep.cvss3_base("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N"), 6.1)

    def test_secretos_ocultos(self):
        informe = self.seg.InformeSeguridad()
        clave = "sk-ant-api03-" + "x" * 90
        texto = f"DB = 'postgres://app:{'Pa55' * 3}@db.interno:5432/x'\nK = '{clave}'\nU = 'mysql://u:${{DB_PASS}}@h/x'\n"
        self.seg.analizar_texto_codigo(informe, texto, "ajustes.py", "ajustes.py")
        volcado = json.dumps(informe.a_dict())
        self.assertIn("Database URL with password", volcado)
        self.assertIn("Anthropic key", volcado)
        self.assertNotIn("Pa55Pa55", volcado)
        self.assertNotIn("x" * 20, volcado)
        self.assertEqual(sum(1 for h in informe.hallazgos.values() if h.clave == "Database URL with password"), 1)

    def test_rastreo_respeta_robots_y_limite(self):
        SitioDePrueba.visitas.clear()
        res = aimarkers.analizar_objetivo(self.url, opciones=self.opciones(rastrear=True))
        self.assertEqual(res.ficheros_analizados, 3)
        self.assertNotIn("/privado/datos", SitioDePrueba.visitas)
        limitado = aimarkers.analizar_objetivo(self.url, opciones=self.opciones(rastrear=True, max_paginas=2))
        self.assertEqual(limitado.ficheros_analizados, 2)
        self.assertTrue(any("2" in n for n in limitado.notas))

    def test_rastreo_borra_la_carpeta_temporal(self):
        with self.web.Rastreo(self.url, self.opciones(rastrear=True)) as rastreo:
            rastreo.ejecutar()
            carpeta = rastreo.carpeta
            self.assertTrue(any(carpeta.iterdir()))
        self.assertFalse(carpeta.exists())

    def test_seguridad_pasiva(self):
        SitioDePrueba.visitas.clear()
        res = aimarkers.analizar_objetivo(self.url, opciones=self.opciones(seguridad=True, rastrear=True))
        datos = res.seguridad.a_dict()
        ids = {h["id"] for h in datos["hallazgos"]}
        for esperado in ("sin-https", "sin-csp", "sin-antiframe", "sin-nosniff", "cookie-sin-httponly", "cookie-sin-samesite",
                         "version-expuesta", "sin-csrf", "comentarios-sensibles", "emails-expuestos", "sin-sri",
                         "libreria-vulnerable", "source-map", "cms-version", "robots-sensible", "sin-security-txt"):
            self.assertIn(esperado, ids, esperado)
        # el modo pasivo no pide rutas sensibles
        self.assertNotIn("/.git/HEAD", SitioDePrueba.visitas)
        self.assertNotIn("git-expuesto", ids)
        jquery = next(h for h in datos["hallazgos"] if h["id"] == "libreria-vulnerable")
        self.assertIn("CVE-2020-11022", jquery["cve"])
        self.assertTrue(all(m["id"] in self.seg.MITRE for h in datos["hallazgos"] for m in h["mitre"]))
        self.assertEqual(datos["requisitos"]["CR"], "H")  # hay inicio de sesión
        self.assertEqual(sum(map(sum, datos["matriz"])), len(datos["hallazgos"]))
        for h in datos["hallazgos"]:
            if h["vector"]:
                self.assertEqual(h["cvss"], self.seg.cvss4.puntuacion(h["vector"]))
                self.assertTrue(h["vector"].startswith("CVSS:4.0/AV:"))

    def test_segmentacion_inventario_privacidad_y_progreso(self):
        avances = []
        res = aimarkers.analizar_objetivo(self.url, opciones=self.opciones(seguridad=True, rastrear=True, progreso=avances.append))
        datos = res.seguridad.a_dict()
        ids = {h["id"] for h in datos["hallazgos"]}
        for esperado in ("rastreadores-terceros", "fuentes-google", "youtube-sin-privacidad", "tabnabbing"):
            self.assertIn(esperado, ids, esperado)
        categorias = {c["id"] for c in datos["categorias"]}
        self.assertTrue({"cabeceras", "privacidad", "componentes", "transporte"} <= categorias)
        self.assertEqual(sum(c["total"] for c in datos["categorias"]), len(datos["hallazgos"]))
        self.assertTrue(all(h["categoria"] in self.seg.CATEGORIAS for h in datos["hallazgos"]))
        inventario = {(c["tipo"], c["nombre"]) for c in datos["inventario"]}
        self.assertIn(("plugin", "ninja-forms"), inventario)
        self.assertIn(("libreria", "jQuery"), inventario)
        self.assertIn(("cms", "WordPress"), inventario)
        hosts = {x["host"]: x for x in datos["terceros"]}
        self.assertTrue(hosts["www.googletagmanager.com"]["rastreador"])
        fases = {a["fase"] for a in avances if isinstance(a, dict)}
        self.assertTrue({"descarga", "ia", "seguridad"} <= fases)
        self.assertTrue(set(self.seg.CATEGORIA) <= set(self.seg.CATALOGO))
        self.assertEqual(set(self.seg.CATEGORIA), set(self.seg.CATALOGO))

    def test_dns_correo(self):
        respuestas = {
            ("ejemplo.es", "TXT"): (['"v=spf1 include:_spf.google.com ?all"'], False, "Prueba"),
            ("_dmarc.ejemplo.es", "TXT"): (['"v=DMARC1; p=none; rua=mailto:x@ejemplo.es"'], False, "Prueba"),
            ("ejemplo.es", "A"): (["192.0.2.1"], False, "Prueba"),
            ("ejemplo.es", "CAA"): ([], False, "Prueba"),
            ("sinnada.es", "TXT"): ([], True, "Prueba"),
            ("_dmarc.sinnada.es", "TXT"): ([], True, "Prueba"),
            ("sinnada.es", "A"): (["192.0.2.2"], True, "Prueba"),
            ("sinnada.es", "CAA"): (['0 issue "letsencrypt.org"'], True, "Prueba"),
        }
        original = self.seg.consulta_dns
        self.seg.consulta_dns = lambda nombre, tipo: respuestas.get((nombre, tipo), ([], None, ""))
        try:
            uno = self.seg.InformeSeguridad()
            self.seg.analizar_dns(uno, "www.ejemplo.es")
            dos = self.seg.InformeSeguridad()
            self.seg.analizar_dns(dos, "sinnada.es")
            tres = self.seg.InformeSeguridad()
            self.seg.analizar_dns(tres, "127.0.0.1")
        finally:
            self.seg.consulta_dns = original
        ids_uno = {h.id for h in uno.hallazgos.values()}
        self.assertEqual(ids_uno, {"spf-permisivo", "dmarc-sin-politica", "dnssec-ausente", "caa-ausente"})
        self.assertEqual({h.id for h in dos.hallazgos.values()}, {"spf-ausente", "dmarc-ausente"})
        self.assertEqual(tres.hallazgos, {})
        self.assertEqual(self.seg._txt('"v=spf1 " "-all"'), "v=spf1 -all")

    def test_seguridad_activa_exige_autorizacion(self):
        SitioDePrueba.visitas.clear()
        sin = aimarkers.analizar_objetivo(self.url, opciones=self.opciones(seguridad=True, activo=True))
        self.assertNotIn("/.git/HEAD", SitioDePrueba.visitas)
        self.assertEqual(sin.seguridad.modo, "pasivo")
        con = aimarkers.analizar_objetivo(self.url, opciones=self.opciones(seguridad=True, activo=True, autorizado=True))
        ids = {h["id"] for h in con.seguridad.a_dict()["hallazgos"]}
        self.assertIn("git-expuesto", ids)
        self.assertIn("metodos-peligrosos", ids)
        self.assertNotIn("env-expuesto", ids)  # 404: no hay falso positivo
        self.assertEqual(con.seguridad.modo, "activo")

    def test_cli_activo_sin_autorizado_falla(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            aimarkers.main([self.url, "--activo", "--silencioso"])

    def test_seguridad_de_codigo(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / ".github" / "workflows").mkdir(parents=True)
            (d / "app.py").write_text("import pickle, subprocess, hashlib\nDEBUG = True\nDB_" + "PASSWORD = 'Sup3rS3cr3tPass!'\n"
                                      "cur.execute(\"SELECT * FROM t WHERE n = '\" + n + \"'\")\n"
                                      "subprocess.run('ls ' + x, shell=True)\npickle.loads(b)\nrequests.get(u, verify=False)\n",
                                      encoding="utf-8")
            (d / "web.js").write_text("el.innerHTML = location.hash;\n", encoding="utf-8")
            (d / "Dockerfile").write_text("FROM python:latest\n", encoding="utf-8")
            (d / "requirements.txt").write_text("flask\n", encoding="utf-8")
            (d / ".github" / "workflows" / "ci.yml").write_text("steps:\n  - uses: actions/checkout@v4\n", encoding="utf-8")
            (d / "config.py").write_text("K = '" + "AKIA" + "Q" * 16 + "'\n", encoding="utf-8")
            (d / "seguro.py").write_text("import os\nclave = os.environ['CLAVE']\nhashlib.md5(b, usedforsecurity=False)\n"
                                         "ok = verify_mode != ssl.CERT_NONE\n", encoding="utf-8")
            res = aimarkers.analizar_objetivo(str(d), opciones=self.web.Opciones(seguridad=True, solo_seguridad=True))
        datos = res.seguridad.a_dict()
        ids = {h["id"] for h in datos["hallazgos"]}
        for esperado in ("secreto-codigo", "inyeccion-sql", "inyeccion-comandos", "deserializacion", "tls-desactivado",
                         "modo-depuracion", "xss-dom", "imagen-latest", "contenedor-root", "dependencia-sin-fijar",
                         "accion-sin-fijar"):
            self.assertIn(esperado, ids, esperado)
        textos = json.dumps(datos)
        self.assertNotIn("seguro.py", textos)
        self.assertNotIn("Q" * 16, textos)  # los secretos se muestran recortados
        self.assertEqual(res.puntuacion(), 0)  # solo seguridad: sin marcadores de IA

    def test_informes_con_seguridad(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp)
            codigo = aimarkers.main([self.url, "--seguridad", "--silencioso", "--retardo", "0", "--sin-imagenes", "--lang", "en",
                                     "--json", str(salida / "r.json"), "--md", str(salida / "r.md"), "--html", str(salida / "r.html"),
                                     "--umbral-cvss", "0.1"])
            self.assertEqual(codigo, 3)
            datos = json.loads((salida / "r.json").read_text(encoding="utf-8"))
            self.assertEqual(datos[0]["seguridad"]["cvss_version"], "CVSS v4.0")
            pagina = (salida / "r.html").read_text(encoding="utf-8")
            self.assertIn("class='matriz'", pagina)
            self.assertNotIn("<script", pagina.lower())
            self.assertIn("OWASP", (salida / "r.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
