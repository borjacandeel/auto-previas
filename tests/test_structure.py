"""
Tests para detección de estructura y selección de segmentos.
Usa audio sintético con secciones de energía conocida.
"""

import numpy as np
from src.analysis.bpm import detect_beat_grid, SR_ANALYSIS
from src.analysis.structure import analyze_structure, SectionType
from src.analysis.segments import build_preview_plan


SR = SR_ANALYSIS


def _sine_burst(freq: float, duration: float, amplitude: float, sr: int = SR) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _make_synthetic_track() -> tuple:
    """
    Pista sintética con estructura clara:
    intro(15s) + buildup(8s) + drop(32s) + breakdown(16s) + buildup(8s) + drop(32s) + outro(10s)
    Total: ~121s (2:01)
    """
    sr = SR
    bpm = 128.0

    # intro: tono suave
    intro = _sine_burst(440, 15.0, 0.05)
    # buildup: tono medio con crescendo
    bu1 = _sine_burst(440, 8.0, 0.3)
    # drop: tono fuerte con componente de graves (60 Hz)
    drop1 = (
        _sine_burst(440, 32.0, 0.6)
        + _sine_burst(60, 32.0, 0.5)  # bombo simulado
    ).clip(-1, 1)
    # breakdown
    bd = _sine_burst(440, 16.0, 0.1)
    # buildup 2
    bu2 = _sine_burst(440, 8.0, 0.35)
    # drop 2
    drop2 = (
        _sine_burst(440, 32.0, 0.6)
        + _sine_burst(60, 32.0, 0.5)
    ).clip(-1, 1)
    # outro
    outro = _sine_burst(440, 10.0, 0.05)

    y = np.concatenate([intro, bu1, drop1, bd, bu2, drop2, outro]).astype(np.float32)
    return y, sr


def test_structure_detects_drops():
    y, sr = _make_synthetic_track()
    grid = detect_beat_grid(y, sr)
    analysis = analyze_structure(y, sr, grid)

    drops = analysis.drops()
    assert len(drops) >= 1, f"Se esperaba al menos 1 drop, hay {len(drops)}"


def test_preview_plan_has_all_drops():
    y, sr = _make_synthetic_track()
    grid = detect_beat_grid(y, sr)
    analysis = analyze_structure(y, sr, grid)
    plan = build_preview_plan(analysis)

    n_drops_original = len(analysis.drops())
    n_drops_plan = sum(1 for s in plan.segments if s.section.type == SectionType.DROP)
    assert n_drops_plan == n_drops_original, (
        f"Plan incluye {n_drops_plan} drops pero el original tiene {n_drops_original}"
    )


def test_preview_plan_segments_in_order():
    y, sr = _make_synthetic_track()
    grid = detect_beat_grid(y, sr)
    analysis = analyze_structure(y, sr, grid)
    plan = build_preview_plan(analysis)

    times = [s.source_start for s in plan.segments]
    assert times == sorted(times), "Los segmentos del plan no están en orden temporal"


def test_preview_plan_max_3_cuts():
    """El plan generado por defecto debe contener como máximo 3 cortes."""
    y, sr = _make_synthetic_track()
    grid = detect_beat_grid(y, sr)
    analysis = analyze_structure(y, sr, grid)
    plan = build_preview_plan(analysis)

    assert len(plan.segments) <= 3, f"El plan tiene {len(plan.segments)} cortes, pero el máximo permitido por defecto es 3"


def test_drop_fullness_detects_loaded_drops():
    """Un drop cargado con bombo y melodía/leads debe tener mayor plenitud (fullness) que un bombo solo."""
    y, sr = _make_synthetic_track()
    grid = detect_beat_grid(y, sr)
    analysis = analyze_structure(y, sr, grid)

    drops = analysis.drops()
    for d in drops:
        assert hasattr(d, "fullness")
        assert d.fullness > 0.40, f"El drop debería tener fullness > 0.40, tiene {d.fullness}"


def test_buildup_and_breakdown_detection():
    """Verifica que las subidas y descansos se distingan con precisión y no se colapsen."""
    y, sr = _make_synthetic_track()
    grid = detect_beat_grid(y, sr)
    analysis = analyze_structure(y, sr, grid)

    buildups = analysis.buildups()
    breakdowns = analysis.breakdowns()
    drops = analysis.drops()

    assert len(drops) >= 1, "Debe detectar al menos un drop"
    assert len(buildups) >= 1, "Debe detectar al menos una subida (buildup)"
    assert len(breakdowns) >= 1, "Debe detectar al menos un descanso (breakdown)"

    # Los descansos deben tener menor energía de bombo que los drops
    avg_drop_kick = np.mean([d.bass_energy for d in drops])
    avg_bd_kick = np.mean([b.bass_energy for b in breakdowns])
    assert avg_drop_kick > avg_bd_kick, "El bombo en el drop debe superar al bombo del descanso"

