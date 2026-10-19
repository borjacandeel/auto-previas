"""
AutoPrevias — Animaciones de interfaz (sutiles y baratas).

Todas respetan el ajuste «Rendimiento»: en modo «Ahorro de recursos» (o con AUTOPREVIAS_NO_ANIM=1)
los cambios se hacen al instante, sin animar. Cada animación se guarda en el propio widget para que
no la recoja el recolector de basura mientras corre.
"""
from __future__ import annotations

import os
import re

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

_MAX = 16777215          # QWIDGETSIZE_MAX
_NUM = re.compile(r"^\d+(\.\d+)?$")


_REDUCE = None


def os_reduce_motion() -> bool:
    """True si el sistema operativo pide «reducir movimiento» (macOS: Accesibilidad → Pantalla; Windows: efectos de
    animación desactivados). Se consulta una sola vez."""
    global _REDUCE
    if _REDUCE is not None:
        return _REDUCE
    _REDUCE = False
    try:
        import subprocess
        import sys
        if sys.platform == "darwin":
            r = subprocess.run(["defaults", "read", "com.apple.universalaccess", "reduceMotion"],
                               capture_output=True, text=True, timeout=1.5)
            _REDUCE = r.stdout.strip() == "1"
        elif sys.platform == "win32":
            import ctypes
            on = ctypes.c_int(1)
            ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0)   # SPI_GETCLIENTAREAANIMATION
            _REDUCE = on.value == 0
    except Exception:
        _REDUCE = False
    return _REDUCE


def enabled() -> bool:
    """False con el modo «Ahorro de recursos», con «reducir movimiento» del sistema o con AUTOPREVIAS_NO_ANIM=1."""
    if os.environ.get("AUTOPREVIAS_NO_ANIM") == "1":
        return False
    force = os.environ.get("AUTOPREVIAS_FORCE_ANIM") == "1"
    if not force and os_reduce_motion():
        return False
    try:
        from src import perf
        return force or perf.get_mode() != "low"
    except Exception:
        return True


def fade_in(widget: QWidget, ms: int = 280, delay: int = 0) -> None:
    """El widget aparece con un fundido (de transparente a opaco)."""
    if widget is None or not enabled():
        return

    def _start():
        try:
            ex = widget.graphicsEffect()
            if ex is not None and ex is not getattr(widget, "_fade_pre", None) and not ex.property("hoverfx"):
                return                                  # ya tiene un efecto propio (sombra de una tarjeta…): no se pisa
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", widget)
            anim.setDuration(ms)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.finished.connect(lambda: widget.setGraphicsEffect(None))
            widget._fade_anim = anim
            anim.start()
        except RuntimeError:
            pass                                    # el widget ya no existe

    eff0 = None
    if delay > 0:
        eff0 = QGraphicsOpacityEffect(widget)       # invisible hasta que le toque
        eff0.setOpacity(0.0)
        widget.setGraphicsEffect(eff0)
        widget._fade_pre = eff0
        QTimer.singleShot(delay, _start)
    else:
        _start()


def stagger_fade_in(widgets, step_ms: int = 60, ms: int = 260) -> None:
    """Varios widgets aparecen uno tras otro."""
    for i, w in enumerate(widgets):
        fade_in(w, ms=ms, delay=i * step_ms)


def reveal(widget: QWidget, show: bool, ms: int = 220) -> None:
    """Muestra u oculta el widget desplegándolo/plegándolo en altura (como un cajón)."""
    if widget is None:
        return
    old = getattr(widget, "_reveal_anim", None)
    if old is not None:
        old.stop()
    if not enabled():
        widget.setMaximumHeight(_MAX)
        widget.setVisible(show)
        return
    if show:
        if widget.isVisible() and widget.maximumHeight() == _MAX:
            return
        widget.setMaximumHeight(0)
        widget.setVisible(True)
        target = max(1, widget.sizeHint().height())
        anim = QVariantAnimation(widget)
        anim.setDuration(ms)
        anim.setStartValue(0)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.valueChanged.connect(lambda v: widget.setMaximumHeight(int(v)))
        anim.finished.connect(lambda: widget.setMaximumHeight(_MAX))
    else:
        if not widget.isVisible():
            widget.setMaximumHeight(_MAX)
            return
        anim = QVariantAnimation(widget)
        anim.setDuration(int(ms * 0.8))
        anim.setStartValue(widget.height())
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.valueChanged.connect(lambda v: widget.setMaximumHeight(int(v)))

        def _done():
            widget.setVisible(False)
            widget.setMaximumHeight(_MAX)
        anim.finished.connect(_done)
    widget._reveal_anim = anim
    anim.start()


