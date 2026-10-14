"""
AutoPrevias — Recorrido de bienvenida (tutorial interactivo de primer uso).

· Solo se ofrece la primera vez (instalación nueva): `should_offer_onboarding()` + `maybe_start_onboarding()`.
· El usuario elige «Hacer el recorrido» u «Omitir» y no se vuelve a preguntar (`onboarding_done`).
· El recorrido oscurece la ventana y resalta, paso a paso, cada parte de la app real. Para enseñar el panel
  de resultados carga una pista de ejemplo sintética (no se guarda nada en Recientes ni en disco al terminar).
· Atajos: → / Intro / Espacio = siguiente · ← = atrás · Esc = salir.
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import (QEasingCurve, QEvent, QObject, QPoint, QRect, QRectF, Qt, QTimer, QVariantAnimation, Signal)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from src.i18n import tr

# Paleta (la misma que la app; se repite aquí para no importar src.ui.app y evitar importaciones circulares)
BG, BG2, BG3, BG4 = "#0a0b0e", "#121419", "#181b22", "#21252f"
ACCENT, ACCENT2 = "#ff1e38", "#ff3e55"
TEXT, TEXT_MID, TEXT_DIM = "#eceef2", "#8c93a4", "#555b6a"
GOLD = "#ffd21f"
BORDER = "#232733"

DEMO_NAME = "Midnight Groove (Demo).wav"


# ───────────────────────────── ofrecer el recorrido solo una vez ─────────────────────────────

def should_offer_onboarding(cfg: dict) -> bool:
    """True solo en una instalación nueva: nunca se ha decidido y no hay historial de uso."""
    if cfg.get("onboarding_done"):
        return False
    if cfg.get("recent_files"):
        return False                      # quien ya usaba la app antes de esta función no necesita bienvenida
    return True


def mark_onboarding_done(cfg: Optional[dict] = None) -> None:
    try:
        from src.config import load, save
        c = load()
        c["onboarding_done"] = True
        save(c)
        if cfg is not None:
            cfg["onboarding_done"] = True
    except Exception:
        pass


# ───────────────────────────── pista de ejemplo ─────────────────────────────

def make_demo_track(path: Path, sec: int = 120, bpm: int = 128, sr: int = 44100) -> Path:
    """Pista sintética con estructura (intro, subida, drop, descanso, drop, outro) a 128 BPM."""
    import numpy as np
    import soundfile as sf
    rng = np.random.default_rng(7)
    t = np.linspace(0, sec, int(sr * sec), endpoint=False)
    beat = 60.0 / bpm
    k_ = sec / 150.0
    secs = [(a * k_, b * k_, kick, bass, hats, pad) for (a, b, kick, bass, hats, pad) in
            [(0, 20, .5, 0, .0, .10), (20, 40, .6, .0, .3, .16), (40, 80, 1.0, .5, .6, .14),
             (80, 100, 0, 0, .15, .30), (100, 130, 1.0, .5, .6, .14), (130, 150, .5, 0, .2, .08)]]
    y = np.zeros_like(t)
    for idx, (a, b, kick, bass, hats, pad) in enumerate(secs):
        m = (t >= a) & (t < b)
        env = np.ones(m.sum())
        if idx == 1:                                  # subida progresiva
            env = np.linspace(.4, 1.3, m.sum())
        y[m] += pad * env * (np.sin(2 * np.pi * 220 * t[m]) + .6 * np.sin(2 * np.pi * 330 * t[m]))
        if bass:
            y[m] += bass * .45 * np.sin(2 * np.pi * 55 * t[m]) * (0.6 + 0.4 * np.sin(2 * np.pi * (bpm / 60) * t[m]))
    for k in range(int(sec / beat)):
        tk0 = k * beat
        sk = next((s_ for s_ in secs if s_[0] <= tk0 < s_[1]), secs[-1])
        i = int(tk0 * sr)
        n = int(0.12 * sr)
        if i + n >= len(y):
            break
        tk = np.linspace(0, 0.12, n)
        if sk[2]:
            y[i:i + n] += sk[2] * 0.7 * np.sin(2 * np.pi * (60 + 90 * np.exp(-tk * 40)) * tk) * np.exp(-tk * 22)
        if sk[4] and k % 2 == 1:
            y[i:i + n] += sk[4] * 0.25 * rng.standard_normal(n) * np.exp(-tk * 55)
    y /= max(1e-9, float(np.abs(y).max())) / 0.9
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.stack([y, y * 0.97], 1), sr, subtype="PCM_16")
    return path


# ───────────────────────────── pasos ─────────────────────────────

@dataclass
class Step:
    key: str
    title: str
    text: str
    target: Optional[Callable[[], object]] = None      # widget, lista de widgets o None (tarjeta centrada)
    page: int = 0                                      # página del stack donde se ve (0 inicio · 2 resultados)
    before: Optional[Callable[[], None]] = None        # prepara la app al entrar (abrir paneles…)
    after: Optional[Callable[[], None]] = None         # deshace al salir
    demo_trigger: bool = False                         # «Siguiente» carga la pista de ejemplo
    optional: bool = False                             # se salta si el objetivo no está visible (edición Básica)
    example: str = ""                                  # cuadro amarillo con un ejemplo / consejo
    hole_pad: int = 6


def _vis(*ws):
    return [w for w in ws if w is not None and w.isVisible()]


def build_steps(win) -> list:
    """Lista completa de pasos del recorrido, adaptada a la edición (Basic / Plus)."""
    from src.config import get_edition
    plus = get_edition() == "plus"
    R = win._results
    S: list[Step] = []

    def add(*a, **k):
        S.append(Step(*a, **k))

    # ── Pantalla de inicio ────────────────────────────────────────────────────────────────
    add("bienvenida", "¡Bienvenido a AutoPrevias!",
        "En unos 5 minutos te enseño toda la app, desde cargar un tema hasta exportar la previa con su vídeo. "
        "Puedes salir cuando quieras con «Omitir» o la tecla Esc. Todo lo que verás es la app real.", None)
    add("cargar", "1 · Carga tu tema",
        "Arrastra aquí un archivo de audio (WAV, MP3, FLAC, AIFF, M4A, OGG…) o pulsa «Abrir archivo». "
        "También puedes soltarlo en cualquier parte de la ventana.",
        lambda: win._drop_zone._card, example="Ejemplo: tu máster «Midnight Groove (Original Mix).wav».")
    add("recientes", "Recientes",
        "Guarda tus últimas previas y temas abiertos. Con un clic vuelves a cargarlos y, si quieres, "
        "«Reabrir proyecto» restaura los mismos ajustes y la misma semilla.", lambda: win._btn_recents)
    if plus:
        add("lote", "Modo Lote (Plus)",
            "Procesa muchas pistas de una vez: las añades a la lista, eliges ajustes y AutoPrevias genera todas las previas sola.",
            lambda: win._btn_batch_hdr, example="Ejemplo: 20 temas del EP → 20 previas mientras tomas un café.")
        add("vigilar", "Vigilar carpeta (Plus)",
            "Elige una carpeta y cada tema nuevo que caiga en ella se convierte en previa automáticamente.",
            lambda: win._btn_watch)
    add("licencia", "Licencia, idioma y actualizaciones",
        "Aquí ves tu versión y tu licencia (1 equipo por clave), cambias el idioma, buscas actualizaciones y ajustas el "
        "rendimiento del equipo. La licencia se revalida sola: no tienes que volver a escribirla.", lambda: win._btn_license)
    add("idioma", "Idioma ES / EN",
        "Cambia entre castellano e inglés en caliente, sin reiniciar. Se recuerda para la próxima vez.", lambda: win._btn_lang)
    add("edicion", "Tu edición: " + ("PLUS" if plus else "BÁSICA"),
        ("Plus incluye WAV 24 bit, FLAC, vídeo sin marca de agua con todas las opciones, lote, presets, modo promo y firma."
         if plus else
         "Básica genera MP3 y vídeo animado con marca de agua. Las funciones de Plus aparecerán marcadas con un candado."),
        lambda: win._edition_badge)
    add("estado", "Barra de estado",
        "Abajo ves siempre qué está pasando: análisis, progreso de la exportación y el resultado (BPM, tonalidad y drops).",
        lambda: [win._progress_label, win._progress_bar])
    add("demo", "Vamos a verlo en acción",
        "Voy a cargar una pista de ejemplo (sintética, no se guarda nada) para enseñarte el panel de resultados real. "
        "Pulsa «Siguiente»: el análisis tarda unos segundos.", None, demo_trigger=True)

    # ── Panel de resultados (con la pista de ejemplo) ─────────────────────────────────────────
    wave_frame = getattr(R, "_waveform", None)
    add("onda", "La forma de onda",
        "Aquí ves la estructura del tema: intro, subida, drop, descanso… AutoPrevias la detecta sola. "
        "Haz clic para escuchar desde ese punto y arrastra los marcadores para retocar dónde se corta.",
        (lambda: wave_frame.parentWidget()) if wave_frame is not None else None, page=2)
    player = getattr(R, "_player", None)
    if player is not None:
        add("reproductor", "Reproductor",
            "Escucha la pista original y la previa generada, y cambia de una a otra al instante. "
            "Barra espaciadora = reproducir/pausar · flechas = saltar 5 s · Esc = detener.",
            lambda: player.parentWidget(), page=2)
    add("tarjetas", "Lo que AutoPrevias ha medido",
        "Archivo, BPM, tonalidad (en Camelot, para mezclar en armonía), duración, número de drops y duración estimada de la previa. "
        "Si el BPM no es correcto, haz doble clic en la tarjeta BPM y corrígelo.",
        lambda: [R._card_file, R._card_bpm, R._card_key, R._card_dur, R._card_drops, R._card_pv], page=2)
    add("duracion", "Duración de la previa",
        "Elige 15 s (teaser), 30 s (promo), 60 s (extendida) o 120 s (club). Los cortes se recalculan al instante "
        "y siempre caen en compás.", lambda: [R._btn_p15, R._btn_p30, R._btn_p60, R._btn_p120], page=2,
        example="Para TikTok o Reels usa 15 o 30 s; para mandar al promotor, 120 s.")
    if plus:
        add("presets", "Mis presets (Plus)",
            "Guarda tu firma, formatos y estilo de vídeo con un nombre y vuélvelos a aplicar con un clic. "
            "Los presets son archivos: puedes copiarlos a otro ordenador.", lambda: R._preset_bar, page=2)
    add("simple", "Estructura de previa optimizada",
        "AutoPrevias ya ha calculado 3 cortes con transiciones suaves. Para la mayoría de temas basta con pulsar Generar.",
        lambda: win._results._simple_box, page=2)
    if plus:
        add("avanzado", "Personalizar cortes y BPM (Plus)",
            "Activa esta casilla para abrir tres pestañas: el editor de cortes (inicio, fin y duración exactos), la variación "
            "de BPM (acelera ligeramente la previa para que nadie pueda mezclarla con tu tema) y la estructura musical con nivel LUFS.",
            lambda: [R._chk_advanced, R._tabs], page=2,
            before=lambda: R._chk_advanced.setChecked(True), after=lambda: R._chk_advanced.setChecked(False))
    add("formatos", "① Nombre y formatos",
        "El nombre del archivo ya viene puesto («PREVIA - tu tema»), pero puedes cambiarlo. "
        + ("Marca los formatos que quieres: WAV 24 bit, MP3 320k y FLAC." if plus else
           "Se exporta MP3 320k (con vídeo siempre se genera también el MP3)."),
        lambda: _vis(R._edit_name, R._chk_wav, R._chk_mp3, R._chk_flac), page=2,
        example="Usa WAV para el promotor, MP3 para las redes y FLAC si quieres calidad sin pérdidas.")
    add("video", "② Vídeo animado",
        "Marca esta casilla y aparece la tarjeta del vídeo: AutoPrevias crea un vídeo animado que late con la música, "
        "listo para TikTok, Reels y YouTube. Todo el vídeo se configura en esa tarjeta.", lambda: R._chk_video, page=2,
        before=lambda: R._chk_video.setChecked(True))
    add("formato_video", "Formato del vídeo",
        "9:16 vertical (TikTok, Reels, Shorts), 1:1 cuadrado (feed de Instagram) o 16:9 horizontal (YouTube). "
        "Elige el que vayas a publicar.", lambda: list(R._aspect_btns.values()), page=2)
    add("paleta", "Estilo y colores",
        ("Elige la paleta de colores y, con «Look», cinco aspectos listos para usar: Neón clásico, foto + barras, "
         "foto + círculo, foto y título o solo la foto." if plus else
         "Elige la paleta de colores de la plantilla Neón: Radical, Rave, Carmesí, Ámbar o Cyber."),
        lambda: _vis(R._combo_video_pal, R._combo_look), page=2)
    if plus:
        add("titulo", "Título y banner (Plus)",
            "El título es lo que sale en el vídeo (si lo dejas vacío usa el nombre de la pista) y el banner es tu frase "
            "de sello encima del vídeo.", lambda: [R._edit_vtitle, R._edit_promo], page=2,
            example="Título: MIDNIGHT GROOVE · Banner: RADICAL RECORDS · PROMO EXCLUSIVA")
        add("personalizar", "Personalizar el vídeo (Plus)",
            "Aquí eliges todo: tu imagen de fondo para cada formato, la onda de sonido (barras, línea o círculo, su posición y color), "
            "qué textos salen y dónde, y el final del vídeo. Tiene vista previa en vivo.", lambda: R._btn_vcustom, page=2)
        add("imagen", "Tu propia imagen de fondo",
            "Arrastra una foto sobre la tarjeta para usarla de fondo. Debe ser 9:16, 1:1 o 16:9: si no lo es, la app te avisa y te "
            "enseña ejemplos de formatos válidos.", lambda: R._lbl_vdrop, page=2)
    add("final", "Final del vídeo",
        ("Elige cómo acaba: firma AutoPrevias, fundido a negro, sin cierre o tu propia imagen con texto." if plus else
         "Elige cómo acaba: firma «Generado por AutoPrevias» o fundido a negro. La marca de agua pequeña se quita con Plus."),
        lambda: _vis(R._combo_vend, R._lbl_vbasic, R._btn_vlock), page=2)
    add("vista_previa", "Vista previa del vídeo",
        "Antes de generar, mira un fragmento real del vídeo con tus ajustes. Si no te convence, cámbialo y vuelve a verlo.",
        lambda: R._btn_vprev, page=2)
    if plus:
        add("efectos", "③ Efectos de estudio (Plus)",
            "Flanger y Filter Sweep añaden transiciones antes de cada drop; Master LUFS deja la previa al volumen estándar "
            "de las plataformas.", lambda: R._adv_fx_widget, page=2,
            before=lambda: R._set_adv_open(True))
        add("voice_drop", "Voice Drop (Plus)",
            "Añade tu firma de voz o jingle («Radical Records…») justo antes del drop o al empezar la previa.",
            lambda: [R._btn_voice_drop, R._combo_voice_pos], page=2,
            before=lambda: R._set_adv_open(True))
        add("modo_promo", "Modo promo antifugas (Plus)",
            "Para que nadie pueda aprovechar tu previa: la exporta en MP3 128 kbps y repite tu firma de voz cada pocos "
            "segundos, así no sirve para mezclarla ni para subirla a otras plataformas.", lambda: R._row_promo_widget, page=2,
            before=lambda: R._set_adv_open(True))
        add("firma", "Firma, carátula y datos (Plus)",
            "Tu nombre de artista, sello, género y carátula se incrustan en los archivos y se usan en el vídeo.",
            lambda: R._branding_card, page=2,
            before=lambda: R._set_adv_open(True))
    add("carpeta", "Carpeta de destino",
        "Por defecto las previas se guardan en Música/Previas. Cambia la carpeta con «Cambiar» y ábrela con «Abrir».",
        lambda: [R._lbl_folder_path, R._btn_folder, R._btn_open_folder], page=2)
    add("resumen", "Resumen antes de generar",
        "Un vistazo a lo que se va a crear (formatos, vídeo, duración y carpeta) para que no haya sorpresas.",
        lambda: R._lbl_summary, page=2)
    add("generar", "▶ Generar previa",
        "Pulsa aquí y AutoPrevias hace el resto: corta, mezcla, aplica efectos, exporta los archivos y crea el vídeo. "
        "Al terminar aparece una tarjeta con «Abrir carpeta».", lambda: R._btn_generate, page=2)
    add("semilla", "Semilla y regenerar",
        "Cada previa usa una semilla; con la misma semilla y los mismos ajustes obtienes siempre el mismo resultado. "
        "El dado 🎲 prueba otra variante.", lambda: [R._spin_seed, R._btn_random_seed, R._btn_regen], page=2,
        optional=True)
    add("nuevo", "Nuevo track",
        "Cuando termines, pulsa «Nuevo track» para volver al inicio y cargar otro tema.",
        lambda: R._btn_new_track_top, page=2)
    add("fin", "¡Listo! Ya sabes usar AutoPrevias",
        "Arrastra tu primer tema y genera tu previa. Si necesitas ayuda, escribe a radicalrecordsvlc@gmail.com. "
        "Mucha suerte con tus lanzamientos · Radical Records.", None)
    return S


# ───────────────────────────── capa visual ─────────────────────────────

def _btn_css(primary: bool) -> str:
    if primary:
        return (f"QPushButton {{ background: {ACCENT}; color: #fff; border: none; border-radius: 8px; padding: 8px 18px;"
                "font-size: 13px; font-weight: 800; }"
                f"QPushButton:hover {{ background: {ACCENT2}; }}"
                f"QPushButton:disabled {{ background: {BG4}; color: {TEXT_DIM}; }}")
    return (f"QPushButton {{ background: {BG4}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 14px;"
            "font-size: 12px; font-weight: 700; }"
            f"QPushButton:hover {{ border-color: {ACCENT}; }}"
            f"QPushButton:disabled {{ color: {TEXT_DIM}; }}")


class TourOverlay(QWidget):
    """Capa a pantalla completa: oscurece la ventana, deja un «agujero» resaltado y muestra la tarjeta del paso."""
    next_clicked = Signal()
    back_clicked = Signal()
    skip_clicked = Signal()
    resized = Signal()

    CARD_W = 420

    def __init__(self, win):
        super().__init__(win)
        self._win = win
        self._hole = QRectF()
        self._hole_anim = QVariantAnimation(self)
        self._hole_anim.setDuration(320)
        self._hole_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._hole_anim.valueChanged.connect(self._on_hole)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.ArrowCursor)
        self.setGeometry(win.rect())

        card = QFrame(self)
        card.setObjectName("tour-card")
        card.setFixedWidth(self.CARD_W)
        card.setStyleSheet(f"QFrame#tour-card {{ background: {BG2}; border: 2px solid {ACCENT}; border-radius: 14px; }}"
                           "QLabel { background: transparent; border: none; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(8)
        top = QHBoxLayout()
        self._lbl_step = QLabel("")
        self._lbl_step.setStyleSheet(f"color: {GOLD}; font-size: 10.5px; font-weight: 900; letter-spacing: 1.5px;")
        top.addWidget(self._lbl_step)
        top.addStretch()
        lay.addLayout(top)
        self._lbl_title = QLabel("")
        self._lbl_title.setWordWrap(True)
        self._lbl_title.setStyleSheet(f"color: {TEXT}; font-size: 18px; font-weight: 900;")
        lay.addWidget(self._lbl_title)
        self._lbl_text = QLabel("")
        self._lbl_text.setWordWrap(True)
        self._lbl_text.setTextFormat(Qt.PlainText)
        self._lbl_text.setStyleSheet(f"color: {TEXT_MID}; font-size: 13px; line-height: 140%;")
        lay.addWidget(self._lbl_text)
        self._lbl_ex = QLabel("")
        self._lbl_ex.setWordWrap(True)
        self._lbl_ex.setStyleSheet(f"color: #ffe58a; font-size: 12.5px; font-weight: 700; background: rgba(255,210,31,.09);"
                                   f"border-left: 4px solid {GOLD}; padding: 7px 10px; border-radius: 4px;")
        lay.addWidget(self._lbl_ex)
        self._bar = QFrame()
        self._bar.setFixedHeight(4)
        self._bar.setStyleSheet(f"background: {BG4}; border-radius: 2px;")
        self._fill = QFrame(self._bar)
        self._fill.setStyleSheet(f"background: {ACCENT}; border-radius: 2px;")
        lay.addWidget(self._bar)
        row = QHBoxLayout()
        row.setSpacing(8)
        self._btn_skip = QPushButton(tr("Omitir recorrido"))
        self._btn_skip.setCursor(Qt.PointingHandCursor)
        self._btn_skip.setStyleSheet(f"QPushButton {{ background: transparent; color: {TEXT_DIM}; border: none; font-size: 11.5px;"
                                     f"font-weight: 700; padding: 6px 2px; }} QPushButton:hover {{ color: {TEXT}; }}")
        self._btn_skip.clicked.connect(self.skip_clicked)
        self._btn_back = QPushButton(tr("← Atrás"))
        self._btn_back.setCursor(Qt.PointingHandCursor)
        self._btn_back.setStyleSheet(_btn_css(False))
        self._btn_back.clicked.connect(self.back_clicked)
        self._btn_next = QPushButton(tr("Siguiente →"))
        self._btn_next.setCursor(Qt.PointingHandCursor)
        self._btn_next.setStyleSheet(_btn_css(True))
        self._btn_next.clicked.connect(self.next_clicked)
        row.addWidget(self._btn_skip)
        row.addStretch()
        row.addWidget(self._btn_back)
        row.addWidget(self._btn_next)
        lay.addLayout(row)
        self._card = card
        self.show_step_idx = (0, 1)
        win.installEventFilter(self)

    # — datos del paso —
    def set_content(self, idx: int, total: int, title: str, text: str, example: str, last: bool, first: bool, busy: bool = False):
        self.show_step_idx = (idx, total)
        self._lbl_step.setText(tr("PASO {n} DE {t}", n=idx + 1, t=total))
        self._lbl_title.setText(tr(title))
        self._lbl_text.setText(tr(text))
        self._lbl_ex.setText(tr(example) if example else "")
        self._lbl_ex.setVisible(bool(example))
        self._btn_back.setVisible(not first)
        self._btn_back.setEnabled(not busy)
        self._btn_next.setEnabled(not busy)
        self._btn_skip.setVisible(not last)
        self._btn_next.setText(tr("¡Terminar!") if last else tr("Siguiente →"))
        self._fill.setGeometry(0, 0, int(self._bar.width() * (idx + 1) / max(1, total)) or 4, 4)
        self._card.adjustSize()
        QTimer.singleShot(0, self._refill)

    def _refill(self):
        idx, total = self.show_step_idx
        self._fill.setGeometry(0, 0, max(4, int(self._bar.width() * (idx + 1) / max(1, total))), 4)

    # — agujero y tarjeta —
    def go_to(self, rect: Optional[QRect], animate: bool = True):
        """Mueve el resaltado a `rect` (coordenadas de la ventana; None = sin resaltar) y recoloca la tarjeta."""
        target = QRectF(rect) if rect is not None and not rect.isNull() else QRectF()
        self._hole_anim.stop()
        if animate and not self._hole.isNull() and not target.isNull():
            self._hole_anim.setStartValue(self._hole)
            self._hole_anim.setEndValue(target)
            self._hole_anim.start()
        else:
            self._hole = target
            self.update()
        self._place_card(target)

    def _on_hole(self, v):
        self._hole = QRectF(v)
        self.update()

    def _place_card(self, hole: QRectF):
        self._card.adjustSize()
        cw, ch = self._card.width(), self._card.height()
        W, H = self.width(), self.height()
        gap = 18
        if hole.isNull():
            self._card.move(int((W - cw) / 2), int((H - ch) / 2))
            return
        spots = [
            (hole.center().x() - cw / 2, hole.bottom() + gap),     # debajo
            (hole.center().x() - cw / 2, hole.top() - ch - gap),   # encima
            (hole.right() + gap, hole.center().y() - ch / 2),      # a la derecha
            (hole.left() - cw - gap, hole.center().y() - ch / 2),  # a la izquierda
        ]
        for x, y in spots:
            x = min(max(12, x), W - cw - 12)
            if 12 <= y and y + ch <= H - 12:
                self._card.move(int(x), int(y))
                return
        # no cabe sin tapar: esquina con más sitio
        x = W - cw - 16 if hole.center().x() < W / 2 else 16
        y = H - ch - 16 if hole.center().y() < H / 2 else 16
        self._card.move(int(x), int(y))

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRect(QRectF(self.rect()))
        if not self._hole.isNull():
            hole = QPainterPath()
            hole.addRoundedRect(self._hole, 10, 10)
            path = path.subtracted(hole)
        p.fillPath(path, QColor(3, 4, 8, 196))
        if not self._hole.isNull():
            for w, a in ((9, 40), (5, 90), (2.5, 255)):
                pen = QPen(QColor(255, 30, 56, a))
                pen.setWidthF(w)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(self._hole, 10, 10)
        p.end()

    def eventFilter(self, obj, ev):
        if obj is self._win and ev.type() == QEvent.Resize:
            self.setGeometry(self._win.rect())
            self.resized.emit()
        return False

    def mousePressEvent(self, ev):                    # la capa bloquea los clics sobre la app
        ev.accept()

    def keyPressEvent(self, ev):
        k = ev.key()
        if k in (Qt.Key_Right, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if self._btn_next.isEnabled():
                self.next_clicked.emit()
        elif k == Qt.Key_Left:
            if self._btn_back.isVisible() and self._btn_back.isEnabled():
                self.back_clicked.emit()
        elif k == Qt.Key_Escape:
            self.skip_clicked.emit()
        else:
            ev.ignore()


def _remove_demo_file(path, tries: int = 12):
    """Borra la pista de ejemplo; si Windows aún la tiene abierta, reintenta unos segundos (liberación asíncrona)."""
    if not path:
        return
    try:
        if path.exists():
            path.unlink()
        return
    except Exception:
        pass
    if tries > 0:
        QTimer.singleShot(500, lambda: _remove_demo_file(path, tries - 1))


class OnboardingTour(QObject):
    """Orquesta el recorrido: pasos, carga/limpieza de la pista de ejemplo y restauración de la app."""
    finished = Signal(bool)         # True = completado, False = omitido

    DEMO_TIMEOUT = 150.0

    def __init__(self, win):
        super().__init__(win)
        self._win = win
        self._steps: list[Step] = []
        self._i = -1
        self._overlay: Optional[TourOverlay] = None
        self._demo_path: Optional[Path] = None
        self._demo_loaded = False
        self._demo_failed = False
        self._poll = QTimer(self)
        self._poll.setInterval(200)
        self._poll.timeout.connect(self._poll_demo)
        self._t0 = 0.0
        self._saved = {}
        self._active_after: Optional[Callable] = None
        self._busy = False

    # — ciclo de vida —
    def start(self):
        w = self._win
        self._steps = build_steps(w)
        self._saved = {
            "video": w._results._chk_video.isChecked(),
            "adv": w._results._chk_advanced.isChecked(),
            "adv_open": bool(getattr(w._results, "_adv_open", False)),
            "page": w._stack.currentIndex(),
        }
        w._tour_demo = False
        self._overlay = TourOverlay(w)
        self._overlay.next_clicked.connect(self.next)
        self._overlay.back_clicked.connect(self.back)
        self._overlay.skip_clicked.connect(lambda: self.finish(False))
        self._overlay.resized.connect(self._on_resized)
        self._overlay.show()
        self._overlay.raise_()
        self._overlay.setFocus()
        self._i = -1
        self.next()

    def finish(self, completed: bool):
        self._poll.stop()
        self._leave_current()
        w = self._win
        ov, self._overlay = self._overlay, None
        if ov is not None:
            ov.hide()
            ov.deleteLater()
        R = w._results
        try:                                         # restaurar los ajustes que el recorrido tocó
            R._chk_video.setChecked(self._saved.get("video", False))
            R._chk_advanced.setChecked(self._saved.get("adv", False))
            R._set_adv_open(self._saved.get("adv_open", False))
        except Exception:
            pass
        if self._demo_loaded or getattr(w, "_tour_demo", False):
            self._demo_cleanup()
        w._tour_demo = False
        self.finished.emit(completed)
        self.deleteLater()

    def _demo_cleanup(self):
        w = self._win
        try:
            if w._worker is not None and w._worker.isRunning():
                try:
                    w._worker.progress.disconnect()
                    w._worker.finished.disconnect()
                    w._worker.error.disconnect()
                except Exception:
                    pass
                w._worker.requestInterruption()
                w._worker.wait(3000)
            pl = getattr(w._results, "_player", None)
            if pl is not None:
                try:
                    pl.release()                          # Windows no deja borrar un archivo abierto por el reproductor
                except Exception:
                    pass
            w._current_file = ""
            w._analysis = None
            w._plan = None
            w._beat_grid = None
            w._back_to_drop()
        except Exception:
            pass
        _remove_demo_file(self._demo_path)

    # — navegación —
    def _leave_current(self):
        fn, self._active_after = self._active_after, None
        if fn:
            try:
                fn()
            except Exception:
                pass

    def next(self):
        if self._busy or self._overlay is None:
            return
        if 0 <= self._i < len(self._steps) and self._steps[self._i].demo_trigger and not self._demo_loaded:
            self._load_demo()
            return
        if self._i >= len(self._steps) - 1:
            self.finish(True)
            return
        self._goto(self._i + 1, +1)

    def back(self):
        if self._busy or self._i <= 0:
            return
        self._goto(self._i - 1, -1)

    def _goto(self, idx: int, direction: int):
        w = self._win
        self._leave_current()
        while 0 <= idx < len(self._steps):
            st = self._steps[idx]
            if st.page == 2 and not self._demo_loaded:     # sin pista de ejemplo no hay panel de resultados
                if self._demo_failed:
                    idx = len(self._steps) - 1
                    continue
                if direction < 0:
                    idx -= 1
                    continue
            if st.page == 0 and st.key not in ("bienvenida", "fin") and w._stack.currentIndex() != 0 and direction < 0:
                w._stack.setCurrentIndex(0)                # al volver atrás desde resultados, regresa a la pantalla de inicio
            break
        idx = max(0, min(idx, len(self._steps) - 1))
        self._i = idx
        st = self._steps[idx]
        if st.page == 0 and idx < len(self._steps) - 1 and w._stack.currentIndex() != 0:
            w._stack.setCurrentIndex(0)
        if st.page == 2 and w._stack.currentIndex() != 2:
            w._stack.setCurrentIndex(2)
        if st.before:
            try:
                st.before()
            except Exception:
                pass
        self._active_after = st.after
        QTimer.singleShot(60, lambda i=idx, d=direction: self._present(i, d))

    def _present(self, idx: int, direction: int):
        if self._overlay is None or idx != self._i:
            return
        st = self._steps[idx]
        rect = self._target_rect(st)
        if st.optional and st.target is not None and rect is None:
            self._goto(idx + direction, direction)          # el objetivo no existe en esta edición
            return
        total = len(self._steps)
        self._overlay.set_content(idx, total, st.title, st.text, st.example, last=(idx == total - 1), first=(idx == 0))
        self._overlay.go_to(rect)
        self._overlay.raise_()
        self._overlay.setFocus()

    def _on_resized(self):
        if self._overlay is not None and not self._busy and 0 <= self._i < len(self._steps):
            self._present(self._i, +1)

    # — geometría del objetivo —
    def _target_rect(self, st: Step) -> Optional[QRect]:
        if st.target is None:
            return None
        try:
            tg = st.target()
        except Exception:
            return None
        ws = [x for x in (tg if isinstance(tg, (list, tuple)) else [tg]) if x is not None and x.isVisible()]
        if not ws:
            return None
        self._scroll_into_view(ws)
        app = self._win
        union = None
        for x in ws:
            r = QRect(x.mapTo(app, QPoint(0, 0)), x.size())
            union = r if union is None else union.united(r)
        pad = st.hole_pad
        union = union.adjusted(-pad, -pad, pad, pad).intersected(QRect(0, 0, app.width(), app.height()))
        return union

    def _scroll_into_view(self, ws):
        """Si el objetivo está dentro de un área con scroll, la desplaza para que quede en la parte alta y deje sitio a la tarjeta."""
        w0 = ws[0]
        sa = None
        p = w0.parentWidget()
        while p is not None:
            if isinstance(p, QScrollArea):
                sa = p
                break
            p = p.parentWidget()
        if sa is None:
            return
        content = sa.widget()
        sb = sa.verticalScrollBar()
        for _ in range(3):                               # el diseño puede tardar en asentarse (equipos lentos, Windows)
            lay = content.layout()
            if lay is not None:
                lay.activate()
            QApplicationProcess()
            top = min(x.mapTo(content, QPoint(0, 0)).y() for x in ws)
            bottom = max(x.mapTo(content, QPoint(0, x.height())).y() for x in ws)
            vp_h = sa.viewport().height()
            want_top = max(24, int(vp_h * 0.12))
            if bottom - top > vp_h * 0.55:               # objetivo muy alto: que se vea entero
                want_top = 24
            goal = max(0, top - want_top)
            # horizontal: en ventanas estrechas (o con fuentes anchas) el panel desborda y hay que acercar el objetivo
            hb = sa.horizontalScrollBar()
            left = min(x.mapTo(content, QPoint(0, 0)).x() for x in ws)
            right = max(x.mapTo(content, QPoint(x.width(), 0)).x() for x in ws)
            vp_w = sa.viewport().width()
            hgoal = hb.value()
            if left < hb.value() + 40 or right > hb.value() + vp_w - 40:
                hgoal = left - 40 if (right - left) > vp_w - 80 else right - vp_w + 40
                hgoal = max(0, hgoal)
            if sb.value() == min(goal, sb.maximum()) and hb.value() == min(hgoal, hb.maximum()):
                break
            sb.setValue(goal)
            hb.setValue(hgoal)
        QApplicationProcess()

    # — pista de ejemplo —
    def _load_demo(self):
        w = self._win
        self._busy = True
        ov = self._overlay
        ov.set_content(self._i, len(self._steps), "Analizando la pista de ejemplo…",
                       "AutoPrevias está detectando el BPM, la tonalidad, los drops y la estructura. Solo tarda unos segundos.",
                       "", last=False, first=False, busy=True)
        ov.go_to(None)
        try:
            from src.config import get_cache_dir
            self._demo_path = make_demo_track(Path(get_cache_dir()) / "tour" / DEMO_NAME)
            w._tour_demo = True
            self._t0 = time.time()
            w._load_file(str(self._demo_path))
            self._poll.start()
        except Exception:
            self._demo_failed = True
            self._busy = False
            self._goto(len(self._steps) - 1, +1)

    def _poll_demo(self):
        w = self._win
        done = w._stack.currentIndex() == 2 and w._analysis is not None
        failed = (time.time() - self._t0 > 2.0 and w._stack.currentIndex() == 0 and not w._worker.isRunning()) \
            or time.time() - self._t0 > self.DEMO_TIMEOUT
        if done:
            self._poll.stop()
            QTimer.singleShot(450, self._demo_ready)             # deja terminar el fundido de página
        elif failed:
            self._poll.stop()
            self._demo_failed = True
            self._busy = False
            self._goto(len(self._steps) - 1, +1)

    def _demo_ready(self):
        self._demo_loaded = True
        self._busy = False
        self._goto(self._i + 1, +1)


def QApplicationProcess():
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()


# ───────────────────────────── bienvenida ─────────────────────────────

class WelcomeDialog(QDialog):
    """Primera vez: ofrece hacer el recorrido o saltárselo. `choice` = 'tour' | 'skip'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.choice = "skip"
        self.setWindowTitle(tr("Bienvenido a AutoPrevias"))
        self.setModal(True)
        self.setFixedWidth(520)
        self.setStyleSheet(f"QDialog {{ background: {BG2}; }} QLabel {{ background: transparent; border: none; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 26, 30, 24)
        lay.setSpacing(12)
        try:
            from src.config import get_assets_dir
            for name in ("logo_emblem.png", "logo.png"):
                fp = Path(get_assets_dir()) / name
                if fp.exists():
                    pm = QPixmap(str(fp))
                    if not pm.isNull():
                        lg = QLabel()
                        lg.setPixmap(pm.scaledToHeight(64, Qt.SmoothTransformation))
                        lg.setAlignment(Qt.AlignCenter)
                        lay.addWidget(lg)
                        break
        except Exception:
            pass
        t = QLabel(tr("¡Bienvenido a AutoPrevias!"))
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(f"color: {TEXT}; font-size: 24px; font-weight: 900;")
        lay.addWidget(t)
        s = QLabel(tr("¿Quieres un recorrido rápido por toda la app? Son unos 5 minutos: te enseño cada botón con una "
                      "pista de ejemplo y no se guarda nada. Solo te lo propongo esta vez."))
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignCenter)
        s.setStyleSheet(f"color: {TEXT_MID}; font-size: 14px;")
        lay.addWidget(s)
        lay.addSpacing(6)
        b1 = QPushButton(tr("▶  Hacer el recorrido"))
        b1.setCursor(Qt.PointingHandCursor)
        b1.setStyleSheet(_btn_css(True))
        b1.clicked.connect(lambda: self._pick("tour"))
        b2 = QPushButton(tr("Omitir"))
        b2.setCursor(Qt.PointingHandCursor)
        b2.setStyleSheet(_btn_css(False))
        b2.clicked.connect(lambda: self._pick("skip"))
        lay.addWidget(b1)
        lay.addWidget(b2)
        b1.setDefault(True)

    def _pick(self, c: str):
        self.choice = c
        self.accept()

    def reject(self):                       # cerrar la ventana = omitir
        self.choice = "skip"
        super().reject()
