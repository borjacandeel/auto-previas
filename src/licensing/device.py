"""Identificador anónimo del equipo para la regla «una licencia = un equipo».

Se envía al servidor de licencias solo como hash SHA-256 (nunca el ID real de la máquina,
nombre de usuario, nombre del equipo ni ningún dato personal).
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

_cache: str | None = None


def _read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return ""


def _mac_uuid() -> str:
    try:
        out = subprocess.run(["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                             capture_output=True, text=True, timeout=5).stdout
        m = re.search(r'"IOPlatformUUID"\s*=\s*"([0-9A-Fa-f-]{20,})"', out)
        return m.group(1) if m else ""
    except Exception:
        return ""


def _windows_guid() -> str:
    try:
        import winreg  # type: ignore[import-not-found]
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography",
                            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            return str(winreg.QueryValueEx(k, "MachineGuid")[0])
    except Exception:
        return ""


def _fallback_file() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "AutoPrevias"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / "AutoPrevias"
    else:
        base = Path.home() / ".autoprevias"
    return base / "device.id"


def _raw_machine_id() -> str:
    override = os.environ.get("AUTOPREVIAS_DEVICE_ID")      # pruebas
    if override:
        return override
    raw = ""
    if sys.platform == "darwin":
        raw = _mac_uuid()
    elif sys.platform == "win32":
        raw = _windows_guid()
    else:
        raw = _read_text("/etc/machine-id") or _read_text("/var/lib/dbus/machine-id")
    if raw:
        return raw
    # Último recurso: un identificador aleatorio guardado en disco (se pierde si se borra la carpeta)
    f = _fallback_file()
    stored = _read_text(str(f))
    if stored:
        return stored
    new = uuid.uuid4().hex
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(new, encoding="utf-8")
    except Exception:
        pass
    return new


def get_device_id() -> str:
    """Hash SHA-256 (64 hex) estable del equipo."""
    global _cache
    if _cache is None or os.environ.get("AUTOPREVIAS_DEVICE_ID"):
        _cache = hashlib.sha256(("autoprevias:v1:" + _raw_machine_id()).encode()).hexdigest()
    return _cache
