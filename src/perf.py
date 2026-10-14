"""
AutoPrevias — perf.py
Uso de recursos del equipo: cuántos hilos usar para analizar y generar vídeo según los núcleos y la RAM,
con un ajuste «Rendimiento» del usuario:

  · auto   (por defecto): usa casi todos los núcleos pero deja uno libre para que la interfaz siga fluida;
                          en equipos con poca RAM reduce los hilos.
  · low    (ahorro):      usa pocos recursos (portátiles con batería, equipos antiguos o trabajar con otros programas abiertos).
  · high   (máximo):      usa todos los núcleos para terminar lo antes posible.

La variable de entorno AUTOPREVIAS_THREADS=<n> fuerza un número de hilos (útil para pruebas y diagnóstico).
Nada de esto cambia el resultado del análisis ni del vídeo: solo cuánto tarda y cuánto consume.
"""
from __future__ import annotations

import os
import sys

MODES = ("auto", "low", "high")
_MODE: str | None = None
_RAM_GB: float | None = None


def cpu_cores() -> int:
    try:
        return max(1, int(os.cpu_count() or 2))
    except Exception:
        return 2


def total_ram_gb() -> float:
    """RAM total del equipo en GB (8.0 si no se puede saber)."""
    global _RAM_GB
    if _RAM_GB is not None:
        return _RAM_GB
    gb = 8.0
    try:
        if sys.platform == "win32":
            import ctypes

            class _MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            ms = _MS()
            ms.dwLength = ctypes.sizeof(_MS)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
                gb = ms.ullTotalPhys / 1024 ** 3
        elif sys.platform == "darwin":
            import subprocess
            out = subprocess.run(["/usr/sbin/sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=3).stdout
            gb = int(out.strip()) / 1024 ** 3
        else:
            gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3
    except Exception:
        pass
    _RAM_GB = float(gb)
    return _RAM_GB


def get_mode() -> str:
    """Modo de rendimiento elegido por el usuario (auto | low | high)."""
    global _MODE
    if _MODE is None:
        try:
            from src.config import load
            m = str(load().get("performance", "auto"))
        except Exception:
            m = "auto"
        _MODE = m if m in MODES else "auto"
    return _MODE


def set_mode(mode: str, persist: bool = True) -> None:
    global _MODE
    _MODE = mode if mode in MODES else "auto"
    if persist:
        try:
            from src.config import load, save
            cfg = load()
            cfg["performance"] = _MODE
            save(cfg)
        except Exception:
            pass


def threads(kind: str = "analysis") -> int:
    """Hilos recomendados para `kind` («analysis» o «render»)."""
    env = os.environ.get("AUTOPREVIAS_THREADS", "").strip()
    if env.isdigit() and int(env) >= 1:
        return int(env)
    cores, ram, mode = cpu_cores(), total_ram_gb(), get_mode()
    if mode == "low":
        n = max(1, min(2, cores // 2))
    elif mode == "high":
        n = min(cores, 12)
    else:
        n = max(1, min(cores - 1, 8))
        if ram < 4:
            n = 1
        elif ram < 8:
            n = min(n, 2)
        elif ram < 12:
            n = min(n, 4)
    return n


def ffmpeg_threads() -> int:
    """Hilos del codificador de vídeo (FFmpeg). 0 = lo decide FFmpeg (automático y máximo); en ahorro se limita."""
    env = os.environ.get("AUTOPREVIAS_THREADS", "").strip()
    if env.isdigit() and int(env) >= 1:
        return int(env)
    return max(1, min(2, cpu_cores() // 2)) if get_mode() == "low" else 0


def describe() -> str:
    return (f"{cpu_cores()} núcleos · {total_ram_gb():.0f} GB RAM · modo {get_mode()} → "
            f"{threads('analysis')} hilos de análisis / {threads('render')} de vídeo")
