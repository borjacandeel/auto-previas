"""
AutoPrevias — Ventana «Firmar tema entero» (Plus).

Arrastras el tema (o varios) y solo se le mete la carátula y las etiquetas: sin masterización, sin efectos,
sin cambiar el volumen ni la duración. Se guarda en FLAC o WAV a máxima calidad (misma frecuencia y bits que el
original, hasta 24 bits). Pensada para firmar temas completos, no previas.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QProgressBar, QPushButton, QRadioButton,
                               QVBoxLayout, QWidget)

from src import i18n
from src.engine.sign import AUDIO_EXTENSIONS, is_lossy, probe, sign_track
from src.i18n import tr
from src.ui import anim
from src.ui.dialog_style import ACCENT, ACCENT2, BG2, BG3, BORDER, DIALOG_QSS, GREEN, RED, TEXT, TEXT2, WARN


def _fmt_time(sec: float) -> str:
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def default_sign_dir(cfg: dict) -> str:
    """Carpeta de salida por defecto: «Firmados» junto a las previas, o en Música."""
    saved = (cfg or {}).get("sign_out_dir")
    if saved:
        return str(saved)
    base = (cfg or {}).get("output_dir") or ""
    if base:
        return str(Path(base).parent / "Firmados") if Path(base).name.lower() in ("previas", "previews") else str(Path(base) / "Firmados")
    return str(Path.home() / "Music" / "Firmados")


class SignWorker(QThread):
    """Firma los temas uno a uno sin bloquear la interfaz."""
    progress = Signal(int, str)            # porcentaje total, mensaje
    item_done = Signal(int, dict)          # posición, resultado
    item_failed = Signal(int, str)
    all_done = Signal(list, list)          # resultados, errores

    def __init__(self, files, out_dir, fmt, cover, metadata, parent=None):
        super().__init__(parent)
        self._files, self._out_dir, self._fmt = list(files), out_dir, fmt
        self._cover, self._meta = cover, dict(metadata)

    def run(self):
        results, errors = [], []
        n = max(1, len(self._files))
        for i, f in enumerate(self._files):
            if self.isInterruptionRequested():
                break
            meta = dict(self._meta)
            if n > 1:
                meta.pop("title", None)                      # con varios temas: el título de cada archivo

            def cb(p, m, i=i, name=Path(f).name):
                self.progress.emit(int((i * 100 + p) / n), f"{name} — {m}")

            try:
                r = sign_track(f, self._out_dir, self._fmt, self._cover, meta, cb)
                results.append(r)
                self.item_done.emit(i, r)
            except Exception as exc:                          # un tema que falla no para al resto
                errors.append((f, str(exc)))
                self.item_failed.emit(i, str(exc))
        self.all_done.emit(results, errors)


class _DropFrame(QFrame):
    """Zona grande para soltar los temas (o pulsar para elegirlos)."""
    files_dropped = Signal(list)
    clicked = Signal()

    _QSS = "QFrame#drop {{ background: {bg}; border: 2px dashed {bd}; border-radius: 14px; }}"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("drop")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(110)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        self._ico = QLabel("🖋")
        self._ico.setAlignment(Qt.AlignCenter)
        self._ico.setStyleSheet("font-size: 30px;")
        lay.addWidget(self._ico)
        self._lbl = QLabel("Arrastra aquí el tema entero (o varios) · o pulsa para elegirlos")
        self._lbl.setAlignment(Qt.AlignCenter)
        self._lbl.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: 700;")
        lay.addWidget(self._lbl)
        self._sub = QLabel("WAV · FLAC · AIFF · MP3 · M4A · OGG")
        self._sub.setAlignment(Qt.AlignCenter)
        self._sub.setStyleSheet(f"color: {TEXT2}; font-size: 11px;")
        lay.addWidget(self._sub)
        self._set_hot(False)

    def _set_hot(self, hot: bool):
        self.setStyleSheet(self._QSS.format(bg="#1b080b" if hot else BG2, bd=ACCENT if hot else BORDER))

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._set_hot(True)

    def dragLeaveEvent(self, e):
        self._set_hot(False)

    def dropEvent(self, e):
        self._set_hot(False)
        files = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if files:
            self.files_dropped.emit(files)
            e.acceptProposedAction()

    def mousePressEvent(self, e):
        self.clicked.emit()


class SignTrackDialog(QDialog):
    def __init__(self, cfg: dict, parent=None, files=None):
        super().__init__(parent)
        self._cfg = cfg
        self._files: list = []
        self._results: list = []
        self._worker = None
        self._cover = ""
        self._out_dir = default_sign_dir(cfg)
        self.setWindowTitle(tr("Firmar tema entero"))
        self.setModal(False)
        self.setMinimumSize(780, 800)
        self.resize(820, 860)
        self.setAcceptDrops(True)
        self.setStyleSheet(DIALOG_QSS + f"""
            QRadioButton {{ color: {TEXT}; font-size: 12px; spacing: 6px; background: transparent; }}
            QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 8px; border: 1px solid {BORDER}; background: {BG3}; }}
            QRadioButton::indicator:checked {{ background: {ACCENT}; border: 3px solid {BG3}; outline: 1px solid {ACCENT}; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(10)

        t = QLabel("🖋 Firmar tema entero")
        t.setStyleSheet("font-size: 20px; font-weight: 900;")
        root.addWidget(t)
        s = QLabel("Solo se le añade la carátula y las etiquetas. Sin masterización ni efectos: el audio queda "
                   "exactamente igual y se guarda en FLAC o WAV a máxima calidad.")
        s.setWordWrap(True)
        s.setStyleSheet(f"color: {TEXT2}; font-size: 12px;")
        root.addWidget(s)

        self._drop = _DropFrame()
        self._drop.files_dropped.connect(self.add_files)
        self._drop.clicked.connect(self._pick_files)
        root.addWidget(self._drop)

        self._list = QListWidget()
        self._list.setMinimumHeight(100)
        self._list.setMaximumHeight(150)
        root.addWidget(self._list)
        row_l = QHBoxLayout()
        self._lbl_warn = QLabel("")
        self._lbl_warn.setWordWrap(True)
        self._lbl_warn.setStyleSheet(f"color: {WARN}; font-size: 11px;")
        row_l.addWidget(self._lbl_warn, stretch=1)
        self._btn_clear = QPushButton("Vaciar lista")
        self._btn_clear.clicked.connect(self._clear)
        row_l.addWidget(self._btn_clear)
        root.addLayout(row_l)

        # carátula + etiquetas
        mid = QHBoxLayout()
        mid.setSpacing(14)
        cov = QVBoxLayout()
        self._lbl_cover = QLabel()
        self._lbl_cover.setFixedSize(168, 168)
        self._lbl_cover.setAlignment(Qt.AlignCenter)
        self._lbl_cover.setStyleSheet(f"background: {BG3}; border: 1px solid {BORDER}; border-radius: 10px; color: {TEXT2};")
        cov.addWidget(self._lbl_cover)
        self._btn_cover = QPushButton("🖼 Elegir carátula…")
        self._btn_cover.clicked.connect(self._pick_cover)
        cov.addWidget(self._btn_cover)
        self._btn_cover_off = QPushButton("Quitar carátula")
        self._btn_cover_off.clicked.connect(lambda: self._set_cover(""))
        cov.addWidget(self._btn_cover_off)
        cov.addStretch()
        mid.addLayout(cov)

        form = QVBoxLayout()
        form.setSpacing(6)
        self._ed = {}
        for key, label, ph in (("title", "Título", "Vacío = el del archivo"), ("artist", "Artista", "Radical Records"),
                               ("album", "Álbum / EP", ""), ("label", "Sello", "Radical Records"),
                               ("genre", "Género", "Techno"), ("comment", "Comentario", ""), ("year", "Año", "2026")):
            r = QHBoxLayout()
            lb = QLabel(label)
            lb.setFixedWidth(70)
            lb.setStyleSheet(f"color: {TEXT2}; font-size: 11px; font-weight: 700;")
            e = QLineEdit()
            e.setMinimumHeight(30)
            e.setPlaceholderText(ph)
            r.addWidget(lb)
            r.addWidget(e, stretch=1)
            form.addLayout(r)
            self._ed[key] = e
        self._ed["artist"].setText(str(cfg.get("tag_artist", "") or ""))
        self._ed["label"].setText(str(cfg.get("tag_label", "") or ""))
        self._ed["album"].setText(str(cfg.get("tag_album", "") or ""))
        self._ed["genre"].setText(str(cfg.get("tag_genre", "") or ""))
        self._ed["comment"].setText("")
        mid.addLayout(form, stretch=1)
        root.addLayout(mid)

        # formato
        fr = QHBoxLayout()
        lbf = QLabel("Formato")
        lbf.setFixedWidth(70)
        lbf.setStyleSheet(f"color: {TEXT2}; font-size: 11px; font-weight: 700;")
        fr.addWidget(lbf)
        self._rb_flac = QRadioButton("FLAC · sin pérdidas (recomendado)")
        self._rb_wav = QRadioButton("WAV · sin comprimir")
        self._rb_flac.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self._rb_flac)
        grp.addButton(self._rb_wav)
        for rb in (self._rb_flac, self._rb_wav):
            rb.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
            fr.addWidget(rb)
        fr.addStretch()
        root.addLayout(fr)
        note = QLabel("Se conservan la frecuencia de muestreo y los bits del original (hasta 24 bits). "
                      "Si el original es MP3/M4A se guarda sin perder nada más, pero no mejora su calidad.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {TEXT2}; font-size: 10.5px;")
        root.addWidget(note)

        # carpeta de salida
        orow = QHBoxLayout()
        lbo = QLabel("Carpeta")
        lbo.setFixedWidth(70)
        lbo.setStyleSheet(f"color: {TEXT2}; font-size: 11px; font-weight: 700;")
        orow.addWidget(lbo)
        self._lbl_out = QLabel("")
        self._lbl_out.setStyleSheet(f"color: {TEXT}; font-size: 11.5px;")
        orow.addWidget(self._lbl_out, stretch=1)
        self._btn_out = QPushButton("Cambiar")
        self._btn_out.clicked.connect(self._pick_out)
        orow.addWidget(self._btn_out)
        self._btn_open = QPushButton("📂 Abrir")
        self._btn_open.clicked.connect(self._open_out)
        orow.addWidget(self._btn_open)
        root.addLayout(orow)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(10)
        self._bar.setStyleSheet(f"QProgressBar {{ background: {BG3}; border: none; border-radius: 5px; }}"
                                f"QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}")
        root.addWidget(self._bar)
        self._lbl_status = QLabel("")
        self._lbl_status.setWordWrap(True)
        self._lbl_status.setStyleSheet(f"color: {TEXT2}; font-size: 11.5px;")
        root.addWidget(self._lbl_status)

        brow = QHBoxLayout()
        brow.addStretch()
        self._btn_close = QPushButton("Cerrar")
        self._btn_close.clicked.connect(self.close)
        brow.addWidget(self._btn_close)
        self._btn_sign = QPushButton("🖋 Firmar")
        self._btn_sign.setObjectName("primary")
        self._btn_sign.setMinimumWidth(190)
        self._btn_sign.clicked.connect(self._start)
        brow.addWidget(self._btn_sign)
        root.addLayout(brow)

        # carátula por defecto: la guardada en «Firma y carátula»
        saved_cover = str(cfg.get("custom_cover_path", "") or "")
        self._set_cover(saved_cover if saved_cover and Path(saved_cover).is_file() else "")
        self._refresh()
        i18n.translate_tree(self)
        if files:
            self.add_files(files)

    # ── lista de temas ────────────────────────────────────────────────────────────
    def files(self) -> list:
        return list(self._files)

    def add_files(self, paths):
        for p in paths:
            p = str(p)
            if Path(p).is_dir():
                for q in sorted(Path(p).iterdir()):
                    if q.suffix.lower() in AUDIO_EXTENSIONS:
                        self.add_files([str(q)])
                continue
            if Path(p).suffix.lower() not in AUDIO_EXTENSIONS or p in self._files or not Path(p).is_file():
                continue
            self._files.append(p)
            info = probe(p)
            if info["readable"]:
                detail = f"{_fmt_time(info['duration'])} · {info['sr'] / 1000:g} kHz · {info['bits']} bit"
            else:
                detail = tr("se decodificará")
            it = QListWidgetItem(f"{Path(p).name}   —   {detail}")
            it.setData(Qt.UserRole, p)
            self._list.addItem(it)
        self._refresh()

    def _clear(self):
        if self._worker is not None and self._worker.isRunning():
            return
        self._files.clear()
        self._list.clear()
        self._results = []
        self._bar.setValue(0)
        self._lbl_status.setText("")
        self._refresh()

    def _pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, tr("Elegir temas para firmar"), "",
                                                tr("Audio (*.wav *.flac *.aiff *.aif *.mp3 *.m4a *.ogg *.opus *.wma)"))
        if files:
            self.add_files(files)

    # ── carátula / carpeta ───────────────────────────────────────────────────────
    def _pick_cover(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("Elegir carátula"), "", tr("Imágenes (*.jpg *.jpeg *.png *.webp)"))
        if f:
            self._set_cover(f)

    def _set_cover(self, path: str):
        self._cover = path
        if path and Path(path).is_file():
            pm = QPixmap(path)
            if not pm.isNull():
                self._lbl_cover.setPixmap(pm.scaled(166, 166, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self._btn_cover_off.setEnabled(True)
                return
        self._cover = ""
        self._lbl_cover.setPixmap(QPixmap())
        self._lbl_cover.setText(tr("Sin carátula"))
        self._btn_cover_off.setEnabled(False)

    def cover(self) -> str:
        return self._cover

    def _pick_out(self):
        d = QFileDialog.getExistingDirectory(self, tr("Carpeta donde guardar los temas firmados"), self._out_dir)
        if d:
            self._out_dir = d
            self._refresh()

    def _open_out(self):
        from src.notifications import reveal_in_os
        Path(self._out_dir).mkdir(parents=True, exist_ok=True)
        reveal_in_os(self._out_dir)

    # ── firmar ───────────────────────────────────────────────────────────────────
    def fmt(self) -> str:
        return "flac" if self._rb_flac.isChecked() else "wav"

    def metadata(self) -> dict:
        return {k: e.text().strip() for k, e in self._ed.items()}

    def _refresh(self):
        n = len(self._files)
        busy = self._worker is not None and self._worker.isRunning()
        self._ed["title"].setEnabled(n <= 1 and not busy)
        self._ed["title"].setPlaceholderText(tr("Vacío = el del archivo") if n <= 1 else tr("El de cada archivo"))
        self._lbl_out.setText(self._out_dir if len(self._out_dir) < 60 else "…" + self._out_dir[-58:])
        self._btn_sign.setEnabled(n > 0 and not busy)
        i18n.set_text(self._btn_sign, "🖋 Firmar {n} tema" if n == 1 else "🖋 Firmar {n} temas", n=n) if n else \
            i18n.set_text(self._btn_sign, "🖋 Firmar")
        self._btn_clear.setEnabled(n > 0 and not busy)
        lossy = [Path(f).name for f in self._files if is_lossy(f)]
        self._lbl_warn.setText(tr("⚠ {n} tema(s) son MP3/M4A: se guardan sin perder nada más, pero no ganan calidad.", n=len(lossy))
                               if lossy else "")

    def _start(self):
        if not self._files or (self._worker is not None and self._worker.isRunning()):
            return
        try:
            from src.config import load, save
            c = load()
            c["sign_out_dir"] = self._out_dir
            save(c)
        except Exception:
            pass
        self._results = []
        self._bar.setValue(0)
        self._lbl_status.setStyleSheet(f"color: {TEXT2}; font-size: 11.5px;")
        self._lbl_status.setText(tr("Firmando…"))
        self._worker = SignWorker(self._files, self._out_dir, self.fmt(), self._cover or None, self.metadata(), self)
        self._worker.progress.connect(lambda p, m: (self._bar.setValue(p), self._lbl_status.setText(m)))
        self._worker.item_done.connect(self._on_item_done)
        self._worker.all_done.connect(self._on_all_done)
        self._refresh()
        self._worker.start()

    def _on_item_done(self, i: int, r: dict):
        it = self._list.item(i)
        if it is not None:
            it.setText("✅ " + it.text())

    def _on_all_done(self, results: list, errors: list):
        self._results = results
        self._bar.setValue(100)
        for f, err in errors:
            for i in range(self._list.count()):
                if self._list.item(i).data(Qt.UserRole) == f:
                    self._list.item(i).setText("❌ " + self._list.item(i).text())
        if results:
            ok = len(results)
            i18n.set_text(self._lbl_status, "✅ {n} tema firmado en {dir}" if ok == 1 else "✅ {n} temas firmados en {dir}",
                          n=ok, dir=self._out_dir)
            self._lbl_status.setStyleSheet(f"color: {GREEN}; font-size: 12px; font-weight: 700;")
            try:
                from src.notifications import notify
                notify("AutoPrevias", tr("✅ {n} tema(s) firmado(s) · pulsa para abrir", n=ok), folder=results[0]["path"])
            except Exception:
                pass
        if errors:
            msg = "; ".join(f"{Path(f).name}: {e}" for f, e in errors[:2])
            self._lbl_status.setText((self._lbl_status.text() + "\n" if results else "") + tr("⚠ No se pudo firmar: {err}", err=msg))
            if not results:
                self._lbl_status.setStyleSheet(f"color: {RED}; font-size: 12px; font-weight: 700;")
        self._refresh()

    # ── arrastrar a la ventana entera ────────────────────────────────────────────
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        files = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if files:
            self.add_files(files)
            e.acceptProposedAction()

    def showEvent(self, e):
        super().showEvent(e)
        anim.fade_in(self._drop, ms=320)

    def closeEvent(self, e):
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(3000)
        super().closeEvent(e)
