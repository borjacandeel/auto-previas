"""
Tests para funcionalidades de AutoPrevias v2.0:
- Extracción de carátula incrustada (FFmpeg)
- Historial de archivos recientes
- Paletas de vídeo v2.0
- Modos de Speedup DJ (Vinyl armónico vs Keylock Rubber Band)
- Inserción de Voice Drop / Firma Vocal
"""

import tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
import pytest

from src.config import extract_embedded_cover, get_recent_files, add_recent_file
from src.engine.video import PALETTES
from src.engine.export import build_preview_audio
from src.analysis.structure import Section, SectionType
from src.analysis.segments import PreviewPlan, PreviewSegment
from src.analysis.bpm import BeatGrid


def test_video_palettes():
    assert "radical" in PALETTES
    assert "rave" in PALETTES
    assert "crimson" in PALETTES
    assert "amber" in PALETTES
    assert "cyber" in PALETTES
    for k, p in PALETTES.items():
        assert "name" in p
        assert "colors_freq" in p
        assert "colors_wave" in p
        assert "progress_hex" in p


def test_recent_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = Path(tmpdir) / "song1.mp3"
        p2 = Path(tmpdir) / "song2.mp3"
        p1.write_bytes(b"dummy1")
        p2.write_bytes(b"dummy2")

        cfg = {}
        assert get_recent_files(cfg) == []
        add_recent_file(str(p1), cfg)
        assert get_recent_files(cfg) == [str(p1.resolve())]
        add_recent_file(str(p2), cfg)
        assert get_recent_files(cfg) == [str(p2.resolve()), str(p1.resolve())]
        # Re-adding p1 moves it to the front
        add_recent_file(str(p1), cfg)
        assert get_recent_files(cfg) == [str(p1.resolve()), str(p2.resolve())]


def test_extract_embedded_cover():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Archivo sin carátula incrustada debe devolver None limpiamente
        dummy = Path(tmpdir) / "dummy.mp3"
        dummy.write_bytes(b"not an audio with id3 cover")
        res = extract_embedded_cover(str(dummy))
        assert res is None


def _make_dummy_plan_and_grid(sr: int = 44100):
    sec1 = Section(type=SectionType.INTRO, start_time=0.0, end_time=3.0, energy=0.5)
    sec2 = Section(type=SectionType.DROP, start_time=3.0, end_time=6.0, energy=0.9)
    seg1 = PreviewSegment(section=sec1, trimmed_start=0.0, trimmed_end=3.0)
    seg2 = PreviewSegment(section=sec2, trimmed_start=0.0, trimmed_end=3.0)
    plan = PreviewPlan(
        segments=[seg1, seg2],
        estimated_duration_before_stretch=6.0,
        estimated_duration_after_stretch=5.5,
        drop_starts=[3.0],
    )
    beat_times = np.arange(0.0, 6.0, 0.46875)
    grid = BeatGrid(
        bpm=128.0,
        beat_times=beat_times,
        beat_frames=np.arange(len(beat_times)),
        sr=sr,
        hop_length=512,
    )
    return plan, grid


def test_export_vinyl_and_keylock():
    sr = 44100
    t = np.linspace(0, 6.0, int(sr * 6.0), endpoint=False)
    sig = np.sin(2 * np.pi * 440.0 * t).astype(np.float32)
    stereo = np.column_stack([sig, sig])

    plan, grid = _make_dummy_plan_and_grid(sr)

    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "source.wav"
        sf.write(str(src_path), stereo, sr)

        # 1. Vinyl mode
        cfg_vinyl = {
            "speed_mode": "vinyl",
            "tempo_min_pct": 2.0,
            "tempo_max_pct": 8.0,
            "studio_mastering": False,
        }
        out_vinyl, out_sr, _ = build_preview_audio(
            source_path=str(src_path),
            plan=plan,
            beat_grid=grid,
            cfg=cfg_vinyl,
        )
        assert isinstance(out_vinyl, np.ndarray)
        assert out_vinyl.shape[0] == 2
        assert out_vinyl.shape[1] > 0

        # 2. Keylock mode
        cfg_keylock = {
            "speed_mode": "keylock",
            "tempo_min_pct": 2.0,
            "tempo_max_pct": 8.0,
            "studio_mastering": False,
        }
        out_keylock, out_sr, _ = build_preview_audio(
            source_path=str(src_path),
            plan=plan,
            beat_grid=grid,
            cfg=cfg_keylock,
        )
        assert isinstance(out_keylock, np.ndarray)
        assert out_keylock.shape[0] == 2
        assert out_keylock.shape[1] > 0


def test_export_with_voice_drop():
    sr = 44100
    t = np.linspace(0, 6.0, int(sr * 6.0), endpoint=False)
    sig = np.sin(2 * np.pi * 440.0 * t).astype(np.float32)
    stereo = np.column_stack([sig, sig])

    plan, grid = _make_dummy_plan_and_grid(sr)

    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "source.wav"
        sf.write(str(src_path), stereo, sr)

        voice_path = Path(tmpdir) / "voice.wav"
        v_t = np.linspace(0, 0.8, int(sr * 0.8), endpoint=False)
        v_sig = (0.5 * np.sin(2 * np.pi * 880.0 * v_t)).astype(np.float32)
        v_stereo = np.column_stack([v_sig, v_sig])
        sf.write(str(voice_path), v_stereo, sr)

        # Test predrop
        cfg_predrop = {
            "speed_mode": "vinyl",
            "voice_drop_enabled": True,
            "voice_drop_path": str(voice_path),
            "voice_drop_position": "predrop",
            "studio_mastering": False,
        }
        out_pd, _, _ = build_preview_audio(
            source_path=str(src_path),
            plan=plan,
            beat_grid=grid,
            cfg=cfg_predrop,
        )
        assert isinstance(out_pd, np.ndarray)
        assert out_pd.shape[0] == 2

        # Test intro
        cfg_intro = {
            "speed_mode": "vinyl",
            "voice_drop_enabled": True,
            "voice_drop_path": str(voice_path),
            "voice_drop_position": "intro",
            "voice_drop_time_sec": 0.5,
            "studio_mastering": False,
        }
        out_in, _, _ = build_preview_audio(
            source_path=str(src_path),
            plan=plan,
            beat_grid=grid,
            cfg=cfg_intro,
        )
        assert isinstance(out_in, np.ndarray)
        assert out_in.shape[0] == 2
