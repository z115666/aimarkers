# Cambios

[English](CHANGELOG.md) · **Español**

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

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
