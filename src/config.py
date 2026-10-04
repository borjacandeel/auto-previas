"""
Configuración persistente de AutoPrevias.
Se guarda en autoprevias_config.json junto al ejecutable/launcher.
"""

import json
from pathlib import Path

# La config vive siempre junto al directorio raíz del proyecto
_CONFIG_PATH = Path(__file__).parent.parent / "autoprevias_config.json"

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
}


def load() -> dict:
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # rellenar claves que falten (migraciones futuras)
            for k, v in _DEFAULTS.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return dict(_DEFAULTS)


def save(cfg: dict) -> None:
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get_output_dir(source_file: str | Path, cfg: dict | None = None) -> Path:
    """
    Devuelve la carpeta donde se guardarán las previas.
    - Si el usuario tiene una carpeta preferida configurada, usa esa.
    - Si no, usa la misma carpeta que el archivo fuente.
    """
    if cfg is None:
        cfg = load()
    preferred = cfg.get("output_dir", "").strip()
    if preferred:
        p = Path(preferred)
        p.mkdir(parents=True, exist_ok=True)
        return p
    return Path(source_file).parent
