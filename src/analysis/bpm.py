"""
Detección de BPM y beat grid de alta precisión.

Estrategia:
  1. Tres canales de onset: completo, percusivo, kick (graves 50-200 Hz).
  2. Tempograma autocorrelación con hop pequeño (HOP_BPM=128) para
     resolución sub-frame (~0.1 BPM de precisión a 165 BPM).
  3. Promedio temporal del tempograma + suavizado gaussiano.
  4. Interpolación parabólica en espacio de lag para precisión sub-bin.
  5. Rango forzado 100-200 BPM (música de DJ).
  6. Refinamiento final con mediana de intervalos entre beats.
"""

from dataclasses import dataclass

import numpy as np
import librosa
from src.compat import apply_librosa_patches
apply_librosa_patches()
import scipy.signal
from scipy.ndimage import gaussian_filter1d


@dataclass
class BeatGrid:
    bpm: float
    beat_times: np.ndarray   # tiempos en segundos
    beat_frames: np.ndarray  # índices de frame a SR_ANALYSIS / HOP_LENGTH
    sr: int
    hop_length: int


SR_ANALYSIS = 22050
HOP_LENGTH  = 512    # hop general para estructura y beat tracking
HOP_BPM     = 128    # hop fino solo para estimar BPM

# Rango de BPM esperado en música de DJ (120 = house/techno · 210 = hardstyle/uptempo)
BPM_MIN = 120
BPM_MAX = 210


def _onset_channels(y: np.ndarray, sr: int, hop: int):
    """Devuelve (onset_full, onset_perc, onset_kick, kick_snr, full_snr)."""
    onset_full = librosa.onset.onset_strength(
        y=y, sr=sr, hop_length=hop, aggregate=np.median
    )
    _, y_perc = librosa.effects.hpss(y, margin=3.0)
    onset_perc = librosa.onset.onset_strength(
        y=y_perc, sr=sr, hop_length=hop, aggregate=np.median
    )
    sos = scipy.signal.butter(4, [50, 200], btype="bandpass", fs=sr, output="sos")
    y_kick = scipy.signal.sosfilt(sos, y)
    onset_kick = librosa.onset.onset_strength(
        y=y_kick, sr=sr, hop_length=hop, aggregate=np.median
    )
    kick_snr = np.std(onset_kick) / (np.mean(onset_kick) + 1e-9)
    full_snr  = np.std(onset_full) / (np.mean(onset_full) + 1e-9)
    return onset_full, onset_perc, onset_kick, kick_snr, full_snr


def _blend_onsets(onset_full, onset_perc, onset_kick, kick_snr, full_snr):
    """Mezcla ponderada según presencia de kicks."""
    has_kicks = kick_snr > 0.3 and kick_snr > full_snr * 0.5
    if has_kicks:
        w = (0.50, 0.30, 0.20)  # kick, perc, full
    else:
        w = (0.10, 0.60, 0.30)
    def _n(x):
        m = x.max()
        return x / m if m > 1e-9 else x
    return w[0] * _n(onset_kick) + w[1] * _n(onset_perc) + w[2] * _n(onset_full)


