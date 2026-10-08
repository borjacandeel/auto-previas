"""
AutoPrevias — Comprobador de actualizaciones en segundo plano.

Flujo:
1. Al arrancar la app, UpdateChecker (QThread) consulta el endpoint de versiones.
2. Compara con la versión instalada.
3. Si hay versión nueva, emite update_available(version, notes).
4. La UI muestra un banner no intrusivo con opción de instalar.

El endpoint es un Cloudflare Worker que actúa como proxy de la GitHub API
para no exponer el repositorio privado en el binario compilado.
Configura la variable UPDATE_ENDPOINT con la URL de tu Worker antes de compilar.
"""
from __future__ import annotations

import base64
import json
from packaging.version import Version

from PySide6.QtCore import QThread, Signal


# URL del endpoint de versiones — codificada en base64 para no exponerla en texto plano.
# Decodifica: tu URL del Cloudflare Worker, p.ej. https://autoprevias-update.TU_USER.workers.dev
# Cambia este valor cuando hayas creado el Worker.
_EP_B64 = b"aHR0cHM6Ly9hdXRvcHJldmlhcy11cGRhdGUucmFkaWNhbHJlY29yZHMud29ya2Vycy5kZXYv"


def _endpoint() -> str:
    try:
        return base64.b64decode(_EP_B64).decode()
    except Exception:
        return ""


class UpdateChecker(QThread):
    update_available = Signal(str, str)   # nueva_version, notas
    check_done       = Signal()           # siempre al terminar (con o sin update)

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self._current = current_version

    def run(self):
        try:
            import urllib.request
            url = _endpoint()
            if not url:
                return
            req = urllib.request.Request(url, headers={"User-Agent": "AutoPrevias-UpdateCheck/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode())
            remote_ver = data.get("version", "")
            notes      = data.get("notes", "")
            if remote_ver and Version(remote_ver) > Version(self._current):
                self.update_available.emit(remote_ver, notes)
        except Exception:
            pass
        finally:
            self.check_done.emit()
