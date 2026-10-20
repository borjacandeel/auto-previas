"""Temas de la app (Original · One Dark · Claro): transformación de colores, parches de Qt y selector en Ajustes."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from src import i18n, themes

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
    themes.uninstall()
    i18n.set_language("es")


def _lum(h):
    r, g, b = themes._hex_to_rgb(h)
    return themes._lum(r, g, b)


def test_hay_tres_temas_y_el_original_no_cambia_nada():
    assert themes.theme_keys() == ["original", "onedark", "light"]
    for h in ("#0a0b0e", "#ff1e38", "#eceef2", "#2ed573", "#ffffff"):
        assert themes.transform_hex(h, "original") == h
    assert themes.transform_css("QFrame { background: #10131a; color: rgba(255,30,56,.5); }", "original").count("#10131a") == 1


@pytest.mark.parametrize("key", ["onedark", "light"])
def test_los_grises_conservan_su_orden_de_oscuro_a_claro_o_al_reves(key):
    ramp = ["#0a0b0e", "#10131a", "#181b22", "#232733", "#2a2f3c", "#3a4050", "#555b6a", "#8c93a4", "#abb2bf", "#eceef2"]
    lum = [_lum(themes.transform_hex(h, key)) for h in ramp]
    if key == "onedark":
        assert lum == sorted(lum)                                   # fondos más oscuros que bordes, y estos que los textos
    else:
        # claro: los fondos son claros y el texto principal oscuro; el contraste texto/fondo es alto
        assert _lum(themes.transform_hex("#10131a", key)) > 0.9 and _lum(themes.transform_hex("#eceef2", key)) < 0.2


def test_el_acento_rojo_pasa_a_azul_en_one_dark_y_sigue_rojo_en_claro():
    r, g, b = themes._hex_to_rgb(themes.transform_hex("#ff1e38", "onedark"))
    assert b > r and b > g                                          # azul
    r, g, b = themes._hex_to_rgb(themes.transform_hex("#ff1e38", "light"))
    assert r > 180 and g < 60 and b < 90                            # rojo marca, un punto más oscuro
    # el rojo oscuro de «seleccionado» también cambia de familia en One Dark y se vuelve un tinte pálido en el claro
    r, g, b = themes._hex_to_rgb(themes.transform_hex("#2a1218", "onedark"))
    assert b > r
    assert _lum(themes.transform_hex("#2a1218", "light")) > 0.85
    # verdes y morados no se tocan en oscuro
    assert themes.transform_hex("#2ed573", "onedark") == "#2ed573"


def test_las_hojas_de_estilo_y_el_html_se_transforman_sin_romper_selectores_ni_entidades():
    css = "QPushButton#abcdef { background: #10131a; border: 1px solid rgba(255, 30, 56, .5); } QLabel { color: #fff; }"
    out = themes.transform_css(css, "onedark")
    assert "#abcdef" in out and "#10131a" not in out and "rgba(255, 30, 56" not in out
    assert themes.transform_css("<span>&#128640; <b style='color:#ff5468'>x</b></span>", "onedark").count("&#128640;") == 1
    assert themes.transform_css("sin colores", "light") == "sin colores"


def test_los_velos_negros_translucidos_se_conservan_en_oscuro_y_se_vuelven_blancos_en_claro():
    assert themes.transform_rgb("onedark", 3, 4, 8, 160) == (3, 4, 8)
    assert themes.transform_rgb("light", 3, 4, 8, 160) == (255, 255, 255)
    assert themes.transform_rgb("light", 18, 20, 26, 230) == (18, 20, 26)         # etiquetas casi opacas: siguen oscuras con su texto blanco


_PROBE = r'''
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, sys.argv[2])
from src import themes
themes.install(sys.argv[1])
from PySide6 import QtGui
from PySide6.QtWidgets import QApplication, QPushButton, QLabel
from PySide6.QtCore import QVariantAnimation
app = QApplication([])
out = []
out.append(QtGui.QColor("#ff1e38").name())
out.append(QtGui.QColor(10, 11, 14).name())
out.append(str(isinstance(QtGui.QColor("#fff"), QtGui.QColor)))
out.append(str(isinstance(QtGui.QPalette().color(QtGui.QPalette.Window), QtGui.QColor)))
b = QPushButton("x"); b.setStyleSheet("QPushButton { background: #10131a; }"); out.append(b.styleSheet())
l = QLabel(); l.setText("<b style='color:#ff5468'>hola</b>"); out.append(l.text())
an = QVariantAnimation(); an.setStartValue(QtGui.QColor("#0a0b0e")); an.setEndValue(QtGui.QColor("#ff1e38")); an.setDuration(10)
an.setCurrentTime(5); out.append(str(an.currentValue().isValid()))
import pyqtgraph as pg
out.append(pg.mkColor("#ff1e38").name())
print("|".join(out))
themes.uninstall()
print(QtGui.QColor("#ff1e38").name())
'''


@pytest.mark.parametrize("key,acc", [("onedark", "#4ba3eb"), ("light", "#eb0a24")])
def test_los_parches_de_qt_funcionan_en_un_proceso_propio_y_se_deshacen(tmp_path, key, acc):
    script = tmp_path / "probe.py"
    script.write_text(_PROBE, encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(script), key, str(ROOT)], capture_output=True, text=True, timeout=120)
    lines = [l for l in r.stdout.splitlines() if "|" in l or l.startswith("#")]
    assert lines, r.stderr[-500:]
    parts = lines[0].split("|")
    assert parts[0] == acc                                           # QColor("#ff1e38") ya viene con el acento del tema
    assert parts[2] == "True" and parts[3] == "True"                 # isinstance sigue valiendo
    assert "#10131a" not in parts[4] and "#ff5468" not in parts[5]   # hoja de estilo y HTML transformados
    assert parts[6] == "True"                                        # las animaciones de color siguen funcionando
    assert parts[7] == acc                                           # pyqtgraph (la onda) también
    assert lines[-1] == "#ff1e38"                                    # uninstall() restaura


def test_el_selector_de_tema_guarda_la_eleccion_y_pide_reiniciar(monkeypatch):
    import src.config as C
    from PySide6.QtWidgets import QMessageBox
    from src.ui.about import LicenseDialog
    asked = []

    class _Box:
        AcceptRole, RejectRole, Question = QMessageBox.AcceptRole, QMessageBox.RejectRole, QMessageBox.Question

        def __init__(self, *a):
            self._btns = []

        def setIcon(self, *a): pass
        def setWindowTitle(self, *a): pass
        def setText(self, t): asked.append(t)
        def setInformativeText(self, *a): pass
        def addButton(self, text, role):
            self._btns.append(text)
            return text
        def exec(self): pass
        def clickedButton(self): return self._btns[-1]                 # «Después»

    monkeypatch.setattr("src.ui.about.QMessageBox", _Box)
    d = LicenseDialog("5.3.0", "plus")
    assert set(d._theme_tiles) == set(themes.theme_keys()) and d._theme_tiles["original"].isChecked()
    d._theme_tiles["onedark"].click()
    assert C.load()["theme"] == "onedark" and d._theme_tiles["onedark"].isChecked() and not d._theme_tiles["original"].isChecked()
    assert asked and "reiniciar" in asked[0].lower()
    assert "reiniciar" in d._lbl_theme.text().lower()
    d._theme_tiles["original"].click()                                 # volver al tema en marcha: no pregunta
    assert len(asked) == 1 and C.load()["theme"] == "original"
    d.deleteLater()


def test_reiniciar_lanza_un_proceso_nuevo(monkeypatch):
    lanzados = []
    monkeypatch.setattr("subprocess.Popen", lambda args, **kw: lanzados.append((args, kw)))
    assert themes.restart_application() is True
    assert lanzados and lanzados[0][0][0] == sys.executable
