"""
AutoPrevias — video.py
Generador de vídeos de alta fidelidad para redes sociales (Reels, TikTok, Shorts).
Crea vídeos MP4 con carátula en alta resolución, fondo desenfocado atmosférico,
visualizador de onda interactivo sincronizado y cartelería con BPM y Clave Camelot.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageFont

from src.config import get_assets_dir, get_cache_dir, get_ffmpeg_path


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Carga fuente tipográfica del sistema con fallback a default de PIL."""
    candidates = []
    if bold:
        candidates.extend([
            "/System/Library/Fonts/SFPro-Bold.ttf",
            "/System/Library/Fonts/SFNSText-Bold.otf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "C:\\Windows\\Fonts\\segoeuib.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ])
    else:
        candidates.extend([
            "/System/Library/Fonts/SFPro.ttf",
            "/System/Library/Fonts/SFNSText.otf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\segoeui.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ])

    for font_path in candidates:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def create_social_overlay_image(
    width: int,
    height: int,
    title: str,
    artist: str,
    bpm: float,
    key_str: str,
    output_path: Path,
) -> Path:
    """
    Genera una imagen PNG semitransparente con los textos, badges estilizados y degradados.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Gradiente superior e inferior para legibilidad cinematográfica
    for y in range(250):
        alpha = int(180 * (1.0 - y / 250.0))
        draw.line([(0, y), (width, y)], fill=(10, 10, 15, alpha))

    for y in range(height - 400, height):
        progress = (y - (height - 400)) / 400.0
        alpha = int(220 * progress)
        draw.line([(0, y), (width, y)], fill=(10, 10, 15, alpha))

    # 2. Tipografías
    font_brand = _get_font(22, bold=True)
    font_title = _get_font(46, bold=True)
    font_artist = _get_font(30, bold=False)
    font_badge = _get_font(24, bold=True)

    # 3. Header de marca superior
    brand_text = "RADICAL RECORDS · STUDIO PREVIEW"
    draw.text((width // 2, 80), brand_text, font=font_brand, fill=(244, 63, 94, 255), anchor="mm")

    # 4. Posición de textos bajo el cuadro de carátula
    # En 9:16 (1080x1920), la carátula está en Y: 280 a 1000 (720x720)
    # El visualizador de onda va de Y: 1040 a 1180
    text_start_y = 1260 if height >= 1600 else (height - 240)

    # Truncar título si es muy extenso
    display_title = title if len(title) <= 32 else title[:29] + "…"
    display_artist = artist if len(artist) <= 38 else artist[:35] + "…"

    draw.text((width // 2, text_start_y), display_title, font=font_title, fill=(255, 255, 255, 255), anchor="mm")
    draw.text((width // 2, text_start_y + 55), display_artist, font=font_artist, fill=(161, 161, 170, 255), anchor="mm")

    # 5. Badges de metadatos (BPM + Camelot / Clave)
    bpm_txt = f"{int(round(bpm))} BPM" if bpm > 0 else "128 BPM"
    key_txt = key_str if key_str else "8A · Am"

    badges = [
        ("⚡", bpm_txt, (34, 197, 94)),      # Emerald green
        ("🎵", key_txt, (59, 130, 246)),      # Blue
        ("🔥", "EXCLUSIVE", (239, 68, 68)),   # Red
    ]

    badge_y = text_start_y + 140
    total_w = sum(150 for _ in badges) + (len(badges) - 1) * 20
    cur_x = (width - total_w) // 2

    for icon, txt, color in badges:
        bw, bh = 150, 48
        # Fondo redondeado semitransparente con borde
        draw.rounded_rectangle(
            [(cur_x, badge_y), (cur_x + bw, badge_y + bh)],
            radius=24,
            fill=(24, 24, 27, 230),
            outline=color,
            width=2,
        )
        full_txt = f"{icon} {txt}"
        draw.text((cur_x + bw // 2, badge_y + bh // 2), full_txt, font=font_badge, fill=(255, 255, 255, 255), anchor="mm")
        cur_x += bw + 20

    img.save(str(output_path), "PNG")
    return output_path


def render_social_video(
    audio_path: str,
    cover_image_path: Optional[str],
    output_video_path: str,
    title: str = "Pista Sin Título",
    artist: str = "Radical Records",
    bpm: float = 128.0,
    key_str: str = "8A · Am",
    aspect_ratio: str = "9:16",
    progress_cb: Optional[Callable[[int, str], None]] = None,
) -> str:
    """
    Renderiza un vídeo MP4 optimizado para TikTok, Instagram Reels y YouTube Shorts.
    Retorna la ruta absoluta del archivo generado.
    """
    def _prog(pct: int, msg: str):
        if progress_cb:
            progress_cb(pct, msg)

    ffmpeg_bin = get_ffmpeg_path()
    if not ffmpeg_bin:
        raise RuntimeError("FFmpeg no encontrado. No es posible generar el vídeo social.")

    _prog(5, "Configurando dimensiones de vídeo…")
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    if aspect_ratio == "1:1":
        vw, vh = 1080, 1080
        cover_size = 560
        cover_y = 120
        wave_y = 720
        wave_w, wave_h = 720, 120
    else:  # "9:16" Vertical Reels/TikTok
        vw, vh = 1080, 1920
        cover_size = 720
        cover_y = 280
        wave_y = 1060
        wave_w, wave_h = 720, 140

    cover_x = (vw - cover_size) // 2
    wave_x = (vw - wave_w) // 2

    # Resolver carátula
    cover_resolved: Optional[Path] = None
    if cover_image_path and Path(cover_image_path).exists():
        cover_resolved = Path(cover_image_path)
    else:
        assets = get_assets_dir()
        for name in ["logo_emblem.png", "logo_banner.png", "logo_emblem_red.png"]:
            cand = assets / name
            if cand.exists():
                cover_resolved = cand
                break

    if not cover_resolved:
        raise RuntimeError("No se encontró imagen de carátula para el vídeo.")

    # Generar overlay gráfico con PIL
    _prog(15, "Diseñando gráfica y badges de metadatos…")
    overlay_png = cache_dir / f"overlay_{os.getpid()}.png"
    create_social_overlay_image(
        width=vw,
        height=vh,
        title=title,
        artist=artist,
        bpm=bpm,
        key_str=key_str,
        output_path=overlay_png,
    )

    _prog(35, "Renderizando vídeo con visualizador de ondas y desenfoque de fondo…")

    # Filtro complejo FFmpeg:
    # 0: audio
    # 1: carátula
    # 2: overlay PNG
    filter_complex = (
        f"[1:v]scale={vw}:{vh}:force_original_aspect_ratio=increase,crop={vw}:{vh},boxblur=30:5[bg];"
        f"[1:v]scale={cover_size}:{cover_size}:force_original_aspect_ratio=decrease[fg];"
        f"[0:a]showwaves=s={wave_w}x{wave_h}:mode=p2p:rate=30:colors=0x22c55e|0x10b981[waves];"
        f"[bg][fg]overlay={cover_x}:{cover_y}[v1];"
        f"[v1][waves]overlay={wave_x}:{wave_y}[v2];"
        f"[v2][2:v]overlay=0:0:shortest=1[vfinal]"
    )

    out_p = Path(output_video_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(audio_path),
        "-loop", "1", "-i", str(cover_resolved),
        "-loop", "1", "-i", str(overlay_png),
        "-filter_complex", filter_complex,
        "-map", "[vfinal]",
        "-map", "0:a",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "320k",
        "-shortest",
        str(out_p),
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        _, err = proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg falló al codificar vídeo: {err[-400:] if err else 'desconocido'}")
    finally:
        if overlay_png.exists():
            try:
                overlay_png.unlink()
            except Exception:
                pass

    _prog(100, "¡Vídeo social exportado con éxito!")
    return str(out_p)
