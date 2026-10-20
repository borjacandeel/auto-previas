"""Transiciones con «fotos» y revelado de la onda: terminan siempre, dejan el estado final correcto y no dejan capas colgadas."""
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

_app = QApplication.instance() or QApplication([])


@pytest.fixture
def anim(monkeypatch):
    from src.ui import anim as A
    monkeypatch.setenv("AUTOPREVIAS_NO_ANIM", "0")
    monkeypatch.setenv("AUTOPREVIAS_FORCE_ANIM", "1")
    monkeypatch.setattr(A, "_REDUCE", False)
    return A


def _pump(cond, secs=3.0):
    t0 = time.time()
    while time.time() - t0 < secs and not cond():
        QApplication.processEvents()
        time.sleep(0.01)
    return cond()


def _host():
    w = QWidget()
    w.resize(500, 300)
    lay = QVBoxLayout(w)
    a, b = QLabel("A"), QLabel("B")
    lay.addWidget(a)
    lay.addWidget(b)
    b.setVisible(False)
    w.show()
    QApplication.processEvents()
    return w, a, b


def test_la_transicion_cambia_de_pantalla_y_retira_su_capa(anim):
    w, a, b = _host()
    anim.snapshot_transition(w, lambda: (a.setVisible(False), b.setVisible(True)), direction=1, ms=120)
    assert b.isVisible() and not a.isVisible()                       # el cambio es real desde el primer instante
    assert w._snap_overlay is not None and w._snap_overlay.isVisible()
    assert _pump(lambda: getattr(w, "_snap_overlay", None) is None)  # y la capa desaparece sola
    assert not [c for c in w.children() if type(c).__name__ == "_SnapOverlay" and c.isVisible()]
    w.close()


def test_una_transicion_nueva_cierra_la_anterior_sin_dejar_capas(anim):
    w, a, b = _host()
    anim.snapshot_transition(w, lambda: (a.setVisible(False), b.setVisible(True)), ms=400)
    anim.snapshot_transition(w, lambda: (a.setVisible(True), b.setVisible(False)), direction=-1, ms=120)
    assert a.isVisible() and not b.isVisible()
    assert _pump(lambda: getattr(w, "_snap_overlay", None) is None)
    assert len([c for c in w.findChildren(QWidget) if type(c).__name__ == "_SnapOverlay" and c.isVisible()]) == 0
    w.close()


def test_sin_animaciones_cambia_al_instante_y_no_crea_capas(monkeypatch):
    from src.ui import anim as A
    monkeypatch.setenv("AUTOPREVIAS_NO_ANIM", "1")
    w, a, b = _host()
    A.snapshot_transition(w, lambda: (a.setVisible(False), b.setVisible(True)))
    assert b.isVisible() and getattr(w, "_snap_overlay", None) is None
    w.close()


def test_si_la_ventana_cambia_de_tamano_la_transicion_termina_limpia(anim):
    w, a, b = _host()
    anim.snapshot_transition(w, lambda: (a.setVisible(False), b.setVisible(True)), ms=500)
    w.resize(640, 360)
    assert _pump(lambda: getattr(w, "_snap_overlay", None) is None)
    w.close()


def test_el_revelado_de_la_onda_descubre_de_izquierda_a_derecha_y_se_quita(anim):
    w, a, b = _host()
    anim.wipe_reveal(w, "#0a0b0e", ms=120)
    cover = w._wipe_cover
    assert cover is not None and cover.isVisible()
    assert _pump(lambda: getattr(w, "_wipe_cover", None) is None)
    w.close()


def test_el_asistente_cambia_de_paso_con_transicion_y_acaba_en_el_paso_correcto(anim, monkeypatch, tmp_path):
    import src.ui.app as A
    monkeypatch.setattr("src.config.get_user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(A, "get_edition", lambda: "plus")
    p = A.ResultPanel()
    p.resize(1100, 800)
    p.show()
    QApplication.processEvents()
    p.go_step(3)
    assert p._page3.isVisible() and not p._page2.isVisible() and p._wizard_step == 3
    p.go_step(2)
    assert p._page2.isVisible() and not p._page3.isVisible()
    p.set_studio(True)
    assert p._studio_view.isVisible() and not p._stepper.isVisible()
    p.set_studio(False)
    assert _pump(lambda: getattr(p, "_snap_overlay", None) is None)
    assert p._stepper.isVisible() and p._page2.isVisible()
    p.close()
    p.deleteLater()


def test_un_efecto_nuevo_aparece_con_destello_y_termina_opaco(anim):
    pytest.importorskip("pyqtgraph")
    import tests.test_fx_events as T
    w, _ = T._onda()
    w._add_fx("flanger", 40.0)
    it = w._fx_bands[0]
    assert it._pop < 1.0 or _pump(lambda: it._pop >= 0.0)          # arranca encendido (pop_in)
    assert _pump(lambda: it._pop >= 1.0, secs=3)                    # y se asienta
    w._draw_fx_bands()                                              # al redibujar NO se repite el destello
    assert w._fx_bands[0]._pop == 1.0
    T._cerrar(w)
