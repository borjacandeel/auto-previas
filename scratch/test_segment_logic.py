"""
Test completo de la lógica de selección de segmentos en ORIGINAL.wav y synthetic track.
"""

import numpy as np
import soundfile as sf
from src.analysis.bpm import detect_beat_grid
from src.analysis.structure import analyze_structure, SectionType, Section, StructureAnalysis

# 1. Probar en ORIGINAL.wav
orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
y, sr = sf.read(orig_path)
if y.ndim > 1: y = y.mean(axis=1)
grid = detect_beat_grid(y, sr)
struct_orig = analyze_structure(y, sr, grid)

print(f"Total secciones en ORIGINAL: {len(struct_orig.sections)}")
for i, s in enumerate(struct_orig.sections):
    print(f"  [{i:02d}] {s.type.name:10s} | {s.start_time:6.2f}s -> {s.end_time:6.2f}s ({s.duration:5.2f}s)")

drops = [s for s in struct_orig.sections if s.type == SectionType.DROP]
print(f"\nDrops detectados en ORIGINAL: {len(drops)}")
for i, d in enumerate(drops):
    print(f"  Drop {i+1}: {d.start_time:6.2f}s -> {d.end_time:6.2f}s ({d.duration:5.2f}s) | fullness={getattr(d, 'fullness', 0):.3f}")
