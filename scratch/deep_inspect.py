"""
Analizador profundo de PREVIA.wav vs ORIGINAL.wav:
1. Detectar si hay pitch shift, varispeed o time stretch.
2. Identificar visual/auditivamente y por compases la estructura de ORIGINAL y de PREVIA.
"""

import numpy as np
import soundfile as sf
import librosa

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

y_orig, sr_orig = sf.read(orig_path)
y_prev, sr_prev = sf.read(prev_path)

print(f"ORIGINAL sr={sr_orig}, shape={y_orig.shape}, dur={len(y_orig)/sr_orig:.2f}s")
print(f"PREVIA   sr={sr_prev}, shape={y_prev.shape}, dur={len(y_prev)/sr_prev:.2f}s")

# Tomemos los canales en mono
if y_orig.ndim > 1:
    y_orig_mono = y_orig.mean(axis=1)
else:
    y_orig_mono = y_orig

if y_prev.ndim > 1:
    y_prev_mono = y_prev.mean(axis=1)
else:
    y_prev_mono = y_prev

# Vamos a detectar los BPMs precisos usando onset strength y autocorrelación de compás
from src.analysis.bpm import detect_beat_grid
from src.analysis.structure import analyze_structure

print("\n--- ANÁLISIS ESTRUCTURAL DE ORIGINAL.wav ---")
grid_orig = detect_beat_grid(y_orig_mono, sr_orig)
print(f"ORIGINAL BPM: {grid_orig.bpm:.2f}, Beats detectados: {len(grid_orig.beat_times)}")
struct_orig = analyze_structure(y_orig_mono, sr_orig, grid_orig)

print(f"Total secciones en ORIGINAL: {len(struct_orig.sections)}")
for i, sec in enumerate(struct_orig.sections):
    print(f"  Sec {i:02d}: {sec.type.value:10s} | {sec.start_time:6.2f}s -> {sec.end_time:6.2f}s ({sec.duration:5.2f}s) | beats {sec.start_beat}->{sec.end_beat} | RMS: {sec.energy:.3f} | Bass: {sec.bass_energy:.3f} | Melody: {getattr(sec, 'melody_energy', 0):.3f} | Fullness: {getattr(sec, 'fullness', 0):.3f}")

print("\n--- ANÁLISIS ESTRUCTURAL DE PREVIA.wav ---")
grid_prev = detect_beat_grid(y_prev_mono, sr_prev)
print(f"PREVIA BPM: {grid_prev.bpm:.2f}, Beats detectados: {len(grid_prev.beat_times)}")
struct_prev = analyze_structure(y_prev_mono, sr_prev, grid_prev)

print(f"Total secciones en PREVIA: {len(struct_prev.sections)}")
for i, sec in enumerate(struct_prev.sections):
    print(f"  Sec {i:02d}: {sec.type.value:10s} | {sec.start_time:6.2f}s -> {sec.end_time:6.2f}s ({sec.duration:5.2f}s) | beats {sec.start_beat}->{sec.end_beat} | RMS: {sec.energy:.3f} | Bass: {sec.bass_energy:.3f} | Melody: {getattr(sec, 'melody_energy', 0):.3f} | Fullness: {getattr(sec, 'fullness', 0):.3f}")

