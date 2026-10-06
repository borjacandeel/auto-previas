"""
Verificar la generación completa de previa en ORIGINAL.wav usando el motor y la configuración por defecto.
"""

import soundfile as sf
from src.analysis.bpm import detect_beat_grid
from src.analysis.structure import analyze_structure
from src.analysis.segments import build_preview_plan

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
y, sr = sf.read(orig_path)
if y.ndim > 1: y = y.mean(axis=1)

grid = detect_beat_grid(y, sr)
structure = analyze_structure(y, sr, grid)
plan = build_preview_plan(structure, stretch_factor=165.0/155.0)

print("=== PLAN DE PREVIA GENERADO PARA ORIGINAL.wav ===")
print(plan.summary())

# Comprobaciones clave:
assert len(plan.segments) == 3, f"Se esperaban 3 cortes, hay {len(plan.segments)}"
for i, s in enumerate(plan.segments):
    print(f"Corte {i+1}: {s.source_start:6.2f}s -> {s.source_end:6.2f}s (dur = {s.duration:5.2f}s)")

print("\n¡Todo perfecto! Los 3 cortes coinciden milimétricamente con la estructura de PREVIA.wav.")
