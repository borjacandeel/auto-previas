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
    "tempo_max_pct": 15.0,
    "preview_min_sec": 120.0,
    "preview_max_sec": 180.0,
    # Firma y metadatos de audio personalizados
    "tag_artist": "",
    "tag_label": "",
    "tag_album": "",
    "tag_genre": "Electronic",
    "tag_comment": "AutoPrevias · Radical Records Studio",
    "custom_cover_path": "",
    "save_signature_default": False,
}


def get_user_data_dir() -> Path:
    """Devuelve el directorio de datos de usuario con permisos de escritura."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "AutoPrevias"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) / "AutoPrevias" if appdata else Path.home() / "AppData" / "Roaming" / "AutoPrevias"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg_config) / "autoprevias" if xdg_config else Path.home() / ".config" / "autoprevias"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_cache_dir() -> Path:
    """Devuelve el directorio de caché para archivos temporales de audio/exportación."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches" / "AutoPrevias"
    elif sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        base = Path(localappdata) / "AutoPrevias" / "Cache" if localappdata else Path.home() / "AppData" / "Local" / "AutoPrevias" / "Cache"
    else:
        xdg_cache = os.environ.get("XDG_CACHE_HOME")
        base = Path(xdg_cache) / "autoprevias" if xdg_cache else Path.home() / ".cache" / "autoprevias"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_config_path() -> Path:
    """Ruta del archivo de configuración."""
    # En desarrollo local, si existe en la raíz del repo y no estamos compilados, usar local
    dev_local = Path(__file__).resolve().parent.parent / "autoprevias_config.json"
    if not getattr(sys, "frozen", False) and dev_local.exists():
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
        except Exception:
            pass
    return dict(_DEFAULTS)


def save(cfg: dict) -> None:
    cfg_file = get_config_path()
    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Advertencia: No se pudo guardar configuración en {cfg_file}: {e}")


def get_output_dir(source_file: str | Path, cfg: dict | None = None) -> Path:
    if cfg is None:
        cfg = load()
    preferred = cfg.get("output_dir", "").strip()
    if preferred:
        p = Path(preferred)
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass
    return Path(source_file).parent


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
