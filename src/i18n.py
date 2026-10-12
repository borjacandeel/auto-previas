"""
AutoPrevias — Internacionalización ES/EN.

· El idioma por defecto es SIEMPRE el castellano, sea cual sea el idioma del sistema.
· Los textos fuente del código están en castellano; `tr()` los traduce al inglés con un
  diccionario exacto (src/i18n_en.py). Lo que no esté en el diccionario se muestra tal cual.
· `translate_tree()` traduce los widgets ya construidos (etiquetas, botones, tooltips,
  cabeceras de tabla…) y recuerda el texto original, por lo que se puede cambiar de idioma
  en caliente sin reiniciar.
"""
from __future__ import annotations

import re

LANGUAGES = {"es": "Español", "en": "English"}
DEFAULT_LANGUAGE = "es"

_lang = DEFAULT_LANGUAGE
_missing: set = set()
_ALPHA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}")


def get_language() -> str:
    return _lang


def set_language(code: str) -> str:
    """Fija el idioma activo ('es' o 'en'). Un código desconocido deja el castellano."""
    global _lang
    _lang = code if code in LANGUAGES else DEFAULT_LANGUAGE
    return _lang


def init_from_config(cfg: dict | None = None) -> str:
    """Lee `language` de la configuración (por defecto 'es')."""
    if cfg is None:
        try:
            from src.config import load
            cfg = load()
        except Exception:
            cfg = {}
    return set_language((cfg or {}).get("language", DEFAULT_LANGUAGE))


def _dicts():
    from src.i18n_en import EN, EN_PATTERNS
    return EN, EN_PATTERNS


def _lookup(text: str) -> str | None:
    EN, _ = _dicts()
    if text in EN:
        return EN[text]
    core = text.strip()
    if core and core in EN:                       # conserva el espaciado exterior
        lead = text[: len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()):]
        return lead + EN[core] + trail
    return None


def translate(text: str) -> str:
    """Traduce un texto fijo o un mensaje con valores (patrones). Sin traducción → igual."""
    if _lang == "es" or not text:
        return text
    hit = _lookup(text)
    if hit is not None:
        return hit
    _, patterns = _dicts()
    core = text.strip()
    for rx, template in patterns:
        m = rx.fullmatch(core)
        if m:
            try:
                return template.format(*m.groups())
            except Exception:
                break
    if _ALPHA.search(text):
        _missing.add(text)
    return text


def tr(text: str, **kw) -> str:
    """Texto traducido; `kw` rellena los {marcadores} después de traducir."""
    out = translate(text)
    if kw:
        try:
            return out.format(**kw)
        except Exception:
            return text.format(**kw) if "{" in text else text
    return out


def missing() -> list:
    """Textos castellanos vistos en modo inglés sin traducción (para depuración/tests)."""
    return sorted(_missing)


def clear_missing() -> None:
    _missing.clear()


# ── Traducción de widgets ya construidos ──────────────────────────────────────

def _retranslate(store: dict, key: str, current: str, setter) -> None:
    """Aplica `translate` al texto original y lo recuerda, de modo que al volver a
    castellano se restaura el original exacto aunque el código haya cambiado el texto."""
    rec = store.get(key)
    src = rec[0] if rec and current == rec[1] else current
    new = translate(src) if src else src
    if new != current:
        setter(new)
    store[key] = (src, new)


def set_text(widget, key: str, **kw) -> None:
    """Pone en `widget` el texto traducido y recuerda la plantilla (key + valores), de modo que
    al cambiar de idioma se vuelve a generar sin quedarse en el idioma anterior."""
    out = tr(key, **kw)
    widget.__dict__.setdefault("_i18n_tpl", {})["text"] = (key, dict(kw), out)
    widget.setText(out)


def mark_dynamic(*widgets) -> None:
    """Marca widgets cuyo texto se genera siempre con tr() para que translate_tree los omita."""
    for w in widgets:
        w.setProperty("i18n_skip", True)


def translate_widget(w) -> None:
    from PySide6.QtWidgets import (
        QAbstractButton, QComboBox, QGroupBox, QLabel, QLineEdit, QTabWidget, QTableWidget,
    )

    if w.property("i18n_skip"):                   # texto ya calculado con tr(): no tocar
        return
    tpl = w.__dict__.get("_i18n_tpl", {}).get("text")
    if tpl is not None:
        key, kw, last = tpl
        if hasattr(w, "text") and w.text() == last:        # nadie lo ha cambiado desde set_text
            new_text = tr(key, **kw)
            if new_text != last:
                w.setText(new_text)
                w.__dict__["_i18n_tpl"]["text"] = (key, kw, new_text)
            return
        w.__dict__["_i18n_tpl"].pop("text", None)           # lo cambió otro código: texto normal
    store = w.__dict__.setdefault("_i18n_store", {})
    if isinstance(w, QLabel) and not w.pixmap():
        _retranslate(store, "text", w.text(), w.setText)
    elif isinstance(w, QAbstractButton):
        _retranslate(store, "text", w.text(), w.setText)
    elif isinstance(w, QGroupBox):
        _retranslate(store, "title", w.title(), w.setTitle)
    elif isinstance(w, QLineEdit):
        _retranslate(store, "ph", w.placeholderText(), w.setPlaceholderText)
    elif isinstance(w, QComboBox):
        for i in range(w.count()):
            _retranslate(store, f"item{i}", w.itemText(i), lambda t, i=i: w.setItemText(i, t))
    elif isinstance(w, QTabWidget):
        for i in range(w.count()):
            _retranslate(store, f"tab{i}", w.tabText(i), lambda t, i=i: w.setTabText(i, t))
    elif isinstance(w, QTableWidget):
        for c in range(w.columnCount()):
            it = w.horizontalHeaderItem(c)
            if it is not None:
                _retranslate(store, f"hdr{c}", it.text(), it.setText)
    tip = w.toolTip()
    if tip or "tip" in store:
        _retranslate(store, "tip", tip, w.setToolTip)
    if w.isWindow():
        _retranslate(store, "title", w.windowTitle(), w.setWindowTitle)


def translate_tree(root) -> None:
    """Traduce `root` y todos sus descendientes según el idioma activo."""
    from PySide6.QtWidgets import QWidget

    translate_widget(root)
    for child in root.findChildren(QWidget):
        translate_widget(child)
