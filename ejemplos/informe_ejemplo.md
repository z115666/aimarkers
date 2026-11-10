# Informe de marcadores de IA

Generado con aimarkers 1.0.0 el 10/11/2026 15:43.

> Los marcadores son indicios, no pruebas. Revisa cada evidencia antes de sacar conclusiones; la ausencia de marcadores tampoco demuestra autoría humana.

## tests/fixtures/web/actividades_sintetico.html

- **Tipo:** web (HTML)
- **Ficheros analizados:** 1
- **Puntuación:** 14/100 — Indicios débiles: rasgos compatibles, nada concluyente
- **Atribución explícita:** no

| Nivel | Marcador | Veces | Ubicación | Evidencia |
| --- | --- | --- | --- | --- |
| Medio | Ráfaga de registros creados cada pocos segundos (carga automatizada) | 1 | `actividades_sintetico.html:datos embebidos` | 25 registros entre 2026-11-09 23:42:45+01:00 y 23:43:33 (hora local), separación mediana 2.0 s |
| Débil | Framework construido con IA (vinext de Cloudflare) | 1 | `actividades_sintetico.html:3` | ipt src=&quot;/_next/static/chunks/vinext-EJEMPLO.js&quot; type=&quot;module&quot;&gt;&lt;/script&gt;&lt;/he |
| Débil | Precisión de coordenadas mezclada (dos orígenes de datos) | 1 | `actividades_sintetico.html:datos embebidos` | 26 con ≤6 decimales, 24 con ≥7 decimales, 0 casi redondas, de 50 |

## tests/fixtures/codigo_ia

- **Tipo:** directorio
- **Ficheros analizados:** 3
- **Puntuación:** 100/100 — Alta probabilidad de generación o asistencia intensa con IA
- **Atribución explícita:** sí

