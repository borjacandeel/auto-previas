"""
Verificar si PREVIA.wav son exactamente los 3 bloques principales de ORIGINAL:
Bloque 1: Intro/Buildup 1 + Drop 1
Bloque 2: Buildup 2 (169.2s) + Drop 2 (178.5s)
Bloque 3: Buildup 3 (260.5s) + Drop 3 (269.8s)
"""

import numpy as np
import soundfile as sf
import librosa

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

y_o, sr = sf.read(orig_path)
y_p, _ = sf.read(prev_path)
if y_o.ndim > 1: y_o = y_o.mean(axis=1)
if y_p.ndim > 1: y_p = y_p.mean(axis=1)

# Analizar con mayor resolución de tiempo
# En PREVIA a 165 BPM:
# Bloque 1 termina en 67.69s (a 155 BPM = 72.06s)
# Bloque 2 dura de 67.69s a 117.84s (duración 50.15s; a 155 BPM = 53.39s)
#   Buildup 2 en PREVIA: 67.69s a 76.74s (9.05s a 165 BPM = 9.64s a 155 BPM)
#   Drop 2 en PREVIA: 76.74s a 117.84s (41.10s a 165 BPM = 43.75s a 155 BPM)
# Bloque 3 dura de 117.84s a 155.50s (duración 37.66s; a 155 BPM = 40.10s)
#   Buildup 3 en PREVIA: 117.84s a 126.64s (8.80s a 165 BPM = 9.37s a 155 BPM)
#   Drop 3 en PREVIA: 126.64s a 155.50s (28.86s a 165 BPM = 30.73s a 155 BPM)

# En ORIGINAL:
# Buildup 2 está en: 169.20s -> 178.49s (duración = 9.29s!)
# Si a 178.49s le sumamos 43.75s = 222.24s
# Buildup 3 está en: 260.55s -> 269.86s (duración = 9.31s!)
# Si a 269.86s le sumamos 30.73s = 300.59s

print("--- COMPROBACIÓN AUDITIVA / MATRICIAL DE LOS TRAMOS ---")

# Comparemos el inicio del Drop 2 en PREVIA (t=76.74s a 86.74s)
# con el Drop 2 en ORIGINAL (t=178.49s a 188.49s):
sr_test = 22050
y_p_test = librosa.resample(y_p, orig_sr=sr, target_sr=sr_test)
y_o_test = librosa.resample(y_o, orig_sr=sr, target_sr=sr_test)

# Estirar PREVIA a 155 BPM
y_p_155 = librosa.effects.time_stretch(y_p_test, rate=155.0/165.0)

# Fragmento Drop 2 en PREVIA (a 155 BPM):
# En PREVIA_155, el Drop 2 empieza en 76.74 * (165/155) = 81.69s
f_p_d2 = y_p_155[int(81.69*sr_test) : int(91.69*sr_test)]
# Fragmento Drop 2 en ORIGINAL:
f_o_d2 = y_o_test[int(178.49*sr_test) : int(188.49*sr_test)]

# Fragmento Drop 3 en PREVIA (a 155 BPM):
# En PREVIA_155, el Drop 3 empieza en 126.64 * (165/155) = 134.81s
f_p_d3 = y_p_155[int(134.81*sr_test) : int(144.81*sr_test)]
# Fragmento Drop 3 en ORIGINAL:
f_o_d3 = y_o_test[int(269.86*sr_test) : int(279.86*sr_test)]

# Correlación espectral
cqt_p_d2 = np.abs(librosa.cqt(f_p_d2, sr=sr_test))
cqt_o_d2 = np.abs(librosa.cqt(f_o_d2, sr=sr_test))
corr_d2 = np.corrcoef(cqt_p_d2.flatten(), cqt_o_d2.flatten())[0, 1]

cqt_p_d3 = np.abs(librosa.cqt(f_p_d3, sr=sr_test))
cqt_o_d3 = np.abs(librosa.cqt(f_o_d3, sr=sr_test))
corr_d3 = np.corrcoef(cqt_p_d3.flatten(), cqt_o_d3.flatten())[0, 1]

print(f"Correlación Drop 2 (PREVIA vs ORIGINAL 178.49s): {corr_d2:.4f}")
print(f"Correlación Drop 3 (PREVIA vs ORIGINAL 269.86s): {corr_d3:.4f}")

# Ahora comprobemos Bloque 1:
# ¿Dónde empieza el Drop 1 de PREVIA? En PREVIA_155 empieza en 24.80 * (165/155) = 26.40s
f_p_d1 = y_p_155[int(26.40*sr_test) : int(36.40*sr_test)]
# ¿Coincide con Drop [04] en ORIGINAL (43.40s)?
f_o_d1_a = y_o_test[int(43.40*sr_test) : int(53.40*sr_test)]
# ¿O coincide con Drop [01] en ORIGINAL (12.42s)?
f_o_d1_b = y_o_test[int(12.42*sr_test) : int(22.42*sr_test)]

cqt_p_d1 = np.abs(librosa.cqt(f_p_d1, sr=sr_test))
cqt_o_d1_a = np.abs(librosa.cqt(f_o_d1_a, sr=sr_test))
cqt_o_d1_b = np.abs(librosa.cqt(f_o_d1_b, sr=sr_test))

corr_d1_a = np.corrcoef(cqt_p_d1.flatten(), cqt_o_d1_a.flatten())[0, 1]
corr_d1_b = np.corrcoef(cqt_p_d1.flatten(), cqt_o_d1_b.flatten())[0, 1]

print(f"Correlación Drop 1 con ORIGINAL 43.40s (Drop 4): {corr_d1_a:.4f}")
print(f"Correlación Drop 1 con ORIGINAL 12.42s (Drop 1): {corr_d1_b:.4f}")

# ¿Y el inicio de Bloque 1 (0 a 16s en PREVIA)?
f_p_intro = y_p_155[int(2.0*sr_test) : int(12.0*sr_test)]
f_o_intro = y_o_test[int(2.0*sr_test) : int(12.0*sr_test)]
corr_intro = np.corrcoef(np.abs(librosa.cqt(f_p_intro, sr=sr_test)).flatten(), np.abs(librosa.cqt(f_o_intro, sr=sr_test)).flatten())[0, 1]
print(f"Correlación Intro con ORIGINAL 0.0s: {corr_intro:.4f}")
