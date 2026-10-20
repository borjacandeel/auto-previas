"""Configuración común de los tests: sin animaciones (los cambios de visibilidad son instantáneos)."""
import os

os.environ.setdefault("AUTOPREVIAS_NO_ANIM", "1")


import pytest


@pytest.fixture(autouse=True)
def _sin_reducir_movimiento_del_sistema(monkeypatch):
    """Los runners de CI pueden tener activado «reducir movimiento»: las pruebas de animación no deben depender del SO."""
    try:
        from src.ui import anim
        monkeypatch.setattr(anim, "_REDUCE", False)
    except Exception:
        pass


class _FakeMediaPlayer:
    """Sustituto sin audio de QMediaPlayer para los tests de interfaz.

    En el runner de Windows (sin tarjeta de sonido) crear decenas de QMediaPlayer/QAudioOutput reales acaba en un
    «access violation» nativo que tumba toda la suite. Los tests de interfaz no necesitan sonido de verdad."""

    def __init__(self, parent=None):
        from PySide6.QtCore import QObject, Signal

        class _Sig(QObject):
            positionChanged = Signal("qlonglong")
            durationChanged = Signal("qlonglong")
            playbackStateChanged = Signal(object)
            mediaStatusChanged = Signal(object)
            errorOccurred = Signal(object, str)
        self._sig = _Sig(parent)
        self.positionChanged = self._sig.positionChanged
        self.durationChanged = self._sig.durationChanged
        self.playbackStateChanged = self._sig.playbackStateChanged
        self.mediaStatusChanged = self._sig.mediaStatusChanged
        self.errorOccurred = self._sig.errorOccurred
        self._pos, self._state, self._source = 0, None, None

    def setAudioOutput(self, _o):
        pass

    def setSource(self, url):
        self._source, self._pos = url, 0

    def source(self):
        return self._source

    def position(self):
        return self._pos

    def setPosition(self, ms):
        self._pos = int(ms)

    def duration(self):
        return 0

    def playbackState(self):
        from PySide6.QtMultimedia import QMediaPlayer
        return self._state or QMediaPlayer.PlaybackState.StoppedState

    def play(self):
        from PySide6.QtMultimedia import QMediaPlayer
        self._state = QMediaPlayer.PlaybackState.PlayingState

    def pause(self):
        from PySide6.QtMultimedia import QMediaPlayer
        self._state = QMediaPlayer.PlaybackState.PausedState

    def stop(self):
        from PySide6.QtMultimedia import QMediaPlayer
        self._state, self._pos = QMediaPlayer.PlaybackState.StoppedState, 0


class _FakeAudioOutput:
    def __init__(self, parent=None):
        self._v = 1.0

    def setVolume(self, v):
        self._v = v

    def volume(self):
        return self._v


@pytest.fixture(autouse=True)
def _reproductor_sin_audio_real(request, monkeypatch):
    """Los tests de interfaz usan un reproductor falso (marca `audio_real` para pedir el de verdad)."""
    if request.node.get_closest_marker("audio_real"):
        return
    try:
        from src.ui import player
        if getattr(player, "HAS_MEDIA", False):
            monkeypatch.setattr(player, "QMediaPlayer", type("QMediaPlayer", (_FakeMediaPlayer,), {
                "PlaybackState": player.QMediaPlayer.PlaybackState, "MediaStatus": player.QMediaPlayer.MediaStatus,
                "Error": player.QMediaPlayer.Error}))
            monkeypatch.setattr(player, "QAudioOutput", _FakeAudioOutput)
    except Exception:
        pass


def pytest_configure(config):
    config.addinivalue_line("markers", "audio_real: usa el reproductor de audio real en lugar del falso")
