"""
Compatibilidad de librerías para ejecutables compilados con Nuitka.
Garantiza rutas de búsqueda de DLLs, plugins de Qt y parches de introspección para Librosa.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
import numpy as np

# Módulos estándar requeridos para inspección de bytecode en Numba/Librosa
import uuid
import dis
import inspect
import opcode

# Asegurar flag frozen para permitir a librerías nativas resolver rutas virtuales en standalone
if not hasattr(sys, "frozen"):
    setattr(sys, "frozen", True)

# Configuración de rutas nativas en Windows
if sys.platform == "win32":
    # Forzar modo de renderizado por software seguro
    os.environ.setdefault("QT_OPENGL", "software")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QMLSCENE_DEVICE", "softwarecontext")
    os.environ.setdefault("QSG_RHI_BACKEND", "software")
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

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
            cur_path = os.environ.get("PATH", "")
            if str(d) not in cur_path:
                os.environ["PATH"] = f"{d};{cur_path}"

# Registrar rutas de plugins de Qt (multimedia, platforms, styles) en standalone
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


def _apply_llvmlite_patch():
    """Parche de carga directa para llvmlite en ejecutables standalone."""
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
            _orig_load_lib(self)

        _ffi._lib_wrapper._load_lib = _robust_load_lib
    except Exception:
        pass


def apply_librosa_patches():
    """
    Parchea librosa para ejecutables standalone donde lazy_loader o numba
    no pueden resolver referencias de módulos dinámicos.
    """
    _apply_llvmlite_patch()

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
