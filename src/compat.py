"""Compatibilidad de librerías para ejecutables compilados con Nuitka."""
import sys
import numpy as np

# Módulos estándar requeridos dinámicamente por Numba, Librosa, Scikit-learn y Pooch en standalone
import uuid
import dis
import inspect
import opcode
import socket
import secrets
import mimetypes
import difflib
import cmath
import ast
import asyncio
import token
import tokenize
import pydoc
import runpy
import timeit
import calendar
import pprint

# Asegurar flag frozen para permitir a Numba y librerías nativas resolver rutas virtuales en standalone
if not hasattr(sys, "frozen"):
    setattr(sys, "frozen", True)

import os
from pathlib import Path

# Registrar directorios de DLLs y configurar renderizado seguro en Windows (especialmente ARM64 emulado)
if sys.platform == "win32":
    import platform

    def _check_is_arm() -> bool:
        # 1. Variables de entorno comunes
        for k in ("PROCESSOR_ARCHITECTURE", "PROCESSOR_ARCHITEW6432", "PROCESSOR_IDENTIFIER"):
            val = os.environ.get(k, "").upper()
            if "ARM" in val or "SNAPDRAGON" in val or "QUALCOMM" in val:
                return True
        # 2. ctypes: GetNativeSystemInfo
        try:
            import ctypes
            from ctypes import wintypes

            class _SYSTEM_INFO(ctypes.Structure):
                _fields_ = [
                    ("wProcessorArchitecture", wintypes.WORD),
                    ("wReserved", wintypes.WORD),
                    ("dwPageSize", wintypes.DWORD),
                    ("lpMinimumApplicationAddress", wintypes.LPVOID),
                    ("lpMaximumApplicationAddress", wintypes.LPVOID),
                    ("dwActiveProcessorMask", ctypes.c_size_t),
                    ("dwNumberOfProcessors", wintypes.DWORD),
                    ("dwProcessorType", wintypes.DWORD),
                    ("dwAllocationGranularity", wintypes.DWORD),
                    ("wProcessorLevel", wintypes.WORD),
                    ("wProcessorRevision", wintypes.WORD),
                ]

            sys_info = _SYSTEM_INFO()
            ctypes.windll.kernel32.GetNativeSystemInfo(ctypes.byref(sys_info))
            # PROCESSOR_ARCHITECTURE_ARM64 = 12, PROCESSOR_ARCHITECTURE_ARM = 5
            if sys_info.wProcessorArchitecture in (12, 5):
                return True
        except Exception:
            pass
        # 3. ctypes: IsWow64Process2
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            if hasattr(kernel32, "IsWow64Process2"):
                proc_mach = wintypes.USHORT()
                native_mach = wintypes.USHORT()
                if kernel32.IsWow64Process2(kernel32.GetCurrentProcess(), ctypes.byref(proc_mach), ctypes.byref(native_mach)):
                    # IMAGE_FILE_MACHINE_ARM64 = 0xAA64 (43620)
                    if native_mach.value in (0xAA64, 0x01C4, 0x01C0):
                        return True
        except Exception:
            pass
        # 4. platform string inspection
        mach = platform.machine().lower()
        proc = platform.processor().lower()
        return "arm" in mach or "arm" in proc

    # En Windows (tanto x64 como ARM64 bajo emulación o virtualización en Parallels / VMware / Snapdragon),
    # los controladores OpenGL / Direct3D emulados pueden bloquear la inicialización de la ventana de Qt.
    # Forzar modo de renderizado por software seguro garantiza arranque instantáneo de la GUI al 100%.
    os.environ.setdefault("QT_OPENGL", "software")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QMLSCENE_DEVICE", "softwarecontext")
    os.environ.setdefault("QSG_RHI_BACKEND", "software")

    exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    for d in [
        exe_dir,
        exe_dir / "llvmlite" / "binding",
        exe_dir / "PySide6",
        exe_dir / "PySide6" / "plugins",
        exe_dir / "PySide6" / "qt-plugins",
        exe_dir / "qt-plugins",
    ]:
        if d.is_dir():
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(str(d))
                except Exception:
                    pass
            # Asegurar en PATH del proceso
            cur_path = os.environ.get("PATH", "")
            if str(d) not in cur_path:
                os.environ["PATH"] = f"{d};{cur_path}"

# Parche de carga directa para llvmlite en ejecutables standalone (evita fallo de importlib.resources)
try:
    import llvmlite.binding.ffi as _ffi
    import ctypes

    _orig_load_lib = _ffi._lib_wrapper._load_lib

    def _robust_load_lib(self):
        test_sym = "LLVMPY_GetVersionInfo"
        exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent

        candidates = [
            exe_dir / "llvmlite.dll",
            exe_dir / "llvmlite" / "binding" / "llvmlite.dll",
            exe_dir / "libllvmlite.dylib",
            exe_dir / "llvmlite" / "binding" / "libllvmlite.dylib",
            exe_dir / "libllvmlite.so",
            exe_dir / "llvmlite" / "binding" / "libllvmlite.so",
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                try:
                    self._lib_handle = ctypes.CDLL(str(c.resolve()))
                    getattr(self._lib_handle, test_sym)()
                    return
                except Exception:
                    pass

        # Fallback al cargador original si no se encontró en candidatos directos
        _orig_load_lib(self)

    _ffi._lib_wrapper._load_lib = _robust_load_lib
except Exception:
    pass

# Registrar rutas de plugins de Qt (multimedia, platforms, styles) en standalone y activar OpenGL software
try:
    from PySide6.QtCore import Qt, QCoreApplication
    if sys.platform == "win32":
        try:
            QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
        except Exception:
            pass
    _base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    for p_dir in [
        _base_dir / "PySide6" / "qt-plugins",
        _base_dir / "PySide6" / "plugins",
        _base_dir / "qt-plugins",
        _base_dir / "plugins",
    ]:
        if p_dir.is_dir():
            _p_str = str(p_dir)
            if _p_str not in QCoreApplication.libraryPaths():
                QCoreApplication.addLibraryPath(_p_str)
except Exception:
    pass



def apply_librosa_patches():
    """
    Parchea funciones DUFunc de librosa para usar directamente NumPy C-loops.
    En ejecutables compilados con Nuitka, el bytecode de Python se reemplaza por
    código C nativo, lo que impide a Numba inspeccionar co_code para JIT en tiempo de ejecución.
    """
    try:
        import librosa
        import librosa.version
        if not hasattr(librosa, "__version__"):
            setattr(librosa, "__version__", librosa.version.version)
    except Exception:
        pass

    try:
        import librosa.util.utils as _lu
        import librosa.util as _lutil

        def _clean_abs2(x, dtype=None):
            if np.iscomplexobj(x):
                y = x.real**2 + x.imag**2
                return y.astype(dtype) if dtype else y
            return np.square(x, dtype=dtype)

        def _clean_phasor(angles, mag=1.0):
            return mag * (np.cos(angles) + 1j * np.sin(angles))

        _lu.abs2 = _clean_abs2
        _lutil.abs2 = _clean_abs2
        _lu.phasor = _clean_phasor
        _lutil.phasor = _clean_phasor
    except Exception:
        pass
