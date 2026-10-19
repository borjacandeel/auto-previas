"""v5.0: cabecera con menús, inicio guiado, deshacer/rehacer, atajos y arrastrar-soltar en toda la ventana."""
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import QMimeData, QPoint, QUrl, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src import i18n
from src.ui.undo import History

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _aislado(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.get_user_data_dir", lambda: tmp_path)
    (tmp_path / "cache").mkdir(exist_ok=True)
    monkeypatch.setattr("src.config.get_cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    i18n.set_language("es")
    yield
    i18n.set_language("es")


def _cerrar(*ws):
    for w in ws:
        w.close()
        w.deleteLater()
    QApplication.processEvents()


# ── historial (lógica pura) ──────────────────────────────────────────────────────────────────────
def test_historial_deshace_rehace_y_recorta():
    h = History(limit=4)
    h.reset("a")
    assert not h.can_undo() and not h.can_redo()
    assert h.record("b") and h.record("c")
    assert not h.record("c")                         # sin cambios no añade
    assert h.undo() == "b" and h.undo() == "a" and h.undo() is None
    assert h.redo() == "b"
    assert h.record("x")                             # editar tras deshacer borra lo rehacible
    assert not h.can_redo() and h.current() == "x"
    for v in "defg":
        h.record(v)
    assert len(h._stack) == 4 and h.current() == "g"  # límite


# ── cabecera ─────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("edition,plus", [("plus", True), ("basic", False)])
def test_cabecera_con_menus_herramientas_y_ayuda(monkeypatch, edition, plus):
    import src.ui.app as A
    monkeypatch.setattr(A, "get_edition", lambda: edition)
    w = A.MainWindow()
    assert w._btn_tools.menu() is w._tools_menu and w._btn_help.menu() is w._help_menu
    assert not w._btn_recents.isVisible() and not w._btn_sign.isVisible()          # los botones sueltos ya no están
    textos = [a.text() for a in w._tools_menu.actions() if not a.isSeparator()]
    assert any("Recientes" in t for t in textos)
    assert any(t.startswith("🔒") for t in textos) == (not plus)                     # Basic: lo de Plus con candado
    assert [a.text() for a in w._help_menu.actions() if not a.isSeparator()][:2] == ["🎓 Guía de 2 minutos", "⌨ Atajos de teclado"]
    _cerrar(w)


def test_menu_de_ayuda_abre_la_guia_y_los_atajos(monkeypatch):
    import src.ui.app as A
    monkeypatch.setattr(A, "get_edition", lambda: "plus")
    w = A.MainWindow()
    llamadas = []
    monkeypatch.setattr(w, "start_tour", lambda: llamadas.append("tour"))
    monkeypatch.setattr(w, "_show_shortcuts", lambda: llamadas.append("atajos"))
    w._act_tour.trigger()
    w._act_keys.trigger()
    assert llamadas == ["tour", "atajos"]
    _cerrar(w)


def test_dialogo_de_atajos_lista_todo():
    from src.ui.shortcuts import SHORTCUTS, ShortcutsDialog
    d = ShortcutsDialog()
    assert len(SHORTCUTS) >= 10
    from PySide6.QtWidgets import QLabel
    assert len(d.findChildren(QLabel)) >= 2 * len(SHORTCUTS)
    _cerrar(d)


# ── inicio ───────────────────────────────────────────────────────────────────────────────────────
def test_inicio_ofrece_seguir_con_el_ultimo_tema(monkeypatch, tmp_path):
    import src.ui.app as A
    import src.config as C
    monkeypatch.setattr(A, "get_edition", lambda: "plus")
    f = tmp_path / "Mi Tema.wav"
    f.write_bytes(b"x")
    cfg = C.load()
    cfg["recent_files"] = [str(f)]
    C.save(cfg)
    dz = A.DropZone()
    dz.show()
    assert dz._btn_continue.isVisible() and "Mi Tema" in dz._btn_continue.text()
    got = []
    dz.file_dropped.connect(got.append)
    dz._btn_continue.click()
    assert [Path(x).resolve() for x in got] == [f.resolve()]
    f.unlink()
    dz.refresh_continue()
    assert not dz._btn_continue.isVisible()
    _cerrar(dz)


# ── deshacer / rehacer en el panel ───────────────────────────────────────────────────────────────
def _panel(monkeypatch, edition="plus"):
    from tests.test_audit_v4 import _panel as base
    p = base(monkeypatch, edition)
    p.resize(1100, 800)
    p.show()
    QApplication.processEvents()
    p._hist_poll()
    return p


def test_deshacer_y_rehacer_un_efecto(monkeypatch):
    p = _panel(monkeypatch)
    assert p._waveform.fx_events() == []
    p._waveform.set_fx_events([{"id": "a1", "type": "flanger", "start": 31.0, "end": 36.0, "amount": 0.75}], emit=True)
    p._hist_poll()
    p._hist_poll()                                       # estable en dos lecturas = un paso
    assert len(p._waveform.fx_events()) == 1
    assert p.undo() is True
    assert p._waveform.fx_events() == []
    assert p.redo() is True
    assert len(p._waveform.fx_events()) == 1
    assert p.redo() is False                             # nada más que rehacer
    _cerrar(p)


def test_deshacer_un_corte_quitado(monkeypatch):
    p = _panel(monkeypatch)
    n = len(p._cut_rows())
    assert n >= 3
    p._remove_cut(1)
    p._hist_poll(force=True)
    assert len(p._cut_rows()) == n - 1
    assert p.undo() is True
    assert len(p._cut_rows()) == n
    _cerrar(p)


def test_deshacer_vale_aunque_aun_no_se_haya_guardado_el_paso(monkeypatch):
    p = _panel(monkeypatch)
    p._waveform.set_fx_events([{"id": "z", "type": "filter_up", "start": 32.0, "end": 40.0, "amount": 0.5}], emit=True)
    assert p.undo() is True                                # sin esperar los 300 ms
    assert p._waveform.fx_events() == []
    _cerrar(p)


# ── atajos de teclado ────────────────────────────────────────────────────────────────────────────
def test_atajos_de_pasos_estudio_y_deshacer(monkeypatch):
    import src.ui.app as A
    monkeypatch.setattr(A, "get_edition", lambda: "plus")
    w = A.MainWindow()
    w._stack.setCurrentIndex(2)
    R = w._results
    R.show()
    w.show()
    llamadas = []
    monkeypatch.setattr(R, "undo", lambda: llamadas.append("undo"))
    monkeypatch.setattr(R, "redo", lambda: llamadas.append("redo"))
    QTest.keyClick(w, Qt.Key_3, Qt.ControlModifier)
    assert R._wizard_step == 3
    QTest.keyClick(w, Qt.Key_2, Qt.ControlModifier)
    assert R._wizard_step == 2
    QTest.keyClick(w, Qt.Key_E, Qt.ControlModifier)
    assert R._studio is True
    QTest.keyClick(w, Qt.Key_E, Qt.ControlModifier)
    assert R._studio is False
    QTest.keyClick(w, Qt.Key_Z, Qt.ControlModifier)
    QTest.keyClick(w, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
    QTest.keyClick(w, Qt.Key_Y, Qt.ControlModifier)
    assert llamadas == ["undo", "redo", "redo"]
    _cerrar(w)


# ── arrastrar y soltar en toda la ventana ────────────────────────────────────────────────────────
def _drop(w, paths):
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    ev = QDropEvent(QPoint(50, 50), Qt.CopyAction, md, Qt.LeftButton, Qt.NoModifier)
    w.dropEvent(ev)
    return ev


def test_soltar_audio_en_la_ventana_carga_el_tema_solo_al_soltar(monkeypatch, tmp_path):
    import src.ui.app as A
    monkeypatch.setattr(A, "get_edition", lambda: "plus")
    w = A.MainWindow()
    cargados = []
    monkeypatch.setattr(w, "_load_file", cargados.append)
    a = tmp_path / "uno.wav"
    a.write_bytes(b"x")
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(str(a))])
    from PySide6.QtGui import QDragEnterEvent
    ev = QDragEnterEvent(QPoint(5, 5), Qt.CopyAction, md, Qt.LeftButton, Qt.NoModifier)
    w.dragEnterEvent(ev)
    assert ev.isAccepted() and cargados == []             # al entrar NO carga (antes sí lo hacía)
    _drop(w, [a])
    assert [Path(x) for x in cargados] == [a]                      # Qt devuelve barras «/» también en Windows
    _cerrar(w)


def test_soltar_una_imagen_es_la_caratula_solo_en_plus(monkeypatch, tmp_path):
    import src.ui.app as A
    from PySide6.QtGui import QImage, QColor
    img = tmp_path / "portada.png"
    im = QImage(64, 64, QImage.Format_RGB32)
    im.fill(QColor("#ff1e38"))
    im.save(str(img))
    for ed in ("plus", "basic"):
        monkeypatch.setattr(A, "get_edition", lambda ed=ed: ed)
        w = A.MainWindow()
        w._stack.setCurrentIndex(2)
        puestas = []
        monkeypatch.setattr(w._results._branding_card._drop_area, "set_cover", puestas.append)
        _drop(w, [img])
        assert ([Path(x) for x in puestas] == [img]) == (ed == "plus")
        _cerrar(w)


# ── avisos con diseño ────────────────────────────────────────────────────────────────────────────
def test_los_avisos_tienen_hoja_de_estilo_valida_y_ejecutan_su_accion(monkeypatch):
    from PySide6.QtCore import qInstallMessageHandler
    from PySide6.QtWidgets import QMainWindow
    from src.ui.toast import toast
    msgs = []
    qInstallMessageHandler(lambda t, c, m: msgs.append(m))
    try:
        win = QMainWindow()
        win.resize(900, 600)
        win.show()
        hecho = []
        for kind in ("info", "success", "warn", "error"):
            t = toast(win, kind, f"Aviso {kind}", "detalle", action=("Reintentar", lambda k=kind: hecho.append(k)))
            QApplication.processEvents()
            t.findChildren(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton)[0].click()
        assert hecho == ["info", "success", "warn", "error"]
    finally:
        qInstallMessageHandler(None)
    assert not [m for m in msgs if "parse stylesheet" in m], msgs
    _cerrar(win)
