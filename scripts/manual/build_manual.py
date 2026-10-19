"""Genera los manuales de usuario en PDF de AutoPrevias (Basic y Plus) — Radical Records.

Uso:
    python scripts/manual/build_manual.py            # captura + PDF de las dos ediciones
    python scripts/manual/build_manual.py plus       # solo una edición
    python scripts/manual/build_manual.py --no-capture   # reutiliza las capturas de docs/manual/_work

Lee la versión de src/__version__.py, así que basta con volver a ejecutarlo en cada versión.
Salida: docs/manual/AutoPrevias-Manual-Basic.pdf  y  docs/manual/AutoPrevias-Manual-Plus.pdf
Requisitos de desarrollo: playwright (+ Chromium), pillow, PySide6 (los de la app) y soundfile.
"""
from __future__ import annotations
import html, os, shutil, subprocess, sys, tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.__version__ import __version__ as VERSION   # noqa: E402
from src import links as L   # noqa: E402

MANUAL = ROOT / "docs" / "manual"
WORK = MANUAL / "_work"
SUPPORT = "radicalrecordsvlc@gmail.com"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]


def fecha_larga() -> str:
    d = date.today()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


# ───────────────────────────── imágenes ─────────────────────────────
def prep_images(edition: str, out: Path) -> dict[str, str]:
    """Convierte las capturas PNG a JPEG ligero y devuelve {nombre: ruta file://}."""
    from PIL import Image
    src = WORK / edition
    out.mkdir(parents=True, exist_ok=True)
    res = {}
    for p in sorted(src.glob("*.png")):
        im = Image.open(p).convert("RGB")
        maxw = 1700 if im.width > 1200 else im.width
        if im.width > maxw:
            im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
        q = out / (p.stem + ".jpg")
        im.save(q, quality=88, optimize=True)
        res[p.stem] = q.as_uri()
    logo = ROOT / "assets" / "logo_banner.png"
    emblem = ROOT / "assets" / "logo_emblem.png"
    for nm, f in (("logo_banner", logo), ("logo_emblem", emblem)):
        if f.exists():
            shutil.copy(f, out / f.name)
            res[nm] = (out / f.name).as_uri()
    return res


# ───────────────────────────── piezas HTML ─────────────────────────────
def fig(src: str, caption: str, cls: str = "") -> str:
    return f'<figure class="{cls}"><img src="{src}"><figcaption>{caption}</figcaption></figure>'


def legend(items: list[tuple[str, str]], cls: str = '') -> str:
    rows = "".join(f'<li><span class="num">{i}</span><div><b>{html.escape(t)}</b> — {d}</div></li>'
                   for i, (t, d) in enumerate(items, 1))
    return f'<ol class="legend {cls}">{rows}</ol>'


def tip(text: str, kind: str = "tip") -> str:
    label = {"tip": "💡 Consejo", "warn": "⚠️ Importante", "plus": "✦ Solo en Plus"}[kind]
    return f'<div class="callout {kind}"><b>{label}</b><p>{text}</p></div>'


def steps(items: list[str]) -> str:
    return '<ol class="steps">' + "".join(f"<li>{s}</li>" for s in items) + "</ol>"


def kbd(*keys: str) -> str:
    return " ".join(f"<kbd>{k}</kbd>" for k in keys)


CSS = """
@page { size: A4; margin: 20mm 17mm 20mm 17mm; }
* { box-sizing: border-box; }
html { font-family: 'Inter','Helvetica Neue',Arial,sans-serif; color: #1b1d26; font-size: 10.4pt; line-height: 1.55; }
body { margin: 0; }
h1 { font-size: 22pt; margin: 0 0 6mm; color: #0c0d12; letter-spacing: -.3px; border-bottom: 3px solid #e11d2e; padding-bottom: 3mm; }
h1, h2, h3 { break-after: avoid; }
h2 { font-size: 14pt; margin: 8mm 0 3mm; color: #0c0d12; }
h3 { font-size: 11.2pt; margin: 6mm 0 2mm; color: #e11d2e; text-transform: uppercase; letter-spacing: .6px; }
p { margin: 0 0 3mm; }
ul, ol { margin: 0 0 3mm; padding-left: 5.5mm; }
li { margin-bottom: 1.4mm; }
section { break-before: page; }
section.flow { break-before: auto; }
.cover { height: 296.5mm; width: 210mm; background: #0a0b10 radial-gradient(circle at 80% 8%, #3a0a12 0, #0a0b10 55%); color: #fff;
  position: relative; padding: 26mm 20mm; break-after: page; overflow: hidden; }
.cover .banner { width: 120mm; margin-bottom: 30mm; }
.cover .kicker { color: #ff3b4e; letter-spacing: 3px; font-weight: 800; font-size: 10pt; text-transform: uppercase; }
.cover h1 { color: #fff; border: 0; font-size: 46pt; line-height: 1.02; margin: 4mm 0 4mm; letter-spacing: -1.5px; }
.cover .sub { font-size: 16pt; color: #c9ccd8; margin-bottom: 10mm; max-width: 140mm; }
.cover .ed { display: inline-block; padding: 2.4mm 7mm; border-radius: 99px; font-weight: 800; letter-spacing: 2px; font-size: 13pt; }
.cover .ed.plus { background: linear-gradient(90deg,#7c3aed,#a855f7); }
.cover .ed.basic { background: linear-gradient(90deg,#1d4ed8,#3b82f6); }
.cover .meta { position: absolute; left: 20mm; bottom: 24mm; color: #9aa0b4; font-size: 10pt; line-height: 1.7; }
.cover .meta b { color: #fff; }
.cover .emblem { position: absolute; right: -18mm; bottom: -20mm; width: 120mm; opacity: .09; }
.toc { list-style: none; padding: 0; counter-reset: t; }
.toc li { display: flex; padding: 2mm 0; border-bottom: 1px dotted #c4c7d3; font-size: 11pt; counter-increment: t; }
.toc li::before { content: counter(t) "."; width: 9mm; color: #e11d2e; font-weight: 800; }
figure { margin: 4mm 0 5mm; break-inside: avoid; text-align: center; }
figure img { max-width: 100%; border-radius: 9px; border: 1px solid #232733; box-shadow: 0 3px 14px rgba(0,0,0,.28); }
figure.small img { max-width: 54%; }
figure.mid img { max-width: 76%; }
figure.tiny img { max-width: 42%; }
figcaption { font-size: 8.8pt; color: #62677a; margin-top: 2mm; }
.legend { list-style: none; padding: 0; margin: 2mm 0 4mm; columns: 1; }
.legend li { display: flex; gap: 3mm; align-items: flex-start; margin-bottom: 2mm; break-inside: avoid; }
.num { flex: none; width: 6.2mm; height: 6.2mm; border-radius: 50%; background: #e11d2e; color: #fff; font-weight: 800;
  font-size: 8.6pt; display: inline-flex; align-items: center; justify-content: center; margin-top: .4mm; }
.legend.two { columns: 2; column-gap: 8mm; }
.steps { list-style: none; counter-reset: s; padding: 0; }
.steps li { counter-increment: s; position: relative; padding: 1.8mm 3mm 1.8mm 12mm; margin-bottom: 1.6mm; background: #f4f5f9;
  border-radius: 8px; break-inside: avoid; }
.steps li::before { content: counter(s); position: absolute; left: 3mm; top: 2.2mm; width: 6.4mm; height: 6.4mm; border-radius: 50%;
  background: #e11d2e; color: #fff; font-weight: 800; font-size: 9pt; text-align: center; line-height: 6.4mm; }
.callout { border-left: 4px solid #e11d2e; background: #fff4f5; padding: 2.5mm 4mm; border-radius: 0 8px 8px 0; margin: 3mm 0 4mm; break-inside: avoid; }
.callout p { margin: 1mm 0 0; }
.callout.tip { border-color: #16a34a; background: #effaf2; }
.callout.warn { border-color: #d97706; background: #fff8eb; }
.callout.plus { border-color: #7c3aed; background: #f5f0ff; }
table { border-collapse: collapse; width: 100%; margin: 2mm 0 4mm; font-size: 9.6pt; break-inside: avoid; }
th { background: #0c0d12; color: #fff; text-align: left; padding: 2mm 3mm; font-weight: 700; }
td { padding: 2mm 3mm; border-bottom: 1px solid #e3e5ee; vertical-align: top; }
tr:nth-child(even) td { background: #f8f9fc; }
td.c, th.c { text-align: center; }
kbd { background: #eceef5; border: 1px solid #c9cddc; border-bottom-width: 2px; border-radius: 4px; padding: 0 1.6mm; font-family: inherit;
  font-size: 9pt; font-weight: 700; }
code { background: #eceef5; border-radius: 4px; padding: .2mm 1.6mm; font-family: 'JetBrains Mono','Menlo',Consolas,monospace; font-size: 9pt; }
pre { background: #0c0d12; color: #e8eaf2; padding: 3mm 4mm; border-radius: 8px; font-size: 9.4pt; overflow: hidden; }
pre code { background: none; color: inherit; padding: 0; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; }
.card { border: 1px solid #e3e5ee; border-radius: 10px; padding: 3mm 4mm; break-inside: avoid; }
.card h4 { margin: 0 0 1.5mm; font-size: 10.6pt; }
.badge { display: inline-block; padding: .3mm 2.4mm; border-radius: 99px; font-size: 8pt; font-weight: 800; letter-spacing: .6px; color: #fff; }
.badge.plus { background: #7c3aed; } .badge.basic { background: #2563eb; }
.small { font-size: 9pt; color: #62677a; }
"""

