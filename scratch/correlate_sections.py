"""
Comparar directamente los 3 bloques de PREVIA con las secciones de ORIGINAL.
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

# Puntos de corte observados en PREVIA.wav (a 165 BPM):
# Bloque 1: 0.0s -> 67.69s
# Bloque 2: 67.69s -> 117.84s
# Bloque 3: 117.84s -> 155.50s

# Tomemos trozos de cada bloque de PREVIA y busquemos exactamente en qué segundo de ORIGINAL están:
# Tomamos 4 segundos de cada trozo clave:
queries = [
    # Bloque 1
    ("B1_intro", 5.0, 4.0),
    ("B1_subida", 20.0, 4.0),
    ("B1_drop_start", 26.0, 4.0),
    ("B1_drop_mid", 45.0, 4.0),
    ("B1_drop_end", 65.0, 4.0),
    # Bloque 2
    ("B2_subida", 72.0, 4.0),
    ("B2_drop_start", 78.0, 4.0),
    ("B2_drop_mid", 95.0, 4.0),
    ("B2_drop_end", 115.0, 4.0),
    # Bloque 3
    ("B3_subida", 122.0, 4.0),
    ("B3_drop_start", 128.0, 4.0),
    ("B3_drop_mid", 142.0, 4.0),
    ("B3_drop_end", 152.0, 3.0),
]

# Usamos MFCC o CQT con time_stretch
sr_fast = 22050
y_o_fast = librosa.resample(y_orig, orig_sr=sr, target_sr=sr_fast)
y_p_fast = librosa.resample(y_prev, orig_sr=sr, target_sr=sr_fast)

# Estiramos PREVIA a 155 BPM
y_p_155 = librosa.effects.time_stretch(y_p_fast, rate=155.0/165.0)

hop = 512
cqt_o = np.abs(librosa.cqt(y_o_fast, sr=sr_fast, hop_length=hop, n_bins=48, bins_per_octave=12))
cqt_p = np.abs(librosa.cqt(y_p_155, sr=sr_fast, hop_length=hop, n_bins=48, bins_per_octave=12))

# Normalizar columnas
cqt_o_n = cqt_o / (np.linalg.norm(cqt_o, axis=0, keepdims=True) + 1e-6)
cqt_p_n = cqt_p / (np.linalg.norm(cqt_p, axis=0, keepdims=True) + 1e-6)

print(f"CQT shapes: orig={cqt_o_n.shape}, previa_155={cqt_p_n.shape}")

print("\n--- LOCALIZACIÓN EXACTA DE CADA PARTE EN ORIGINAL ---")
for name, t_p_real, dur in queries:
    # Tiempo en previa_155:
    t_p_155 = t_p_real * (165.0 / 155.0)
    f_start = int(t_p_155 * sr_fast / hop)
    f_len = int(dur * (165.0/155.0) * sr_fast / hop)
    
    sub = cqt_p_n[:, f_start:f_start+f_len]
    sub_norm = np.linalg.norm(sub)
    
    # Correlación rápida 2D a lo largo del tiempo
    n_search = cqt_o_n.shape[1] - f_len + 1
    scores = np.zeros(n_search)
    for b in range(cqt_o_n.shape[0]):
        scores += np.correlate(cqt_o_n[b], sub[b], mode='valid')
        
    best_f = np.argmax(scores)
    best_t_o = best_f * hop / sr_fast
    
    # Calcular la diferencia t_orig - t_p_155 para ver si es un bloque continuo
    offset = best_t_o - t_p_155
    print(f"{name:15s} (PREVIA {t_p_real:5.1f}s) -> ORIGINAL {best_t_o:6.2f}s ({int(best_t_o//60)}:{int(best_t_o%60):02d}) [offset={offset:6.2f}s, score={scores[best_f]/f_len:.2f}]")
