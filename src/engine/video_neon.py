"""
AutoPrevias — video_neon.py
Vídeo animado «Radical Neón» para Reels / TikTok / Shorts: la carátula del usuario late con el bombo,
los drops disparan flash + glitch, los textos entran con golpe y las barras reaccionan de verdad al audio.

Motor propio en Python: analiza el audio (kick, energía, drops, espectro), dibuja cada fotograma con
Pillow/numpy y se lo pasa a FFmpeg por tubería. Sin dependencias nuevas (ni Chrome ni Node).
Formatos: 9:16 (1080x1920), 1:1 (1080x1080) y 16:9 (1920x1080).
"""
from __future__ import annotations

import math
import os
import subprocess
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from src.config import get_assets_dir, get_cache_dir, get_ffmpeg_path
from src import links as _links
from src import perf as _perf

FPS = 30
ASPECTS = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080)}

# Paletas Radical Neón: (primario, secundario, destello)
NEON_PALETTES = {
    "crimson": ((255, 31, 58), (255, 120, 40), (255, 235, 200)),
    "radical": ((0, 245, 255), (255, 0, 127), (255, 255, 255)),
    "rave":    ((57, 255, 20), (0, 245, 255), (230, 255, 230)),
    "amber":   ((255, 183, 0), (255, 60, 0), (255, 245, 210)),
    "cyber":   ((176, 38, 255), (0, 245, 255), (245, 230, 255)),
}
BG = (5, 6, 10)

# Ajustes de «vídeo propio» (solo Plus): imagen de fondo, onda de sonido, disposición y final con foto
CUSTOM_DEFAULTS = {
    "style": "neon",          # "neon" (plantilla) | "image" (imagen propia)
    "bg": {},                 # {"default": ruta, "9:16": ruta, "1:1": ruta, "16:9": ruta}
    "fit": "crop",            # "crop" (rellena recortando) | "blur" (imagen entera con fondo desenfocado)
    "wave": True,
    "wave_style": "bars",     # "bars" | "line" | "circle"
    "wave_pos": "bottom",     # "top" | "center" | "bottom"
    "wave_color": "palette",  # "palette" | "white"
    "texts": True,            # (compatibilidad) False = sin ningún texto
    "title": True,            # título de la pista
    "artist": True,           # artista
    "chips": True,            # BPM y tonalidad
    "kicker": True,           # etiqueta «PREVIA EXCLUSIVA»
    "only_photo": False,      # solo la foto: sin textos, onda, banner ni barra de progreso
    "texts_pos": "top",       # "top" | "center" | "bottom"
    "end_image": "",          # imagen del final (modo de final «image»)
    "end_text": "",
}
_CHOICES = {"style": ("neon", "image"), "fit": ("crop", "blur"), "wave_style": ("bars", "line", "circle"),
            "wave_pos": ("top", "center", "bottom"), "wave_color": ("palette", "white"), "texts_pos": ("top", "center", "bottom")}


def normalize_custom(c: Optional[dict]) -> dict:
    """Completa y valida los ajustes de vídeo propio (valores desconocidos → por defecto)."""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in CUSTOM_DEFAULTS.items()}
    if isinstance(c, dict):
        for k in out:
            if k in c and c[k] is not None:
                out[k] = c[k]
    for k, allowed in _CHOICES.items():
        if out[k] not in allowed:
            out[k] = CUSTOM_DEFAULTS[k]
    out["wave"], out["texts"] = bool(out["wave"]), bool(out["texts"])
    for k in ("title", "artist", "chips", "kicker", "only_photo"):
        out[k] = bool(out[k])
    if not out["texts"] or out["only_photo"]:          # «sin textos» / «solo la foto» apagan todos los textos
        out["title"] = out["artist"] = out["chips"] = out["kicker"] = False
    if out["only_photo"]:
        out["wave"] = False
    out["texts"] = any(out[k] for k in ("title", "artist", "chips", "kicker"))
    out["bg"] = {str(k): str(v) for k, v in (out["bg"] or {}).items() if v}
    out["end_image"], out["end_text"] = str(out["end_image"] or ""), str(out["end_text"] or "").strip()[:80]
    return out


ASPECT_VALUES = {a: w / h for a, (w, h) in ASPECTS.items()}
_COMMON_RATIOS = ((4, 3), (3, 4), (4, 5), (5, 4), (3, 2), (2, 3), (21, 9), (9, 21), (16, 10), (10, 16), (2, 1), (1, 2))


def match_aspect(w: int, h: int, tol: float = 0.06) -> Optional[str]:
    """Formato de vídeo ('9:16' | '1:1' | '16:9') al que corresponde una imagen w×h, o None si no encaja (±6 %)."""
    if w <= 0 or h <= 0:
        return None
    r = w / h
    for a, v in ASPECT_VALUES.items():
        if abs(r - v) / v <= tol:
            return a
    return None


def describe_ratio(w: int, h: int) -> str:
    """Proporción legible de una imagen: «4:3», «3:2»… o, si no es una habitual, «ancho×alto»."""
    if w <= 0 or h <= 0:
        return "?"
    r = w / h
    for a, b in _COMMON_RATIOS:
        if abs(r - a / b) / (a / b) <= 0.02:
            return f"{a}:{b}"
    m = match_aspect(w, h)
    return m or f"{w}×{h}"


def image_size(path: str) -> Optional[tuple]:
    """(ancho, alto) de una imagen sin cargarla entera; None si no se puede leer."""
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def image_format_problems(custom: dict, aspect: str) -> list:
    """Imágenes elegidas cuyo formato no coincide con el del vídeo `aspect`. Devuelve [(rol, ruta, proporción)], donde rol es
    «fondo» o «final». Se usa antes de exportar para avisar al usuario."""
    c = normalize_custom(custom)
    out = []
    if c["fit"] == "blur":              # la imagen se muestra entera sobre un fondo desenfocado: no hay recorte que avisar
        return out
    if c["style"] == "image":
        p = resolve_bg(c, aspect)
        if p:
            sz = image_size(p)
            if sz and match_aspect(*sz) != aspect:
                out.append(("fondo", p, describe_ratio(*sz)))
    ei = c["end_image"]
    if ei and Path(ei).exists():
        sz = image_size(ei)
        if sz and match_aspect(*sz) != aspect:
            out.append(("final", ei, describe_ratio(*sz)))
    return out


# «Looks» de un clic (Plus): combinaciones listas de fondo, onda y textos. Conservan las imágenes elegidas por el usuario.
LOOKS = ("neon", "bars", "circle", "title", "photo")
LOOK_DEFS = {
    "neon":   {"style": "neon"},
    "bars":   {"style": "image", "only_photo": False, "wave": True, "wave_style": "bars", "wave_pos": "bottom",
               "title": True, "artist": True, "chips": True, "kicker": True, "texts_pos": "top"},
    "circle": {"style": "image", "only_photo": False, "wave": True, "wave_style": "circle", "wave_pos": "center",
               "title": True, "artist": True, "chips": True, "kicker": True, "texts_pos": "top"},
    "title":  {"style": "image", "only_photo": False, "wave": False,
               "title": True, "artist": True, "chips": False, "kicker": False, "texts_pos": "bottom"},
    "photo":  {"style": "image", "only_photo": True},
}


