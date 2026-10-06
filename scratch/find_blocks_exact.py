"""
Búsqueda exhaustiva del inicio y fin de cada bloque de PREVIA en ORIGINAL.
"""

import numpy as np
import soundfile as sf
import librosa
from scipy.signal import fftconvolve

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

y_o, sr = sf.read(orig_path)
y_p, _ = sf.read(prev_path)
if y_o.ndim > 1: y_o = y_o.mean(axis=1)
if y_p.ndim > 1: y_p = y_p.mean(axis=1)

sr_fast = 11025
y_o_fast = librosa.resample(y_o, orig_sr=sr, target_sr=sr_fast)
y_p_fast = librosa.resample(y_p, orig_sr=sr, target_sr=sr_fast)

# Ralentizar PREVIA a 155 BPM
y_p_155 = librosa.effects.time_stretch(y_p_fast, rate=155.0/165.0)

# Extraer envolvente espectral o MFCC (13 bandas)
hop = 256
mfcc_o = librosa.feature.mfcc(y=y_o_fast, sr=sr_fast, n_mfcc=13, hop_length=hop)
mfcc_p = librosa.feature.mfcc(y=y_p_155, sr=sr_fast, n_mfcc=13, hop_length=hop)

# Normalizar
mfcc_o = (mfcc_o - mfcc_o.mean(axis=1, keepdims=True)) / (mfcc_o.std(axis=1, keepdims=True) + 1e-6)
mfcc_p = (mfcc_p - mfcc_p.mean(axis=1, keepdims=True)) / (mfcc_p.std(axis=1, keepdims=True) + 1e-6)

# Los 3 bloques en PREVIA_155:
# Bloque 1: 0.0s a ~72.1s
# Bloque 2: 72.1s a ~125.4s
# Bloque 3: 125.4s a ~165.5s

blocks = [
    ("BLOQUE 1", 0.0, 72.06),
    ("BLOQUE 2", 72.06, 125.44),
    ("BLOQUE 3", 125.44, 165.53)
]

print(f"Duración ORIGINAL: {len(y_o)/sr:.2f}s")
print(f"Duración PREVIA_155: {len(y_p_155)/sr_fast:.2f}s\n")

for name, t_s, t_e in blocks:
    # Tomamos un trozo central de 8 segundos de cada bloque para encontrar su alineación exacta
    # (en la mitad del bloque)
    t_mid = (t_s + t_e) / 2.0
    f_mid_s = int((t_mid - 4.0) * sr_fast / hop)
    f_mid_e = int((t_mid + 4.0) * sr_fast / hop)
    
    probe = mfcc_p[:, f_mid_s:f_mid_e]
    win_len = probe.shape[1]
    
    # Correlación con mfcc_o
    n_search = mfcc_o.shape[1] - win_len + 1
    scores = np.zeros(n_search)
    for c in range(mfcc_o.shape[0]):
        scores += np.correlate(mfcc_o[c], probe[c], mode='valid')
        
    best_f = np.argmax(scores)
    t_orig_mid = (best_f + win_len / 2.0) * hop / sr_fast
    
    # Entonces el inicio de este bloque en ORIGINAL sería:
    t_orig_start = t_orig_mid - (t_mid - t_s)
    t_orig_end = t_orig_mid + (t_e - t_mid)
    
    print(f"=== {name} ===")
    print(f"  PREVIA (165 BPM): {t_s*(155/165):5.1f}s -> {t_e*(155/165):5.1f}s (dur = {(t_e-t_s)*(155/165):5.1f}s)")
    print(f"  PREVIA (155 BPM): {t_s:5.1f}s -> {t_e:5.1f}s (dur = {t_e-t_s:5.1f}s)")
    print(f"  -> Coincide en ORIGINAL.wav: {t_orig_start:6.2f}s -> {t_orig_end:6.2f}s ({int(t_orig_start//60)}:{int(t_orig_start%60):02d} -> {int(t_orig_end//60)}:{int(t_orig_end%60):02d})")
    print(f"  Score de similitud: {scores[best_f]/win_len:.2f}\n")

