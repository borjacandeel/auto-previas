"""
Inspección auditiva y espectral precisa para determinar la relación exacta:
¿Tiene PREVIA variación de tempo? ¿Es varispeed (pitch y tempo suben juntos)?
¿O qué algoritmo usó?
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

print(f"Longitud ORIGINAL: {len(y_orig)/48000:.3f}s")
print(f"Longitud PREVIA:   {len(y_prev)/48000:.3f}s")

# Miremos el inicio de PREVIA (0s a 15s)
# Calculemos el tempo local a lo largo de PREVIA
tempo_prev_dyn = librosa.feature.tempo(y=y_prev, sr=48000, aggregate=None)
print("Tempo local dinámico en PREVIA (primeros 20 frames):", np.round(tempo_prev_dyn[:20], 1))
print("Tempo local dinámico en PREVIA (frames medios):", np.round(tempo_prev_dyn[len(tempo_prev_dyn)//2 : len(tempo_prev_dyn)//2 + 20], 1))
print("Tempo local dinámico en PREVIA (últimos 20 frames):", np.round(tempo_prev_dyn[-20:], 1))

tempo_orig_dyn = librosa.feature.tempo(y=y_orig, sr=48000, aggregate=None)
print("\nTempo local dinámico en ORIGINAL (primeros 20 frames):", np.round(tempo_orig_dyn[:20], 1))
print("Tempo local dinámico en ORIGINAL (frames medios):", np.round(tempo_orig_dyn[len(tempo_orig_dyn)//2 : len(tempo_orig_dyn)//2 + 20], 1))

# Miremos onsets en los primeros 10s de ambos
onsets_p = librosa.onset.onset_detect(y=y_prev[:48000*15], sr=48000, units='time')
print("\nOnsets primeros 15s de PREVIA:")
print(np.round(onsets_p, 3))
intervals_p = np.diff(onsets_p)
print("Intervalos entre onsets PREVIA:", np.round(intervals_p, 3))

onsets_o = librosa.onset.onset_detect(y=y_orig[:48000*15], sr=48000, units='time')
print("\nOnsets primeros 15s de ORIGINAL:")
print(np.round(onsets_o, 3))
intervals_o = np.diff(onsets_o)
print("Intervalos entre onsets ORIGINAL:", np.round(intervals_o, 3))

# Verifiquemos si el inicio de PREVIA coincide con alguna parte de ORIGINAL
# Usando cross-correlation normalizada de envolvente de energía (RMS)
rms_p = librosa.feature.rms(y=y_prev, frame_length=2048, hop_length=512)[0]
rms_o = librosa.feature.rms(y=y_orig, frame_length=2048, hop_length=512)[0]

print(f"\nRMS shape PREVIA: {len(rms_p)}, ORIGINAL: {len(rms_o)}")
