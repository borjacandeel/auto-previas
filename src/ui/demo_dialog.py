"""AutoPrevias Demo — pantalla bloqueante cuando termina la demo de 7 días (o se detecta manipulación)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from src import links
from src.i18n import tr
from src.ui.activate import ACCENT, ACCENT2, BG, BG3, BORDER, TEXT, TEXT2, _ASSETS_DIR


class DemoEndedDialog(QDialog):
    """«Tu demo ha terminado»: solo permite comprar una edición o salir. No hay forma de seguir usando la demo."""

    def __init__(self, parent=None, status: str = "expired"):
        super().__init__(parent)
        self.setWindowTitle("AutoPrevias Demo")
        self.setModal(True)
        self.setFixedSize(500, 500)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; }}
            QLabel {{ background: transparent; color: {TEXT}; }}
            QPushButton {{ border-radius: 10px; font-size: 14px; font-weight: 700; padding: 0 14px; }}
            QPushButton#buy {{ background: {BG3}; color: {TEXT}; border: 1px solid {BORDER}; }}
            QPushButton#buy:hover {{ border-color: {ACCENT}; }}
            QPushButton#primary {{ background: {ACCENT}; color: #fff; border: none; }}
            QPushButton#primary:hover {{ background: {ACCENT2}; }}
            QPushButton#quit {{ background: transparent; color: {TEXT2}; border: none; font-weight: 600; }}
            QPushButton#quit:hover {{ color: {TEXT}; }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 24)
        root.setSpacing(0)
        icon = QLabel()
        icon.setAlignment(Qt.AlignCenter)
        logo = _ASSETS_DIR / "logo_emblem.png"
        if logo.exists():
            icon.setPixmap(QPixmap(str(logo)).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        root.addWidget(icon)
        root.addSpacing(10)
        title = QLabel(tr("Tu demo ha terminado") if status == "expired" else tr("La demo no puede continuar"))
        title.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(19)
        f.setWeight(QFont.Weight.ExtraBold)
        title.setFont(f)
        root.addWidget(title)
        root.addSpacing(6)
        msg = {"expired": tr("Los 7 días de prueba gratuita han terminado. Para seguir usando AutoPrevias, elige tu edición."),
               "clock": tr("Se ha detectado un cambio de fecha en tu equipo. Para seguir usando AutoPrevias, elige tu edición."),
               }.get(status, tr("No se ha podido verificar la demo en este equipo. Para seguir usando AutoPrevias, elige tu edición."))
        sub = QLabel(msg)
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {TEXT2}; font-size: 13px; background: transparent;")
        root.addWidget(sub)
        root.addSpacing(20)
        self._buy_buttons = []
        for ed, label in (("plus", "AutoPrevias Plus"), ("basic", "AutoPrevias Basic")):
            b = QPushButton(tr("Conseguir {n}", n=label))
            b.setObjectName("primary" if ed == "plus" else "buy")
            b.setFixedHeight(46)
            b.setCursor(Qt.PointingHandCursor)
            url = links.url_for(ed)
            b.setProperty("url", url)
            b.clicked.connect(lambda _c=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            root.addWidget(b)
            root.addSpacing(10)
            self._buy_buttons.append(b)
        hint = QLabel(tr("Tras el pago recibirás tu clave por correo y podrás descargar tu edición completa."))
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {TEXT2}; font-size: 12px; background: transparent;")
        root.addWidget(hint)
        root.addSpacing(12)
        q = QPushButton(tr("Salir de AutoPrevias"))
        q.setObjectName("quit")
        q.setFixedHeight(34)
        q.setCursor(Qt.PointingHandCursor)
        q.clicked.connect(lambda _c=False: self.reject())
        root.addWidget(q)
        root.addStretch()
