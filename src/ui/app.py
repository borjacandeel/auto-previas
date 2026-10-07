"""
AutoPrevias — Radical Records
Interfaz principal — Sesión 2: rewrite UI premium x100 + Fase C completa.

Cambios vs v1:
- Diseño glassmorphism dark (fondo #1a1d23, cards con blur simulado)
- Header con degradado animado pulsante
- Drop zone rediseñada: partículas SVG animadas en CSS, icono 3D
- Panel de resultados completamente reestructurado:
    ① WaveformWidget (pyqtgraph) con regiones coloreadas y playhead
    ② PlayerWidget (QMediaPlayer) sincronizado con waveform
    ③ Seed QSpinBox visible/editable + botón dado aleatorio
    ④ Stats strip premium (BPM, duración, drops, seed)
    ⑤ Tabs mejoradas con badges de color
- Botón GENERAR con efecto shimmer animado
- Progress bar con efecto glow
- Todas las animaciones con QPropertyAnimation + QEasingCurve
- Compatible Windows + macOS (sin Win32 ni AppKit)
"""

import math
import random
import sys
from pathlib import Path

import numpy as np

from PySide6.QtCore import (
    Qt, QThread, Signal, QTimer, QPropertyAnimation,
    QEasingCurve, QRect, QPoint,
)
from PySide6.QtGui import (
    QColor, QDragEnterEvent, QDropEvent, QPalette, QFont,
    QLinearGradient, QPainter, QBrush, QPen, QPainterPath, QPixmap, QImage,
)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QGraphicsOpacityEffect,
    QHBoxLayout, QLabel, QLineEdit, QTextEdit, QMainWindow, QProgressBar,
    QPushButton, QStackedWidget, QTableWidget, QSpinBox, QDoubleSpinBox,
    QComboBox, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
    QFrame, QTabWidget, QAbstractItemView, QSizePolicy,
    QScrollArea, QGraphicsDropShadowEffect, QMenu,
)

_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_ROOT))

from src.config import (
    load as load_cfg, save as save_cfg, get_output_dir, get_assets_dir,
    get_active_cover_path, save_custom_cover,
)
_ASSETS_DIR = get_assets_dir()

from src.analysis.bpm import detect_beat_grid, SR_ANALYSIS
from src.analysis.structure import analyze_structure, SectionType
from src.analysis.segments import build_preview_plan
from src.engine.export import build_preview_audio, export_files, output_paths
from src.engine.variations import compute_preview_tempo_curve

try:
    import pyqtgraph as pg
    pg.setConfigOptions(antialias=False, useOpenGL=False)
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False

try:
    from src.ui.waveform import WaveformWidget
    HAS_WAVEFORM = True
except ImportError:
    HAS_WAVEFORM = False

try:
    from src.ui.player import PlayerWidget
    HAS_PLAYER = True
except ImportError:
    HAS_PLAYER = False

# ── Paleta RR STUDIO Synth (Hardware Rack Crimson & Obsidian) ─────────────────
BG        = "#0a0b0e"
BG2       = "#121419"
BG3       = "#181b22"
BG4       = "#21252f"
BG5       = "#2a2f3c"
GLASS     = "#14161d"
ACCENT    = "#ff1e38"
ACCENT2   = "#ff3e55"
ACCENT_HV = "#ff546a"
GREEN     = "#ff1e38"
GREEN_HV  = "#ff3e55"
GREEN_DIM = "#990014"
RED       = "#ff1e38"
RED_BTN   = "#ff1e38"
ORANGE    = "#ff7b2b"
TEXT      = "#eceef2"
TEXT_DIM  = "#555b6a"
TEXT_MID  = "#8c93a4"
TEXT_SUB  = "#b8bfce"
SUCCESS   = "#ff1e38"
WARN      = "#ff7b2b"
BORDER    = "#232733"
BORDER_HV = "#ff1e38"
SHIMMER   = "#ffffff18"

VERSION   = "2.0"
CREATOR   = "Radical Records"
SUPPORT   = "radicalrecordsvlc@gmail.com"

# Colores semánticos para medidores de audio (independientes de la marca)
METER_OK   = "#27c98a"   # verde: nivel seguro
METER_WARN = WARN        # naranja: atención
METER_CLIP = ACCENT      # rojo: peligro/clip

SECTION_COLOR = {
    SectionType.INTRO:     "#ff2e4d",
    SectionType.BUILDUP:   "#ff7b2b",
    SectionType.DROP:      "#ff0033",
    SectionType.BREAKDOWN: "#c91650",
    SectionType.OUTRO:     "#ff5436",
    SectionType.UNKNOWN:   "#883344",
}
SECTION_LABEL = {
    SectionType.INTRO:     "Intro",
    SectionType.BUILDUP:   "Subida",
    SectionType.DROP:      "Drop",
    SectionType.BREAKDOWN: "Descanso",
    SectionType.OUTRO:     "Outro",
    SectionType.UNKNOWN:   "?",
}

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".aiff", ".aif", ".m4a"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_time(sec: float) -> str:
    m = int(sec) // 60
    s = sec - m * 60
    return f"{m}:{s:05.2f}"

def fmt_time_short(sec: float) -> str:
    m = int(sec) // 60
    s = int(sec) % 60
    return f"{m}:{s:02d}"

def short_path(p: str, max_len: int = 38) -> str:
    parts = Path(p).parts
    if len(parts) <= 3:
        return str(Path(p))
    return "…/" + "/".join(parts[-2:])

def preview_filename(source_path: str) -> str:
    p = Path(source_path)
    return f"PREVIA - {p.stem}"


# ── Workers ───────────────────────────────────────────────────────────────────

class AnalysisWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(object, object, object, float, float, object)
    error    = Signal(str)

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def run(self):
        try:
            import gc
            if self.isInterruptionRequested():
                return
            from src.engine.audio_io import load_audio_file
            from src.analysis.key import detect_musical_key
            self.progress.emit(5,  "Cargando audio…")
            y, sr = load_audio_file(self.path, sr=SR_ANALYSIS, mono=True, dtype=np.float32)
            if self.isInterruptionRequested():
                return
            dur = float(len(y)) / float(sr)
            self.progress.emit(25, "Detectando BPM y beat grid…")
            grid = detect_beat_grid(y, sr)
            if self.isInterruptionRequested():
                return
            self.progress.emit(45, "Detectando Tonalidad Armónica y Camelot…")
            key_res = detect_musical_key(y, sr)
            if self.isInterruptionRequested():
                return
            self.progress.emit(68, "Analizando estructura musical…")
            analysis = analyze_structure(y, sr, grid)
            if self.isInterruptionRequested():
                return
            self.progress.emit(85, "Construyendo plan de previa (Preset 120s / 2 Min)…")
            plan = build_preview_plan(analysis, target_duration_sec=120.0)
            if self.isInterruptionRequested():
                return
            self.progress.emit(100, "¡Análisis completado!")

            # Liberar el buffer de audio de análisis inmediatamente
            del y
            gc.collect()

            if not self.isInterruptionRequested():
                self.finished.emit(analysis, plan, grid, grid.bpm, dur, key_res)
        except Exception:
            if not self.isInterruptionRequested():
                import traceback
                self.error.emit(traceback.format_exc())


class ExportWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(list, int)
    error    = Signal(str)

    def __init__(self, source_path, plan, beat_grid, cfg, seed=None):
        super().__init__()
        self.source_path = source_path
        self.plan        = plan
        self.beat_grid   = beat_grid
        self.cfg         = cfg
        self.seed        = seed

    def run(self):
        try:
            import gc
            if self.isInterruptionRequested():
                return
            audio, sr, seed_used = build_preview_audio(
                self.source_path, self.plan, self.beat_grid, self.cfg,
                progress_cb=self.progress.emit, seed=self.seed,
            )
            out_dir = str(get_output_dir(self.source_path, self.cfg))
            paths   = output_paths(
                self.source_path, out_dir,
                export_wav=self.cfg.get("export_wav", True),
                export_mp3=self.cfg.get("export_mp3", True),
                export_flac=self.cfg.get("export_flac", False),
                export_aiff=self.cfg.get("export_aiff", False),
                export_video=self.cfg.get("export_video", False),
                custom_name=self.cfg.get("custom_name"),
            )
            metadata = dict(self.cfg.get("metadata") or {})
            if self.beat_grid and hasattr(self.beat_grid, "bpm"):
                metadata["bpm"] = self.beat_grid.bpm
            if self.cfg.get("key_str"):
                metadata["key"] = self.cfg.get("key_str")
            metadata["video_palette"]    = self.cfg.get("video_palette", "radical")
            metadata["video_promo_text"] = self.cfg.get("video_promo_text", "RADICAL RECORDS · PROMO EXCLUSIVA")
            metadata["aspect_ratio"]     = self.cfg.get("aspect_ratio", "9:16")

            cover_path = self.cfg.get("cover_path")

            generated = export_files(
                audio, sr, paths,
                progress_cb=self.progress.emit,
                metadata=metadata,
                cover_image_path=cover_path,
            )

            # Liberar buffer de audio exportado inmediatamente
            del audio
            gc.collect()

            self.finished.emit(generated, seed_used)
        except Exception:
            import traceback
            self.error.emit(traceback.format_exc())


# ── Estilos compartidos ───────────────────────────────────────────────────────

def _btn(bg: str, fg: str, bg_hv: str, radius: int = 7,
         fs: int = 11, bold: bool = True, border: str = "") -> str:
    brd = f"border: 1px solid {border};" if border else "border: none;"
    weight = "700" if bold else "500"
    return f"""
        QPushButton {{
            background: {bg};
            color: {fg};
            {brd}
            border-radius: {radius}px;
            font-size: {fs}px;
            font-weight: {weight};
            padding: 0 14px;
            letter-spacing: 0.3px;
        }}
        QPushButton:hover  {{ background: {bg_hv}; }}
        QPushButton:pressed {{ background: {bg}; }}
        QPushButton:disabled {{
            background: {BG3};
            color: {TEXT_DIM};
            border: none;
        }}
    """

def _input_style() -> str:
    return f"""
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background: {BG3};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 6px;
            font-size: 11px;
            padding: 0 6px;
            selection-background-color: {ACCENT}44;
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border: 1px solid {ACCENT};
        }}
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            width: 0; height: 0; border: none;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 16px;
        }}
        QComboBox QAbstractItemView {{
            background: {BG3};
            color: {TEXT};
            selection-background-color: {BG4};
            border: 1px solid {BORDER};
        }}
    """

def _table_style() -> str:
    return f"""
        QTableWidget {{
            background: {BG2};
            alternate-background-color: {BG3};
            color: {TEXT};
            font-size: 11px;
            border: none;
            gridline-color: transparent;
            selection-background-color: {ACCENT}22;
            outline: none;
        }}
        QTableWidget::item {{
            padding: 2px 6px;
            border: none;
        }}
        QHeaderView::section {{
            background: {BG3};
            color: {TEXT_DIM};
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1.2px;
            padding: 5px 8px;
            border: none;
            border-bottom: 1px solid {BORDER};
            text-transform: uppercase;
        }}
        QScrollBar:vertical {{
            background: {BG2};
            width: 5px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {BG5};
            border-radius: 2px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {TEXT_DIM};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
    """

def _tab_style() -> str:
    return f"""
        QTabWidget::pane {{
            background: {BG2};
            border: 1px solid {BORDER};
            border-radius: 10px;
            border-top-left-radius: 0px;
        }}
        QTabBar::tab {{
            background: {BG3};
            color: {TEXT_SUB};
            padding: 6px 18px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 2px;
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        QTabBar::tab:selected {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {ACCENT}, stop:1 {ACCENT2});
            color: white;
        }}
        QTabBar::tab:hover:!selected {{
            background: {BG5};
            color: {TEXT};
        }}
    """

def _shadow(widget: QWidget, radius: int = 20, color: str = "#000000",
            alpha: int = 80, offset: int = 4):
    eff = QGraphicsDropShadowEffect(widget)
    c = QColor(color)
    c.setAlpha(alpha)
    eff.setColor(c)
    eff.setBlurRadius(radius)
    eff.setOffset(0, offset)
    widget.setGraphicsEffect(eff)


# ── Drop Zone ─────────────────────────────────────────────────────────────────

class GlowFrame(QFrame):
    """Frame con borde que pulsa en color."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._glow_alpha = 40
        self._glow_color = QColor(ACCENT)
        self._hovering   = False

    def set_glow(self, alpha: int, hovering: bool = False):
        self._glow_alpha = alpha
        self._hovering   = hovering
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        if self._hovering:
            c = QColor(ACCENT)
            c.setAlpha(200)
            pen = QPen(c, 2, Qt.SolidLine)
        else:
            c = QColor(ACCENT)
            c.setAlpha(self._glow_alpha)
            pen = QPen(c, 2, Qt.DashLine)

        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 20, 20)
        p.end()


class DropZone(QWidget):
    file_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self._hovering    = False
        self._pulse_phase = 0.0
        self._particles   = []
        self._build_ui()
        self._init_particles()

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick)
        self._pulse_timer.start(66)  # ~15 fps — suficiente para partículas

    def showEvent(self, event):
        super().showEvent(event)
        if not self._pulse_timer.isActive():
            self._pulse_timer.start(66)

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._pulse_timer.isActive():
            self._pulse_timer.stop()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)
        outer.setContentsMargins(0, 0, 0, 0)

        # Card principal
        self._card = GlowFrame()
        self._card.setObjectName("drop-card")
        self._card.setFixedSize(580, 420)
        self._card.setStyleSheet(f"""
            QFrame#drop-card {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {BG3}, stop:1 {BG2});
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}
        """)

        lay = QVBoxLayout(self._card)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(14)
        lay.setContentsMargins(60, 36, 60, 36)

        # Emblema Radical Records
        emblem_path = _ASSETS_DIR / "logo_emblem.png"
        if not emblem_path.exists():
            emblem_path = _ASSETS_DIR / "logo_emblem_red.png"
        self._icon_pix_normal = None   # pixmap original (o None si es emoji)
        if emblem_path.exists():
            pix = QPixmap(str(emblem_path))
            if not pix.isNull():
                self._icon_lbl = QLabel()
                self._icon_lbl.setAlignment(Qt.AlignCenter)
                scaled = pix.scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._icon_lbl.setPixmap(scaled)
                self._icon_lbl.setStyleSheet("background: transparent; border: none;")
                self._icon_pix_normal = scaled
            else:
                self._icon_lbl = QLabel("🎧")
                self._icon_lbl.setAlignment(Qt.AlignCenter)
                self._icon_lbl.setStyleSheet("font-size: 64px; background: transparent; border: none;")
        else:
            self._icon_lbl = QLabel("🎧")
            self._icon_lbl.setAlignment(Qt.AlignCenter)
            self._icon_lbl.setStyleSheet("font-size: 64px; background: transparent; border: none;")
        lay.addWidget(self._icon_lbl)

        # Título
        title = QLabel("Arrastra tu track aquí")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"font-size: 24px; font-weight: 800; color: {TEXT};"
            "background: transparent; border: none; letter-spacing: -0.5px;"
        )
        lay.addWidget(title)

        # Formatos
        sub = QLabel("WAV  ·  MP3  ·  FLAC  ·  AIFF  ·  M4A")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(
            f"font-size: 11px; color: {TEXT_DIM}; letter-spacing: 3px;"
            "background: transparent; border: none; font-weight: 600;"
        )
        lay.addWidget(sub)

        # Separador
        sep = QLabel("— o —")
        sep.setAlignment(Qt.AlignCenter)
        sep.setStyleSheet(
            f"font-size: 12px; color: {TEXT_DIM}; margin: 2px 0;"
            "background: transparent; border: none;"
        )
        lay.addWidget(sep)

        # Botón abrir
        self._btn_open = QPushButton("  Abrir archivo  ")
        self._btn_open.setFixedHeight(46)
        self._btn_open.setMinimumWidth(220)
        self._btn_open.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ACCENT}, stop:1 #a80016);
                color: white;
                border: 1px solid #ff4d63;
                border-radius: 12px;
                font-size: 14px;
                font-weight: 800;
                padding: 0 28px;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ACCENT_HV}, stop:1 #d6001e);
                border: 1px solid #ff7588;
            }}
            QPushButton:pressed {{
                background: #800010;
            }}
        """)
        self._btn_open.setCursor(Qt.PointingHandCursor)
        self._btn_open.clicked.connect(self._open_dialog)
        lay.addWidget(self._btn_open, alignment=Qt.AlignCenter)

        # Marca Radical Records en drop zone
        banner_path = _ASSETS_DIR / "logo_banner.png"
        if not banner_path.exists():
            banner_path = _ASSETS_DIR / "logo_banner_red.png"
        if banner_path.exists():
            b_pix = QPixmap(str(banner_path))
            if not b_pix.isNull():
                lbl_wm = QLabel()
                lbl_wm.setAlignment(Qt.AlignCenter)
                lbl_wm.setPixmap(b_pix.scaledToHeight(22, Qt.SmoothTransformation))
                lbl_wm.setStyleSheet("background: transparent; border: none; margin-top: 10px;")
                lay.addWidget(lbl_wm, alignment=Qt.AlignCenter)

        outer.addWidget(self._card)

    def _init_particles(self):
        import random
        for _ in range(18):
            self._particles.append({
                "x": random.uniform(0, 560),
                "y": random.uniform(0, 380),
                "r": random.uniform(1, 3),
                "speed": random.uniform(0.3, 1.0),
                "phase": random.uniform(0, math.pi * 2),
                "alpha": random.randint(20, 70),
            })

    def _tick(self):
        self._pulse_phase = (self._pulse_phase + 0.03) % (2 * math.pi)
        t = (math.sin(self._pulse_phase) + 1) / 2
        alpha = int(30 + 90 * t)
        self._card.set_glow(alpha, self._hovering)
        # Update particles
        for p in self._particles:
            p["y"] -= p["speed"]
            if p["y"] < -5:
                p["y"] = 385
                p["x"] = random.uniform(0, 560)
        self._card.update()

    def _restore_icon(self):
        if self._icon_pix_normal is not None:
            self._icon_lbl.setPixmap(self._icon_pix_normal)
        else:
            self._icon_lbl.setText("🎧")

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._hovering = True
            self._card.set_glow(200, True)
            self._icon_lbl.setText("📂")

    def dragLeaveEvent(self, e):
        self._hovering = False
        self._card.set_glow(40, False)
        self._restore_icon()

    def dropEvent(self, e: QDropEvent):
        self._hovering = False
        self._card.set_glow(40, False)
        self._restore_icon()
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in AUDIO_EXTS:
                self.file_dropped.emit(path)
                break

    def _open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona un tema de audio", "",
            "Audio (*.wav *.mp3 *.flac *.aiff *.aif *.m4a)"
        )
        if path:
            self.file_dropped.emit(path)


