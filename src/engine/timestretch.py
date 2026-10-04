"""
Cambio de velocidad + pitch juntos (sin keylock, como vinilo).

rate > 1.0  →  más rápido + pitch más alto
rate < 1.0  →  más lento  + pitch más bajo

Usa scipy.signal.resample (FFT-based), que es ~10× más rápido que el
phase vocoder de librosa y preserva la coherencia de fase naturalmente.
"""

import numpy as np
import scipy.signal


def speed_change(y: np.ndarray, rate: float) -> np.ndarray:
    """
    Cambia velocidad y pitch a la vez (estilo vinilo).
    rate=1.15 → 15 % más rápido, 15 % más agudo, 15 % más corto.
    """
    if abs(rate - 1.0) < 0.001:
        return y
    new_len = max(1, round(len(y) / rate))
    return scipy.signal.resample(y, new_len).astype(y.dtype, copy=False)


def crossfade(a: np.ndarray, b: np.ndarray, sr: int,
              duration_ms: float = 30.0) -> np.ndarray:
    n = int(sr * duration_ms / 1000)
    n = min(n, len(a), len(b))
    if n < 2:
        return np.concatenate([a, b])
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)
    overlap = a[-n:] * (1.0 - t) + b[:n] * t
    return np.concatenate([a[:-n], overlap, b[n:]])
