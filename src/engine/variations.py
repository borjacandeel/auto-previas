"""
Envolvente de pitch progresivo anti-retoque.

En lugar de cortes abruptos entre tramos, genera una curva de velocidad
continua con 5-8 deslizamientos suaves. Cada deslizamiento va de un pitch
a otro en ~10 segundos usando interpolación coseno (ease in/out).
El resultado: el pitch sube y baja imperceptiblemente pero de forma orgánica,
imposible de corregir a grid con time-warp.

Uso:
    rate_env, seed = make_rate_envelope(n_samples, sr, min_rate, max_rate, seed)
    # rate_env es un array float32 shape (n_samples,)
    # aplicar con apply_rate_envelope(audio, rate_env)
"""

import random
import math
from typing import Optional, Tuple

import numpy as np
import scipy.signal


def make_rate_envelope(
    n_samples: int,
    sr: int,
    min_rate: float = 1.0,
    max_rate: float = 1.15,
    seed: Optional[int] = None,
    glide_duration_s: float = 10.0,  # duración de cada deslizamiento
    n_events_range: Tuple[int, int] = (7, 10),
) -> Tuple[np.ndarray, int]:
    """
    Genera envolvente de velocidad con deslizamientos suaves.

    Devuelve:
        rate_env: array float32 shape (n_samples,) con el factor de velocidad
                  para cada muestra del audio ensamblado
        seed_used: semilla usada (para reproducibilidad)
    """
    if seed is None:
        seed = random.randint(0, 99999)
    rng = random.Random(seed)

    duration = n_samples / sr
    n_events = rng.randint(*n_events_range)

    # Generar N puntos de control: (tiempo, rate_objetivo)
    # El rate base arranca en un valor aleatorio del rango medio
    base_rate = rng.uniform(min_rate, (min_rate + max_rate) / 2)
    control = [(0.0, base_rate)]

    # Distribuir eventos con jitter ±10 % del spacing
    spacing = duration / (n_events + 1)
    for i in range(n_events):
        t = spacing * (i + 1) + rng.uniform(-spacing * 0.2, spacing * 0.2)
        t = max(glide_duration_s, min(duration - glide_duration_s, t))
        # alternar entre high y low para efecto de vaivén
        if i % 2 == 0:
            rate = rng.uniform((min_rate + max_rate) / 2, max_rate)
        else:
            rate = rng.uniform(min_rate, (min_rate + max_rate) / 2)
        control.append((t, rate))

    # cerrar con el rate del último evento
    control.append((duration, control[-1][1]))
    control.sort(key=lambda x: x[0])

    # Construir la envolvente muestra a muestra con rampas coseno
    t_arr = np.linspace(0.0, duration, n_samples, endpoint=False)
    rate_arr = np.ones(n_samples, dtype=np.float32)

    for j in range(len(control) - 1):
        t0, r0 = control[j]
        t1, r1 = control[j + 1]

        # La transición ocupa glide_duration_s en el centro del intervalo
        # (si el intervalo es más corto, ocupa todo el intervalo)
        span     = t1 - t0
        glide    = min(glide_duration_s, span)
        t_glide0 = t0 + (span - glide) / 2
        t_glide1 = t_glide0 + glide

        mask_flat0 = (t_arr >= t0)     & (t_arr < t_glide0)
        mask_ramp  = (t_arr >= t_glide0) & (t_arr < t_glide1)
        mask_flat1 = (t_arr >= t_glide1) & (t_arr < t1)

        rate_arr[mask_flat0] = r0
        if mask_ramp.any():
            phase = (t_arr[mask_ramp] - t_glide0) / glide   # 0..1
            rate_arr[mask_ramp] = r0 + (r1 - r0) * (1 - np.cos(phase * math.pi)) / 2
        rate_arr[mask_flat1] = r1

    return rate_arr, seed


def make_custom_rate_envelope(
    n_samples: int,
    sr: int,
    base_bpm: float,
    events: list[dict],
) -> tuple[np.ndarray, int]:
    """
    Genera una envolvente de velocidad basada en puntos de control manuales definidos por el usuario.
    Cada evento es un dict con:
      - 'time_sec': float (tiempo en segundos dentro de la previa)
      - 'bpm_delta': float (variación en BPM, ej. +5.0 o -3.0)
      - 'duration_sec': float (duración total del cambio)
      - 'transition_sec': float (duración de la rampa de aceleración/desaceleración)
      - 'style': 'surge' (subida y bajada) | 'ramp' (subida y mantener)
    """
    duration_sec = n_samples / max(sr, 1)
    t_arr = np.linspace(0, duration_sec, n_samples, endpoint=False)
    delta_bpm = np.zeros(n_samples, dtype=np.float32)

    for ev in events:
        t0 = float(ev.get("time_sec", 0.0))
        db = float(ev.get("bpm_delta", 5.0))
        dur = max(1.0, float(ev.get("duration_sec", 16.0)))
        tr = max(0.5, min(float(ev.get("transition_sec", 4.0)), dur / 2.0))
        style = ev.get("style", "surge")

        if style == "surge":
            t_rise = t0 + tr
            t_fall = t0 + dur - tr
            t_end = t0 + dur

            m_rise = (t_arr >= t0) & (t_arr < t_rise)
            if m_rise.any():
                phase = (t_arr[m_rise] - t0) / tr
                delta_bpm[m_rise] += db * (1.0 - np.cos(phase * math.pi)) / 2.0

            m_flat = (t_arr >= t_rise) & (t_arr < t_fall)
            if m_flat.any():
                delta_bpm[m_flat] += db

            m_fall = (t_arr >= t_fall) & (t_arr < t_end)
            if m_fall.any():
                phase = (t_arr[m_fall] - t_fall) / tr
                delta_bpm[m_fall] += db * (1.0 + np.cos(phase * math.pi)) / 2.0

        elif style == "ramp":
            t_rise = t0 + tr
            m_rise = (t_arr >= t0) & (t_arr < t_rise)
            if m_rise.any():
                phase = (t_arr[m_rise] - t0) / tr
                delta_bpm[m_rise] += db * (1.0 - np.cos(phase * math.pi)) / 2.0
            m_stay = (t_arr >= t_rise)
            if m_stay.any():
                delta_bpm[m_stay] += db

    current_bpm = np.clip(base_bpm + delta_bpm, 60.0, 300.0)
    rate_arr = np.clip(current_bpm / max(base_bpm, 1e-3), 0.7, 1.4).astype(np.float32)
    return rate_arr, 0


