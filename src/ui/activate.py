"""
AutoPrevias — Pantalla de activación de licencia.
Se muestra al arrancar si no hay licencia válida guardada.
"""
from __future__ import annotations

from pathlib import Path

from src import i18n, links
from src.i18n import tr

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




def _buy_url() -> str:
    """Enlace de compra de la edición instalada (Basic → producto Basic; Plus → producto Plus)."""
    try:
        from src.config import get_edition
        return links.url_for(get_edition())
    except Exception:
        return links.STORE_URL


def _buy_short() -> str:
    return links.short(_buy_url())


def _edition_now() -> str:
    try:
        from src.config import get_edition
        return get_edition()
    except Exception:
        return "basic"


def _renew_options() -> list:
    """[(duración, enlace)] para comprar/renovar la licencia de la edición instalada."""
    try:
        from src.config import get_edition
        return links.renew_options(get_edition())
    except Exception:
        return links.renew_options("basic")


class _ActivateWorker(QThread):
    done = Signal(bool, str, str)   # éxito, edition, error

    def __init__(self, key: str):
        super().__init__()
        self._key = key

    def run(self):
        try:
            from src.licensing.license import activate
            ok, edition, err = activate(self._key)
        except Exception as e:        # p. ej. disco bloqueado al guardar: el botón no puede quedarse en «Verificando…»
            ok, edition, err = False, "", f"No se pudo guardar la licencia en este equipo ({type(e).__name__}). Comprueba los permisos de tu carpeta de usuario o el antivirus y vuelve a intentarlo."
        self.done.emit(ok, edition, err)


class ActivationDialog(QDialog):
    """Diálogo modal de activación de licencia."""

    activated = Signal(str)   # edition activada ('basic' o 'plus')

    def __init__(self, parent=None, expired: bool = False, reason: str = ""):
        super().__init__(parent)
        self._reason = reason
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
        i18n.mark_dynamic(self._lbl_status)
        i18n.translate_tree(self)

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

        if self._reason == "term_ended":
            msg = "Tu licencia anterior ha caducado.\nIntroduce la clave de tu nueva licencia para continuar."
            color = RED
        elif self._reason == "in_use":
            msg = ("Esta licencia se ha activado en otro equipo.\n"
                   "Solo puede estar activa en un equipo a la vez.")
            color = RED
        elif self._reason == "wrong_edition":
            msg = ("Tu clave es de otra edición de AutoPrevias (Basic o Plus).\n"
                   "Usa la edición que corresponde a tu compra.")
            color = RED
        elif self._reason:
            msg = "Tu licencia ya no es válida.\nIntroduce una clave válida para continuar."
            color = RED
        elif self._expired:
            msg = "Tu período de gracia ha expirado.\nIntroduce tu clave para continuar usando la app."
            color = RED
        else:
            msg = tr("Introduce tu clave de licencia para activar AutoPrevias.\nPuedes obtenerla en {link}", link=_buy_short())
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
        if self._reason == "term_ended":
            opts = " · ".join(f'<a href="{url}" style="color:{ACCENT2}; text-decoration:none;">{tr(label)}</a>'
                              for label, url in _renew_options())
            lbl_link = QLabel(tr("Comprar licencia:") + " " + opts)
        else:
            lbl_link = QLabel(
                f'<a href="{_buy_url()}" '
                f'style="color:{ACCENT2}; text-decoration:none;">' + tr("Obtener licencia en {link}", link=_buy_short()) + '</a>'
            )
        lbl_link.setAlignment(Qt.AlignCenter)
        lbl_link.setOpenExternalLinks(True)
        lbl_link.setStyleSheet("font-size: 12px; background: transparent;")
        root.addWidget(lbl_link)

    def _activate(self):
        key = self._input.text().strip()
        if not key:
            self._set_status(tr("Introduce una clave de licencia."), RED)
            return

        self._btn.setEnabled(False)
        self._btn.setText(tr("Verificando…"))
        self._set_status(tr("Conectando con el servidor de licencias…"), TEXT2)

        self._worker = _ActivateWorker(key)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def done(self, r):
        """Cerrar con la verificación en marcha: un QThread destruido en ejecución cierra toda la app."""
        w = self._worker
        if w is not None and w.isRunning():
            try:
                w.done.disconnect()
            except (RuntimeError, TypeError):
                pass
            w.setParent(None)
            keep = getattr(ActivationDialog, "_orphans", [])
            keep.append(w)
            ActivationDialog._orphans = keep
            w.finished.connect(lambda *_a, x=w: keep.remove(x) if x in keep else None)
        super().done(r)

    def _on_done(self, ok: bool, edition: str, error: str):
        self._btn.setEnabled(True)
        self._btn.setText(tr("Activar licencia"))

        if ok:
            plan = "Plus ✨" if edition == "plus" else "Basic"
            self._set_status(tr("✅ Licencia {plan} activada correctamente.", plan=plan), GREEN)
            self.activated.emit(edition)
            # Cerrar el diálogo automáticamente tras 1 segundo
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1200, self.accept)
        else:
            self._set_status(f"❌ {tr(error)}", RED)

    def _set_status(self, msg: str, color: str):
        self._lbl_status.setText(msg)
        self._lbl_status.setStyleSheet(
            f"font-size: 12px; color: {color}; background: transparent;"
        )


