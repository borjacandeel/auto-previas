"""
Selección de segmentos para la previa a partir de la estructura detectada.

Reglas musicales profesionales:
- Los drops principales deben sonar contundentes y amplios. Está bien recortar
  la cola de un drop muy largo (>40s) para dejar 24-36s (16 a 24 compases completos),
  pero NUNCA trocearlo en micro-fragmentos sin sentido.
- Incluir siempre la MELODÍA principal (breakdown melódico con leads, acordes y voces).
- Incluir la subida (buildup) inmediatamente anterior a cada drop para generar tensión.
- Incluir una intro musical adecuada (10-16s).
- Ajustar la duración total para que tras el time-stretch (factor medio ~1.075)
  el resultado final caiga siempre en el rango ideal de [2:00, 3:00] (120s – 180s).
"""

from dataclasses import dataclass, field
from typing import List, Tuple

from .structure import Section, SectionType, StructureAnalysis

# Rango objetivo en segundos para la SELECCIÓN (antes de time-stretch)
TARGET_MIN_SEC = 90.0
TARGET_MAX_SEC = 129.0   # ~120s final tras factor 1.075

# Rango final deseado tras time-stretch (máx 2:00 min por defecto)
FINAL_MIN_SEC = 60.0
FINAL_MAX_SEC = 120.0    # 2:00 máx por defecto

# Factor medio de stretch esperado
AVG_STRETCH_FACTOR = 1.075


@dataclass
class PreviewSegment:
    section: Section
    trimmed_start: float   # tiempo de inicio dentro de la sección (relativo a section.start_time)
    trimmed_end: float     # tiempo de fin dentro de la sección

    @property
    def duration(self) -> float:
        return self.trimmed_end - self.trimmed_start

    @property
    def source_start(self) -> float:
        return self.section.start_time + self.trimmed_start

    @property
    def source_end(self) -> float:
        return self.section.start_time + self.trimmed_end