# ───────────────────────────── contenido ─────────────────────────────

def portada(ed: str, im: dict) -> str:
    plus = ed == "plus"
    nombre = "PLUS" if plus else "BASIC"
    return f"""
<div class="cover">
  <img class="banner" src="{im.get('logo_banner','')}">
  <div class="kicker">Manual de usuario</div>
  <h1>AutoPrevias</h1>
  <div class="sub">{'Todas las funciones de estudio: edición avanzada, firma, modo promo, lote y más.' if plus else 'Genera previas profesionales de tus tracks en un solo clic.'}</div>
  <span class="ed {ed}">EDICIÓN {nombre}</span>
  <div class="meta"><b>Radical Records</b><br>Versión {VERSION} · {fecha_larga()}<br>Soporte: {SUPPORT}</div>
  <img class="emblem" src="{im.get('logo_emblem','')}">
</div>"""


def indice(plus: bool) -> str:
    items = ["Qué es AutoPrevias", "Instalación (macOS y Windows)", "Activar tu licencia", "Recorrido por la interfaz",
             "Tu primera previa, paso a paso", "Forma de onda, cortes y reproductor",
             "Ajustes de exportación"]
    if plus:
        items += ["Editor avanzado: cortes, BPM y estructura", "Efectos, Voice Drop y Modo promo",
                  "Firma, carátula y presets propios", "Lote, carpeta vigilada y Recientes"]
    else:
        items += ["Historial de pistas recientes", "Pasar a la edición Plus"]
    items += ["Actualizaciones, licencia e idioma", "Atajos de teclado", "Solución de problemas", "Soporte y licencias de terceros"]
    lis = "".join(f"<li>{t}</li>" for t in items)
    return f'<section class="flow" style="break-before:auto"><h1>Contenido</h1><ul class="toc">{lis}</ul></section>'


def s_intro(ed: str, plus: bool) -> str:
    inc = ("Exportación en <b>MP3 320 kbps</b> con metadatos, análisis de BPM y tonalidad, previas de 15/30/60/120 s, "
           "<b>vídeo animado Radical Neón</b> (con marca de agua), forma de onda con cortes ajustables, <b>efectos Flanger y Filter Sweep</b> que colocas tú sobre la onda, reproductor A/B y actualizaciones automáticas." if not plus else
           "Todo lo de Basic y además: exportación <b>WAV 24 bit / FLAC / MP3</b>, editor avanzado de cortes y BPM, efectos en la onda y Master LUFS, "
           "<b>Voice Drop</b>, <b>Modo promo antifugas</b>, firma y carátula, presets propios, historial, lote, carpeta vigilada y vídeo animado Radical Neón <b>sin marca de agua</b>, con tu propia imagen, onda de sonido y final a tu elección.")
    return f"""
<section><h1>1. Qué es AutoPrevias</h1>
<p><b>AutoPrevias</b> es la herramienta de <b>Radical Records</b> para crear <b>previas profesionales</b> de tus temas. Arrastras un track, la
aplicación analiza su estructura (intro, subidas, <i>drops</i>, descansos), calcula los mejores fragmentos y construye una previa lista para enviar a
promotores, sellos, DJs o redes sociales.</p>
<h3>Qué hace por ti</h3>
<ul>
<li><b>Detecta el BPM y la tonalidad</b> (sistema Camelot) del tema.</li>
<li><b>Encuentra los drops</b> y las secciones clave, y propone los cortes ideales.</li>
<li><b>Une los fragmentos</b> con transiciones cuidadas, sin saltos de ritmo.</li>
<li><b>Exporta</b> la previa con el nombre, los metadatos y la carátula que elijas.</li>
</ul>
<h3>Qué incluye la edición {'Plus' if plus else 'Basic'}</h3>
<p>{inc}</p>
<h3>Formatos de audio que puedes cargar</h3>
<p><code>WAV</code> · <code>MP3</code> · <code>FLAC</code> · <code>AIFF</code> · <code>M4A</code></p>
<h3>Requisitos del sistema</h3>
<table><tr><th>Sistema</th><th>Requisito</th></tr>
<tr><td>macOS</td><td>Mac con chip Apple Silicon (M1, M2, M3, M4) — macOS 12 o superior</td></tr>
<tr><td>Windows</td><td>Windows 10 u 11 de 64 bits</td></tr>
<tr><td>Procesador</td><td>Cuantos más núcleos, más rápido analiza y genera vídeo (4 o más recomendados). El ajuste <b>⚙ Licencia → Rendimiento</b> controla cuántos usa.</td></tr>
<tr><td>Memoria y espacio</td><td>8 GB de RAM recomendados · 600 MB de espacio libre</td></tr>
<tr><td>Internet</td><td>Solo para activar la licencia, la verificación automática (al abrir la app y cada pocas horas; puedes trabajar hasta 14 días sin conexión) y buscar actualizaciones</td></tr></table>
</section>"""


def s_install(ed: str) -> str:
    cap = "Plus" if ed == "plus" else "Basic"
    buy = L.short(L.url_for(ed))
    return f"""
<section><h1>2. Instalación</h1>
<p>Tras tu compra en la tienda de Radical Records (<b>{buy}</b>) descarga desde Payhip el instalador de tu edición (<b>{cap}</b>):</p>
<table><tr><th>Sistema</th><th>Archivo</th></tr>
<tr><td>macOS (Apple Silicon)</td><td><code>AutoPrevias-{cap}-macOS-arm64.dmg</code></td></tr>
<tr><td>Windows (64 bits)</td><td><code>AutoPrevias-{cap}-Windows-x64-Setup.exe</code></td></tr></table>
<h3>🍏 En macOS</h3>
{steps(["Haz doble clic en el archivo <code>.dmg</code> para abrirlo.",
        "Arrastra el icono de <b>AutoPrevias</b> a la carpeta <b>Aplicaciones</b>.",
        "Expulsa la imagen de disco desde el Finder.",
        "La primera vez, macOS puede avisar de que no puede verificar al desarrollador (la app no usa el certificado de pago de Apple). Abre la app <b>Terminal</b> y ejecuta:"])}
<pre><code>xattr -cr /Applications/AutoPrevias.app</code></pre>
<p>Después ábrela con doble clic con normalidad. <b>Alternativa sin Terminal:</b> abre la app, pulsa <i>Cancelar</i> en el aviso,
ve a <i>Ajustes del Sistema → Privacidad y seguridad</i>, y pulsa <b>«Abrir de todos modos»</b>.</p>
<h3>🪟 En Windows</h3>
{steps(["Haz doble clic en el instalador <code>.exe</code>.",
        "Si aparece la pantalla azul <b>«Windows protegió su PC»</b> (SmartScreen), pulsa <b>«Más información»</b> y después <b>«Ejecutar de todas formas»</b>. Solo ocurre la primera vez.",
        "Elige el idioma del asistente, la carpeta de instalación y los accesos directos, y pulsa <b>Instalar</b>.",
        "Al terminar, pulsa <b>Completar</b> para abrir AutoPrevias."])}
</section>"""


