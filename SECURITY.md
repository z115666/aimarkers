# Security policy

**English** · [Español](SECURITY.es.md)

## Supported versions

| Version | Supported |
| --- | --- |
| 1.3.x | Yes |
| 1.2.x | Yes |
| 1.1.x | Yes |
| 1.0.x | No: upgrade to 1.1 |

## Reporting a vulnerability

Do not open a public issue. Use **[Report a vulnerability](../../security/advisories/new)** in the repository's *Security* tab (private GitHub advisory).

Include the version, operating system, steps to reproduce and, if possible, a minimal sample file or repository. I reply within 7 days and publish the fix with a security advisory where appropriate.

## Threat model

aimarkers is meant to analyse **untrusted** content: third-party repositories, websites, images or files. These are the measures it applies:

| Risk | Measure |
| --- | --- |
| Command execution when analysing a tampered Git repository (`core.fsmonitor`, hooks, `diff.external`, `textconv` in `.git/config` or `.gitattributes`) | `git` runs without a shell, with list arguments and with `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c diff.external=`, `--no-ext-diff`, `--no-textconv` and `GIT_CONFIG_NOSYSTEM=1`. Checked against a hostile repository |
| Regular expression denial of service (ReDoS) | Bounded quantifiers in the rules that scan HTML attributes and metadata |
| Crafted images: decompression bombs, boxes with fake lengths, endlessly nested CBOR | `zTXt`/`iTXt` decompression limited to 2 MB; every JUMBF/ISO BMFF box is validated against the buffer bounds; the CBOR decoder limits depth (64) and element count; DER is only walked within its bounds. Tested with bombs, malformed boxes and randomly corrupted images |
| Huge or binary files | 3 MB limit per text file and 50 MB per image, binary detection and minified code skipped |
| Symbolic links pointing outside the project | Not followed |
| Images in a local HTML file pointing outside its folder (`../`) | Discarded: only files inside the HTML file's folder are read |
| Downloading URLs and images | `http`/`https` only, including after redirects; timeouts; at most 15 images of 15 MB, in a temporary folder deleted afterwards |
| `c2patool` | Located on the PATH with `shutil.which`, run by absolute path, without a shell, with list arguments and a 60 s timeout. It is optional |
| Graphical interface (`--gui`) attacked from another website or tab | Listens on 127.0.0.1 only; 256-bit token in the URL fragment, required in a header; `Host` and `Origin` checks against DNS rebinding and CSRF; strict CSP without inline scripts; static files from a closed list; uploads limited and sanitised into a temporary folder deleted on exit |
| Crawling a whole website | Same site and http(s) only, `robots.txt` and `nofollow` respected, pause between requests, size limits per file and 2 GB in total; everything in a temporary folder deleted at the end, even after errors |
| Misuse of the active security mode against third parties | Off by default; requires `--active` and an explicit `--authorized` declaration (a confirmation box in the interface). It only requests well-known paths: no injection payloads, credentials or exploits |
| Leaking secrets found during the analysis | Keys and tokens are shown truncated in reports |
| Report injection | The HTML report escapes all analysed content and contains no scripts; Markdown escapes HTML and pipes |
| Supply chain | No runtime dependencies (standard library only). GitHub Actions pinned by commit hash and development tools installed with `--require-hashes`. The Homebrew formula points to a specific commit with its SHA-256 |

## Accepted risks

| Alert | Where | Why it is accepted | Mitigations | Review |
| --- | --- | --- | --- | --- |
| CodeQL `py/path-injection` (CWE-22/23/36/73/99): «Uncontrolled data used in path expression» | `aimarkers.py` (`analizar_objetivo`) and the paths it reaches | Analysing the file, folder or URL the user chooses is the tool's purpose. In the CLI the path is the operator's own argument, so it crosses no trust boundary. In the interface it arrives over HTTP, but only from the page that holds the session token. | The server listens on 127.0.0.1 only; a random 256-bit token is required on every request; `Host` and `Origin` are checked; files are read-only and size-limited; symbolic links are not followed; nothing is written outside a temporary folder. An attacker would already need to run code as the user. | On every change to `aimarkers_gui.py` or to how targets are received |

## Development lifecycle controls

- **CI** on every push and pull request: ruff (including the `S` security rules), bandit and unit tests on Linux, macOS and Windows with Python 3.9 and the latest stable release.
- **CodeQL** with the `security-extended` suite for Python, the interface JavaScript and the workflows themselves, on every change and weekly.
- **Dependabot** for GitHub Actions and development tools.
- **Least privilege** in workflows: read-only permissions except for uploading CodeQL results, and `persist-credentials: false`.

## Privacy

aimarkers sends no data anywhere except to the URL you ask it to analyse, its images and its `/llms.txt`. Use `--no-images` if you do not want images downloaded. Reports may contain excerpts of the analysed content, including prompts stored in images: treat them as confidentially as the original. That is why `.gitignore` excludes generated reports.
