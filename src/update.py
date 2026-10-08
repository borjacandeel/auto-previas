"""
AutoPrevias — Comprobador de actualizaciones en segundo plano.

Consulta la API pública de GitHub Releases para comparar la versión
instalada con la última publicada. Si hay versión nueva emite
update_available(version, notes) para que la UI muestre un banner.
"""
from __future__ import annotations

import json
from packaging.version import Version
from PySide6.QtCore import QThread, Signal

_RELEASES_URL = (
    "https://api.github.com/repos/borjacandeel/auto-previas/releases/latest"
)


class UpdateChecker(QThread):
    update_available = Signal(str, str)   # nueva_version, notas
    check_done       = Signal()           # siempre al terminar

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self._current = current_version

    def run(self):
        try:
            import urllib.request
            req = urllib.request.Request(
                _RELEASES_URL,
                headers={
                    "User-Agent": "AutoPrevias-UpdateCheck/1.0",
                    "Accept": "application/vnd.github+json",
                },
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode())
            remote_ver = (data.get("tag_name") or "").lstrip("v")
            notes      = (data.get("body") or "").split("\n")[0]
            if remote_ver and Version(remote_ver) > Version(self._current):
                self.update_available.emit(remote_ver, notes)
        except Exception:
            pass
        finally:
            self.check_done.emit()
