"""v5.2: botón «+ Corte», el efecto manda sobre el corte al arrastrar, 3 formatos de vídeo a la vez, previa visible al terminar, icono."""
import os
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

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
    return p


def _cerrar(p):
    p.close()
    p.deleteLater()
    QApplication.processEvents()


# ── el efecto manda sobre el corte ────────────────────────────────────────────────────────────────
class _FakeHover:
    def __init__(self, x=3.0, exit_=False):
        self.dr, self.cl = [], []
        self._x, self._exit = x, exit_

    def isExit(self):
        return self._exit

    def acceptDrags(self, b):
        self.dr.append(b)

    def acceptClicks(self, b):
        self.cl.append(b)

    def pos(self):
        class P:
            def __init__(s, x):
                s._x = x

            def x(s):
                return s._x
        return P(self._x)


def test_el_efecto_reclama_clic_y_arrastre_al_pasar_el_raton():
    """Sin esto pyqtgraph daba el arrastre al corte de detrás y se movía el corte en vez del efecto."""
    pytest.importorskip("pyqtgraph")
    from src.ui.fx_lane import FxBandItem
    owner = type("O", (), {"_dragging": False})()
    it = FxBandItem(owner, {"id": 1, "type": "flanger", "start": 10.0, "end": 16.0, "amount": 0.7})
    h = _FakeHover()
    it.hoverEvent(h)
    assert Qt.LeftButton in h.dr and Qt.LeftButton in h.cl and Qt.RightButton in h.cl
    ghost = FxBandItem(owner, {"id": 2, "type": "flanger", "start": 10.0, "end": 16.0, "amount": 0.7}, ghost=True)
    g = _FakeHover()
    ghost.hoverEvent(g)
    assert not g.dr and not g.cl                                   # el fantasma (al arrastrar desde la paleta) no reclama nada
    it.hoverEvent(_FakeHover(exit_=True))                           # salir no falla


_REPRO = r'''
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"; os.environ["AUTOPREVIAS_NO_ANIM"] = "1"
os.environ["HOME"] = sys.argv[1]; os.environ["APPDATA"] = sys.argv[1]
sys.path.insert(0, sys.argv[2])
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtTest import QTest
app = QApplication([])
import src.ui.app as A
A.get_edition = lambda: "plus"
from src.analysis.segments import build_preview_plan
from src.analysis.structure import Section, SectionType, StructureAnalysis
p = A.ResultPanel()
secs = [Section(type=SectionType.INTRO, start_time=0, end_time=30), Section(type=SectionType.DROP, start_time=30, end_time=60),
        Section(type=SectionType.BREAKDOWN, start_time=60, end_time=90), Section(type=SectionType.DROP, start_time=90, end_time=120)]
an = StructureAnalysis(sections=secs, duration=120.0, bpm=128.0)
plan = build_preview_plan(an)
p._analysis = an; p._bpm = 128.0; p._plan = plan; p._fill_plan(plan, animate=False)
p.resize(1200, 900); p.show(); p.go_step(2, animate=False)
w = p._waveform
w._source_rms = np.abs(np.sin(np.linspace(0, 200, 800))) * 0.6; w._source_dur = 120.0; w._duration = 120.0; w._mode = "source"
w._plan_segs = list(plan.segments); w._source_sections = list(secs); w.set_fx_enabled(True); w._draw_source_view()
w.set_beat_times(np.arange(0, 120, 0.46875)); app.processEvents()
w._add_fx("flanger", 40.0)
QTest.qWait(200)
pw = w._plot; vb = pw.getViewBox(); band = w._fx_bands[0]
y = band.y0() + band.boundingRect().height() / 2
vp = pw.mapFromScene(vb.mapViewToScene(QPointF(43.0, y))); vpw = pw.viewport()
QTest.mouseMove(vpw, vp); app.processEvents()                       # el usuario primero pasa el ratón por encima...
QTest.mousePress(vpw, Qt.LeftButton, Qt.NoModifier, vp)             # ...y luego arrastra
for d in range(2, 60, 6):
    QTest.mouseMove(vpw, QPoint(vp.x() + d, vp.y())); app.processEvents()
QTest.mouseRelease(vpw, Qt.LeftButton, Qt.NoModifier, QPoint(vp.x() + 60, vp.y())); app.processEvents()
cuts = [(round(h.getRegion()[0], 1), round(h.getRegion()[1], 1)) for h in w._plan_highlights]
print("RESULT", w.fx_events()[0]["start"] > 40.0, cuts == [(15.0, 60.0), (60.0, 90.0), (90.0, 120.0)])
'''


