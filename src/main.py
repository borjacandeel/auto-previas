#!/usr/bin/env python3
"""AutoPrevias — Radical Records. Punto de entrada principal."""

import sys
import os
import tempfile
import traceback
from pathlib import Path
import time
import multiprocessing
import logging
import logging.handlers

# Prevenir fork-bombs o spawns descontrolados en Windows en ejecutables standalone
multiprocessing.freeze_support()

# Prevenir escritura de .pyc en runtime (crucial para instalaciones en C:\Program Files)
sys.dont_write_bytecode = True

# Registro ultra-inmediato en TEMP
if sys.platform == "win32":
    try:
        _td = os.environ.get("TEMP") or os.environ.get("TMP") or str(Path.home() / "AppData" / "Local" / "Temp")
        with open(os.path.join(_td, "autoprevias_startup.log"), "a", encoding="utf-8") as _f:
            _f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] AutoPrevias entrypoint alcanzado (pid={os.getpid()})\n")
            _f.flush()
    except Exception:
        pass

def _log_startup(msg: str):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    formatted = f"[{ts}] {msg}"
    try:
        print(formatted, flush=True)
    except Exception:
        pass
    if sys.platform == "win32":
        # Escribir a dos ubicaciones seguras: TEMP y LOCALAPPDATA
        targets = []
        temp_dir = os.environ.get("TEMP") or os.environ.get("TMP")
        if temp_dir:
            targets.append(Path(temp_dir) / "autoprevias_startup.log")
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            targets.append(Path(local_app) / "AutoPrevias" / "startup.log")
        for target in targets:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "a", encoding="utf-8", errors="replace") as f:
                    f.write(formatted + "\n")
                    f.flush()
            except Exception:
                pass

# Configuración defensiva de renderizado en Windows (Software OpenGL garantizado para x64 y ARM64 Parallels)
if sys.platform == "win32":
    os.environ["QT_OPENGL"] = "software"
    os.environ["QT_QUICK_BACKEND"] = "software"
    os.environ["QMLSCENE_DEVICE"] = "softwarecontext"
    os.environ["QSG_RHI_BACKEND"] = "software"
    os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["PYTHONUNBUFFERED"] = "1"
    _log_startup(f"AutoPrevias proceso iniciado (pid={os.getpid()})")
    try:
        from PySide6.QtCore import Qt, QCoreApplication
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
        _log_startup("Qt AA_UseSoftwareOpenGL activado.")
    except Exception as _e:
        _log_startup(f"Aviso al configurar AA_UseSoftwareOpenGL: {_e}")

# Capturador global de excepciones para evitar cierre silencioso sin consola
def _global_exception_handler(exc_type, exc_value, exc_tb):
    err_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _log_startup(f"FATAL UNHANDLED EXCEPTION:\n{err_text}")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Error inesperado al ejecutar AutoPrevias:\n\n{exc_value}\n\nDetalles técnicos guardados en:\n%TEMP%\\autoprevias_startup.log\n%LOCALAPPDATA%\\AutoPrevias\\startup.log",
                "AutoPrevias - Error crítico",
                0x10,
            )
        except Exception:
            pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)

# F9 — Crash log con rotación (máx 3 archivos de 512 KB)
def _setup_crash_logger() -> logging.Logger:
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", str(Path.home()))
        log_dir = Path(local) / "AutoPrevias" / "logs"
    else:
        log_dir = Path.home() / "Library" / "Logs" / "AutoPrevias" if sys.platform == "darwin" \
                  else Path.home() / ".local" / "share" / "autoprevias" / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            log_dir / "crashes.log",
            maxBytes=512 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger = logging.getLogger("autoprevias.crash")
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)
        return logger
    except Exception:
        return logging.getLogger("autoprevias.crash")

_crash_logger = _setup_crash_logger()

_orig_excepthook = sys.excepthook

def _global_exception_handler_with_log(exc_type, exc_value, exc_tb):
    try:
        _crash_logger.error("UNHANDLED EXCEPTION", exc_info=(exc_type, exc_value, exc_tb))
    except Exception:
        pass
    _global_exception_handler(exc_type, exc_value, exc_tb)

sys.excepthook = _global_exception_handler_with_log

# Asegurar raíz en sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if not hasattr(sys, "frozen"):
    setattr(sys, "frozen", True)

