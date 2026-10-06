import numpy as np
import soundfile as sf
import librosa

def analyze():
    print("Cargando audios completos a 22050 Hz mono...")
    y_o, sr = librosa.load("ejemplos/ORIGINAL 2.flac", sr=22050, mono=True)
    y_p, _ = librosa.load("ejemplos/PREVIA 2.wav", sr=22050, mono=True)
    
    dur_o = len(y_o) / sr
    dur_p = len(y_p) / sr
    print(f"Duración Original: {dur_o:.2f}s, Previa: {dur_p:.2f}s")
    
    # Calcular onset strength envelope
    hop_length = 512
    onset_o = librosa.onset.onset_strength(y=y_o, sr=sr, hop_length=hop_length)
    onset_p = librosa.onset.onset_strength(y=y_p, sr=sr, hop_length=hop_length)
    
    # Detectar beats
    tempo_o, _ = librosa.beat.beat_track(onset_envelope=onset_o, sr=sr, hop_length=hop_length)
    tempo_p, _ = librosa.beat.beat_track(onset_envelope=onset_p, sr=sr, hop_length=hop_length)
    tempo_o_val = float(tempo_o[0]) if hasattr(tempo_o, '__len__') else float(tempo_o)
    tempo_p_val = float(tempo_p[0]) if hasattr(tempo_p, '__len__') else float(tempo_p)
    print(f"BPM Original: {tempo_o_val:.1f}, BPM Previa: {tempo_p_val:.1f}")
    speed_ratio = tempo_p_val / tempo_o_val
    print(f"Ratio de aceleración detectado: {speed_ratio:.4f}")
    
    # Calcular MFCC (invariante a volumen y casi invariante a pequeños cambios)
    mfcc_o = librosa.feature.mfcc(y=y_o, sr=sr, n_mfcc=13, hop_length=hop_length)
    mfcc_p = librosa.feature.mfcc(y=y_p, sr=sr, n_mfcc=13, hop_length=hop_length)
    
    # Normalizar MFCCs
    mfcc_o = (mfcc_o - np.mean(mfcc_o, axis=1, keepdims=True)) / (np.std(mfcc_o, axis=1, keepdims=True) + 1e-6)
    mfcc_p = (mfcc_p - np.mean(mfcc_p, axis=1, keepdims=True)) / (np.std(mfcc_p, axis=1, keepdims=True) + 1e-6)
    
    # Mapear cada frame de la previa al frame más cercano del original
    # Para tener en cuenta la diferencia de velocidad, podemos usar ventanas de ~3 segundos
    win_sec = 3.0
    win_frames_p = int(win_sec * sr / hop_length)
    win_frames_o = int(win_frames_p / speed_ratio)
    
    step_sec = 1.0
    step_frames_p = int(step_sec * sr / hop_length)
    
    print("\nRealizando coincidencia de bloques para encontrar cortes...")
    timeline = []
    
    # Búsqueda usando correlación de mel spectrogram
    mel_o = librosa.feature.melspectrogram(y=y_o, sr=sr, n_mels=40, hop_length=hop_length)
    mel_p = librosa.feature.melspectrogram(y=y_p, sr=sr, n_mels=40, hop_length=hop_length)
    mel_o = np.log1p(mel_o)
    mel_p = np.log1p(mel_p)
    
    # Resample mel_p en tiempo según speed_ratio para que coincida en longitud temporal con mel_o
    from scipy.ndimage import zoom
    # Queremos expandir el tiempo de la previa para que coincida con el tiempo original:
    mel_p_stretched = zoom(mel_p, (1.0, speed_ratio))
    print(f"Dimensiones Mel Original: {mel_o.shape}, Mel Previa estirada: {mel_p_stretched.shape}")
    
    # Ahora comparar columnas
    win_f = int(2.5 * sr / hop_length)
    for p_idx in range(0, mel_p_stretched.shape[1] - win_f, int(1.0 * sr / hop_length)):
        chunk_p = mel_p_stretched[:, p_idx:p_idx+win_f]
        chunk_p_norm = chunk_p - np.mean(chunk_p)
        norm_p = np.linalg.norm(chunk_p_norm)
        if norm_p == 0:
            continue
            
        # Correlación con el original completo mediante dot product
        # Para acelerar: buscar en ventanas de mel_o
        # Hacemos convolución en 2D o producto de matrices
        # Más rápido: usar librosa.segment.cross_similarity en bandas
        best_score = -1e9
        best_o_idx = 0
        
        # Muestreamos candidatos cada 4 frames (~0.1s)
        scores = []
        for o_idx in range(0, mel_o.shape[1] - win_f, 4):
            chunk_o = mel_o[:, o_idx:o_idx+win_f]
            chunk_o_norm = chunk_o - np.mean(chunk_o)
            norm_o = np.linalg.norm(chunk_o_norm)
            if norm_o > 0:
                sim = np.sum(chunk_p_norm * chunk_o_norm) / (norm_p * norm_o)
                if sim > best_score:
                    best_score = sim
                    best_o_idx = o_idx
                    
        sec_in_previa = (p_idx / speed_ratio) * hop_length / sr
        sec_in_original = best_o_idx * hop_length / sr
        timeline.append((sec_in_previa, sec_in_original, best_score))
        
    print(f"\nTimeline calculada ({len(timeline)} puntos). Buscando discontinuidades...")
    cuts = []
    for i in range(1, len(timeline)):
        prev_p, prev_o, sc1 = timeline[i-1]
        cur_p, cur_o, sc2 = timeline[i]
        
        expected_o = prev_o + (cur_p - prev_p)
        diff = cur_o - expected_o
        if abs(diff) > 4.0: # Salto de más de 4 segundos en la canción original
            print(f"-> Salto detectado en PREVIA a los {cur_p:.1f}s: pasa de original {prev_o:.1f}s a {cur_o:.1f}s (salto de {diff:+.1f}s, sim: {sc2:.2f})")
            cuts.append((cur_p, prev_o, cur_o))
            
    print("\nResumen inicial de secciones detectadas:")
    last_o = timeline[0][1]
    last_p = 0
    print(f"Sección 1 empieza en original: ~{timeline[0][1]:.1f}s")
    for cut_p, cut_o_end, cut_o_start in cuts:
        print(f"  Previa: {last_p:.1f}s -> {cut_p:.1f}s  |  Mapea a Original: {last_o:.1f}s -> {cut_o_end:.1f}s (duración {cut_o_end - last_o:.1f}s)")
        last_p = cut_p
        last_o = cut_o_start
    print(f"  Previa: {last_p:.1f}s -> final  |  Mapea a Original: {last_o:.1f}s -> {timeline[-1][1]:.1f}s")

if __name__ == "__main__":
    analyze()
