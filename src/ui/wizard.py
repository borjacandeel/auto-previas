"""
AutoPrevias v5 — Piezas del asistente de 3 pasos.

· `WizardStepper`: la cinta «① Tu tema · ② Tu previa · ③ Exportar» (cada chip se puede pulsar).
· `DestinationCard`: «¿Para qué es esta previa?» — un clic deja duración, formatos, vídeo y arranque/final listos.
· `DESTINATIONS` / `destination_settings()`: el contenido de cada destino (lógica pura, probada sin interfaz).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

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

# clave: (icono, título, subtítulo, segundos, ¿vídeo?)
DESTINATIONS = {
    "redes": ("📱", "Redes sociales", "15 s · MP3 + vídeo vertical", 15),
    "radio": ("📻", "Radio / emisoras", "30 s · MP3", 30),
    "sello": ("🏷", "Sello / promo", "60 s · WAV (Plus) o MP3", 60),
    "club": ("🔥", "Club / DJ", "2 min · FLAC (Plus) o MP3, con arranque y frenazo", 120),
    "custom": ("🛠", "Lo monto yo", "Sin ajustes previos: lo eliges todo", 0),
}


def destination_settings(key: str, plus: bool) -> dict:
    """Ajustes que aplica un destino. `seconds` 0 = no tocar la duración. Basic nunca recibe WAV/FLAC."""
    key = key if key in DESTINATIONS else "custom"
    seconds = DESTINATIONS[key][3]
    s = {"seconds": seconds, "wav": False, "mp3": True, "flac": False, "video": False,
         "aspect": "9:16", "start_mode": None, "end_mode": None, "open_detail": False}
    if key == "redes":
        s.update(video=True, aspect="9:16")
    elif key == "sello":
        s.update(wav=plus)
    elif key == "club":
        s.update(flac=plus, mp3=True, wav=False)
        if plus:
            s.update(start_mode="vinyl", end_mode="vinyl")
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


class DestinationCard(QFrame):
    """«¿Para qué es esta previa?»: botones exclusivos; `chosen(clave)` al elegir."""
    chosen = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("destcard")
        self.setStyleSheet(f"QFrame#destcard {{ background: {BG2}; border: 1px solid {BORDER}; border-radius: 12px; }}"
                           " QLabel { background: transparent; border: none; }")
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 12)
        v.setSpacing(8)
        t = QLabel("¿Para qué es esta previa?")
        t.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: 800;")
        self._hint = QLabel("Elige un destino y dejo la duración, los formatos y el vídeo listos. Luego puedes cambiar lo que quieras.")
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(f"color: {TEXT_MID}; font-size: 11px;")
        v.addWidget(t)
        v.addWidget(self._hint)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        for key, (icon, title, sub, _s) in DESTINATIONS.items():
            b = QPushButton(f"{icon}  {tr(title)}\n{tr(sub)}")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(54)
            b.setToolTip(tr(sub))
            b.setStyleSheet(
                f"QPushButton {{ background: {BG3}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 10px;"
                " font-size: 11.5px; font-weight: 700; padding: 6px 10px; text-align: left; }"
                f"QPushButton:hover {{ border-color: {ACCENT}; }}"
                f"QPushButton:checked {{ background: #2a1218; border: 2px solid {ACCENT}; }}")
            self.group.addButton(b)
            self.buttons[key] = b
            b.clicked.connect(lambda _=False, k=key: self.chosen.emit(k))
            row.addWidget(b, 1)
        v.addLayout(row)

    def select(self, key: str):
        b = self.buttons.get(key)
        if b:
            b.setChecked(True)
