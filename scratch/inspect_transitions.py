"""
Inspeccionar exactamente qué pasa en los puntos de unión de PREVIA.wav:
- En t ~ 67.69s (unión entre Bloque 1 y Bloque 2)
- En t ~ 117.84s (unión entre Bloque 2 y Bloque 3)
- En t = 0.0s (cómo empieza la previa)
- En t = 154.5s - 155.5s (cómo termina la previa)
"""

import numpy as np
import soundfile as sf
import librosa

prev_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/PREVIA.wav"
y, sr = sf.read(prev_path)

print(f"Sample rate: {sr}")

def inspect_window(name: str, center_sec: float, span_sec: float = 2.0):
    start_sample = max(0, int((center_sec - span_sec/2) * sr))
    end_sample = min(len(y), int((center_sec + span_sec/2) * sr))
    chunk = y[start_sample:end_sample]
    
    # RMS en ventanas pequeñas de 10ms (480 samples a 48kHz)
    hop = 480
    if chunk.ndim > 1:
        chunk_mono = chunk.mean(axis=1)
    else:
        chunk_mono = chunk
        
    rms = [np.sqrt(np.mean(chunk_mono[i:i+hop]**2)) for i in range(0, len(chunk_mono)-hop, hop)]
    t_axis = np.linspace(center_sec - span_sec/2, center_sec + span_sec/2, len(rms))
    
    print(f"\n==========================================")
    print(f"INSPECCIÓN: {name} (alrededor de {center_sec:.2f}s)")
    print(f"==========================================")
    
    # Imprimir valores RMS cada 100ms
    step = max(1, len(rms) // 20)
    for idx in range(0, len(rms), step):
        val = rms[idx]
        bars = int(val * 40)
        print(f"t={t_axis[idx]:6.2f}s | RMS={val:6.3f} | {'█' * bars}")

inspect_window("INICIO DE PREVIA", 1.0, span_sec=2.0)
inspect_window("CORTE 1 -> 2", 67.69, span_sec=3.0)
inspect_window("CORTE 2 -> 3", 117.84, span_sec=3.0)
inspect_window("FINAL DE PREVIA", 154.5, span_sec=3.0)
