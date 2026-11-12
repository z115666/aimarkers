// aimarkers · interfaz local. Todo el contenido analizado se pinta con textContent: nunca como HTML.
"use strict";

const TEXTOS = {
  es: {
    "saltar": "Ir al contenido",
    "etiqueta-objetivo": "Ruta o URL que quieres analizar",
    "placeholder": "Ruta de un fichero o carpeta, o una URL",
    "elegir-fichero": "Elegir archivo",
    "elegir-carpeta": "Elegir carpeta",
    "analizar": "Analizar",
    "idioma": "Idioma",
    "tema": "Apariencia",
    "tema-auto": "Apariencia: la del sistema",
    "tema-light": "Apariencia: clara",
    "tema-dark": "Apariencia: oscura",
    "casos": "Casos de esta sesión",
    "casos-vacio": "Cada análisis queda aquí hasta que cierres aimarkers.",
    "titular": "Saca a la luz lo que no se ve",
    "entradilla": "Arrastra aquí ficheros, carpetas o imágenes, o escribe arriba una ruta o una URL. Todo se analiza en este equipo.",
    "cap-codigo-t": "Código y textos",
    "cap-codigo": "Firmas de asistentes, restos de chat, muletillas y plantillas sin rellenar.",
    "cap-imagen-t": "Imágenes",
    "cap-imagen": "Credenciales C2PA, origen IPTC, EXIF y parámetros de Stable Diffusion o ComfyUI.",
    "cap-repo-t": "Repositorios y webs",
    "cap-repo": "Coautorías en commits, ramas de agentes, constructores web y cargas masivas de datos.",
    "progreso-total": "Progreso del análisis",
    "ver-por": "Ver por", "ver-nivel": "Nivel", "ver-ubicacion": "Fichero o página",
    "agrupar": "Agrupar resultados", "agrupar-por": "Agrupar por", "agr-riesgo": "Riesgo", "agr-categoria": "Categoría", "agr-cid": "CID",
    "seg-inventario": "Componentes detectados", "seg-terceros": "Servicios de terceros", "rastreador": "rastrea",
    "sin-owasp": "Fuera de OWASP",
    "tipo-cms": "CMS", "tipo-plugin": "Plugin", "tipo-tema": "Tema", "tipo-libreria": "Librería", "tipo-servidor": "Servidor", "tipo-lenguaje": "Lenguaje",
    "hallazgos-n": "{n} hallazgos", "hallazgos-1": "1 hallazgo", "marcadores-n": "{n} marcadores", "marcadores-1": "1 marcador",
    "tiempo-calculando": "Calculando el tiempo restante…", "tiempo-seg": "Quedan unos {n} s", "tiempo-min": "Quedan unos {n} min",
    "tiempo-casi": "Casi listo", "tiempo-transcurrido": "{t} transcurridos",
    "fase-subida": "Preparar ficheros", "fase-descarga": "Descargar la web", "fase-ia": "Marcadores de IA en las páginas",
    "fase-imagenes": "Metadatos de las imágenes", "fase-ficheros": "Marcadores de IA en los ficheros", "fase-git": "Historial de Git",
    "fase-scripts": "JavaScript del sitio", "fase-seguridad": "Cabeceras, cookies y contenido", "fase-dns": "Correo y DNS",
    "fase-activo": "Rutas sensibles (modo activo)", "fase-codigo": "Seguridad del código",
    "fase-dependencias": "Dependencias vulnerables (OSV.dev)",
    "px-titulo": "Lectura de píxeles", "px-imagen": "Imagen", "px-ruido": "Ruido de sensor", "px-periodico": "Huella periódica",
    "px-tamano": "Tamaño", "i-pixeles": "Píxeles", "px-captura": "Captura y edición",
    "px-ayuda": "Medidas sobre la propia imagen, no sobre sus metadatos. Umbrales conservadores: una foto real casi nunca da positivo, pero muchas imágenes generadas tampoco.",
    "volver-inicio": "Volver al inicio",
    "resumen": "Resumen", "resumen-analisis": "Resumen del análisis", "l-ia": "Marcadores de IA", "en-esta-pagina": "En esta página",
    "repetir": "Repetir análisis", "i-resumen": "Veredicto", "i-ia": "Marcadores de IA", "i-seguridad": "Seguridad",
    "i-categorias": "Categorías", "i-hallazgos": "Hallazgos", "i-componentes": "Componentes", "i-terceros": "Terceros", "i-notas": "Notas",
    "corto-fichero": "Archivo", "corto-carpeta": "Carpeta",
    "cap-seg-t": "Seguridad",
    "cap-seg": "OWASP Top 10, técnicas de MITRE ATT&CK, CVSS v4.0 y matriz de riesgos sobre la triada CID.",
    "analizando": "Analizando",
    "parar": "Detener análisis", "deteniendo": "Deteniendo…",
    "detenido": "Análisis detenido. No se ha guardado nada y los ficheros temporales se han borrado.",
    "subiendo": "Preparando {a} de {b} ficheros",
    "explicita": "El propio contenido declara una herramienta de IA.",
    "sin-hallazgos": "No hay marcadores. Recuerda que su ausencia no demuestra autoría humana.",
    "exportar": "Guardar el informe",
    "aviso": "Los marcadores son indicios, no pruebas. Revisa cada evidencia antes de sacar conclusiones.",
    "soltar": "Suelta para analizar",
    "notas": "Notas ({n})",
    "veces-1": "1 vez",
    "veces-n": "{n} veces",
    "pts-nivel": "{n} puntos por marcador",
    "ficheros-1": "1 fichero analizado",
    "ficheros-n": "{n} ficheros analizados",
    "espectro": "Puntuación {n} de 100: {v}",
    "falta-objetivo": "Escribe una ruta o una URL, o arrastra ficheros a la ventana.",
    "error-red": "aimarkers no responde. Comprueba que sigue abierto en la terminal.",
    "error-token": "Esta pestaña no tiene permiso. Abre la dirección que muestra la terminal.",
    "error-tamano": "Hay demasiados datos: el límite es 50 MB por fichero y 500 MB en total.",
    "error-general": "No se ha podido completar el análisis ({e}).",
    "sin-seleccion": "No se ha elegido nada.",
    "guardado": "Informe {f} guardado en Descargas.",
    "c2pa-si": "<strong>Firmas C2PA:</strong> se verifican con c2patool.",
    "c2pa-no": "<strong>Firmas C2PA:</strong> sin verificar. Instala c2patool para comprobarlas.",
    "px-si": "<strong>Lectura de píxeles:</strong> activa.",
    "px-no": "<strong>Lectura de píxeles:</strong> instala Pillow y NumPy para activarla.",
    "atajo": "Atajo: {k}",
    "varios": "{n} ficheros sueltos",
    "opciones": "Opciones",
    "op-que": "Qué analizar",
    "op-ia": "Marcadores de IA",
    "op-seguridad": "Seguridad (OWASP, MITRE, CVSS)",
    "op-consultas": "Consultar bases públicas (DNS y OSV.dev)",
    "op-confiar": "Confiar en el certificado de esta web",
    "op-confiar-ayuda": "Para webs internas con certificado propio. Solo afecta a la web analizada y queda registrado como hallazgo.",
    "op-consultas-ayuda": "Solo se envían el dominio y el nombre y la versión de cada dependencia, nunca tu código.",
    "imagenes-web": "Imágenes de las webs",
    "op-webs": "Webs",
    "op-rastrear": "Rastrear todo el sitio",
    "op-max-paginas": "Máximo de páginas",
    "op-rastrear-ayuda": "Se descarga a una carpeta temporal que se borra al terminar. Respeta robots.txt; −1 sin límite.",
    "op-activo-t": "Modo activo",
    "op-activo": "Comprobar rutas sensibles (.git, .env, copias…)",
    "op-autorizado": "Confirmo que tengo autorización del responsable de esta web para analizarla.",
    "op-activo-ayuda": "Sin permiso puede ser delito (art. 197 bis del Código Penal). No se envían ataques: solo peticiones a rutas conocidas.",
    "falta-autorizacion": "Para el modo activo, confirma en Opciones que tienes autorización sobre la web.",
    "falta-analisis": "Activa en Opciones al menos los marcadores de IA o la seguridad.",
    "seg-titulo": "Seguridad",
    "seg-cvss-max": "CVSS v4.0 máximo",
    "seg-matriz": "Matriz de riesgos",
    "seg-ejes": "Filas: probabilidad. Columnas: impacto.",
    "seg-sin": "No se han encontrado fallos con las comprobaciones realizadas.",
    "seg-aviso": "Evaluación automática y no intrusiva: no sustituye a una auditoría ni a una prueba de intrusión. El CVSS parte de vectores tipo para cada hallazgo y del contexto detectado.",
    "seg-contexto": "Contexto: {c}. Requisitos de entorno: confidencialidad {cr}, integridad {ir}, disponibilidad {ar}.",
    "seg-veredicto": "Riesgo de seguridad {n}",
    "seg-veredicto-nada": "Sin fallos de seguridad detectados",
    "seg-recomendacion": "Recomendación",
    "seg-riesgo": "riesgo {n}",
    "seg-celda": "Probabilidad {p}, impacto {i}: {n} hallazgos",
    "seg-informativo": "informativo",
    "seg-cid": "Afecta a: {d}",
    "seg-probabilidad-impacto": "Probabilidad {p} de 5, impacto {i} de 5.",
    "req-H": "alta", "req-M": "media", "req-L": "baja",
    "dim-C": "Confidencialidad", "dim-I": "Integridad", "dim-D": "Disponibilidad",
    "riesgo-critico": "Crítico", "riesgo-alto": "Alto", "riesgo-medio": "Medio", "riesgo-bajo": "Bajo", "riesgo-ninguno": "Ninguno",
    "sev-critical": "Crítica", "sev-high": "Alta", "sev-medium": "Media", "sev-low": "Baja", "sev-none": "Ninguna",
  },
  en: {
    "saltar": "Skip to content",
    "etiqueta-objetivo": "Path or URL to analyse",
    "placeholder": "Path to a file or folder, or a URL",
    "elegir-fichero": "Choose file",
    "elegir-carpeta": "Choose folder",
    "analizar": "Analyse",
    "idioma": "Language",
    "tema": "Appearance",
    "tema-auto": "Appearance: system",
    "tema-light": "Appearance: light",
    "tema-dark": "Appearance: dark",
    "casos": "Cases this session",
    "casos-vacio": "Each analysis stays here until you close aimarkers.",
    "titular": "Bring hidden traces to light",
    "entradilla": "Drop files, folders or images here, or type a path or URL above. Everything is analysed on this computer.",
    "cap-codigo-t": "Code and text",
    "cap-codigo": "Assistant signatures, chat leftovers, stock phrases and unfilled templates.",
    "cap-imagen-t": "Images",
    "cap-imagen": "C2PA Content Credentials, IPTC source, EXIF and Stable Diffusion or ComfyUI parameters.",
    "cap-repo-t": "Repositories and websites",
    "cap-repo": "Commit co-authors, agent branches, website builders and bulk data loads.",
    "progreso-total": "Analysis progress",
    "ver-por": "View by", "ver-nivel": "Level", "ver-ubicacion": "File or page",
    "agrupar": "Group results", "agrupar-por": "Group by", "agr-riesgo": "Risk", "agr-categoria": "Category", "agr-cid": "CIA",
    "seg-inventario": "Detected components", "seg-terceros": "Third-party services", "rastreador": "tracks",
    "sin-owasp": "Outside OWASP",
    "tipo-cms": "CMS", "tipo-plugin": "Plugin", "tipo-tema": "Theme", "tipo-libreria": "Library", "tipo-servidor": "Server", "tipo-lenguaje": "Language",
    "hallazgos-n": "{n} findings", "hallazgos-1": "1 finding", "marcadores-n": "{n} markers", "marcadores-1": "1 marker",
    "tiempo-calculando": "Estimating time left…", "tiempo-seg": "About {n} s left", "tiempo-min": "About {n} min left",
    "tiempo-casi": "Almost done", "tiempo-transcurrido": "{t} elapsed",
    "fase-subida": "Prepare files", "fase-descarga": "Download the website", "fase-ia": "AI markers in pages",
    "fase-imagenes": "Image metadata", "fase-ficheros": "AI markers in files", "fase-git": "Git history",
    "fase-scripts": "Site JavaScript", "fase-seguridad": "Headers, cookies and content", "fase-dns": "Email and DNS",
    "fase-activo": "Sensitive paths (active mode)", "fase-codigo": "Code security",
    "fase-dependencias": "Vulnerable dependencies (OSV.dev)",
    "px-titulo": "Pixel reading", "px-imagen": "Image", "px-ruido": "Sensor noise", "px-periodico": "Periodic trace",
    "px-tamano": "Size", "i-pixeles": "Pixels", "px-captura": "Screenshot and editing",
    "px-ayuda": "Measurements on the image itself, not its metadata. Conservative thresholds: a real photo almost never triggers them, but many generated images do not either.",
    "volver-inicio": "Back to start",
    "resumen": "Summary", "resumen-analisis": "Analysis summary", "l-ia": "AI markers", "en-esta-pagina": "On this page",
    "repetir": "Run again", "i-resumen": "Verdict", "i-ia": "AI markers", "i-seguridad": "Security",
    "i-categorias": "Categories", "i-hallazgos": "Findings", "i-componentes": "Components", "i-terceros": "Third parties", "i-notas": "Notes",
    "corto-fichero": "File", "corto-carpeta": "Folder",
    "cap-seg-t": "Security",
    "cap-seg": "OWASP Top 10, MITRE ATT&CK techniques, CVSS v4.0 and a risk matrix over the CIA triad.",
    "analizando": "Analysing",
    "parar": "Stop analysis", "deteniendo": "Stopping…",
    "detenido": "Analysis stopped. Nothing was saved and temporary files were deleted.",
    "subiendo": "Preparing {a} of {b} files",
    "explicita": "The content itself declares an AI tool.",
    "sin-hallazgos": "No markers found. Remember that their absence does not prove human authorship.",
    "exportar": "Save the report",
    "aviso": "Markers are signs, not proof. Review every piece of evidence before drawing conclusions.",
    "soltar": "Drop to analyse",
    "notas": "Notes ({n})",
    "veces-1": "once",
    "veces-n": "{n} times",
    "pts-nivel": "{n} points per marker",
    "ficheros-1": "1 file analysed",
    "ficheros-n": "{n} files analysed",
    "espectro": "Score {n} out of 100: {v}",
    "falta-objetivo": "Type a path or URL, or drop files onto the window.",
    "error-red": "aimarkers is not responding. Check that it is still running in the terminal.",
    "error-token": "This tab is not authorised. Open the address shown in the terminal.",
    "error-tamano": "Too much data: the limit is 50 MB per file and 500 MB in total.",
    "error-general": "The analysis could not be completed ({e}).",
    "sin-seleccion": "Nothing was chosen.",
    "guardado": "{f} report saved to Downloads.",
    "c2pa-si": "<strong>C2PA signatures:</strong> verified with c2patool.",
    "c2pa-no": "<strong>C2PA signatures:</strong> not verified. Install c2patool to check them.",
    "px-si": "<strong>Pixel reading:</strong> on.",
    "px-no": "<strong>Pixel reading:</strong> install Pillow and NumPy to turn it on.",
    "atajo": "Shortcut: {k}",
    "varios": "{n} separate files",
    "opciones": "Options",
    "op-que": "What to analyse",
    "op-ia": "AI markers",
    "op-seguridad": "Security (OWASP, MITRE, CVSS)",
    "op-consultas": "Query public databases (DNS and OSV.dev)",
    "op-confiar": "Trust this website's certificate",
    "op-confiar-ayuda": "For internal sites with their own certificate. It only affects the analysed site and is recorded as a finding.",
    "op-consultas-ayuda": "Only the domain and each dependency's name and version are sent, never your code.",
    "imagenes-web": "Website images",
    "op-webs": "Websites",
    "op-rastrear": "Crawl the whole site",
    "op-max-paginas": "Maximum pages",
    "op-rastrear-ayuda": "Downloaded to a temporary folder that is deleted afterwards. Respects robots.txt; −1 for no limit.",
    "op-activo-t": "Active mode",
    "op-activo": "Check sensitive paths (.git, .env, backups…)",
    "op-autorizado": "I confirm I have permission from the owner of this website to test it.",
    "op-activo-ayuda": "Without permission this may be a crime. No attacks are sent: only requests to well-known paths.",
    "falta-autorizacion": "For active mode, confirm in Options that you are authorised to test the website.",
    "falta-analisis": "Turn on AI markers or security in Options.",
    "seg-titulo": "Security",
    "seg-cvss-max": "Highest CVSS v4.0",
    "seg-matriz": "Risk matrix",
    "seg-ejes": "Rows: likelihood. Columns: impact.",
    "seg-sin": "No issues found with the checks performed.",
    "seg-aviso": "Automated, non-intrusive assessment: it does not replace an audit or a penetration test. CVSS starts from typical vectors for each finding and the detected context.",
    "seg-contexto": "Context: {c}. Environmental requirements: confidentiality {cr}, integrity {ir}, availability {ar}.",
    "seg-veredicto": "{n} security risk",
    "seg-veredicto-nada": "No security issues detected",
    "seg-recomendacion": "Recommendation",
    "seg-riesgo": "risk {n}",
    "seg-celda": "Likelihood {p}, impact {i}: {n} findings",
    "seg-informativo": "informational",
    "seg-cid": "Affects: {d}",
    "seg-probabilidad-impacto": "Likelihood {p} of 5, impact {i} of 5.",
    "req-H": "high", "req-M": "medium", "req-L": "low",
    "dim-C": "Confidentiality", "dim-I": "Integrity", "dim-D": "Availability",
    "riesgo-critico": "Critical", "riesgo-alto": "High", "riesgo-medio": "Medium", "riesgo-bajo": "Low", "riesgo-ninguno": "None",
    "sev-critical": "Critical", "sev-high": "High", "sev-medium": "Medium", "sev-low": "Low", "sev-none": "None",
  },
};

