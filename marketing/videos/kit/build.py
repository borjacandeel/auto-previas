"""Kit de vídeos de marketing de AutoPrevias (Radical Records).

Cada vídeo es un «spec» (marketing/videos/specs/<id>.py) con una lista de escenas. Este script:
  1) sintetiza la narración (Kokoro, local) y mide su duración → fija la duración de cada escena,
  2) genera el proyecto HyperFrames (index.html + assets) con las escenas animadas,
  3) sintetiza música (128 BPM) y efectos sincronizados con las escenas y mezcla la voz con ducking,
  4) renderiza a MP4 (1080x1920) y lo recomprime para web.

Uso:  python build.py <id> [--no-render] [--no-voice]
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image
from scipy import signal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VID = HERE.parent
PROMO = ROOT / "marketing" / "promo-video"
FIT = 1.6
sys.path.insert(0, str(ROOT))
from src import links as LK  # noqa: E402
SR = 44100
BPM = 128
BEAT = 60.0 / BPM
TTS_PY = Path("/tmp/claude-0/ttsvenv/bin/python")
NODE = ["npx", "--yes", "hyperframes@0.8.151"]


# ───────────────────────────── utilidades de spec ─────────────────────────────

def load_spec(vid: str) -> dict:
    p = VID / "specs" / f"{vid}.py"
    spec = importlib.util.spec_from_file_location(f"spec_{vid}", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.SPEC


_META: dict = {}


def rects(edition: str) -> dict:
    if edition not in _META:
        _META[edition] = json.loads((ROOT / "docs" / "manual" / "_work" / edition / "meta.json").read_text())["rects"]
    return _META[edition]


def center(ed: str, ref):
    if isinstance(ref, (list, tuple)):
        return [float(ref[0]), float(ref[1])]
    st, key = ref.split(".")
    r = rects(ed)[st][key]
    return [(r[0] + r[2] / 2) * FIT, (r[1] + r[3] / 2) * FIT]


def box(ed: str, ref, pad=8):
    if isinstance(ref, (list, tuple)):
        return [float(v) for v in ref]
    st, key = ref.split(".")
    r = rects(ed)[st][key]
    return [r[0] * FIT - pad, r[1] * FIT - pad, r[2] * FIT + 2 * pad, r[3] * FIT + 2 * pad]


def fmt_words(text: str, size: int) -> int:
    return int(min(size, 980 / max(1, len(text)) / 0.74))


# ───────────────────────────── narración ─────────────────────────────

def voice_line(text: str, voice: str, lang: str, speed: float) -> tuple[Path, float]:
    cache = HERE / "vo_cache"
    cache.mkdir(exist_ok=True)
    h = hashlib.sha1(f"{voice}|{lang}|{speed}|{text}".encode()).hexdigest()[:16]
    out = cache / f"{h}.wav"
    if not out.exists():
        subprocess.run([str(TTS_PY), str(HERE / "tts.py"), voice, lang, str(speed), str(out), text], check=True,
                       capture_output=True)
    data, sr = sf.read(str(out))
    return out, len(data) / sr


# ───────────────────────────── HTML de cada escena ─────────────────────────────

def word(text, cls="", size=150, extra=""):
    t = text.replace("'", "&#39;")
    return (f'<div class="word {cls}" style="font-size:{fmt_words(text, size)}px" data-hf-motion-blur=\'{{"samplesPerFrame": 8}}\'>'
            f'<span class="t">{t}</span><span class="g r" data-layout-allow-overlap>{t}</span>'
            f'<span class="g c" data-layout-allow-overlap>{t}</span>{extra}</div>')


def html_words(sc, i):
    lines = sc["lines"]
    n = len(lines)
    top = sc.get("top", max(120, int(960 - n * 120)))
    body = "".join(word(l["t"], l.get("cls", ""), l.get("size", 150), '<i class="strike"></i>' if sc.get("strike", {}).get("line") == k else "")
                   for k, l in enumerate(lines))
    bars = f'<div class="hbars" style="top:{top - 100}px;height:{n * 140 + 300}px"></div>' if sc.get("bars") else ""
    sub = f'<div class="wsub" style="top:{sc.get("sub_top", 1500)}px">{sc["sub"]}</div>' if sc.get("sub") else ""
    return f'{bars}<div class="words" style="top:{top}px">{body}</div>{sub}'


def html_shot(sc, i):
    ed = sc.get("edition", "plus")
    try:
        sc["img_size"] = list(Image.open(ROOT / "docs" / "manual" / "_work" / ed / f"{sc['imgs'][0]['name']}.png").size)
    except Exception:
        sc["img_size"] = None
    caps = "".join(f'<div class="cap"><div class="num">{c["num"]}</div><div class="ttl">{c["title"]}</div><div class="sub">{c["sub"]}</div></div>' for c in sc["caps"])
    imgs = "".join(f'<img class="shot" data-n="{n}" src="assets/{n}.jpg" alt="" />' for n in sorted({m["name"] for m in sc["imgs"]}))
    dlg = f'<img class="dlg" src="assets/{sc["dlg"]["name"]}.jpg" style="left:{sc["dlg"]["x"]}px;top:{sc["dlg"]["y"]}px;width:{sc["dlg"]["w"]}px" alt="" />' if sc.get("dlg") else ""
    chip = f'<div class="chip">{sc["chip"]["text"]}</div>' if sc.get("chip") else ""
    steps = sc.get("steps", 5)
    stepper = "<i></i>" * steps
    return (f'<div class="caps">{caps}</div><div class="vp"><div class="cam">{imgs}<div class="dim"></div>{dlg}<div class="hls"></div>'
            f'{chip}<div class="ripples"></div><div class="cursor"><div class="cin">{ "<svg width=\"40\" height=\"44\" viewBox=\"0 0 40 44\"><path d=\"M4 2 L4 33 L12 26 L18 40 L24 37.5 L18 24 L29 24 Z\" fill=\"#fff\" stroke=\"#05060a\" stroke-width=\"2.6\" stroke-linejoin=\"round\"/></svg>" }</div></div></div></div>'
            f'<div class="conf"></div><div class="stepper">{stepper}</div><div class="stlbl" data-layout-allow-occlusion>AUTOPREVIAS</div>'
            f'<img class="logomini" src="assets/logo_banner.png" alt="" />')


def html_race(sc, i):
    t_top, t_bot = 140, 960
    stamps = "".join(f'<div class="stamp {s.get("cls", "")}" style="left:{s["x"]}px;top:{s["y"]}px">{s["t"]}</div>' for s in sc["stamps_def"])
    return (f'<div class="race">'
            f'<div class="rp"><div class="rlbl" style="top:{t_top}px">A MANO ✂</div><div class="rtimer tA" style="top:{t_top - 30}px;color:#c9ccd8">00:00</div>'
            f'<div class="daw" style="top:{t_top + 110}px"><div class="bar"><b></b><b></b><b></b><span>Proyecto_FINAL_v7_REAL.als</span></div><div class="lanes"></div><div class="playhead"></div></div>{stamps}</div>'
            f'<div class="rp"><div class="rlbl red" style="top:{t_bot}px">AUTOPREVIAS ⚡</div><div class="rtimer tB" style="top:{t_bot - 30}px">00:00</div>'
            f'<div class="rvp" style="top:{t_bot + 110}px;height:470px">' + "".join(f'<img src="assets/{m["name"]}.jpg" alt="" />' for m in sc["imgs"]) +
            f'</div><div class="rdone" style="top:{t_bot + 640}px">LISTO ✓</div></div></div>')


def html_cards(sc, i):
    cards = "".join(f'<img class="ncard" src="assets/{c["src"]}.jpg" style="left:{c["x"]}px;top:{c["y"]}px;width:{c["w"]}px;height:{c["h"]}px" alt="" />' for c in sc["cards"])
    title = f'<div class="ctitle" style="top:{sc.get("title_top", 1370)}px">{word(sc["title"], sc.get("title_cls", ""), sc.get("title_size", 118))}</div>' if sc.get("title") else ""
    sub = f'<div class="csub" style="top:{sc.get("sub_top", 1580)}px">{sc["sub"]}</div>' if sc.get("sub") else ""
    badges = "".join(f'<div class="badge" style="left:{b["x"]}px;top:{b["y"]}px;background:{b.get("bg", "#ff1f3a")};color:{b.get("fg", "#fff")}">{b["t"]}</div>' for b in sc.get("badges", []))
    head = f'<div class="ctitle" style="top:{sc.get("head_top", 120)}px">{word(sc["head"], "red", 96)}</div>' if sc.get("head") else ""
    return head + cards + title + sub + badges


def html_compare(sc, i):
    out = ""
    for p in sc["panels"]:
        items = "".join(f'<div class="it"><b>✓</b>{t}</div>' for t in p["items"])
        out += f'<div class="cpanel {p["cls"]}" style="top:{p["top"]}px"><div class="hd">{p["name"]}</div>{items}</div>'
    return out


def html_tips(sc, i):
    head = f'<div class="ctitle" style="top:150px">{word(sc["head"], "red", 110)}</div>' if sc.get("head") else ""
    tips = ""
    for k, t in enumerate(sc["tips"]):
        tips += (f'<div class="tip" style="top:{t["top"]}px"><div class="n">{t["n"]}</div><div class="bad"><b>✗</b>{t["bad"]}</div>'
                 f'<div class="fix">✓ {t["fix"]}</div></div>')
    return head + tips


def html_gallery(sc, i):
    imgs = "".join(f'<img src="assets/{f["src"]}.jpg" alt="" />' for f in sc["frames"])
    labs = "".join(f'<div class="glabel" style="color:{f["color"]}">{f["label"]}</div>' for f in sc["frames"])
    sws = "".join(f'<i style="background:{f["color"]}"></i>' for f in sc["frames"])
    return f'<div class="gframe">{imgs}</div>{labs}<div class="gsw">{sws}</div>'


def wave_profile(n=120, seed=3):
    rng = np.random.default_rng(seed)
    prof = []
    for k in range(n):
        x = k / n
        if x < 0.14: a = 0.22 + 0.08 * rng.random()
        elif x < 0.34: a = 0.28 + 0.62 * ((x - 0.14) / 0.2) + 0.08 * rng.random()
        elif x < 0.62: a = 0.82 + 0.16 * rng.random()
        elif x < 0.74: a = 0.18 + 0.1 * rng.random()
        elif x < 0.92: a = 0.8 + 0.18 * rng.random()
        else: a = 0.35 - 0.3 * (x - 0.92) / 0.08 + 0.05 * rng.random()
        prof.append(max(0.06, min(1.0, a)))
    return prof


def html_scan(sc, i):
    prof = wave_profile()
    n = len(prof)
    W, H = 960, 420
    bw = W / n
    rects_ = ""
    for k, a in enumerate(prof):
        col = next((s["color"] for s in sc["secs"] if s["from"] <= k / n < s["to"]), "#8a8fa3")
        h = a * (H - 130)
        rects_ += f'<rect x="{k * bw + 1:.1f}" y="{(H - h) / 2 + 40:.1f}" width="{bw - 2:.1f}" height="{h:.1f}" rx="2" fill="{col}"/>'
    lbls = "".join(f'<div class="seclbl" style="left:{s["from"] * W + 4:.0f}px;max-width:{(s["to"] - s["from"]) * W - 8:.0f}px;overflow:hidden;white-space:nowrap;font-size:26px;padding:8px 12px;background:{s["color"]}">{s["name"]}</div>' for s in sc["secs"])
    cards = "".join(f'<div class="scard" style="left:{c["x"]}px;top:{c["y"]}px"><div class="v">{c["v"]}</div><div class="l">{c["l"]}</div></div>' for c in sc["cards"])
    head = word(sc["title"], "red", 100) if sc.get("title") else ""
    return (f'<div style="position:absolute;left:0;right:0;top:300px">{head}</div>'
            f'<div class="wfrap"><svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{rects_}</svg>{lbls}<div class="scanline"></div></div>{cards}')


def html_antileak(sc, i):
    prof = wave_profile(100, 5)
    W, H = 960, 300
    bw = W / len(prof)
    rects_ = "".join(f'<rect x="{k * bw + 1:.1f}" y="{(H - a * 180) / 2 + 30:.1f}" width="{bw - 2:.1f}" height="{a * 180:.1f}" rx="2" fill="#5b6075"/>' for k, a in enumerate(prof))
    marks = "".join(f'<div class="mark" style="left:{m * W - 35:.0f}px"><div class="ic">🎙</div><div class="ln"></div></div>' for m in sc["mark_pos"])
    badges = "".join(f'<div class="badge" style="left:{b["x"]}px;top:{b["y"]}px;background:{b.get("bg", "#ff1f3a")};color:{b.get("fg", "#fff")}">{b["t"]}</div>' for b in sc["badges"])
    head = f'<div style="position:absolute;left:0;right:0;top:230px">{word(sc["title"], "red", 100)}</div>' if sc.get("title") else ""
    return (head + f'<div class="tlbar" style="top:560px"><svg width="{W}" height="{H}">{rects_}</svg>{marks}</div>' + badges +
            f'<div style="position:absolute;left:0;right:0;top:1260px;display:flex;justify-content:center"><div class="stamp big" style="position:relative;font-size:58px">PROMO — NO DISTRIBUIR</div></div>')


def html_tempo(sc, i):
    vals = sc["vals"]
    W, H = 960, 560
    pts = []
    n = 90
    for k in range(n):
        x = k / (n - 1)
        v = 128 + 2.6 * math.sin(x * 9.5) + 1.2 * math.sin(x * 23 + 1)
        pts.append((x * (W - 80) + 40, H / 2 - (v - 128) * 70))
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    ref = H / 2
    head = f'<div style="position:absolute;left:0;right:0;top:230px">{word(sc["title"], "red", 100)}</div>' if sc.get("title") else ""
    badges = "".join(f'<div class="badge" style="left:{b["x"]}px;top:{b["y"]}px;background:{b.get("bg", "#ff1f3a")};color:{b.get("fg", "#fff")}">{b["t"]}</div>' for b in sc.get("badges", []))
    return (head + f'<div class="tempo" style="top:520px"><svg width="{W}" height="{H}"><line x1="40" x2="{W - 40}" y1="{ref}" y2="{ref}" stroke="#3a3f52" stroke-width="4" stroke-dasharray="14 12"/>'
            f'<path class="w" d="{d}" fill="none" stroke="#ff1f3a" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            f'<div class="tnum" style="left:40px;top:20px">128.0</div><div class="tnum" style="right:40px;top:20px;font-size:50px;color:#8a8fa3;opacity:0">BPM</div></div>'
            f'<div class="stamp big" style="left:200px;top:1160px">NO CUADRA ✗</div>' + badges)


def html_folder(sc, i):
    n = sc["n"]
    chips = "".join(f'<div class="fchip">Tema {k + 1:02d}.wav</div>' for k in range(n))
    head = f'<div style="position:absolute;left:0;right:0;top:200px">{word(sc["title"], "red", 100)}</div>' if sc.get("title") else ""
    return (head + f'<div class="fcount fcount" style="top:380px">0 / {n}</div>'
            f'<div class="fgrid" style="top:700px">{chips}</div><div style="position:absolute;left:0;right:0;top:1500px;display:flex;justify-content:center"><div class="stamp big green" style="position:relative;font-size:60px">☕ TÓMATE UN CAFÉ</div></div>')


def html_cta(sc, i):
    letters = "".join(f"<span>{c}</span>" for c in "AUTOPREVIAS")
    cur = '<svg width="40" height="44" viewBox="0 0 40 44"><path d="M4 2 L4 33 L12 26 L18 40 L24 37.5 L18 24 L29 24 Z" fill="#fff" stroke="#05060a" stroke-width="2.6" stroke-linejoin="round"/></svg>'
    lbl = sc.get("buy_lbl", "CÓMPRALO EN")
    if sc.get("dual") and LK.BASIC_URL != LK.PLUS_URL:      # dos enlaces de producto distintos: un botón por edición
        buy = (f'<div class="buy" style="top:1090px;padding:26px 20px;background:linear-gradient(180deg,#3b82f6,#1d4ed8)"><small>BASIC</small>{LK.short(LK.BASIC_URL)}</div>'
               f'<div class="buy" style="top:1290px;padding:26px 20px;background:linear-gradient(180deg,#a855f7,#6d28d9)"><small>PLUS</small>{LK.short(LK.PLUS_URL)}</div>')
    else:
        buy = f'<div class="buy"><small>{lbl}</small>{LK.short(LK.STORE_URL)}</div>'
    return (f'<div class="ctaemb" data-hf-motion-blur=\'{{"samplesPerFrame": 10}}\'><img src="assets/logo_emblem.png" alt="" /></div>'
            f'<div class="ctatitle">{letters}</div><div class="eds"><span class="b">BASIC</span><span class="p">PLUS</span></div>'
            f'<div class="ctaline"><div>{sc["line1"]}</div><div>{sc["line2"]}</div></div>'
            f'{buy}'
            f'<img class="ctabanner" src="assets/logo_banner.png" alt="" /><div class="ctatag">{sc.get("tag", "macOS · Windows · Radical Records")}</div>'
            f'<div class="rip2"></div><div class="cur2" data-layout-allow-overflow data-hf-motion-blur=\'{{"samplesPerFrame": 12, "shutterAngle": 540}}\'><div class="cin">{cur}</div></div>')


HTML = dict(words=html_words, shot=html_shot, race=html_race, cards=html_cards, compare=html_compare, tips=html_tips,
            gallery=html_gallery, scan=html_scan, antileak=html_antileak, tempo=html_tempo, folder=html_folder, cta=html_cta)


# ───────────────────────────── resolución de escenas (tiempos y objetivos) ─────────────────────────────

def resolve_scene(sc: dict):
    t = sc["type"]
    ed = sc.get("edition", "plus")
    if t == "words":
        n = len(sc["lines"])
        gap = sc.get("gap", 0.42)
        sc.setdefault("at", [0.15 + k * gap for k in range(n)])
        sc.setdefault("sub_at", sc["at"][-1] + 0.6)
        if "strike" in sc:
            sc["strike"] = dict(sc["strike"])
    elif t == "shot":
        sc["cam"] = [dict(a, cx=center(ed, a["c"])[0], cy=center(ed, a["c"])[1]) if "c" in a and not isinstance(a["c"], (int, float)) else a for a in sc["cam"]]
        for a in sc["cam"]:
            if "c" in a:
                a["cx"], a["cy"] = center(ed, a["c"])
        cur = []
        for m in sc.get("cur", []):
            if "set" in m:
                x, y = center(ed, m["set"]); cur.append(dict(at=m["at"], set=True, x=x, y=y))
            else:
                x, y = center(ed, m["to"]); cur.append(dict(at=m["at"], d=m["d"], x=x + m.get("dx", 0), y=y + m.get("dy", 0)))
        sc["cur"] = cur
        sc["clicks"] = [dict(at=c["at"], x=center(ed, c["to"])[0], y=center(ed, c["to"])[1]) for c in sc.get("clicks", [])]
        sc["hls"] = [dict(at=h["at"], hold=h.get("hold", 0.4), box=box(ed, h["box"], h.get("pad", 8))) for h in sc.get("hls", [])]
        if sc.get("chip"):
            c = sc["chip"]
            c["to"] = center(ed, c["to"]) if not isinstance(c["to"], list) else c["to"]
        sc["imgs"] = [dict(at=m["at"], id=m["name"], name=m["name"]) for m in sc["imgs"]]
    elif t == "gallery":
        pass
    return sc


# ───────────────────────────── eventos de sonido ─────────────────────────────

def sfx_events(sc: dict, i: int):
    t0 = sc["t0"]
    ev = []
    if i > 0:
        ev.append((t0 - 0.45, "whoosh", 0.5))
    ev.append((t0, "impact", 0.7 if sc["type"] != "cta" else 0.9))
    ty = sc["type"]
    if ty == "words":
        ev += [(t0 + a, "slam", 0.9) for a in sc["at"]]
        if sc.get("strike"):
            ev.append((t0 + sc["strike"]["at"], "slam", 0.7))
    elif ty == "shot":
        ev += [(t0 + c["at"], "click", 0.9) for c in sc["clicks"]]
        ev += [(t0 + m["at"], "whoosh", 0.4) for k, m in enumerate(sc["imgs"]) if k]
        if sc.get("confetti") is not None:
            ev += [(t0 + sc["confetti"], "ding", 0.8), (t0 + sc["confetti"] + 0.15, "ding2", 0.8)]
    elif ty == "race":
        ev += [(t0 + a, "stamp", 0.8) for a in sc["stamps"]]
        ev += [(t0 + sc["done_at"], "ding", 0.9), (t0 + sc["done_at"] + 0.15, "ding2", 0.9)]
    elif ty == "cards":
        ev += [(t0 + c["at"], "pop", 0.8) for c in sc["cards"]]
        if sc.get("title"):
            ev.append((t0 + sc["title_at"], "slam", 0.8))
        ev += [(t0 + b["at"], "pop", 0.7) for b in sc.get("badges", [])]
    elif ty == "compare":
        for p in sc["panels"]:
            ev.append((t0 + p["at"], "pop", 0.8))
            ev += [(t0 + a, "tick", 0.7) for a in p["items_at"]]
    elif ty == "tips":
        for p in sc["tips"]:
            ev += [(t0 + p["at"], "stamp", 0.8), (t0 + p["fix_at"], "ding", 0.6)]
    elif ty == "gallery":
        ev += [(t0 + f["at"], "slam", 0.7) for f in sc["frames"]]
    elif ty == "scan":
        ev += [(t0 + sc["sweep_at"] + sc["sweep_d"] * s["from"], "hit" if s.get("hit") else "tick", 0.8) for s in sc["secs"]]
        ev += [(t0 + c["at"], "pop", 0.8) for c in sc["cards"]]
    elif ty == "antileak":
        ev += [(t0 + a, "pop", 0.8) for a in sc["marks"]]
        ev += [(t0 + b["at"], "pop", 0.7) for b in sc["badges"]]
        ev.append((t0 + sc["stamp_at"], "stamp", 1.0))
    elif ty == "tempo":
        ev.append((t0 + sc["stamp_at"], "stamp", 1.0))
        ev += [(t0 + b["at"], "pop", 0.7) for b in sc.get("badges", [])]
    elif ty == "folder":
        n = sc["n"]
        ev += [(t0 + sc["run_at"] + sc["run_d"] * math.pow(k / (n - 1), 0.8), "tick", 0.5) for k in range(n)]
        ev += [(t0 + sc["run_at"] + sc["run_d"], "ding", 0.9), (t0 + sc["run_at"] + sc["run_d"] + 0.15, "ding2", 0.9)]
    elif ty == "cta":
        ev += [(t0 + sc["click_at"], "click", 1.0), (t0 + sc["click_at"] + 0.05, "ding", 0.6)]
    return ev


# ───────────────────────────── síntesis de audio ─────────────────────────────

class Synth:
    def __init__(self, dur):
        self.N = int(dur * SR)
        self.L = np.zeros(self.N)
        self.R = np.zeros(self.N)
        self.rng = np.random.default_rng(42)

    def tt(self, d):
        return np.arange(int(d * SR)) / SR

    def lp(self, x, f, o=2):
        return signal.lfilter(*signal.butter(o, f / (SR / 2), "low"), x)

    def hp(self, x, f, o=2):
        return signal.lfilter(*signal.butter(o, f / (SR / 2), "high"), x)

    def bp(self, x, f1, f2, o=2):
        return signal.lfilter(*signal.butter(o, [f1 / (SR / 2), f2 / (SR / 2)], "band"), x)

    def put(self, sig, t, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i >= self.N or i < 0:
            if i < 0:
                sig = sig[-i:]; i = 0
            else:
                return
        sig = sig[: self.N - i]
        self.L[i:i + len(sig)] += sig * gain * (1 - max(0, pan))
        self.R[i:i + len(sig)] += sig * gain * (1 + min(0, pan))

    def kick(self, vol=1.0):
        t = self.tt(0.42); f = 42 + 130 * np.exp(-t * 32)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8.5)
        s += 0.35 * self.hp(self.rng.standard_normal(len(t)), 2000) * np.exp(-t * 180)
        return s * vol

    def hat(self, open_=False, vol=1.0):
        t = self.tt(0.35 if open_ else 0.07)
        return self.hp(self.rng.standard_normal(len(t)), 7500) * np.exp(-t * (16 if open_ else 70)) * vol

    def clap(self, vol=1.0):
        t = self.tt(0.3); n = self.bp(self.rng.standard_normal(len(t)), 900, 3800); env = np.exp(-t * 22)
        for k in (0.0, 0.011, 0.022):
            env += 0.8 * np.exp(-np.clip(t - k, 0, None) * 120) * (t >= k)
        return n * env * 0.5 * vol

    def click(self, vol=1.0, f=1500):
        t = self.tt(0.06)
        return (np.sin(2 * np.pi * f * t) * np.exp(-t * 90) * 0.7 + self.hp(self.rng.standard_normal(len(t)), 3000) * np.exp(-t * 400) * 0.6) * vol

    def impact(self, vol=1.0):
        t = self.tt(2.2); f = 60 * np.exp(-t * 1.2) + 28
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
        n = self.lp(self.rng.standard_normal(len(t)), 2500) * np.exp(-t * 3.0) * 0.5
        c = self.hp(self.rng.standard_normal(len(t)), 5000) * np.exp(-t * 2.2) * 0.25
        return (s + n + c) * vol

    def whoosh(self, d=0.9, vol=1.0):
        t = self.tt(d); n = self.rng.standard_normal(len(t)); out = np.zeros(len(t)); blocks = 18
        edges = np.linspace(0, len(t), blocks + 1).astype(int)
        for b in range(blocks):
            a, z = edges[b], edges[b + 1]; frac = (b + 0.5) / blocks
            fc = 400 + 5200 * frac ** 1.6
            out[a:z] = self.bp(n[a:z], fc * 0.7, fc * 1.4, 1)
        return out * np.sin(np.pi * np.linspace(0, 1, len(t))) ** 1.5 * 1.6 * vol

    def riser(self, d, vol=1.0):
        t = self.tt(d); f = 180 * (1 + 9 * (t / d) ** 2)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
        n = self.hp(self.rng.standard_normal(len(t)), 1800) * (t / d) ** 2 * 0.6
        return (s + n) * (t / d) ** 1.4 * vol

    def saw_note(self, f, d, cut=700, vol=1.0):
        t = self.tt(d)
        s = signal.sawtooth(2 * np.pi * f * t) + 0.6 * signal.sawtooth(2 * np.pi * f * 1.006 * t)
        return self.lp(s, cut) * np.minimum(1, t / 0.005) * np.exp(-t * 7) * vol

    def pad(self, freqs, d, vol=1.0):
        t = self.tt(d); s = np.zeros(len(t))
        for f in freqs:
            for det in (0.994, 1.0, 1.007):
                s += signal.sawtooth(2 * np.pi * f * det * t)
        s = self.lp(s, 2200) / (len(freqs) * 3)
        return s * np.minimum(1, t / 0.08) * np.minimum(1, (d - t) / 0.25) * vol

    def ding(self, f, vol=1.0):
        d = self.tt(1.0)
        return np.sin(2 * np.pi * f * d) * np.exp(-d * 5) * 0.22 * vol


def make_audio(spec: dict, scenes: list, dur: float, vo: list, out: Path):
    s = Synth(dur)
    g0 = spec["groove_from"]
    g1 = dur - 0.9
    # compás: bombo suave antes del groove + riser
    nb = int(dur / BEAT) + 1
    for k in range(nb):
        tb = k * BEAT
        if tb < g0 - 0.2:
            s.put(s.kick(0.35), tb, 1.0)
    if g0 > 1.0:
        s.put(s.riser(min(g0, 3.4), 0.7), max(0.0, g0 - min(g0, 3.4)), 0.8)
    pump = np.ones(s.N)
    for k in range(nb):
        tb = k * BEAT
        if g0 <= tb < g1:
            i = int(tb * SR); m = min(s.N - i, int(BEAT * SR))
            pump[i:i + m] = np.minimum(pump[i:i + m], 1 - 0.85 * np.exp(-np.arange(m) / SR * 9))
    for k in range(nb):
        tb = k * BEAT
        if g0 <= tb < g1:
            s.put(s.kick(1.0), tb, 1.0)
            s.put(s.hat(True, 0.38), tb + BEAT / 2, 0.8, pan=0.2)
            for s16 in (0.25, 0.75):
                s.put(s.hat(False, 0.3), tb + BEAT * s16, 0.8, pan=-0.2)
            if k % 2 == 1:
                s.put(s.clap(0.9), tb, 0.9)
    NOTES = [55.0, 55.0, 82.41, 55.0, 98.0, 55.0, 82.41, 73.42]
    for tb in np.arange(g0, g1, BEAT / 2):
        idx = int(round((tb - g0) / (BEAT / 2))) % len(NOTES)
        sig = s.saw_note(NOTES[idx], BEAT / 2 * 0.9, cut=520, vol=0.5)
        i = int(tb * SR); m = min(len(sig), s.N - i)
        if m > 0:
            sig = sig[:m] * pump[i:i + m]; s.L[i:i + m] += sig; s.R[i:i + m] += sig
    CH = [[220, 261.63, 329.63], [196, 246.94, 293.66], [174.61, 220, 261.63], [196, 246.94, 293.66]]
    for b, tb in enumerate(np.arange(g0, g1, 4 * BEAT)):
        ch = s.pad(CH[b % 4], 4 * BEAT, 0.45); i = int(tb * SR); m = min(len(ch), s.N - i)
        if m > 0:
            ch = ch[:m] * pump[i:i + m]; s.L[i:i + m] += ch * 0.9; s.R[i:i + m] += ch
    # música más baja bajo la voz (ducking)
    duck = np.ones(s.N)
    for (t0, t1) in [(v[0], v[1]) for v in vo]:
        a, b = int(max(0, t0 - 0.15) * SR), int(min(dur, t1 + 0.25) * SR)
        env = np.ones(b - a) * 0.38
        r = int(0.15 * SR)
        env[:r] = np.linspace(1, 0.38, r); env[-r:] = np.linspace(0.38, 1, r)
        duck[a:b] = np.minimum(duck[a:b], env)
    s.L *= duck; s.R *= duck
    # efectos (no se duckean)
    for sc_i, sc in enumerate(scenes):
        for (t, kind, v) in sfx_events(sc, sc_i):
            if kind == "whoosh":
                s.put(s.whoosh(0.85, 0.5 * v), max(0.0, t - 0.0), 1.0)
            elif kind == "impact":
                s.put(s.impact(0.8 * v), t, 1.0)
            elif kind == "slam":
                s.put(s.impact(0.35 * v), t, 1.0); s.put(s.click(0.9 * v, 220), t, 1.0)
            elif kind == "click":
                s.put(s.click(0.9 * v), t, 1.0)
            elif kind == "tick":
                s.put(s.click(0.5 * v, 2200), t, 1.0, pan=0.2)
            elif kind == "pop":
                s.put(s.click(0.7 * v, 1000), t, 1.0); s.put(s.impact(0.15 * v), t, 1.0)
            elif kind == "stamp":
                s.put(s.impact(0.5 * v), t, 1.0); s.put(s.click(0.9 * v, 180), t, 1.0)
            elif kind == "hit":
                s.put(s.impact(0.6 * v), t, 1.0); s.put(s.click(0.8 * v, 330), t, 1.0)
            elif kind == "ding":
                s.put(s.ding(1568.0, v), t, 1.0)
            elif kind == "ding2":
                s.put(s.ding(2093.0, v), t, 1.0)
    # voz
    voice = np.zeros((s.N, 2))
    for (t0, t1, path) in vo:
        d, sr = sf.read(str(path))
        if d.ndim > 1:
            d = d.mean(axis=1)
        if sr != SR:
            d = signal.resample(d, int(len(d) * SR / sr))
        rms = np.sqrt(np.mean(d ** 2)) + 1e-9
        d = d * (0.115 / rms)
        d = np.clip(d, -0.9, 0.9)
        i = int(t0 * SR); m = min(len(d), s.N - i)
        voice[i:i + m, 0] += d[:m]; voice[i:i + m, 1] += d[:m]
    mix = np.stack([s.L, s.R], 1)
    mix = np.tanh(mix * 0.9) / np.tanh(0.9)
    mix /= max(1e-6, np.abs(mix).max() / 0.55)
    mix = mix + voice * 1.0
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix /= max(1e-6, np.abs(mix).max() / 0.85)
    fade = np.minimum(1, (dur - np.arange(s.N) / SR) / 0.9)
    mix *= fade[:, None]
    wav = out.with_suffix(".wav")
    sf.write(str(wav), mix, SR, subtype="PCM_16")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-codec:a", "libmp3lame", "-b:a", "192k", str(out)], check=True)
    wav.unlink()


# ───────────────────────────── proyecto HyperFrames ─────────────────────────────

SCENE_CLS = "scene clip"


def build(vid: str, render=True, voice=True):
    spec = load_spec(vid)
    work = VID / "work" / vid
    if work.exists():
        shutil.rmtree(work)
    (work / "assets" / "fonts").mkdir(parents=True)
    (work / "compositions" / "components").mkdir(parents=True)
    for f in ("hyperframes.json", "package.json", "meta.json"):
        shutil.copy(PROMO / f, work / f)
    shutil.copy(PROMO / "compositions" / "components" / "motion-blur.html", work / "compositions" / "components")
    for f in (PROMO / "assets" / "fonts").iterdir():
        shutil.copy(f, work / "assets" / "fonts" / f.name)
    for f in ("grain.png", "logo_emblem.png", "logo_banner.png"):
        shutil.copy(PROMO / "assets" / f, work / "assets" / f)

    # escenas: voz → duración
    t = 0.0
    scenes = [resolve_scene(dict(sc)) for sc in spec["scenes"]]
    vo = []
    for k, sc in enumerate(scenes):
        sc["t0"] = t
        d = float(sc.get("dur", 3.0))
        if sc.get("vo") and voice:
            path, vlen = voice_line(sc["vo"], sc.get("voice", spec["voice"]), spec["lang"], spec.get("speed", 1.0))
            at = sc.get("vo_at", 0.3)
            d = max(d, at + vlen + sc.get("vo_pad", 0.45))
            vo.append((t + at, t + at + vlen, path))
        sc["dur"] = d
        t += d
    total = t
    for sc in scenes:
        if sc["type"] == "cta" and sc["dur"] < 6.5:
            pass

    # imágenes necesarias
    def need(name, edition="plus"):
        dst = work / "assets" / f"{name}.jpg"
        if dst.exists():
            return
        src = ROOT / "docs" / "manual" / "_work" / edition / f"{name}.png"
        if src.exists():
            Image.open(src).convert("RGB").save(dst, quality=90, optimize=True)
            return
        st = VID / "stills" / f"{name}.jpg"
        if st.exists():
            shutil.copy(st, dst)
            return
        raise FileNotFoundError(name)

    for sc in scenes:
        ed = sc.get("edition", "plus")
        if sc["type"] == "shot":
            for m in sc["imgs"]:
                need(m["name"], ed)
            if sc.get("dlg"):
                need(sc["dlg"]["name"], ed)
        elif sc["type"] == "race":
            for m in sc["imgs"]:
                need(m["name"], ed)
        elif sc["type"] == "cards":
            for c in sc["cards"]:
                need(c["src"])
        elif sc["type"] == "gallery":
            for f in sc["frames"]:
                need(f["src"])

    # HTML
    sc_html = ""
    for k, sc in enumerate(scenes):
        body = HTML[sc["type"]](sc, k)
        sc_html += (f'<div class="scene clip" id="s{k}" data-start="{sc["t0"]:.3f}" data-duration="{sc["dur"]:.3f}">{body}</div>\n')
    # groove
    spec_out = dict(bpm=BPM, dur=total, seed=spec.get("seed", 2026), groove=[spec["groove_from"], total - 0.9],
                    scenes=[{k: v for k, v in sc.items() if k not in ("vo",)} for sc in scenes])
    css = (HERE / "scenes.css").read_text()
    js = (HERE / "runtime.js").read_text()
    mb = (PROMO / "compositions" / "components" / "motion-blur.html").read_text()
    i0 = mb.index("<script>"); j0 = mb.index("</script>", i0) + len("</script>")
    html = f"""<!doctype html>
