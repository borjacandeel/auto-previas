"""AutoPrevias package root."""
import sys

# Asegurar flag frozen para permitir a Numba y librerías nativas resolver rutas virtuales en standalone
if not hasattr(sys, "frozen"):
    setattr(sys, "frozen", True)