const $ = (id) => document.getElementById(id);
const estado = { idioma: "es", tema: "auto", token: "", config: null, casos: [], actual: null, ocupado: false, parando: false, subida: null };

function guardar(clave, valor) { try { localStorage.setItem("aimarkers." + clave, valor); } catch (_) { /* sin almacenamiento */ } }
function leer(clave) { try { return localStorage.getItem("aimarkers." + clave); } catch (_) { return null; } }

function t(clave, valores = {}) {
  const texto = (TEXTOS[estado.idioma] || TEXTOS.en)[clave] || clave;
  return texto.replace(/\{(\w+)\}/g, (_, k) => String(valores[k] ?? ""));
}

function el(etiqueta, clase, texto) {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  if (texto !== undefined) nodo.textContent = texto;
  return nodo;
}

// Pone un texto propio (nunca contenido analizado) que contiene <strong>
function textoConNegrita(nodo, texto) {
  nodo.replaceChildren();
  const m = /^<strong>(.*?)<\/strong>\s*(.*)$/.exec(texto);
  if (!m) { nodo.textContent = texto; return; }
  nodo.append(el("strong", null, m[1]), " " + m[2]);
}

// ---------- Token y API ----------
function iniciarToken() {
  const m = /(?:^|[#&])t=([A-Za-z0-9_-]{20,})/.exec(location.hash);
  if (m) {
    estado.token = m[1];
    try { sessionStorage.setItem("aimarkers.token", m[1]); } catch (_) { /* nada */ }
    history.replaceState(null, "", location.pathname);
  } else {
    try { estado.token = sessionStorage.getItem("aimarkers.token") || ""; } catch (_) { estado.token = ""; }
  }
}

class ErrorApi extends Error {
  constructor(estadoHttp, codigo) { super(codigo); this.estadoHttp = estadoHttp; }
}

async function api(ruta, cuerpo, opciones = {}) {
  let respuesta;
  try {
    respuesta = await fetch(ruta, {
      method: cuerpo === undefined ? "GET" : "POST",
      headers: { "X-Aimarkers-Token": estado.token, ...(opciones.tipo ? { "Content-Type": opciones.tipo } : { "Content-Type": "application/json" }) },
      body: cuerpo === undefined ? undefined : (opciones.crudo ? cuerpo : JSON.stringify(cuerpo)),
      cache: "no-store",
      signal: opciones.senal,
    });
  } catch (e) {
    if (e && e.name === "AbortError") throw new ErrorApi(409, "cancelled");
    throw new ErrorApi(0, "red");
  }
  if (!respuesta.ok) {
    let codigo = String(respuesta.status);
    try { codigo = (await respuesta.json()).error || codigo; } catch (_) { /* cuerpo no JSON */ }
    throw new ErrorApi(respuesta.status, codigo);
  }
  return opciones.blob ? respuesta.blob() : respuesta.json();
}

function mensajeError(e) {
  if (e instanceof ErrorApi) {
    if (e.estadoHttp === 0) return t("error-red");
    if (e.estadoHttp === 403) return t("error-token");
    if (e.estadoHttp === 413) return t("error-tamano");
    return t("error-general", { e: e.message });
  }
  return t("error-general", { e: String(e && e.message || e) });
}

// ---------- Aviso flotante ----------
let temporizadorAviso = 0;
function avisar(texto, error = false) {
  const nodo = $("toast");
  nodo.textContent = texto;
  nodo.classList.toggle("error", error);
  nodo.classList.add("visible");
  clearTimeout(temporizadorAviso);
  temporizadorAviso = setTimeout(() => nodo.classList.remove("visible"), error ? 6000 : 3200);
}

// ---------- Idioma y tema ----------
function aplicarIdioma() {
  document.documentElement.lang = estado.idioma;
  document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((n) => { n.placeholder = t(n.dataset.i18nPlaceholder); });
  document.querySelectorAll("[data-i18n-aria]").forEach((n) => { n.setAttribute("aria-label", t(n.dataset.i18nAria)); });
  document.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === estado.idioma)));
  const atajo = navigator.platform.toLowerCase().includes("mac") ? "⌘K" : "Ctrl+K";
  $("objetivo").title = t("atajo", { k: atajo });
  aplicarTema();
  pintarEstadoC2pa();
}

