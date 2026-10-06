"""
Verificar si el Bloque 1 de PREVIA es directamente el tramo desde t=0 de ORIGINAL
o desde dónde.
"""

import numpy as np
import soundfile as sf
import librosa

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

y_orig, sr = sf.read(orig_path)
y_prev, _ = sf.read(prev_path)

if y_orig.ndim > 1: y_orig = y_orig.mean(axis=1)
if y_prev.ndim > 1: y_prev = y_prev.mean(axis=1)

# Tomemos los primeros 80 segundos de ORIGINAL y los primeros 70s de PREVIA
# A 155 BPM:
# Beat 1 en ORIGINAL está en:
from src.analysis.bpm import detect_beat_grid
grid_o = detect_beat_grid(y_orig, sr)
grid_p = detect_beat_grid(y_prev, sr)

print(f"ORIGINAL BPM: {grid_o.bpm:.2f}, primer beat: {grid_o.beat_times[0]:.4f}s")
print(f"PREVIA BPM:   {grid_p.bpm:.2f}, primer beat: {grid_p.beat_times[0]:.4f}s")

# Imprimir los primeros 20 beat times de ambos
print("Primeros 10 beats ORIGINAL:")
print(np.round(grid_o.beat_times[:10], 3))

print("Primeros 10 beats PREVIA:")
print(np.round(grid_p.beat_times[:10], 3))

# Calculemos la correlación directa entre los beats de PREVIA y ORIGINAL
# Para cada beat de PREVIA (hasta el beat 120):
# ¿A qué beat de ORIGINAL corresponde acústicamente?