_log_startup("Aplicando parches de compatibilidad...")
from src.compat import apply_librosa_patches
apply_librosa_patches()

from src.__version__ import __version__


def run_selftest() -> int:
    """
    Ejecuta el auto-test de diagnóstico del motor completo de AutoPrevias.
    Valida importación de dependencias, backend de audio, detección musical,
    procesamiento de señal y exportación a WAV y MP3.
    Retorna 0 si todo es correcto, o 1 en caso de fallo.
    """
    print("=" * 60)
    print(f"AutoPrevias v{__version__} — MODO SELFTEST DE DIAGNÓSTICO")
    print(f"Plataforma: {sys.platform} | Python: {sys.version.split()[0]}")
    print("=" * 60)

    try:
        # 1. Comprobar imports clave
        print("[1/6] Verificando dependencias críticas...")
        import numpy as np
        import scipy
        import soundfile as sf
        import pedalboard
        import librosa
        from PySide6 import QtCore, QtWidgets, QtGui
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        from src.config import get_ffmpeg_path, get_assets_dir, get_cache_dir, load as load_cfg
        from src.analysis.bpm import detect_beat_grid
        from src.analysis.structure import analyze_structure
        from src.analysis.segments import build_preview_plan
        from src.engine.export import build_preview_audio, export_files

        ffmpeg_bin = get_ffmpeg_path()
        assets_dir = get_assets_dir()
        cache_dir = get_cache_dir()

        print(f"  ✓ NumPy: {np.__version__}")
        print(f"  ✓ SciPy: {scipy.__version__}")
        print(f"  ✓ SoundFile: {sf.__version__}")
        print(f"  ✓ Pedalboard: {pedalboard.__version__}")
        librosa_ver = getattr(librosa, "__version__", None)
        if not librosa_ver:
            try:
                import librosa.version
                librosa_ver = librosa.version.version
            except Exception:
                librosa_ver = "0.11.0"
        print(f"  ✓ Librosa: {librosa_ver}")
        print(f"  ✓ Qt: {QtCore.qVersion()} (PySide6)")
        print(f"  ✓ FFmpeg binario: {ffmpeg_bin or 'No detectado (se usará fallback interno)'}")
        print(f"  ✓ Directorio assets: {assets_dir}")
        print(f"  ✓ Directorio caché: {cache_dir}")

        # Actualizador y activación: deben quedar empaquetados en el binario
        from src import update as _upd, updater_core as _upc
        from src.ui import update_dialog as _upd_dlg, activate as _act
        assert _upc.is_newer("2.10.0", "2.9.9") and not _upc.is_newer("2.9.7", "2.9.7")
        assert _upc.installer_asset_name("plus", "darwin", "arm64") == "AutoPrevias-Plus-macOS-arm64.dmg"
        print("  ✓ Actualizador y diálogo de activación empaquetados")

        # Construir widgets reales: detecta crashes del binario compilado (p. ej. pyqtgraph)
        from src.ui.waveform import WaveformWidget
        _wf = WaveformWidget()
        _dlg = _act.ActivationDialog()
        _wf.deleteLater()
        _dlg.deleteLater()
        print("  ✓ Widgets de forma de onda y activación construidos sin crash")

        # Vídeo animado Radical Neón: debe renderizar fotogramas reales en el binario compilado
        from src.engine import video_neon as _vn
        import numpy as _np
        _an = _vn.AudioAnalysis(duration=1.0, n_frames=30, bars=_np.full((30, 44), 0.5, dtype=_np.float32),
                                kick=_np.zeros(30, dtype=_np.float32), energy=_np.full(30, 0.5, dtype=_np.float32), drops=[])
        for _asp in _vn.ASPECTS:
            _r = _vn._Renderer(_an, None, "TEST", "Radical Records", 128.0, "8A · Am", _asp, "crimson", "", "PREVIA EXCLUSIVA", 0.25)
            assert _r.frame(3, 0.1).size
        print("  ✓ Generador de vídeo Radical Neón construye fotogramas en los 3 formatos")

        from src.ui import video_preview as _vp
        assert hasattr(_vp, "VideoPreviewDialog")
        print("  ✓ Vista previa del vídeo empaquetada")

        # Licencia «un equipo por clave»: el identificador de equipo debe poder calcularse en el binario compilado
        from src.licensing.device import get_device_id as _gdi
        from src.licensing import license as _lic
        _did = _gdi()
        assert len(_did) == 64 and _did == _gdi()
        assert _lic._decode_key(_lic._encode_key("TEST-KEY-1234", _did), _did) == "TEST-KEY-1234"
        _act.ActivationDialog(reason="in_use").deleteLater()
        print("  ✓ Identificador de equipo y cifrado local de clave operativos")

        # Funciones 3.1: idioma, presets, historial, licencia y modo promo (panel de resultados real)
        from src import i18n as _i18n, presets as _pre
        from src.engine.effects import promo_tag_times
        from src.ui.about import LicenseDialog
        from src.ui.app import ResultPanel
        from src.ui.history_dialog import HistoryDialog
        from src.ui.presets_bar import PresetBar, SavePresetDialog
        _i18n.set_language("en")
        assert _i18n.translate("▶   GENERAR PREVIA") == "▶   GENERATE PREVIEW"
        _i18n.set_language("es")
        assert _i18n.get_language() == "es" and _i18n.DEFAULT_LANGUAGE == "es"
        assert _pre.slugify("Radical Main") == "Radical Main" and len(promo_tag_times(90.0, 1.5)) >= 3
        _panel = ResultPanel()
        assert "style" in _panel.get_state() and _panel.get_export_options()["promo_mode"] is False
        for _x in (PresetBar(), SavePresetDialog([]), HistoryDialog(plus=True, entries=[], recent_tracks=[]),
                   LicenseDialog(__version__, "plus"), _panel):
            _x.deleteLater()
        print("  ✓ Presets, historial, licencia, idioma y modo promo construidos sin crash")

        try:
            tmp_ctx = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        except TypeError:
            tmp_ctx = tempfile.TemporaryDirectory()

        with tmp_ctx as tmpdir:
            tmp_path = Path(tmpdir)

            # 2. Generar audio sintético
            print("\n[2/6] Generando señal sintética de prueba (15s @ 44.1kHz, 128 BPM)...")
            sr = 44100
            duration = 15.0
            n_samples = int(sr * duration)
            t = np.linspace(0, duration, n_samples, endpoint=False)

            y = 0.3 * np.sin(2 * np.pi * 440 * t)
            beat_interval = int(sr * (60.0 / 128.0))
            for b in range(0, n_samples, beat_interval):
                end_b = min(b + int(sr * 0.08), n_samples)
                t_k = np.linspace(0, 0.08, end_b - b)
                y[b:end_b] += 0.5 * np.sin(2 * np.pi * 80 * t_k) * np.exp(-t_k * 40)

            y = np.clip(y, -1.0, 1.0).astype(np.float32)
            stereo = np.stack([y, y])
            synth_src_wav = tmp_path / "selftest_source.wav"
            sf.write(str(synth_src_wav), stereo.T, sr, subtype="PCM_16")
            print(f"  ✓ Archivo fuente sintético: {synth_src_wav.name} ({duration:.1f}s)")

            # 3. Análisis rítmico y estructural
            print("\n[3/6] Analizando BPM, beat grid y estructura musical...")
            grid = detect_beat_grid(y, sr)
            print(f"  ✓ BPM detectado: {grid.bpm:.1f}")
            structure = analyze_structure(y, sr, grid)
            print(f"  ✓ Secciones detectadas: {len(structure.sections)}")

            # 4. Plan de previa y síntesis de audio
            print("\n[4/6] Generando plan de previa y procesando cortes...")
            plan = build_preview_plan(structure)
            print(f"  ✓ Segmentos en plan: {len(plan.segments)}")

            cfg = load_cfg()
            cfg["preview_min_sec"] = 5.0
            cfg["preview_max_sec"] = 15.0

            preview_audio, preview_sr, seed = build_preview_audio(
                source_path=str(synth_src_wav),
                plan=plan,
                beat_grid=grid,
                cfg=cfg,
            )
            dur_out = preview_audio.shape[1] / preview_sr
            print(f"  ✓ Audio de previa procesado: {dur_out:.2f}s ({preview_audio.shape[0]} canales @ {preview_sr} Hz)")

            # 5. Exportación a WAV y MP3
            print("\n[5/6] Verificando exportación a WAV y MP3...")
            out_stem = tmp_path / "PREVIA - Selftest_Track"
            paths = {
                "wav": out_stem.with_suffix(".wav"),
                "mp3": out_stem.with_suffix(".mp3"),
            }
            exported = export_files(preview_audio, preview_sr, paths)
            assert len(exported) >= 1, "No se generó ningún archivo en exportación"

            for fmt, p in paths.items():
                if not p.exists() or p.stat().st_size == 0:
                    raise RuntimeError(f"Fallo al exportar formato {fmt.upper()}: archivo vacío o no existe")
                print(f"  ✓ {fmt.upper()} generado: {p.name} ({p.stat().st_size} bytes)")

            # 6. Motor de reproducción integrado (QMediaPlayer / QAudioOutput)
            print("\n[6/6] Verificando motor de reproducción de audio (QMediaPlayer / QAudioOutput)...")
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PySide6.QtCore import QUrl
            player = QMediaPlayer()
            audio_out = QAudioOutput()
            player.setAudioOutput(audio_out)
            player.setSource(QUrl.fromLocalFile(str(paths["wav"])))

            import time
            for _ in range(50):
                app.processEvents()
                if player.mediaStatus() in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia, QMediaPlayer.MediaStatus.InvalidMedia):
                    break
                time.sleep(0.02)

            status = player.mediaStatus()
            dev_name = audio_out.device().description() or "Predeterminado"
            print(f"  ✓ Estado backend QMediaPlayer: {status.name} (dispositivo: {dev_name})")
            if status == QMediaPlayer.MediaStatus.InvalidMedia:
                raise RuntimeError("Backend de QtMultimedia reporta InvalidMedia: plugins multimedia no disponibles")

            # Liberar explícitamente el archivo para evitar bloqueos en Windows
            try:
                player.stop()
                player.setSource(QUrl())
                del player
                del audio_out
                import gc
                gc.collect()
                app.processEvents()
            except Exception:
                pass

        print("\n" + "=" * 60)
        print("✓ SELFTEST EXITOSO: Todos los componentes funcionan correctamente.")
        print("=" * 60)
        return 0

    except Exception as e:
        print("\n" + "!" * 60)
        print(f"✗ ERROR EN SELFTEST: {e}")
        traceback.print_exc()
        print("!" * 60)
        return 1


