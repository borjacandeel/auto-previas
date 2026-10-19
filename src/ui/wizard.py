"""
AutoPrevias v5 — Piezas del asistente de 3 pasos.

· `WizardStepper`: la cinta «① Tu tema · ② Tu previa · ③ Exportar» (cada chip se puede pulsar).
· `DestinationCard`: «¿Para qué es esta previa?» — un clic deja duración, formatos, vídeo y arranque/final listos.
· `DESTINATIONS` / `destination_settings()`: el contenido de cada destino (lógica pura, probada sin interfaz).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from src.i18n import tr

BG2, BG3, BG4 = "#121419", "#181b22", "#21252f"
BORDER, ACCENT = "#232733", "#ff1e38"
TEXT, TEXT_DIM, TEXT_MID = "#eceef2", "#555b6a", "#8c93a4"
GREEN = "#2ed573"

STEPS = (
    (1, "Tu tema"),
    (2, "Tu previa"),
    (3, "Exportar"),
)

# clave: (icono, título, línea principal, línea secundaria, segundos)
DESTINATIONS = {
    "redes": ("📱", "Redes sociales", "15 s · Vídeo vertical 9:16 con onda animada y carátula", "Instagram · TikTok · Shorts", 15),
    "radio": ("📻", "Radio y promotores", "30 s · MP3 listo para enviar", "Para enviar por correo", 30),
    "sello": ("🏷", "Sellos y A&R", "60 s · WAV de alta calidad (Plus) o MP3 320k", "Para demos y firmas", 60),
    "club": ("🎧", "DJ y club", "2 min · FLAC (Plus) con arranque y final de vinilo", "Para pinchar y compartir en set", 120),
    "seguro": ("🛡", "Envío seguro", "MP3 128k con tu voz repetida (Plus)", "Nadie puede reutilizarlo sin ti", 30),
    "custom": ("🎛", "Lo monto yo", "Elige cortes, efectos, formato…", "Para quien quiere control total", 0),
}
RECOMMENDED = "sello"


def destination_settings(key: str, plus: bool) -> dict:
    """Ajustes que aplica un destino. `seconds` 0 = no tocar la duración. Basic nunca recibe WAV/FLAC ni modo promo."""
    key = key if key in DESTINATIONS else "custom"
    seconds = DESTINATIONS[key][4]
    s = {"seconds": seconds, "wav": False, "mp3": True, "flac": False, "video": False, "promo": False,
         "aspect": "9:16", "start_mode": None, "end_mode": None, "open_detail": False}
    if key == "redes":
        s.update(video=True, aspect="9:16")
    elif key == "sello":
        s.update(wav=plus)
    elif key == "club":
        s.update(flac=plus, mp3=True, wav=False)
        if plus:
            s.update(start_mode="vinyl", end_mode="vinyl")
    elif key == "seguro":
        s.update(promo=plus)
    elif key == "custom":
        s.update(open_detail=True)
    return s


class WizardStepper(QFrame):
    """Cinta de pasos. `step_clicked(n)` al pulsar un chip; los pasos ya hechos llevan ✓."""
    step_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("wzstep")
        self.setStyleSheet("QFrame#wzstep { background: transparent; border: none; }")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.chips: dict[int, QPushButton] = {}
        self._lines: list[QFrame] = []
        for i, (n, name) in enumerate(STEPS):
            b = QPushButton()
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(32)
            b.clicked.connect(lambda _=False, n=n: self.step_clicked.emit(n))
            self.chips[n] = b
            lay.addWidget(b)
            if i < len(STEPS) - 1:
                ln = QFrame()
                ln.setFixedHeight(2)
                ln.setMinimumWidth(24)
                lay.addWidget(ln, 1)
                self._lines.append(ln)
        self.current = 2
        self.set_step(2)

    def set_step(self, n: int):
        self.current = n
        for k, b in self.chips.items():
            name = dict(STEPS)[k]
            done = k < n
            if k == n:
                b.setText(f"{k}  {tr(name)}")
                b.setStyleSheet(f"QPushButton {{ background: {ACCENT}; color: #ffffff; border: none; border-radius: 16px;"
                                " font-size: 12px; font-weight: 800; padding: 0 16px; }")
            elif done:
                b.setText(f"✓  {tr(name)}")
                b.setStyleSheet(f"QPushButton {{ background: {BG3}; color: {GREEN}; border: 1px solid {BORDER}; border-radius: 16px;"
                                " font-size: 12px; font-weight: 700; padding: 0 14px; }"
                                f"QPushButton:hover {{ border-color: {GREEN}; }}")
            else:
                b.setText(f"{k}  {tr(name)}")
                b.setStyleSheet(f"QPushButton {{ background: {BG2}; color: {TEXT_MID}; border: 1px solid {BORDER}; border-radius: 16px;"
                                " font-size: 12px; font-weight: 700; padding: 0 14px; }"
                                f"QPushButton:hover {{ border-color: {ACCENT}; color: {TEXT}; }}")
        for i, ln in enumerate(self._lines):
            ln.setStyleSheet(f"background: {GREEN if i + 1 < n else BORDER}; border: none; border-radius: 1px;")

    def retranslate(self):
        self.set_step(self.current)


class MiniWave(QWidget):
    """Onda pequeña de la cabecera de la pantalla de destino (solo dibuja una envolvente)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        self.setMinimumWidth(220)
        self._env = None

    def set_envelope(self, rms):
        try:
            import numpy as np
            a = np.asarray(rms, dtype=float).ravel()
            if a.size == 0:
                self._env = None
            else:
                n = 140
                idx = np.linspace(0, a.size, n + 1).astype(int)
                v = np.array([a[idx[i]:max(idx[i] + 1, idx[i + 1])].max() for i in range(n)])
                self._env = v / (v.max() or 1.0)
        except Exception:
            self._env = None
        self.update()

    def paintEvent(self, _e):
        from PySide6.QtGui import QColor, QPainter
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1b1d27"))
        p.drawRoundedRect(self.rect(), 8, 8)
        if self._env is not None:
            n = len(self._env)
            w = self.width() / n
            mid = self.height() / 2
            p.setBrush(QColor("#ff1e38"))
            for i, v in enumerate(self._env):
                h = max(2.0, float(v) * (self.height() - 10))
                p.drawRoundedRect(i * w + 0.5, mid - h / 2, max(1.0, w - 1.2), h, 1, 1)
        p.end()


