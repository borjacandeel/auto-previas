"""
AutoPrevias — Pantalla «Licencia y ajustes»: versión, edición, estado de la licencia,
idioma, búsqueda manual de actualizaciones y desactivación de la licencia.
"""
from __future__ import annotations

import datetime as _dt

from PySide6.QtCore import QRectF, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPainter
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src import i18n, links
from src.i18n import tr
from src.ui.dialog_style import ACCENT, DIALOG_QSS, GREEN, RED, TEXT2, WARN

SUPPORT_EMAIL = "radicalrecordsvlc@gmail.com"


def describe_license(local: dict | None, now: float | None = None, grace_days: int = 14) -> dict:
    """Resumen de la licencia local para mostrar (función pura, testeable).

    Devuelve: state ('active'|'grace_expired'|'revoked'|'none'), license_id, verified, valid_until, days_left.
    """
    import time as _time

    if not local:
        return {"state": "none", "license_id": "", "verified": "", "valid_until": "", "days_left": 0}
    now = _time.time() if now is None else now
    verified_at = float(local.get("verified_at", 0) or 0)
    until = verified_at + grace_days * 86400
    days_left = int((until - now) // 86400)
    fmt = lambda ts: _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "—"
    state = "active" if now <= until else "grace_expired"
    if local.get("revoked"):
        state = "revoked"
    exp = float(local.get("expires_at", 0) or 0)           # licencia temporal (3 / 12 meses…); 0 = permanente
    if exp and not local.get("revoked") and (local.get("term_ended") or now >= exp):
        state = "term_ended"
    return {
        "expires": fmt(exp) if exp else "",
        "term_days": max(int(-(-(exp - now) // 86400)), 0) if exp else None,
        "state": state,
        "license_id": str(local.get("key_hash", ""))[:8].upper(),
        "verified": fmt(verified_at),
        "valid_until": fmt(until),
        "days_left": max(days_left, 0),
    }


class _TermRefresh(QThread):
    """Pregunta al servidor cuánto le queda a una licencia temporal (sin bloquear la ventana)."""
    done = Signal()

    def run(self):
        try:
            from src.licensing.license import reverify_if_due
            reverify_if_due(force=True)
        except Exception:
            pass
        self.done.emit()


class ThemeTile(QPushButton):
    """Tarjeta de un tema: miniatura de la interfaz con sus colores reales + nombre. Se puede marcar."""

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(138, 104)
        self.setToolTip(tr(theme.description))
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")

    def paintEvent(self, _e):
        from src import themes
        _themes_mod = themes
        qc = themes.raw_qcolor                       # los colores de la miniatura ya son los finales: no se pasan por el tema
        sel = self.isChecked()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg, card, accent, text = (qc(c) for c in self.theme.swatch)
        frame = QRectF(1.5, 1.5, self.width() - 3, self.height() - 3)
        p.setPen(qc("#ff1e38" if sel else "#555b6a"))
        p.setBrush(qc("#00000000"))
        pen = p.pen()
        pen.setWidthF(2.4 if sel else 1.2)
        p.setPen(pen)
        p.drawRoundedRect(frame, 12, 12)
        prev = QRectF(9, 9, self.width() - 18, 56)
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(prev, 8, 8)
        p.setBrush(card)                              # dos tarjetas de ejemplo
        p.drawRoundedRect(QRectF(15, 28, 52, 30), 5, 5)
        p.drawRoundedRect(QRectF(72, 28, 52, 30), 5, 5)
        p.setBrush(accent)                            # botón de acento
        p.drawRoundedRect(QRectF(15, 15, 34, 8), 4, 4)
        p.setBrush(text)                              # «texto»
        p.drawRoundedRect(QRectF(54, 17, 40, 4), 2, 2)
        p.drawRoundedRect(QRectF(20, 36, 30, 3.5), 1.7, 1.7)
        p.drawRoundedRect(QRectF(77, 36, 30, 3.5), 1.7, 1.7)
        p.setBrush(accent)
        p.drawRoundedRect(QRectF(77, 46, 22, 5), 2.5, 2.5)
        p.setPen(qc("#eceef2" if _themes_mod.get(_themes_mod.current()).dark else "#1b2030"))
        f = p.font()
        f.setPixelSize(12)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, 70, self.width(), 24), Qt.AlignCenter, ("✓ " if sel else "") + tr(self.theme.label))
        p.end()


class LicenseDialog(QDialog):
    language_changed = Signal(str)
    update_found = Signal(object)        # ReleaseInfo
    license_removed = Signal()
    tour_requested = Signal()            # «Ver recorrido de bienvenida»

    def __init__(self, version: str, edition: str, parent=None):
        super().__init__(parent)
        self._version = version
        self._edition = edition
        self._checker = None

        self.setWindowTitle("AutoPrevias — Licencia y ajustes")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setStyleSheet(DIALOG_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 20)
        root.setSpacing(10)

        title = QLabel("AutoPrevias")
        title.setStyleSheet("font-size: 20px; font-weight: 800;")
        root.addWidget(title)

        self._lbl_version = QLabel()
        self._lbl_version.setStyleSheet(f"font-size: 13px; color: {TEXT2};")
        root.addWidget(self._lbl_version)

        root.addWidget(self._separator())

        lic_title = QLabel("LICENCIA")
        lic_title.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {TEXT2}; letter-spacing: 1px;")
        root.addWidget(lic_title)
        self._lbl_state = QLabel()
        self._lbl_state.setWordWrap(True)
        self._lbl_state.setStyleSheet("font-size: 13px; font-weight: 700;")
        root.addWidget(self._lbl_state)
        self._lbl_detail = QLabel()
        self._lbl_detail.setWordWrap(True)
        self._lbl_detail.setStyleSheet(f"font-size: 12px; color: {TEXT2};")
        root.addWidget(self._lbl_detail)

        # Licencia temporal (3 / 12 meses): botones para renovar
        self._renew_box = QWidget()
        rl = QHBoxLayout(self._renew_box)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        self._renew_btns = []
        for label, url in links.renew_options(self._edition):
            price = links.price_text(self._edition, 12 if label.startswith("12") else 3, i18n.get_language())
            b = QPushButton(tr("Renovar {d} · {p}", d=tr(label), p=price) if price else tr("Renovar {d}", d=tr(label)))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _c=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            rl.addWidget(b)
            self._renew_btns.append(b)
        self._renew_box.setVisible(False)
        root.addWidget(self._renew_box)

        root.addWidget(self._separator())

        lang_row = QHBoxLayout()
        lang_lbl = QLabel("Idioma")
        lang_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
        self._combo_lang = QComboBox()
        for code, name in i18n.LANGUAGES.items():
            self._combo_lang.addItem(name, code)       # los nombres de idioma no se traducen
        self._combo_lang.setCurrentIndex(max(0, self._combo_lang.findData(i18n.get_language())))
        self._combo_lang.currentIndexChanged.connect(self._on_language)
        lang_row.addWidget(lang_lbl)
        lang_row.addStretch()
        lang_row.addWidget(self._combo_lang)
        root.addLayout(lang_row)

        # Tema de la app: Original, One Dark, Claro (y los que vengan). Se aplica al reiniciar la aplicación.
        from src import themes as _themes
        from src.config import load as _lc
        theme_lbl = QLabel("Tema de la app")
        theme_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
        root.addWidget(theme_lbl)
        self._theme_saved = str(_lc().get("theme") or _themes.DEFAULT_THEME)
        self._theme_running = _themes.current()
        trow = QHBoxLayout()
        trow.setSpacing(10)
        self._theme_tiles = {}
        for key in _themes.theme_keys():
            tile = ThemeTile(_themes.get(key))
            tile.setChecked(key == self._theme_saved)
            tile.clicked.connect(lambda _c=False, k=key: self._on_theme(k))
            trow.addWidget(tile)
            self._theme_tiles[key] = tile
        trow.addStretch()
        root.addLayout(trow)
        self._lbl_theme = QLabel("")
        self._lbl_theme.setWordWrap(True)
        self._lbl_theme.setStyleSheet(f"font-size: 11px; color: {TEXT2};")
        root.addWidget(self._lbl_theme)
        self._refresh_theme_hint()

        # Rendimiento: cuántos recursos del equipo usa AutoPrevias al analizar y generar vídeo
        from src import perf
        perf_row = QHBoxLayout()
        perf_lbl = QLabel("Rendimiento")
        perf_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
        self._combo_perf = QComboBox()
        for code, txt in (("auto", "Automático (recomendado)"), ("low", "Ahorro de recursos"), ("high", "Máximo rendimiento")):
            self._combo_perf.addItem(tr(txt), code)
        self._combo_perf.setCurrentIndex(max(0, self._combo_perf.findData(perf.get_mode())))
        self._combo_perf.setToolTip(tr("Automático se adapta a tu equipo y deja libre un núcleo para que la app siga fluida. "
                                       "Ahorro usa pocos recursos (portátil con batería, equipo antiguo u otros programas abiertos). "
                                       "Máximo usa todos los núcleos para terminar antes."))
        self._combo_perf.currentIndexChanged.connect(self._on_perf)
        perf_row.addWidget(perf_lbl)
        perf_row.addStretch()
        perf_row.addWidget(self._combo_perf)
        root.addLayout(perf_row)
        self._lbl_perf = QLabel("")
        self._lbl_perf.setStyleSheet(f"font-size: 11px; color: {TEXT2};")
        self._lbl_perf.setWordWrap(True)
        root.addWidget(self._lbl_perf)
        self._refresh_perf_hint()

        # Modo Estudio: para quien ya domina la app, todo en una sola pantalla en vez del asistente de 3 pasos
        from PySide6.QtWidgets import QCheckBox
        from src.config import load as _load_cfg, save as _save_cfg
        self._chk_studio = QCheckBox("Abrir siempre en modo Estudio (todo en una pantalla, sin asistente)")
        self._chk_studio.setToolTip("El asistente de 3 pasos es lo más fácil para empezar. Si ya conoces la app, el modo Estudio "
                                    "te enseña cortes, efectos y exportación a la vez. También se cambia con Ctrl/⌘ + E.")
        self._chk_studio.setChecked(bool(_load_cfg().get("always_studio")))

        def _save_studio(on):
            c = _load_cfg()
            c["always_studio"] = bool(on)
            _save_cfg(c)
        self._chk_studio.toggled.connect(_save_studio)
        root.addWidget(self._chk_studio)

        root.addWidget(self._separator())

        self._lbl_update = QLabel("")
        self._lbl_update.setWordWrap(True)
        self._lbl_update.setStyleSheet(f"font-size: 12px; color: {TEXT2};")
        root.addWidget(self._lbl_update)

        btn_row = QHBoxLayout()
        self._btn_update = QPushButton("Buscar actualizaciones")
        self._btn_update.clicked.connect(self._check_updates)
        self._btn_remove = QPushButton("Desactivar licencia en este equipo")
        self._btn_remove.setObjectName("danger")
        self._btn_remove.clicked.connect(self._remove_license)
        btn_row.addWidget(self._btn_update)
        btn_row.addWidget(self._btn_remove)
        root.addLayout(btn_row)

        self._btn_tour = QPushButton("Ver recorrido de bienvenida")
        self._btn_tour.setToolTip("Repite el recorrido guiado por toda la app (solo se ofrece solo la primera vez)")
        self._btn_tour.clicked.connect(lambda: (self.tour_requested.emit(), self.accept()))
        root.addWidget(self._btn_tour)

        self._lbl_support = QLabel()
        self._lbl_support.setStyleSheet(f"font-size: 11px; color: {TEXT2};")
        self._lbl_support.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self._lbl_support)

        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("primary")
        btn_close.clicked.connect(self.accept)
        close_row.addWidget(btn_close)
        root.addLayout(close_row)

        i18n.mark_dynamic(self._lbl_version, self._lbl_state, self._lbl_detail,
                          self._lbl_support, self._lbl_update, self._lbl_perf)
        self._refresh()
        i18n.translate_tree(self)
        self._term_thread = None
        self._refresh_term_from_server()

    def _refresh_term_from_server(self):
        """Licencia temporal: se consulta al Worker cuánto le queda y se actualiza lo que se muestra."""
        from src.config import _get_baked_edition
        from src.licensing.license import load_local
        local = load_local() or {}
        if _get_baked_edition() is None or not local.get("expires_at"):
            return
        self._term_thread = _TermRefresh(self)
        self._term_thread.done.connect(self._refresh)
        self._term_thread.start()

    def done(self, r):                     # la consulta en curso no debe sobrevivir al diálogo
        t = getattr(self, "_term_thread", None)
        if t is not None and t.isRunning():
            t.wait(9000)
        super().done(r)

    @staticmethod
    def _separator() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #232733; max-height: 1px; border: none;")
        return sep

    # ── Contenido dinámico (se vuelve a calcular al cambiar de idioma) ─────────
    def _refresh(self):
        plan = tr("PLUS") if self._edition == "plus" else tr("BÁSICA")
        self._lbl_version.setText(tr("Versión {v}  ·  Edición {ed}", v=self._version, ed=plan))
        self._lbl_support.setText(tr("Soporte: {mail}", mail=SUPPORT_EMAIL))

        from src.config import _get_baked_edition
        if _get_baked_edition() is None:
            self._lbl_state.setText(tr("🛠️ Modo desarrollo (sin licencia)"))
            self._lbl_state.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {WARN};")
            self._lbl_detail.setText(tr("Esta copia se ejecuta desde el código fuente: no se exige licencia."))
            self._btn_remove.setEnabled(False)
            return
        from src.licensing.license import GRACE_DAYS, load_local
        info = describe_license(load_local(), grace_days=GRACE_DAYS)
        self._renew_box.setVisible(info["expires"] != "")      # solo las licencias temporales se renuevan
        if info["state"] == "term_ended":
            self._lbl_state.setText(tr("⚠️ Licencia caducada"))
            self._lbl_state.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {RED};")
            self._lbl_detail.setText(tr("ID de licencia: {lid}\nCaducó el {exp}. Renueva para seguir usando AutoPrevias.",
                                        lid=info["license_id"], exp=info["expires"]))
        elif info["state"] == "active":
            n = info["term_days"]
            self._lbl_state.setText(tr("✅ Licencia activa"))
            self._lbl_state.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {GREEN if (n is None or n > 7) else WARN};")
            extra = ""
            if n is not None:
                extra = tr("Caduca el {exp} · quedan {n} días", exp=info["expires"], n=n) + "\n"
            self._lbl_detail.setText(extra + tr(
                "ID de licencia: {lid}\nÚltima verificación: {ver}\nVálida sin conexión hasta: {until} ({days} días)",
                lid=info["license_id"], ver=info["verified"], until=info["valid_until"], days=info["days_left"]))
        elif info["state"] == "revoked":
            self._lbl_state.setText(tr("⚠️ Esta licencia ya no es válida en este equipo"))
            self._lbl_state.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {RED};")
            self._lbl_detail.setText(tr(
                "ID de licencia: {lid}\nSe activó en otro equipo o fue desactivada.\nReinicia AutoPrevias para activarla de nuevo.",
                lid=info["license_id"]))
        elif info["state"] == "grace_expired":
            self._lbl_state.setText(tr("⚠️ Hay que volver a verificar la licencia"))
            self._lbl_state.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {WARN};")
            self._lbl_detail.setText(tr(
                "ID de licencia: {lid}\nÚltima verificación: {ver}\nConéctate a internet y reinicia AutoPrevias.",
                lid=info["license_id"], ver=info["verified"]))
        else:
            self._lbl_state.setText(tr("Sin licencia activada"))
            self._lbl_state.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {RED};")
            self._lbl_detail.setText("")
            self._btn_remove.setEnabled(False)

    def _refresh_theme_hint(self):
        from src import themes as _themes
        if self._theme_saved != self._theme_running:
            self._lbl_theme.setText(tr("Elegido: {t}. Se aplicará al reiniciar AutoPrevias.", t=tr(_themes.get(self._theme_saved).label)))
        else:
            self._lbl_theme.setText(tr("Más temas llegarán en próximas versiones."))

    def _on_theme(self, key: str):
        """Guarda el tema elegido y ofrece reiniciar para aplicarlo (así toda la interfaz queda coherente)."""
        from src.config import load as _lc, save as _sc
        for k, t in self._theme_tiles.items():
            t.setChecked(k == key)
            t.update()
        c = _lc()
        c["theme"] = key
        _sc(c)
        self._theme_saved = key
        self._refresh_theme_hint()
        if key == self._theme_running:
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(tr("Cambiar el tema"))
        box.setText(tr("Para aplicar el tema hay que reiniciar AutoPrevias."))
        box.setInformativeText(tr("Si estás generando una previa o un vídeo, espera a que termine antes de reiniciar."))
        b_now = box.addButton(tr("Reiniciar ahora"), QMessageBox.AcceptRole)
        box.addButton(tr("Después"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is b_now:
            from PySide6.QtWidgets import QApplication
            from src import themes as _t
            if _t.restart_application():
                QApplication.quit()

    def _refresh_perf_hint(self):
        from src import perf
        self._lbl_perf.setText(tr("Tu equipo: {c} núcleos · {r} GB de RAM → hasta {a} hilos al analizar y {v} al generar vídeo.",
                                  c=perf.cpu_cores(), r=round(perf.total_ram_gb()), a=perf.threads("analysis"), v=perf.threads("render")))

    def _on_perf(self):
        from src import perf
        perf.set_mode(self._combo_perf.currentData())
        self._refresh_perf_hint()

    def _on_language(self):
        code = self._combo_lang.currentData()
        i18n.set_language(code)
        self.language_changed.emit(code)
        self._refresh()
        i18n.translate_tree(self)

    # ── Actualizaciones ───────────────────────────────────────────────────────
    def _check_updates(self):
        from src.__version__ import __version__
        from src.update import UpdateChecker
        self._btn_update.setEnabled(False)
        self._lbl_update.setText(tr("Buscando actualizaciones…"))
        self._found = False
        self._checker = UpdateChecker(__version__, parent=self, ignore_skipped=True)
        self._checker.update_available.connect(self._on_update_found)
        self._checker.check_done.connect(self._on_check_done)
        self._checker.start()

    def _on_update_found(self, info):
        self._found = True
        self._lbl_update.setText(tr("🆕 Hay una versión nueva: {v}", v=info.version))
        self.update_found.emit(info)

    def _on_check_done(self):
        self._btn_update.setEnabled(True)
        if not getattr(self, "_found", False):
            self._lbl_update.setText(tr("✅ Estás al día ({v}).", v=self._version))

    # ── Desactivar licencia ───────────────────────────────────────────────────
    def _release_on_server(self) -> bool:
        """Libera la licencia en el servidor. False = el usuario cancela."""
        from PySide6.QtWidgets import QApplication
        from src.licensing.license import deactivate_online
        while True:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                ok, _code = deactivate_online()
            finally:
                QApplication.restoreOverrideCursor()
            if ok:
                return True
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle(tr("Desactivar licencia"))
            box.setText(tr("No se pudo contactar con el servidor para liberar la licencia.\n"
                           "Si la desactivas solo aquí, no podrás activarla en otro equipo hasta que "
                           "pasen 15 días o escribas a {mail}.", mail=SUPPORT_EMAIL))
            retry = box.addButton(tr("Reintentar"), QMessageBox.AcceptRole)
            local = box.addButton(tr("Desactivar solo aquí"), QMessageBox.DestructiveRole)
            box.addButton(tr("Cancelar"), QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is retry:
                continue
            return box.clickedButton() is local

    def _remove_license(self):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(tr("Desactivar licencia"))
        box.setText(tr("Se liberará la licencia para que puedas usarla en otro equipo y AutoPrevias se cerrará. "
                       "Podrás volver a activarla con tu clave cuando quieras."))
        yes = box.addButton(tr("Desactivar y cerrar"), QMessageBox.AcceptRole)
        box.addButton(tr("Cancelar"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is yes:
            if not self._release_on_server():
                return
            from src.licensing.license import clear_local
            clear_local()
            self.license_removed.emit()
            self.accept()

    def done(self, result):
        if self._checker is not None and self._checker.isRunning():
            self._checker.wait(2000)
        super().done(result)
