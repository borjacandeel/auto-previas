"""
Analizar ORIGINAL.wav completamente e imprimir todas las secciones detectadas
por analyze_structure y los segmentos generados por select_preview_segments.
"""

import soundfile as sf
import numpy as np
from src.analysis.bpm import detect_beat_grid
from src.analysis.structure import analyze_structure, SectionType
from src.analysis.segments import build_preview_plan

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
y, sr = sf.read(orig_path)
if y.ndim > 1: y = y.mean(axis=1)

print(f"Cargado ORIGINAL.wav: {len(y)/sr:.2f}s")
grid = detect_beat_grid(y, sr)
print(f"BPM: {grid.bpm}")

structure = analyze_structure(y, sr, grid)
print(f"\n--- SECCIONES DETECTADAS EN ORIGINAL.wav ({len(structure.sections)} secciones) ---")
for i, s in enumerate(structure.sections):
    print(f"[{i:02d}] {s.type.name:10s} | {s.start_time:6.2f}s -> {s.end_time:6.2f}s ({s.duration:5.2f}s) | beats {s.start_beat:3d}..{s.end_beat:3d} | E:{s.energy:4.2f} Bass:{s.bass_energy:4.2f} Mel:{getattr(s, 'melody_energy', 0):4.2f} Full:{getattr(s, 'fullness', 0):4.2f}")

plan = build_preview_plan(structure)
print(f"\n--- PLAN DE PREVIA (MÁXIMO 3 CORTES) ---")
print(plan.summary())


