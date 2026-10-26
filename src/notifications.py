"""
AutoPrevias — Notificaciones del sistema operativo.

· Con la interfaz abierta se usa el sistema de notificaciones de la propia aplicación (`QSystemTrayIcon`):
  sale con el logo de AutoPrevias (`assets/notify_icon.png`, fondo oscuro para que se vea también sobre
  fondos claros) y, **al pulsarla, se abre la carpeta donde está la previa** (Finder / Explorador).
· Si el sistema no permite notificaciones propias (sin bandeja, entorno sin pantalla, otro hilo…) se recurre
  al método antiguo: macOS (osascript) y Windows (PowerShell Toast). Ese método no puede mostrar el logo ni
  reaccionar al clic.
Falla en silencio si el sistema no lo admite.
"""
from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path

_tray = None            # un único icono de notificaciones, reutilizado
_target = ""            # archivo o carpeta que se abre al pulsar la notificación
_hide_seq = 0           # para ocultar el icono solo tras la última notificación


def reveal_in_os(path_or_dir: str) -> bool:
    """Abre la carpeta (o selecciona el archivo) en Finder / Explorador de archivos."""
    if not path_or_dir:
        return False
    try:
        p = Path(path_or_dir)
        if not p.exists():
            p = p.parent
        if not p.exists():
            return False
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(p)] if p.is_file() else ["open", str(p)])
        elif sys.platform == "win32":
            # Cadena completa: con lista, Python entrecomilla todo «/select,ruta con espacios» y el Explorador lo ignora.
            subprocess.Popen(f'explorer /select,"{p}"' if p.is_file() else f'explorer "{p}"')
        else:
            subprocess.Popen(["xdg-open", str(p if p.is_dir() else p.parent)])
        return True
    except Exception:
        return False


def notify_icon_path() -> Path | None:
    """Icono cuadrado de AutoPrevias para las notificaciones."""
    try:
        from src.config import get_assets_dir
        p = Path(get_assets_dir()) / "notify_icon.png"
        return p if p.exists() else None
    except Exception:
        return None


def notify(title: str, message: str, sound: bool = True, folder: str | None = None) -> None:
    """Muestra una notificación. Con `folder` (carpeta o archivo), al pulsarla se abre esa ubicación."""
    try:
        # macOS no enseña los avisos de una app mientras esa app está en primer plano (justo cuando acaba una previa y
        # la app lleva al usuario a los resultados): ahí se usa el aviso de osascript, que sale de otro proceso.
        if not (sys.platform == "darwin" and _app_is_active()) and _show_with_tray(title, message, folder):
            return
    except Exception:
        pass
    threading.Thread(target=_send, args=(title, message, sound), daemon=True).start()


def _app_is_active() -> bool:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        return app is not None and app.applicationState() == Qt.ApplicationActive
    except Exception:
        return False


# ── Notificación propia de la aplicación (logo + clic) ────────────────────────────────────

def _make_tray():
    """Crea el icono de notificaciones (se separa para poder sustituirlo en las pruebas)."""
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon
    app = QApplication.instance()
    if app is None or not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    p = notify_icon_path()
    return QSystemTrayIcon(QIcon(str(p)) if p else QIcon(), app)


def _show_with_tray(title: str, message: str, folder: str | None) -> bool:
    global _tray, _target, _hide_seq
    from PySide6.QtCore import QThread, QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None or QThread.currentThread() is not app.thread():
        return False
    if _tray is None:
        _tray = _make_tray()
        if _tray is None:
            return False
        _tray.messageClicked.connect(_on_clicked)
    from PySide6.QtGui import QIcon
    p = notify_icon_path()
    icon = QIcon(str(p)) if p else QIcon()
    _target = folder or ""
    _tray.setIcon(icon)
    _tray.setToolTip("AutoPrevias")
    _tray.show()
    _tray.showMessage(title, message, icon, 10000)
    _hide_seq += 1
    seq = _hide_seq
    QTimer.singleShot(20000, lambda: _hide_tray(seq))        # el icono de la bandeja no se queda puesto
    return True


def _hide_tray(seq: int | None = None) -> None:
    if _tray is not None and (seq is None or seq == _hide_seq):
        try:
            _tray.hide()
        except Exception:
            pass


def _on_clicked() -> None:
    target = _target
    _hide_tray()
    reveal_in_os(target)


# ── Método antiguo (sin logo ni clic) ──────────────────────────────────────────────────────

def _send(title: str, message: str, sound: bool) -> None:
    title = title.replace("\\", " ").replace('"', "'")
    message = message.replace("\\", " ").replace('"', "'")
    if sys.platform == "win32":                       # en PowerShell «$» y «`» dentro de comillas dobles se interpretan
        title = title.replace("$", " ").replace("`", "'")
        message = message.replace("$", " ").replace("`", "'")

    if sys.platform == "darwin":
        sound_clause = "sound name \"default\"" if sound else ""
        script = (
            f'display notification "{message}" with title "{title}"'
            + (f' {sound_clause}' if sound_clause else '')
        )
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=4)
        except Exception:
            pass

    elif sys.platform == "win32":
        ps = f"""
Add-Type -AssemblyName Windows.UI 2>$null
try {{
    [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime]
    $tmpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
        [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $nodes = $tmpl.GetElementsByTagName('text')
    $nodes.Item(0).AppendChild($tmpl.CreateTextNode("{title}")) | Out-Null
    $nodes.Item(1).AppendChild($tmpl.CreateTextNode("{message}")) | Out-Null
    $notif = [Windows.UI.Notifications.ToastNotification]::new($tmpl)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("AutoPrevias").Show($notif)
}} catch {{ }}
"""
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True, timeout=6
            )
        except Exception:
            pass
