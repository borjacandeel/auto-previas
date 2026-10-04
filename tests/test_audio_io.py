"""
Pruebas unitarias para audio_io: carga robusta y reparación de cabeceras WAV.
"""

from pathlib import Path
import struct
import tempfile
import numpy as np
import pytest
import soundfile as sf

from src.engine.audio_io import load_audio_file, repair_wav_header_if_needed


def test_load_valid_audio():
    sr = 44100
    dur = 1.0
    samples = int(sr * dur)
    t = np.linspace(0, dur, samples, endpoint=False)
    sig = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    try:
        sf.write(tmp_path, sig, sr, subtype="FLOAT")
        y, loaded_sr = load_audio_file(tmp_path, sr=22050, mono=True)
        assert loaded_sr == 22050
        assert len(y) == 22050
        assert isinstance(y, np.ndarray)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_repair_and_load_truncated_header_wav():
    """Simula un WAV exportado por FL Studio con chunk 'data' corrupto/truncado."""
    sr = 48000
    dur = 2.0
    samples = int(sr * dur)
    stereo_sig = np.zeros((samples, 2), dtype=np.float32)
    stereo_sig[:, 0] = 0.5 * np.sin(2 * np.pi * 220 * np.linspace(0, dur, samples, endpoint=False))
    stereo_sig[:, 1] = 0.5 * np.cos(2 * np.pi * 220 * np.linspace(0, dur, samples, endpoint=False))

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    try:
        sf.write(tmp_path, stereo_sig, sr, subtype="FLOAT")
        assert Path(tmp_path).stat().st_size > 1000

        # Corromper el tamaño del chunk 'data' a solo 76 bytes
        with open(tmp_path, "r+b") as f:
            content = f.read()
            dpos = content.find(b"data")
            assert dpos != -1
            f.seek(dpos + 4)
            f.write(struct.pack("<I", 76))

        # Verificar que soundfile estándar solo leería 9 frames
        data_corrupt, _ = sf.read(tmp_path)
        assert len(data_corrupt) < 20

        # Probar reparación automática y carga
        repaired = repair_wav_header_if_needed(tmp_path)
        assert repaired is True

        y, loaded_sr = load_audio_file(tmp_path, sr=48000, mono=False)
        assert y.shape == (2, samples)
        assert loaded_sr == 48000
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_short_audio_raises_value_error():
    """Un audio menor a 2048 muestras debe lanzar ValueError claro."""
    sr = 22050
    sig = np.zeros(50, dtype=np.float32)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    try:
        sf.write(tmp_path, sig, sr, subtype="PCM_16")
        with pytest.raises(ValueError, match="insuficiente para análisis musical"):
            load_audio_file(tmp_path, mono=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_missing_file_raises_not_found():
    with pytest.raises(FileNotFoundError):
        load_audio_file("/ruta/inexistente/cancion_fantasma.wav")