@dataclass
class PreviewPlan:
    segments: List[PreviewSegment] = field(default_factory=list)
    estimated_duration_before_stretch: float = 0.0
    estimated_duration_after_stretch: float = 0.0
    drop_starts: List[float] = field(default_factory=list)

    def total_raw_duration(self) -> float:
        return sum(s.duration for s in self.segments)

    def summary(self) -> str:
        lines = [f"Previa — {len(self.segments)} segmentos:"]
        t = 0.0
        for seg in self.segments:
            lines.append(
                f"  [{seg.section.type.value:10s}] "
                f"src {seg.source_start:.1f}s–{seg.source_end:.1f}s "
                f"({seg.duration:.1f}s)  →  previa {t:.1f}s–{t+seg.duration:.1f}s"
            )
            t += seg.duration
        lines.append(
            f"  Total seleccionado: {self.total_raw_duration():.1f}s "
            f"| estimado tras stretch: {self.estimated_duration_after_stretch:.1f}s"
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _full_segment(section: Section) -> PreviewSegment:
    return PreviewSegment(
        section=section,
        trimmed_start=0.0,
        trimmed_end=section.duration,
    )


def _trim_to(seg: PreviewSegment, max_duration: float) -> PreviewSegment:
    """Recorta un segmento al máximo de max_duration segundos desde su inicio."""
    if seg.duration <= max_duration:
        return seg
    return PreviewSegment(
        section=seg.section,
        trimmed_start=seg.trimmed_start,
        trimmed_end=seg.trimmed_start + max_duration,
    )


def _estimated_final(raw_duration: float, stretch: float = AVG_STRETCH_FACTOR) -> float:
    return raw_duration / stretch


def _buildup_start(sections: list, drop_sec: "Section", bar_dur: float, max_bars: int = 8) -> float:
    """
    Busca hacia atrás desde drop_sec el inicio real del buildup/breakdown más próximo.
    Si encuentra BUILDUP, devuelve su inicio exacto.
    Si encuentra BREAKDOWN, toma los últimos N compases (no todo el breakdown, que puede ser largo).
    Si no encuentra nada útil, cae al offset fijo de max_bars compases.
    """
    try:
        idx = sections.index(drop_sec)
    except ValueError:
        return max(0.0, drop_sec.start_time - max_bars * bar_dur)

    for i in range(idx - 1, -1, -1):
        s = sections[i]
        if s.type == SectionType.BUILDUP:
            return s.start_time
        if s.type == SectionType.BREAKDOWN:
            # Coger los últimos max_bars compases del breakdown para no incluir demasiado
            window = min(s.duration, max_bars * bar_dur)
            return max(s.start_time, s.end_time - window)
        if s.type in (SectionType.DROP, SectionType.INTRO):
            break

    return max(0.0, drop_sec.start_time - max_bars * bar_dur)


# ---------------------------------------------------------------------------
# Lógica de selección
# ---------------------------------------------------------------------------

def build_preview_plan(
    analysis: StructureAnalysis,
    stretch_factor: float = AVG_STRETCH_FACTOR,
    target_min: float = TARGET_MIN_SEC,
    target_max: float = TARGET_MAX_SEC,
    target_duration_sec: float | None = None,
    cfg: dict | None = None,
) -> PreviewPlan:
    """
    Construye el plan de segmentos para la previa con MÁXIMO 3 CORTES por defecto
    o con la duración exacta requerida si se especifica un Preset (15s, 30s, 60s).
    """
    sections = analysis.sections
    if not sections:
        return PreviewPlan()

    # Si se pasa configuración con duración de previa objetivo o valor por defecto
    effective_target: float | None = target_duration_sec
    if effective_target is None and cfg is not None:
        effective_target = float(cfg.get("default_preset_sec", cfg.get("preview_max_sec", 120.0)))
    if effective_target is None:
        effective_target = 120.0  # Siempre 120s (máximo 2 minutos) por defecto

    all_drops = [s for s in sections if s.type == SectionType.DROP]
    bpm = analysis.bpm if analysis.bpm > 0 else 128.0
    bar_dur = 4.0 * (60.0 / bpm)
    bu_dur = 6.0 * bar_dur

    if not all_drops:
        # Fallback si no hay drops: tomar secciones con mayor energía
        by_energy = sorted(sections, key=lambda s: getattr(s, "fullness", s.energy), reverse=True)
        limit = 1 if (effective_target and effective_target <= 20.0) else (2 if effective_target and effective_target <= 45.0 else 3)
        selected = sorted(by_energy[:limit], key=lambda s: s.start_time)
        segs = []
        for s in selected:
            dur = s.duration
            if effective_target and dur > effective_target:
                dur = effective_target
            segs.append(PreviewSegment(section=s, trimmed_start=0.0, trimmed_end=dur))
        raw = sum(s.duration for s in segs)
        return PreviewPlan(
            segments=segs,
            estimated_duration_before_stretch=raw,
            estimated_duration_after_stretch=_estimated_final(raw, stretch_factor),
        )

    # ── MODO PRESET RÁPIDO: 15s (Teaser) ──────────────────────────────────
    if effective_target is not None and effective_target <= 20.0:
        # Tomar el drop de mayor impacto
        best_drop = max(all_drops, key=lambda d: getattr(d, "fullness", d.energy) * (d.duration ** 0.5))
        bu_s = max(0.0, best_drop.start_time - min(4.0 * bar_dur, 5.0))
        target_len = effective_target if effective_target >= 10.0 else 15.0
        c_end = min(best_drop.end_time, bu_s + target_len)
        sec = Section(
            type=best_drop.type,
            start_time=bu_s,
            end_time=c_end,
            energy=best_drop.energy,
            fullness=getattr(best_drop, "fullness", 0.8),
        )
        segs = [PreviewSegment(section=sec, trimmed_start=0.0, trimmed_end=c_end - bu_s)]
        raw = sum(s.duration for s in segs)
        return PreviewPlan(
            segments=segs,
            estimated_duration_before_stretch=raw,
            estimated_duration_after_stretch=raw,
            drop_starts=[best_drop.start_time],
        )

    # ── MODO PRESET RÁPIDO: 30s (Promo) ───────────────────────────────────
    if effective_target is not None and 20.0 < effective_target <= 45.0:
        if len(all_drops) >= 2:
            d1, d2 = all_drops[0], all_drops[1]
            c1_s = max(0.0, d1.start_time - min(3.0 * bar_dur, 4.0))
            c1_e = c1_s + 14.0
            c2_s = max(c1_e + 2.0, d2.start_time - min(3.0 * bar_dur, 4.0))
            c2_e = c2_s + (effective_target - 14.0)

            s1 = Section(type=d1.type, start_time=c1_s, end_time=c1_e, energy=d1.energy)
            s2 = Section(type=d2.type, start_time=c2_s, end_time=c2_e, energy=d2.energy)
            segs = [
                PreviewSegment(section=s1, trimmed_start=0.0, trimmed_end=c1_e - c1_s),
                PreviewSegment(section=s2, trimmed_start=0.0, trimmed_end=c2_e - c2_s),
            ]
            preset_drops = [d1.start_time, d2.start_time]
        else:
            d1 = all_drops[0]
            c1_s = max(0.0, d1.start_time - min(4.0 * bar_dur, 6.0))
            c1_e = min(d1.end_time, c1_s + effective_target)
            s1 = Section(type=d1.type, start_time=c1_s, end_time=c1_e, energy=d1.energy)
            segs = [PreviewSegment(section=s1, trimmed_start=0.0, trimmed_end=c1_e - c1_s)]
            preset_drops = [d1.start_time]

        raw = sum(s.duration for s in segs)
        return PreviewPlan(
            segments=segs,
            estimated_duration_before_stretch=raw,
            estimated_duration_after_stretch=raw,
            drop_starts=preset_drops,
        )

    # Filtrar drops principales por impacto acústico (duración y fullness)
    major_drops = [d for d in all_drops if d.duration >= 20.0]
    if len(major_drops) < 2:
        major_drops = all_drops
    if len(major_drops) < 2:
        major_drops = all_drops

    raw_cuts: List[Tuple[float, float, Section]] = []

    if len(major_drops) >= 3:
        # ── CASO >= 3 DROPS: 3 CORTES POTENTES CON SUBIDAS ──
        # Seleccionar los 3 de mayor impacto musical (masa acústica) ordenados cronológicamente
        def _drop_impact(d: Section) -> float:
            f = getattr(d, "fullness", d.energy)
            return f * (d.duration ** 0.5)

        top_3 = sorted(
            sorted(major_drops, key=_drop_impact, reverse=True)[:3],
            key=lambda d: d.start_time,
        )
        d1, d2, d3 = top_3

        # Corte 1: Intro / Tema + Subida 1 + Drop 1
        idx_d1 = sections.index(d1)
        prev_d1 = sections[idx_d1 - 1] if idx_d1 > 0 else None
        if prev_d1 and prev_d1.type == SectionType.BUILDUP:
            bu_s = prev_d1.start_time
            # Si la intro antes de la subida es concisa (<= 16 compases), empezar desde el inicio
            if bu_s <= 16.0 * bar_dur:
                c1_start = 0.0
            else:
                c1_start = max(0.0, bu_s - 8.0 * bar_dur)
        else:
            c1_start = _buildup_start(sections, d1, bar_dur)

        drop1_bars = min(int(d1.duration / bar_dur), 28)
        c1_end = d1.start_time + drop1_bars * bar_dur
        raw_cuts.append((c1_start, c1_end, d1))

        # Corte 2: Parón Melódico Central + Subida 2 + Drop 2 Clímax
        # (Aprendido de PREVIA 2: el clímax central debe incluir los compases melódicos del breakdown)
        idx_d2 = sections.index(d2)
        prev_d2 = sections[idx_d2 - 1] if idx_d2 > 0 else None
        bu2_start = prev_d2.start_time if (prev_d2 and prev_d2.type == SectionType.BUILDUP) else _buildup_start(sections, d2, bar_dur)

        # Buscar breakdown melódico entre el final del Corte 1 y la Subida 2
        candidate_bd = None
        for s in sections:
            if s.type == SectionType.BREAKDOWN and c1_end <= s.start_time < bu2_start:
                candidate_bd = s
                break

        if candidate_bd:
            # Tomar hasta 12-16 compases de breakdown melódico antes de la subida
            bd_len = min(candidate_bd.duration, 12.0 * bar_dur)
            c2_start = max(candidate_bd.start_time, bu2_start - bd_len)
        elif prev_d2 and prev_d2.type == SectionType.BUILDUP:
            c2_start = prev_d2.start_time
        else:
            c2_start = max(c1_end + 2.0, d2.start_time - bu_dur)

        drop2_bars = min(int(d2.duration / bar_dur), 28)
        c2_end = d2.start_time + drop2_bars * bar_dur
        raw_cuts.append((c2_start, c2_end, d2))

        # Corte 3: Subida 3 + Drop 3 Final
        idx_d3 = sections.index(d3)
        prev_d3 = sections[idx_d3 - 1] if idx_d3 > 0 else None
        if prev_d3 and prev_d3.type == SectionType.BUILDUP:
            c3_start = prev_d3.start_time
        else:
            c3_start = _buildup_start(sections, d3, bar_dur)

        drop3_bars = min(int(d3.duration / bar_dur), 24)
        c3_end = d3.start_time + drop3_bars * bar_dur
        raw_cuts.append((c3_start, c3_end, d3))

    elif len(major_drops) == 2:
        # ── CASO 2 DROPS: Subida 1 + Drop 1, Breakdown + Subida 2, Drop 2 ──
        d1, d2 = major_drops[0], major_drops[1]

        # Corte 1: Subida 1 + Drop 1
        idx_d1 = sections.index(d1)
        prev_d1 = sections[idx_d1 - 1] if idx_d1 > 0 else None
        c1_start = prev_d1.start_time if (prev_d1 and prev_d1.type == SectionType.BUILDUP) else _buildup_start(sections, d1, bar_dur)
        drop1_bars = min(int(d1.duration / bar_dur), 28)
        c1_end = d1.start_time + drop1_bars * bar_dur
        raw_cuts.append((c1_start, c1_end, d1))

        # Corte 2: Breakdown melódico central + Subida 2
        breakdowns = [s for s in sections if s.type == SectionType.BREAKDOWN and c1_end <= s.start_time < d2.start_time]
        idx_d2 = sections.index(d2)
        prev_d2 = sections[idx_d2 - 1] if idx_d2 > 0 else None
        bu2_start = prev_d2.start_time if (prev_d2 and prev_d2.type == SectionType.BUILDUP) else _buildup_start(sections, d2, bar_dur)

        if breakdowns:
            best_bd = max(breakdowns, key=lambda b: (getattr(b, "melody_energy", 0.5), b.duration))
            c2_start = best_bd.start_time
            c2_end = d2.start_time
            raw_cuts.append((c2_start, c2_end, best_bd))
        else:
            c2_start = bu2_start
            c2_end = d2.start_time
            raw_cuts.append((c2_start, c2_end, prev_d2 if prev_d2 else d2))

        # Corte 3: Drop 2 (Clímax final)
        drop2_bars = min(int(d2.duration / bar_dur), 32)
        c3_end = d2.start_time + drop2_bars * bar_dur
        raw_cuts.append((d2.start_time, c3_end, d2))

    else:
        # ── CASO 1 DROP: Intro/Tema, Breakdown + Subida, Drop Clímax ──
        d1 = all_drops[0]
        intros = [s for s in sections if s.type == SectionType.INTRO and s.end_time <= d1.start_time]
        if intros:
            raw_cuts.append((intros[0].start_time, min(intros[0].end_time, 30.0), intros[0]))
        
        idx_d1 = sections.index(d1)
        prev_d1 = sections[idx_d1 - 1] if idx_d1 > 0 else None
        bu_s = prev_d1.start_time if (prev_d1 and prev_d1.type == SectionType.BUILDUP) else _buildup_start(sections, d1, bar_dur)
        raw_cuts.append((bu_s, d1.start_time, prev_d1 if prev_d1 else d1))

        drop_bars = min(int(d1.duration / bar_dur), 32)
        raw_cuts.append((d1.start_time, d1.start_time + drop_bars * bar_dur, d1))

    # Asegurar orden cronológico y límite estricto de MÁXIMO 3 CORTES
    raw_cuts = sorted(raw_cuts, key=lambda c: c[0])[:3]

    # Convertir a objetos PreviewSegment
    segments: List[PreviewSegment] = []
    for s_t, e_t, ref_sec in raw_cuts:
        dur = e_t - s_t
        if dur >= 4.0:
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

    # Asegurar que nunca supere el límite máximo (120s / 2 min por defecto)
    max_limit = effective_target if effective_target is not None else FINAL_MAX_SEC
    if final_est > max_limit and final_est > 0:
        ratio = max_limit / final_est
        trimmed_segs = []
        for seg in segments:
            new_dur = max(4.0, seg.duration * ratio)
            trimmed_segs.append(PreviewSegment(
                section=seg.section,
                trimmed_start=seg.trimmed_start,
                trimmed_end=seg.trimmed_start + new_dur,
            ))
        segments = trimmed_segs
        raw_total = sum(s.duration for s in segments)
        final_est = _estimated_final(raw_total, stretch_factor)

    # Identificar momentos de impacto de drops incluidos en los segmentos
    included_drops = [
        s.start_time for s in all_drops
        if any(seg.source_start <= s.start_time <= seg.source_end for seg in segments)
    ]
    if not included_drops and all_drops:
        included_drops = [d.start_time for d in all_drops[:3]]

    return PreviewPlan(
        segments=segments,
        estimated_duration_before_stretch=raw_total,
        estimated_duration_after_stretch=final_est,
        drop_starts=included_drops,
    )
