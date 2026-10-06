"""
Detectar los puntos exactos de corte en PREVIA.wav mediante:
1. Valles de volumen / silencio (fades de corte)
2. Cambios bruscos de novedad espectral (spectral novelty / flux)
3. Estructura de compases y frases (cada 16/32 beats)
"""

import numpy as np
import soundfile as sf
import librosa

prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"
y, sr = sf.read(prev_path)
if y.ndim > 1: y = y.mean(axis=1)

dur = len(y) / sr
print(f"PREVIA duración total: {dur:.2f} segundos")

# RMS con salto de 512 samples (~10ms)
hop = 256
rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop)[0]
t_rms = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)

# Detectar valles profundos en el RMS (donde el volumen baja a casi cero por un corte/fade)
# Umbral: rms < 0.1 del percentil 90
thresh = np.percentile(rms, 90) * 0.15
valleys = np.where(rms < thresh)[0]

# Agrupar valles contiguos
valley_ranges = []
if len(valleys) > 0:
    cur_start = valleys[0]
    cur_end = valleys[0]
    for v in valleys[1:]:
        if v == cur_end + 1:
            cur_end = v
        else:
            if (cur_end - cur_start) * hop / sr >= 0.1: # al menos 100ms
                valley_ranges.append((cur_start * hop / sr, cur_end * hop / sr))
            cur_start = v
            cur_end = v
    if (cur_end - cur_start) * hop / sr >= 0.1:
        valley_ranges.append((cur_start * hop / sr, cur_end * hop / sr))

print("\n--- VALLES DE VOLUMEN (POSIBLES CORTES O FADES EN PREVIA.wav) ---")
for s, e in valley_ranges:
    print(f"  Silencio/Bajada: {s:6.2f}s -> {e:6.2f}s (duración: {e-s:4.2f}s) [{int(s//60)}:{int(s%60):02d} -> {int(e//60)}:{int(e%60):02d}]")

# Detectar cambios espectrales bruscos (discontinuidades de corte)
onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
spec_diff = np.abs(np.diff(onset_env))
p99 = np.percentile(spec_diff, 99.5)
big_jumps = np.where(spec_diff > p99)[0]

print(f"\nRMS promedio: {np.mean(rms):.3f}, RMS max: {np.max(rms):.3f}")
