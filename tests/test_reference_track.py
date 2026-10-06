"""
Test de validación de estructura sobre pista de referencia real.
Se salta automáticamente si ejemplos/ORIGINAL.wav no está presente en el entorno.
"""

from pathlib import Path
import pytest

REFERENCE_TRACK = Path(__file__).resolve().parent.parent / "ejemplos" / "ORIGINAL.wav"


@pytest.mark.skipif(
    not REFERENCE_TRACK.exists(),
    reason="ejemplos/ORIGINAL.wav no está presente (omitido en CI o clon limpio)"
)
def test_reference_track_structure_and_cuts():
    import soundfile as sf
    from src.analysis.bpm import detect_beat_grid
    from src.analysis.structure import analyze_structure
    from src.analysis.segments import build_preview_plan

    y, sr = sf.read(str(REFERENCE_TRACK))
    if y.ndim > 1:
        y = y.mean(axis=1)

    grid = detect_beat_grid(y, sr)
    assert abs(grid.bpm - 155.0) <= 2.0 or abs(grid.bpm - 77.5) <= 1.0

    structure = analyze_structure(y, sr, grid)
    plan = build_preview_plan(structure, stretch_factor=165.0 / 155.0)

    assert len(plan.segments) == 3, f"Se esperaban 3 cortes, hay {len(plan.segments)}"
