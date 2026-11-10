"""v6.5.2: en Windows (app sin consola) todo proceso hijo recibe stdin/stdout/stderr válidos (evita «[WinError 6]»)."""
import subprocess
import sys

from src import compat


def test_procesos_sin_consola_reciben_nul(monkeypatch):
    seen = {}

    class FakePopen:
        def __init__(self, *args, **kwargs):
            seen.update(kwargs)

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "Popen", FakePopen)
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    assert compat._silence_console_windows()
    subprocess.Popen(["ffmpeg", "-version"], stdout=subprocess.PIPE)
    assert seen["stdin"] == subprocess.DEVNULL and seen["stdout"] == subprocess.PIPE
    assert seen["stderr"] == subprocess.DEVNULL and seen["creationflags"] == 0x08000000
