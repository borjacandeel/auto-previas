"""
AutoPrevias — Temas de la aplicación (Original · One Dark · Claro) y espacio para más en el futuro.

Cómo funciona (sin tocar las ~350 definiciones de color de la interfaz):
· La interfaz está dibujada con la paleta «Original» (oscura, con acento carmesí). Cada tema es una TRANSFORMACIÓN de esa
  paleta: los grises (fondos, bordes, textos) se reasignan a los grises del tema y el acento rojo se cambia por el acento del
  tema. Los demás colores (verdes, amarillos…) se conservan o se ajustan para tener contraste.
· `install(clave)` se llama UNA vez, al arrancar y antes de importar la interfaz: sustituye `QColor` por una versión que pasa
  cada color por el tema y envuelve `setStyleSheet` / `QLabel.setText` para hacer lo mismo con las hojas de estilo y el HTML.
  Con el tema «Original» no se instala nada (cero coste, comportamiento idéntico al de siempre).
· Cambiar de tema pide reiniciar la aplicación (así TODO queda coherente: hojas de estilo, onda, reproductor…).

Para añadir un tema nuevo: crear un `Theme` en `THEMES` con sus anclas de grises (luminancia original → color del tema) y su acento.
"""
from __future__ import annotations

import colorsys
import re
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

DEFAULT_THEME = "original"


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    description: str
    dark: bool = True
    # anclas de los grises: (luminancia 0-1 en la paleta original, color #rrggbb del tema), de oscuro a claro
    anchors: tuple = field(default_factory=tuple)
    accent_hue: Optional[float] = None          # tono (0-360) que sustituye al rojo de la marca; None = se conserva
    accent_sat: float = 1.0                     # factor de saturación del acento
    accent_light: float = 0.0                   # ajuste de luminosidad del acento (-1..1)
    swatch: tuple = ("#0a0b0e", "#181b22", "#ff1e38", "#eceef2")    # fondo, tarjeta, acento, texto (para la vista previa)


THEMES: dict = {
    "original": Theme("original", "Original", "El oscuro de siempre, con acento carmesí.", True, swatch=("#0a0b0e", "#181b22", "#ff1e38", "#eceef2")),
    "onedark": Theme(
        "onedark", "One Dark", "Gris pizarra suave inspirado en Atom One Dark, con acento azul.", True,
        anchors=((0.000, "#1b1f27"), (0.015, "#1e2229"), (0.040, "#21252b"), (0.062, "#282c34"), (0.075, "#2a2f38"),
                 (0.085, "#2c313a"), (0.100, "#2f343e"), (0.135, "#353b45"), (0.150, "#3b414d"), (0.180, "#404755"),
                 (0.250, "#4b5263"), (0.350, "#5c6370"), (0.560, "#8a91a0"), (0.690, "#abb2bf"), (0.780, "#bcc2cf"),
                 (0.930, "#d7dae0"), (1.000, "#ffffff")),
        accent_hue=207.0, accent_sat=0.80, accent_light=0.05, swatch=("#21252b", "#2c313a", "#61afef", "#d7dae0")),
    "light": Theme(
        "light", "Claro", "Fondo blanco roto para trabajar con mucha luz, con el mismo acento carmesí.", False,
        anchors=((0.000, "#f6f7fa"), (0.015, "#f6f7fa"), (0.040, "#f1f3f7"), (0.062, "#ffffff"), (0.075, "#fbfbfd"),
                 (0.085, "#f7f8fb"), (0.100, "#f0f2f6"), (0.135, "#e8ebf1"), (0.150, "#dde1ea"), (0.180, "#d3d8e2"),
                 (0.250, "#c2c8d6"), (0.350, "#7b8397"), (0.560, "#5a6275"), (0.690, "#434b5c"), (0.780, "#303747"),
                 (0.930, "#1b2030"), (1.000, "#ffffff")),
        accent_hue=None, swatch=("#f1f3f7", "#ffffff", "#e8203a", "#1b2030")),
}

_current: str = DEFAULT_THEME
_installed = False
_originals: dict = {}


def current() -> str:
    return _current


def theme_keys() -> list:
    return list(THEMES)


def get(key: Optional[str]) -> Theme:
    return THEMES.get(key or DEFAULT_THEME, THEMES[DEFAULT_THEME])


