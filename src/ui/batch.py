"""
AutoPrevias — batch.py
Módulo de Procesamiento por Lote (Batch Processing) para sellos discográficos y DJs.
Permite encolar múltiples pistas o carpetas completas y procesar todas las previas
automáticamente en segundo plano con exportación multi-formato y vídeo social.
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.analysis.bpm import detect_beat_grid, SR_ANALYSIS
from src.analysis.key import detect_musical_key
from src.analysis.segments import build_preview_plan
from src.analysis.structure import analyze_structure
from src.config import get_output_dir, load as load_cfg
from src.engine.audio_io import load_audio_file
from src.engine.export import build_preview_audio, export_files, output_paths

# Paleta de color coherente con AutoPrevias
BG = "#08080a"
BG2 = "#0e0e12"
BG3 = "#141418"
BG4 = "#1c1c22"
BG5 = "#24242c"
BORDER = "#252530"
ACCENT = "#ff1e38"
ACCENT2 = "#990014"
TEXT = "#f0f0f4"
TEXT_MID = "#8b8b9e"
TEXT_DIM = "#4e4e5e"
GREEN = "#27c98a"
PURPLE = "#a855f7"
WARN = "#f59e0b"

AUDIO_EXTS = {".wav", ".mp3", ".aiff", ".aif", ".flac", ".m4a", ".ogg"}


class BatchWorker(QThread):
    file_started = Signal(int, str)             # index, filename
    file_progress = Signal(int, int, str)       # index, pct, msg
    file_finished = Signal(int, str, str, list) # index, bpm_key_info, status, generated_paths
    batch_finished = Signal(int, int, list)     # total_ok, total_err, all_generated
    log_message = Signal(str)

    def __init__(self, files: List[str], cfg: dict):
        super().__init__()
        self.files = files
        self.cfg = cfg
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        ok_count = 0
        err_count = 0
        total = len(self.files)
        all_generated: List[str] = []

        for idx, file_path in enumerate(self.files):
            if self._is_cancelled:
                break

            p = Path(file_path)
            self.file_started.emit(idx, p.name)

            try:
                # 1. Cargar audio
                self.file_progress.emit(idx, 15, "Cargando audio…")
                y, sr = load_audio_file(file_path, sr=SR_ANALYSIS, mono=True)

                # 2. Análisis rítmico y tonal
                self.file_progress.emit(idx, 35, "Detectando BPM y Camelot…")
                grid = detect_beat_grid(y, sr)
                key_res = detect_musical_key(y, sr)
                bpm_val = grid.bpm
                key_info = f"{bpm_val:.1f} BPM · {key_res.camelot} ({key_res.notation})"

                # 3. Estructura y plan
                self.file_progress.emit(idx, 55, "Estructurando previa…")
                structure = analyze_structure(y, sr, grid)
                plan = build_preview_plan(structure)

                # 4. Síntesis y efectos
                self.file_progress.emit(idx, 75, "Procesando audio y efectos…")
                audio, preview_sr, seed = build_preview_audio(
                    source_path=file_path,
                    plan=plan,
                    beat_grid=grid,
                    cfg=self.cfg,
                )

                # 5. Exportar formatos
                self.file_progress.emit(idx, 90, "Exportando archivos y vídeo…")
                out_dir = str(get_output_dir(file_path, self.cfg))
                paths = output_paths(
                    source_path=file_path,
                    out_dir=out_dir,
                    export_wav=self.cfg.get("export_wav", True),
                    export_mp3=self.cfg.get("export_mp3", True),
                    export_flac=self.cfg.get("export_flac", False),
                    export_aiff=self.cfg.get("export_aiff", False),
                    export_video=self.cfg.get("export_video", False),
                    custom_name=None,
                )

                meta = {
                    "bpm": bpm_val,
                    "key": f"{key_res.camelot} · {key_res.notation}",
                    "camelot": key_res.camelot,
                    "title": p.stem,
                }
                generated = export_files(
                    audio=audio,
                    sr=preview_sr,
                    paths=paths,
                    metadata=meta,
                    cover_image_path=self.cfg.get("cover_path"),
                )

                ok_count += 1
                all_generated.extend(generated)
                self.file_finished.emit(idx, key_info, "✅ Listo", generated)
            except Exception as e:
                err_count += 1
                err_msg = str(e).splitlines()[-1] if str(e) else "Error"
                self.file_finished.emit(idx, "—", f"❌ {err_msg}", [])
                self.log_message.emit(f"Error en {p.name}: {traceback.format_exc()}")

        self.batch_finished.emit(ok_count, err_count, all_generated)


class BatchDialog(QDialog):
    """Diálogo de procesamiento en lote para múltiples pistas de estudio."""

    def __init__(self, initial_files: Optional[List[str]] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("AutoPrevias — Procesamiento por Lote de Estudio (Batch Engine)")
        self.resize(880, 580)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background: {BG};
                color: {TEXT};
            }}
        """)
        self._cfg = load_cfg()
        self._files: List[str] = []
        self._worker: Optional[BatchWorker] = None
        self._build_ui()

        if initial_files:
            self._add_files(initial_files)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        # ── Header ───────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        icon = QLabel("📁")
        icon.setStyleSheet("font-size: 24px;")
        hdr.addWidget(icon)

        t_col = QVBoxLayout()
        t_col.setSpacing(2)
        lbl_t = QLabel("PROCESAMIENTO POR LOTE · RADICAL RECORDS")
        lbl_t.setStyleSheet(f"color: {ACCENT}; font-size: 14px; font-weight: 900; letter-spacing: 0.5px;")
        t_col.addWidget(lbl_t)
        lbl_sub = QLabel("Analiza y genera previas para múltiples pistas automáticamente con detección armónica y vídeo.")
        lbl_sub.setStyleSheet(f"color: {TEXT_MID}; font-size: 11px;")
        t_col.addWidget(lbl_sub)
        hdr.addLayout(t_col, stretch=1)
        root.addLayout(hdr)

        # ── Toolbar ──────────────────────────────────────────────────────────
        tb = QHBoxLayout()
        tb.setSpacing(8)

        btn_add = QPushButton("➕ Añadir Pistas…")
        btn_add.setFixedHeight(28)
        btn_add.setStyleSheet(self._btn_style(BG3, TEXT, ACCENT))
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._browse_files)
        tb.addWidget(btn_add)

        btn_dir = QPushButton("📂 Añadir Carpeta…")
        btn_dir.setFixedHeight(28)
        btn_dir.setStyleSheet(self._btn_style(BG3, TEXT, ACCENT))
        btn_dir.setCursor(Qt.PointingHandCursor)
        btn_dir.clicked.connect(self._browse_dir)
        tb.addWidget(btn_dir)

        btn_clear = QPushButton("🗑️ Limpiar")
        btn_clear.setFixedHeight(28)
        btn_clear.setStyleSheet(self._btn_style(BG3, TEXT_DIM, "#ef4444"))
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_list)
        tb.addWidget(btn_clear)

        tb.addStretch()

        self._lbl_count = QLabel("0 pistas en cola")
        self._lbl_count.setStyleSheet(f"color: {TEXT_MID}; font-size: 11px; font-weight: 700;")
        tb.addWidget(self._lbl_count)
        root.addLayout(tb)

        # ── Destino de Exportación ───────────────────────────────────────────
        dest_box = QFrame()
        dest_box.setStyleSheet(f"background: {BG2}; border: 1px solid {BORDER}; border-radius: 8px;")
        dest_lay = QHBoxLayout(dest_box)
        dest_lay.setContentsMargins(12, 6, 12, 6)
        dest_lay.setSpacing(10)

        lbl_dest = QLabel("📁 Carpeta destino:")
        lbl_dest.setStyleSheet(f"color: {TEXT_MID}; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        dest_lay.addWidget(lbl_dest)

        self._lbl_dest_path = QLabel("Subcarpeta 'Previas' en cada pista de origen (Predeterminado)")
        self._lbl_dest_path.setStyleSheet(f"color: {GREEN}; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        dest_lay.addWidget(self._lbl_dest_path, stretch=1)

        btn_ch_dest = QPushButton("Cambiar…")
        btn_ch_dest.setFixedHeight(24)
        btn_ch_dest.setStyleSheet(self._btn_style(BG3, TEXT, ACCENT))
        btn_ch_dest.setCursor(Qt.PointingHandCursor)
        btn_ch_dest.clicked.connect(self._choose_dest_folder)
        dest_lay.addWidget(btn_ch_dest)

        btn_rst_dest = QPushButton("Restablecer")
        btn_rst_dest.setFixedHeight(24)
        btn_rst_dest.setStyleSheet(self._btn_style(BG3, TEXT_DIM, "#ef4444"))
        btn_rst_dest.setCursor(Qt.PointingHandCursor)
        btn_rst_dest.clicked.connect(self._reset_dest_folder)
        dest_lay.addWidget(btn_rst_dest)

        btn_op_dest = QPushButton("📂 Abrir Carpeta")
        btn_op_dest.setFixedHeight(24)
        btn_op_dest.setStyleSheet(self._btn_style(BG3, TEXT, GREEN))
        btn_op_dest.setCursor(Qt.PointingHandCursor)
        btn_op_dest.clicked.connect(self._open_current_dest)
        dest_lay.addWidget(btn_op_dest)

        root.addWidget(dest_box)

        # ── Tabla de Archivos ────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["PISTA / ARCHIVO", "DURACIÓN", "BPM / TONALIDAD", "ESTADO", "ACCIONES"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.cellDoubleClicked.connect(self._on_table_double_clicked)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: {BG2};
                border: 1px solid {BORDER};
                border-radius: 8px;
                gridline-color: {BORDER};
                color: {TEXT};
                font-size: 11px;
            }}
            QHeaderView::section {{
                background: {BG3};
                color: {TEXT_MID};
                padding: 6px;
                border: none;
                border-bottom: 1px solid {BORDER};
                font-size: 9.5px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }}
        """)
        root.addWidget(self._table, stretch=1)

        # ── Opciones de Lote ─────────────────────────────────────────────────
        opt_box = QFrame()
        opt_box.setStyleSheet(f"background: {BG2}; border: 1px solid {BORDER}; border-radius: 8px;")
        opt_lay = QHBoxLayout(opt_box)
        opt_lay.setContentsMargins(12, 8, 12, 8)
        opt_lay.setSpacing(16)

        lbl_f = QLabel("Formatos:")
        lbl_f.setStyleSheet(f"color: {TEXT_MID}; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        opt_lay.addWidget(lbl_f)

        self._chk_wav = QCheckBox("WAV 24b")
        self._chk_wav.setChecked(True)
        self._chk_wav.setStyleSheet("color: white; font-size: 11px; border: none; background: transparent;")
        opt_lay.addWidget(self._chk_wav)

        self._chk_mp3 = QCheckBox("MP3 320k")
        self._chk_mp3.setChecked(True)
        self._chk_mp3.setStyleSheet("color: white; font-size: 11px; border: none; background: transparent;")
        opt_lay.addWidget(self._chk_mp3)

        self._chk_flac = QCheckBox("FLAC")
        self._chk_flac.setChecked(False)
        self._chk_flac.setStyleSheet("color: white; font-size: 11px; border: none; background: transparent;")
        opt_lay.addWidget(self._chk_flac)

        self._chk_video = QCheckBox("🎬 Vídeo 9:16 (TikTok/Reels)")
        self._chk_video.setChecked(False)
        self._chk_video.setStyleSheet("color: #a855f7; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        opt_lay.addWidget(self._chk_video)

        opt_lay.addStretch()

        lbl_fx = QLabel("Efectos:")
        lbl_fx.setStyleSheet(f"color: {TEXT_MID}; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        opt_lay.addWidget(lbl_fx)

        self._chk_flanger = QCheckBox("Flanger Pre-Drop")
        self._chk_flanger.setChecked(False)
        self._chk_flanger.setStyleSheet("color: white; font-size: 11px; border: none; background: transparent;")
        opt_lay.addWidget(self._chk_flanger)

        self._chk_master = QCheckBox("Master LUFS (-9 dB)")
        self._chk_master.setChecked(True)
        self._chk_master.setStyleSheet("color: #27c98a; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        opt_lay.addWidget(self._chk_master)

        root.addWidget(opt_box)

        # ── Barra de Progreso y Acciones ─────────────────────────────────────
        bot = QHBoxLayout()
        bot.setSpacing(10)

        self._prog = QProgressBar()
        self._prog.setRange(0, 100)
        self._prog.setValue(0)
        self._prog.setTextVisible(True)
        self._prog.setFixedHeight(22)
        self._prog.setStyleSheet(f"""
            QProgressBar {{
                background: {BG3};
                border: 1px solid {BORDER};
                border-radius: 5px;
                color: white;
                font-size: 10px;
                font-weight: 800;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ACCENT}, stop:1 {ACCENT2});
                border-radius: 4px;
            }}
        """)
        bot.addWidget(self._prog, stretch=1)

        self._btn_start = QPushButton("🚀 Iniciar Lote")
        self._btn_start.setFixedHeight(34)
        self._btn_start.setFixedWidth(140)
        self._btn_start.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ACCENT}, stop:1 {ACCENT2});
                color: white;
                font-size: 12px;
                font-weight: 800;
                border: 1px solid #ff4d63;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: #ff334b;
            }}
            QPushButton:disabled {{
                background: {BG4};
                color: {TEXT_DIM};
                border-color: transparent;
            }}
        """)
        self._btn_start.setCursor(Qt.PointingHandCursor)
        self._btn_start.clicked.connect(self._toggle_batch)
        bot.addWidget(self._btn_start)

        root.addLayout(bot)

    def _btn_style(self, bg, fg, border):
        return f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1px solid {BORDER};
                border-radius: 5px;
                font-size: 11px;
                font-weight: 700;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                border-color: {border};
                color: white;
            }}
        """

    def _browse_files(self):
        ext_filter = "Archivos de Audio (*.wav *.mp3 *.aiff *.flac *.m4a *.ogg)"
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar pistas de audio", "", ext_filter)
        if files:
            self._add_files(files)

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta con pistas")
        if folder:
            p = Path(folder)
            found = [str(f) for f in p.glob("*") if f.suffix.lower() in AUDIO_EXTS]
            if found:
                self._add_files(found)

    def _add_files(self, paths: List[str]):
        for path in paths:
            if path not in self._files and Path(path).suffix.lower() in AUDIO_EXTS:
                self._files.append(path)
                row = self._table.rowCount()
                self._table.insertRow(row)

                p = Path(path)
                item_name = QTableWidgetItem(p.name)
                item_name.setToolTip(path)
                self._table.setItem(row, 0, item_name)

                # Duración estimada por tamaño
                sz_mb = p.stat().st_size / (1024 * 1024)
                item_sz = QTableWidgetItem(f"{sz_mb:.1f} MB")
                self._table.setItem(row, 1, item_sz)

                item_key = QTableWidgetItem("—")
                self._table.setItem(row, 2, item_key)

                item_st = QTableWidgetItem("⏳ En cola")
                item_st.setForeground(QColor(TEXT_MID))
                self._table.setItem(row, 3, item_st)

                item_act = QTableWidgetItem("—")
                item_act.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row, 4, item_act)

        self._lbl_count.setText(f"{len(self._files)} pistas en cola")
        self._btn_start.setEnabled(len(self._files) > 0)

    def _choose_dest_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta destino para el lote")
        if folder:
            self._custom_out_dir = folder
            self._lbl_dest_path.setText(str(folder))
            self._lbl_dest_path.setStyleSheet(f"color: {TEXT}; font-size: 11px; font-weight: 700; border: none; background: transparent;")

    def _reset_dest_folder(self):
        self._custom_out_dir = None
        self._lbl_dest_path.setText("Subcarpeta 'Previas' en cada pista de origen (Predeterminado)")
        self._lbl_dest_path.setStyleSheet(f"color: {GREEN}; font-size: 11px; font-weight: 600; border: none; background: transparent;")

    def _open_current_dest(self):
        if hasattr(self, "_custom_out_dir") and self._custom_out_dir:
            self._reveal_paths([self._custom_out_dir])
        elif self._files:
            self._reveal_paths([str(Path(self._files[0]).parent)])
        else:
            from src.config import get_output_dir
            self._reveal_paths([str(get_output_dir("", self._cfg))])

    def _reveal_paths(self, paths: list):
        if not paths:
            return
        target = paths[0]
        p = Path(target)
        try:
            import subprocess, sys
            if not p.exists():
                p = p.parent
            if sys.platform == "darwin":
                if p.is_file():
                    subprocess.run(["open", "-R", str(p)])
                else:
                    subprocess.run(["open", str(p)])
            elif sys.platform == "win32":
                if p.is_file():
                    subprocess.run(["explorer", f"/select,{p}"])
                else:
                    subprocess.run(["explorer", str(p)])
            else:
                target_str = str(p if p.is_dir() else p.parent)
                subprocess.run(["xdg-open", target_str])
        except Exception:
            pass

    def _on_table_double_clicked(self, row: int, col: int):
        if hasattr(self, "_generated_map") and row in self._generated_map:
            self._reveal_paths(self._generated_map[row])
        elif 0 <= row < len(self._files):
            self._reveal_paths([self._files[row]])

    def _clear_list(self):
        if self._worker and self._worker.isRunning():
            return
        self._files.clear()
        self._table.setRowCount(0)
        self._lbl_count.setText("0 pistas en cola")
        self._btn_start.setEnabled(False)

    def _toggle_batch(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._btn_start.setText("🚀 Iniciar Lote")
            return

        if not self._files:
            return

        cfg = dict(self._cfg)
        cfg["export_wav"] = self._chk_wav.isChecked()
        cfg["export_mp3"] = self._chk_mp3.isChecked()
        cfg["export_flac"] = self._chk_flac.isChecked()
        cfg["export_video"] = self._chk_video.isChecked()
        cfg["fx_flanger"] = self._chk_flanger.isChecked()
        cfg["studio_mastering"] = self._chk_master.isChecked()

        if hasattr(self, "_custom_out_dir") and self._custom_out_dir:
            cfg["output_dir"] = self._custom_out_dir

        self._generated_map = {}
        self._prog.setValue(0)
        self._btn_start.setText("⏹ Detener")

        self._worker = BatchWorker(self._files, cfg)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_progress.connect(self._on_file_progress)
        self._worker.file_finished.connect(self._on_file_finished)
        self._worker.batch_finished.connect(self._on_batch_finished)
        self._worker.start()

    def _on_file_started(self, idx: int, name: str):
        item = self._table.item(idx, 3)
        if item:
            item.setText("⚙️ Procesando…")
            item.setForeground(QColor(WARN))

    def _on_file_progress(self, idx: int, pct: int, msg: str):
        total = len(self._files)
        overall = int(((idx + (pct / 100.0)) / total) * 100)
        self._prog.setValue(overall)
        item = self._table.item(idx, 3)
        if item:
            item.setText(f"⚙️ {msg}")

    def _on_file_finished(self, idx: int, key_info: str, status: str, generated: list):
        if not hasattr(self, "_generated_map"):
            self._generated_map = {}
        self._generated_map[idx] = generated

        if key_info != "—":
            it_key = self._table.item(idx, 2)
            if it_key:
                it_key.setText(key_info)
                it_key.setForeground(QColor(PURPLE))

        item = self._table.item(idx, 3)
        if item:
            item.setText(status)
            item.setForeground(QColor(GREEN if "Listo" in status else "#ef4444"))

        if generated:
            btn_open = QPushButton("📂 Abrir")
            btn_open.setFixedHeight(22)
            btn_open.setStyleSheet(f"""
                QPushButton {{
                    background: {BG3};
                    color: {TEXT};
                    border: 1px solid {BORDER};
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 0 6px;
                }}
                QPushButton:hover {{
                    border-color: {GREEN};
                    color: {GREEN};
                }}
            """)
            btn_open.setCursor(Qt.PointingHandCursor)
            btn_open.setToolTip(f"Abrir carpeta y ver archivos ({len(generated)}):\n" + "\n".join(Path(p).name for p in generated))
            btn_open.clicked.connect(lambda _, g=generated: self._reveal_paths(g))
            self._table.setCellWidget(idx, 4, btn_open)

    def _on_batch_finished(self, ok: int, err: int, all_generated: list):
        self._prog.setValue(100)
        self._btn_start.setText("🚀 Iniciar Lote")

        out_dirs = list(dict.fromkeys(str(Path(p).parent) for p in all_generated if Path(p).exists()))
        dirs_text = "<br>".join(f"• <code>{d}</code>" for d in out_dirs[:4])
        if len(out_dirs) > 4:
            dirs_text += f"<br><i>... y {len(out_dirs) - 4} carpetas adicionales.</i>"

        vid_count = sum(1 for p in all_generated if p.lower().endswith(".mp4"))

        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("🎉 Procesamiento por Lote Completado")
        msg.setIcon(QMessageBox.Information)
        msg.setText(
            f"<h3>¡Procesamiento por lote finalizado con éxito!</h3>"
            f"<p>✓ <b>{ok}</b> pistas procesadas correctamente.<br>"
            f"✓ <b>{len(all_generated)}</b> archivos generados en total"
            f" (incluyendo <b>{vid_count}</b> vídeos MP4 9:16 para redes).<br>"
            f"✗ <b>{err}</b> errores.</p>"
            f"<hr>"
            f"<p><b>📁 Archivos guardados en:</b><br>{dirs_text}</p>"
        )
        btn_open = msg.addButton("📂 Abrir Carpeta en Finder / Explorador", QMessageBox.ActionRole)
        msg.addButton("Cerrar", QMessageBox.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_open and out_dirs:
            self._reveal_paths([out_dirs[0]])
