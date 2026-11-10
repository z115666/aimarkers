# AI markers report

Generated with aimarkers 1.1.0 on 2026-11-10 20:27.

> Markers are signs, not proof. Review every piece of evidence before drawing conclusions; the absence of markers does not prove human authorship either.

## tests/fixtures/web/actividades_sintetico.html

- **Type:** web page (HTML)
- **Files analysed:** 1
- **Score:** 14/100 — Weak signs: compatible traits, nothing conclusive
- **Explicit attribution:** no

| Level | Marker | Count | Location | Evidence |
| --- | --- | --- | --- | --- |
| Medium | Burst of records created seconds apart (automated load) | 1 | `actividades_sintetico.html:embedded data` | 25 records between 2026-11-09 23:42:45+01:00 and 23:43:33 (local time), median gap 2.0 s |
| Weak | Framework built with AI (Cloudflare vinext) | 1 | `actividades_sintetico.html:3` | ipt src=&quot;/_next/static/chunks/vinext-EJEMPLO.js&quot; type=&quot;module&quot;&gt;&lt;/script&gt;&lt;/he |
| Weak | Mixed coordinate precision (two data sources) | 1 | `actividades_sintetico.html:embedded data` | 26 with ≤6 decimals, 24 with ≥7 decimals, 0 near-round, out of 50 |

## tests/fixtures/codigo_ia

- **Type:** directory
- **Files analysed:** 3
- **Score:** 100/100 — High likelihood of AI generation or heavy AI assistance
- **Explicit attribution:** yes

