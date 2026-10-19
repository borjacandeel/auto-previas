"""Tests de la 3.10.0: orden y nombres de los cortes, punto de inicio, arranque de BPM, firmar tema entero,
notificaciones con clic y animaciones."""
import os
import shutil
import subprocess
import time
from pathlib import Path

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


def _espera(cond, secs=60):
    t0 = time.time()
    while time.time() - t0 < secs and not cond():
        QApplication.processEvents()
        time.sleep(0.02)
    return cond()


def _ffmpeg():
    from src.config import get_ffmpeg_path
    return get_ffmpeg_path()


# ── cortes: nombres fijos y orden ───────────────────────────────────────────────────────────────
def _analisis(dur=120.0):
    from src.analysis.structure import Section, SectionType, StructureAnalysis
    secs = [Section(type=SectionType.INTRO, start_time=0, end_time=30),
            Section(type=SectionType.DROP, start_time=30, end_time=60),
            Section(type=SectionType.BREAKDOWN, start_time=60, end_time=90),
            Section(type=SectionType.DROP, start_time=90, end_time=120)]
    return StructureAnalysis(sections=secs, duration=dur, bpm=128.0)


def test_los_cortes_reciben_nombres_fijos_por_orden_en_la_cancion():
    from src.analysis.segments import PreviewSegment, assign_cut_ids, build_preview_plan
    from src.analysis.structure import Section, SectionType
    plan = build_preview_plan(_analisis())
    assert [s.cut_id for s in plan.segments] == list(range(1, len(plan.segments) + 1))
    # un corte nuevo recibe el siguiente número y los existentes no cambian
    nuevo = PreviewSegment(Section(type=SectionType.DROP, start_time=2, end_time=10), 0, 8)
    ids = [s.cut_id for s in plan.segments]
    plan.segments.append(nuevo)
    assign_cut_ids(plan.segments)
    assert nuevo.cut_id == max(ids) + 1 and [s.cut_id for s in plan.segments[:-1]] == ids


def _panel(monkeypatch, edition):
    import src.ui.app as A
    from src.analysis.segments import build_preview_plan
    monkeypatch.setattr(A, "get_edition", lambda: edition)
    p = A.ResultPanel()
    p._analysis = _analisis()
    p._bpm = 128.0
    p._plan = build_preview_plan(p._analysis)
    p._fill_plan(p._plan, animate=False)
    return p


@pytest.mark.parametrize("edition", ["basic", "plus"])
def test_ordenar_cortes_y_punto_de_inicio_en_basic_y_plus(monkeypatch, edition):
    p = _panel(monkeypatch, edition)
    tbl = p._tbl_cuts
    n = len(p._plan.segments)
    assert n >= 2
    nombres = [tbl.cellWidget(r, 0).text() for r in range(n)]
    assert nombres[0] == "1º · Corte 1" and nombres[1] == "2º · Corte 2"
    # ▼ en el primero: ahora suena segundo, pero sigue llamándose «Corte 1»
    p._move_cut(0, 1)
    assert [s.cut_id for s in p._plan.segments][:2] == [2, 1]
    assert tbl.cellWidget(0, 0).text() == "1º · Corte 2" and tbl.cellWidget(1, 0).text() == "2º · Corte 1"
    p._move_cut(0, -1)                                         # en el borde no hace nada
    assert [s.cut_id for s in p._plan.segments][:2] == [2, 1]
    # el orden de la tabla es el orden en que se exportará
    assert [s.source_start for s in p._plan.segments] == [r[0] for r in p._cut_rows()]
    # empezar al inicio / a mitad del tema
    dur_primero = p._plan.segments[0].duration
    p._start_at_beginning()
    assert p._plan.segments[0].source_start == pytest.approx(0.0, abs=0.6)
    assert p._plan.segments[0].duration == pytest.approx(dur_primero, abs=0.2)
    p._start_at_middle()
    assert abs(p._plan.segments[0].source_start - 60.0) < 2.5
    # edición: Basic y Plus ven el editor de cortes; solo Plus las pestañas de BPM y estructura
    p._chk_advanced.setChecked(True)
    assert not p._chk_advanced.isHidden()
    assert p._tabs.isTabVisible(0) and p._tabs.isTabVisible(1) == (edition == "plus") and p._tabs.isTabVisible(2) == (edition == "plus")
    _cerrar(p)


