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


def enabled() -> bool:
    """False con el modo «Ahorro de recursos» o con AUTOPREVIAS_NO_ANIM=1."""
    if os.environ.get("AUTOPREVIAS_NO_ANIM") == "1":
        return False
    try:
        from src import perf
        return perf.get_mode() != "low"
    except Exception:
        return True


def fade_in(widget: QWidget, ms: int = 280, delay: int = 0) -> None:
    """El widget aparece con un fundido (de transparente a opaco)."""
    if widget is None or not enabled():
        return

    def _start():
        try:
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