def s_activ(ed: str, im: dict) -> str:
    cap = "Plus" if ed == "plus" else "Basic"
    buy = L.short(L.url_for(ed))
    return f"""
<section><h1>3. Activar tu licencia</h1>
<p>La primera vez que abras AutoPrevias verás la pantalla de activación. Necesitas la <b>clave de licencia {cap}</b> que recibiste por correo
al comprar en la tienda de Radical Records (<b>{buy}</b>).</p>
{fig(im.get('10_activacion',''), 'Pantalla de activación (se muestra vacía; tu clave es personal)', 'tiny')}
{steps(["Copia la clave del correo de compra.", "Pégala en el campo de la pantalla de activación.",
        "Pulsa <b>Activar licencia</b>. Hace falta conexión a Internet solo en este momento.",
        "Listo: AutoPrevias se abre y ya no volverá a pedirte la clave."])}
<h3>Cada clave es de su edición</h3>
<p>La clave de <b>Basic</b> solo activa AutoPrevias Basic y la de <b>Plus</b> solo activa AutoPrevias Plus. Si usas un instalador que no corresponde a tu compra,
la app te avisa y no se activa nada: descarga el instalador correcto en la tienda de Radical Records.</p>
<h3>Una licencia = un equipo</h3>
<p>Tu clave puede estar activa en <b>un solo ordenador a la vez</b>. Si ya la usas en uno, no se podrá activar en otro hasta que la
desactives allí (<b>⚙ Licencia → Desactivar licencia en este equipo</b>, que la libera al instante) o pasen 15 días sin que ese equipo
se conecte. Si un ordenador se avería, escríbenos y la liberamos. El equipo se identifica con un código anónimo: no se envía ningún dato personal.</p>
<h3>Cómo funciona después</h3>
<table><tr><th>Situación</th><th>Qué ocurre</th></tr>
<tr><td>Con Internet</td><td>AutoPrevias se verifica sola con el servidor cada vez que la abres y cada 6 horas, en segundo plano. <b>No vuelve a pedirte la clave.</b></td></tr>
<tr><td>Sin Internet</td><td>Puedes seguir trabajando con normalidad hasta <b>14 días</b> desde la última verificación (periodo de gracia).</td></tr>
<tr><td>Más de 14 días sin conexión</td><td>Al abrir, la app se verifica sola. Si sigues sin Internet te pide conectarte (<i>Reintentar</i> / <i>Salir</i>); no necesitas escribir la clave otra vez.</td></tr></table>
{tip(f"Cada instalador lleva su edición incluida: el instalador {cap} solo acepta claves {cap}. Tu clave es personal: no la compartas ni la publiques; si crees que alguien la ha visto, escribe a " + SUPPORT + ".", "warn")}
</section>"""


def s_interfaz(ed: str, plus: bool, im: dict) -> str:
    if plus:
        l1 = [("Abrir archivo", "elige un track desde tu ordenador (también puedes arrastrarlo a la ventana)."),
              ("Recientes", "historial de previas generadas y pistas abiertas, para reabrir un proyecto."),
              ("Modo Lote", "procesa varias pistas seguidas de forma automática."),
              ("Vigilar Carpeta", "genera previas solas cuando cae un tema nuevo en una carpeta."),
              ("Firmar tema", "firma un tema entero (no una previa): carátula y etiquetas, en FLAC o WAV a máxima calidad."),
              ("Licencia", "versión, estado de la licencia, idioma y búsqueda de actualizaciones."),
              ("ES / EN", "cambia el idioma de la interfaz (castellano por defecto)."),
              ("Distintivo de edición", "te indica que trabajas con la edición PLUS.")]
    else:
        l1 = [("Abrir archivo", "elige un track desde tu ordenador (también puedes arrastrarlo a la ventana)."),
              ("Recientes", "lista de pistas abiertas recientemente para volver a cargarlas con un clic."),
              ("Licencia", "versión, estado de la licencia, idioma y búsqueda de actualizaciones."),
              ("ES / EN", "cambia el idioma de la interfaz (castellano por defecto)."),
              ("Distintivo de edición", "te indica que trabajas con la edición BÁSICA.")]
    if plus:
        l2 = [("Forma de onda", "tu track con las secciones coloreadas y los cortes que irán a la previa."),
              ("Reproductor", "escucha la pista original o la previa generada (A/B)."),
              ("BPM", "tempo detectado; haz doble clic para corregirlo."),
              ("Duración de la previa", "15 s, 30 s, 60 s o 2 min (club)."),
              ("Mis presets", "guarda y aplica tus propios ajustes de firma y estilo."),
              ("Personalizar cortes y BPM", "abre el editor avanzado."),
              ("Efectos en la onda", "arrastra Flanger o Filter Sweep hasta donde quieras que suenen."),
              ("Cómo empieza y acaba", "arranque y final de la previa: con el efecto de vinilo o a los BPM originales."),
              ("Nombre y formatos", "nombre del archivo y formatos de salida."),
              ("Master LUFS", "volumen de club; los efectos Flanger y Filter Sweep se arrastran sobre la onda."),
              ("Voice Drop", "superpone tu firma de voz o jingle sobre la previa."),
              ("Modo promo", "firma repetida y MP3 128 kbps para proteger el audio."),
              ("Firma y carátula", "artista, sello, álbum, género, comentario y portada."),
              ("GENERAR PREVIA", "crea y exporta la previa.")]
    else:
        l2 = [("Forma de onda", "tu track con las secciones coloreadas y los cortes que irán a la previa."),
              ("Reproductor", "escucha la pista original o la previa generada (A/B)."),
              ("BPM", "tempo detectado; haz doble clic para corregirlo."),
              ("Duración de la previa", "15 s, 30 s, 60 s o 2 min (club)."),
              ("Ordenar y mover cortes", "pon nombre y orden a los cortes y elige dónde empieza la previa."),
              ("Efectos en la onda", "arrastra Flanger o Filter Sweep hasta donde quieras que suenen."),
              ("Nombre", "nombre del archivo de la previa."),
              ("Cambiar carpeta", "elige dónde se guardan las previas."),
              ("GENERAR PREVIA", "crea y exporta la previa en MP3 320 kbps.")]
    return f"""
<section><h1>4. Recorrido por la interfaz</h1>
<h3>Pantalla de inicio</h3>
{fig(im.get('01_bienvenida_anot',''), 'Pantalla de inicio de AutoPrevias')}
{legend(l1)}
<section class="flow" style="break-before:page">
<h3>Pantalla de trabajo</h3>
<p>Al cargar un track, AutoPrevias lo analiza (unos segundos) y muestra la pantalla de trabajo, con todo lo necesario para generar tu previa.</p>
{fig(im.get('03_cargada_anot',''), 'Pantalla de trabajo con una pista analizada')}
{legend(l2, 'two')}
</section></section>"""


def s_primera(ed: str, plus: bool, im: dict) -> str:
    extra = (" Si quieres retocar algo, activa <b>Personalizar Cortes &amp; BPM</b> (ver capítulo 8)." if plus else "")
    return f"""
<section><h1>5. Tu primera previa, paso a paso</h1>
{steps(["<b>Carga el track.</b> Arrástralo a la ventana o pulsa <b>Abrir archivo</b> y elígelo.",
        "<b>Espera al análisis.</b> AutoPrevias detecta BPM, tonalidad, drops y secciones. Verás una barra de progreso; suele tardar unos segundos.",
        "<b>Revisa el resultado.</b> En la forma de onda aparecen coloreados los fragmentos que formarán la previa; las tarjetas muestran archivo, BPM, tonalidad, duración, nº de drops y duración estimada de la previa.",
        "<b>Elige la duración.</b> Pulsa <b>15 s (Teaser)</b>, <b>30 s (Promo)</b>, <b>60 s (Extended)</b> o <b>120 s / 2 min (Club)</b>, que es la opción por defecto. Los cortes se recalculan al instante." + extra,
        "<b>Escúchala (opcional).</b> Con el reproductor puedes oír la pista original y, tras generarla, la previa.",
        "<b>Ponle nombre y carpeta.</b> El nombre propuesto es <code>PREVIA - nombre del track</code>; puedes cambiarlo. Con <b>Cambiar</b> eliges la carpeta de destino.",
        "<b>Pulsa GENERAR PREVIA.</b> AutoPrevias construye la previa y la exporta.",
        "<b>Listo.</b> Aparece la tarjeta de éxito con los archivos creados. Pulsa <b>Abrir carpeta</b> para verlos o <b>Generar otra previa</b> para continuar."])}
{fig(im.get('02_analisis',''), 'Durante el análisis aparece una pantalla de progreso', 'mid')}
</section>
<section class="flow">
{fig(im.get('08_generada_anot',''), 'Previa generada: la tarjeta de éxito indica los archivos creados y la carpeta')}
{legend([("Tarjeta de éxito", "lista los archivos exportados y la carpeta donde se guardaron."),
         ("Abrir carpeta", "abre la carpeta de destino en el Finder / Explorador de archivos."),
         ("Generar otra previa", "vuelve a la pantalla de inicio para cargar otro track.")])}
{tip("Tras generar, el reproductor cambia solo a la pestaña <b>Previa Generada</b> para que la oigas enseguida. Con la pestaña <b>Pista Original</b> puedes volver a comparar (A/B).")}
{tip("Al terminar, el sistema te muestra una <b>notificación con el logo de AutoPrevias</b>. Si la pulsas, se abre la carpeta donde se ha guardado la previa.")}
</section>"""


