# Política de seguridad

[English](SECURITY.md) · **Español**

## Versiones con soporte

| Versión | Soporte |
| --- | --- |
| 1.3.x | Sí |
| 1.2.x | Sí |
| 1.1.x | Sí |
| 1.0.x | No: actualiza a 1.1 |

## Cómo informar de una vulnerabilidad

No abras un *issue* público. Usa **[Report a vulnerability](../../security/advisories/new)** en la pestaña *Security* del repositorio (aviso privado de GitHub).

Incluye la versión, el sistema operativo, los pasos para reproducirlo y, si puedes, un fichero o repositorio mínimo de ejemplo. Respondo en un plazo de 7 días y publico la corrección con un aviso de seguridad cuando proceda.

## Modelo de amenazas

aimarkers está pensado para analizar contenido **no confiable**: repositorios, webs, imágenes o ficheros de terceros. Estas son las medidas que aplica:

| Riesgo | Medida |
| --- | --- |
| Ejecución de comandos al analizar un repositorio Git manipulado (`core.fsmonitor`, hooks, `diff.external`, `textconv` en `.git/config` o `.gitattributes`) | `git` se invoca sin shell, con argumentos en lista y con `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c diff.external=`, `--no-ext-diff`, `--no-textconv` y `GIT_CONFIG_NOSYSTEM=1`. Comprobado con un repositorio hostil |
| Denegación de servicio por expresiones regulares (ReDoS) | Cuantificadores acotados en las reglas que recorren atributos HTML y metadatos |
| Imágenes manipuladas: bombas de descompresión, cajas con longitudes falsas, CBOR anidado sin fin | Descompresión de `zTXt`/`iTXt` limitada a 2 MB; cada caja JUMBF/ISO BMFF se valida contra los límites del búfer; el decodificador CBOR limita la profundidad (64) y el número de elementos; el DER solo se recorre dentro de sus límites. Probado con bombas, cajas malformadas e imágenes corrompidas al azar |
| Ficheros enormes o binarios | Límite de 3 MB por fichero de texto y 50 MB por imagen, detección de binarios y omisión de código minificado |
| Enlaces simbólicos que apuntan fuera del proyecto | No se siguen |
| Imágenes de un HTML local que apuntan fuera de su carpeta (`../`) | Se descartan: solo se leen ficheros dentro de la carpeta del HTML |
| Descarga de URLs e imágenes | Solo `http`/`https`, también tras redirecciones; tiempo máximo de espera; como máximo 15 imágenes de 15 MB, en una carpeta temporal que se borra al terminar |
| `c2patool` | Se busca en el PATH con `shutil.which`, se invoca con la ruta absoluta, sin shell, con argumentos en lista y con un tiempo máximo de 60 s. Es opcional |
| Interfaz gráfica (`--gui`) atacada desde otra web o pestaña | Solo escucha en 127.0.0.1; token de 256 bits en el fragmento de la URL, exigido en una cabecera; comprobación de `Host` y `Origin` frente a DNS rebinding y CSRF; CSP estricta sin scripts en línea; ficheros estáticos de una lista cerrada; subidas limitadas y saneadas en una carpeta temporal que se borra al salir |
| Rastreo de una web completa | Solo el mismo sitio y solo http(s); respeta `robots.txt` y `nofollow`; pausa entre peticiones; límites por fichero y 2 GB en total; todo en una carpeta temporal que se borra al terminar, también tras un error |
| Uso indebido del modo de seguridad activo contra terceros | Desactivado por defecto; exige `--activo` y una declaración expresa con `--autorizado` (una casilla de confirmación en la interfaz). Solo pide rutas conocidas: sin cargas de inyección, credenciales ni exploits |
| Filtrado de secretos encontrados durante el análisis | Las claves y tokens se muestran recortados en los informes |
| Inyección en los informes | El informe HTML escapa todo el contenido analizado y no contiene scripts; el Markdown escapa HTML y barras verticales |
| Cadena de suministro | Sin dependencias en tiempo de ejecución (solo biblioteca estándar). Acciones de GitHub fijadas por hash de commit y herramientas de desarrollo instaladas con `--require-hashes`. La fórmula de Homebrew apunta a un commit concreto con su SHA-256 |

## Riesgos aceptados

| Alerta | Dónde | Por qué se acepta | Medidas | Revisión |
| --- | --- | --- | --- | --- |
| CodeQL `py/path-injection` (CWE-22/23/36/73/99): «Uncontrolled data used in path expression» | `aimarkers.py` (`analizar_objetivo`) y las rutas que alcanza | Analizar el fichero, la carpeta o la URL que elige el usuario es el propósito de la herramienta. En el CLI la ruta es el argumento del propio operador y no cruza ninguna frontera de confianza. En la interfaz llega por HTTP, pero solo desde la página que tiene el token de sesión. | El servidor solo escucha en 127.0.0.1; cada petición exige un token aleatorio de 256 bits; se comprueban `Host` y `Origin`; los ficheros solo se leen y con límite de tamaño; no se siguen enlaces simbólicos; nada se escribe fuera de una carpeta temporal. Un atacante ya tendría que ejecutar código como el usuario. | En cada cambio de `aimarkers_gui.py` o de la forma de recibir los objetivos |

## Controles en el ciclo de desarrollo

- **CI** en cada *push* y *pull request*: ruff (incluye reglas de seguridad `S`), bandit y pruebas unitarias en Linux, macOS y Windows con Python 3.9 y la última estable.
- **CodeQL** con la batería `security-extended` para Python, el JavaScript de la interfaz y los propios workflows, en cada cambio y cada semana.
- **Dependabot** para las acciones de GitHub y las herramientas de desarrollo.
- **Mínimo privilegio** en los workflows: permisos de solo lectura salvo la subida de resultados de CodeQL, y `persist-credentials: false`.

## Privacidad

aimarkers no envía datos a ningún sitio salvo la URL que le pidas analizar, sus imágenes y su `/llms.txt`. Usa `--sin-imagenes` si no quieres descargar las imágenes. Los informes pueden contener extractos del contenido analizado, incluidos los *prompts* guardados en imágenes: trátalos con la misma confidencialidad que el original. Por eso `.gitignore` excluye los informes generados.
