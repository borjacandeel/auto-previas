"""Compatibilidad de librerías para ejecutables compilados con Nuitka."""
import sys
import numpy as np

# Asegurar flag frozen para permitir a Numba y librerías nativas resolver rutas virtuales en standalone
if not hasattr(sys, "frozen"):
    setattr(sys, "frozen", True)


def apply_librosa_patches():
    """
    Parchea funciones DUFunc de librosa para usar directamente NumPy C-loops.
    En ejecutables compilados con Nuitka, el bytecode de Python se reemplaza por
    código C nativo, lo que impide a Numba inspeccionar co_code para JIT en tiempo de ejecución.
    """
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
