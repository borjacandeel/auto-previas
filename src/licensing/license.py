"""
AutoPrevias — Sistema de verificación de licencias.

Flujo:
1. Al arrancar, se lee la licencia guardada localmente.
2. Si no hay licencia válida, se muestra la pantalla de activación.
3. La clave se envía al Cloudflare Worker, que la verifica con Payhip.
4. Si es válida, se guarda localmente y se establece la edición (basic/plus).
5. Se reverifica sola con el servidor en cada arranque y cada 6 h mientras la app está abierta
   (en segundo plano, sin pedir nunca la clave otra vez: la clave se guarda cifrada en el equipo).
6. Una licencia = un equipo: el Worker ata la clave al identificador anónimo del equipo
   (src/licensing/device.py). Si ya está activa en otro equipo, no se puede activar en uno nuevo
   hasta que se desactive allí (o pasen 15 días sin que ese equipo la verifique).
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────

# Worker URL en base64 para no exponerla en texto plano
_W_B64 = b"aHR0cHM6Ly9hdXRvcHJldmlhcy1saWNlbnNlLnJhZGljYWxyZWNvcmRzdmxjLndvcmtlcnMuZGV2"


# Tiempo entre verificaciones en línea mientras la app está abierta (6 h en segundos)
REVERIFY_INTERVAL = 6 * 3600

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
    """Contexto SSL por defecto; en macOS añade el bundle del sistema si existe.

    No importar certifi: su módulo compilado con Nuitka provoca un segfault.
    """
    import ssl, os
    ctx = ssl.create_default_context()
    for path in ("/etc/ssl/cert.pem", "/usr/local/etc/openssl@3/cert.pem",
                 "/usr/local/etc/openssl/cert.pem"):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            try:
                ctx.load_verify_locations(cafile=path)
            except Exception:
                pass
            break
    return ctx


def _ssl_log(msg: str) -> None:
    """Log rápido de errores SSL a /tmp para diagnóstico."""
    try:
        import os, traceback
        log = os.path.join(os.environ.get("TMPDIR", "/tmp"), "autoprevias_ssl.log")
        with open(log, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


# Mensajes para el usuario (se traducen con tr() al mostrarlos)
MSG_INVALID = "Clave no válida"
MSG_NETWORK = "No se pudo conectar con el servidor de licencias. Comprueba tu conexión a Internet."
MSG_IN_USE = ("Esta licencia ya está activada en otro equipo. Desactívala allí (⚙ Licencia → Desactivar "
              "licencia en este equipo) o escribe a radicalrecordsvlc@gmail.com.")
MSG_UPDATE = "Hay una versión nueva de AutoPrevias: actualiza para poder activar tu licencia."
_MESSAGES = {"invalid": MSG_INVALID, "network": MSG_NETWORK, "in_use": MSG_IN_USE,
             "update_required": MSG_UPDATE, "not_owner": MSG_IN_USE}


def _request(payload: dict) -> tuple[dict | None, bool]:
    """POST al Worker. Devuelve (datos | None, error_de_red)."""
    try:
        req = urllib.request.Request(
            _worker_url(),
            data=json.dumps(payload).encode(),
            # Cloudflare bloquea (403, error 1010) el User-Agent por defecto de urllib
            headers={"Content-Type": "application/json",
                     "User-Agent": "AutoPrevias-License/1.0",
                     "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8, context=_make_ssl_context()) as resp:
            return json.loads(resp.read().decode()), False
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode()), False       # el Worker responde JSON también en errores
        except Exception:
            _ssl_log(f"license HTTP {exc.code}")
    except Exception as exc:
        import traceback
        _ssl_log(f"license request error [{type(exc).__name__}]: {exc}\n{traceback.format_exc()}")
    return None, True


def verify_online(license_key: str, action: str = "activate", device_id: str | None = None) -> dict:
    """
    Envía la clave y el identificador del equipo al Worker.
    action: 'activate' (primera vez), 'verify' (reverificación periódica) o 'deactivate'.
    Retorna {'success': True, 'edition': ...} o {'success': False, 'code': ..., 'error': ...}
    con code ∈ network | invalid | in_use | update_required | not_owner.
    El Worker prueba Plus y Basic internamente usando las product-secret-keys.
    """
    from src.licensing.device import get_device_id
    payload = {"action": action, "license_key": license_key.strip().upper(),
               "device_id": device_id or get_device_id(), "platform": sys.platform}
    data, net_error = _request(payload)
    if net_error or not isinstance(data, dict):
        return {"success": False, "code": "network", "error": MSG_NETWORK}
    if data.get("success"):
        return {"success": True, "edition": data.get("edition", "basic"), "raw": data}
    code = str(data.get("code") or "invalid")
    return {"success": False, "code": code, "error": _MESSAGES.get(code, MSG_INVALID)}


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


def _xor(data: bytes, device_id: str) -> bytes:
    pad = hashlib.sha256(("autoprevias:key:" + device_id).encode()).digest()
    return bytes(b ^ pad[i % len(pad)] for i, b in enumerate(data))


def _encode_key(license_key: str, device_id: str) -> str:
    """Ofusca la clave ligándola al equipo: copiar license.json a otro PC no sirve de nada."""
    return base64.b64encode(_xor(license_key.strip().upper().encode(), device_id)).decode()


def _decode_key(blob: str, device_id: str) -> str:
    try:
        return _xor(base64.b64decode(blob.encode()), device_id).decode()
    except Exception:
        return ""


def _write_local(data: dict) -> None:
    _license_file().write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_local(license_key: str, edition: str) -> None:
    """Guarda la licencia verificada en disco, atada a este equipo."""
    from src.licensing.device import get_device_id
    dev = get_device_id()
    now = int(time.time())
    _write_local({
        "key_hash":    _obfuscate(license_key),
        "key_enc":     _encode_key(license_key, dev),
        "device":      dev,
        "edition":     edition,
        "verified_at": now,
        "last_check":  now,
    })


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
    REVOKED    = "revoked"     # el servidor indicó que ya no es válida en este equipo


def check_license() -> tuple[LicenseStatus, str]:
    """
    Comprueba el estado de la licencia al arrancar (sin red; la reverificación va en segundo plano).
    Devuelve (estado, edition) donde edition es 'basic', 'plus' o ''.
    """
    local = load_local()
    if local is None:
        return LicenseStatus.UNLICENSED, ""

    edition = local.get("edition", "basic")
    if local.get("revoked"):
        return LicenseStatus.REVOKED, edition

    # licencia copiada desde otro equipo → no vale
    dev = local.get("device")
    if dev:
        from src.licensing.device import get_device_id
        if dev != get_device_id():
            return LicenseStatus.UNLICENSED, ""

    # Período de gracia: la última verificación correcta fue hace < GRACE_DAYS días
    days_since = (int(time.time()) - local.get("verified_at", 0)) / 86400
    if days_since > GRACE_DAYS:
        return LicenseStatus.EXPIRED, edition
    return LicenseStatus.VALID, edition


def activate(license_key: str) -> tuple[bool, str, str]:
    """
    Intenta activar una clave de licencia en este equipo.
    Devuelve (éxito, edition, mensaje_error).
    """
    result = verify_online(license_key, action="activate")
    if result["success"]:
        edition = result["edition"]
        save_local(license_key, edition)
        return True, edition, ""
    return False, "", result.get("error", MSG_INVALID)


def reverify_if_due(force: bool = False) -> str:
    """
    Reverificación automática con el servidor (usa la clave guardada: el usuario no la vuelve a escribir).
    Sin force solo actúa si pasaron REVERIFY_INTERVAL desde la última correcta; con force=True siempre
    (arranque). Reintenta mientras no lo logre.
    Pensada para un hilo en segundo plano: no toca la interfaz.
    Devuelve 'skipped' | 'ok' | 'network' | 'revoked' | 'legacy'.
    Una negativa explícita del servidor (clave desactivada/reembolsada o licencia en otro equipo)
    deja la licencia marcada como revocada: surte efecto en el siguiente arranque.
    """
    local = load_local()
    if local is None:
        return "skipped"
    now = int(time.time())
    if not force and now - int(local.get("last_check", 0)) < REVERIFY_INTERVAL:
        return "skipped"
    from src.licensing.device import get_device_id
    dev = get_device_id()
    blob = local.get("key_enc")
    if not blob or local.get("device") not in (None, dev):
        return "legacy"            # licencia guardada por una versión antigua (sin clave): se renueva al reactivar
    key = _decode_key(blob, dev)
    if not key:
        return "legacy"
    res = verify_online(key, action="verify", device_id=dev)
    if res["success"]:
        local.update({"verified_at": now, "last_check": now, "edition": res["edition"]})
        local.pop("revoked", None)
        _write_local(local)
        return "ok"
    code = res.get("code")
    if code in ("in_use", "invalid"):
        local["revoked"] = code
        _write_local(local)
        return "revoked"
    return "network"               # sin conexión o servidor no disponible: se reintenta en el próximo arranque


def deactivate_online() -> tuple[bool, str]:
    """
    Libera la licencia en el servidor para poder activarla en otro equipo.
    Devuelve (liberada, código): código 'network' si no hubo conexión, 'legacy' si no hay clave guardada.
    """
    local = load_local()
    if local is None:
        return True, "skipped"
    from src.licensing.device import get_device_id
    dev = get_device_id()
    blob = local.get("key_enc")
    key = _decode_key(blob, dev) if blob else ""
    if not key:
        return True, "legacy"
    res = verify_online(key, action="deactivate", device_id=dev)
    if res["success"] or res.get("code") in ("not_owner", "invalid"):
        return True, "ok"          # ya estaba libre / ya no es válida: nada que liberar
    return False, res.get("code", "network")


def revoked_reason() -> str:
    """'' si la licencia local sigue vigente; si el servidor la revocó, el motivo ('in_use' | 'invalid')."""
    local = load_local()
    return str(local.get("revoked") or "") if local else ""
