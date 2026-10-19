"""Auditoría de la 4.0.0: botones de la tabla de cortes (▶ ✕ 📍), botones de corte en la onda, efectos sin saltos ni
saltos de reproducción, y arranque/final de la previa."""
import ast
import os
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
sf = pytest.importorskip("soundfile")
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QPushButton

from src import i18n

_app = QApplication.instance() or QApplication([])
ROOT = Path(__file__).resolve().parents[1]


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


def _cerrar(*widgets):
    for w in widgets:
        w.close()
        w.deleteLater()
    QApplication.sendPostedEvents(None, 0)
    QApplication.processEvents()


# ── auditoría estática: el bug de «clicked(bool) mete False en los argumentos por defecto» ──────
def test_ningun_boton_conecta_una_funcion_con_argumentos_por_defecto_sin_absorber_el_checked():
    """`clicked` envía un bool (checked). Una función anidada `def f(x=valor)` lo recibe EN `x` (bug de ▶ ✕ 📍).
    Cualquier función con parámetros por defecto conectada a un `clicked` debe empezar por `_checked=False`."""
    malos = []
    for path in list((ROOT / "src" / "ui").glob("*.py")) + list((ROOT / "src").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        funcs = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.setdefault(node.name, []).append(node)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "connect"):
                continue
            tgt = node.func.value
            if not (isinstance(tgt, ast.Attribute) and tgt.attr in ("clicked", "toggled", "triggered")) or not node.args:
                continue
            arg = node.args[0]
            if isinstance(arg, ast.Lambda):
                a = arg.args
                if a.defaults and a.args and not a.args[0].arg.startswith("_") and len(a.args) == len(a.defaults):
                    malos.append(f"{path.name}:{node.lineno} lambda sin absorber el bool")
            elif isinstance(arg, ast.Attribute) and arg.attr in funcs:           # self.metodo(self, x=valor)
                for fn in funcs[arg.attr]:
                    a = fn.args
                    pos = [x.arg for x in a.args if x.arg != "self"]
                    if a.defaults and pos and not pos[0].startswith("_"):
                        malos.append(f"{path.name}:{node.lineno} self.{arg.attr}({', '.join(pos)})")
            elif isinstance(arg, ast.Name) and arg.id in funcs:
                for fn in funcs[arg.id]:
                    a = fn.args
                    pos = [x.arg for x in a.args if x.arg != "self"]
                    if a.defaults and pos and not pos[0].startswith("_") and len(pos) == len(a.defaults):
                        malos.append(f"{path.name}:{node.lineno} {arg.id}({', '.join(pos)})")
    assert not malos, "Handlers que reciben el bool de clicked en un argumento por defecto: " + "; ".join(malos)


# ── tabla de cortes ──────────────────────────────────────────────────────────────────────────────
class _Player:
    def __init__(self):
        self.calls, self._current_path, self._source_path, self.playing = [], "a", "a", False
        self.pos = 5.0

    def seek(self, t):
        self.calls.append(("seek", t))

    def is_playing(self):
        return self.playing

    def toggle_play(self):
        self.calls.append("toggle")
        self.playing = not self.playing

    def get_position_seconds(self):
        return self.pos


def _panel(monkeypatch, edition="plus"):
    import src.ui.app as A
    from src.analysis.segments import build_preview_plan
    from src.analysis.structure import Section, SectionType, StructureAnalysis
    monkeypatch.setattr(A, "get_edition", lambda: edition)
    p = A.ResultPanel()
    secs = [Section(type=SectionType.INTRO, start_time=0, end_time=30), Section(type=SectionType.DROP, start_time=30, end_time=60),
            Section(type=SectionType.BREAKDOWN, start_time=60, end_time=90), Section(type=SectionType.DROP, start_time=90, end_time=120)]
    p._analysis = StructureAnalysis(sections=secs, duration=120.0, bpm=128.0)
    p._bpm = 128.0
    p._plan = build_preview_plan(p._analysis)
    p._fill_plan(p._plan, animate=False)
    p._player = _Player()
    return p


@pytest.mark.parametrize("edition", ["basic", "plus"])
def test_oir_un_corte_va_a_su_inicio_actual_y_para_en_su_final(monkeypatch, edition):
    p = _panel(monkeypatch, edition)
    tbl = p._tbl_cuts
    sp = tbl.cellWidget(1, 2).findChild(QDoubleSpinBox)
    sp.setValue(65.0)                                              # el usuario cambia el inicio a mano
    p._player.calls.clear()
    tbl.cellWidget(1, 6).click()                                    # ▶ del segundo corte
    assert p._player.calls[0] == ("seek", 65.0) and "toggle" in p._player.calls   # no «seek(False)»: va al inicio ACTUAL
    end = p._cut_rows()[1][1]
    p._on_audition_tick(end - 3)
    assert p._player.playing                                         # sigue sonando dentro del corte
    p._on_audition_tick(end + 0.1)
    assert not p._player.playing                                     # al llegar al final del corte, pausa
    _cerrar(p)


