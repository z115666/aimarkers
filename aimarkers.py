#!/usr/bin/env python3
# aimarkers: ignore-file
"""
aimarkers - Análisis de marcadores de IA en código, documentación, webs y repositorios Git.

Busca indicios de que un contenido se ha generado o asistido con IA y los
puntúa por niveles (explícito, fuerte, medio, débil). No es un detector
infalible: el resultado es una estimación basada en evidencias que hay que
revisar a mano.

Uso rápido:
    python aimarkers.py ./mi_repo
    python aimarkers.py informe.md script.ps1
    python aimarkers.py https://ejemplo.com --html informe.html
    python aimarkers.py pagina_guardada.html --json resultado.json --md resultado.md

Solo usa la biblioteca estándar de Python (3.9+). El módulo subprocess se usa
únicamente para invocar git con argumentos en lista y una configuración endurecida.
Autor: Alberto
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import statistics
import subprocess  # nosec B404
import sys
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Escala de pesos
# ---------------------------------------------------------------------------

PESOS = {"explicito": 40, "fuerte": 20, "medio": 8, "debil": 3}
NOMBRE_NIVEL = {"explicito": "Explícito", "fuerte": "Fuerte", "medio": "Medio", "debil": "Débil"}
ORDEN_NIVEL = ["explicito", "fuerte", "medio", "debil"]
MAX_REPETICION = 3.0          # un marcador repetido suma como máximo 3 veces su peso
MIN_PALABRAS_ESTILO = 150     # por debajo no se puntúa el estilo del texto
MAX_TAMANO_FICHERO = 3_000_000
PREVALENCIA_PLENA = 0.10      # medio/débil puntúan completos si afectan al 10 % de los ficheros
# Marcadores de nivel de proyecto o de datos: no se escalan por número de ficheros
SIN_PREVALENCIA = {"commits-grandes", "mensajes-uniformes", "rafaga-datos", "coordenadas-mixtas",
                   "stack-generador", "llms-txt", "framework-ia"}

BANDAS = [
    (70, "Alta probabilidad de generación o asistencia intensa con IA"),
    (40, "Probable asistencia de IA en parte del contenido"),
    (15, "Indicios débiles: rasgos compatibles, nada concluyente"),
    (0, "Sin indicios relevantes"),
]

EXT_CODIGO = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".ps1", ".psm1", ".psd1", ".sh", ".bash",
    ".zsh", ".bat", ".cmd", ".java", ".kt", ".swift", ".go", ".rs", ".rb", ".php", ".c", ".h",
    ".cpp", ".hpp", ".cs", ".vb", ".lua", ".r", ".sql", ".scala", ".dart", ".vue", ".svelte",
    ".css", ".scss", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".json",
}
EXT_TEXTO = {".md", ".markdown", ".txt", ".rst", ".adoc", ".org", ".tex"}
EXT_HTML = {".html", ".htm", ".xhtml"}

DIRS_IGNORADOS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build", ".next",
    ".nuxt", "out", "target", "vendor", ".tox", ".mypy_cache", ".pytest_cache", "coverage",
    ".idea", ".vscode-test", "bower_components", "site-packages",
}

# Ficheros y carpetas que solo existen para dar instrucciones a agentes de IA
FICHEROS_AGENTE = {
    "CLAUDE.md": "Claude Code", "CLAUDE.local.md": "Claude Code", "AGENTS.md": "Codex / agentes (AGENTS.md)",
    "GEMINI.md": "Gemini CLI", ".cursorrules": "Cursor", ".windsurfrules": "Windsurf",
    ".clinerules": "Cline", ".roomodes": "Roo Code", "copilot-instructions.md": "GitHub Copilot",
    ".aider.conf.yml": "Aider", ".aider.chat.history.md": "Aider", ".aider.input.history": "Aider",
    "CONVENTIONS.md": "Aider (convenciones)", ".replit": "Replit", "replit.nix": "Replit",
}
DIRS_AGENTE = {
    ".claude": "Claude Code", ".cursor": "Cursor", ".windsurf": "Windsurf", ".kiro": "Kiro",
    ".clinerules": "Cline", ".roo": "Roo Code", ".continue": "Continue", ".opencode": "OpenCode",
    ".junie": "JetBrains Junie", ".amazonq": "Amazon Q", ".gemini": "Gemini CLI",
    ".specstory": "SpecStory (historial de chats con IA)",
}

# ---------------------------------------------------------------------------
# Modelos de datos
# ---------------------------------------------------------------------------


@dataclass
class Hallazgo:
    regla: str
    nivel: str
    descripcion: str
    ubicacion: str
    extracto: str = ""

    @property
    def peso(self) -> int:
        return PESOS[self.nivel]


@dataclass
class Resultado:
    objetivo: str
    tipo: str
    hallazgos: list[Hallazgo] = field(default_factory=list)
    notas: list[str] = field(default_factory=list)
    ficheros_analizados: int = 0

    def anadir(self, regla: str, nivel: str, descripcion: str, ubicacion: str, extracto: str = "") -> None:
        extracto = re.sub(r"\s+", " ", extracto).strip()
        if len(extracto) > 140:
            extracto = extracto[:137] + "..."
        self.hallazgos.append(Hallazgo(regla, nivel, descripcion, ubicacion, extracto))

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

    def banda(self) -> str:
        p = self.puntuacion()
        if p < 15 and any(h.nivel in ("medio", "fuerte") for h in self.hallazgos):
            return BANDAS[2][1]  # hay algún indicio concreto aunque puntúe poco
        for umbral, texto in BANDAS:
            if p >= umbral:
                return texto
        return BANDAS[-1][1]

    def atribucion_explicita(self) -> bool:
        return any(h.nivel == "explicito" for h in self.hallazgos)

    def a_dict(self) -> dict:
        return {
            "objetivo": self.objetivo,
            "tipo": self.tipo,
            "puntuacion": self.puntuacion(),
            "valoracion": self.banda(),
            "atribucion_explicita": self.atribucion_explicita(),
            "ficheros_analizados": self.ficheros_analizados,
            "notas": self.notas,
            "hallazgos": [dict(asdict(h), peso=h.peso) for h in self.hallazgos],
            "resumen_por_marcador": {
                k: {"nivel": v[0].nivel, "veces": len(v), "puntos": round(self.contribucion(v), 1),
                    "prevalencia": round(self.prevalencia(v), 4)}
                for k, v in self.por_regla().items()},
        }


# ---------------------------------------------------------------------------
# Reglas basadas en expresiones regulares
# ---------------------------------------------------------------------------

I = re.IGNORECASE
M = re.MULTILINE

# Aplicables a cualquier contenido (código, texto, HTML)
REGLAS_GENERALES = [
    ("firma-generador", "explicito", "Firma de herramienta de IA en el contenido",
     re.compile(r"(?:generated|created|written|built)\s+(?:with|by|using)\s+\[?(?:claude(?:\s+code)?|chatgpt|gpt-?[345o][\w.-]*|github\s+copilot|copilot|cursor|gemini|codeium|windsurf|devin|aider|lovable|bolt\.new|v0(?:\.dev|\.app)?)\b", I)),
    ("firma-robot", "explicito", "Pie «🤖 Generated with…» de un agente",
     re.compile(r"🤖\s*Generated\s+with", I)),
    ("coautor-ia", "explicito", "Coautoría declarada a una IA",
     re.compile(r"Co-?authored-?by:\s*[^\n<]{0,120}(?:claude|anthropic|copilot|cursor\s*agent|devin|aider|openai|codex|gemini|jules)", I)),
    ("citas-chatgpt", "explicito", "Rastro de citas de ChatGPT copiado del chat",
     re.compile(r"contentReference\[oaicite:\d+\]|oaicite:\d+|\ue200cite|turn\d+(?:search|news|view|fetch)\d+", I)),
    ("utm-chatgpt", "explicito", "Enlace copiado desde ChatGPT (utm_source=chatgpt.com/openai)",
     re.compile(r"utm_source=(?:chatgpt\.com|chatgpt|openai|perplexity|copilot\.microsoft|gemini)", I)),
    ("autodeclaracion-modelo", "explicito", "El texto se declara modelo de lenguaje",
     re.compile(r"as an ai (?:language )?model|as a large language model|como (?:un )?modelo de (?:lenguaje|ia)|(?:my|mi) (?:knowledge cutoff|fecha de corte de conocimiento)", I)),
]

# Restos de conversación con el chat
REGLAS_CHAT = [
    ("resto-chat", "fuerte", "Frase de chat copiada dentro del fichero",
     re.compile(r"^\W{0,6}(?:certainly!|sure! here|of course! here|here(?:'s| is) (?:the|your) (?:updated|complete|full|revised|corrected|improved|final|refactored)|claro,? aquí (?:tienes|está)|¡claro! aquí|por supuesto,? aquí (?:tienes|está)|aquí tienes (?:el|la|tu) (?:código|script|versión) (?:actualizad|complet|corregid|mejorad))", I | M)),
    ("cierre-chat", "fuerte", "Cierre típico de respuesta de chat",
     re.compile(r"(?:i hope this helps|hope this helps!|let me know if you(?:'d| would) like me to|would you like me to (?:add|create|write|generate|expand|adjust|make)|espero que (?:esto )?te (?:sea|resulte) (?:de )?(?:útil|ayuda)|¿quieres que (?:te )?(?:lo|la|añada|prepare|genere|adapte|amplíe|redacte)|si quieres,? (?:también )?puedo (?:prepararte|generarte|añadir|crear|redactar|adaptar))", I)),
]

# Huecos de plantilla: solo en texto, con mayúscula inicial y sin ser enlace Markdown
REGLA_HUECO = ("hueco-plantilla", "fuerte", "Hueco de plantilla sin rellenar",
               re.compile(r"\[(?:Insert|Insertar|Inserte|Añadir|Add|Your|YOUR|Tu|TU|Su|Nombre|NOMBRE|Company|Empresa|EMPRESA|Fecha|FECHA|Date|Name)\b[^\]\n]{0,40}\](?![(:\[])"))

# Específicas de código
RE_COMENTARIO = re.compile(r"^\s*(?:#|//|/\*|\*|--|<!--|REM\b|')", I)
REGLAS_CODIGO_LINEA = [
    ("comentario-demo", "medio", "Comentario de código de demostración",
     re.compile(r"in a real(?:-world)? (?:application|app|implementation|scenario|project|system|environment)|for (?:demonstration|demo|illustration) purposes|this is a (?:simplified|basic|placeholder|mock) (?:version|implementation|example)|you would (?:typically|normally|usually)|placeholder (?:implementation|logic)|en (?:un|una) (?:entorno|aplicación|proyecto|caso|implementación) real|con fines (?:de demostración|demostrativos|ilustrativos)|esto es una (?:versión|implementación) simplificada|aquí (?:iría|irá) (?:la|tu) lógica", I)),
    ("placeholder", "medio", "Valor de ejemplo sin sustituir",
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
    ("gen-lovable", "fuerte", "Huella de Lovable (data-lov-*, gptengineer, lovable-tagger)",
     re.compile(r"data-lov-(?:id|name)|gptengineer(?:\.js)?|cdn\.gpteng\.co|lovable-tagger|lovable\.(?:dev|app)/|edit with lovable", I)),
    ("gen-v0", "fuerte", "Huella de v0 (Vercel)",
     re.compile(r"<meta[^>]{0,200}name=[\"']generator[\"'][^>]{0,200}content=[\"']v0(?:\.dev|\.app)?[\"']|made with v0|v0\.(?:dev|app)/chat", I)),
    ("gen-bolt", "fuerte", "Huella de Bolt.new",
     re.compile(r"bolt\.new|made in bolt|built with bolt", I)),
    ("gen-otros", "fuerte", "Huella de otro constructor web con IA",
     re.compile(r"readdy\.ai|base44\.(?:app|com)|durable\.co|10web\.io/ai|same\.(?:dev|new)/|create\.xyz|tempo\.new|framer\.ai|hostinger[^\"'<]{0,30}ai builder|wix(?:[^\"'<]{0,20})adi\b", I)),
    ("imagen-ia", "fuerte", "Imagen con nombre de generador de IA",
     re.compile(r"(?:src|href|content|srcset)=[\"'][^\"']{0,300}?(?:dall[·\-_ %c2b7]*e|chatgpt[ _-]?image|gemini_generated_image|midjourney|mj_|firefly|leonardo[_.-]ai|ideogram|stable[-_]?diffusion|sdxl|flux[-_]?(?:dev|schnell|pro))[^\"']{0,300}[\"']", I)),
    ("framework-ia", "debil", "Framework construido con IA (vinext de Cloudflare)",
     re.compile(r"vinext", I)),
]
RE_META_GENERATOR = re.compile(r"<meta[^>]{0,200}name=[\"']generator[\"'][^>]{0,200}content=[\"']([^\"']{1,200})[\"']", I)
RE_TIMESTAMP = re.compile(
    r"\\?[\"'](?:created_?at|createdAt|inserted_?at|insertedAt|date_?created|dateCreated|published_?at|publishedAt|creado_?en|fecha_?alta)\\?[\"']\s*:\s*\\?[\"']"
    r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)", I)
RE_LATITUD = re.compile(r"\\?[\"'](?:latitude|lat)\\?[\"']\s*:\s*(-?\d{1,3}(?:\.\d+)?)", I)
RE_STACK_GENERADOR = [
    re.compile(r"data-slot=[\"']"),                     # shadcn/ui
    re.compile(r"class=[\"'][^\"']{0,300}lucide lucide-"),     # iconos lucide
    re.compile(r"from-(?:purple|violet|indigo)-\d{3}[^\"']{0,200}to-(?:blue|pink|cyan)-\d{3}"),  # degradado por defecto
]

# Git
RE_BOT_AUTOR = re.compile(r"copilot-swe-agent|copilot\[bot\]|devin-ai-integration|google-labs-jules|claude\[bot\]|cursor(?:agent|-agent)|openai-codex|codex\[bot\]|sweep-ai|\(aider\)", I)
RE_RAMA_AGENTE = re.compile(r"^(?:remotes/)?(?:origin/)?(?:claude|copilot|cursor|codex|devin|jules|aider|sweep|windsurf)[/-]", I)
RE_CONVENTIONAL = re.compile(r"^(?:feat|fix|chore|docs|refactor|test|style|perf|build|ci|revert)(?:\([^)]+\))?!?: ")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def plural(n: int, palabra: str) -> str:
    return f"{n} {palabra}" if n == 1 else f"{n} {palabra}s"


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
    for regla, nivel, desc, patron in reglas:
        limite = 1 if nivel == "debil" else max_por_regla
        lineas_vistas: set[int] = set()
        for m in patron.finditer(texto):
            linea = num_linea(texto, m.start())
            if linea in lineas_vistas:
                continue
            lineas_vistas.add(linea)
            inicio = max(0, m.start() - 30)
            res.anadir(regla, nivel, desc, f"{ubic}:{linea}", texto[inicio:m.end() + 40])
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
        if palabras >= 50 and res.tipo not in ("directorio", "repositorio git"):
            res.notas.append(f"{ubic}: {palabras} palabras; muestra insuficiente para valorar el estilo.")
        return

    # Muletillas: solo cuentan por densidad
    encontradas: list[str] = []
    for patron in RE_MULETILLAS:
        encontradas += [m.group(0) for m in patron.finditer(texto)]
    densidad = len(encontradas) * 1000 / palabras
    if len(encontradas) >= 3 and densidad >= 3:
        unicas = sorted({e.lower() for e in encontradas})
        res.anadir("muletillas", "debil", "Densidad alta de muletillas típicas de LLM",
                   ubic, f"{len(encontradas)} apariciones ({densidad:.1f}/1000 palabras): " + ", ".join(unicas[:10]))

    # Raya tipográfica
    rayas = texto.count("—")
    if rayas >= 5 and rayas * 100 / palabras > 1:
        res.anadir("rayas", "debil", "Uso intensivo de la raya (—)", ubic, f"{rayas} rayas en {palabras} palabras")

    # Viñetas con término en negrita
    vinetas = len(RE_VINETA.findall(texto))
    negritas = len(RE_VINETA_NEGRITA.findall(texto))
    if negritas >= 5 and vinetas and negritas / vinetas >= 0.5:
        res.anadir("vinetas-negrita", "debil", "Viñetas con «**Término:** explicación» de forma sistemática",
                   ubic, f"{negritas} de {vinetas} viñetas")

    # Emojis en títulos
    titulos_emoji = len(RE_EMOJI_TITULO.findall(texto))
    if titulos_emoji >= 3:
        res.anadir("emoji-titulos", "debil", "Títulos que empiezan con emoji", ubic, f"{titulos_emoji} títulos")

    # Ritmo de frases (burstiness)
    prosa = re.sub(r"```.*?```", " ", texto, flags=re.S)
    prosa = "\n".join(l for l in prosa.splitlines() if not RE_VINETA.match(l) and not l.lstrip().startswith(("#", "|")))
    frases = [f for f in re.split(r"(?<=[.!?])\s+", prosa) if contar_palabras(f) >= 3]
    if len(frases) >= 15:
        longitudes = [contar_palabras(f) for f in frases]
        media = statistics.mean(longitudes)
        cv = statistics.pstdev(longitudes) / media if media else 1
        if cv < 0.35:
            res.anadir("ritmo-uniforme", "debil", "Frases de longitud muy uniforme (baja burstiness)",
                       ubic, f"{len(frases)} frases, media {media:.1f} palabras, coef. de variación {cv:.2f}")


def analizar_texto(res: Resultado, texto: str, ubic: str) -> None:
    aplicar_reglas(res, texto, REGLAS_GENERALES, ubic)
    aplicar_reglas(res, texto, REGLAS_CHAT + [REGLA_HUECO], ubic, max_por_regla=3)
    analizar_estilo(res, texto, ubic)


# ---------------------------------------------------------------------------
# Análisis de código
# ---------------------------------------------------------------------------


def analizar_codigo(res: Resultado, texto: str, ubic: str, extension: str) -> None:
    aplicar_reglas(res, texto, REGLAS_GENERALES, ubic)
    aplicar_reglas(res, texto, [r for r in REGLAS_CHAT if r[0] == "resto-chat"], ubic, max_por_regla=3)

    lineas = texto.splitlines()
    comentarios = [(i + 1, l) for i, l in enumerate(lineas) if RE_COMENTARIO.match(l) or "#" in l or "//" in l]

    for regla, nivel, desc, patron in REGLAS_CODIGO_LINEA:
        vistos = 0
        lista = comentarios if regla == "comentario-demo" else list(enumerate(lineas, 1))
        for n, l in lista:
            if patron.search(l):
                res.anadir(regla, nivel, desc, f"{ubic}:{n}", l)
                vistos += 1
                if vistos >= 5:
                    break

    pasos = [(n, l) for n, l in enumerate(lineas, 1) if RE_PASO.match(l)]
    if len(pasos) >= 3:
        res.anadir("comentarios-paso", "debil", "Comentarios numerados por pasos («# Step 1:»)",
                   f"{ubic}:{pasos[0][0]}", f"{len(pasos)} comentarios de paso; p. ej. {pasos[0][1].strip()}")

    emojis = [(n, l) for n, l in enumerate(lineas, 1) if RE_EMOJI_LOG.search(l)]
    if emojis:
        res.anadir("emoji-logs", "medio", "Emojis en mensajes de consola o log",
                   f"{ubic}:{emojis[0][0]}", f"{plural(len(emojis), 'línea')}; p. ej. {emojis[0][1].strip()}")

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
            res.anadir("valla-markdown", "fuerte", "Fichero envuelto en una valla Markdown (```) copiada del chat",
                       f"{ubic}:{candidato[0]}", candidato[1])

    if extension == ".py":
        funciones = re.findall(r"^\s*def \w+\(", texto, M)
        docs_args = re.findall(r"\"\"\"[^\"]*?\n\s*(?:Args|Parameters|Returns):", texto)
        if len(funciones) >= 5 and len(docs_args) / len(funciones) >= 0.8:
            res.anadir("docstrings-uniformes", "debil", "Docstrings Args/Returns en casi todas las funciones",
                       ubic, f"{len(docs_args)} de {len(funciones)} funciones")

    genericos = RE_EXCEPT_GENERICO.findall(texto)
    if len(genericos) >= 3:
        res.anadir("errores-genericos", "debil", "Manejo de errores genérico repetido («An error occurred»)",
                   ubic, f"{len(genericos)} bloques")

    if extension not in {".md", ".txt", ".json"}:
        tip = [(n, l) for n, l in enumerate(lineas, 1) if RE_TIPOGRAFICO.search(l)]
        if len(tip) >= 2:
            res.anadir("tipografia-codigo", "debil", "Caracteres tipográficos en código (raya, comillas curvas, invisibles)",
                       f"{ubic}:{tip[0][0]}", f"{plural(len(tip), 'línea')}; p. ej. {tip[0][1].strip()}")

    # Densidad de comentarios, sin contar la cabecera inicial (licencia, shebang)
    cuerpo = list(lineas)
    while cuerpo and (not cuerpo[0].strip() or RE_COMENTARIO.match(cuerpo[0])):
        cuerpo.pop(0)
    cuerpo = [l for l in cuerpo if l.strip()]
    if len(cuerpo) >= 40:
        densidad = sum(1 for l in cuerpo if RE_COMENTARIO.match(l)) / len(cuerpo)
        if densidad >= 0.4:
            res.anadir("densidad-comentarios", "debil", "Densidad de comentarios muy alta",
                       ubic, f"{densidad:.0%} de las líneas son comentarios")


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
        t = "".join(self.partes)
        t = re.sub(r"[ \t]+", " ", t)
        return re.sub(r"\n\s*\n+", "\n", t).strip()


def detectar_rafagas(res: Resultado, crudo: str, ubic: str) -> None:
    marcas = sorted({t for t in (parsear_fecha(v) for v in RE_TIMESTAMP.findall(crudo)) if t is not None})
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
        res.anadir("rafaga-datos", "medio", "Ráfaga de registros creados cada pocos segundos (carga automatizada)",
                   f"{ubic}:datos embebidos",
                   f"{len(r)} registros entre {desde} y {hasta} (hora local), separación mediana {statistics.median(huecos):.1f} s")


def analizar_coordenadas(res: Resultado, crudo: str, ubic: str) -> None:
    valores = RE_LATITUD.findall(crudo)
    if len(valores) < 20:
        return
    decimales = [len(v.split(".")[1]) if "." in v else 0 for v in valores]
    bajos = sum(1 for d in decimales if d <= 6)
    altos = sum(1 for d in decimales if d >= 7)
    redondos = sum(1 for d in decimales if d <= 2)
    if bajos / len(valores) >= 0.15 and altos / len(valores) >= 0.15:
        res.anadir("coordenadas-mixtas", "debil", "Precisión de coordenadas mezclada (dos orígenes de datos)",
                   f"{ubic}:datos embebidos",
                   f"{bajos} con ≤6 decimales, {altos} con ≥7 decimales, {redondos} casi redondas, de {len(valores)}")


def analizar_html(res: Resultado, crudo: str, ubic: str) -> None:
    aplicar_reglas(res, crudo, REGLAS_GENERALES, ubic)
    aplicar_reglas(res, crudo, REGLAS_HTML, ubic, max_por_regla=3)

    gen = RE_META_GENERATOR.search(crudo)
    if gen:
        res.notas.append(f"{ubic}: meta generator = «{gen.group(1)}»")

    coincidencias_stack = sum(1 for p in RE_STACK_GENERADOR if p.search(crudo))
    if coincidencias_stack >= 2:
        res.anadir("stack-generador", "debil", "Stack por defecto de los generadores (shadcn/ui, lucide, degradados)",
                   ubic, f"{coincidencias_stack} de 3 rasgos presentes")

    detectar_rafagas(res, crudo, ubic)
    analizar_coordenadas(res, crudo, ubic)

    extractor = ExtractorTexto()
    try:
        extractor.feed(crudo)
        visible = extractor.texto()
    except Exception:  # noqa: BLE001 - HTML malformado: seguimos sin texto visible
        visible = ""
    if visible:
        aplicar_reglas(res, visible, REGLAS_CHAT + [REGLA_HUECO], f"{ubic} (texto visible)", max_por_regla=3)
        analizar_estilo(res, visible, f"{ubic} (texto visible)")


class _RedireccionSegura(urllib.request.HTTPRedirectHandler):
    """Solo sigue redirecciones a http/https (evita file://, ftp://...)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not re.match(r"https?://", newurl, I):
            raise urllib.error.URLError(f"redirección rechazada a un esquema no permitido: {newurl[:80]}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_ABRIDOR = urllib.request.build_opener(_RedireccionSegura)


def descargar(url: str, timeout: int = 20) -> tuple[str | None, str]:
    if not re.match(r"https?://", url, I):
        return None, "solo se admiten URLs http(s)"
    cabeceras = {"User-Agent": f"aimarkers/{VERSION} (+analisis de marcadores de IA)"}
    peticion = urllib.request.Request(url, headers=cabeceras)  # noqa: S310 - esquema http(s) validado arriba
    try:
        with _ABRIDOR.open(peticion, timeout=timeout) as r:  # nosec B310
            datos = r.read(MAX_TAMANO_FICHERO)
            juego = r.headers.get_content_charset() or "utf-8"
            return datos.decode(juego, errors="replace"), ""
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        return None, str(e)


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
        res.notas.append("Repositorio Git sin commits o git no disponible.")
        return
    commits = []
    for bloque in log.split("\x1e"):
        partes = bloque.strip("\n").split("\x1f")
        if len(partes) == 7:
            commits.append(partes)
    res.notas.append(f"Git: {len(commits)} commits analizados.")

    contadores: dict[str, int] = {}
    for h, an, ae, cn, ce, _fecha, cuerpo in commits:
        corto = h[:8]
        quien = f"{an} <{ae}> / {cn} <{ce}>"
        if RE_BOT_AUTOR.search(quien):
            contadores["bot"] = contadores.get("bot", 0) + 1
            if contadores["bot"] <= 5:
                res.anadir("autor-bot", "explicito", "Commit firmado por un agente o bot de IA", f"commit {corto}", quien)
        for linea in cuerpo.splitlines():
            if re.match(r"\s*Co-?authored-?by:", linea, I) and REGLAS_GENERALES[2][3].search(linea):
                contadores["coautor"] = contadores.get("coautor", 0) + 1
                if contadores["coautor"] <= 5:
                    res.anadir("coautor-ia", "explicito", "Coautoría declarada a una IA", f"commit {corto}", linea)
            elif REGLAS_GENERALES[1][3].search(linea) or REGLAS_GENERALES[0][3].search(linea):
                contadores["pie"] = contadores.get("pie", 0) + 1
                if contadores["pie"] <= 5:
                    res.anadir("firma-robot", "explicito", "Pie de mensaje de un agente de IA", f"commit {corto}", linea)
    for clave, total in contadores.items():
        if total > 5:
            res.notas.append(f"Git: {total} commits con marcador «{clave}» (se muestran 5).")

    ramas = git(repo, "branch", "-a", "--format=%(refname:short)").splitlines()
    agentes = [r for r in ramas if RE_RAMA_AGENTE.match(r.strip())]
    for r in agentes[:5]:
        res.anadir("rama-agente", "fuerte", "Rama con prefijo de agente de IA", "ramas", r.strip())

    # Commits muy grandes
    numstat = git(repo, "log", "--all", f"-n{max_commits}", "--no-merges", "--no-ext-diff", "--no-textconv",
                  "--format=@@%h", "--numstat")
    grandes, actual, suma = [], None, 0
    for linea in numstat.splitlines() + ["@@fin"]:
        if linea.startswith("@@"):
            if actual and suma > 1000:
                grandes.append((actual, suma))
            actual, suma = linea[2:], 0
        else:
            partes = linea.split("\t")
            if len(partes) == 3 and partes[0].isdigit():
                suma += int(partes[0])
    if len(grandes) >= 3:
        res.anadir("commits-grandes", "medio", "Varios commits con más de 1.000 líneas añadidas",
                   "historial", f"{len(grandes)} commits; mayor: {max(grandes, key=lambda x: x[1])[0]} "
                                f"(+{max(g[1] for g in grandes)} líneas)")

    # Mensajes uniformes
    if len(commits) >= 20:
        conv = sum(1 for c in commits if RE_CONVENTIONAL.match(c[6]))
        con_vinetas = sum(1 for c in commits if len(re.findall(r"^\s*[-*] ", c[6], M)) >= 3)
        if conv / len(commits) >= 0.9 and con_vinetas / len(commits) >= 0.5:
            res.anadir("mensajes-uniformes", "debil", "Mensajes de commit perfectamente uniformes con cuerpo en viñetas",
                       "historial", f"{conv}/{len(commits)} Conventional Commits, {con_vinetas} con viñetas")


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
            res.anadir("fichero-agente", "fuerte", "Fichero de instrucciones para agentes de IA", str(rel), f"{nombre} → {herramienta}")


def analizar_fichero(res: Resultado, ruta: Path, ubic: str) -> None:
    texto = leer_fichero(ruta)
    if texto is None:
        return
    if "aimarkers: ignore-file" in texto[:2000]:
        res.notas.append(f"{ubic}: omitido por la directiva «aimarkers: ignore-file».")
        return
    ext = ruta.suffix.lower()
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


def analizar_directorio(res: Resultado, raiz: Path) -> None:
    rutas: list[Path] = []
    for actual, dirs, ficheros in os.walk(raiz):
        base = Path(actual)
        for d in list(dirs):
            if d in DIRS_AGENTE:
                res.anadir("carpeta-agente", "fuerte", "Carpeta de configuración de agentes de IA",
                           str((base / d).relative_to(raiz)), f"{d}/ → {DIRS_AGENTE[d]}")
        dirs[:] = [d for d in dirs if d not in DIRS_IGNORADOS and d not in DIRS_AGENTE]
        rutas += [base / f for f in ficheros if not (base / f).is_symlink()]
    comprobar_ficheros_agente(res, raiz, rutas)
    for ruta in rutas:
        analizar_fichero(res, ruta, str(ruta.relative_to(raiz)))
    if (raiz / ".git").exists():
        res.tipo = "repositorio git"
        analizar_git(res, raiz)


def analizar_objetivo(objetivo: str) -> Resultado:
    if re.match(r"https?://", objetivo, I):
        res = Resultado(objetivo, "web (URL)")
        crudo, error = descargar(objetivo)
        if crudo is None:
            res.notas.append(f"No se pudo descargar: {error}")
            return res
        res.ficheros_analizados = 1
        analizar_html(res, crudo, "página")
        m = re.match(r"(https?://[^/]+)", objetivo, I)
        if m:
            llms, _ = descargar(m.group(1) + "/llms.txt", timeout=10)
            if llms and not llms.lstrip().lower().startswith(("<!doctype", "<html")):
                res.anadir("llms-txt", "debil", "El dominio publica /llms.txt (preparado para agentes)", "/llms.txt",
                           llms[:120])
        return res

    ruta = Path(objetivo)
    if ruta.is_dir():
        res = Resultado(str(ruta.resolve()), "directorio")
        analizar_directorio(res, ruta)
        return res
    if ruta.is_file():
        ext = ruta.suffix.lower()
        tipo = "web (HTML)" if ext in EXT_HTML else "texto" if ext in EXT_TEXTO else "código" if ext in EXT_CODIGO else "fichero"
        res = Resultado(str(ruta), tipo)
        comprobar_ficheros_agente(res, ruta.parent, [ruta])
        analizar_fichero(res, ruta, ruta.name)
        if res.ficheros_analizados == 0 and not res.notas:
            res.notas.append("Tipo de fichero no reconocido o binario; no se ha analizado.")
        return res

    res = Resultado(objetivo, "desconocido")
    res.notas.append("No existe el fichero o directorio.")
    return res


# ---------------------------------------------------------------------------
# Informes
# ---------------------------------------------------------------------------

COLORES = {"explicito": "\033[1;31m", "fuerte": "\033[31m", "medio": "\033[33m", "debil": "\033[36m"}
RESET = "\033[0m"
AVISO = ("Los marcadores son indicios, no pruebas. Revisa cada evidencia antes de sacar conclusiones; "
         "la ausencia de marcadores tampoco demuestra autoría humana.")


def informe_consola(resultados: list[Resultado], max_ev: int, color: bool) -> str:
    c = (lambda nivel, t: f"{COLORES[nivel]}{t}{RESET}") if color else (lambda nivel, t: t)
    salida = []
    for res in resultados:
        salida.append("=" * 78)
        salida.append(f"Objetivo : {res.objetivo}")
        salida.append(f"Tipo     : {res.tipo}   ·   {plural(res.ficheros_analizados, 'fichero')} analizado{'' if res.ficheros_analizados == 1 else 's'}")
        salida.append(f"Puntuación: {res.puntuacion()}/100  →  {res.banda()}")
        if res.atribucion_explicita():
            salida.append(c("explicito", "ATRIBUCIÓN EXPLÍCITA: el propio contenido declara una herramienta de IA."))
        grupos = res.por_regla()
        for nivel in ORDEN_NIVEL:
            reglas = [(k, v) for k, v in grupos.items() if v[0].nivel == nivel]
            if not reglas:
                continue
            salida.append("")
            salida.append(c(nivel, f"[{NOMBRE_NIVEL[nivel]} · {PESOS[nivel]} pts]"))
            for _, lista in reglas:
                extra = ""
                if res.ficheros_analizados >= 10 and nivel in ("medio", "debil") and lista[0].regla not in SIN_PREVALENCIA:
                    extra = f", {res.prevalencia(lista):.1%} de los ficheros"
                salida.append(f"  • {lista[0].descripcion} ({len(lista)}{extra}) → +{res.contribucion(lista):.1f}")
                for h in lista[:max_ev]:
                    salida.append(f"      {h.ubicacion}  {h.extracto}")
                if len(lista) > max_ev:
                    salida.append(f"      … {len(lista) - max_ev} más")
        if not res.hallazgos:
            salida.append("\nNo se han encontrado marcadores.")
        if res.notas:
            salida.append("\nNotas:")
            salida += [f"  - {n}" for n in res.notas[:15]]
            if len(res.notas) > 15:
                salida.append(f"  - … {len(res.notas) - 15} notas más")
    salida.append("=" * 78)
    salida.append(AVISO)
    return "\n".join(salida)


def informe_markdown(resultados: list[Resultado], max_ev: int) -> str:
    md = ["# Informe de marcadores de IA", "",
          f"Generado con aimarkers {VERSION} el {datetime.now(timezone.utc).astimezone():%d/%m/%Y %H:%M}.", "", f"> {AVISO}", ""]
    for res in resultados:
        md += [f"## {res.objetivo}", "",
               f"- **Tipo:** {res.tipo}", f"- **Ficheros analizados:** {res.ficheros_analizados}",
               f"- **Puntuación:** {res.puntuacion()}/100 — {res.banda()}",
               f"- **Atribución explícita:** {'sí' if res.atribucion_explicita() else 'no'}", ""]
        if res.hallazgos:
            md += ["| Nivel | Marcador | Veces | Ubicación | Evidencia |", "| --- | --- | --- | --- | --- |"]
            for nivel in ORDEN_NIVEL:
                for lista in res.por_regla().values():
                    if lista[0].nivel != nivel:
                        continue
                    for i, h in enumerate(lista[:max_ev]):
                        ev = html.escape(h.extracto).replace("|", "\\|")
                        md.append(f"| {NOMBRE_NIVEL[nivel] if i == 0 else ''} | {h.descripcion if i == 0 else ''} | "
                                  f"{len(lista) if i == 0 else ''} | `{h.ubicacion}` | {ev} |")
            md.append("")
        else:
            md += ["No se han encontrado marcadores.", ""]
        if res.notas:
            md += ["**Notas**", ""] + [f"- {n}" for n in res.notas] + [""]
    return "\n".join(md)


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
                    evid += f"<li class='mas'>… {len(lista) - max_ev} más</li>"
                filas.append(f"<tr><td><span class='nivel {nivel}'>{NOMBRE_NIVEL[nivel]}</span></td>"
                             f"<td>{e(lista[0].descripcion)}</td><td class='num'>{len(lista)}</td><td><ul>{evid}</ul></td></tr>")
        tabla = (f"<table><thead><tr><th>Nivel</th><th>Marcador</th><th>Veces</th><th>Evidencias</th></tr></thead>"
                 f"<tbody>{''.join(filas)}</tbody></table>") if filas else "<p>No se han encontrado marcadores.</p>"
        notas = ("<details><summary>Notas</summary><ul>" + "".join(f"<li>{e(n)}</li>" for n in res.notas)
                 + "</ul></details>") if res.notas else ""
        explicita = "<p class='explicita'>Atribución explícita: el propio contenido declara una herramienta de IA.</p>" \
            if res.atribucion_explicita() else ""
        bloques.append(f"""
<section>
  <div class="cabecera">
    <div class="marcador {clase}"><span>{p}</span><small>/100</small></div>
    <div><h2>{e(res.objetivo)}</h2>
      <p class="meta">{e(res.tipo)} · {plural(res.ficheros_analizados, 'fichero')} analizado{'' if res.ficheros_analizados == 1 else 's'}</p>
      <p class="banda">{e(res.banda())}</p></div>
  </div>
  {explicita}{tabla}{notas}
</section>""")
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Informe aimarkers</title>
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
.marcador span {{ font-size:26px; font-weight:700 }} .marcador small {{ color:var(--sub); font-size:11px; margin-top:3px }} .alta {{ border-color:var(--exp) }} .media {{ border-color:var(--fue) }}
.baja {{ border-color:var(--med) }} .nula {{ border-color:var(--deb) }}
.explicita {{ color:var(--exp); font-weight:600 }}
table {{ width:100%; border-collapse:collapse; font-size:14px }} th,td {{ text-align:left; vertical-align:top;
  padding:8px; border-top:1px solid var(--borde) }} th {{ color:var(--sub); font-weight:600 }}
td ul {{ margin:0; padding-left:16px }} code {{ font-size:12px; color:var(--sub) }} .num {{ text-align:right }}
.nivel {{ font-size:12px; font-weight:700; padding:2px 8px; border-radius:99px; color:#fff; white-space:nowrap }}
.explicito {{ background:var(--exp) }} .fuerte {{ background:var(--fue) }} .medio {{ background:var(--med) }}
.debil {{ background:var(--deb) }} .mas {{ color:var(--sub); list-style:none }}
details {{ margin-top:12px; color:var(--sub) }}
@media (max-width:640px) {{ table, tbody, tr, td {{ display:block }} thead {{ display:none }}
  td {{ border:none; padding:4px 0 }} tr {{ border-top:1px solid var(--borde); padding:8px 0 }}
  td.num {{ text-align:left; color:var(--sub) }} td.num::before {{ content:"Veces: " }} }}
</style></head>
<body><main>
<h1>Informe de marcadores de IA</h1>
<p class="aviso">aimarkers {VERSION} · {datetime.now(timezone.utc).astimezone():%d/%m/%Y %H:%M} · {e(AVISO)}</p>
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="aimarkers",
        description="Analiza marcadores de IA en código, documentación, webs (fichero o URL) y repositorios Git.")
    ap.add_argument("objetivos", nargs="+", help="Ficheros, directorios, repositorios o URLs a analizar")
    ap.add_argument("--json", metavar="FICHERO", help="Guardar el resultado en JSON")
    ap.add_argument("--md", metavar="FICHERO", help="Guardar el informe en Markdown")
    ap.add_argument("--html", metavar="FICHERO", help="Guardar el informe en HTML")
    ap.add_argument("--evidencias", type=int, default=3, help="Evidencias a mostrar por marcador (por defecto 3)")
    ap.add_argument("--sin-color", action="store_true", help="Desactivar colores en consola")
    ap.add_argument("--silencioso", action="store_true", help="No imprimir el informe en consola")
    ap.add_argument("--umbral", type=int, default=None,
                    help="Devolver código de salida 2 si algún objetivo alcanza esta puntuación (útil en CI)")
    ap.add_argument("--version", action="version", version=f"aimarkers {VERSION}")
    args = ap.parse_args(argv)

    resultados = [analizar_objetivo(o) for o in args.objetivos]

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
