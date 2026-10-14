"""
Ajustes del vídeo propio (edición Plus): estilo (plantilla Neón o imagen propia), imagen por formato,
onda de sonido, textos, disposición y final con imagen. Avisa cuando una imagen no tiene el formato del vídeo
(9:16, 1:1 o 16:9) y muestra ejemplos. Devuelve un diccionario compatible con `src.engine.video_neon.normalize_custom`.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src.engine.video_neon import ASPECTS, describe_ratio, image_size, match_aspect, normalize_custom
from src.i18n import tr
from src.ui.dialog_style import DIALOG_QSS, GREEN, TEXT2, WARN

_IMG_FILTER = "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)"
_FORMATS = (("default", "Todos los formatos"), ("9:16", "Vertical 9:16 (TikTok / Reels / Shorts)"),
            ("1:1", "Cuadrado 1:1"), ("16:9", "Horizontal 16:9 (YouTube)"))
_EXAMPLES = (("9:16", "Vertical 9:16", "TikTok · Reels · Shorts", "1080×1920"),
             ("1:1", "Cuadrado 1:1", "Instagram · feed", "1080×1080"),
             ("16:9", "Horizontal 16:9", "YouTube · pantalla", "1920×1080"))
_MIN_SHORT_SIDE = 720


def _example_pixmap(aspect: str, box: int = 150) -> QPixmap:
    """Dibujo de ejemplo de un formato (proporción real) con la leyenda «Tu imagen»."""
    w, h = ASPECTS[aspect]
    k = box / max(w, h)
    pw, ph = max(40, int(w * k)), max(40, int(h * k))
    pm = QPixmap(box + 8, box + 8)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    x, y = (pm.width() - pw) // 2, (pm.height() - ph) // 2
    g = QLinearGradient(x, y, x + pw, y + ph)
    g.setColorAt(0, QColor("#ff1e38")); g.setColorAt(1, QColor("#7c3aed"))
    p.setBrush(g); p.setPen(QPen(QColor("#ffffff"), 2))
    p.drawRoundedRect(QRectF(x, y, pw, ph), 8, 8)
    p.setPen(QColor("#ffffff"))
    f = QFont(); f.setPointSize(10); f.setBold(True); p.setFont(f)
    p.drawText(QRectF(x, y, pw, ph), Qt.AlignCenter, tr("Tu imagen"))
    p.end()
    return pm


class FormatExamplesDialog(QDialog):
    """Muestra los tres formatos de vídeo válidos con su proporción, medida recomendada y uso típico."""

    def __init__(self, parent=None, highlight: str = ""):
        super().__init__(parent)
        self.setWindowTitle(tr("Formatos de imagen válidos"))
        self.setStyleSheet(DIALOG_QSS)
        lay = QVBoxLayout(self)
        intro = QLabel(tr("Los vídeos se generan en uno de estos tres formatos. Para que tu imagen se vea completa y sin deformarse, "
                          "usa una imagen con la misma proporción que el formato del vídeo:"))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        grid = QGridLayout()
        for col, (asp, name, use, size) in enumerate(_EXAMPLES):
            pic = QLabel()
            pic.setPixmap(_example_pixmap(asp))
            pic.setAlignment(Qt.AlignCenter)
            if asp == highlight:
                pic.setStyleSheet("border:2px solid #ff3e55; border-radius:10px;")
            t = QLabel(f"<b>{tr(name)}</b><br>{tr(use)}<br><span style='color:#8c93a4'>{tr('Medida ideal')}: {size}</span>")
            t.setAlignment(Qt.AlignCenter)
            grid.addWidget(pic, 0, col)
            grid.addWidget(t, 1, col)
        lay.addLayout(grid)
        tip = QLabel(tr("Si tu imagen tiene otra proporción (por ejemplo 4:3 o 3:2), recórtala en cualquier editor al formato que necesites, "
                        "o elige «Imagen entera con fondo desenfocado» para que no se recorte."))
        tip.setWordWrap(True)
        tip.setStyleSheet(f"color:{TEXT2}; font-size:11px;")
        lay.addWidget(tip)
        row = QHBoxLayout()
        row.addStretch()
        ok = QPushButton(tr("Entendido"))
        ok.setObjectName("primary")
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        lay.addLayout(row)


def ask_format_mismatch(parent, rows: list, aspect: str = "") -> str:
    """Avisa de que una imagen no tiene el formato del vídeo. `rows` = [(rol, ruta, proporción)].
    Devuelve «change» (cambiar la imagen) o «continue» (usarla igualmente: se recortará o se verá con fondo desenfocado)."""
    while True:
        names = {"fondo": tr("Imagen de fondo"), "final": tr("Imagen del final")}
        lines = "<br>".join(f"• {names.get(r, r)}: <b>{Path(p).name}</b> → {ratio}" for r, p, ratio in rows)
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(tr("El formato de la imagen no es correcto"))
        box.setTextFormat(Qt.RichText)
        need = f"<b>{aspect}</b>" if aspect else tr("<b>9:16</b>, <b>1:1</b> o <b>16:9</b>")
        box.setText(f"{tr('El vídeo es')} {need} {tr('y esta imagen tiene otra proporción:')}<br><br>{lines}<br><br>"
                    + tr("Cámbiala por una imagen con el formato del vídeo. Si la usas igualmente, se recortará o se verá con fondo desenfocado, "
                         "según lo que hayas elegido."))
        b_change = box.addButton(tr("Cambiar la imagen"), QMessageBox.AcceptRole)
        b_ex = box.addButton(tr("Ver ejemplos de formatos"), QMessageBox.HelpRole)
        b_cont = box.addButton(tr("Usarla igualmente"), QMessageBox.DestructiveRole)
        box.setDefaultButton(b_change)
        box.exec()
        clicked = box.clickedButton()
        if clicked is b_ex:
            FormatExamplesDialog(parent, aspect).exec()
            continue
        return "continue" if clicked is b_cont else "change"


class _ImagePicker(QWidget):
    """«Elegir…» + nombre + «✕», con el estado del formato de la imagen (✓ correcto / ⚠ no es el formato)."""

    def __init__(self, path: str = "", target: str | None = None, role: str = "fondo", parent=None):
        super().__init__(parent)
        self._role = role
        self._path = path if path and Path(path).exists() else ""
        self._target = target                  # '9:16' | '1:1' | '16:9' | None (imagen general / final: sirve a cualquier formato)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(2)
        lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self._btn = QPushButton(tr("Elegir imagen…"))
        self._btn.clicked.connect(self._pick)
        self._lbl = QLabel()
        self._lbl.setStyleSheet(f"color:{TEXT2}; font-size:11px;")
        self._clear = QPushButton(tr("Quitar"))
        self._clear.setFixedWidth(64)
        self._clear.setToolTip(tr("Quitar la imagen"))
        self._clear.clicked.connect(lambda: self.set_path(""))
        self.changed = None                 # callback opcional (la ventana lo usa para refrescar la vista previa)
        lay.addWidget(self._btn)
        lay.addWidget(self._lbl, stretch=1)
        lay.addWidget(self._clear)
        outer.addLayout(lay)
        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setStyleSheet("font-size:10.5px;")
        outer.addWidget(self._status)
        self.set_path(self._path)

    def _pick(self):
        start = str(Path(self._path).parent) if self._path else ""
        while True:
            p, _ = QFileDialog.getOpenFileName(self, tr("Elegir imagen"), start, tr(_IMG_FILTER))
            if not p:
                return
            sz = image_size(p)
            if sz is None:
                QMessageBox.warning(self, tr("Elegir imagen"), tr("No se ha podido abrir esa imagen. Prueba con un PNG o JPG."))
                continue
            m = match_aspect(*sz)
            bad = (m != self._target) if self._target else (m is None)
            if bad:
                ans = ask_format_mismatch(self, [(self._role, p, describe_ratio(*sz))], self._target or "")
                if ans == "change":
                    start = str(Path(p).parent)
                    continue
            self.set_path(p)
            return

    def set_path(self, p: str):
        self._path = p or ""
        self._lbl.setText(Path(self._path).name if self._path else tr("(ninguna)"))
        self._clear.setVisible(bool(self._path))
        self._refresh_status()
        if callable(self.changed):
            self.changed()

    def _refresh_status(self):
        if not self._path:
            self._status.setText("")
            return
        sz = image_size(self._path)
        if sz is None:
            self._status.setText("⚠ " + tr("No se puede leer la imagen"))
            self._status.setStyleSheet(f"color:{WARN}; font-size:10.5px;")
            return
        m, ratio = match_aspect(*sz), describe_ratio(*sz)
        info = f"{sz[0]}×{sz[1]} · {ratio}"
        low = min(sz) < _MIN_SHORT_SIDE
        if self._target:
            ok = (m == self._target)
            txt = (f"✓ {info} — " + tr("formato correcto")) if ok else (f"⚠ {info} — " + tr("no es {fmt}: cámbiala o se recortará", fmt=self._target))
        elif m:
            txt = f"✓ {info} — " + tr("encaja en {fmt}; en los otros formatos se recortará o se adaptará", fmt=m)
        else:
            txt = f"⚠ {info} — " + tr("no es ni 9:16, 1:1 ni 16:9: se recortará o se adaptará")
            ok = False
        good = txt.startswith("✓")
        if low:
            txt += " · " + tr("resolución baja, puede verse borrosa")
        self._status.setText(txt)
        self._status.setStyleSheet(f"color:{GREEN if good and not low else WARN}; font-size:10.5px;")

    def path(self) -> str:
        return self._path


def _combo(items, current):
    c = QComboBox()
    for label, data in items:
        c.addItem(tr(label), data)
    for i in range(c.count()):
        if c.itemData(i) == current:
            c.setCurrentIndex(i)
            break
    return c


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("color:#232733;")
    return f


def _title(text: str) -> QLabel:
    lb = QLabel(tr(text))
    lb.setStyleSheet("font-size:13px; font-weight:800; color:#ff3e55;")
    return lb


class _PreviewWorker(QThread):
    """Dibuja un fotograma de ejemplo con los ajustes actuales (en segundo plano para no congelar la ventana)."""
    done = Signal(int, object)

    def __init__(self, token: int, custom: dict, sample: dict, aspect: str, parent=None):
        super().__init__(parent)
        self._token, self._custom, self._sample, self._aspect = token, custom, sample, aspect

    def run(self):
        try:
            import numpy as np
            from src.engine import video_neon as vn
            n = 90
            rng = np.random.default_rng(3)
            shape = np.clip(np.linspace(1.0, 0.12, 44) ** 1.4 + rng.normal(0, 0.07, 44), 0.05, 1).astype(np.float32)
            bars = np.tile(shape, (n, 1))
            kick = np.zeros(n, np.float32); kick[34:40] = 0.55
            an = vn.AudioAnalysis(duration=3.0, n_frames=n, bars=bars, kick=kick, energy=np.full(n, 0.6, np.float32), drops=[])
            sm = self._sample
            r = vn._Renderer(an, sm.get("cover") or None, sm.get("title") or "Título de la pista", sm.get("artist") or "Radical Records",
                             float(sm.get("bpm") or 128.0), str(sm.get("key") or "8A · Am"), self._aspect,
                             sm.get("palette") or "crimson", sm.get("banner") or "", "PREVIA EXCLUSIVA", 1.0, custom=self._custom)
            im = r.frame(36, 1.2).convert("RGB")
            im.thumbnail((420, 420))
            qi = QImage(im.tobytes(), im.width, im.height, 3 * im.width, QImage.Format_RGB888).copy()
            self.done.emit(self._token, qi)
        except Exception as ex:                      # pragma: no cover - la vista previa nunca debe romper la ventana
            self.done.emit(self._token, str(ex))


class VideoCustomDialog(QDialog):
    """Ventana «Ajustes del vídeo» (Plus)."""

    def __init__(self, current: dict | None = None, parent=None, sample: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Ajustes del vídeo"))
        self.setStyleSheet(DIALOG_QSS)
        self.setMinimumWidth(580 if not sample else 860)
        c = normalize_custom(current)
        self._result: dict | None = None
        self._sample = sample
        self._token = 0
        self._worker: _PreviewWorker | None = None
        self._pending = False
        self._prev_aspect = (sample or {}).get("aspect") if (sample or {}).get("aspect") in ASPECTS else "9:16"

        outer = QHBoxLayout(self)
        root = QVBoxLayout()
        root.setSpacing(10)
        outer.addLayout(root, 1)

        # — estilo —
        head = QHBoxLayout()
        head.addWidget(_title("Fondo del vídeo"))
        head.addStretch()
        b_ex = QPushButton(tr("📐 Ver formatos válidos"))
        b_ex.setToolTip(tr("Ejemplos de los tres formatos de vídeo: 9:16, 1:1 y 16:9"))
        b_ex.clicked.connect(lambda: FormatExamplesDialog(self).exec())
        head.addWidget(b_ex)
        root.addLayout(head)
        self._style = _combo((("🎬 Plantilla Neón (carátula que late con el bombo)", "neon"),
                              ("🖼 Mi imagen (tu foto de fondo con zoom lento)", "image")), c["style"])
        root.addWidget(self._style)
        self._img_box = QWidget()
        form = QFormLayout(self._img_box)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignLeft)
        self._bg = {}
        for key, label in _FORMATS:
            self._bg[key] = _ImagePicker((c["bg"] or {}).get(key, ""), None if key == "default" else key)
            form.addRow(QLabel(tr(label)), self._bg[key])
        self._fit = _combo((("Recortar para rellenar la pantalla", "crop"),
                            ("Imagen entera con fondo desenfocado", "blur")), c["fit"])
        form.addRow(QLabel(tr("Si la imagen no encaja")), self._fit)
        hint = QLabel(tr("Usa una imagen con la proporción de cada formato (9:16, 1:1 o 16:9). Pon una por formato o una sola en "
                         "«Todos los formatos»: se usa la del formato elegido y, si no hay, la general."))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{TEXT2}; font-size:10.5px;")
        form.addRow(hint)
        root.addWidget(self._img_box)
        root.addWidget(_sep())

        # — qué se muestra —
        root.addWidget(_title("Qué se muestra sobre la imagen (solo con «Mi imagen»)"))
        self._only = QCheckBox(tr("Solo la foto (sin textos, onda ni banner)"))
        self._only.setChecked(c["only_photo"])
        root.addWidget(self._only)
        self._opt_box = QWidget()
        of = QFormLayout(self._opt_box)
        of.setContentsMargins(0, 0, 0, 0)
        self._wave = QCheckBox(tr("Mostrar la onda de sonido"))
        self._wave.setChecked(c["wave"])
        of.addRow(self._wave)
        self._wave_style = _combo((("Barras", "bars"), ("Línea", "line"), ("Círculo", "circle")), c["wave_style"])
        self._wave_pos = _combo((("Abajo", "bottom"), ("Centro", "center"), ("Arriba", "top")), c["wave_pos"])
        self._wave_col = _combo((("Colores de la paleta Neón", "palette"), ("Blanco", "white")), c["wave_color"])
        of.addRow(QLabel(tr("Estilo de la onda")), self._wave_style)
        of.addRow(QLabel(tr("Posición de la onda")), self._wave_pos)
        of.addRow(QLabel(tr("Color de la onda")), self._wave_col)
        self._chk_title = QCheckBox(tr("Título de la pista"))
        self._chk_artist = QCheckBox(tr("Artista"))
        self._chk_chips = QCheckBox(tr("BPM y tonalidad"))
        self._chk_kicker = QCheckBox(tr("Etiqueta «Previa exclusiva»"))
        for chk, key in ((self._chk_title, "title"), (self._chk_artist, "artist"),
                         (self._chk_chips, "chips"), (self._chk_kicker, "kicker")):
            chk.setChecked(c[key])
        grid = QGridLayout()
        grid.addWidget(self._chk_title, 0, 0); grid.addWidget(self._chk_artist, 0, 1)
        grid.addWidget(self._chk_chips, 1, 0); grid.addWidget(self._chk_kicker, 1, 1)
        wrap = QWidget(); wrap.setLayout(grid); grid.setContentsMargins(0, 0, 0, 0)
        of.addRow(QLabel(tr("Textos")), wrap)
        self._texts_pos = _combo((("Arriba", "top"), ("Centro", "center"), ("Abajo", "bottom")), c["texts_pos"])
        of.addRow(QLabel(tr("Posición de los textos")), self._texts_pos)
        root.addWidget(self._opt_box)
        root.addWidget(_sep())

        # — final con imagen —
        root.addWidget(_title("Final con tu imagen"))
        fe = QFormLayout()
        self._end_img = _ImagePicker(c["end_image"], None, "final")
        fe.addRow(QLabel(tr("Imagen del final")), self._end_img)
        self._end_txt = QLineEdit(c["end_text"])
        self._end_txt.setPlaceholderText(tr("Texto opcional bajo la imagen (p. ej. «Disponible en Beatport»)"))
        self._end_txt.setMaxLength(80)
        fe.addRow(QLabel(tr("Texto")), self._end_txt)
        root.addLayout(fe)
        hint2 = QLabel(tr("Para usarla, elige «Final: mi imagen» en el selector de final del vídeo."))
        hint2.setStyleSheet(f"color:{TEXT2}; font-size:10.5px;")
        root.addWidget(hint2)

        # — botones —
        row = QHBoxLayout()
        row.addStretch()
        b_cancel = QPushButton(tr("Cancelar"))
        b_cancel.clicked.connect(self.reject)
        b_ok = QPushButton(tr("Guardar"))
        b_ok.setObjectName("primary")
        b_ok.setDefault(True)
        b_ok.clicked.connect(self._accept)
        row.addWidget(b_cancel)
        row.addWidget(b_ok)
        root.addLayout(row)

        for sig in (self._style.currentIndexChanged, self._wave.toggled, self._only.toggled,
                    self._chk_title.toggled, self._chk_artist.toggled, self._chk_chips.toggled, self._chk_kicker.toggled,
                    self._wave_style.currentIndexChanged, self._wave_pos.currentIndexChanged, self._wave_col.currentIndexChanged,
                    self._texts_pos.currentIndexChanged, self._fit.currentIndexChanged):
            sig.connect(self._sync)
        if sample is not None:
            self._build_preview_panel(outer)
        for pk in list(self._bg.values()) + [self._end_img]:
            pk.changed = self._sync              # al cambiar una imagen se actualiza la vista previa
        self._sync()

    # — vista previa en vivo —
    def _build_preview_panel(self, outer: QHBoxLayout):
        col = QVBoxLayout()
        col.setSpacing(6)
        cap = QLabel(tr("Vista previa"))
        cap.setStyleSheet("font-size:13px; font-weight:800; color:#ff3e55;")
        col.addWidget(cap)
        self._prev_lbl = QLabel(tr("Preparando…"))
        self._prev_lbl.setAlignment(Qt.AlignCenter)
        self._prev_lbl.setFixedSize(300, 340)
        self._prev_lbl.setWordWrap(True)
        self._prev_lbl.setStyleSheet("background:#05060a; color:#8c93a4; border:1px solid #232733; border-radius:10px; font-size:11px;")
        col.addWidget(self._prev_lbl)
        row = QHBoxLayout()
        self._prev_btns = {}
        for asp in ASPECTS:
            b = QPushButton(asp)
            b.setCheckable(True)
            b.setChecked(asp == self._prev_aspect)
            b.clicked.connect(lambda _c=False, a=asp: self._set_prev_aspect(a))
            row.addWidget(b)
            self._prev_btns[asp] = b
        col.addLayout(row)
        note = QLabel(tr("Así se verá el vídeo con tus ajustes (el fotograma es de ejemplo: en el vídeo real se mueve al ritmo de tu tema)."))
        note.setWordWrap(True)
        note.setFixedWidth(300)
        note.setStyleSheet(f"color:{TEXT2}; font-size:10.5px;")
        col.addWidget(note)
        col.addStretch()
        outer.addLayout(col)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(350)
        self._debounce.timeout.connect(self._start_preview)

    def _set_prev_aspect(self, asp: str):
        self._prev_aspect = asp
        for a, b in self._prev_btns.items():
            b.setChecked(a == asp)
        self._schedule_preview()

    def _schedule_preview(self):
        if self._sample is not None and hasattr(self, "_debounce"):
            self._debounce.start()

    def _start_preview(self):
        if self._worker is not None and self._worker.isRunning():
            self._pending = True
            return
        c = self._collect()
        if c["style"] == "image" and not any(w.path() for w in self._bg.values()):
            self._prev_lbl.setPixmap(QPixmap())
            self._prev_lbl.setText(tr("Elige una imagen de fondo para ver la vista previa."))
            return
        self._token += 1
        self._worker = _PreviewWorker(self._token, c, self._sample or {}, self._prev_aspect, self)
        self._worker.done.connect(self._on_preview)
        self._worker.start()

    def _on_preview(self, token: int, result):
        if isinstance(result, QImage):
            self._prev_lbl.setText("")
            self._prev_lbl.setPixmap(QPixmap.fromImage(result).scaled(self._prev_lbl.size() - QSize(8, 8),
                                                                      Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self._prev_lbl.setText(tr("No se pudo dibujar la vista previa."))
        if self._pending:
            self._pending = False
            self._start_preview()

    def _stop_preview(self):
        if hasattr(self, "_debounce"):
            self._debounce.stop()
        w = self._worker
        if w is not None:
            try:
                w.done.disconnect()
            except Exception:
                pass
            w.wait(5000)
        self._pending = False

    def done(self, r):
        self._stop_preview()
        super().done(r)

    def _any_text(self) -> bool:
        return any(c.isChecked() for c in (self._chk_title, self._chk_artist, self._chk_chips, self._chk_kicker))

    def _sync(self, *_):
        img = self._style.currentData() == "image"
        full = img and not self._only.isChecked()
        self._img_box.setEnabled(img)
        self._only.setEnabled(img)
        self._opt_box.setEnabled(full)
        w = self._wave.isChecked()
        for x in (self._wave_style, self._wave_pos, self._wave_col):
            x.setEnabled(full and w)
        for x in (self._chk_title, self._chk_artist, self._chk_chips, self._chk_kicker):
            x.setEnabled(full)
        self._texts_pos.setEnabled(full and self._any_text())
        self._schedule_preview()

    def _accept(self):
        if self._style.currentData() == "image" and not any(w.path() for w in self._bg.values()):
            QMessageBox.information(self, tr("Ajustes del vídeo"),
                                    tr("Elige al menos una imagen de fondo, o vuelve a la plantilla Neón."))
            return
        self._result = self._collect()
        self.accept()

    def _collect(self) -> dict:
        return normalize_custom({
            "style": self._style.currentData(),
            "bg": {k: w.path() for k, w in self._bg.items()},
            "fit": self._fit.currentData(),
            "only_photo": self._only.isChecked(),
            "wave": self._wave.isChecked(),
            "wave_style": self._wave_style.currentData(),
            "wave_pos": self._wave_pos.currentData(),
            "wave_color": self._wave_col.currentData(),
            "title": self._chk_title.isChecked(),
            "artist": self._chk_artist.isChecked(),
            "chips": self._chk_chips.isChecked(),
            "kicker": self._chk_kicker.isChecked(),
            "texts_pos": self._texts_pos.currentData(),
            "end_image": self._end_img.path(),
            "end_text": self._end_txt.text(),
        })

    def result_custom(self) -> dict:
        return self._result or normalize_custom(None)
