"""
AutoPrevias v2.1 — video.py
Generador de vídeos de alta fidelidad para redes sociales (Reels, TikTok, Shorts).
Crea vídeos MP4 con carátula en alta resolución, fondo cinemático atmosférico,
visualizador TRIPLE (espectrograma de color + FFT de barras + osciloscopio P2P),
paletas de color neón seleccionables y barra de progreso TikTok animada.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageFont

from src.config import get_assets_dir, get_cache_dir, get_ffmpeg_path

# ── Paletas Neón de Estudio ──────────────────────────────────────────────────
PALETTES = {
    "radical": {
        "name": "Cian & Magenta Radical",
        "colors_freq": "0x00f5ff|0xff007f|0xffea00",
        "colors_wave": "0xff007f|0x00f5ff",
        "glow_rgb": (56, 189, 248),
        "accent_rgb": (244, 63, 94),
        "tag_bg": (244, 63, 94, 225),
        "progress_hex": "0x00f5ff",
    },
    "rave": {
        "name": "Verde Neón Rave / Acid",
        "colors_freq": "0x39ff14|0x00ff88|0x00f5ff",
        "colors_wave": "0x39ff14|0x00ff88",
        "glow_rgb": (57, 255, 20),
        "accent_rgb": (0, 255, 136),
        "tag_bg": (34, 197, 94, 225),
        "progress_hex": "0x39ff14",
    },
    "crimson": {
        "name": "Rojo Carmesí Studio",
        "colors_freq": "0xff1e38|0xff5e00|0xffea00",
        "colors_wave": "0xff1e38|0xff5e00",
        "glow_rgb": (255, 30, 56),
        "accent_rgb": (255, 94, 0),
        "tag_bg": (255, 30, 56, 225),
        "progress_hex": "0xff1e38",
    },
    "amber": {
        "name": "Ámbar Gold & Solar",
        "colors_freq": "0xffea00|0xff9900|0xff3300",
        "colors_wave": "0xffea00|0xff9900",
        "glow_rgb": (255, 183, 0),
        "accent_rgb": (255, 136, 0),
        "tag_bg": (245, 158, 11, 225),
        "progress_hex": "0xffea00",
    },
    "cyber": {
        "name": "Cyber Violet & Purple",
        "colors_freq": "0xb026ff|0x7928ca|0x00f5ff",
        "colors_wave": "0xb026ff|0x7928ca",
        "glow_rgb": (176, 38, 255),
        "accent_rgb": (121, 40, 202),
        "tag_bg": (168, 85, 247, 225),
        "progress_hex": "0xb026ff",
    },
}


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
    palette_key: str = "radical",
    promo_text: str = "",
) -> Path:
    """
    Genera una imagen PNG semitransparente de estudio profesional con marco de carátula iluminado,
    tarjeta de analizador de espectro, tipografía broadcast, badges vectoriales y banner promocional.
    """
    p_cfg = PALETTES.get(palette_key.lower(), PALETTES["radical"])
    glow_col = p_cfg["glow_rgb"]
    accent_col = p_cfg["accent_rgb"]
    tag_bg = p_cfg["tag_bg"]

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    is_vertical = height >= 1600

    # 1. Gradiente superior e inferior para máxima legibilidad cinematográfica
    for y in range(320):
        alpha = int(220 * (1.0 - y / 320.0))
        draw.line([(0, y), (width, y)], fill=(6, 8, 14, alpha))

    for y in range(height - 520, height):
        progress = (y - (height - 520)) / 520.0
        alpha = int(245 * progress)
        draw.line([(0, y), (width, y)], fill=(6, 8, 14, alpha))

    # 2. Tipografías
    font_brand = _get_font(21 if is_vertical else 16, bold=True)
    font_promo = _get_font(15 if is_vertical else 12, bold=True)
    font_title = _get_font(52 if is_vertical else 38, bold=True)
    font_artist = _get_font(30 if is_vertical else 24, bold=True)
    font_badge = _get_font(18 if is_vertical else 15, bold=True)
    font_card_head = _get_font(13 if is_vertical else 11, bold=True)
    font_ruler = _get_font(11 if is_vertical else 10, bold=True)
    font_tag = _get_font(13 if is_vertical else 11, bold=True)

    # 3. Header de marca superior tipo banner broadcast
    top_y = 95 if is_vertical else 40
    dot_r = 7 if is_vertical else 5
    dot_x = width // 2 - (220 if is_vertical else 160)
    draw.ellipse([(dot_x - dot_r, top_y - dot_r), (dot_x + dot_r, top_y + dot_r)], fill=(239, 68, 68, 255))
    draw.text((width // 2 - 80, top_y), "RADICAL RECORDS", font=font_brand, fill=(255, 255, 255, 255), anchor="mm")
    draw.text((width // 2 + 115, top_y), "· STUDIO PREVIEW", font=font_brand, fill=accent_col + (255,), anchor="mm")

    # Banner promocional opcional (Apartado 2: 3)
    p_text = promo_text.strip() if promo_text and promo_text.strip() else "EXCLUSIVA · RADICAL RECORDS"
    promo_y = top_y + (38 if is_vertical else 26)
    promo_w = min(width - 80, int(len(p_text) * 11 + 40))
    draw.rounded_rectangle(
        [(width // 2 - promo_w // 2, promo_y - 12), (width // 2 + promo_w // 2, promo_y + 12)],
        radius=12,
        fill=(15, 23, 42, 190),
        outline=glow_col + (140,),
        width=1,
    )
    draw.text((width // 2, promo_y), p_text.upper(), font=font_promo, fill=glow_col + (240,), anchor="mm")

    # 4. Geometría según aspecto
    if is_vertical:
        cover_size = 660
        cover_y = 205
        card_w, card_h = 890, 350
        card_y = cover_y + cover_size + 42
        text_start_y = card_y + card_h + 58
    else:
        cover_size = 440
        cover_y = 65
        card_w, card_h = 840, 225
        card_y = cover_y + cover_size + 20
        text_start_y = card_y + card_h + 30

    cover_x = (width - cover_size) // 2
    card_x = (width - card_w) // 2

    # 5. Marco exterior brillante y sombra multicapa de la carátula (Glow Neón)
    # Resplandor exterior suave
    draw.rounded_rectangle(
        [(cover_x - 12, cover_y - 12), (cover_x + cover_size + 12, cover_y + cover_size + 12)],
        radius=40,
        outline=glow_col + (65,),
        width=3,
    )
    # Resplandor medio
    draw.rounded_rectangle(
        [(cover_x - 6, cover_y - 6), (cover_x + cover_size + 6, cover_y + cover_size + 6)],
        radius=34,
        outline=glow_col + (140,),
        width=2,
    )
    # Bisel nítido blanco de estudio
    draw.rounded_rectangle(
        [(cover_x - 2, cover_y - 2), (cover_x + cover_size + 2, cover_y + cover_size + 2)],
        radius=30,
        outline=(255, 255, 255, 180),
        width=2,
    )

    # 6. Tarjeta contenedora Glassmorphism para el visualizador triple
    draw.rounded_rectangle(
        [(card_x, card_y), (card_x + card_w, card_y + card_h)],
        radius=26,
        fill=(8, 10, 20, 240),
        outline=glow_col + (170,),
        width=2,
    )
    # Reflejo de luz en borde superior
    draw.line([(card_x + 30, card_y + 1), (card_x + card_w - 30, card_y + 1)], fill=(255, 255, 255, 140), width=1)
    # Segundo bisel más sutil
    draw.rounded_rectangle(
        [(card_x + 3, card_y + 3), (card_x + card_w - 3, card_y + card_h - 3)],
        radius=23,
        outline=glow_col + (40,),
        width=1,
    )

    # Header de la tarjeta — título y sample rate
    draw.text((card_x + 22, card_y + 14), "TRIPLE VISUALIZER · STUDIO ANALYZER", font=font_card_head, fill=glow_col + (250,))
    draw.text((card_x + card_w - 22, card_y + 14), "24-BIT · 44.1 kHz", font=font_card_head, fill=(203, 213, 225, 220), anchor="ra")

    # ── Líneas divisoras entre las tres capas del visualizador ──────────────
    # Estas alturas deben coincidir aproximadamente con los umbrales spec/fft/wave
    if is_vertical:
        div1_y = card_y + 38 + 105   # tras espectrograma
        div2_y = div1_y + 130        # tras barras FFT
    else:
        div1_y = card_y + 32 + 62
        div2_y = div1_y + 95

    # Divisor 1: espectrograma → FFT
    draw.line([(card_x + 16, div1_y), (card_x + card_w - 16, div1_y)], fill=glow_col + (55,), width=1)
    draw.text((card_x + 22, div1_y + 3), "FREQUENCY SPECTRUM", font=font_ruler, fill=glow_col + (160,))
    draw.text((card_x + card_w - 22, div1_y + 3), "FFT BARS", font=font_ruler, fill=(148, 163, 184, 140), anchor="ra")

    # Divisor 2: FFT → osciloscopio
    draw.line([(card_x + 16, div2_y), (card_x + card_w - 16, div2_y)], fill=accent_col + (55,), width=1)
    draw.text((card_x + 22, div2_y + 3), "WAVEFORM P2P", font=font_ruler, fill=accent_col + (170,))

    # Etiqueta superior del espectrograma (dentro del card, encima de la capa 1)
    draw.text((card_x + 22, card_y + 36), "SPECTROGRAM", font=font_ruler, fill=glow_col + (180,))
    draw.text((card_x + card_w - 22, card_y + 36), "SCROLL ›", font=font_ruler, fill=(100, 116, 139, 130), anchor="ra")

    # Líneas guía de dB en la zona FFT (capa 2)
    grid_y1 = div1_y + int((div2_y - div1_y) * 0.32)
    grid_y2 = div1_y + int((div2_y - div1_y) * 0.62)
    for gx in range(card_x + 35, card_x + card_w - 35, 20):
        draw.line([(gx, grid_y1), (gx + 10, grid_y1)], fill=(255, 255, 255, 20))
        draw.line([(gx, grid_y2), (gx + 10, grid_y2)], fill=(255, 255, 255, 20))
    draw.text((card_x + 26, grid_y1 - 5), "-6 dB", font=font_ruler, fill=(100, 116, 139, 120))
    draw.text((card_x + 26, grid_y2 - 5), "-18 dB", font=font_ruler, fill=(100, 116, 139, 110))

    # Regla de frecuencias en la parte inferior del card
    freq_scale = "20Hz    125Hz    500Hz    1kHz    4kHz    10kHz    20kHz"
    draw.text((card_x + card_w // 2, card_y + card_h - 12), freq_scale, font=font_ruler, fill=glow_col + (190,), anchor="mm")

    # 7. Título de pista y Artista con sombra de texto para máxima legibilidad
    tag_y = text_start_y - 28
    tag_w, tag_h = 240, 28
    draw.rounded_rectangle(
        [(width // 2 - tag_w // 2, tag_y - tag_h // 2), (width // 2 + tag_w // 2, tag_y + tag_h // 2)],
        radius=14,
        fill=tag_bg,
    )
    draw.text((width // 2, tag_y), "EXCLUSIVE AUDIO PREVIEW", font=font_tag, fill=(255, 255, 255, 255), anchor="mm")

    display_title = title if len(title) <= 32 else title[:29] + "…"
    display_artist = artist if len(artist) <= 38 else artist[:35] + "…"

    # Sombra del título
    draw.text((width // 2 + 2, text_start_y + 16), display_title, font=font_title, fill=(0, 0, 0, 240), anchor="mm")
    draw.text((width // 2, text_start_y + 14), display_title, font=font_title, fill=(255, 255, 255, 255), anchor="mm")

    # Artista con acento de color de la paleta
    artist_y = text_start_y + (68 if is_vertical else 50)
    draw.text((width // 2 + 2, artist_y + 2), display_artist, font=font_artist, fill=(0, 0, 0, 240), anchor="mm")
    draw.text((width // 2, artist_y), display_artist, font=font_artist, fill=glow_col + (255,), anchor="mm")

    # 8. Badges de metadatos (BPM, Clave Camelot, Mastering) con iconos vectoriales dibujados
    bpm_txt = f"{int(round(bpm))} BPM" if bpm > 0 else "128 BPM"
    key_txt = key_str if key_str else "8A · Am"

    badges = [
        ("bpm", bpm_txt, (34, 197, 94)),              # Emerald
        ("key", key_txt, (168, 85, 247)),            # Cyber Purple
        ("master", "STUDIO MASTER", glow_col),        # Paleta Glow
        ("exclusive", "EXCLUSIVE", accent_col),       # Paleta Accent
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
    footer_text = "RADICAL RECORDS · PRODUCED WITH AUTOPREVIAS v2.0"
    draw.text((width // 2, height - (55 if is_vertical else 30)), footer_text, font=font_card_head, fill=(100, 116, 139, 180), anchor="mm")

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
    palette_key: str = "radical",
    promo_text: str = "",
    progress_cb: Optional[Callable[[int, str], None]] = None,
) -> str:
    """
    Renderiza un vídeo MP4 de estudio optimizado para TikTok, Instagram Reels y YouTube Shorts.
    Integra analizador dual de espectro de frecuencias + osciloscopio en tiempo real con
    carátula con esquinas redondeadas, atmósfera cinematográfica profunda y barra de progreso TikTok.
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

    p_cfg = PALETTES.get(palette_key.lower(), PALETTES["radical"])

    # Calcular duración del audio para la barra de progreso animada
    dur_sec = 60.0
    try:
        import soundfile as sf
        info = sf.info(audio_path)
        dur_sec = max(1.0, float(info.duration))
    except Exception:
        pass

    if aspect_ratio == "1:1":
        vw, vh = 1080, 1080
        cover_size = 440
        cover_y = 65
        card_w, card_h = 840, 225
        card_y = cover_y + cover_size + 20
        wave_w = 800
        spec_h = 62      # espectrograma scrolling
        freq_h = 95      # barras FFT
        wave_sub_h = 48  # osciloscopio P2P
        wave_y = card_y + 28
    else:  # "9:16" Vertical Reels/TikTok
        vw, vh = 1080, 1920
        cover_size = 660
        cover_y = 205
        card_w, card_h = 890, 350
        card_y = cover_y + cover_size + 42
        wave_w = 850
        spec_h = 105     # espectrograma scrolling
        freq_h = 130     # barras FFT
        wave_sub_h = 68  # osciloscopio P2P
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
        palette_key=palette_key,
        promo_text=promo_text,
    )

    _prog(40, "Renderizando vídeo triple-capa (espectrograma + FFT + osciloscopio P2P) y barra TikTok…")

    # Filtro complejo FFmpeg — visualizador triple:
    # 0: audio fuente
    # 1: carátula original → fondo cinemático con color grading intenso
    # 2: carátula recortada redondeada (carátula de estudio)
    # 3: overlay PNG (textos, tarjeta glassmorphism, badges vectoriales)
    # Capa 1: showspectrum (heatmap de color scrolling — la más colorida)
    # Capa 2: showfreqs   (barras EQ FFT multicolor)
    # Capa 3: showwaves   (osciloscopio peak-to-peak — líneas gruesas)
    filter_complex = (
        # Fondo cinemático ultra-profundo con desenfoque atmosférico y color grading de alta saturación
        f"[1:v]scale={vw}:{vh}:force_original_aspect_ratio=increase,crop={vw}:{vh},"
        f"boxblur=52:6,eq=brightness=-0.28:contrast=1.48:saturation=3.0[bg];"

        # Espectrograma de color scrolling (heatmap arcoíris — la joya visual)
        # color=channel: cada canal de frecuencia tiene su propio color del espectro visual
        # scale=cbrt: compresión cúbica para realzar detalles de frecuencias medias
        # saturation=8: colores extremadamente vívidos y saturados
        f"[0:a]volume=3.2,showspectrum=s={wave_w}x{spec_h}:scale=cbrt:"
        f"color=channel:saturation=8:gain=5:slide=scroll:fps=30,"
        f"colorkey=0x000000:0.05:0.05[spec];"

        # Analizador FFT de barras multi-banda (EQ visual de estudio)
        # win_size=2048: mayor resolución frecuencial para barras más detalladas
        f"[0:a]volume=2.8,showfreqs=s={wave_w}x{freq_h}:mode=bar:ascale=sqrt:"
        f"fscale=log:win_size=2048:averaging=1:colors={p_cfg['colors_freq']},"
        f"colorkey=0x000000:0.12:0.12[fq];"

        # Osciloscopio P2P (peak-to-peak) — líneas gruesas y coloridas
        # mode=p2p: conecta los picos positivos y negativos, mucho más visible que cline
        # draw=full: rellena el área entre positivo y negativo
        f"[0:a]volume=2.2,showwaves=s={wave_w}x{wave_sub_h}:mode=p2p:"
        f"scale=sqrt:draw=full:colors={p_cfg['colors_wave']}:rate=30,"
        f"colorkey=0x000000:0.08:0.08[wv];"

        # Apilar los tres visualizadores verticalmente
        f"[spec][fq][wv]vstack=inputs=3[waves];"

        # Composición: fondo + carátula + visualizador + overlay de texto
        f"[bg][2:v]overlay={cover_x}:{cover_y}[v1];"
        f"[v1][waves]overlay={wave_x}:{wave_y}[v2];"
        f"[v2][3:v]overlay=0:0:shortest=1[v_over];"

        # Barra de progreso TikTok animada (track inferior con brillo neón)
        f"[v_over]drawbox=x=0:y=ih-14:w=iw:h=14:color=0x07090f@0.92:t=fill,"
        f"drawbox=x=0:y=ih-14:w='min(iw,iw*(t/{dur_sec:.2f}))':h=14:color={p_cfg['progress_hex']}@0.95:t=fill,"
        f"drawbox=x=0:y=ih-15:w='min(iw,iw*(t/{dur_sec:.2f}))':h=3:color=0xffffff@0.85:t=fill[vfinal]"
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
