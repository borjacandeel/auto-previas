"""
AutoPrevias — Firmar un tema entero (no una previa).

Solo mete la carátula y las etiquetas (artista, sello…) y guarda el tema en FLAC o WAV a máxima calidad:
· NO se masteriza, NO hay efectos, NO se cambia el volumen, la duración ni la frecuencia de muestreo.
· Se conserva la frecuencia de muestreo y los canales del archivo original; la profundidad es la del original
  (16 o 24 bits) y, si el original es de 32 bits o coma flotante, se guarda en 24 bits (el máximo del FLAC).
· Si el original es un MP3/M4A/OGG se decodifica a 24 bits sin tocar nada más (no mejora la calidad, la conserva).
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

import numpy as np

SUPPORTED_FORMATS = ("flac", "wav")
AUDIO_EXTENSIONS = (".wav", ".flac", ".aiff", ".aif", ".mp3", ".m4a", ".ogg", ".opus", ".wma")
LOSSY_EXTENSIONS = (".mp3", ".m4a", ".ogg", ".opus", ".wma")
COVER_SIZE = 1400                     # px (cuadrada) para la carátula incrustada


def unique_path(path: Path) -> Path:
    """Si ya existe, añade « (2)», « (3)»… para no pisar nada."""
    if not path.exists():
        return path
    n = 2
    while True:
        cand = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not cand.exists():
            return cand
        n += 1


def is_lossy(path: str) -> bool:
    return Path(path).suffix.lower() in LOSSY_EXTENSIONS


def probe(path: str) -> dict:
    """Frecuencia, canales, duración y profundidad del original (sin cargarlo entero)."""
    import soundfile as sf
    try:
        info = sf.info(path)
        sub = info.subtype or ""
        bits = {"PCM_16": 16, "PCM_24": 24, "PCM_32": 32, "PCM_S8": 8, "PCM_U8": 8, "FLOAT": 32, "DOUBLE": 64}.get(sub, 24)
        return {"sr": int(info.samplerate), "channels": int(info.channels), "duration": float(info.duration),
                "bits": bits, "subtype": sub, "format": info.format, "readable": True}
    except Exception:
        return {"sr": 0, "channels": 0, "duration": 0.0, "bits": 24, "subtype": "", "format": "", "readable": False}


def _decode_with_ffmpeg(ffmpeg: str, src: str, dst: str) -> None:
    """Decodifica cualquier formato a WAV PCM de 24 bits conservando frecuencia y canales."""
    res = subprocess.run([ffmpeg, "-y", "-v", "error", "-i", src, "-vn", "-c:a", "pcm_s24le", dst],
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if res.returncode != 0 or not Path(dst).exists():
        raise RuntimeError("No se pudo leer el audio: " + res.stderr.decode("utf-8", "ignore").strip()[-200:])


def _to_pcm_wav(src: str, dst: str, info: dict, progress_cb: Optional[Callable[[int], None]] = None) -> int:
    """Copia el audio a un WAV PCM de 16 o 24 bits SIN tocar las muestras (por bloques, sin cargar el tema entero).
    Devuelve la profundidad usada."""
    import soundfile as sf
    bits = 16 if info["bits"] == 16 else 24
    subtype = "PCM_16" if bits == 16 else "PCM_24"
    frames_total = max(1, int(info["duration"] * info["sr"]))
    done = 0
    with sf.SoundFile(src) as fin, sf.SoundFile(dst, "w", samplerate=fin.samplerate, channels=fin.channels,
                                                  format="WAV", subtype=subtype) as fout:
        for block in fin.blocks(blocksize=1 << 20, dtype="float64" if info["bits"] >= 24 else "float32", always_2d=True):
            fout.write(np.clip(block, -1.0, 1.0))
            done += len(block)
            if progress_cb:
                progress_cb(min(99, int(100 * done / frames_total)))
    return bits


# ── Etiquetas ID3 dentro del WAV (FFmpeg no deja adjuntar carátula a un WAV) ─────────────────

def _syncsafe(n: int) -> bytes:
    return bytes([(n >> 21) & 0x7F, (n >> 14) & 0x7F, (n >> 7) & 0x7F, n & 0x7F])


def _frame(fid: str, payload: bytes) -> bytes:
    import struct
    return fid.encode("ascii") + struct.pack(">I", len(payload)) + b"\x00\x00" + payload


def _text_frame(fid: str, text: str) -> bytes:
    return _frame(fid, b"\x01\xff\xfe" + text.encode("utf-16-le") + b"\x00\x00")


def build_id3v23(tags: dict, cover_jpeg: Optional[bytes]) -> bytes:
    """Etiqueta ID3v2.3 con título, artista, álbum, sello, género, comentario, año, BPM, tonalidad y carátula."""
    frames = b""
    for fid, key in (("TIT2", "title"), ("TPE1", "artist"), ("TALB", "album"), ("TPUB", "publisher"),
                     ("TCON", "genre"), ("TYER", "year"), ("TBPM", "bpm"), ("TKEY", "key")):
        v = str(tags.get(key) or "").strip()
        if v:
            frames += _text_frame(fid, v)
    c = str(tags.get("comment") or "").strip()
    if c:
        frames += _frame("COMM", b"\x01eng\xff\xfe\x00\x00\xff\xfe" + c.encode("utf-16-le") + b"\x00\x00")
    if cover_jpeg:
        frames += _frame("APIC", b"\x00image/jpeg\x00\x03\x00" + cover_jpeg)
    return b"ID3\x03\x00\x00" + _syncsafe(len(frames)) + frames


def append_id3_to_wav(wav_path: str, tag: bytes) -> None:
    """Añade el trozo «id3 » al final del WAV y corrige el tamaño de la cabecera RIFF."""
    import struct
    pad = b"\x00" if len(tag) % 2 else b""
    chunk = b"id3 " + struct.pack("<I", len(tag)) + tag + pad
    with open(wav_path, "r+b") as f:
        f.seek(0, os.SEEK_END)
        f.write(chunk)
        f.seek(4)
        riff = struct.unpack("<I", f.read(4))[0]
        f.seek(4)
        f.write(struct.pack("<I", riff + len(chunk)))


def read_source_tags(ffmpeg: str, src: str) -> dict:
    """Etiquetas que ya trae el original (se conservan si no se cambian): título, BPM, tonalidad…"""
    try:
        res = subprocess.run([ffmpeg, "-v", "error", "-i", src, "-f", "ffmetadata", "-"],
                             capture_output=True, timeout=20)
        out = {}
        for line in res.stdout.decode("utf-8", "ignore").splitlines():
            if "=" in line and not line.startswith(";"):
                k, v = line.split("=", 1)
                out[k.strip().lower()] = v.strip()
        return out
    except Exception:
        return {}


def sign_track(
    src_path: str,
    out_dir: str,
    fmt: str = "flac",
    cover_path: Optional[str] = None,
    metadata: Optional[dict] = None,
    progress_cb: Optional[Callable[[int, str], None]] = None,
) -> dict:
    """Firma el tema entero. Devuelve {path, format, sr, bits, channels, cover, warnings}."""
    from src.config import get_ffmpeg_path
    fmt = fmt.lower()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Formato no válido: {fmt}")
    src = str(src_path)
    if not Path(src).is_file():
        raise FileNotFoundError(src)

    def prog(p: int, m: str):
        if progress_cb:
            progress_cb(p, m)

    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError("Falta FFmpeg: sin él no se puede incrustar la carátula.")
    meta = dict(metadata or {})
    warnings = []
    info = probe(src)
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)
    target = unique_path(out_dir_p / f"{Path(src).stem}.{fmt}")

    tmp_files = []
    try:
        # 1) audio de trabajo: WAV PCM 16/24 bits con las mismas muestras que el original
        prog(5, "Leyendo el tema…")
        work = tempfile.NamedTemporaryFile(prefix="autoprevias_sign_", suffix=".wav", delete=False)
        work.close()
        tmp_files.append(work.name)
        if info["readable"] and not is_lossy(src):
            bits = _to_pcm_wav(src, work.name, info, lambda pc: prog(5 + int(pc * 0.45), "Copiando el audio sin tocarlo…"))
            if info["bits"] > 24:
                warnings.append("bits_reducidos")
        else:
            prog(10, "Decodificando el tema…")
            _decode_with_ffmpeg(ffmpeg, src, work.name)
            info = {**info, **probe(work.name)}
            bits = 24
            if is_lossy(src):
                warnings.append("origen_con_perdida")

        # 2) carátula cuadrada (si hay)
        cover = None
        if cover_path and Path(cover_path).is_file():
            from src.engine.export import prepare_cover_art
            cover = prepare_cover_art(cover_path, output_size=COVER_SIZE)
            if cover is None:
                warnings.append("sin_caratula")

        # 3) guardar con carátula y etiquetas (las del original se conservan salvo las que se cambien)
        prog(55, "Incrustando la carátula y las etiquetas…")
        tags = {"title": meta.get("title"), "artist": meta.get("artist"), "album": meta.get("album"),
                "publisher": meta.get("label"), "genre": meta.get("genre"), "comment": meta.get("comment"),
                "date": meta.get("year")}
        if fmt == "flac":
            cmd = [ffmpeg, "-y", "-v", "error", "-i", work.name, "-i", src]
            if cover:
                cmd += ["-i", str(cover)]
            cmd += ["-map", "0:a"]
            if cover:
                cmd += ["-map", "2:v"]
            cmd += ["-map_metadata", "1", "-c:a", "flac", "-compression_level", "8"]
            if cover:
                cmd += ["-c:v", "copy", "-disposition:v:0", "attached_pic"]
            for k, v in tags.items():
                if v is not None and str(v).strip():
                    cmd += ["-metadata", f"{k}={str(v).strip()}"]
            cmd.append(str(target))
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if res.returncode != 0 or not target.exists():
                target.unlink(missing_ok=True)
                raise RuntimeError("No se pudo guardar el archivo: " + res.stderr.decode("utf-8", "ignore").strip()[-200:])
        else:
            import shutil
            shutil.copyfile(work.name, str(target))                    # mismas muestras, sin recodificar
            old_tags = read_source_tags(ffmpeg, src)
            merged = {
                "title": tags["title"] or old_tags.get("title") or Path(src).stem,
                "artist": tags["artist"] or old_tags.get("artist"),
                "album": tags["album"] or old_tags.get("album"),
                "publisher": tags["publisher"] or old_tags.get("publisher") or old_tags.get("label"),
                "genre": tags["genre"] or old_tags.get("genre"),
                "comment": tags["comment"] or old_tags.get("comment"),
                "year": tags["date"] or (old_tags.get("date") or "")[:4],
                "bpm": old_tags.get("tbpm") or old_tags.get("bpm"),
                "key": old_tags.get("tkey") or old_tags.get("initialkey") or old_tags.get("key"),
            }
            jpeg = Path(cover).read_bytes() if cover else None
            append_id3_to_wav(str(target), build_id3v23(merged, jpeg))
        prog(100, "¡Listo!")
        return {"path": str(target), "format": fmt, "sr": info["sr"], "bits": bits, "channels": info["channels"],
                "cover": bool(cover), "warnings": warnings}
    finally:
        for f in tmp_files:
            try:
                os.unlink(f)
            except OSError:
                pass
