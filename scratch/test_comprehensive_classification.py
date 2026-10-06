"""
Sistema integral de clasificación:
- Drops reales (sin confundir con bases de intro).
- Descansos melódicos / breakdowns (sin bombo, melódicos, estables).
- Subidas / buildups dinámicas (cortas de 2-4 compases, estándar de 6 compases, o largas de 8-16 compases).
- Intros y outros.
"""

import numpy as np
import soundfile as sf
import librosa
from scipy.ndimage import gaussian_filter1d
import scipy.signal
from src.analysis.bpm import detect_beat_grid
from src.analysis.structure import (
    SectionType, Section, StructureAnalysis,
    _kick_bass_envelope, _melody_envelope, _pitos_leads_envelope,
    _rms_envelope, _k_weight, _lufs_from_kweighted, _peak_dbfs,
    SR_ANALYSIS, HOP_LENGTH
)

orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
y, sr = sf.read(orig_path)
if y.ndim > 1: y = y.mean(axis=1)

grid = detect_beat_grid(y, sr)
bpm = grid.bpm
beats = grid.beat_times
n_beats = len(beats)
n_bars = n_beats // 4
bar_dur = 4.0 * (60.0 / bpm)

sr_ana = SR_ANALYSIS
if sr != sr_ana:
    y_ana = librosa.resample(y, orig_sr=sr, target_sr=sr_ana)
else:
    y_ana = y.copy()

hop = HOP_LENGTH
rms_env = _rms_envelope(y_ana, hop=hop)
kick_env = _kick_bass_envelope(y_ana, sr_ana, hop=hop)
mel_env = _melody_envelope(y_ana, sr_ana, hop=hop)
pitos_env = _pitos_leads_envelope(y_ana, sr_ana, hop=hop)
spec_cent = librosa.feature.spectral_centroid(y=y_ana, sr=sr_ana, hop_length=hop)[0]
spec_cent_norm = (spec_cent - spec_cent.min()) / (spec_cent.max() - spec_cent.min() + 1e-6)
y_kw = _k_weight(y_ana, sr_ana)

# Valores por compás
bar_kick = np.zeros(n_bars)
bar_mel = np.zeros(n_bars)
bar_pitos = np.zeros(n_bars)
bar_rms = np.zeros(n_bars)
bar_bright = np.zeros(n_bars)
bar_times = np.zeros(n_bars)

for b in range(n_bars):
    t0 = beats[b * 4]
    t1 = beats[min(n_beats - 1, (b + 1) * 4)]
    f0 = max(0, min(librosa.time_to_frames(t0, sr=sr_ana, hop_length=hop), len(rms_env) - 1))
    f1 = max(f0 + 1, min(librosa.time_to_frames(t1, sr=sr_ana, hop_length=hop), len(rms_env)))
    
    bar_kick[b] = np.mean(kick_env[f0:f1])
    bar_mel[b] = np.mean(mel_env[f0:f1])
    bar_pitos[b] = np.mean(pitos_env[f0:f1])
    bar_rms[b] = np.mean(rms_env[f0:f1])
    bar_bright[b] = np.mean(spec_cent_norm[f0:f1])
    bar_times[b] = t0

bar_leads = 0.55 * bar_mel + 0.45 * bar_pitos
bar_fullness = 0.35 * bar_kick + 0.35 * bar_rms + 0.30 * bar_leads

# Pendientes compás a compás
slope_leads = np.gradient(gaussian_filter1d(bar_leads, 1.0))
slope_bright = np.gradient(gaussian_filter1d(bar_bright, 1.0))
slope_rms = np.gradient(gaussian_filter1d(bar_rms, 1.0))

# ── PASO 1: Identificación precisa de DROPS ──
# Drop = Bombo contundente + RMS alto + Carga melódica/leads real
is_drop = (bar_kick >= 0.42) & (bar_rms >= 0.40) & ((bar_leads >= 0.20) | (bar_fullness >= 0.48))

