"""AutoPrevias — los efectos colocados en la onda se oyen al reproducir (v6.5.3, sustituye al botón «▶ Oír»).

Cada vez que cambian los efectos se prepara en segundo plano una copia del tema ORIGINAL con los efectos aplicados
en su sitio (los tiempos no cambian) y el reproductor pasa a sonar esa copia sin perder la posición. Sin efectos,
vuelve a sonar el archivo original. Nada pesado se hace en el hilo de la interfaz.
"""
from __future__ import annotations

import threading
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal


class FxMonitor(QObject):
    ready = Signal(int, str)            # (turno, ruta del archivo con efectos o "" para volver al original)

    def __init__(self, parent=None, delay_ms: int = 450, tmp_dir: Path | None = None):
        super().__init__(parent)
        self._token = 0
        self._source = ""
        self._audio = None              # (audio estéreo float32 (2, N), sr) del tema original, decodificado una vez
        self._events: list = []
        self._tmp_dir = tmp_dir
        self._files: list[Path] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(delay_ms)
        self._timer.timeout.connect(self._start)
        self._lock = threading.Lock()

    # — API —
    def set_source(self, path: str):
        """Tema nuevo: olvida el audio y los efectos anteriores."""
        self._token += 1
        self._source = path or ""
        self._audio = None
        self._events = []
        self._timer.stop()

    def set_events(self, events: list):
        self._events = [dict(e) for e in (events or [])]
        self._timer.start()

    def flush(self):
        """Prepara ya (sin esperar)."""
        self._timer.stop()
        self._start()

    def cleanup(self, keep: str = ""):
        """Borra los archivos temporales que ya no suenan (Windows no deja borrar el que está abierto)."""
        rest = []
        for f in self._files:
            if keep and str(f) == keep:
                rest.append(f)
                continue
            try:
                f.unlink(missing_ok=True)
            except OSError:
                rest.append(f)
        self._files = rest

    # — interno —
    def _dir(self) -> Path:
        if self._tmp_dir is None:
            from src.config import get_cache_dir
            self._tmp_dir = Path(get_cache_dir())
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        return self._tmp_dir

    def _start(self):
        self._token += 1
        tok, src, evs = self._token, self._source, list(self._events)
        if not src:
            return
        if not evs:
            self.ready.emit(tok, "")
            return
        out = self._dir() / f"fx_monitor_{uuid.uuid4().hex[:8]}.wav"
        threading.Thread(target=self._work, args=(tok, src, evs, out), name="fx-monitor", daemon=True).start()

    def _load(self, src: str):
        with self._lock:
            if self._audio is not None and self._audio[2] == src:
                return self._audio[0], self._audio[1]
            import numpy as np
            try:
                import soundfile as sf
                data, sr = sf.read(src, dtype="float32", always_2d=True)
                y = data.T
            except Exception:
                from src.engine.audio_io import load_audio_file
                y, sr = load_audio_file(src, sr=None, mono=False)
                y = np.asarray(y, dtype=np.float32)
                if y.ndim == 1:
                    y = y[None, :]
            if y.shape[0] == 1:
                y = np.vstack([y, y])
            y = np.ascontiguousarray(y[:2], dtype=np.float32)
            self._audio = (y, int(sr), src)
            return y, int(sr)

    def _work(self, tok: int, src: str, evs: list, out: Path):
        try:
            import soundfile as sf
            from src.engine.fx_events import apply_events_to_source
            y, sr = self._load(src)
            if tok != self._token:
                return
            wet = apply_events_to_source(y, sr, evs)
            if tok != self._token:
                return
            sf.write(str(out), wet.T, sr, subtype="PCM_16")
            self._files.append(out)
            self.ready.emit(tok, str(out))
        except Exception:
            self.ready.emit(tok, "")            # si algo falla, se sigue oyendo el original

    def is_current(self, tok: int) -> bool:
        return tok == self._token