class ExpiredDialog(QDialog):
    """Menú «Tu licencia ha caducado»: comprar una licencia nueva (3 o 12 meses) y volver al panel de activación."""

    ENTER_KEY = 1          # resultado de exec(): «Ya tengo una clave nueva»

    def __init__(self, parent=None, edition: str = "", expired_on: str = ""):
        super().__init__(parent)
        self.setWindowTitle("AutoPrevias — Licencia caducada")
        self.setModal(True)
        self.setFixedSize(500, 470)
        self._edition = edition
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

        lbl_icon = QLabel()
        lbl_icon.setAlignment(Qt.AlignCenter)
        logo = _ASSETS_DIR / "logo_emblem.png"
        if logo.exists():
            lbl_icon.setPixmap(QPixmap(str(logo)).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        root.addWidget(lbl_icon)
        root.addSpacing(10)

        title = QLabel(tr("Tu licencia ha caducado"))
        title.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(19)
        f.setWeight(QFont.Weight.ExtraBold)
        title.setFont(f)
        root.addWidget(title)
        root.addSpacing(6)

        plan = "Plus" if str(edition).lower() == "plus" else "Basic"
        when = tr("Venció el {d}.", d=expired_on) + " " if expired_on else ""
        sub = QLabel(when + tr("Para seguir usando AutoPrevias {plan}, compra una licencia nueva y activa su clave.", plan=plan))
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {TEXT2}; font-size: 13px; background: transparent;")
        root.addWidget(sub)
        root.addSpacing(22)

        opts = _renew_options() if not edition else links.renew_options(edition)
        self._buy_buttons = []
        for label, url in opts:
            months = 12 if label.startswith("12") else 3
            price = links.price_text(edition or _edition_now(), months, i18n.get_language())
            b = QPushButton(tr("Comprar licencia de {d} · {p}", d=tr(label), p=price) if price
                            else tr("Comprar licencia de {d}", d=tr(label)))
            b.setObjectName("buy")
            b.setFixedHeight(46)
            b.setCursor(Qt.PointingHandCursor)
            b.setProperty("url", url)
            b.clicked.connect(lambda _c=False, u=url: self._open(u))
            root.addWidget(b)
            root.addSpacing(10)
            self._buy_buttons.append(b)

        hint = QLabel(tr("Tras el pago recibirás tu clave por correo. Después pulsa el botón de abajo."))
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {TEXT2}; font-size: 12px; background: transparent;")
        root.addWidget(hint)
        root.addSpacing(14)

        self._btn_enter = QPushButton(tr("Ya tengo una clave nueva"))
        self._btn_enter.setObjectName("primary")
        self._btn_enter.setFixedHeight(46)
        self._btn_enter.setCursor(Qt.PointingHandCursor)
        self._btn_enter.clicked.connect(lambda _c=False: self.done(self.ENTER_KEY))
        root.addWidget(self._btn_enter)
        root.addSpacing(6)

        self._btn_quit = QPushButton(tr("Salir de AutoPrevias"))
        self._btn_quit.setObjectName("quit")
        self._btn_quit.setFixedHeight(34)
        self._btn_quit.setCursor(Qt.PointingHandCursor)
        self._btn_quit.clicked.connect(lambda _c=False: self.reject())
        root.addWidget(self._btn_quit)
        root.addStretch()
        i18n.translate_tree(self)

    @staticmethod
    def _open(url: str):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(url))


def run_expired_flow(parent=None, edition: str = "", expired_on: str = "") -> str | None:
    """Licencia temporal caducada: menú de compra → panel de activación. Devuelve la edición activada, o None si el usuario sale.

    Si cierra el panel de activación sin activar, vuelve al menú (no se puede seguir sin una licencia en regla).
    """
    while True:
        menu = ExpiredDialog(parent, edition=edition, expired_on=expired_on)
        if menu.exec() != ExpiredDialog.ENTER_KEY:
            return None
        dlg = ActivationDialog(parent, reason="term_ended")
        got: list = []
        dlg.activated.connect(got.append)
        dlg.exec()
        if got:
            return got[0]
