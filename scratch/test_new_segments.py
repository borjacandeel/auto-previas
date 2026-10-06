"""
Probar la nueva implementación de build_preview_plan y verificar tests.
"""

from src.analysis.structure import analyze_structure, SectionType, Section, StructureAnalysis
from src.analysis.bpm import detect_beat_grid
import soundfile as sf
import numpy as np

def build_perfect_preview_plan(
    analysis: StructureAnalysis,
    stretch_factor: float = 1.075,
    target_min: float = 130.0,
    target_max: float = 195.0,
):
    from src.analysis.segments import PreviewPlan, PreviewSegment, _estimated_final
    sections = analysis.sections
    if not sections:
        return PreviewPlan()

    all_drops = [s for s in sections if s.type == SectionType.DROP]
    if not all_drops:
        by_energy = sorted(sections, key=lambda s: getattr(s, "fullness", s.energy), reverse=True)
        selected = sorted(by_energy[:3], key=lambda s: s.start_time)
        segs = [PreviewSegment(section=s, trimmed_start=0.0, trimmed_end=s.duration) for s in selected]
        raw = sum(s.duration for s in segs)
        return PreviewPlan(
            segments=segs,
            estimated_duration_before_stretch=raw,
            estimated_duration_after_stretch=_estimated_final(raw, stretch_factor),
        )

    # Duración estimada de un compás (4 beats)
    bpm = analysis.bpm if analysis.bpm > 0 else 128.0
    bar_dur = 4.0 * (60.0 / bpm)
    bu_dur = 6.0 * bar_dur  # 6 compases estándar de subida (~9.3s a 155 BPM)

    # Identificar drops principales (filtrar mini-drops de puente si hay drops largos de más de 30s)
    major_drops = [d for d in all_drops if d.duration >= 20.0]
    if len(major_drops) < 2:
        major_drops = all_drops

    raw_cuts = [] # (start_time, end_time, section_ref)

    if len(major_drops) >= 3:
        # CASO 3 DROPS: 3 cortes profesionales (Subida 1 + Drop 1, Subida 2 + Drop 2, Subida 3 + Drop 3)
        # Seleccionar los 3 principales cronológicamente
        if len(major_drops) == 3:
            d1, d2, d3 = major_drops
        # Si hay más de 3, seleccionar los 3 de mayor impacto musical (plenitud * duración) en orden temporal
        def _drop_score(d):
            # Masa acústica: combina la carga instrumental/bombo con la envergadura temporal del drop
            f = getattr(d, "fullness", d.energy)
            return f * np.sqrt(d.duration)

        top_3 = sorted(sorted(major_drops, key=_drop_score, reverse=True)[:3], key=lambda d: d.start_time)
        d1, d2, d3 = top_3

        # ── CORTE 1: Intro / Tema + Subida 1 + Drop 1 ──
        idx_d1 = sections.index(d1)
        prev_d1 = sections[idx_d1 - 1] if idx_d1 > 0 else None
        
        # Inicio del Corte 1: si hay subida detectada, usarla; si hay intro previa corta, incluir tema
        if prev_d1 and prev_d1.type == SectionType.BUILDUP:
            bu_s = prev_d1.start_time
            # Si antes de la subida hay intro, incluir unos compases de melodía de tema
            c1_start = max(0.0, bu_s - 8.0 * bar_dur) if bu_s >= 8.0 * bar_dur else 0.0
        else:
            c1_start = max(0.0, d1.start_time - bu_dur)

        # Duración de Drop 1: hasta 28 compases (~43s) alineado a compás
        drop1_bars = min(int(d1.duration / bar_dur), 28)
        c1_end = d1.start_time + drop1_bars * bar_dur
        raw_cuts.append((c1_start, c1_end, d1))

        # ── CORTE 2: Subida 2 + Drop 2 Clímax ──
        idx_d2 = sections.index(d2)
        prev_d2 = sections[idx_d2 - 1] if idx_d2 > 0 else None
        if prev_d2 and prev_d2.type == SectionType.BUILDUP:
            c2_start = prev_d2.start_time
        else:
            c2_start = max(c1_end + 2.0, d2.start_time - bu_dur)

        drop2_bars = min(int(d2.duration / bar_dur), 28)
        c2_end = d2.start_time + drop2_bars * bar_dur
        raw_cuts.append((c2_start, c2_end, d2))

        # ── CORTE 3: Subida 3 + Drop 3 Final ──
        idx_d3 = sections.index(d3)
        prev_d3 = sections[idx_d3 - 1] if idx_d3 > 0 else None
        if prev_d3 and prev_d3.type == SectionType.BUILDUP:
            c3_start = prev_d3.start_time
        else:
            c3_start = max(c2_end + 2.0, d3.start_time - bu_dur)

        drop3_bars = min(int(d3.duration / bar_dur), 24)
        c3_end = d3.start_time + drop3_bars * bar_dur
        raw_cuts.append((c3_start, c3_end, d3))

    elif len(major_drops) == 2:
        # CASO 2 DROPS:
        # Corte 1: Subida 1 + Drop 1
        # Corte 2: Breakdown Melódico Central + Subida 2
        # Corte 3: Drop 2 (Clímax final)
        d1, d2 = major_drops[0], major_drops[1]
        
        idx_d1 = sections.index(d1)
        prev_d1 = sections[idx_d1 - 1] if idx_d1 > 0 else None
        c1_start = prev_d1.start_time if (prev_d1 and prev_d1.type == SectionType.BUILDUP) else max(0.0, d1.start_time - bu_dur)
        drop1_bars = min(int(d1.duration / bar_dur), 28)
        c1_end = d1.start_time + drop1_bars * bar_dur
        raw_cuts.append((c1_start, c1_end, d1))

        # Breakdown central
        breakdowns = [s for s in sections if s.type == SectionType.BREAKDOWN and c1_end <= s.start_time < d2.start_time]
        idx_d2 = sections.index(d2)
        prev_d2 = sections[idx_d2 - 1] if idx_d2 > 0 else None
        bu2_start = prev_d2.start_time if (prev_d2 and prev_d2.type == SectionType.BUILDUP) else max(c1_end, d2.start_time - bu_dur)

        if breakdowns:
            best_bd = max(breakdowns, key=lambda b: (getattr(b, "melody_energy", 0.5), b.duration))
            c2_start = best_bd.start_time
            c2_end = d2.start_time  # incluye breakdown + subida 2
            raw_cuts.append((c2_start, c2_end, best_bd))
        else:
            c2_start = bu2_start
            # Si no hay breakdown, Corte 2 es la subida 2
            c2_end = d2.start_time
            raw_cuts.append((c2_start, c2_end, prev_d2 if prev_d2 else d2))

        # Corte 3: Drop 2 entero/clímax
        drop2_bars = min(int(d2.duration / bar_dur), 32)
        c3_end = d2.start_time + drop2_bars * bar_dur
        raw_cuts.append((d2.start_time, c3_end, d2))

    else:
        # CASO 1 DROP:
        d1 = all_drops[0]
        # Corte 1: Intro / Tema
        intros = [s for s in sections if s.type == SectionType.INTRO and s.end_time <= d1.start_time]
        if intros:
            raw_cuts.append((intros[0].start_time, min(intros[0].end_time, 30.0), intros[0]))
        # Corte 2: Breakdown / Melodía + Subida
        idx_d1 = sections.index(d1)
        prev_d1 = sections[idx_d1 - 1] if idx_d1 > 0 else None
        bu_s = prev_d1.start_time if (prev_d1 and prev_d1.type == SectionType.BUILDUP) else max(0.0, d1.start_time - bu_dur)
        raw_cuts.append((max(0.0, bu_s - 16.0), d1.start_time, prev_d1 if prev_d1 else d1))
        # Corte 3: Drop Clímax
        drop_bars = min(int(d1.duration / bar_dur), 32)
        raw_cuts.append((d1.start_time, d1.start_time + drop_bars * bar_dur, d1))

    # Limitar estrictamente a MÁXIMO 3 CORTES
    raw_cuts = sorted(raw_cuts, key=lambda c: c[0])[:3]

    # Convertir a objetos PreviewSegment
    segments = []
    for s_t, e_t, ref_sec in raw_cuts:
        dur = e_t - s_t
        if dur >= 4.0:
            # Crear sección ajustada para que source_start y source_end sean exactos
            sec = Section(
                type=ref_sec.type,
                start_time=s_t,
                end_time=e_t,
                energy=ref_sec.energy,
                bass_energy=ref_sec.bass_energy,
                melody_energy=getattr(ref_sec, "melody_energy", 0.5),
                fullness=getattr(ref_sec, "fullness", 0.5),
            )
            segments.append(PreviewSegment(
                section=sec,
                trimmed_start=0.0,
                trimmed_end=dur,
            ))

    raw_total = sum(s.duration for s in segments)
    final_est = _estimated_final(raw_total, stretch_factor)

    return PreviewPlan(
        segments=segments,
        estimated_duration_before_stretch=raw_total,
        estimated_duration_after_stretch=final_est,
    )

# Probar en ORIGINAL.wav
orig_path = "/Users/borjacandel/Documents/AutoPrevias/ejemplos/ORIGINAL.wav"
y, sr = sf.read(orig_path)
if y.ndim > 1: y = y.mean(axis=1)
grid = detect_beat_grid(y, sr)
struct_orig = analyze_structure(y, sr, grid)

plan = build_perfect_preview_plan(struct_orig, stretch_factor=165.0/155.0)
print("\n" + plan.summary())