def _bpm_from_tempogram(onset_env: np.ndarray, sr: int, hop: int) -> float:
    """
    BPM preciso via tempograma promediado + interpolación parabólica en lag.

    Resolución aproximada con hop=128, sr=22050:
      lag 62  → 167.5 BPM
      lag 63  → 164.9 BPM   (cerca de 165.0)
      lag 64  → 162.4 BPM
    La interpolación parabólica da <0.1 BPM de error.
    """
    win_length = 512
    tg = librosa.feature.tempogram(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop,
        win_length=win_length,
    )
    global_tg = tg.mean(axis=1)           # (win_length,) — promedio temporal
    tempo_freqs = librosa.tempo_frequencies(len(global_tg), sr=sr, hop_length=hop)

    # Forzar rango DJ
    mask = (tempo_freqs >= BPM_MIN) & (tempo_freqs <= BPM_MAX)
    if not mask.any():
        mask = (tempo_freqs >= 60) & (tempo_freqs <= 220)

    tg_dj = global_tg[mask]
    tf_dj = tempo_freqs[mask]

    tg_smooth = gaussian_filter1d(tg_dj.astype(np.float64), sigma=1.5)
    peak = int(np.argmax(tg_smooth))

    # Interpolación parabólica en espacio BPM (tf está en BPM, no en lag)
    if 0 < peak < len(tg_smooth) - 1:
        y0, y1, y2 = tg_smooth[peak - 1], tg_smooth[peak], tg_smooth[peak + 1]
        denom = 2 * (2 * y1 - y0 - y2)
        if abs(denom) > 1e-12:
            delta = (y2 - y0) / denom          # desplazamiento fraccional [-0.5, 0.5]
            # Los tf están invertidos (decrece) → negamos delta
            bpm = float(tf_dj[peak]) - delta * abs(float(tf_dj[peak]) - float(tf_dj[peak - 1]))
            return bpm

    return float(tf_dj[peak])


