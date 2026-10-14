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
    assert _rend(watermark=True, end_mode="fade").end_mode == "fade"      # pero sí elegir el fundido a negro
    assert _rend(watermark=True, end_mode="image").end_mode == "brand"    # la imagen propia es de Plus


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


# ───────────── vídeo propio (Plus): imagen de fondo, onda, disposición y final con imagen ─────────────

def _img(tmp_path, name="f.png", size=(300, 200), color=(40, 90, 200)):
    p = tmp_path / name
    Image.new("RGB", size, color).save(p)
    return str(p)


def test_normalize_custom_valida_y_completa():
    c = vn.normalize_custom({"style": "raro", "wave_style": "zigzag", "wave_pos": "abajo", "bg": {"9:16": "a.jpg", "1:1": ""}})
    assert c["style"] == "neon" and c["wave_style"] == "bars" and c["wave_pos"] == "bottom" and c["bg"] == {"9:16": "a.jpg"}
    assert vn.normalize_custom(None)["texts"] is True and vn.normalize_custom(None)["fit"] == "crop"


def test_imagen_por_formato_manda_sobre_la_general(tmp_path):
    a, b = _img(tmp_path, "a.png"), _img(tmp_path, "b.png")
    c = vn.normalize_custom({"bg": {"default": a, "9:16": b}})
    assert vn.resolve_bg(c, "9:16") == b and vn.resolve_bg(c, "1:1") == a and vn.resolve_bg(c, "16:9") == a
    assert vn.resolve_bg(vn.normalize_custom({"bg": {"default": str(tmp_path / "no.png")}}), "1:1") is None


@pytest.mark.parametrize("aspect", list(vn.ASPECTS))
@pytest.mark.parametrize("wave_style", ["bars", "line", "circle"])
@pytest.mark.parametrize("pos", ["top", "center", "bottom"])
def test_modo_imagen_dibuja_en_todos_los_formatos(tmp_path, aspect, wave_style, pos):
    cu = {"style": "image", "bg": {"default": _img(tmp_path)}, "wave_style": wave_style, "wave_pos": pos, "texts_pos": "center"}
    r = vn._Renderer(_analysis(), None, "Título", "Artista", 128.0, "8A", aspect, "crimson", "BANNER", "PREVIA EXCLUSIVA", 1.0, custom=cu)
    assert r.img_mode and r.L.W == vn.ASPECTS[aspect][0]
    im = r.frame(12, 0.4)
    assert im.size == vn.ASPECTS[aspect] and np.asarray(im).mean() > 5


def test_modo_imagen_sin_imagen_cae_a_la_plantilla_neon(tmp_path):
    r = vn._Renderer(_analysis(), None, "T", "A", 128.0, "8A", "1:1", "crimson", "", "X", 0.25,
                     custom={"style": "image", "bg": {"default": str(tmp_path / "nada.png")}})
    assert not r.img_mode


def test_onda_y_textos_se_pueden_ocultar(tmp_path):
    base = {"style": "image", "bg": {"default": _img(tmp_path)}}
    mk = lambda **kw: vn._Renderer(_analysis(), None, "Título", "Artista", 128.0, "8A", "1:1", "crimson", "", "X", 1.0,
                                   custom={**base, **kw})
    full, nowave, notext = mk(), mk(wave=False), mk(texts=False)
    f0, f1, f2 = (np.asarray(r.frame(12, 0.9), np.int16) for r in (full, nowave, notext))
    assert np.abs(f0 - f1).sum() > 0 and np.abs(f0 - f2).sum() > 0          # cada elemento cambia el fotograma
    assert nowave.wave_h == 0 and notext.custom["texts"] is False


def test_el_zoom_lento_mueve_la_imagen(tmp_path):
    grad = np.tile(np.linspace(0, 255, 600, dtype=np.uint8), (900, 1))
    p = tmp_path / "g.png"; Image.fromarray(np.stack([grad, grad[::-1], grad], -1), "RGB").save(p)
    r = vn._Renderer(_analysis(), None, "T", "A", 128.0, "8A", "9:16", "crimson", "", "X", 1.0,
                     custom={"style": "image", "bg": {"default": str(p)}, "wave": False, "texts": False})
    a, b = np.asarray(r.frame(0, 1.0), np.int16)[:1800], np.asarray(r.frame(29, 9.0), np.int16)[:1800]
    assert np.abs(a - b).mean() > 0.5


def test_final_con_imagen_propia_y_texto(tmp_path):
    img = _img(tmp_path, color=(10, 200, 60))
    n = 330
    an = vn.AudioAnalysis(duration=n / vn.FPS, n_frames=n, bars=np.full((n, 44), 0.5, dtype=np.float32),
                          kick=np.zeros(n, dtype=np.float32), energy=np.full(n, 0.5, dtype=np.float32), drops=[])
    r = vn._Renderer(an, None, "T", "A", 120.0, "1A", "9:16", "crimson", "", "X", 0.25, end_mode="image",
                     custom={"end_image": img, "end_text": "Disponible en Beatport"})
    assert r.end_mode == "image"
    g = np.asarray(r.outro, np.int16)
    assert g[..., 1].mean() > g[..., 0].mean()                                   # es la imagen verde del usuario
    last = np.asarray(r.frame(n - 2, an.duration - 0.05), np.int16)
    assert np.abs(last - g).mean() < 6                                           # el vídeo acaba en esa imagen
    assert vn._Renderer(an, None, "T", "A", 120.0, "1A", "9:16", "crimson", "", "X", 0.25, end_mode="image").end_mode == "brand"


