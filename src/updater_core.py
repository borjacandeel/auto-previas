"""
AutoPrevias — Lógica pura del actualizador (sin Qt, testeable en cualquier entorno).

Consulta la última Release de GitHub, elige el instalador que corresponde a la
plataforma y edición instaladas, y verifica su SHA-256 contra SHA256SUMS.txt.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

RELEASES_URL = "https://api.github.com/repos/borjacandeel/auto-previas/releases/latest"
SUMS_NAME = "SHA256SUMS.txt"
# GitHub exige User-Agent; Cloudflare bloquea el de urllib por defecto (error 1010)
USER_AGENT = "AutoPrevias-Updater/1.0"


@dataclass
class ReleaseInfo:
    version: str
    notes: str
    assets: dict[str, str] = field(default_factory=dict)   # nombre -> URL de descarga


def parse_version(text: str | None) -> tuple[int, int, int] | None:
    m = re.match(r"^\s*v?(\d+)\.(\d+)\.(\d+)", text or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def is_newer(remote: str, current: str) -> bool:
    r, c = parse_version(remote), parse_version(current)
    return r is not None and c is not None and r > c


def parse_release(data: dict) -> ReleaseInfo | None:
    """Convierte la respuesta de la API en ReleaseInfo. Ignora borradores y pre-releases."""
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    tag = (data.get("tag_name") or "").lstrip("v")
    if parse_version(tag) is None:
        return None
    assets = {
        a["name"]: a["browser_download_url"]
        for a in data.get("assets") or []
        if a.get("name") and a.get("browser_download_url")
    }
    return ReleaseInfo(
        version=tag,
        notes=(data.get("body") or "").strip(),
        assets=assets,
    )


def installer_asset_name(edition: str, plat: str | None = None, machine: str | None = None) -> str | None:
    """Nombre estable del instalador de la Release para esta plataforma y edición."""
    plat = plat or sys.platform
    machine = (machine or platform.machine()).lower()
    ed = "Plus" if (edition or "").lower() == "plus" else "Basic"
    if plat == "darwin":
        # Solo se publican builds Apple Silicon
        return f"AutoPrevias-{ed}-macOS-arm64.dmg" if machine in ("arm64", "aarch64") else None
    if plat == "win32":
        return f"AutoPrevias-{ed}-Windows-x64-Setup.exe"
    return None


def strip_links(text: str) -> str:
    """Quita enlaces y URLs de las notas: se muestra solo el texto, nunca direcciones."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text or "")
    return re.sub(r"https?://\S+", "", text)


def parse_sha256sums(text: str) -> dict[str, str]:
    """Lee el formato de sha256sum/shasum: '<hash>  <nombre>' o '<hash> *<nombre>'."""
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+?)\s*$", line)
        if m:
            out[m.group(2)] = m.group(1).lower()
    return out


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_ssl_context(bundled: bool = False):
    """Reutiliza el contexto SSL de la capa de licencias (bundle del sistema en macOS).

    Con `bundled=True` usa los certificados raíz de la app (plan B para Windows con certificados antiguos)."""
    try:
        from src.licensing.license import _make_ssl_context
        return _make_ssl_context(bundled=bundled)
    except Exception:
        import ssl
        return ssl.create_default_context()


def open_url(url: str, timeout: int = 15):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json, application/octet-stream",
    })
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=make_ssl_context())
    except Exception as e:
        try:
            from src.licensing.license import _is_cert_error
            if not _is_cert_error(e):
                raise
        except ImportError:
            raise e
        log_update_error(f"Certificados del sistema rechazados ({type(e).__name__}); se reintenta con los de la app")
        return urllib.request.urlopen(req, timeout=timeout, context=make_ssl_context(bundled=True))


def fetch_latest_release() -> ReleaseInfo | None:
    with open_url(RELEASES_URL, timeout=8) as resp:
        return parse_release(json.loads(resp.read().decode("utf-8")))


def log_update_error(detail: str) -> None:
    """Detalle técnico solo en un log local; nunca se muestra al usuario (puede contener URLs)."""
    try:
        import tempfile, time
        path = Path(tempfile.gettempdir()) / "autoprevias_update.log"
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {detail}\n")
    except Exception:
        pass


# ── Versión omitida por el usuario ────────────────────────────────────────────

def _state_file() -> Path:
    try:
        from src.licensing.license import _license_file
        return _license_file().parent / "update_state.json"
    except Exception:
        return Path.home() / ".autoprevias_update_state.json"


def get_skipped_version() -> str:
    try:
        return json.loads(_state_file().read_text(encoding="utf-8")).get("skipped", "")
    except Exception:
        return ""


def set_skipped_version(version: str) -> None:
    try:
        _state_file().write_text(json.dumps({"skipped": version}), encoding="utf-8")
    except Exception:
        pass
