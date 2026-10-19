"""v5.0: asistente de 3 pasos (Tu tema · Tu previa · Exportar), destinos de un clic y modo Estudio."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from src import i18n
from src.ui.wizard import DESTINATIONS, STEPS, destination_settings

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


def _panel(monkeypatch, edition="plus"):
    from tests.test_audit_v4 import _panel as base
    return base(monkeypatch, edition)


def _cerrar(p):
    p.close()
    p.deleteLater()
    QApplication.processEvents()


# ── lógica pura de los destinos ──────────────────────────────────────────────────────────────────
def test_los_destinos_cuadran_con_lo_prometido():
    assert [k for k in DESTINATIONS] == ["redes", "radio", "sello", "club", "custom"]
    r = destination_settings("redes", plus=False)
    assert r["seconds"] == 15 and r["video"] and r["aspect"] == "9:16" and r["mp3"] and not r["wav"]
    assert destination_settings("radio", True)["seconds"] == 30
    assert destination_settings("sello", True)["wav"] is True and destination_settings("sello", False)["wav"] is False
    club = destination_settings("club", True)
    assert club["seconds"] == 120 and club["flac"] and club["start_mode"] == "vinyl" and club["end_mode"] == "vinyl"
    club_b = destination_settings("club", False)
    assert not club_b["flac"] and club_b["mp3"] and club_b["start_mode"] is None
    assert destination_settings("custom", True)["open_detail"] is True
    assert destination_settings("nada", True)["seconds"] == 0              # clave desconocida = «lo monto yo»


def test_basic_nunca_recibe_wav_ni_flac():
    for k in DESTINATIONS:
        s = destination_settings(k, plus=False)
        assert not s["wav"] and not s["flac"]


# ── pasos ────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("edition", ["basic", "plus"])
def test_dos_pasos_se_alternan_y_el_otro_no_ocupa_sitio(monkeypatch, edition):
    p = _panel(monkeypatch, edition)
    p.resize(1100, 800)
    p.show()
    p.go_step(2, animate=False)
    assert p._page2.isVisible() and not p._page3.isVisible()
    assert p._waveform.isVisibleTo(p) and not p._btn_generate.isVisibleTo(p)
    p.go_step(3, animate=False)
    assert p._page3.isVisible() and not p._page2.isVisible()
    assert p._btn_generate.isVisibleTo(p) and p._edit_name.isVisibleTo(p) and not p._waveform.isVisibleTo(p)
    assert p._stepper.current == 3
    _cerrar(p)


def test_la_cinta_de_pasos_y_los_botones_de_navegacion(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p.show()
    p.go_step(2, animate=False)
    p._btn_next.click()
    assert p._wizard_step == 3 and p._page3.isVisible()
    p._btn_back.click()
    assert p._wizard_step == 2 and p._page2.isVisible()
    p._stepper.chips[3].click()
    assert p._wizard_step == 3
    p._stepper.chips[2].click()
    assert p._wizard_step == 2
    assert "✓" in p._stepper.chips[1].text() and len(STEPS) == 3
    _cerrar(p)


def test_modo_estudio_enseña_todo_junto_y_sin_asistente(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p.resize(1100, 800)
    p.show()
    p.set_studio(True)
    assert p._page2.isVisible() and p._page3.isVisible()
    assert not p._stepper.isVisible() and not p._btn_next.isVisible() and not p._btn_back.isVisible()
    p.go_step(3)                                                             # no rompe nada en Estudio
    assert p._page2.isVisible() and p._page3.isVisible()
    p.set_studio(False)
    assert p._stepper.isVisible() and p._page3.isVisible() and not p._page2.isVisible()
    _cerrar(p)


# ── destinos aplicados a la interfaz ─────────────────────────────────────────────────────────────
def test_elegir_redes_deja_15s_mp3_y_video_vertical(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p._dest_card.buttons["redes"].click()
    assert p._active_preset_sec == 15
    assert p._chk_video.isChecked() and p._chk_mp3.isChecked() and not p._chk_wav.isChecked() and not p._chk_flac.isChecked()
    assert p._combo_aspect.currentData() == "9:16"
    _cerrar(p)


def test_elegir_club_en_plus_pone_flac_y_vinilo(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p._set_start_mode("original")
    p._set_end_mode("original")
    p._dest_card.buttons["club"].click()
    assert p._active_preset_sec == 120 and p._chk_flac.isChecked() and not p._chk_video.isChecked()
    assert p._start_mode == "vinyl" and p._end_mode == "vinyl"
    _cerrar(p)


def test_elegir_destino_en_basic_no_activa_formatos_de_plus(monkeypatch):
    p = _panel(monkeypatch, "basic")
    p._dest_card.buttons["club"].click()
    assert not p._chk_flac.isChecked() and not p._chk_wav.isChecked() and p._chk_mp3.isChecked()
    p._dest_card.buttons["sello"].click()
    assert not p._chk_wav.isChecked() and p._chk_mp3.isChecked()
    _cerrar(p)


def test_lo_monto_yo_abre_el_detalle_y_no_toca_formatos(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p._chk_flac.setChecked(True)
    p._dest_card.buttons["custom"].click()
    assert p._chk_advanced.isChecked() and p._chk_flac.isChecked()
    _cerrar(p)


def test_el_modo_promo_bloquea_el_cambio_de_formatos_del_destino(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p._chk_promo.setChecked(True)
    antes = (p._chk_wav.isChecked(), p._chk_mp3.isChecked(), p._chk_flac.isChecked())
    p._dest_card.buttons["club"].click()
    assert (p._chk_wav.isChecked(), p._chk_mp3.isChecked(), p._chk_flac.isChecked()) == antes
    _cerrar(p)