def count_up(setter, text: str, ms: int = 650, owner: QWidget | None = None) -> None:
    """Muestra `text`; si es un número, lo cuenta desde 0 hasta el valor (con los mismos decimales).
    `setter(str)` pinta el texto en cada paso."""
    if not enabled() or not _NUM.match(str(text).strip()):
        setter(text)
        return
    target = float(text)
    dec = len(text.split(".")[1]) if "." in text else 0
    if target == 0:
        setter(text)
        return
    anim = QVariantAnimation(owner)
    anim.setDuration(ms)
    anim.setStartValue(0.0)
    anim.setEndValue(target)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    anim.valueChanged.connect(lambda v: setter(f"{float(v):.{dec}f}"))
    anim.finished.connect(lambda: setter(text))
    if owner is not None:
        old = getattr(owner, "_count_anim", None)
        if old is not None:
            old.stop()
        owner._count_anim = anim
    anim.start()


def pulse_border(widget: QWidget, base_qss: str, hot_qss: str, ms: int = 220) -> None:
    """Cambio de estilo con un destello corto (hot) y vuelta al normal (base)."""
    if not enabled():
        widget.setStyleSheet(base_qss)
        return
    widget.setStyleSheet(hot_qss)
    QTimer.singleShot(ms, lambda: widget.setStyleSheet(base_qss))


# ═══════════════════════════ 4.1: animaciones por toda la app ═══════════════════════════

from PySide6.QtCore import QEvent, QObject, QPoint, Qt as _Qt                       # noqa: E402
from PySide6.QtGui import QColor                                                    # noqa: E402
from PySide6.QtWidgets import (QAbstractButton, QDialog, QGraphicsDropShadowEffect,  # noqa: E402
                               QProgressBar, QPushButton, QToolButton)

GLOW_COLOR = (255, 30, 56)          # el carmesí de AutoPrevias


def animate_value(owner, start: float, end: float, ms: int, setter, easing=QEasingCurve.OutCubic, finished=None,
                  key: str = "_va"):
    """Anima un número de `start` a `end` llamando a `setter(valor)`. Guarda la animación en `owner` (con `key`) y
    para la anterior con la misma clave. Sin animaciones activadas, aplica el valor final al instante."""
    old = getattr(owner, key, None) if owner is not None else None
    if old is not None:
        try:
            old.stop()
        except RuntimeError:
            pass
    if not enabled() or ms <= 0:
        setter(end)
        if finished:
            finished()
        return None
    a = QVariantAnimation(owner)
    a.setDuration(ms)
    a.setStartValue(float(start))
    a.setEndValue(float(end))
    a.setEasingCurve(easing)

    def _step(v):
        try:
            setter(float(v))
        except RuntimeError:
            a.stop()                                   # el objeto ya no existe
    a.valueChanged.connect(_step)

    def _done():
        try:
            setter(float(end))
            if finished:
                finished()
        except RuntimeError:
            pass
    a.finished.connect(_done)
    if owner is not None:
        setattr(owner, key, a)
    a.start()
    return a


# ── botones con vida: brillo al pasar el ratón y «hundido» al pulsar ──────────────────────────────

