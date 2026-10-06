"""
Tests para StereoVUMeter, filtrado DC y exportación mejorada.
"""

import numpy as np
from src.engine.export import _dc_blocker, _soft_limiter
from src.ui.player import StereoVUMeter


def test_dc_blocker_removes_constant_offset():
    # Señal con offset DC constante de +0.5
    t = np.linspace(0, 1.0, 44100, endpoint=False)
    sig = (np.sin(2 * np.pi * 100 * t) + 0.5).astype(np.float32)
    stereo = np.stack([sig, sig])

    filtered = _dc_blocker(stereo, r=0.995)

    # El offset medio de la segunda mitad debe haber caído a prácticamente cero
    mean_dc = np.abs(np.mean(filtered[:, 22050:]))
    assert mean_dc < 0.02


def test_soft_limiter_clamps_peaks():
    # Señal con picos que sobrepasan 0 dB (hasta +3 dB = 1.41)
    stereo = np.array([[1.4, -1.3], [1.2, -1.4]], dtype=np.float32)
    limited = _soft_limiter(stereo, ceiling_db=-0.5)

    ceiling = 10.0 ** (-0.5 / 20.0)
    assert np.max(np.abs(limited)) <= ceiling + 1e-5


def test_stereo_vu_meter_levels():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None

    vu = StereoVUMeter()
    assert vu._lvl_l == 0.0
    assert vu._lvl_r == 0.0

    # Activar con señal a -6 dBFS (~0.5)
    vu.set_levels(0.5, 0.5)
    assert vu._lvl_l >= 0.5
    assert vu._lvl_r >= 0.5

    # Decaimiento
    vu.decay_step()
    assert vu._lvl_l < 0.5

    # Reset
    vu.reset()
    assert vu._lvl_l == 0.0
    assert vu._lvl_r == 0.0


def test_waveform_cut_indicators_and_masks():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None

    from src.ui.waveform import WaveformWidget, START_LINE_COLOR, END_LINE_COLOR
    from src.analysis.structure import Section, SectionType
    from src.analysis.segments import PreviewSegment

    widget = WaveformWidget()
    rms = np.ones(100, dtype=np.float32) * 0.5
    widget._on_source_loaded(rms, duration=100.0)

    sec1 = Section(type=SectionType.BUILDUP, start_time=10.0, end_time=30.0, energy=0.7)
    sec2 = Section(type=SectionType.DROP, start_time=30.0, end_time=60.0, energy=0.95)

    seg1 = PreviewSegment(section=sec1, trimmed_start=5.0, trimmed_end=20.0)
    seg2 = PreviewSegment(section=sec2, trimmed_start=0.0, trimmed_end=25.0)
    widget.set_sections([sec1, sec2], plan_segments=[seg1, seg2])

    # Check cut highlights and badges
    assert len(widget._plan_highlights) == 2
    assert len(widget._cut_badges) == 2

    # Verify green line start and red line end pen colors
    hl0 = widget._plan_highlights[0]
    assert hl0.lines[0].pen.color().getRgb()[:3] == START_LINE_COLOR[:3]
    assert hl0.lines[1].pen.color().getRgb()[:3] == END_LINE_COLOR[:3]

    # Verify omitted masks are generated
    assert len(widget._omitted_masks) >= 1

    # Verify cut region update handler updates badge and mask positions
    widget._on_cut_region_changing(hl0, 0)
    assert widget._dragging is True

    # Verify signal emission on cut change finished
    emitted_cuts = []
    widget.cuts_changed.connect(lambda cuts: emitted_cuts.append(cuts))
    widget._on_cut_region_changed()
    assert len(emitted_cuts) == 1
    assert len(emitted_cuts[0]) == 2

    # Verify update_plan_highlights updates positions
    new_seg1 = PreviewSegment(section=sec1, trimmed_start=6.0, trimmed_end=22.0)
    widget.update_plan_highlights([new_seg1, seg2])
    r0, r1 = widget._plan_highlights[0].getRegion()
    assert abs(r0 - 16.0) < 0.1
    assert abs(r1 - 32.0) < 0.1

    # Verify _clear_all clears everything
    widget._clear_all()
    assert len(widget._plan_highlights) == 0
    assert len(widget._cut_badges) == 0
    assert len(widget._omitted_masks) == 0


def test_branding_and_cover_export(tmp_path):
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None

    from src.engine.export import prepare_cover_art, export_files
    from src.ui.app import BrandingCard
    from PySide6.QtGui import QImage, QColor

    # 1. Crear una imagen cuadrada sintética
    test_img_path = tmp_path / "custom_art.png"
    img = QImage(300, 300, QImage.Format_RGB888)
    img.fill(QColor(255, 46, 77))  # Crimson
    img.save(str(test_img_path), "PNG")

    # 2. Verificar prepare_cover_art
    prepared = prepare_cover_art(test_img_path, output_size=500)
    assert prepared is not None
    assert prepared.exists()
    assert prepared.stat().st_size > 0

    # 3. Verificar BrandingCard
    card = BrandingCard()
    card._drop_area.set_cover(str(test_img_path))
    assert card._drop_area.get_cover_path() == str(test_img_path.resolve())

    card._edit_artist.setText("Radical DJ")
    card._edit_label.setText("Radical Records")
    meta = card.get_metadata()
    assert meta["artist"] == "Radical DJ"
    assert meta["label"] == "Radical Records"

    # 4. Probar export_files con audio sintético y metadata
    sr = 44100
    audio = np.zeros((2, sr * 2), dtype=np.float32)
    paths = {
        "wav": tmp_path / "test_out.wav",
        "mp3": tmp_path / "test_out.mp3",
    }
    meta["bpm"] = 128
    gen = export_files(audio, sr, paths, metadata=meta, cover_image_path=str(test_img_path))
    assert str(paths["wav"]) in gen
    assert str(paths["mp3"]) in gen
    assert paths["wav"].exists() and paths["wav"].stat().st_size > 0
    assert paths["mp3"].exists() and paths["mp3"].stat().st_size > 0


