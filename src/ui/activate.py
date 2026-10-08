"""
AutoPrevias — Pantalla de activación de licencia.
Se muestra al arrancar si no hay licencia válida guardada.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame,
)

_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"

# Colores — mismos que app.py
BG      = "#0a0b0e"
BG2     = "#121419"
BG3     = "#1a1c22"
BORDER  = "#232733"
TEXT    = "#eceef2"
TEXT2   = "#8c93a4"
ACCENT  = "#ff1e38"
ACCENT2 = "#ff3e55"
GREEN   = "#22c55e"
RED     = "#ef4444"

_STORE_URL = "https://payhip.com/RADICALRECVLC"


class _ActivateWorker(QThread):
    done = Signal(bool, str, str)   # éxito, edition, error

    def __init__(self, key: str):
        super().__init__()
        self._key = key

    def run(self):
        from src.licensing.license import activate
        ok, edition, err = activate(self._key)
        self.done.emit(ok, edition, err)


class ActivationDialog(QDialog):
    """Diálogo modal de activación de licencia."""

    activated = Signal(str)   # edition activada ('basic' o 'plus')

    def __init__(self, parent=None, expired: bool = False):
        super().__init__(parent)
        self.setWindowTitle("AutoPrevias — Activación")
        self.setModal(True)
        self.setFixedSize(480, 420)
        self.setStyleSheet(f"""
            QDialog {{
                background: {BG};
            }}
            QLabel {{
                background: transparent;
                color: {TEXT};
            }}
            QLineEdit {{
                background: {BG3};
                border: 1px solid {BORDER};
                border-radius: 8px;
                color: {TEXT};
                font-size: 14px;
                padding: 10px 14px;
                letter-spacing: 1px;
                font-family: 'JetBrains Mono', 'Courier New', monospace;
            }}
            QLineEdit:focus {{
                border-color: {ACCENT};
            }}
            QLineEdit::placeholder {{
                color: {TEXT2};
            }}
        """)
        self._expired = expired
        self._worker  = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 36, 40, 36)
        root.setSpacing(0)

        # Logo oficial de la app
        lbl_icon = QLabel()
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setStyleSheet("background: transparent;")
        logo_path = _ASSETS_DIR / "logo_emblem.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaled(
                72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            lbl_icon.setPixmap(pix)
        else:
            lbl_icon.setText("🎵")
            lbl_icon.setStyleSheet("font-size: 44px; background: transparent;")
        root.addWidget(lbl_icon)
        root.addSpacing(12)

        lbl_title = QLabel("AutoPrevias")
        lbl_title.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(20)
        f.setWeight(QFont.Weight.ExtraBold)
        lbl_title.setFont(f)
        root.addWidget(lbl_title)
        root.addSpacing(6)

        if self._expired:
            msg = "Tu período de gracia ha expirado.\nIntroduce tu clave para continuar usando la app."
            color = RED
        else:
            msg = "Introduce tu clave de licencia para activar AutoPrevias.\nPuedes obtenerla en payhip.com/RADICALRECVLC"
            color = TEXT2

        lbl_msg = QLabel(msg)
        lbl_msg.setAlignment(Qt.AlignCenter)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet(f"color: {color}; font-size: 13px; background: transparent;")
        root.addWidget(lbl_msg)
        root.addSpacing(28)

        # Campo de clave
        self._input = QLineEdit()
        self._input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self._input.setAlignment(Qt.AlignCenter)
        self._input.returnPressed.connect(self._activate)
        root.addWidget(self._input)
        root.addSpacing(12)

        # Botón activar
        self._btn = QPushButton("Activar licencia")
        self._btn.setFixedHeight(44)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT};
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: {ACCENT2}; }}
            QPushButton:disabled {{ background: {BG3}; color: {TEXT2}; }}
        """)
        self._btn.clicked.connect(self._activate)
        root.addWidget(self._btn)
        root.addSpacing(14)

        # Estado / error
        self._lbl_status = QLabel("")
        self._lbl_status.setAlignment(Qt.AlignCenter)
        self._lbl_status.setWordWrap(True)
        self._lbl_status.setStyleSheet(f"font-size: 12px; color: {TEXT2}; background: transparent;")
        root.addWidget(self._lbl_status)

        root.addStretch()

        # Enlace a la tienda principal de Radical Records en Payhip
        lbl_link = QLabel(
            f'<a href="{_STORE_URL}" '
            f'style="color:{ACCENT2}; text-decoration:none;">Obtener licencia en payhip.com/RADICALRECVLC</a>'
        )
        lbl_link.setAlignment(Qt.AlignCenter)
        lbl_link.setOpenExternalLinks(True)
        lbl_link.setStyleSheet("font-size: 12px; background: transparent;")
        root.addWidget(lbl_link)

    def _activate(self):
        key = self._input.text().strip()
        if not key:
            self._set_status("Introduce una clave de licencia.", RED)
            return

        self._btn.setEnabled(False)
        self._btn.setText("Verificando…")
        self._set_status("Conectando con el servidor de licencias…", TEXT2)

        self._worker = _ActivateWorker(key)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, ok: bool, edition: str, error: str):
        self._btn.setEnabled(True)
        self._btn.setText("Activar licencia")

        if ok:
            plan = "Plus ✨" if edition == "plus" else "Basic"
            self._set_status(f"✅ Licencia {plan} activada correctamente.", GREEN)
            self.activated.emit(edition)
            # Cerrar el diálogo automáticamente tras 1 segundo
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1200, self.accept)
        else:
            self._set_status(f"❌ {error}", RED)

    def _set_status(self, msg: str, color: str):
        self._lbl_status.setText(msg)
        self._lbl_status.setStyleSheet(
            f"font-size: 12px; color: {color}; background: transparent;"
        )
