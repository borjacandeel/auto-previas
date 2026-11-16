"""v6.5.3: los efectos se oyen al reproducir el tema (sin «▶ Oír») y entran y salen de forma progresiva."""
import numpy as np

from src.engine.fx_events import apply_events_to_source, progressive_envelope


def test_envolvente_progresiva_sube_y_baja():
    sr = 1000
    w = progressive_envelope(10 * sr, sr)                     # efecto de 10 s → rampas de 3 s
    assert w[0] == 0.0 and abs(w[-1]) < 1e-3
    assert 0.0 < w[int(1.5 * sr)] < 1.0 and w[5 * sr] == 1.0
    assert np.all(np.diff(w[: 3 * sr]) >= -1e-6)               # subida sin saltos
    # si el efecto cae en dos trozos, la curva sigue siendo una sola
    a = progressive_envelope(4 * sr, sr, t0=0.0, ev_len=10.0)
    b = progressive_envelope(6 * sr, sr, t0=4.0, ev_len=10.0)
    assert np.allclose(np.concatenate([a, b]), w, atol=1e-4)


def test_efectos_sobre_el_tema_original_en_su_sitio():
    sr = 22050
    t = np.arange(6 * sr) / sr
    y = np.stack([np.sin(2 * np.pi * 220 * t), np.sin(2 * np.pi * 330 * t)]).astype(np.float32) * 0.5
    ev = [{"id": 1, "type": "filter_up", "start": 2.0, "end": 4.0, "amount": 0.9}]
    out = apply_events_to_source(y, sr, ev)
    assert out.shape == y.shape
    assert np.allclose(out[:, : 2 * sr], y[:, : 2 * sr]) and np.allclose(out[:, 4 * sr + 10:], y[:, 4 * sr + 10:])
    assert not np.allclose(out[:, int(3 * sr): int(3.2 * sr)], y[:, int(3 * sr): int(3.2 * sr)])
    assert apply_events_to_source(y, sr, []) is y                   # sin efectos: el mismo audio, sin copias


def test_el_monitor_prepara_la_copia_y_vuelve_al_original(tmp_path, qtbot=None):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import soundfile as sf
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QEventLoop, QTimer
    from src.ui.fx_monitor import FxMonitor
    app = QApplication.instance() or QApplication([])
    sr = 22050
    src = tmp_path / "tema.wav"
    sf.write(str(src), (np.random.default_rng(0).standard_normal((4 * sr, 2)) * 0.1).astype(np.float32), sr)
    m = FxMonitor(None, delay_ms=1, tmp_dir=tmp_path / "c")
    got = []
    m.ready.connect(lambda tok, p: got.append((m.is_current(tok), p)))
    m.set_source(str(src))
    m.set_events([{"id": 1, "type": "flanger", "start": 1.0, "end": 2.5, "amount": 0.8}])
    m.flush()
    loop = QEventLoop()
    for _ in range(100):
        QTimer.singleShot(50, loop.quit); loop.exec()
        if got:
            break
    assert got and got[-1][0] and got[-1][1].endswith(".wav")
    d, sr2 = sf.read(got[-1][1])
    assert sr2 == sr and d.shape[0] == 4 * sr
    m.set_events([])
    m.flush()
    app.processEvents()
    assert got[-1][1] == ""
    m.cleanup()