def compute_preview_tempo_curve(
    duration_sec: float,
    base_bpm: float,
    events: list[dict],
    n_points: int = 500,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calcula de forma rápida los vectores (tiempos, bpms) para graficar
    la curva de BPM en la interfaz de usuario en tiempo real.
    """
    t_arr = np.linspace(0, duration_sec, n_points)
    delta_bpm = np.zeros(n_points, dtype=np.float32)

    for ev in events:
        t0 = float(ev.get("time_sec", 0.0))
        db = float(ev.get("bpm_delta", 5.0))
        dur = max(1.0, float(ev.get("duration_sec", 16.0)))
        tr = max(0.5, min(float(ev.get("transition_sec", 4.0)), dur / 2.0))
        style = ev.get("style", "surge")

        if style == "surge":
            t_rise = t0 + tr
            t_fall = t0 + dur - tr
            t_end = t0 + dur

            m_rise = (t_arr >= t0) & (t_arr < t_rise)
            if m_rise.any():
                phase = (t_arr[m_rise] - t0) / tr
                delta_bpm[m_rise] += db * (1.0 - np.cos(phase * math.pi)) / 2.0

            m_flat = (t_arr >= t_rise) & (t_arr < t_fall)
            if m_flat.any():
                delta_bpm[m_flat] += db

            m_fall = (t_arr >= t_fall) & (t_arr < t_end)
            if m_fall.any():
                phase = (t_arr[m_fall] - t_fall) / tr
                delta_bpm[m_fall] += db * (1.0 + np.cos(phase * math.pi)) / 2.0

        elif style == "ramp":
            t_rise = t0 + tr
            m_rise = (t_arr >= t0) & (t_arr < t_rise)
            if m_rise.any():
                phase = (t_arr[m_rise] - t0) / tr
                delta_bpm[m_rise] += db * (1.0 - np.cos(phase * math.pi)) / 2.0
            m_stay = (t_arr >= t_rise)
            if m_stay.any():
                delta_bpm[m_stay] += db

    bpm_arr = np.clip(base_bpm + delta_bpm, 60.0, 300.0)
    return t_arr, bpm_arr


def apply_rate_envelope(
    audio: np.ndarray,
    rate_env: np.ndarray,
    chunk_samples: int = 8192,
) -> np.ndarray:
    """
    Aplica una envolvente de velocidad continua a audio stereo (2, N).

    Usa integración temporal continua muestra a muestra (varispeed continuo),
    eliminando cualquier artefacto de bloque, salto audible o discontinuidad
    de fase.

    Devuelve audio stereo (2, M) donde M ≈ sum(1 / rate).
    """
    n_src = audio.shape[1]
    if len(rate_env) < n_src:
        rate_full = np.pad(rate_env, (0, n_src - len(rate_env)), constant_values=1.0)
    else:
        rate_full = rate_env[:n_src]

    # Prevenir división por cero o velocidades negativas
    rate_clamped = np.clip(rate_full, 0.05, 3.0).astype(np.float64)

    # dt_out por cada muestra de entrada = 1.0 / rate
    dt_out = 1.0 / rate_clamped
    t_out = np.cumsum(dt_out)
    t_out -= t_out[0]
    total_out = int(np.round(t_out[-1]))

    if total_out <= 0:
        return audio

    # Mapeo continuo de muestra de salida -> posición fraccional de entrada
    m_grid = np.arange(total_out, dtype=np.float64)
    input_indices = np.arange(n_src, dtype=np.float64)
    frac_in = np.interp(m_grid, t_out, input_indices).astype(np.float32)

    # Interpolación continua de alta fidelidad para canal izquierdo y derecho
    out_L = np.interp(frac_in, input_indices, audio[0]).astype(np.float32)
    out_R = np.interp(frac_in, input_indices, audio[1]).astype(np.float32)

    return np.stack([out_L, out_R])

