"""
Motor de exportación de la previa.

Flujo:
1. Cargar audio fuente completo (stereo 44100 Hz)
2. Extraer y concatenar los segmentos del plan con crossfades
3. Generar envolvente de pitch progresivo (5-8 glides suaves)
4. Aplicar envolvente por chunks
5. Fade in / fade out cuadráticos
6. Normalizar a -1 dBFS
7. Exportar WAV 24-bit y/o MP3 320 kbps
"""

from pathlib import Path
from typing import Callable, List

import numpy as np
import soundfile as sf

from src.analysis.bpm import BeatGrid
from src.analysis.segments import PreviewPlan
from src.engine.timestretch import crossfade
from src.engine.variations import make_rate_envelope, make_custom_rate_envelope, apply_rate_envelope

SR_OUT   = 44100
XFADE_MS = 30.0


# ── fades y limitador ────────────────────────────────────────────────────────

def _apply_fades(y: np.ndarray, sr: int,
                 fade_in_sec: float, fade_out_sec: float) -> np.ndarray:
    """Aplica fade-in y fade-out con curva en S tipo coseno (cero clicks, inicio y fin planos)."""
    y = y.copy()
    n_in  = min(int(fade_in_sec  * sr), len(y) // 4)
    n_out = min(int(fade_out_sec * sr), len(y) // 4)
    if n_in > 0:
        t_in = (1.0 - np.cos(np.linspace(0.0, np.pi, n_in, dtype=np.float32))) / 2.0
        y[:n_in] *= t_in
    if n_out > 0:
        t_out = (1.0 + np.cos(np.linspace(0.0, np.pi, n_out, dtype=np.float32))) / 2.0
        y[-n_out:] *= t_out
    return y


def _dc_blocker(audio: np.ndarray, r: float = 0.995) -> np.ndarray:
    """
    Filtro paso-alto DC Blocker de precisión (~5 Hz).
    Elimina cualquier offset de corriente continua acumulado en transiciones o sintes analógicos.
    """
    from scipy.signal import lfilter
    out = np.zeros_like(audio)
    for ch in range(audio.shape[0]):
        out[ch] = lfilter([1.0, -1.0], [1.0, -r], audio[ch]).astype(np.float32)
    return out


def _soft_limiter(audio: np.ndarray, ceiling_db: float = -0.5) -> np.ndarray:
    """
    Limitador transparente de masterización con codo suave (soft-knee).
    Evita cualquier distorsión digital o recorte duro al modular el pitch y tempo.
    """
    ceiling = 10.0 ** (ceiling_db / 20.0)
    peak = float(np.max(np.abs(audio)))
    if peak <= ceiling:
        return audio.astype(np.float32)

    knee_start = ceiling * 0.88
    out = audio.copy()
    mask = np.abs(out) > knee_start
    if np.any(mask):
        overshoot = np.abs(out[mask]) - knee_start
        scale_range = ceiling - knee_start
        compressed = knee_start + scale_range * np.tanh(overshoot / scale_range)
        out[mask] = np.sign(out[mask]) * compressed
    return np.clip(out, -ceiling, ceiling).astype(np.float32)


# ── ensamblado ──────────────────────────────────────────────────────────────

def build_preview_audio(
    source_path: str,
    plan: PreviewPlan,
    beat_grid: BeatGrid,
    cfg: dict,
    progress_cb: Callable[[int, str], None] | None = None,
    seed: int | None = None,
) -> tuple:
    """
    Construye el audio de la previa.
    Devuelve (audio_float32 shape (2,N), sr, seed_usado).
    """
    def _prog(pct: int, msg: str):
        if progress_cb:
            progress_cb(pct, msg)

    min_rate  = 1.0 + cfg.get("tempo_min_pct", 0.0)  / 100
    max_rate  = 1.0 + cfg.get("tempo_max_pct", 15.0) / 100
    fade_in   = cfg.get("fade_in_sec",  2.0)
    fade_out  = cfg.get("fade_out_sec", 4.0)

    _prog(5, "Cargando audio fuente…")
    from src.engine.audio_io import load_audio_file
    y_src, sr_src = load_audio_file(source_path, sr=SR_OUT, mono=False, dtype=np.float32)

    if y_src.ndim == 1:
        y_src = np.stack([y_src, y_src])          # mono → stereo

    # ── paso 1: extraer y concatenar segmentos (sin speed change todavía) ──
    _prog(15, "Agrupando bloques musicales continuos…")
    # Agrupar segmentos contiguos en bloques de audio continuo (sin cortes ni fades entre ellos)
    blocks: List[List[float]] = []
    for seg in plan.segments:
        if not blocks:
            blocks.append([seg.source_start, seg.source_end])
        else:
            prev_end = blocks[-1][1]
            if abs(seg.source_start - prev_end) <= 0.08:
                # Contiguos en la canción original (ej. subida enlazando directo con el drop):
                # extender el bloque para que el bombo impacte al 100% de volumen sin interrupción
                blocks[-1][1] = max(prev_end, seg.source_end)
            else:
                blocks.append([seg.source_start, seg.source_end])

    _prog(25, "Extrayendo audio de bloques musicales…")
    block_audios: List[np.ndarray] = []
    n_blocks = len(blocks)
    for idx, (b_s, b_e) in enumerate(blocks):
        pct = 25 + int(25 * idx / max(n_blocks, 1))
        _prog(pct, f"Extrayendo bloque {idx + 1}/{n_blocks} ({b_e - b_s:.1f}s)…")
        f_s = max(0, min(int(b_s * SR_OUT), y_src.shape[1] - 1))
        f_e = max(f_s + 1, min(int(b_e * SR_OUT), y_src.shape[1]))
        block_audios.append(y_src[:, f_s:f_e])

    # ── paso 1b: Efectos de estudio automáticos en subidas (5s antes de cada drop) ──
    from src.engine.effects import apply_predrop_effects
    drop_times = list(getattr(plan, "drop_starts", []))
    if not drop_times:
        from src.analysis.structure import SectionType
        drop_times = [
            seg.section.start_time for seg in plan.segments
            if getattr(seg.section, "type", None) == SectionType.DROP
        ]

    if (cfg.get("fx_flanger") or cfg.get("fx_filter_sweep")) and drop_times:
        _prog(38, "Aplicando efectos automáticos 5s antes de los drops (Flanger + Filter Sweep)…")
        for idx, (b_s, b_e) in enumerate(blocks):
            block_audios[idx] = apply_predrop_effects(
                block_audios[idx],
                sr=SR_OUT,
                block_start_sec=b_s,
                block_end_sec=b_e,
                drop_timestamps=drop_times,
                cfg=cfg,
                pre_drop_sec=5.0,
            )

    # ── Aplicar en los cortes entre bloques: 1.0s bajada a cero y 1.0s subida a 100% ──
    _prog(45, "Aplicando transición en cortes (1s bajada a 0 y 1s subida)…")
    n_dip = int(1.0 * SR_OUT)  # 1.0 segundo exacto a 44100 Hz
    t_out = (1.0 + np.cos(np.linspace(0.0, np.pi, n_dip, dtype=np.float32))) / 2.0
    t_in  = (1.0 - np.cos(np.linspace(0.0, np.pi, n_dip, dtype=np.float32))) / 2.0

    processed_blocks: List[np.ndarray] = []
    for idx, b_aud in enumerate(block_audios):
        aud = b_aud.copy()
        # En todos los bloques a partir del segundo: subida progresiva de 1s desde 0 al comenzar tras el corte
        if idx > 0 and aud.shape[1] > 0:
            fl_in = min(n_dip, aud.shape[1] // 2)
            if fl_in > 0:
                aud[0, :fl_in] *= t_in[:fl_in]
                aud[1, :fl_in] *= t_in[:fl_in]

        # En todos los bloques antes del último: bajada progresiva de 1s hacia cero antes de saltar
        if idx < len(block_audios) - 1 and aud.shape[1] > 0:
            fl_out = min(n_dip, aud.shape[1] // 2)
            if fl_out > 0:
                aud[0, -fl_out:] *= t_out[-fl_out:]
                aud[1, -fl_out:] *= t_out[-fl_out:]

        processed_blocks.append(aud)

    _prog(50, "Uniendo bloques musicales procesados…")
    assembled = processed_blocks[0]
    for b_aud in processed_blocks[1:]:
        L = crossfade(assembled[0], b_aud[0], SR_OUT, duration_ms=40.0)
        R = crossfade(assembled[1], b_aud[1], SR_OUT, duration_ms=40.0)
        assembled = np.stack([L, R])

    # Liberar memoria de la pista original completa y bloques
    del y_src, block_audios, processed_blocks

    # ── paso 2: generar envolvente de pitch y aplicarla ────────────────────
    tempo_mode   = cfg.get("tempo_mode", "auto")
    tempo_events = cfg.get("tempo_events", [])
    base_bpm     = beat_grid.bpm if beat_grid else 128.0

    if tempo_mode == "manual" and tempo_events:
        _prog(60, "Aplicando curva de BPM personalizada (manual)…")
        rate_env, _ = make_custom_rate_envelope(
            n_samples=assembled.shape[1],
            sr=SR_OUT,
            base_bpm=base_bpm,
            events=tempo_events,
        )
        seed_used = seed if seed is not None else 0  # preservar seed original del usuario
    else:
        _prog(60, "Generando envolvente de pitch progresivo…")
        rate_env, seed_used = make_rate_envelope(
            n_samples=assembled.shape[1],
            sr=SR_OUT,
            min_rate=min_rate,
            max_rate=max_rate,
            seed=seed,
        )

    # ── paso 2b: efecto vinilo — spin-up en intro, spin-down en outro ────────
    # La velocidad arranca desde casi cero (vinilo arrancando) y sube de forma
    # perfectamente suave y continua (sin saltos ni bloques) al tempo original en 1.0 segundo.
    # En el final, desacelera suavemente de tempo original a casi cero en 1.0 segundo.
    SPIN_MIN = 0.08          # velocidad mínima (~8% = arranca casi de cero)
    SPIN_SEC = 1.0           # duración exacta: 1 segundo

    n_spin = min(int(SPIN_SEC * SR_OUT), assembled.shape[1] // 4)

    if n_spin > 0:
        # Rampa suave tipo coseno (curva en S sin saltos audibles)
        phase_up = np.linspace(0.0, np.pi, n_spin, dtype=np.float32)
        ramp_up = SPIN_MIN + (1.0 - SPIN_MIN) * (1.0 - np.cos(phase_up)) / 2.0
        rate_env[:n_spin] *= ramp_up

        phase_dn = np.linspace(0.0, np.pi, n_spin, dtype=np.float32)
        ramp_dn = SPIN_MIN + (1.0 - SPIN_MIN) * (1.0 + np.cos(phase_dn)) / 2.0
        rate_env[-n_spin:] *= ramp_dn

    speed_mode = cfg.get("speed_mode", "vinyl").lower()
    if speed_mode == "keylock":
        _prog(65, "Aplicando aceleración Keylock (tempo aumentado, tono original conservado)…")
        from src.engine.timestretch import stretch_audio
        avg_rate = float(np.mean(rate_env[n_spin:-n_spin])) if len(rate_env) > 2 * n_spin else float(np.mean(rate_env))
        avg_rate = max(0.85, min(1.35, avg_rate))

        # Spin-up/down: aplicar varispeed vinilo en los tramos de arranque/parada
        # (sube/baja con pitch natural), y time-stretch sin pitch en el cuerpo central.
        if n_spin > 0 and assembled.shape[1] > 2 * n_spin:
            spin_in  = assembled[:, :n_spin]
            body     = assembled[:, n_spin:-n_spin]
            spin_out = assembled[:, -n_spin:]

            # Rampa del spin: mismos vectores calculados arriba para rate_env
            spin_up_env = rate_env[:n_spin]
            spin_dn_env = rate_env[-n_spin:]

            proc_spin_in  = apply_rate_envelope(spin_in,  spin_up_env)
            proc_body     = stretch_audio(body, SR_OUT, stretch_factor=avg_rate)
            proc_spin_out = apply_rate_envelope(spin_out, spin_dn_env)

            L = crossfade(crossfade(proc_spin_in[0], proc_body[0], SR_OUT, 20.0),
                          proc_spin_out[0], SR_OUT, 20.0)
            R = crossfade(crossfade(proc_spin_in[1], proc_body[1], SR_OUT, 20.0),
                          proc_spin_out[1], SR_OUT, 20.0)
            result = np.stack([L, R])
        else:
            result = stretch_audio(assembled, SR_OUT, stretch_factor=avg_rate)
    else:
        _prog(65, "Aplicando aceleración Vinilo DJ Clásico (pitch armónico natural + spin)…")
        result = apply_rate_envelope(assembled, rate_env)

    del assembled, rate_env

    # ── paso 3: DC blocker + fades de volumen ──────────────────────────────────
    _prog(88, "Filtrando offset DC y aplicando fades…")
    result = _dc_blocker(result)

    actual_fade_in = min(fade_in, 1.0)
    actual_fade_out = min(fade_out, 1.0)
    result[0] = _apply_fades(result[0], SR_OUT, actual_fade_in, actual_fade_out)
    result[1] = _apply_fades(result[1], SR_OUT, actual_fade_in, actual_fade_out)

    # ── paso 4: Inserción de firma de voz / Voice Drop (v2.0) ──────────────────
    voice_drop = cfg.get("voice_drop_path")
    voice_enabled = bool(cfg.get("voice_drop_enabled", True if voice_drop else False))
    if voice_enabled and voice_drop and Path(voice_drop).exists():
        _prog(93, "Incrustando firma de voz / Voice Drop con auto-ducking…")
        from src.engine.effects import inject_voice_drop
        pos = cfg.get("voice_drop_position", "predrop").lower()
        manual_t = float(cfg.get("voice_drop_time_sec", -1.0))
        if pos == "manual" and manual_t >= 0:
            insert_t = manual_t
        elif pos == "intro":
            insert_t = float(cfg.get("voice_drop_time_sec", 1.8))
            if insert_t < 0:
                insert_t = 1.8
        else:
            # Pre-Drop: posicionar 3.8s antes del drop principal
            first_drop = drop_times[0] if drop_times else 16.0
            insert_t = max(1.5, float(first_drop) - 3.8)
        v_db = float(cfg.get("voice_drop_volume_db", -1.5))
        result = inject_voice_drop(result, SR_OUT, voice_drop, insert_time_sec=insert_t, volume_db=v_db)

    # ── paso 5: Masterización de estudio LUFS y limitador ─────────────────────
    if cfg.get("studio_mastering", True):
        _prog(94, "Aplicando limitador y masterización de estudio LUFS…")
        from src.engine.effects import apply_studio_mastering
        target_lufs = float(cfg.get("target_lufs", -9.0))
        result = apply_studio_mastering(result, SR_OUT, target_lufs=target_lufs, ceiling_db=-0.3)
    else:
        peak = np.abs(result).max()
        if peak > 0:
            result = result * (0.891 / peak)          # -1 dBFS (0.891)
        result = _soft_limiter(result, ceiling_db=-0.5)

    _prog(95, "Audio listo.")
    return result, SR_OUT, seed_used


# ── nombre de archivo ───────────────────────────────────────────────────────

def output_paths(
    source_path: str,
    out_dir: str,
    export_wav: bool,
    export_mp3: bool,
    export_flac: bool = False,
    export_aiff: bool = False,
    export_video: bool = False,
    custom_name: str | None = None,
) -> dict:
    base = custom_name.strip() if custom_name and custom_name.strip() \
           else f"PREVIA - {Path(source_path).stem}"
    paths = {}

    def _safe(directory: Path, filename: str) -> Path:
        p = directory / filename
        n = 1
        while p.exists():
            name, ext = filename.rsplit(".", 1)
            p = directory / f"{name} ({n}).{ext}"
            n += 1
        return p

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if export_wav:
        paths["wav"] = _safe(out, f"{base}.wav")
    if export_mp3:
        paths["mp3"] = _safe(out, f"{base}.mp3")
    if export_flac:
        paths["flac"] = _safe(out, f"{base}.flac")
    if export_aiff:
        paths["aiff"] = _safe(out, f"{base}.aiff")
    if export_video:
        paths["video"] = _safe(out, f"{base}.mp4")

    return paths


# ── gestión de carátula y metadatos ──────────────────────────────────────────

def prepare_cover_art(image_path: str | Path | None, output_size: int = 1000) -> Path | None:
    """
    Toma cualquier imagen (JPG, PNG, WebP) y genera un JPEG cuadrado RGB optimizado
    (máx 1000x1000 px) ideal para incrustación ID3/APIC y máxima compatibilidad
    con Pioneer CDJ, Rekordbox, Serato, Apple Music y exploradores del SO.
    """
    from src.config import get_cache_dir, get_assets_dir
    cache_dir = get_cache_dir()
    target_jpg = cache_dir / "cover_embedded.jpg"

    candidate: Path | None = None
    if image_path:
        p = Path(image_path).resolve()
        if p.exists() and p.is_file():
            candidate = p

    if not candidate:
        assets = get_assets_dir()
        for name in ["logo_emblem.png", "logo_emblem_red.png", "logo_banner.png"]:
            p = assets / name
            if p.exists() and p.is_file():
                candidate = p
                break

    if not candidate:
        return None

    # Intentar con QImage de PySide6 para escalado y centrado cuadrado en fondo dark
    try:
        from PySide6.QtGui import QImage, QPainter, QColor
        from PySide6.QtCore import Qt

        img = QImage(str(candidate))
        if not img.isNull():
            square = QImage(output_size, output_size, QImage.Format_RGB888)
            square.fill(QColor(14, 14, 17))  # Fondo dark #0e0e11

            scaled = img.scaled(output_size, output_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x_off = (output_size - scaled.width()) // 2
            y_off = (output_size - scaled.height()) // 2

            painter = QPainter(square)
            painter.drawImage(x_off, y_off, scaled)
            painter.end()

            square.save(str(target_jpg), "JPG", 90)
            return target_jpg
    except Exception:
        pass

    # Fallback FFmpeg si QImage no está disponible
    from src.config import get_ffmpeg_path
    import subprocess
    ffmpeg_bin = get_ffmpeg_path()
    if ffmpeg_bin:
        try:
            cmd = [
                ffmpeg_bin, "-y", "-i", str(candidate),
                "-vf", f"scale={output_size}:{output_size}:force_original_aspect_ratio=decrease,pad={output_size}:{output_size}:(ow-iw)/2:(oh-ih)/2:color=#0e0e11,format=yuvj420p",
                "-q:v", "2",
                str(target_jpg)
            ]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and target_jpg.exists():
                return target_jpg
        except Exception:
            pass

    return candidate


# ── exportación ─────────────────────────────────────────────────────────────

def export_files(
    audio: np.ndarray,
    sr: int,
    paths: dict,
    progress_cb: Callable[[int, str], None] | None = None,
    metadata: dict | None = None,
    cover_image_path: str | None = None,
) -> List[str]:
    """audio shape: (2, N) float32 stereo"""
    def _prog(pct: int, msg: str):
        if progress_cb:
            progress_cb(pct, msg)

    generated = []
    temp_wav_for_mp3: str | None = None

    meta = metadata or {}
    artist  = meta.get("artist") or "Radical Records"
    album   = meta.get("album") or "Radical Records Previews"
    label   = meta.get("label") or "Radical Records"
    genre   = meta.get("genre") or "Electronic"
    comment = meta.get("comment") or "AutoPrevias · Radical Records Studio"
    year    = str(meta.get("year") or "2026")
    bpm_val = meta.get("bpm")

    # Preparar carátula optimizada
    optimized_cover = prepare_cover_art(cover_image_path)

    if "wav" in paths:
        _prog(96, "Exportando WAV de estudio (24-bit PCM)…")
        wav_target = str(paths["wav"])
        sf.write(wav_target, audio.T, sr, subtype="PCM_24")
        generated.append(wav_target)

    if "mp3" in paths:
        _prog(98, "Exportando MP3 320kbps con firma y carátula…")
        mp3_target = str(paths["mp3"])
        mp3_done = False

        # Si ya tenemos el WAV exportado, usar FFmpeg con Xing headers y carátula ID3
        import subprocess
        import os
        from src.config import get_ffmpeg_path, get_cache_dir

        ffmpeg_bin = get_ffmpeg_path()

        src_wav = str(paths["wav"]) if "wav" in paths and Path(paths["wav"]).exists() else None
        if not src_wav:
            temp_wav_for_mp3 = str(get_cache_dir() / f"autoprevias_temp_{os.getpid()}.wav")
            sf.write(temp_wav_for_mp3, audio.T, sr, subtype="PCM_16")
            src_wav = temp_wav_for_mp3

        stem_name = Path(mp3_target).stem
        track_title = meta.get("title") or stem_name.replace("PREVIA - ", "")

        if ffmpeg_bin and src_wav:
            # 1. Intentar con carátula incrustada oficial o personalizada
            if optimized_cover and Path(optimized_cover).exists():
                try:
                    cmd_cover = [
                        ffmpeg_bin, "-y",
                        "-i", src_wav,
                        "-i", str(optimized_cover),
                        "-map", "0:a", "-map", "1:v",
                        "-codec:a", "libmp3lame", "-b:a", "320k",
                        "-codec:v", "copy",
                        "-disposition:v:0", "attached_pic",
                        "-write_xing", "1", "-id3v2_version", "3",
                        "-metadata", f"title={track_title}",
                        "-metadata", f"artist={artist}",
                        "-metadata", f"album={album}",
                        "-metadata", f"publisher={label}",
                        "-metadata", f"genre={genre}",
                        "-metadata", f"comment={comment}",
                        "-metadata", f"date={year}",
                    ]
                    if bpm_val:
                        try:
                            bpm_int = int(round(float(bpm_val)))
                            cmd_cover.extend(["-metadata", f"TBPM={bpm_int}"])
                        except Exception:
                            pass
                    key_val = meta.get("key") or meta.get("camelot")
                    if key_val:
                        cmd_cover.extend(["-metadata", f"TKEY={key_val}"])
                    cmd_cover.append(mp3_target)

                    res = subprocess.run(cmd_cover, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if res.returncode == 0 and Path(mp3_target).exists():
                        generated.append(mp3_target)
                        mp3_done = True
                except Exception:
                    mp3_done = False

            # 2. Si falló o no hay imagen, exportar con tags ID3 completos
            if not mp3_done:
                try:
                    cmd_nopic = [
                        ffmpeg_bin, "-y", "-i", src_wav,
                        "-codec:a", "libmp3lame", "-b:a", "320k",
                        "-write_xing", "1", "-id3v2_version", "3",
                        "-metadata", f"title={track_title}",
                        "-metadata", f"artist={artist}",
                        "-metadata", f"album={album}",
                        "-metadata", f"publisher={label}",
                        "-metadata", f"genre={genre}",
                        "-metadata", f"comment={comment}",
                        "-metadata", f"date={year}",
                    ]
                    if bpm_val:
                        try:
                            bpm_int = int(round(float(bpm_val)))
                            cmd_nopic.extend(["-metadata", f"TBPM={bpm_int}"])
                        except Exception:
                            pass
                    key_val = meta.get("key") or meta.get("camelot")
                    if key_val:
                        cmd_nopic.extend(["-metadata", f"TKEY={key_val}"])
                    cmd_nopic.append(mp3_target)

                    res = subprocess.run(cmd_nopic, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if res.returncode == 0 and Path(mp3_target).exists():
                        generated.append(mp3_target)
                        mp3_done = True
                except Exception:
                    mp3_done = False

        if not mp3_done:
            try:
                from pedalboard.io import AudioFile
                with AudioFile(mp3_target, "w", samplerate=sr,
                                num_channels=2, quality=320) as f:
                    f.write(audio)
                generated.append(mp3_target)
            except Exception as e:
                _prog(98, f"⚠ MP3 no disponible: {e}")

    if "flac" in paths:
        _prog(98, "Exportando FLAC Lossless…")
        flac_target = str(paths["flac"])
        sf.write(flac_target, audio.T, sr, format="FLAC")
        generated.append(flac_target)

    if "aiff" in paths:
        _prog(98, "Exportando AIFF 24-bit…")
        aiff_target = str(paths["aiff"])
        sf.write(aiff_target, audio.T, sr, format="AIFF", subtype="PCM_24")
        generated.append(aiff_target)

    if "video" in paths:
        _prog(99, "Generando vídeo de previa (TikTok / Reels / Shorts)…")
        try:
            from src.engine.video import render_social_video
            video_target = str(paths["video"])
            audio_for_vid = str(paths.get("wav") or temp_wav_for_mp3 or paths.get("mp3"))
            track_title = meta.get("title") or "Previa"
            render_social_video(
                audio_path=audio_for_vid,
                cover_image_path=cover_image_path,
                output_video_path=video_target,
                title=track_title,
                artist=artist,
                bpm=float(bpm_val or 128.0),
                key_str=str(meta.get("key") or "8A · Am"),
                aspect_ratio=str(meta.get("aspect_ratio") or "9:16"),
                palette_key=str(meta.get("video_palette") or "radical"),
                promo_text=str(meta.get("video_promo_text") or ""),
            )
            generated.append(video_target)
        except Exception as e:
            _prog(99, f"⚠ Vídeo social no generado: {e}")

    # Si se creó un WAV temporal y no había WAV de salida de usuario, lo registramos para el reproductor interno
    if temp_wav_for_mp3 and Path(temp_wav_for_mp3).exists():
        # Insertar al inicio para que el reproductor interno y la waveform utilicen el WAV sin latencia ni advertencias
        generated.insert(0, temp_wav_for_mp3)

    _prog(100, "¡Exportación completada!")
    return generated
