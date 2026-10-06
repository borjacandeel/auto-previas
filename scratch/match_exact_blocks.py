"""
Mapeo exacto de PREVIA.wav a ORIGINAL.wav a 155.0 BPM.
Como PREVIA está a 165.0 BPM y ORIGINAL a 155.0 BPM,
resampleamos PREVIA con factor (155.0 / 165.0) para que tengan la MISMA velocidad exacta,
y encontramos los puntos de corte, transiciones y fragmentos exactos.
"""

import numpy as np
import soundfile as sf
import librosa

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"

sr = 22050
y_orig, _ = librosa.load(orig_path, sr=sr, mono=True)
y_prev, _ = librosa.load(prev_path, sr=sr, mono=True)

# PREVIA está acelerada a 165.0 BPM. La ralentizamos a 155.0 BPM:
# Para ralentizarla, la duración se multiplica por (165.0 / 155.0)
y_prev_sync = librosa.resample(y_prev, orig_sr=16500, target_sr=15500)

print(f"y_orig dur: {len(y_orig)/sr:.2f}s")
print(f"y_prev dur: {len(y_prev)/sr:.2f}s")
print(f"y_prev_sync dur: {len(y_prev_sync)/sr:.2f}s")

# Ahora correlacionamos ventanas de 2 segundos de y_prev_sync a lo largo de y_orig
hop = 512
rms_orig = librosa.feature.rms(y=y_orig, frame_length=2048, hop_length=hop)[0]
rms_prev = librosa.feature.rms(y=y_prev_sync, frame_length=2048, hop_length=hop)[0]

# También espectrograma Mel normalizado
mel_orig = librosa.feature.melspectrogram(y=y_orig, sr=sr, n_mels=40, hop_length=hop)
mel_prev = librosa.feature.melspectrogram(y=y_prev_sync, sr=sr, n_mels=40, hop_length=hop)
mel_orig = librosa.power_to_db(mel_orig)
mel_prev = librosa.power_to_db(mel_prev)

win_sec = 3.0
win_frames = int(win_sec * sr / hop)
step_sec = 0.5
step_frames = int(step_sec * sr / hop)

trajectory = [] # (prev_sec_real, orig_sec, corr)

for p_f in range(0, mel_prev.shape[1] - win_frames, step_frames):
    chunk = mel_prev[:, p_f:p_f + win_frames]
    chunk = chunk - chunk.mean()
    chunk_norm = np.linalg.norm(chunk)
    if chunk_norm < 1e-3:
        continue
    chunk = chunk / chunk_norm
    
    # Correlación cruzada 2D
    # Para ser muy rápido: producto con cada posición en mel_orig
    # Vectorizar usando convolución
    n_search = mel_orig.shape[1] - win_frames + 1
    corrs = np.zeros(n_search)
    for m in range(mel_orig.shape[0]):
        # mel_orig row m con chunk row m
        corrs += np.correlate(mel_orig[m] - mel_orig[m].mean(), chunk[m], mode='valid')
    
    best_orig_f = np.argmax(corrs)
    orig_time = best_orig_f * hop / sr
    
    # Tiempo en la previa real (en segundos de PREVIA.wav)
    prev_sync_time = p_f * hop / sr
    prev_real_time = prev_sync_time * (155.0 / 165.0)
    
    trajectory.append((prev_real_time, orig_time, corrs[best_orig_f]))

print("\n--- TRAYECTORIA DE SEGUIMIENTO (PREVIA -> ORIGINAL) ---")
# Agrupar en tramos continuos
blocks = []
current_block = []

for i, (p_t, o_t, c_val) in enumerate(trajectory):
    if not current_block:
        current_block.append((p_t, o_t, c_val))
    else:
        last_p, last_o, _ = current_block[-1]
        delta_p = p_t - last_p
        expected_o = last_o + delta_p
        # Si la pista avanza al mismo ritmo (con margen de 1.2s):
        if abs(o_t - expected_o) < 1.5:
            current_block.append((p_t, o_t, c_val))
        else:
            if len(current_block) >= 3: # al menos 1.5s
                blocks.append(current_block)
            current_block = [(p_t, o_t, c_val)]

if len(current_block) >= 3:
    blocks.append(current_block)

print(f"\nTOTAL BLOQUES CONTINUOS DETECTADOS: {len(blocks)}")
for idx, b in enumerate(blocks):
    p_s, o_s, _ = b[0]
    p_e, o_e, _ = b[-1]
    dur_p = p_e - p_s
    dur_o = o_e - o_s
    print(f"\n🔹 BLOQUE #{idx+1}:")
    print(f"   En PREVIA.wav:   {p_s:6.1f}s -> {p_e:6.1f}s  (Duración previa: {dur_p:5.1f}s)  [{int(p_s//60)}:{int(p_s%60):02d} -> {int(p_e//60)}:{int(p_e%60):02d}]")
    print(f"   En ORIGINAL.wav: {o_s:6.1f}s -> {o_e:6.1f}s  (Duración orig:   {dur_o:5.1f}s)  [{int(o_s//60)}:{int(o_s%60):02d} -> {int(o_e//60)}:{int(o_e%60):02d}]")