function aplicarTema() {
  const raiz = document.documentElement;
  if (estado.tema === "auto") raiz.removeAttribute("data-theme"); else raiz.dataset.theme = estado.tema;
  $("tema-uso").setAttribute("href", "/icon.svg#" + { auto: "auto", light: "sol", dark: "luna" }[estado.tema]);
  $("tema").setAttribute("aria-label", t("tema-" + estado.tema));
  $("tema").title = t("tema-" + estado.tema);
}

function pintarEstadoC2pa() {
  if (!estado.config) return;
  textoConNegrita($("estado-c2pa"), t(estado.config.c2patool ? "c2pa-si" : "c2pa-no"));
  textoConNegrita($("estado-pixeles"), t(estado.config.pixeles ? "px-si" : "px-no"));
}


// ---------- Ilustración: una hoja con marcas ocultas que la lupa UV hace visibles ----------
const SVGNS = "http://www.w3.org/2000/svg";
const LINEAS = [220, 180, 250, 140, 230, 200, 120, 240, 170, 210, 150];
const MARCAS = { 1: ["explicito", "Co-Authored-By: Claude"], 4: ["fuerte", "utm_source=chatgpt"],
  7: ["medio", "c2pa: trainedAlgorithmic"], 9: ["debil", "CVSS:4.0/AV:N/AC:L"] };
const ilu = { x: 200, y: 170, objetivo: null, modo: "deriva", activo: false, t: 0, ultimo: 0 };

function svg(etiqueta, atributos, padre) {
  const nodo = document.createElementNS(SVGNS, etiqueta);
  for (const [k, v] of Object.entries(atributos)) nodo.setAttribute(k, v);
  if (padre) padre.append(nodo);
  return nodo;
}

function construirIlustracion() {
  const lineas = $("ilu-lineas");
  const revelado = $("ilu-revelado");
  if (!lineas || lineas.childElementCount) return;
  LINEAS.forEach((ancho, i) => {
    const y = 124 + i * 24;
    const x = 64 + (i % 4 === 2 ? 24 : 0);
    svg("rect", { x, y, width: ancho, height: 8, rx: 4, class: "ilu-linea" }, lineas);
    const marca = MARCAS[i];
    if (!marca) return;
    // Bajo la luz, la línea normal se tapa y aparece la marca fluorescente
    svg("rect", { x: x - 4, y: y - 6, width: ancho + 8, height: 20, class: "ilu-tapa" }, revelado);
    const texto = svg("text", { x, y: y + 8, class: "ilu-marca " + marca[0] }, revelado);
    texto.textContent = marca[1];
    svg("rect", { x, y: y + 12, width: Math.min(ancho, marca[1].length * 7.4), height: 2, rx: 1,
      class: "ilu-subrayado " + marca[0], filter: "url(#ilu-brillo)" }, revelado);
  });
  // Credencial C2PA en la imagen del fondo
  const insignia = svg("g", { class: "ilu-insignia", transform: "rotate(-7 410 115)" }, revelado);
  svg("rect", { x: 318, y: 54, width: 46, height: 20, rx: 6, filter: "url(#ilu-brillo)" }, insignia);
  svg("text", { x: 327, y: 68 }, insignia).textContent = "C2PA";

  const lienzo = $("ilustracion");
  const punto = (ev) => {
    const ctm = lienzo.getScreenCTM();
    if (!ctm) return null;
    const p = new DOMPoint(ev.clientX, ev.clientY).matrixTransform(ctm.inverse());
    return { x: Math.max(60, Math.min(500, p.x)), y: Math.max(80, Math.min(390, p.y)) };
  };
  lienzo.addEventListener("pointermove", (ev) => { if (ev.pointerType === "mouse") ilu.objetivo = punto(ev); });
  lienzo.addEventListener("pointerleave", () => { ilu.objetivo = null; });
  colocarLupa(200, 150);
}

function colocarLupa(x, y) {
  ilu.x = x; ilu.y = y;
  $("ilu-circulo").setAttribute("cx", x.toFixed(1));
  $("ilu-circulo").setAttribute("cy", y.toFixed(1));
  $("ilu-luz-circulo").setAttribute("cx", x.toFixed(1));
  $("ilu-luz-circulo").setAttribute("cy", y.toFixed(1));
  $("ilu-lupa").setAttribute("transform", `translate(${x.toFixed(1)} ${y.toFixed(1)})`);
}

function pasoIlustracion(ahora) {
  if (!ilu.activo) return;
  const lienzo = $("ilustracion");
  if (!lienzo || !lienzo.isConnected || lienzo.getBoundingClientRect().width === 0 || document.hidden) {
    ilu.activo = false;
    return;
  }
  const dt = Math.min(64, ahora - (ilu.ultimo || ahora)) / 1000;
  ilu.ultimo = ahora;
  ilu.t += dt * (ilu.modo === "escaneo" ? 2.6 : 1);
  let destino;
  if (ilu.objetivo) destino = ilu.objetivo;
  else if (ilu.modo === "escaneo") destino = { x: 205 + 115 * Math.sin(ilu.t * 1.3), y: 140 + ((ilu.t * 38) % 250) };
  else destino = { x: 210 + 120 * Math.sin(ilu.t * 0.33), y: 230 + 105 * Math.sin(ilu.t * 0.47 + 1) };
  const suavizado = ilu.objetivo ? 0.18 : 0.06;
  colocarLupa(ilu.x + (destino.x - ilu.x) * suavizado, ilu.y + (destino.y - ilu.y) * suavizado);
  requestAnimationFrame(pasoIlustracion);
}

function animarIlustracion(modo) {
  ilu.modo = modo;
  if (reducirMovimiento.matches) { colocarLupa(150, 150); return; }
  if (!ilu.activo) { ilu.activo = true; ilu.ultimo = 0; requestAnimationFrame(pasoIlustracion); }
}

function moverIlustracion(destino, modo) {
  const lienzo = $("ilustracion");
  if (!lienzo) return;
  $(destino).append(lienzo);
  animarIlustracion(modo);
}

