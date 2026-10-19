"""Firmar tema entero: la carátula se incrusta SIEMPRE (venga la imagen como venga) y se comprueba en el archivo guardado."""
import os
import struct
import subprocess
import time
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
sf = pytest.importorskip("soundfile")
PIL = pytest.importorskip("PIL")
from PIL import Image
from PySide6.QtWidgets import QApplication

from src import i18n

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _aislado(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.get_user_data_dir", lambda: tmp_path)
    (tmp_path / "cache").mkdir(exist_ok=True)
    monkeypatch.setattr("src.config.get_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    i18n.set_language("es")
    yield
    i18n.set_language("es")


def _wav(path, sec=1.5, sr=44100, sub="PCM_24"):
    t = np.linspace(0, sec, int(sr * sec), endpoint=False)
    sf.write(str(path), np.stack([0.4 * np.sin(2 * np.pi * 440 * t), 0.3 * np.sin(2 * np.pi * 660 * t)], 1), sr, subtype=sub)
    return str(path)


def _imagen(tmp_path, kind):
    p = tmp_path / f"cover_{kind}"
    if kind == "jpg":
        Image.new("RGB", (1200, 900), (200, 20, 40)).save(str(p) + ".jpg")
        return str(p) + ".jpg"
    if kind == "png_alpha":
        Image.new("RGBA", (800, 600), (20, 200, 40, 128)).save(str(p) + ".png")
        return str(p) + ".png"
    if kind == "webp":
        Image.new("RGB", (900, 900), (20, 40, 200)).save(str(p) + ".webp")
        return str(p) + ".webp"
    if kind == "cmyk":
        Image.new("CMYK", (700, 700), (10, 200, 10, 0)).save(str(p) + ".jpg")
        return str(p) + ".jpg"
    Image.new("P", (500, 700)).save(str(p) + ".gif")
    return str(p) + ".gif"


@pytest.mark.parametrize("kind", ["jpg", "png_alpha", "webp", "cmyk", "gif"])
@pytest.mark.parametrize("fmt", ["flac", "wav"])
def test_la_caratula_se_incrusta_con_cualquier_imagen_y_se_comprueba(tmp_path, kind, fmt):
    from src.engine.sign import sign_track
    src = _wav(tmp_path / "tema.wav")
    r = sign_track(src, str(tmp_path / "out"), fmt, _imagen(tmp_path, kind), {"artist": "DJ Test", "label": "Radical"})
    assert r["cover"] and r["cover_ok"] and not r["warnings"], r
    from src.config import get_ffmpeg_path
    txt = subprocess.run([get_ffmpeg_path(), "-hide_banner", "-i", r["path"]], capture_output=True, text=True).stderr
    assert "Video: mjpeg" in txt and "1400x1400" in txt


def test_sin_caratula_se_dice_y_no_se_inventa_una(tmp_path):
    from src.engine.sign import sign_track
    r = sign_track(_wav(tmp_path / "t.wav"), str(tmp_path / "o"), "flac", None, {})
    assert r["cover"] is False and r["cover_ok"] is False
    r2 = sign_track(_wav(tmp_path / "t2.wav"), str(tmp_path / "o"), "flac", str(tmp_path / "no_existe.png"), {})
    assert r2["cover"] is False and "caratula_no_encontrada" in r2["warnings"]        # no se calla que la imagen no estaba


def test_wav_lleva_etiqueta_id3_con_las_dos_grafias_y_lista_info_y_el_audio_no_cambia(tmp_path):
    from src.engine.sign import sign_track
    src = _wav(tmp_path / "a.wav")
    antes = sf.read(src, dtype="int32")[0]
    r = sign_track(src, str(tmp_path / "o"), "wav", _imagen(tmp_path, "jpg"), {"title": "Mi Tema", "artist": "DJ Test", "genre": "Techno"})
    data = Path(r["path"]).read_bytes()
    assert data[:4] == b"RIFF" and struct.unpack("<I", data[4:8])[0] == len(data) - 8     # cabecera coherente
    assert b"id3 " in data and b"ID3 " in data and b"LIST" in data and b"INAM" in data and b"IART" in data
    assert np.array_equal(sf.read(r["path"], dtype="int32")[0], antes)                      # mismas muestras
    from src.config import get_ffmpeg_path
    tags = subprocess.run([get_ffmpeg_path(), "-v", "error", "-i", r["path"], "-f", "ffmetadata", "-"], capture_output=True, text=True).stdout
    assert "DJ Test" in tags and "Mi Tema" in tags


def _esperar(d, secs=60):
    t0 = time.time()
    while time.time() - t0 < secs and d._worker is not None and d._worker.isRunning():
        QApplication.processEvents()
        time.sleep(0.02)
    for _ in range(20):
        QApplication.processEvents()


def test_la_ventana_conserva_la_caratula_aunque_qt_no_pueda_mostrar_la_miniatura(tmp_path, monkeypatch):
    """Antes, si Qt no leía la imagen (p. ej. WebP sin plugin) la carátula se descartaba EN SILENCIO y el tema salía sin ella."""
    import src.ui.sign_track as S
    cover = _imagen(tmp_path, "webp")

    from PySide6.QtGui import QPixmap as _QPixmap

    class _Nula(_QPixmap):                                             # un QPixmap que siempre «no se pudo leer»
        def isNull(self):
            return True

    monkeypatch.setattr(S, "QPixmap", _Nula)
    d = S.SignTrackDialog({}, None, [_wav(tmp_path / "t.wav")])
    d._out_dir = str(tmp_path / "out")
    d._set_cover(cover)
    assert d.cover() == cover and d._btn_cover_off.isEnabled()
    d._start()
    _esperar(d)
    assert "Carátula incrustada y comprobada" in d._lbl_status.text()
    assert d._results and d._results[0]["cover_ok"]
    d.deleteLater()


def test_la_ventana_avisa_cuando_se_firma_sin_caratula(tmp_path):
    import src.ui.sign_track as S
    d = S.SignTrackDialog({}, None, [_wav(tmp_path / "t.wav")])
    d._out_dir = str(tmp_path / "out")
    assert "Sin carátula" in d._lbl_cover_hint.text()                 # aviso visible ANTES de firmar
    d._start()
    _esperar(d)
    assert "SIN carátula" in d._lbl_status.text()
    d.deleteLater()


def test_la_ventana_usa_la_caratula_y_las_etiquetas_de_firma_y_caratula_de_la_ventana_principal(tmp_path):
    import src.ui.sign_track as S
    cover = _imagen(tmp_path, "jpg")
    d = S.SignTrackDialog({"tag_artist": "Viejo"}, None, None,
                          defaults={"cover": cover, "meta": {"artist": "DJ Actual", "label": "Radical Records", "genre": "Techno"}})
    assert d.cover() == cover
    assert d._ed["artist"].text() == "DJ Actual" and d._ed["label"].text() == "Radical Records" and d._ed["genre"].text() == "Techno"
    d.deleteLater()
    # sin carátula en la principal: la última usada aquí; y si tampoco, la guardada como predeterminada
    d2 = S.SignTrackDialog({"sign_cover_path": cover}, None, None)
    assert d2.cover() == cover
    d2.deleteLater()
    d3 = S.SignTrackDialog({"custom_cover_path": cover}, None, None)
    assert d3.cover() == cover
    d3.deleteLater()


def test_la_caratula_elegida_se_recuerda_para_la_proxima_vez(tmp_path):
    import src.ui.sign_track as S
    from src.config import load
    cover = _imagen(tmp_path, "png_alpha")
    d = S.SignTrackDialog(load(), None, [_wav(tmp_path / "t.wav")])
    d._out_dir = str(tmp_path / "out")
    d._set_cover(cover)
    d._start()
    _esperar(d)
    assert load().get("sign_cover_path") == cover
    d.deleteLater()
