"""
AutoPrevias v5 — Montaje visual de los pasos ② «Tu previa» y ③ «Exportar».

`ResultPanel._build_ui` crea todos los controles con sus nombres de siempre; aquí se recolocan en tarjetas con el
diseño nuevo (títulos grandes, selectores con descripción, interruptores, tarjetas de formato). No hay lógica nueva
de audio: solo presentación y sincronización de lo que ya existía.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from src.i18n import tr
from src.ui import theme5 as T

PRESET_SUBS = {15: "Teaser para redes", 30: "Promo para radio", 60: "Para sellos y A&R", 120: "Club · recomendado"}
PRESET_TITLES = {15: "15 s", 30: "30 s", 60: "60 s", 120: "2 min"}


def _clear(layout):
    """Vacía un layout sin destruir los widgets (se guardan en R._v5_old para que sigan vivos)."""
    out = []
    while layout.count():
        it = layout.takeAt(0)
        w = it.widget()
        if w is not None:
            out.append(w)
        elif it.layout() is not None:
            out.extend(_clear(it.layout()))
    return out


def _wrap(layout) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    w.setLayout(layout)
    return w


def assemble(R, edition_plus: bool):
    """Monta los pasos ② y ③ del asistente con los widgets ya creados de `R` (ResultPanel)."""
    R._v5_old = []
    taken = []
    for lay in (R._page2.layout(), R._page3.layout()):
        for w in _clear(lay):
            taken.append((w, w.isHidden()))
            w.hide()
            R._v5_old.append(w)
    # widgets sueltos que ya no se ven pero siguen existiendo (otros códigos los consultan)
    R._hidden_holder = QWidget(R)
    R._hidden_holder.hide()
    hl = QVBoxLayout(R._hidden_holder)
    for w in (R._card_file, R._card_bpm, R._card_key, R._card_dur, R._card_drops, R._card_pv, R._chk_advanced,
              R._lbl_simple_desc, R._btn_new_track_top, R._chk_fx_flanger, R._chk_fx_filter):
        hl.addWidget(w)
    R._hidden_holder.hide()
    _step2(R, edition_plus)
    _step3(R, edition_plus)
    # los widgets que se reutilizan recuperan su visibilidad de antes (los marcos viejos se quedan ocultos)
    keep = {R._tabs, R._branding_card, R._lbl_summary, R._btn_generate, R._card_export_success, R._nav2, R._nav3,
            R._card_startend, R._spin_seed, R._btn_random_seed, R._btn_regen, R._btn_new}
    for w, was_hidden in taken:
        if w in keep:
            w.setHidden(was_hidden)


# ───────────────────────────── paso ② Tu previa ─────────────────────────────

def _step2(R, plus: bool):
    L = R._page2.layout()
    L.setSpacing(14)
    L.setContentsMargins(4, 0, 4, 0)

    R._s2_title = T.h1("Tu previa está lista para revisar", 28)
    R._s2_sub = T.sub("AutoPrevias ya ha elegido los mejores momentos. Escúchala y, si quieres, cámbiala.", 13)
    head = QHBoxLayout()
    col = QVBoxLayout()
    col.setSpacing(4)
    col.addWidget(R._s2_title)
    col.addWidget(R._s2_sub)
    head.addLayout(col, 1)
    R._btn_change_dest = QPushButton("🎯  Cambiar destino")
    R._btn_change_dest.setFixedHeight(34)
    R._btn_change_dest.setCursor(Qt.PointingHandCursor)
    R._btn_change_dest.setStyleSheet(T.ghost_css(17, 11.5))
    R._btn_change_dest.setToolTip("Volver a elegir para qué es la previa: redes, radio, sello, club…")
    R._btn_change_dest.clicked.connect(lambda _=False: R.change_destination_requested.emit())
    head.addWidget(R._btn_change_dest, 0, Qt.AlignTop)
    L.addLayout(head)

    # — tarjeta principal: reproductor + datos + onda —
    main = T.card(18)
    R._main_card = main
    mv = QVBoxLayout(main)
    mv.setContentsMargins(16, 14, 16, 12)
    mv.setSpacing(8)
    if R._player is not None:
        R._player.setStyleSheet("PlayerWidget { background: transparent; }")
        mv.addWidget(R._player)
    # fila de datos
    R._chips_row = QWidget()
    R._chips_row.setStyleSheet("background: transparent;")
    cr = QHBoxLayout(R._chips_row)
    cr.setContentsMargins(0, 0, 0, 0)
    cr.setSpacing(8)
    R._chip_file = QLabel("")
    R._chip_file.setStyleSheet(f"color: {T.TEXT}; font-size: 12.5px; font-weight: 800; {T._T}")
    cr.addWidget(R._chip_file, 1)
    R._chip_bpm, R._chip_key, R._chip_drops, R._chip_dur = T.chip("— BPM"), T.chip("—"), T.chip("— drops"), T.chip("—")
    R._chip_bpm.setCursor(Qt.PointingHandCursor)
    R._chip_bpm.setToolTip("Doble clic para corregir el BPM")
    R._chip_bpm.mouseDoubleClickEvent = lambda e: R._edit_bpm()
    for c in (R._chip_dur, R._chip_bpm, R._chip_key, R._chip_drops):
        cr.addWidget(c)
    mv.addWidget(R._chips_row)
    wf = getattr(R, "_waveform", None)
    if wf is not None:
        mv.addWidget(wf, 1)
    hint = T.sub("Las zonas marcadas son lo que entra en la previa. Arrastra los bordes verdes y rojos para cambiarlas.", 11.5)
    R._lbl_wave_hint = hint
    mv.addWidget(hint)
    L.addWidget(main)

    # — fila: duración + principio y final —
    row = QHBoxLayout()
    row.setSpacing(14)
    dur = T.card(16)
    R._card_duration = dur
    dv = QVBoxLayout(dur)
    dv.setContentsMargins(16, 14, 16, 12)
    dv.setSpacing(10)
    dv.addWidget(T.section_label("¿Cuánto debe durar?"))
    grid = QGridLayout()
    grid.setSpacing(10)
    R._preset_buttons = []
    grp = QButtonGroup(dur)
    grp.setExclusive(True)
    for i, sec in enumerate((15, 30, 60, 120)):
        t = T.Tile(tr(PRESET_TITLES[sec]), tr(PRESET_SUBS[sec]), min_h=70)
        t.setChecked(sec == getattr(R, "_active_preset_sec", 120))
        grp.addButton(t)
        t.clicked.connect(lambda _c=False, s=sec: R._apply_duration_preset(s))
        grid.addWidget(t, i // 2, i % 2)
        R._preset_buttons.append((t, sec))
        setattr(R, {15: "_btn_p15", 30: "_btn_p30", 60: "_btn_p60", 120: "_btn_p120"}[sec], t)
    dv.addLayout(grid)
    R._lbl_simple_desc.setParent(dur)
    R._lbl_simple_desc.setStyleSheet(f"color: {T.TEXT_DIM}; font-size: 10.5px; {T._T}")
    R._lbl_simple_desc.setWordWrap(True)
    R._lbl_simple_desc.show()
    dv.addWidget(R._lbl_simple_desc)
    row.addWidget(dur, 3)

    se = T.card(16)
    R._card_startend_simple = se
    sv = QVBoxLayout(se)
    sv.setContentsMargins(16, 14, 16, 12)
    sv.setSpacing(8)
    sv.addWidget(T.section_label("Cómo suena el principio y el final"))

    def _toggle_row(title, subtitle, setter, on):
        r = QHBoxLayout()
        c = QVBoxLayout()
        c.setSpacing(1)
        a = QLabel(title)
        a.setStyleSheet(f"color: {T.TEXT}; font-size: 14px; font-weight: 800; {T._T}")
        b = QLabel(subtitle)
        b.setStyleSheet(f"color: {T.TEXT_MID}; font-size: 11px; {T._T}")
        c.addWidget(a)
        c.addWidget(b)
        r.addLayout(c, 1)
        tg = T.Toggle(on=on)
        tg.toggled.connect(lambda on_, s=setter: s("vinyl" if on_ else "original"))
        r.addWidget(tg)
        return r, tg
    r1, R._tg_start = _toggle_row(tr("Arrancar como un disco de vinilo"), tr("Empieza lento y coge velocidad"),
                                  R._set_start_mode, R._start_mode == "vinyl")
    r2, R._tg_end = _toggle_row(tr("Acabar frenando"), tr("Como un disco que se para"), R._set_end_mode,
                                R._end_mode == "vinyl")
    sv.addLayout(r1)
    sep = QFrame()
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background: {T.BORDER}; border: none;")
    sv.addWidget(sep)
    sv.addLayout(r2)
    sv.addStretch()
    se.setVisible(plus)
    row.addWidget(se, 2)
    L.addLayout(row)

    # — «Retocar con más detalle» —
    det = T.card(16)
    R._detail_card = det
    dtv = QVBoxLayout(det)
    dtv.setContentsMargins(0, 0, 0, 0)
    dtv.setSpacing(0)
    head_d = T.ClickCard("detailhead")
    head_d.setStyleSheet("QFrame#detailhead { background: transparent; border: none; } QFrame#detailhead QLabel { background: transparent; border: none; }")
    hl = QHBoxLayout(head_d)
    hl.setContentsMargins(18, 14, 18, 14)
    ic = QLabel("🎛")
    ic.setStyleSheet(f"font-size: 22px; {T._T}")
    hl.addWidget(ic)
    tc = QVBoxLayout()
    tc.setSpacing(1)
    t1 = QLabel("Retocar con más detalle")
    t1.setStyleSheet(f"color: {T.TEXT}; font-size: 15px; font-weight: 800; {T._T}")
    t2 = QLabel("Cortes exactos, orden, variación de BPM… solo si lo necesitas." if plus
                else "Ordenar y mover los cortes… solo si lo necesitas.")
    t2.setStyleSheet(f"color: {T.TEXT_MID}; font-size: 11.5px; {T._T}")
    tc.addWidget(t1)
    tc.addWidget(t2)
    hl.addLayout(tc, 1)
    hl.addWidget(T.tag("Opcional"))
    R._lbl_detail_arrow = QLabel("▾")
    R._lbl_detail_arrow.setStyleSheet(f"color: {T.TEXT_MID}; font-size: 14px; {T._T}")
    hl.addWidget(R._lbl_detail_arrow)
    head_d.clicked.connect(lambda: R._chk_advanced.setChecked(not R._chk_advanced.isChecked()))
    dtv.addWidget(head_d)
    R._detail_body = QWidget()
    R._detail_body.setStyleSheet("background: transparent;")
    bv = QVBoxLayout(R._detail_body)
    bv.setContentsMargins(14, 0, 14, 14)
    bv.setSpacing(10)
    R._card_startend.setParent(R._detail_body)
    bv.addWidget(R._card_startend)
    R._preset_bar.setParent(R._detail_body)
    bv.addWidget(R._preset_bar)
    R._tabs.setParent(R._detail_body)
    R._tabs.setVisible(True)
    bv.addWidget(R._tabs)
    R._detail_body.setVisible(False)
    dtv.addWidget(R._detail_body)
    L.addWidget(det)

    L.addWidget(R._nav2)
    R._nav2.setParent(R._page2)
    L.addStretch(1)
    R._btn_back_drop.setStyleSheet(T.ghost_css(10, 12))
    R._btn_back_drop.setFixedHeight(40)
    R._btn_next.setText("Siguiente: elegir formatos  →")
    R._btn_next.setFixedHeight(48)
    R._btn_next.setStyleSheet(T.cta_css(12, 14))


# ───────────────────────────── paso ③ Exportar ─────────────────────────────

def _fmt_card(R, key, icon, desc, boxes, tagtext="", extra=None, name="fmt5"):
    """Tarjeta de formato con su(s) casilla(s) real(es) dentro. Se marca sola cuando alguna casilla está activa."""
    c = T.ClickCard(name)
    v = QVBoxLayout(c)
    v.setContentsMargins(16, 14, 16, 14)
    v.setSpacing(6)
    top = QHBoxLayout()
    ic = QLabel(icon)
    ic.setStyleSheet(f"font-size: 26px; {T._T}")
    top.addWidget(ic)
    top.addStretch()
    if tagtext:
        top.addWidget(T.tag(tagtext))
    v.addLayout(top)
    for b in boxes:
        b.setParent(c)
        b.setStyleSheet(T.checkbox_css())
        v.addWidget(b)
    d = QLabel(desc)
    d.setWordWrap(True)
    d.setStyleSheet(f"color: {T.TEXT_MID}; font-size: 11px; {T._T}")
    v.addWidget(d)
    if extra is not None:
        v.addWidget(extra)
    v.addStretch()

    def _sync(*_):
        c.set_selected(any(b.isChecked() for b in boxes))
    for b in boxes:
        b.toggled.connect(_sync)
    _sync()
    c.clicked.connect(lambda: boxes[0].isEnabled() and boxes[0].setChecked(not boxes[0].isChecked()))
    c._sync = _sync
    return c


def _step3(R, plus: bool):
    L = R._page3.layout()
    L.setSpacing(14)
    L.setContentsMargins(4, 0, 4, 0)

    L.addWidget(R._nav3)
    R._btn_back.setStyleSheet(T.ghost_css(10, 11.5))
    R._btn_back.setFixedHeight(34)
    L.addWidget(T.h1("¿Qué quieres crear?", 28))
    L.addWidget(T.sub("Marca lo que necesites. Lo más habitual ya viene elegido.", 13))

    # — fila de formatos —
    fr = QHBoxLayout()
    fr.setSpacing(14)
    R._chk_mp3.setText("MP3 320k")
    R._card_f_mp3 = _fmt_card(R, "mp3", "🎧", tr("Ligero, para enviar por correo y redes"), [R._chk_mp3], tagtext=tr("Recomendado"))
    fr.addWidget(R._card_f_mp3)
    R._chk_wav.setText("WAV 24b")
    R._card_f_wav = _fmt_card(R, "wav", "💿", tr("Máxima calidad para sellos y masters"), [R._chk_wav, R._chk_flac])
    R._card_f_wav.setVisible(plus)
    fr.addWidget(R._card_f_wav)
    # vídeo: formatos de imagen como pastillas dentro de la tarjeta
    asp = QWidget()
    asp.setStyleSheet("background: transparent;")
    ah = QHBoxLayout(asp)
    ah.setContentsMargins(0, 2, 0, 0)
    ah.setSpacing(6)
    for key, b in R._aspect_btns.items():
        b.setParent(asp)
        b.setText({"9:16": "9:16", "1:1": "1:1", "16:9": "16:9"}[key])
        b.setFixedHeight(24)
        b.setStyleSheet(f"QPushButton {{ background: #1a1d26; color: {T.TEXT_MID}; border: 1px solid {T.BORDER}; border-radius: 12px;"
                        " padding: 0 11px; font-size: 10.5px; font-weight: 800; }"
                        f"QPushButton:hover {{ border-color: {T.ACCENT}; }}"
                        f"QPushButton:checked {{ background: {T.ACCENT_DIM}; color: {T.ACCENT}; border-color: {T.ACCENT}; }}")
        ah.addWidget(b)
    ah.addStretch()
    R._chk_video.setText("Vídeo para redes")
    R._card_f_video = _fmt_card(R, "video", "🎬", tr("Con onda animada y carátula, listo para TikTok, Reels y YouTube"),
                                [R._chk_video], extra=asp)
    fr.addWidget(R._card_f_video)
    # modo promo (Plus)
    promo_extra = QWidget()
    promo_extra.setStyleSheet("background: transparent;")
    ph = QHBoxLayout(promo_extra)
    ph.setContentsMargins(0, 2, 0, 0)
    ph.setSpacing(6)
    R._spin_promo.setParent(promo_extra)
    ph.addWidget(R._spin_promo)
    R._lbl_promo.setParent(promo_extra)
    ph.addWidget(R._lbl_promo, 1)
    R._chk_promo.setText("Modo promo")
    R._card_f_promo = _fmt_card(R, "promo", "🛡", tr("Con tu voz repetida para que no se pueda reutilizar"), [R._chk_promo],
                                extra=promo_extra)
    R._card_f_promo.setVisible(plus)
    R._row_promo_widget.setVisible(False)                 # la fila antigua ya no se usa
    fr.addWidget(R._card_f_promo)
    L.addLayout(fr)
    if not plus:                                          # Basic: invitación discreta a Plus
        R._btn_plus_formats = QPushButton("🔒  WAV, FLAC, vídeo sin marca de agua y modo promo: solo en Plus")
        R._btn_plus_formats.setFixedHeight(34)
        R._btn_plus_formats.setCursor(Qt.PointingHandCursor)
        R._btn_plus_formats.setStyleSheet(f"QPushButton {{ background: transparent; color: #c4b5fd; border: 1px dashed #6d28d9;"
                                          " border-radius: 17px; font-size: 11.5px; font-weight: 700; padding: 0 18px; }"
                                          "QPushButton:hover { background: #2a1a4a; }")
        R._btn_plus_formats.clicked.connect(lambda _=False: R._open_plus_page())
        L.addWidget(R._btn_plus_formats, 0, Qt.AlignLeft)

    # detalles del vídeo (aparecen al marcarlo)
    L.addWidget(R._row_video_title_widget)

    # — nombre y carpeta | firma y carátula —
    row = QHBoxLayout()
    row.setSpacing(14)
    nc = T.card(16)
    R._card_name = nc
    nv = QVBoxLayout(nc)
    nv.setContentsMargins(16, 14, 16, 14)
    nv.setSpacing(8)
    nv.addWidget(T.section_label("Nombre y carpeta"))
    R._edit_name.setParent(nc)
    R._edit_name.setFixedHeight(38)
    R._edit_name.setStyleSheet(f"QLineEdit {{ background: #0c0e13; color: {T.TEXT}; border: 1px solid {T.BORDER}; border-radius: 10px;"
                               " padding: 0 12px; font-size: 13px; font-weight: 600; }"
                               f"QLineEdit:focus {{ border-color: {T.ACCENT}; }}")
    nv.addWidget(R._edit_name)
    fh = QHBoxLayout()
    fh.setSpacing(8)
    ficon = QLabel("📁")
    ficon.setStyleSheet(f"font-size: 14px; {T._T}")
    fh.addWidget(ficon)
    R._lbl_folder_path.setParent(nc)
    R._lbl_folder_path.setStyleSheet(f"color: {T.TEXT_MID}; font-size: 11.5px; {T._T}")
    fh.addWidget(R._lbl_folder_path, 1)
    for b in (R._btn_folder, R._btn_open_folder):
        b.setParent(nc)
        b.setFixedSize(84, 28)
        b.setStyleSheet(T.ghost_css(8, 11))
        fh.addWidget(b)
    nv.addLayout(fh)
    row.addWidget(nc, 3)

    fc = T.card(16)
    R._card_sign = fc
    fv = QHBoxLayout(fc)
    fv.setContentsMargins(16, 14, 16, 14)
    fv.setSpacing(14)
    R._lbl_sign_thumb = QLabel("RR")
    R._lbl_sign_thumb.setFixedSize(64, 64)
    R._lbl_sign_thumb.setAlignment(Qt.AlignCenter)
    R._lbl_sign_thumb.setStyleSheet("color: white; font-size: 20px; font-weight: 900; border-radius: 10px;"
                                    " background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #ff2a44, stop:1 #6e0010);")
    fv.addWidget(R._lbl_sign_thumb)
    fcol = QVBoxLayout()
    fcol.setSpacing(2)
    fcol.addWidget(T.section_label("Firma y carátula"))
    R._lbl_sign_name = QLabel("Radical Records")
    R._lbl_sign_name.setStyleSheet(f"color: {T.TEXT}; font-size: 15px; font-weight: 800; {T._T}")
    fcol.addWidget(R._lbl_sign_name)
    R._lbl_sign_sub = QLabel("Artista · sello · carátula puestos")
    R._lbl_sign_sub.setStyleSheet(f"color: {T.TEXT_MID}; font-size: 11px; {T._T}")
    fcol.addWidget(R._lbl_sign_sub)
    R._btn_sign_edit = QPushButton("✎  Editar")
    R._btn_sign_edit.setFixedHeight(28)
    R._btn_sign_edit.setCursor(Qt.PointingHandCursor)
    R._btn_sign_edit.setStyleSheet(T.ghost_css(8, 11))
    R._btn_sign_edit.clicked.connect(lambda _=False: R._open_signature_editor())
    fcol.addWidget(R._btn_sign_edit, 0, Qt.AlignLeft)
    fv.addLayout(fcol, 1)
    fc.setVisible(plus)
    row.addWidget(fc, 2)
    L.addLayout(row)

    # — opciones avanzadas (voz, master, firma completa) —
    R._btn_adv.setParent(R._page3)
    R._btn_adv.setStyleSheet(f"QPushButton {{ background: transparent; color: {T.TEXT_MID}; border: none; text-align: left;"
                             " font-size: 11.5px; font-weight: 700; padding: 4px 2px; }"
                             f"QPushButton:hover {{ color: {T.TEXT}; }}")
    L.addWidget(R._btn_adv)
    R._adv_fx_widget.setParent(R._page3)
    L.addWidget(R._adv_fx_widget)
    R._branding_card.setParent(R._page3)
    L.addWidget(R._branding_card)

    # — barra final: resumen + GENERAR —
    bar = T.card(16, accent=True, name="genbar")
    R._gen_bar = bar
    bh = QHBoxLayout(bar)
    bh.setContentsMargins(18, 12, 18, 12)
    bh.setSpacing(16)
    R._lbl_summary.setParent(bar)
    R._lbl_summary.setMaximumHeight(16777215)
    R._lbl_summary.setStyleSheet(f"color: {T.TEXT_MID}; font-size: 11px; background: transparent; border: none;")
    R._lbl_summary.setTextFormat(Qt.RichText)
    bh.addWidget(R._lbl_summary, 1)
    R._btn_generate.setParent(bar)
    R._btn_generate.setFixedHeight(54)
    R._btn_generate.setMinimumWidth(280)
    R._btn_generate.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    bh.addWidget(R._btn_generate)
    L.addWidget(bar)

    # — variante (seed) —
    sd = QHBoxLayout()
    sd.setSpacing(8)
    lab = QLabel("Variante (seed)")
    lab.setStyleSheet(f"color: {T.TEXT_DIM}; font-size: 11px; font-weight: 700; {T._T}")
    sd.addWidget(lab)
    for w in (R._spin_seed, R._btn_random_seed, R._btn_regen):
        w.setParent(R._page3)
        sd.addWidget(w)
    R._btn_new.setParent(R._page3)
    R._btn_new.setStyleSheet(T.ghost_css(8, 11))
    sd.addStretch()
    sd.addWidget(R._btn_new)
    L.addLayout(sd)

    L.addWidget(R._card_export_success)
    L.addStretch(1)
