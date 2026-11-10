"""Pruebas de aimarkers. Ejecutar con: python -m unittest discover tests -v"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ.parent))
import aimarkers

F = RAIZ / "fixtures"


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
        res = aimarkers.Resultado("x", "código")
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


if __name__ == "__main__":
    unittest.main()
