"""La firma y carátula sale una sola vez (tarjeta de la derecha) y «Editar» abre una ventana con todos los campos."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog

from tests.test_v52_features import _aislado, _cerrar, _panel  # noqa: F401  (fixture autouse + ayudas)


def test_firma_solo_una_vez_en_el_asistente(monkeypatch):
    p = _panel(monkeypatch)
    p.go_step(3, animate=False)
    p.show()
    QApplication.processEvents()
    assert p._card_sign.isVisibleTo(p)
    assert not p._branding_card.isVisibleTo(p)
    p._set_adv_open(True)
    QApplication.processEvents()
    assert not p._branding_card.isVisibleTo(p)       # abrir las opciones avanzadas ya no la enseña
    _cerrar(p)


def test_editar_abre_ventana_y_la_tarjeta_vuelve(monkeypatch):
    p = _panel(monkeypatch)
    p.go_step(3, animate=False)
    p.show()
    QApplication.processEvents()
    home = p._branding_card.parentWidget()
    visto = {}

    def _en_ventana():
        dlg = p._sig_dialog
        visto["dlg"] = isinstance(dlg, QDialog)
        visto["dentro"] = p._branding_card.parentWidget() is dlg
        visto["visible"] = p._branding_card.isVisible()
        dlg.accept()

    QTimer.singleShot(50, _en_ventana)
    p._btn_sign_edit.click()
    QApplication.processEvents()
    assert visto == {"dlg": True, "dentro": True, "visible": True}
    assert p._branding_card.parentWidget() is home
    assert not p._branding_card.isVisibleTo(p)
    assert p._sig_dialog is None
    _cerrar(p)
