"""Pruebas de aimarkers / aimarkers tests. Ejecutar / run: python -m unittest discover tests -v"""
import http.client
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
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

    def test_ruta_relativa_segura(self):
        self.assertEqual(str(self.gui.ruta_relativa_segura("a/./b\\c.txt")), "a/b/c.txt")
        for mala in ("..", "../a", "a/../../b", "", "\x00", "C:\\a"):
            self.assertIsNone(self.gui.ruta_relativa_segura(mala), mala)


if __name__ == "__main__":
    unittest.main()
