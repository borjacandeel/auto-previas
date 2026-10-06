"""
Detalle exacto de las secciones en ORIGINAL.wav y comparación de huella sonora con PREVIA.
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

# Comparemos las 3 secciones principales de PREVIA:
# PREVIA Bloque 1: 0.0s -> 67.7s  (duración 67.7s a 165 BPM = 46.5 compases)
# PREVIA Bloque 2: 67.7s -> 117.8s (duración 50.1s a 165 BPM = 34.5 compases)
# PREVIA Bloque 3: 117.8s -> 155.5s (duración 37.7s a 165 BPM = 26 compases)

# En ORIGINAL:
# Calculemos el beat grid exacto de ORIGINAL (a 155 BPM)
from src.analysis.bpm import detect_beat_grid
grid_orig = detect_beat_grid(y_orig, sr)
print(f"ORIGINAL BPM: {grid_orig.bpm}")

# Imprimir los compases (cada 4 beats) donde ocurren cambios en ORIGINAL
# Compás = 4 beats = 4 * (60 / 155) = 1.5484 segundos
bar_dur = 4.0 * (60.0 / grid_orig.bpm)
print(f"Duración de 1 compás (4 beats) a {grid_orig.bpm} BPM: {bar_dur:.4f}s")
print(f"Duración de 4 compases (16 beats / 1 frase): {4 * bar_dur:.4f}s")
print(f"Duración de 8 compases (32 beats / 1 frase doble): {8 * bar_dur:.4f}s")
print(f"Duración de 16 compases (64 beats): {16 * bar_dur:.4f}s")

# Calculemos la energía de agudos (melodía/pitos) y graves (bombo) por cada compás de ORIGINAL:
from src.analysis.structure import _kick_bass_envelope, _melody_envelope, _pitos_leads_envelope

kick_env = _kick_bass_envelope(y_orig, sr)
melody_env = _melody_envelope(y_orig, sr)
pitos_env = _pitos_leads_envelope(y_orig, sr)
rms_env = librosa.feature.rms(y=y_orig, frame_length=1024, hop_length=256)[0]

n_bars = len(grid_orig.beat_times) // 4
print(f"\nTotal compases en ORIGINAL: {n_bars}")

print("\n--- COMPASES CLAVE DE ORIGINAL.wav ---")
for bar_idx in range(n_bars):
    t_start = grid_orig.beat_times[bar_idx * 4]
    t_end = grid_orig.beat_times[min(len(grid_orig.beat_times)-1, (bar_idx + 1) * 4)]
    
    # Calcular promedios en este compás
    s_frame = int(t_start * sr / 256)
    e_frame = int(t_end * sr / 256)
    
    k = np.mean(kick_env[s_frame:e_frame]) if e_frame > s_frame else 0
    m = np.mean(melody_env[s_frame:e_frame]) if e_frame > s_frame else 0
    p = np.mean(pitos_env[s_frame:e_frame]) if e_frame > s_frame else 0
    r = np.mean(rms_env[s_frame:e_frame]) if e_frame > s_frame else 0
    
    # Solo imprimir compases donde hay cambios importantes o cada 4 compases (frase)
    if bar_idx % 4 == 0 or k > 0.5 or m > 0.5 or p > 0.5:
        # Etiqueta rápida
        tag = ""
        if k > 0.4 and p > 0.2:
            tag = "🔥 DROP CARGADO (Bombo + Pitos/Leads)"
        elif k > 0.4:
            tag = "🥁 BASE / BOMBO SOLO"
        elif p > 0.25 or m > 0.35:
            tag = "🎹 MELODÍA / SINTES"
        elif r > 0.25 and k < 0.3:
            tag = "⚡ SUBIDA / RISER"
        else:
            tag = "Intro/Outro/Break"
            
        print(f"Bar {bar_idx:3d} ({int(bar_idx/4):2d} frases) | {t_start:6.2f}s -> {t_end:6.2f}s | K:{k:4.2f} M:{m:4.2f} P:{p:4.2f} R:{r:4.2f} | {tag}")

