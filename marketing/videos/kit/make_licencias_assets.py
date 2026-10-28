"""Capturas reales para el vídeo «3 o 12 meses»: ⚙ Licencia con días restantes y botones Renovar, menú de licencia caducada
y panel de activación tras caducar. HOME aislado (sin claves ni datos reales: la licencia es un DEMO local)."""
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_SCALE_FACTOR"] = "1.6"
os.environ["HOME"] = tempfile.mkdtemp(prefix="ap_lic_home_")
os.environ["AUTOPREVIAS_DEVICE_ID"] = "demo-device"
WORK = ROOT / "docs" / "manual" / "_work" / "plus"


EDF = ROOT / "src" / "_edition.py"


def main():
    EDF.write_text('BAKED_EDITION = "plus"\n', encoding="utf-8")      # como el instalador real (en desarrollo no muestra la licencia)
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    from src.__version__ import __version__
    from src.config import set_edition
    from src.licensing import license as L
    from src.ui import activate
    from src.ui.about import LicenseDialog
    from src import links
    links.PRICES.clear()                                    # los vídeos no enseñan precios (decisión del usuario)
    L.reverify_if_due = lambda *a, **k: "skipped"          # sin consultar al servidor: la licencia de la captura es solo un DEMO local
    set_edition("plus")
    L.save_local("DEMO", "plus", int(time.time()) + 80 * 86400)
    dlg = LicenseDialog(__version__, "plus")
    dlg.show()
    for _ in range(40):
        app.processEvents(); time.sleep(0.02)
    dlg.grab().save(str(WORK / "p_lic_0.png"))
    if "--keep" not in sys.argv:
        pass
    dlg.close()
    L.clear_local()

    state = {"step": 0}

    def tick():
        top = app.activeModalWidget()
        if top is None:
            return
        if isinstance(top, activate.ExpiredDialog) and state["step"] == 0:
            top.grab().save(str(WORK / "p_lic_1.png"))
            state["step"] = 1
            top._btn_enter.click()
        elif isinstance(top, activate.ActivationDialog) and state["step"] == 1:
            top.grab().save(str(WORK / "p_lic_2.png"))
            state["step"] = 2
            top.reject()
        elif isinstance(top, activate.ExpiredDialog) and state["step"] == 2:
            state["step"] = 3
            top._btn_quit.click()
    t = QTimer()
    t.setInterval(150)
    t.timeout.connect(tick)
    t.start()
    activate.run_expired_flow(None, edition="plus", expired_on="2026-10-22")
    EDF.unlink(missing_ok=True)
    from PIL import Image
    for n in ("p_lic_1", "p_lic_2"):                         # mismo tamaño de lienzo para poder cambiar de una a otra en el vídeo
        im = Image.open(WORK / f"{n}.png").convert("RGB")
        bg = im.getpixel((2, 2))
        canvas = Image.new("RGB", (800, 780), bg)
        canvas.paste(im, ((800 - im.width) // 2, (780 - im.height) // 2))
        canvas.save(WORK / f"{n}.png")
    os._exit(0)


main()