// ---------- Vistas ----------
function mostrar(vista) {
  for (const nombre of ["inicio", "analizando", "resultado"]) $("vista-" + nombre).hidden = nombre !== vista;
  if (vista === "analizando") moverIlustracion("destino-analizando", "escaneo");
  else moverIlustracion("destino-inicio", "deriva");
}

const reducirMovimiento = matchMedia("(prefers-reduced-motion: reduce)");
// El veredicto se revela como una huella bajo la lámpara: de muy degradado a nítido
function revelar(nodo) {
  const pasos = ["f100", "f50", "f20"];
  nodo.classList.remove(...pasos);
  if (reducirMovimiento.matches) return;
  let i = 0;
  nodo.classList.add(pasos[0]);
  const avanzar = () => {
    nodo.classList.remove(pasos[i]);
    i += 1;
    if (i < pasos.length) { nodo.classList.add(pasos[i]); setTimeout(avanzar, 140); }
  };
  setTimeout(avanzar, 260);
}


// Frases sencillas de lo que se está comprobando en cada fase
const FRASES = {
  es: {
    subida: ["Preparando los ficheros para el análisis", "Copiándolos a una carpeta temporal que se borrará al terminar"],
    descarga: ["Descargando la página", "Siguiendo los enlaces del mismo sitio", "Respetando robots.txt", "Guardando una copia temporal de cada página"],
    ia: ["Buscando firmas de asistentes de IA", "Comprobando restos de conversación con el chat", "Midiendo muletillas típicas de los modelos",
      "Buscando huellas de constructores web con IA", "Revisando ráfagas de datos cargados automáticamente"],
    imagenes: ["Leyendo credenciales de contenido C2PA", "Revisando metadatos EXIF y XMP", "Buscando parámetros de Stable Diffusion o ComfyUI",
      "Comprobando el origen digital declarado (IPTC)"],
    ficheros: ["Buscando firmas de asistentes en el código", "Comprobando ficheros de instrucciones para agentes", "Revisando comentarios y plantillas sin rellenar",
      "Leyendo metadatos de las imágenes"],
    git: ["Revisando el historial de commits", "Buscando coautorías de IA", "Comprobando ramas de agentes"],
    scripts: ["Descargando el JavaScript del sitio", "Identificando versiones de librerías", "Buscando claves expuestas en el código del cliente"],
    seguridad: ["Comprobando las cabeceras de seguridad", "Revisando las cookies de sesión", "Verificando el certificado TLS",
      "Buscando contenido cargado sin cifrar", "Revisando formularios y protección CSRF", "Calculando CVSS v4.0 y la matriz de riesgos"],
    dns: ["Consultando SPF del dominio", "Comprobando la política DMARC", "Verificando DNSSEC y CAA"],
    activo: ["Probando rutas sensibles conocidas", "Buscando copias de seguridad expuestas", "Comprobando métodos HTTP permitidos"],
    codigo: ["Buscando secretos en el código", "Revisando patrones de inyección", "Comprobando dependencias y acciones sin fijar",
      "Buscando criptografía débil"],
    dependencias: ["Leyendo los ficheros de bloqueo", "Consultando avisos en OSV.dev", "Buscando la versión que corrige cada fallo"],
  },
  en: {
    subida: ["Preparing files for analysis", "Copying them to a temporary folder deleted afterwards"],
    descarga: ["Downloading the page", "Following links on the same site", "Respecting robots.txt", "Keeping a temporary copy of each page"],
    ia: ["Looking for AI assistant signatures", "Checking for chat leftovers", "Measuring typical model stock phrases",
      "Looking for AI website builder fingerprints", "Checking for bursts of automatically loaded data"],
    imagenes: ["Reading C2PA Content Credentials", "Checking EXIF and XMP metadata", "Looking for Stable Diffusion or ComfyUI parameters",
      "Checking the declared digital source (IPTC)"],
    ficheros: ["Looking for assistant signatures in code", "Checking agent instruction files", "Reviewing comments and unfilled templates",
      "Reading image metadata"],
    git: ["Reviewing commit history", "Looking for AI co-authors", "Checking agent branches"],
    scripts: ["Downloading the site's JavaScript", "Identifying library versions", "Looking for keys exposed in client code"],
    seguridad: ["Checking security headers", "Reviewing session cookies", "Verifying the TLS certificate", "Looking for unencrypted content",
      "Reviewing forms and CSRF protection", "Computing CVSS v4.0 and the risk matrix"],
    dns: ["Querying the domain's SPF", "Checking the DMARC policy", "Verifying DNSSEC and CAA"],
    activo: ["Trying well-known sensitive paths", "Looking for exposed backups", "Checking allowed HTTP methods"],
    codigo: ["Looking for secrets in code", "Reviewing injection patterns", "Checking unpinned dependencies and actions", "Looking for weak cryptography"],
    dependencias: ["Reading lock files", "Querying advisories on OSV.dev", "Finding the version that fixes each issue"],
  },
};

const carga = { mostrado: 0, objetivo: 0, muestras: [], eta: null, inicio: 0, fase: "", plan: [], frase: 0, totales: {} };
let temporizadorFrase = 0;
let temporizadorCifra = 0;

function reiniciarCarga(plan = []) {
  Object.assign(carga, { mostrado: 0, objetivo: 0, muestras: [], eta: null, inicio: performance.now(), fase: "", plan, frase: 0, totales: {} });
  $("carga-porcentaje").textContent = "0";
  $("carga-relleno").style.width = "0%";
  $("carga-barra").setAttribute("aria-valuenow", "0");
  $("carga-tiempo").textContent = t("tiempo-calculando");
  $("progreso").textContent = "";
  pintarPasos();
}

function pintarPasos() {
  const lista = $("carga-pasos");
  lista.replaceChildren();
  const actual = carga.plan.indexOf(carga.fase);
  carga.plan.forEach((fase, i) => {
    const li = el("li");
    li.dataset.estado = i < actual ? "hecho" : i === actual ? "activo" : "pendiente";
    const cuenta = carga.totales[fase];
    li.append(el("span", "marca-paso"), el("span", null, t("fase-" + fase)), el("span", "cuenta-paso", cuenta ? `${cuenta[0]}/${cuenta[1]}` : ""));
    lista.append(li);
  });
}

function rotarFrase(forzar = false) {
  const lista = (FRASES[estado.idioma] || FRASES.en)[carga.fase];
  if (!lista) return;
  if (!forzar) carga.frase = (carga.frase + 1) % lista.length;
  const nodo = $("carga-fase");
  const texto = lista[carga.frase % lista.length];
  if (reducirMovimiento.matches) { nodo.textContent = texto; return; }
  nodo.classList.add("cambiando");
  setTimeout(() => { nodo.textContent = texto; nodo.classList.remove("cambiando"); }, 220);
}

function formatoTiempo(segundos) {
  if (segundos < 60) return `${Math.max(1, Math.round(segundos))} s`;
  return `${Math.floor(segundos / 60)} min ${String(Math.round(segundos % 60)).padStart(2, "0")} s`;
}

function actualizarCarga(dato) {
  if (!dato || !dato.fase) return;
  if (dato.plan && dato.plan.join() !== carga.plan.join()) carga.plan = dato.plan;
  if (dato.total) carga.totales[dato.fase] = [Math.min(dato.hecho, dato.total), dato.total];
  if (dato.fase !== carga.fase) {
    if (carga.fase && carga.totales[carga.fase]) carga.totales[carga.fase][0] = carga.totales[carga.fase][1];
    carga.fase = dato.fase;
    carga.frase = 0;
    rotarFrase(true);
  }
  pintarPasos();
  if (dato.detalle) $("progreso").textContent = dato.detalle;
  carga.objetivo = Math.max(carga.objetivo, Number(dato.porcentaje) || 0);
  // Tiempo restante: velocidad media de los últimos 15 s
  const ahora = performance.now();
  carga.muestras.push([ahora, carga.objetivo]);
  carga.muestras = carga.muestras.filter(([m]) => ahora - m < 15000);
  const [t0, p0] = carga.muestras[0];
  const transcurrido = (ahora - carga.inicio) / 1000;
  let texto = t("tiempo-calculando");
  if (carga.objetivo >= 97) texto = t("tiempo-casi");
  else if (carga.objetivo > 2 && transcurrido > 3 && ahora - t0 > 2000 && carga.objetivo > p0) {
    const restante = (100 - carga.objetivo) / ((carga.objetivo - p0) / ((ahora - t0) / 1000));
    carga.eta = carga.eta === null ? restante : carga.eta * 0.7 + restante * 0.3;
    texto = carga.eta < 60 ? t("tiempo-seg", { n: Math.max(1, Math.round(carga.eta / 5) * 5 || 1) })
      : t("tiempo-min", { n: Math.round(carga.eta / 60) });
  }
  $("carga-tiempo").textContent = `${texto} (${t("tiempo-transcurrido", { t: formatoTiempo(transcurrido) })})`;
}

function animarCifra() {
  clearInterval(temporizadorCifra);
  temporizadorCifra = setInterval(() => {
    if (!estado.ocupado) return;
    const diferencia = carga.objetivo - carga.mostrado;
    carga.mostrado += Math.abs(diferencia) < 0.5 ? diferencia : diferencia * 0.18;
    const valor = Math.floor(carga.mostrado);
    $("carga-porcentaje").textContent = String(valor);
    $("carga-relleno").style.width = carga.mostrado.toFixed(1) + "%";
    $("carga-barra").setAttribute("aria-valuenow", String(valor));
  }, 60);
}

