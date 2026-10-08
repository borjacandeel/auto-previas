"""
Configuración persistente y resolución de rutas de AutoPrevias.
- Las preferencias se guardan en las carpetas de usuario estándar:
  * macOS: ~/Library/Application Support/AutoPrevias/autoprevias_config.json
  * Windows: %APPDATA%/AutoPrevias/autoprevias_config.json
  * Linux: ~/.config/autoprevias/autoprevias_config.json
- Soporta búsqueda de FFmpeg en el bundle empaquetado antes de recurrir al PATH.
- Resolución de assets dinámica para ejecutables compilados con Nuitka/PyInstaller y modo desarrollo.
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

_DEFAULTS = {
    "output_dir": "",          # vacío = misma carpeta que el archivo fuente
    "export_mp3": True,
    "export_wav": True,
    "mp3_bitrate": 320,
    "wav_bit_depth": 24,
    "fade_in_sec": 2.0,
    "fade_out_sec": 4.0,
    "tempo_min_pct": 0.0,
    "tempo_max_pct": 3.0,
    "preview_min_sec": 90.0,
    "preview_max_sec": 120.0,  # 2 minutos máx por defecto
    "default_preset_sec": 120,
    # Aceleración DJ v2.0: Vinilo analógico (+pitch armónico) vs Keylock digital
    "speed_mode": "vinyl",     # "vinyl" o "keylock"
    # Vídeo viral v2.0
    "video_palette": "radical",  # "radical", "rave", "crimson", "amber", "cyber"
    "video_promo_text": "RADICAL RECORDS · PROMO EXCLUSIVA",
    # Firma de voz / Voice drop v2.0
    "voice_drop_enabled": False,
    "voice_drop_path": "",
    "voice_drop_position": "predrop",  # "predrop" o "intro"
    "voice_drop_volume_db": -1.5,
    # Automatización y lote v2.0
    "watch_folder_enabled": False,
    "watch_folder_path": "",
    "recent_files": [],
    # Firma y metadatos de audio personalizados
    "tag_artist": "",
    "tag_label": "",
    "tag_album": "",
    "tag_genre": "Electronic",
    "tag_comment": "AutoPrevias · Radical Records Studio",
    "custom_cover_path": "",
    "save_signature_default": False,
    # Edición del producto: "plus" (completa) o "basic" (limitada)
    # La licencia sobreescribirá este valor al activarse.
    "edition": "plus",
    # Formatos de exportación adicionales
    "export_flac": False,
    "export_aiff": False,
    "export_video": False,
    "aspect_ratio": "9:16",
    # FX checkboxes
    "fx_flanger": False,
    "fx_filter_sweep": False,
    "studio_mastering": True,
}


def get_user_data_dir() -> Path:
    """Devuelve el directorio de datos de usuario con permisos de escritura."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "AutoPrevias"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata) / "AutoPrevias"
        else:
            base = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "AutoPrevias"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg_config) / "autoprevias" if xdg_config else Path.home() / ".config" / "autoprevias"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:
        base = Path(tempfile.gettempdir()) / "AutoPrevias"
        base.mkdir(parents=True, exist_ok=True)
    return base


