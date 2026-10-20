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
    QButtonGroup, QApplication, QCheckBox, QFileDialog, QGraphicsOpacityEffect,
    QHBoxLayout, QLabel, QLineEdit, QTextEdit, QMainWindow, QProgressBar,
    QPushButton, QStackedWidget, QTableWidget, QSpinBox, QDoubleSpinBox,
    QComboBox, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
    QFrame, QTabWidget, QAbstractItemView, QSizePolicy,
    QScrollArea, QGraphicsDropShadowEffect, QMenu, QSplashScreen, QMessageBox,
)

_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_ROOT))

from src.config import (
    load as load_cfg, save as save_cfg, get_output_dir, get_assets_dir,
    get_active_cover_path, save_custom_cover, get_edition,
)
_ASSETS_DIR = get_assets_dir()

from src.analysis.bpm import detect_beat_grid, SR_ANALYSIS
from src.analysis.structure import analyze_structure, SectionType
from src.analysis.segments import build_preview_plan
from src.engine.export import build_preview_audio, export_files, output_paths
from src.engine.variations import compute_preview_tempo_curve
from src.ui import anim as _anim
from src.engine.video_neon import apply_look, detect_look, match_aspect, normalize_custom
from src import i18n
from src.i18n import tr

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

try:
    from src.__version__ import __version__ as _APP_VERSION
except Exception:
    _APP_VERSION = "2.5"
VERSION   = _APP_VERSION
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
            self.progress.emit(25, "Detectando BPM, beat grid y tonalidad…")
            # BPM y tonalidad son independientes: se calculan a la vez (mismo resultado, menos espera)
            from src.analysis.fastdsp import pmap
            grid, key_res = pmap([lambda: detect_beat_grid(y, sr), lambda: detect_musical_key(y, sr)])
            if self.isInterruptionRequested():
                return
            self.progress.emit(45, "Tonalidad Armónica y Camelot detectada")
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
                export_mp3=self.cfg.get("export_mp3", True) or bool(self.cfg.get("export_video", False)),
                export_flac=self.cfg.get("export_flac", False),
                export_aiff=self.cfg.get("export_aiff", False),
                export_video=self.cfg.get("export_video", False),
                custom_name=self.cfg.get("custom_name"),
                video_aspects=self.cfg.get("aspect_ratios") or [self.cfg.get("aspect_ratio", "9:16")],
            )
            metadata = dict(self.cfg.get("metadata") or {})
            if self.beat_grid and hasattr(self.beat_grid, "bpm"):
                metadata["bpm"] = self.beat_grid.bpm
            if self.cfg.get("key_str"):
                metadata["key"] = self.cfg.get("key_str")
            metadata["video_palette"]    = self.cfg.get("video_palette", "crimson")
            metadata["video_promo_text"] = self.cfg.get("video_promo_text", "RADICAL RECORDS · PROMO EXCLUSIVA")
            metadata["video_title"]      = self.cfg.get("video_title", "")
            metadata["video_end"]        = self.cfg.get("video_end", "brand")
            metadata["video_custom"]     = self.cfg.get("video_custom")
            metadata["aspect_ratio"]     = self.cfg.get("aspect_ratio", "9:16")
            if self.cfg.get("mp3_kbps"):
                metadata["mp3_kbps"] = int(self.cfg["mp3_kbps"])

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

