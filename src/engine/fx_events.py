"""
AutoPrevias — Efectos manuales colocados por el usuario en la forma de onda.

Cada efecto es un evento {id, type, start, end, amount} con tiempos del TEMA ORIGINAL (segundos).
Al montar la previa se aplica a cada bloque de audio extraído la parte que se solapa con el evento, así
el efecto «viaja» con su trozo aunque se reordenen los cortes. Lo que cae fuera de los cortes no suena.

Tipos: «flanger», «filter_up» (barrido de filtro hacia arriba: sube la tensión) y «filter_down»
(barrido hacia abajo: el filtro se abre de nuevo).
"""
from __future__ import annotations

from typing import Iterable, List

import numpy as np

FX_TYPES = ("flanger", "filter_up", "filter_down")
FX_LABELS = {
    "flanger": "Flanger",
    "filter_up": "Filter Sweep ↗",
    "filter_down": "Filter Sweep ↘",
}
FX_ICONS = {"flanger": "🌀", "filter_up": "🌊", "filter_down": "🌊"}
DEFAULT_DURATION = {"flanger": 6.0, "filter_up": 8.0, "filter_down": 8.0}
DEFAULT_AMOUNT = 0.75
MIN_DURATION = 0.5
MAX_DURATION = 60.0
MAX_EVENTS = 24
EDGE_FADE_SEC = 0.012          # entrada/salida suave del efecto (sin clics)


def normalize_events(events: Iterable[dict] | None, duration: float | None = None) -> List[dict]:
    """Limpia la lista: tipos válidos, tiempos dentro del tema, duración y cantidad razonables."""
    out: List[dict] = []
    nxt = 1
    for ev in list(events or []):
        if not isinstance(ev, dict) or ev.get("type") not in FX_TYPES:
            continue
        try:
            s = float(ev.get("start", 0.0))
            e = float(ev.get("end", s + DEFAULT_DURATION[ev["type"]]))
            amt = float(ev.get("amount", DEFAULT_AMOUNT))
        except (TypeError, ValueError):
            continue
        if not (np.isfinite(s) and np.isfinite(e) and np.isfinite(amt)):
            continue
        s = max(0.0, s)
        if duration and duration > 0:
            s = min(s, max(0.0, duration - MIN_DURATION))
            e = min(e, duration)
        e = min(e, s + MAX_DURATION)
        if e - s < MIN_DURATION:
            e = s + MIN_DURATION
            if duration and duration > 0 and e > duration:
                continue
        try:
            eid = int(ev.get("id", 0)) or nxt
        except (TypeError, ValueError):
            eid = nxt
        nxt = max(nxt, eid) + 1
        out.append({"id": eid, "type": ev["type"], "start": round(s, 3), "end": round(e, 3),
                    "amount": round(min(1.0, max(0.1, amt)), 2)})
        if len(out) >= MAX_EVENTS:
            break
    out.sort(key=lambda d: (d["start"], d["id"]))
    return out


RAMP_FRACTION = 0.3            # v6.5.3: el efecto entra y sale de forma progresiva (30 % del efecto en cada extremo)
RAMP_MAX_SEC = 4.0
# Cuánto de cada extremo es rampa, por tipo: el barrido ↗ debe llegar arriba (sale más corto); el ↘ entra más directo
RAMPS = {"flanger": (0.3, 0.3), "filter_up": (0.25, 0.1), "filter_down": (0.1, 0.25)}


def progressive_envelope(n: int, sr: int, t0: float = 0.0, ev_len: float | None = None,
                         ramp_in: float = RAMP_FRACTION, ramp_out: float = RAMP_FRACTION) -> np.ndarray:
    """Peso del efecto (0→1→0) para un trozo de `n` muestras que empieza `t0` s después del inicio del efecto.

    Sube suave al principio y baja suave al final (curva coseno), así el efecto «entra» y «sale» poco a poco."""
    ev_len = float(ev_len) if ev_len else n / float(sr)
    t = t0 + np.arange(n, dtype=np.float64) / float(sr)
    r_in = max(EDGE_FADE_SEC, min(RAMP_MAX_SEC, ramp_in * ev_len))
    r_out = max(EDGE_FADE_SEC, min(RAMP_MAX_SEC, ramp_out * ev_len))
    up = np.clip(t / r_in, 0.0, 1.0)
    down = np.clip((ev_len - t) / r_out, 0.0, 1.0)
    w = np.minimum(up, down)
    return (0.5 - 0.5 * np.cos(np.pi * w)).astype(np.float32)