# ── Stat Card ─────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    """Tarjeta de estadística individual con valor grande y etiqueta."""
    def __init__(self, label: str, value: str = "—",
                 accent: str = TEXT, parent=None):
        super().__init__(parent)
        self._accent = accent
        self.setStyleSheet(f"""
            QFrame {{
                background: {BG3};
                border-radius: 8px;
                border: 1px solid {BORDER};
                border-top: 2px solid {accent};
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignCenter)

        self._val_lbl = QLabel(value)
        self._val_lbl.setAlignment(Qt.AlignCenter)
        self._val_lbl.setStyleSheet(
            f"color: {accent}; font-size: 16px; font-weight: 800;"
            "background: transparent; border: none;"
        )
        lay.addWidget(self._val_lbl)

        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 8px; font-weight: 700;"
            "letter-spacing: 1.5px; background: transparent; border: none;"
        )
        lay.addWidget(lbl)

    def set_value(self, v: str):
        self._val_lbl.setText(v)

    def set_accent(self, color: str):
        self._accent = color
        self.setStyleSheet(f"""
            QFrame {{
                background: {BG3};
                border-radius: 8px;
                border: 1px solid {BORDER};
                border-top: 2px solid {color};
            }}
        """)
        self._val_lbl.setStyleSheet(
            f"color: {color}; font-size: 16px; font-weight: 800;"
            "background: transparent; border: none;"
        )


# ── Shimmer Button ─────────────────────────────────────────────────────────────

class ShimmerButton(QPushButton):
    """Botón con efecto shimmer animado cuando está activo (auto-stop tras 3 ciclos)."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._shimmer_pos = -1.0
        self._shimmer_cycles = 0
        self._anim_timer  = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_shimmer)
        self._enabled_state = True

    def start_shimmer(self):
        self._shimmer_pos = -1.0
        self._shimmer_cycles = 0
        self._anim_timer.start(25)

    def stop_shimmer(self):
        self._anim_timer.stop()
        self._shimmer_pos = -1.0
        self._shimmer_cycles = 0
        self.update()

    def _tick_shimmer(self):
        self._shimmer_pos += 0.04
        if self._shimmer_pos > 2.0:
            self._shimmer_pos = -1.0
            self._shimmer_cycles += 1
            if self._shimmer_cycles >= 3:
                self.stop_shimmer()
                return
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._shimmer_pos < 0 or not self.isEnabled():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx = int(self._shimmer_pos * w)
        grad = QLinearGradient(cx - 60, 0, cx + 60, h)
        grad.setColorAt(0.0, QColor(255, 255, 255, 0))
        grad.setColorAt(0.5, QColor(255, 255, 255, 45))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 12, 12)
        p.setClipPath(path)
        p.fillRect(0, 0, w, h, QBrush(grad))
# ── Gestión de Carátula y Firma (Drag & Drop + Metadatos) ─────────────────────