def apply_look(custom: Optional[dict], look: str) -> dict:
    """Aplica un look a los ajustes actuales sin perder las imágenes (fondo por formato, final) ni el ajuste de encaje."""
    if look not in LOOK_DEFS:
        return normalize_custom(custom)
    base = normalize_custom(custom)
    base["texts"] = True                 # el look decide qué textos se ven (si venía de «solo la foto» se recuperan)
    base["wave"] = True if look != "photo" else base["wave"]
    base.update(LOOK_DEFS[look])
    if look not in ("photo",):
        base["only_photo"] = False
    return normalize_custom(base)


def detect_look(custom: Optional[dict]) -> str:
    """Look que coincide con los ajustes actuales, o «custom» si es una combinación propia."""
    c = normalize_custom(custom)
    for look in LOOKS:
        d = normalize_custom({**CUSTOM_DEFAULTS, **LOOK_DEFS[look]}) if look != "neon" else None
        if look == "neon":
            if c["style"] == "neon":
                return "neon"
            continue
        if all(c[k] == d[k] for k in LOOK_DEFS[look] if k != "style") and c["style"] == "image":
            if look == "photo" and not c["only_photo"]:
                continue
            return look
    return "custom"


def resolve_bg(custom: dict, aspect: str) -> Optional[str]:
    """Imagen de fondo para un formato: la específica del formato o, si no hay, la general. None si no existe."""
    bg = custom.get("bg") or {}
    for key in (aspect, "default"):
        p = bg.get(key)
        if p and Path(p).exists():
            return p
    return None


