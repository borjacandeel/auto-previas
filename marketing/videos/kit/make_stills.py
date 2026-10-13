"""Genera las imágenes «Radical Neón» de muestra (5 paletas, 3 formatos, marca de agua Basic) con el motor real de la app."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from src.engine import video_neon as vn

OUT = Path(__file__).resolve().parents[1] / "stills"
OUT.mkdir(exist_ok=True)
SCR = Path("/tmp/claude-0/-home-user-auto-previas/6b1ecf54-1d04-5f4e-928d-776ea9cba7c0/scratchpad/neon")
AUDIO = SCR / "sample_audio.wav"
FONT = str(Path(__file__).resolve().parents[3] / "assets" / "fonts" / "Inter-BlackItalic.otf")


def cover(name: str, hue: tuple, path: Path):
    W = 1200
    im = Image.new("RGB", (W, W), (12, 8, 30))
    d = ImageDraw.Draw(im)
    for k in range(W):
        t = k / W
        d.line([(0, k), (W, k)], fill=(int(hue[0][0] * (1 - t) + hue[1][0] * t), int(hue[0][1] * (1 - t) + hue[1][1] * t), int(hue[0][2] * (1 - t) + hue[1][2] * t)))
    glow = Image.new("RGB", (W, W), (0, 0, 0)); g = ImageDraw.Draw(glow)
    g.ellipse((260, 200, 940, 880), fill=hue[2]); glow = glow.filter(ImageFilter.GaussianBlur(70))
    im = ImageChops.add(im, glow)
    d = ImageDraw.Draw(im)
    d.ellipse((330, 270, 870, 810), fill=(10, 8, 20), outline=(255, 255, 255), width=8)
    f = ImageFont.truetype(FONT, 110 if len(name) < 12 else 92)
    tw = d.textlength(name, font=f)
    d.text(((W - tw) / 2, 930), name, font=f, fill=(255, 255, 255))
    im.save(path)


COVERS = [
    ("MIDNIGHT GROOVE", ((40, 10, 120), (180, 20, 70), (255, 60, 120)), "crimson"),
    ("ACID RAIN", ((5, 40, 20), (20, 120, 40), (90, 255, 40)), "rave"),
    ("SOLAR FLARE", ((90, 30, 0), (200, 90, 0), (255, 190, 20)), "amber"),
    ("NEON DRIFT", ((0, 20, 60), (0, 110, 140), (0, 240, 255)), "radical"),
    ("VOID RAVE", ((30, 0, 70), (100, 20, 160), (190, 60, 255)), "cyber"),
]

an = vn.analyze_audio(str(AUDIO))
FR = 401
for name, hue, pal in COVERS:
    cp = OUT / f"cover_{pal}.png"
    cover(name, hue, cp)
    r = vn._Renderer(an, str(cp), name.title(), "Radical Records", 128.0, "11B · A", "9:16", pal, "PROMO EXCLUSIVA · RADICAL RECORDS", "PREVIA EXCLUSIVA", 1.0)
    for i in range(380, FR):
        r.frame(i, i / 30)
    r.frame(FR, FR / 30).convert("RGB").save(OUT / f"neon_916_{pal}.jpg", quality=88)
    if pal == "crimson":
        for asp, nm in (("1:1", "neon_11"), ("16:9", "neon_169")):
            r2 = vn._Renderer(an, str(cp), name.title(), "Radical Records", 128.0, "11B · A", asp, pal, "PROMO EXCLUSIVA · RADICAL RECORDS", "PREVIA EXCLUSIVA", 1.0)
            for i in range(380, FR):
                r2.frame(i, i / 30)
            r2.frame(FR, FR / 30).convert("RGB").save(OUT / f"{nm}.jpg", quality=88)
        rb = vn._Renderer(an, str(cp), name.title(), "Radical Records", 128.0, "11B · A", "9:16", pal, "", "PREVIA EXCLUSIVA", 1.0, watermark=True)
        for i in range(380, FR):
            rb.frame(i, i / 30)
        rb.frame(FR, FR / 30).convert("RGB").save(OUT / "neon_916_basic.jpg", quality=88)
        r.outro.convert("RGB").save(OUT / "neon_outro_916.jpg", quality=88)
print(sorted(p.name for p in OUT.iterdir()))
