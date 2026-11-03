"""AutoPrevias Demo — prueba gratuita de 7 días, ligada al equipo.

La demo cuenta 7 días desde el PRIMER arranque en ese ordenador. Para que no se pueda reiniciar borrando una carpeta:
  · el inicio se guarda a la vez en VARIOS sitios (carpeta de la app, otra carpeta del sistema compartida y, en Windows,
    el registro), todos firmados con un sello ligado al identificador del equipo; se usa siempre el inicio más antiguo;
  · si alguna copia está manipulada, o el reloj se ha retrasado, la demo se bloquea;
  · si hay conexión, además se pregunta al servidor de licencias (acción «demo»), que recuerda el primer arranque de ese
    equipo aunque se reinstale todo (clave por equipo, no se reinicia).
Nada de esto sale del ordenador salvo el identificador anónimo (hash) que ya usan las licencias.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

DEMO_DAYS = 7
_SECRET = b"autoprevias-demo-v1|radical-records"
_DAY = 86400


@dataclass
class DemoState:
    status: str            # "active" | "expired" | "tampered" | "clock"
    start: int = 0
    expires_at: int = 0
    days_left: int = 0

    @property
    def ok(self) -> bool:
        return self.status == "active"


def _dev() -> str:
    from src.licensing.device import get_device_id
    return get_device_id()


def _seal(start: int, last: int, dev: str) -> str:
    return hmac.new(_SECRET, f"{start}|{last}|{dev}".encode(), hashlib.sha256).hexdigest()[:40]


def _record(start: int, last: int, dev: str) -> dict:
    return {"start": int(start), "last": int(last), "dev": dev[:16], "seal": _seal(start, last, dev)}


def _valid(rec, dev: str) -> bool:
    try:
        return (isinstance(rec, dict) and rec.get("dev") == dev[:16]
                and hmac.compare_digest(str(rec.get("seal", "")), _seal(int(rec["start"]), int(rec["last"]), dev)))
    except Exception:
        return False


def _locations(dev: str) -> list[Path]:
    h = dev[:10]
    home = Path.home()
    out: list[Path] = []
    try:
        from src.config import get_user_data_dir
        out.append(Path(get_user_data_dir()) / "demo.json")
    except Exception:
        pass
    if sys.platform == "win32":
        la = os.environ.get("LOCALAPPDATA")
        pd = os.environ.get("PROGRAMDATA")
        if la:
            out.append(Path(la) / "AutoPrevias" / "demo.dat")
        if pd:
            out.append(Path(pd) / "AutoPrevias" / f"demo_{h}.dat")
        out.append(home / "AppData" / "Roaming" / "Microsoft" / "Windows" / f".apdemo_{h}")
    elif sys.platform == "darwin":
        out += [home / "Library" / "Preferences" / f".autoprevias_demo_{h}",
                Path("/Users/Shared") / f".autoprevias_demo_{h}",
                home / "Library" / "Application Support" / ".apdemo",
                home / "Library" / "Caches" / f".apdemo_{h}"]
    else:
        out += [home / ".local" / "share" / f".apdemo_{h}", home / ".config" / f".apdemo_{h}"]
    return out


def _reg_read() -> dict | None:
    if sys.platform != "win32":
        return None
    try:
        import winreg  # type: ignore[import-not-found]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\RadicalRecords\AutoPrevias", 0, winreg.KEY_READ) as k:
            return json.loads(str(winreg.QueryValueEx(k, "DemoState")[0]))
    except Exception:
        return None


def _reg_write(rec: dict) -> None:
    if sys.platform != "win32":
        return
    try:
        import winreg  # type: ignore[import-not-found]
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\RadicalRecords\AutoPrevias") as k:
            winreg.SetValueEx(k, "DemoState", 0, winreg.REG_SZ, json.dumps(rec))
    except Exception:
        pass


def _read_all(dev: str) -> list:
    recs = []
    for p in _locations(dev):
        try:
            if p.is_file():
                recs.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            recs.append({"bad": True})                   # archivo presente pero ilegible/manipulado
    r = _reg_read()
    if r is not None:
        recs.append(r)
    return recs


def _write_all(rec: dict, dev: str) -> None:
    txt = json.dumps(rec)
    for p in _locations(dev):
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_name(p.name + ".tmp")
            tmp.write_text(txt, encoding="utf-8")
            os.replace(tmp, p)
        except Exception:
            pass
    _reg_write(rec)


def server_start(dev: str) -> dict | None:
    """Pregunta al servidor de licencias por el primer arranque de este equipo (None si no hay conexión)."""
    try:
        from src.licensing import license as L
        data, net_error = L._request({"action": "demo", "device_id": dev, "platform": sys.platform, "app_edition": "demo"})
        if not net_error and isinstance(data, dict) and data.get("success"):
            return {"start": int(data.get("start") or 0), "expires_at": int(data.get("expires_at") or 0),
                    "expired": bool(data.get("expired"))}
    except Exception:
        pass
    return None


def check_demo(now: int | None = None, online: bool = False) -> DemoState:
    """Estado de la demo en este equipo. Crea el inicio si es el primer arranque. `online=True` consulta además al servidor."""
    now = int(time.time()) if now is None else int(now)
    dev = _dev()
    recs = _read_all(dev)
    good = [r for r in recs if _valid(r, dev)]
    if recs and not good:                               # hay copias y ninguna es válida: manipuladas
        return DemoState("tampered")
    if any(("bad" in r) or (isinstance(r, dict) and not _valid(r, dev)) for r in recs):
        return DemoState("tampered")
    if good:
        start = min(int(r["start"]) for r in good)
        last = max(int(r["last"]) for r in good)
    else:
        start, last = now, now
    if online:
        sv = server_start(dev)
        if sv and sv["start"]:
            start = min(start, sv["start"])
            if sv["expired"]:
                start = min(start, now - DEMO_DAYS * _DAY - 1)
    if now < last - 3600:                                # el reloj se ha retrasado más de 1 h
        return DemoState("clock", start, start + DEMO_DAYS * _DAY, 0)
    last = max(last, now)
    _write_all(_record(start, last, dev), dev)           # también restaura las copias que falten
    exp = start + DEMO_DAYS * _DAY
    if now >= exp:
        return DemoState("expired", start, exp, 0)
    return DemoState("active", start, exp, max(1, -(-(exp - now) // _DAY)))
