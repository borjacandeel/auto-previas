"""Tests de interfaz de las funciones de la 3.1 (diálogos, presets, modo promo, edición Básica)."""
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
sf = pytest.importorskip("soundfile")
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication

from src import history, i18n, presets

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _aislado(tmp_path, monkeypatch):
    """Cada test usa su propia carpeta de datos y arranca en castellano."""
    monkeypatch.setattr("src.config.get_user_data_dir", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    i18n.set_language("es")
    yield
    i18n.set_language("es")


def _wav(tmp_path, name="firma.wav", sec=1.0):
    p = tmp_path / name
    sf.write(str(p), np.zeros((int(44100 * sec), 2), dtype="float32"), 44100)
    return str(p)


# ── Licencia y ajustes ───────────────────────────────────────────────────────────
def test_describe_license_estados():
    from src.ui.about import describe_license
    assert describe_license(None)["state"] == "none"
    now = 1_000_000_000.0
    ok = describe_license({"key_hash": "abcdef1234567890", "verified_at": now - 2 * 86400}, now=now, grace_days=14)
    assert ok["state"] == "active" and ok["license_id"] == "ABCDEF12" and ok["days_left"] == 12
    caducada = describe_license({"key_hash": "x", "verified_at": now - 30 * 86400}, now=now, grace_days=14)
    assert caducada["state"] == "grace_expired" and caducada["days_left"] == 0


def test_dialogo_licencia_modo_desarrollo_y_cambio_de_idioma(monkeypatch):
    from src.ui.about import LicenseDialog
    monkeypatch.setattr("src.config._get_baked_edition", lambda: None)
    d = LicenseDialog("3.1.0", "plus")
    assert "desarrollo" in d._lbl_state.text() and not d._btn_remove.isEnabled()
    emitted = []
    d.language_changed.connect(emitted.append)
    d._combo_lang.setCurrentIndex(d._combo_lang.findData("en"))
    assert emitted == ["en"] and i18n.get_language() == "en"
    assert d._btn_update.text() == "Check for updates" and "Development mode" in d._lbl_state.text()
    d._combo_lang.setCurrentIndex(d._combo_lang.findData("es"))
    assert d._btn_update.text() == "Buscar actualizaciones" and "desarrollo" in d._lbl_state.text()
    d.deleteLater()


def test_dialogo_licencia_activa_y_desactivar(monkeypatch):
    from src.licensing import license as L
    from src.ui import about
    monkeypatch.setattr("src.config._get_baked_edition", lambda: "plus")
    L.save_local("CLAVE-X", "plus")
    d = about.LicenseDialog("3.1.0", "plus")
    assert "activa" in d._lbl_state.text() and "ID de licencia" in d._lbl_detail.text() and d._btn_remove.isEnabled()
    removed = []
    d.license_removed.connect(lambda: removed.append(True))

    class _Box:                                   # el aviso de confirmación responde «Desactivar»
        Warning, AcceptRole, RejectRole = 0, 0, 1
        def __init__(self, *_a): self._yes = None
        def setIcon(self, *_a): pass
        def setWindowTitle(self, *_a): pass
        def setText(self, *_a): pass
        def addButton(self, _t, role):
            b = object(); self._yes = b if role == 0 else self._yes; return b
        def exec(self): pass
        def clickedButton(self): return self._yes
    monkeypatch.setattr(about, "QMessageBox", _Box)
    d._remove_license()
    assert removed == [True] and L.load_local() is None
    d.deleteLater()


# ── Recientes ────────────────────────────────────────────────────────────────────
def test_historial_plus_lista_reabre_y_quita(tmp_path):
    from src.ui.history_dialog import HistoryDialog, pick_playable, format_summary
    src_wav = _wav(tmp_path, "pista.wav")
    mp3 = tmp_path / "PREVIA - pista.mp3"; mp3.write_bytes(b"x")
    eid = history.add_entry(src_wav, [str(mp3)], seed=9, bpm=128, key="8A", duration_sec=75, settings={"state": {}})
    d = HistoryDialog(plus=True, recent_tracks=[src_wav])
    assert d._table.rowCount() == 1 and d._table.item(0, 1).text() == "pista"
    assert d._table.item(0, 2).text() == "1:15" and d._table.item(0, 4).text() == "MP3"
    d._table.selectRow(0)
    assert d._btn_reopen.isEnabled() and d._btn_reveal.isEnabled()
    got = []
    d.reopen_requested.connect(got.append)
    d._reopen()
    assert got and got[0]["id"] == eid and got[0]["seed"] == 9
    d2 = HistoryDialog(plus=True, recent_tracks=[])
    d2._table.selectRow(0); d2._remove()
    assert d2._table.rowCount() == 0 and history.list_entries() == []
    assert pick_playable(["a.wav", "b.mp3"]) == "b.mp3" and format_summary(["x.mp3", "y.wav", "z.mp3"]) == "MP3 · WAV"
    for x in (d, d2): x.deleteLater()


def test_historial_basic_muestra_bloqueo():
    from src.ui.history_dialog import HistoryDialog
    history.add_entry("/x/a.wav", ["/x/a.mp3"])
    d = HistoryDialog(plus=False, recent_tracks=[])
    assert d._table.rowCount() == 0 and "PLUS" in d._lbl_empty.text()
    d.deleteLater()


# ── Presets ──────────────────────────────────────────────────────────────────────
def test_barra_de_presets_recarga_y_senales():
    from src.ui.presets_bar import PresetBar
    bar = PresetBar()
    assert bar.current_name() == "" and not bar._btn_apply.isEnabled()
    presets.save_preset("Radical Main", {"style": {"duration_sec": 60}})
    bar.reload(select="Radical Main")
    assert bar.current_name() == "Radical Main" and bar._btn_apply.isEnabled() and bar._btn_delete.isEnabled()
    got = []
    bar.apply_requested.connect(got.append)
    bar._btn_apply.click()
    assert got == ["Radical Main"]
    bar.deleteLater()


def test_dialogo_guardar_preset_valida_nombre_y_opciones():
    from src.ui.presets_bar import SavePresetDialog
    d = SavePresetDialog(["Radical Main"], "")
    d._accept()
    assert "nombre" in d._lbl_warn.text().lower() and d.result() == 0
    d._combo.setCurrentText("Radical Main")
    assert "sobrescribirá" in d._lbl_warn.text()
    d._chk_sig.setChecked(False); d._chk_style.setChecked(False)
    d._accept()
    assert "al menos una" in d._lbl_warn.text()
    d._chk_style.setChecked(True); d._accept()
    assert d.result_values() == ("Radical Main", False, True)
    d.deleteLater()


# ── Panel de resultados: modo promo, estado y edición Básica ─────────────────────
@pytest.fixture(autouse=True)
def _config_aislada(tmp_path, monkeypatch):
    """Los tests de interfaz guardan ajustes (vídeo, opciones avanzadas…): nunca sobre la configuración real."""
    import src.config as C
    monkeypatch.setattr(C, "get_config_path", lambda: tmp_path / "cfg_test.json")
    yield


def _panel(monkeypatch, edition="plus"):
    import src.ui.app as A
    monkeypatch.setattr(A, "get_edition", lambda: edition)
    return A.ResultPanel()


def test_modo_promo_fuerza_mp3_128_y_restaura_formatos(tmp_path, monkeypatch):
    p = _panel(monkeypatch)
    p._chk_wav.setChecked(True); p._chk_flac.setChecked(True)
    assert p.get_export_options()["promo_mode"] is False and "mp3_kbps" not in p.get_export_options()
    p._set_voice_drop_path(_wav(tmp_path))
    p._chk_promo.setChecked(True)
    o = p.get_export_options()
    assert o["promo_mode"] and o["export_mp3"] and not o["export_wav"] and not o["export_flac"] and o["mp3_kbps"] == 128
    assert not p._chk_wav.isEnabled() and p._chk_mp3.text() == "MP3 128k"
    # un preset guardado con el modo activo conserva los formatos reales del usuario
    st = p.get_state()["style"]
    assert st["export"]["wav"] is True and st["export"]["flac"] is True and st["promo"]["enabled"] is True
    p._chk_promo.setChecked(False)
    assert p._chk_wav.isChecked() and p._chk_flac.isChecked() and p._chk_wav.isEnabled() and p._chk_mp3.text() == "MP3 320k"
    p.deleteLater()


def test_estado_firma_y_estilo_ida_y_vuelta(tmp_path, monkeypatch):
    p = _panel(monkeypatch)
    p._set_voice_drop_path(_wav(tmp_path))
    p._chk_fx_master.setChecked(False); p._chk_video.setChecked(True); p._spin_promo.setValue(35)
    p._branding_card._edit_artist.setText("DJ Test"); p._branding_card._edit_label.setText("Radical")
    state = p.get_state()
    q = _panel(monkeypatch)
    q.apply_state(state)
    assert not q._chk_fx_master.isChecked() and q._chk_video.isChecked() and q._spin_promo.value() == 35
    assert q._voice_drop_path == p._voice_drop_path
    assert q._branding_card._edit_artist.text() == "DJ Test" and q._branding_card._edit_label.text() == "Radical"
    # aplicar solo la firma no toca el estilo
    r = _panel(monkeypatch)
    r.apply_state({"signature": {"artist": "Solo Firma"}})
    assert r._branding_card._edit_artist.text() == "Solo Firma" and r._chk_fx_master.isChecked()
    for x in (p, q, r): x.deleteLater()


def test_preset_guardado_y_aplicado_desde_el_panel(monkeypatch):
    p = _panel(monkeypatch)
    p._chk_fx_master.setChecked(False)
    p._on_preset_save("Mi Estilo", False, True)
    assert presets.list_presets() == ["Mi Estilo"] and p._preset_bar.current_name() == "Mi Estilo"
    p._chk_fx_master.setChecked(True)
    msgs = []
    p.status_message.connect(msgs.append)
    p._on_preset_apply("Mi Estilo")
    assert not p._chk_fx_master.isChecked() and any("Mi Estilo" in m and "estilo" in m for m in msgs)
    p._on_preset_delete("Mi Estilo")
    assert presets.list_presets() == []
    p.deleteLater()


def test_edicion_basica_oculta_presets_y_promo(monkeypatch):
    p = _panel(monkeypatch, "basic")
    assert p._preset_bar.isHidden() and p._row_promo_widget.isHidden()
    assert p._promo_options()["promo_mode"] is False
    p._chk_promo.setChecked(True)                              # aunque se forzara, en Básica no se aplica
    assert p.get_export_options()["promo_mode"] is False
    p.deleteLater()


def test_titulo_del_video_elegible_por_el_autor(monkeypatch):
    p = _panel(monkeypatch)
    assert p.get_export_options()["video_title"] == ""            # vacío = nombre de la pista
    p._edit_vtitle.setText("  Midnight Groove (Radical Edit)  ")
    assert p.get_export_options()["video_title"] == "Midnight Groove (Radical Edit)"
    assert not p._row_video_title_widget.isVisibleTo(p)
    p._chk_video.setChecked(True)
    assert p._row_video_title_widget.isVisibleTo(p)               # aparece junto a las opciones del vídeo


def _export_con_titulo(tmp_path, monkeypatch, meta, nombre="PREVIA - Mi Tema Brutal"):
    import src.engine.export as E
    import src.engine.video_neon as VN
    seen = {}

    def fake_render(**kw):
        seen.update(kw)
        Path(kw["output_video_path"]).write_bytes(b"x")
    monkeypatch.setattr(VN, "render_neon_video", fake_render)
    paths = {"wav": tmp_path / f"{nombre}.wav", "video": tmp_path / f"{nombre}.mp4"}
    E.export_files(np.zeros((2, 4410), dtype="float32"), 44100, paths, metadata=meta)
    return seen


def test_titulo_del_video_por_defecto_es_el_nombre_de_la_pista(tmp_path, monkeypatch):
    """Sin título elegido, el vídeo usa el nombre del archivo sin «PREVIA - » (antes salía «Previa»)."""
    seen = _export_con_titulo(tmp_path, monkeypatch, {"video_title": ""})
    assert seen["title"] == "Mi Tema Brutal"


def test_titulo_del_video_elegido_manda(tmp_path, monkeypatch):
    seen = _export_con_titulo(tmp_path, monkeypatch, {"video_title": "Mi Título Propio", "title": "Otro"})
    assert seen["title"] == "Mi Título Propio"


def test_video_marcado_fuerza_y_bloquea_el_mp3(monkeypatch):
    """Sin previa no hay vídeo: con el vídeo marcado el MP3 se exporta siempre y no se puede desmarcar."""
    p = _panel(monkeypatch)
    p._chk_mp3.setChecked(False)
    assert p.get_export_options()["export_mp3"] is False
    p._chk_video.setChecked(True)
    o = p.get_export_options()
    assert o["export_mp3"] and p._chk_mp3.isChecked() and not p._chk_mp3.isEnabled()
    p._chk_promo.setChecked(True); p._chk_promo.setChecked(False)       # el modo promo no libera el bloqueo
    assert p._chk_mp3.isChecked() and not p._chk_mp3.isEnabled()
    p._chk_video.setChecked(False)
    assert p._chk_mp3.isEnabled()


def test_vista_previa_del_video_abre_y_cierra(tmp_path, monkeypatch):
    import src.ui.video_preview as VP
    from PIL import Image
    fr = [Image.new("RGB", (60, 100), (i * 10 % 255, 0, 0)) for i in range(6)]
    monkeypatch.setattr(VP.PreviewWorker, "run", lambda self: self.done.emit({"frames": fr, "fps": 15, "audio": ""}))
    d = VP.VideoPreviewDialog({})
    for _ in range(50):
        QApplication.processEvents()
        if d._pix:
            break
        d._worker.wait(50)
    assert len(d._pix) == 6 and d._pix[0].width() == 60
    d._tick()
    assert d._lbl_video.pixmap() is not None
    d.close()


def test_boton_vista_previa_presente(monkeypatch):
    p = _panel(monkeypatch)
    assert p._btn_vprev.text().endswith("Vista previa")
    p._source_path = ""
    p._open_video_preview()          # sin pista cargada no hace nada ni falla


def test_basic_tiene_video_con_marca_y_sin_opciones_plus(monkeypatch):
    p = _panel(monkeypatch, "basic")
    assert not p._chk_video.isHidden()                 # Basic ya puede generar vídeo
    p._chk_video.setChecked(True)
    assert p._row_video_title_widget.isVisibleTo(p) and p._lbl_vbasic.isVisibleTo(p)
    assert not p._edit_promo.isVisibleTo(p) and not p._btn_vcustom.isVisibleTo(p)
    assert p._combo_vend.isVisibleTo(p)                                    # Basic elige: firma o fundido a negro
    assert [p._combo_vend.itemData(i) for i in range(p._combo_vend.count())] == ["brand", "fade"]
    o = p.get_export_options()
    assert o["export_video"] and o["export_mp3"] and o["video_end"] == "brand" and o["video_custom"] is None
    p._set_combo_by_data(p._combo_vend, "fade")
    assert p.get_export_options()["video_end"] == "fade"


def test_plus_elige_el_final_del_video(monkeypatch):
    p = _panel(monkeypatch, "plus")
    p._chk_video.setChecked(True)
    assert p._combo_vend.isVisibleTo(p) and not p._lbl_vbasic.isVisibleTo(p)
    assert p.get_export_options()["video_end"] == "brand"
    p._set_combo_by_data(p._combo_vend, "fade")
    assert p.get_export_options()["video_end"] == "fade"


def test_export_basic_marca_de_agua_y_plus_no(tmp_path, monkeypatch):
    import src.engine.export as E
    import src.config as C
    import src.engine.video_neon as VN
    seen = {}
    monkeypatch.setattr(VN, "render_neon_video", lambda **kw: (seen.update(kw), Path(kw["output_video_path"]).write_bytes(b"x")))
    custom = {"style": "image", "bg": {"default": "x.jpg"}}
    for ed, wm, vend, end in (("basic", True, "fade", "fade"), ("basic", True, "none", "brand"),
                              ("basic", True, "image", "brand"), ("plus", False, "fade", "fade"),
                              ("plus", False, "image", "image")):
        seen.clear()
        monkeypatch.setattr(C, "get_edition", lambda ed=ed: ed)
        paths = {"wav": tmp_path / f"PREVIA - X{ed}{vend}.wav", "video": tmp_path / f"PREVIA - X{ed}{vend}.mp4"}
        E.export_files(np.zeros((2, 4410), dtype="float32"), 44100, paths,
                       metadata={"video_end": vend, "video_promo_text": "BANNER", "video_custom": custom})
        assert seen["watermark"] is wm and seen["end_mode"] == end
        assert (seen["promo_text"] == "") == (ed == "basic")           # Basic no pone banner propio
        assert (seen["custom"] is None) == (ed == "basic")             # ni imagen propia


def _cerrar(*widgets):
    """Destruye los diálogos del test antes de que Qt se cierre (evita abortos al salir del intérprete)."""
    for w in widgets:
        w.close()
        w.deleteLater()
    QApplication.sendPostedEvents(None, 0)
    QApplication.processEvents()


def test_plus_ajustes_de_video_y_final_con_imagen(monkeypatch, tmp_path):
    from src.engine.video_neon import normalize_custom
    p = _panel(monkeypatch, "plus")
    p._chk_video.setChecked(True)
    assert p._btn_vcustom.isVisibleTo(p)
    assert [p._combo_vend.itemData(i) for i in range(p._combo_vend.count())] == ["brand", "fade", "none", "image"]
    img = tmp_path / "a.png"; Image.new("RGB", (64, 64), (200, 30, 30)).save(img)
    p._video_custom = normalize_custom({"style": "image", "bg": {"default": str(img)}, "wave_style": "circle",
                                        "wave_pos": "center", "end_image": str(img)})
    p._set_combo_by_data(p._combo_vend, "image")
    o = p.get_export_options()
    assert o["video_end"] == "image" and o["video_custom"]["wave_style"] == "circle" and o["video_custom"]["bg"]["default"] == str(img)


def test_dialogo_ajustes_de_video(monkeypatch, tmp_path):
    from PySide6.QtWidgets import QApplication
    from src.ui.video_custom import VideoCustomDialog
    QApplication.instance() or QApplication([])
    img = tmp_path / "a.png"; Image.new("RGB", (64, 64)).save(img)
    d = VideoCustomDialog({"style": "image", "bg": {"16:9": str(img)}, "wave_style": "line", "texts_pos": "bottom"})
    assert d._style.currentData() == "image" and d._wave_style.currentData() == "line" and d._bg["16:9"].path() == str(img)
    d._wave.setChecked(False)
    assert not d._wave_style.isEnabled()
    d._accept()
    r = d.result_custom()
    assert r["wave"] is False and r["texts_pos"] == "bottom" and r["bg"] == {"16:9": str(img)}
    _cerrar(d)


def test_dialogo_avisa_del_formato_y_muestra_ejemplos(monkeypatch, tmp_path):
    from PySide6.QtWidgets import QApplication, QFileDialog
    import src.ui.video_custom as VC
    QApplication.instance() or QApplication([])
    ok = tmp_path / "ok.png"; Image.new("RGB", (1080, 1920)).save(ok)
    mal = tmp_path / "mal.png"; Image.new("RGB", (1600, 1200)).save(mal)
    d = VC.VideoCustomDialog({"style": "image"})
    pk = d._bg["9:16"]
    # imagen correcta: se acepta sin preguntar
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(ok), "")))
    monkeypatch.setattr(VC, "ask_format_mismatch", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía avisar")))
    pk._pick()
    assert pk.path() == str(ok) and pk._status.text().startswith("✓")
    # imagen 4:3 para 9:16: avisa; «cambiar» no la guarda (y vuelve a abrir el selector); «usarla igualmente» sí
    asked = []
    answers = iter(["change", "continue"])
    monkeypatch.setattr(VC, "ask_format_mismatch", lambda parent, rows, asp="": (asked.append((rows, asp)), next(answers))[1])
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(mal), "")))
    pk.set_path("")
    pk._pick()
    assert len(asked) == 2 and asked[0][0][0][2] == "4:3" and asked[0][1] == "9:16"
    assert pk.path() == str(mal) and pk._status.text().startswith("⚠")
    # imagen general: acepta cualquiera de los tres formatos sin avisar; una 4:3 sí avisa
    g = d._bg["default"]
    monkeypatch.setattr(VC, "ask_format_mismatch", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debía avisar")))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(ok), "")))
    g._pick()
    assert g.path() == str(ok)
    ej = VC.FormatExamplesDialog(None, "16:9")
    _cerrar(ej, d)


def test_dialogo_solo_la_foto_y_textos(monkeypatch, tmp_path):
    from PySide6.QtWidgets import QApplication
    from src.ui.video_custom import VideoCustomDialog
    QApplication.instance() or QApplication([])
    img = tmp_path / "a.png"; Image.new("RGB", (1080, 1920)).save(img)
    d = VideoCustomDialog({"style": "image", "bg": {"default": str(img)}})
    d._chk_title.setChecked(False)
    d._accept()
    r = d.result_custom()
    assert r["title"] is False and r["artist"] is True and r["only_photo"] is False
    d2 = VideoCustomDialog({"style": "image", "bg": {"default": str(img)}})
    d2._only.setChecked(True)
    assert not d2._wave.isEnabled() and not d2._chk_title.isEnabled()
    d2._accept()
    r2 = d2.result_custom()
    assert r2["only_photo"] and not r2["wave"] and not r2["texts"]
    _cerrar(d, d2)


def test_exportar_avisa_si_la_imagen_no_tiene_el_formato(monkeypatch, tmp_path):
    from src.engine.video_neon import image_format_problems
    mal = tmp_path / "mal.png"; Image.new("RGB", (1600, 1200)).save(mal)
    c = {"style": "image", "bg": {"default": str(mal)}}
    assert image_format_problems(c, "16:9") == [("fondo", str(mal), "4:3")]


def _img_file(tmp_path, name, size):
    f = tmp_path / name
    Image.new("RGB", size, (30, 90, 200)).save(f)
    return str(f)


def test_tarjeta_de_video_formato_con_botones_y_looks(monkeypatch, tmp_path):
    p = _panel(monkeypatch, "plus")
    p._chk_video.setChecked(True)
    assert p._row_video_title_widget.isVisibleTo(p) and p._row_look_widget.isVisibleTo(p) and not p._btn_vlock.isVisibleTo(p)
    # los botones de formato controlan el selector interno (y al revés)
    assert p._aspect_btns["9:16"].isChecked()
    p._aspect_btns["16:9"].click()
    assert p._combo_aspect.currentData() == "16:9" and p.get_export_options()["aspect_ratio"] == "16:9"
    p._set_combo_by_data(p._combo_aspect, "1:1")
    assert p._aspect_btns["1:1"].isChecked() and not p._aspect_btns["16:9"].isChecked()
    # look: sin imagen pide una; con imagen se aplica y el selector lo refleja
    img = _img_file(tmp_path, "sq.png", (1000, 1000))
    monkeypatch.setattr(p, "_bg_image_from_user", lambda path="": img)
    p._combo_look.setCurrentIndex(p._combo_look.findData("circle"))
    p._on_look_chosen(0)
    o = p.get_export_options()["video_custom"]
    assert o["style"] == "image" and o["wave_style"] == "circle" and o["bg"]["1:1"] == img
    assert p._combo_look.currentData() == "circle"
    p._combo_look.setCurrentIndex(p._combo_look.findData("neon")); p._on_look_chosen(0)
    assert p.get_export_options()["video_custom"]["style"] == "neon" and p._combo_look.currentData() == "neon"
    # cancelar la elección de imagen deja el look como estaba
    p._video_custom = vn_norm(None)
    monkeypatch.setattr(p, "_bg_image_from_user", lambda path="": "")
    p._combo_look.setCurrentIndex(p._combo_look.findData("photo")); p._on_look_chosen(0)
    assert p._combo_look.currentData() == "neon" and p._video_custom["style"] == "neon"


def vn_norm(c):
    from src.engine.video_neon import normalize_custom
    return normalize_custom(c)


def test_arrastrar_una_imagen_a_la_tarjeta(monkeypatch, tmp_path):
    p = _panel(monkeypatch, "plus")
    ok = _img_file(tmp_path, "h.png", (1920, 1080))
    p._on_video_image_dropped(ok)
    c = p.get_export_options()["video_custom"]
    assert p._chk_video.isChecked() and c["style"] == "image" and c["bg"] == {"16:9": ok}
    assert p._combo_aspect.currentData() == "16:9" and p._combo_look.currentData() == "bars"       # cambia al formato de la imagen
    # imagen con otra proporción: avisa y, si el usuario la quiere cambiar, no se guarda
    mal = _img_file(tmp_path, "m.png", (1600, 1200))
    import src.ui.video_custom as VC
    monkeypatch.setattr(VC, "ask_format_mismatch", lambda *a, **k: "change")
    p._video_custom = vn_norm(None)
    monkeypatch.setattr("PySide6.QtWidgets.QFileDialog.getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    p._on_video_image_dropped(mal)
    assert p._video_custom["style"] == "neon"
    monkeypatch.setattr(VC, "ask_format_mismatch", lambda *a, **k: "continue")
    p._on_video_image_dropped(mal)
    assert p._video_custom["bg"] == {"default": mal} and p._video_custom["style"] == "image"


def test_basic_ve_las_opciones_plus_bloqueadas_y_no_arrastra(monkeypatch, tmp_path):
    p = _panel(monkeypatch, "basic")
    p._chk_video.setChecked(True)
    assert p._btn_vlock.isVisibleTo(p) and not p._row_look_widget.isVisibleTo(p) and not p._lbl_vdrop.isVisibleTo(p)
    assert not p._btn_adv.isVisibleTo(p)
    shown = []
    import PySide6.QtWidgets as QW
    monkeypatch.setattr(QW.QMessageBox, "information", staticmethod(lambda *a, **k: shown.append(a)))
    p._on_video_image_dropped(_img_file(tmp_path, "x.png", (1080, 1920)))
    assert shown and p._video_custom["style"] == "neon"


def test_opciones_avanzadas_plegadas_y_se_abren_solas(monkeypatch):
    p = _panel(monkeypatch, "plus")
    assert not p._adv_fx_widget.isVisibleTo(p) and not p._branding_card.isVisibleTo(p)
    assert p._btn_adv.isVisibleTo(p) and "Opciones avanzadas" in p._btn_adv.text() and "▸" in p._btn_adv.text()
    p._btn_adv.click()
    assert p._adv_fx_widget.isVisibleTo(p) and p._branding_card.isVisibleTo(p) and "▾" in p._btn_adv.text()
    p._btn_adv.click()
    assert not p._adv_fx_widget.isVisibleTo(p)
    p._chk_promo.setChecked(True)                             # activar una opción avanzada abre la sección
    assert p._adv_fx_widget.isVisibleTo(p) and "Modo promo" in p._btn_adv.text()


def test_resumen_de_lo_que_se_va_a_crear(monkeypatch, tmp_path):
    p = _panel(monkeypatch, "plus")
    p._chk_wav.setChecked(True); p._chk_mp3.setChecked(True); p._chk_flac.setChecked(False)
    p._update_summary()
    t = p._lbl_summary.text()
    assert "WAV 24b" in t and "MP3 320k" in t and "vídeo" not in t and "📁" in t
    p._chk_video.setChecked(True); p._set_combo_by_data(p._combo_aspect, "1:1")
    p._video_custom = vn_norm({"style": "image", "bg": {"default": _img_file(tmp_path, "a.png", (500, 500))}, "wave_style": "circle", "wave_pos": "center"})
    p._sync_look_combo()
    p._chk_fx_master.setChecked(True)
    p._update_summary()
    t = p._lbl_summary.text()
    assert "🎬 vídeo 1:1 (tu imagen + círculo" in t and "Master LUFS" in t
    pb = _panel(monkeypatch, "basic")
    pb._chk_video.setChecked(True); pb._update_summary()
    assert "marca de agua" in pb._lbl_summary.text() and "WAV" not in pb._lbl_summary.text()


def test_dialogo_con_vista_previa_en_vivo(monkeypatch, tmp_path):
    import time
    import src.ui.video_custom as VC
    img = _img_file(tmp_path, "a.png", (1080, 1920))
    d = VC.VideoCustomDialog({"style": "image", "bg": {"default": img}}, sample={"title": "Mi tema", "aspect": "9:16"})
    d.show()
    t0 = time.time()
    while time.time() - t0 < 20:
        QApplication.processEvents(); time.sleep(0.05)
        pm = d._prev_lbl.pixmap()
        if pm is not None and not pm.isNull():
            break
    assert d._prev_lbl.pixmap() is not None and not d._prev_lbl.pixmap().isNull()
    d._set_prev_aspect("16:9")                                # cambiar el formato de la muestra también redibuja
    assert d._prev_btns["16:9"].isChecked() and not d._prev_btns["9:16"].isChecked()
    _cerrar(d)


def test_ajuste_de_rendimiento_en_la_ventana_de_licencia(monkeypatch):
    import src.perf as perf
    from src.ui.about import LicenseDialog
    monkeypatch.setattr(perf, "_MODE", None)
    d = LicenseDialog("9.9.9", "plus")
    assert [d._combo_perf.itemData(i) for i in range(d._combo_perf.count())] == ["auto", "low", "high"]
    assert d._combo_perf.currentData() == "auto" and "núcleos" in d._lbl_perf.text()
    d._combo_perf.setCurrentIndex(d._combo_perf.findData("low"))
    assert perf.get_mode() == "low"
    perf._MODE = None
    assert perf.get_mode() == "low"                                   # se guarda en la configuración
    perf._MODE = None
    _cerrar(d)


def test_el_pulso_del_cursor_de_la_onda_solo_corre_cuando_se_mueve():
    from src.ui import waveform as WF
    if not WF.HAS_PYQTGRAPH:
        pytest.skip("sin pyqtgraph")
    w = WF.WaveformWidget()
    w.show()
    assert not w._glow_timer.isActive()                                # en reposo no repinta
    w._duration = 100.0
    w.set_playhead(10.0)
    assert w._glow_timer.isActive()                                    # al moverse el cursor, sí
    w._glow_last_move -= 5.0                                           # sin movimiento durante un rato
    w._tick_playhead_glow()
    assert not w._glow_timer.isActive()
    _cerrar(w)