class ButtonFx(QObject):
    """Filtro de eventos de TODA la aplicación: los botones reales (no los iconos diminutos de las tablas) brillan
    al pasar el ratón y se «hunden» un instante al pulsarlos. El efecto se crea al primer paso del ratón y se quita
    al salir, así que no cuesta nada en reposo."""

    def __init__(self, app):
        super().__init__(app)

    @staticmethod
    def _eligible(w) -> bool:
        if not isinstance(w, (QPushButton, QToolButton)) or not w.isEnabled():
            return False
        if w.property("nofx") or w.height() < 22 or w.width() < 28:
            return False
        ex = w.graphicsEffect()
        return ex is None or bool(ex.property("hoverfx"))

    @staticmethod
    def _effect(w, create: bool):
        ex = w.graphicsEffect()
        if isinstance(ex, QGraphicsDropShadowEffect) and ex.property("hoverfx"):
            return ex
        if not create or w.graphicsEffect() is not None:
            return None
        ex = QGraphicsDropShadowEffect(w)
        ex.setOffset(0, 0)
        ex.setBlurRadius(0)
        ex.setColor(QColor(*GLOW_COLOR, 0))
        ex.setProperty("hoverfx", True)
        w.setGraphicsEffect(ex)
        return ex

    @staticmethod
    def _glow_to(w, blur: float, alpha: int, ms: int, offset_y: float = 0.0, remove_at_end: bool = False):
        ex = ButtonFx._effect(w, True)
        if ex is None:
            return
        start_b, start_a = ex.blurRadius(), ex.color().alpha()

        def _set(t):
            try:
                ex.setBlurRadius(start_b + (blur - start_b) * t)
                ex.setColor(QColor(*GLOW_COLOR, int(start_a + (alpha - start_a) * t)))
                ex.setOffset(0, offset_y * t)
            except RuntimeError:
                pass

        def _fin():
            if remove_at_end:
                try:
                    if w.graphicsEffect() is ex:
                        w.setGraphicsEffect(None)
                except RuntimeError:
                    pass
        animate_value(w, 0.0, 1.0, ms, _set, QEasingCurve.OutCubic, _fin, key="_glow_anim")

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t not in (QEvent.Enter, QEvent.Leave, QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
                     QEvent.EnabledChange):
            return False
        if not isinstance(obj, (QPushButton, QToolButton)) or not enabled():
            return False
        try:
            if t == QEvent.Enter and self._eligible(obj):
                self._glow_to(obj, 16, 120, 140)
            elif t == QEvent.Leave and self._effect(obj, False) is not None:
                self._glow_to(obj, 0, 0, 160, remove_at_end=True)
            elif t == QEvent.MouseButtonPress and self._effect(obj, False) is not None:
                self._glow_to(obj, 5, 190, 70, offset_y=1.5)              # «se hunde»: el brillo se recoge
            elif t == QEvent.MouseButtonRelease and self._effect(obj, False) is not None:
                self._glow_to(obj, 16, 120, 140)
            elif t == QEvent.EnabledChange and not obj.isEnabled() and self._effect(obj, False) is not None:
                obj.setGraphicsEffect(None)
        except RuntimeError:
            pass
        return False


def install_button_fx(app) -> None:
    """Instala el brillo de botones en toda la aplicación (una sola vez)."""
    if app is None or getattr(app, "_button_fx", None) is not None:
        return
    app._button_fx = ButtonFx(app)
    app.installEventFilter(app._button_fx)


def pulse_glow(btn: QWidget, on: bool, lo: float = 8, hi: float = 26, ms: int = 1500) -> None:
    """El botón «respira»: un brillo que sube y baja mientras `on` (p. ej. ▶ GENERAR cuando está listo)."""
    anim = getattr(btn, "_pulse_anim", None)
    if anim is not None:
        try:
            anim.stop()
        except RuntimeError:
            pass
        btn._pulse_anim = None
    if not on or not enabled():
        ex = btn.graphicsEffect()
        if ex is not None and ex.property("pulsefx"):
            btn.setGraphicsEffect(None)
        btn.setProperty("nofx", False)
        return
    ex = btn.graphicsEffect()
    if ex is None or not ex.property("pulsefx"):
        ex = QGraphicsDropShadowEffect(btn)
        ex.setOffset(0, 0)
        ex.setProperty("pulsefx", True)
        btn.setGraphicsEffect(ex)
    btn.setProperty("nofx", True)                    # el brillo de pasar el ratón no pisa este
    a = QVariantAnimation(btn)
    a.setStartValue(0.0)
    a.setKeyValueAt(0.5, 1.0)
    a.setEndValue(0.0)
    a.setDuration(ms)
    a.setLoopCount(-1)
    a.setEasingCurve(QEasingCurve.InOutSine)

    def _step(v):
        try:
            v = float(v)
            ex.setBlurRadius(lo + (hi - lo) * v)
            ex.setColor(QColor(*GLOW_COLOR, int(70 + 110 * v)))
        except RuntimeError:
            a.stop()
    a.valueChanged.connect(_step)
    btn._pulse_anim = a
    a.start()


# ── pantallas y ventanas ────────────────────────────────────────────────────────────────────────

def slide_fade_in(widget: QWidget, dx: int = 36, dy: int = 0, ms: int = 380) -> None:
    """La pantalla entra deslizándose unos píxeles y apareciendo (más elegante que solo el fundido)."""
    if widget is None or not enabled():
        return
    try:
        base = widget.pos()
        eff = QGraphicsOpacityEffect(widget)
        eff.setOpacity(0.0)
        widget.setGraphicsEffect(eff)
        grp = getattr(widget, "_slide_anim", None)
        if grp is not None:
            grp.stop()

        def _frame(t):
            try:
                eff.setOpacity(min(1.0, t * 1.35))
                widget.move(base.x() + int(dx * (1 - t)), base.y() + int(dy * (1 - t)))
            except RuntimeError:
                pass

        def _end():
            try:
                widget.move(base)
                widget.setGraphicsEffect(None)
                lay = widget.parentWidget().layout() if widget.parentWidget() else None
                if lay is not None:
                    lay.activate()
            except RuntimeError:
                pass
        widget._slide_anim = animate_value(widget, 0.0, 1.0, ms, _frame, QEasingCurve.OutCubic, _end, key="_slide_anim")
    except RuntimeError:
        pass


