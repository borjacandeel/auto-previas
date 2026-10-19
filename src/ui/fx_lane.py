"""
AutoPrevias — Carril de efectos sobre la forma de onda (Basic y Plus).

· `FxPalette`: tarjetas de efectos que se arrastran hasta la onda (o se pulsan para ponerlas en el cursor).
· `FxPlotWidget`: la onda, que acepta las tarjetas soltadas encima.
· `FxBandItem`: el bloque del efecto dentro de la onda; se mueve, se estira por los bordes y se borra con Supr,
  igual que los cortes.
· `FxInspector`: fila con inicio, duración e intensidad del efecto seleccionado.
"""
from __future__ import annotations

from PySide6.QtCore import QMimeData, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QFont, QFontMetrics, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSlider, QWidget)

from src.engine.fx_events import FX_ICONS, FX_LABELS, FX_TYPES, MIN_DURATION
from src.i18n import tr

try:
    import pyqtgraph as pg
    HAS_PG = True
except ImportError:                                   # pragma: no cover
    pg = None
    HAS_PG = False

MIME = "application/x-autoprevias-fx"
FX_COLORS = {
    "flanger": (190, 90, 255),
    "filter_up": (60, 200, 255),
    "filter_down": (255, 170, 60),
}
Y_LO, Y_SPAN = -1.15, 2.3   # rango vertical fijo de la onda (ver WaveformWidget.reset_zoom)
LANE_H = 0.125              # alto de un carril, como fracción del alto de la onda
LANE_BASE = 0.02
LANE_GAP = 0.015
EDGE_PX = 7                # ancho de agarre de los bordes


def fx_label(kind: str) -> str:
    return tr(FX_LABELS.get(kind, kind))


def assign_lanes(events: list[dict]) -> dict[int, int]:
    """Reparte los bloques en 2 carriles para que los que se solapan no se tapen."""
    ends: list[float] = []
    lanes: dict[int, int] = {}
    for ev in sorted(events, key=lambda e: (e["start"], e["id"])):
        for ln, end in enumerate(ends):
            if ev["start"] >= end - 1e-6:
                ends[ln] = ev["end"]
                lanes[ev["id"]] = ln
                break
        else:
            ends.append(ev["end"])
            lanes[ev["id"]] = len(ends) - 1
    return {k: min(v, 2) for k, v in lanes.items()}


