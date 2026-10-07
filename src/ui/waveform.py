"""
AutoPrevias — Widget de forma de onda interactiva y profesional (Fase C+).

Novedades:
- Doble modo sincronizado:
  * "source"  → Visualiza la pista completa original con regiones coloreadas,
                cajas de corte discontinuas de la previa y límites arrastrables.
  * "preview" → Visualiza la forma de onda de la previa generada con sus
                transiciones, drops estirados y regiones de segmento en orden.
- Indicador en tiempo real de sección actual (badge dinámico con color y nombre:
  INTRO, SUBIDA, DROP 1, DESCANSO, DROP 2).
- Loader ultrarrápido con soundfile + numpy (<20ms para WAV) con fallback a librosa.
- Sincronización instantánea de playhead y seek por clic directo en cualquier punto.
- Líneas divisorias arrastrables con feedback visual continuo.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton

try:
    import pyqtgraph as pg
    pg.setConfigOptions(antialias=False, useOpenGL=False)
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False

# ── Paleta estética ───────────────────────────────────────────────────────────
SECTION_COLORS: dict[str, tuple] = {
    "intro":     (220,  30,  50, 55),
    "buildup":   (255, 110,  20, 75),
    "drop":      (255,  25,  55, 95),
    "breakdown": (140,  20, 160, 60),
    "outro":     (200,  25,  60, 60),
    "unknown":   (100,  20,  35, 45),
}
SECTION_LABELS: dict[str, str] = {
    "intro": "Intro", "buildup": "Subida", "drop": "Drop",
    "breakdown": "Descanso", "outro": "Outro", "unknown": "Sección",
}
SECTION_ICONS: dict[str, str] = {
    "intro": "🎧", "buildup": "⚡", "drop": "🔥",
    "breakdown": "🌙", "outro": "🏁", "unknown": "🎵",
}

WAVEFORM_COLOR     = (255, 30, 56)         # neon crimson red
PREVIEW_WAVE_COLOR = (255, 75, 45)         # fiery flame orange-red
PLAYHEAD_COLOR     = "#ffffff"             # láser blanco puro
BOUNDARY_COLOR     = (255, 70, 95, 230)    # línea de corte carmesí brillante
START_LINE_COLOR   = (46, 213, 115, 255)   # verde esmeralda neón (inicio de corte)
END_LINE_COLOR     = (255, 71, 87, 255)    # rojo carmesí neón (fin de corte)
CUT_BORDER_COLOR   = (255, 45, 85, 200)    # borde luminoso caja de corte
MASK_BG_COLOR      = (6, 7, 10, 195)       # máscara oscura zonas fuera de previa
BG_COLOR           = (12, 13, 16)          # rack synth deep black

MAX_POINTS = 1600


# ── Loader ultrarrápido en background ──────────────────────────────────────────

class WaveformLoader(QThread):
    """Carga audio y calcula RMS en background con soundfile + numpy para máxima velocidad."""
    finished = Signal(object, float)   # (rms_array float32, duration_sec)
    error    = Signal(str)

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            from src.engine.audio_io import load_audio_file
            y, sr = load_audio_file(self.path, sr=22050, mono=True, dtype=np.float32)
            if self.isInterruptionRequested():
                return
            dur = len(y) / max(sr, 1)

            N = len(y)
            if N == 0:
                if not self.isInterruptionRequested():
                    self.finished.emit(np.zeros(100, dtype=np.float32), 0.0)
                return

            step = max(1, N // MAX_POINTS)
            trimmed = y[: (N // step) * step].reshape(-1, step)
            rms = np.sqrt(np.mean(trimmed**2, axis=1)).astype(np.float32)
            mx = float(rms.max())
            if mx > 1e-9:
                rms /= mx

            if not self.isInterruptionRequested():
                self.finished.emit(rms, float(dur))
        except Exception as e:
            if not self.isInterruptionRequested():
                self.error.emit(str(e))


# ── Widget principal ──────────────────────────────────────────────────────────

class WaveformWidget(QWidget):
    """
    Widget de forma de onda interactivo y profesional.
    Soporta visualización del track original y de la previa generada.
    """
    seek_requested     = Signal(float)  # clic en forma de onda → segundos
    boundaries_changed = Signal(list)   # límites arrastrados → [t0, t1, …]
    cuts_changed       = Signal(list)   # cortes ajustados → [(start, end), …]
    voice_drop_moved   = Signal(float)  # marcador voice drop arrastrado → segundos

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode             = "source"   # "source" o "preview"
        self._duration         = 0.0
        self._rms: Optional[np.ndarray] = None

        # Datos pista original
        self._source_rms: Optional[np.ndarray] = None
        self._source_dur       = 0.0
        self._source_sections  = []
        self._plan_segs        = []

        # Datos previa generada
        self._preview_rms: Optional[np.ndarray] = None
        self._preview_dur      = 0.0
        self._preview_segs     = []

        # Elementos gráficos de pyqtgraph
        self._regions          = []   # LinearRegionItem fondo de secciones
        self._section_lines    = []   # InfiniteLine divisores sutiles de secciones
        self._plan_highlights  = []   # LinearRegionItem cajas de corte interactivas
        self._cut_badges       = []   # TextItem títulos flotantes de los cortes
        self._omitted_masks    = []   # LinearRegionItem máscaras oscuras para zonas fuera de previa
        self._omitted_labels   = []   # TextItem etiquetas 'FUERA DE PREVIA'
        self._boundaries       = []   # InfiniteLine transiciones en vista preview
        self._boundary_times: list[float] = []
        self._voice_drop_line   = None  # InfiniteLine marcador de inicio Voice Drop (arrastrable)
        self._voice_drop_region = None  # LinearRegionItem región sombreada [t, t+dur]
        self._voice_drop_dur    = 0.0   # duración del archivo de voice drop en segundos

        self._loader           = None
        self._preview_loader   = None
        self._dragging         = False

        self._build_ui()

    # ── Construcción ──────────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if not HAS_PYQTGRAPH:
            lbl = QLabel("⚠ Instala pyqtgraph para ver la forma de onda\n    pip install pyqtgraph")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #636d83; font-size: 13px; background: #21252b; border-radius: 8px;")
            layout.addWidget(lbl)
            return

        pg.setConfigOptions(antialias=False, useOpenGL=False, background=BG_COLOR)

        # ── Barra superior de estado / badge de sección ───────────────────
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(6, 4, 6, 2)
        top_bar.setSpacing(8)

        self._badge_mode = QLabel("🎵 Pista Original")
        self._badge_mode.setStyleSheet("""
            color: #ff2542; font-size: 10px; font-weight: 800;
            background: #2a070c; border: 1px solid #ff203a66;
            border-radius: 4px; padding: 2px 7px; letter-spacing: 0.5px;
        """)
        top_bar.addWidget(self._badge_mode)

        self._lbl_sec_live = QLabel("Inicio")
        self._lbl_sec_live.setStyleSheet("""
            color: #abb2bf; font-size: 10px; font-weight: 700;
            background: transparent; border: none;
        """)
        top_bar.addWidget(self._lbl_sec_live)
        top_bar.addSpacing(6)

        self._hint_lbl = QLabel("Arrastra las líneas 🟩 verdes (inicio) y 🟥 rojas (fin) para ajustar los cortes")
        self._hint_lbl.setStyleSheet("color: #7d8799; font-size: 10px; font-weight: 600; background: transparent; border: none;")
        top_bar.addWidget(self._hint_lbl)
        top_bar.addStretch()

        btn_zoom_out = QPushButton("➖")
        btn_zoom_out.setFixedSize(22, 20)
        btn_zoom_out.setCursor(Qt.PointingHandCursor)
        btn_zoom_out.setToolTip("Alejar zoom")
        btn_zoom_out.setStyleSheet("""
            QPushButton {
                background: #181b22; color: #8c93a4; border: 1px solid #232733;
                border-radius: 4px; font-size: 10px; font-weight: 700;
            }
            QPushButton:hover { background: #2a2f3c; color: #eceef2; border-color: #ff1e38; }
        """)
        btn_zoom_out.clicked.connect(self._zoom_out_step)
        top_bar.addWidget(btn_zoom_out)

        btn_zoom_in = QPushButton("➕")
        btn_zoom_in.setFixedSize(22, 20)
        btn_zoom_in.setCursor(Qt.PointingHandCursor)
        btn_zoom_in.setToolTip("Acercar zoom")
        btn_zoom_in.setStyleSheet("""
            QPushButton {
                background: #181b22; color: #8c93a4; border: 1px solid #232733;
                border-radius: 4px; font-size: 10px; font-weight: 700;
            }
            QPushButton:hover { background: #2a2f3c; color: #eceef2; border-color: #ff1e38; }
        """)
        btn_zoom_in.clicked.connect(self._zoom_in_step)
        top_bar.addWidget(btn_zoom_in)

        self._btn_fit = QPushButton("🔍 100%")
        self._btn_fit.setFixedHeight(20)
        self._btn_fit.setCursor(Qt.PointingHandCursor)
        self._btn_fit.setToolTip("Restablecer vista a la pista completa (100%)")
        self._btn_fit.setStyleSheet("""
            QPushButton {
                background: #181b22;
                color: #8c93a4;
                border: 1px solid #232733;
                border-radius: 4px;
                font-size: 9.5px;
                font-weight: 700;
                padding: 0 6px;
            }
            QPushButton:hover {
                background: #2a2f3c;
                color: #eceef2;
                border-color: #ff1e38;
            }
        """)
        self._btn_fit.clicked.connect(self.reset_zoom)
        top_bar.addWidget(self._btn_fit)

        layout.addLayout(top_bar)

        # ── Área gráfica de waveform ───────────────────────────────────────
        self._plot = pg.PlotWidget()
        self._plot.setMinimumHeight(135)
        self._plot.showGrid(x=False, y=False)
        self._plot.hideAxis("left")
        self._plot.hideAxis("bottom")
        self._plot.setMouseEnabled(x=False, y=False)  # Forma de onda siempre fija y estable
        self._plot.setMenuEnabled(False)
        self._plot.setBackground(pg.mkBrush(color=BG_COLOR))
        self._plot.getPlotItem().setContentsMargins(0, 0, 0, 0)
        self._plot.getViewBox().setDefaultPadding(0)

        # Línea de reproducción (playhead) — capa de brillo pulsante
        self._playhead_glow_alpha = 80
        self._playhead_glow_dir   = 1
        self._playhead_glow = pg.InfiniteLine(
            pos=0, angle=90,
            pen=pg.mkPen(color=(255, 30, 56, 80), width=8, style=Qt.SolidLine),
            movable=False,
        )
        self._playhead_glow.setZValue(19)
        self._plot.addItem(self._playhead_glow)

        self._playhead_line = pg.InfiniteLine(
            pos=0, angle=90,
            pen=pg.mkPen(color=PLAYHEAD_COLOR, width=2, style=Qt.SolidLine),
            movable=False,
        )
        self._playhead_line.setZValue(20)
        self._plot.addItem(self._playhead_line)

        # Timer para el pulso del glow
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(45)
        self._glow_timer.timeout.connect(self._tick_playhead_glow)
        self._glow_timer.start()

        # Clic para seek instantáneo
        self._plot.scene().sigMouseClicked.connect(self._on_click)
        layout.addWidget(self._plot)

        # ── Leyenda de colores inline ──────────────────────────────────────
        self._legend_row = QHBoxLayout()
        self._legend_row.setContentsMargins(8, 2, 8, 2)
        self._legend_row.setSpacing(14)
        layout.addLayout(self._legend_row)

    # ── API pública ───────────────────────────────────────────────────────────

    def load_track(self, path: str):
        """Carga el audio original en background."""
        if not HAS_PYQTGRAPH:
            return
        self._clear_all()
        self._mode = "source"
        self._update_badges()
        if self._loader and self._loader.isRunning():
            try:
                self._loader.finished.disconnect()
            except RuntimeError:
                pass
            self._loader.requestInterruption()
            self._loader.wait(2000)
        self._loader = WaveformLoader(path)
        self._loader.finished.connect(self._on_source_loaded)
        self._loader.start()

    def load_preview(self, path: str, plan_segments=None):
        """Carga la previa generada en background y la muestra automáticamente."""
        if not HAS_PYQTGRAPH:
            return
        self._preview_segs = list(plan_segments or [])
        if self._preview_loader and self._preview_loader.isRunning():
            try:
                self._preview_loader.finished.disconnect()
            except RuntimeError:
                pass
            self._preview_loader.requestInterruption()
            self._preview_loader.wait(2000)
        self._preview_loader = WaveformLoader(path)
        self._preview_loader.finished.connect(self._on_preview_loaded)
        self._preview_loader.start()

    def cleanup_threads(self):
        """Detiene de forma limpia e inmediata cualquier hilo de carga de onda activo."""
        for loader_attr in ["_loader", "_preview_loader"]:
            ldr = getattr(self, loader_attr, None)
            if ldr and ldr.isRunning():
                try:
                    ldr.finished.disconnect()
                except Exception:
                    pass
                ldr.requestInterruption()
                ldr.wait(400)
                if ldr.isRunning():
                    ldr.terminate()
                    ldr.wait(200)

    def set_sections(self, sections, plan_segments=None):
        """Asigna secciones del análisis original y los segmentos del plan."""
        self._source_sections = list(sections)
        self._plan_segs       = list(plan_segments or [])
        if self._mode == "source" and self._source_rms is not None:
            # RMS ya cargado: redibujar para mostrar las regiones
            self._draw_source_view()

    def update_plan_highlights(self, plan_segments):
        """Actualiza el resaltado visual de los cortes de la previa sin mover las líneas si no es necesario."""
        self._plan_segs = list(plan_segments or [])
        if self._mode == "source":
            if len(self._plan_highlights) == len(self._plan_segs) and self._duration > 0:
                for i, (hl, seg) in enumerate(zip(self._plan_highlights, self._plan_segs)):
                    s_start = max(0.0, float(seg.source_start))
                    s_end   = min(self._duration, float(seg.source_end))
                    hl.blockSignals(True)
                    hl.setRegion((s_start, s_end))
                    hl.blockSignals(False)
                    if i < len(self._cut_badges):
                        dur = s_end - s_start
                        type_name = seg.section.type.value.lower()
                        sec_title = SECTION_LABELS.get(type_name, type_name.capitalize()).upper()
                        icon = SECTION_ICONS.get(type_name, "✂")
                        self._cut_badges[i].setPos((s_start + s_end) / 2.0, 0.80)
                        self._cut_badges[i].setHtml(
                            f"<div style='color:#ffffff; font-weight:800; font-size:9pt; "
                            f"background:#1b080b; border:1px solid #ff2542; border-radius:4px; "
                            f"padding:2px 7px; letter-spacing:0.3px;'>"
                            f"✂ CORTE {i + 1} · {icon} {sec_title} ({dur:.1f}s)</div>"
                        )
                self._update_omitted_masks_positions()
            else:
                self._draw_plan_highlights()

    def set_mode(self, mode: str):
        """Alterna entre la vista de 'source' (original) y 'preview' (previa generada)."""
        self._mode = mode
        self._update_badges()
        if mode == "source":
            self._draw_source_view()
        else:
            if self._preview_rms is not None:
                self._draw_preview_view()
            else:
                self._lbl_sec_live.setText("⏳ Cargando onda de la previa…")


    def _tick_playhead_glow(self):
        if not HAS_PYQTGRAPH:
            return
        self._playhead_glow_alpha += self._playhead_glow_dir * 6
        if self._playhead_glow_alpha >= 160:
            self._playhead_glow_alpha = 160
            self._playhead_glow_dir = -1
        elif self._playhead_glow_alpha <= 30:
            self._playhead_glow_alpha = 30
            self._playhead_glow_dir = 1
        self._playhead_glow.setPen(
            pg.mkPen(color=(255, 30, 56, self._playhead_glow_alpha),
                     width=8, style=Qt.SolidLine)
        )

    def set_playhead(self, time_sec: float):
        """Mueve el cursor de reproducción y actualiza el indicador de sección."""
        if not HAS_PYQTGRAPH or self._duration <= 0:
            return
        t = max(0.0, min(float(time_sec), self._duration))
        self._playhead_line.setValue(t)
        self._playhead_glow.setValue(t)
        self._update_current_section_badge(t)

    def get_boundary_times(self) -> list[float]:
        return list(self._boundary_times)

    def reset_zoom(self):
        """Restablece el zoom al 100% de la pista [0, duration] con tope estricto de alejamiento."""
        if not HAS_PYQTGRAPH or self._duration <= 0 or self._plot is None:
            return
        p_item = self._plot.getPlotItem()
        if p_item is not None:
            vb = p_item.getViewBox()
            if vb is not None:
                # Límites estrictos: No se puede alejar más allá de la pista ni salir de 0 o duration
                vb.setLimits(
                    xMin=0.0,
                    xMax=self._duration,
                    minXRange=min(3.0, self._duration),
                    maxXRange=self._duration,
                    yMin=-1.15,
                    yMax=1.15,
                    minYRange=2.3,
                    maxYRange=2.3,
                )
                vb.setXRange(0.0, self._duration, padding=0)
                vb.setYRange(-1.15, 1.15, padding=0)

    def _zoom_in_step(self):
        """Acerca un paso de zoom de forma controlada si el usuario lo desea."""
        if not HAS_PYQTGRAPH or self._duration <= 0 or self._plot is None:
            return
        p_item = self._plot.getPlotItem()
        if p_item is not None:
            vb = p_item.getViewBox()
            if vb is not None:
                vr = vb.viewRange()[0]
                cur_w = vr[1] - vr[0]
                new_w = max(min(5.0, self._duration), cur_w * 0.7)
                center = (vr[0] + vr[1]) / 2.0
                new_x0 = max(0.0, center - new_w / 2.0)
                new_x1 = min(self._duration, new_x0 + new_w)
                if new_x1 - new_x0 < new_w:
                    new_x0 = max(0.0, new_x1 - new_w)
                vb.setXRange(new_x0, new_x1, padding=0)

    def _zoom_out_step(self):
        """Aleja un paso de zoom de forma controlada hasta el 100% máximo."""
        if not HAS_PYQTGRAPH or self._duration <= 0 or self._plot is None:
            return
        p_item = self._plot.getPlotItem()
        if p_item is not None:
            vb = p_item.getViewBox()
            if vb is not None:
                vr = vb.viewRange()[0]
                cur_w = vr[1] - vr[0]
                new_w = min(self._duration, cur_w / 0.7)
                center = (vr[0] + vr[1]) / 2.0
                new_x0 = max(0.0, center - new_w / 2.0)
                new_x1 = min(self._duration, new_x0 + new_w)
                if new_x1 - new_x0 < new_w:
                    new_x0 = max(0.0, new_x1 - new_w)
                vb.setXRange(new_x0, new_x1, padding=0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if HAS_PYQTGRAPH and self._duration > 0 and self._plot is not None:
            p_item = self._plot.getPlotItem()
            if p_item is not None:
                vb = p_item.getViewBox()
                if vb is not None:
                    # Si el usuario estaba viendo la vista global, mantener encuadrado exacto a los bordes
                    vr = vb.viewRange()[0]
                    if vr[0] <= 0.5 and vr[1] >= self._duration - 0.5:
                        vb.setXRange(0.0, self._duration, padding=0)
                    else:
                        # Asegurar que se respeten los límites de alejamiento
                        vb.setLimits(
                            xMin=0.0,
                            xMax=self._duration,
                            minXRange=min(3.0, self._duration),
                            maxXRange=self._duration,
                            yMin=-1.15,
                            yMax=1.15,
                            minYRange=2.3,
                            maxYRange=2.3,
                        )

    def reset(self):
        self._clear_all()

    # ── Renderizado por modo ──────────────────────────────────────────────────

    def _update_badges(self):
        if self._mode == "source":
            n_cuts = len(self._plan_segs)
            self._badge_mode.setText(f"🎵 Pista Original · {n_cuts} Cortes Activos")
            self._badge_mode.setStyleSheet("""
                color: #eceef2; font-size: 10px; font-weight: 700;
                background: #181b22; border: 1px solid #2a2f3c;
                border-left: 3px solid #ff1e38;
                border-radius: 4px; padding: 2px 7px; letter-spacing: 0.5px;
            """)
            self._hint_lbl.setText("Arrastra las líneas 🟩 verdes (inicio) o 🟥 rojas (fin) para ajustar qué va a la previa")
        else:
            self._badge_mode.setText("✨ Previa Generada · Escucha Final")
            self._badge_mode.setStyleSheet("""
                color: #ff3e55; font-size: 10px; font-weight: 700;
                background: #25070a; border: 1px solid #ff1e3888;
                border-left: 3px solid #ff1e38;
                border-radius: 4px; padding: 2px 7px; letter-spacing: 0.5px;
            """)
            self._hint_lbl.setText("Previa lista · Haz clic en la onda para saltar a cualquier punto")

    def _draw_source_view(self):
        """Dibuja la onda completa original con cortes interactivos y zonas fuera de previa."""
        self._clear_all()
        if self._source_rms is None:
            return
        self._rms      = self._source_rms
        self._duration = self._source_dur

        self._draw_waveform(color=WAVEFORM_COLOR)
        self._draw_regions()
        self._draw_plan_highlights()
        self._draw_legend()
        self._playhead_line.setValue(0.0)
        self._playhead_glow.setValue(0.0)

    def _draw_preview_view(self):
        """Dibuja la onda de la previa generada con sus secciones consecutivas."""
        self._clear_all()
        if self._preview_rms is None:
            return
        self._rms      = self._preview_rms
        self._duration = self._preview_dur

        self._draw_waveform(color=PREVIEW_WAVE_COLOR)
        self._draw_preview_regions()
        self._draw_legend_preview()
        self._playhead_line.setValue(0.0)
        self._playhead_glow.setValue(0.0)

    def _draw_waveform(self, color: tuple):
        if self._rms is None or not HAS_PYQTGRAPH or self._duration <= 0:
            return
        n  = len(self._rms)
        x  = np.linspace(0, self._duration, n)
        y_pos = self._rms
        y_neg = -self._rms

        pen_w = pg.mkPen(color=(*color, 240), width=1.5)
        brush = pg.mkBrush(color=(*color, 50))

        fill = pg.FillBetweenItem(
            pg.PlotDataItem(x, y_pos, pen=pen_w),
            pg.PlotDataItem(x, y_neg, pen=pen_w),
            brush=brush,
        )
        self._plot.addItem(fill)
        self.reset_zoom()

    def _draw_regions(self):
        """Dibuja las regiones coloreadas de fondo y divisores tenues no arrastrables."""
        for r in self._regions:
            try: self._plot.removeItem(r)
            except Exception: pass
        for l in self._section_lines:
            try: self._plot.removeItem(l)
            except Exception: pass
        self._regions = []
        self._section_lines = []

        if not self._source_sections:
            return

        for sec in self._source_sections:
            type_name = sec.type.value.lower()
            rgba  = SECTION_COLORS.get(type_name, SECTION_COLORS["unknown"])
            brush = pg.mkBrush(color=rgba)
            pen   = pg.mkPen(color=(*rgba[:3], 0), width=0)

            region = pg.LinearRegionItem(
                values=(sec.start_time, sec.end_time),
                brush=brush, pen=pen, movable=False,
            )
            region.setZValue(1)
            self._plot.addItem(region)
            self._regions.append(region)

        # Divisores de sección sutiles y estáticos (no arrastrables para no confundir con cortes)
        for i in range(len(self._source_sections) - 1):
            sec = self._source_sections[i]
            t = sec.end_time
            line = pg.InfiniteLine(
                pos=t, angle=90,
                pen=pg.mkPen(color=(255, 255, 255, 20), width=1, style=Qt.DashLine),
                movable=False,
            )
            line.setZValue(2)
            self._plot.addItem(line)
            self._section_lines.append(line)

    def _draw_preview_regions(self):
        """Dibuja las regiones consecutivas de la previa ya ensamblada."""
        self._clear_regions_and_boundaries()
        if not self._preview_segs or self._duration <= 0:
            return

        # Calcular tiempo relativo acumulado de cada segmento
        t_accum = 0.0
        # Escalar duración acumulada para ajustarla a la duración real post time-stretch
        raw_total = sum(s.duration for s in self._preview_segs)
        scale = (self._duration / raw_total) if raw_total > 0 else 1.0

        prev_src_end = None
        for i, seg in enumerate(self._preview_segs):
            dur_seg = seg.duration * scale
            t_start = t_accum
            t_end   = min(self._duration, t_accum + dur_seg)
            t_accum = t_end

            # Indicador visual en la onda si hay un corte DJ con transición entre partes lejanas
            if prev_src_end is not None and abs(seg.source_start - prev_src_end) > 0.08 and t_start > 0.5:
                cut_pen = pg.mkPen(color=(255, 255, 255, 160), width=1.5, style=Qt.DashLine)
                cut_line = pg.InfiniteLine(pos=t_start, angle=90, pen=cut_pen, movable=False)
                cut_line.setZValue(8)
                lbl = pg.InfLineLabel(
                    cut_line, text="  ✂ CORTE 1s", position=0.88,
                    rotateAxis=(1, 0), anchor=(0.5, 0.5),
                )
                lbl.setColor((255, 255, 255, 200))
                self._plot.addItem(cut_line)
                self._boundaries.append(cut_line)

            prev_src_end = seg.source_end

            type_name = seg.section.type.value.lower()
            rgba  = SECTION_COLORS.get(type_name, SECTION_COLORS["unknown"])
            brush = pg.mkBrush(color=(*rgba[:3], 65))
            pen   = pg.mkPen(color=(*rgba[:3], 180), width=1)

            region = pg.LinearRegionItem(
                values=(t_start, t_end),
                brush=brush, pen=pen, movable=False,
            )
            region.setZValue(1)
            self._plot.addItem(region)
            self._regions.append(region)

    def _draw_plan_highlights(self):
        """Dibuja los cortes interactivos resaltados y las zonas oscurecidas fuera de previa."""
        if not HAS_PYQTGRAPH:
            return

        # Limpiar cortes, badges y máscaras anteriores
        for item_list in [self._plan_highlights, self._cut_badges, self._omitted_masks, self._omitted_labels]:
            for item in item_list:
                try: self._plot.removeItem(item)
                except Exception: pass
            item_list.clear()

        if not self._plan_segs or self._duration <= 0:
            return

        # 1. ZONAS DE CORTE ACTIVAS (INCLUIDAS EN LA PREVIA)
        for i, seg in enumerate(self._plan_segs):
            s_start = max(0.0, float(seg.source_start))
            s_end   = min(self._duration, float(seg.source_end))
            dur     = s_end - s_start

            type_name = seg.section.type.value.lower()
            rgba = SECTION_COLORS.get(type_name, (255, 30, 56))

            # Región interactiva del corte (cuerpo luminoso)
            pen_border = pg.mkPen(color=CUT_BORDER_COLOR, width=1.5, style=Qt.SolidLine)
            hl = pg.LinearRegionItem(
                values=(s_start, s_end),
                brush=pg.mkBrush(color=(*rgba[:3], 45)),
                pen=pen_border,
                movable=True,
                hoverBrush=pg.mkBrush(color=(*rgba[:3], 70)),
            )
            hl.setZValue(6)
            hl.setCursor(Qt.OpenHandCursor)
            hl.setToolTip(f"✂ Corte {i + 1} ({dur:.1f}s) — Arrastra el bloque para desplazarlo")

            # Línea de INICIO (Verde esmeralda neón arrastrable)
            line_s = hl.lines[0]
            line_s.setPen(pg.mkPen(color=START_LINE_COLOR, width=2.5))
            line_s.setHoverPen(pg.mkPen(color=(255, 255, 255, 255), width=3.5))
            line_s.setCursor(Qt.SizeHorCursor)
            line_s.setToolTip(f"Inicio Corte {i + 1} ({s_start:.1f}s) — Arrastra horizontalmente")
            lbl_s = pg.InfLineLabel(
                line_s, text=" INICIO ", position=0.92,
                anchor=(1.0, 0.5),
            )
            lbl_s.setColor(START_LINE_COLOR[:3])

            # Línea de FIN (Rojo carmesí neón arrastrable)
            line_e = hl.lines[1]
            line_e.setPen(pg.mkPen(color=END_LINE_COLOR, width=2.5))
            line_e.setHoverPen(pg.mkPen(color=(255, 255, 255, 255), width=3.5))
            line_e.setCursor(Qt.SizeHorCursor)
            line_e.setToolTip(f"Fin Corte {i + 1} ({s_end:.1f}s) — Arrastra horizontalmente")
            lbl_e = pg.InfLineLabel(
                line_e, text=" FIN ", position=0.92,
                anchor=(0.0, 0.5),
            )
            lbl_e.setColor(END_LINE_COLOR[:3])

            # Badge superior del corte (diseño limpio tipo DAW)
            center_x = (s_start + s_end) / 2.0
            badge = pg.TextItem(
                html=(
                    f"<div style='color:#ffffff; font-weight:700; font-size:8.5pt; "
                    f"background:rgba(18, 20, 26, 0.90); border:1px solid #ff2542; "
                    f"border-radius:10px; padding:1px 8px; letter-spacing:0.2px;'>"
                    f"✂ Corte {i + 1} · {dur:.1f}s</div>"
                ),
                anchor=(0.5, 0),
            )
            badge.setPos(center_x, 0.86)
            badge.setZValue(7)

            # Conectar señales interactivas de arrastre
            hl.sigRegionChanged.connect(lambda it=hl, idx=i: self._on_cut_region_changing(it, idx))
            hl.sigRegionChangeFinished.connect(self._on_cut_region_changed)

            self._plot.addItem(hl)
            self._plot.addItem(badge)
            self._plan_highlights.append(hl)
            self._cut_badges.append(badge)

        # 2. ZONAS FUERA DE PREVIA (OMITIDAS / NO INCLUIDAS)
        self._draw_omitted_masks()

    def _draw_omitted_masks(self):
        """Crea las máscaras oscuras para las zonas fuera de la previa (sin textos molestos)."""
        for item in self._omitted_masks:
            try: self._plot.removeItem(item)
            except Exception: pass
        for item in self._omitted_labels:
            try: self._plot.removeItem(item)
            except Exception: pass
        self._omitted_masks.clear()
        self._omitted_labels.clear()

        if not self._plan_highlights or self._duration <= 0:
            return

        intervals = []
        for hl in self._plan_highlights:
            r0, r1 = hl.getRegion()
            intervals.append((max(0.0, min(r0, r1)), min(self._duration, max(r0, r1))))
        intervals.sort(key=lambda x: x[0])

        omitted = []
        cur = 0.0
        for s, e in intervals:
            if s > cur + 0.3:
                omitted.append((cur, s))
            cur = max(cur, e)
        if cur < self._duration - 0.3:
            omitted.append((cur, self._duration))

        mask_brush = pg.mkBrush(color=MASK_BG_COLOR)
        mask_pen   = pg.mkPen(color=(0, 0, 0, 0), width=0)

        for t0, t1 in omitted:
            mask = pg.LinearRegionItem(values=(t0, t1), brush=mask_brush, pen=mask_pen, movable=False)
            mask.setZValue(3)
            self._plot.addItem(mask)
            self._omitted_masks.append(mask)

    def _update_omitted_masks_positions(self):
        """Actualiza en caliente las posiciones de las máscaras oscuras durante el arrastre."""
        if not self._plan_highlights or self._duration <= 0:
            return

        intervals = []
        for hl in self._plan_highlights:
            r0, r1 = hl.getRegion()
            intervals.append((max(0.0, min(r0, r1)), min(self._duration, max(r0, r1))))
        intervals.sort(key=lambda x: x[0])

        omitted = []
        cur = 0.0
        for s, e in intervals:
            if s > cur + 0.3:
                omitted.append((cur, s))
            cur = max(cur, e)
        if cur < self._duration - 0.3:
            omitted.append((cur, self._duration))

        # Si el número de intervalos coincide con las máscaras existentes, actualizar regiones en vivo
        if len(omitted) == len(self._omitted_masks):
            for mask, (t0, t1) in zip(self._omitted_masks, omitted):
                mask.setRegion((t0, t1))
        else:
            self._draw_omitted_masks()

    def _on_cut_region_changing(self, item: pg.LinearRegionItem, idx: int):
        self._dragging = True
        r0, r1 = item.getRegion()
        start = max(0.0, min(r0, r1))
        end   = min(self._duration, max(r0, r1))
        dur   = end - start

        # Actualizar posición y duración del badge flotante del corte
        if idx < len(self._cut_badges):
            badge = self._cut_badges[idx]
            badge.setPos((start + end) / 2.0, 0.86)
            badge.setHtml(
                f"<div style='color:#ffffff; font-weight:700; font-size:8.5pt; "
                f"background:rgba(18, 20, 26, 0.90); border:1px solid #ff2542; "
                f"border-radius:10px; padding:1px 8px; letter-spacing:0.2px;'>"
                f"✂ Corte {idx + 1} · {dur:.1f}s</div>"
            )

        # Actualizar texto explicativo en la barra superior
        self._hint_lbl.setText(
            f"✂️ Editando Corte {idx + 1}: {start:.1f}s – {end:.1f}s (duración: {dur:.1f}s)"
        )

        # Actualizar máscaras de zonas omitidas en vivo
        self._update_omitted_masks_positions()

    def _on_cut_region_changed(self):
        if not self._plan_highlights or self._duration <= 0:
            QTimer.singleShot(80, lambda: setattr(self, "_dragging", False))
            return
        cuts = []
        for hl in self._plan_highlights:
            r0, r1 = hl.getRegion()
            start = max(0.0, min(r0, r1))
            end   = min(self._duration, max(r0, r1))
            # Ajustar límites si es necesario
            if abs(start - r0) > 0.05 or abs(end - r1) > 0.05:
                hl.blockSignals(True)
                hl.setRegion((start, end))
                hl.blockSignals(False)
            cuts.append((start, end))

        self._hint_lbl.setText("Arrastra las líneas 🟩 verdes (inicio) y 🟥 rojas (fin) para ajustar los cortes")
        self.cuts_changed.emit(cuts)
        QTimer.singleShot(80, lambda: setattr(self, "_dragging", False))

    def _draw_boundaries(self):
        """Líneas divisorias mantenidas para compatibilidad."""
        pass

    def _draw_legend(self):
        """Leyenda gráfica limpia y compacta."""
        self._clear_legend()

        lbl_cut_start = QLabel("🟩 Inicio")
        lbl_cut_start.setStyleSheet("color: #2ed573; font-size: 10px; font-weight: 700; background: transparent;")
        lbl_cut_start.setToolTip("Línea verde: inicio del corte (arrastra para ajustar)")
        self._legend_row.addWidget(lbl_cut_start)

        lbl_cut_end = QLabel("🟥 Fin")
        lbl_cut_end.setStyleSheet("color: #ff4757; font-size: 10px; font-weight: 700; background: transparent;")
        lbl_cut_end.setToolTip("Línea roja: fin del corte (arrastra para ajustar)")
        self._legend_row.addWidget(lbl_cut_end)

        lbl_in = QLabel("✨ En previa")
        lbl_in.setStyleSheet("color: #abb2bf; font-size: 10px; font-weight: 600; background: transparent;")
        lbl_in.setToolTip("Zonas iluminadas: se incluirán en el archivo de previa")
        self._legend_row.addWidget(lbl_in)

        lbl_out = QLabel("⬛ Descartado")
        lbl_out.setStyleSheet("color: #5c6370; font-size: 10px; font-weight: 600; background: transparent;")
        lbl_out.setToolTip("Zonas oscurecidas: quedan fuera de la previa")
        self._legend_row.addWidget(lbl_out)

        sep = QLabel("│")
        sep.setStyleSheet("color: #2b303c; font-size: 10px;")
        self._legend_row.addWidget(sep)

        # Chips de secciones musicales
        seen = set()
        for sec in self._source_sections:
            t = sec.type.value.lower()
            if t not in seen:
                seen.add(t)
                self._add_legend_item(t)
        self._legend_row.addStretch()

    def _draw_legend_preview(self):
        """Leyenda de colores para la vista de previa."""
        self._clear_legend()
        seen = set()
        for seg in self._preview_segs:
            t = seg.section.type.value.lower()
            if t not in seen:
                seen.add(t)
                self._add_legend_item(t)
        self._legend_row.addStretch()

    def _clear_legend(self):
        while self._legend_row.count():
            item = self._legend_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_legend_item(self, t: str):
        rgba  = SECTION_COLORS.get(t, SECTION_COLORS["unknown"])
        hex_c = "#{:02x}{:02x}{:02x}".format(*rgba[:3])
        text  = SECTION_LABELS.get(t, t.capitalize())
        icon  = SECTION_ICONS.get(t, "•")
        lbl   = QLabel(f"{icon} {text}")
        lbl.setStyleSheet(f"""
            color: {hex_c}; font-size: 11px; font-weight: 700;
            background: transparent; border: none; letter-spacing: 0.3px;
        """)
        self._legend_row.addWidget(lbl)

    # ── Actualización de badge en tiempo real ─────────────────────────────────

    def _update_current_section_badge(self, t: float):
        sec_name = "Reproduciendo"
        sec_icon = "▶"
        sec_color = "#abb2bf"

        if self._mode == "source" and self._source_sections:
            for i, sec in enumerate(self._source_sections):
                if sec.start_time <= t <= sec.end_time:
                    t_val = sec.type.value.lower()
                    sec_name = SECTION_LABELS.get(t_val, t_val.capitalize())
                    sec_icon = SECTION_ICONS.get(t_val, "📍")
                    rgba = SECTION_COLORS.get(t_val, (171, 178, 191))
                    sec_color = "#{:02x}{:02x}{:02x}".format(*rgba[:3])
                    break
        elif self._mode == "preview" and self._preview_segs and self._duration > 0:
            raw_total = sum(s.duration for s in self._preview_segs)
            scale = (self._duration / raw_total) if raw_total > 0 else 1.0
            accum = 0.0
            for seg in self._preview_segs:
                d = seg.duration * scale
                if accum <= t <= accum + d + 0.1:
                    t_val = seg.section.type.value.lower()
                    sec_name = SECTION_LABELS.get(t_val, t_val.capitalize())
                    sec_icon = SECTION_ICONS.get(t_val, "🔥")
                    rgba = SECTION_COLORS.get(t_val, (152, 195, 121))
                    sec_color = "#{:02x}{:02x}{:02x}".format(*rgba[:3])
                    break
                accum += d

        self._lbl_sec_live.setText(f"{sec_icon} {(sec_name or '').upper()} · {t:.1f}s")
        if sec_color != getattr(self, "_last_sec_color", None):
            self._lbl_sec_live.setStyleSheet(f"""
                color: {sec_color}; font-size: 10px; font-weight: 800;
                background: transparent; border: none; letter-spacing: 0.5px;
            """)
            self._last_sec_color = sec_color

    # ── Callbacks de eventos y carga ──────────────────────────────────────────

    def _on_source_loaded(self, rms: np.ndarray, duration: float):
        self._source_rms = rms
        self._source_dur = duration
        if self._mode == "source":
            # Diferir el dibujado un tick para garantizar que el widget
            # ya está visible y tiene geometría real antes de llamar a reset_zoom()
            QTimer.singleShot(80, self._draw_source_view)

    def _on_preview_loaded(self, rms: np.ndarray, duration: float):
        self._preview_rms = rms
        self._preview_dur = duration
        self._mode = "preview"
        self._update_badges()
        self._draw_preview_view()
        # Redibujar en el siguiente ciclo de eventos para garantizar geometría perfecta del viewport
        QTimer.singleShot(60, self._draw_preview_view)


    def _on_click(self, event):
        """Seek al hacer clic directo en cualquier punto de la onda, o restablecer zoom al 100% con doble clic."""
        if self._duration <= 0 or self._dragging:
            return
        if hasattr(event, "double") and event.double():
            self.reset_zoom()
            return
        pos = event.scenePos()
        p_item = self._plot.getPlotItem() if self._plot is not None else None
        if p_item is not None:
            vb = p_item.getViewBox()
            if vb is not None:
                mp = vb.mapSceneToView(pos)
                t = float(mp.x())
                t = max(0.0, min(t, self._duration))
                self.seek_requested.emit(t)

    def _on_boundary_drag_started(self):
        self._dragging = True

    def _on_boundary_moved(self, line: pg.InfiniteLine, idx: int):
        val = line.value()
        t = float(val[0]) if isinstance(val, (list, tuple)) else float(val)
        min_t = self._boundary_times[idx - 1] + 0.5 if idx > 0 else 0.5
        max_t = self._boundary_times[idx + 1] - 0.5 if idx < len(self._boundary_times) - 1 else (self._duration - 0.5)
        t = max(min_t, min(max_t, t))
        line.setValue(t)
        self._boundary_times[idx] = t

        if idx < len(self._regions):
            self._regions[idx].setRegion((
                self._boundary_times[idx - 1] if idx > 0 else 0.0,
                t
            ))
        if idx + 1 < len(self._regions):
            self._regions[idx + 1].setRegion((
                t,
                self._boundary_times[idx + 1] if idx + 1 < len(self._boundary_times) else self._duration
            ))

    def _on_boundary_released(self):
        self._dragging = False
        self.boundaries_changed.emit(list(self._boundary_times))

    def set_voice_drop_marker(self, t: float | None, dur: float = 0.0):
        """
        Muestra/actualiza el marcador de posición Voice Drop en la waveform.
        - Línea dorada discontinua arrastrable en el punto de inicio.
        - Región sombreada [t, t+dur] si se conoce la duración del archivo.
        t=None/t<0 lo oculta. Emite voice_drop_moved(t) al soltar el arrastre.
        """
        if not HAS_PYQTGRAPH:
            return

        # Limpiar marcadores anteriores
        for _item in (self._voice_drop_region, self._voice_drop_line):
            if _item is not None:
                try:
                    self._plot.removeItem(_item)
                except Exception:
                    pass
        self._voice_drop_line   = None
        self._voice_drop_region = None

        if t is None or t < 0:
            return

        self._voice_drop_dur = max(0.0, float(dur))

        from PySide6.QtCore import Qt as _Qt

        # Región sombreada dorada [t, t+dur] (solo visual, no arrastrable)
        if self._voice_drop_dur > 0.05:
            self._voice_drop_region = pg.LinearRegionItem(
                values=(t, t + self._voice_drop_dur),
                brush=pg.mkBrush(255, 215, 0, 40),
                pen=pg.mkPen(color="#FFD700", width=1),
                movable=False,
            )
            self._plot.addItem(self._voice_drop_region)

        # Línea arrastrable en el inicio
        pen = pg.mkPen(color="#FFD700", width=2, style=_Qt.DashLine)
        label_text = f"🎙 Voice Drop{f'  ({self._voice_drop_dur:.1f}s)' if self._voice_drop_dur > 0.05 else ''}"
        self._voice_drop_line = pg.InfiniteLine(
            pos=t, angle=90, pen=pen, movable=True,
            label=label_text,
            labelOpts={"position": 0.92, "color": "#FFD700",
                       "fill": pg.mkBrush(0, 0, 0, 150), "movable": True},
        )

        # Al arrastrar: mover también la región sombreada
        def _on_drag_finished(ln):
            new_t = float(ln.value())
            if self._voice_drop_region is not None:
                self._voice_drop_region.setRegion((new_t, new_t + self._voice_drop_dur))
            self.voice_drop_moved.emit(new_t)

        self._voice_drop_line.sigPositionChangeFinished.connect(_on_drag_finished)
        self._plot.addItem(self._voice_drop_line)

    def _clear_all(self):
        if not HAS_PYQTGRAPH:
            return
        # Guardar posición y duración del marcador voice drop antes de limpiar
        _vd_t:   float | None = None
        _vd_dur: float        = self._voice_drop_dur
        if self._voice_drop_line is not None:
            try:
                _vd_t = float(self._voice_drop_line.value())
            except Exception:
                pass

        self._plot.clear()
        self._regions         = []
        self._plan_highlights = []
        self._boundaries      = []
        self._boundary_times  = []
        self._section_lines   = []
        self._cut_badges      = []
        self._omitted_masks   = []
        self._omitted_labels  = []
        self._voice_drop_line   = None
        self._voice_drop_region = None
        self._plot.addItem(self._playhead_line)

        # Restaurar marcador voice drop si había uno
        if _vd_t is not None:
            self.set_voice_drop_marker(_vd_t, dur=_vd_dur)

    def _clear_regions_and_boundaries(self):
        for r in self._regions:
            try:
                self._plot.removeItem(r)
            except Exception:
                pass
        for h in self._plan_highlights:
            try:
                self._plot.removeItem(h)
            except Exception:
                pass
        for b in self._boundaries:
            try:
                self._plot.removeItem(b)
            except Exception:
                pass
        for sl in self._section_lines:
            try:
                self._plot.removeItem(sl)
            except Exception:
                pass
        for cb in self._cut_badges:
            try:
                self._plot.removeItem(cb)
            except Exception:
                pass
        for om in self._omitted_masks:
            try:
                self._plot.removeItem(om)
            except Exception:
                pass
        for ol in self._omitted_labels:
            try:
                self._plot.removeItem(ol)
            except Exception:
                pass
        self._regions         = []
        self._plan_highlights = []
        self._boundaries      = []
        self._section_lines   = []
        self._cut_badges      = []
        self._omitted_masks   = []
        self._omitted_labels  = []
