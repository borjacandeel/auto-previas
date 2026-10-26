"""
AutoPrevias — Actualizador en segundo plano (hilos Qt).

UpdateChecker  : consulta la última Release y emite update_available(ReleaseInfo).
UpdateDownloader: descarga el instalador correcto, con progreso, y verifica su SHA-256.
La lógica pura vive en src/updater_core.py.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.updater_core import (
    SUMS_NAME, ReleaseInfo, fetch_latest_release, get_skipped_version,
    is_newer, log_update_error, open_url, parse_sha256sums, sha256_file,
)


class UpdateChecker(QThread):
    update_available = Signal(object)   # ReleaseInfo
    check_done       = Signal()         # siempre al terminar

    def __init__(self, current_version: str, parent=None, ignore_skipped: bool = False):
        super().__init__(parent)
        self._current = current_version
        self._ignore_skipped = ignore_skipped

    def run(self):
        try:
            info = fetch_latest_release()
            if info and is_newer(info.version, self._current):
                if self._ignore_skipped or info.version != get_skipped_version():
                    self.update_available.emit(info)
        except Exception as e:
            log_update_error(f"Comprobación de versión fallida: {type(e).__name__}: {e}")
        finally:
            self.check_done.emit()


def _download_dir() -> Path:
    d = Path.home() / "Downloads"
    if d.is_dir() and os.access(d, os.W_OK):
        return d
    return Path(tempfile.gettempdir())


class UpdateDownloader(QThread):
    progress    = Signal(int, int)   # bytes descargados, total (0 si se desconoce)
    status      = Signal(str)
    finished_ok = Signal(str)        # ruta del instalador verificado
    failed      = Signal(str)

    def __init__(self, asset_name: str, info: ReleaseInfo, parent=None):
        super().__init__(parent)
        self._name = asset_name
        self._info = info
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _expected_hash(self) -> str | None:
        url = self._info.assets.get(SUMS_NAME)
        if not url:
            return None
        try:
            with open_url(url, timeout=15) as resp:
                return parse_sha256sums(resp.read().decode("utf-8", "replace")).get(self._name)
        except Exception:
            return None

    def run(self):
        part = None
        try:
            url = self._info.assets.get(self._name)
            if not url:
                self.failed.emit("El instalador no está disponible en esta versión.")
                return
            dest = _download_dir() / self._name
            part = dest.with_suffix(dest.suffix + ".part")

            self.status.emit("Descargando…")
            with open_url(url, timeout=30) as resp, open(part, "wb") as out:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                while True:
                    if self._cancel:
                        out.close()
                        part.unlink(missing_ok=True)
                        self.failed.emit("Descarga cancelada.")
                        return
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    self.progress.emit(done, total)

            self.status.emit("Verificando integridad…")
            expected = self._expected_hash()
            if expected is None:
                part.unlink(missing_ok=True)
                self.failed.emit(
                    "No se pudo verificar la integridad del archivo descargado. "
                    "Por seguridad no se instalará."
                )
                return
            if sha256_file(part) != expected:
                part.unlink(missing_ok=True)
                self.failed.emit("El archivo descargado está corrupto (la suma SHA-256 no coincide).")
                return

            dest.unlink(missing_ok=True)
            part.replace(dest)
            self.finished_ok.emit(str(dest))
        except Exception as exc:
            try:
                if part is not None:
                    part.unlink(missing_ok=True)
            except Exception:
                pass
            log_update_error(f"{type(exc).__name__}: {exc}")
            self.failed.emit("No se pudo descargar la actualización. Comprueba tu conexión a internet e inténtalo de nuevo.")