class DestinationPage(QWidget):
    """Pantalla «¿Para qué es esta previa?»: tarjeta con el tema, seis destinos grandes y accesos a la guía."""
    chosen = Signal(str)
    skipped = Signal()
    other_track = Signal()
    guide_requested = Signal()

    def __init__(self, plus: bool, parent=None):
        super().__init__(parent)
        from src.ui import theme5 as T
        self.plus = plus
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 6, 40, 6)
        outer.setSpacing(14)
        # — cabecera con el tema —
        hdr = T.card(16)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(16, 12, 16, 12)
        hl.setSpacing(14)
        thumb = QLabel("RR")
        thumb.setFixedSize(52, 52)
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setStyleSheet("color: white; font-size: 17px; font-weight: 900; border-radius: 10px;"
                            " background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ff2a44, stop:1 #6e0010);")
        hl.addWidget(thumb)
        col = QVBoxLayout()
        col.setSpacing(1)
        self.lbl_name = QLabel("")
        self.lbl_name.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 800; background: transparent; border: none;")
        self.lbl_meta = QLabel("")
        self.lbl_meta.setStyleSheet(f"color: {TEXT_MID}; font-size: 11.5px; background: transparent; border: none;")
        col.addWidget(self.lbl_name)
        col.addWidget(self.lbl_meta)
        hl.addLayout(col, 1)
        self.wave = MiniWave()
        hl.addWidget(self.wave, 2)
        self.btn_other = QPushButton("Otro tema")
        self.btn_other.setFixedHeight(34)
        self.btn_other.setCursor(Qt.PointingHandCursor)
        self.btn_other.setStyleSheet(T.ghost_css(10, 11.5))
        self.btn_other.clicked.connect(lambda _=False: self.other_track.emit())
        hl.addWidget(self.btn_other)
        outer.addWidget(hdr)
        outer.addWidget(T.h1("¿Para qué es esta previa?", 28))
        outer.addWidget(T.sub("Elige y listo: AutoPrevias prepara duración, formato, vídeo y firma. Podrás verla y retocarla antes de exportar.", 13))
        # — destinos —
        grid = QGridLayout()
        grid.setSpacing(14)
        self.tiles: dict[str, T.Tile] = {}
        for i, (key, (icon, title, line1, line2, _sec)) in enumerate(DESTINATIONS.items()):
            locked = key == "seguro" and not plus
            t = T.Tile(tr(title), "", icon=icon, tagtext=(tr("Recomendado") if key == RECOMMENDED else ""),
                       checkable=False, min_h=150, big_icon=True)
            t.lbl_sub.setText(f"{tr(line1)}\n{tr(line2)}")
            if locked:
                t.lbl_title.setText("🔒 " + tr(title) + " (Plus)")
            if key == RECOMMENDED:
                t.setStyleSheet(t.styleSheet() + f"QPushButton#tile5 {{ border: 1px solid {ACCENT}; background: {T.ACCENT_DIM}; }}")
            t.clicked.connect(lambda _=False, k=key: self.chosen.emit(k))
            grid.addWidget(t, i // 3, i % 3)
            self.tiles[key] = t
        outer.addLayout(grid)
        # — pie —
        foot = QHBoxLayout()
        foot.setSpacing(10)
        q = QLabel("¿Primera vez?")
        q.setStyleSheet(f"color: {TEXT_MID}; font-size: 11.5px; background: transparent; border: none;")
        foot.addWidget(q)
        g = QPushButton("🎓  Guía de 2 minutos")
        g.setFixedHeight(32)
        g.setCursor(Qt.PointingHandCursor)
        g.setStyleSheet(T.ghost_css(10, 11.5))
        g.clicked.connect(lambda _=False: self.guide_requested.emit())
        foot.addWidget(g)
        foot.addStretch()
        self.chk_never = QCheckBox("No volver a mostrar esta pantalla")
        self.chk_never.setStyleSheet(f"QCheckBox {{ color: {TEXT_DIM}; font-size: 11px; background: transparent; }}")
        foot.addWidget(self.chk_never)
        self.btn_skip = QPushButton("Saltar este paso  →")
        self.btn_skip.setFixedHeight(32)
        self.btn_skip.setCursor(Qt.PointingHandCursor)
        self.btn_skip.setStyleSheet(T.ghost_css(10, 11.5))
        self.btn_skip.clicked.connect(lambda _=False: self.skipped.emit())
        foot.addWidget(self.btn_skip)
        outer.addLayout(foot)
        outer.addStretch(1)

    def set_track(self, name: str, meta: str, rms=None):
        self.lbl_name.setText(name)
        self.lbl_meta.setText(meta)
        self.wave.set_envelope(rms if rms is not None else [])
