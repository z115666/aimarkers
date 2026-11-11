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
    "imagenes-web": "Analizar también las imágenes de las webs",
    "analizando": "Analizando",
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
    "atajo": "Atajo: {k}",
    "varios": "{n} ficheros sueltos",
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
    "imagenes-web": "Also analyse images on websites",
    "analizando": "Analysing",
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
    "atajo": "Shortcut: {k}",
    "varios": "{n} separate files",
  },
};

const $ = (id) => document.getElementById(id);
const estado = { idioma: "es", tema: "auto", token: "", config: null, casos: [], actual: null, ocupado: false };

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
    });
  } catch (_) {
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
}

// ---------- Vistas ----------
function mostrar(vista) {
  for (const nombre of ["inicio", "analizando", "resultado"]) $("vista-" + nombre).hidden = nombre !== vista;
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

function ocupado(activo, progreso = "") {
  estado.ocupado = activo;
  $("analizar").disabled = activo;
  $("progreso").textContent = progreso;
  if (activo) { mostrar("analizando"); latido(true); } else latido(false);
}

// ---------- Resultado ----------
function pintarResultado(caso) {
  const r = caso.resultados[0];
  estado.actual = caso;
  $("r-objetivo").textContent = r.objetivo;
  const veredicto = $("r-veredicto");
  veredicto.textContent = r.valoracion;
  veredicto.dataset.banda = r.banda;
  const meta = $("r-meta");
  meta.replaceChildren(el("span", null, r.tipo_nombre),
    el("span", null, t(r.ficheros_analizados === 1 ? "ficheros-1" : "ficheros-n", { n: r.ficheros_analizados })));

  $("r-espectro").dataset.banda = r.banda;
  $("r-puntos").textContent = r.banda === "indeterminada" ? "?" : String(r.puntuacion);
  $("r-espectro-texto").textContent = t("espectro", { n: r.puntuacion, v: r.valoracion });
  const marca = $("r-marca");
  marca.style.left = "0%";
  requestAnimationFrame(() => requestAnimationFrame(() => { marca.style.left = r.puntuacion + "%"; }));

  $("r-explicita").hidden = !r.atribucion_explicita;

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
  $("r-vacio").hidden = r.grupos.length > 0;

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

function pintarCasos() {
  const lista = $("lista-casos");
  lista.replaceChildren();
  for (const caso of [...estado.casos].reverse()) {
    const r = caso.resultados[0];
    const boton = el("button", "caso");
    boton.type = "button";
    boton.title = r.objetivo;
    if (caso === estado.actual) boton.setAttribute("aria-current", "true");
    const puntos = el("span", "caso-puntos", String(r.puntuacion));
    puntos.style.color = r.banda === "indeterminada" ? "var(--tinta-3)" : `var(--banda-${r.banda})`;
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
async function analizar(peticion, casoExistente = null) {
  if (estado.ocupado) return;
  ocupado(true);
  try {
    const datos = await api("/api/analyze", { ...peticion, idioma: estado.idioma, imagenes: $("imagenes-web").checked });
    // Repetir el mismo objetivo actualiza su caso en lugar de duplicarlo
    const clave = peticion.objetivo ? "o:" + peticion.objetivo.replace(/\/+$/, "").toLowerCase() : "l:" + peticion.lote;
    const repetido = casoExistente || estado.casos.find((c) => c.clave === clave);
    const caso = repetido || { peticion, clave };
    caso.id = datos.id;
    caso.resultados = datos.resultados;
    caso.idioma = estado.idioma;
    if (repetido) estado.casos.splice(estado.casos.indexOf(repetido), 1);
    estado.casos.push(caso);
    ocupado(false);
    pintarResultado(caso);
  } catch (e) {
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
  if (!ficheros.length || estado.ocupado) return;
  const lote = nuevoLote();
  ocupado(true, t("subiendo", { a: 0, b: ficheros.length }));
  estado.ocupado = true;
  let hechos = 0;
  try {
    const cola = [...ficheros];
    const trabajador = async () => {
      while (cola.length) {
        const { fichero, ruta } = cola.shift();
        await api(`/api/upload?batch=${lote}&path=${encodeURIComponent(ruta)}`, fichero,
          { crudo: true, tipo: "application/octet-stream" });
        hechos += 1;
        $("progreso").textContent = t("subiendo", { a: hechos, b: ficheros.length });
      }
    };
    await Promise.all(Array.from({ length: Math.min(4, ficheros.length) }, trabajador));
  } catch (e) {
    ocupado(false);
    mostrar(estado.actual ? "resultado" : "inicio");
    avisar(mensajeError(e), true);
    return;
  }
  estado.ocupado = false;
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
  conectar();
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
