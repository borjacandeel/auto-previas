"""Sintetiza la música y los efectos del vídeo promocional de AutoPrevias (128 BPM, ~48 s).

Salida: assets/promo-music.mp3  (estéreo, 44,1 kHz).  Los tiempos vienen de choreo.json,
el mismo fichero que usa build_html.py, así que audio e imagen siempre van sincronizados.
Uso: python build_audio.py
"""
import json, subprocess
from pathlib import Path
import numpy as np
from scipy import signal
import soundfile as sf

HERE = Path(__file__).resolve().parent
C = json.loads((HERE / "choreo.json").read_text())
SR = 44100
BEAT = 60.0 / C["bpm"]


def M(t):
    """Tiempo original -> tiempo final (pausas de lectura en tiempos de compás). Igual que en build_html.py / main.js."""
    return t + sum(b * BEAT for p, b in C["holds"] if p <= t + 1e-9)


DUR = M(C["duration"])
N = int(DUR * SR)
TS = {k: M(v) for k, v in C["scenes"].items()}
rng = np.random.default_rng(42)
L = np.zeros(N); R = np.zeros(N)


def tt(d):
    return np.arange(int(d * SR)) / SR


def lp(x, f, o=2):
    return signal.lfilter(*signal.butter(o, f / (SR / 2), "low"), x)


def hp(x, f, o=2):
    return signal.lfilter(*signal.butter(o, f / (SR / 2), "high"), x)


def bp(x, f1, f2, o=2):
    return signal.lfilter(*signal.butter(o, [f1 / (SR / 2), f2 / (SR / 2)], "band"), x)


def put(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N or i < 0:
        return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(0, pan))
    R[i:i + len(sig)] += sig * gain * (1 + min(0, pan))


def kick(vol=1.0):
    t = tt(0.42)
    f = 42 + 130 * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 8.5)
    s += 0.35 * hp(rng.standard_normal(len(t)), 2000) * np.exp(-t * 180)
    return s * vol


def hat(open_=False, vol=1.0):
    t = tt(0.35 if open_ else 0.07)
    s = hp(rng.standard_normal(len(t)), 7500) * np.exp(-t * (16 if open_ else 70))
    return s * vol


def clap(vol=1.0):
    t = tt(0.3)
    n = bp(rng.standard_normal(len(t)), 900, 3800)
    env = np.exp(-t * 22)
    for k in (0.0, 0.011, 0.022):
        env += 0.8 * np.exp(-np.clip(t - k, 0, None) * 120) * (t >= k)
    return n * env * 0.5 * vol


def click(vol=1.0, f=1500):
    t = tt(0.06)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 90) * 0.7 + hp(rng.standard_normal(len(t)), 3000) * np.exp(-t * 400) * 0.6) * vol


def impact(vol=1.0):
    t = tt(2.2)
    f = 60 * np.exp(-t * 1.2) + 28
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    n = lp(rng.standard_normal(len(t)), 2500) * np.exp(-t * 3.0) * 0.5
    c = hp(rng.standard_normal(len(t)), 5000) * np.exp(-t * 2.2) * 0.25
    return (s + n + c) * vol


def whoosh(d=0.9, vol=1.0, up=True):
    t = tt(d)
    n = rng.standard_normal(len(t))
    out = np.zeros(len(t))
    blocks = 18
    edges = np.linspace(0, len(t), blocks + 1).astype(int)
    for b in range(blocks):
        a, z = edges[b], edges[b + 1]
        frac = (b + 0.5) / blocks
        fc = 400 + 5200 * (frac if up else 1 - frac) ** 1.6
        out[a:z] = bp(n[a:z], fc * 0.7, fc * 1.4, 1)
    env = np.sin(np.pi * np.linspace(0, 1, len(t))) ** 1.5
    return out * env * 1.6 * vol


def riser(d, vol=1.0):
    t = tt(d)
    f = 180 * (1 + 9 * (t / d) ** 2)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    n = hp(rng.standard_normal(len(t)), 1800) * (t / d) ** 2 * 0.6
    return (s + n) * (t / d) ** 1.4 * vol


def saw_note(f, d, cut=700, vol=1.0):
    t = tt(d)
    s = signal.sawtooth(2 * np.pi * f * t) + 0.6 * signal.sawtooth(2 * np.pi * f * 1.006 * t)
    s = lp(s, cut)
    env = np.minimum(1, t / 0.005) * np.exp(-t * 7)
    return s * env * vol


def pad(freqs, d, vol=1.0):
    t = tt(d)
    s = np.zeros(len(t))
    for f in freqs:
        for det in (0.994, 1.0, 1.007):
            s += signal.sawtooth(2 * np.pi * f * det * t)
    s = lp(s, 2200) / (len(freqs) * 3)
    env = np.minimum(1, t / 0.08) * np.minimum(1, (d - t) / 0.25)
    return s * env * vol


def beats(n0, n1):
    return [n * BEAT for n in range(n0, n1)]


# ── secciones ────────────────────────────────────────────────────────────
GROOVE = (TS["reveal"], DUR - 0.9)  # beat completo (revelación → final, con fundido)
PUMP = np.ones(N)                # sidechain: baja bajo/pad en cada bombo
for tb in beats(0, int(DUR / BEAT) + 1):
    if GROOVE[0] <= tb < GROOVE[1]:
        i = int(tb * SR)
        m = min(N - i, int(BEAT * SR))
        PUMP[i:i + m] = np.minimum(PUMP[i:i + m], 1 - 0.85 * np.exp(-np.arange(m) / SR * 9))

