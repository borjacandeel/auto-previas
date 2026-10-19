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


def apply_event_to_chunk(chunk: np.ndarray, sr: int, ev: dict) -> np.ndarray:
    """Aplica un efecto a un trozo de audio estéreo (2, N) con entrada y salida suaves."""
    from src.engine import effects
    n = chunk.shape[1]
    if n < int(0.05 * sr):
        return chunk
    amt = float(ev.get("amount", DEFAULT_AMOUNT))
    kind = ev["type"]
    if kind == "flanger":
        wet = effects.apply_flanger(chunk, sr, rate_hz=0.65, depth_ms=3.8, base_delay_ms=1.0, feedback=0.74,
                                    mix=min(0.95, max(0.1, amt)), ramp_in_sec=min(0.8, n / (sr * 3.0)),
                                    hard_stop=False)
    else:
        top = float(min(9000.0, 400.0 * (2800.0 / 400.0) ** (amt / 0.75)))      # amt 0.75 ≙ 2800 Hz (como antes)
        lo, hi = (60.0, top) if kind == "filter_up" else (top, 60.0)
        wet = effects.apply_filter_sweep(chunk, sr, start_freq=lo, end_freq=hi, kind="highpass", hard_stop=False)
    # entrada y salida suaves para que no haya clics en los bordes del efecto
    k = min(int(EDGE_FADE_SEC * sr), n // 4)
    if k > 1:
        w = np.ones(n, dtype=np.float32)
        w[:k] = np.linspace(0.0, 1.0, k, dtype=np.float32)
        w[-k:] = np.linspace(1.0, 0.0, k, dtype=np.float32)
        return (chunk * (1.0 - w) + wet * w).astype(np.float32)
    return wet


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
            a[:, i0:i1] = apply_event_to_chunk(a[:, i0:i1], sr, ev)
            out[i] = a
    return out