def _btn_icon(bg: str, fg: str, bg_hv: str, radius: int = 5, fs: int = 10) -> str:
    """Botón pequeño de un solo símbolo (▲ ▼ ▶ 📍 ✕): sin relleno lateral para que el símbolo se vea."""
    return f"""
        QPushButton {{ background: {bg}; color: {fg}; border: none; border-radius: {radius}px;
                      font-size: {fs}px; font-weight: 700; padding: 0; }}
        QPushButton:hover {{ background: {bg_hv}; }}
        QPushButton:disabled {{ background: {BG3}; color: {TEXT_DIM}; }}
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

# ── Splash Screen ─────────────────────────────────────────────────────────────

def _build_splash_pixmap(pct: int = 0, msg: str = "Iniciando…") -> QPixmap:
    """Pinta el splash sobre un QPixmap — sin widgets, sin transparencia problemática."""
    W, H = 520, 290
    pix = QPixmap(W, H)
    pix.fill(QColor(BG2))

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Marco rojo
    p.setPen(QPen(QColor(ACCENT), 2))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(1, 1, W - 2, H - 2, 14, 14)

    # Línea decorativa interior
    p.setPen(QPen(QColor(ACCENT + "33"), 1))
    p.drawRoundedRect(6, 6, W - 12, H - 12, 10, 10)

    # Logo
    logo_file = None
    for cand in [_ASSETS_DIR / "logo_emblem.png", _ASSETS_DIR / "logo.png",
                 _ASSETS_DIR / "logo_emblem_red.png"]:
        if cand.exists():
            logo_file = str(cand)
            break
    if logo_file:
        lp = QPixmap(logo_file)
        if not lp.isNull():
            lp = lp.scaled(84, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap((W - 84) // 2, 24, lp)

    # Título AUTOPREVIAS
    from PySide6.QtGui import QFont as _QFont
    f = _QFont()
    f.setPixelSize(24)
    f.setBold(True)
    f.setLetterSpacing(_QFont.AbsoluteSpacing, 5)
    p.setFont(f)
    p.setPen(QColor(TEXT))
    p.drawText(QRect(0, 118, W, 32), Qt.AlignCenter, "AUTOPREVIAS")

    # Subtítulo
    f2 = _QFont()
    f2.setPixelSize(10)
    f2.setBold(True)
    f2.setLetterSpacing(_QFont.AbsoluteSpacing, 2)
    p.setFont(f2)
    p.setPen(QColor(ACCENT))
    p.drawText(QRect(0, 154, W, 18), Qt.AlignCenter, "RADICAL RECORDS  ·  STUDIO")

    # Barra de progreso — fondo
    bx, by, bw, bh = 70, 190, W - 140, 6
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(BG4))
    p.drawRoundedRect(bx, by, bw, bh, 3, 3)

    # Barra de progreso — relleno con gradiente
    if pct > 0:
        fill = max(8, int(bw * pct / 100))
        grad = QLinearGradient(bx, 0, bx + bw, 0)
        grad.setColorAt(0.0, QColor(ACCENT))
        grad.setColorAt(1.0, QColor("#ff8c00"))
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(bx, by, fill, bh, 3, 3)

    # Porcentaje
    f3 = _QFont()
    f3.setPixelSize(11)
    f3.setBold(True)
    p.setFont(f3)
    p.setPen(QColor(TEXT_MID))
    p.drawText(QRect(0, 202, W, 18), Qt.AlignCenter, f"{pct}%")

    # Mensaje de estado
    f4 = _QFont()
    f4.setPixelSize(10)
    p.setFont(f4)
    p.setPen(QColor(TEXT_DIM))
    p.drawText(QRect(0, 224, W, 16), Qt.AlignCenter, msg)

    p.end()
    return pix


class SplashWindow(QSplashScreen):
    """Splash screen usando QSplashScreen estándar — sin ventanas fantasma."""

    _STEPS = [
        (15,  "Cargando motor espectral…"),
        (35,  "Preparando análisis de BPM…"),
        (60,  "Iniciando renderizador de audio…"),
        (85,  "Cargando interfaz de usuario…"),
    ]

    def __init__(self):
        pix = _build_splash_pixmap(0, "Iniciando…")
        super().__init__(pix, Qt.WindowStaysOnTopHint)
        self._pct = 0
        self._cur_msg = "Iniciando…"

        self._fake_pct = 0
        self._fake_timer = QTimer(self)
        self._fake_timer.timeout.connect(self._fake_step)
        self._fake_timer.start(25)

    def _fake_step(self):
        if self._fake_pct >= 88:
            self._fake_timer.stop()
            return
        self._fake_pct = min(88, self._fake_pct + 2)
        msg = self._cur_msg
        for pct, m in self._STEPS:
            if self._fake_pct >= pct:
                msg = m
        self._cur_msg = msg
        self._repaint(self._fake_pct, msg)

    def _repaint(self, pct: int, msg: str):
        self._pct = pct
        self.setPixmap(_build_splash_pixmap(pct, msg))
        self.repaint()

    def set_progress(self, pct: int, msg: str):
        self._fake_timer.stop()
        self._cur_msg = msg
        self._repaint(pct, msg)

    def finish(self, main_window):
        self._fake_timer.stop()
        self._repaint(100, "¡Todo listo!")
        super().finish(main_window)


# ── Página de análisis en curso ────────────────────────────────────────────────

class _PulseLogo(QWidget):
    """Logo que «late» con un anillo de luz. Se dibuja con QPainter (escala y brillo sin tocar el tamaño del widget), así el
    diseño de la pantalla no se recalcula en cada fotograma y la animación va fluida."""

    SIZE = 190

    def __init__(self, pix=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._pix = pix
        self._phase = 0.0

    def set_phase(self, phase: float):
        self._phase = phase
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        t = (math.sin(self._phase) + 1) / 2
        c = self.rect().center()
        # anillos de luz que se abren y se desvanecen
        for k, r0 in enumerate((58, 74)):
            tt = (t + k * 0.5) % 1.0
            col = QColor(ACCENT)
            col.setAlpha(int(70 * (1 - tt)))
            p.setPen(QPen(col, 2.0))
            p.setBrush(Qt.NoBrush)
            rr = r0 + 22 * tt
            p.drawEllipse(c, rr, rr)
        if self._pix is not None:
            sc = 0.92 + 0.16 * t
            p.translate(c)
            p.scale(sc, sc)
            w, h = self._pix.width(), self._pix.height()
            p.drawPixmap(-w // 2, -h // 2, self._pix)
        else:
            p.setPen(QColor(TEXT))
            f = p.font()
            f.setPixelSize(72)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter, "🎧")
        p.end()


class AnalysisPage(QWidget):
    """Pantalla que se muestra mientras se analiza un archivo: logo animado + progreso."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {BG};")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(24)
        lay.setContentsMargins(40, 40, 40, 40)

        # Logo grande animado
        logo_file = None
        for cand in [_ASSETS_DIR / "logo_emblem.png", _ASSETS_DIR / "logo.png",
                     _ASSETS_DIR / "logo_emblem_red.png"]:
            if cand.exists():
                logo_file = str(cand)
                break
        self._logo_pix_orig = None
        if logo_file:
            pix = QPixmap(logo_file)
            if not pix.isNull():
                self._logo_pix_orig = pix.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._logo_lbl = _PulseLogo(self._logo_pix_orig)
        lay.addWidget(self._logo_lbl, alignment=Qt.AlignCenter)

        # Nombre del archivo
        self._file_lbl = QLabel("Analizando…")
        self._file_lbl.setAlignment(Qt.AlignCenter)
        self._file_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 15px; font-weight: 700; background: transparent; border: none;"
        )
        lay.addWidget(self._file_lbl)

        # Mensaje de estado
        self._status_lbl = QLabel("")
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet(
            f"color: {TEXT_MID}; font-size: 11px; background: transparent; border: none;"
        )
        lay.addWidget(self._status_lbl)

        # Barra de progreso
        bar_frame = QFrame()
        bar_frame.setFixedWidth(380)
        bar_lay = QVBoxLayout(bar_frame)
        bar_lay.setContentsMargins(0, 0, 0, 0)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background: {BG3};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ACCENT}, stop:1 #ff8c00);
                border-radius: 3px;
            }}
        """)
        bar_lay.addWidget(self._bar)
        lay.addWidget(bar_frame, alignment=Qt.AlignCenter)

        # Animación del logo
        self._pulse_phase = 0.0
        self._scale = 1.0
        self._anim_timer = QTimer(self)
        self._anim_timer.setTimerType(Qt.PreciseTimer)
        self._anim_timer.timeout.connect(self._tick)

    def start(self, filename: str):
        self._file_lbl.setText(filename[:60] + ("…" if len(filename) > 60 else ""))
        i18n.set_text(self._status_lbl, "Preparando análisis…")
        self._bar.setValue(0)
        self._anim_timer.start(16)            # 60 fps: solo se repinta el logo, el resto de la pantalla no se toca

    def stop(self):
        self._anim_timer.stop()

    def update_progress(self, pct: int, msg: str):
        self._bar.setValue(pct)
        i18n.set_text(self._status_lbl, msg)

    def _tick(self):
        self._pulse_phase = (self._pulse_phase + 0.045) % (2 * math.pi)
        self._logo_lbl.set_phase(self._pulse_phase)


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

    def hideEvent(self, event):
        super().hideEvent(event)
        if self._pulse_timer.isActive():
            self._pulse_timer.stop()

    def _build_ui(self):
        # v5: inicio guiado — título, zona para soltar el tema, los 3 pasos explicados y accesos a la guía / último tema
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)
        outer.setContentsMargins(20, 0, 20, 0)
        outer.setSpacing(14)

        title = QLabel("Crea la previa de tu tema en 3 pasos")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size: 26px; font-weight: 900; color: {TEXT}; background: transparent; border: none; letter-spacing: -0.5px;")
        outer.addWidget(title)
        self._lbl_home_sub = QLabel("Sin conocimientos técnicos: tú eliges el tema y para qué lo quieres; AutoPrevias hace el resto.")
        self._lbl_home_sub.setAlignment(Qt.AlignCenter)
        self._lbl_home_sub.setStyleSheet(f"font-size: 12.5px; color: {TEXT_MID}; background: transparent; border: none;")
        outer.addWidget(self._lbl_home_sub)

        # Tarjeta para soltar el tema (la que resalta el recorrido)
        self._card = GlowFrame()
        self._card.setObjectName("drop-card")
        self._card.setMinimumSize(780, 230)
        self._card.setMaximumWidth(1100)
        self._card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._card.setStyleSheet(f"""
            QFrame#drop-card {{
                background: qlineargradient(x1:0.5,y1:0.5,x2:1,y2:1, stop:0 #1c0b10, stop:0.6 #0f0a0d, stop:1 #0a0b0e);
                border: none;
                border-radius: 20px;
            }}
        """)
        lay = QVBoxLayout(self._card)
        lay.setContentsMargins(40, 18, 40, 20)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignCenter)

        emblem_path = _ASSETS_DIR / "logo_emblem.png"
        if not emblem_path.exists():
            emblem_path = _ASSETS_DIR / "logo_emblem_red.png"
        self._icon_pix_normal = None
        self._icon_lbl = QLabel("🎵")
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet("font-size: 44px; background: transparent; border: none;")
        if emblem_path.exists():
            pix = QPixmap(str(emblem_path))
            if not pix.isNull():
                scaled = pix.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._icon_lbl.setPixmap(scaled)
                self._icon_pix_normal = scaled
        lay.addWidget(self._icon_lbl)
        t2 = QLabel("Arrastra aquí tu tema")
        t2.setAlignment(Qt.AlignCenter)
        t2.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {TEXT}; background: transparent; border: none;")
        lay.addWidget(t2)
        sub = QLabel("WAV  ·  MP3  ·  FLAC  ·  AIFF  ·  M4A")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"font-size: 10.5px; color: {TEXT_DIM}; letter-spacing: 3px; background: transparent; border: none; font-weight: 700;")
        lay.addWidget(sub)
        o = QLabel("o")
        o.setAlignment(Qt.AlignCenter)
        o.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent; border: none;")
        lay.addWidget(o)
        self._btn_open = QPushButton("Elegir archivo…")
        self._btn_open.setFixedHeight(48)
        self._btn_open.setMinimumWidth(220)
        from src.ui import theme5 as _T5
        self._btn_open.setStyleSheet(_T5.cta_css(12, 14))
        self._btn_open.setCursor(Qt.PointingHandCursor)
        self._btn_open.clicked.connect(self._open_dialog)
        lay.addWidget(self._btn_open, alignment=Qt.AlignCenter)
        # «Seguir con …»: el último tema abierto (si sigue existiendo)
        self._btn_continue = QPushButton("")
        self._btn_continue.setFixedHeight(34)
        self._btn_continue.setCursor(Qt.PointingHandCursor)
        self._btn_continue.setStyleSheet(_T5.ghost_css(10, 11.5))
        self._btn_continue.clicked.connect(lambda _=False: self._continue_last())
        outer.addWidget(self._card, 0, Qt.AlignCenter)

        # Los 3 pasos (círculos numerados)
        steps = QHBoxLayout()
        steps.setSpacing(30)
        steps.setAlignment(Qt.AlignCenter)
        self._home_steps = []
        for n, head, body in (
            ("1", "Suelta tu tema", "WAV, MP3, FLAC… Lo analizo yo: BPM, tonalidad y estructura."),
            ("2", "Revisa la previa", "AutoPrevias la monta sola; tú solo la ajustas si quieres."),
            ("3", "Descarga", "Audio, vídeo animado y carátula, listos para publicar."),
        ):
            c = QWidget()
            c.setFixedWidth(250)
            c.setMinimumHeight(118)
            c.setStyleSheet("background: transparent;")
            cl = QVBoxLayout(c)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(4)
            cl.setAlignment(Qt.AlignHCenter)
            num = QLabel(n)
            num.setFixedSize(30, 30)
            num.setAlignment(Qt.AlignCenter)
            num.setStyleSheet(f"color: white; font-size: 13px; font-weight: 900; border-radius: 15px; background: {ACCENT};")
            cl.addWidget(num, 0, Qt.AlignHCenter)
            h = QLabel(head)
            h.setAlignment(Qt.AlignCenter)
            h.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 800; background: transparent; border: none;")
            b = QLabel(body)
            b.setWordWrap(True)
            b.setAlignment(Qt.AlignCenter)
            b.setStyleSheet(f"color: {TEXT_MID}; font-size: 11px; background: transparent; border: none;")
            cl.addWidget(h)
            cl.addWidget(b)
            steps.addWidget(c)
            self._home_steps.append(c)
        outer.addLayout(steps)

        chips = QHBoxLayout()
        chips.setSpacing(10)
        chips.setAlignment(Qt.AlignCenter)
        self._btn_guide = QPushButton("🎓  Guía de 2 minutos")
        self._btn_guide.setFixedHeight(34)
        self._btn_guide.setCursor(Qt.PointingHandCursor)
        self._btn_guide.setStyleSheet(_T5.ghost_css(10, 11.5))
        chips.addWidget(self._btn_guide)
        chips.addWidget(self._btn_continue)
        outer.addLayout(chips)
        self.refresh_continue()

    # — «Seguir con…» —
    def last_track(self) -> str:
        try:
            from src.config import get_recent_files
            for f in get_recent_files():
                if Path(f).exists():
                    return f
        except Exception:
            pass
        return ""

    def refresh_continue(self):
        last = self.last_track()
        self._btn_continue.setVisible(bool(last))
        if last:
            name = Path(last).stem
            name = name if len(name) <= 24 else name[:22] + "…"
            self._btn_continue.setText(tr("↻  Seguir con «{n}»", n=name))
            self._btn_continue.setToolTip(last)

    def _continue_last(self):
        last = self.last_track()
        if last:
            self.file_dropped.emit(last)

    def showEvent(self, event):
        self.refresh_continue()
        super().showEvent(event)
        if not self._pulse_timer.isActive():
            self._pulse_timer.start(66)

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
            self, tr("Selecciona un tema de audio"), "",
            tr("Audio (*.wav *.mp3 *.flac *.aiff *.aif *.m4a)")
        )
        if path:
            self.file_dropped.emit(path)


# ── Stat Card ─────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    """Tarjeta de estadística individual con valor grande y etiqueta. Opcional: editable con doble clic."""
    def __init__(self, label: str, value: str = "—",
                 accent: str = TEXT, on_edit=None, parent=None):
        super().__init__(parent)
        self._accent  = accent
        self._on_edit = on_edit
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

        if on_edit:
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip("Doble clic para corregir")

    def mouseDoubleClickEvent(self, event):
        if self._on_edit:
            self._on_edit()
        super().mouseDoubleClickEvent(event)

    def set_value(self, v: str, animate: bool = False):
        if animate:
            from src.ui import anim
            anim.count_up(self._val_lbl.setText, v, owner=self)       # los números «cuentan» hasta su valor
        else:
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
                self, tr("Seleccionar carátula para la previa"), "",
                tr("Imágenes (*.png *.jpg *.jpeg *.webp);;Todos los archivos (*.*)")
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
            i18n.set_text(self._badge, "PERSONALIZADA")
            self._badge.setStyleSheet(f"""
                background: {GREEN}22; color: {GREEN};
                font-size: 8.5px; font-weight: 700;
                padding: 2px 6px; border-radius: 4px; border: 1px solid {GREEN}44;
            """)
            self._btn_reset_cover.setVisible(True)
        else:
            i18n.set_text(self._badge, "OFICIAL")
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

    def apply_signature(self, sig: dict):
        """Aplica una firma guardada (solo las claves presentes) y su carátula si existe."""
        for key, edit in (("artist", self._edit_artist), ("label", self._edit_label),
                          ("album", self._edit_album), ("genre", self._edit_genre),
                          ("comment", self._edit_comment)):
            if key in sig:
                edit.setText(sig.get(key) or "")
        cover = sig.get("cover_path") or ""
        if cover and Path(cover).exists():
            self._drop_area.set_cover(cover)

    def persist_if_requested(self):
        c = load_cfg()
        # Los campos de texto siempre se guardan al generar (para no perderse entre sesiones)
        c["tag_artist"]  = self._edit_artist.text().strip()
        c["tag_label"]   = self._edit_label.text().strip()
        c["tag_album"]   = self._edit_album.text().strip()
        c["tag_genre"]   = self._edit_genre.text().strip()
        c["tag_comment"] = self._edit_comment.text().strip()

        # La carátula personalizada y el flag "por defecto" solo se guardan si el usuario marcó "Recordar"
        if self._chk_remember.isChecked():
            c["save_signature_default"] = True
            cover_p = self._drop_area.get_cover_path()
            if cover_p:
                saved_cover = save_custom_cover(cover_p)
                c["custom_cover_path"] = saved_cover
            else:
                c["custom_cover_path"] = ""

        # Persistir también las preferencias de exportación del ResultPanel padre
        parent = self.parent()
        while parent is not None and not hasattr(parent, "_speed_mode"):
            parent = parent.parent() if hasattr(parent, "parent") else None
        if parent and hasattr(parent, "_speed_mode"):
            c["speed_mode"]    = parent._speed_mode
            if hasattr(parent, "_combo_video_pal"):
                c["video_palette"] = parent._combo_video_pal.currentData()
            if hasattr(parent, "_combo_aspect"):
                c["aspect_ratio"]  = parent._combo_aspect.currentData()
                c["aspect_ratios"] = parent.selected_aspects()
            if hasattr(parent, "_combo_vend"):
                c["video_end"]     = parent._combo_vend.currentData()
            if hasattr(parent, "_video_custom"):
                c["video_custom"]  = parent._video_custom
            if hasattr(parent, "_chk_fx_flanger"):
                c["fx_flanger"]      = parent._chk_fx_flanger.isChecked()
                c["fx_filter_sweep"] = parent._chk_fx_filter.isChecked()
                c["studio_mastering"] = parent._chk_fx_master.isChecked()

        save_cfg(c)


# ── Panel de resultados ───────────────────────────────────────────────────────


class _VideoCard(QFrame):
    """Tarjeta «Vídeo animado»: acepta imágenes arrastradas para usarlas como fondo (Plus)."""
    imageDropped = Signal(str)
    _EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("vcard")
        self.setAcceptDrops(True)
        self._set_hover(False)

    def _set_hover(self, on: bool):
        border = ACCENT if on else BORDER
        bg = "#1d0f14" if on else "qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #151922, stop:1 #10131a)"
        self.setStyleSheet(f"QFrame#vcard {{ background: {bg}; border: 1px solid {border}; border-radius: 16px; }}"
                           " QFrame#vcard QLabel { background: transparent; border: none; }")

    def _image_in(self, md) -> str:
        for u in md.urls():
            p = u.toLocalFile()
            if p and p.lower().endswith(self._EXT):
                return p
        return ""

    def dragEnterEvent(self, e):
        if self._image_in(e.mimeData()):
            self._set_hover(True)
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self._set_hover(False)
        e.accept()

    def dropEvent(self, e):
        self._set_hover(False)
        p = self._image_in(e.mimeData())
        if p:
            e.acceptProposedAction()
            self.imageDropped.emit(p)


class ResultPanel(QWidget):
    regen_requested       = Signal(int)   # con seed
    folder_requested      = Signal()
    open_folder_requested = Signal()
    new_file_requested    = Signal()
    load_file_requested   = Signal(str)   # path de nuevo audio a cargar directamente
    generate_requested    = Signal()
    play_requested        = Signal(str)   # path del archivo para reproducir
    bpm_corrected         = Signal(float) # BPM corregido manualmente por el usuario
    status_message        = Signal(str)   # avisos breves para la barra de estado
    change_destination_requested = Signal()   # v5: «Cambiar destino» (vuelve a la pantalla de elegir destino)

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
        self._voice_drop_dur_sec  = 0.0   # duración del archivo de voice drop
        self._promo_saved         = None  # formatos del usuario mientras el modo promo está activo
        self._build_ui()
        from src.ui import v5_layout
        v5_layout.assemble(self, get_edition() == "plus")       # v5: los pasos ② y ③ con el diseño nuevo
        self._apply_edition_limits()
        # v5: deshacer/rehacer de cortes y efectos. Una «foto» del estado editable cada 300 ms: si cambió y ya no se mueve
        # (el usuario soltó el ratón) se guarda como un paso; así cubre TODAS las formas de editar sin tocar cada una.
        from src.ui.undo import History
        self._hist = History()
        self._hist_ready = False
        self._hist_restoring = False
        self._hist_pending = None
        self._hist_timer = QTimer(self)
        self._hist_timer.setInterval(300)
        self._hist_timer.timeout.connect(self._hist_poll)
        self._hist_timer.start()

    def _build_ui(self):
        # v5: asistente de 3 pasos. ① Tu tema (ya analizado) · ② Tu previa · ③ Exportar. Cada paso es un contenedor;
        # el que no toca se oculta (no ocupa sitio). Los widgets conservan sus nombres de siempre.
        from src.ui.wizard import WizardStepper
        shell = QVBoxLayout(self)
        shell.setSpacing(10)
        shell.setContentsMargins(0, 0, 0, 0)
        self._stepper = WizardStepper()
        self._stepper.step_clicked.connect(self._on_stepper_clicked)
        shell.addWidget(self._stepper)
        self._page2 = QWidget()
        self._page3 = QWidget()
        for _pg in (self._page2, self._page3):
            _pg.setStyleSheet("background: transparent;")
        root = QVBoxLayout(self._page2)
        root.setSpacing(10)
        root.setContentsMargins(0, 0, 0, 0)
        root3 = QVBoxLayout(self._page3)
        root3.setSpacing(10)
        root3.setContentsMargins(0, 0, 0, 0)
        shell.addWidget(self._page2)
        shell.addWidget(self._page3, 1)
        self._wizard_step = 2
        self._studio = False
        self._studio_view = None
        self._studio_entered = False
        self._shell = shell

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
            self._waveform.setMaximumHeight(340)         # v5: el paso ② cabe mejor en pantalla (antes crecía con la ventana)
            self._waveform.seek_requested.connect(self._on_waveform_seek)
            self._waveform.boundaries_changed.connect(self._on_boundaries_changed)
            self._waveform.cuts_changed.connect(self._on_waveform_cuts_changed)
            self._waveform.set_fx_enabled(True)               # efectos arrastrables a la onda (Basic y Plus)
            self._waveform.cut_play_requested.connect(self._audition_cut)      # ▶ sobre cada corte de la onda
            self._waveform.cut_remove_requested.connect(self._remove_cut)      # ✕ sobre cada corte de la onda
            self._waveform.voice_drop_moved.connect(self._on_voice_drop_marker_moved)
            self._waveform.fx_audition_requested.connect(self._audition_fx)      # ▶ Oír el efecto seleccionado
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
            self._player.position_changed.connect(self._on_audition_tick)
            pl.addWidget(self._player)
            root.addWidget(player_frame)
        else:
            self._player = None

        # ── 3. STATS STRIP ────────────────────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(6)

        self._card_file  = StatCard("ARCHIVO",   "—",   TEXT)
        self._card_bpm   = StatCard("BPM",       "—",   ACCENT,   on_edit=self._edit_bpm)
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

        # Presets guardados (firma y estilo como archivos con nombre) — solo Plus
        from src.ui.presets_bar import PresetBar
        self._preset_bar = PresetBar()
        self._preset_bar.apply_requested.connect(self._on_preset_apply)
        self._preset_bar.save_requested.connect(self._on_preset_save)
        self._preset_bar.delete_requested.connect(self._on_preset_delete)
        p_lay.addWidget(self._preset_bar)

        # Botón "Nuevo Track" — accesible desde la barra de presets
        self._btn_new_track_top = QPushButton("← Nuevo track")
        self._btn_new_track_top.setFixedHeight(24)
        self._btn_new_track_top.setCursor(Qt.PointingHandCursor)
        self._btn_new_track_top.setToolTip("Cargar otro archivo de audio")
        self._btn_new_track_top.setStyleSheet(f"""
            QPushButton {{
                background: {BG4};
                color: {TEXT_MID};
                border: 1px solid {BORDER};
                border-radius: 5px;
                font-size: 10px;
                font-weight: 700;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                border-color: {ACCENT};
                color: {TEXT};
                background: {BG3};
            }}
        """)
        self._btn_new_track_top.clicked.connect(self._pick_new_file)
        p_lay.addWidget(self._btn_new_track_top)

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

        # ── 4b. Cómo EMPIEZA y cómo ACABA la previa (Plus): siempre visible, no escondido en una pestaña ──
        root.addWidget(self._build_startend_card())

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

        # Navegación del paso ② al ③
        self._nav2 = QWidget()
        n2 = QHBoxLayout(self._nav2)
        n2.setContentsMargins(0, 4, 0, 0)
        n2.setSpacing(8)
        self._btn_back_drop = QPushButton("← Otro tema")
        self._btn_back_drop.setFixedHeight(36)
        self._btn_back_drop.setCursor(Qt.PointingHandCursor)
        self._btn_back_drop.setStyleSheet(_btn(BG3, TEXT_SUB, BG4, radius=9, fs=12))
        self._btn_back_drop.clicked.connect(lambda _=False: self._pick_new_file())
        self._btn_next = ShimmerButton("Siguiente: Exportar  →")
        self._btn_next.setFixedHeight(40)
        self._btn_next.setCursor(Qt.PointingHandCursor)
        self._btn_next.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff1e38, stop:1 #990014); color: white;"
            " border: 1px solid #ff4d63; border-radius: 10px; font-size: 13px; font-weight: 800; padding: 0 26px; }"
            "QPushButton:hover { border: 1px solid #ff7588; }")
        self._btn_next.clicked.connect(lambda _=False: self.go_step(3))
        n2.addWidget(self._btn_back_drop)
        n2.addStretch()
        n2.addWidget(self._btn_next)
        root.addWidget(self._nav2)
        root.addStretch(1)

        root = root3

        # Navegación del paso ③ al ②
        self._nav3 = QWidget()
        n3 = QHBoxLayout(self._nav3)
        n3.setContentsMargins(0, 0, 0, 0)
        self._btn_back = QPushButton("←  Volver a la previa")
        self._btn_back.setFixedHeight(32)
        self._btn_back.setCursor(Qt.PointingHandCursor)
        self._btn_back.setStyleSheet(_btn(BG3, TEXT_SUB, BG4, radius=8, fs=11.5))
        self._btn_back.clicked.connect(lambda _=False: self.go_step(2))
        n3.addWidget(self._btn_back)
        n3.addStretch()
        root.addWidget(self._nav3)

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

        self._lbl_step1 = QLabel("① Nombre y formatos")
        self._lbl_step1.setStyleSheet("color:#8c93a4; font-size:9.5px; font-weight:800; letter-spacing:0.8px; background:transparent; border:none;")
        exp_lay.addWidget(self._lbl_step1)

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
        self._chk_video = QCheckBox("🎬 Vídeo animado (TikTok/Reels/YouTube)")
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

        # Modo DJ: solo Vinilo (Keylock eliminado por decisión de producto)
        # Modo siempre Vinilo (+Pitch Armónico) — keylock eliminado, un único modo posible.
        # No se usa QComboBox para evitar que macOS muestre una ventana flotante al inicializar
        # el widget nativo NSPopUpButton antes de que la ventana principal sea visible.
        self._speed_mode = "vinyl"

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

        # Flanger y Filter Sweep ya no son casillas automáticas: se arrastran a la onda (Basic y Plus).
        # Las casillas se conservan ocultas y siempre apagadas por compatibilidad con presets antiguos.
        self._chk_fx_flanger.setVisible(False)
        self._chk_fx_filter.setVisible(False)
        self._lbl_fx_hint = QLabel("🎛 Flanger y Filter Sweep: arrástralos sobre la onda")
        self._lbl_fx_hint.setStyleSheet(f"color: {TEXT_MID}; font-size: 10px; font-weight: 600; background: transparent; border: none;")
        self._lbl_fx_hint.setToolTip("Bajo la forma de onda están las tarjetas de efecto: arrástralas hasta donde quieras que suenen")
        row_fx.addWidget(lbl_fx)
        row_fx.addWidget(self._lbl_fx_hint)
        row_fx.addWidget(self._chk_fx_master)
        row_fx.addSpacing(4)
        row_fx.addWidget(self._btn_voice_drop)
        row_fx.addWidget(self._combo_voice_pos)
        row_fx.addWidget(self._lbl_voice_drop)

        # Modo promo antifugas (Plus): repite la firma y exporta MP3 128 kbps
        self._row_promo_widget = QWidget()
        row_promo = QHBoxLayout(self._row_promo_widget)
        row_promo.setContentsMargins(0, 0, 0, 0)
        row_promo.setSpacing(6)
        self._chk_promo = QCheckBox("🛡️ Modo promo")
        self._chk_promo.setStyleSheet(chk_style)
        self._chk_promo.setToolTip(
            "Modo promo antifugas: repite tu firma de voz cada pocos segundos sobre toda la previa y exporta "
            "solo en MP3 128 kbps, para que el audio no se pueda reutilizar sin tu firma")
        self._spin_promo = QSpinBox()
        self._spin_promo.setRange(10, 60)
        self._spin_promo.setValue(20)
        self._spin_promo.setSuffix(" s")
        self._spin_promo.setFixedSize(64, 22)
        self._spin_promo.setStyleSheet(_input_style())
        self._spin_promo.setToolTip("Cada cuántos segundos se repite la firma")
        self._spin_promo.setEnabled(False)
        self._lbl_promo = QLabel("")
        self._lbl_promo.setStyleSheet("font-size: 10px; font-weight: 600; background: transparent; border: none;")
        row_promo.addWidget(self._chk_promo)
        row_promo.addWidget(self._spin_promo)
        row_promo.addWidget(self._lbl_promo)
        row_fx.addSpacing(10)
        row_fx.addWidget(self._row_promo_widget)

        row_fx.addStretch()
        row_fx.setContentsMargins(0, 0, 0, 0)
        self._adv_fx_widget = QWidget()
        self._adv_fx_widget.setStyleSheet("background: transparent;")
        self._adv_fx_widget.setLayout(row_fx)

        self._chk_promo.toggled.connect(self._on_promo_toggled)
        self._spin_promo.valueChanged.connect(lambda _v: self._update_promo_hint())

        # ── Tarjeta «Vídeo animado» (formato, look, color, título, final y vista previa en un solo sitio) ──
        self._row_video_title_widget = _VideoCard()
        self._row_video_widget = self._row_video_title_widget          # alias (compatibilidad)
        vlay = QVBoxLayout(self._row_video_title_widget)
        vlay.setContentsMargins(10, 6, 10, 6)
        vlay.setSpacing(5)
        _lblv = ("color: #8c93a4; font-size: 9.5px; font-weight: 800; letter-spacing: 1px;"
                 "background: transparent; border: none;")

        # fila 1: título de la tarjeta + formato (3 botones) + color
        r1 = QHBoxLayout(); r1.setSpacing(6)
        lbl_vopt = QLabel("🎬 AJUSTES DEL VÍDEO")
        lbl_vopt.setStyleSheet(_lblv)
        r1.addWidget(lbl_vopt)
        r1.addSpacing(8)
        self._combo_aspect = QComboBox(self)           # modelo del formato (los botones lo controlan)
        self._combo_aspect.addItem("📱 9:16 (TikTok/Reels/Shorts)", "9:16")
        self._combo_aspect.addItem("⏹️ 1:1 (Post Cuadrado)", "1:1")
        self._combo_aspect.addItem("🖥️ 16:9 (YouTube / Horizontal)", "16:9")
        self._combo_aspect.setVisible(False)
        self._aspect_btns = {}
        _fmt_style = (f"QPushButton {{ background:{BG3}; color:{TEXT_MID}; border:1px solid {BORDER}; border-radius:5px; padding:0 9px; font-size:10.5px; font-weight:700; }}"
                      "QPushButton:hover { border-color:#a855f7; }"
                      f"QPushButton:checked {{ background:{ACCENT}; color:#ffffff; border-color:{ACCENT}; }}")
        self._aspect_group = QButtonGroup(self)
        self._aspect_group.setExclusive(False)         # se pueden marcar los 3 formatos a la vez (un vídeo por formato)
        for asp, txt, tip in (("9:16", "📱 9:16 Vertical", "Vertical: TikTok, Instagram Reels y YouTube Shorts"),
                              ("1:1", "⏹ 1:1 Cuadrado", "Cuadrado: publicaciones de Instagram y Facebook"),
                              ("16:9", "🖥 16:9 Horizontal", "Horizontal: YouTube y pantallas")):
            b_ = QPushButton(txt)
            b_.setCheckable(True)
            b_.setFixedHeight(24)
            b_.setCursor(Qt.PointingHandCursor)
            b_.setStyleSheet(_fmt_style)
            b_.setToolTip(tip)
            self._aspect_group.addButton(b_)
            self._aspect_btns[asp] = b_
            b_.clicked.connect(lambda _c=False, a=asp: self._on_aspect_clicked(a))
            r1.addWidget(b_)
        self._aspect_btns["9:16"].setChecked(True)
        self._combo_aspect.currentIndexChanged.connect(self._sync_aspect_buttons)
        self._combo_video_pal = QComboBox()
        self._combo_video_pal.setFixedHeight(24)
        self._combo_video_pal.setStyleSheet(_input_style())
        self._combo_video_pal.addItem("⚡ Cian & Magenta Radical", "radical")
        self._combo_video_pal.addItem("🟢 Verde Neón Rave", "rave")
        self._combo_video_pal.addItem("🔥 Rojo Carmesí Studio", "crimson")
        self._combo_video_pal.addItem("🟡 Ámbar Gold & Solar", "amber")
        self._combo_video_pal.addItem("🟣 Cyber Violet", "cyber")
        self._combo_video_pal.setToolTip("Paleta de color neón del vídeo animado Radical Neón (carátula, barras, destellos)")
        r1.addSpacing(6)
        r1.addWidget(self._combo_video_pal, stretch=1)
        vlay.addLayout(r1)

        # fila 2 (Plus): look de un clic + personalizar + banner
        self._row_look_widget = QWidget()
        self._row_look_widget.setStyleSheet("background: transparent;")
        r2 = QHBoxLayout(self._row_look_widget); r2.setContentsMargins(0, 0, 0, 0); r2.setSpacing(6)
        lbl_look = QLabel("Look")
        lbl_look.setFixedWidth(52); lbl_look.setStyleSheet(_lblv)
        self._combo_look = QComboBox()
        self._combo_look.setFixedHeight(24)
        self._combo_look.setStyleSheet(_input_style())
        self._combo_look.setToolTip("Elige un aspecto listo con un clic. Con «Foto…» se usa tu imagen de fondo (o arrástrala sobre esta tarjeta). «Personalizar…» abre todos los ajustes.")
        for key, txt in (("neon", "🎬 Neón clásico (carátula que late)"), ("bars", "🖼 Foto + barras abajo"),
                         ("circle", "🖼 Foto + círculo en el centro"), ("title", "🖼 Foto y título (sin onda)"),
                         ("photo", "🖼 Solo la foto")):
            self._combo_look.addItem(txt, key)
        self._video_custom = normalize_custom(None)
        self._btn_vcustom = QPushButton("⚙ Personalizar…")
        self._btn_vcustom.setFixedHeight(24)
        self._btn_vcustom.setCursor(Qt.PointingHandCursor)
        self._btn_vcustom.setStyleSheet(_btn("#1f2937", "#e5e7eb", "#374151", radius=5, fs=10.5))
        self._btn_vcustom.setToolTip("Plus: tu imagen de fondo (una por formato), la onda de sonido (barras, línea o círculo), los textos, su posición y un final con tu imagen, con vista previa en vivo.")
        self._btn_vcustom.clicked.connect(self._open_video_custom)
        self._edit_promo = QLineEdit()
        self._edit_promo.setPlaceholderText("Banner: RADICAL RECORDS · PROMO EXCLUSIVA")
        self._edit_promo.setFixedHeight(24)
        self._edit_promo.setStyleSheet(_input_style())
        self._edit_promo.setToolTip("Texto del banner promocional visible en el vídeo")
        r2.addWidget(lbl_look)
        r2.addWidget(self._combo_look, stretch=1)
        r2.addWidget(self._btn_vcustom)
        r2.addWidget(self._edit_promo, stretch=1)
        vlay.addWidget(self._row_look_widget)
        self._combo_look.activated.connect(self._on_look_chosen)

        # fila 3: título + final + vista previa
        r3 = QHBoxLayout(); r3.setSpacing(6)
        lbl_vt = QLabel("Título")
        lbl_vt.setFixedWidth(52); lbl_vt.setStyleSheet(_lblv)
        self._edit_vtitle = QLineEdit()
        self._edit_vtitle.setPlaceholderText("Título que sale en el vídeo (vacío = nombre de la pista)")
        self._edit_vtitle.setFixedHeight(24)
        self._edit_vtitle.setStyleSheet(_input_style())
        self._edit_vtitle.setToolTip("Nombre que aparece en el centro del vídeo. Si lo dejas vacío se usa el nombre de la pista (sin «PREVIA - »).")
        self._combo_vend = QComboBox()
        self._combo_vend.setFixedHeight(24)
        self._combo_vend.setStyleSheet(_input_style())
        self._combo_vend.addItem("✨ Final: firma AutoPrevias + enlace", "brand")
        self._combo_vend.addItem("🌑 Final: fundido a negro", "fade")
        self._combo_vend.addItem("✂ Final: sin cierre (corte seco)", "none")
        self._combo_vend.addItem("🖼 Final: mi imagen", "image")
        self._combo_vend.setToolTip("Cómo termina el vídeo: con el cierre «Generado por AutoPrevias · Radical Records» y el enlace, con un fundido a negro, con tu propia imagen o sin cierre (Plus). En Basic puedes elegir entre la firma o el fundido a negro.")
        self._combo_vend.currentIndexChanged.connect(self._on_vend_changed)
        self._btn_vprev = QPushButton("👁 Vista previa")
        self._btn_vprev.setFixedHeight(24)
        self._btn_vprev.setCursor(Qt.PointingHandCursor)
        self._btn_vprev.setStyleSheet(_btn(ACCENT, "#ffffff", "#ff4d63", radius=5, fs=10.5))
        self._btn_vprev.setToolTip("Mira unos segundos del vídeo (a baja resolución y con sonido) antes de generarlo, con tu título, paleta, formato y banner.")
        self._btn_vprev.clicked.connect(self._open_video_preview)
        r3.addWidget(lbl_vt)
        r3.addWidget(self._edit_vtitle, stretch=1)
        r3.addWidget(self._combo_vend)
        r3.addWidget(self._btn_vprev)
        vlay.addLayout(r3)

        # fila 4: ayuda (Plus: arrastrar imagen) o candado (Basic)
        self._lbl_vdrop = QLabel("💡 Arrastra una imagen sobre esta tarjeta para usarla de fondo del vídeo")
        self._lbl_vdrop.setStyleSheet("color:#9a8fc4; font-size:10px; background: transparent; border: none;")
        self._lbl_vbasic = QLabel("Marca de agua incluida · se quita con Plus")
        self._lbl_vbasic.setStyleSheet("color:#c084fc; font-size:10px; font-weight:600; background: transparent; border: none;")
        self._lbl_vbasic.setToolTip("En la edición Basic el vídeo lleva una marca de agua pequeña («Generado por Radical Records · AutoPrevias Basic») y termina con la firma de AutoPrevias o con un fundido a negro, como prefieras. La edición Plus no lleva marca de agua y te deja elegirlo todo: fondo, onda de sonido, textos y final.")
        self._btn_vlock = QPushButton("🔒 Tu imagen de fondo, onda de sonido y final a medida: solo en Plus")
        self._btn_vlock.setFixedHeight(22)
        self._btn_vlock.setCursor(Qt.PointingHandCursor)
        self._btn_vlock.setStyleSheet("QPushButton { background: transparent; color:#c084fc; border: 1px dashed #6d28d9; border-radius:5px; padding:0 8px; font-size:10px; font-weight:600; }"
                                      "QPushButton:hover { background:#2a1a4a; }")
        self._btn_vlock.setToolTip("La edición Plus añade vídeo sin marca de agua, con tu propia imagen, onda de sonido a elegir y final a medida. Pulsa para ver cómo conseguirla.")
        self._btn_vlock.clicked.connect(self._open_plus_page)
        r4 = QHBoxLayout(); r4.setSpacing(8)
        r4.addWidget(self._lbl_vdrop, stretch=1)
        r4.addWidget(self._lbl_vbasic)
        r4.addWidget(self._btn_vlock)
        vlay.addLayout(r4)

        self._row_video_title_widget.setVisible(False)
        exp_lay.addWidget(self._row_video_title_widget)
        self._row_video_title_widget.imageDropped.connect(self._on_video_image_dropped)

        # ③ Opciones avanzadas (efectos, voz, modo promo y firma): plegadas por defecto
        self._adv_open = False
        self._btn_adv = QPushButton()
        self._btn_adv.setCursor(Qt.PointingHandCursor)
        self._btn_adv.setFixedHeight(24)
        self._btn_adv.setStyleSheet(f"QPushButton {{ background: transparent; color:{TEXT_MID}; border:none; text-align:left; font-size:10.5px; font-weight:700; padding:0 2px; }}"
                                    f"QPushButton:hover {{ color:{TEXT}; }}")
        self._btn_adv.setToolTip("Efectos de estudio, Voice Drop, Modo promo antifugas y firma/carátula personalizadas")
        self._btn_adv.clicked.connect(lambda: self._set_adv_open(not self._adv_open))
        exp_lay.addWidget(self._btn_adv)
        exp_lay.addWidget(self._adv_fx_widget)
        for _chk in (self._chk_fx_flanger, self._chk_fx_filter, self._chk_promo):
            _chk.toggled.connect(lambda on: on and self._set_adv_open(True))
        self._chk_video.toggled.connect(lambda on: _anim.reveal(self._row_video_title_widget, bool(on)))
        self._chk_video.toggled.connect(lambda _on: self._sync_video_mp3())
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
        self._btn_folder.setFixedSize(84, 24)
        self._btn_folder.setStyleSheet(_btn(BG4, TEXT_MID, BG5, radius=5, fs=10.5))
        self._btn_folder.setCursor(Qt.PointingHandCursor)
        self._btn_folder.setToolTip("Cambiar la carpeta de destino donde se guardan las previas")
        self._btn_folder.clicked.connect(self.folder_requested.emit)

        self._btn_open_folder = QPushButton("📂 Abrir")
        self._btn_open_folder.setFixedSize(84, 24)
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

        # ── 5.2 RESUMEN de lo que se va a crear ───────────────────────────
        self._lbl_summary = QLabel("")
        self._lbl_summary.setWordWrap(True)
        self._lbl_summary.setStyleSheet(f"color:{TEXT_MID}; font-size:10.5px; padding:4px 8px; background:{BG2}; border:1px solid {BORDER}; border-radius:7px;")
        self._lbl_summary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._lbl_summary.setMaximumHeight(46)
        root.addWidget(self._lbl_summary)
        self._summary_timer = QTimer(self)
        self._summary_timer.setInterval(500)
        self._summary_timer.timeout.connect(self._update_summary)
        self._summary_timer.start()

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
        root.addStretch(1)                               # el hueco sobrante va abajo, no repartido entre las tarjetas

    # ── Helpers de UI ─────────────────────────────────────────────────────

    def _on_toggle_advanced(self, checked: bool):
        _anim.reveal(self._detail_body, checked, ms=260)
        self._lbl_detail_arrow.setText("▴" if checked else "▾")
        plus = get_edition() == "plus"
        if checked:
            i18n.set_text(self._chk_advanced, "⚙️  Ocultar Personalización" if plus else "✂️  Ocultar cortes")
            i18n.set_text(self._lbl_simple_desc,
                          "Ajustes manuales activos: edita la tabla de cortes, curva de tempo o estructura." if plus else
                          "Ordena los cortes con ▲ ▼, elige dónde empieza la previa o arrástralos en la onda.")
        else:
            i18n.set_text(self._chk_advanced, "⚙️  Personalizar Cortes & BPM" if plus else "✂️  Ordenar y mover cortes")
            i18n.set_text(self._lbl_simple_desc, "3 cortes listos · Arrastra en la onda para retocar o pulsa abajo en Generar Previa")

    def _apply_generate_style(self, ready: bool):
        _anim.pulse_glow(self._btn_generate, bool(ready) and self._btn_generate.isEnabled())
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
        i18n.set_text(self._btn_regen, "⟳  Regenerar con esta seed")
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
        self.hist_reset()
        if getattr(self, "_fx_aud", None) is not None:
            self._fx_aud.release()
        if hasattr(self, "_banner_ready"):
            self._banner_ready.setVisible(False)
        self.set_studio(bool(load_cfg().get("always_studio")))
        self.go_step(2, animate=False)
        self._session_cover = cfg.get("cover_path", "") if isinstance(cfg, dict) else ""
        if hasattr(self, "_edit_vtitle"):
            self._edit_vtitle.clear()        # el título del vídeo es por pista
        self._bpm         = bpm
        self._key_res     = key_res
        name = Path(file_path).stem
        max_n = 16
        self._card_file.set_value(name[:max_n] + ("…" if len(name) > max_n else ""))
        self._card_bpm.set_value(f"{bpm:.1f}", animate=True)
        if key_res:
            self._key_str = f"{key_res.camelot} · {key_res.notation}"
            self._card_key.set_value(f"{key_res.camelot}  {key_res.notation}")
        else:
            self._key_str = ""
            self._card_key.set_value("—")
        self._card_dur.set_value(fmt_time_short(dur))
        self._card_drops.set_value(str(len(analysis.drops())), animate=True)

        est = plan.estimated_duration_after_stretch
        ok  = 15 <= est <= 180
        self._card_pv.set_value(fmt_time_short(est))
        self._card_pv.set_accent(GREEN if ok else WARN)

        self._out_path = str(get_output_dir(file_path, cfg))
        self._lbl_folder_path.setText(short_path(self._out_path))
        from src.config import get_edition as _get_ed
        if _get_ed() == "plus":
            self._chk_wav.setChecked(cfg.get("export_wav", True))
        self._chk_mp3.setChecked(cfg.get("export_mp3", True))
        if hasattr(self, "_branding_card"):
            self._branding_card.load_from_cfg(cfg)

        # Restaurar preferencias guardadas (speed_mode, palette, aspect_ratio, fx)
        persisted_cfg = load_cfg()
        if persisted_cfg.get("speed_mode"):
            self._speed_mode = persisted_cfg["speed_mode"]
        if hasattr(self, "_combo_video_pal") and persisted_cfg.get("video_palette"):
            for i in range(self._combo_video_pal.count()):
                if self._combo_video_pal.itemData(i) == persisted_cfg["video_palette"]:
                    self._combo_video_pal.setCurrentIndex(i)
                    break
        if hasattr(self, "_video_custom") and persisted_cfg.get("video_custom"):
            self._video_custom = normalize_custom(persisted_cfg["video_custom"])
        if hasattr(self, "_combo_look"):
            self._sync_look_combo()
        if persisted_cfg.get("adv_panel_open") or persisted_cfg.get("save_signature_default") \
                or persisted_cfg.get("fx_flanger") or persisted_cfg.get("fx_filter_sweep"):
            self._adv_open = True
        self._apply_adv_visibility()
        if hasattr(self, "_combo_vend") and persisted_cfg.get("video_end"):
            self._set_combo_by_data(self._combo_vend, persisted_cfg["video_end"])
        if hasattr(self, "_combo_aspect") and persisted_cfg.get("aspect_ratio"):
            for i in range(self._combo_aspect.count()):
                if self._combo_aspect.itemData(i) == persisted_cfg["aspect_ratio"]:
                    self._combo_aspect.setCurrentIndex(i)
                    break
            if persisted_cfg.get("aspect_ratios"):
                self._set_aspects(persisted_cfg["aspect_ratios"], persisted_cfg.get("aspect_ratio"))
        # Restaurar estado de FX (los tres checkboxes se persisten entre sesiones)
        if "studio_mastering" in persisted_cfg:
            self._chk_fx_master.setChecked(persisted_cfg["studio_mastering"])

        default_name = preview_filename(file_path)
        self._edit_name.setText(default_name)
        self._last_default_name = default_name

        self._fill_structure(analysis)
        self._fill_plan(plan)
        self._animate_stat_cards()
        _anim.stagger_fade_in([self._btn_p15, self._btn_p30, self._btn_p60, self._btn_p120], step_ms=60, ms=240)

        # Waveform
        if HAS_WAVEFORM:
            self._waveform.load_track(file_path)
            self._waveform.set_sections(analysis.sections, plan.segments)

        # Reproductor: cargar el track original inmediatamente
        if self._player:
            self._player.set_source_track(file_path)

        self._active_preset_sec = 120
        self._update_preset_styles(120)
        i18n.set_text(self._lbl_simple_desc, "Preset 120s (2 Min · Defecto) aplicado ({n} cortes calculados)",
                      n=len(plan.segments))

        self._btn_generate.setEnabled(True)
        self._apply_generate_style(True)
        self._btn_generate.start_shimmer()
        self._update_tempo_plot()

    def _animate_stat_cards(self):
        cards = [self._card_file, self._card_bpm, self._card_key,
                 self._card_dur, self._card_drops, self._card_pv]
        self._card_anims = []
        for i, card in enumerate(cards):
            eff = QGraphicsOpacityEffect(card)
            eff.setOpacity(0.0)
            card.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", self)
            anim.setDuration(300)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.finished.connect(lambda c=card: c.setGraphicsEffect(None))
            self._card_anims.append(anim)
            QTimer.singleShot(i * 70, anim.start)

    def _update_preset_styles(self, active_sec: int):
        if not hasattr(self, "_preset_buttons"):
            return
        for btn, sec in self._preset_buttons:
            if hasattr(btn, "lbl_title"):                      # v5: tarjeta-selector
                btn.setChecked(sec == active_sec)
                continue
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

    # ── v5: asistente de 3 pasos, destinos y modo Estudio ─────────────────

    def go_step(self, n: int, animate: bool = True):
        """Muestra el paso ② (Tu previa) o ③ (Exportar). En modo Estudio se ve todo y no hace nada."""
        n = 3 if n == 3 else 2
        self._wizard_step = n
        self._stepper.set_step(n)
        if self._studio:
            return

        def _switch():
            self._page2.setVisible(n == 2)
            self._page3.setVisible(n == 3)
        if animate and self.isVisible():
            _anim.snapshot_transition(self, _switch, direction=(1 if n == 3 else -1), ms=320)   # fotos: estable a 60 fps
        else:
            _switch()

    # ── ▶ Oír efecto ───────────────────────────────────────────────────────
    def _fx_auditioner(self):
        aud = getattr(self, "_fx_aud", None)
        if aud is None:
            from src.ui.fx_audition import FxAuditioner
            aud = FxAuditioner(self)
            aud.state_changed.connect(lambda on: self._waveform.set_fx_playing(on) if HAS_WAVEFORM else None)
            self._fx_aud = aud
        return aud

    def _audition_fx(self, ev: dict):
        """▶ Oír: suena SOLO este efecto sobre el tema original (2 s antes y 2 s después). Pulsar otra vez lo para."""
        aud = self._fx_auditioner()
        if aud.is_playing():
            aud.stop()
            return
        if not self._source_path:
            return
        if self._player is not None and getattr(self._player, "is_playing", lambda: False)():
            self._player.toggle_play()                     # el reproductor principal se pausa mientras suena el efecto
        try:
            ok = aud.play_event(self._source_path, ev)
        except Exception as ex:
            self.status_message.emit(tr("⚠ No se pudo preparar el efecto: {err}", err=str(ex)))
            return
        if not ok:
            self.status_message.emit("⚠ No se pudo reproducir el efecto en este equipo")

    # ── v5: deshacer / rehacer ─────────────────────────────────────────────
    def _snapshot(self):
        rows = tuple((round(a, 3), round(b, 3), int(c)) for a, b, c in self._cut_rows()) if hasattr(self, "_tbl_cuts") else ()
        ev = ()
        if HAS_WAVEFORM:
            ev = tuple(sorted((str(e.get("id")), e.get("type"), round(float(e.get("start", 0)), 3),
                               round(float(e.get("end", 0)), 3), round(float(e.get("amount", 0)), 3))
                              for e in self._waveform.fx_events()))
        return (rows, ev)

    def _hist_poll(self, force: bool = False):
        if self._hist_restoring or not self._analysis or not self.isVisible():
            return
        snap = self._snapshot()
        if not self._hist_ready:
            self._hist.reset(snap)
            self._hist_ready = True
            self._hist_pending = None
            return
        if snap == self._hist.current():
            self._hist_pending = None
            return
        if force or snap == self._hist_pending:
            self._hist.record(snap)
            self._hist_pending = None
        else:
            self._hist_pending = snap

    def hist_reset(self):
        self._hist_ready = False
        self._hist_pending = None

    def _hist_restore(self, snap):
        rows, ev = snap
        self._hist_restoring = True
        try:
            if tuple(rows) != self._snapshot()[0]:
                self._apply_cut_rows([(a, b, c) for a, b, c in rows])
            if HAS_WAVEFORM and tuple(ev) != self._snapshot()[1]:
                self._waveform.set_fx_events([{"id": i, "type": t, "start": a, "end": b, "amount": m} for i, t, a, b, m in ev],
                                             emit=True)
            self._hist.replace_current(self._snapshot())
        finally:
            self._hist_restoring = False

    def undo(self):
        self._hist_poll(force=True)
        snap = self._hist.undo()
        if snap is None:
            self.status_message.emit("Nada que deshacer")
            return False
        self._hist_restore(snap)
        self.status_message.emit("↶ Deshecho")
        return True

    def redo(self):
        self._hist_poll(force=True)
        snap = self._hist.redo()
        if snap is None:
            self.status_message.emit("Nada que rehacer")
            return False
        self._hist_restore(snap)
        self.status_message.emit("↷ Rehecho")
        return True

    def _on_stepper_clicked(self, n: int):
        if n == 1:
            self._pick_new_file()
        else:
            self.go_step(n)

    def set_studio(self, on: bool):
        """Modo Estudio (expertos): una sola vista con la onda, los carriles, las herramientas y la exportación, sin asistente."""
        on = bool(on)
        self._studio = on

        def _chrome():
            self._stepper.setVisible(not on)
            self._nav2.setVisible(not on)
            self._nav3.setVisible(not on)
        if on == self._studio_entered:
            _chrome()
            if not on:
                self.go_step(self._wizard_step, animate=False)
            return
        if self.isVisible():
            _anim.snapshot_transition(self, lambda: (_chrome(), self._apply_studio(on)), direction=(1 if on else -1), ms=340, slide=0)
        else:
            _chrome()
            self._apply_studio(on)

    def _apply_studio(self, on: bool):
        if on:
            from src.ui.studio import StudioView
            if self._studio_view is None:
                self._studio_view = StudioView(self)
                self._shell.addWidget(self._studio_view, 1)
            self._page2.setVisible(False)
            self._page3.setVisible(False)
            self._studio_view.enter()
            self._studio_view.setVisible(True)
            if get_edition() == "plus":
                self._adv_fx_widget.setVisible(True)
            self._studio_entered = True
        else:
            self._studio_view.leave()
            self._studio_view.setVisible(False)
            self._studio_entered = False
            self._apply_adv_visibility()
            self.go_step(self._wizard_step, animate=False)

    def _apply_destination(self, key: str):
        """Un clic en «¿Para qué es?»: duración, formatos, vídeo y arranque/final del destino elegido."""
        from src.ui.wizard import destination_settings
        plus = get_edition() == "plus"
        s = destination_settings(key, plus)
        self._dest_key = key
        if s["seconds"]:
            self._apply_duration_preset(s["seconds"])
        if key != "custom":
            if plus and bool(s.get("promo")) != self._chk_promo.isChecked():
                self._chk_promo.setChecked(bool(s.get("promo")))          # el destino fija el modo promo (y libera los formatos)
                if s.get("promo") and not self._voice_drop_path:
                    self.status_message.emit("Modo promo activado: elige tu firma de voz en «Opciones avanzadas» (Voice Drop)")
                    self._set_adv_open(True)
            if not self._chk_promo.isChecked():
                if plus:
                    self._chk_wav.setChecked(s["wav"])
                    self._chk_flac.setChecked(s["flac"])
                self._chk_mp3.setChecked(s["mp3"])
            self._chk_video.setChecked(bool(s["video"]))
            if s["video"]:
                self._set_aspects([s["aspect"]])
            if plus and s["start_mode"]:
                self._set_start_mode(s["start_mode"])
                self._set_end_mode(s["end_mode"])
        if s["open_detail"]:
            self._chk_advanced.setChecked(True)
        self.status_message.emit("Destino aplicado: puedes cambiar lo que quieras en los pasos ② y ③")

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
            i18n.set_text(self._lbl_simple_desc, "Preset 120s (2 Min · Defecto) aplicado ({n} cortes calculados)",
                          n=len(new_plan.segments))
        else:
            i18n.set_text(self._lbl_simple_desc, "Preset {s}s aplicado ({n} cortes calculados)",
                          s=seconds, n=len(new_plan.segments))

    def _pick_new_file(self):
        """Abre selector de archivo y emite load_file_requested sin salir de la app."""
        file, _ = QFileDialog.getOpenFileName(
            self,
            tr("Seleccionar track para nueva previa"),
            "",
            tr("Audio (*.mp3 *.wav *.flac *.aiff *.m4a *.ogg *.opus *.wma)"),
        )
        if file:
            self.load_file_requested.emit(file)

    def _select_voice_drop(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            tr("Seleccionar firma de voz / Voice Drop / Jingle"),
            "",
            tr("Archivos de Audio (*.wav *.mp3 *.aiff *.flac *.m4a)"),
        )
        if file:
            self._set_voice_drop_path(file)

    def _set_voice_drop_path(self, file: str):
        self._voice_drop_path = file
        if file:
            self._set_adv_open(True)
        # Leer duración del archivo para mostrar región en la waveform
        dur = 0.0
        try:
            import soundfile as _sf
            dur = float(_sf.info(file).duration)
        except Exception:
            try:
                import librosa as _lr
                dur = float(_lr.get_duration(path=file))
            except Exception:
                pass
        self._voice_drop_dur_sec = dur
        p = Path(file)
        dur_str = f" · {dur:.1f}s" if dur > 0 else ""
        self._lbl_voice_drop.setText(f"✓ {p.name[:14]}{dur_str}")
        self._btn_voice_drop.setText(tr("🎙️ Cambiar Drop"))
        self._update_voice_drop_marker()
        self._update_promo_hint()

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
        self._waveform.set_voice_drop_marker(t, dur=self._voice_drop_dur_sec)

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
        speed_mode = getattr(self, "_speed_mode", "vinyl")
        video_pal = self._combo_video_pal.currentData() if hasattr(self, "_combo_video_pal") else "crimson"
        promo_txt = self._edit_promo.text().strip() if hasattr(self, "_edit_promo") else ""
        vtitle = self._edit_vtitle.text().strip() if hasattr(self, "_edit_vtitle") else ""
        aspect = self._combo_aspect.currentData() if hasattr(self, "_combo_aspect") else "9:16"
        voice_pos = self._combo_voice_pos.currentData() if hasattr(self, "_combo_voice_pos") else "predrop"

        return {
            "export_wav": self._chk_wav.isChecked(),
            "export_mp3": self._chk_mp3.isChecked() or self._chk_video.isChecked(),   # sin previa no hay vídeo
            "export_flac": self._chk_flac.isChecked(),
            "export_video": self._chk_video.isChecked(),
            "fx_flanger": False,                         # el efecto automático antes del drop ya no existe
            "fx_filter_sweep": False,
            "fx_events": self._waveform.fx_events() if HAS_WAVEFORM else [],
            "studio_mastering": self._chk_fx_master.isChecked(),
            "speed_mode": speed_mode,
            "video_palette": video_pal,
            "video_promo_text": promo_txt,
            "video_title": vtitle,
            "video_end": self._video_end_for_edition(),
            "video_custom": dict(self._video_custom) if get_edition() == "plus" else None,
            "aspect_ratio": aspect,
            "aspect_ratios": self.selected_aspects(),
            "voice_drop_enabled": bool(self._voice_drop_path),
            "voice_drop_path": self._voice_drop_path,
            "voice_drop_position": voice_pos,
            "voice_drop_time_sec": self._voice_drop_time_sec,
            "key_str": self._key_str,
            # Arranque de la previa (solo Plus elige; en Basic siempre el efecto de vinilo de 1 s)
            "start_mode": self._start_mode if get_edition() == "plus" else "vinyl",
            "start_spin_sec": float(self._spin_start.value()) if get_edition() == "plus" else 1.0,
            "end_mode": self._end_mode if get_edition() == "plus" else "vinyl",
            "end_spin_sec": float(self._spin_end.value()) if get_edition() == "plus" else 1.0,
            **self._promo_options(),
        }

    def refresh_language(self):
        """Repinta lo que se genera por código (leyendas de la gráfica, pista del modo promo)."""
        try:
            self._update_promo_hint()
            if HAS_WAVEFORM and self._plan is not None and self._source_path:
                self._waveform.update_plan_highlights(self._plan.segments)
                self._waveform._update_badges()
                self._update_voice_drop_marker()
        except Exception:
            pass
        i18n.translate_tree(self)

    # ── Modo promo antifugas ──────────────────────────────────────────────────
    def _promo_options(self) -> dict:
        """Opciones del modo promo. Con el modo activo solo se exporta MP3 128 kbps."""
        on = bool(self._chk_promo.isChecked()) and get_edition() == "plus"
        opts = {"promo_mode": on, "promo_interval_sec": int(self._spin_promo.value())}
        if on:
            opts.update({"export_wav": False, "export_flac": False, "export_mp3": True, "mp3_kbps": 128})
        return opts

    def _video_end_for_edition(self) -> str:
        """Final elegido; en Basic solo vale la firma o el fundido a negro."""
        v = self._combo_vend.currentData() if hasattr(self, "_combo_vend") else "brand"
        if get_edition() != "plus" and v not in ("brand", "fade"):
            return "brand"
        return v or "brand"

    def _refresh_vend_items(self, plus: bool):
        """Basic ofrece solo «firma» y «fundido a negro»; Plus añade «sin cierre» y «mi imagen»."""
        cb = self._combo_vend
        cur = cb.currentData()
        cb.blockSignals(True)
        cb.clear()
        cb.addItem(tr("✨ Final: firma AutoPrevias + enlace"), "brand")
        cb.addItem(tr("🌑 Final: fundido a negro"), "fade")
        if plus:
            cb.addItem(tr("✂ Final: sin cierre (corte seco)"), "none")
            cb.addItem(tr("🖼 Final: mi imagen"), "image")
        for i in range(cb.count()):
            if cb.itemData(i) == cur:
                cb.setCurrentIndex(i)
                break
        cb.blockSignals(False)

    def _on_vend_changed(self, *_):
        if self._combo_vend.currentData() == "image" and not self._video_custom.get("end_image"):
            self._open_video_custom()

    def _video_sample(self) -> dict:
        """Datos de la pista actual para la vista previa del diálogo de ajustes."""
        from src.config import load as _lc
        md = self.get_branding_metadata() or {}
        opts = self.get_export_options()
        title = (opts.get("video_title") or md.get("title") or self.get_export_name()).replace("PREVIA - ", "").strip()
        return {
            "cover": self.get_branding_cover_path() or getattr(self, "_session_cover", "") or None,
            "title": title or "Previa", "artist": md.get("artist") or "Radical Records",
            "bpm": float(self._bpm or 128.0), "key": str(getattr(self, "_key_str", "") or "8A · Am"),
            "aspect": opts.get("aspect_ratio", "9:16"), "palette": opts.get("video_palette", "crimson"),
            "banner": opts.get("video_promo_text", ""),
        }

    def _save_video_custom(self):
        from src.config import load as _lc, save as _sc
        try:
            cfg = _lc()
            cfg["video_custom"] = self._video_custom
            _sc(cfg)
        except Exception:
            pass

    def _open_video_custom(self):
        if get_edition() != "plus":
            return
        from src.ui.video_custom import VideoCustomDialog
        dlg = VideoCustomDialog(self._video_custom, self, sample=self._video_sample())
        if dlg.exec():
            self._video_custom = dlg.result_custom()
            self._save_video_custom()
        self._sync_look_combo()
        if self._combo_vend.currentData() == "image" and not self._video_custom.get("end_image"):
            self._set_combo_by_data(self._combo_vend, "brand")      # sin imagen de final, vuelve a la firma

    # — formato, looks, imágenes arrastradas —
    def selected_aspects(self) -> list:
        """Formatos de vídeo marcados (en orden 9:16, 1:1, 16:9); el formato principal (el de la vista previa) va siempre incluido."""
        cur = self._combo_aspect.currentData() or "9:16"
        out = [a for a, b in self._aspect_btns.items() if b.isChecked() or a == cur]
        return out or ["9:16"]

    def _on_aspect_clicked(self, asp: str):
        """Marca/desmarca un formato. Siempre queda al menos uno; el principal pasa a ser el último marcado."""
        b = self._aspect_btns[asp]
        marked = [a for a, x in self._aspect_btns.items() if x.isChecked()]
        if not marked:                                           # no se puede dejar sin ningún formato
            b.setChecked(True)
            marked = [asp]
        if b.isChecked():
            self._set_combo_by_data(self._combo_aspect, asp)
        elif self._combo_aspect.currentData() == asp:
            self._set_combo_by_data(self._combo_aspect, marked[0])
        self._sync_aspect_buttons()
        self._refresh_summary_safe()

    def _set_aspects(self, aspects, primary: str | None = None):
        """Deja marcados exactamente estos formatos (al cargar un destino, un preset o un proyecto)."""
        asps = [a for a in self._aspect_btns if a in (aspects or [])] or ["9:16"]
        prim = primary if primary in asps else asps[0]
        self._combo_aspect.blockSignals(True)
        self._set_combo_by_data(self._combo_aspect, prim)
        self._combo_aspect.blockSignals(False)
        for a, b in self._aspect_btns.items():
            b.setChecked(a in asps)

    def _refresh_summary_safe(self):
        try:
            self._update_summary()
        except Exception:
            pass

    def _sync_aspect_buttons(self, *_):
        """Si cambia el formato principal (preset, imagen arrastrada…), queda marcado sin quitar los demás."""
        cur = self._combo_aspect.currentData()
        if cur in self._aspect_btns:
            self._aspect_btns[cur].setChecked(True)

    def _sync_look_combo(self):
        """Muestra en el selector el look que coincide con los ajustes (o «Personalizado»)."""
        look = detect_look(self._video_custom)
        cb = self._combo_look
        idx = cb.findData("custom")
        if look == "custom" and idx < 0:
            cb.addItem(tr("⚙ Personalizado"), "custom")
        elif look != "custom" and idx >= 0:
            cb.removeItem(idx)
        self._set_combo_by_data(cb, look)

    def _bg_image_from_user(self, path: str = "") -> str:
        """Pide (si no se da) y valida una imagen de fondo: avisa si no tiene el formato del vídeo. '' = cancelado."""
        from src.engine.video_neon import describe_ratio, image_size
        from src.ui.video_custom import ask_format_mismatch
        aspect = ""
        while True:
            if not path:
                path, _ = QFileDialog.getOpenFileName(self, tr("Elegir imagen"), "", tr("Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)"))
                if not path:
                    return ""
            sz = image_size(path)
            if sz is None:
                QMessageBox.warning(self, tr("Elegir imagen"), tr("No se ha podido abrir esa imagen. Prueba con un PNG o JPG."))
                path = ""
                continue
            if match_aspect(*sz) is None:          # un formato válido distinto del actual no avisa: se cambia al de la imagen
                if ask_format_mismatch(self, [("fondo", path, describe_ratio(*sz))], aspect) == "change":
                    path = ""
                    continue
            return path

    def _use_background_image(self, path: str):
        """Usa `path` como fondo: si encaja en un formato, para ese formato (y cambia a él); si no, para todos."""
        from src.engine.video_neon import image_size
        sz = image_size(path)
        m = match_aspect(*sz) if sz else None
        was_neon = self._video_custom.get("style") != "image"
        bg = dict(self._video_custom.get("bg") or {})
        bg[m or "default"] = path
        c = normalize_custom({**self._video_custom, "bg": bg, "style": "image"})
        if was_neon:
            c = apply_look(c, "bars")           # primer uso de una imagen: foto + barras abajo
        self._video_custom = c
        if m:
            self._set_combo_by_data(self._combo_aspect, m)
        self._save_video_custom()
        self._sync_look_combo()

    def _on_look_chosen(self, _idx: int):
        key = self._combo_look.currentData()
        if key == "custom":
            self._open_video_custom()
            return
        if key != "neon" and not self._video_custom.get("bg"):
            path = self._bg_image_from_user()
            if not path:
                self._sync_look_combo()
                return
            self._use_background_image(path)
        self._video_custom = apply_look(self._video_custom, key)
        self._save_video_custom()
        self._sync_look_combo()

    def _on_video_image_dropped(self, path: str):
        if get_edition() != "plus":
            QMessageBox.information(self, tr("Tu imagen de fondo"),
                                    tr("Usar tu propia imagen como fondo del vídeo es una función de la edición Plus."))
            return
        ok = self._bg_image_from_user(path)
        if ok:
            self._chk_video.setChecked(True)
            self._use_background_image(ok)

    def _open_plus_page(self):
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            from src import links as _links
            QDesktopServices.openUrl(QUrl(_links.url_for("plus")))
        except Exception:
            pass

    # — opciones avanzadas plegables —
    def _set_adv_open(self, open_: bool):
        self._adv_open = bool(open_)
        self._apply_adv_visibility()
        try:
            from src.config import load as _lc, save as _sc
            cfg = _lc(); cfg["adv_panel_open"] = self._adv_open; _sc(cfg)
        except Exception:
            pass

    def _adv_active_names(self) -> list:
        names = []
        for chk, nm in ((self._chk_fx_master, "Master LUFS"), (self._chk_promo, "Modo promo")):
            if chk.isChecked():
                names.append(nm)
        if self._voice_drop_path:
            names.append("Voice Drop")
        return names

    def _apply_adv_visibility(self):
        plus = get_edition() == "plus"
        show = plus and self._adv_open
        _anim.reveal(self._adv_fx_widget, show)
        self._btn_adv.setVisible(plus)
        act = self._adv_active_names()
        suffix = ("  ·  " + ", ".join(act)) if act else ""
        arrow = "▾" if self._adv_open else "▸"
        self._btn_adv.setText(f"{arrow} " + tr("Opciones avanzadas: master, voz y firma completa") + suffix)

    # — resumen antes de generar —
    def _update_summary(self):
        if not hasattr(self, "_lbl_summary"):
            return
        plus = get_edition() == "plus"
        parts = []
        if plus and self._chk_wav.isChecked():
            parts.append("WAV 24b")
        if self._chk_mp3.isChecked() or self._chk_video.isChecked():
            parts.append("MP3 128k" if self._chk_promo.isChecked() else "MP3 320k")
        if plus and self._chk_flac.isChecked():
            parts.append("FLAC")
        if self._chk_video.isChecked():
            asp = " + ".join(self.selected_aspects())
            if plus:
                look = detect_look(self._video_custom)
                how = {"neon": tr("plantilla Neón"), "bars": tr("tu imagen + barras"), "circle": tr("tu imagen + círculo"),
                       "title": tr("tu imagen + título"), "photo": tr("solo tu imagen"), "custom": tr("a medida")}[look]
                end = {"brand": tr("firma"), "fade": tr("negro"), "none": tr("sin cierre"), "image": tr("tu imagen")}.get(
                    self._combo_vend.currentData(), tr("firma"))
                parts.append(f"🎬 {tr('vídeo')} {asp} ({how}, {tr('final')}: {end})")
            else:
                end = tr("firma") if self._combo_vend.currentData() == "brand" else tr("negro")
                parts.append(f"🎬 {tr('vídeo')} {asp} ({tr('con marca de agua')}, {tr('final')}: {end})")
        line1 = (" · ".join(parts) if parts else tr("nada: marca algún formato"))
        pv = self._card_pv._val_lbl.text() if hasattr(self._card_pv, "_val_lbl") else ""
        bits = []
        if pv and pv != "—":
            bits.append(tr("⏱ Previa de {t}", t=pv))
        adv = self._adv_active_names()
        if adv:
            bits.append("🎚 " + ", ".join(adv))
        bits.append("📁 " + (self._lbl_folder_path.text() or "—"))
        from html import escape
        txt = (f"<div style='font-size:10px; letter-spacing:1px; color:#6b7285;'>{escape(tr('SE CREARÁ').upper())}</div>"
               f"<div style='font-size:15px; font-weight:800; color:#eceef2;'>{escape(line1)}</div>"
               f"<div style='font-size:11px; color:#8c93a4;'>{escape('  ·  '.join(bits))}</div>")
        if txt != self._lbl_summary.text():
            self._lbl_summary.setText(txt)
        self._refresh_chips()

    def _refresh_chips(self):
        """Títulos y pastillas del paso ② a partir de los valores que ya calcula la app."""
        if not hasattr(self, "_chip_bpm"):
            return
        v = lambda c: c._val_lbl.text()
        self._chip_bpm.setText(f"{v(self._card_bpm)} BPM" if v(self._card_bpm) != "—" else "— BPM")
        self._chip_key.setText(v(self._card_key).replace("  ", " · ") if v(self._card_key) != "—" else "—")
        self._chip_drops.setText(tr("{n} drops", n=v(self._card_drops)) if v(self._card_drops) != "—" else "— drops")
        self._chip_dur.setText(v(self._card_dur))
        self._chip_file.setText(self._source_path and Path(self._source_path).stem or "")
        if self._studio_entered and self._studio_view is not None:
            self._studio_view.refresh()
        pv = v(self._card_pv)
        if pv and pv != "—":
            self._s2_title.setText(tr("Tu previa de {t} está lista para revisar", t=pv))
        if self._source_path:
            self._s2_sub.setText(tr("AutoPrevias ya ha elegido los mejores momentos de «{n}». Escúchala y, si quieres, cámbiala.",
                                    n=Path(self._source_path).stem))
        if hasattr(self, "_lbl_sign_name") and hasattr(self, "_branding_card"):
            md = self._branding_card.get_metadata()
            self._lbl_sign_name.setText(md.get("artist") or md.get("label") or "Radical Records")
            cover = self._branding_card.get_cover_path()
            if cover and Path(cover).exists():
                pm = QPixmap(cover)
                if not pm.isNull():
                    self._lbl_sign_thumb.setText("")
                    self._lbl_sign_thumb.setPixmap(pm.scaled(64, 64, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))

    def _open_signature_editor(self):
        """«Editar» firma y carátula: la tarjeta completa se abre en una ventana y, al cerrarla, vuelve a su sitio."""
        if getattr(self, "_sig_dialog", None) is not None:
            return
        from PySide6.QtWidgets import QDialog
        from src.ui import theme5 as T
        card = self._branding_card
        home = card.parentWidget()
        lay = home.layout() if home is not None else None
        idx = lay.indexOf(card) if lay is not None else -1
        was_visible = card.isVisibleTo(home) if home is not None else False
        dlg = QDialog(self)
        self._sig_dialog = dlg
        dlg.setWindowTitle(tr("Firma y carátula"))
        dlg.setModal(True)
        dlg.setMinimumWidth(560)
        dlg.setStyleSheet(f"QDialog {{ background: {T.BG}; }}")
        v = QVBoxLayout(dlg)
        v.setContentsMargins(20, 18, 20, 16)
        v.setSpacing(12)
        v.addWidget(T.h1(tr("Firma y carátula"), 22))
        v.addWidget(T.sub(tr("Tu artista, sello, género y carátula se incrustan en los archivos y salen en el vídeo.")))
        v.addWidget(card)
        card.setVisible(True)
        row = QHBoxLayout()
        row.addStretch(1)
        btn = QPushButton(tr("Listo"))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(36)
        btn.setMinimumWidth(110)
        btn.setStyleSheet(T.cta_css(10, 13))
        btn.clicked.connect(lambda _=False: dlg.accept())
        row.addWidget(btn)
        v.addLayout(row)
        try:
            dlg.exec()
        finally:
            v.removeWidget(card)
            card.setParent(home)
            if lay is not None:
                lay.insertWidget(idx if idx >= 0 else lay.count(), card)
            card.setVisible(was_visible)
            self._sig_dialog = None
            dlg.deleteLater()
            self._refresh_chips()
            try:
                self._update_summary()
            except Exception:
                pass

    def _open_video_preview(self):
        """Vista previa rápida del vídeo con los ajustes actuales (título, paleta, formato, banner, carátula)."""
        src = getattr(self, "_source_path", "") or ""
        if not src or not Path(src).exists():
            return
        from src.ui.video_preview import VideoPreviewDialog
        from src.config import load as _lc
        md = self.get_branding_metadata() or {}
        opts = self.get_export_options()
        title = (opts.get("video_title") or md.get("title") or self.get_export_name()).replace("PREVIA - ", "").strip()
        start = -1.0
        try:
            drops = self._analysis.drops() if self._analysis else []
            if drops:
                start = max(0.0, float(drops[0].start_time) - 1.0)
        except Exception:
            pass
        en = str(_lc().get("language", "es")) == "en"
        params = dict(
            audio_path=src,
            cover_image_path=self.get_branding_cover_path() or getattr(self, "_session_cover", "") or None,
            title=title or "Previa", artist=md.get("artist") or "Radical Records",
            bpm=float(self._bpm or 128.0), key_str=str(getattr(self, "_key_str", "") or "8A · Am"),
            aspect_ratio=opts.get("aspect_ratio", "9:16"), palette_key=opts.get("video_palette", "crimson"),
            promo_text=opts.get("video_promo_text", ""), kicker="EXCLUSIVE PREVIEW" if en else "PREVIA EXCLUSIVA",
            start_sec=start,
            watermark=(get_edition() != "plus"),
            end_mode=opts.get("video_end", "brand"),
            custom=opts.get("video_custom"),
        )
        dlg = VideoPreviewDialog(params, self)
        dlg.setAttribute(Qt.WA_DeleteOnClose, True)
        self._video_preview_dlg = dlg
        dlg.show()

    def _sync_video_mp3(self):
        """El vídeo se hace a partir de la previa: con «Vídeo animado» marcado el MP3 queda marcado y bloqueado."""
        if self._chk_video.isChecked():
            self._chk_mp3.setChecked(True)
            self._chk_mp3.setEnabled(False)
            self._chk_mp3.setToolTip("El vídeo se genera a partir de la previa, por eso siempre se exporta también el MP3.")
        elif not self._chk_promo.isChecked():
            self._chk_mp3.setEnabled(True)
            self._chk_mp3.setToolTip("")

    def _on_promo_toggled(self, on: bool):
        self._spin_promo.setEnabled(on)
        fmt = (self._chk_wav, self._chk_flac, self._chk_mp3)
        if on:
            self._promo_saved = (self._chk_wav.isChecked(), self._chk_flac.isChecked(), self._chk_mp3.isChecked())
            self._chk_wav.setChecked(False)
            self._chk_flac.setChecked(False)
            self._chk_mp3.setChecked(True)
            self._chk_mp3.setText("MP3 128k")
            for w in fmt:
                w.setEnabled(False)
        else:
            for w in fmt:
                w.setEnabled(True)
            self._chk_mp3.setText("MP3 320k")
            if self._promo_saved:
                self._chk_wav.setChecked(self._promo_saved[0])
                self._chk_flac.setChecked(self._promo_saved[1])
                self._chk_mp3.setChecked(self._promo_saved[2])
            self._promo_saved = None
        self._sync_video_mp3()
        self._update_promo_hint()

    def _update_promo_hint(self):
        if not self._chk_promo.isChecked():
            self._lbl_promo.setText("")
            return
        if not self._voice_drop_path:
            self._lbl_promo.setStyleSheet(f"color: {WARN}; font-size: 10px; font-weight: 600; background: transparent; border: none;")
            i18n.set_text(self._lbl_promo, "⚠ Elige tu firma (Voice Drop)")
        else:
            self._lbl_promo.setStyleSheet(f"color: {GREEN}; font-size: 10px; font-weight: 600; background: transparent; border: none;")
            i18n.set_text(self._lbl_promo, "«{name}» cada ~{sec} s · MP3 128k",
                          name=Path(self._voice_drop_path).stem[:14], sec=self._spin_promo.value())

    # ── Estado guardable (presets e historial) ────────────────────────────────
    def get_state(self, signature: bool = True, style: bool = True, events: bool = False) -> dict:
        """`events=True` (solo al guardar el proyecto de una pista) incluye los efectos colocados en su onda."""
        state: dict = {}
        if style:
            saved = self._promo_saved if (self._chk_promo.isChecked() and self._promo_saved) else None
            wav, flac, mp3 = saved if saved else (self._chk_wav.isChecked(), self._chk_flac.isChecked(),
                                                  self._chk_mp3.isChecked())
            state["style"] = {
                "duration_sec": int(getattr(self, "_active_preset_sec", 120)),
                "export": {"wav": wav, "mp3": mp3, "flac": flac, "video": self._chk_video.isChecked()},
                "fx": {"master": self._chk_fx_master.isChecked()},
                "voice": {"path": self._voice_drop_path, "position": self._combo_voice_pos.currentData(),
                          "time_sec": self._voice_drop_time_sec},
                "promo": {"enabled": self._chk_promo.isChecked(), "interval_sec": int(self._spin_promo.value())},
                "start": {"mode": self._start_mode, "sec": float(self._spin_start.value())},
                "end": {"mode": self._end_mode, "sec": float(self._spin_end.value())},
                "video": {"palette": self._combo_video_pal.currentData(), "aspect": self._combo_aspect.currentData(),
                          "aspects": self.selected_aspects(),
                          "banner": self._edit_promo.text().strip(), "end": self._combo_vend.currentData(),
                          "custom": self._video_custom if get_edition() == "plus" else None},
            }
        if style and events and HAS_WAVEFORM:
            state["style"]["fx_events"] = self._waveform.fx_events()
        if signature and hasattr(self, "_branding_card"):
            md = self._branding_card.get_metadata()
            state["signature"] = {k: md.get(k, "") for k in ("artist", "label", "album", "genre", "comment")}
            state["signature"]["cover_path"] = self._branding_card.get_cover_path()
        return state

    @staticmethod
    def _set_combo_by_data(combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def apply_state(self, state: dict):
        """Aplica firma y/o estilo (solo los grupos presentes). Respeta las limitaciones de la edición."""
        plus = get_edition() == "plus"
        sig = state.get("signature") or {}
        if sig and plus and hasattr(self, "_branding_card"):
            self._branding_card.apply_signature(sig)
        st = state.get("style") or {}
        if not st:
            return
        if self._chk_promo.isChecked():
            self._chk_promo.setChecked(False)           # libera los formatos antes de fijarlos
        ex = st.get("export") or {}
        for key, chk in (("wav", self._chk_wav), ("mp3", self._chk_mp3), ("flac", self._chk_flac),
                         ("video", self._chk_video)):
            if key in ex and not chk.isHidden():
                chk.setChecked(bool(ex[key]))
        if plus:
            fx = st.get("fx") or {}
            if "master" in fx:
                self._chk_fx_master.setChecked(bool(fx["master"]))
        if st.get("fx_events") and HAS_WAVEFORM:
            self._waveform.set_fx_events(st["fx_events"], emit=True)
        sec = st.get("duration_sec")
        if sec in (15, 30, 60, 120):
            self._apply_duration_preset(int(sec))
        start = st.get("start") or {}
        if plus and start:
            self._set_start_mode(start.get("mode", "vinyl"))
            try:
                self._spin_start.setValue(float(start.get("sec", 1.0)))
            except Exception:
                pass
        end = st.get("end") or {}
        if plus and end:
            self._set_end_mode(end.get("mode", "vinyl"))
            try:
                self._spin_end.setValue(float(end.get("sec", 1.0)))
            except Exception:
                pass
        voice = st.get("voice") or {}
        if plus and voice:
            vp = voice.get("path") or ""
            if vp and Path(vp).exists():
                self._set_voice_drop_path(vp)
            elif vp:
                self.status_message.emit(tr("⚠ No se encuentra el audio de firma del preset: {name}", name=Path(vp).name))
            self._set_combo_by_data(self._combo_voice_pos, voice.get("position", "predrop"))
            self._voice_drop_time_sec = float(voice.get("time_sec", -1.0))
            self._update_voice_drop_marker()
        vid = st.get("video") or {}
        if vid:
            self._set_combo_by_data(self._combo_video_pal, vid.get("palette"))
            self._set_aspects(vid.get("aspects") or [vid.get("aspect") or "9:16"], vid.get("aspect"))
            self._edit_promo.setText(vid.get("banner", ""))
            if plus and vid.get("end"):
                self._set_combo_by_data(self._combo_vend, vid.get("end"))
            if plus and vid.get("custom"):
                self._video_custom = normalize_custom(vid.get("custom"))
                self._sync_look_combo()
        promo = st.get("promo") or {}
        if plus and promo:
            self._spin_promo.setValue(int(promo.get("interval_sec", 20)))
            self._chk_promo.setChecked(bool(promo.get("enabled")))

    def restore_project(self, settings: dict, seed: int):
        """«Reabrir proyecto»: mismos ajustes, mismo tempo y misma seed que la previa original."""
        self.apply_state(settings.get("state") or {})
        try:
            mode = settings.get("tempo_mode")
            events = settings.get("tempo_events") or []
            if mode == "manual" and events:
                self._set_tempo_mode("manual")
                self._load_tempo_events(events)
        except Exception:
            pass
        self._spin_seed.setValue(int(seed))

    def _on_preset_apply(self, name: str):
        from src.presets import load_preset
        data = load_preset(name)
        if data is None:
            self.status_message.emit(tr("⚠ No se pudo leer el preset «{name}»", name=name))
            return
        self.apply_state(data)
        parts = []
        if "signature" in data:
            parts.append(tr("firma"))
        if "style" in data:
            parts.append(tr("estilo"))
        self.status_message.emit(tr("✅ Preset «{name}» aplicado ({what})", name=name, what=" + ".join(parts)))

    def _on_preset_save(self, name: str, with_signature: bool, with_style: bool):
        from src.presets import save_preset
        try:
            saved = save_preset(name, self.get_state(signature=with_signature, style=with_style))
        except Exception as exc:
            self.status_message.emit(tr("⚠ No se pudo guardar el preset: {err}", err=str(exc)))
            return
        self._preset_bar.reload(select=saved)
        self.status_message.emit(tr("💾 Preset «{name}» guardado", name=saved))

    def _on_preset_delete(self, name: str):
        from src.presets import delete_preset
        delete_preset(name)
        self._preset_bar.reload()
        self.status_message.emit(tr("🗑️ Preset «{name}» borrado", name=name))

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
        i18n.set_text(self._btn_generate, "▶   GENERAR PREVIA")
        self._apply_generate_style(True)
        self._btn_generate.start_shimmer()

        # Mostrar tarjeta de confirmación con los archivos y la carpeta exacta
        if generated:
            # Excluir temp WAVs internos del nombre de archivo y cálculo de carpeta
            user_files = [p for p in generated if not Path(p).name.startswith("autoprevias_temp_")]
            display_files = user_files if user_files else generated
            out_dir = str(Path(display_files[0]).parent)
            file_names = [Path(p).name for p in display_files]
            has_vid = any(p.lower().endswith(".mp4") for p in generated)

            title_text = "🎉 ¡Previa y Vídeo Social exportados con éxito!" if has_vid else "✅ ¡Previa de audio exportada con éxito!"
            i18n.set_text(self._lbl_succ_title, title_text)
            i18n.set_text(self._lbl_succ_files, "Archivos:  {files}", files="  ·  ".join(file_names))
            i18n.set_text(self._lbl_succ_dir, "📁 Carpeta de guardado:\n{dir}", dir=out_dir)
            self._card_export_success.setVisible(True)
            _anim.fade_in(self._card_export_success, ms=350)

            # Priorizar WAV de usuario (no temp) para el reproductor interno
            prev_file = next((p for p in generated if p.lower().endswith(".wav") and not Path(p).name.startswith("autoprevias_temp_")),
                             next((p for p in generated if p.lower().endswith(".wav")), generated[0]))
            if HAS_WAVEFORM and self._plan:
                self._waveform.load_preview(prev_file, self._plan.segments)
            if self._player:
                self._player.set_preview_track(prev_file, autoplay=True)
            self.play_requested.emit(prev_file)
            self._show_generated_preview(Path(prev_file).name, has_vid)

    def _show_generated_preview(self, name: str, has_video: bool):
        """Al terminar de exportar se lleva al usuario a la onda y al reproductor (paso ②) con la previa ya cargada,
        para que la VEA y la OIGA en AutoPrevias sin tener que buscarla. En modo Estudio ya está todo a la vista."""
        if not hasattr(self, "_banner_ready"):
            return
        extra = tr(" Los vídeos están en la carpeta.") if has_video else ""
        i18n.set_text(self._lbl_ready, "✅ Previa generada: la estás viendo y oyendo aquí («{name}»).{extra}", name=name, extra=extra)
        self._banner_ready.setVisible(True)
        _anim.fade_in(self._banner_ready, ms=350)
        if not self._studio and self._wizard_step == 3:
            self.go_step(2)

    def on_export_start(self):
        if hasattr(self, "_banner_ready"):
            self._banner_ready.setVisible(False)
        if hasattr(self, "_card_export_success"):
            self._card_export_success.setVisible(False)
        self._btn_generate.setEnabled(False)
        i18n.set_text(self._btn_generate, "⏳   Generando previa…")
        self._btn_generate.stop_shimmer()
        self._apply_generate_style(False)

    def get_export_name(self) -> str:
        return self._edit_name.text().strip() or self._last_default_name or "PREVIA"

    def get_export_formats(self) -> tuple:
        return self._chk_wav.isChecked(), self._chk_mp3.isChecked()

    def _edit_bpm(self):
        from PySide6.QtWidgets import QInputDialog
        current_text = self._card_bpm._val_lbl.text()
        try:
            current_val = float(current_text)
        except ValueError:
            current_val = 128.0
        val, ok = QInputDialog.getDouble(
            self, tr("Corregir BPM"), tr("Introduce el BPM real del track:"),
            current_val, 40.0, 250.0, 1
        )
        if ok and abs(val - current_val) > 0.01:
            self._card_bpm.set_value(f"{val:.1f}")
            self._bpm = val
            self.bpm_corrected.emit(val)

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

        # 2b. Dónde empieza la previa (Basic y Plus): al inicio del tema, a mitad, o donde el usuario arrastre el primer corte
        start_bar = QHBoxLayout()
        start_bar.setSpacing(5)
        lbl_st = QLabel("LA PREVIA EMPIEZA:")
        lbl_st.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9.5px; font-weight: 700; letter-spacing: 0.5px; background: transparent; border: none;"
        )
        start_bar.addWidget(lbl_st)
        self._btn_start_begin = QPushButton("⏮ Al inicio del tema")
        self._btn_start_begin.setFixedHeight(24)
        self._btn_start_begin.setStyleSheet(_btn(BG3, TEXT, BG4, radius=5, fs=10))
        self._btn_start_begin.setCursor(Qt.PointingHandCursor)
        self._btn_start_begin.setToolTip("El primer corte pasa a empezar al principio de la canción (en el primer compás)")
        self._btn_start_begin.clicked.connect(self._start_at_beginning)
        start_bar.addWidget(self._btn_start_begin)
        self._btn_start_mid = QPushButton("⏺ A mitad del tema")
        self._btn_start_mid.setFixedHeight(24)
        self._btn_start_mid.setStyleSheet(_btn(BG3, TEXT, BG4, radius=5, fs=10))
        self._btn_start_mid.setCursor(Qt.PointingHandCursor)
        self._btn_start_mid.setToolTip("El primer corte pasa a empezar a la mitad de la canción (ajustado a un compás)")
        self._btn_start_mid.clicked.connect(self._start_at_middle)
        start_bar.addWidget(self._btn_start_mid)
        lbl_free = QLabel("o arrastra el primer corte en la onda · ▲ ▼ cambian el orden")
        lbl_free.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; background: transparent; border: none;")
        start_bar.addWidget(lbl_free)
        start_bar.addStretch()
        lay.addLayout(start_bar)

        # 3. Tabla de cortes interactiva
        self._tbl_cuts = QTableWidget(0, 9)
        self._tbl_cuts.setHorizontalHeaderLabels([
            "ORDEN · CORTE", "SECCIÓN", "INICIO (s)", "FIN (s)", "DURACIÓN", "EN PREVIA", "OÍR", "QUITAR", "ORDEN"
        ])
        self._tbl_cuts.verticalHeader().setVisible(False)
        self._tbl_cuts.horizontalHeader().setStretchLastSection(False)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self._tbl_cuts.setColumnWidth(0, 98)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self._tbl_cuts.setColumnWidth(6, 44)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
        self._tbl_cuts.setColumnWidth(7, 60)
        self._tbl_cuts.horizontalHeader().setSectionResizeMode(8, QHeaderView.Fixed)
        self._tbl_cuts.setColumnWidth(8, 66)
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
            lbl_n = tbl.cellWidget(r, 0)
            cid = int(lbl_n.property("cut_id") or 0) if lbl_n is not None else 0
            seg = PreviewSegment(section=new_sec, trimmed_start=0.0, trimmed_end=dur, cut_id=cid)
            new_segs.append(seg)

        from src.analysis.segments import AVG_STRETCH_FACTOR, PreviewPlan
        raw_dur = sum(s.duration for s in new_segs)
        est_stretch = raw_dur / AVG_STRETCH_FACTOR
        self._plan = PreviewPlan(
            segments=new_segs,
            estimated_duration_before_stretch=raw_dur,
            estimated_duration_after_stretch=est_stretch,
            drop_starts=list(getattr(self._plan, "drop_starts", []) or []),
        )

        i18n.set_text(self._lbl_cuts_summary, "{n} cortes  ·  Total: {raw}s  ·  Previa est: {est}",
                      n=len(new_segs), raw=f"{raw_dur:.1f}", est=fmt_time_short(est_stretch))
        ok = 120 <= est_stretch <= 180
        self._card_pv.set_value(fmt_time_short(est_stretch))
        self._card_pv.set_accent(GREEN if ok else WARN)

        if HAS_WAVEFORM and self._source_path:
            self._waveform.update_plan_highlights(new_segs)

        self._update_tempo_plot()

    def _quick_cut_start(self, track_dur: float, length: float = 16.0) -> float:
        """Dónde nace un corte nuevo: donde está el cursor de reproducción; si está al principio, en el primer hueco libre."""
        pos = self._player.get_position_seconds() if self._player else 0.0
        if pos > 0.5:
            return min(track_dur - 4.0, max(0.0, round(pos, 1)))
        taken = [(float(s.source_start), float(s.source_end)) for s in (self._plan.segments if self._plan else [])]
        cands = sorted({round(float(x.start_time), 1) for x in self._analysis.sections} | {round(e, 1) for _a, e in taken})
        for c in cands:
            if c + 8.0 <= track_dur and all(c + length <= a or c >= b for a, b in taken):
                return c
        return min(track_dur - 4.0, max(0.0, round(pos, 1)))

    def quick_add_cut(self):
        """Botón «+ Corte»: añade un corte nuevo al instante y avisa de cómo moverlo."""
        if not self._analysis:
            return
        n_before = len(self._plan.segments) if self._plan else 0
        self._on_add_cut_clicked()
        if self._plan and len(self._plan.segments) > n_before:
            seg = self._plan.segments[-1]
            try:
                from src.ui.toast import toast
                toast(self.window(), "info", tr("Corte {n} añadido", n=len(self._plan.segments)),
                      tr("Está en {a}s–{b}s. Arrastra el bloque en la onda para moverlo y sus bordes para cambiar su duración.",
                         a=f"{seg.source_start:.0f}", b=f"{seg.source_end:.0f}"), seconds=5)
            except Exception:
                pass

    def _on_add_cut_clicked(self):
        if not self._analysis:
            return
        track_dur = self._analysis.duration if self._analysis else 300.0
        start = self._quick_cut_start(track_dur)
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
        current_segs.append(new_seg)                 # al final de la previa; con ▲ ▼ se puede colocar donde se quiera

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

    def _fill_plan(self, plan, animate: bool = True):
        if not hasattr(self, "_tbl_cuts"):
            return
        from src.analysis.segments import assign_cut_ids
        assign_cut_ids(plan.segments)
        tbl = self._tbl_cuts
        tbl.setRowCount(0)
        t_pv = 0.0
        track_dur = self._analysis.duration if self._analysis else 600.0

        for idx, seg in enumerate(plan.segments):
            row = tbl.rowCount()
            tbl.insertRow(row)
            tbl.setRowHeight(row, 28)

            # Col 0: # badge
            lbl_num = QLabel(tr("{o}º · Corte {n}", o=idx + 1, n=seg.cut_id))
            lbl_num.setProperty("cut_id", int(seg.cut_id))
            lbl_num.setAlignment(Qt.AlignCenter)
            lbl_num.setStyleSheet(
                f"color: {TEXT_SUB}; font-size: 10.5px; font-weight: 700; background: transparent;"
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
            btn_s_now.setStyleSheet(_btn_icon(BG4, TEXT, BG5))
            btn_s_now.setToolTip("Poner inicio del corte en la posición actual del reproductor")
            btn_s_now.setCursor(Qt.PointingHandCursor)
            def _set_start(_checked=False, sp=spin_s):
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
            btn_e_now.setStyleSheet(_btn_icon(BG4, TEXT, BG5))
            btn_e_now.setToolTip("Poner fin del corte en la posición actual del reproductor")
            btn_e_now.setCursor(Qt.PointingHandCursor)
            def _set_end(_checked=False, sp=spin_e):
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
            btn_play.setStyleSheet(_btn_icon(BG4, GREEN, BG5))
            btn_play.setCursor(Qt.PointingHandCursor)
            btn_play.setToolTip("Escuchar este corte en la pista original")
            btn_play.clicked.connect(lambda _=False, b=btn_play: self._audition_cut(self._cut_row_of(b, 6)))
            tbl.setCellWidget(row, 6, btn_play)

            # Col 7: ELIMINAR CORTE (✕)
            btn_del = QPushButton("✕")
            btn_del.setFixedSize(22, 22)
            btn_del.setStyleSheet(_btn_icon(BG3, RED, BG4))
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setToolTip("Eliminar este corte de la previa")
            btn_del.clicked.connect(lambda _=False, b=btn_del: self._remove_cut(self._cut_row_of(b, 7)))
            tbl.setCellWidget(row, 7, btn_del)

            # Col 8: ORDEN (▲ ▼): el corte suena antes o después en la previa
            w_o = QWidget()
            lay_o = QHBoxLayout(w_o)
            lay_o.setContentsMargins(2, 1, 2, 1)
            lay_o.setSpacing(2)
            for sym, delta, tip in (("▲", -1, "Subir: este corte suena antes en la previa"),
                                    ("▼", 1, "Bajar: este corte suena después en la previa")):
                b_o = QPushButton(sym)
                b_o.setFixedSize(24, 22)
                b_o.setStyleSheet(_btn_icon(BG4, TEXT, BG5, fs=10))
                b_o.setCursor(Qt.PointingHandCursor)
                b_o.setToolTip(tip)
                b_o.setEnabled(0 <= idx + delta < len(plan.segments))
                b_o.clicked.connect(lambda _=False, i=idx, d=delta: self._move_cut(i, d))
                lay_o.addWidget(b_o)
            tbl.setCellWidget(row, 8, w_o)

            t_pv += seg.duration

        raw_dur = sum(s.duration for s in plan.segments)
        est = plan.estimated_duration_after_stretch
        i18n.set_text(self._lbl_cuts_summary, "{n} cortes  ·  Total: {raw}s  ·  Previa est: {est}",
                      n=len(plan.segments), raw=f"{raw_dur:.1f}", est=fmt_time_short(est))
        if animate:
            self._animate_cuts_rows()

    # ── Orden de los cortes y punto de inicio (Basic y Plus) ─────────────────────
    def _cut_rows(self) -> list:
        """Cortes tal como están en la tabla (en el orden en que sonarán): [(inicio, fin, número)]."""
        out = []
        tbl = self._tbl_cuts
        for r in range(tbl.rowCount()):
            w_s, w_e = tbl.cellWidget(r, 2), tbl.cellWidget(r, 3)
            sp_s = w_s.findChild(QDoubleSpinBox) if w_s else None
            sp_e = w_e.findChild(QDoubleSpinBox) if w_e else None
            lbl = tbl.cellWidget(r, 0)
            if sp_s and sp_e:
                out.append((float(sp_s.value()), float(sp_e.value()), int(lbl.property("cut_id") or 0) if lbl else 0))
        return out

    def _apply_cut_rows(self, rows: list):
        """Reconstruye la previa con estos cortes (en este orden) y refresca tabla, onda y tempo."""
        if not self._analysis:
            return
        from src.analysis.structure import Section
        from src.analysis.segments import PreviewSegment, PreviewPlan, AVG_STRETCH_FACTOR
        segs = []
        for (t_s, t_e, cid) in rows:
            sec_type = SectionType.UNKNOWN
            for sec in self._analysis.sections:
                if sec.start_time <= (t_s + t_e) / 2.0 <= sec.end_time:
                    sec_type = sec.type
                    break
            segs.append(PreviewSegment(section=Section(type=sec_type, start_time=t_s, end_time=t_e),
                                       trimmed_start=0.0, trimmed_end=t_e - t_s, cut_id=cid))
        raw_dur = sum(x.duration for x in segs)
        self._plan = PreviewPlan(segments=segs, estimated_duration_before_stretch=raw_dur,
                                 estimated_duration_after_stretch=raw_dur / AVG_STRETCH_FACTOR,
                                 drop_starts=list(getattr(self._plan, "drop_starts", []) or []))
        self._fill_plan(self._plan, animate=False)
        est = self._plan.estimated_duration_after_stretch
        self._card_pv.set_value(fmt_time_short(est))
        self._card_pv.set_accent(GREEN if 120 <= est <= 180 else WARN)
        if HAS_WAVEFORM and self._source_path:
            self._waveform.update_plan_highlights(self._plan.segments)
        self._update_tempo_plot()

    def _cut_row_of(self, widget, col: int) -> int:
        """Fila de la tabla de cortes donde está este botón (-1 si ya no está)."""
        for r in range(self._tbl_cuts.rowCount()):
            if self._tbl_cuts.cellWidget(r, col) is widget:
                return r
        return -1

    def _audition_cut(self, idx: int):
        """▶: escucha este corte en la pista original, desde su inicio ACTUAL (el de la tabla) y hasta su final."""
        rows = self._cut_rows()
        if not self._player or not (0 <= idx < len(rows)):
            return
        start, end, _cid = rows[idx]
        pl = self._player
        if hasattr(pl, "_current_path") and hasattr(pl, "_source_path"):
            if pl._current_path != pl._source_path and pl._source_path:
                pl._switch_to_source(autoplay=False)
        self._audition_end = float(end)
        pl.seek(float(start))
        if not pl.is_playing():
            pl.toggle_play()
        self._audition_pos = float(start)

    def _on_audition_tick(self, pos: float):
        """Al llegar al final del corte que se está escuchando, pausa."""
        end = getattr(self, "_audition_end", None)
        if end is None:
            return
        if pos + 0.05 < getattr(self, "_audition_pos", 0.0) - 1.0:     # el usuario saltó hacia atrás: deja de vigilar
            self._audition_end = None
            return
        self._audition_pos = pos
        if pos >= end:
            self._audition_end = None
            try:
                if self._player and self._player.is_playing():
                    self._player.toggle_play()
            except Exception:
                pass

    def _remove_cut(self, idx: int):
        """✕: quita este corte. Se renumera el orden, se rehacen las flechas ▲ ▼ y se redibuja la onda.
        Siempre debe quedar al menos un corte."""
        rows = self._cut_rows()
        if not (0 <= idx < len(rows)):
            return
        if len(rows) <= 1:
            self.status_message.emit(tr("⚠ La previa necesita al menos un corte"))
            return
        rows.pop(idx)
        self._apply_cut_rows(rows)

    def _move_cut(self, idx: int, delta: int):
        """▲ ▼: cambia el orden en que suenan los cortes (cada corte conserva su nombre «Corte N»)."""
        rows = self._cut_rows()
        j = idx + delta
        if not (0 <= idx < len(rows) and 0 <= j < len(rows)):
            return
        rows[idx], rows[j] = rows[j], rows[idx]
        self._apply_cut_rows(rows)

    def set_beat_times(self, beat_times):
        """Pulsos de la canción (para ajustar el punto de inicio a un compás)."""
        try:
            self._beat_times = [float(x) for x in beat_times]
        except Exception:
            self._beat_times = []
        if HAS_WAVEFORM:
            self._waveform.set_beat_times(self._beat_times)

    def _snap_to_bar(self, t: float) -> float:
        bpm = float(self._bpm or 128.0)
        bar = 4.0 * 60.0 / max(bpm, 1.0)
        bt = getattr(self, "_beat_times", None)
        first = bt[0] if bt else 0.0
        return max(0.0, first + round((t - first) / bar) * bar)

    def _set_first_cut_start(self, t: float):
        """El primer corte de la previa pasa a empezar en `t` (conserva su duración)."""
        rows = self._cut_rows()
        if not rows or not self._analysis:
            return
        t_s, t_e, cid = rows[0]
        dur = max(0.5, t_e - t_s)
        total = float(self._analysis.duration)
        new_s = max(0.0, min(float(t), max(0.0, total - dur)))
        rows[0] = (round(new_s, 1), round(min(total, new_s + dur), 1), cid)
        self._apply_cut_rows(rows)
        if self._player is not None:
            try:
                self._player.seek(rows[0][0])
            except Exception:
                pass

    def _start_at_beginning(self):
        bt = getattr(self, "_beat_times", None)
        self._set_first_cut_start(self._snap_to_bar(bt[0]) if bt else 0.0)

    def _start_at_middle(self):
        if self._analysis:
            self._set_first_cut_start(self._snap_to_bar(float(self._analysis.duration) / 2.0))

    def _animate_cuts_rows(self):
        tbl = self._tbl_cuts
        n = tbl.rowCount()
        for r in range(n):
            tbl.setRowHidden(r, True)
        for r in range(n):
            QTimer.singleShot(r * 35, lambda row=r: tbl.setRowHidden(row, False))

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

    def _build_startend_card(self) -> QFrame:
        """Tarjeta «Cómo empieza y cómo acaba la previa» (Plus): con el efecto de vinilo (de 0 al tempo al empezar,
        del tempo a 0 al acabar, en los segundos que elijas) o directamente a los BPM originales."""
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {BG2}; border: 1px solid {BORDER}; border-radius: 10px; border-left: 3px solid {ACCENT}; }}"
                           " QLabel { background: transparent; border: none; }")
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 7, 12, 7)
        v.setSpacing(5)
        lbl_t = QLabel("🎚 Cómo empieza y cómo acaba la previa")
        lbl_t.setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: 700; background: transparent; border: none;")
        v.addWidget(lbl_t)

        def _row(label, vinyl_txt, vinyl_tip, orig_txt, orig_tip, spin_tip, mode_setter):
            r = QHBoxLayout()
            r.setSpacing(6)
            lab = QLabel(label)
            lab.setFixedWidth(66)
            lab.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9.5px; font-weight: 700; letter-spacing: 0.5px; background: transparent; border: none;")
            r.addWidget(lab)
            b_v = QPushButton(vinyl_txt)
            b_v.setFixedHeight(24)
            b_v.setCursor(Qt.PointingHandCursor)
            b_v.setToolTip(vinyl_tip)
            b_v.clicked.connect(lambda _=False: mode_setter("vinyl"))
            r.addWidget(b_v)
            sp = QDoubleSpinBox()
            sp.setRange(0.5, 6.0)
            sp.setDecimals(1)
            sp.setSingleStep(0.5)
            sp.setValue(1.0)
            sp.setSuffix(" s")
            sp.setFixedHeight(24)
            sp.setStyleSheet(_input_style())
            sp.setToolTip(spin_tip)
            r.addWidget(sp)
            b_o = QPushButton(orig_txt)
            b_o.setFixedHeight(24)
            b_o.setCursor(Qt.PointingHandCursor)
            b_o.setToolTip(orig_tip)
            b_o.clicked.connect(lambda _=False: mode_setter("original"))
            r.addWidget(b_o)
            r.addStretch()
            return r, b_v, sp, b_o

        r1, self._btn_start_vinyl, self._spin_start, self._btn_start_orig = _row(
            "ARRANQUE:", "🌀 Vinilo: de 0 al tempo",
            "La previa arranca como un disco que coge velocidad: de 0 BPM al tempo de la canción en los segundos que elijas",
            "▶ BPM originales desde el inicio", "La previa empieza ya a los BPM originales, sin efecto de arranque",
            "Segundos que tarda en llegar al tempo original", self._set_start_mode)
        r2, self._btn_end_vinyl, self._spin_end, self._btn_end_orig = _row(
            "FINAL:", "🌀 Vinilo: frena hasta parar",
            "La previa acaba como un disco que se para: del tempo de la canción a 0 BPM en los segundos que elijas",
            "⏹ Acabar a los BPM originales", "La previa acaba a los BPM originales, sin frenazo (solo el fundido final)",
            "Segundos que tarda en frenar hasta parar", self._set_end_mode)
        v.addLayout(r1)
        v.addLayout(r2)
        self._start_mode = "vinyl"
        self._end_mode = "vinyl"
        self._refresh_start_mode_ui()
        self._card_startend = card
        card.setVisible(get_edition() == "plus")
        return card

    def _set_start_mode(self, mode: str):
        self._start_mode = "original" if mode == "original" else "vinyl"
        self._refresh_start_mode_ui()

    def _set_end_mode(self, mode: str):
        self._end_mode = "original" if mode == "original" else "vinyl"
        self._refresh_start_mode_ui()

    def _refresh_start_mode_ui(self):
        on = f"QPushButton {{ background: {ACCENT}; color: #ffffff; border: 1px solid {ACCENT}; border-radius: 5px; font-size: 10px; font-weight: 800; padding: 0 9px; }}"
        off = _btn(BG3, TEXT_SUB, BG4, radius=5, fs=10)
        self._btn_start_vinyl.setStyleSheet(on if self._start_mode == "vinyl" else off)
        self._btn_start_orig.setStyleSheet(on if self._start_mode == "original" else off)
        self._spin_start.setEnabled(self._start_mode == "vinyl")
        self._btn_end_vinyl.setStyleSheet(on if self._end_mode == "vinyl" else off)
        self._btn_end_orig.setStyleSheet(on if self._end_mode == "original" else off)
        self._spin_end.setEnabled(self._end_mode == "vinyl")
        for tg, mode in ((getattr(self, "_tg_start", None), self._start_mode), (getattr(self, "_tg_end", None), self._end_mode)):
            if tg is not None and tg.isChecked() != (mode == "vinyl"):
                tg.blockSignals(True)
                tg.setChecked(mode == "vinyl")
                tg.blockSignals(False)
                tg.update()

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
            i18n.set_text(self._lbl_auto_info, "🛡️  Modo Automático activo: El motor aplica micro-variaciones matemáticas orgánicas según la semilla (Seed). "
                "La música suena natural al oído, pero resulta imposible de pinchar o mezclar en reproductores DJ. "
                "Para acelerar en los Drops o crear tus propias subidas, pulsa en 'Manual'.")
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
            i18n.set_text(self._lbl_auto_info, "🎛️  Modo Manual activo: Elige cualquiera de los Presets DJ ('+5 BPM en Drops', 'Rampa Final') "
                "o añade momentos en la tabla para acelerar (+BPM) o ralentizar (-BPM) tramos de la previa.")
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
        def _set_here(_checked=False, sp=spin_t):
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
        def _del_row(_checked=False, target_btn=btn_del):
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

    # ── Edición del producto ──────────────────────────────────────────────────

    def _apply_edition_limits(self):
        """Oculta/deshabilita features exclusivos de Plus en la edición Básica."""
        plus = get_edition() == "plus"

        # Formatos de exportación: WAV y FLAC solo en Plus
        for w in (self._chk_wav, self._chk_flac):
            w.setVisible(plus)
        if not plus:
            self._chk_wav.setChecked(False)

        # Vídeo: Basic lo tiene con marca de agua + cierre con firma obligatorios; Plus sin marca y con final a elegir
        self._chk_video.setVisible(True)
        self._refresh_vend_items(plus)
        self._combo_vend.setVisible(True)          # Basic: firma o fundido a negro · Plus: todas las opciones
        self._row_look_widget.setVisible(plus)     # looks, «Personalizar…» y banner propio: solo Plus
        self._lbl_vdrop.setVisible(plus)
        self._lbl_vbasic.setVisible(not plus)
        self._btn_vlock.setVisible(not plus)
        self._edit_promo.setVisible(plus)          # el banner propio es de Plus
        if not plus:
            self._edit_promo.clear()

        # Siempre modo Vinyl — _speed_mode ya es "vinyl", sin combo que gestionar.

        # Voice Drop solo en Plus
        for w in (self._btn_voice_drop, self._combo_voice_pos, self._lbl_voice_drop):
            w.setVisible(plus)

        # Cortes: orden, nombres y punto de inicio en Basic y Plus. La variación de BPM y la estructura musical, solo Plus.
        self._chk_advanced.setVisible(True)
        self._tabs.setTabVisible(1, plus)
        self._tabs.setTabVisible(2, plus)
        if not plus:
            self._chk_advanced.setChecked(False)
            i18n.set_text(self._chk_advanced, "✂️  Ordenar y mover cortes")

        # FX (Flanger, Filter, Master) — solo Plus
        for w in (self._chk_fx_master, self._lbl_fx_hint):
            w.setVisible(plus)
        self._chk_fx_flanger.setVisible(False)          # sustituidos por los efectos de la onda (Basic y Plus)
        self._chk_fx_filter.setVisible(False)
        self._chk_fx_flanger.setChecked(False)
        self._chk_fx_filter.setChecked(False)
        if not plus:
            self._chk_fx_master.setChecked(False)

        # BrandingCard (firma + carátula) y efectos — solo Plus, dentro de «Opciones avanzadas» (plegadas por defecto)
        self._apply_adv_visibility()

        # Cómo empieza y cómo acaba la previa — solo Plus (en Basic siempre el efecto de vinilo)
        self._card_startend.setVisible(plus)

        # Presets y modo promo antifugas — solo Plus
        self._preset_bar.setVisible(plus)
        self._row_promo_widget.setVisible(plus)
        if not plus:
            self._chk_promo.setChecked(False)

        # Badge informativo en modo Básico
        if not plus and not hasattr(self, "_badge_basic"):
            from PySide6.QtWidgets import QLabel
            self._badge_basic = QLabel("  BÁSICA  ·  Actualiza a PLUS para más formatos y controles  ")
            self._badge_basic.setAlignment(Qt.AlignCenter)
            self._badge_basic.setMaximumHeight(30)
            self._badge_basic.setStyleSheet(f"""
                background: {ACCENT}1a;
                color: {ACCENT};
                border: 1px solid {ACCENT}55;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 700;
                padding: 4px 10px;
                letter-spacing: 0.4px;
            """)
            # Insertar bajo el check de avanzado (último widget antes de tabs)
            lay = self._page2.layout()
            if lay is not None:
                lay.insertWidget(max(0, lay.count() - 2), self._badge_basic)


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
        icon_path = _ASSETS_DIR / "app_icon_1024.png"
        if not icon_path.exists():
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
        self._tour = None                # recorrido de bienvenida en curso
        self._tour_demo = False          # True mientras se analiza la pista de ejemplo del recorrido
        self._pending_project = None     # «Reabrir proyecto»: ajustes a aplicar tras el análisis
        self._update_info   = None
        i18n.init_from_config(self._cfg)
        i18n.install_auto_translate()

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
        if i18n.get_language() != "es":
            i18n.translate_tree(self)
        _log_startup("MainWindow: interfaz de usuario lista.")

        if initial_file:
            _log_startup(f"MainWindow: cargando archivo inicial: {initial_file}")
            self._load_file(initial_file)

    # ── Badge de edición ──────────────────────────────────────────────────

    def _apply_badge_style(self, shimmer: int = 0):
        """Aplica el estilo del badge con offset de shimmer (0-100) para Plus."""
        if self._badge_is_plus:
            # El shimmer desplaza el punto blanco brillante de izquierda a derecha
            s = shimmer / 100.0
            self._edition_badge.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #5b21b6,
                        stop:{max(0.0, s-0.15):.2f} #7c3aed,
                        stop:{s:.2f} #c4b5fd,
                        stop:{min(1.0, s+0.15):.2f} #7c3aed,
                        stop:1 #6d28d9);
                    color: #f5f3ff;
                    border: 1px solid #a78bfa;
                    border-radius: 7px;
                    font-size: 11px;
                    font-weight: 900;
                    padding: 3px 12px;
                    letter-spacing: 2px;
                }}
            """)
        else:
            self._edition_badge.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 #1e3a5f, stop:1 #1d4ed8);
                    color: #bfdbfe;
                    border: 1px solid #60a5fa;
                    border-radius: 7px;
                    font-size: 11px;
                    font-weight: 900;
                    padding: 3px 12px;
                    letter-spacing: 2px;
                }}
            """)

    def _tick_badge_shimmer(self):
        # Un barrido de brillo (~1,8 s) y después reposo (~7 s) con el temporizador parado: antes cambiaba una hoja de estilo
        # cada 60 ms para siempre, lo que mantenía la CPU despierta y relayout constante de la cabecera.
        self._badge_shimmer_phase += 3
        if self._badge_shimmer_phase >= 100 or not self.isVisible():
            self._badge_shimmer_phase = 0
            self._apply_badge_style(100)
            self._badge_shimmer_timer.stop()
            QTimer.singleShot(7000, self._restart_badge_shimmer)
            return
        self._apply_badge_style(self._badge_shimmer_phase)

    def _restart_badge_shimmer(self):
        try:
            if self.isVisible() and not self.isMinimized():
                self._badge_shimmer_timer.start(60)
            else:
                QTimer.singleShot(7000, self._restart_badge_shimmer)
        except RuntimeError:                  # la ventana ya se cerró
            pass

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
        try:
            from src.main import _log_startup as _log
        except Exception:
            def _log(msg): pass
        _log("_build_ui: creando root widget...")
        root_w = QWidget()
        self.setCentralWidget(root_w)
        root = QVBoxLayout(root_w)
        root.setContentsMargins(18, 12, 18, 10)
        root.setSpacing(8)

        # ── HEADER ───────────────────────────────────────────────────────
        _log("_build_ui: construyendo header...")
        self._hdr = QFrame()
        self._hdr.setFixedHeight(66)
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

        # (la versión ya no se enseña en la cabecera: está en ⚙ Licencia y ajustes)

        self._btn_recents = QPushButton("🕒 Recientes")
        self._btn_recents.setFixedHeight(22)
        self._btn_recents.setCursor(Qt.PointingHandCursor)
        self._btn_recents.setStyleSheet(_btn(BG3, TEXT_MID, BG4, radius=4, fs=10))
        self._btn_recents.setToolTip("Ver y cargar archivos de audio procesados recientemente")
        self._btn_recents.clicked.connect(self._open_history_dialog)
        self._btn_recents.setVisible(False)          # v5: viven en el menú «Herramientas»

        self._btn_batch_hdr = QPushButton("📁 Modo Lote")
        self._btn_batch_hdr.setFixedHeight(22)
        self._btn_batch_hdr.setCursor(Qt.PointingHandCursor)
        self._btn_batch_hdr.setStyleSheet(_btn(BG3, TEXT_MID, BG4, radius=4, fs=10))
        self._btn_batch_hdr.setToolTip("Procesar múltiples pistas en lote automáticamente")
        self._btn_batch_hdr.clicked.connect(lambda: self._open_batch_dialog())
        self._btn_batch_hdr.setVisible(False)          # v5: viven en el menú «Herramientas»

        self._btn_watch = QPushButton("👁️ Vigilar Carpeta")
        self._btn_watch.setFixedHeight(22)
        self._btn_watch.setCursor(Qt.PointingHandCursor)
        self._update_watch_button_style()
        self._btn_watch.setToolTip("Vigilar una carpeta y generar previas automáticamente cuando caiga un nuevo tema")
        self._btn_watch.clicked.connect(self._toggle_watch_folder)
        self._btn_watch.setVisible(False)          # v5: viven en el menú «Herramientas»

        self._btn_sign = QPushButton("🖋 Firmar tema")
        self._btn_sign.setFixedHeight(22)
        self._btn_sign.setCursor(Qt.PointingHandCursor)
        self._btn_sign.setStyleSheet(_btn(BG3, TEXT_MID, BG4, radius=4, fs=10))
        self._btn_sign.setToolTip("Firma un tema entero (no una previa): solo le mete la carátula y las etiquetas y lo guarda en FLAC o WAV a máxima calidad")
        self._btn_sign.clicked.connect(lambda _=False: self._open_sign_dialog())
        self._btn_sign.setVisible(False)          # v5: viven en el menú «Herramientas»

        # v5: cabecera simple — «Herramientas ▾» y «Ayuda ▾» agrupan lo que antes eran seis botones sueltos
        self._hdr_btns = QHBoxLayout()
        self._hdr_btns.setSpacing(8)
        self._build_header_menus(self._hdr_btns)

        self._btn_license = QPushButton("⚙")
        self._btn_license.setFixedSize(34, 26)
        self._btn_license.setCursor(Qt.PointingHandCursor)
        self._btn_license.setStyleSheet(f"QPushButton {{ background: {BG3}; color: {TEXT_SUB}; border: 1px solid {BORDER}; border-radius: 6px; font-size: 13px; font-weight: 700; }}"
                                        f"QPushButton:hover {{ border-color: {ACCENT}; color: {TEXT}; }}")
        self._btn_license.setToolTip("Versión, licencia, idioma y actualizaciones")
        self._btn_license.clicked.connect(self._open_license_dialog)
        self._hdr_btns.addWidget(self._btn_license)

        self._btn_lang = QPushButton(i18n.get_language().upper())
        self._btn_lang.setFixedSize(36, 26)
        self._btn_lang.setCursor(Qt.PointingHandCursor)
        self._btn_lang.setStyleSheet(
            f"QPushButton {{ background: {BG3}; color: {TEXT_SUB}; border: 1px solid {BORDER}; border-radius: 6px;"
            "font-size: 11px; font-weight: 800; padding: 0; }"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {TEXT}; }}")
        self._btn_lang.setToolTip("Idioma · Language (ES / EN)")
        self._btn_lang.clicked.connect(self._toggle_language)
        self._hdr_btns.addWidget(self._btn_lang)

        # Ocultar features de lote en edición Básica

        logo_col.addLayout(logo_row)

        sub_lbl = QLabel("RADICAL RECORDS · HARDWARE SYNTH & PREVIEW ENGINE")
        sub_lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 8px; font-weight: 700;"
            "letter-spacing: 1.2px; background: transparent; border: none;"
        )
        logo_col.addWidget(sub_lbl)
        hdr_lay.addLayout(logo_col)
        hdr_lay.addStretch()
        hdr_lay.addLayout(self._hdr_btns)
        hdr_lay.addSpacing(20)

        # Right — banner de Radical Records
        right_col = QVBoxLayout()
        right_col.setSpacing(1)
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

        # Badge de edición — grande, con gradiente y shimmer animado (Plus)
        _ed = get_edition()
        if _ed == "plus":
            _ed_text = "✦  PLUS"
            self._badge_is_plus = True
        else:
            _ed_text = "◈  BÁSICA"
            self._badge_is_plus = False

        self._edition_badge = QLabel(_ed_text)
        self._edition_badge.setAlignment(Qt.AlignCenter)
        self._edition_badge.setMinimumWidth(80)
        self._edition_badge.setFixedHeight(22)
        self._apply_badge_style(0)
        right_col.addWidget(self._edition_badge)

        # Shimmer animado solo en Plus
        self._badge_shimmer_phase = 0
        if self._badge_is_plus:
            self._badge_shimmer_timer = QTimer(self)
            self._badge_shimmer_timer.timeout.connect(self._tick_badge_shimmer)
            self._badge_shimmer_timer.start(60)

        hdr_lay.addLayout(right_col)

        root.addWidget(self._hdr)

        # ── STACK ────────────────────────────────────────────────────────
        _log("_build_ui: construyendo stack...")
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")

        # Página 0 — Drop zone
        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(self._load_file)
        self._drop_zone._btn_guide.clicked.connect(lambda _=False: self.start_tour())
        self._stack.addWidget(self._drop_zone)

        # Página 1 — Análisis en curso (logo animado + progress)
        self._analysis_page = AnalysisPage()
        self._stack.addWidget(self._analysis_page)

        # Página 2 — Resultados (scroll)
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
        self._results.bpm_corrected.connect(self._on_bpm_corrected)
        self._results.status_message.connect(lambda m: self._progress_label.setText(i18n.translate(m)))
        scroll.setWidget(self._results)
        self._stack.addWidget(scroll)  # índice 2

        # Página 3 — «¿Para qué es esta previa?» (se enseña tras analizar el tema; se puede saltar)
        from src.ui.wizard import DestinationPage
        dscroll = QScrollArea()
        dscroll.setWidgetResizable(True)
        dscroll.setFrameShape(QFrame.NoFrame)
        dscroll.setStyleSheet(scroll.styleSheet())
        self._dest_page = DestinationPage(get_edition() == "plus")
        self._dest_page.chosen.connect(self._on_destination_chosen)
        self._dest_page.skipped.connect(lambda: self._leave_destination(None))
        self._dest_page.other_track.connect(lambda: self._drop_zone._open_dialog())
        self._dest_page.guide_requested.connect(lambda: self.start_tour())
        dscroll.setWidget(self._dest_page)
        self._stack.addWidget(dscroll)  # índice 3
        self._results.change_destination_requested.connect(lambda: self._fade_to_page(3))

        root.addWidget(self._stack, stretch=1)

        # ── PROGRESS FRAME ────────────────────────────────────────────────
        _log("_build_ui: construyendo progress frame...")
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
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setFixedHeight(16)
        self._progress_bar.setMinimumWidth(100)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {BG3};
                border: none;
                border-radius: 7px;
                color: {TEXT};
                font-size: 9px;
                font-weight: 700;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {ACCENT}, stop:1 {ACCENT2});
                border-radius: 7px;
            }}
        """)

        pf.addWidget(self._progress_label, stretch=1)
        pf.addWidget(self._progress_bar)
        root.addWidget(prog_frame)

        # ── Banner de actualización (oculto por defecto) ──────────────────
        _log("_build_ui: construyendo banner actualización...")
        self._update_banner = QLabel()
        self._update_banner.setOpenExternalLinks(False)
        self._update_banner.linkActivated.connect(lambda _l: self._show_update_dialog())
        self._update_info = None
        self._update_banner.setAlignment(Qt.AlignCenter)
        self._update_banner.setVisible(False)
        self._update_banner.setStyleSheet(f"""
            QLabel {{
                background: #1e1b4b;
                color: #c4b5fd;
                border: 1px solid #6d28d9;
                border-radius: 6px;
                font-size: 11px;
                padding: 5px 12px;
            }}
        """)
        root.addWidget(self._update_banner)

        # ── Lanzar comprobador de actualizaciones en segundo plano ────────
        try:
            from src.update import UpdateChecker
            from src.__version__ import __version__
            self._update_checker = UpdateChecker(__version__, parent=self)
            self._update_checker.update_available.connect(self._on_update_available)
            self._update_checker.start()
        except Exception:
            self._update_banner = None

        self._start_license_watch()

    # ── Vigilancia de la licencia (la verificación con el servidor la hace un hilo aparte) ──
    def _start_license_watch(self):
        try:
            from src.config import _get_baked_edition
            if _get_baked_edition() is None:        # en desarrollo no hay licencia
                return
        except Exception:
            return
        self._license_timer = QTimer(self)
        self._license_timer.setInterval(30_000)
        self._license_timer.timeout.connect(self._check_license_watch)
        self._license_timer.start()

    def _check_license_watch(self):
        """Si el servidor revocó la licencia (otro equipo, reembolso…), avisa y cierra al terminar de exportar."""
        from src.licensing.license import revoked_reason
        reason = revoked_reason()
        if not reason:
            return
        worker = getattr(self, "_export_worker", None)
        if worker is not None and worker.isRunning():
            return                                  # no cortar una exportación en curso
        self._license_timer.stop()
        from PySide6.QtWidgets import QApplication, QMessageBox
        if reason == "in_use":
            msg = ("Esta licencia se ha activado en otro equipo.\nSolo puede estar activa en un equipo a la vez.\n"
                   "AutoPrevias se cerrará.")
        else:
            msg = "Tu licencia ya no es válida.\nAutoPrevias se cerrará."
        QMessageBox.critical(self, "AutoPrevias", tr(msg))
        QApplication.quit()

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
        self._fade_to_page(self._stack.currentIndex())

    def _fade_to_page(self, index: int):
        """Transición suave hacia la página `index` del stack (a los resultados se entra deslizando)."""
        if _anim.enabled() and index == 2 and self._stack.currentIndex() != index and self._stack.isVisible():
            _anim.snapshot_transition(self._stack, lambda: self._stack.setCurrentIndex(index), direction=1, ms=380, slide=44)
            return
        self._stack.setCurrentIndex(index)
        w = self._stack.currentWidget()
        if w is None:
            return
        if _anim.enabled() and index == 2:
            return
        if _anim.enabled() and index == 3 and getattr(self, "_dest_page", None) is not None:
            # «¿Para qué es esta previa?»: las seis tarjetas entran una tras otra (son pequeñas: no pesa)
            _anim.stagger_fade_in(list(self._dest_page.tiles.values()), step_ms=55, ms=260)
            return
        eff = QGraphicsOpacityEffect(w)
        w.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(320)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: w.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    # ── Carga ─────────────────────────────────────────────────────────────

    def _load_file(self, path: str):
        from src.engine.audio_io import repair_wav_header_if_needed
        repair_wav_header_if_needed(path)

        demo = bool(getattr(self, "_tour_demo", False))      # pista de ejemplo del recorrido: sin rastro en Recientes
        # Registrar en historial de recientes (Apartado 3: 3)
        try:
            from src.config import add_recent_file
            if not demo:
                add_recent_file(path, self._cfg)
        except Exception:
            pass

        # Extracción automática de carátula incrustada (Apartado 2: 2)
        try:
            from src.config import extract_embedded_cover
            emb_cover = None if demo else extract_embedded_cover(path)
            if emb_cover and emb_cover.exists():
                self._cfg["session_cover_path"] = str(emb_cover)
                self._cfg["cover_path"] = str(emb_cover)
        except Exception:
            pass

        self._current_file = path
        name = Path(path).name
        self._hint_lbl.setText(name[:50] + ("…" if len(name) > 50 else ""))
        self._set_progress(0, "Analizando  {name}", name=name)
        self._start_dots()

        # Mostrar página de análisis animada con crossfade
        self._analysis_page.start(name)
        self._fade_to_page(1)

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
        self._worker.progress.connect(self._analysis_page.update_progress)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_analysis_done(self, analysis, plan, grid, bpm: float, dur: float, key_res=None):
        self._stop_dots()
        self._analysis_page.stop()
        self._analysis  = analysis
        self._plan      = plan
        self._beat_grid = grid
        self._key_res   = key_res

        # v5: tras analizar se pregunta «¿Para qué es esta previa?» (salvo en el recorrido, al reabrir un proyecto, en modo
        # Estudio o si el usuario marcó «No volver a mostrar»); si no, directo a los resultados (índice 2)
        ask = not (self._tour_demo or self._pending_project is not None or load_cfg().get("always_studio")
                   or load_cfg().get("skip_destination"))
        self._fade_to_page(3 if ask else 2)

        try:
            self._results.set_beat_times(getattr(grid, "beat_times", []))
        except Exception:
            pass
        self._results.populate(analysis, plan, bpm, dur,
                               self._current_file, self._cfg, key_res=key_res)

        drops = len(analysis.drops())
        self._fill_destination_page(self._current_file, bpm, dur, key_res, drops)
        key_str = f"  ·  {key_res.camelot} ({key_res.notation})" if key_res else ""
        self._set_progress(
            100, "✅  {name}  ·  {bpm} BPM{key}  ·  {drops} {word}",
            name=Path(self._current_file).name, bpm=f"{bpm:.1f}", key=key_str, drops=drops,
            word="drop" if drops == 1 else "drops",
        )

        # «Reabrir proyecto»: restaurar ajustes y seed de la previa original
        if self._pending_project is not None:
            entry, self._pending_project = self._pending_project, None
            try:
                self._results.restore_project(entry.get("settings") or {}, int(entry.get("seed", 0)))
                self._set_progress(100, "🔄 Proyecto reabierto: mismos ajustes y misma seed que la previa original")
            except Exception:
                pass

    def _on_destination_chosen(self, key: str):
        self._leave_destination(key)

    def _leave_destination(self, key):
        """Sale de la pantalla de destino hacia el paso ② (aplicando el destino elegido, si lo hay)."""
        if self._dest_page.chk_never.isChecked():
            try:
                c = load_cfg()
                c["skip_destination"] = True
                save_cfg(c)
            except Exception:
                pass
        self._fade_to_page(2)
        self._results.go_step(2, animate=False)
        if key:
            self._results._apply_destination(key)

    def _fill_destination_page(self, name: str, bpm: float, dur: float, key_res, drops: int):
        r = self._results
        wf = getattr(r, "_waveform", None)
        rms = getattr(wf, "_source_rms", None) if wf is not None else None
        mins, secs = divmod(int(round(dur)), 60)
        bits = [f"{mins}:{secs:02d}", f"{bpm:.0f} BPM"]
        if key_res:
            bits.append(f"{key_res.camelot}")
        bits.append(tr("{n} drops detectados", n=drops) if drops != 1 else tr("1 drop detectado"))
        self._dest_page.set_track(Path(name).stem, " · ".join(bits), rms)
        # la onda se carga en segundo plano: se vuelve a pintar cuando llega
        for ms in (600, 1500, 3500):
            QTimer.singleShot(ms, lambda: self._dest_page.wave.set_envelope(getattr(getattr(r, "_waveform", None), "_source_rms", [])))

    def _on_error(self, msg: str):
        self._stop_dots()
        self._analysis_page.stop()
        self._fade_to_page(0)
        # Mostrar solo la última línea del traceback para no saturar
        lines = [ln for ln in msg.strip().splitlines() if ln.strip()]
        short = lines[-1] if lines else msg
        self._set_progress(0, f"❌  {short}")
        from src.ui.toast import toast
        retry = self._current_file
        toast(self, "error", "No se pudo analizar el tema", short,
              action=(("Reintentar", lambda: self._load_file(retry)) if retry else None))

    def _set_progress(self, pct: int, msg: str, **kw):
        """`msg` es el texto fuente en castellano (plantilla si lleva `kw`): se traduce según el idioma
        activo y se recuerda para poder volver a pintarlo al cambiar de idioma."""
        self._progress_src = (msg, kw)
        text = tr(msg, **kw) if kw else i18n.translate(msg)
        _anim.smooth_progress(self._progress_bar, pct)
        # Guardar el mensaje limpio para la animación de puntos
        self._progress_msg = text.rstrip(".… ")
        self._progress_label.setText(text)

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
        self._analysis_page.stop()
        self._fade_to_page(0)
        i18n.set_text(self._hint_lbl, "Arrastra un track para comenzar")
        self._set_progress(0, "Listo — arrastra un track o pulsa Abrir archivo")

    def _set_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, tr("Carpeta donde guardar las previas"),
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
        if video:
            mp3 = options["export_mp3"] = True      # sin previa no hay vídeo
        if options.get("promo_mode") and not (options.get("voice_drop_path")
                                               and Path(options["voice_drop_path"]).exists()):
            self._set_progress(0, "⚠  El modo promo necesita tu firma: elige un audio con 🎙️ Voice Drop…")
            return
        if not any([wav, mp3, flac, video]):
            self._set_progress(0, "⚠  Selecciona al menos un formato para exportar")
            return
        if video and get_edition() == "plus" and options.get("video_custom"):
            # Plus: avisa si la imagen elegida no tiene el formato del vídeo (9:16, 1:1 o 16:9)
            from src.engine.video_neon import image_format_problems
            from src.ui.video_custom import ask_format_mismatch
            for _asp in (options.get("aspect_ratios") or [options.get("aspect_ratio", "9:16")]):
                _probs = image_format_problems(options["video_custom"], _asp)
                if _probs:
                    if ask_format_mismatch(self, _probs, _asp) == "change":
                        self._results._open_video_custom()
                        return
                    break                                       # «seguir igualmente»: no se pregunta por cada formato

        seed = self._results.get_seed()
        metadata = self._results.get_branding_metadata()
        if options.get("promo_mode"):
            metadata = dict(metadata)
            base = (metadata.get("comment") or "").strip()
            metadata["comment"] = (base + " · " if base else "") + "PROMO — NO DISTRIBUIR / NOT FOR DISTRIBUTION"
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
            user_files = [p for p in generated if not Path(p).name.startswith("autoprevias_temp_")]
            display = user_files if user_files else generated
            names = ", ".join(Path(p).name for p in display)
            folder = str(Path(display[0]).parent)
            self._set_progress(100, "✅  Guardado en: {folder}  ·  ({names})", folder=folder, names=names)
            self._record_history(generated, seed)
            self._results._btn_open_folder.setStyleSheet(_btn("#059669", "#ffffff", "#10b981", radius=5, fs=10.5))
            from src.ui.toast import toast
            toast(self, "success", "Previa generada", names, action=("Abrir carpeta", self._open_export_folder), seconds=8)
            # F6 — Notificación nativa del SO
            try:
                from src.notifications import notify
                track = Path(self._current_file).stem if self._current_file else "Track"
                notify("AutoPrevias", tr("✅ Previa «{track}» generada · pulsa para abrir", track=track),
                       folder=str(display[0]))
            except Exception:
                pass
        else:
            self._set_progress(0, "⚠  No se generaron archivos.")

    def _on_bpm_corrected(self, bpm: float):
        """F4 — Actualiza el beat grid con el BPM corregido manualmente."""
        if self._beat_grid is not None:
            try:
                from src.analysis.bpm import BeatGrid
                import dataclasses
                self._beat_grid = dataclasses.replace(self._beat_grid, bpm=bpm)
            except Exception:
                pass

    def _on_update_available(self, info):
        """Hay versión nueva: banner discreto y ventana de actualización."""
        if not hasattr(self, "_update_banner") or self._update_banner is None:
            return
        self._update_info = info
        self._render_update_banner()
        self._update_banner.setVisible(True)
        QTimer.singleShot(1000, self._show_update_dialog)

    def _show_update_dialog(self):
        info = getattr(self, "_update_info", None)
        if info is None or getattr(self, "_update_dialog_open", False):
            return
        self._update_dialog_open = True
        try:
            from src.ui.update_dialog import UpdateDialog
            from src.config import get_edition
            from src.__version__ import __version__
            UpdateDialog(info, __version__, get_edition(), parent=self).exec()
        except Exception:
            pass
        finally:
            self._update_dialog_open = False

    def _on_export_error(self, msg: str):
        self._stop_dots()
        lines = [ln for ln in msg.strip().splitlines() if ln.strip()]
        short = lines[-1] if lines else msg
        self._results._btn_generate.setEnabled(True)
        i18n.set_text(self._results._btn_generate, "▶   GENERAR PREVIA")
        self._results._apply_generate_style(True)
        self._set_progress(0, f"❌  {short}")
        from src.ui.toast import toast
        toast(self, "error", "No se pudo generar la previa", short,
              action=("Reintentar", lambda: self._results._btn_generate.click()))

    # ── Drag global (ventana) ─────────────────────────────────────────────

    _IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

    def _classify_drop(self, md):
        audio, images = [], []
        for url in md.urls():
            path = url.toLocalFile()
            suf = Path(path).suffix.lower()
            if suf in AUDIO_EXTS:
                audio.append(path)
            elif suf in self._IMG_EXTS:
                images.append(path)
        return audio, images

    def dragEnterEvent(self, e: QDragEnterEvent):
        # v5: se acepta audio (en cualquier pantalla) e imágenes (carátula, en Plus y con un tema cargado); se carga al SOLTAR
        if not e.mimeData().hasUrls():
            return
        audio, images = self._classify_drop(e.mimeData())
        if audio or images:
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            audio, images = self._classify_drop(e.mimeData())
            if audio or images:
                e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        audio, images = self._classify_drop(e.mimeData())
        if audio:
            e.acceptProposedAction()
            if len(audio) > 1 and get_edition() == "plus":
                self._open_batch_dialog(audio)
            else:
                self._load_file(audio[0])
        elif images:
            e.acceptProposedAction()
            self._cover_dropped(images[0])

    def _cover_dropped(self, path: str):
        """Imagen soltada en la ventana con un tema cargado = carátula de la previa (Plus)."""
        from src.ui.toast import toast
        if self._stack.currentIndex() != 2:
            toast(self, "info", "Primero carga un tema", "Suelta una imagen cuando el tema esté cargado y la usaré como carátula.")
            return
        if get_edition() != "plus":
            toast(self, "info", "Carátula propia: solo en Plus",
                  "La edición Plus te deja elegir tu carátula y firmar los archivos.",
                  action=("Ver Plus", self._results._open_plus_page))
            return
        try:
            self._results._branding_card._drop_area.set_cover(path)
            self._results._set_adv_open(True)
            toast(self, "success", "Carátula cambiada", Path(path).name)
        except Exception as ex:
            toast(self, "error", "No se pudo usar la imagen", str(ex))

    def _open_audio_dialog(self):
        self._drop_zone._open_dialog()

    def _open_batch_dialog(self, initial_files: list | None = None):
        try:
            from src.ui.batch import BatchDialog
            dlg = BatchDialog(initial_files=initial_files, parent=self)
            dlg.exec()
        except Exception as ex:
            self._set_progress(0, "❌ Error abriendo Modo Lote: {err}", err=str(ex))

    def _build_header_menus(self, logo_row):
        """Botones «🧰 Herramientas ▾» y «❓ Ayuda ▾» de la cabecera."""
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMenu
        plus = get_edition() == "plus"
        menu_css = (f"QMenu {{ background: {BG2}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px; }}"
                    f"QMenu::item {{ padding: 7px 18px; border-radius: 5px; font-size: 12px; }}"
                    f"QMenu::item:selected {{ background: {ACCENT}; color: #ffffff; }}"
                    f"QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px 8px; }}")
        btn_css = (f"QPushButton {{ background: {BG3}; color: {TEXT_SUB}; border: 1px solid {BORDER}; border-radius: 6px;"
                   " font-size: 11px; font-weight: 700; padding: 0 12px; }"
                   f"QPushButton:hover {{ border-color: {ACCENT}; color: {TEXT}; }}"
                   "QPushButton::menu-indicator { image: none; width: 0; }")

        def _lock(txt: str):
            return f"🔒 {txt} (Plus)"

        # — Herramientas —
        self._btn_tools = QPushButton("🧰 Herramientas  ▾")
        self._btn_tools.setFixedHeight(26)
        self._btn_tools.setCursor(Qt.PointingHandCursor)
        self._btn_tools.setStyleSheet(btn_css)
        self._btn_tools.setToolTip("Recientes, Modo Lote, Vigilar carpeta y Firmar tema entero")
        self._tools_menu = QMenu(self._btn_tools)
        self._tools_menu.setStyleSheet(menu_css)
        self._act_recents = self._tools_menu.addAction("🕒 Recientes")
        self._act_recents.triggered.connect(lambda _=False: self._open_history_dialog())
        self._tools_menu.addSeparator()
        self._act_batch = self._tools_menu.addAction("📁 Modo Lote" if plus else _lock("Modo Lote"))
        self._act_watch = self._tools_menu.addAction("👁 Vigilar carpeta" if plus else _lock("Vigilar carpeta"))
        self._act_sign = self._tools_menu.addAction("🖋 Firmar tema entero" if plus else _lock("Firmar tema entero"))
        if plus:
            self._act_batch.triggered.connect(lambda _=False: self._open_batch_dialog())
            self._act_watch.triggered.connect(lambda _=False: self._toggle_watch_folder())
            self._act_sign.triggered.connect(lambda _=False: self._open_sign_dialog())
        else:
            for a in (self._act_batch, self._act_watch, self._act_sign):
                a.triggered.connect(lambda _=False: self._results._open_plus_page())
        self._tools_menu.aboutToShow.connect(self._refresh_tools_menu)
        self._btn_tools.setMenu(self._tools_menu)
        logo_row.addWidget(self._btn_tools)

        # — Ayuda —
        self._btn_help = QPushButton("❓ Ayuda  ▾")
        self._btn_help.setFixedHeight(26)
        self._btn_help.setCursor(Qt.PointingHandCursor)
        self._btn_help.setStyleSheet(btn_css)
        self._btn_help.setToolTip("Guía de 2 minutos, atajos de teclado y soporte")
        self._help_menu = QMenu(self._btn_help)
        self._help_menu.setStyleSheet(menu_css)
        self._act_tour = self._help_menu.addAction("🎓 Guía de 2 minutos")
        self._act_tour.triggered.connect(lambda _=False: self.start_tour())
        self._act_keys = self._help_menu.addAction("⌨ Atajos de teclado")
        self._act_keys.triggered.connect(lambda _=False: self._show_shortcuts())
        self._help_menu.addSeparator()
        self._act_support = self._help_menu.addAction("✉ Escribir a soporte")
        self._act_support.triggered.connect(lambda _=False: self._open_support_mail())
        self._btn_help.setMenu(self._help_menu)
        logo_row.addWidget(self._btn_help)

    def _refresh_menu_texts(self):
        """Los textos de los menús no los recorre translate_tree: se repintan al cambiar de idioma."""
        plus = get_edition() == "plus"
        self._btn_tools.setText(tr("🧰 Herramientas  ▾"))
        self._btn_help.setText(tr("❓ Ayuda  ▾"))
        self._act_recents.setText(tr("🕒 Recientes"))
        lock = lambda t: tr(f"🔒 {t} (Plus)")
        self._act_batch.setText(tr("📁 Modo Lote") if plus else lock("Modo Lote"))
        self._act_sign.setText(tr("🖋 Firmar tema entero") if plus else lock("Firmar tema entero"))
        self._act_watch.setText(tr("👁 Vigilar carpeta") if plus else lock("Vigilar carpeta"))
        self._act_tour.setText(tr("🎓 Guía de 2 minutos"))
        self._act_keys.setText(tr("⌨ Atajos de teclado"))
        self._act_support.setText(tr("✉ Escribir a soporte"))

    def _refresh_tools_menu(self):
        """El texto de «Vigilar carpeta» refleja si está activo."""
        if get_edition() != "plus":
            return
        if self._watching and self._watched_folder:
            self._act_watch.setText(tr("👁 Dejar de vigilar «{n}»", n=Path(self._watched_folder).name))
        else:
            self._act_watch.setText(tr("👁 Vigilar carpeta"))

    def _open_support_mail(self):
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(f"mailto:{SUPPORT}"))
        except Exception:
            pass

    def _show_shortcuts(self):
        from src.ui.shortcuts import ShortcutsDialog
        ShortcutsDialog(self).exec()

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
            i18n.set_text(self._btn_watch, "👁️ Vigilar Carpeta")
            self._btn_watch.setStyleSheet(_btn(BG3, TEXT_MID, BG4, radius=4, fs=10))

    def _open_history_dialog(self):
        from src.ui.history_dialog import HistoryDialog
        dlg = HistoryDialog(plus=get_edition() == "plus", parent=self)
        dlg.reopen_requested.connect(self._reopen_project)
        dlg.open_track_requested.connect(self._load_file)
        dlg.reveal_requested.connect(self._reveal_in_os)
        dlg.exec()

    def _reopen_project(self, entry: dict):
        src = entry.get("source") or ""
        if not (src and Path(src).exists()):
            self._set_progress(0, "⚠ No se encuentra la pista original: {name}", name=Path(src).name or "—")
            return
        self._pending_project = entry
        self._load_file(src)

    def _record_history(self, generated: list, seed: int):
        """Guarda la previa en el historial («Recientes») con los ajustes para poder reabrirla."""
        try:
            from src.history import add_entry
            r = self._results
            est = r._plan.estimated_duration_after_stretch if r._plan else 0.0
            settings = {"state": r.get_state(True, True, events=True), "tempo_mode": r.get_tempo_mode(),
                        "tempo_events": r.get_tempo_events()}
            add_entry(self._current_file, generated, seed=seed, bpm=r._bpm, key=r._key_str, duration_sec=est,
                      settings=settings, promo=bool(r.get_export_options().get("promo_mode")))
        except Exception:
            pass

    def _render_update_banner(self):
        info = self._update_info
        if info is None or getattr(self, "_update_banner", None) is None:
            return
        self._update_banner.setText(tr(
            "🆕  AutoPrevias {v} disponible — <a href='update' style='color:#a78bfa;'>Actualizar</a>",
            v=info.version))

    # ── Recorrido de bienvenida (solo la primera vez en una instalación nueva) ─────────────────
    def maybe_start_onboarding(self):
        """Primera vez: ofrece el recorrido («Hacer el recorrido» / «Omitir»). Después no vuelve a preguntar."""
        from src.ui import tour
        if not tour.should_offer_onboarding(load_cfg()):
            return
        dlg = tour.WelcomeDialog(self)
        dlg.exec()
        tour.mark_onboarding_done(self._cfg)
        if dlg.choice == "tour":
            self.start_tour()

    def start_tour(self):
        """Lanza el recorrido guiado (también desde ⚙ Licencia → «Ver recorrido de bienvenida»)."""
        from src.ui import tour
        if getattr(self, "_tour", None) is not None:
            return
        if self._worker is not None and self._worker.isRunning():
            return
        if self._stack.currentIndex() != 0:
            self._back_to_drop()
        self._tour = tour.OnboardingTour(self)
        self._tour.finished.connect(lambda _c: setattr(self, "_tour", None))
        self._tour.start()

    def _open_sign_dialog(self, files=None):
        """Ventana «Firmar tema entero» (Plus): carátula + etiquetas, sin masterizar, en FLAC o WAV."""
        if get_edition() != "plus":
            return
        from src.ui.sign_track import SignTrackDialog
        dlg = getattr(self, "_sign_dialog", None)
        if dlg is None or not dlg.isVisible():
            # datos al día (no los de cuando se abrió la app) y lo que haya ahora en «Firma y carátula»
            try:
                fresh = load_cfg()
            except Exception:
                fresh = dict(self._cfg)
            defaults = {}
            try:
                r = self._results
                defaults = {"meta": r.get_branding_metadata(), "cover": r.get_branding_cover_path()}
            except Exception:
                pass
            dlg = SignTrackDialog(fresh, parent=self, files=files if isinstance(files, (list, tuple)) else None,
                                  defaults=defaults)
            dlg.setAttribute(Qt.WA_DeleteOnClose, True)
            dlg.destroyed.connect(lambda *_: setattr(self, "_sign_dialog", None))
            self._sign_dialog = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _open_license_dialog(self):
        from src.ui.about import LicenseDialog
        found = []
        dlg = LicenseDialog(VERSION, get_edition(), parent=self)
        dlg.language_changed.connect(self._apply_language)
        dlg.tour_requested.connect(lambda: QTimer.singleShot(0, self.start_tour))
        dlg.update_found.connect(found.append)
        dlg.license_removed.connect(lambda: QTimer.singleShot(0, self.close))
        dlg.exec()
        if found:
            self._on_update_available(found[0])

    def _toggle_language(self):
        self._apply_language("en" if i18n.get_language() == "es" else "es")

    def _apply_language(self, code: str):
        """Cambia el idioma en caliente y lo recuerda para el próximo arranque."""
        code = i18n.set_language(code)
        self._cfg["language"] = code
        try:
            c = load_cfg()
            c["language"] = code
            save_cfg(c)
        except Exception:
            pass
        def _retranslate():
            i18n.translate_tree(self)
            self._btn_lang.setText(code.upper())
            self._render_update_banner()
            src = getattr(self, "_progress_src", None)
            if src is not None:
                self._set_progress(self._progress_bar.value(), src[0], **src[1])
            self._results.refresh_language()
            self._refresh_menu_texts()
        _anim.crossfade_transition(self.centralWidget(), _retranslate)

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
            self, tr("Seleccionar carpeta para vigilar (Watch Folder)"),
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
        self._set_progress(0, "👁️ Vigilando: {name} (escanea nuevos audios cada 4s)", name=Path(folder).name)

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
        _seen_in_scan = set()
        for f in p_dir.glob("*"):
            if f.suffix.lower() not in AUDIO_EXTS:
                continue
            rf = str(f.resolve())
            if rf in self._watched_processed or rf in _seen_in_scan:
                continue
            _seen_in_scan.add(rf)
            try:
                if f.stat().st_size > 10000:
                    new_files.append(f)
            except Exception:
                pass

        if new_files:
            target = new_files[0]
            self._watched_processed.add(str(target.resolve()))
            self._set_progress(0, "👁️ Detectado nuevo tema en carpeta vigilada: {name}", name=target.name)
            self._load_file(str(target))

    def keyPressEvent(self, e):
        # Atajos de reproducción para DJs cuando no se está editando un campo de texto
        focus = QApplication.focusWidget()
        in_input = isinstance(focus, (QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox))
        mods = e.modifiers()
        ctrl = bool(mods & Qt.ControlModifier)
        k0 = e.key()
        R = getattr(self, "_results", None)
        on_results = R is not None and self._stack.currentIndex() == 2
        if ctrl and k0 == Qt.Key_O:
            self._open_audio_dialog()
            e.accept()
            return
        if ctrl and k0 == Qt.Key_G and on_results:
            R.go_step(3, animate=False)
            if R._btn_generate.isEnabled():
                R._btn_generate.click()
            e.accept()
            return
        if ctrl and k0 in (Qt.Key_2, Qt.Key_3) and on_results:
            R.go_step(2 if k0 == Qt.Key_2 else 3)
            e.accept()
            return
        if ctrl and k0 == Qt.Key_E and on_results:
            R.set_studio(not R._studio)
            self._cfg["always_studio"] = bool(R._studio)
            try:
                c = load_cfg()
                c["always_studio"] = bool(R._studio)
                save_cfg(c)
            except Exception:
                pass
            e.accept()
            return
        if not in_input and on_results and ctrl and (k0 == Qt.Key_Z or k0 == Qt.Key_Y):
            if k0 == Qt.Key_Y or (mods & Qt.ShiftModifier):
                R.redo()
            else:
                R.undo()
            e.accept()
            return
        if not in_input and (k0 == Qt.Key_F1 or (k0 == Qt.Key_Question and not ctrl)):
            self._show_shortcuts()
            e.accept()
            return
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

