"""
AutoPrevias v5 — Piezas visuales del nuevo diseño (tarjetas grandes, selectores con título y descripción, interruptores).

Todas son widgets pequeños y reutilizables; no contienen lógica de la aplicación.
"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, Property, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QAbstractButton, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout,
                               QWidget)

from src.i18n import tr

BG = "#0a0b0e"
CARD = "#10131a"
CARD2 = "#151922"
BORDER = "#232733"
ACCENT = "#ff1e38"
ACCENT_DIM = "#2a1218"
TEXT = "#eceef2"
TEXT_MID = "#8c93a4"
TEXT_DIM = "#5d6477"
GREEN = "#2ed573"

_T = "background: transparent; border: none;"


def card(radius: int = 16, accent: bool = False, name: str = "card5") -> QFrame:
    """Tarjeta redondeada. Su hoja de estilo solo toca a la propia tarjeta; las etiquetas de dentro quedan transparentes."""
    f = QFrame()
    f.setObjectName(name)
    border = ACCENT if accent else BORDER
    bg = ("qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #1d0f14, stop:1 #12090c)" if accent
          else f"qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {CARD2}, stop:1 {CARD})")
    f.setStyleSheet(f"QFrame#{name} {{ background: {bg}; border: 1px solid {border}; border-radius: {radius}px; }}"
                    f" QFrame#{name} QLabel {{ {_T} }}")
    return f


def h1(text: str, size: int = 26) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(f"color: {TEXT}; font-size: {size}px; font-weight: 900; letter-spacing: -0.4px; {_T}")
    l.setWordWrap(True)
    return l


def sub(text: str, size: float = 12.5) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(f"color: {TEXT_MID}; font-size: {size}px; font-weight: 500; {_T}")
    l.setWordWrap(True)
    return l


def section_label(text: str) -> QLabel:
    l = QLabel(text.upper())
    l.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-weight: 800; letter-spacing: 1.2px; {_T}")
    return l


def tag(text: str, color: str = ACCENT) -> QLabel:
    l = QLabel(text.upper())
    l.setAlignment(Qt.AlignCenter)
    l.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: 900; letter-spacing: 1px; border: 1px solid {color};"
                    f" border-radius: 5px; padding: 2px 8px; background: transparent;")
    return l


def chip(text: str) -> QLabel:
    """Pastilla roja pequeña (BPM, tonalidad, drops)."""
    l = QLabel(text)
    l.setAlignment(Qt.AlignCenter)
    l.setStyleSheet(f"color: #ff5468; background: #2a0d13; border: 1px solid #5c1620; border-radius: 6px;"
                    f" font-size: 10.5px; font-weight: 800; padding: 3px 9px;")
    return l


def cta_css(radius: int = 12, fs: int = 14) -> str:
    return (f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff2a44, stop:1 #a80016); color: #ffffff;"
            f" border: 1px solid #ff5a6e; border-radius: {radius}px; font-size: {fs}px; font-weight: 900; padding: 0 28px;"
            " letter-spacing: 0.3px; }"
            "QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff4a60, stop:1 #c4001c); border-color: #ff8595; }"
            "QPushButton:pressed { background: #8a0013; }"
            f"QPushButton:disabled {{ background: #1a1d26; color: {TEXT_DIM}; border: 1px solid {BORDER}; }}")


def ghost_css(radius: int = 10, fs: int = 11.5) -> str:
    return (f"QPushButton {{ background: {CARD}; color: #c3c9d8; border: 1px solid {BORDER}; border-radius: {radius}px;"
            f" font-size: {fs}px; font-weight: 700; padding: 0 16px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {TEXT}; }}"
            f"QPushButton:disabled {{ color: {TEXT_DIM}; }}")


class Toggle(QAbstractButton):
    """Interruptor deslizante (rojo = activado)."""

    def __init__(self, parent=None, on: bool = False):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(on)
        self.setFixedSize(46, 26)
        self.setCursor(Qt.PointingHandCursor)
        self._pos = 1.0 if on else 0.0
        self._anim = QPropertyAnimation(self, b"pos_", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._go)

    def _go(self, on: bool):
        from src.ui import anim
        if anim.enabled() and self.isVisible():
            self._anim.stop()
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(1.0 if on else 0.0)
            self._anim.start()
        else:
            self._pos = 1.0 if on else 0.0
            self.update()

    def get_pos(self):
        return self._pos

    def set_pos(self, v):
        self._pos = float(v)
        self.update()
    pos_ = Property(float, get_pos, set_pos)

    def sizeHint(self):
        return self.size()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        off, on = QColor("#2a2f3c"), QColor(ACCENT)
        t = self._pos
        col = QColor(int(off.red() + (on.red() - off.red()) * t), int(off.green() + (on.green() - off.green()) * t),
                     int(off.blue() + (on.blue() - off.blue()) * t))
        if not self.isEnabled():
            col.setAlpha(110)
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        r = QRectF(0, 0, self.width(), self.height())
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = 3 + (r.width() - d - 6) * t
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(x, 3, d, d))
        p.end()


class Tile(QPushButton):
    """Botón-tarjeta con título y descripción (opcionalmente una etiqueta tipo «RECOMENDADO»). Se puede marcar."""

    def __init__(self, title: str, subtitle: str = "", icon: str = "", tagtext: str = "", checkable: bool = True,
                 min_h: int = 64, big_icon: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(min_h)
        self.setObjectName("tile5")
        self.setStyleSheet(
            f"QPushButton#tile5 {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; text-align: left; }}"
            f"QPushButton#tile5:hover {{ border-color: #4a2a32; background: {CARD2}; }}"
            f"QPushButton#tile5:checked {{ background: {ACCENT_DIM}; border: 2px solid {ACCENT}; }}")
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(2)
        self.tag = None
        if big_icon:
            top = QHBoxLayout()
            ic = QLabel(icon)
            ic.setStyleSheet(f"font-size: 32px; {_T}")
            top.addWidget(ic)
            top.addStretch()
            if tagtext:
                self.tag = tag(tagtext)
                self.tag.setFixedHeight(22)
                top.addWidget(self.tag, 0, Qt.AlignTop)
            v.addLayout(top)
            self.lbl_title = QLabel(title)
            self.lbl_title.setStyleSheet(f"color: {TEXT}; font-size: 17px; font-weight: 900; {_T}")
            v.addWidget(self.lbl_title)
        else:
            top = QHBoxLayout()
            top.setSpacing(8)
            if icon:
                ic = QLabel(icon)
                ic.setStyleSheet(f"font-size: 20px; {_T}")
                top.addWidget(ic)
            self.lbl_title = QLabel(title)
            self.lbl_title.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 800; {_T}")
            top.addWidget(self.lbl_title, 1)
            if tagtext:
                self.tag = tag(tagtext)
                self.tag.setFixedHeight(22)
                top.addWidget(self.tag, 0, Qt.AlignTop)
            v.addLayout(top)
        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet(f"color: {TEXT_MID}; font-size: 11px; font-weight: 500; {_T}")
        v.addWidget(self.lbl_sub)
        for w in self.findChildren(QLabel):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_texts(self, title: str, subtitle: str):
        self.lbl_title.setText(title)
        self.lbl_sub.setText(subtitle)


class ClickCard(QFrame):
    """Tarjeta que reacciona a un clic en cualquier punto (para activar la casilla que lleva dentro)."""
    clicked = Signal()

    def __init__(self, name: str = "fmt5", parent=None):
        super().__init__(parent)
        self.setObjectName(name)
        self._name = name
        self.setCursor(Qt.PointingHandCursor)
        self.set_selected(False)

    def set_selected(self, on: bool, locked: bool = False):
        border = ACCENT if on else BORDER
        bg = ACCENT_DIM if on else CARD
        w = 2 if on else 1
        self.setStyleSheet(f"QFrame#{self._name} {{ background: {bg}; border: {w}px solid {border}; border-radius: 14px; }}"
                           f" QFrame#{self._name}:hover {{ border-color: {ACCENT if on else '#4a2a32'}; }}"
                           f" QFrame#{self._name} QLabel {{ {_T} }}")

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()


def checkbox_css(color: str = ACCENT) -> str:
    return (f"QCheckBox {{ color: {TEXT}; font-size: 14px; font-weight: 800; spacing: 8px; background: transparent; }}"
            f"QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 9px; border: 2px solid #3a4050; background: {CARD}; }}"
            f"QCheckBox::indicator:checked {{ background: {color}; border-color: {color}; }}"
            f"QCheckBox:disabled {{ color: {TEXT_DIM}; }}")