def test_la_ventana_de_la_waveform_usa_el_numero_fijo_del_corte(monkeypatch):
    pytest.importorskip("pyqtgraph")
    from src.ui.waveform import WaveformWidget
    w = WaveformWidget()
    from src.analysis.segments import PreviewPlan
    p = _panel(monkeypatch, "plus")
    p._move_cut(0, 1)
    w._plan_segs = list(p._plan.segments)
    assert w._cut_n(0) == 2 and w._cut_n(1) == 1
    _cerrar(w, p)


# ── arranque de BPM (Plus) ───────────────────────────────────────────────────────────────────────
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


def test_arranque_vinilo_por_defecto_y_bpm_originales(tmp_path):
    from src.engine.export import build_preview_audio
    src, plan, grid = _plan_sintetico(tmp_path)
    base = {"speed_mode": "vinyl", "studio_mastering": False}
    por_defecto, sr, _ = build_preview_audio(src, plan, grid, dict(base), seed=1)
    explicito, _, _ = build_preview_audio(src, plan, grid, {**base, "start_mode": "vinyl", "start_spin_sec": 1.0}, seed=1)
    assert np.array_equal(por_defecto, explicito)                  # el comportamiento de siempre no cambia
    original, _, _ = build_preview_audio(src, plan, grid, {**base, "start_mode": "original"}, seed=1)
    n = int(0.5 * sr)
    rms = lambda a: float(np.sqrt((a[:, :n] ** 2).mean()))
    assert rms(original) > rms(por_defecto) * 1.5                  # sin arranque, el inicio suena ya a tempo y volumen
    lento, _, _ = build_preview_audio(src, plan, grid, {**base, "start_mode": "vinyl", "start_spin_sec": 3.0}, seed=1)
    assert lento.shape[1] > por_defecto.shape[1]                   # arranque más largo = previa más larga


def test_boton_de_arranque_solo_en_plus_y_se_guarda_en_los_presets(monkeypatch):
    p = _panel(monkeypatch, "plus")
    assert p.get_export_options()["start_mode"] == "vinyl"
    p._set_start_mode("original")
    p._spin_start.setValue(2.0)
    o = p.get_export_options()
    assert o["start_mode"] == "original" and o["start_spin_sec"] == 2.0
    estado = p.get_state()
    assert estado["style"]["start"] == {"mode": "original", "sec": 2.0}
    p._set_start_mode("vinyl")
    p.apply_state(estado)
    assert p._start_mode == "original" and p._spin_start.value() == 2.0
    _cerrar(p)
    b = _panel(monkeypatch, "basic")
    b._set_start_mode("original")
    assert b.get_export_options()["start_mode"] == "vinyl"         # en Basic siempre el efecto de vinilo
    _cerrar(b)


# ── firmar tema entero ───────────────────────────────────────────────────────────────────────────
def _wav24(path, sec=2.0, sr=48000):
    t = np.linspace(0, sec, int(sr * sec), endpoint=False)
    y = np.stack([0.5 * np.sin(2 * np.pi * 440 * t), 0.4 * np.sin(2 * np.pi * 660 * t)], 1)
    sf.write(str(path), y, sr, subtype="PCM_24")
    return str(path)


def _caratula(path):
    from PIL import Image
    Image.new("RGB", (900, 700), (200, 20, 40)).save(path)
    return str(path)


def test_id3_en_wav_no_rompe_el_audio_y_corrige_la_cabecera(tmp_path):
    import struct
    from src.engine.sign import append_id3_to_wav, build_id3v23
    wav = _wav24(tmp_path / "a.wav")
    antes = sf.read(wav, dtype="int32")[0]
    tag = build_id3v23({"title": "Tema", "artist": "Radical Records", "year": "2026", "bpm": "128"}, b"\xff\xd8\xff\xe0JPEGDATA")
    assert tag[:3] == b"ID3" and tag[3] == 3
    append_id3_to_wav(wav, tag)
    data = Path(wav).read_bytes()
    assert struct.unpack("<I", data[4:8])[0] == len(data) - 8       # tamaño RIFF correcto
    assert b"id3 " in data[-len(tag) - 16:]
    despues = sf.read(wav, dtype="int32")[0]
    assert np.array_equal(antes, despues)