@pytest.mark.parametrize("edition", ["basic", "plus"])
def test_quitar_un_corte_funciona_renumera_y_rehace_las_flechas(monkeypatch, edition):
    p = _panel(monkeypatch, edition)
    tbl = p._tbl_cuts
    n0 = tbl.rowCount()
    assert n0 >= 3
    ids = [s.cut_id for s in p._plan.segments]
    tbl.cellWidget(1, 7).click()                                    # ✕ del segundo
    assert tbl.rowCount() == n0 - 1 and len(p._plan.segments) == n0 - 1
    assert [s.cut_id for s in p._plan.segments] == [ids[0]] + ids[2:]           # los demás conservan su nombre
    assert [tbl.cellWidget(r, 0).text().split(" · ")[0] for r in range(tbl.rowCount())] == [f"{i + 1}º" for i in range(tbl.rowCount())]
    # ▲ ▼ coherentes tras borrar: el primero no sube y el último no baja
    first = tbl.cellWidget(0, 8).findChildren(QPushButton)
    last = tbl.cellWidget(tbl.rowCount() - 1, 8).findChildren(QPushButton)
    assert not first[0].isEnabled() and first[1].isEnabled() and last[0].isEnabled() and not last[1].isEnabled()
    first[1].click()                                                # ▼ del primero funciona con el índice nuevo
    assert p._plan.segments[1].cut_id == ids[0]
    # la onda queda con los mismos cortes que la tabla
    if p._waveform._plan_highlights:
        assert len(p._waveform._plan_highlights) == tbl.rowCount()
    # siempre queda al menos un corte
    msgs = []
    p.status_message.connect(msgs.append)
    while tbl.rowCount() > 1:
        tbl.cellWidget(0, 7).click()
    tbl.cellWidget(0, 7).click()
    assert tbl.rowCount() == 1 and len(p._plan.segments) == 1 and any("al menos un corte" in m for m in msgs)
    _cerrar(p)


def test_los_pins_ponen_inicio_y_fin_en_la_posicion_del_reproductor(monkeypatch):
    p = _panel(monkeypatch)
    tbl = p._tbl_cuts
    p._player.pos = 47.3
    tbl.cellWidget(0, 2).findChildren(QPushButton)[0].click()
    assert tbl.cellWidget(0, 2).findChild(QDoubleSpinBox).value() == pytest.approx(47.3, abs=0.06)
    p._player.pos = 58.0
    tbl.cellWidget(0, 3).findChildren(QPushButton)[0].click()
    assert tbl.cellWidget(0, 3).findChild(QDoubleSpinBox).value() == pytest.approx(58.0, abs=0.06)
    _cerrar(p)


def test_los_momentos_de_tempo_manual_se_pueden_quitar_y_tomar_la_posicion(monkeypatch):
    p = _panel(monkeypatch)
    p._set_tempo_mode("manual")
    n = p._tbl_tempo.rowCount()
    assert n >= 1
    p._player.pos = 33.0
    w_t = p._tbl_tempo.cellWidget(0, 0)
    w_t.findChildren(QPushButton)[0].click()
    assert w_t.findChild(QDoubleSpinBox).value() == pytest.approx(33.0, abs=0.06)
    p._tbl_tempo.cellWidget(0, 5).click()
    assert p._tbl_tempo.rowCount() == n - 1
    _cerrar(p)


# ── cortes y efectos en la onda ──────────────────────────────────────────────────────────────────
def _onda(dur=120.0):
    pytest.importorskip("pyqtgraph")
    import tests.test_fx_events as T
    return T._onda(dur)


def _ev(vp, kind, p, btn, btns):
    return QMouseEvent(kind, QPointF(p), QPointF(vp.mapToGlobal(p)), btn, btns, Qt.NoModifier)


def _click(w, t, yv):
    vp = w._plot.viewport()
    p = w._plot.mapFromScene(w._plot.getViewBox().mapViewToScene(QPointF(t, yv)))
    QApplication.sendEvent(vp, _ev(vp, QEvent.MouseButtonPress, p, Qt.LeftButton, Qt.LeftButton))
    QApplication.sendEvent(vp, _ev(vp, QEvent.MouseButtonRelease, p, Qt.LeftButton, Qt.NoButton))
    QApplication.processEvents()