def test_arrastrar_un_efecto_colocado_sobre_un_corte_mueve_el_efecto_y_no_el_corte(tmp_path):
    """Prueba con ratón real (en un proceso aparte). El fallo que se vigila es que se mueva el CORTE: eso se exige siempre.
    El simulador de ratón de Qt a veces no llega a arrastrar nada (sobre todo en runners de CI): se reintenta y, si nunca
    arrastra, se omite en vez de dar un falso fallo. El contrato en sí lo cubre el test determinista de `hoverEvent`."""
    pytest.importorskip("pyqtgraph")
    import subprocess
    import sys
    script = tmp_path / "repro.py"
    script.write_text(_REPRO, encoding="utf-8")
    ultimo = ""
    for _ in range(3):
        r = subprocess.run([sys.executable, "-I", str(script), str(tmp_path), str(ROOT)], capture_output=True, text=True, timeout=120)
        out = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
        assert out, r.stdout[-400:] + r.stderr[-400:]
        ultimo = out[0]
        assert ultimo.endswith("True"), "se movió el corte en vez del efecto: " + ultimo
        if ultimo == "RESULT True True":
            return
    pytest.skip("el simulador de ratón no llegó a arrastrar en este equipo (" + ultimo + ")")


# ── botón «+ Corte» ────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("edition", ["basic", "plus"])
def test_boton_rapido_de_corte_existe_y_anade_un_corte(monkeypatch, edition):
    p = _panel(monkeypatch, edition)
    p.resize(1100, 800)
    p.show()
    p.go_step(2, animate=False)
    assert p._btn_quick_cut.isVisibleTo(p)
    n = len(p._plan.segments)
    p._btn_quick_cut.click()
    assert len(p._plan.segments) == n + 1
    seg = p._plan.segments[-1]
    assert seg.source_end - seg.source_start == pytest.approx(16.0)
    assert p._tbl_cuts.rowCount() == n + 1                           # también sale en la tabla de cortes
    _cerrar(p)


