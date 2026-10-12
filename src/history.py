"""
AutoPrevias — Historial de previas generadas (panel «Recientes»).

Se guarda en `<datos de usuario>/history.json`, más reciente primero. Cada entrada
recuerda la pista original, los archivos generados y los ajustes (seed, opciones),
de modo que «Reabrir proyecto» pueda regenerar la misma previa.
"""
from __future__ import annotations

import datetime as _dt
import json
import uuid
from pathlib import Path

MAX_ENTRIES = 200


def history_file() -> Path:
    from src.config import get_user_data_dir
    return get_user_data_dir() / "history.json"


def _load_raw(path: Path) -> list:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_raw(entries: list, path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries[:MAX_ENTRIES], indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def add_entry(
    source: str,
    generated: list,
    seed: int = 0,
    bpm: float = 0.0,
    key: str = "",
    duration_sec: float = 0.0,
    settings: dict | None = None,
    promo: bool = False,
    path: Path | None = None,
) -> str:
    """Añade una entrada y devuelve su id. Ignora los WAV temporales internos."""
    path = path or history_file()
    files = [str(Path(p)) for p in generated if not Path(p).name.startswith("autoprevias_temp_")]
    entry = {
        "id": uuid.uuid4().hex[:12],
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        "source": str(source or ""),
        "title": Path(source).stem if source else (Path(files[0]).stem if files else "—"),
        "files": files,
        "seed": int(seed),
        "bpm": round(float(bpm or 0.0), 1),
        "key": key or "",
        "duration_sec": round(float(duration_sec or 0.0), 1),
        "settings": settings or {},
        "promo": bool(promo),
    }
    entries = [entry] + _load_raw(path)
    _save_raw(entries, path)
    return entry["id"]


def list_entries(path: Path | None = None) -> list:
    """Entradas con `exists` (¿siguen existiendo los archivos?) y `source_exists`."""
    out = []
    for e in _load_raw(path or history_file()):
        if not isinstance(e, dict) or "id" not in e:
            continue
        e = dict(e)
        e["existing_files"] = [f for f in e.get("files", []) if Path(f).exists()]
        e["exists"] = bool(e["existing_files"])
        e["source_exists"] = bool(e.get("source")) and Path(e["source"]).exists()
        out.append(e)
    return out


def remove_entry(entry_id: str, path: Path | None = None) -> bool:
    path = path or history_file()
    entries = _load_raw(path)
    kept = [e for e in entries if not (isinstance(e, dict) and e.get("id") == entry_id)]
    if len(kept) == len(entries):
        return False
    _save_raw(kept, path)
    return True


def clear(path: Path | None = None) -> None:
    _save_raw([], path or history_file())