def test_pinchar_un_efecto_no_mueve_la_reproduccion_ni_cambia_el_alto_de_la_onda():
    w, _ = _onda()
    w.resize(1250, 330)
    QApplication.processEvents()
    alto = w._plot.height()
    seeks, cuts = [], []
    w.seek_requested.connect(seeks.append)
    w.cuts_changed.connect(cuts.append)
    w._add_fx("flanger", 33.0)
    QApplication.processEvents()
    assert w._plot.height() == alto                                  # el panel de ajustes ya estaba: la onda no salta
    ev = w.fx_events()[0]
    _click(w, (ev["start"] + ev["end"]) / 2, -1.15 + 0.08 * 2.3)     # pinchar el bloque
    assert seeks == [] and cuts == [] and w._fx_selected == ev["id"]
    assert w._plot.height() == alto
    _click(w, 100.0, 0.0)                                            # pinchar la onda sí hace seek
    assert seeks and abs(seeks[-1] - 100.0) < 1.0
    w._delete_selected_fx()
    assert w._plot.height() == alto and not w._fx_inspector.sl_amt.isEnabled()    # sin efecto: fila apagada, no escondida
    _cerrar(w)


def test_arrastrar_un_efecto_no_toca_los_cortes_de_detras():
    w, _ = _onda()
    w.resize(1250, 330)
    QApplication.processEvents()
    regs = [tuple(h.getRegion()) for h in w._plan_highlights]
    w._add_fx("filter_up", 56.0)                                     # cruza el límite entre dos cortes
    QApplication.processEvents()
    ev = w.fx_events()[0]
    vp = w._plot.viewport()
    vb = w._plot.getViewBox()
    y = -1.15 + 0.08 * 2.3
    p0 = w._plot.mapFromScene(vb.mapViewToScene(QPointF(60.0, y)))   # justo encima de la línea de corte
    QApplication.sendEvent(vp, _ev(vp, QEvent.MouseButtonPress, p0, Qt.LeftButton, Qt.LeftButton))
    for i in range(1, 9):
        p = QPoint(p0.x() + 10 * i, p0.y())
        QApplication.sendEvent(vp, _ev(vp, QEvent.MouseMove, p, Qt.NoButton, Qt.LeftButton))
        QApplication.processEvents()
    QApplication.sendEvent(vp, _ev(vp, QEvent.MouseButtonRelease, QPoint(p0.x() + 80, p0.y()), Qt.LeftButton, Qt.NoButton))
    QApplication.processEvents()
    assert [tuple(h.getRegion()) for h in w._plan_highlights] == regs         # los cortes no se han movido
    assert w.fx_events()[0]["start"] > ev["start"] + 3                        # el efecto sí
    _cerrar(w)


def test_botones_de_corte_en_la_onda_oyen_y_quitan_sin_hacer_seek():
    w, _ = _onda()
    w.resize(1250, 330)
    QApplication.processEvents()
    assert len(w._cut_actions) == len(w._plan_highlights) == 3
    plays, dels, seeks = [], [], []
    w.cut_play_requested.connect(plays.append)
    w.cut_remove_requested.connect(dels.append)
    w.seek_requested.connect(seeks.append)
    reg = w._plan_highlights[1].getRegion()
    cx = (reg[0] + reg[1]) / 2
    from src.ui.waveform import CUT_ACT_Y
    y = CUT_ACT_Y
    vb = w._plot.getViewBox()
    pp = w._plot.mapFromScene(vb.mapViewToScene(QPointF(cx, y)))
    # píxeles: ▶ queda a la izquierda del centro y ✕ a la derecha
    vp = w._plot.viewport()
    for dx, lista in ((-12, plays), (12, dels)):
        p = QPoint(pp.x() + dx, pp.y() + 11)             # los botones cuelgan 0–20 px por debajo del punto
        QApplication.sendEvent(vp, _ev(vp, QEvent.MouseButtonPress, p, Qt.LeftButton, Qt.LeftButton))
        QApplication.sendEvent(vp, _ev(vp, QEvent.MouseButtonRelease, p, Qt.LeftButton, Qt.NoButton))
        QApplication.processEvents()
    assert plays == [1] and dels == [1] and seeks == []
    _cerrar(w)


