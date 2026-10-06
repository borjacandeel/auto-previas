"""
Simular el plan de previa con la lógica de 3 Grandes Drops + Subidas de 6 compases.
"""

import numpy as np
import soundfile as sf
from src.analysis.bpm import detect_beat_grid
from src.analysis.structure import (
    analyze_structure, SectionType, Section, StructureAnalysis,
    _kick_bass_envelope, _melody_envelope, _pitos_leads_envelope,
    _rms_envelope, HOP_LENGTH, SR_ANALYSIS
)

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
y, sr = sf.read(orig_path)
if y.ndim > 1: y = y.mean(axis=1)

grid = detect_beat_grid(y, sr)
bpm = grid.bpm
beats = grid.beat_times
n_bars = len(beats) // 4

def find_major_drops_and_buildups(y, sr, grid):
    if sr != SR_ANALYSIS:
        import librosa
        y = librosa.resample(y, orig_sr=sr, target_sr=SR_ANALYSIS)
        sr = SR_ANALYSIS
        
    rms_env = _rms_envelope(y)
    kick_env = _kick_bass_envelope(y, sr)
    mel_env = _melody_envelope(y, sr)
    pitos_env = _pitos_leads_envelope(y, sr)
    
    n_bars = len(grid.beat_times) // 4
    bar_kick = np.zeros(n_bars)
    bar_leads = np.zeros(n_bars)
    bar_rms = np.zeros(n_bars)
    
    for b in range(n_bars):
        import librosa
        t0 = grid.beat_times[b * 4]
        t1 = grid.beat_times[min(len(grid.beat_times) - 1, (b + 1) * 4)]
        f0 = max(0, min(librosa.time_to_frames(t0, sr=sr, hop_length=HOP_LENGTH), len(rms_env) - 1))
        f1 = max(f0 + 1, min(librosa.time_to_frames(t1, sr=sr, hop_length=HOP_LENGTH), len(rms_env)))
        
        bar_kick[b] = float(np.mean(kick_env[f0:f1]))
        m = float(np.mean(mel_env[f0:f1]))
        p = float(np.mean(pitos_env[f0:f1]))
        bar_leads[b] = 0.55 * m + 0.45 * p
        bar_rms[b] = float(np.mean(rms_env[f0:f1]))
        
    fullness = 0.35 * bar_kick + 0.35 * bar_rms + 0.30 * bar_leads
    
    # 1. Identificar compases con características de Drop real (bombo + energía + leads/pitos)
    is_drop = (bar_kick >= 0.42) & (bar_rms >= 0.40) & ((bar_leads >= 0.20) | (fullness >= 0.48))
    
    # Excluir intro DJ mix beat (los primeros compases antes del primer breakdown)
    for b in range(min(25, n_bars)):
        if b / n_bars < 0.15 and (bar_leads[b] < 0.35 or fullness[b] < 0.52):
            is_drop[b] = False
            
    # Unir micro-huecos (redobles de 1 o 2 compases dentro de un drop)
    bridged = np.copy(is_drop)
    for b in range(1, n_bars - 2):
        if not bridged[b] and bridged[b-1] and (bridged[b+1] or (b < n_bars-2 and bridged[b+2])):
            bridged[b] = True
            if b < n_bars - 2 and bridged[b+2]:
                bridged[b+1] = True
                
    # Detectar bloques continuos de drop
    drops = []
    in_d = False
    s_b = 0
    for b in range(n_bars):
        if bridged[b] and not in_d:
            in_d = True
            s_b = b
        elif not bridged[b] and in_d:
            in_d = False
            if b - s_b >= 8:  # al menos 8 compases
                drops.append((s_b, b))
    if in_d and n_bars - s_b >= 8:
        drops.append((s_b, n_bars))
        
    # Unir drops que están separados sólo por un mini-puente de menos de 4 compases
    merged_drops = []
    for d in drops:
        if not merged_drops:
            merged_drops.append(d)
        else:
            prev_s, prev_e = merged_drops[-1]
            curr_s, curr_e = d
            if curr_s - prev_e <= 4: # separados por <= 4 compases
                merged_drops[-1] = (prev_s, curr_e)
            else:
                merged_drops.append(d)
                
    return merged_drops, fullness