# Excluir base de mezcla en la intro (primeros compases antes del primer descanso)
for b in range(min(25, n_bars)):
    if b / n_bars < 0.15 and (bar_leads[b] < 0.35 or bar_fullness[b] < 0.52):
        is_drop[b] = False

# Puenteo de fills y turnarounds de 1-2 compases dentro de un drop
bridged_drop = np.copy(is_drop)
for b in range(1, n_bars - 2):
    if not bridged_drop[b] and bridged_drop[b-1]:
        if bridged_drop[b+1] or (b < n_bars-2 and bridged_drop[b+2]):
            bridged_drop[b] = True
            if b < n_bars-2 and bridged_drop[b+2]:
                bridged_drop[b+1] = True

# Descartar ráfagas aisladas de menos de 6 compases (falsos drops)
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

# ── PASO 2: Identificación DINÁMICA de SUBIDAS (cortas o largas) ──
# Para cada drop, rastrear hacia atrás para encontrar la longitud real de la subida
is_buildup = np.zeros(n_bars, dtype=bool)

# Encontrar índices de inicio de cada bloque de drop
drop_start_bars = []
for b in range(1, n_bars):
    if clean_drop[b] and not clean_drop[b - 1]:
        drop_start_bars.append(b)

for d_bar in drop_start_bars:
    # Rastrear hacia atrás hasta un máximo de 16 compases
    bu_len = 0
    for look in range(1, min(17, d_bar)):
        bar = d_bar - look
        if clean_drop[bar]: # Tope con drop anterior
            break
            
        k = bar_kick[bar]
        l = bar_leads[bar]
        br = bar_bright[bar]
        sh = slope_leads[bar]
        sb = slope_bright[bar]
        sr = slope_rms[bar]
        
        # Criterios de subida / riser / redoble:
        # 1. Pendiente positiva de leads/riser o brillo espectral o RMS
        is_bu = False
        if (sh > 0.012 or sb > 0.012 or sr > 0.018) and k < 0.42:
            is_bu = True
        elif l >= 0.25 and k < 0.35 and look <= 8:
            is_bu = True
        elif bar_rms[bar] > 0.35 and k < 0.30 and look <= 6:
            is_bu = True
            
        if is_bu:
            bu_len = look
        else:
            if look > 2: # Si tras 2 compases ya no hay subida, detener
                break
                
    # Si detectó una subida pero no es múltiplo de compás estándar, redondear
    # Puede ser corta (2, 4 compases) o larga (6, 8, 12, 16 compases)
    if bu_len == 0:
        bu_len = min(4, d_bar)
    elif bu_len in (1, 3):
        bu_len += 1
    elif bu_len in (5, 7):
        bu_len += 1
        
    for bb in range(d_bar - bu_len, d_bar):
        if bb >= 0 and not clean_drop[bb]:
            is_buildup[bb] = True

# ── PASO 3: Clasificación de secciones restantes ──
# - DESCANSO / BREAKDOWN: ausencia de bombo (k < 0.35), melodía/voces/leads activos, estable.
# - INTRO / OUTRO: en los extremos sin drop ni subida.
final_types: list[SectionType] = []
for b in range(n_bars):
    rel = b / n_bars
    if clean_drop[b]:
        final_types.append(SectionType.DROP)
    elif is_buildup[b]:
        final_types.append(SectionType.BUILDUP)
    elif rel > 0.88 and bar_kick[b] < 0.40 and bar_rms[b] < 0.40:
        final_types.append(SectionType.OUTRO)
    elif rel < 0.12 and not any(is_buildup[:b+1]) and not any(clean_drop[:b+1]):
        final_types.append(SectionType.INTRO)
    elif bar_kick[b] < 0.38 and (bar_leads[b] >= 0.20 or bar_rms[b] >= 0.25):
        # DESCANSO / BREAKDOWN REAL: bombo ausente/bajo, melodía y armonía presentes
        final_types.append(SectionType.BREAKDOWN)
    elif rel < 0.20 and not any(clean_drop[:b+1]):
        final_types.append(SectionType.INTRO)
    else:
        final_types.append(SectionType.BREAKDOWN)

