import numpy as np
import librosa
import soundfile as sf

def main():
    print("Analizando transiciones rítmicas en PREVIA 2.wav...")
    y, sr = librosa.load("ejemplos/PREVIA 2.wav", sr=22050, mono=True)
    
    # Detección de onsets y beats
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)
    beat_times = librosa.frames_to_time(beats, sr=sr)
    
    # Calcular intervalos entre beats (IBI)
    ibis = np.diff(beat_times)
    median_ibi = np.median(ibis)
    print(f"BPM medio: {60.0/median_ibi:.2f}, IBI medio: {median_ibi:.3f}s")
    
    # Si hay un corte que no cae en el compás o donde la música salta, el IBI o la fase cambiará bruscamente
    # También calculamos la diferencia espectral (spectral flux) por frame
    spec = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    spectral_diff = np.sqrt(np.sum(np.diff(spec, axis=1)**2, axis=0))
    # Normalizar
    spectral_diff = spectral_diff / np.max(spectral_diff)
    
    # Buscar picos muy grandes de spectral diff donde la música cambia completamente
    peaks = librosa.util.peak_pick(spectral_diff, pre_max=20, post_max=20, pre_avg=20, post_avg=20, delta=0.15, wait=40)
    peak_times = librosa.frames_to_time(peaks, sr=sr, hop_length=512)
    
    print(f"Puntos de cambio tímbrico brusco detectados en PREVIA 2 ({len(peak_times)} candidatos):")
    for pt in peak_times:
        print(f"  t = {pt:6.2f}s (compás aprox: {pt / (median_ibi*4):.1f})")

if __name__ == "__main__":
    main()
