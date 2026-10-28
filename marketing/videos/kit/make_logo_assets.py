"""Imágenes del vídeo «Tu logo en cada vídeo»: logo de ejemplo, fotogramas reales del motor con el logo (3 formatos)
y capturas reales de la ventana «Ajustes del vídeo» con el logo en distintos estados (p_logo_0..3)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1.6")
import tempfile
os.environ["HOME"] = tempfile.mkdtemp(prefix="ap_logo_home_")

import numpy as np
from PIL import Image, ImageDraw, ImageFont

VID = ROOT / "marketing" / "videos"
STILLS = VID / "stills"
WORK = ROOT / "docs" / "manual" / "_work" / "plus"
SCR = Path("/tmp/claude-0/-home-user-auto-previas/6b1ecf54-1d04-5f4e-928d-776ea9cba7c0/scratchpad/neon")
LOGO = STILLS / "logo_demo.png"


def make_logo():
    f = ImageFont.truetype(str(ROOT / "assets" / "fonts" / "Inter-BlackItalic.otf"), 150)
    im = Image.new("RGBA", (760, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, 753, 293), 56, outline=(255, 255, 255, 255), width=12, fill=(10, 10, 16, 235))
    tw = d.textlength("DJ NOVA", font=f)
    d.text(((760 - tw) / 2, 52), "DJ NOVA", font=f, fill=(255, 255, 255, 255))
    d.rectangle((150, 232, 610, 246), fill=(255, 31, 58, 255))
    im.save(LOGO)


def make_stills():
    from src.engine import video_neon as vn
    an = vn.analyze_audio(str(SCR / "sample_audio.wav"))
    cp = STILLS / "cover_crimson.png"
    lg = {"path": str(LOGO), "x": 0.80, "y": 0.09, "size": 0.26}
    for asp, nm, pos in (("9:16", "logo_916", (0.80, 0.075)), ("1:1", "logo_11", (0.80, 0.10)), ("16:9", "logo_169", (0.86, 0.12))):
        r = vn._Renderer(an, str(cp), "Midnight Groove", "DJ Nova", 128.0, "11B · A", asp, "crimson", "", "PREVIA EXCLUSIVA", 1.0,
                         custom={"logo": dict(lg, x=pos[0], y=pos[1])})
        for i in range(380, 401):
            r.frame(i, i / 30)
        r.frame(401, 401 / 30).convert("RGB").save(STILLS / f"{nm}.jpg", quality=88)


def make_captures():
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    from src.ui import video_custom as vc
    dlg = vc.VideoCustomDialog({}, None, sample={"title": "Midnight Groove", "artist": "DJ Nova", "aspect": "9:16",
                                                 "cover": str(STILLS / "cover_crimson.png"), "bpm": 128, "key": "11B · A"})
    dlg.show()
    dlg.resize(860, 1000)
    steps = []

    def grab(n):
        dlg.grab().save(str(WORK / f"p_logo_{n}.png"))

    def s0():
        grab(0)
        dlg._set_logo_path(str(LOGO))
        dlg._logo.update({"x": 0.80, "y": 0.075, "size": 0.26})
        dlg._refresh_logo_ui()
        QTimer.singleShot(500, s1)

    def s1():
        grab(1)
        dlg._logo.update({"x": 0.22, "y": 0.80, "size": 0.34})          # arrastrado abajo a la izquierda y más grande
        dlg._refresh_logo_ui()
        QTimer.singleShot(500, s2)

    def s2():
        grab(2)
        dlg._logo.update({"x": 0.5, "y": 0.50, "size": 0.40, "rotate": -12.0, "opacity": 0.6, "flip_h": True})
        dlg._refresh_logo_ui()
        QTimer.singleShot(500, s3)

    def s3():
        grab(3)
        app.quit()
    QTimer.singleShot(9000, s0)
    app.exec()


if __name__ == "__main__":
    STILLS.mkdir(exist_ok=True)
    make_logo()
    make_stills()
    make_captures()
    print("ok")
