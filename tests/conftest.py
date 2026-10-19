"""Configuración común de los tests: sin animaciones (los cambios de visibilidad son instantáneos)."""
import os

os.environ.setdefault("AUTOPREVIAS_NO_ANIM", "1")


import pytest


@pytest.fixture(autouse=True)
def _sin_reducir_movimiento_del_sistema(monkeypatch):
    """Los runners de CI pueden tener activado «reducir movimiento»: las pruebas de animación no deben depender del SO."""
    try:
        from src.ui import anim
        monkeypatch.setattr(anim, "_REDUCE", False)
    except Exception:
        pass
