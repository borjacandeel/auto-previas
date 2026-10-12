"""Tests de la internacionalización ES/EN."""
import os
import re

import pytest

from src import i18n
from src.i18n_en import EN, EN_PATTERNS


@pytest.fixture(autouse=True)
def _reset_lang():
    i18n.set_language("es")
    i18n.clear_missing()
    yield
    i18n.set_language("es")


def test_castellano_por_defecto_aunque_el_sistema_este_en_ingles(monkeypatch):
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.setenv("LC_ALL", "en_US.UTF-8")
    assert i18n.init_from_config({}) == "es"
    assert i18n.init_from_config({"language": "en"}) == "en"
    assert i18n.init_from_config({"language": "fr"}) == "es"          # idioma desconocido → castellano
    assert i18n.DEFAULT_LANGUAGE == "es"


def test_castellano_no_traduce_nada():
    assert i18n.translate("▶   GENERAR PREVIA") == "▶   GENERAR PREVIA"
    assert i18n.tr("Hola {n}", n=3) == "Hola 3"


def test_ingles_traduce_exacto_con_espacios_y_patrones():
    i18n.set_language("en")
    assert i18n.translate("▶   GENERAR PREVIA") == "▶   GENERATE PREVIEW"
    assert i18n.translate("  Abrir archivo  ") == "  Open file  "
    assert i18n.translate("Extrayendo bloque 2/3 (12.5s)…") == "Extracting block 2/3 (12.5s)…"
    assert i18n.translate("Exportando MP3 128kbps con firma y carátula…") == "Exporting MP3 128kbps with signature and cover art…"
    assert i18n.translate("⚠ MP3 no disponible: boom") == "⚠ MP3 unavailable: boom"


def test_sin_traduccion_se_deja_igual_y_se_registra():
    i18n.set_language("en")
    assert i18n.translate("Texto inventado sin traducir") == "Texto inventado sin traducir"
    assert "Texto inventado sin traducir" in i18n.missing()
    i18n.translate("123 / 45")                                         # sin letras → no es un texto a traducir
    assert "123 / 45" not in i18n.missing()


def test_diccionario_coherente():
    for es, en in EN.items():
        assert en.strip(), f"traducción vacía: {es!r}"
        assert set(re.findall(r"\{(\w*)\}", es)) == set(re.findall(r"\{(\w*)\}", en)), f"marcadores distintos: {es!r}"
    assert len(EN) > 200


def test_patrones_validos():
    for rx, template in EN_PATTERNS:
        assert rx.groups == len(re.findall(r"\{\d+\}", template))


def test_traductor_de_widgets_en_caliente():
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGroupBox, QLabel, QLineEdit,
                                   QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QWidget, QVBoxLayout)
    app = QApplication.instance() or QApplication([])
    root = QWidget()
    lay = QVBoxLayout(root)
    lbl = QLabel("Nombre")
    btn = QPushButton("▶   GENERAR PREVIA"); btn.setToolTip("Semilla aleatoria")
    chk = QCheckBox("🔊 Master LUFS")
    box = QGroupBox("Carpeta")
    edit = QLineEdit(); edit.setPlaceholderText("PREVIA - NombreOriginal")
    combo = QComboBox(); combo.addItem("📍 Pre-Drop", "predrop"); combo.addItem("📍 Intro", "intro")
    tabs = QTabWidget(); tabs.addTab(QWidget(), "  📊 Estructura Musical  ")
    table = QTableWidget(0, 1); table.setHorizontalHeaderItem(0, QTableWidgetItem("Cambiar"))
    for w in (lbl, btn, chk, box, edit, combo, tabs, table):
        lay.addWidget(w)

    i18n.set_language("en"); i18n.translate_tree(root)
    assert (lbl.text(), btn.text(), btn.toolTip(), chk.text(), box.title()) == \
        ("Name", "▶   GENERATE PREVIEW", "Random seed", "🔊 Master LUFS", "Folder")
    assert edit.placeholderText() == "PREVIEW - OriginalName"
    assert combo.itemText(0) == "📍 Pre-Drop" and combo.itemData(0) == "predrop"   # los datos internos NO cambian
    assert tabs.tabText(0) == "  📊 Musical Structure  "
    assert table.horizontalHeaderItem(0).text() == "Change"

    # el código cambia un texto después de traducir → se toma como nuevo original
    lbl.setText("Seed:"); btn.setText("⏳   Generando previa…")
    i18n.translate_tree(root)
    assert btn.text() == "⏳   Generating preview…"

    # volver a castellano restaura el texto original exacto
    i18n.set_language("es"); i18n.translate_tree(root)
    assert (btn.text(), btn.toolTip(), box.title(), tabs.tabText(0)) == \
        ("⏳   Generando previa…", "Semilla aleatoria", "Carpeta", "  📊 Estructura Musical  ")
    assert edit.placeholderText() == "PREVIA - NombreOriginal" and table.horizontalHeaderItem(0).text() == "Cambiar"
    root.deleteLater()
