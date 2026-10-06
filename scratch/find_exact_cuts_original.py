"""
Comparar ORIGINAL.wav y PREVIA.wav para extraer con precisión milimétrica:
1. ¿En qué segundo de ORIGINAL empieza el bloque 1 y en cuál termina?
2. ¿En qué segundo de ORIGINAL empieza el bloque 2 y en cuál termina?
3. ¿En qué segundo de ORIGINAL empieza el bloque 3 y en cuál termina?
4. ¿Qué son cada una de esas partes en ORIGINAL (subida, drop cargado, etc.)?
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

# Tiempo de PREVIA a 165 BPM. Puntos de corte en PREVIA identificados por transiciones:
# Bloque 1: ~0.0s a ~67.7s
# Bloque 2: ~67.7s a ~117.8s
# Bloque 3: ~117.8s a ~155.5s

# Vamos a encontrar el matching exacto de audio buscando fragmentos representativos
# Para evitar problemas de BPM, busquemos qué trozo de ORIGINAL tiene la misma melodía/armonía
# utilizando Chroma cross-correlation sobre ventanas.

# Extraer chromagramas a 22050 Hz
sr_c = 22050
y_o_22 = librosa.resample(y_orig, orig_sr=sr, target_sr=sr_c)
y_p_22 = librosa.resample(y_prev, orig_sr=sr, target_sr=sr_c)

# Como PREVIA está a 165 BPM y ORIGINAL a 155 BPM (ratio = 165/155 = 1.064516)
# Estiramos y_p_22 a 155 BPM:
y_p_stretch = librosa.effects.time_stretch(y_p_22, rate=155.0/165.0)

hop = 512
chroma_o = librosa.feature.chroma_cqt(y=y_o_22, sr=sr_c, hop_length=hop)
chroma_p = librosa.feature.chroma_cqt(y=y_p_stretch, sr=sr_c, hop_length=hop)

# Matriz de similitud coseno entre frames de PREVIA estirada y frames de ORIGINAL
# chroma_o: (12, T_o), chroma_p: (12, T_p)
norm_o = np.linalg.norm(chroma_o, axis=0, keepdims=True) + 1e-6
norm_p = np.linalg.norm(chroma_p, axis=0, keepdims=True) + 1e-6

chroma_o_norm = chroma_o / norm_o
chroma_p_norm = chroma_p / norm_p

# Puntos de corte en PREVIA (en segundos de PREVIA estirada a 155 BPM):
# PREVIA dura 155.5s a 165 BPM -> a 155 BPM dura 155.5 * (165/155) = 165.53s
# Corte 1: 67.69s * (165/155) = 72.06s
# Corte 2: 117.84s * (165/155) = 125.44s
# Fin: 155.5s * (165/155) = 165.53s

print(f"Duración total ORIGINAL: {len(y_orig)/sr:.2f}s")
print(f"Duración total PREVIA a 155 BPM: {len(y_p_stretch)/sr_c:.2f}s")

# Busquemos trozos de 10 segundos en cada bloque:
# Bloque 1: prueba en t=30s (de PREVIA estirada)
# Bloque 2: prueba en t=90s (de PREVIA estirada)
# Bloque 3: prueba en t=140s (de PREVIA estirada)

def find_best_match(t_prev_155, win_sec=6.0):
    f_p = int(t_prev_155 * sr_c / hop)
    w_f = int(win_sec * sr_c / hop)
    sub_p = chroma_p_norm[:, f_p:f_p+w_f]
    
    # Correlación sobre todo chroma_o_norm
    n_o = chroma_o_norm.shape[1] - w_f + 1
    scores = np.zeros(n_o)
    for i in range(n_o):
        scores[i] = np.sum(chroma_o_norm[:, i:i+w_f] * sub_p) / w_f
        
    best_f = np.argmax(scores)
    best_t_o = best_f * hop / sr_c
    return best_t_o, scores[best_f]

for test_t, label in [(10.0, "Bloque 1 Intro"), (20.0, "Bloque 1 Subida"), (45.0, "Bloque 1 Drop"),
                      (78.0, "Bloque 2 Subida"), (95.0, "Bloque 2 Drop"),
                      (130.0, "Bloque 3 Subida"), (145.0, "Bloque 3 Drop")]:
    best_t_o, score = find_best_match(test_t, win_sec=8.0)
    print(f"PREVIA (a 155) {test_t:5.1f}s ({label:18s}) -> ORIGINAL en {best_t_o:6.2f}s ({int(best_t_o//60)}:{int(best_t_o%60):02d}) [score={score:.3f}]")

