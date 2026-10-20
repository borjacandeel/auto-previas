#!/usr/bin/env python3
"""
Genera assets/icon.ico (Windows) y assets/icon.icns (macOS) a partir del icono de AutoPrevias.

Fuentes (las dibuja scripts/build_app_icon.py y se suben al repositorio):
  assets/app_icon_1024.png      → .ico (el icono llena casi todo el lienzo)
  assets/app_icon_mac_1024.png  → .icns (cuadrícula de macOS: 824 de 1024 px)
En macOS usa `iconutil`; en cualquier sistema, si no está, escribe el .icns con Pillow.
"""
from pathlib import Path
import sys
import subprocess
import shutil
import tempfile
from PIL import Image

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
WIN_PNG = ROOT / "assets" / "app_icon_1024.png"
MAC_PNG = ROOT / "assets" / "app_icon_mac_1024.png"
ICNS_OUT = ROOT / "assets" / "icon.icns"
ICO_OUT = ROOT / "assets" / "icon.ico"


def main():
    for p in (WIN_PNG, MAC_PNG):
        if not p.exists():
            print(f"Error: {p} no existe (ejecuta scripts/build_app_icon.py)")
            return 1
    win = Image.open(WIN_PNG).convert("RGBA")
    mac = Image.open(MAC_PNG).convert("RGBA")

    # 1. .ico para Windows
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    win.save(ICO_OUT, format="ICO", sizes=ico_sizes)
    print(f"[OK] Creado: {ICO_OUT}")

    # 2. .icns para macOS
    done = False
    if sys.platform == "darwin" and shutil.which("iconutil"):
        with tempfile.TemporaryDirectory() as tmpdir:
            iconset = Path(tmpdir) / "icon.iconset"
            iconset.mkdir()
            specs = [(16, "icon_16x16.png"), (32, "icon_16x16@2x.png"), (32, "icon_32x32.png"),
                     (64, "icon_32x32@2x.png"), (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
                     (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"), (512, "icon_512x512.png"),
                     (1024, "icon_512x512@2x.png")]
            for sz, fname in specs:
                mac.resize((sz, sz), Image.Resampling.LANCZOS).save(iconset / fname, "PNG")
            try:
                subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(ICNS_OUT)], check=True)
                print(f"[OK] Creado: {ICNS_OUT}")
                done = True
            except Exception as e:
                print(f"Aviso: iconutil falló ({e}); se usa Pillow.")
    if not done:
        mac.save(ICNS_OUT, format="ICNS", sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)])
        print(f"[OK] Creado (Pillow): {ICNS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