if HAS_PG:

    class FxBandItem(pg.GraphicsObject):
        """Bloque de efecto dentro de la onda (tiempos del tema original)."""

        def __init__(self, owner, ev: dict, lane: int = 0, ghost: bool = False):
            super().__init__()
            self.owner = owner
            self.ev = dict(ev)
            self.lane = lane
            self.ghost = ghost
            self.selected = False
            self.dim = False                           # fuera de los cortes: no sonará
            self._hover = None
            self._drag = None
            self.setZValue(9)
            self.setAcceptHoverEvents(True)
            self.setCursor(Qt.OpenHandCursor)

        # geometría
        def y0(self) -> float:
            return Y_LO + (LANE_BASE + self.lane * (LANE_H + LANE_GAP)) * Y_SPAN

        def set_range(self, start: float, end: float):
            self.prepareGeometryChange()
            self.ev["start"], self.ev["end"] = float(start), float(end)
            self.update()

        def boundingRect(self) -> QRectF:
            s, e = self.ev["start"], self.ev["end"]
            return QRectF(s, self.y0(), max(1e-6, e - s), LANE_H * Y_SPAN)

        def _px_per_sec(self) -> float:
            vb = self.getViewBox()
            if vb is None:
                return 1.0
            x0, x1 = vb.viewRange()[0]
            return max(1e-6, vb.width() / max(1e-6, x1 - x0))

        def _edge_at(self, x: float) -> str:
            """'l', 'r' o 'm' según dónde está el cursor (en segundos)."""
            pps = self._px_per_sec()
            s, e = self.ev["start"], self.ev["end"]
            m = min(EDGE_PX / pps, (e - s) / 3.0)
            if x <= s + m:
                return "l"
            if x >= e - m:
                return "r"
            return "m"

        # dibujo (en píxeles: así el texto no se deforma con la escala de la onda)
        def paint(self, p: QPainter, *_):
            r = p.worldTransform().mapRect(self.boundingRect())
            p.save()
            p.resetTransform()
            p.setRenderHint(QPainter.Antialiasing, True)
            col = QColor(*FX_COLORS.get(self.ev["type"], (255, 255, 255)))
            a_fill = 40 if self.dim else (95 if self.ghost else 150)
            fill = QColor(col)
            fill.setAlpha(a_fill)
            border = QColor(255, 255, 255, 235) if self.selected else QColor(col.red(), col.green(), col.blue(),
                                                                         110 if self.dim else 255)
            p.setBrush(fill)
            pen = QPen(border, 2.0 if self.selected else 1.4)
            if self.ghost or self.dim:
                pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            rr = r.adjusted(0.5, 0.5, -0.5, -0.5)
            p.drawRoundedRect(rr, 5, 5)

            # curva del efecto (adorno)
            p.setPen(QPen(QColor(255, 255, 255, 70 if not self.dim else 30), 1.3))
            kind = self.ev["type"]
            x0, x1 = rr.left() + 8, rr.right() - 8
            yc, ah = rr.center().y(), rr.height() * 0.30
            if x1 - x0 > 24:
                import math
                pts = []
                n = max(8, int((x1 - x0) / 4))
                for i in range(n + 1):
                    u = i / n
                    if kind == "flanger":
                        y = yc - ah * math.sin(u * math.pi * max(2.0, (x1 - x0) / 38.0))
                    elif kind == "filter_up":
                        y = yc + ah - 2 * ah * u
                    else:
                        y = yc - ah + 2 * ah * u
                    pts.append(QPointF(x0 + (x1 - x0) * u, y))
                p.drawPolyline(QPolygonF(pts))

            # texto
            dur = self.ev["end"] - self.ev["start"]
            txt = f"{FX_ICONS.get(kind, '')} {fx_label(kind)} · {dur:.1f}s"
            f = QFont(p.font())
            f.setPointSizeF(8.5)
            f.setBold(True)
            p.setFont(f)
            fm = QFontMetrics(f)
            avail = int(rr.width() - 14)
            if avail > 20:
                p.setPen(QColor(255, 255, 255, 120 if self.dim else 245))
                for cand in (txt, f"{FX_ICONS.get(kind, '')} {fx_label(kind)}", FX_ICONS.get(kind, "")):
                    if fm.horizontalAdvance(cand) <= avail:
                        txt = cand
                        break
                else:
                    txt = fm.elidedText(txt, Qt.ElideRight, avail)
                p.drawText(QRectF(rr.left() + 7, rr.top(), rr.width() - 14, rr.height()),
                           Qt.AlignVCenter | Qt.AlignLeft, txt)

            # agarres de los bordes
            if self.selected or self._hover in ("l", "r") or self.ghost:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 255, 255, 235))
                for x in (rr.left() + 2.5, rr.right() - 2.5):
                    p.drawRoundedRect(QRectF(x - 1.5, rr.top() + rr.height() * 0.22, 3.0, rr.height() * 0.56), 1.5, 1.5)
            p.restore()

        # ratón
        def hoverEvent(self, ev):
            if ev.isExit():
                self._hover = None
                self.setCursor(Qt.OpenHandCursor)
                self.update()
                return
            h = self._edge_at(ev.pos().x())
            self._hover = h
            self.setCursor(Qt.SizeHorCursor if h in ("l", "r") else Qt.OpenHandCursor)
            self.update()

        def mouseClickEvent(self, ev):
            if ev.button() == Qt.LeftButton:
                ev.accept()
                self.owner._select_fx(self.ev["id"])
            elif ev.button() == Qt.RightButton:
                ev.accept()
                self.owner._select_fx(self.ev["id"])
                self.owner._remove_fx(self.ev["id"])

        def mouseDragEvent(self, ev):
            if ev.button() != Qt.LeftButton or self.ghost:
                ev.ignore()
                return
            ev.accept()
            if ev.isStart():
                self.owner._select_fx(self.ev["id"])
                self._drag = (self._edge_at(ev.buttonDownPos().x()), self.ev["start"], self.ev["end"])
                self.owner._dragging = True
                self.setCursor(Qt.ClosedHandCursor if self._drag[0] == "m" else Qt.SizeHorCursor)
            if self._drag is None:
                return
            mode, s0, e0 = self._drag
            dx = ev.pos().x() - ev.buttonDownPos().x()
            s, e = self.owner._fx_move(self.ev["id"], mode, s0, e0, dx)
            self.set_range(s, e)
            self.owner._fx_live(self.ev["id"], s, e)
            if ev.isFinish():
                self._drag = None
                self.setCursor(Qt.OpenHandCursor)
                self.owner._fx_commit(self.ev["id"], s, e)


    class FxPlotWidget(pg.PlotWidget):
        """Onda que acepta tarjetas de efecto soltadas encima."""
        fx_over = Signal(str, float)
        fx_left = Signal()
        fx_dropped = Signal(str, float)
        fx_delete_key = Signal()

        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.setAcceptDrops(True)
            self.viewport().setAcceptDrops(True)

        def _kind(self, ev) -> str:
            md = ev.mimeData()
            if md is not None and md.hasFormat(MIME):
                k = bytes(md.data(MIME)).decode("utf-8", "ignore")
                return k if k in FX_TYPES else ""
            return ""

        def _time(self, ev) -> float:
            pt = ev.position().toPoint()
            return float(self.getViewBox().mapSceneToView(self.mapToScene(pt)).x())

        def dragEnterEvent(self, ev):
            if self._kind(ev):
                ev.acceptProposedAction()
            else:
                super().dragEnterEvent(ev)

        def dragMoveEvent(self, ev):
            k = self._kind(ev)
            if k:
                ev.acceptProposedAction()
                self.fx_over.emit(k, self._time(ev))
            else:
                super().dragMoveEvent(ev)

        def dragLeaveEvent(self, ev):
            self.fx_left.emit()
            super().dragLeaveEvent(ev)

        def dropEvent(self, ev):
            k = self._kind(ev)
            if k:
                ev.acceptProposedAction()
                self.fx_dropped.emit(k, self._time(ev))
            else:
                super().dropEvent(ev)

        def keyPressEvent(self, ev):
            if ev.key() in (Qt.Key_Delete, Qt.Key_Backspace):
                self.fx_delete_key.emit()
                return
            super().keyPressEvent(ev)


