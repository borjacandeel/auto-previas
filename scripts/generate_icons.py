#!/usr/bin/env python3
"""
Genera assets/icon.icns y assets/icon.ico a partir de assets/logo_emblem.png
Centra la imagen en un lienzo cuadrado transparente con margen armónico.
"""
from pathlib import Path
import subprocess
import shutil
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE_PNG = ROOT / "assets" / "logo_emblem.png"
ICNS_OUT = ROOT / "assets" / "icon.icns"
ICO_OUT = ROOT / "assets" / "icon.ico"


def create_square_canvas(src: Image.Image, size: int = 1024) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # Escalar para que el lado más largo ocupe ~88% del lienzo para dejar margen
    target_max = int(size * 0.88)
    src_w, src_h = src.size
    ratio = min(target_max / src_w, target_max / src_h)
    new_w, new_h = int(src_w * ratio), int(src_h * ratio)
    resized = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
    pos_x = (size - new_w) // 2
    pos_y = (size - new_h) // 2
    canvas.paste(resized, (pos_x, pos_y), resized if resized.mode == "RGBA" else None)
    return canvas


def main():
    if not SOURCE_PNG.exists():
        print(f"Error: {SOURCE_PNG} no existe")
        return 1

    src = Image.open(SOURCE_PNG).convert("RGBA")
    master = create_square_canvas(src, 1024)

    # 1. Generar .ico para Windows
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    master.save(ICO_OUT, format="ICO", sizes=ico_sizes)
    print(f"✓ Creado: {ICO_OUT}")

    # 2. Generar .icns para macOS
    with tempfile.TemporaryDirectory() as tmpdir:
        iconset = Path(tmpdir) / "icon.iconset"
        iconset.mkdir()

        specs = [
            (16, "icon_16x16.png"),
            (32, "icon_16x16@2x.png"),
            (32, "icon_32x32.png"),
            (64, "icon_32x32@2x.png"),
            (128, "icon_128x128.png"),
            (256, "icon_128x128@2x.png"),
            (256, "icon_256x256.png"),
            (512, "icon_256x256@2x.png"),
            (512, "icon_512x512.png"),
            (1024, "icon_512x512@2x.png"),
        ]

        for sz, fname in specs:
            img = master.resize((sz, sz), Image.Resampling.LANCZOS)
            img.save(iconset / fname, "PNG")

        cmd = ["iconutil", "-c", "icns", str(iconset), "-o", str(ICNS_OUT)]
        try:
            subprocess.run(cmd, check=True)
            print(f"✓ Creado: {ICNS_OUT}")
        except Exception as e:
            print(f"Aviso: iconutil falló o no disponible ({e}). Guardando como PNG si aplica.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
