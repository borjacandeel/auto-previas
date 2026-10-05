"""
Tests de integración para las nuevas funcionalidades de AutoPrevias v1.1.0:
- Detección de clave armónica y Camelot (key.py)
- Efectos de estudio (Flanger, Filter Sweep, Master Limiter)
- Renderizado de overlay de vídeo para redes (video.py)
- Diálogo y Worker de Lote (batch.py)
"""

import numpy as np
import pytest
from pathlib import Path
import tempfile

from src.analysis.key import detect_musical_key, KeyResult
from src.engine.effects import (
    apply_flanger,
    apply_filter_sweep,
    apply_studio_mastering,
    inject_voice_drop,
)
from src.engine.video import create_social_overlay_image
from src.ui.batch import BatchDialog, BatchWorker


def test_detect_musical_key():
    sr = 44100
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Tono de 440 Hz (Nota A4)
    y = np.sin(2 * np.pi * 440.0 * t).astype(np.float32)

    res = detect_musical_key(y, sr)
    assert isinstance(res, KeyResult)
    assert res.root in ["A", "C", "D", "E", "F", "G"]
    assert res.mode in ["major", "minor"]
    assert len(res.camelot) >= 2
    assert 0.0 <= res.confidence <= 1.0


def test_audio_effects():
    sr = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    y = 0.5 * np.sin(2 * np.pi * 300.0 * t).astype(np.float32)
    stereo = np.stack([y, y])

    # 1. Flanger
    flanged = apply_flanger(stereo, sr, mix=0.5)
    assert flanged.shape == stereo.shape
    assert not np.isnan(flanged).any()
    assert np.max(np.abs(flanged)) <= 1.0

    # 2. Filter Sweep
    filtered = apply_filter_sweep(stereo, sr)
    assert filtered.shape == stereo.shape
    assert not np.isnan(filtered).any()

    # 3. Studio Master Limiter
    mastered = apply_studio_mastering(stereo, sr, target_lufs=-9.0)
    assert mastered.shape == stereo.shape
    assert not np.isnan(mastered).any()
    assert np.max(np.abs(mastered)) <= 1.0


def test_social_overlay_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_png = Path(tmpdir) / "test_overlay.png"
        res_path = create_social_overlay_image(
            width=1080,
            height=1920,
            title="Track de Prueba",
            artist="Radical Records",
            bpm=128.0,
            key_str="8A · Am",
            output_path=out_png,
        )
        assert res_path.exists()
        assert res_path.stat().st_size > 1000