def s_onda(ed: str, plus: bool, im: dict) -> str:
    return f"""
<section><h1>6. Forma de onda, cortes y reproductor</h1>
<h3>La forma de onda</h3>
{fig(im.get('z_waveform',''), 'Forma de onda con tres cortes activos')}
<p>La onda muestra todo el tema. Las <b>zonas coloreadas</b> son los fragmentos que formarán la previa; las oscuras están descartadas.</p>
<ul>
<li>Las <b>líneas verdes</b> marcan el inicio de cada corte y las <b>rojas</b>, el final. <b>Arrástralas</b> para ajustar qué parte entra en la previa.</li>
<li>La leyenda inferior indica el tipo de sección detectada: <b>Intro</b>, <b>Descanso</b>, <b>Subida</b>, <b>Drop</b> y <b>Outro</b>.</li>
<li>Con los botones <b>−</b> / <b>+</b> y el indicador <b>100%</b> haces zoom a la onda.</li>
<li>Haz clic en la onda para saltar a cualquier punto de la reproducción.</li>
</ul>
<h3>Nombres, orden y punto de inicio de los cortes</h3>
{fig(im.get('z_cortes_basic' if not plus else 'z_04_editor_cortes',''), 'Editor de cortes: nombres, orden y punto de inicio')}
<p>Cada corte se crea con su nombre: <b>Corte 1</b>, <b>Corte 2</b>, <b>Corte 3</b>… Ese nombre es fijo, aunque cambies el orden. Activa la casilla
<b>{'⚙ Personalizar Cortes &amp; BPM' if plus else '✂ Ordenar y mover cortes'}</b> para verlos en una tabla:</p>
<ul>
<li><b>▲ ▼</b> cambian el <b>orden</b> en que suenan en la previa (por ejemplo, que el drop suene primero). La primera columna indica el orden («1º · Corte 2»).</li>
<li><b>«La previa empieza»</b>: <b>⏮ Al inicio del tema</b> lleva el primer corte al principio de la canción y <b>⏺ A mitad del tema</b> lo coloca a la mitad (siempre ajustado a un compás). Para cualquier otro punto, <b>arrastra el primer corte</b> sobre la forma de onda o cambia sus segundos en la tabla.</li>
<li>Puedes <b>añadir</b> cortes, <b>quitarlos</b> con ✕ y escuchar cada uno con ▶ (suena desde su inicio hasta su final). Los mismos botones <b>▶ ✕</b> están sobre cada corte en la propia onda. Siempre queda al menos un corte. Los presets rápidos (<i>Estándar AI</i>, <i>Solo Drops</i>, <i>Intro corta 15 s</i>) recolocan los cortes de golpe.</li>
</ul>
{f"""<h3>Cómo empieza y cómo acaba la previa</h3>
{fig(im.get('z_startend',''), 'Tarjeta «Cómo empieza y cómo acaba la previa»: arranque y final a tu elección')}
<p>Justo encima del panel de exportación tienes esta tarjeta, siempre a la vista (no hace falta abrir ninguna pestaña). Elige cada extremo por separado:</p>
<table><tr><th>Opción</th><th>Qué hace</th></tr>
<tr><td><b>ARRANQUE · 🌀 Vinilo: de 0 al tempo</b></td><td>La previa arranca como un disco que coge velocidad: de 0 BPM al tempo del tema en los segundos que pongas (por defecto 1 s).</td></tr>
<tr><td><b>ARRANQUE · ▶ BPM originales desde el inicio</b></td><td>La previa empieza ya a los BPM originales, sin efecto.</td></tr>
<tr><td><b>FINAL · 🌀 Vinilo: frena hasta parar</b></td><td>La previa acaba como un disco que se para: del tempo a 0 BPM en los segundos que pongas (por defecto 1 s).</td></tr>
<tr><td><b>FINAL · ⏹ Acabar a los BPM originales</b></td><td>La previa acaba a los BPM originales, sin frenazo (queda solo el fundido final).</td></tr></table>
<p>Tu elección se guarda en los presets y en «Reabrir proyecto». En Basic la previa siempre arranca y acaba con el efecto de vinilo de 1 s.</p>""" if plus else ""}
<h3>Efectos en la onda (Flanger y Filter Sweep)</h3>
{fig(im.get('z_efectos',''), 'Efectos colocados sobre la onda: tarjetas para arrastrar, bloques en la onda y ajustes del efecto elegido')}
<p>Debajo de la onda están las <b>tarjetas de efecto</b>. Tú decides <b>qué efecto</b>, <b>dónde empieza</b> y <b>cuánto dura</b>; AutoPrevias no coloca nada por su cuenta.</p>
<table><tr><th>Efecto</th><th>Qué hace</th></tr>
<tr><td><b>🌀 Flanger</b></td><td>Flanger analógico estéreo con modulación LFO.</td></tr>
<tr><td><b>🌊 Filter Sweep ↗</b></td><td>Barrido de filtro hacia arriba: va quitando graves y sube la tensión (ideal antes de un drop).</td></tr>
<tr><td><b>🌊 Filter Sweep ↘</b></td><td>Barrido hacia abajo: el filtro se abre y los graves vuelven poco a poco.</td></tr></table>
{steps(["<b>Arrastra</b> una tarjeta hasta la onda y suéltala donde quieras que empiece (o <b>púlsala</b> para ponerla donde está el cursor de reproducción). Mientras arrastras ves el hueco que ocupará y se ajusta solo al pulso más cercano.",
        "<b>Muévelo</b> arrastrando el bloque y <b>estira sus bordes</b> para elegir la duración, igual que haces con los cortes. Si hay dos efectos a la vez, se colocan en dos filas.",
        "Con el bloque seleccionado, la fila de abajo te deja afinar el <b>inicio</b>, la <b>duración</b> y la <b>intensidad</b>. <b>Quitar</b> (o la tecla " + kbd('Supr') + ", o clic derecho sobre el bloque) lo borra; <b>Quitar todos</b> limpia la onda."])}
{tip("El efecto se queda pegado a su trozo del tema: si cambias el orden de los cortes, sigue sonando en ese mismo trozo. Si lo dejas <b>fuera de los cortes</b> verás el bloque apagado y no sonará. Los efectos pertenecen a este tema: no se guardan en los presets, pero sí en «Reabrir proyecto».", "tip")}
<h3>El reproductor</h3>
{fig(im.get('z_player',''), 'Reproductor con pestañas Pista Original / Previa Generada')}
<ul>
<li>Pestañas <b>Pista Original</b> y <b>Previa Generada</b>: cambia entre ambas para comparar.</li>
<li>Botones de retroceso, parada, reproducir/pausa, avance y repetición; vúmetro estéreo (L/R) y volumen.</li>
<li>Barra de progreso: arrástrala o haz clic para moverte por el tema.</li>
</ul>
<h3>Las tarjetas de información</h3>
{fig(im.get('z_stats',''), 'Tarjetas: archivo, BPM, clave Camelot, duración, drops y previa estimada')}
<p><b>BPM</b> y <b>Clave / Camelot</b> te sirven para mezclar y catalogar. Si el BPM detectado no es el correcto (por ejemplo, el doble o la mitad),
<b>haz doble clic en la tarjeta BPM</b> e introduce el valor real: la previa se recalcula con el nuevo tempo.</p>
<h3>Los presets de duración</h3>
{fig(im.get('z_presets',''), 'Presets de duración' + (' y presets guardados' if plus else ''))}
<table><tr><th>Preset</th><th>Para qué sirve</th></tr>
<tr><td><b>⚡ 15 s · Teaser</b></td><td>Avance muy corto para redes sociales o historias.</td></tr>
<tr><td><b>📻 30 s · Promo</b></td><td>Formato clásico de promoción para promotores y radios.</td></tr>
<tr><td><b>🚀 60 s · Extended</b></td><td>Más recorrido del tema, ideal para sellos y A&amp;R.</td></tr>
<tr><td><b>🔥 120 s · Club</b></td><td>Previa de dos minutos con intro, subida y drops. <i>Opción por defecto.</i></td></tr></table>
</section>"""


