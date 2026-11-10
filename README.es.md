# aimarkers

[English](README.md) · **Español**

[![CI](https://github.com/z115666/aimarkers/actions/workflows/ci.yml/badge.svg)](https://github.com/z115666/aimarkers/actions/workflows/ci.yml)
[![CodeQL](https://github.com/z115666/aimarkers/actions/workflows/codeql.yml/badge.svg)](https://github.com/z115666/aimarkers/actions/workflows/codeql.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-blue.svg)](LICENSE)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)

Herramienta de línea de comandos para buscar **marcadores de IA** en código fuente, documentación, webs (fichero HTML o URL), **imágenes** (credenciales C2PA, IPTC, EXIF y parámetros de generación) y repositorios Git. Puntúa cada indicio por niveles y genera un informe con las evidencias, en español o en inglés.

> Los marcadores son indicios, no pruebas. La herramienta ayuda a revisar; la conclusión la pones tú.

## Instalación

### macOS con Homebrew

```bash
brew install z115666/tap/aimarkers
aimarkers --version

# Opcional: verificación criptográfica de las firmas C2PA
brew install c2patool
```

Para actualizar: `brew update && brew upgrade aimarkers`.

### Cualquier sistema (Windows, macOS, Linux)

```bash
git clone https://github.com/z115666/aimarkers.git
cd aimarkers
python3 aimarkers.py --version
```

Requisitos: Python 3.9 o superior y, para analizar historiales, `git` en el PATH. Solo usa la biblioteca estándar: no hay dependencias que instalar. En Windows usa `py` en lugar de `python3`. [`c2patool`](https://github.com/contentauth/c2pa-rs/tree/main/cli) es opcional y solo hace falta para verificar firmas C2PA.

## Uso

Si lo instalaste con Homebrew, usa `aimarkers` en lugar de `python3 aimarkers.py` en los ejemplos.

```bash
# Un repositorio (analiza ficheros, imágenes, historial Git y ramas)
python3 aimarkers.py ~/Proyectos/mi-repo

# Ficheros sueltos
python3 aimarkers.py informe.md Limpiar-Temp.ps1

# Imágenes
python3 aimarkers.py foto.jpg ~/Descargas/*.png

# Una web por URL (descarga la página y sus imágenes y comprueba /llms.txt)
python3 aimarkers.py https://ejemplo.com

# Una web guardada con "Guardar como…"
python3 aimarkers.py pagina.html

# Informes
python3 aimarkers.py ./proyecto --html informe.html --md informe.md --json informe.json
```

### Idioma

La salida sale en el idioma del sistema (español si el *locale* empieza por `es`, inglés en otro caso). Para forzarlo:

```bash
aimarkers --lang en informe.md
AIMARKERS_LANG=es aimarkers informe.md
```

El idioma afecta a la consola y a los informes. Los identificadores de los marcadores (`coautor-ia`, `c2pa-ia`…) y las claves del JSON no cambian, para que los scripts que los usan sigan funcionando.

### Opciones

| Opción | Qué hace |
| --- | --- |
| `--html FICHERO` | Informe HTML autocontenido (modo claro y oscuro, legible en móvil) |
| `--md FICHERO` | Informe en Markdown |
| `--json FICHERO` | Resultado completo en JSON, con `resumen_por_marcador` |
| `--lang es\|en` | Idioma de la salida |
| `--evidencias N` | Evidencias mostradas por marcador (por defecto 3) |
| `--umbral N` | Sale con código 2 si algún objetivo llega a N puntos (útil en CI) |
| `--sin-imagenes` | No analiza las imágenes enlazadas desde las webs |
| `--silencioso` | No imprime el informe en consola |
| `--sin-color` | Consola sin colores |

Cada opción tiene también su nombre en inglés: `--evidence`, `--threshold`, `--no-images`, `--quiet`, `--no-color`.

## Cómo puntúa

| Nivel | Peso | Ejemplos |
| --- | --- | --- |
| Explícito | 40 | `Co-Authored-By: Claude`, `🤖 Generated with Claude Code`, `utm_source=chatgpt.com`, autor `copilot-swe-agent[bot]`, C2PA o IPTC que declaran imagen generada con IA, parámetros de Stable Diffusion |
| Fuerte | 20 | `CLAUDE.md`, `.cursorrules`, `.claude/`, `data-lov-id` (Lovable), «Claro, aquí tienes…», rama `claude/…`, `Software: Midjourney` en EXIF |
| Medio | 8 | Comentarios «In a real application…», `your_api_key_here`, emojis en logs, ráfagas de registros cada 2 s |
| Débil | 3 | Muletillas de LLM por densidad, rayas (—), docstrings uniformes, ritmo de frases uniforme |

- Un marcador repetido suma con rendimiento decreciente, hasta 3 veces su peso.
- En proyectos de 10 ficheros o más, los marcadores **medios y débiles** se ponderan por prevalencia: puntúan completos si afectan al 10 % de los ficheros y proporcionalmente menos si son casos aislados.
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
- **Webs**: huellas de Lovable, v0, Bolt, Readdy, Base44 y similares; imágenes con nombre de generador (`ChatGPT Image…`, `DALL·E`, `Gemini_Generated_Image`); stack por defecto de los generadores; framework `vinext`; **datos embebidos** (ráfagas de `created_at` y precisión de coordenadas); el texto visible con las reglas de texto; y los **metadatos de las imágenes** de la página.
- **Imágenes** (`.jpg`, `.png`, `.webp`, `.heic`, `.avif`, `.tif`…): ver la sección siguiente.
- **Repositorios Git**: trailers `Co-authored-by`, pies «Generated with», autores bot, ramas de agentes, commits enormes, mensajes uniformes; además, ficheros y carpetas de agentes (`CLAUDE.md`, `AGENTS.md`, `.cursor/`, `.github/copilot-instructions.md`…).

Ignora `node_modules`, `.venv`, `dist`, `build`, `.git` (como ficheros) y el código minificado.

## Imágenes: C2PA y otros metadatos

[C2PA](https://c2pa.org/) (*Content Credentials*) es un estándar abierto para adjuntar a un fichero un **manifiesto firmado** con su procedencia: qué herramienta lo creó, qué acciones se le aplicaron y si se generó con IA. Lo incluyen, entre otros, ChatGPT/DALL·E, Adobe Firefly, Microsoft Designer, Google y algunas cámaras (Leica, Sony, Nikon). El manifiesto va dentro de la imagen en cajas JUMBF con datos CBOR y una firma COSE con un certificado X.509.

aimarkers lee, sin dependencias:

| Fuente | Dónde está | Qué busca | Nivel |
| --- | --- | --- | --- |
| Manifiesto C2PA | JPEG (APP11), PNG (`caBX`), WebP (`C2PA`), HEIC/AVIF/TIFF | `digitalSourceType` = `trainedAlgorithmicMedia` (generada con IA) o `compositeWithTrainedAlgorithmicMedia` (editada con IA); herramienta de IA como generador o `softwareAgent`. Muestra también el firmante del certificado | Explícito |
| IPTC en XMP | `Iptc4xmpExt:DigitalSourceType` | Los mismos valores de origen digital | Explícito |
| Textos PNG | `tEXt`, `zTXt`, `iTXt` | `parameters` de Stable Diffusion (A1111/Forge), `prompt`/`workflow` de ComfyUI, InvokeAI, NovelAI | Explícito |
| EXIF y XMP | `Software`, `Artist`, `ImageDescription`, `CreatorTool`… | Nombres de generadores (Midjourney, DALL·E, Firefly, Stable Diffusion, Gemini…) | Fuerte |

Un manifiesto C2PA **sin** declaración de IA (por ejemplo, una foto de cámara) no puntúa: aparece como nota con el origen, la herramienta y el firmante.

**Verificación de la firma.** aimarkers interpreta el manifiesto, pero no verifica la criptografía. Si `c2patool` está instalado (`brew install c2patool`), lo usa para comprobar que la firma es válida y que la imagen no se ha modificado después de firmarla, y lo indica en la evidencia: «válida, certificado de confianza», «válida, certificado no reconocido» o «NO VÁLIDA». Sin `c2patool`, la evidencia dice «no verificada».

**Límites.** Los metadatos se pierden con facilidad: una captura de pantalla, muchas redes sociales y muchos editores los eliminan. La ausencia de C2PA no indica nada. Y un manifiesto sin verificar se puede falsificar; para una conclusión firme, instala `c2patool`.

**Imágenes de webs.** En modo URL, aimarkers descarga hasta 15 imágenes de la página (`<img src>`, `og:image`, `twitter:image`), solo por http(s) y de 15 MB como máximo cada una, a una carpeta temporal que se borra al terminar. Con un HTML local, solo analiza imágenes que estén dentro de la carpeta del HTML. `--sin-imagenes` desactiva ambas cosas.

## Excluir ficheros

Añade `aimarkers: ignore-file` en las primeras líneas de un fichero para que no se analice. Lo usa el propio `aimarkers.py`, que contiene todos los patrones que busca.

Ojo: la carpeta `tests/fixtures/` contiene ejemplos con marcadores a propósito. Si analizas la carpeta de la herramienta entera, saldrá con puntuación alta.

## Pruebas

```bash
python3 -m unittest discover tests -v
```

Incluyen casos positivos (código, texto, web generada, repositorio con commits de agente creado al vuelo, web sintética con carga masiva de datos, imágenes con C2PA firmado, IPTC, EXIF y parámetros de Stable Diffusion y ComfyUI) y casos negativos (notas escritas a mano, la biblioteca estándar de Python, una foto de cámara con C2PA y otra con EXIF normal). También prueban entradas hostiles: bombas de descompresión, cajas JUMBF malformadas e imágenes corrompidas al azar.

Para desarrollar, instala las herramientas de análisis con versiones y hashes fijados:

```bash
python3 -m pip install --require-hashes --no-deps -r requirements-dev.txt
ruff check .
bandit -c pyproject.toml -r aimarkers.py
```

Validación hecha: la biblioteca estándar de Python (11.630 ficheros) puntúa 3/100; 400 imágenes del sistema no dan ningún falso positivo; una web real con 144 registros cargados en 5 minutos se detecta como ráfaga; el repositorio `psf/requests` puntúa 48/100 por un commit real de marzo de 2026 con `Co-Authored-By: Claude Opus 4.6`.

## Ampliar reglas

Las reglas están al principio de `aimarkers.py`, en listas de tuplas `(id, nivel, patrón)`. Las descripciones en los dos idiomas están en el diccionario `DESCRIPCIONES`, y los demás textos en `TEXTOS`.

- `REGLAS_GENERALES`: se aplican a todo.
- `REGLAS_CHAT` y `REGLA_HUECO`: restos de conversación.
- `REGLAS_CODIGO_LINEA`: línea a línea en código.
- `REGLAS_HTML`: webs.
- `RE_GENERADOR_META`: nombres de generadores en metadatos de imágenes.
- `MULETILLAS_ES` / `MULETILLAS_EN`: frases típicas (solo cuentan por densidad).
- `FICHEROS_AGENTE` / `DIRS_AGENTE`: nombres de ficheros y carpetas de agentes.

Añade la regla y su descripción en español e inglés, crea un fixture en `tests/fixtures/` y una prueba en `tests/test_aimarkers.py`.

## Seguridad

aimarkers está diseñado para analizar contenido no confiable. Invoca `git` con una configuración endurecida para que un repositorio manipulado no pueda ejecutar comandos (hooks, `fsmonitor`, `textconv`), acota las expresiones regulares frente a ReDoS, limita la descompresión y la profundidad al leer imágenes, no sigue enlaces simbólicos, limita tamaños y solo descarga por http(s). El detalle, el modelo de amenazas y cómo informar de vulnerabilidades están en [SECURITY.es.md](SECURITY.es.md).

## Limitaciones

- No comprueba si el código usa APIs inventadas: eso exige ejecutarlo o revisarlo contra la documentación.
- No detecta imágenes generadas con IA a partir de los píxeles, solo a partir de sus metadatos. Tampoco lee marcas de agua invisibles como SynthID.
- La ausencia de marcadores no demuestra autoría humana: los trailers y pies se pueden borrar, los textos se pueden reescribir y los metadatos se pueden eliminar.
- Las URLs que necesitan JavaScript para mostrar contenido se analizan solo por su HTML inicial. En ese caso, guarda la página desde el navegador y analiza el fichero.

---
Autor: Alberto · [Licencia MIT](LICENSE)
