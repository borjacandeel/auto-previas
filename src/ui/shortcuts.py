"""AutoPrevias v5 — Lista de atajos de teclado y su ventana de ayuda."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QGridLayout, QLabel, QPushButton, QVBoxLayout

from src.i18n import tr

MOD = "⌘" if sys.platform == "darwin" else "Ctrl"

# (teclas, qué hace)
SHORTCUTS = (
    ("Espacio", "Reproducir / pausa"),
    ("← →", "Saltar 5 segundos"),
    ("Inicio  ·  0", "Volver al principio"),
    ("Esc", "Detener"),
    ("M", "Silenciar / activar sonido"),
    (f"{MOD} + O", "Abrir un tema"),
    (f"{MOD} + G", "Generar la previa"),
    (f"{MOD} + 2  ·  {MOD} + 3", "Ir al paso ② Tu previa  ·  ③ Exportar"),
    (f"{MOD} + E", "Cambiar entre asistente y modo Estudio"),
    (f"{MOD} + Z", "Deshacer (cortes y efectos)"),
    (f"{MOD} + Mayús + Z  ·  {MOD} + Y", "Rehacer"),
    ("Supr", "Borrar el efecto seleccionado de la onda"),
    ("F1  ·  ?", "Ver esta ayuda"),
)


class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Atajos de teclado"))
        self.setMinimumWidth(520)
        self.setStyleSheet("QDialog { background: #121419; } QLabel { color: #eceef2; font-size: 12.5px; }")
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(10)
        t = QLabel(tr("⌨ Atajos de teclado"))
        t.setStyleSheet("font-size: 17px; font-weight: 800;")
        v.addWidget(t)
        g = QGridLayout()
        g.setHorizontalSpacing(20)
        g.setVerticalSpacing(7)
        for r, (keys, what) in enumerate(SHORTCUTS):
            k = QLabel(keys)
            k.setStyleSheet("background: #21252f; border: 1px solid #2a2f3c; border-radius: 6px; padding: 3px 9px;"
                            " font-weight: 800; font-size: 11.5px; color: #eceef2;")
            k.setAlignment(Qt.AlignCenter)
            g.addWidget(k, r, 0, Qt.AlignLeft)
            g.addWidget(QLabel(tr(what)), r, 1)
        g.setColumnStretch(1, 1)
        v.addLayout(g)
        b = QPushButton(tr("Cerrar"))
        b.setFixedHeight(32)
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet("QPushButton { background: #ff1e38; color: white; border: none; border-radius: 8px; font-weight: 800; padding: 0 22px; }"
                        "QPushButton:hover { background: #ff3e55; }")
        b.clicked.connect(self.accept)
        v.addWidget(b, 0, Qt.AlignRight)