def s_export(ed: str, plus: bool, im: dict) -> str:
    if plus:
        fmts = ("<li><b>WAV 24 bit</b> — máxima calidad, con firma y carátula incrustadas.</li>"
                "<li><b>MP3 320 kbps</b> — ligero y compatible con todo (128 kbps en Modo promo).</li>"
                "<li><b>FLAC</b> — sin pérdidas y más pequeño que el WAV.</li>"
                "<li><b>Vídeo animado Radical Neón</b> — MP4 con tu carátula, analizador de espectro y destellos al ritmo del bombo, en formato vertical 9:16 (TikTok / Reels), cuadrado 1:1 o horizontal 16:9 (YouTube). Eliges la paleta de color y un texto de banner.</li>")
    else:
        fmts = ("<li><b>MP3 320 kbps</b> — máxima calidad MP3, con metadatos, compatible con cualquier reproductor.</li>"
                "<li><b>Vídeo animado Radical Neón</b> — MP4 hecho a partir de tu previa en MP3, en 9:16, 1:1 o 16:9. En la edición Basic lleva una marca de agua pequeña y termina con «Generado por AutoPrevias · Radical Records» o con un fundido a negro, como prefieras.</li>")
    banner_txt = " y un <b>texto de banner</b> (por ejemplo, <i>RADICAL RECORDS · PROMO EXCLUSIVA</i>)" if plus else ""
    video_section = (
        "<h3>Vídeo animado Radical Neón</h3>"
        "<p>Marca <b>🎬 Vídeo animado</b> y se exportará, junto al audio, un MP4 animado al estilo Radical Records: tu <b>carátula</b> con resplandor neón, "
        "el título, artista, BPM y tonalidad, un <b>analizador de espectro</b> que baila con la música y destellos que golpean con el bombo, con un golpe "
        "especial cuando entra el drop. Elige el formato —<b>9:16</b> (TikTok / Reels), <b>1:1</b> (Instagram) o <b>16:9</b> (YouTube)—, la <b>paleta de color</b>"
        + banner_txt + ".</p>"
        "<p>Todo el vídeo está en una sola tarjeta, <b>② Vídeo animado</b>, que aparece al marcar la casilla: elige el <b>formato</b> con los tres botones "
        "(<b>9:16 Vertical</b>, <b>1:1 Cuadrado</b> o <b>16:9 Horizontal</b>) y el <b>color</b>; después el <b>título</b>, el <b>final</b> y la <b>vista previa</b>.</p>"
        + fig(im.get('z_video', ''), 'Tarjeta «Vídeo animado»' + (' (edición Plus)' if plus else ' (edición Basic, con las opciones de Plus bloqueadas)')) +
        "<p>En el campo <b>Título</b> escribes el nombre que sale en el centro del vídeo; si lo dejas vacío se usa el nombre de la pista. Pulsa "
        "<b>👁 Vista previa</b> para ver unos segundos del vídeo (con sonido y a baja resolución) con tus ajustes antes de generarlo. Como el vídeo se hace "
        "a partir de la previa, al marcarlo el <b>MP3 se exporta siempre</b>.</p>"
    )
    if plus:
        video_section += (
            "<h3>El final del vídeo</h3>"
            "<p>La edición <b>Plus</b> no lleva marca de agua y te deja elegir cómo termina el vídeo con el selector <b>Final</b>:</p>"
            "<ul><li><b>Firma AutoPrevias + enlace</b> — cierre con el logo de Radical Records, «Generado por AutoPrevias · Radical Records» y el enlace de compra.</li>"
            "<li><b>Fundido a negro</b> — la imagen se oscurece suavemente al terminar.</li>"
            "<li><b>Sin cierre</b> — el vídeo acaba cortado a la vez que el audio.</li>"
            "<li><b>Mi imagen</b> — el vídeo termina con la imagen que elijas (tu logo, el cartel del sello…) y un texto opcional debajo.</li></ul>"
            "<h3>Estilo del vídeo: tu propia imagen</h3>"
            "<p>Con el selector <b>Look</b> eliges un aspecto listo con un clic: <b>Neón clásico</b>, <b>Foto + barras abajo</b>, <b>Foto + círculo en el centro</b>, "
            "<b>Foto y título</b> o <b>Solo la foto</b>. Con los looks de foto, AutoPrevias te pide tu imagen, o puedes <b>arrastrar una imagen sobre la tarjeta</b> del vídeo "
            "y se usa de fondo al instante (si la imagen es de otro formato válido, cambia solo a ese formato).</p>"
            "<p>Pulsa <b>⚙ Personalizar…</b> para ajustarlo todo, con una <b>vista previa en vivo</b> que cambia al tocar cada opción y que puedes ver en los tres formatos. Es una función exclusiva de Plus:</p>"
            "<ul><li><b>Fondo:</b> la plantilla Neón de siempre o <b>Mi imagen</b>, tu foto de fondo con un zoom lento. Puedes poner <b>una imagen distinta para cada formato</b> "
            "(9:16, 1:1 y 16:9) o una sola para todos, y elegir si se <b>recorta</b> para rellenar la pantalla o se muestra <b>entera sobre un fondo desenfocado</b>.</li>"
            "<li><b>Onda de sonido:</b> mostrarla o no; en <b>barras</b>, <b>línea</b> o <b>círculo</b>; abajo, en el centro o arriba; con los colores de la paleta Neón o en blanco.</li>"
            "<li><b>Textos:</b> elige cuáles se ven (título, artista, BPM y tonalidad, etiqueta «Previa exclusiva»), arriba, en el centro o abajo. Con <b>Solo la foto</b> se muestra únicamente tu imagen, sin textos, onda ni banner.</li>"
            "<li><b>Formato de la imagen:</b> los vídeos son <b>9:16, 1:1 o 16:9</b>. Si eliges una imagen con otra proporción, AutoPrevias te avisa de que el formato no es correcto y te muestra ejemplos de los tres formatos (botón <b>📐 Ver formatos válidos</b>); puedes cambiarla o usarla igualmente. Junto a cada imagen ves si el formato es correcto y si la resolución es baja.</li>"
            "<li><b>Final con tu imagen:</b> elige la imagen y un texto opcional; después selecciona «Final: mi imagen» en el selector de final.</li></ul>"
            "<p>La <b>👁 Vista previa</b> muestra el resultado con tus ajustes. Los ajustes se recuerdan y se guardan también en tus presets de estilo.</p>"
            + fig(im.get('z_video_imagen', ''), 'Tras arrastrar una imagen: el vídeo cambia a su formato (aquí 16:9) y aplica el look «Foto + barras abajo»')
            + fig(im.get('16_estilo_video', ''), 'Ventana «Estilo del vídeo» (solo Plus)', 'tiny')
        )
    else:
        video_section += (
            "<h3>Marca de agua y final (edición Basic)</h3>"
            "<p>En la edición <b>Basic</b> el vídeo lleva siempre una <b>marca de agua pequeña y translúcida</b> en la esquina inferior derecha "
            "(«Generado por Radical Records · AutoPrevias Basic»), que no se puede quitar. Con el selector <b>Final</b> eliges cómo termina: "
            "con el cierre «Generado por AutoPrevias · Radical Records» y el enlace de compra, o con un <b>fundido a negro</b>. "
            "La edición <b>Plus</b> elimina la marca de agua y te deja personalizar el vídeo con tu propia imagen, la onda de sonido y el final.</p>"
            "<p>En la tarjeta del vídeo verás esas opciones de Plus <b>bloqueadas con un candado</b> (🔒) para que sepas qué ganas al pasar a Plus; al pulsarlo se abre la página de compra.</p>"
        )
    return f"""
<section><h1>7. Ajustes de exportación</h1>
{fig(im.get('z_export',''), 'Panel de exportación' + (' de la edición Plus' if plus else ' de la edición Basic'))}
<h3>Nombre del archivo</h3>
<p>Por defecto, <code>PREVIA - nombre del track</code>. Escribe el que prefieras; AutoPrevias añade la extensión según el formato.</p>
<h3>Formatos de salida</h3>
<ul>{fmts}</ul>
{video_section}
<h3>Lo que verás en el panel</h3>
<p>El panel de exportación está ordenado en pasos: <b>① Nombre y formatos</b>, <b>② Vídeo animado</b>{' y <b>③ Opciones avanzadas</b> (efectos, Voice Drop, Modo promo y firma/carátula), que viene plegada para que el panel quede limpio y se abre sola en cuanto activas algo de ella' if plus else ''}.
Justo encima del botón <b>Generar previa</b>, una línea de resumen te dice qué se va a crear (formatos, vídeo, duración de la previa y carpeta de destino) para que no haya sorpresas.</p>

{'' if plus else tip('La edición Plus añade WAV 24 bit, FLAC, vídeo animado sin marca de agua, con tu propia imagen y el final a tu elección, firma y carátula personalizadas, efectos de estudio y mucho más. Mira el capítulo «Pasar a la edición Plus».')}
<h3>Carpeta de destino</h3>
<p>Pulsa <b>Cambiar</b> para elegir dónde se guardan las previas y <b>Abrir</b> para ver esa carpeta en el Finder / Explorador. La carpeta se recuerda para la próxima vez.</p>
<h3>Seed y «Regenerar con seed»</h3>
<p>La <b>seed</b> (semilla) controla las pequeñas decisiones aleatorias del motor. Con la <b>misma seed</b> obtienes <b>la misma previa</b>; cambia la seed
(botón 🎲 para una al azar) y pulsa <b>⟳ Regenerar con seed</b> para obtener otra variación. Así puedes repetir exactamente una previa que te gustó.</p>
<h3>Qué se guarda dentro del archivo</h3>
<p>Las previas MP3{' y WAV' if plus else ''} incluyen <b>etiquetas de metadatos</b> (título{', artista, sello, álbum, género, comentario' if plus else ''}) y la <b>carátula</b> de Radical Records.</p>
</section>"""


