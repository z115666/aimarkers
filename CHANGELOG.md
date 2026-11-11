# Changelog

**English** · [Español](CHANGELOG.es.md)

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [semantic versioning](https://semver.org/).

## [1.3.1] - 2026-11-11

### Added
- Interface: animated illustration of an ultraviolet magnifier that reveals hidden markers (follows the mouse; still when the system asks for reduced motion), also shown while analysing; icons for the capabilities and buttons; a fourth capability card for security; the logo returns to the start screen.
- Note when a website answers with an HTTP error status.

### Changed
- Responsive layout: icon-only buttons at medium widths, path field and «Analyse» on the same row on tablets and phones, short button labels and an options bottom sheet on phones, no empty gap above the session list on narrow screens.

## [1.3.0] - 2026-11-11

### Added
- Whole-site crawling (`--crawl`, `--max-pages`, `--max-images`, `--delay`): same site only, respects robots.txt, downloads to a temporary folder deleted afterwards.
- Security module (`--security`, `--security-only`): OWASP Top 10:2025 classification, CWE, MITRE ATT&CK techniques, effect on the CIA triad, 5×5 risk matrix and CVSS v4.0 scores (FIRST's official algorithm, `cvss4.py`) with environmental requirements derived from the site's context.
  - Passive website checks: transport and TLS, security headers, cookies, mixed content, SRI, vulnerable JavaScript libraries, forms, comments, errors, exposed secrets, source maps, robots.txt and security.txt.
  - Active mode (`--active --authorized`): well-known sensitive paths, HTTP methods, CORS reflection and old TLS versions.
  - Code checks: secrets, injection patterns, deserialisation, DOM XSS, TLS verification, weak crypto and randomness, debug mode, silenced exceptions, unpinned dependencies and actions, containers.
  - `--cvss-threshold` exit code 3 for CI.
- Interface: Options panel (AI markers, security, website images, crawl, page limit, active mode with authorisation confirmation), live progress, and a security view with CVSS, CIA triad, risk matrix and findings with OWASP/CWE/ATT&CK/CVE links.

## [1.2.1] - 2026-11-11

### Changed
- Images with no metadata at all (no C2PA, XMP or EXIF: screenshots, search engine thumbnails, social networks) are now reported as "Cannot be determined" instead of "No relevant signs", with a note suggesting a reverse image search.
- Interface: analysing the same target again updates its case instead of duplicating it.

## [1.2.0] - 2026-11-10

### Added
- Graphical interface (`--gui`) that runs locally in the browser: drag and drop of files and folders, system file picker, session history, light and dark appearance, English and Spanish, report export. Fonts: Redaction and Martian Mono (SIL OFL 1.1), bundled.
- `--port` and `--no-browser` options.

### Security
- The interface server listens only on 127.0.0.1 with a random 256-bit token, `Host`/`Origin` checks, strict CSP, upload limits and path sanitising. Covered by tests.

## [1.1.0] - 2026-11-10

### Added
- Image metadata analysis (JPEG, PNG, WebP, HEIC, AVIF, TIFF…):
  - **C2PA** Content Credentials: dependency-free JUMBF, CBOR and COSE parsing; digital source type, generating tool, actions and certificate signer.
  - Optional signature verification with `c2patool` when installed.
  - IPTC `DigitalSourceType` in XMP.
  - Generation parameters in PNG: Stable Diffusion (A1111/Forge), ComfyUI, InvokeAI, NovelAI.
  - AI generator names in EXIF and XMP.
- Analysis of website images: up to 15 images in URL mode and local images of a saved HTML page. `--no-images` / `--sin-imagenes` option.
- Bilingual English/Spanish interface: console, HTML/Markdown/JSON reports and help. `--lang es|en` option, `AIMARKERS_LANG` variable and system language detection.
- English option names: `--evidence`, `--threshold`, `--quiet`, `--no-color`.
- `idioma` (language) field in the JSON output.
- Documentation in English and Spanish.

### Changed
- The main README is now in English; the Spanish version is `README.es.md`.
- Rule tuples are now `(id, level, pattern)`; descriptions live in `DESCRIPCIONES`.

### Security
- Limits when reading images: 2 MB decompression, CBOR depth and element count, box length validation and maximum image size.
- Images referenced by a local HTML file are only read if they are inside its folder.

## [1.0.0] - 2026-11-10

### Added
- AI marker analysis for code, text, websites (file or URL) and Git repositories.
- Weight scale (explicit 40, strong 20, medium 8, weak 3), diminishing returns on repetition and prevalence weighting in large projects.
- Detection of record bursts and mixed coordinate precision in embedded website data.
- Console, HTML (light and dark, mobile friendly), Markdown and JSON reports.
- `--umbral` option for CI integration.
- Homebrew formula in the `z115666/tap` tap.

### Security
- Hardened `git` invocation against tampered repositories.
- Bounded quantifiers against ReDoS, size limits and http(s)-only redirects.
