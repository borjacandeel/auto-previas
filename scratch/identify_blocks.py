"""
Localizar los 3 bloques exactos de PREVIA en ORIGINAL usando correlación directa
de fragmentos de audio time-stretched con keylock.
"""

import numpy as np
import soundfile as sf
import librosa
from scipy.signal import correlate

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

sr = 22050
y_orig, _ = librosa.load(orig_path, sr=sr, mono=True)
y_prev, _ = librosa.load(prev_path, sr=sr, mono=True)

# Como PREVIA tiene keylock a 165 BPM, la ralentizamos con phase vocoder o resample
# Si tiene keylock, librosa.effects.time_stretch con rate = 155.0 / 165.0 (~0.939)
# preserva el pitch y alinea los beats con ORIGINAL
print("Aplicando time stretch a PREVIA para desacelerar de 165 a 155 BPM...")
y_prev_155 = librosa.effects.time_stretch(y_prev, rate=155.0 / 165.0)

print(f"Duración PREVIA original: {len(y_prev)/sr:.2f}s")
print(f"Duración PREVIA a 155BPM: {len(y_prev_155)/sr:.2f}s")

# Definir puntos de prueba dentro de los 3 bloques en PREVIA (en segundos de y_prev_155):
# En y_prev_155:
# Bloque 1: ~0s a 72s
# Bloque 2: ~72s a 125s
# Bloque 3: ~125s a 165s

probe_points = [
    ("Bloque 1 - Inicio", 5.0, 10.0),
    ("Bloque 1 - Subida", 20.0, 25.0),
    ("Bloque 1 - Drop", 40.0, 50.0),
    ("Bloque 2 - Subida", 75.0, 80.0),
    ("Bloque 2 - Drop", 90.0, 100.0),
    ("Bloque 3 - Subida", 130.0, 135.0),
    ("Bloque 3 - Drop", 145.0, 155.0),
]

# Usar CQT espectral normalizado para robustez absoluta
hop = 512
cqt_orig = np.abs(librosa.cqt(y_orig, sr=sr, hop_length=hop))
cqt_orig_norm = (cqt_orig - cqt_orig.mean()) / (np.linalg.norm(cqt_orig) + 1e-6)

cqt_prev = np.abs(librosa.cqt(y_prev_155, sr=sr, hop_length=hop))

print("\n--- IDENTIFICACIÓN DE CADA PARTE EN ORIGINAL.wav ---")
for name, t_start, t_end in probe_points:
    f_s = int(t_start * sr / hop)
    f_e = int(t_end * sr / hop)
    chunk = cqt_prev[:, f_s:f_e]
    chunk_norm = (chunk - chunk.mean()) / (np.linalg.norm(chunk) + 1e-6)
    
    # Correlación con cqt_orig
    n_win = chunk.shape[1]
    n_search = cqt_orig.shape[1] - n_win + 1
    
    # Dot product sumado sobre todas las frecuencias
    corrs = np.zeros(n_search)
    for row in range(cqt_orig.shape[0]):
        corrs += np.correlate(cqt_orig[row], chunk[row], mode='valid')
        
    best_idx = np.argmax(corrs)
    match_sec = best_idx * hop / sr
    score = corrs[best_idx]
    
    print(f"{name:20s} (PREVIA {t_start:5.1f}s-{t_end:5.1f}s) -> ORIGINAL en {match_sec:6.2f}s ({int(match_sec//60)}:{int(match_sec%60):02d}) [score={score:.1f}]")