@pytest.mark.skipif(_ffmpeg() is None, reason="sin FFmpeg")
@pytest.mark.parametrize("fmt", ["flac", "wav"])
def test_firmar_tema_conserva_el_audio_exacto_y_mete_caratula_y_etiquetas(tmp_path, fmt):
    from src.engine.sign import sign_track
    src = _wav24(tmp_path / "Mi Tema.wav")
    res = sign_track(src, str(tmp_path / "out"), fmt, _caratula(tmp_path / "c.png"),
                     {"title": "Mi Tema", "artist": "Radical Records", "label": "RR", "genre": "Techno"})
    assert Path(res["path"]).suffix == f".{fmt}" and res["sr"] == 48000 and res["bits"] == 24 and res["cover"]
    a = sf.read(res["path"], dtype="int32", always_2d=True)
    b = sf.read(src, dtype="int32", always_2d=True)
    assert a[1] == b[1] == 48000 and np.array_equal(a[0], b[0])      # ni master, ni efectos, ni cambios
    if shutil.which("ffprobe"):
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:stream_disposition=attached_pic:format_tags=title,artist,genre",
                              "-of", "default=nw=1", res["path"]], capture_output=True, text=True).stdout
        assert "attached_pic=1" in out and "artist=Radical Records" in out and "genre=Techno" in out
    # no pisa un archivo existente
    otra = sign_track(src, str(tmp_path / "out"), fmt, None, {})
    assert otra["path"] != res["path"] and Path(res["path"]).exists()


@pytest.mark.skipif(_ffmpeg() is None, reason="sin FFmpeg")
def test_firmar_un_mp3_avisa_de_que_no_gana_calidad(tmp_path):
    from src.engine.sign import sign_track
    src = _wav24(tmp_path / "t.wav")
    mp3 = str(tmp_path / "t.mp3")
    subprocess.run([_ffmpeg(), "-y", "-v", "error", "-i", src, "-b:a", "192k", mp3], check=True)
    res = sign_track(mp3, str(tmp_path / "out"), "flac", None, {"artist": "X"})
    assert "origen_con_perdida" in res["warnings"] and Path(res["path"]).exists()


@pytest.mark.skipif(_ffmpeg() is None, reason="sin FFmpeg")
def test_ventana_firmar_arrastrar_y_firmar_de_principio_a_fin(tmp_path):
    from src.ui.sign_track import SignTrackDialog
    d = SignTrackDialog({"output_dir": str(tmp_path / "Music" / "Previas")})
    assert d._out_dir.endswith("Firmados") and d.fmt() == "flac"
    a, b = _wav24(tmp_path / "uno.wav"), _wav24(tmp_path / "dos.wav")
    d.add_files([a, b, str(tmp_path / "no_audio.txt")])
    assert d.files() == [a, b] and not d._ed["title"].isEnabled()    # con varios temas, el título es el de cada archivo
    d.add_files([a])
    assert len(d.files()) == 2                                       # sin duplicados
    d._set_cover(_caratula(tmp_path / "c.png"))
    d._out_dir = str(tmp_path / "salida")
    d._rb_wav.setChecked(True)
    d._start()
    assert _espera(lambda: d._worker is not None and not d._worker.isRunning())
    QApplication.processEvents()
    assert len(d._results) == 2 and all(r["format"] == "wav" for r in d._results)
    assert sorted(p.name for p in (tmp_path / "salida").glob("*.wav")) == ["dos.wav", "uno.wav"]
    assert d._bar.value() == 100 and "firmados" in d._lbl_status.text()
    _cerrar(d)


def test_boton_firmar_tema_solo_en_plus(monkeypatch):
    import src.ui.app as A
    for ed, visible in (("plus", True), ("basic", False)):
        monkeypatch.setattr(A, "get_edition", lambda ed=ed: ed)
        w = A.MainWindow()
        assert (not w._btn_sign.isHidden()) == visible
        _cerrar(w)


# ── notificaciones: logo y clic que abre la carpeta ────────────────────────────────────────────────
class _FakeTray:
    instances = []

    def __init__(self):
        self.shown, self.messages, self.hidden = False, [], False
        self.clicked_cb = None
        self.messageClicked = type("S", (), {"connect": lambda s, cb: setattr(self, "clicked_cb", cb)})()
        _FakeTray.instances.append(self)

    def setIcon(self, i): self.icon = i
    def setToolTip(self, t): self.tip = t
    def show(self): self.shown = True
    def hide(self): self.hidden = True
    def showMessage(self, title, msg, icon, ms): self.messages.append((title, msg, icon.isNull(), ms))