def fade_window_in(win: QWidget, ms: int = 170) -> None:
    """Una ventana (diálogo) aparece con un fundido corto."""
    if win is None or not enabled() or not win.isWindow():
        return
    try:
        win.setWindowOpacity(0.0)
        animate_value(win, 0.0, 1.0, ms, lambda v: win.setWindowOpacity(v), QEasingCurve.OutCubic,
                      lambda: win.setWindowOpacity(1.0), key="_win_fade")
    except RuntimeError:
        pass


class DialogFx(QObject):
    """Todas las ventanas de AutoPrevias (Licencia, Historial, Firmar, Lote, Actualización…) aparecen con fundido y su
    contenido entra en cascada."""

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Show and isinstance(obj, QDialog) and enabled() \
                and type(obj).__module__.startswith("src.ui") and not getattr(obj, "_dlg_fx_done", False):
            obj._dlg_fx_done = True
            fade_window_in(obj)
            try:
                lay = obj.layout()
                kids = []
                if lay is not None:
                    for i in range(min(lay.count(), 12)):
                        it = lay.itemAt(i)
                        w = it.widget() if it is not None else None
                        if w is not None and w.graphicsEffect() is None:
                            kids.append(w)
                if kids:
                    QTimer.singleShot(60, lambda ks=kids: stagger_fade_in([k for k in ks if k.isVisible()], step_ms=45, ms=240))
            except RuntimeError:
                pass
        return False


def install_dialog_fx(app) -> None:
    if app is None or getattr(app, "_dialog_fx", None) is not None:
        return
    app._dialog_fx = DialogFx(app)
    app.installEventFilter(app._dialog_fx)


# ── barras de progreso y textos ─────────────────────────────────────────────────────────────────

def smooth_progress(bar: QProgressBar, target: int, ms: int = 260) -> None:
    """La barra avanza deslizándose hasta el valor (no a saltos); si retrocede o reinicia, salta."""
    target = int(target)
    if not enabled() or target <= bar.value() or target >= 100 and bar.value() == 0:
        old = getattr(bar, "_prog_anim", None)
        if old is not None:
            try:
                old.stop()
            except RuntimeError:
                pass
        if not enabled() or target < bar.value() or target == 0:
            bar.setValue(target)
            return
    animate_value(bar, bar.value(), target, ms, lambda v: bar.setValue(int(round(v))), QEasingCurve.OutCubic,
                  key="_prog_anim")


def swap_text(label: QWidget, text: str, ms: int = 200) -> None:
    """Cambia el texto de una etiqueta con un fundido corto (en vez de a golpe)."""
    label.setText(text)
    if not enabled() or label.graphicsEffect() is not None or not label.isVisible():
        return
    try:
        eff = QGraphicsOpacityEffect(label)
        label.setGraphicsEffect(eff)

        def _end():
            try:
                if label.graphicsEffect() is eff:
                    label.setGraphicsEffect(None)
            except RuntimeError:
                pass
        animate_value(label, 0.35, 1.0, ms, lambda v: eff.setOpacity(v), QEasingCurve.OutCubic, _end, key="_swap_anim")
    except RuntimeError:
        pass


def crossfade_transition(widget: QWidget, change_fn, ms: int = 260) -> None:
    """Hace `change_fn()` (p. ej. cambiar de idioma) y funde desde una «foto» de cómo estaba la pantalla, sin parpadeo."""
    if widget is None or not enabled() or not widget.isVisible():
        change_fn()
        return
    from PySide6.QtWidgets import QLabel
    try:
        snap = widget.grab()
        change_fn()
        ov = QLabel(widget)
        ov.setPixmap(snap)
        ov.setGeometry(widget.rect())
        ov.setAttribute(_Qt.WA_TransparentForMouseEvents, True)
        ov.show()
        ov.raise_()
        eff = QGraphicsOpacityEffect(ov)
        ov.setGraphicsEffect(eff)

        def _end():
            try:
                ov.hide()
                ov.deleteLater()
            except RuntimeError:
                pass
        animate_value(ov, 1.0, 0.0, ms, lambda v: eff.setOpacity(v), QEasingCurve.OutCubic, _end, key="_xf_anim")
    except RuntimeError:
        change_fn()
