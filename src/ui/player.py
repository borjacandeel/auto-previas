"""
AutoPrevias — Reproductor integrado de alta precisión (Fase C) — v3 pulido.

Características:
- Selector de modo: Pista original vs Previa generada con cambio instantáneo.
- Barra de seek táctil e instantánea (clic directo en cualquier punto para saltar).
- Sincronización bidireccional con el playhead de la forma de onda.
- Detección de estado ultra-robusta (compatible con macOS AVFoundation y Windows Media Foundation).
- Controles completos: Play/Pause (Space), Stop, -10s, +10s, Volumen con control de mute.
- Etiquetas de tiempo y estado con diseño premium dark glassmorphism.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal, QUrl, QTimer
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider,
)

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    HAS_MEDIA = True
except ImportError:
    HAS_MEDIA = False

# ── Paleta estética Rack Synth ────────────────────────────────────────────────
_BG2      = "#121419"
_BG3      = "#181b22"
_BG4      = "#21252f"
_BG5      = "#2a2f3c"
_ACCENT   = "#ff1e38"
_ACCENT2  = "#ff3e55"
_GREEN    = "#27c98a"
_RED      = "#ff1e38"
_WARN     = "#ff7b2b"
_TEXT     = "#e2e5eb"
_TEXT_DIM = "#505563"
_BORDER   = "#272b36"


def _fmt(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


class StereoVUMeter(QWidget):
    """
    Medidor estéreo de nivel VU / Peak estilo hardware rack synth.
    Muestra dos canales independientes (L y R) con 14 segmentos LED discretos:
    - 8 verdes (-36 dB a -12 dB)
    - 4 ámbar (-12 dB a -3 dB)
    - 2 rojo carmesí (-3 dB a 0 dB / Peak Clip)
    Incluye indicador Peak-Hold ultra-rápido y caída analógica suave.
    """
    NUM_SEGS = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(116, 24)
        self.setToolTip("Medidor de nivel estéreo VU / Peak (L / R en dBFS)")

        self._lvl_l = 0.0
        self._lvl_r = 0.0
        self._peak_l = 0.0
        self._peak_r = 0.0
        self._peak_hold_l = 0
        self._peak_hold_r = 0

        # Precalcular colores lit (encendido) y dim (apagado)
        self._colors_lit = []
        self._colors_dim = []
        for i in range(self.NUM_SEGS):
            if i < 8:
                self._colors_lit.append(QColor("#27c98a"))
                self._colors_dim.append(QColor("#0d2419"))
            elif i < 12:
                self._colors_lit.append(QColor("#ff9020"))
                self._colors_dim.append(QColor("#2a1805"))
            else:
                self._colors_lit.append(QColor("#ff1e38"))
                self._colors_dim.append(QColor("#2b060a"))

    def set_levels(self, l_amp: float, r_amp: float):
        """Actualiza los niveles de audio en tiempo real con ataque instantáneo."""
        self._lvl_l = max(l_amp, self._lvl_l * 0.72)
        self._lvl_r = max(r_amp, self._lvl_r * 0.72)

        seg_l = self._amp_to_seg(self._lvl_l)
        seg_r = self._amp_to_seg(self._lvl_r)

        # Peak hold L
        if seg_l >= self._peak_l:
            self._peak_l = float(seg_l)
            self._peak_hold_l = 15  # ~500ms
        else:
            if self._peak_hold_l > 0:
                self._peak_hold_l -= 1
            else:
                self._peak_l = max(0.0, self._peak_l - 0.5)

        # Peak hold R
        if seg_r >= self._peak_r:
            self._peak_r = float(seg_r)
            self._peak_hold_r = 15
        else:
            if self._peak_hold_r > 0:
                self._peak_hold_r -= 1
            else:
                self._peak_r = max(0.0, self._peak_r - 0.5)

        self.update()

    def decay_step(self) -> bool:
        """Decae suavemente hacia 0 cuando se pausa o detiene. Devuelve True si aún hay actividad."""
        self._lvl_l *= 0.62
        self._lvl_r *= 0.62
        self._peak_l = max(0.0, self._peak_l - 0.8)
        self._peak_r = max(0.0, self._peak_r - 0.8)
        self.update()
        return self._lvl_l > 0.005 or self._lvl_r > 0.005 or self._peak_l > 0.1 or self._peak_r > 0.1

    def reset(self):
        """Restablece los medidores a cero."""
        self._lvl_l = 0.0
        self._lvl_r = 0.0
        self._peak_l = 0.0
        self._peak_r = 0.0
        self._peak_hold_l = 0
        self._peak_hold_r = 0
        self.update()

    def _amp_to_seg(self, amp: float) -> int:
        if amp <= 0.001:
            return 0
        db = 20.0 * np.log10(max(1e-4, amp))
        # Escala: -36 dB (seg 0) a 0 dB (seg 14)
        norm = (db + 36.0) / 36.0
        return int(np.clip(norm * self.NUM_SEGS, 0, self.NUM_SEGS))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        w = self.width()
        h = self.height()

        # Marco del chasis del medidor
        painter.fillRect(0, 0, w, h, QColor("#101217"))
        painter.setPen(QColor("#232733"))
        painter.drawRect(0, 0, w - 1, h - 1)

        # Labels "L" y "R"
        font = QFont("Helvetica", 7, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#8c93a4"))
        painter.drawText(3, 9, "L")
        painter.drawText(3, 20, "R")

        seg_x_start = 14
        seg_w = 6.0
        seg_gap = 1.2
        bar_h = 7

        segs_active_l = self._amp_to_seg(self._lvl_l)
        segs_active_r = self._amp_to_seg(self._lvl_r)
        peak_idx_l = int(self._peak_l)
        peak_idx_r = int(self._peak_r)

        for i in range(self.NUM_SEGS):
            x = int(seg_x_start + i * (seg_w + seg_gap))

            # Canal L (fila superior y=3)
            is_lit_l = (i < segs_active_l) or (i == peak_idx_l and peak_idx_l > 0)
            color_l = self._colors_lit[i] if is_lit_l else self._colors_dim[i]
            painter.fillRect(x, 3, int(seg_w), bar_h, color_l)

            # Canal R (fila inferior y=13)
            is_lit_r = (i < segs_active_r) or (i == peak_idx_r and peak_idx_r > 0)
            color_r = self._colors_lit[i] if is_lit_r else self._colors_dim[i]
            painter.fillRect(x, 13, int(seg_w), bar_h, color_r)

        painter.end()


class ClickableSlider(QSlider):
    """QSlider con salto directo al hacer clic en cualquier parte de la barra."""
    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            w = self.width()
            if w > 0:
                pos = ev.position().x()
                pct = max(0.0, min(1.0, pos / w))
                val = self.minimum() + int(pct * (self.maximum() - self.minimum()))
                self.setValue(val)
                self.sliderMoved.emit(val)
        super().mousePressEvent(ev)


class PlayerWidget(QWidget):
    """
    Reproductor de audio integrado con PySide6.QtMultimedia.

    Señales:
        position_changed(float)  — posición actual en segundos (para el playhead)
        track_switched(str)      — path del track activo ("original" vs "preview")
    """
    position_changed = Signal(float)
    track_switched   = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_path  = ""
        self._preview_path = ""
        self._current_path = ""
        self._seeking      = False
        self._ready        = False
        self._dur_ms       = 0
        self._autoplay     = False

        # Datos para el medidor VU estéreo
        self._vu_cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self._vu_peaks_L: np.ndarray | None = None
        self._vu_peaks_R: np.ndarray | None = None
        self._vu_fps: float = 50.0

        self._build_ui()
        self._setup_player()

    # ── Construcción UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # ── Fila superior: Selector de pista (Original / Previa) + Estado ───
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        # Pills de selección de pista
        self._btn_mode_source = QPushButton("🎵 Pista Original")
        self._btn_mode_source.setFixedHeight(24)
        self._btn_mode_source.setCursor(Qt.PointingHandCursor)
        self._btn_mode_source.setToolTip("Escuchar la canción completa original")
        self._btn_mode_source.clicked.connect(self._switch_to_source)

        self._btn_mode_preview = QPushButton("✨ Previa Generada")
        self._btn_mode_preview.setFixedHeight(24)
        self._btn_mode_preview.setCursor(Qt.PointingHandCursor)
        self._btn_mode_preview.setEnabled(False)
        self._btn_mode_preview.setToolTip("Escuchar la previa recortada con sus transiciones y cambios de BPM")
        self._btn_mode_preview.clicked.connect(self._switch_to_preview)

        self._update_mode_buttons_style(is_source=True)

        top_row.addWidget(self._btn_mode_source)
        top_row.addWidget(self._btn_mode_preview)
        top_row.addStretch()

        self._lbl_status = QLabel("Sin archivo cargado")
        self._lbl_status.setStyleSheet(
            f"color: {_TEXT_DIM}; font-size: 10px; font-weight: 500; background: transparent; border: none;"
        )
        top_row.addWidget(self._lbl_status)
        root.addLayout(top_row)

        # ── Barra de seek táctil ───────────────────────────────────────────
        self._slider = ClickableSlider(Qt.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(0)
        self._slider.setEnabled(False)
        self._slider.setFixedHeight(16)
        self._slider.setCursor(Qt.PointingHandCursor)
        self._slider.setToolTip("Haz clic en cualquier punto para saltar a ese segundo")
        self._slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {_BG3};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {_ACCENT}, stop:1 {_ACCENT2});
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: white;
                width: 10px;
                height: 10px;
                border-radius: 5px;
                margin: -3px 0;
                border: 2px solid {_ACCENT};
            }}
            QSlider::handle:horizontal:hover {{
                background: {_ACCENT};
                border-color: white;
            }}
            QSlider::handle:horizontal:disabled {{
                background: {_BG4};
                border-color: {_BG4};
            }}
        """)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._slider.sliderMoved.connect(self._on_slider_moved)
        root.addWidget(self._slider)

        # ── Fila de controles principales ─────────────────────────────────
        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(0, 0, 0, 0)
        ctrl_row.setSpacing(6)

        # Tiempo actual / total — LED digital rojo estilo sintetizador
        self._lbl_time = QLabel("0:00 / 0:00")
        self._lbl_time.setFixedWidth(86)
        self._lbl_time.setStyleSheet(
            "color: #ff203a; font-size: 11px; font-weight: 800; font-family: 'Menlo', 'Consolas', monospace;"
            "background: #190507; border: 1px solid #ff203a44; border-radius: 4px; padding: 1px 4px;"
        )
        ctrl_row.addWidget(self._lbl_time)

        # Medidor estéreo VU estilo hardware rack
        self._vu_meter = StereoVUMeter(self)
        ctrl_row.addWidget(self._vu_meter)

        ctrl_row.addStretch()

        # Botón ◀◀ (-10s / Flecha Izquierda: -5s)
        self._btn_rew = self._mk_btn("◀◀", _BG3, _TEXT, w=30)
        self._btn_rew.setToolTip("Retroceder 10s (Flecha Izquierda: -5s)")
        self._btn_rew.clicked.connect(self._rewind)
        ctrl_row.addWidget(self._btn_rew)

        # Botón STOP ⏹ (Escape)
        self._btn_stop = self._mk_btn("⏹", _BG3, _TEXT, w=30)
        self._btn_stop.setToolTip("Detener (Escape)")
        self._btn_stop.clicked.connect(self.stop)
        ctrl_row.addWidget(self._btn_stop)

        # Botón PLAY/PAUSE ▶ (Barra espaciadora) — destacado
        self._btn_play = QPushButton("▶")
        self._btn_play.setFixedSize(46, 28)
        self._btn_play.setCursor(Qt.PointingHandCursor)
        self._btn_play.setToolTip("Reproducir / Pausar (Barra espaciadora)")
        self._btn_play.setEnabled(False)
        self._btn_play.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {_ACCENT}, stop:1 #b30018);
                color: white;
                border: 1px solid #ff5268;
                border-radius: 7px;
                font-size: 13px;
                font-weight: 800;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #ff3b52, stop:1 #cc001c);
                border-color: white;
            }}
            QPushButton:pressed {{
                background: #8f0013;
            }}
            QPushButton:disabled {{
                background: {_BG4};
                color: {_TEXT_DIM};
                border-color: transparent;
            }}
        """)
        self._btn_play.clicked.connect(self.toggle_play)
        ctrl_row.addWidget(self._btn_play)

        # Botón ▶▶ (+10s / Flecha Derecha: +5s)
        self._btn_fwd = self._mk_btn("▶▶", _BG3, _TEXT, w=30)
        self._btn_fwd.setToolTip("Avanzar 10s (Flecha Derecha: +5s)")
        self._btn_fwd.clicked.connect(self._forward)
        ctrl_row.addWidget(self._btn_fwd)

        ctrl_row.addStretch()

        # Volumen
        vol_box = QHBoxLayout()
        vol_box.setSpacing(5)
        self._btn_mute = QPushButton("🔊")
        self._btn_mute.setFixedSize(22, 22)
        self._btn_mute.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        self._btn_mute.setCursor(Qt.PointingHandCursor)
        self._btn_mute.clicked.connect(self._toggle_mute)
        vol_box.addWidget(self._btn_mute)

        self._vol_slider = QSlider(Qt.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(90)
        self._vol_slider.setFixedWidth(60)
        self._vol_slider.setFixedHeight(12)
        self._vol_slider.setToolTip("Volumen")
        self._vol_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {_BG3};
                height: 3px;
                border-radius: 1.5px;
            }}
            QSlider::sub-page:horizontal {{
                background: {_TEXT};
                height: 3px;
                border-radius: 1.5px;
            }}
            QSlider::handle:horizontal {{
                background: white;
                width: 9px; height: 9px;
                border-radius: 4.5px;
                margin: -3px 0;
            }}
        """)
        self._vol_slider.valueChanged.connect(self._on_volume_changed)
        vol_box.addWidget(self._vol_slider)
        ctrl_row.addLayout(vol_box)

        root.addLayout(ctrl_row)

        if not HAS_MEDIA:
            warn = QLabel("⚠ PySide6.QtMultimedia no está disponible en este entorno.")
            warn.setAlignment(Qt.AlignCenter)
            warn.setStyleSheet(f"color: {_WARN}; font-size: 10px; background: transparent; border: none;")
            root.addWidget(warn)

    def _mk_btn(self, text: str, bg: str, fg: str, w: int = 30) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(w, 26)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1px solid {_BORDER};
                border-radius: 5px;
                font-size: 10px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {_BG5};
                border-color: {_ACCENT}44;
            }}
            QPushButton:disabled {{
                background: {_BG3};
                color: {_TEXT_DIM};
                border-color: transparent;
            }}
        """)
        return btn

    def _update_mode_buttons_style(self, is_source: bool):
        if is_source:
            self._btn_mode_source.setStyleSheet(f"""
                QPushButton {{
                    background: {_ACCENT}25;
                    color: {_ACCENT};
                    border: 1px solid {_ACCENT}66;
                    border-radius: 5px;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 0 8px;
                }}
            """)
            self._btn_mode_preview.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {_TEXT_DIM};
                    border: 1px solid transparent;
                    border-radius: 5px;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 0 8px;
                }}
                QPushButton:hover {{
                    color: {_TEXT};
                    border-color: {_BORDER};
                }}
            """)
        else:
            self._btn_mode_source.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {_TEXT_DIM};
                    border: 1px solid transparent;
                    border-radius: 5px;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 0 8px;
                }}
                QPushButton:hover {{
                    color: {_TEXT};
                    border-color: {_BORDER};
                }}
            """)
            self._btn_mode_preview.setStyleSheet(f"""
                QPushButton {{
                    background: {_GREEN}25;
                    color: {_GREEN};
                    border: 1px solid {_GREEN}66;
                    border-radius: 5px;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 0 8px;
                }}
            """)

    # ── Setup QMediaPlayer ────────────────────────────────────────────────────

    def _setup_player(self):
        if not HAS_MEDIA:
            return

        # Asegurar que Qt descubra los plugins multimedia en bundles standalone
        try:
            from PySide6.QtCore import QCoreApplication
            import sys
            base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent.parent
            for p_dir in [
                base / "PySide6" / "qt-plugins",
                base / "PySide6" / "plugins",
                base / "qt-plugins",
                base / "plugins",
            ]:
                if p_dir.is_dir() and str(p_dir) not in QCoreApplication.libraryPaths():
                    QCoreApplication.addLibraryPath(str(p_dir))
        except Exception:
            pass

        self._audio_out = QAudioOutput(self)
        self._audio_out.setVolume(self._vol_slider.value() / 100.0)

        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_out)

        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.playbackStateChanged.connect(self._on_state)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_error)

        # Timer de refresco para el medidor VU (30 FPS)
        self._vu_timer = QTimer(self)
        self._vu_timer.setInterval(33)
        self._vu_timer.timeout.connect(self._on_vu_tick)

    # ── Gestión de pistas ─────────────────────────────────────────────────────

    def set_source_track(self, path: str, autoplay: bool = False):
        """Asigna y carga el track original subido por el usuario."""
        self._source_path = path
        self._btn_mode_source.setEnabled(True)
        self._switch_to_source(autoplay=autoplay)

    def set_preview_track(self, path: str, autoplay: bool = True):
        """Asigna la previa generada y cambia la reproducción a ella."""
        self._preview_path = path
        self._btn_mode_preview.setEnabled(True)
        self._switch_to_preview(autoplay=autoplay)

    def _switch_to_source(self, autoplay: bool = False):
        if not self._source_path:
            return
        self._update_mode_buttons_style(is_source=True)
        self.load_file(self._source_path, autoplay=autoplay)
        self.track_switched.emit("source")

    def _switch_to_preview(self, autoplay: bool = False):
        if not self._preview_path:
            return
        self._update_mode_buttons_style(is_source=False)
        self.load_file(self._preview_path, autoplay=autoplay)
        self.track_switched.emit("preview")

    def load_file(self, path: str, autoplay: bool = False):
        """Carga un archivo en QMediaPlayer."""
        if not HAS_MEDIA:
            return
        resolved = Path(path).resolve()
        if not resolved.exists():
            self._set_status(f"❌ Archivo no encontrado: {resolved.name}", _RED)
            return

        from src.engine.audio_io import repair_wav_header_if_needed
        repair_wav_header_if_needed(str(resolved))

        self._current_path = str(resolved)
        self._ready        = False
        self._dur_ms       = 0
        self._autoplay     = autoplay

        # Obtener duración inmediata mediante SoundFile para no depender únicamente del buffer de Qt
        try:
            import soundfile as sf
            info = sf.info(str(resolved))
            if info.duration > 0:
                self._dur_ms = int(info.duration * 1000)
                self._lbl_time.setText(f"0:00 / {_fmt(self._dur_ms)}")
                self._ready = True
        except Exception:
            self._lbl_time.setText("0:00 / 0:00")

        self._btn_play.setEnabled(True)
        self._slider.setEnabled(True)
        self._slider.setValue(0)
        self._set_status("Cargando…", _TEXT_DIM)

        self._get_or_load_vu(str(resolved))

        self._player.stop()
        self._player.setSource(QUrl.fromLocalFile(str(resolved)))

    # ── Controles de reproducción ─────────────────────────────────────────────

    def toggle_play(self):
        """Alterna play/pause. Si estaba al final, recomienza desde 0."""
        if not HAS_MEDIA or not self._current_path:
            return

        # Si llegó al final, volver al inicio
        if self._dur_ms > 0 and self._player.position() >= self._dur_ms:
            self._player.setPosition(0)

        state = self._player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def stop(self):
        """Detiene y vuelve al inicio."""
        if not HAS_MEDIA:
            return
        self._player.stop()
        self._slider.setValue(0)
        self._lbl_time.setText(f"0:00 / {_fmt(self._dur_ms)}")
        self._vu_meter.reset()
        self.position_changed.emit(0.0)

    def seek(self, time_sec: float):
        """Seek solicitado externamente (por ejemplo al hacer clic en la waveform)."""
        if not HAS_MEDIA:
            return
        ms = int(time_sec * 1000)
        if self._dur_ms > 0:
            ms = max(0, min(ms, self._dur_ms))
        self._player.setPosition(ms)
        if self._dur_ms > 0:
            self._slider.blockSignals(True)
            self._slider.setValue(int(ms * 1000 / self._dur_ms))
            self._slider.blockSignals(False)
            self._lbl_time.setText(f"{_fmt(ms)} / {_fmt(self._dur_ms)}")
        self.position_changed.emit(ms / 1000.0)

    def is_playing(self) -> bool:
        if not HAS_MEDIA:
            return False
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def is_playing_source(self) -> bool:
        return self._current_path == self._source_path

    # ── Callbacks de eventos ──────────────────────────────────────────────────

    def _on_position(self, ms: int):
        if self._seeking:
            return
        if self._dur_ms <= 0 and self._player.duration() > 0:
            self._dur_ms = self._player.duration()
            self._ready  = True
            self._btn_play.setEnabled(True)
            self._slider.setEnabled(True)

        if self._dur_ms > 0:
            pct = max(0, min(1000, int(ms * 1000 / self._dur_ms)))
            self._slider.blockSignals(True)
            self._slider.setValue(pct)
            self._slider.blockSignals(False)
            t_str = f"{_fmt(ms)} / {_fmt(self._dur_ms)}"
            if getattr(self, "_last_time_str", None) != t_str:
                self._last_time_str = t_str
                self._lbl_time.setText(t_str)

        # Emitir siempre para que la waveform sincronice el playhead en ambos modos
        self.position_changed.emit(ms / 1000.0)

    def _on_duration(self, ms: int):
        if ms > 0:
            self._dur_ms = ms
            self._ready  = True
            self._btn_play.setEnabled(True)
            self._slider.setEnabled(True)
            self._lbl_time.setText(f"0:00 / {_fmt(ms)}")
            if self._lbl_status.text() == "Cargando…":
                tag = "🎵 Pista original lista" if self.is_playing_source() else "✨ Previa lista"
                self._set_status(f"✅ {tag}", _GREEN)

    def _on_state(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._btn_play.setText("⏸")
            tag = "Pista original" if self.is_playing_source() else "Previa"
            self._set_status(f"▶ Reproduciendo ({tag})", _GREEN)
            self._vu_timer.start()
        else:
            self._btn_play.setText("▶")
            if state == QMediaPlayer.PlaybackState.PausedState:
                self._set_status("⏸ Pausado", _TEXT_DIM)
            elif self._ready:
                self._set_status("⏹ Detenido", _TEXT_DIM)

    def _on_vu_tick(self):
        if not HAS_MEDIA:
            return
        is_playing = (self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        if is_playing:
            pos_s = self._player.position() / 1000.0
            idx = int(pos_s * self._vu_fps)
            if self._vu_peaks_L is not None and 0 <= idx < len(self._vu_peaks_L):
                vl = float(self._vu_peaks_L[idx])
                vr = float(self._vu_peaks_R[idx])
            else:
                vl, vr = 0.0, 0.0
            self._vu_meter.set_levels(vl, vr)
        else:
            still = self._vu_meter.decay_step()
            if not still:
                self._vu_timer.stop()

    def _get_or_load_vu(self, path: str):
        if path in self._vu_cache:
            self._vu_peaks_L, self._vu_peaks_R = self._vu_cache[path]
            return
        self._build_vu_profile(path)
        if self._vu_peaks_L is not None and self._vu_peaks_R is not None:
            self._vu_cache[path] = (self._vu_peaks_L, self._vu_peaks_R)

    def _build_vu_profile(self, path: str):
        try:
            from src.engine.audio_io import load_audio_file
            y, sr = load_audio_file(path, sr=22050, mono=False, dtype=np.float32)
            if y.ndim == 1:
                y = np.stack([y, y])
            hop = int(sr / self._vu_fps)
            n_frames = y.shape[1] // max(1, hop)
            if n_frames > 0:
                y_l = y[0, :n_frames * hop].reshape(n_frames, hop)
                y_r = y[1, :n_frames * hop].reshape(n_frames, hop)
                self._vu_peaks_L = np.max(np.abs(y_l), axis=1)
                self._vu_peaks_R = np.max(np.abs(y_r), axis=1)
            else:
                self._vu_peaks_L = None
                self._vu_peaks_R = None
        except Exception:
            self._vu_peaks_L = None
            self._vu_peaks_R = None

    def _on_media_status(self, status):
        MS = QMediaPlayer.MediaStatus
        if status in (MS.LoadedMedia, MS.BufferedMedia):
            self._ready = True
            self._btn_play.setEnabled(True)
            self._slider.setEnabled(True)
            if self._autoplay:
                self._autoplay = False
                self._player.play()
            else:
                tag = "Pista original lista" if self.is_playing_source() else "Previa lista"
                self._set_status(f"✅ {tag}", _GREEN)
        elif status == MS.LoadingMedia:
            self._set_status("Cargando…", _TEXT_DIM)
        elif status == MS.InvalidMedia:
            self._ready = False
            self._set_status("❌ Formato no compatible", _RED)
        elif status == MS.EndOfMedia:
            self._set_status("⏹ Fin", _TEXT_DIM)
            self._slider.setValue(1000)

    def _on_error(self, error, error_string: str):
        if error_string:
            self._set_status(f"❌ {error_string}", _RED)

    def _on_slider_pressed(self):
        self._seeking = True

    def _on_slider_released(self):
        self._seeking = False
        if not HAS_MEDIA or self._dur_ms <= 0:
            return
        ms = int(self._slider.value() * self._dur_ms / 1000)
        self._player.setPosition(ms)
        self.position_changed.emit(ms / 1000.0)

    def _on_slider_moved(self, value: int):
        if self._dur_ms > 0:
            ms = int(value * self._dur_ms / 1000)
            self._lbl_time.setText(f"{_fmt(ms)} / {_fmt(self._dur_ms)}")

    def _on_volume_changed(self, value: int):
        if HAS_MEDIA:
            self._audio_out.setVolume(value / 100.0)
            if value == 0:
                self._btn_mute.setText("🔇")
            else:
                self._btn_mute.setText("🔊")

    def toggle_mute(self):
        if not HAS_MEDIA:
            return
        is_muted = self._audio_out.isMuted()
        self._audio_out.setMuted(not is_muted)
        self._btn_mute.setText("🔇" if not is_muted else "🔊")

    def _toggle_mute(self):
        self.toggle_mute()

    def rewind(self, sec: float = 10.0):
        """Retrocede un número de segundos en la reproducción."""
        if HAS_MEDIA and self._ready:
            pos = max(0, self._player.position() - int(sec * 1000))
            self._player.setPosition(pos)
            self.position_changed.emit(pos / 1000.0)

    def forward(self, sec: float = 10.0):
        """Avanza un número de segundos en la reproducción."""
        if HAS_MEDIA and self._ready:
            pos = min(self._dur_ms, self._player.position() + int(sec * 1000))
            self._player.setPosition(pos)
            self.position_changed.emit(pos / 1000.0)

    def _rewind(self):
        self.rewind(10.0)

    def _forward(self):
        self.forward(10.0)

    def get_position_seconds(self) -> float:
        """Devuelve la posición actual de reproducción en segundos."""
        if HAS_MEDIA and self._ready:
            return self._player.position() / 1000.0
        return 0.0

    def _set_status(self, msg: str, color: str = _TEXT_DIM):
        self._lbl_status.setText(msg)
        self._lbl_status.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 600; background: transparent; border: none;"
        )
