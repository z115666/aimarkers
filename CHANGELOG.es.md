# Cambios

[English](CHANGELOG.md) · **Español**

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [1.9.0] - 2026-11-12

### Añadido
- Las webs que no envían su certificado intermedio se analizan como lo haría un navegador: el intermedio se descarga de la dirección que indica el certificado (AIA), la verificación sigue activa y la raíz tiene que seguir siendo de confianza. Nuevo hallazgo de seguridad: «El servidor no envía la cadena de certificados completa».

## [1.8.0] - 2026-11-12

### Añadido
- Webs internas con certificado propio: `--ca fichero.pem` confía en una CA interna o en el certificado del servidor y mantiene la verificación; `--confiar-certificado` (y la opción **Confiar en el certificado de esta web** de la interfaz) acepta un certificado no válido solo para el host analizado. El certificado sigue apareciendo como hallazgo de seguridad y, cuando una web falla por su certificado, el informe explica cómo analizarla.

## [1.7.0] - 2026-11-11

### Añadido
- Documentos de Office y PDF: se analizan ficheros de Word, PowerPoint, Excel, LibreOffice y PDF. aimarkers lee sus metadatos (herramientas de IA y librerías con las que los asistentes crean ficheros, como python-docx, python-pptx, openpyxl, PptxGenJS y ReportLab), su texto (con las reglas habituales más el Markdown literal pegado desde un chat) y las imágenes que llevan dentro. Solo biblioteca estándar, con límites frente a bombas zip y PDF; pypdf es opcional para los PDF con fuentes incrustadas.
- Capturas de pantalla: origen según metadatos o nombre de fichero, tamaño de pantalla real, un marcador medio para capturas con tamaño de salida de generador (como el 1024×1536 de ChatGPT) y sin programa de captura, y detección de zonas que pasaron por JPEG dentro de una captura sin pérdida (recortes pegados). Nueva columna «Captura y edición» en la lectura de píxeles.

## [1.6.0] - 2026-11-11

### Añadido
- Lectura de píxeles de las imágenes (opcional, con Pillow y NumPy): ruido de sensor, huella periódica en la rejilla de 8 píxeles y tamaños de salida de generadores, con la marca y el modelo de la cámara como contraindicio. Solo añade marcadores débiles o medios, con umbrales que no marcaron ninguna foto real en el conjunto de calibración. Se muestra como tabla en la interfaz y en los informes; `--sin-pixeles` la desactiva.
- Dependencias con vulnerabilidades conocidas: lee las versiones exactas de `requirements*.txt`, `poetry.lock`, `uv.lock`, `pdm.lock`, `Pipfile.lock`, `package-lock.json`, `npm-shrinkwrap.json`, `yarn.lock`, `composer.lock`, `Gemfile.lock`, `go.mod`, `Cargo.lock` y `packages.lock.json` y las contrasta con OSV.dev, con los avisos, la peor severidad y la versión que lo corrige. También contrasta las librerías JavaScript detectadas en las webs. `--sin-osv` lo desactiva; la interfaz tiene la opción **Consultar bases públicas** para DNS y OSV.dev.
- Más secretos detectados en código y webs: Anthropic, Hugging Face, GitLab, npm, PyPI, Azure Storage, Twilio, Shopify, Mailchimp, bots de Telegram, webhooks de Teams y Discord y URL de bases de datos con contraseña (la contraseña nunca se muestra).
- README: nueva sección «Cómo decide» que explica los tres tipos de evidencia y qué se lee en cada tipo de contenido.

## [1.5.0] - 2026-11-11

### Añadido
- Botón para detener el análisis en la pantalla de progreso, por si se inicia por error. Cancela las subidas en curso y borra sus ficheros; el análisis se detiene en el siguiente punto de control (normalmente en menos de un segundo), borra sus carpetas temporales y no genera informe.
- Línea de comandos: Ctrl+C detiene el análisis limpiamente con código de salida 130 y un mensaje, sin traza de error.

## [1.4.1] - 2026-11-11

### Cambiado
- Interfaz: el contenido se centra en pantallas anchas y los resultados muestran un panel lateral con el resumen (puntuación de IA, CVSS máximo, hallazgos por riesgo), un índice de la página que sigue el desplazamiento y botones para repetir el análisis y guardar el informe. Por debajo de 1280 px el panel se oculta y la composición sigue en una columna.

## [1.4.0] - 2026-11-11

### Añadido
- Seguridad: comprobaciones de correo y DNS (SPF, DMARC, DNSSEC, CAA) por DNS sobre HTTPS (`--sin-dns` para omitirlas); privacidad y servicios de terceros (rastreadores, Google Fonts, YouTube sin modo de privacidad); *reverse tabnabbing*; Cross-Origin-Opener-Policy; enumeración de usuarios de WordPress con `?author=1` y versión mediante `readme.html` en modo activo.
- Inventario de componentes (CMS, plugins, temas, librerías, servidor) y lista de servicios de terceros en la interfaz y los informes.
- Hallazgos segmentados en nueve categorías con resumen de riesgo por categoría; la interfaz los reagrupa por riesgo, categoría, OWASP o dimensión CID, y muestra los marcadores de IA por fichero o página.
- Interfaz: pantalla de progreso con porcentaje, tiempo restante, fases y descripción sencilla de cada comprobación.

### Corregido
- Informes HTML: las URLs y el código largos ya no se salen de la tarjeta del informe.

## [1.3.1] - 2026-11-11

### Añadido
- Interfaz: ilustración animada de una lupa ultravioleta que revela marcadores ocultos (sigue al ratón; queda quieta si el sistema pide reducir el movimiento), también mientras se analiza; iconos en las capacidades y los botones; una cuarta tarjeta de capacidad para la seguridad; el logotipo vuelve a la pantalla de inicio.
- Nota cuando una web responde con un estado HTTP de error.

