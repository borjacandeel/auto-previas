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


def _draw_vector_icon(draw: ImageDraw.ImageDraw, icon_type: str, cx: int, cy: int, color: tuple):
    """
    Dibuja iconos vectoriales nítidos para evitar depender de fuentes de emojis del sistema
    (evitando así los cuadrados vacíos [] en Windows y macOS).
    """
    if icon_type == "bpm":
        # Rayo de energía BPM
        pts = [
            (cx + 2, cy - 9),
            (cx - 5, cy + 1),
            (cx, cy + 1),
            (cx - 3, cy + 10),
            (cx + 6, cy - 1),
            (cx + 1, cy - 1),
        ]
        draw.polygon(pts, fill=color)
    elif icon_type == "key":
        # Disco de vinilo / Nota musical
        draw.ellipse([(cx - 8, cy - 8), (cx + 8, cy + 8)], outline=color, width=2)
        draw.ellipse([(cx - 2, cy - 2), (cx + 2, cy + 2)], fill=color)
    elif icon_type == "master":
        # Faders de mesa de mezclas de estudio
        draw.line([(cx - 4, cy - 7), (cx - 4, cy + 7)], fill=color, width=2)
        draw.rectangle([(cx - 6, cy - 3), (cx - 2, cy + 1)], fill=color)
        draw.line([(cx + 4, cy - 7), (cx + 4, cy + 7)], fill=color, width=2)
        draw.rectangle([(cx + 2, cy + 1), (cx + 6, cy + 5)], fill=color)
    elif icon_type == "exclusive":
        # Estrella / Llama de exclusividad
        pts = [
            (cx, cy - 8), (cx + 2, cy - 2), (cx + 8, cy - 2),
            (cx + 3, cy + 2), (cx + 5, cy + 8), (cx, cy + 4),
            (cx - 5, cy + 8), (cx - 3, cy + 2), (cx - 8, cy - 2), (cx - 2, cy - 2)
        ]
        draw.polygon(pts, fill=color)


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
    for y in range(280):
        alpha = int(210 * (1.0 - y / 280.0))
        draw.line([(0, y), (width, y)], fill=(6, 8, 14, alpha))

    for y in range(height - 480, height):
        progress = (y - (height - 480)) / 480.0
        alpha = int(240 * progress)
        draw.line([(0, y), (width, y)], fill=(6, 8, 14, alpha))

    # 2. Tipografías
    font_brand = _get_font(21 if is_vertical else 16, bold=True)
    font_title = _get_font(50 if is_vertical else 38, bold=True)
    font_artist = _get_font(30 if is_vertical else 24, bold=True)
    font_badge = _get_font(18 if is_vertical else 15, bold=True)
    font_card_head = _get_font(13 if is_vertical else 11, bold=True)
    font_ruler = _get_font(11 if is_vertical else 10, bold=True)
    font_tag = _get_font(13 if is_vertical else 11, bold=True)

    # 3. Header de marca superior tipo banner broadcast
    top_y = 95 if is_vertical else 40
    # Punto rojo de emisión en directo
    dot_r = 7 if is_vertical else 5
    dot_x = width // 2 - (220 if is_vertical else 160)
    draw.ellipse([(dot_x - dot_r, top_y - dot_r), (dot_x + dot_r, top_y + dot_r)], fill=(239, 68, 68, 255))
    draw.text((width // 2 - 80, top_y), "RADICAL RECORDS", font=font_brand, fill=(255, 255, 255, 255), anchor="mm")
    draw.text((width // 2 + 115, top_y), "· STUDIO PREVIEW", font=font_brand, fill=(244, 63, 94, 255), anchor="mm")

    # 4. Geometría según aspecto
    if is_vertical:
        cover_size = 680
        cover_y = 190
        card_w, card_h = 880, 310
        card_y = cover_y + cover_size + 40
        text_start_y = card_y + card_h + 65
    else:
        cover_size = 440
        cover_y = 65
        card_w, card_h = 840, 200
        card_y = cover_y + cover_size + 20
        text_start_y = card_y + card_h + 35

    cover_x = (width - cover_size) // 2
    card_x = (width - card_w) // 2

    # 5. Marco exterior brillante y sombra de la carátula
    draw.rounded_rectangle(
        [(cover_x - 10, cover_y - 10), (cover_x + cover_size + 10, cover_y + cover_size + 10)],
        radius=38,
        outline=(56, 189, 248, 85),
        width=2,
    )
    draw.rounded_rectangle(
        [(cover_x - 3, cover_y - 3), (cover_x + cover_size + 3, cover_y + cover_size + 3)],
        radius=30,
        outline=(255, 255, 255, 150),
        width=3,
    )

    # 6. Tarjeta contenedora Glassmorphism para el visualizador
    draw.rounded_rectangle(
        [(card_x, card_y), (card_x + card_w, card_y + card_h)],
        radius=24,
        fill=(12, 14, 24, 225),
        outline=(56, 189, 248, 150),
        width=2,
    )
    # Títulos superiores de la tarjeta
    draw.text((card_x + 24, card_y + 16), "SPECTRUM & DYNAMIC FREQUENCY ANALYZER", font=font_card_head, fill=(56, 189, 248, 240))
    draw.text((card_x + card_w - 24, card_y + 16), "24-BIT MASTER · 44.1 kHz", font=font_card_head, fill=(203, 213, 225, 210), anchor="ra")

    # Líneas guía de decibelios sutiles
    grid_y1 = card_y + int(card_h * 0.35)
    grid_y2 = card_y + int(card_h * 0.60)
    for gx in range(card_x + 35, card_x + card_w - 35, 18):
        draw.line([(gx, grid_y1), (gx + 9, grid_y1)], fill=(255, 255, 255, 25))
        draw.line([(gx, grid_y2), (gx + 9, grid_y2)], fill=(255, 255, 255, 25))

    draw.text((card_x + 28, grid_y1 - 6), "-6 dB", font=font_ruler, fill=(148, 163, 184, 130))
    draw.text((card_x + 28, grid_y2 - 6), "-18 dB", font=font_ruler, fill=(148, 163, 184, 130))

    # Regla de frecuencias inferior calibrada
    freq_scale = "20Hz    60Hz    120Hz    250Hz    500Hz    1kHz    2.5kHz    5kHz    10kHz    20kHz"
    draw.text((card_x + card_w // 2, card_y + card_h - 14), freq_scale, font=font_ruler, fill=(125, 211, 252, 190), anchor="mm")

    # 7. Título de pista y Artista con sombra de texto para máxima legibilidad
    tag_y = text_start_y - 28
    tag_w, tag_h = 220, 28
    draw.rounded_rectangle(
        [(width // 2 - tag_w // 2, tag_y - tag_h // 2), (width // 2 + tag_w // 2, tag_y + tag_h // 2)],
        radius=14,
        fill=(244, 63, 94, 220),
    )
    draw.text((width // 2, tag_y), "EXCLUSIVE AUDIO PREVIEW", font=font_tag, fill=(255, 255, 255, 255), anchor="mm")

    display_title = title if len(title) <= 32 else title[:29] + "…"
    display_artist = artist if len(artist) <= 38 else artist[:35] + "…"

    # Sombra del título
    draw.text((width // 2 + 2, text_start_y + 16), display_title, font=font_title, fill=(0, 0, 0, 230), anchor="mm")
    draw.text((width // 2, text_start_y + 14), display_title, font=font_title, fill=(255, 255, 255, 255), anchor="mm")

    # Artista en Cyan Eléctrico con sombra
    artist_y = text_start_y + (68 if is_vertical else 50)
    draw.text((width // 2 + 2, artist_y + 2), display_artist, font=font_artist, fill=(0, 0, 0, 230), anchor="mm")
    draw.text((width // 2, artist_y), display_artist, font=font_artist, fill=(56, 189, 248, 255), anchor="mm")

    # 8. Badges de metadatos (BPM, Clave Camelot, Mastering) con iconos vectoriales dibujados
    bpm_txt = f"{int(round(bpm))} BPM" if bpm > 0 else "128 BPM"
    key_txt = key_str if key_str else "8A · Am"

    badges = [
        ("bpm", bpm_txt, (34, 197, 94)),          # Emerald
        ("key", key_txt, (168, 85, 247)),        # Cyber Purple
        ("master", "STUDIO MASTER", (56, 189, 248)),  # Electric Cyan
        ("exclusive", "EXCLUSIVE", (244, 63, 94)),  # Radical Rose
    ]

    badge_y = artist_y + (85 if is_vertical else 60)
    bw, bh = (184, 50) if is_vertical else (156, 42)
    spacing = 16 if is_vertical else 12
    total_w = len(badges) * bw + (len(badges) - 1) * spacing
    cur_x = (width - total_w) // 2

    for icon_type, txt, color in badges:
        draw.rounded_rectangle(
            [(cur_x, badge_y), (cur_x + bw, badge_y + bh)],
            radius=bh // 2,
            fill=(18, 20, 32, 235),
            outline=color,
            width=2,
        )
        # Dibujar icono vectorial nítido
        _draw_vector_icon(draw, icon_type, cur_x + 24, badge_y + bh // 2, color)
        # Dibujar texto
        draw.text((cur_x + 36 + (bw - 36) // 2, badge_y + bh // 2), txt, font=font_badge, fill=(255, 255, 255, 255), anchor="mm")
        cur_x += bw + spacing

    # Marca de agua al pie
    footer_text = "RADICAL RECORDS · PRODUCED WITH AUTOPREVIAS AI"
    draw.text((width // 2, height - (55 if is_vertical else 30)), footer_text, font=font_card_head, fill=(100, 116, 139, 170), anchor="mm")

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
    Integra analizador dual de espectro de frecuencias + osciloscopio en tiempo real con
    carátula con esquinas redondeadas y atmósfera cinematográfica profunda.
    """
    def _prog(pct: int, msg: str):
        if progress_cb:
            progress_cb(pct, msg)

    ffmpeg_bin = get_ffmpeg_path()
    if not ffmpeg_bin:
        raise RuntimeError("FFmpeg no encontrado. No es posible generar el vídeo social.")

    _prog(5, "Configurando dimensiones y plantilla de estudio…")
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    if aspect_ratio == "1:1":
        vw, vh = 1080, 1080
        cover_size = 440
        cover_y = 65
        card_w, card_h = 840, 190
        card_y = cover_y + cover_size + 20
        wave_w = 800
        freq_h = 110
        wave_sub_h = 50
        wave_y = card_y + 24
    else:  # "9:16" Vertical Reels/TikTok
        vw, vh = 1080, 1920
        cover_size = 660
        cover_y = 200
        card_w, card_h = 880, 290
        card_y = cover_y + cover_size + 35
        wave_w = 840
        freq_h = 175
        wave_sub_h = 75
        wave_y = card_y + 32

    cover_x = (vw - cover_size) // 2
    wave_x = (vw - wave_w) // 2

    # Resolver carátula original
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

    # Generar carátula con esquinas redondeadas de estudio
    _prog(12, "Procesando carátula con esquinas redondeadas y máscara alfa…")
    rounded_cover_png = cache_dir / f"rounded_cover_{os.getpid()}.png"
    try:
        cov_img = Image.open(cover_resolved).convert("RGBA")
        cov_img = cov_img.resize((cover_size, cover_size), Image.Resampling.LANCZOS)
        mask = Image.new("L", (cover_size, cover_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (cover_size, cover_size)], radius=28, fill=255)
        cov_img.putalpha(mask)
        cov_img.save(str(rounded_cover_png), "PNG")
    except Exception:
        rounded_cover_png = cover_resolved

    # Generar overlay gráfico con PIL
    _prog(20, "Diseñando interfaz de estudio, badges vectoriales y tarjeta de espectro…")
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

    _prog(40, "Renderizando vídeo con espectro FFT + osciloscopio dinámico y colorkey…")

    # Filtro complejo FFmpeg:
    # 0: audio
    # 1: carátula original (usada para fondo atmosférico)
    # 2: carátula recortada redondeada
    # 3: overlay PNG (gráfica, textos y tarjeta)
    filter_complex = (
        f"[1:v]scale={vw}:{vh}:force_original_aspect_ratio=increase,crop={vw}:{vh},boxblur=40:5,eq=brightness=-0.35:contrast=1.35:saturation=2.2[bg];"
        f"[0:a]volume=2.4,showfreqs=s={wave_w}x{freq_h}:mode=bar:ascale=sqrt:fscale=log:win_size=1024:averaging=1:colors=0x00f5ff|0xff007f|0xffea00,colorkey=0x000000:0.1:0.1[fq];"
        f"[0:a]volume=1.8,showwaves=s={wave_w}x{wave_sub_h}:mode=cline:scale=sqrt:draw=full:colors=0xff007f|0x00f5ff:rate=30,colorkey=0x000000:0.1:0.1[wv];"
        f"[fq][wv]vstack[waves];"
        f"[bg][2:v]overlay={cover_x}:{cover_y}[v1];"
        f"[v1][waves]overlay={wave_x}:{wave_y}[v2];"
        f"[v2][3:v]overlay=0:0:shortest=1[vfinal]"
    )

    out_p = Path(output_video_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(audio_path),
        "-loop", "1", "-i", str(cover_resolved),
        "-loop", "1", "-i", str(rounded_cover_png),
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
        for tmp_file in [overlay_png, rounded_cover_png]:
            if tmp_file != cover_resolved and Path(tmp_file).exists():
                try:
                    Path(tmp_file).unlink()
                except Exception:
                    pass

    _prog(100, "¡Vídeo social de alta fidelidad exportado con éxito!")
    return str(out_p)