| Nivel | Marcador | Veces | Ubicación | Evidencia |
| --- | --- | --- | --- | --- |
| Explícito | Firma de herramienta de IA en el contenido | 1 | `backup_manager.py:3` | &quot;&quot;&quot; Backup manager utility. Generated with Claude Code &quot;&quot;&quot; import os import shutil API_KEY = |
| Fuerte | Carpeta de configuración de agentes de IA | 1 | `.claude` | .claude/ → Claude Code |
| Fuerte | Fichero de instrucciones para agentes de IA | 2 | `.cursorrules` | .cursorrules → Cursor |
|  |  |  | `CLAUDE.md` | CLAUDE.md → Claude Code |
| Fuerte | Frase de chat copiada dentro del fichero | 1 | `Limpiar-Temp.ps1:1` | # Here&#x27;s the updated script with improved error handling: `` |
| Fuerte | Fichero envuelto en una valla Markdown (```) copiada del chat | 1 | `Limpiar-Temp.ps1:2` | ```powershell |
| Medio | Comentario de código de demostración | 2 | `Limpiar-Temp.ps1:8` | # En un entorno real, aquí iría la lógica de registro |
|  |  |  | `backup_manager.py:47` | # In a real application, you would upload this to cloud storage |
| Medio | Emojis en mensajes de consola o log | 2 | `Limpiar-Temp.ps1:10` | 1 línea; p. ej. Write-Host &quot;✅ Limpieza completada&quot; |
|  |  |  | `backup_manager.py:24` | 3 líneas; p. ej. print(&quot;❌ Source folder not found&quot;) |
| Medio | Valor de ejemplo sin sustituir | 1 | `backup_manager.py:8` | API_KEY = &quot;your_api_key_here&quot; # Replace with your actual API key |
| Débil | Comentarios numerados por pasos («# Step 1:») | 2 | `Limpiar-Temp.ps1:3` | 3 comentarios de paso; p. ej. # Paso 1: Obtener los ficheros temporales |
|  |  |  | `backup_manager.py:22` | 3 comentarios de paso; p. ej. # Step 1: Validate input |
| Débil | Docstrings Args/Returns en casi todas las funciones | 1 | `backup_manager.py` | 5 de 5 funciones |
| Débil | Manejo de errores genérico repetido («An error occurred») | 1 | `backup_manager.py` | 3 bloques |

## tests/fixtures/texto/articulo_ia.md

- **Tipo:** texto
- **Ficheros analizados:** 1
- **Puntuación:** 72/100 — Alta probabilidad de generación o asistencia intensa con IA
- **Atribución explícita:** sí

| Nivel | Marcador | Veces | Ubicación | Evidencia |
| --- | --- | --- | --- | --- |
| Explícito | Enlace copiado desde ChatGPT (utm_source=chatgpt.com/openai) | 1 | `articulo_ia.md:19` | a](https://www.incibe.es/guia?utm_source=chatgpt.com). Espero que te sea útil. ¿Quieres que |
| Fuerte | Cierre típico de respuesta de chat | 1 | `articulo_ia.md:21` | uia?utm_source=chatgpt.com). Espero que te sea útil. ¿Quieres que añada una lista de verifi |
| Débil | Densidad alta de muletillas típicas de LLM | 1 | `articulo_ia.md` | 13 apariciones (41.8/1000 palabras): cabe destacar, desempeña un papel crucial, en definitiva, en el panorama actual, es importante señal... |
| Débil | Viñetas con «**Término:** explicación» de forma sistemática | 1 | `articulo_ia.md` | 5 de 5 viñetas |
| Débil | Títulos que empiezan con emoji | 1 | `articulo_ia.md` | 4 títulos |
| Débil | Frases de longitud muy uniforme (baja burstiness) | 1 | `articulo_ia.md` | 22 frases, media 11.2 palabras, coef. de variación 0.26 |

## tests/fixtures/web/landing.html

- **Tipo:** web (HTML)
- **Ficheros analizados:** 1
- **Puntuación:** 93/100 — Alta probabilidad de generación o asistencia intensa con IA
- **Atribución explícita:** no

| Nivel | Marcador | Veces | Ubicación | Evidencia |
| --- | --- | --- | --- | --- |
| Fuerte | Huella de Lovable (data-lov-*, gptengineer, lovable-tagger) | 2 | `landing.html:2` | &lt;/title&gt; &lt;script src=&quot;https://cdn.gpteng.co/gptengineer.js&quot; type=&quot;module&quot;&gt;&lt;/script&gt; |
|  |  |  | `landing.html:3` | &quot;&gt;&lt;/script&gt;&lt;/head&gt; &lt;body&gt;&lt;div data-lov-id=&quot;src/pages/Index.tsx:12:4&quot; class=&quot;bg-gr |
| Fuerte | Huella de v0 (Vercel) | 1 | `landing.html:1` | &quot;&gt;&lt;head&gt;&lt;meta charset=&quot;utf-8&quot;&gt;&lt;meta name=&quot;generator&quot; content=&quot;v0.app&quot;&gt;&lt;title&gt;Clínica Dental Sonrisa&lt;/title&gt; &lt; |
| Fuerte | Imagen con nombre de generador de IA | 1 | `landing.html:5` | &quot;&gt;Reservar cita&lt;/button&gt; &lt;img src=&quot;/assets/ChatGPT Image 3 nov 2026, 10_12_45.png&quot; alt=&quot;equipo&quot;&gt; &lt;h1&gt;Tu sonrisa, nuestra p |
| Fuerte | Frase de chat copiada dentro del fichero | 1 | `landing.html (texto visible):4` | Tu sonrisa, nuestra prioridad Claro, aquí tienes el texto para la sección de bienvenida: |
| Débil | Stack por defecto de los generadores (shadcn/ui, lucide, degradados) | 1 | `landing.html` | 3 de 3 rasgos presentes |

**Notas**

- landing.html: meta generator = «v0.app»
