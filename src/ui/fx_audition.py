"""AutoPrevias — «▶ Oír efecto»: reproduce un efecto suelto sobre el tema original (con 2 s antes y después).

Usa su propio reproductor (no toca el del panel) y un archivo temporal que se libera antes de reescribirlo
(Windows no deja borrar archivos abiertos)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    HAS_MEDIA = True
except ImportError:                                           # pragma: no cover
    HAS_MEDIA = False


class FxAuditioner(QObject):
    state_changed = Signal(bool)                              # True = sonando

    def __init__(self, parent=None, tmp_dir: Path | None = None):
        super().__init__(parent)
        self._playing = False
        self._player = None
        self._out = None
        self._tmp_dir = tmp_dir
        if HAS_MEDIA:
            try:
                self._out = QAudioOutput(self)
                self._out.setVolume(0.9)
                self._player = QMediaPlayer(self)
                self._player.setAudioOutput(self._out)
                self._player.playbackStateChanged.connect(self._on_state)
            except Exception:
                self._player = None

    @property
    def available(self) -> bool:
        return self._player is not None

    def is_playing(self) -> bool:
        return self._playing

    def _path(self) -> Path:
        if self._tmp_dir is None:
            from src.config import get_cache_dir
            self._tmp_dir = Path(get_cache_dir())
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        return self._tmp_dir / "fx_audition.wav"

    def play_event(self, source_path: str, ev: dict) -> bool:
        """Renderiza el efecto y lo reproduce. False si no se pudo (sin reproductor o sin audio)."""
        from src.engine.fx_events import render_effect_preview
        import soundfile as sf
        self.stop()
        audio, sr = render_effect_preview(source_path, ev)
        if self._player is None or audio.shape[1] < int(0.1 * sr):
            return False
        out = self._path()
        self._player.setSource(QUrl())                         # libera el archivo antes de reescribirlo
        sf.write(str(out), audio.T, sr, subtype="PCM_16")
        self._player.setSource(QUrl.fromLocalFile(str(out)))
        self._player.play()
        return True

    def stop(self):
        if self._player is not None:
            try:
                self._player.stop()
            except Exception:
                pass
        self._set(False)

    def release(self):
        """Suelta el archivo (para poder borrarlo) y para el sonido."""
        self.stop()
        if self._player is not None:
            try:
                self._player.setSource(QUrl())
            except Exception:
                pass

    def _on_state(self, state):
        self._set(state == QMediaPlayer.PlaybackState.PlayingState)

    def _set(self, on: bool):
        if on != self._playing:
            self._playing = on
            self.state_changed.emit(on)
