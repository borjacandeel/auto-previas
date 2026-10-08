"""
AutoPrevias — Notificaciones nativas del sistema operativo.
Soporta macOS (osascript) y Windows (PowerShell Toast).
Falla silenciosamente si el sistema no lo admite.
"""
import sys
import subprocess
import threading


def notify(title: str, message: str, sound: bool = True) -> None:
    """Muestra una notificación nativa sin bloquear el hilo principal."""
    threading.Thread(target=_send, args=(title, message, sound), daemon=True).start()


def _send(title: str, message: str, sound: bool) -> None:
    title   = title.replace('"', "'")
    message = message.replace('"', "'")

    if sys.platform == "darwin":
        sound_clause = "sound name \"default\"" if sound else ""
        script = (
            f'display notification "{message}" with title "{title}"'
            + (f' {sound_clause}' if sound_clause else '')
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, timeout=4
            )
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
