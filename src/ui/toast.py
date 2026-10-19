"""
AutoPrevias — Avisos con diseño propio (tarjetas que se deslizan desde la esquina).

Sustituyen a los textos sueltos y a las cajas grises del sistema: icono, título, detalle y, si hace falta, un botón de
acción («Reintentar», «Abrir carpeta»…). Los de información y éxito se van solos; los de error se quedan hasta que se
cierran. Respetan el ajuste «Rendimiento» (sin animaciones aparecen al instante).
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget)

from src.i18n import tr
from src.ui import anim

KINDS = {
    # tipo: (icono, color de acento, segundos visibles; 0 = hasta cerrarla)
    "info": ("ℹ", "#5aa0ff", 4.0),
    "success": ("✔", "#2ed573", 3.6),
    "warn": ("⚠", "#ffb020", 6.0),
    "error": ("✖", "#ff4757", 0.0),
}
MAX_VISIBLE = 3
W = 360


class Toast(QFrame):
    def __init__(self, host: "ToastHost", kind: str, title: str, detail: str = "",
                 action: Optional[tuple] = None, seconds: Optional[float] = None):
        super().__init__(host.window)
        self.host = host
        self.kind = kind if kind in KINDS else "info"
        icon, col, secs = KINDS[self.kind]
        self.seconds = secs if seconds is None else seconds
        self.setObjectName("toast")
        self.setFixedWidth(W)
        self.setStyleSheet(
            f"QFrame#toast {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #181b23, stop:1 #12141a);"
            f" border: 1px solid #2a2f3c; border-left: 4px solid {col}; border-radius: 10px; }}"
            " QLabel { background: transparent; border: none; }")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 10, 10)
        lay.setSpacing(10)
        ic = QLabel(icon)
        ic.setFixedWidth(22)
        ic.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        ic.setStyleSheet(f"color: {col}; font-size: 17px; font-weight: 900; background: transparent; border: none;")
        lay.addWidget(ic)
        col_v = QVBoxLayout()
        col_v.setSpacing(2)
        t = QLabel(title)
        t.setWordWrap(True)
        t.setStyleSheet("color: #eceef2; font-size: 12.5px; font-weight: 800; background: transparent; border: none;")
        col_v.addWidget(t)
        if detail:
            d = QLabel(detail)
            d.setWordWrap(True)
            d.setStyleSheet("color: #9aa2b4; font-size: 11px; font-weight: 500; background: transparent; border: none;")
            col_v.addWidget(d)
        if action:
            row = QHBoxLayout()
            row.setContentsMargins(0, 6, 0, 0)
            b = QPushButton(tr(action[0]))
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(24)
            b.setStyleSheet(f"QPushButton {{ background: {col}; color: #0b0c10; border: none; border-radius: 6px;"
                            " font-size: 11px; font-weight: 800; padding: 0 12px; }}"
                            "QPushButton:hover { background: #ffffff; }")
            fn = action[1]
            b.clicked.connect(lambda _=False, f=fn: (self.dismiss(), f()))
            row.addWidget(b)
            row.addStretch()
            col_v.addLayout(row)
        lay.addLayout(col_v, 1)
        x = QPushButton("✕")
        x.setFixedSize(20, 20)
        x.setCursor(Qt.PointingHandCursor)
        x.setProperty("nofx", True)
        x.setStyleSheet("QPushButton { background: transparent; color: #6b7285; border: none; font-size: 12px; font-weight: 800; }"
                        "QPushButton:hover { color: #ffffff; }")
        x.clicked.connect(lambda _=False: self.dismiss())
        lay.addWidget(x, 0, Qt.AlignTop)
        self.adjustSize()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.dismiss)
        self._closing = False

    def enterEvent(self, e):
        self._timer.stop()                                   # con el ratón encima no se va
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self.seconds and not self._closing:
            self._timer.start(1800)
        super().leaveEvent(e)

    def dismiss(self):
        if self._closing:
            return
        self._closing = True
        self._timer.stop()
        self.host._remove(self)


class ToastHost(QObject):
    """Gestiona las tarjetas de una ventana: las apila abajo a la derecha, las desliza y las retira."""

    def __init__(self, window: QWidget):
        super().__init__(window)
        self.window = window
        self.items: list[Toast] = []
        window.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if obj is self.window and ev.type() in (QEvent.Resize, QEvent.Move):
            self._layout(animated=False)
        return False

    # ── API ───────────────────────────────────────────────────────────────────────
    def show(self, kind: str, title: str, detail: str = "", action: Optional[tuple] = None,
             seconds: Optional[float] = None) -> Toast:
        # un aviso idéntico no se repite
        for it in self.items:
            if not it._closing and it.kind == kind and it.property("sig") == (title, detail):
                it._timer.start(int((it.seconds or 4) * 1000))
                return it
        t = Toast(self, kind, tr(title), tr(detail) if detail else "", action, seconds)
        t.setProperty("sig", (title, detail))
        self.items.append(t)
        while len([i for i in self.items if not i._closing]) > MAX_VISIBLE:
            old = next(i for i in self.items if not i._closing)
            old.dismiss()
        t.show()
        t.raise_()
        self._layout(animated=False)
        self._enter(t)
        if t.seconds:
            t._timer.start(int(t.seconds * 1000))
        return t

    def clear(self):
        for it in list(self.items):
            it.dismiss()

    # ── colocación ─────────────────────────────────────────────────────────────────
    def _target(self, idx_from_bottom: int, h_below: int, t: Toast) -> QPoint:
        w = self.window
        return QPoint(w.width() - W - 18, w.height() - h_below - t.height() - 38)

    def _layout(self, animated: bool = True):
        below = 0
        for t in reversed([i for i in self.items if not i._closing]):
            tgt = self._target(0, below, t)
            if animated and anim.enabled() and t.isVisible():
                p0 = t.pos()
                anim.animate_value(t, p0.y(), tgt.y(), 220, lambda v, t=t, x=tgt.x(): t.move(x, int(v)),
                                   QEasingCurve.OutCubic, key="_lay")
            else:
                t.move(tgt)
            below += t.height() + 8

    def _enter(self, t: Toast):
        if not anim.enabled():
            return
        eff = QGraphicsOpacityEffect(t)
        t.setGraphicsEffect(eff)
        end = t.pos()

        def _f(v):
            eff.setOpacity(min(1.0, v * 1.4))
            t.move(end.x() + int((1 - v) * 60), end.y())

        def _done():
            try:
                t.setGraphicsEffect(None)
                t.move(end)
            except RuntimeError:
                pass
        anim.animate_value(t, 0.0, 1.0, 320, _f, QEasingCurve.OutBack, _done, key="_in")

    def _remove(self, t: Toast):
        def _gone():
            try:
                if t in self.items:
                    self.items.remove(t)
                t.hide()
                t.deleteLater()
            except RuntimeError:
                pass
            self._layout(animated=True)
        if anim.enabled():
            eff = QGraphicsOpacityEffect(t)
            t.setGraphicsEffect(eff)
            start = t.pos()
            anim.animate_value(t, 1.0, 0.0, 200, lambda v: (eff.setOpacity(v), t.move(start.x() + int((1 - v) * 50), start.y())),
                               QEasingCurve.InCubic, _gone, key="_out")
        else:
            _gone()


def host_for(window: QWidget) -> ToastHost:
    h = getattr(window, "_toast_host", None)
    if h is None:
        h = ToastHost(window)
        window._toast_host = h
    return h


def toast(window: QWidget, kind: str, title: str, detail: str = "", action: Optional[tuple] = None,
          seconds: Optional[float] = None) -> Toast:
    """Atajo: muestra un aviso en la ventana (se crea el gestor la primera vez)."""
    return host_for(window).show(kind, title, detail, action, seconds)
