"""Captura de pantallas REALES de AutoPrevias para los manuales (Basic / Plus).

Uso:  python scripts/manual/capture.py basic|plus  [carpeta_salida]

Abre la aplicación real en modo offscreen (sin ventana visible), con un HOME
aislado y una pista sintética, y guarda PNG en la carpeta de salida:
  - capturas completas y recortes por zona
  - versiones anotadas con marcadores numerados (los números se explican en el manual)
No contiene ni usa claves de licencia reales: los diálogos se muestran vacíos.
"""
from __future__ import annotations
import json, os, sys, tempfile, time
from pathlib import Path

EDITION = (sys.argv[1] if len(sys.argv) > 1 else "plus").lower()
assert EDITION in ("basic", "plus")
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs" / "manual" / "_work" / EDITION
OUT.mkdir(parents=True, exist_ok=True)

HOME = Path(tempfile.mkdtemp(prefix="ap_manual_home_"))
os.environ.update(QT_QPA_PLATFORM="offscreen", HOME=str(HOME), XDG_CONFIG_HOME=str(HOME / ".config"),
                  XDG_CACHE_HOME=str(HOME / ".cache"), APPDATA=str(HOME / ".config"),
                  USERPROFILE=str(HOME), QT_SCALE_FACTOR="1.6")
sys.path.insert(0, str(ROOT))

import numpy as np, soundfile as sf
from PySide6.QtCore import Qt, QPoint, QRect, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QBrush
from PySide6.QtWidgets import QApplication

TRACK_NAME = "Midnight Groove (Original Mix).wav"


def make_track(path: Path, sec=150, bpm=128, sr=44100):
    """Pista sintética con estructura (intro, subida, drop, descanso, drop, outro)."""
    rng = np.random.default_rng(7)
    t = np.linspace(0, sec, int(sr * sec), endpoint=False)
    beat = 60.0 / bpm
    # (inicio, fin, kick, bajo, hats, pad)
    secs = [(0, 20, .5, 0, .0, .10), (20, 40, .6, .0, .3, .16), (40, 80, 1.0, .5, .6, .14),
            (80, 100, 0, 0, .15, .30), (100, 130, 1.0, .5, .6, .14), (130, 150, .5, 0, .2, .08)]
    y = np.zeros_like(t)
    for (a, b, kick, bass, hats, pad) in secs:
        m = (t >= a) & (t < b)
        env = np.ones(m.sum())
        if (a, b) == (20, 40):                    # subida progresiva
            env = np.linspace(.4, 1.3, m.sum())
        y[m] += pad * env * (np.sin(2 * np.pi * 220 * t[m]) + .6 * np.sin(2 * np.pi * 330 * t[m]))
        if bass:
            y[m] += bass * .45 * np.sin(2 * np.pi * 55 * t[m]) * (0.6 + 0.4 * np.sin(2 * np.pi * (bpm / 60) * t[m]))
    for k in range(int(sec / beat)):
        tk0 = k * beat
        sec_k = next(s_ for s_ in secs if s_[0] <= tk0 < s_[1])
        i = int(tk0 * sr); n = int(0.12 * sr)
        if i + n >= len(y):
            break
        tk = np.linspace(0, 0.12, n)
        if sec_k[2]:
            y[i:i + n] += sec_k[2] * 0.7 * np.sin(2 * np.pi * (60 + 90 * np.exp(-tk * 40)) * tk) * np.exp(-tk * 22)
        if sec_k[4] and k % 2 == 1:
            y[i:i + n] += sec_k[4] * 0.25 * rng.standard_normal(n) * np.exp(-tk * 55)
    y /= max(1e-9, np.abs(y).max()) / 0.9
    sf.write(str(path), np.stack([y, y * 0.97], 1), sr, subtype="PCM_16")


def make_tag(path: Path, sr=44100):
    t = np.linspace(0, 1.6, int(sr * 1.6), endpoint=False)
    y = 0.4 * np.sin(2 * np.pi * 440 * t) * np.exp(-t * 2.2)
    sf.write(str(path), np.stack([y, y], 1), sr, subtype="PCM_16")


