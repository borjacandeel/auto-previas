"""v5.1: «▶ Oír efecto» — escuchar un efecto suelto sobre el tema original."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sf = pytest.importorskip("soundfile")
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from src import i18n
from src.engine.fx_events import FX_TYPES, render_effect_preview

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


def _wav(tmp_path, sec=20.0, sr=44100, stereo=True):
    t = np.linspace(0, sec, int(sr * sec), endpoint=False)
    y = (0.3 * np.sin(2 * np.pi * 220 * t) + 0.1 * np.random.RandomState(1).randn(t.size)).astype("float32")
    data = np.stack([y, y * 0.9], 1) if stereo else y
    p = tmp_path / "tema.wav"
    sf.write(str(p), data, sr, subtype="PCM_16")
    return str(p), sr


@pytest.mark.parametrize("kind", FX_TYPES)
@pytest.mark.parametrize("stereo", [True, False])
def test_el_trozo_dura_el_efecto_mas_dos_segundos_a_cada_lado_y_cambia_el_audio(tmp_path, kind, stereo):
    path, sr = _wav(tmp_path, stereo=stereo)
    ev = {"id": 1, "type": kind, "start": 8.0, "end": 12.0, "amount": 0.75}
    out, osr = render_effect_preview(path, ev)
    assert osr == sr and out.shape[0] == 2 and np.isfinite(out).all() and np.max(np.abs(out)) <= 1.0
    assert abs(out.shape[1] / sr - 8.0) < 0.1                     # 2 s + 4 s de efecto + 2 s
    ref, _ = sf.read(path, start=int(6.0 * sr), frames=out.shape[1], dtype="float32", always_2d=True)
    ref = ref.T if stereo else np.vstack([ref.T, ref.T])
    pre = int(1.5 * sr)
    assert np.allclose(out[:, int(0.05 * sr):pre], ref[:, int(0.05 * sr):pre], atol=1e-3)      # antes del efecto: idéntico
    mid = slice(int(2.5 * sr), int(5.5 * sr))
    assert not np.allclose(out[:, mid], ref[:, mid], atol=1e-3)                                 # durante el efecto: cambia


def test_efecto_al_principio_del_tema_no_falla(tmp_path):
    path, sr = _wav(tmp_path)
    out, _ = render_effect_preview(path, {"id": 1, "type": "flanger", "start": 0.0, "end": 3.0, "amount": 0.5})
    assert abs(out.shape[1] / sr - 5.0) < 0.1                     # sin los 2 s de antes (no existen)


def test_boton_oir_emite_el_efecto_seleccionado_y_cambia_a_parar(tmp_path):
    from src.ui.waveform import HAS_PYQTGRAPH, WaveformWidget
    if not HAS_PYQTGRAPH:
        pytest.skip("sin pyqtgraph")
    w = WaveformWidget()
    w._source_dur = w._duration = 30.0
    w.set_fx_enabled(True)
    w._add_fx("flanger", 5.0)
    vistos = []
    w.fx_audition_requested.connect(vistos.append)
    w._fx_inspector.btn_play.click()
    assert len(vistos) == 1 and vistos[0]["type"] == "flanger"
    w.set_fx_playing(True)
    assert "Parar" in w._fx_inspector.btn_play.text()
    w.set_fx_playing(False)
    assert "Oír" in w._fx_inspector.btn_play.text()
    w._fx_selected = None
    w._fx_inspector.audition.emit()
    assert len(vistos) == 1                                        # sin efecto seleccionado no emite
    w.deleteLater()


def test_el_panel_prepara_el_efecto_y_lo_para_al_pulsar_otra_vez(tmp_path, monkeypatch):
    import src.ui.app as A
    monkeypatch.setattr(A, "get_edition", lambda: "plus")
    p = A.ResultPanel()
    path, _ = _wav(tmp_path)
    p._source_path = path
    llamadas = []

    class _Aud:
        def __init__(self):
            self.on = False

        def is_playing(self):
            return self.on

        def play_event(self, src, ev):
            llamadas.append(("play", src, ev["type"]))
            self.on = True
            return True

        def stop(self):
            llamadas.append(("stop",))
            self.on = False

        def release(self):
            pass
    p._fx_aud = _Aud()
    ev = {"id": 1, "type": "filter_up", "start": 4.0, "end": 8.0, "amount": 0.75}
    p._audition_fx(ev)
    p._audition_fx(ev)                                             # segunda pulsación = parar
    assert llamadas == [("play", path, "filter_up"), ("stop",)]
    p.close()
    p.deleteLater()


def test_el_reproductor_propio_toca_un_efecto_real_y_libera_el_archivo(tmp_path):
    from src.ui.fx_audition import FxAuditioner
    path, _ = _wav(tmp_path)
    aud = FxAuditioner(tmp_dir=tmp_path / "aud")
    if not aud.available:
        pytest.skip("sin QtMultimedia")
    ev = {"id": 1, "type": "flanger", "start": 5.0, "end": 8.0, "amount": 0.75}
    assert aud.play_event(path, ev) is True
    assert (tmp_path / "aud" / "fx_audition.wav").exists()
    aud.release()
    assert aud.play_event(path, ev) is True                       # reescribir tras liberar no falla
    aud.release()
    (tmp_path / "aud" / "fx_audition.wav").unlink()               # y se puede borrar (Windows)
