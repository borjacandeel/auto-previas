"""
AutoPrevias — key.py
Detección de Tonalidad Musical y Código Camelot (Harmonic Key Detection).
Implementa el algoritmo Krumhansl-Schmuckler sobre perfiles de cromagrama (Chroma CENS / CQT)
con correlación de Pearson y mapeo directo a la rueda Camelot para DJs (Rekordbox, Traktor, Serato).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import librosa

# Perfiles tonales de Krumhansl-Schmuckler (pesos de las 12 notas de la escala)
# C, C#, D, D#, E, F, F#, G, G#, A, A#, B
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88], dtype=np.float32)
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17], dtype=np.float32)

_PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Mapeo a Rueda Camelot:
# Major -> "B", Minor -> "A"
# C major: 8B, A minor: 8A
_CAMELOT_MAJOR = {
    "C": "8B", "Db": "3B", "C#": "3B", "D": "10B", "Eb": "5B", "D#": "5B",
    "E": "12B", "F": "7B", "F#": "2B", "Gb": "2B", "G": "9B", "Ab": "4B",
    "G#": "4B", "A": "11B", "Bb": "6B", "A#": "6B", "B": "1B",
}

_CAMELOT_MINOR = {
    "C": "5A", "Db": "12A", "C#": "12A", "D": "7A", "Eb": "2A", "D#": "2A",
    "E": "9A", "F": "4A", "F#": "11A", "Gb": "11A", "G": "6A", "Ab": "1A",
    "G#": "1A", "A": "8A", "Bb": "3A", "A#": "3A", "B": "10A",
}


@dataclass
class KeyResult:
    root: str           # ej. "A", "F#", "C"
    mode: str           # "minor" o "major"
    notation: str       # ej. "Am", "F#m", "C"
    camelot: str        # ej. "8A", "11A", "8B"
    confidence: float   # 0.0 a 1.0


def detect_musical_key(y: np.ndarray, sr: int) -> KeyResult:
    """
    Detecta la tonalidad armónica de una señal de audio (mono o estéreo).
    Retorna el resultado con clave clásica, escala, código Camelot y confianza.
    """
    if y.ndim > 1:
        y = np.mean(y, axis=0)

    # Si el audio es muy largo, analizar una muestra representativa (hasta 90s centrales)
    duration_s = len(y) / sr
    if duration_s > 90.0:
        start_samp = int((duration_s * 0.2) * sr)
        end_samp = int(min(duration_s * 0.8, start_samp + 90.0) * sr)
        y_proc = y[start_samp:end_samp]
    else:
        y_proc = y

    # Extraer vector cromático medio (12 clases de tono promediadas en tiempo)
    try:
        chroma = librosa.feature.chroma_cens(y=y_proc, sr=sr, n_chroma=12)
        chroma_mean = np.mean(chroma, axis=1)
    except Exception:
        chroma = librosa.feature.chroma_stft(y=y_proc, sr=sr, n_chroma=12)
        chroma_mean = np.mean(chroma, axis=1)

    norm = np.linalg.norm(chroma_mean)
    if norm > 1e-7:
        chroma_mean = chroma_mean / norm
    else:
        return KeyResult(root="C", mode="major", notation="C", camelot="8B", confidence=0.0)

    best_corr = -2.0
    best_root = "C"
    best_mode = "major"
    all_corrs = []

    # Correlacionar con cada una de las 12 rotaciones de Major y Minor
    for i, root_name in enumerate(_PITCH_NAMES):
        maj_rot = np.roll(_MAJOR_PROFILE, i)
        min_rot = np.roll(_MINOR_PROFILE, i)

        maj_rot_norm = maj_rot / np.linalg.norm(maj_rot)
        min_rot_norm = min_rot / np.linalg.norm(min_rot)

        corr_maj = float(np.corrcoef(chroma_mean, maj_rot_norm)[0, 1])
        corr_min = float(np.corrcoef(chroma_mean, min_rot_norm)[0, 1])

        all_corrs.extend([corr_maj, corr_min])

        if corr_maj > best_corr:
            best_corr = corr_maj
            best_root = root_name
            best_mode = "major"

        if corr_min > best_corr:
            best_corr = corr_min
            best_root = root_name
            best_mode = "minor"

    # Confianza normalizada entre el mejor y el promedio
    mean_corr = float(np.mean(all_corrs))
    std_corr = float(np.std(all_corrs)) + 1e-6
    confidence = float(np.clip((best_corr - mean_corr) / (2.5 * std_corr), 0.1, 0.99))

    notation = f"{best_root}{'m' if best_mode == 'minor' else ''}"
    camelot = _CAMELOT_MINOR.get(best_root, "8A") if best_mode == "minor" else _CAMELOT_MAJOR.get(best_root, "8B")

    return KeyResult(
        root=best_root,
        mode=best_mode,
        notation=notation,
        camelot=camelot,
        confidence=confidence,
    )