def s_plus_editor(im: dict) -> str:
    return f"""
<section><h1>8. Editor avanzado: cortes, BPM y estructura</h1>
<p><span class="badge plus">PLUS</span> Activa la casilla <b>⚙ Personalizar Cortes &amp; BPM</b> para abrir el editor, con tres pestañas.</p>
<h3>Pestaña «Editor de Cortes»</h3>
{fig(im.get('z_04_editor_cortes_anot',''), 'Editor de cortes')}
{legend([("Añadir corte", "crea un fragmento nuevo en la previa."),
         ("Tabla de cortes", "ajusta los segundos exactos de cada corte; ▶ lo escucha en la pista original y 🗑 lo elimina."),
         ("Resumen", "número de cortes, duración total y duración estimada de la previa; se actualiza mientras editas.")])}
<p>Además, puedes <b>arrastrar los marcadores</b> verdes (inicio) y rojos (fin) directamente sobre la forma de onda para mover o recortar los fragmentos.</p>
<ul>
<li><b>Presets rápidos:</b> <i>Estándar AI</i> (la previa recomendada), <i>Solo Drops</i> (va directa a los drops con máxima energía) e <i>Intro corta 15 s</i>.</li>
<li>Los botones <b>📍</b> toman la posición actual del reproductor como inicio o fin del corte.</li>
<li><b>Nombres y orden:</b> cada corte tiene un nombre fijo («Corte 1», «Corte 2»…) y los botones <b>▲ ▼</b> cambian el orden en que suenan. <b>⏮ Al inicio del tema</b> y <b>⏺ A mitad del tema</b> colocan el primer corte donde quieras que empiece la previa (ajustado a un compás); también puedes arrastrarlo sobre la onda. Esta parte también la tiene la edición Basic.</li>
</ul>
</section>
<section>
<h3>Pestaña «Variación de BPM»</h3>
{fig(im.get('z_05_editor_bpm_anot',''), 'Variación de tempo: modo automático y manual')}
{legend([("Automático", "micro-variaciones orgánicas de tempo según la seed. Suena natural pero impide mezclar la previa sin permiso."),
         ("Manual (Presets DJ)", "tú decides las subidas de BPM."),
         ("Curva de tempo", "muestra cómo cambia la velocidad a lo largo de la previa.")])}
<p>Es la <b>protección anti-retoque por tempo</b>: al variar ligeramente la velocidad, nadie puede pinchar ni sincronizar la previa con otro tema sin pasar por ti.
En modo manual dispones de presets: <b>+5 BPM en Drops</b>, <b>+8 % Rampa</b>, <b>±4 BPM Vaivén</b>, <b>+3 BPM Fijo</b> y <b>0 BPM</b>, además de <b>➕ Momento</b> para añadir cambios exactos.</p>
<h3>Pestaña «Estructura Musical»</h3>
{fig(im.get('z_06_estructura',''), 'Estructura detectada: tipo, inicio, fin, duración, LUFS y pico', 'mid')}
<p>Tabla informativa con todas las secciones detectadas, su duración, el nivel <b>LUFS</b> y el pico en dBFS de cada una.</p>
</section>"""


def s_plus_fx(im: dict) -> str:
    return f"""
<section><h1>9. Efectos, Voice Drop y Modo promo</h1>
<p><span class="badge plus">PLUS</span></p>
<h3>Master LUFS</h3>
<table><tr><th>Opción</th><th>Qué hace</th></tr>
<tr><td><b>🔊 Master LUFS</b></td><td>Normalización y limitador transparente a <b>−9 LUFS</b> (nivel de club / Beatport).</td></tr></table>
{tip("Flanger y Filter Sweep ya no son casillas automáticas: se arrastran sobre la forma de onda y eliges tú dónde suenan (capítulo 6, «Efectos en la onda»). Están disponibles en Basic y en Plus.", "tip")}
<h3>Voice Drop (tu firma de voz)</h3>
<p>Superpone tu firma de voz o <i>jingle</i> de DJ sobre la previa.</p>
{steps(["Pulsa <b>🎙 Voice Drop…</b> y elige tu audio de firma (WAV, MP3…).", "Elige el momento: <b>📍 Pre-Drop</b> (justo antes del primer drop), <b>📍 Intro</b> o <b>🎯 Manual</b>.",
        "En modo manual arrastra el <b>marcador dorado</b> por la forma de onda hasta el punto exacto.", "Verás «✓ Firma … 1.6 s» cuando esté cargada. Puedes cambiarla con <b>Cambiar Drop</b>."])}
<h3>Modo promo antifugas</h3>
{fig(im.get('z_export_promo',''), 'Modo promo activado: la firma se repite cada 20 s y la salida es MP3 128 kbps')}
<p>Pensado para enviar previas a promotores sin que el audio pueda reutilizarse sin tu firma:</p>
<ul>
<li>Repite tu firma de voz <b>cada pocos segundos</b> (por defecto, cada 20 s) a lo largo de toda la previa.</li>
<li>Exporta <b>solo en MP3 de 128 kbps</b>.</li>
<li>Añade al comentario del archivo el texto <i>«PROMO — NO DISTRIBUIR / NOT FOR DISTRIBUTION»</i>.</li>
</ul>
{tip("El Modo promo necesita una firma cargada con <b>Voice Drop…</b>. Si falta, AutoPrevias te avisará antes de generar.", "warn")}
</section>"""


def s_plus_firma(im: dict) -> str:
    return f"""
<section><h1>10. Firma, carátula y presets propios</h1>
<p><span class="badge plus">PLUS</span></p>
<h3>Firma y carátula personalizadas</h3>
{fig(im.get('z_firma',''), 'Tarjeta de firma y carátula')}
<p>Rellena <b>Artista / DJ</b>, <b>Sello</b>, <b>Álbum</b>, <b>Género</b> y <b>Comentario</b>: se incrustan como metadatos en tus previas. Pulsa o arrastra una
imagen sobre la <b>carátula</b> para personalizarla (con <b>Restablecer portada</b> vuelves a la de Radical Records). Marca
<b>«Guardar firma y carátula como predeterminada»</b> para que se carguen solas en la próxima sesión.</p>
<h3>🖋 Firmar un tema entero</h3>
{fig(im.get('17_firmar_tema',''), 'Ventana «Firmar tema entero»', 'tiny')}
<p>El botón <b>🖋 Firmar tema</b> de la cabecera abre una ventana aparte pensada para <b>canciones completas, no previas</b>. Solo le mete la <b>carátula y las etiquetas</b>:
sin masterización, sin efectos y sin tocar el volumen ni la duración. El audio queda <b>exactamente igual</b>.</p>
{steps(["<b>Arrastra el tema</b> (o varios) a la ventana, o pulsa la zona para elegirlos.", "Elige la <b>carátula</b> (si guardaste una en «Firma y carátula», aparece sola) y rellena artista, sello, álbum, género y comentario.",
        "Elige el formato: <b>FLAC</b> (sin pérdidas, recomendado) o <b>WAV</b> (sin comprimir).", "Pulsa <b>🖋 Firmar</b>. Los temas firmados se guardan en la carpeta <b>Firmados</b> (puedes cambiarla) y se muestra una notificación; púlsala para abrir la carpeta."])}
<ul>
<li>Se conservan la <b>frecuencia de muestreo</b> y los <b>bits</b> del original (hasta 24 bits).</li>
<li>Si el original es un MP3 o M4A, se guarda sin perder nada más, pero <b>no gana calidad</b>.</li>
<li>Nunca se pisa tu archivo original: si ya existe uno con ese nombre, se añade «(2)».</li>
</ul>
<h3>Mis presets</h3>
{fig(im.get('z_presets_guardados',''), 'Barra de presets con un preset guardado', 'mid')}
<p>Guarda toda tu configuración como un <b>preset con nombre</b> y aplícala con un clic:</p>
{steps(["Deja todo como te gusta (formatos, efectos, firma, estilo…).", "Pulsa <b>💾 Guardar…</b>, escribe un nombre (por ejemplo «Radical Main») y elige si el preset incluye la <b>firma</b> y el <b>estilo</b>.",
        "Para usarlo, elígelo en el desplegable <b>Mis presets</b> y pulsa <b>✓ Aplicar</b>.", "Para borrarlo, selecciónalo y pulsa 🗑."])}
{fig(im.get('15_guardar_preset',''), 'Diálogo para guardar un preset', 'tiny')}
<p class="small">Los presets se guardan como archivos en tu carpeta de usuario, así que puedes copiarlos a otro ordenador.</p>
</section>"""


