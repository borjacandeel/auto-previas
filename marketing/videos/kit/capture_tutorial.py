"""Capturas REALES de AutoPrevias Plus para el vídeo tutorial (estados del panel de vídeo, diálogos y vista previa).
Reutiliza la preparación de scripts/manual/capture.py (app real en offscreen, HOME aislado, pista sintética) y guarda en
docs/manual/_work/tutorial/ las capturas t*.png y meta.json con los rectángulos de cada widget (para cámara y resaltados).
Uso: python marketing/videos/kit/capture_tutorial.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.argv = ["capture.py", "plus", str(ROOT / "docs" / "manual" / "_work" / "tutorial")]
_src = (ROOT / "scripts" / "manual" / "capture.py").read_text(encoding="utf-8")
_head = _src[:_src.index("# ── 3b.")].replace("ROOT = Path(__file__).resolve().parents[2]", f"ROOT = Path({str(ROOT)!r})")
exec(compile(_head, "capture_head", "exec"), globals())

# ═════════════════════════ capturas del tutorial ═════════════════════════
import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QPushButton

PH = ROOT / "marketing" / "videos" / "stills" / "tutorial"
RECTS: dict = {}


def snap(name, stage, widgets, root=None):
    pump(40, 0.02)
    root = root or w
    save(root.grab() if root is not w else grab(w), name)
    RECTS[stage] = {k: list(rect_of(v, root).getRect()) for k, v in widgets.items()}


def find_btn(dlg, text):
    return next(b for b in dlg.findChildren(QPushButton) if text in b.text())


w.resize(W, 1560); pump(30)
R._set_adv_open(False)
R._chk_video.setChecked(False); pump(30)

# 1) formatos de salida, sin vídeo
snap("t01_sin_video", "sin_video", dict(chk_video=R._chk_video, chk_wav=R._chk_wav, chk_mp3=R._chk_mp3, chk_flac=R._chk_flac,
                                        name=R._edit_name, generate=R._btn_generate, summary=R._lbl_summary))

# 2) con vídeo: aparece la tarjeta
R._chk_video.setChecked(True); pump(40, 0.02)
VID = dict(card=R._row_video_title_widget, chk_video=R._chk_video, f916=R._aspect_btns["9:16"], f11=R._aspect_btns["1:1"],
           f169=R._aspect_btns["16:9"], pal=R._combo_video_pal, look=R._combo_look, custom=R._btn_vcustom, banner=R._edit_promo,
           vtitle=R._edit_vtitle, final=R._combo_vend, prev=R._btn_vprev, drop=R._lbl_vdrop, adv=R._btn_adv,
           summary=R._lbl_summary, generate=R._btn_generate)
snap("t02_video", "video", VID)

# 2b) con título y banner escritos
R._edit_vtitle.setText("MIDNIGHT GROOVE")
R._edit_promo.setText("RADICAL RECORDS · PROMO EXCLUSIVA")
snap("t02b_video_rellenado", "video_rellenado", VID)

# 3) arrastrar una foto 16:9 sobre la tarjeta
R._on_video_image_dropped(str(PH / "foto_16x9.jpg")); pump(40, 0.02)
snap("t03_foto", "video_foto", VID)

# 4) opciones avanzadas abiertas
R._set_adv_open(True); pump(30, 0.02)
snap("t04_avanzadas", "avanzadas", dict(adv=R._btn_adv, fx=R._adv_fx_widget, flanger=R._chk_fx_flanger, filt=R._chk_fx_filter,
                                         master=R._chk_fx_master, voice=R._btn_voice_drop, promo=R._chk_promo,
                                         branding=R._branding_card, summary=R._lbl_summary, card=R._row_video_title_widget))
R._set_adv_open(False); pump(20)

# 5) guardar el estilo como preset
R._on_preset_save("Mi estilo de vídeo", True, True); pump(30, 0.02)
snap("t05_presets", "presets", dict(bar=R._preset_bar, combo=R._preset_bar._combo, apply=R._preset_bar._btn_apply,
                                    save=R._preset_bar._btn_save, card=R._row_video_title_widget))

# 6) ventana «Personalizar…» con vista previa en vivo
from src.engine.video_neon import normalize_custom
from src.ui.video_custom import VideoCustomDialog, FormatExamplesDialog, ask_format_mismatch


def wait_preview(dlg, secs=25):
    t0 = time.time()
    last = None
    while time.time() - t0 < secs:
        pump(1, 0.05)
        pm = dlg._prev_lbl.pixmap()
        if pm is not None and not pm.isNull() and dlg._worker is not None and not dlg._worker.isRunning():
            if last is None:
                last = time.time()
            if time.time() - last > 0.6:
                break
    pump(10, 0.05)


def dlg_widgets(dlg):
    return dict(style=dlg._style, bgdef=dlg._bg["default"], bg916=dlg._bg["9:16"], bg11=dlg._bg["1:1"], bg169=dlg._bg["16:9"],
                fit=dlg._fit, only=dlg._only, wave=dlg._wave, wstyle=dlg._wave_style, wpos=dlg._wave_pos, wcol=dlg._wave_col,
                ctitle=dlg._chk_title, cartist=dlg._chk_artist, cchips=dlg._chk_chips, ckicker=dlg._chk_kicker,
                tpos=dlg._texts_pos, endimg=dlg._end_img, endtxt=dlg._end_txt, prev=dlg._prev_lbl,
                pbtn916=dlg._prev_btns["9:16"], pbtn11=dlg._prev_btns["1:1"], pbtn169=dlg._prev_btns["16:9"],
                formats=find_btn(dlg, "formatos válidos"), save=find_btn(dlg, "Guardar"))


CUST = normalize_custom({"style": "image", "bg": {"9:16": str(PH / "foto_9x16.jpg"), "1:1": str(PH / "foto_1x1.jpg"),
                                                   "16:9": str(PH / "foto_16x9.jpg")},
                         "wave_style": "circle", "wave_pos": "center", "end_image": str(PH / "foto_16x9.jpg"),
                         "end_text": "Disponible en Beatport"})
R._video_custom = CUST; R._sync_look_combo()
sample = R._video_sample()
sample["aspect"] = "16:9"
dlg = VideoCustomDialog(CUST, R, sample=sample)
dlg.show(); wait_preview(dlg)
save(dlg.grab(), "t06_personalizar"); RECTS["dlg_a"] = {k: list(rect_of(v, dlg).getRect()) for k, v in dlg_widgets(dlg).items()}
# otra combinación: onda en línea, abajo, solo título
dlg._wave_style.setCurrentIndex(dlg._wave_style.findData("line")); dlg._wave_pos.setCurrentIndex(dlg._wave_pos.findData("bottom"))
dlg._chk_artist.setChecked(False); dlg._chk_chips.setChecked(False); dlg._chk_kicker.setChecked(False)
wait_preview(dlg)
save(dlg.grab(), "t07_personalizar_b"); RECTS["dlg_b"] = {k: list(rect_of(v, dlg).getRect()) for k, v in dlg_widgets(dlg).items()}
# solo la foto
dlg._only.setChecked(True); wait_preview(dlg)
save(dlg.grab(), "t08_personalizar_solofoto"); RECTS["dlg_c"] = {k: list(rect_of(v, dlg).getRect()) for k, v in dlg_widgets(dlg).items()}
dlg.close(); pump(10)

# 7) una imagen con formato distinto (4:3) en el hueco «Cuadrado 1:1» → ⚠
CUST2 = normalize_custom({"style": "image", "bg": {"1:1": str(PH / "foto_4x3.jpg"), "16:9": str(PH / "foto_16x9.jpg")}, "fit": "crop"})
dlg = VideoCustomDialog(CUST2, R, sample=sample)
dlg.show(); wait_preview(dlg)
save(dlg.grab(), "t09_formato_mal"); RECTS["dlg_mal"] = {k: list(rect_of(v, dlg).getRect()) for k, v in dlg_widgets(dlg).items()}
dlg.close(); pump(10)

# 8) ejemplos de formatos
ex = FormatExamplesDialog(R, "16:9"); ex.show(); pump(30, 0.02)
save(ex.grab(), "t10_formatos_validos"); RECTS["formatos_validos"] = {"dlg": [0, 0, ex.width(), ex.height()]}
ex.close(); pump(10)

# 9) aviso «el formato de la imagen no es correcto» (diálogo modal)
def _grab_modal():
    m = QApplication.activeModalWidget()
    if m is not None:
        save(m.grab(), "t11_aviso_formato")
        RECTS["aviso_formato"] = {"dlg": [0, 0, m.width(), m.height()]}
        (m.defaultButton() or m.buttons()[0]).click()       # un QMessageBox sin botón de escape ignora close()


QTimer.singleShot(700, _grab_modal)
ask_format_mismatch(R, [("fondo", str(PH / "foto_4x3.jpg"), "4:3")], "16:9")
pump(10)

# guardado intermedio de los rectángulos (por si un paso lento se queda parado)
(OUT / "meta.json").write_text(json.dumps({"rects": RECTS, "window": [W, 1560]}, ensure_ascii=False, indent=2), encoding="utf-8")
print("meta parcial guardada", flush=True)
import faulthandler; faulthandler.dump_traceback_later(200, repeat=False, exit=False)

# 10) vista previa real del vídeo
R._video_custom = normalize_custom({"style": "image", "bg": {"16:9": str(PH / "foto_16x9.jpg")}}); R._sync_look_combo()
R._set_combo_by_data(R._combo_aspect, "16:9")
R._open_video_preview()
pv = R._video_preview_dlg
t0 = time.time()
while time.time() - t0 < 90 and not pv._pix:
    pump(1, 0.1)
pump(30, 0.1)
save(pv.grab(), "t12_vista_previa"); RECTS["vista_previa"] = {"dlg": [0, 0, pv.width(), pv.height()], "video": list(rect_of(pv._lbl_video, pv).getRect())}
pv.close(); pump(10)

# 11) generar de verdad (previa de 15 s) con el vídeo animado
R._btn_p15.click(); pump(60, 0.05)
w._generate()
t0 = time.time()
while time.time() - t0 < 420:
    pump(1, 0.1)
    if R._card_export_success.isVisible():
        break
pump(40, 0.05)
from PySide6.QtWidgets import QLabel
for _l in R._card_export_success.findChildren(QLabel):
    if str(HOME) in _l.text():
        _l.setText(_l.text().replace(str(HOME) + "/Music/Previas", "~/Música/Previas"))
w._progress_label.setText("✅ Guardado en: ~/Música/Previas")
snap("t13_generada", "generada", dict(success=R._card_export_success, open=R._btn_succ_open, new=R._btn_succ_new,
                                      generate=R._btn_generate, folder=R._btn_folder, card=R._row_video_title_widget))
(OUT / "meta.json").write_text(json.dumps({"rects": RECTS, "window": [W, 1560], "files": sorted(p.name for p in (HOME / "Music" / "Previas").glob("*"))},
                                          ensure_ascii=False, indent=2), encoding="utf-8")
print("OK tutorial →", OUT, sorted(p.name for p in OUT.glob("t*.png")))
os._exit(0)
