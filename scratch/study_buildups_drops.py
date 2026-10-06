"""
Estudio acústico profundo de ORIGINAL.wav:
Analizar bar a bar para detectar con precisión física y musical:
1. Subidas (buildups): pendientes de energía, centroide espectral creciente, redobles, risers.
   Determinar duración real dinámica (corta vs larga: 2, 4, 6, 8, 12, 16 compases).
2. Drops reales: estallido de bombo + plenitud tímbrica + espectro completo.
3. Descansos (breakdowns): melodía/sintes sin bombo, sin pendiente de subida.
4. Bases de mezcla (intro/outro): bombos vacíos sin melodía ni carga.
"""

import numpy as np
import soundfile as sf
import librosa
from scipy.ndimage import gaussian_filter1d
from src.analysis.bpm import detect_beat_grid

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
y, sr = sf.read(orig_path)
if y.ndim > 1: y = y.mean(axis=1)

grid = detect_beat_grid(y, sr)
bpm = grid.bpm
beats = grid.beat_times
n_beats = len(beats)
n_bars = n_beats // 4
bar_dur = 4.0 * (60.0 / bpm)

print(f"Pista: {len(y)/sr:.2f}s, BPM: {bpm:.1f}, Compases totales: {n_bars}, Duración compás: {bar_dur:.3f}s\n")

# Extraer señales separadas en bandas
sr_ana = 22050
y_ana = librosa.resample(y, orig_sr=sr, target_sr=sr_ana)

hop = 512
# 1. Banda sub/kick (40 - 130 Hz)
import scipy.signal
sos_kick = scipy.signal.butter(4, [40, 130], btype="bandpass", fs=sr_ana, output="sos")
y_kick = scipy.signal.sosfilt(sos_kick, y_ana)
rms_kick = librosa.feature.rms(y=y_kick, frame_length=2048, hop_length=hop)[0]
rms_kick = rms_kick / (rms_kick.max() + 1e-6)

# 2. Banda de medios/melodía/voces (300 - 3000 Hz)
sos_mid = scipy.signal.butter(4, [300, 3000], btype="bandpass", fs=sr_ana, output="sos")
y_mid = scipy.signal.sosfilt(sos_mid, y_ana)
rms_mid = librosa.feature.rms(y=y_mid, frame_length=2048, hop_length=hop)[0]
rms_mid = rms_mid / (rms_mid.max() + 1e-6)

# 3. Banda de agudos/leads/pitos/risers (2500 - 9000 Hz)
sos_high = scipy.signal.butter(4, [2500, 9000], btype="bandpass", fs=sr_ana, output="sos")
y_high = scipy.signal.sosfilt(sos_high, y_ana)
rms_high = librosa.feature.rms(y=y_high, frame_length=2048, hop_length=hop)[0]
rms_high = rms_high / (rms_high.max() + 1e-6)

# 4. RMS global
rms_global = librosa.feature.rms(y=y_ana, frame_length=2048, hop_length=hop)[0]
rms_global = rms_global / (rms_global.max() + 1e-6)

# 5. Centroide espectral (brillo / apertura de filtros)
spec_cent = librosa.feature.spectral_centroid(y=y_ana, sr=sr_ana, hop_length=hop)[0]
spec_cent_norm = (spec_cent - spec_cent.min()) / (spec_cent.max() - spec_cent.min() + 1e-6)

# 6. Flujo espectral (spectral flux) y Onset density (para detectar redobles acelerados)
onset_env = librosa.onset.onset_strength(y=y_ana, sr=sr_ana, hop_length=hop)
onset_norm = (onset_env - onset_env.min()) / (onset_env.max() - onset_env.min() + 1e-6)

# Calcular métricas compás a compás
b_kick = np.zeros(n_bars)
b_mid = np.zeros(n_bars)
b_high = np.zeros(n_bars)
b_rms = np.zeros(n_bars)
b_bright = np.zeros(n_bars)
b_onset = np.zeros(n_bars)
b_time = np.zeros(n_bars)

for b in range(n_bars):
    t0 = beats[b * 4]
    t1 = beats[min(n_beats - 1, (b + 1) * 4)]
    f0 = max(0, min(librosa.time_to_frames(t0, sr=sr_ana, hop_length=hop), len(rms_global) - 1))
    f1 = max(f0 + 1, min(librosa.time_to_frames(t1, sr=sr_ana, hop_length=hop), len(rms_global)))
    
    b_kick[b] = np.mean(rms_kick[f0:f1])
    b_mid[b] = np.mean(rms_mid[f0:f1])
    b_high[b] = np.mean(rms_high[f0:f1])
    b_rms[b] = np.mean(rms_global[f0:f1])
    b_bright[b] = np.mean(spec_cent_norm[f0:f1])
    b_onset[b] = np.mean(onset_norm[f0:f1])
    b_time[b] = t0

# Calcular pendientes (derivadas temporales compás a compás)
# En una subida:
# - b_high y b_bright tienen pendiente POSITIVA sostenida (crescendo / riser)
# - b_kick suele caer a cero o estar bajo respecto al drop
# - b_rms crece hacia el final de la subida
slope_high = np.gradient(gaussian_filter1d(b_high, 1.2))
slope_bright = np.gradient(gaussian_filter1d(b_bright, 1.2))
slope_rms = np.gradient(gaussian_filter1d(b_rms, 1.2))

print(f"{'Bar':>4} | {'Tiempo':>6} | {'Kick':>5} {'Mid':>5} {'High':>5} {'RMS':>5} | {'Bright':>6} {'dHigh':>6} {'dBrgt':>6} | Diagnóstico")
print("-" * 75)

for b in range(n_bars):
    t = b_time[b]
    k, m, h, r = b_kick[b], b_mid[b], b_high[b], b_rms[b]
    br = b_bright[b]
    dh = slope_high[b]
    db = slope_bright[b]
    
    diag = []
    # Drop: Bombo fuerte + RMS alto + carga tímbrica (Mid o High)
    if k >= 0.45 and r >= 0.45 and (m >= 0.22 or h >= 0.25):
        diag.append("🔥 DROP")
    elif k >= 0.45 and r < 0.42:
        diag.append("🥁 Base/Bombo solo (sin carga)")
    elif k < 0.30 and (m >= 0.25 or h >= 0.25):
        if dh > 0.015 or db > 0.02 or (h > 0.35 and k < 0.2):
            diag.append("⚡ SUBIDA/RISER")
        else:
            diag.append("🎹 DESCANSO/MELODÍA")
    elif r < 0.25:
        diag.append("Intro/Outro suave")
    else:
        diag.append("Transición/Puente")
        
    tag = " | ".join(diag)
    
    # Imprimir compases clave (donde hay cambios de tag o cada 4 compases)
    if b % 4 == 0 or "SUBIDA" in tag or "DROP" in tag:
        print(f"{b:4d} | {t:6.2f}s | {k:5.2f} {m:5.2f} {h:5.2f} {r:5.2f} | {br:6.2f} {dh:+6.3f} {db:+6.3f} | {tag}")
