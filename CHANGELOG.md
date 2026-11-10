# Changelog

**English** · [Español](CHANGELOG.es.md)

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [semantic versioning](https://semver.org/).

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