# ── transformación de colores ────────────────────────────────────────────────────────────────────────
def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lum(r: int, g: int, b: int) -> float:
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def _interp(anchors: tuple, y: float) -> tuple:
    pts = [(a, _hex_to_rgb(c)) for a, c in anchors]
    if y <= pts[0][0]:
        return pts[0][1]
    for (y0, c0), (y1, c1) in zip(pts, pts[1:]):
        if y <= y1:
            t = 0.0 if y1 == y0 else (y - y0) / (y1 - y0)
            return tuple(int(round(c0[i] + (c1[i] - c0[i]) * t)) for i in range(3))
    return pts[-1][1]


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


@lru_cache(maxsize=8192)
def transform_rgb(theme_key: str, r: int, g: int, b: int, a: int = 255) -> tuple:
    """(r, g, b) de la paleta original → (r, g, b) del tema."""
    th = get(theme_key)
    if th.key == DEFAULT_THEME:
        return r, g, b
    y = _lum(r, g, b)
    if a < 255 and y < 0.10:                       # negros translúcidos
        if th.dark or a >= 200:                    # (en oscuro, siempre; y las etiquetas casi opacas de la onda, en todos)
            return r, g, b
        return 255, 255, 255                       # un velo para «apagar» una zona: en un tema claro es blanco
    hh, ll, ss = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    hdeg = hh * 360.0
    hi, lo = max(r, g, b), min(r, g, b)
    sat_hsv = 0.0 if hi == 0 else (hi - lo) / hi
    # grises de la paleta original (fondos, bordes y textos): neutros o con un ligero tinte azulado
    if sat_hsv < 0.34 or (190 <= hdeg <= 260 and sat_hsv < 0.5 and hi - lo < 60):
        return _interp(th.anchors, y)
    red_family = hdeg >= 335 or hdeg <= 18         # el rojo de la marca y sus tonos oscuros (estados «seleccionado»…)
    if th.dark:
        if red_family and th.accent_hue is not None:
            ss2 = _clamp01(ss * th.accent_sat)
            if ll > 0.25:
                ll2 = _clamp01(ll + th.accent_light)
            else:                                  # fondos teñidos oscuros: se suben un poco, como los grises del tema
                ll2 = _clamp01(ll + 0.10 * (1 - ll / 0.25))
            rr, gg, bb = colorsys.hls_to_rgb(th.accent_hue / 360.0, ll2, ss2)
            return int(round(rr * 255)), int(round(gg * 255)), int(round(bb * 255))
        return r, g, b
    # tema claro
    if ll < 0.30:                                  # fondos teñidos oscuros (p. ej. el rojo oscuro de «seleccionado») → tinte pálido
        rr, gg, bb = colorsys.hls_to_rgb(hh, 0.95 - ll * 0.35, _clamp01(ss * 0.75))
    elif ll > 0.62:                                # colores claros pensados para fondo oscuro (lilas, amarillos…) → más oscuros
        rr, gg, bb = colorsys.hls_to_rgb(hh, max(0.32, ll * 0.58), _clamp01(ss * 0.95))
    else:                                          # acentos de tono medio: un punto más oscuros para que se lean sobre blanco
        rr, gg, bb = colorsys.hls_to_rgb(hh, ll * 0.86, ss * 0.92)
    return int(round(rr * 255)), int(round(gg * 255)), int(round(bb * 255))


def transform_hex(h: str, theme_key: Optional[str] = None) -> str:
    """'#rrggbb' o '#aarrggbb' (formato de Qt) → el mismo color en el tema."""
    key = theme_key or _current
    body = h.lstrip("#")
    if len(body) == 3:
        body = "".join(c * 2 for c in body)
    if len(body) == 8:
        a = int(body[0:2], 16)
        r, g, b = transform_rgb(key, int(body[2:4], 16), int(body[4:6], 16), int(body[6:8], 16), a)
        return f"#{a:02x}{r:02x}{g:02x}{b:02x}"
    if len(body) != 6:
        return h
    r, g, b = transform_rgb(key, *_hex_to_rgb(body))
    return f"#{r:02x}{g:02x}{b:02x}"


_HEX = re.compile(r"(?<![\w&])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z])")
_RGBA = re.compile(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([\d.]+%?)\s*)?\)")


