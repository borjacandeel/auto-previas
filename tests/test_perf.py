"""Rendimiento: política de hilos según el equipo y, sobre todo, que acelerar NO cambia ningún resultado."""
import os

import numpy as np
import pytest

import src.perf as perf
from src.analysis import fastdsp


@pytest.fixture(autouse=True)
def _aislado(tmp_path, monkeypatch):
    import src.config as C
    monkeypatch.setattr(C, "get_config_path", lambda: tmp_path / "cfg_test.json")
    monkeypatch.delenv("AUTOPREVIAS_THREADS", raising=False)
    monkeypatch.setattr(perf, "_MODE", None)
    yield
    perf._MODE = None


def _equipo(monkeypatch, cores, ram):
    monkeypatch.setattr(perf, "cpu_cores", lambda: cores)
    monkeypatch.setattr(perf, "total_ram_gb", lambda: ram)


def test_politica_de_hilos_segun_equipo_y_modo(monkeypatch):
    _equipo(monkeypatch, 10, 32)
    assert perf.threads("analysis") == 8 and perf.threads("render") == 8      # auto: casi todo, sin pasar de 8
    perf.set_mode("high", persist=False); assert perf.threads("render") == 10
    perf.set_mode("low", persist=False); assert perf.threads("analysis") == 2
    _equipo(monkeypatch, 4, 16)
    perf.set_mode("auto", persist=False); assert perf.threads("analysis") == 3  # deja un núcleo libre para la interfaz
    _equipo(monkeypatch, 8, 6); assert perf.threads("analysis") == 2            # poca RAM: menos hilos
    _equipo(monkeypatch, 8, 3); assert perf.threads("analysis") == 1
    _equipo(monkeypatch, 2, 16); assert perf.threads("analysis") == 1
    _equipo(monkeypatch, 4, 16); perf.set_mode("low", persist=False); assert perf.threads("analysis") == 2
    _equipo(monkeypatch, 1, 16); perf.set_mode("low", persist=False); assert perf.threads("analysis") == 1


def test_variable_de_entorno_fuerza_los_hilos(monkeypatch):
    _equipo(monkeypatch, 16, 64)
    monkeypatch.setenv("AUTOPREVIAS_THREADS", "1")
    assert perf.threads("analysis") == 1 and perf.threads("render") == 1 and perf.ffmpeg_threads() == 1
    monkeypatch.setenv("AUTOPREVIAS_THREADS", "5")
    assert perf.threads("render") == 5


def test_el_modo_se_guarda_y_se_lee(monkeypatch):
    perf.set_mode("low")
    perf._MODE = None
    assert perf.get_mode() == "low"
    perf.set_mode("raro", persist=False)
    assert perf.get_mode() == "auto"


def test_ffmpeg_solo_se_limita_en_ahorro(monkeypatch):
    _equipo(monkeypatch, 8, 16)
    assert perf.ffmpeg_threads() == 0                        # automático y máximo: lo decide FFmpeg
    perf.set_mode("high", persist=False); assert perf.ffmpeg_threads() == 0
    perf.set_mode("low", persist=False); assert perf.ffmpeg_threads() == 2


def test_ram_se_detecta():
    perf._RAM_GB = None
    assert perf.total_ram_gb() > 0.5


def test_pmap_conserva_el_orden_y_propaga_errores():
    assert fastdsp.pmap([lambda i=i: i * i for i in range(8)], workers=4) == [i * i for i in range(8)]
    assert fastdsp.pmap([lambda: 1, lambda: 2], workers=1) == [1, 2]
    def boom():
        raise ValueError("fallo")
    with pytest.raises(ValueError):
        fastdsp.pmap([lambda: 1, boom], workers=2)