def test_notificacion_con_logo_y_clic_abre_la_carpeta(monkeypatch, tmp_path):
    from src import notifications as N
    monkeypatch.setattr(N, "_tray", None)
    _FakeTray.instances.clear()
    monkeypatch.setattr(N, "_make_tray", lambda: _FakeTray())
    abiertos = []
    monkeypatch.setattr(N, "reveal_in_os", lambda p: abiertos.append(p) or True)
    previa = tmp_path / "PREVIA - Tema.mp3"
    previa.write_bytes(b"x")
    N.notify("AutoPrevias", "✅ Previa «Tema» generada · pulsa para abrir", folder=str(previa))
    tray = _FakeTray.instances[0]
    assert tray.shown and tray.messages[0][0] == "AutoPrevias"
    assert tray.messages[0][2] is False                              # lleva icono (el logo)
    tray.clicked_cb()                                                # el usuario pulsa la notificación
    assert abiertos == [str(previa)]
    N.notify("AutoPrevias", "otra", folder=str(tmp_path))            # reutiliza el mismo icono de bandeja
    assert len(_FakeTray.instances) == 1
    tray.clicked_cb()
    assert abiertos[-1] == str(tmp_path)


def test_icono_de_notificacion_existe_y_es_cuadrado():
    from PIL import Image
    from src.notifications import notify_icon_path
    p = notify_icon_path()
    assert p is not None and p.exists()
    im = Image.open(p)
    assert im.size[0] == im.size[1] and im.mode == "RGBA" and im.getpixel((im.size[0] // 2, 6))[3] == 255   # fondo sólido, no transparente


def test_sin_bandeja_se_usa_el_metodo_antiguo(monkeypatch):
    from src import notifications as N
    monkeypatch.setattr(N, "_tray", None)
    monkeypatch.setattr(N, "_make_tray", lambda: None)               # el sistema no permite notificaciones propias
    enviados = []
    monkeypatch.setattr(N, "_send", lambda *a: enviados.append(a))
    N.notify("AutoPrevias", "hola", folder="/tmp")
    assert _espera(lambda: bool(enviados), secs=3)


def test_reveal_in_os_con_ruta_inexistente_no_falla():
    from src.notifications import reveal_in_os
    assert reveal_in_os("") is False
    assert reveal_in_os("/ruta/que/no/existe/de/ninguna/manera") is False


# ── animaciones ───────────────────────────────────────────────────────────────────────────────────
def test_animaciones_se_desactivan_con_la_variable_y_con_el_modo_ahorro(monkeypatch):
    from src.ui import anim
    assert anim.enabled() is False                                   # conftest: AUTOPREVIAS_NO_ANIM=1
    monkeypatch.delenv("AUTOPREVIAS_NO_ANIM")
    monkeypatch.setattr("src.perf.get_mode", lambda: "auto")
    assert anim.enabled() is True
    monkeypatch.setattr("src.perf.get_mode", lambda: "low")
    assert anim.enabled() is False


def test_cuenta_animada_termina_en_el_valor_exacto_y_reveal_pliega(monkeypatch):
    from PySide6.QtWidgets import QLabel, QWidget
    from src.ui import anim
    monkeypatch.delenv("AUTOPREVIAS_NO_ANIM")
    monkeypatch.setattr("src.perf.get_mode", lambda: "auto")
    lbl = QLabel("—")
    anim.count_up(lbl.setText, "129.0", ms=120, owner=lbl)
    assert _espera(lambda: lbl.text() == "129.0", secs=3)
    lbl2 = QLabel()
    anim.count_up(lbl2.setText, "2:00", ms=120, owner=lbl2)          # no numérico: directo
    assert lbl2.text() == "2:00"
    host = QWidget()
    inner = QLabel("contenido", host)
    inner.resize(200, 80)
    host.show()
    anim.reveal(inner, False, ms=100)
    assert _espera(lambda: not inner.isVisible(), secs=3)
    anim.reveal(inner, True, ms=100)
    assert inner.isVisible()
    assert _espera(lambda: inner.maximumHeight() == 16777215, secs=3)
    _cerrar(host)