let temporizadorLatido = 0;
function latido(activo) {
  const nodo = $("texto-analizando");
  clearInterval(temporizadorLatido);
  nodo.classList.remove("f100", "f50", "f20");
  if (!activo || reducirMovimiento.matches) return;
  const pasos = ["f100", "f50", "f20", "", "f20", "f50"];
  let i = 0;
  temporizadorLatido = setInterval(() => {
    nodo.classList.remove("f100", "f50", "f20");
    if (pasos[i]) nodo.classList.add(pasos[i]);
    i = (i + 1) % pasos.length;
  }, 180);
}

function ocupado(activo, plan = null) {
  estado.ocupado = activo;
  $("analizar").disabled = activo;
  clearInterval(temporizadorFrase);
  if (activo) {
    estado.parando = false;
    $("parar").disabled = false;
    $("parar-texto").textContent = t("parar");
    if (plan) reiniciarCarga(plan);
    mostrar("analizando");
    latido(true);
    animarCifra();
    temporizadorFrase = setInterval(() => rotarFrase(), 2600);
  } else {
    latido(false);
    clearInterval(temporizadorCifra);
  }
}

// ---------- Resultado ----------
function pintarResultado(caso) {
  const r = caso.resultados[0];
  estado.actual = caso;
  $("r-objetivo").textContent = r.objetivo;
  const veredicto = $("r-veredicto");
  const soloSeg = Boolean(r.solo_seguridad && r.seguridad);
  $("vista-resultado").classList.toggle("solo-seguridad", soloSeg);
  for (const id of ["r-espectro", "r-grupos"]) $(id).hidden = soloSeg;
  if (soloSeg) {
    const peor = peorRiesgo(r.seguridad);
    const frase = peor ? t("seg-veredicto", { n: t("riesgo-" + peor).toLowerCase() }) : t("seg-veredicto-nada");
    veredicto.textContent = frase.charAt(0).toUpperCase() + frase.slice(1);
    veredicto.dataset.banda = { critico: "alta", alto: "alta", medio: "media" }[peor] || "nula";
  } else {
    veredicto.textContent = r.valoracion;
    veredicto.dataset.banda = r.banda;
  }
  const meta = $("r-meta");
  meta.replaceChildren(el("span", null, r.tipo_nombre),
    el("span", null, t(r.ficheros_analizados === 1 ? "ficheros-1" : "ficheros-n", { n: r.ficheros_analizados })));

  $("r-espectro").dataset.banda = r.banda;
  $("r-puntos").textContent = r.banda === "indeterminada" ? "?" : String(r.puntuacion);
  $("r-espectro-texto").textContent = t("espectro", { n: r.puntuacion, v: r.valoracion });
  const marca = $("r-marca");
  marca.style.left = "0%";
  requestAnimationFrame(() => requestAnimationFrame(() => { marca.style.left = r.puntuacion + "%"; }));

  $("r-explicita").hidden = soloSeg || !r.atribucion_explicita;

  const grupos = $("r-grupos");
  grupos.replaceChildren();
  for (const g of r.grupos) {
    const seccion = el("section", "grupo");
    seccion.dataset.nivel = g.nivel;
    const titulo = el("h2");
    titulo.append(el("span", "punto"), el("span", null, g.nombre), el("small", null, t("pts-nivel", { n: g.peso })));
    const lista = el("ul");
    for (const m of g.marcadores) {
      const item = el("li");
      const detalle = el("details", "marcador");
      const resumen = el("summary");
      resumen.append(el("span", "marcador-desc", m.descripcion),
        el("span", "marcador-veces", t(m.veces === 1 ? "veces-1" : "veces-n", { n: m.veces })),
        el("span", "marcador-puntos", "+" + m.puntos.toLocaleString(estado.idioma)));
      const evidencias = el("ul", "evidencias");
      for (const e of m.evidencias) {
        const fila = el("li", "evidencia");
        fila.append(el("code", null, e.ubicacion), el("span", null, e.extracto));
        evidencias.append(fila);
      }
      detalle.append(resumen, evidencias);
      if (g.nivel === "explicito") detalle.open = true;
      item.append(detalle);
      lista.append(item);
    }
    seccion.append(titulo, lista);
    grupos.append(seccion);
  }
  $("r-vacio").hidden = soloSeg || r.grupos.length > 0;
  const variasUbicaciones = (r.por_ubicacion || []).length > 1;
  $("r-segmentos").hidden = soloSeg || !variasUbicaciones;
  pintarUbicaciones(r);
  cambiarVistaIa(variasUbicaciones ? (estado.vistaIa || "nivel") : "nivel");
  pintarSeguridad(r.seguridad);
  pintarPixeles(r);
  pintarLateral(r);

  const notas = $("r-notas");
  notas.replaceChildren(...r.notas.map((n) => el("li", null, n)));
  $("r-notas-bloque").hidden = r.notas.length === 0;
  $("r-notas-bloque").open = r.grupos.length === 0;
  $("r-notas-titulo").textContent = t("notas", { n: r.notas.length });

  mostrar("resultado");
  revelar(veredicto);
  pintarCasos();
  $("banco").focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: reducirMovimiento.matches ? "auto" : "smooth" });
}

const ORDEN_RIESGO = ["critico", "alto", "medio", "bajo"];
function peorRiesgo(seg) {
  return ORDEN_RIESGO.find((n) => seg.hallazgos.some((h) => h.nivel_riesgo === n && !h.informativo)) || "";
}

function enlace(texto, url, titulo) {
  const a = el("a", null, texto);
  a.href = url;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  if (titulo) a.title = titulo;
  return a;
}

