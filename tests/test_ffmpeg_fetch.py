"""v6.5.1: si al instalador le falta FFmpeg, la app lo descarga sola a su caché."""
import io
import sys
import zipfile

from src import ffmpeg_fetch as F


def _zip(name):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(name, b"x" * 2_000_000)
    return b.getvalue()


def test_descarga_y_deja_ffmpeg_en_la_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.get_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(F, "_works", lambda p: False)
    monkeypatch.setattr(sys, "platform", "win32")
    out = F.download_ffmpeg(fetch=lambda url: _zip("ffmpeg.exe"))
    assert out and (tmp_path / "ffmpeg" / "ffmpeg.exe").is_file()


def test_zip_sin_ffmpeg_no_rompe(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.get_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(F, "_works", lambda p: False)
    monkeypatch.setattr(sys, "platform", "win32")
    assert F.download_ffmpeg(fetch=lambda url: _zip("otra.txt")) is None


def test_sin_red_devuelve_none(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.get_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(F, "_works", lambda p: False)
    monkeypatch.setattr(sys, "platform", "win32")

    def _boom(url):
        raise OSError("sin conexión")
    assert F.download_ffmpeg(fetch=_boom) is None


def test_la_copia_descargada_se_encuentra(tmp_path, monkeypatch):
    import src.config as C
    monkeypatch.setattr(C, "get_cache_dir", lambda: tmp_path)
    exe = tmp_path / "ffmpeg" / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"x" * 2_000_000)
    monkeypatch.setattr(C.shutil, "which", lambda n: None)
    monkeypatch.setattr(C, "Path", C.Path)
    p = C.get_ffmpeg_path()
    assert p is not None
