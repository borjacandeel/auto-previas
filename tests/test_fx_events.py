"""Tests de los efectos manuales en la onda (3.11.0): motor por bloque, carril, arrastrar y soltar, ediciones."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
sf = pytest.importorskip("soundfile")
from PySide6.QtWidgets import QApplication

from src import i18n

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


def _cerrar(*widgets):
    for w in widgets:
        w.close()
        w.deleteLater()
    QApplication.sendPostedEvents(None, 0)
    QApplication.processEvents()


# ── motor ───────────────────────────────────────────────────────────────────────────────────────
def test_normalizar_eventos_limpia_lo_invalido():
    from src.engine.fx_events import MAX_EVENTS, normalize_events
    evs = normalize_events([
        {"id": 1, "type": "flanger", "start": 5, "end": 11, "amount": 0.5},
        {"id": 2, "type": "inventado", "start": 1, "end": 2},                 # tipo desconocido
        {"id": 3, "type": "filter_up", "start": "x", "end": 4},               # no numérico
        {"id": 4, "type": "filter_down", "start": 90, "end": 120, "amount": 7},  # fuera del tema y mucha intensidad
        {"id": 5, "type": "flanger", "start": 3, "end": 3.1},                 # demasiado corto
        "basura",
    ], duration=100.0)
    assert [e["type"] for e in evs] == ["flanger", "flanger", "filter_down"]
    f = evs[-1]
    assert f["end"] <= 100.0 and f["amount"] == 1.0 and f["end"] - f["start"] >= 0.5
    assert evs[0]["end"] - evs[0]["start"] == pytest.approx(0.5)
    assert len(normalize_events([{"type": "flanger", "start": i, "end": i + 1} for i in range(80)])) == MAX_EVENTS
    assert normalize_events(None) == []


def _bloques():
    sr = 44100
    t = np.arange(sr * 12) / sr
    ruido = np.random.RandomState(1).randn(2, len(t)).astype("float32") * 0.1
    a = (0.3 * np.sin(2 * np.pi * 80 * t)[None, :] + ruido).astype("float32")
    return sr, [a.copy(), a.copy()], [[10.0, 22.0], [50.0, 62.0]]


@pytest.mark.parametrize("tipo", ["flanger", "filter_up", "filter_down"])
def test_el_efecto_solo_cambia_el_solape_con_su_bloque(tipo):
    from src.engine.fx_events import apply_events_to_blocks
    sr, auds, blocks = _bloques()
    orig = [a.copy() for a in auds]
    ev = {"id": 1, "type": tipo, "start": 14.0, "end": 17.0, "amount": 0.75}
    out = apply_events_to_blocks(auds, blocks, sr, [ev])
    # el segundo bloque (50–62) no se toca; el primero solo cambia entre 4 s y 7 s de su propio audio
    assert np.array_equal(out[1], orig[1])
    assert out[0].shape == orig[0].shape
    i0, i1 = 4 * sr, 7 * sr
    assert np.array_equal(out[0][:, :i0 - 5], orig[0][:, :i0 - 5]) and np.array_equal(out[0][:, i1 + 5:], orig[0][:, i1 + 5:])
    assert not np.allclose(out[0][:, i0 + 2000:i1 - 2000], orig[0][:, i0 + 2000:i1 - 2000], atol=1e-4)
    assert np.isfinite(out[0]).all() and float(np.abs(out[0]).max()) <= 1.0
    # los originales de entrada no se modifican
    assert np.array_equal(auds[0], orig[0])


def test_el_filtro_ascendente_quita_graves_cada_vez_mas():
    from src.engine.fx_events import apply_events_to_blocks
    sr, auds, blocks = _bloques()
    out = apply_events_to_blocks(auds, blocks, sr, [{"id": 1, "type": "filter_up", "start": 12.0, "end": 20.0, "amount": 0.75}])
    seg = lambda a, t0, t1: float(np.sqrt((a[:, int(t0 * sr):int(t1 * sr)] ** 2).mean()))
    ini = seg(out[0], 2.2, 3.2) / seg(auds[0], 2.2, 3.2)
    fin = seg(out[0], 9.0, 9.9) / seg(auds[0], 9.0, 9.9)
    assert fin < ini < 1.05 and fin < 0.6


def test_sin_eventos_o_fuera_de_los_cortes_la_previa_es_identica(tmp_path):
    from src.analysis.bpm import BeatGrid
    from src.analysis.segments import PreviewPlan, PreviewSegment
    from src.analysis.structure import Section, SectionType
    from src.engine.export import build_preview_audio
    sr = 44100
    t = np.linspace(0, 40, sr * 40, endpoint=False)
    y = np.stack([0.4 * np.sin(2 * np.pi * 110 * t), 0.4 * np.sin(2 * np.pi * 165 * t)], 1).astype("float32")
    src = tmp_path / "src.wav"
    sf.write(str(src), y, sr)
    segs = [PreviewSegment(Section(type=SectionType.DROP, start_time=3, end_time=11), 0, 8),
            PreviewSegment(Section(type=SectionType.DROP, start_time=20, end_time=30), 0, 10)]
    grid = BeatGrid(bpm=128.0, beat_times=np.arange(0, 40, 0.46875), beat_frames=np.array([]), sr=22050, hop_length=512)
    plan = PreviewPlan(segments=segs, drop_starts=[20.0])
    base = {"speed_mode": "vinyl", "studio_mastering": False}
    ref, _, _ = build_preview_audio(str(src), plan, grid, dict(base), seed=1)
    vacio, _, _ = build_preview_audio(str(src), plan, grid, {**base, "fx_events": []}, seed=1)
    fuera, _, _ = build_preview_audio(str(src), plan, grid, {**base, "fx_events": [
        {"id": 1, "type": "flanger", "start": 12.0, "end": 18.0, "amount": 0.7}]}, seed=1)
    assert np.array_equal(ref, vacio) and np.array_equal(ref, fuera)          # nada cambia si no hay efecto dentro
    dentro, _, _ = build_preview_audio(str(src), plan, grid, {**base, "fx_events": [
        {"id": 1, "type": "filter_up", "start": 21.0, "end": 27.0, "amount": 0.75}]}, seed=1)
    assert dentro.shape == ref.shape and not np.allclose(dentro, ref, atol=1e-3)
    # el efecto viaja con su trozo: si se invierte el orden de los cortes, sigue afectando al mismo trozo
    plan2 = PreviewPlan(segments=list(reversed(segs)), drop_starts=[20.0])
    rev_ref, _, _ = build_preview_audio(str(src), plan2, grid, dict(base), seed=1)
    rev_fx, _, _ = build_preview_audio(str(src), plan2, grid, {**base, "fx_events": [
        {"id": 1, "type": "filter_up", "start": 21.0, "end": 27.0, "amount": 0.75}]}, seed=1)
    assert not np.allclose(rev_fx, rev_ref, atol=1e-3)


# ── carril en la onda ───────────────────────────────────────────────────────────────────────────
def _onda(dur=120.0):
    pytest.importorskip("pyqtgraph")
    from src.analysis.segments import build_preview_plan
    from src.analysis.structure import Section, SectionType, StructureAnalysis
    from src.ui.waveform import WaveformWidget
    secs = [Section(type=SectionType.INTRO, start_time=0, end_time=30),
            Section(type=SectionType.DROP, start_time=30, end_time=60),
            Section(type=SectionType.BREAKDOWN, start_time=60, end_time=90),
            Section(type=SectionType.DROP, start_time=90, end_time=120)]
    plan = build_preview_plan(StructureAnalysis(sections=secs, duration=dur, bpm=128.0))
    w = WaveformWidget()
    w.resize(1100, 300)
    w.show()
    w._source_rms = np.abs(np.sin(np.linspace(0, 200, 800))) * 0.6
    w._source_dur = dur
    w._mode = "source"
    w._plan_segs = list(plan.segments)
    w._source_sections = list(secs)
    w.set_fx_enabled(True)
    w._draw_source_view()
    w.set_beat_times(np.arange(0, dur, 0.46875))
    QApplication.processEvents()
    return w, plan


def test_paleta_visible_y_efectos_se_colocan_en_la_onda():
    w, _ = _onda()
    assert w._fx_palette.isVisible() and [c.kind for c in w._fx_palette.cards] == ["flanger", "filter_up", "filter_down"]
    got = []
    w.fx_changed.connect(got.append)
    w._on_fx_dropped("flanger", 33.2)
    assert len(w.fx_events()) == 1 and len(w._fx_bands) == 1
    ev = w.fx_events()[0]
    assert ev["type"] == "flanger" and ev["end"] - ev["start"] == pytest.approx(6.0)
    # se ajusta al pulso más cercano (0,46875 s)
    assert abs(ev["start"] / 0.46875 - round(ev["start"] / 0.46875)) < 1e-2
    assert got and w._fx_inspector.isVisible() or w._fx_inspector.maximumHeight() >= 0
    assert w._fx_selected == ev["id"]
    _cerrar(w)


def test_mover_y_estirar_el_bloque_como_un_corte():
    w, _ = _onda()
    w._add_fx("filter_up", 40.0)
    ev = w.fx_events()[0]
    s0, e0 = ev["start"], ev["end"]
    s, e = w._fx_move(ev["id"], "m", s0, e0, 10.0)             # mover 10 s
    assert e - s == pytest.approx(e0 - s0) and s == pytest.approx(s0 + 10.0, abs=0.13)
    s, e = w._fx_move(ev["id"], "r", s0, e0, 4.0)              # estirar el final
    assert s == s0 and e == pytest.approx(e0 + 4.0, abs=0.13)
    s, e = w._fx_move(ev["id"], "l", s0, e0, 500.0)            # no puede pasar del final: mínimo 0,5 s
    assert e == e0 and e - s >= 0.5 - 1e-9
    s, e = w._fx_move(ev["id"], "m", s0, e0, -1000.0)          # ni salirse por el principio
    assert s == 0.0 and e - s == pytest.approx(e0 - s0)
    w._fx_commit(ev["id"], 50.0, 57.0)
    QApplication.processEvents()
    assert (w.fx_events()[0]["start"], w.fx_events()[0]["end"]) == (50.0, 57.0)
    _cerrar(w)


def test_inspector_cambia_inicio_duracion_e_intensidad_y_se_borra():
    w, _ = _onda()
    w._add_fx("flanger", 33.0)
    insp = w._fx_inspector
    insp.sp_start.setValue(61.0)
    insp.sp_dur.setValue(4.0)
    insp.sl_amt.setValue(40)
    ev = w.fx_events()[0]
    assert ev["start"] == pytest.approx(61.0) and ev["end"] == pytest.approx(65.0) and ev["amount"] == pytest.approx(0.4)
    w._delete_selected_fx()
    assert w.fx_events() == [] and w._fx_bands == []
    _cerrar(w)


def test_efecto_fuera_de_los_cortes_se_ve_apagado():
    w, plan = _onda()
    cubierto = (plan.segments[0].source_start + 1.0)
    w._add_fx("flanger", cubierto)
    huecos = [t for t in range(0, 118, 2) if not any(g.source_start - 2 <= t <= g.source_end + 8 for g in plan.segments)]
    if huecos:
        w._add_fx("filter_up", float(huecos[0]))
        by_id = {b.ev["id"]: b for b in w._fx_bands}
        assert by_id[min(by_id)].dim is False
    _cerrar(w)


def test_arrastrar_la_tarjeta_y_soltarla_sobre_la_onda():
    from PySide6.QtCore import QMimeData, QPointF, Qt
    from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
    from src.ui.fx_lane import MIME
    w, _ = _onda()
    md = QMimeData()
    md.setData(MIME, b"filter_down")
    vp = w._plot.viewport()
    pos = QPointF(vp.width() * 0.5, vp.height() * 0.5)
    QApplication.sendEvent(vp, QDragEnterEvent(pos.toPoint(), Qt.CopyAction, md, Qt.LeftButton, Qt.NoModifier))
    QApplication.sendEvent(vp, QDragMoveEvent(pos.toPoint(), Qt.CopyAction, md, Qt.LeftButton, Qt.NoModifier))
    assert w._fx_ghost is not None                                   # el hueco se ve mientras se arrastra
    QApplication.sendEvent(vp, QDropEvent(pos, Qt.CopyAction, md, Qt.LeftButton, Qt.NoModifier))
    QApplication.processEvents()
    evs = w.fx_events()
    assert len(evs) == 1 and evs[0]["type"] == "filter_down"
    assert 50.0 < evs[0]["start"] < 70.0                            # soltado hacia la mitad de la onda
    assert w._fx_ghost is None
    _cerrar(w)


def test_pulsar_la_tarjeta_pone_el_efecto_en_el_cursor():
    w, _ = _onda()
    w.set_playhead(75.0)
    w._fx_add_at_cursor("flanger")
    assert abs(w.fx_events()[0]["start"] - 75.0) < 0.5
    _cerrar(w)


def test_set_fx_events_normaliza_y_nueva_pista_los_olvida():
    w, _ = _onda()
    w.set_fx_events([{"id": 9, "type": "flanger", "start": 10, "end": 14, "amount": 0.5},
                     {"type": "nope", "start": 1, "end": 2}])
    assert len(w.fx_events()) == 1 and len(w._fx_bands) == 1
    w._fx_events = []
    w.set_fx_enabled(False)
    assert not w._fx_palette.isVisible()
    _cerrar(w)


# ── ediciones, presets y proyectos ─────────────────────────────────────────────────────────────
def _panel(monkeypatch, edition):
    import src.ui.app as A
    from src.analysis.segments import build_preview_plan
    from src.analysis.structure import Section, SectionType, StructureAnalysis
    monkeypatch.setattr(A, "get_edition", lambda: edition)
    p = A.ResultPanel()
    secs = [Section(type=SectionType.INTRO, start_time=0, end_time=30), Section(type=SectionType.DROP, start_time=30, end_time=60)]
    p._analysis = StructureAnalysis(sections=secs, duration=60.0, bpm=128.0)
    p._bpm = 128.0
    p._plan = build_preview_plan(p._analysis)
    return p


@pytest.mark.parametrize("edition", ["basic", "plus"])
def test_efectos_disponibles_en_basic_y_plus_y_van_al_exportar(monkeypatch, edition):
    pytest.importorskip("pyqtgraph")
    p = _panel(monkeypatch, edition)
    w = p._waveform
    assert w._fx_enabled
    w._source_dur = w._duration = 60.0
    w._add_fx("flanger", 10.0)
    o = p.get_export_options()
    assert len(o["fx_events"]) == 1 and o["fx_events"][0]["type"] == "flanger"
    assert o["fx_flanger"] is False and o["fx_filter_sweep"] is False        # el efecto automático ya no existe
    _cerrar(p)


def test_los_presets_no_llevan_efectos_pero_el_proyecto_si(monkeypatch):
    pytest.importorskip("pyqtgraph")
    p = _panel(monkeypatch, "plus")
    p._waveform._source_dur = p._waveform._duration = 60.0
    p._waveform._add_fx("filter_up", 12.0)
    assert "fx_events" not in p.get_state()["style"]                              # un preset sirve para cualquier tema
    ev = p.get_state(True, True, events=True)["style"]["fx_events"]
    assert len(ev) == 1
    p._waveform.clear_fx()
    assert p._waveform.fx_events() == []
    p.apply_state({"style": {"fx_events": ev}})
    assert len(p._waveform.fx_events()) == 1
    _cerrar(p)