def _senal(seg=8, sr=22050, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(sr * seg) / sr
    return (0.5 * np.sin(2 * np.pi * 220 * t) + 0.3 * rng.standard_normal(len(t)) * (np.sin(2 * np.pi * 2 * t) > 0.5)).astype(np.float32)


def test_filtro_de_mediana_en_paralelo_es_identico():
    from scipy.ndimage import median_filter
    S = np.abs(np.random.default_rng(1).standard_normal((513, 400))).astype(np.float32)
    for size in ((1, 31), (31, 1)):
        ref = median_filter(S, size=size, mode="reflect")
        for w in (1, 2, 3, 4):
            assert np.array_equal(fastdsp.parallel_median_filter(S, size, workers=w), ref)


@pytest.mark.parametrize("margin", [1.0, 3.0])
def test_hpss_compartido_es_identico_a_librosa(margin):
    import librosa
    y = _senal()
    fastdsp.clear_hpss_cache()
    ref = librosa.effects.hpss(y, margin=margin)
    got = fastdsp.hpss_cached(y, margin=margin)
    assert np.array_equal(ref[0], got[0]) and np.array_equal(ref[1], got[1])
    h_only = fastdsp.hpss_cached(y, margin=margin, which="harm")
    p_only = fastdsp.hpss_cached(y, margin=margin, which="perc")
    assert h_only[1] is None and p_only[0] is None
    assert np.array_equal(h_only[0], ref[0]) and np.array_equal(p_only[1], ref[1])
    other = fastdsp.hpss_cached(y, margin=3.0 if margin == 1.0 else 1.0)           # segunda llamada: reutiliza la STFT
    ref2 = librosa.effects.hpss(y, margin=3.0 if margin == 1.0 else 1.0)
    assert np.array_equal(ref2[0], other[0]) and np.array_equal(ref2[1], other[1])
    fastdsp.clear_hpss_cache()
    assert fastdsp._CACHE.get("key") is None


def test_la_cache_no_mezcla_senales_distintas():
    import librosa
    a, b = _senal(seed=1), _senal(seed=2)
    fastdsp.clear_hpss_cache()
    fastdsp.hpss_cached(a)
    got = fastdsp.hpss_cached(b)
    assert np.array_equal(got[0], librosa.effects.hpss(b)[0])
    fastdsp.clear_hpss_cache()


def test_analisis_con_varios_hilos_da_el_mismo_resultado(monkeypatch):
    from src.analysis.bpm import detect_beat_grid, SR_ANALYSIS
    from src.analysis.structure import analyze_structure
    sr = SR_ANALYSIS
    t = np.arange(sr * 40) / sr
    beat = (t * 128 / 60) % 1
    y = (0.7 * np.sin(2 * np.pi * 55 * t) * np.exp(-beat * 8) + 0.1 * np.sin(2 * np.pi * 440 * t) * (np.sin(2 * np.pi * 0.1 * t) > 0)).astype(np.float32)
    res = {}
    for n in ("1", "4"):
        monkeypatch.setenv("AUTOPREVIAS_THREADS", n)
        fastdsp.clear_hpss_cache()
        g = detect_beat_grid(y, sr)
        a = analyze_structure(y, sr, g)
        res[n] = (g.bpm, g.beat_times.tolist(), [(str(s.type), s.start_time, s.end_time, float(s.energy)) for s in a.sections])
    assert res["1"] == res["4"]
    assert fastdsp._CACHE.get("key") is None                  # la STFT compartida se libera al terminar la estructura


def test_fotogramas_de_video_en_paralelo_son_identicos(tmp_path):
    import hashlib
    from PIL import Image
    from src.engine import video_neon as vn
    img = tmp_path / "f.png"; Image.new("RGB", (320, 180), (40, 90, 200)).save(img)
    n = 30
    an = vn.AudioAnalysis(duration=n / vn.FPS, n_frames=n, bars=np.abs(np.random.default_rng(2).normal(0.5, 0.2, (n, 44))).clip(0, 1).astype(np.float32),
                          kick=np.abs(np.sin(np.arange(n) / 3)).astype(np.float32), energy=np.full(n, 0.6, np.float32), drops=[10])
    for cu in (None, {"style": "image", "bg": {"default": str(img)}, "wave_style": "circle"}):
        r = vn._Renderer(an, None, "T", "A", 128.0, "8A", "1:1", "crimson", "B", "X", 0.5, custom=cu)
        seq = [(i, hashlib.md5(f.tobytes()).hexdigest()) for i, f in vn._iter_frames(r, n, 1, workers=1)]
        par = [(i, hashlib.md5(f.tobytes()).hexdigest()) for i, f in vn._iter_frames(r, n, 1, workers=4)]
        assert seq == par and [i for i, _ in par] == list(range(n))
    # con salto (vista previa): mismos índices y orden
    a = [i for i, _ in vn._iter_frames(r, 30, 2, workers=3)]
    assert a == list(range(0, 30, 2))