def _start_background_reverify() -> None:
    """Verifica la licencia con el servidor en cada arranque y luego cada 6 h, en un hilo aparte."""
    try:
        import threading
        import time as _time
        from src.licensing.license import reverify_if_due, REVERIFY_INTERVAL

        def _run():
            first = True
            while True:
                try:
                    _log_startup(f"Verificación automática de licencia: {reverify_if_due(force=first)}")
                except Exception as ex:      # nunca debe afectar a la app
                    _log_startup(f"Verificación de licencia falló: {ex}")
                first = False
                _time.sleep(REVERIFY_INTERVAL)

        threading.Thread(target=_run, name="license-reverify", daemon=True).start()
    except Exception as ex:
        _log_startup(f"No se pudo lanzar la verificación de licencia: {ex}")


def _reverify_expired_blocking(app) -> str:
    """
    La última verificación correcta fue hace más de 14 días: se verifica ahora mismo con la clave guardada,
    sin pedírsela al usuario. Si no hay conexión, ofrece reintentar o salir. Devuelve el estado resultante.
    """
    from PySide6.QtWidgets import QMessageBox
    from src import i18n
    from src.licensing.license import check_license, reverify_if_due, LicenseStatus
    while True:
        outcome = reverify_if_due(force=True)
        if outcome == "network":
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("AutoPrevias")
            box.setText(i18n.tr("AutoPrevias necesita conectarse a Internet para verificar tu licencia "
                                "(lleva más de 14 días sin hacerlo).\nComprueba tu conexión y reintenta."))
            retry = box.addButton(i18n.tr("Reintentar"), QMessageBox.AcceptRole)
            box.addButton(i18n.tr("Salir"), QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is retry:
                continue
            return "quit"
        break
    return check_license()[0]


def _check_license_on_startup() -> bool:
    """
    Comprueba la licencia al arrancar. Muestra la pantalla de activación
    si no hay licencia válida. Devuelve True si puede continuar.
    En modo desarrollo (sin BAKED_EDITION) siempre devuelve True.
    """
    try:
        from src.config import _get_baked_edition
        # En desarrollo (sin binario compilado) no bloquear
        if _get_baked_edition() is None:
            return True
    except Exception:
        return True

    try:
        from src import i18n
        i18n.init_from_config()          # el diálogo de activación también respeta el idioma
        i18n.install_auto_translate()
        from src.licensing.license import check_license, LicenseStatus
        from src.config import set_edition

        status, edition = check_license()

        if status == LicenseStatus.EXPIRED:
            # Verificación automática con la clave guardada (solo las licencias de versiones ≤3.1.0, que no
            # guardaban la clave, tendrán que escribirla una vez más)
            from PySide6.QtWidgets import QApplication
            _app0 = QApplication.instance() or QApplication(sys.argv)
            status = _reverify_expired_blocking(_app0)
            if status == "quit":
                return False
            from src.licensing.license import load_local as _ll
            edition = (_ll() or {}).get("edition", edition)

        if status == LicenseStatus.REVOKED:
            # Antes de pedir la clave, se confirma con el servidor: si la marca de revocada fue un error
            # puntual (p. ej. una versión anterior con el servicio caído), se limpia sola y el usuario no escribe nada.
            from src.licensing.license import reverify_if_due
            if reverify_if_due(force=True) == "ok":
                status, edition = check_license()

        if status in (LicenseStatus.VALID, LicenseStatus.GRACE):
            set_edition(edition)
            _start_background_reverify()
            return True

        # Sin licencia o expirada — mostrar pantalla de activación
        from PySide6.QtWidgets import QApplication
        _app = QApplication.instance() or QApplication(sys.argv)

        from src.ui.activate import ActivationDialog
        expired = (status == LicenseStatus.EXPIRED)
        reason = ""
        if status == LicenseStatus.REVOKED:
            from src.licensing.license import load_local
            reason = str((load_local() or {}).get("revoked") or "invalid")
        dlg = ActivationDialog(expired=expired, reason=reason)

        activated_edition = []

        def _on_activated(ed):
            activated_edition.append(ed)

        dlg.activated.connect(_on_activated)
        result = dlg.exec()

        if activated_edition:
            set_edition(activated_edition[0])
            return True

        return False

    except Exception as ex:
        _log_startup(f"Error en verificación de licencia: {ex}")
        # En caso de error inesperado, dejar pasar para no bloquear
        return True


def main():
    _log_startup(f"Iniciando AutoPrevias v{__version__} (argv={sys.argv})")
    _log_startup(f"Plataforma: {sys.platform} | Python: {sys.version.split()[0]}")

    if "--version" in sys.argv or "-v" in sys.argv:
        print(f"AutoPrevias {__version__}")
        sys.exit(0)

    if "--selftest" in sys.argv:
        sys.exit(run_selftest())

    # Forzar edición vía argumento (útil para launchers y pruebas)
    for _arg in sys.argv[1:]:
        if _arg.startswith("--edition="):
            _ed = _arg.split("=", 1)[1].strip().lower()
            if _ed in ("basic", "plus"):
                from src.config import set_edition
                set_edition(_ed)
                _log_startup(f"Edición forzada por argumento: {_ed}")
            break

    target = ""
    for arg in sys.argv[1:]:
        if not arg.startswith("-") and Path(arg).is_file():
            target = arg
            break

    try:
        _log_startup("Importando módulo de interfaz gráfica src.ui.app...")
        from src.ui.app import launch

        # ── Comprobación de licencia ──────────────────────────────────────
        # Solo en builds compilados (BAKED_EDITION presente) o si la config
        # tiene licencia guardada. En modo desarrollo se salta.
        _log_startup("Verificando licencia...")
        _license_ok = _check_license_on_startup()
        if not _license_ok:
            _log_startup("Licencia no válida — cerrando.")
            sys.exit(0)

        _log_startup("Módulo UI cargado. Invocando launch()...")
        launch(target)
    except Exception as e:
        err_msg = f"Error fatal al iniciar AutoPrevias:\n{e}\n\n{traceback.format_exc()}"
        _log_startup(err_msg)
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"Error al iniciar AutoPrevias:\n\n{e}\n\nDetalles técnicos guardados en:\n%TEMP%\\autoprevias_startup.log\n%LOCALAPPDATA%\\AutoPrevias\\startup.log",
                    "AutoPrevias - Error de arranque",
                    0x10,
                )
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()
