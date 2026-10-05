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
    rate_hz: float = 0.4,
    depth_ms: float = 2.5,
    base_delay_ms: float = 1.5,
    feedback: float = 0.5,
    mix: float = 0.5,
) -> np.ndarray:
    """
    Aplica un efecto Flanger analógico estéreo con modulación LFO independiente por canal.
    audio: array (canales, muestras) float32 [-1, 1]
    """
    if audio.ndim == 1:
        audio = np.stack([audio, audio])

    channels, n_samples = audio.shape
    out = np.zeros_like(audio, dtype=np.float32)

    max_delay_samples = int((base_delay_ms + depth_ms) * 0.001 * sr) + 5
    buf_size = max_delay_samples + 2

    t = np.arange(n_samples) / sr

    for ch in range(channels):
        # Desfase de 90 grados entre canal izquierdo y derecho para amplitud estéreo
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

            # Interpolación lineal entre muestras
            delayed_sample = (1.0 - d_frac) * buffer[read_idx_0] + d_frac * buffer[read_idx_1]

            cur_sample = ch_in[i] + feedback * delayed_sample
            buffer[buf_idx] = cur_sample
            buf_idx = (buf_idx + 1) % buf_size

            ch_out[i] = (1.0 - mix) * ch_in[i] + mix * delayed_sample

        out[ch] = ch_out

    return np.clip(out, -1.0, 1.0).astype(np.float32)


def apply_filter_sweep(
    audio: np.ndarray,
    sr: int,
    start_freq: float = 250.0,
    end_freq: float = 3500.0,
    kind: str = "highpass",
) -> np.ndarray:
    """
    Aplica un barrido de filtro progresivo (útil para generar tensión en subidas).
    """
    if audio.ndim == 1:
        audio = np.stack([audio, audio])

    channels, n_samples = audio.shape
    if n_samples < 256:
        return audio

    num_blocks = 32
    block_len = n_samples // num_blocks
    out = np.zeros_like(audio, dtype=np.float32)

    freqs = np.geomspace(max(40.0, start_freq), min(sr * 0.45, end_freq), num_blocks)

    for b in range(num_blocks):
        i0 = b * block_len
        i1 = n_samples if b == num_blocks - 1 else (b + 1) * block_len
        block_audio = audio[:, i0:i1]

        cutoff = freqs[b]
        nyq = sr * 0.5
        norm_cutoff = np.clip(cutoff / nyq, 0.01, 0.95)

        try:
            sos = signal.butter(2, norm_cutoff, btype=kind, output="sos")
            for ch in range(channels):
                out[ch, i0:i1] = signal.sosfilt(sos, block_audio[ch])
        except Exception:
            out[:, i0:i1] = block_audio

    return np.clip(out, -1.0, 1.0).astype(np.float32)


def inject_voice_drop(
    base_audio: np.ndarray,
    sr: int,
    drop_file_path: str,
    insert_time_sec: float,
    volume_db: float = -1.5,
    ducking_db: float = -4.0,
) -> np.ndarray:
    """
    Superpone una firma de voz / jingle / audio tag sobre la previa en el segundo indicado.
    Aplica auto-ducking suave en la música de fondo durante el habla para máxima inteligibilidad.
    """
    from src.engine.audio_io import load_audio_file

    tag_audio, tag_sr = load_audio_file(drop_file_path, sr=sr, mono=False, dtype=np.float32)
    if tag_audio.ndim == 1:
        tag_audio = np.stack([tag_audio, tag_audio])

    # Escalar volumen del tag
    tag_gain = 10.0 ** (volume_db / 20.0)
    tag_audio = tag_audio * tag_gain

    out = np.copy(base_audio)
    channels = min(out.shape[0], tag_audio.shape[0])

    start_idx = max(0, int(insert_time_sec * sr))
    tag_len = tag_audio.shape[1]
    end_idx = min(out.shape[1], start_idx + tag_len)

    actual_len = end_idx - start_idx
    if actual_len <= 0:
        return out

    # Curva de ducking sobre la música de fondo
    duck_gain = 10.0 ** (ducking_db / 20.0)
    fade_len = min(int(0.08 * sr), actual_len // 4)
    envelope = np.ones(actual_len, dtype=np.float32) * duck_gain

    if fade_len > 0:
        fade_in = np.linspace(1.0, duck_gain, fade_len)
        fade_out = np.linspace(duck_gain, 1.0, fade_len)
        envelope[:fade_len] = fade_in
        envelope[-fade_len:] = fade_out

    for ch in range(channels):
        out[ch, start_idx:end_idx] = (
            out[ch, start_idx:end_idx] * envelope + tag_audio[ch, :actual_len]
        )

    # Limitar para evitar saturación
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
