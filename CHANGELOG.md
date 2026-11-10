# Cambios

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/).

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