class _FxCard(QFrame):
    """Tarjeta de efecto: se arrastra hasta la onda (o se pulsa para ponerla en el cursor)."""
    clicked = Signal(str)

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self._press = None
        col = FX_COLORS[kind]
        self.setCursor(Qt.OpenHandCursor)
        self.setFixedHeight(30)
        self.setStyleSheet(
            f"QFrame {{ background: rgba({col[0]},{col[1]},{col[2]},0.16); border: 1px solid rgba({col[0]},{col[1]},{col[2]},0.75);"
            f" border-radius: 7px; }} QFrame:hover {{ background: rgba({col[0]},{col[1]},{col[2]},0.32); }}"
            " QLabel { background: transparent; border: none; color: #eceef2; font-size: 11px; font-weight: 700; }")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 12, 0)
        lay.setSpacing(6)
        self._lbl = QLabel(f"{FX_ICONS[kind]} {fx_label(kind)}")
        lay.addWidget(self._lbl)
        self.setToolTip(tr("Arrastra este efecto hasta la onda, o púlsalo para ponerlo donde está el cursor"))

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._press = ev.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, ev):
        if self._press is None or not (ev.buttons() & Qt.LeftButton):
            return
        if (ev.position().toPoint() - self._press).manhattanLength() < 8:
            return
        self._press = None
        drag = QDrag(self)
        md = QMimeData()
        md.setData(MIME, self.kind.encode("utf-8"))
        md.setText(fx_label(self.kind))
        drag.setMimeData(md)
        pm = self.grab()
        drag.setPixmap(pm)
        drag.setHotSpot(QPointF(8, pm.height() / 2).toPoint())
        drag.exec(Qt.CopyAction)
        self.setCursor(Qt.OpenHandCursor)

    def mouseReleaseEvent(self, ev):
        if self._press is not None and ev.button() == Qt.LeftButton:
            self.clicked.emit(self.kind)
        self._press = None
        self.setCursor(Qt.OpenHandCursor)


_BTN = ("QPushButton { background: #181b22; color: #8c93a4; border: 1px solid #232733; border-radius: 6px;"
        " font-size: 10.5px; font-weight: 700; padding: 0 10px; } "
        "QPushButton:hover { background: #2a2f3c; color: #eceef2; border-color: #ff1e38; }")


class FxPalette(QWidget):
    """Fila «🎛 EFECTOS»: tarjetas arrastrables y botón para quitarlos todos."""
    add_at_cursor = Signal(str)
    clear_all = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(8)
        lbl = QLabel(tr("🎛 EFECTOS"))
        lbl.setStyleSheet("color: #8c93a4; font-size: 9.5px; font-weight: 800; letter-spacing: 0.8px;"
                          " background: transparent; border: none;")
        lay.addWidget(lbl)
        self.cards = []
        for k in FX_TYPES:
            c = _FxCard(k, self)
            c.clicked.connect(self.add_at_cursor.emit)
            lay.addWidget(c)
            self.cards.append(c)
        self.hint = QLabel(tr("Arrastra un efecto hasta la onda · elige dónde empieza y cuánto dura · Supr borra el seleccionado"))
        self.hint.setStyleSheet("color: #636d83; font-size: 10px; font-weight: 600; background: transparent; border: none;")
        self.hint.setWordWrap(False)
        self.hint.setMinimumWidth(0)
        self.hint.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)     # no ensancha la ventana si no cabe
        lay.addWidget(self.hint, 1)
        self.btn_clear = QPushButton(tr("🗑 Quitar todos"))
        self.btn_clear.setFixedHeight(24)
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setStyleSheet(_BTN)
        self.btn_clear.clicked.connect(self.clear_all.emit)
        self.btn_clear.setVisible(False)
        lay.addWidget(self.btn_clear)