def apply_event_to_chunk(chunk: np.ndarray, sr: int, ev: dict, t0: float = 0.0,
                         ev_len: float | None = None) -> np.ndarray:
    """Aplica un efecto a un trozo de audio estéreo (2, N) con entrada y salida progresivas.

    `t0` = segundos desde el inicio del efecto hasta el inicio del trozo; `ev_len` = duración total del efecto
    (por defecto, el propio trozo). Así, si el efecto cae en dos cortes, la subida y la bajada siguen siendo una sola."""
    from src.engine import effects
    n = chunk.shape[1]
    if n < int(0.05 * sr):
        return chunk
    amt = float(ev.get("amount", DEFAULT_AMOUNT))
    kind = ev["type"]
    if kind == "flanger":
        # v6.2: más marcado (más profundidad, más realimentación y mezcla mínima del 55 %) para que se note en cualquier tema
        wet = effects.fast_flanger(chunk, sr, amount=amt)
    else:
        top = float(min(9000.0, 500.0 * 10.0 ** (amt / 0.75)))                   # amt 0.75 ≙ 5 kHz: se nota mucho más que antes (2,8 kHz)
        lo, hi = (60.0, top) if kind == "filter_up" else (top, 60.0)
        wet = effects.apply_filter_sweep(chunk, sr, start_freq=lo, end_freq=hi, kind="highpass", hard_stop=False, order=4)
    r_in, r_out = RAMPS.get(kind, (RAMP_FRACTION, RAMP_FRACTION))
    w = progressive_envelope(n, sr, t0, ev_len, r_in, r_out)
    return (chunk * (1.0 - w) + wet * w).astype(np.float32)


def apply_events_to_blocks(block_audios: List[np.ndarray], blocks: List[List[float]], sr: int,
                           events: Iterable[dict] | None, progress_cb=None) -> List[np.ndarray]:
    """Aplica los eventos a cada bloque (tiempos de origen b_s..b_e) en el solape de ambos. Devuelve la lista."""
    evs = normalize_events(events)
    if not evs:
        return block_audios
    out = list(block_audios)
    total = max(1, len(evs))
    for k, ev in enumerate(evs):
        if progress_cb:
            progress_cb(k, total)
        for i, (b_s, b_e) in enumerate(blocks):
            lo, hi = max(ev["start"], b_s), min(ev["end"], b_e)
            if hi - lo < 0.05:
                continue
            a = out[i]
            if a.ndim == 1:
                a = np.stack([a, a])
            i0 = max(0, int(round((lo - b_s) * sr)))
            i1 = min(a.shape[1], int(round((hi - b_s) * sr)))
            if i1 - i0 < int(0.05 * sr):
                continue
            a = a.copy()
            a[:, i0:i1] = apply_event_to_chunk(a[:, i0:i1], sr, ev, t0=lo - ev["start"], ev_len=ev["end"] - ev["start"])
            out[i] = a
    return out


def render_effect_preview(source_path: str, ev: dict, pad: float = 2.0):
    """Prepara la escucha de UN efecto: el trozo del tema original (con `pad` s antes y después) con el efecto aplicado.

    Devuelve (audio estéreo (2, N) float32, frecuencia de muestreo). No toca el resto de la previa."""
    import soundfile as sf
    s0, e0 = float(ev["start"]), float(ev["end"])
    t0 = max(0.0, s0 - pad)
    audio = None
    sr = 0
    try:
        info = sf.info(source_path)
        sr = int(info.samplerate)
        i0 = int(t0 * sr)
        n = int((e0 + pad) * sr) - i0
        data, _ = sf.read(source_path, start=i0, frames=max(1, n), dtype="float32", always_2d=True)
        audio = data.T
    except Exception:
        from src.engine.audio_io import load_audio_file
        y, sr = load_audio_file(source_path, sr=None, mono=False)
        y = np.asarray(y, dtype=np.float32)
        if y.ndim == 1:
            y = y[None, :]
        audio = y[:, int(t0 * sr):int((e0 + pad) * sr)]
    if audio.shape[0] == 1:
        audio = np.vstack([audio, audio])
    audio = audio[:2].astype(np.float32, copy=True)
    a = max(0, int(round((s0 - t0) * sr)))
    b = min(audio.shape[1], a + int(round((e0 - s0) * sr)))
    if b - a >= int(0.05 * sr):
        audio[:, a:b] = apply_event_to_chunk(audio[:, a:b], sr, ev)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.98:
        np.clip(audio, -0.98, 0.98, out=audio)            # solo recorta los picos: no cambia el volumen de lo que suena antes y después
    k = min(int(0.02 * sr), audio.shape[1] // 4)
    if k > 1:
        audio[:, :k] *= np.linspace(0.0, 1.0, k, dtype=np.float32)
        audio[:, -k:] *= np.linspace(1.0, 0.0, k, dtype=np.float32)
    return audio, sr


def apply_events_to_source(audio: np.ndarray, sr: int, events: Iterable[dict] | None) -> np.ndarray:
    """v6.5.3: el tema ORIGINAL entero con los efectos aplicados en su sitio (para oírlos al reproducir, sin «▶ Oír»).

    `audio` es estéreo (2, N); devuelve una copia del mismo tamaño (los tiempos no cambian)."""
    out = audio
    copied = False
    for ev in normalize_events(events, audio.shape[1] / float(sr)):
        i0 = max(0, int(round(ev["start"] * sr)))
        i1 = min(audio.shape[1], int(round(ev["end"] * sr)))
        if i1 - i0 < int(0.05 * sr):
            continue
        if not copied:
            out = audio.copy()
            copied = True
        out[:, i0:i1] = apply_event_to_chunk(out[:, i0:i1], sr, ev)
    if copied:
        np.clip(out, -0.999, 0.999, out=out)
    return out

