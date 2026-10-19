"""Configuración común de los tests: sin animaciones (los cambios de visibilidad son instantáneos)."""
import os

os.environ.setdefault("AUTOPREVIAS_NO_ANIM", "1")