app = QApplication.instance() or QApplication(sys.argv)
track = HOME / TRACK_NAME
make_track(track)
tag = HOME / "Firma Radical Records.wav"
make_tag(tag)
(HOME / "Music" / "Previas").mkdir(parents=True, exist_ok=True)

import src.config as C
cfg = C.load()
cfg["edition"] = EDITION
cfg["output_dir"] = str(HOME / "Music" / "Previas")
C.save(cfg)
from src import i18n
i18n.set_language("es")

import src.ui.app as A
from src.__version__ import __version__

W, H = 1400, (1180 if EDITION == "plus" else 1010)
w = A.MainWindow(); w.resize(W, H); w.show()


def pump(n=20, delay=0.0):
    for _ in range(n):
        app.processEvents()
        if delay:
            time.sleep(delay)


pump(30)
S = app.primaryScreen().devicePixelRatio() if False else 1.0


def grab(widget) -> QImage:
    pump(10)
    img = widget.grab().toImage()
    img.setDevicePixelRatio(1.0)   # trabajamos en píxeles físicos
    return img


def rect_of(widget, root) -> QRect:
    p = widget.mapTo(root, QPoint(0, 0))
    return QRect(p, widget.size())


def annotate(img: QImage, items, dpr: float, name: str):
    """items = [(QRect lógico, número)] → dibuja marco y círculo numerado."""
    out = img.copy()
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    for rect, num in items:
        r = QRect(int(rect.x() * dpr), int(rect.y() * dpr), int(rect.width() * dpr), int(rect.height() * dpr))
        pen = QPen(QColor("#ffcc00")); pen.setWidth(max(2, int(2 * dpr)))
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(-3, -3, 3, 3), 6, 6)
        d = int(26 * dpr / 1.6 * 1.25)
        c = QRect(r.x() - d // 2 - 3, r.y() - d // 2 - 3, d, d)
        p.setPen(QPen(QColor("#ffffff"), 2)); p.setBrush(QBrush(QColor("#e11d2e")))
        p.drawEllipse(c)
        f = QFont("Inter"); f.setBold(True); f.setPixelSize(int(d * 0.58)); p.setFont(f)
        p.drawText(c, Qt.AlignCenter, str(num))
    p.end()
    out.save(str(OUT / f"{name}.png"))


def annotate_crop(img: QImage, region: QRect, items, dpr: float, name: str, pad: int = 6):
    tmp = OUT / "_tmp_annot.png"
    annotate(img, items, dpr, "_tmp_annot")
    full = QImage(str(tmp)); tmp.unlink()
    crop(full, region, dpr, pad).save(str(OUT / f"{name}.png")); print("captura:", name)


def save(img: QImage, name: str):
    img.save(str(OUT / f"{name}.png")); print("captura:", name)


def crop(img: QImage, rect: QRect, dpr: float, pad: int = 8) -> QImage:
    r = QRect(int((rect.x() - pad) * dpr), int((rect.y() - pad) * dpr),
              int((rect.width() + 2 * pad) * dpr), int((rect.height() + 2 * pad) * dpr))
    return img.copy(r.intersected(img.rect()))


def dpr_of(img: QImage) -> float:
    return img.width() / W


meta = {"edition": EDITION, "version": __version__, "track": TRACK_NAME, "window": [W, H]}

# ── 1. Pantalla de bienvenida ──────────────────────────────────────────────
w.resize(W, 820); pump(20)
img = grab(w); d = dpr_of(img)
save(img, "01_bienvenida")
items = [(rect_of(w._drop_zone._btn_open, w), 1)]
if EDITION == "plus":
    items += [(rect_of(w._btn_recents, w), 2), (rect_of(w._btn_batch_hdr, w), 3),
              (rect_of(w._btn_watch, w), 4), (rect_of(w._btn_license, w), 5), (rect_of(w._btn_lang, w), 6)]
else:
    items += [(rect_of(w._btn_recents, w), 2), (rect_of(w._btn_license, w), 3), (rect_of(w._btn_lang, w), 4)]
items.append((rect_of(w._edition_badge, w), len(items) + 1))
annotate(img, items, d, "01_bienvenida_anot")
meta["welcome_items"] = [n for _, n in items]

# ── 2. Análisis en curso ──────────────────────────────────────────────────
w._stack.setCurrentIndex(1)
w._analysis_page.start(TRACK_NAME)
w._analysis_page.update_progress(58, "Detectando secciones y drops…")
pump(30, 0.02)
save(grab(w), "02_analisis")

# ── 3. Pista cargada ──────────────────────────────────────────────────────
w._stack.setCurrentIndex(0)
w.resize(W, H); pump(10)
w._load_file(str(track))
t0 = time.time()
while time.time() - t0 < 180:
    pump(1, 0.05)
    if getattr(w._results, "_plan", None) is not None:
        break
pump(60, 0.02)
R = w._results
R._waveform.parentWidget().setMaximumHeight(300)
R._waveform.setMaximumHeight(230)   # onda compacta, como en una ventana normal
pump(20)
img = grab(w); d = dpr_of(img)
save(img, "03_cargada")

items = [(rect_of(R._waveform, w), 1), (rect_of(R._player, w), 2), (rect_of(R._card_bpm, w), 3),
         (rect_of(R._btn_p120, w), 4), (rect_of(R._edit_name, w), 5), (rect_of(R._btn_folder, w), 6),
         (rect_of(R._btn_generate, w), 7)]
if EDITION == "plus":
    items = [(rect_of(R._waveform, w), 1), (rect_of(R._player, w), 2), (rect_of(R._card_bpm, w), 3),
             (rect_of(R._btn_p120, w), 4), (rect_of(R._preset_bar, w), 5), (rect_of(R._chk_advanced, w), 6),
             (rect_of(R._edit_name, w), 7), (rect_of(R._chk_fx_flanger, w), 8), (rect_of(R._btn_voice_drop, w), 9),
             (rect_of(R._chk_promo, w), 10), (rect_of(R._branding_card, w), 11), (rect_of(R._btn_generate, w), 12)]
annotate(img, items, d, "03_cargada_anot")
meta["loaded_items"] = [n for _, n in items]

# recortes por zona
zones = {
    "z_waveform": R._waveform, "z_player": R._player,
    "z_stats": R._card_file.parentWidget() if False else None,
    "z_presets": R._btn_p15.parentWidget(), "z_export": R._edit_name.parentWidget(),
}
for nm, wd in zones.items():
    if wd is None:
        continue
    save(crop(img, rect_of(wd, w), d, 4), nm)
stats_rect = rect_of(R._card_file, w).united(rect_of(R._card_pv, w))
save(crop(img, stats_rect, d, 4), "z_stats")
if EDITION == "plus":
    save(crop(img, rect_of(R._branding_card, w), d, 4), "z_firma")

# ── 4. Editor avanzado (Plus) ─────────────────────────────────────────────
w.resize(W, 1300 if EDITION == "plus" else H); pump(20)   # ventana alta: se ve el panel completo sin scroll
if EDITION == "plus":
    R._chk_advanced.setChecked(True); pump(30, 0.02)
    for idx, nm in enumerate(("04_editor_cortes", "05_editor_bpm", "06_estructura")):
        R._tabs.setCurrentIndex(idx); pump(30, 0.02)
        im = grab(w); save(im, nm)
        tabs_r = rect_of(R._tabs, w)
        save(crop(im, tabs_r, dpr_of(im), 4), "z_" + nm)
        if idx == 0:
            annotate_crop(im, tabs_r, [(rect_of(R._btn_add_cut, w), 1), (rect_of(R._tbl_cuts, w), 2),
                                       (rect_of(R._lbl_cuts_summary, w), 3)], dpr_of(im), "z_04_editor_cortes_anot")
        if idx == 1:
            annotate_crop(im, tabs_r, [(rect_of(R._btn_mode_auto, w), 1), (rect_of(R._btn_mode_manual, w), 2),
                                       (rect_of(R._tempo_plot_frame, w), 3)], dpr_of(im), "z_05_editor_bpm_anot")
    R._chk_advanced.setChecked(False); pump(20)

    # ── 5. Modo promo + Voice Drop ───────────────────────────────────────
    R._set_voice_drop_path(str(tag)); pump(20)
    R._chk_promo.setChecked(True); pump(30, 0.02)
    im = grab(w); d = dpr_of(im)
    save(im, "07_promo")
    export_r = rect_of(R._edit_name.parentWidget(), w)
    save(crop(im, export_r, d, 4), "z_export_promo")
    annotate(crop(im, export_r, d, 4), [], d, "z_export_promo_anot")
    R._chk_promo.setChecked(False); pump(10)

    # ── 6. Presets guardados ──────────────────────────────────────────────
    R._on_preset_save("Radical Main", True, True); pump(20)
    R._on_preset_save("Set de Verano", True, True); pump(20)
    im = grab(w)
    save(crop(im, rect_of(R._btn_p15.parentWidget(), w), dpr_of(im), 4), "z_presets_guardados")

# ── 7. Generar una previa real (MP3, y WAV en Plus) ───────────────────────
R._chk_fx_master.setChecked(EDITION == "plus")
w._generate()
t0 = time.time()
while time.time() - t0 < 240:
    pump(1, 0.05)
    if R._card_export_success.isVisible():
        break
pump(40, 0.02)
from PySide6.QtWidgets import QLabel
for _l in R._card_export_success.findChildren(QLabel):
    if str(HOME) in _l.text():
        _l.setText(_l.text().replace(str(HOME) + "/Music/Previas", "~/Música/Previas"))
w._progress_label.setText("✅ Guardado en: ~/Música/Previas · PREVIA - Midnight Groove (Original Mix).mp3")
im = grab(w); d = dpr_of(im)
save(im, "08_generada")
if R._card_export_success.isVisible():
    sr = rect_of(R._card_export_success, w)
    save(crop(im, sr, d, 6), "z_exito")
    annotate(im, [(sr, 1), (rect_of(R._btn_succ_open, w), 2), (rect_of(R._btn_succ_new, w), 3)], d, "08_generada_anot")
else:
    print("AVISO: no apareció la tarjeta de éxito")
meta["generated"] = [p.name for p in (HOME / "Music" / "Previas").glob("*")]

# ── 8. Diálogos ───────────────────────────────────────────────────────────
from src import history
import src.licensing.license as L
from src.ui.about import LicenseDialog
from src.ui.activate import ActivationDialog
from src.ui.update_dialog import UpdateDialog
from src.updater_core import ReleaseInfo

C._get_baked_edition = lambda: EDITION
for t, sec, promo in (("Midnight Groove (Original Mix)", 120, False), ("Sunset Drive (Club Mix)", 60, EDITION == "plus"),
                      ("Neon Nights (Extended)", 30, False)):
    history.add_entry(str(track), [str(HOME / "Music" / "Previas" / f"PREVIA - {t}.mp3")], seed=42, bpm=128,
                      key="11B · A", duration_sec=sec, settings={}, promo=promo)


def dlg_shot(dlg, name):
    dlg.show(); pump(30, 0.01)
    dlg.grab().save(str(OUT / f"{name}.png")); print("captura:", name); dlg.close()


dlg_shot(ActivationDialog(), "10_activacion")
L.save_local("DEMO", EDITION)                               # solo para dibujar el diálogo
dlg_shot(LicenseDialog(__version__, EDITION), "11_licencia")
L.clear_local()
info = ReleaseInfo(version="9.9.9", notes="• Mejoras de rendimiento\n• Nuevas funciones",
                   assets={"AutoPrevias-Plus-macOS.dmg": "https://example.invalid/x.dmg",
                           "AutoPrevias-Basic-macOS.dmg": "https://example.invalid/x.dmg",
                           "AutoPrevias-Plus-Windows.exe": "https://example.invalid/x.exe",
                           "AutoPrevias-Basic-Windows.exe": "https://example.invalid/x.exe"})
try:
    dlg_shot(UpdateDialog(info, __version__, EDITION), "12_actualizacion")
except Exception as e:
    print("update dialog:", e)
from src.ui.history_dialog import HistoryDialog
dlg_shot(HistoryDialog(plus=EDITION == "plus"), "13_recientes")
if EDITION == "plus":
    from src.ui.batch import BatchDialog
    from src.ui.presets_bar import SavePresetDialog
    dlg_shot(BatchDialog(initial_files=[str(track)]), "14_lote")
    dlg_shot(SavePresetDialog(["Radical Main", "Set de Verano"], "Radical Main"), "15_guardar_preset")

(OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print("OK", EDITION, "→", OUT)
os._exit(0)