| Level | Marker | Count | Location | Evidence |
| --- | --- | --- | --- | --- |
| Explicit | AI tool signature in the content | 1 | `backup_manager.py:3` | &quot;&quot;&quot; Backup manager utility. Generated with Claude Code &quot;&quot;&quot; import os import shutil API_KEY = |
| Strong | Configuration folder for AI agents | 1 | `.claude` | .claude/ → Claude Code |
| Strong | Instruction file for AI agents | 2 | `.cursorrules` | .cursorrules → Cursor |
|  |  |  | `CLAUDE.md` | CLAUDE.md → Claude Code |
| Strong | Chat phrase pasted into the file | 1 | `Limpiar-Temp.ps1:1` | # Here&#x27;s the updated script with improved error handling: `` |
| Strong | File wrapped in a Markdown fence (```) pasted from the chat | 1 | `Limpiar-Temp.ps1:2` | ```powershell |
| Medium | Demo-style code comment | 2 | `Limpiar-Temp.ps1:8` | # En un entorno real, aquí iría la lógica de registro |
|  |  |  | `backup_manager.py:47` | # In a real application, you would upload this to cloud storage |
| Medium | Emojis in console or log messages | 2 | `Limpiar-Temp.ps1:10` | 1 line; e.g. Write-Host &quot;✅ Limpieza completada&quot; |
|  |  |  | `backup_manager.py:24` | 3 lines; e.g. print(&quot;❌ Source folder not found&quot;) |
| Medium | Example value left unreplaced | 1 | `backup_manager.py:8` | API_KEY = &quot;your_api_key_here&quot; # Replace with your actual API key |
| Weak | Numbered step comments («# Step 1:») | 2 | `Limpiar-Temp.ps1:3` | 3 step comments; e.g. # Paso 1: Obtener los ficheros temporales |
|  |  |  | `backup_manager.py:22` | 3 step comments; e.g. # Step 1: Validate input |
| Weak | Args/Returns docstrings on almost every function | 1 | `backup_manager.py` | 5 of 5 functions |
| Weak | Repeated generic error handling («An error occurred») | 1 | `backup_manager.py` | 3 blocks |

## tests/fixtures/texto/articulo_ia.md

- **Type:** text
- **Files analysed:** 1
- **Score:** 72/100 — High likelihood of AI generation or heavy AI assistance
- **Explicit attribution:** yes

| Level | Marker | Count | Location | Evidence |
| --- | --- | --- | --- | --- |
| Explicit | Link copied from an AI assistant (utm_source=chatgpt.com…) | 1 | `articulo_ia.md:19` | a](https://www.incibe.es/guia?utm_source=chatgpt.com). Espero que te sea útil. ¿Quieres que |
| Strong | Typical chat-reply closing line | 1 | `articulo_ia.md:21` | uia?utm_source=chatgpt.com). Espero que te sea útil. ¿Quieres que añada una lista de verifi |
| Weak | High density of typical LLM stock phrases | 1 | `articulo_ia.md` | 13 occurrences (41.8/1000 words): cabe destacar, desempeña un papel crucial, en definitiva, en el panorama actual, es importante señalar, fomentar, no solo a... |
| Weak | Systematic «**Term:** explanation» bullet points | 1 | `articulo_ia.md` | 5 of 5 bullets |
| Weak | Headings that start with an emoji | 1 | `articulo_ia.md` | 4 headings |
| Weak | Very uniform sentence length (low burstiness) | 1 | `articulo_ia.md` | 22 sentences, mean 11.2 words, coefficient of variation 0.26 |

## tests/fixtures/web/landing.html

- **Type:** web page (HTML)
- **Files analysed:** 1
- **Score:** 93/100 — High likelihood of AI generation or heavy AI assistance
- **Explicit attribution:** no

| Level | Marker | Count | Location | Evidence |
| --- | --- | --- | --- | --- |
| Strong | Lovable fingerprint (data-lov-*, gptengineer, lovable-tagger) | 2 | `landing.html:2` | &lt;/title&gt; &lt;script src=&quot;https://cdn.gpteng.co/gptengineer.js&quot; type=&quot;module&quot;&gt;&lt;/script&gt; |
|  |  |  | `landing.html:3` | &quot;&gt;&lt;/script&gt;&lt;/head&gt; &lt;body&gt;&lt;div data-lov-id=&quot;src/pages/Index.tsx:12:4&quot; class=&quot;bg-gr |
| Strong | v0 (Vercel) fingerprint | 1 | `landing.html:1` | &quot;&gt;&lt;head&gt;&lt;meta charset=&quot;utf-8&quot;&gt;&lt;meta name=&quot;generator&quot; content=&quot;v0.app&quot;&gt;&lt;title&gt;Clínica Dental Sonrisa&lt;/title&gt; &lt; |
| Strong | Image named after an AI generator | 1 | `landing.html:5` | &quot;&gt;Reservar cita&lt;/button&gt; &lt;img src=&quot;/assets/ChatGPT Image 3 nov 2026, 10_12_45.png&quot; alt=&quot;equipo&quot;&gt; &lt;h1&gt;Tu sonrisa, nuestra p |
| Strong | Chat phrase pasted into the file | 1 | `landing.html (visible text):4` | Tu sonrisa, nuestra prioridad Claro, aquí tienes el texto para la sección de bienvenida: |
| Weak | Default stack of AI builders (shadcn/ui, lucide, gradients) | 1 | `landing.html` | 3 of 3 traits present |

**Notes**

- landing.html: meta generator = «v0.app»

## tests/fixtures/imagenes/c2pa_ia.png

- **Type:** image
- **Files analysed:** 1
- **Score:** 40/100 — Likely AI assistance in part of the content
- **Explicit attribution:** yes

| Level | Marker | Count | Location | Evidence |
| --- | --- | --- | --- | --- |
| Explicit | C2PA Content Credentials declare AI generation | 1 | `c2pa_ia.png:C2PA` | source: AI-generated; tool: Prueba Generador IA 1.0; signer: C2PA Test Signing Cert (C2PA Signer); signature: not verified (install c2patool) |

**Notes**

- c2patool is not installed: C2PA signatures were not verified (brew install c2patool).

## tests/fixtures/imagenes/sd_parametros.png

- **Type:** image
- **Files analysed:** 1
- **Score:** 40/100 — Likely AI assistance in part of the content
- **Explicit attribution:** yes

| Level | Marker | Count | Location | Evidence |
| --- | --- | --- | --- | --- |
| Explicit | Stable Diffusion/ComfyUI/InvokeAI generation parameters in the image | 1 | `sd_parametros.png:PNG «parameters»` | a lighthouse at dusk, oil painting Negative prompt: blurry Steps: 30, Sampler: DPM++ 2M Karras, CFG scale: 7, Seed: 12345, Size: 512x512, Model: sd_xl |

## tests/fixtures/imagenes/c2pa_camara.jpg

- **Type:** image
- **Files analysed:** 1
- **Score:** 0/100 — No relevant signs
- **Explicit attribution:** no

No markers found.

**Notes**

- c2patool is not installed: C2PA signatures were not verified (brew install c2patool).
- c2pa_camara.jpg: C2PA credentials without an AI declaration (source: digital capture (camera); tool: Prueba Cámara 2.3; signer: C2PA Test Signing Cert (C2PA Signer); signature: not verified (install c2patool)).
