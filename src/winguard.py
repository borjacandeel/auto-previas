"""Arranque seguro en Windows.

Si la app se cierra de golpe al abrirse (cierre nativo de Qt Multimedia, controladores de audio/vídeo…), el siguiente
arranque lo detecta (el arranque anterior se quedó «pendiente») y prueba otra configuración:

1.er cierre  → cambia el motor de audio de Qt (WMF «windows» → «ffmpeg»).
2.º cierre   → modo seguro: sin animaciones y sin reproductor nativo (la app funciona; la escucha queda desactivada).

Cuando la ventana lleva unos segundos abierta sin problemas, se marca el arranque como correcto.
Todo queda anotado en el registro de arranque.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

BACKENDS = ("windows", "ffmpeg")


def state_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "AutoPrevias" / "startup_state.json"


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def decide(state: dict) -> dict:
    """Calcula la configuración de este arranque a partir del estado anterior (función pura, testeable).
    Si el arranque anterior quedó pendiente, su motor se apunta como «malo» y se prueba el siguiente; si todos han
    fallado, modo seguro. Lo que funciona se conserva en los siguientes arranques."""
    bad = [b for b in (state.get("bad") or []) if b in BACKENDS]
    backend = state.get("backend") if state.get("backend") in BACKENDS else BACKENDS[0]
    safe = bool(state.get("safe_mode"))
    if state.get("pending"):
        if safe:
            pass  # ya estaba en modo seguro: no hay nada más que desactivar
        else:
            if backend not in bad:
                bad.append(backend)
            libres = [b for b in BACKENDS if b not in bad]
            if libres:
                backend = libres[0]
            else:
                safe = True
    return {
        "backend": backend,
        "bad": bad,
        "crashes": len(bad) + (1 if safe else 0),
        "safe_mode": safe,
        "pending": True,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def prepare(path: Path | None = None, log=None, env=None) -> dict:
    """Llamar ANTES de importar Qt Multimedia. Aplica el motor de audio y, si hace falta, el modo seguro."""
    env = os.environ if env is None else env
    path = path or state_path()
    cfg = decide(_read(path))
    if "QT_MEDIA_BACKEND" not in env:
        env["QT_MEDIA_BACKEND"] = cfg["backend"]
    if cfg["safe_mode"]:
        env["AUTOPREVIAS_NO_ANIM"] = "1"
        env["AUTOPREVIAS_NO_MEDIA"] = "1"
    _write(path, cfg)
    if log:
        try:
            log(f"Arranque seguro: motor de audio={env.get('QT_MEDIA_BACKEND')} cierres_previos={cfg['crashes']} "
                f"modo_seguro={cfg['safe_mode']}")
        except Exception:
            pass
    return cfg


def mark_ok(path: Path | None = None, log=None) -> None:
    """La ventana lleva unos segundos abierta: el arranque fue bien. Se conserva el motor que funcionó."""
    path = path or state_path()
    data = _read(path)
    data["pending"] = False
    _write(path, data)
    if log:
        try:
            log(f"Arranque correcto (motor de audio={data.get('backend')}).")
        except Exception:
            pass


def media_disabled() -> bool:
    return os.environ.get("AUTOPREVIAS_NO_MEDIA") == "1"


def active() -> bool:
    return sys.platform == "win32"
