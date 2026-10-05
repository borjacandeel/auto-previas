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

# Registrar directorios de DLLs en Windows para ctypes y llvmlite
if sys.platform == "win32":
    exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    for d in [exe_dir, exe_dir / "llvmlite" / "binding", exe_dir / "PySide6"]:
        if d.is_dir() and hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(d))
            except Exception:
                pass

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

# Registrar rutas de plugins de Qt (multimedia, platforms, styles) en standalone
try:
    from PySide6.QtCore import QCoreApplication
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
