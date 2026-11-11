# aimarkers: ignore-file
"""
Módulo de seguridad de aimarkers / aimarkers security module.

Evalúa la seguridad de webs (modo pasivo por defecto y activo con autorización) y de
ficheros de código. Cada hallazgo se clasifica con OWASP Top 10:2025, CWE y técnicas de
MITRE ATT&CK, se puntúa con CVSS v4.0 (algoritmo oficial de FIRST, en cvss4.py) y se sitúa
en una matriz de riesgos 5x5 (probabilidad x impacto) según su efecto sobre la triada CID.

Lo que NO hace: no envía cargas de inyección, no prueba credenciales ni explota fallos.
El modo activo solo pide rutas conocidas (ficheros expuestos, paneles) y lee las cabeceras.
Autor: Alberto
"""

from __future__ import annotations

import html
import json
import re
import secrets
import socket
import ssl
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import aimarkers
import aimarkers_web as web
import cvss4

# ---------------------------------------------------------------------------
# Referencias: OWASP Top 10:2025, MITRE ATT&CK, severidades
# ---------------------------------------------------------------------------

OWASP = {
    "A01": ("Control de acceso roto", "Broken Access Control"),
    "A02": ("Configuración de seguridad incorrecta", "Security Misconfiguration"),
    "A03": ("Fallos en la cadena de suministro de software", "Software Supply Chain Failures"),
    "A04": ("Fallos criptográficos", "Cryptographic Failures"),
    "A05": ("Inyección", "Injection"),
    "A06": ("Diseño inseguro", "Insecure Design"),
    "A07": ("Fallos de autenticación", "Authentication Failures"),
    "A08": ("Fallos de integridad del software o los datos", "Software or Data Integrity Failures"),
    "A09": ("Fallos de registro y alertas de seguridad", "Security Logging and Alerting Failures"),
    "A10": ("Gestión incorrecta de condiciones excepcionales", "Mishandling of Exceptional Conditions"),
}

MITRE = {
    "T1040": "Network Sniffing",
    "T1059": "Command and Scripting Interpreter",
    "T1059.007": "Command and Scripting Interpreter: JavaScript",
    "T1078": "Valid Accounts",
    "T1083": "File and Directory Discovery",
    "T1087": "Account Discovery",
    "T1110": "Brute Force",
    "T1185": "Browser Session Hijacking",
    "T1189": "Drive-by Compromise",
    "T1190": "Exploit Public-Facing Application",
    "T1195.001": "Supply Chain Compromise: Compromise Software Dependencies and Development Tools",
    "T1195.002": "Supply Chain Compromise: Compromise Software Supply Chain",
    "T1204.001": "User Execution: Malicious Link",
    "T1213": "Data from Information Repositories",
    "T1499": "Endpoint Denial of Service",
    "T1505.003": "Server Software Component: Web Shell",
    "T1539": "Steal Web Session Cookie",
    "T1552.001": "Unsecured Credentials: Credentials In Files",
    "T1552.004": "Unsecured Credentials: Private Keys",
    "T1557": "Adversary-in-the-Middle",
    "T1565": "Data Manipulation",
    "T1589.002": "Gather Victim Identity Information: Email Addresses",
    "T1592.002": "Gather Victim Host Information: Software",
    "T1594": "Search Victim-Owned Websites",
    "T1595.002": "Active Scanning: Vulnerability Scanning",
}

TEXTOS = {
    "seg.titulo": ("Seguridad", "Security"),
    "seg.contexto": ("Contexto", "Context"),
    "seg.contexto_ninguno": ("web informativa, sin formularios sensibles", "informational site, no sensitive forms"),
    "seg.contexto_ficheros": ("código y ficheros (contexto de uso desconocido)", "code and files (usage context unknown)"),
    "seg.ctx.login": ("inicio de sesión", "login"),
    "seg.ctx.datos": ("formularios con datos personales", "forms with personal data"),
    "seg.ctx.pagos": ("pagos", "payments"),
    "seg.ctx.subida": ("subida de ficheros", "file uploads"),
    "seg.ctx.formularios": ("formularios", "forms"),
    "seg.requisitos": ("Requisitos CVSS de entorno", "CVSS environmental requirements"),
    "seg.cvss_max": ("CVSS máximo", "Highest CVSS"),
    "seg.hallazgos": ("Hallazgos", "Findings"),
    "seg.sin_hallazgos": ("No se han encontrado fallos de seguridad con las comprobaciones realizadas.",
                          "No security issues found with the checks performed."),
    "seg.triada": ("Riesgo sobre la triada CID", "Risk to the CIA triad"),
    "seg.c": ("Confidencialidad", "Confidentiality"),
    "seg.i": ("Integridad", "Integrity"),
    "seg.d": ("Disponibilidad", "Availability"),
    "seg.matriz": ("Matriz de riesgos (probabilidad × impacto)", "Risk matrix (likelihood × impact)"),
    "seg.probabilidad": ("Probabilidad", "Likelihood"),
    "seg.impacto": ("Impacto", "Impact"),
    "seg.riesgo": ("Riesgo", "Risk"),
    "seg.recomendacion": ("Recomendación", "Recommendation"),
    "seg.evidencia": ("Evidencia", "Evidence"),
    "seg.ubicaciones": ("Ubicaciones", "Locations"),
    "seg.vector": ("Vector", "Vector"),
    "seg.informativo": ("informativo", "informational"),
    "seg.modo_pasivo": ("Modo pasivo: solo se ha analizado lo que recibe cualquier visitante.",
                        "Passive mode: only what any visitor receives was analysed."),
    "seg.modo_activo": ("Modo activo con autorización declarada: se han comprobado rutas sensibles conocidas.",
                        "Active mode with declared authorisation: known sensitive paths were checked."),
    "seg.activo_sin_autorizacion": ("El modo activo necesita --autorizado: confirma que tienes permiso para analizar esa web.",
                                    "Active mode needs --authorized: confirm you have permission to test that website."),
    "seg.aviso": ("Evaluación automática y no intrusiva: no sustituye a una auditoría ni a una prueba de intrusión. "
                  "El CVSS se calcula con vectores tipo para cada hallazgo y el contexto detectado; revísalo antes de usarlo.",
                  "Automated, non-intrusive assessment: it does not replace an audit or a penetration test. "
                  "CVSS is computed from typical vectors for each finding and the detected context; review it before use."),
    "seg.tls": ("TLS", "TLS"),
    "seg.peticiones": ("{n} peticiones de comprobación", "{n} check requests"),
    "nivel_riesgo.bajo": ("Bajo", "Low"),
    "nivel_riesgo.medio": ("Medio", "Medium"),
    "nivel_riesgo.alto": ("Alto", "High"),
    "nivel_riesgo.critico": ("Crítico", "Critical"),
    "nivel_riesgo.ninguno": ("Ninguno", "None"),
    "sev.none": ("Ninguna", "None"),
    "sev.low": ("Baja", "Low"),
    "sev.medium": ("Media", "Medium"),
    "sev.high": ("Alta", "High"),
    "sev.critical": ("Crítica", "Critical"),
    "req.H": ("Alta", "High"),
    "req.M": ("Media", "Medium"),
    "req.L": ("Baja", "Low"),
    "prog.seguridad": ("Analizando la seguridad…", "Analysing security…"),
    "prog.activo": ("Comprobando rutas sensibles ({n})…", "Checking sensitive paths ({n})…"),
}

# ---------------------------------------------------------------------------
# Catálogo de comprobaciones
#   t: título · d: por qué importa · r: recomendación · o: OWASP · cwe · mitre
#   v: vector base CVSS v4.0 · e: madurez del exploit (A atacado, P prueba de concepto, U sin informes)
#   info: hallazgo informativo, sin CVSS
# ---------------------------------------------------------------------------

def _c(t, d, r, o, cwe, mitre, v=None, e="U", info=False):
    return {"t": t, "d": d, "r": r, "o": o, "cwe": cwe, "mitre": mitre, "v": v, "e": e, "info": info}


