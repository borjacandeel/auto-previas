"""Prepara los recursos del vídeo: capturas reales de la app (de docs/manual/_work/plus),
logos de Radical Records, tipografía Inter y grano de película.
Antes: python scripts/manual/capture.py plus   (genera las capturas y sus rectángulos)"""
import json, shutil
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "docs" / "manual" / "_work" / "plus"
OUT = HERE / "assets"
OUT.mkdir(exist_ok=True)

for name in ("01_bienvenida", "02_analisis", "03_cargada", "04_editor_cortes", "05_editor_bpm", "07_promo", "08_generada"):
    Image.open(SRC / f"{name}.png").convert("RGB").save(OUT / f"{name}.jpg", quality=90, optimize=True)
for name in ("13_recientes", "14_lote"):
    Image.open(SRC / f"{name}.png").convert("RGB").save(OUT / f"{name}.jpg", quality=92, optimize=True)
for logo in ("logo_emblem", "logo_banner", "logo_emblem_red", "logo_banner_red"):
    shutil.copy(ROOT / "assets" / f"{logo}.png", OUT / f"{logo}.png")
fonts = OUT / "fonts"; fonts.mkdir(exist_ok=True)
for f in ("Inter-Black.otf", "Inter-ExtraBold.otf", "Inter-Bold.otf", "Inter-Medium.otf"):
    p = Path("/usr/share/fonts/opentype/inter") / f
    if p.exists():
        shutil.copy(p, fonts / f)
# grano (determinista)
rng = np.random.default_rng(3)
g = (rng.random((256, 256)) * 255).astype("uint8")
Image.fromarray(np.dstack([g, g, g, np.full_like(g, 255)]), "RGBA").save(OUT / "grain.png")
meta = json.loads((SRC / "meta.json").read_text())
(HERE / "rects.json").write_text(json.dumps(meta["rects"], indent=1))
print("OK", sorted(p.name for p in OUT.iterdir()))
