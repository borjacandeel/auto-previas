"""
Descubrir exactamente qué partes de ORIGINAL.wav componen PREVIA.wav.
Analizamos:
Bloque 1: 0.0s -> 67.7s de PREVIA
Bloque 2: 67.7s -> 117.8s de PREVIA
Bloque 3: 117.8s -> 155.5s de PREVIA
"""

import numpy as np
import soundfile as sf
import librosa

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

sr = 22050
y_orig, _ = librosa.load(orig_path, sr=sr, mono=True)
y_prev, _ = librosa.load(prev_path, sr=sr, mono=True)

# Vamos a extraer trozos de audio representativos de PREVIA:
# 1. Trozo del Bloque 1 (por ejemplo de 30s a 40s de PREVIA, que está en pleno Drop 1)
# 2. Trozo del Bloque 2 (por ejemplo de 90s a 100s de PREVIA, que está en pleno Drop 2)
# 3. Trozo del Bloque 3 (por ejemplo de 135s a 145s de PREVIA, que está en pleno Drop 3)

# Pero primero, verifiquemos si PREVIA tiene PITCH SHIFT o TIME STRETCH o VARISPEED
# Tomemos un espectrograma de alta resolución FFT de un sinte sostenido o nota fija
# en ORIGINAL y en PREVIA para ver si la frecuencia fundamental ha cambiado.

print("--- ANÁLISIS DE PITCH Y VELOCIDAD ---")
# Comparemos el inicio (0 a 10s)
# Calculamos CQT (Constant-Q Transform) que mide directamente notas musicales
cqt_o = np.abs(librosa.cqt(y_orig[int(2*sr):int(10*sr)], sr=sr))
cqt_p = np.abs(librosa.cqt(y_prev[int(2*sr):int(10*sr)], sr=sr))

# Promedio espectral por frecuencias
spec_o = cqt_o.mean(axis=1)
spec_p = cqt_p.mean(axis=1)

# Correlación de CQT para ver desfase en semitonos (cada bin de CQT son 12 bins por octava = 1 bin por semitono si bins_per_octave=12)
cqt_o_12 = np.abs(librosa.cqt(y_orig[int(5*sr):int(12*sr)], sr=sr, bins_per_octave=12))
cqt_p_12 = np.abs(librosa.cqt(y_prev[int(5*sr):int(12*sr)], sr=sr, bins_per_octave=12))

chroma_o = librosa.feature.chroma_cqt(C=cqt_o_12)
chroma_p = librosa.feature.chroma_cqt(C=cqt_p_12)

mean_chroma_o = chroma_o.mean(axis=1)
mean_chroma_p = chroma_p.mean(axis=1)

print("Chroma perfil ORIGINAL:", np.round(mean_chroma_o, 2))
print("Chroma perfil PREVIA:  ", np.round(mean_chroma_p, 2))

# Ver si hay rotación de semitonos
best_shift = 0
best_corr = -1
for shift in range(12):
    corr = np.corrcoef(mean_chroma_o, np.roll(mean_chroma_p, -shift))[0, 1]
    if corr > best_corr:
        best_corr = corr
        best_shift = shift

print(f"Mejor coincidencia de tono: shift de {best_shift} semitonos (corr={best_corr:.3f})")
if best_shift == 0 or best_corr > 0.95:
    print("-> El pitch tonal es IDENTICO (Keylock preservado o mismo semitono).")
else:
    print(f"-> Hay un pitch shift de {best_shift} semitonos.")