class FxInspector(QFrame):
    """Ajustes del efecto seleccionado: inicio, duración, intensidad y quitar."""
    changed = Signal(float, float, float)          # inicio, fin, intensidad
    removed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._busy = False
        self.setStyleSheet("QFrame#fxinsp { background: #14161c; border: 1px solid #2a2f3c; border-radius: 8px; }"
                           " QLabel { background: transparent; border: none; color: #8c93a4; font-size: 10px; font-weight: 700; }")
        self.setObjectName("fxinsp")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 5, 10, 5)
        lay.setSpacing(8)
        self.lbl_kind = QLabel("")
        self.lbl_kind.setStyleSheet("color: #eceef2; font-size: 11px; font-weight: 800; background: transparent; border: none;")
        lay.addWidget(self.lbl_kind)
        spin_css = ("QDoubleSpinBox { background: #181b22; color: #eceef2; border: 1px solid #2a2f3c; border-radius: 5px;"
                    " padding: 1px 4px; font-size: 11px; font-weight: 700; } QDoubleSpinBox:focus { border-color: #ff1e38; }")
        lay.addWidget(QLabel(tr("INICIO")))
        self.sp_start = QDoubleSpinBox()
        self.sp_start.setDecimals(1)
        self.sp_start.setSingleStep(0.5)
        self.sp_start.setSuffix(" s")
        self.sp_start.setStyleSheet(spin_css)
        self.sp_start.setMinimumWidth(86)
        lay.addWidget(self.sp_start)
        lay.addWidget(QLabel(tr("DURACIÓN")))
        self.sp_dur = QDoubleSpinBox()
        self.sp_dur.setDecimals(1)
        self.sp_dur.setSingleStep(0.5)
        self.sp_dur.setRange(MIN_DURATION, 60.0)
        self.sp_dur.setSuffix(" s")
        self.sp_dur.setStyleSheet(spin_css)
        self.sp_dur.setMinimumWidth(86)
        lay.addWidget(self.sp_dur)
        lay.addWidget(QLabel(tr("INTENSIDAD")))
        self.sl_amt = QSlider(Qt.Horizontal)
        self.sl_amt.setRange(10, 100)
        self.sl_amt.setFixedWidth(120)
        self.sl_amt.setStyleSheet(
            "QSlider::groove:horizontal { height: 4px; background: #2a2f3c; border-radius: 2px; }"
            " QSlider::sub-page:horizontal { background: #ff1e38; border-radius: 2px; }"
            " QSlider::handle:horizontal { background: #eceef2; width: 12px; margin: -5px 0; border-radius: 6px; }")
        lay.addWidget(self.sl_amt)
        self.lbl_amt = QLabel("75%")
        self.lbl_amt.setMinimumWidth(34)
        lay.addWidget(self.lbl_amt)
        lay.addStretch()
        self.btn_del = QPushButton(tr("🗑 Quitar"))
        self.btn_del.setFixedHeight(24)
        self.btn_del.setCursor(Qt.PointingHandCursor)
        self.btn_del.setStyleSheet(_BTN)
        lay.addWidget(self.btn_del)
        self.sp_start.valueChanged.connect(self._emit)
        self.sp_dur.valueChanged.connect(self._emit)
        self.sl_amt.valueChanged.connect(self._emit)
        self.btn_del.clicked.connect(self.removed.emit)
        self.hide()

    def show_event(self, ev: dict, duration: float):
        self._busy = True
        self.lbl_kind.setText(f"{FX_ICONS.get(ev['type'], '')} {fx_label(ev['type'])}")
        self.sp_start.setRange(0.0, max(0.0, duration - MIN_DURATION))
        self.sp_start.setValue(round(ev["start"], 1))
        self.sp_dur.setMaximum(max(MIN_DURATION, min(60.0, duration - ev["start"])) if duration else 60.0)
        self.sp_dur.setValue(round(ev["end"] - ev["start"], 1))
        self.sl_amt.setValue(int(round(ev["amount"] * 100)))
        self.lbl_amt.setText(f"{self.sl_amt.value()}%")
        self._busy = False

    def update_range(self, start: float, end: float):
        """Mientras se arrastra el bloque en la onda."""
        self._busy = True
        self.sp_start.setValue(round(start, 1))
        self.sp_dur.setValue(round(end - start, 1))
        self._busy = False

    def _emit(self, *_):
        if self._busy:
            return
        self.lbl_amt.setText(f"{self.sl_amt.value()}%")
        s = float(self.sp_start.value())
        self.changed.emit(s, s + float(self.sp_dur.value()), self.sl_amt.value() / 100.0)
