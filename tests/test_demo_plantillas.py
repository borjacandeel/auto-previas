"""v6.7: AutoPrevias Demo elige entre 4 plantillas (15 s, 30 s, 1 min y 2 min) sin poder tocar los cortes."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def _panel(monkeypatch, edition):
    import src.ui.app as A
    import src.config as C
    from src.analysis.segments import build_preview_plan
    from src.analysis.structure import Section, SectionType, StructureAnalysis
    monkeypatch.setattr(A, "get_edition", lambda: edition)
    monkeypatch.setattr(C, "get_edition", lambda: edition)
    p = A.ResultPanel()
    secs = [Section(type=SectionType.INTRO, start_time=0, end_time=60), Section(type=SectionType.DROP, start_time=60, end_time=120),
            Section(type=SectionType.BREAKDOWN, start_time=120, end_time=180), Section(type=SectionType.DROP, start_time=180, end_time=240)]
    p._analysis = StructureAnalysis(sections=secs, duration=240.0, bpm=128.0)
    p._bpm = 128.0
    p._plan = build_preview_plan(p._analysis)
    p._fill_plan(p._plan, animate=False)
    return p


def test_demo_tiene_cuatro_plantillas_y_cortes_bloqueados(monkeypatch, tmp_path):
    monkeypatch.setattr("src.config.get_user_data_dir", lambda: tmp_path)
    p = _panel(monkeypatch, "demo")
    assert [s for _, s in p._preset_buttons] == [15, 30, 60, 120]
    assert all(not b.isHidden() for b, _ in p._preset_buttons)
    durs = {}
    for b, sec in p._preset_buttons:
        b.click()
        assert p._active_preset_sec == sec
        durs[sec] = float(p._plan.estimated_duration_after_stretch)
    assert durs[15] < durs[30] < durs[60] < durs[120]
    assert getattr(p._waveform, "_locked", False)                # los cortes no se mueven en la Demo
    assert p._detail_card.isHidden() and p._btn_quick_cut.isHidden()


def test_basic_y_plus_siguen_con_dos_plantillas(monkeypatch, tmp_path):
    monkeypatch.setattr("src.config.get_user_data_dir", lambda: tmp_path)
    for ed in ("basic", "plus"):
        p = _panel(monkeypatch, ed)
        assert [s for _, s in p._preset_buttons] == [60, 120]
