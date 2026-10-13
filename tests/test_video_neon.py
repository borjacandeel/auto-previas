"""Tests del generador de vídeo animado Radical Neón."""
import numpy as np
import pytest
from PIL import Image

from src.engine import video_neon as vn


def _analysis(n=30):
    return vn.AudioAnalysis(duration=n / vn.FPS, n_frames=n, bars=np.full((n, 44), 0.5, dtype=np.float32),
                            kick=np.linspace(0, 1, n).astype(np.float32), energy=np.full(n, 0.6, dtype=np.float32), drops=[10])


@pytest.mark.parametrize("aspect", list(vn.ASPECTS))
def test_frame_tiene_el_tamano_del_formato(aspect):

    r = vn._Renderer(_analysis(), None, "Título muy largo de prueba para comprobar el ajuste", "Radical Records",
                     128.0, "8A · Am", aspect, "cyber", "BANNER", "PREVIA EXCLUSIVA", 0.25)
    w, h = vn.ASPECTS[aspect]
    im = r.frame(12, 12 / vn.FPS)
    assert im.size[0] > 0 and im.size[0] / im.size[1] == pytest.approx(w / h, rel=0.02)
    assert np.asarray(im).std() > 5                                  # no es un fotograma vacío


def test_paleta_desconocida_usa_carmesi():
    r = vn._Renderer(_analysis(), None, "T", "A", 120.0, "1A", "1:1", "no-existe", "", "K", 0.25)
    assert r.P == vn.NEON_PALETTES["crimson"][0]


def test_render_completo_con_audio_sintetico(tmp_path):
    sf = pytest.importorskip("soundfile")
    from src.config import get_ffmpeg_path
    if not get_ffmpeg_path():
        pytest.skip("sin ffmpeg")
    sr = 44100
    t = np.linspace(0, 2.0, sr * 2, endpoint=False)
    y = (0.4 * np.sin(2 * np.pi * 60 * t) * (np.sin(2 * np.pi * 2 * t) > 0)).astype(np.float32)
    wav = tmp_path / "a.wav"
    sf.write(str(wav), np.stack([y, y], 1), sr)
    out = tmp_path / "v.mp4"
    steps = []
    vn.render_neon_video(str(wav), None, str(out), "Test", "Radical", 120.0, "8A", "1:1", "crimson", scale=0.25,
                         progress_cb=lambda p, m: steps.append(p))
    assert out.exists() and out.stat().st_size > 2000
    assert steps and steps[-1] >= 99


@pytest.mark.parametrize("aspect", list(vn.ASPECTS))
def test_cierre_tiene_firma_y_enlace(aspect):
    """El cierre lleva logo + firma + píldora blanca del enlace (zona muy clara que no existe en el fondo rojo)."""
    r = vn._Renderer(_analysis(), None, "T", "A", 120.0, "1A", aspect, "crimson", "", "PREVIA EXCLUSIVA", 0.25)
    assert (np.asarray(r.outro.convert("L")) > 245).sum() > 3000
    assert vn._Renderer(_analysis(), None, "T", "A", 120.0, "1A", aspect, "crimson", "", "EXCLUSIVE PREVIEW", 0.25).lang_en
