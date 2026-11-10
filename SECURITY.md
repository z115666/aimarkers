# Política de seguridad

## Versiones con soporte

| Versión | Soporte |
| --- | --- |
| 1.x | Sí |

## Cómo informar de una vulnerabilidad

No abras un *issue* público. Usa **[Report a vulnerability](../../security/advisories/new)** en la pestaña *Security* del repositorio (aviso privado de GitHub).

Incluye la versión, el sistema operativo, los pasos para reproducirlo y, si puedes, un fichero o repositorio mínimo de ejemplo. Respondo en un plazo de 7 días y publico la corrección con un aviso de seguridad cuando proceda.

## Modelo de amenazas

aimarkers está pensado para analizar contenido **no confiable**: repositorios, webs o ficheros de terceros. Estas son las medidas que aplica:

| Riesgo | Medida |
| --- | --- |
| Ejecución de comandos al analizar un repositorio Git manipulado (`core.fsmonitor`, hooks, `diff.external`, `textconv` en `.git/config` o `.gitattributes`) | `git` se invoca sin shell, con argumentos en lista y con `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c diff.external=`, `--no-ext-diff`, `--no-textconv` y `GIT_CONFIG_NOSYSTEM=1`. Cubierto por una prueba manual con un repositorio hostil |
| Denegación de servicio por expresiones regulares (ReDoS) | Cuantificadores acotados en las reglas que recorren atributos HTML; probado con entradas de 200 KB |
| Ficheros enormes o binarios | Límite de 3 MB por fichero, detección de binarios y omisión de código minificado |
| Enlaces simbólicos que apuntan fuera del proyecto | No se siguen |
| Descarga de URLs | Solo `http`/`https`, también tras redirecciones; tiempo máximo de espera y límite de tamaño |
| Inyección en los informes | El informe HTML escapa todo el contenido analizado; el Markdown escapa HTML y barras verticales |
| Cadena de suministro | Sin dependencias en tiempo de ejecución (solo biblioteca estándar). Acciones de GitHub fijadas por hash de commit y herramientas de desarrollo instaladas con `--require-hashes` |

## Controles en el ciclo de desarrollo

- **CI** en cada *push* y *pull request*: ruff (incluye reglas de seguridad `S`), bandit y pruebas unitarias en Linux, macOS y Windows con Python 3.9 y la última estable.
- **CodeQL** con la batería `security-extended` para Python y para los propios workflows, en cada cambio y cada semana.
- **Dependabot** para las acciones de GitHub y las herramientas de desarrollo.
- **Mínimo privilegio** en los workflows: permisos de solo lectura salvo la subida de resultados de CodeQL, y `persist-credentials: false`.

## Privacidad

aimarkers no envía datos a ningún sitio salvo la URL que le pidas analizar (y su `/llms.txt`). Los informes pueden contener extractos del contenido analizado: trátalos con la misma confidencialidad que el original. Por eso `.gitignore` excluye los informes generados.