def transform_css(css: str, theme_key: Optional[str] = None) -> str:
    """Pasa por el tema todos los colores de una hoja de estilo (o de un HTML): #hex y rgb()/rgba()."""
    key = theme_key or _current
    if get(key).key == DEFAULT_THEME or not css or ("#" not in css and "rgb" not in css):
        return css

    def hexrep(m):
        return transform_hex(m.group(0), key)

    def rgbrep(m):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        alpha = m.group(4)
        a255 = 255
        if alpha is not None:
            try:
                a255 = int(round(float(alpha[:-1]) * 2.55)) if alpha.endswith("%") else int(round(float(alpha) * 255)) if float(alpha) <= 1 else int(float(alpha))
            except ValueError:
                a255 = 255
        nr, ng, nb = transform_rgb(key, min(r, 255), min(g, 255), min(b, 255), a255)
        return f"rgba({nr}, {ng}, {nb}, {alpha})" if alpha is not None else f"rgb({nr}, {ng}, {nb})"

    return _RGBA.sub(rgbrep, _HEX.sub(hexrep, css))


# ── instalación (parches de Qt) ──────────────────────────────────────────────────────────────────────
def install(key: Optional[str]) -> str:
    """Activa el tema `key` para TODA la interfaz creada a partir de ahora. Debe llamarse antes de importar `src.ui`."""
    global _current, _installed
    th = get(key)
    _current = th.key
    if th.key == DEFAULT_THEME or _installed:
        return _current
    from PySide6 import QtGui, QtWidgets
    try:
        import pyqtgraph  # noqa: F401  (se importa ANTES del parche: hereda de QColor al cargarse, y eso no admite el sustituto)
    except Exception:
        pass

    Base = _originals.setdefault("QColor", QtGui.QColor)

    class _ThemedColorFactory:
        """Se comporta como la clase QColor (se llama, tiene sus métodos de clase y vale en isinstance) pero devuelve QColor
        REALES ya pasados por el tema. (Una subclase de Python no vale: los QVariant de las animaciones no la reconocen.)"""

        def __call__(self, *args):
            try:
                if len(args) == 1 and isinstance(args[0], str) and args[0].startswith("#"):
                    args = (transform_hex(args[0]),)
                elif len(args) in (3, 4) and all(isinstance(v, int) and not isinstance(v, bool) for v in args):
                    a = args[3] if len(args) == 4 else 255
                    r, g, b = transform_rgb(_current, *[max(0, min(255, v)) for v in args[:3]], a)
                    args = (r, g, b) + ((a,) if len(args) == 4 else ())
            except Exception:
                pass
            return Base(*args)

        def __getattr__(self, name):
            return getattr(Base, name)

        def __instancecheck__(self, inst):
            return isinstance(inst, Base)

        def __subclasscheck__(self, sub):
            return issubclass(sub, Base)

        def __or__(self, other):                    # anotaciones como «QColor | str» (las usa pyqtgraph al importarse)
            return Base | other

        def __ror__(self, other):
            return other | Base

        def __repr__(self):
            return repr(Base)

    QtGui.QColor = _ThemedColorFactory()

    orig_qwidget_ss = _originals.setdefault("QWidget.setStyleSheet", QtWidgets.QWidget.setStyleSheet)

    def widget_set_stylesheet(self, css):
        return orig_qwidget_ss(self, transform_css(css) if isinstance(css, str) else css)

    QtWidgets.QWidget.setStyleSheet = widget_set_stylesheet

    orig_app_ss = _originals.setdefault("QApplication.setStyleSheet", QtWidgets.QApplication.setStyleSheet)

    def app_set_stylesheet(self, css):
        return orig_app_ss(self, transform_css(css) if isinstance(css, str) else css)

    QtWidgets.QApplication.setStyleSheet = app_set_stylesheet

    orig_label_text = _originals.setdefault("QLabel.setText", QtWidgets.QLabel.setText)

    def label_set_text(self, text):
        if isinstance(text, str) and "#" in text and "<" in text:
            text = transform_css(text)
        return orig_label_text(self, text)

    QtWidgets.QLabel.setText = label_set_text

    orig_html = _originals.setdefault("QGraphicsTextItem.setHtml", QtWidgets.QGraphicsTextItem.setHtml)

    def item_set_html(self, html):                  # las etiquetas de la onda (pyqtgraph TextItem) también llevan colores en HTML
        return orig_html(self, transform_css(html) if isinstance(html, str) else html)

    QtWidgets.QGraphicsTextItem.setHtml = item_set_html

    if not th.dark:
        # Logos blancos (pensados para fondo oscuro): en un tema claro se pintan con el color del texto del tema.
        OrigPix = _originals.setdefault("QPixmap", QtGui.QPixmap)

        class _ThemedPixmapFactory:
            def __call__(self, *args):
                pm = OrigPix(*args)
                try:
                    if len(args) == 1 and isinstance(args[0], str) and not pm.isNull():
                        name = args[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
                        if name.startswith("logo") and "_red" not in name:
                            ink = Base(*_hex_to_rgb(th.swatch[3]))
                            painter = QtGui.QPainter(pm)
                            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
                            painter.fillRect(pm.rect(), ink)
                            painter.end()
                except Exception:
                    pass
                return pm

            def __getattr__(self, name):
                return getattr(OrigPix, name)

            def __instancecheck__(self, inst):
                return isinstance(inst, OrigPix)

            def __subclasscheck__(self, sub):
                return issubclass(sub, OrigPix)

        QtGui.QPixmap = _ThemedPixmapFactory()

    # pyqtgraph (la onda, el tempo…) crea sus lápices y pinceles con su propio mkColor: también pasan por el tema.
    try:
        import pyqtgraph.functions as _pgf
        orig_mk = _originals.setdefault("pg.mkColor", _pgf.mkColor)

        def mk_color(*args, **kw):
            c = orig_mk(*args, **kw)
            if len(args) == 1 and isinstance(args[0], Base):         # un QColor ya viene pasado por el tema
                return c
            try:
                r, g, b = transform_rgb(_current, c.red(), c.green(), c.blue(), c.alpha())
                c.setRgb(r, g, b, c.alpha())
            except Exception:
                pass
            return c

        _pgf.mkColor = mk_color
        import pyqtgraph as _pg
        if hasattr(_pg, "mkColor"):
            _pg.mkColor = mk_color
    except Exception:
        pass
    _installed = True
    return _current


def raw_qcolor(hexcolor: str):
    """QColor SIN pasar por el tema (para dibujar las miniaturas de los propios temas)."""
    from PySide6 import QtGui
    return _originals.get("QColor", QtGui.QColor)(hexcolor)


def uninstall() -> None:
    """Deshace los parches (para las pruebas)."""
    global _current, _installed
    if not _installed:
        _current = DEFAULT_THEME
        return
    from PySide6 import QtGui, QtWidgets
    QtGui.QColor = _originals["QColor"]
    QtWidgets.QWidget.setStyleSheet = _originals["QWidget.setStyleSheet"]
    QtWidgets.QApplication.setStyleSheet = _originals["QApplication.setStyleSheet"]
    QtWidgets.QLabel.setText = _originals["QLabel.setText"]
    QtWidgets.QGraphicsTextItem.setHtml = _originals["QGraphicsTextItem.setHtml"]
    if "QPixmap" in _originals:
        QtGui.QPixmap = _originals["QPixmap"]
    try:
        import pyqtgraph as _pg
        import pyqtgraph.functions as _pgf
        if "pg.mkColor" in _originals:
            _pgf.mkColor = _originals["pg.mkColor"]
            if hasattr(_pg, "mkColor"):
                _pg.mkColor = _originals["pg.mkColor"]
    except Exception:
        pass
    _installed = False
    _current = DEFAULT_THEME


def install_from_config() -> str:
    """Lee el tema elegido en la configuración e instálalo (arranque de la aplicación)."""
    try:
        from src.config import load
        return install(str(load().get("theme") or DEFAULT_THEME))
    except Exception:
        return DEFAULT_THEME


def restart_application() -> bool:
    """Vuelve a abrir la aplicación (para aplicar un tema nuevo). Devuelve True si se lanzó el nuevo proceso."""
    import subprocess
    try:
        exe = str(sys.executable)
        if sys.platform == "darwin" and ".app/Contents/MacOS" in exe:
            # En macOS la nueva instancia debe abrirse con LaunchServices (foco, Dock y notificaciones del paquete .app)
            subprocess.Popen(["open", "-n", exe.split(".app/Contents/MacOS")[0] + ".app"])
            return True
        args = [sys.executable] + ([] if getattr(sys, "frozen", False) else sys.argv)
        if getattr(sys, "frozen", False):
            args += [a for a in sys.argv[1:] if a not in ("--restarted",)]
        kw = {"close_fds": True}
        if sys.platform == "win32":
            kw["creationflags"] = 0x00000008 | 0x00000200      # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        else:
            kw["start_new_session"] = True
        subprocess.Popen(args, **kw)
        return True
    except Exception:
        return False
