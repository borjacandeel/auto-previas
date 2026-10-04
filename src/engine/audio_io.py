"""
AutoPrevias — audio_io.py
Carga robusta y reparación automática de archivos de audio (WAV, MP3, FLAC, AIFF, OGG).
Soluciona bugs de renderizado de DAWs (FL Studio, Ableton, Cubase) como cabeceras WAV
con chunk 'data' corrupto o truncado.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import struct
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Chunks reconocidos como trailers después de los datos PCM en archivos WAV/RIFF
WAV_TRAILER_CHUNK_IDS = (
    b"smpl",
    b"LIST",
    b"id3 ",
    b"ID3 ",
    b"bext",
    b"cue ",
    b"cart",
    b"DISP",
    b"acid",
    b"inst",
    b"note",
    b"labl",
    b"ltxt",
    b"JUNK",
)


def repair_wav_header_if_needed(path: str) -> bool:
    """
    Inspecciona archivos WAV y repara en caliente la cabecera si el tamaño declarado
    del chunk 'data' está truncado o corrupto respecto al audio real del archivo
    (típico de exportaciones interrumpidas o bugs de cabecera en DAWs como FL Studio).
    
    Retorna True si el archivo fue reparado, False si ya era correcto o no requería acción.
    """
    try:
        p = Path(path)
        if not p.is_file():
            return False

        file_size = p.stat().st_size
        if file_size < 128:
            return False

        with open(p, "rb") as f:
            riff = f.read(12)
            if len(riff) < 12 or riff[:4] != b"RIFF" or riff[8:12] != b"WAVE":
                return False

            fmt_info = None
            data_pos = None
            declared_data_size = None
            data_start = None

            while True:
                h = f.read(8)
                if len(h) < 8:
                    break
                cid, csz = struct.unpack("<4sI", h)
                if cid == b"fmt ":
                    fmt_data = f.read(csz)
                    if len(fmt_data) >= 16:
                        tag, channels, sr, byterate, align, bits = struct.unpack(
                            "<HHIIHH", fmt_data[:16]
                        )
                        fmt_info = {
                            "tag": tag,
                            "channels": channels,
                            "sr": sr,
                            "align": align,
                            "bits": bits,
                        }
                    continue
                elif cid == b"data":
                    data_pos = f.tell() - 4
                    declared_data_size = csz
                    data_start = f.tell()
                    break
                else:
                    if csz % 2 == 1:
                        csz += 1
                    f.seek(csz, 1)

            if data_pos is None or data_start is None or not fmt_info:
                return False

            align = fmt_info.get("align", 4) or 4

            # Buscar chunks trailers posteriores al audio en los últimos 512 KB
            scan_len = min(file_size - data_start, 512 * 1024)
            if scan_len <= 0:
                return False

            f.seek(file_size - scan_len)
            tail_buf = f.read(scan_len)
            tail_start_abs = file_size - scan_len

            trailer_pos = file_size
            for i in range(0, scan_len - 8, 2):
                cid = tail_buf[i : i + 4]
                if cid in WAV_TRAILER_CHUNK_IDS:
                    csz = struct.unpack("<I", tail_buf[i + 4 : i + 8])[0]
                    chunk_abs = tail_start_abs + i
                    # Verificar que el chunk trailer encaje dentro del archivo
                    if chunk_abs + 8 + csz <= file_size + 1:
                        if chunk_abs > data_start and chunk_abs < trailer_pos:
                            trailer_pos = chunk_abs

            actual_data_len = trailer_pos - data_start
            actual_data_len = (actual_data_len // align) * align

            # Si el tamaño real supera al declarado por más de un bloque de audio,
            # la cabecera está defectuosa y truncando el archivo
            if actual_data_len <= declared_data_size + align:
                return False

        # Aplicar reparación in-place
        with open(p, "r+b") as f:
            f.seek(data_pos)
            f.write(struct.pack("<I", actual_data_len))

            riff_size = file_size - 8
            f.seek(4)
            f.write(struct.pack("<I", riff_size))

        logger.info(
            f"Cabecera WAV reparada automáticamente para {p.name}: "
            f"tamaño data corregido de {declared_data_size} a {actual_data_len} bytes."
        )
        return True

    except (PermissionError, OSError) as e:
        logger.warning(f"No se pudo escribir reparación de cabecera en {path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado al inspeccionar cabecera WAV {path}: {e}")
        return False


def load_audio_file(
    path: str,
    sr: Optional[int] = None,
    mono: bool = True,
    dtype: np.dtype = np.float32,
) -> Tuple[np.ndarray, int]:
    """
    Carga cualquier archivo de audio de forma ultrarrápida y a prueba de fallos.
    
    1. Repara automáticamente cabeceras WAV truncadas o defectuosas.
    2. Utiliza soundfile en C como ruta principal ultrarrápida.
    3. Fallback a pedalboard.io para MP3 y formatos complejos.
    4. Fallback a librosa.
    5. Realiza resampleado preciso si `sr` está especificado.
    6. Valida que el audio tenga una duración mínima suficiente para análisis.
    """
    import librosa
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Archivo de audio no encontrado: {path}")

    # Reparar cabecera WAV si es necesario
    repair_wav_header_if_needed(path)

    y: Optional[np.ndarray] = None
    native_sr: int = 44100

    # 1. soundfile (C libsndfile) — <20ms para WAV/FLAC
    try:
        import soundfile as sf
        data, native_sr = sf.read(path, dtype="float32", always_2d=True)
        if len(data) > 0:
            if mono:
                y = np.mean(data, axis=1) if data.shape[1] > 1 else data[:, 0]
            else:
                y = data.T  # shape (channels, N)
    except Exception:
        y = None

    # 2. pedalboard.io — carga limpia para MP3 sin spawn de ffmpeg
    if y is None or (y.ndim == 1 and len(y) < 100) or (y.ndim > 1 and y.shape[-1] < 100):
        try:
            import pedalboard.io
            with pedalboard.io.AudioFile(path) as f:
                data = f.read(f.frames)
                native_sr = f.samplerate
                if mono:
                    y = np.mean(data, axis=0) if data.ndim > 1 else data
                else:
                    y = data
        except Exception:
            y = None

    # 3. Fallback a librosa.load
    if y is None or (y.ndim == 1 and len(y) < 100) or (y.ndim > 1 and y.shape[-1] < 100):
        y, native_sr = librosa.load(path, sr=None, mono=mono, dtype=dtype)

    # 4. Resampleado si es necesario
    if sr is not None and sr != native_sr:
        y = librosa.resample(y, orig_sr=native_sr, target_sr=sr)
        native_sr = sr

    # Asegurar tipo de datos
    y = np.asarray(y, dtype=dtype)

    # 5. Comprobar que el audio tenga una longitud viable
    sample_count = len(y) if y.ndim == 1 else y.shape[-1]
    if sample_count < 2048:
        raise ValueError(
            f"El archivo '{p.name}' contiene solo {sample_count} muestras "
            f"({sample_count / max(native_sr, 1):.3f}s), insuficiente para análisis musical."
        )

    return y, native_sr
