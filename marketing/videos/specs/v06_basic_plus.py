"""Vídeo 6 · Basic o Plus: cuál te toca (voz en castellano)."""
SPEC = dict(
    voice="em_alex", lang="es", speed=1.04, groove_from=3.0,
    scenes=[
        dict(type="words", dur=3.0, bars=True, top=640, gap=0.7, vo="¿Basic o Plus? Te lo explico en diez segundos.",
             lines=[dict(t="¿BASIC", cls="", size=230), dict(t="O PLUS?", cls="red", size=230, big=True)]),
        dict(type="compare", dur=6.0, panels=[dict(name="BASIC", cls="basic big", top=600, at=0.2, items_at=[1.0, 1.9, 3.0, 4.1],
             items=["Previa MP3 320 kbps", "Análisis de BPM y tonalidad", "Vídeo con marca de agua", "15 s · 30 s · 60 s · 2 min"])],
             vo="Basic: previa automática en eme pe tres de trescientos veinte, y vídeo animado con marca de agua.", vo_at=0.5),
        dict(type="compare", dur=8.0, panels=[dict(name="PLUS", cls="plus big", top=480, at=0.2, items_at=[0.9, 1.9, 3.1, 4.3, 5.5],
             items=["Todo lo de Basic", "WAV 24 bit y FLAC", "Vídeo sin marca de agua y final a elegir", "Tu firma, Voice Drop y modo promo", "Presets, lote y carpeta vigilada"])],
             vo="Plus: uave de veinticuatro bits, flac, vídeo sin marca de agua, tu firma, modo promo, presets y lote.", vo_at=0.5),
        dict(type="cta", dur=7.0, click_at=4.4, line1="Elige la tuya.", line2="Basic o Plus.", vo="Elige la tuya en Pei jip.", vo_at=1.2),
    ])
