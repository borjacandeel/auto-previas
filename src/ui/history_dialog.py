"""
AutoPrevias — Panel «Recientes»: previas generadas (con reproductor rápido, reabrir
proyecto, mostrar archivo y quitar) y pistas abiertas recientemente.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from src import i18n
from src.i18n import tr
from src.ui.dialog_style import DIALOG_QSS, GREEN, TEXT2, WARN

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    HAS_MM = True
except Exception:                                   # pragma: no cover - entorno sin QtMultimedia
    HAS_MM = False

_COLS = ["Fecha", "Pista", "Duración", "BPM", "Formatos", "Modo"]
_PLAY_ORDER = (".mp3", ".wav", ".flac", ".aiff", ".aif")


def format_summary(files: list) -> str:
    exts = []
    for f in files:
        e = Path(f).suffix.lstrip(".").upper()
        if e and e not in exts:
            exts.append(e)
    return " · ".join(exts) or "—"


def pick_playable(files: list) -> str:
    """Archivo de audio a reproducir: prioriza MP3 (ligero) y luego WAV."""
    for ext in _PLAY_ORDER:
        for f in files:
            if f.lower().endswith(ext):
                return f
    return ""


def fmt_duration(sec: float) -> str:
    sec = int(round(sec or 0))
    return f"{sec // 60}:{sec % 60:02d}" if sec else "—"


class HistoryDialog(QDialog):
    reopen_requested = Signal(dict)
    reveal_requested = Signal(str)
    open_track_requested = Signal(str)

    def __init__(self, plus: bool = True, entries: list | None = None,
                 recent_tracks: list | None = None, parent=None):
        super().__init__(parent)
        self._plus = plus
        self._player = None
        self._audio = None
        self._playing_id = ""

        self.setWindowTitle("AutoPrevias — Recientes")
        self.setModal(True)
        self.resize(820, 520)
        self.setStyleSheet(DIALOG_QSS)

        if entries is None:
            from src.history import list_entries
            entries = list_entries() if plus else []
        if recent_tracks is None:
            from src.config import get_recent_files
            recent_tracks = get_recent_files()
        self._entries = list(entries)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(10)

        self._tabs = QTabWidget()
        root.addWidget(self._tabs, stretch=1)

        # ── Pestaña 1: previas generadas ────────────────────────────────────
        tab1 = QWidget()
        l1 = QVBoxLayout(tab1)
        l1.setContentsMargins(12, 12, 12, 12)
        self._table = QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels(_COLS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 130)
        self._table.setColumnWidth(1, 270)
        self._table.setColumnWidth(2, 80)
        self._table.setColumnWidth(3, 60)
        self._table.setColumnWidth(4, 110)
        self._table.itemSelectionChanged.connect(self._update_buttons)
        self._table.itemDoubleClicked.connect(lambda _i: self._reopen())
        l1.addWidget(self._table)

        self._lbl_empty = QLabel("")
        self._lbl_empty.setAlignment(Qt.AlignCenter)
        self._lbl_empty.setWordWrap(True)
        self._lbl_empty.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        l1.addWidget(self._lbl_empty)

        row = QHBoxLayout()
        self._btn_play = QPushButton("▶ Reproducir")
        self._btn_play.clicked.connect(self._toggle_play)
        self._btn_reveal = QPushButton("📂 Mostrar archivo")
        self._btn_reveal.clicked.connect(self._reveal)
        self._btn_reopen = QPushButton("🔄 Reabrir proyecto")
        self._btn_reopen.setObjectName("primary")
        self._btn_reopen.setToolTip("Carga la pista original con los mismos ajustes y la misma seed")
        self._btn_reopen.clicked.connect(self._reopen)
        self._btn_remove = QPushButton("🗑 Quitar de la lista")
        self._btn_remove.setObjectName("danger")
        self._btn_remove.clicked.connect(self._remove)
        for b in (self._btn_play, self._btn_reveal, self._btn_reopen):
            row.addWidget(b)
        row.addStretch()
        row.addWidget(self._btn_remove)
        l1.addLayout(row)
        self._lbl_now = QLabel("")
        self._lbl_now.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
        l1.addWidget(self._lbl_now)

        # ── Pestaña 2: pistas abiertas ──────────────────────────────────────
        tab2 = QWidget()
        l2 = QVBoxLayout(tab2)
        l2.setContentsMargins(12, 12, 12, 12)
        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._open_track)
        l2.addWidget(self._list)
        self._lbl_tracks_empty = QLabel("")
        self._lbl_tracks_empty.setAlignment(Qt.AlignCenter)
        self._lbl_tracks_empty.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        l2.addWidget(self._lbl_tracks_empty)
        row2 = QHBoxLayout()
        btn_open = QPushButton("🎵 Abrir pista")
        btn_open.setObjectName("primary")
        btn_open.clicked.connect(lambda: self._open_track(self._list.currentItem()))
        self._btn_clear_tracks = QPushButton("🗑️ Borrar historial")
        self._btn_clear_tracks.setObjectName("danger")
        self._btn_clear_tracks.clicked.connect(self._clear_tracks)
        row2.addWidget(btn_open)
        row2.addStretch()
        row2.addWidget(self._btn_clear_tracks)
        l2.addLayout(row2)

        self._tabs.addTab(tab1, "Previas generadas")
        self._tabs.addTab(tab2, "Pistas abiertas")

        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

        i18n.mark_dynamic(self._lbl_empty, self._lbl_tracks_empty, self._lbl_now)
        self._fill_table()
        self._fill_tracks(recent_tracks)
        self._update_buttons()
        i18n.translate_tree(self)

    # ── Rellenado ─────────────────────────────────────────────────────────────
    def _fill_table(self):
        self._table.setRowCount(0)
        if not self._plus:
            self._lbl_empty.setText(tr("🔒 El historial de previas generadas es una función de la edición PLUS."))
            self._lbl_empty.setStyleSheet(f"color: {WARN}; font-size: 12px;")
            return
        if not self._entries:
            self._lbl_empty.setText(tr("Todavía no has generado ninguna previa. Aparecerán aquí."))
        else:
            self._lbl_empty.setText("")
        self._lbl_empty.setVisible(not self._entries or not self._plus)
        for e in self._entries:
            r = self._table.rowCount()
            self._table.insertRow(r)
            ts = (e.get("ts") or "").replace("T", "  ")[:16]
            missing = not e.get("exists", True)
            files = e.get("existing_files") if e.get("existing_files") is not None else e.get("files", [])
            title = e.get("title", "—") + (tr("  (archivo no encontrado)") if missing else "")
            cells = [ts, title, fmt_duration(e.get("duration_sec", 0)),
                     f"{e.get('bpm', 0):.0f}" if e.get("bpm") else "—",
                     format_summary(e.get("files", [])), "🛡️ Promo" if e.get("promo") else "—"]
            for c, text in enumerate(cells):
                it = QTableWidgetItem(text)
                if c == 0:
                    it.setData(Qt.UserRole, e.get("id", ""))
                if missing:
                    it.setForeground(Qt.gray)
                self._table.setItem(r, c, it)
            self._table.item(r, 0).setData(Qt.UserRole + 1, files)

    def _fill_tracks(self, tracks: list):
        self._list.clear()
        for t in tracks:
            it = QListWidgetItem(f"🎵 {Path(t).name}")
            it.setData(Qt.UserRole, t)
            it.setToolTip(t)
            self._list.addItem(it)
        self._lbl_tracks_empty.setText("" if tracks else tr("No hay archivos recientes"))
        self._lbl_tracks_empty.setVisible(not tracks)
        self._btn_clear_tracks.setEnabled(bool(tracks))

    # ── Selección y botones ───────────────────────────────────────────────────
    def _current_entry(self) -> dict | None:
        r = self._table.currentRow()
        if r < 0:
            return None
        eid = self._table.item(r, 0).data(Qt.UserRole)
        return next((e for e in self._entries if e.get("id") == eid), None)

    def _update_buttons(self):
        e = self._current_entry()
        has = e is not None
        files = (e or {}).get("existing_files") or []
        self._btn_play.setEnabled(has and bool(pick_playable(files)) and HAS_MM)
        self._btn_reveal.setEnabled(has and bool(files))
        self._btn_reopen.setEnabled(has and bool(e.get("source_exists")))
        self._btn_remove.setEnabled(has)

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _toggle_play(self):
        e = self._current_entry()
        if not e or not HAS_MM:
            return
        if self._player is not None and self._playing_id == e["id"] and \
                self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.stop()
            return
        path = pick_playable(e.get("existing_files") or [])
        if not path:
            return
        if self._player is None:
            self._player = QMediaPlayer(self)
            self._audio = QAudioOutput(self)
            self._player.setAudioOutput(self._audio)
            self._player.playbackStateChanged.connect(self._on_state)
        self._player.setSource(QUrl.fromLocalFile(path))
        self._playing_id = e["id"]
        self._player.play()
        self._lbl_now.setText(tr("▶ Reproduciendo: {name}", name=Path(path).name))

    def _on_state(self, state):
        playing = state == QMediaPlayer.PlayingState
        self._btn_play.setText(tr("⏹ Detener") if playing else tr("▶ Reproducir"))
        if not playing:
            self._lbl_now.setText("")

    def _reveal(self):
        e = self._current_entry()
        files = (e or {}).get("existing_files") or []
        if files:
            self.reveal_requested.emit(files[0])

    def _reopen(self):
        e = self._current_entry()
        if e and e.get("source_exists"):
            self._stop()
            self.reopen_requested.emit(dict(e))
            self.accept()

    def _remove(self):
        e = self._current_entry()
        if not e:
            return
        from src.history import remove_entry
        remove_entry(e["id"])
        self._entries = [x for x in self._entries if x.get("id") != e["id"]]
        self._fill_table()
        i18n.translate_tree(self)
        self._update_buttons()

    def _open_track(self, item):
        if item is None:
            return
        path = item.data(Qt.UserRole)
        if path and Path(path).exists():
            self._stop()
            self.open_track_requested.emit(path)
            self.accept()

    def _clear_tracks(self):
        from src.config import load, save
        cfg = load()
        cfg["recent_files"] = []
        save(cfg)
        self._fill_tracks([])

    def _stop(self):
        if self._player is not None:
            self._player.stop()

    def done(self, result):
        self._stop()
        super().done(result)
