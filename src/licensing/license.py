"""
AutoPrevias — Sistema de verificación de licencias.

Flujo:
1. Al arrancar, se lee la licencia guardada localmente.
2. Si no hay licencia válida, se muestra la pantalla de activación.
3. La clave se envía al Cloudflare Worker, que la verifica con Payhip.
4. Si es válida, se guarda localmente y se establece la edición (basic/plus).
5. Cada 7 días se reverifica en segundo plano (sin bloquear la app).
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.request
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────

# Worker URL en base64 para no exponerla en texto plano
_W_B64 = b"aHR0cHM6Ly9hdXRvcHJldmlhcy1saWNlbnNlLnJhZGljYWxyZWNvcmRzdmxjLndvcmtlcnMuZGV2"


# Tiempo entre verificaciones en línea (7 días en segundos)
REVERIFY_INTERVAL = 7 * 24 * 3600

# Días de gracia si no hay conexión
GRACE_DAYS = 14


def _worker_url() -> str:
    return base64.b64decode(_W_B64).decode()


def _license_file() -> Path:
    """Ruta del archivo de licencia local."""
    import sys
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "AutoPrevias"
    elif sys.platform == "win32":
        import os
        base = Path(os.environ.get("APPDATA", Path.home())) / "AutoPrevias"
    else:
        base = Path.home() / ".autoprevias"
    base.mkdir(parents=True, exist_ok=True)
    return base / "license.json"


def _obfuscate(key: str) -> str:
    """Hash simple para no guardar la clave en texto plano."""
    return hashlib.sha256(key.encode()).hexdigest()


# ── Verificación online ────────────────────────────────────────────────────────

def _make_ssl_context():
    """Crea un contexto SSL con certifi (primero) o certs del sistema como fallback."""
    import ssl, os
    cafile = None

    # 1. Certifi: bundle propio, funciona en cualquier plataforma (incluye binarios Nuitka)
    try:
        import certifi
        candidate = certifi.where()
        if candidate and os.path.exists(candidate):
            cafile = candidate
    except Exception:
        pass

    # 2. Fallback: certs raíz del sistema (macOS y Linux)
    if not cafile:
        for path in ("/etc/ssl/cert.pem", "/usr/local/etc/openssl/cert.pem",
                     "/usr/local/etc/openssl@3/cert.pem", "/usr/local/share/ca-certificates/cacert.pem"):
            if os.path.exists(path) and os.path.getsize(path) > 0:
                cafile = path
                break

    if cafile:
        return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


def _ssl_log(msg: str) -> None:
    """Log rápido de errores SSL a /tmp para diagnóstico."""
    try:
        import os, traceback
        log = os.path.join(os.environ.get("TMPDIR", "/tmp"), "autoprevias_ssl.log")
        with open(log, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def verify_online(license_key: str) -> dict:
    """
    Envía la clave al Worker y devuelve el resultado normalizado.
    Retorna dict con 'success', 'edition' y opcionalmente 'error'.
    El Worker prueba Plus y Basic internamente usando las product-secret-keys.
    """
    key = license_key.strip().upper()
    try:
        payload = json.dumps({"license_key": key}).encode()
        req = urllib.request.Request(
            _worker_url(),
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        ctx = _make_ssl_context()
        with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
            data = json.loads(resp.read().decode())

        if data.get("success"):
            return {"success": True, "edition": data.get("edition", "basic"), "raw": data}

    except Exception as exc:
        import traceback
        _ssl_log(f"verify_online error [{type(exc).__name__}]: {exc}\n{traceback.format_exc()}")

    return {"success": False, "error": "Clave no válida o sin conexión"}


# ── Licencia local ─────────────────────────────────────────────────────────────

def load_local() -> dict | None:
    """Carga la licencia guardada. Devuelve None si no existe o está corrupta."""
    try:
        data = json.loads(_license_file().read_text(encoding="utf-8"))
        if "key_hash" in data and "edition" in data:
            return data
    except Exception:
        pass
    return None


def save_local(license_key: str, edition: str) -> None:
    """Guarda la licencia verificada en disco."""
    data = {
        "key_hash":      _obfuscate(license_key),
        "edition":       edition,
        "verified_at":   int(time.time()),
        "last_check":    int(time.time()),
    }
    _license_file().write_text(json.dumps(data, indent=2), encoding="utf-8")


def clear_local() -> None:
    """Elimina la licencia guardada (para desactivar)."""
    try:
        _license_file().unlink(missing_ok=True)
    except Exception:
        pass


# ── Estado de la licencia ──────────────────────────────────────────────────────

class LicenseStatus:
    VALID      = "valid"       # licencia en regla
    GRACE      = "grace"       # sin conexión, dentro del período de gracia
    EXPIRED    = "expired"     # período de gracia agotado
    UNLICENSED = "unlicensed"  # sin licencia


def check_license() -> tuple[LicenseStatus, str]:
    """
    Comprueba el estado de la licencia al arrancar.
    Devuelve (estado, edition) donde edition es 'basic', 'plus' o ''.
    """
    local = load_local()
    if local is None:
        return LicenseStatus.UNLICENSED, ""

    edition      = local.get("edition", "basic")
    last_check   = local.get("last_check", 0)
    verified_at  = local.get("verified_at", 0)
    now          = int(time.time())

    # Si han pasado más de REVERIFY_INTERVAL desde la última comprobación,
    # intentar verificar en línea (en segundo plano — no bloquea el arranque)
    if now - last_check > REVERIFY_INTERVAL:
        # Marcar intento para no reintentar en cada arranque si no hay conexión
        try:
            local["last_check"] = now
            _license_file().write_text(json.dumps(local, indent=2), encoding="utf-8")
        except Exception:
            pass

    # Período de gracia: si la última verificación exitosa fue hace < GRACE_DAYS días
    days_since = (now - verified_at) / 86400
    if days_since > GRACE_DAYS:
        return LicenseStatus.EXPIRED, edition

    return LicenseStatus.VALID, edition


def activate(license_key: str) -> tuple[bool, str, str]:
    """
    Intenta activar una clave de licencia.
    Devuelve (éxito, edition, mensaje_error).
    """
    result = verify_online(license_key)
    if result["success"]:
        edition = result["edition"]
        save_local(license_key, edition)
        return True, edition, ""
    return False, "", result.get("error", "Error desconocido")
