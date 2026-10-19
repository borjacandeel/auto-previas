"""AutoPrevias v5 — Historial de deshacer/rehacer (lógica pura, sin interfaz).

Guarda «fotos» comparables (tuplas) del estado editable: cortes + efectos de la onda.
"""
from __future__ import annotations


class History:
    def __init__(self, limit: int = 80):
        self._stack: list = []
        self._i = -1
        self.limit = limit

    def reset(self, snap) -> None:
        self._stack = [snap]
        self._i = 0

    def current(self):
        return self._stack[self._i] if self._i >= 0 else None

    def replace_current(self, snap) -> None:
        if self._i >= 0:
            self._stack[self._i] = snap

    def record(self, snap) -> bool:
        """Añade una foto si cambió respecto a la actual (borra lo que había por rehacer). True si se añadió."""
        if self._i >= 0 and snap == self._stack[self._i]:
            return False
        del self._stack[self._i + 1:]
        self._stack.append(snap)
        if len(self._stack) > self.limit:
            del self._stack[0]
        self._i = len(self._stack) - 1
        return True

    def can_undo(self) -> bool:
        return self._i > 0

    def can_redo(self) -> bool:
        return 0 <= self._i < len(self._stack) - 1

    def undo(self):
        if not self.can_undo():
            return None
        self._i -= 1
        return self._stack[self._i]

    def redo(self):
        if not self.can_redo():
            return None
        self._i += 1
        return self._stack[self._i]
