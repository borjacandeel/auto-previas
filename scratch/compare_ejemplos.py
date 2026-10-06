"""
Script para analizar y comparar ORIGINAL.wav y PREVIA.wav en ejemplos/
Usa audio fingerprinting / cross-correlation espectral o MFCCs / chroma
para encontrar exactamente qué fragmentos de ORIGINAL.wav componen PREVIA.wav,
sus tiempos exactos, compases, BPM, y estructura musical.
"""

import sys
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

print("--- INFORMACIÓN DE ARCHIVOS ---")
info_orig = sf.info(orig_path)
info_prev = sf.info(prev_path)

print(f"ORIGINAL: {info_orig.frames} frames, {info_orig.samplerate} Hz, {info_orig.channels} ch, {info_orig.duration:.2f} s")
print(f"PREVIA:   {info_prev.frames} frames, {info_prev.samplerate} Hz, {info_prev.channels} ch, {info_prev.duration:.2f} s")

# Cargar a 22050 mono para análisis musical rápido
print("\nCargando audio a 22050 Hz...")
y_orig, sr = librosa.load(orig_path, sr=22050, mono=True)
y_prev, _ = librosa.load(prev_path, sr=22050, mono=True)

print("Detectando BPM y beat grids...")
tempo_orig, beats_orig = librosa.beat.beat_track(y=y_orig, sr=sr)
tempo_prev, beats_prev = librosa.beat.beat_track(y=y_prev, sr=sr)
beat_times_orig = librosa.frames_to_time(beats_orig, sr=sr)
beat_times_prev = librosa.frames_to_time(beats_prev, sr=sr)

print(f"BPM ORIGINAL estimado: {float(np.atleast_1d(tempo_orig)[0]):.2f}")
print(f"BPM PREVIA   estimado: {float(np.atleast_1d(tempo_prev)[0]):.2f}")

# Extraer chromagramas para alineamiento y búsqueda de coincidencia
print("\nExtrayendo características de croma/espectrograma para mapeo...")
hop_length = 512
chroma_orig = librosa.feature.chroma_cqt(y=y_orig, sr=sr, hop_length=hop_length)
chroma_prev = librosa.feature.chroma_cqt(y=y_prev, sr=sr, hop_length=hop_length)

# Ventana deslizante para encontrar los tramos de PREVIA en ORIGINAL
# Muestreamos cada 1 segundo en PREVIA para encontrar dónde encaja en ORIGINAL
n_frames_prev = chroma_prev.shape[1]
n_frames_orig = chroma_orig.shape[1]

print(f"Frames PREVIA: {n_frames_prev} (~{len(y_prev)/sr:.1f}s), Frames ORIGINAL: {n_frames_orig} (~{len(y_orig)/sr:.1f}s)")

# Usamos ventanas de 3 segundos (3 * sr / hop_length ~ 130 frames) para buscar coincidencias
win_frames = int(3.0 * sr / hop_length)
step_frames = int(1.0 * sr / hop_length)

matches = [] # (prev_sec, orig_sec, similarity)

# Para velocidad, buscar correlación por bloques
for p_idx in range(0, n_frames_prev - win_frames, step_frames):
    p_chunk = chroma_prev[:, p_idx:p_idx + win_frames]
    p_norm = np.linalg.norm(p_chunk)
    if p_norm < 1e-4:
        continue
    p_chunk = p_chunk / p_norm
    
    # Correlación cruzada con original a lo largo del tiempo
    # Para ser más rápido, calcular producto punto
    # chroma_orig shape: (12, T)
    # convolucionamos cada una de las 12 notas
    corrs = np.zeros(n_frames_orig - win_frames + 1)
    for c in range(12):
        corrs += np.correlate(chroma_orig[c], p_chunk[c], mode='valid')
    
    # Normalizar por la energía del chunk de original
    best_orig_idx = np.argmax(corrs)
    best_score = corrs[best_orig_idx]
    
    p_time = p_idx * hop_length / sr
    o_time = best_orig_idx * hop_length / sr
    matches.append((p_time, o_time, best_score))

print("\n--- MAPEO PREVIA -> ORIGINAL (cada segundo) ---")
prev_o = None
cuts = []
current_cut = []

for p_t, o_t, score in matches:
    if prev_o is not None:
        expected_o = prev_o + 1.0
        # Si la diferencia entre lo esperado y lo encontrado es mayor a 1.5s, hubo un corte/salto
        if abs(o_t - expected_o) > 1.8:
            if current_cut:
                cuts.append(current_cut)
                current_cut = []
    current_cut.append((p_t, o_t, score))
    prev_o = o_t

if current_cut:
    cuts.append(current_cut)

print(f"Total de bloques/cortes detectados en la PREVIA: {len(cuts)}")
for i, c in enumerate(cuts):
    p_start, o_start, _ = c[0]
    p_end, o_end, _ = c[-1]
    dur = p_end - p_start + 1.0
    print(f"\n--- BLOQUE #{i+1} ---")
    print(f"  En PREVIA:   {p_start:6.1f}s -> {p_end+1.0:6.1f}s (duración: {dur:5.1f}s) [{int(p_start//60)}:{int(p_start%60):02d} -> {int((p_end+1)//60)}:{int((p_end+1)%60):02d}]")
    print(f"  En ORIGINAL: {o_start:6.1f}s -> {o_end+1.0:6.1f}s (duración orig: {o_end-o_start+1.0:5.1f}s) [{int(o_start//60)}:{int(o_start%60):02d} -> {int((o_end+1)//60)}:{int((o_end+1)%60):02d}]")
