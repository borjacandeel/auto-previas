"""
AutoPrevias — Pantalla «Licencia y ajustes»: versión, edición, estado de la licencia,
idioma, búsqueda manual de actualizaciones y desactivación de la licencia.
"""
from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout,
)

from src import i18n
from src.i18n import tr
from src.ui.dialog_style import ACCENT, DIALOG_QSS, GREEN, RED, TEXT2, WARN

SUPPORT_EMAIL = "radicalrecordsvlc@gmail.com"


def describe_license(local: dict | None, now: float | None = None, grace_days: int = 14) -> dict:
    """Resumen de la licencia local para mostrar (función pura, testeable).

    Devuelve: state ('active'|'grace_expired'|'revoked'|'none'), license_id, verified, valid_until, days_left.
    """
    import time as _time

    if not local:
        return {"state": "none", "license_id": "", "verified": "", "valid_until": "", "days_left": 0}
    now = _time.time() if now is None else now
    verified_at = float(local.get("verified_at", 0) or 0)
    until = verified_at + grace_days * 86400
    days_left = int((until - now) // 86400)
    fmt = lambda ts: _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "—"
    state = "active" if now <= until else "grace_expired"
    if local.get("revoked"):
        state = "revoked"
    return {
        "state": state,
        "license_id": str(local.get("key_hash", ""))[:8].upper(),
        "verified": fmt(verified_at),
        "valid_until": fmt(until),
        "days_left": max(days_left, 0),
    }


class LicenseDialog(QDialog):
    language_changed = Signal(str)
    update_found = Signal(object)        # ReleaseInfo
    license_removed = Signal()

    def __init__(self, version: str, edition: str, parent=None):
        super().__init__(parent)
        self._version = version
        self._edition = edition
        self._checker = None

        self.setWindowTitle("AutoPrevias — Licencia y ajustes")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setStyleSheet(DIALOG_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 20)
        root.setSpacing(10)

        title = QLabel("AutoPrevias")
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        root.addWidget(title)

        self._lbl_version = QLabel()
        self._lbl_version.setStyleSheet(f"font-size: 13px; color: {TEXT2};")
        root.addWidget(self._lbl_version)

        root.addWidget(self._separator())

        lic_title = QLabel("LICENCIA")
        lic_title.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {TEXT2}; letter-spacing: 1px;")
        root.addWidget(lic_title)
        self._lbl_state = QLabel()
        self._lbl_state.setWordWrap(True)
        self._lbl_state.setStyleSheet("font-size: 13px; font-weight: 700;")
        root.addWidget(self._lbl_state)
        self._lbl_detail = QLabel()
        self._lbl_detail.setWordWrap(True)
        self._lbl_detail.setStyleSheet(f"font-size: 12px; color: {TEXT2};")
        root.addWidget(self._lbl_detail)

        root.addWidget(self._separator())

        lang_row = QHBoxLayout()
        lang_lbl = QLabel("Idioma")
        lang_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
        self._combo_lang = QComboBox()
        for code, name in i18n.LANGUAGES.items():
            self._combo_lang.addItem(name, code)       # los nombres de idioma no se traducen
        self._combo_lang.setCurrentIndex(max(0, self._combo_lang.findData(i18n.get_language())))
        self._combo_lang.currentIndexChanged.connect(self._on_language)
        lang_row.addWidget(lang_lbl)
        lang_row.addStretch()
        lang_row.addWidget(self._combo_lang)
        root.addLayout(lang_row)

        root.addWidget(self._separator())

        self._lbl_update = QLabel("")
        self._lbl_update.setWordWrap(True)
        self._lbl_update.setStyleSheet(f"font-size: 12px; color: {TEXT2};")
        root.addWidget(self._lbl_update)

        btn_row = QHBoxLayout()
        self._btn_update = QPushButton("Buscar actualizaciones")
        self._btn_update.clicked.connect(self._check_updates)
        self._btn_remove = QPushButton("Desactivar licencia en este equipo")
        self._btn_remove.setObjectName("danger")
        self._btn_remove.clicked.connect(self._remove_license)
        btn_row.addWidget(self._btn_update)
        btn_row.addWidget(self._btn_remove)
        root.addLayout(btn_row)

        self._lbl_support = QLabel()
        self._lbl_support.setStyleSheet(f"font-size: 11px; color: {TEXT2};")
        self._lbl_support.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self._lbl_support)

        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("primary")
        btn_close.clicked.connect(self.accept)
        close_row.addWidget(btn_close)
        root.addLayout(close_row)

        i18n.mark_dynamic(self._lbl_version, self._lbl_state, self._lbl_detail,
                          self._lbl_support, self._lbl_update)
        self._refresh()
        i18n.translate_tree(self)

    @staticmethod
    def _separator() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #232733; max-height: 1px; border: none;")
        return sep

    # ── Contenido dinámico (se vuelve a calcular al cambiar de idioma) ─────────
    def _refresh(self):
        plan = tr("PLUS") if self._edition == "plus" else tr("BÁSICA")
        self._lbl_version.setText(tr("Versión {v}  ·  Edición {ed}", v=self._version, ed=plan))
        self._lbl_support.setText(tr("Soporte: {mail}", mail=SUPPORT_EMAIL))

        from src.config import _get_baked_edition
        if _get_baked_edition() is None:
            self._lbl_state.setText(tr("🛠️ Modo desarrollo (sin licencia)"))
            self._lbl_state.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {WARN};")
            self._lbl_detail.setText(tr("Esta copia se ejecuta desde el código fuente: no se exige licencia."))
            self._btn_remove.setEnabled(False)
            return
        from src.licensing.license import GRACE_DAYS, load_local
        info = describe_license(load_local(), grace_days=GRACE_DAYS)
        if info["state"] == "active":
            self._lbl_state.setText(tr("✅ Licencia activa"))
            self._lbl_state.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {GREEN};")
            self._lbl_detail.setText(tr(
                "ID de licencia: {lid}\nÚltima verificación: {ver}\nVálida sin conexión hasta: {until} ({days} días)",
                lid=info["license_id"], ver=info["verified"], until=info["valid_until"], days=info["days_left"]))
        elif info["state"] == "revoked":
            self._lbl_state.setText(tr("⚠️ Esta licencia ya no es válida en este equipo"))
            self._lbl_state.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {RED};")
            self._lbl_detail.setText(tr(
                "ID de licencia: {lid}\nSe activó en otro equipo o fue desactivada.\nReinicia AutoPrevias para activarla de nuevo.",
                lid=info["license_id"]))
        elif info["state"] == "grace_expired":
            self._lbl_state.setText(tr("⚠️ Hay que volver a verificar la licencia"))
            self._lbl_state.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {WARN};")
            self._lbl_detail.setText(tr(
                "ID de licencia: {lid}\nÚltima verificación: {ver}\nConéctate a internet y reinicia AutoPrevias.",
                lid=info["license_id"], ver=info["verified"]))
        else:
            self._lbl_state.setText(tr("Sin licencia activada"))
            self._lbl_state.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {RED};")
            self._lbl_detail.setText("")
            self._btn_remove.setEnabled(False)

    def _on_language(self):
        code = self._combo_lang.currentData()
        i18n.set_language(code)
        self.language_changed.emit(code)
        self._refresh()
        i18n.translate_tree(self)

    # ── Actualizaciones ───────────────────────────────────────────────────────
    def _check_updates(self):
        from src.__version__ import __version__
        from src.update import UpdateChecker
        self._btn_update.setEnabled(False)
        self._lbl_update.setText(tr("Buscando actualizaciones…"))
        self._found = False
        self._checker = UpdateChecker(__version__, parent=self, ignore_skipped=True)
        self._checker.update_available.connect(self._on_update_found)
        self._checker.check_done.connect(self._on_check_done)
        self._checker.start()

    def _on_update_found(self, info):
        self._found = True
        self._lbl_update.setText(tr("🆕 Hay una versión nueva: {v}", v=info.version))
        self.update_found.emit(info)

    def _on_check_done(self):
        self._btn_update.setEnabled(True)
        if not getattr(self, "_found", False):
            self._lbl_update.setText(tr("✅ Estás al día ({v}).", v=self._version))

    # ── Desactivar licencia ───────────────────────────────────────────────────
    def _release_on_server(self) -> bool:
        """Libera la licencia en el servidor. False = el usuario cancela."""
        from PySide6.QtWidgets import QApplication
        from src.licensing.license import deactivate_online
        while True:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                ok, _code = deactivate_online()
            finally:
                QApplication.restoreOverrideCursor()
            if ok:
                return True
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle(tr("Desactivar licencia"))
            box.setText(tr("No se pudo contactar con el servidor para liberar la licencia.\n"
                           "Si la desactivas solo aquí, no podrás activarla en otro equipo hasta que "
                           "pasen 15 días o escribas a {mail}.", mail=SUPPORT_EMAIL))
            retry = box.addButton(tr("Reintentar"), QMessageBox.AcceptRole)
            local = box.addButton(tr("Desactivar solo aquí"), QMessageBox.DestructiveRole)
            box.addButton(tr("Cancelar"), QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is retry:
                continue
            return box.clickedButton() is local

    def _remove_license(self):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(tr("Desactivar licencia"))
        box.setText(tr("Se liberará la licencia para que puedas usarla en otro equipo y AutoPrevias se cerrará. "
                       "Podrás volver a activarla con tu clave cuando quieras."))
        yes = box.addButton(tr("Desactivar y cerrar"), QMessageBox.AcceptRole)
        box.addButton(tr("Cancelar"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is yes:
            if not self._release_on_server():
                return
            from src.licensing.license import clear_local
            clear_local()
            self.license_removed.emit()
            self.accept()

    def done(self, result):
        if self._checker is not None and self._checker.isRunning():
            self._checker.wait(2000)
        super().done(result)