def _refine_bpm_grid(
    beat_times: np.ndarray,
    bpm_initial: float,
    search_range: float = 5.0,
    step: float = 0.5,
) -> float:
    """
    Búsqueda fina de BPM por scoring de grid.

    Para cada candidato BPM en [bpm_initial ± search_range] con paso `step`:
      - Calcula el período esperado T = 60/bpm
      - Computa los residuos de beat_times módulo T (fase de cada beat respecto al grid)
      - Puntua por 1 - std(residuos_norm): mayor puntaje = beats más regulares a ese tempo

    Devuelve el BPM candidato con mayor puntaje.
    Funciona bien para corregir errores de ±3-4 BPM como 155→52 o 165→161.5.
    """
    if len(beat_times) < 8:
        return bpm_initial

    candidates = np.arange(
        max(BPM_MIN, bpm_initial - search_range),
        min(BPM_MAX, bpm_initial + search_range + step * 0.5),
        step,
    )
    if len(candidates) == 0:
        return bpm_initial

    best_bpm   = bpm_initial
    best_score = -1.0

    # Usar solo beats centrales (descarte 10% inicio/fin para evitar outliers)
    n = len(beat_times)
    trim = max(1, n // 10)
    bt = beat_times[trim: n - trim]
    if len(bt) < 4:
        bt = beat_times

    for cand in candidates:
        T = 60.0 / cand
        # Fase de cada beat respecto al grid del candidato (0..1)
        phase = (bt % T) / T
        # Mapear fase a distancia al grid más cercano (0..0.5)
        dist = np.minimum(phase, 1.0 - phase)
        # Puntaje: menor dispersión de distancias = mejor fit
        score = 1.0 - float(np.std(dist))
        if score > best_score:
            best_score = score
            best_bpm   = float(cand)

    return best_bpm


def _estimate_bpm_robust(y: np.ndarray, sr: int) -> float:
    """
    Estimación de BPM robusta multi-canal con alta precisión.
    Devuelve el BPM en el rango 100-200 con resolución ~0.1 BPM.
    """
    onset_full, onset_perc, onset_kick, kick_snr, full_snr = _onset_channels(y, sr, HOP_BPM)
    combined = _blend_onsets(onset_full, onset_perc, onset_kick, kick_snr, full_snr)

    bpm = _bpm_from_tempogram(combined, sr, HOP_BPM)

    # Sanity check: si el BPM es mitad del rango, intentar doblar
    if bpm < BPM_MIN * 0.95 and bpm * 2 <= BPM_MAX:
        bpm *= 2
    # Si es el doble, dividir
    if bpm > BPM_MAX * 1.05 and bpm / 2 >= BPM_MIN:
        bpm /= 2

    return float(bpm)


def detect_beat_grid(y: np.ndarray, sr: int) -> BeatGrid:
    """Analiza audio mono float32 → BPM + beat grid alineado a beats."""
    if len(y) < 2048:
        raise ValueError(
            f"El archivo de audio contiene solo {len(y)} muestras, insuficiente para detectar BPM."
        )

    if sr != SR_ANALYSIS:
        y = librosa.resample(y, orig_sr=sr, target_sr=SR_ANALYSIS)
        sr = SR_ANALYSIS

    bpm_robust = _estimate_bpm_robust(y, sr)

    # Beat tracking con el BPM robusto como ancla
    onset_env = librosa.onset.onset_strength(
        y=y, sr=sr, hop_length=HOP_LENGTH, aggregate=np.median
    )
    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=HOP_LENGTH,
        bpm=bpm_robust,
        trim=False,
        tightness=85,           # menos rígido que 100 → mejor en cambios de energía
    )
    bpm_tracker = float(np.atleast_1d(tempo)[0])

    # Si el tracker difiere >3 BPM del robusto, usar el robusto
    if abs(bpm_tracker - bpm_robust) > 3.0:
        bpm = bpm_robust
        _, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sr,
            hop_length=HOP_LENGTH,
            bpm=bpm_robust,
            trim=False,
            tightness=85,
        )
    else:
        bpm = bpm_tracker

    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=HOP_LENGTH)

    # ── Refinamiento 1: mediana de intervalos entre beats reales ─────────────
    if len(beat_times) > 8:
        intervals = np.diff(beat_times)
        # Recorte 15-85 percentil para eliminar outliers de inicio/fin
        p15, p85 = np.percentile(intervals, [15, 85])
        clean = intervals[(intervals >= p15) & (intervals <= p85)]
        if len(clean) > 4:
            bpm_from_beats = 60.0 / float(np.median(clean))
            bpm_rounded    = round(bpm_from_beats * 2) / 2
            if abs(bpm_rounded - bpm) <= 5.0:
                bpm = bpm_rounded

    # ── Refinamiento 2: grid scoring fino ±5 BPM en pasos de 0.5 ─────────────
    # Corrige casos como 155→52 o 165→161.5 donde el tempograma
    # cae en un mínimo local cercano al BPM real.
    bpm_grid = _refine_bpm_grid(beat_times, bpm, search_range=5.0, step=0.5)
    # Solo aceptar si el candidato ganador difiere del actual (evita ruido)
    if abs(bpm_grid - bpm) >= 0.5:
        # Re-verificar con el candidato: pedir beat_track anclado a bpm_grid
        _, bf2 = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sr,
            hop_length=HOP_LENGTH,
            bpm=bpm_grid,
            trim=False,
            tightness=100,
        )
        bt2 = librosa.frames_to_time(bf2, sr=sr, hop_length=HOP_LENGTH)
        # Comparar consistencia: menor std de intervalos gana
        def _interval_std(bt):
            if len(bt) < 4:
                return float("inf")
            ivs = np.diff(bt)
            p15, p85 = np.percentile(ivs, [15, 85])
            cl = ivs[(ivs >= p15) & (ivs <= p85)]
            return float(np.std(cl)) if len(cl) > 2 else float("inf")

        if _interval_std(bt2) < _interval_std(beat_times):
            bpm        = bpm_grid
            beat_times = bt2
            beat_frames = bf2

    # Redondeo final al entero más cercano si está a menos de 0.4 BPM
    bpm_int = round(bpm)
    if abs(bpm_int - bpm) <= 0.4 and BPM_MIN <= bpm_int <= BPM_MAX:
        bpm = float(bpm_int)

    return BeatGrid(
        bpm=bpm,
        beat_times=beat_times,
        beat_frames=beat_frames,
        sr=sr,
        hop_length=HOP_LENGTH,
    )


def nearest_beat(time_sec: float, beat_grid: BeatGrid) -> float:
    idx = int(np.argmin(np.abs(beat_grid.beat_times - time_sec)))
    return float(beat_grid.beat_times[idx])


def beat_index_at(time_sec: float, beat_grid: BeatGrid) -> int:
    return int(np.argmin(np.abs(beat_grid.beat_times - time_sec)))


def snap_to_phrase(beat_index: int, phrase_len: int = 16) -> int:
    return int(round(beat_index / phrase_len) * phrase_len)