### Cambiado
- Diseño adaptable: botones solo con icono en anchos medios, campo de ruta y «Analizar» en la misma fila en tablet y móvil, etiquetas cortas y panel de opciones como hoja inferior en el móvil, sin hueco vacío antes de la lista de casos en pantallas estrechas.

## [1.3.0] - 2026-11-11

### Añadido
- Rastreo de webs completas (`--rastrear`, `--max-paginas`, `--max-imagenes`, `--retardo`): solo el mismo sitio, respeta robots.txt y descarga a una carpeta temporal que se borra al terminar.
- Módulo de seguridad (`--seguridad`, `--solo-seguridad`): clasificación OWASP Top 10:2025, CWE, técnicas de MITRE ATT&CK, efecto sobre la triada CID, matriz de riesgos 5×5 y CVSS v4.0 (algoritmo oficial de FIRST, `cvss4.py`) con requisitos de entorno según el contexto de la web.
  - Comprobaciones pasivas de webs: transporte y TLS, cabeceras de seguridad, cookies, contenido mixto, SRI, librerías JavaScript vulnerables, formularios, comentarios, errores, secretos expuestos, mapas de código, robots.txt y security.txt.
  - Modo activo (`--activo --autorizado`): rutas sensibles conocidas, métodos HTTP, reflejo de CORS y versiones antiguas de TLS.
  - Comprobaciones de código: secretos, patrones de inyección, deserialización, XSS en el navegador, verificación TLS, criptografía y aleatoriedad débiles, depuración, excepciones silenciadas, dependencias y acciones sin fijar, contenedores.
  - `--umbral-cvss` con código de salida 3 para CI.
- Interfaz: panel de Opciones (marcadores de IA, seguridad, imágenes de las webs, rastreo, límite de páginas, modo activo con confirmación de autorización), progreso en directo y vista de seguridad con CVSS, triada CID, matriz de riesgos y hallazgos con enlaces a OWASP, CWE, ATT&CK y CVE.

## [1.2.1] - 2026-11-11

### Cambiado
- Las imágenes sin ningún metadato (ni C2PA, ni XMP, ni EXIF: capturas, miniaturas de buscadores, redes sociales) se valoran ahora como «No se puede determinar» en lugar de «Sin indicios relevantes», con una nota que sugiere una búsqueda inversa de imágenes.
- Interfaz: analizar otra vez el mismo objetivo actualiza su caso en lugar de duplicarlo.

## [1.2.0] - 2026-11-10

### Añadido
- Interfaz gráfica (`--gui`) que funciona en local en el navegador: arrastrar y soltar ficheros y carpetas, selector de ficheros del sistema, historial de la sesión, apariencia clara y oscura, español e inglés y exportación de informes. Fuentes: Redaction y Martian Mono (SIL OFL 1.1), incluidas.
- Opciones `--port` y `--no-browser`.

### Seguridad
- El servidor de la interfaz solo escucha en 127.0.0.1, con token aleatorio de 256 bits, comprobación de `Host` y `Origin`, CSP estricta, límites de subida y saneado de rutas. Cubierto por pruebas.

## [1.1.0] - 2026-11-10

### Añadido
- Análisis de metadatos de imágenes (JPEG, PNG, WebP, HEIC, AVIF, TIFF…):
  - Credenciales de contenido **C2PA**: lectura de JUMBF, CBOR y COSE sin dependencias; origen digital, herramienta generadora, acciones y firmante del certificado.
  - Verificación opcional de la firma con `c2patool` si está instalado.
  - IPTC `DigitalSourceType` en XMP.
  - Parámetros de generación en PNG: Stable Diffusion (A1111/Forge), ComfyUI, InvokeAI, NovelAI.
  - Nombres de generadores de IA en EXIF y XMP.
- Análisis de las imágenes de las webs: hasta 15 imágenes en modo URL y las imágenes locales de un HTML guardado. Opción `--sin-imagenes` / `--no-images`.
- Interfaz bilingüe español/inglés: consola, informes HTML/Markdown/JSON y ayuda. Opción `--lang es|en`, variable `AIMARKERS_LANG` y detección del idioma del sistema.
- Nombres de opción en inglés: `--evidence`, `--threshold`, `--quiet`, `--no-color`.
- Campo `idioma` en el JSON.
- Documentación en inglés y en español.

### Cambiado
- El README principal está en inglés; la versión en español está en `README.es.md`.
- Las tuplas de reglas pasan a `(id, nivel, patrón)`; las descripciones están en `DESCRIPCIONES`.

### Seguridad
- Límites al leer imágenes: descompresión de 2 MB, profundidad y número de elementos CBOR, validación de longitudes de cajas y tamaño máximo de imagen.
- Las imágenes de un HTML local solo se leen si están dentro de su carpeta.

## [1.0.0] - 2026-11-10

### Añadido
- Análisis de marcadores de IA en código, texto, webs (fichero o URL) y repositorios Git.
- Escala de pesos (explícito 40, fuerte 20, medio 8, débil 3), rendimiento decreciente por repetición y ponderación por prevalencia en proyectos grandes.
- Detección de ráfagas de registros y precisión de coordenadas mezclada en datos embebidos de webs.
- Informes en consola, HTML (claro y oscuro, adaptable a móvil), Markdown y JSON.
- Opción `--umbral` para integrarlo en CI.
- Fórmula de Homebrew en el tap `z115666/tap`.

### Seguridad
- Invocación endurecida de `git` frente a repositorios manipulados.
- Cuantificadores acotados frente a ReDoS, límites de tamaño y redirecciones solo http(s).