CATALOGO = {
    # --- Transporte y TLS -------------------------------------------------
    "sin-https": _c(
        ("La web se sirve sin HTTPS", "The website is served without HTTPS"),
        ("Todo el tráfico, incluidas credenciales y cookies, viaja en claro y se puede leer o modificar en la red.",
         "All traffic, including credentials and cookies, travels in clear text and can be read or altered on the network."),
        ("Sirve el sitio solo por HTTPS con un certificado válido y redirige HTTP a HTTPS.",
         "Serve the site over HTTPS only with a valid certificate and redirect HTTP to HTTPS."),
        "A04", [319], ["T1557", "T1040"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N"),
    "http-sin-redireccion": _c(
        ("HTTP no redirige a HTTPS", "HTTP does not redirect to HTTPS"),
        ("Quien entra por http:// navega sin cifrar y puede ser víctima de un ataque de intermediario.",
         "Visitors arriving via http:// browse unencrypted and can be targeted by a man-in-the-middle attack."),
        ("Responde a todas las peticiones HTTP con una redirección 301 a HTTPS y activa HSTS.",
         "Answer every HTTP request with a 301 redirect to HTTPS and enable HSTS."),
        "A04", [319], ["T1557"], "AV:N/AC:H/AT:P/PR:N/UI:P/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "sin-hsts": _c(
        ("Falta la cabecera Strict-Transport-Security (HSTS)", "Missing Strict-Transport-Security (HSTS) header"),
        ("Sin HSTS, un atacante en la red puede degradar la primera conexión a HTTP (SSL stripping).",
         "Without HSTS, a network attacker can downgrade the first connection to HTTP (SSL stripping)."),
        ("Envía «Strict-Transport-Security: max-age=31536000; includeSubDomains».",
         "Send «Strict-Transport-Security: max-age=31536000; includeSubDomains»."),
        "A04", [319, 523], ["T1557"], "AV:N/AC:H/AT:P/PR:N/UI:P/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "hsts-corto": _c(
        ("HSTS con una duración demasiado corta", "HSTS max-age is too short"),
        ("Un max-age inferior a seis meses deja ventanas en las que el navegador vuelve a aceptar HTTP.",
         "A max-age under six months leaves windows in which the browser accepts HTTP again."),
        ("Usa max-age de al menos 31536000 segundos (un año).", "Use a max-age of at least 31536000 seconds (one year)."),
        "A04", [523], ["T1557"], "AV:N/AC:H/AT:P/PR:N/UI:P/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N"),
    "cert-invalido": _c(
        ("Certificado TLS no válido", "Invalid TLS certificate"),
        ("El navegador no puede verificar la identidad del servidor; los usuarios se acostumbran a aceptar avisos.",
         "The browser cannot verify the server identity; users get used to accepting warnings."),
        ("Instala un certificado emitido por una autoridad reconocida y que cubra el nombre del sitio.",
         "Install a certificate issued by a trusted authority that covers the site name."),
        "A04", [295], ["T1557"], "AV:N/AC:H/AT:P/PR:N/UI:P/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N"),
    "cert-caduca": _c(
        ("El certificado TLS caduca pronto", "The TLS certificate expires soon"),
        ("Si caduca, los navegadores bloquearán el acceso a la web.", "Once expired, browsers will block access to the site."),
        ("Renueva el certificado y automatiza la renovación (por ejemplo, con ACME).",
         "Renew the certificate and automate renewal (for example with ACME)."),
        "A02", [298], ["T1499"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:N/VI:N/VA:L/SC:N/SI:N/SA:N"),
    "tls-obsoleto": _c(
        ("Protocolo TLS obsoleto (1.0 o 1.1)", "Obsolete TLS protocol (1.0 or 1.1)"),
        ("TLS 1.0 y 1.1 tienen debilidades conocidas y los navegadores modernos ya no los admiten.",
         "TLS 1.0 and 1.1 have known weaknesses and modern browsers no longer support them."),
        ("Desactiva TLS 1.0 y 1.1; ofrece solo TLS 1.2 y 1.3.", "Disable TLS 1.0 and 1.1; offer TLS 1.2 and 1.3 only."),
        "A04", [326, 327], ["T1557", "T1040"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    # --- Cabeceras -------------------------------------------------------------
    "sin-csp": _c(
        ("Falta la cabecera Content-Security-Policy", "Missing Content-Security-Policy header"),
        ("Sin CSP, cualquier fallo de XSS permite ejecutar scripts arbitrarios en el navegador de los visitantes.",
         "Without CSP, any XSS flaw lets arbitrary scripts run in visitors' browsers."),
        ("Define una CSP restrictiva (script-src con nonces o hashes, object-src 'none', base-uri 'none').",
         "Define a restrictive CSP (script-src with nonces or hashes, object-src 'none', base-uri 'none')."),
        "A02", [693, 1021], ["T1059.007", "T1189"], "AV:N/AC:H/AT:P/PR:N/UI:A/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "csp-debil": _c(
        ("Content-Security-Policy débil", "Weak Content-Security-Policy"),
        ("La política permite 'unsafe-inline', 'unsafe-eval', comodines o HTTP, y apenas frena un XSS.",
         "The policy allows 'unsafe-inline', 'unsafe-eval', wildcards or HTTP, so it barely stops XSS."),
        ("Elimina 'unsafe-inline' y 'unsafe-eval' y usa nonces o hashes; evita * y http: en las fuentes.",
         "Remove 'unsafe-inline' and 'unsafe-eval' and use nonces or hashes; avoid * and http: sources."),
        "A02", [693], ["T1059.007", "T1189"], "AV:N/AC:H/AT:P/PR:N/UI:A/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "sin-antiframe": _c(
        ("La web se puede incrustar en otras (clickjacking)", "The site can be framed by others (clickjacking)"),
        ("Otra web puede cargarla en un marco invisible y engañar al usuario para que pulse donde no quiere.",
         "Another site can load it in an invisible frame and trick users into clicking where they do not intend."),
        ("Añade «Content-Security-Policy: frame-ancestors 'self'» (o X-Frame-Options: DENY).",
         "Add «Content-Security-Policy: frame-ancestors 'self'» (or X-Frame-Options: DENY)."),
        "A02", [1021], ["T1204.001", "T1185"], "AV:N/AC:L/AT:N/PR:N/UI:A/VC:N/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "sin-nosniff": _c(
        ("Falta X-Content-Type-Options: nosniff", "Missing X-Content-Type-Options: nosniff"),
        ("El navegador puede interpretar ficheros con un tipo distinto al declarado y ejecutar contenido subido.",
         "The browser may interpret files with a different type than declared and execute uploaded content."),
        ("Envía «X-Content-Type-Options: nosniff» en todas las respuestas.", "Send «X-Content-Type-Options: nosniff» on every response."),
        "A02", [693], ["T1189"], "AV:N/AC:H/AT:P/PR:N/UI:P/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "sin-referrer": _c(
        ("Falta Referrer-Policy", "Missing Referrer-Policy"),
        ("Las URLs internas (con identificadores o tokens) pueden filtrarse a sitios de terceros.",
         "Internal URLs (with identifiers or tokens) may leak to third-party sites."),
        ("Envía «Referrer-Policy: strict-origin-when-cross-origin» o más estricta.",
         "Send «Referrer-Policy: strict-origin-when-cross-origin» or stricter."),
        "A02", [200], ["T1594"], "AV:N/AC:H/AT:P/PR:N/UI:P/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N"),
    "sin-permissions-policy": _c(
        ("Falta Permissions-Policy", "Missing Permissions-Policy"),
        ("No se limitan las APIs del navegador (cámara, micrófono, ubicación) para el sitio y sus marcos.",
         "Browser APIs (camera, microphone, location) are not restricted for the site and its frames."),
        ("Envía una Permissions-Policy que desactive lo que no uses, p. ej. «camera=(), microphone=(), geolocation=()».",
         "Send a Permissions-Policy disabling what you do not use, e.g. «camera=(), microphone=(), geolocation=()»."),
        "A02", [693], [], info=True),
    "version-expuesta": _c(
        ("El servidor revela software y versiones", "The server reveals software and versions"),
        ("Las cabeceras Server, X-Powered-By o similares facilitan buscar vulnerabilidades conocidas de esas versiones.",
         "Server, X-Powered-By or similar headers make it easy to look up known vulnerabilities for those versions."),
        ("Oculta las versiones en las cabeceras del servidor y del lenguaje (server_tokens off, expose_php Off…).",
         "Hide versions in server and language headers (server_tokens off, expose_php Off…)."),
        "A02", [200, 497], ["T1592.002", "T1595.002"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N"),
    "cors-permisivo": _c(
        ("CORS permite cualquier origen con credenciales", "CORS allows any origin with credentials"),
        ("Otra web podría leer respuestas autenticadas del usuario.", "Another website could read the user's authenticated responses."),
        ("Limita Access-Control-Allow-Origin a una lista de orígenes concretos.",
         "Restrict Access-Control-Allow-Origin to an explicit list of origins."),
        "A01", [942], ["T1185"], "AV:N/AC:L/AT:P/PR:N/UI:A/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "cache-sensible": _c(
        ("Páginas con credenciales que se pueden guardar en caché", "Pages with credentials can be cached"),
        ("Un equipo compartido o un proxy pueden conservar páginas con formularios de acceso o datos.",
         "A shared computer or proxy may keep pages with login forms or data."),
        ("Envía «Cache-Control: no-store» en páginas con datos personales o formularios de acceso.",
         "Send «Cache-Control: no-store» on pages with personal data or login forms."),
        "A02", [525], ["T1552.001"], "AV:L/AC:L/AT:P/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N"),
    # --- Cookies --------------------------------------------------------------
    "cookie-sin-secure": _c(
        ("Cookie sin el atributo Secure", "Cookie without the Secure attribute"),
        ("La cookie puede enviarse por HTTP y ser interceptada.", "The cookie can be sent over HTTP and intercepted."),
        ("Marca todas las cookies con Secure.", "Mark every cookie as Secure."),
        "A07", [614], ["T1539", "T1557"], "AV:N/AC:H/AT:P/PR:N/UI:P/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "cookie-sin-httponly": _c(
        ("Cookie de sesión sin HttpOnly", "Session cookie without HttpOnly"),
        ("Un script inyectado (XSS) podría leer la cookie de sesión y suplantar al usuario.",
         "An injected script (XSS) could read the session cookie and impersonate the user."),
        ("Marca las cookies de sesión con HttpOnly.", "Mark session cookies as HttpOnly."),
        "A07", [1004], ["T1539", "T1185"], "AV:N/AC:H/AT:P/PR:N/UI:P/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "cookie-sin-samesite": _c(
        ("Cookie sin SameSite", "Cookie without SameSite"),
        ("Sin SameSite, la cookie viaja en peticiones iniciadas por otras webs, lo que facilita ataques CSRF.",
         "Without SameSite, the cookie is sent on requests started by other sites, which helps CSRF attacks."),
        ("Añade SameSite=Lax (o Strict) a las cookies.", "Add SameSite=Lax (or Strict) to cookies."),
        "A01", [1275, 352], ["T1185"], "AV:N/AC:L/AT:P/PR:N/UI:A/VC:N/VI:L/VA:N/SC:N/SI:N/SA:N"),
    # --- Contenido de las páginas ---------------------------------------------
    "contenido-mixto": _c(
        ("Contenido activo cargado por HTTP en una página HTTPS", "Active content loaded over HTTP on an HTTPS page"),
        ("Un atacante en la red puede sustituir ese script o marco y tomar el control de la página.",
         "A network attacker can replace that script or frame and take over the page."),
        ("Carga todos los recursos por HTTPS.", "Load every resource over HTTPS."),
        "A04", [319], ["T1557", "T1189"], "AV:N/AC:H/AT:P/PR:N/UI:P/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N"),
    "contenido-mixto-pasivo": _c(
        ("Imágenes o medios cargados por HTTP en una página HTTPS", "Images or media loaded over HTTP on an HTTPS page"),
        ("Se pueden sustituir o espiar; el navegador muestra la página como no segura.",
         "They can be replaced or observed; the browser marks the page as not secure."),
        ("Carga todos los recursos por HTTPS.", "Load every resource over HTTPS."),
        "A04", [319], ["T1557"], "AV:N/AC:H/AT:P/PR:N/UI:P/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "sin-sri": _c(
        ("Scripts de terceros sin Subresource Integrity", "Third-party scripts without Subresource Integrity"),
        ("Si el CDN o el tercero se compromete, el script modificado se ejecutará en tu web.",
         "If the CDN or third party is compromised, the modified script will run on your site."),
        ("Añade integrity=\"sha384-…\" y crossorigin=\"anonymous\" a los scripts y estilos externos, o alójalos tú.",
         "Add integrity=\"sha384-…\" and crossorigin=\"anonymous\" to external scripts and styles, or self-host them."),
        "A08", [353, 829], ["T1195.002", "T1189"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:L/VI:L/VA:N/SC:L/SI:L/SA:N"),
    "libreria-vulnerable": _c(
        ("Librería JavaScript con vulnerabilidades conocidas", "JavaScript library with known vulnerabilities"),
        ("La versión publicada tiene CVE públicos; algunos permiten XSS o contaminación de prototipos.",
         "The published version has public CVEs; some allow XSS or prototype pollution."),
        ("Actualiza la librería a la versión corregida o retírala si ya no se usa.",
         "Update the library to the fixed version or remove it if it is no longer used."),
        "A03", [1104, 1395], ["T1190", "T1189"], "AV:N/AC:L/AT:P/PR:N/UI:A/VC:L/VI:L/VA:N/SC:L/SI:L/SA:N", e="P"),
    "libreria-sin-soporte": _c(
        ("Librería JavaScript sin soporte", "Unsupported JavaScript library"),
        ("La librería ya no recibe parches de seguridad.", "The library no longer receives security patches."),
        ("Migra a una alternativa mantenida.", "Migrate to a maintained alternative."),
        "A03", [1104], ["T1190"], "AV:N/AC:L/AT:P/PR:N/UI:A/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "cms-version": _c(
        ("El CMS publica su versión", "The CMS publishes its version"),
        ("Saber la versión exacta de WordPress, Joomla o Drupal permite buscar fallos conocidos de esa versión.",
         "Knowing the exact WordPress, Joomla or Drupal version lets attackers look up its known flaws."),
        ("Quita la etiqueta generator y mantén el CMS y sus plugins actualizados.",
         "Remove the generator tag and keep the CMS and its plugins up to date."),
        "A02", [200], ["T1592.002"], info=True),
    "formulario-inseguro": _c(
        ("Formulario que envía datos por HTTP", "Form submits data over HTTP"),
        ("Los datos del formulario viajan sin cifrar.", "Form data travels unencrypted."),
        ("Usa siempre acciones https:// en los formularios.", "Always use https:// form actions."),
        "A04", [319], ["T1557", "T1040"], "AV:N/AC:H/AT:P/PR:N/UI:P/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "password-get": _c(
        ("Contraseña enviada por GET", "Password sent with GET"),
        ("La contraseña queda en la URL: historial, registros del servidor y cabecera Referer.",
         "The password ends up in the URL: history, server logs and the Referer header."),
        ("Envía los formularios de acceso con method=\"post\".", "Submit login forms with method=\"post\"."),
        "A07", [598], ["T1552.001"], "AV:N/AC:L/AT:P/PR:N/UI:P/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N"),
    "sin-csrf": _c(
        ("Formulario sin token anti-CSRF aparente", "Form without an apparent anti-CSRF token"),
        ("Otra web podría hacer que el navegador del usuario envíe el formulario en su nombre.",
         "Another site could make the user's browser submit the form on their behalf."),
        ("Incluye un token aleatorio por sesión en los formularios POST y valídalo en el servidor; usa SameSite.",
         "Include a random per-session token in POST forms and validate it server-side; use SameSite."),
        "A01", [352], ["T1185", "T1204.001"], "AV:N/AC:L/AT:N/PR:N/UI:A/VC:N/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "emails-expuestos": _c(
        ("Direcciones de correo publicadas", "Published email addresses"),
        ("Facilitan campañas de phishing y spam dirigidas.", "They make targeted phishing and spam campaigns easier."),
        ("Usa formularios de contacto o alias genéricos y filtros antispam.", "Use contact forms or generic aliases and spam filters."),
        "A06", [200], ["T1589.002", "T1594"], info=True),
    "comentarios-sensibles": _c(
        ("Comentarios HTML con información sensible", "HTML comments with sensitive information"),
        ("Los comentarios del código fuente pueden revelar rutas, usuarios, tareas pendientes o claves.",
         "Source code comments may reveal paths, users, pending tasks or keys."),
        ("Elimina los comentarios en el paso de publicación.", "Strip comments in the build or deployment step."),
        "A02", [615], ["T1594"], "AV:N/AC:L/AT:P/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N"),
    "error-detallado": _c(
        ("Mensajes de error detallados", "Detailed error messages"),
        ("Trazas de pila y errores de base de datos revelan tecnología, rutas y consultas.",
         "Stack traces and database errors reveal technology, paths and queries."),
        ("Muestra errores genéricos al usuario y guarda el detalle solo en los registros.",
         "Show generic errors to users and keep details in the logs only."),
        "A10", [209], ["T1592.002", "T1190"], "AV:N/AC:L/AT:P/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N"),
    "listado-directorios": _c(
        ("Listado de directorios activado", "Directory listing enabled"),
        ("Cualquiera puede ver y descargar todos los ficheros de esa carpeta.", "Anyone can see and download every file in that folder."),
        ("Desactiva el listado de directorios (Options -Indexes, autoindex off).", "Disable directory listing (Options -Indexes, autoindex off)."),
        "A01", [548], ["T1083"], "AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N", e="A"),
    "secreto-expuesto": _c(
        ("Clave o token expuesto en la web", "Key or token exposed on the website"),
        ("Cualquier visitante puede usar la clave para acceder al servicio asociado.", "Any visitor can use the key to access the associated service."),
        ("Revoca la clave, crea otra y no la incluyas en el código del cliente; si es pública por diseño, restríngela por dominio.",
         "Revoke the key, issue a new one and keep it out of client code; if it is public by design, restrict it by domain."),
        "A07", [798, 200], ["T1552.001", "T1078"], "AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:L/VA:N/SC:H/SI:L/SA:N", e="P"),
    "source-map": _c(
        ("Mapas de código fuente publicados", "Source maps published"),
        ("Permiten reconstruir el código original, con comentarios y nombres internos.",
         "They let anyone rebuild the original code, with comments and internal names."),
        ("No publiques los .map en producción o restringe su acceso.", "Do not publish .map files in production or restrict access to them."),
        "A02", [540], ["T1592.002"], info=True),
    "sin-security-txt": _c(
        ("Falta /.well-known/security.txt", "Missing /.well-known/security.txt"),
        ("Quien encuentre un fallo no tiene un canal claro para avisar (RFC 9116).",
         "Whoever finds a flaw has no clear channel to report it (RFC 9116)."),
        ("Publica un security.txt con contacto y fecha de caducidad.", "Publish a security.txt with a contact and an expiry date."),
        "A09", [1059], [], info=True),
    "robots-sensible": _c(
        ("robots.txt señala rutas sensibles", "robots.txt points to sensitive paths"),
        ("robots.txt es público: listar ahí rutas de administración o copias las descubre a cualquiera.",
         "robots.txt is public: listing admin or backup paths there reveals them to anyone."),
        ("Protege esas rutas con autenticación en lugar de ocultarlas.", "Protect those paths with authentication instead of hiding them."),
        "A01", [200], ["T1594"], info=True),
    # --- Modo activo -----------------------------------------------------------
    "git-expuesto": _c(
        ("Repositorio .git accesible", "Accessible .git repository"),
        ("Se puede descargar el código fuente completo y su historial, a menudo con contraseñas.",
         "The full source code and history can be downloaded, often with passwords."),
        ("Bloquea el acceso a /.git en el servidor y no despliegues esa carpeta.", "Block access to /.git on the server and do not deploy that folder."),
        "A02", [538, 527], ["T1213", "T1552.001"], "AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:L/SI:N/SA:N", e="A"),
    "env-expuesto": _c(
        ("Fichero .env accesible", "Accessible .env file"),
        ("Suele contener contraseñas de bases de datos, claves de API y secretos de la aplicación.",
         "It usually contains database passwords, API keys and application secrets."),
        ("Retira el fichero de la carpeta pública, bloquea /.env y cambia todos los secretos que contenga.",
         "Remove the file from the public folder, block /.env and rotate every secret in it."),
        "A02", [538, 798], ["T1552.001", "T1078"], "AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:N", e="A"),
    "copia-expuesta": _c(
        ("Copia de seguridad o volcado accesible", "Accessible backup or dump"),
        ("Permite descargar el código o la base de datos completa.", "It allows downloading the code or the whole database."),
        ("Saca las copias de la carpeta pública y guárdalas cifradas fuera del servidor web.",
         "Move backups out of the web root and store them encrypted outside the web server."),
        "A02", [530], ["T1213"], "AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:N/VA:N/SC:N/SI:N/SA:N", e="A"),
    "config-expuesta": _c(
        ("Fichero de configuración accesible", "Accessible configuration file"),
        ("Copias de configuración (.bak, ~) se sirven como texto y exponen credenciales.",
         "Configuration backups (.bak, ~) are served as text and expose credentials."),
        ("Borra esas copias y bloquea extensiones de copia en el servidor.", "Delete those copies and block backup extensions on the server."),
        "A02", [538, 260], ["T1552.001"], "AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N", e="A"),
    "info-servidor": _c(
        ("Página de diagnóstico del servidor accesible", "Server diagnostics page accessible"),
        ("phpinfo, server-status o actuator revelan configuración, rutas, variables y a veces secretos.",
         "phpinfo, server-status or actuator reveal configuration, paths, variables and sometimes secrets."),
        ("Elimina esas páginas o restringe su acceso a administradores.", "Remove those pages or restrict them to administrators."),
        "A02", [200, 215], ["T1592.002"], "AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N", e="A"),
    "usuarios-enumerables": _c(
        ("Se pueden enumerar los usuarios", "Users can be enumerated"),
        ("La API pública lista los nombres de usuario, lo que facilita ataques de fuerza bruta.",
         "The public API lists usernames, which helps brute-force attacks."),
        ("Restringe /wp-json/wp/v2/users a usuarios autenticados.", "Restrict /wp-json/wp/v2/users to authenticated users."),
        "A01", [200, 204], ["T1087", "T1110"], "AV:N/AC:L/AT:N/PR:N/UI:N/VC:L/VI:N/VA:N/SC:N/SI:N/SA:N", e="A"),
    "xmlrpc": _c(
        ("XML-RPC de WordPress activo", "WordPress XML-RPC enabled"),
        ("Permite probar muchas contraseñas en una sola petición y lanzar ataques pingback.",
         "It allows trying many passwords in a single request and pingback attacks."),
        ("Desactiva xmlrpc.php si no lo usas.", "Disable xmlrpc.php if you do not use it."),
        "A07", [307], ["T1110", "T1499"], "AV:N/AC:L/AT:P/PR:N/UI:N/VC:L/VI:L/VA:L/SC:N/SI:N/SA:N", e="A"),
    "panel-admin": _c(
        ("Panel de administración expuesto a Internet", "Administration panel exposed to the Internet"),
        ("Cualquiera puede intentar acceder; es un objetivo habitual de fuerza bruta.", "Anyone can try to log in; it is a common brute-force target."),
        ("Restringe el panel por IP o VPN, activa MFA y limita los intentos.", "Restrict the panel by IP or VPN, enable MFA and rate-limit attempts."),
        "A07", [1390], ["T1110", "T1078"], info=True),
    "metodos-peligrosos": _c(
        ("Métodos HTTP peligrosos permitidos", "Dangerous HTTP methods allowed"),
        ("TRACE, PUT o DELETE habilitados pueden permitir robo de cookies o modificar ficheros.",
         "Enabled TRACE, PUT or DELETE may allow cookie theft or file modification."),
        ("Permite solo GET, POST y HEAD donde haga falta.", "Allow only GET, POST and HEAD where needed."),
        "A02", [749], ["T1505.003"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "cors-reflejado": _c(
        ("CORS refleja cualquier origen con credenciales", "CORS reflects any origin with credentials"),
        ("Cualquier web puede leer respuestas autenticadas del usuario.", "Any website can read the user's authenticated responses."),
        ("Valida el origen contra una lista cerrada antes de devolverlo.", "Validate the origin against a fixed allow-list before echoing it."),
        "A01", [942, 346], ["T1185"], "AV:N/AC:L/AT:N/PR:N/UI:A/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N", e="P"),
    "tls-antiguo-aceptado": _c(
        ("El servidor acepta TLS 1.0 o 1.1", "The server accepts TLS 1.0 or 1.1"),
        ("Un atacante puede forzar una conexión con un protocolo débil.", "An attacker can force a connection using a weak protocol."),
        ("Desactiva TLS 1.0 y 1.1.", "Disable TLS 1.0 and 1.1."),
        "A04", [326, 757], ["T1557"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    # --- Código y ficheros -------------------------------------------------------
    "secreto-codigo": _c(
        ("Credencial o clave escrita en el código", "Credential or key hard-coded in source"),
        ("Cualquiera con acceso al código (o a su historial) obtiene acceso al servicio.",
         "Anyone with access to the code (or its history) gets access to the service."),
        ("Mueve el secreto a un gestor de secretos o variable de entorno y revócalo: sigue en el historial de Git.",
         "Move the secret to a secrets manager or environment variable and revoke it: it remains in the Git history."),
        "A07", [798], ["T1552.001", "T1078"], "AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:H/VA:L/SC:L/SI:L/SA:N"),
    "clave-privada": _c(
        ("Clave privada incluida en los ficheros", "Private key included in the files"),
        ("Permite suplantar al servidor o descifrar comunicaciones.", "It allows impersonating the server or decrypting traffic."),
        ("Retírala, revoca el certificado o la clave y genera una nueva.", "Remove it, revoke the certificate or key and generate a new one."),
        "A04", [321], ["T1552.004"], "AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:H/VA:N/SC:L/SI:L/SA:N"),
    "env-en-ficheros": _c(
        ("Fichero .env con secretos entre los ficheros", "A .env file with secrets among the files"),
        ("Los ficheros .env no deben compartirse ni subirse al repositorio.", "Env files must not be shared or committed."),
        ("Añade .env a .gitignore, publica solo un .env.example y cambia los secretos expuestos.",
         "Add .env to .gitignore, publish only a .env.example and rotate exposed secrets."),
        "A02", [538], ["T1552.001"], "AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "inyeccion-sql": _c(
        ("Posible inyección SQL (consulta concatenada)", "Possible SQL injection (concatenated query)"),
        ("Si alguna variable viene del usuario, puede leer o modificar la base de datos.",
         "If any variable comes from the user, they can read or modify the database."),
        ("Usa consultas parametrizadas o un ORM; nunca concatenes valores en el SQL.",
         "Use parameterised queries or an ORM; never concatenate values into SQL."),
        "A05", [89], ["T1190"], "AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N"),
    "inyeccion-comandos": _c(
        ("Posible inyección de comandos del sistema", "Possible OS command injection"),
        ("Ejecutar comandos con una shell y texto variable permite ejecutar órdenes arbitrarias.",
         "Running commands through a shell with variable text allows arbitrary commands."),
        ("Pasa los argumentos como lista y sin shell; valida las entradas con listas blancas.",
         "Pass arguments as a list without a shell; validate inputs with allow-lists."),
        "A05", [78], ["T1059", "T1190"], "AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"),
    "evaluacion-dinamica": _c(
        ("Evaluación dinámica de código (eval)", "Dynamic code evaluation (eval)"),
        ("eval, exec, new Function o Invoke-Expression ejecutan texto como código.",
         "eval, exec, new Function or Invoke-Expression run text as code."),
        ("Sustitúyelo por estructuras de datos o funciones explícitas.", "Replace it with data structures or explicit functions."),
        "A05", [95], ["T1059", "T1190"], "AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N"),
    "deserializacion": _c(
        ("Deserialización insegura", "Insecure deserialisation"),
        ("pickle, yaml.load, unserialize o BinaryFormatter con datos externos permiten ejecutar código.",
         "pickle, yaml.load, unserialize or BinaryFormatter on external data allow code execution."),
        ("Usa formatos seguros (JSON) o cargadores seguros (yaml.safe_load).", "Use safe formats (JSON) or safe loaders (yaml.safe_load)."),
        "A08", [502], ["T1190", "T1059"], "AV:N/AC:L/AT:P/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"),
    "xss-dom": _c(
        ("Posible XSS en el navegador (innerHTML, document.write)", "Possible DOM XSS (innerHTML, document.write)"),
        ("Insertar HTML construido con datos permite ejecutar scripts.", "Inserting HTML built from data allows script execution."),
        ("Usa textContent o una librería de saneado como DOMPurify.", "Use textContent or a sanitising library such as DOMPurify."),
        "A05", [79], ["T1059.007", "T1189"], "AV:N/AC:L/AT:P/PR:N/UI:A/VC:L/VI:L/VA:N/SC:L/SI:L/SA:N"),
    "tls-desactivado": _c(
        ("Verificación TLS desactivada en el código", "TLS verification disabled in code"),
        ("Las conexiones aceptan cualquier certificado y son vulnerables a intermediarios.",
         "Connections accept any certificate and are open to man-in-the-middle attacks."),
        ("Mantén la verificación activada y, si hace falta, añade la CA interna al almacén de confianza.",
         "Keep verification on and, if needed, add the internal CA to the trust store."),
        "A04", [295], ["T1557"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:H/VA:N/SC:N/SI:N/SA:N"),
    "cripto-debil": _c(
        ("Criptografía débil", "Weak cryptography"),
        ("MD5, SHA-1, DES, RC4 o el modo ECB no protegen contraseñas ni datos.", "MD5, SHA-1, DES, RC4 or ECB mode do not protect passwords or data."),
        ("Usa Argon2, scrypt o bcrypt para contraseñas y AES-GCM o ChaCha20-Poly1305 para datos.",
         "Use Argon2, scrypt or bcrypt for passwords and AES-GCM or ChaCha20-Poly1305 for data."),
        "A04", [327, 328], ["T1557"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "aleatorio-inseguro": _c(
        ("Aleatoriedad no criptográfica para secretos", "Non-cryptographic randomness for secrets"),
        ("Math.random o random no sirven para tokens, contraseñas o identificadores de sesión.",
         "Math.random or random are not suitable for tokens, passwords or session identifiers."),
        ("Usa secrets (Python), crypto.getRandomValues (JS) o RandomNumberGenerator (.NET).",
         "Use secrets (Python), crypto.getRandomValues (JS) or RandomNumberGenerator (.NET)."),
        "A04", [330, 338], ["T1110"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "modo-depuracion": _c(
        ("Modo de depuración activado", "Debug mode enabled"),
        ("Muestra trazas, variables y a veces una consola interactiva en producción.",
         "It shows traces, variables and sometimes an interactive console in production."),
        ("Desactiva la depuración en producción mediante configuración por entorno.", "Disable debugging in production through environment configuration."),
        "A02", [489, 215], ["T1592.002", "T1059"], "AV:N/AC:L/AT:P/PR:N/UI:N/VC:L/VI:L/VA:N/SC:N/SI:N/SA:N"),
    "excepcion-silenciada": _c(
        ("Excepciones silenciadas", "Silenced exceptions"),
        ("Capturar errores sin tratarlos ni registrarlos oculta fallos y ataques.", "Catching errors without handling or logging them hides failures and attacks."),
        ("Captura excepciones concretas, regístralas y falla de forma segura.", "Catch specific exceptions, log them and fail safely."),
        "A10", [390, 703], ["T1565"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:N/VI:L/VA:L/SC:N/SI:N/SA:N"),
    "dependencia-sin-fijar": _c(
        ("Dependencias sin versión fijada", "Dependencies without pinned versions"),
        ("Cada instalación puede traer una versión distinta, incluida una comprometida.",
         "Each install may pull a different version, including a compromised one."),
        ("Fija versiones exactas y usa ficheros de bloqueo con hashes.", "Pin exact versions and use lock files with hashes."),
        "A03", [1357, 829], ["T1195.001"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:H/VA:L/SC:N/SI:N/SA:N"),
    "descarga-ejecutada": _c(
        ("Se descarga y ejecuta código sin verificar", "Code is downloaded and executed without verification"),
        ("«curl … | sh» o «iex (iwr …)» ejecutan lo que haya en el servidor remoto en ese momento.",
         "«curl … | sh» or «iex (iwr …)» run whatever the remote server holds at that moment."),
        ("Descarga, verifica la firma o el hash y solo entonces ejecuta.", "Download, verify the signature or hash, and only then execute."),
        "A08", [494], ["T1195.002", "T1059"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"),
    "accion-sin-fijar": _c(
        ("Acción de GitHub sin fijar a un commit", "GitHub Action not pinned to a commit"),
        ("Una etiqueta (v1, main) puede moverse a código malicioso, como ocurrió con tj-actions/changed-files.",
         "A tag (v1, main) can be moved to malicious code, as happened with tj-actions/changed-files."),
        ("Fija las acciones por SHA completo y deja la versión en un comentario.", "Pin actions by full SHA and keep the version in a comment."),
        "A03", [829], ["T1195.002"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:H/VA:N/SC:L/SI:L/SA:N"),
    "contenedor-root": _c(
        ("Contenedor que se ejecuta como root", "Container running as root"),
        ("Si la aplicación se compromete, el atacante tiene privilegios máximos en el contenedor.",
         "If the application is compromised, the attacker gets full privileges in the container."),
        ("Añade un usuario sin privilegios con USER.", "Add an unprivileged user with USER."),
        "A02", [250], ["T1190"], "AV:N/AC:H/AT:P/PR:N/UI:N/VC:L/VI:L/VA:L/SC:N/SI:N/SA:N"),
    "imagen-latest": _c(
        ("Imagen base sin versión fijada", "Base image without a pinned version"),
        ("«latest» cambia con el tiempo y puede introducir vulnerabilidades sin aviso.",
         "«latest» changes over time and can introduce vulnerabilities without notice."),
        ("Fija la imagen por versión y, mejor, por digest sha256.", "Pin the image by version and preferably by sha256 digest."),
        "A03", [1357], ["T1195.002"], info=True),
}

# Librerías JavaScript: (nombre, patrón de versión en URL o cabecera, [(versión corregida, [CVE])], sin soporte)
LIBRERIAS = [
    ("jQuery", r"jquery(?:[.-]|/)(\d+\.\d+\.\d+)(?:[./-]|$)|jquery(?:\.min)?\.js\?ver=(\d+\.\d+\.\d+)|jQuery v(\d+\.\d+\.\d+)",
     [("1.9.0", ["CVE-2012-6708"]), ("3.0.0", ["CVE-2015-9251"]), ("3.4.0", ["CVE-2019-11358"]),
      ("3.5.0", ["CVE-2020-11022", "CVE-2020-11023"])], None),
    ("jQuery UI", r"jquery-ui(?:[.-]|/)(\d+\.\d+\.\d+)|jQuery UI - v(\d+\.\d+\.\d+)",
     [("1.13.0", ["CVE-2021-41182", "CVE-2021-41183", "CVE-2021-41184"]), ("1.13.2", ["CVE-2022-31160"])], None),
    ("Bootstrap", r"bootstrap(?:[.-]|/|@)(\d+\.\d+\.\d+)|Bootstrap v(\d+\.\d+\.\d+)",
     [("3.4.0", ["CVE-2018-14040", "CVE-2018-14041", "CVE-2018-14042"]), ("3.4.1", ["CVE-2019-8331"])], None),
    ("AngularJS", r"angular(?:js)?(?:[.-]|/|@)(1\.\d+\.\d+)|AngularJS v(1\.\d+\.\d+)", [], "AngularJS 1.x (EOL 2021-12-31)"),
    ("Lodash", r"lodash(?:[.-]|/|@)(\d+\.\d+\.\d+)|lodash (\d+\.\d+\.\d+)", [("4.17.21", ["CVE-2021-23337"])], None),
    ("Moment.js", r"moment(?:[.-]|/|@)(\d+\.\d+\.\d+)|moment\.js[^\n]{0,20}version : (\d+\.\d+\.\d+)",
     [("2.29.2", ["CVE-2022-24785"]), ("2.29.4", ["CVE-2022-31129"])], None),
    ("Handlebars", r"handlebars(?:[.-]|/|@)(\d+\.\d+\.\d+)|handlebars v(\d+\.\d+\.\d+)", [("4.7.7", ["CVE-2021-23369"])], None),
]
# Bootstrap 4 tiene su propia corrección de CVE-2019-8331
BOOTSTRAP4 = ("4.3.1", ["CVE-2019-8331"])

# Hosts de terceros cuyo script cambia por diseño y no admite SRI
SIN_SRI_POSIBLE = re.compile(r"googletagmanager\.com|google-analytics\.com|gstatic\.com/recaptcha|google\.com/recaptcha|"
                             r"maps\.googleapis\.com|js\.stripe\.com|connect\.facebook\.net|platform\.twitter\.com|"
                             r"static\.hotjar\.com|cdn\.cookielaw\.org|consent\.cookiebot\.com|challenges\.cloudflare\.com|"
                             r"js\.hs-scripts\.com|snap\.licdn\.com|www\.youtube\.com", re.I)

SECRETOS = [
    ("AWS access key", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Stripe secret key", re.compile(r"\b[sr]k_live_[0-9a-zA-Z]{20,}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{60,}\b")),
    ("Slack token", re.compile(r"\bxox[abposr]-[0-9A-Za-z-]{10,}\b")),
    ("Slack webhook", re.compile(r"https://hooks\.slack\.com/services/T[0-9A-Z]{6,}/B[0-9A-Z]{6,}/[0-9A-Za-z]{20,}")),
    ("SendGrid key", re.compile(r"\bSG\.[0-9A-Za-z_-]{22}\.[0-9A-Za-z_-]{43}\b")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("Private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----")),
]
RE_SECRETO_GENERICO = re.compile(
    r"(?i)\b\w*?(password|passwd|pwd|contrase(?:ñ|n)a|secret|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|client[_-]?secret)\b"
    r"[\"']?\s*[:=]\s*[\"']([^\"'\s]{8,120})[\"']")
RE_MARCADOR_POSICION = re.compile(r"(?i)^(?:(?:your|tu|su|change|cambia|example|ejemplo|test|dummy|placeholder|redacted|replace|"
                                  r"password|secret|null|none|undefined|true|false)(?:[_\-\s.:]|$)|x{3,}|\*+|<|\$\{|\{\{|%)")

RE_EMAIL = re.compile(r"(?<![\w.%+-])[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}\b")
RE_COMENTARIO_HTML = re.compile(r"<!--(?!\[if|\s*\[endif|<!)(.{0,2000}?)-->", re.S)
RE_COMENTARIO_SENSIBLE = re.compile(r"(?i)\b(password|passwd|contrase(?:ñ|n)a|todo|fixme|hack|debug|api[_ -]?key|secret|"
                                    r"token|usuario|username|admin|staging|preprod|192\.168\.|10\.\d+\.\d+\.\d+)\b")
RE_ERRORES = re.compile(r"Traceback \(most recent call last\)|<b>(?:Fatal error|Warning|Parse error)</b>:|"
                        r"\bSQLSTATE\[|\bORA-\d{5}\b|You have an error in your SQL syntax|Microsoft OLE DB Provider|"
                        r"\bat [\w$.]+\([\w]+\.java:\d+\)|Server Error in '/' Application|System\.NullReferenceException|"
                        r"Whoops, looks like something went wrong|DEBUG = True|Stack trace:", re.I)
RE_FORM = re.compile(r"<form\b([^>]{0,2000})>(.*?)</form>", re.I | re.S)
RE_INPUT = re.compile(r"<(?:input|select|textarea)\b([^>]{0,1000})>", re.I)
RE_ETIQUETA_RECURSO = re.compile(r"<(script|iframe|link|img|audio|video|source|embed|object)\b([^>]{0,2000})>", re.I)
CAMPOS_PERSONALES = re.compile(r"(?i)e-?mail|correo|tel(?:efono|éfono|ephone)?\b|phone|movil|móvil|dni|nif|nie|passport|"
                               r"pasaporte|nombre|apellido|first.?name|last.?name|surname|direcci[oó]n|address|nacimiento|"
                               r"birth|postal|zip")
CAMPOS_PAGO = re.compile(r"(?i)card.?number|cc-?number|tarjeta|cvv|cvc|iban|expir|caducidad")
RE_SCRIPTS_PAGO = re.compile(r"js\.stripe\.com|paypal\.com/sdk|paypalobjects|redsys|sis\.redsys\.es|adyen|braintree", re.I)
RE_TOKEN_CSRF = re.compile(r"(?i)csrf|xsrf|_token|authenticity|nonce|requestverificationtoken|__viewstate|form_key|"
                           r"form_build_id|_wpnonce")
COOKIES_SESION = re.compile(r"(?i)sess|sid\b|^sid|token|auth|jwt|login|phpsessid|jsessionid|asp\.net_sessionid|"
                            r"laravel_session|wordpress_logged_in|connect\.sid|remember")


def _t(par: tuple[str, str]) -> str:
    return par[0] if aimarkers.idioma() == "es" else par[1]


def registrar_textos() -> None:
    aimarkers.TEXTOS.update(TEXTOS)


registrar_textos()


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------

NIVEL_V = {"N": 0, "L": 1, "H": 2}
NIVEL_R = {"L": 1, "M": 2, "H": 3}
IMPACTO_DE = {0: 1, 1: 1, 2: 2, 3: 3, 4: 4, 6: 5}


@dataclass
class Contexto:
    login: bool = False
    datos: bool = False
    pagos: bool = False
    subida: bool = False
    formularios: bool = False
    ficheros: bool = False

    def requisitos(self) -> dict[str, str]:
        if self.ficheros:
            return {"CR": "M", "IR": "M", "AR": "M"}
        cr = "H" if (self.login or self.datos or self.pagos) else ("M" if self.formularios else "L")
        ir = "H" if (self.login or self.pagos) else ("M" if (self.formularios or self.subida) else "L")
        ar = "H" if self.pagos else "M"
        return {"CR": cr, "IR": ir, "AR": ar}

    def descripcion(self) -> str:
        if self.ficheros:
            return aimarkers.t("seg.contexto_ficheros")
        partes = [aimarkers.t(f"seg.ctx.{k}") for k, v in (("login", self.login), ("datos", self.datos),
                                                             ("pagos", self.pagos), ("subida", self.subida)) if v]
        if not partes and self.formularios:
            partes.append(aimarkers.t("seg.ctx.formularios"))
        return ", ".join(partes) or aimarkers.t("seg.contexto_ninguno")


@dataclass
class HallazgoSeg:
    id: str
    clave: str
    detalle: str = ""                     # texto añadido al título (p. ej. «jQuery 1.12.4»)
    evidencias: list[tuple[str, str]] = field(default_factory=list)  # (ubicación, extracto)
    cve: list[str] = field(default_factory=list)
    vector_base: str | None = None
    e: str | None = None

    @property
    def ficha(self) -> dict:
        return CATALOGO[self.id]

    @property
    def informativo(self) -> bool:
        return bool(self.ficha["info"])


@dataclass
class InformeSeguridad:
    contexto: Contexto = field(default_factory=Contexto)
    hallazgos: dict[str, HallazgoSeg] = field(default_factory=dict)
    notas: list[str] = field(default_factory=list)
    modo: str = "pasivo"
    tls: dict = field(default_factory=dict)

    def anadir(self, id_: str, ubicacion: str, extracto: str = "", clave: str = "", detalle: str = "",
               cve: list[str] | None = None, vector: str | None = None, e: str | None = None) -> None:
        llave = f"{id_}|{clave}"
        h = self.hallazgos.get(llave)
        if h is None:
            h = self.hallazgos[llave] = HallazgoSeg(id_, clave, detalle, [], list(cve or []), vector, e)
        extracto = re.sub(r"\s+", " ", extracto).strip()[:200]
        if len(h.evidencias) < 25 and (ubicacion, extracto) not in h.evidencias:
            h.evidencias.append((ubicacion, extracto))

    # --- cálculo -----------------------------------------------------------
    def evaluar(self, h: HallazgoSeg) -> dict:
        ficha = h.ficha
        req = self.contexto.requisitos()
        base_txt = h.vector_base or ficha["v"]
        datos = {"id": h.id, "titulo": _t(ficha["t"]) + (f": {h.detalle}" if h.detalle else ""),
                 "descripcion": _t(ficha["d"]), "recomendacion": _t(ficha["r"]),
                 "owasp": ficha["o"], "owasp_nombre": _t(OWASP[ficha["o"]]),
                 "cwe": [f"CWE-{c}" for c in ficha["cwe"]],
                 "mitre": [{"id": m, "nombre": MITRE[m]} for m in ficha["mitre"]],
                 "cve": h.cve, "evidencias": [{"ubicacion": u, "extracto": x} for u, x in h.evidencias],
                 "veces": len(h.evidencias), "informativo": h.informativo}
        if base_txt is None:
            datos.update({"cvss": None, "cvss_base": None, "vector": None, "severidad": "none",
                          "cid": {"C": "N", "I": "N", "D": "N"}, "probabilidad": 2, "impacto": 1})
        else:
            base = "CVSS:4.0/" + base_txt
            completo = cvss4.componer(base, E=h.e or ficha["e"], **req)
            m = cvss4.parsear(completo)
            valor = cvss4.puntuacion(completo)
            datos.update({"cvss": valor, "cvss_base": cvss4.puntuacion(base), "vector": completo,
                          "severidad": cvss4.severidad(valor)})
            c = max(NIVEL_V[m["VC"]], NIVEL_V[m["SC"]])
            i = max(NIVEL_V[m["VI"]], NIVEL_V[m["SI"]])
            d = max(NIVEL_V[m["VA"]], NIVEL_V[m["SA"]])
            letra = {0: "N", 1: "L", 2: "H"}
            datos["cid"] = {"C": letra[c], "I": letra[i], "D": letra[d]}
            impacto = max(c * NIVEL_R[req["CR"]], i * NIVEL_R[req["IR"]], d * NIVEL_R[req["AR"]])
            datos["impacto"] = IMPACTO_DE.get(impacto, 5)
            # Probabilidad 1-5 a partir de la explotabilidad CVSS y de la madurez del exploit
            p = 1.0 + (m["AV"] == "N") + (m["AC"] == "L") + (m["AT"] == "N") + 0.5 * (m["PR"] == "N") \
                + {"N": 1.0, "P": 0.5, "A": 0.0}[m["UI"]] + {"A": 0.5, "P": 0.0, "U": -0.5}[m["E"]]
            datos["probabilidad"] = max(1, min(5, int(p + 0.5)))
        datos["riesgo"] = datos["probabilidad"] * datos["impacto"]
        datos["nivel_riesgo"] = nivel_riesgo(datos["riesgo"])
        return datos

    def evaluados(self) -> list[dict]:
        lista = [self.evaluar(h) for h in self.hallazgos.values()]
        lista.sort(key=lambda x: (-x["riesgo"], -(x["cvss"] or 0), x["titulo"]))
        return lista

    def a_dict(self) -> dict:
        hallazgos = self.evaluados()
        req = self.contexto.requisitos()
        matriz = [[0] * 5 for _ in range(5)]
        for h in hallazgos:
            matriz[h["probabilidad"] - 1][h["impacto"] - 1] += 1
        triada = {}
        for dim in ("C", "I", "D"):
            afectados = [h for h in hallazgos if h["cid"][dim] != "N"]
            maximo = max((h["riesgo"] for h in afectados), default=0)
            triada[dim] = {"hallazgos": len(afectados), "riesgo_max": maximo,
                           "nivel": nivel_riesgo(maximo) if maximo else "ninguno"}
        puntuados = [h["cvss"] for h in hallazgos if h["cvss"]]
        maximo = max(puntuados, default=0.0)
        por_severidad = {s: sum(1 for h in hallazgos if h["severidad"] == s) for s in ("critical", "high", "medium", "low", "none")}
        return {"modo": self.modo, "contexto": self.contexto.descripcion(), "requisitos": req,
                "cvss_max": maximo, "severidad_max": cvss4.severidad(maximo), "por_severidad": por_severidad,
                "triada": triada, "matriz": matriz, "hallazgos": hallazgos, "notas": self.notas, "tls": self.tls,
                "owasp_version": "OWASP Top 10:2025", "cvss_version": "CVSS v4.0"}


def nivel_riesgo(valor: int) -> str:
    if valor >= 17:
        return "critico"
    if valor >= 10:
        return "alto"
    if valor >= 5:
        return "medio"
    return "bajo"


def _version(texto: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", texto)[:3])


# ---------------------------------------------------------------------------
# Comprobaciones de contenido (HTML y JavaScript)
# ---------------------------------------------------------------------------


def detectar_librerias(informe: InformeSeguridad, texto: str, ubic: str) -> None:
    for nombre, patron, correcciones, eol in LIBRERIAS:
        for m in re.finditer(patron, texto, re.I):
            version = next((g for g in m.groups() if g), None)
            if not version:
                continue
            v = _version(version)
            if eol:
                informe.anadir("libreria-sin-soporte", ubic, m.group(0), clave=nombre, detalle=f"{nombre} {version}")
                break
            fixes = list(correcciones)
            if nombre == "Bootstrap" and v[:1] == (4,):
                fixes = [BOOTSTRAP4]
            elif nombre == "Bootstrap" and v[:1] >= (5,):
                fixes = []
            cves = [c for fijo, lista in fixes if v < _version(fijo) for c in lista]
            if cves:
                informe.anadir("libreria-vulnerable", ubic, m.group(0), clave=f"{nombre} {version}",
                               detalle=f"{nombre} {version}", cve=cves)
            break


def buscar_secretos(informe: InformeSeguridad, texto: str, ubic: str, id_: str = "secreto-expuesto") -> None:
    for nombre, patron in SECRETOS:
        m = patron.search(texto)
        if m:
            valor = m.group(0)
            oculto = valor[:8] + "…" if len(valor) > 12 else valor
            if nombre == "Private key":
                informe.anadir("clave-privada" if id_ == "secreto-codigo" else id_, ubic, valor, clave=nombre, detalle=nombre)
            else:
                informe.anadir(id_, ubic, f"{nombre}: {oculto}", clave=nombre, detalle=nombre)


def analizar_html_seguridad(informe: InformeSeguridad, texto: str, url: str, ubic: str) -> None:
    """Comprobaciones sobre el contenido de una página (válidas también para HTML local)."""
    es_https = url.lower().startswith("https://")
    ctx = informe.contexto
    # Recursos: contenido mixto y SRI
    for m in RE_ETIQUETA_RECURSO.finditer(texto):
        etiqueta = m.group(1).lower()
        attrs = web.atributos(m.group(2))
        destino = attrs.get("src") or (attrs.get("href") if etiqueta == "link" else "") or attrs.get("data") or ""
        if not destino:
            continue
        absoluta = urllib.parse.urljoin(url, destino) if url.startswith("http") else destino
        if etiqueta == "link" and "stylesheet" not in attrs.get("rel", "").lower() and "preload" not in attrs.get("rel", "").lower():
            continue
        if es_https and absoluta.lower().startswith("http://"):
            activo = etiqueta in ("script", "iframe", "link", "embed", "object")
            informe.anadir("contenido-mixto" if activo else "contenido-mixto-pasivo", ubic, f"<{etiqueta}> {absoluta}")
        if etiqueta in ("script", "link") and absoluta.lower().startswith(("http://", "https://", "//")) \
                and url.startswith("http") and not web.mismo_sitio(absoluta, url) and "integrity" not in attrs:
            if not SIN_SRI_POSIBLE.search(absoluta):
                informe.anadir("sin-sri", ubic, absoluta, clave=absoluta.split("?")[0])
        if etiqueta == "script":
            detectar_librerias(informe, absoluta, ubic)
            if RE_SCRIPTS_PAGO.search(absoluta):
                ctx.pagos = True
    # CMS
    gen = re.search(r"<meta[^>]{0,200}name=[\"']generator[\"'][^>]{0,200}content=[\"']((?:WordPress|Joomla!?|Drupal)[^\"']{0,40}\d[^\"']{0,20})",
                    texto, re.I)
    if gen:
        informe.anadir("cms-version", ubic, gen.group(1), clave="cms", detalle=gen.group(1))
    # Formularios
    for f in RE_FORM.finditer(texto):
        attrs = web.atributos(f.group(1))
        campos = [web.atributos(x.group(1)) for x in RE_INPUT.finditer(f.group(2))]
        visibles = [c for c in campos if c.get("type", "text").lower() not in ("hidden", "submit", "button", "image", "reset")]
        if not visibles:
            continue
        ctx.formularios = True
        tiene_password = any(c.get("type", "").lower() == "password" for c in campos)
        nombres = " ".join(f"{c.get('name', '')} {c.get('id', '')} {c.get('type', '')} {c.get('autocomplete', '')}" for c in visibles)
        if tiene_password:
            ctx.login = True
        if CAMPOS_PERSONALES.search(nombres):
            ctx.datos = True
        if CAMPOS_PAGO.search(nombres):
            ctx.pagos = True
        if any(c.get("type", "").lower() == "file" for c in campos):
            ctx.subida = True
        metodo = attrs.get("method", "get").lower()
        accion = urllib.parse.urljoin(url, attrs.get("action", "")) if url.startswith("http") else attrs.get("action", "")
        resumen = f"<form method={metodo} action={attrs.get('action', '')}>"
        if (es_https and accion.lower().startswith("http://")) or (url.lower().startswith("http://") and (tiene_password or ctx.datos)):
            informe.anadir("formulario-inseguro", ubic, resumen)
        if tiene_password and metodo == "get":
            informe.anadir("password-get", ubic, resumen)
        busqueda = len(visibles) == 1 and re.search(r"(?i)\b(q|s|search|buscar|query|keyword)\b", nombres)
        ocultos = " ".join(f"{c.get('name', '')} {c.get('id', '')}" for c in campos if c.get("type", "").lower() == "hidden")
        if metodo == "post" and not busqueda and not RE_TOKEN_CSRF.search(ocultos) and (tiene_password or len(visibles) >= 2):
            informe.anadir("sin-csrf", ubic, resumen)
    # Comentarios, errores, listado de directorios, correos, secretos
    for c in RE_COMENTARIO_HTML.finditer(texto):
        if RE_COMENTARIO_SENSIBLE.search(c.group(1)) and not re.search(r"(?i)google|wordpress|yoast|cache|w3 total|generated", c.group(1)):
            informe.anadir("comentarios-sensibles", ubic, "<!--" + c.group(1)[:150] + "-->")
            break
    error = RE_ERRORES.search(texto)
    if error:
        informe.anadir("error-detallado", ubic, texto[max(0, error.start() - 40):error.end() + 80])
    if re.search(r"<title>\s*Index of /", texto, re.I):
        informe.anadir("listado-directorios", ubic, "Index of /")
    correos = {e.lower() for e in RE_EMAIL.findall(re.sub(r"<script\b.*?</script>", " ", texto, flags=re.S | re.I))
               if not re.search(r"\.(png|jpe?g|gif|webp|svg)$|example\.|sentry|wixpress", e, re.I)}
    for correo in sorted(correos)[:10]:
        informe.anadir("emails-expuestos", ubic, correo, clave="emails")
    buscar_secretos(informe, texto, ubic)


def analizar_js_seguridad(informe: InformeSeguridad, texto: str, ubic: str) -> None:
    detectar_librerias(informe, texto[:4000], ubic)
    buscar_secretos(informe, texto, ubic)
    mapa = re.search(r"//[#@] sourceMappingURL=(?!data:)(\S+\.map)", texto[-2000:])
    if mapa:
        informe.anadir("source-map", ubic, mapa.group(0), clave="map")


# ---------------------------------------------------------------------------
# Comprobaciones de cabeceras, cookies y TLS
# ---------------------------------------------------------------------------


def analizar_cabeceras(informe: InformeSeguridad, p: web.Pagina, ubic: str) -> None:
    es_https = p.url.lower().startswith("https://")
    if es_https:
        hsts = p.cabecera("strict-transport-security")
        if not hsts:
            informe.anadir("sin-hsts", ubic, "Strict-Transport-Security: —")
        else:
            edad = re.search(r"max-age\s*=\s*\"?(\d+)", hsts, re.I)
            if edad and int(edad.group(1)) < 15_552_000:
                informe.anadir("hsts-corto", ubic, f"Strict-Transport-Security: {hsts}")
    if not p.es_html:
        return
    csp = p.cabecera("content-security-policy")
    meta_csp = re.search(r"<meta[^>]{0,200}http-equiv=[\"']content-security-policy[\"'][^>]{0,200}content=[\"']([^\"']+)",
                         p.texto()[:30000], re.I)
    politica = csp or (meta_csp.group(1) if meta_csp else "")
    if not politica:
        extra = " (Report-Only)" if p.cabecera("content-security-policy-report-only") else ""
        informe.anadir("sin-csp", ubic, "Content-Security-Policy: —" + extra)
    else:
        directivas = {d.strip().split(" ")[0].lower(): d.strip() for d in politica.split(";") if d.strip()}
        scripts = directivas.get("script-src") or directivas.get("default-src", "")
        debil = [x for x in ("'unsafe-inline'", "'unsafe-eval'") if x in scripts and "'strict-dynamic'" not in scripts
                 and not re.search(r"'nonce-|'sha(256|384|512)-", scripts)]
        if re.search(r"(?:^|\s)(\*|https?:|data:)(?:\s|$)", scripts):
            debil.append("*/http:/data:")
        if not scripts:
            debil.append("script-src/default-src —")
        if debil:
            informe.anadir("csp-debil", ubic, f"{', '.join(debil)} → {scripts[:150]}")
    if "frame-ancestors" not in politica.lower() and not p.cabecera("x-frame-options"):
        informe.anadir("sin-antiframe", ubic, "X-Frame-Options: — / frame-ancestors: —")
    if p.cabecera("x-content-type-options").lower() != "nosniff":
        informe.anadir("sin-nosniff", ubic, "X-Content-Type-Options: —")
    if not p.cabecera("referrer-policy") and not re.search(r"<meta[^>]{0,100}name=[\"']referrer[\"']", p.texto()[:30000], re.I):
        informe.anadir("sin-referrer", ubic, "Referrer-Policy: —")
    if not p.cabecera("permissions-policy"):
        informe.anadir("sin-permissions-policy", ubic, "Permissions-Policy: —", clave="pp")
    for nombre in ("server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version", "x-generator", "x-drupal-cache", "x-runtime"):
        valor = p.cabecera(nombre)
        if valor and (re.search(r"\d", valor) or nombre in ("x-powered-by", "x-aspnet-version", "x-generator")):
            informe.anadir("version-expuesta", ubic, f"{nombre}: {valor}", clave=nombre, detalle=f"{nombre}: {valor[:40]}")
    acao, acac = p.cabecera("access-control-allow-origin"), p.cabecera("access-control-allow-credentials")
    if acao == "*" and acac.lower() == "true":
        informe.anadir("cors-permisivo", ubic, f"ACAO: {acao}; ACAC: {acac}")
    if re.search(r"type=[\"']password", p.texto(), re.I) and "no-store" not in p.cabecera("cache-control").lower():
        informe.anadir("cache-sensible", ubic, f"Cache-Control: {p.cabecera('cache-control') or '—'}")


def analizar_cookies(informe: InformeSeguridad, p: web.Pagina, ubic: str) -> None:
    es_https = p.url.lower().startswith("https://")
    for linea in p.todas("set-cookie"):
        partes = [x.strip() for x in linea.split(";")]
        nombre = partes[0].split("=", 1)[0].strip()
        if not nombre:
            continue
        atributos = {x.split("=", 1)[0].lower(): (x.split("=", 1)[1] if "=" in x else "") for x in partes[1:]}
        resumen = f"{nombre}; " + "; ".join(partes[1:])[:120]
        if es_https and "secure" not in atributos:
            informe.anadir("cookie-sin-secure", ubic, resumen, clave=nombre, detalle=nombre)
        if COOKIES_SESION.search(nombre) and "httponly" not in atributos:
            informe.anadir("cookie-sin-httponly", ubic, resumen, clave=nombre, detalle=nombre)
        if "samesite" not in atributos or (atributos.get("samesite", "").lower() == "none" and "secure" not in atributos):
            informe.anadir("cookie-sin-samesite", ubic, resumen, clave=nombre, detalle=nombre)


def analizar_tls(informe: InformeSeguridad, host: str, puerto: int = 443) -> None:
    contexto = ssl.create_default_context()
    try:
        with socket.create_connection((host, puerto), timeout=10) as s, contexto.wrap_socket(s, server_hostname=host) as t:
            cert = t.getpeercert() or {}
            informe.tls = {"version": t.version(), "cifrado": (t.cipher() or ("",))[0]}
            caduca = cert.get("notAfter")
            if caduca:
                fecha = datetime.fromtimestamp(ssl.cert_time_to_seconds(caduca), tz=timezone.utc)
                dias = (fecha - datetime.now(timezone.utc)).days
                informe.tls["caduca"] = fecha.date().isoformat()
                informe.tls["dias"] = dias
                if dias < 21:
                    informe.anadir("cert-caduca", f"{host}:{puerto}", f"notAfter: {caduca} ({dias} d)")
            if t.version() in ("TLSv1", "TLSv1.1"):
                informe.anadir("tls-obsoleto", f"{host}:{puerto}", t.version() or "")
    except ssl.SSLCertVerificationError as e:
        informe.anadir("cert-invalido", f"{host}:{puerto}", str(e.verify_message or e))
    except ssl.SSLError as e:
        if re.search(r"unsupported protocol|wrong version|protocol version", str(e), re.I):
            informe.anadir("tls-obsoleto", f"{host}:{puerto}", str(e))
        else:
            informe.notas.append(f"TLS {host}: {e}")
    except OSError as e:
        informe.notas.append(f"TLS {host}: {e}")


# ---------------------------------------------------------------------------
# Modo activo: rutas sensibles conocidas (solo con autorización)
# ---------------------------------------------------------------------------

RUTAS_ACTIVAS = [
    ("/.git/HEAD", "git-expuesto", lambda c, t: t.startswith("ref: refs/") or re.fullmatch(r"[0-9a-f]{40}\s*", t) is not None),
    ("/.git/config", "git-expuesto", lambda c, t: "[core]" in t and "<html" not in t.lower()),
    ("/.env", "env-expuesto", lambda c, t: len(re.findall(r"(?m)^[A-Z][A-Z0-9_]{2,}=", t)) >= 2 and "<html" not in t.lower()),
    ("/.env.production", "env-expuesto", lambda c, t: len(re.findall(r"(?m)^[A-Z][A-Z0-9_]{2,}=", t)) >= 2 and "<html" not in t.lower()),
    ("/.svn/entries", "git-expuesto", lambda c, t: re.match(r"\d+\s*\n", t) is not None or "svn:wc" in t),
    ("/.DS_Store", "listado-directorios", lambda c, t: c[:8] == b"\x00\x00\x00\x01Bud1"),
    ("/backup.zip", "copia-expuesta", lambda c, t: c[:4] == b"PK\x03\x04"),
    ("/backup.tar.gz", "copia-expuesta", lambda c, t: c[:2] == b"\x1f\x8b"),
    ("/site.zip", "copia-expuesta", lambda c, t: c[:4] == b"PK\x03\x04"),
    ("/www.zip", "copia-expuesta", lambda c, t: c[:4] == b"PK\x03\x04"),
    ("/db.sql", "copia-expuesta", lambda c, t: re.search(r"CREATE TABLE|INSERT INTO|-- MySQL dump", t, re.I) is not None),
    ("/dump.sql", "copia-expuesta", lambda c, t: re.search(r"CREATE TABLE|INSERT INTO|-- MySQL dump", t, re.I) is not None),
    ("/database.sql", "copia-expuesta", lambda c, t: re.search(r"CREATE TABLE|INSERT INTO|-- MySQL dump", t, re.I) is not None),
    ("/wp-config.php.bak", "config-expuesta", lambda c, t: "DB_PASSWORD" in t),
    ("/wp-config.php~", "config-expuesta", lambda c, t: "DB_PASSWORD" in t),
    ("/wp-config.php.save", "config-expuesta", lambda c, t: "DB_PASSWORD" in t),
    ("/config.php.bak", "config-expuesta", lambda c, t: "<?php" in t),
    ("/phpinfo.php", "info-servidor", lambda c, t: "phpinfo()" in t or "PHP Version" in t and "<table" in t),
    ("/info.php", "info-servidor", lambda c, t: "phpinfo()" in t or "PHP Version" in t and "<table" in t),
    ("/server-status", "info-servidor", lambda c, t: "Apache Server Status" in t),
    ("/actuator/env", "info-servidor", lambda c, t: '"propertySources"' in t),
    ("/elmah.axd", "info-servidor", lambda c, t: "Error Log for" in t),
    ("/wp-json/wp/v2/users", "usuarios-enumerables", lambda c, t: t.lstrip().startswith("[") and '"slug"' in t),
    ("/xmlrpc.php", "xmlrpc", lambda c, t: "XML-RPC server accepts POST requests only" in t),
    ("/wp-login.php", "panel-admin", lambda c, t: 'name="pwd"' in t or "user_login" in t),
    ("/administrator/", "panel-admin", lambda c, t: re.search(r"type=[\"']password", t, re.I) is not None),
    ("/phpmyadmin/", "panel-admin", lambda c, t: "phpMyAdmin" in t),
    ("/admin/", "panel-admin", lambda c, t: re.search(r"type=[\"']password", t, re.I) is not None),
]


def comprobar_activo(informe: InformeSeguridad, base: str, opciones: web.Opciones) -> None:
    peticiones = 0
    origen = urllib.parse.urlsplit(base)
    raiz = f"{origen.scheme}://{origen.netloc}"
    aleatoria, _ = web.obtener(f"{raiz}/aimarkers-{secrets.token_hex(6)}", maximo=200_000, seguir=False)
    peticiones += 1
    huella_404 = (aleatoria.estado, len(aleatoria.cuerpo)) if aleatoria else None
    if aleatoria and RE_ERRORES.search(aleatoria.texto()):
        informe.anadir("error-detallado", aleatoria.url, RE_ERRORES.search(aleatoria.texto()).group(0))
    for i, (ruta, id_, validar) in enumerate(RUTAS_ACTIVAS):
        if callable(opciones.progreso):
            opciones.progreso(aimarkers.t("prog.activo", n=f"{i + 1}/{len(RUTAS_ACTIVAS)}"))
        time.sleep(max(0.2, opciones.retardo))
        p, _ = web.obtener(raiz + ruta, maximo=262_144, timeout=15, seguir=False)
        peticiones += 1
        if not p or p.estado != 200:
            continue
        if huella_404 and huella_404 == (p.estado, len(p.cuerpo)):
            continue  # página «no encontrado» que responde 200
        if validar(p.cuerpo, p.texto()):
            extracto = ruta if not p.es_html and b"\x00" in p.cuerpo[:200] else p.texto()[:120]
            informe.anadir(id_, raiz + ruta, extracto, clave=ruta)
    opciones_resp, _ = web.obtener(raiz + "/", metodo="OPTIONS", maximo=10_000, seguir=False)
    peticiones += 1
    if opciones_resp:
        permitidos = opciones_resp.cabecera("allow") + "," + opciones_resp.cabecera("access-control-allow-methods")
        peligrosos = sorted({m for m in ("TRACE", "PUT", "DELETE", "TRACK") if re.search(rf"\b{m}\b", permitidos, re.I)})
        if peligrosos:
            informe.anadir("metodos-peligrosos", raiz + "/", "Allow: " + permitidos.strip(","))
    falso = "https://aimarkers-cors-check.example"
    cors, _ = web.obtener(base, maximo=50_000, cabeceras={"Origin": falso})
    peticiones += 1
    if cors and cors.cabecera("access-control-allow-origin") == falso and cors.cabecera("access-control-allow-credentials").lower() == "true":
        informe.anadir("cors-reflejado", base, f"Origin: {falso} → ACAO: {falso}; ACAC: true")
    if origen.scheme == "https":
        peticiones += 1
        try:
            contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            contexto.check_hostname = False
            # Solo se negocia el protocolo para saber si acepta TLS antiguo; no se envían datos
            contexto.verify_mode = ssl.CERT_NONE  # nosec B501
            contexto.minimum_version = ssl.TLSVersion.TLSv1
            contexto.maximum_version = ssl.TLSVersion.TLSv1_1
            contexto.set_ciphers("DEFAULT:@SECLEVEL=0")
            with socket.create_connection((origen.hostname, origen.port or 443), timeout=10) as s, \
                    contexto.wrap_socket(s, server_hostname=origen.hostname) as t:
                informe.anadir("tls-antiguo-aceptado", f"{origen.hostname}:443", t.version() or "TLSv1.x")
        except (ssl.SSLError, OSError, ValueError):
            pass
    informe.notas.append(aimarkers.t("seg.peticiones", n=peticiones))


# ---------------------------------------------------------------------------
# Puntos de entrada
# ---------------------------------------------------------------------------


def analizar_web(rastreo: web.Rastreo, opciones: web.Opciones) -> InformeSeguridad:
    informe = InformeSeguridad()
    if callable(opciones.progreso):
        opciones.progreso(aimarkers.t("prog.seguridad"))
    if not rastreo.paginas:
        return informe
    primera = rastreo.paginas[0]
    inicio = rastreo.inicio
    # Transporte
    if primera.url.lower().startswith("http://"):
        informe.anadir("sin-https", primera.url, primera.url)
    else:
        partes = urllib.parse.urlsplit(primera.url)
        http, _ = web.obtener(f"http://{partes.netloc}/", maximo=100_000, timeout=10)
        if http is not None and http.url.lower().startswith("http://") and http.estado < 400:
            informe.anadir("http-sin-redireccion", f"http://{partes.netloc}/", f"HTTP {http.estado}, sin redirección a HTTPS")
        analizar_tls(informe, partes.hostname or "", partes.port or 443)
    if inicio.lower().startswith("https://") and primera.url.lower().startswith("http://"):
        informe.anadir("sin-https", primera.url, f"{inicio} → {primera.url}")
    # Páginas
    for p in rastreo.paginas:
        ubic = p.url
        analizar_cabeceras(informe, p, ubic)
        analizar_cookies(informe, p, ubic)
        if p.es_html:
            analizar_html_seguridad(informe, p.texto(), p.url, ubic)
    for js in rastreo.scripts_propios():
        analizar_js_seguridad(informe, js.texto(), js.url)
    # robots.txt y security.txt
    if rastreo.robots_txt:
        sensibles = re.findall(r"(?im)^\s*Disallow:\s*(\S*(?:admin|backup|bak|private|privado|secret|config|old|test|dev|staging)\S*)",
                               rastreo.robots_txt)
        for ruta in sensibles[:10]:
            informe.anadir("robots-sensible", "/robots.txt", f"Disallow: {ruta}", clave="robots")
    partes = urllib.parse.urlsplit(primera.url)
    st, _ = web.obtener(f"{partes.scheme}://{partes.netloc}/.well-known/security.txt", maximo=50_000, timeout=10)
    if not st or st.estado != 200 or st.es_html or "contact:" not in st.texto().lower():
        informe.anadir("sin-security-txt", "/.well-known/security.txt", "404 / —", clave="st")
    # Modo activo
    if opciones.activo:
        if opciones.autorizado:
            informe.modo = "activo"
            comprobar_activo(informe, primera.url, opciones)
        else:
            informe.notas.append(aimarkers.t("seg.activo_sin_autorizacion"))
    informe.notas.insert(0, aimarkers.t("seg.modo_activo" if informe.modo == "activo" else "seg.modo_pasivo"))
    return informe


# --- Ficheros y código -------------------------------------------------------

REGLAS_CODIGO = [
    # (id, patrón, extensiones o None)
    ("inyeccion-sql", re.compile(r"(?i)(?:execute|executemany|query|exec|raw|cursor\.execute|mysqli_query|->query|prepare)\s*\(\s*"
                                 r"(?:f[\"'](?:SELECT|INSERT|UPDATE|DELETE)[^\"']*\{|\"(?:SELECT|INSERT|UPDATE|DELETE)\b[^\"]*\"\s*(?:\+|\.|%\s*[\w(])|"
                                 r"'(?:SELECT|INSERT|UPDATE|DELETE)\b[^']*'\s*(?:\+|\.|%\s*[\w(])|"
                                 r"\$\"(?:SELECT|INSERT|UPDATE|DELETE)[^\"]*\{)"), None),
    ("inyeccion-sql", re.compile(r"(?i)[\"'](?:SELECT|INSERT|UPDATE|DELETE)\b[^\"'\n]{0,200}\$_(?:GET|POST|REQUEST|COOKIE)\["), {".php"}),
    ("inyeccion-comandos", re.compile(r"subprocess\.(?:run|call|Popen|check_output|check_call)\([^)\n]{0,300}shell\s*=\s*True|"
                                      r"\bos\.(?:system|popen)\s*\(\s*(?:f[\"']|[^\"')]*\+)"), {".py"}),
    ("inyeccion-comandos", re.compile(r"\b(?:shell_exec|system|passthru|exec|popen|proc_open)\s*\(\s*[^)\n]{0,200}\$_(?:GET|POST|REQUEST|COOKIE)"), {".php"}),
    ("inyeccion-comandos", re.compile(r"child_process[^\n]{0,80}\.exec(?:Sync)?\s*\(\s*(?:`[^`]*\$\{|[^)\n]*\+)|\bexecSync\s*\(\s*`[^`]*\$\{"),
     {".js", ".ts", ".mjs", ".cjs"}),
    ("evaluacion-dinamica", re.compile(r"(?<![\w.])(?:eval|exec)\s*\(\s*(?!['\"][^'\"]*['\"]\s*\))(?:request|input|sys\.argv|data|params|body|"
                                       r"req\.|args|user|payload|[a-z_]+\s*\))"), {".py"}),
    ("evaluacion-dinamica", re.compile(r"(?<![\w.])eval\s*\(\s*(?!['\"`][^'\"`]*['\"`]\s*\))|new\s+Function\s*\("), {".js", ".ts", ".mjs", ".cjs", ".html", ".htm"}),
    ("evaluacion-dinamica", re.compile(r"(?i)\b(?:Invoke-Expression|iex)\s+(?:\$|\()"), {".ps1", ".psm1"}),
    ("evaluacion-dinamica", re.compile(r"\beval\s*\(\s*\$"), {".php"}),
    ("deserializacion", re.compile(r"\bpickle\.loads?\s*\(|\bmarshal\.loads?\s*\(|\byaml\.load\s*\((?![^)\n]*Loader\s*=\s*(?:yaml\.)?(?:Safe|C?Safe)Loader)|"
                                   r"\bjsonpickle\.decode\s*\("), {".py"}),
    ("deserializacion", re.compile(r"\bunserialize\s*\(\s*\$_(?:GET|POST|REQUEST|COOKIE)"), {".php"}),
    ("deserializacion", re.compile(r"\bBinaryFormatter\s*\(\)|\bNetDataContractSerializer\b"), {".cs", ".vb"}),
    ("xss-dom", re.compile(r"\.(?:innerHTML|outerHTML)\s*\+?=\s*(?![\"'`][^\"'`$]*[\"'`]\s*;)|document\.write(?:ln)?\s*\(|"
                           r"\.insertAdjacentHTML\s*\(|dangerouslySetInnerHTML"), {".js", ".ts", ".tsx", ".jsx", ".mjs", ".html", ".htm", ".vue", ".svelte"}),
    ("tls-desactivado", re.compile(r"verify\s*=\s*False|ssl\._create_unverified_context|(?<![=!<>])=\s*(?:ssl\.)?CERT_NONE\b|"
                                   r"check_hostname\s*=\s*False|"
                                   r"rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|"
                                   r"ServerCertificateValidationCallback\s*=\s*\{?\s*\$true|SkipCertificateCheck|"
                                   r"CURLOPT_SSL_VERIFYPEER\s*,\s*(?:false|0)|InsecureSkipVerify\s*:\s*true|curl\s+(?:-k|--insecure)\b|"
                                   r"wget\s+--no-check-certificate"), None),
    ("cripto-debil", re.compile(r"(?i)\bhashlib\.(?:md5|sha1)\s*\((?![^)\n]*usedforsecurity\s*=\s*False)|\bmd5\s*\(\s*\$_?(?:pass|pwd|password)|"
                                r"createHash\s*\(\s*['\"](?:md5|sha1)['\"]|\bDES\.new\b|\bARC4\b|\bRC4\b|MODE_ECB|AES/ECB|"
                                r"MD5CryptoServiceProvider|SHA1Managed|Get-FileHash[^\n]{0,60}-Algorithm\s+MD5"), None),
    ("aleatorio-inseguro", re.compile(r"(?i)(?:token|secret|password|passwd|session|nonce|salt|otp|key)\w*\s*=\s*[^\n]{0,60}"
                                      r"(?:Math\.random\(|random\.(?:random|randint|choice|choices)\(|\brand\(|mt_rand\(|Get-Random)"), None),
    ("modo-depuracion", re.compile(r"(?m)^\s*DEBUG\s*=\s*True\b|\.run\([^)\n]{0,100}debug\s*=\s*True|APP_DEBUG\s*=\s*true|"
                                   r"display_errors\s*=\s*On|ini_set\(\s*['\"]display_errors['\"]\s*,\s*['\"]?1|"
                                   r"<compilation[^>]{0,100}debug=\"true\"|customErrors mode=\"Off\""), None),
    ("excepcion-silenciada", re.compile(r"except(?:\s+Exception)?\s*:\s*\n\s*pass\b|catch\s*\([^)]*\)\s*\{\s*\}|catch\s*\{\s*\}|"
                                        r"except\s*:\s*pass"), None),
    ("descarga-ejecutada", re.compile(r"(?i)(?:curl|wget)\s[^\n|]{0,200}\|\s*(?:sudo\s+)?(?:ba|z)?sh\b|"
                                      r"(?:iex|Invoke-Expression)\s*\(?\s*\(?\s*(?:iwr|irm|Invoke-WebRequest|Invoke-RestMethod|"
                                      r"New-Object\s+Net\.WebClient)"), None),
]
EXT_REVISABLES = aimarkers.EXT_CODIGO | aimarkers.EXT_HTML | {".env", ".txt", ".md", ".pem", ".key", ".dockerfile", ".tf",
                                                             ".properties", ".xml", ".config", ".gradle"}


def _linea(texto: str, pos: int) -> tuple[int, str]:
    inicio = texto.rfind("\n", 0, pos) + 1
    fin = texto.find("\n", pos)
    return texto.count("\n", 0, pos) + 1, texto[inicio:fin if fin != -1 else len(texto)].strip()


def analizar_texto_codigo(informe: InformeSeguridad, texto: str, nombre: str, ubic: str) -> None:
    ext = Path(nombre).suffix.lower()
    base = Path(nombre).name.lower()
    # Ficheros por nombre
    if re.fullmatch(r"\.env(?:\.(?!example|sample|template|dist)[\w-]+)?", base) and \
            len(re.findall(r"(?m)^[A-Z][A-Z0-9_]{2,}=\S", texto)) >= 1:
        informe.anadir("env-en-ficheros", ubic, base, clave=ubic)
    if base == "dockerfile" or ext == ".dockerfile":
        for m in re.finditer(r"(?im)^FROM\s+([^\s]+)", texto):
            imagen = m.group(1)
            if imagen.lower() != "scratch" and ("@sha256:" not in imagen) and (":" not in imagen.split("/")[-1] or imagen.endswith(":latest")):
                informe.anadir("imagen-latest", f"{ubic}:{_linea(texto, m.start())[0]}", m.group(0))
        if not re.search(r"(?im)^USER\s+(?!root\b|0\b)\S+", texto):
            informe.anadir("contenedor-root", ubic, "USER —")
    if base in ("requirements.txt", "requirements-dev.txt", "requirements.in") or (base.startswith("requirements") and ext == ".txt"):
        sueltas = [l.strip() for l in texto.splitlines()
                   if l.strip() and not l.strip().startswith(("#", "-", "--")) and "==" not in l and "@" not in l]
        if sueltas:
            informe.anadir("dependencia-sin-fijar", ubic, ", ".join(sueltas[:5]), clave=ubic)
    if base == "package.json":
        try:
            datos = json.loads(texto)
        except ValueError:
            datos = {}
        sueltas = [f"{k}@{v}" for sec in ("dependencies", "devDependencies") for k, v in (datos.get(sec) or {}).items()
                   if isinstance(v, str) and (v.strip() in ("*", "latest", "") or v.startswith(("git", "http")) and "#" not in v)]
        if sueltas:
            informe.anadir("dependencia-sin-fijar", ubic, ", ".join(sueltas[:5]), clave=ubic)
    if "/.github/workflows/" in "/" + ubic.replace("\\", "/") and ext in (".yml", ".yaml"):
        for m in re.finditer(r"(?m)^\s*-?\s*uses:\s*([\w.-]+/[\w./-]+)@([\w.-]+)", texto):
            if not re.fullmatch(r"[0-9a-f]{40}", m.group(2)) and not m.group(1).startswith("./"):
                informe.anadir("accion-sin-fijar", f"{ubic}:{_linea(texto, m.start())[0]}", m.group(0).strip(), clave=m.group(1))
    # Secretos
    for nombre_secreto, patron in SECRETOS:
        m = patron.search(texto)
        if m:
            linea, contenido = _linea(texto, m.start())
            id_ = "clave-privada" if nombre_secreto == "Private key" else "secreto-codigo"
            valor = m.group(0)
            informe.anadir(id_, f"{ubic}:{linea}", f"{nombre_secreto}: {valor[:8]}…", clave=nombre_secreto, detalle=nombre_secreto)
    if ext not in (".md", ".txt", ".html", ".htm"):
        for m in RE_SECRETO_GENERICO.finditer(texto):
            valor = m.group(2)
            if RE_MARCADOR_POSICION.match(valor) or re.fullmatch(r"[\w.]+\(.*|\$\w+|%\w+%|[A-Z_]{8,}", valor) \
                    or "os.environ" in texto[max(0, m.start() - 80):m.start()]:
                continue
            linea, contenido = _linea(texto, m.start())
            informe.anadir("secreto-codigo", f"{ubic}:{linea}", f"{m.group(1)} = {valor[:3]}…", clave="gen")
            break
    # Patrones de código
    for id_, patron, extensiones in REGLAS_CODIGO:
        if extensiones and ext not in extensiones:
            continue
        if extensiones is None and ext in (".md", ".txt"):
            continue
        vistas = 0
        for m in patron.finditer(texto):
            linea, contenido = _linea(texto, m.start())
            if contenido.lstrip().startswith(("#", "//", "*", "--", "<#")) and id_ not in ("modo-depuracion",):
                continue
            informe.anadir(id_, f"{ubic}:{linea}", contenido, clave=id_)
            vistas += 1
            if vistas >= 3:
                break


def analizar_ficheros(rutas: list[Path], raiz: Path) -> InformeSeguridad:
    informe = InformeSeguridad(contexto=Contexto(ficheros=True))
    omitidos = 0
    for ruta in rutas:
        nombre = ruta.name
        ext = ruta.suffix.lower()
        if not (ext in EXT_REVISABLES or nombre.lower() in ("dockerfile", ".env", "package.json", "id_rsa", "id_dsa", "id_ecdsa",
                                                             "id_ed25519") or nombre.startswith(".env")):
            continue
        texto = aimarkers.leer_fichero(ruta)
        if texto is None:
            continue
        if "aimarkers: ignore-file" in texto[:2000]:
            omitidos += 1
            continue
        try:
            ubic = str(ruta.relative_to(raiz)) if ruta != raiz else ruta.name
        except ValueError:
            ubic = ruta.name
        analizar_texto_codigo(informe, texto, nombre, ubic)
        if ext in aimarkers.EXT_HTML:
            analizar_html_seguridad(informe, texto, "", ubic)
    if omitidos:
        informe.notas.append(aimarkers.t("nota.ignorado", u=f"{omitidos} ficheros" if aimarkers.idioma() == "es" else f"{omitidos} files"))
    return informe


# ---------------------------------------------------------------------------
# Informes
# ---------------------------------------------------------------------------

COLOR_RIESGO = {"critico": "\033[1;35m", "alto": "\033[1;31m", "medio": "\033[33m", "bajo": "\033[36m", "ninguno": ""}


def informe_consola(datos: dict, color: bool, max_ev: int = 3) -> list[str]:
    def c(nivel: str, texto: str) -> str:
        return f"{COLOR_RIESGO.get(nivel, '')}{texto}\033[0m" if color and COLOR_RIESGO.get(nivel) else texto

    t = aimarkers.t
    req = datos["requisitos"]
    salida = ["", "-" * 78, f"{t('seg.titulo').upper()}  ({datos['owasp_version']}, {datos['cvss_version']}, MITRE ATT&CK)", "-" * 78,
              f"{t('seg.contexto')}: {datos['contexto']}",
              f"{t('seg.requisitos')}: C {t('req.' + req['CR'])}, I {t('req.' + req['IR'])}, D {t('req.' + req['AR'])}"]
    if datos.get("tls"):
        tls = datos["tls"]
        salida.append(f"TLS: {tls.get('version', '?')} {tls.get('cifrado', '')}" + (f", caduca {tls['caduca']}" if tls.get("caduca") and aimarkers.idioma() == "es"
                                                                                   else f", expires {tls['caduca']}" if tls.get("caduca") else ""))
    sev = datos["por_severidad"]
    salida.append(f"{t('seg.cvss_max')}: {datos['cvss_max']:.1f} ({t('sev.' + datos['severidad_max'])})   "
                  f"{t('seg.hallazgos')}: " + ", ".join(f"{sev[s]} {t('sev.' + s).lower()}" for s in ("critical", "high", "medium", "low", "none")))
    tri = datos["triada"]
    salida.append(f"{t('seg.triada')}: " + "   ".join(
        f"{t('seg.' + k.lower())} {c(tri[k]['nivel'], t('nivel_riesgo.' + tri[k]['nivel']))}" for k in ("C", "I", "D")))
    salida.append("")
    salida.append(t("seg.matriz"))
    etiqueta_p = t("seg.probabilidad")
    salida.append(f"{'':>{len(etiqueta_p) + 3}}" + "".join(f"{i:>5}" for i in range(1, 6)) + f"   ← {t('seg.impacto')}")
    for p in range(5, 0, -1):
        fila = ""
        for i in range(1, 6):
            n = datos["matriz"][p - 1][i - 1]
            celda = f"{n:>5}" if n else f"{'·':>5}"
            fila += c(nivel_riesgo(p * i), celda) if n else celda
        salida.append(f"{etiqueta_p if p == 5 else '':>{len(etiqueta_p)}} {p} " + fila)
    if not datos["hallazgos"]:
        salida += ["", t("seg.sin_hallazgos")]
    for h in datos["hallazgos"]:
        salida.append("")
        cvss = f"CVSS {h['cvss']:.1f} ({t('sev.' + h['severidad'])}, B {h['cvss_base']:.1f})" if h["cvss"] is not None else t("seg.informativo")
        etiqueta = f"[{t('nivel_riesgo.' + h['nivel_riesgo'])} {h['riesgo']}]"
        salida.append(f"  {c(h['nivel_riesgo'], etiqueta)} {h['titulo']} — {cvss}")
        refs = [f"OWASP {h['owasp']}"] + h["cwe"][:2] + [m["id"] for m in h["mitre"]] + h["cve"][:3]
        salida.append(f"      {', '.join(refs)}   CID {h['cid']['C']}/{h['cid']['I']}/{h['cid']['D']}   "
                      f"P{h['probabilidad']}×I{h['impacto']}")
        if h["vector"]:
            salida.append(f"      {h['vector']}")
        for e in h["evidencias"][:max_ev]:
            salida.append(f"      {e['ubicacion']}  {e['extracto']}")
        if h["veces"] > max_ev:
            salida.append("      " + t("ui.mas", n=h["veces"] - max_ev))
        salida.append(f"      {t('seg.recomendacion')}: {h['recomendacion']}")
    if datos["notas"]:
        salida.append("")
        salida += [f"  - {n}" for n in datos["notas"]]
    salida.append("")
    salida.append(t("seg.aviso"))
    return salida


def informe_markdown(datos: dict) -> list[str]:
    t = aimarkers.t
    e = html.escape
    req = datos["requisitos"]
    md = [f"### {t('seg.titulo')}", "",
          f"- **{t('seg.contexto')}:** {e(datos['contexto'])}",
          f"- **{t('seg.requisitos')}:** C {t('req.' + req['CR'])}, I {t('req.' + req['IR'])}, D {t('req.' + req['AR'])}",
          f"- **{t('seg.cvss_max')}:** {datos['cvss_max']:.1f} ({t('sev.' + datos['severidad_max'])})",
          f"- **{t('seg.triada')}:** " + ", ".join(f"{t('seg.' + k.lower())} {t('nivel_riesgo.' + datos['triada'][k]['nivel'])}"
                                                   for k in ("C", "I", "D")), "",
          f"**{t('seg.matriz')}**", "",
          f"| {t('seg.probabilidad')} \\ {t('seg.impacto')} | 1 | 2 | 3 | 4 | 5 |", "| --- | --- | --- | --- | --- | --- |"]
    for p in range(5, 0, -1):
        md.append(f"| {p} | " + " | ".join(str(datos["matriz"][p - 1][i - 1] or "·") for i in range(1, 6)) + " |")
    md.append("")
    if datos["hallazgos"]:
        md += [f"| {t('seg.riesgo')} | {t('seg.hallazgos')} | CVSS | OWASP | CWE | MITRE ATT&CK | CID |",
               "| --- | --- | --- | --- | --- | --- | --- |"]
        for h in datos["hallazgos"]:
            cvss = f"{h['cvss']:.1f} {t('sev.' + h['severidad'])}" if h["cvss"] is not None else t("seg.informativo")
            md.append(f"| {t('nivel_riesgo.' + h['nivel_riesgo'])} ({h['riesgo']}) | {e(h['titulo'])} | {cvss} | {h['owasp']} | "
                      f"{', '.join(h['cwe'])} | {', '.join(m['id'] for m in h['mitre'])} | {h['cid']['C']}/{h['cid']['I']}/{h['cid']['D']} |")
        md.append("")
        for h in datos["hallazgos"]:
            md += [f"#### {e(h['titulo'])}", "", e(h["descripcion"]), ""]
            if h["vector"]:
                md.append(f"- `{h['vector']}`")
            if h["cve"]:
                md.append(f"- {', '.join(h['cve'])}")
            for ev in h["evidencias"][:5]:
                extracto = e(ev["extracto"]).replace("|", "\\|")
                md.append(f"- `{e(ev['ubicacion'])}` {extracto}")
            md += [f"- **{t('seg.recomendacion')}:** {e(h['recomendacion'])}", ""]
    else:
        md += [t("seg.sin_hallazgos"), ""]
    md += [f"_{e(t('seg.aviso'))}_", ""]
    return md


def informe_html(datos: dict) -> str:
    t = aimarkers.t
    e = html.escape
    req = datos["requisitos"]
    celdas = ""
    for p in range(5, 0, -1):
        celdas += f"<tr><th>{p}</th>" + "".join(
            f"<td class='r-{nivel_riesgo(p * i)}'>{datos['matriz'][p - 1][i - 1] or ''}</td>" for i in range(1, 6)) + "</tr>"
    matriz = (f"<table class='matriz'><caption>{e(t('seg.matriz'))}</caption><tr><th></th>"
              + "".join(f"<th>{i}</th>" for i in range(1, 6)) + f"</tr>{celdas}</table>")
    tri = "".join(f"<li><span>{e(t('seg.' + k.lower()))}</span><strong class='t-{datos['triada'][k]['nivel']}'>"
                  f"{e(t('nivel_riesgo.' + datos['triada'][k]['nivel']))}</strong></li>" for k in ("C", "I", "D"))
    filas = ""
    for h in datos["hallazgos"]:
        cvss = f"{h['cvss']:.1f} · {e(t('sev.' + h['severidad']))}" if h["cvss"] is not None else e(t("seg.informativo"))
        refs = (f"<a href='https://owasp.org/Top10/2025/'>OWASP {h['owasp']}</a> "
                + " ".join(f"<a href='https://cwe.mitre.org/data/definitions/{c[4:]}.html'>{c}</a>" for c in h["cwe"])
                + " " + " ".join(f"<a href='https://attack.mitre.org/techniques/{m['id'].replace('.', '/')}/' title='{e(m['nombre'])}'>{m['id']}</a>"
                                 for m in h["mitre"])
                + " " + " ".join(f"<a href='https://www.cve.org/CVERecord?id={c}'>{c}</a>" for c in h["cve"]))
        evid = "".join(f"<li><code>{e(x['ubicacion'])}</code> {e(x['extracto'])}</li>" for x in h["evidencias"][:5])
        vector = f"<p><code>{e(h['vector'])}</code></p>" if h["vector"] else ""
        filas += (f"<tr><td><span class='nivel r-{h['nivel_riesgo']}'>{e(t('nivel_riesgo.' + h['nivel_riesgo']))} {h['riesgo']}</span></td>"
                  f"<td><strong>{e(h['titulo'])}</strong><p>{e(h['descripcion'])}</p><p class='refs'>{refs}</p>{vector}"
                  f"<ul>{evid}</ul><p><em>{e(t('seg.recomendacion'))}:</em> {e(h['recomendacion'])}</p></td>"
                  f"<td class='num'>{cvss}</td><td>{h['cid']['C']}/{h['cid']['I']}/{h['cid']['D']}</td></tr>")
    tabla = (f"<table><thead><tr><th>{e(t('seg.riesgo'))}</th><th>{e(t('seg.hallazgos'))}</th><th>CVSS v4.0</th><th>CID</th></tr></thead>"
             f"<tbody>{filas}</tbody></table>") if filas else f"<p>{e(t('seg.sin_hallazgos'))}</p>"
    return (f"<div class='seguridad'><h3>{e(t('seg.titulo'))}</h3>"
            f"<p class='meta'>{e(t('seg.contexto'))}: {e(datos['contexto'])} — {e(t('seg.requisitos'))}: C {e(t('req.' + req['CR']))}, "
            f"I {e(t('req.' + req['IR']))}, D {e(t('req.' + req['AR']))}</p>"
            f"<p class='meta'>{e(t('seg.cvss_max'))}: <strong>{datos['cvss_max']:.1f}</strong> ({e(t('sev.' + datos['severidad_max']))})</p>"
            f"<div class='seg-resumen'><ul class='triada'>{tri}</ul>{matriz}</div>{tabla}"
            f"<p class='aviso-seg'>{e(t('seg.aviso'))}</p></div>")


CSS_HTML = """
.seguridad { margin-top: 18px; border-top: 1px solid var(--borde); padding-top: 12px }
.seguridad h3 { margin: 0 0 6px } .seg-resumen { display:flex; flex-wrap:wrap; gap:24px; align-items:flex-start; margin:12px 0 }
.triada { list-style:none; padding:0; margin:0; display:grid; gap:6px; min-width:200px }
.triada li { display:flex; justify-content:space-between; gap:16px }
.matriz { width:auto; border-collapse:separate; border-spacing:3px } .matriz td, .matriz th { width:34px; height:28px; text-align:center; border:0; padding:0 }
.matriz caption { text-align:left; color:var(--sub); font-size:13px; padding-bottom:4px }
.r-bajo { background:color-mix(in srgb, var(--deb) 25%, transparent) } .r-medio { background:color-mix(in srgb, var(--med) 35%, transparent) }
.r-alto { background:color-mix(in srgb, var(--fue) 45%, transparent) } .r-critico { background:color-mix(in srgb, var(--exp) 55%, transparent) }
.t-alto, .t-critico { color:var(--exp) } .t-medio { color:var(--med) } .t-bajo { color:var(--deb) }
.refs a { margin-right:6px; font-size:12px } .aviso-seg { color:var(--sub); font-size:13px }
"""