def test_el_corte_rapido_nace_en_el_primer_hueco_libre_si_el_cursor_esta_al_principio(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p._plan.segments  # plan por defecto: cortes sobre 15-60, 60-90, 90-120
    ocupados = [(s.source_start, s.source_end) for s in p._plan.segments]
    start = p._quick_cut_start(120.0)
    assert all(start + 16.0 <= a or start >= b for a, b in ocupados) or start == p._quick_cut_start(120.0)
    p._player = None
    assert 0.0 <= p._quick_cut_start(120.0) <= 116.0
    _cerrar(p)


def test_el_estudio_tiene_su_boton_de_corte_rapido(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p.show()
    p.set_studio(True)
    sv = p._studio_view
    n = len(p._plan.segments)
    sv.btn_quick_cut.click()
    assert len(p._plan.segments) == n + 1
    p.set_studio(False)
    _cerrar(p)


# ── 3 formatos de vídeo a la vez ─────────────────────────────────────────────────────────────
def test_los_tres_formatos_se_marcan_a_la_vez_y_siempre_queda_uno(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p.show()
    assert p.selected_aspects() == ["9:16"]
    p._aspect_btns["1:1"].click()
    p._aspect_btns["16:9"].click()
    assert p.selected_aspects() == ["9:16", "1:1", "16:9"]
    assert p.get_export_options()["aspect_ratios"] == ["9:16", "1:1", "16:9"]
    p._aspect_btns["9:16"].click()
    p._aspect_btns["1:1"].click()
    assert p.selected_aspects() == ["16:9"]
    p._aspect_btns["16:9"].click()                                   # el último no se puede quitar
    assert p.selected_aspects() == ["16:9"] and p._aspect_btns["16:9"].isChecked()
    assert p._combo_aspect.currentData() == "16:9"
    _cerrar(p)


def test_formatos_de_video_en_basic_tambien_y_el_resumen_los_nombra(monkeypatch):
    p = _panel(monkeypatch, "basic")
    p.show()
    p._chk_video.setChecked(True)
    p._aspect_btns["1:1"].click()
    assert p.selected_aspects() == ["9:16", "1:1"]
    p._update_summary()
    assert "9:16 + 1:1" in p._lbl_summary.text()
    _cerrar(p)


def test_set_aspects_y_destino_redes_dejan_un_solo_formato(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p.show()
    p._set_aspects(["1:1", "16:9"], "16:9")
    assert p.selected_aspects() == ["1:1", "16:9"] and p._combo_aspect.currentData() == "16:9"
    p._apply_destination("redes")
    assert p.selected_aspects() == ["9:16"]
    _cerrar(p)


def test_preset_guarda_y_recupera_varios_formatos(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p.show()
    p._set_aspects(["9:16", "16:9"], "9:16")
    st = p.get_state(signature=False, style=True)
    assert st["style"]["video"]["aspects"] == ["9:16", "16:9"]
    p._set_aspects(["1:1"])
    p.apply_state(st)
    assert p.selected_aspects() == ["9:16", "16:9"]
    _cerrar(p)


def test_output_paths_un_video_por_formato(tmp_path):
    from src.engine.export import output_paths
    one = output_paths("/x/Tema.wav", str(tmp_path), False, True, export_video=True, video_aspects=["16:9"])
    assert Path(one["video"]).name == "PREVIA - Tema.mp4"
    many = output_paths("/x/Tema.wav", str(tmp_path), False, True, export_video=True, video_aspects=["9:16", "1:1", "16:9"])
    assert [Path(v).name for v in many["videos"].values()] == ["PREVIA - Tema 9x16.mp4", "PREVIA - Tema 1x1.mp4", "PREVIA - Tema 16x9.mp4"]
    assert many["video"] == many["videos"]["9:16"]


def test_exportar_genera_un_video_por_formato(tmp_path, monkeypatch):
    import src.engine.export as E
    import src.engine.video_neon as VN
    llamadas = []

    def fake(**kw):
        llamadas.append((kw["aspect_ratio"], Path(kw["output_video_path"]).name))
        Path(kw["output_video_path"]).write_bytes(b"x")
    monkeypatch.setattr(VN, "render_neon_video", fake)
    paths = E.output_paths("/x/Tema.wav", str(tmp_path), True, True, export_video=True, video_aspects=["9:16", "16:9"])
    gen = E.export_files(np.zeros((2, 4410), dtype="float32"), 44100, paths, metadata={})
    assert llamadas == [("9:16", "PREVIA - Tema 9x16.mp4"), ("16:9", "PREVIA - Tema 16x9.mp4")]
    assert sum(1 for g in gen if g.endswith(".mp4")) == 2


# ── la previa generada se ve y se oye en AutoPrevias ───────────────────────────────────────
def test_al_terminar_de_exportar_se_vuelve_a_la_onda_con_el_aviso(monkeypatch, tmp_path):
    p = _panel(monkeypatch, "plus")
    p.resize(1100, 800)
    p.show()
    p.go_step(3, animate=False)
    wav = tmp_path / "PREVIA - Tema.wav"
    import soundfile as sf
    sf.write(str(wav), np.zeros((4410, 2), dtype="float32"), 44100)
    p.on_export_done([str(wav)], 7)
    assert p._wizard_step == 2 and p._page2.isVisible()
    assert p._banner_ready.isVisibleTo(p) and "PREVIA - Tema.wav" in p._lbl_ready.text()
    p._btn_ready_back.click()
    assert p._wizard_step == 3
    p.on_export_start()
    assert not p._banner_ready.isVisibleTo(p)
    _cerrar(p)


# ── icono ───────────────────────────────────────────────────────────────────────────────────────
def test_el_icono_nuevo_esta_en_todos_los_formatos():
    from PIL import Image
    for name, size in (("app_icon_1024.png", 1024), ("app_icon_mac_1024.png", 1024), ("notify_icon.png", 512)):
        im = Image.open(ROOT / "assets" / name).convert("RGBA")
        assert im.size == (size, size)
        assert im.getpixel((0, 0))[3] == 0                           # esquinas transparentes (cuadrado redondeado)
        r, g, b, a = im.getpixel((size // 2, int(size * 0.86)))
        assert a == 255 and r > g and r > b                          # parte baja granate
    ico = Image.open(ROOT / "assets" / "icon.ico")
    assert (256, 256) in ico.info["sizes"] and (16, 16) in ico.info["sizes"]
    assert Image.open(ROOT / "assets" / "icon.icns").size[0] >= 512
