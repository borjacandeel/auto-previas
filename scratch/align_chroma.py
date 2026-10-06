import numpy as np
import librosa

def main():
    sr = 22050
    hop = 1024
    print("Cargando audios...")
    y_o, _ = librosa.load("ejemplos/ORIGINAL 2.flac", sr=sr, mono=True)
    y_p, _ = librosa.load("ejemplos/PREVIA 2.wav", sr=sr, mono=True)
    
    chroma_o = librosa.feature.chroma_cens(y=y_o, sr=sr, hop_length=hop)
    chroma_p = librosa.feature.chroma_cens(y=y_p, sr=sr, hop_length=hop)
    
    win = int(3.0 * sr / hop)
    points = []
    
    # Muestrear cada 2 segundos en la previa
    for t_p in np.arange(1.0, (chroma_p.shape[1] - win) * hop / sr, 2.0):
        f_p = int(t_p * sr / hop)
        pat = chroma_p[:, f_p:f_p+win]
        pat_shifted = np.roll(pat, -1, axis=0) # shift=-1 semitono confirmado
        norm_p = np.linalg.norm(pat_shifted)
        if norm_p == 0:
            continue
            
        best_score = -1
        best_t_o = 0
        
        for f_o in range(0, chroma_o.shape[1] - win, 2):
            chunk_o = chroma_o[:, f_o:f_o+win]
            norm_o = np.linalg.norm(chunk_o)
            if norm_o > 0:
                sim = np.sum(pat_shifted * chunk_o) / (norm_p * norm_o)
                if sim > best_score:
                    best_score = sim
                    best_t_o = (f_o * hop) / sr
                    
        points.append((t_p, best_t_o, best_score))
        
    print(f"Total puntos rastreados: {len(points)}")
    # Detectar transiciones / cortes
    cuts = []
    for i in range(1, len(points)):
        p_prev, o_prev, s_prev = points[i-1]
        p_curr, o_curr, s_curr = points[i]
        
        exp_o = o_prev + (p_curr - p_prev) * 1.0765
        diff = o_curr - exp_o
        if abs(diff) > 4.0 and s_curr > 0.85:
            cuts.append((p_curr, o_prev, o_curr, diff))
            
    print("\n" + "="*60)
    print("CORTES EXACTOS IDENTIFICADOS EN PREVIA 2:")
    print("="*60)
    for c in cuts:
        print(f"En Previa t = {c[0]:5.1f}s: Salto en Original de {c[1]:5.1f}s a {c[2]:5.1f}s (salto de {c[3]:+5.1f}s)")
        
    # Imprimir los bloques enteros
    print("\n" + "="*60)
    print("BLOQUES MUSICALES DE PREVIA 2:")
    print("="*60)
    prev_p = 0.0
    prev_o = points[0][1]
    for c in cuts:
        dur_p = c[0] - prev_p
        dur_o = c[1] - prev_o
        print(f"Bloque: Previa {prev_p:5.1f}s -> {c[0]:5.1f}s ({dur_p:4.1f}s)  |  Mapea a Original: {prev_o:5.1f}s -> {c[1]:5.1f}s ({dur_o:4.1f}s)")
        prev_p = c[0]
        prev_o = c[2]
    dur_p = points[-1][0] - prev_p
    dur_o = points[-1][1] - prev_o
    print(f"Bloque Final: Previa {prev_p:5.1f}s -> {points[-1][0]:5.1f}s ({dur_p:4.1f}s)  |  Mapea a Original: {prev_o:5.1f}s -> {points[-1][1]:5.1f}s ({dur_o:4.1f}s)")

if __name__ == "__main__":
    main()