def test_basic_ignora_la_imagen_propia(tmp_path):
    cu = {"style": "image", "bg": {"default": _img(tmp_path)}, "end_image": _img(tmp_path, "e.png")}
    r = vn._Renderer(_analysis(), None, "T", "A", 128.0, "8A", "1:1", "crimson", "", "X", 0.25, watermark=True, end_mode="image", custom=cu)
    assert not r.img_mode and r.end_mode == "brand" and r.wm_layer is not None


def test_render_completo_modo_imagen(tmp_path):
    import soundfile as sf
    from src.config import get_ffmpeg_path
    if not get_ffmpeg_path():
        pytest.skip("sin ffmpeg")                       # el CI no tiene ffmpeg en la fase de tests
    sr = 22050
    t = np.arange(sr * 3) / sr
    y = (np.sin(2 * np.pi * 440 * t) * 0.3).astype(np.float32)
    wav = tmp_path / "a.wav"; sf.write(wav, y, sr)
    out = tmp_path / "v.mp4"
    vn.render_neon_video(str(wav), None, str(out), aspect_ratio="1:1", scale=0.25,
                         custom={"style": "image", "bg": {"default": _img(tmp_path)}, "wave_style": "circle"})
    assert out.exists() and out.stat().st_size > 1000


# ───────────── formato de la imagen, textos por separado y «solo la foto» ─────────────

@pytest.mark.parametrize("w,h,esperado", [(1080, 1920, "9:16"), (1000, 1000, "1:1"), (1920, 1080, "16:9"),
                                          (1600, 1200, None), (1200, 1600, None), (2160, 3840, "9:16"), (1000, 1050, "1:1")])
def test_formato_de_la_imagen(w, h, esperado):
    assert vn.match_aspect(w, h) == esperado


def test_proporcion_legible():
    assert vn.describe_ratio(1600, 1200) == "4:3" and vn.describe_ratio(1200, 1800) == "2:3"
    assert vn.describe_ratio(1080, 1920) == "9:16" and vn.describe_ratio(1111, 1000) == "1111×1000"


def test_avisa_de_imagenes_con_otro_formato(tmp_path):
    ok = _img(tmp_path, "ok.png", (1080, 1920)); mal = _img(tmp_path, "mal.png", (1600, 1200))
    c = {"style": "image", "bg": {"default": mal}, "end_image": ok}
    assert vn.image_format_problems(c, "9:16") == [("fondo", mal, "4:3")]
    assert vn.image_format_problems({**c, "bg": {"default": ok}}, "9:16") == []
    assert vn.image_format_problems({**c, "bg": {"1:1": mal, "default": ok}}, "1:1") == [("fondo", mal, "4:3"), ("final", ok, "9:16")]
    assert vn.image_format_problems({**c, "fit": "blur"}, "9:16") == []           # entera con fondo desenfocado: nada que avisar
    assert vn.image_format_problems({"style": "neon"}, "9:16") == []


def test_textos_por_separado_y_solo_la_foto():
    c = vn.normalize_custom({"title": False, "chips": False})
    assert c["artist"] and c["kicker"] and not c["title"] and not c["chips"] and c["texts"]
    assert not vn.normalize_custom({"texts": False})["title"]                         # compatibilidad: sin textos
    o = vn.normalize_custom({"only_photo": True, "wave": True})
    assert o["wave"] is False and o["texts"] is False and not o["kicker"]


def test_cada_texto_se_dibuja_u_oculta_por_separado(tmp_path):
    base = {"style": "image", "bg": {"default": _img(tmp_path)}, "wave": False}
    mk = lambda **kw: vn._Renderer(_analysis(), None, "Título", "Artista", 128.0, "8A", "1:1", "crimson", "", "X", 1.0, custom={**base, **kw})
    todos, sin_titulo, ninguno = mk(), mk(title=False), mk(title=False, artist=False, chips=False, kicker=False)
    assert len(todos.text_items) == 4 and len(sin_titulo.text_items) == 3 and ninguno.text_items == []
    a = np.asarray(todos.frame(12, 0.9), np.int16); b = np.asarray(sin_titulo.frame(12, 0.9), np.int16)
    assert np.abs(a - b).sum() > 0


def test_solo_la_foto_no_dibuja_nada_encima(tmp_path):
    g = tmp_path / "g.png"
    Image.fromarray(np.tile(np.linspace(0, 255, 400, dtype=np.uint8), (400, 1))[..., None].repeat(3, 2), "RGB").save(g)
    r = vn._Renderer(_analysis(), None, "Título", "Artista", 128.0, "8A", "1:1", "crimson", "BANNER", "X", 1.0,
                     custom={"style": "image", "bg": {"default": str(g)}, "only_photo": True})
    assert r.banner is None and r.text_items == [] and r.wave_h == 0
    full = r.frame(15, 1.0)
    prog = np.asarray(full)[-12:]                                                      # sin barra de progreso
    ref = vn._Renderer(_analysis(), None, "Título", "Artista", 128.0, "8A", "1:1", "crimson", "BANNER", "X", 1.0,
                       custom={"style": "image", "bg": {"default": str(g)}})
    assert np.abs(prog.astype(int) - np.asarray(ref.frame(15, 1.0))[-12:].astype(int)).sum() > 0