def get_cache_dir() -> Path:
    """Devuelve el directorio de caché para archivos temporales de audio/exportación."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches" / "AutoPrevias"
    elif sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            base = Path(localappdata) / "AutoPrevias" / "Cache"
        else:
            base = Path(tempfile.gettempdir()) / "AutoPrevias" / "Cache"
    else:
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        base = Path(xdg_cache) / "autoprevias" if xdg_cache else Path.home() / ".cache" / "autoprevias"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except Exception:
        base = Path(tempfile.gettempdir()) / "AutoPrevias" / "Cache"
        base.mkdir(parents=True, exist_ok=True)
    return base


def get_config_path() -> Path:
    """Ruta del archivo de configuración."""
    is_standalone = getattr(sys, "frozen", False) or hasattr(sys, "__compiled__")
    if not is_standalone:
        dev_local = Path(__file__).resolve().parent.parent / "autoprevias_config.json"
        if dev_local.exists():
            return dev_local
    return get_user_data_dir() / "autoprevias_config.json"


def get_assets_dir() -> Path:
    """
    Localiza la carpeta assets/ tanto en entorno de desarrollo
    como dentro de bundles compilados (Nuitka / PyInstaller / .app).
    """
    # 1. Chequear ejecutables congelados
    if getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"):
        exe_dir = Path(sys.executable).parent
        candidates = [
            exe_dir / "assets",
            exe_dir.parent / "Resources" / "assets",
            exe_dir / ".." / "Resources" / "assets",
            Path(getattr(sys, "_MEIPASS", exe_dir)) / "assets",
        ]
        for cand in candidates:
            if cand.exists() and cand.is_dir():
                return cand.resolve()

    # 2. Directorio relativo al código fuente (src/config.py -> ../assets)
    src_assets = Path(__file__).resolve().parent.parent / "assets"
    if src_assets.exists() and src_assets.is_dir():
        return src_assets.resolve()

    # 3. Fallbacks
    exe_assets = Path(sys.executable).parent / "assets"
    if exe_assets.exists() and exe_assets.is_dir():
        return exe_assets.resolve()

    cwd_assets = Path.cwd() / "assets"
    if cwd_assets.exists() and cwd_assets.is_dir():
        return cwd_assets.resolve()

    return src_assets


def get_ffmpeg_path() -> str | None:
    """
    Busca el binario de FFmpeg primero dentro del bundle/carpeta de la aplicación,
    y si no lo encuentra, en el PATH del sistema operativo.
    """
    exe_dir = Path(sys.executable).parent
    root_dir = Path(__file__).resolve().parent.parent

    bundle_candidates = [
        # Junto al ejecutable (Windows dist o macOS bundle Contents/MacOS)
        exe_dir / "ffmpeg",
        exe_dir / "ffmpeg.exe",
        exe_dir / "bin" / "ffmpeg",
        exe_dir / "bin" / "ffmpeg.exe",
        exe_dir / "ffmpeg_bin" / "ffmpeg",
        exe_dir / "ffmpeg_bin" / "ffmpeg.exe",
        # En Resources de macOS .app
        exe_dir.parent / "Resources" / "ffmpeg",
        exe_dir.parent / "Resources" / "bin" / "ffmpeg",
        # En la raíz del proyecto (desarrollo o build Nuitka)
        root_dir / "ffmpeg_bin" / "ffmpeg",
        root_dir / "ffmpeg_bin" / "ffmpeg.exe",
        root_dir / "bin" / "ffmpeg",
        root_dir / "bin" / "ffmpeg.exe",
    ]

    for cand in bundle_candidates:
        if cand.exists() and cand.is_file():
            if sys.platform != "win32":
                try:
                    os.chmod(cand, 0o755)
                except Exception:
                    pass
            return str(cand.resolve())

    # 2. PATH del sistema
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    # 3. Rutas estándar en macOS (Homebrew)
    if sys.platform == "darwin":
        for brew_path in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
            p = Path(brew_path)
            if p.exists() and p.is_file():
                return str(p.resolve())

    return None


def load() -> dict:
    cfg_file = get_config_path()
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in _DEFAULTS.items():
                data.setdefault(k, v)
            return data
        except Exception as e:
            # JSON corrupto: hacer backup antes de devolver defaults
            print(f"Advertencia: config corrupta ({e}), usando valores por defecto.")
            try:
                backup = cfg_file.with_suffix(".bak")
                shutil.copy2(str(cfg_file), str(backup))
            except Exception:
                pass
    return dict(_DEFAULTS)


def save(cfg: dict) -> None:
    cfg_file = get_config_path()
    tmp_file = cfg_file.with_suffix(".tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        tmp_file.replace(cfg_file)  # operación atómica en la mayoría de sistemas
    except Exception as e:
        print(f"Advertencia: No se pudo guardar configuración en {cfg_file}: {e}")
        try:
            tmp_file.unlink(missing_ok=True)
        except Exception:
            pass


def get_output_dir(source_file: str | Path, cfg: dict | None = None) -> Path:
    """
    Devuelve la carpeta de destino donde se guardarán las previas.
    Por defecto, crea y utiliza una subcarpeta organizada llamada 'Previas'
    dentro del directorio de origen de la pista (o dentro de la ruta configurada).
    """
    if cfg is None:
        cfg = load()
    preferred = cfg.get("output_dir", "").strip()
    if preferred:
        p = Path(preferred)
        if p.name.lower() != "previas":
            p = p / "Previas"
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass
    if source_file and str(source_file).strip():
        p_src = Path(source_file)
        src_parent = p_src if p_src.is_dir() else p_src.parent
        out_p = src_parent / "Previas"
        try:
            out_p.mkdir(parents=True, exist_ok=True)
            return out_p
        except Exception:
            return src_parent
    fallback = Path.cwd() / "Previas"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    except Exception:
        return Path.cwd()


def get_active_cover_path(cfg: dict | None = None) -> Path:
    """
    Devuelve la carátula activa:
    1. Si hay una carátula personalizada en config y existe en disco, se devuelve esa.
    2. En su defecto, devuelve el logotipo emblem oficial de assets/.
    """
    if cfg is None:
        cfg = load()
    custom = cfg.get("custom_cover_path", "").strip()
    if custom:
        p = Path(custom)
        if p.exists() and p.is_file():
            return p.resolve()

    assets = get_assets_dir()
    for name in ["logo_emblem.png", "logo_emblem_red.png", "logo_banner.png"]:
        p = assets / name
        if p.exists() and p.is_file():
            return p.resolve()

    return assets / "logo_emblem.png"


def save_custom_cover(src_image_path: str | Path) -> str:
    """
    Guarda una imagen personalizada en el directorio de datos de usuario de AutoPrevias
    para que persista permanentemente y no dependa de carpetas temporales.
    """
    src = Path(src_image_path).resolve()
    if not src.exists() or not src.is_file():
        return ""

    user_dir = get_user_data_dir()
    ext = src.suffix.lower() if src.suffix else ".jpg"
    dest = user_dir / f"user_cover{ext}"
    try:
        shutil.copy2(src, dest)
        return str(dest.resolve())
    except Exception as e:
        print(f"Advertencia: No se pudo guardar carátula en {dest}: {e}")
        return str(src)


def extract_embedded_cover(audio_path: str | Path) -> Path | None:
    """
    Extrae la carátula incrustada en un archivo de audio (MP3, FLAC, M4A, AIFF, WAV con ID3)
    utilizando FFmpeg. Si se detecta una imagen válida, la almacena en el directorio
    de datos de usuario como 'embedded_cover.jpg' y devuelve su Path.
    Si no contiene carátula o falla la extracción, devuelve None.
    """
    src_p = Path(audio_path).resolve()
    if not src_p.exists() or not src_p.is_file():
        return None

    ffmpeg_bin = get_ffmpeg_path()
    if not ffmpeg_bin:
        return None

    user_dir = get_user_data_dir()
    dest = user_dir / f"embedded_cover_{os.getpid()}.jpg"

    # Intentar extracción directa con copia de códec o transcodificación mjpeg
    cmds = [
        [ffmpeg_bin, "-y", "-i", str(src_p), "-an", "-vcodec", "copy", str(dest)],
        [ffmpeg_bin, "-y", "-i", str(src_p), "-an", "-frames:v", "1", str(dest)],
    ]

    for cmd in cmds:
        try:
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
            if res.returncode == 0 and dest.exists() and dest.stat().st_size > 1024:
                # Normalizar a nombre permanente para la sesión
                perm_dest = user_dir / "session_embedded_cover.jpg"
                shutil.move(str(dest), str(perm_dest))
                return perm_dest.resolve()
        except Exception:
            pass

    if dest.exists():
        try:
            dest.unlink()
        except Exception:
            pass
    return None


def get_recent_files(cfg: dict | None = None) -> list[str]:
    """Devuelve la lista de archivos de audio procesados recientemente que todavía existen en disco."""
    if cfg is None:
        cfg = load()
    recents = cfg.get("recent_files", [])
    valid = []
    for item in recents:
        if item and Path(item).exists() and item not in valid:
            valid.append(str(Path(item).resolve()))
    return valid[:10]


def add_recent_file(file_path: str | Path, cfg: dict | None = None) -> list[str]:
    """Añade un archivo de audio a la lista de temas recientes y guarda la configuración."""
    p = str(Path(file_path).resolve())
    if cfg is None:
        cfg = load()
    current = cfg.get("recent_files", [])
    updated = [p] + [f for f in current if f != p and Path(f).exists()]
    cfg["recent_files"] = updated[:10]
    save(cfg)
    return cfg["recent_files"]


# ── Edición del producto ──────────────────────────────────────────────────────

def _get_baked_edition() -> str | None:
    """
    Devuelve la edición horneada en el binario en tiempo de compilación, o None
    si se está ejecutando desde el código fuente (entorno de desarrollo).
    El archivo src/_edition.py lo genera el CI antes de compilar con Nuitka
    y nunca se sube al repositorio (está en .gitignore).
    """
    try:
        from src._edition import BAKED_EDITION  # type: ignore[import]
        if BAKED_EDITION in ("basic", "plus"):
            return BAKED_EDITION
    except ImportError:
        pass
    return None


def get_edition() -> str:
    """
    Devuelve la edición activa.
    Orden de prioridad:
      1. BAKED_EDITION del binario compilado (inmutable, no sobreescribible)
      2. Campo 'edition' del JSON de configuración del usuario
      3. 'plus' por defecto en modo desarrollo
    """
    baked = _get_baked_edition()
    if baked is not None:
        return baked
    return load().get("edition", "plus")


def set_edition(edition: str) -> None:
    """
    Establece la edición en el JSON de configuración.
    En builds compilados (BAKED_EDITION presente) esta función no tiene efecto
    sobre la edición real — solo persiste el valor para coherencia con el sistema
    de licencias, que lo usará cuando BAKED_EDITION no esté presente.
    """
    if edition not in ("basic", "plus"):
        raise ValueError(f"Edición desconocida: {edition!r}")
    cfg = load()
    cfg["edition"] = edition
    save(cfg)


def is_plus() -> bool:
    return get_edition() == "plus"


def is_basic() -> bool:
    return get_edition() == "basic"