major_drops, fullness = find_major_drops_and_buildups(y, sr, grid)
print(f"Grandes Drops detectados ({len(major_drops)}):")
for i, (sb, eb) in enumerate(major_drops):
    t_s = beats[sb * 4]
    t_e = beats[min(len(beats)-1, eb * 4)]
    dur = t_e - t_s
    n_b = eb - sb
    f_val = np.mean(fullness[sb:eb])
    print(f"  Drop {i+1}: Compás {sb:3d}..{eb:3d} ({n_b:2d} compases, {dur:5.1f}s) | {t_s:6.2f}s -> {t_e:6.2f}s | Fullness: {f_val:.3f}")

# Ahora generemos los 3 cortes para la previa:
print("\n--- GENERACIÓN DE LOS 3 CORTES MUSICALES ---")
cuts = []
# REGLA PROFESIONAL DE PREVIA:
# Si hay 3 drops principales:
# Corte 1: Intro/Buildup 1 + Drop 1
# Corte 2: Buildup 2 + Drop 2
# Corte 3: Buildup 3 + Drop 3
BU_BARS = 6  # 6 compases exactos = 24 beats (igual que en PREVIA.wav)

if len(major_drops) >= 3:
    # Elegir los 3 drops principales (los 3 de mayor plenitud o 3 cronológicos)
    selected_drops = major_drops[:3] if len(major_drops) == 3 else sorted(sorted(major_drops, key=lambda d: np.mean(fullness[d[0]:d[1]]), reverse=True)[:3], key=lambda d: d[0])
    
    # Corte 1:
    d1_sb, d1_eb = selected_drops[0]
    # Si hay intro antes de la subida, podemos empezar en compás 0 o en d1_sb - BU_BARS
    # En PREVIA.wav empieza en 0.0s (compás 0) y va hasta el final de la frase del drop
    c1_start_bar = max(0, d1_sb - BU_BARS - 8) if d1_sb >= BU_BARS + 8 else max(0, d1_sb - BU_BARS)
    # Limitar el drop a ~28-30 compases alineado a múltiplo de 4 compases (frase)
    d1_len = min(eb - sb for sb, eb in [selected_drops[0]])
    c1_drop_bars = min(d1_eb - d1_sb, 28)
    c1_end_bar = d1_sb + (c1_drop_bars // 4) * 4  # exact multiple of 4 bars
    cuts.append((c1_start_bar, c1_end_bar, "Corte 1 (Apertura + Subida 1 + Drop 1)"))
    
    # Corte 2:
    d2_sb, d2_eb = selected_drops[1]
    c2_start_bar = max(0, d2_sb - BU_BARS)
    c2_drop_bars = min(d2_eb - d2_sb, 28)
    c2_end_bar = d2_sb + (c2_drop_bars // 4) * 4
    cuts.append((c2_start_bar, c2_end_bar, "Corte 2 (Subida 2 + Drop 2 Clímax)"))
    
    # Corte 3:
    d3_sb, d3_eb = selected_drops[2]
    c3_start_bar = max(0, d3_sb - BU_BARS)
    c3_drop_bars = min(d3_eb - d3_sb, 24)
    c3_end_bar = d3_sb + (c3_drop_bars // 4) * 4
    cuts.append((c3_start_bar, c3_end_bar, "Corte 3 (Subida 3 + Drop 3 Final)"))

total_dur = 0
for idx, (sb, eb, label) in enumerate(cuts):
    t_s = beats[sb * 4]
    t_e = beats[min(len(beats)-1, eb * 4)]
    dur = t_e - t_s
    total_dur += dur
    n_b = eb - sb
    print(f"{label}:")
    print(f"   Compás {sb:3d}..{eb:3d} ({n_b:2d} compases) | {t_s:6.2f}s -> {t_e:6.2f}s | Duración: {dur:5.1f}s [{int(t_s//60)}:{int(t_s%60):02d} -> {int(t_e//60)}:{int(t_e%60):02d}]")

print(f"\nDuración total previa antes de stretch: {total_dur:.1f}s ({int(total_dur//60)}:{int(total_dur%60):02d})")
print(f"Duración estimada a 165 BPM (factor 165/155): {total_dur * (155/165):.1f}s ({int(total_dur*(155/165)//60)}:{int(total_dur*(155/165)%60):02d})")
print(f"Duración PREVIA.wav real del usuario: 155.5s (2:35)")