class CoverDropArea(QFrame):
    """
    Área visual para la carátula oficial o personalizada:
    - Soporta Drag & Drop directo de imágenes (.jpg, .jpeg, .png, .webp).
    - Clic para abrir el selector de archivos del sistema.
    - Previsualización recortada/centrada con bordes redondeados.
    - Botón para restaurar la carátula oficial.
    """
    cover_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedSize(94, 94)
        self._current_path: str = ""
        self._default_pixmap: QPixmap | None = None
        self._is_hovered = False

        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Haz clic o arrastra una imagen para personalizar la carátula de tus previas")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._lbl_preview = QLabel()
        self._lbl_preview.setAlignment(Qt.AlignCenter)
        self._lbl_preview.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(self._lbl_preview)

        self._load_default()
        self._update_style()

    def _load_default(self):
        assets = _ASSETS_DIR
        for name in ["logo_emblem.png", "logo_emblem_red.png", "logo_banner.png"]:
            p = assets / name
            if p.exists() and p.is_file():
                pm = QPixmap(str(p))
                if not pm.isNull():
                    self._default_pixmap = pm.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self._lbl_preview.setPixmap(self._default_pixmap)
                    break

    def _update_style(self):
        border_c = ACCENT if self._is_hovered else (BORDER_HV if self._current_path else BORDER)
        bg = BG4 if self._is_hovered else BG3
        border_type = "dashed" if self._is_hovered else "solid"
        self.setStyleSheet(f"""
            CoverDropArea {{
                background: {bg};
                border: 2px {border_type} {border_c};
                border-radius: 10px;
            }}
        """)

    def set_cover(self, path: str):
        p = Path(path).resolve() if path else None
        if p and p.exists() and p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
            pm = QPixmap(str(p))
            if not pm.isNull():
                self._current_path = str(p)
                scaled = pm.scaled(86, 86, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                rect = QRect((scaled.width() - 86) // 2, (scaled.height() - 86) // 2, 86, 86)
                cropped = scaled.copy(rect)
                self._lbl_preview.setPixmap(cropped)
                self._update_style()
                self.cover_changed.emit(self._current_path)
                return

        self._current_path = ""
        if self._default_pixmap:
            self._lbl_preview.setPixmap(self._default_pixmap)
        self._update_style()
        self.cover_changed.emit("")

    def get_cover_path(self) -> str:
        return self._current_path

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    self._is_hovered = True
                    self._update_style()
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._is_hovered = False
        self._update_style()

    def dropEvent(self, event: QDropEvent):
        self._is_hovered = False
        self._update_style()
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                p = Path(url.toLocalFile())
                if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    self.set_cover(str(p))
                    event.acceptProposedAction()
                    return

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            fpath, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar carátula para la previa", "",
                "Imágenes (*.png *.jpg *.jpeg *.webp);;Todos los archivos (*.*)"
            )
            if fpath:
                self.set_cover(fpath)


class BrandingCard(QFrame):
    """
    Panel compacto de firma de audio y metadatos oficiales / personalizados.
    Permite arrastrar o seleccionar carátula, asignar artista, sello, colección, comentario y BPM.
    """
    signature_changed = Signal()

    def __init__(self, cfg: dict | None = None, parent=None):
        super().__init__(parent)
        self._cfg = cfg or {}
        self.setStyleSheet(f"""
            BrandingCard {{
                background: {BG2};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        # ── Header ──────────────────────────────────────────────
        h_row = QHBoxLayout()
        h_row.setSpacing(6)

        lbl_icon = QLabel("🏷️")
        lbl_icon.setStyleSheet("font-size: 13px; background: transparent; border: none;")
        h_row.addWidget(lbl_icon)

        lbl_t = QLabel("FIRMA & CARÁTULA PERSONALIZADA")
        lbl_t.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9.5px; font-weight: 700;"
            "letter-spacing: 1px; background: transparent; border: none;"
        )
        h_row.addWidget(lbl_t)

        self._badge = QLabel("OFICIAL")
        self._badge.setStyleSheet(f"""
            background: {BG4}; color: {TEXT_SUB};
            font-size: 8.5px; font-weight: 700;
            padding: 2px 6px; border-radius: 4px; border: 1px solid {BORDER};
        """)
        h_row.addWidget(self._badge)

        h_row.addStretch()

        self._btn_reset_cover = QPushButton("Restablecer portada")
        self._btn_reset_cover.setFixedHeight(20)
        self._btn_reset_cover.setStyleSheet(_btn(BG3, TEXT_DIM, BG4, radius=4, fs=9.5))
        self._btn_reset_cover.setCursor(Qt.PointingHandCursor)
        self._btn_reset_cover.setVisible(False)
        self._btn_reset_cover.clicked.connect(self._on_reset_cover)
        h_row.addWidget(self._btn_reset_cover)

        lay.addLayout(h_row)

        # ── Body (Carátula a la izquierda + Campos a la derecha) ─
        b_row = QHBoxLayout()
        b_row.setSpacing(10)

        # Drop area
        self._drop_area = CoverDropArea(self)
        self._drop_area.cover_changed.connect(self._on_cover_changed)
        b_row.addWidget(self._drop_area)

        # Form fields
        form_col = QVBoxLayout()
        form_col.setSpacing(4)

        row_f1 = QHBoxLayout()
        row_f1.setSpacing(6)

        self._edit_artist = QLineEdit()
        self._edit_artist.setPlaceholderText("Artista / DJ (ej. Radical Records)")
        self._edit_artist.setStyleSheet(_input_style())
        self._edit_artist.setFixedHeight(26)
        row_f1.addWidget(self._edit_artist)

        self._edit_label = QLineEdit()
        self._edit_label.setPlaceholderText("Sello / Discográfica (ej. Radical Records)")
        self._edit_label.setStyleSheet(_input_style())
        self._edit_label.setFixedHeight(26)
        row_f1.addWidget(self._edit_label)
        form_col.addLayout(row_f1)

        row_f2 = QHBoxLayout()
        row_f2.setSpacing(6)

        self._edit_album = QLineEdit()
        self._edit_album.setPlaceholderText("Álbum / Colección (ej. Radical Previews 2026)")
        self._edit_album.setStyleSheet(_input_style())
        self._edit_album.setFixedHeight(26)
        row_f2.addWidget(self._edit_album)

        self._edit_genre = QLineEdit()
        self._edit_genre.setPlaceholderText("Género (ej. Tech House / Electronic)")
        self._edit_genre.setStyleSheet(_input_style())
        self._edit_genre.setFixedHeight(26)
        row_f2.addWidget(self._edit_genre)
        form_col.addLayout(row_f2)

        row_f3 = QHBoxLayout()
        row_f3.setSpacing(6)

        self._edit_comment = QLineEdit()
        self._edit_comment.setPlaceholderText("Comentario / Promo (ej. Previa Exclusiva · Solo para sets)")
        self._edit_comment.setStyleSheet(_input_style())
        self._edit_comment.setFixedHeight(26)
        row_f3.addWidget(self._edit_comment)
        form_col.addLayout(row_f3)

        row_f4 = QHBoxLayout()
        row_f4.setSpacing(8)

        chk_s = f"""
            QCheckBox {{
                color: {TEXT_SUB};
                font-size: 10px;
                font-weight: 500;
                spacing: 4px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 12px; height: 12px;
                border: 1px solid {BORDER};
                border-radius: 3px;
                background: {BG3};
            }}
            QCheckBox::indicator:checked {{
                background: {ACCENT};
                border-color: {ACCENT};
            }}
        """
        self._chk_remember = QCheckBox("Guardar firma y carátula como predeterminada")
        self._chk_remember.setStyleSheet(chk_s)
        self._chk_remember.setChecked(self._cfg.get("save_signature_default", False))
        row_f4.addWidget(self._chk_remember)
        row_f4.addStretch()

        form_col.addLayout(row_f4)
        b_row.addLayout(form_col, stretch=1)
        lay.addLayout(b_row)

        self.load_from_cfg(self._cfg)

    def load_from_cfg(self, cfg: dict):
        if not cfg:
            return
        self._cfg = cfg
        self._edit_artist.setText(cfg.get("tag_artist", ""))
        self._edit_label.setText(cfg.get("tag_label", ""))
        self._edit_album.setText(cfg.get("tag_album", ""))
        self._edit_genre.setText(cfg.get("tag_genre", "Electronic"))
        self._edit_comment.setText(cfg.get("tag_comment", "AutoPrevias · Radical Records Studio"))
        self._chk_remember.setChecked(cfg.get("save_signature_default", False))

        # Prioridad: 1) custom_cover_path guardado por el usuario, 2) cover_path de sesión (embebida)
        cpath = cfg.get("custom_cover_path", "") or cfg.get("cover_path", "")
        if cpath and Path(cpath).exists():
            self._drop_area.set_cover(cpath)

    def _on_cover_changed(self, path: str):
        if path:
            self._badge.setText("PERSONALIZADA")
            self._badge.setStyleSheet(f"""
                background: {GREEN}22; color: {GREEN};
                font-size: 8.5px; font-weight: 700;
                padding: 2px 6px; border-radius: 4px; border: 1px solid {GREEN}44;
            """)
            self._btn_reset_cover.setVisible(True)
        else:
            self._badge.setText("OFICIAL")
            self._badge.setStyleSheet(f"""
                background: {BG4}; color: {TEXT_SUB};
                font-size: 8.5px; font-weight: 700;
                padding: 2px 6px; border-radius: 4px; border: 1px solid {BORDER};
            """)
            self._btn_reset_cover.setVisible(False)
        self.signature_changed.emit()

    def _on_reset_cover(self):
        self._drop_area.set_cover("")

    def get_metadata(self) -> dict:
        return {
            "artist":  self._edit_artist.text().strip(),
            "label":   self._edit_label.text().strip(),
            "album":   self._edit_album.text().strip(),
            "genre":   self._edit_genre.text().strip() or "Electronic",
            "comment": self._edit_comment.text().strip() or "AutoPrevias · Radical Records Studio",
            "remember": self._chk_remember.isChecked(),
        }

    def get_cover_path(self) -> str:
        return self._drop_area.get_cover_path()

    def persist_if_requested(self):
        if self._chk_remember.isChecked():
            c = load_cfg()
            c["tag_artist"]  = self._edit_artist.text().strip()
            c["tag_label"]   = self._edit_label.text().strip()
            c["tag_album"]   = self._edit_album.text().strip()
            c["tag_genre"]   = self._edit_genre.text().strip()
            c["tag_comment"] = self._edit_comment.text().strip()
            c["save_signature_default"] = True

            cover_p = self._drop_area.get_cover_path()
            if cover_p:
                saved_cover = save_custom_cover(cover_p)
                c["custom_cover_path"] = saved_cover
            else:
                c["custom_cover_path"] = ""

            # Persistir también las preferencias de exportación del ResultPanel padre
            parent = self.parent()
            while parent is not None and not hasattr(parent, "_combo_speed_mode"):
                parent = parent.parent() if hasattr(parent, "parent") else None
            if parent and hasattr(parent, "_combo_speed_mode"):
                c["speed_mode"]    = parent._combo_speed_mode.currentData()
                c["video_palette"] = parent._combo_video_pal.currentData()
                c["aspect_ratio"]  = parent._combo_aspect.currentData()

            save_cfg(c)


# ── Panel de resultados ───────────────────────────────────────────────────────


class ResultPanel(QWidget):
    regen_requested       = Signal(int)   # con seed
    folder_requested      = Signal()
    open_folder_requested = Signal()
    new_file_requested    = Signal()
    load_file_requested   = Signal(str)   # path de nuevo audio a cargar directamente
    generate_requested    = Signal()
    play_requested        = Signal(str)   # path del archivo para reproducir

    def __init__(self):
        super().__init__()
        self._analysis         = None
        self._plan             = None
        self._out_path         = ""
        self._source_path      = ""
        self._bpm              = 0.0
        self._last_seed        = 0
        self._generated_paths  = []
        self._last_default_name = ""
        self._tempo_mode       = "auto"
        self._tempo_events     = []
        self._tempo_plot       = None
        self._tempo_curve_item = None
        self._tempo_base_line  = None
        self._key_res          = None
        self._key_str          = ""
        self._voice_drop_path     = ""
        self._voice_drop_time_sec = -1.0  # -1 = usar cálculo automático
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(0, 0, 0, 0)

        # ── 1. WAVEFORM ───────────────────────────────────────────────────
        wave_frame = QFrame()
        wave_frame.setStyleSheet(f"""
            QFrame {{
                background: {BG2};
                border-radius: 12px;
                border: 1px solid {BORDER};
            }}
        """)
        wave_lay = QVBoxLayout(wave_frame)
        wave_lay.setContentsMargins(6, 6, 6, 3)
        wave_lay.setSpacing(0)

        if HAS_WAVEFORM:
            self._waveform = WaveformWidget()
            self._waveform.setMinimumHeight(135)
            self._waveform.seek_requested.connect(self._on_waveform_seek)
            self._waveform.boundaries_changed.connect(self._on_boundaries_changed)
            self._waveform.cuts_changed.connect(self._on_waveform_cuts_changed)
            self._waveform.voice_drop_moved.connect(self._on_voice_drop_marker_moved)
            wave_lay.addWidget(self._waveform)
        else:
            placeholder = QLabel("Instala pyqtgraph para ver la forma de onda")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setFixedHeight(70)
            placeholder.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 11px; background: transparent; border: none;"
            )
            wave_lay.addWidget(placeholder)

        root.addWidget(wave_frame)

        # ── 2. REPRODUCTOR ────────────────────────────────────────────────
        if HAS_PLAYER:
            player_frame = QFrame()
            player_frame.setStyleSheet(f"""
                QFrame {{
                    background: {BG2};
                    border-radius: 10px;
                    border: 1px solid {BORDER};
                }}
            """)
            pl = QVBoxLayout(player_frame)
            pl.setContentsMargins(10, 5, 10, 5)
            self._player = PlayerWidget()
            if HAS_WAVEFORM:
                self._player.position_changed.connect(self._waveform.set_playhead)
                self._player.track_switched.connect(self._on_track_switched)
            pl.addWidget(self._player)
            root.addWidget(player_frame)
        else:
            self._player = None

        # ── 3. STATS STRIP ────────────────────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(6)

        self._card_file  = StatCard("ARCHIVO",   "—",   TEXT)
        self._card_bpm   = StatCard("BPM",       "—",   ACCENT)
        self._card_key   = StatCard("CLAVE / CAMELOT", "—", "#a855f7")
        self._card_dur   = StatCard("DURACIÓN",  "—",   TEXT)
        self._card_drops = StatCard("DROPS",     "—",   GREEN)
        self._card_pv    = StatCard("PREVIA EST.", "—", WARN)

        for card in (self._card_file, self._card_bpm, self._card_key, self._card_dur,
                     self._card_drops, self._card_pv):
            stats_row.addWidget(card)

        root.addLayout(stats_row)

        # ── 3.1 PRESETS DE DURACIÓN ───────────────────────────────────────
        preset_frame = QFrame()
        preset_frame.setStyleSheet(f"""
            QFrame {{
                background: {BG2};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)
        p_lay = QHBoxLayout(preset_frame)
        p_lay.setContentsMargins(10, 5, 10, 5)
        p_lay.setSpacing(8)

        lbl_pre = QLabel("⚡ PRESETS:")
        lbl_pre.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; font-weight: 800; letter-spacing: 0.8px; border: none; background: transparent;")
        p_lay.addWidget(lbl_pre)

        self._btn_p15  = QPushButton("⚡ 15s (Teaser)")
        self._btn_p30  = QPushButton("📻 30s (Promo)")
        self._btn_p60  = QPushButton("🚀 60s (Extended)")
        self._btn_p120 = QPushButton("🔥 120s / 2 Min (Club · Defecto)")

        self._preset_buttons = [
            (self._btn_p15, 15),
            (self._btn_p30, 30),
            (self._btn_p60, 60),
            (self._btn_p120, 120),
        ]

        for btn, sec in self._preset_buttons:
            btn.setFixedHeight(24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, s=sec: self._apply_duration_preset(s))
            p_lay.addWidget(btn)

        self._active_preset_sec = 120
        self._update_preset_styles(120)

        p_lay.addStretch()
        root.addWidget(preset_frame)

        # ── 4. PANEL SIMPLE POR DEFECTO + TOGGLE MODO AVANZADO ────────────
        self._simple_box = QFrame()
        self._simple_box.setStyleSheet(f"""
            QFrame {{
                background: {BG2};
                border: 1px solid {BORDER};
                border-radius: 10px;
                border-left: 3px solid {ACCENT};
            }}
        """)
        sb_lay = QHBoxLayout(self._simple_box)
        sb_lay.setContentsMargins(12, 8, 12, 8)
        sb_lay.setSpacing(10)

        icon_ai = QLabel("✨")
        icon_ai.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        sb_lay.addWidget(icon_ai)

        sb_col = QVBoxLayout()
        sb_col.setSpacing(1)
        lbl_ai_t = QLabel("Estructura de previa optimizada")
        lbl_ai_t.setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: 700; background: transparent; border: none;")
        sb_col.addWidget(lbl_ai_t)

        self._lbl_simple_desc = QLabel("3 cortes listos · Arrastra en la onda para retocar o pulsa abajo en Generar Previa")
        self._lbl_simple_desc.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10.5px; background: transparent; border: none;")
        sb_col.addWidget(self._lbl_simple_desc)
        sb_lay.addLayout(sb_col, stretch=1)

        # Toggle de opciones avanzadas
        self._chk_advanced = QCheckBox("⚙️  Personalizar Cortes & BPM")
        self._chk_advanced.setCursor(Qt.PointingHandCursor)
        self._chk_advanced.setStyleSheet(f"""
            QCheckBox {{
                color: {TEXT_SUB};
                font-size: 11px;
                font-weight: 700;
                spacing: 6px;
                background: {BG3};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 5px 9px;
            }}
            QCheckBox:hover {{
                border-color: {ACCENT};
                color: {TEXT};
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {BORDER};
                border-radius: 3px;
                background: {BG2};
            }}
            QCheckBox::indicator:checked {{
                background: {ACCENT};
                border-color: {ACCENT};
            }}
        """)
        self._chk_advanced.toggled.connect(self._on_toggle_advanced)
        sb_lay.addWidget(self._chk_advanced)

        root.addWidget(self._simple_box)

        # ── 5. TABS AVANZADAS (Ocultas por defecto) ───────────────────────
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(_tab_style())
        self._tabs.setMinimumHeight(160)

        self._tabs.addTab(self._build_cuts_tab(), "  ✂️ Editor de Cortes  ")
        self._tabs.addTab(self._build_tempo_tab(), "  ⚡ Variación de BPM  ")
        self._tbl_structure = self._make_table(
            ["TIPO", "INICIO", "FIN", "DUR", "LUFS", "PEAK dBFS"]
        )
        self._tabs.addTab(self._tbl_structure, "  📊 Estructura Musical  ")
        self._tabs.setVisible(False)  # Super simple por defecto
        root.addWidget(self._tabs, stretch=1)

        # ── 5. PANEL DE EXPORTACIÓN ───────────────────────────────────────
        exp_frame = QFrame()
        exp_frame.setStyleSheet(f"""
            QFrame {{
                background: {BG2};
                border-radius: 10px;
                border: 1px solid {BORDER};
            }}
        """)
        exp_lay = QVBoxLayout(exp_frame)
        exp_lay.setContentsMargins(12, 6, 12, 6)
        exp_lay.setSpacing(5)

        # Fila nombre + formato
        row_name = QHBoxLayout()
        row_name.setSpacing(6)

        lbl_n = QLabel("Nombre")
        lbl_n.setFixedWidth(52)
        lbl_n.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9.5px; font-weight: 700;"
            "letter-spacing: 0.8px; background: transparent; border: none;"
        )
        self._edit_name = QLineEdit()
        self._edit_name.setPlaceholderText("PREVIA - NombreOriginal")
        self._edit_name.setFixedHeight(28)
        self._edit_name.setStyleSheet(_input_style())

        chk_style = f"""
            QCheckBox {{
                color: {TEXT};
                font-size: 11px;
                font-weight: 600;
                spacing: 5px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {BORDER};
                border-radius: 3px;
                background: {BG3};
            }}
            QCheckBox::indicator:checked {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {ACCENT}, stop:1 {ACCENT2});
                border-color: {ACCENT};
            }}
        """
        self._chk_wav = QCheckBox("WAV 24b")
        self._chk_wav.setStyleSheet(chk_style)
        self._chk_wav.setChecked(True)
        self._chk_mp3 = QCheckBox("MP3 320k")
        self._chk_mp3.setStyleSheet(chk_style)
        self._chk_mp3.setChecked(True)
        self._chk_flac = QCheckBox("FLAC")
        self._chk_flac.setStyleSheet(chk_style)
        self._chk_flac.setChecked(False)
        self._chk_video = QCheckBox("🎬 Vídeo 9:16 (TikTok/Reels)")
        self._chk_video.setStyleSheet(f"""
            QCheckBox {{
                color: #c084fc;
                font-size: 11px;
                font-weight: 700;
                spacing: 5px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid #9333ea;
                border-radius: 3px;
                background: {BG3};
            }}
            QCheckBox::indicator:checked {{
                background: #a855f7;
                border-color: #a855f7;
            }}
        """)
        self._chk_video.setChecked(False)

        row_name.addWidget(lbl_n)
        row_name.addWidget(self._edit_name, stretch=1)
        row_name.addSpacing(6)
        row_name.addWidget(self._chk_wav)
        row_name.addSpacing(4)
        row_name.addWidget(self._chk_mp3)
        row_name.addSpacing(4)
        row_name.addWidget(self._chk_flac)
        row_name.addSpacing(4)
        row_name.addWidget(self._chk_video)
        exp_lay.addLayout(row_name)

        # Fila Efectos de Estudio y Modo DJ v2.0
        row_fx = QHBoxLayout()
        row_fx.setSpacing(8)
        lbl_fx = QLabel("Efectos")
        lbl_fx.setFixedWidth(52)
        lbl_fx.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9.5px; font-weight: 700;"
            "letter-spacing: 0.8px; background: transparent; border: none;"
        )
        self._chk_fx_flanger = QCheckBox("🎛️ Flanger")
        self._chk_fx_flanger.setStyleSheet(chk_style)
        self._chk_fx_flanger.setToolTip("Aplica un efecto Flanger analógico estéreo con modulación LFO")

        self._chk_fx_filter = QCheckBox("🌊 Filter Sweep")
        self._chk_fx_filter.setStyleSheet(chk_style)
        self._chk_fx_filter.setToolTip("Aplica un barrido de filtro dinámico para generar tensión en las subidas")

        self._chk_fx_master = QCheckBox("🔊 Master LUFS")
        self._chk_fx_master.setStyleSheet(f"""
            QCheckBox {{
                color: {GREEN};
                font-size: 11px;
                font-weight: 700;
                spacing: 5px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {BORDER};
                border-radius: 3px;
                background: {BG3};
            }}
            QCheckBox::indicator:checked {{
                background: {GREEN};
                border-color: {GREEN};
            }}
        """)
        self._chk_fx_master.setChecked(True)
        self._chk_fx_master.setToolTip("Normalización y limitador analógico transparente (-9 LUFS Club / Beatport)")

        # Modo DJ v2.0: Vinilo (+Pitch Armónico) vs Keylock
        self._combo_speed_mode = QComboBox()
        self._combo_speed_mode.setFixedHeight(24)
        self._combo_speed_mode.setStyleSheet(_input_style())
        self._combo_speed_mode.addItem("💿 Vinilo (+Pitch Armónico)", "vinyl")
        self._combo_speed_mode.addItem("🔒 Keylock (Tono Original)", "keylock")
        self._combo_speed_mode.setToolTip("Modo de aceleración: Vinilo analógico (el pitch sube y baja armónicamente al acelerar) o Keylock digital (Rubber Band congela el tono)")

        self._btn_voice_drop = QPushButton("🎙️ Voice Drop…")
        self._btn_voice_drop.setFixedHeight(22)
        self._btn_voice_drop.setStyleSheet(_btn(BG4, TEXT_MID, BG5, radius=4, fs=10))
        self._btn_voice_drop.setCursor(Qt.PointingHandCursor)
        self._btn_voice_drop.setToolTip("Superponer firma de voz o jingle de DJ sobre la previa")
        self._btn_voice_drop.clicked.connect(self._select_voice_drop)

        self._combo_voice_pos = QComboBox()
        self._combo_voice_pos.setFixedHeight(22)
        self._combo_voice_pos.setStyleSheet(_input_style())
        self._combo_voice_pos.addItem("📍 Pre-Drop", "predrop")
        self._combo_voice_pos.addItem("📍 Intro", "intro")
        self._combo_voice_pos.addItem("🎯 Manual (arrastrar)", "manual")
        self._combo_voice_pos.setToolTip("Momento de inserción: Pre-Drop, Intro, o arrastrar el marcador dorado en la forma de onda")

        self._lbl_voice_drop = QLabel("")
        self._lbl_voice_drop.setStyleSheet(f"color: {GREEN}; font-size: 10px; font-weight: 600; background: transparent; border: none;")

        row_fx.addWidget(lbl_fx)
        row_fx.addWidget(self._chk_fx_flanger)
        row_fx.addWidget(self._chk_fx_filter)
        row_fx.addWidget(self._chk_fx_master)
        row_fx.addWidget(self._combo_speed_mode)
        row_fx.addSpacing(4)
        row_fx.addWidget(self._btn_voice_drop)
        row_fx.addWidget(self._combo_voice_pos)
        row_fx.addWidget(self._lbl_voice_drop)
        row_fx.addStretch()
        exp_lay.addLayout(row_fx)

        # Fila Opciones de Vídeo Viral v2.0 (Apartado 2: 3 y 4)
        self._row_video_widget = QWidget()
        row_video = QHBoxLayout(self._row_video_widget)
        row_video.setContentsMargins(0, 0, 0, 0)
        row_video.setSpacing(8)
        lbl_vopt = QLabel("Vídeo 2.0")
        lbl_vopt.setFixedWidth(52)
        lbl_vopt.setStyleSheet(
            f"color: #c084fc; font-size: 9.5px; font-weight: 700;"
            "letter-spacing: 0.8px; background: transparent; border: none;"
        )
        self._combo_video_pal = QComboBox()
        self._combo_video_pal.setFixedHeight(24)
        self._combo_video_pal.setStyleSheet(_input_style())
        self._combo_video_pal.addItem("⚡ Cian & Magenta Radical", "radical")
        self._combo_video_pal.addItem("🟢 Verde Neón Rave", "rave")
        self._combo_video_pal.addItem("🔥 Rojo Carmesí Studio", "crimson")
        self._combo_video_pal.addItem("🟡 Ámbar Gold & Solar", "amber")
        self._combo_video_pal.addItem("🟣 Cyber Violet", "cyber")
        self._combo_video_pal.setToolTip("Paleta de color neón del analizador FFT y osciloscopio en el vídeo")

        self._edit_promo = QLineEdit()
        self._edit_promo.setPlaceholderText("Banner: RADICAL RECORDS · PROMO EXCLUSIVA")
        self._edit_promo.setFixedHeight(24)
        self._edit_promo.setStyleSheet(_input_style())
        self._edit_promo.setToolTip("Texto del banner promocional visible en el vídeo")

        self._combo_aspect = QComboBox()
        self._combo_aspect.setFixedHeight(24)
        self._combo_aspect.setStyleSheet(_input_style())
        self._combo_aspect.addItem("📱 9:16 (TikTok/Reels/Shorts)", "9:16")
        self._combo_aspect.addItem("⏹️ 1:1 (Post Cuadrado)", "1:1")

        row_video.addWidget(lbl_vopt)
        row_video.addWidget(self._combo_video_pal)
        row_video.addWidget(self._edit_promo, stretch=1)
        row_video.addWidget(self._combo_aspect)
        self._row_video_widget.setVisible(False)
        exp_lay.addWidget(self._row_video_widget)

        self._chk_video.toggled.connect(self._row_video_widget.setVisible)
        self._combo_voice_pos.currentIndexChanged.connect(
            lambda _: self._update_voice_drop_marker()
        )

        # Fila carpeta
        row_folder = QHBoxLayout()
        row_folder.setSpacing(6)
        lbl_f = QLabel("Carpeta")
        lbl_f.setFixedWidth(52)
        lbl_f.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9.5px; font-weight: 700;"
            "letter-spacing: 0.8px; background: transparent; border: none;"
        )
        self._lbl_folder_path = QLabel("—")
        self._lbl_folder_path.setStyleSheet(
            f"color: {TEXT_MID}; font-size: 11px; background: transparent; border: none;"
        )
        self._btn_folder = QPushButton("Cambiar")
        self._btn_folder.setFixedSize(60, 24)
        self._btn_folder.setStyleSheet(_btn(BG4, TEXT_MID, BG5, radius=5, fs=10.5))
        self._btn_folder.setCursor(Qt.PointingHandCursor)
        self._btn_folder.setToolTip("Cambiar la carpeta de destino donde se guardan las previas")
        self._btn_folder.clicked.connect(self.folder_requested.emit)

        self._btn_open_folder = QPushButton("📂 Abrir")
        self._btn_open_folder.setFixedSize(60, 24)
        self._btn_open_folder.setStyleSheet(_btn(BG4, TEXT_MID, BG5, radius=5, fs=10.5))
        self._btn_open_folder.setCursor(Qt.PointingHandCursor)
        self._btn_open_folder.setToolTip("Abrir la carpeta de destino en Finder / Explorador de archivos")
        self._btn_open_folder.clicked.connect(self.open_folder_requested.emit)

        row_folder.addWidget(lbl_f)
        row_folder.addWidget(self._lbl_folder_path, stretch=1)
        row_folder.addWidget(self._btn_folder)
        row_folder.addWidget(self._btn_open_folder)
        exp_lay.addLayout(row_folder)

        root.addWidget(exp_frame)

        # ── 5.1 FIRMA & CARÁTULA PERSONALIZADA ─────────────────────────────
        self._branding_card = BrandingCard(load_cfg(), parent=self)
        root.addWidget(self._branding_card)

        # ── 6. SEED + CONTROLES ───────────────────────────────────────────
        seed_row = QHBoxLayout()
        seed_row.setSpacing(6)

        self._btn_new = QPushButton("← Nuevo track")
        self._btn_new.setFixedHeight(28)
        self._btn_new.setStyleSheet(_btn(BG3, TEXT_SUB, BG4, radius=7, fs=11))
        self._btn_new.setCursor(Qt.PointingHandCursor)
        self._btn_new.clicked.connect(self.new_file_requested.emit)
        seed_row.addWidget(self._btn_new)

        seed_row.addStretch()

        # Seed
        lbl_seed = QLabel("Seed:")
        lbl_seed.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 10px; font-weight: 700;"
            "background: transparent; border: none; letter-spacing: 0.5px;"
        )
        seed_row.addWidget(lbl_seed)

        self._spin_seed = QSpinBox()
        self._spin_seed.setRange(0, 99999)
        self._spin_seed.setValue(0)
        self._spin_seed.setFixedSize(80, 26)
        self._spin_seed.setStyleSheet(_input_style())
        self._spin_seed.setToolTip("Semilla de aleatoriedad — misma seed = misma variación de tempo")
        self._spin_seed.valueChanged.connect(self._on_seed_changed)
        seed_row.addWidget(self._spin_seed)

        self._btn_random_seed = QPushButton("🎲")
        self._btn_random_seed.setFixedSize(28, 26)
        self._btn_random_seed.setToolTip("Semilla aleatoria")
        self._btn_random_seed.setStyleSheet(_btn(BG3, TEXT, BG4, radius=6, fs=12))
        self._btn_random_seed.setCursor(Qt.PointingHandCursor)
        self._btn_random_seed.clicked.connect(self._randomize_seed)
        seed_row.addWidget(self._btn_random_seed)

        self._btn_regen = QPushButton("⟳  Regenerar con seed")
        self._btn_regen.setFixedHeight(26)
        self._btn_regen.setStyleSheet(
            _btn(BG3, ACCENT, BG4, radius=7, fs=11, border=ACCENT + "44")
        )
        self._btn_regen.setCursor(Qt.PointingHandCursor)
        self._btn_regen.clicked.connect(self._on_regen)
        seed_row.addWidget(self._btn_regen)

        root.addLayout(seed_row)

        # ── 7. BOTÓN GENERAR (shimmer) ────────────────────────────────────
        self._btn_generate = ShimmerButton("▶   GENERAR PREVIA")
        self._btn_generate.setFixedHeight(46)
        self._btn_generate.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._btn_generate.setCursor(Qt.PointingHandCursor)
        self._btn_generate.setEnabled(False)
        self._apply_generate_style(False)
        self._btn_generate.clicked.connect(self.generate_requested.emit)
        root.addWidget(self._btn_generate)

        # ── 7b. TARJETA DE CONFIRMACIÓN DE EXPORTACIÓN ───────────────────────
        self._card_export_success = QFrame()
        self._card_export_success.setStyleSheet(f"""
            QFrame {{
                background: {BG2};
                border: 1px solid {GREEN};
                border-radius: 9px;
            }}
        """)
        card_lay = QVBoxLayout(self._card_export_success)
        card_lay.setContentsMargins(14, 10, 14, 10)
        card_lay.setSpacing(6)

        hdr_row = QHBoxLayout()
        lbl_succ_icon = QLabel("✅")
        lbl_succ_icon.setStyleSheet("font-size: 16px; border: none; background: transparent;")
        hdr_row.addWidget(lbl_succ_icon)

        self._lbl_succ_title = QLabel("¡Previa y contenido exportados con éxito!")
        self._lbl_succ_title.setStyleSheet(f"color: {GREEN}; font-size: 12px; font-weight: 800; border: none; background: transparent;")
        hdr_row.addWidget(self._lbl_succ_title, stretch=1)

        btn_close_succ = QPushButton("✕")
        btn_close_succ.setFixedSize(20, 20)
        btn_close_succ.setStyleSheet(_btn(BG3, TEXT_DIM, BG4, radius=4, fs=10))
        btn_close_succ.setCursor(Qt.PointingHandCursor)
        btn_close_succ.clicked.connect(lambda: self._card_export_success.setVisible(False))
        hdr_row.addWidget(btn_close_succ)
        card_lay.addLayout(hdr_row)

        self._lbl_succ_files = QLabel("")
        self._lbl_succ_files.setStyleSheet(f"color: {TEXT}; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        self._lbl_succ_files.setWordWrap(True)
        card_lay.addWidget(self._lbl_succ_files)

        self._lbl_succ_dir = QLabel("")
        self._lbl_succ_dir.setStyleSheet(f"color: {TEXT_MID}; font-size: 10.5px; border: none; background: transparent;")
        self._lbl_succ_dir.setWordWrap(True)
        card_lay.addWidget(self._lbl_succ_dir)

        act_row = QHBoxLayout()
        self._btn_succ_open = QPushButton("📂 Abrir Carpeta")
        self._btn_succ_open.setFixedHeight(28)
        self._btn_succ_open.setStyleSheet(f"""
            QPushButton {{
                background: {GREEN};
                color: #000000;
                font-size: 11px;
                font-weight: 800;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background: #34d399;
            }}
        """)
        self._btn_succ_open.setCursor(Qt.PointingHandCursor)
        self._btn_succ_open.clicked.connect(self.open_folder_requested.emit)
        act_row.addWidget(self._btn_succ_open)

        self._btn_succ_new = QPushButton("🎵  Generar otra previa")
        self._btn_succ_new.setFixedHeight(28)
        self._btn_succ_new.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT};
                color: #ffffff;
                font-size: 11px;
                font-weight: 800;
                border: none;
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: #ff4d63;
            }}
        """)
        self._btn_succ_new.setCursor(Qt.PointingHandCursor)
        self._btn_succ_new.clicked.connect(self._pick_new_file)
        act_row.addWidget(self._btn_succ_new)
        act_row.addStretch()
        card_lay.addLayout(act_row)

        self._card_export_success.setVisible(False)
        root.addWidget(self._card_export_success)

    # ── Helpers de UI ─────────────────────────────────────────────────────

    def _on_toggle_advanced(self, checked: bool):
        self._tabs.setVisible(checked)
        if checked:
            self._chk_advanced.setText("⚙️  Ocultar Personalización")
            self._lbl_simple_desc.setText(
                "Ajustes manuales activos: edita la tabla de cortes, curva de tempo o estructura."
            )
        else:
            self._chk_advanced.setText("⚙️  Personalizar Cortes & BPM")
            self._lbl_simple_desc.setText(
                "3 cortes listos · Arrastra en la onda para retocar o pulsa abajo en Generar Previa"
            )

    def _apply_generate_style(self, ready: bool):
        if ready:
            self._btn_generate.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #ff1e38, stop:0.5 #d90020, stop:1 #990014);
                    color: white;
                    border: 1px solid #ff4d63;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 800;
                    letter-spacing: 0.8px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #ff3e55, stop:0.5 #ff1e38, stop:1 #b30018);
                    border: 1px solid #ff7588;
                }}
                QPushButton:pressed {{
                    background: #800010;
                }}
                QPushButton:disabled {{
                    background: {BG3};
                    color: {TEXT_DIM};
                    border: 1px solid {BORDER};
                }}
            """)
        else:
            self._btn_generate.setStyleSheet(f"""
                QPushButton {{
                    background: {BG3};
                    color: {TEXT_DIM};
                    border: 1px solid {BORDER};
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 800;
                    letter-spacing: 0.8px;
                }}
            """)

    def _make_table(self, headers: list) -> QTableWidget:
        tbl = QTableWidget(0, len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        tbl.setShowGrid(False)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(_table_style())
        tbl.setFocusPolicy(Qt.NoFocus)
        return tbl

    def _randomize_seed(self):
        self._spin_seed.setValue(random.randint(0, 99999))

    def _on_regen(self):
        self.regen_requested.emit(self._spin_seed.value())
        # Resetear apariencia del botón al estado normal
        self._btn_regen.setText("⟳  Regenerar con esta seed")
        self._btn_regen.setStyleSheet(
            _btn(BG3, ACCENT, BG4, radius=10, fs=12, border=ACCENT + "44")
        )

    def _on_waveform_seek(self, t: float):
        if self._player:
            self._player.seek(t)

    def _on_track_switched(self, mode: str):
        if HAS_WAVEFORM:
            self._waveform.set_mode(mode)

    def _on_boundaries_changed(self, boundary_times: list):
        """
        El usuario arrastró una línea en la waveform.
        Reconstruye las secciones con los nuevos tiempos y recalcula el plan
        en tiempo real para que la previa refleje exactamente la edición del usuario.
        """
        if not self._analysis or not boundary_times:
            return
        import dataclasses
        sections = self._analysis.sections
        if len(boundary_times) != len(sections) - 1:
            return   # número de límites no coincide, ignorar

        # Clonar secciones con los nuevos límites garantizando monotonicidad
        new_sections = []
        cur_start = sections[0].start_time
        for i, sec in enumerate(sections):
            if i < len(boundary_times):
                new_end = max(cur_start + 0.5, float(boundary_times[i]))
            else:
                new_end = sec.end_time

            new_sec = dataclasses.replace(
                sec,
                start_time=cur_start,
                end_time=new_end,
            )
            new_sections.append(new_sec)
            cur_start = new_end

        # Actualizar el analysis y reconstruir el plan de previa con los nuevos cortes
        self._analysis = dataclasses.replace(self._analysis, sections=new_sections)
        self._plan = build_preview_plan(self._analysis)

        # Actualizar tablas de UI
        self._fill_structure(self._analysis)
        self._fill_plan(self._plan)

        # Actualizar estimación de previa
        est = self._plan.estimated_duration_after_stretch
        ok  = 120 <= est <= 180
        self._card_pv.set_value(fmt_time_short(est))
        self._card_pv.set_accent(GREEN if ok else WARN)

        # Actualizar resaltado de las cajas de la previa en la waveform
        if HAS_WAVEFORM:
            self._waveform.update_plan_highlights(self._plan.segments)

    # ── API pública ───────────────────────────────────────────────────────

    def populate(self, analysis, plan, bpm: float, dur: float,
                 file_path: str, cfg: dict, key_res=None):
        self._analysis    = analysis
        self._plan        = plan
        self._source_path = file_path
        self._bpm         = bpm
        self._key_res     = key_res
        name = Path(file_path).stem
        max_n = 16
        self._card_file.set_value(name[:max_n] + ("…" if len(name) > max_n else ""))
        self._card_bpm.set_value(f"{bpm:.1f}")
        if key_res:
            self._key_str = f"{key_res.camelot} · {key_res.notation}"
            self._card_key.set_value(f"{key_res.camelot}  {key_res.notation}")
        else:
            self._key_str = ""
            self._card_key.set_value("—")
        self._card_dur.set_value(fmt_time_short(dur))
        self._card_drops.set_value(str(len(analysis.drops())))

        est = plan.estimated_duration_after_stretch
        ok  = 15 <= est <= 180
        self._card_pv.set_value(fmt_time_short(est))
        self._card_pv.set_accent(GREEN if ok else WARN)

        self._out_path = str(get_output_dir(file_path, cfg))
        self._lbl_folder_path.setText(short_path(self._out_path))
        self._chk_wav.setChecked(cfg.get("export_wav", True))
        self._chk_mp3.setChecked(cfg.get("export_mp3", True))
        if hasattr(self, "_branding_card"):
            self._branding_card.load_from_cfg(cfg)

        # Restaurar preferencias guardadas (speed_mode, palette, aspect_ratio)
        persisted_cfg = load_cfg()
        if hasattr(self, "_combo_speed_mode") and persisted_cfg.get("speed_mode"):
            for i in range(self._combo_speed_mode.count()):
                if self._combo_speed_mode.itemData(i) == persisted_cfg["speed_mode"]:
                    self._combo_speed_mode.setCurrentIndex(i)
                    break
        if hasattr(self, "_combo_video_pal") and persisted_cfg.get("video_palette"):
            for i in range(self._combo_video_pal.count()):
                if self._combo_video_pal.itemData(i) == persisted_cfg["video_palette"]:
                    self._combo_video_pal.setCurrentIndex(i)
                    break
        if hasattr(self, "_combo_aspect") and persisted_cfg.get("aspect_ratio"):
            for i in range(self._combo_aspect.count()):
                if self._combo_aspect.itemData(i) == persisted_cfg["aspect_ratio"]:
                    self._combo_aspect.setCurrentIndex(i)
                    break

        default_name = preview_filename(file_path)
        self._edit_name.setText(default_name)
        self._last_default_name = default_name

        self._fill_structure(analysis)
        self._fill_plan(plan)

        # Waveform
        if HAS_WAVEFORM:
            self._waveform.load_track(file_path)
            self._waveform.set_sections(analysis.sections, plan.segments)

        # Reproductor: cargar el track original inmediatamente
        if self._player:
            self._player.set_source_track(file_path)

        self._active_preset_sec = 120
        self._update_preset_styles(120)
        self._lbl_simple_desc.setText(f"Preset 120s (2 Min · Defecto) aplicado ({len(plan.segments)} cortes calculados)")

        self._btn_generate.setEnabled(True)
        self._apply_generate_style(True)
        self._btn_generate.start_shimmer()
        self._update_tempo_plot()

    def _update_preset_styles(self, active_sec: int):
        if not hasattr(self, "_preset_buttons"):
            return
        for btn, sec in self._preset_buttons:
            if sec == active_sec:
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                            stop:0 #ff1e38, stop:1 #b30018);
                        color: #ffffff;
                        border: 1px solid #ff4d63;
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: 800;
                        padding: 0 8px;
                    }
                """)
            else:
                btn.setStyleSheet(_btn(BG3, TEXT_MID, BG4, radius=4, fs=10))

    def _apply_duration_preset(self, seconds: int):
        self._active_preset_sec = seconds
        self._update_preset_styles(seconds)
        if not self._analysis:
            return
        cfg = load_cfg()
        cfg["preview_min_sec"] = float(max(5, seconds - 2))
        cfg["preview_max_sec"] = float(seconds)
        new_plan = build_preview_plan(self._analysis, target_duration_sec=float(seconds), cfg=cfg)
        self.update_after_regen(new_plan)
        if seconds == 120:
            self._lbl_simple_desc.setText(f"Preset 120s (2 Min · Defecto) aplicado ({len(new_plan.segments)} cortes calculados)")
        else:
            self._lbl_simple_desc.setText(f"Preset {seconds}s aplicado ({len(new_plan.segments)} cortes calculados)")

    def _pick_new_file(self):
        """Abre selector de archivo y emite load_file_requested sin salir de la app."""
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar track para nueva previa",
            "",
            "Audio (*.mp3 *.wav *.flac *.aiff *.m4a *.ogg *.opus *.wma)",
        )
        if file:
            self.load_file_requested.emit(file)

    def _select_voice_drop(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar firma de voz / Voice Drop / Jingle",
            "",
            "Archivos de Audio (*.wav *.mp3 *.aiff *.flac *.m4a)",
        )
        if file:
            self._voice_drop_path = file
            p = Path(file)
            self._lbl_voice_drop.setText(f"✓ {p.name[:16]}")
            self._btn_voice_drop.setText("🎙️ Cambiar Drop")
            self._update_voice_drop_marker()

    def _update_voice_drop_marker(self):
        """Calcula y muestra el marcador dorado de Voice Drop en la waveform."""
        if not (HAS_WAVEFORM and hasattr(self, "_waveform") and self._voice_drop_path):
            return
        pos = self._combo_voice_pos.currentData() if hasattr(self, "_combo_voice_pos") else "predrop"
        if pos == "manual" and self._voice_drop_time_sec >= 0:
            t = self._voice_drop_time_sec
        elif pos == "intro":
            t = 1.8
        else:
            # Pre-Drop: calcular desde drops del plan
            drop_t = 16.0
            if self._plan:
                from src.analysis.structure import SectionType
                drops = [seg.section.start_time for seg in self._plan.segments
                         if getattr(seg.section, "type", None) == SectionType.DROP]
                if drops:
                    drop_t = drops[0]
            t = max(1.5, drop_t - 3.8)
        self._waveform.set_voice_drop_marker(t)

    def _on_voice_drop_marker_moved(self, t: float):
        """El usuario arrastró el marcador dorado → activar modo Manual y guardar posición."""
        self._voice_drop_time_sec = t
        if hasattr(self, "_combo_voice_pos"):
            for i in range(self._combo_voice_pos.count()):
                if self._combo_voice_pos.itemData(i) == "manual":
                    self._combo_voice_pos.blockSignals(True)
                    self._combo_voice_pos.setCurrentIndex(i)
                    self._combo_voice_pos.blockSignals(False)
                    break

    def get_export_options(self) -> dict:
        speed_mode = self._combo_speed_mode.currentData() if hasattr(self, "_combo_speed_mode") else "vinyl"
        video_pal = self._combo_video_pal.currentData() if hasattr(self, "_combo_video_pal") else "radical"
        promo_txt = self._edit_promo.text().strip() if hasattr(self, "_edit_promo") else ""
        aspect = self._combo_aspect.currentData() if hasattr(self, "_combo_aspect") else "9:16"
        voice_pos = self._combo_voice_pos.currentData() if hasattr(self, "_combo_voice_pos") else "predrop"

        return {
            "export_wav": self._chk_wav.isChecked(),
            "export_mp3": self._chk_mp3.isChecked(),
            "export_flac": self._chk_flac.isChecked(),
            "export_video": self._chk_video.isChecked(),
            "fx_flanger": self._chk_fx_flanger.isChecked(),
            "fx_filter_sweep": self._chk_fx_filter.isChecked(),
            "studio_mastering": self._chk_fx_master.isChecked(),
            "speed_mode": speed_mode,
            "video_palette": video_pal,
            "video_promo_text": promo_txt,
            "aspect_ratio": aspect,
            "voice_drop_enabled": bool(self._voice_drop_path),
            "voice_drop_path": self._voice_drop_path,
            "voice_drop_position": voice_pos,
            "voice_drop_time_sec": self._voice_drop_time_sec,
            "key_str": self._key_str,
        }

    def update_after_regen(self, plan):
        self._plan = plan
        self._fill_plan(plan)
        est = plan.estimated_duration_after_stretch
        ok  = 10 <= est <= 180
        self._card_pv.set_value(fmt_time_short(est))
        self._card_pv.set_accent(GREEN if ok else WARN)
        if HAS_WAVEFORM and self._source_path:
            self._waveform.update_plan_highlights(plan.segments)
        self._update_tempo_plot()

    def update_folder(self, file_path: str, cfg: dict):
        self._out_path = str(get_output_dir(file_path, cfg))
        self._lbl_folder_path.setText(short_path(self._out_path))

    def on_export_done(self, generated: list, seed: int):
        self._last_seed        = seed
        self._generated_paths  = generated
        self._spin_seed.setValue(seed)
        self._btn_generate.setEnabled(True)
        self._btn_generate.setText("▶   GENERAR PREVIA")
        self._apply_generate_style(True)
        self._btn_generate.start_shimmer()

        # Mostrar tarjeta de confirmación con los archivos y la carpeta exacta
        if generated:
            out_dir = str(Path(generated[0]).parent)
            file_names = [Path(p).name for p in generated]
            has_vid = any(p.lower().endswith(".mp4") for p in generated)

            title_text = "🎉 ¡Previa y Vídeo Social exportados con éxito!" if has_vid else "✅ ¡Previa de audio exportada con éxito!"
            self._lbl_succ_title.setText(title_text)
            self._lbl_succ_files.setText("Archivos:  " + "  ·  ".join(file_names))
            self._lbl_succ_dir.setText(f"📁 Carpeta de guardado:\n{out_dir}")
            self._card_export_success.setVisible(True)

            # Priorizar archivo WAV sin comprimir para evitar retrasos de búsqueda y advertencias [mp3float]
            prev_file = next((p for p in generated if p.lower().endswith(".wav")), generated[0])
            if HAS_WAVEFORM and self._plan:
                self._waveform.load_preview(prev_file, self._plan.segments)
            if self._player:
                self._player.set_preview_track(prev_file, autoplay=True)
            self.play_requested.emit(prev_file)

    def on_export_start(self):
        if hasattr(self, "_card_export_success"):
            self._card_export_success.setVisible(False)
        self._btn_generate.setEnabled(False)
        self._btn_generate.setText("⏳   Generando previa…")
        self._btn_generate.stop_shimmer()
        self._apply_generate_style(False)

    def get_export_name(self) -> str:
        return self._edit_name.text().strip() or self._last_default_name or "PREVIA"

    def get_export_formats(self) -> tuple:
        return self._chk_wav.isChecked(), self._chk_mp3.isChecked()

    def get_seed(self) -> int:
        return self._spin_seed.value()

    def get_branding_metadata(self) -> dict:
        if hasattr(self, "_branding_card"):
            return self._branding_card.get_metadata()
        return {}

    def get_branding_cover_path(self) -> str:
        if hasattr(self, "_branding_card"):
            return self._branding_card.get_cover_path()
        return ""

    def persist_branding_if_requested(self):
        if hasattr(self, "_branding_card"):
            self._branding_card.persist_if_requested()

    def _fill_structure(self, analysis):
        tbl = self._tbl_structure
        tbl.setRowCount(0)
        for sec in analysis.sections:
            row = tbl.rowCount()
            tbl.insertRow(row)
            tbl.setRowHeight(row, 26)
            c  = SECTION_COLOR.get(sec.type, "#888899")
            lb = SECTION_LABEL.get(sec.type, "?")
            tbl.setCellWidget(row, 0, _badge(lb, c))
            tbl.setItem(row, 1, _cell(fmt_time(sec.start_time)))
            tbl.setItem(row, 2, _cell(fmt_time(sec.end_time)))
            tbl.setItem(row, 3, _cell(f"{sec.duration:.1f}s"))
            tbl.setItem(row, 4, _lufs_cell(sec.lufs))
            tbl.setItem(row, 5, _peak_cell(sec.peak_dbfs))

    # ── Pestaña de Cortes interactivos (Desde / Hasta) ─────────────────────

    def _build_cuts_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(5)

        # 1. Banner explicativo amigable
        guide_box = QFrame()
        guide_box.setStyleSheet(f"""
            QFrame {{
                background: {BG3};
                border-radius: 6px;
                border: 1px solid {BORDER};
                border-left: 3px solid {ACCENT};
            }}
        """)
        glay = QHBoxLayout(guide_box)
        glay.setContentsMargins(10, 4, 10, 4)
        glay.setSpacing(6)

        lbl_icon = QLabel("💡")
        lbl_icon.setStyleSheet("font-size: 13px; background: transparent; border: none;")
        glay.addWidget(lbl_icon)

        lbl_text = QLabel(
            "<b>Editor de Previa:</b> Arrastra las cajas en la forma de onda superior para mover o recortar trozos, "
            "o ajusta los segundos en la tabla. Usa <b>📍 Aquí</b> para capturar la posición actual del reproductor."
        )
        lbl_text.setStyleSheet(f"color: {TEXT_MID}; font-size: 10px; background: transparent; border: none;")
        lbl_text.setWordWrap(True)
        glay.addWidget(lbl_text, stretch=1)
        lay.addWidget(guide_box)

        # 2. Barra de presets rápidos y acciones
        top_bar = QHBoxLayout()
        top_bar.setSpacing(5)

        lbl_t = QLabel("PRESETS RÁPIDOS:")
        lbl_t.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9.5px; font-weight: 700; letter-spacing: 0.5px; background: transparent; border: none;"
        )
        top_bar.addWidget(lbl_t)

        btn_p1 = QPushButton("⚡ Estándar AI")
        btn_p1.setFixedHeight(24)
        btn_p1.setStyleSheet(_btn(BG3, TEXT, BG4, radius=5, fs=10))
        btn_p1.setCursor(Qt.PointingHandCursor)
        btn_p1.setToolTip("Restaura la previa recomendada por IA (Intro + Drops)")
        btn_p1.clicked.connect(self._on_reset_cuts_clicked)
        top_bar.addWidget(btn_p1)

        btn_p2 = QPushButton("🔥 Solo Drops")
        btn_p2.setFixedHeight(24)
        btn_p2.setStyleSheet(_btn(BG3, ACCENT, BG4, radius=5, fs=10))
        btn_p2.setCursor(Qt.PointingHandCursor)
        btn_p2.setToolTip("Elimina la intro: la previa va directa a los drops con máxima energía")
        btn_p2.clicked.connect(self._preset_only_drops)
        top_bar.addWidget(btn_p2)

        btn_p3 = QPushButton("⏱️ Intro Corta 15s")
        btn_p3.setFixedHeight(24)
        btn_p3.setStyleSheet(_btn(BG3, WARN, BG4, radius=5, fs=10))
        btn_p3.setCursor(Qt.PointingHandCursor)
        btn_p3.setToolTip("Acorta la intro a 15 segundos antes del subidón")
        btn_p3.clicked.connect(self._preset_short_intro)
        top_bar.addWidget(btn_p3)

        top_bar.addStretch()

        self._lbl_cuts_summary = QLabel("—")
        self._lbl_cuts_summary.setStyleSheet(
            f"color: {ACCENT}; font-size: 10px; font-weight: 700; background: {BG3}; border: 1px solid {BORDER}; border-radius: 5px; padding: 2px 7px;"
        )
        top_bar.addWidget(self._lbl_cuts_summary)

        self._btn_add_cut = QPushButton("➕ Añadir corte")
        self._btn_add_cut.setFixedHeight(24)
        self._btn_add_cut.setStyleSheet(_btn(BG4, TEXT_SUB, BG5, radius=5, fs=10))
        self._btn_add_cut.setCursor(Qt.PointingHandCursor)
        self._btn_add_cut.setToolTip("Añade un nuevo fragmento a la previa")
        self._btn_add_cut.clicked.connect(self._on_add_cut_clicked)
        top_bar.addWidget(self._btn_add_cut)

        lay.addLayout(top_bar)

        # 3. Tabla de cortes interactiva
        self._tbl_cuts = QTableWidget(0, 8)
        self._tbl_cuts.setHorizontalHeaderLabels([
            "#", "SECCIÓN", "INICIO (s)", "FIN (s)", "DURACIÓN", "EN PREVIA", "OÍR", "QUITAR"
        ])
        self._tbl_cuts.verticalHeader().setVisible(False)
        self._tbl_cuts.horizontalHeader().setStretchLastSection(False)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._tbl_cuts.setColumnWidth(0, 32)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self._tbl_cuts.setColumnWidth(6, 38)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self._tbl_cuts.setColumnWidth(7, 32)
        self._tbl_cuts.setShowGrid(False)
        self._tbl_cuts.setAlternatingRowColors(True)
        self._tbl_cuts.setStyleSheet(_table_style())
        self._tbl_cuts.setSelectionMode(QAbstractItemView.NoSelection)
        self._tbl_cuts.setMinimumHeight(105)

        lay.addWidget(self._tbl_cuts, stretch=1)
        return w

    def _on_waveform_cuts_changed(self, cuts: list):
        """El usuario arrastró un corte o sus límites directamente en la waveform."""
        if not hasattr(self, "_tbl_cuts"):
            return
        tbl = self._tbl_cuts
        if tbl.rowCount() != len(cuts):
            return

        for r, (start, end) in enumerate(cuts):
            w_s = tbl.cellWidget(r, 2)
            w_e = tbl.cellWidget(r, 3)
            spin_s = w_s.findChild(QDoubleSpinBox) if w_s else None
            spin_e = w_e.findChild(QDoubleSpinBox) if w_e else None
            if spin_s and spin_e:
                spin_s.blockSignals(True)
                spin_e.blockSignals(True)
                spin_s.setValue(round(float(start), 1))
                spin_e.setValue(round(float(end), 1))
                spin_s.blockSignals(False)
                spin_e.blockSignals(False)

        self._sync_cuts_from_table()

    def _sync_cuts_from_table(self):
        if not self._analysis or not hasattr(self, "_tbl_cuts"):
            return
        tbl = self._tbl_cuts
        new_segs = []
        t_pv = 0.0

        for r in range(tbl.rowCount()):
            w_s = tbl.cellWidget(r, 2)
            w_e = tbl.cellWidget(r, 3)
            spin_s = w_s.findChild(QDoubleSpinBox) if w_s else None
            spin_e = w_e.findChild(QDoubleSpinBox) if w_e else None
            lbl_dur = tbl.cellWidget(r, 4)
            lbl_pv  = tbl.cellWidget(r, 5)

            if not (spin_s and spin_e):
                continue

            t_s = float(spin_s.value())
            t_e = float(spin_e.value())

            # Garantizar que el fin sea posterior al inicio
            if t_e <= t_s + 0.5:
                t_e = t_s + 0.5
                spin_e.blockSignals(True)
                spin_e.setValue(t_e)
                spin_e.blockSignals(False)

            dur = t_e - t_s

            if lbl_dur and isinstance(lbl_dur, QLabel):
                lbl_dur.setText(f"{dur:.1f}s")
            if lbl_pv and isinstance(lbl_pv, QLabel):
                lbl_pv.setText(f"{fmt_time(t_pv)}  →  {fmt_time(t_pv + dur)}")

            t_pv += dur

            # Determinar tipo de sección según análisis original
            sec_type = SectionType.UNKNOWN
            for sec in self._analysis.sections:
                if sec.start_time <= (t_s + t_e) / 2.0 <= sec.end_time:
                    sec_type = sec.type
                    break

            from src.analysis.structure import Section
            from src.analysis.segments import PreviewSegment
            new_sec = Section(type=sec_type, start_time=t_s, end_time=t_e)
            seg = PreviewSegment(section=new_sec, trimmed_start=0.0, trimmed_end=dur)
            new_segs.append(seg)

        from src.analysis.segments import AVG_STRETCH_FACTOR, PreviewPlan
        raw_dur = sum(s.duration for s in new_segs)
        est_stretch = raw_dur / AVG_STRETCH_FACTOR
        self._plan = PreviewPlan(
            segments=new_segs,
            estimated_duration_before_stretch=raw_dur,
            estimated_duration_after_stretch=est_stretch,
        )

        self._lbl_cuts_summary.setText(
            f"{len(new_segs)} cortes  ·  Total: {raw_dur:.1f}s  ·  Previa est: {fmt_time_short(est_stretch)}"
        )
        ok = 120 <= est_stretch <= 180
        self._card_pv.set_value(fmt_time_short(est_stretch))
        self._card_pv.set_accent(GREEN if ok else WARN)

        if HAS_WAVEFORM and self._source_path:
            self._waveform.update_plan_highlights(new_segs)

        self._update_tempo_plot()

    def _on_add_cut_clicked(self):
        if not self._analysis:
            return
        track_dur = self._analysis.duration if self._analysis else 300.0
        pos = self._player.get_position_seconds() if self._player else 0.0
        start = min(track_dur - 4.0, max(0.0, round(pos, 1)))
        end = min(track_dur, start + 16.0)

        sec_type = SectionType.DROP
        for sec in self._analysis.sections:
            if sec.start_time <= (start + end) / 2.0 <= sec.end_time:
                sec_type = sec.type
                break

        from src.analysis.structure import Section
        from src.analysis.segments import PreviewSegment, PreviewPlan, AVG_STRETCH_FACTOR
        new_sec = Section(type=sec_type, start_time=start, end_time=end)
        new_seg = PreviewSegment(section=new_sec, trimmed_start=0.0, trimmed_end=end - start)

        current_segs = list(self._plan.segments) if self._plan else []
        current_segs.append(new_seg)
        current_segs.sort(key=lambda s: s.source_start)

        raw_dur = sum(s.duration for s in current_segs)
        self._plan = PreviewPlan(
            segments=current_segs,
            estimated_duration_before_stretch=raw_dur,
            estimated_duration_after_stretch=raw_dur / AVG_STRETCH_FACTOR,
        )
        self._fill_plan(self._plan)
        if HAS_WAVEFORM:
            self._waveform.update_plan_highlights(current_segs)

    def _on_reset_cuts_clicked(self):
        if not self._analysis:
            return
        self._plan = build_preview_plan(self._analysis)
        self._fill_plan(self._plan)
        if HAS_WAVEFORM:
            self._waveform.update_plan_highlights(self._plan.segments)

    def _preset_short_intro(self):
        """Acorta la intro a los últimos 15 segundos antes de romper."""
        if not self._analysis:
            return
        base_plan = build_preview_plan(self._analysis)
        new_segs = []
        for seg in base_plan.segments:
            if seg.section.type == SectionType.INTRO and seg.duration > 15.0:
                from src.analysis.segments import PreviewSegment
                t_start = max(0.0, seg.section.end_time - 15.0 - seg.section.start_time)
                short_s = PreviewSegment(
                    section=seg.section,
                    trimmed_start=t_start,
                    trimmed_end=seg.section.end_time - seg.section.start_time,
                )
                new_segs.append(short_s)
            else:
                new_segs.append(seg)

        from src.analysis.segments import PreviewPlan, AVG_STRETCH_FACTOR
        raw_dur = sum(s.duration for s in new_segs)
        self._plan = PreviewPlan(
            segments=new_segs,
            estimated_duration_before_stretch=raw_dur,
            estimated_duration_after_stretch=raw_dur / AVG_STRETCH_FACTOR,
        )
        self._fill_plan(self._plan)
        if HAS_WAVEFORM:
            self._waveform.update_plan_highlights(self._plan.segments)

    def _preset_only_drops(self):
        """Previa directa a los Drops con máxima energía."""
        if not self._analysis:
            return
        base_plan = build_preview_plan(self._analysis)
        drop_segs = [s for s in base_plan.segments if s.section.type == SectionType.DROP]
        if not drop_segs:
            drop_segs = base_plan.segments[-2:] if len(base_plan.segments) >= 2 else base_plan.segments

        from src.analysis.segments import PreviewPlan, AVG_STRETCH_FACTOR
        raw_dur = sum(s.duration for s in drop_segs)
        self._plan = PreviewPlan(
            segments=drop_segs,
            estimated_duration_before_stretch=raw_dur,
            estimated_duration_after_stretch=raw_dur / AVG_STRETCH_FACTOR,
        )
        self._fill_plan(self._plan)
        if HAS_WAVEFORM:
            self._waveform.update_plan_highlights(self._plan.segments)

    def _fill_plan(self, plan):
        if not hasattr(self, "_tbl_cuts"):
            return
        tbl = self._tbl_cuts
        tbl.setRowCount(0)
        t_pv = 0.0
        track_dur = self._analysis.duration if self._analysis else 600.0

        for idx, seg in enumerate(plan.segments):
            row = tbl.rowCount()
            tbl.insertRow(row)
            tbl.setRowHeight(row, 28)

            # Col 0: # badge
            lbl_num = QLabel(f"#{idx + 1}")
            lbl_num.setAlignment(Qt.AlignCenter)
            lbl_num.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 10px; font-weight: 700; background: transparent;"
            )
            tbl.setCellWidget(row, 0, lbl_num)

            # Col 1: Tipo badge
            c  = SECTION_COLOR.get(seg.section.type, "#888899")
            lb = SECTION_LABEL.get(seg.section.type, "?")
            tbl.setCellWidget(row, 1, _badge(lb, c))

            # Col 2: DESDE (s) + botón 📍
            w_s = QWidget()
            lay_s = QHBoxLayout(w_s)
            lay_s.setContentsMargins(2, 1, 2, 1)
            lay_s.setSpacing(3)
            spin_s = QDoubleSpinBox()
            spin_s.setRange(0.0, track_dur)
            spin_s.setDecimals(1)
            spin_s.setSingleStep(0.5)
            spin_s.setSuffix(" s")
            spin_s.setValue(float(seg.source_start))
            spin_s.setStyleSheet(_input_style())
            spin_s.setFixedHeight(22)
            spin_s.valueChanged.connect(self._sync_cuts_from_table)
            lay_s.addWidget(spin_s)

            btn_s_now = QPushButton("📍")
            btn_s_now.setFixedSize(22, 22)
            btn_s_now.setStyleSheet(_btn(BG4, TEXT, BG5, radius=5, fs=10))
            btn_s_now.setToolTip("Poner inicio del corte en la posición actual del reproductor")
            btn_s_now.setCursor(Qt.PointingHandCursor)
            def _set_start(sp=spin_s):
                if self._player:
                    if hasattr(self._player, "_current_path") and hasattr(self._player, "_source_path"):
                        if self._player._current_path != self._player._source_path and self._player._source_path:
                            self._player._switch_to_source(autoplay=False)
                    pos = self._player.get_position_seconds()
                    sp.setValue(round(pos, 1))
            btn_s_now.clicked.connect(_set_start)
            lay_s.addWidget(btn_s_now)
            tbl.setCellWidget(row, 2, w_s)

            # Col 3: HASTA (s) + botón 📍
            w_e = QWidget()
            lay_e = QHBoxLayout(w_e)
            lay_e.setContentsMargins(2, 1, 2, 1)
            lay_e.setSpacing(3)
            spin_e = QDoubleSpinBox()
            spin_e.setRange(0.0, track_dur)
            spin_e.setDecimals(1)
            spin_e.setSingleStep(0.5)
            spin_e.setSuffix(" s")
            spin_e.setValue(float(seg.source_end))
            spin_e.setStyleSheet(_input_style())
            spin_e.setFixedHeight(22)
            spin_e.valueChanged.connect(self._sync_cuts_from_table)
            lay_e.addWidget(spin_e)

            btn_e_now = QPushButton("📍")
            btn_e_now.setFixedSize(22, 22)
            btn_e_now.setStyleSheet(_btn(BG4, TEXT, BG5, radius=5, fs=10))
            btn_e_now.setToolTip("Poner fin del corte en la posición actual del reproductor")
            btn_e_now.setCursor(Qt.PointingHandCursor)
            def _set_end(sp=spin_e):
                if self._player:
                    if hasattr(self._player, "_current_path") and hasattr(self._player, "_source_path"):
                        if self._player._current_path != self._player._source_path and self._player._source_path:
                            self._player._switch_to_source(autoplay=False)
                    pos = self._player.get_position_seconds()
                    sp.setValue(round(pos, 1))
            btn_e_now.clicked.connect(_set_end)
            lay_e.addWidget(btn_e_now)
            tbl.setCellWidget(row, 3, w_e)

            # Col 4: DURACIÓN
            lbl_dur = QLabel(f"{seg.duration:.1f}s")
            lbl_dur.setAlignment(Qt.AlignCenter)
            lbl_dur.setStyleSheet(
                f"color: {TEXT_SUB}; font-size: 10.5px; font-weight: 600; background: transparent;"
            )
            tbl.setCellWidget(row, 4, lbl_dur)

            # Col 5: EN PREVIA
            lbl_pv = QLabel(f"{fmt_time(t_pv)}  →  {fmt_time(t_pv + seg.duration)}")
            lbl_pv.setStyleSheet(
                f"color: {TEXT_MID}; font-size: 10.5px; background: transparent;"
            )
            tbl.setCellWidget(row, 5, lbl_pv)

            # Col 6: OÍR CORTE (▶)
            btn_play = QPushButton("▶")
            btn_play.setFixedSize(26, 22)
            btn_play.setStyleSheet(_btn(BG4, GREEN, BG5, radius=5, fs=10))
            btn_play.setCursor(Qt.PointingHandCursor)
            btn_play.setToolTip("Escuchar este corte en la pista original")
            def _play_cut(start_t=seg.source_start):
                if self._player:
                    if hasattr(self._player, "_current_path") and hasattr(self._player, "_source_path"):
                        if self._player._current_path != self._player._source_path and self._player._source_path:
                            self._player._switch_to_source(autoplay=False)
                    self._player.seek(start_t)
                    if not self._player.is_playing():
                        self._player.toggle_play()
            btn_play.clicked.connect(_play_cut)
            tbl.setCellWidget(row, 6, btn_play)

            # Col 7: ELIMINAR CORTE (✕)
            btn_del = QPushButton("✕")
            btn_del.setFixedSize(22, 22)
            btn_del.setStyleSheet(_btn(BG3, RED, BG4, radius=5, fs=10))
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setToolTip("Eliminar este corte de la previa")
            def _del_cut(target_btn=btn_del):
                for r in range(self._tbl_cuts.rowCount()):
                    if self._tbl_cuts.cellWidget(r, 7) == target_btn:
                        self._tbl_cuts.removeRow(r)
                        break
                self._sync_cuts_from_table()
            btn_del.clicked.connect(_del_cut)
            tbl.setCellWidget(row, 7, btn_del)

            t_pv += seg.duration

        raw_dur = sum(s.duration for s in plan.segments)
        est = plan.estimated_duration_after_stretch
        self._lbl_cuts_summary.setText(
            f"{len(plan.segments)} cortes  ·  Total: {raw_dur:.1f}s  ·  Previa est: {fmt_time_short(est)}"
        )

    # ── Pestaña de Curva de BPM ───────────────────────────────────────────

    def _build_tempo_tab(self) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(5)

        # 1. Banner explicativo amigable de BPM
        guide_box = QFrame()
        guide_box.setStyleSheet(f"""
            QFrame {{
                background: {BG3};
                border-radius: 6px;
                border: 1px solid {BORDER};
                border-left: 3px solid {ACCENT};
            }}
        """)
        glay = QHBoxLayout(guide_box)
        glay.setContentsMargins(10, 4, 10, 4)
        glay.setSpacing(6)

        lbl_icon = QLabel("🛡️")
        lbl_icon.setStyleSheet("font-size: 13px; background: transparent; border: none;")
        glay.addWidget(lbl_icon)

        lbl_text = QLabel(
            "<b>Protección Anti-Retoque por Tempo:</b> Modula la velocidad para que nadie pueda pinchar ni sincronizar la previa sin pagar. "
            "Elige <b>Automático</b> para variaciones orgánicas o pulsa un <b>Preset DJ</b> para acelerar en los drops."
        )
        lbl_text.setStyleSheet(f"color: {TEXT_MID}; font-size: 10px; background: transparent; border: none;")
        lbl_text.setWordWrap(True)
        glay.addWidget(lbl_text, stretch=1)
        lay.addWidget(guide_box)

        # 2. Barra de modo + presets
        top_bar = QHBoxLayout()
        top_bar.setSpacing(5)

        lbl_mode = QLabel("MODO:")
        lbl_mode.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9.5px; font-weight: 700; letter-spacing: 0.5px; background: transparent; border: none;"
        )
        top_bar.addWidget(lbl_mode)

        self._btn_mode_auto = QPushButton("🎲  Automático")
        self._btn_mode_auto.setFixedHeight(24)
        self._btn_mode_auto.setCursor(Qt.PointingHandCursor)
        self._btn_mode_auto.setToolTip("Variación analógica orgánica matemática recomendada para evitar mezclas")
        self._btn_mode_auto.clicked.connect(lambda: self._set_tempo_mode("auto"))
        top_bar.addWidget(self._btn_mode_auto)

        self._btn_mode_manual = QPushButton("🎛️  Manual (Presets DJ)")
        self._btn_mode_manual.setFixedHeight(24)
        self._btn_mode_manual.setCursor(Qt.PointingHandCursor)
        self._btn_mode_manual.setToolTip("Permite elegir subidas de BPM en Drops, rampas o editar momentos exactos")
        self._btn_mode_manual.clicked.connect(lambda: self._set_tempo_mode("manual"))
        top_bar.addWidget(self._btn_mode_manual)

        top_bar.addSpacing(6)

        lbl_pr = QLabel("PRESETS:")
        lbl_pr.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9.5px; font-weight: 700; background: transparent; border: none;"
        )
        top_bar.addWidget(lbl_pr)

        self._btn_preset_drops = QPushButton("🔥 +5 BPM en Drops")
        self._btn_preset_drops.setFixedHeight(24)
        self._btn_preset_drops.setStyleSheet(_btn(BG3, ACCENT, BG4, radius=5, fs=10))
        self._btn_preset_drops.setCursor(Qt.PointingHandCursor)
        self._btn_preset_drops.setToolTip("Detecta automáticamente los Drops y sube +5 BPM durante cada uno")
        self._btn_preset_drops.clicked.connect(self._preset_boost_drops)
        top_bar.addWidget(self._btn_preset_drops)

        self._btn_preset_ramp = QPushButton("⚡ +8% Rampa")
        self._btn_preset_ramp.setFixedHeight(24)
        self._btn_preset_ramp.setStyleSheet(_btn(BG3, ACCENT2, BG4, radius=5, fs=10))
        self._btn_preset_ramp.setCursor(Qt.PointingHandCursor)
        self._btn_preset_ramp.setToolTip("Acelera progresivamente un 8% hacia el clímax final")
        self._btn_preset_ramp.clicked.connect(self._preset_progressive)
        top_bar.addWidget(self._btn_preset_ramp)

        self._btn_preset_wave = QPushButton("🌊 ±4 BPM Vaivén")
        self._btn_preset_wave.setFixedHeight(24)
        self._btn_preset_wave.setStyleSheet(_btn(BG3, GREEN, BG4, radius=5, fs=10))
        self._btn_preset_wave.setCursor(Qt.PointingHandCursor)
        self._btn_preset_wave.setToolTip("Ondulaciones rítmicas alternadas")
        self._btn_preset_wave.clicked.connect(self._preset_vaiven)
        top_bar.addWidget(self._btn_preset_wave)

        self._btn_preset_boost = QPushButton("🛡️ +3 BPM Fijo")
        self._btn_preset_boost.setFixedHeight(24)
        self._btn_preset_boost.setStyleSheet(_btn(BG3, TEXT_SUB, BG4, radius=5, fs=10))
        self._btn_preset_boost.setCursor(Qt.PointingHandCursor)
        self._btn_preset_boost.setToolTip("Acelera toda la previa uniformemente a +3 BPM")
        self._btn_preset_boost.clicked.connect(self._preset_boost_all)
        top_bar.addWidget(self._btn_preset_boost)

        self._btn_preset_flat = QPushButton("⚪ 0 BPM")
        self._btn_preset_flat.setFixedHeight(24)
        self._btn_preset_flat.setStyleSheet(_btn(BG3, TEXT_DIM, BG4, radius=5, fs=10))
        self._btn_preset_flat.setCursor(Qt.PointingHandCursor)
        self._btn_preset_flat.setToolTip("Sin alteración de tempo (plano)")
        self._btn_preset_flat.clicked.connect(self._preset_flat)
        top_bar.addWidget(self._btn_preset_flat)

        top_bar.addStretch()

        self._btn_add_event = QPushButton("➕ Momento")
        self._btn_add_event.setFixedHeight(24)
        self._btn_add_event.setStyleSheet(_btn(BG4, TEXT_SUB, BG5, radius=5, fs=10))
        self._btn_add_event.setCursor(Qt.PointingHandCursor)
        self._btn_add_event.setToolTip("Añade un momento específico de cambio de BPM")
        self._btn_add_event.clicked.connect(self._on_add_event_clicked)
        top_bar.addWidget(self._btn_add_event)

        self._btn_clear_events = QPushButton("🗑️")
        self._btn_clear_events.setFixedSize(24, 24)
        self._btn_clear_events.setStyleSheet(_btn(BG4, RED, BG5, radius=5, fs=10))
        self._btn_clear_events.setCursor(Qt.PointingHandCursor)
        self._btn_clear_events.setToolTip("Limpiar todos los momentos")
        self._btn_clear_events.clicked.connect(self._clear_tempo_events)
        top_bar.addWidget(self._btn_clear_events)

        lay.addLayout(top_bar)

        # 2. Mini gráfico de BPM interactivo
        self._tempo_plot_frame = QFrame()
        self._tempo_plot_frame.setFixedHeight(80)
        self._tempo_plot_frame.setStyleSheet(f"""
            QFrame {{
                background: {BG};
                border-radius: 8px;
                border: 1px solid {BORDER};
            }}
        """)
        tpf_lay = QVBoxLayout(self._tempo_plot_frame)
        tpf_lay.setContentsMargins(4, 4, 4, 4)

        if HAS_PYQTGRAPH:
            self._tempo_plot = pg.PlotWidget()
            self._tempo_plot.setBackground(BG)
            self._tempo_plot.showGrid(x=True, y=True, alpha=0.15)
            self._tempo_plot.getPlotItem().setMenuEnabled(False)
            self._tempo_plot.getPlotItem().hideButtons()
            self._tempo_plot.getPlotItem().setMouseEnabled(x=False, y=False)
            self._tempo_plot.getAxis('bottom').setPen(pg.mkPen(color=TEXT_DIM, width=1))
            self._tempo_plot.getAxis('left').setPen(pg.mkPen(color=TEXT_DIM, width=1))
            self._tempo_plot.getAxis('bottom').setTextPen(pg.mkPen(color=TEXT_MID))
            self._tempo_plot.getAxis('left').setTextPen(pg.mkPen(color=TEXT_MID))
            self._tempo_plot.getAxis('left').setStyle(tickFont=QFont("Menlo", 8))
            self._tempo_plot.getAxis('bottom').setStyle(tickFont=QFont("Menlo", 8))

            self._tempo_base_line = pg.InfiniteLine(
                pos=150.0, angle=0,
                pen=pg.mkPen(color=TEXT_DIM, style=Qt.DashLine, width=1)
            )
            self._tempo_plot.addItem(self._tempo_base_line)

            self._tempo_curve_item = self._tempo_plot.plot(
                pen=pg.mkPen(color=ACCENT, width=2),
                fillLevel=120.0,
                brush=pg.mkBrush(QColor(255, 30, 56, 40)),
            )
            tpf_lay.addWidget(self._tempo_plot)
        else:
            lbl_noplot = QLabel("Curva de BPM visual")
            lbl_noplot.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
            tpf_lay.addWidget(lbl_noplot)

        lay.addWidget(self._tempo_plot_frame)

        # 3. Label de estado de modo
        self._lbl_auto_info = QLabel(
            "ℹ️  Modo Automático activo: El motor genera micro-variaciones analógicas continuas e imperceptibles "
            "controladas por la semilla (Seed). Para definir subidas de BPM específicas (ej. +5 BPM en drops), pulsa en 'Manual'."
        )
        self._lbl_auto_info.setWordWrap(True)
        self._lbl_auto_info.setStyleSheet(
            f"color: {TEXT_MID}; font-size: 10px; padding: 4px 8px; background: {BG3}; "
            f"border-radius: 5px; border: 1px solid {BORDER};"
        )
        lay.addWidget(self._lbl_auto_info)

        # 4. Tabla de eventos
        self._tbl_tempo = QTableWidget(0, 6)
        self._tbl_tempo.setHorizontalHeaderLabels([
            "MOMENTO PREVIA", "CAMBIO BPM", "DURACIÓN", "RAMPA", "TIPO EFECTO", ""
        ])
        self._tbl_tempo.verticalHeader().setVisible(False)
        self._tbl_tempo.horizontalHeader().setStretchLastSection(False)
        self._tbl_tempo.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._tbl_tempo.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._tbl_tempo.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._tbl_tempo.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._tbl_tempo.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._tbl_tempo.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self._tbl_tempo.setColumnWidth(5, 32)
        self._tbl_tempo.setShowGrid(False)
        self._tbl_tempo.setAlternatingRowColors(True)
        self._tbl_tempo.setStyleSheet(_table_style())
        self._tbl_tempo.setSelectionMode(QAbstractItemView.NoSelection)
        self._tbl_tempo.setMinimumHeight(95)
        lay.addWidget(self._tbl_tempo, stretch=1)

        self._update_tempo_mode_ui()
        return tab

    def _set_tempo_mode(self, mode: str):
        self._tempo_mode = mode
        if mode == "manual" and not self._tempo_events and self._tbl_tempo.rowCount() == 0:
            self._preset_boost_drops()
        else:
            self._update_tempo_mode_ui()

    def _update_tempo_mode_ui(self):
        if self._tempo_mode == "auto":
            self._btn_mode_auto.setStyleSheet(
                _btn(BG4, ACCENT, BG5, radius=6, fs=10, bold=True, border=ACCENT)
            )
            self._btn_mode_manual.setStyleSheet(
                _btn(BG3, TEXT_DIM, BG4, radius=6, fs=10, bold=False, border="")
            )
            self._lbl_auto_info.setText(
                "🛡️  Modo Automático activo: El motor aplica micro-variaciones matemáticas orgánicas según la semilla (Seed). "
                "La música suena natural al oído, pero resulta imposible de pinchar o mezclar en reproductores DJ. "
                "Para acelerar en los Drops o crear tus propias subidas, pulsa en 'Manual'."
            )
            self._lbl_auto_info.setStyleSheet(
                f"color: {TEXT_MID}; font-size: 10px; padding: 4px 8px; background: {BG3}; "
                f"border-radius: 5px; border: 1px solid {BORDER}; border-left: 3px solid {ACCENT};"
            )
            self._tbl_tempo.setEnabled(False)
        else:
            self._btn_mode_auto.setStyleSheet(
                _btn(BG3, TEXT_DIM, BG4, radius=6, fs=10, bold=False, border="")
            )
            self._btn_mode_manual.setStyleSheet(
                _btn(BG4, ACCENT, BG5, radius=6, fs=10, bold=True, border=ACCENT)
            )
            self._lbl_auto_info.setText(
                "🎛️  Modo Manual activo: Elige cualquiera de los Presets DJ ('+5 BPM en Drops', 'Rampa Final') "
                "o añade momentos en la tabla para acelerar (+BPM) o ralentizar (-BPM) tramos de la previa."
            )
            self._lbl_auto_info.setStyleSheet(
                f"color: {TEXT_MID}; font-size: 10px; padding: 4px 8px; background: {BG3}; "
                f"border-radius: 5px; border: 1px solid {BORDER}; border-left: 3px solid {WARN};"
            )
            self._tbl_tempo.setEnabled(True)
        self._update_tempo_plot()

    def _on_seed_changed(self, val: int):
        if self._tempo_mode == "auto":
            self._update_tempo_plot()

    def _preset_boost_drops(self):
        new_events = []
        if self._plan and self._plan.segments:
            t = 0.0
            for seg in self._plan.segments:
                if seg.section.type == SectionType.DROP:
                    dur = max(4.0, float(seg.duration))
                    trans = min(3.5, dur / 3.0)
                    new_events.append({
                        "time_sec": round(t, 1),
                        "bpm_delta": 5.0,
                        "duration_sec": round(dur, 1),
                        "transition_sec": round(trans, 1),
                        "style": "surge",
                    })
                t += float(seg.duration)

        if not new_events:
            new_events = [{
                "time_sec": 30.0,
                "bpm_delta": 5.0,
                "duration_sec": 18.0,
                "transition_sec": 3.5,
                "style": "surge",
            }]

        self._tempo_mode = "manual"
        self._load_tempo_events(new_events)
        self._update_tempo_mode_ui()

    def _preset_progressive(self):
        dur = float(self._plan.estimated_duration_after_stretch) if self._plan else 120.0
        base_bpm = self._bpm if self._bpm > 0 else 150.0
        delta = round(base_bpm * 0.08, 1) or 8.0
        t0 = round(dur * 0.4, 1)
        event_dur = round(dur - t0, 1)
        trans = min(12.0, event_dur / 2.0)
        new_events = [{
            "time_sec": t0,
            "bpm_delta": delta,
            "duration_sec": event_dur,
            "transition_sec": trans,
            "style": "ramp",
        }]
        self._tempo_mode = "manual"
        self._load_tempo_events(new_events)
        self._update_tempo_mode_ui()

    def _preset_vaiven(self):
        dur = float(self._plan.estimated_duration_after_stretch) if self._plan else 120.0
        spacing = dur / 4.0
        new_events = [
            {"time_sec": round(spacing * 0.8, 1), "bpm_delta": 4.0, "duration_sec": 16.0, "transition_sec": 3.5, "style": "surge"},
            {"time_sec": round(spacing * 1.8, 1), "bpm_delta": -3.5, "duration_sec": 16.0, "transition_sec": 3.5, "style": "surge"},
            {"time_sec": round(spacing * 2.8, 1), "bpm_delta": 5.0, "duration_sec": 20.0, "transition_sec": 4.0, "style": "surge"},
        ]
        self._tempo_mode = "manual"
        self._load_tempo_events(new_events)
        self._update_tempo_mode_ui()

    def _preset_boost_all(self):
        """Acelera toda la previa uniformemente a +3 BPM."""
        dur = float(self._plan.estimated_duration_after_stretch) if self._plan else 120.0
        new_events = [{
            "time_sec": 0.0,
            "bpm_delta": 3.0,
            "duration_sec": round(dur, 1),
            "transition_sec": 1.0,
            "style": "surge",
        }]
        self._tempo_mode = "manual"
        self._load_tempo_events(new_events)
        self._update_tempo_mode_ui()

    def _preset_flat(self):
        """Previa plana a tempo constante original (0 BPM de variación)."""
        self._tempo_mode = "manual"
        self._load_tempo_events([])
        self._update_tempo_mode_ui()

    def _clear_tempo_events(self):
        self._tbl_tempo.setRowCount(0)
        self._tempo_events = []
        self._update_tempo_plot()

    def _on_add_event_clicked(self):
        pos = self._player.get_position_seconds() if self._player else 0.0
        ev = {
            "time_sec": round(pos, 1),
            "bpm_delta": 5.0,
            "duration_sec": 16.0,
            "transition_sec": 3.5,
            "style": "surge",
        }
        self._add_tempo_event_row(ev)
        self._tempo_mode = "manual"
        self._sync_tempo_events_from_table()
        self._update_tempo_mode_ui()

    def _load_tempo_events(self, events: list[dict]):
        self._tbl_tempo.setRowCount(0)
        for ev in events:
            self._add_tempo_event_row(ev)
        self._sync_tempo_events_from_table()

    def _add_tempo_event_row(self, ev: dict):
        tbl = self._tbl_tempo
        row = tbl.rowCount()
        tbl.insertRow(row)
        tbl.setRowHeight(row, 28)

        # Col 0: Momento + botón "📍"
        w_t = QWidget()
        lay_t = QHBoxLayout(w_t)
        lay_t.setContentsMargins(2, 1, 2, 1)
        lay_t.setSpacing(3)
        spin_t = QDoubleSpinBox()
        spin_t.setRange(0.0, 999.0)
        spin_t.setDecimals(1)
        spin_t.setSingleStep(1.0)
        spin_t.setSuffix(" s")
        spin_t.setValue(float(ev.get("time_sec", 0.0)))
        spin_t.setStyleSheet(_input_style())
        spin_t.setFixedHeight(22)
        spin_t.valueChanged.connect(self._sync_tempo_events_from_table)
        lay_t.addWidget(spin_t)

        btn_here = QPushButton("📍")
        btn_here.setFixedSize(22, 22)
        btn_here.setStyleSheet(_btn(BG4, TEXT, BG5, radius=5, fs=10))
        btn_here.setToolTip("Tomar posición actual del reproductor")
        btn_here.setCursor(Qt.PointingHandCursor)
        def _set_here(sp=spin_t):
            pos = self._player.get_position_seconds() if self._player else 0.0
            sp.setValue(round(pos, 1))
        btn_here.clicked.connect(_set_here)
        lay_t.addWidget(btn_here)
        tbl.setCellWidget(row, 0, w_t)

        # Col 1: Delta BPM (ej. +5.0 BPM)
        spin_db = QDoubleSpinBox()
        spin_db.setRange(-50.0, 50.0)
        spin_db.setDecimals(1)
        spin_db.setSingleStep(0.5)
        spin_db.setSuffix(" BPM")
        spin_db.setValue(float(ev.get("bpm_delta", 5.0)))
        spin_db.setStyleSheet(_input_style())
        spin_db.setFixedHeight(22)
        spin_db.valueChanged.connect(self._sync_tempo_events_from_table)
        tbl.setCellWidget(row, 1, spin_db)

        # Col 2: Duración (s)
        spin_dur = QDoubleSpinBox()
        spin_dur.setRange(1.0, 300.0)
        spin_dur.setDecimals(1)
        spin_dur.setSingleStep(1.0)
        spin_dur.setSuffix(" s")
        spin_dur.setValue(float(ev.get("duration_sec", 16.0)))
        spin_dur.setStyleSheet(_input_style())
        spin_dur.setFixedHeight(22)
        spin_dur.valueChanged.connect(self._sync_tempo_events_from_table)
        tbl.setCellWidget(row, 2, spin_dur)

        # Col 3: Rampa transición (s)
        spin_tr = QDoubleSpinBox()
        spin_tr.setRange(0.2, 30.0)
        spin_tr.setDecimals(1)
        spin_tr.setSingleStep(0.5)
        spin_tr.setSuffix(" s")
        spin_tr.setValue(float(ev.get("transition_sec", 3.5)))
        spin_tr.setStyleSheet(_input_style())
        spin_tr.setFixedHeight(22)
        spin_tr.valueChanged.connect(self._sync_tempo_events_from_table)
        tbl.setCellWidget(row, 3, spin_tr)

        # Col 4: Tipo de efecto (Surge vs Ramp)
        cmb_style = QComboBox()
        cmb_style.addItem("▲▼ Subida y bajada (Surge)", "surge")
        cmb_style.addItem("▲— Rampa sostenida (Ramp)", "ramp")
        cmb_style.setStyleSheet(_input_style())
        cmb_style.setFixedHeight(22)
        if ev.get("style", "surge") == "ramp":
            cmb_style.setCurrentIndex(1)
        else:
            cmb_style.setCurrentIndex(0)
        cmb_style.currentIndexChanged.connect(self._sync_tempo_events_from_table)
        tbl.setCellWidget(row, 4, cmb_style)

        # Col 5: Botón eliminar
        btn_del = QPushButton("✕")
        btn_del.setFixedSize(22, 22)
        btn_del.setStyleSheet(_btn(BG3, RED, BG4, radius=5, fs=10))
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setToolTip("Eliminar este momento")
        def _del_row(target_btn=btn_del):
            for r in range(self._tbl_tempo.rowCount()):
                if self._tbl_tempo.cellWidget(r, 5) == target_btn:
                    self._tbl_tempo.removeRow(r)
                    break
            self._sync_tempo_events_from_table()
        btn_del.clicked.connect(_del_row)
        tbl.setCellWidget(row, 5, btn_del)

    def _sync_tempo_events_from_table(self):
        events = []
        tbl = self._tbl_tempo
        for r in range(tbl.rowCount()):
            w_t = tbl.cellWidget(r, 0)
            spin_t = w_t.findChild(QDoubleSpinBox) if w_t else None
            spin_db = tbl.cellWidget(r, 1)
            spin_dur = tbl.cellWidget(r, 2)
            spin_tr = tbl.cellWidget(r, 3)
            cmb = tbl.cellWidget(r, 4)
            if spin_t and spin_db and spin_dur and spin_tr and cmb:
                style_val = str(cmb.currentData() or "surge")
                events.append({
                    "time_sec": float(spin_t.value()),
                    "bpm_delta": float(spin_db.value()),
                    "duration_sec": float(spin_dur.value()),
                    "transition_sec": float(spin_tr.value()),
                    "style": style_val,
                })
        events.sort(key=lambda x: x["time_sec"])
        self._tempo_events = events
        self._update_tempo_plot()

    def _update_tempo_plot(self):
        if not HAS_PYQTGRAPH or self._tempo_plot is None:
            return

        base_bpm = self._bpm if self._bpm > 0 else 150.0
        dur = 120.0
        if self._plan and hasattr(self._plan, "estimated_duration_after_stretch"):
            dur = max(10.0, float(self._plan.estimated_duration_after_stretch))

        if self._tempo_base_line is not None:
            self._tempo_base_line.setValue(base_bpm)

        if self._tempo_mode == "manual":
            t_arr, bpm_arr = compute_preview_tempo_curve(
                dur, base_bpm, self._tempo_events, n_points=400
            )
            color = ACCENT
            brush_c = QColor(255, 30, 56, 45)
        else:
            seed = self._spin_seed.value() if hasattr(self, "_spin_seed") else 42
            from src.engine.variations import make_rate_envelope
            sim_rate, _ = make_rate_envelope(400, 10, min_rate=0.98, max_rate=1.06, seed=seed)
            t_arr = np.linspace(0, dur, 400)
            bpm_arr = base_bpm * sim_rate
            color = "#ff7b2b"
            brush_c = QColor(255, 123, 43, 40)

        if self._tempo_curve_item is not None:
            self._tempo_curve_item.setData(t_arr, bpm_arr)
            self._tempo_curve_item.setPen(pg.mkPen(color=color, width=2))
            self._tempo_curve_item.setBrush(pg.mkBrush(brush_c))

        min_y = min(float(np.min(bpm_arr)), base_bpm) - 4.0
        max_y = max(float(np.max(bpm_arr)), base_bpm) + 4.0
        p_item = self._tempo_plot.getPlotItem()
        if p_item is not None:
            vb = p_item.getViewBox()
            if vb is not None:
                if dur > 0:
                    vb.setLimits(xMin=0.0, xMax=dur, minXRange=min(5.0, dur), maxXRange=dur)
                vb.setYRange(min_y, max_y, padding=0.05)
                vb.setXRange(0, dur, padding=0.02)

    def get_tempo_mode(self) -> str:
        return self._tempo_mode

    def get_tempo_events(self) -> list:
        return list(self._tempo_events)


# ── Helpers de tabla ──────────────────────────────────────────────────────────

def _badge(label: str, color: str) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(w)
    lay.setContentsMargins(6, 2, 6, 2)
    lay.setAlignment(Qt.AlignCenter)
    lbl = QLabel(f"  {label}  ")
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(f"""
        background: {color}1a;
        color: {color};
        border: 1px solid {color}55;
        border-radius: 5px;
        font-size: 10px;
        font-weight: 800;
        padding: 3px 8px;
        letter-spacing: 0.5px;
    """)
    lay.addWidget(lbl)
    return w

def _cell(text: str) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setTextAlignment(Qt.AlignCenter)
    return it

def _lufs_cell(lufs: float) -> QTableWidgetItem:
    text = f"{lufs:.1f}" if lufs > -60 else "—"
    it = QTableWidgetItem(text)
    it.setTextAlignment(Qt.AlignCenter)
    if lufs > -60:
        if lufs >= -16:
            it.setForeground(QColor(METER_OK))
        elif lufs >= -24:
            it.setForeground(QColor(METER_WARN))
        else:
            it.setForeground(QColor(TEXT_MID))
    return it

def _peak_cell(peak: float) -> QTableWidgetItem:
    text = f"{peak:.1f}" if peak > -60 else "—"
    it = QTableWidgetItem(text)
    it.setTextAlignment(Qt.AlignCenter)
    if peak > -60:
        if peak >= -1.0:
            it.setForeground(QColor(METER_CLIP))
        elif peak >= -6.0:
            it.setForeground(QColor(METER_WARN))
        else:
            it.setForeground(QColor(METER_OK))
    return it


# ── Progress Bar con glow ─────────────────────────────────────────────────────

class GlowProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._glow_phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._active = False

    def set_active(self, v: bool):
        self._active = v
        if v:
            self._timer.start(40)
        else:
            self._timer.stop()
            self._glow_phase = 0.0
            self.update()

    def _tick(self):
        self._glow_phase = (self._glow_phase + 0.06) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._active or self.value() == 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = (math.sin(self._glow_phase) + 1) / 2
        alpha = int(30 + 60 * t)
        filled_w = int(self.width() * self.value() / 100)
        c = QColor(ACCENT)
        c.setAlpha(alpha)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c))
        p.drawRoundedRect(0, 0, filled_w, self.height(), 3, 3)
        p.end()


# ── Ventana Principal ─────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, initial_file: str = ""):
        super().__init__()
        try:
            from src.main import _log_startup
        except Exception:
            def _log_startup(msg): pass

        _log_startup("MainWindow: configurando título y dimensiones...")
        self.setWindowTitle("AutoPrevias — Radical Records")
        self.setMinimumSize(980, 640)

        # Adaptación de pantalla: objetivo 1600x900 adaptado para todo tipo de pantallas
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_w = min(1600, max(1000, int(avail.width() * 0.94)))
            target_h = min(920, max(680, int(avail.height() * 0.92)))
            self.resize(target_w, target_h)
            self.move(
                avail.x() + max(0, (avail.width() - target_w) // 2),
                avail.y() + max(0, (avail.height() - target_h) // 2),
            )
        else:
            self.resize(1600, 900)

        self.setAcceptDrops(True)

        # Icono de la ventana / aplicación
        icon_path = _ASSETS_DIR / "logo.png"
        if not icon_path.exists():
            icon_path = _ASSETS_DIR / "logo_emblem.png"
        if icon_path.exists():
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(str(icon_path)))

        _log_startup("MainWindow: cargando configuración de usuario...")
        self._cfg           = load_cfg()
        self._current_file  = ""
        self._analysis      = None
        self._plan          = None
        self._beat_grid     = None
        self._worker        = None
        self._export_worker = None

        self._dot_count    = 0
        self._progress_msg = ""   # mensaje limpio (sin puntos animados)
        self._dot_timer    = QTimer(self)
        self._dot_timer.timeout.connect(self._tick_dots)

        # Watch Folder (Apartado 4: 1)
        self._watching = False
        self._watched_folder = self._cfg.get("watch_folder_path", "")
        self._watched_processed = set()
        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(4000)
        self._watch_timer.timeout.connect(self._scan_watch_folder)
        if self._cfg.get("watch_folder_enabled", False) and self._watched_folder:
            self._watching = True
            self._watch_timer.start()

        _log_startup("MainWindow: aplicando paleta y estilos de color...")
        self._apply_palette()

        _log_startup("MainWindow: construyendo widgets de interfaz de usuario...")
        self._build_ui()
        _log_startup("MainWindow: interfaz de usuario lista.")

        if initial_file:
            _log_startup(f"MainWindow: cargando archivo inicial: {initial_file}")
            self._load_file(initial_file)

    # ── Paleta ────────────────────────────────────────────────────────────

    def _apply_palette(self):
        pal = QPalette()
        pal.setColor(QPalette.Window,          QColor(BG))
        pal.setColor(QPalette.WindowText,      QColor(TEXT))
        pal.setColor(QPalette.Base,            QColor(BG2))
        pal.setColor(QPalette.AlternateBase,   QColor(BG3))
        pal.setColor(QPalette.Text,            QColor(TEXT))
        pal.setColor(QPalette.Button,          QColor(BG3))
        pal.setColor(QPalette.ButtonText,      QColor(TEXT))
        pal.setColor(QPalette.Highlight,       QColor(ACCENT))
        pal.setColor(QPalette.HighlightedText, QColor("white"))
        self.setPalette(pal)
        sys_font = (
            "'.AppleSystemUIFont', 'Helvetica Neue', Arial"
            if sys.platform == "darwin"
            else "'Segoe UI', Arial"
        )
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {BG};
                font-family: {sys_font};
            }}
            QToolTip {{
                background: {BG3};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                font-size: 11px;
                padding: 4px 8px;
            }}
        """)

    # ── Layout ────────────────────────────────────────────────────────────

    def _build_ui(self):
        root_w = QWidget()
        self.setCentralWidget(root_w)
        root = QVBoxLayout(root_w)
        root.setContentsMargins(18, 12, 18, 10)
        root.setSpacing(8)

        # ── HEADER ───────────────────────────────────────────────────────
        self._hdr = QFrame()
        self._hdr.setFixedHeight(58)
        self._hdr.setObjectName("hdr")
        self._hdr.setStyleSheet(f"""
            QFrame#hdr {{
                background: {BG2};
                border-radius: 10px;
                border: 1px solid {BORDER};
                border-top: 2px solid {ACCENT};
            }}
        """)
        hdr_lay = QHBoxLayout(self._hdr)
        hdr_lay.setContentsMargins(18, 0, 18, 0)
        hdr_lay.setSpacing(0)

        # Logo
        logo_col = QVBoxLayout()
        logo_col.setSpacing(2)
        logo_col.setAlignment(Qt.AlignVCenter)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        logo_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Logo de empresa (emblema)
        self._logo_img = QLabel()
        logo_file = None
        for cand in [
            _ASSETS_DIR / "logo_emblem.png",
            _ASSETS_DIR / "logo.png",
            _ASSETS_DIR / "logo_emblem_red.png",
        ]:
            if cand.exists():
                logo_file = str(cand)
                break
        if logo_file:
            pix = QPixmap(logo_file)
            if not pix.isNull():
                self._logo_img.setPixmap(pix.scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self._logo_img.setStyleSheet("background: transparent; border: none;")
                logo_row.addWidget(self._logo_img)

        self._logo_lbl = QLabel("RR STUDIO · AUTOPREVIAS")
        self._logo_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 16px; font-weight: 900;"
            "letter-spacing: 0.5px; background: transparent; border: none;"
        )
        logo_row.addWidget(self._logo_lbl)

        v_badge = QLabel("PRO STUDIO v2.0")
        v_badge.setStyleSheet("""
            color: #ffffff;
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #ff1e38, stop:1 #990014);
            font-size: 8px;
            font-weight: 800;
            letter-spacing: 1px;
            border: 1px solid #ff4d63;
            border-radius: 4px;
            padding: 2px 5px;
        """)
        logo_row.addWidget(v_badge)

        self._btn_recents = QPushButton("🕒 Recientes")
        self._btn_recents.setFixedHeight(22)
        self._btn_recents.setCursor(Qt.PointingHandCursor)
        self._btn_recents.setStyleSheet(_btn(BG3, TEXT_MID, BG4, radius=4, fs=10))
        self._btn_recents.setToolTip("Ver y cargar archivos de audio procesados recientemente")
        self._btn_recents.clicked.connect(self._show_recent_menu)
        logo_row.addWidget(self._btn_recents)

        self._btn_batch_hdr = QPushButton("📁 Modo Lote")
        self._btn_batch_hdr.setFixedHeight(22)
        self._btn_batch_hdr.setCursor(Qt.PointingHandCursor)
        self._btn_batch_hdr.setStyleSheet(_btn(BG3, TEXT_MID, BG4, radius=4, fs=10))
        self._btn_batch_hdr.setToolTip("Procesar múltiples pistas en lote automáticamente")
        self._btn_batch_hdr.clicked.connect(lambda: self._open_batch_dialog())
        logo_row.addWidget(self._btn_batch_hdr)

        self._btn_watch = QPushButton("👁️ Vigilar Carpeta")
        self._btn_watch.setFixedHeight(22)
        self._btn_watch.setCursor(Qt.PointingHandCursor)
        self._update_watch_button_style()
        self._btn_watch.setToolTip("Vigilar una carpeta y generar previas automáticamente cuando caiga un nuevo tema")
        self._btn_watch.clicked.connect(self._toggle_watch_folder)
        logo_row.addWidget(self._btn_watch)

        logo_col.addLayout(logo_row)

        sub_lbl = QLabel("RADICAL RECORDS · HARDWARE SYNTH & PREVIEW ENGINE")
        sub_lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 8px; font-weight: 700;"
            "letter-spacing: 1.2px; background: transparent; border: none;"
        )
        logo_col.addWidget(sub_lbl)
        hdr_lay.addLayout(logo_col)
        hdr_lay.addStretch()

        # Right — banner de Radical Records
        right_col = QVBoxLayout()
        right_col.setSpacing(2)
        right_col.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        banner_path = _ASSETS_DIR / "logo_banner.png"
        if not banner_path.exists():
            banner_path = _ASSETS_DIR / "logo_banner_red.png"
        if banner_path.exists():
            b_pix = QPixmap(str(banner_path))
            if not b_pix.isNull():
                lbl_b = QLabel()
                lbl_b.setAlignment(Qt.AlignRight)
                lbl_b.setPixmap(b_pix.scaledToHeight(20, Qt.SmoothTransformation))
                lbl_b.setStyleSheet("background: transparent; border: none;")
                right_col.addWidget(lbl_b)

        self._hint_lbl = QLabel("AUDIO ENGINE READY")
        self._hint_lbl.setAlignment(Qt.AlignRight)
        self._hint_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 9.5px; font-weight: 800; letter-spacing: 1px;"
            "background: transparent; border: none;"
        )
        right_col.addWidget(self._hint_lbl)

        support_lbl = QLabel(f"SOPORTE: {SUPPORT}")
        support_lbl.setAlignment(Qt.AlignRight)
        support_lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 8px; font-weight: 600; letter-spacing: 0.3px;"
            "background: transparent; border: none;"
        )
        right_col.addWidget(support_lbl)
        hdr_lay.addLayout(right_col)

        root.addWidget(self._hdr)

        # ── STACK ────────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")

        # Página 0 — Drop zone
        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(self._load_file)
        self._stack.addWidget(self._drop_zone)

        # Página 1 — Resultados (scroll)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {BG};
                width: 5px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {BG5};
                border-radius: 2px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        self._results = ResultPanel()
        self._results.regen_requested.connect(self._regenerate)
        self._results.folder_requested.connect(self._set_folder)
        self._results.open_folder_requested.connect(self._open_export_folder)
        self._results.new_file_requested.connect(self._back_to_drop)
        self._results.generate_requested.connect(self._generate)
        self._results.load_file_requested.connect(self._load_file)
        scroll.setWidget(self._results)
        self._stack.addWidget(scroll)

        root.addWidget(self._stack, stretch=1)

        # ── PROGRESS FRAME ────────────────────────────────────────────────
        prog_frame = QFrame()
        prog_frame.setFixedHeight(40)
        prog_frame.setStyleSheet(f"""
            QFrame {{
                background: {BG2};
                border-radius: 8px;
                border: 1px solid {BORDER};
            }}
        """)
        pf = QHBoxLayout(prog_frame)
        pf.setContentsMargins(14, 0, 14, 0)
        pf.setSpacing(12)

        self._progress_label = QLabel("Listo — arrastra un track o pulsa Abrir archivo")
        self._progress_label.setStyleSheet(
            f"color: {TEXT_MID}; font-size: 11px; background: transparent; border: none;"
        )

        self._progress_bar = GlowProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(5)
        self._progress_bar.setMinimumWidth(180)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {BG3};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ACCENT}, stop:1 {ACCENT2});
                border-radius: 2px;
            }}
        """)

        pf.addWidget(self._progress_label, stretch=1)
        pf.addWidget(self._progress_bar)
        root.addWidget(prog_frame)

    # ── Animación de puntos en progreso ──────────────────────────────────

    def _tick_dots(self):
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count
        self._progress_label.setText(self._progress_msg + dots)

    def _start_dots(self):
        self._dot_count = 0
        self._dot_timer.start(400)
        self._progress_bar.set_active(True)

    def _stop_dots(self):
        self._dot_timer.stop()
        self._progress_bar.set_active(False)

    # ── Fade-in del panel de resultados ──────────────────────────────────

    def _fade_in_results(self):
        eff = QGraphicsOpacityEffect(self._stack.currentWidget())
        self._stack.currentWidget().setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(400)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    # ── Carga ─────────────────────────────────────────────────────────────

    def _load_file(self, path: str):
        from src.engine.audio_io import repair_wav_header_if_needed
        repair_wav_header_if_needed(path)

        # Registrar en historial de recientes (Apartado 3: 3)
        try:
            from src.config import add_recent_file
            add_recent_file(path, self._cfg)
        except Exception:
            pass

        # Extracción automática de carátula incrustada (Apartado 2: 2)
        try:
            from src.config import extract_embedded_cover
            emb_cover = extract_embedded_cover(path)
            if emb_cover and emb_cover.exists():
                self._cfg["session_cover_path"] = str(emb_cover)
                self._cfg["cover_path"] = str(emb_cover)
        except Exception:
            pass

        self._current_file = path
        name = Path(path).name
        self._hint_lbl.setText(name[:50] + ("…" if len(name) > 50 else ""))
        self._set_progress(0, f"Analizando  {name}")
        self._start_dots()

        if self._worker and self._worker.isRunning():
            try:
                self._worker.progress.disconnect()
                self._worker.finished.disconnect()
                self._worker.error.disconnect()
            except RuntimeError:
                pass
            self._worker.requestInterruption()
            self._worker.wait(2000)

        self._worker = AnalysisWorker(path)
        self._worker.progress.connect(self._set_progress)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_analysis_done(self, analysis, plan, grid, bpm: float, dur: float, key_res=None):
        self._stop_dots()
        self._analysis  = analysis
        self._plan      = plan
        self._beat_grid = grid
        self._key_res   = key_res

        # Mostrar la página de resultados ANTES de populate() para que el
        # WaveformWidget tenga geometría real cuando el loader dispare el dibujado
        self._stack.setCurrentIndex(1)
        self._fade_in_results()

        self._results.populate(analysis, plan, bpm, dur,
                               self._current_file, self._cfg, key_res=key_res)

        drops = len(analysis.drops())
        key_str = f"  ·  {key_res.camelot} ({key_res.notation})" if key_res else ""
        self._set_progress(100,
            f"✅  {Path(self._current_file).name}  ·  "
            f"{bpm:.1f} BPM{key_str}  ·  {drops} drop{'s' if drops != 1 else ''}"
        )

    def _on_error(self, msg: str):
        self._stop_dots()
        # Mostrar solo la última línea del traceback para no saturar
        lines = [ln for ln in msg.strip().splitlines() if ln.strip()]
        short = lines[-1] if lines else msg
        self._set_progress(0, f"❌  {short}")

    def _set_progress(self, pct: int, msg: str):
        self._progress_bar.setValue(pct)
        # Guardar el mensaje limpio para la animación de puntos
        self._progress_msg = msg.rstrip(".… ")
        self._progress_label.setText(msg)

    # ── Acciones ──────────────────────────────────────────────────────────

    def _regenerate(self, seed: int):
        # Usar el analysis que puede haber sido editado por el usuario
        # en la waveform (boundaries_changed actualiza self._results._analysis)
        analysis = self._results._analysis or self._analysis
        if analysis:
            self._plan    = build_preview_plan(analysis)
            self._analysis = analysis   # sincronizar el estado
            self._results.update_after_regen(self._plan)
            self._set_progress(100, "Plan actualizado con secciones editadas ✅")


    def _back_to_drop(self):
        self._stack.setCurrentIndex(0)
        self._hint_lbl.setText("Arrastra un track para comenzar")
        self._set_progress(0, "Listo — arrastra un track o pulsa Abrir archivo")

    def _set_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Carpeta donde guardar las previas",
            self._cfg.get("output_dir", "") or str(Path.home())
        )
        if folder:
            self._cfg["output_dir"] = folder
            save_cfg(self._cfg)
            if self._current_file:
                self._results.update_folder(self._current_file, self._cfg)

    def _open_export_folder(self):
        """Abre la carpeta de exportación en el explorador del sistema operativo."""
        out_dir = self._results._out_path or self._cfg.get("output_dir", "") or str(Path.home())
        self._reveal_in_os(out_dir)

    def _reveal_in_os(self, path_or_dir: str):
        """Abre la ruta o selecciona el archivo en Finder / Explorador de archivos."""
        try:
            import subprocess
            p = Path(path_or_dir)
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
                target = str(p if p.is_dir() else p.parent)
                subprocess.run(["xdg-open", target])
        except Exception:
            pass

    def _generate(self):
        plan = self._results._plan or self._plan
        if not (plan and self._beat_grid and self._current_file):
            return

        custom_name = self._results.get_export_name()
        options = self._results.get_export_options()
        wav = options.get("export_wav", True)
        mp3 = options.get("export_mp3", True)
        flac = options.get("export_flac", False)
        video = options.get("export_video", False)
        if not any([wav, mp3, flac, video]):
            self._set_progress(0, "⚠  Selecciona al menos un formato para exportar")
            return

        seed = self._results.get_seed()
        metadata = self._results.get_branding_metadata()
        cover_path = self._results.get_branding_cover_path()
        self._results.persist_branding_if_requested()

        cfg = dict(self._cfg)
        cfg.update(options)
        cfg["custom_name"]  = custom_name
        cfg["tempo_mode"]   = self._results.get_tempo_mode()
        cfg["tempo_events"] = self._results.get_tempo_events()
        cfg["metadata"]   = metadata
        # Usar la carátula del branding card si hay una; si no, la cover de sesión (embebida)
        cfg["cover_path"] = cover_path or self._cfg.get("cover_path", "")
        if hasattr(self, "_key_res") and self._key_res:
            cfg["key_str"] = f"{self._key_res.camelot} · {self._key_res.notation}"

        self._results.on_export_start()
        self._set_progress(0, "Generando previa")
        self._start_dots()

        if self._export_worker and self._export_worker.isRunning():
            try:
                self._export_worker.progress.disconnect()
                self._export_worker.finished.disconnect()
                self._export_worker.error.disconnect()
            except RuntimeError:
                pass
            self._export_worker.requestInterruption()
            self._export_worker.wait(2000)

        self._export_worker = ExportWorker(
            self._current_file, plan, self._beat_grid, cfg, seed=seed
        )
        self._export_worker.progress.connect(self._set_progress)
        self._export_worker.finished.connect(self._on_export_done)
        self._export_worker.error.connect(self._on_export_error)
        self._export_worker.start()

    def _on_export_done(self, generated: list, seed: int):
        self._stop_dots()
        self._results.on_export_done(generated, seed)
        if generated:
            names = ", ".join(Path(p).name for p in generated)
            folder = str(Path(generated[0]).parent)
            self._set_progress(100,
                f"✅  Guardado en: {folder}  ·  ({names})"
            )
            self._results._btn_open_folder.setStyleSheet(_btn("#059669", "#ffffff", "#10b981", radius=5, fs=10.5))
        else:
            self._set_progress(0, "⚠  No se generaron archivos.")

    def _on_export_error(self, msg: str):
        self._stop_dots()
        lines = [ln for ln in msg.strip().splitlines() if ln.strip()]
        short = lines[-1] if lines else msg
        self._results._btn_generate.setEnabled(True)
        self._results._btn_generate.setText("▶   GENERAR PREVIA")
        self._results._apply_generate_style(True)
        self._set_progress(0, f"❌  {short}")

    # ── Drag global (ventana) ─────────────────────────────────────────────

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

        audio_files = []
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in AUDIO_EXTS:
                audio_files.append(path)

        if len(audio_files) > 1:
            self._open_batch_dialog(audio_files)
        elif len(audio_files) == 1:
            self._load_file(audio_files[0])

    def _open_batch_dialog(self, initial_files: list | None = None):
        try:
            from src.ui.batch import BatchDialog
            dlg = BatchDialog(initial_files=initial_files, parent=self)
            dlg.exec()
        except Exception as ex:
            self._set_progress(0, f"❌ Error abriendo Modo Lote: {ex}")

    def _update_watch_button_style(self):
        if not hasattr(self, "_btn_watch"):
            return
        if self._watching and self._watched_folder:
            f_name = Path(self._watched_folder).name
            short_n = f_name if len(f_name) <= 12 else f_name[:10] + "…"
            self._btn_watch.setText(f"👁️ {short_n}")
            self._btn_watch.setStyleSheet("""
                QPushButton {
                    background: #0d2818;
                    color: #00ff88;
                    border: 1px solid #00ff88;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 0 6px;
                }
                QPushButton:hover {
                    background: #143d24;
                }
            """)
        else:
            self._btn_watch.setText("👁️ Vigilar Carpeta")
            self._btn_watch.setStyleSheet(_btn(BG3, TEXT_MID, BG4, radius=4, fs=10))

    def _show_recent_menu(self):
        from src.config import get_recent_files
        recents = get_recent_files(self._cfg)
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {BG2};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 14px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {BG4};
                color: {ACCENT};
            }}
        """)
        if not recents:
            act = menu.addAction("No hay archivos recientes")
            act.setEnabled(False)
        else:
            for item in recents:
                p = Path(item)
                lbl = p.name if len(p.name) <= 50 else p.name[:47] + "…"
                action = menu.addAction(f"🎵 {lbl}")
                action.setData(item)
                action.setToolTip(item)
            menu.addSeparator()
            act_clear = menu.addAction("🗑️ Borrar historial")
            act_clear.setData("__clear__")

        pos = self._btn_recents.mapToGlobal(QPoint(0, self._btn_recents.height() + 2))
        selected_act = menu.exec(pos)
        if selected_act:
            data = selected_act.data()
            if data == "__clear__":
                self._cfg["recent_files"] = []
                from src.config import save as save_cfg
                save_cfg(self._cfg)
            elif data and Path(data).exists():
                self._load_file(data)

    def _toggle_watch_folder(self):
        if self._watching:
            self._watching = False
            self._watch_timer.stop()
            self._cfg["watch_folder_enabled"] = False
            from src.config import save as save_cfg
            save_cfg(self._cfg)
            self._update_watch_button_style()
            self._set_progress(0, "👁️ Carpeta vigilada desactivada.")
            return

        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta para vigilar (Watch Folder)",
            self._watched_folder or str(Path.home())
        )
        if not folder:
            return

        self._watched_folder = folder
        self._cfg["watch_folder_path"] = folder
        self._cfg["watch_folder_enabled"] = True
        from src.config import save as save_cfg
        save_cfg(self._cfg)

        # Sembrar los existentes para no procesar todo de golpe al activar
        self._watched_processed.clear()
        p_dir = Path(folder)
        for ext in AUDIO_EXTS:
            for f in p_dir.glob(f"*{ext}"):
                self._watched_processed.add(str(f.resolve()))
            for f in p_dir.glob(f"*{ext.upper()}"):
                self._watched_processed.add(str(f.resolve()))

        self._watching = True
        self._watch_timer.start()
        self._update_watch_button_style()
        self._set_progress(0, f"👁️ Vigilando: {Path(folder).name} (escanea nuevos audios cada 4s)")

    def _scan_watch_folder(self):
        if not self._watching or not self._watched_folder:
            return
        p_dir = Path(self._watched_folder)
        if not p_dir.is_dir():
            return

        # Si ya hay un análisis o exportación en curso, esperar
        if (self._worker and self._worker.isRunning()) or (self._export_worker and self._export_worker.isRunning()):
            return

        new_files = []
        for ext in AUDIO_EXTS:
            for f in p_dir.glob(f"*{ext}"):
                rf = str(f.resolve())
                if rf not in self._watched_processed:
                    try:
                        sz1 = f.stat().st_size
                        if sz1 > 10000:
                            new_files.append(f)
                    except Exception:
                        pass
            for f in p_dir.glob(f"*{ext.upper()}"):
                rf = str(f.resolve())
                if rf not in self._watched_processed:
                    try:
                        sz1 = f.stat().st_size
                        if sz1 > 10000:
                            new_files.append(f)
                    except Exception:
                        pass

        if new_files:
            target = new_files[0]
            self._watched_processed.add(str(target.resolve()))
            self._set_progress(0, f"👁️ Detectado nuevo tema en carpeta vigilada: {target.name}")
            self._load_file(str(target))

    def keyPressEvent(self, e):
        # Atajos de reproducción para DJs cuando no se está editando un campo de texto
        focus = QApplication.focusWidget()
        in_input = isinstance(focus, (QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox))
        if not in_input and hasattr(self, "_results") and self._results._player:
            player = self._results._player
            k = e.key()
            if k == Qt.Key_Space:
                player.toggle_play()
                e.accept()
                return
            elif k == Qt.Key_Left:
                player.rewind(5.0)
                e.accept()
                return
            elif k == Qt.Key_Right:
                player.forward(5.0)
                e.accept()
                return
            elif k in (Qt.Key_Home, Qt.Key_0):
                player.seek(0.0)
                e.accept()
                return
            elif k == Qt.Key_Escape:
                player.stop()
                e.accept()
                return
            elif k == Qt.Key_M:
                player.toggle_mute()
                e.accept()
                return
        super().keyPressEvent(e)

    def closeEvent(self, event):
        """Detiene de forma limpia todos los hilos antes del cierre para evitar QThread Destroyed abort."""
        self._cleanup_threads()
        super().closeEvent(event)

    def _cleanup_threads(self):
        if hasattr(self, "_watch_timer") and self._watch_timer.isActive():
            self._watch_timer.stop()
        for worker_name in ["_worker", "_export_worker"]:
            w = getattr(self, worker_name, None)
            if w and w.isRunning():
                try:
                    w.progress.disconnect()
                    w.finished.disconnect()
                    w.error.disconnect()
                except Exception:
                    pass
                w.requestInterruption()
                w.wait(600)
                if w.isRunning():
                    w.terminate()
                    w.wait(200)

        if hasattr(self, "_results") and getattr(self._results, "_waveform", None):
            wf = self._results._waveform
            if hasattr(wf, "cleanup_threads"):
                wf.cleanup_threads()


# ── Entry point ───────────────────────────────────────────────────────────────

def launch(initial_file: str = ""):
    if sys.platform == "win32":
        try:
            from PySide6.QtCore import Qt, QCoreApplication
            QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
        except Exception:
            pass

    try:
        from src.main import _log_startup
    except Exception:
        def _log_startup(msg): pass

    _log_startup("Iniciando QApplication...")
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    # Fuente del sistema nativa (sin avisos de alias)
    family_to_use = ".AppleSystemUIFont" if sys.platform == "darwin" else "Segoe UI"
    app.setFont(QFont(family_to_use, 12))

    _log_startup("Instanciando MainWindow...")
    win = MainWindow(initial_file=initial_file)
    app.aboutToQuit.connect(win._cleanup_threads)

    _log_startup("Mostrando ventana principal...")
    win.show()
    win.raise_()
    win.activateWindow()

    _log_startup("Ventana principal visible. Ejecutando app.exec()...")
    sys.exit(app.exec())


if __name__ == "__main__":
    launch(sys.argv[1] if len(sys.argv) > 1 else "")