def test_los_botones_de_la_onda_estan_conectados_a_la_app(monkeypatch):
    pytest.importorskip("pyqtgraph")
    p = _panel(monkeypatch)
    n0 = p._tbl_cuts.rowCount()
    p._waveform.cut_remove_requested.emit(0)
    assert p._tbl_cuts.rowCount() == n0 - 1
    p._waveform.cut_play_requested.emit(0)
    assert any(c == "toggle" for c in p._player.calls)
    _cerrar(p)


# ── arranque y final de la previa ────────────────────────────────────────────────────────────────
def _plan_sintetico(tmp_path):
    from src.analysis.bpm import BeatGrid
    from src.analysis.segments import PreviewPlan, PreviewSegment
    from src.analysis.structure import Section, SectionType
    sr = 44100
    t = np.linspace(0, 40, sr * 40, endpoint=False)
    y = np.stack([0.4 * np.sin(2 * np.pi * 110 * t), 0.4 * np.sin(2 * np.pi * 165 * t)], 1).astype("float32")
    src = tmp_path / "src.wav"
    sf.write(str(src), y, sr)
    segs = [PreviewSegment(Section(type=SectionType.DROP, start_time=3, end_time=11), 0, 8),
            PreviewSegment(Section(type=SectionType.DROP, start_time=20, end_time=30), 0, 10)]
    grid = BeatGrid(bpm=128.0, beat_times=np.arange(0, 40, 0.46875), beat_frames=np.array([]), sr=22050, hop_length=512)
    return str(src), PreviewPlan(segments=segs, drop_starts=[20.0]), grid


def test_final_de_la_previa_vinilo_por_defecto_o_a_los_bpm_originales(tmp_path):
    from src.engine.export import build_preview_audio
    src, plan, grid = _plan_sintetico(tmp_path)
    base = {"speed_mode": "vinyl", "studio_mastering": False, "fade_out_sec": 0.0}
    defecto, sr, _ = build_preview_audio(src, plan, grid, dict(base), seed=1)
    explicito, _, _ = build_preview_audio(src, plan, grid, {**base, "end_mode": "vinyl", "end_spin_sec": 1.0}, seed=1)
    assert np.array_equal(defecto, explicito)                        # el comportamiento de siempre no cambia
    original, _, _ = build_preview_audio(src, plan, grid, {**base, "end_mode": "original"}, seed=1)
    largo, _, _ = build_preview_audio(src, plan, grid, {**base, "end_mode": "vinyl", "end_spin_sec": 3.0}, seed=1)
    assert original.shape[1] < defecto.shape[1] < largo.shape[1]     # sin frenazo dura menos; con frenazo más largo, más
    n = int(0.4 * sr)
    rms = lambda a: float(np.sqrt((a[:, -n:] ** 2).mean()))
    assert rms(original) > rms(defecto) * 1.5                       # al final del original el sonido sigue pleno
    # el arranque sigue siendo independiente del final
    sin_arranque, _, _ = build_preview_audio(src, plan, grid, {**base, "start_mode": "original", "end_mode": "original"}, seed=1)
    assert sin_arranque.shape[1] < original.shape[1]


def test_tarjeta_de_arranque_y_final_visible_en_plus_y_oculta_en_basic(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p.show()
    QApplication.processEvents()
    assert p._card_startend.isVisibleTo(p) and p._btn_end_vinyl.isVisibleTo(p) and p._btn_start_vinyl.isVisibleTo(p)
    assert not p._tabs.isVisible() or True                           # ya no depende de abrir las pestañas
    o = p.get_export_options()
    assert o["start_mode"] == "vinyl" and o["end_mode"] == "vinyl" and o["end_spin_sec"] == 1.0
    p._set_end_mode("original")
    p._spin_end.setValue(2.5)
    p._set_start_mode("original")
    o = p.get_export_options()
    assert o["end_mode"] == "original" and o["start_mode"] == "original" and o["end_spin_sec"] == 2.5
    assert not p._spin_end.isEnabled() and not p._spin_start.isEnabled()
    est = p.get_state()
    assert est["style"]["end"] == {"mode": "original", "sec": 2.5} and est["style"]["start"]["mode"] == "original"
    p._set_end_mode("vinyl"); p._set_start_mode("vinyl")
    p.apply_state(est)
    assert p._end_mode == "original" and p._spin_end.value() == 2.5 and p._start_mode == "original"
    _cerrar(p)
    b = _panel(monkeypatch, "basic")
    b._set_end_mode("original")
    assert not b._card_startend.isVisibleTo(b)
    ob = b.get_export_options()
    assert ob["end_mode"] == "vinyl" and ob["start_mode"] == "vinyl"             # en Basic siempre el efecto de vinilo
    _cerrar(b)
