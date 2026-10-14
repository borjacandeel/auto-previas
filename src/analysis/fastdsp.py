"""
AutoPrevias — fastdsp.py
Aceleración del análisis SIN cambiar ningún resultado (las salidas son idénticas a las de librosa/scipy):

  · pmap(): ejecuta cálculos independientes a la vez (hilos; NumPy/SciPy sueltan el GIL en lo pesado).
  · parallel_median_filter(): el filtro de mediana de HPSS se reparte por filas/columnas independientes.
  · hpss_cached(): separación armónico/percusiva que comparte la STFT y los filtros de mediana entre el
    análisis del BPM (margin=3) y el de la estructura (margin=1), que antes se calculaban dos veces.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Sequence

import numpy as np
import librosa
from scipy.ndimage import median_filter

from src import perf


def pmap(fns: Sequence[Callable], workers: int | None = None) -> list:
    """Ejecuta los cálculos `fns` (sin argumentos) y devuelve sus resultados en el MISMO orden."""
    fns = list(fns)
    n = perf.threads("analysis") if workers is None else int(workers)
    if n <= 1 or len(fns) <= 1:
        return [f() for f in fns]
    with ThreadPoolExecutor(max_workers=min(n, len(fns))) as ex:
        futs = [ex.submit(f) for f in fns]
        return [f.result() for f in futs]


def parallel_median_filter(S: np.ndarray, size: tuple, workers: int | None = None) -> np.ndarray:
    """Igual que scipy.ndimage.median_filter(S, size=size, mode='reflect') pero repartido en hilos.
    Solo se trocea a lo largo de un eje con tamaño 1 (filas o columnas independientes) → resultado idéntico."""
    n = perf.threads("analysis") if workers is None else int(workers)
    if n <= 1 or S.ndim != 2 or sum(1 for s in size if s == 1) != 1 or min(S.shape) < 2 * n:
        return median_filter(S, size=size, mode="reflect")
    axis = 0 if size[0] == 1 else 1                      # eje a trocear = el que NO se filtra
    out = np.empty_like(S)
    bounds = np.linspace(0, S.shape[axis], n + 1, dtype=int)

    def work(a, b):
        if axis == 0:
            out[a:b] = median_filter(S[a:b], size=size, mode="reflect")
        else:
            out[:, a:b] = median_filter(S[:, a:b], size=size, mode="reflect")

    with ThreadPoolExecutor(max_workers=n) as ex:
        for f in [ex.submit(work, int(a), int(b)) for a, b in zip(bounds[:-1], bounds[1:]) if b > a]:
            f.result()
    return out


_LOCK = threading.Lock()
_CACHE: dict = {"key": None}


def _fingerprint(y: np.ndarray) -> tuple:
    return (len(y), y.dtype.str, float(np.sum(y[::1009], dtype=np.float64)), float(np.sum(np.abs(y[::2003]), dtype=np.float64)))


def clear_hpss_cache() -> None:
    with _LOCK:
        _CACHE.clear()
        _CACHE["key"] = None


def hpss_cached(y: np.ndarray, margin: float = 1.0, kernel_size: int = 31, power: float = 2.0, which: str = "both"):
    """Equivale a librosa.effects.hpss(y, margin=margin) con los parámetros por defecto del resto.
    La STFT, la magnitud/fase y los dos filtros de mediana (lo más caro) se calculan una vez por señal.
    `which`: «both» | «harm» | «perc» — el componente no pedido se devuelve como None (se ahorra su máscara y su ISTFT)."""
    key = _fingerprint(y)
    with _LOCK:
        if _CACHE.get("key") != key:
            D = librosa.stft(y, n_fft=2048, hop_length=None, win_length=None, window="hann", center=True, pad_mode="constant")
            S, phase = librosa.magphase(D)
            del D
            harm_shape = (1, int(kernel_size))
            perc_shape = (int(kernel_size), 1)
            _CACHE.clear()
            _CACHE.update(key=key, S=S, phase=phase,
                          harm=parallel_median_filter(S, harm_shape), perc=parallel_median_filter(S, perc_shape))
        S, phase, harm, perc = _CACHE["S"], _CACHE["phase"], _CACHE["harm"], _CACHE["perc"]
    split_zeros = float(margin) == 1.0
    n = len(y)

    def comp(num, den):
        mask = librosa.util.softmask(num, den * margin, power=power, split_zeros=split_zeros)
        return librosa.istft((S * mask) * phase, dtype=y.dtype, n_fft=2048, hop_length=None, win_length=None, center=True, length=n)

    y_harm = comp(harm, perc) if which in ("both", "harm") else None
    y_perc = comp(perc, harm) if which in ("both", "perc") else None
    return y_harm, y_perc