function numero(valor) {
  return Number(valor).toLocaleString(estado.idioma, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function pintarSeguridad(seg) {
  const panel = $("r-seguridad");
  panel.hidden = !seg;
  if (!seg) return;
  const req = seg.requisitos;
  $("seg-contexto").textContent = t("seg-contexto", { c: seg.contexto, cr: t("req-" + req.CR), ir: t("req-" + req.IR), ar: t("req-" + req.AR) });
  const cvss = $("seg-cvss");
  cvss.textContent = numero(seg.cvss_max);
  cvss.parentElement.dataset.sev = seg.severidad_max;
  $("seg-severidad").textContent = t("sev-" + seg.severidad_max);

  const triada = $("seg-triada");
  triada.replaceChildren();
  for (const dim of ["C", "I", "D"]) {
    const d = seg.triada[dim];
    const fila = el("div", "triada-fila");
    fila.setAttribute("role", "listitem");
    fila.dataset.riesgo = d.nivel;
    const barra = el("span", "triada-barra");
    const relleno = el("i");
    relleno.style.setProperty("--w", Math.round((d.riesgo_max / 25) * 100) + "%");
    barra.append(relleno);
    fila.append(el("span", null, t("dim-" + dim)), el("strong", null, t("riesgo-" + d.nivel)), barra);
    triada.append(fila);
  }

  const matriz = $("seg-matriz");
  matriz.replaceChildren();
  for (let p = 5; p >= 1; p--) {
    const fila = el("div");
    fila.setAttribute("role", "row");
    fila.style.display = "contents";
    fila.append(el("span", "eje", String(p)));
    for (let i = 1; i <= 5; i++) {
      const n = seg.matriz[p - 1][i - 1];
      const celda = el("span", "matriz-celda" + (n ? "" : " vacia"), n ? String(n) : "0");
      celda.setAttribute("role", "cell");
      celda.dataset.riesgo = p * i >= 17 ? "critico" : p * i >= 10 ? "alto" : p * i >= 5 ? "medio" : "bajo";
      celda.title = t("seg-celda", { p, i, n });
      celda.setAttribute("aria-label", celda.title);
      fila.append(celda);
    }
    matriz.append(fila);
  }
  const pie = el("div");
  pie.style.display = "contents";
  pie.append(el("span", "eje", ""));
  for (let i = 1; i <= 5; i++) pie.append(el("span", "eje", String(i)));
  matriz.append(pie);

  estado.seguridad = seg;
  pintarCategorias(seg);
  pintarGruposSeguridad(seg);
  pintarAnexos(seg);
  $("seg-vacio").hidden = seg.hallazgos.length > 0;
}

const NIVELES_RIESGO = ["critico", "alto", "medio", "bajo"];

function pintarCategorias(seg) {
  const caja = $("seg-categorias");
  caja.replaceChildren();
  caja.hidden = seg.categorias.length < 2;
  for (const c of seg.categorias) {
    const boton = el("button", "cat-tarjeta");
    boton.type = "button";
    boton.dataset.riesgo = c.peor;
    boton.setAttribute("aria-pressed", String(estado.agrupar === "categoria" && estado.categoriaFoco === c.id));
    const cabecera = el("span", "cat-cabecera");
    cabecera.append(el("span", "cat-nombre", c.nombre), el("span", "cat-total", String(c.total)));
    const barra = el("span", "cat-barra");
    for (const n of NIVELES_RIESGO) {
      if (!c.por_nivel[n]) continue;
      const tramo = el("i");
      tramo.dataset.riesgo = n;
      tramo.style.flex = String(c.por_nivel[n]);
      tramo.title = `${t("riesgo-" + n)}: ${c.por_nivel[n]}`;
      barra.append(tramo);
    }
    const pie = el("span", "cat-pie", NIVELES_RIESGO.filter((n) => c.por_nivel[n]).map((n) => `${c.por_nivel[n]} ${t("riesgo-" + n).toLowerCase()}`).join(", "));
    boton.append(cabecera, barra, pie);
    boton.addEventListener("click", () => {
      estado.categoriaFoco = c.id;
      cambiarAgrupacion("categoria");
      const destino = document.querySelector(`#seg-grupos [data-grupo="${c.id}"]`);
      if (destino) destino.scrollIntoView({ behavior: reducirMovimiento.matches ? "auto" : "smooth", block: "start" });
    });
    caja.append(boton);
  }
}

function cambiarAgrupacion(modo) {
  estado.agrupar = modo;
  guardar("agrupar", modo);
  document.querySelectorAll("[data-agrupar]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.agrupar === modo)));
  if (estado.seguridad) { pintarCategorias(estado.seguridad); pintarGruposSeguridad(estado.seguridad); }
}

function gruposPor(seg, modo) {
  if (modo === "categoria") {
    return seg.categorias.map((c) => ({ clave: c.id, titulo: c.nombre, nivel: c.peor, lista: seg.hallazgos.filter((h) => h.categoria === c.id) }));
  }
  if (modo === "owasp") {
    const claves = [...new Set(seg.hallazgos.map((h) => h.owasp || "—"))].sort((a, b) => (a === "—") - (b === "—") || a.localeCompare(b));
    return claves.map((k) => {
      const lista = seg.hallazgos.filter((h) => (h.owasp || "—") === k);
      const nombre = k === "—" ? t("sin-owasp") : `${k} ${lista[0].owasp_nombre}`;
      return { clave: k, titulo: nombre, nivel: NIVELES_RIESGO.find((n) => lista.some((h) => h.nivel_riesgo === n)) || "bajo", lista };
    });
  }
  if (modo === "cid") {
    return ["C", "I", "D"].map((d) => {
      const lista = seg.hallazgos.filter((h) => h.cid[d] !== "N");
      return { clave: d, titulo: t("dim-" + d), nivel: seg.triada[d].nivel === "ninguno" ? "bajo" : seg.triada[d].nivel, lista };
    }).filter((g) => g.lista.length);
  }
  return NIVELES_RIESGO.map((n) => ({ clave: n, titulo: t("riesgo-" + n), nivel: n, lista: seg.hallazgos.filter((h) => h.nivel_riesgo === n) }))
    .filter((g) => g.lista.length);
}

function fichaHallazgo(h, abierta) {
  const item = el("li");
  const detalle = el("details", "marcador");
  const resumen = el("summary");
  const chip = el("span", "seg-cvss-chip");
  chip.dataset.sev = h.severidad;
  if (h.cvss === null) chip.textContent = t("seg-informativo");
  else chip.append("CVSS ", el("b", null, numero(h.cvss)));
  const riesgo = el("span", "marcador-veces", `${t("riesgo-" + h.nivel_riesgo)} ${h.riesgo}`);
  riesgo.dataset.riesgo = h.nivel_riesgo;
  riesgo.style.color = "var(--r)";
  resumen.append(el("span", "marcador-desc", h.titulo), riesgo, chip);
  const cuerpo = el("div", "seg-detalle");
  cuerpo.append(el("p", null, h.descripcion));
  const refs = el("p", "seg-refs");
  if (h.owasp) refs.append(enlace(`OWASP ${h.owasp}`, "https://owasp.org/Top10/2025/", h.owasp_nombre));
  refs.append(el("span", "seg-cat", h.categoria_nombre));
  for (const c of h.cwe) refs.append(enlace(c, `https://cwe.mitre.org/data/definitions/${c.slice(4)}.html`));
  for (const m of h.mitre) refs.append(enlace(m.id, `https://attack.mitre.org/techniques/${m.id.replace(".", "/")}/`, m.nombre));
  for (const c of h.cve) refs.append(enlace(c, `https://www.cve.org/CVERecord?id=${c}`));
  cuerpo.append(refs);
  const afectadas = ["C", "I", "D"].filter((d) => h.cid[d] !== "N").map((d) => `${t("dim-" + d)} (${h.cid[d]})`);
  const lineaCid = afectadas.length ? t("seg-cid", { d: afectadas.join(", ") }) + ". " : "";
  cuerpo.append(el("p", null, `${lineaCid}${t("seg-probabilidad-impacto", { p: h.probabilidad, i: h.impacto })}`));
  if (h.vector) cuerpo.append(el("p", "seg-vector", h.vector));
  const evid = el("ul", "evidencias");
  for (const e of h.evidencias.slice(0, 8)) {
    const fila = el("li", "evidencia");
    fila.append(el("code", null, e.ubicacion), el("span", null, e.extracto));
    evid.append(fila);
  }
  cuerpo.append(evid);
  const rec = el("p", "seg-recomendacion");
  rec.append(el("strong", null, t("seg-recomendacion") + ": "), h.recomendacion);
  cuerpo.append(rec);
  detalle.append(resumen, cuerpo);
  detalle.open = abierta;
  item.append(detalle);
  return item;
}

function pintarGruposSeguridad(seg) {
  const grupos = $("seg-grupos");
  grupos.replaceChildren();
  const modo = ["riesgo", "categoria", "owasp", "cid"].includes(estado.agrupar) ? estado.agrupar : "riesgo";
  for (const g of gruposPor(seg, modo)) {
    if (!g.lista.length) continue;
    const seccion = el("section", "grupo");
    seccion.dataset.nivel = g.nivel;
    seccion.dataset.grupo = g.clave;
    const titulo = el("h2");
    titulo.append(el("span", "punto"), el("span", null, g.titulo),
      el("small", null, t(g.lista.length === 1 ? "hallazgos-1" : "hallazgos-n", { n: g.lista.length })));
    const ul = el("ul");
    for (const h of g.lista) ul.append(fichaHallazgo(h, h.nivel_riesgo === "critico"));
    seccion.append(titulo, ul);
    grupos.append(seccion);
  }
}

function pintarAnexos(seg) {
  const inventario = $("seg-inventario");
  inventario.replaceChildren();
  for (const c of seg.inventario || []) {
    const fila = el("tr");
    fila.append(el("td", null, t("tipo-" + c.tipo)), el("td", null, c.nombre), el("td", "version", c.version || ""));
    inventario.append(fila);
  }
  $("seg-inventario-bloque").hidden = !(seg.inventario || []).length;
  const terceros = $("seg-terceros");
  terceros.replaceChildren();
  for (const x of seg.terceros || []) {
    const fila = el("tr");
    const nombre = el("td");
    nombre.append(el("span", null, x.nombre + " "), el("code", null, x.host));
    fila.append(el("td", null, x.tipo_nombre), nombre, el("td", "rastreador", x.rastreador ? t("rastreador") : ""));
    terceros.append(fila);
  }
  $("seg-terceros-bloque").hidden = !(seg.terceros || []).length;
}

function pintarPixeles(r) {
  const filas = $("r-pixeles-filas");
  filas.replaceChildren();
  for (const f of r.pixeles || []) {
    const fila = el("tr", f.alerta ? "alerta" : null);
    const celda = el("td");
    celda.append(el("code", null, f.ubicacion));
    if (f.camara) celda.append(el("small", null, f.camara));
    fila.append(celda, el("td", null, f.ruido), el("td", null, f.periodico), el("td", null, f.tamano), el("td", null, f.captura));
    filas.append(fila);
  }
  $("r-pixeles").hidden = !(r.pixeles || []).length || Boolean(r.solo_seguridad && r.seguridad);
}

function pintarUbicaciones(r) {
  const lista = $("r-ubicaciones");
  lista.replaceChildren();
  const maximo = Math.max(1, ...(r.por_ubicacion || []).map((u) => u.peso));
  for (const u of r.por_ubicacion || []) {
    const li = el("li");
    li.dataset.nivel = u.peor;
    const medidor = el("span", "medidor");
    const relleno = el("i");
    relleno.style.setProperty("--w", Math.round((u.peso / maximo) * 100) + "%");
    medidor.append(relleno);
    li.append(el("code", null, u.ubicacion), medidor, el("span", "cuenta", t(u.veces === 1 ? "marcadores-1" : "marcadores-n", { n: u.veces })));
    li.title = u.ubicacion;
    lista.append(li);
  }
}

function cambiarVistaIa(modo) {
  estado.vistaIa = modo;
  document.querySelectorAll("[data-vista-ia]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.vistaIa === modo)));
  const r = estado.actual?.resultados[0];
  const soloSeg = Boolean(r?.solo_seguridad && r?.seguridad);
  $("r-grupos").hidden = soloSeg || modo === "ubicacion";
  $("r-ubicaciones").hidden = soloSeg || modo !== "ubicacion";
}


// ---------- Panel lateral: resumen, índice de la página y acciones ----------
let idsIndice = [];
let destinoElegido = null; // sección pulsada en el índice, hasta que el usuario se desplace por su cuenta

function pintarLateral(r) {
  const soloSeg = Boolean(r.solo_seguridad && r.seguridad);
  $("l-ia").hidden = soloSeg;
  $("l-ia-valor").textContent = r.banda === "indeterminada" ? "?" : String(r.puntuacion);
  $("l-ia").style.setProperty("--c", r.banda === "indeterminada" ? "var(--tinta-3)" : `var(--banda-${r.banda})`);
  const seg = r.seguridad;
  $("l-cvss").hidden = !seg;
  const riesgos = $("l-riesgos");
  riesgos.replaceChildren();
  if (seg) {
    $("l-cvss-valor").textContent = numero(seg.cvss_max);
    $("l-cvss").style.setProperty("--c", { critical: "var(--explicito)", high: "var(--fuerte)", medium: "var(--medio)", low: "var(--debil)" }[seg.severidad_max] || "var(--tinta)");
    for (const n of NIVELES_RIESGO) {
      const total = seg.hallazgos.filter((h) => h.nivel_riesgo === n).length;
      if (!total) continue;
      const chip = el("span", "chip-riesgo", `${total} ${t("riesgo-" + n).toLowerCase()}`);
      chip.dataset.riesgo = n;
      riesgos.append(chip);
    }
  }
  const entradas = [["r-cabecera", "i-resumen", ""]];
  if (!soloSeg) entradas.push([r.grupos.length ? "r-grupos" : "r-vacio", "i-ia", r.hallazgos.length || ""]);
  if (!soloSeg && (r.pixeles || []).length) entradas.push(["r-pixeles", "i-pixeles", r.pixeles.length]);
  if (seg) {
    entradas.push(["r-seguridad", "i-seguridad", ""]);
    if (seg.categorias.length > 1) entradas.push(["seg-categorias", "i-categorias", seg.categorias.length]);
    if (seg.hallazgos.length) entradas.push(["seg-grupos", "i-hallazgos", seg.hallazgos.length]);
    if ((seg.inventario || []).length) entradas.push(["seg-inventario-bloque", "i-componentes", seg.inventario.length]);
    if ((seg.terceros || []).length) entradas.push(["seg-terceros-bloque", "i-terceros", seg.terceros.length]);
  }
  if (r.notas.length) entradas.push(["r-notas-bloque", "i-notas", r.notas.length]);
  const indice = $("l-indice");
  indice.replaceChildren();
  for (const [id, clave, cuenta] of entradas) {
    const a = el("a");
    a.href = "#" + id;
    a.dataset.destino = id;
    a.append(el("span", null, t(clave)), el("span", null, cuenta === "" ? "" : String(cuenta)));
    a.addEventListener("click", (ev) => {
      ev.preventDefault();
      const destino = $(id);
      if (id === "r-notas-bloque") destino.open = true;
      destinoElegido = id;
      destino.scrollIntoView({ behavior: reducirMovimiento.matches ? "auto" : "smooth", block: "start" });
    });
    const li = el("li");
    li.append(a);
    indice.append(li);
  }
  // Marca la última sección cuyo inicio ya ha pasado bajo la barra superior
  destinoElegido = null;
  idsIndice = entradas.map(([id]) => id).filter((id) => $(id));
  requestAnimationFrame(marcarIndice); // tras mostrar la vista, cuando ya hay medidas reales
}

function marcarIndice() {
  if (!idsIndice.length) return;
  let actual = idsIndice[0];
  if (destinoElegido) actual = destinoElegido;
  else {
    for (const id of idsIndice) if ($(id).getBoundingClientRect().top <= 140) actual = id;
  if (scrollY > 0 && innerHeight + scrollY >= document.documentElement.scrollHeight - 4) actual = idsIndice[idsIndice.length - 1];
  }
  $("l-indice").querySelectorAll("a").forEach((a) => a.setAttribute("aria-current", String(a.dataset.destino === actual)));
}

let marcaPendiente = false;
for (const tipo of ["wheel", "touchstart", "keydown"]) addEventListener(tipo, () => { destinoElegido = null; }, { passive: true });
addEventListener("scroll", () => {
  if (marcaPendiente) return;
  marcaPendiente = true;
  requestAnimationFrame(() => { marcaPendiente = false; marcarIndice(); });
}, { passive: true });

function pintarCasos() {
  const lista = $("lista-casos");
  lista.replaceChildren();
  for (const caso of [...estado.casos].reverse()) {
    const r = caso.resultados[0];
    const boton = el("button", "caso");
    boton.type = "button";
    boton.title = r.objetivo;
    if (caso === estado.actual) boton.setAttribute("aria-current", "true");
    const puntos = el("span", "caso-puntos", r.solo_seguridad && r.seguridad ? numero(r.seguridad.cvss_max) : String(r.puntuacion));
    const colorSev = { critical: "--explicito", high: "--fuerte", medium: "--medio", low: "--debil" }[r.seguridad?.severidad_max] || "--tinta-3";
    puntos.style.color = r.solo_seguridad && r.seguridad ? `var(${colorSev})`
      : r.banda === "indeterminada" ? "var(--tinta-3)" : `var(--banda-${r.banda})`;
    if (r.banda === "indeterminada") puntos.textContent = "?";
    boton.append(el("span", "caso-nombre", r.objetivo.split(/[\\/]/).filter(Boolean).pop() || r.objetivo), puntos);
    boton.addEventListener("click", () => pintarResultado(caso));
    const item = el("li");
    item.append(boton);
    lista.append(item);
  }
  $("casos-vacio").hidden = estado.casos.length > 0;
}

// ---------- Análisis ----------
function opcionesActuales() {
  const maximo = parseInt($("op-max-paginas").value, 10);
  const ia = $("op-ia").checked;
  const seguridad = $("op-seguridad").checked || $("op-activo").checked;
  return {
    imagenes: $("imagenes-web").checked, rastrear: $("op-rastrear").checked,
    max_paginas: Number.isFinite(maximo) ? maximo : 0,
    seguridad, solo_seguridad: seguridad && !ia,
    activo: $("op-activo").checked, autorizado: $("op-activo").checked && $("op-autorizado").checked,
    consultas: $("op-consultas").checked,
    confiar_certificado: $("op-confiar").checked,
  };
}

function opcionesValidas() {
  const op = opcionesActuales();
  if (!$("op-ia").checked && !op.seguridad) { avisar(t("falta-analisis"), true); $("opciones").open = true; return false; }
  if (op.activo && !op.autorizado) { avisar(t("falta-autorizacion"), true); $("opciones").open = true; $("op-autorizado").focus(); return false; }
  return true;
}

const OPCIONES_GUARDADAS = ["op-ia", "op-seguridad", "imagenes-web", "op-rastrear", "op-consultas"];
function cargarOpciones() {
  for (const id of OPCIONES_GUARDADAS) {
    const valor = leer("op." + id);
    if (valor === "1" || valor === "0") $(id).checked = valor === "1";
  }
  const maximo = leer("op.max-paginas");
  if (maximo && /^-?\d{1,7}$/.test(maximo)) $("op-max-paginas").value = maximo;
  actualizarOpciones();
}

function actualizarOpciones() {
  $("op-autorizado-fila").hidden = !$("op-activo").checked;
  if (!$("op-activo").checked) $("op-autorizado").checked = false;
  const activas = ["op-seguridad", "op-rastrear", "op-activo"].filter((id) => $(id).checked).length + ($("op-ia").checked ? 0 : 1)
    + ($("op-consultas").checked ? 0 : 1) + ($("op-confiar").checked ? 1 : 0);
  $("opciones-cuenta").textContent = activas ? String(activas) : "";
}

let temporizadorProgreso = 0;
function seguirProgreso(activo) {
  clearInterval(temporizadorProgreso);
  if (!activo) return;
  temporizadorProgreso = setInterval(async () => {
    try {
      const dato = await api("/api/progress");
      if (estado.ocupado) actualizarCarga(dato);
    } catch (_) { /* el análisis sigue; se reintenta */ }
  }, 700);
}

// ---------- Detener un análisis iniciado por error ----------
function esCancelacion(e) { return e instanceof ErrorApi && e.message === "cancelled"; }

async function parar() {
  if (!estado.ocupado || estado.parando) return;
  estado.parando = true;
  $("parar").disabled = true;
  $("parar-texto").textContent = t("deteniendo");
  const subida = estado.subida;
  if (subida) {
    subida.cancelada = true;
    for (const control of subida.controles) control.abort();
  }
  try {
    await api("/api/cancel", subida ? { lote: subida.lote } : {});
  } catch (_) { /* si el servidor no responde, la petición de análisis acabará fallando y se avisará */ }
}

function detenido() {
  seguirProgreso(false);
  ocupado(false);
  estado.subida = null;
  mostrar(estado.actual ? "resultado" : "inicio");
  avisar(t("detenido"));
}

async function analizar(peticion, casoExistente = null) {
  if (estado.ocupado || !opcionesValidas()) return;
  ocupado(true, peticion.lote && carga.plan.includes("subida") ? null : []);
  seguirProgreso(true);
  try {
    const datos = await api("/api/analyze", { ...peticion, ...opcionesActuales(), idioma: estado.idioma });
    // Repetir el mismo objetivo actualiza su caso en lugar de duplicarlo
    const clave = peticion.objetivo ? "o:" + peticion.objetivo.replace(/\/+$/, "").toLowerCase() : "l:" + peticion.lote;
    const repetido = casoExistente || estado.casos.find((c) => c.clave === clave);
    const caso = repetido || { peticion, clave };
    caso.id = datos.id;
    caso.resultados = datos.resultados;
    caso.idioma = estado.idioma;
    if (repetido) estado.casos.splice(estado.casos.indexOf(repetido), 1);
    estado.casos.push(caso);
    seguirProgreso(false);
    ocupado(false);
    pintarResultado(caso);
  } catch (e) {
    if (esCancelacion(e)) return detenido();
    seguirProgreso(false);
    ocupado(false);
    mostrar(estado.actual ? "resultado" : "inicio");
    avisar(mensajeError(e), true);
  }
}

function nuevoLote() {
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

async function subirYAnalizar(ficheros, nombre) {
  if (!ficheros.length || estado.ocupado || !opcionesValidas()) return;
  const lote = nuevoLote();
  ocupado(true, ["subida"]);
  const subida = { lote, controles: new Set(), cancelada: false };
  estado.subida = subida;
  actualizarCarga({ fase: "subida", hecho: 0, total: ficheros.length, porcentaje: 0 });
  let hechos = 0;
  try {
    const cola = [...ficheros];
    const trabajador = async () => {
      while (cola.length && !subida.cancelada) {
        const { fichero, ruta } = cola.shift();
        const control = new AbortController();
        subida.controles.add(control);
        try {
          await api(`/api/upload?batch=${lote}&path=${encodeURIComponent(ruta)}`, fichero,
            { crudo: true, tipo: "application/octet-stream", senal: control.signal });
        } finally {
          subida.controles.delete(control);
        }
        hechos += 1;
        actualizarCarga({ fase: "subida", hecho: hechos, total: ficheros.length, detalle: ruta,
          porcentaje: Math.round((hechos / ficheros.length) * 100) });
      }
    };
    await Promise.all(Array.from({ length: Math.min(4, ficheros.length) }, trabajador));
  } catch (e) {
    if (subida.cancelada || esCancelacion(e)) return detenido();
    ocupado(false);
    mostrar(estado.actual ? "resultado" : "inicio");
    avisar(mensajeError(e), true);
    return;
  }
  if (subida.cancelada) return detenido();
  estado.subida = null;
  estado.ocupado = false;
  carga.objetivo = 0;
  carga.mostrado = 0;
  carga.plan = [];
  await analizar({ lote, nombre });
}

// Recorre carpetas soltadas con la API de entradas del navegador
function leerEntradas(entrada, prefijo, salida) {
  return new Promise((resolver) => {
    if (entrada.isFile) {
      entrada.file((f) => { salida.push({ fichero: f, ruta: prefijo + f.name }); resolver(); }, () => resolver());
    } else if (entrada.isDirectory) {
      const lector = entrada.createReader();
      const todas = [];
      const leerLote = () => lector.readEntries(async (lote) => {
        if (!lote.length) {
          for (const hija of todas) {
            if (["node_modules", ".venv", "venv", "__pycache__"].includes(hija.name)) continue;
            await leerEntradas(hija, prefijo + entrada.name + "/", salida);
          }
          resolver();
        } else { todas.push(...lote); leerLote(); }
      }, () => resolver());
      leerLote();
    } else resolver();
  });
}

// ---------- Exportar ----------
async function exportar(formato) {
  if (!estado.actual) return;
  try {
    const blob = await api("/api/export", { id: estado.actual.id, formato, idioma: estado.idioma }, { blob: true });
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(blob);
    enlace.download = { html: "aimarkers-report.html", md: "aimarkers-report.md", json: "aimarkers-report.json" }[formato];
    document.body.append(enlace);
    enlace.click();
    enlace.remove();
    setTimeout(() => URL.revokeObjectURL(enlace.href), 2000);
    avisar(t("guardado", { f: formato === "md" ? "Markdown" : formato.toUpperCase() }));
  } catch (e) {
    avisar(mensajeError(e), true);
  }
}

// ---------- Eventos ----------
function conectar() {
  $("formulario").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const objetivo = $("objetivo").value.trim();
    if (!objetivo) { avisar(t("falta-objetivo")); $("objetivo").focus(); return; }
    analizar({ objetivo });
  });

  for (const tipo of ["file", "folder"]) {
    $(tipo === "file" ? "elegir-fichero" : "elegir-carpeta").addEventListener("click", async () => {
      if (!estado.config || !estado.config.selector) {
        const entrada = $("selector-ficheros");
        entrada.toggleAttribute("webkitdirectory", tipo === "folder");
        entrada.click();
        return;
      }
      try {
        const { ruta } = await api("/api/pick", { tipo });
        if (!ruta) { avisar(t("sin-seleccion")); return; }
        $("objetivo").value = ruta;
        analizar({ objetivo: ruta });
      } catch (e) { avisar(mensajeError(e), true); }
    });
  }
  $("selector-ficheros").addEventListener("change", (ev) => {
    const ficheros = [...ev.target.files].map((f) => ({ fichero: f, ruta: f.webkitRelativePath || f.name }));
    const carpeta = ficheros[0]?.ruta.includes("/") ? ficheros[0].ruta.split("/")[0] : "";
    const nombre = ficheros.length === 1 ? ficheros[0].fichero.name : (carpeta || t("varios", { n: ficheros.length }));
    ev.target.value = "";
    subirYAnalizar(ficheros, nombre);
  });

  document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => {
    if (estado.idioma === b.dataset.lang) return;
    estado.idioma = b.dataset.lang;
    guardar("idioma", estado.idioma);
    aplicarIdioma();
    // Los textos del resultado vienen del motor: se vuelve a pedir en el nuevo idioma
    if (estado.actual && !$("vista-resultado").hidden) analizar(estado.actual.peticion, estado.actual);
  }));

  for (const id of [...OPCIONES_GUARDADAS, "op-activo", "op-autorizado"]) {
    $(id).addEventListener("change", () => {
      if (OPCIONES_GUARDADAS.includes(id)) guardar("op." + id, $(id).checked ? "1" : "0");
      actualizarOpciones();
    });
  }
  $("op-max-paginas").addEventListener("change", () => guardar("op.max-paginas", $("op-max-paginas").value));
  document.addEventListener("click", (ev) => {
    if ($("opciones").open && !$("opciones").contains(ev.target)) $("opciones").open = false;
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && $("opciones").open) { $("opciones").open = false; $("opciones").querySelector("summary").focus(); }
  });

  $("parar").addEventListener("click", parar);
  $("l-repetir").addEventListener("click", () => {
    if (estado.actual) analizar(estado.actual.peticion, estado.actual);
  });
  $("inicio").addEventListener("click", () => {
    if (estado.ocupado) return;
    estado.actual = null;
    mostrar("inicio");
    pintarCasos();
    revelar($("titular-inicio"));
  });

  document.querySelectorAll("[data-agrupar]").forEach((b) => b.addEventListener("click", () => {
    estado.categoriaFoco = null;
    cambiarAgrupacion(b.dataset.agrupar);
  }));
  document.querySelectorAll("[data-vista-ia]").forEach((b) => b.addEventListener("click", () => cambiarVistaIa(b.dataset.vistaIa)));

  $("tema").addEventListener("click", () => {
    estado.tema = { auto: "dark", dark: "light", light: "auto" }[estado.tema];
    guardar("tema", estado.tema);
    aplicarTema();
  });

  document.querySelectorAll("[data-formato]").forEach((b) => b.addEventListener("click", () => exportar(b.dataset.formato)));

  document.addEventListener("keydown", (ev) => {
    if ((ev.metaKey || ev.ctrlKey) && ev.key.toLowerCase() === "k") { ev.preventDefault(); $("objetivo").focus(); $("objetivo").select(); }
  });

  // Arrastrar y soltar en toda la ventana
  let profundidad = 0;
  const capa = $("soltar");
  const conFicheros = (ev) => [...(ev.dataTransfer?.types || [])].includes("Files");
  window.addEventListener("dragenter", (ev) => { if (!conFicheros(ev)) return; ev.preventDefault(); profundidad += 1; capa.hidden = false; });
  window.addEventListener("dragover", (ev) => { if (conFicheros(ev)) ev.preventDefault(); });
  window.addEventListener("dragleave", () => { profundidad = Math.max(0, profundidad - 1); if (!profundidad) capa.hidden = true; });
  window.addEventListener("drop", async (ev) => {
    if (!conFicheros(ev)) return;
    ev.preventDefault();
    profundidad = 0;
    capa.hidden = true;
    const entradas = [...ev.dataTransfer.items].map((i) => i.webkitGetAsEntry && i.webkitGetAsEntry()).filter(Boolean);
    const ficheros = [];
    if (entradas.length) {
      for (const entrada of entradas) await leerEntradas(entrada, "", ficheros);
    } else {
      for (const f of ev.dataTransfer.files) ficheros.push({ fichero: f, ruta: f.name });
    }
    const nombre = entradas.length === 1 ? entradas[0].name : t("varios", { n: ficheros.length });
    subirYAnalizar(ficheros, nombre);
  });
}

async function iniciar() {
  iniciarToken();
  estado.tema = ["auto", "light", "dark"].includes(leer("tema")) ? leer("tema") : "auto";
  const idiomaGuardado = leer("idioma");
  estado.idioma = ["es", "en"].includes(idiomaGuardado) ? idiomaGuardado
    : ((navigator.language || "").toLowerCase().startsWith("es") ? "es" : "en");
  estado.agrupar = ["riesgo", "categoria", "owasp", "cid"].includes(leer("agrupar")) ? leer("agrupar") : "riesgo";
  document.querySelectorAll("[data-agrupar]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.agrupar === estado.agrupar)));
  conectar();
  construirIlustracion();
  animarIlustracion("deriva");
  document.addEventListener("visibilitychange", () => { if (!document.hidden) animarIlustracion(ilu.modo); });
  cargarOpciones();
  aplicarIdioma();
  revelar($("titular-inicio"));
  try {
    estado.config = await api("/api/config");
    if (!leer("idioma") && estado.config.forzado) { estado.idioma = estado.config.idioma; aplicarIdioma(); }
    pintarEstadoC2pa();
  } catch (e) {
    avisar(mensajeError(e), true);
  }
  pintarCasos();
}

document.addEventListener("DOMContentLoaded", iniciar);