# ── PASO 4: Agrupación en secciones continuas ──
sections: list[Section] = []
cur_t = final_types[0]
cur_start_b = 0

for b in range(1, n_bars):
    if final_types[b] != cur_t:
        t_s = float(bar_times[cur_start_b])
        t_e = float(bar_times[b])
        sections.append(Section(
            type=cur_t,
            start_time=t_s,
            end_time=t_e,
            start_beat=cur_start_b * 4,
            end_beat=b * 4,
        ))
        cur_t = final_types[b]
        cur_start_b = b

# Última sección
sections.append(Section(
    type=cur_t,
    start_time=float(bar_times[cur_start_b]),
    end_time=float(len(y)/sr),
    start_beat=cur_start_b * 4,
    end_beat=n_beats,
))

# Fusionar secciones adyacentes del mismo tipo
merged: list[Section] = []
for s in sections:
    if merged and merged[-1].type == s.type:
        merged[-1].end_time = s.end_time
        merged[-1].end_beat = s.end_beat
    else:
        merged.append(s)

# Calcular métricas para cada sección
for sec in merged:
    f_s = max(0, min(librosa.time_to_frames(sec.start_time, sr=sr_ana, hop_length=hop), len(rms_env) - 1))
    f_e = max(f_s + 1, min(librosa.time_to_frames(sec.end_time, sr=sr_ana, hop_length=hop), len(rms_env)))
    
    sec.energy = float(np.mean(rms_env[f_s:f_e]))
    sec.bass_energy = float(np.mean(kick_env[f_s:f_e]))
    m_val = float(np.mean(mel_env[f_s:f_e]))
    p_val = float(np.mean(pitos_env[f_s:f_e]))
    sec.melody_energy = float(0.55 * m_val + 0.45 * p_val)
    sec.fullness = float(0.35 * sec.bass_energy + 0.35 * sec.energy + 0.30 * sec.melody_energy)
    
    s_start = max(0, min(int(sec.start_time * sr_ana), len(y_ana) - 1))
    s_end = max(s_start + 1, min(int(sec.end_time * sr_ana), len(y_ana)))
    sec.lufs = _lufs_from_kweighted(y_kw[s_start:s_end])
    sec.peak_dbfs = _peak_dbfs(y_ana[s_start:s_end])

print(f"\nTOTAL SECCIONES CLASIFICADAS: {len(merged)}")
print(f"{'Idx':>3} | {'Tipo':>10} | {'Inicio':>7} -> {'Fin':>7} ({'Dur':>5}) | {'Beats':>9} | {'Full':>5} {'Bass':>5} {'Melo':>5} | Diagnóstico")
print("-" * 80)
for i, s in enumerate(merged):
    n_b = (s.end_beat - s.start_beat) // 4
    diag = ""
    if s.type == SectionType.BUILDUP:
        if n_b <= 3:
            diag = f"⚡ SUBIDA CORTA ({n_b} compases)"
        elif n_b <= 6:
            diag = f"⚡ SUBIDA ESTÁNDAR ({n_b} compases)"
        else:
            diag = f"⚡ SUBIDA LARGA ({n_b} compases)"
    elif s.type == SectionType.DROP:
        diag = f"🔥 DROP CLÍMAX ({n_b} compases, {s.duration:.1f}s)"
    elif s.type == SectionType.BREAKDOWN:
        diag = f"🎹 DESCANSO MELÓDICO ({n_b} compases, {s.duration:.1f}s)"
    elif s.type == SectionType.INTRO:
        diag = f"🎧 INTRO ({n_b} compases)"
    elif s.type == SectionType.OUTRO:
        diag = f"🏁 OUTRO ({n_b} compases)"
        
    print(f"[{i:02d}] | {s.type.name:10s} | {s.start_time:6.2f}s -> {s.end_time:6.2f}s ({s.duration:4.1f}s) | {s.start_beat:4d}..{s.end_beat:4d} | {s.fullness:5.2f} {s.bass_energy:5.2f} {s.melody_energy:5.2f} | {diag}")
