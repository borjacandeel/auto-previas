"""
AutoPrevias — Ventana de actualización.

Se muestra al arrancar si hay una versión nueva: notas de la versión, descarga
directa del instalador a la carpeta Descargas del usuario con progreso,
verificación de integridad y apertura del instalador. Nunca abre ni muestra
páginas web: si algo falla, lo indica aquí mismo y permite reintentar.
"""
from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QTextEdit,
    QProgressBar, QPushButton, QVBoxLayout,
)

from src import i18n
from src.i18n import tr
from src.updater_core import ReleaseInfo, installer_asset_name, set_skipped_version, strip_links

BG, BG3, BORDER = "#0a0b0e", "#1a1c22", "#232733"
TEXT, TEXT2 = "#eceef2", "#8c93a4"
ACCENT, ACCENT2, GREEN, RED = "#ff1e38", "#ff3e55", "#22c55e", "#ef4444"

_IDLE, _DOWNLOADING, _READY, _FAILED = "idle", "downloading", "ready", "failed"


def _fmt_mb(n: int) -> str:
    return f"{n / (1024 * 1024):.1f} MB"


class UpdateDialog(QDialog):
    def __init__(self, info: ReleaseInfo, current_version: str, edition: str, parent=None):
        super().__init__(parent)
        self._info = info
        self._asset = installer_asset_name(edition)
        self._installer_path = ""
        self._downloader = None
        self._state = _IDLE

        self.setWindowTitle("AutoPrevias — Actualización disponible")
        self.setModal(True)
        self.setMinimumSize(520, 460)
        self.setStyleSheet(f"""
            QDialog {{ background: {BG}; }}
            QLabel {{ background: transparent; color: {TEXT}; }}
            QTextEdit {{
                background: {BG3}; border: 1px solid {BORDER}; border-radius: 8px;
                color: {TEXT}; font-size: 12px; padding: 8px;
            }}
            QProgressBar {{
                background: {BG3}; border: 1px solid {BORDER}; border-radius: 6px;
                height: 14px; text-align: center; color: {TEXT}; font-size: 10px;
            }}
            QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}
            QPushButton {{
                background: {BG3}; color: {TEXT}; border: 1px solid {BORDER};
                border-radius: 8px; padding: 10px 16px; font-size: 13px;
            }}
            QPushButton:hover {{ border-color: {ACCENT}; }}
            QPushButton:disabled {{ color: {TEXT2}; }}
            QPushButton#primary {{
                background: {ACCENT}; color: #fff; border: none; font-weight: 700;
            }}
            QPushButton#primary:hover {{ background: {ACCENT2}; }}
            QPushButton#primary:disabled {{ background: {BG3}; color: {TEXT2}; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(10)

        title = QLabel("🆕  Hay una versión nueva de AutoPrevias")
        title.setStyleSheet("font-size: 17px; font-weight: 800;")
        root.addWidget(title)

        sub = QLabel(tr("Versión <b>{v}</b> disponible &nbsp;·&nbsp; tienes la {cur}",
                        v=info.version, cur=current_version))
        i18n.mark_dynamic(sub)
        sub.setStyleSheet(f"font-size: 13px; color: {TEXT2};")
        root.addWidget(sub)

        notes_title = QLabel("Novedades")
        notes_title.setStyleSheet("font-size: 12px; font-weight: 700; margin-top: 6px;")
        root.addWidget(notes_title)

        self._notes = QTextEdit()
        self._notes.setReadOnly(True)
        self._notes.setMarkdown(self._clean_notes(info.notes))
        root.addWidget(self._notes, stretch=1)

        self._bar = QProgressBar()
        self._bar.setVisible(False)
        root.addWidget(self._bar)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setStyleSheet(f"font-size: 12px; color: {TEXT2};")
        root.addWidget(self._status)

        row = QHBoxLayout()
        row.setSpacing(8)
        self._btn_skip = QPushButton("Omitir esta versión")
        self._btn_later = QPushButton("Más tarde")
        self._btn_main = QPushButton("Descargar e instalar")
        self._btn_main.setObjectName("primary")
        self._btn_main.setDefault(True)
        row.addWidget(self._btn_skip)
        row.addStretch()
        row.addWidget(self._btn_later)
        row.addWidget(self._btn_main)
        root.addLayout(row)

        self._btn_skip.clicked.connect(self._on_skip)
        self._btn_later.clicked.connect(self._on_later)
        self._btn_main.clicked.connect(self._on_main)

        if not (self._asset and self._asset in info.assets):
            self._btn_main.setVisible(False)
            self._set_status("Esta versión todavía no tiene instalador disponible para tu sistema.")
        i18n.mark_dynamic(self._status)
        i18n.translate_tree(self)

    @staticmethod
    def _clean_notes(notes: str) -> str:
        text = strip_links(notes).strip()
        if not text:
            return "Mejoras y correcciones de la nueva versión."
        return text[:4000] + ("…" if len(text) > 4000 else "")

    def _set_status(self, msg: str, color: str = TEXT2):
        self._status.setText(i18n.translate(msg))
        self._status.setStyleSheet(f"font-size: 12px; color: {color};")

    def _on_main(self):
        if self._state == _READY:
            self._install_and_quit()
        elif self._state in (_IDLE, _FAILED):
            self._start_download()

    def _on_later(self):
        self.reject()

    def _on_skip(self):
        set_skipped_version(self._info.version)
        self.reject()

    def _cancel_download(self):
        if self._downloader is not None and self._downloader.isRunning():
            self._downloader.cancel()
            self._downloader.wait(3000)

    def done(self, result):
        self._cancel_download()
        super().done(result)

    # ── Descarga ──────────────────────────────────────────────────────────
    def _start_download(self):
        from src.update import UpdateDownloader
        self._state = _DOWNLOADING
        self._btn_main.setEnabled(False)
        self._btn_skip.setEnabled(False)
        self._btn_later.setText(tr("Cancelar"))
        self._bar.setVisible(True)
        self._bar.setRange(0, 0)
        self._set_status("Preparando descarga…")

        self._downloader = UpdateDownloader(self._asset, self._info, parent=self)
        self._downloader.progress.connect(self._on_progress)
        self._downloader.status.connect(self._set_status)
        self._downloader.finished_ok.connect(self._on_downloaded)
        self._downloader.failed.connect(self._on_failed)
        self._downloader.start()

    def _on_progress(self, done: int, total: int):
        if total > 0:
            self._bar.setRange(0, 100)
            self._bar.setValue(int(done * 100 / total))
            self._set_status(tr("Descargando… {done} de {total}", done=_fmt_mb(done), total=_fmt_mb(total)))
        else:
            self._set_status(tr("Descargando… {done}", done=_fmt_mb(done)))

    def _on_downloaded(self, path: str):
        self._state = _READY
        self._installer_path = path
        self._bar.setRange(0, 100)
        self._bar.setValue(100)
        self._btn_later.setText(tr("Más tarde"))
        self._btn_skip.setEnabled(True)
        self._btn_main.setEnabled(True)
        self._btn_main.setText(tr("Instalar y cerrar AutoPrevias"))
        folder = os.path.basename(os.path.dirname(path))
        folder = "Descargas" if folder.lower() == "downloads" else (folder or "Descargas")
        if sys.platform == "darwin":
            self._set_status(tr("✅ Descargado en «{folder}» y verificado. Se abrirá el instalador: "
                                "arrastra AutoPrevias a Aplicaciones y vuelve a abrir la app.", folder=folder), GREEN)
        else:
            self._set_status(tr("✅ Descargado en «{folder}» y verificado. Se abrirá el instalador y "
                                "AutoPrevias se cerrará para poder actualizarse.", folder=folder), GREEN)

    def _on_failed(self, msg: str):
        self._state = _FAILED
        self._bar.setVisible(False)
        self._btn_later.setText(tr("Cerrar"))
        self._btn_skip.setEnabled(True)
        self._btn_main.setEnabled(True)
        self._btn_main.setText(tr("Reintentar"))
        self._set_status(f"❌ {i18n.translate(msg)}", RED)

    def _install_and_quit(self):
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", self._installer_path])
            elif sys.platform == "win32":
                os.startfile(self._installer_path)  # type: ignore[attr-defined]
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(self._installer_path))
        except Exception:
            self._set_status("❌ No se pudo abrir el instalador. Búscalo en tu carpeta Descargas "
                             "y ábrelo manualmente.", RED)
            return
        self.accept()
        QApplication.quit()
