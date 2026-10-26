"""
AutoPrevias — Presets guardados como archivos.

Cada preset es un JSON dentro de `<datos de usuario>/presets/`. Puede incluir la
FIRMA (artista, sello, álbum, género, comentario y carátula) y/o el ESTILO
(duración, formatos, efectos, voice drop, modo promo, vídeo). Las claves
presentes en `data` son exactamente lo que se aplicará al cargarlo.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import shutil
from pathlib import Path

_VERSION = 1
_COVER_SUFFIX = "_cover"
_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def presets_dir() -> Path:
    from src.config import get_user_data_dir
    d = get_user_data_dir() / "presets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def slugify(name: str) -> str:
    """Nombre de archivo seguro (conserva letras con tilde); '' si no queda nada."""
    s = re.sub(r"[^\w\- ]+", "_", (name or "").strip(), flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip(" ._")
    s = s[:60]
    if s.upper() in _WIN_RESERVED:                   # CON.json, NUL.json… son dispositivos en Windows
        s += "_"
    return s


def _file(name: str, base: Path | None = None) -> Path:
    return (base or presets_dir()) / f"{slugify(name)}.json"


def list_presets(base: Path | None = None) -> list[str]:
    """Nombres de preset (tal como los escribió el usuario), ordenados sin distinguir mayúsculas."""
    names = []
    for f in (base or presets_dir()).glob("*.json"):
        try:
            names.append(json.loads(f.read_text(encoding="utf-8")).get("name") or f.stem)
        except Exception:
            continue
    return sorted(names, key=str.lower)


def save_preset(name: str, data: dict, base: Path | None = None) -> str:
    """Guarda (o sobrescribe) un preset. Devuelve el nombre guardado. Copia la carátula junto al JSON."""
    name = (name or "").strip()
    if not slugify(name):
        raise ValueError("El nombre del preset no es válido")
    base = base or presets_dir()
    base.mkdir(parents=True, exist_ok=True)
    data = dict(data)
    sig = data.get("signature")
    if isinstance(sig, dict):
        sig = dict(sig)
        cover = sig.get("cover_path") or ""
        _delete_cover(name, base)
        if cover and Path(cover).is_file():
            dest = base / f"{slugify(name)}{_COVER_SUFFIX}{Path(cover).suffix.lower() or '.jpg'}"
            try:
                shutil.copy2(cover, dest)
                sig["cover_path"] = dest.name           # relativo: el preset es portable
            except Exception:
                sig["cover_path"] = ""
        else:
            sig["cover_path"] = ""
        data["signature"] = sig
    payload = {
        "version": _VERSION,
        "name": name,
        "saved_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "data": data,
    }
    f = _file(name, base)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)
    return name


def load_preset(name: str, base: Path | None = None) -> dict | None:
    """Devuelve `data` del preset (con la carátula resuelta a ruta absoluta) o None si no existe/está corrupto."""
    base = base or presets_dir()
    try:
        payload = json.loads(_file(name, base).read_text(encoding="utf-8"))
        data = dict(payload.get("data") or {})
    except Exception:
        return None
    sig = data.get("signature")
    if isinstance(sig, dict) and sig.get("cover_path"):
        cover = base / sig["cover_path"]
        sig = dict(sig)
        sig["cover_path"] = str(cover) if cover.is_file() else ""
        data["signature"] = sig
    return data


def _delete_cover(name: str, base: Path) -> None:
    for c in base.glob(f"{slugify(name)}{_COVER_SUFFIX}.*"):
        if c.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue                                 # «foo_cover.json» es otro preset, no la carátula de «foo»
        try:
            c.unlink()
        except Exception:
            pass


def delete_preset(name: str, base: Path | None = None) -> bool:
    base = base or presets_dir()
    f = _file(name, base)
    existed = f.exists()
    try:
        f.unlink(missing_ok=True)
    except Exception:
        return False
    _delete_cover(name, base)
    return existed
