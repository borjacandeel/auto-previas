"""Marca de agua propia en el vídeo (Plus) y carátula/imagen sin desplazarse de lado a lado."""
import numpy as np
import pytest
from PIL import Image

from src.engine import video_neon as vn


def _an(n=60, kick=0.55, drops=()):
    return vn.AudioAnalysis(duration=n / vn.FPS, n_frames=n, bars=np.full((n, 44), 0.5, dtype=np.float32),
                            kick=np.full(n, kick, dtype=np.float32), energy=np.full(n, 0.6, dtype=np.float32), drops=list(drops))


def _logo_png(tmp_path, size=(80, 40)):
    """Logo de prueba: mitad izquierda roja, mitad derecha azul, franja verde arriba (para ver giros y volteos)."""
    im = Image.new("RGBA", size, (0, 0, 255, 255))
    im.paste((255, 0, 0, 255), (0, 0, size[0] // 2, size[1]))
    im.paste((0, 255, 0, 255), (0, 0, size[0], 6))
    p = tmp_path / "logo.png"
    im.save(p)
    return str(p)


def test_normalize_logo_limita_y_vacia(tmp_path):
    assert vn.normalize_logo(None) == {} and vn.normalize_logo({}) == {} and vn.normalize_logo({"path": ""}) == {}
    lg = vn.normalize_logo({"path": "x.png", "size": 9, "opacity": 0, "x": -5, "y": 7, "rotate": 270, "flip_h": 1})
    assert lg["size"] == 1.5 and lg["opacity"] == 0.1 and lg["x"] == -0.25 and lg["y"] == 1.25
    assert lg["rotate"] == -90 and lg["flip_h"] is True and lg["flip_v"] is False
    assert vn.normalize_logo({"path": "x.png", "size": "mal", "x": float("nan")})["x"] == 0.86


def test_custom_incluye_el_logo_y_basic_lo_ignora(tmp_path):
    p = _logo_png(tmp_path)
    c = vn.normalize_custom({"logo": {"path": p, "size": 0.3}})
    assert c["logo"]["path"] == p and c["logo"]["size"] == 0.3
    assert vn.normalize_custom(None)["logo"] == {}
    plus = vn._Renderer(_an(), None, "T", "A", 120.0, "1A", "1:1", "crimson", "", "K", 0.25, custom=c)
    basic = vn._Renderer(_an(), None, "T", "A", 120.0, "1A", "1:1", "crimson", "", "K", 0.25, watermark=True, custom=c)
    assert plus.logo_layer is not None and basic.logo_layer is None        # Basic nunca lleva logo propio


def test_render_logo_voltea_gira_y_escala(tmp_path):
    p = _logo_png(tmp_path)
    base = vn.render_logo({"path": p, "size": 0.5}, 400)
    assert base.size == (200, 100)
    px = lambda im, x, y: im.getpixel((x, y))[:3]
    assert px(base, 10, 50) == (255, 0, 0) and px(base, 190, 50) == (0, 0, 255)          # rojo a la izquierda
    fh = vn.render_logo({"path": p, "size": 0.5, "flip_h": True}, 400)
    assert px(fh, 10, 50) == (0, 0, 255) and px(fh, 190, 50) == (255, 0, 0)
    fv = vn.render_logo({"path": p, "size": 0.5, "flip_v": True}, 400)
    assert px(fv, 100, 2) != (0, 255, 0) and px(fv, 100, 97) == (0, 255, 0)             # la franja verde pasa abajo
    rot = vn.render_logo({"path": p, "size": 0.5, "rotate": 90}, 400)
    assert rot.size == (100, 200)                                                       # 90° horario: el ancho pasa a alto
    assert px(rot, 50, 10) == (255, 0, 0)                                               # la mitad roja queda arriba
    op = vn.render_logo({"path": p, "size": 0.5, "opacity": 0.5}, 400)
    assert 120 <= op.getpixel((100, 50))[3] <= 135
    assert vn.render_logo({"path": str(tmp_path / "no.png")}, 400) is None


def _plain(custom, aspect="1:1", **kw):
    return vn._Renderer(_an(**kw), None, "T", "A", 120.0, "1A", aspect, "crimson", "", "K", 0.25, custom=custom)


def test_el_logo_aparece_donde_se_coloca(tmp_path):
    p = _logo_png(tmp_path, (60, 60))
    sin = _plain(None)
    con = _plain({"logo": {"path": p, "x": 0.25, "y": 0.75, "size": 0.30}})
    a = np.asarray(sin.frame(30, 1.0).convert("RGB"), np.int16)
    b = np.asarray(con.frame(30, 1.0).convert("RGB"), np.int16)
    diff = np.abs(a - b).sum(axis=2) > 40
    ys, xs = np.nonzero(diff)
    H, W = diff.shape
    assert diff.sum() > 200
    assert abs(xs.mean() / W - 0.25) < 0.03 and abs(ys.mean() / H - 0.75) < 0.03        # centrado donde se pidió


def test_el_logo_dura_todo_el_video_y_se_funde_al_negro(tmp_path):
    p = _logo_png(tmp_path, (60, 60))
    c = {"logo": {"path": p, "x": 0.5, "y": 0.5, "size": 0.4}}
    r = vn._Renderer(_an(n=300), None, "T", "A", 120.0, "1A", "1:1", "crimson", "", "K", 0.25, end_mode="none", custom=c)
    for t in (0.5, 5.0, r.an.duration - 0.2):
        im = np.asarray(r.frame(int(t * vn.FPS), t).convert("RGB"))
        h, w, _ = im.shape
        assert tuple(im[h // 2, w // 2 - 5]) == (255, 0, 0)                         # el logo sigue ahí (parte roja)
    f = vn._Renderer(_an(n=300), None, "T", "A", 120.0, "1A", "1:1", "crimson", "", "K", 0.25, end_mode="fade", custom=c)
    last = np.asarray(f.frame(299, f.an.duration - 0.01).convert("RGB"))
    assert last.max() < 40                                                          # fundido a negro: el logo también se apaga


def test_la_caratula_no_se_mueve_de_lado_a_lado_solo_empuja():
    """Antes la carátula temblaba (desplazamiento aleatorio) con el bombo y en los drops. Ahora solo crece/encoge."""
    r = _plain(None, kick=0.8, drops=[10])
    a = np.asarray(r.frame(36, 1.2).convert("RGB"), np.int16)
    b = np.asarray(r.frame(37, 1.2).convert("RGB"), np.int16)       # mismo audio, otro fotograma: antes cambiaba el azar del temblor
    assert np.abs(a - b).max() == 0


def test_el_drop_no_desplaza_bandas_ni_colores_de_lado(monkeypatch):
    """El glitch del drop movía franjas horizontales de la imagen y separaba los colores de la carátula."""
    def _prohibido(*a, **k):
        raise AssertionError("desplazamiento lateral de la imagen")
    monkeypatch.setattr(vn.ImageChops, "offset", _prohibido)
    r = _plain(None, kick=0.8, drops=[10])
    r.frame(12, 0.4)                                                # en pleno drop (glitch activo)


def test_el_empuje_del_bombo_si_agranda_la_caratula():
    quieto, golpe = _plain(None, kick=0.0), _plain(None, kick=1.0)
    a = np.asarray(quieto.frame(36, 1.2).convert("L"), np.int16)
    b = np.asarray(golpe.frame(36, 1.2).convert("L"), np.int16)
    assert np.abs(a - b).sum() > 0


def test_imagen_propia_no_se_desliza_de_lado_a_lado(tmp_path):
    """El zoom es siempre centrado: una franja vertical en el centro de la foto se queda en el centro en todo el vídeo."""
    im = Image.new("RGB", (1080, 1080), (20, 20, 20))
    im.paste((255, 255, 255), (520, 0, 560, 1080))
    p = tmp_path / "bg.png"
    im.save(p)
    r = vn._Renderer(_an(n=300), None, "T", "A", 120.0, "1A", "1:1", "crimson", "", "K", 0.5, end_mode="none",
                     custom={"style": "image", "only_photo": True, "bg": {"default": str(p)}})
    cols = []
    for t in (0.3, 2.5, 4.7, 7.9):
        g = np.asarray(r.frame(int(t * vn.FPS), t).convert("L"), np.float32)
        row = g[g.shape[0] // 2]
        cols.append(float((row * np.arange(len(row))).sum() / max(1.0, row.sum())) / len(row))
    assert max(cols) - min(cols) < 0.004, cols
