"""Red de seguridad de FFmpeg.

El instalador ya lleva FFmpeg dentro. Si aun así no aparece (antivirus que lo borra, instalación incompleta…),
AutoPrevias lo descarga solo, una vez, a su carpeta de caché, sin que el usuario tenga que hacer nada.
"""
from __future__ import annotations

import io
import os
import sys
import threading
import time
import zipfile
from pathlib import Path

_URLS = {
    "win32": "https://github.com/Tyrrrz/FFmpegBin/releases/download/9.0.2/ffmpeg-windows-x64.zip",
    "darwin": "https://github.com/Tyrrrz/FFmpegBin/releases/download/9.0.2/ffmpeg-osx-arm64.zip",
}
_LOCK = threading.Lock()


def exe_name() -> str:
    return "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"


def cache_target() -> Path:
    from src.config import get_cache_dir
    return Path(get_cache_dir()) / "ffmpeg" / exe_name()


def _log(msg: str) -> None:
    try:
        import tempfile
        with open(Path(tempfile.gettempdir()) / "autoprevias_ffmpeg.log", "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _fetch(url: str, timeout: float = 60.0) -> bytes:
    import urllib.request
    from src.licensing.license import _make_ssl_context
    req = urllib.request.Request(url, headers={"User-Agent": "AutoPrevias-FFmpeg/1.0"})
    last = None
    for bundled in (False, True):                         # plan B: certificados raíz que lleva la app
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_make_ssl_context(bundled=bundled)) as r:
                return r.read()
        except Exception as e:                            # noqa: BLE001
            last = e
    raise last  # type: ignore[misc]


def _works(path: Path) -> bool:
    try:
        import subprocess
        r = subprocess.run([str(path), "-version"], capture_output=True, timeout=20)
        return r.returncode == 0 and b"ffmpeg" in (r.stdout or b"").lower()
    except Exception:
        return False


def download_ffmpeg(fetch=None) -> str | None:
    """Descarga FFmpeg a la caché de la app. Devuelve la ruta o None. `fetch` permite probarlo sin red."""
    url = _URLS.get(sys.platform)
    if not url:
        return None
    with _LOCK:
        dst = cache_target()
        if dst.is_file() and _works(dst):
            return str(dst)
        try:
            _log(f"Descargando FFmpeg: {url}")
            data = (fetch or _fetch)(url)
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                member = next((n for n in z.namelist() if Path(n).name.lower() == exe_name()), None)
                if not member:
                    _log("El zip no trae ffmpeg")
                    return None
                dst.parent.mkdir(parents=True, exist_ok=True)
                tmp = dst.with_suffix(dst.suffix + ".part")
                tmp.write_bytes(z.read(member))
            if sys.platform != "win32":
                os.chmod(tmp, 0o755)
            os.replace(tmp, dst)
            _log(f"FFmpeg listo en {dst}")
            return str(dst)
        except Exception as e:                            # noqa: BLE001
            _log(f"No se pudo descargar FFmpeg: {e}")
            return None


def ensure_ffmpeg() -> str | None:
    """FFmpeg de la app; si falta, lo descarga y lo deja listo."""
    from src.config import get_ffmpeg_path
    return get_ffmpeg_path() or download_ffmpeg()


def prefetch_in_background() -> None:
    """Al abrir la app: si falta FFmpeg, se descarga en segundo plano para que esté listo cuando haga falta."""
    def _run():
        try:
            from src.config import get_ffmpeg_path
            if not get_ffmpeg_path():
                download_ffmpeg()
        except Exception:
            pass
    threading.Thread(target=_run, name="ffmpeg-prefetch", daemon=True).start()
