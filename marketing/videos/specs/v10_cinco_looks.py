"""Vídeo 10 · Un tema, 5 looks (sin voz)."""
F = lambda src, label, color, at: dict(src=src, label=label, color=color, at=at)
SPEC = dict(
    voice="em_alex", lang="es", groove_from=2.8,
    scenes=[
        dict(type="words", dur=2.8, bars=True, top=520, gap=0.5,
             lines=[dict(t="UN TEMA", size=230), dict(t="5 LOOKS", cls="red", size=250, big=True)]),
        dict(type="gallery", dur=7.4, frames=[F("neon_916_crimson", "ROJO CARMESÍ", "#ff1f3a", 0.5), F("neon_916_rave", "VERDE RAVE", "#39ff14", 1.9),
                                               F("neon_916_amber", "ÁMBAR SOLAR", "#ffb700", 3.3), F("neon_916_radical", "CIAN Y MAGENTA", "#00f5ff", 4.7),
                                               F("neon_916_cyber", "CYBER VIOLET", "#b026ff", 6.1)]),
        dict(type="words", dur=3.4, top=520, gap=0.6, sub="Tu carátula, tu título, tu banner.<br>9:16 · 1:1 · 16:9", sub_at=1.6, sub_top=1330,
             lines=[dict(t="ELIGE", size=200), dict(t="TU LOOK", cls="red", size=230, big=True)]),
        dict(type="cta", dur=7.0, click_at=4.4, line1="Exporta en 30 segundos.", line2="Con tu estilo."),
    ])
