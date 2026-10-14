"""Materiales del vídeo tutorial (16:9): fotos de ejemplo y fotogramas reales del motor «Radical Neón» para cada opción.

Genera en marketing/videos/stills/tutorial/:
  foto_16x9.jpg · foto_9x16.jpg · foto_1x1.jpg · foto_4x3.jpg   (fotos de ejemplo de un evento, mismo motivo en 4 formatos)
  tut_*.jpg                                                         (fotogramas del motor para cada ejemplo del tutorial)
Uso: python make_tutorial_assets.py [--solo-fotos]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

OUT = ROOT / "marketing" / "videos" / "stills" / "tutorial"
OUT.mkdir(parents=True, exist_ok=True)
COVER = ROOT / "marketing" / "videos" / "stills" / "cover_crimson.png"


def make_photo(w: int, h: int, path: Path):
    """Foto de ejemplo de una sala de club (haces de luz, bokeh y público), en coordenadas relativas para que
    el mismo motivo se vea bien en 9:16, 1:1, 4:3 y 16:9."""
    m = min(w, h)
    rng = np.random.default_rng(7)
    yy = np.linspace(0, 1, h)[:, None]
    top, bot = np.array([8, 5, 28], np.float32), np.array([58, 10, 82], np.float32)
    arr = (top * (1 - yy) + bot * yy)[:, None, :].repeat(w, 1).reshape(h, w, 3) if False else None
    base = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        base[..., c] = (top[c] * (1 - yy) + bot[c] * yy)
    im = Image.fromarray(base.clip(0, 255).astype(np.uint8), "RGB")
    # haz de luz
    beams = Image.new("RGB", (w, h), (0, 0, 0))
    bd = ImageDraw.Draw(beams)
    cols = [(255, 40, 90), (120, 60, 255), (40, 200, 255), (255, 120, 40), (255, 40, 160)]
    for k, ox in enumerate((0.12, 0.32, 0.52, 0.72, 0.9)):
        sx = ox * w
        tgt = (0.5 + (ox - 0.5) * 1.9 + rng.uniform(-0.15, 0.15)) * w
        wid = 0.07 * w
        bd.polygon([(sx - 6, 0), (sx + 6, 0), (tgt + wid, h * 0.86), (tgt - wid, h * 0.86)], fill=tuple(int(c * 0.55) for c in cols[k]))
    beams = beams.filter(ImageFilter.GaussianBlur(m * 0.018))
    im = ImageChops.add(im, beams)
    # niebla central
    haze = Image.new("RGB", (w, h), (0, 0, 0))
    ImageDraw.Draw(haze).ellipse((w * 0.22, h * 0.30, w * 0.78, h * 0.95), fill=(150, 20, 90))
    im = ImageChops.add(im, haze.filter(ImageFilter.GaussianBlur(m * 0.18)))
    # bokeh
    bok = Image.new("RGB", (w, h), (0, 0, 0))
    bk = ImageDraw.Draw(bok)
    for _ in range(46):
        x, y, r = rng.uniform(0, w), rng.uniform(0, h * 0.8), rng.uniform(0.012, 0.045) * m
        c = cols[int(rng.integers(0, len(cols)))]
        bk.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(v * rng.uniform(0.18, 0.5)) for v in c))
    im = ImageChops.add(im, bok.filter(ImageFilter.GaussianBlur(m * 0.004)))
    # público (siluetas con brazos en alto)
    sil = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(sil)
    base_y = h * 0.90
    x = -0.02 * w
    while x < w * 1.02:
        hr = rng.uniform(0.018, 0.03) * m
        cy = base_y - rng.uniform(0, 0.05) * h
        sd.ellipse((x - hr, cy - hr, x + hr, cy + hr), fill=255)
        sd.rectangle((x - hr * 1.5, cy + hr * 0.6, x + hr * 1.5, h), fill=255)
        if rng.random() < 0.45:
            ax = x + rng.choice([-1, 1]) * hr * 1.7
            sd.line((ax, cy + hr, ax + rng.uniform(-0.01, 0.01) * m, cy - hr * rng.uniform(3, 5)), fill=255, width=int(max(3, hr * 0.7)))
        x += rng.uniform(1.6, 2.7) * hr
    sil = sil.filter(ImageFilter.GaussianBlur(m * 0.0012))
    im = Image.composite(Image.new("RGB", (w, h), (4, 2, 10)), im, sil)
    # grano suave
    n = (rng.normal(0, 4, (h, w, 1)) * np.ones((1, 1, 3))).astype(np.float32)
    im = Image.fromarray(np.clip(np.asarray(im, np.float32) + n, 0, 255).astype(np.uint8), "RGB")
    im.save(path, quality=92)


for nm, (w, h) in (("16x9", (1920, 1080)), ("9x16", (1080, 1920)), ("1x1", (1080, 1080)), ("4x3", (1600, 1200))):
    make_photo(w, h, OUT / f"foto_{nm}.jpg")
print("fotos listas")
if "--solo-fotos" in sys.argv:
    sys.exit(0)

# ───────────── fotogramas con el motor real ─────────────
import subprocess
from src.engine import video_neon as vn
from src.config import get_ffmpeg_path

SRC = Path("/tmp/claude-0/ana_track.wav")
EXC = Path("/tmp/claude-0/tut_excerpt.wav")
if not EXC.exists():
    subprocess.run([get_ffmpeg_path() or "ffmpeg", "-y", "-v", "error", "-ss", "52", "-t", "20", "-i", str(SRC), "-ac", "2", "-ar", "44100", str(EXC)], check=True)
AN = vn.analyze_audio(str(EXC))
FRAME = 401 if AN.n_frames > 402 else AN.n_frames - 2
TITLE, ARTIST, BPM, KEY = "Midnight Groove", "Radical Records", 128.0, "11B · A"
BANNER = "RADICAL RECORDS · PROMO EXCLUSIVA"


def still(name, aspect="16:9", custom=None, title=TITLE, banner="", pal="crimson", cover=None, end_mode="brand", at=None):
    r = vn._Renderer(AN, str(cover or COVER), title, ARTIST, BPM, KEY, aspect, pal, banner, "PREVIA EXCLUSIVA", 1.0, end_mode=end_mode, custom=custom)
    i = FRAME if at is None else at
    for k in range(max(0, i - 22), i):
        r.frame(k, k / 30)
    im = r.frame(i, i / 30).convert("RGB")
    im.save(OUT / f"{name}.jpg", quality=90)
    print("still", name)
    return r, im


def photo(nm):
    return str(OUT / f"foto_{nm}.jpg")


BG = {"default": photo("16x9")}
IMG = {"style": "image", "bg": BG}
# formatos (una imagen por formato)
PER = {"style": "image", "bg": {"9:16": photo("9x16"), "1:1": photo("1x1"), "16:9": photo("16x9")}}
for asp, key in (("9:16", "916"), ("1:1", "11"), ("16:9", "169")):
    still(f"tut_fmt_{key}_foto", asp, PER, banner=BANNER)
    still(f"tut_fmt_{key}_neon", asp, None, banner=BANNER)
# paletas (neón, 16:9)
for pal in ("radical", "rave", "crimson", "amber", "cyber"):
    cv = ROOT / "marketing" / "videos" / "stills" / f"cover_{pal}.png"
    still(f"tut_pal_{pal}", "16:9", None, pal=pal, cover=cv, title="Midnight Groove" if pal == "crimson" else {"radical": "Neon Drift", "rave": "Acid Rain", "amber": "Solar Flare", "cyber": "Void Rave"}[pal])
# título y banner
still("tut_title_pista", "16:9", None, title="Midnight Groove (Original Mix)")
still("tut_title_propio", "16:9", None, title="Midnight Groove")
still("tut_banner_off", "16:9", None, banner="")
still("tut_banner_on", "16:9", None, banner=BANNER)
# looks
for look in vn.LOOKS:
    still(f"tut_look_{look}", "16:9", vn.apply_look({"bg": BG}, look), banner=BANNER)
# fondo con imagen: encaje (foto 4x3 en 16:9)
F43 = {"default": photo("4x3")}
still("tut_fit_crop", "16:9", vn.normalize_custom({"style": "image", "bg": F43, "fit": "crop"}))
still("tut_fit_blur", "16:9", vn.normalize_custom({"style": "image", "bg": F43, "fit": "blur"}))
# onda: estilo, posición, color
for st in ("bars", "line", "circle"):
    still(f"tut_wave_{st}", "16:9", vn.normalize_custom({**IMG, "wave_style": st, "wave_pos": "bottom" if st != "circle" else "center"}))
for pos in ("top", "center", "bottom"):
    still(f"tut_wpos_{pos}", "16:9", vn.normalize_custom({**IMG, "wave_style": "bars", "wave_pos": pos, "texts_pos": "top" if pos != "top" else "bottom"}))
still("tut_wcol_white", "16:9", vn.normalize_custom({**IMG, "wave_style": "bars", "wave_color": "white"}))
still("tut_wcol_palette", "16:9", vn.normalize_custom({**IMG, "wave_style": "bars", "wave_color": "palette"}))
# textos
still("tut_txt_todos", "16:9", vn.normalize_custom({**IMG}), banner=BANNER)
still("tut_txt_titulo", "16:9", vn.normalize_custom({**IMG, "artist": False, "chips": False, "kicker": False}))
still("tut_txt_ninguno", "16:9", vn.normalize_custom({**IMG, "texts": False}))
still("tut_txt_solofoto", "16:9", vn.normalize_custom({**IMG, "only_photo": True}), banner=BANNER)
# finales
dur_i = AN.n_frames - 8
r_b, _ = still("tut_end_brand_0", "16:9", None, end_mode="brand")
r_b.outro.convert("RGB").save(OUT / "tut_end_brand.jpg", quality=90)
_, last = still("tut_end_none", "16:9", None, end_mode="none")
Image.blend(last, Image.new("RGB", last.size, (0, 0, 0)), 0.62).save(OUT / "tut_end_fade.jpg", quality=90)
EI = vn.normalize_custom({"end_image": photo("16x9"), "end_text": "Disponible en Beatport"})
r_i = vn._Renderer(AN, str(COVER), TITLE, ARTIST, BPM, KEY, "16:9", "crimson", "", "PREVIA EXCLUSIVA", 1.0, end_mode="image", custom=EI)
r_i.outro.convert("RGB").save(OUT / "tut_end_image.jpg", quality=90)
print("stills del tutorial listos:", len(list(OUT.glob("tut_*.jpg"))))