def _save_hw_cache():
    """Guarda specs del hardware en cache para arranques futuros más informados."""
    try:
        import json
        import platform
        import multiprocessing
        from src.config import get_user_data_dir
        cache_file = Path(get_user_data_dir()) / "hw_cache.json"
        if cache_file.exists():
            return  # ya está cacheado
        specs: dict = {
            "cpu":       platform.processor() or platform.machine(),
            "cores":     multiprocessing.cpu_count(),
            "platform":  sys.platform,
            "python":    platform.python_version(),
            "machine":   platform.machine(),
            "node":      platform.node(),
        }
        try:
            import psutil
            specs["ram_gb"] = round(psutil.virtual_memory().total / 1e9, 1)
        except Exception:
            pass
        cache_file.write_text(json.dumps(specs, indent=2, ensure_ascii=False))
    except Exception:
        pass


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
    _anim.install_button_fx(app)           # brillo al pasar el ratón sobre los botones
    _anim.install_dialog_fx(app)           # las ventanas aparecen con fundido

    # Fuente del sistema nativa (sin avisos de alias)
    family_to_use = ".AppleSystemUIFont" if sys.platform == "darwin" else "Segoe UI"
    app.setFont(QFont(family_to_use, 12))

    # Splash screen animado mientras se carga MainWindow
    splash = SplashWindow()
    splash.show()
    app.processEvents()

    _log_startup("Iniciando cache de hardware...")
    _save_hw_cache()

    _log_startup("Instanciando MainWindow...")
    splash.set_progress(60, "Construyendo interfaz…")
    app.processEvents()

    win = MainWindow(initial_file=initial_file)
    app.aboutToQuit.connect(win._cleanup_threads)

    splash.set_progress(100, "¡Todo listo!")
    splash.repaint()

    _log_startup("Mostrando ventana principal...")
    # Mostramos la ventana ANTES de cerrar el splash para que macOS inicialice
    # los controles nativos (QComboBox → NSPopUpButton) con la ventana ya visible.
    # Esto evita el popup fantasma "Vinilo (+Pitch Armónico)" que aparecía cuando
    # QSplashScreen.finish() llamaba winId() antes de que la ventana fuera visible.
    # El splash se cierra 80ms después para asegurar que la transición es suave.
    win.show()
    QTimer.singleShot(80, splash.close)
    QTimer.singleShot(1200, win.maybe_start_onboarding)      # bienvenida: solo en instalaciones nuevas

    _log_startup("Ventana principal visible. Ejecutando app.exec()...")
    sys.exit(app.exec())


if __name__ == "__main__":
    launch(sys.argv[1] if len(sys.argv) > 1 else "")
