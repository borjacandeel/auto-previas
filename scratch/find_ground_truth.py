"""
Encontrar exactamente qué compases de ORIGINAL.wav están en PREVIA.wav.
Usamos onset detection y envelopes a la misma frecuencia de muestreo.
"""

import numpy as np
import soundfile as sf
import librosa
from scipy.signal import correlate

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

y_orig, sr = sf.read(orig_path)
y_prev, _ = sf.read(prev_path)

if y_orig.ndim > 1: y_orig = y_orig.mean(axis=1)
if y_prev.ndim > 1: y_prev = y_prev.mean(axis=1)

# Envolvente RMS en ventanas de 100ms
hop = 512
sr_r = 22050
y_o = librosa.resample(y_orig, orig_sr=sr, target_sr=sr_r)
y_p = librosa.resample(y_prev, orig_sr=sr, target_sr=sr_r)

# PREVIA está acelerada un factor exacto: 165.0 / 155.0 = 1.064516
# Para buscar en ORIGINAL, desaceleramos PREVIA a 155 BPM:
y_p_155 = librosa.effects.time_stretch(y_p, rate=155.0/165.0)

# Calculemos el onset envelope de ambos
onset_o = librosa.onset.onset_strength(y=y_o, sr=sr_r, hop_length=hop)
onset_p = librosa.onset.onset_strength(y=y_p_155, sr=sr_r, hop_length=hop)

# Calculemos RMS de ambos
rms_o = librosa.feature.rms(y=y_o, frame_length=1024, hop_length=hop)[0]
rms_p = librosa.feature.rms(y=y_p_155, frame_length=1024, hop_length=hop)[0]

# Combinar onset + rms como huella rítmico-dinámica
fp_o = (onset_o - onset_o.mean()) / (onset_o.std() + 1e-6) + (rms_o - rms_o.mean()) / (rms_o.std() + 1e-6)
fp_p = (onset_p - onset_p.mean()) / (onset_p.std() + 1e-6) + (rms_p - rms_p.mean()) / (rms_p.std() + 1e-6)

print(f"Duración frames ORIGINAL: {len(fp_o)} ({len(y_o)/sr_r:.2f}s)")
print(f"Duración frames PREVIA_155: {len(fp_p)} ({len(y_p_155)/sr_r:.2f}s)")

# En PREVIA a 165 BPM, los cortes están en:
# Bloque 1: 0.0s -> ~67.7s (en PREVIA_155: 0.0s -> 72.1s)
# Bloque 2: 67.7s -> ~117.8s (en PREVIA_155: 72.1s -> 125.4s)
# Bloque 3: 117.8s -> ~155.5s (en PREVIA_155: 125.4s -> 165.5s)

def match_window(t_p_start, dur_sec):
    f_start = int(t_p_start * sr_r / hop)
    f_len = int(dur_sec * sr_r / hop)
    pat = fp_p[f_start:f_start + f_len]
    
    corr = correlate(fp_o, pat, mode='valid')
    best_f = np.argmax(corr)
    t_orig = best_f * hop / sr_r
    score = corr[best_f] / f_len
    return t_orig, score

print("\n--- BUSCANDO COINCIDENCIAS DE PREVIA EN ORIGINAL ---")
# Bloque 1 (inicio, subida, drop)
for t_p, dur, desc in [
    (2.0, 6.0, "Bloque 1 Inicio"),
    (18.0, 6.0, "Bloque 1 Subida (prev 16.9s)"),
    (30.0, 10.0, "Bloque 1 Drop parte 1"),
    (50.0, 10.0, "Bloque 1 Drop parte 2"),
    (75.0, 6.0, "Bloque 2 Subida (prev 70.4s)"),
    (85.0, 10.0, "Bloque 2 Drop parte 1"),
    (105.0, 10.0, "Bloque 2 Drop parte 2"),
    (130.0, 6.0, "Bloque 3 Subida (prev 122.0s)"),
    (140.0, 10.0, "Bloque 3 Drop parte 1"),
    (155.0, 8.0, "Bloque 3 Drop parte 2")
]:
    t_o, sc = match_window(t_p, dur)
    print(f"PREVIA_155 t={t_p:5.1f}s ({desc:30s}) -> ORIGINAL en {t_o:6.2f}s ({int(t_o//60)}:{int(t_o%60):02d}) [score={sc:6.2f}]")
