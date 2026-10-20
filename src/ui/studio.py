"""
AutoPrevias v5 — Modo Estudio: todo en una sola vista, como un editor profesional pero sencillo.

Arriba el reproductor con los datos y «Deshacer / Rehacer»; a la izquierda un menú de herramientas (Cortes, Efectos, Tempo,
Firma, Vídeo, Presets); en el centro la onda con sus carriles de cortes y efectos y, debajo, el panel de la herramienta
elegida; abajo los formatos, el nombre y GENERAR.

No duplica nada: al entrar, `StudioView.enter()` traslada a esta vista los widgets reales del asistente (reproductor, onda,
pestañas, casillas…) y al salir `leave()` los devuelve exactamente a su sitio.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

from src.i18n import tr
from src.ui import theme5 as T


def find_slot(w):
    """(layout, índice) donde está un widget dentro del layout de su padre (buscando en layouts anidados)."""
    p = w.parentWidget()
    if p is None or p.layout() is None:
        return None, -1

    def walk(lay):
        for i in range(lay.count()):
            it = lay.itemAt(i)
            if it.widget() is w:
                return lay, i
            sub = it.layout()
            if sub is not None:
                r = walk(sub)
                if r[0] is not None:
                    return r
        return None, -1
    return walk(p.layout())


def _chip_check_css() -> str:
    return (f"QCheckBox {{ color: {T.TEXT_MID}; font-size: 12px; font-weight: 800; spacing: 6px; padding: 6px 14px;"
            f" background: {T.CARD}; border: 1px solid {T.BORDER}; border-radius: 16px; }}"
            f"QCheckBox:checked {{ color: {T.TEXT}; border: 1px solid {T.ACCENT}; background: {T.ACCENT_DIM}; }}"
            "QCheckBox::indicator { width: 0; height: 0; }"
            f"QCheckBox:disabled {{ color: {T.TEXT_DIM}; }}")


TOOLS = (
    ("cortes", "✂", "Cortes", False),
    ("efectos", "🎛", "Efectos", True),
    ("tempo", "⚡", "Tempo", True),
    ("firma", "🏷", "Firma", True),
    ("video", "🎬", "Vídeo", False),
    ("presets", "💾", "Presets", True),
)


class StudioView(QWidget):
    def __init__(self, R):
        super().__init__()
        self.R = R
        self._docked: list = []
        self._tool = "cortes"
        self.setStyleSheet("background: transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 0, 4, 0)
        root.setSpacing(12)

        # — barra superior: reproductor + datos + deshacer/rehacer —
        top = T.card(16)
        tv = QVBoxLayout(top)
        tv.setContentsMargins(14, 10, 14, 10)
        tv.setSpacing(6)
        self.l_player = QVBoxLayout()
        self.l_player.setContentsMargins(0, 0, 0, 0)
        tv.addLayout(self.l_player)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.chip_dur, self.chip_bpm, self.chip_key = T.chip("—"), T.chip("— BPM"), T.chip("—")
        for c in (self.chip_dur, self.chip_bpm, self.chip_key):
            row.addWidget(c)
        row.addStretch()
        self.btn_undo = QPushButton("↶  Deshacer")
        self.btn_redo = QPushButton("↷  Rehacer")
        for b in (self.btn_undo, self.btn_redo):
            b.setFixedHeight(30)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(T.ghost_css(8, 11.5))
        self.btn_undo.clicked.connect(lambda _=False: R.undo())
        self.btn_redo.clicked.connect(lambda _=False: R.redo())
        self.btn_quick_cut = QPushButton("✂  + Corte")
        self.btn_quick_cut.setFixedHeight(30)
        self.btn_quick_cut.setCursor(Qt.PointingHandCursor)
        self.btn_quick_cut.setStyleSheet(T.ghost_css(8, 11.5))
        self.btn_quick_cut.setToolTip("Añade un corte de 16 s donde está el cursor de reproducción (o en el primer hueco libre). "
                                      "Luego arrástralo y estíralo en la onda.")
        self.btn_quick_cut.clicked.connect(lambda _=False: R.quick_add_cut())
        row.addWidget(self.btn_quick_cut)
        row.addWidget(self.btn_undo)
        row.addWidget(self.btn_redo)
        self.lbl_prev = QLabel("")
        self.lbl_prev.setStyleSheet(f"color: {T.TEXT_MID}; font-size: 12px; font-weight: 700; background: transparent; border: none;")
        row.addWidget(self.lbl_prev)
        self.btn_exit = QPushButton("Salir del Estudio")
        self.btn_exit.setFixedHeight(30)
        self.btn_exit.setCursor(Qt.PointingHandCursor)
        self.btn_exit.setStyleSheet(T.ghost_css(8, 11.5))
        self.btn_exit.clicked.connect(lambda _=False: R.set_studio(False))
        row.addWidget(self.btn_exit)
        tv.addLayout(row)
        root.addWidget(top)

        # — centro: menú de herramientas + onda + panel —
        mid = QHBoxLayout()
        mid.setSpacing(12)
        side = T.card(16, name="side5")
        sv = QVBoxLayout(side)
        sv.setContentsMargins(8, 10, 8, 10)
        sv.setSpacing(6)
        self.side_btns: dict[str, QPushButton] = {}
        plus = R._studio_plus
        for key, icon, name, plus_only in TOOLS:
            if plus_only and not plus:
                continue
            b = QPushButton(f"{icon}\n{tr(name)}")
            b.setCheckable(True)
            b.setFixedSize(78, 62)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(f"QPushButton {{ background: transparent; color: {T.TEXT_MID}; border: 1px solid transparent; border-radius: 12px;"
                            " font-size: 11px; font-weight: 700; }"
                            f"QPushButton:hover {{ color: {T.TEXT}; background: {T.CARD}; }}"
                            f"QPushButton:checked {{ color: {T.TEXT}; background: {T.ACCENT_DIM}; border: 1px solid {T.ACCENT}; }}")
            b.clicked.connect(lambda _=False, k=key: self.show_tool(k))
            sv.addWidget(b)
            self.side_btns[key] = b
        sv.addStretch()
        mid.addWidget(side, 0)
        cv = QVBoxLayout()
        cv.setSpacing(12)
        self.l_wave = QVBoxLayout()
        self.l_wave.setContentsMargins(0, 0, 0, 0)
        wf_card = T.card(16)
        wv = QVBoxLayout(wf_card)
        wv.setContentsMargins(12, 10, 12, 10)
        wv.addLayout(self.l_wave)
        cv.addWidget(wf_card)
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        self.pages: dict[str, QVBoxLayout] = {}
        for key in ("tabs", "efectos", "firma", "video", "presets"):
            pg = QWidget()
            pg.setStyleSheet("background: transparent;")
            pl = QVBoxLayout(pg)
            pl.setContentsMargins(0, 0, 0, 0)
            pl.setSpacing(10)
            pl.addStretch(1)
            self.stack.addWidget(pg)
            self.pages[key] = pl
            pg._key = key
        cv.addWidget(self.stack, 1)
        mid.addLayout(cv, 1)
        root.addLayout(mid, 1)

        # — barra inferior: formatos, nombre y GENERAR —
        bar = T.card(16, accent=True, name="genbar2")
        bh = QHBoxLayout(bar)
        bh.setContentsMargins(16, 10, 16, 10)
        bh.setSpacing(10)
        self.l_formats = QHBoxLayout()
        self.l_formats.setSpacing(8)
        bh.addLayout(self.l_formats)
        self.l_name = QHBoxLayout()
        bh.addLayout(self.l_name, 1)
        self.l_gen = QHBoxLayout()
        bh.addLayout(self.l_gen)
        root.addWidget(bar)

    # ── trasladar los widgets reales ─────────────────────────────────────────
    def _widgets(self):
        R = self.R
        plus = R._studio_plus
        return [
            (R._player, self.l_player),
            (R._waveform, self.l_wave),
            (R._tabs, self.pages["tabs"]),
            (R._card_startend_simple, self.pages["efectos"]),
            (R._card_startend, self.pages["efectos"]),
            (R._adv_fx_widget, self.pages["efectos"]),
            (R._branding_card, self.pages["firma"]),
            (R._row_video_title_widget, self.pages["video"]),
            (R._preset_bar, self.pages["presets"]),
            (R._chk_mp3, self.l_formats), (R._chk_wav, self.l_formats), (R._chk_flac, self.l_formats),
            (R._chk_video, self.l_formats),
            (R._edit_name, self.l_name),
            (R._btn_generate, self.l_gen),
        ]

    def enter(self):
        R = self.R
        items = [(w, lay) for w, lay in self._widgets() if isinstance(w, QWidget)]
        slots = [(w, *find_slot(w)) for w, _ in items]               # primero se anotan TODOS los sitios de origen…
        self._docked = [s for s in slots if s[1] is not None]
        self._saved_css = {id(w): w.styleSheet() for w, _ in items}
        for w, lay in items:                                         # …y luego se mueven
            idx = lay.count() - 1 if lay in self.pages.values() else lay.count()
            lay.insertWidget(max(0, idx), w, 1 if w is R._waveform else 0)
        R._tabs.setVisible(True)
        for c in (R._chk_mp3, R._chk_wav, R._chk_flac, R._chk_video):
            c.setStyleSheet(_chip_check_css())
        R._chk_video.setText("🎬 Vídeo")
        R._edit_name.setMinimumWidth(220)
        R._btn_generate.setMinimumWidth(240)
        R._btn_generate.setFixedHeight(44)
        R._row_video_title_widget.setVisible(R._chk_video.isChecked())
        R._card_startend.setVisible(R._studio_plus)
        R._card_startend_simple.setVisible(R._studio_plus)
        R._branding_card.setVisible(True)
        self.show_tool(self._tool if self._tool in self.side_btns else "cortes")
        self.refresh()

    def leave(self):
        R = self.R
        for w, lay, idx in sorted(self._docked, key=lambda s: (id(s[1]), s[2])):
            lay.insertWidget(min(idx, lay.count()), w)
        for w, _ in self._widgets():
            if isinstance(w, QWidget) and id(w) in self._saved_css:
                w.setStyleSheet(self._saved_css[id(w)])
        R._chk_video.setText("Vídeo para redes")
        R._btn_generate.setFixedHeight(54)
        R._btn_generate.setMinimumWidth(280)
        R._edit_name.setMinimumWidth(0)
        R._card_startend_simple.setVisible(R._studio_plus)
        R._card_startend.setVisible(R._studio_plus)
        R._branding_card.setVisible(False)       # en el asistente la firma se edita con «Editar» (ventana)
        self._docked = []

    # ── interacción ─────────────────────────────────────────────────────────
    def show_tool(self, key: str):
        R = self.R
        self._tool = key
        for k, b in self.side_btns.items():
            b.setChecked(k == key)
        page = {"cortes": "tabs", "tempo": "tabs", "efectos": "efectos", "firma": "firma", "video": "video",
                "presets": "presets"}[key]
        if key == "cortes":
            R._tabs.setCurrentIndex(0)
        elif key == "tempo":
            R._tabs.setCurrentIndex(1)
        if key == "video" and not R._chk_video.isChecked():
            R._chk_video.setChecked(True)
        for i in range(self.stack.count()):
            if self.stack.widget(i)._key == page:
                self.stack.setCurrentIndex(i)
        if key == "firma":
            R._set_adv_open(True)
            R._branding_card.setVisible(True)

    def refresh(self):
        R = self.R
        v = lambda c: c._val_lbl.text()
        self.chip_dur.setText(v(R._card_dur))
        self.chip_bpm.setText(f"{v(R._card_bpm)} BPM" if v(R._card_bpm) != "—" else "— BPM")
        self.chip_key.setText(v(R._card_key).replace("  ", " · "))
        pv = v(R._card_pv)
        self.lbl_prev.setText(tr("Previa: {t}", t=pv) if pv != "—" else "")
        self.btn_undo.setEnabled(R._hist.can_undo())
        self.btn_redo.setEnabled(R._hist.can_redo())