# gancho (0–3.75): latido grave + riser
for k, tb in enumerate(beats(0, int(round(TS["pain"] / BEAT)))):
    put(kick(0.4), tb, 1.0)
put(riser(TS["pain"] - 0.15, 0.6), 0.0, 0.8)
# dolor (3.75–7.5): reloj + bombo a medio tiempo + tensión
for k, tb in enumerate(np.arange(TS["pain"], M(7.0), BEAT / 2)):
    put(click(0.55, 1900 if k % 2 == 0 else 1350), tb, 1.0, pan=-0.3 if k % 2 else 0.3)
for tb in beats(int(round(TS["pain"] / BEAT)), int(round((TS["reveal"] - BEAT) / BEAT)) + 1):
    if (round(tb / BEAT) % 2) == 0:
        put(kick(0.7), tb, 1.0)
put(riser(TS["reveal"] - TS["pain"] - 0.35, 1.0), TS["pain"] + 0.05, 0.9)
# hueco antes del drop (7.2–7.5) = silencio relativo
# groove completo
for tb in beats(0, int(DUR / BEAT) + 1):
    n = round(tb / BEAT)
    if GROOVE[0] <= tb < GROOVE[1]:
        put(kick(1.0), tb, 1.0)
        put(hat(True, 0.38), tb + BEAT / 2, 0.8, pan=0.2)
        for s16 in (0.25, 0.75):
            put(hat(False, 0.3), tb + BEAT * s16 * 1.0, 0.8, pan=-0.2)
        if n % 2 == 1:
            put(clap(0.9), tb, 0.9)
# bajo (16avos) y acordes
NOTES = [55.0, 55.0, 82.41, 55.0, 98.0, 55.0, 82.41, 73.42]
bar_i = 0
for tb in np.arange(GROOVE[0], GROOVE[1], BEAT / 2):
    idx = int(round((tb - GROOVE[0]) / (BEAT / 2))) % len(NOTES)
    sig = saw_note(NOTES[idx], BEAT / 2 * 0.9, cut=520, vol=0.55)
    i = int(tb * SR)
    m = min(len(sig), N - i)
    if m > 0:
        sig = sig[:m] * PUMP[i:i + m]
        L[i:i + m] += sig; R[i:i + m] += sig
CHORDS = [[220, 261.63, 329.63], [196, 246.94, 293.66], [174.61, 220, 261.63], [196, 246.94, 293.66]]
b = 0
for tb in np.arange(GROOVE[0], GROOVE[1], 4 * BEAT):
    ch = pad(CHORDS[b % 4], 4 * BEAT, 0.5)
    i = int(tb * SR)
    m = min(len(ch), N - i)
    if m > 0:
        ch = ch[:m] * PUMP[i:i + m]
        L[i:i + m] += ch * 0.9; R[i:i + m] += ch * 1.0
    b += 1
# redoble de caja antes de la estadística (24.4–26.25)
ROLL0, ROLL1 = M(C["scenes"]["neon"]) - 4 * BEAT, M(C["scenes"]["neon"])
for k, tb in enumerate(np.arange(ROLL0, ROLL1, BEAT / 4)):
    put(clap(0.45 + 0.04 * k), tb, 0.7)
# cola final: acorde largo + brillo
put(pad([220, 329.63, 440, 523.25], DUR - TS["cta"], 0.7), TS["cta"], 0.9)
for k, f in enumerate([880, 1318.5, 1760, 2093] * 4):
    t = tt(0.9)
    put(np.sin(2 * np.pi * f * t) * np.exp(-t * 4.5) * 0.18, TS["cta"] + 0.18 + k * BEAT, 1.0, pan=(-0.4 if k % 2 else 0.4))

# efectos de edición
for t in C["impacts"]:
    put(impact(0.9 if t not in (0.0,) else 0.6), M(t), 1.0)
for t in C["whooshes"]:
    put(whoosh(0.85, 0.55), max(0.0, M(t) - 0.45), 1.0)
for t in C["slams"]:
    put(impact(0.35), M(t), 1.0)
    put(click(0.9, 220), M(t), 1.0)
for t in C["clicks"]:
    put(click(0.9), M(t), 1.0)
# ding de análisis y de éxito
for t, f in ((13.125, 1318.5), (18.75, 1568.0), (18.9, 2093.0)):
    t = M(t)
    d = tt(1.0)
    put(np.sin(2 * np.pi * f * d) * np.exp(-d * 5) * 0.22, t, 1.0)

# ── masterización ───────────────────────────────────────────────────────
mix = np.stack([L, R], 1)
mix = np.tanh(mix * 0.9) / np.tanh(0.9)
mix /= np.abs(mix).max() / 0.78
fade = np.minimum(1, (DUR - np.arange(N) / SR) / 0.9)
mix *= fade[:, None]
out = HERE / "assets"
out.mkdir(exist_ok=True)
wav = out / "_promo-music.wav"
sf.write(str(wav), mix, SR, subtype="PCM_16")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-codec:a", "libmp3lame", "-b:a", "192k",
                str(out / "promo-music.mp3")], check=True)
wav.unlink()
print("OK", out / "promo-music.mp3")
