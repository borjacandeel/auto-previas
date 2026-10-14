"""
Ajustes del vídeo propio (edición Plus): estilo (plantilla Neón o imagen propia), imagen por formato,
onda de sonido, disposición de textos y final con imagen. Devuelve un diccionario compatible con
`src.engine.video_neon.normalize_custom`.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src.engine.video_neon import normalize_custom
from src.i18n import tr
from src.ui.dialog_style import DIALOG_QSS, TEXT2

_IMG_FILTER = "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)"
_FORMATS = (("default", "Todos los formatos"), ("9:16", "Vertical 9:16 (TikTok / Reels / Shorts)"),
            ("1:1", "Cuadrado 1:1"), ("16:9", "Horizontal 16:9 (YouTube)"))


class _ImagePicker(QWidget):
    """Botón «Elegir…» + nombre del archivo + «✕»."""

    def __init__(self, path: str = "", parent=None):
        super().__init__(parent)
        self._path = path if path and Path(path).exists() else ""
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self._btn = QPushButton(tr("Elegir imagen…"))
        self._btn.clicked.connect(self._pick)
        self._lbl = QLabel()
        self._lbl.setStyleSheet(f"color:{TEXT2}; font-size:11px;")
        self._clear = QPushButton("✕")
        self._clear.setFixedWidth(32)
        self._clear.setToolTip(tr("Quitar la imagen"))
        self._clear.clicked.connect(lambda: self.set_path(""))
        lay.addWidget(self._btn)
        lay.addWidget(self._lbl, stretch=1)
        lay.addWidget(self._clear)
        self.set_path(self._path)

    def _pick(self):
        p, _ = QFileDialog.getOpenFileName(self, tr("Elegir imagen"), str(Path(self._path).parent) if self._path else "",
                                           tr(_IMG_FILTER))
        if p:
            self.set_path(p)

    def set_path(self, p: str):
        self._path = p or ""
        self._lbl.setText(Path(self._path).name if self._path else tr("(ninguna)"))
        self._clear.setVisible(bool(self._path))

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


class VideoCustomDialog(QDialog):
    """Ventana «Ajustes del vídeo» (Plus)."""

    def __init__(self, current: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Ajustes del vídeo"))
        self.setStyleSheet(DIALOG_QSS)
        self.setMinimumWidth(560)
        c = normalize_custom(current)
        self._result: dict | None = None

        root = QVBoxLayout(self)
        root.setSpacing(10)

        # — estilo —
        root.addWidget(_title("Fondo del vídeo"))
        self._style = _combo((("🎬 Plantilla Neón (carátula que late con el bombo)", "neon"),
                              ("🖼 Mi imagen (tu foto de fondo con zoom lento)", "image")), c["style"])
        root.addWidget(self._style)
        self._img_box = QWidget()
        form = QFormLayout(self._img_box)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignLeft)
        self._bg = {}
        for key, label in _FORMATS:
            self._bg[key] = _ImagePicker((c["bg"] or {}).get(key, ""))
            form.addRow(QLabel(tr(label)), self._bg[key])
        self._fit = _combo((("Recortar para rellenar la pantalla", "crop"),
                            ("Imagen entera con fondo desenfocado", "blur")), c["fit"])
        form.addRow(QLabel(tr("Si la imagen no encaja")), self._fit)
        hint = QLabel(tr("Pon una imagen por formato o una sola en «Todos los formatos»: se usa la del formato elegido y, si no hay, la general."))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{TEXT2}; font-size:10.5px;")
        form.addRow(hint)
        root.addWidget(self._img_box)
        root.addWidget(_sep())

        # — onda y textos —
        root.addWidget(_title("Onda de sonido y textos (solo con «Mi imagen»)"))
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
        self._texts = QCheckBox(tr("Mostrar título, artista, BPM y tonalidad"))
        self._texts.setChecked(c["texts"])
        of.addRow(self._texts)
        self._texts_pos = _combo((("Arriba", "top"), ("Centro", "center"), ("Abajo", "bottom")), c["texts_pos"])
        of.addRow(QLabel(tr("Posición de los textos")), self._texts_pos)
        root.addWidget(self._opt_box)
        root.addWidget(_sep())

        # — final con imagen —
        root.addWidget(_title("Final con tu imagen"))
        fe = QFormLayout()
        self._end_img = _ImagePicker(c["end_image"])
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

        self._style.currentIndexChanged.connect(self._sync)
        self._wave.toggled.connect(self._sync)
        self._texts.toggled.connect(self._sync)
        self._sync()

    def _sync(self, *_):
        img = self._style.currentData() == "image"
        self._img_box.setEnabled(img)
        self._opt_box.setEnabled(img)
        w = self._wave.isChecked()
        for x in (self._wave_style, self._wave_pos, self._wave_col):
            x.setEnabled(img and w)
        self._texts_pos.setEnabled(img and self._texts.isChecked())

    def _accept(self):
        if self._style.currentData() == "image" and not any(w.path() for w in self._bg.values()):
            QMessageBox.information(self, tr("Ajustes del vídeo"),
                                    tr("Elige al menos una imagen de fondo, o vuelve a la plantilla Neón."))
            return
        self._result = normalize_custom({
            "style": self._style.currentData(),
            "bg": {k: w.path() for k, w in self._bg.items()},
            "fit": self._fit.currentData(),
            "wave": self._wave.isChecked(),
            "wave_style": self._wave_style.currentData(),
            "wave_pos": self._wave_pos.currentData(),
            "wave_color": self._wave_col.currentData(),
            "texts": self._texts.isChecked(),
            "texts_pos": self._texts_pos.currentData(),
            "end_image": self._end_img.path(),
            "end_text": self._end_txt.text(),
        })
        self.accept()

    def result_custom(self) -> dict:
        return self._result or normalize_custom(None)
