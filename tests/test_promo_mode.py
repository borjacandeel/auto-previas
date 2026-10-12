"""Tests del modo promo antifugas y de la mezcla de tags (motor de audio)."""
import numpy as np
import pytest

sf = pytest.importorskip("soundfile")

from src.engine.effects import inject_repeating_tags, inject_voice_drop, promo_tag_times

SR = 44100


def _make_tag(tmp_path, sec=1.5, freq=1000.0, amp=0.5):
    t = np.linspace(0, sec, int(SR * sec), endpoint=False)
    y = amp * np.sin(2 * np.pi * freq * t)
    p = tmp_path / "tag.wav"
    sf.write(str(p), np.stack([y, y], 1).astype(np.float32), SR, subtype="PCM_16")
    return str(p)


def _base(sec=60.0, level=0.3):
    t = np.linspace(0, sec, int(SR * sec), endpoint=False)
    y = (level * np.sin(2 * np.pi * 110 * t)).astype(np.float32)
    return np.stack([y, y])


def test_promo_tag_times_deterministas_y_sin_solapes():
    a = promo_tag_times(90.0, 1.5, interval_sec=20, jitter_sec=3, first_sec=8, seed=7)
    b = promo_tag_times(90.0, 1.5, interval_sec=20, jitter_sec=3, first_sec=8, seed=7)
    c = promo_tag_times(90.0, 1.5, interval_sec=20, jitter_sec=3, first_sec=8, seed=8)
    assert a == b and a != c
    assert a[0] == 8.0 and len(a) >= 4
    assert all(y - x >= 1.5 + 2.0 for x, y in zip(a, a[1:]))          # nunca se solapan
    assert all(t + 1.5 <= 90.0 - 2.0 for t in a)                       # ninguno queda cortado al final


def test_promo_tag_times_respeta_intervalo_minimo():
    # Intervalo absurdo (1 s) con tag de 3 s: se fuerza el hueco mínimo
    t = promo_tag_times(60.0, 3.0, interval_sec=1.0, jitter_sec=0.0, first_sec=0.0, seed=1)
    assert all(y - x >= 3.0 + 2.0 - 1e-6 for x, y in zip(t, t[1:]))
    assert promo_tag_times(5.0, 3.0, first_sec=4.0) == []              # no cabe ningún tag


def test_inject_repeating_tags_mete_energia_en_cada_tag(tmp_path):
    base = _base(60.0)
    out = inject_repeating_tags(base, SR, _make_tag(tmp_path), interval_sec=15, jitter_sec=0,
                                first_sec=5, volume_db=0.0, seed=3)
    assert out.shape == base.shape and out.dtype == np.float32
    assert np.isfinite(out).all() and np.abs(out).max() <= 0.98 + 1e-6
    times = promo_tag_times(60.0, 1.5, 15, 0, 5, 3)
    assert len(times) >= 3
    tone = np.sin(2 * np.pi * 1000.0 * np.arange(int(1.0 * SR)) / SR)
    for t in times:
        i = int((t + 0.2) * SR)
        seg_out = out[0, i:i + SR]
        corr = abs(float(np.dot(seg_out, tone)))
        corr_base = abs(float(np.dot(base[0, i:i + SR], tone)))
        assert corr > 20 * max(corr_base, 1.0)                         # el tag de 1 kHz domina esa zona
    # entre tags (lejos de cualquier ducking) la señal es la original
    far = int((times[0] + 1.5 + 3.0) * SR)
    assert np.allclose(out[0, far:far + 2000], base[0, far:far + 2000], atol=1e-6)


def test_voice_drop_unico_mantiene_su_ducking(tmp_path):
    base = np.full((2, SR * 10), 0.5, dtype=np.float32)
    tag = _make_tag(tmp_path, sec=1.0, amp=0.0)                        # tag silencioso: solo se ve el ducking
    out = inject_voice_drop(base, SR, tag, insert_time_sec=4.0, volume_db=0.0)
    assert out[0, int(2.0 * SR)] == pytest.approx(0.5, abs=1e-6)       # antes de la rampa
    assert out[0, int(4.5 * SR)] == pytest.approx(0.5 * 10 ** (-14 / 20), abs=1e-3)   # durante el tag: ≈20 %
    assert out[0, int(8.0 * SR)] == pytest.approx(0.5, abs=1e-6)       # tras la rampa de subida
