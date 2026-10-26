"""Vista previa del vídeo animado Radical Neón: unos segundos de la pista a baja resolución + cierre con firma."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from src.i18n import tr

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    HAS_MM = True
except Exception:  # pragma: no cover
    HAS_MM = False


class PreviewWorker(QThread):
    progress = Signal(int, str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, params: dict, parent=None):
        super().__init__(parent)
        self.params = params

    def run(self):
        try:
            from src.engine.video_neon import render_preview
            res = render_preview(progress_cb=lambda p, m: self.progress.emit(int(p), m), **self.params)
            self.done.emit(res)
        except Exception as e:
            self.failed.emit(str(e))


def pil_to_pixmap(im) -> QPixmap:
    im = im.convert("RGB")
    qi = QImage(im.tobytes(), im.width, im.height, 3 * im.width, QImage.Format_RGB888).copy()
    return QPixmap.fromImage(qi)


class VideoPreviewDialog(QDialog):
    """Genera en segundo plano la muestra y la reproduce en bucle (con sonido si hay multimedia)."""

    def __init__(self, params: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Vista previa del vídeo"))
        self.setModal(False)
        self._pix: list = []
        self._idx = 0
        self._player = None
        self._audio = None
        self._clip = ""

        lay = QVBoxLayout(self)
        self._lbl_video = QLabel(tr("Preparando la vista previa…"))
        self._lbl_video.setAlignment(Qt.AlignCenter)
        self._lbl_video.setMinimumSize(300, 300)
        self._lbl_video.setStyleSheet("background:#05060a; color:#c9ccd8; border-radius:10px; font-size:12px;")
        lay.addWidget(self._lbl_video, stretch=1)
        self._lbl_msg = QLabel(tr("Es una muestra de unos segundos a baja resolución; el vídeo final sale a 1080p con el audio completo."))
        self._lbl_msg.setWordWrap(True)
        self._lbl_msg.setStyleSheet("color:#8a8fa3; font-size:10.5px;")
        lay.addWidget(self._lbl_msg)
        row = QHBoxLayout()
        row.addStretch()
        self._btn_close = QPushButton(tr("Cerrar"))
        self._btn_close.clicked.connect(self.close)
        row.addWidget(self._btn_close)
        lay.addLayout(row)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._worker = PreviewWorker(params, self)
        self._worker.progress.connect(lambda p, m: self._lbl_video.setText(f"{tr(m)}  {p}%"))
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_failed(self, msg: str):
        self._lbl_video.setText(tr("⚠ No se pudo crear la vista previa: {err}", err=msg[:160]))

    def _on_done(self, res: dict):
        self._pix = [pil_to_pixmap(f) for f in res["frames"]]
        self._clip = res.get("audio") or ""
        if not self._pix:
            return self._on_failed("sin fotogramas")
        pm = self._pix[0]
        self._lbl_video.setMinimumSize(pm.width(), pm.height())
        self._lbl_video.setMaximumSize(pm.width(), pm.height())
        self._lbl_msg.setFixedWidth(max(300, pm.width()))
        self.layout().activate()
        self.setFixedSize(self.sizeHint())
        self._interval = int(1000 / max(1, res.get("fps", 15)))
        if HAS_MM and self._clip:
            try:
                self._player = QMediaPlayer(self)
                self._audio = QAudioOutput(self)
                self._player.setAudioOutput(self._audio)
                self._player.setSource(QUrl.fromLocalFile(self._clip))
            except Exception:
                self._player = None
        self._restart()
        self._timer.start(self._interval)

    def _restart(self):
        self._idx = 0
        if self._player is not None:
            try:
                self._player.stop()
                self._player.play()
            except Exception:
                pass

    def _tick(self):
        if not self._pix:
            return
        self._lbl_video.setPixmap(self._pix[self._idx])
        self._idx += 1
        if self._idx >= len(self._pix):
            self._timer.stop()
            QTimer.singleShot(700, self._loop)

    def _loop(self):
        if self.isVisible() and self._pix:
            self._restart()
            self._timer.start(self._interval)

    def _cleanup(self):
        self._timer.stop()
        try:
            if self._player is not None:
                self._player.stop()
                self._player.setSource(QUrl())          # Windows no borra archivos abiertos
            if self._worker.isRunning():
                self._worker.wait(8000)
            if self._clip:
                Path(self._clip).unlink(missing_ok=True)
                self._clip = ""
        except Exception:
            pass

    def done(self, r):                                  # Esc / Cerrar / aceptar: no pasan por closeEvent
        self._cleanup()
        super().done(r)

    def closeEvent(self, e):
        self._cleanup()
        super().closeEvent(e)
