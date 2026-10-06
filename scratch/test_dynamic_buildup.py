"""
Algoritmo de detección acústica dinámica de subidas (cortas o largas),
drops reales y descansos melódicos.
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

sr_ana = 22050
y_ana = librosa.resample(y, orig_sr=sr, target_sr=sr_ana)
hop = 512

import scipy.signal
# 1. Bombo/Sub (40 - 130 Hz)
sos_kick = scipy.signal.butter(4, [40, 130], btype="bandpass", fs=sr_ana, output="sos")
y_kick = scipy.signal.sosfilt(sos_kick, y_ana)
rms_kick = librosa.feature.rms(y=y_kick, frame_length=2048, hop_length=hop)[0]
rms_kick = rms_kick / (rms_kick.max() + 1e-6)

# 2. Medios/Melodía (350 - 3500 Hz)
sos_mid = scipy.signal.butter(4, [350, 3500], btype="bandpass", fs=sr_ana, output="sos")
y_mid = scipy.signal.sosfilt(sos_mid, y_ana)
rms_mid = librosa.feature.rms(y=y_mid, frame_length=2048, hop_length=hop)[0]
rms_mid = rms_mid / (rms_mid.max() + 1e-6)

# 3. Agudos/Risers/Pitos (2500 - 9000 Hz)
sos_high = scipy.signal.butter(4, [2500, 9000], btype="bandpass", fs=sr_ana, output="sos")
y_high = scipy.signal.sosfilt(sos_high, y_ana)
rms_high = librosa.feature.rms(y=y_high, frame_length=2048, hop_length=hop)[0]
rms_high = rms_high / (rms_high.max() + 1e-6)

# 4. RMS global
rms_global = librosa.feature.rms(y=y_ana, frame_length=2048, hop_length=hop)[0]
rms_global = rms_global / (rms_global.max() + 1e-6)

# 5. Centroide espectral normalizado
spec_cent = librosa.feature.spectral_centroid(y=y_ana, sr=sr_ana, hop_length=hop)[0]
spec_cent_norm = (spec_cent - spec_cent.min()) / (spec_cent.max() - spec_cent.min() + 1e-6)

# Onset strength
onset_env = librosa.onset.onset_strength(y=y_ana, sr=sr_ana, hop_length=hop)
onset_norm = (onset_env - onset_env.min()) / (onset_env.max() - onset_env.min() + 1e-6)

# Compás a compás
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

# Carga tímbrica y plenitud
b_leads = 0.55 * b_mid + 0.45 * b_high
b_fullness = 0.35 * b_kick + 0.35 * b_rms + 0.30 * b_leads

# Pendientes de subida
slope_high = np.gradient(gaussian_filter1d(b_high, 1.0))
slope_bright = np.gradient(gaussian_filter1d(b_bright, 1.0))
slope_rms = np.gradient(gaussian_filter1d(b_rms, 1.0))

print("=== CLASIFICACIÓN AVANZADA ===")

# 1. Detectar compases de DROP
# Drop = Bombo contundente + RMS alto + Carga melódica/leads real
is_drop = (b_kick >= 0.42) & (b_rms >= 0.40) & ((b_leads >= 0.20) | (b_fullness >= 0.48))

# Excluir intro DJ mix beat (los primeros compases con bombos pero sin subida ni melodía plena)
for b in range(min(25, n_bars)):
    if b / n_bars < 0.15 and (b_leads[b] < 0.35 or b_fullness[b] < 0.52):
        is_drop[b] = False

# Puenteo de fills/turnarounds (1 o 2 compases dentro de un drop)
bridged_drop = np.copy(is_drop)
for b in range(1, n_bars - 2):
    if not bridged_drop[b] and bridged_drop[b-1]:
        if bridged_drop[b+1] or (b < n_bars-2 and bridged_drop[b+2]):
            bridged_drop[b] = True
            if b < n_bars-2 and bridged_drop[b+2]:
                bridged_drop[b+1] = True

# Filtrar ráfagas de drop < 6 compases (deben durar al menos 6-8 compases para ser drops reales)
runs = []
cur_v = bridged_drop[0]
cur_l = 1
for b in range(1, n_bars):
    if bridged_drop[b] == cur_v:
        cur_l += 1
    else:
        runs.append((cur_v, cur_l))
        cur_v = bridged_drop[b]
        cur_l = 1
runs.append((cur_v, cur_l))

clean_drop = []
for v, l in runs:
    if v and l < 6:
        clean_drop.extend([False] * l)
    else:
        clean_drop.extend([v] * l)
clean_drop = np.array(clean_drop)

# 2. Localizar cada Drop y detectar DINÁMICAMENTE la duración exacta de su SUBIDA previa
drop_starts = []
for b in range(1, n_bars):
    if clean_drop[b] and not clean_drop[b - 1]:
        drop_starts.append(b)

print(f"Inicios de Drop detectados en compases: {drop_starts}")

def detect_dynamic_buildup(drop_bar, max_lookback=16):
    """
    Rastrea hacia atrás desde drop_bar para encontrar la duración REAL de la subida:
    - Puede ser corta (2 compases, 4 compases) o larga (6, 8, 12, 16 compases).
    - Criterios de subida:
      * Pendiente positiva de agudos (slope_high > 0) o brillo creciente (slope_bright > 0).
      * Presencia de redobles o risers (b_high > 0.25).
      * Bombo ausente o atenuado (b_kick < 0.40).
      * RMS creciente hacia el drop.
    """
    # Empezamos desde el compás inmediatamente anterior al drop (drop_bar - 1)
    bu_bars = 0
    for look in range(1, min(max_lookback + 1, drop_bar)):
        bar = drop_bar - look
        if clean_drop[bar]: # Chocamos con un drop anterior
            break
            
        k = b_kick[bar]
        h = b_high[bar]
        br = b_bright[bar]
        sh = slope_high[bar]
        sb = slope_bright[bar]
        sr = slope_rms[bar]
        
        # ¿Tiene características de subida / riser / redoble?
        is_buildup_bar = False
        # Caso A: Riser o filtro abriéndose claramente
        if (sh > 0.015 or sb > 0.015 or sr > 0.02) and k < 0.42:
            is_buildup_bar = True
        # Caso B: Agudos/leads altos con bombo reducido justo antes del drop (últimos compases del riser)
        elif h >= 0.25 and k < 0.35 and look <= 8:
            is_buildup_bar = True
        # Caso C: Redoble potente de caja/snare (onset alto + mid/high)
        elif b_onset[bar] > 0.35 and k < 0.42 and look <= 8:
            is_buildup_bar = True
            
        if is_buildup_bar:
            bu_bars = look
        else:
            # Si encontramos 2 compases seguidos sin subida, paramos
            if look > 2:
                break
                
    # Si detectó una subida pero no es múltiplo estándar, podemos redondear a 2, 4, 6, 8, 12, 16 compases
    # Mínimo si hay subida: 2 compases. Si no detectó nada obvio pero hay descanso antes: fallback 4 compases
    if bu_bars == 0:
        bu_bars = min(4, drop_bar)
    elif bu_bars in (1, 3):
        bu_bars += 1 # ajustar a compás par (2, 4, 6...)
        
    return bu_bars

print("\n--- ANÁLISIS DINÁMICO DE SUBIDAS PARA CADA DROP ---")
for idx, d_bar in enumerate(drop_starts):
    bu_len = detect_dynamic_buildup(d_bar)
    bu_start_bar = d_bar - bu_len
    t_bu_s = beats[bu_start_bar * 4]
    t_d_s = beats[d_bar * 4]
    dur_bu = t_d_s - t_bu_s
    
    # Clasificación de tipo de subida:
    if bu_len <= 3:
        bu_type = f"CORTA ({bu_len} compases, {dur_bu:.1f}s)"
    elif bu_len <= 6:
        bu_type = f"ESTÁNDAR ({bu_len} compases, {dur_bu:.1f}s)"
    else:
        bu_type = f"LARGA ({bu_len} compases, {dur_bu:.1f}s)"
        
    print(f"Drop #{idx+1} en {t_d_s:6.2f}s (Compás {d_bar:3d}) -> Subida {bu_type}: Compás {bu_start_bar:3d}..{d_bar:3d} [{t_bu_s:6.2f}s -> {t_d_s:6.2f}s]")

