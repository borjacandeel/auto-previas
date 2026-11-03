"""AutoPrevias Demo: 7 días por equipo, a prueba de borrados parciales, de manipulación y de cambios de reloj."""
import json
import time

import pytest

from src.licensing import demo

DAY = 86400


@pytest.fixture
def aislado(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPREVIAS_DEVICE_ID", "equipo-test")
    monkeypatch.setattr(demo, "_locations", lambda dev: [tmp_path / "a" / "demo.json", tmp_path / "b" / ".apdemo", tmp_path / "c" / ".apdemo2"])
    monkeypatch.setattr(demo, "_reg_read", lambda: None)
    monkeypatch.setattr(demo, "_reg_write", lambda rec: None)
    return tmp_path


def test_primer_arranque_empieza_la_cuenta_atras(aislado):
    t0 = 1_800_000_000
    st = demo.check_demo(now=t0)
    assert st.ok and st.days_left == 7 and st.start == t0
    assert demo.check_demo(now=t0 + 3 * DAY).days_left == 4


def test_caduca_a_los_7_dias_y_no_se_reinicia(aislado):
    t0 = 1_800_000_000
    demo.check_demo(now=t0)
    assert demo.check_demo(now=t0 + 7 * DAY + 5).status == "expired"
    assert demo.check_demo(now=t0 + 30 * DAY).status == "expired"


def test_borrar_una_copia_no_reinicia_y_se_restaura(aislado):
    t0 = 1_800_000_000
    demo.check_demo(now=t0)
    (aislado / "a" / "demo.json").unlink()                       # el usuario borra la carpeta de la app
    st = demo.check_demo(now=t0 + 6 * DAY)
    assert st.ok and st.days_left == 1                           # sigue contando desde el primer arranque
    assert (aislado / "a" / "demo.json").exists()                # y la copia borrada se restaura
    (aislado / "a" / "demo.json").unlink(); (aislado / "b" / ".apdemo").unlink()
    assert demo.check_demo(now=t0 + 8 * DAY).status == "expired"  # aunque queden menos copias


def test_copia_manipulada_bloquea(aislado):
    t0 = 1_800_000_000
    demo.check_demo(now=t0)
    p = aislado / "b" / ".apdemo"
    rec = json.loads(p.read_text())
    rec["start"] = t0 + 5 * DAY                                  # intenta «rejuvenecer» la demo sin conocer el sello
    p.write_text(json.dumps(rec))
    assert demo.check_demo(now=t0 + 8 * DAY).status == "tampered"
    p.write_text("basura")
    assert demo.check_demo(now=t0 + 8 * DAY).status == "tampered"


def test_copiar_la_demo_de_otro_equipo_no_vale(aislado, monkeypatch):
    t0 = 1_800_000_000
    demo.check_demo(now=t0)
    monkeypatch.setenv("AUTOPREVIAS_DEVICE_ID", "otro-equipo")
    assert demo.check_demo(now=t0 + DAY).status == "tampered"


def test_reloj_atrasado_bloquea(aislado):
    t0 = 1_800_000_000
    demo.check_demo(now=t0)
    demo.check_demo(now=t0 + 3 * DAY)
    assert demo.check_demo(now=t0 + 1 * DAY).status == "clock"   # volver el reloj atrás para ganar días


def test_servidor_recuerda_el_primer_arranque(aislado, monkeypatch):
    t0 = 1_800_000_000
    monkeypatch.setattr(demo, "server_start", lambda dev: {"start": t0 - 6 * DAY, "expires_at": t0 + DAY, "expired": False})
    st = demo.check_demo(now=t0, online=True)                    # equipo «nuevo» (carpetas borradas) pero el servidor ya lo conocía
    assert st.ok and st.days_left == 1
    monkeypatch.setattr(demo, "server_start", lambda dev: {"start": t0 - 9 * DAY, "expires_at": t0 - 2 * DAY, "expired": True})
    assert demo.check_demo(now=t0 + 1, online=True).status == "expired"


def test_la_demo_nunca_falla_en_abierto_sin_red(aislado, monkeypatch):
    monkeypatch.setattr(demo, "server_start", lambda dev: None)
    assert demo.check_demo(now=1_800_000_000, online=True).ok


def test_pantalla_de_fin_de_demo_y_edicion_demo(monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from src.ui.demo_dialog import DemoEndedDialog
    for st in ("expired", "clock", "tampered"):
        d = DemoEndedDialog(status=st)
        assert len(d._buy_buttons) == 2 and all(b.property("url").startswith("https://payhip.com/") for b in d._buy_buttons)
        d.deleteLater()
    from src import config
    monkeypatch.setattr(config, "_get_baked_edition", lambda: "demo")
    assert config.get_edition() == "demo"


def test_en_la_demo_los_cortes_estan_bloqueados(monkeypatch):
    pytest.importorskip("pyqtgraph")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from src.ui.waveform import WaveformWidget
    w = WaveformWidget()
    w.set_locked(True)
    assert w._locked is True and w._add_fx("flanger", 3.0) is None
    w.deleteLater()