def s_plus_lote(im: dict) -> str:
    return f"""
<section><h1>11. Lote, carpeta vigilada y Recientes</h1>
<p><span class="badge plus">PLUS</span></p>
<h3>📁 Modo Lote</h3>
{fig(im.get('14_lote',''), 'Procesamiento por lote', 'mid')}
<p>Procesa muchas pistas de una vez con los mismos ajustes: añade archivos, revisa la lista y lanza el proceso. AutoPrevias genera una previa por cada track y te muestra el progreso de cada uno.</p>
<h3>👁 Vigilar Carpeta</h3>
<p>Elige una carpeta y AutoPrevias <b>genera la previa automáticamente</b> cada vez que cae un tema nuevo en ella (los archivos que ya estaban se ignoran). Es ideal para dejar el ordenador del estudio trabajando. Pulsa de nuevo el botón para desactivarlo.</p>
<h3>🕒 Recientes</h3>
{fig(im.get('13_recientes',''), 'Historial: previas generadas y pistas abiertas', 'mid')}
<p>Dos pestañas:</p>
<ul>
<li><b>Previas generadas</b>: cada previa que has creado, con fecha, duración y si era modo promo. Con <b>Reabrir proyecto</b> se vuelve a cargar el track con <b>los mismos ajustes y la misma seed</b>, para repetir o retocar la previa.</li>
<li><b>Pistas abiertas</b>: los últimos tracks que has cargado, para abrirlos otra vez con un clic.</li>
</ul>
</section>"""


def s_basic_recientes(im: dict) -> str:
    return f"""
<section><h1>8. Historial de pistas recientes</h1>
<p>El botón <b>🕒 Recientes</b> de la cabecera abre la lista de los últimos tracks que has cargado, para volver a abrirlos con un clic sin buscarlos en el disco.</p>
{fig(im.get('13_recientes',''), 'Pistas abiertas recientemente', 'mid')}
</section>"""


def s_basic_upsell() -> str:
    return f"""
<section><h1>9. Pasar a la edición Plus</h1>
<p>Si necesitas más control, la <b>edición Plus</b> de AutoPrevias añade:</p>
<div class="cols">
<div class="card"><h4>🎚 Más formatos</h4><p>Exportación <b>WAV 24 bit</b> y <b>FLAC</b>, y <b>vídeo animado sin marca de agua</b> (MP4 9:16, 1:1 o 16:9) con tu propia imagen de fondo (una por formato), onda de sonido en barras, línea o círculo y el final a tu elección: firma AutoPrevias, fundido a negro, tu imagen o sin cierre.</p></div>
<div class="card"><h4>✂ Editor avanzado</h4><p>Controla la variación de BPM, elige si la previa arranca con el efecto de vinilo o a los BPM originales y consulta la estructura musical detallada.</p></div>
<div class="card"><h4>🖋 Firmar temas enteros</h4><p>Mete carátula y etiquetas a canciones completas y guárdalas en FLAC o WAV a máxima calidad, sin tocar el audio.</p></div>
<div class="card"><h4>🔊 Master LUFS</h4><p>Nivel de club (−9 LUFS) con limitador transparente. Los efectos Flanger y Filter Sweep ya los tienes también en Basic.</p></div>
<div class="card"><h4>🎙 Voice Drop</h4><p>Superpón tu firma de voz o jingle en el momento exacto.</p></div>
<div class="card"><h4>🛡 Modo promo antifugas</h4><p>Firma repetida y MP3 128 kbps para enviar previas sin riesgo de reutilización.</p></div>
<div class="card"><h4>🏷 Firma y carátula</h4><p>Artista, sello, álbum, género, comentario y portada propia en los metadatos.</p></div>
<div class="card"><h4>💾 Presets y historial</h4><p>Guarda tus ajustes con nombre y reabre cualquier previa con los mismos parámetros.</p></div>
<div class="card"><h4>📁 Lote y carpeta vigilada</h4><p>Procesa decenas de tracks seguidos o deja que AutoPrevias trabaje solo.</p></div>
</div>
{tip("Para pasar a Plus, compra la licencia Plus en la tienda de Radical Records ({L.short(L.PLUS_URL)}), descarga el instalador <b>Plus</b> y actívalo con la nueva clave. Puedes tener Basic y Plus instalados a la vez.", "tip")}
</section>"""


def s_updates(ed: str, plus: bool, im: dict, n: int) -> str:
    return f"""
<section><h1>{n}. Actualizaciones, licencia e idioma</h1>
<h3>Actualizaciones automáticas</h3>
<p>AutoPrevias comprueba al arrancar si hay una versión nueva. Si la hay, aparece un aviso en la parte inferior de la ventana: púlsalo para abrir el asistente de actualización.</p>
{fig(im.get('12_actualizacion',''), 'Asistente de actualización (los datos del ejemplo son ficticios)', 'tiny')}
{steps(["Lee las novedades de la versión.", "Pulsa <b>Descargar e instalar</b>: AutoPrevias descarga el instalador directamente en tu carpeta de <b>Descargas</b>, comprueba su integridad (SHA-256) y lo abre.",
        "Sigue el instalador como la primera vez; tus ajustes y tu licencia se conservan.",
        "Si prefieres esperar, pulsa <b>Omitir esta versión</b> y no te volverá a avisar de esa."])}
<h3>Recorrido de bienvenida (solo la primera vez)</h3>
<p>La primera vez que abres AutoPrevias en un equipo nuevo, tras activar la licencia, aparece un aviso de bienvenida con dos botones: <b>Hacer el recorrido</b> u <b>Omitir</b>. No se vuelve a preguntar nunca más.</p>
{fig(im.get('01c_recorrido',''), 'El recorrido oscurece la ventana y resalta cada parte de la app real con una explicación', 'mid')}
<ul>
<li>Son unos 5 minutos: te enseña la pantalla de inicio, carga una <b>pista de ejemplo</b> sintética y recorre todo el panel de resultados (forma de onda, efectos arrastrables, reproductor, duración, formatos, vídeo animado, carpeta y botón Generar).</li>
<li>Avanza con <b>Siguiente</b> (o las teclas <b>→</b>, <b>Intro</b> o <b>Espacio</b>), vuelve con <b>Atrás</b> (<b>←</b>) y sal cuando quieras con <b>Omitir recorrido</b> o <b>Esc</b>.</li>
<li>No guarda nada: la pista de ejemplo no aparece en Recientes y tus ajustes quedan como estaban.</li>
<li>Si quieres repetirlo, pulsa <b>Ver recorrido de bienvenida</b> en la ventana <b>⚙ Licencia</b>.</li>
</ul>
<h3>Ventana «⚙ Licencia»</h3>
{fig(im.get('11_licencia',''), 'Versión, licencia e idioma', 'tiny')}
<ul>
<li>Muestra la <b>versión</b>, la <b>edición</b> y el <b>estado de la licencia</b>: fecha de última verificación y hasta cuándo es válida sin conexión.</li>
<li><b>Buscar actualizaciones</b> lanza la comprobación al momento.</li>
<li><b>Rendimiento</b> elige cuántos recursos del equipo usa AutoPrevias al analizar y generar vídeo: <b>Automático</b> (recomendado; se adapta a tu equipo y deja un núcleo libre para que la app siga fluida), <b>Ahorro de recursos</b> (portátil con batería, equipo antiguo u otros programas abiertos) o <b>Máximo rendimiento</b> (todos los núcleos, para terminar antes). Debajo ves cuántos núcleos y cuánta memoria detecta la app.</li>
<li><b>Desactivar licencia en este equipo</b> libera la clave en el servidor para poder usarla en otro ordenador (necesita conexión).</li>
<li><b>Idioma</b>: Español (por defecto) o English. También puedes alternarlo con el botón <b>ES / EN</b> de la cabecera; todo se traduce al instante.</li>
</ul>
</section>"""


def s_atajos(n: int) -> str:
    return f"""
<section class="flow"><h2>{n}. Atajos de teclado</h2>
<p>Funcionan cuando no estás escribiendo en un campo de texto.</p>
<table><tr><th>Tecla</th><th>Acción</th></tr>
<tr><td>{kbd('Espacio')}</td><td>Reproducir / pausa</td></tr>
<tr><td>{kbd('←')} {kbd('→')}</td><td>Retroceder / avanzar 5 segundos</td></tr>
<tr><td>{kbd('Inicio')} · {kbd('0')}</td><td>Volver al principio</td></tr>
<tr><td>{kbd('Esc')}</td><td>Detener</td></tr>
<tr><td>{kbd('M')}</td><td>Silenciar / activar sonido</td></tr>
<tr><td>{kbd('Supr')}</td><td>Borrar el efecto seleccionado en la onda</td></tr></table>
</section>"""


