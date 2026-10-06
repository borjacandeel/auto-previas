import numpy as np
import soundfile as sf
import librosa
import scipy.signal

def main():
    print("Cargando audios a 11025 Hz...")
    sr_target = 11025
    y_o, sr = librosa.load("ejemplos/ORIGINAL 2.flac", sr=sr_target, mono=True)
    y_p, _ = librosa.load("ejemplos/PREVIA 2.wav", sr=sr_target, mono=True)
    
    # Previa 2 acelerada: ratio ~1.0765
    ratio = 183.0 / 170.0
    # Des-aceleramos previa 2 para alinearla al tiempo del original
    y_p_orig_speed = scipy.signal.resample(y_p, int(len(y_p) * ratio))
    print(f"Duración original: {len(y_o)/sr_target:.2f}s, Previa des-acelerada: {len(y_p_orig_speed)/sr_target:.2f}s")
    
    # Extraer espectrogramas de potencia o onset envelopes
    hop = 256
    env_o = librosa.onset.onset_strength(y=y_o, sr=sr_target, hop_length=hop)
    env_p = librosa.onset.onset_strength(y=y_p_orig_speed, sr=sr_target, hop_length=hop)
    
    # También RMS de kick/bass para matching robusto
    win_f = int(3.0 * sr_target / hop) # ventanas de 3s
    step_f = int(0.5 * sr_target / hop) # paso de 0.5s
    
    print("Mapeando segundos de la previa al original...")
    mappings = []
    
    for p_start in range(0, len(env_p) - win_f, step_f):
        clip = env_p[p_start : p_start + win_f]
        clip_norm = clip - np.mean(clip)
        norm_val = np.linalg.norm(clip_norm)
        if norm_val < 1e-4:
            continue
            
        corr = scipy.signal.correlate(env_o, clip_norm, mode='valid')
        best_idx = np.argmax(corr)
        
        t_previa = (p_start * hop) / (sr_target * ratio) # tiempo real en PREVIA 2
        t_orig = (best_idx * hop) / sr_target            # tiempo en ORIGINAL 2
        score = corr[best_idx] / norm_val
        mappings.append((t_previa, t_orig, score))
        
    # Agrupar tramos continuos
    print("\nTramos continuos identificados:")
    segments = []
    current_start_p = mappings[0][0]
    current_start_o = mappings[0][1]
    last_p = mappings[0][0]
    last_o = mappings[0][1]
    
    for p, o, sc in mappings[1:]:
        expected_o = last_o + (p - last_p) * ratio
        diff = o - expected_o
        if abs(diff) > 3.0: # Discontinuidad de más de 3 segundos
            # Fin del tramo
            dur_p = last_p - current_start_p
            dur_o = last_o - current_start_o
            segments.append((current_start_p, last_p, current_start_o, last_o, dur_p, dur_o))
            current_start_p = p
            current_start_o = o
        last_p = p
        last_o = o
        
    dur_p = last_p - current_start_p
    dur_o = last_o - current_start_o
    segments.append((current_start_p, last_p, current_start_o, last_o, dur_p, dur_o))
    
    for i, (sp, ep, so, eo, dp, do) in enumerate(segments):
        if dp > 4.0: # filtrar ruido
            print(f"Bloque {i+1}:")
            print(f"  En PREVIA 2:   {sp:6.1f}s -> {ep:6.1f}s (duración: {dp:5.1f}s)")
            print(f"  En ORIGINAL 2: {so:6.1f}s -> {eo:6.1f}s (duración: {do:5.1f}s)")

if __name__ == "__main__":
    main()
