# aimarkers

[![CI](https://github.com/z115666/aimarkers/actions/workflows/ci.yml/badge.svg)](https://github.com/z115666/aimarkers/actions/workflows/ci.yml)
[![CodeQL](https://github.com/z115666/aimarkers/actions/workflows/codeql.yml/badge.svg)](https://github.com/z115666/aimarkers/actions/workflows/codeql.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-blue.svg)](LICENSE)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)

Herramienta de línea de comandos para buscar **marcadores de IA** en código fuente, documentación, webs (fichero HTML o URL) y repositorios Git. Puntúa cada indicio por niveles y genera un informe con las evidencias.

> Los marcadores son indicios, no pruebas. La herramienta ayuda a revisar; la conclusión la pones tú.

## Instalación

### macOS con Homebrew

```bash
brew install z115666/tap/aimarkers
aimarkers --version
```

Para actualizar: `brew update && brew upgrade aimarkers`.

### Cualquier sistema (Windows, macOS, Linux)

```bash
git clone https://github.com/z115666/aimarkers.git
cd aimarkers
python3 aimarkers.py --version
```

Requisitos: Python 3.9 o superior y, para analizar historiales, `git` en el PATH. Solo usa la biblioteca estándar: no hay dependencias que instalar. En Windows usa `py` en lugar de `python3`.

## Uso

Si lo instalaste con Homebrew, usa `aimarkers` en lugar de `python3 aimarkers.py` en los ejemplos.

```bash
# Un repositorio (analiza ficheros + historial Git + ramas)
python3 aimarkers.py ~/Proyectos/mi-repo

# Ficheros sueltos
python3 aimarkers.py informe.md Limpiar-Temp.ps1

# Una web por URL (descarga la página y comprueba /llms.txt)
python3 aimarkers.py https://ejemplo.com

# Una web guardada con "Guardar como…" o con el código fuente copiado
python3 aimarkers.py pagina.html

# Informes
python3 aimarkers.py ./proyecto --html informe.html --md informe.md --json informe.json
```

### Opciones

| Opción | Qué hace |
| --- | --- |
| `--html FICHERO` | Informe HTML autocontenido (modo claro y oscuro, legible en móvil) |
| `--md FICHERO` | Informe en Markdown |
| `--json FICHERO` | Resultado completo en JSON, con `resumen_por_marcador` |
| `--evidencias N` | Evidencias mostradas por marcador (por defecto 3) |
| `--umbral N` | Sale con código 2 si algún objetivo llega a N puntos (útil en CI) |
| `--silencioso` | No imprime el informe en consola |
| `--sin-color` | Consola sin colores |

## Cómo puntúa

| Nivel | Peso | Ejemplos |
| --- | --- | --- |
| Explícito | 40 | `Co-Authored-By: Claude`, `🤖 Generated with Claude Code`, `utm_source=chatgpt.com`, autor `copilot-swe-agent[bot]` |
| Fuerte | 20 | `CLAUDE.md`, `.cursorrules`, `.claude/`, `data-lov-id` (Lovable), «Claro, aquí tienes…», rama `claude/…` |
| Medio | 8 | Comentarios «In a real application…», `your_api_key_here`, emojis en logs, ráfagas de registros cada 2 s |
| Débil | 3 | Muletillas de LLM por densidad, rayas (—), docstrings uniformes, ritmo de frases uniforme |

- Un marcador repetido suma con rendimiento decreciente, hasta 3 veces su peso.
- En proyectos de 10 ficheros o más, los marcadores **medios y débiles** se ponderan por prevalencia: puntúan completos si afectan al 10 % de los ficheros y proporcionalmente menos si son casos aislados. Así un proyecto grande no se dispara por acumulación de rasgos sueltos.
- El estilo de un texto no se valora por debajo de 150 palabras.
- Tope de 100 puntos.

| Puntuación | Valoración |
| --- | --- |
| 0–14 | Sin indicios relevantes (o «indicios débiles» si hay algún marcador medio o fuerte) |
| 15–39 | Indicios débiles |
| 40–69 | Probable asistencia de IA en parte del contenido |
| 70–100 | Alta probabilidad de generación o asistencia intensa |

## Qué analiza

- **Código** (`.py`, `.ps1`, `.js`, `.ts`, `.sh`, `.cs`, `.go`…): firmas de herramientas, restos de chat, ficheros envueltos en vallas ```` ``` ````, comentarios de demostración, placeholders, emojis en logs, pasos numerados, docstrings uniformes, errores genéricos, tipografía rara en código.
- **Texto** (`.md`, `.txt`, `.rst`…): citas de ChatGPT (`oaicite`, `turn0search0`), enlaces con `utm_source=chatgpt.com`, cierres de chat, huecos `[Nombre de la empresa]`, muletillas en español e inglés, viñetas «**Término:**», títulos con emoji, ritmo de frases.
- **Webs**: huellas de Lovable, v0, Bolt, Readdy, Base44 y similares; imágenes con nombre de generador (`ChatGPT Image…`, `DALL·E`, `Gemini_Generated_Image`); stack por defecto de los generadores; framework `vinext`; **datos embebidos** (ráfagas de `created_at` y precisión de coordenadas); el texto visible con las reglas de texto.
- **Repositorios Git**: trailers `Co-authored-by`, pies «Generated with», autores bot, ramas de agentes, commits enormes, mensajes uniformes; además, ficheros y carpetas de agentes (`CLAUDE.md`, `AGENTS.md`, `.cursor/`, `.github/copilot-instructions.md`…).

Ignora `node_modules`, `.venv`, `dist`, `build`, `.git` (como ficheros) y el código minificado.

## Excluir ficheros

Añade `aimarkers: ignore-file` en las primeras líneas de un fichero para que no se analice. Lo usa el propio `aimarkers.py`, que contiene todos los patrones que busca.

Ojo: la carpeta `tests/fixtures/` contiene ejemplos con IA a propósito. Si analizas la carpeta de la herramienta entera, saldrá con puntuación alta.

## Pruebas

```bash
python3 -m unittest discover tests -v
```

Incluyen casos con IA (código, texto, web generada, repositorio con commits de agente creado al vuelo, web sintética con carga masiva de datos) y casos humanos (notas escritas a mano y la biblioteca estándar de Python), para vigilar los falsos positivos.

Para desarrollar, instala las herramientas de análisis con versiones y hashes fijados:

```bash
python3 -m pip install --require-hashes --no-deps -r requirements-dev.txt
ruff check .
bandit -c pyproject.toml -r aimarkers.py
```

Validación hecha: la biblioteca estándar de Python y sus paquetes (11.630 ficheros) puntúa 3/100; una web real con una carga masiva de 144 registros en 5 minutos se detecta como ráfaga; el repositorio `psf/requests` puntúa 48/100 por un commit real de marzo de 2026 con `Co-Authored-By: Claude Opus 4.6`.

## Ampliar reglas

Las reglas están al principio de `aimarkers.py`, en listas de tuplas `(id, nivel, descripción, patrón)`:

- `REGLAS_GENERALES`: se aplican a todo.
- `REGLAS_CHAT` y `REGLA_HUECO`: restos de conversación.
- `REGLAS_CODIGO_LINEA`: línea a línea en código.
- `REGLAS_HTML`: webs.
- `MULETILLAS_ES` / `MULETILLAS_EN`: frases típicas (solo cuentan por densidad).
- `FICHEROS_AGENTE` / `DIRS_AGENTE`: nombres de ficheros y carpetas de agentes.

Añade la regla, crea un fixture en `tests/fixtures/` y una prueba en `tests/test_aimarkers.py`.

## Seguridad

aimarkers está diseñado para analizar contenido no confiable. Invoca `git` con una configuración endurecida para que un repositorio manipulado no pueda ejecutar comandos (hooks, `fsmonitor`, `textconv`), acota las expresiones regulares frente a ReDoS, no sigue enlaces simbólicos, limita tamaños y solo descarga por http(s). El detalle, el modelo de amenazas y cómo informar de vulnerabilidades están en [SECURITY.md](SECURITY.md).

## Limitaciones

- No comprueba si el código usa APIs inventadas: eso exige ejecutarlo o revisarlo contra la documentación.
- No lee metadatos C2PA de imágenes; para eso usa `exiftool imagen.png`.
- La ausencia de marcadores no demuestra autoría humana: los trailers y pies se pueden borrar y los textos se pueden reescribir.
- Las URLs que necesitan JavaScript para mostrar contenido se analizan solo por su HTML inicial. En ese caso, guarda la página desde el navegador y analiza el fichero.

---
Autor: Alberto · [Licencia MIT](LICENSE)
