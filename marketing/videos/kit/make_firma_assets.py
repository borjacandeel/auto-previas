"""Capturas reales de «Firmar tema entero» para el vídeo «Firma tus temas»: sin carátula → con carátula y etiquetas → firmado."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_SCALE_FACTOR"] = "1.6"
HOME = Path(tempfile.mkdtemp(prefix="ap_firma_home_"))
os.environ["HOME"] = str(HOME)

VID = ROOT / "marketing" / "videos"
WORK = ROOT / "docs" / "manual" / "_work" / "plus"
TRACK = Path("/tmp/claude-0/-home-user-auto-previas/6b1ecf54-1d04-5f4e-928d-776ea9cba7c0/scratchpad/demo_track.wav")


def main():
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    from src.ui.sign_track import SignTrackDialog
    d = SignTrackDialog({"output_dir": str(HOME / "Music" / "Previas"), "sign_finder_compat": True}, files=[str(TRACK)])
    d.resize(820, 860)
    d.show()

    def grab(n):
        d.grab().save(str(WORK / f"p_firma_{n}.png"))

    def s0():
        grab(0)
        d._set_cover(str(VID / "stills" / "cover_crimson.png"))
        for k, v in (("title", "Midnight Groove"), ("artist", "DJ Nova"), ("album", "Midnight EP"), ("label", "Radical Records"),
                     ("genre", "Techno"), ("comment", "Previa exclusiva")):
            d._ed[k].setText(v)
        QTimer.singleShot(600, s1)

    def s1():
        grab(1)
        d._start()
        QTimer.singleShot(1500, wait)

    def wait():
        if d._worker is not None and d._worker.isRunning():
            QTimer.singleShot(800, wait)
        else:
            QTimer.singleShot(800, s2)

    def s2():
        grab(2)
        os._exit(0)
    QTimer.singleShot(1500, s0)
    app.exec()


main()
