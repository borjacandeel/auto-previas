"""Tests del recorrido de bienvenida (primera vez, pasos, traducción y limpieza de la pista de ejemplo)."""
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("soundfile")
from PySide6.QtWidgets import QApplication

from src import i18n

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _aislado(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.get_user_data_dir", lambda: tmp_path)
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


def _ventana(monkeypatch, edition, size=(1400, 900)):
    import src.config as C
    import src.ui.app as A
    monkeypatch.setattr(C, "get_edition", lambda: edition)
    monkeypatch.setattr(A, "get_edition", lambda: edition)
    cfg = C.load()
    cfg["edition"] = edition
    C.save(cfg)
    w = A.MainWindow()
    w.resize(*size)
    w.show()
    for _ in range(10):
        QApplication.processEvents()
    return w


def _pump(cond, secs=120):
    t0 = time.time()
    while time.time() - t0 < secs and not cond():
        QApplication.processEvents()
        time.sleep(0.05)
    return cond()


def test_solo_se_ofrece_en_instalacion_nueva():
    from src.ui import tour
    assert tour.should_offer_onboarding({}) is True
    assert tour.should_offer_onboarding({"onboarding_done": False, "recent_files": []}) is True
    assert tour.should_offer_onboarding({"onboarding_done": True}) is False          # ya decidió (hizo el recorrido u omitió)
    assert tour.should_offer_onboarding({"recent_files": ["/x/a.wav"]}) is False      # ya usaba la app antes


def test_marcar_hecho_se_guarda_en_la_config():
    import src.config as C
    from src.ui import tour
    assert C.load().get("onboarding_done") is False
    tour.mark_onboarding_done()
    assert C.load()["onboarding_done"] is True
    assert tour.should_offer_onboarding(C.load()) is False


def test_pista_de_ejemplo_tiene_bpm_y_estructura(tmp_path):
    import soundfile as sf
    from src.ui import tour
    p = tour.make_demo_track(tmp_path / "demo.wav", sec=20)
    info = sf.info(str(p))
    assert info.samplerate == 44100 and info.channels == 2 and 19.5 < info.duration < 20.5


@pytest.mark.parametrize("edition", ["plus", "basic"])
def test_todos_los_pasos_tienen_traduccion_inglesa(monkeypatch, edition):
    from src.ui import tour
    w = _ventana(monkeypatch, edition)
    steps = tour.build_steps(w)
    assert len(steps) >= 24
    assert steps[0].key == "bienvenida" and steps[-1].key == "fin"
    keys = [s.key for s in steps]
    assert len(set(keys)) == len(keys)
    assert sum(s.demo_trigger for s in steps) == 1
    from src.i18n_en import EN
    for s in steps:
        for txt in (s.title, s.text, s.example):
            if txt:
                assert txt in EN, f"falta traducción: {txt!r}"
    for txt in ("Omitir recorrido", "← Atrás", "Siguiente →", "¡Terminar!", "PASO {n} DE {t}", "Omitir",
                "¡Bienvenido a AutoPrevias!", "▶  Hacer el recorrido", "Ver recorrido de bienvenida"):
        assert txt in EN
    # la edición Básica no enseña funciones de Plus (lote, presets, efectos…)
    if edition == "basic":
        assert not {"lote", "vigilar", "presets", "avanzado", "efectos", "voice_drop", "modo_promo", "firma",
                    "personalizar", "titulo", "imagen"} & set(keys)
    else:
        assert {"lote", "vigilar", "presets", "avanzado", "efectos", "voice_drop", "modo_promo", "firma", "personalizar"} <= set(keys)
    _cerrar(w)


def test_dialogo_de_bienvenida_omitir_y_recorrido():
    from src.ui import tour
    d = tour.WelcomeDialog()
    assert d.choice == "skip"
    d._pick("tour")
    assert d.choice == "tour"
    d2 = tour.WelcomeDialog()
    d2.reject()
    assert d2.choice == "skip"
    _cerrar(d, d2)


@pytest.mark.parametrize("size", [(1400, 900), (980, 640)])        # la ventana mínima desborda el panel: hay que desplazar también en horizontal
def test_recorrido_completo_sin_dejar_rastro(monkeypatch, size):
    import src.config as C
    from src.ui import tour
    w = _ventana(monkeypatch, "plus", size)
    antes = (w._results._chk_video.isChecked(), w._results._chk_advanced.isChecked(), w._results._adv_open)
    w.start_tour()
    T = w._tour
    assert T is not None and T._overlay is not None
    visto = []
    t0 = time.time()
    while w._tour is not None and time.time() - t0 < 300:
        QApplication.processEvents()
        if T._busy:
            time.sleep(0.1)
            continue
        st = T._steps[T._i]
        if st.target is not None:                        # todo paso con objetivo resalta algo (en CI lenta puede tardar)
            assert _pump(lambda: not T._overlay._hole.isNull(), secs=5), f"sin resaltado: {st.key}"
        else:
            for _ in range(10):
                QApplication.processEvents()
                time.sleep(0.02)
        visto.append(st.key)
        T._overlay.next_clicked.emit()
        for _ in range(8):
            QApplication.processEvents()
            time.sleep(0.02)
    assert w._tour is None
    assert visto[0] == "bienvenida" and visto[-1] == "fin" and "onda" in visto and "generar" in visto
    # sin rastro: ni Recientes, ni pista cargada, ni ajustes tocados
    assert C.load().get("recent_files") == []
    assert w._current_file == "" and w._analysis is None and w._stack.currentIndex() == 0
    assert (w._results._chk_video.isChecked(), w._results._chk_advanced.isChecked(), w._results._adv_open) == antes
    demo = C.get_cache_dir() / "tour" / tour.DEMO_NAME
    assert _pump(lambda: not demo.exists(), secs=10)               # en Windows el borrado puede esperar a que el reproductor suelte el archivo
    _cerrar(w)


def test_omitir_con_esc_a_mitad_de_recorrido(monkeypatch):
    w = _ventana(monkeypatch, "plus")
    finished = []
    w.start_tour()
    w._tour.finished.connect(finished.append)
    for _ in range(3):
        w._tour._overlay.next_clicked.emit()
        for _ in range(8):
            QApplication.processEvents()
            time.sleep(0.02)
    w._tour._overlay.skip_clicked.emit()
    assert finished == [False] and w._tour is None
    _cerrar(w)
