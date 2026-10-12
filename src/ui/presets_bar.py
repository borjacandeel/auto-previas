"""
AutoPrevias — Barra de presets (firma y estilo guardados como archivos con nombre).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src import i18n
from src.i18n import tr
from src.ui.dialog_style import DIALOG_QSS, TEXT2

BG3, BG4, BORDER, TEXT_MID, ACCENT = "#1a1c22", "#232733", "#2a2f3d", "#b4bac8", "#ff1e38"


class SavePresetDialog(QDialog):
    """Pide el nombre del preset y qué grupos incluir (firma y/o estilo)."""

    def __init__(self, existing: list[str], suggested: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guardar preset")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 16)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Nombre del preset"))
        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.addItems(existing)
        self._combo.setCurrentText(suggested)
        self._combo.lineEdit().setPlaceholderText("Ej. Radical Main · Set de Verano")
        lay.addWidget(self._combo)

        lay.addWidget(QLabel("Qué incluir"))
        self._chk_sig = QCheckBox("Firma: artista, sello, álbum, género, comentario y carátula")
        self._chk_sig.setChecked(True)
        self._chk_style = QCheckBox("Estilo: duración, formatos, efectos, voice drop, modo promo y vídeo")
        self._chk_style.setChecked(True)
        lay.addWidget(self._chk_sig)
        lay.addWidget(self._chk_style)

        self._lbl_warn = QLabel("")
        self._lbl_warn.setStyleSheet("color: #f59e0b; font-size: 11px;")
        self._lbl_warn.setWordWrap(True)
        i18n.mark_dynamic(self._lbl_warn)
        lay.addWidget(self._lbl_warn)

        row = QHBoxLayout()
        row.addStretch()
        b_cancel = QPushButton("Cancelar")
        b_cancel.clicked.connect(self.reject)
        self._b_ok = QPushButton("Guardar")
        self._b_ok.setObjectName("primary")
        self._b_ok.clicked.connect(self._accept)
        row.addWidget(b_cancel)
        row.addWidget(self._b_ok)
        lay.addLayout(row)

        self._existing = {n.lower() for n in existing}
        self._combo.currentTextChanged.connect(self._on_text)
        self._on_text(self._combo.currentText())
        i18n.translate_tree(self)

    def _on_text(self, text: str):
        self._lbl_warn.setText(tr("Ya existe un preset con ese nombre: se sobrescribirá.")
                               if text.strip().lower() in self._existing else "")

    def _accept(self):
        from src.presets import slugify
        if not slugify(self._combo.currentText()):
            self._lbl_warn.setText(tr("Escribe un nombre válido."))
            return
        if not (self._chk_sig.isChecked() or self._chk_style.isChecked()):
            self._lbl_warn.setText(tr("Marca al menos una opción (firma o estilo)."))
            return
        self.accept()

    def result_values(self) -> tuple:
        return (self._combo.currentText().strip(), self._chk_sig.isChecked(), self._chk_style.isChecked())


class PresetBar(QWidget):
    """Selector de presets + Aplicar / Guardar / Borrar."""

    apply_requested = Signal(str)
    save_requested = Signal(str, bool, bool)       # nombre, incluir firma, incluir estilo
    delete_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        lbl = QLabel("💾 MIS PRESETS:")
        lbl.setStyleSheet("color: #555b6a; font-size: 9px; font-weight: 800; letter-spacing: 0.8px;"
                          "background: transparent; border: none;")
        self._combo = QComboBox()
        self._combo.setFixedHeight(24)
        self._combo.setMinimumWidth(150)
        self._combo.setStyleSheet(
            f"QComboBox {{ background: {BG3}; color: #eceef2; border: 1px solid {BORDER};"
            "border-radius: 5px; padding: 2px 8px; font-size: 11px; }")
        self._combo.currentIndexChanged.connect(self._update_buttons)

        self._btn_apply = self._small("✔ Aplicar", "Aplica la firma y/o el estilo guardados en este preset", primary=True)
        self._btn_save = self._small("💾 Guardar…", "Guarda la firma y/o el estilo actuales como preset con nombre")
        self._btn_delete = self._small("🗑", "Borrar el preset seleccionado")
        self._btn_apply.clicked.connect(lambda: self.apply_requested.emit(self.current_name()))
        self._btn_save.clicked.connect(self._on_save)
        self._btn_delete.clicked.connect(self._on_delete)

        lay.addWidget(lbl)
        lay.addWidget(self._combo)
        lay.addWidget(self._btn_apply)
        lay.addWidget(self._btn_save)
        lay.addWidget(self._btn_delete)
        lay.addStretch()
        self.reload()

    @staticmethod
    def _small(text: str, tip: str, primary: bool = False) -> QPushButton:
        b = QPushButton(text)
        b.setFixedHeight(24)
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tip)
        if primary:
            b.setStyleSheet(f"QPushButton {{ background: {ACCENT}33; color: {ACCENT}; border: 1px solid {ACCENT}66;"
                            "border-radius: 5px; padding: 0 10px; font-size: 10.5px; font-weight: 700; }")
        else:
            b.setStyleSheet(f"QPushButton {{ background: {BG4}; color: {TEXT_MID}; border: 1px solid {BORDER};"
                            "border-radius: 5px; padding: 0 10px; font-size: 10.5px; }"
                            f"QPushButton:hover {{ border-color: {ACCENT}; }}")
        return b

    def current_name(self) -> str:
        return self._combo.currentData() or ""

    def reload(self, select: str = ""):
        from src.presets import list_presets
        names = list_presets()
        self._combo.blockSignals(True)
        self._combo.clear()
        if names:
            for n in names:
                self._combo.addItem(n, n)               # nombres de usuario: no se traducen
        else:
            self._combo.addItem("— Sin presets guardados —", "")
        if select and select in names:
            self._combo.setCurrentIndex(names.index(select))
        self._combo.blockSignals(False)
        self._update_buttons()
        i18n.translate_tree(self)

    def _update_buttons(self):
        has = bool(self.current_name())
        self._btn_apply.setEnabled(has)
        self._btn_delete.setEnabled(has)

    def _on_save(self):
        from src.presets import list_presets
        dlg = SavePresetDialog(list_presets(), self.current_name(), parent=self.window())
        if dlg.exec():
            name, sig, style = dlg.result_values()
            self.save_requested.emit(name, sig, style)

    def _on_delete(self):
        name = self.current_name()
        if not name:
            return
        box = QMessageBox(self.window())
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(tr("Borrar preset"))
        box.setText(tr("¿Borrar el preset «{name}»?", name=name))
        yes = box.addButton(tr("Borrar"), QMessageBox.AcceptRole)
        box.addButton(tr("Cancelar"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is yes:
            self.delete_requested.emit(name)
