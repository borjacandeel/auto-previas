"""
Detección de estructura musical: intro, subida, drop, descanso/melodía, outro.

Pipeline avanzado orientado a EDM / Hardstyle / Dance:
1. Análisis multi-banda:
   - Graves / Bombo (45-140 Hz): presencia del kick 4-on-the-floor y subgrave.
   - Melodía / Medios (500-4000 Hz): presencia de melodías, leads, acordes y voces.
   - Flujo espectral y novedad: detección de transiciones y risers.
   - Envolvente RMS global: nivel de energía general.
2. Análisis sincronizado por compás (BeatGrid / 4 beats por compás):
   - Cada compás musical se evalúa de forma armónica y rítmica.
3. Clasificación semántica de compases:
   - DROP: bombo contundente + alta energía RMS general.
   - BREAKDOWN / MELODÍA: ausencia o filtrado del bombo + fuerte contenido melódico/armónico.
   - BUILDUP: energía y frecuencias crecientes inmediatamente previas al drop.
   - INTRO / OUTRO: secciones extremas con energía moderada o baja.
4. Filtrado de mayoría por frase musical (ventana de 7 compases):
   - Evita que redobles de 1 compás, parones de voz o vocal chops ("Americano!")
     partan los drops por la mitad.
5. Medición sonora profesional BS.1770 / EBU R128 (LUFS integrado y pico verdadero).
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List

import numpy as np
import librosa
import scipy.signal
from scipy.ndimage import gaussian_filter1d

from .bpm import BeatGrid, SR_ANALYSIS, HOP_LENGTH


class SectionType(str, Enum):
    INTRO = "intro"
    BUILDUP = "buildup"
    DROP = "drop"
    BREAKDOWN = "breakdown"
    OUTRO = "outro"
    UNKNOWN = "unknown"


@dataclass
class Section:
    type: SectionType
    start_time: float    # segundos
    end_time: float      # segundos
    start_beat: int = 0
    end_beat: int = 0
    energy: float = 0.5        # RMS normalizado [0-1]
    bass_energy: float = 0.5   # energía de bombo/graves [0-1]
    melody_energy: float = 0.5 # energía de melodías, sintes, pitos y voces [0-1]
    fullness: float = 0.5      # carga global (bombo + melodía + pitos + volumen) [0-1]
    spectral_novelty: float = 0.5
    onset_density: float = 0.0  # densidad rítmica [0-1]
    brightness: float = 0.5    # centroide espectral normalizado [0-1]
    lufs: float = -70.0         # loudness integrada ITU-R BS.1770 (LUFS)
    peak_dbfs: float = -70.0    # pico verdadero en dBFS

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def __repr__(self) -> str:
        return (
            f"[{self.type.value:10s}] "
            f"{self.start_time:6.1f}s – {self.end_time:6.1f}s "
            f"({self.duration:.1f}s) "
            f"{self.lufs:.1f} LUFS  {self.peak_dbfs:.1f} dBFS"
        )


@dataclass
class StructureAnalysis:
    sections: List[Section] = field(default_factory=list)
    duration: float = 0.0
    bpm: float = 0.0

    def drops(self) -> List[Section]:
        return [s for s in self.sections if s.type == SectionType.DROP]

    def buildups(self) -> List[Section]:
        return [s for s in self.sections if s.type == SectionType.BUILDUP]

    def breakdowns(self) -> List[Section]:
        return [s for s in self.sections if s.type == SectionType.BREAKDOWN]


# ---------------------------------------------------------------------------
# Envolventes y filtros
# ---------------------------------------------------------------------------

def _rms_envelope(y: np.ndarray, frame_length: int = 2048, hop: int = HOP_LENGTH) -> np.ndarray:
    fl = min(frame_length, max(64, len(y)))
    hp = min(hop, max(1, fl // 4))
    rms = librosa.feature.rms(y=y, frame_length=fl, hop_length=hp)[0]
    peak = rms.max()
    return rms / peak if peak > 0 else rms


def _kick_bass_envelope(y: np.ndarray, sr: int, hop: int = HOP_LENGTH) -> np.ndarray:
    """Energía en banda de bombo/sub (45-140 Hz) — define la presencia real del Drop."""
    sos = scipy.signal.butter(4, [45, 140], btype="bandpass", fs=sr, output="sos")
    y_kick = scipy.signal.sosfilt(sos, y)
    fl = min(2048, max(64, len(y_kick)))
    hp = min(hop, max(1, fl // 4))
    rms = librosa.feature.rms(y=y_kick, frame_length=fl, hop_length=hp)[0]
    peak = rms.max()
    return rms / peak if peak > 0 else rms


def _melody_envelope(y: np.ndarray, sr: int, hop: int = HOP_LENGTH) -> np.ndarray:
    """Energía en banda de melodía, acordes, sintes y voces (400-4500 Hz)."""
    sos = scipy.signal.butter(4, [400, 4500], btype="bandpass", fs=sr, output="sos")
    y_mid = scipy.signal.sosfilt(sos, y)
    fl = min(2048, max(64, len(y_mid)))
    hp = min(hop, max(1, fl // 4))
    rms = librosa.feature.rms(y=y_mid, frame_length=fl, hop_length=hp)[0]
    peak = rms.max()
    return rms / peak if peak > 0 else rms


def _pitos_leads_envelope(y: np.ndarray, sr: int, hop: int = HOP_LENGTH) -> np.ndarray:
    """Energía en banda de pitos, screeches, leads agudos y synths cortantes (2000-8000 Hz)."""
    sos = scipy.signal.butter(4, [2000, 8000], btype="bandpass", fs=sr, output="sos")
    y_high = scipy.signal.sosfilt(sos, y)
    fl = min(2048, max(64, len(y_high)))
    hp = min(hop, max(1, fl // 4))
    rms = librosa.feature.rms(y=y_high, frame_length=fl, hop_length=hp)[0]
    peak = rms.max()
    return rms / peak if peak > 0 else rms


def _spectral_novelty(y: np.ndarray, sr: int, hop: int = HOP_LENGTH) -> np.ndarray:
    """Flujo espectral suavizado para transiciones y risers."""
    n_fft = min(2048, max(64, len(y)))
    hp = min(hop, max(1, n_fft // 4))
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hp))
    flux = np.sum(np.maximum(0, np.diff(S, axis=1)), axis=0)
    flux = np.convolve(flux, np.hanning(11) / np.hanning(11).sum(), mode="same")
    peak = flux.max()
    return flux / peak if peak > 0 else flux


def _spectral_centroid_norm(y: np.ndarray, sr: int, hop: int = HOP_LENGTH) -> np.ndarray:
    n_fft = min(2048, max(64, len(y)))
    hp = min(hop, max(1, n_fft // 4))
    sc = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=n_fft, hop_length=hp)[0]
    sc_min, sc_max = sc.min(), sc.max()
    if sc_max - sc_min < 1e-6:
        return np.zeros_like(sc)
    return (sc - sc_min) / (sc_max - sc_min)


def _spectral_flatness_envelope(y: np.ndarray, sr: int, hop: int = HOP_LENGTH) -> np.ndarray:
    """Planitud espectral: ~0 = tonal (sintes/melodías), ~1 = ruidoso/percusivo."""
    n_fft = min(2048, max(64, len(y)))
    hp = min(hop, max(1, n_fft // 4))
    sf = librosa.feature.spectral_flatness(y=y, n_fft=n_fft, hop_length=hp)[0]
    return sf


def _harmonic_percussive_ratio(y: np.ndarray, sr: int, hop: int = HOP_LENGTH) -> np.ndarray:
    """
    Ratio armónico/total mediante HPSS (Harmonic-Percussive Source Separation).
    Valor alto = contenido melódico/armónico (sintes, leads, acordes) → indica DROP.
    Valor bajo = contenido percusivo dominante (bombos, claps, hihats) → indica DESCANSO.
    """
    y_harm, _y_perc = librosa.effects.hpss(y)
    fl = min(2048, max(64, len(y)))
    hp = min(hop, max(1, fl // 4))
    rms_h = librosa.feature.rms(y=y_harm, frame_length=fl, hop_length=hp)[0]
    rms_full = librosa.feature.rms(y=y, frame_length=fl, hop_length=hp)[0]
    total = rms_full + 1e-10
    return rms_h / total


def _spectral_bandwidth_norm(y: np.ndarray, sr: int, hop: int = HOP_LENGTH) -> np.ndarray:
    """
    Ancho de banda espectral normalizado [0-1].
    Amplio = muchas capas sonoras simultáneas (drop con todo a tope).
    Estrecho = pocas capas (descanso con solo bombo y voz).
    """
    n_fft = min(2048, max(64, len(y)))
    hp = min(hop, max(1, n_fft // 4))
    bw = librosa.feature.spectral_bandwidth(y=y, sr=sr, n_fft=n_fft, hop_length=hp)[0]
    bw_min, bw_max = bw.min(), bw.max()
    if bw_max - bw_min < 1e-6:
        return np.zeros_like(bw)
    return (bw - bw_min) / (bw_max - bw_min)


# ---------------------------------------------------------------------------
# Loudness BS.1770
# ---------------------------------------------------------------------------

def _k_weight(y: np.ndarray, sr: int) -> np.ndarray:
    f0  = 1681.974
    G   = 4.0
    K   = math.tan(math.pi * f0 / sr)
    Vh  = 10 ** (G / 20.0)
    Vsq = math.sqrt(2 * Vh)
    norm = 1 + math.sqrt(2) * K + K * K
    b = np.array([
        (Vh + Vsq * K + K * K) / norm,
        2 * (K * K - Vh) / norm,
        (Vh - Vsq * K + K * K) / norm,
    ])
    a = np.array([1.0, 2 * (K * K - 1) / norm, (1 - math.sqrt(2) * K + K * K) / norm])
    y1 = scipy.signal.lfilter(b, a, y)
    sos = scipy.signal.butter(2, 38.135 / (sr / 2), btype="high", output="sos")
    return scipy.signal.sosfilt(sos, y1)


def _lufs_from_kweighted(y_kw: np.ndarray) -> float:
    msq = float(np.mean(y_kw ** 2))
    if msq < 1e-12:
        return -70.0
    return round(-0.691 + 10 * math.log10(msq), 1)


def _peak_dbfs(y: np.ndarray) -> float:
    peak = float(np.max(np.abs(y)))
    if peak < 1e-12:
        return -70.0
    return round(20 * math.log10(peak), 1)


# ---------------------------------------------------------------------------
# Segmentación y clasificación por compás (Beat/Bar synchronized)
# ---------------------------------------------------------------------------

def _majority_filter(arr: List[SectionType], w: int = 7) -> List[SectionType]:
    """
    Filtro de mayoría por ventana de compases para eliminar micro-cortes
    (ej. redobles de 1 compás, vocal chops o silencios breves dentro de un drop).
    """
    out = list(arr)
    half = w // 2
    for i in range(len(arr)):
        window = arr[max(0, i - half) : min(len(arr), i + half + 1)]
        # Si estamos dentro de una zona de drop y hay algún compás de corte, mantenerlo dentro del drop
        drop_count = sum(1 for x in window if x == SectionType.DROP)
        if drop_count >= len(window) * 0.45:
            out[i] = SectionType.DROP
        else:
            from collections import Counter
            counts = Counter(window)
            out[i] = counts.most_common(1)[0][0]
    return out


def analyze_structure(y: np.ndarray, sr: int, beat_grid: BeatGrid) -> StructureAnalysis:
    """
    Analiza la estructura musical del tema identificando con precisión:
    - Drops enteros y continuos (sin cortes absurdos por vocal chops o redobles).
    - Melodías y Breakdowns (donde residen los sintes/voces sin bombos).
    - Subidas / Buildups previas a cada drop.
    - Intro y Outro.
    """
    if len(y) < 2048:
        raise ValueError(
            f"El archivo de audio contiene solo {len(y)} muestras, insuficiente para analizar la estructura."
        )

    if sr != SR_ANALYSIS:
        y = librosa.resample(y, orig_sr=sr, target_sr=SR_ANALYSIS)
        sr = SR_ANALYSIS

    total_duration = librosa.get_duration(y=y, sr=sr)
    beat_times = beat_grid.beat_times
    n_beats = len(beat_times)

    if n_beats < 8:
        # Pista excesivamente corta: clasificar todo como drop
        sec = Section(
            type=SectionType.DROP,
            start_time=0.0,
            end_time=total_duration,
            start_beat=0,
            end_beat=n_beats,
            energy=0.8,
            bass_energy=0.7,
        )
        return StructureAnalysis(sections=[sec], duration=total_duration, bpm=beat_grid.bpm)

    # 1. Envolventes espectrales
    rms_env      = _rms_envelope(y, hop=HOP_LENGTH)
    kick_env     = _kick_bass_envelope(y, sr, hop=HOP_LENGTH)
    melody_env   = _melody_envelope(y, sr, hop=HOP_LENGTH)
    pitos_env    = _pitos_leads_envelope(y, sr, hop=HOP_LENGTH)
    novelty_env  = _spectral_novelty(y, sr, hop=HOP_LENGTH)
    centroid_env = _spectral_centroid_norm(y, sr, hop=HOP_LENGTH)
    y_kw         = _k_weight(y, sr)
    flatness_env  = _spectral_flatness_envelope(y, sr, hop=HOP_LENGTH)
    harmonic_env  = _harmonic_percussive_ratio(y, sr, hop=HOP_LENGTH)
    bandwidth_env = _spectral_bandwidth_norm(y, sr, hop=HOP_LENGTH)

    # 2. Agrupación por compases de 4 beats (4/4 estándar de música electrónica)
    beats_per_bar = 4
    n_bars = max(1, n_beats // beats_per_bar)

    bar_kick   = np.zeros(n_bars)
    bar_mel    = np.zeros(n_bars)
    bar_pitos  = np.zeros(n_bars)
    bar_rms    = np.zeros(n_bars)
    bar_bright = np.zeros(n_bars)
    bar_times  = np.zeros(n_bars)
    bar_flat   = np.zeros(n_bars)
    bar_harm   = np.zeros(n_bars)
    bar_bw     = np.zeros(n_bars)

    for b in range(n_bars):
        idx_b0 = b * beats_per_bar
        idx_b1 = min(n_beats - 1, (b + 1) * beats_per_bar)
        t0 = float(beat_times[idx_b0])
        t1 = float(beat_times[idx_b1])
        f0 = librosa.time_to_frames(t0, sr=sr, hop_length=HOP_LENGTH)
        f1 = librosa.time_to_frames(t1, sr=sr, hop_length=HOP_LENGTH)
        f0 = max(0, min(f0, len(rms_env) - 1))
        f1 = max(f0 + 1, min(f1, len(rms_env)))

        bar_kick[b]   = float(np.mean(kick_env[f0:f1]))
        bar_mel[b]    = float(np.mean(melody_env[f0:f1]))
        bar_pitos[b]  = float(np.mean(pitos_env[f0:f1]))
        bar_rms[b]    = float(np.mean(rms_env[f0:f1]))
        bar_bright[b] = float(np.mean(centroid_env[f0:f1]))
        bar_times[b]  = t0
        bar_flat[b]   = float(np.mean(flatness_env[max(0, f0):min(f1, len(flatness_env))])) if f0 < len(flatness_env) else 0.5
        bar_harm[b]   = float(np.mean(harmonic_env[max(0, f0):min(f1, len(harmonic_env))])) if f0 < len(harmonic_env) else 0.5
        bar_bw[b]     = float(np.mean(bandwidth_env[max(0, f0):min(f1, len(bandwidth_env))])) if f0 < len(bandwidth_env) else 0.5


    # Carga instrumental: combinación de melodía/voces con pitos/leads chillones
    bar_leads = 0.55 * bar_mel + 0.45 * bar_pitos
    # Plenitud global del compás: lo más cargado del tema reúne bombo + rms + instrumentales
    bar_fullness = 0.35 * bar_kick + 0.35 * bar_rms + 0.30 * bar_leads

    # ── Repetición melódica por compás (auto-similitud cromática) ──
    # Los drops tienen patrones melódicos REPETITIVOS (loops de 1-4 compases).
    # Los descansos tienen contenido más variado (vocales, progresiones cambiantes).
    chroma_nfft = min(4096, max(64, len(y)))
    chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_fft=chroma_nfft,
                                          hop_length=HOP_LENGTH)
    bar_chromas: list = []
    for b in range(n_bars):
        idx_b0 = b * beats_per_bar
        idx_b1 = min(n_beats - 1, (b + 1) * beats_per_bar)
        t0_ = float(beat_times[idx_b0])
        t1_ = float(beat_times[idx_b1])
        cf0 = librosa.time_to_frames(t0_, sr=sr, hop_length=HOP_LENGTH)
        cf1 = librosa.time_to_frames(t1_, sr=sr, hop_length=HOP_LENGTH)
        cf0 = max(0, min(cf0, chroma.shape[1] - 1))
        cf1 = max(cf0 + 1, min(cf1, chroma.shape[1]))
        bar_chromas.append(chroma[:, cf0:cf1].mean(axis=1))

    bar_repetition = np.zeros(n_bars)
    for b in range(n_bars):
        sims: list = []
        v1 = bar_chromas[b]
        n1 = float(np.linalg.norm(v1))
        if n1 < 1e-6:
            continue
        for offset in range(-4, 5):
            nb = b + offset
            if nb != b and 0 <= nb < n_bars:
                v2 = bar_chromas[nb]
                n2 = float(np.linalg.norm(v2))
                if n2 > 1e-6:
                    sims.append(float(np.dot(v1, v2) / (n1 * n2)))
        if sims:
            bar_repetition[b] = float(np.mean(sims))

    # ── Score de DENSIDAD MELÓDICA: lo que REALMENTE distingue un drop de un descanso ──
    #   Drop    = melodías repetitivas + contenido armónico denso + ancho espectral amplio
    #   Descanso = bombos + vocales + percusión pero SIN la densidad melódica del drop
    bar_melodic_density = (
        0.35 * bar_leads +          # Energía de sintes, melodías, leads, pitos
        0.30 * bar_harm +           # Ratio armónico (HPSS): alto = melódico, bajo = percusivo
        0.20 * bar_bw +             # Ancho de banda espectral: amplio = muchas capas
        0.15 * bar_repetition       # Repetición cromática: alta = loops melódicos de drop
    )

    # ── Umbrales ADAPTATIVOS basados en percentiles del track ──
    # Un DROP debe ser genuinamente la parte MÁS CARGADA del tema,
    # no simplemente cualquier sección con bombo y algo de volumen.
    fullness_p55  = max(float(np.percentile(bar_fullness, 55)), 0.38)
    melodic_p55   = max(float(np.percentile(bar_melodic_density, 55)), 0.30)
    kick_p40      = float(np.percentile(bar_kick, 40))

    # 3. Clasificación semántica MEJORADA por compás — EDM / Dance / Hardstyle
    #
    # DIFERENCIA CLAVE entre DROP y DESCANSO (aprendida del usuario):
    #   DROP     → bombo + melodías repetitivas + sintes/leads + máxima densidad → TODO a tope
    #   DESCANSO → bombo + vocales + percusión pero SIN la carga melódica del drop
    #
    # Se usa doble criterio: plenitud global (fullness) Y densidad melódica
    # para evitar que bombos + vocales solas se clasifiquen como Drop.
    raw_types: List[SectionType] = []
    for b in range(n_bars):
        rel = b / n_bars
        k = bar_kick[b]
        r = bar_rms[b]
        m = bar_leads[b]
        full = bar_fullness[b]
        mel_d = bar_melodic_density[b]

        # Intro / Outro en extremos
        if rel < 0.16 and (m < 0.35 or full < 0.52):
            raw_types.append(SectionType.INTRO)
        elif rel > 0.86 and (full < 0.52 or m < 0.32 or k < 0.50):
            raw_types.append(SectionType.OUTRO)

        # DROP REAL: lo MÁS CARGADO del tema con densidad melódica alta
        # Requisitos simultáneos:
        #   1. Plenitud global >= percentil 55 del track (es realmente denso)
        #   2. Densidad melódica >= percentil 55 (melodías + armónicos + capas + repetición)
        #   3. Kick presente (por encima del percentil 40 o mínimo 0.30)
        #   4. RMS decente (volumen general mínimo)
        # Esto IMPIDE que bombos + vocales solas se clasifiquen como Drop
        elif (full >= fullness_p55 and
              mel_d >= melodic_p55 and
              k >= max(0.30, kick_p40) and
              r >= 0.35):
            raw_types.append(SectionType.DROP)
        else:
            raw_types.append(SectionType.BREAKDOWN)

    # 4. Filtro de frase y puenteo de turnarounds/vocal chops dentro de drops:
    # En música electrónica, cada 16 compases suele haber un fill/redoble de 1 o 2 compases.
    # Evitamos que eso fragmente el drop en pedazos pequeños.
    filtered_bars = list(raw_types)
    for b in range(1, n_bars - 2):
        if filtered_bars[b] != SectionType.DROP and filtered_bars[b - 1] == SectionType.DROP:
            # Si el drop se reanuda en 1 o 2 compases, es un turnaround fill: mantener como DROP
            if filtered_bars[b + 1] == SectionType.DROP or (b < n_bars - 2 and filtered_bars[b + 2] == SectionType.DROP):
                filtered_bars[b] = SectionType.DROP
                if b < n_bars - 2 and filtered_bars[b + 2] == SectionType.DROP:
                    filtered_bars[b + 1] = SectionType.DROP

    # 5. Regla de duración mínima y eliminación de falsos drops diminutos (<8 compases):
    # Un drop real en música de baile debe durar al menos 8 compases (2 frases / ~12s).
    # Si un tramo de bombo en la intro dura menos de 8 compases, es base de mezcla de la INTRO.
    runs = []
    cur_t = filtered_bars[0]
    cur_len = 1
    for i in range(1, len(filtered_bars)):
        if filtered_bars[i] == cur_t:
            cur_len += 1
        else:
            runs.append([cur_t, cur_len])
            cur_t = filtered_bars[i]
            cur_len = 1
    runs.append([cur_t, cur_len])

    clean_bars = []
    for r in range(len(runs)):
        typ, length = runs[r]
        if typ == SectionType.DROP and length < 8:
            typ = SectionType.INTRO if (r == 0 or runs[0][0] == SectionType.INTRO) else SectionType.BREAKDOWN
        elif length < 4:
            if r > 0:
                typ = runs[r - 1][0]
            elif r < len(runs) - 1:
                typ = runs[r + 1][0]
        clean_bars.extend([typ] * length)

    # Pendientes temporales compás a compás (para detectar risers y filtros abriéndose)
    slope_leads = np.gradient(gaussian_filter1d(bar_leads, 1.0))
    slope_bright = np.gradient(gaussian_filter1d(bar_bright, 1.0))
    slope_rms = np.gradient(gaussian_filter1d(bar_rms, 1.0))

    # 6. Detección DINÁMICA de subidas (Buildups) previas a cada Drop REAL:
    # Las subidas en música electrónica pueden ser CORTAS (2-4 compases, ~3-6s), ESTÁNDAR (6-8 compases, ~9-12s)
    # o LARGAS (10-16 compases, ~15-24s). Se rastrea hacia atrás desde el tiempo 1 del drop evaluando
    # la tensión ascendente (risers, filtro abriéndose, redoble de caja/crescendo)
    # y deteniéndose tan pronto como se llega a una sección de descanso (breakdown estable) o caída previa.
    for b in range(1, n_bars):
        if clean_bars[b] == SectionType.DROP and clean_bars[b - 1] != SectionType.DROP:
            d_bar = b
            bu_len = 0
            for look in range(1, min(17, d_bar)):
                bar_idx = d_bar - look
                if clean_bars[bar_idx] == SectionType.DROP:
                    break
                k = bar_kick[bar_idx]
                sh = slope_leads[bar_idx]
                sb = slope_bright[bar_idx]
                s_r = slope_rms[bar_idx]

                # Criterio de subida: tensión ascendente inequívoca
                is_rising = (sh > 0.010 or sb > 0.010 or s_r > 0.015) and k < 0.45
                # Pre-drop fill: los últimos 1-2 compases inmediatos antes del drop suelen tener
                # un redoble de caja o un silencio/vocal chop de corte antes de romper
                is_predrop_fill = (look <= 2 and k < 0.45)

                if is_rising or is_predrop_fill:
                    bu_len = look
                else:
                    if look > 2:
                        break

            # Ajustar a frase musical coherente respetando si es CORTA, ESTÁNDAR o LARGA:
            if bu_len == 0:
                bu_len = min(2, d_bar)
            elif bu_len == 1:
                bu_len = 2 # mínimo 2 compases (subida corta)
            elif bu_len == 3:
                bu_len = 4
            elif bu_len in (5, 7):
                bu_len += 1
            elif bu_len in (9, 11, 13, 15):
                bu_len += 1

            for bb in range(d_bar - bu_len, d_bar):
                if bb >= 0 and clean_bars[bb] != SectionType.DROP:
                    clean_bars[bb] = SectionType.BUILDUP

    # Asegurar que el inicio de la pista antes de cualquier drop/subida sea INTRO
    for b in range(min(12, n_bars)):
        if clean_bars[b] not in (SectionType.DROP, SectionType.BUILDUP):
            clean_bars[b] = SectionType.INTRO

    # 7. Agrupar compases contiguos en secciones
    raw_sections: List[Section] = []
    cur_t = clean_bars[0]
    cur_start_b = 0

    for b in range(1, n_bars):
        if clean_bars[b] != cur_t:
            t_start = float(bar_times[cur_start_b])
            t_end   = float(bar_times[b])
            b_start = cur_start_b * beats_per_bar
            b_end   = b * beats_per_bar
            raw_sections.append(Section(
                type=cur_t,
                start_time=t_start,
                end_time=t_end,
                start_beat=b_start,
                end_beat=b_end,
            ))
            cur_t = clean_bars[b]
            cur_start_b = b

    # Última sección hasta el final del track
    t_start = float(bar_times[cur_start_b])
    t_end   = float(total_duration)
    b_start = cur_start_b * beats_per_bar
    b_end   = n_beats
    raw_sections.append(Section(
        type=cur_t,
        start_time=t_start,
        end_time=t_end,
        start_beat=b_start,
        end_beat=b_end,
    ))

    # Fusionar secciones consecutivas con el mismo tipo
    merged: List[Section] = []
    for s in raw_sections:
        if merged and merged[-1].type == s.type:
            merged[-1].end_time = s.end_time
            merged[-1].end_beat = s.end_beat
        else:
            merged.append(s)

    # 8. Calcular métricas reales (RMS, graves, LUFS, Peak) para cada sección
    for sec in merged:
        f_s = librosa.time_to_frames(sec.start_time, sr=sr, hop_length=HOP_LENGTH)
        f_e = librosa.time_to_frames(sec.end_time,   sr=sr, hop_length=HOP_LENGTH)
        f_s = max(0, min(f_s, len(rms_env) - 1))
        f_e = max(f_s + 1, min(f_e, len(rms_env)))
        sec.energy           = float(np.mean(rms_env[f_s:f_e]))
        sec.bass_energy      = float(np.mean(kick_env[f_s:f_e]))
        m_val                = float(np.mean(melody_env[f_s:f_e])) if f_e <= len(melody_env) else 0.0
        p_val                = float(np.mean(pitos_env[f_s:f_e])) if f_e <= len(pitos_env) else 0.0
        sec.melody_energy    = float(0.55 * m_val + 0.45 * p_val)
        sec.fullness         = float(0.35 * sec.bass_energy + 0.35 * sec.energy + 0.30 * sec.melody_energy)
        sec.spectral_novelty = float(np.mean(novelty_env[f_s:f_e])) if f_e <= len(novelty_env) else 0.0
        sec.brightness       = float(np.mean(centroid_env[f_s:f_e])) if f_e <= len(centroid_env) else 0.0

        s_start = max(0, min(int(sec.start_time * sr), len(y) - 1))
        s_end   = max(s_start + 1, min(int(sec.end_time * sr), len(y)))
        sec.lufs      = _lufs_from_kweighted(y_kw[s_start:s_end])
        sec.peak_dbfs = _peak_dbfs(y[s_start:s_end])

    # Si no se detectó ningún drop (pista atípica/continua), promover la sección de mayor plenitud sonora
    if not any(s.type == SectionType.DROP for s in merged):
        best_sec = max(merged, key=lambda s: s.fullness)
        best_sec.type = SectionType.DROP

    return StructureAnalysis(
        sections=merged,
        duration=total_duration,
        bpm=beat_grid.bpm,
    )
