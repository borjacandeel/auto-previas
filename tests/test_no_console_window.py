"""Windows: los programas de consola (FFmpeg…) no deben abrir una ventana negra al lanzarse desde la app."""
import subprocess
import sys

from src import compat


def test_popen_sin_ventana_en_windows(monkeypatch):
    seen = {}

    class FakePopen:
        def __init__(self, *a, **kw):
            seen.update(kw)

    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    monkeypatch.setattr(sys, "platform", "win32")
    assert compat._silence_console_windows() is True
    subprocess.Popen(["x"])
    assert seen["creationflags"] == 0x08000000
    seen.clear()
    subprocess.Popen(["x"], creationflags=0x8)          # los flags explícitos se respetan
    assert seen["creationflags"] == 0x8


def test_no_toca_otros_sistemas(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert compat._silence_console_windows() is False
