"""Vídeo nuevo 2 · «Basic vs Plus: ¿cuál es para ti?». Sin voz."""
SPEC = dict(
    tall=True,
    voice="edge:es-ES-AlvaroNeural", lang="es", speed=1.16, groove_from=2.4,
    scenes=[
        dict(type="words", dur=2.6, bars=True, top=600, gap=0.5,
             lines=[dict(t="¿BASIC", size=250), dict(t="O PLUS?", cls="red", size=250, big=True)]),
        dict(type="compare", dur=5.0, panels=[dict(name="BASIC", cls="basic big", top=420, at=0.2, items_at=[0.7, 1.4, 2.1, 2.8],
             items=["Previa automática", "Cortes y efectos a mano", "MP3 320 kbps", "Vídeo con marca de agua"])]),
        dict(type="compare", dur=6.6, panels=[dict(name="PLUS", cls="plus big", top=340, at=0.2, items_at=[0.7, 1.4, 2.1, 2.8, 3.5, 4.2],
             items=["Todo lo de Basic", "WAV 24 bit y FLAC", "Vídeo sin marca de agua", "Tu propio logo en el vídeo", "Modo antifugas y tu voz", "Lote, presets y firma"])]),
        dict(type="words", dur=3.6, bars=True, top=420, gap=0.55,
             lines=[dict(t="BASIC", size=220), dict(t="PARA EMPEZAR", size=120), dict(t="PLUS", cls="red", size=220, big=True), dict(t="PARA TODO", cls="red", size=120)]),
        dict(type="cta", dual=True, dur=5.6, click_at=4.0, line1="Elige la tuya.", line2=""),
    ])