def s_faq(ed: str, plus: bool, n: int) -> str:
    cap = "Plus" if plus else "Basic"
    return f"""
<section class="flow"><h2>{n}. Solución de problemas</h2>
<table><tr><th>Problema</th><th>Solución</th></tr>
<tr><td>macOS dice que la app «no se puede abrir» o «está dañada»</td><td>Ejecuta en Terminal <code>xattr -cr /Applications/AutoPrevias.app</code> y vuelve a abrirla.</td></tr>
<tr><td>Windows muestra «Windows protegió su PC»</td><td>Pulsa <b>Más información → Ejecutar de todas formas</b>.</td></tr>
<tr><td>«Clave no válida» al activar</td><td>Comprueba que has copiado la clave completa, sin espacios, y que es de la edición {cap}. Necesitas Internet. Si persiste, escríbenos.</td></tr>
<tr><td>«Esta clave es de AutoPrevias Basic/Plus y estás usando…»</td><td>Tu clave corresponde a la otra edición. Descarga e instala la edición que compraste; la clave no se queda ligada a ningún equipo.</td></tr>
<tr><td>El análisis o el vídeo tardan mucho, o el equipo va justo</td><td>Abre <b>⚙ Licencia → Rendimiento</b>. <b>Automático</b> se adapta a tu equipo; <b>Máximo rendimiento</b> usa todos los núcleos para terminar antes; <b>Ahorro de recursos</b> usa pocos si trabajas con otros programas o con batería. Cierra otros programas pesados mientras generas el vídeo.</td></tr>
{"<tr><td>«El formato de la imagen no es correcto»</td><td>Los vídeos son 9:16, 1:1 o 16:9. Cambia la imagen por una con esa proporción (pulsa <b>📐 Ver formatos válidos</b> para ver ejemplos) o elige «Imagen entera con fondo desenfocado».</td></tr>" if plus else ""}
<tr><td>«Esta licencia ya está activada en otro equipo»</td><td>Tu clave solo puede estar en un ordenador. Desactívala en el otro (<b>⚙ Licencia → Desactivar licencia en este equipo</b>) o escribe a soporte si ese equipo ya no está disponible.</td></tr>
<tr><td>Me dice que necesita conexión para verificar la licencia</td><td>Han pasado más de 14 días sin verificarla: conéctate a Internet y pulsa <b>Reintentar</b>. No hace falta volver a escribir la clave.</td></tr>
<tr><td>El BPM detectado es el doble o la mitad</td><td>Haz doble clic en la tarjeta <b>BPM</b> y escribe el valor real.</td></tr>
<tr><td>Un efecto que puse en la onda no suena</td><td>Solo suena dentro de los cortes de la previa. Si el bloque se ve apagado está fuera de ellos: muévelo sobre un corte o amplía el corte.</td></tr>
<tr><td>La previa no empieza donde quiero</td><td>Arrastra los marcadores verdes/rojos en la forma de onda{' o usa el Editor de Cortes' if plus else ' o elige otro preset de duración'}.</td></tr>
<tr><td>No oigo nada al reproducir</td><td>Revisa el volumen del reproductor y que no esté silenciado (tecla {kbd('M')}) y el dispositivo de salida de tu sistema.</td></tr>
<tr><td>No encuentro mis previas</td><td>Pulsa <b>Abrir</b> junto a «Carpeta» para ver la carpeta de destino; puedes cambiarla con <b>Cambiar</b>.</td></tr>
<tr><td>La actualización automática falla</td><td>Pulsa <b>Reintentar</b> o descarga de nuevo el instalador desde tu compra en Payhip ({L.short(L.url_for(ed))}).</td></tr></table>
</section>"""


def s_soporte(n: int, ed: str) -> str:
    return f"""
<section class="flow"><h2>{n}. Soporte y licencias de terceros</h2>
<div class="card"><h4>📧 Soporte técnico</h4><p>Escríbenos a <b>{SUPPORT}</b> indicando tu sistema operativo, la versión de AutoPrevias ({VERSION}) y qué ocurre. Si es posible, adjunta una captura de pantalla.</p></div>
<p></p>
<p class="small">AutoPrevias utiliza componentes de código abierto, entre ellos <b>pedalboard</b> (GPL-3) y <b>Rubber Band</b> (GPL), además de PySide6, librosa, NumPy y otras bibliotecas.
Si necesitas los textos completos de sus licencias, solicítalos a soporte y te los enviamos.</p>
<p class="small">© Radical Records. AutoPrevias {VERSION}. Todos los derechos reservados. Este manual corresponde a la versión {VERSION}
de la edición {ed.capitalize()}.</p>
</section>"""


def build_html(ed: str, im: dict) -> str:
    plus = ed == "plus"
    parts = [indice(plus), s_intro(ed, plus), s_install(ed), s_activ(ed, im),
             s_interfaz(ed, plus, im), s_primera(ed, plus, im), s_onda(ed, plus, im), s_export(ed, plus, im)]
    if plus:
        parts += [s_plus_editor(im), s_plus_fx(im), s_plus_firma(im), s_plus_lote(im)]
        n = 12
    else:
        parts += [s_basic_recientes(im), s_basic_upsell()]
        n = 10
    parts += [s_updates(ed, plus, im, n), s_atajos(n + 1), s_faq(ed, plus, n + 2), s_soporte(n + 3, ed)]
    body = "\n".join(parts)
    return _wrap(body, ed)


def _wrap(body: str, ed: str, cover: bool = False) -> str:
    extra = '@page { margin: 0; }' if cover else ''
    return f"<!doctype html><html lang='es'><head><meta charset='utf-8'><title>AutoPrevias {ed.capitalize()} — Manual</title><style>{CSS}{extra}</style></head><body>{body}</body></html>"


def render_pdf(html_path: Path, pdf_path: Path, ed: str, cover: bool = False):
    from playwright.sync_api import sync_playwright
    exe = os.environ.get("CHROMIUM_PATH") or next(
        (p for p in ("/opt/pw-browsers/chromium", "/usr/bin/chromium", "/usr/bin/google-chrome") if Path(p).exists()), None)
    cap = ed.capitalize()
    header = "<div style='font-size:7.5pt;width:100%;padding:0 17mm;color:#8a8fa3;font-family:Inter,Arial'>RADICAL RECORDS · AutoPrevias — Manual de usuario</div>"
    footer = (f"<div style='font-size:7.5pt;width:100%;padding:0 17mm;color:#8a8fa3;font-family:Inter,Arial;display:flex;justify-content:space-between'>"
              f"<span>Edición {cap} · v{VERSION}</span><span>Página <span class='pageNumber'></span> de <span class='totalPages'></span></span></div>")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        pg = b.new_page()
        pg.goto(html_path.as_uri())
        pg.wait_for_load_state("networkidle")
        if cover:
            pg.pdf(path=str(pdf_path), format="A4", print_background=True, prefer_css_page_size=True)
        else:
            pg.pdf(path=str(pdf_path), format="A4", print_background=True, display_header_footer=True,
                   header_template=header, footer_template=footer, prefer_css_page_size=True)
        b.close()


def merge(cover_pdf: Path, body_pdf: Path, out: Path):
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter()
    for f in (cover_pdf, body_pdf):
        for page in PdfReader(str(f)).pages:
            w.add_page(page)
    with open(out, "wb") as fh:
        w.write(fh)


def set_metadata(pdf: Path, ed: str):
    from pypdf import PdfReader, PdfWriter
    r = PdfReader(str(pdf)); w = PdfWriter(clone_from=r)
    w.add_metadata({"/Title": f"AutoPrevias {ed.capitalize()} {VERSION} — Manual de usuario",
                    "/Author": "Radical Records", "/Subject": f"Manual de usuario de AutoPrevias {VERSION} (edición {ed.capitalize()})",
                    "/Keywords": f"AutoPrevias {VERSION}; manual; {ed}", "/Creator": "Radical Records", "/Producer": "Radical Records"})
    with open(pdf, "wb") as f:
        w.write(f)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    editions = args or ["basic", "plus"]
    do_capture = "--no-capture" not in sys.argv
    MANUAL.mkdir(parents=True, exist_ok=True)
    for ed in editions:
        if do_capture:
            print(f"== Capturando {ed} ==")
            subprocess.run([sys.executable, str(ROOT / "scripts" / "manual" / "capture.py"), ed], check=True)
        tmp = Path(tempfile.mkdtemp(prefix="ap_manual_"))
        im = prep_images(ed, tmp / "img")
        h = tmp / "manual.html"
        h.write_text(build_html(ed, im), encoding="utf-8")
        pdf = MANUAL / f"AutoPrevias-Manual-{ed.capitalize()}.pdf"
        hc = tmp / "cover.html"
        hc.write_text(_wrap(portada(ed, im), ed, cover=True), encoding="utf-8")
        render_pdf(hc, tmp / "cover.pdf", ed, cover=True)
        render_pdf(h, tmp / "body.pdf", ed)
        merge(tmp / "cover.pdf", tmp / "body.pdf", pdf)
        set_metadata(pdf, ed)
        print(f"✔ {pdf.relative_to(ROOT)}  ({pdf.stat().st_size/1e6:.1f} MB)")
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