def _fit_image(path: str, w: int, h: int, mode: str) -> Image.Image:
    """Ajusta una imagen a w×h: «crop» la recorta centrada; «blur» la deja entera sobre su propio fondo desenfocado."""
    im = Image.open(path).convert("RGB")
    cover_k = max(w / im.width, h / im.height)
    cov = im.resize((max(w, int(im.width * cover_k + 0.5)), max(h, int(im.height * cover_k + 0.5))), Image.LANCZOS)
    l, t = (cov.width - w) // 2, (cov.height - h) // 2
    cov = cov.crop((l, t, l + w, t + h))
    if mode != "blur":
        return cov
    bg = cov.filter(ImageFilter.GaussianBlur(max(w, h) // 40)).point(lambda v: int(v * 0.55))
    k = min(w / im.width, h / im.height)
    fg = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    bg.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    return bg


# ───────────────────────────── análisis de audio ─────────────────────────────

@dataclass
class AudioAnalysis:
    duration: float
    n_frames: int
    bars: np.ndarray      # (n_frames, n_bars) 0..1, con caída suave
    kick: np.ndarray      # (n_frames,) 0..1, pulso del bombo
    energy: np.ndarray    # (n_frames,) 0..1, volumen suavizado
    drops: list           # fotogramas donde entra un drop


def _load_mono(path: str, sr: int = 22050) -> np.ndarray:
    ffmpeg = get_ffmpeg_path()
    if ffmpeg:
        try:
            raw = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                                 capture_output=True, check=True).stdout
            if raw:
                return np.frombuffer(raw, dtype=np.float32).copy()
        except Exception:
            pass
    import soundfile as sf
    y, file_sr = sf.read(path, always_2d=True, dtype="float32")
    y = y.mean(axis=1)
    if file_sr != sr:
        from scipy.signal import resample_poly
        g = math.gcd(int(file_sr), sr)
        y = resample_poly(y, sr // g, int(file_sr) // g).astype(np.float32)
    return y


def analyze_audio(path: str, fps: int = FPS, n_bars: int = 44, sr: int = 22050) -> AudioAnalysis:
    y = _load_mono(path, sr)
    dur = len(y) / sr
    n = max(1, int(math.ceil(dur * fps)))
    win = 2048
    hop = sr / fps
    pad = np.concatenate([np.zeros(win // 2, np.float32), y, np.zeros(win, np.float32)])
    starts = (np.arange(n) * hop).astype(int)
    hann = np.hanning(win).astype(np.float32)
    freqs = np.fft.rfftfreq(win, 1 / sr)

    edges = np.geomspace(45, 11000, n_bars + 1)
    band_idx = [np.where((freqs >= edges[i]) & (freqs < edges[i + 1]))[0] for i in range(n_bars)]
    low = np.where((freqs >= 40) & (freqs <= 130))[0]

    bands = np.zeros((n, n_bars), np.float32)
    low_e = np.zeros(n, np.float32)
    tot_e = np.zeros(n, np.float32)
    chunk = 256
    for a in range(0, n, chunk):
        idx = starts[a:a + chunk, None] + np.arange(win)[None, :]
        mag = np.abs(np.fft.rfft(pad[idx] * hann, axis=1)).astype(np.float32)
        for b, ix in enumerate(band_idx):
            if len(ix):
                bands[a:a + chunk, b] = mag[:, ix].mean(axis=1)
        low_e[a:a + chunk] = mag[:, low].mean(axis=1)
        tot_e[a:a + chunk] = mag.mean(axis=1)

    # barras: escala logarítmica normalizada + caída suave (ataque inmediato, caída lenta)
    lb = np.log1p(bands * 6.0)
    lb /= max(1e-6, float(np.percentile(lb, 99.5)))
    lb = np.clip(lb, 0, 1)
    bars = lb.copy()
    for i in range(1, n):
        bars[i] = np.maximum(lb[i], bars[i - 1] * 0.86)

    # kick: subida brusca de la banda grave
    flux = np.maximum(0, np.diff(low_e, prepend=low_e[0]))
    flux /= max(1e-6, float(np.percentile(flux, 97)))
    flux = np.clip(flux, 0, 1)
    kick = np.zeros(n, np.float32)
    for i in range(n):
        kick[i] = max(flux[i] if flux[i] > 0.35 else 0.0, kick[i - 1] * 0.80 if i else 0.0)

    # energía y drops
    e = np.convolve(tot_e, np.ones(9) / 9, mode="same")
    e /= max(1e-6, float(np.percentile(e, 98)))
    e = np.clip(e, 0, 1)
    long = np.convolve(e, np.ones(int(fps * 1.5)) / int(fps * 1.5), mode="same")
    drops, last = [], -10 ** 9
    lag = int(fps * 1.5)
    for i in range(lag, n):
        if long[i] > 0.45 and long[i] > 1.30 * long[i - lag] and i - last > fps * 4:
            drops.append(i)
            last = i
    return AudioAnalysis(dur, n, bars, kick, e, drops)


# ───────────────────────────── utilidades gráficas ─────────────────────────────

def _font(size: int, kind: str = "black") -> ImageFont.ImageFont:
    names = {"black": "Inter-BlackItalic.otf", "bold": "Inter-Bold.otf"}
    p = Path(get_assets_dir()) / "fonts" / names.get(kind, names["bold"])
    if p.exists():
        try:
            return ImageFont.truetype(str(p), size)
        except Exception:
            pass
    from src.engine.video import _get_font
    return _get_font(size, bold=True)


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _outro_link() -> str:
    """Enlace del cierre del vídeo: el de compra de la edición con la que se genera."""
    try:
        from src.config import get_edition
        return _links.short(_links.url_for(get_edition()))
    except Exception:
        return _links.short(_links.STORE_URL)


def _ease_out(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def _text_layer(text: str, size: int, fill, kind: str = "black", tracking: int = 0, upper: bool = True,
                max_w: Optional[int] = None, max_lines: int = 1, line_gap: float = 0.08) -> Image.Image:
    """RGBA con el texto ajustado al ancho (reduce el cuerpo o parte en líneas)."""
    text = text.upper() if upper else text
    s = size
    while True:
        f = _font(s, kind)
        words = text.split()
        lines, cur = [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if _measure(t, f, tracking) <= (max_w or 10 ** 6) or not cur:
                cur = t
            else:
                lines.append(cur); cur = w
        if cur:
            lines.append(cur)
        if (len(lines) <= max_lines and all(_measure(l, f, tracking) <= (max_w or 10 ** 6) for l in lines)) or s <= 18:
            break
        s -= 3
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * (1 + line_gap))
    W = max(_measure(l, f, tracking) for l in lines) + 8
    H = lh * len(lines) + 8
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for k, l in enumerate(lines):
        x = 4
        if tracking:
            for ch in l:
                d.text((x, 4 + k * lh), ch, font=f, fill=fill)
                x += int(f.getlength(ch)) + tracking
        else:
            d.text((x, 4 + k * lh), l, font=f, fill=fill)
    return img


def _measure(t: str, f, tracking: int) -> int:
    return int(f.getlength(t)) + tracking * max(0, len(t) - 1)


def _shear(img: Image.Image, k: float) -> Image.Image:
    """Inclina el texto (cursiva) hacia la derecha."""
    w, h = img.size
    return img.transform((w + int(k * h), h), Image.AFFINE, (1, k, -k * h, 0, 1, 0), resample=Image.BICUBIC)


def _glow_sprite(r: int, rgb) -> Image.Image:
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    a = np.clip(1 - np.sqrt(xx ** 2 + yy ** 2) / r, 0, 1) ** 2
    arr = np.zeros((2 * r + 1, 2 * r + 1, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = rgb
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def _radial(h: int, w: int, cx: float, cy: float, rad: float) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w]
    return np.clip(1 - np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / rad, 0, 1) ** 1.6


def _cover_square(path: Optional[str], size: int) -> Image.Image:
    p = Path(path) if path and Path(path).exists() else None
    if p is None:
        assets = Path(get_assets_dir())
        for n in ("logo_emblem.png", "logo.png"):
            if (assets / n).exists():
                p = assets / n
                break
    if p is None:
        return Image.new("RGBA", (size, size), (20, 20, 30, 255))
    im = Image.open(p).convert("RGBA")
    if im.getchannel("A").getextrema()[0] < 255 and p.name.startswith("logo"):   # logo con transparencia: sobre fondo oscuro
        bg = Image.new("RGBA", im.size, (14, 15, 22, 255)); bg.alpha_composite(im); im = bg
    s = min(im.size)
    l, t = (im.width - s) // 2, (im.height - s) // 2
    return im.crop((l, t, l + s, t + s)).resize((size, size), Image.LANCZOS)


# ───────────────────────────── composición ─────────────────────────────

@dataclass
class _Layout:
    W: int
    H: int
    cover: int
    cover_xy: tuple
    text_x: int           # borde izquierdo (16:9) o margen lateral
    text_w: int
    title_size: int
    stack_top: int        # y donde empieza la pila de textos (None = centrada junto a la carátula)
    bars_rect: tuple      # x0, y0, x1, y1
    banner_y: int
    center_text: bool


def _layout(aspect: str) -> _Layout:
    W, H = ASPECTS[aspect]
    if aspect == "9:16":
        c = 640
        return _Layout(W, H, c, ((W - c) // 2, 170), 70, W - 140, 100, 170 + c + 50, (70, 1385, W - 70, 1640), 1700, True)
    if aspect == "1:1":
        c = 380
        return _Layout(W, H, c, ((W - c) // 2, 40), 60, W - 120, 60, 40 + c + 28, (70, 790, W - 70, 965), 990, True)
    c = 720                                              # 16:9
    return _Layout(W, H, c, (110, (H - c) // 2), 940, 880, 92, 0, (940, 800, W - 100, 960), 988, False)


class _Renderer:
    def __init__(self, an: AudioAnalysis, cover_path, title, artist, bpm, key_str, aspect, palette_key, promo_text,
                 kicker, scale: float, watermark: bool = False, end_mode: str = "brand", custom: Optional[dict] = None):
        self.an = an
        self.watermark = bool(watermark)
        self.aspect = aspect
        # Edición Basic (marca de agua): sin ajustes propios; el final solo puede ser la firma o el fundido a negro
        self.custom = normalize_custom(None if self.watermark else custom)
        self.end_image = self.custom["end_image"] if self.custom["end_image"] and Path(self.custom["end_image"]).exists() else ""
        if end_mode not in ("brand", "fade", "none", "image"):
            end_mode = "brand"
        if self.watermark and end_mode not in ("brand", "fade"):
            end_mode = "brand"
        if end_mode == "image" and not self.end_image:
            end_mode = "brand"
        self.end_mode = end_mode
        self.bg_path = resolve_bg(self.custom, aspect) if self.custom["style"] == "image" else None
        self.img_mode = bool(self.bg_path)
        self.L = _layout(aspect)
        if self.img_mode:                       # con imagen propia los textos van centrados y a todo el ancho útil
            self.L = replace(self.L, center_text=True, text_w=self.L.W - (140 if self.L.W < self.L.H else 360),
                             title_size=self.L.title_size if self.L.W < self.L.H else 84)
        self.P, self.S, self.F = NEON_PALETTES.get(palette_key, NEON_PALETTES["crimson"])
        self.promo_text = promo_text.strip()
        L = self.L
        W, H = L.W, L.H

        if not self.img_mode:
            # fondo: carátula ampliada, desenfocada y oscura + rejilla + viñeta
            big = _cover_square(cover_path, 256).resize((max(W, H) // 2, max(W, H) // 2), Image.BICUBIC)
            big = big.filter(ImageFilter.GaussianBlur(26)).convert("RGB")
            l, t = (big.width - W // 2) // 2, (big.height - H // 2) // 2
            bgp = big.crop((l, t, l + W // 2, t + H // 2)).resize((W, H), Image.BICUBIC)
            arr = np.asarray(bgp, np.float32) * 0.28 + np.array(BG, np.float32) * 0.72
            yy, xx = np.mgrid[0:H, 0:W]
            grid = (((xx % 90) < 1) | ((yy % 90) < 1)).astype(np.float32)[..., None] * 9
            vig = np.clip(1 - 0.78 * (np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 1.4) ** 2.2, 0.15, 1)[..., None]
            self.bg = Image.fromarray(np.clip((arr + grid) * vig, 0, 255).astype(np.uint8), "RGB")
            # resplandor: se hornea en dos fondos (frío y caliente) con rayas CRT y varios granos; por fotograma solo se mezclan
            gh, gw = H // 4, W // 4
            gl = _radial(gh, gw, gw * (0.5 if L.center_text else 0.30), gh * 0.34, max(gw, gh) * 0.75)
            glow_full = np.asarray(Image.fromarray((np.clip(gl, 0, 1) * 255).astype(np.uint8), "L")
                                   .resize((W, H), Image.BILINEAR), np.float32)[..., None] / 255.0
            base_arr = np.asarray(self.bg, np.float32)
            hot_arr = base_arr + glow_full * np.array(self.P, np.float32)[None, None, :] * 1.9
            stripes = np.zeros((H, W, 1), np.float32)
            stripes[::4] = 11
            rn = np.random.default_rng(5)
            self.bg_cold, self.bg_hot = [], []
            for _ in range(3):
                n = np.asarray(Image.fromarray(rn.integers(0, 12, size=(H // 4, W // 4), dtype=np.uint8), "L")
                               .resize((W, H), Image.NEAREST), np.float32)[..., None]
                self.bg_cold.append(Image.fromarray(np.clip(base_arr - stripes + n, 0, 255).astype(np.uint8), "RGB"))
                self.bg_hot.append(Image.fromarray(np.clip(hot_arr - stripes + n, 0, 255).astype(np.uint8), "RGB"))

            # carátula
            cs = L.cover
            self.cover = _cover_square(cover_path, cs)
            mask = Image.new("L", (cs, cs), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, cs - 1, cs - 1), radius=int(cs * 0.05), fill=255)
            self.cover.putalpha(mask)
            dim, hot = self._neon_frame(cs, 0.35), self._neon_frame(cs, 1.0)
            self._frame_levels = [Image.blend(dim, hot, k / 5) for k in range(6)]

        # textos
        self.lang_en = str(kicker).upper().startswith("EXCLUSIVE")
        self.kicker = self._kicker(kicker)
        self.title = _shear(_text_layer(title or "Sin título", L.title_size, (255, 255, 255, 255), "black", tracking=-2,
                                        max_w=L.text_w, max_lines=2 if self.aspect != "1:1" else 1), 0.2)
        self.artist = _text_layer(artist or "Radical Records", int(L.title_size * 0.46), (255, 255, 255, 235), "black", tracking=2,
                                  max_w=L.text_w)
        self.chips = self._chips(bpm, key_str)
        self._stack_texts()
        self.banner = self._banner(self.promo_text) if self.promo_text else None
        self.outro = self._outro_image() if self.end_mode == "image" else self._outro()
        if self.img_mode:
            self._setup_image_mode()
        self.wm_layer = self._watermark_layer() if self.watermark else None
        self.spark = {k: _glow_sprite(r, self.F if k == "hot" else self.P) for k, r in (("sm", 7), ("md", 12), ("hot", 18))}
        rng = np.random.default_rng(11)
        self.parts = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(40, 150), rng.uniform(0.4, 1.0), rng.uniform(0, 6.28))
                      for _ in range(30)]


    def _stack_texts(self):
        """Coloca kicker, título, artista y chips uno bajo otro según su altura real."""
        L = self.L
        gaps = (14, 20, 26)
        layers = [self.kicker, self.title, self.artist, self.chips]
        total = sum(l.height for l in layers) + sum(gaps)
        y = L.stack_top if L.stack_top else max(40, L.cover_xy[1] + L.cover // 2 - total // 2)
        self.ys = []
        for k, l in enumerate(layers):
            self.ys.append(y)
            y += l.height + (gaps[k] if k < 3 else 0)

    # — piezas estáticas —
    def _neon_frame(self, cs: int, k: float) -> Image.Image:
        pad = 60
        im = Image.new("RGBA", (cs + 2 * pad, cs + 2 * pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        r = int(cs * 0.05)
        d.rounded_rectangle((pad - 3, pad - 3, pad + cs + 2, pad + cs + 2), radius=r + 3, outline=self.P + (int(255 * k),), width=7)
        glow = im.filter(ImageFilter.GaussianBlur(20))
        glow = Image.merge("RGBA", (*glow.split()[:3], glow.getchannel("A").point(lambda v: min(255, int(v * 2.2 * k)))))
        glow.alpha_composite(im)
        return glow

    def _kicker(self, text: str) -> Image.Image:
        lay = _text_layer(text, 32, (255, 255, 255, 255), "bold", tracking=8, max_w=self.L.text_w - 60)
        w, h = lay.width + 56, lay.height + 18
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=self.P + (255,))
        im.alpha_composite(lay, (28, 9))
        return im

    def _chips(self, bpm, key_str) -> Image.Image:
        items = [f"{bpm:.0f} BPM", str(key_str)]
        f = _font(34, "bold")
        pad, gap = 24, 16
        widths = [int(f.getlength(t)) + 2 * pad for t in items]
        W = sum(widths) + gap * (len(items) - 1) + 8
        im = Image.new("RGBA", (W, 76), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        x = 4
        for t, w in zip(items, widths):
            d.rounded_rectangle((x, 6, x + w, 66), radius=30, fill=(255, 255, 255, 22), outline=self.P + (230,), width=3)
            d.text((x + pad, 17), t, font=f, fill=(255, 255, 255, 255))
            x += w + gap
        return im

    def _banner(self, text: str) -> Image.Image:
        L = self.L
        w = L.text_w if L.center_text else L.W - L.text_x - 100
        lay = _text_layer(text, 40, (255, 255, 255, 255), "black", tracking=2, max_w=w - 60)
        h = lay.height + 30
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), radius=16, fill=self.P + (255,))
        im.alpha_composite(_shear(lay, 0.18), ((w - lay.width) // 2, 15))
        return im

    def _outro(self) -> Image.Image:
        L = self.L
        im = Image.new("RGB", (L.W, L.H), BG)
        glow = _radial(L.H // 4, L.W // 4, L.W // 8, L.H // 8, L.H // 3) [..., None] * np.array(self.P, np.float32) * 0.9
        im.paste(Image.fromarray(np.clip(glow, 0, 255).astype(np.uint8), "RGB").resize((L.W, L.H), Image.BICUBIC))
        assets = Path(get_assets_dir())
        emb, ban = assets / "logo_emblem.png", assets / "logo_banner.png"
        cy = L.H // 2 - 70
        if emb.exists():
            e = Image.open(emb).convert("RGBA"); e.thumbnail((int(min(L.W, L.H) * 0.34),) * 2, Image.LANCZOS)
            im.paste(e, ((L.W - e.width) // 2, cy - e.height // 2), e)
        if ban.exists():
            b = Image.open(ban).convert("RGBA"); b.thumbnail((int(L.W * (0.5 if L.W < L.H else 0.32)), 140), Image.LANCZOS)
            by = cy + int(min(L.W, L.H) * 0.20)
            im.paste(b, ((L.W - b.width) // 2, by), b)
            y = by + b.height + int(L.H * 0.035)
        else:
            y = cy + int(min(L.W, L.H) * 0.30)
        # firma de la herramienta + enlace de compra (Payhip)
        en = self.lang_en
        credit = "GENERATED BY AUTOPREVIAS · RADICAL RECORDS" if en else "GENERADO POR AUTOPREVIAS · RADICAL RECORDS"
        t1 = _text_layer(credit, int(L.W * 0.036) if L.W < L.H else 30, (235, 236, 242), "bold", tracking=3, max_w=int(L.W * 0.88))
        im.paste(t1, ((L.W - t1.width) // 2, y), t1)
        t2 = _text_layer(_outro_link(), int(L.W * 0.052) if L.W < L.H else 40, (10, 11, 16), "black",
                         upper=False, max_w=int(L.W * 0.80))
        pw, ph = t2.width + 70, t2.height + 36
        px, py = (L.W - pw) // 2, y + t1.height + int(L.H * 0.022)
        ImageDraw.Draw(im).rounded_rectangle((px, py, px + pw, py + ph), radius=ph // 2, fill=(255, 255, 255))
        im.paste(t2, (px + 35, py + 18), t2)
        return im

    def _watermark_layer(self) -> Image.Image:
        """Marca de agua pequeña y translúcida (esquina inferior derecha) de la edición Basic."""
        L = self.L
        txt = ("Made with AutoPrevias Basic · Radical Records" if self.lang_en
               else "Generado por Radical Records · AutoPrevias Basic")
        size = max(22, int(min(L.W, L.H) * 0.026))
        lay = _text_layer(txt, size, (255, 255, 255, 255), "bold", tracking=1, upper=False, max_w=int(L.W * 0.5))
        lay = lay.copy()
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * 0.42)))
        return lay

    # — fotograma —
    def frame(self, i: int, t: float) -> Image.Image:
        if self.img_mode:
            return self._frame_image(i, t)
        L, an, P = self.L, self.an, self.P
        W, H = L.W, L.H
        kick = float(an.kick[min(i, an.n_frames - 1)])
        en = float(an.energy[min(i, an.n_frames - 1)])
        rng = np.random.default_rng(1000 + i)

        # tiempo desde el último drop (flash y glitch)
        since = min([(i - d) / FPS for d in an.drops if d <= i] or [99.0])
        flash = max(0.0, 1 - since / 0.45) ** 2 if since < 0.45 else 0.0
        glitch = since < 0.30

        # fondo + resplandor que late con el bombo
        k_glow = min(1.0, (0.30 + 0.55 * kick + 0.35 * en + 1.1 * flash) / 1.9)
        j = (i // 2) % 3
        base = Image.blend(self.bg_cold[j], self.bg_hot[j], k_glow)

        # partículas ascendentes
        for (px, py, sp, br, ph) in self.parts:
            y = (py - sp * t) % (H + 60) - 30
            x = px + 14 * math.sin(t * 0.9 + ph)
            kind = "hot" if (br > 0.9 and kick > 0.3) else ("md" if br > 0.6 else "sm")
            if 0 <= y < H:
                s = self.spark[kind]
                base.paste(s, (int(x) - s.width // 2, int(y) - s.height // 2), s)

        # carátula: late con el bombo, tiembla en los golpes fuertes
        sc = 1 + 0.050 * kick + 0.012 * en + 0.035 * flash
        cs = int(L.cover * sc)
        cov = self.cover.resize((cs, cs), Image.BILINEAR)
        lvl = int(round(min(1.0, kick + flash) * 5))
        frm = self._frame_levels[lvl]
        fs = frm.width
        cx, cy = L.cover_xy[0] + L.cover // 2, L.cover_xy[1] + L.cover // 2
        sh = 9 * kick
        ox, oy = int(rng.uniform(-sh, sh)), int(rng.uniform(-sh, sh))
        base.paste(frm, (cx - fs // 2 + ox, cy - fs // 2 + oy), frm)
        if glitch:                                        # separación RGB de la carátula en el drop
            r, g, b = cov.convert("RGB").split()
            off = int(14 * (1 - since / 0.30)) + 2
            cov_rgb = Image.merge("RGB", (ImageChops.offset(r, off, 0), g, ImageChops.offset(b, -off, 0)))
            cov = Image.merge("RGBA", (*cov_rgb.split(), cov.getchannel("A")))
        base.paste(cov, (cx - cs // 2 + ox, cy - cs // 2 + oy), cov)

        # textos: entrada con golpe
        self._draw_texts(base, t, kick, flash, glitch, since)

        # barras de espectro con resplandor
        self._draw_bars(base, i, kick)

        # banner promo
        if self.banner is not None:
            a = _ease_out((t - 0.9) / 0.35)
            if a > 0:
                bx = (W - self.banner.width) // 2 if L.center_text else L.text_x
                y = L.banner_y + int((1 - a) * 60)
                base.paste(self.banner, (bx, y), self.banner)

        # destello, rayas, grano, glitch de bandas
        if flash > 0.02:
            base = Image.blend(base, Image.new("RGB", (W, H), self.F), min(0.55, flash * 0.6))
        if glitch:
            for _ in range(5):
                y0 = int(rng.uniform(0, H - 60)); h = int(rng.uniform(10, 50)); dx = int(rng.uniform(-70, 70))
                strip = base.crop((0, y0, W, y0 + h))
                base.paste(ImageChops.offset(strip, dx, 0), (0, y0))

        # barra de progreso
        d = ImageDraw.Draw(base)
        d.rectangle((0, H - 12, W, H), fill=(10, 11, 16))
        d.rectangle((0, H - 12, int(W * min(1.0, t / max(0.1, an.duration))), H), fill=self.P)

        return self._finish(base, t)

    def _finish(self, base: Image.Image, t: float) -> Image.Image:
        """Entrada desde negro, marca de agua (Basic) y final elegido (firma / imagen propia / fundido a negro / corte)."""
        L, an = self.L, self.an
        W, H = L.W, L.H
        if t < 0.35:
            base = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), base, t / 0.35)
        if self.wm_layer is not None:
            wl = self.wm_layer
            base.paste(wl, (W - wl.width - int(W * 0.025), H - 12 - wl.height - int(min(W, H) * 0.02)), wl)
        if an.duration > 8:
            if self.end_mode in ("brand", "image"):
                out_len = 3.2
                if t > an.duration - out_len:
                    a = _ease_out((t - (an.duration - out_len)) / 0.7)
                    base = Image.blend(base, self.outro, min(1.0, a))
            elif self.end_mode == "fade":
                out_len = 1.6
                if t > an.duration - out_len:
                    base = Image.blend(base, Image.new("RGB", (W, H), (0, 0, 0)), min(1.0, (t - (an.duration - out_len)) / out_len))
        return base

    # — modo «imagen propia» (Plus) —
    def _outro_image(self) -> Image.Image:
        """Final con la imagen elegida por el autor (+ texto opcional)."""
        L = self.L
        im = _fit_image(self.end_image, L.W, L.H, self.custom["fit"])
        txt = self.custom["end_text"]
        if txt:
            shade = Image.new("RGBA", (L.W, L.H), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shade)
            for k in range(int(L.H * 0.30)):
                sd.line((0, L.H - 1 - k, L.W, L.H - 1 - k), fill=(0, 0, 0, int(190 * (1 - k / (L.H * 0.30)) ** 1.6)))
            im = im.convert("RGBA"); im.alpha_composite(shade); im = im.convert("RGB")
            lay = _text_layer(txt, int(L.W * 0.05) if L.W < L.H else 52, (255, 255, 255, 255), "black", tracking=2,
                              upper=False, max_w=int(L.W * 0.86))
            im.paste(lay, ((L.W - lay.width) // 2, int(L.H * 0.86) - lay.height // 2), lay)
        return im

    def _setup_image_mode(self):
        """Prepara la imagen de fondo (con margen para el zoom lento), el velo de legibilidad y la disposición."""
        L = self.L
        W, H = L.W, L.H
        self.kb_w, self.kb_h = int(W * 1.12), int(H * 1.12)
        self.kb = _fit_image(self.bg_path, self.kb_w, self.kb_h, self.custom["fit"])
        c = self.custom
        if c["only_photo"]:
            self.banner = None
        tx_items = [(self.kicker, 0.10, c["kicker"]), (self.title, 0.22, c["title"]),
                    (self.artist, 0.40, c["artist"]), (self.chips, 0.55, c["chips"])]
        tx_items = [(l, t0) for l, t0, on in tx_items if on]
        lay = [l for l, _ in tx_items]
        gaps_all = 20
        text_h = (sum(l.height for l in lay) + gaps_all * (len(lay) - 1)) if lay else 0
        ban_h = (self.banner.height + 30) if (self.banner is not None) else 0
        if c["wave"]:
            if c["wave_style"] == "circle":
                self.wave_h = int(min(W, H) * (0.46 if W < H else 0.62))
                self.wave_w = self.wave_h
            else:
                self.wave_h = int(H * (0.12 if W < H else 0.20))
                self.wave_w = W - (140 if W < H else 360)
        else:
            self.wave_h = self.wave_w = 0
        margin_t, margin_b, gap = int(H * 0.06), int(H * 0.075), 34
        slots = {"top": [], "center": [], "bottom": []}
        if lay or ban_h:
            slots[c["texts_pos"]].append(("texts", text_h + ban_h))
        if c["wave"]:
            slots[c["wave_pos"]].append(("wave", self.wave_h))
        y_of = {}
        for slot, items in slots.items():
            if not items:
                continue
            total = sum(h for _, h in items) + gap * (len(items) - 1)
            y = margin_t if slot == "top" else (H - margin_b - total if slot == "bottom" else (H - total) // 2)
            for name, h in items:
                y_of[name] = y
                y += h + gap
        # textos (prioridad): dentro del encuadre aunque la pila sea muy alta
        tb = text_h + ban_h
        ty = y_of.get("texts", margin_t)
        if tb:
            ty = min(max(ty, margin_t), max(margin_t, H - margin_b - tb))
        self.text_items = []
        y = ty
        for k, (l, t0) in enumerate(tx_items):
            self.text_items.append((l, y, t0))
            y += l.height + gaps_all
        self.banner_y_img = (ty + text_h + 26) if lay else ty
        self.text_block = (ty, ty + tb) if tb else None
        # onda: en su sitio si cabe; si pisa los textos o se sale del encuadre, se reduce y se recoloca en el hueco libre
        wy = y_of.get("wave", H - margin_b - self.wave_h)
        if c["wave"]:
            out_of_frame = wy < 0 or wy + self.wave_h > H - 12
            overlap = bool(self.text_block) and wy < self.text_block[1] + gap and wy + self.wave_h > self.text_block[0] - gap
            if out_of_frame or overlap:
                if self.text_block:
                    above, below = self.text_block[0] - gap - margin_t, H - margin_b - (self.text_block[1] + gap)
                    r0, r1 = (self.text_block[1] + gap, H - margin_b) if below >= above else (margin_t, self.text_block[0] - gap)
                else:
                    r0, r1 = margin_t, H - margin_b
                rh = max(1, r1 - r0)
                self.wave_h = min(self.wave_h, rh)
                if c["wave_style"] == "circle":
                    self.wave_w = self.wave_h
                wy = r0 + (rh - self.wave_h) // 2
        # onda
        self.wave_rect = ((W - self.wave_w) // 2, wy, (W + self.wave_w) // 2, wy + self.wave_h)
        # velo oscuro suave detrás de textos y onda (legibilidad sobre cualquier foto); se combina con el máximo de cada zona
        zones = []
        if lay or ban_h:
            zones.append((ty - 40, ty + text_h + ban_h + 40))
        if c["wave"]:
            zones.append((wy - 40, wy + self.wave_h + 40))
        yy = np.arange(H, dtype=np.float32)
        alpha = np.zeros(H, np.float32)
        for (z0, z1) in zones:
            fade = max(30, (z1 - z0) // 3)
            up = np.clip((yy - (z0 - fade)) / fade, 0, 1)
            down = np.clip(1 - (yy - z1) / fade, 0, 1)
            alpha = np.maximum(alpha, np.minimum(up, down))
        col = np.repeat((alpha * 150).astype(np.uint8)[:, None], W, axis=1)
        veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        veil.putalpha(Image.fromarray(col, "L"))
        self.veil = veil

    def _wave_color(self, v: float):
        if self.custom["wave_color"] == "white":
            return (255, 255, 255)
        return _lerp(self.P, self.S, v * 2) if v < 0.5 else _lerp(self.S, self.F, (v - 0.5) * 2)

    def _draw_wave(self, base, i, kick):
        an = self.an
        x0, y0, x1, y1 = self.wave_rect
        w, h = x1 - x0, y1 - y0
        pad = 40
        layer = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        vals = an.bars[min(i, an.n_frames - 1)].astype(np.float32)
        n = len(vals)
        style = self.custom["wave_style"]
        if style == "bars":
            slot = w / n
            bw = max(4, int(slot * 0.62))
            for k in range(n):
                v = float(vals[k]) ** 0.9
                bh = max(6, int(v * h))
                x = pad + int(k * slot + (slot - bw) / 2)
                d.rounded_rectangle((x, pad + h - bh, x + bw, pad + h), radius=bw // 2, fill=self._wave_color(v) + (255,))
        elif style == "line":
            xs = np.linspace(0, w, 120)
            vv = np.interp(xs, np.linspace(0, w, n), vals)
            vv = np.convolve(np.pad(vv, 2, mode="edge"), np.ones(5) / 5, mode="valid")[:len(xs)]
            cy = pad + h / 2
            up = [(pad + float(x), cy - float(v) ** 0.9 * h / 2) for x, v in zip(xs, vv)]
            dn = [(px, 2 * cy - py) for px, py in up]
            col = self._wave_color(0.55) + (255,)
            d.line(up, fill=col, width=7, joint="curve")
            d.line(dn, fill=col, width=7, joint="curve")
            mid = [(pad + float(x), cy) for x in xs]
            d.line(mid, fill=self._wave_color(0.2) + (140,), width=3)
        else:   # circle
            cx, cy = pad + w / 2, pad + h / 2
            r0 = h * 0.30 * (1 + 0.05 * kick)
            rmax = h / 2 - r0
            m = n * 2
            for k in range(m):
                v = float(vals[k % n if k < n else (m - 1 - k) % n]) ** 0.9
                ang = 2 * math.pi * k / m - math.pi / 2
                r1 = r0 + max(5.0, v * rmax)
                d.line((cx + r0 * math.cos(ang), cy + r0 * math.sin(ang), cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)),
                       fill=self._wave_color(v) + (255,), width=max(4, int(2 * math.pi * r0 / m * 0.62)))
        glow = layer.filter(ImageFilter.GaussianBlur(11))
        base.paste(glow, (x0 - pad, y0 - pad), glow)
        base.paste(layer, (x0 - pad, y0 - pad), layer)

    def _frame_image(self, i: int, t: float) -> Image.Image:
        L, an = self.L, self.an
        W, H = L.W, L.H
        kick = float(an.kick[min(i, an.n_frames - 1)])
        en = float(an.energy[min(i, an.n_frames - 1)])
        since = min([(i - d) / FPS for d in an.drops if d <= i] or [99.0])
        flash = max(0.0, 1 - since / 0.45) ** 2 if since < 0.45 else 0.0
        # zoom lento (efecto cámara) + pequeño latido con el bombo
        prog = min(1.0, t / max(1.0, an.duration))
        z = 1.0 + 0.07 * prog + 0.012 * kick + 0.012 * flash
        # el zoom 1.0 enseña el lienzo entero menos el margen (1/1.12 del tamaño ampliado)
        cw, ch = (self.kb_w / 1.12) / z, (self.kb_h / 1.12) / z
        cx = self.kb_w / 2 + 0.018 * self.kb_w * math.sin(t * 0.35)
        cy = self.kb_h / 2 + 0.012 * self.kb_h * math.cos(t * 0.27)
        box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
        base = self.kb.resize((W, H), Image.BILINEAR, box=box)
        only = self.custom["only_photo"]
        if flash > 0.02 and not only:
            base = Image.blend(base, Image.new("RGB", (W, H), self.F), min(0.30, flash * 0.35))
        if not only:
            base.paste(self.veil, (0, 0), self.veil)
        if self.text_items:
            self._draw_texts(base, t, kick, flash, False, 99.0)
        if self.banner is not None:
            a = _ease_out((t - 0.9) / 0.35)
            if a > 0:
                base.paste(self.banner, ((W - self.banner.width) // 2, self.banner_y_img + int((1 - a) * 60)), self.banner)
        if self.custom["wave"]:
            self._draw_wave(base, i, kick)
        if not only:
            d = ImageDraw.Draw(base)
            d.rectangle((0, H - 12, W, H), fill=(10, 11, 16))
            d.rectangle((0, H - 12, int(W * min(1.0, t / max(0.1, an.duration))), H), fill=self.P)
        return self._finish(base, t)

    def _paste_layer(self, base, layer, x, y, scale=1.0, alpha=1.0):
        if alpha <= 0:
            return
        if abs(scale - 1) > 0.004:
            layer = layer.resize((max(1, int(layer.width * scale)), max(1, int(layer.height * scale))), Image.BILINEAR)
        if alpha < 0.999:
            layer = layer.copy(); layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
        base.paste(layer, (int(x - layer.width / 2), int(y - layer.height / 2)), layer)

    def _draw_texts(self, base, t, kick, flash, glitch, since):
        L = self.L
        cx = L.W // 2
        seq = self.text_items if self.img_mode else ((self.kicker, self.ys[0], 0.10), (self.title, self.ys[1], 0.22),
                                                      (self.artist, self.ys[2], 0.40), (self.chips, self.ys[3], 0.55))
        for layer, y, t0 in seq:
            a = _ease_out((t - t0) / 0.30)
            if a <= 0:
                continue
            slam = 1 + (1 - a) * 0.9                       # golpe: empieza grande y encaja
            pulse = 1 + 0.025 * kick if layer is self.title else 1.0
            px = cx if L.center_text else L.text_x + layer.width / 2
            if a < 1:                                      # estela de movimiento al entrar
                for k in (3, 2, 1):
                    ak = max(0.0, a - 0.12 * k)
                    self._paste_layer(base, layer, px, y + layer.height / 2 + 40 * k * (1 - a), slam * (1 + 0.08 * k * (1 - a)), ak * 0.22)
            self._paste_layer(base, layer, px, y + layer.height / 2, slam * pulse, a)
            if glitch and layer is self.title:             # separación RGB del título en el drop
                off = int(10 * (1 - since / 0.30)) + 2
                for sgn, col in ((-1, (255, 0, 51)), (1, (0, 229, 255))):
                    g = Image.new("RGBA", layer.size, col + (0,))
                    g.putalpha(layer.getchannel("A").point(lambda v: int(v * 0.55)))
                    base.paste(g, (int(px - layer.width / 2 + sgn * off), int(y)), g)

    def _draw_bars(self, base, i, kick):
        L, an = self.L, self.an
        x0, y0, x1, y1 = L.bars_rect
        n = an.bars.shape[1]
        w, h = x1 - x0, y1 - y0
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        slot = w / n
        bw = max(4, int(slot * 0.62))
        vals = an.bars[min(i, an.n_frames - 1)]
        for k in range(n):
            v = float(vals[k]) ** 0.9
            bh = max(6, int(v * h))
            x = int(k * slot + (slot - bw) / 2)
            col = _lerp(self.P, self.S, v * 2) if v < 0.5 else _lerp(self.S, self.F, (v - 0.5) * 2)
            d.rounded_rectangle((x, h - bh, x + bw, h), radius=bw // 2, fill=col + (255,))
        glow = layer.filter(ImageFilter.GaussianBlur(11))
        base.paste(glow, (x0, y0), glow)
        base.paste(layer, (x0, y0), layer)


def _iter_frames(r, n_frames: int, step: int = 1, workers: Optional[int] = None):
    """Rinde los fotogramas 0, step, 2·step… en orden. Se dibujan varios a la vez (hilos: Pillow/NumPy sueltan el GIL),
    con un margen acotado para no gastar memoria; el resultado es idéntico al dibujado secuencial."""
    idx = list(range(0, n_frames, step))
    n = _perf.threads("render") if workers is None else int(workers)
    if n <= 1 or len(idx) < 4:
        for i in idx:
            yield i, r.frame(i, i / FPS)
        return
    from collections import deque
    from concurrent.futures import ThreadPoolExecutor
    window = n * 3
    with ThreadPoolExecutor(max_workers=n) as ex:
        pending, nxt = deque(), 0
        try:
            for k, i in enumerate(idx):
                while nxt < len(idx) and len(pending) < window:
                    j = idx[nxt]
                    pending.append((j, ex.submit(r.frame, j, j / FPS)))
                    nxt += 1
                j, fut = pending.popleft()
                yield j, fut.result()
        finally:
            for _, f in pending:
                f.cancel()


# ───────────────────────────── API pública ─────────────────────────────

def render_neon_video(
    audio_path: str,
    cover_image_path: Optional[str],
    output_video_path: str,
    title: str = "Pista sin título",
    artist: str = "Radical Records",
    bpm: float = 128.0,
    key_str: str = "8A · Am",
    aspect_ratio: str = "9:16",
    palette_key: str = "crimson",
    promo_text: str = "",
    kicker: str = "PREVIA EXCLUSIVA",
    scale: float = 1.0,
    progress_cb: Optional[Callable[[int, str], None]] = None,
    watermark: bool = False,
    end_mode: str = "brand",
    custom: Optional[dict] = None,
) -> str:
    """Renderiza el vídeo animado Radical Neón. scale<1 = borrador rápido (menos resolución)."""
    def _prog(p, m):
        if progress_cb:
            progress_cb(int(p), m)

    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError("FFmpeg no encontrado. No es posible generar el vídeo social.")
    if aspect_ratio not in ASPECTS:
        aspect_ratio = "9:16"

    _prog(3, "Analizando el ritmo de la previa (bombo, drops, espectro)…")
    an = analyze_audio(audio_path)
    _prog(12, "Preparando el diseño Radical Neón…")
    r = _Renderer(an, cover_image_path, title, artist, bpm, key_str, aspect_ratio, palette_key, promo_text, kicker, scale,
                  watermark=watermark, end_mode=end_mode, custom=custom)
    W, H = r.L.W, r.L.H
    ow, oh = (int(W * scale) // 2 * 2, int(H * scale) // 2 * 2)

    out = Path(output_video_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(audio_path)]
    if (ow, oh) != (W, H):
        cmd += ["-vf", f"scale={ow}:{oh}:flags=lanczos"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k"]
    if _perf.ffmpeg_threads() > 0:                 # solo en modo ahorro (o forzado): limita los hilos del codificador
        cmd += ["-threads", str(_perf.ffmpeg_threads())]
    cmd += ["-movflags", "+faststart", "-shortest", str(out)]
    err_file = tempfile.TemporaryFile()
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=err_file)
    try:
        for i, fr in _iter_frames(r, an.n_frames):
            proc.stdin.write(fr.tobytes())
            if i % 15 == 0:
                _prog(15 + 83 * i / an.n_frames, f"Dibujando fotogramas ({i}/{an.n_frames})…")
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            err_file.seek(0)
            raise RuntimeError("FFmpeg falló al codificar el vídeo: " + err_file.read().decode("utf-8", "ignore")[-400:])
    except BrokenPipeError:
        err_file.seek(0)
        raise RuntimeError("FFmpeg se cerró de forma inesperada: " + err_file.read().decode("utf-8", "ignore")[-400:])
    finally:
        try:
            if proc.poll() is None:
                proc.kill()
            err_file.close()
        except Exception:
            pass
    _prog(100, "¡Vídeo Radical Neón exportado!")
    return str(out)


def render_preview(
    audio_path: str,
    cover_image_path: Optional[str],
    title: str = "Pista sin título",
    artist: str = "Radical Records",
    bpm: float = 128.0,
    key_str: str = "8A · Am",
    aspect_ratio: str = "9:16",
    palette_key: str = "crimson",
    promo_text: str = "",
    kicker: str = "PREVIA EXCLUSIVA",
    start_sec: float = -1.0,
    seconds: float = 6.0,
    out_height: int = 540,
    fps: int = 15,
    progress_cb: Optional[Callable[[int, str], None]] = None,
    watermark: bool = False,
    end_mode: str = "brand",
    custom: Optional[dict] = None,
) -> dict:
    """Vista previa rápida del vídeo: unos segundos de la pista (desde `start_sec`, o desde el 30 % si es <0)
    a baja resolución, seguidos del cierre con firma. Devuelve {"frames": [PIL.Image RGB], "fps": fps, "audio": wav|None}."""
    def _prog(p, m):
        if progress_cb:
            progress_cb(int(p), m)

    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError("FFmpeg no encontrado.")
    if aspect_ratio not in ASPECTS:
        aspect_ratio = "9:16"
    _prog(5, "Preparando la muestra de audio…")
    total = len(_load_mono(audio_path, 8000)) / 8000.0
    seconds = max(2.0, min(float(seconds), max(2.0, total)))
    if start_sec is None or start_sec < 0:
        start_sec = total * 0.30
    start_sec = max(0.0, min(float(start_sec), max(0.0, total - seconds)))
    import uuid
    clip = Path(tempfile.gettempdir()) / f"autoprevias_vprev_{os.getpid()}_{uuid.uuid4().hex[:8]}.wav"
    subprocess.run([ffmpeg, "-y", "-v", "error", "-ss", f"{start_sec:.3f}", "-t", f"{seconds:.3f}", "-i", str(audio_path),
                    "-ac", "2", "-ar", "44100", str(clip)], check=True, capture_output=True)
    _prog(20, "Analizando el ritmo…")
    an = analyze_audio(str(clip))
    r = _Renderer(an, cover_image_path, title, artist, bpm, key_str, aspect_ratio, palette_key, promo_text, kicker, 1.0,
                  watermark=watermark, end_mode=end_mode, custom=custom)
    W, H = r.L.W, r.L.H
    k = out_height / float(H)
    size = (max(2, int(W * k)) // 2 * 2, out_height)
    step = max(1, round(FPS / fps))
    n = max(1, int(an.duration * fps))
    frames = []
    for j, (i, im) in enumerate(_iter_frames(r, n * step, step)):
        frames.append(im.convert("RGB").resize(size, Image.BILINEAR))
        if j % 6 == 0:
            _prog(25 + 70 * j / n, "Dibujando la vista previa…")
    last = frames[-1]
    if r.end_mode in ("brand", "image"):
        out_img = r.outro.convert("RGB").resize(size, Image.BILINEAR)
        for j in range(int(1.8 * fps)):          # cierre con firma y enlace
            frames.append(Image.blend(last, out_img, min(1.0, _ease_out(j / (0.6 * fps)))))
    elif r.end_mode == "fade":
        black = Image.new("RGB", size, (0, 0, 0))
        for j in range(int(1.0 * fps)):          # fundido a negro
            frames.append(Image.blend(last, black, min(1.0, (j + 1) / (1.0 * fps))))
    _prog(100, "Lista")
    return {"frames": frames, "fps": fps, "audio": str(clip)}