<html lang="{spec['lang']}"><head><meta charset="UTF-8" /><meta name="viewport" content="width=1080, height=1920" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{css}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="1080" data-height="1920" data-fps="30">
<div id="bg"></div><div id="gridlines"></div>
<div id="world">
{sc_html}</div>
<div id="pulse" data-layout-allow-occlusion></div><div id="tear" data-layout-allow-occlusion></div><div id="flashred" data-layout-allow-occlusion></div><div id="flash" data-layout-allow-occlusion></div><div id="scan" data-layout-allow-occlusion></div><div id="vig" data-layout-allow-occlusion></div><div id="grain" data-layout-allow-occlusion></div>
<audio id="music" src="assets/music.mp3" data-start="0" data-duration="{total:.3f}" data-volume="1"></audio>
</div>
<script>window.SPEC = {json.dumps(spec_out, ensure_ascii=False)};</script>
<script>{js}</script>
{mb[i0:j0]}
</body></html>"""
    (work / "index.html").write_text(html, encoding="utf-8")
    print(f"[{vid}] {len(scenes)} escenas · {total:.1f}s · voz: {len(vo)} líneas")
    make_audio(spec, scenes, total, vo, work / "assets" / "music.mp3")
    if not render:
        return work
    out = VID / "out"
    out.mkdir(exist_ok=True)
    raw = work / "render.mp4"
    log = (work / "render.log").open("w")
    subprocess.run(NODE + ["render", "-o", str(raw)], cwd=work, stdout=log, stderr=subprocess.STDOUT, check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-c:v", "libx264", "-crf", "25", "-preset", "slow",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out / f"{vid}.mp4")], check=True)
    print(f"[{vid}] listo → {out / (vid + '.mp4')}")
    return work


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    build(args[0], render="--no-render" not in sys.argv, voice="--no-voice" not in sys.argv)
