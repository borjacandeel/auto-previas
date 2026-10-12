"""
AutoPrevias — effects.py
Efectos de Audio de Estudio, Procesamiento Acústico y Masterización.

Efectos incluidos:
- Flanger analógico de estudio (LFO sinusoidal, feedback de resonancia, dry/wet).
- Filter Sweep dinámico (barrido de filtro paso alto HPF -> paso bajo LPF para subidas y transiciones).
- Inserción de Audio Tag / Voice Drop ("Firma de voz" de DJ o sello discográfico con mezcla transparente).
- Masterizador / Normalizador LUFS comercial con limitador de picos transparente.
- Riser sintético de transición (sweep de ruido blanco filtrado para suavizar saltos).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from scipy import signal


def apply_flanger(
    audio: np.ndarray,
    sr: int,
    rate_hz: float = 0.65,
    depth_ms: float = 3.8,
    base_delay_ms: float = 1.0,
    feedback: float = 0.74,
    mix: float = 0.75,
    ramp_in_sec: float = 0.0,
    hard_stop: bool = False,
) -> np.ndarray:
    """
    Aplica un efecto Flanger analógico estéreo agresivo de estudio.
    - Modulación LFO sinusoidal en cuadratura (90 grados de desfase estéreo).
    - Feedback resonante elevado (0.74) para emular el barrido tipo turbina / jet-plane.
    - ramp_in_sec: rampa suave de entrada para evitar clicks al activarse en la subida.
    - hard_stop: corte en seco micro-faded (3ms) en el downbeat exacto del drop.
    """
    if audio.ndim == 1:
        audio = np.stack([audio, audio])

    channels, n_samples = audio.shape
    if n_samples < 16:
        return audio

    out = np.zeros_like(audio, dtype=np.float32)

    max_delay_samples = int((base_delay_ms + depth_ms) * 0.001 * sr) + 8
    buf_size = max_delay_samples + 4

    t = np.arange(n_samples, dtype=np.float32) / sr

    # Envolvente dinámica del nivel de mezcla Wet
    mix_env = np.full(n_samples, mix, dtype=np.float32)
    if ramp_in_sec > 0.0:
        n_ramp = min(int(ramp_in_sec * sr), n_samples)
        if n_ramp > 0:
            mix_env[:n_ramp] = (np.linspace(0.0, 1.0, n_ramp, dtype=np.float32) ** 1.5) * mix

    if hard_stop:
        # Micro-fade de 3ms al final para cortar en seco sin generar click digital
        n_micro = min(int(0.003 * sr), max(1, n_samples // 4))
        if n_micro > 0:
            mix_env[-n_micro:] *= np.linspace(1.0, 0.0, n_micro, dtype=np.float32)

    for ch in range(channels):
        # Desfase de 90 grados entre canal izquierdo y derecho para apertura estéreo máxima
        phase_offset = 0.0 if ch == 0 else (np.pi / 2)
        lfo = (np.sin(2 * np.pi * rate_hz * t + phase_offset) + 1.0) * 0.5
        delay_mod = (base_delay_ms + depth_ms * lfo) * 0.001 * sr

        buffer = np.zeros(buf_size, dtype=np.float32)
        buf_idx = 0
        ch_in = audio[ch]
        ch_out = np.zeros(n_samples, dtype=np.float32)

        for i in range(n_samples):
            d = delay_mod[i]
            d_int = int(d)
            d_frac = d - d_int

            read_idx_0 = (buf_idx - d_int) % buf_size
            read_idx_1 = (buf_idx - d_int - 1) % buf_size

            delayed_sample = (1.0 - d_frac) * buffer[read_idx_0] + d_frac * buffer[read_idx_1]

            # Inyección de feedback con saturación suave para evitar auto-oscilación descontrolada
            cur_sample = ch_in[i] + feedback * np.tanh(delayed_sample)
            buffer[buf_idx] = cur_sample
            buf_idx = (buf_idx + 1) % buf_size

            m = mix_env[i]
            ch_out[i] = (1.0 - m) * ch_in[i] + m * delayed_sample

        out[ch] = ch_out

    return np.clip(out, -1.0, 1.0).astype(np.float32)


def apply_filter_sweep(
    audio: np.ndarray,
    sr: int,
    start_freq: float = 60.0,
    end_freq: float = 2800.0,
    kind: str = "highpass",
    hard_stop: bool = False,
) -> np.ndarray:
    """
    Aplica un barrido de filtro progresivo para acumular tensión en la subida antes del drop.
    - High-Pass Filter (HPF): arranca en 60Hz (dejando pasar todo) y barre hasta 2800Hz,
      eliminando el bombo y graves gradualmente.
    - hard_stop: al llegar al drop, corta en seco en 3ms devolviendo el 100% de pegada de graves.
    """
    if audio.ndim == 1:
        audio = np.stack([audio, audio])

    channels, n_samples = audio.shape
    if n_samples < 256:
        return audio

    num_blocks = 32
    block_len = n_samples // num_blocks
    out = np.zeros_like(audio, dtype=np.float32)

    freqs = np.geomspace(max(30.0, start_freq), min(sr * 0.45, end_freq), num_blocks)

    for b in range(num_blocks):
        i0 = b * block_len
        i1 = n_samples if b == num_blocks - 1 else (b + 1) * block_len
        block_audio = audio[:, i0:i1]

        cutoff = freqs[b]
        nyq = sr * 0.5
        norm_cutoff = np.clip(cutoff / nyq, 0.005, 0.95)

        try:
            sos = signal.butter(2, norm_cutoff, btype=kind, output="sos")
            for ch in range(channels):
                out[ch, i0:i1] = signal.sosfilt(sos, block_audio[ch])
        except Exception:
            out[:, i0:i1] = block_audio

    if hard_stop:
        # Micro-fade al final para volver instantáneamente a la pista limpia y sin filtrar
        n_micro = min(int(0.003 * sr), max(1, n_samples // 4))
        if n_micro > 0:
            for ch in range(channels):
                fade_dry = np.linspace(0.0, 1.0, n_micro, dtype=np.float32)
                fade_wet = 1.0 - fade_dry
                out[ch, -n_micro:] = out[ch, -n_micro:] * fade_wet + audio[ch, -n_micro:] * fade_dry

    return np.clip(out, -1.0, 1.0).astype(np.float32)


def apply_predrop_effects(
    block_audio: np.ndarray,
    sr: int,
    block_start_sec: float,
    block_end_sec: float,
    drop_timestamps: list[float],
    cfg: dict,
    pre_drop_sec: float = 5.0,
) -> np.ndarray:
    """
    Aplica automáticamente los efectos seleccionados (Flanger agresivo, Filter Sweep)
    EXCLUSIVAMENTE durante los 5 segundos previos a cada Drop ('subida').
    Al llegar exactamente al drop, el efecto se detiene en seco para que el bombo
    e impacto del drop exploten limpios, contundentes y al 100% de fuerza acústica.
    """
    if block_audio.ndim == 1:
        block_audio = np.stack([block_audio, block_audio])

    has_flanger = bool(cfg.get("fx_flanger"))
    has_filter  = bool(cfg.get("fx_filter_sweep"))

    if not has_flanger and not has_filter:
        return block_audio

    out = block_audio.copy()
    n_samples = out.shape[1]

    for d_t in drop_timestamps:
        # El drop debe estar dentro de este bloque con al menos 0.5s de margen desde el inicio
        if block_start_sec + 0.5 < d_t <= block_end_sec + 0.05:
            drop_sample = min(n_samples, int((d_t - block_start_sec) * sr))
            bu_start_sample = max(0, int((d_t - pre_drop_sec - block_start_sec) * sr))

            window_len = drop_sample - bu_start_sample
            if window_len < int(0.5 * sr):
                continue

            chunk = out[:, bu_start_sample:drop_sample]
            ramp_in = min(0.8, window_len / (sr * 3.0))

            if has_filter:
                chunk = apply_filter_sweep(
                    chunk, sr,
                    start_freq=60.0,
                    end_freq=2800.0,
                    kind="highpass",
                    hard_stop=True,
                )

            if has_flanger:
                flanger_mix = float(cfg.get("flanger_mix", 0.75))
                chunk = apply_flanger(
                    chunk, sr,
                    rate_hz=0.65,
                    depth_ms=3.8,
                    base_delay_ms=1.0,
                    feedback=0.74,
                    mix=flanger_mix,
                    ramp_in_sec=ramp_in,
                    hard_stop=True,
                )

            out[:, bu_start_sample:drop_sample] = chunk

    return out


def _mix_tag(
    out: np.ndarray,
    sr: int,
    tag_audio: np.ndarray,
    insert_time_sec: float,
    ducking_db: float = -14.0,
    fade_ramp_sec: float = 1.0,
) -> None:
    """Mezcla (in situ) un tag ya cargado sobre `out` con ducking del master alrededor."""
    total = out.shape[1]
    channels = min(out.shape[0], tag_audio.shape[0])

    vd_start = max(0, int(insert_time_sec * sr))
    vd_end = min(total, vd_start + tag_audio.shape[1])
    vd_len = vd_end - vd_start
    if vd_len <= 0:
        return

    duck_gain = 10.0 ** (ducking_db / 20.0)   # ≈ 0.2 a -14 dB
    fade_samps = int(fade_ramp_sec * sr)

    duck_start = max(0, vd_start - fade_samps)
    duck_end = min(total, vd_end + fade_samps)

    env_len = duck_end - duck_start
    envelope = np.ones(env_len, dtype=np.float32)

    pre_len = vd_start - duck_start
    if pre_len > 0:
        envelope[:pre_len] = np.linspace(1.0, duck_gain, pre_len)

    vd_env_start = vd_start - duck_start
    vd_env_end = vd_end - duck_start
    envelope[vd_env_start:vd_env_end] = duck_gain

    post_len = duck_end - vd_end
    if post_len > 0:
        envelope[vd_env_end:vd_env_end + post_len] = np.linspace(duck_gain, 1.0, post_len)

    for ch in range(out.shape[0]):
        out[ch, duck_start:duck_end] *= envelope
    for ch in range(channels):
        out[ch, vd_start:vd_end] += tag_audio[ch, :vd_len]


def _load_tag(drop_file_path: str, sr: int, volume_db: float) -> np.ndarray:
    from src.engine.audio_io import load_audio_file

    tag_audio, _ = load_audio_file(drop_file_path, sr=sr, mono=False, dtype=np.float32)
    if tag_audio.ndim == 1:
        tag_audio = np.stack([tag_audio, tag_audio])
    return tag_audio * (10.0 ** (volume_db / 20.0))


def inject_voice_drop(
    base_audio: np.ndarray,
    sr: int,
    drop_file_path: str,
    insert_time_sec: float,
    volume_db: float = -1.5,
    ducking_db: float = -14.0,   # ~20 % del volumen original
    fade_ramp_sec: float = 1.0,  # 1 s de bajada antes y subida después
) -> np.ndarray:
    """
    Superpone una firma de voz / jingle sobre la previa en el punto indicado.
    Curva de ducking:
      · 1 s de rampa descendente hasta ~20 % antes de que empiece el voice drop
      · Durante el voice drop el master queda al 20 %
      · 1 s de rampa ascendente de vuelta al 100 % tras el voice drop
    """
    tag_audio = _load_tag(drop_file_path, sr, volume_db)
    out = np.copy(base_audio)
    _mix_tag(out, sr, tag_audio, insert_time_sec, ducking_db, fade_ramp_sec)
    return np.clip(out, -0.98, 0.98).astype(np.float32)


def promo_tag_times(
    total_sec: float,
    tag_len_sec: float,
    interval_sec: float = 20.0,
    jitter_sec: float = 3.0,
    first_sec: float = 8.0,
    seed: int = 0,
    end_guard_sec: float = 2.0,
) -> list:
    """
    Instantes (s) en que se repite el tag en el modo promo antifugas.
    Determinista para una misma `seed`. Los tags nunca se solapan ni se cortan
    contra el final de la previa.
    """
    import random

    rng = random.Random(int(seed))
    min_gap = tag_len_sec + 2.0           # hueco mínimo entre tags
    interval = max(float(interval_sec), min_gap)
    times: list = []
    t = max(0.0, float(first_sec))
    while t + tag_len_sec <= total_sec - end_guard_sec:
        times.append(round(t, 3))
        step = interval + rng.uniform(-jitter_sec, jitter_sec)
        t += max(step, min_gap)
    return times


def inject_repeating_tags(
    base_audio: np.ndarray,
    sr: int,
    tag_file_path: str,
    interval_sec: float = 20.0,
    jitter_sec: float = 3.0,
    first_sec: float = 8.0,
    volume_db: float = -3.0,
    seed: int = 0,
    ducking_db: float = -10.0,
) -> np.ndarray:
    """
    Modo promo antifugas: superpone el tag de voz/jingle repetidamente sobre toda
    la previa (con ducking suave), de modo que el audio sea inservible para
    reutilizarlo sin la firma.
    """
    tag_audio = _load_tag(tag_file_path, sr, volume_db)
    out = np.copy(base_audio)
    total_sec = out.shape[1] / float(sr)
    tag_len = tag_audio.shape[1] / float(sr)
    for t in promo_tag_times(total_sec, tag_len, interval_sec, jitter_sec, first_sec, seed):
        _mix_tag(out, sr, tag_audio, t, ducking_db=ducking_db, fade_ramp_sec=0.4)
    return np.clip(out, -0.98, 0.98).astype(np.float32)


def apply_studio_mastering(
    audio: np.ndarray,
    sr: int,
    target_lufs: float = -9.0,
    ceiling_db: float = -0.3,
) -> np.ndarray:
    """
    Normalizador y limitador de masterización de estudio.
    Calcula la sonoridad RMS ponderada y ajusta la ganancia para pegada comercial.
    """
    if audio.ndim == 1:
        audio = np.stack([audio, audio])

    rms = np.sqrt(np.mean(audio**2)) + 1e-9
    current_db = 20.0 * np.log10(rms)

    # Estimación de ganancia hacia target LUFS comercial
    gain_db = np.clip(target_lufs - current_db, -6.0, 8.0)
    linear_gain = 10.0 ** (gain_db / 20.0)

    amplified = audio * linear_gain

    # Limitador analógico suave (tanh soft-clipping)
    ceiling_linear = 10.0 ** (ceiling_db / 20.0)
    threshold = ceiling_linear * 0.85

    abs_a = np.abs(amplified)
    mask = abs_a > threshold

    out = np.copy(amplified)
    # Compresión suave sobre el umbral
    overshoot = abs_a[mask] - threshold
    headroom = ceiling_linear - threshold
    compressed = threshold + headroom * np.tanh(overshoot / max(1e-6, headroom))

    out[mask] = np.sign(amplified[mask]) * compressed
    return np.clip(out, -ceiling_linear, ceiling_linear).astype(np.float32)
