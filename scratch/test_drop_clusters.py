"""
Probar la nueva lógica de detección de Drops reales, Buildups de 6 compases,
y selección de los 3 cortes para la previa en ORIGINAL.wav.
"""

import numpy as np
import soundfile as sf
import librosa
from src.analysis.bpm import detect_beat_grid
from src.analysis.structure import (
    analyze_structure, SectionType, Section, StructureAnalysis,
    _kick_bass_envelope, _melody_envelope, _pitos_leads_envelope,
    _rms_envelope, HOP_LENGTH, SR_ANALYSIS, _k_weight, _lufs_from_kweighted, _peak_dbfs
)

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
y, sr = sf.read(orig_path)
if y.ndim > 1: y = y.mean(axis=1)

grid = detect_beat_grid(y, sr)
print(f"ORIGINAL BPM: {grid.bpm}")
bar_dur = 4.0 * (60.0 / grid.bpm)
print(f"Duración compás: {bar_dur:.3f}s, 4 compases (frase): {4*bar_dur:.3f}s, 6 compases (subida): {6*bar_dur:.3f}s")

# Implementemos la detección perfeccionada de Drops y Subidas:
def detect_perfect_structure(y, sr, grid):
    if sr != SR_ANALYSIS:
        y = librosa.resample(y, orig_sr=sr, target_sr=SR_ANALYSIS)
        sr = SR_ANALYSIS
        
    total_dur = len(y) / sr
    n_beats = len(grid.beat_times)
    n_bars = n_beats // 4
    
    rms_env = _rms_envelope(y)
    kick_env = _kick_bass_envelope(y, sr)
    mel_env = _melody_envelope(y, sr)
    pitos_env = _pitos_leads_envelope(y, sr)
    y_kw = _k_weight(y, sr)
    
    bar_kick = np.zeros(n_bars)
    bar_mel = np.zeros(n_bars)
    bar_pitos = np.zeros(n_bars)
    bar_rms = np.zeros(n_bars)
    bar_times = np.zeros(n_bars)
    
    for b in range(n_bars):
        t0 = grid.beat_times[b * 4]
        t1 = grid.beat_times[min(n_beats - 1, (b + 1) * 4)]
        f0 = max(0, min(librosa.time_to_frames(t0, sr=sr, hop_length=HOP_LENGTH), len(rms_env) - 1))
        f1 = max(f0 + 1, min(librosa.time_to_frames(t1, sr=sr, hop_length=HOP_LENGTH), len(rms_env)))
        
        bar_kick[b] = float(np.mean(kick_env[f0:f1]))
        bar_mel[b] = float(np.mean(mel_env[f0:f1]))
        bar_pitos[b] = float(np.mean(pitos_env[f0:f1]))
        bar_rms[b] = float(np.mean(rms_env[f0:f1]))
        bar_times[b] = t0
        
    bar_leads = 0.55 * bar_mel + 0.45 * bar_pitos
    bar_fullness = 0.35 * bar_kick + 0.35 * bar_rms + 0.30 * bar_leads
    
    # 1. Encontrar los picos de Drops reales (lo más cargado del tema)
    # Un Drop real tiene bombo fuerte + leads/pitos + rms alto
    is_drop_bar = (bar_kick >= 0.45) & (bar_rms >= 0.42) & ((bar_leads >= 0.22) | (bar_fullness >= 0.50))
    
    # Eliminar falsos drops de la intro (primeros 20% del tema si son sólo de mezcla DJ)
    # Si en los primeros 25 compases hay bombos pero luego viene un break/melodía antes del Drop 1
    # comprobamos si hay una subida posterior
    for b in range(min(25, n_bars)):
        # Si no tiene suficiente carga melódica en la intro, es intro beat
        if b / n_bars < 0.15 and (bar_leads[b] < 0.35 or bar_fullness[b] < 0.52):
            is_drop_bar[b] = False
            
    # Agrupar compases de drop contiguos con majority filter
    clean_drop_bars = np.copy(is_drop_bar)
    for b in range(2, n_bars - 2):
        if np.sum(is_drop_bar[b-2:b+3]) >= 3:
            clean_drop_bars[b] = True
        elif np.sum(is_drop_bar[b-2:b+3]) <= 1:
            clean_drop_bars[b] = False
            
    # Encontrar bloques continuos de Drop
    drop_clusters = []
    in_drop = False
    start_b = 0
    for b in range(n_bars):
        if clean_drop_bars[b] and not in_drop:
            in_drop = True
            start_b = b
        elif not clean_drop_bars[b] and in_drop:
            in_drop = False
            if b - start_b >= 8: # Mínimo 8 compases de drop (12 segundos)
                drop_clusters.append((start_b, b))
    if in_drop and n_bars - start_b >= 8:
        drop_clusters.append((start_b, n_bars))
        
    print(f"\n--- CLUSTERS DE DROP REALES DETECTADOS ({len(drop_clusters)}) ---")
    for i, (sb, eb) in enumerate(drop_clusters):
        t_s = grid.beat_times[sb * 4]
        t_e = grid.beat_times[min(n_beats - 1, eb * 4)]
        dur = t_e - t_s
        n_b = eb - sb
        full = np.mean(bar_fullness[sb:eb])
        print(f"Drop {i+1}: Compases {sb:3d}..{eb:3d} ({n_b:2d} compases, {dur:5.1f}s) | {t_s:6.2f}s -> {t_e:6.2f}s | Fullness: {full:.3f}")
        
    return drop_clusters, bar_times, bar_fullness, n_bars

clusters, bar_times, fullness, n_bars = detect_perfect_structure(y, sr, grid)
