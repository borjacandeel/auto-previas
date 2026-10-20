#!/usr/bin/env python3
"""
Dibuja el icono de AutoPrevias (cuadrado redondeado granate con el emblema «RR» de Radical Records) en alta resolución.

Entrada : assets/logo1_raw.png (emblema blanco sobre negro, 741×595).
Salida  : assets/app_icon_1024.png      (el icono llena casi todo el lienzo: Windows, ventana, notificaciones)
          assets/app_icon_mac_1024.png  (cuadrícula de macOS: el cuerpo ocupa 824 de 1024 px)
          assets/notify_icon.png        (512 px, el mismo icono de la app: decisión del usuario)
          assets/icon.ico / assets/icon.icns (vía scripts/generate_icons.py)
Se ejecuta a mano cuando cambia el diseño; los resultados se suben al repositorio.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
EMBLEM = ASSETS / "logo1_raw.png"

BORDER = (232, 42, 66)


def _body(size: int) -> Image.Image:
    """Cuerpo del icono (degradado + resplandor + borde rojo) de `size`×`size`, con las esquinas transparentes."""
    S = size * 2                                                 # se dibuja al doble y se reduce: bordes suaves
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / (S - 1)
    top, bot = np.array([14, 10, 14], np.float32), np.array([112, 14, 33], np.float32)
    t = (yy ** 1.55)[..., None]
    img = top + (bot - top) * t
    glow = np.clip(1.0 - np.hypot((xx - 0.5) * 1.25, (yy - 1.0) * 0.95) / 0.78, 0, 1) ** 1.6
    img = img + (np.array([160, 24, 56], np.float32) - img) * (glow[..., None] * 0.85)
    rgb = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").convert("RGBA")

    radius = int(S * 0.245)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius, fill=255)
    bw = max(3, int(S * 0.009))
    ring = ImageChops.subtract(mask, Image.new("L", (S, S), 0))
    inner = Image.new("L", (S, S), 0)
    ImageDraw.Draw(inner).rounded_rectangle((bw, bw, S - 1 - bw, S - 1 - bw), max(1, radius - bw), fill=255)
    ring = ImageChops.subtract(mask, inner)
    border = Image.new("RGBA", (S, S), BORDER + (255,))
    rgb.paste(border, (0, 0), ring)
    # brillo suave del borde hacia dentro
    halo = ring.filter(ImageFilter.GaussianBlur(S * 0.012))
    halo = ImageChops.multiply(halo, inner).point(lambda v: int(v * 0.55))
    rgb.paste(Image.new("RGBA", (S, S), (255, 40, 70, 255)), (0, 0), halo)
    rgb.putalpha(mask)

    # emblema blanco con resplandor
    em = Image.open(EMBLEM).convert("L")
    bbox = em.point(lambda v: 255 if v > 40 else 0).getbbox()
    em = em.crop(bbox)
    target_w = int(S * 0.76)
    scale = target_w / em.width
    em = em.resize((target_w, int(em.height * scale)), Image.LANCZOS)
    pad = int(S * 0.04)                                          # margen para que el resplandor no se corte
    em_p = Image.new("L", (em.width + 2 * pad, em.height + 2 * pad), 0)
    em_p.paste(em, (pad, pad))
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ex, ey = (S - em_p.width) // 2, int((S - em_p.height) / 2)
    white = Image.new("RGBA", em_p.size, (255, 255, 255, 255))
    white.putalpha(em_p)
    pink = Image.new("RGBA", em_p.size, (255, 70, 100, 255))
    pink.putalpha(em_p.filter(ImageFilter.GaussianBlur(S * 0.011)).point(lambda v: min(255, int(v * 0.8))))
    layer.alpha_composite(pink, (ex, ey))
    layer.alpha_composite(white, (ex, ey))
    rgb.alpha_composite(layer)
    rgb.putalpha(mask)
    return rgb.resize((size, size), Image.LANCZOS)


def main() -> int:
    if not EMBLEM.exists():
        print(f"Error: falta {EMBLEM}")
        return 1
    # Windows / ventana / notificaciones: el cuerpo llena el 94 % del lienzo
    canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    body = _body(int(1024 * 0.94))
    canvas.alpha_composite(body, ((1024 - body.width) // 2, (1024 - body.height) // 2))
    canvas.save(ASSETS / "app_icon_1024.png")
    # macOS: plantilla de Apple (824 px de cuerpo en 1024)
    mac = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    mb = _body(824)
    mac.alpha_composite(mb, (100, 100))
    mac.save(ASSETS / "app_icon_mac_1024.png")
    canvas.resize((512, 512), Image.LANCZOS).save(ASSETS / "notify_icon.png")
    print("[OK] app_icon_1024.png, app_icon_mac_1024.png, notify_icon.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
