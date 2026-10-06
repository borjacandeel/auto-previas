"""
Alinear PREVIA.wav con ORIGINAL.wav compensando el tempo (155 vs 163.5 BPM)
para encontrar los timestamps muestra a muestra exactos en ORIGINAL.
"""

import numpy as np
import soundfile as sf
import librosa
from scipy.signal import correlate

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

y_orig, sr = librosa.load(orig_path, sr=22050, mono=True)
y_prev, _ = librosa.load(prev_path, sr=22050, mono=True)

bpm_orig = 155.0
bpm_prev = 163.5
speed_ratio = bpm_prev / bpm_orig  # ~1.0548

print(f"Speed ratio estimada (PREVIA/ORIGINAL): {speed_ratio:.4f}")

# Estirar la previa a la velocidad original para hacer correlación perfecta
y_prev_stretched = librosa.resample(y_prev, orig_sr=int(22050 * speed_ratio), target_sr=22050)
print(f"PREVIA reescalada dur: {len(y_prev_stretched)/22050:.2f}s (era {len(y_prev)/22050:.2f}s)")

# Puntos clave en PREVIA (en segundos de la PREVIA original):
# Bloque 1: 0.0s -> 67.7s (Intro + Buildup 1 + Drop 1)
# Bloque 2: 67.7s -> 117.8s (Buildup 2 + Drop 2)
# Bloque 3: 117.8s -> 155.5s (Buildup 3 + Drop 3)

# Busquemos chunks de 5 segundos de cada parte de la previa en el original:
probe_times_prev = [2.0, 10.0, 20.0, 30.0, 45.0, 60.0, 70.0, 80.0, 100.0, 120.0, 130.0, 145.0]

# Extraer MFCC o espectro de potencia
hop = 512
mfcc_orig = librosa.feature.mfcc(y=y_orig, sr=sr, n_mfcc=20, hop_length=hop)
mfcc_prev = librosa.feature.mfcc(y=y_prev_stretched, sr=sr, n_mfcc=20, hop_length=hop)

# Normalizar MFCCs
mfcc_orig = (mfcc_orig - mfcc_orig.mean(axis=1, keepdims=True)) / (mfcc_orig.std(axis=1, keepdims=True) + 1e-6)
mfcc_prev = (mfcc_prev - mfcc_prev.mean(axis=1, keepdims=True)) / (mfcc_prev.std(axis=1, keepdims=True) + 1e-6)

print("\n--- BÚSQUEDA DE PUNTOS CLAVE EN ORIGINAL ---")
for t_p in probe_times_prev:
    # Tiempo en prev_stretched
    t_p_str = t_p * speed_ratio
    f_p = int(t_p_str * sr / hop)
    win = int(4.0 * sr / hop)  # ventana de 4 segundos
    
    if f_p + win > mfcc_prev.shape[1]:
        continue
        
    chunk = mfcc_prev[:, f_p:f_p + win]
    
    # Correlación con orig
    # Producto punto deslizante
    corrs = np.zeros(mfcc_orig.shape[1] - win + 1)
    for c in range(mfcc_orig.shape[0]):
        corrs += np.correlate(mfcc_orig[c], chunk[c], mode='valid')
        
    best_f_orig = np.argmax(corrs)
    t_o = best_f_orig * hop / sr
    corr_val = corrs[best_f_orig] / win
    
    print(f"PREVIA t={t_p:5.1f}s -> ORIGINAL t={t_o:6.2f}s ({int(t_o//60)}:{int(t_o%60):02d}) [corr={corr_val:5.1f}]")

