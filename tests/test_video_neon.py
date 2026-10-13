"""Tests del generador de vídeo animado Radical Neón."""
from pathlib import Path
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


def test_vista_previa_devuelve_fotogramas_y_audio(tmp_path):
    sf = pytest.importorskip("soundfile")
    from src.config import get_ffmpeg_path
    if not get_ffmpeg_path():
        pytest.skip("sin ffmpeg")
    sr = 44100
    t = np.linspace(0, 8.0, sr * 8, endpoint=False)
    y = (0.4 * np.sin(2 * np.pi * 60 * t) * (np.sin(2 * np.pi * 2 * t) > 0)).astype(np.float32)
    wav = tmp_path / "a.wav"
    sf.write(str(wav), np.stack([y, y], 1), sr)
    for asp in ("9:16", "16:9"):
        res = vn.render_preview(str(wav), None, "Mi Tema", "Radical", 120.0, "8A", asp, "cyber", "B", seconds=3.0, out_height=240, fps=10)
        w, h = res["frames"][0].size
        assert h == 240 and (w < h) == (asp == "9:16")
        assert len(res["frames"]) >= 3 * 10 + 10          # muestra + cierre
        assert Path(res["audio"]).exists()


def _rend(aspect="9:16", **kw):
    return vn._Renderer(_analysis(40), None, "T", "A", 120.0, "1A", aspect, "crimson", "", "PREVIA EXCLUSIVA", 0.25, **kw)


@pytest.mark.parametrize("aspect", list(vn.ASPECTS))
def test_marca_de_agua_basic_abajo_a_la_derecha(aspect):
    """La edición Basic dibuja una marca pequeña y translúcida solo en la esquina inferior derecha."""
    sin, con = _rend(aspect), _rend(aspect, watermark=True)
    a = np.asarray(sin.frame(20, 0.6), np.int16)
    b = np.asarray(con.frame(20, 0.6), np.int16)
    diff = np.abs(a - b).sum(axis=2) > 0
    ys, xs = np.nonzero(diff)
    H, W = diff.shape
    assert diff.any()
    assert xs.min() > W * 0.45 and ys.min() > H * 0.90          # solo abajo a la derecha
    assert diff.sum() < W * H * 0.02                              # pequeña
    assert con.wm_layer.getchannel("A").getextrema()[1] < 140     # translúcida


def test_final_elegible_en_plus_y_cierre_obligatorio_en_basic():
    assert _rend(end_mode="fade").end_mode == "fade"
    assert _rend(end_mode="none").end_mode == "none"
    assert _rend(end_mode="raro").end_mode == "brand"
    assert _rend(watermark=True, end_mode="none").end_mode == "brand"     # Basic no puede quitar el cierre


def test_final_fundido_a_negro_y_sin_cierre():
    n = 330   # 11 s a 30 fps
    an = vn.AudioAnalysis(duration=n / vn.FPS, n_frames=n, bars=np.full((n, 44), 0.5, dtype=np.float32),
                          kick=np.zeros(n, dtype=np.float32), energy=np.full(n, 0.5, dtype=np.float32), drops=[])
    mk = lambda m: vn._Renderer(an, None, "T", "A", 120.0, "1A", "1:1", "crimson", "", "PREVIA EXCLUSIVA", 0.25, end_mode=m)
    fade, none, brand = mk("fade"), mk("none"), mk("brand")
    t_end = an.duration - 0.05
    assert np.asarray(fade.frame(n - 2, t_end)).mean() < 8                 # casi negro
    assert np.asarray(none.frame(n - 2, t_end)).mean() > 25                # sigue la animación
    assert np.abs(np.asarray(brand.frame(n - 2, t_end), np.int16) - np.asarray(brand.outro, np.int16)).mean() < 6   # cierre de marca
