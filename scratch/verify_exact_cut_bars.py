"""
Encontrar los compases musicales EXACTOS (downbeats) de los 3 cortes de PREVIA en ORIGINAL.
"""

import numpy as np
import soundfile as sf
import librosa
from src.analysis.bpm import detect_beat_grid

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

y_o, sr = sf.read(orig_path)
y_p, _ = sf.read(prev_path)
if y_o.ndim > 1: y_o = y_o.mean(axis=1)
if y_p.ndim > 1: y_p = y_p.mean(axis=1)

grid_o = detect_beat_grid(y_o, sr)
grid_p = detect_beat_grid(y_p, sr)

# Beats de ORIGINAL:
beats_o = grid_o.beat_times

# Compases en ORIGINAL (cada 4 beats):
# Un compás = 4 beats = 1.5484s
# Una frase = 16 beats (4 compases) = 6.1935s
# Una frase doble = 32 beats (8 compases) = 12.3871s

# Bloque 1 en PREVIA:
# Duración en PREVIA: 67.69s (186 beats a 165 BPM = 46.5 compases)
# En ORIGINAL (a 155 BPM): 67.69 * (165/155) = 72.06s (186 beats = 46.5 compases)

# Bloque 2 en PREVIA:
# Duración en PREVIA: 50.15s (138 beats a 165 BPM = 34.5 compases)
# En ORIGINAL (a 155 BPM): 50.15 * (165/155) = 53.39s (138 beats = 34.5 compases)

# Bloque 3 en PREVIA:
# Duración en PREVIA: 37.66s (103.5 beats a 165 BPM = ~26 compases)
# En ORIGINAL (a 155 BPM): 37.66 * (165/155) = 40.09s (103.5 beats = ~26 compases)

print("--- ANÁLISIS DE PUNTOS DE INICIO Y FIN DE BLOQUES EN ORIGINAL ---")

# Busquemos los compases exactos alrededor de:
# Bloque 1: start ~23s..25s, end ~95s..97s
# Bloque 2: start ~169s, end ~222s..230s
# Bloque 3: start ~260s, end ~300s..316s

# Para cada compás candidato, calculemos la correlación muestra a muestra:
# Ralentizar PREVIA a 155 BPM con time_stretch
sr_fast = 22050
y_o_fast = librosa.resample(y_o, orig_sr=sr, target_sr=sr_fast)
y_p_fast = librosa.resample(y_p, orig_sr=sr, target_sr=sr_fast)
y_p_155 = librosa.effects.time_stretch(y_p_fast, rate=155.0/165.0)

hop = 256
mfcc_o = librosa.feature.mfcc(y=y_o_fast, sr=sr_fast, n_mfcc=20, hop_length=hop)
mfcc_p = librosa.feature.mfcc(y=y_p_155, sr=sr_fast, n_mfcc=20, hop_length=hop)

def find_best_orig_beat(p_time_155, win_sec=4.0, search_center=None, search_radius=15.0):
    f_p = int(p_time_155 * sr_fast / hop)
    w_f = int(win_sec * sr_fast / hop)
    if f_p + w_f > mfcc_p.shape[1]:
        w_f = mfcc_p.shape[1] - f_p
    sub_p = mfcc_p[:, f_p:f_p+w_f]
    sub_p = (sub_p - sub_p.mean()) / (np.linalg.norm(sub_p) + 1e-6)
    
    if search_center is not None:
        c_f = int(search_center * sr_fast / hop)
        r_f = int(search_radius * sr_fast / hop)
        start_f = max(0, c_f - r_f)
        end_f = min(mfcc_o.shape[1] - w_f, c_f + r_f)
    else:
        start_f = 0
        end_f = mfcc_o.shape[1] - w_f
        
    scores = []
    for i in range(start_f, end_f):
        cand = mfcc_o[:, i:i+w_f]
        cand = (cand - cand.mean()) / (np.linalg.norm(cand) + 1e-6)
        scores.append(np.sum(cand * sub_p))
        
    best_idx = start_f + np.argmax(scores)
    best_t = best_idx * hop / sr_fast
    
    # Encontrar el beat de ORIGINAL más cercano a best_t
    beat_idx = np.argmin(np.abs(beats_o - best_t))
    closest_beat = beats_o[beat_idx]
    bar_num = beat_idx // 4
    beat_in_bar = beat_idx % 4 + 1
    return closest_beat, beat_idx, bar_num, beat_in_bar, scores[np.argmax(scores)]

# 1. Inicio de Bloque 1 (t=0.0s en PREVIA_155)
b1_s, idx_b1_s, bar_b1_s, b_in_bar_1s, sc1s = find_best_orig_beat(1.0, win_sec=2.0, search_center=15.0, search_radius=15.0)
print(f"Bloque 1 Inicio:  t={b1_s:.3f}s | beat {idx_b1_s} (Compás {bar_b1_s}, beat {b_in_bar_1s}) [score={sc1s:.2f}]")

# 1. Fin de Bloque 1 (t=71.0s en PREVIA_155)
b1_e, idx_b1_e, bar_b1_e, b_in_bar_1e, sc1e = find_best_orig_beat(70.0, win_sec=2.0, search_center=86.0, search_radius=10.0)
print(f"Bloque 1 Fin:     t={b1_e:.3f}s | beat {idx_b1_e} (Compás {bar_b1_e}, beat {b_in_bar_1e}) [score={sc1e:.2f}]")

# 2. Inicio de Bloque 2 (t=73.0s en PREVIA_155)
b2_s, idx_b2_s, bar_b2_s, b_in_bar_2s, sc2s = find_best_orig_beat(73.0, win_sec=2.0, search_center=169.0, search_radius=10.0)
print(f"Bloque 2 Inicio:  t={b2_s:.3f}s | beat {idx_b2_s} (Compás {bar_b2_s}, beat {b_in_bar_2s}) [score={sc2s:.2f}]")

# 2. Fin de Bloque 2 (t=124.0s en PREVIA_155)
b2_e, idx_b2_e, bar_b2_e, b_in_bar_2e, sc2e = find_best_orig_beat(123.0, win_sec=2.0, search_center=223.0, search_radius=10.0)
print(f"Bloque 2 Fin:     t={b2_e:.3f}s | beat {idx_b2_e} (Compás {bar_b2_e}, beat {b_in_bar_2e}) [score={sc2e:.2f}]")

# 3. Inicio de Bloque 3 (t=126.5s en PREVIA_155)
b3_s, idx_b3_s, bar_b3_s, b_in_bar_3s, sc3s = find_best_orig_beat(126.5, win_sec=2.0, search_center=260.0, search_radius=10.0)
print(f"Bloque 3 Inicio:  t={b3_s:.3f}s | beat {idx_b3_s} (Compás {bar_b3_s}, beat {b_in_bar_3s}) [score={sc3s:.2f}]")

# 3. Fin de Bloque 3 (t=163.0s en PREVIA_155)
b3_e, idx_b3_e, bar_b3_e, b_in_bar_3e, sc3e = find_best_orig_beat(162.0, win_sec=2.0, search_center=300.0, search_radius=20.0)
print(f"Bloque 3 Fin:     t={b3_e:.3f}s | beat {idx_b3_e} (Compás {bar_b3_e}, beat {b_in_bar_3e}) [score={sc3e:.2f}]")


