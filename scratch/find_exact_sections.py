"""
Encontrar exactamente qué compases / segundos de ORIGINAL.wav componen PREVIA.wav.
"""

import numpy as np
import soundfile as sf
import librosa

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

sr = 22050
y_orig, _ = librosa.load(orig_path, sr=sr, mono=True)
y_prev, _ = librosa.load(prev_path, sr=sr, mono=True)

# Ralentizar PREVIA a 155 BPM con time_stretch para que coincida exactamente con ORIGINAL en tiempo y pitch
tempo_orig = 155.0
# Encontramos la tasa exacta de estiramiento:
# En los primeros 10s: intervalo medio orig = 0.19355s (155.0 BPM, beat = 0.3871s, semicorchea = 0.0968s)
# PREVIA intervalo medio = 0.18182s (165.0 BPM, beat = 0.3636s)
rate = 155.0 / 165.0
y_prev_155 = librosa.effects.time_stretch(y_prev, rate=rate)

dur_orig = len(y_orig) / sr
dur_prev = len(y_prev) / sr
dur_prev_155 = len(y_prev_155) / sr

print(f"Duración ORIGINAL: {dur_orig:.2f}s")
print(f"Duración PREVIA (165 BPM): {dur_prev:.2f}s")
print(f"Duración PREVIA estirada (155 BPM): {dur_prev_155:.2f}s")

# Extraer CQT de ambos
hop = 512
cqt_orig = np.abs(librosa.cqt(y_orig, sr=sr, hop_length=hop, n_bins=60, bins_per_octave=12))
cqt_prev = np.abs(librosa.cqt(y_prev_155, sr=sr, hop_length=hop, n_bins=60, bins_per_octave=12))

# Ventanas de 2 segundos a 155 BPM
win_frames = int(2.0 * sr / hop)
step_frames = int(0.5 * sr / hop)

trajectory = []
for p_f in range(0, cqt_prev.shape[1] - win_frames, step_frames):
    chunk = cqt_prev[:, p_f:p_f + win_frames]
    chunk_norm = np.linalg.norm(chunk)
    if chunk_norm < 1e-4:
        continue
    
    # Calcular correlación cruzada en el tiempo con cqt_orig
    # Multiplicación matricial rápida
    # cqt_orig: [n_bins, T_orig], chunk: [n_bins, win_frames]
    # Sum over bins de conv(cqt_orig[b], chunk[b])
    corrs = np.zeros(cqt_orig.shape[1] - win_frames + 1)
    for b in range(cqt_orig.shape[0]):
        corrs += np.correlate(cqt_orig[b], chunk[b], mode='valid')
        
    best_orig_f = np.argmax(corrs)
    max_corr = corrs[best_orig_f] / chunk_norm
    
    t_prev_155 = p_f * hop / sr
    t_prev_real = t_prev_155 * (155.0 / 165.0)
    t_orig = best_orig_f * hop / sr
    
    trajectory.append((t_prev_real, t_prev_155, t_orig, max_corr))

# Imprimir trajectory muestreada cada 2 segundos de PREVIA
print("\n--- PUNTOS DE CORRELACIÓN EN TIEMPO ---")
for t_pr, t_p155, t_o, corr in trajectory[::4]:
    print(f"PREVIA: {t_pr:5.1f}s (a 155: {t_p155:5.1f}s) -> ORIGINAL: {t_o:6.2f}s ({int(t_o//60)}:{int(t_o%60):02d}) [corr={corr:6.1f}]")
