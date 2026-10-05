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
    Genera una imagen PNG semitransparente con marco de carátula iluminado,
    tarjeta de analizador de espectro de estudio, tipografía premium y badges con glow.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    is_vertical = height >= 1600

    # 1. Gradiente superior e inferior para máxima legibilidad cinematográfica
    for y in range(260):
        alpha = int(190 * (1.0 - y / 260.0))
        draw.line([(0, y), (width, y)], fill=(8, 10, 16, alpha))

    for y in range(height - 450, height):
        progress = (y - (height - 450)) / 450.0
        alpha = int(230 * progress)
        draw.line([(0, y), (width, y)], fill=(8, 10, 16, alpha))

    # 2. Tipografías
    font_brand = _get_font(20, bold=True)
    font_title = _get_font(42 if is_vertical else 34, bold=True)
    font_artist = _get_font(28 if is_vertical else 24, bold=False)
    font_badge = _get_font(20 if is_vertical else 17, bold=True)
    font_card_head = _get_font(13 if is_vertical else 11, bold=True)
    font_ruler = _get_font(11 if is_vertical else 10, bold=True)

    # 3. Header de marca superior
    brand_text = "RADICAL RECORDS · STUDIO PREVIEW"
    draw.text((width // 2, 70 if is_vertical else 40), brand_text, font=font_brand, fill=(244, 63, 94, 255), anchor="mm")

    # 4. Geometría según aspecto
    if is_vertical:
        cover_size = 680
        cover_y = 220
        card_w, card_h = 860, 240
        card_y = cover_y + cover_size + 35
        text_start_y = card_y + card_h + 45
    else:
        cover_size = 460
        cover_y = 75
        card_w, card_h = 840, 170
        card_y = cover_y + cover_size + 25
        text_start_y = card_y + card_h + 30

    cover_x = (width - cover_size) // 2
    card_x = (width - card_w) // 2

    # 5. Marco exterior brillante y sombra de la carátula
    draw.rounded_rectangle(
        [(cover_x - 8, cover_y - 8), (cover_x + cover_size + 8, cover_y + cover_size + 8)],
        radius=20,
        outline=(56, 189, 248, 70),
        width=2,
    )
    draw.rounded_rectangle(
        [(cover_x - 3, cover_y - 3), (cover_x + cover_size + 3, cover_y + cover_size + 3)],
        radius=16,
        outline=(255, 255, 255, 120),
        width=3,
    )

    # 6. Tarjeta contenedora de estudio para el visualizador
    draw.rounded_rectangle(
        [(card_x, card_y), (card_x + card_w, card_y + card_h)],
        radius=20,
        fill=(15, 17, 26, 220),
        outline=(56, 189, 248, 140),
        width=2,
    )
    # Títulos superiores de la tarjeta
    draw.text((card_x + 22, card_y + 14), "SPECTRUM & DYNAMIC FREQUENCY ANALYZER", font=font_card_head, fill=(56, 189, 248, 240))
    draw.text((card_x + card_w - 22, card_y + 14), "24-BIT MASTER · 44.1 kHz", font=font_card_head, fill=(148, 163, 184, 210), anchor="ra")

    # Regla de frecuencias inferior
    freq_scale = "20Hz       100Hz       250Hz       500Hz       1kHz       2.5kHz       5kHz       10kHz       20kHz"
    draw.text((card_x + card_w // 2, card_y + card_h - 13), freq_scale, font=font_ruler, fill=(125, 211, 252, 170), anchor="mm")

    # 7. Título de pista y Artista
    display_title = title if len(title) <= 32 else title[:29] + "…"
    display_artist = artist if len(artist) <= 38 else artist[:35] + "…"

    draw.text((width // 2, text_start_y), display_title, font=font_title, fill=(255, 255, 255, 255), anchor="mm")
    draw.text((width // 2, text_start_y + (52 if is_vertical else 42)), display_artist, font=font_artist, fill=(161, 161, 170, 255), anchor="mm")

    # 8. Badges de metadatos (BPM, Clave Camelot, Mastering)
    bpm_txt = f"{int(round(bpm))} BPM" if bpm > 0 else "128 BPM"
    key_txt = key_str if key_str else "8A · Am"

    badges = [
        ("⚡", bpm_txt, (34, 197, 94)),      # Emerald
        ("🎵", key_txt, (168, 85, 247)),    # Cyber Purple
        ("🎛️", "STUDIO MASTER", (56, 189, 248)),  # Electric Cyan
        ("🔥", "EXCLUSIVE", (244, 63, 94)),  # Radical Rose
    ]

    badge_y = text_start_y + (130 if is_vertical else 90)
    bw, bh = (175, 46) if is_vertical else (150, 38)
    spacing = 16 if is_vertical else 12
    total_w = len(badges) * bw + (len(badges) - 1) * spacing
    cur_x = (width - total_w) // 2

    for icon, txt, color in badges:
        draw.rounded_rectangle(
            [(cur_x, badge_y), (cur_x + bw, badge_y + bh)],
            radius=bh // 2,
            fill=(22, 24, 34, 230),
            outline=color,
            width=2,
        )
        full_txt = f"{icon} {txt}"
        draw.text((cur_x + bw // 2, badge_y + bh // 2), full_txt, font=font_badge, fill=(255, 255, 255, 255), anchor="mm")
        cur_x += bw + spacing

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
    Renderiza un vídeo MP4 de estudio optimizado para TikTok, Instagram Reels y YouTube Shorts.
    Integra analizador dual de espectro de frecuencias + osciloscopio en tiempo real.
    """
    def _prog(pct: int, msg: str):
        if progress_cb:
            progress_cb(pct, msg)

    ffmpeg_bin = get_ffmpeg_path()
    if not ffmpeg_bin:
        raise RuntimeError("FFmpeg no encontrado. No es posible generar el vídeo social.")

    _prog(5, "Configurando dimensiones de vídeo de estudio…")
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    if aspect_ratio == "1:1":
        vw, vh = 1080, 1080
        cover_size = 460
        cover_y = 75
        card_w, card_h = 840, 170
        card_y = cover_y + cover_size + 25
        wave_w = 800
        freq_h = 75
        wave_sub_h = 45
        wave_y = card_y + 26
    else:  # "9:16" Vertical Reels/TikTok
        vw, vh = 1080, 1920
        cover_size = 680
        cover_y = 220
        card_w, card_h = 860, 240
        card_y = cover_y + cover_size + 35
        wave_w = 820
        freq_h = 110
        wave_sub_h = 65
        wave_y = card_y + 36

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
    _prog(15, "Diseñando gráfica de estudio y tarjeta de espectro…")
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

    _prog(35, "Renderizando vídeo con espectro FFT + osciloscopio dinámico…")

    # Filtro complejo FFmpeg:
    # 0: audio
    # 1: carátula
    # 2: overlay PNG
    filter_complex = (
        f"[1:v]scale={vw}:{vh}:force_original_aspect_ratio=increase,crop={vw}:{vh},boxblur=30:5[bg];"
        f"[1:v]scale={cover_size}:{cover_size}:force_original_aspect_ratio=decrease[fg];"
        f"[0:a]showfreqs=s={wave_w}x{freq_h}:mode=bar:ascale=cbrt:fscale=log:win_size=2048:averaging=2:colors=0x22d3ee|0xa855f7[fq];"
        f"[0:a]showwaves=s={wave_w}x{wave_sub_h}:mode=cline:scale=cbrt:colors=0xf43f5e|0xa855f7:rate=30[wv];"
        f"[fq][wv]vstack[waves];"
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
