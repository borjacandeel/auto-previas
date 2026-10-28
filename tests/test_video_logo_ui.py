"""Ventana «Ajustes del vídeo»: controles de la marca de agua propia y arrastre en la vista previa."""
import os

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, QPoint, Qt
from PySide6.QtGui import QPixmap, QImage, QColor
from PySide6.QtWidgets import QApplication

from src.ui import video_custom as vc


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _logo(tmp_path):
    p = tmp_path / "logo.png"
    Image.new("RGBA", (120, 60), (255, 40, 80, 255)).save(p)
    return str(p)


def _dlg(app, tmp_path, current=None):
    d = vc.VideoCustomDialog(current, None, sample={"title": "T", "artist": "A", "aspect": "9:16"})
    d._stop_preview()
    img = QImage(280, 320, QImage.Format_RGB888)
    img.fill(QColor("#202636"))
    d._prev_lbl.setPixmap(QPixmap.fromImage(img))              # fotograma de ejemplo ya «renderizado»
    return d


def test_sin_logo_los_controles_estan_apagados(app, tmp_path):
    d = _dlg(app, tmp_path)
    assert d._collect()["logo"] == {} and not d._logo_box.isEnabled() and d._logo_clear.isHidden()
    d.deleteLater()


def test_elegir_logo_y_ajustar(app, tmp_path):
    d = _dlg(app, tmp_path)
    d._set_logo_path(_logo(tmp_path))
    assert d._logo_box.isEnabled() and not d._logo_clear.isHidden()
    d._lg_size.setValue(40); d._lg_op.setValue(70); d._lg_rot.setValue(30)
    d._lg_fh.click(); d._lg_fv.click()
    lg = d._collect()["logo"]
    assert lg["size"] == 0.40 and lg["opacity"] == 0.70 and lg["rotate"] == 30 and lg["flip_h"] and lg["flip_v"]
    d._rotate90()
    assert d._collect()["logo"]["rotate"] == 120
    d._set_logo_path("")
    assert d._collect()["logo"] == {}
    d.deleteLater()


def test_posicion_rapida_y_arrastre_en_la_vista_previa(app, tmp_path):
    d = _dlg(app, tmp_path)
    d._set_logo_path(_logo(tmp_path))
    d._lg_pos.setCurrentIndex(d._lg_pos.findData("bl"))
    d._quick_pos()
    lg = d._collect()["logo"]
    assert lg["x"] < 0.3 and lg["y"] > 0.7
    pv = d._prev_lbl
    fr = pv._frame_rect()
    assert not fr.isEmpty()
    pv.mousePressEvent(_Ev(QPointF(fr.left() + fr.width() * 0.75, fr.top() + fr.height() * 0.25)))
    pv.mouseMoveEvent(_Ev(QPointF(fr.left() + fr.width() * 0.60, fr.top() + fr.height() * 0.40)))
    pv.mouseReleaseEvent(_Ev(QPointF(0, 0)))
    lg = d._collect()["logo"]
    assert lg["x"] == pytest.approx(0.60, abs=0.01) and lg["y"] == pytest.approx(0.40, abs=0.01)
    d.deleteLater()


def test_rueda_cambia_el_tamano(app, tmp_path):
    d = _dlg(app, tmp_path, {"logo": {"path": _logo(tmp_path), "size": 0.2}})
    antes = d._collect()["logo"]["size"]

    class _W:
        def angleDelta(self): return QPoint(0, 120)
        def accept(self): pass
    d._prev_lbl.wheelEvent(_W())
    assert d._collect()["logo"]["size"] == pytest.approx(antes + 0.01)
    d.deleteLater()


def test_el_logo_se_conserva_al_reabrir(app, tmp_path):
    p = _logo(tmp_path)
    d = _dlg(app, tmp_path, {"logo": {"path": p, "x": 0.3, "y": 0.6, "size": 0.25, "rotate": -45, "flip_h": True, "opacity": 0.8}})
    lg = d._collect()["logo"]
    assert (lg["x"], lg["y"], lg["size"], lg["rotate"], lg["flip_h"], lg["opacity"]) == (0.3, 0.6, 0.25, -45, True, 0.8)
    d.deleteLater()


class _Ev:
    def __init__(self, pos):
        self._p = pos
    def position(self): return self._p
    def button(self): return Qt.LeftButton
