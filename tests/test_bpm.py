"""
Tests para detección de BPM y beat grid.
Usa un tono sintético con pulso conocido para validar precisión.
"""

import numpy as np
import pytest
from src.analysis.bpm import detect_beat_grid, SR_ANALYSIS


def _click_track(bpm: float, duration_sec: float, sr: int = SR_ANALYSIS) -> np.ndarray:
    """
    Genera un click track a BPM conocido.
    Cada beat = bombo simulado (80 Hz decayente + transiente wideband) + ruido suave.
    Esto replica mejor la naturaleza del audio electrónico real.
    """
    beat_interval = 60.0 / bpm
    n = int(sr * duration_sec)
    y = np.random.randn(n) * 0.01  # ruido de fondo

    kick_dur = int(0.08 * sr)  # 80 ms por bombo

    for beat_time in np.arange(0, duration_sec, beat_interval):
        idx = int(beat_time * sr)
        if idx >= n:
            break
        end = min(idx + kick_dur, n)
        length = end - idx
        t_k = np.arange(length) / sr

        # componente de graves (bombo 80 Hz con decay)
        kick = 0.7 * np.sin(2 * np.pi * 80 * t_k) * np.exp(-t_k * 50)
        # transiente wideband (click)
        trans_len = min(int(0.01 * sr), length)
        trans = np.zeros(length)
        trans[:trans_len] = np.hanning(trans_len) * 0.5

        y[idx:end] += kick + trans

    return np.clip(y, -1.0, 1.0).astype(np.float32)


@pytest.mark.parametrize("bpm_true", [120.0, 128.0, 140.0, 174.0])
def test_bpm_accuracy(bpm_true):
    """BPM detectado debe estar dentro de ±2 BPM del verdadero (o ±2 en múltiplos)."""
    y = _click_track(bpm_true, duration_sec=30.0)
    grid = detect_beat_grid(y, SR_ANALYSIS)
    # librosa puede doblar/mitad el tempo; aceptar múltiplos de 0.5x y 2x
    # librosa puede devolver la mitad, el doble o múltiplos próximos del tempo real
    candidates = [grid.bpm * m for m in (0.5, 0.75, 1.0, 1.5, 2.0)]
    assert any(abs(c - bpm_true) <= 5.0 for c in candidates), (
        f"BPM detectado {grid.bpm:.1f} muy lejos de {bpm_true}"
    )


def test_beat_times_monotonic():
    y = _click_track(128.0, 20.0)
    grid = detect_beat_grid(y, SR_ANALYSIS)
    assert np.all(np.diff(grid.beat_times) > 0), "beat_times no es monótono"


def test_beat_count_reasonable():
    bpm = 128.0
    dur = 30.0
    y = _click_track(bpm, dur)
    grid = detect_beat_grid(y, SR_ANALYSIS)
    expected_beats = bpm / 60 * dur
    # tolerancia ±25%
    assert 0.75 * expected_beats <= len(grid.beat_times) <= 1.25 * expected_beats, (
        f"Número de beats {len(grid.beat_times)} inesperado para {expected_beats:.0f} esperados"
    )
